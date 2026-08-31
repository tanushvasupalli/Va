@echo off
title Wednesday AI - Transfer Exact Project to Phone
cd /d "%~dp0"
echo ========================================================
echo   Packaging Exact Project for Vivo Y15 / Android
echo ========================================================
python scripts/export_to_phone.py
pause
