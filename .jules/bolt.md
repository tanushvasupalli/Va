## 2024-10-25 - Supabase Connection Pooling
**Learning:** Supabase PostgreSQL connections currently use a new connection per query, adding TCP/TLS handshake latency overhead and causing database leaks.
**Action:** Implement a connection pool in `core/storage.py` using `psycopg2.pool.ThreadedConnectionPool` to reuse connections, while maintaining the context manager interface for ease of use.
