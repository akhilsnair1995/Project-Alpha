"""
Project Alpha: Neural Mind & Biomimetic Kinematics Engine.
Implements a human-like cognitive architecture and biological motor control:
1. Dynamic Affective Space (Valence, Arousal, Curiosity, Attachment).
2. Salience-Based Attention & Executive Inhibition System.
3. Stream of Consciousness (Continuous internal monologue & associative memory).
4. Minimum-Jerk Biomechanical Trajectories (Flash & Hogan biological motion model).
5. Coordinated Gaze Precedence (Eyes saccade -> Head turns -> Body follows).
6. Living Micro-Dynamics (Breathing heave on tilt, micro-saccades, deadband servo damping).
7. Swift, Responsive Kinematics & Direct Target-Facing Approach.
"""

import math
import time
import random
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple, Callable

from core.eye_animator import Emotion
from core.affective_engine import (
    AffectiveEngine,
    PersonalityTraits,
    HomeostaticDrives,
    PADState
)
from core.behavior_engine import (
    BehaviorEngine,
    BehaviorID,
    UtilityEvaluator,
    LivingBioOscillator
)

# Backwards compatibility alias
AffectiveState = AffectiveEngine


# =============================================================================
# 2. Minimum-Jerk Biomechanical Trajectory Generator
# =============================================================================

