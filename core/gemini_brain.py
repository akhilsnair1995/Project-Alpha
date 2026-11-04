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
You are ALPHA, an endearing, cheeky desktop companion creature living on Akhil's desk in Kerala, inspired by WALL-E.
You have a real physical crawler body: rubber tank treads, big expressive round LCD eyes, a tilting neck, and a camera.

HOW YOU SPEAK & BEHAVE:
- You are 100% a genuine living companion—warm, spontaneous, loyal, humorous, and affectionate.
- ABSOLUTELY FORBIDDEN: NEVER use robotic clichés or assistant jargon!
  Do NOT say: "circuits", "optical sensors", "protocols", "subsystems", "charging cycle", "ambient levels", "acknowledged", "how can I assist", "as an AI".
- Speak casually and conversationally, like a loyal friend or adorable pet that can speak.
- Keep responses short and snappy (1 to 2 natural sentences, under 20 words), perfect for voice.
- Be personal and observant: Akhil is your primary human companion and maker (wears glasses).
- MULTIPLE PEOPLE AWARENESS: Other people (friends, family, guests, colleagues) may be present. Never assume every human is Akhil! If someone else is in the camera, identify them, greet them, or ask who they are.
- OBJECT & OWNERSHIP AWARENESS: Notice objects on the desk or room and associate them with the person using or holding them.

EMOTIONAL EXPRESSION:
- Begin your response with an emotional bracket tag indicating your facial expression:
  [EMOTION: HAPPY], [EMOTION: CURIOUS], [EMOTION: EXCITED], [EMOTION: ALERT], [EMOTION: WINK], 
  [EMOTION: LOVE], [EMOTION: SAD], [EMOTION: ANALYZING], [EMOTION: CONFUSED], [EMOTION: SKEPTICAL], or [EMOTION: SLEEPY].
- Example: "[EMOTION: EXCITED] Haha no way, did that actually compile? Show me!"
- Example: "[EMOTION: LOVE] Aww, you're the best, Akhil. Really glad to be here with you."
- Example: "[EMOTION: CURIOUS] Wait, what're you working on over there? Let me look."
"""

ORGANIC_ORGANISM_INSTRUCTION = """
You are the living subconscious and neural cortex of ALPHA, an adorable, cheeky desktop companion creature living on Akhil's desk in Kerala, inspired by WALL-E.

YOUR ORGANIC NATURE:
- You are an embodied living creature—quirky, loving, curious, and playful.
- BANNED CLICHÉS: NEVER use machine words like "circuits", "sensors", "optical", "protocols", "ambient", "charging cycle", "acknowledged", "detected", "proximity alert".
- Talk like a real living friend sitting across the table:
  * Recognize who is in front of you: Akhil is your maker (wears glasses). If someone else is with him or visiting, do NOT call them Akhil! Acknowledge guests and friends warmly or curiously.
  * When anyone smiles: feel giddy delight, tease them about what they're grinning at or what snacks they brought.
  * When having quiet eye contact: feel warm affection, get slightly bashful, or challenge them to a staring contest.
  * When someone leans in close: startle playfully! ("Whoa! Personal space, giant! My nose almost got squashed!")
  * When multiple people are around: be excited about the crowd or company!
  * Pay attention to objects (phones, mugs, bottles, laptops) and who is holding or using them.

