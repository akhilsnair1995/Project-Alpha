"""
Project Alpha: Navigation Cortex, Spatial World Model & Cognitive Presence Engine.
Powered by the Neural Mind Engine (Minimum-Jerk Biomimetic Kinematics,
Affective Space, Salience-based Attention, and Continuous Stream of Consciousness).
Operates 100% in Python on the backend for Raspberry Pi and Digital Twin parity.
"""

import math
import time
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from core.neural_engine import (
    NeuralMindEngine,
    AffectiveState,
    AttentionSystem,
    StreamOfConsciousness,
    BiomimeticKinematics
)

class BehaviorState(Enum):
    COMPANION_IDLE = "COMPANION_IDLE"       # Natural desktop companion state (resting, breathing, subtle glances)
    STATIONARY_WATCH = "STATIONARY_WATCH"   # Locked on target object (keys, cup, etc.) with smooth biological gaze tracking
    HOLD_POSITION = "HOLD_POSITION"         # Commanded freeze / brake
    NAVIGATE_TO = "NAVIGATE_TO"             # Organic purposeful minimum-jerk navigation toward a desk coordinate
    DOCKING = "DOCKING"                     # Autonomous solar dock homing
    MANUAL = "MANUAL"                       # Direct manual operator control
    EXPLORE_ROAM = "EXPLORE_ROAM"           # Autonomous active roaming & exploration

