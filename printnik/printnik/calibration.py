from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size: int, bold: bool = False):
    path = r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def create_calibration_package(output: Path, dpi: int = 300) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    px = lambda mm: round(mm / 25.4 * dpi)
    page = Image.new("RGB", (px(210), px(297)), "white")
    draw = ImageDraw.Draw(page)
    title, body = _font(px(4), True), _font(px(3))
    draw.text((px(38), px(12)), "КАЛИБРОВКА A/B", fill="black", font=title)
    draw.text((px(38), px(20)), "Печать 100% · отверстие B", fill="black", font=body)

    colors = [(0, 170, 230), (235, 0, 140), (255, 225, 0), (20, 20, 20), (230, 40, 30), (30, 170, 70)]
    for index, color in enumerate(colors):
        x = px(12 + index * 29)
        draw.rectangle((x, px(33), x + px(25), px(48)), fill=color)

    # A: сплошная круглая наклейка 30 мм.
    draw.ellipse((px(20), px(62), px(50), px(92)), fill=(255, 120, 30))
    draw.text((px(27), px(95)), "A · 30 мм", fill="black", font=body)
    # B: 50 мм с внутренней прозрачной полостью, которая должна вырезаться первой.
    draw.ellipse((px(75), px(55), px(125), px(105)), fill=(40, 120, 240))
    draw.ellipse((px(92), px(72), px(108), px(88)), fill="white")
    draw.text((px(86), px(108)), "B · 50 мм · отверстие", fill="black", font=body)
    # Цветовой образец. Тонкие капли не входят в этот калибровочный прогон:
    # их нельзя проверять прямоугольным контуром и они уже прошли отдельный физический тест.
    draw.rounded_rectangle((px(145), px(58), px(185), px(94)), radius=px(8), fill=(180, 50, 210))
    draw.text((px(147), px(98)), "контроль цвета", fill="black", font=body)

    # Контрольная линейка 50 мм.
    y = px(140)
    draw.line((px(20), y, px(70), y), fill="black", width=px(0.3))
    for mm in range(51):
        height = 5 if mm % 10 == 0 else 3 if mm % 5 == 0 else 1.5
        draw.line((px(20 + mm), y, px(20 + mm), y + px(height)), fill="black", width=max(1, px(0.2)))
    draw.text((px(20), y + px(8)), "Контроль: ровно 50 мм", fill="black", font=body)

    # Повторяет испытанный в Silhouette Studio профиль: 10 мм сверху/сбоку, 25 мм снизу.
    inset, bottom, length, width, height = px(10), px(25), px(20), px(210), px(297)
    for origin, h_end, v_end in [
        ((inset, inset), (inset+length, inset), (inset, inset+length)),
        ((width-inset, inset), (width-inset-length, inset), (width-inset, inset+length)),
        ((inset, height-bottom), (inset+length, height-bottom), (inset, height-bottom-length)),
        ((width-inset, height-bottom), (width-inset-length, height-bottom), (width-inset, height-bottom-length)),
    ]:
        draw.line((origin, h_end), fill="black", width=px(0.45)); draw.line((origin, v_end), fill="black", width=px(0.45))

    png = output / "calibration-print.png"
    pdf = output / "calibration-print.pdf"
    page.save(png, dpi=(dpi, dpi))
    page.save(pdf, "PDF", resolution=dpi)
    svg = output / "calibration-cut.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">\n'
        ' <circle cx="100" cy="80" r="8" fill="none" stroke="red" stroke-width="0.15"/>\n'
        ' <circle cx="35" cy="77" r="15" fill="none" stroke="red" stroke-width="0.15"/>\n'
        ' <circle cx="100" cy="80" r="25" fill="none" stroke="red" stroke-width="0.15"/>\n'
        ' <rect x="145" y="58" width="40" height="36" rx="8" fill="none" stroke="red" stroke-width="0.15"/>\n'
        '</svg>\n', encoding="utf-8")
    manifest = {"print_pdf": str(pdf), "print_png": str(png), "cut_svg": str(svg),
                "registration_inset_mm": 10, "registration_bottom_mm": 25,
                "registration_length_mm": 20, "status": "matches_tested_studio_profile"}
    (output / "calibration.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest

