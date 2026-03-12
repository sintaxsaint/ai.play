"""
ai.play user memory manager
Handles per-user memory with local + remote persistence.
Works with out.in(user=auto, storage=path) for shared data centre storage.

Memory file layout (local or shared mount):
    {storage_dir}/users/{username}/memory.json       — rule memory
    {storage_dir}/users/{username}/genmemory.json    — generative memory
    {storage_dir}/users/{username}/profile.json      — user metadata

Remote upload: POST memory JSON to a URL endpoint.
"""

import os
import json
import time
import uuid
import threading
import urllib.request
import urllib.error

DEFAULT_STORAGE = '.aiplay_users'

class UserSession:
    def __init__(self, username, storage_dir, memory_mode, remote_url=None):
        self.username    = username
        self.storage_dir = storage_dir
        self.memory_mode = memory_mode   # 'rule' | 'generative' | 'upload'
        self.remote_url  = remote_url
        self.is_new      = False
        self.memory      = None
        self._setup()

    def _user_dir(self):
        d = os.path.join(self.storage_dir, 'users', self.username)
        os.makedirs(d, exist_ok=True)
        return d

    def _setup(self):
        from memory_engine import RuleMemory, GenerativeMemory

        udir = self._user_dir()
        profile_path = os.path.join(udir, 'profile.json')

        # Check if user exists
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                profile = json.load(f)
            self.is_new = False
            print(f"[ai.play] User '{self.username}' found — loading memory")
        else:
            # New user
            profile = {
                'username':   self.username,
                'created':    time.time(),
                'sessions':   0,
            }
            with open(profile_path, 'w') as f:
                json.dump(profile, f)
            self.is_new = True
            print(f"[ai.play] New user '{self.username}' — creating memory")

        # Update session count
        profile['sessions'] = profile.get('sessions', 0) + 1
        profile['last_seen'] = time.time()
        with open(profile_path, 'w') as f:
            json.dump(profile, f)

        # Load appropriate memory type
        if self.memory_mode in ('generative', 'upload'):
            mem_path = os.path.join(udir, 'genmemory.json')
            self.memory = GenerativeMemory(path=mem_path)
        else:
            mem_path = os.path.join(udir, 'memory.json')
            self.memory = RuleMemory(path=mem_path)

    def add(self, role, text):
        if self.memory:
            self.memory.add(role, text)

    def get_context(self, query):
        if self.memory:
            return self.memory.get_context(query)
        return {}

    def format_for_context(self, ctx):
        if self.memory:
            return self.memory.format_for_context(ctx)
        return ''

    def save(self):
        """Save memory locally (already handled by memory engine on each add)."""
        # Memory is auto-saved on each add() call
        # This is a manual flush for disconnect events
        if self.memory and hasattr(self.memory, '_save'):
            self.memory._save()

    def upload(self):
        """Upload memory to remote URL if configured."""
        if not self.remote_url:
            return
        try:
            udir = self._user_dir()
            # Read all memory files
            payload = {'username': self.username, 'timestamp': time.time()}
            for fname in ('memory.json', 'genmemory.json', 'profile.json'):
                fpath = os.path.join(udir, fname)
                if os.path.exists(fpath):
                    with open(fpath, 'r') as f:
                        payload[fname] = json.load(f)

            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self.remote_url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'X-AIP-User':   self.username,
                }
            )
            urllib.request.urlopen(req, timeout=5)
            print(f"[ai.play] Memory uploaded for '{self.username}'")
        except Exception as e:
            print(f"[ai.play] Memory upload failed for '{self.username}': {e}")

    def disconnect(self):
        """Called when user disconnects — save and optionally upload."""
        self.save()
        if self.remote_url:
            # Upload in background so it doesn't block
            t = threading.Thread(target=self.upload, daemon=True)
            t.start()
        print(f"[ai.play] User '{self.username}' disconnected — memory saved")


class UserMemoryManager:
    """
    Manages multiple concurrent user sessions.
    Used by the server when out.in() has user= set.
    """
    def __init__(self, storage_dir=DEFAULT_STORAGE, memory_mode='rule', remote_url=None):
        self.storage_dir = os.path.expanduser(storage_dir)
        self.memory_mode = memory_mode
        self.remote_url  = remote_url
        self.sessions    = {}   # username -> UserSession
        os.makedirs(self.storage_dir, exist_ok=True)
        print(f"[ai.play] User storage: {self.storage_dir}")

    def get_or_create(self, username):
        """
        Get existing session or create new one.
        username can be a real name (passed by website) or auto-generated UUID.
        """
        if not username or username == 'auto':
            username = f'user_{uuid.uuid4().hex[:8]}'

        # Sanitise username — alphanumeric + underscore + hyphen only
        import re
        username = re.sub(r'[^a-zA-Z0-9_\-]', '_', username)[:64]

        if username not in self.sessions:
            session = UserSession(
                username    = username,
                storage_dir = self.storage_dir,
                memory_mode = self.memory_mode,
                remote_url  = self.remote_url,
            )
            self.sessions[username] = session

        return self.sessions[username]

    def disconnect(self, username):
        if username in self.sessions:
            self.sessions[username].disconnect()
            del self.sessions[username]

    def list_users(self):
        """List all known users in storage."""
        users_dir = os.path.join(self.storage_dir, 'users')
        if not os.path.exists(users_dir):
            return []
        return os.listdir(users_dir)
