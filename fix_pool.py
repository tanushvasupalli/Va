import psycopg2
from psycopg2.pool import ThreadedConnectionPool, PoolError
import time
import threading

class ConnectionProxy:
    """
    Safely wraps a psycopg2 pool connection, adding liveness checks, automatic retries,
    and returning the connection to the pool when garbage collected or exiting context.
    """
    def __init__(self, pool, max_retries=10, delay=0.5):
        self.pool = pool
        self.conn = None
        self._closed = False
        for _ in range(max_retries):
            try:
                conn = self.pool.getconn()
                # True liveness check
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                except Exception:
                    self.pool.putconn(conn, close=True)
                    continue

                self.conn = conn
                self.conn.autocommit = True
                break
            except PoolError:
                time.sleep(delay)

        if not self.conn:
            raise PoolError("Connection pool exhausted after retries.")

    def cursor(self, *args, **kwargs):
        """Returns a proxy cursor that keeps the connection proxy alive."""
        real_cursor = self.conn.cursor(*args, **kwargs)
        # Keep a reference to the connection proxy on the cursor to prevent GC
        real_cursor._connection_proxy = self
        return real_cursor

    def close(self):
        if not self._closed and self.conn is not None:
            self._closed = True
            self.pool.putconn(self.conn)
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def __getattr__(self, name):
        return getattr(self.conn, name)
