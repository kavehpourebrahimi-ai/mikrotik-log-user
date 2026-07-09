@echo off
setlocal
cd /d "%~dp0\.."
set SERVICE_NAME=EnterpriseVmsServer
set BIN_PATH="%~dp0\..\bin\vms_server.exe" --service
sc query "%SERVICE_NAME%" >nul 2>&1
if %ERRORLEVEL%==0 (
  echo Service %SERVICE_NAME% already exists.
  exit /b 0
)
sc create "%SERVICE_NAME%" binPath= "%BIN_PATH%" start= auto DisplayName= "Enterprise VMS Server"
sc description "%SERVICE_NAME%" "Enterprise VMS Server Service"
sc start "%SERVICE_NAME%"
echo Service installed and started.
endlocal
