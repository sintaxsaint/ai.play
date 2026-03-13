"""
ai.play call handler — on.connect(), on.disconnect(), on.silence(), on.keyword()
Phone call lifecycle event hooks for ai.voice(yes) deployments.
"""

import threading
import time

class CallHandler:
    def __init__(self, voice_engine=None):
        self.voice_engine  = voice_engine
        self.hooks         = {}    # event_name -> callable
        self.active        = False
        self.silence_timer = None
        self.silence_limit = None  # seconds
        self.keywords      = {}    # keyword -> callable
        self._last_speech  = time.time()

    def on(self, event, callback, param=None):
        """Register an event hook."""
        if event == 'silence' and param:
            self.silence_limit = int(param)
            self.hooks['silence'] = callback
        elif event == 'keyword' and param:
            self.keywords[param.lower()] = callback
        else:
            self.hooks[event] = callback

    def connect(self):
        """Call when a user connects."""
        self.active = True
        self._last_speech = time.time()
        if 'connect' in self.hooks:
            self.hooks['connect']()
        if self.silence_limit:
            self._start_silence_monitor()

    def disconnect(self):
        """Call when a user disconnects."""
        self.active = False
        if self.silence_timer:
            self.silence_timer.cancel()
        if 'disconnect' in self.hooks:
            self.hooks['disconnect']()

    def speech_received(self, text):
        """Call whenever speech input arrives — resets silence timer, checks keywords."""
        self._last_speech = time.time()

        # Check keywords
        lower = text.lower()
        for kw, hook in self.keywords.items():
            if kw in lower:
                hook()
                return  # keyword takes priority

    def _start_silence_monitor(self):
        def monitor():
            while self.active:
                elapsed = time.time() - self._last_speech
                if elapsed >= self.silence_limit:
                    if 'silence' in self.hooks:
                        self.hooks['silence']()
                    self._last_speech = time.time()  # reset after firing
                time.sleep(1)
        self.silence_timer = threading.Thread(target=monitor, daemon=True)
        self.silence_timer.start()

    def transfer(self, number):
        """Transfer the call to a number (stub — implement with Twilio etc)."""
        gateway = __import__('os').environ.get('AIPLAY_CALL_GATEWAY', '')
        if not gateway:
            print(f"[ai.play] Transfer to {number} — set AIPLAY_CALL_GATEWAY for real transfers")
        else:
            print(f"[ai.play] Transferring to {number}")
