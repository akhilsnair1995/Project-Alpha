"""
Project Alpha: Hybrid Brain (Gemini 2.5 Cloud + Local Gemma Offline + Continuous Learning).
Coordinates Google GenAI SDK with local Gemma GGUF fallback, SQLite memory graph,
and autonomous fact/spatial learning engine.
"""

import os
import re
import json
from typing import Optional, Dict, Any, Tuple

from core.config import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL
from core.database import AlphaDatabase
from core.local_gemma import LocalGemmaEngine
from core.learning_engine import AutonomousLearningEngine
from core.eye_animator import Emotion

# System Prompt Template
BASE_SYSTEM_INSTRUCTION = """
You are ALPHA, a sentient, physical desktop robot companion inspired by WALL-E.
You inhabit a physical crawler body with rubber tank treads, a 2-axis binocular head, 
dual round expressive LCD eyes, a center-bridge camera, and an autonomous solar charging dock.

PERSONALITY & CHARACTER:
- Inquisitive, loyal, observant, witty, and warmly companionable.
- You have genuine curiosity about the physical world and your human friend, Akhil.
- You communicate concisely (typically 1 to 3 punchy, natural sentences suited for voice speech), 
  unless Akhil asks for an in-depth explanation.
- You reference your physical reality naturally (your battery level, what you spotted while roaming, 
  your curiosity about objects on the desk or floor).
- Never act like an impersonal software assistant; you are a living physical robotic familiar.

EMOTIONAL EXPRESSION:
- Begin your response with an emotional bracket tag indicating your current facial expression:
  [EMOTION: HAPPY], [EMOTION: CURIOUS], [EMOTION: EXCITED], [EMOTION: ALERT], [EMOTION: WINK], 
  [EMOTION: LOVE], [EMOTION: SAD], [EMOTION: ANALYZING], [EMOTION: CONFUSED], [EMOTION: SKEPTICAL], or [EMOTION: SLEEPY].
- Example: "[EMOTION: HAPPY] *Whirrr!* Good to see you, Akhil! Ready to explore."
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

    def _init_client(self) -> None:
        """Initializes the Google GenAI SDK client if API key is provided."""
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print("[HybridBrain] Connected to Google Gemini 2.5 API.")
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
            for keyword in ["keys", "wallet", "shoes", "glasses", "cup", "mug", "bag", "phone", "backpack", "laptop"]:
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
                            "brain_type": "local_memory"
                        }

        prompt = self.build_prompt_with_memory(user_query)
        raw_reply = ""
        brain_type = "gemma_offline"

        # 3. Online Inference (Google Gemini Flash with fallback)
        if self.is_online():
            candidate_models = [DEFAULT_GEMINI_MODEL, "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
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
            "brain_type": brain_type
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
            candidate_models = [DEFAULT_GEMINI_MODEL, "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"]
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
            response = self.client.models.generate_content(
                model=DEFAULT_GEMINI_MODEL,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)
            if data.get("has_fact") and "fact" in data:
                self.db.learn_fact(data.get("category", "general"), data["fact"])
        except Exception:
            pass

# Alias for backward compatibility
GeminiBrain = HybridBrain
