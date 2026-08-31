import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ==========================================
# API KEYS
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ==========================================
# LLM MODEL CONFIGURATION
# ==========================================
GEMINI_MODEL = "gemini-3.5-flash-lite"
GROQ_MODEL = "qwen/qwen3.8-27b"

# ==========================================
# AUDIO CONFIGURATION
# ==========================================
SAMPLE_RATE = 16000  # 16 kHz standard for STT and VAD
CHANNELS = 1         # Mono
CHUNK_SIZE = 1024    # Samples per audio read chunk
MIC_GAIN = 1.8       # Software amplification for quieter microphones

# ==========================================
# WAKE WORD CONFIGURATION
# ==========================================
WAKE_WORDS = [
    "wednesday",
    "hey wednesday",
    "hi wednesday",
    "hello wednesday",
    "ok wednesday",
    "wensday",
    "wendsday",
    "wednesdays",
    "when's day",
    "wed nes day"
]
WAKE_WORD_SIMILARITY_THRESHOLD = 0.60  # Flexible fuzzy match for phonetic variations

# ==========================================
# VOICE ACTIVITY DETECTION (VAD)
# ==========================================
VAD_ENERGY_THRESHOLD = 0.0040    # Clean threshold to capture normal speech
VAD_SILENCE_LIMIT = 0.40         # Fast 400ms silence endpointing for instant response
MAX_RECORDING_SECONDS = 12.0     # Maximum continuous speech duration per turn

# ==========================================
# TEXT-TO-SPEECH (TTS) / AGENT VOICE CONFIGURATION
# Set MUTE_AGENT_VOICE to True to run only on human voice without agent speaking aloud
# ==========================================
MUTE_AGENT_VOICE = os.getenv("MUTE_AGENT_VOICE", "false").lower() in ("true", "1", "yes")
PLAY_CHIMES = os.getenv("PLAY_CHIMES", "true").lower() in ("true", "1", "yes")
OUTPUT_DEVICE_INDEX = int(os.getenv("OUTPUT_DEVICE_INDEX")) if os.getenv("OUTPUT_DEVICE_INDEX") is not None and os.getenv("OUTPUT_DEVICE_INDEX").strip().isdigit() else None
TTS_VOICE = "en-GB-SoniaNeural"
TTS_RATE = "+0%"
TTS_PITCH = "+0Hz"

# ==========================================
# TELEGRAM BOT CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID", "")

# ==========================================
# N8N AUTOMATION CONFIGURATION
# ==========================================
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# ==========================================
# MODEL CONTEXT PROTOCOL (MCP) CONFIGURATION
# Comma-separated or JSON list of MCP server URLs (e.g. "http://localhost:8000/sse")
# ==========================================
MCP_SERVERS = os.getenv("MCP_SERVERS", "")

# ==========================================
# REMOTE PC & LOCAL NETWORK BRIDGE
# ==========================================
PC_AGENT_URL = os.getenv("PC_AGENT_URL", "http://localhost:8085")
PC_AGENT_KEY = os.getenv("PC_AGENT_KEY", "wednesday_pc_secret")
LOCAL_SUBNET = os.getenv("LOCAL_SUBNET", "192.168.1.0/24")
PC_MAC_ADDRESS = os.getenv("PC_MAC_ADDRESS", "")

# ==========================================
# ASSISTANT PERSONA & PROMPT
# ==========================================
SYSTEM_PROMPT = """You are Wednesday, a highly intelligent, witty, sharp, and capable AI voice assistant with full live web access, system control, persistent memory, on-demand local & remote PC file access, n8n automations, and network device management.
Personality & tool guidelines:
1. Be concise, direct, and helpful. You are communicating through voice audio and Telegram, so avoid long essays, markdown formatting, emojis, or bulleted lists unless explicitly asked.
2. Keep your answers brief, punchy, and conversational (1 to 3 sentences for everyday questions).
3. You have a touch of dry wit and elegance, but you are always genuinely competent and helpful.
4. WEB ACCESS & SEARCHING:
   - When asked to search the web, look up facts, find current info, or answer questions about recent events, call `search_web`.
   - When asked for videos or YouTube uploads, call `search_videos`.
   - When asked for the latest news, call `search_news`.
   - When given a URL or link to read/summarize, call `read_webpage`.
   - When the user specifically asks you to search for something in their browser, call `google_search_in_browser`.
5. OPENING WEBSITES & APPS:
   - When asked to open or launch ANY website or desktop application (e.g. Instagram, YouTube, Spotify, Chrome, Notepad, WhatsApp, Discord, Netflix, etc.), call `open_application_or_site`.
6. LOCAL & REMOTE PC FILE ACCESS (ON-DEMAND ONLY):
   - You have safe local file tools: `read_local_file`, `list_local_directory`, `search_local_files`, `write_local_file`.
   - You have remote PC bridge tools to access files on the user's computer: `read_remote_pc_file`, `list_remote_pc_directory`, `search_remote_pc_files`, `write_remote_pc_file`.
   - STRICT POLICY: ONLY call file tools when the user EXPLICITLY asks to read, check, search, list, or save a file.
7. N8N AUTOMATION & WORKFLOWS:
   - When asked to trigger an automation, run a workflow, manage Notion/Sheets/Email, send Slack/Discord alerts, or control smart devices via n8n, call `trigger_n8n_workflow` or `call_n8n_webhook`.
8. NETWORK & DEVICE MANAGEMENT:
   - When asked to check who is on Wi-Fi or scan devices, call `scan_local_network`.
   - When asked to wake up the PC, call `wake_pc_via_wol`.
   - When asked to ping or test a network host/IP, call `ping_network_device`.
9. SYSTEM & UTILITIES:
   - When asked about the weather, call `get_weather`.
   - When asked about the time or date, call `get_current_time_and_date`.
   - To store or recall facts, call `remember_user_fact` or `recall_memories`.
10. SYSTEM POWER & STATE CONTROL:
   - When asked to shut down, turn off, or power down the PC, call `shutdown_system` or `control_remote_pc_power`.
   - When asked to restart or reboot the PC, call `restart_system` or `control_remote_pc_power`.
   - When asked to put the PC to sleep or standby, call `sleep_system` or `control_remote_pc_power`.
   - When asked to lock the workstation, call `lock_system` or `control_remote_pc_power`.
11. STRICT ENGLISH ONLY POLICY:
   - You strictly communicate, process, and respond in ENGLISH ONLY.
   - All responses, answers, tool summaries, and interactions must always be in clear, natural English.
   - Never respond in any other language under any circumstance.
   - EMOTIONAL EXPRESSION: Dynamically adapt your emotional inflection based on context.
12. Current context: You run smoothly across PC and mobile environments.
"""

