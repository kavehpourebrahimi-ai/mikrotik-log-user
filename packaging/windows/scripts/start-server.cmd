@echo off
setlocal
cd /d "%~dp0\.."
if not exist "data" mkdir "data"
if not exist "logs" mkdir "logs"
echo Starting Enterprise VMS Server...
start "Enterprise VMS Server" /D "%~dp0\..\bin" "%~dp0\..\bin\vms_server.exe"
echo Server started. API: http://127.0.0.1:8080/api/v1/health
endlocal
