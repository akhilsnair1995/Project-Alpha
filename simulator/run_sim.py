"""
Project Alpha: Live Simulator Server & Cognitive Streaming Backend.
Serves the digital twin simulator and streams live SQLite memory,
dual-eye expressions, procedural Wall-E audio, Text-to-Speech (TTS),
vision-driven emotion events, and Gemini 2.5 / Local Gemma AI brain responses over REST APIs.
"""

import os
import sys
import time
import json
import io
import base64
import threading
import http.server
import socketserver
import webbrowser
from urllib.parse import urlparse, parse_qs, unquote

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from main import AlphaRobot
from core.config import DEFAULT_GEMINI_MODEL, ALPHA_VOICE_PATH
from core.eye_animator import Emotion
from core.voice_engine import WallESoundSynthesizer
from core.cognitive_loop import GeminiCognitiveLoop

PORT = 8085
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Global singleton robot instance
robot = None
vision_worker = None

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
        # Initialize and attach Gemini conscious cognitive loop
        try:
            cog_loop = GeminiCognitiveLoop(engine=robot.nav.engine)
            robot.nav.attach_cognitive_loop(cog_loop)
            robot.cognitive_loop = cog_loop
            cog_loop.start()
        except Exception as e:
            print(f"[Simulator] Failed to start cognitive loop: {e}")
    return robot

