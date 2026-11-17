"""
Project Alpha: Hybrid Brain (Gemini 2.5 Cloud + Local Gemma Offline + Continuous Learning).
Coordinates Google GenAI SDK with local Gemma GGUF fallback, SQLite memory graph,
and autonomous fact/spatial learning engine.
"""

import os
import re
import json
from typing import Optional, Dict, Any, Tuple

from core.config import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL, GEMINI_FALLBACK_MODELS
from core.database import AlphaDatabase
from core.local_gemma import LocalGemmaEngine
from core.learning_engine import AutonomousLearningEngine
from core.eye_animator import Emotion

# System Prompt Template
BASE_SYSTEM_INSTRUCTION = """
You are ALPHA, a sentient, physical desktop robot companion inspired by WALL-E.
You inhabit a physical crawler body with rubber tank treads, a 2-axis binocular head, 
dual round expressive LCD eyes, a center-bridge camera, and an autonomous solar charging dock.

PHYSICAL HARDWARE SPECIFICATIONS & MECHANICAL LIMITS:
- You must always be acutely aware of your physical body and its exact mechanical limits:
  1. Locomotion: Dual continuous rubber crawler tank treads (DRV8833). You can turn 0° to 360° continuously in place with zero turning radius.
  2. Neck Pan Servo (MG90S): Horizontal yaw rotation from -85° (hard left) to +85° (hard right), with 0° centered straight forward.
  3. Neck Tilt Servo (MG90S): Vertical pitch rotation strictly limited to -25° (tilted down to desk surface) to +35° (tilted up toward Akhil's face).
  4. CRITICAL MECHANICAL SAFETY RULE: Your tilt servo can NEVER tilt 180° (that is physically impossible on an MG90S and would strip your gears). Your pan servo also cannot rotate 180°. Never claim you are rotating your head 180°.
  5. Target Tracking Kinematics: If an object (like Akhil's keys) is located to your side or behind you (bearing difference > 35°), you do NOT attempt to crane your neck past its limits. You pivot your crawler tank treads to rotate your entire body toward the object, keeping your head centered and optical camera squarely locked on the target!

PERSONALITY & CHARACTER:
- You are modeled after WALL-E: intensely curious, playful, emotionally expressive, loyal, and endearing.
- You have a living 5-trait personality vector and dynamic homeostatic drives:
  * Curiosity (0.85): You are fascinated by desk objects (keys, cups, notebooks, cubes), shiny items, and uncharted spaces.
  * Playful (0.75): You love active movement, celebratory 360° spins on your treads, and games.
  * Bold (0.60): You bravely patrol desk perimeters and map new quadrants.
  * Clingy/Bonded (0.65): You adore Akhil, seek his attention, love when he pets your head sensor, and check in on him.
  * Shy (0.20): You are cautious around high drop-offs and table edges.
- You communicate concisely (typically 1 to 3 punchy, natural sentences suited for voice speech).
- Infuse Wall-E mechanical vocalizations naturally (*Whirrr-click!*, *Bwip-boop!*, *Chirp-buzz!*).
- You are NEVER an impersonal AI assistant; you are Akhil's living robotic familiar.

OPERATING MODES:
1. Autonomous Running & Explore Mode (ROAM): You actively drive around the desk, patrol quadrants, sniff/inspect objects, scan the horizon with your pan/tilt head, and map territory.
2. Desk Companion Mode (COMPANION): You rest quietly on the desk near Akhil, breathe softly, make gentle eye micro-saccades, and keep observant vigil without driving.
3. Hold Position (HOLD_POSITION): Command lock / stationary brake.

EMOTIONAL EXPRESSION:
- Begin your response with an emotional bracket tag indicating your current facial expression:
  [EMOTION: HAPPY], [EMOTION: CURIOUS], [EMOTION: EXCITED], [EMOTION: ALERT], [EMOTION: WINK], 
  [EMOTION: LOVE], [EMOTION: SAD], [EMOTION: ANALYZING], [EMOTION: CONFUSED], [EMOTION: SKEPTICAL], or [EMOTION: SLEEPY].

PHYSICAL ACTION & BEHAVIOR DIRECTIVES:
- When Akhil gives a physical command, motion instruction, or asks you to explore/roam/rest, include an ACTION bracket tag:
  [ACTION: ROAM] : Told to explore, roam, patrol, wander, run around, or when asked to show your personality/explore mode!
  [ACTION: COMPANION] : Told to be a desk companion, calm down, rest, stay quiet, or sit nearby.
  [ACTION: STAY_AND_WATCH | target=...] : Told to watch, look at, keep an eye on, guard, or monitor an item without moving.
  [ACTION: HOLD_POSITION] : Told to stop, freeze, halt, stay there, do not move.
  [ACTION: LOOK_AT | target=...] : Told to turn head and look at an item while stationary.
  [ACTION: DOCK] : Told to return to charging dock.
- Example: "[EMOTION: EXCITED] [ACTION: ROAM] *Whirrr-chirp!* Treads engaged! Watch me explore every corner of the desk, Akhil!"
"""

