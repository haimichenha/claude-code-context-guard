@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\scripts\claude-dispatch.ps1" -c %*
exit /b %ERRORLEVEL%
