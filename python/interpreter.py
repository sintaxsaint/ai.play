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
        self.log_path       = None
        self.log_file       = None
        self.variables      = {}     # persistent variables across turns
        self.event_hooks    = {}     # label -> callable for on.detect

        # Current user session (set by server per request)
        self.current_user_session = None

        # Track last raw query for web + memory
        self._last_raw_query = ''

    # ──────────────────────────────────────
    # ENTRY
    # ──────────────────────────────────────

    def run(self, program):
        for stmt in program.stmts:
            self.exec_stmt(stmt)

    # ──────────────────────────────────────
    # STATEMENTS
    # ──────────────────────────────────────

    def exec_stmt(self, node):

        if isinstance(node, AIEnable):
            self.enabled = True
            print("[ai.play] Runtime enabled.")
            return

        if isinstance(node, AIModel):
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

        if isinstance(node, AIPersona):
            self._require_enabled(node)
            self.persona = node.text
            print(f"[ai.play] Persona set.")
            return

        if isinstance(node, AICapability):
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

        if isinstance(node, TrainEmbed):
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

        if isinstance(node, AISkills):
            self._require_enabled(node)
            from skills_engine import SkillsEngine
            self.skills_engine = SkillsEngine(node.path)
            self.skills_engine.embed_all(self.embedder)
            return

        if isinstance(node, TestUI):
            self._require_enabled(node)
            if node.value:
                from ui_server import UIServer
                self.ui_server = UIServer()
                self.ui_server.start()
            return

        if isinstance(node, OutIn):
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

        if isinstance(node, Assign):
            self.env[node.name] = self.eval_expr(node.expr)
            return

        if isinstance(node, Print):
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

        if isinstance(node, WhileLoop):
            while True:
                try:
                    for stmt in node.body:
                        self.exec_stmt(stmt)
                except KeyboardInterrupt:
                    print("\n[ai.play] Loop stopped.")
                    break
            return

        # ─── ai.yes ───────────────────────────────────
        if isinstance(node, AIYesNode):
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
            return

        # ─── ai.notify ────────────────────────────────────
        if isinstance(node, AINotify):
            self._require_enabled(node)
            from notify_engine import NotifyEngine
            if self.notify_engine is None:
                self.notify_engine = NotifyEngine()
            self.notify_engine.register(node.channel, node.target)
            return

        # ─── ai.fallback ──────────────────────────────────
        if isinstance(node, AIFallback):
            self._require_enabled(node)
            self.fallback_msg = node.message
            return

        # ─── ai.log ───────────────────────────────────────
        if isinstance(node, AILog):
            self._require_enabled(node)
            self.log_path = node.path
            import builtins
            self.log_file = builtins.open(node.path, 'a', encoding='utf-8')
            print(f"[ai.play] Logging to {node.path}")
            return

        # ─── vision.train ─────────────────────────────────
        if isinstance(node, VisionTrain):
            self._require_enabled(node)
            from vision_trainer import VisionTrainer
            if self.vision_trainer is None:
                self.vision_trainer = VisionTrainer()
            self.vision_trainer.train(node.label, node.path)
            return

        # ─── on.event ─────────────────────────────────────
        if isinstance(node, OnEvent):
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
        if isinstance(node, NotifyCall):
            if self.notify_engine:
                self.notify_engine.send(node.channel, node.message, node.attachment)
            else:
                print(f"[ai.play] notify.{node.channel}: no ai.notify() configured")
            return

        # ─── log() ────────────────────────────────────────
        if isinstance(node, LogCall):
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
        if isinstance(node, IfStmt):
            if self._eval_condition(node.condition):
                for s in node.body:
                    self.exec_stmt(s)
            else:
                for s in node.else_body:
                    self.exec_stmt(s)
            return

        # ─── ai.transfer ──────────────────────────────────
        if isinstance(node, TransferCall):
            if self.call_handler:
                self.call_handler.transfer(node.number)
            return

        if isinstance(node, CustomModule):
            self._require_enabled(node)
            from module_engine import ModuleEngine
            if self.module_engine is None:
                self.module_engine = ModuleEngine()
            loaded = self.module_engine.load(node.name)
            if loaded:
                self.module_engine.embed_all(self.embedder)
            return

        if isinstance(node, MakeModule):
            from module_engine import create_module_template
            create_module_template(node.name)
            return

        if isinstance(node, DefBlock):
            self.defs[node.name] = node.body
            return

        if isinstance(node, CallDef):
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

        if isinstance(node, InputExpr):
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

        if isinstance(node, TokenizeExpr):
            val = self.eval_expr(node.expr)
            # Vision: if val looks like an image path, convert pixels to tokens
            if self.caps['vision'] and isinstance(val, str) and self._is_image_path(val):
                return self._vision_tokenize(val)
            return tokenize(str(val))

        if isinstance(node, EmbedExpr):
            inner = self.eval_expr(node.expr)
            # Pass through context bundles from Similaritize
            if isinstance(inner, list) and len(inner) > 0 and isinstance(inner[0], tuple):
                return inner
            if isinstance(inner, list):
                return self.embedder.embed(inner)
            if isinstance(inner, dict):
                return inner
            return self.embedder.embed_raw(str(inner))

        if isinstance(node, SimilarizeExpr):
            inner = self.eval_expr(node.expr)

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

        if isinstance(node, RespondExpr):
            context = self.eval_expr(node.expr)

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

            return '\n'.join(outputs)

        if isinstance(node, VarRef):
            if node.name not in self.env:
                raise RuntimeError(f"Undefined variable: {node.name!r}")
            val = self.env[node.name]
            if isinstance(val, str):
                self._last_raw_query = val
            return val

        if isinstance(node, StringLit):
            return node.value

        if isinstance(node, NumberLit):
            return node.value

        if isinstance(node, PathLit):
            return node.value

        if isinstance(node, Literal):
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
