"""
Unit Tests for Project Alpha: Local SQLite Database & Knowledge Graph.
"""

import unittest
import tempfile
from pathlib import Path
from core.database import AlphaDatabase

class TestAlphaDatabase(unittest.TestCase):

    def setUp(self):
        # Create a temporary in-memory or isolated test database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = Path(self.temp_dir.name) / "test_memory.db"
        self.db = AlphaDatabase(db_path=self.test_db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_learn_and_retrieve_facts(self):
        self.db.learn_fact("preference", "Loves dark roast coffee")
        self.db.learn_fact("project", "Assembling Wall-E rover in Kerala")

        facts = self.db.get_user_facts()
        self.assertEqual(len(facts), 2)
        fact_texts = [f["fact"] for f in facts]
        self.assertIn("Loves dark roast coffee", fact_texts)
        self.assertIn("Assembling Wall-E rover in Kerala", fact_texts)

    def test_record_and_find_discovered_objects(self):
        self.db.record_discovered_object(
            name="Car Keys",
            description="Silver ring with black remote fob",
            room_name="Living Room"
        )
        self.db.record_discovered_object(
            name="Yellow Mug",
            description="Ceramic mug with chai",
            room_name="Work Desk"
        )

        # Search query: "keys"
        results = self.db.find_objects("keys")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Car Keys")
        self.assertEqual(results[0]["room_name"], "Living Room")

        # Search query: "mug"
        results = self.db.find_objects("mug")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Yellow Mug")

    def test_roaming_observation_log(self):
        self.db.log_observation(
            observation="Observed bright sunlight streaming through east window.",
            room_name="Living Room",
            ambient_light="Bright",
            battery_level=7.8
        )
        recent = self.db.get_recent_observations(limit=1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["room_name"], "Living Room")
        self.assertIn("sunlight", recent[0]["observation"])

    def test_system_prompt_context_generation(self):
        self.db.learn_fact("habit", "Works late night on coding projects")
        self.db.log_observation("Desk lamp was left on", room_name="Work Desk")
        context = self.db.generate_system_prompt_context()

        self.assertIn("LOCAL MEMORY & HOUSEHOLD AWARENESS", context)
        self.assertIn("Works late night on coding projects", context)
        self.assertIn("Desk lamp was left on", context)

if __name__ == "__main__":
    unittest.main()
