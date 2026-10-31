## 2026-10-31 - Database Connection Pooling
**Learning:** Opening a new psycopg2 connection to Supabase for every query causes massive latency overhead due to repeated TCP/TLS handshakes.
**Action:** Always use psycopg2.pool.ThreadedConnectionPool with a proxy wrapper to handle autocommit and context managers cleanly.
