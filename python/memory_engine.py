"""
ai.play memory engine
Two modes:
  rule       — stores conversation history, retrieves by pattern match
  generative — Elliot's Generative Memory architecture: compresses and evolves memory over time
"""

import os
import json
import re
import math
import time
from collections import defaultdict


# ─────────────────────────────────────────
# RULE-BASED MEMORY
# ─────────────────────────────────────────

class RuleMemory:
    def __init__(self, path='.aiplay_memory.json'):
        self.path    = path
        self.history = []  # list of {'role': 'user'|'ai', 'text': str, 'ts': float}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def _save(self):
        try:
            with open(self.path, 'w') as f:
                json.dump(self.history[-500:], f)  # keep last 500 turns
        except Exception:
            pass

    def add(self, role, text):
        self.history.append({'role': role, 'text': text, 'ts': time.time()})
        self._save()

    def get_context(self, query, top_k=5):
        """Return most relevant past exchanges for the current query."""
        query_words = set(re.findall(r'\w+', query.lower()))
        scored = []
        for i, item in enumerate(self.history):
            words = set(re.findall(r'\w+', item['text'].lower()))
            overlap = len(query_words & words)
            recency = i / max(len(self.history), 1)
            score = overlap + recency * 2
            scored.append((score, item))
        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:top_k]]

    def get_recent(self, n=10):
        return self.history[-n:]

    def format_for_context(self, items):
        lines = []
        for item in items:
            role = 'User' if item['role'] == 'user' else 'AI'
            lines.append(f"{role}: {item['text']}")
        return '\n'.join(lines)


# ─────────────────────────────────────────
# GENERATIVE MEMORY  (sintaxsaint architecture)
# ─────────────────────────────────────────
# Core principle: instead of raw history, maintain a compressed evolving
# memory representation. New inputs are merged into the existing memory
# rather than appended, keeping it dense and small.
# Based on: github.com/sintaxsaint/generative-AI-memory

class GenerativeMemory:
    def __init__(self, path='.aiplay_genmemory.json'):
        self.path       = path
        self.memory     = {}   # concept -> weight
        self.timestamps = {}   # concept -> last_seen
        self.exchanges  = []   # compressed exchange log
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    self.memory     = data.get('memory', {})
                    self.timestamps = data.get('timestamps', {})
                    self.exchanges  = data.get('exchanges', [])
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.path, 'w') as f:
                json.dump({
                    'memory':     self.memory,
                    'timestamps': self.timestamps,
                    'exchanges':  self.exchanges[-200:],
                }, f)
        except Exception:
            pass

    def _extract_concepts(self, text):
        """Extract key concepts (meaningful words) from text."""
        stopwords = {'the','a','an','is','are','was','were','be','been','being',
                     'have','has','had','do','does','did','will','would','could',
                     'should','may','might','shall','can','need','dare','ought',
                     'i','you','he','she','it','we','they','what','which','who',
                     'this','that','these','those','am','to','of','in','for',
                     'on','with','at','by','from','as','into','through','about',
                     'not','or','and','but','if','then','so','yet','both','nor'}
        words = re.findall(r'\b[a-z][a-z0-9]{2,}\b', text.lower())
        return [w for w in words if w not in stopwords]

    def _decay(self):
        """Apply time-based decay to memory weights."""
        now = time.time()
        to_remove = []
        for concept, ts in self.timestamps.items():
            age_hours = (now - ts) / 3600
            decay = math.exp(-0.01 * age_hours)  # slow decay
            self.memory[concept] = self.memory.get(concept, 0) * decay
            if self.memory[concept] < 0.01:
                to_remove.append(concept)
        for c in to_remove:
            del self.memory[c]
            del self.timestamps[c]

    def absorb(self, role, text):
        """
        Core generative memory step: merge new input into memory.
        Concepts from the input reinforce existing memory or create new entries.
        Timestamp injection: each concept tagged with current time.
        """
        now = time.time()
        concepts = self._extract_concepts(text)

        # Reinforcement: seen concepts get stronger, new ones start weak
        for concept in concepts:
            current = self.memory.get(concept, 0.0)
            # Logarithmic reinforcement — avoids runaway dominance
            self.memory[concept] = current + (1.0 / (1.0 + current))
            self.timestamps[concept] = now

        # Store compressed exchange (just key concepts + role)
        self.exchanges.append({
            'role':     role,
            'concepts': concepts[:10],  # top 10 concepts
            'ts':       now,
        })

        self._decay()
        self._save()

    def get_context(self, query, top_k=5):
        """
        Retrieve memory context relevant to query.
        Returns concepts weighted by both memory strength and query relevance.
        """
        query_concepts = set(self._extract_concepts(query))

        # Score each memory concept by relevance to query
        scored = {}
        for concept, weight in self.memory.items():
            if concept in query_concepts:
                scored[concept] = weight * 2.0  # boost exact matches
            else:
                scored[concept] = weight

        # Find relevant exchanges
        relevant = []
        for ex in reversed(self.exchanges):
            overlap = len(set(ex['concepts']) & query_concepts)
            if overlap > 0:
                relevant.append(ex)
            if len(relevant) >= top_k:
                break

        return {
            'top_concepts': sorted(scored.items(), key=lambda x: -x[1])[:20],
            'exchanges':    relevant,
        }

    def format_for_context(self, ctx):
        """Format memory context as a string for the responder."""
        lines = []
        if ctx['top_concepts']:
            concepts_str = ', '.join(c for c, _ in ctx['top_concepts'][:10])
            lines.append(f"Memory context: {concepts_str}")
        for ex in ctx['exchanges'][:3]:
            role = 'User' if ex['role'] == 'user' else 'AI'
            lines.append(f"{role} discussed: {', '.join(ex['concepts'])}")
        return '\n'.join(lines)

    def add(self, role, text):
        self.absorb(role, text)

    def get_recent(self, n=10):
        return self.exchanges[-n:]


# ─────────────────────────────────────────
# FACTORY
# ─────────────────────────────────────────

def make_memory(mode, session_id='default'):
    path_prefix = f'.aiplay_{session_id}'
    if mode == 'generative':
        return GenerativeMemory(path=f'{path_prefix}_genmemory.json')
    elif mode == 'rule':
        return RuleMemory(path=f'{path_prefix}_memory.json')
    return None
