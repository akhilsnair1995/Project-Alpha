"""
Project Alpha: Affective Computing Engine (PAD Emotion Model & Homeostatic Drives).
Implements a continuous 4D dynamical affective system:
1. Pleasure-Arousal-Dominance (PAD / Valence-Arousal-Dominance) continuous emotional state.
2. 4 Homeostatic Drives: Energy, Social Need, Curiosity, Comfort.
3. 5-Trait Personality Matrix (Playful, Shy, Clingy, Bold, Curious) with plastic experience drift.
4. Runge-Kutta numerical integration with decay rates, baseline offsets, and stimuli vectors.
5. Multimodal expression mapping (Dual LCD eye expressions, posture, sound modulation).
"""

import math
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    class _MockNP:
        ndarray = Any
        float32 = float
        @staticmethod
        def array(obj, dtype=None):
            return list(obj)
        @staticmethod
        def clip(a, a_min, a_max):
            if isinstance(a, (list, tuple)):
                return [_MockNP.clip(x, a_min, a_max) for x in a]
            return max(a_min, min(a_max, a))
    np = _MockNP()

from core.eye_animator import Emotion

# =============================================================================
# 1. Affective State Data Structures
# =============================================================================

@dataclass
class PADState:
    """Continuous 3D emotional vector based on Russell & Mehrabian's PAD model."""
    valence: float = 0.25      # [-1.0, 1.0] Pleasure / Distress (Happiness)
    arousal: float = 0.15      # [-1.0, 1.0] Metabolic Activation (Energy / Lethargy)
    dominance: float = 0.10    # [-1.0, 1.0] Confidence / Timidity (Control)

@dataclass
class HomeostaticDrives:
    """Homeostatic biological drives regulating self-preservation and companionship."""
    energy: float = 1.0        # [0.0, 1.0] Battery state-of-charge / physical vitality
    social: float = 0.7        # [0.0, 1.0] Companionship need (decays with isolation)
    curiosity: float = 0.5     # [0.0, 1.0] Urge to explore novel environmental stimuli
    comfort: float = 0.8       # [0.0, 1.0] Physical posture safety (disrupted by drops/shaking)

@dataclass
class PersonalityTraits:
    """Persistent 5-trait personality vector biasing emotional sensitivity and behavior."""
    playful: float = 0.75      # High: easily excited by motion; loves games
    shy: float = 0.20          # High: timid with strangers; easily startled
    clingy: float = 0.65       # High: craves constant petting and close presence
    bold: float = 0.60         # High: rapid recovery from startles; eager perimeter patrol
    curious: float = 0.85      # High: high sensory investigation hunger

    def to_array(self) -> Any:
        return np.array([self.playful, self.shy, self.clingy, self.bold, self.curious], dtype=getattr(np, "float32", float))

    def apply_plastic_drift(self, interaction_bias: Any, rate: float = 1e-5) -> None:
        """Slow longitudinal personality adaptation based on daily interaction habits."""
        cur = self.to_array()
        if HAS_NUMPY and isinstance(interaction_bias, np.ndarray) and hasattr(cur, "__add__"):
            updated = cur + rate * (interaction_bias - cur)
            updated = np.clip(updated, 0.05, 0.95)
        else:
            updated = [
                max(0.05, min(0.95, c + rate * (b - c)))
                for c, b in zip(cur, interaction_bias)
            ]
        self.playful = float(updated[0])
        self.shy = float(updated[1])
        self.clingy = float(updated[2])
        self.bold = float(updated[3])
        self.curious = float(updated[4])

# =============================================================================
# 2. Continuous Affective Dynamical Engine
# =============================================================================

