@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === VMS Mobile Bridge ===
echo Open in browser: http://localhost:8080/
echo.

python check_setup.py
if errorlevel 1 (
    echo.
    echo Fix the errors above, then run start.bat again.
    pause
    exit /b 1
)

python app.py
pause
