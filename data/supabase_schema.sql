-- =========================================================================
-- WEDNESDAY AI VOICE AGENT — SUPABASE CLOUD DATABASE SCHEMA
-- Copy and paste this script into your Supabase Dashboard -> SQL Editor -> Run
-- =========================================================================

-- 1. Create Sessions Table (for Multi-Conversation support)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Create Conversations Table (Stores multi-turn chat history & context window)
CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    source TEXT DEFAULT 'text', -- 'text' or 'voice'
    latency REAL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Create Long-Term Memories Table (Permanent facts, notes, user preferences)
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

-- 5. Seed default session if table is empty
INSERT INTO sessions (id, title)
VALUES ('default', 'Main Conversation')
ON CONFLICT (id) DO NOTHING;

-- 6. Enable Row Level Security (RLS) policies (Optional: allowing public access with anon key)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable all operations for anon" ON sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all operations for anon" ON conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all operations for anon" ON memories FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all operations for anon" ON preferences FOR ALL USING (true) WITH CHECK (true);
