"""
ai.play interpreter — walks the AST and executes against the runtime.
Handles: multi-turn, memory (rule + generative), vision, diffusion,
         streaming, persona, file-type auto-detection, test.ui, out.in
"""

import os
import sys
import time

from ast_nodes import *
from runtime import (
    tokenize, Embedder,
    similaritize, respond,
    web_search, build_custom_model
)
from format_detector import load_any
from memory_engine   import make_memory

class RuntimeError(Exception):
    pass

class Interpreter:
    def __init__(self):
        self.env          = {}
        self.enabled      = False
        self.model_type   = 'factual'
        self.model_config = {}
        self.persona      = None
        self.caps         = {
            'web':       False,
            'memory':    False,
            'vision':    False,   # False | 'live' | 'normal'
            'diffusion': False,
            'video':     False,
            'voice':     False,
        }
        self.memory_mode  = None   # 'rule' | 'generative'
        self.memory       = None   # memory engine instance
        self.embedder     = Embedder()
        self.train_store  = []
        self.fitted       = False

        # UI / server
        self.ui_server    = None
        self.aip_server   = None

        # Streaming
        self.stream       = False

        # User-defined def blocks
        self.defs = {}

        # Skills engine
        self.skills_engine = None

        # Custom module engine
        self.module_engine = None

        # v0.6 engines
        self.notify_engine  = None
        self.vision_trainer = None
        self.live_vision    = None
        self.call_handler   = None
        self.ai_yes         = None
        self.fallback_msg   = None
        self.ai_name        = None
        self.ai_language    = 'english'
        self.ai_encrypt     = False
        self.ai_version     = None
        self.ai_creator     = None
        self.log_path       = None
        self.log_file       = None
        self.variables      = {}     # persistent variables across turns
        self.event_hooks    = {}     # label -> callable for on.detect

        # Current user session (set by server per request)
        self.current_user_session = None

        # Track last raw query for web + memory
        self._last_raw_query = ''
        self._encrypt_key = None
        self.artifacts_enabled = False
        self.output_deny   = False
        self.mcp_engine    = None
        self.sandbox       = None
        self.admin_engine  = None
        self._load_techniques()

    # ──────────────────────────────────────
    # ENTRY
    # ──────────────────────────────────────

    def _is(self, node, *names):
        """Match node by class name — works across module boundaries."""
        return type(node).__name__ in names

    def run(self, program):
        for stmt in program.stmts:
            self.exec_stmt(stmt)

    # ──────────────────────────────────────
    # STATEMENTS
    # ──────────────────────────────────────

    def exec_stmt(self, node):

        if self._is(node, 'AIEnable'):
            self.enabled = True
            print("[ai.play] Runtime enabled.")
            return

        if self._is(node, 'AIModel'):
            self._require_enabled(node)
            if node.name == 'custom':
                if not node.path:
                    raise RuntimeError("ai.model(custom) requires a path")
                self.model_config = build_custom_model(node.path)
                self.model_type   = 'custom'
                print(f"[ai.play] Custom model loaded from {node.path}")
            else:
                valid = ('fun', 'factual', 'thinking')
                if node.name not in valid:
                    raise RuntimeError(f"Unknown model: {node.name!r}. Choose from {valid} or custom")
                self.model_type = node.name
                print(f"[ai.play] Model: {node.name}")
            return

        if self._is(node, 'AIPersona'):
            self._require_enabled(node)
            self.persona = node.text
            print(f"[ai.play] Persona set.")
            return

        if self._is(node, 'AICapability'):
            self._require_enabled(node)
            cap, value = node.cap, node.value

            if cap == 'memory':
                # value can be True/False/yes/no or 'rule'/'generative'
                if value in (True, 'yes', 'rule'):
                    self.memory_mode = 'rule'
                    self.memory = make_memory('rule')
                    self.caps['memory'] = True
                    print(f"[ai.play] Memory: rule-based")
                elif value == 'generative':
                    self.memory_mode = 'generative'
                    self.memory = make_memory('generative')
                    self.caps['memory'] = True
                    print(f"[ai.play] Memory: generative (sintaxsaint architecture)")
                else:
                    self.caps['memory'] = False
                    self.memory = None
                    print(f"[ai.play] Memory: disabled")
                return

            if cap == 'vision':
                self.caps['vision'] = value  # 'live', 'normal', False
                state = value if value else 'disabled'
                print(f"[ai.play] Vision: {state}")
                return

            if cap == 'diffusion':
                self.caps['diffusion'] = value
                print(f"[ai.play] Diffusion: {'enabled' if value else 'disabled'}")
                return

            if cap == 'video':
                self.caps['video'] = value
                print(f"[ai.play] Video generation: {'enabled' if value else 'disabled'}")
                return

            if cap == 'voice':
                self.caps['voice'] = value
                print(f"[ai.play] Voice: {'enabled' if value else 'disabled'}")
                return

            if cap == 'web':
                self.caps['web'] = value
                print(f"[ai.play] Web: {'enabled' if value else 'disabled'}")
                return

            self.caps[cap] = value
            return

        if self._is(node, 'TrainEmbed'):
            self._require_enabled(node)
            print(f"[ai.play] Loading training data from {node.path}...")
            pairs, fmt = load_any(node.path)
            print(f"[ai.play] Format detected: {fmt}")

            if not pairs:
                print(f"[ai.play] Warning: no training pairs extracted.")
                return

            docs = [tokenize(p['question'] + ' ' + p['answer']) for p in pairs]
            self.embedder.fit(docs)

            self.train_store = []
            for p in pairs:
                vec = self.embedder.embed_raw(p['question'] + ' ' + p['answer'])
                self.train_store.append({
                    'question': p['question'],
                    'answer':   p['answer'],
                    'vec':      vec,
                })
            self.fitted = True
            print(f"[ai.play] Embedded {len(pairs)} training pairs.")
            return

        if self._is(node, 'AIMemory'):
            self._require_enabled(node)
            mode = node.mode
            if mode in ('rule', 'yes'):
                self.memory_mode = 'rule'
                self.memory = make_memory('rule')
                self.caps['memory'] = True
                print(f"[ai.play] Memory: rule-based")
            elif mode == 'generative':
                self.memory_mode = 'generative'
                self.memory = make_memory('generative')
                self.caps['memory'] = True
                print(f"[ai.play] Memory: generative (sintaxsaint architecture)")
            elif mode == 'upload':
                self.memory_mode = 'upload'
                self.memory = make_memory('generative')
                self.caps['memory'] = True
                print(f"[ai.play] Memory: upload mode")
            return

        if self._is(node, 'AISkills'):
            self._require_enabled(node)
            from skills_engine import SkillsEngine
            self.skills_engine = SkillsEngine(node.path)
            self.skills_engine.embed_all(self.embedder)
            return

        if self._is(node, 'TestUI'):
            self._require_enabled(node)
            val = getattr(node, 'value', None) or getattr(node, 'val', None)
            if val and val not in (False, 'no', 'No'):
                from ui_server import UIServer
                self.ui_server = UIServer()
                self.ui_server.start()
            return

        if self._is(node, 'OutIn'):
            self._require_enabled(node)
            from server import AIPServer
            self.aip_server = AIPServer(
                api_key     = node.key,
                user_mode   = node.user,
                storage_dir = node.storage or '.aiplay_users',
                remote_url  = node.upload,
                memory_mode = self.memory_mode or 'rule',
            )
            self.aip_server.start()
            return

        if self._is(node, 'Assign'):
            self.env[node.name] = self.eval_expr(node.expr)
            return

        if self._is(node, 'Print', 'PrintStmt'):
            # PrintStmt stores val as string, old Print stores expr as node
            if hasattr(node, 'expr'):
                val = self.eval_expr(node.expr)
            else:
                raw = node.val
                # Look up variable if it exists
                val = self.env.get(raw, raw)
            output = str(val)

            # Memory: store AI output
            if self.memory:
                self.memory.add('ai', output)

            # Stream or print
            if self.stream:
                for word in output.split():
                    print(word, end=' ', flush=True)
                    time.sleep(0.03)
                print()
            else:
                print(output)

            # Speak output if voice enabled
            if self.caps['voice'] and not self.ui_server and not self.aip_server:
                from voice_engine import speak
                speak(output)

            # Send to UI or server if active
            if self.ui_server:
                self.ui_server.send_output(output)
            if self.aip_server:
                self.aip_server.send_output(output)
            return

        if self._is(node, 'WhileLoop'):
            while True:
                try:
                    for stmt in node.body:
                        self.exec_stmt(stmt)
                except KeyboardInterrupt:
                    print("\n[ai.play] Loop stopped.")
                    break
            return

        # ─── ai.yes ───────────────────────────────────
        if self._is(node, 'AIYesNode'):
            self._require_enabled(node)
            from ai_yes import AIYes
            self.ai_yes = AIYes()
            config = self.ai_yes.activate(node.target)
            if config:
                # Auto-enable caps
                for cap in config.get('caps', []):
                    self.caps[cap] = True
                # Auto-load modules
                if self.module_engine is None and config.get('modules'):
                    from module_engine import ModuleEngine
                    self.module_engine = ModuleEngine()
                for mod in config.get('modules', []):
                    if self.module_engine:
                        self.module_engine.load(mod)
                # Set model mode
                self.model_mode = config.get('model_mode', 'factual')
                # Auto-enable artifacts if model supports file generation
                if config.get('artifacts', False):
                    self.artifacts_enabled = True
                    self._inject_artifact_pairs()
            return

        # ─── ai.notify ────────────────────────────────────
        if self._is(node, 'AINotify'):
            self._require_enabled(node)
            from notify_engine import NotifyEngine
            if self.notify_engine is None:
                self.notify_engine = NotifyEngine()
            self.notify_engine.register(node.channel, node.target)
            return

        # ─── ai.language ──────────────────────────────────
        if self._is(node, 'AILanguage'):
            self._require_enabled(node)
            self.ai_language = node.lang.lower()
            print(f"[ai.play] Language: {node.lang}")
            return

        if self._is(node, 'AITrain'):
            self._require_enabled(node)
            url = node.url
            print(f"[ai.play] Downloading training data from {url}...")
            try:
                import urllib.request, tempfile, os
                suffix = os.path.splitext(url.split('?')[0])[-1] or '.data'
                tmp = tempfile.mktemp(suffix=suffix)
                urllib.request.urlretrieve(url, tmp)
                from format_detector import load_any
                pairs, fmt = load_any(tmp)
                os.remove(tmp)
                if pairs:
                    docs = [tokenize(p['question'] + ' ' + p['answer']) for p in pairs]
                    self.embedder.fit(docs)
                    for p in pairs:
                        vec = self.embedder.embed_raw(p['question'] + ' ' + p['answer'])
                        self.train_store.append({'question': p['question'], 'answer': p['answer'], 'vec': vec})
                    self.fitted = True
                    print(f"[ai.play] Downloaded and embedded {len(pairs)} pairs ({fmt})")
                else:
                    print(f"[ai.play] Warning: no training pairs found in downloaded file")
            except Exception as e:
                print(f"[ai.play] Train download failed: {e}")
            return

        if self._is(node, 'AIName'):
            self._require_enabled(node)
            self.ai_name = node.name
            self._inject_identity_pairs()
            print(f"[ai.play] Name: {node.name}")
            return

        if self._is(node, 'AIVersion'):
            self._require_enabled(node)
            self.ai_version = node.version
            self._inject_identity_pairs()
            print(f"[ai.play] Version: {node.version}")
            return

        if self._is(node, 'AICreator'):
            self._require_enabled(node)
            self.ai_creator = node.creator
            self._inject_identity_pairs()
            print(f"[ai.play] Creator: {node.creator}")
            return

        if self._is(node, 'AISchedule'):
            self._require_enabled(node)
            import threading, time
            def _run_scheduled():
                while True:
                    # Parse interval or time
                    when = node.when
                    if ':' in when:
                        # Clock time e.g. 09:00
                        import datetime
                        h, m = map(int, when.split(':'))
                        now = datetime.datetime.now()
                        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                        if target < now:
                            target += datetime.timedelta(days=1)
                        time.sleep((target - datetime.datetime.now()).total_seconds())
                    else:
                        # Interval e.g. 30s, 5m, 1h
                        unit = when[-1]
                        val = int(when[:-1])
                        secs = {'s': 1, 'm': 60, 'h': 3600}.get(unit, 60) * val
                        time.sleep(secs)
                    if node.path:
                        try:
                            with open(node.path, 'r', encoding='utf-8') as f:
                                src = f.read()
                            from lexer import Lexer
                            from parser import Parser
                            prog = Parser(Lexer(src).tokenize()).parse()
                            sub = Interpreter()
                            sub.run(prog)
                        except Exception as e:
                            print(f"[ai.play] Schedule error: {e}")
            t = threading.Thread(target=_run_scheduled, daemon=True)
            t.start()
            print(f"[ai.play] Scheduled: {node.when}")
            return

        if self._is(node, 'AIEncrypt'):
            self._require_enabled(node)
            self._encrypt_key = node.key
            print(f"[ai.play] Memory encryption: enabled")
            return

        if self._is(node, 'TechniqueAdd'):
            self._require_enabled(node)
            name = node.name
            source = node.source or ''
            # If source is a file path, read it
            if source and os.path.exists(source):
                with open(source, 'r', encoding='utf-8') as f:
                    source = f.read()
            # Store as training pair
            q = f"how do I {name.replace('_', ' ')}"
            if self.embedder.vocabulary_:
                vec = self.embedder.embed_raw(q + ' ' + source)
                self.train_store.append({'question': q, 'answer': source, 'vec': vec})
            else:
                self.train_store.append({'question': q, 'answer': source, 'vec': {}})
            # Save to techniques file for persistence
            tech_file = os.path.join(os.getcwd(), '.aiplay_techniques.data')
            with open(tech_file, 'a', encoding='utf-8') as f:
                f.write(f"{q}:{source}\n")
            print(f"[ai.play] Technique saved: {name}")
            return

        if self._is(node, 'AIMcp'):
            self._require_enabled(node)
            from mcp_engine import MCPEngine
            if self.mcp_engine is None:
                self.mcp_engine = MCPEngine()
            conn = self.mcp_engine.connect(node.url)
            if conn:
                # Inject tool knowledge as training pairs
                pairs = self.mcp_engine.inject_training_pairs()
                for p in pairs:
                    self.train_store.append({'question': p['question'], 'answer': p['answer'], 'vec': {}})
            return

        if self._is(node, 'AIAdmin'):
            self._require_enabled(node)
            from admin_engine import AdminEngine
            self.admin_engine = AdminEngine(mode=str(node.mode))
            print(f"[ai.play] Admin access: {node.mode}")
            return

        if self._is(node, 'SandboxStart'):
            self._require_enabled(node)
            from sandbox_engine import SandboxEngine
            self.sandbox = SandboxEngine()
            ok = self.sandbox.start(str(node.mode))
            if not ok:
                print("[ai.play] Sandbox failed to start")
                self.sandbox = None
            return

        if self._is(node, 'SandboxInstall'):
            if not self.sandbox:
                print("[ai.play] No sandbox running — use sandbox.start() first")
                return
            result = self.sandbox.install(str(node.package))
            print(str(result))
            return

        if self._is(node, 'SandboxRun'):
            if not self.sandbox:
                print("[ai.play] No sandbox running — use sandbox.start() first")
                return
            result = self.sandbox.run(str(node.command))
            print(str(result))
            return

        if self._is(node, 'ArtifactsOn'):
            self._require_enabled(node)
            enabled = str(node.val).lower() not in ('no', 'false', '0')
            self.artifacts_enabled = enabled
            if enabled:
                self._inject_artifact_pairs()
            print(f"[ai.play] Artifacts: {'enabled' if enabled else 'disabled'}")
            return

        if self._is(node, 'OutputDeny'):
            self._require_enabled(node)
            self.output_deny = True
            print(f"[ai.play] Output deny: enabled (enforcement in v1)")
            return

        if self._is(node, 'AIFallback'):
            self._require_enabled(node)
            self.fallback_msg = node.message
            return

        # ─── ai.log ───────────────────────────────────────
        if self._is(node, 'AILog'):
            self._require_enabled(node)
            self.log_path = node.path
            import builtins
            self.log_file = builtins.open(node.path, 'a', encoding='utf-8')
            print(f"[ai.play] Logging to {node.path}")
            return

        # ─── vision.train ─────────────────────────────────
        if self._is(node, 'VisionTrain'):
            self._require_enabled(node)
            from vision_trainer import VisionTrainer
            if self.vision_trainer is None:
                self.vision_trainer = VisionTrainer()
            self.vision_trainer.train(node.label, node.path)
            return

        # ─── on.event ─────────────────────────────────────
        if self._is(node, 'OnEvent'):
            self._require_enabled(node)
            body = node.body

            def make_hook(b):
                def hook(*args):
                    for s in b:
                        self.exec_stmt(s)
                return hook

            h = make_hook(body)

            if node.event in ('connect', 'disconnect'):
                from call_handler import CallHandler
                if self.call_handler is None:
                    self.call_handler = CallHandler()
                self.call_handler.on(node.event, h)

            elif node.event == 'silence':
                from call_handler import CallHandler
                if self.call_handler is None:
                    self.call_handler = CallHandler()
                self.call_handler.on('silence', h, param=node.param)

            elif node.event == 'keyword':
                from call_handler import CallHandler
                if self.call_handler is None:
                    self.call_handler = CallHandler()
                self.call_handler.on('keyword', h, param=node.param)

            elif node.event == 'detect':
                # Register vision detection hook
                self.event_hooks[node.param or node.event] = h
                if self.vision_trainer and self.caps.get('vision'):
                    from vision_trainer import LiveVisionLoop
                    if self.live_vision is None:
                        self.live_vision = LiveVisionLoop(
                            self.vision_trainer,
                            self.event_hooks,
                            self.notify_engine,
                        )
                        self.live_vision.start()
            return

        # ─── notify.channel ───────────────────────────────
        if self._is(node, 'NotifyCall'):
            if self.notify_engine:
                self.notify_engine.send(node.channel, node.message, node.attachment)
            else:
                print(f"[ai.play] notify.{node.channel}: no ai.notify() configured")
            return

        # ─── log() ────────────────────────────────────────
        if self._is(node, 'LogCall'):
            val = self.variables.get(node.value, node.value)
            msg = str(val)
            if self.log_file:
                import time
                self.log_file.write("[" + time.strftime("%Y-%m-%d %H:%M:%S") + "] " + msg + chr(10))
                self.log_file.flush()
            else:
                print(f"[log] {msg}")
            return

        # ─── if / else ────────────────────────────────────
        if self._is(node, 'IfStmt'):
            if self._eval_condition(node.condition):
                for s in node.body:
                    self.exec_stmt(s)
            else:
                for s in node.else_body:
                    self.exec_stmt(s)
            return

        # ─── ai.transfer ──────────────────────────────────
        if self._is(node, 'TransferCall'):
            if self.call_handler:
                self.call_handler.transfer(node.number)
            return

        if self._is(node, 'CustomModule'):
            self._require_enabled(node)
            from module_engine import ModuleEngine
            if self.module_engine is None:
                self.module_engine = ModuleEngine()
            loaded = self.module_engine.load(node.name)
            if loaded:
                self.module_engine.embed_all(self.embedder)
            return

        if self._is(node, 'MakeModule'):
            from module_engine import create_module_template
            create_module_template(node.name)
            return

        if self._is(node, 'DefBlock'):
            self.defs[node.name] = node.body
            return

        if self._is(node, 'CallDef'):
            if node.name not in self.defs:
                raise RuntimeError(f"Undefined def: {node.name!r}. Define it with def {node.name}(): ...")
            for stmt in self.defs[node.name]:
                self.exec_stmt(stmt)
            return

        raise RuntimeError(f"Unknown statement: {type(node).__name__}")

    # ──────────────────────────────────────
    # EXPRESSIONS
    # ──────────────────────────────────────

    def eval_expr(self, node):

        if self._is(node, 'InputExpr'):
            # If server is running, get input from there
            if self.aip_server:
                text = self.aip_server.get_input()
                # Load per-user memory from server session
                session = self.aip_server.get_active_session()
                if session:
                    self.current_user_session = session
            elif self.ui_server:
                text = self.ui_server.get_input()
            elif self.caps['voice']:
                from voice_engine import listen
                text = listen()
            else:
                text = input()

            # Handle technique saving command
            if text.lower().startswith('save this as a technique') or 'save as technique' in text.lower():
                import re
                m = re.search(r'technique[:\s]+(.+)', text, re.IGNORECASE)
                name = m.group(1).strip().replace(' ', '_') if m else 'unnamed'
                last_response = self.env.get('Response', '')
                if last_response:
                    q = f"how do I {name.replace('_', ' ')}"
                    tech_file = os.path.join(os.getcwd(), '.aiplay_techniques.data')
                    with open(tech_file, 'a', encoding='utf-8') as f:
                        f.write(f"{q}:{last_response}\n")
                    self.train_store.append({'question': q, 'answer': last_response, 'vec': {}})
                    return f"Technique '{name}' saved."
                return "Nothing to save yet."

            self._last_raw_query = text

            # Voice input — if voice enabled, listen instead of type
            # (already handled above by listen(), text is the transcription)

            # Vision: auto-detect image input
            if self.caps['vision'] and self._is_image_path(text):
                return self._vision_tokenize(text)

            # Memory: store user input
            if self.current_user_session:
                self.current_user_session.add('user', text)
            elif self.memory:
                self.memory.add('user', text)

            return text

        if self._is(node, 'TokenizeExpr'):
            val = self.eval_expr(node.inner)
            # Vision: if val looks like an image path, convert pixels to tokens
            if self.caps['vision'] and isinstance(val, str) and self._is_image_path(val):
                return self._vision_tokenize(val)
            return tokenize(str(val))

        if self._is(node, 'EmbedExpr'):
            inner = self.eval_expr(node.inner)
            # Pass through context bundles from Similaritize
            if isinstance(inner, list) and len(inner) > 0 and isinstance(inner[0], tuple):
                return inner
            if isinstance(inner, list):
                return self.embedder.embed(inner)
            if isinstance(inner, dict):
                return inner
            return self.embedder.embed_raw(str(inner))

        if self._is(node, 'SimilarizeExpr'):
            inner = self.eval_expr(node.inner)

            # Embed if needed
            if isinstance(inner, list) and (not inner or not isinstance(inner[0], tuple)):
                query_vec = self.embedder.embed(inner)
            elif isinstance(inner, dict):
                query_vec = inner
            else:
                query_vec = self.embedder.embed_raw(str(inner))

            store = list(self.train_store)

            # Modules: inject relevant module pairs into store
            if self.module_engine:
                mod_store, output_type = self.module_engine.get_store(self._last_raw_query)
                if mod_store:
                    store = mod_store + store
                    self._active_output_type = output_type

            # Skills: inject relevant skill pairs into store
            if self.skills_engine:
                skill_store, skill_tone, skill_name = self.skills_engine.get_skill_store(
                    self._last_raw_query
                )
                if skill_store:
                    store = skill_store + store  # skill pairs take priority
                    self._active_skill_tone = skill_tone
                    if skill_name:
                        pass  # could log: using skill X
                else:
                    self._active_skill_tone = ''

            # Web augmentation
            if self.caps.get('web') and self._last_raw_query:
                web_results = web_search(self._last_raw_query)
                for item in web_results:
                    vec = self.embedder.embed_raw(item['question'] + ' ' + item['answer'])
                    store.append({'question': item['question'], 'answer': item['answer'], 'vec': vec})

            # Memory augmentation — use per-user session memory if server is running
            active_memory = None
            if self.current_user_session:
                active_memory = self.current_user_session
            elif self.memory:
                active_memory = self.memory

            # Memory augmentation — inject relevant memory into store
            if active_memory and self._last_raw_query:
                ctx = self.memory.get_context(self._last_raw_query)
                mem_text = self.memory.format_for_context(ctx)
                if mem_text:
                    vec = self.embedder.embed_raw(mem_text)
                    store.insert(0, {'question': self._last_raw_query, 'answer': mem_text, 'vec': vec})


            # Vision: if enabled, Similaritize also prompts for image context
            if self.caps['vision'] == 'live':
                cam_tokens = self._capture_live_frame()
                if cam_tokens:
                    cam_vec = self.embedder.embed(cam_tokens)
                    store.insert(0, {
                        'question': self._last_raw_query,
                        'answer': 'visual context: ' + ' '.join(cam_tokens[:30]),
                        'vec': cam_vec,
                    })

            top_k = int(self.model_config.get('top_k', 5)) if self.model_type == 'custom' else 5
            return similaritize(query_vec, store, top_k=top_k)

        if self._is(node, 'RespondExpr'):
            context = self.eval_expr(node.inner)

            # ── Intent analysis ───────────────────────────────────────
            from intent_engine import analyse
            intent = analyse(self._last_raw_query, context, self.caps)

            # If a hard intent was detected but capability is missing,
            # return the missing message instead of a text response
            if intent.blocked:
                msg = intent.missing_message()
                if msg:
                    return msg

            # Persona injection + active skill tone
            skill_tone = getattr(self, '_active_skill_tone', '')
            persona_parts = []
            if self.persona:
                persona_parts.append(self.persona)
            if skill_tone:
                persona_parts.append(f"Tone: {skill_tone}")
            persona_prefix = '\n'.join(persona_parts)

            result = respond(context, model_type=self.model_type, persona=persona_prefix)

            outputs = [result]

            # Intent-driven modality actions
            if intent.wants('diffusion'):
                img_path = self._diffuse(result)
                if img_path:
                    outputs.append(f"[Image generated: {img_path}]")

            if intent.wants('video'):
                vid_path = self._generate_video(self._last_raw_query or result)
                if vid_path:
                    outputs.append(f"[Video generated: {vid_path}]")

            if intent.wants('web') and not self.caps.get('web'):
                pass  # already handled in Similaritize

            final = '\n'.join(outputs)
            # Execute any sandbox or admin commands in the response
            final = self._handle_action_commands(final)
            # Translate if language set and not english
            if self.ai_language not in ('english', 'en', ''):
                try:
                    import urllib.request, urllib.parse, json as _json
                    lang_map = {
                        'french': 'fr', 'spanish': 'es', 'german': 'de',
                        'italian': 'it', 'portuguese': 'pt', 'dutch': 'nl',
                        'japanese': 'ja', 'chinese': 'zh', 'korean': 'ko',
                        'arabic': 'ar', 'russian': 'ru', 'hindi': 'hi',
                        'auto': 'auto'
                    }
                    target = lang_map.get(self.ai_language, self.ai_language[:2])
                    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={target}&dt=t&q={urllib.parse.quote(final)}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as r:
                        data = _json.loads(r.read())
                    translated = ''.join(part[0] for part in data[0] if part[0])
                    final = translated
                except Exception:
                    pass  # Fall back to English if translation fails
            return final

        if self._is(node, 'VarRef'):
            if node.name not in self.env:
                raise RuntimeError(f"Undefined variable: {node.name!r}")
            val = self.env[node.name]
            if isinstance(val, str):
                self._last_raw_query = val
            return val

        if self._is(node, 'StringLit'):
            return node.value

        if self._is(node, 'NumberLit'):
            return node.value

        if self._is(node, 'PathLit'):
            return node.value

        if self._is(node, 'Literal'):
            # If the value is a string that matches a variable, return the variable
            if isinstance(node.value, str) and node.value in self.env:
                val = self.env[node.value]
                if isinstance(val, str):
                    self._last_raw_query = val
                return val
            return node.value

        raise RuntimeError(f"Unknown expression: {type(node).__name__}")

    # ──────────────────────────────────────
    # VISION
    # ──────────────────────────────────────

    def _is_image_path(self, text):
        return isinstance(text, str) and any(
            text.lower().endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')
        )

    def _vision_tokenize(self, path_or_data):
        """
        Convert an image to pseudo-tokens (colour region descriptors).
        Turns pixel data into human-readable 'words' the rest of the pipeline can use.
        """
        try:
            import struct, zlib

            if isinstance(path_or_data, str) and os.path.exists(path_or_data):
                with open(path_or_data, 'rb') as f:
                    data = f.read()
            else:
                return tokenize(str(path_or_data))

            # Sample pixels from the image — simple pure-Python approach
            tokens = []

            # Try to use PIL if available (better quality)
            try:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(data)).convert('RGB').resize((32, 32))
                pixels = list(img.getdata())
                tokens = self._pixels_to_tokens(pixels, 32, 32)
            except ImportError:
                # Fallback: describe the file without PIL
                tokens = [f'image_{len(data)}bytes', 'visual_input']

            return tokens
        except Exception:
            return ['image', 'visual_input']

    def _pixels_to_tokens(self, pixels, w, h):
        """Convert pixel grid to descriptive tokens the pipeline can embed."""
        tokens = []
        # Divide into 4x4 grid of regions
        region_size_x = w // 4
        region_size_y = h // 4
        colours = {
            'red':    (200,80,80),
            'green':  (80,200,80),
            'blue':   (80,80,200),
            'yellow': (200,200,80),
            'white':  (220,220,220),
            'black':  (40,40,40),
            'grey':   (128,128,128),
            'orange': (220,140,40),
            'purple': (140,80,200),
            'pink':   (220,120,180),
        }

        def nearest_colour(r, g, b):
            best, best_d = 'grey', 9e9
            for name, (cr, cg, cb) in colours.items():
                d = (r-cr)**2 + (g-cg)**2 + (b-cb)**2
                if d < best_d:
                    best, best_d = name, d
            bright = (r+g+b) / 3
            if bright > 200: return 'bright_' + best
            if bright < 60:  return 'dark_' + best
            return best

        for ry in range(4):
            for rx in range(4):
                r_total = g_total = b_total = count = 0
                for y in range(ry*region_size_y, (ry+1)*region_size_y):
                    for x in range(rx*region_size_x, (rx+1)*region_size_x):
                        idx = y * w + x
                        if idx < len(pixels):
                            pr, pg, pb = pixels[idx][:3]
                            r_total += pr; g_total += pg; b_total += pb; count += 1
                if count:
                    col = nearest_colour(r_total//count, g_total//count, b_total//count)
                    tokens.append(f'region_{rx}_{ry}_{col}')

        # Overall brightness
        all_r = sum(p[0] for p in pixels) / len(pixels)
        all_g = sum(p[1] for p in pixels) / len(pixels)
        all_b = sum(p[2] for p in pixels) / len(pixels)
        tokens.append(f'avg_{nearest_colour(int(all_r), int(all_g), int(all_b))}')
        tokens.append('image_input')
        return tokens

    def _capture_live_frame(self):
        """Capture a frame from the webcam and tokenize it."""
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            if ret:
                import tempfile, os
                tmp = tempfile.mktemp(suffix='.jpg')
                cv2.imwrite(tmp, frame)
                tokens = self._vision_tokenize(tmp)
                os.remove(tmp)
                return tokens
        except Exception:
            pass
        return []

    # ──────────────────────────────────────
    # DIFFUSION
    # ──────────────────────────────────────

    def _diffuse(self, prompt):
        """
        Generate an image from a text prompt.
        Uses local diffusion if available, otherwise stubs.
        """
        try:
            # Try diffusers (local, offline)
            from diffusers import StableDiffusionPipeline
            import torch
            pipe = StableDiffusionPipeline.from_pretrained(
                'runwayml/stable-diffusion-v1-5',
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            pipe = pipe.to('cuda' if torch.cuda.is_available() else 'cpu')
            image = pipe(prompt).images[0]
            path = f'aiplay_output_{int(time.time())}.png'
            image.save(path)
            return path
        except ImportError:
            # No diffusers installed — note it
            print(f"[ai.play] Diffusion: install 'diffusers' and 'torch' for image generation")
            return None
        except Exception as e:
            print(f"[ai.play] Diffusion error: {e}")
            return None

    # ──────────────────────────────────────
    # VIDEO
    # ──────────────────────────────────────

    def _generate_video(self, prompt):
        from video_engine import generate_video
        return generate_video(prompt)

    # ──────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────

    def _load_techniques(self):
        """Load saved techniques from disk on startup."""
        tech_file = os.path.join(os.getcwd(), '.aiplay_techniques.data')
        if os.path.exists(tech_file):
            try:
                with open(tech_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if ':' in line:
                            q, _, a = line.partition(':')
                            self.train_store.append({'question': q.strip(), 'answer': a.strip(), 'vec': {}})
            except Exception:
                pass

    def _handle_action_commands(self, text):
        """Parse and execute sandbox/admin action tags in AI responses."""
        import re

        # <run>command</run> — run in sandbox
        def exec_sandbox(m):
            cmd = m.group(1).strip()
            if self.sandbox and self.sandbox.is_ready():
                result = self.sandbox.run(cmd)
                return f"```\n$ {cmd}\n{result}\n```"
            elif self.admin_engine:
                result = self.admin_engine.run(cmd, reason="AI wants to run a command")
                return f"```\n$ {cmd}\n{result}\n```"
            return m.group(0)

        # <install>package</install> — install in sandbox
        def exec_install(m):
            pkg = m.group(1).strip()
            if self.sandbox and self.sandbox.is_ready():
                result = self.sandbox.install(pkg)
                return f"Installing {pkg}... {'done' if result.success else 'failed'}"
            elif self.admin_engine:
                result = self.admin_engine.install(pkg)
                return f"Installing {pkg}... {'done' if result.success else 'failed'}"
            return m.group(0)

        # <python>code</python> — run Python in sandbox
        def exec_python(m):
            code = m.group(1).strip()
            if self.sandbox and self.sandbox.is_ready():
                result = self.sandbox.run_python(code)
                return f"```\n{result}\n```"
            return m.group(0)

        text = re.sub(r'<run>(.*?)</run>', exec_sandbox, text, flags=re.DOTALL)
        text = re.sub(r'<install>(.*?)</install>', exec_install, text, flags=re.DOTALL)
        text = re.sub(r'<python>(.*?)</python>', exec_python, text, flags=re.DOTALL)
        return text

    def _translate(self, text, target_lang):
        """Translate text using Google Translate free endpoint."""
        try:
            import urllib.request, urllib.parse, json
            lang_codes = {
                'french': 'fr', 'spanish': 'es', 'german': 'de', 'italian': 'it',
                'portuguese': 'pt', 'dutch': 'nl', 'russian': 'ru', 'japanese': 'ja',
                'chinese': 'zh', 'korean': 'ko', 'arabic': 'ar', 'hindi': 'hi',
                'polish': 'pl', 'swedish': 'sv', 'norwegian': 'no', 'danish': 'da',
                'finnish': 'fi', 'turkish': 'tr', 'greek': 'el', 'czech': 'cs',
            }
            code = lang_codes.get(target_lang.lower(), target_lang[:2])
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl={code}&dt=t&q={urllib.parse.quote(text)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
            return ''.join(item[0] for item in data[0] if item[0])
        except Exception:
            return text  # fallback to English if translation fails

    def _inject_artifact_pairs(self):
        """Inject artifact syntax knowledge so the AI knows how to produce files."""
        pairs = [
            ("create a python script", '<artifact type="py" name="script.py">\ndef hello():\n    print("Hello!")\nhello()\n</artifact>'),
            ("make a python file", '<artifact type="py" name="output.py">\n# Your Python code here\nprint("Hello!")\n</artifact>'),
            ("write a html page", '<artifact type="html" name="page.html">\n<!DOCTYPE html>\n<html>\n<body>\n<h1>Hello</h1>\n</body>\n</html>\n</artifact>'),
            ("create a text file", '<artifact type="txt" name="output.txt">\nYour text content here\n</artifact>'),
            ("make a javascript file", '<artifact type="js" name="script.js">\nconsole.log("Hello!");\n</artifact>'),
            ("create a json file", '<artifact type="json" name="data.json">\n{"key": "value"}\n</artifact>'),
            ("write a bash script", '<artifact type="sh" name="script.sh">\n#!/bin/bash\necho "Hello!"\n</artifact>'),
            ("make a css file", '<artifact type="css" name="style.css">\nbody { font-family: sans-serif; }\n</artifact>'),
            ("how do I create a file as an artifact", 'Wrap the file content in an artifact tag like this: <artifact type="py" name="myfile.py">code here</artifact>'),
            ("what file types can you make", 'I can create artifacts of any type: .py .html .js .css .json .txt .sh .md and more. Just ask me to create a file.'),
        ]
        for q, a in pairs:
            if self.embedder.vocabulary_:
                vec = self.embedder.embed_raw(q + ' ' + a)
                self.train_store = [p for p in self.train_store if p['question'] != q]
                self.train_store.append({'question': q, 'answer': a, 'vec': vec})
            else:
                self.train_store.append({'question': q, 'answer': a, 'vec': {}})

    def _inject_identity_pairs(self):
        """Inject identity knowledge into train_store so the AI knows who it is."""
        name    = self.ai_name    or 'an AI assistant'
        version = self.ai_version or '1.0'
        creator = self.ai_creator or 'an independent developer'

        pairs = [
            (f"what is your name",           f"My name is {name}."),
            (f"who are you",                  f"I am {name}, an AI assistant."),
            (f"what are you called",          f"I am called {name}."),
            (f"what version are you",         f"I am version {version}."),
            (f"who made you",                 f"I was created by {creator}."),
            (f"who created you",              f"I was created by {creator}."),
            (f"who built you",                f"I was built by {creator}."),
            (f"what type of ai are you",      f"I am {name}, a local AI assistant built by {creator}. I run entirely on your device."),
            (f"are you chatgpt",              f"No, I am {name}. I run locally on your device, not in the cloud."),
            (f"are you an ai",                f"Yes, I am {name}, an AI assistant created by {creator}."),
            (f"tell me about yourself",       f"I am {name} version {version}, created by {creator}. I run entirely on your device with no data leaving your machine."),
        ]

        for q, a in pairs:
            if not self.embedder.vocabulary_:
                # Embedder not fitted yet — store raw for later
                self.train_store.append({'question': q, 'answer': a, 'vec': {}})
            else:
                vec = self.embedder.embed_raw(q + ' ' + a)
                # Remove any existing identity pair with same question
                self.train_store = [p for p in self.train_store if p['question'] != q]
                self.train_store.append({'question': q, 'answer': a, 'vec': vec})

    def _eval_condition(self, condition):
        """Evaluate a simple condition string."""
        import re
        cond = condition.strip()

        # Variable contains string: Input contains "hello"
        m = re.match(r'(\w+)\s+contains\s+"?([^"]+)"?', cond, re.IGNORECASE)
        if m:
            var_name, substring = m.group(1), m.group(2)
            val = str(self.variables.get(var_name, ''))
            return substring.lower() in val.lower()

        # Variable equals value: Input == "hello"
        m = re.match(r'(\w+)\s*==\s*"?([^"]+)"?', cond)
        if m:
            var_name, value = m.group(1), m.group(2)
            val = str(self.variables.get(var_name, ''))
            return val.strip().lower() == value.strip().lower()

        # Variable not equals: Input != "hello"
        m = re.match(r'(\w+)\s*!=\s*"?([^"]+)"?', cond)
        if m:
            var_name, value = m.group(1), m.group(2)
            val = str(self.variables.get(var_name, ''))
            return val.strip().lower() != value.strip().lower()

        # Numeric comparison: count > 5
        m = re.match(r'(\w+)\s*([><=!]+)\s*(\d+)', cond)
        if m:
            var_name, op, num = m.group(1), m.group(2), int(m.group(3))
            val = self.variables.get(var_name, 0)
            try:
                val = float(val)
                if op == '>':  return val > num
                if op == '<':  return val < num
                if op == '>=': return val >= num
                if op == '<=': return val <= num
                if op == '==': return val == num
                if op == '!=': return val != num
            except Exception:
                pass

        # yes/no/true/false literals
        if cond.lower() in ('yes', 'true', '1'):
            return True
        if cond.lower() in ('no', 'false', '0'):
            return False

        # Variable alone — truthy check
        if cond in self.variables:
            return bool(self.variables[cond])

        return False

    def _require_enabled(self, node):
        if not self.enabled:
            raise RuntimeError(
                f"{type(node).__name__} called before ai.enable(). "
                "Add ai.enable() at the top of your .aip file."
            )
