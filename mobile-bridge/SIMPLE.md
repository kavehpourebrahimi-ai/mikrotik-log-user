# VMS Mobile — راهنمای ساده

## پروژه قبلی را پاک نکنید — همین `mobile-bridge` را ادامه دهید

این همان پروژه است، فقط کامل‌تر شده.

---

## چه کار می‌کند؟

```
مرورگر  →  mobile-bridge (روی سرور VMS)  →  دیتابیس + آرشیو + دوربین
```

| قابلیت | توضیح |
|--------|--------|
| لیست دوربین | از دیتابیس `surveillancesystem` |
| لایو | user/pass از DB، ONVIF یا مسیر `/0` `/1` |
| Main / Sub | دکمه در صفحه دوربین |
| چندتایی | تب «چندتایی» — پیش‌نمایش Sub هر ۴ ثانیه |
| ضبط با زمان دقیق | انتخاب تاریخ + ساعت + دکمه پخش |
| ONVIF | خودکار از DB — `use_onvif = true` |

---

## نصب

1. Python + ffmpeg در `C:\ffmpeg`
2. `install.bat`
3. `config.ini` را ویرایش کنید
4. `start.bat`
5. `http://IP-سرور:8080/`

```ini
[tools]
ffmpeg_bin = C:\ffmpeg\bin\ffmpeg.exe
ffprobe_bin = C:\ffmpeg\bin\ffprobe.exe
[archive]
record_root = E:\VMS\Record
[live]
use_onvif = true
copy_codec = true
```

---

## نکته CPU

`copy_codec = true` → سرور فقط پروکسی می‌کند، decode روی مرورگر/ویندوز شما.

ffmpeg فقط برای بسته‌بندی استریم لازم است، نه تبدیل کدک.
