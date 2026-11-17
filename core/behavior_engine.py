"""
Project Alpha: Hybrid Utility AI & Reactive Behavior Engine.
Coordinates goal selection, priority arbitration, and biological micro-dynamics:
1. Priority 0 Reflexive Preemption (Cliff drop, thermal protection, freefall <10ms).
2. Multi-Attribute Utility AI Goal Evaluator (scores across PAD, drives, personality).
3. 24 Concrete Behaviors library with entry conditions and transition rules.
4. Living Bio-Oscillators (Breathing heave on tilt, Poisson micro-saccades, 1D Perlin sway).
"""

import math
import time
import random
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Callable

from core.affective_engine import PADState, HomeostaticDrives, PersonalityTraits

# =============================================================================
# 1. Behavior Identifiers (24 Concrete Behaviors)
# =============================================================================

class BehaviorID(Enum):
    # Reflexive & Safety (Priority 90-100)
    EMERGENCY_RECOIL   = "EMERGENCY_RECOIL"
    THERMAL_SHUTDOWN   = "THERMAL_SHUTDOWN"
    STARTLE_JUMP       = "STARTLE_JUMP"

    # Vital & Homeostatic (Priority 70-85)
    SEEK_DOCK          = "SEEK_DOCK"
    SLEEP_RECHARGE     = "SLEEP_RECHARGE"
    MORNING_WAKEUP     = "MORNING_WAKEUP"

    # Social & Attachment (Priority 60-70)
    GREET_OWNER        = "GREET_OWNER"
    BEG_FOR_ATTENTION  = "BEG_FOR_ATTENTION"
    ENJOY_PETTING      = "ENJOY_PETTING"
    SULK_WITHDRAWN     = "SULK_WITHDRAWN"

    # Curiosity & Exploration (Priority 45-60)
    INVESTIGATE_SOUND  = "INVESTIGATE_SOUND"
    INSPECT_OBJECT     = "INSPECT_OBJECT"
    PLAY_TAG_CHASE     = "PLAY_TAG_CHASE"
    POUNCE_PLAY        = "POUNCE_PLAY"
    WANDER_CURIOUS     = "WANDER_CURIOUS"
    PERIMETER_PATROL   = "PERIMETER_PATROL"

    # Idle & Attentive (Priority 25-45)
    LOOK_AT_FACE       = "LOOK_AT_FACE"
    SUNBATHE_WARM      = "SUNBATHE_WARM"
    CONFUSED_TILT      = "CONFUSED_TILT"
    DAYDREAM_GLANCE    = "DAYDREAM_GLANCE"

    # Living Micro-Behaviors (Parallel Bio-Oscillators)
    TREAD_STRETCH      = "TREAD_STRETCH"
    MICRO_SACCADE      = "MICRO_SACCADE"
    BREATHING_HEAVE    = "BREATHING_HEAVE"
    SPONTANEOUS_BLINK  = "SPONTANEOUS_BLINK"

# =============================================================================
# 2. Multi-Attribute Utility AI Evaluator
# =============================================================================

