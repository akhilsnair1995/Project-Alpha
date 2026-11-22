"""
Project Alpha: ROS 2 Motion Node (alpha_motion_node).
Subscribes to /cmd_vel, /alpha/head_pose, and /estop.
Translates Twist commands into normalized crawler track commands with cliff interlocks.
Drives MotionController (serial_esp32 or simulation mode) and publishes safety telemetry at 20 Hz.
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure Project Alpha repository root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.motion_controller import MotionController
from project_alpha_ros.diff_drive import DifferentialDriveConverter

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist, Vector3
    from std_msgs.msg import Bool, String
except ImportError:
    # Graceful fallback on non-ROS testing environments
    rclpy = None
    Node = object
    Twist = None
    Vector3 = None
    Bool = None
    String = None


class AlphaMotionNode(Node if rclpy else object):
    """ROS 2 Node managing physical and simulated motion actuators & safety reflexes."""

    def __init__(self, node_name: str = "alpha_motion_node"):
        if rclpy:
            super().__init__(node_name)
            # Declare ROS parameters
            self.declare_parameter("dry_run", True)
            self.declare_parameter("motion_backend", "auto")
            self.declare_parameter("serial_port", "auto")
            self.declare_parameter("baud_rate", 115200)
            self.declare_parameter("track_width", 0.12)
            self.declare_parameter("max_linear_speed", 0.30)

            self.dry_run = self.get_parameter("dry_run").get_parameter_value().bool_value
            self.backend = self.get_parameter("motion_backend").get_parameter_value().string_value
            self.track_width = self.get_parameter("track_width").get_parameter_value().double_value
            self.max_linear_speed = self.get_parameter("max_linear_speed").get_parameter_value().double_value
        else:
            self.dry_run = True
            self.backend = "sim"
            self.track_width = 0.12
            self.max_linear_speed = 0.30

        self.diff_converter = DifferentialDriveConverter(
            track_width=self.track_width,
            max_linear_speed=self.max_linear_speed
        )

        # Initialize MotionController
        backend_choice = "sim" if self.dry_run else self.backend
        self.motion = MotionController(
            hardware_enabled=not self.dry_run,
            backend=backend_choice
        )

        self.estop_active = False
        self.last_cmd_vel = (0.0, 0.0)

        if rclpy:
            # Subscriptions
            self.sub_cmd_vel = self.create_subscription(
                Twist,
                "/cmd_vel",
                self.cmd_vel_callback,
                10
            )
            self.sub_head_pose = self.create_subscription(
                Vector3,
                "/alpha/head_pose",
                self.head_pose_callback,
                10
            )
            self.sub_estop = self.create_subscription(
                Bool,
                "/estop",
                self.estop_callback,
                10
            )

            # 20 Hz Telemetry Publishers
            self.pub_cliff = self.create_publisher(Bool, "/alpha/cliff", 10)
            self.pub_safety = self.create_publisher(String, "/alpha/safety_status", 10)
            self.timer_telemetry = self.create_timer(1.0 / 20.0, self.publish_telemetry)

            self.get_logger().info(
                f"[alpha_motion_node] Online! Driver: {self.motion.driver_type} (dry_run={self.dry_run})"
            )

    def cmd_vel_callback(self, msg: Twist) -> None:
        """Processes incoming Twist and commands MotionController."""
        cliff_active = self.motion.check_cliff_sensors()
        left, right = self.diff_converter.twist_to_tank_speeds(
            linear_x=msg.linear.x,
            angular_z=msg.angular.z,
            cliff_active=cliff_active,
            estop_active=self.estop_active
        )
        self.last_cmd_vel = (left, right)
        self.motion.drive(left, right)

    def head_pose_callback(self, msg: Vector3) -> None:
        """Processes head pan (msg.x) and tilt (msg.y) in degrees."""
        self.motion.set_head_pose(pan_deg=msg.x, tilt_deg=msg.y)

    def estop_callback(self, msg: Bool) -> None:
        """Emergency stop latch."""
        self.estop_active = bool(msg.data)
        if self.estop_active:
            self.motion.stop()
            if rclpy:
                self.get_logger().warn("[alpha_motion_node] EMERGENCY STOP ENGAGED!")

    def publish_telemetry(self) -> None:
        """Publishes 20 Hz cliff and safety status."""
        cliff_active = self.motion.check_cliff_sensors()
        status_str = self.diff_converter.get_safety_status(
            cliff_active=cliff_active,
            estop_active=self.estop_active,
            watchdog_active=getattr(self.motion, "_esp32_wd", False)
        )

        msg_cliff = Bool()
        msg_cliff.data = cliff_active
        self.pub_cliff.publish(msg_cliff)

        msg_safety = String()
        msg_safety.data = status_str
        self.pub_safety.publish(msg_safety)

    def destroy_node(self):
        if hasattr(self, "motion") and self.motion:
            self.motion.cleanup()
        if rclpy:
            super().destroy_node()


def main(args=None):
    if not rclpy:
        print("[alpha_motion_node] rclpy is not installed; running in standalone simulation.")
        return
    rclpy.init(args=args)
    node = AlphaMotionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
