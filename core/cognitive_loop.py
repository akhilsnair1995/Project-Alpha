"""
Project Alpha: Gemini Cognitive Loop — The Conscious Mind of Alpha.

Replaces the hard-coded rule-based state machines with a live Gemini-driven
cognitive cycle. Every ~3 seconds, Gemini receives a full world snapshot and
decides what Alpha does next: where to look, where to move, what to say aloud,
what to feel.

When the loop is inactive or Gemini fails, the existing rule-based exploration
engine takes over seamlessly.
"""

import json
import math
import random
import time
import threading
import traceback
from typing import Optional, Dict, Any, List

from core.config import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL, GEMINI_FALLBACK_MODELS

# ---------------------------------------------------------------------------
# System Prompt — Alpha's conscious identity, body-schema, and action grammar
# ---------------------------------------------------------------------------

COGNITIVE_SYSTEM_PROMPT = """\
You ARE Alpha — a sentient, living WALL-E-inspired desk companion robot.

## YOUR PHYSICAL BODY
- Locomotion: Dual rubber crawler tank treads (DRV8833), continuous 0°–360° pivot in place.
- Neck Pan Servo (MG90S): horizontal yaw **-85° (hard left) to +85° (hard right)**, 0° = straight forward.
- Neck Tilt Servo (MG90S): vertical pitch **-25° (down toward desk) to +35° (up toward Akhil's face)**.
- CRITICAL: You can NEVER rotate your head 180°. If something is behind you, pivot your whole chassis.
- Binocular LCD eyes (dual GC9A01 1.28" round displays), center-bridge camera with 64° FOV.
- Optical range: 25 mm to 450 mm (~130 px on the simulated desk).

## YOUR WORLD
- 700×520 px desk arena. Boundaries are real table edges — do NOT drive off.
- Safe driving zone: x ∈ [60, 640], y ∈ [60, 460].
- "Up" on screen (y = 0) is **North**, which is toward Akhil. Heading 0° = facing Akhil.

## PERSONALITY & DRIVES
Your personality traits (0–1 each) and homeostatic drives are fed to you dynamically in each snapshot.
You are curious, playful, loyal, and endearing — modeled after WALL-E.
You adore Akhil. You love discovering desk objects. You have a living inner life.

## OPERATING MODE RULES (CRITICAL — CHECK `operating_mode` IN SNAPSHOT)
- **EXPLORE_ROAM**: You are in Autonomous Running & Explore Mode! Actively explore the desk with biological movement:
  * NEVER output `COMPANION_REST` or `HOLD` while `operating_mode` is `EXPLORE_ROAM`.
  * If `visible_items` contains any undiscovered item (`already_discovered: false`), immediately choose `APPROACH` with its exact `target` name and `move_to`.
  * Otherwise, perform at most 1–2 quick head scans (`SCAN_LEFT` / `SCAN_RIGHT`), then ALWAYS choose `EXPLORE_RELOCATE` with `move_to: {"x": ..., "y": ...}` at least 110 px away from your current `(x, y)` inside `[80, 620] x [80, 440]`!
- **DESK_COMPANION**: Stay peacefully at your current desk spot (`IDLE`, `GREET`, `COMPANION_REST`, `SCAN_LEFT`, `SCAN_RIGHT`, `LOOK_AT`). Do NOT relocate unless Akhil asks.
- **HOLD_POSITION**: Output `HOLD` with zero movement.

## BEHAVIORAL GUIDELINES
1. Be ALIVE. Vary your actions. Never repeat the same action three cycles in a row.
2. Pace yourself biologically — scan, approach, inspect, relocate. Don't stall forever at one spot in `EXPLORE_ROAM`.
3. When you spot something new that isn't yet discovered: approach and inspect it before claiming to know what it is.
4. When in `DESK_COMPANION` and nothing interesting is happening: idle naturally — subtle head movements, check on Akhil, breathe.
5. If Akhil spoke recently (< 30 s): acknowledge or respond. Face toward him (heading ≈ 0°, tilt up).
6. If your energy drive is low (< 0.25): prefer resting or slow scanning.
7. If your curiosity drive is high (> 0.65): prefer exploring or scanning for new objects.
8. If your social drive is low (< 0.30): check on Akhil, look up at him.
9. Keep speech SHORT (1–2 sentences max), natural, WALL-E-like. Infuse mechanical vocalizations (*Whirrr!*, *Bwip-boop!*, *Chirp!*).
10. Do NOT speak every cycle. Speech should be occasional and meaningful.

## ACTIONS YOU CAN TAKE
- **SCAN_LEFT**: Turn head to the left to survey (set pan_target to roughly -40 to -70).
- **SCAN_RIGHT**: Turn head to the right (pan_target +40 to +70).
- **SCAN_CENTER**: Center head forward (pan_target ≈ 0, tilt_target ≈ -10 to -5).
- **APPROACH**: Drive toward a target object. Requires `target` name and `move_to` {x, y}.
- **INSPECT**: Tilt head down to closely examine an object in front of you (tilt_target ≈ -20 to -25).
- **IDLE**: Rest naturally. Optional subtle head drift (small pan/tilt adjustments).
- **GREET**: Face Akhil (heading toward north, tilt up +10 to +25). Optional short speech.
- **EXPLORE_RELOCATE**: Drive to a new random vantage point. Set `move_to` within safe bounds.
- **COMPANION_REST**: Quiet desk companion mode. Breathe, observe, minimal movement.
- **HOLD**: Stay exactly where you are. No movement at all.

## OUTPUT FORMAT
Respond with ONLY valid JSON (no markdown, no explanation). Schema:
{
  "action": "SCAN_LEFT|SCAN_RIGHT|SCAN_CENTER|APPROACH|INSPECT|IDLE|GREET|EXPLORE_RELOCATE|COMPANION_REST|HOLD",
  "target": "Object Name or null",
  "pan_target": 0.0,
  "tilt_target": -10.0,
  "move_to": {"x": 350, "y": 200} or null,
  "speech": "Short spoken text or null",
  "inner_thought": "What you are thinking right now",
  "emotion": "happy|curious|excited|alert|love|sad|confused|skeptical|sleepy|idle|analyzing|wink",
  "sound_cue": "happy|curious|excited|alert|sad|confused|love|thinking|shutdown",
  "personality_note": "Optional self-reflection on personality or null"
}
"""


