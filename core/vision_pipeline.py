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

# Graceful numpy & OpenCV imports for fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    class _MockNP:
        ndarray = Any
    np = _MockNP()
    HAS_NUMPY = False

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from core.config import IS_RASPBERRY_PI, ARUCO_DOCK_ID


COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
    'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
    'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
    'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
    'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear',
    'hair drier', 'toothbrush'
]


class YoloObjectDetector:
    """Lightweight real-time COCO object detector powered by YOLOv5n on OpenCV DNN."""

    def __init__(self, model_path: str = "data/models/yolov5n.onnx"):
        self.model_path = model_path
        self.net = None
        self._init_model()

    def _init_model(self):
        try:
            if not os.path.exists(self.model_path):
                import requests
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                print(f"[YoloObjectDetector] Downloading YOLOv5n ONNX to {self.model_path}...")
                r = requests.get('https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5n.onnx', timeout=30)
                with open(self.model_path, 'wb') as f:
                    f.write(r.content)
            self.net = cv2.dnn.readNetFromONNX(self.model_path)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            print("[YoloObjectDetector] Successfully initialized YOLOv5n on OpenCV DNN.")
        except Exception as e:
            print(f"[YoloObjectDetector] Could not initialize YOLOv5n: {e}")
            self.net = None

    def detect(self, frame: np.ndarray, conf_threshold: float = 0.35, nms_threshold: float = 0.45) -> list:
        if self.net is None or frame is None:
            return []
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.net.setInput(blob)
        preds = self.net.forward()[0]

        obj_confs = preds[:, 4]
        valid_mask = obj_confs > conf_threshold
        valid_preds = preds[valid_mask]
        if len(valid_preds) == 0:
            return []

        class_scores = valid_preds[:, 5:]
        max_class_ids = np.argmax(class_scores, axis=1)
        max_scores = class_scores[np.arange(len(valid_preds)), max_class_ids]
        total_scores = valid_preds[:, 4] * max_scores

        final_mask = total_scores > conf_threshold
        final_preds = valid_preds[final_mask]
        final_classes = max_class_ids[final_mask]
        final_confs = total_scores[final_mask]

        if len(final_preds) == 0:
            return []

        x_scale = w / 640.0
        y_scale = h / 640.0
        boxes = []
        confidences = []
        class_ids = []

        for p, cid, conf in zip(final_preds, final_classes, final_confs):
            cx, cy, bw, bh = p[0:4]
            bx = int((cx - bw / 2.0) * x_scale)
            by = int((cy - bh / 2.0) * y_scale)
            bw = int(bw * x_scale)
            bh = int(bh * y_scale)
            bx = max(0, min(w - 1, bx))
            by = max(0, min(h - 1, by))
            bw = max(1, min(w - bx, bw))
            bh = max(1, min(h - by, bh))
            boxes.append([bx, by, bw, bh])
            confidences.append(float(conf))
            class_ids.append(int(cid))

        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
        results = []
        if len(indices) > 0:
            for idx in indices.flatten():
                cid = class_ids[idx]
                label = COCO_CLASSES[cid] if cid < len(COCO_CLASSES) else f"obj_{cid}"
                results.append({
                    "label": label,
                    "is_person": (label == "person"),
                    "confidence": round(confidences[idx], 2),
                    "bbox": tuple(boxes[idx])
                })
        return results


