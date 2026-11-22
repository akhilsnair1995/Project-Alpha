"""
Differential Drive Kinematics & Safety Interlock Converter for Project Alpha.
Converts geometry_msgs/Twist (linear.x, angular.z) into normalized differential
crawler track speeds (-1.0 to +1.0) with table-edge cliff interlocks and E-stop logic.
"""

from typing import Tuple


class DifferentialDriveConverter:
    """
    Kinematic model for Wall-E mini crawler chassis:
    v_left  = v - (omega * track_width / 2)
    v_right = v + (omega * track_width / 2)
    """

    def __init__(self, track_width: float = 0.12, max_linear_speed: float = 0.30):
        self.track_width = max(0.01, float(track_width))
        self.max_linear_speed = max(0.01, float(max_linear_speed))

    def twist_to_tank_speeds(
        self,
        linear_x: float,
        angular_z: float,
        cliff_active: bool = False,
        estop_active: bool = False
    ) -> Tuple[float, float]:
        """
        Converts linear and angular velocities to clamped tank speeds [-1.0, 1.0].
        Enforces safety interlocks for E-stop and cliff detection.
        """
        if estop_active:
            return 0.0, 0.0

        v = float(linear_x)
        omega = float(angular_z)

        # Differential drive kinematic split
        v_l = v - (omega * self.track_width / 2.0)
        v_r = v + (omega * self.track_width / 2.0)

        # Normalize relative to max linear speed
        norm_l = v_l / self.max_linear_speed
        norm_r = v_r / self.max_linear_speed

        # Clamp strictly between -1.0 and +1.0
        clamped_l = max(-1.0, min(1.0, norm_l))
        clamped_r = max(-1.0, min(1.0, norm_r))

        # Cliff Safety Interlock:
        # If a cliff is detected under the front sensors and any forward motion is commanded,
        # immediately suppress forward motion to 0.0 to prevent falling off the table!
        if cliff_active and (clamped_l > 0.0 or clamped_r > 0.0):
            return 0.0, 0.0

        return round(clamped_l, 4), round(clamped_r, 4)

    def get_safety_status(
        self,
        cliff_active: bool = False,
        estop_active: bool = False,
        watchdog_active: bool = False
    ) -> str:
        """Returns diagnostic safety status string."""
        if estop_active:
            return "ESTOP_ENGAGED"
        if cliff_active:
            return "CLIFF_ALERT"
        if watchdog_active:
            return "WATCHDOG_TIMEOUT"
        return "OK"
