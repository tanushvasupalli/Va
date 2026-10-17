
## 2024-10-17 - Connection Pooling for PostgreSQL
**Learning:** Establishing a fresh PostgreSQL connection for every DB operation introduces severe latency overhead due to repeated TCP/TLS handshakes, and can lead to connection leaks if not properly managed.
**Action:** Always use a connection pool (like `psycopg2.pool.ThreadedConnectionPool`) and yield connections via a context manager to maintain a pool of long-lived connections for reuse.
