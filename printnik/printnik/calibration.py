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


def create_registration_test_package(output: Path, *, left_mm: float = 10, right_mm: float = 10,
                                     top_mm: float = 10, bottom_mm: float = 10,
                                     length_mm: float = 20, dpi: int = 300,
                                     image_source: Path | None = None, image_height_mm: float = 50) -> dict:
    """Create an A4 print experiment with artwork beside the lower-left mark."""
    offsets = {"left_mm": left_mm, "right_mm": right_mm,
               "top_mm": top_mm, "bottom_mm": bottom_mm}
    if any(not isinstance(value, (int, float)) or not 2 <= value <= 40 for value in offsets.values()):
        raise ValueError("Каждый отступ должен быть от 2 до 40 мм.")
    if not 5 <= length_mm <= 30:
        raise ValueError("Длина метки должна быть от 5 до 30 мм.")
    if left_mm + right_mm + 2 * length_mm >= 210 or top_mm + bottom_mm + 2 * length_mm >= 297:
        raise ValueError("Регистрационные метки пересекаются.")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    px = lambda mm: round(mm / 25.4 * dpi)
    page = Image.new("RGB", (px(210), px(297)), "white")
    draw = ImageDraw.Draw(page)
    corners_mm = [
        ((left_mm, top_mm), (left_mm + length_mm, top_mm), (left_mm, top_mm + length_mm)),
        ((210 - right_mm, top_mm), (210 - right_mm - length_mm, top_mm), (210 - right_mm, top_mm + length_mm)),
        ((left_mm, 297 - bottom_mm), (left_mm + length_mm, 297 - bottom_mm),
         (left_mm, 297 - bottom_mm - length_mm)),
        ((210 - right_mm, 297 - bottom_mm), (210 - right_mm - length_mm, 297 - bottom_mm),
         (210 - right_mm, 297 - bottom_mm - length_mm)),
    ]
    for origin, horizontal, vertical in corners_mm:
        draw.line([tuple(map(px, origin)), tuple(map(px, horizontal))], fill="black", width=max(2, px(0.45)))
        draw.line([tuple(map(px, origin)), tuple(map(px, vertical))], fill="black", width=max(2, px(0.45)))
    image_box_mm = None
    if image_source is not None:
        source = Image.open(image_source).convert("RGBA")
        alpha_box = source.getchannel("A").getbbox()
        if alpha_box is None:
            raise ValueError("Выбранное изображение полностью прозрачное.")
        source = source.crop(alpha_box)
        image_width_mm = image_height_mm * source.width / source.height
        x_mm = left_mm + length_mm + 4
        y_mm = 297 - bottom_mm - image_height_mm
        if not 20 <= image_height_mm <= 80 or y_mm < top_mm + length_mm + 4:
            raise ValueError("Изображение не помещается по высоте рядом с нижней меткой.")
        if x_mm + image_width_mm > 210 - right_mm - length_mm - 4:
            raise ValueError("Изображение не помещается между регистрационными метками.")
        source = source.resize((px(image_width_mm), px(image_height_mm)), Image.Resampling.LANCZOS)
        page.paste(source, (px(x_mm), px(y_mm)), source)
        image_box_mm = {"left": x_mm, "top": y_mm,
                        "right": x_mm + image_width_mm, "bottom": y_mm + image_height_mm}
    draw.line([(px(80), px(45)), (px(130), px(45))], fill="black", width=max(2, px(0.3)))
    draw.text((px(82), px(48)), "50 mm", fill="black", font=_font(max(12, px(2.4))))
    pdf = output / "registration-test-print.pdf"
    png = output / "registration-test-preview.png"
    page.save(png, dpi=(dpi, dpi))
    page.save(pdf, "PDF", resolution=dpi)
    manifest = {"status": "experimental_unverified", "print_pdf": str(pdf), "preview_png": str(png),
                "page_mm": [210, 297], "offsets_mm": offsets, "length_mm": length_mm,
                "mark_origins_mm": [list(origin) for origin, _, _ in corners_mm],
                "image_source": str(image_source) if image_source is not None else None,
                "image_box_mm": image_box_mm,
                "cut_file": None,
                "test_requirements": ["Проверить, что принтер напечатал все четыре метки целиком.",
                                      "Проверить считывание всех меток Cameo отдельным пробным режимом.",
                                      "Лишь затем проверять совпадение реза с печатью."]}
    (output / "registration-test.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")
    return manifest


def create_first_cut_test_package(output: Path, dpi: int = 300) -> dict:
    """Make a fixed 25 mm registration sheet with one small lower-left target.

    This package contains a *plan* for a 48 mm square cut, not executable USB
    commands. The first direct-cut implementation must validate it separately.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    px = lambda mm: round(mm / 25.4 * dpi)
    page = Image.new("RGB", (px(210), px(297)), "white")
    draw = ImageDraw.Draw(page)
    corners = [
        ((10, 10), (30, 10), (10, 30)),
        ((200, 10), (180, 10), (200, 30)),
        ((10, 272), (30, 272), (10, 252)),
        ((200, 272), (180, 272), (200, 252)),
    ]
    for origin, horizontal, vertical in corners:
        draw.line([tuple(map(px, origin)), tuple(map(px, horizontal))],
                  fill="black", width=max(2, px(0.45)))
        draw.line([tuple(map(px, origin)), tuple(map(px, vertical))],
                  fill="black", width=max(2, px(0.45)))
    draw.line((px(80), px(45), px(130), px(45)), fill="black", width=max(2, px(0.3)))
    draw.text((px(82), px(48)), "50 mm", fill="black", font=_font(max(12, px(2.4))))
    # One 12 x 12 mm target beside the successful lower-left registration mark.
    target = (50, 245, 62, 257)
    draw.rectangle(tuple(map(px, target)), outline="black", width=max(2, px(0.35)))
    draw.text((px(42), px(235)), "TEST 12 mm", fill="black",
              font=_font(max(12, px(2.4))))
    png = output / "first-cut-preview.png"
    pdf = output / "first-cut-print.pdf"
    page.save(png, dpi=(dpi, dpi))
    page.save(pdf, "PDF", resolution=dpi)
    path = [[50, 245], [62, 245], [62, 257], [50, 257], [50, 245]]
    manifest = {
        "status": "first_cut_prepared_not_sent",
        "page_mm": [210, 297],
        "offsets_mm": {"left_mm": 10, "right_mm": 10, "top_mm": 10, "bottom_mm": 25},
        "length_mm": 20,
        "mark_origins_mm": [[10, 10], [200, 10], [10, 272], [200, 272]],
        "target_box_mm": list(target),
        "cut_path_mm": path,
        "cut_length_mm": 48,
        "material_id": "matte_white",
        "print_pdf": str(pdf),
        "preview_png": str(png),
        "usb_cut_enabled": True,
    }
    (output / "first-cut.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
    # The existing scan-only button can verify these same printed marks before
    # any cutting code is enabled. It deliberately sees no cut path.
    scan_manifest = {
        "status": "experimental_unverified", "cut_file": None,
        "page_mm": [210, 297], "offsets_mm": manifest["offsets_mm"],
        "length_mm": 20, "mark_origins_mm": manifest["mark_origins_mm"],
        "print_pdf": str(pdf), "preview_png": str(png),
    }
    (output / "registration-test.json").write_text(
        json.dumps(scan_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest

