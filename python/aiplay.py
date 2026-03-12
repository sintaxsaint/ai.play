#!/usr/bin/env python3
"""
ai.play — live compiler and runtime
Every run reads the source fresh. Edit your .aip file, run it, changes apply instantly.
"""

import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from lexer       import Lexer,       LexError
from parser      import Parser,      ParseError
from interpreter import Interpreter, RuntimeError as AIPRuntimeError

BANNER = """
 ai.play v0.1 — The language of AIs
"""

HELP = """Usage:
  aip <file.aip>         Run an ai.play program
  aip check <file.aip>   Syntax check without running
  aip help               Show this message

Files are live-compiled — edit and re-run instantly, no build step.
"""


def live_compile(path):
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
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
