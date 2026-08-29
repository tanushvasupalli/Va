import re
import json
import time
from typing import Optional
from google import genai
from google.genai import types
from groq import Groq
import config
from core.storage import storage
from tools.system_tools import (
    get_current_time_and_date,
    open_application_or_site,
    shutdown_system,
    restart_system,
    sleep_system,
    hibernate_system,
    lock_system,
    cancel_shutdown
)
from tools.memory_tools import remember_user_fact, recall_memories, forget_memory_topic
from tools.file_tools import read_local_file, list_local_directory, search_local_files, write_local_file
from tools.web_tools import (
    search_web,
    search_videos,
    search_news,
    read_webpage,
    get_weather,
    google_search_in_browser
)

def clean_llm_response(text: str) -> str:
    """Sanitizes LLM responses, strips thinking tokens, tool tags, and ensures clean speech in any language."""
    if not text:
        return ""
    
    # Strip thinking tags even if unclosed/truncated
    if "<think>" in text:
        if "</think>" in text:
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        else:
            text = re.sub(r"<think>.*", "", text, flags=re.DOTALL)

    # Strip any stray XML / tool tags
    text = re.sub(r"</?think>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<toolcall>.*?</toolcall>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</?(?:function|parameter|tool_call|toolcall)[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^Assistant:\s*", "", text, flags=re.IGNORECASE)
    
    text = text.replace("—", " - ").replace("–", " - ")
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", " - ")
    text = text.replace("\u202f", " ").replace("\u00a0", " ").replace("\u2009", " ").replace("\u200b", "")
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = re.sub(r"[*_#`]", "", text)
    return text.strip()

def execute_tool(name: str, args: dict) -> str:
    """Executes a tool by name with arguments dict."""
    try:
        clean_name = name.lower().replace("_", "")
        # File Tools (On-Demand Only)
        if "readlocalfile" in clean_name or "readfile" in clean_name:
            return read_local_file(args.get("file_path", str(args)))
        elif "listlocaldirectory" in clean_name or "listdirectory" in clean_name or "listfiles" in clean_name:
            return list_local_directory(args.get("folder_name_or_path", "documents"))
        elif "searchlocalfiles" in clean_name or "searchfiles" in clean_name:
            return search_local_files(args.get("query", str(args)), args.get("search_in", "documents"))
        elif "writelocalfile" in clean_name or "writefile" in clean_name or "savefile" in clean_name:
            return write_local_file(args.get("file_path", "notes.txt"), args.get("content", ""))
        
        # Memory Tools
        elif "remember" in clean_name or "savefact" in clean_name:
            return remember_user_fact(args.get("topic", "general"), args.get("fact", str(args)))
        elif "recall" in clean_name or "getmemories" in clean_name:
            return recall_memories()
        elif "forget" in clean_name:
            return forget_memory_topic(args.get("topic", str(args)))
        
        # Web & Video Tools
        elif "video" in clean_name or "youtube" in clean_name:
            return search_videos(args.get("query", str(args)))
        elif "searchweb" in clean_name:
            return search_web(args.get("query", str(args)))
        elif "searchnews" in clean_name:
            return search_news(args.get("topic", "world news"))
        elif "readwebpage" in clean_name:
            return read_webpage(args.get("url", str(args)))
        elif "weather" in clean_name:
            return get_weather(args.get("location", "current location"))
        elif "googlesearch" in clean_name:
            return google_search_in_browser(args.get("query", str(args)))
        elif "open" in clean_name or "application" in clean_name or "site" in clean_name:
            return open_application_or_site(args.get("target", str(args)))
        elif "time" in clean_name or "date" in clean_name:
            return get_current_time_and_date()
        
        # System Power & State Tools
        elif "shutdown" in clean_name and "cancel" not in clean_name and "abort" not in clean_name:
            return shutdown_system(args.get("delay_seconds", 5))
        elif "restart" in clean_name or "reboot" in clean_name:
            return restart_system(args.get("delay_seconds", 5))
        elif "sleep" in clean_name or "suspend" in clean_name:
            return sleep_system()
        elif "hibernate" in clean_name:
            return hibernate_system()
        elif "lock" in clean_name:
            return lock_system()
        elif "cancelshutdown" in clean_name or "abortshutdown" in clean_name:
            return cancel_shutdown()
        return f"Completed {name}."
    except Exception as e:
        return f"Tool execution error: {e}"

