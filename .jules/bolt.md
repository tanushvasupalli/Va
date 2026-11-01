## 2024-05-24 - ThreadedConnectionPool Proxy
**Learning:** psycopg2.pool.ThreadedConnectionPool requires pre-ping mechanism and proxy classes to gracefully handle proxy state with autocommit=True, otherwise context managers break normal connection state behavior causing application failures.
**Action:** Use a PooledConnectionProxy class when working with psycopg2 connection pools and autocommit, making sure the connection is properly closed into the pool using putconn on __exit__.

## 2024-05-24 - ThreadedConnectionPool Pre-Ping Proxy
**Learning:** psycopg2.pool.ThreadedConnectionPool lacks automatic pre-ping and blocking queues. In order to reliably use it with autocommit=True, a proxy class must be implemented that performs liveness checks on connections retrieved from the pool, explicitly manages the autocommit state, and explicitly calls `putconn` within `__exit__`. Otherwise, context managers will break.
**Action:** Use a PooledConnectionProxy when using psycopg2 pool with autocommit. Ensure it has a pre-ping retry loop and implements __exit__ closing mechanism.
