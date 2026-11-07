## 2024-05-14 - psycopg2 Pool and Autocommit Context Manager Conflict
**Learning:** `psycopg2` standard connection pool doesn't natively integrate with `autocommit=True` inside Python's `with` statement because standard connections try to manage transactions in `__enter__`.
**Action:** When migrating to a `ThreadedConnectionPool`, always implement a proxy wrapper (like `PooledConnectionProxy`) to manage liveness checks, safely set `autocommit`, and ensure the connection is correctly returned to the pool using `putconn()` on exit or destruction.
