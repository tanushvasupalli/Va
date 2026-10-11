## 2024-10-24 - Database Connection Pooling
**Learning:** Recreating a Supabase (or any PostgreSQL) connection using `psycopg2.connect` for every query incurs massive latency overhead from repeated TCP/TLS handshakes, especially when querying frequently.
**Action:** Always use connection pooling (e.g., `psycopg2.pool.ThreadedConnectionPool`) and yield connections via a context manager to eliminate handshake latency and prevent connection leaks.
