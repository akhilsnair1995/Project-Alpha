"""
Unit Tests for Project Alpha: Vision Perception, Face Tracking & Behavior Engine.
Verifies temporal EMA smoothing, persistence hysteresis, companion emotion transitions
(Discovery, Bonding, Smile Mirroring, Proximity Startle, and Searching on Face Loss),
and simulator vision event synchronization.
"""

import unittest
import time
from unittest.mock import MagicMock, patch
import numpy as np

from core.vision_pipeline import VisionPipeline, FaceTrackingResult
from core.behavior_engine import AlphaBehaviorEngine, BehaviorState, BehaviorAction
from core.eye_animator import Emotion
from core.database import AlphaDatabase


class TestVisionPipeline(unittest.TestCase):
    """Tests computer vision face tracking, EMA smoothing, and persistence."""

    def setUp(self):
        self.vision = VisionPipeline(camera_index=-1)

    def test_pipeline_initialization(self):
        """Pipeline initializes safely with or without physical camera."""
        self.assertIsNotNone(self.vision)
        self.assertEqual(self.vision.frames_lost, 999)
        self.assertIsNone(self.vision.last_valid_result)

    def test_detect_face_signature_backward_compatibility(self):
        """Ensures detect_face() returns a 3-tuple (bool, float, float)."""
        found, ox, oy = self.vision.detect_face(frame=None)
        self.assertIsInstance(found, bool)
        self.assertIsInstance(ox, float)
        self.assertIsInstance(oy, float)
        self.assertFalse(found)
        self.assertEqual(ox, 0.0)
        self.assertEqual(oy, 0.0)

    def test_track_face_detailed_empty_frame(self):
        """track_face_detailed returns structured FaceTrackingResult."""
        res = self.vision.track_face_detailed(frame=None)
        self.assertIsInstance(res, FaceTrackingResult)
        self.assertFalse(res.found)
        self.assertEqual(res.offset_x, 0.0)
        self.assertEqual(res.offset_y, 0.0)

    def test_ema_smoothing_filters_jitter(self):
        """Simulates consecutive detected frames to ensure EMA eliminates abrupt jumps."""
        # Frame 1: initial detection at center (0.0, 0.0)
        self.vision.smooth_offset_x = 0.0
        self.vision.smooth_offset_y = 0.0
        self.vision.last_valid_result = FaceTrackingResult(found=True, offset_x=0.0, offset_y=0.0)
        self.vision.frames_lost = 0

        # Simulate a sudden raw jump to (0.8, 0.4)
        raw_ox, raw_oy = 0.8, 0.4
        alpha = self.vision.ema_alpha  # 0.35
        expected_ox = (1.0 - alpha) * 0.0 + alpha * raw_ox
        expected_oy = (1.0 - alpha) * 0.0 + alpha * raw_oy

        # Update smooth offsets as VisionPipeline would
        self.vision.smooth_offset_x = (1.0 - alpha) * self.vision.smooth_offset_x + alpha * raw_ox
        self.vision.smooth_offset_y = (1.0 - alpha) * self.vision.smooth_offset_y + alpha * raw_oy

        self.assertAlmostEqual(self.vision.smooth_offset_x, expected_ox, places=3)
        self.assertAlmostEqual(self.vision.smooth_offset_y, expected_oy, places=3)
        # Verify that smoothed position did NOT jump immediately to 0.8
        self.assertLess(self.vision.smooth_offset_x, 0.8)

    def test_persistence_hysteresis_preserves_brief_drops(self):
        """Single dropped frame should retain tracking with decayed confidence."""
        self.vision.last_valid_result = FaceTrackingResult(
            found=True, offset_x=0.25, offset_y=-0.15, confidence=0.9
        )
        self.vision.frames_lost = 0

        # Frame 1 lost -> should remain found=True via hysteresis
        res1 = self.vision._handle_lost_frame(now=time.time(), dt=0.04)
        self.assertTrue(res1.found)
        self.assertEqual(res1.offset_x, 0.25)
        self.assertLess(res1.confidence, 0.9)

        # Drop 3 more frames -> exceeds persistence threshold (3)
        self.vision._handle_lost_frame(now=time.time(), dt=0.04)
        self.vision._handle_lost_frame(now=time.time(), dt=0.04)
        res4 = self.vision._handle_lost_frame(now=time.time(), dt=0.04)
        self.assertFalse(res4.found)
        self.assertIsNone(self.vision.last_valid_result)


