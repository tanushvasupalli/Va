## 2024-05-24 - Database Connection Pool Bottleneck
**Learning:** Constant TCP/TLS handshakes to Supabase PostgreSQL on every request cause massive latency overhead and potential connection leaks, as they were newly created and torn down continuously.
**Action:** Use a lazily-initialized `psycopg2.pool.ThreadedConnectionPool` instance variable coupled with a robust ConnectionProxy wrapper (for liveness pre-pings `conn.closed` and retry logic) to reuse connections safely and minimize request latency overhead.
