import os
import sys
import gc
import psutil
from pathlib import Path

LOCK_FILE = Path(__file__).resolve().parent.parent / "data" / "wednesday.lock"

def optimize_process():
    """Sets process priority to below normal to guarantee zero lag on other Windows apps/games."""
    try:
        p = psutil.Process(os.getpid())
        if sys.platform == "win32":
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception as e:
        print(f"[Optimizer Notice] Priority set: {e}")

def acquire_single_instance_lock() -> bool:
    """Ensures only one instance of Wednesday runs in the background at any time."""
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        if LOCK_FILE.exists():
            try:
                old_pid = int(LOCK_FILE.read_text().strip())
                if psutil.pid_exists(old_pid) and old_pid != os.getpid():
                    # Check if process is indeed python
                    proc = psutil.Process(old_pid)
                    if "python" in proc.name().lower():
                        print(f"[Optimizer] Another instance of Wednesday is already active (PID: {old_pid}). Exiting duplicate.")
                        return False
            except Exception:
                pass
        
        LOCK_FILE.write_text(str(os.getpid()))
        return True
    except Exception as e:
        print(f"[Optimizer Notice] Lock error: {e}")
        return True

def release_lock():
    """Cleans up lock file on shutdown."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass

def cleanup_memory():
    """Runs Python garbage collection to keep RAM usage minimal."""
    gc.collect()
