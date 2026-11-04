"""
Unit Tests for Project Alpha: Dual GC9A01 Expression Engine.
Verifies procedural eye rendering across all 16 emotional states,
gaze clamping, blinking, and emotion parsing.
"""

import unittest
from PIL import Image
from core.eye_animator import DualEyeController, EyeRenderer, Emotion

class TestEyeExpressions(unittest.TestCase):

    def setUp(self):
        self.controller = DualEyeController(hardware_enabled=False)

    def test_all_16_emotions_exist(self):
        expected_emotions = {
            "idle", "happy", "curious", "squint", "wink", "sad",
            "sleepy", "surprised", "alert", "analyzing", "excited",
            "love", "angry", "confused", "skeptical", "offline"
        }
        actual_emotions = {e.value for e in Emotion}
        self.assertEqual(expected_emotions, actual_emotions)

    def test_emotion_from_str_and_aliases(self):
        self.assertEqual(Emotion.from_str("happy"), Emotion.HAPPY)
        self.assertEqual(Emotion.from_str("CURIOUS"), Emotion.CURIOUS)
        self.assertEqual(Emotion.from_str("sleep"), Emotion.SLEEPY)
        self.assertEqual(Emotion.from_str("alarm"), Emotion.ALERT)
        self.assertEqual(Emotion.from_str("heart"), Emotion.LOVE)
        self.assertEqual(Emotion.from_str("grumpy"), Emotion.ANGRY)
        self.assertEqual(Emotion.from_str("unknown_state"), Emotion.IDLE)
        self.assertEqual(Emotion.from_str(""), Emotion.IDLE)

    def test_render_all_emotional_frames(self):
        for emo in Emotion:
            self.controller.set_emotion(emo)
            left_img, right_img = self.controller.render_eyes()
            self.assertIsInstance(left_img, Image.Image)
            self.assertIsInstance(right_img, Image.Image)
            self.assertEqual(left_img.size, (240, 240))
            self.assertEqual(right_img.size, (240, 240))
            self.assertEqual(left_img.mode, "RGB")
            self.assertEqual(right_img.mode, "RGB")

    def test_gaze_clamping(self):
        self.controller.set_gaze(2.5, -3.0)
        state = self.controller.get_state()
        self.assertEqual(state["gaze_x"], 1.0)
        self.assertEqual(state["gaze_y"], -1.0)

        self.controller.set_gaze(-1.5, 0.5)
        state = self.controller.get_state()
        self.assertEqual(state["gaze_x"], -1.0)
        self.assertEqual(state["gaze_y"], 0.5)

    def test_blink_and_wink(self):
        self.controller.blink(duration_sec=0.01)
        self.assertEqual(self.controller.left_eye.blink_ratio, 0.0)
        self.assertEqual(self.controller.right_eye.blink_ratio, 0.0)

        self.controller.wink(is_right_eye=True, duration_sec=0.01)
        self.assertEqual(self.controller.right_eye.blink_ratio, 0.0)

    def test_talking_pulse(self):
        self.controller.talking_pulse(cycles=1)
        self.assertEqual(self.controller.left_eye.blink_ratio, 0.0)

    def test_get_state(self):
        self.controller.set_emotion(Emotion.EXCITED)
        self.controller.set_gaze(0.25, -0.5)
        state = self.controller.get_state()
        self.assertEqual(state["emotion"], "excited")
        self.assertEqual(state["gaze_x"], 0.25)
        self.assertEqual(state["gaze_y"], -0.5)
        self.assertEqual(len(state["available_emotions"]), 16)

if __name__ == "__main__":
    unittest.main()
