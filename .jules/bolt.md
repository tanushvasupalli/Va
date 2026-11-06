
## 2025-05-19 - ThreadedConnectionPool Custom Wrapper Caveats
**Learning:** Overriding `__exit__` in a connection proxy to return connections to the pool can interfere with psycopg2's native transaction management when `conn.autocommit = True` is omitted or if `conn.__exit__` is not called properly. Also, lazy evaluation in `__init__` routines can result in inadvertent cross-process resource sharing. Shadowing properties like `closed` breaks liveness checks. Hardcoded database URIs are a massive security hazard.
**Action:** Be meticulous when wrapping stateful resources like DB connections; always wrap native `__enter__`/`__exit__` and safely forward attributes avoiding name collisions. Enforce complete secret removal and use environment variables instead.
