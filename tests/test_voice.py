"""
Unit Tests for Project Alpha: Voice Engine & Procedural Sound Synthesis.
Verifies WAV generation across all Wall-E sound presets, TTS coordination,
and emotional sentiment classification.
"""

import unittest
import wave
import io
from core.voice_engine import VoiceEngine, WallESoundSynthesizer
from core.gemini_brain import HybridBrain
from core.eye_animator import Emotion
from core.motion_controller import MotionController

class TestVoiceAndSoundEngine(unittest.TestCase):

    def setUp(self):
        self.voice = VoiceEngine(voice_enabled=True)
        self.motion = MotionController(hardware_enabled=False)

    def test_synthesize_all_sound_presets(self):
        presets = [
            "startup", "shutdown", "happy", "curious", "alert",
            "excited", "love", "sad", "bump", "wink", "confused",
            "angry", "thinking"
        ]
        for preset in presets:
            wav_bytes = WallESoundSynthesizer.generate_sound(preset)
            self.assertIsInstance(wav_bytes, bytes)
            self.assertGreater(len(wav_bytes), 1000)

            # Verify it is a valid RIFF WAV
            buffer = io.BytesIO(wav_bytes)
            with wave.open(buffer, "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)  # 16-bit
                self.assertEqual(wf.getframerate(), 44100)
                self.assertGreater(wf.getnframes(), 0)

    def test_voice_engine_sound_generation(self):
        wav = self.voice.get_wav_bytes("happy")
        self.assertTrue(wav.startswith(b"RIFF"))

    def test_emotion_and_sound_parsing(self):
        brain = HybridBrain()

        # Explicit tag parsing
        emo, text, sound = brain._parse_emotion_and_text("[EMOTION: EXCITED] Look what I found!")
        self.assertEqual(emo, Emotion.EXCITED)
        self.assertEqual(text, "Look what I found!")
        self.assertEqual(sound, "excited")

        emo, text, sound = brain._parse_emotion_and_text("[EMOTION: ALERT] Warning! Edge detected.")
        self.assertEqual(emo, Emotion.ALERT)
        self.assertEqual(text, "Warning! Edge detected.")
        self.assertEqual(sound, "alert")

        emo, text, sound = brain._parse_emotion_and_text("[EMOTION: LOVE] You are my best friend!")
        self.assertEqual(emo, Emotion.LOVE)
        self.assertEqual(sound, "love")

        # Heuristic fallback classification
        emo, text, sound = brain._parse_emotion_and_text("I love exploring with you today.")
        self.assertEqual(emo, Emotion.LOVE)
        self.assertEqual(sound, "love")

        emo, text, sound = brain._parse_emotion_and_text("Where are the car keys?")
        self.assertEqual(emo, Emotion.CURIOUS)
        self.assertEqual(sound, "curious")

        emo, text, sound = brain._parse_emotion_and_text("Danger! Cliff ahead!")
        self.assertEqual(emo, Emotion.ALERT)
        self.assertEqual(sound, "alert")

    def test_motion_express_emotion(self):
        # Ensure express_emotion does not throw for any emotion
        for emo in Emotion:
            self.motion.express_emotion(emo)

    def test_alpha_voice_asset_and_playback(self):
        """Verifies Alpha's authentic voice clip exists and can be retrieved."""
        from core.config import ALPHA_VOICE_PATH
        self.assertTrue(ALPHA_VOICE_PATH.exists())
        voice_bytes = self.voice.get_alpha_voice_bytes()
        self.assertGreater(len(voice_bytes), 1000)
        self.assertTrue(voice_bytes.startswith(b"ID3"))

    def test_neural_speech_synthesis_and_caching(self):
        """Verifies neural TTS generates MP3 bytes and caches them for fast retrieval."""
        test_phrase = "Testing neural companion voice for Alpha."
        audio_bytes = self.voice.get_neural_speech_bytes(test_phrase, emotion=Emotion.HAPPY)
        self.assertIsInstance(audio_bytes, bytes)
        self.assertGreater(len(audio_bytes), 2000)
        # Verify file exists in disk cache
        cached_file = self.voice.get_neural_speech_file(test_phrase, emotion=Emotion.HAPPY)
        self.assertIsNotNone(cached_file)
        self.assertTrue(cached_file.exists())
        # Subsequent retrieval must be fast and identical
        cached_bytes = self.voice.get_neural_speech_bytes(test_phrase, emotion=Emotion.HAPPY)
        self.assertEqual(audio_bytes, cached_bytes)

    def test_intro_phrase_maps_to_voice_1(self):
        """Verifies that Alpha's iconic intro phrases cleanly map to Voice 1 asset."""
        f1 = self.voice.get_neural_speech_file("Hello, I'm Alpha. I am your pet.")
        from core.config import ALPHA_VOICE_PATH
        self.assertEqual(f1, ALPHA_VOICE_PATH)

if __name__ == "__main__":
    unittest.main()
