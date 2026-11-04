"""
Project Alpha: Vision Pipeline & Computer Vision Cortex.
Performs real-time face tracking with temporal EMA smoothing, profile resilience,
smile/emotion cues, proximity classification, and ArUco dock homing.
"""

import time
import os
import sys
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
import numpy as np

# Lazy OpenCV import for graceful fallback
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from core.config import IS_RASPBERRY_PI, ARUCO_DOCK_ID


@dataclass
class FaceTrackingResult:
    """Rich sensory perception result from camera face tracking."""
    found: bool = False
    offset_x: float = 0.0          # Normalized -1.0 (Left) to +1.0 (Right)
    offset_y: float = 0.0          # Normalized -1.0 (Up) to +1.0 (Down)
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0) # (x, y, w, h) of primary face
    face_ratio: float = 0.0        # Ratio of frame area covered by face (0.0 to 1.0)
    distance_category: str = "optimal" # "close", "optimal", "far"
    is_smiling: bool = False
    confidence: float = 0.0        # 0.0 to 1.0
    velocity_x: float = 0.0        # Motion speed horizontally
    velocity_y: float = 0.0        # Motion speed vertically
    num_faces: int = 0             # Total count of detected persons
    all_faces: list = None         # List of (x, y, w, h) for all detected people
    identified_name: Optional[str] = None # Name of identified person (if resolved)

    def __post_init__(self):
        if self.all_faces is None:
            self.all_faces = []


