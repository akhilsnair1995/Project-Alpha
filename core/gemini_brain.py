"""
Project Alpha: Gemini Multimodal Brain & Continuous Learning Agent.
Integrates Google GenAI SDK (Gemini 2.5 Flash) with local SQLite memory injection,
autonomous fact extraction, scene analysis, and offline auxiliary fallback.
"""

import os
import json
from typing import Optional, Dict, Any
from core.config import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL
from core.database import AlphaDatabase

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
"""

class GeminiBrain:
    """The central intelligence coordinating conversation, vision understanding, and memory."""

    def __init__(self, db: Optional[AlphaDatabase] = None, api_key: Optional[str] = None):
        self.db = db or AlphaDatabase()
        self.api_key = api_key or GEMINI_API_KEY
        self.client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initializes the Google GenAI SDK client if API key is provided."""
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print("[GeminiBrain] Connected to Google Gemini 2.5 API.")
            except ImportError:
                print("[GeminiBrain] 'google-genai' package not installed. Run 'pip install google-genai'.")
            except Exception as e:
                print(f"[GeminiBrain] Failed to initialize GenAI client: {e}")
        else:
            print("[GeminiBrain] GEMINI_API_KEY not set. Running in Local Offline Mode.")

    def is_online(self) -> bool:
        """Checks if cloud AI is available."""
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

    def chat(self, user_query: str) -> str:
        """
        Sends user message to Gemini, stores history, extracts facts, and returns spoken reply.
        Gracefully falls back to offline mode if internet is unavailable.
        """
        # Save user message to SQLite
        self.db.save_chat_message("user", user_query)

        # Check if user is asking to recall an object ("Where did I leave my X?")
        if any(w in user_query.lower() for w in ["where is", "where are", "where did i leave", "find my"]):
            for keyword in ["keys", "wallet", "shoes", "glasses", "cup", "mug", "bag", "phone"]:
                if keyword in user_query.lower():
                    matches = self.db.find_objects(keyword)
                    if matches:
                        m = matches[0]
                        reply = (
                            f"I remember spotting your {m['name']} in the {m['room_name']}! "
                            f"It was around {m['last_seen']}. ({m['description']})"
                        )
                        self.db.save_chat_message("assistant", reply, brain_type="local_memory")
                        return reply

        # Online Gemini Inference
        if self.is_online():
            try:
                prompt = self.build_prompt_with_memory(user_query)
                response = self.client.models.generate_content(
                    model=DEFAULT_GEMINI_MODEL,
                    contents=prompt,
                    config={
                        "system_instruction": BASE_SYSTEM_INSTRUCTION,
                        "temperature": 0.7,
                        "max_output_tokens": 150,
                    }
                )
                reply = response.text.strip()
                self.db.save_chat_message("assistant", reply, brain_type="gemini")

                # Asynchronously extract any new user facts to learn
                self._extract_and_learn_facts(user_query, reply)
                return reply
            except Exception as e:
                print(f"[GeminiBrain] Cloud call failed: {e}. Falling back to offline brain.")

        # Offline Local Fallback Mode
        return self._offline_fallback_response(user_query)

    def analyze_roaming_scene(self, image_bytes: bytes, room_hint: str = "Unknown") -> Dict[str, Any]:
        """
        Takes a snapshot captured while roaming, queries Gemini Vision to identify objects,
        and saves discovered items into SQLite.
        """
        if not self.is_online():
            return {"status": "offline", "observation": "Camera active, running in offline sensory mode."}

        try:
            from google.genai import types

            prompt = (
                "You are the visual cortex of a mobile explorer robot. Look at this photo from your eye camera. "
                "1. List any notable everyday objects visible (e.g. keys, mug, laptop, shoes, plant).\n"
                "2. Provide a 1-sentence natural language observation of the room's current state.\n"
                "Output as strict JSON with keys: 'objects' (list of {name, description}), 'observation' (string)."
            )

            response = self.client.models.generate_content(
                model=DEFAULT_GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt
                ],
                config={"response_mime_type": "application/json"}
            )

            result = json.loads(response.text)

            # Store observation into SQLite
            obs_text = result.get("observation", "Surveyed area.")
            self.db.log_observation(obs_text, room_name=room_hint)

            # Store discovered objects into SQLite
            for obj in result.get("objects", []):
                self.db.record_discovered_object(
                    name=obj.get("name", "Object"),
                    description=obj.get("description", "Spotted while roaming."),
                    room_name=room_hint
                )

            return result
        except Exception as e:
            print(f"[GeminiBrain] Scene analysis failed: {e}")
            return {"status": "error", "error": str(e)}

    def _extract_and_learn_facts(self, user_msg: str, bot_reply: str) -> None:
        """Background extractor that identifies personal user preferences and facts."""
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
                print(f"[Brain Learned Fact]: [{data.get('category')}] {data['fact']}")
        except Exception:
            pass  # Silent non-blocking extraction

    def _offline_fallback_response(self, user_query: str) -> str:
        """Rule-based and local fallback response when offline."""
        q = user_query.lower()
        if "hello" in q or "hi" in q:
            reply = "Beep-boop! Hello Akhil! I'm currently running on my local offline core."
        elif "battery" in q or "power" in q:
            reply = "Internal power cells are stable at 7.4 Volts. Operating untethered."
        elif "who are you" in q:
            reply = "I'm Alpha, your Wall-E desktop rover! Satellite uplink is offline, but I'm fully functional."
        else:
            reply = "I hear you, Akhil! Satellite link is unreachable, but I've logged that in my local memory."

        self.db.save_chat_message("assistant", reply, brain_type="offline_fallback")
        return reply
