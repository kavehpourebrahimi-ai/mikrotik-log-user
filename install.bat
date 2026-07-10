@echo off
echo Installing MikroTik 4D Syslog Analyzer...
python -m venv .venv
call .venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q
if not exist .env copy .env.example .env
if not exist data\logs mkdir data\logs
echo.
echo Installation complete!
echo   CLI:        python main.py
echo   Dashboard:  python main.py --dashboard
echo   Browser:    http://MIKROTIK_IP:8080
pause
