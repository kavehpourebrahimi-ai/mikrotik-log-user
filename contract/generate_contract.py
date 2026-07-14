#!/usr/bin/env python3
"""Generate modified Mazandaran University contract PDF."""

from pathlib import Path

from arabic_reshaper import reshape
from bidi.algorithm import get_display
from fpdf import FPDF

FONT_PATH = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"
FONT_LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
OUTPUT = Path(__file__).parent / "قرارداد_ویرایش_شده.pdf"


def fa(text: str) -> str:
    return get_display(reshape(text))


class ContractPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.add_font("Noto", "", FONT_PATH)
        self.add_font("Noto", "B", FONT_BOLD_PATH)
        self.add_font("Latin", "", FONT_LATIN)
        self.set_auto_page_break(auto=True, margin=20)

    def header_block(self):
        self.set_font("Noto", "", 10)
        self.cell(0, 6, fa("تاریخ: ۱۳۹۷/۱۲/۲۸"), align="L", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, fa("شماره: ۶/۹۶/۲۱۴"), align="L", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, fa("پیوست:"), align="L", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def university_header(self):
        self.set_font("Noto", "B", 11)
        self.cell(0, 7, fa("دانشگاه علم و فناوری مازندران"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Noto", "", 9)
        self.cell(0, 5, fa("وزارت علوم، تحقیقات و فناوری"), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def doc_title(self, text: str):
        self.set_font("Noto", "B", 16)
        self.cell(0, 12, fa(text), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def paragraph(self, text: str, bold: bool = False):
        self.set_font("Noto", "B" if bold else "", 10)
        self.multi_cell(0, 7, fa(text), align="R")
        self.ln(1)

    def footer_info(self):
        self.set_y(-25)
        self.set_font("Noto", "", 8)
        self.multi_cell(
            0,
            4,
            fa(
                "آدرس: بهشهر، مازندران  |  کد پستی: ۴۸۵۱۸-۷۸۱۹۵  |  "
                "تلفن: ۰۱۱۳۴۵۵۲۰۰۷  |  فکس: ۰۱۱۳۴۵۵۲۰۰۸"
            ),
            align="C",
        )


def build_pdf():
    pdf = ContractPDF()

    # Page 1
    pdf.add_page()
    pdf.header_block()
    pdf.university_header()
    pdf.doc_title("قرارداد")
    pdf.paragraph(
        "این قرارداد فی‌مابین کارفرما: دانشگاه علم و فناوری مازندران "
        "به نمایندگی دکتر حمید محمدزاده (رئیس دانشگاه) و مجری: "
        "آقای مهندس کاوه پورابراهیمی فومنی فرزند عباس منعقد می‌گردد."
    )

    pdf.paragraph("ماده ۱: موضوع قرارداد", bold=True)
    pdf.paragraph(
        "موضوع قرارداد عبارت است از ارائه خدمات فنی و پشتیبانی شبکه و "
        "سیستم‌های رایانه‌ای دانشگاه شامل موارد زیر:\n"
        "۱- نگهداری و پشتیبانی شبکه فیبر نوری و بی‌سیم\n"
        "۲- نگهداری و پشتیبانی تجهیزات امنیتی شبکه (Fortigate)\n"
        "۳- نگهداری و پشتیبانی دوربین‌های مداربسته (CCTV)\n"
        "۴- نگهداری و پشتیبانی سرورها و سرویس‌های شبکه\n"
        "۵- عیب‌یابی و رفع مشکلات سخت‌افزاری و نرم‌افزاری\n"
        "۶- پشتیبانی کاربران و سیستم‌های اداری\n"
        "۷- نصب، راه‌اندازی و به‌روزرسانی تجهیزات شبکه\n"
        "۸- پشتیبانی سیستم‌های تلفنی و VoIP\n"
        "۹- پشتیبانی سیستم‌های پشتیبان‌گیری (Backup)\n"
        "۱۰- نظارت و مانیتورینگ شبکه\n"
        "۱۱- مدیریت دسترسی کاربران\n"
        "۱۲- پشتیبانی سیستم‌های ضبط تصاویر\n"
        "۱۳- رفع اشکالات سیستم‌های کامپیوتری\n"
        "۱۴- پشتیبانی نرم‌افزارهای اداری\n"
        "۱۵- سایر خدمات مرتبط با حوزه فناوری اطلاعات"
    )

    pdf.paragraph("ماده ۲: مدت قرارداد", bold=True)
    pdf.paragraph(
        "مدت این قرارداد از تاریخ ۱۳۹۸/۰۱/۰۱ لغایت ۱۳۹۸/۱۲/۲۹ می‌باشد."
    )
    pdf.footer_info()

    # Page 2
    pdf.add_page()
    pdf.header_block()
    pdf.university_header()

    pdf.paragraph("ماده ۳: حق‌الزحمه قرارداد", bold=True)
    pdf.paragraph(
        "مبلغ قرارداد به صورت ماهانه مبلغ ۳۰,۰۰۰,۰۰۰ ریال تعیین می‌گردد "
        "که به شماره حساب ۱۰,۶۷۸۰۵۶۴,۱ نزد بانک رسالت به نام کاوه پورابراهیمی "
        "فومنی واریز خواهد شد.\n"
        "تبصره: کارفرما می‌تواند حجم کار را تا ۲۵٪ افزایش یا کاهش دهد "
        "که در این صورت مبلغ قرارداد متناسب با آن تعدیل می‌گردد."
    )

    pdf.paragraph("ماده ۴: تعهدات کارپذیر (مجری)", bold=True)
    pdf.paragraph(
        "۴-۱- رعایت اصول حرفه‌ای، اخلاقی و اداری در انجام کار.\n"
        "۴-۲- حفظ محرمانگی اطلاعات پروژه و عدم افشای آن به اشخاص ثالث.\n"
        "۴-۳- مسئولیت جبران خسارات ناشی از قصور در انجام پروژه.\n"
        "۴-۴- اعلام اینکه مجری بازنشسته دولتی نمی‌باشد.\n"
        "۴-۵- دارا بودن مجوزها و صلاحیت قانونی لازم برای انجام کار.\n"
        "۴-۶- فاقد سابقه کیفری و امنیتی بودن.\n"
        "۴-۷- این قرارداد ایجاد رابطه استخدامی نمی‌نماید."
    )
    pdf.footer_info()

    # Page 3
    pdf.add_page()
    pdf.header_block()
    pdf.university_header()

    pdf.paragraph(
        "۴-۸- رعایت مقررات بیمه‌ای مربوطه.\n"
        "۴-۹- رعایت قوانین مبارزه با رشوه و فساد."
    )

    pdf.paragraph("ماده ۵: تعهدات کارفرما", bold=True)
    pdf.paragraph(
        "۵-۱- فراهم نمودن امکانات لازم برای انجام موضوع قرارداد.\n"
        "۵-۲- پرداخت حق‌الزحمه مطابق ماده ۳ قرارداد.\n"
        "۵-۳- همکاری لازم با مجری در انجام تعهدات قراردادی."
    )

    pdf.paragraph("ماده ۶: موارد حل اختلاف", bold=True)
    pdf.paragraph(
        "در صورت بروز اختلاف، طرفین ابتدا از طریق مذاکره و سازش اقدام "
        "می‌نمایند و در صورت عدم توافق، موضوع از طریق مراجع قانونی "
        "پیگیری خواهد شد."
    )

    pdf.paragraph("ماده ۷: مبادله قرارداد", bold=True)
    pdf.paragraph(
        "این قرارداد در ۷ ماده و در ۴ نسخه تنظیم و مبادله گردید که "
        "هر نسخه حکم واحد را دارد."
    )

    pdf.ln(8)
    pdf.set_font("Noto", "", 10)
    pdf.cell(95, 8, fa("کارفرما: حمید محمدزاده - رئیس دانشگاه"), align="R")
    pdf.cell(95, 8, fa("مجری: کاوه پورابراهیمی فومنی"), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Noto", "", 9)
    pdf.paragraph(
        "رونوشت:\n"
        "۱- مجری\n"
        "۲- دفتر قراردادها\n"
        "۳- دفتر مالی\n"
        "۴- ناظر قرارداد"
    )
    pdf.footer_info()

    pdf.output(str(OUTPUT))
    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
