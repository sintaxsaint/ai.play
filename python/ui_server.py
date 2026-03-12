"""
ai.play test UI — test.ui(yes)
Opens a clean, modern browser chat interface for demoing and testing your AI locally.
"""

import threading
import webbrowser
import queue
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

UI_PORT = 7732

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ai.play — Test UI</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f0f13;
    --surface: #1a1a22;
    --border: #2a2a38;
    --accent: #7c6af7;
    --accent2: #a78bfa;
    --text: #e8e8f0;
    --muted: #6b6b80;
    --user-bg: #2d2b4e;
    --ai-bg: #1e1e2a;
    --radius: 14px;
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--surface);
  }
  .logo {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; font-weight: 700; color: white;
  }
  header h1 { font-size: 16px; font-weight: 600; color: var(--text); }
  header span { font-size: 12px; color: var(--muted); margin-left: 4px; }
  .status {
    margin-left: auto;
    display: flex; align-items: center; gap: 6px;
    font-size: 12px; color: var(--muted);
  }
  .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #4ade80; animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; } 50% { opacity: 0.4; }
  }
  #messages {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    scroll-behavior: smooth;
  }
  #messages::-webkit-scrollbar { width: 4px; }
  #messages::-webkit-scrollbar-track { background: transparent; }
  #messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
  .message {
    display: flex;
    gap: 12px;
    max-width: 80%;
    animation: fadeIn 0.2s ease;
  }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
  .message.user { align-self: flex-end; flex-direction: row-reverse; }
  .message.ai { align-self: flex-start; }
  .avatar {
    width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 600;
  }
  .message.user .avatar { background: var(--user-bg); color: var(--accent2); }
  .message.ai .avatar { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: white; }
  .bubble {
    padding: 12px 16px;
    border-radius: var(--radius);
    line-height: 1.6;
    font-size: 14px;
    max-width: 100%;
    word-break: break-word;
  }
  .message.user .bubble {
    background: var(--user-bg);
    border-bottom-right-radius: 4px;
    color: var(--text);
  }
  .message.ai .bubble {
    background: var(--ai-bg);
    border: 1px solid var(--border);
    border-bottom-left-radius: 4px;
    color: var(--text);
  }
  .typing { display: flex; gap: 4px; align-items: center; padding: 4px 0; }
  .typing span {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--muted); animation: bounce 1.2s infinite;
  }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce { 0%,80%,100% { transform: scale(0.7); } 40% { transform: scale(1); } }
  .input-area {
    padding: 16px 24px;
    border-top: 1px solid var(--border);
    background: var(--surface);
    display: flex;
    gap: 12px;
    align-items: flex-end;
  }
  #input {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    color: var(--text);
    font-size: 14px;
    resize: none;
    max-height: 120px;
    min-height: 44px;
    outline: none;
    transition: border-color 0.2s;
    font-family: inherit;
    line-height: 1.5;
  }
  #input:focus { border-color: var(--accent); }
  #input::placeholder { color: var(--muted); }
  #send {
    width: 44px; height: 44px;
    background: var(--accent);
    border: none; border-radius: 12px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: background 0.2s, transform 0.1s;
    flex-shrink: 0;
  }
  #send:hover { background: var(--accent2); }
  #send:active { transform: scale(0.95); }
  #send svg { width: 18px; height: 18px; fill: white; }
  #send:disabled { opacity: 0.4; cursor: not-allowed; }
  .empty-state {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 12px; color: var(--muted);
  }
  .empty-state .big-logo {
    width: 64px; height: 64px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 20px;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; font-weight: 800; color: white;
    margin-bottom: 8px;
  }
  .empty-state h2 { font-size: 20px; color: var(--text); }
  .empty-state p { font-size: 14px; text-align: center; max-width: 300px; line-height: 1.6; }
</style>
</head>
<body>
<header>
  <div class="logo">A</div>
  <h1>ai.play <span>Test UI</span></h1>
  <div class="status"><div class="dot"></div> Running</div>
</header>
<div id="messages">
  <div class="empty-state" id="empty">
    <div class="big-logo">A</div>
    <h2>ai.play</h2>
    <p>Your AI is ready. Send a message to start testing.</p>
  </div>
</div>
<div class="input-area">
  <textarea id="input" placeholder="Type a message..." rows="1"></textarea>
  <button id="send">
    <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
  </button>
</div>
<script>
  const msgs = document.getElementById('messages');
  const input = document.getElementById('input');
  const sendBtn = document.getElementById('send');
  const empty = document.getElementById('empty');
  let waiting = false;

  function addMsg(role, text) {
    if (empty) empty.remove();
    const div = document.createElement('div');
    div.className = `message ${role}`;
    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? 'You' : 'AI';
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;
    div.appendChild(avatar);
    div.appendChild(bubble);
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function addTyping() {
    const div = document.createElement('div');
    div.className = 'message ai';
    div.id = 'typing';
    div.innerHTML = '<div class="avatar">AI</div><div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  async function send() {
    const text = input.value.trim();
    if (!text || waiting) return;
    waiting = true;
    sendBtn.disabled = true;
    input.value = '';
    input.style.height = 'auto';
    addMsg('user', text);
    addTyping();
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({input: text})
      });
      const data = await res.json();
      document.getElementById('typing')?.remove();
      addMsg('ai', data.output || 'No response');
    } catch(e) {
      document.getElementById('typing')?.remove();
      addMsg('ai', 'Error connecting to AI runtime.');
    }
    waiting = false;
    sendBtn.disabled = false;
    input.focus();
  }

  sendBtn.addEventListener('click', send);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
</script>
</body>
</html>"""


class _UIHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())

    def do_POST(self):
        if self.path == '/chat':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            text = body.get('input', '')
            self.server.input_queue.put(text)
            try:
                response = self.server.output_queue.get(timeout=30)
            except queue.Empty:
                response = 'timeout'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'output': response}).encode())


class UIServer:
    def __init__(self):
        self.input_queue  = queue.Queue()
        self.output_queue = queue.Queue()
        self.httpd        = None

    def start(self):
        self.httpd = HTTPServer(('localhost', UI_PORT), _UIHandler)
        self.httpd.input_queue  = self.input_queue
        self.httpd.output_queue = self.output_queue
        t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        t.start()
        url = f'http://localhost:{UI_PORT}'
        print(f"[ai.play] Test UI: {url}")
        webbrowser.open(url)

    def get_input(self):
        return self.input_queue.get()

    def send_output(self, text):
        self.output_queue.put(str(text))