class UtilityEvaluator:
    """
    Evaluates multi-attribute utility curves to select the optimal behavioral goal
    balancing self-preservation, affective state, and personality biases.
    """

    @staticmethod
    def evaluate(
        pad: PADState,
        drives: HomeostaticDrives,
        traits: PersonalityTraits,
        perception: Dict[str, Any]
    ) -> Tuple[BehaviorID, float]:
        """Returns the winning (BehaviorID, utility_score)."""

        # ---------------------------------------------------------------------
        # Tier 0: Reflexive Safety Overrides (<10ms Reaction)
        # ---------------------------------------------------------------------
        if perception.get("cliff_detected", False) or perception.get("freefall", False):
            return BehaviorID.EMERGENCY_RECOIL, 100.0

        if perception.get("overheat", False) or perception.get("stall_current", False):
            return BehaviorID.THERMAL_SHUTDOWN, 99.0

        if perception.get("loud_sound", False):
            return BehaviorID.STARTLE_JUMP, 90.0

        # ---------------------------------------------------------------------
        # Tier 1: Vital Homeostatic Demands
        # ---------------------------------------------------------------------
        if drives.energy < 0.12 or perception.get("battery_critical", False):
            return BehaviorID.SEEK_DOCK, 85.0

        if perception.get("dock_charging", False) or (pad.arousal < -0.45 and perception.get("darkness", False)):
            return BehaviorID.SLEEP_RECHARGE, 80.0

        # ---------------------------------------------------------------------
        # Tier 2: Continuous Utility Scoring
        # ---------------------------------------------------------------------
        scores: Dict[BehaviorID, float] = {}

        # 1. Enjoy Petting (Driven by touch + social need + clinginess)
        if perception.get("touch_active", False):
            u_pet = 0.50 + (1.0 - drives.social) * 0.35 + traits.clingy * 0.25 + pad.valence * 0.15
            scores[BehaviorID.ENJOY_PETTING] = u_pet
        else:
            scores[BehaviorID.ENJOY_PETTING] = 0.0

        # 2. Greet Owner (Owner face or enthusiastic voice + social urge)
        if perception.get("owner_face_visible", False) or perception.get("wake_word_detected", False):
            u_greet = 0.45 + (1.0 - drives.social) * 0.40 + pad.arousal * 0.20 + (1.0 - traits.shy) * 0.15
            scores[BehaviorID.GREET_OWNER] = u_greet
        else:
            scores[BehaviorID.GREET_OWNER] = 0.0

        # 3. Beg for Attention (Low social drive, owner in room, high clinginess)
        if drives.social < 0.30 and perception.get("owner_present", False):
            scores[BehaviorID.BEG_FOR_ATTENTION] = 0.40 + (0.30 - drives.social) * 0.8 + traits.clingy * 0.25
        else:
            scores[BehaviorID.BEG_FOR_ATTENTION] = 0.0

        # 4. Sulk Withdrawn (Prolonged social neglect + very low valence)
        if pad.valence < -0.35 and drives.social < 0.25:
            scores[BehaviorID.SULK_WITHDRAWN] = 0.45 + abs(pad.valence) * 0.35
        else:
            scores[BehaviorID.SULK_WITHDRAWN] = 0.0

        # 5. Play Tag / Chase (Playful trait + moving stimulus + high arousal)
        if traits.playful > 0.55 and perception.get("motion_detected", False) and pad.arousal > 0.30:
            scores[BehaviorID.PLAY_TAG_CHASE] = 0.35 + traits.playful * 0.30 + pad.arousal * 0.25
        else:
            scores[BehaviorID.PLAY_TAG_CHASE] = 0.0

        # 6. Inspect Object (Novel visual bounding box + curiosity drive)
        if perception.get("novel_object_visible", False):
            scores[BehaviorID.INSPECT_OBJECT] = 0.35 + drives.curiosity * 0.45 + traits.curious * 0.25
        else:
            scores[BehaviorID.INSPECT_OBJECT] = 0.0

        # 7. Investigate Sound (Directional audio sound cue)
        if perception.get("unclassified_sound", False):
            scores[BehaviorID.INVESTIGATE_SOUND] = 0.30 + drives.curiosity * 0.35 + (1.0 - traits.shy) * 0.20
        else:
            scores[BehaviorID.INVESTIGATE_SOUND] = 0.0

        # 8. Wander Curious (Autonomous exploration)
        scores[BehaviorID.WANDER_CURIOUS] = 0.20 + drives.curiosity * 0.40 + pad.arousal * 0.25

        # 9. Perimeter Patrol (Bold trait + uncharted desk/room perimeter)
        if traits.bold > 0.55 and drives.energy > 0.40:
            scores[BehaviorID.PERIMETER_PATROL] = 0.15 + traits.bold * 0.35 + drives.curiosity * 0.20
        else:
            scores[BehaviorID.PERIMETER_PATROL] = 0.0

        # 10. Daydream Glance / Idle Presence (Default peaceful baseline)
        scores[BehaviorID.DAYDREAM_GLANCE] = 0.18 + (1.0 - pad.arousal) * 0.25 + pad.valence * 0.15

        winning_id = max(scores, key=scores.get)
        return winning_id, float(scores[winning_id])

# =============================================================================
# 3. Living Bio-Oscillator (Breathing, Micro-Saccades, Postural Sway)
# =============================================================================

