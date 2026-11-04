"""
Unit Tests for Autonomous Learning Engine, Spatial Object Tracking, and Local Gemma.
"""

import unittest
import tempfile
from pathlib import Path

from core.database import AlphaDatabase
from core.learning_engine import AutonomousLearningEngine
from core.local_gemma import LocalGemmaEngine
from core.gemini_brain import HybridBrain

class TestLearningAndGemma(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = Path(self.temp_dir.name) / "test_learn.db"
        self.db = AlphaDatabase(db_path=self.test_db_path)
        self.learning_engine = AutonomousLearningEngine(db=self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_conversational_fact_extraction(self):
        """Tests that user preferences, projects, and locations are learned automatically."""
        # Test 1: Preference
        learned = self.learning_engine.extract_and_learn_from_text("I love dark roast coffee and chai")
        self.assertTrue(any(cat == "preference" for cat, _ in learned))

        # Test 2: Project
        learned = self.learning_engine.extract_and_learn_from_text("I am working on Project Alpha rover")
        self.assertTrue(any(cat == "project" for cat, _ in learned))

        # Test 3: Location
        learned = self.learning_engine.extract_and_learn_from_text("I live in Kerala, India")
        self.assertTrue(any(cat == "location" for cat, _ in learned))

        # Verify they are stored in SQLite
        facts = self.db.get_user_facts()
        self.assertGreaterEqual(len(facts), 3)

    def test_person_introduction_and_ownership_learning(self):
        """Tests that new persons and object ownership associations are extracted and remembered."""
        # Introduce a guest
        learned = self.learning_engine.extract_and_learn_from_text("This is my friend Sarah")
        self.assertTrue(any(cat == "person_introduction" for cat, _ in learned))
        sarah = self.db.get_person_by_name("Sarah")
        self.assertIsNotNone(sarah)

        # Mention an object belonging to Sarah
        learned_own = self.learning_engine.extract_and_learn_from_text("This is Sarah's water bottle")
        self.assertTrue(any(cat == "object_ownership" for cat, _ in learned_own))
        bottle = self.db.find_objects("water bottle")
        self.assertEqual(len(bottle), 1)
        self.assertEqual(bottle[0]["owner_name"], "Sarah")

    def test_spatial_object_tracking_and_movement(self):
        """Tests that objects spotted while roaming are tracked and movements are detected."""
        # 1. Spot keys in Living Room
        sighting1 = self.learning_engine.learn_object_sighting(
            object_name="Car Keys",
            description="Silver ring with black fob",
            room_name="Living Room",
            owner_name="Akhil"
        )
        self.assertFalse(sighting1["moved"])
        self.assertEqual(sighting1["owner"], "Akhil")

        # 2. Later, spot the SAME keys in Work Desk (Moved!)
        sighting2 = self.learning_engine.learn_object_sighting(
            object_name="Car Keys",
            description="Silver ring with black fob on desk",
            room_name="Work Desk",
            owner_name="Akhil"
        )
        self.assertTrue(sighting2["moved"])
        self.assertEqual(sighting2["previous_room"], "Living Room")

        # 3. Ask where the keys are
        recall_text = self.learning_engine.recall_object_location("keys")
        self.assertIsNotNone(recall_text)
        self.assertIn("Work Desk", recall_text)
        self.assertIn("Akhil's", recall_text)

        # 4. Spot Sarah's notebook in Lab
        self.learning_engine.learn_object_sighting(
            object_name="Notebook",
            description="Spiral bound math notes",
            room_name="Lab",
            owner_name="Sarah"
        )
        sarah_recall = self.learning_engine.recall_object_location("Sarah's Notebook")
        self.assertIsNotNone(sarah_recall)
        self.assertIn("Sarah's", sarah_recall)
        self.assertIn("Lab", sarah_recall)

    def test_curiosity_scoring(self):
        """Tests curiosity scoring for brand new vs familiar objects."""
        # Novel object never seen before
        score_new = self.learning_engine.evaluate_curiosity("Mystery Box", "Living Room")
        self.assertEqual(score_new, 1.0)

        # Record object in Living Room
        self.learning_engine.learn_object_sighting("Backpack", "Blue bag", "Living Room")

        # Same object in same room -> low curiosity
        score_familiar = self.learning_engine.evaluate_curiosity("Backpack", "Living Room")
        self.assertLess(score_familiar, 0.5)

    def test_local_gemma_fallback_generation(self):
        """Tests that local Gemma engine generates coherent offline responses."""
        engine = LocalGemmaEngine()
        reply = engine.generate("Hello Alpha!", system_instruction="You are Alpha")
        self.assertIsInstance(reply, str)
        self.assertGreater(len(reply), 5)

if __name__ == "__main__":
    unittest.main()
