from core.storage import storage
import time

start = time.time()
print(f"Creating session 1...")
storage.create_session("Test1")
print(f"Creating session 2...")
storage.create_session("Test2")
print(f"Creating session 3...")
storage.create_session("Test3")
print(f"Done in {time.time() - start:.2f}s")
