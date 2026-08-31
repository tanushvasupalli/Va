# Running Wednesday AI 24/7 on Vivo Y15 (Android - 4GB RAM)

This guide details how to turn your **Vivo Y15 Android smartphone (4GB RAM)** into a **24/7 always-on autonomous server** and **local network hub** capable of discovering, monitoring, and controlling all devices on your Wi-Fi network.

---

## 🏗 System Architecture on Vivo Y15

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         VIVO Y15 (4GB RAM) - 24/7 SERVER                    │
 │                                                                             │
 │   • RAM Footprint: ~80-120 MB (Leaves 3.8 GB free for Android OS)          │
 │   • Power Consumption: ~2-5 Watts (Safe for 24/7 continuous charging)       │
 │   • Services:                                                               │
 │       1. Telegram Bot Core (Voice note & text command processor)            │
 │       2. FastAPI Web Dashboard (Accessible at http://<phone-ip>:8000)       │
 │       3. Local Network Scanner & Device Manager (/scan, /portscan, /wake)   │
 │       4. Remote PC Bridge & n8n / MCP Automation Gateway                    │
 └───────────────────────┬───────────────────────────────┬─────────────────────┘
                         │                               │
            (Local Wi-Fi Subnet)                (Internet / 4G / 5G)
                         │                               │
         ┌───────────────┴──────────────┐                ▼
         ▼                              ▼    ┌─────────────────────────┐
 ┌─────────────────────┐  ┌──────────────────┐│  Telegram Mobile / PC   │
 │   Windows Host PC   │  │ Smart Devices    ││  (Voice & Remote Mgmt) │
 │  • PC Companion     │  │ • Routers        │└─────────────────────────┘
 │  • File Downloads   │  │ • Smart Plugs/TV │
 │  • Wake-on-LAN      │  │ • Home Assistant │
 │  • Power & Scripts  │  │ • RTSP Cameras   │
 └─────────────────────┘  └──────────────────┘
```

---

## 📱 Step 1: Vivo Y15 & Funtouch OS 24/7 Optimization (Critical)

Vivo's **Funtouch OS** has aggressive power-saving policies that kill background processes when the screen turns off. Follow these exact steps to ensure uninterrupted 24/7 execution:

### 1. Enable High Background Power Consumption
* Open **Settings** $\rightarrow$ **Battery**.
* Tap **High background power consumption**.
* Find **Termux** and **Termux:Boot** and toggle both to **Allow / ON**.

### 2. Grant Autostart Permission
* Open **Settings** $\rightarrow$ **More Settings** $\rightarrow$ **Applications** $\rightarrow$ **Autostart**.
  *(Or open the built-in **iManager** app $\rightarrow$ **App manager** $\rightarrow$ **Autostart manager**)*
* Enable **Termux** and **Termux:Boot**.

### 3. Lock Termux in Recent Apps
* Open the **Termux** app.
* Swipe up / tap the Recent Apps button to view running applications.
* Long press or swipe down on the Termux preview card and tap the **Lock (Padlock)** icon. This prevents Funtouch OS from killing Termux during memory cleanups.

### 4. Keep Wi-Fi Active During Sleep
* Open **Settings** $\rightarrow$ **Wi-Fi** $\rightarrow$ **Advanced Settings** (or three dots menu).
* Ensure **Keep Wi-Fi on during sleep** is set to **Always**.

---

## 🚀 Step 2: Install Termux & Wednesday AI on Vivo Y15

### 1. Install Termux & Termux:Boot
> ⚠️ **Important**: Do NOT install Termux from Google Play Store (it is deprecated). Install from **F-Droid**:
> * [Download Termux on F-Droid](https://f-droid.org/en/packages/com.termux/)
> * [Download Termux:Boot on F-Droid](https://f-droid.org/en/packages/com.termux.boot/)

### 2. One-Line Setup
Open Termux on your Vivo Y15 and run:
```bash
pkg install -y git
git clone https://github.com/tanushvasupalli/Va.git wednesday
cd wednesday
chmod +x setup_termux.sh start_phone.sh
./setup_termux.sh
```

The script will automatically:
1. Install Python, FFmpeg, Clang, build tools, `net-tools`, and `nmap`.
2. Create an isolated Python virtual environment and install all dependencies.
3. Configure **Termux:Boot** so Wednesday starts automatically whenever your phone reboots or powers on.
4. Acquire an Android CPU wake-lock (`termux-wake-lock`).

---

## ⚙️ Step 3: Configure Environment Variables (`.env`)

Edit your `.env` configuration file on the phone:
```bash
nano .env
```

Configure your credentials:
```env
# AI Engine API Keys
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Telegram Remote Control
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_ALLOWED_USER_ID=your_telegram_user_id

# Windows PC Companion on LAN
PC_AGENT_URL=http://192.168.1.50:8085
PC_AGENT_KEY=wednesday_pc_secret
PC_MAC_ADDRESS=AA:BB:CC:DD:EE:FF

# Security PIN for Power Operations
POWER_SECURITY_PIN=2206
```
*(Press `Ctrl + O` then `Enter` to save, and `Ctrl + X` to exit nano)*

---

## ▶️ Step 4: Start Wednesday 24/7 Daemon

Start the daemon runner:
```bash
./start_phone.sh
```

Wednesday is now active and protected by an auto-restart supervisor loop!

---

## 🌐 Accessing & Controlling Local Network Devices

Your Vivo Y15 can now discover and interact with any device on your Wi-Fi network:

### 1. Subnet Discovery (`/scan`)
In Telegram, send:
```
/scan
```
Wednesday will sweep all 254 IP addresses on your local subnet in under 2 seconds, displaying:
* IP Address & Hostname
* MAC Address (for Wake-on-LAN)
* Open services (e.g. *Wednesday PC Companion*, *Router Web UI*, *Home Assistant*, *SSH*, *Smart TV*)

### 2. Port & Service Probing (`/portscan`)
To inspect what services are running on a specific device:
```
/portscan 192.168.1.50
```

### 3. Controlling Your Windows PC
On your Windows PC, double click `start_pc_companion.bat` (or run `python pc_companion.py`).
From your Vivo Y15 or Telegram:
* **Fetch any file**: `/getfile Desktop/project.pdf`
* **Send Wake-on-LAN**: `/wake`
* **Capture PC Screen**: `/screenshot`
* **Power Management**: `/pc sleep 2206` or `/pc lock`
* **Execute Terminal Commands**: Ask Wednesday: *"Run `git pull` on my PC"*

### 4. Smart Home & IoT HTTP Requests
Ask Wednesday via voice or text:
* *"Send an HTTP POST to `192.168.1.120/api/relay/1` with JSON `{'state': 'on'}`"*
* *"Trigger n8n workflow 'evening_lights'"*

### 5. Accessing the Web Dashboard from any PC/Phone
Open your browser on any laptop or phone connected to the same Wi-Fi:
```
http://<VIVO_Y15_IP>:8000
```
*(You can check your Vivo Y15's IP in Termux by running `ifconfig wlan0` or sending `/status` in Telegram).*

---

## 🛡 24/7 Hardware Best Practices for Vivo Y15

1. **Power Supply**: Keep the Vivo Y15 plugged into a standard 5V/1A or 5V/2A charger.
2. **Thermal Care**: Place the phone on a flat surface or stand in a well-ventilated spot away from direct sunlight.
3. **Screen Timeout**: Set screen lock timeout to 30 seconds or 1 minute; `termux-wake-lock` ensures the CPU and network stay fully active with the screen off.