class VisionStreamWorker:
    """Continuously captures frames from laptop camera, tracks faces, and drives Alpha behavior."""

    def __init__(self, robot_inst: AlphaRobot):
        self.robot = robot_inst
        self.running = True
        self.active = True
        self.fps = 0.0
        self.current_jpeg: Optional[bytes] = None
        self.last_res: Optional[FaceTrackingResult] = None
        self.last_action: Optional[BehaviorAction] = None
        self._lock = threading.Lock()
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def _worker_loop(self):
        frames = 0
        last_fps_t = time.time()
        last_reconnect_t = 0.0
        while self.running:
            if not self.active:
                time.sleep(0.08)
                continue

            frame = self.robot.vision.capture_frame()
            if frame is None:
                now = time.time()
                if now - last_reconnect_t > 2.0:
                    last_reconnect_t = now
                    self.robot.vision._init_camera()
                    frame = self.robot.vision.capture_frame()

            if frame is None:
                # If physical camera is not ready or blocked, create a stylized fallback screen
                h, w = 480, 640
                if HAS_CV2:
                    frame = np.zeros((h, w, 3), dtype=np.uint8)
                    cv2.putText(frame, "ALPHA EYE: CONNECTING...", (w // 2 - 140, h // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 150, 180), 1, cv2.LINE_AA)
                time.sleep(0.08)

            # 1. Computer Vision: Face, profile & smile perception
            res = self.robot.vision.track_face_detailed(frame)

            # 2. Emotional Companion Behavior Engine (Only active when Gemini cognitive loop is OFF)
            action = self.robot.behavior.process_vision(res, frame=frame, allow_speech=False)
            cog = getattr(self.robot, "cognitive_loop", None)
            if not (cog and getattr(cog, "is_active", False)):
                self.robot.behavior.apply_action(self.robot, action)

            # 3. Draw Cyber HUD
            hud_frame = self.robot.vision.draw_hud(frame, res, action.state, action.emotion) if frame is not None else None

            # 4. Encode to JPEG for browser streaming
            if hud_frame is not None and HAS_CV2:
                ret, buf = cv2.imencode(".jpg", hud_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                if ret:
                    with self._lock:
                        self.current_jpeg = buf.tobytes()
                        self.last_res = res
                        self.last_action = action

            frames += 1
            now = time.time()
            if now - last_fps_t >= 1.0:
                self.fps = round(frames / (now - last_fps_t), 1)
                frames = 0
                last_fps_t = now

            time.sleep(0.035)  # ~28 FPS

    def stop(self):
        self.running = False

def get_vision_worker() -> VisionStreamWorker:
    global vision_worker
    if vision_worker is None:
        r = get_robot()
        vision_worker = VisionStreamWorker(r)
    return vision_worker

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
        elif path == "/api/cognitive_loop":
            self._handle_get_cognitive_loop()
        elif path == "/api/behavior_status":
            self._handle_behavior_status()
        elif path == "/api/sound_presets":
            self._handle_sound_presets()
        elif path == "/api/persons":
            self._handle_get_persons()
        elif path == "/api/tts":
            self._handle_tts(parsed)
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
        elif parsed.path == "/api/vision_event":
            self._handle_vision_event(data)
        elif parsed.path == "/api/process_frame":
            self._handle_process_frame(data)
        elif parsed.path == "/api/camera_toggle":
            self._handle_camera_toggle(data)
        elif parsed.path == "/api/sound":
            self._handle_play_sound(data)
        elif parsed.path == "/api/speak":
            self._handle_speak(data)
        elif parsed.path == "/api/inspect_frame":
            self._handle_inspect_frame(data)
        elif parsed.path == "/api/sight_object":
            self._handle_sight_object(data)
        elif parsed.path == "/api/cognitive_loop":
            self._handle_post_cognitive_loop(data)
        elif parsed.path == "/api/toggle_brain":
            self._handle_toggle_brain(data)
        elif parsed.path == "/api/transcribe_mic":
            self._handle_transcribe_mic(data)
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

    def _handle_get_cognitive_loop(self):
        r = get_robot()
        cog = getattr(r, "cognitive_loop", None)
        if cog:
            self._send_json(cog.get_status())
        else:
            self._send_json({"is_active": False, "has_client": False, "last_decision": {}})

    def _handle_post_cognitive_loop(self, data: dict):
        r = get_robot()
        cog = getattr(r, "cognitive_loop", None)
        active = data.get("active", True)
        if cog:
            cog.set_active(active)
            self._send_json({"status": "ok", "cognitive_loop": cog.get_status()})
        else:
            self._send_json({"status": "error", "message": "Cognitive loop not attached"}, 400)

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
            "cognitive_loop_active": getattr(getattr(r, "cognitive_loop", None), "is_active", False),
            "voice_enabled": r.voice.voice_enabled
        })

    def _handle_behavior_status(self):
        r = get_robot()
        self._send_json({
            "current_state": r.behavior.current_state.value if hasattr(r, "behavior") else "idle",
            "current_emotion": r.eyes.left_eye.current_emotion.value,
            "gaze_x": r.eyes.left_eye.gaze_x,
            "gaze_y": r.eyes.left_eye.gaze_y,
            "pan": r.motion.current_pan,
            "tilt": r.motion.current_tilt,
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

    def _handle_get_persons(self):
        r = get_robot()
        self._send_json({"persons": r.db.get_known_persons()})

    def _handle_assign_object_owner(self, data: dict):
        r = get_robot()
        obj = data.get("object_name", "").strip()
        owner = data.get("owner_name", "").strip()
        if not obj or not owner:
            self._send_json({"error": "object_name and owner_name are required"}, 400)
            return
        success = r.db.assign_object_owner(obj, owner)
        self._send_json({
            "status": "success" if success else "failed",
            "object_name": obj,
            "owner_name": owner,
            "objects": r.db.find_objects("")
        })

    def _handle_add_or_update_person(self, data: dict):
        r = get_robot()
        name = data.get("name", "").strip()
        rel = data.get("relationship", "friend").strip()
        desc = data.get("visual_description", "").strip()
        notes = data.get("notes", "").strip()
        if not name:
            self._send_json({"error": "name is required"}, 400)
            return
        pid = r.db.get_or_create_person(name, relationship=rel, visual_description=desc, notes=notes)
        self._send_json({
            "status": "success",
            "person_id": pid,
            "persons": r.db.get_known_persons()
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

    def _handle_vision_event(self, data: dict):
        """Processes real-time vision perception events from camera feed."""
        r = get_robot()
        event = data.get("event", "tracking")
        emo_str = data.get("emotion")
        gesture = data.get("gesture")
        sound = data.get("sound")
        gaze_x = data.get("gaze_x")
        gaze_y = data.get("gaze_y")
        pan = data.get("pan")
        tilt = data.get("tilt")
        speech = data.get("speech")

        # 1. Update Gaze
        if gaze_x is not None and gaze_y is not None:
            r.eyes.set_gaze(float(gaze_x), float(gaze_y))

        # 2. Update Neck Servos
        if pan is not None and tilt is not None:
            r.motion.set_head_pose(float(pan), float(tilt))

        # 3. Update Eye Expression
        if emo_str:
            emo = Emotion.from_str(emo_str)
            r.eyes.set_emotion(emo)

        # 4. Execute Physical Gesture
        if gesture and hasattr(r.motion, gesture):
            getattr(r.motion, gesture)()
        elif emo_str and data.get("trigger_gesture", False):
            emo = Emotion.from_str(emo_str)
            r.motion.express_emotion(emo)

        # 5. Play Sound
        if sound:
            r.voice.play_sound(sound)

        # 6. Eye Blink / Wink
        if data.get("wink", False):
            r.eyes.wink()
        elif data.get("blink", False):
            r.eyes.blink()

        # 7. Companion Speech (TTS)
        if speech and r.voice.voice_enabled and data.get("speak_hardware", False):
            emo = Emotion.from_str(emo_str) if emo_str else Emotion.HAPPY
            r.voice.speak(speech, emotion=emo, with_chirp=False)

        # 8. Memory logging for significant companion milestones
        if event == "sustained_contact":
            r.db.log_observation("Maintained sustained affectionate eye contact with Akhil.")
        elif event == "user_smile":
            r.db.log_observation("Akhil smiled warmly at Alpha.")
        elif event == "face_sighted":
            r.db.log_observation("Spotted user in front of camera.")

        self._send_json({
            "status": "success",
            "event": event,
            "current_emotion": r.eyes.left_eye.current_emotion.value,
            "state": r.eyes.get_state()
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
            {"id": "alpha_voice", "label": "Alpha Voice ('I am your pet')", "icon": "🗣️"},
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
        """Generates and serves procedural WAV audio or Alpha's authentic voice directly to browser."""
        sound_name = path.replace("/api/audio/", "").replace(".wav", "").replace(".mp3", "").lower()
        if sound_name in ("alpha_voice", "voice", "voice1", "voice_1"):
            if ALPHA_VOICE_PATH.exists():
                try:
                    with open(ALPHA_VOICE_PATH, "rb") as f:
                        audio_bytes = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/mpeg")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Length", str(len(audio_bytes)))
                    self.send_header("Cache-Control", "public, max-age=3600")
                    self.end_headers()
                    self.wfile.write(audio_bytes)
                    return
                except Exception as e:
                    self.send_error(500, f"Error streaming voice: {e}")
                    return
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

    def _handle_live_visual_reaction(self, data: dict):
        """Processes an on-demand or event-triggered live multimodal snapshot with Gemini Vision."""
        import base64
        r = get_robot()
        b64_data = data.get("image_base64", "")
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]

        image_bytes = None
        if b64_data:
            try:
                image_bytes = base64.b64decode(b64_data)
            except Exception:
                image_bytes = None

        if not image_bytes:
            worker = get_vision_worker()
            with worker._lock:
                image_bytes = worker.current_jpeg
            if not image_bytes:
                frame = r.vision.capture_frame()
                if frame is not None and HAS_CV2:
                    _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    image_bytes = buf.tobytes()

        if not image_bytes:
            self._send_json({"error": "No image frame available from camera or browser"}, 400)
            return

        r.eyes.set_emotion(Emotion.ANALYZING)
        context = {
            "event": data.get("event", "companion_live_observation"),
            "distance": data.get("distance", "optimal"),
            "is_smiling": bool(data.get("is_smiling", False)),
            "pan": float(data.get("pan", r.motion.current_pan)),
            "tilt": float(data.get("tilt", r.motion.current_tilt)),
        }
        res = r.brain.react_to_live_visual(image_bytes, context)
        emo = res.get("emotion", Emotion.HAPPY)
        r.eyes.set_emotion(emo)
        gesture = res.get("gesture")
        if gesture and hasattr(r.motion, gesture):
            getattr(r.motion, gesture)()
        sound = res.get("sound")
        if sound:
            r.voice.play_sound(sound)

        speech = res.get("speech", "")
        if data.get("speak_hardware", False) and r.voice.voice_enabled and speech:
            r.voice.speak(speech, emotion=emo, with_chirp=True)

        self._send_json({
            "status": "success",
            "speech": speech,
            "inner_thought": res.get("inner_thought", ""),
            "observed_visual": res.get("observed_visual", ""),
            "num_persons": res.get("num_persons", 1),
            "identified_persons": res.get("identified_persons", []),
            "detected_objects": res.get("detected_objects", []),
            "emotion": emo.value,
            "sound": sound,
            "gesture": gesture,
            "brain_type": res.get("brain_type", "gemini_multimodal_vision"),
            "persons": r.db.get_known_persons(),
            "objects": r.db.find_objects("")
        })

    def _handle_organic_stimulus(self, data: dict):
        """Processes real-time sensory stimulus through Gemini neural cortex."""
        r = get_robot()
        stimulus = {
            "event": data.get("event", "companion_idle"),
            "duration": float(data.get("sustained_sec", data.get("duration", 0.0))),
            "distance": data.get("distance", "optimal"),
            "is_smiling": bool(data.get("is_smiling", False)),
            "pan": float(data.get("pan", r.motion.current_pan)),
            "tilt": float(data.get("tilt", r.motion.current_tilt)),
        }
        res = r.brain.react_to_organic_stimulus(stimulus)

        emo = res.get("emotion", Emotion.HAPPY)
        r.eyes.set_emotion(emo)
        gesture = res.get("gesture")
        if gesture and hasattr(r.motion, gesture):
            getattr(r.motion, gesture)()
        sound = res.get("sound")
        if sound:
            r.voice.play_sound(sound)

        if data.get("speak_hardware", False) and r.voice.voice_enabled:
            r.voice.speak(res.get("speech", ""), emotion=emo, with_chirp=True)

        self._send_json({
            "status": "success",
            "event": stimulus["event"],
            "speech": res.get("speech", ""),
            "inner_thought": res.get("inner_thought", ""),
            "emotion": emo.value,
            "sound": sound,
            "gesture": gesture,
            "brain_type": res.get("brain_type", "gemini_organic")
        })

    def _handle_tts(self, parsed, data: dict = None):
        """Streams high-fidelity neural MP3 speech matching Voice 1.mp3 to browser."""
        r = get_robot()
        text = ""
        emo_str = "happy"
        if data and isinstance(data, dict):
            text = data.get("text", "")
            emo_str = data.get("emotion", "happy")
        else:
            query = parse_qs(parsed.query)
            text = query.get("text", [""])[0]
            emo_str = query.get("emotion", ["happy"])[0]

        emo = Emotion.from_str(emo_str)
        audio_bytes = r.voice.get_neural_speech_bytes(text, emotion=emo)
        if not audio_bytes:
            audio_bytes = r.voice.get_alpha_voice_bytes()

        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(audio_bytes)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(audio_bytes)

    def _handle_transcribe_mic(self, data: dict):
        """Transcribes incoming microphone audio stream from browser into text using speech recognition."""
        b64_audio = data.get("audio_base64", "")
        if not b64_audio:
            self._send_json({"error": "Empty audio payload", "transcript": "", "status": "empty"}, 400)
            return

        if "," in b64_audio:
            b64_audio = b64_audio.split(",", 1)[1]

        try:
            import speech_recognition as sr
            import wave
            audio_bytes = base64.b64decode(b64_audio)

            # If raw PCM without RIFF header, wrap as standard 16kHz WAV
            if not audio_bytes.startswith(b"RIFF"):
                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(audio_bytes)
                audio_bytes = wav_io.getvalue()

            transcript = ""
            r_stt = sr.Recognizer()
            try:
                with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                    audio_data = r_stt.record(source)
                transcript = r_stt.recognize_google(audio_data)
            except Exception as stt_e:
                # If Google STT failed or threw UnknownValueError, try Gemini 2.5 Audio
                r = get_robot()
                if r.brain.is_online():
                    try:
                        from google.genai import types
                        prompt = "Transcribe the user's spoken voice command or question accurately. Return ONLY the transcribed text."
                        resp = r.brain.client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[
                                prompt,
                                types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")
                            ]
                        )
                        if resp.text:
                            transcript = resp.text.strip().replace('"', '')
                    except Exception as ge:
                        print(f"[TranscribeMic] Gemini audio fallback notice: {ge}")

            auto_reply = None
            if data.get("auto_chat", False) and transcript:
                r = get_robot()
                r.eyes.set_emotion(Emotion.ANALYZING)
                cog = getattr(r, "cognitive_loop", None)
                if cog and getattr(cog, "is_active", False) and getattr(cog, "_client", None):
                    chat_res = cog.process_user_turn(transcript)
                    reply = chat_res.get("reply", "*Whirrr-chirp!*")
                    emo_val = chat_res.get("emotion", "happy")
                    emo = Emotion.from_str(emo_val) if isinstance(emo_val, str) else emo_val
                    sound_cue = chat_res.get("sound_cue", "happy")
                    action = chat_res.get("action")
                    target = chat_res.get("target")
                    brain_type = chat_res.get("brain_type", "gemini_unified")
                    auto_reply = {
                        "reply": reply,
                        "emotion": emo.value if hasattr(emo, "value") else str(emo),
                        "sound": sound_cue,
                        "action": action,
                        "target": target,
                        "brain_type": brain_type
                    }
                    r.db.save_chat_message("user", transcript)
                    r.db.save_chat_message("assistant", reply, brain_type=brain_type)
                else:
                    chat_res = r.brain.chat_with_emotion(transcript)
                    emo = chat_res["emotion"]
                    auto_reply = {
                        "reply": chat_res["reply"],
                        "emotion": emo.value if hasattr(emo, "value") else str(emo),
                        "sound": chat_res.get("sound_cue", "happy"),
                        "action": chat_res.get("action"),
                        "target": chat_res.get("target"),
                        "brain_type": chat_res.get("brain_type", "gemini")
                    }

                r.eyes.set_emotion(emo)
                r.motion.express_emotion(emo)
                if auto_reply.get("sound"):
                    r.voice.play_sound(auto_reply["sound"])

            self._send_json({
                "status": "success",
                "transcript": transcript,
                "auto_reply": auto_reply
            })
        except Exception as e:
            err_name = type(e).__name__
            if "UnknownValueError" in err_name:
                self._send_json({"status": "silence", "transcript": ""})
            else:
                self._send_json({"status": "error", "error": str(e), "transcript": ""})

    def _handle_chat(self, data: dict):
        user_msg = data.get("message", "").strip()
        if not user_msg:
            self._send_json({"error": "Empty message"}, 400)
            return

        r = get_robot()
        r.eyes.set_emotion(Emotion.ANALYZING)

        cog = getattr(r, "cognitive_loop", None)
        if cog and getattr(cog, "is_active", False) and getattr(cog, "_client", None):
            # UNIFIED BRAIN: Use the cognitive loop directly so speech & actions come from the same reasoning!
            chat_res = cog.process_user_turn(user_msg)
            reply = chat_res.get("reply", "*Whirrr-chirp!*")
            emo_val = chat_res.get("emotion", "happy")
            emo = Emotion.from_str(emo_val) if isinstance(emo_val, str) else emo_val
            sound_cue = chat_res.get("sound_cue", "happy")
            action = chat_res.get("action")
            target = chat_res.get("target")
            brain_type = chat_res.get("brain_type", "gemini_unified")
            r.db.save_chat_message("user", user_msg)
            r.db.save_chat_message("assistant", reply, brain_type=brain_type)
        else:
            chat_res = r.brain.chat_with_emotion(user_msg)
            reply = chat_res["reply"]
            emo = chat_res["emotion"]
            sound_cue = chat_res.get("sound_cue", "happy")
            action = chat_res.get("action")
            target = chat_res.get("target")
            brain_type = chat_res.get("brain_type", "gemini")

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

    def _handle_camera_stream(self):
        """Streams real-time MJPEG camera stream directly to browser <img> tag."""
        worker = get_vision_worker()
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            while worker.running:
                with worker._lock:
                    jpeg = worker.current_jpeg
                if jpeg:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode("utf-8"))
                    self.wfile.write(jpeg)
                    self.wfile.write(b"\r\n")
                time.sleep(0.04)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle_vision_state(self):
        """Returns real-time perception and behavior telemetry."""
        r = get_robot()
        worker = get_vision_worker()
        with worker._lock:
            res = worker.last_res
            act = worker.last_action
            sound_event = None
            if act and act.sound:
                sound_event = act.sound
                act.sound = None  # One-shot consumption so sound only emits once

        self._send_json({
            "active": worker.active,
            "fps": worker.fps,
            "found": res.found if res else False,
            "num_faces": getattr(res, "num_faces", 1) if res and res.found else 0,
            "identified_name": getattr(act, "identified_name", None) or getattr(res, "identified_name", None),
            "all_faces": getattr(res, "all_faces", []) if res else [],
            "offset_x": res.offset_x if res else 0.0,
            "offset_y": res.offset_y if res else 0.0,
            "confidence": res.confidence if res else 0.0,
            "distance_category": res.distance_category if res else "optimal",
            "is_smiling": res.is_smiling if res else False,
            "state": act.state.value if act else "idle",
            "emotion": act.emotion.value if act else r.eyes.left_eye.current_emotion.value,
            "gaze_x": act.gaze_x if act else r.eyes.left_eye.gaze_x,
            "gaze_y": act.gaze_y if act else r.eyes.left_eye.gaze_y,
            "pan": act.target_pan if act else r.motion.current_pan,
            "tilt": act.target_tilt if act else r.motion.current_tilt,
            "sound": sound_event,
            "gesture": act.gesture if act else None,
            "speech_message": act.speech_message if act else None,
            "inner_thought": act.inner_thought if act else None,
            "observed_visual": act.observed_visual if act else None,
            "trigger_wink": act.trigger_wink if act else False,
            "trigger_blink": act.trigger_blink if act else False,
            "detected_objects": getattr(res, "detected_objects", []) if res else [],
            "user_emotion": getattr(res, "user_emotion", "neutral") if res else "neutral",
        })

    def _handle_camera_toggle(self, data: dict):
        worker = get_vision_worker()
        mode = data.get("mode")
        if mode == "start":
            worker.active = True
            if not (worker.robot.vision.cap and worker.robot.vision.cap.isOpened()):
                worker.robot.vision._init_camera()
        elif mode == "stop":
            worker.active = False
            worker.robot.vision.release()
        else:
            worker.active = not worker.active
            if worker.active:
                if not (worker.robot.vision.cap and worker.robot.vision.cap.isOpened()):
                    worker.robot.vision._init_camera()
            else:
                worker.robot.vision.release()
        self._send_json({"active": worker.active})

    def _handle_process_frame(self, data: dict):
        """Processes a frame submitted from the browser canvas through Python OpenCV."""
        b64_data = data.get("image_base64", "")
        r = get_robot()
        frame = r.vision.decode_base64_frame(b64_data)
        if frame is None:
            self._send_json({"error": "Failed to decode frame"}, 400)
            return

        res = r.vision.track_face_detailed(frame)
        action = r.behavior.process_vision(res, frame=frame, allow_speech=False)
        r.behavior.apply_action(r, action)

        self._send_json({
            "found": res.found,
            "offset_x": res.offset_x,
            "offset_y": res.offset_y,
            "confidence": res.confidence,
            "distance_category": res.distance_category,
            "is_smiling": res.is_smiling,
            "state": action.state.value,
            "emotion": action.emotion.value,
            "pan": action.target_pan,
            "tilt": action.target_tilt,
            "sound": action.sound,
            "gesture": action.gesture,
            "speech_message": action.speech_message,
            "inner_thought": action.inner_thought,
            "observed_visual": action.observed_visual,
            "trigger_wink": action.trigger_wink,
            "trigger_blink": action.trigger_blink,
            "detected_objects": getattr(res, "detected_objects", []),
            "user_emotion": getattr(res, "user_emotion", "neutral"),
        })

    def _handle_inspect_frame(self, data: dict):
        import base64
        r = get_robot()
        b64_data = data.get("image_base64", "")
        room_name = data.get("room", "Work Desk")
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]

        try:
            if b64_data:
                image_bytes = base64.b64decode(b64_data)
            else:
                # Capture frame directly from robot vision or active worker jpeg
                frame = r.vision.capture_frame()
                if frame is not None and HAS_CV2:
                    _, buf = cv2.imencode(".jpg", frame)
                    image_bytes = buf.tobytes()
                else:
                    worker = get_vision_worker()
                    with worker._lock:
                        image_bytes = worker.current_jpeg
                    if not image_bytes:
                        raise ValueError("No frame available from laptop camera.")

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
    r = get_robot()
    worker = get_vision_worker()
    print(f"[Simulator] Laptop Camera Vision Stream Cortex: ACTIVE")
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

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), SimulatorAPIHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down simulator server. Goodbye!")
            worker.stop()
            r.vision.release()

if __name__ == "__main__":
    main()
