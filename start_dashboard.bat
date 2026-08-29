@echo off
title Wednesday AI Dashboard
cd /d "%~dp0"
call ".\venv\Scripts\activate.bat"
python -m dashboard.app
pause
