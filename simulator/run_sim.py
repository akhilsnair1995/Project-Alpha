"""
Project Alpha: Live Simulator Server & Cognitive Streaming Backend.
Serves the digital twin simulator and streams live SQLite memory,
Gemini 2.5 / Local Gemma AI brain responses, and continuous learning updates over REST APIs.
"""

import os
import sys
import json
import http.server
import socketserver
import webbrowser
from urllib.parse import urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import AlphaRobot
from core.eye_animator import Emotion

PORT = 8085
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Global singleton robot instance
robot = None

def get_robot() -> AlphaRobot:
    global robot
    if robot is None:
        robot = AlphaRobot()
    return robot

class SimulatorAPIHandler(http.server.SimpleHTTPRequestHandler):
    """Serves static simulator files and handles live AI & memory streaming endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self._handle_status()
        elif parsed.path == "/api/memory":
            self._handle_memory()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if parsed.path == "/api/chat":
            self._handle_chat(data)
        elif parsed.path == "/api/inspect_frame":
            self._handle_inspect_frame(data)
        elif parsed.path == "/api/sight_object":
            self._handle_sight_object(data)
        elif parsed.path == "/api/toggle_brain":
            self._handle_toggle_brain(data)
        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, data: dict, status_code: int = 200):
        response_bytes = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def _handle_status(self):
        r = get_robot()
        facts = r.db.get_user_facts()
        objects = r.db.find_objects("")
        self._send_json({
            "status": "online" if r.brain.is_online() else "offline",
            "brain_name": "Google Gemini 3.5 Flash" if r.brain.is_online() else "Local Gemma 2B (Auxiliary Core)",
            "facts_count": len(facts),
            "objects_count": len(objects),
            "emotion": r.eyes.left_eye.current_emotion.value,
            "battery_volts": 7.85
        })

    def _handle_memory(self):
        r = get_robot()
        self._send_json({
            "facts": r.db.get_user_facts(limit=25),
            "objects": r.db.find_objects(""),
            "observations": r.db.get_recent_observations(limit=15),
            "chat_history": r.db.get_recent_chat(limit=10)
        })

    def _handle_chat(self, data: dict):
        user_msg = data.get("message", "").strip()
        if not user_msg:
            self._send_json({"error": "Empty message"}, 400)
            return

        r = get_robot()
        # Set eyes to analyzing while processing
        r.eyes.set_emotion(Emotion.ANALYZING)
        reply = r.brain.chat(user_msg)
        r.eyes.set_emotion(Emotion.HAPPY)

        self._send_json({
            "reply": reply,
            "emotion": r.eyes.left_eye.current_emotion.value,
            "brain_type": "gemini" if r.brain.is_online() else "local_gemma",
            "facts": r.db.get_user_facts(limit=15),
            "observations": r.db.get_recent_observations(limit=5)
        })

    def _handle_inspect_frame(self, data: dict):
        import base64
        r = get_robot()
        b64_data = data.get("image_base64", "")
        room_name = data.get("room", "Work Desk")
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        
        try:
            image_bytes = base64.b64decode(b64_data)
            r.eyes.set_emotion(Emotion.ANALYZING)
            result = r.brain.analyze_roaming_scene(image_bytes, room_hint=room_name)
            r.eyes.set_emotion(Emotion.HAPPY)
            self._send_json({
                "status": "success",
                "result": result,
                "objects": r.db.find_objects(""),
                "observations": r.db.get_recent_observations(limit=5)
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    def _handle_sight_object(self, data: dict):
        r = get_robot()
        obj_name = data.get("name", "Unknown Object")
        room_name = data.get("room", "Work Desk")
        desc = data.get("description", "Discovered while roaming.")

        sighting = r.brain.learning_engine.learn_object_sighting(
            object_name=obj_name,
            description=desc,
            room_name=room_name
        )

        r.eyes.set_emotion(Emotion.CURIOUS)
        self._send_json({
            "status": "recorded",
            "sighting": sighting,
            "objects": r.db.find_objects("")
        })

    def _handle_toggle_brain(self, data: dict):
        r = get_robot()
        target_mode = data.get("mode", "toggle")
        
        if target_mode == "offline":
            r.brain.client = None
        elif target_mode == "online":
            r.brain._init_client()
        else:
            if r.brain.is_online():
                r.brain.client = None
            else:
                r.brain._init_client()

        mode_name = "online" if r.brain.is_online() else "offline"
        self._send_json({
            "mode": mode_name,
            "brain_name": "Google Gemini 3.5 Flash" if r.brain.is_online() else "Local Gemma 2B (Auxiliary Core)"
        })

def main():
    print("=" * 65)
    print("  PROJECT ALPHA - LIVE SIMULATOR & COGNITIVE BACKEND SERVER")
    print("=" * 65)
    get_robot()
    print(f"[Simulator] Serving digital twin from: {DIRECTORY}")
    print(f"[Simulator] Live Backend URL: http://localhost:{PORT}")
    print("=" * 65)

    url = f"http://localhost:{PORT}/index.html"
    webbrowser.open(url)

    with socketserver.TCPServer(("", PORT), SimulatorAPIHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down simulator server. Goodbye!")

if __name__ == "__main__":
    main()
