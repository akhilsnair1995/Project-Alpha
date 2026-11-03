"""
Project Alpha: Vision Pipeline & Computer Vision Cortex.
Performs real-time face detection, gaze tracking coordinates, ArUco dock homing,
and camera frame capture with graceful PC webcam fallback.
"""

import time
import os
from typing import Tuple, Optional, Dict, Any
import numpy as np

# Lazy OpenCV import for graceful fallback
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from core.config import IS_RASPBERRY_PI, ARUCO_DOCK_ID

class VisionPipeline:
    """Handles camera capture, face detection, and dock fiducial tracking."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None
        self.face_cascade = None
        self.prev_gray_frame = None

        if HAS_OPENCV:
            self._init_camera()
            self._init_face_detector()
        else:
            print("[VisionPipeline] OpenCV (cv2) not installed. Running in mock vision mode.")

    def _init_camera(self) -> None:
        """Initializes OpenCV video capture."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            if self.cap.isOpened():
                print(f"[VisionPipeline] Camera #{self.camera_index} opened successfully (640x480).")
            else:
                print(f"[VisionPipeline] Camera #{self.camera_index} not accessible.")
        except Exception as e:
            print(f"[VisionPipeline] Camera init error: {e}")

    def _init_face_detector(self) -> None:
        """Loads OpenCV's bundled Haar cascade for real-time face tracking."""
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                print("[VisionPipeline] Loaded Haar cascade face detector.")
        except Exception as e:
            print(f"[VisionPipeline] Could not load face cascade: {e}")

    def capture_frame(self) -> Optional[np.ndarray]:
        """Captures a single BGR frame from the camera."""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None

    def detect_face(self, frame: Optional[np.ndarray] = None) -> Tuple[bool, float, float]:
        """
        Detects the primary face in the frame.
        Returns:
            (face_found: bool, offset_x: float, offset_y: float)
            Where offset_x and offset_y range from -1.0 (Left/Up) to +1.0 (Right/Down).
        """
        if frame is None:
            frame = self.capture_frame()

        if frame is None or self.face_cascade is None:
            return False, 0.0, 0.0

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=5,
            minSize=(60, 60)
        )

        if len(faces) == 0:
            return False, 0.0, 0.0

        # Choose the largest detected face (closest person)
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face

        # Calculate center of face relative to frame dimensions
        frame_h, frame_w = frame.shape[:2]
        face_cx = x + w / 2.0
        face_cy = y + h / 2.0

        # Normalize offset to -1.0 .. +1.0
        offset_x = (face_cx - (frame_w / 2.0)) / (frame_w / 2.0)
        offset_y = (face_cy - (frame_h / 2.0)) / (frame_h / 2.0)

        return True, float(offset_x), float(offset_y)

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

    def release(self) -> None:
        """Releases camera hardware."""
        if self.cap:
            self.cap.release()
