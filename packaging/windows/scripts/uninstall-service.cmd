@echo off
setlocal
set SERVICE_NAME=EnterpriseVmsServer
sc stop "%SERVICE_NAME%" >nul 2>&1
sc delete "%SERVICE_NAME%"
echo Service removed (if it existed).
endlocal
