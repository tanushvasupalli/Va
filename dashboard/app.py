import os
import sys
import json
import time
import asyncio
import threading
import webbrowser
from pathlib import Path
from typing import List, Dict, Optional, Any
import requests

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
import uvicorn

import atexit
import config
from core.storage import storage
from core.audio_io import audio_io
from core.vad import vad_detector
from core.transcriber import transcriber
from core.wake_word import wake_word_detector
from core.speaker_recognition import speaker_recognizer
from core.brain import brain
from core.speaker import speaker
from core.system_optimizer import optimize_process, acquire_single_instance_lock, release_lock, cleanup_memory
from tools.system_tools import resolve_target_url

# Optimize process priority for silent, low-resource background operation
optimize_process()
atexit.register(release_lock)

app = FastAPI(title="Wednesday AI Dashboard")

# Safe JSON serializer
def safe_json_dumps(data: dict) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)

# Track connected WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        text_payload = safe_json_dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(text_payload)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Global state
app_state = {
    "status": "idle",       # idle, listening, thinking, speaking
    "voice_muted": getattr(config, "MUTE_AGENT_VOICE", False),
    "current_session_id": "default",
    "model_name": config.GEMINI_MODEL,
    "voice_name": config.TTS_VOICE,
}

# Event loop for background thread broadcasting
main_loop = None

def broadcast_sync(message: dict):
    """Safely broadcasts a message from sync threads to WebSocket clients."""
    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(manager.broadcast(message), main_loop)

def update_status(new_status: str):
    app_state["status"] = new_status
    broadcast_sync({"type": "status_change", "status": new_status})

# HTML File directory
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard template not found.</h1>")

@app.get("/telegram", response_class=HTMLResponse)
async def get_telegram_dashboard():
    telegram_path = TEMPLATES_DIR / "telegram.html"
    if telegram_path.exists():
        return HTMLResponse(content=telegram_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Telegram Dashboard template not found.</h1>")

# =============================================================================
# TELEGRAM DASHBOARD REST APIS
# =============================================================================

@app.get("/api/telegram/stats")
async def api_get_telegram_stats():
    """Returns live metrics and configuration status for the Telegram Bot."""
    stats = storage.get_telegram_stats()
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "").strip()
    configured = bool(token and token != "your_telegram_bot_token_here")
    allowed_user = getattr(config, "TELEGRAM_ALLOWED_USER_ID", "All (Open)")
    return {
        "status": "success",
        "stats": stats,
        "bot": {
            "configured": configured,
            "allowed_user": str(allowed_user) if allowed_user else "All (Open)",
            "model": app_state["model_name"] or config.GEMINI_MODEL,
            "voice": app_state["voice_name"] or config.TTS_VOICE,
            "muted": app_state["voice_muted"]
        }
    }

@app.get("/api/telegram/messages")
async def api_get_telegram_messages(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    filter: Optional[str] = Query("all")
):
    """Retrieves filtered, searchable Telegram conversation history."""
    messages = storage.get_telegram_messages(limit=limit, offset=offset, search=search, source_filter=filter)
    return {"status": "success", "messages": messages, "count": len(messages)}

@app.post("/api/telegram/ask")
async def api_ask_telegram(payload: dict = Body(...)):
    """Simulates/triggers an interactive conversation turn as Telegram User."""
    user_prompt = payload.get("prompt", "").strip()
    sender_name = payload.get("sender", "Tanush")
    is_voice = payload.get("is_voice", False)
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    source = "voice_telegram" if is_voice else "telegram"
    start_time = time.time()
    reply = brain.query(user_prompt, source=source, session_id="telegram", speaker=sender_name, is_owner=True)
    latency = round(time.time() - start_time, 2)

    broadcast_sync({
        "type": "telegram_update",
        "action": "new_message",
        "prompt": user_prompt,
        "reply": reply,
        "latency": latency
    })

    return {
        "status": "success",
        "user_prompt": user_prompt,
        "reply": reply,
        "latency": latency,
        "source": source
    }

