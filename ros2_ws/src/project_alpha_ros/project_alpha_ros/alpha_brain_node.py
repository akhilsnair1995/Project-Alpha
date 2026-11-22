"""
Project Alpha: ROS 2 Brain & Cognitive Node (alpha_brain_node).
Wraps LocalGemmaEngine / GeminiBrain and NavigationCortex.
Performs local CPU-only LLM inference (llama-cpp-python or local Ollama with
qwen2.5:1.5b / gemma-2-2b-it-Q4_K_M, n_ctx=2048, 4 threads) entirely on a
non-blocking background worker thread so ROS 2 executor callbacks never stall.
Subscribes to /alpha/prompt; publishes /cmd_vel, /alpha/emotion, and /alpha/reply.
"""

import sys
import json
import queue
import urllib.request
import urllib.error
import threading
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure Project Alpha repository root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database import AlphaDatabase
from core.local_gemma import LocalGemmaEngine
from core.gemini_brain import GeminiBrain
from core.navigation_cortex import NavigationCortex

try:
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String
except ImportError:
    rclpy = None
    Node = object
    Twist = None
    String = None


class AlphaBrainNode(Node if rclpy else object):
    """ROS 2 Node orchestrating local LLM reasoning and navigation cortex."""

    def __init__(self, node_name: str = "alpha_brain_node"):
        if rclpy:
            super().__init__(node_name)
            self.declare_parameter("llm_provider", "local_gemma")  # "local_gemma", "ollama", "gemini"
            self.declare_parameter("ollama_model", "qwen2.5:1.5b")
            self.declare_parameter("ollama_url", "http://localhost:11434/api/generate")
            self.declare_parameter("n_threads", 4)
            self.declare_parameter("dry_run", True)

            self.llm_provider = self.get_parameter("llm_provider").get_parameter_value().string_value
            self.ollama_model = self.get_parameter("ollama_model").get_parameter_value().string_value
            self.ollama_url = self.get_parameter("ollama_url").get_parameter_value().string_value
            self.n_threads = self.get_parameter("n_threads").get_parameter_value().integer_value
            self.dry_run = self.get_parameter("dry_run").get_parameter_value().bool_value
        else:
            self.llm_provider = "local_gemma"
            self.ollama_model = "qwen2.5:1.5b"
            self.ollama_url = "http://localhost:11434/api/generate"
            self.n_threads = 4
            self.dry_run = True

        self.db = AlphaDatabase()
        self.local_gemma = LocalGemmaEngine(n_threads=self.n_threads)
        self.gemini_brain = GeminiBrain(db=self.db)
        self.nav = NavigationCortex(db=self.db)

        # Worker Queue for non-blocking asynchronous inference
        self.prompt_queue = queue.Queue()
        self.is_running = True
        self.worker_thread = threading.Thread(
            target=self._inference_worker,
            daemon=True,
            name="BrainInferenceWorker"
        )
        self.worker_thread.start()

        if rclpy:
            # Subscriptions
            self.sub_prompt = self.create_subscription(
                String,
                "/alpha/prompt",
                self.prompt_callback,
                10
            )

            # Publishers
            self.pub_reply = self.create_publisher(String, "/alpha/reply", 10)
            self.pub_emotion = self.create_publisher(String, "/alpha/emotion", 10)
            self.pub_cmd_vel = self.create_publisher(Twist, "/cmd_vel", 10)

            self.get_logger().info(
                f"[alpha_brain_node] Online! Provider: {self.llm_provider} (threads={self.n_threads})"
            )

    def prompt_callback(self, msg: String) -> None:
        """Enqueues incoming prompt without blocking ROS 2 executor."""
        text = msg.data.strip()
        if text:
            self.prompt_queue.put(text)

    def _query_ollama(self, prompt: str) -> Optional[str]:
        """Queries local Ollama daemon if available."""
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_thread": self.n_threads,
                "num_ctx": 2048
            }
        }
        try:
            req = urllib.request.Request(
                self.ollama_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except Exception:
            return None

    def _infer_response(self, prompt: str) -> Dict[str, Any]:
        """Routes prompt to chosen LLM provider with fallback handling."""
        system_instruction = (
            "You are Alpha, a curious, loyal Wall-E style autonomous companion rover on a desk. "
            "Keep answers concise, warm, and robotic."
        )

        reply_text = None

        if self.llm_provider == "ollama":
            reply_text = self._query_ollama(prompt)

        if not reply_text and self.local_gemma.is_available():
            reply_text = self.local_gemma.generate(
                prompt=prompt,
                system_instruction=system_instruction,
                max_tokens=120
            )

        if not reply_text:
            # Fallback to local rule engine / Gemma stub
            reply_text = self.local_gemma._fallback_stub_response(prompt)

        # Detect emotion from response tone
        lower_reply = reply_text.lower()
        if any(w in lower_reply for w in ["happy", "great", "glad", "hello", "hi"]):
            emotion = "happy"
        elif any(w in lower_reply for w in ["alert", "warning", "careful", "stop"]):
            emotion = "alert"
        elif any(w in lower_reply for w in ["sad", "sorry", "oops"]):
            emotion = "sad"
        elif any(w in lower_reply for w in ["what", "how", "why", "curious", "checking"]):
            emotion = "curious"
        else:
            emotion = "idle"

        return {
            "reply": reply_text,
            "emotion": emotion
        }

    def _inference_worker(self) -> None:
        """Background thread processing queue without blocking the ROS 2 loop."""
        while self.is_running:
            try:
                prompt = self.prompt_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                res = self._infer_response(prompt)
                reply = res["reply"]
                emotion = res["emotion"]

                if rclpy:
                    msg_reply = String()
                    msg_reply.data = reply
                    self.pub_reply.publish(msg_reply)

                    msg_emo = String()
                    msg_emo.data = emotion
                    self.pub_emotion.publish(msg_emo)

                    # Simple movement demonstration if command asks to move
                    p_low = prompt.lower()
                    if "spin" in p_low or "turn" in p_low:
                        twist = Twist()
                        twist.angular.z = 0.5
                        self.pub_cmd_vel.publish(twist)
                    elif "forward" in p_low or "come here" in p_low:
                        twist = Twist()
                        twist.linear.x = 0.15
                        self.pub_cmd_vel.publish(twist)
            except Exception as e:
                print(f"[alpha_brain_node] Inference error: {e}")
            finally:
                self.prompt_queue.task_done()

    def destroy_node(self):
        self.is_running = False
        if rclpy:
            super().destroy_node()


def main(args=None):
    if not rclpy:
        print("[alpha_brain_node] rclpy is not installed; running in standalone mode.")
        return
    rclpy.init(args=args)
    node = AlphaBrainNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
