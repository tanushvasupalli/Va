import os
import io
import sys
import time
import json
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

import psutil
from pathlib import Path

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
    exec_remote_pc_command
)
from tools.network_tools import scan_local_network, wake_pc_via_wol, ping_network_device

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

*System Commands:*
• `/status` - Live phone & PC health, RAM, CPU, active models
• `/model <name>` - Switch AI model (Gemini / Groq)
• `/prompt <text>` - Update system persona on the fly
• `/voice <name|mute|unmute>` - Change TTS voice or toggle mute
• `/memories` - View stored facts in Supabase
• `/remember <topic> <fact>` - Save a persistent memory

*PC & Network Commands:*
• `/getfile <path>` - Fetch and download a file from PC
• `/pc <sleep|lock|restart|shutdown|status>` - Control PC power
• `/wake` - Send Wake-on-LAN to turn on PC
• `/scan` - Discover devices on local Wi-Fi
• `/ping <host>` - Ping an IP or domain

*Automation & MCP:*
• `/n8n <workflow> [data]` - Trigger n8n workflow
• `/mcp` - List connected MCP tools
• `/exec <bash>` - Run command on phone/server
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

async def cmd_pc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    action = context.args[0] if context.args else "status"
    res = control_remote_pc_power(action)
    await update.message.reply_text(f"💻 *PC Command Result:*\n{res}", parse_mode="Markdown")

async def cmd_wake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    res = wake_pc_via_wol()
    await update.message.reply_text(f"⚡ {res}")

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    status_msg = await update.message.reply_text("🔍 Scanning local network for devices...")
    res = scan_local_network()
    await status_msg.edit_text(res)

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

async def cmd_mcp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await auth_guard(update):
        return
    res = list_connected_mcp_tools()
    await update.message.reply_text(res)

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

def create_telegram_application() -> Optional[Application]:
    """Builds and configures the Telegram Bot application instance."""
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "your_telegram_bot_token_here":
        print("[Telegram Bot] TELEGRAM_BOT_TOKEN not configured. Telegram bot interface disabled.")
        return None

    app = Application.builder().token(token).build()

    # Register commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("prompt", cmd_prompt))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(CommandHandler("remember", cmd_remember))
    app.add_handler(CommandHandler("memories", cmd_memories))
    app.add_handler(CommandHandler("getfile", cmd_getfile))
    app.add_handler(CommandHandler("pc", cmd_pc))
    app.add_handler(CommandHandler("wake", cmd_wake))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("network", cmd_scan))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("n8n", cmd_n8n))
    app.add_handler(CommandHandler("mcp", cmd_mcp))
    app.add_handler(CommandHandler("exec", cmd_exec))
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
