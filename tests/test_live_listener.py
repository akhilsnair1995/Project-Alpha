"""
tests/test_live_listener.py
Unit tests for Alpha's Live Background Microphone Listener, VAD,
and natural speech sanitization.
"""

import io
import wave
import unittest
import numpy as np

from core.voice_engine import VoiceEngine, sanitize_speech_text
from core.live_listener import LiveMicrophoneListener
from core.eye_animator import Emotion


class TestNaturalSpeechSanitization(unittest.TestCase):
    def test_sanitize_emojis_and_stage_directions(self):
        raw = "[EMOTION: HAPPY] *wiggles tracks joyfully* Hey Akhil! 😊 How is your coding going? *chirp* ❤️"
        cleaned = sanitize_speech_text(raw)
        self.assertEqual(cleaned, "Hey Akhil! How is your coding going?")

    def test_sanitize_markdown_and_actions(self):
        raw = "**Beep boop!** I found your (blue backpack) under the #desk! *happy chirp*"
        cleaned = sanitize_speech_text(raw)
        self.assertEqual(cleaned, "Beep boop! I found your under the desk!")

    def test_sanitize_clean_dialogue_unaltered(self):
        raw = "Hello! I am Alpha, your desktop companion."
        cleaned = sanitize_speech_text(raw)
        self.assertEqual(cleaned, raw)

    def test_sanitize_empty_or_none(self):
        self.assertEqual(sanitize_speech_text(""), "")
        self.assertEqual(sanitize_speech_text(None), "")


class TestLiveMicrophoneListener(unittest.TestCase):
    def setUp(self):
        self.voice = VoiceEngine(voice_enabled=False)
        self.listener = LiveMicrophoneListener(voice_engine=self.voice)

    def test_vad_speech_energy_calculation(self):
        # Generate silence chunk (RMS ~ 0)
        silence_chunk = np.zeros(1024, dtype=np.int16)
        self.listener._process_audio_chunk(silence_chunk)
        self.assertFalse(self.listener.is_user_speaking)

        # Generate loud speech chunk (16kHz sine wave)
        t = np.linspace(0, 1024 / 16000, 1024, endpoint=False)
        speech_chunk = (0.5 * 32767 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)

        detected = []
        self.listener.on_speech_detected = lambda: detected.append(True)

        self.listener._process_audio_chunk(speech_chunk)
        self.assertTrue(self.listener.is_user_speaking)
        self.assertTrue(len(detected) > 0)

    def test_voice_barge_in_stops_alpha_speaking(self):
        """When Alpha is speaking and user shouts, Alpha immediately stops speaking."""
        self.voice.is_speaking = True
        stopped = []
        self.voice.stop_speaking = lambda: stopped.append(True)

        # Generate very loud barge-in chunk
        t = np.linspace(0, 1024 / 16000, 1024, endpoint=False)
        loud_chunk = (0.8 * 32767 * np.sin(2 * np.pi * 300 * t)).astype(np.int16)

        self.listener._process_audio_chunk(loud_chunk)
        self.assertTrue(len(stopped) > 0)

    def test_finalize_speech_segment_creates_valid_wav(self):
        """Buffered audio chunks are concatenated and formatted as standard 16-bit PCM WAV."""
        # Buffer 1 second of audio
        t = np.linspace(0, 1.0, 16000, endpoint=False)
        tone = (0.3 * 32767 * np.sin(2 * np.pi * 440 * t)).astype(np.int16)
        for i in range(0, 16000, 1024):
            self.listener.audio_buffer.append(tone[i:i+1024])

        self.listener._finalize_speech_segment()
        # Item should be in transcription queue
        self.assertFalse(self.listener._transcribe_queue.empty())
        wav_bytes = self.listener._transcribe_queue.get()
        self.assertTrue(wav_bytes.startswith(b"RIFF"))

        # Verify WAV properties
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 16000)


if __name__ == "__main__":
    unittest.main()
