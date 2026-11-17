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
                    sighting_count INTEGER DEFAULT 1,
                    is_moved INTEGER DEFAULT 0,
                    previous_room TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES Rooms(room_id)
                )
            """)

            # Safe migrations for existing databases
            for col_def in [
                ("sighting_count", "INTEGER DEFAULT 1"),
                ("is_moved", "INTEGER DEFAULT 0"),
                ("previous_room", "TEXT")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE DiscoveredObjects ADD COLUMN {col_def[0]} {col_def[1]}")
                except Exception:
                    pass

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

            # 6. Episodic Events Memory with Salience and Reinforcement
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS EpisodicEvents (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    valence_delta REAL DEFAULT 0.0,
                    arousal_delta REAL DEFAULT 0.0,
                    salience REAL DEFAULT 0.5,
                    reinforcement_count INTEGER DEFAULT 1,
                    last_recalled TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 7. Owner Profile (Akhil's long-term attachment profile)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS OwnerProfile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_name TEXT NOT NULL UNIQUE,
                    face_enrolled INTEGER DEFAULT 1,
                    voice_enrolled INTEGER DEFAULT 1,
                    attachment_level REAL DEFAULT 0.75,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 8. Contextual Thompson Sampling Interaction Bandits
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS InteractionBandits (
                    action_name TEXT PRIMARY KEY,
                    alpha_param REAL DEFAULT 1.0,
                    beta_param REAL DEFAULT 1.0,
                    total_trials INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

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
                "SELECT object_id, room_id FROM DiscoveredObjects WHERE name = ?",
                (clean_name,)
            )
            existing = cursor.fetchone()
            if existing:
                # Detect if object has moved to a new room
                cursor.execute("SELECT name FROM Rooms WHERE room_id = ?", (existing["room_id"],))
                prev_room_row = cursor.fetchone()
                prev_room_name = prev_room_row["name"] if prev_room_row else ""
                moved = (prev_room_name.lower() != room_name.lower()) if prev_room_name else False

                cursor.execute("""
                    UPDATE DiscoveredObjects SET
                        room_id = ?,
                        description = ?,
                        thumbnail_path = COALESCE(?, thumbnail_path),
                        confidence = ?,
                        sighting_count = COALESCE(sighting_count, 1) + 1,
                        is_moved = ?,
                        previous_room = CASE WHEN ? = 1 THEN ? ELSE previous_room END,
                        last_seen = CURRENT_TIMESTAMP
                    WHERE object_id = ?
                """, (
                    room_id, description, thumbnail_path, confidence,
                    1 if moved else 0, 1 if moved else 0, prev_room_name,
                    existing["object_id"]
                ))
                conn.commit()
                return existing["object_id"]
            else:
                cursor.execute("""
                    INSERT INTO DiscoveredObjects (name, room_id, description, thumbnail_path, confidence, sighting_count, is_moved)
                    VALUES (?, ?, ?, ?, ?, 1, 0)
                """, (clean_name, room_id, description, thumbnail_path, confidence))
                conn.commit()
                return cursor.lastrowid

    def find_objects(self, query: str = "", limit: int = 50) -> List[Dict[str, Any]]:
        """Answers 'where are my keys / shoes / wallet' by searching memory."""
        clean_q = f"%{query.strip()}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.name, o.description, r.name as room_name, o.last_seen, o.thumbnail_path,
                       COALESCE(o.sighting_count, 1) as sighting_count,
                       COALESCE(o.is_moved, 0) as is_moved,
                       o.previous_room
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

    # =========================================================================
    # 6. Episodic Memory & Ebbinghaus Retention Dynamics
    # =========================================================================

    def record_episodic_event(
        self,
        event_type: str,
        description: str,
        valence_delta: float = 0.0,
        arousal_delta: float = 0.0,
        salience: Optional[float] = None
    ) -> int:
        """
        Stores an episodic event with an intrinsic salience.
        Salience S = min(1.0, |d_val| + |d_aro| + baseline).
        """
        if salience is None:
            salience = min(1.0, 0.35 + abs(valence_delta) + abs(arousal_delta))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO EpisodicEvents (
                    event_type, description, valence_delta, arousal_delta, salience
                ) VALUES (?, ?, ?, ?, ?)
            """, (event_type, description.strip(), float(valence_delta), float(arousal_delta), float(salience)))
            event_id = cursor.lastrowid
            conn.commit()
            return event_id

    def get_active_episodic_memories(
        self,
        min_retention: float = 0.15,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Computes Ebbinghaus retention R(t) = S * (1 + delta_hours / 24.0) ** -0.45
        Returns currently retained active episodic memories.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_id, timestamp, event_type, description,
                       valence_delta, arousal_delta, salience,
                       reinforcement_count, last_recalled
                FROM EpisodicEvents
                ORDER BY event_id DESC
                LIMIT 50
            """)
            rows = cursor.fetchall()

        now = datetime.datetime.now(datetime.timezone.utc)
        active = []
        for r in rows:
            d = dict(r)
            try:
                # Handle SQLite timestamp parsing
                ts_str = d["timestamp"].replace("Z", "").split(".")[0]
                ev_time = datetime.datetime.fromisoformat(ts_str)
                if ev_time.tzinfo is None:
                    ev_time = ev_time.replace(tzinfo=datetime.timezone.utc)
                delta_hours = max(0.0, (now - ev_time).total_seconds() / 3600.0)
            except Exception:
                delta_hours = 0.0

            # Ebbinghaus Power-Law Retention Equation
            s = d["salience"]
            # Each reinforcement extends effective stability
            tau = 24.0 * (1.0 + 0.5 * (d["reinforcement_count"] - 1))
            retention = s * ((1.0 + (delta_hours / tau)) ** -0.45)
            d["retention"] = round(retention, 4)

            if retention >= min_retention:
                active.append(d)
                if len(active) >= limit:
                    break

        return active

    def reinforce_episodic_memory(self, event_id: int) -> None:
        """Strengthens an episodic memory when recalled, increasing retention."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE EpisodicEvents
                SET reinforcement_count = reinforcement_count + 1,
                    salience = MIN(1.0, salience + 0.15),
                    last_recalled = CURRENT_TIMESTAMP
                WHERE event_id = ?
            """, (event_id,))
            conn.commit()

    def prune_decayed_memories(self, threshold: float = 0.08) -> int:
        """Prunes memories whose retention has fallen below retention threshold."""
        active = self.get_active_episodic_memories(min_retention=threshold, limit=500)
        active_ids = {m["event_id"] for m in active}

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_id FROM EpisodicEvents")
            all_ids = {r[0] for r in cursor.fetchall()}
            decayed_ids = all_ids - active_ids
            if decayed_ids:
                placeholders = ",".join("?" for _ in decayed_ids)
                cursor.execute(f"DELETE FROM EpisodicEvents WHERE event_id IN ({placeholders})", list(decayed_ids))
                conn.commit()
            return len(decayed_ids)

    # =========================================================================
    # 7. Owner Profile & Attachment Dynamics
    # =========================================================================

    def get_or_create_owner_profile(self, owner_name: str = "Akhil") -> Dict[str, Any]:
        """Fetches or initializes the long-term owner profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM OwnerProfile WHERE owner_name = ?", (owner_name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            cursor.execute(
                "INSERT INTO OwnerProfile (owner_name, attachment_level) VALUES (?, ?)",
                (owner_name, 0.85)
            )
            conn.commit()
            cursor.execute("SELECT * FROM OwnerProfile WHERE owner_name = ?", (owner_name,))
            return dict(cursor.fetchone())

    def update_owner_attachment(self, owner_name: str = "Akhil", delta: float = 0.02) -> float:
        """Modulates attachment level toward owner with asymptotic limits [0.1, 1.0]."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT attachment_level FROM OwnerProfile WHERE owner_name = ?", (owner_name,))
            row = cursor.fetchone()
            curr = row[0] if row else 0.8
            new_level = max(0.1, min(1.0, curr + delta))
            cursor.execute("""
                UPDATE OwnerProfile
                SET attachment_level = ?, last_seen = CURRENT_TIMESTAMP
                WHERE owner_name = ?
            """, (new_level, owner_name))
            conn.commit()
            return new_level

    # =========================================================================
    # 8. Contextual Thompson Sampling Interaction Bandits
    # =========================================================================

    def record_bandit_feedback(self, action_name: str, positive: bool = True) -> None:
        """Updates Beta distribution parameters (alpha, beta) for an interaction action."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if positive:
                cursor.execute("""
                    INSERT INTO InteractionBandits (action_name, alpha_param, beta_param, total_trials)
                    VALUES (?, 2.0, 1.0, 1)
                    ON CONFLICT(action_name) DO UPDATE SET
                        alpha_param = alpha_param + 1.0,
                        total_trials = total_trials + 1,
                        last_updated = CURRENT_TIMESTAMP
                """, (action_name,))
            else:
                cursor.execute("""
                    INSERT INTO InteractionBandits (action_name, alpha_param, beta_param, total_trials)
                    VALUES (?, 1.0, 2.0, 1)
                    ON CONFLICT(action_name) DO UPDATE SET
                        beta_param = beta_param + 1.0,
                        total_trials = total_trials + 1,
                        last_updated = CURRENT_TIMESTAMP
                """, (action_name,))
            conn.commit()

    def get_bandit_parameters(self) -> Dict[str, Dict[str, float]]:
        """Retrieves active alpha, beta params for all interaction behaviors."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT action_name, alpha_param, beta_param, total_trials FROM InteractionBandits")
            rows = cursor.fetchall()
            return {
                r["action_name"]: {
                    "alpha": r["alpha_param"],
                    "beta": r["beta_param"],
                    "trials": r["total_trials"]
                }
                for r in rows
            }

    def clear_all_memory(self) -> None:
        """
        Clears all user facts, discovered objects, roaming observations, and chat history,
        allowing the SQLite memory to build 100% organically from scratch with zero injections.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM UserFacts")
            cursor.execute("DELETE FROM DiscoveredObjects")
            cursor.execute("DELETE FROM RoamingObservations")
            cursor.execute("DELETE FROM ChatHistory")
            cursor.execute("DELETE FROM EpisodicEvents")
            conn.commit()
