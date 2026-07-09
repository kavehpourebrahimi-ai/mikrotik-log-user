@echo off
setlocal
cd /d "%~dp0\.."
start "Enterprise VMS Web UI" "http://127.0.0.1:8080/"
endlocal