# Tool schema definitions for Groq
GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_local_file",
            "description": "Reads contents of a local file on PC. ONLY use when user explicitly asks to read a file.",
            "parameters": {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Filename or path to read"}},
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_local_directory",
            "description": "Lists files in a local directory (e.g. desktop, documents, downloads). ONLY use when explicitly requested.",
            "parameters": {
                "type": "object",
                "properties": {"folder_name_or_path": {"type": "string", "description": "Folder alias (desktop, documents, downloads) or path"}},
                "required": ["folder_name_or_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_local_files",
            "description": "Searches for files matching a filename or pattern on your PC. ONLY use when explicitly requested.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Filename or pattern (e.g. 'resume', '*.pdf')"},
                    "search_in": {"type": "string", "description": "Folder alias (desktop, documents, downloads, all)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_local_file",
            "description": "Creates or writes text content to a local file. ONLY use when explicitly asked to save or create a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Destination file path"},
                    "content": {"type": "string", "description": "Text content to write"}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_user_fact",
            "description": "Saves a persistent fact, preference, or memory about the user into Supabase storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Subject/category"},
                    "fact": {"type": "string", "description": "Information to remember permanently"}
                },
                "required": ["topic", "fact"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memories",
            "description": "Lists all facts and long-term memories currently stored in Wednesday's memory.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_videos",
            "description": "Searches YouTube and video platforms for videos, topics, and channel uploads.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Channel name or video topic"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Performs a live web search for current information, news, facts, and events.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_application_or_site",
            "description": "Opens applications (e.g. Word, Excel, Calculator, Spotify, Chrome) or websites.",
            "parameters": {
                "type": "object",
                "properties": {"target": {"type": "string", "description": "Name of app or website"}},
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Gets current weather for any location.",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "City name"}},
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time_and_date",
            "description": "Returns current local time and date.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_system",
            "description": "Shuts down / powers off the Windows PC. Use when user asks to turn off, shut down, or power off the computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {"type": "integer", "description": "Delay in seconds before shutting down (default 5)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restart_system",
            "description": "Restarts / reboots the Windows PC. Use when user asks to restart or reboot the computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_seconds": {"type": "integer", "description": "Delay in seconds before restarting (default 5)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sleep_system",
            "description": "Puts the Windows PC into Sleep / Standby mode immediately.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hibernate_system",
            "description": "Puts the Windows PC into Hibernation mode.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_system",
            "description": "Locks the Windows workstation screen immediately.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_shutdown",
            "description": "Aborts or cancels a scheduled Windows shutdown or restart.",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

class Brain:
    """The dynamic multi-model intelligence, file access, and memory layer powering Wednesday."""

    def __init__(self):
        self.active_model = config.GROQ_MODEL
        self.gemini_client = None
        self.groq_client = None
        self._init_clients()

    def _init_clients(self):
        if config.GEMINI_API_KEY and config.GEMINI_API_KEY != "your_gemini_api_key_here":
            try:
                self.gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
            except Exception as e:
                print(f"[Brain Warning] Gemini initialization failed: {e}")

        if config.GROQ_API_KEY and config.GROQ_API_KEY != "your_groq_api_key_here":
            try:
                self.groq_client = Groq(api_key=config.GROQ_API_KEY)
            except Exception as e:
                print(f"[Brain Warning] Groq initialization failed: {e}")

    def set_model(self, model_name: str):
        """Dynamically switches the active AI model from the dashboard UI."""
        if model_name:
            self.active_model = model_name.strip()
            print(f"[Brain] Active model dynamically switched to: '{self.active_model}'")

    def _build_system_prompt_with_memory(self, speaker_name: Optional[str] = None, is_owner: bool = True) -> str:
        """Injects stored long-term facts, memories, and verified speaker identity into the system instructions."""
        memories_block = storage.format_memories_for_prompt()
        base_prompt = config.SYSTEM_PROMPT
        speaker_info = ""
        if speaker_name:
            if is_owner:
                speaker_info = f"\n[VOICE RECOGNITION CONTEXT]: Current speaker is '{speaker_name}' (Primary Owner/Authorized User with verified voice print). Address them naturally and personalize responses."
            else:
                speaker_info = f"\n[VOICE RECOGNITION CONTEXT]: Current speaker is identified as '{speaker_name}' (Guest / Unregistered voice). Be polite and helpful."
        
        combined = f"{base_prompt}{speaker_info}"
        if memories_block:
            return f"{combined}\n{memories_block}\nAlways utilize the above stored memories and context when answering."
        return combined

    def _query_groq(self, model_name: str, messages: list, start_time: float, clean_prompt: str, source: str, session_id: str) -> Optional[str]:
        """Queries Groq with tool calling."""
        if not self.groq_client:
            return None
        try:
            completion = self.groq_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=GROQ_TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1024
            )
            msg = completion.choices[0].message

            if msg.tool_calls:
                last_tool_res = ""
                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    try:
                        func_args = json.loads(tc.function.arguments)
                    except Exception:
                        func_args = {"query": tc.function.arguments, "file_path": tc.function.arguments, "folder_name_or_path": tc.function.arguments}
                    
                    tool_res = execute_tool(func_name, func_args)
                    last_tool_res = tool_res

                    if "open" in func_name.lower():
                        latency = round(time.time() - start_time, 2)
                        storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
                        storage.add_message("assistant", tool_res, latency=latency, session_id=session_id)
                        return tool_res

                    messages.append(msg)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(tool_res)
                    })

                follow_up = self.groq_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1024
                )
                reply = clean_llm_response(follow_up.choices[0].message.content)
                if not reply:
                    reply = last_tool_res

                if reply:
                    latency = round(time.time() - start_time, 2)
                    storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
                    storage.add_message("assistant", reply, latency=latency, session_id=session_id)
                    return reply

            if msg.content:
                reply = clean_llm_response(msg.content)
                if reply:
                    latency = round(time.time() - start_time, 2)
                    storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
                    storage.add_message("assistant", reply, latency=latency, session_id=session_id)
                    return reply
        except Exception as e:
            print(f"[Brain Notice] Groq query ({model_name}): {e}")
        return None

    def _query_gemini(self, model_name: str, history_turns: list, system_instruction: str, start_time: float, clean_prompt: str, source: str, session_id: str) -> Optional[str]:
        """Queries Google Gemini."""
        if not self.gemini_client:
            return None
        try:
            contents = []
            for turn in history_turns:
                role_tag = "user" if turn["role"] == "user" else "model"
                contents.append(types.Content(
                    role=role_tag,
                    parts=[types.Part.from_text(text=turn["content"])]
                ))
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=clean_prompt)]
            ))

            response = self.gemini_client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                )
            )

            if response and response.text:
                reply = clean_llm_response(response.text)
                if reply:
                    latency = round(time.time() - start_time, 2)
                    storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
                    storage.add_message("assistant", reply, latency=latency, session_id=session_id)
                    return reply
        except Exception as e:
            print(f"[Brain Notice] Gemini query ({model_name}): {e}")
        return None

    def query(self, user_input: str, source: str = "text", session_id: str = "default", model_override: Optional[str] = None, speaker: Optional[str] = None, is_owner: bool = True) -> str:
        """
        Processes user query with multi-turn context window, on-demand local file access, speaker recognition, and persistent memory.
        """
        if not user_input or not user_input.strip():
            return ""

        clean_prompt = user_input.strip()
        start_time = time.time()
        chosen_model = model_override or self.active_model

        # Fast direct action dispatch for system power and state commands
        p_lower = re.sub(r"[^\w\s]", "", clean_prompt.lower()).strip()
        p_lower = re.sub(r"^(?:please\s+|can\s+you\s+|would\s+you\s+|wednesday\s+)?", "", p_lower).strip()

        if p_lower in [
            "shutdown", "shut down", "turn off pc", "turn off the pc", "turn off computer",
            "turn off the computer", "power off", "power off pc", "power off computer",
            "shutdown pc", "shutdown computer", "shut down pc", "shut down computer",
            "shut down the pc", "shut down the computer"
        ]:
            reply = shutdown_system(delay_seconds=5)
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply

        elif p_lower in [
            "restart", "reboot", "restart pc", "reboot pc", "restart computer", "reboot computer",
            "restart the pc", "restart the computer", "reboot the pc", "reboot the computer"
        ]:
            reply = restart_system(delay_seconds=5)
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply

        elif p_lower in [
            "sleep", "go to sleep", "sleep pc", "put pc to sleep", "put computer to sleep",
            "sleep mode", "standby", "suspend", "put the pc to sleep", "put the computer to sleep"
        ]:
            reply = sleep_system()
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply

        elif p_lower in [
            "hibernate", "hibernate pc", "hibernate computer", "put pc in hibernation",
            "hibernate the pc", "hibernate the computer", "enter hibernation"
        ]:
            reply = hibernate_system()
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply

        elif p_lower in [
            "lock", "lock pc", "lock computer", "lock screen", "lock workstation",
            "lock the pc", "lock the screen", "lock the computer", "lock the workstation"
        ]:
            reply = lock_system()
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply

        elif p_lower in [
            "cancel shutdown", "abort shutdown", "stop shutdown", "dont shutdown",
            "cancel restart", "abort restart", "stop restart"
        ]:
            reply = cancel_shutdown()
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply

        # Fast direct action dispatch for strict open/launch commands
        is_query_or_file = any(k in clean_prompt.lower() for k in [
            "find", "search", "what", "how", "who", "which", "latest", "video", "channel",
            "tell me", "explain", "why", "when", "summary", "look up", "remember", "recall",
            "forget", "do you remember", "my name", "file", "folder", "read", "desktop", "documents",
            "directory", "write", "save", "download"
        ])
        
        if not is_query_or_file:
            open_match = re.match(r"^(?:please\s+|can\s+you\s+|would\s+you\s+)?(?:open|launch|start|go\s+to)\s+([a-zA-Z0-9\.\s]+)$", clean_prompt, flags=re.IGNORECASE)
            if open_match:
                target = open_match.group(1).strip()
                if target and target not in ["the door", "up", "a file", "it"]:
                    reply = open_application_or_site(target)
                    latency = round(time.time() - start_time, 2)
                    storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
                    storage.add_message("assistant", reply, latency=latency, session_id=session_id)
                    return reply

        # Retrieve Sliding Context Window (last 8 turns)
        history_turns = storage.get_context_window(limit=8, session_id=session_id)
        system_instruction = self._build_system_prompt_with_memory(speaker_name=speaker, is_owner=is_owner)

        if not self.gemini_client and not self.groq_client:
            self._init_clients()

        # Build Groq messages list
        groq_messages = [{"role": "system", "content": system_instruction}]
        for turn in history_turns:
            role = "user" if turn["role"] == "user" else "assistant"
            groq_messages.append({"role": role, "content": turn["content"]})
        groq_messages.append({"role": "user", "content": clean_prompt})

        # ROUTING LOGIC: Is chosen model Gemini or Groq?
        if "gemini" in chosen_model.lower():
            # 1. Primary: Gemini
            reply = self._query_gemini(chosen_model, history_turns, system_instruction, start_time, clean_prompt, source, session_id)
            if reply:
                return reply
            # Fallback: Groq
            reply = self._query_groq(config.GROQ_MODEL, groq_messages, start_time, clean_prompt, source, session_id)
            if reply:
                return reply
        else:
            # 1. Primary: Groq (GPT-OSS-120B, Qwen, etc.)
            reply = self._query_groq(chosen_model, groq_messages, start_time, clean_prompt, source, session_id)
            if reply:
                return reply
            # Fallback: Gemini
            reply = self._query_gemini(config.GEMINI_MODEL, history_turns, system_instruction, start_time, clean_prompt, source, session_id)
            if reply:
                return reply

        fallback_msg = "Consider it done."
        storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
        storage.add_message("assistant", fallback_msg, session_id=session_id)
        return fallback_msg

# Global singleton instance
brain = Brain()
