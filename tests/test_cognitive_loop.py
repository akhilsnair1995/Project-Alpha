"""
Unit tests for Project Alpha: Gemini Cognitive Loop (The Living Conscious Mind).
Verifies world snapshot construction, directive application, action grammar,
speech output, emotion mapping, and fallback behavior.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from core.neural_engine import NeuralMindEngine
from core.cognitive_loop import GeminiCognitiveLoop


class TestGeminiCognitiveLoop(unittest.TestCase):

    def setUp(self):
        self.engine = NeuralMindEngine()
        self.loop = GeminiCognitiveLoop(engine=self.engine, cycle_interval=1.0)
        self.engine.attach_cognitive_loop(self.loop)

    def tearDown(self):
        if self.loop.is_active:
            self.loop.stop()

    def test_init_and_attributes(self):
        self.assertEqual(self.loop.engine, self.engine)
        self.assertEqual(self.loop.cycle_interval, 1.0)
        self.assertFalse(self.loop.is_active)
        self.assertIsNone(self.loop.last_user_message)
        self.assertEqual(self.loop.last_user_time, 0.0)

    def test_set_active_and_notify_user(self):
        self.loop.set_active(True)
        self.assertTrue(self.loop.is_active)

        self.loop.notify_user_speech("Hey Alpha, what are you doing?")
        self.assertEqual(self.loop.last_user_message, "Hey Alpha, what are you doing?")
        self.assertGreater(self.loop.last_user_time, 0.0)

        status = self.loop.get_status()
        self.assertTrue(status["is_active"])

    def test_build_world_snapshot(self):
        self.engine.body.x = 200.0
        self.engine.body.y = 150.0
        self.engine.body.heading = 90.0
        self.engine.body.pan = 10.0
        self.engine.body.tilt = -5.0
        self.loop.notify_user_speech("Hello Alpha")

        snapshot = self.loop._build_world_snapshot()

        self.assertIn("robot", snapshot)
        self.assertEqual(snapshot["robot"]["x"], 200.0)
        self.assertEqual(snapshot["robot"]["y"], 150.0)
        self.assertEqual(snapshot["robot"]["heading"], 90.0)
        self.assertEqual(snapshot["robot"]["pan"], 10.0)
        self.assertEqual(snapshot["robot"]["tilt"], -5.0)

        self.assertIn("visible_items", snapshot)
        self.assertIn("discovered_objects", snapshot)
        self.assertIn("emotion", snapshot)
        self.assertIn("drives", snapshot)
        self.assertIn("traits", snapshot)
        self.assertIn("owner", snapshot)
        self.assertEqual(snapshot["owner"]["last_message"], "Hello Alpha")

    def test_apply_directive_scan_and_head_look(self):
        directive = {
            "action": "SCAN_LEFT",
            "target": None,
            "pan_target": -45.0,
            "tilt_target": -12.0,
            "speech": None,
            "inner_thought": "Surveying the left desk boundary.",
            "emotion": "curious",
            "sound_cue": "curious"
        }
        self.loop._apply_directive(directive)

        self.assertEqual(self.engine.consciousness.current_thought, "Surveying the left desk boundary.")
        self.assertEqual(self.engine.current_behavior, "EXPLORE_ROAM")
        self.assertEqual(self.engine.explore_substate, "SCANNING")
        self.assertEqual(self.engine.body.target_pan_goal, -45.0)
        self.assertEqual(self.engine.body.target_tilt_goal, -12.0)

    def test_apply_directive_approach_and_speech(self):
        directive = {
            "action": "APPROACH",
            "target": "Coffee Mug",
            "pan_target": 0.0,
            "tilt_target": -10.0,
            "speech": "Ooh, a Coffee Mug! Let me roll closer.",
            "inner_thought": "Heading over to the mug.",
            "emotion": "excited",
            "sound_cue": "excited"
        }
        self.loop._apply_directive(directive)

        self.assertEqual(self.engine.behavior_target, "Coffee Mug")
        self.assertEqual(self.engine.consciousness.current_thought, "Ooh, a Coffee Mug! Let me roll closer.")
        self.assertTrue(len(self.engine.speech_feedback_queue) > 0)
        feedback = self.engine.speech_feedback_queue[0]
        self.assertEqual(feedback["text"], "Ooh, a Coffee Mug! Let me roll closer.")
        self.assertEqual(feedback["emotion"], "excited")

    def test_apply_directive_greet_akhil(self):
        directive = {
            "action": "GREET",
            "target": "Akhil",
            "pan_target": 0.0,
            "tilt_target": 18.0,
            "speech": "Hello Akhil! *Whirrr-chirp!*",
            "inner_thought": "Checking in on my favorite person.",
            "emotion": "love",
            "sound_cue": "love"
        }
        self.loop._apply_directive(directive)

        self.assertEqual(self.engine.current_behavior, "CHECKING_AKHIL")
        self.assertEqual(self.engine.behavior_target, "Akhil")
        self.assertEqual(self.engine.body.target_tilt_goal, 18.0)

    def test_apply_directive_hold_and_companion_rest(self):
        # HOLD
        self.loop._apply_directive({"action": "HOLD", "inner_thought": "Freezing in place."})
        self.assertEqual(self.engine.current_behavior, "HOLD_POSITION")
        self.assertEqual(self.engine.body.speed, 0.0)

        # COMPANION_REST
        self.loop._apply_directive({"action": "COMPANION_REST", "inner_thought": "Breathing softly nearby."})
        self.assertEqual(self.engine.current_behavior, "COMPANION_IDLE")

    def test_thread_lifecycle_start_and_stop(self):
        self.loop.start()
        self.assertTrue(self.loop.is_active)
        self.assertIsNotNone(self.loop._thread)
        self.assertTrue(self.loop._thread.is_alive())

        self.loop.stop()
        self.assertFalse(self.loop.is_active)
        self.assertFalse(self.loop._thread is not None and self.loop._thread.is_alive())

    @patch("core.cognitive_loop.GeminiCognitiveLoop._call_gemini")
    def test_cognitive_cycle_execution(self, mock_gemini):
        mock_gemini.return_value = {
            "action": "SCAN_RIGHT",
            "target": None,
            "pan_target": 45.0,
            "tilt_target": -10.0,
            "speech": None,
            "inner_thought": "Surveying northeast sector.",
            "emotion": "curious",
            "sound_cue": "curious"
        }

        self.loop._client = MagicMock()
        self.loop.is_active = True

        self.loop._cognitive_cycle()

        self.assertEqual(self.engine.consciousness.current_thought, "Surveying northeast sector.")
        self.assertEqual(self.loop.last_decision["action"], "SCAN_RIGHT")
        self.assertEqual(self.loop._consecutive_failures, 0)


if __name__ == "__main__":
    unittest.main()
