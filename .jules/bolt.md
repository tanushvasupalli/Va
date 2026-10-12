## 2024-05-19 - Supabase Connection Latency
**Learning:** Recreating a `psycopg2` connection to the Supabase Cloud PostgreSQL database for every query adds massive latency overhead (~200-500ms) due to repetitive TCP/TLS handshakes, and can leak connections under load.
**Action:** Use `psycopg2.pool.ThreadedConnectionPool` (and yield via `@contextmanager`) to reuse persistent connections across database interactions, significantly speeding up database reads/writes and memory operations.
