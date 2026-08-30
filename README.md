# Wednesday AI - Full-Fledged Autonomous AI Voice & Remote Assistant

Wednesday is a high-speed, intelligent AI assistant with persistent cloud memory, full web access, dynamic Model Context Protocol (MCP) server support, n8n workflow automations, remote PC file & power control, local network discovery, and a complete Telegram Bot interface with voice note support.

Designed to run smoothly on an **Android Phone (4GB RAM)** via Termux using only **~120MB RAM**, as well as on Windows/Linux.

---

## Key Features

1. 📱 **Mobile & Low-RAM Optimization (4GB RAM Phones)**: Runs 24/7 on Android Termux with under ~120MB RAM footprint using cloud-assisted intelligence.
2. 🤖 **Telegram Control Center & Voice Assistant**:
   - Send text or **voice notes** directly in Telegram.
   - Wednesday transcribes voice notes, reasons through the Brain, and replies back with both text and natural Edge-TTS audio.
   - Switch models (`/model`), customize system prompt (`/prompt`), manage memories (`/remember`), or run remote bash commands (`/exec`).
3. 💻 **Remote PC File & Power Access**:
   - Access your Windows PC files (search, read, list, and download) from your phone or Telegram.
   - Request any file in Telegram (e.g. `/getfile Desktop/report.pdf`) and Wednesday sends the document straight into your chat!
   - Control PC power: Sleep, Lock, Hibernate, Restart, or Wake-on-LAN.
4. 🔗 **n8n Automation & Workflows**:
   - Call n8n webhooks and REST API workflows dynamically.
   - Ask Wednesday to trigger smart home actions, send emails, manage Notion/Sheets, or post to Discord/Slack.
5. 🧩 **Model Context Protocol (MCP) Integration**:
   - Acts as an MCP client over SSE/HTTP and stdio.
   - Automatically discovers tools exposed by any MCP server and makes them callable by Gemini and Groq.
6. 🌐 **Local Network & IoT Management**:
   - Scan Wi-Fi subnet for connected devices and IP/MAC addresses (`/scan`).
   - Send Wake-on-LAN magic packets (`/wake`) to power on your PC remotely.

---

## Quick Setup Guide

### Step 1: Clone Repository & Configure `.env`
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Key environment variables:
* `GROQ_API_KEY`: For ultra-fast Whisper STT and reasoning.
* `GEMINI_API_KEY`: For Google Gemini 2.5 Flash.
* `TELEGRAM_BOT_TOKEN`: From `@BotFather` on Telegram.
* `TELEGRAM_ALLOWED_USER_ID`: From `@userinfobot` (restricts access to you).
* `N8N_BASE_URL` & `N8N_WEBHOOK_URL`: Your n8n instance.
* `PC_AGENT_URL`: Tailscale IP or LAN IP of your PC (e.g. `http://100.x.y.z:8085`).

---

### Step 2: Running on Android Phone (Termux)
1. Install **Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/).
2. In Android Settings $\rightarrow$ Apps $\rightarrow$ Termux $\rightarrow$ Battery $\rightarrow$ Set to **Unrestricted**.
3. Open Termux and run:
```bash
pkg install git -y
git clone https://github.com/tanushvasupalli/Va.git wednesday
cd wednesday
chmod +x setup_termux.sh start_phone.sh
./setup_termux.sh
```
4. Configure `.env` (`nano .env`) and start Wednesday:
```bash
./start_phone.sh
```

---

### Step 3: Running PC Companion on Windows (For PC Files & Power)
On your Windows PC:
1. Double-click `start_pc_companion.bat` (or run `python pc_companion.py`).
2. It starts listening on port `8085`.
3. *(Optional for Anywhere-Access)* Install **Tailscale** on both Phone and PC to access your PC files over 4G/5G mobile data.

---

## Telegram Bot Commands Cheat Sheet

| Command | Action | Example |
| :--- | :--- | :--- |
| `/status` | View real-time phone RAM, CPU, uptime, active model & PC status | `/status` |
| `/model <name>` | Switch active LLM on the fly | `/model gemini-2.5-flash` |
| `/prompt <text>` | Update persona/instructions dynamically | `/prompt Be witty and concise` |
| `/voice <name\|mute>` | Change TTS voice or mute voice audio | `/voice en-GB-SoniaNeural` |
| `/getfile <path>` | Fetch file from PC and send as Telegram document | `/getfile Desktop/resume.pdf` |
| `/pc <action>` | Control PC power | `/pc sleep` or `/pc lock` |
| `/wake` | Send Wake-on-LAN to wake up PC | `/wake` |
| `/scan` | Discover all active devices on local Wi-Fi | `/scan` |
| `/ping <host>` | Test connection to IP or hostname | `/ping 192.168.1.1` |
| `/n8n <workflow>` | Trigger an n8n automation workflow | `/n8n sync_notion {"done": true}` |
| `/mcp` | List connected MCP tools | `/mcp` |
| `/memories` | View long-term stored facts in Supabase | `/memories` |
| `/remember <t> <f>` | Store a new persistent memory | `/remember work Lead dev on AI` |
| `/exec <cmd>` | Execute terminal command on phone/host | `/exec git pull` |
| `/restart` | Hot-restart Wednesday service | `/restart` |

---

## Architecture

```
                       ┌────────────────────────────────────────┐
                       │           TELEGRAM (Mobile App)        │
                       │   • Text & Voice Notes                 │
                       │   • Control Commands (/model, /prompt) │
                       │   • Remote Execution & File Editing    │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │                     ANDROID PHONE (Termux - 4GB RAM)                            │
 │                                                                                 │
 │   ┌──────────────────────┐    ┌───────────────────┐    ┌────────────────────┐   │
 │   │  Telegram Bot Core   │───▶│  Wednesday Brain  │───▶│   MCP Client &     │   │
 │   │ (Voice Note Handler) │    │  (Gemini / Groq)   │    │  n8n Tool Bridge   │   │
 │   └──────────────────────┘    └─────────┬─────────┘    └──────────┬─────────┘   │
 │                                         │                         │             │
 └─────────────────────────────────────────┼─────────────────────────┼─────────────┘
                                           │                         │
            ┌──────────────────────────────┴───────┐                 │
            ▼                                      ▼                 ▼
 ┌──────────────────────┐              ┌────────────────┐  ┌───────────────────┐
 │   Google Gemini /    │              │    Supabase    │  │    n8n Engine /   │
 │      Groq API        │              │  Cloud Storage │  │    MCP Servers    │
 └──────────────────────┘              └────────────────┘  │ (Workflows, Tools)│
                                                           └───────────────────┘
```