"""
Unit Tests for Backend Navigation Cortex & Decoupled Architecture.
Verifies that spatial world modeling, stationary target tracking,
intentional movement, and telemetry updates run 100% in Python.
"""

import unittest
from core.navigation_cortex import NavigationCortex, BehaviorState

class TestNavigationCortex(unittest.TestCase):

    def setUp(self):
        self.nav = NavigationCortex()

    def test_default_companion_idle_state(self):
        """Tests that robot defaults to companion idle with zero track motion."""
        self.assertEqual(self.nav.behavior_state, BehaviorState.COMPANION_IDLE)
        self.assertEqual(self.nav.speed, 0.0)
        self.assertEqual(self.nav.turn_speed, 0.0)
        telemetry = self.nav.get_telemetry()
        self.assertEqual(telemetry["speed"], 0.0)
        self.assertEqual(telemetry["behavior_state"], "COMPANION_IDLE")

    def test_stationary_watch_directive(self):
        """Tests that STAY_AND_WATCH locks chassis and aims pan/tilt at target object."""
        self.nav.execute_directive("STAY_AND_WATCH", "Keys")
        self.assertEqual(self.nav.behavior_state, BehaviorState.STATIONARY_WATCH)
        self.assertEqual(self.nav.locked_target, "Keys")
        self.assertEqual(self.nav.speed, 0.0)
        self.assertEqual(self.nav.turn_speed, 0.0)

        # Step simulation loop
        telemetry = self.nav.step(0.05)
        self.assertEqual(telemetry["speed"], 0.0)
        self.assertEqual(telemetry["behavior_state"], "STATIONARY_WATCH")
        self.assertNotEqual(telemetry["pan"], 0.0)  # Pan aligned to Keys

    def test_dynamic_obstacle_tracking(self):
        """Tests that moving an obstacle updates pan angle when watching."""
        self.nav.execute_directive("STAY_AND_WATCH", "Keys")
        self.nav.step(0.05)
        orig_pan = self.nav.pan_angle

        # Move keys to right side of desk
        self.nav.update_obstacle_position("Keys", 500.0, 120.0)
        self.nav.step(0.05)
        new_pan = self.nav.pan_angle

        self.assertNotEqual(orig_pan, new_pan)
        self.assertEqual(self.nav.speed, 0.0)  # Chassis remained stationary

    def test_hold_position_directive(self):
        """Tests that HOLD_POSITION stops all locomotion."""
        self.nav.speed = 2.0
        self.nav.turn_speed = 1.0
        self.nav.execute_directive("HOLD_POSITION")
        self.assertEqual(self.nav.behavior_state, BehaviorState.HOLD_POSITION)
        self.assertEqual(self.nav.speed, 0.0)
        self.assertEqual(self.nav.turn_speed, 0.0)

    def test_manual_motion_and_stop(self):
        """Tests operator manual motor control."""
        self.nav.set_manual_motion("forward")
        self.assertEqual(self.nav.behavior_state, BehaviorState.MANUAL)
        self.assertGreater(self.nav.speed, 0.0)

        self.nav.set_manual_motion("stop")
        self.assertEqual(self.nav.behavior_state, BehaviorState.COMPANION_IDLE)
        self.assertEqual(self.nav.speed, 0.0)

if __name__ == "__main__":
    unittest.main()
