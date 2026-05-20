@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\scripts\ccrun.ps1" %*
exit /b %ERRORLEVEL%
