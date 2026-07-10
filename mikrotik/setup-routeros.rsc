# ============================================================
# MikroTik RouterOS 7.13 — 4D Syslog Analyzer Setup Script
# Run these commands on your MikroTik after enabling container mode
# ============================================================

# --- STEP 1: Enable container mode (requires physical button press) ---
# /system/device-mode/update container=yes

# --- STEP 2: Create container network ---
/interface/veth/add name=veth-analyzer address=172.17.0.2/24 gateway=172.17.0.1
/interface/bridge/add name=containers
/ip/address/add address=172.17.0.1/24 interface=containers
/interface/bridge/port add bridge=containers interface=veth-analyzer
/ip/firewall/nat/add chain=srcnat action=masquerade src-address=172.17.0.0/24 comment="container NAT"

# --- STEP 3: Container registry config (adjust disk path) ---
/container/config/set registry-url=https://registry-1.docker.io tmpdir=disk1/tmp

# --- STEP 4: Deploy the analyzer container ---
# Build image on a PC:  docker build -t mikrotik-4d-analyzer .
# Save & transfer:       docker save mikrotik-4d-analyzer | gzip > analyzer.tar.gz
# Import on MikroTik:
# /container/add file=analyzer.tar.gz interface=veth-analyzer root-dir=disk1/analyzer name=4d-analyzer start-on-boot=yes logging=yes
# /container/start 0

# --- STEP 5: Port forwarding — access dashboard at http://<ROUTER_IP>:8080 ---
/ip/firewall/nat/add chain=dstnat protocol=tcp dst-port=8080 action=dst-nat to-addresses=172.17.0.2 to-ports=8080 comment="4D Analyzer Web"
/ip/firewall/nat/add chain=dstnat protocol=udp dst-port=514 action=dst-nat to-addresses=172.17.0.2 to-ports=514 comment="4D Analyzer Syslog"

# --- STEP 6: Configure MikroTik to send FULL logs to the container ---
/system/logging/action/set [find name=remote] remote=172.17.0.2 remote-port=514 target=remote
/system/logging/add action=remote topics=info,warning,error,critical
/system/logging/add action=remote topics=dhcp,!debug
/system/logging/add action=remote topics=dns,!debug
/system/logging/add action=remote topics=firewall,!debug
/system/logging/add action=remote topics=hotspot,!debug
/system/logging/add action=remote topics=wireless,!debug
/system/logging/add action=remote topics=ppp,!debug

# --- STEP 7: Verify ---
# /container/print detail
# /log/print where topics~"dhcp"
# Open browser: http://192.168.88.1:8080  (replace with your router IP)

# ============================================================
# Alternative: Run dashboard on external PC/server
# Point MikroTik remote syslog to your PC IP instead of 172.17.0.2
# ============================================================
# /system/logging/action/set [find name=remote] remote=192.168.88.100 remote-port=514
# Then run on PC:  python main.py --dashboard
# Open: http://192.168.88.100:8080 and enter MikroTik IP to pull live data
