"""
ai.play intent engine
Analyses the context bundle from Similaritize + the raw query
and decides which modalities the responder should use.

Also enforces built-in intent rules — if the user clearly wants
a video, image, voice response etc, the responder acts on it
or tells the user exactly how to enable it.
"""

import re

# ─────────────────────────────────────────
# INTENT RULES
# Each rule: pattern list, required_cap, suggestion
# Patterns are matched against the raw query (lowercased)
# ─────────────────────────────────────────

INTENT_RULES = [
    {
        'name':         'video_generation',
        'patterns':     [
            r'\bmake\b.{0,30}\bvideo\b',
            r'\bgenerate\b.{0,30}\bvideo\b',
            r'\bcreate\b.{0,30}\bvideo\b',
            r'\bvideo\b.{0,20}\bof\b',
            r'\bfilm\b',
            r'\banimate\b',
            r'\banimation\b',
        ],
        'cap':          'video',
        'syntax':       'ai.video(yes)',
        'label':        'video generation',
        'action':       'video',
    },
    {
        'name':         'image_generation',
        'patterns':     [
            r'\bmake\b.{0,30}\bimage\b',
            r'\bgenerate\b.{0,30}\bimage\b',
            r'\bcreate\b.{0,30}\bimage\b',
            r'\bdraw\b',
            r'\bpaint\b',
            r'\bpicture\b.{0,20}\bof\b',
            r'\billustrate\b',
            r'\bshow\b.{0,20}\bwhat\b.{0,20}\blooks like\b',
            r'\bimage\b.{0,20}\bof\b',
        ],
        'cap':          'diffusion',
        'syntax':       'ai.diffusion(yes)',
        'label':        'image generation',
        'action':       'diffusion',
    },
    {
        'name':         'web_search',
        'patterns':     [
            r'\bsearch\b.{0,20}\bweb\b',
            r'\blook\b.{0,20}\bup\b',
            r'\blatest\b',
            r'\bcurrent\b.{0,20}\bnews\b',
            r'\btoday\b',
            r'\bright now\b',
            r'\brecently\b',
        ],
        'cap':          'web',
        'syntax':       'ai.web(yes)',
        'label':        'web search',
        'action':       'web',
    },
    {
        'name':         'vision_input',
        'patterns':     [
            r'\blook\b.{0,20}\bat\b',
            r'\bwhat\b.{0,20}\bdo you see\b',
            r'\bdescribe\b.{0,20}\bimage\b',
            r'\banalyse\b.{0,20}\bimage\b',
            r'\banalyze\b.{0,20}\bimage\b',
            r'\bwhat\b.{0,20}\bin\b.{0,20}\bpicture\b',
            r'\bwhat\b.{0,20}\bin\b.{0,20}\bphoto\b',
            r'\bwhat\b.{0,20}\bin\b.{0,20}\bimage\b',
        ],
        'cap':          'vision',
        'syntax':       'ai.vision(normal)',
        'label':        'vision',
        'action':       'vision',
    },
    {
        'name':         'voice_output',
        'patterns':     [
            r'\bsay\b.{0,20}\baloud\b',
            r'\bread\b.{0,20}\bout\b.{0,20}\bloud\b',
            r'\bspeak\b',
            r'\btell\b.{0,20}\bme\b.{0,20}\bvoice\b',
        ],
        'cap':          'voice',
        'syntax':       'ai.voice(yes)',
        'label':        'voice output',
        'action':       'voice',
    },
    {
        'name':         'memory_recall',
        'patterns':     [
            r'\bremember\b',
            r'\bdo you recall\b',
            r'\bwhat did (i|we) say\b',
            r'\bearlier\b.{0,20}\bsaid\b',
            r'\bprevious\b.{0,20}\bconversation\b',
        ],
        'cap':          'memory',
        'syntax':       'ai.memory(rule)',
        'label':        'memory',
        'action':       'memory',
    },
]

# ─────────────────────────────────────────
# SIMILARITY-BASED MODALITY HINTS
# If top training pairs contain these keywords,
# hint that a certain modality would enrich the response
# ─────────────────────────────────────────

SIMILARITY_HINTS = {
    'video':     ['video', 'film', 'animation', 'movie', 'footage'],
    'diffusion': ['image', 'picture', 'photo', 'visual', 'drawing', 'illustration'],
    'web':       ['news', 'latest', 'current', 'today', 'recent', 'update'],
    'voice':     ['speak', 'say', 'listen', 'audio', 'sound'],
}


# ─────────────────────────────────────────
# MAIN INTENT ANALYSER
# ─────────────────────────────────────────

def analyse(raw_query, context_bundle, caps):
    """
    Analyse query + context and return an IntentResult.

    raw_query:      the original user input string
    context_bundle: list of (score, question, answer) from Similaritize
    caps:           dict of enabled capabilities from the interpreter

    Returns IntentResult with:
      .actions       — list of modality actions to take ('text', 'video', 'diffusion', etc)
      .missing       — list of (label, syntax) for capabilities needed but not enabled
      .blocked       — True if a hard intent was detected but capability is missing
    """
    q = raw_query.lower().strip()
    actions  = ['text']   # text is always included
    missing  = []
    blocked  = False

    # ── Rule-based intent matching ────────────────────────────────
    for rule in INTENT_RULES:
        matched = any(re.search(p, q) for p in rule['patterns'])
        if not matched:
            continue

        cap   = rule['cap']
        label = rule['label']
        syn   = rule['syntax']
        act   = rule['action']

        cap_enabled = caps.get(cap, False)

        if cap_enabled:
            if act not in actions:
                actions.append(act)
        else:
            # Capability needed but not enabled
            missing.append({'label': label, 'syntax': syn})
            blocked = True  # hard intent detected, cannot fulfil

    # ── Similarity-based modality hints ──────────────────────────
    # Soft hints — only activate if cap is already enabled
    if context_bundle:
        top_answers = ' '.join(a for _, _, a in context_bundle[:3]).lower()
        for cap, keywords in SIMILARITY_HINTS.items():
            if caps.get(cap) and any(k in top_answers for k in keywords):
                if cap not in actions:
                    actions.append(cap)

    return IntentResult(actions=actions, missing=missing, blocked=blocked)


class IntentResult:
    def __init__(self, actions, missing, blocked):
        self.actions = actions    # ['text', 'video', ...]
        self.missing = missing    # [{'label': 'video generation', 'syntax': 'ai.video(yes)'}]
        self.blocked = blocked    # True if hard intent but cap missing

    def missing_message(self):
        """
        Returns the user-facing message when a needed capability is missing.
        """
        if not self.missing:
            return None
        parts = []
        for m in self.missing:
            parts.append(
                f"The current AI model used doesn't support \"{m['label']}\" — "
                f"contact the dev, or if you are the dev, to enable it put "
                f"\"{m['syntax']}\" at the top of your .aip file for this model."
            )
        return '\n'.join(parts)

    def wants(self, action):
        return action in self.actions

    def __repr__(self):
        return f"IntentResult(actions={self.actions}, missing={len(self.missing)}, blocked={self.blocked})"
