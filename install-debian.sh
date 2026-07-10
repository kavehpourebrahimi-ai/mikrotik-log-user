#!/usr/bin/env bash
# نصب MikroTik 4D Syslog Analyzer روی Ubuntu / Debian
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/mikrotik-analyzer}"
SERVICE_USER="${SERVICE_USER:-mikrotik-analyzer}"

echo "=== نصب MikroTik Analyzer روی Ubuntu/Debian ==="

if [ "$(id -u)" -ne 0 ]; then
  echo "لطفاً با sudo اجرا کنید: sudo bash install-debian.sh"
  exit 1
fi

apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git

id "$SERVICE_USER" &>/dev/null || useradd -r -s /bin/false "$SERVICE_USER"

mkdir -p "$INSTALL_DIR"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || rsync -a --exclude='.git' "$SCRIPT_DIR/" "$INSTALL_DIR/"

cd "$INSTALL_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

if [ ! -f .env ]; then
  cp .env.example .env
fi

mkdir -p data/logs
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

cat > /etc/systemd/system/mikrotik-analyzer.service << EOF
[Unit]
Description=MikroTik 4D Syslog Analyzer
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/python main.py --dashboard
Restart=always
RestartSec=5

# Syslog needs port 514 (privileged) — use CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable mikrotik-analyzer
systemctl restart mikrotik-analyzer

SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ نصب کامل شد!"
echo ""
echo "  داشبورد:     http://${SERVER_IP}:8080"
echo "  Syslog UDP:  ${SERVER_IP}:514"
echo ""
echo "  روی MikroTik این دستورات را اجرا کنید:"
echo "  /system logging action set [find name=remote] remote=${SERVER_IP} remote-port=514"
echo "  (یا فایل mikrotik/forward-logs-to-server.rsc را import کنید)"
echo ""
echo "  وضعیت سرویس: systemctl status mikrotik-analyzer"
echo ""
