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
