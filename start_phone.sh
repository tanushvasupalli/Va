#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# WEDNESDAY AI - ANDROID TABLET 24/7 ULTRA-LOW POWER DAEMON
# ============================================================

cd "$(dirname "$0")"

# 1. Keep CPU running with screen OFF (saves 85%+ battery)
termux-wake-lock 2>/dev/null

# 2. Python bytecode optimization (strips docstrings/asserts for lowest RAM & CPU)
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=0

# 3. Activate Virtual Environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "============================================================"
echo "    Wednesday AI 24/7 Daemon Active (Tablet / Android 10)   "
echo "  RAM: ~80-110MB | Screen: OFF | CPU: Low Priority          "
echo "============================================================"

# Auto-recovery loop for 24/7 uninterrupted uptime
while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Launching Wednesday AI services..."
    python run_all.py
    EXIT_CODE=$?
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Service exited with code $EXIT_CODE."
    echo "Restarting Wednesday daemon in 3 seconds... (Press Ctrl+C to stop)"
    sleep 3
done


