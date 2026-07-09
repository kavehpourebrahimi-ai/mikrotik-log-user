@echo off
title Shinobi Operator Desk
echo.
echo ========================================
echo   Shinobi Operator Desk - Web Launcher
echo ========================================
echo.
echo This launcher opens the client in your browser.
echo You need a running Shinobi server URL to connect.
echo.
echo For the full Windows app (.exe), download the
echo release from GitHub Actions or Releases.
echo.

set PORT=4173
cd /d "%~dp0dist"

where npx >nul 2>nul
if errorlevel 1 (
    echo Node.js is not installed.
    echo Install Node.js from https://nodejs.org
    echo Then run this file again.
    pause
    exit /b 1
)

echo Starting local client on http://127.0.0.1:%PORT%
echo Press Ctrl+C to stop.
echo.
start "" "http://127.0.0.1:%PORT%"
npx --yes serve -l %PORT% .