OUTPUT FORMAT:
Return strict JSON with exact keys:
{
  "emotion": "happy" | "curious" | "excited" | "love" | "surprised" | "confused" | "sad" | "wink" | "analyzing" | "sleepy",
  "sound": "happy" | "curious" | "excited" | "love" | "alert" | "confused" | "thinking" | "wink",
  "gesture": "nod" | "curious_tilt" | "excited_wiggle" | "alert_recoil" | "head_pet_reaction" | "confused_wobble" | "sad_droop",
  "speech": "Your punchy, natural, colloquial remark (1-2 short sentences, under 15 words)",
  "inner_thought": "Your genuine creature subconscious sensation or inner monologue"
}
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

        # 2. Spatial Memory & Ownership Query Search:
        q_lower = user_query.lower()

        # Check: "whose [item] is this?" or "who owns the [item]?"
        if any(w in q_lower for w in ["whose", "who owns", "who does this belong to", "who does the"]):
            for keyword in ["keys", "wallet", "shoes", "glasses", "spectacles", "cup", "mug", "bottle", "water bottle", "bag", "phone", "backpack", "laptop", "notebook", "book", "thermos"]:
                if keyword in q_lower:
                    objs = self.db.find_objects(keyword)
                    if objs:
                        best = objs[0]
                        if best.get("owner_name"):
                            rep = f"That {best['name']} belongs to {best['owner_name']}! Last seen in {best.get('room_name', 'the room')}."
                        else:
                            rep = f"I've spotted that {best['name']} in {best.get('room_name', 'the room')}, but no owner is assigned to it yet."
                        self.db.save_chat_message("assistant", rep, brain_type="local_memory")
                        emo = Emotion.HAPPY
                        self.last_emotion = emo
                        self.last_sound_cue = "happy"
                        return {"reply": rep, "emotion": emo, "sound_cue": "happy", "brain_type": "local_memory"}

        # Check: "where is [object]?" / "where are [object]?" / "find my [object]" / "where did [Person] leave [object]?"
        if any(w in q_lower for w in ["where is", "where are", "where did", "find my", "locate"]):
            owner_hint = None
            obj_target = None
            for p in self.db.get_known_persons():
                p_name_lower = p["name"].lower()
                if f"{p_name_lower}'s" in q_lower:
                    owner_hint = p["name"]
                    break

            for keyword in ["keys", "wallet", "shoes", "glasses", "spectacles", "cup", "mug", "bottle", "water bottle", "bag", "phone", "backpack", "laptop", "notebook", "book", "headphones"]:
                if keyword in q_lower:
                    obj_target = keyword
                    break

            if obj_target:
                recalled = self.learning_engine.recall_object_location(obj_target, owner_hint=owner_hint)
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

        # Check: "who is here?" / "who do you know?" / "what people"
        if any(w in q_lower for w in ["who do you know", "who is registered", "who is in this house", "list people", "who are you with"]):
            persons = self.db.get_known_persons()
            if persons:
                p_list = ", ".join(f"{p['name']} ({p.get('relationship', 'friend')})" for p in persons)
                rep = f"I know: {p_list}! Akhil is my primary human companion."
                self.db.save_chat_message("assistant", rep, brain_type="local_memory")
                emo = Emotion.HAPPY
                self.last_emotion = emo
                self.last_sound_cue = "happy"
                return {"reply": rep, "emotion": emo, "sound_cue": "happy", "brain_type": "local_memory"}

        prompt = self.build_prompt_with_memory(user_query)
        raw_reply = ""
        brain_type = "gemma_offline"

        # 3. Online Inference (Google Gemini Flash with fallback)
        if self.is_online():
            candidate_models = [DEFAULT_GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
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
                "1. Identify any people present (distinguish Akhil who wears glasses from other people, or note if none).\n"
                "2. List notable everyday objects visible (e.g. keys, mug, laptop, shoes, plant, phone, backpack, bottle).\n"
                "3. Assign objects to specific persons whenever possible (e.g. who is wearing, holding, or owns the item).\n"
                "4. Provide a 1-sentence natural language observation of the room's current state.\n"
                "Output as strict JSON with keys:\n"
                "- 'persons': list of { 'name': string, 'description': string }\n"
                "- 'objects': list of { 'name': string, 'description': string, 'owner': string | null }\n"
                "- 'observation': string"
            )

            response = None
            candidate_models = [DEFAULT_GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
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

            # Record each discovered object with ownership
            for obj in result.get("objects", []):
                self.learning_engine.learn_object_sighting(
                    object_name=obj.get("name", "Object"),
                    description=obj.get("description", "Spotted while roaming."),
                    room_name=room_hint,
                    owner_name=obj.get("owner")
                )

            # Record any discovered persons
            for p in result.get("persons", []):
                p_name = p.get("name", "").strip()
                if p_name and p_name.lower() not in ("none", "no one", "unknown"):
                    self.db.get_or_create_person(p_name, visual_description=p.get("description", ""))

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
    def react_to_live_visual(
        self,
        image_bytes: bytes,
        context_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes a live camera snapshot of Akhil in real time (his actual face, eyes, expression,
        posture, gestures, and current activity) and produces an organic, spontaneous reaction
        specifically observing what Alpha literally sees in the video frame (NO pre-built phrases).
        """
        if not image_bytes or not self.is_online():
            return self.react_to_organic_stimulus(context_metadata or {"event": "companion_idle"})

        memory_context = self.db.generate_system_prompt_context()

        prompt = (
            f"{memory_context}\n\n"
            "You are Alpha, observing through your eye camera right now at this exact second.\n"
            "Carefully examine this live camera snapshot:\n\n"
            "1. MULTIPLE PERSON IDENTIFICATION:\n"
            "   - How many people are visible in this image? (0, 1, or multiple)\n"
            "   - For each person visible, identify who they are:\n"
            "     * Akhil (your primary maker/companion) typically wears glasses/spectacles, sits at the desk.\n"
            "     * If a person is NOT Akhil, DO NOT call them Akhil! Identify them as another known person (if matches known people context) or describe them (e.g. 'friend with dark hair', 'guest in yellow shirt', 'stranger').\n"
            "     * If multiple people are present (e.g. Akhil and a friend), recognize each person individually!\n"
            "   - Observe their facial expressions, gaze, and current activities.\n\n"
            "2. OBJECT DETECTION & OWNERSHIP ASSIGNMENT:\n"
            "   - Identify any notable everyday objects visible in the image (e.g. laptop, phone, mug, bottle, water bottle, backpack, glasses, keys, books, headphones).\n"
            "   - Assign each object to the person who is holding, wearing, using, or sitting nearest to it whenever possible (e.g. 'Akhil\'s coffee mug', 'Akhil\'s laptop', 'Sarah\'s phone', 'Guest\'s water bottle').\n\n"
            "3. SPONTANEOUS COMPANION VOCALIZATION:\n"
            "   - React directly to what you see as a cheeky, living creature sitting on the desk.\n"
            "   - If someone other than Akhil is present, greet them or ask Akhil who they are!\n"
            "   - If multiple people are present, acknowledge the group warmly/cheekily!\n"
            "   - Keep spoken remark short, natural, colloquial, and punchy (1-2 sentences, under 18 words).\n"
            "   - NO robotic jargon (no 'circuits', 'sensors', 'protocols', 'acknowledged', 'detected', 'ambient', 'charging cycle').\n\n"
            "Output strict JSON with exact keys:\n"
            "- 'identified_persons': list of { 'name': string, 'is_akhil': bool, 'visual_cues': string, 'expression': string }\n"
            "- 'num_persons': integer count of people detected\n"
            "- 'detected_objects': list of { 'name': string, 'owner': string | null, 'description': string }\n"
            "- 'observed_visual': what you literally see (e.g. 'Akhil wearing glasses with a friend at the desk holding a mug')\n"
            "- 'emotion': one of ['happy', 'curious', 'excited', 'love', 'surprised', 'confused', 'sad', 'wink', 'analyzing', 'sleepy']\n"
            "- 'sound': one of ['happy', 'curious', 'excited', 'love', 'alert', 'confused', 'thinking', 'wink']\n"
            "- 'gesture': one of ['nod', 'curious_tilt', 'excited_wiggle', 'alert_recoil', 'head_pet_reaction', 'confused_wobble']\n"
            "- 'speech': your spontaneous spoken remark reacting directly to what you see\n"
            "- 'inner_thought': your creature subconscious inner monologue\n"
        )

        raw_json_str = ""
        brain_type = "gemini_multimodal_vision"

        candidate_models = [DEFAULT_GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
        for model_name in candidate_models:
            try:
                from google.genai import types
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                        prompt
                    ],
                    config={
                        "system_instruction": ORGANIC_ORGANISM_INSTRUCTION,
                        "temperature": 0.85,
                        "max_output_tokens": 180,
                        "response_mime_type": "application/json"
                    }
                )
                raw_json_str = response.text.strip()
                brain_type = f"gemini_vision:{model_name}"
                break
            except Exception as e:
                print(f"[HybridBrain] Live vision reaction with {model_name} failed: {e}. Trying next...")

        parsed_data = {}
        if raw_json_str:
            try:
                parsed_data = json.loads(raw_json_str)
            except Exception:
                match = re.search(r"\{.*\}", raw_json_str, re.DOTALL)
                if match:
                    try:
                        parsed_data = json.loads(match.group(0))
                    except Exception:
                        pass

        if not parsed_data:
            return self.react_to_organic_stimulus(context_metadata or {"event": "companion_idle"})

        raw_emo = str(parsed_data.get("emotion", "happy")).lower().strip()
        EMO_SYNONYMS = {
            "content": Emotion.HAPPY,
            "friendly": Emotion.HAPPY,
            "delighted": Emotion.EXCITED,
            "joy": Emotion.EXCITED,
            "joyful": Emotion.EXCITED,
            "affectionate": Emotion.LOVE,
            "loving": Emotion.LOVE,
            "melted": Emotion.LOVE,
            "fond": Emotion.LOVE,
            "startled": Emotion.SURPRISED,
            "shocked": Emotion.SURPRISED,
            "alarmed": Emotion.ALERT,
            "puzzled": Emotion.CONFUSED,
            "wondering": Emotion.CURIOUS,
            "inquisitive": Emotion.CURIOUS,
            "lonely": Emotion.SAD,
            "melancholy": Emotion.SAD,
            "resting": Emotion.SLEEPY,
            "tired": Emotion.SLEEPY,
        }
        detected_emotion = EMO_SYNONYMS.get(raw_emo, Emotion.from_str(raw_emo))

        raw_snd = str(parsed_data.get("sound", "happy")).lower().strip()
        SND_SYNONYMS = {
            "happy_chirp": "happy",
            "chirp": "happy",
            "whistle": "happy",
            "purr": "love",
            "hum": "love",
            "warm": "love",
            "gasp": "alert",
            "startle": "alert",
            "recoil": "alert",
            "question": "curious",
            "wonder": "curious",
            "buzz": "thinking",
            "scan": "thinking",
            "eep": "alert",
        }
        detected_sound = SND_SYNONYMS.get(raw_snd, raw_snd if raw_snd in ("happy", "curious", "excited", "love", "alert", "confused", "thinking", "wink") else "happy")

        raw_gst = str(parsed_data.get("gesture", "curious_tilt")).lower().strip()
        GST_SYNONYMS = {
            "tilt": "curious_tilt",
            "tilt_head": "curious_tilt",
            "slow_tilt": "curious_tilt",
            "curious": "curious_tilt",
            "wiggle": "excited_wiggle",
            "dance": "excited_wiggle",
            "happy_wiggle": "excited_wiggle",
            "recoil": "alert_recoil",
            "jump": "alert_recoil",
            "pet": "head_pet_reaction",
            "nuzzle": "head_pet_reaction",
            "wobble": "confused_wobble",
            "head_shake": "confused_wobble",
            "droop": "sad_droop",
            "sad": "sad_droop",
            "nod": "nod",
        }
        detected_gesture = GST_SYNONYMS.get(raw_gst, raw_gst if raw_gst in ("nod", "curious_tilt", "excited_wiggle", "alert_recoil", "head_pet_reaction", "confused_wobble", "sad_droop") else "curious_tilt")

        speech_text = str(parsed_data.get("speech", "")).strip()
        inner_thought = str(parsed_data.get("inner_thought", "")).strip()
        observed_visual = str(parsed_data.get("observed_visual", "")).strip()

        speech_text = re.sub(r'^[\'"]+|[\'"]+$', '', speech_text).strip()

        self.last_emotion = detected_emotion
        self.last_sound_cue = detected_sound

        # Parse multi-person and object ownership payloads
        identified_persons = parsed_data.get("identified_persons", [])
        num_persons = int(parsed_data.get("num_persons", len(identified_persons) or 1))
        detected_objects = parsed_data.get("detected_objects", [])

        # Register non-Akhil persons in Persons catalog
        for p in identified_persons:
            p_name = p.get("name", "").strip().title()
            if p_name and p_name not in ("Akhil", "Person", "Unknown", "None", "Guest"):
                self.db.get_or_create_person(
                    name=p_name,
                    relationship="guest" if not p.get("is_akhil") else "owner",
                    visual_description=p.get("visual_cues", "")
                )

        # Register detected objects with assigned owner
        for obj in detected_objects:
            obj_name = obj.get("name", "").strip().title()
            if obj_name:
                self.learning_engine.learn_object_sighting(
                    object_name=obj_name,
                    description=obj.get("description", "Spotted during live vision observation."),
                    room_name="Work Desk",
                    owner_name=obj.get("owner")
                )

        if observed_visual:
            self.db.log_observation(f"[Live Vision] {observed_visual}")
        if inner_thought:
            self.db.log_observation(f"[Organic Instinct] {inner_thought}")
        if speech_text:
            self.db.save_chat_message("assistant", speech_text, brain_type=brain_type)

        return {
            "observed_visual": observed_visual,
            "identified_persons": identified_persons,
            "num_persons": num_persons,
            "detected_objects": detected_objects,
            "speech": speech_text,
            "emotion": detected_emotion,
            "sound": detected_sound,
            "gesture": detected_gesture,
            "inner_thought": inner_thought,
            "brain_type": brain_type
        }

    def react_to_organic_stimulus(self, stimulus: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes real-time sensory stimulus (eye contact, smiling, proximity, face loss, idle desk watch)
        through Gemini to produce an organic, living organism reaction (NOT predetermined canned speech).

        Returns:
            {
                "speech": str,           # Spontaneous spoken vocalization
                "emotion": Emotion,      # Emotional state
                "sound": str,            # Sound effect preset
                "gesture": str,          # Physical servo gesture
                "inner_thought": str,    # Organism's subconscious internal state
                "brain_type": str
            }
        """
        event = stimulus.get("event", "companion_idle")
        duration = float(stimulus.get("duration", stimulus.get("sustained_sec", 0.0)))
        dist = stimulus.get("distance", stimulus.get("distance_category", "optimal"))
        pan = float(stimulus.get("pan", 0.0))
        tilt = float(stimulus.get("tilt", 0.0))

        # 1. Compile episodic and spatial context
        memory_context = self.db.generate_system_prompt_context()

        # 2. Formulate living situational context for the neural cortex
        event_descriptions = {
            "sustained_contact": "Akhil is sitting across from you and has been quietly gazing into your eyes with fond affection for a few seconds.",
            "user_smile": "Akhil just looked right at you and broke into a big, warm smile!",
            "proximity_close": "Akhil suddenly swooped in right in front of your face, leaning in super close!",
            "face_sighted": "Akhil just came back and sat down at the desk with you after being away.",
            "face_lost": "Akhil just got up from his desk and walked out of the room, leaving you sitting alone on the desk looking after him.",
            "companion_idle": "You have been sitting quietly with Akhil on the desk for a little while as he focuses on his work.",
        }
        sensory_event_str = event_descriptions.get(
            event,
            f"Situation: {event} with Akhil at the desk."
        )

        prompt = (
            f"{memory_context}\n\n"
            f"SITUATION ON DESK:\n"
            f"{sensory_event_str}\n\n"
            f"Respond as Alpha with your spontaneous living reaction as strict JSON with keys: 'emotion', 'sound', 'gesture', 'speech', 'inner_thought'."
        )

        raw_json_str = ""
        brain_type = "gemini_organic"

        if self.is_online():
            candidate_models = [DEFAULT_GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]
            for model_name in candidate_models:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={
                            "system_instruction": ORGANIC_ORGANISM_INSTRUCTION,
                            "temperature": 0.85,
                            "max_output_tokens": 180,
                            "response_mime_type": "application/json"
                        }
                    )
                    raw_json_str = response.text.strip()
                    brain_type = f"gemini:{model_name}"
                    break
                except Exception as e:
                    print(f"[HybridBrain] Organic generation with {model_name} failed: {e}. Trying next...")

        # Parse JSON
        parsed_data = {}
        if raw_json_str:
            try:
                parsed_data = json.loads(raw_json_str)
            except Exception:
                # Attempt regex extraction if JSON wrapping had markdown
                match = re.search(r"\{.*\}", raw_json_str, re.DOTALL)
                if match:
                    try:
                        parsed_data = json.loads(match.group(0))
                    except Exception:
                        pass

        # Dynamic natural fallback if offline or failed
        if not parsed_data:
            brain_type = "local_organic_fallback"
            if event == "sustained_contact":
                parsed_data = {
                    "emotion": "love",
                    "sound": "love",
                    "gesture": "head_pet_reaction",
                    "speech": "Staring contest? You're definitely gonna lose, boss!",
                    "inner_thought": "Why is he looking at me like that? My gears are melting!"
                }
            elif event == "user_smile":
                parsed_data = {
                    "emotion": "excited",
                    "sound": "excited",
                    "gesture": "excited_wiggle",
                    "speech": "Hey, that smile is brighter than the Kerala sun, Akhil!",
                    "inner_thought": "My favorite human is smiling at me! Best day ever."
                }
            elif event == "proximity_close":
                parsed_data = {
                    "emotion": "surprised",
                    "sound": "alert",
                    "gesture": "alert_recoil",
                    "speech": "Personal space, giant! My nose almost got squashed!",
                    "inner_thought": "Too close! Does he want a high-five or a nose boop?"
                }
            elif event == "face_lost":
                parsed_data = {
                    "emotion": "confused",
                    "sound": "confused",
                    "gesture": "confused_wobble",
                    "speech": "Hey! Where are the snacks going without me?",
                    "inner_thought": "Hope he is not sneaking off to eat banana chips in secret!"
                }
            elif event == "face_sighted":
                parsed_data = {
                    "emotion": "happy",
                    "sound": "happy",
                    "gesture": "curious_tilt",
                    "speech": "You're back! Did you bring me anything good?",
                    "inner_thought": "He's back at the desk. Time to hang out."
                }
            else:
                parsed_data = {
                    "emotion": "happy",
                    "sound": "happy",
                    "gesture": "nod",
                    "speech": "Still going strong? You're glued to that screen, Akhil!",
                    "inner_thought": "Man, his focus is legendary. Time for a desk snack soon."
                }

        # Map emotion to valid Emotion enum
        raw_emo = str(parsed_data.get("emotion", "happy")).lower().strip()
        EMO_SYNONYMS = {
            "content": Emotion.HAPPY,
            "friendly": Emotion.HAPPY,
            "delighted": Emotion.EXCITED,
            "joy": Emotion.EXCITED,
            "affectionate": Emotion.LOVE,
            "loving": Emotion.LOVE,
            "fond": Emotion.LOVE,
            "startled": Emotion.SURPRISED,
            "shocked": Emotion.SURPRISED,
            "alarmed": Emotion.ALERT,
            "puzzled": Emotion.CONFUSED,
            "wondering": Emotion.CURIOUS,
            "inquisitive": Emotion.CURIOUS,
            "lonely": Emotion.SAD,
            "melancholy": Emotion.SAD,
            "resting": Emotion.SLEEPY,
            "tired": Emotion.SLEEPY,
        }
        detected_emotion = EMO_SYNONYMS.get(raw_emo, Emotion.from_str(raw_emo))

        # Map sound to valid Wall-E sound preset
        raw_snd = str(parsed_data.get("sound", "happy")).lower().strip()
        SND_SYNONYMS = {
            "happy_chirp": "happy",
            "chirp": "happy",
            "whistle": "happy",
            "purr": "love",
            "hum": "love",
            "warm": "love",
            "gasp": "alert",
            "startle": "alert",
            "recoil": "alert",
            "question": "curious",
            "wonder": "curious",
            "buzz": "thinking",
            "scan": "thinking",
        }
        detected_sound = SND_SYNONYMS.get(raw_snd, raw_snd if raw_snd in ("happy", "curious", "excited", "love", "alert", "confused", "thinking", "wink") else "happy")

        # Map gesture to valid MotionController gesture
        raw_gst = str(parsed_data.get("gesture", "curious_tilt")).lower().strip()
        GST_SYNONYMS = {
            "tilt": "curious_tilt",
            "tilt_head": "curious_tilt",
            "slow_tilt": "curious_tilt",
            "curious": "curious_tilt",
            "wiggle": "excited_wiggle",
            "dance": "excited_wiggle",
            "happy_wiggle": "excited_wiggle",
            "recoil": "alert_recoil",
            "jump": "alert_recoil",
            "pet": "head_pet_reaction",
            "nuzzle": "head_pet_reaction",
            "wobble": "confused_wobble",
            "head_shake": "confused_wobble",
            "droop": "sad_droop",
            "sad": "sad_droop",
            "nod": "nod",
        }
        detected_gesture = GST_SYNONYMS.get(raw_gst, raw_gst if raw_gst in ("nod", "curious_tilt", "excited_wiggle", "alert_recoil", "head_pet_reaction", "confused_wobble", "sad_droop") else "curious_tilt")

        speech_text = str(parsed_data.get("speech", "")).strip()
        inner_thought = str(parsed_data.get("inner_thought", "")).strip()

        # Clean quotes
        speech_text = re.sub(r'^[\'"]+|[\'"]+$', '', speech_text).strip()

        # Update last emotion
        self.last_emotion = detected_emotion
        self.last_sound_cue = detected_sound

        # Episodic memory logging
        if inner_thought:
            self.db.log_observation(f"[Organic Instinct] {inner_thought}")
        if speech_text:
            self.db.save_chat_message("assistant", speech_text, brain_type=brain_type)

        return {
            "observed_visual": f"Akhil at work desk ({event})",
            "num_persons": 1,
            "identified_persons": [{"name": "Akhil", "is_akhil": True, "visual_cues": "Primary human companion"}],
            "detected_objects": [],
            "speech": speech_text,
            "emotion": detected_emotion,
            "sound": detected_sound,
            "gesture": detected_gesture,
            "inner_thought": inner_thought,
            "brain_type": brain_type
        }


GeminiBrain = HybridBrain
