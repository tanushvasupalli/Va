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

    def forget_fact(self, topic: str) -> int:
        """Removes memories matching a topic from Supabase."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM memories WHERE topic ILIKE %s", (f"%{topic.strip().lower()}%",))
                    return cur.rowcount
        except Exception as e:
            print(f"[Supabase Error] forget_fact: {e}")
            return 0

# Global singleton storage instance connected to Supabase
storage = SupabaseStorageManager()
