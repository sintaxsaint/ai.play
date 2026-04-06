"""
ai.play voice engine — ai.voice(yes)
Speech-to-text input + text-to-speech output.
Phone-call style: listen -> process -> speak, continuously.
Pure Python where possible, falls back gracefully.
"""

import os
import sys
import threading
import queue
import tempfile
import wave
import struct
import math

# ─────────────────────────────────────────
# SPEECH TO TEXT
# ─────────────────────────────────────────

def listen():
    """
    Record from microphone until silence, return transcribed text.
    Tries: faster-whisper (local, fast) -> speech_recognition -> stub
    """
    audio_data = _record_until_silence()
    if audio_data is None:
        return input("[voice] (mic unavailable, type instead): ")

    # Try faster-whisper first (local, no API)
    text = _transcribe_faster_whisper(audio_data)
    if text:
        print(f"[voice] Heard: {text}")
        return text

    # Try SpeechRecognition with Google (needs internet)
    text = _transcribe_sr(audio_data)
    if text:
        print(f"[voice] Heard: {text}")
        return text

    # Fallback to typed input
    return input("[voice] (transcription unavailable, type instead): ")


def _record_until_silence(silence_threshold=500, silence_duration=1.5, max_seconds=30):
    """Record audio until silence is detected. Returns raw PCM bytes or None."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        print("[voice] Listening...")
        frames = []
        silent_chunks = 0
        required_silent = int(silence_duration * 16000 / 1024)
        max_chunks = int(max_seconds * 16000 / 1024)

        for _ in range(max_chunks):
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)
            # RMS volume — trim to even byte count before unpacking 16-bit samples
            even = data[:len(data) // 2 * 2]
            if not even:
                continue
            shorts = struct.unpack(f'{len(even) // 2}h', even)
            rms = math.sqrt(sum(s*s for s in shorts) / len(shorts))
            if rms < silence_threshold:
                silent_chunks += 1
                if silent_chunks >= required_silent and len(frames) > required_silent:
                    break
            else:
                silent_chunks = 0

        stream.stop_stream()
        stream.close()
        pa.terminate()
        return b''.join(frames)
    except ImportError:
        return None
    except Exception:
        return None


def _transcribe_faster_whisper(audio_bytes):
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        fd, tmp = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        try:
            with wave.open(tmp, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_bytes)
            segments, _ = model.transcribe(tmp, beam_size=1)
            text = ' '.join(s.text for s in segments).strip()
        finally:
            try: os.remove(tmp)
            except OSError: pass
        return text if text else None
    except ImportError:
        return None
    except Exception:
        return None


def _transcribe_sr(audio_bytes):
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        fd, tmp = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        try:
            with wave.open(tmp, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_bytes)
            with sr.AudioFile(tmp) as source:
                audio = r.record(source)
        finally:
            try: os.remove(tmp)
            except OSError: pass
        return r.recognize_google(audio)
    except Exception:
        return None


# ─────────────────────────────────────────
# TEXT TO SPEECH
# ─────────────────────────────────────────

def speak(text):
    """
    Speak text aloud.
    Tries: pyttsx3 (offline, any OS) -> espeak -> system TTS -> print only
    """
    # Try pyttsx3 (cross-platform, offline)
    if _speak_pyttsx3(text):
        return

    # Try espeak (Linux/Windows)
    if _speak_espeak(text):
        return

    # Windows SAPI via PowerShell
    if _speak_windows_sapi(text):
        return

    # macOS say
    if _speak_mac_say(text):
        return

    # Silent fallback — text already printed by interpreter
    print(f"[voice] (TTS unavailable) {text}")


def _speak_pyttsx3(text):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception:
        return False


def _speak_espeak(text):
    try:
        import subprocess
        subprocess.run(['espeak', '-s', '175', text],
                      capture_output=True, timeout=30)
        return True
    except Exception:
        return False


def _speak_windows_sapi(text):
    try:
        import subprocess
        safe = text.replace("'", "")
        subprocess.run(
            ['powershell', '-Command',
             f"Add-Type -AssemblyName System.Speech; "
             f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
             f"$s.Speak('{safe}')"],
            capture_output=True, timeout=30
        )
        return True
    except Exception:
        return False


def _speak_mac_say(text):
    try:
        import subprocess
        subprocess.run(['say', text], capture_output=True, timeout=30)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────
# VOICE TOKENIZER
# Convert speech audio bytes directly to tokens
# so tokenize() handles voice natively
# ─────────────────────────────────────────

def audio_to_tokens(audio_bytes):
    """
    Converts raw PCM audio to pseudo-tokens representing acoustic features.
    Used by tokenize() when voice is enabled and input is audio data.
    Falls back to transcription + normal tokenize if possible.
    """
    # Best path: transcribe and tokenize the text
    text = _transcribe_faster_whisper(audio_bytes) or _transcribe_sr(audio_bytes)
    if text:
        from runtime import tokenize
        return tokenize(text)

    # Fallback: acoustic feature tokens (pitch + energy per frame)
    tokens = []
    if len(audio_bytes) < 2:
        return ['audio_empty']

    chunk_size = 1024
    for i in range(0, min(len(audio_bytes), 32768), chunk_size):
        chunk = audio_bytes[i:i+chunk_size]
        if len(chunk) < 2:
            break
        shorts = struct.unpack(f'{len(chunk)//2}h', chunk[:len(chunk)//2*2])
        rms = math.sqrt(sum(s*s for s in shorts) / max(len(shorts), 1))
        if rms < 200:
            tokens.append('silence')
        elif rms < 2000:
            tokens.append('quiet_speech')
        elif rms < 8000:
            tokens.append('normal_speech')
        else:
            tokens.append('loud_speech')

    tokens.append('audio_input')
    return tokens if tokens else ['audio_input']
