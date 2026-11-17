"""
Project Alpha: Live Simulator Server & Cognitive Streaming Backend.
Serves the digital twin simulator and streams live SQLite memory,
dual-eye expressions, procedural Wall-E audio, Text-to-Speech (TTS),
and Gemini 2.5 / Local Gemma AI brain responses over REST APIs.
"""

import os
import sys
import time
import json
import threading
import http.server
import socketserver
import webbrowser
from urllib.parse import urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import AlphaRobot
from core.config import DEFAULT_GEMINI_MODEL
from core.eye_animator import Emotion
from core.voice_engine import WallESoundSynthesizer

PORT = 8085
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Global singleton robot instance
robot = None

def start_backend_kinematics_loop(r: AlphaRobot):
    """Continuous 20Hz backend physics, navigation, and cognitive thought loop."""
    def loop():
        while True:
            try:
                r.nav.step(0.05)
            except Exception:
                pass
            time.sleep(0.05)
    t = threading.Thread(target=loop, daemon=True, name="AlphaKinematicsLoop")
    t.start()
    print("[Backend Kinematics] Autonomous navigation cortex active @ 20Hz.")

def get_robot() -> AlphaRobot:
    global robot
    if robot is None:
        robot = AlphaRobot(voice_enabled=True)
        start_backend_kinematics_loop(robot)
    return robot

