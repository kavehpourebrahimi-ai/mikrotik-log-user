#!/usr/bin/env bash
set -euo pipefail

echo "🔧 Installing MikroTik 4D Syslog Analyzer..."

python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate

pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ ! -f .env ]; then
  cp .env.example .env
  echo "📋 Created .env — edit MIKROTIK_HOST and credentials"
fi

mkdir -p data/logs

echo ""
echo "✅ Installation complete!"
echo ""
echo "  CLI:        python main.py"
echo "  Dashboard:  python main.py --dashboard"
echo "  Browser:    http://<MIKROTIK_IP>:8080"
echo ""
