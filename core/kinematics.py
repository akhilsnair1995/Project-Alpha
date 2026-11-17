"""
Project Alpha: Biomimetic Kinematics, Flash-Hogan Trajectories & Gaze Precedence.
Implements biological, organic neuromuscular motion control:
1. Flash & Hogan (1985) Minimum-Jerk 5th-Order Polynomial Trajectories.
2. Coordinated Gaze Precedence (Pupil Saccade -> Neck Pan/Tilt -> Chassis Tracks -> VOR Settling).
3. Servo Anti-Wobble Deadband Stabilizer (Eliminates MG90S hunting & jitter).
4. Two-Phase Differential Drive Navigation (Zero-forward pivot + straight cruising + direct object facing).
"""

import math
import time
from typing import Optional, Tuple, Callable, Dict, Any

class MinimumJerkTrajectory:
    """
    Flash & Hogan (1985) Minimum-Jerk biological trajectory model.
    Minimizes the third time-derivative of position (integral of square jerk),
    producing the characteristic bell-shaped velocity profiles of living organisms.
    """

    def __init__(self, start_val: float, target_val: float, duration: float):
        self.start = float(start_val)
        self.target = float(target_val)
        self.duration = max(0.05, float(duration))
        self.elapsed = 0.0
        self.is_finished = (start_val == target_val)

    def update(self, dt: float) -> Tuple[float, float, float]:
        """
        Advances the trajectory by dt.
        Returns: (position, velocity, acceleration)
        """
        if self.is_finished:
            return self.target, 0.0, 0.0

        self.elapsed += dt
        tau = min(1.0, self.elapsed / self.duration)

        # 5th-order minimum-jerk polynomial: s(tau) = 10*tau^3 - 15*tau^4 + 6*tau^5
        tau3 = tau * tau * tau
        tau4 = tau3 * tau
        tau5 = tau4 * tau

        s = 10.0 * tau3 - 15.0 * tau4 + 6.0 * tau5
        ds = (30.0 * tau * tau - 60.0 * tau3 + 30.0 * tau4) / self.duration
        dds = (60.0 * tau - 180.0 * tau * tau + 120.0 * tau3) / (self.duration * self.duration)

        delta = self.target - self.start
        pos = self.start + delta * s
        vel = delta * ds
        acc = delta * dds

        if tau >= 1.0:
            self.is_finished = True
            pos = self.target
            vel = 0.0
            acc = 0.0

        return pos, vel, acc

