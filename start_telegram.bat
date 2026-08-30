@echo off
title Wednesday Telegram Assistant
cd /d "%~dp0"
echo ========================================================
echo   Starting Wednesday AI Telegram Bot & Remote Server
echo ========================================================
echo.
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe core\telegram_bot.py
) else (
    python core\telegram_bot.py
)
pause
