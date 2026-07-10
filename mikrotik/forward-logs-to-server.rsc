# ============================================================
# فوروارد کامل لاگ‌های MikroTik به سرور Ubuntu/Debian
# IP سرور جمع‌آوری لاگ را جایگزین کنید: SERVER_IP
# ============================================================

:local serverIP "192.168.88.100"
:local serverPort 514

/system/logging/action/set [find name=remote] remote=$serverIP remote-port=$serverPort target=remote bsd-syslog=yes syslog-facility=daemon

# حذف قوانین remote قبلی (اختیاری — اگر تکراری شد)
# /system logging remove [find action=remote]

/system/logging/add action=remote topics=info,warning,error,critical
/system/logging/add action=remote topics=account
/system/logging/add action=remote topics=dhcp
/system/logging/add action=remote topics=dns
/system/logging/add action=remote topics=firewall
/system/logging/add action=remote topics=hotspot
/system/logging/add action=remote topics=ppp
/system/logging/add action=remote topics=wireless
/system/logging/add action=remote topics=system
/system/logging/add action=remote topics=route

# فعال‌سازی لاگ account برای ورود به روتر
/system/logging/add action=remote topics=account,info

# بررسی:
# /system logging print
# /log print where topics~"account"

# ============================================================
# SERVER_IP = IP سرور Ubuntu/Debian که analyzer روش نصب شده
# بعد از اجرا، داشبورد: http://SERVER_IP:8080
# ============================================================