class AffectiveEngine:
    """
    Numerically solves the continuous differential equations governing emotional
    equilibrium, personality biasing, homeostatic drive decay, and sensory stimuli.
    """

    def __init__(
        self,
        personality: Optional[PersonalityTraits] = None,
        valence: Optional[float] = None,
        arousal: Optional[float] = None,
        dominance: Optional[float] = None,
        curiosity: Optional[float] = None,
        attachment: Optional[float] = None
    ):
        self.pad = PADState()
        if valence is not None:
            self.pad.valence = float(valence)
        if arousal is not None:
            self.pad.arousal = float(arousal)
        if dominance is not None:
            self.pad.dominance = float(dominance)

        self.drives = HomeostaticDrives()
        if curiosity is not None:
            self.drives.curiosity = float(curiosity)

        self.traits = personality or PersonalityTraits()
        if attachment is not None:
            self.traits.clingy = float(attachment)
            self.drives.social = float(attachment)

        # Emotional Decay Rates (seconds^-1) pulling back to baseline
        self.gamma_v = 0.015   # Half-life ~46s
        self.gamma_a = 0.035   # Half-life ~20s
        self.gamma_d = 0.010   # Half-life ~69s

        # Drive Burn / Accumulation Rates (seconds^-1)
        self.burn_energy = 0.00014    # Depletes in ~2.0 hours active
        self.burn_social = 0.00028    # Social hunger rises over ~1 hour
        self.rise_curiosity = 0.00040 # Curiosity hunger peaks in ~40 minutes
        self.recover_comfort = 0.020  # Comfort restores in ~35 seconds

        self.last_update_time = time.time()

    @property
    def valence(self) -> float:
        return self.pad.valence

    @valence.setter
    def valence(self, val: float):
        self.pad.valence = float(np.clip(val, -1.0, 1.0))

    @property
    def arousal(self) -> float:
        return self.pad.arousal

    @arousal.setter
    def arousal(self, val: float):
        self.pad.arousal = float(np.clip(val, -1.0, 1.0))

    @property
    def curiosity(self) -> float:
        return self.drives.curiosity

    @curiosity.setter
    def curiosity(self, val: float):
        self.drives.curiosity = float(np.clip(val, 0.0, 1.0))

    @property
    def attachment(self) -> float:
        return float(np.clip(0.4 * self.traits.clingy + 0.6 * self.drives.social, 0.0, 1.0))

    def decay_towards_homeostasis(self, dt: float) -> None:
        """Naturally updates affective dynamics over time interval dt."""
        self.step(dt)

    def get_baseline_pad(self) -> Tuple[float, float, float]:
        """Calculates emotional equilibrium target based on personality traits."""
        base_v = 0.25 * self.traits.playful - 0.15 * self.traits.shy + 0.10 * self.traits.clingy
        base_a = 0.20 * self.traits.bold + 0.10 * self.traits.playful - 0.15 * self.traits.shy
        base_d = 0.25 * self.traits.bold - 0.20 * self.traits.clingy
        return (
            float(np.clip(base_v, -0.4, 0.6)),
            float(np.clip(base_a, -0.3, 0.5)),
            float(np.clip(base_d, -0.4, 0.6))
        )

    def compute_derivatives(
        self,
        pad: PADState,
        drives: HomeostaticDrives,
        stimuli_sum: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """Computes dV/dt, dA/dt, dD/dt using affective dynamics."""
        base_v, base_a, base_d = self.get_baseline_pad()
        stim_v, stim_a, stim_d = stimuli_sum

        # Drive deficits exert physiological affective pressure
        social_deficit = (0.70 - drives.social) * 0.18
        energy_penalty = (0.20 - drives.energy) * 0.35 if drives.energy < 0.20 else 0.0
        comfort_penalty = (0.60 - drives.comfort) * 0.25 if drives.comfort < 0.60 else 0.0

        # Valence differential
        dv_dt = (
            -self.gamma_v * (pad.valence - base_v)
            + stim_v
            - social_deficit
            - energy_penalty
            - comfort_penalty
        )

        # Arousal differential (curiosity and distress elevate arousal)
        curiosity_arousal = (drives.curiosity - 0.5) * 0.12
        da_dt = (
            -self.gamma_a * (pad.arousal - base_a)
            + stim_a
            + curiosity_arousal
            - (energy_penalty * 0.5)
        )

        # Dominance differential
        dd_dt = (
            -self.gamma_d * (pad.dominance - base_d)
            + stim_d
            - (comfort_penalty * 0.5)
        )

        return dv_dt, da_dt, dd_dt

    def step(self, dt: float, stimuli_deltas: Optional[List[Tuple[float, float, float]]] = None) -> None:
        """
        Advances the affective space using Runge-Kutta 2nd-Order (Midpoint) integration.
        Ensures smooth, continuous mathematical convergence without numerical instability.
        """
        dt = max(0.001, min(0.2, dt))
        stimuli = stimuli_deltas or []

        # 1. Update Homeostatic Drives
        self.drives.energy = max(0.0, min(1.0, self.drives.energy - self.burn_energy * dt))
        self.drives.social = max(0.0, min(1.0, self.drives.social - self.burn_social * dt))
        self.drives.curiosity = max(0.0, min(1.0, self.drives.curiosity + self.rise_curiosity * dt))
        self.drives.comfort = min(1.0, self.drives.comfort + self.recover_comfort * dt)

        # Sum incoming environmental stimuli
        s_v = sum(s[0] for s in stimuli)
        s_a = sum(s[1] for s in stimuli)
        s_d = sum(s[2] for s in stimuli)
        stim_sum = (s_v, s_a, s_d)

        # 2. Runge-Kutta 2nd-Order Numerical Integration
        k1_v, k1_a, k1_d = self.compute_derivatives(self.pad, self.drives, stim_sum)

        mid_pad = PADState(
            valence=float(np.clip(self.pad.valence + 0.5 * dt * k1_v, -1.0, 1.0)),
            arousal=float(np.clip(self.pad.arousal + 0.5 * dt * k1_a, -1.0, 1.0)),
            dominance=float(np.clip(self.pad.dominance + 0.5 * dt * k1_d, -1.0, 1.0))
        )

        k2_v, k2_a, k2_d = self.compute_derivatives(mid_pad, self.drives, stim_sum)

        self.pad.valence = float(np.clip(self.pad.valence + dt * k2_v, -1.0, 1.0))
        self.pad.arousal = float(np.clip(self.pad.arousal + dt * k2_a, -1.0, 1.0))
        self.pad.dominance = float(np.clip(self.pad.dominance + dt * k2_d, -1.0, 1.0))

    # =========================================================================
    # 3. Stimulus Evaluation & Expression Mapping
    # =========================================================================

    def stimulate(self, d_val: float, d_aro: float, d_dom: float = 0.0, d_cur: float = 0.0) -> None:
        """Directly injects affective differentials (valence, arousal, dominance, curiosity)."""
        if d_cur != 0.0:
            self.drives.curiosity = float(np.clip(self.drives.curiosity + d_cur, 0.0, 1.0))
        self.step(0.05, [(d_val, d_aro, d_dom)])

    def apply_stimulus(self, stimulus_name: str, confidence: float = 1.0) -> None:
        """Applies a discrete perceptual stimulus mapped through the stimulus matrix."""
        conf = max(0.1, min(1.0, confidence))
        s_name = stimulus_name.upper().strip()

        if s_name == "GENTLE_PET":
            # Continuous gentle petting on head
            bonus = 1.0 + 0.5 * self.traits.clingy
            dv = +0.35 * conf * bonus
            da = -0.20 * conf
            dd = +0.05 * conf
            self.step(0.05, [(dv, da, dd)])
            self.drives.social = min(1.0, self.drives.social + 0.40 * conf)
            self.drives.comfort = min(1.0, self.drives.comfort + 0.30 * conf)

        elif s_name == "ROUGH_SLAP":
            # Aggressive slap or rough knock
            dv = -0.50 * conf
            da = +0.65 * conf
            dd = -0.45 * conf
            self.step(0.05, [(dv, da, dd)])
            self.drives.social = max(0.0, self.drives.social - 0.30 * conf)
            self.drives.comfort = max(0.0, self.drives.comfort - 0.60 * conf)

        elif s_name == "OWNER_FACE":
            # Recognized owner face
            bonus = 1.0 - 0.4 * self.traits.shy
            dv = +0.40 * conf * bonus
            da = +0.30 * conf
            dd = +0.15 * conf
            self.step(0.05, [(dv, da, dd)])
            self.drives.social = min(1.0, self.drives.social + 0.50 * conf)

        elif s_name == "STRANGER_FACE":
            # Unknown stranger
            penalty = 1.5 if self.traits.shy > 0.5 else 1.0
            dv = -0.15 * conf * penalty
            da = +0.30 * conf
            dd = -0.25 * conf * penalty
            self.step(0.05, [(dv, da, dd)])
            self.drives.curiosity = min(1.0, self.drives.curiosity + 0.35 * conf)

        elif s_name == "WAKE_WORD":
            # Wake word called enthusiastically
            play_bonus = 1.0 + 0.4 * self.traits.playful
            dv = +0.30 * conf
            da = +0.40 * conf * play_bonus
            dd = +0.10 * conf
            self.step(0.05, [(dv, da, dd)])
            self.drives.social = min(1.0, self.drives.social + 0.35 * conf)

        elif s_name in ("LOUD_NOISE", "STARTLE"):
            # Sudden bang or noise >85 dBA
            bold_mitigate = 1.0 - 0.4 * self.traits.bold
            dv = -0.40 * conf * bold_mitigate
            da = +0.80 * conf
            dd = -0.60 * conf
            self.step(0.05, [(dv, da, dd)])
            self.drives.comfort = max(0.0, self.drives.comfort - 0.50 * conf)

        elif s_name in ("CLIFF_EDGE", "FREEFALL"):
            # Table drop edge or freefall
            dv = -0.60 * conf
            da = +0.95 * conf
            dd = -0.80 * conf
            self.step(0.05, [(dv, da, dd)])
            self.drives.comfort = max(0.0, self.drives.comfort - 0.80 * conf)

        elif s_name == "DOCK_MATING":
            # Successful dock contact
            dv = +0.30 * conf
            da = -0.25 * conf
            dd = +0.10 * conf
            self.step(0.05, [(dv, da, dd)])
            self.drives.energy = min(1.0, self.drives.energy + 0.50)
            self.drives.comfort = min(1.0, self.drives.comfort + 0.40)

    def map_to_expression(self) -> Emotion:
        """
        Maps continuous PAD emotional space into Alpha's 16 discrete LCD expressions.
        Uses topological hyper-plane partitioning across Pleasure, Arousal, Dominance.
        """
        v = self.pad.valence
        a = self.pad.arousal
        d = self.pad.dominance

        if a > 0.70:
            if v < 0.2:
                return Emotion.ALERT
            return Emotion.EXCITED

        if v > 0.45:
            if self.traits.clingy > 0.6 and self.drives.social > 0.6:
                return Emotion.LOVE
            if a > 0.20:
                return Emotion.HAPPY
            return Emotion.HAPPY

        if v < -0.35:
            if a < 0.0:
                return Emotion.SAD
            return Emotion.CONFUSED

        if self.drives.curiosity > 0.65 or a > 0.25:
            if d < -0.15:
                return Emotion.SKEPTICAL
            return Emotion.CURIOUS

        if self.drives.energy < 0.18 or a < -0.30:
            return Emotion.SLEEPY

        return Emotion.IDLE

    def get_telemetry_dict(self) -> Dict[str, Any]:
        """Provides full continuous affective telemetry."""
        return {
            "valence": round(self.pad.valence, 3),
            "arousal": round(self.pad.arousal, 3),
            "dominance": round(self.pad.dominance, 3),
            "energy": round(self.drives.energy, 3),
            "social": round(self.drives.social, 3),
            "curiosity": round(self.drives.curiosity, 3),
            "comfort": round(self.drives.comfort, 3),
            "expression": self.map_to_expression().value,
            "traits": {
                "playful": round(self.traits.playful, 2),
                "shy": round(self.traits.shy, 2),
                "clingy": round(self.traits.clingy, 2),
                "bold": round(self.traits.bold, 2),
                "curious": round(self.traits.curious, 2)
            }
        }