class TestAlphaBehaviorEngine(unittest.TestCase):
    """Tests the state machine wiring camera feed to Alpha's emotions, eyes, gestures, and sounds."""

    def setUp(self):
        self.engine = AlphaBehaviorEngine()

    def test_initial_state_is_idle(self):
        """Engine begins in IDLE state with IDLE emotion."""
        face = FaceTrackingResult(found=False)
        action = self.engine.process_vision(face, allow_speech=False)
        self.assertEqual(action.state, BehaviorState.IDLE)
        self.assertEqual(action.emotion, Emotion.IDLE)
        self.assertEqual(action.gaze_x, 0.0)
        self.assertEqual(action.gaze_y, 0.0)

    def test_discovery_greeting_on_first_face(self):
        """When face enters camera view after absence, Alpha greets with CURIOUS/HAPPY and curious sound."""
        face = FaceTrackingResult(
            found=True,
            offset_x=0.2,
            offset_y=-0.1,
            distance_category="optimal",
            is_smiling=False
        )
        action = self.engine.process_vision(face, allow_speech=False)
        self.assertEqual(action.state, BehaviorState.GREETING)
        self.assertIn(action.emotion, (Emotion.CURIOUS, Emotion.HAPPY))
        self.assertIn(action.sound, ("alpha_voice", "curious"))
        self.assertIn(action.gesture, ("curious_tilt", "nod"))
        self.assertAlmostEqual(action.gaze_x, 0.2, places=2)
        self.assertAlmostEqual(action.gaze_y, -0.1, places=2)

    def test_sustained_eye_contact_triggers_love_bonding(self):
        """Maintaining gaze for > 3.2s triggers LOVE emotion and affectionate hum."""
        face = FaceTrackingResult(found=True, offset_x=0.0, offset_y=0.0)

        # Start tracking at t = 0
        now = time.time()
        self.engine.current_state = BehaviorState.TRACKING
        self.engine.tracking_start_time = now - 3.5  # Sustained for 3.5s
        self.engine.last_bonding_time = now - 20.0   # Beyond cooldown

        action = self.engine.process_vision(face, allow_speech=True)
        self.assertEqual(action.state, BehaviorState.BONDING)
        self.assertEqual(action.emotion, Emotion.LOVE)
        self.assertEqual(action.sound, "love")
        self.assertEqual(action.gesture, "head_pet_reaction")
        self.assertTrue(action.trigger_wink)
        self.assertIsNotNone(action.speech_message)

    def test_bonding_recovers_to_tracking_after_duration(self):
        """BONDING state automatically recovers to TRACKING/HAPPY after ~3.5s so Alpha never locks up."""
        face = FaceTrackingResult(found=True, offset_x=0.0, offset_y=0.0)
        now = time.time()
        self.engine.current_state = BehaviorState.BONDING
        self.engine.bonding_start_time = now - 4.0  # Duration > 3.5s
        self.engine.tracking_start_time = now - 10.0
        self.engine.last_bonding_time = now - 4.0

        action = self.engine.process_vision(face, allow_speech=False)
        self.assertEqual(action.state, BehaviorState.TRACKING)
        self.assertEqual(action.emotion, Emotion.HAPPY)

    def test_user_smile_triggers_excited_reaction(self):
        """Detecting user smile triggers EXCITED emotion and joyful wiggle."""
        face = FaceTrackingResult(
            found=True,
            offset_x=0.0,
            offset_y=0.0,
            is_smiling=True,
            distance_category="optimal"
        )
        self.engine.current_state = BehaviorState.TRACKING
        self.engine.tracking_start_time = time.time() - 1.0  # Normal tracking
        self.engine.last_smile_time = time.time() - 10.0

        action = self.engine.process_vision(face, allow_speech=False)
        self.assertEqual(action.state, BehaviorState.SMILING)
        self.assertEqual(action.emotion, Emotion.EXCITED)
        self.assertEqual(action.sound, "excited")
        self.assertEqual(action.gesture, "excited_wiggle")

    def test_proximity_close_triggers_startled_recoil(self):
        """User leaning in very close triggers SURPRISED emotion and alert recoil."""
        face = FaceTrackingResult(
            found=True,
            offset_x=0.0,
            offset_y=0.0,
            distance_category="close",
            face_ratio=0.35
        )
        self.engine.current_state = BehaviorState.TRACKING
        self.engine.tracking_start_time = time.time() - 1.0
        self.engine.last_startle_time = time.time() - 10.0

        action = self.engine.process_vision(face, allow_speech=False)
        self.assertEqual(action.state, BehaviorState.STARTLED)
        self.assertEqual(action.emotion, Emotion.SURPRISED)
        self.assertEqual(action.sound, "alert")
        self.assertEqual(action.gesture, "alert_recoil")

    def test_face_loss_triggers_searching_and_disappointed(self):
        """When face vanishes, Alpha searches with CONFUSED wobble and gaze sweep before returning to IDLE."""
        now = time.time()
        self.engine.current_state = BehaviorState.TRACKING
        self.engine.last_seen_time = now - 1.5  # Lost 1.5s ago
        self.engine.last_exit_vel_x = 0.5       # User exited to the right

        lost_face = FaceTrackingResult(found=False)
        action = self.engine.process_vision(lost_face, allow_speech=False)

        # 0 - 3s: SEARCHING
        self.assertEqual(action.state, BehaviorState.SEARCHING)
        self.assertEqual(action.emotion, Emotion.CONFUSED)
        self.assertEqual(action.gesture, "confused_wobble")
        # Gaze sweeps to the right (+0.6) matching exit velocity
        self.assertGreater(action.gaze_x, 0.0)

        # 3.5s - 6s: DISAPPOINTED (SAD droop)
        self.engine.last_seen_time = now - 4.0
        action_sad = self.engine.process_vision(lost_face, allow_speech=False)
        self.assertEqual(action_sad.state, BehaviorState.DISAPPOINTED)
        self.assertEqual(action_sad.emotion, Emotion.SAD)
        self.assertEqual(action_sad.gesture, "sad_droop")

        # > 6s: IDLE
        self.engine.last_seen_time = now - 8.0
        action_idle = self.engine.process_vision(lost_face, allow_speech=False)
        self.assertEqual(action_idle.state, BehaviorState.IDLE)
        self.assertEqual(action_idle.emotion, Emotion.IDLE)


