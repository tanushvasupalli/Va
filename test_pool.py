import psycopg2
from psycopg2.pool import ThreadedConnectionPool, PoolError
import time

class ConnectionProxy:
    def __init__(self, pool, max_retries=3, delay=0.1):
        self.pool = pool
        self.conn = None
        for _ in range(max_retries):
            try:
                conn = self.pool.getconn()
                if conn.closed:
                    self.pool.putconn(conn, close=True)
                    continue
                self.conn = conn
                self.conn.autocommit = True
                break
            except PoolError:
                time.sleep(delay)

        if not self.conn:
            raise PoolError("Connection pool exhausted after retries.")

    def close(self):
        if self.conn is not None:
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

# Mock test for proxy
print("Proxy defined successfully.")
