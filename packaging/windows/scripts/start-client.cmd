@echo off
setlocal
cd /d "%~dp0\.."
if "%~1"=="" (
  set SERVER_URL=http://127.0.0.1:8080
) else (
  set SERVER_URL=%~1
)
echo Starting Enterprise VMS Client...
"%~dp0\..\bin\vms_client.exe" --server %SERVER_URL%
endlocal
