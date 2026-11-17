"""
Project Alpha: Autonomous Learning Engine.
Processes sensory streams, extracts personal facts and relationships from conversation,
tracks spatial object movement across rooms, and manages person-object ownership associations.
"""

import re
import datetime
from typing import Dict, List, Optional, Any, Tuple
from core.database import AlphaDatabase

class AutonomousLearningEngine:
    """Manages continuous spatial, episodic, person, and object-ownership learning."""

    def __init__(self, db: Optional[AlphaDatabase] = None):
        self.db = db or AlphaDatabase()

        # Regex patterns for fast on-device fact extraction (zero LLM latency needed)
        self.fact_patterns = [
            (r"(?:i like|i love|my favorite\s+(\w+)\s+is)\s+([^.!?]+)", "preference"),
            (r"(?:i am working on|i'm building|my project is)\s+([^.!?]+)", "project"),
            (r"(?:i live in|i am from|i'm located in)\s+([^.!?]+)", "location"),
            (r"(?:my name is|i am called)\s+([^.!?]+)", "identity"),
            (r"(?:i usually|every morning i|every night i)\s+([^.!?]+)", "habit"),
            (r"(?:don't like|i hate|i dislike)\s+([^.!?]+)", "dislike"),
        ]

        # Ownership & Person Introduction Patterns
        self.ownership_patterns = [
            # "this is Akhil's laptop" or "that is Sarah's bottle"
            r"(?:this is|that is|these are|it's|it is)\s+([a-zA-Z]+)'s\s+([a-zA-Z0-9\s]+)",
            # "Akhil owns the laptop"
            r"([a-zA-Z]+)\s+owns\s+(?:the\s+)?([a-zA-Z0-9\s]+)",
            # "the laptop belongs to Akhil"
            r"(?:the\s+)?([a-zA-Z0-9\s]+)\s+belongs to\s+([a-zA-Z]+)",
        ]

    # =========================================================================
    # 1. Personal Fact & Relationship Learning (Conversation-Driven)
    # =========================================================================

    def extract_and_learn_from_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Parses user text with heuristic patterns to extract personal facts,
        new persons, and object ownership, saving them directly into SQLite.
        Returns list of (category, fact) learned.
        """
        learned = []
        lower_text = text.lower().strip()

        # Check standard fact patterns
        for pattern, category in self.fact_patterns:
            matches = re.findall(pattern, lower_text)
            for m in matches:
                if isinstance(m, tuple):
                    fact_str = " ".join(s for s in m if s).strip()
                else:
                    fact_str = str(m).strip()

                if len(fact_str) > 3:
                    formatted_fact = f"User {category}: {fact_str}"
                    self.db.learn_fact(category, formatted_fact, confidence=0.9)
                    learned.append((category, formatted_fact))

        # Check person introduction patterns (e.g. "This is my friend Sarah")
        intro_patterns = [
            r"(?:this is|meet|say hello to)\s+(?:my\s+)?(?:friend|colleague|brother|sister|guest|cousin)?\s*([A-Z][a-z]+)",
            r"(?:my friend|guest)\s+([A-Z][a-z]+)\s+is here",
        ]
        for ipat in intro_patterns:
            matches = re.findall(ipat, text, re.IGNORECASE)
            for person_name in matches:
                p_clean = person_name.strip().title()
                if p_clean and p_clean not in ("Akhil", "Alpha", "Hello", "Hey", "The", "Here"):
                    self.db.get_or_create_person(p_clean, relationship="guest", notes=f"Introduced during conversation: '{text}'")
                    learned.append(("person_introduction", f"Met new person: {p_clean}"))

        # Check ownership patterns (e.g. "This is Sarah's water bottle")
        for opat in self.ownership_patterns:
            matches = re.findall(opat, text, re.IGNORECASE)
            for m in matches:
                if isinstance(m, tuple) and len(m) == 2:
                    p1, p2 = m[0].strip(), m[1].strip()
                    # Determine which is person and which is object
                    if "belong" in opat:
                        obj_name, person_name = p1, p2
                    else:
                        person_name, obj_name = p1, p2

                    if len(person_name) > 1 and len(obj_name) > 2:
                        p_clean = person_name.title()
                        o_clean = obj_name.title()
                        self.db.assign_object_owner(o_clean, p_clean)
                        learned.append(("object_ownership", f"Assigned {o_clean} to {p_clean}"))

        return learned

    # =========================================================================
    # 2. Spatial & Object Learning (Vision-Driven while Roaming or Desk Monitoring)
    # =========================================================================

    def learn_object_sighting(
        self,
        object_name: str,
        description: str,
        room_name: str = "Work Desk",
        owner_name: Optional[str] = None,
        confidence: float = 0.85
    ) -> Dict[str, Any]:
        """
        Records an object observation during roaming or desk observation.
        Detects if an object has moved from another room, and associates owner!
        """
        clean_name = object_name.strip().title()
        clean_owner = owner_name.strip().title() if owner_name else None

        # Check where this object was last seen
        previous_records = self.db.find_objects(clean_name)
        moved = False
        prev_room = None

        if previous_records:
            prev = previous_records[0]
            if prev["room_name"].lower() != room_name.lower():
                moved = True
                prev_room = prev["room_name"]

        # Record sighting in SQLite with owner
        obj_id = self.db.record_discovered_object(
            name=clean_name,
            description=description,
            room_name=room_name,
            owner_name=clean_owner,
            confidence=confidence
        )

        owner_tag = f" (Belongs to {clean_owner})" if clean_owner else ""
        log_msg = f"Spotted {clean_name}{owner_tag} in {room_name}."
        if moved:
            log_msg += f" (Moved from {prev_room}!)"

        self.db.log_observation(log_msg, room_name=room_name)

        return {
            "object_id": obj_id,
            "name": clean_name,
            "room": room_name,
            "owner": clean_owner,
            "moved": moved,
            "previous_room": prev_room
        }

    # =========================================================================
    # 3. Episodic Memory Recall ("Where are my keys / shoes / Sarah's phone?")
    # =========================================================================

    def recall_object_location(
        self,
        object_query: str,
        owner_hint: Optional[str] = None
    ) -> Optional[str]:
        """Queries SQLite for the last known position of an object, filtered optionally by owner."""
        clean_q = object_query.strip()

        # Check if query itself has ownership syntax: e.g. "Akhil's mug" or "Sarah's phone"
        owner_match = re.search(r"([a-zA-Z]+)'s\s+([a-zA-Z0-9\s]+)", clean_q)
        if owner_match:
            owner_hint = owner_match.group(1).title()
            clean_q = owner_match.group(2).strip()
        elif clean_q.lower().startswith("my "):
            clean_q = clean_q[3:].strip()
            owner_hint = "Akhil"

        results = self.db.find_objects(clean_q, owner_name=owner_hint)
        if not results:
            # Fallback search without owner filter
            results = self.db.find_objects(clean_q)

        if not results:
            return None

        best = results[0]
        owner_str = ""
        if best.get("owner_name"):
            owner_str = f"{best['owner_name']}'s "

        return (
            f"I last saw {owner_str}{best['name']} in the {best['room_name']} "
            f"(Around {best['last_seen']}). Description: {best['description']}."
        )

    # =========================================================================
    # 4. Curiosity & Novelty Scoring
    # =========================================================================

    def evaluate_curiosity(self, detected_label: str, room_name: str) -> float:
        """
        Returns a curiosity score (0.0 to 1.0).
        High score indicates a brand new object or unexpected item.
        """
        matches = self.db.find_objects(detected_label)
        if not matches:
            # Never seen this object anywhere! Maximum curiosity!
            return 1.0

        # Seen before, but in this room?
        in_this_room = any(m["room_name"].lower() == room_name.lower() for m in matches)
        if not in_this_room:
            # Object moved to a new room! High curiosity!
            return 0.75

        # Familiar object in familiar place
        return 0.2

    # =========================================================================
    # 5. Contextual Thompson Sampling Bandits & Adaptive Attachment
    # =========================================================================

    def sample_interaction_behavior(self, candidate_actions: Optional[List[str]] = None) -> str:
        """
        Samples an action using Beta-Bernoulli Thompson Sampling:
        theta_k ~ Beta(alpha_k, beta_k)
        Returns the action with the maximum sampled probability.
        """
        import random
        bandits = self.db.get_bandit_parameters()
        if not candidate_actions:
            candidate_actions = list(bandits.keys()) if bandits else ["VOCAL_CHIRP"]

        best_action = candidate_actions[0]
        max_sample = -1.0

        for act in candidate_actions:
            param = bandits.get(act, {"alpha": 1.5, "beta": 1.0})
            a = max(0.1, param["alpha"])
            b = max(0.1, param["beta"])
            # Sample from Beta distribution using random.betavariate
            sampled_theta = random.betavariate(a, b)
            if sampled_theta > max_sample:
                max_sample = sampled_theta
                best_action = act

        return best_action

    def register_interaction_feedback(self, action_name: str, positive: bool = True) -> None:
        """Records owner feedback (praise/pet vs scold/push) to update Bandit parameters."""
        self.db.record_bandit_feedback(action_name, positive=positive)
        # Update long-term attachment accordingly
        delta_attach = 0.015 if positive else -0.01
        self.db.update_owner_attachment(owner_name="Akhil", delta=delta_attach)

    # =========================================================================
    # 6. Episodic Memory with Ebbinghaus Retention Dynamics
    # =========================================================================

    def record_affective_episode(
        self,
        event_type: str,
        description: str,
        valence_delta: float = 0.0,
        arousal_delta: float = 0.0
    ) -> int:
        """Encodes an episodic experience with emotional salience."""
        return self.db.record_episodic_event(
            event_type=event_type,
            description=description,
            valence_delta=valence_delta,
            arousal_delta=arousal_delta
        )

    def get_salient_memories(self, min_retention: float = 0.2, limit: int = 6) -> List[Dict[str, Any]]:
        """Retrieves memories that have survived the Ebbinghaus forgetting curve."""
        return self.db.get_active_episodic_memories(min_retention=min_retention, limit=limit)

    def reinforce_memory(self, event_id: int) -> None:
        """Strengthens memory trace via rehearsal / conversational recall."""
        self.db.reinforce_episodic_memory(event_id)

    def maintain_memory_hygiene(self) -> int:
        """Prunes memories that have decayed below retention threshold."""
        return self.db.prune_decayed_memories(threshold=0.08)
