
## 2024-05-17 - Connection Pooling with psycopg2 Autocommit
**Learning:** When using `psycopg2` ThreadedConnectionPool for cloud databases like Supabase, using `autocommit=True` breaks the standard connection `__enter__` context manager. Additionally, lazy initialization of the connection pool prevents import-time network hangs. A connection proxy that implements `__getattr__` and explicit cleanup via `close()`, `__enter__`, `__exit__`, and `__del__` is necessary. Pre-pinging `conn.closed` handles cloud environment disconnects.
**Action:** Implement `PooledConnectionProxy` to manage pool checkouts and return them safely using `putconn`, and lazily initialize the ThreadedConnectionPool in the manager class.
