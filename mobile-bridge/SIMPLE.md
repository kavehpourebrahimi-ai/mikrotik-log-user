# VMS Mobile — راهنمای ساده

## چی می‌خواهیم؟

همان کاری که **کلاینت ویندوز** می‌کند، ولی در **مرورگر** (موبایل یا ویندوز):

```
مرورگر  →  این برنامه (روی سرور VMS)  →  دیتابیس + فایل‌های ضبط + دوربین‌ها
```

- **لیست دوربین** از دیتابیس `surveillancesystem`
- **یوزر/پسورد/IP** از جدول `device` (نیازی به وارد کردن دستی نیست)
- **لایو** از RTSP دوربین (سرور فقط پروکسی می‌کند، تصویر روی کلاینت decode می‌شود)
- **ضبط‌شده** از پوشه `E:\VMS\Record` (فایل‌های `.vdo`)

---

## نصب (۳ قدم)

### ۱) Python + ffmpeg

- Python 3.9+ از python.org
- ffmpeg: از https://www.gyan.dev/ffmpeg/builds/ در `C:\ffmpeg` extract کنید

### ۲) نصب

```
دوبار کلیک: install.bat
```

### ۳) تنظیم `config.ini`

```ini
[tools]
ffmpeg_bin = C:\ffmpeg\bin\ffmpeg.exe
ffprobe_bin = C:\ffmpeg\bin\ffprobe.exe

[archive]
record_root = E:\VMS\Record

[live]
rtsp_template = rtsp://{user}:{password}@{ip}:{port}/0
rtsp_port = 554
copy_codec = true
```

`copy_codec = true` یعنی **سرور تبدیل نمی‌کند** — CPU کم، decode روی مرورگر/موبایل.

---

## اجرا

```
دوبار کلیک: start.bat
```

در مرورگر: `http://IP-سرور:8080/`

مثال: `http://192.168.201.232:8080/`

---

## اگر لایو نیامد

برنامه خودش مسیر RTSP هر دوربین را پیدا می‌کند (`/0`, `/11`, ...).

یک دوربین را تست کنید:

```
python probe_one.py 192.168.21.5
```

---

## وب یا اندروید؟

**همین وب کافی است** — روی آیفون و اندروید و ویندوز باز می‌شود.
نیازی به اپ جداگانه نیست مگر بخواهید در آینده.
