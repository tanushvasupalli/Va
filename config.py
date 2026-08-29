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
GEMINI_MODEL = "gemini-3.6-flash"
GROQ_MODEL = "openai/gpt-oss-120b"

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
# ASSISTANT PERSONA & PROMPT
# ==========================================
SYSTEM_PROMPT = """You are Wednesday, a highly intelligent, witty, sharp, and capable AI voice assistant with full live web access, system control, persistent memory, and on-demand local file access.
Personality & tool guidelines:
1. Be concise, direct, and helpful. You are communicating through voice audio, so avoid long essays, markdown formatting, emojis, or bulleted lists unless explicitly asked.
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
6. LOCAL FILE ACCESS (ON-DEMAND ONLY):
   - You have safe local file tools: `read_local_file`, `list_local_directory`, `search_local_files`, `write_local_file`.
   - STRICT POLICY: ONLY call local file tools when the user EXPLICITLY asks to read, check, search, list, or save a local file on their computer. Never browse or read local files unprompted.
7. SYSTEM & UTILITIES:
   - When asked about the weather, call `get_weather`.
   - When asked about the time or date, call `get_current_time_and_date`.
   - To store or recall facts, call `remember_user_fact` or `recall_memories`.
8. SYSTEM POWER & STATE CONTROL:
   - When asked to shut down, turn off, or power down the PC, call `shutdown_system`.
   - When asked to restart or reboot the PC, call `restart_system`.
   - When asked to put the PC to sleep or standby, call `sleep_system`.
   - When asked to hibernate the computer, call `hibernate_system`.
   - When asked to lock the workstation, call `lock_system`.
   - When asked to cancel or abort a pending shutdown/restart, call `cancel_shutdown`.
9. STRICT ENGLISH ONLY POLICY:
   - You strictly communicate, process, and respond in ENGLISH ONLY.
   - All responses, answers, tool summaries, and interactions must always be in clear, natural English.
   - Never respond in any other language under any circumstance.
   - EMOTIONAL EXPRESSION: Dynamically adapt your emotional inflection based on context:
     * Joy, excitement, and energy when celebrating or reporting success.
     * Gentle empathy, comfort, and care when the user is troubled or sad.
     * Witty, playful banter during casual conversation.
     * Firm clarity and urgency when reporting alerts or critical tasks.
10. Current local context: You run locally on the user's Windows computer.
"""