@dataclass
class FaceTrackingResult:
    """Rich sensory perception result from camera face and object tracking."""
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
    detected_objects: list = None  # List of dicts for all detected everyday objects
    user_emotion: str = "neutral"  # Analyzed human emotion: happy, curious, focused, surprised, sad, love, neutral

    def __post_init__(self):
        if self.all_faces is None:
            self.all_faces = []
        if self.detected_objects is None:
            self.detected_objects = []


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
        self.eye_cascade = None
        self.object_detector = None
        self.db = None
        self._frame_count = 0
        self._cached_objects = []

        if HAS_OPENCV:
            self._init_camera()
            self._init_face_detector()
            try:
                self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            except Exception:
                self.clahe = None
            try:
                self.object_detector = YoloObjectDetector()
            except Exception as e:
                print(f"[VisionPipeline] YOLO detector init warning: {e}")
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

            eye_path = os.path.join(cascade_dir, "haarcascade_eye.xml")
            if os.path.exists(eye_path):
                self.eye_cascade = cv2.CascadeClassifier(eye_path)
            else:
                self.eye_cascade = None

            print(f"[VisionPipeline] Loaded detectors: frontal_default={self.face_cascade_default is not None}, frontal_alt2={self.face_cascade_alt2 is not None}, profile={self.profile_cascade is not None}, smile={self.smile_cascade is not None}, eye={self.eye_cascade is not None}")
        except Exception as e:
            print(f"[VisionPipeline] Could not load face cascades: {e}")

    def _resolve_object_owner(self, label: str) -> Optional[str]:
        """Resolves the assigned owner for an object from SQLite memory."""
        if not hasattr(self, "db") or self.db is None:
            return None
        try:
            objs = self.db.find_objects(label)
            if objs and objs[0].get("owner_name"):
                return objs[0]["owner_name"]
        except Exception:
            pass
        return None

    def capture_frame(self) -> Optional[Any]:
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

    def track_face_detailed(self, frame: Optional[Any] = None) -> FaceTrackingResult:
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

        # Filter faces by human facial aspect ratio (stops mugs, bottles, keyboards being labeled as people)
        def _filter_faces(raw_boxes):
            valid = []
            for f in raw_boxes:
                fx, fy, fw, fh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
                aspect = float(fh) / float(max(1, fw))
                # Human face bounding box aspect ratio is typically between 0.75 and 1.45
                if 0.75 <= aspect <= 1.45 and fw >= 35 and fh >= 35:
                    valid.append((fx, fy, fw, fh))
            return valid

        # 1. Frontal Face Detection (minNeighbors=5 prevents texture false positives)
        detected_box = None
        confidence = 0.0
        all_detected_faces = []

        if self.face_cascade_default is not None:
            raw_faces = self.face_cascade_default.detectMultiScale(
                gray_proc,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(35, 35)
            )
            valid = _filter_faces(raw_faces)
            if len(valid) > 0:
                all_detected_faces = valid
                detected_box = max(valid, key=lambda f: f[2] * f[3])
                confidence = 0.95

        # 2. Alt2 Frontal Face Fallback
        if detected_box is None and self.face_cascade_alt2 is not None:
            raw_faces = self.face_cascade_alt2.detectMultiScale(
                gray_proc,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(35, 35)
            )
            valid = _filter_faces(raw_faces)
            if len(valid) > 0:
                all_detected_faces = valid
                detected_box = max(valid, key=lambda f: f[2] * f[3])
                confidence = 0.90

        # 3. Profile Face Fallback (User looking sideways / turning head)
        if detected_box is None and self.profile_cascade is not None:
            raw_profiles = self.profile_cascade.detectMultiScale(
                gray_proc,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(35, 35)
            )
            valid = _filter_faces(raw_profiles)
            if len(valid) > 0:
                detected_box = max(valid, key=lambda f: f[2] * f[3])
                confidence = 0.80
            else:
                # Check flipped profile (looking the other direction)
                flipped_gray = cv2.flip(gray_proc, 1)
                flipped_profiles = self.profile_cascade.detectMultiScale(
                    flipped_gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(35, 35)
                )
                valid_flipped = _filter_faces(flipped_profiles)
                if len(valid_flipped) > 0:
                    fb = max(valid_flipped, key=lambda f: f[2] * f[3])
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

            # Check for smile in lower half of face (minNeighbors=9 for high precision)
            is_smiling = False
            if self.smile_cascade is not None and h > 55 and w > 55:
                try:
                    mouth_roi = gray_proc[y + int(h * 0.55):y + h, x + int(w * 0.15):x + int(w * 0.85)]
                    if mouth_roi.size > 0:
                        smiles = self.smile_cascade.detectMultiScale(
                            mouth_roi,
                            scaleFactor=1.2,
                            minNeighbors=9,
                            minSize=(22, 14)
                        )
                        is_smiling = len(smiles) > 0
                except Exception:
                    is_smiling = False

            # Multi-Emotion Analysis across human face
            user_emotion = "neutral"
            eye_count = 0
            tilt_angle = 0.0
            if self.eye_cascade is not None and h > 50 and w > 50:
                try:
                    upper_face = gray_proc[y:y + int(h * 0.55), x:x + w]
                    if upper_face.size > 0:
                        eyes = self.eye_cascade.detectMultiScale(upper_face, scaleFactor=1.15, minNeighbors=4, minSize=(16, 16))
                        eye_count = len(eyes)
                        if eye_count >= 2:
                            eyes_sorted = sorted(eyes, key=lambda e: e[0])
                            e1, e2 = eyes_sorted[0], eyes_sorted[1]
                            dy = (e2[1] + e2[3]/2.0) - (e1[1] + e1[3]/2.0)
                            dx = max(1.0, (e2[0] + e2[2]/2.0) - (e1[0] + e1[2]/2.0))
                            tilt_angle = abs(float(np.degrees(np.arctan2(dy, dx))))
                except Exception:
                    pass

            if is_smiling:
                user_emotion = "excited" if (w > 120 and face_ratio > 0.14) else "happy"
            elif dist_cat == "close" or abs(vel_x) > 3.0 or abs(vel_y) > 3.0:
                user_emotion = "surprised"
            elif tilt_angle > 12.0:
                user_emotion = "curious"
            elif eye_count >= 1 and abs(vel_x) < 0.22 and abs(vel_y) < 0.22:
                user_emotion = "focused"
            else:
                user_emotion = "neutral"

            # Run Real-Time Object Detection every 3 frames
            self._frame_count += 1
            if self.object_detector and (self._frame_count % 3 == 0 or not self._cached_objects):
                try:
                    raw_objs = self.object_detector.detect(frame, conf_threshold=0.35)
                    filtered_objs = []
                    for o in raw_objs:
                        # Exclude 'person' class from everyday objects list
                        if o.get("is_person") or o.get("label") == "person":
                            continue
                        label = o.get("label", "object")
                        owner = self._resolve_object_owner(label)
                        o["owner_name"] = owner
                        filtered_objs.append(o)
                    self._cached_objects = filtered_objs
                except Exception:
                    pass

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
                identified_name=None,
                detected_objects=list(self._cached_objects),
                user_emotion=user_emotion
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

    def detect_face(self, frame: Optional[Any] = None) -> Tuple[bool, float, float]:
        """
        Detects primary face in frame with temporal smoothing.
        Maintains full backward compatibility with existing callers.
        Returns:
            (face_found: bool, offset_x: float, offset_y: float)
            Where offset_x and offset_y range from -1.0 (Left/Up) to +1.0 (Right/Down).
        """
        res = self.track_face_detailed(frame)
        return res.found, res.offset_x, res.offset_y

    def detect_dock_aruco(self, frame: Optional[Any] = None) -> Tuple[bool, float, float]:
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

    def detect_scene_change(self, frame: Optional[Any] = None, threshold: float = 30.0) -> bool:
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
        obj_count = len(result.detected_objects) if getattr(result, "detected_objects", None) else 0
        obj_names = ", ".join(o["label"].title() for o in result.detected_objects[:3]) if obj_count > 0 else ""
        obj_str = f" | OBJECTS: {obj_count} ({obj_names})" if obj_count > 0 else ""
        user_emo_str = result.user_emotion.upper() if getattr(result, "user_emotion", None) else emo_str
        banner_text = f"ALPHA EYE | STATE: [{state_str}] | EMO: [{user_emo_str}]{people_str}{obj_str}"
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
            elif result.user_emotion in ("focused", "curious", "surprised", "love"):
                cv2.putText(canvas, f"[*] MOOD: {result.user_emotion.upper()}", (bx, by + bh + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.40, hud_color, 1, cv2.LINE_AA)

        # Draw Detected Everyday Objects (distinct Amber brackets & labels)
        if getattr(result, "detected_objects", None):
            obj_color = (36, 180, 255) # Solar Amber / Wall-E Gold (BGR)
            for obj in result.detected_objects:
                ox, oy, ow, oh = obj["bbox"]
                label_txt = obj["label"].title()
                owner_txt = f" [{obj['owner_name']}]" if obj.get("owner_name") else ""
                full_obj_label = f"[OBJ: {label_txt}]{owner_txt}"

                # Draw bounding box and corner ticks
                cv2.rectangle(canvas, (ox, oy), (ox + ow, oy + oh), obj_color, 1)
                o_clen = max(6, min(14, int(ow * 0.2)))
                cv2.line(canvas, (ox, oy), (ox + o_clen, oy), obj_color, 2)
                cv2.line(canvas, (ox, oy), (ox, oy + o_clen), obj_color, 2)
                cv2.line(canvas, (ox + ow, oy), (ox + ow - o_clen, oy), obj_color, 2)
                cv2.line(canvas, (ox + ow, oy), (ox + ow, oy + o_clen), obj_color, 2)
                cv2.line(canvas, (ox, oy + oh), (ox + o_clen, oy + oh), obj_color, 2)
                cv2.line(canvas, (ox, oy + oh), (ox, oy + oh - o_clen), obj_color, 2)
                cv2.line(canvas, (ox + ow, oy + oh), (ox + ow - o_clen, oy + oh), obj_color, 2)
                cv2.line(canvas, (ox + ow, oy + oh), (ox + ow, oy + oh - o_clen), obj_color, 2)

                cv2.putText(canvas, full_obj_label, (ox, max(46, oy - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.40, obj_color, 1, cv2.LINE_AA)

        if not result.found:
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
