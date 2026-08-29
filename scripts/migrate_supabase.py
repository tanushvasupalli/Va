import psycopg2
import sys

CONNECTION_URIS = [
    "postgresql://postgres.bpbwqvkvzjtfvxezxhja:Tanurithu.1209@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres",
    "postgresql://postgres.bpbwqvkvzjtfvxezxhja:Tanurithu.1209@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
    "postgresql://postgres:Tanurithu.1209@db.bpbwqvkvzjtfvxezxhja.supabase.co:5432/postgres"
]

SCHEMA_SQL = """
-- 1. Create Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Create Conversations Table
CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    source TEXT DEFAULT 'text',
    latency REAL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Create Memories Table
CREATE TABLE IF NOT EXISTS memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    topic TEXT NOT NULL,
    fact TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. Create Preferences Table
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. Seed default session
INSERT INTO sessions (id, title)
VALUES ('default', 'Main Conversation')
ON CONFLICT (id) DO NOTHING;
"""

def test_and_migrate():
    conn = None
    working_uri = None
    
    for uri in CONNECTION_URIS:
        try:
            print(f"Attempting connection to: {uri.split('@')[1]} ...")
            conn = psycopg2.connect(uri, connect_timeout=8)
            working_uri = uri
            print(f"[Success] Connected to Supabase via {uri.split('@')[1]}!")
            break
        except Exception as e:
            print(f"[Failed] {e}")

    if not conn:
        print("[Error] Could not connect to Supabase with provided credentials.")
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            conn.commit()
            print("[Success] All tables (sessions, conversations, memories, preferences) created successfully in Supabase!")
        conn.close()
    except Exception as e:
        print(f"[Migration Error] {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_and_migrate()