class SimulatorAPIHandler(http.server.SimpleHTTPRequestHandler):
    """Serves static simulator files and handles live AI, expression & audio endpoints."""

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
        path = parsed.path

        if path == "/api/telemetry":
            self._handle_telemetry()
        elif path == "/api/status":
            self._handle_status()
        elif path == "/api/memory":
            self._handle_memory()
        elif path == "/api/expression":
            self._handle_get_expression()
        elif path == "/api/sound_presets":
            self._handle_sound_presets()
        elif path.startswith("/api/audio/"):
            self._handle_audio_stream(path)
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
        elif parsed.path == "/api/obstacle":
            self._handle_obstacle(data)
        elif parsed.path == "/api/environment_physics":
            self._handle_environment_physics(data)
        elif parsed.path == "/api/environment_physics/delete":
            self._handle_environment_physics_delete(data)
        elif parsed.path == "/api/motor":
            self._handle_motor(data)
        elif parsed.path == "/api/directive":
            self._handle_directive(data)
        elif parsed.path == "/api/mode":
            self._handle_mode(data)
        elif parsed.path == "/api/expression":
            self._handle_set_expression(data)
        elif parsed.path == "/api/sound":
            self._handle_play_sound(data)
        elif parsed.path == "/api/speak":
            self._handle_speak(data)
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

    def _handle_telemetry(self):
        r = get_robot()
        self._send_json(r.nav.get_telemetry())

    def _handle_obstacle(self, data: dict):
        r = get_robot()
        title = data.get("title", "")
        x = float(data.get("x", 0.0))
        y = float(data.get("y", 0.0))
        r.nav.update_obstacle_position(title, x, y)
        self._send_json({"status": "ok", "telemetry": r.nav.get_telemetry()})

    def _handle_environment_physics(self, data: dict):
        r = get_robot()
        items = data.get("items", [])
        r.nav.update_environment_physics(items)
        self._send_json({"status": "ok", "items_count": len(r.nav.engine.physical_environment_items), "telemetry": r.nav.get_telemetry()})

    def _handle_environment_physics_delete(self, data: dict):
        r = get_robot()
        title = data.get("title", "")
        r.nav.remove_environment_physics_item(title)
        self._send_json({"status": "ok", "telemetry": r.nav.get_telemetry()})

    def _handle_motor(self, data: dict):
        r = get_robot()
        action = data.get("action", "stop")
        r.nav.set_manual_motion(action)
        self._send_json({"status": "ok", "telemetry": r.nav.get_telemetry()})

    def _handle_directive(self, data: dict):
        r = get_robot()
        action = data.get("action", "")
        target = data.get("target")
        r.nav.execute_directive(action, target)
        self._send_json({"status": "ok", "telemetry": r.nav.get_telemetry()})

    def _handle_mode(self, data: dict):
        r = get_robot()
        mode = data.get("mode", "EXPLORE_ROAM")
        r.nav.set_operating_mode(mode)
        self._send_json({"status": "ok", "operating_mode": r.nav.engine.operating_mode, "telemetry": r.nav.get_telemetry()})

    def _handle_status(self):
        r = get_robot()
        facts = r.db.get_user_facts()
        disc_objects = list(r.nav.engine.discovered_objects.values())
        self._send_json({
            "status": "online" if r.brain.is_online() else "offline",
            "brain_name": f"Google Gemini ({DEFAULT_GEMINI_MODEL})" if r.brain.is_online() else "Local Gemma 2B (Auxiliary Core)",
            "facts_count": len(facts),
            "objects_count": len(disc_objects),
            "discovered_objects": disc_objects,
            "emotion": r.eyes.left_eye.current_emotion.value,
            "gaze_x": r.eyes.left_eye.gaze_x,
            "gaze_y": r.eyes.left_eye.gaze_y,
            "battery_volts": 7.85,
            "voice_enabled": r.voice.voice_enabled
        })

    def _handle_memory(self):
        r = get_robot()
        disc_objects = list(r.nav.engine.discovered_objects.values())
        self._send_json({
            "facts": r.db.get_user_facts(limit=25),
            "objects": disc_objects,
            "observations": r.db.get_recent_observations(limit=15),
            "chat_history": r.db.get_recent_chat(limit=10)
        })

    def _handle_get_expression(self):
        r = get_robot()
        self._send_json(r.eyes.get_state())

    def _handle_set_expression(self, data: dict):
        r = get_robot()
        emo_str = data.get("emotion")
        if emo_str:
            emo = Emotion.from_str(emo_str)
            r.eyes.set_emotion(emo)
            if data.get("gesture", True):
                r.motion.express_emotion(emo)

        if "gaze_x" in data and "gaze_y" in data:
            r.eyes.set_gaze(float(data["gaze_x"]), float(data["gaze_y"]))

        if data.get("blink", False):
            r.eyes.blink()

        if data.get("wink", False):
            r.eyes.wink()

        if data.get("play_sound", False) and emo_str:
            sound_map = {
                "happy": "happy", "curious": "curious", "alert": "alert",
                "excited": "excited", "love": "love", "sad": "sad",
                "confused": "confused", "wink": "wink", "sleep": "shutdown",
                "angry": "angry"
            }
            snd = sound_map.get(emo_str.lower(), "happy")
            r.voice.play_sound(snd)

        self._send_json({
            "status": "success",
            "current_state": r.eyes.get_state()
        })

    def _handle_play_sound(self, data: dict):
        r = get_robot()
        snd_name = data.get("sound", "happy")
        r.voice.play_sound(snd_name)
        self._send_json({"status": "playing", "sound": snd_name})

    def _handle_speak(self, data: dict):
        r = get_robot()
        text = data.get("text", "")
        emo_str = data.get("emotion", "happy")
        emo = Emotion.from_str(emo_str)
        with_chirp = data.get("with_chirp", True)

        r.eyes.set_emotion(emo)
        r.motion.express_emotion(emo)
        r.voice.speak(text, emotion=emo, with_chirp=with_chirp)
        self._send_json({"status": "spoken", "text": text, "emotion": emo.value})

    def _handle_sound_presets(self):
        presets = [
            {"id": "startup", "label": "Startup Chime", "icon": "🎵"},
            {"id": "happy", "label": "Happy Chirp", "icon": "😊"},
            {"id": "curious", "label": "Curious Trill", "icon": "❓"},
            {"id": "excited", "label": "Excited Fanfare", "icon": "⚡"},
            {"id": "alert", "label": "Alert Siren", "icon": "🚨"},
            {"id": "love", "label": "Love Hum", "icon": "💖"},
            {"id": "sad", "label": "Sad Whimper", "icon": "😢"},
            {"id": "bump", "label": "Bump Squeak", "icon": "💥"},
            {"id": "wink", "label": "Wink Twinkle", "icon": "😉"},
            {"id": "confused", "label": "Confused Warble", "icon": "🌀"},
            {"id": "shutdown", "label": "Power Down", "icon": "💤"},
        ]
        self._send_json({"presets": presets})

    def _handle_audio_stream(self, path: str):
        """Generates and serves procedural WAV audio directly to browser."""
        sound_name = path.replace("/api/audio/", "").replace(".wav", "").lower()
        try:
            wav_bytes = WallESoundSynthesizer.generate_sound(sound_name)
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(wav_bytes)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(wav_bytes)
        except Exception as e:
            self.send_error(500, f"Error generating sound: {e}")

    def _handle_chat(self, data: dict):
        user_msg = data.get("message", "").strip()
        if not user_msg:
            self._send_json({"error": "Empty message"}, 400)
            return

        r = get_robot()
        r.eyes.set_emotion(Emotion.ANALYZING)
        chat_res = r.brain.chat_with_emotion(user_msg)

        reply = chat_res["reply"]
        emo = chat_res["emotion"]
        sound_cue = chat_res.get("sound_cue", "happy")

        # Update robot eyes and motion
        r.eyes.set_emotion(emo)
        r.motion.express_emotion(emo)

        # Enforce backend navigation cortex directive
        action = chat_res.get("action")
        target = chat_res.get("target")
        if action:
            if action in ("ROAM", "EXPLORE"):
                r.nav.set_operating_mode("EXPLORE_ROAM")
            elif action in ("DESK", "COMPANION"):
                r.nav.set_operating_mode("DESK_COMPANION")
            elif action in ("HOLD_POSITION", "STOP"):
                r.nav.set_operating_mode("HOLD_POSITION")
            r.nav.execute_directive(action, target)
        r.nav.current_emotion = emo.value
        r.current_directive = {"action": action, "target": target}

        # Optionally speak on PC/Hardware speaker if requested
        if data.get("speak_hardware", False):
            r.voice.speak(reply, emotion=emo, with_chirp=True)

        self._send_json({
            "reply": reply,
            "emotion": emo.value,
            "sound_cue": sound_cue,
            "brain_type": chat_res.get("brain_type", "gemini"),
            "action": action,
            "target": target,
            "telemetry": r.nav.get_telemetry(),
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
        r.motion.curious_tilt()
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
            "brain_name": f"Google Gemini ({DEFAULT_GEMINI_MODEL})" if r.brain.is_online() else "Local Gemma 2B (Auxiliary Core)"
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
    try:
        if os.system("which explorer.exe >/dev/null 2>&1") == 0:
            os.system(f"explorer.exe '{url}' 2>/dev/null &")
        else:
            webbrowser.open(url)
    except Exception:
        pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), SimulatorAPIHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down simulator server. Goodbye!")

if __name__ == "__main__":
    main()
