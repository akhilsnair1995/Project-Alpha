"""
Project Alpha: ROS 2 Face & Voice Node (alpha_face_voice_node).
Wraps DualEyeController (dual GC9A01 1.28" LCDs) and VoiceEngine (I2S MAX98357A / TTS).
Subscribes to /alpha/emotion and /alpha/reply.
"""

import sys
from pathlib import Path

# Ensure Project Alpha repository root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.eye_animator import DualEyeController, Emotion
from core.voice_engine import VoiceEngine

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
except ImportError:
    rclpy = None
    Node = object
    String = None


class AlphaFaceVoiceNode(Node if rclpy else object):
    """ROS 2 Node controlling facial LCD animations and I2S/TTS speech synthesis."""

    def __init__(self, node_name: str = "alpha_face_voice_node"):
        if rclpy:
            super().__init__(node_name)
            self.declare_parameter("voice_enabled", True)
            self.declare_parameter("dry_run", True)

            self.voice_enabled = self.get_parameter("voice_enabled").get_parameter_value().bool_value
            self.dry_run = self.get_parameter("dry_run").get_parameter_value().bool_value
        else:
            self.voice_enabled = True
            self.dry_run = True

        # Initialize Dual Eye Displays (Simulation on PC, Hardware SPI on Pi 5)
        self.eyes = DualEyeController(hardware_enabled=not self.dry_run)

        # Initialize Voice Engine
        self.voice = VoiceEngine(voice_enabled=self.voice_enabled)

        # Synchronize speech mouth pulse with LCD eyes
        self.voice.on_speech_start = lambda: self.eyes.talking_pulse(cycles=1)

        if rclpy:
            self.sub_emotion = self.create_subscription(
                String,
                "/alpha/emotion",
                self.emotion_callback,
                10
            )
            self.sub_reply = self.create_subscription(
                String,
                "/alpha/reply",
                self.reply_callback,
                10
            )
            self.get_logger().info(
                f"[alpha_face_voice_node] Online! (voice={self.voice_enabled}, dry_run={self.dry_run})"
            )

    def emotion_callback(self, msg: String) -> None:
        """Sets animated facial emotion from emotion name string."""
        raw_emo = msg.data.strip()
        try:
            emo = Emotion.from_str(raw_emo)
            self.eyes.set_emotion(emo)
        except Exception:
            pass

    def reply_callback(self, msg: String) -> None:
        """Speaks out synthesized reply text."""
        text = msg.data.strip()
        if text:
            self.voice.speak(text, async_play=True)

    def destroy_node(self):
        if rclpy:
            super().destroy_node()


def main(args=None):
    if not rclpy:
        print("[alpha_face_voice_node] rclpy is not installed; running in standalone mode.")
        return
    rclpy.init(args=args)
    node = AlphaFaceVoiceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
