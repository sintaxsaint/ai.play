"""
ai.play skills engine — ai.skills(path)
Loads .skill files from a directory.
Each skill defines domain knowledge, tone, and behaviour.
The AI auto-selects the right skill based on the conversation.

.skill file format:
    name: Customer Support
    keywords: help, problem, issue, broken, refund, complaint, support
    tone: friendly and patient
    priority: 10
    ---
    question:answer
    question:answer
"""

import os
import re
from collections import defaultdict

class Skill:
    def __init__(self, name, keywords, tone, priority, pairs, path):
        self.name     = name
        self.keywords = keywords   # list of trigger words
        self.tone     = tone       # tone instruction for responder
        self.priority = priority   # higher = preferred when multiple match
        self.pairs    = pairs      # list of {'question', 'answer'}
        self.path     = path
        self.vec_store = []        # embedded pairs, filled by engine

    def __repr__(self):
        return f"Skill({self.name!r}, keywords={self.keywords[:3]}, pairs={len(self.pairs)})"


def load_skill_file(path):
    """Parse a .skill file into a Skill object."""
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Split on --- separator between header and pairs
    if '---' in content:
        header, _, body = content.partition('---')
    else:
        header, body = '', content

    # Parse header
    meta = {}
    for line in header.splitlines():
        line = line.strip()
        if ':' in line and not line.startswith('#'):
            k, _, v = line.partition(':')
            meta[k.strip().lower()] = v.strip()

    name     = meta.get('name', os.path.splitext(os.path.basename(path))[0])
    keywords = [k.strip().lower() for k in meta.get('keywords', '').split(',') if k.strip()]
    tone     = meta.get('tone', '')
    priority = int(meta.get('priority', 5))

    # Parse pairs from body
    pairs = []
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            q, _, a = line.partition(':')
            q, a = q.strip(), a.strip()
            if q and a:
                pairs.append({'question': q, 'answer': a})

    return Skill(name=name, keywords=keywords, tone=tone,
                 priority=priority, pairs=pairs, path=path)


class SkillsEngine:
    def __init__(self, skills_path):
        self.skills_path = skills_path
        self.skills      = []
        self._load_all()

    def _load_all(self):
        path = os.path.expanduser(self.skills_path)
        if not os.path.exists(path):
            print(f"[ai.play] Skills directory not found: {path}")
            return

        count = 0
        for fname in os.listdir(path):
            if fname.endswith('.skill'):
                try:
                    skill = load_skill_file(os.path.join(path, fname))
                    self.skills.append(skill)
                    count += 1
                except Exception as e:
                    print(f"[ai.play] Failed to load skill {fname}: {e}")

        print(f"[ai.play] Loaded {count} skill(s) from {path}")

    def embed_all(self, embedder):
        """Embed all skill pairs using the main embedder."""
        for skill in self.skills:
            skill.vec_store = []
            for p in skill.pairs:
                vec = embedder.embed_raw(p['question'] + ' ' + p['answer'])
                skill.vec_store.append({
                    'question': p['question'],
                    'answer':   p['answer'],
                    'vec':      vec,
                    'skill':    skill.name,
                })

    def select_skill(self, query):
        """
        Select the most relevant skill for this query.
        Returns (skill, score) or (None, 0) if no match.
        """
        if not self.skills:
            return None, 0

        q_words = set(re.findall(r'\w+', query.lower()))
        best_skill, best_score = None, 0

        for skill in self.skills:
            kw_set = set(skill.keywords)
            overlap = len(q_words & kw_set)
            score   = overlap * skill.priority
            if score > best_score:
                best_skill, best_score = skill, score

        return best_skill, best_score

    def get_skill_store(self, query):
        """
        Return the vec_store for the best matching skill,
        plus the skill's tone instruction.
        Returns (store, tone_hint) — store is [] if no match.
        """
        skill, score = self.select_skill(query)
        if skill and score > 0:
            return skill.vec_store, skill.tone, skill.name
        return [], '', None

    def all_stores(self):
        """Return all skill pairs combined — used as fallback."""
        combined = []
        for skill in self.skills:
            combined.extend(skill.vec_store)
        return combined
