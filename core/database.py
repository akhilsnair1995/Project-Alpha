"""
Project Alpha: Local SQLite Knowledge Graph & Long-Term Memory Engine.
Provides persistent, private on-device memory for user facts, discovered objects,
room mapping, known people, person-object ownership associations, and roaming observations.
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
        """Initializes tables for world knowledge, episodic logs, user memory, and person profiling."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. User Facts & Preferences (What Alpha learns about Akhil and household)
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

            # 2. Known People & Companions (Multiple person identification & profiling)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Persons (
                    person_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    relationship TEXT DEFAULT 'friend',
                    visual_description TEXT,
                    face_encoding TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """)

            # 3. Known Rooms & Exploration Landmarks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Rooms (
                    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    first_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_visited TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Discovered Objects Catalog (Learned while roaming or at desk with ownership)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS DiscoveredObjects (
                    object_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    room_id INTEGER,
                    description TEXT,
                    owner_name TEXT DEFAULT NULL,
                    thumbnail_path TEXT,
                    confidence REAL DEFAULT 0.8,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES Rooms(room_id)
                )
            """)

            # Schema Migration: Ensure 'owner_name' column exists in DiscoveredObjects if upgraded
            cursor.execute("PRAGMA table_info(DiscoveredObjects)")
            cols = [r[1] for r in cursor.fetchall()]
            if "owner_name" not in cols:
                cursor.execute("ALTER TABLE DiscoveredObjects ADD COLUMN owner_name TEXT DEFAULT NULL")

            # 5. Roaming Observations (Episodic memory timeline)
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

            # 6. Conversation History (For continuous conversational rapport)
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

            # Seed primary companion & owner: Akhil
            cursor.execute("SELECT COUNT(*) FROM Persons WHERE name = 'Akhil'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO Persons (name, relationship, visual_description, notes)
                    VALUES (?, ?, ?, ?)
                """, (
                    "Akhil",
                    "owner",
                    "Primary human companion & maker. Wears spectacles, sits at desk, builder of Alpha.",
                    "Creator and primary companion of Project Alpha."
                ))

            conn.commit()

    # =========================================================================
    # Person Identification & Profiling (Multiple Persons)
    # =========================================================================

    def get_or_create_person(
        self,
        name: str,
        relationship: str = "friend",
        visual_description: str = "",
        notes: str = ""
    ) -> int:
        """Resolves or inserts a known person and updates their last seen timestamp."""
        clean_name = name.strip().title()
        if not clean_name:
            clean_name = "Guest"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT person_id FROM Persons WHERE name = ?", (clean_name,))
            row = cursor.fetchone()
            if row:
                if visual_description or (relationship and relationship != "friend"):
                    cursor.execute("""
                        UPDATE Persons SET
                            last_seen = CURRENT_TIMESTAMP,
                            visual_description = CASE WHEN ? != '' THEN ? ELSE visual_description END,
                            relationship = CASE WHEN ? != 'friend' THEN ? ELSE relationship END
                        WHERE person_id = ?
                    """, (visual_description, visual_description, relationship, relationship, row["person_id"]))
                else:
                    cursor.execute("UPDATE Persons SET last_seen = CURRENT_TIMESTAMP WHERE person_id = ?", (row["person_id"],))
                conn.commit()
                return row["person_id"]

            cursor.execute("""
                INSERT INTO Persons (name, relationship, visual_description, notes, last_seen)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (clean_name, relationship.lower(), visual_description, notes))
            conn.commit()
            return cursor.lastrowid

    def update_person_profile(
        self,
        name: str,
        relationship: Optional[str] = None,
        visual_description: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Updates attributes of a known person."""
        clean_name = name.strip().title()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT person_id FROM Persons WHERE name = ?", (clean_name,))
            row = cursor.fetchone()
            if not row:
                return False
            cursor.execute("""
                UPDATE Persons SET
                    relationship = COALESCE(?, relationship),
                    visual_description = COALESCE(?, visual_description),
                    notes = COALESCE(?, notes),
                    last_seen = CURRENT_TIMESTAMP
                WHERE person_id = ?
            """, (relationship, visual_description, notes, row["person_id"]))
            conn.commit()
            return True

    def get_known_persons(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves list of all registered persons."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Persons ORDER BY last_seen DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_person_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Case-insensitive search for a person."""
        clean_name = name.strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Persons WHERE name LIKE ? LIMIT 1", (f"%{clean_name}%",))
            row = cursor.fetchone()
            return dict(row) if row else None

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
    # Room & Object Discovery with Ownership Tracking
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
        owner_name: Optional[str] = None,
        thumbnail_path: Optional[str] = None,
        confidence: float = 0.85
    ) -> int:
        """Records an object identified by vision while roaming or observing desk (tracks location and owner)."""
        room_id = self.get_or_create_room(room_name)
        clean_name = name.strip().title()
        clean_owner = owner_name.strip().title() if owner_name else None

        if clean_owner and clean_owner.lower() not in ("none", "unassigned", "unknown", "shared"):
            self.get_or_create_person(clean_owner)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT object_id, owner_name FROM DiscoveredObjects WHERE name = ?",
                (clean_name,)
            )
            existing = cursor.fetchone()
            if existing:
                final_owner = clean_owner if clean_owner else existing["owner_name"]
                cursor.execute("""
                    UPDATE DiscoveredObjects SET
                        room_id = ?,
                        description = ?,
                        owner_name = ?,
                        thumbnail_path = COALESCE(?, thumbnail_path),
                        confidence = ?,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE object_id = ?
                """, (room_id, description, final_owner, thumbnail_path, confidence, existing["object_id"]))
                conn.commit()
                return existing["object_id"]
            else:
                cursor.execute("""
                    INSERT INTO DiscoveredObjects (name, room_id, description, owner_name, thumbnail_path, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (clean_name, room_id, description, clean_owner, thumbnail_path, confidence))
                conn.commit()
                return cursor.lastrowid

    def assign_object_owner(self, object_name: str, owner_name: str) -> bool:
        """Assigns or updates an object's owner (e.g. 'Akhil', 'John'). Inserts object if not yet cataloged."""
        clean_name = object_name.strip().title()
        clean_owner = owner_name.strip().title()
        self.get_or_create_person(clean_owner)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT object_id FROM DiscoveredObjects WHERE name LIKE ?",
                (f"%{clean_name}%",)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE DiscoveredObjects SET
                        owner_name = ?,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE object_id = ?
                """, (clean_owner, existing["object_id"]))
                conn.commit()
                return True

        # Insert new object if not already cataloged
        self.record_discovered_object(
            name=clean_name,
            description=f"Item belonging to {clean_owner}.",
            owner_name=clean_owner
        )
        return True

    def get_person_objects(self, owner_name: str) -> List[Dict[str, Any]]:
        """Returns all objects owned by or assigned to a specific person."""
        clean_owner = f"%{owner_name.strip()}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.name, o.description, r.name as room_name, o.owner_name, o.last_seen, o.thumbnail_path
                FROM DiscoveredObjects o
                LEFT JOIN Rooms r ON o.room_id = r.room_id
                WHERE o.owner_name LIKE ?
                ORDER BY o.last_seen DESC
            """, (clean_owner,))
            return [dict(row) for row in cursor.fetchall()]

    def find_objects(self, query: str = "", owner_name: Optional[str] = None, limit: int = 15) -> List[Dict[str, Any]]:
        """Answers 'where are my keys / shoes / wallet' by searching memory with optional owner filter."""
        clean_q = f"%{query.strip()}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if owner_name:
                clean_owner = f"%{owner_name.strip()}%"
                cursor.execute("""
                    SELECT o.name, o.description, r.name as room_name, o.owner_name, o.last_seen, o.thumbnail_path
                    FROM DiscoveredObjects o
                    LEFT JOIN Rooms r ON o.room_id = r.room_id
                    WHERE (o.name LIKE ? OR o.description LIKE ?) AND o.owner_name LIKE ?
                    ORDER BY o.last_seen DESC LIMIT ?
                """, (clean_q, clean_q, clean_owner, limit))
            else:
                cursor.execute("""
                    SELECT o.name, o.description, r.name as room_name, o.owner_name, o.last_seen, o.thumbnail_path
                    FROM DiscoveredObjects o
                    LEFT JOIN Rooms r ON o.room_id = r.room_id
                    WHERE o.name LIKE ? OR o.description LIKE ?
                    ORDER BY o.last_seen DESC LIMIT ?
                """, (clean_q, clean_q, limit))
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
            return [dict(r) for r in reversed(rows)]

    def generate_system_prompt_context(self) -> str:
        """
        Synthesizes the local knowledge graph into an active context string
        to inject into Gemini or Gemma's system prompt.
        """
        persons = self.get_known_persons(limit=6)
        objects = self.find_objects("", limit=8)
        facts = self.get_user_facts(limit=8)
        observations = self.get_recent_observations(limit=4)

        context_lines = ["\n[LOCAL MEMORY & HOUSEHOLD AWARENESS]"]

        if persons:
            context_lines.append("Known People in Household:")
            for p in persons:
                rel = f" ({p['relationship'].capitalize()})" if p.get("relationship") else ""
                desc = f": {p['visual_description']}" if p.get("visual_description") else ""
                context_lines.append(f" - {p['name']}{rel}{desc}")

        if objects:
            context_lines.append("\nTracked Objects & Assigned Owners:")
            for obj in objects:
                owner = f" [Owner: {obj['owner_name']}]" if obj.get("owner_name") else " [Unassigned]"
                context_lines.append(f" - {obj['name']}{owner} in {obj.get('room_name', 'Unknown')}: {obj.get('description', '')}")

        if facts:
            context_lines.append("\nKnown Facts About User & Home:")
            for f in facts:
                context_lines.append(f" - [{f['category'].capitalize()}] {f['fact']}")

        if observations:
            context_lines.append("\nWhat Alpha Observed While Recently Roaming:")
            for obs in observations:
                context_lines.append(f" - At {obs['timestamp']} in {obs['room_name']}: {obs['observation']}")

        return "\n".join(context_lines)
