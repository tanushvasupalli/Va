@echo off
title Wednesday AI Voice Agent
cd /d "%~dp0"
call ".\venv\Scripts\activate.bat"
python main.py
pause
