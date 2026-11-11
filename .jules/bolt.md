
## 2025-02-23 - [Database Connection Pooling]
**Learning:** Continuous TCP/TLS handshakes for Supabase cloud connections cause latency. Standard `psycopg2.pool.ThreadedConnectionPool` needs a wrapper (`PooledConnectionProxy`) to manage context correctly when `autocommit=True` is used, and lazy initialization is crucial for testing without environment variables.
**Action:** Always wrap standard connection pools in proxy objects for `autocommit` context management and lazily instantiate them to prevent startup blocking.