class LivingBioOscillator:
    """
    Synthesizes continuous non-repeating biological micro-movements to ensure
    the robot appears genuinely alive even when completely stationary.
    """

    def __init__(self):
        self.start_time = time.time()
        self.next_micro_saccade_time = time.time() + 2.0
        self.saccade_dx = 0.0
        self.saccade_dy = 0.0
        self.next_blink_time = time.time() + random.uniform(3.0, 6.0)
        self.is_blinking = False
        self.blink_progress = 0.0

    def step(self, dt: float, arousal: float) -> Dict[str, float]:
        """
        Advances biological oscillators.
        Returns: {breathing_tilt, saccade_x, saccade_y, postural_sway, is_blinking}
        """
        now = time.time()
        elapsed = now - self.start_time

        # 1. Breathing Sinusoid (Frequency scaled by arousal: 0.16 Hz sleepy to 0.45 Hz excited)
        f_breath = 0.22 + 0.12 * max(-0.5, min(1.0, arousal))
        amplitude = 1.15
        breathing_tilt = math.sin(2.0 * math.pi * f_breath * elapsed) * amplitude

        # 2. Pseudo-Random Coherent Postural Sway (Multi-octave sine blend approximating Perlin noise)
        sway_pan = (
            math.sin(elapsed * 0.35) * 0.45
            + math.sin(elapsed * 0.73) * 0.25
            + math.sin(elapsed * 1.41) * 0.12
        )

        # 3. Micro-Saccades (Poisson ocular fixation twitches)
        if now >= self.next_micro_saccade_time:
            self.saccade_dx = random.uniform(-0.05, 0.05)
            self.saccade_dy = random.uniform(-0.03, 0.03)
            # Poisson interval (mean 2.8s)
            self.next_micro_saccade_time = now + random.expovariate(1.0 / 2.8)
        else:
            self.saccade_dx *= 0.88
            self.saccade_dy *= 0.88

        # 4. Spontaneous Blinking (120ms total eyelid occlusion)
        if not self.is_blinking and now >= self.next_blink_time:
            self.is_blinking = True
            self.blink_progress = 0.0
            self.next_blink_time = now + random.uniform(3.5, 7.5)

        if self.is_blinking:
            self.blink_progress += dt / 0.12
            if self.blink_progress >= 1.0:
                self.is_blinking = False
                self.blink_progress = 0.0

        return {
            "breathing_tilt": float(breathing_tilt),
            "postural_sway": float(sway_pan),
            "saccade_x": float(self.saccade_dx),
            "saccade_y": float(self.saccade_dy),
            "is_blinking": 1.0 if self.is_blinking else 0.0
        }

# =============================================================================
# 4. Behavior Coordination Engine
# =============================================================================

class BehaviorEngine:
    """Coordinates behavior state machine, entry/exit hooks, and micro-behavior execution."""

    def __init__(self):
        self.active_behavior: BehaviorID = BehaviorID.DAYDREAM_GLANCE
        self.behavior_start_time: float = time.time()
        self.bio_oscillator = LivingBioOscillator()
        self.behavior_dwell_min: float = 2.0  # Minimum seconds to stay in behavior (prevents thrashing)

    def step(
        self,
        dt: float,
        pad: PADState,
        drives: HomeostaticDrives,
        traits: PersonalityTraits,
        perception: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Runs the 20Hz behavior arbitration and micro-dynamics cycle."""
        now = time.time()
        candidate_behavior, score = UtilityEvaluator.evaluate(pad, drives, traits, perception)

        # Preemptive behaviors (Reflexive) override dwell timer immediately
        is_reflexive = candidate_behavior in (
            BehaviorID.EMERGENCY_RECOIL,
            BehaviorID.THERMAL_SHUTDOWN,
            BehaviorID.STARTLE_JUMP
        )

        time_in_behavior = now - self.behavior_start_time
        if is_reflexive or (time_in_behavior >= self.behavior_dwell_min and candidate_behavior != self.active_behavior):
            self.active_behavior = candidate_behavior
            self.behavior_start_time = now

        # Step living bio-oscillators
        bio_metrics = self.bio_oscillator.step(dt, pad.arousal)

        return {
            "behavior_id": self.active_behavior.value,
            "utility_score": round(score, 3),
            "duration_in_state": round(now - self.behavior_start_time, 2),
            **bio_metrics
        }