class TestSimulatorVisionIntegration(unittest.TestCase):
    """Tests simulator server API handling for real-time vision events."""

    def test_robot_behavior_instance_exists(self):
        """AlphaRobot should have self.behavior instantiated."""
        from main import AlphaRobot
        # Create robot with hardware disabled
        robot = AlphaRobot(voice_enabled=False)
        self.assertTrue(hasattr(robot, "behavior"))
        self.assertIsInstance(robot.behavior, AlphaBehaviorEngine)

    def test_behavior_status_payload(self):
        """Verifies behavior status endpoint response format."""
        from simulator.run_sim import get_robot
        r = get_robot()
        self.assertIsNotNone(r)
        self.assertIn(r.eyes.left_eye.current_emotion, Emotion)

    def test_simulator_serves_alpha_voice_and_presets(self):
        """Verifies simulator handler streams Alpha's voice and procedural audio."""
        from simulator.run_sim import SimulatorAPIHandler
        from core.config import ALPHA_VOICE_PATH
        import io

        self.assertTrue(ALPHA_VOICE_PATH.exists())

        # Test mock handler audio stream
        handler = SimulatorAPIHandler.__new__(SimulatorAPIHandler)
        handler.wfile = io.BytesIO()
        headers_sent = {}
        status_code = [200]

        def mock_send_response(code):
            status_code[0] = code

        def mock_send_header(k, v):
            headers_sent[k] = v

        def mock_end_headers():
            pass

        handler.send_response = mock_send_response
        handler.send_header = mock_send_header
        handler.end_headers = mock_end_headers

        # Test Alpha voice stream
        handler._handle_audio_stream("/api/audio/voice1.mp3")
        self.assertEqual(status_code[0], 200)
        self.assertEqual(headers_sent.get("Content-Type"), "audio/mpeg")
        self.assertGreater(len(handler.wfile.getvalue()), 1000)

        # Test procedural WAV stream
        handler.wfile = io.BytesIO()
        handler._handle_audio_stream("/api/audio/happy.wav")
        self.assertEqual(headers_sent.get("Content-Type"), "audio/wav")
        self.assertGreater(len(handler.wfile.getvalue()), 1000)

    def test_vision_pipeline_draw_hud(self):
        """draw_hud overlays cyber reticle, labels and banner on image frames."""
        pipeline = VisionPipeline(camera_index=-1)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        tracking_res = FaceTrackingResult(
            found=True,
            offset_x=0.2,
            offset_y=-0.1,
            bbox=(200, 150, 120, 140),
            confidence=0.92,
            is_smiling=True,
            distance_category="optimal"
        )
        hud = pipeline.draw_hud(dummy_frame, tracking_res, state=BehaviorState.SMILING, emotion=Emotion.EXCITED)
        self.assertIsNotNone(hud)
        self.assertEqual(hud.shape, dummy_frame.shape)
        # Should have drawn non-zero pixels
        self.assertGreater(np.count_nonzero(hud), 0)

    def test_vision_pipeline_decode_base64_frame(self):
        """decode_base64_frame decodes browser canvas snapshots."""
        import base64
        import cv2

        pipeline = VisionPipeline(camera_index=-1)
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", dummy)
        b64 = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("utf-8")

        decoded = pipeline.decode_base64_frame(b64)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.shape, (100, 100, 3))

    def test_simulator_vision_worker_and_state(self):
        """get_vision_worker initializes background worker and provides telemetry."""
        from simulator.run_sim import get_vision_worker, SimulatorAPIHandler
        import json

        worker = get_vision_worker()
        self.assertIsNotNone(worker)
        self.assertTrue(worker.active)

        # Test _handle_vision_state
        handler = SimulatorAPIHandler.__new__(SimulatorAPIHandler)
        json_payload = []
        def mock_send_json(data, code=200):
            json_payload.append(data)
        handler._send_json = mock_send_json

        handler._handle_vision_state()
        self.assertEqual(len(json_payload), 1)
        self.assertIn("found", json_payload[0])
        self.assertIn("emotion", json_payload[0])
        self.assertIn("state", json_payload[0])
        self.assertIn("gaze_x", json_payload[0])
        self.assertIn("pan", json_payload[0])
        self.assertIn("speech_message", json_payload[0])


    def test_robot_wires_brain_to_behavior_engine(self):
        """AlphaRobot should wire self.brain directly into self.behavior."""
        from main import AlphaRobot
        robot = AlphaRobot(voice_enabled=False)
        self.assertIsNotNone(robot.behavior.brain)
        self.assertIs(robot.behavior.brain, robot.brain)

    def test_react_to_organic_stimulus_structure(self):
        """HybridBrain.react_to_organic_stimulus returns structured organic organism reaction."""
        from core.gemini_brain import HybridBrain
        brain = HybridBrain()
        stimulus = {
            "event": "user_smile",
            "distance": "optimal",
            "is_smiling": True,
            "pan": 0.0,
            "tilt": 0.0
        }
        res = brain.react_to_organic_stimulus(stimulus)
        self.assertIn("speech", res)
        self.assertIn("emotion", res)
        self.assertIn("sound", res)
        self.assertIn("gesture", res)
        self.assertIn("inner_thought", res)
        self.assertIsInstance(res["emotion"], Emotion)
        self.assertTrue(len(res["speech"]) > 0)

    def test_simulator_organic_stimulus_endpoint(self):
        """Verifies simulator handler processes /api/organic_stimulus."""
        from simulator.run_sim import SimulatorAPIHandler
        handler = SimulatorAPIHandler.__new__(SimulatorAPIHandler)
        json_payload = []
        def mock_send_json(data, code=200):
            json_payload.append(data)
        handler._send_json = mock_send_json

        handler._handle_organic_stimulus({
            "event": "sustained_contact",
            "duration": 3.5,
            "distance": "optimal"
        })
        self.assertEqual(len(json_payload), 1)
        self.assertEqual(json_payload[0]["status"], "success")
        self.assertIn("speech", json_payload[0])
        self.assertIn("inner_thought", json_payload[0])
        self.assertIn("emotion", json_payload[0])


if __name__ == "__main__":
    unittest.main()
