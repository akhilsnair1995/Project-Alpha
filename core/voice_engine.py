"""
Project Alpha: Expressive Voice Cortex & Procedural Sound Synthesis Engine.
Generates authentic Wall-E procedural sound effects (chirps, trills, sirens, beeps),
provides native playback for Alpha's signature voice clip ('Voice 1.mp3'),
and provides cross-platform offline Text-to-Speech (TTS) coordinated with eye animations.
"""

import os
import re
import io
import wave
import struct
import math
import time
import threading
import asyncio
import hashlib
import concurrent.futures
from typing import Optional, Callable, Dict, Any, Tuple
from pathlib import Path

from core.config import DATA_DIR, IS_RASPBERRY_PI, ALPHA_VOICE_PATH
from core.eye_animator import Emotion

SOUNDS_DIR = DATA_DIR / "sounds"
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

TTS_CACHE_DIR = DATA_DIR / "tts_cache"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Default high-fidelity neural voice (calibrated to match Alpha's Voice 1.mp3)
DEFAULT_NEURAL_VOICE = "en-US-AnaNeural"

# Emotion-adaptive prosody and sound mapping for living companion expressions
EMOTION_PROSODY: Dict[str, Dict[str, str]] = {
    "happy": {"pitch": "+14Hz", "rate": "+4%", "sound": "happy"},
    "excited": {"pitch": "+22Hz", "rate": "+12%", "sound": "excited"},
    "curious": {"pitch": "+16Hz", "rate": "+2%", "sound": "curious"},
    "love": {"pitch": "+6Hz", "rate": "-4%", "sound": "love"},
    "alert": {"pitch": "+26Hz", "rate": "+14%", "sound": "alert"},
    "surprised": {"pitch": "+24Hz", "rate": "+10%", "sound": "alert"},
    "sad": {"pitch": "-12Hz", "rate": "-15%", "sound": "sad"},
    "analyzing": {"pitch": "+8Hz", "rate": "+0%", "sound": "thinking"},
    "confused": {"pitch": "+12Hz", "rate": "-5%", "sound": "confused"},
    "wink": {"pitch": "+15Hz", "rate": "+6%", "sound": "wink"},
    "sleepy": {"pitch": "-16Hz", "rate": "-20%", "sound": "shutdown"},
    "angry": {"pitch": "+8Hz", "rate": "-5%", "sound": "angry"},
    "skeptical": {"pitch": "+6Hz", "rate": "-2%", "sound": "confused"},
    "squint": {"pitch": "+10Hz", "rate": "+0%", "sound": "thinking"},
}


def sanitize_speech_text(text: str) -> str:
    """
    Cleans raw text for natural, conversational human-like TTS speech.
    Strips out:
      - Bracketed tags: [EMOTION: ...], [MOOD: ...]
      - Stage directions: *wiggles tracks*, (laughs), *chirps happily*
      - Markdown markers: *, _, #, `, >, ~
      - Unicode emojis and symbol icons
      - Multiple spaces
    """
    if not text:
        return ""
    t = re.sub(r"\[[A-Za-z0-9_: -]+\]", " ", text)
    t = re.sub(r"\*{2,}([^*]+)\*{2,}", r"\1", t)
    t = re.sub(r"\*[^*]+\*", " ", t)
    t = re.sub(r"\([^)]+\)", " ", t)
    t = re.sub(r"[*_#`>~]", "", t)
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)
    t = re.sub(r"[•★☆✓✔➔➡➜✨🤖👀❤️💖🐾]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _play_mp3_windows(mp3_abs_path: str) -> bool:
    """Plays MP3 using Windows winmm MCI or PowerShell MediaPlayer fallback."""
    try:
        import ctypes
        mci = ctypes.windll.winmm.mciSendStringW
        alias = f"alpha_voice_{int(time.time() * 1000) % 100000}"
        open_cmd = f'open "{mp3_abs_path}" type mpegvideo alias {alias}'
        res = mci(open_cmd, None, 0, 0)
        if res == 0:
            mci(f'play {alias} wait', None, 0, 0)
            mci(f'close {alias}', None, 0, 0)
            return True
    except Exception:
        pass

    # Secondary fallback using presentationCore MediaPlayer
    try:
        import subprocess
        ps_cmd = (
            f"Add-Type -AssemblyName presentationCore; "
            f"$p = New-Object System.Windows.Media.MediaPlayer; "
            f"$p.Open([System.Uri]'{mp3_abs_path}'); "
            f"$p.Play(); "
            f"Start-Sleep -Milliseconds 3400"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False


def _play_mp3_linux(mp3_abs_path: str) -> bool:
    """Plays MP3 using Linux / Raspberry Pi audio tools."""
    import subprocess
    for cmd in [["mpg123", "-q"], ["cvlc", "--play-and-exit", "-q"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]]:
        try:
            res = subprocess.run(cmd + [mp3_abs_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return True
        except Exception:
            continue
    return False


class WallESoundSynthesizer:
    """
    Pure Python procedural waveform synthesizer.
    Generates 44.1kHz 16-bit PCM RIFF WAV audio in-memory for authentic
    Wall-E robotic expressions, beeps, chimes, and vocalizations.
    """

    SAMPLE_RATE = 44100

    @classmethod
    def _create_wav(cls, samples: list[float]) -> bytes:
        """Converts float samples [-1.0 to 1.0] to a complete 16-bit PCM WAV byte stream."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(cls.SAMPLE_RATE)
            # Clip and pack into 16-bit signed integers
            raw_bytes = bytearray()
            for s in samples:
                val = max(-1.0, min(1.0, s))
                int_val = int(val * 32767.0)
                raw_bytes.extend(struct.pack("<h", int_val))
            wf.writeframes(raw_bytes)
        return buffer.getvalue()

    @classmethod
    def generate_sound(cls, sound_name: str) -> bytes:
        """Generates WAV byte stream for a named Wall-E sound preset."""
        s = sound_name.lower().strip()
        sr = cls.SAMPLE_RATE

        if s in ("startup", "boot"):
            # Iconic warm ascending major triad chord (C5 -> E5 -> G5 -> C6)
            freqs = [523.25, 659.25, 783.99, 1046.50]
            duration = 1.2
            total_samples = int(sr * duration)
            samples = [0.0] * total_samples

            for i, f in enumerate(freqs):
                start_sample = int(i * 0.16 * sr)
                note_len = int(0.7 * sr)
                for j in range(note_len):
                    idx = start_sample + j
                    if idx >= total_samples:
                        break
                    t = j / sr
                    env = math.exp(-4.5 * (t / 0.7)) * min(1.0, t * 80)
                    wave_val = (
                        0.6 * math.sin(2 * math.pi * f * t) +
                        0.25 * math.sin(4 * math.pi * f * t) +
                        0.15 * math.sin(6 * math.pi * f * t)
                    )
                    samples[idx] += wave_val * env * 0.28
            return cls._create_wav(samples)

        elif s in ("shutdown", "powerdown", "sleep"):
            # Descending resonant motor/power-whir fade
            duration = 0.9
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                f = 820.0 * (1.0 - t / duration) ** 1.8 + 80.0
                env = (1.0 - t / duration) ** 1.5 * min(1.0, t * 50)
                w = 0.7 * math.sin(2 * math.pi * f * t) + 0.3 * math.sin(4 * math.pi * f * t)
                samples.append(w * env * 0.65)
            return cls._create_wav(samples)

        elif s in ("happy", "joy", "cheer"):
            # Fast cheerful ascending two-tone chirp
            duration = 0.38
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                if t < 0.16:
                    f = 750.0 + (t / 0.16) * 600.0
                    env = math.sin(math.pi * (t / 0.16))
                else:
                    t2 = t - 0.16
                    f = 1100.0 + (t2 / 0.22) * 550.0
                    env = math.sin(math.pi * (t2 / 0.22))
                w = math.sin(2 * math.pi * f * t) + 0.2 * math.sin(4 * math.pi * f * t)
                samples.append(w * env * 0.7)
            return cls._create_wav(samples)

        elif s in ("curious", "question", "inquire"):
            # Wall-E questioning upward lilt with slight vibrato
            duration = 0.42
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                vibrato = math.sin(2 * math.pi * 14.0 * t) * 35.0
                f = 460.0 + (t / duration) ** 1.4 * 650.0 + vibrato
                env = math.sin(math.pi * (t / duration)) ** 0.8
                w = 0.8 * math.sin(2 * math.pi * f * t) + 0.2 * math.sin(3 * math.pi * f * t)
                samples.append(w * env * 0.68)
            return cls._create_wav(samples)

        elif s in ("alert", "alarm", "danger", "cliff"):
            # Urgent two-tone rapid warning siren beeps
            duration = 0.45
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                cycle = int(t * 12.0) % 2
                f = 1380.0 if cycle == 0 else 1050.0
                env = min(1.0, math.sin(math.pi * ((t * 12.0) % 1.0)) * 1.5)
                # Slightly edgy pulse
                w = 0.7 * math.sin(2 * math.pi * f * t) + 0.3 * (1.0 if math.sin(2 * math.pi * f * t) > 0 else -1.0)
                samples.append(w * env * 0.75)
            return cls._create_wav(samples)

        elif s in ("sad", "whimper", "mourn"):
            # Melancholic descending slide with slow quiver
            duration = 0.65
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                tremolo = 1.0 + 0.15 * math.sin(2 * math.pi * 9.0 * t)
                f = 580.0 * (1.0 - 0.55 * (t / duration))
                env = (1.0 - t / duration) * min(1.0, t * 40)
                w = math.sin(2 * math.pi * f * t)
                samples.append(w * env * tremolo * 0.6)
            return cls._create_wav(samples)

        elif s in ("excited", "thrilled", "celebrate"):
            # Rapid 4-note ascending arpeggio fanfare
            freqs = [659.25, 830.61, 987.77, 1318.51]
            duration = 0.45
            total_samples = int(sr * duration)
            samples = [0.0] * total_samples
            step = 0.09
            for i, f in enumerate(freqs):
                start = int(i * step * sr)
                dur = int(0.18 * sr)
                for j in range(dur):
                    idx = start + j
                    if idx >= total_samples:
                        break
                    t = j / sr
                    env = math.sin(math.pi * (j / dur))
                    w = 0.75 * math.sin(2 * math.pi * f * t) + 0.25 * math.sin(4 * math.pi * f * t)
                    samples[idx] += w * env * 0.35
            return cls._create_wav(samples)

        elif s in ("love", "affection", "coo", "purr"):
            # Soft warm harmonic purr chord (F4 + C5)
            duration = 0.55
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                trem = 1.0 + 0.18 * math.sin(2 * math.pi * 12.0 * t)
                w1 = math.sin(2 * math.pi * 349.23 * t)
                w2 = math.sin(2 * math.pi * 523.25 * t)
                env = math.sin(math.pi * (t / duration)) ** 1.2
                samples.append((0.55 * w1 + 0.45 * w2) * env * trem * 0.65)
            return cls._create_wav(samples)

        elif s in ("bump", "collision", "boing"):
            # Rubbery impact boing (fast downward pitch plunge)
            duration = 0.28
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                f = 420.0 * math.exp(-12.0 * t) + 95.0
                env = math.exp(-9.0 * t)
                w = math.sin(2 * math.pi * f * t) + 0.3 * math.sin(3 * math.pi * f * t)
                samples.append(w * env * 0.8)
            return cls._create_wav(samples)

        elif s in ("wink", "twinkle", "blip"):
            # Delicate high-frequency twinkle
            duration = 0.16
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                f = 1750.0 + (t / duration) * 400.0
                env = math.sin(math.pi * (t / duration))
                w = math.sin(2 * math.pi * f * t)
                samples.append(w * env * 0.6)
            return cls._create_wav(samples)

        elif s in ("confused", "puzzled"):
            # Asymmetrical warbling slide
            duration = 0.4
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                f = 410.0 + math.sin(2 * math.pi * 16.0 * t) * 140.0
                env = math.sin(math.pi * (t / duration))
                w = math.sin(2 * math.pi * f * t)
                samples.append(w * env * 0.65)
            return cls._create_wav(samples)

        elif s in ("angry", "grumpy"):
            # Low buzz / raspberry
            duration = 0.35
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                f = 145.0
                w = 1.0 if math.sin(2 * math.pi * f * t) > 0 else -1.0
                env = math.sin(math.pi * (t / duration))
                samples.append(w * env * 0.5)
            return cls._create_wav(samples)

        else:
            # Default soft computing blip / thinking
            duration = 0.12
            total_samples = int(sr * duration)
            samples = []
            for i in range(total_samples):
                t = i / sr
                f = 880.0
                env = math.sin(math.pi * (t / duration))
                w = math.sin(2 * math.pi * f * t)
                samples.append(w * env * 0.55)
            return cls._create_wav(samples)


class VoiceEngine:
    """
    Unified voice synthesizer & audio player.
    Supports offline/online Text-to-Speech (TTS), procedural Wall-E sounds,
    and native playback of Alpha's authentic voice ('Voice 1.mp3').
    """

    def __init__(self, voice_enabled: bool = True):
        self.voice_enabled = voice_enabled
        self.is_speaking = False
        self._sapi_voice = None
        self._lock = threading.Lock()

        # Hooks for eye animation synchronization during speech
        self.on_speech_start: Optional[Callable[[], None]] = None
        self.on_speech_end: Optional[Callable[[], None]] = None

        self._init_tts()

    def _init_tts(self) -> None:
        """Initializes system TTS (Windows SAPI5 or Linux espeak)."""
        if os.name == "nt":
            try:
                import win32com.client
                self._sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
                # Speed up slightly (+2) for cheerful, brisk robotic cadence
                self._sapi_voice.Rate = 2
                self._sapi_voice.Volume = 95
                print("[VoiceEngine] Windows SAPI5 Speech Engine Initialized.")
            except Exception as e:
                print(f"[VoiceEngine] Could not initialize SAPI5: {e}")
        elif IS_RASPBERRY_PI or os.name == "posix":
            print("[VoiceEngine] Linux/Pi Audio Engine active (using aplay & espeak).")

    def play_alpha_voice(self, async_play: bool = True) -> bool:
        """
        Plays Alpha's authentic voice clip ('Hello, I'm Alpha. I am your pet.').
        Synchronizes with eye speech pulse callbacks.
        """
        if not ALPHA_VOICE_PATH.exists():
            print(f"[VoiceEngine] Alpha voice clip not found at {ALPHA_VOICE_PATH}. Falling back to chirp.")
            self.play_sound("happy", async_play=async_play)
            return False

        def _play_worker():
            if self.on_speech_start:
                self.on_speech_start()
            mp3_abs = str(ALPHA_VOICE_PATH.resolve())
            success = False
            if os.name == "nt":
                success = _play_mp3_windows(mp3_abs)
            else:
                success = _play_mp3_linux(mp3_abs)
            if not success:
                self.play_sound("happy", async_play=False)
            if self.on_speech_end:
                self.on_speech_end()

        if async_play:
            threading.Thread(target=_play_worker, daemon=True).start()
        else:
            _play_worker()
        return True

    def play_sound(self, sound_name: str, async_play: bool = True) -> None:
        """Plays a procedural Wall-E sound effect or Alpha's authentic voice clip."""
        s = sound_name.lower().strip()
        if s in ("alpha_voice", "voice", "voice1", "voice_1", "intro", "alpha", "pet"):
            self.play_alpha_voice(async_play=async_play)
            return

        wav_bytes = WallESoundSynthesizer.generate_sound(sound_name)

        def _play():
            try:
                if os.name == "nt":
                    import winsound
                    # In dedicated background worker thread, SND_MEMORY plays cleanly without blocking caller
                    winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
                else:
                    # On Linux/Pi, stream raw WAV to aplay
                    import subprocess
                    proc = subprocess.Popen(
                        ["aplay", "-q"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    proc.communicate(input=wav_bytes)
            except Exception as e:
                print(f"[VoiceEngine] Error playing sound '{sound_name}': {e}")

        if async_play:
            threading.Thread(target=_play, daemon=True).start()
        else:
            _play()

    def _get_emotion_prosody(self, emotion: Optional[Emotion | str]) -> Tuple[str, str, str]:
        """Resolves (pitch, rate, chime_sound) based on current emotion."""
        if not emotion:
            return ("+14Hz", "+4%", "happy")
        emo_str = emotion.value if isinstance(emotion, Emotion) else str(emotion).lower().strip()
        config = EMOTION_PROSODY.get(emo_str, EMOTION_PROSODY["happy"])
        return (config["pitch"], config["rate"], config["sound"])

    def get_neural_speech_file(
        self,
        text: str,
        emotion: Optional[Emotion | str] = None,
        voice: str = DEFAULT_NEURAL_VOICE
    ) -> Optional[Path]:
        """
        Synthesizes high-fidelity neural MP3 speech matching Alpha's Voice 1 timbre.
        Uses disk caching for sub-10ms retrieval on repeated phrases.
        Returns Path to the cached MP3 file.
        """
        clean_text = sanitize_speech_text(text)
        if not clean_text:
            return None

        # If text is Alpha's signature intro, return original Voice 1.mp3 asset
        lower = clean_text.lower()
        if (("alpha" in lower and ("pet" in lower or "your pet" in lower)) or
            "hello, i'm alpha" in lower or "hello i'm alpha" in lower):
            if ALPHA_VOICE_PATH.exists():
                return ALPHA_VOICE_PATH

        pitch, rate, _ = self._get_emotion_prosody(emotion)
        cache_key = hashlib.md5(f"{voice}_{pitch}_{rate}_{clean_text}".encode("utf-8")).hexdigest()
        cache_file = TTS_CACHE_DIR / f"{cache_key}.mp3"

        if cache_file.exists() and cache_file.stat().st_size > 500:
            return cache_file

        try:
            import edge_tts

            async def _synthesize():
                comm = edge_tts.Communicate(clean_text, voice, pitch=pitch, rate=rate)
                await comm.save(str(cache_file))

            # Safely handle existing event loops (e.g. inside tornado / asyncio servers)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    pool.submit(asyncio.run, _synthesize()).result(timeout=6.0)
            else:
                asyncio.run(_synthesize())

            if cache_file.exists() and cache_file.stat().st_size > 500:
                return cache_file
        except Exception as e:
            print(f"[VoiceEngine] Neural speech synthesis notice: {e}")

        return None

    def get_neural_speech_bytes(
        self,
        text: str,
        emotion: Optional[Emotion | str] = None,
        voice: str = DEFAULT_NEURAL_VOICE
    ) -> bytes:
        """
        Returns high-fidelity neural MP3 bytes for the given text and emotion.
        Suitable for HTTP streaming to the web simulator.
        """
        mp3_path = self.get_neural_speech_file(text, emotion, voice=voice)
        if mp3_path and mp3_path.exists():
            try:
                with open(mp3_path, "rb") as f:
                    return f.read()
            except Exception:
                pass
        return b""

    def stop_speaking(self) -> None:
        """Instantly interrupts any ongoing speech or audio playback (barge-in support)."""
        self.is_speaking = False
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.winmm.mciSendStringW("close all", None, 0, 0)
            except Exception:
                pass
            if self._sapi_voice:
                try:
                    self._sapi_voice.Speak("", 2)  # SVSFPurgeBeforeSpeak
                except Exception:
                    pass
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:
                pass
        elif IS_RASPBERRY_PI or os.name == "posix":
            try:
                import subprocess
                subprocess.run(["pkill", "-9", "-f", "aplay|mpg123|cvlc|espeak"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        if self.on_speech_end:
            try:
                self.on_speech_end()
            except Exception:
                pass

    def speak(
        self,
        text: str,
        emotion: Optional[Emotion | str] = None,
        with_chirp: bool = True,
        async_speech: bool = True
    ) -> None:
        """
        Speaks text through calibrated neural TTS (matching Voice 1.mp3)
        with Wall-E emotive chimes, pupil lip-sync callbacks, and offline SAPI5/espeak fallback.
        """
        if not self.voice_enabled or not text:
            return

        clean_text = sanitize_speech_text(text)
        _, _, sound_preset = self._get_emotion_prosody(emotion)

        def _speak_worker():
            with self._lock:
                self.is_speaking = True
                try:
                    # 1. Play emotive Wall-E chime
                    if with_chirp:
                        self.play_sound(sound_preset, async_play=False)
                        time.sleep(0.06)

                    # 2. Trigger speech start hook (e.g. eye pulse)
                    if self.on_speech_start:
                        self.on_speech_start()

                    # 3. Primary: High-Fidelity Neural Speech (matching Voice 1)
                    neural_mp3 = self.get_neural_speech_file(clean_text, emotion=emotion)
                    played_neural = False
                    if neural_mp3 and neural_mp3.exists():
                        abs_path = str(neural_mp3.resolve())
                        if os.name == "nt":
                            played_neural = _play_mp3_windows(abs_path)
                        else:
                            played_neural = _play_mp3_linux(abs_path)

                    # 4. Secondary: Graceful Offline Fallback (Windows SAPI5 / Linux espeak)
                    if not played_neural:
                        if os.name == "nt":
                            if self._sapi_voice:
                                self._sapi_voice.Speak(clean_text, 0)
                            else:
                                import subprocess
                                escaped = clean_text.replace("'", "''").replace('"', '`"')
                                ps_cmd = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate = 2; $s.Speak('{escaped}')"
                                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        elif IS_RASPBERRY_PI or os.name == "posix":
                            import subprocess
                            subprocess.run(
                                ["espeak", "-v", "en+f4", "-p", "72", "-s", "165", clean_text],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                        else:
                            time.sleep(len(clean_text) * 0.05)
                except Exception as e:
                    print(f"[VoiceEngine] Speak error: {e}")
                finally:
                    self.is_speaking = False
                    if self.on_speech_end:
                        self.on_speech_end()

        if async_speech:
            threading.Thread(target=_speak_worker, daemon=True).start()
        else:
            _speak_worker()

    def get_wav_bytes(self, sound_name: str) -> bytes:
        """Returns WAV bytes for a sound preset, suitable for HTTP streaming."""
        return WallESoundSynthesizer.generate_sound(sound_name)

    @staticmethod
    def get_alpha_voice_bytes() -> bytes:
        """Returns raw MP3 bytes of Alpha's authentic voice."""
        if ALPHA_VOICE_PATH.exists():
            with open(ALPHA_VOICE_PATH, "rb") as f:
                return f.read()
        return b""
