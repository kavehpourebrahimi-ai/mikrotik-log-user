@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === VMS Mobile Bridge - install ===
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo pip install failed
    pause
    exit /b 1
)

if not exist config.ini (
    copy /Y config.example.ini config.ini
    echo Created config.ini - please edit record_root and ffmpeg paths if needed.
)

echo.
echo Done. Next: edit config.ini, then double-click start.bat
pause
