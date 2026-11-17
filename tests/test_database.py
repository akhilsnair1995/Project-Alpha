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

    def test_persons_catalog_and_profiles(self):
        # Verify Akhil is automatically seeded as owner
        akhil = self.db.get_person_by_name("Akhil")
        self.assertIsNotNone(akhil)
        self.assertEqual(akhil["relationship"], "owner")

        # Register a friend
        pid = self.db.get_or_create_person("Sarah", relationship="friend", visual_description="Long dark hair, blue jacket")
        self.assertGreater(pid, 0)
        sarah = self.db.get_person_by_name("Sarah")
        self.assertIsNotNone(sarah)
        self.assertEqual(sarah["relationship"], "friend")
        self.assertIn("blue jacket", sarah["visual_description"])

        # Check list of known persons
        persons = self.db.get_known_persons()
        names = [p["name"] for p in persons]
        self.assertIn("Akhil", names)
        self.assertIn("Sarah", names)

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

    def test_object_ownership_assignment(self):
        # Record an object with an assigned owner
        self.db.record_discovered_object(
            name="MacBook Pro",
            description="Silver laptop on desk",
            room_name="Work Desk",
            owner_name="Akhil"
        )
        # Record an object for another person
        self.db.record_discovered_object(
            name="Blue Water Bottle",
            description="Insulated thermos",
            room_name="Work Desk",
            owner_name="Sarah"
        )

        # Search Akhil's objects
        akhil_objs = self.db.get_person_objects("Akhil")
        self.assertEqual(len(akhil_objs), 1)
        self.assertEqual(akhil_objs[0]["name"], "Macbook Pro")
        self.assertEqual(akhil_objs[0]["owner_name"], "Akhil")

        # Search Sarah's objects
        sarah_objs = self.db.get_person_objects("Sarah")
        self.assertEqual(len(sarah_objs), 1)
        self.assertEqual(sarah_objs[0]["name"], "Blue Water Bottle")
        self.assertEqual(sarah_objs[0]["owner_name"], "Sarah")

        # Reassign object owner
        self.db.assign_object_owner("Blue Water Bottle", "John")
        reassigned = self.db.find_objects("Bottle")
        self.assertEqual(reassigned[0]["owner_name"], "John")

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
        self.db.record_discovered_object("Coffee Mug", "Ceramic mug", owner_name="Akhil")
        context = self.db.generate_system_prompt_context()

        self.assertIn("LOCAL MEMORY & HOUSEHOLD AWARENESS", context)
        self.assertIn("Known People in Household:", context)
        self.assertIn("Akhil (Owner)", context)
        self.assertIn("Coffee Mug [Owner: Akhil]", context)
        self.assertIn("Works late night on coding projects", context)
        self.assertIn("Desk lamp was left on", context)

if __name__ == "__main__":
    unittest.main()
