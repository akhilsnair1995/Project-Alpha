"""
Unit Tests for Project Alpha Affective Memory, Contextual Bandits, and Behavior Systems.
Verifies Ebbinghaus retention dynamics, Thompson Sampling, PAD integration, and Utility AI.
"""

import unittest
import tempfile
from pathlib import Path

from core.database import AlphaDatabase
from core.learning_engine import AutonomousLearningEngine
from core.affective_engine import AffectiveEngine, PADState, HomeostaticDrives, PersonalityTraits
from core.behavior_engine import BehaviorEngine, LivingBioOscillator

class TestAffectiveMemoryAndBandits(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_memory.db"
        self.db = AlphaDatabase(db_path=self.db_path)
        self.learning = AutonomousLearningEngine(db=self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_episodic_event_and_ebbinghaus_retention(self):
        """Verifies episodic event storage and Ebbinghaus retention calculation."""
        ev_id = self.learning.record_affective_episode(
            event_type="OWNER_PRAISE",
            description="Akhil said good boy and petted Alpha",
            valence_delta=0.5,
            arousal_delta=0.3
        )
        self.assertGreater(ev_id, 0)

        # Retrieve active memories
        memories = self.learning.get_salient_memories(min_retention=0.1)
        self.assertTrue(any(m["event_id"] == ev_id for m in memories))
        target_mem = next(m for m in memories if m["event_id"] == ev_id)
        self.assertGreater(target_mem["retention"], 0.5)

        # Test reinforcement
        self.learning.reinforce_memory(ev_id)
        reinforced_mems = self.learning.get_salient_memories(min_retention=0.1)
        reinforced_target = next(m for m in reinforced_mems if m["event_id"] == ev_id)
        self.assertEqual(reinforced_target["reinforcement_count"], 2)

    def test_thompson_sampling_bandits(self):
        """Verifies Beta-Bernoulli bandit sampling and feedback updates."""
        # Initial action selection
        action = self.learning.sample_interaction_behavior(["CHASE_OBJECT", "GENTLE_NUZZLE"])
        self.assertIn(action, ["CHASE_OBJECT", "GENTLE_NUZZLE"])

        # Record positive feedback for GENTLE_NUZZLE
        for _ in range(5):
            self.learning.register_interaction_feedback("GENTLE_NUZZLE", positive=True)

        params = self.db.get_bandit_parameters()
        self.assertIn("GENTLE_NUZZLE", params)
        self.assertGreaterEqual(params["GENTLE_NUZZLE"]["alpha"], 5.0)

        # Sample multiple times; GENTLE_NUZZLE should win majority of trials
        samples = [self.learning.sample_interaction_behavior(["CHASE_OBJECT", "GENTLE_NUZZLE"]) for _ in range(20)]
        self.assertGreater(samples.count("GENTLE_NUZZLE"), 10)

    def test_owner_profile_and_attachment(self):
        """Verifies long-term owner profile attachment updates."""
        profile = self.db.get_or_create_owner_profile("Akhil")
        initial_attach = profile["attachment_level"]
        self.assertGreater(initial_attach, 0.5)

        # Increase attachment
        new_attach = self.db.update_owner_attachment("Akhil", delta=0.05)
        self.assertAlmostEqual(new_attach, initial_attach + 0.05, places=2)

    def test_affective_engine_rk2_integration(self):
        """Verifies AffectiveEngine numerical stability and drive decays."""
        engine = AffectiveEngine()
        initial_v = engine.pad.valence
        initial_a = engine.pad.arousal

        # Apply high stimulus
        engine.stimulate(0.4, 0.5, 0.2)
        self.assertGreater(engine.pad.valence, initial_v)
        self.assertGreater(engine.pad.arousal, initial_a)

        # Step 5 seconds; should decay towards baseline
        for _ in range(100):
            engine.step(dt=0.05)

        self.assertLess(engine.pad.arousal, 0.9)
        self.assertGreater(engine.pad.valence, 0.2)

    def test_behavior_engine_utility_arbitration(self):
        """Verifies BehaviorEngine evaluates utilities and handles hard subsumption."""
        aff = AffectiveEngine()
        b_engine = BehaviorEngine()

        # Normal idle condition
        out = b_engine.step(
            dt=0.05,
            pad=aff.pad,
            drives=aff.drives,
            traits=aff.traits,
            perception={}
        )
        self.assertIn(out["behavior_id"], ["DAYDREAM_GLANCE", "WANDER_CURIOUS", "LOOK_AT_FACE"])

        # Hard cliff detection override
        out_cliff = b_engine.step(
            dt=0.05,
            pad=aff.pad,
            drives=aff.drives,
            traits=aff.traits,
            perception={"cliff_detected": True}
        )
        self.assertEqual(out_cliff["behavior_id"], "EMERGENCY_RECOIL")
        self.assertEqual(out_cliff["utility_score"], 100.0)

        # Startle override
        out_startle = b_engine.step(
            dt=0.05,
            pad=aff.pad,
            drives=aff.drives,
            traits=aff.traits,
            perception={"loud_sound": True}
        )
        self.assertEqual(out_startle["behavior_id"], "STARTLE_JUMP")

if __name__ == "__main__":
    unittest.main()
