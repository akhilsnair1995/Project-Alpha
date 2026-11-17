"""
Unit Tests for Neural Mind Engine & Biomimetic Biological Kinematics.
Verifies Flash & Hogan minimum-jerk trajectories, affective state mapping,
attention salience, continuous stream of consciousness, and living micro-dynamics.
"""

import math
import time
import unittest
from core.eye_animator import Emotion
from core.neural_engine import (
    NeuralMindEngine,
    AffectiveState,
    MinimumJerkTrajectory,
    AttentionSystem,
    StreamOfConsciousness,
    BiomimeticKinematics
)

class TestNeuralEngine(unittest.TestCase):

    def setUp(self):
        self.engine = NeuralMindEngine()

    def test_affective_state_mapping(self):
        """Tests that continuous (V, A, C) coordinates map to natural expressions."""
        aff = AffectiveState(valence=0.8, arousal=0.3, curiosity=0.5, attachment=0.9)
        self.assertEqual(aff.map_to_expression(), Emotion.LOVE)

        aff_curious = AffectiveState(valence=0.4, arousal=0.5, curiosity=0.85)
        self.assertEqual(aff_curious.map_to_expression(), Emotion.CURIOUS)

        aff_alert = AffectiveState(valence=-0.2, arousal=0.9, curiosity=0.5)
        self.assertEqual(aff_alert.map_to_expression(), Emotion.ALERT)

    def test_minimum_jerk_trajectory(self):
        """Tests that Flash & Hogan 5th-order polynomial ensures zero initial/final velocity."""
        traj = MinimumJerkTrajectory(start_val=0.0, target_val=50.0, duration=1.0)
        
        # At start
        pos_start, vel_start, _ = traj.update(0.0)
        self.assertEqual(pos_start, 0.0)

        # Midway (t = 0.5s)
        pos_mid, vel_mid, _ = traj.update(0.5)
        self.assertAlmostEqual(pos_mid, 25.0, delta=2.0)
        self.assertGreater(vel_mid, 0.0)  # Peak bell-curve velocity

        # At finish (t = 1.0s)
        pos_end, vel_end, _ = traj.update(0.5)
        self.assertAlmostEqual(pos_end, 50.0, delta=0.1)
        self.assertEqual(vel_end, 0.0)  # Rest-to-rest zero velocity

    def test_attention_salience_and_executive_lock(self):
        """Tests attention weighting and executive suppression during user commands."""
        attn = AttentionSystem()
        attn.register_or_update("Cup", 180.0, 360.0)
        attn.register_or_update("Keys", 150.0, 120.0)

        aff = AffectiveState(curiosity=0.8)
        focal = attn.evaluate_salience(320.0, 250.0, aff)
        self.assertIsNotNone(focal)

        # Executive lock on Keys
        attn.lock_focus("Keys")
        focal_locked = attn.evaluate_salience(320.0, 250.0, aff)
        self.assertEqual(focal_locked, "Keys")

        # Unlock restores spontaneous attention
        attn.unlock_focus()
        self.assertIsNone(attn.locked_command_target)

    def test_living_micro_dynamics(self):
        """Tests breathing heave and micro-saccades in biomimetic kinematics."""
        body = BiomimeticKinematics()
        initial_tilt = body.tilt

        # Advance 1.5 seconds to observe breathing oscillation
        for _ in range(30):
            body.step(0.05)

        # Breathing should cause subtle tilt heave around baseline
        self.assertNotEqual(body.tilt, initial_tilt)

    def test_stream_of_consciousness(self):
        """Tests continuous sentient thought generation."""
        soc = StreamOfConsciousness()
        aff = AffectiveState()
        thought = soc.generate_thought(aff, "Keys", is_locked=True, battery_volts=7.8, is_moving=False)
        self.assertIn("Keys", thought)
        self.assertTrue(len(thought) > 10)

    def test_pan_servo_stability_no_wobble(self):
        """Tests that deadband filtering prevents pan servo chatter and wobbling."""
        body = BiomimeticKinematics()
        body.plan_smooth_head_look(30.0, -10.0, duration=0.6)
        traj1 = body.pan_traj
        self.assertIsNotNone(traj1)

        # Step 2 ticks
        body.step(0.05)
        body.step(0.05)

        # Call again with almost identical angle (e.g. 30.5 deg within 1.5 deg deadband)
        body.plan_smooth_head_look(30.5, -10.0, duration=0.6)
        traj2 = body.pan_traj

        # Must NOT have recreated the trajectory from scratch!
        self.assertIs(traj1, traj2)

    def test_close_approach_and_facing_object(self):
        """Tests that Alpha drives right up to an object (< 55px) and turns to face it squarely."""
        self.engine.receive_command_directive("NAVIGATE_TO", "Keys")
        self.assertEqual(self.engine.body.facing_target_name, "Keys")

        # Step until arrival (up to 120 steps = 6.0 seconds)
        for _ in range(120):
            self.engine.step(0.05)
            if self.engine.body.target_coord_goal is None and self.engine.body.facing_target_pos is None:
                break

        keys_obs = self.engine.obstacles["Keys"]
        ox = keys_obs["x"] + keys_obs["width"] / 2.0
        oy = keys_obs["y"] + keys_obs["height"] / 2.0
        cx = self.engine.body.x + 30.0
        cy = self.engine.body.y + 35.0
        dist_to_obj = math.hypot(ox - cx, oy - cy)

        # Verifies close approach (within 55px of object center)
        self.assertLess(dist_to_obj, 55.0)

        # Verifies chassis heading is facing directly toward the object, NOT North (0 deg)!
        bearing_to_keys = (math.atan2(ox - cx, -(oy - cy)) * 180.0 / math.pi + 360.0) % 360.0
        heading_diff = (bearing_to_keys - self.engine.body.heading + 540.0) % 360.0 - 180.0
        self.assertLess(abs(heading_diff), 6.0)

    def test_neural_mind_step_telemetry(self):
        """Tests full 20Hz neural mind step and telemetry output."""
        telemetry = self.engine.step(0.05)
        self.assertIn("valence", telemetry)
        self.assertIn("arousal", telemetry)
        self.assertIn("curiosity", telemetry)
        self.assertIn("current_thought", telemetry)
        self.assertIn("pan", telemetry)
        self.assertIn("tilt", telemetry)

    def test_physical_hardware_limits_never_180(self):
        """Tests that servo pan is clamped to [-85, 85] and tilt to [-25, 35], never 180."""
        body = BiomimeticKinematics()
        body.plan_smooth_head_look(target_pan=180.0, target_tilt=180.0, duration=0.5)
        self.assertEqual(body.target_pan_goal, 85.0)
        self.assertEqual(body.target_tilt_goal, 35.0)

        body.plan_smooth_head_look(target_pan=-180.0, target_tilt=-180.0, duration=0.5)
        self.assertEqual(body.target_pan_goal, -85.0)
        self.assertEqual(body.target_tilt_goal, -25.0)

    def test_rear_target_tracking_pivots_chassis(self):
        """Tests that when an object is behind Alpha (>80 deg off), chassis pivots to face it."""
        # Alpha center is cx = 320 + 30 = 350, cy = 250 + 35 = 285 facing 0.0 (North)
        # Put obstacle center at tx = 350 (x = 325), ty = 485 (y = 460) -> directly South (180 deg)
        self.engine.update_obstacle("Keys", 325.0, 460.0)
        self.engine._orient_mind_toward_target("Keys")
        # Should have planned a heading trajectory to rotate body toward 180 degrees
        self.assertIsNotNone(self.engine.body.heading_traj)
        self.assertAlmostEqual(self.engine.body.heading_traj.target % 360.0, 180.0, delta=2.0)

    def test_clean_database_no_injection(self):
        """Tests that database initializes completely clean with zero artificial facts."""
        import tempfile
        from pathlib import Path
        from core.database import AlphaDatabase
        with tempfile.TemporaryDirectory() as tmp:
            test_db = AlphaDatabase(db_path=Path(tmp) / "clean.db")
            self.assertEqual(len(test_db.get_user_facts()), 0)
            self.assertEqual(len(test_db.find_objects("")), 0)
            self.assertEqual(len(test_db.get_recent_observations()), 0)
            self.assertEqual(len(test_db.get_recent_chat()), 0)

    def test_autonomous_running_and_exploring_mode(self):
        """Tests that EXPLORE_ROAM mode actively navigates waypoints and performs sensory head sweeps."""
        self.engine.set_operating_mode("EXPLORE_ROAM")
        self.assertEqual(self.engine.operating_mode, "EXPLORE_ROAM")

        # Force next exploration leg
        self.engine.pause_at_destination_until = 0.0
        self.engine.step(0.05)

        # Should have initiated biological sensory head look or purposeful transit
        self.assertTrue(bool(
            self.engine.body.pan_traj or
            self.engine.body.tilt_traj or
            self.engine.body.target_coord_goal or
            self.engine.body.facing_target_pos or
            self.engine.body.heading_traj
        ))
        t = self.engine.get_telemetry()
        self.assertEqual(t["operating_mode"], "EXPLORE_ROAM")
        self.assertIn("traits", t)
        self.assertIn("drives", t)
        self.assertGreater(t["traits"]["curious"], 0.7)

    def test_personality_traits_and_affective_stimuli(self):
        """Tests that personality traits and homeostatic drives update via environmental stimuli."""
        initial_curiosity = self.engine.affective.drives.curiosity
        initial_social = self.engine.affective.drives.social
        initial_valence = self.engine.affective.valence

        # Gentle pet stimulus
        self.engine.affective.apply_stimulus("GENTLE_PET", confidence=1.0)
        self.assertGreaterEqual(self.engine.affective.drives.social, initial_social)
        self.assertGreater(self.engine.affective.valence, initial_valence)

        # Verify 5-trait presence in telemetry
        telemetry = self.engine.get_telemetry()
        self.assertEqual(len(telemetry["traits"]), 5)
        self.assertIn("playful", telemetry["traits"])
        self.assertIn("curious", telemetry["traits"])
        self.assertIn("bold", telemetry["traits"])
        self.assertIn("clingy", telemetry["traits"])
        self.assertIn("shy", telemetry["traits"])

    def test_optical_cone_organic_discovery_and_speech(self):
        """Tests that Alpha discovers an object only when it enters its optical cone and speaks aloud."""
        self.engine.discovered_objects = {}
        self.assertEqual(len(self.engine.discovered_objects), 0)

        # Place a physical object directly in front of Alpha's camera cone
        # Alpha is at (320, 250), heading = 0.0 (pointing North / -Y)
        # Front is dy < 0, dx = 0: place keys at cx = 350 (x = 325), cy = 200 (y = 175) -> 85px ahead
        self.engine.update_environment_physics([
            {"id": "obs_keys", "title": "Keys", "x": 325.0, "y": 175.0, "width": 50, "height": 50, "emoji": "🔑"}
        ])

        # Verify cognitive memory does NOT cheat (zero pre-loaded knowledge)
        self.assertEqual(len(self.engine.discovered_objects), 0)

        # Point head straight forward (pan = 0, heading = 0)
        self.engine.body.pan = 0.0
        self.engine.body.heading = 0.0
        self.engine.operating_mode = "EXPLORE_ROAM"

        # Step neural engine: optical perception cone catches the keys!
        self.engine._process_optical_perception()

        # Should have queued spoken feedback and initiated approach
        self.assertGreater(len(self.engine.speech_feedback_queue), 0)
        self.assertIn("Spotted something", self.engine.speech_feedback_queue[0]["text"])
        self.assertEqual(self.engine.explore_substate, "APPROACHING")

        # Step until arrival and inspection
        for _ in range(120):
            self.engine.step(0.05)
            if "Keys" in self.engine.discovered_objects:
                break

        # Sighting should now be recorded organically
        self.assertIn("Keys", self.engine.discovered_objects)
        t = self.engine.get_telemetry()
        self.assertGreater(t["discovered_count"], 0)

    def test_optical_cone_notices_removed_object(self):
        """Tests that when an object is removed from HTML, Alpha notices when looking at that spot."""
        # Pre-condition: Alpha remembers Keys at (325, 175)
        self.engine.discovered_objects["Keys"] = {
            "title": "Keys",
            "x": 350.0,
            "y": 200.0,
            "discovered_at": time.time()
        }
        # But user removed it from physical desk!
        self.engine.physical_environment_items = {}

        # Alpha looks directly at where Keys used to be
        self.engine.body.pan = 0.0
        self.engine.body.heading = 0.0

        # Run perception
        self.engine._process_optical_perception()

        # Should notice it's gone and queue speech feedback
        self.assertNotIn("Keys", self.engine.discovered_objects)
        self.assertGreater(len(self.engine.speech_feedback_queue), 0)
        self.assertIn("not on the desk anymore", self.engine.speech_feedback_queue[-1]["text"])

if __name__ == "__main__":
    unittest.main()
