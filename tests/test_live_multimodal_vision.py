import unittest
import base64
try:
    import numpy as np
    import cv2
    HAS_CV2_NUMPY = True
except ImportError:
    HAS_CV2_NUMPY = False

from core.gemini_brain import HybridBrain
from core.eye_animator import Emotion

@unittest.skipUnless(HAS_CV2_NUMPY, "Requires cv2 and numpy")
class TestLiveMultimodalVision(unittest.TestCase):
    def setUp(self):
        self.brain = HybridBrain()
        # Create a sample test frame (320x240 RGB)
        self.test_img = np.zeros((240, 320, 3), dtype=np.uint8)
        # Draw a bright circle (simulating a face/activity)
        cv2.circle(self.test_img, (160, 120), 50, (200, 180, 150), -1)
        _, buf = cv2.imencode(".jpg", self.test_img)
        self.jpeg_bytes = buf.tobytes()

    def test_react_to_live_visual_structure(self):
        res = self.brain.react_to_live_visual(
            self.jpeg_bytes,
            context_metadata={"event": "companion_test_look", "distance": "optimal"}
        )
        self.assertIn("speech", res)
        self.assertIn("emotion", res)
        self.assertIn("sound", res)
        self.assertIn("gesture", res)
        self.assertIn("inner_thought", res)
        self.assertIn("num_persons", res)
        self.assertIn("detected_objects", res)
        self.assertIn("identified_persons", res)
        self.assertIsInstance(res["emotion"], Emotion)
        self.assertTrue(len(res["speech"]) > 0)
        # Check that no banned robotic jargon appears in spoken speech
        banned = ["circuits", "sensors", "protocol", "acknowledged", "optimal", "charging cycle"]
        for b in banned:
            self.assertNotIn(b, res["speech"].lower())

    def test_react_to_live_visual_offline_fallback(self):
        # Even with empty bytes, it should gracefully fall back to organic stimulus
        res = self.brain.react_to_live_visual(b"", context_metadata={"event": "sustained_contact"})
        self.assertIn("speech", res)
        self.assertIn("emotion", res)

    def test_ownership_chat_query_recall(self):
        # Register a person and their object
        self.brain.db.record_discovered_object(
            name="Coffee Mug",
            description="Ceramic mug with chai",
            room_name="Work Desk",
            owner_name="Akhil"
        )
        self.brain.db.record_discovered_object(
            name="Blue Backpack",
            description="School bag",
            room_name="Living Room",
            owner_name="John"
        )

        # Ask whose mug it is
        res_whose = self.brain.chat_with_emotion("Whose coffee mug is this?")
        self.assertIn("Akhil", res_whose["reply"])

        # Ask where John's backpack is
        res_where = self.brain.chat_with_emotion("Where is John's backpack?")
        self.assertIn("Living Room", res_where["reply"])
        self.assertIn("John's", res_where["reply"])

if __name__ == "__main__":
    unittest.main()
