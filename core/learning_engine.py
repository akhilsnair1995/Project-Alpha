"""
Project Alpha: Autonomous Learning Engine.
Processes sensory streams, extracts personal facts from conversation,
tracks spatial object movement across rooms, and generates episodic memories.
"""

import re
import datetime
from typing import Dict, List, Optional, Any, Tuple
from core.database import AlphaDatabase

class AutonomousLearningEngine:
    """Manages continuous spatial, episodic, and personal fact learning."""

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

    # =========================================================================
    # 1. Personal Fact Learning (Conversation-Driven)
    # =========================================================================

    def extract_and_learn_from_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Parses user text with heuristic patterns to extract personal facts,
        and saves them immediately into SQLite.
        Returns list of (category, fact) learned.
        """
        learned = []
        lower_text = text.lower().strip()

        for pattern, category in self.fact_patterns:
            matches = re.findall(pattern, lower_text)
            for m in matches:
                if isinstance(m, tuple):
                    # Handle multiple capture groups
                    fact_str = " ".join(s for s in m if s).strip()
                else:
                    fact_str = str(m).strip()

                if len(fact_str) > 3:
                    formatted_fact = f"User {category}: {fact_str}"
                    self.db.learn_fact(category, formatted_fact, confidence=0.9)
                    learned.append((category, formatted_fact))

        return learned

    # =========================================================================
    # 2. Spatial & Object Learning (Vision-Driven while Roaming)
    # =========================================================================

    def learn_object_sighting(
        self,
        object_name: str,
        description: str,
        room_name: str = "Work Desk",
        confidence: float = 0.85
    ) -> Dict[str, Any]:
        """
        Records an object observation during roaming.
        Detects if an object has moved from another room!
        """
        clean_name = object_name.strip().title()

        # Check where this object was last seen
        previous_records = self.db.find_objects(clean_name)
        moved = False
        prev_room = None

        if previous_records:
            prev = previous_records[0]
            if prev["room_name"].lower() != room_name.lower():
                moved = True
                prev_room = prev["room_name"]

        # Record sighting in SQLite
        obj_id = self.db.record_discovered_object(
            name=clean_name,
            description=description,
            room_name=room_name,
            confidence=confidence
        )

        log_msg = f"Spotted {clean_name} in {room_name}."
        if moved:
            log_msg += f" (Moved from {prev_room}!)"

        self.db.log_observation(log_msg, room_name=room_name)

        return {
            "object_id": obj_id,
            "name": clean_name,
            "room": room_name,
            "moved": moved,
            "previous_room": prev_room
        }

    # =========================================================================
    # 3. Episodic Memory Recall ("Where are my keys / shoes?")
    # =========================================================================

    def recall_object_location(self, object_query: str) -> Optional[str]:
        """Queries SQLite for the last known position of an object."""
        results = self.db.find_objects(object_query)
        if not results:
            return None

        best = results[0]
        return (
            f"I last saw your {best['name']} in the {best['room_name']} "
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