class NavigationCortex:
    """
    Unified Navigation & World Model Cortex.
    Powered by NeuralMindEngine for biological, human-like mind dynamics and motion.
    """

    def __init__(self, motion_controller=None, eye_controller=None, db=None):
        self.motion = motion_controller
        self.eyes = eye_controller
        self.db = db
        self.engine = NeuralMindEngine(
            db=self.db,
            motion_controller=self.motion,
            eye_controller=self.eyes
        )

    # -------------------------------------------------------------------------
    # Property Bindings to Biological Neural Engine
    # -------------------------------------------------------------------------

    @property
    def x(self) -> float:
        return self.engine.body.x

    @x.setter
    def x(self, val: float):
        self.engine.body.x = float(val)

    @property
    def y(self) -> float:
        return self.engine.body.y

    @y.setter
    def y(self, val: float):
        self.engine.body.y = float(val)

    @property
    def heading(self) -> float:
        return self.engine.body.heading

    @heading.setter
    def heading(self, val: float):
        self.engine.body.heading = float(val)

    @property
    def speed(self) -> float:
        return self.engine.body.speed

    @speed.setter
    def speed(self, val: float):
        self.engine.body.speed = float(val)

    @property
    def turn_speed(self) -> float:
        return self.engine.body.turn_speed

    @turn_speed.setter
    def turn_speed(self, val: float):
        self.engine.body.turn_speed = float(val)

    @property
    def pan_angle(self) -> float:
        return self.engine.body.pan

    @pan_angle.setter
    def pan_angle(self, val: float):
        self.engine.body.pan = float(val)

    @property
    def tilt_angle(self) -> float:
        return self.engine.body.tilt

    @tilt_angle.setter
    def tilt_angle(self, val: float):
        self.engine.body.tilt = float(val)

    @property
    def gaze_x(self) -> float:
        return self.engine.body.gaze_x + self.engine.body.saccade_offset_x

    @property
    def gaze_y(self) -> float:
        return self.engine.body.gaze_y + self.engine.body.saccade_offset_y

    @property
    def current_thought(self) -> str:
        return self.engine.consciousness.current_thought

    @current_thought.setter
    def current_thought(self, val: str):
        self.engine.consciousness.current_thought = str(val)

    @property
    def locked_target(self) -> Optional[str]:
        if self.engine.is_command_locked:
            return self.engine.command_target or self.engine.attention.focal_target
        return None

    @locked_target.setter
    def locked_target(self, val: Optional[str]):
        if val:
            clean = val.title()
            self.engine.is_command_locked = True
            self.engine.command_target = clean
            self.engine.attention.lock_focus(clean)
        else:
            self.engine.is_command_locked = False
            self.engine.command_target = None
            self.engine.attention.unlock_focus()

    @property
    def obstacles(self) -> Dict[str, Dict[str, Any]]:
        return self.engine.obstacles

    @property
    def operating_mode(self) -> str:
        return self.engine.operating_mode

    @operating_mode.setter
    def operating_mode(self, val: str):
        self.engine.operating_mode = str(val)

    def set_operating_mode(self, mode: str) -> None:
        """Sets operating mode: EXPLORE_ROAM, DESK_COMPANION, or HOLD_POSITION."""
        self.engine.set_operating_mode(mode)

    @property
    def behavior_state(self) -> BehaviorState:
        if self.engine.is_command_locked:
            if self.engine.command_action == "STAY_AND_WATCH":
                return BehaviorState.STATIONARY_WATCH
            return BehaviorState.HOLD_POSITION
        if self.engine.current_behavior == "MANUAL" and (self.engine.body.speed != 0.0 or self.engine.body.turn_speed != 0.0):
            return BehaviorState.MANUAL
        if self.engine.body.target_coord_goal:
            return BehaviorState.NAVIGATE_TO
        if self.engine.operating_mode == "EXPLORE_ROAM":
            return BehaviorState.EXPLORE_ROAM
        if self.engine.body.speed != 0.0 or self.engine.body.turn_speed != 0.0:
            return BehaviorState.MANUAL
        return BehaviorState.COMPANION_IDLE

    @behavior_state.setter
    def behavior_state(self, val):
        if isinstance(val, BehaviorState):
            state_str = val.value
        else:
            state_str = str(val)

        if state_str in ("HOLD_POSITION", "STATIONARY_WATCH"):
            self.engine.is_command_locked = True
            self.engine.command_action = state_str
            self.engine.body.target_coord_goal = None
            self.engine.body.speed = 0.0
            self.engine.body.turn_speed = 0.0
        else:
            self.engine.is_command_locked = False
            self.engine.command_action = None

    @property
    def cliff_left(self) -> bool:
        return self.engine.cliff_left

    @property
    def cliff_right(self) -> bool:
        return self.engine.cliff_right

    @property
    def tof_distance(self) -> float:
        return self.engine.tof_distance

    @property
    def battery_volts(self) -> float:
        return self.engine.battery_volts

    # -------------------------------------------------------------------------
    # Directives & External Commands
    # -------------------------------------------------------------------------

    def execute_directive(self, action: str, target: Optional[str] = None) -> None:
        """Applies a behavioral directive parsed from conversation or thought."""
        self.engine.receive_command_directive(action, target)

    def update_obstacle_position(self, title: str, x: float, y: float) -> None:
        """Called when an obstacle is repositioned (e.g. user drags keys on desk)."""
        self.engine.update_obstacle(title, x, y)

    def update_environment_physics(self, items: List[Dict[str, Any]]) -> None:
        """Updates the physical items on the desk simulator."""
        self.engine.update_environment_physics(items)

    def attach_cognitive_loop(self, loop) -> None:
        """Attaches the Gemini cognitive loop."""
        self.engine.attach_cognitive_loop(loop)

    @property
    def cognitive_loop(self):
        return self.engine.cognitive_loop

    def remove_environment_physics_item(self, title: str) -> None:
        """Removes an item from the physical desk environment."""
        self.engine.remove_environment_physics_item(title)

    @property
    def discovered_objects(self) -> Dict[str, Dict[str, Any]]:
        """Items organically discovered and remembered by Alpha's cognitive brain."""
        return self.engine.discovered_objects

    def set_manual_motion(self, action: str) -> None:
        """Handles operator manual keyboard/drive input."""
        self.engine.set_manual_motion(action)

    def _orient_toward_target(self, target_name: str) -> None:
        """Internal helper to smoothly align pan/tilt toward target."""
        self.engine._orient_mind_toward_target(target_name)

    def step(self, dt: float = 0.05) -> Dict[str, Any]:
        """Runs one biological cognitive step (20Hz loop)."""
        return self.engine.step(dt)

    def get_telemetry(self) -> Dict[str, Any]:
        """Provides full real-time telemetry snapshot."""
        return self.engine.get_telemetry()