class BiomimeticKinematicsCore:
    """
    Unified biological motor controller.
    Eliminates robotic snaps and linear speed jumps through minimum-jerk curves,
    coordinated gaze sequencing, and stabilized differential drive.
    """

    def __init__(self):
        # 2D Tabletop Arena Coordinates
        self.x: float = 320.0
        self.y: float = 250.0
        self.heading: float = 0.0      # Degrees (0 = North / Up, 90 = East / Right)
        self.speed: float = 0.0        # Linear speed (pixels/step)
        self.turn_speed: float = 0.0   # Angular speed (deg/step)

        # Neck Pan & Tilt Servos
        self.pan: float = 0.0          # Current pan angle (-85° to +85°)
        self.tilt: float = 0.0         # Current tilt angle (-30° to +40°)
        self.target_pan_goal: float = 0.0
        self.target_tilt_goal: float = 0.0

        # Expressive Virtual Pupil Gaze
        self.gaze_x: float = 0.0       # -1.0 to +1.0
        self.gaze_y: float = 0.0       # -1.0 to +1.0

        # Minimum-Jerk Active Trajectories
        self.pan_traj: Optional[MinimumJerkTrajectory] = None
        self.tilt_traj: Optional[MinimumJerkTrajectory] = None
        self.heading_traj: Optional[MinimumJerkTrajectory] = None

        # Two-Phase Navigation Goals
        self.target_coord_goal: Optional[Tuple[float, float]] = None
        self.facing_target_pos: Optional[Tuple[float, float]] = None
        self.facing_target_name: Optional[str] = None
        self.on_arrival_callback: Optional[Callable[[str], None]] = None

        # Operational Boundaries
        self.desk_min_x: float = 45.0
        self.desk_min_y: float = 45.0
        self.desk_max_x: float = 655.0
        self.desk_max_y: float = 475.0

    def plan_smooth_head_look(self, target_pan: float, target_tilt: float, duration: float = 0.5) -> None:
        """
        Plans biological eye-head gaze shift.
        Employs deadband filtering to prevent servo chatter and wobbling.
        """
        clamped_pan = max(-85.0, min(85.0, target_pan))
        clamped_tilt = max(-30.0, min(40.0, target_tilt))

        # Anti-Wobble Deadband Check
        pan_change = abs(clamped_pan - self.target_pan_goal)
        tilt_change = abs(clamped_tilt - self.target_tilt_goal)

        if self.pan_traj and not self.pan_traj.is_finished and pan_change < 1.5:
            # Trajectory active towards virtually the same angle; do NOT reset velocity to 0
            return

        if self.pan_traj is None and abs(clamped_pan - self.pan) < 0.8 and abs(clamped_tilt - self.tilt) < 0.8:
            # Already settled within 0.8 degree deadband
            return

        self.target_pan_goal = clamped_pan
        self.target_tilt_goal = clamped_tilt

        # Coordinated Gaze-Ahead: Eyes flick ahead first to acquire target
        self.gaze_x = max(-1.0, min(1.0, (clamped_pan - self.pan) / 35.0))
        self.gaze_y = max(-1.0, min(1.0, (clamped_tilt - self.tilt) / 25.0))

        # Dynamic duration scaled to angular travel distance
        ang_dist = math.hypot(clamped_pan - self.pan, clamped_tilt - self.tilt)
        eff_dur = max(0.25, min(0.65, (ang_dist / 60.0) * duration))

        self.pan_traj = MinimumJerkTrajectory(self.pan, clamped_pan, eff_dur)
        self.tilt_traj = MinimumJerkTrajectory(self.tilt, clamped_tilt, eff_dur * 0.9)

    def plan_smooth_turn(self, target_heading: float, duration: float = 0.7) -> None:
        """Smooth biological chassis turn with bell-shaped angular acceleration."""
        diff = (target_heading - self.heading + 540.0) % 360.0 - 180.0
        dest = self.heading + diff
        self.heading_traj = MinimumJerkTrajectory(self.heading, dest, duration)

    def plan_transit(self, dest_x: float, dest_y: float, face_pos: Optional[Tuple[float, float]] = None, face_name: Optional[str] = None) -> None:
        """Initiates two-phase navigation: transit to (dest_x, dest_y) then face face_pos."""
        self.target_coord_goal = (
            max(self.desk_min_x + 35, min(self.desk_max_x - 35, dest_x)),
            max(self.desk_min_y + 35, min(self.desk_max_y - 35, dest_y))
        )
        self.facing_target_pos = face_pos
        self.facing_target_name = face_name

    def step(self, dt: float, breathing_tilt: float = 0.0, saccade_x: float = 0.0, saccade_y: float = 0.0) -> None:
        """Advances biological kinematics by dt."""

        # 1. Step Neck Pan Trajectory
        if self.pan_traj and not self.pan_traj.is_finished:
            pos, vel, _ = self.pan_traj.update(dt)
            self.pan = pos
            self.gaze_x *= 0.92  # Vestibulo-ocular reflex settling
        else:
            self.pan_traj = None
            self.gaze_x *= 0.95

        # 2. Step Neck Tilt Trajectory + Add Living Breath
        if self.tilt_traj and not self.tilt_traj.is_finished:
            pos, vel, _ = self.tilt_traj.update(dt)
            self.tilt = pos + breathing_tilt
            self.gaze_y *= 0.92
        else:
            self.tilt_traj = None
            self.tilt = self.target_tilt_goal + breathing_tilt
            self.gaze_y *= 0.95

        # 3. Step Chassis Heading Trajectory (if active)
        if self.heading_traj and not self.heading_traj.is_finished:
            pos, vel, _ = self.heading_traj.update(dt)
            self.heading = pos % 360.0
            self.turn_speed = vel
        else:
            self.heading_traj = None

        # 4. Step Two-Phase Differential Drive Navigation
        if self.target_coord_goal:
            tx, ty = self.target_coord_goal
            cx = self.x + 30.0
            cy = self.y + 35.0
            dx = tx - cx
            dy = ty - cy
            dist = math.hypot(dx, dy)

            # Within arrival threshold (14px from waypoint)
            if dist < 14.0:
                self.speed = 0.0

                # Phase 2: Pivot to face target squarely
                if self.facing_target_pos:
                    ox, oy = self.facing_target_pos
                    bearing_to_obj = (math.atan2(ox - cx, -(oy - cy)) * 180.0 / math.pi + 360.0) % 360.0
                    face_diff = (bearing_to_obj - self.heading + 540.0) % 360.0 - 180.0

                    if abs(face_diff) > 3.0:
                        self.speed = 0.0
                        self.turn_speed = max(-4.0, min(4.0, face_diff * 0.45))
                    else:
                        # Squared up directly facing object!
                        self.speed = 0.0
                        self.turn_speed = 0.0
                        self.target_coord_goal = None
                        self.facing_target_pos = None
                        self.plan_smooth_head_look(target_pan=0.0, target_tilt=-14.0, duration=0.4)
                        if self.on_arrival_callback and self.facing_target_name:
                            self.on_arrival_callback(self.facing_target_name)
                else:
                    self.speed = 0.0
                    self.turn_speed = 0.0
                    self.target_coord_goal = None
            else:
                # Phase 1: Transit to waypoint
                desired_heading = (math.atan2(dx, -dy) * 180.0 / math.pi + 360.0) % 360.0
                h_diff = (desired_heading - self.heading + 540.0) % 360.0 - 180.0

                if abs(h_diff) > 20.0:
                    # Heading misaligned: pivot in place! Zero forward speed prevents orbital loops
                    self.speed = 0.0
                    self.turn_speed = max(-4.5, min(4.5, h_diff * 0.4))
                else:
                    # Heading aligned: drive straight toward waypoint with gentle proportional steering
                    max_speed = min(4.5, max(1.2, dist / 15.0))
                    self.speed += (max_speed - self.speed) * 0.25
                    self.turn_speed = max(-2.5, min(2.5, h_diff * 0.2))

        # 5. Kinematic Integration
        if not self.heading_traj and self.turn_speed != 0.0:
            self.heading = (self.heading + self.turn_speed) % 360.0

        if self.speed != 0.0:
            rad = math.radians(self.heading)
            self.x += math.sin(rad) * self.speed
            self.y -= math.cos(rad) * self.speed

        # Desk boundary clamping
        self.x = max(self.desk_min_x, min(self.desk_max_x, self.x))
        self.y = max(self.desk_min_y, min(self.desk_max_y, self.y))