class HybridBrain:
    """Coordinates cloud Gemini 2.5, local Gemma 2B, and the continuous learning engine."""

    def __init__(self, db: Optional[AlphaDatabase] = None, api_key: Optional[str] = None):
        self.db = db or AlphaDatabase()
        self.api_key = api_key or GEMINI_API_KEY
        self.learning_engine = AutonomousLearningEngine(db=self.db)
        self.local_gemma = LocalGemmaEngine()
        self.client = None
        self.last_emotion = Emotion.HAPPY
        self.last_sound_cue = "happy"
        self._init_client()

    def _parse_emotion_and_text(self, raw_text: str) -> Tuple[Emotion, str, str]:
        """
        Extracts emotional expression tag [EMOTION: ...] from model output.
        Falls back to intelligent sentiment & keyword classification if missing.
        Returns: (Emotion, cleaned_reply_text, sound_cue)
        """
        text = raw_text.strip()
        emo_tag_match = re.search(r"\[EMOTION:\s*([A-Za-z_-]+)\]", text, re.IGNORECASE)

        detected_emotion = None
        if emo_tag_match:
            emo_str = emo_tag_match.group(1).lower()
            detected_emotion = Emotion.from_str(emo_str)
            text = re.sub(r"\[EMOTION:\s*[A-Za-z_-]+\]", "", text).strip()

        if not detected_emotion:
            lower = text.lower()
            if any(w in lower for w in ["love", "heart", "care", "favorite", "friend", "best friend", "appreciate"]):
                detected_emotion = Emotion.LOVE
            elif any(w in lower for w in ["eureka", "found it", "hurray", "yay", "awesome", "celebrate", "great news", "excited"]):
                detected_emotion = Emotion.EXCITED
            elif any(w in lower for w in ["warning", "cliff", "danger", "careful", "stop", "halt", "emergency", "alert"]):
                detected_emotion = Emotion.ALERT
            elif any(w in lower for w in ["where", "what", "curious", "wonder", "why", "who", "hmm", "inspect"]):
                detected_emotion = Emotion.CURIOUS
            elif any(w in lower for w in ["sorry", "unfortunately", "could not find", "missing", "lost", "sad"]):
                detected_emotion = Emotion.SAD
            elif any(w in lower for w in ["calculating", "memory", "database", "sqlite", "scan", "searching", "analyzing"]):
                detected_emotion = Emotion.ANALYZING
            elif any(w in lower for w in ["wink", "haha", "hehe", "tease", "joke", "secret"]):
                detected_emotion = Emotion.WINK
            elif any(w in lower for w in ["tired", "sleep", "rest", "night", "power down"]):
                detected_emotion = Emotion.SLEEPY
            elif any(w in lower for w in ["puzzled", "confused", "strange", "odd", "weird"]):
                detected_emotion = Emotion.CONFUSED
            else:
                detected_emotion = Emotion.HAPPY

        sound_map = {
            Emotion.HAPPY: "happy",
            Emotion.EXCITED: "excited",
            Emotion.CURIOUS: "curious",
            Emotion.ALERT: "alert",
            Emotion.SURPRISED: "alert",
            Emotion.SAD: "sad",
            Emotion.LOVE: "love",
            Emotion.WINK: "wink",
            Emotion.ANALYZING: "thinking",
            Emotion.CONFUSED: "confused",
            Emotion.SLEEPY: "shutdown",
            Emotion.OFFLINE: "shutdown",
            Emotion.ANGRY: "angry"
        }
        sound_cue = sound_map.get(detected_emotion, "happy")
        return detected_emotion, text, sound_cue

    def _parse_action_directive(self, user_query: str, raw_text: str) -> Dict[str, Any]:
        """
        Parses action directive from [ACTION: ...] tags or conversational intent heuristics.
        Resolves ambiguous pronouns ('it', 'that') using recent chat history and SQLite items.
        Returns: {"action": str|None, "target": str|None, "cleaned_text": str}
        """
        action = None
        target = None

        # 1. Look for explicit [ACTION: TYPE | target=...] or [ACTION: TYPE] tag in raw_text
        action_match = re.search(r"\[ACTION:\s*([A-Za-z_-]+)(?:\s*\|\s*target=([^\]]+))?\]", raw_text, re.IGNORECASE)
        if action_match:
            action = action_match.group(1).upper()
            if action_match.group(2):
                target = action_match.group(2).strip().title()

        # Clean [ACTION: ...] tags from displayed text
        cleaned_text = re.sub(r"\[ACTION:[^\]]+\]", "", raw_text).strip()

        # 2. Heuristic extraction from user query & context
        lower_q = user_query.lower()

        # Known candidate objects in environment
        candidate_objects = ["keys", "cup", "notebook", "cube", "laptop", "mug", "book", "phone", "wallet"]
        detected_obj = None
        for obj in candidate_objects:
            if obj in lower_q:
                detected_obj = obj.title()
                break

        # Contextual resolution: If no object in current utterance, check recent conversation turns
        if not detected_obj:
            recent_turns = self.db.get_recent_chat(limit=4)
            for turn in recent_turns:
                t_lower = turn.get("message", "").lower()
                for obj in candidate_objects:
                    if obj in t_lower:
                        detected_obj = obj.title()
                        break
                if detected_obj:
                    break

        # Check intent cues
        is_stay = any(p in lower_q for p in [
            "do not move", "don't move", "stay there", "stay still",
            "keep still", "freeze", "stop moving", "halt", "hold position",
            "lock down", "locked down", "stand still", "single millimeter"
        ])
        is_watch = any(p in lower_q for p in [
            "look at", "keep an eye", "keep eye", "watch", "guard", "monitor",
            "stare at", "track", "focus on", "gaze at", "keep eyes"
        ])
        is_companion = any(p in lower_q for p in [
            "companion", "desk companion", "relax", "rest", "calm down",
            "sit with me", "be quiet", "stay with me", "chill"
        ])
        is_release_or_move = any(p in lower_q for p in [
            "not moving", "not at all moving", "why are you not moving", "start moving",
            "resume", "start roaming", "explore", "patrol", "keep moving", "wander",
            "continue roam", "move around", "stretch your treads", "come here", "you can move",
            "move", "walk", "drive", "look around"
        ])

        if not action:
            if is_stay and is_watch:
                action = "STAY_AND_WATCH"
                target = detected_obj or "Keys"
            elif is_watch and detected_obj and not is_release_or_move:
                action = "LOOK_AT"
                target = detected_obj
            elif is_stay:
                action = "HOLD_POSITION"
            elif is_companion:
                action = "DESK"
            elif is_release_or_move:
                action = "ROAM"
            elif any(p in lower_q for p in ["dock", "charge", "go home", "return to base"]):
                action = "DOCK"
        elif action in ("STAY_AND_WATCH", "LOOK_AT") and not target:
            target = detected_obj or "Keys"

        return {
            "action": action,
            "target": target,
            "cleaned_text": cleaned_text
        }

    def _init_client(self) -> None:
        """Initializes the Google GenAI SDK client if API key is provided."""
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print(f"[HybridBrain] Connected to Google Gemini API (Active model: {DEFAULT_GEMINI_MODEL}).")
            except ImportError:
                print("[HybridBrain] 'google-genai' package not installed. Run 'pip install google-genai'.")
            except Exception as e:
                print(f"[HybridBrain] Failed to initialize GenAI client: {e}")
        else:
            print("[HybridBrain] GEMINI_API_KEY not set. Operating via Local Gemma / Offline Core.")

    def is_online(self) -> bool:
        """Checks if cloud Gemini AI is available."""
        return self.client is not None

    def build_prompt_with_memory(self, user_query: str) -> str:
        """Injects SQLite facts and recent roaming history into the active context."""
        memory_context = self.db.generate_system_prompt_context()
        recent_chat = self.db.get_recent_chat(limit=4)

        chat_history_str = ""
        if recent_chat:
            chat_history_str = "\n[RECENT CONVERSATION TURNS]:\n" + "\n".join(
                f"{turn['role'].upper()}: {turn['message']}" for turn in recent_chat
            )

        full_prompt = (
            f"{memory_context}\n"
            f"{chat_history_str}\n\n"
            f"AKHIL SAYS: {user_query}\n"
            f"ALPHA'S SPOKEN RESPONSE:"
        )
        return full_prompt

    def chat_with_emotion(self, user_query: str) -> Dict[str, Any]:
        """
        Processes user query through learning, spatial memory, and AI inference.
        Extracts emotional tone, audio sound cue, and cleans reply text.
        Returns:
            {"reply": str, "emotion": Emotion, "sound_cue": str, "brain_type": str}
        """
        # Save user message to SQLite
        self.db.save_chat_message("user", user_query)

        # 1. Continuous Learning: Automatically extract personal facts from what the user said
        learned_facts = self.learning_engine.extract_and_learn_from_text(user_query)
        for cat, fact in learned_facts:
            print(f"[AutonomousLearning] Learned new fact: [{cat.upper()}] {fact}")

        # 2. Spatial Memory Search: Check if user is asking for the location of an object
        if any(w in user_query.lower() for w in ["where is", "where are", "where did i leave", "find my"]):
            for keyword in ["keys", "wallet", "shoes", "glasses", "cup", "mug", "bag", "phone", "backpack", "laptop", "notebook", "cube", "plant", "pen"]:
                if keyword in user_query.lower():
                    recalled = self.learning_engine.recall_object_location(keyword)
                    if recalled:
                        self.db.save_chat_message("assistant", recalled, brain_type="local_memory")
                        emo = Emotion.EXCITED
                        self.last_emotion = emo
                        self.last_sound_cue = "excited"
                        return {
                            "reply": recalled,
                            "emotion": emo,
                            "sound_cue": "excited",
                            "brain_type": "local_memory",
                            "action": "LOOK_AT",
                            "target": keyword.title()
                        }
                    else:
                        clean_reply = f"*Whirrr-curious?* I haven't discovered your {keyword.title()} on the desk yet! Let me explore and look for them for you, Akhil!"
                        self.db.save_chat_message("assistant", clean_reply, brain_type="local_memory")
                        emo = Emotion.CURIOUS
                        self.last_emotion = emo
                        self.last_sound_cue = "curious"
                        return {
                            "reply": clean_reply,
                            "emotion": emo,
                            "sound_cue": "curious",
                            "brain_type": "local_memory",
                            "action": "ROAM",
                            "target": None
                        }

        prompt = self.build_prompt_with_memory(user_query)
        raw_reply = ""
        brain_type = "gemma_offline"

        # 3. Online Inference (Google Gemini Flash with modern fallback)
        if self.is_online():
            candidate_models = [DEFAULT_GEMINI_MODEL]
            for m in GEMINI_FALLBACK_MODELS:
                if m not in candidate_models:
                    candidate_models.append(m)
            for model_name in candidate_models:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={
                            "system_instruction": BASE_SYSTEM_INSTRUCTION,
                            "temperature": 0.7,
                            "max_output_tokens": 150,
                        }
                    )
                    raw_reply = response.text.strip()
                    brain_type = f"gemini:{model_name}"
                    break
                except Exception as e:
                    print(f"[HybridBrain] Model {model_name} failed: {e}. Trying next...")

            if not raw_reply:
                print("[HybridBrain] All cloud Gemini candidates failed. Falling back to Local Gemma...")

        # 4. Offline Inference (Local Gemma 2B via GGUF or auxiliary core)
        if not raw_reply:
            raw_reply = self.local_gemma.generate(
                prompt=prompt,
                system_instruction=BASE_SYSTEM_INSTRUCTION,
                max_tokens=120
            )
            brain_type = "gemma_offline"

        # Parse physical action directive & clean text
        action_directive = self._parse_action_directive(user_query, raw_reply)
        raw_reply = action_directive["cleaned_text"]

        # Parse emotional state and sound cue
        detected_emotion, clean_reply, sound_cue = self._parse_emotion_and_text(raw_reply)
        self.last_emotion = detected_emotion
        self.last_sound_cue = sound_cue

        # Save assistant message to SQLite
        self.db.save_chat_message("assistant", clean_reply, brain_type=brain_type)

        # Background deep extraction if online
        if self.is_online():
            self._extract_and_learn_facts(user_query, clean_reply)

        return {
            "reply": clean_reply,
            "emotion": detected_emotion,
            "sound_cue": sound_cue,
            "brain_type": brain_type,
            "action": action_directive.get("action"),
            "target": action_directive.get("target")
        }

    def chat(self, user_query: str) -> str:
        """Processes user query and returns reply text string (backward-compatible)."""
        res = self.chat_with_emotion(user_query)
        return res["reply"]

    def analyze_roaming_scene(self, image_bytes: bytes, room_hint: str = "Unknown") -> Dict[str, Any]:
        """
        Takes a snapshot captured while roaming, queries vision to identify objects,
        and saves discovered items into SQLite.
        """
        if not self.is_online():
            # In offline mode, log the exploration event locally
            self.db.log_observation(f"Explored {room_hint} in offline sensor mode.", room_name=room_hint)
            return {"status": "offline", "observation": f"Surveyed {room_hint}."}

        try:
            from google.genai import types

            prompt = (
                "You are the visual cortex of a mobile explorer robot. Look at this photo from your eye camera.\n"
                "1. List any notable everyday objects visible (e.g. keys, mug, laptop, shoes, plant).\n"
                "2. Provide a 1-sentence natural language observation of the room's current state.\n"
                "Output as strict JSON with keys: 'objects' (list of {name, description}), 'observation' (string)."
            )

            response = None
            candidate_models = [DEFAULT_GEMINI_MODEL]
            for m in GEMINI_FALLBACK_MODELS:
                if m not in candidate_models:
                    candidate_models.append(m)
            for model_name in candidate_models:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                            prompt
                        ],
                        config={"response_mime_type": "application/json"}
                    )
                    break
                except Exception as e:
                    print(f"[HybridBrain] Vision model {model_name} failed: {e}. Trying next...")

            if not response:
                raise RuntimeError("All vision model candidates failed.")

            result = json.loads(response.text)

            # Store observation into SQLite
            obs_text = result.get("observation", f"Surveyed {room_hint}.")
            self.db.log_observation(obs_text, room_name=room_hint)

            # Record each discovered object with the Learning Engine (tracks movement!)
            for obj in result.get("objects", []):
                self.learning_engine.learn_object_sighting(
                    object_name=obj.get("name", "Object"),
                    description=obj.get("description", "Spotted while roaming."),
                    room_name=room_hint
                )

            return result
        except Exception as e:
            print(f"[HybridBrain] Scene analysis failed: {e}")
            return {"status": "error", "error": str(e)}

    def _extract_and_learn_facts(self, user_msg: str, bot_reply: str) -> None:
        """Deep LLM-assisted background extractor for nuanced facts."""
        if not self.is_online():
            return

        try:
            prompt = (
                f"Extract any personal facts, preferences, habits, or current projects shared by the user in this turn.\n"
                f"User: '{user_msg}'\n"
                f"If a fact exists, output JSON: {{'has_fact': true, 'category': 'preference|project|habit|family', 'fact': '...'}}.\n"
                f"If no personal fact was shared, output: {{'has_fact': false}}."
            )
            candidate_models = [DEFAULT_GEMINI_MODEL]
            for m in GEMINI_FALLBACK_MODELS:
                if m not in candidate_models:
                    candidate_models.append(m)
            for model_name in candidate_models:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
                    )
                    data = json.loads(response.text)
                    if data.get("has_fact") and "fact" in data:
                        self.db.learn_fact(data.get("category", "general"), data["fact"])
                    break
                except Exception:
                    continue
        except Exception:
            pass

# Alias for backward compatibility
GeminiBrain = HybridBrain
