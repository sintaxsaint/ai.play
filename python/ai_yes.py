"""
ai.play ai.yes() engine
Searches HuggingFace for the best open-licence equivalent to a target AI,
checks licence (MIT or Apache 2.0 only), downloads weights, and
auto-configures the correct capabilities.

Usage:
    ai.yes(chatgpt)
    ai.yes(claude)
    ai.yes(sora)
    ai.yes(midjourney)
    ai.yes(whisper)
    ai.yes(elevenlabs)
    ai.yes(copilot)
    ai.yes(gemini)
"""

import os
import json
import urllib.request

# ─────────────────────────────────────────
# TARGET PROFILES
# Maps known AI names to HuggingFace search
# terms and the capabilities to auto-enable
# ─────────────────────────────────────────

TARGETS = {
    'chatgpt': {
        'search':       'mistral instruct chat',
        'candidates':   ['mistralai/Mistral-7B-Instruct-v0.3',
                         'Qwen/Qwen2.5-7B-Instruct',
                         'microsoft/phi-3-mini-4k-instruct'],
        'caps':         ['web', 'memory'],
        'model_mode':   'factual',
        'description':  'General purpose conversational AI',
    },
    'claude': {
        'search':       'reasoning instruction following',
        'candidates':   ['mistralai/Mistral-7B-Instruct-v0.3',
                         'Qwen/Qwen2.5-72B-Instruct',
                         'meta-llama/Llama-3.1-8B-Instruct'],
        'caps':         ['web', 'memory'],
        'model_mode':   'thinking',
        'description':  'Reasoning focused conversational AI',
    },
    'copilot': {
        'search':       'code generation instruct',
        'candidates':   ['Qwen/Qwen2.5-Coder-7B-Instruct',
                         'bigcode/starcoder2-15b',
                         'codellama/CodeLlama-7b-Instruct-hf'],
        'caps':         [],
        'model_mode':   'factual',
        'modules':      ['python', 'javascript', 'git'],
        'description':  'Code generation and assistance',
    },
    'gemini': {
        'search':       'multimodal vision language model',
        'candidates':   ['llava-hf/llava-1.5-7b-hf',
                         'Qwen/Qwen2-VL-7B-Instruct'],
        'caps':         ['web', 'vision', 'memory'],
        'model_mode':   'factual',
        'description':  'Multimodal AI with vision',
    },
    'sora': {
        'search':       'text to video generation',
        'candidates':   ['ali-vilab/text-to-video-ms-1.7b',
                         'cerspense/zeroscope_v2_576w'],
        'caps':         ['video'],
        'model_mode':   'fun',
        'description':  'Text to video generation',
    },
    'midjourney': {
        'search':       'stable diffusion image generation',
        'candidates':   ['stabilityai/stable-diffusion-xl-base-1.0',
                         'stabilityai/stable-diffusion-2-1',
                         'runwayml/stable-diffusion-v1-5'],
        'caps':         ['diffusion'],
        'model_mode':   'fun',
        'description':  'Image generation from text',
    },
    'dalle': {
        'search':       'stable diffusion image generation',
        'candidates':   ['stabilityai/stable-diffusion-xl-base-1.0'],
        'caps':         ['diffusion'],
        'model_mode':   'fun',
        'description':  'Image generation from text',
    },
    'whisper': {
        'search':       'speech recognition whisper',
        'candidates':   ['openai/whisper-large-v3',
                         'openai/whisper-medium'],
        'caps':         ['voice'],
        'model_mode':   'factual',
        'description':  'Speech to text transcription',
    },
    'elevenlabs': {
        'search':       'text to speech tts',
        'candidates':   ['suno/bark',
                         'coqui/XTTS-v2'],
        'caps':         ['voice'],
        'model_mode':   'factual',
        'description':  'Text to speech voice synthesis',
    },
}

ALLOWED_LICENCES = {'mit', 'apache-2.0', 'apache 2.0', 'apache2'}

HF_API = 'https://huggingface.co/api/models/'


def _check_licence(model_id):
    """Check HuggingFace model licence. Returns True if MIT or Apache 2.0."""
    try:
        url = f'{HF_API}{model_id}'
        req = urllib.request.Request(url, headers={'User-Agent': 'aiplay/0.6'})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())

        licence = data.get('cardData', {}).get('license', '')
        if not licence:
            # Check tags
            tags = data.get('tags', [])
            for tag in tags:
                if tag.lower() in ALLOWED_LICENCES:
                    return True, tag
            return False, 'unknown'

        if licence.lower() in ALLOWED_LICENCES:
            return True, licence
        return False, licence
    except Exception as e:
        print(f"[ai.play] Licence check failed for {model_id}: {e}")
        return False, 'check_failed'


def resolve_target(target_name):
    """
    Find the best open-licence model for the target.
    Returns (model_id, profile) or (None, error_message).
    """
    name = target_name.lower().strip()

    if name not in TARGETS:
        return None, (
            f"Unknown target '{target_name}'.\n"
            f"Known targets: {', '.join(sorted(TARGETS.keys()))}\n"
            f"Request new targets: https://github.com/sintaxsaint/ai.play/issues"
        )

    profile = TARGETS[name]
    print(f"[ai.play] ai.yes({name}): {profile['description']}")
    print(f"[ai.play] Checking licences on HuggingFace...")

    for candidate in profile['candidates']:
        ok, licence = _check_licence(candidate)
        if ok:
            print(f"[ai.play] Selected: {candidate} (licence: {licence})")
            return candidate, profile
        else:
            print(f"[ai.play] Skipped: {candidate} (licence: {licence})")

    return None, (
        f"No MIT or Apache 2.0 licensed model found for '{target_name}'.\n"
        f"Check https://huggingface.co/models for alternatives.\n"
        f"Or request an update: https://github.com/sintaxsaint/ai.play/issues"
    )


class AIYes:
    """
    Handles ai.yes() — finds, verifies, and configures the right model.
    Returns a config dict the interpreter uses to set up capabilities.
    """
    def __init__(self):
        self.active_target  = None
        self.active_model   = None
        self.active_profile = None

    def activate(self, target_name):
        model_id, result = resolve_target(target_name)

        if model_id is None:
            print(f"[ai.play] ai.yes failed: {result}")
            return None

        self.active_target  = target_name
        self.active_model   = model_id
        self.active_profile = result

        print(f"[ai.play] ai.yes({target_name}) ready")
        print(f"[ai.play] Model: {model_id}")
        print(f"[ai.play] Auto-enabling: {result.get('caps', [])}")

        return {
            'model_id':   model_id,
            'caps':       result.get('caps', []),
            'model_mode': result.get('model_mode', 'factual'),
            'modules':    result.get('modules', []),
        }
