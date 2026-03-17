"""
ai.play module engine — custom.module()
Lets developers create and load .aimod files that teach the AI
new languages, APIs, behaviours, or any specialised knowledge.

Resolution order:
  1. Explicit path — custom.module(./modules/python.aimod)
  2. System modules directory — C:\aiplay\modules\python.aimod (Windows)
                                 ~/.aiplay/modules/python.aimod (Linux/Mac)
  3. Not found — tell the developer where to look

.aimod file format:
    name: Python
    version: 1.0
    type: language
    trigger: write code, python, function, script, def, class
    output: code
    description: Teaches the AI to write and explain Python code
    ---
    Training.data(pairs):
    how do I write a for loop in python:for i in range(10):\n    print(i)
    what is a list in python:A list is an ordered collection: my_list = [1, 2, 3]
"""

import os
import re
import sys

# ─────────────────────────────────────────
# SYSTEM MODULES DIRECTORY
# ─────────────────────────────────────────

def get_system_modules_dir():
    if sys.platform == 'win32':
        # Windows — same dir as the installer puts everything
        prog = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
        return os.path.join(prog, 'aiplay', 'modules')
    else:
        return os.path.expanduser('~/.aiplay/modules')

NOT_FOUND_MESSAGE = """\
Module '{name}' not found locally.

Find community modules at:
  https://sintaxsaint.pages.dev
  https://github.com/sintaxsaint/ai.play/issues

Once downloaded, place the .aimod file in:
  {modules_dir}

Then use it with:
  custom.module({name})

To share your own module with the community:
  https://github.com/sintaxsaint/ai.play/issues
"""


# ─────────────────────────────────────────
# MODULE CLASS
# ─────────────────────────────────────────

class AIModule:
    def __init__(self, name, version, type_, triggers, output_type,
                 description, pairs, path):
        self.name        = name
        self.version     = version
        self.type        = type_          # language | api | behaviour | knowledge
        self.triggers    = triggers       # list of trigger words/phrases
        self.output_type = output_type    # text | code | json | etc
        self.description = description
        self.pairs       = pairs          # list of {'question', 'answer'}
        self.path        = path
        self.vec_store   = []             # embedded, filled by engine

    def __repr__(self):
        return f"AIModule({self.name!r} v{self.version}, {len(self.pairs)} pairs)"


# ─────────────────────────────────────────
# LOADER
# ─────────────────────────────────────────

