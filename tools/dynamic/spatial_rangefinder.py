"""
Dynamic Tool: spatial_rangefinder.py
Self-programmed spatial reasoning tool for Project Alpha.
Calculates distance and relative angle offsets to detected objects on the desk.
"""

import math
from typing import Dict, Any

def run(x_center_ratio: float, box_width_ratio: float, known_width_cm: float = 8.0, focal_length_px: float = 600.0, frame_width: int = 640) -> Dict[str, Any]:
    """
    Estimates real-world distance (cm) and bearing angle (degrees) to a detected object.
    
    Args:
        x_center_ratio: Horizontal center of object in frame (0.0 to 1.0, 0.5 = center).
        box_width_ratio: Width of object bounding box relative to frame width (0.0 to 1.0).
        known_width_cm: Approximate actual width of the object in cm (default: 8.0cm for coffee mug/cup).
        focal_length_px: Calibrated camera focal length in pixels.
        frame_width: Camera image width in pixels.
        
    Returns:
        Dictionary with estimated distance_cm, bearing_deg, and navigation recommendation.
    """
    if box_width_ratio <= 0.001:
        return {"error": "Invalid bounding box width."}

    # Pin-hole camera distance estimation: D = (W_actual * f) / W_pixel
    pixel_width = box_width_ratio * frame_width
    estimated_distance_cm = (known_width_cm * focal_length_px) / pixel_width

    # Angular bearing offset: -X is left, +X is right (FOV ~60 degrees)
    offset_from_center = x_center_ratio - 0.5
    bearing_deg = offset_from_center * 60.0

    recommendation = "optimal_view"
    if estimated_distance_cm > 60:
        recommendation = "advance_forward"
    elif estimated_distance_cm < 18:
        recommendation = "too_close_reverse_or_tilt_up"

    return {
        "distance_cm": round(estimated_distance_cm, 1),
        "bearing_deg": round(bearing_deg, 1),
        "recommendation": recommendation
    }
