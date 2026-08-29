@echo off
setlocal
cd /d "%~dp0.."
echo ========================================================
echo   Enabling Wednesday AI Windows Background Autostart
echo ========================================================

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Startup'), 'WednesdayAI.lnk')); $s.TargetPath = 'wscript.exe'; $s.Arguments = '\"%~dp0start_silent_background.vbs\"'; $s.WorkingDirectory = '%~dp0..'; $s.Save()"

echo [Success] Wednesday AI will now start automatically in the background when your PC boots up!
echo ========================================================
pause
