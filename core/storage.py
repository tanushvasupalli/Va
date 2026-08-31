import os
import uuid
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import config

SUPABASE_DATABASE_URI = os.getenv(
    "SUPABASE_DATABASE_URL",
    "postgresql://postgres.bpbwqvkvzjtfvxezxhja:Tanurithu.1209@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
)

def serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Converts datetime objects and non-serializable fields to clean JSON strings."""
    clean = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            clean[k] = v.strftime("%Y-%m-%d %I:%M %p")
        else:
            clean[k] = v
    return clean

class SupabaseStorageManager:
    """
    Cloud Storage Manager connected directly to Supabase Cloud PostgreSQL Database.
    Handles multi-conversation sessions, sliding context windows, permanent facts, and user preferences.
    """

    def __init__(self, db_uri: str = SUPABASE_DATABASE_URI):
        self.db_uri = db_uri
        self._ensure_tables()

    def _get_connection(self):
        """Creates a reliable connection to Supabase PostgreSQL."""
        conn = psycopg2.connect(self.db_uri, connect_timeout=10)
        conn.autocommit = True
        return conn

    def _ensure_tables(self):
        """Verifies tables exist in Supabase."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS sessions (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL DEFAULT 'New Conversation',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                        );
                        CREATE TABLE IF NOT EXISTS conversations (
                            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                            content TEXT NOT NULL,
                            source TEXT DEFAULT 'text',
                            latency REAL DEFAULT 0.0,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                        );
                        CREATE TABLE IF NOT EXISTS memories (
                            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            topic TEXT NOT NULL,
                            fact TEXT NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                        );
                        CREATE TABLE IF NOT EXISTS preferences (
                            key TEXT PRIMARY KEY,
                            value TEXT NOT NULL,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
                        );
                        INSERT INTO sessions (id, title) VALUES ('default', 'Main Conversation') ON CONFLICT (id) DO NOTHING;
                        INSERT INTO sessions (id, title) VALUES ('telegram', 'Telegram Assistant') ON CONFLICT (id) DO NOTHING;
                    """)
            print("[Storage] Supabase PostgreSQL Cloud Database connected and ready!")
        except Exception as e:
            print(f"[Storage Notice] Supabase table check: {e}")

    # =========================================================================
    # MULTI-SESSION MANAGEMENT
    # =========================================================================

    def create_session(self, title: str = "New Conversation") -> str:
        """Creates a new conversation session and returns its ID."""
        session_id = str(uuid.uuid4())[:8]
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())",
                        (session_id, title)
                    )
            return session_id
        except Exception as e:
            print(f"[Supabase Error] create_session: {e}")
            return session_id

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """Returns all sessions ordered by latest update with JSON-safe timestamps."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT s.id, s.title, s.created_at, s.updated_at,
                               COUNT(c.id) as message_count
                        FROM sessions s
                        LEFT JOIN conversations c ON s.id = c.session_id
                        GROUP BY s.id
                        ORDER BY s.updated_at DESC
                    """)
                    rows = cur.fetchall()
                    return [serialize_row(dict(r)) for r in rows]
        except Exception as e:
            print(f"[Supabase Error] get_all_sessions: {e}")
            return [{"id": "default", "title": "Main Conversation"}]

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session and its associated messages."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM conversations WHERE session_id = %s", (session_id,))
                    cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
            return True
        except Exception as e:
            print(f"[Supabase Error] delete_session: {e}")
            return False

    def rename_session(self, session_id: str, new_title: str):
        """Renames a session title."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE sessions SET title = %s, updated_at = NOW() WHERE id = %s", (new_title.strip(), session_id))
        except Exception as e:
            print(f"[Supabase Error] rename_session: {e}")

    def update_session_timestamp(self, session_id: str, auto_title_prompt: Optional[str] = None):
        """Refreshes updated_at timestamp and auto-names session from first message."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if auto_title_prompt:
                        cur.execute("SELECT title FROM sessions WHERE id = %s", (session_id,))
                        row = cur.fetchone()
                        if row and row["title"] in ["New Conversation", "Main Conversation"]:
                            clean_title = auto_title_prompt[:32].strip() + ("..." if len(auto_title_prompt) > 32 else "")
                            cur.execute("UPDATE sessions SET title = %s, updated_at = NOW() WHERE id = %s", (clean_title, session_id))
                            return
                    cur.execute("UPDATE sessions SET updated_at = NOW() WHERE id = %s", (session_id,))
        except Exception as e:
            print(f"[Supabase Error] update_session_timestamp: {e}")

    # =========================================================================
    # CONVERSATION & CONTEXT WINDOW MANAGEMENT
    # =========================================================================

    def add_message(self, role: str, content: str, source: str = "text", latency: float = 0.0, session_id: str = "default") -> int:
        """Stores a message (user or assistant) directly into Supabase."""
        if not content or not content.strip():
            return -1

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO sessions (id, title) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                        (session_id, "Telegram Assistant" if session_id == "telegram" else session_id)
                    )
                    cur.execute("""
                        INSERT INTO conversations (session_id, role, content, source, latency, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        RETURNING id
                    """, (session_id, role.strip(), content.strip(), source, latency))
                    msg_id = cur.fetchone()[0]

            if role == "user":
                self.update_session_timestamp(session_id, auto_title_prompt=content)
            else:
                self.update_session_timestamp(session_id)
            return msg_id
        except Exception as e:
            print(f"[Supabase Error] add_message: {e}")
            return -1

    def get_context_window(self, limit: int = 10, session_id: str = "default") -> List[Dict[str, Any]]:
        """Retrieves latest N messages for LLM context window in chronological order."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT role, content, source, latency, created_at
                        FROM conversations
                        WHERE session_id = %s
                        ORDER BY id DESC
                        LIMIT %s
                    """, (session_id, limit))
                    rows = cur.fetchall()
                    return [serialize_row(dict(r)) for r in reversed(rows)]
        except Exception as e:
            print(f"[Supabase Error] get_context_window: {e}")
            return []

    def get_session_messages(self, session_id: str, limit: int = 80) -> List[Dict[str, Any]]:
        """Returns message history for a specific conversation session with clean string timestamps."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT id, session_id, role, content, source, latency,
                               to_char(created_at, 'HH12:MI AM') as timestamp,
                               created_at
                        FROM conversations
                        WHERE session_id = %s
                        ORDER BY id ASC
                        LIMIT %s
                    """, (session_id, limit))
                    rows = cur.fetchall()
                    return [serialize_row(dict(r)) for r in rows]
        except Exception as e:
            print(f"[Supabase Error] get_session_messages: {e}")
            return []

    def get_telegram_messages(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves Telegram messages with optional full-text search and source filter."""
        try:
            query = """
                SELECT id, session_id, role, content, source, latency,
                       to_char(created_at, 'YYYY-MM-DD HH12:MI AM') as formatted_time,
                       to_char(created_at, 'HH12:MI AM') as timestamp,
                       created_at
                FROM conversations
                WHERE (session_id = 'telegram' OR source ILIKE '%%telegram%%')
            """
            params = []

            if source_filter and source_filter.lower() != "all":
                if source_filter == "voice":
                    query += " AND (source ILIKE '%%voice%%')"
                elif source_filter == "text":
                    query += " AND (source NOT ILIKE '%%voice%%')"
                elif source_filter in ("user", "assistant"):
                    query += " AND role = %s"
                    params.append(source_filter)

            if search and search.strip():
                query += " AND content ILIKE %s"
                params.append(f"%{search.strip()}%")

            query += " ORDER BY id DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, tuple(params))
                    rows = cur.fetchall()
                    # Return in chronological order for chat view
                    return [serialize_row(dict(r)) for r in reversed(rows)]
        except Exception as e:
            print(f"[Supabase Error] get_telegram_messages: {e}")
            return []

    def get_telegram_stats(self) -> Dict[str, Any]:
        """Calculates aggregate metrics for Telegram interactions."""
        default_stats = {
            "total_messages": 0,
            "user_messages": 0,
            "assistant_messages": 0,
            "voice_notes_count": 0,
            "text_messages_count": 0,
            "avg_latency": 0.0,
            "last_active": "Never"
        }
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_messages,
                            COUNT(*) FILTER (WHERE role = 'user') as user_messages,
                            COUNT(*) FILTER (WHERE role = 'assistant') as assistant_messages,
                            COUNT(*) FILTER (WHERE source ILIKE '%%voice%%') as voice_notes_count,
                            COUNT(*) FILTER (WHERE source NOT ILIKE '%%voice%%') as text_messages_count,
                            COALESCE(AVG(latency) FILTER (WHERE role = 'assistant' AND latency > 0), 0) as avg_latency,
                            MAX(created_at) as last_active_ts
                        FROM conversations
                        WHERE (session_id = 'telegram' OR source ILIKE '%%telegram%%')
                    """)
                    row = cur.fetchone()
                    if row:
                        stats = dict(row)
                        last_ts = stats.get("last_active_ts")
                        stats["last_active"] = last_ts.strftime("%b %d, %I:%M %p") if last_ts else "No interactions yet"
                        stats["avg_latency"] = round(float(stats.get("avg_latency", 0)), 2)
                        return serialize_row(stats)
            return default_stats
        except Exception as e:
            print(f"[Supabase Error] get_telegram_stats: {e}")
            return default_stats

    def delete_message_by_id(self, message_id: int) -> bool:
        """Deletes a specific message by its ID."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM conversations WHERE id = %s", (message_id,))
            return True
        except Exception as e:
            print(f"[Supabase Error] delete_message_by_id: {e}")
            return False

    def clear_telegram_history(self) -> bool:
        """Deletes all conversation records associated with Telegram."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM conversations WHERE session_id = 'telegram' OR source ILIKE '%%telegram%%'")
            return True
        except Exception as e:
            print(f"[Supabase Error] clear_telegram_history: {e}")
            return False

    def clear_session_messages(self, session_id: str):
        """Clears messages for a session."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM conversations WHERE session_id = %s", (session_id,))
        except Exception as e:
            print(f"[Supabase Error] clear_session_messages: {e}")

    def clear_all_data(self):
        """Wipes all conversations and resets sessions."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM conversations")
                    cur.execute("DELETE FROM sessions")
                    cur.execute("INSERT INTO sessions (id, title) VALUES ('default', 'Main Conversation')")
                    cur.execute("INSERT INTO sessions (id, title) VALUES ('telegram', 'Telegram Assistant')")
        except Exception as e:
            print(f"[Supabase Error] clear_all_data: {e}")

    # =========================================================================
    # LONG-TERM MEMORY & KNOWLEDGE FACTS
    # =========================================================================

    def remember_fact(self, topic: str, fact: str) -> bool:
        """Saves a permanent fact into Supabase memories table."""
        if not fact or not fact.strip():
            return False

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO memories (topic, fact, created_at) VALUES (%s, %s, NOW())",
                        (topic.strip().lower(), fact.strip())
                    )
            return True
        except Exception as e:
            print(f"[Supabase Error] remember_fact: {e}")
            return False

    def get_all_memories(self) -> List[Dict[str, Any]]:
        """Returns all persistent memories from Supabase with JSON-safe timestamps."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT id, topic, fact, created_at FROM memories ORDER BY id DESC")
                    rows = cur.fetchall()
                    return [serialize_row(dict(r)) for r in rows]
        except Exception as e:
            print(f"[Supabase Error] get_all_memories: {e}")
            return []

    def delete_memory_by_id(self, memory_id: int) -> bool:
        """Deletes a memory entry by ID from Supabase."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
            return True
        except Exception as e:
            print(f"[Supabase Error] delete_memory_by_id: {e}")
            return False

    def format_memories_for_prompt(self) -> str:
        """Formats long-term memories for LLM system prompt injection."""
        memories = self.get_all_memories()
        if not memories:
            return ""
        lines = [f"- [{m['topic'].capitalize()}]: {m['fact']}" for m in memories]
        return "\n[Persistent Memories / Known User Facts]:\n" + "\n".join(lines) + "\n"

    def get_preference(self, key: str, default: str = "") -> str:
        """Retrieves a stored system configuration preference from Supabase."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT value FROM preferences WHERE key = %s", (key.strip(),))
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        return str(row[0])
            return default
        except Exception as e:
            print(f"[Supabase Error] get_preference: {e}")
            return default

    def set_preference(self, key: str, value: str) -> bool:
        """Saves or updates a system preference in Supabase."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO preferences (key, value, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                    """, (key.strip(), str(value).strip()))
            return True
        except Exception as e:
            print(f"[Supabase Error] set_preference: {e}")
            return False

# Global singleton storage instance connected to Supabase
storage = SupabaseStorageManager()
