@echo off
setlocal
cd /d "%~dp0.."
echo ========================================================
echo         Stopping Wednesday AI Background Service
echo ========================================================

powershell -NoProfile -Command "$lock = 'data\wednesday.lock'; if (Test-Path $lock) { $pidToKill = Get-Content $lock; Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue; Remove-Item $lock -Force -ErrorAction SilentlyContinue; Write-Host '[Success] Wednesday background process stopped.' } else { Write-Host '[Notice] No active Wednesday lock file found.' }"

echo ========================================================
pause

