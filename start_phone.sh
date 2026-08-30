#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# WEDNESDAY AI - PHONE DAEMON RUNNER
# ============================================================

cd "$(dirname "$0")"

# Keep phone CPU alive when screen is off
termux-wake-lock 2>/dev/null

# Activate Virtual Environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "============================================================"
echo "          Starting Wednesday AI on Android Phone            "
echo "============================================================"

python run_all.py
