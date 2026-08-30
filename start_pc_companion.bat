@echo off
title Wednesday PC Companion Agent
cd /d "%~dp0"
echo ========================================================
echo   Starting Wednesday PC Companion Agent (Remote Access)
echo ========================================================
echo.
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe pc_companion.py
) else (
    python pc_companion.py
)
pause