@app.post("/api/telegram/send")
async def api_send_to_telegram(payload: dict = Body(...)):
    """Dispatches a direct message to authorized Telegram user via Telegram Bot API."""
    text = payload.get("text", "").strip()
    chat_id = payload.get("chat_id") or getattr(config, "TELEGRAM_ALLOWED_USER_ID", "")
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "").strip()

    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if not token or token == "your_telegram_bot_token_here":
        raise HTTPException(status_code=400, detail="Telegram Bot Token is not configured in .env")
    if not chat_id:
        raise HTTPException(status_code=400, detail="No Telegram Chat ID specified")

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        res_data = resp.json()
        if not res_data.get("ok"):
            return JSONResponse(status_code=400, content={"status": "error", "detail": res_data.get("description", "Failed to send")})

        storage.add_message("assistant", text, source="telegram_manual", session_id="telegram")
        broadcast_sync({"type": "telegram_update", "action": "sent"})
        return {"status": "success", "message": "Dispatched to Telegram"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/telegram/messages/{message_id}")
async def api_delete_telegram_message(message_id: int):
    """Deletes a specific message by ID."""
    ok = storage.delete_message_by_id(message_id)
    if ok:
        broadcast_sync({"type": "telegram_update", "action": "delete", "id": message_id})
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to delete message")

@app.post("/api/telegram/clear")
async def api_clear_telegram():
    """Clears all Telegram conversation logs."""
    ok = storage.clear_telegram_history()
    if ok:
        broadcast_sync({"type": "telegram_update", "action": "clear"})
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to clear history")

@app.get("/api/telegram/export")
async def api_export_telegram(format: str = Query("json")):
    """Exports conversation transcripts as JSON or text."""
    messages = storage.get_telegram_messages(limit=1000)
    if format.lower() == "txt":
        lines = ["# Wednesday AI - Telegram Conversations Transcript", f"# Exported: {time.strftime('%Y-%m-%d %I:%M %p')}\n"]
        for m in messages:
            sender = "Wednesday AI" if m["role"] == "assistant" else "You"
            src_tag = f" [{m['source']}]" if m.get("source") else ""
            lat_tag = f" ({m['latency']}s)" if m.get("latency") and m["role"] == "assistant" else ""
            lines.append(f"[{m.get('formatted_time', m.get('timestamp', ''))}] {sender}{src_tag}{lat_tag}:")
            lines.append(f"{m['content']}\n")
        return PlainTextResponse("\n".join(lines), headers={"Content-Disposition": "attachment; filename=telegram_conversations.txt"})
# =============================================================================
# SECURITY & PIN MANAGEMENT APIS
# =============================================================================

@app.post("/api/security/pin")
async def api_change_security_pin(payload: dict = Body(...)):
    """Updates the 4-digit security PIN used for power actions."""
    from core.security import set_power_password
    current_pin = payload.get("current_pin", "").strip()
    new_pin = payload.get("new_pin", "").strip()
    if not current_pin or not new_pin:
        raise HTTPException(status_code=400, detail="Both current_pin and new_pin are required")
    
    ok, msg = set_power_password(current_pin, new_pin)
    if ok:
        return {"status": "success", "message": msg}
    return JSONResponse(status_code=400, content={"status": "error", "detail": msg})

@app.get("/api/security/status")
async def api_security_status():
    """Returns security PIN status."""
    return {"status": "success", "pin_protection_active": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Ensure current session exists in Supabase
    sessions = storage.get_all_sessions()
    if not sessions:
        storage.create_session("Main Conversation")
        sessions = storage.get_all_sessions()

    current_sid = app_state["current_session_id"]
    if not any(s["id"] == current_sid for s in sessions):
        current_sid = sessions[0]["id"]
        app_state["current_session_id"] = current_sid

    past_messages = storage.get_session_messages(current_sid, limit=80)
    all_memories = storage.get_all_memories()
    all_voice_profiles = speaker_recognizer.list_enrolled_speakers()

    # Send initial state, sessions list, memories, and voice profiles safely
    await websocket.send_text(safe_json_dumps({
        "type": "init",
        "state": app_state,
        "current_session_id": current_sid,
        "sessions": sessions,
        "history": past_messages,
        "memories": all_memories,
        "voice_profiles": all_voice_profiles
    }))

    try:
        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)
            msg_type = data.get("type")

            # 1. Text Message
            if msg_type == "text_message":
                user_text = data.get("text", "").strip()
                session_id = data.get("session_id", app_state["current_session_id"])
                if user_text:
                    handle_text_query(user_text, session_id=session_id)

            # 2. Start New Conversation
            elif msg_type == "new_session":
                new_title = data.get("title", "New Conversation")
                new_sid = storage.create_session(new_title)
                app_state["current_session_id"] = new_sid
                all_sessions = storage.get_all_sessions()
                await manager.broadcast({
                    "type": "session_switched",
                    "session_id": new_sid,
                    "sessions": all_sessions,
                    "history": []
                })

            # 3. Switch to Existing Session
            elif msg_type == "switch_session":
                target_sid = data.get("session_id")
                if target_sid:
                    app_state["current_session_id"] = target_sid
                    session_msgs = storage.get_session_messages(target_sid)
                    all_sessions = storage.get_all_sessions()
                    await websocket.send_text(safe_json_dumps({
                        "type": "session_switched",
                        "session_id": target_sid,
                        "sessions": all_sessions,
                        "history": session_msgs
                    }))

            # 4. Clear Current Conversation Messages
            elif msg_type == "clear_session":
                sid = data.get("session_id", app_state["current_session_id"])
                storage.clear_session_messages(sid)
                all_sessions = storage.get_all_sessions()
                await manager.broadcast({
                    "type": "session_cleared",
                    "session_id": sid,
                    "sessions": all_sessions
                })

            # 5. Delete Entire Session
            elif msg_type == "delete_session":
                del_sid = data.get("session_id")
                if del_sid:
                    storage.delete_session(del_sid)
                    all_sessions = storage.get_all_sessions()
                    if not all_sessions:
                        new_sid = storage.create_session("Main Conversation")
                        all_sessions = storage.get_all_sessions()
                    else:
                        new_sid = all_sessions[0]["id"]
                    
                    app_state["current_session_id"] = new_sid
                    new_msgs = storage.get_session_messages(new_sid)
                    await manager.broadcast({
                        "type": "session_switched",
                        "session_id": new_sid,
                        "sessions": all_sessions,
                        "history": new_msgs
                    })

            # 6. Memory Management Actions
            elif msg_type == "get_memories":
                await websocket.send_text(safe_json_dumps({
                    "type": "memories_list",
                    "memories": storage.get_all_memories()
                }))

            elif msg_type == "delete_memory":
                mem_id = data.get("memory_id")
                if mem_id:
                    storage.delete_memory_by_id(mem_id)
                    await manager.broadcast({
                        "type": "memories_list",
                        "memories": storage.get_all_memories()
                    })

            elif msg_type == "add_memory":
                topic = data.get("topic", "General")
                fact = data.get("fact", "")
                if fact:
                    storage.remember_fact(topic, fact)
                    await manager.broadcast({
                        "type": "memories_list",
                        "memories": storage.get_all_memories()
                    })

            # 7. Voice Profiles Management
            elif msg_type == "get_voice_profiles":
                await websocket.send_text(safe_json_dumps({
                    "type": "voice_profiles_list",
                    "profiles": speaker_recognizer.list_enrolled_speakers()
                }))

            elif msg_type == "delete_voice_profile":
                prof_name = data.get("name")
                if prof_name:
                    speaker_recognizer.delete_profile(prof_name)
                    await manager.broadcast({
                        "type": "voice_profiles_list",
                        "profiles": speaker_recognizer.list_enrolled_speakers()
                    })

            # 8. Voice Mute Toggle
            elif msg_type == "toggle_mute":
                app_state["voice_muted"] = not app_state["voice_muted"]
                speaker.set_muted(app_state["voice_muted"])
                await manager.broadcast({
                    "type": "mute_change",
                    "voice_muted": app_state["voice_muted"]
                })

            # 9. Dynamic AI Model Switching
            elif msg_type == "change_model":
                new_model = data.get("model_name", config.GROQ_MODEL)
                app_state["model_name"] = new_model
                brain.set_model(new_model)
                await manager.broadcast({
                    "type": "model_changed",
                    "model_name": new_model
                })

            # 10. Push-to-Talk Trigger
            elif msg_type == "trigger_listen":
                threading.Thread(target=manual_listen_trigger, daemon=True).start()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

def check_and_broadcast_url(user_text: str) -> str | None:
    """Checks if the user asked to open a site or application and broadcasts it to the browser."""
    url = resolve_target_url(user_text)
    if url:
        broadcast_sync({"type": "open_url", "url": url})
    return url

def handle_text_query(user_text: str, session_id: str = "default"):
    """Processes text sent directly through the dashboard UI with multi-turn context."""
    def _worker():
        speaker.stop()
        broadcast_sync({
            "type": "new_message",
            "session_id": session_id,
            "role": "user",
            "text": user_text,
            "source": "text",
            "speaker": "Owner (Dashboard)",
            "timestamp": time.strftime("%I:%M %p")
        })

        target_url = check_and_broadcast_url(user_text)

        update_status("thinking")
        start_time = time.time()
        reply = brain.query(user_text, source="text", session_id=session_id, speaker="Tanush", is_owner=True)
        latency = round(time.time() - start_time, 2)

        broadcast_sync({
            "type": "new_message",
            "session_id": session_id,
            "role": "assistant",
            "text": reply,
            "url": target_url,
            "latency": latency,
            "timestamp": time.strftime("%I:%M %p"),
            "sessions": storage.get_all_sessions()
        })

        if not app_state["voice_muted"]:
            update_status("speaking")
            speaker.speak(reply)

        update_status("idle")

    threading.Thread(target=_worker, daemon=True).start()

def manual_listen_trigger():
    """Manual voice listening triggered by clicking mic button in dashboard."""
    session_id = app_state["current_session_id"]
    try:
        speaker.stop()
        update_status("listening")
        speaker.play_chime("wake")
        frames = vad_detector.record_until_silence(timeout_initial_speech=6.0)
        
        if not frames:
            speaker.play_chime("sleep")
            update_status("idle")
            return

        update_status("thinking")
        user_text = transcriber.transcribe(frames)
        
        if not user_text.strip():
            update_status("idle")
            return

        # Voice Biometrics / Speaker Identification
        speaker_name, confidence, is_owner = speaker_recognizer.identify_speaker(frames)

        broadcast_sync({
            "type": "new_message",
            "session_id": session_id,
            "role": "user",
            "text": user_text,
            "source": "voice",
            "speaker": speaker_name,
            "confidence": confidence,
            "is_owner": is_owner,
            "timestamp": time.strftime("%I:%M %p")
        })

        target_url = check_and_broadcast_url(user_text)

        start_time = time.time()
        reply = brain.query(user_text, source="voice", session_id=session_id, speaker=speaker_name, is_owner=is_owner)
        latency = round(time.time() - start_time, 2)

        broadcast_sync({
            "type": "new_message",
            "session_id": session_id,
            "role": "assistant",
            "text": reply,
            "url": target_url,
            "latency": latency,
            "timestamp": time.strftime("%I:%M %p"),
            "sessions": storage.get_all_sessions()
        })

        if not app_state["voice_muted"]:
            update_status("speaking")
            speaker.speak(reply)

        update_status("idle")
    except Exception as e:
        print(f"[Manual Listen Error] {e}")
        update_status("idle")

def voice_listener_background():
    """Continuous background listener for the 'Wednesday' wake word."""
    time.sleep(2)
    try:
        audio_io.start_stream()
    except Exception as e:
        print(f"[Dashboard Voice Warning] Could not start mic: {e}")
        return

    while True:
        try:
            session_id = app_state["current_session_id"]
            if app_state["status"] != "idle":
                time.sleep(0.2)
                continue

            triggered, inline_command, wake_frames = wake_word_detector.listen_for_wake_word()
            if not triggered:
                time.sleep(0.05)
                continue

            update_status("listening")
            speaker.play_chime("wake")

            user_command = inline_command
            active_frames = wake_frames

            if not user_command:
                frames = vad_detector.record_until_silence(timeout_initial_speech=6.0)
                if not frames:
                    speaker.play_chime("sleep")
                    update_status("idle")
                    continue

                active_frames = frames
                update_status("thinking")
                user_command = transcriber.transcribe(frames)

            if not user_command.strip():
                update_status("idle")
                continue

            # Identify speaker biometrics
            speaker_name, confidence, is_owner = speaker_recognizer.identify_speaker(active_frames)

            broadcast_sync({
                "type": "new_message",
                "session_id": session_id,
                "role": "user",
                "text": user_command,
                "source": "voice",
                "speaker": speaker_name,
                "confidence": confidence,
                "is_owner": is_owner,
                "timestamp": time.strftime("%I:%M %p")
            })

            target_url = check_and_broadcast_url(user_command)

            if user_command.lower() in ["stop", "never mind", "cancel", "go to sleep", "sleep"]:
                reply = "Going to standby."
                broadcast_sync({
                    "type": "new_message",
                    "session_id": session_id,
                    "role": "assistant",
                    "text": reply,
                    "timestamp": time.strftime("%I:%M %p")
                })
                if not app_state["voice_muted"]:
                    speaker.speak(reply)
                    speaker.play_chime("sleep")
                update_status("idle")
                continue

            update_status("thinking")
            start_time = time.time()
            reply = brain.query(user_command, source="voice", session_id=session_id, speaker=speaker_name, is_owner=is_owner)
            latency = round(time.time() - start_time, 2)

            broadcast_sync({
                "type": "new_message",
                "session_id": session_id,
                "role": "assistant",
                "text": reply,
                "url": target_url,
                "latency": latency,
                "timestamp": time.strftime("%I:%M %p"),
                "sessions": storage.get_all_sessions()
            })

            if not app_state["voice_muted"]:
                update_status("speaking")
                speaker.speak(reply)

            update_status("idle")

        except Exception as e:
            print(f"[Voice Loop Notice] {e}")
            update_status("idle")
            time.sleep(1)

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    listener_thread = threading.Thread(target=voice_listener_background, daemon=True)
    listener_thread.start()

def run_server():
    if not acquire_single_instance_lock():
        print("[Wednesday] Instance already running in background.")
        sys.exit(0)

    print("\n========================================================")
    print("      WEDNESDAY AI VOICE AGENT - LIVE DASHBOARD        ")
    print("========================================================")
    print(" [Web UI URL]: http://localhost:8000")
    print(" [Voice Recognition]: Voice Biometrics & Multi-Engine STT Enabled")
    print(" [Storage]: Supabase Cloud Database (PostgreSQL)")
    print("========================================================\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

if __name__ == "__main__":
    run_server()
