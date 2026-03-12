"""
ai.play format detector — auto-detects training file format and extracts pairs.
Tries known layouts first, falls back to flat knowledge base.
"""

import os
import re
import json

# ─────────────────────────────────────────
# LAYOUT DATABASE
# Each entry: {'name', 'detect', 'extract'}
# detect(content) -> True/False
# extract(content, path) -> list of {'question': str, 'answer': str}
# ─────────────────────────────────────────

def _extract_flat(text):
    """Turn flat text into overlapping chunks as a knowledge base."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    pairs = []
    for i, s in enumerate(sentences):
        context = ' '.join(sentences[max(0,i-1):i+2])
        pairs.append({'question': s, 'answer': context})
    return pairs

def _extract_aiplay_data(content, path):
    pairs = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('Training.data') or line.startswith('#'):
            continue
        if ':' in line:
            q, _, a = line.partition(':')
            q, a = q.strip(), a.strip()
            if q and a:
                pairs.append({'question': q, 'answer': a})
    return pairs

def _extract_openai_jsonl(content, path):
    pairs = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            # {"prompt": "...", "completion": "..."}
            if 'prompt' in obj and 'completion' in obj:
                pairs.append({'question': obj['prompt'].strip(), 'answer': obj['completion'].strip()})
            # {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}
            elif 'messages' in obj:
                msgs = obj['messages']
                for i, m in enumerate(msgs):
                    if m.get('role') == 'user' and i+1 < len(msgs) and msgs[i+1].get('role') == 'assistant':
                        pairs.append({'question': m['content'], 'answer': msgs[i+1]['content']})
        except Exception:
            continue
    return pairs

def _extract_json_pairs(content, path):
    pairs = []
    try:
        data = json.loads(content)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    q_keys = [k for k in item if k.lower() in ('question','q','input','prompt','user')]
                    a_keys = [k for k in item if k.lower() in ('answer','a','output','response','completion','assistant')]
                    if q_keys and a_keys:
                        pairs.append({'question': str(item[q_keys[0]]), 'answer': str(item[a_keys[0]])})
                    else:
                        vals = list(item.values())
                        if len(vals) >= 2:
                            pairs.append({'question': str(vals[0]), 'answer': str(vals[1])})
        elif isinstance(data, dict):
            for k, v in data.items():
                pairs.append({'question': str(k), 'answer': str(v)})
    except Exception:
        pass
    return pairs

def _extract_csv(content, path):
    pairs = []
    try:
        import csv, io
        reader = csv.DictReader(io.StringIO(content))
        fields = reader.fieldnames or []
        q_col = next((f for f in fields if f.lower() in ('question','q','input','prompt','user','term')), None)
        a_col = next((f for f in fields if f.lower() in ('answer','a','output','response','definition','desc','description')), None)
        if q_col and a_col:
            for row in reader:
                q, a = row.get(q_col,'').strip(), row.get(a_col,'').strip()
                if q and a:
                    pairs.append({'question': q, 'answer': a})
        else:
            # Use first two columns
            for row in reader:
                vals = list(row.values())
                if len(vals) >= 2 and vals[0] and vals[1]:
                    pairs.append({'question': vals[0].strip(), 'answer': vals[1].strip()})
    except Exception:
        pass
    return pairs

def _extract_txt(content, path):
    # Try question:answer lines first
    pairs = _extract_aiplay_data(content, path)
    if pairs:
        return pairs
    # Try Q: / A: format
    pairs = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r'^[Qq]\s*[:\.]\s*', line):
            q = re.sub(r'^[Qq]\s*[:\.]\s*', '', line).strip()
            a_parts = []
            i += 1
            while i < len(lines) and re.match(r'^[Aa]\s*[:\.]\s*', lines[i].strip()):
                a_parts.append(re.sub(r'^[Aa]\s*[:\.]\s*', '', lines[i].strip()))
                i += 1
            if a_parts:
                pairs.append({'question': q, 'answer': ' '.join(a_parts)})
                continue
        i += 1
    if pairs:
        return pairs
    # Flat fallback
    return _extract_flat(content)

def _extract_pdf(content, path):
    try:
        import subprocess
        result = subprocess.run(
            ['python3', '-c', f"""
