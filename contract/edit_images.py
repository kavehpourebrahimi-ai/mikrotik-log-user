#!/usr/bin/env python3
"""Edit scanned contract images in-place with requested text changes."""

from __future__ import annotations

import re
from pathlib import Path

import arabic_reshaper
import cv2
import easyocr
import numpy as np
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
ORIGINAL_DIR = ROOT / "original"
EDITED_DIR = ROOT / "edited"
FONT_PATH = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"

# Persian and ASCII digit variants for matching/replacement
DIGIT_MAP = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_persian_digits(value: str) -> str:
    return value.translate(DIGIT_MAP)


def fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def normalize_digits(text: str) -> str:
    return text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size)


def cover_box(draw: ImageDraw.ImageDraw, box, padding: int = 4, fill=(255, 255, 255)):
    x1, y1, x2, y2 = box
    draw.rectangle(
        [x1 - padding, y1 - padding, x2 + padding, y2 + padding],
        fill=fill,
        outline=fill,
    )


def draw_rtl_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box,
    font: ImageFont.FreeTypeFont,
    fill=(0, 0, 0),
):
    x1, y1, x2, y2 = box
    shaped = fa(text)
    bbox = draw.textbbox((0, 0), shaped, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = x2 - text_w
    y = y1 + max(0, ((y2 - y1) - text_h) // 2)
    draw.text((x, y), shaped, font=font, fill=fill)


def replace_text_in_region(
    image: Image.Image,
    reader: easyocr.Reader,
    region: tuple[int, int, int, int],
    old_patterns: list[str],
    new_text: str,
    font_size: int | None = None,
) -> bool:
    img_np = np.array(image)
    x1, y1, x2, y2 = region
    crop = img_np[y1:y2, x1:x2]
    results = reader.readtext(crop, detail=1, paragraph=False)

    draw = ImageDraw.Draw(image)
    replaced = False

    for box_pts, text, _conf in results:
        norm = normalize_digits(text)
        if not any(re.search(pat, norm) for pat in old_patterns):
            continue

        xs = [int(p[0]) for p in box_pts]
        ys = [int(p[1]) for p in box_pts]
        abs_box = (
            min(xs) + x1,
            min(ys) + y1,
            max(xs) + x1,
            max(ys) + y1,
        )
        h = abs_box[3] - abs_box[1]
        size = font_size or max(14, int(h * 0.85))
        font = load_font(size)
        cover_box(draw, abs_box, padding=6)
        draw_rtl_text(draw, new_text, abs_box, font)
        replaced = True

    return replaced


def edit_page1(image: Image.Image, reader: easyocr.Reader) -> Image.Image:
    w, h = image.size
    replace_text_in_region(
        image,
        reader,
        (0, 0, int(w * 0.35), int(h * 0.12)),
        [r"1396", r"۱۳۹۶"],
        to_persian_digits("1397/12/28"),
    )
    replace_text_in_region(
        image,
        reader,
        (0, int(h * 0.55), w, h),
        [r"1397/01/01", r"۱۳۹۷/۰۱/۰۱"],
        to_persian_digits("1398/01/01"),
        font_size=18,
    )
    replace_text_in_region(
        image,
        reader,
        (0, int(h * 0.55), w, h),
        [r"1397/12/29", r"۱۳۹۷/۱۲/۲۹"],
        to_persian_digits("1398/12/29"),
        font_size=18,
    )
    return image


def edit_page2(image: Image.Image, reader: easyocr.Reader) -> Image.Image:
    w, h = image.size
    replace_text_in_region(
        image,
        reader,
        (0, 0, int(w * 0.35), int(h * 0.12)),
        [r"1396", r"۱۳۹۶"],
        to_persian_digits("1397/12/28"),
    )
    replace_text_in_region(
        image,
        reader,
        (0, int(h * 0.08), w, int(h * 0.35)),
        [r"16,?000,?000", r"۱۶,?۰۰۰,?۰۰۰", r"16000000", r"۱۶۰۰۰۰۰۰"],
        to_persian_digits("30,000,000"),
        font_size=20,
    )
    return image


def edit_page3(image: Image.Image, reader: easyocr.Reader) -> Image.Image:
    w, h = image.size
    replace_text_in_region(
        image,
        reader,
        (0, 0, int(w * 0.35), int(h * 0.12)),
        [r"1396", r"۱۳۹۶"],
        to_persian_digits("1397/12/28"),
    )
    return image


def process_images():
    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    EDITED_DIR.mkdir(parents=True, exist_ok=True)

    images = sorted(
        [
            *ORIGINAL_DIR.glob("*.jpg"),
            *ORIGINAL_DIR.glob("*.jpeg"),
            *ORIGINAL_DIR.glob("*.png"),
            *ORIGINAL_DIR.glob("*.webp"),
        ]
    )
    if len(images) < 3:
        raise SystemExit(
            f"لطفاً ۳ تصویر را در پوشه {ORIGINAL_DIR} قرار دهید "
            f"(page1.jpg, page2.jpg, page3.jpg)"
        )

    editors = [edit_page1, edit_page2, edit_page3]
    reader = easyocr.Reader(["fa", "en"], gpu=False)

    for idx, src in enumerate(images[:3]):
        image = Image.open(src).convert("RGB")
        edited = editors[idx](image, reader)
        out = EDITED_DIR / f"page{idx + 1}_edited{src.suffix}"
        edited.save(out, quality=95)
        print(f"Saved: {out}")


if __name__ == "__main__":
    process_images()
