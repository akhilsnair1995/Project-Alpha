"""
Project Alpha: Expressive Voice Cortex & Procedural Sound Synthesis Engine.
Generates authentic Wall-E procedural sound effects (chirps, trills, sirens, beeps)
and provides cross-platform offline Text-to-Speech (TTS) coordinated with eye animations.
"""

import os
import io
import wave
import struct
import math
import time
import threading
from typing import Optional, Callable, Dict, Any
from pathlib import Path

from core.config import DATA_DIR, IS_RASPBERRY_PI
from core.eye_animator import Emotion

SOUNDS_DIR = DATA_DIR / "sounds"
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)


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
    Supports offline/online Text-to-Speech (TTS) and procedural Wall-E sounds.
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
                # Speed up slightly (+1 or +2) for cheerful, brisk robotic cadence
                self._sapi_voice.Rate = 2
                self._sapi_voice.Volume = 95
                print("[VoiceEngine] Windows SAPI5 Speech Engine Initialized.")
            except Exception as e:
                print(f"[VoiceEngine] Could not initialize SAPI5: {e}")
        elif IS_RASPBERRY_PI or os.name == "posix":
            print("[VoiceEngine] Linux/Pi Audio Engine active (using aplay & espeak).")

    def play_sound(self, sound_name: str, async_play: bool = True) -> None:
        """Plays a procedural Wall-E sound effect (cross-platform)."""
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

    def speak(
        self,
        text: str,
        emotion: Optional[Emotion | str] = None,
        with_chirp: bool = True,
        async_speech: bool = True
    ) -> None:
        """
        Speaks text through TTS with emotional chimes and synchronized callbacks.
        """
        if not self.voice_enabled or not text:
            return

        clean_text = text.replace("*", "").replace("#", "").replace("_", "").strip()

        # Determine sound chime based on emotion
        sound_preset = "happy"
        if emotion:
            emo_str = emotion.value if isinstance(emotion, Emotion) else str(emotion).lower()
            if emo_str in ("curious", "analyzing"):
                sound_preset = "curious"
            elif emo_str in ("alert", "surprised"):
                sound_preset = "alert"
            elif emo_str in ("excited", "joy"):
                sound_preset = "excited"
            elif emo_str in ("sad",):
                sound_preset = "sad"
            elif emo_str in ("love",):
                sound_preset = "love"
            elif emo_str in ("wink",):
                sound_preset = "wink"
            elif emo_str in ("confused",):
                sound_preset = "confused"

        def _speak_worker():
            with self._lock:
                self.is_speaking = True
                try:
                    # 1. Play emotive chime
                    if with_chirp:
                        self.play_sound(sound_preset, async_play=False)
                        time.sleep(0.08)

                    # 2. Trigger speech start hook (e.g. eye pulse)
                    if self.on_speech_start:
                        self.on_speech_start()

                    # 3. Speech execution
                    if os.name == "nt" and self._sapi_voice:
                        # 0 = SVSFDefault (synchronous in this worker thread)
                        self._sapi_voice.Speak(clean_text, 0)
                    elif IS_RASPBERRY_PI or os.name == "posix":
                        import subprocess
                        # espeak with female/cheerful robotic pitch
                        subprocess.run(
                            ["espeak", "-v", "en+f4", "-p", "72", "-s", "165", clean_text],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    else:
                        print(f"[VoiceEngine:Simulated] Speaking: {clean_text}")
                        time.sleep(len(clean_text) * 0.05)
                except Exception as e:
                    print(f"[VoiceEngine] TTS error: {e}")
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
