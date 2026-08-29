@echo off
title GitHub Push - Wednesday AI
cd /d "%~dp0"
echo ========================================================
echo   Pushing Wednesday AI Voice Agent to GitHub
echo ========================================================
echo.
set GCM_OAUTH_FLOW=device
set GCM_INTERACTIVE=always
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Code pushed successfully to GitHub!
) else (
    echo [ERROR] Push encountered an issue.
)
echo.
pause

