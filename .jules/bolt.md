## 2024-11-03 - Database Connection Pooling
**Learning:** Establishing new connections to a remote cloud database (like Supabase PostgreSQL) introduces significant TCP handshake and TLS latency on every request, creating a severe bottleneck when many quick queries are run. A standard context manager connection wrapper recreates connections repeatedly.
**Action:** Use a database connection pool (e.g., `psycopg2.pool.ThreadedConnectionPool`) along with a lazy instantiation wrapper and pre-ping checks (`conn.closed`) to maintain long-lived connections safely without degrading performance.
