# راهنمای نصب روی Debian/Ubuntu — MikroTik Log Analyzer
# (شبیه FortiAnalyzer برای MikroTik)

## مرحله ۱ — نصب روی سرور Debian

```bash
git clone https://github.com/kavehpourebrahimi-ai/mikrotik-log-user.git
cd mikrotik-log-user
sudo bash install-debian.sh
```

بعد از نصب:
- **داشبورد:** `http://IP_سرور:8080`
- **Syslog:** `IP_سرور:514/udp`

---

## مرحله ۲ — تنظیم MikroTik (فوروارد لاگ)

### روش A — Import فایل (ساده‌تر)

1. فایل `mikrotik/full-logging-setup.rsc` را باز کنید
2. `SERVER_IP` را با IP سرور Debian عوض کنید (مثلاً `192.168.88.100`)
3. فایل را به MikroTik آپلود کنید (Files → Upload)
4. در Terminal:

```
/import file-name=full-logging-setup.rsc
```

### روش B — دستی در Terminal MikroTik

```
/system logging action set [find name=remote] remote=192.168.88.100 remote-port=514 target=remote bsd-syslog=yes
/system logging add action=remote topics=account
/system logging add action=remote topics=dhcp
/system logging add action=remote topics=dns
/system logging add action=remote topics=firewall
/system logging add action=remote topics=hotspot
/system logging add action=remote topics=ppp
/system logging add action=remote topics=wireless
/system logging add action=remote topics=system
/system logging add action=remote topics=info,warning,error,critical
```

---

## مرحله ۳ — فعال‌سازی accounting (ترافیک کاربران)

### Hotspot — ترافیک و uptime

```
/ip hotspot profile set [find default=yes] accounting=yes
```

### PPP/VPN — L2TP, SSTP, PPTP

```
/ppp aaa set accounting=yes
```

---

## مرحله ۴ — باز کردن داشبورد

1. مرورگر: `http://192.168.88.100:8080`
2. IP MikroTik + user + password → **اتصال**
3. تیک **syslog** را بزنید تا remote logging خودکار تنظیم شود

---

## تب‌های داشبورد (مثل FortiAnalyzer)

| تب | محتوا |
|----|--------|
| **کاربران** | همه لاگ‌های هر کاربر — VPN + Hotspot + ورود |
| **PPP/VPN** | L2TP, SSTP, IPIP, PPTP — IP مبدأ/مقصد، uptime، ترافیک |
| **Hotspot** | کاربران آنلاین + login/logout |
| **DNS** | کلاینت → دامنه → IP resolve |
| **پشته لاگ** | تمام syslog ذخیره‌شده در SQLite |

---

## عیب‌یابی

```bash
# وضعیت سرویس
sudo systemctl status mikrotik-analyzer

# لاگ سرویس
sudo journalctl -u mikrotik-analyzer -f

# تست syslog
echo "test" | nc -u IP_سرور 514
```

---

## Firewall سرور Debian

```
ufw allow 8080/tcp
ufw allow 514/udp
```

## Firewall MikroTik

مطمئن شوید UDP 514 از MikroTik به سرور Debian مسدود نیست.
