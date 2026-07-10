# =============================================================================
# MikroTik → Syslog Server (FortiAnalyzer-style)
# IP سرور Debian را جایگزین SERVER_IP کنید
# Import: /import file-name=full-logging-setup.rsc
# =============================================================================

:local serverIP "SERVER_IP"
:local serverPort SERVER_PORT

# --- 1. تنظیم action remote ---
/system/logging/action/set [find name=remote] remote=$serverIP remote-port=$serverPort target=remote bsd-syslog=yes syslog-facility=daemon syslog-time-format=iso8601

# --- 2. حذف قوانین remote تکراری (اختیاری) ---
# :foreach i in=[/system logging find action=remote] do={ /system logging remove $i }

# --- 3. فوروارد تمام topicهای لازم برای تحلیل ---

# ورود/خروج admin و کاربران روتر
/system/logging/add action=remote topics=account

# DHCP — تخصیص IP
/system/logging/add action=remote topics=dhcp

# DNS — resolve دامنه‌ها
/system/logging/add action=remote topics=dns

# Firewall — accept/drop/nat
/system/logging/add action=remote topics=firewall

# Hotspot — login/logout کاربران
/system/logging/add action=remote topics=hotspot

# PPP/VPN — L2TP, SSTP, PPTP, PPPoE, OVPN
/system/logging/add action=remote topics=ppp

# Wireless — WiFi
/system/logging/add action=remote topics=wireless

# System — رویدادهای سیستم
/system/logging/add action=remote topics=system

# Route — BGP/OSPF
/system/logging/add action=remote topics=route

# Info/Warning/Error
/system/logging/add action=remote topics=info,warning,error,critical

# Event — رویدادهای RouterOS
/system/logging/add action=remote topics=event

# Script
/system/logging/add action=remote topics=script

# --- 4. فعال‌سازی accounting برای Hotspot (ترافیک کاربران) ---
/ip/hotspot/print
# اگر Hotspot دارید، accounting را فعال کنید:
# /ip hotspot profile set [find default=yes] accounting=yes transparent-proxy=no

# --- 5. فعال‌سازی لاگ PPP (اتصال/قطع VPN) ---
/ppp/aaa/print
# /ppp aaa set use-radius=no accounting=yes

# --- 6. Firewall log برای ترافیک (اختیاری — حجم بالا) ---
# /ip firewall filter add chain=forward action=log log-prefix=FWD place-before=0
# /ip firewall filter add chain=input action=log log-prefix=IN

# --- 7. بررسی ---
# /system logging print
# /log print where topics~"ppp"
# /log print where topics~"hotspot"
# /log print where topics~"account"

# =============================================================================
# بعد از import:
#   سرور Debian: http://SERVER_IP:8080
#   Syslog UDP:   SERVER_IP:SERVER_PORT
# =============================================================================
