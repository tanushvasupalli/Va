## 2024-05-18 - psycopg2 connection overhead and pooling
**Learning:** Establishing a new PostgreSQL connection (especially to a cloud provider like Supabase) for every database operation introduces significant latency (often 50-200ms+ per operation due to TCP/TLS handshakes).
**Action:** Use `psycopg2.pool.ThreadedConnectionPool` to maintain a pool of persistent connections, and yield them via a `@contextlib.contextmanager` wrapper. This avoids connection creation overhead on every query.
