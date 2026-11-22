"""
Unit tests for Project Alpha upgrades:
(a) ESP32 serial command formatting and TELEM parsing
(b) Non-blocking gesture execution and cancellation in MotionController
(c) Differential-drive /cmd_vel clamping and cliff interlock logic
(d) main.py single-instance behavior wiring
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
ROS_PKG_DIR = REPO_ROOT / "ros2_ws" / "src" / "project_alpha_ros"
if str(ROS_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(ROS_PKG_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.motion_controller import MotionController
from core.behavior_engine import AlphaBehaviorEngine
from project_alpha_ros.diff_drive import DifferentialDriveConverter


class TestESP32SerialProtocol(unittest.TestCase):
    """(a) Tests ESP32 serial command formatting and TELEM frame parsing."""

    def test_format_motor_cmd_normalization_and_clamping(self):
        # Normal values
        cmd = MotionController.format_motor_cmd(0.5, -0.5)
        self.assertEqual(cmd, "M 0.50 -0.50\n")

        # Zero values
        cmd_zero = MotionController.format_motor_cmd(0.0, 0.0)
        self.assertEqual(cmd_zero, "M 0.00 0.00\n")

        # Out-of-bounds clamping
        cmd_clamped = MotionController.format_motor_cmd(2.5, -3.8)
        self.assertEqual(cmd_clamped, "M 1.00 -1.00\n")

    def test_format_head_cmd_clamping(self):
        # Standard angles
        cmd = MotionController.format_head_cmd(15.0, -10.0)
        self.assertEqual(cmd, "H 15.0 -10.0\n")

        # Exceeding pan [-85, 85] and tilt [-25, 35]
        cmd_exceeded = MotionController.format_head_cmd(120.0, -60.0)
        self.assertEqual(cmd_exceeded, "H 85.0 -25.0\n")

        cmd_tilt_high = MotionController.format_head_cmd(-100.0, 90.0)
        self.assertEqual(cmd_tilt_high, "H -85.0 35.0\n")

    def test_parse_telem_line_valid(self):
        line = "TELEM cliff_l=0 cliff_r=1 wd=0\n"
        res = MotionController.parse_telem_line(line)
        self.assertIsNotNone(res)
        self.assertEqual(res["cliff_l"], 0)
        self.assertEqual(res["cliff_r"], 1)
        self.assertEqual(res["wd"], 0)

    def test_parse_telem_line_watchdog_active(self):
        line = "TELEM cliff_l=1 cliff_r=1 wd=1"
        res = MotionController.parse_telem_line(line)
        self.assertIsNotNone(res)
        self.assertEqual(res["cliff_l"], 1)
        self.assertEqual(res["cliff_r"], 1)
        self.assertEqual(res["wd"], 1)

    def test_parse_telem_line_invalid(self):
        self.assertIsNone(MotionController.parse_telem_line("ACK M\n"))
        self.assertIsNone(MotionController.parse_telem_line("RANDOM_TEXT"))
        self.assertIsNone(MotionController.parse_telem_line("TELEM corrupted"))

    def test_serial_esp32_driver_cliff_update(self):
        motion = MotionController(hardware_enabled=False, backend="sim")
        motion.driver_type = "serial_esp32"
        motion._esp32_cliff_left = False
        motion._esp32_cliff_right = False
        self.assertFalse(motion.check_cliff_sensors())

        # Simulate incoming cliff telemetry
        parsed = MotionController.parse_telem_line("TELEM cliff_l=1 cliff_r=0 wd=0\n")
        motion._esp32_cliff_left = bool(parsed["cliff_l"])
        motion._esp32_cliff_right = bool(parsed["cliff_r"])
        self.assertTrue(motion.check_cliff_sensors())
        self.assertEqual(motion.get_cliff_status(), (True, False))


class TestNonBlockingMotionGestures(unittest.TestCase):
    """(b) Tests non-blocking gesture execution and cancellation in MotionController."""

    def setUp(self):
        self.motion = MotionController(hardware_enabled=False, backend="sim")

    def tearDown(self):
        self.motion.cleanup()

    def test_nod_is_non_blocking(self):
        t0 = time.time()
        # nod(repeats=2) has 4 steps totaling ~0.48s in blocking mode
        self.motion.nod(repeats=2, blocking=False)
        elapsed = time.time() - t0
        # Should return almost instantaneously (< 50ms)
        self.assertLess(elapsed, 0.08, "nod() blocked the calling thread!")
        self.assertTrue(self.motion.is_gesture_running())
        self.motion.cancel_gesture()
        self.assertFalse(self.motion.is_gesture_running())

    def test_gesture_cancellation(self):
        self.motion.nod(repeats=5, blocking=False)
        self.assertTrue(self.motion.is_gesture_running())
        self.motion.cancel_gesture()
        self.assertFalse(self.motion.is_gesture_running())

    def test_all_gestures_non_blocking_execution(self):
        gestures = [
            self.motion.curious_tilt,
            self.motion.excited_wiggle,
            self.motion.alert_recoil,
            self.motion.sad_droop,
            self.motion.confused_wobble,
            self.motion.head_pet_reaction,
        ]
        for gst in gestures:
            t0 = time.time()
            gst(blocking=False)
            elapsed = time.time() - t0
            self.assertLess(elapsed, 0.08, f"{gst.__name__} blocked caller thread!")
            self.motion.cancel_gesture()

    def test_emergency_cliff_evasion_is_non_blocking(self):
        t0 = time.time()
        self.motion._emergency_cliff_evasion(blocking=False)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 0.08, "_emergency_cliff_evasion blocked caller thread!")
        self.assertTrue(self.motion.is_cliff_evading())
        self.motion.cancel_cliff_evasion()
        self.assertFalse(self.motion.is_cliff_evading())


class TestDifferentialDriveAndSafetyInterlock(unittest.TestCase):
    """(c) Tests differential-drive /cmd_vel clamping and cliff interlock logic."""

    def setUp(self):
        self.converter = DifferentialDriveConverter(track_width=0.12, max_linear_speed=0.30)

    def test_straight_forward_and_reverse(self):
        # Max speed forward: linear.x = 0.30, angular.z = 0.0 -> (1.0, 1.0)
        l, r = self.converter.twist_to_tank_speeds(linear_x=0.30, angular_z=0.0)
        self.assertEqual(l, 1.0)
        self.assertEqual(r, 1.0)

        # Half speed reverse: linear.x = -0.15, angular.z = 0.0 -> (-0.5, -0.5)
        l, r = self.converter.twist_to_tank_speeds(linear_x=-0.15, angular_z=0.0)
        self.assertEqual(l, -0.5)
        self.assertEqual(r, -0.5)

    def test_pure_rotation_spin(self):
        # In-place spin: linear.x = 0.0, angular.z = 5.0 rad/s
        # v_l = -5.0 * 0.06 = -0.30 -> -1.0
        # v_r = +5.0 * 0.06 = +0.30 -> +1.0
        l, r = self.converter.twist_to_tank_speeds(linear_x=0.0, angular_z=5.0)
        self.assertEqual(l, -1.0)
        self.assertEqual(r, 1.0)

    def test_saturation_clamping(self):
        # Massive linear and angular inputs must be clamped strictly within [-1.0, 1.0]
        l, r = self.converter.twist_to_tank_speeds(linear_x=10.0, angular_z=20.0)
        self.assertLessEqual(l, 1.0)
        self.assertGreaterEqual(l, -1.0)
        self.assertLessEqual(r, 1.0)
        self.assertGreaterEqual(r, -1.0)

    def test_cliff_interlock_stops_forward_motion(self):
        # Forward motion attempted while cliff is active -> must be zeroed to (0.0, 0.0)!
        l, r = self.converter.twist_to_tank_speeds(
            linear_x=0.20,
            angular_z=0.0,
            cliff_active=True
        )
        self.assertEqual(l, 0.0)
        self.assertEqual(r, 0.0)

        # Forward turn attempted while cliff active -> must also be zeroed!
        l_turn, r_turn = self.converter.twist_to_tank_speeds(
            linear_x=0.10,
            angular_z=1.0,
            cliff_active=True
        )
        self.assertEqual(l_turn, 0.0)
        self.assertEqual(r_turn, 0.0)

    def test_cliff_interlock_permits_reverse_evasion(self):
        # Reverse motion attempted while cliff is active -> allowed so robot can back away!
        l, r = self.converter.twist_to_tank_speeds(
            linear_x=-0.20,
            angular_z=0.0,
            cliff_active=True
        )
        self.assertLess(l, 0.0)
        self.assertLess(r, 0.0)

    def test_estop_forces_zero(self):
        l, r = self.converter.twist_to_tank_speeds(
            linear_x=0.30,
            angular_z=2.0,
            estop_active=True
        )
        self.assertEqual(l, 0.0)
        self.assertEqual(r, 0.0)

    def test_safety_status_diagnostics(self):
        self.assertEqual(self.converter.get_safety_status(cliff_active=False, estop_active=False), "OK")
        self.assertEqual(self.converter.get_safety_status(cliff_active=True, estop_active=False), "CLIFF_ALERT")
        self.assertEqual(self.converter.get_safety_status(cliff_active=False, estop_active=True), "ESTOP_ENGAGED")
        self.assertEqual(self.converter.get_safety_status(watchdog_active=True), "WATCHDOG_TIMEOUT")


class TestMainBehaviorSingleInstance(unittest.TestCase):
    """(d) Tests main.py single-instance behavior engine wiring."""

    def test_single_behavior_engine_shared_with_navigation_cortex(self):
        from main import AlphaRobot
        robot = AlphaRobot(voice_enabled=False)

        # 1. Behavior engine is initialized and wired to brain
        self.assertIsNotNone(robot.behavior)
        self.assertIsInstance(robot.behavior, AlphaBehaviorEngine)
        self.assertIs(robot.behavior.brain, robot.brain)

        # 2. Crucial fix: NavigationCortex shares the EXACT same instance as self.behavior
        self.assertIs(
            robot.behavior,
            robot.nav.engine.behavior_engine,
            "NavigationCortex must share the same behavior_engine instance as AlphaRobot!"
        )

        robot.motion.cleanup()


if __name__ == "__main__":
    unittest.main()
