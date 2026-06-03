@echo off
python "%USERPROFILE%\.claude\scripts\ensure-claude-context-policy.py" --quiet
python "%USERPROFILE%\.claude\scripts\ensure-claude-live-monitor.py" --quiet
call "%USERPROFILE%\.claude\scripts\context-policy-env.cmd"
call "%APPDATA%\npm\claude.cmd" --permission-mode auto -c %*
set _CLAUDE_EXIT=%ERRORLEVEL%
python "%USERPROFILE%\.claude\scripts\check-claude-context-errors.py" >NUL 2>NUL
exit /b %_CLAUDE_EXIT%
