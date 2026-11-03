"""
Project Alpha: Local SQLite Knowledge Graph & Long-Term Memory Engine.
Provides persistent, private on-device memory for user facts, discovered objects,
room mapping, and roaming observations.
"""

import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from core.config import DB_PATH

class AlphaDatabase:
    """Manages the local SQLite knowledge graph on the Raspberry Pi."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.init_database()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_database(self) -> None:
        """Initializes tables for world knowledge, episodic logs, and user memory."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. User Facts & Preferences (What Alpha learns about Akhil)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS UserFacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    fact TEXT NOT NULL UNIQUE,
                    confidence REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Known Rooms & Exploration Landmarks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Rooms (
                    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    first_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_visited TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Discovered Objects Catalog (Learned while roaming)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS DiscoveredObjects (
                    object_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    room_id INTEGER,
                    description TEXT,
                    thumbnail_path TEXT,
                    confidence REAL DEFAULT 0.8,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES Rooms(room_id)
                )
            """)

            # 4. Roaming Observations (Episodic memory timeline)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS RoamingObservations (
                    obs_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    room_id INTEGER,
                    observation TEXT NOT NULL,
                    ambient_light TEXT DEFAULT 'Normal',
                    battery_level REAL,
                    FOREIGN KEY (room_id) REFERENCES Rooms(room_id)
                )
            """)

            # 5. Conversation History (For continuous conversational rapport)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ChatHistory (
                    msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    brain_type TEXT DEFAULT 'gemini'
                )
            """)

            # Seed default room if empty
            cursor.execute("SELECT COUNT(*) FROM Rooms")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO Rooms (name, description) VALUES (?, ?)",
                    ("Work Desk", "Home base and charging dock station.")
                )

            conn.commit()

    # =========================================================================
    # User Fact Learning
    # =========================================================================

    def learn_fact(self, category: str, fact: str, confidence: float = 1.0) -> None:
        """Stores or updates a learned fact about the user or household."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO UserFacts (category, fact, confidence, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(fact) DO UPDATE SET
                    category = excluded.category,
                    confidence = excluded.confidence,
                    updated_at = CURRENT_TIMESTAMP
            """, (category.lower().strip(), fact.strip(), confidence))
            conn.commit()

    def get_user_facts(self, category: Optional[str] = None, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieves learned facts about the user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "SELECT * FROM UserFacts WHERE category = ? ORDER BY updated_at DESC LIMIT ?",
                    (category.lower().strip(), limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM UserFacts ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Room & Object Discovery
    # =========================================================================

    def get_or_create_room(self, name: str, description: str = "") -> int:
        """Resolves or inserts a room name and returns its ID."""
        clean_name = name.strip().title()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT room_id FROM Rooms WHERE name = ?", (clean_name,))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE Rooms SET last_visited = CURRENT_TIMESTAMP WHERE room_id = ?", (row["room_id"],))
                conn.commit()
                return row["room_id"]
            cursor.execute(
                "INSERT INTO Rooms (name, description, last_visited) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (clean_name, description)
            )
            conn.commit()
            return cursor.lastrowid

    def record_discovered_object(
        self,
        name: str,
        description: str,
        room_name: str = "Work Desk",
        thumbnail_path: Optional[str] = None,
        confidence: float = 0.85
    ) -> int:
        """Records an object identified by vision while roaming (updates location if moved)."""
        room_id = self.get_or_create_room(room_name)
        clean_name = name.strip().title()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check if this object was already seen anywhere in the house
            cursor.execute(
                "SELECT object_id FROM DiscoveredObjects WHERE name = ?",
                (clean_name,)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE DiscoveredObjects SET
                        room_id = ?,
                        description = ?,
                        thumbnail_path = COALESCE(?, thumbnail_path),
                        confidence = ?,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE object_id = ?
                """, (room_id, description, thumbnail_path, confidence, existing["object_id"]))
                conn.commit()
                return existing["object_id"]
            else:
                cursor.execute("""
                    INSERT INTO DiscoveredObjects (name, room_id, description, thumbnail_path, confidence)
                    VALUES (?, ?, ?, ?, ?)
                """, (clean_name, room_id, description, thumbnail_path, confidence))
                conn.commit()
                return cursor.lastrowid

    def find_objects(self, query: str) -> List[Dict[str, Any]]:
        """Answers 'where are my keys / shoes / wallet' by searching memory."""
        clean_q = f"%{query.strip()}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.name, o.description, r.name as room_name, o.last_seen, o.thumbnail_path
                FROM DiscoveredObjects o
                LEFT JOIN Rooms r ON o.room_id = r.room_id
                WHERE o.name LIKE ? OR o.description LIKE ?
                ORDER BY o.last_seen DESC LIMIT 5
            """, (clean_q, clean_q))
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Episodic Roaming Observations
    # =========================================================================

    def log_observation(
        self,
        observation: str,
        room_name: str = "Work Desk",
        ambient_light: str = "Normal",
        battery_level: float = 7.4
    ) -> None:
        """Logs a natural language observation during autonomous roaming."""
        room_id = self.get_or_create_room(room_name)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO RoamingObservations (room_id, observation, ambient_light, battery_level)
                VALUES (?, ?, ?, ?)
            """, (room_id, observation.strip(), ambient_light, battery_level))
            conn.commit()

    def get_recent_observations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetches the latest roaming logs for conversational recall."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.timestamp, r.name as room_name, o.observation, o.ambient_light, o.battery_level
                FROM RoamingObservations o
                LEFT JOIN Rooms r ON o.room_id = r.room_id
                ORDER BY o.timestamp DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Conversation Rapport & Context Injection
    # =========================================================================

    def save_chat_message(self, role: str, message: str, brain_type: str = "gemini") -> None:
        """Saves a conversation turn."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ChatHistory (role, message, brain_type) VALUES (?, ?, ?)",
                (role, message.strip(), brain_type)
            )
            conn.commit()

    def get_recent_chat(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Returns the most recent conversation turns."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, message, timestamp FROM ChatHistory ORDER BY msg_id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            # Return in chronological order
            return [dict(r) for r in reversed(rows)]

    def generate_system_prompt_context(self) -> str:
        """
        Synthesizes the local knowledge graph into an active context string
        to inject into Gemini or Gemma's system prompt.
        """
        facts = self.get_user_facts(limit=10)
        observations = self.get_recent_observations(limit=4)

        context_lines = ["\n[LOCAL MEMORY & HOUSEHOLD AWARENESS]"]

        if facts:
            context_lines.append("Known Facts About User & Home:")
            for f in facts:
                context_lines.append(f" - [{f['category'].capitalize()}] {f['fact']}")

        if observations:
            context_lines.append("\nWhat Alpha Observed While Recently Roaming:")
            for obs in observations:
                context_lines.append(f" - At {obs['timestamp']} in {obs['room_name']}: {obs['observation']}")

        return "\n".join(context_lines)
