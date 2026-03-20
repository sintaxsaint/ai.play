"""
ai.play — The language of AIs
"""
__version__ = '0.7.0'

def run(source: str):
    """Run ai.play source code from a Python string. For Colab and scripting use."""
    import os, sys, tempfile
    tmp = tempfile.mktemp(suffix='.aip')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(source)
    try:
        from aiplay.aiplay import run_file
        run_file(tmp)
    finally:
        os.remove(tmp)
