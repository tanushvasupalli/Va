import psycopg2
conn = psycopg2.connect("postgresql://test:test@localhost/test")
conn.autocommit = True
try:
    with conn:
        pass
except Exception as e:
    print(f"Error: {e}")