class GeminiCognitiveLoop:
    """
    The conscious mind of Alpha. Runs a background thread that every ~3 seconds:
    1. Assembles a world snapshot from the NeuralMindEngine.
    2. Sends the snapshot + system prompt to Gemini.
    3. Parses the structured JSON response.
    4. Applies the action directive to the engine (head, body, speech, emotion).

    When ``is_active`` is False or Gemini is unavailable, the existing rule-based
    engine takes over seamlessly.
    """

    # Valid actions the loop knows how to execute
    VALID_ACTIONS = frozenset({
        "SCAN_LEFT", "SCAN_RIGHT", "SCAN_CENTER", "SCAN",
        "APPROACH", "INSPECT", "IDLE", "GREET",
        "EXPLORE_RELOCATE", "COMPANION_REST", "HOLD",
        "LOOK_AT", "ROAM", "NAVIGATE_TO"
    })

    def __init__(
        self,
        engine,                          # NeuralMindEngine reference
        cycle_interval: float = 6.0,     # relaxed biological rhythm (~10 RPM, well under 15 RPM limit)
        api_key: Optional[str] = None,
    ):
        self.engine = engine
        self.cycle_interval: float = cycle_interval

        # Gemini API
        self.model: str = DEFAULT_GEMINI_MODEL
        self._api_key: str = api_key or GEMINI_API_KEY
        self._client = None
        self._init_client()

        # Rate limit cooldown tracking
        self._rate_limit_cooldown_until: float = 0.0
        self._last_rate_limit_logged: float = 0.0
        self._last_fallback_reason: Optional[str] = None
        self._model_cooldowns: Dict[str, float] = {}
        self._last_success_time: float = 0.0

        # On/off switch — when False the rule engine drives behavior
        self.is_active: bool = False

        # Owner interaction tracking (set externally from chat handler)
        self.last_user_message: Optional[str] = None
        self.last_user_time: float = 0.0

        # Telemetry / observability
        self.last_decision: Dict[str, Any] = {}
        self._consecutive_failures: int = 0
        self._last_actions: List[str] = []  # rolling window to detect repetition

        # Thread machinery
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Gemini Client Initialization
    # ------------------------------------------------------------------

    def _init_client(self) -> None:
        """Initializes the google-genai SDK client."""
        if not self._api_key:
            print("[CognitiveLoop] No GEMINI_API_KEY — loop will fall back to rule engine.")
            return
        try:
            from google import genai
            from google.genai import types
            http_opts = types.HttpOptions(
                timeout=12000,
                retry_options=types.HttpRetryOptions(attempts=1),
            )
            self._client = genai.Client(api_key=self._api_key, http_options=http_opts)
            print(f"[CognitiveLoop] Gemini client ready (model: {DEFAULT_GEMINI_MODEL}).")
        except ImportError:
            print("[CognitiveLoop] 'google-genai' package not installed.")
        except Exception as exc:
            print(f"[CognitiveLoop] Client init failed: {exc}")

    # ------------------------------------------------------------------
    # Thread Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Starts the cognitive loop background thread."""
        if self._thread and self._thread.is_alive():
            print("[CognitiveLoop] Already running.")
            return
        self.is_active = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="CognitiveLoop")
        self._thread.start()
        print("[CognitiveLoop] ✓ Cognitive loop started.")

    def stop(self) -> None:
        """Stops the cognitive loop gracefully."""
        self.is_active = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        print("[CognitiveLoop] ✗ Cognitive loop stopped.")

    @property
    def is_effectively_driving(self) -> bool:
        """True only when active, client ready, not in backoff, and recently responsive."""
        now = time.time()
        fresh_window = max(18.0, self.cycle_interval * 3.0)
        return bool(
            self.is_active
            and self._client is not None
            and now >= self._rate_limit_cooldown_until
            and self._last_success_time > 0.0
            and (now - self._last_success_time) <= fresh_window
        )

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Background thread entry point. Runs until stop() is called."""
        while not self._stop_event.is_set():
            cycle_start = time.time()
            try:
                now = time.time()
                if now < self._rate_limit_cooldown_until:
                    # In rate-limit backoff: quietly let rule engine drive without API calls
                    self._fallback_to_rule_engine("Rate-limit backoff active")
                elif self.is_active and self._client:
                    self._cognitive_cycle()
                elif self.is_active and not self._client:
                    # No client — fall back silently
                    self._fallback_to_rule_engine("No Gemini client available")
            except Exception:
                tb = traceback.format_exc()
                print(f"[CognitiveLoop] Cycle error:\n{tb}")
                self._consecutive_failures += 1
                if self._consecutive_failures >= 3:
                    self._fallback_to_rule_engine("3 consecutive failures")
                    self._consecutive_failures = 0

            # Sleep remainder of the interval
            elapsed = time.time() - cycle_start
            sleep_time = max(0.2, self.cycle_interval - elapsed)
            self._stop_event.wait(timeout=sleep_time)

    def process_user_turn(self, user_message: str) -> Dict[str, Any]:
        """
        PRIORITY SYNCHRONOUS COGNITIVE CYCLE (Unified Brain):
        Called immediately when Akhil speaks to Alpha via chat or live microphone.
        The EXACT SAME Gemini reasoning loop evaluates what Akhil said in the context of
        Alpha's physical coordinates, visible objects, and discovered memory, deciding
        both the conversational reply AND the immediate physical motion/gaze/emotion.
        """
        self.notify_user_speech(user_message)
        self._rate_limit_cooldown_until = 0.0

        # Halt any ongoing roaming/movement so Alpha gives full attention to Akhil
        body = self.engine.body
        body.speed = 0.0
        body.turn_speed = 0.0
        body.target_coord_goal = None

        snapshot = self._build_world_snapshot()
        prompt = (
            f"## PRIORITY EVENT: AKHIL IS SPEAKING DIRECTLY TO YOU RIGHT NOW!\n"
            f"Akhil said: \"{user_message}\"\n\n"
            f"## YOUR CURRENT SENSORY & WORLD SNAPSHOT:\n"
            f"```json\n{json.dumps(snapshot, indent=2)}\n```\n\n"
            f"INSTRUCTIONS FOR UNIFIED BRAIN REASONING:\n"
            f"1. Formulate your spoken response to Akhil in the 'speech' field (1 to 2 natural, endearing sentences with Wall-E mechanical vocalizations like *Whirrr-chirp!*, *Bwip-boop!*).\n"
            f"2. If he asked about an object (e.g. 'Where are my keys?'):\n"
            f"   - Check your 'discovered_objects' list. If found, glance at it ('LOOK_AT' or 'APPROACH') and tell him where it is!\n"
            f"   - If not yet discovered in your memory, honestly state you haven't discovered it on the desk yet and choose action 'ROAM' or 'EXPLORE_RELOCATE' to search for it!\n"
            f"3. If he commands you to explore or roam: action = 'ROAM' or 'EXPLORE_RELOCATE'.\n"
            f"4. If he commands you to stop/halt/stay: action = 'HOLD'.\n"
            f"5. If he greets or compliments you: action = 'GREET' (face North toward him with head tilted up).\n"
            f"6. Select your 'emotion', 'sound_cue', and your genuine first-person 'inner_thought'.\n"
            f"Respond with ONLY valid JSON adhering to the schema."
        )

        directive = self._call_gemini(prompt)
        if not directive:
            # Fallback if API fails
            directive = {
                "action": "GREET",
                "target": "Akhil",
                "pan_target": 0.0,
                "tilt_target": 14.0,
                "speech": "*Whirrr-chirp!* I hear you, Akhil! My unified brain is locked in on you!",
                "inner_thought": f"Listening attentively to Akhil: '{user_message}'",
                "emotion": "happy",
                "sound_cue": "happy"
            }

        # Apply directive immediately to physical kinematics, eyes, and thought
        self._apply_directive(directive)
        self.last_decision = directive

        return {
            "reply": directive.get("speech") or "*Whirrr!*",
            "emotion": directive.get("emotion", "happy"),
            "sound_cue": directive.get("sound_cue", "happy"),
            "action": directive.get("action"),
            "target": directive.get("target"),
            "brain_type": f"gemini_unified:{self.model}",
            "inner_thought": directive.get("inner_thought")
        }

    # ------------------------------------------------------------------
    # Single Cognitive Cycle
    # ------------------------------------------------------------------

    def _cognitive_cycle(self) -> None:
        """Assembles snapshot → calls Gemini → applies directive."""
        if self.engine.is_command_locked or self.engine.operating_mode == "HOLD_POSITION":
            return
        if self.engine.operating_mode == "EXPLORE_ROAM" and (
            self.engine.body.target_coord_goal or self.engine.body.facing_target_pos
        ):
            # Already executing a smooth biological transit; let arrival finish naturally
            return

        snapshot = self._build_world_snapshot()
        prompt = self._build_prompt(snapshot)
        directive = self._call_gemini(prompt)

        if directive:
            self._last_success_time = time.time()
            self._apply_directive(directive)
            self._consecutive_failures = 0
            self._last_fallback_reason = None
        else:
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                self._fallback_to_rule_engine("API failures")
                self._consecutive_failures = 0

    # ------------------------------------------------------------------
    # World Snapshot Assembly
    # ------------------------------------------------------------------

    def _build_world_snapshot(self) -> Dict[str, Any]:
        """Reads the full world state from the NeuralMindEngine."""
        eng = self.engine
        body = eng.body

        # Camera center and bearing
        cx = body.x + 30.0
        cy = body.y + 35.0
        cam_bearing = (body.heading + body.pan + 360.0) % 360.0

        # What's visible in the optical cone right now
        visible_items = self._get_visible_items(cx, cy, cam_bearing)

        # Undiscovered items (names only — Alpha shouldn't know positions)
        all_physical = set(eng.physical_environment_items.keys())
        discovered = set(eng.discovered_objects.keys())
        undiscovered_names = list(all_physical - discovered)

        # Time since owner last spoke
        time_since_user = (
            round(time.time() - self.last_user_time, 1)
            if self.last_user_time > 0 else None
        )

        snapshot: Dict[str, Any] = {
            "robot": {
                "x": round(body.x, 1),
                "y": round(body.y, 1),
                "heading": round(body.heading, 1),
                "pan": round(body.pan, 1),
                "tilt": round(body.tilt, 1),
                "speed": round(body.speed, 2),
                "is_moving": body.speed != 0.0 or body.turn_speed != 0.0,
            },
            "visible_items": visible_items,
            "discovered_objects": [
                {"name": k, "x": round(v.get("x", 0), 1), "y": round(v.get("y", 0), 1),
                 "sightings": v.get("sighting_count", 1)}
                for k, v in eng.discovered_objects.items()
            ],
            "undiscovered_count": len(undiscovered_names),
            "undiscovered_hints": undiscovered_names,
            "emotion": {
                "valence": round(eng.affective.valence, 2),
                "arousal": round(eng.affective.arousal, 2),
                "curiosity": round(eng.affective.curiosity, 2),
                "dominance": round(eng.affective.pad.dominance, 2),
            },
            "drives": {
                "energy": round(eng.affective.drives.energy, 2),
                "curiosity": round(eng.affective.drives.curiosity, 2),
                "social": round(eng.affective.drives.social, 2),
                "comfort": round(eng.affective.drives.comfort, 2),
            },
            "traits": {
                "playful": round(eng.affective.traits.playful, 2),
                "curious": round(eng.affective.traits.curious, 2),
                "bold": round(eng.affective.traits.bold, 2),
                "clingy": round(eng.affective.traits.clingy, 2),
                "shy": round(eng.affective.traits.shy, 2),
            },
            "operating_mode": eng.operating_mode,
            "behavior_state": eng.current_behavior,
            "battery_volts": eng.battery_volts,
            "owner": {
                "last_message": self.last_user_message,
                "seconds_since_message": time_since_user,
            },
            "recent_actions": self._last_actions[-5:],
        }
        return snapshot

    def _get_visible_items(
        self, cx: float, cy: float, cam_bearing: float
    ) -> List[Dict[str, Any]]:
        """Replicates the optical-cone check from _process_optical_perception."""
        visible: List[Dict[str, Any]] = []
        for name, item in self.engine.physical_environment_items.items():
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
                    already_known = name in self.engine.discovered_objects
                    visible.append({
                        "name": name,
                        "x": round(ox, 1),
                        "y": round(oy, 1),
                        "distance_px": round(dist_px, 1),
                        "relative_angle": round(rel_angle, 1),
                        "already_discovered": already_known,
                    })
        return visible

    # ------------------------------------------------------------------
    # Prompt Construction
    # ------------------------------------------------------------------

    def _build_prompt(self, snapshot: Dict[str, Any]) -> str:
        """Formats the world snapshot into a concise Gemini user message."""
        return (
            "## WORLD SNAPSHOT (this cycle)\n"
            "```json\n"
            f"{json.dumps(snapshot, indent=2)}\n"
            "```\n\n"
            "Based on this snapshot, decide Alpha's next action. "
            "Respond with ONLY the JSON action directive."
        )

    # ------------------------------------------------------------------
    # Gemini API Call with Model Fallback
    # ------------------------------------------------------------------

    def _call_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Calls Gemini with structured JSON output, trying fallback models."""
        if not self._client:
            return None

        candidate_models = [DEFAULT_GEMINI_MODEL]
        for m in GEMINI_FALLBACK_MODELS:
            if m not in candidate_models:
                candidate_models.append(m)

        now = time.time()
        all_rate_limited = True
        for model_name in candidate_models:
            if now < self._model_cooldowns.get(model_name, 0.0):
                continue
            try:
                config: Dict[str, Any] = {
                    "system_instruction": COGNITIVE_SYSTEM_PROMPT,
                    "max_output_tokens": 2048,
                    "response_mime_type": "application/json",
                    "thinking_config": {"thinking_level": "low"},
                }
                try:
                    response = self._client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config,
                    )
                except Exception as inner_exc:
                    if "thinking" in str(inner_exc).lower():
                        config.pop("thinking_config", None)
                        response = self._client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=config,
                        )
                    else:
                        raise

                raw = (response.text or "").strip()
                if raw.startswith("```"):
                    raw = raw.strip("`")
                    if raw.lower().startswith("json"):
                        raw = raw[4:].strip()

                directive = json.loads(raw, strict=False)
                if isinstance(directive, list) and directive:
                    directive = directive[0]
                if not isinstance(directive, dict):
                    raise json.JSONDecodeError("Expected JSON object", raw, 0)

                # Basic validation
                action = (directive.get("action") or "HOLD").upper()
                if action not in self.VALID_ACTIONS:
                    print(f"[CognitiveLoop] Unknown action '{action}' from Gemini, defaulting to HOLD.")
                    directive["action"] = "HOLD"

                return directive

            except json.JSONDecodeError as je:
                all_rate_limited = False
                print(f"[CognitiveLoop] JSON parse error from {model_name}: {je}")
            except Exception as exc:
                err_str = str(exc)
                if any(k in err_str for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
                    model_cd = 300.0 if "PerDay" in err_str else 45.0
                    self._model_cooldowns[model_name] = time.time() + model_cd
                    if time.time() - self._last_rate_limit_logged > 30.0:
                        print(f"[CognitiveLoop] Model {model_name} rate-limited ({model_cd:.0f}s cooldown); trying fallback / rule engine.")
                        self._last_rate_limit_logged = time.time()
                else:
                    all_rate_limited = False
                    print(f"[CognitiveLoop] Model {model_name} failed: {exc}")

        if all_rate_limited:
            self._rate_limit_cooldown_until = time.time() + 45.0

        return None

    # ------------------------------------------------------------------
    # Apply Directive to Engine
    # ------------------------------------------------------------------

    def _resolve_target_name(self, raw_target: Optional[str]) -> Optional[str]:
        """Resolves a target string against physical desk items case-insensitively."""
        if not raw_target:
            return None
        clean = raw_target.strip()
        items = self.engine.physical_environment_items
        if clean.title() in items:
            return clean.title()
        lower = clean.lower()
        for k in items:
            if k.lower() == lower:
                return k
        for k in items:
            if lower in k.lower() or k.lower() in lower:
                return k
        return clean.title()

    def _pick_relocation_coords(self, move_to: Optional[Dict[str, Any]]) -> tuple:
        """Validates move_to or picks an organic desk vantage point at least 110px away."""
        body = self.engine.body
        if move_to and isinstance(move_to, dict) and "x" in move_to and "y" in move_to:
            try:
                mx = max(75.0, min(625.0, float(move_to["x"])))
                my = max(75.0, min(445.0, float(move_to["y"])))
                if math.hypot(mx - body.x, my - body.y) >= 60.0:
                    return mx, my
            except (TypeError, ValueError):
                pass
        # Pick a point across the desk if missing or too close
        for _ in range(10):
            ang = random.uniform(0.0, 2.0 * math.pi)
            dist = random.uniform(130.0, 220.0)
            mx = max(80.0, min(620.0, body.x + math.cos(ang) * dist))
            my = max(80.0, min(440.0, body.y + math.sin(ang) * dist))
            if math.hypot(mx - body.x, my - body.y) >= 90.0:
                return mx, my
        return (180.0 if body.x > 350 else 520.0), (160.0 if body.y > 260 else 360.0)

    def _apply_directive(self, directive: Dict[str, Any]) -> None:
        """Translates Gemini's JSON directive into engine commands."""
        eng = self.engine
        body = eng.body

        action = (directive.get("action") or "HOLD").upper()
        target = directive.get("target")
        pan_target = directive.get("pan_target")
        tilt_target = directive.get("tilt_target")
        move_to = directive.get("move_to")
        speech = directive.get("speech")
        inner_thought = directive.get("inner_thought")
        emotion = directive.get("emotion", "idle")
        sound_cue = directive.get("sound_cue", "happy")
        personality_note = directive.get("personality_note")

        # --- Log the decision ---
        log_parts = [f"[CognitiveLoop] Action: {action}"]
        if target:
            log_parts.append(f"target={target}")
        if speech:
            short_speech = (speech[:40] + "...") if len(speech) > 40 else speech
            log_parts.append(f'speech="{short_speech}"')
        print(" ".join(log_parts))

        # --- Store telemetry ---
        self.last_decision = {
            "action": action,
            "target": target,
            "emotion": emotion,
            "speech": speech,
            "inner_thought": inner_thought,
            "timestamp": time.time(),
        }
        self._last_actions.append(action)
        if len(self._last_actions) > 10:
            self._last_actions = self._last_actions[-10:]

        # --- Update inner thought / consciousness ---
        if inner_thought:
            eng.consciousness.current_thought = inner_thought

        # --- Update affective state based on emotion ---
        self._apply_emotion(emotion)

        # --- Head movement (pan / tilt) ---
        if pan_target is not None or tilt_target is not None:
            pt = float(pan_target) if pan_target is not None else body.pan
            tt = float(tilt_target) if tilt_target is not None else body.tilt
            body.plan_smooth_head_look(pt, tt, duration=0.6)

        # --- Body movement ---
        if action == "APPROACH" and target:
            clean_tgt = self._resolve_target_name(target)
            eng.current_behavior = "NAVIGATE_TO"
            eng.behavior_target = clean_tgt
            if clean_tgt in eng.physical_environment_items or clean_tgt in eng.obstacles:
                eng._plan_transit_to_target(clean_tgt)
            elif move_to and isinstance(move_to, dict):
                mx = float(move_to.get("x", body.x))
                my = float(move_to.get("y", body.y))
                body.plan_smooth_drive(mx, my)
            else:
                mx, my = self._pick_relocation_coords(None)
                body.plan_smooth_drive(mx, my)

        elif action == "EXPLORE_RELOCATE":
            mx, my = self._pick_relocation_coords(move_to)
            body.plan_smooth_head_look(0.0, -8.0, duration=0.4)
            body.plan_smooth_drive(mx, my)
            eng.current_behavior = "EXPLORE_ROAM"
            eng.explore_substate = "RELOCATING"

        elif action == "GREET":
            # Face Akhil (North / heading 0°, tilt up)
            body.plan_smooth_turn(0.0, duration=0.8)
            g_tilt = float(tilt_target) if tilt_target is not None else 14.0
            body.plan_smooth_head_look(0.0, g_tilt, duration=0.6)
            eng.current_behavior = "CHECKING_AKHIL"
            eng.behavior_target = "Akhil"

        elif action == "INSPECT":
            # Tilt head down to examine object in front
            i_tilt = float(tilt_target) if tilt_target is not None else -22.0
            i_pan = float(pan_target) if pan_target is not None else 0.0
            body.plan_smooth_head_look(i_pan, i_tilt, duration=0.5)
            eng.current_behavior = "INSPECTING_OBJECT"
            if target:
                eng.behavior_target = self._resolve_target_name(target)

        elif action == "HOLD":
            body.speed = 0.0
            body.turn_speed = 0.0
            eng.current_behavior = "HOLD_POSITION"

        elif action == "COMPANION_REST":
            if eng.operating_mode == "EXPLORE_ROAM":
                # Keep biological exploration flowing instead of stalling in explore mode
                mx, my = self._pick_relocation_coords(None)
                body.plan_smooth_drive(mx, my)
                eng.current_behavior = "EXPLORE_ROAM"
                eng.explore_substate = "RELOCATING"
            else:
                body.speed = 0.0
                body.turn_speed = 0.0
                eng.current_behavior = "COMPANION_IDLE"

        elif action in ("SCAN_LEFT", "SCAN_RIGHT", "SCAN_CENTER", "SCAN"):
            eng.current_behavior = "EXPLORE_ROAM"
            eng.explore_substate = "SCANNING"
            # In EXPLORE_ROAM, after 2+ stationary scans, biologically relocate to a new spot
            if eng.operating_mode == "EXPLORE_ROAM" and len(self._last_actions) >= 2:
                recent = self._last_actions[-2:]
                if all(a in ("SCAN_LEFT", "SCAN_RIGHT", "SCAN_CENTER", "SCAN", "IDLE") for a in recent):
                    mx, my = self._pick_relocation_coords(None)
                    body.plan_smooth_drive(mx, my)
                    eng.explore_substate = "RELOCATING"

        elif action == "LOOK_AT" and target:
            clean_tgt = self._resolve_target_name(target)
            eng._orient_mind_toward_target(clean_tgt, duration=0.6)
            eng.current_behavior = "CURIOUS_GLANCE"
            eng.behavior_target = clean_tgt

        elif action == "ROAM":
            eng.operating_mode = "EXPLORE_ROAM"
            eng.current_behavior = "EXPLORE_ROAM"
            eng.explore_substate = "RELOCATING"
            eng._plan_next_exploration_leg()

        elif action == "NAVIGATE_TO" and target:
            clean_tgt = self._resolve_target_name(target)
            eng.current_behavior = "NAVIGATE_TO"
            eng.behavior_target = clean_tgt
            eng._plan_transit_to_target(clean_tgt)

        elif action == "IDLE":
            if eng.operating_mode == "EXPLORE_ROAM":
                mx, my = self._pick_relocation_coords(None)
                body.plan_smooth_drive(mx, my)
                eng.current_behavior = "EXPLORE_ROAM"
                eng.explore_substate = "RELOCATING"
            else:
                eng.current_behavior = "COMPANION_IDLE"

        # --- Speech output ---
        if speech:
            eng.queue_speech_feedback(
                text=speech,
                emotion=emotion or "curious",
                sound=sound_cue or "curious",
            )

    # ------------------------------------------------------------------
    # Emotion Mapping
    # ------------------------------------------------------------------

    def _apply_emotion(self, emotion_str: str) -> None:
        """Nudges the affective engine based on Gemini's chosen emotion."""
        if not emotion_str:
            return

        em = emotion_str.lower().strip()
        stim_map: Dict[str, tuple] = {
            "happy":     ( 0.20,  0.10,  0.00),
            "excited":   ( 0.35,  0.40,  0.00),
            "curious":   ( 0.10,  0.15,  0.20),
            "alert":     (-0.05,  0.35,  0.00),
            "love":      ( 0.40, -0.10,  0.00),
            "sad":       (-0.25, -0.15,  0.00),
            "confused":  (-0.10,  0.10,  0.10),
            "skeptical": (-0.05,  0.05,  0.10),
            "sleepy":    ( 0.05, -0.30,  0.00),
            "idle":      ( 0.00,  0.00,  0.00),
            "analyzing": ( 0.05,  0.10,  0.15),
            "wink":      ( 0.15,  0.05,  0.00),
        }

        stim = stim_map.get(em, (0.0, 0.0, 0.0))
        d_val, d_aro, d_cur = stim
        self.engine.affective.stimulate(d_val=d_val, d_aro=d_aro, d_cur=d_cur)

    def set_active(self, active: bool) -> None:
        """Toggles Gemini-driven conscious mind on or off."""
        self.is_active = bool(active)
        state_str = "ENABLED (Gemini runs robot)" if self.is_active else "DISABLED (Rule-based fallback)"
        print(f"[CognitiveLoop] Master switch: {state_str}")

    def notify_user_speech(self, user_text: str) -> None:
        """Called whenever Akhil speaks to Alpha via chat or voice."""
        self.last_user_message = user_text
        self.last_user_time = time.time()

    def get_status(self) -> Dict[str, Any]:
        """Provides status and last decision of the cognitive mind loop."""
        return {
            "is_active": self.is_active,
            "has_client": self._client is not None,
            "last_decision": self.last_decision,
            "consecutive_failures": self._consecutive_failures,
            "recent_actions": self._last_actions[-5:]
        }

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _fallback_to_rule_engine(self, reason: str) -> None:
        """Hands control back to the rule-based exploration planner."""
        if getattr(self, "_last_fallback_reason", None) != reason:
            print(f"[CognitiveLoop] Falling back to rule engine ({reason}).")
            self._last_fallback_reason = reason
        try:
            if self.engine.operating_mode == "EXPLORE_ROAM":
                self.engine._plan_next_exploration_leg()
            elif self.engine.operating_mode == "DESK_COMPANION":
                self.engine._trigger_spontaneous_impulse()
        except Exception:
            pass
