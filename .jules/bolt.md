## 2024-05-24 - Context Manager Conflicts with Psycopg2 Autocommit
**Learning:** When using `psycopg2` with `autocommit=True`, the native connection context manager (`__enter__`) attempts to manage transactions (via `BEGIN` and `COMMIT`), causing conflict and errors when pooling.
**Action:** When building connection pools with autocommit enabled, wrap the connection in a proxy class that routes `__enter__` to return the connection directly and uses `__exit__` exclusively for returning the connection back to the pool via `putconn()`.
