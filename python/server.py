"""
ai.play server — out.in() implementation
Supports:
  out.in(key)
  out.in(key, user=auto)
  out.in(key, user=auto, storage=./shared/)
  out.in(key, user=auto, storage=./shared/, upload=https://memory.site.com)

Per-user memory: each connection identified by username.
Shared storage: all AI instances point at the same directory (NFS, network mount etc).
"""

import threading
import json
import time
import queue
import os
import re
import subprocess
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 7731

class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _check_key(self):
        key = self.headers.get('X-AIP-Key', '')
        if str(key) != str(self.server.api_key):
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "invalid api key"}')
            return False
        return True

    def _get_username(self):
        """Extract username from header, query string, or generate one."""
        # From header
        name = self.headers.get('X-AIP-User', '')
        if not name:
            # From query string ?user=name
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            name = params.get('user', [''])[0]
        return name or 'auto'

    def do_POST(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path

        if path == '/input':
            if not self._check_key():
                return

            length  = int(self.headers.get('Content-Length', 0))
            body    = self.rfile.read(length)
            username = self._get_username()

            try:
                data = json.loads(body)
                text = data.get('input', '')
                # Allow username override in body
                if data.get('user'):
                    username = data['user']
            except Exception:
                text = body.decode()

            # Put (username, text) into queue
            self.server.input_queue.put((username, text))

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            # Wait for response
            try:
                response = self.server.output_queue.get(timeout=30)
            except queue.Empty:
                response = 'timeout'

            self.wfile.write(json.dumps({
                'output': response,
                'user':   username,
            }).encode())

        elif path == '/disconnect':
            if not self._check_key():
                return
            username = self._get_username()
            if self.server.user_manager:
                self.server.user_manager.disconnect(username)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status": "disconnected"}')

        elif path == '/users':
            if not self._check_key():
                return
            users = self.server.user_manager.list_users() if self.server.user_manager else []
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'users': users}).encode())

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status':  'ok',
                'runtime': 'ai.play',
                'users':   len(self.server.user_manager.sessions) if self.server.user_manager else 0,
            }).encode())


class AIPServer:
    def __init__(self, api_key, user_mode=None, storage_dir=None,
                 remote_url=None, memory_mode='rule'):
        self.api_key      = str(api_key)
        self.user_mode    = user_mode     # 'auto' | specific name | None
        self.storage_dir  = storage_dir or '.aiplay_users'
        self.remote_url   = remote_url
        self.memory_mode  = memory_mode
        self.input_queue  = queue.Queue()
        self.output_queue = queue.Queue()
        self.httpd        = None
        self.tunnel_url   = None
        self._thread      = None
        self.user_manager = None
        self._current_user = None

        if user_mode is not None:
            from user_memory import UserMemoryManager
            self.user_manager = UserMemoryManager(
                storage_dir  = self.storage_dir,
                memory_mode  = self.memory_mode,
                remote_url   = self.remote_url,
            )

    def start(self):
        self.httpd = HTTPServer(('0.0.0.0', PORT), _Handler)
        self.httpd.api_key      = self.api_key
        self.httpd.input_queue  = self.input_queue
        self.httpd.output_queue = self.output_queue
        self.httpd.user_manager = self.user_manager

        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

        self.tunnel_url = self._establish_tunnel()

        print(f"[ai.play] Server running — port {PORT}")
        print(f"[ai.play] API key: {self.api_key}")
        if self.user_manager:
            print(f"[ai.play] User storage: {self.storage_dir}")
        if self.tunnel_url:
            print(f"[ai.play] Public URL: {self.tunnel_url}")
        else:
            print(f"[ai.play] Forward port {PORT} for public access")

    def get_input(self):
        """Returns (username, text) tuple."""
        result = self.input_queue.get()
        if isinstance(result, tuple):
            username, text = result
        else:
            username, text = 'unknown', result
        self._current_user = username

        # Load user memory if user manager is active
        if self.user_manager:
            session = self.user_manager.get_or_create(username)
            self._active_session = session
        else:
            self._active_session = None

        return text

    def get_current_user(self):
        return self._current_user

    def get_active_session(self):
        return getattr(self, '_active_session', None)

    def send_output(self, text):
        self.output_queue.put(str(text))
        # Save to active session memory
        if self._active_session:
            self._active_session.add('ai', str(text))

    def _establish_tunnel(self):
        if self._check_direct():
            print(f"[ai.play] Tunnel: direct (public IP detected)")
            return None
        url = self._try_cloudflare()
        if url: return url
        url = self._try_ngrok()
        if url: return url
        url = self._try_bore()
        if url: return url
        url = self._try_localhost_run()
        if url: return url
        return None

    def _check_direct(self):
        try:
            urllib.request.urlopen('https://api.ipify.org', timeout=3)
            return True
        except Exception:
            return False

    def _try_cloudflare(self):
        try:
            proc = subprocess.Popen(
                ['cloudflared', 'tunnel', '--url', f'http://localhost:{PORT}'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            time.sleep(4)
            output = proc.stderr.read1(4096).decode() if hasattr(proc.stderr,'read1') else ''
            m = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', output)
            if m:
                print(f"[ai.play] Tunnel: Cloudflare")
                return m.group(0)
        except Exception:
            pass
        return None

    def _try_ngrok(self):
        try:
            subprocess.Popen(['ngrok','http',str(PORT)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(3)
            r = urllib.request.urlopen('http://localhost:4040/api/tunnels', timeout=3)
            data = json.loads(r.read())
            for t in data.get('tunnels',[]):
                if t.get('proto') == 'https':
                    print(f"[ai.play] Tunnel: ngrok")
                    return t['public_url']
        except Exception:
            pass
        return None

    def _try_bore(self):
        try:
            proc = subprocess.Popen(
                ['bore','local',str(PORT),'--to','bore.pub'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            time.sleep(3)
            line = proc.stdout.readline().decode()
            m = re.search(r'bore\.pub:\d+', line)
            if m:
                print(f"[ai.play] Tunnel: bore.pub")
                return f'http://{m.group(0)}'
        except Exception:
            pass
        return None

    def _try_localhost_run(self):
        try:
            proc = subprocess.Popen(
                ['ssh','-R',f'80:localhost:{PORT}','nokey@localhost.run',
                 '-o','StrictHostKeyChecking=no'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            time.sleep(5)
            line = proc.stdout.readline().decode()
            m = re.search(r'https://[a-z0-9\-]+\.lhr\.life', line)
            if m:
                print(f"[ai.play] Tunnel: localhost.run")
                return m.group(0)
        except Exception:
            pass
        return None
