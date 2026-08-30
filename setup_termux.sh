#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# WEDNESDAY AI - AUTOMATED TERMUX INSTALLER (4GB RAM PHONES)
# ============================================================

echo "============================================================"
echo "    Installing Wednesday AI Assistant on Android Termux     "
echo "============================================================"

# 1. Update Termux repositories
echo "[1/5] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# 2. Install essential compilers and dependencies
echo "[2/5] Installing Python, Git, FFmpeg, and build tools..."
pkg install -y python git ffmpeg clang libffi openssl termux-api

# 3. Create Python Virtual Environment
echo "[3/5] Setting up Python virtual environment..."
python -m venv venv
source venv/bin/activate
pip install --upgrade pip

# 4. Install requirements
echo "[4/5] Installing Python libraries..."
pip install -r requirements.txt

# 5. Acquire Wake Lock
echo "[5/5] Acquiring Termux wake lock (prevents CPU sleep)..."
termux-wake-lock

echo ""
echo "============================================================"
echo " [SUCCESS] Installation Complete!"
echo " 1. Edit your credentials:  nano .env"
echo " 2. Start Wednesday:       ./start_phone.sh"
echo "============================================================"
