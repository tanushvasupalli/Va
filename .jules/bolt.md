## 2024-05-19 - Database Connection Pooling
**Learning:** Database connections are currently established per-request, leading to high latency from TLS handshakes. Since `psycopg2` is used with `autocommit=True`, the native connection context manager conflicts.
**Action:** Use a ThreadedConnectionPool for PostgreSQL connections to reuse them and reduce query latency. Create a proxy class to correctly handle connection release back to the pool via a `close` method when using a context manager.