def _parse_aimod(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    if '---' in content:
        header, _, body = content.partition('---')
    else:
        header, body = '', content

    meta = {}
    for line in header.splitlines():
        line = line.strip()
        if ':' in line and not line.startswith('#'):
            k, _, v = line.partition(':')
            meta[k.strip().lower()] = v.strip()

    name        = meta.get('name', os.path.splitext(os.path.basename(path))[0])
    version     = meta.get('version', '1.0')
    type_       = meta.get('type', 'knowledge')
    triggers    = [t.strip().lower() for t in meta.get('trigger', '').split(',') if t.strip()]
    output_type = meta.get('output', 'text')
    description = meta.get('description', '')

    # Split body into sections by ---
    sections = content.split('---')
    # Section 0 = header (already parsed), 1 = training, 2 = web, 3 = skills
    training_body = sections[1] if len(sections) > 1 else body

    # Parse training pairs — stop at Web.training or Skills.inject
    pairs = []
    in_pairs = False
    for line in training_body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.startswith('Training.data'):
            in_pairs = True
            continue
        if stripped.startswith('Web.training') or stripped.startswith('Skills.inject'):
            break
        if not in_pairs:
            # No Training.data header found yet — treat all lines as pairs
            in_pairs = True
        if ':' in stripped:
            q, _, a = stripped.partition(':')
            q, a = q.strip(), a.strip()
            a = a.replace('\\n', '\n')
            if q and a:
                pairs.append({'question': q, 'answer': a})

    # Parse Skills.inject for tone and on_request directives
    skills_tone = ''
    on_requests = {}
    if len(sections) > 3:
        for line in sections[3].splitlines():
            line = line.strip()
            if line.startswith('tone:'):
                skills_tone = line[5:].strip()
            elif line.startswith('on_request('):
                key = line.split('(')[1].split(')')[0]
                val = line.partition(':')[2].strip()
                on_requests[key] = val

    mod = AIModule(
        name        = name,
        version     = version,
        type_       = type_,
        triggers    = triggers,
        output_type = output_type,
        description = description,
        pairs       = pairs,
        path        = path,
    )
    mod.skills_tone  = skills_tone
    mod.on_requests  = on_requests
    return mod


def resolve_module(name_or_path):
    """
    Resolve a module name or path to a loaded AIModule.
    Returns (module, None) on success or (None, error_message) on failure.
    """
    modules_dir = get_system_modules_dir()

    # 1. Explicit path
    if os.sep in name_or_path or name_or_path.startswith('.'):
        path = os.path.expanduser(name_or_path)
        if not path.endswith('.aimod'):
            path += '.aimod'
        if os.path.exists(path):
            try:
                return _parse_aimod(path), None
            except Exception as e:
                return None, f"Failed to load module at {path}: {e}"
        return None, NOT_FOUND_MESSAGE.format(name=name_or_path, modules_dir=modules_dir)

    # 2. System modules directory
    sys_path = os.path.join(modules_dir, f'{name_or_path}.aimod')
    if os.path.exists(sys_path):
        try:
            return _parse_aimod(sys_path), None
        except Exception as e:
            return None, f"Failed to load module '{name_or_path}': {e}"

    # 3. Not found — helpful message
    return None, NOT_FOUND_MESSAGE.format(name=name_or_path, modules_dir=modules_dir)


# ─────────────────────────────────────────
# MODULE ENGINE
# ─────────────────────────────────────────

class ModuleEngine:
    def __init__(self):
        self.modules = []   # list of loaded AIModule

    def load(self, name_or_path):
        """Load a module by name or path. Prints result."""
        module, err = resolve_module(name_or_path)
        if err:
            print(f"[ai.play] {err}")
            return False
        self.modules.append(module)
        print(f"[ai.play] Module loaded: {module.name} v{module.version} ({len(module.pairs)} pairs)")
        return True

    def embed_all(self, embedder):
        """Embed all module pairs using the main embedder."""
        for mod in self.modules:
            mod.vec_store = []
            for p in mod.pairs:
                vec = embedder.embed_raw(p['question'] + ' ' + p['answer'])
                mod.vec_store.append({
                    'question':    p['question'],
                    'answer':      p['answer'],
                    'vec':         vec,
                    'module':      mod.name,
                    'output_type': mod.output_type,
                })

    def select_modules(self, query):
        """Return modules relevant to this query based on trigger words."""
        q_words = set(re.findall(r'\w+', query.lower()))
        matched = []
        for mod in self.modules:
            trigger_set = set()
            for t in mod.triggers:
                trigger_set.update(re.findall(r'\w+', t))
            overlap = len(q_words & trigger_set)
            if overlap > 0:
                matched.append((overlap, mod))
        matched.sort(key=lambda x: -x[0])
        return [m for _, m in matched]

    def get_store(self, query):
        """
        Return combined vec_store from relevant modules for this query.
        Also returns the dominant output_type (code, json, text etc).
        """
        relevant = self.select_modules(query)
        if not relevant:
            # Return all module pairs as fallback
            store = []
            for mod in self.modules:
                store.extend(mod.vec_store)
            return store, 'text'

        store = []
        output_types = []
        for mod in relevant:
            store.extend(mod.vec_store)
            output_types.append(mod.output_type)

        dominant_type = output_types[0] if output_types else 'text'
        return store, dominant_type

    def installed_modules(self):
        return [(m.name, m.version, m.description) for m in self.modules]


# ─────────────────────────────────────────
# MODULE MAKER HELPER
# Creates a blank .aimod template for developers
# ─────────────────────────────────────────

def create_module_template(name, output_path=None):
    """
    Generate a blank .aimod template for a developer to fill in.
    """
    if output_path is None:
        output_path = f'{name.lower().replace(" ", "_")}.aimod'

    template = f"""name: {name}
version: 1.0
type: knowledge
trigger: {name.lower()}, 
output: text
description: Describe what this module teaches the AI
---
# Training pairs — question:answer
# Use \\n in answers for multiline content (e.g. code blocks)
# Lines starting with # are comments

Training.data(pairs):
what is {name.lower()}:Describe {name} here
how do I use {name.lower()}:Explain how to use {name} here
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template)

    print(f"[ai.play] Module template created: {output_path}")
    print(f"[ai.play] Fill it in, then load it with: custom.module({name.lower()})")
    print(f"[ai.play] Share it with the community: https://github.com/sintaxsaint/ai.play/issues")
    print(f"[ai.play] Browse existing modules:         https://sintaxsaint.pages.dev")
    return output_path