import sys
try:
    import pdfplumber
    with pdfplumber.open('{path}') as pdf:
        text = ' '.join(p.extract_text() or '' for p in pdf.pages)
    print(text)
except ImportError:
    pass
"""], capture_output=True, text=True, timeout=30)
        text = result.stdout.strip()
        if text:
            return _extract_flat(text)
    except Exception:
        pass
    return []

def _extract_docx(content, path):
    try:
        import subprocess
        result = subprocess.run(
            ['python3', '-c', f"""
try:
    import docx
    doc = docx.Document('{path}')
    print(' '.join(p.text for p in doc.paragraphs))
except ImportError:
    pass
"""], capture_output=True, text=True, timeout=30)
        text = result.stdout.strip()
        if text:
            return _extract_flat(text)
    except Exception:
        pass
    return []

def _extract_code(content, path):
    """Extract function name + body as pairs from code files."""
    pairs = []
    ext = os.path.splitext(path)[1].lower()
    if ext == '.py':
        # Python functions
        for m in re.finditer(r'def\s+(\w+)\s*\([^)]*\)\s*:([^@]+?)(?=\ndef|\Z)', content, re.S):
            name = m.group(1)
            body = m.group(2).strip()
            if body:
                pairs.append({'question': f'what does {name} do', 'answer': body[:500]})
    elif ext in ('.js', '.ts'):
        for m in re.finditer(r'function\s+(\w+)\s*\([^)]*\)\s*\{([^}]+)\}', content, re.S):
            pairs.append({'question': f'what does {m.group(1)} do', 'answer': m.group(2).strip()[:500]})
    if not pairs:
        pairs = _extract_flat(content)
    return pairs

# Layout database — ordered by specificity
LAYOUTS = [
    {
        'name': 'ai.play native',
        'detect': lambda c, p: 'Training.data' in c or (c.count(':') > 2 and '\n' in c and not c.strip().startswith('{')),
        'extract': _extract_aiplay_data,
    },
    {
        'name': 'OpenAI JSONL',
        'detect': lambda c, p: c.strip().startswith('{') and ('prompt' in c or '"messages"' in c),
        'extract': _extract_openai_jsonl,
    },
    {
        'name': 'JSON pairs',
        'detect': lambda c, p: c.strip().startswith(('{', '[')),
        'extract': _extract_json_pairs,
    },
    {
        'name': 'CSV',
        'detect': lambda c, p: p.endswith('.csv') or (c.count(',') > 5 and '\n' in c),
        'extract': _extract_csv,
    },
    {
        'name': 'PDF',
        'detect': lambda c, p: p.endswith('.pdf'),
        'extract': lambda c, p: _extract_pdf(c, p),
    },
    {
        'name': 'DOCX',
        'detect': lambda c, p: p.endswith('.docx'),
        'extract': lambda c, p: _extract_docx(c, p),
    },
    {
        'name': 'Code',
        'detect': lambda c, p: os.path.splitext(p)[1].lower() in ('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs'),
        'extract': _extract_code,
    },
    {
        'name': 'Plain text / Q&A',
        'detect': lambda c, p: True,  # always matches — fallback
        'extract': _extract_txt,
    },
]


def load_any(path):
    """
    Auto-detect format and extract training pairs from any file.
    Returns (pairs, detected_format_name)
    """
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Training file not found: {path}")

    ext = os.path.splitext(path)[1].lower()

    # Binary files — can't read as text
    if ext in ('.pdf', '.docx'):
        for layout in LAYOUTS:
            if layout['detect']('', path):
                pairs = layout['extract']('', path)
                if pairs:
                    return pairs, layout['name']
        return [], 'unknown'

    # Text files
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        raise RuntimeError(f"Could not read {path}: {e}")

    for layout in LAYOUTS:
        try:
            if layout['detect'](content, path):
                pairs = layout['extract'](content, path)
                if pairs:
                    return pairs, layout['name']
        except Exception:
            continue

    return _extract_flat(content), 'flat knowledge base'
