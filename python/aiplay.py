#!/usr/bin/env python3
"""
ai.play — live compiler and runtime
Every run reads ALL source files fresh from disk.
Edit any .py or .aip file, run again — changes apply instantly, no rebuild needed.
"""

import sys
import os
import importlib.util

# ── find install directory ────────────────────────────────────────────────────
# sys.executable = path to aip.exe (frozen) or python (dev)
# For PyInstaller --onedir, all .py files sit next to the exe
# __file__ is wrong inside a frozen exe — always use sys.executable

if getattr(sys, 'frozen', False):
    # Running as compiled exe
    _HERE = os.path.dirname(os.path.abspath(sys.executable))
else:
    # Running as plain python aiplay.py
    _HERE = os.path.dirname(os.path.abspath(__file__))

# ── dynamic disk loader ───────────────────────────────────────────────────────

def _load(name):
    path = os.path.join(_HERE, f"{name}.py")
    if not os.path.exists(path):
        print(f"[ai.play] Missing module: {path}")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# Load all modules from disk
_load('ast_nodes')
_load('lexer')
_load('runtime')
_load('format_detector')
_load('memory_engine')
_load('skills_engine')
_load('module_engine')
_load('user_memory')
_load('intent_engine')
_load('voice_engine')
_load('video_engine')
_load('server')
_load('ui_server')
_load('notify_engine')
_load('vision_trainer')
_load('ai_yes')
_load('call_handler')
_load('interpreter')
_load('parser')

from lexer       import LexError
from parser      import ParseError
from interpreter import Interpreter
from interpreter import RuntimeError as AIPRuntimeError

# ─────────────────────────────────────────────────────────────────────────────

BANNER = """
 ai.play v0.6 — The language of AIs
 github.com/sintaxsaint/ai.play
"""

HELP = """Usage:
  aip <file.aip>         Run an ai.play program
  aip check <file.aip>   Syntax check without running
  aip help               Show this message

Files are live-compiled — edit and re-run instantly, no build step.
Drop updated .py files into the install directory to patch without reinstalling.
"""


def live_compile(path):
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    _load('ast_nodes')
    _load('lexer')
    _load('parser')
    from lexer  import Lexer
    from parser import Parser
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


def run_file(path):
    path = os.path.abspath(path)
    if not os.path.exists(path):
        print(f"[ai.play] Error: file not found: {path}")
        sys.exit(1)
    if not path.endswith('.aip'):
        print(f"[ai.play] Warning: {os.path.basename(path)} does not have .aip extension")

    program = live_compile(path)
    os.chdir(os.path.dirname(path))

    interp = Interpreter()
    interp.run(program)


def check_file(path):
    path = os.path.abspath(path)
    if not os.path.exists(path):
        print(f"[ai.play] Error: file not found: {path}")
        sys.exit(1)
    try:
        live_compile(path)
        print(f"[ai.play] {os.path.basename(path)} — syntax OK")
    except (LexError, ParseError) as e:
        print(f"[ai.play] Syntax error: {e}")
        sys.exit(1)


def main():
    args = sys.argv[1:]

    if not args or args[0] in ('help', '--help', '-h'):
        print(BANNER)
        print(HELP)
        sys.exit(0)

    if args[0] == 'check':
        if len(args) < 2:
            print("[ai.play] Error: check requires a file path")
            sys.exit(1)
        check_file(args[1])
        return

    path = args[0]

    try:
        run_file(path)
    except FileNotFoundError as e:
        print(f"[ai.play] Error: {e}")
        sys.exit(1)
    except LexError as e:
        print(f"[ai.play] Lex error: {e}")
        sys.exit(1)
    except ParseError as e:
        print(f"[ai.play] Parse error: {e}")
        sys.exit(1)
    except AIPRuntimeError as e:
        print(f"[ai.play] Runtime error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[ai.play] Stopped.")
        sys.exit(0)


if __name__ == '__main__':
    main()
