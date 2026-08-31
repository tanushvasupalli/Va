#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# WEDNESDAY AI - AUTOMATED ANDROID / TABLET INSTALLER (4GB RAM)
# ============================================================

echo "============================================================"
echo "    Installing Wednesday AI Assistant on Android Tablet     "
echo "============================================================"

# 1. Update Termux repositories
echo "[1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# 2. Install essential compilers, build tools, prebuilt binaries & utilities
echo "[2/6] Installing Python, Rust, Build Tools & Prebuilt Packages..."
pkg install -y python python-pip python-numpy python-pillow python-psutil python-cffi python-cryptography rust binutils postgresql git ffmpeg clang libffi openssl termux-api net-tools nmap

# 3. Create Python Virtual Environment with system site packages
echo "[3/6] Setting up optimized Python virtual environment..."
python -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# 4. Install requirements
echo "[4/6] Installing Python libraries (Cross-Platform)..."
pip install -r requirements.txt

# 5. Setup Termux:Boot (Auto-start on Tablet Reboot)
echo "[5/6] Configuring auto-start on boot (Termux:Boot)..."
mkdir -p ~/.termux/boot
CURRENT_DIR="$(pwd)"
cat << 'EOF' > ~/.termux/boot/start_wednesday.sh
#!/data/data/com.termux/files/usr/bin/bash
export PYTHONOPTIMIZE=1
termux-wake-lock 2>/dev/null
cd CURRENT_DIR_PLACEHOLDER
./start_phone.sh > wednesday_boot.log 2>&1 &
EOF
sed -i "s|CURRENT_DIR_PLACEHOLDER|$CURRENT_DIR|g" ~/.termux/boot/start_wednesday.sh
chmod +x ~/.termux/boot/start_wednesday.sh

# 6. Acquire Wake Lock
echo "[6/6] Acquiring Termux wake lock (prevents CPU sleep)..."
termux-wake-lock 2>/dev/null

echo ""
echo "============================================================"
echo " [SUCCESS] Android Tablet Installation Complete!"
echo " 1. Configure .env credentials:  nano .env"
echo " 2. Start Wednesday 24/7 daemon: ./start_phone.sh"
echo "============================================================"

