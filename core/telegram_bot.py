import os
import io
import sys
import time

# Guard against NoneType stdout/stderr when running silently via pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

import json
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import psutil

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import config

from core.brain import brain
from core.speaker import speaker
from core.storage import storage
from tools.n8n_tools import trigger_n8n_workflow, list_n8n_workflows
from tools.mcp_tools import list_connected_mcp_tools
from tools.pc_bridge_tools import (
    check_pc_status,
    download_pc_file_bytes,
    control_remote_pc_power,
    exec_remote_pc_command,
    fetch_pc_screenshot_bytes
)
from tools.network_tools import scan_local_network, port_scan_device, wake_pc_via_wol, ping_network_device

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING
)
logger = logging.getLogger("WednesdayTelegram")

START_TIME = time.time()

def is_authorized(user_id: int) -> bool:
    """Verifies if the sender is authorized to use Wednesday."""
    allowed = str(getattr(config, "TELEGRAM_ALLOWED_USER_ID", "")).strip()
    if not allowed:
        return True # Allow all if no ID restriction is set
    allowed_ids = [i.strip() for i in allowed.split(",") if i.strip()]
    return str(user_id) in allowed_ids

async def auth_guard(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else 0
    if not is_authorized(user_id):
        if update.message:
            await update.message.reply_text(
                f"⛔ Access Restricted.\nYour User ID: `{user_id}`\nAdd this to `TELEGRAM_ALLOWED_USER_ID` in .env to grant access.",
                parse_mode="Markdown"
            )
        return False
    return True

# ============================================================
# COMMAND HANDLERS
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    msg = """👋 *Hello, I am Wednesday.*

Your AI Assistant & Remote Control Center is active and ready.

*Conversation:*
• Send any text message to chat.
• Send a *voice note* for instant speech-to-speech interaction.

*Screen Vision & UI Control:*
• `/see` (or `/vision`) - Analyze laptop screen with AI Vision
• `/click <target>` - Click any named icon/button or `(x, y)` coordinates
• `/type <text>` - Type text into active window on laptop
• `/press <hotkey>` - Press shortcuts (`ctrl+c`, `win+d`, `alt+tab`)
• `/scroll <amount>` - Scroll screen up or down
• `/record [seconds]` - Record PC screen video (MP4) and send to Telegram
• `/screenshot` (or `/ss`) - Capture & send real-time PC screenshot

*Settings & Config:*
• `/config` - View active settings & variables
• `/config get <KEY>` - Inspect a specific setting
• `/config set <KEY> <VALUE>` - Update any setting live
• `/model <name>` - Switch active AI model
• `/prompt <text>` - Update system persona live
• `/voice <name|mute|unmute>` - Change TTS voice or toggle mute
• `/status` - Live health, RAM, CPU, active model

*Persistent Memory:*
• `/memories` - View stored facts in Supabase
• `/remember <topic> <fact>` - Save a new memory

*PC & Network Commands:*
• `/getfile <path>` - Fetch and download a file from PC
• `/pc <sleep|lock|restart|shutdown|status>` - Control PC power
• `/wake` - Send Wake-on-LAN to turn on PC
• `/scan` - Discover devices on local Wi-Fi
• `/ping <host>` - Ping an IP or domain

*Automation & MCP:*
• `/mcp [list|add|remove|refresh|call]` - Manage MCP servers & tools
• `/n8n <workflow> [data]` - Trigger n8n workflow
• `/exec <cmd>` - Run shell command on host
• `/help` - Show this guide
"""
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return

    # Memory & System stats
    mem = psutil.virtual_memory()
    proc = psutil.Process(os.getpid())
    proc_mem_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
    total_mem_gb = round(mem.total / (1024**3), 2)
    used_mem_gb = round((mem.total - mem.available) / (1024**3), 2)
    uptime_sec = int(time.time() - START_TIME)
    uptime_str = f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m {uptime_sec % 60}s"

    # PC companion check
    pc_info = check_pc_status()

    status_msg = f"""📊 *Wednesday System Status*

📱 *Phone / Host Node:*
• *Process RAM:* `{proc_mem_mb} MB`
• *System RAM:* `{used_mem_gb} GB / {total_mem_gb} GB` ({mem.percent}% used)
• *CPU Load:* `{psutil.cpu_percent(interval=0.1)}%`
• *Uptime:* `{uptime_str}`
• *Platform:* `{sys.platform}`

🧠 *AI Intelligence:*
• *Active Model:* `{brain.active_model}`
• *Voice Output:* `{'MUTED' if getattr(config, 'MUTE_AGENT_VOICE', False) else config.TTS_VOICE}`

💻 *Remote PC Companion:*
• {pc_info}
"""
    await update.message.reply_text(status_msg, parse_mode="Markdown")

async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text(
            f"Current active model: `{brain.active_model}`\n\nUsage: `/model gemini-2.5-flash` or `/model openai/gpt-oss-120b` or `/model llama-3.3-70b-versatile`",
            parse_mode="Markdown"
        )
        return
    new_model = " ".join(context.args).strip()
    brain.set_model(new_model)
    await update.message.reply_text(f"✅ Active model switched to: `{new_model}`", parse_mode="Markdown")

async def cmd_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text(f"Current System Prompt:\n\n`{config.SYSTEM_PROMPT[:500]}...`", parse_mode="Markdown")
        return
    new_prompt = update.message.text.partition(" ")[2].strip()
    config.SYSTEM_PROMPT = new_prompt
    await update.message.reply_text("✅ System prompt and personality updated live!", parse_mode="Markdown")

async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text(
            f"Current Voice: `{config.TTS_VOICE}` (Muted: `{speaker.muted}`)\n\nUsage: `/voice mute`, `/voice unmute`, or `/voice en-US-AriaNeural`",
            parse_mode="Markdown"
        )
        return
    arg = context.args[0].lower()
    if arg == "mute":
        speaker.set_muted(True)
        await update.message.reply_text("🔇 Agent voice responses muted.")
    elif arg == "unmute":
        speaker.set_muted(False)
        await update.message.reply_text("🔊 Agent voice responses unmuted.")
    else:
        config.TTS_VOICE = context.args[0]
        speaker.default_voice = context.args[0]
        await update.message.reply_text(f"🎙 Voice changed to: `{config.TTS_VOICE}`", parse_mode="Markdown")

async def cmd_remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/remember <topic> <fact to remember>`", parse_mode="Markdown")
        return
    topic = context.args[0]
    fact = " ".join(context.args[1:])
    storage.save_memory(topic, fact)
    await update.message.reply_text(f"🧠 Remembered under *{topic}*:\n_{fact}_", parse_mode="Markdown")

async def cmd_memories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    memories = storage.get_all_memories()
    if not memories:
        await update.message.reply_text("No persistent memories stored yet.")
        return
    lines = ["🧠 *Stored Persistent Memories:*"]
    for m in memories[:20]:
        lines.append(f"• *[{m.get('topic')}]* {m.get('fact')}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_getfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/getfile Desktop/notes.txt` or `/getfile C:/Users/Documents/report.pdf`", parse_mode="Markdown")
        return
    path_str = " ".join(context.args).strip()
    status_msg = await update.message.reply_text(f"⏳ Fetching '{path_str}' from your PC...")
    file_bytes, filename = download_pc_file_bytes(path_str)
    if not file_bytes:
        await status_msg.edit_text(f"❌ Failed to fetch file: {filename}")
        return
    try:
        await update.message.reply_document(
            document=io.BytesIO(file_bytes),
            filename=filename,
            caption=f"📄 {filename} retrieved from PC."
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Error sending file document: {e}")

async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    status_msg = await update.message.reply_text("📸 Capturing screenshot from your PC...")
    try:
        png_bytes, meta = fetch_pc_screenshot_bytes()
        if not png_bytes or len(png_bytes) < 100:
            await status_msg.edit_text(f"❌ Failed to capture screenshot: {meta}")
            return
        bio = io.BytesIO(png_bytes)
        bio.name = "screenshot.png"
        caption_text = f"📸 *PC Screenshot*\n_{meta}_"
        await update.message.reply_photo(
            photo=bio,
            caption=caption_text,
            parse_mode="Markdown"
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Error sending screenshot: {e}")

def send_screenshot_to_owner_sync(caption: str = "📸 PC Screenshot") -> str:
    """Synchronous trigger to capture and send a screenshot to Telegram owner chat."""
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "").strip()
    allowed = str(getattr(config, "TELEGRAM_ALLOWED_USER_ID", "")).strip()
    if not token or token == "your_telegram_bot_token_here":
        return "Telegram bot token is not configured in .env."
    if not allowed:
        return "TELEGRAM_ALLOWED_USER_ID is not configured in .env."
    user_id = allowed.split(",")[0].strip()
    try:
        png_bytes, meta = fetch_pc_screenshot_bytes()
        if not png_bytes or len(png_bytes) < 100:
            return f"Failed to capture screenshot: {meta}"
        
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        files = {"photo": ("screenshot.png", png_bytes, "image/png")}
        data = {
            "chat_id": user_id,
            "caption": f"{caption}\n_{meta}_",
            "parse_mode": "Markdown"
        }
        import requests
        r = requests.post(url, data=data, files=files, timeout=15)
        if r.status_code == 200:
            return "Screenshot captured and sent to your Telegram successfully."
        else:
            return f"Telegram API error: {r.text}"
    except Exception as e:
        return f"Failed to send screenshot: {e}"

def send_video_to_owner_sync(video_path: str, caption: str = "🎥 PC Screen Recording") -> str:
    """Synchronous trigger to transmit an MP4 video file to the authorized Telegram chat."""
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "").strip()
    allowed = str(getattr(config, "TELEGRAM_ALLOWED_USER_ID", "")).strip()
    if not token or token == "your_telegram_bot_token_here":
        return "Telegram bot token is not configured in .env."
    if not allowed:
        return "TELEGRAM_ALLOWED_USER_ID is not configured in .env."
    user_id = allowed.split(",")[0].strip()
    try:
        import os
        import requests
        if not os.path.exists(video_path):
            return f"Video file not found: {video_path}"
        
        url = f"https://api.telegram.org/bot{token}/sendVideo"
        with open(video_path, "rb") as vf:
            files = {"video": (os.path.basename(video_path), vf, "video/mp4")}
            data = {
                "chat_id": user_id,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            r = requests.post(url, data=data, files=files, timeout=60)
            if r.status_code == 200:
                return "Screen recording video sent to your Telegram successfully."
            else:
                return f"Telegram API error sending video: {r.text}"
    except Exception as e:
        return f"Failed to send video: {e}"

async def cmd_see(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyzes what is currently displayed on the PC screen with AI Vision."""
    if not await auth_guard(update):
        return
    prompt = " ".join(context.args).strip() if context.args else None
    status_msg = await update.message.reply_text("👁 Analyzing your laptop screen with AI Vision...")
    from tools.vision_tools import get_screen_view
    res = get_screen_view(prompt)
    await status_msg.edit_text(f"🖥 *Screen Analysis:*\n\n{res}", parse_mode="Markdown")

async def cmd_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clicks on a named UI icon/element or exact (x, y) coordinates."""
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage:\n• `/click Start button` (AI Vision)\n• `/click Google Chrome`\n• `/click 500 300` (Coordinates)", parse_mode="Markdown")
        return

    from tools.ui_control_tools import click_screen_item, click_coordinates
    args_str = " ".join(context.args).strip()
    
    # Check if two integer coordinates passed
    parts = args_str.split()
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        x, y = int(parts[0]), int(parts[1])
        status_msg = await update.message.reply_text(f"🖱 Clicking at ({x}, {y})...")
        res = click_coordinates(x, y)
        await status_msg.edit_text(f"✅ {res}")
        return

    status_msg = await update.message.reply_text(f"🔍 Locating and clicking '{args_str}' on screen...")
    res = click_screen_item(args_str)
    await status_msg.edit_text(f"🖱 {res}")

async def cmd_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Types text into the active focused window on the PC."""
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/type Hello World`", parse_mode="Markdown")
        return
    text = " ".join(context.args)
    from tools.ui_control_tools import type_text_into_ui
    res = type_text_into_ui(text)
    await update.message.reply_text(f"⌨️ {res}")

async def cmd_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simulates pressing keyboard shortcuts or keys."""
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/press ctrl+c` or `/press alt+tab` or `/press win+d` or `/press enter`", parse_mode="Markdown")
        return
    hotkey_str = " ".join(context.args).strip()
    from tools.ui_control_tools import press_hotkey
    res = press_hotkey(hotkey_str)
    await update.message.reply_text(f"⌨️ {res}", parse_mode="Markdown")

async def cmd_scroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scrolls the screen up or down."""
    if not await auth_guard(update):
        return
    amount = -3
    if context.args and (context.args[0].isdigit() or (context.args[0].startswith("-") and context.args[0][1:].isdigit())):
        amount = int(context.args[0])
    elif context.args and context.args[0].lower() in ("up", "top"):
        amount = 5
    elif context.args and context.args[0].lower() in ("down", "bottom"):
        amount = -5

    from tools.ui_control_tools import scroll_screen
    res = scroll_screen(amount)
    await update.message.reply_text(f"📜 {res}")

async def cmd_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Records the PC screen for N seconds and sends the MP4 video."""
    if not await auth_guard(update):
        return
    
    duration = 10
    if context.args and context.args[0].isdigit():
        duration = max(2, min(int(context.args[0]), 60))

    status_msg = await update.message.reply_text(f"🎥 Recording PC screen for {duration} seconds...")
    from tools.screen_recorder import record_screen_video
    video_path, msg = record_screen_video(duration_seconds=duration)
    
    if not video_path:
        await status_msg.edit_text(f"❌ {msg}")
        return

    try:
        await status_msg.edit_text("📤 Uploading screen recording video...")
        with open(video_path, "rb") as vf:
            await update.message.reply_video(
                video=vf,
                caption=f"🎥 *PC Screen Recording* ({duration}s)\n_{os.path.basename(video_path)}_",
                parse_mode="Markdown"
            )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Error sending video: {e}")

async def cmd_pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/pc <sleep|lock|restart|shutdown|status> [pin]`", parse_mode="Markdown")
        return
    action = context.args[0].lower().strip()
    pin = context.args[1].strip() if len(context.args) > 1 else None

    if action in ("sleep", "hibernate", "restart", "shutdown", "poweroff"):
        from core.security import verify_power_password
        if not pin:
            await update.message.reply_text(
                f"🔒 *Authentication Required:*\nTo execute PC `{action}`, please provide your 4-digit security PIN.\n\n*Usage:* `/pc {action} 2206`",
                parse_mode="Markdown"
            )
            return
        if not verify_power_password(pin):
            await update.message.reply_text("❌ *Authentication Failed:* Incorrect security PIN.", parse_mode="Markdown")
            return

    res = control_remote_pc_power(action, pin=pin)
    await update.message.reply_text(f"💻 *PC Command Result:*\n{res}", parse_mode="Markdown")

async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/pin <current_pin> <new_pin>`", parse_mode="Markdown")
        return
    current_pin, new_pin = context.args[0], context.args[1]
    from core.security import set_power_password
    ok, msg = set_power_password(current_pin, new_pin)
    emoji = "✅" if ok else "❌"
    await update.message.reply_text(f"{emoji} {msg}")

async def cmd_wake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    res = wake_pc_via_wol()
    await update.message.reply_text(f"⚡ {res}")

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    status_msg = await update.message.reply_text("🔍 Scanning local network for devices across subnet...")
    res = scan_local_network()
    await status_msg.edit_text(res, parse_mode="Markdown")

async def cmd_portscan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/portscan 192.168.1.50` or `/portscan 192.168.1.1 80,443,8080`", parse_mode="Markdown")
        return
    host = context.args[0]
    ports = context.args[1] if len(context.args) > 1 else None
    status_msg = await update.message.reply_text(f"🔍 Scanning open ports on `{host}`...", parse_mode="Markdown")
    res = port_scan_device(host, ports)
    await status_msg.edit_text(res, parse_mode="Markdown")

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/ping 192.168.1.1` or `/ping google.com`", parse_mode="Markdown")
        return
    res = ping_network_device(context.args[0])
    await update.message.reply_text(res)

async def cmd_n8n(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if not context.args:
        res = list_n8n_workflows()
        await update.message.reply_text(res)
        return
    workflow = context.args[0]
    payload = " ".join(context.args[1:]) if len(context.args) > 1 else None
    res = trigger_n8n_workflow(workflow, payload)
    await update.message.reply_text(f"⚡ *n8n Workflow Result:*\n{res}", parse_mode="Markdown")

async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return

    from core.config_manager import get_all_configs, get_config_value, set_config_value

    if not context.args:
        configs = get_all_configs(mask_secrets=True)
        lines = [
            "⚙️ *Wednesday AI - Configuration Center*",
            "",
            "🧠 *AI & Models:*",
            f"• `GROQ_MODEL`: `{configs.get('GROQ_MODEL')}`",
            f"• `GEMINI_MODEL`: `{configs.get('GEMINI_MODEL')}`",
            f"• `GROQ_API_KEY`: `{configs.get('GROQ_API_KEY')}`",
            f"• `GEMINI_API_KEY`: `{configs.get('GEMINI_API_KEY')}`",
            "",
            "🎙 *Voice & Audio:*",
            f"• `TTS_VOICE`: `{configs.get('TTS_VOICE')}`",
            f"• `MUTE_AGENT_VOICE`: `{configs.get('MUTE_AGENT_VOICE')}`",
            f"• `PLAY_CHIMES`: `{configs.get('PLAY_CHIMES')}`",
            "",
            "📱 *Security & Access:*",
            f"• `TELEGRAM_ALLOWED_USER_ID`: `{configs.get('TELEGRAM_ALLOWED_USER_ID')}`",
            f"• `TELEGRAM_BOT_TOKEN`: `{configs.get('TELEGRAM_BOT_TOKEN')}`",
            f"• `SUPABASE_URL`: `{configs.get('SUPABASE_URL')}`",
            "",
            "💻 *Remote PC & Network:*",
            f"• `PC_AGENT_URL`: `{configs.get('PC_AGENT_URL')}`",
            f"• `PC_AGENT_KEY`: `{configs.get('PC_AGENT_KEY')}`",
            f"• `LOCAL_SUBNET`: `{configs.get('LOCAL_SUBNET')}`",
            f"• `PC_MAC_ADDRESS`: `{configs.get('PC_MAC_ADDRESS')}`",
            "",
            "🔗 *Integrations & MCP:*",
            f"• `N8N_BASE_URL`: `{configs.get('N8N_BASE_URL')}`",
            f"• `MCP_SERVERS`: `{configs.get('MCP_SERVERS')}`",
            "",
            "💡 *Config Commands:*",
            "• `/config get <KEY>` - Inspect a setting",
            "• `/config set <KEY> <VALUE>` - Update any setting live"
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    subcmd = context.args[0].lower()

    if subcmd == "get":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/config get <KEY>` (e.g. `/config get GROQ_MODEL`)", parse_mode="Markdown")
            return
        key = context.args[1].upper()
        val = get_config_value(key, mask_secrets=False)
        await update.message.reply_text(f"🔑 *{key}* = `{val}`", parse_mode="Markdown")

    elif subcmd == "set":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/config set <KEY> <VALUE>` or `/config set KEY=VALUE`", parse_mode="Markdown")
            return
        
        rest = " ".join(context.args[1:]).strip()
        if "=" in rest and not (" " in rest and rest.find("=") > rest.find(" ")):
            k, _, v = rest.partition("=")
        else:
            parts = rest.split(None, 1)
            k = parts[0]
            v = parts[1] if len(parts) > 1 else ""
        
        ok, msg = set_config_value(k, v)
        emoji = "✅" if ok else "❌"
        await update.message.reply_text(f"{emoji} {msg}", parse_mode="Markdown")

    else:
        if "=" in context.args[0]:
            k, _, v = " ".join(context.args).partition("=")
            ok, msg = set_config_value(k, v)
            emoji = "✅" if ok else "❌"
            await update.message.reply_text(f"{emoji} {msg}", parse_mode="Markdown")
        else:
            await update.message.reply_text("Unknown config command. Usage:\n• `/config`\n• `/config get <KEY>`\n• `/config set <KEY> <VALUE>`", parse_mode="Markdown")

async def cmd_mcp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return

    from core.config_manager import get_mcp_servers, add_mcp_server, remove_mcp_server
    from tools.mcp_tools import call_mcp_tool_direct
    from core.mcp_client import mcp_client

    if not context.args or context.args[0].lower() in ("list", "status"):
        servers = get_mcp_servers()
        tools = mcp_client.refresh_tools()

        lines = ["🧩 *Model Context Protocol (MCP) Dashboard*", ""]
        lines.append("*Connected MCP Servers:*")
        if servers:
            for idx, s in enumerate(servers, 1):
                lines.append(f"{idx}. `{s}`")
        else:
            lines.append("_(No external MCP servers configured)_")

        lines.append("")
        lines.append(f"*Discovered Tools ({len(tools)}):*")
        if tools:
            for name, data in list(tools.items())[:25]:
                desc = data.get("schema", {}).get("description", "No description")
                server = data.get("server_url", "")
                lines.append(f"• *{name}* (`{server}`): {desc}")
        else:
            lines.append("_(No tools discovered. Connect a server with `/mcp add <URL>`)_")

        lines.extend([
            "",
            "🛠 *MCP Commands:*",
            "• `/mcp add <URL>` - Connect new MCP server",
            "• `/mcp remove <URL or Index>` - Disconnect server",
            "• `/mcp refresh` - Pull latest tools",
            "• `/mcp call <tool_name> [json_args]` - Test tool"
        ])
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    sub = context.args[0].lower()

    if sub in ("add", "connect"):
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/mcp add <server_url>` (e.g. `/mcp add http://localhost:8000/sse`)", parse_mode="Markdown")
            return
        url = context.args[1].strip()
        status_msg = await update.message.reply_text(f"⏳ Connecting to MCP server `{url}`...", parse_mode="Markdown")
        ok, msg = add_mcp_server(url)
        await status_msg.edit_text(msg, parse_mode="Markdown")

    elif sub in ("remove", "rm", "del", "delete", "disconnect"):
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/mcp remove <server_url or index_number>`", parse_mode="Markdown")
            return
        target = context.args[1].strip()
        ok, msg = remove_mcp_server(target)
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif sub == "refresh":
        status_msg = await update.message.reply_text("🔄 Refreshing MCP tool schemas...")
        tools = mcp_client.refresh_tools()
        await status_msg.edit_text(f"✅ Refreshed! Total {len(tools)} MCP tools currently active.")

    elif sub == "call":
        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/mcp call <tool_name> [json_args]`\nExample: `/mcp call get_weather {\"city\":\"London\"}`", parse_mode="Markdown")
            return
        tool_name = context.args[1].strip()
        args_str = " ".join(context.args[2:]).strip() if len(context.args) > 2 else "{}"
        status_msg = await update.message.reply_text(f"⚡ Executing MCP Tool `{tool_name}`...", parse_mode="Markdown")
        res = call_mcp_tool_direct(tool_name, args_str)
        await status_msg.edit_text(f"🛠 *MCP Tool Output ({tool_name}):*\n```\n{res[:3500]}\n```", parse_mode="Markdown")

    else:
        await update.message.reply_text("Unknown MCP command. Usage:\n• `/mcp list`\n• `/mcp add <URL>`\n• `/mcp remove <URL>`\n• `/mcp refresh`\n• `/mcp call <tool> [args]`", parse_mode="Markdown")

async def cmd_n8n(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return

    from tools.n8n_tools import (
        search_n8n_templates,
        search_n8n_nodes,
        get_n8n_node_schema,
        trigger_n8n_workflow,
        list_n8n_workflows
    )

    if not context.args:
        msg = (
            "⚡ *n8n Automation & MCP Suite*\n\n"
            "• `/n8n templates <query>` - Search 2,709+ n8n workflow templates\n"
            "• `/n8n nodes <query>` - Search 2,616+ workflow integration nodes\n"
            "• `/n8n schema <node_type>` - Inspect node schema & operations\n"
            "• `/n8n list` - List active workflows on your connected n8n instance\n"
            "• `/n8n run <name/id> [payload]` - Trigger an automation workflow"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    sub = context.args[0].lower()
    query = " ".join(context.args[1:]).strip()

    if sub in ("template", "templates", "tpl"):
        if not query:
            query = "automation"
        status_msg = await update.message.reply_text(f"🔍 Searching 2,700+ n8n templates for *'{query}'*...", parse_mode="Markdown")
        res = search_n8n_templates(query=query)
        await status_msg.edit_text(f"📦 *n8n Templates for '{query}':*\n```\n{res[:3500]}\n```", parse_mode="Markdown")

    elif sub in ("node", "nodes", "search"):
        if not query:
            await update.message.reply_text("Usage: `/n8n nodes <query>` (e.g. `/n8n nodes telegram` or `/n8n nodes slack`)", parse_mode="Markdown")
            return
        status_msg = await update.message.reply_text(f"🔍 Searching 2,616+ n8n nodes for *'{query}'*...", parse_mode="Markdown")
        res = search_n8n_nodes(query=query)
        await status_msg.edit_text(f"🔌 *n8n Nodes matching '{query}':*\n```\n{res[:3500]}\n```", parse_mode="Markdown")

    elif sub in ("schema", "node_info", "info"):
        if not query:
            await update.message.reply_text("Usage: `/n8n schema <node_type>` (e.g. `/n8n schema n8n-nodes-base.telegram`)", parse_mode="Markdown")
            return
        status_msg = await update.message.reply_text(f"🔍 Inspecting schema for *'{query}'*...", parse_mode="Markdown")
        res = get_n8n_node_schema(node_type=query)
        await status_msg.edit_text(f"📋 *n8n Node Schema for '{query}':*\n```\n{res[:3500]}\n```", parse_mode="Markdown")

    elif sub in ("list", "workflows"):
        status_msg = await update.message.reply_text("📋 Fetching active workflows from n8n instance...", parse_mode="Markdown")
        res = list_n8n_workflows()
        await status_msg.edit_text(f"⚡ *Connected n8n Workflows:*\n{res}", parse_mode="Markdown")

    elif sub in ("run", "trigger", "exec"):
        if not query:
            await update.message.reply_text("Usage: `/n8n run <workflow_name_or_id> [json_payload]`", parse_mode="Markdown")
            return
        parts = query.split(maxsplit=1)
        wf_name = parts[0]
        payload = parts[1] if len(parts) > 1 else "{}"
        status_msg = await update.message.reply_text(f"🚀 Triggering n8n workflow *'{wf_name}'*...", parse_mode="Markdown")
        res = trigger_n8n_workflow(wf_name, payload)
        await status_msg.edit_text(f"✅ *Execution Result:*\n{res}", parse_mode="Markdown")

    else:
        await update.message.reply_text("Unknown n8n command. Use `/n8n` to see available options.", parse_mode="Markdown")

async def cmd_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/exec uptime` or `/exec git status`", parse_mode="Markdown")
        return
    cmd_str = update.message.text.partition(" ")[2].strip()
    try:
        proc = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=20)
        output = proc.stdout if proc.stdout else proc.stderr
        res = output.strip() if output else "Command finished with no output."
        await update.message.reply_text(f"```\n{res[:3500]}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Execution error: {e}")

async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    await update.message.reply_text("🔄 Restarting Wednesday service...")
    os._exit(0)

# ============================================================
# TEXT & VOICE MESSAGE HANDLERS
# ============================================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    user_text = update.message.text
    if not user_text or not user_text.strip():
        return

    # Check if user asks for a PC file directly (e.g. "send me / download myfile.pdf from PC")
    if any(k in user_text.lower() for k in ["send me the file", "download file", "send file from pc", "get file from pc"]):
        # Extract potential filename
        words = user_text.split()
        for w in words:
            if "." in w and len(w) > 3 and not w.startswith("http"):
                file_bytes, filename = download_pc_file_bytes(w)
                if file_bytes:
                    await update.message.reply_document(
                        document=io.BytesIO(file_bytes),
                        filename=filename,
                        caption=f"📄 {filename} retrieved from PC."
                    )
                    return

    # Check if user asks for screen recording directly
    clean_lower = user_text.lower().strip()
    rec_triggers = ["record screen", "record my screen", "record video", "screen recording", "capture video", "screen record"]
    if any(t in clean_lower for t in rec_triggers) and not any(k in clean_lower for k in ["how to", "what is", "code", "explain"]):
        import re
        dur_match = re.search(r"(\d+)\s*(?:seconds?|secs?|s)", clean_lower)
        dur = int(dur_match.group(1)) if dur_match else 10
        dur = max(2, min(dur, 60))
        status_msg = await update.message.reply_text(f"🎥 Recording PC screen for {dur} seconds...")
        from tools.screen_recorder import record_screen_video
        video_path, msg = record_screen_video(duration_seconds=dur)
        if video_path and os.path.exists(video_path):
            with open(video_path, "rb") as vf:
                await update.message.reply_video(video=vf, caption=f"🎥 *PC Screen Recording* ({dur}s)", parse_mode="Markdown")
            await status_msg.delete()
            return
        else:
            await status_msg.edit_text(f"❌ {msg}")
            return

    # Check if user asks for screenshot directly
    ss_triggers = ["take a screenshot", "take screenshot", "send me a screenshot", "send screenshot", "capture screen", "capture desktop", "screenshot my pc", "screenshot"]
    if any(t in clean_lower for t in ss_triggers) and not any(k in clean_lower for k in ["how to", "what is", "code", "explain"]):
        status_msg = await update.message.reply_text("📸 Capturing screenshot from your PC...")
        png_bytes, meta = fetch_pc_screenshot_bytes()
        if png_bytes and len(png_bytes) > 100:
            bio = io.BytesIO(png_bytes)
            bio.name = "screenshot.png"
            await update.message.reply_photo(photo=bio, caption=f"📸 *PC Screenshot*\n_{meta}_", parse_mode="Markdown")
            await status_msg.delete()
            return
        else:
            await status_msg.edit_text(f"❌ Failed to capture screenshot: {meta}")
            return

    # Brain reasoning
    sender_name = update.effective_user.first_name if update.effective_user else "User"
    response = brain.query(user_text, source="telegram", session_id="telegram", speaker=sender_name, is_owner=True)
    if not response:
        response = "Done."

    # Send text reply
    await update.message.reply_text(response)

    # If voice is enabled, also generate and send voice note audio!
    if not speaker.muted:
        try:
            audio_bytes = speaker.generate_audio_bytes(response)
            if audio_bytes and len(audio_bytes) > 500:
                await update.message.reply_voice(voice=io.BytesIO(audio_bytes))
        except Exception as e:
            logger.warning(f"Failed to send voice reply: {e}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    status_msg = await update.message.reply_text("🎧 Listening...")

    try:
        # Download voice file
        voice_file = await context.bot.get_file(voice.file_id)
        voice_bytes = await voice_file.download_as_bytearray()

        # Transcribe audio using Groq Whisper if available, or SpeechRecognition
        transcribed_text = ""
        if config.GROQ_API_KEY and config.GROQ_API_KEY != "your_groq_api_key_here":
            try:
                from groq import Groq
                client = Groq(api_key=config.GROQ_API_KEY)
                bio = io.BytesIO(voice_bytes)
                bio.name = "audio.ogg"
                transcription = client.audio.transcriptions.create(
                    file=bio,
                    model="whisper-large-v3",
                    response_format="text"
                )
                transcribed_text = str(transcription).strip()
            except Exception as ge:
                logger.warning(f"Groq transcription notice: {ge}")

        if not transcribed_text:
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with io.BytesIO(voice_bytes) as audio_file:
                    with sr.AudioFile(audio_file) as source:
                        audio_data = r.record(source)
                        transcribed_text = r.recognize_google(audio_data)
            except Exception:
                pass

        if not transcribed_text:
            await status_msg.edit_text("Sorry, I could not transcribe that audio note clearly.")
            return

        # Check voice for screenshot trigger
        clean_voice = transcribed_text.lower().strip()
        ss_triggers = ["take a screenshot", "take screenshot", "send me a screenshot", "send screenshot", "capture screen", "capture desktop", "screenshot my pc", "screenshot"]
        if any(t in clean_voice for t in ss_triggers) and not any(k in clean_voice for k in ["how to", "what is"]):
            await status_msg.edit_text(f"🗣 _{transcribed_text}_", parse_mode="Markdown")
            png_bytes, meta = fetch_pc_screenshot_bytes()
            if png_bytes and len(png_bytes) > 100:
                bio = io.BytesIO(png_bytes)
                bio.name = "screenshot.png"
                await update.message.reply_photo(photo=bio, caption=f"📸 *PC Screenshot*\n_{meta}_", parse_mode="Markdown")
                return

        # Query Brain
        sender_name = update.effective_user.first_name if update.effective_user else "User"
        await status_msg.edit_text(f"🗣 _{transcribed_text}_", parse_mode="Markdown")

        response = brain.query(transcribed_text, source="voice_telegram", session_id="telegram", speaker=sender_name, is_owner=True)
        if not response:
            response = "Done."

        # Send text reply
        await update.message.reply_text(response)

        # Send voice reply
        if not speaker.muted:
            try:
                audio_bytes = speaker.generate_audio_bytes(response)
                if audio_bytes and len(audio_bytes) > 500:
                    await update.message.reply_voice(voice=io.BytesIO(audio_bytes))
            except Exception as ve:
                logger.warning(f"Failed to generate voice note reply: {ve}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error processing voice note: {e}")

async def post_init(application: Application):
    """Registers the bot command autocomplete menu with Telegram."""
    commands = [
        BotCommand("start", "Start assistant & view help menu"),
        BotCommand("status", "Check phone RAM, CPU, uptime & PC status"),
        BotCommand("see", "Analyze PC screen with AI Vision"),
        BotCommand("screenshot", "Capture and send real-time PC screenshot"),
        BotCommand("getfile", "Fetch and download a file from PC"),
        BotCommand("scan", "Discover all devices on local Wi-Fi"),
        BotCommand("portscan", "Scan open ports & services on target IP"),
        BotCommand("wake", "Send Wake-on-LAN to wake up PC"),
        BotCommand("ping", "Ping an IP address or domain"),
        BotCommand("pc", "Control PC power (sleep, lock, restart, status)"),
        BotCommand("model", "Switch active AI model (Gemini / Groq)"),
        BotCommand("prompt", "Update system persona / instructions live"),
        BotCommand("voice", "Change TTS voice or toggle mute"),
        BotCommand("remember", "Save a persistent fact into long-term memory"),
        BotCommand("memories", "View stored long-term memories"),
        BotCommand("n8n", "Trigger an n8n automation workflow"),
        BotCommand("mcp", "List connected Model Context Protocol tools"),
        BotCommand("click", "Click UI element or (x, y) coordinates on PC"),
        BotCommand("type", "Type text into active focused window on PC"),
        BotCommand("press", "Simulate hotkey shortcut on PC"),
        BotCommand("scroll", "Scroll the PC screen up or down"),
        BotCommand("record", "Record PC screen video (MP4)"),
        BotCommand("config", "Inspect and update settings live"),
        BotCommand("pin", "Change the 4-digit security power PIN"),
        BotCommand("exec", "Run shell command on host"),
        BotCommand("restart", "Hot-restart Wednesday bot services")
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info(f"Registered {len(commands)} commands in Telegram command menu.")
    except Exception as e:
        logger.warning(f"Failed to set bot commands in Telegram: {e}")

def create_telegram_application() -> Optional[Application]:
    """Builds and configures the Telegram Bot application instance."""
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "your_telegram_bot_token_here":
        print("[Telegram Bot] TELEGRAM_BOT_TOKEN not configured. Telegram bot interface disabled.")
        return None

    app = Application.builder().token(token).post_init(post_init).build()

    # Register commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("see", cmd_see))
    app.add_handler(CommandHandler("vision", cmd_see))
    app.add_handler(CommandHandler("screen", cmd_see))
    app.add_handler(CommandHandler("click", cmd_click))
    app.add_handler(CommandHandler("type", cmd_type))
    app.add_handler(CommandHandler("press", cmd_press))
    app.add_handler(CommandHandler("scroll", cmd_scroll))
    app.add_handler(CommandHandler("record", cmd_record))
    app.add_handler(CommandHandler("rec", cmd_record))
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("settings", cmd_config))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("prompt", cmd_prompt))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(CommandHandler("remember", cmd_remember))
    app.add_handler(CommandHandler("memories", cmd_memories))
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))
    app.add_handler(CommandHandler("ss", cmd_screenshot))
    app.add_handler(CommandHandler("getfile", cmd_getfile))
    app.add_handler(CommandHandler("pc", cmd_pc))
    app.add_handler(CommandHandler("wake", cmd_wake))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("network", cmd_scan))
    app.add_handler(CommandHandler("portscan", cmd_portscan))
    app.add_handler(CommandHandler("ports", cmd_portscan))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("n8n", cmd_n8n))
    app.add_handler(CommandHandler("mcp", cmd_mcp))
    app.add_handler(CommandHandler("exec", cmd_exec))
    app.add_handler(CommandHandler("pin", cmd_pin))
    app.add_handler(CommandHandler("restart", cmd_restart))

    # Register text and voice handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    return app

def run_telegram_bot():
    """Runs the Telegram Bot in a blocking polling loop."""
    app = create_telegram_application()
    if not app:
        return
    print(f"""
============================================================
           WEDNESDAY TELEGRAM BOT ACTIVE & POLLING           
============================================================
 [Status] Ready for Voice Notes & Remote Commands
 [Authorized User] {config.TELEGRAM_ALLOWED_USER_ID or 'All (Open)'}
============================================================
""")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    run_telegram_bot()
