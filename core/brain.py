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
    cancel_shutdown,
    change_power_pin,
    execute_raw_power_action
)
from core.security import (
    get_power_password,
    verify_power_password,
    set_power_password,
    extract_pin_from_text,
    set_pending_power_action,
    get_pending_power_action,
    clear_pending_power_action
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

from tools.n8n_tools import (
    trigger_n8n_workflow,
    call_n8n_webhook,
    list_n8n_workflows,
    search_n8n_templates,
    get_n8n_template,
    search_n8n_nodes,
    get_n8n_node_schema,
    validate_n8n_workflow,
    create_and_deploy_n8n_workflow,
    activate_n8n_workflow,
    deactivate_n8n_workflow
)
from tools.pc_bridge_tools import (
    read_remote_pc_file,
    list_remote_pc_directory,
    search_remote_pc_files,
    write_remote_pc_file,
    control_remote_pc_power,
    exec_remote_pc_command,
    check_pc_status
)
from tools.network_tools import (
    scan_local_network,
    port_scan_device,
    wake_pc_via_wol,
    ping_network_device,
    send_network_http_request
)
from tools.mcp_tools import list_connected_mcp_tools, execute_mcp_tool
from core.mcp_client import mcp_client

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
        # Remote PC Bridge Tools
        if "readremotepc" in clean_name or "readpcfile" in clean_name:
            return read_remote_pc_file(args.get("file_path", str(args)))
        elif "listremotepc" in clean_name or "listpcdirectory" in clean_name:
            return list_remote_pc_directory(args.get("folder_path", "Desktop"))
        elif "searchremotepc" in clean_name or "searchpcfiles" in clean_name:
            return search_remote_pc_files(args.get("query", str(args)), args.get("search_in", "Desktop"))
        elif "writeremotepc" in clean_name or "writepcfile" in clean_name:
            return write_remote_pc_file(args.get("file_path", "notes.txt"), args.get("content", ""))
        elif "controlremotepc" in clean_name or "pcpower" in clean_name:
            return control_remote_pc_power(args.get("action", "status"), pin=args.get("pin", None))
        elif "executepccommand" in clean_name or "execpccommand" in clean_name:
            return exec_remote_pc_command(args.get("command", str(args)))
        elif "checkpcstatus" in clean_name:
            return check_pc_status()

        # Local Network & Device Tools
        elif "portscan" in clean_name or "scanport" in clean_name:
            return port_scan_device(args.get("host", str(args)), args.get("ports", None))
        elif "scanlocalnetwork" in clean_name or "scannetwork" in clean_name or "wifiscan" in clean_name:
            return scan_local_network(args.get("subnet", ""))
        elif "wakepc" in clean_name or "wakeonlan" in clean_name or "wol" in clean_name:
            return wake_pc_via_wol(args.get("mac_address", ""))
        elif "pingnetwork" in clean_name or "pingdevice" in clean_name:
            return ping_network_device(args.get("host", str(args)))
        elif "networkhttprequest" in clean_name or "iotrequest" in clean_name:
            return send_network_http_request(args.get("url", ""), args.get("method", "GET"), args.get("json_data", None))

        # n8n Automation & MCP Tools
        elif "createn8nworkflow" in clean_name or "deployn8nworkflow" in clean_name or "createanddeployn8n" in clean_name:
            return create_and_deploy_n8n_workflow(args.get("name", "Automated Workflow"), args.get("workflow_json", args.get("workflow", {})), args.get("activate", True))
        elif "activaten8n" in clean_name:
            return activate_n8n_workflow(args.get("workflow_id", str(args)))
        elif "deactivaten8n" in clean_name:
            return deactivate_n8n_workflow(args.get("workflow_id", str(args)))
        elif "getn8ntemplate" in clean_name:
            return get_n8n_template(args.get("template_id", str(args)))
        elif "searchn8ntemplates" in clean_name or "n8ntemplates" in clean_name:
            return search_n8n_templates(args.get("query", str(args)), args.get("task", ""), args.get("complexity", ""))
        elif "searchn8nnodes" in clean_name or "n8nnodes" in clean_name:
            return search_n8n_nodes(args.get("query", str(args)), args.get("category", ""))
        elif "getn8nnodeschema" in clean_name or "n8nnodeschema" in clean_name:
            return get_n8n_node_schema(args.get("node_type", str(args)))
        elif "validaten8nworkflow" in clean_name or "validaten8n" in clean_name:
            return validate_n8n_workflow(args.get("workflow_json", args.get("workflow", "")))
        elif "triggern8n" in clean_name or "n8nworkflow" in clean_name:
            return trigger_n8n_workflow(args.get("workflow_id_or_name", str(args)), args.get("payload_data", None))
        elif "calln8nwebhook" in clean_name or "n8nwebhook" in clean_name:
            return call_n8n_webhook(args.get("path_or_url", ""), args.get("payload", None))
        elif "listn8n" in clean_name:
            return list_n8n_workflows()

        # Model Context Protocol (MCP) Tools
        elif "connectmcpserver" in clean_name or "addmcpserver" in clean_name:
            from tools.mcp_tools import connect_mcp_server
            return connect_mcp_server(args.get("server_url", str(args)))
        elif "disconnectmcpserver" in clean_name or "removemcpserver" in clean_name:
            from tools.mcp_tools import disconnect_mcp_server
            return disconnect_mcp_server(args.get("server_url", str(args)))
        elif clean_name.startswith("mcp") or name.startswith("mcp_"):
            return execute_mcp_tool(name, args)

        # Settings & Config Tools
        elif "updatesystemsetting" in clean_name or "configuresetting" in clean_name or "setconfig" in clean_name:
            from core.config_manager import set_config_value
            k = args.get("key", "")
            v = args.get("value", "")
            ok, msg = set_config_value(k, v)
            return msg
        elif "getsystemsetting" in clean_name or "getconfig" in clean_name:
            from core.config_manager import get_config_value
            k = args.get("key", "")
            return f"{k} = {get_config_value(k, mask_secrets=True)}"

        # File Tools (Local)
        elif "readlocalfile" in clean_name or "readfile" in clean_name:
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
        
        # Screen Vision & UI Control Tools
        elif "getscreenview" in clean_name or "analyzescreen" in clean_name or "seescreen" in clean_name:
            from tools.vision_tools import get_screen_view
            return get_screen_view(args.get("prompt", args.get("question", "")))
        elif "clickscreenitem" in clean_name or "clickitem" in clean_name or "clickelement" in clean_name:
            from tools.ui_control_tools import click_screen_item
            return click_screen_item(args.get("target_description", str(args)), args.get("click_type", "single"))
        elif "clickcoordinates" in clean_name or "clickxy" in clean_name:
            from tools.ui_control_tools import click_coordinates
            return click_coordinates(int(args.get("x", 0)), int(args.get("y", 0)), args.get("click_type", "single"))
        elif "typetextintoui" in clean_name or "typetext" in clean_name:
            from tools.ui_control_tools import type_text_into_ui
            return type_text_into_ui(args.get("text", ""), args.get("press_enter", False))
        elif "presshotkey" in clean_name or "presskey" in clean_name:
            from tools.ui_control_tools import press_hotkey
            return press_hotkey(args.get("hotkey", str(args)))
        elif "scrollscreen" in clean_name:
            from tools.ui_control_tools import scroll_screen
            return scroll_screen(int(args.get("clicks", -3)))
        elif "recordscreenvideo" in clean_name or "recordscreen" in clean_name:
            from tools.screen_recorder import record_and_send_telegram_sync
            return record_and_send_telegram_sync(int(args.get("duration_seconds", 10)), args.get("caption", ""))

        # Screenshot Tool
        elif "screenshot" in clean_name or "capturescreen" in clean_name:
            from core.telegram_bot import send_screenshot_to_owner_sync
            caption = args.get("caption", "📸 Real-time PC Screenshot")
            return send_screenshot_to_owner_sync(caption)

        # System Power & State Tools (PIN Protected)
        elif "changepowerpin" in clean_name or "changepin" in clean_name or "changepassword" in clean_name:
            return change_power_pin(args.get("current_pin", ""), args.get("new_pin", ""))
        elif "shutdown" in clean_name and "cancel" not in clean_name and "abort" not in clean_name:
            return shutdown_system(args.get("delay_seconds", 5), pin=args.get("pin", ""))
        elif "restart" in clean_name or "reboot" in clean_name:
            return restart_system(args.get("delay_seconds", 5), pin=args.get("pin", ""))
        elif "sleep" in clean_name or "suspend" in clean_name:
            return sleep_system(pin=args.get("pin", ""))
        elif "hibernate" in clean_name:
            return hibernate_system(pin=args.get("pin", ""))
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
            "name": "change_power_pin",
            "description": "Changes the 4-digit security PIN required for PC shutdown, restart, and sleep operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_pin": {"type": "string", "description": "Current 4-digit security PIN"},
                    "new_pin": {"type": "string", "description": "New 4-digit security PIN"}
                },
                "required": ["current_pin", "new_pin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_system",
            "description": "Shuts down / powers off the Windows PC. Requires 4-digit security PIN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pin": {"type": "string", "description": "4-digit security PIN (default 2206)"},
                    "delay_seconds": {"type": "integer", "description": "Delay in seconds before shutting down (default 5)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restart_system",
            "description": "Restarts / reboots the Windows PC. Requires 4-digit security PIN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pin": {"type": "string", "description": "4-digit security PIN (default 2206)"},
                    "delay_seconds": {"type": "integer", "description": "Delay in seconds before restarting (default 5)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sleep_system",
            "description": "Puts the Windows PC into Sleep / Standby mode immediately. Requires 4-digit security PIN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pin": {"type": "string", "description": "4-digit security PIN (default 2206)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hibernate_system",
            "description": "Puts the Windows PC into Hibernation mode. Requires 4-digit security PIN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pin": {"type": "string", "description": "4-digit security PIN (default 2206)"}
                }
            }
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
    },
    {
        "type": "function",
        "function": {
            "name": "read_remote_pc_file",
            "description": "Reads contents of a file on the remote Windows PC. ONLY use when user explicitly asks to read or check a PC file.",
            "parameters": {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Path or filename on PC"}},
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_remote_pc_directory",
            "description": "Lists files in a directory on the remote PC (e.g. Desktop, Documents, Downloads).",
            "parameters": {
                "type": "object",
                "properties": {"folder_path": {"type": "string", "description": "Folder alias (Desktop, Documents, Downloads) or path"}},
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_remote_pc_files",
            "description": "Searches for files on the remote Windows PC by query/name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Filename search term or pattern"},
                    "search_in": {"type": "string", "description": "Folder alias (Desktop, Documents, Downloads, all)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_remote_pc_file",
            "description": "Writes text content to a file on the remote PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Destination file path on PC"},
                    "content": {"type": "string", "description": "Text content to save"}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_remote_pc_power",
            "description": "Controls remote PC state (sleep, lock, hibernate, restart, shutdown, cancel).",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "string", "description": "Action: 'sleep', 'lock', 'hibernate', 'restart', 'shutdown', 'cancel', 'status'"}},
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_local_network",
            "description": "Scans local Wi-Fi/LAN network and returns connected devices with IP addresses, hostnames, and active services.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "port_scan_device",
            "description": "Scans a specific device on the network for open ports and services (e.g. PC companion, Web, SSH, Home Assistant, RTSP).",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "Target IP address or hostname to scan"},
                    "ports": {"type": "string", "description": "Optional comma-separated list of ports"}
                },
                "required": ["host"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wake_pc_via_wol",
            "description": "Sends Wake-on-LAN (WOL) magic packet to power on sleeping PC.",
            "parameters": {
                "type": "object",
                "properties": {"mac_address": {"type": "string", "description": "Optional MAC address of PC"}}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ping_network_device",
            "description": "Pings a network IP address or hostname to verify if it is online.",
            "parameters": {
                "type": "object",
                "properties": {"host": {"type": "string", "description": "IP address or hostname"}},
                "required": ["host"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_n8n_workflow",
            "description": "Triggers an n8n automation workflow or webhook by name/ID with dynamic data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_id_or_name": {"type": "string", "description": "n8n workflow name or webhook slug"},
                    "payload_data": {"type": "object", "description": "JSON payload to pass into workflow"}
                },
                "required": ["workflow_id_or_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_n8n_templates",
            "description": "Searches across 2,709+ curated n8n automation templates for workflows, triggers, and integrations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keywords describing the automation (e.g. 'telegram alert', 'lead generation', 'slack sync')"},
                    "task": {"type": "string", "description": "Optional task category (e.g. 'webhook_processing', 'data_sync')"},
                    "complexity": {"type": "string", "description": "Optional complexity ('simple', 'medium', 'complex')"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_n8n_nodes",
            "description": "Searches across 2,616+ n8n workflow integration nodes (e.g. 'telegram', 'slack', 'gmail', 'postgres', 'openai').",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Node name or keyword"},
                    "category": {"type": "string", "description": "Optional category filter"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_n8n_node_schema",
            "description": "Gets properties, operations, documentation, and schema for a specific n8n node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_type": {"type": "string", "description": "n8n node type (e.g. 'n8n-nodes-base.telegram', 'n8n-nodes-base.slack')"}
                },
                "required": ["node_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_n8n_workflow",
            "description": "Validates the structure, nodes, and connections of an n8n workflow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_json": {"type": "string", "description": "Workflow JSON string or object to validate"}
                },
                "required": ["workflow_json"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_and_deploy_n8n_workflow",
            "description": "Autonomously creates, saves, hosts, and activates a workflow locally in your n8n instance via REST API without manual steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Workflow name (e.g. 'Telegram AI News Alert')"},
                    "workflow_json": {"type": "string", "description": "Valid workflow JSON containing nodes, connections, and settings"},
                    "activate": {"type": "boolean", "description": "Whether to immediately activate and host the workflow (default true)"}
                },
                "required": ["name", "workflow_json"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_n8n_template",
            "description": "Retrieves the complete workflow JSON template from n8n-mcp library by numeric template ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "template_id": {"type": "integer", "description": "Template numeric ID (e.g. 4740)"}
                },
                "required": ["template_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "activate_n8n_workflow",
            "description": "Activates a workflow in n8n so it starts running/listening locally.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_id": {"type": "string", "description": "ID of workflow to activate"}
                },
                "required": ["workflow_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot_and_send_telegram",
            "description": "Captures a live screenshot of the PC desktop and sends the photo directly to the user's Telegram chat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "caption": {"type": "string", "description": "Optional description or note for the screenshot"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_system_setting",
            "description": "Updates a system configuration setting or environment variable (e.g. TTS_VOICE, GROQ_MODEL, GEMINI_MODEL, MUTE_AGENT_VOICE).",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Setting name / variable key (e.g. TTS_VOICE, GROQ_MODEL)"},
                    "value": {"type": "string", "description": "New value to assign"}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "connect_mcp_server",
            "description": "Connects and registers a new Model Context Protocol (MCP) server by URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_url": {"type": "string", "description": "Full URL of the MCP server (e.g. http://localhost:8000/sse)"}
                },
                "required": ["server_url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_screen_view",
            "description": "Analyzes the laptop's live screen with AI Vision to describe what's open, read text, identify UI elements, or diagnose errors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Specific question or analysis prompt for the screen view"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_screen_item",
            "description": "Uses AI spatial vision to locate any icon, button, menu item, or text on the screen and clicks it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_description": {"type": "string", "description": "Name or description of the icon/button to click (e.g. 'Start button', 'Google Chrome icon', 'Submit button')"},
                    "click_type": {"type": "string", "description": "Click type: single, double, right, middle", "default": "single"}
                },
                "required": ["target_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "type_text_into_ui",
            "description": "Types text into the active focused window or input field on the laptop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                    "press_enter": {"type": "boolean", "description": "Whether to press Enter after typing"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "press_hotkey",
            "description": "Simulates pressing keyboard shortcuts or special keys (e.g. 'ctrl+c', 'win+d', 'alt+tab', 'enter', 'esc').",
            "parameters": {
                "type": "object",
                "properties": {
                    "hotkey": {"type": "string", "description": "Key or hotkey combination to press"}
                },
                "required": ["hotkey"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_screen_video_and_send_telegram",
            "description": "Records the laptop desktop screen for a specified duration into an MP4 video and sends it to the user's Telegram chat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_seconds": {"type": "integer", "description": "Duration in seconds (e.g. 5 to 30 seconds)", "default": 10},
                    "caption": {"type": "string", "description": "Optional caption for the video"}
                }
            }
        }
    }
]

GROQ_MODELS_CASCADE = [
    "qwen/qwen3.8-27b",
    "groq/compound-mini",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b"
]

GEMINI_MODELS_CASCADE = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash"
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

    def _get_groq_tools(self) -> list:
        tools = list(GROQ_TOOLS)
        try:
            mcp_defs = mcp_client.get_tool_definitions_for_groq()
            if mcp_defs:
                tools.extend(mcp_defs)
        except Exception:
            pass
        return tools

    def _query_groq_single(self, model_name: str, messages: list, start_time: float, clean_prompt: str, source: str, session_id: str) -> Optional[str]:
        """Queries a single Groq model with tool calling."""
        if not self.groq_client:
            return None
        try:
            all_tools = self._get_groq_tools()
            try:
                completion = self.groq_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=all_tools if all_tools else None,
                    tool_choice="auto" if all_tools else None,
                    temperature=0.7,
                    max_tokens=1024
                )
            except Exception as te:
                if "tool calling" in str(te).lower() or "not supported" in str(te).lower():
                    completion = self.groq_client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1024
                    )
                else:
                    raise te

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

    def _query_groq(self, model_name: str, messages: list, start_time: float, clean_prompt: str, source: str, session_id: str) -> Optional[str]:
        """Queries Groq with automatic cascading fallback across fast models."""
        models_to_try = [model_name] + [m for m in GROQ_MODELS_CASCADE if m != model_name]
        for m in models_to_try:
            import copy
            msg_copy = copy.deepcopy(messages)
            res = self._query_groq_single(m, msg_copy, start_time, clean_prompt, source, session_id)
            if res:
                return res
        return None

    def _query_gemini_single(self, model_name: str, history_turns: list, system_instruction: str, start_time: float, clean_prompt: str, source: str, session_id: str) -> Optional[str]:
        """Queries a single Google Gemini model."""
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

    def _query_gemini(self, model_name: str, history_turns: list, system_instruction: str, start_time: float, clean_prompt: str, source: str, session_id: str) -> Optional[str]:
        """Queries Gemini with cascading fallback across active Gemini models."""
        models_to_try = [model_name] + [m for m in GEMINI_MODELS_CASCADE if m != model_name]
        for m in models_to_try:
            res = self._query_gemini_single(m, history_turns, system_instruction, start_time, clean_prompt, source, session_id)
            if res:
                return res
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

        # 1. Check if there is an active pending power action awaiting security PIN
        pending = get_pending_power_action(session_id)
        candidate_pin = extract_pin_from_text(clean_prompt)

        if pending and candidate_pin:
            clear_pending_power_action(session_id)
            if verify_power_password(candidate_pin):
                action = pending["action"]
                delay = pending.get("delay_seconds", 5)
                reply = execute_raw_power_action(action, delay)
            else:
                reply = "Authentication failed: incorrect security PIN. Power command cancelled."
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply

        # 2. Check for PIN Change requests
        change_match = re.search(
            r"(?:change|update|set)\s+(?:the\s+)?(?:power\s+)?(?:password|pin|passcode|code)\s+(?:from\s+(\w+)\s+to\s+(\w+)|to\s+(\w+)(?:\s+(?:with|current\s+pin|old\s+pin|using)\s+(\w+))?)",
            clean_prompt,
            re.IGNORECASE
        )
        if change_match:
            old_raw = change_match.group(1) or change_match.group(4)
            new_raw = change_match.group(2) or change_match.group(3)
            old_p = extract_pin_from_text(old_raw) if old_raw else None
            new_p = extract_pin_from_text(new_raw) if new_raw else None
            if old_p and new_p:
                reply = change_power_pin(old_p, new_p)
            elif new_p and not old_p:
                reply = f"To update your security PIN to '{new_p}', please state your current PIN (e.g. 'change power pin from [current PIN] to {new_p}')."
            else:
                reply = "Usage: Say 'change power pin from [current PIN] to [new PIN]'."
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply

        # 3. Check for System Power & State Commands
        p_lower = re.sub(r"[^\w\s]", "", clean_prompt.lower()).strip()
        p_lower = re.sub(r"^(?:please\s+|can\s+you\s+|would\s+you\s+|wednesday\s+)?", "", p_lower).strip()

        power_action = None
        if any(w in p_lower for w in ["shutdown", "shut down", "turn off pc", "turn off the pc", "turn off computer", "turn off the computer", "power off", "power off pc", "power off computer", "turn off laptop", "shut down laptop", "shutdown laptop"]):
            power_action = "shutdown"
        elif any(w in p_lower for w in ["restart", "reboot", "restart pc", "reboot pc", "restart computer", "reboot computer", "restart laptop", "reboot laptop"]):
            power_action = "restart"
        elif any(w in p_lower for w in ["sleep", "go to sleep", "sleep pc", "put pc to sleep", "put computer to sleep", "put laptop to sleep", "standby", "suspend", "sleep laptop"]):
            power_action = "sleep"
        elif any(w in p_lower for w in ["hibernate", "hibernate pc", "hibernate computer", "put pc in hibernation", "hibernate laptop"]):
            power_action = "hibernate"
        elif any(w in p_lower for w in ["lock", "lock pc", "lock computer", "lock screen", "lock workstation", "lock laptop"]):
            reply = lock_system()
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply
        elif any(w in p_lower for w in ["cancel shutdown", "abort shutdown", "stop shutdown", "dont shutdown", "cancel restart", "abort restart"]):
            reply = cancel_shutdown()
            clear_pending_power_action(session_id)
            storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
            storage.add_message("assistant", reply, latency=0.01, session_id=session_id)
            return reply

        if power_action:
            # Check if user provided the PIN in the same command
            if candidate_pin:
                if verify_power_password(candidate_pin):
                    reply = execute_raw_power_action(power_action)
                else:
                    reply = "Authentication failed: incorrect security PIN. Power command cancelled."
            else:
                # Set pending state and request PIN
                set_pending_power_action(session_id, power_action)
                action_text = "shut down" if power_action == "shutdown" else ("restart" if power_action == "restart" else ("put your laptop to sleep" if power_action == "sleep" else "hibernate"))
                reply = f"Authentication required to {action_text} your laptop. Please provide the 4-digit security PIN."
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
            # 1. Primary: Groq (Qwen, GPT-OSS, etc.)
            reply = self._query_groq(chosen_model, groq_messages, start_time, clean_prompt, source, session_id)
            if reply:
                return reply
            # Fallback: Gemini
            reply = self._query_gemini(config.GEMINI_MODEL, history_turns, system_instruction, start_time, clean_prompt, source, session_id)
            if reply:
                return reply

        fallback_msg = "I'm currently unable to reach the AI models due to temporary API rate limits or network issues. Please check your API quota or try again in a moment."
        storage.add_message("user", clean_prompt, source=source, latency=0.0, session_id=session_id)
        storage.add_message("assistant", fallback_msg, session_id=session_id)
        return fallback_msg

# Global singleton instance
brain = Brain()