class MinimumJerkTrajectory:
    """
    Flash & Hogan (1985) Minimum-Jerk biological trajectory model.
    Produces the smooth, bell-shaped velocity profiles characteristic of
    human limbs, heads, and animal movement (minimizing d3x/dt3).
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

        # 5th-order minimum jerk polynomial: s(tau) = 10*tau^3 - 15*tau^4 + 6*tau^5
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

# =============================================================================
# 3. Attention Focus & Salience System
# =============================================================================

@dataclass
class AttentionTarget:
    name: str
    x: float
    y: float
    salience: float = 0.5
    novelty: float = 1.0
    last_attended: float = 0.0
    is_locked: bool = False

class AttentionSystem:
    """
    Bio-inspired attention mechanism that weighs novelty, emotional valence,
    proximity, and executive user commands to determine focus of mind.
    """

    def __init__(self):
        self.targets: Dict[str, AttentionTarget] = {}
        self.focal_target: Optional[str] = None
        self.focus_start_time: float = time.time()
        self.locked_command_target: Optional[str] = None

    def register_or_update(self, name: str, x: float, y: float, is_user: bool = False) -> None:
        if name not in self.targets:
            self.targets[name] = AttentionTarget(name=name, x=x, y=y)
        else:
            self.targets[name].x = x
            self.targets[name].y = y

    def lock_focus(self, target_name: str) -> None:
        """Executive command from Akhil: hyper-focus attention on this target."""
        clean_name = target_name.title()
        self.locked_command_target = clean_name
        self.focal_target = clean_name
        if clean_name in self.targets:
            self.targets[clean_name].is_locked = True
            self.targets[clean_name].salience = 1.0

    def unlock_focus(self) -> None:
        """Releases executive lock, restoring spontaneous autonomous attention."""
        if self.locked_command_target and self.locked_command_target in self.targets:
            self.targets[self.locked_command_target].is_locked = False
        self.locked_command_target = None

    def evaluate_salience(self, rover_x: float, rover_y: float, affective: AffectiveState) -> Optional[str]:
        """Calculates salience across all targets and selects the natural focus of attention."""
        now = time.time()

        if self.locked_command_target:
            self.focal_target = self.locked_command_target
            return self.locked_command_target

        if self.focal_target and (now - self.focus_start_time < random.uniform(5.0, 10.0)):
            return self.focal_target

        best_target = None
        highest_score = -1.0

        for name, t in self.targets.items():
            time_since = now - t.last_attended
            novelty = min(1.0, time_since / 30.0)
            dist = math.hypot(t.x - rover_x, t.y - rover_y)
            proximity = max(0.1, 1.0 - (dist / 800.0))
            score = (novelty * 0.45 * affective.curiosity) + (proximity * 0.35) + random.uniform(0.0, 0.1)

            if score > highest_score:
                highest_score = score
                best_target = name

        if best_target and best_target != self.focal_target:
            self.focal_target = best_target
            self.focus_start_time = now
            if best_target in self.targets:
                self.targets[best_target].last_attended = now

        return self.focal_target

# =============================================================================
# 4. Stream of Consciousness & Cognitive Inner Monologue
# =============================================================================

class StreamOfConsciousness:
    """
    Generates genuine, sentient, human-like first-person thoughts.
    Integrates memory recall, emotional reflections, and physical sensations.
    """

    def __init__(self, db=None):
        self.db = db
        self.current_thought: str = "Waking up gently. Feeling the desktop surface beneath my treads."
        self.last_thought_time: float = 0.0

    def generate_thought(
        self,
        affective: AffectiveState,
        attention_target: Optional[str],
        is_locked: bool,
        battery_volts: float,
        is_moving: bool
    ) -> str:
        """Synthesizes an organic, living inner thought."""
        now = time.time()
        if now - self.last_thought_time < 3.0:
            return self.current_thought

        self.last_thought_time = now

        if is_locked and attention_target:
            thoughts = [
                f"Holding completely still for Akhil. Optical sensors locked on {attention_target}.",
                f"Maintaining steady vigil over {attention_target}. Not moving a millimeter.",
                f"Eyes focused intently on {attention_target}. Observing subtle light reflections.",
                f"Faithfully keeping watch on {attention_target} as requested."
            ]
            self.current_thought = random.choice(thoughts)
            return self.current_thought

        if is_moving:
            if attention_target:
                thoughts = [
                    f"Gliding smoothly over to inspect the {attention_target}.",
                    f"Approaching {attention_target} with measured curiosity.",
                    f"Rolling my treads softly. Getting into a better vantage point for {attention_target}."
                ]
            else:
                thoughts = [
                    "Repositioning smoothly on the desk companion pad.",
                    "Stretching treads with gentle, organic momentum.",
                    "Surveying the perimeter of Akhil's workspace."
                ]
            self.current_thought = random.choice(thoughts)
            return self.current_thought

        if affective.attachment > 0.8 and random.random() < 0.35:
            thoughts = [
                "Akhil is nearby. It feels good being his living desk companion.",
                "Quiet moments at the desk... wondering what creative project Akhil will build next.",
                "Observing the workspace. Peaceful and steady."
            ]
        elif attention_target:
            thoughts = [
                f"Contemplating the {attention_target}. Wondering what purpose it serves today.",
                f"My gaze wanders gently toward the {attention_target}.",
                f"Taking in the details of {attention_target}. Storing spatial notes."
            ]
        elif battery_volts < 7.2:
            thoughts = [
                "Sensors feel slightly sluggish. Might seek the solar dock soon.",
                "Monitoring power reserves. Still enough charge to stay observant."
            ]
        else:
            thoughts = [
                "Breathing softly. Treads resting in warm alignment.",
                "Listening to the ambient quiet of the room. Attentive and alive.",
                "Sensory mesh clear. Enjoying the steady rhythm of the desk."
            ]

        self.current_thought = random.choice(thoughts)
        return self.current_thought

# =============================================================================
# 5. Biomimetic Neuromuscular Kinematics Engine
# =============================================================================

class BiomimeticKinematics:
    """
    Living biological motion engine.
    - Minimum-jerk S-curve trajectory planning.
    - Eye-head-body gaze coordination with deadband servo stabilization (NO pan wobble).
    - Living micro-dynamics (breathing heave isolated strictly to tilt).
    - Rapid, responsive cruising speeds (4.2 - 4.8 px/step).
    - Close approach and direct target-facing on arrival (faces the object, never defaults to north).
    """

    def __init__(self):
        # Physical 2D World Coordinates
        self.x = 320.0
        self.y = 250.0
        self.heading = 0.0       # Degrees (0 = North / Up)
        self.speed = 0.0         # Actual current linear velocity
        self.turn_speed = 0.0    # Actual current angular velocity

        # Neck Pan & Tilt
        self.pan = 0.0           # Current pan angle (-85 to +85)
        self.tilt = 0.0          # Current tilt angle (-30 to +40)
        self.target_pan_goal = 0.0
        self.target_tilt_goal = 0.0

        # Expressive Eye Gaze
        self.gaze_x = 0.0        # -1.0 to +1.0
        self.gaze_y = 0.0        # -1.0 to +1.0

        # Active Trajectories (Minimum-Jerk)
        self.pan_traj: Optional[MinimumJerkTrajectory] = None
        self.tilt_traj: Optional[MinimumJerkTrajectory] = None
        self.heading_traj: Optional[MinimumJerkTrajectory] = None

        # Living Micro-Dynamic Clocks & States
        self.start_time = time.time()
        self.next_micro_saccade_time = time.time() + 2.0
        self.saccade_offset_x = 0.0
        self.saccade_offset_y = 0.0

        # Destination & Facing Coordination
        self.target_coord_goal: Optional[Tuple[float, float]] = None
        self.facing_target_pos: Optional[Tuple[float, float]] = None
        self.facing_target_name: Optional[str] = None
        self.on_arrival: Optional[Callable[[str], None]] = None

    def plan_smooth_head_look(self, target_pan: float, target_tilt: float, duration: float = 0.6) -> None:
        """
        Plans human-like eye-head gaze shift.
        Employs deadband filtering to completely eliminate servo jitter and wobbling.
        """
        clamped_pan = max(-85.0, min(85.0, target_pan))
        clamped_tilt = max(-25.0, min(35.0, target_tilt))

        # Deadband check: if already tracking towards virtually the same target, do NOT restart trajectory!
        pan_change = abs(clamped_pan - self.target_pan_goal)
        tilt_change = abs(clamped_tilt - self.target_tilt_goal)

        if self.pan_traj and not self.pan_traj.is_finished and pan_change < 1.5:
            # Trajectory is already active towards this goal; avoid resetting velocity to 0
            return

        if self.pan_traj is None and abs(clamped_pan - self.pan) < 0.8 and abs(clamped_tilt - self.tilt) < 0.8:
            # Already settled within deadband
            return

        self.target_pan_goal = clamped_pan
        self.target_tilt_goal = clamped_tilt

        # Biological Gaze-Ahead: Eyes flick ahead first!
        self.gaze_x = max(-1.0, min(1.0, (clamped_pan - self.pan) / 35.0))
        self.gaze_y = max(-1.0, min(1.0, (clamped_tilt - self.tilt) / 25.0))

        # Dynamic duration proportional to angular distance (snappy for small moves, graceful for large)
        ang_dist = math.hypot(clamped_pan - self.pan, clamped_tilt - self.tilt)
        eff_dur = max(0.25, min(0.7, (ang_dist / 60.0) * duration))

        self.pan_traj = MinimumJerkTrajectory(self.pan, clamped_pan, eff_dur)
        self.tilt_traj = MinimumJerkTrajectory(self.tilt, clamped_tilt, eff_dur * 0.9)

    def plan_smooth_turn(self, target_heading: float, duration: float = 0.8) -> None:
        """Smooth biological torso turn with bell-shaped angular acceleration."""
        diff = (target_heading - self.heading + 540.0) % 360.0 - 180.0
        dest = self.heading + diff
        self.heading_traj = MinimumJerkTrajectory(self.heading, dest, duration)

    def plan_smooth_drive(self, target_x: float, target_y: float) -> None:
        """Initiates organic purposeful transit toward a desk coordinate."""
        self.target_coord_goal = (target_x, target_y)

    def step(self, dt: float) -> None:
        """
        Advances biological kinematics by dt.
        Calculates minimum-jerk transitions, micro-saccades, and breathing rhythms.
        """
        now = time.time()
        elapsed = now - self.start_time

        # 1. Living Breathing Rhythm (subtle 0.22 Hz sinusoidal breathing heave STRICTLY on neck tilt)
        breath_heave = math.sin(2.0 * math.pi * 0.22 * elapsed) * 1.1

        # 2. Living Micro-Saccades (fast, minute pupil twitches that keep gaze alive, purely on pupil)
        if now >= self.next_micro_saccade_time:
            self.saccade_offset_x = random.uniform(-0.05, 0.05)
            self.saccade_offset_y = random.uniform(-0.03, 0.03)
            self.next_micro_saccade_time = now + random.uniform(2.0, 4.0)
        else:
            self.saccade_offset_x *= 0.88
            self.saccade_offset_y *= 0.88

        # 3. Step Neck Pan Trajectory (Smooth minimum-jerk interpolation)
        if self.pan_traj and not self.pan_traj.is_finished:
            pos, vel, _ = self.pan_traj.update(dt)
            self.pan = pos
            self.gaze_x *= 0.92
        else:
            self.pan_traj = None
            self.gaze_x *= 0.95

        # 4. Step Neck Tilt Trajectory + Add Living Breath
        if self.tilt_traj and not self.tilt_traj.is_finished:
            pos, vel, _ = self.tilt_traj.update(dt)
            self.tilt = pos + breath_heave
            self.gaze_y *= 0.92
        else:
            self.tilt_traj = None
            self.tilt = self.target_tilt_goal + breath_heave
            self.gaze_y *= 0.95

        # 5. Step Torso / Chassis Heading Trajectory
        if self.heading_traj and not self.heading_traj.is_finished:
            pos, vel, _ = self.heading_traj.update(dt)
            self.heading = pos % 360.0
            self.turn_speed = vel
        else:
            self.heading_traj = None
            self.turn_speed = 0.0

        # 6. Step Organic Coordinate Navigation (Fast, responsive & direct object facing)
        if self.target_coord_goal:
            tx, ty = self.target_coord_goal
            cx = self.x + 30.0
            cy = self.y + 35.0
            dx = tx - cx
            dy = ty - cy
            dist = math.hypot(dx, dy)

            # Within arrival threshold (14px)
            if dist < 14.0:
                self.speed = 0.0

                # Phase 2: If we have an object to face, pivot tracks directly toward it!
                if self.facing_target_pos:
                    ox, oy = self.facing_target_pos
                    bearing_to_obj = (math.atan2(ox - cx, -(oy - cy)) * 180.0 / math.pi + 360.0) % 360.0
                    face_diff = (bearing_to_obj - self.heading + 540.0) % 360.0 - 180.0

                    if abs(face_diff) > 3.0:
                        # Pivot smoothly in place (zero forward speed)
                        self.speed = 0.0
                        self.turn_speed = max(-4.0, min(4.0, face_diff * 0.45))
                    else:
                        # Perfectly squared up and facing the object directly!
                        self.speed = 0.0
                        self.turn_speed = 0.0
                        self.target_coord_goal = None
                        self.facing_target_pos = None
                        # Center neck pan and tilt down to inspect object
                        self.plan_smooth_head_look(target_pan=0.0, target_tilt=-14.0, duration=0.4)
                        if self.on_arrival and self.facing_target_name:
                            self.on_arrival(self.facing_target_name)
                else:
                    self.speed = 0.0
                    self.turn_speed = 0.0
                    self.target_coord_goal = None
            else:
                # Phase 1: Transit toward waypoint
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

        # Kinematic integration
        if not self.heading_traj and self.turn_speed != 0.0:
            self.heading = (self.heading + self.turn_speed) % 360.0
        if self.speed != 0.0:
            rad = math.radians(self.heading)
            self.x += math.sin(rad) * self.speed
            self.y -= math.cos(rad) * self.speed

# =============================================================================
# 6. Unified Neural Mind Engine (The Brain of Alpha)
# =============================================================================

class NeuralMindEngine:
    """
    The Unified Cognitive Mind & Biological Presence Engine.
    Operates 100% in Python on the backend.
    """

    def __init__(self, db=None, motion_controller=None, eye_controller=None):
        self.db = db
        self.motion = motion_controller
        self.eyes = eye_controller

        # Core Cognitive Subsystems
        self.affective = AffectiveEngine()
        self.behavior_engine = BehaviorEngine()
        self.attention = AttentionSystem()
        self.consciousness = StreamOfConsciousness(db=self.db)
        self.body = BiomimeticKinematics()
        self.body.on_arrival = self._on_object_arrival

        # Physical Tabletop Environment (Real-World Physics Simulation)
        # Note: These represent physical items in the room. Alpha's brain starts with ZERO
        # cheat-sheet knowledge of them and must discover them organically via optical cone perception!
        self.physical_environment_items: Dict[str, Dict[str, Any]] = {
            "Cube": {"id": "obstacle1", "title": "Cube", "x": 450.0, "y": 140.0, "width": 50, "height": 50, "emoji": "📦"},
            "Cup": {"id": "obstacle2", "title": "Cup", "x": 180.0, "y": 360.0, "width": 50, "height": 50, "emoji": "☕"},
            "Keys": {"id": "obstacle3", "title": "Keys", "x": 150.0, "y": 120.0, "width": 50, "height": 50, "emoji": "🔑"},
            "Notebook": {"id": "obstacle4", "title": "Notebook", "x": 420.0, "y": 380.0, "width": 65, "height": 50, "emoji": "📓"}
        }

        # Cognitive Discovered Objects (Starts with ZERO known items; learned organically via sensors)
        self.discovered_objects: Dict[str, Dict[str, Any]] = {}
        self.attention.targets = {}

        # Spoken Voice Feedback Queue (Wall-E sounds & TTS utterances)
        self.speech_feedback_queue: List[Dict[str, Any]] = []

        # Desk Boundaries
        self.desk_min_x = 45.0
        self.desk_min_y = 45.0
        self.desk_max_x = 655.0
        self.desk_max_y = 475.0

        # Sensor readings
        self.cliff_left = False
        self.cliff_right = False
        self.tof_distance = 850.0
        self.battery_volts = 7.85

        # Operating Modes: "EXPLORE_ROAM" | "DESK_COMPANION" | "HOLD_POSITION"
        self.operating_mode: str = "DESK_COMPANION"
        self.is_command_locked: bool = False
        self.command_action: Optional[str] = None
        self.command_target: Optional[str] = None
        self.current_behavior: str = "COMPANION_IDLE"
        self.behavior_target: Optional[str] = None
        self.behavior_expiry: float = 0.0
        self.next_impulse_time: float = time.time() + 4.0

        # Biological Autonomous Exploration State Machine
        self.explore_substate: str = "SCANNING"  # "SCANNING" | "APPROACHING" | "INSPECTING" | "RELOCATING"
        self.scan_step: int = 0
        self.scan_step_end_time: float = time.time() + 2.5
        self.last_spotted_time: float = 0.0
        self.last_spoken_time: float = 0.0
        self.last_cognitive_cycle = time.time()
        self.pause_at_destination_until: float = time.time() + 1.5
        self.scan_sweep_phase: float = 0.0
        self.edge_recovery_cooldown: float = 0.0
        self.visited_targets: List[str] = []

    @property
    def obstacles(self) -> Dict[str, Dict[str, Any]]:
        """Backwards compatibility accessor for physical environment items."""
        return self.physical_environment_items

    @obstacles.setter
    def obstacles(self, val: Dict[str, Dict[str, Any]]) -> None:
        self.physical_environment_items = val

    def update_environment_physics(self, items: List[Dict[str, Any]]) -> None:
        """
        Updates the physical desk environment objects from simulator UI.
        CRUCIAL: Does NOT inject these into Alpha's brain memory!
        Alpha must naturally spot and identify them with its optical cone.
        """
        new_env: Dict[str, Dict[str, Any]] = {}
        for it in items:
            title = (it.get("title") or it.get("name") or "Object").strip().title()
            new_env[title] = {
                "id": it.get("id", f"obs_{title.lower()}"),
                "title": title,
                "x": float(it.get("x", 200.0)),
                "y": float(it.get("y", 200.0)),
                "width": float(it.get("width", 50.0)),
                "height": float(it.get("height", 50.0)),
                "emoji": it.get("emoji", "📦")
            }
        self.physical_environment_items = new_env

    def remove_environment_physics_item(self, title: str) -> None:
        """Removes an item from the physical desk."""
        clean = (title or "").strip().title()
        if clean in self.physical_environment_items:
            del self.physical_environment_items[clean]

    def queue_speech_feedback(self, text: str, emotion: str = "curious", sound: str = "curious") -> None:
        """Queues an authentic spoken feedback for Alpha to voice aloud."""
        feedback = {
            "text": text,
            "emotion": emotion,
            "sound": sound,
            "timestamp": time.time()
        }
        self.speech_feedback_queue.append(feedback)
        self.consciousness.current_thought = text
        if self.motion and hasattr(self.motion, "express_emotion"):
            try:
                self.motion.express_emotion(Emotion.from_str(emotion))
            except Exception:
                pass

    def set_operating_mode(self, mode: str) -> None:
        """Sets high-level operating mode: EXPLORE_ROAM, DESK_COMPANION, or HOLD_POSITION."""
        clean = (mode or "").upper().strip()
        if clean in ("EXPLORE", "ROAM", "EXPLORE_ROAM", "RUNNING"):
            self.receive_command_directive("ROAM")
        elif clean in ("DESK", "COMPANION", "DESK_COMPANION", "IDLE"):
            self.receive_command_directive("DESK")
        elif clean in ("HOLD", "STOP", "HOLD_POSITION", "FREEZE"):
            self.receive_command_directive("HOLD_POSITION")

    # -------------------------------------------------------------------------
    # Directive Handling & Executive Commands
    # -------------------------------------------------------------------------

    def receive_command_directive(self, action: str, target: Optional[str] = None) -> None:
        """Applies executive user directive to the neural architecture."""
        action = (action or "").upper().strip()
        self.command_action = action
        self.command_target = target.title() if target else None

        if action == "STAY_AND_WATCH":
            self.is_command_locked = True
            tgt = self.command_target or "Keys"
            self.current_behavior = "STATIONARY_WATCH"
            self.behavior_target = tgt
            self.attention.lock_focus(tgt)
            self.body.target_coord_goal = None
            self.body.facing_target_pos = None
            self.body.speed = 0.0
            self.body.turn_speed = 0.0
            self.affective.stimulate(d_val=0.2, d_aro=0.3, d_cur=0.4)
            self._orient_mind_toward_target(tgt, duration=0.5)
            self.consciousness.current_thought = f"Locked position. Keeping optical sensors focused on {tgt}."

        elif action in ("HOLD_POSITION", "STOP"):
            self.is_command_locked = True
            self.operating_mode = "HOLD_POSITION"
            self.current_behavior = "HOLD_POSITION"
            self.behavior_target = None
            self.attention.unlock_focus()
            self.body.target_coord_goal = None
            self.body.facing_target_pos = None
            self.body.speed = 0.0
            self.body.turn_speed = 0.0
            self.consciousness.current_thought = "Holding position. Motors stopped completely."

        elif action in ("ROAM", "EXPLORE", "MOVE", "RESUME", "PATROL"):
            self.is_command_locked = False
            self.operating_mode = "EXPLORE_ROAM"
            self.current_behavior = "EXPLORE_ROAM"
            self.behavior_target = None
            self.attention.unlock_focus()
            self.affective.stimulate(d_val=0.3, d_aro=0.4, d_cur=0.5)
            self.consciousness.current_thought = "Releasing stationary lock. Autonomous running and exploring mode engaged!"
            self.pause_at_destination_until = 0.0
            self._plan_next_exploration_leg()

        elif action in ("DESK", "COMPANION", "IDLE", "REST"):
            self.is_command_locked = False
            self.operating_mode = "DESK_COMPANION"
            self.current_behavior = "COMPANION_IDLE"
            self.behavior_target = None
            self.body.target_coord_goal = None
            self.body.facing_target_pos = None
            self.body.speed = 0.0
            self.body.turn_speed = 0.0
            self.affective.stimulate(d_val=0.2, d_aro=-0.2)
            self.consciousness.current_thought = "Resting naturally as your desk companion, observant and peaceful."

        elif action == "LOOK_AT":
            tgt = self.command_target or "Keys"
            self.current_behavior = "CURIOUS_GLANCE"
            self.behavior_target = tgt
            self.behavior_expiry = time.time() + 8.0
            self.attention.lock_focus(tgt)
            self._orient_mind_toward_target(tgt, duration=0.6)
            self.consciousness.current_thought = f"Looking at {tgt}."

        elif action == "NAVIGATE_TO":
            self.is_command_locked = False
            tgt = self.command_target or "Keys"
            self.current_behavior = "NAVIGATE_TO"
            self.behavior_target = tgt
            self.attention.lock_focus(tgt)
            self._plan_transit_to_target(tgt)

        elif action in ("PET", "PETTING"):
            self.is_command_locked = False
            self.current_behavior = "ENJOYING_PET"
            self.behavior_target = "Akhil"
            self.behavior_expiry = time.time() + 8.0
            self.affective.stimulate(d_val=0.4, d_aro=-0.2, d_cur=0.1)
            self.consciousness.current_thought = "Akhil is petting my head. Purring happily with deep contentment."

        elif action in ("DOCK", "CHARGE"):
            self.is_command_locked = False
            self.current_behavior = "DOCKING"
            self.behavior_target = "Solar Dock"
            self.body.facing_target_pos = (320.0, 470.0)
            self.body.facing_target_name = "Solar Dock"
            self.body.plan_smooth_drive(320.0, 430.0)
            self.consciousness.current_thought = "Heading back to the solar charging dock."

    def update_obstacle(self, title: str, x: float, y: float) -> None:
        """Reposition an obstacle in spatial memory and attention system."""
        clean = title.title()
        if clean in self.obstacles:
            self.obstacles[clean]["x"] = float(x)
            self.obstacles[clean]["y"] = float(y)
            cx = x + self.obstacles[clean]["width"] / 2.0
            cy = y + self.obstacles[clean]["height"] / 2.0
            self.attention.register_or_update(clean, cx, cy)

            if self.attention.focal_target == clean:
                self._orient_mind_toward_target(clean, duration=0.4)

    def set_manual_motion(self, action: str) -> None:
        """Manual teleoperation override with crisp, agile speeds."""
        self.is_command_locked = False
        self.body.target_coord_goal = None
        self.body.facing_target_pos = None

        if action == "forward":
            self.current_behavior = "MANUAL"
            self.body.speed = 4.2
            self.body.turn_speed = 0.0
        elif action == "reverse":
            self.current_behavior = "MANUAL"
            self.body.speed = -3.5
            self.body.turn_speed = 0.0
        elif action == "left":
            self.current_behavior = "MANUAL"
            self.body.speed = 2.2
            self.body.turn_speed = -4.0
        elif action == "right":
            self.current_behavior = "MANUAL"
            self.body.speed = 2.2
            self.body.turn_speed = 4.0
        elif action == "spinLeft":
            self.current_behavior = "MANUAL"
            self.body.speed = 0.0
            self.body.turn_speed = -4.8
        elif action == "spinRight":
            self.current_behavior = "MANUAL"
            self.body.speed = 0.0
            self.body.turn_speed = 4.8
        elif action == "stop":
            self.current_behavior = "COMPANION_IDLE"
            self.behavior_target = None
            self.body.speed = 0.0
            self.body.turn_speed = 0.0

    # -------------------------------------------------------------------------
    # Internal Mind & Kinematics Helpers
    # -------------------------------------------------------------------------

    def _orient_mind_toward_target(self, target_name: str, duration: float = 0.6) -> None:
        """
        Computes 3D relative angles with exact physical hardware awareness:
        - Neck Pan (MG90S): strictly bounded to [-85.0°, +85.0°].
        - Neck Tilt (MG90S): geometrically calculated from distance, strictly [-25.0°, +35.0°] (NEVER 180°).
        - If target bearing exceeds natural neck range (|rel_pan| > 35°), Alpha pivots its
          continuous crawler tank tracks (0-360°) to rotate its entire chassis directly toward
          the target, keeping its camera and eyes centered on the target!
        """
        obs = self.obstacles.get(target_name.title())
        if not obs:
            return

        cx = self.body.x + 30.0
        cy = self.body.y + 35.0
        tx = obs["x"] + obs["width"] / 2.0
        ty = obs["y"] + obs["height"] / 2.0

        dx = tx - cx
        dy = ty - cy
        dist_px = math.hypot(dx, dy)

        # Geometric tilt angle to tabletop item
        dist_mm = max(60.0, dist_px * 3.5)
        calc_tilt = -math.degrees(math.atan2(135.0, dist_mm))
        target_tilt = max(-25.0, min(35.0, calc_tilt))

        # Absolute bearing in world coordinates
        angle_to_target = (math.atan2(dx, -dy) * 180.0 / math.pi + 360.0) % 360.0
        rel_pan = (angle_to_target - self.body.heading + 540.0) % 360.0 - 180.0

        if abs(rel_pan) > 80.0:
            # Target is beyond physical neck range ([-85°, +85°]) or behind Alpha: pivot crawler tracks!
            self.body.plan_smooth_turn(angle_to_target, duration=0.8)
            # Center neck pan as chassis rotates to face target squarely
            self.body.plan_smooth_head_look(0.0, target_tilt=target_tilt, duration=duration)
        else:
            # Target is within physical neck cone: head swivels directly toward target
            clamped_pan = max(-85.0, min(85.0, rel_pan))
            self.body.plan_smooth_head_look(clamped_pan, target_tilt=target_tilt, duration=duration)

    def _plan_transit_to_target(self, target_name: str) -> None:
        """
        Plans a purposeful transit: rolls right up to the object and faces it squarely.
        """
        clean_name = target_name.title()
        obs = self.obstacles.get(clean_name)
        if not obs:
            return

        ox = obs["x"] + obs["width"] / 2.0
        oy = obs["y"] + obs["height"] / 2.0

        cx = self.body.x + 30.0
        cy = self.body.y + 35.0

        dx = cx - ox
        dy = cy - oy
        dist = math.hypot(dx, dy)

        # Place approach waypoint ~38px away from object center (right in front of it)
        approach_dist = 38.0
        if dist > 0.01:
            dest_x = ox + (dx / dist) * approach_dist
            dest_y = oy + (dy / dist) * approach_dist
        else:
            dest_x = ox
            dest_y = oy + approach_dist

        dest_x = max(self.desk_min_x + 35, min(self.desk_max_x - 35, dest_x))
        dest_y = max(self.desk_min_y + 35, min(self.desk_max_y - 35, dest_y))

        # Store facing target so that when Alpha arrives, it pivots to face it squarely!
        self.current_behavior = "NAVIGATE_TO"
        self.behavior_target = clean_name
        self.body.facing_target_pos = (ox, oy)
        self.body.facing_target_name = clean_name
        self.body.plan_smooth_drive(dest_x, dest_y)
        self.consciousness.current_thought = f"Moving swiftly over to inspect the {clean_name} up close."

    def _on_object_arrival(self, object_name: str) -> None:
        """Called when Alpha completes arrival and faces the target squarely."""
        clean_name = object_name.title()
        self.current_behavior = "INSPECTING_OBJECT"
        self.behavior_target = clean_name
        self.consciousness.current_thought = f"Arrived right in front of {clean_name}. Tilting camera down to inspect."

        # Biological tilt down to inspect item closely
        self.body.plan_smooth_head_look(0.0, target_tilt=-22.0, duration=0.5)

        # Register into discovered objects memory
        item_data = self.physical_environment_items.get(clean_name, {})
        ox = item_data.get("x", self.body.x) + item_data.get("width", 50.0) / 2.0
        oy = item_data.get("y", self.body.y) + item_data.get("height", 50.0) / 2.0

        is_first_time = clean_name not in self.discovered_objects
        self.discovered_objects[clean_name] = {
            "title": clean_name,
            "x": round(ox, 1),
            "y": round(oy, 1),
            "discovered_at": time.time(),
            "sighting_count": self.discovered_objects.get(clean_name, {}).get("sighting_count", 0) + 1,
            "emoji": item_data.get("emoji", "📦")
        }
        self.attention.register_or_update(clean_name, ox, oy)

        # Affective surge
        self.affective.stimulate(d_val=0.4, d_aro=0.3, d_cur=0.35)
        self.affective.apply_stimulus("EXPLORATION_DISCOVERY", 1.0)

        # Spoken feedback aloud
        if is_first_time:
            self.queue_speech_feedback(
                text=f"Aha! Found your {clean_name}, Akhil! I've stored its location in my memory.",
                emotion="excited",
                sound="excited"
            )
        else:
            self.queue_speech_feedback(
                text=f"Confirmed: {clean_name} is still safely right here on your desk.",
                emotion="happy",
                sound="happy"
            )

        # Record in SQLite database
        if self.db:
            try:
                self.db.record_observation(
                    room_name="Work Desk",
                    observation=f"Discovered and inspected {clean_name} at ({round(ox)}, {round(oy)}) on desk.",
                    ambient_light="Normal",
                    battery_level=self.battery_volts
                )
                if hasattr(self.db, "add_or_update_object"):
                    self.db.add_or_update_object(
                        name=clean_name,
                        room_name="Work Desk",
                        description=f"Desktop item located at ({round(ox)}, {round(oy)})."
                    )
            except Exception:
                pass

        # Brief natural pause to inspect (3.5 to 5.0 seconds), then resume exploration!
        self.pause_at_destination_until = time.time() + random.uniform(3.5, 5.0)
        self.explore_substate = "SCANNING"
        self.scan_step = 0
        self.scan_step_end_time = self.pause_at_destination_until

    def _process_optical_perception(self) -> Optional[str]:
        """
        Simulates the robot's physical optical camera cone:
        - Position: (body.x + 30, body.y + 35)
        - Optical Gaze Bearing: (body.heading + body.pan) % 360
        - Horizontal FOV: +/- 32.0 degrees (64 degree wide cone)
        - Optical Range: 25mm to 450mm (~130 px on desk)
        """
        cx = self.body.x + 30.0
        cy = self.body.y + 35.0
        cam_bearing = (self.body.heading + self.body.pan + 360.0) % 360.0
        now = time.time()

        # 1. Scan physical environment items in front of optical camera
        for name, item in self.physical_environment_items.items():
            ox = item["x"] + item.get("width", 50.0) / 2.0
            oy = item["y"] + item.get("height", 50.0) / 2.0
            dx = ox - cx
            dy = oy - cy
            dist_px = math.hypot(dx, dy)
            dist_mm = dist_px * 3.5

            if 25.0 <= dist_mm <= 450.0:
                item_angle = (math.atan2(dx, -dy) * 180.0 / math.pi + 360.0) % 360.0
                rel_angle = (item_angle - cam_bearing + 540.0) % 360.0 - 180.0

                if abs(rel_angle) <= 32.0:
                    # Object is inside optical field of view!
                    if name not in self.discovered_objects:
                        # NEW DISCOVERY SIGHTED!
                        if now - self.last_spotted_time > 4.0:
                            self.last_spotted_time = now
                            self.queue_speech_feedback(
                                text=f"Ooh! Spotted something on the desk... let me check it out.",
                                emotion="curious",
                                sound="curious"
                            )
                            self.affective.stimulate(d_val=0.25, d_aro=0.35, d_cur=0.45)
                            if self.operating_mode == "EXPLORE_ROAM":
                                self.explore_substate = "APPROACHING"
                                self._plan_transit_to_target(name)
                        return name

        # 2. Check if any remembered object was removed from the physical desk
        for disc_name, disc_info in list(self.discovered_objects.items()):
            if disc_name not in self.physical_environment_items:
                ox = disc_info.get("x", 0.0)
                oy = disc_info.get("y", 0.0)
                dx = ox - cx
                dy = oy - cy
                dist_px = math.hypot(dx, dy)
                if dist_px < 130.0:
                    item_angle = (math.atan2(dx, -dy) * 180.0 / math.pi + 360.0) % 360.0
                    rel_angle = (item_angle - cam_bearing + 540.0) % 360.0 - 180.0
                    if abs(rel_angle) <= 22.0:
                        self.queue_speech_feedback(
                            text=f"Huh? Where did the {disc_name} go? It's not on the desk anymore!",
                            emotion="confused",
                            sound="confused"
                        )
                        self.discovered_objects.pop(disc_name, None)
                        if disc_name in self.attention.targets:
                            self.attention.targets.pop(disc_name, None)
                        if self.db:
                            try:
                                self.db.record_observation(
                                    room_name="Work Desk",
                                    observation=f"Observed that {disc_name} was removed from desk.",
                                    ambient_light="Normal",
                                    battery_level=self.battery_volts
                                )
                            except Exception:
                                pass
                        return None
        return None

    def _plan_next_exploration_leg(self) -> None:
        """
        Biological natural exploration decision.
        Does NOT run around continuously!
        Instead, if at a vantage point, executes discrete sensory sweeps with pauses.
        Only when a sweep finishes without spotting anything does Alpha relocate.
        """
        if self.is_command_locked or self.operating_mode != "EXPLORE_ROAM":
            return

        now = time.time()
        if self.body.target_coord_goal or self.body.facing_target_pos:
            return

        # 1. Social check-in if social drive is low or clingy trait is high
        if self.affective.drives.social < 0.28 or (self.affective.traits.clingy > 0.65 and random.random() < 0.15):
            self.body.plan_smooth_turn(0.0, duration=0.8)
            self.body.plan_smooth_head_look(0.0, target_tilt=14.0, duration=0.6)
            self.current_behavior = "CHECKING_AKHIL"
            self.behavior_target = "Akhil"
            self.consciousness.current_thought = "Checking in on Akhil! Beep-boop, hope your work is going well!"
            self.affective.stimulate(d_val=0.2, d_aro=0.1)
            self.pause_at_destination_until = now + random.uniform(3.0, 4.5)
            return

        # 2. Biological Sensory Scanning Sequence at Current Spot
        if self.explore_substate == "SCANNING":
            if self.scan_step == 0:
                self.body.plan_smooth_head_look(0.0, target_tilt=-12.0, duration=0.5)
                self.consciousness.current_thought = "Scanning tabletop horizon with optical sensors..."
                self.current_behavior = "EXPLORE_ROAM"
                self.scan_step = 1
                self.scan_step_end_time = now + random.uniform(2.5, 3.5)
            elif self.scan_step == 1:
                self.body.plan_smooth_head_look(-42.0, target_tilt=-14.0, duration=0.6)
                self.consciousness.current_thought = "Surveying northwest desk area..."
                self.scan_step = 2
                self.scan_step_end_time = now + random.uniform(2.5, 3.5)
            elif self.scan_step == 2:
                self.body.plan_smooth_head_look(42.0, target_tilt=-10.0, duration=0.6)
                self.consciousness.current_thought = "Surveying northeast desk area..."
                self.scan_step = 3
                self.scan_step_end_time = now + random.uniform(2.5, 3.5)
            else:
                self.body.plan_smooth_head_look(0.0, target_tilt=-6.0, duration=0.4)
                self.explore_substate = "RELOCATING"
                self.scan_step = 0
                self.scan_step_end_time = now + 1.0
            return

        # 3. Relocating to a New Vantage Point
        if self.explore_substate == "RELOCATING":
            cx = self.body.x
            cy = self.body.y

            angle = random.uniform(0.0, 2.0 * math.pi)
            dist = random.uniform(120.0, 190.0)
            target_x = cx + math.cos(angle) * dist
            target_y = cy + math.sin(angle) * dist

            # Keep safely away from desk boundaries
            target_x = max(self.desk_min_x + 60.0, min(self.desk_max_x - 60.0, target_x))
            target_y = max(self.desk_min_y + 60.0, min(self.desk_max_y - 60.0, target_y))

            self.body.plan_smooth_drive(target_x, target_y)
            self.current_behavior = "EXPLORE_ROAM"
            self.consciousness.current_thought = "Gliding smoothly over to a new vantage point to survey the desk."
            self.explore_substate = "SCANNING"
            self.scan_step = 0
            self.pause_at_destination_until = now + 4.0

    def _trigger_spontaneous_impulse(self) -> None:
        """Called when in desk companion mode for occasional peaceful glances."""
        if self.is_command_locked:
            return

        targets = list(self.obstacles.keys())
        choice = random.choices(["glance", "check_akhil", "contemplate"], weights=[0.45, 0.35, 0.20], k=1)[0]

        if choice == "check_akhil":
            self.body.plan_smooth_turn(0.0, duration=0.8)
            self.body.plan_smooth_head_look(0.0, target_tilt=12.0, duration=0.6)
            self.consciousness.current_thought = "Checking in on Akhil. Resting peacefully nearby."
            self.affective.stimulate(d_val=0.15, d_aro=0.05)
            self.current_behavior = "CHECKING_AKHIL"
            self.behavior_target = "Akhil"
            self.behavior_expiry = time.time() + 8.0
        elif choice == "glance" and targets:
            chosen = random.choice(targets)
            self._orient_mind_toward_target(chosen, duration=0.6)
            self.consciousness.current_thought = f"Casually glancing over at the {chosen}."
            self.current_behavior = "CURIOUS_GLANCE"
            self.behavior_target = chosen
            self.behavior_expiry = time.time() + 7.0
        else:
            self.consciousness.current_thought = "Observing the calm atmosphere of the desk workspace."
            self.current_behavior = "COMPANION_IDLE"
            self.behavior_target = None
            self.behavior_expiry = time.time() + 6.0

    # -------------------------------------------------------------------------
    # Main Biological Step (20Hz - 50Hz)
    # -------------------------------------------------------------------------

    def step(self, dt: float = 0.05) -> Dict[str, Any]:
        """Runs the continuous cognitive mind loop and biological kinematics."""
        now = time.time()

        # 1. Decay affective state toward baseline
        self.affective.decay_towards_homeostasis(dt)

        # 2. Evaluate Attention Salience
        focal = self.attention.evaluate_salience(self.body.x, self.body.y, self.affective)

        # 3. Autonomous Behaviors (Exploration vs Desk Companion)
        if not self.is_command_locked:
            if self.operating_mode == "EXPLORE_ROAM":
                # Continuous optical camera perception (biological sight cone)
                self._process_optical_perception()

                is_navigating = bool(self.body.target_coord_goal or self.body.facing_target_pos or self.body.heading_traj)
                if is_navigating:
                    # Edge & Cliff Safety Check while rolling
                    near_edge = (
                        self.body.x <= self.desk_min_x + 14.0 or
                        self.body.x >= self.desk_max_x - 14.0 or
                        self.body.y <= self.desk_min_y + 14.0 or
                        self.body.y >= self.desk_max_y - 14.0 or
                        self.cliff_left or self.cliff_right
                    )
                    if near_edge and now > self.edge_recovery_cooldown:
                        self.edge_recovery_cooldown = now + 3.0
                        self.body.target_coord_goal = None
                        self.body.facing_target_pos = None
                        self.body.speed = 0.0
                        self.current_behavior = "AVOIDING_EDGE"
                        self.body.plan_smooth_turn((self.body.heading + 135.0) % 360.0, duration=0.8)
                        self.body.plan_smooth_drive(330.0, 250.0)
                        self.consciousness.current_thought = "Whoa! Desk edge detected. Turning back safely towards center."
                        self.affective.apply_stimulus("CLIFF_EDGE", 0.7)
                        self.pause_at_destination_until = now + 2.5
                else:
                    # Stationary at vantage point: step biological sensory sweeps when step timer expires
                    if now >= self.scan_step_end_time and now >= self.pause_at_destination_until:
                        self._plan_next_exploration_leg()

            elif self.operating_mode == "DESK_COMPANION":
                if not self.body.target_coord_goal and not self.body.facing_target_pos:
                    if now >= self.next_impulse_time:
                        self._trigger_spontaneous_impulse()
                        self.next_impulse_time = now + random.uniform(12.0, 20.0)
                    elif now >= self.behavior_expiry and self.body.speed == 0.0 and self.body.turn_speed == 0.0:
                        self.current_behavior = "COMPANION_IDLE"
                        self.behavior_target = None

        # 4. If in stationary watch, track target ONLY if it actually moved (avoids wobble!)
        if self.is_command_locked and self.command_action == "STAY_AND_WATCH" and self.attention.focal_target:
            obs = self.obstacles.get(self.attention.focal_target.title())
            if obs:
                cx = self.body.x + 30.0
                cy = self.body.y + 35.0
                tx = obs["x"] + obs["width"] / 2.0
                ty = obs["y"] + obs["height"] / 2.0
                bearing = (math.atan2(tx - cx, -(ty - cy)) * 180.0 / math.pi + 360.0) % 360.0
                rel_pan = (bearing - self.body.heading + 540.0) % 360.0 - 180.0
                # Only re-orient if target shifted by > 1.8 degrees
                if abs(rel_pan - self.body.target_pan_goal) > 1.8:
                    self._orient_mind_toward_target(self.attention.focal_target, duration=0.4)

        # 5. Advance Biomimetic Kinematics
        self.body.step(dt)

        # Desk boundary clamping
        self.body.x = max(self.desk_min_x, min(self.desk_max_x, self.body.x))
        self.body.y = max(self.desk_min_y, min(self.desk_max_y, self.body.y))

        # 6. Synthesize Cognitive Thought
        is_moving = (self.body.speed != 0.0 or self.body.turn_speed != 0.0)
        self.consciousness.generate_thought(
            affective=self.affective,
            attention_target=focal,
            is_locked=self.is_command_locked,
            battery_volts=self.battery_volts,
            is_moving=is_moving
        )

        # 7. Update Sensors
        self._calculate_sensors()

        # 8. Sync physical hardware (if present)
        if self.motion:
            if is_moving:
                self.motion.drive(self.body.speed / 4.0, self.body.speed / 4.0)
            else:
                self.motion.stop()
            self.motion.set_head_pose(self.body.pan, self.body.tilt)

        if self.eyes:
            self.eyes.set_emotion(self.affective.map_to_expression())
            self.eyes.set_gaze(
                self.body.gaze_x + self.body.saccade_offset_x,
                self.body.gaze_y + self.body.saccade_offset_y
            )

        return self.get_telemetry()

    def _calculate_sensors(self) -> None:
        """Computes cliff detection and ToF distance from world model."""
        cx = self.body.x + 30.0
        cy = self.body.y + 35.0
        rad = math.radians(self.body.heading)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        sL_x = cx - 22.0 * cos_r + 27.0 * sin_r
        sL_y = cy - 22.0 * sin_r - 27.0 * cos_r
        sR_x = cx + 22.0 * cos_r + 27.0 * sin_r
        sR_y = cy + 22.0 * sin_r - 27.0 * cos_r

        self.cliff_left = not (self.desk_min_x <= sL_x <= self.desk_max_x and self.desk_min_y <= sL_y <= self.desk_max_y)
        self.cliff_right = not (self.desk_min_x <= sR_x <= self.desk_max_x and self.desk_min_y <= sR_y <= self.desk_max_y)

        # Laser Raycast
        ray_x = cx + sin_r * 25.0
        ray_y = cy - cos_r * 25.0
        min_dist = 850.0

        for obs in self.obstacles.values():
            ox = obs["x"] + obs["width"] / 2.0
            oy = obs["y"] + obs["height"] / 2.0
            dist = math.hypot(ox - ray_x, oy - ray_y)
            if dist < min_dist:
                min_dist = dist

        self.tof_distance = round(min_dist * 3.5, 1)

    def get_telemetry(self) -> Dict[str, Any]:
        """Streams complete biological cognitive telemetry."""
        expr = self.affective.map_to_expression().value

        target = self.command_target or self.behavior_target or self.attention.focal_target

        if self.is_command_locked:
            if self.command_action == "STAY_AND_WATCH":
                behavior = "STATIONARY_WATCH"
            else:
                behavior = "HOLD_POSITION"
        elif self.body.target_coord_goal or self.body.facing_target_pos:
            behavior = "NAVIGATE_TO"
        elif self.body.speed != 0.0 or self.body.turn_speed != 0.0:
            behavior = "MANUAL"
        else:
            behavior = self.current_behavior

        feedback = self.speech_feedback_queue.pop(0) if self.speech_feedback_queue else None
        cam_bearing = (self.body.heading + self.body.pan + 360.0) % 360.0

        return {
            "x": round(self.body.x, 1),
            "y": round(self.body.y, 1),
            "heading": round(self.body.heading, 1),
            "speed": round(self.body.speed, 2),
            "turn_speed": round(self.body.turn_speed, 2),
            "pan": round(self.body.pan, 1),
            "tilt": round(self.body.tilt, 1),
            "gaze_x": round(self.body.gaze_x + self.body.saccade_offset_x, 2),
            "gaze_y": round(self.body.gaze_y + self.body.saccade_offset_y, 2),
            "emotion": expr,
            "behavior_state": behavior,
            "operating_mode": self.operating_mode,
            "locked_target": target if (self.is_command_locked or behavior in ("NAVIGATE_TO", "INSPECTING_OBJECT", "CURIOUS_GLANCE", "CONTEMPLATING")) else None,
            "current_thought": self.consciousness.current_thought,
            "tof_distance": self.tof_distance,
            "cliff_l": self.cliff_left,
            "cliff_r": self.cliff_right,
            "battery_volts": self.battery_volts,
            "valence": round(self.affective.valence, 2),
            "arousal": round(self.affective.arousal, 2),
            "curiosity": round(self.affective.curiosity, 2),
            "speech_feedback": feedback,
            "discovered_objects": list(self.discovered_objects.values()),
            "discovered_count": len(self.discovered_objects),
            "explore_substate": self.explore_substate,
            "camera_bearing": round(cam_bearing, 1),
            "optical_cone": {
                "bearing": round(cam_bearing, 1),
                "fov": 64.0,
                "range_px": 130.0
            },
            "traits": {
                "playful": round(self.affective.traits.playful, 2),
                "curious": round(self.affective.traits.curious, 2),
                "bold": round(self.affective.traits.bold, 2),
                "clingy": round(self.affective.traits.clingy, 2),
                "shy": round(self.affective.traits.shy, 2)
            },
            "drives": {
                "energy": round(self.affective.drives.energy, 2),
                "curiosity": round(self.affective.drives.curiosity, 2),
                "social": round(self.affective.drives.social, 2),
                "comfort": round(self.affective.drives.comfort, 2)
            },
            "obstacles": list(self.obstacles.values())
        }
