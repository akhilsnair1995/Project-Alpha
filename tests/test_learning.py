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

    def test_action_directive_extraction_and_pronoun_resolution(self):
        """Tests that physical action directives are parsed and pronouns ('that', 'it') resolve from context."""
        brain = HybridBrain(db=self.db, api_key=None)

        # 1. Direct explicit instruction
        d1 = brain._parse_action_directive("Keep an eye on the keys and do not move", "[ACTION: STAY_AND_WATCH | target=Keys] Watching them!")
        self.assertEqual(d1["action"], "STAY_AND_WATCH")
        self.assertEqual(d1["target"], "Keys")

        # 2. Contextual pronoun resolution from recent chat
        self.db.save_chat_message("user", "Where did I put my keys?")
        self.db.save_chat_message("assistant", "Found on work desk.")

        d2 = brain._parse_action_directive("Go and look at that. Do not move. Just look at that and keep an eye on it.", "Understood!")
        self.assertEqual(d2["action"], "STAY_AND_WATCH")
        self.assertEqual(d2["target"], "Keys")

        # 3. Pure hold position directive
        d3 = brain._parse_action_directive("Halt! Freeze! Do not move!", "Stopping now!")
        self.assertEqual(d3["action"], "HOLD_POSITION")

        # 4. Resume roam directive
        d4 = brain._parse_action_directive("Okay Alpha, resume roaming and explore the room", "Exploring now!")
        self.assertEqual(d4["action"], "ROAM")

if __name__ == "__main__":
    unittest.main()