class VisionPipeline:
    """Handles camera capture, stabilized face tracking, and dock fiducial tracking."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None
        self.face_cascade = None
        self.profile_cascade = None
        self.smile_cascade = None
        self.clahe = None
        self.prev_gray_frame = None

        # Temporal EMA smoothing & persistence state
        self.smooth_offset_x = 0.0
        self.smooth_offset_y = 0.0
        self.smooth_w = 0.0
        self.smooth_h = 0.0
        self.prev_face_center: Optional[Tuple[float, float]] = None
        self.prev_detect_time = 0.0
        self.frames_lost = 999
        self.persistence_threshold = 3  # Tolerate up to 3 dropped frames before losing track
        self.last_valid_result: Optional[FaceTrackingResult] = None
        self.ema_alpha = 0.35           # Smoothing factor (0.35 gives crisp responsiveness without jitter)
        self._last_reconnect_attempt = 0.0
        self.face_cascade_default = None
        self.face_cascade_alt2 = None

        if HAS_OPENCV:
            self._init_camera()
            self._init_face_detector()
            try:
                self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            except Exception:
                self.clahe = None
        else:
            print("[VisionPipeline] OpenCV (cv2) not installed. Running in mock vision mode.")

    def _init_camera(self) -> None:
        """Initializes OpenCV video capture with multi-backend fallback and warm-up verification."""
        try:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

            if self.camera_index < 0:
                print(f"[VisionPipeline] Camera index {self.camera_index} invalid. Running in simulated vision mode.")
                return

            # Multi-backend fallback: MSMF (Windows Media Foundation), CAP_ANY, DSHOW (DirectShow)
            backends = [cv2.CAP_ANY, cv2.CAP_MSMF, cv2.CAP_DSHOW] if sys.platform == "win32" else [cv2.CAP_V4L2, cv2.CAP_ANY]

            # Try candidate backends and indices (0 and 1)
            indices_to_try = [self.camera_index] if self.camera_index != 0 else [0, 1]
            for idx in indices_to_try:
                for b in backends:
                    try:
                        cap = cv2.VideoCapture(idx, b)
                        if cap.isOpened():
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            # Warm up read verification (up to 3 tries)
                            for _ in range(3):
                                ret, test_f = cap.read()
                                if ret and test_f is not None and getattr(test_f, "size", 0) > 0:
                                    self.cap = cap
                                    self.camera_index = idx
                                    print(f"[VisionPipeline] Camera #{idx} opened successfully (backend {b}, 640x480).")
                                    return
                            cap.release()
                    except Exception:
                        pass

            print(f"[VisionPipeline] Camera #{self.camera_index} not accessible (all backends failed or in-use by another application).")
        except Exception as e:
            print(f"[VisionPipeline] Camera init error: {e}")

    def _init_face_detector(self) -> None:
        """Loads OpenCV Haar cascades with dual frontal fallback and profile/smile detection."""
        try:
            cascade_dir = cv2.data.haarcascades
            default_path = os.path.join(cascade_dir, "haarcascade_frontalface_default.xml")
            alt2_path = os.path.join(cascade_dir, "haarcascade_frontalface_alt2.xml")
            profile_path = os.path.join(cascade_dir, "haarcascade_profileface.xml")
            smile_path = os.path.join(cascade_dir, "haarcascade_smile.xml")

            if os.path.exists(default_path):
                self.face_cascade_default = cv2.CascadeClassifier(default_path)
            else:
                self.face_cascade_default = None

            if os.path.exists(alt2_path):
                self.face_cascade_alt2 = cv2.CascadeClassifier(alt2_path)
            else:
                self.face_cascade_alt2 = None

            # Primary face cascade is default (most sensitive & reliable under webcams) or alt2
            self.face_cascade = self.face_cascade_default or self.face_cascade_alt2

            if os.path.exists(profile_path):
                self.profile_cascade = cv2.CascadeClassifier(profile_path)
            else:
                self.profile_cascade = None

            if os.path.exists(smile_path):
                self.smile_cascade = cv2.CascadeClassifier(smile_path)
            else:
                self.smile_cascade = None

            print(f"[VisionPipeline] Loaded detectors: frontal_default={self.face_cascade_default is not None}, frontal_alt2={self.face_cascade_alt2 is not None}, profile={self.profile_cascade is not None}, smile={self.smile_cascade is not None}")
        except Exception as e:
            print(f"[VisionPipeline] Could not load face cascades: {e}")

    def capture_frame(self) -> Optional[np.ndarray]:
        """Captures a single BGR frame from the camera with auto-reconnect."""
        if self.cap is None or not self.cap.isOpened():
            now = time.time()
            if now - self._last_reconnect_attempt > 3.0:
                self._last_reconnect_attempt = now
                self._init_camera()

        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None and getattr(frame, "size", 0) > 0:
                self.frames_lost = 0
                return frame
            if not ret:
                self.frames_lost += 1
                if self.frames_lost > 35:
                    self.release()
        return None

    def track_face_detailed(self, frame: Optional[np.ndarray] = None) -> FaceTrackingResult:
        """
        Performs high-stability face tracking with temporal EMA smoothing,
        profile resilience, smile analysis, and proximity detection.
        """
        now = time.time()
        dt = max(0.001, now - self.prev_detect_time) if self.prev_detect_time > 0 else 0.05
        self.prev_detect_time = now

        if frame is None:
            frame = self.capture_frame()

        if frame is None or self.face_cascade is None or not HAS_OPENCV:
            return self._handle_lost_frame(now, dt)

        frame_h, frame_w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Contrast-Limited Adaptive Histogram Equalization for back-lighting robustness
        if self.clahe is not None:
            gray_proc = self.clahe.apply(gray)
        else:
            gray_proc = cv2.equalizeHist(gray)

        # 1. Frontal Face Detection (Default cascade: highly robust under all lighting)
        detected_box = None
        confidence = 0.0
        all_detected_faces = []

        if self.face_cascade_default is not None:
            faces = self.face_cascade_default.detectMultiScale(
                gray_proc,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(30, 30)
            )
            if len(faces) > 0:
                all_detected_faces = [tuple(map(int, f)) for f in faces]
                detected_box = max(faces, key=lambda f: f[2] * f[3])
                confidence = 0.95

        # 2. Alt2 Frontal Face Fallback
        if detected_box is None and self.face_cascade_alt2 is not None:
            faces = self.face_cascade_alt2.detectMultiScale(
                gray_proc,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(30, 30)
            )
            if len(faces) > 0:
                all_detected_faces = [tuple(map(int, f)) for f in faces]
                detected_box = max(faces, key=lambda f: f[2] * f[3])
                confidence = 0.90

        # 3. Profile Face Fallback (User looking sideways / turning head)
        if detected_box is None and self.profile_cascade is not None:
            profiles = self.profile_cascade.detectMultiScale(
                gray_proc,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(30, 30)
            )
            if len(profiles) > 0:
                detected_box = max(profiles, key=lambda f: f[2] * f[3])
                confidence = 0.80
            else:
                # Check flipped profile (looking the other direction)
                flipped_gray = cv2.flip(gray_proc, 1)
                flipped_profiles = self.profile_cascade.detectMultiScale(
                    flipped_gray,
                    scaleFactor=1.1,
                    minNeighbors=3,
                    minSize=(30, 30)
                )
                if len(flipped_profiles) > 0:
                    fb = max(flipped_profiles, key=lambda f: f[2] * f[3])
                    detected_box = (frame_w - fb[0] - fb[2], fb[1], fb[2], fb[3])
                    confidence = 0.80

        if detected_box is not None:
            # Face found this frame!
            x, y, w, h = detected_box
            self.frames_lost = 0

            # Raw normalized center: -1.0 (Left/Up) to +1.0 (Right/Down)
            raw_cx = x + w / 2.0
            raw_cy = y + h / 2.0
            raw_ox = (raw_cx - (frame_w / 2.0)) / (frame_w / 2.0)
            raw_oy = (raw_cy - (frame_h / 2.0)) / (frame_h / 2.0)

            # Apply Exponential Moving Average (EMA) to eliminate jitter
            if self.last_valid_result is None or self.frames_lost > self.persistence_threshold:
                self.smooth_offset_x = raw_ox
                self.smooth_offset_y = raw_oy
                self.smooth_w = float(w)
                self.smooth_h = float(h)
                vel_x = 0.0
                vel_y = 0.0
            else:
                vel_x = (raw_ox - self.smooth_offset_x) / dt
                vel_y = (raw_oy - self.smooth_offset_y) / dt
                self.smooth_offset_x = (1.0 - self.ema_alpha) * self.smooth_offset_x + self.ema_alpha * raw_ox
                self.smooth_offset_y = (1.0 - self.ema_alpha) * self.smooth_offset_y + self.ema_alpha * raw_oy
                self.smooth_w = (1.0 - self.ema_alpha) * self.smooth_w + self.ema_alpha * float(w)
                self.smooth_h = (1.0 - self.ema_alpha) * self.smooth_h + self.ema_alpha * float(h)

            # Clamping offsets
            smooth_ox = max(-1.0, min(1.0, self.smooth_offset_x))
            smooth_oy = max(-1.0, min(1.0, self.smooth_offset_y))

            # Calculate proximity / face ratio
            face_area = self.smooth_w * self.smooth_h
            frame_area = frame_w * frame_h
            face_ratio = float(face_area / max(1.0, frame_area))

            if face_ratio > 0.28:
                dist_cat = "close"
            elif face_ratio < 0.04:
                dist_cat = "far"
            else:
                dist_cat = "optimal"

            # Check for smile in lower half of face
            is_smiling = False
            if self.smile_cascade is not None and h > 60 and w > 60:
                try:
                    mouth_roi = gray_proc[y + int(h * 0.55):y + h, x + int(w * 0.15):x + int(w * 0.85)]
                    if mouth_roi.size > 0:
                        smiles = self.smile_cascade.detectMultiScale(
                            mouth_roi,
                            scaleFactor=1.2,
                            minNeighbors=8,
                            minSize=(20, 12)
                        )
                        is_smiling = len(smiles) > 0
                except Exception:
                    is_smiling = False

            if not all_detected_faces and detected_box is not None:
                all_detected_faces = [(int(x), int(y), int(w), int(h))]

            result = FaceTrackingResult(
                found=True,
                offset_x=round(float(smooth_ox), 3),
                offset_y=round(float(smooth_oy), 3),
                bbox=(int(x), int(y), int(w), int(h)),
                face_ratio=round(face_ratio, 3),
                distance_category=dist_cat,
                is_smiling=is_smiling,
                confidence=round(confidence, 2),
                velocity_x=round(float(vel_x), 2),
                velocity_y=round(float(vel_y), 2),
                num_faces=len(all_detected_faces),
                all_faces=all_detected_faces,
                identified_name=None
            )
            self.last_valid_result = result
            return result

        # No direct detection this frame
        return self._handle_lost_frame(now, dt)

    def _handle_lost_frame(self, now: float, dt: float) -> FaceTrackingResult:
        """Applies persistence hysteresis so single dropped frames do not interrupt gaze."""
        self.frames_lost += 1
        if self.last_valid_result and self.frames_lost <= self.persistence_threshold:
            # Retain tracking with slightly reduced confidence
            decayed = FaceTrackingResult(
                found=True,
                offset_x=self.last_valid_result.offset_x,
                offset_y=self.last_valid_result.offset_y,
                bbox=self.last_valid_result.bbox,
                face_ratio=self.last_valid_result.face_ratio,
                distance_category=self.last_valid_result.distance_category,
                is_smiling=False,
                confidence=max(0.2, self.last_valid_result.confidence * 0.7),
                velocity_x=0.0,
                velocity_y=0.0,
                num_faces=self.last_valid_result.num_faces,
                all_faces=self.last_valid_result.all_faces,
                identified_name=self.last_valid_result.identified_name
            )
            return decayed

        # Fully lost
        self.last_valid_result = None
        return FaceTrackingResult(found=False, num_faces=0, all_faces=[])

    def detect_face(self, frame: Optional[np.ndarray] = None) -> Tuple[bool, float, float]:
        """
        Detects primary face in frame with temporal smoothing.
        Maintains full backward compatibility with existing callers.
        Returns:
            (face_found: bool, offset_x: float, offset_y: float)
            Where offset_x and offset_y range from -1.0 (Left/Up) to +1.0 (Right/Down).
        """
        res = self.track_face_detailed(frame)
        return res.found, res.offset_x, res.offset_y

    def detect_dock_aruco(self, frame: Optional[np.ndarray] = None) -> Tuple[bool, float, float]:
        """
        Detects the charging dock's ArUco marker #0.
        Returns:
            (marker_found: bool, offset_x: float, approx_distance_m: float)
        """
        if frame is None:
            frame = self.capture_frame()

        if frame is None or not HAS_OPENCV:
            return False, 0.0, 0.0

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Use ArUco 4x4 dictionary
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            detector_params = cv2.aruco.DetectorParameters()
            detector = cv2.aruco.ArucoDetector(aruco_dict, detector_params)
            corners, ids, _ = detector.detectMarkers(gray)

            if ids is not None and ARUCO_DOCK_ID in ids:
                idx = list(ids.flatten()).index(ARUCO_DOCK_ID)
                c = corners[idx][0]
                marker_cx = np.mean(c[:, 0])
                marker_w = np.linalg.norm(c[0] - c[1])

                frame_w = frame.shape[1]
                offset_x = (marker_cx - (frame_w / 2.0)) / (frame_w / 2.0)
                # Approximate distance based on 50mm marker width
                focal_length = 500.0
                approx_dist = (0.05 * focal_length) / max(1.0, marker_w)

                return True, float(offset_x), float(approx_dist)
        except Exception:
            pass

        return False, 0.0, 0.0

    def detect_scene_change(self, frame: Optional[np.ndarray] = None, threshold: float = 30.0) -> bool:
        """Determines if the environment in front has changed or if entering a new area."""
        if frame is None:
            frame = self.capture_frame()

        if frame is None or not HAS_OPENCV:
            return False

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_gray_frame is None:
            self.prev_gray_frame = gray
            return False

        delta = cv2.absdiff(self.prev_gray_frame, gray)
        mean_delta = float(np.mean(delta))
        self.prev_gray_frame = gray

        return mean_delta > threshold

    def draw_hud(
        self,
        frame: np.ndarray,
        result: FaceTrackingResult,
        state: Optional[Any] = None,
        emotion: Optional[Any] = None
    ) -> np.ndarray:
        """
        Overlays a futuristic Wall-E cyber HUD with corner brackets,
        crosshair reticle, smile status, distance, and emotion tags onto the frame.
        """
        if frame is None or not HAS_OPENCV:
            return frame

        canvas = frame.copy()
        h, w = canvas.shape[:2]

        state_str = state.value.upper() if hasattr(state, "value") else str(state).upper() if state else "SCANNING"
        emo_str = emotion.value.upper() if hasattr(emotion, "value") else str(emotion).upper() if emotion else "IDLE"

        # Theme color based on emotion
        if emo_str in ("LOVE", "BONDING"):
            hud_color = (94, 63, 244)     # Rose / Pink (BGR)
        elif emo_str in ("EXCITED", "SMILING"):
            hud_color = (74, 222, 128)    # Energetic Green (BGR)
        elif emo_str in ("SURPRISED", "ALERT"):
            hud_color = (36, 191, 251)    # Warning Amber (BGR)
        elif emo_str in ("CONFUSED", "SEARCHING"):
            hud_color = (252, 132, 192)   # Purple / Lavender (BGR)
        else:
            hud_color = (248, 189, 56)    # Wall-E Cyan (BGR)

        # Draw Top HUD Banner
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (w, 34), (10, 14, 20), -1)
        cv2.addWeighted(overlay, 0.75, canvas, 0.25, 0, canvas)
        cv2.line(canvas, (0, 34), (w, 34), hud_color, 1)

        people_str = f" | PEOPLE: {result.num_faces}" if result.found and result.num_faces > 0 else ""
        banner_text = f"ALPHA EYE | STATE: [{state_str}] | EMO: [{emo_str}]{people_str}"
        cv2.putText(canvas, banner_text, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, hud_color, 1, cv2.LINE_AA)

        pan_deg = int(result.offset_x * 45) if result.found else 0
        tilt_deg = int(-result.offset_y * 25) if result.found else 0
        servo_text = f"PAN:{pan_deg:+03d}\xb0 TILT:{tilt_deg:+03d}\xb0"
        cv2.putText(canvas, servo_text, (w - 150, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 200, 220), 1, cv2.LINE_AA)

        if result.found:
            bx, by, bw, bh = result.bbox
            cx = bx + bw // 2
            cy = by + bh // 2

            # Corner brackets around face
            clen = max(10, min(24, int(bw * 0.22)))
            # Top-Left
            cv2.line(canvas, (bx, by), (bx + clen, by), hud_color, 2)
            cv2.line(canvas, (bx, by), (bx, by + clen), hud_color, 2)
            # Top-Right
            cv2.line(canvas, (bx + bw, by), (bx + bw - clen, by), hud_color, 2)
            cv2.line(canvas, (bx + bw, by), (bx + bw, by + clen), hud_color, 2)
            # Bottom-Left
            cv2.line(canvas, (bx, by + bh), (bx + clen, by + bh), hud_color, 2)
            cv2.line(canvas, (bx, by + bh), (bx, by + bh - clen), hud_color, 2)
            # Bottom-Right
            cv2.line(canvas, (bx + bw, by + bh), (bx + bw - clen, by + bh), hud_color, 2)
            cv2.line(canvas, (bx + bw, by + bh), (bx + bw, by + bh - clen), hud_color, 2)

            # Center target crosshair
            cv2.line(canvas, (cx - 8, cy), (cx + 8, cy), hud_color, 1)
            cv2.line(canvas, (cx, cy - 8), (cx, cy + 8), hud_color, 1)

            # Render secondary faces if multiple people are in frame
            if result.all_faces and len(result.all_faces) > 1:
                sec_color = (251, 191, 36) # Amber secondary indicator
                sec_num = 2
                for sbox in result.all_faces:
                    sx, sy, sw, sh = sbox
                    if (sx, sy, sw, sh) == (bx, by, bw, bh):
                        continue
                    cv2.rectangle(canvas, (sx, sy), (sx + sw, sy + sh), sec_color, 1)
                    cv2.putText(canvas, f"PERSON {sec_num}", (sx, max(46, sy - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, sec_color, 1, cv2.LINE_AA)
                    sec_num += 1

            # Primary face label (Dynamic person identification)
            dist_cm = int(3500 / max(30, bw))
            conf_pct = int(result.confidence * 100)
            if result.identified_name:
                user_label = f"{result.identified_name.upper()} ({conf_pct}%)"
            elif result.num_faces > 1:
                user_label = f"PERSON 1 (PRIMARY) ({conf_pct}%)"
            else:
                user_label = f"PERSON ({conf_pct}%)"
            cv2.putText(canvas, user_label, (bx, max(46, by - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, hud_color, 1, cv2.LINE_AA)

            dist_label = f"~{dist_cm}cm [{result.distance_category.upper()}]"
            cv2.putText(canvas, dist_label, (bx, by + bh + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (210, 220, 235), 1, cv2.LINE_AA)

            if result.is_smiling:
                cv2.putText(canvas, "[*] SMILE DETECTED!", (bx, by + bh + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (74, 222, 128), 1, cv2.LINE_AA)
        else:
            # Idle scanning crosshair in frame center
            mid_x, mid_y = w // 2, h // 2
            cv2.line(canvas, (mid_x - 12, mid_y), (mid_x + 12, mid_y), (100, 120, 140), 1)
            cv2.line(canvas, (mid_x, mid_y - 12), (mid_x, mid_y + 12), (100, 120, 140), 1)
            cv2.putText(canvas, "SEARCHING USER...", (mid_x - 60, mid_y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 120, 140), 1, cv2.LINE_AA)

        return canvas

    @staticmethod
    def decode_base64_frame(b64_str: str) -> Optional[np.ndarray]:
        """Decodes base64 JPEG/PNG string from browser canvas into OpenCV BGR frame."""
        if not HAS_OPENCV or not b64_str:
            return None
        try:
            import base64
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_str)
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"[VisionPipeline] Error decoding base64 frame: {e}")
            return None

    def release(self) -> None:
        """Releases camera hardware."""
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
