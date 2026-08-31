@echo off
setlocal
cd /d "%~dp0"
call ".\venv\Scripts\python.exe" -c "from core.toggle_service import toggle_wednesday; ok, msg = toggle_wednesday(); print(msg)"
ping 127.0.0.1 -n 2 >nul
