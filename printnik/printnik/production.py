from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .catalog import AssetCatalog
from .dxf import bounds, path_points, render_dxf
from .materials import MaterialProfile
from .models import Order
from .prototype import (
    SIZES_MM, cut_mask_for_size, fill_internal_holes, grow_bleed,
    needs_small_contour_review, scaled_to_frame, simplify, trace_loops,
)
from .size_rules import validate_size_rule


@dataclass
class PreflightResult:
    asset_id: str
    source: str
    errors: list[str]
    warnings: list[str]


@dataclass
class PreparedSticker:
    asset_id: str
    size_code: str
    image: Image.Image
    print_image: Image.Image
    cut_mask: np.ndarray
    packing_mask_mm: np.ndarray
    pad_px: int
    dpi: int
    packing_pad_mm: int
    contour_review_required: bool = False

    def rotated(self) -> "PreparedSticker":
        return PreparedSticker(
            self.asset_id, self.size_code,
            self.image.rotate(90, expand=True), self.print_image.rotate(90, expand=True),
            np.rot90(self.cut_mask, 1).copy(), np.rot90(self.packing_mask_mm, 1).copy(),
            self.pad_px, self.dpi, self.packing_pad_mm,
            self.contour_review_required,
        )


@dataclass
class Placement:
    sticker: PreparedSticker
    x_mm: int
    y_mm: int
    rotated: bool


class PreflightError(RuntimeError):
    def __init__(self, results: list[PreflightResult]):
        self.results = results
        super().__init__("; ".join(error for result in results for error in result.errors))


def preflight(path: Path, asset_id: str, size_code: str, dpi: int = 300, *, allow_opaque: bool = False) -> PreflightResult:
    image = Image.open(path).convert("RGBA")
    alpha = np.array(image)[:, :, 3]
    errors: list[str] = []
    warnings: list[str] = []
    transparent_fraction = float(np.mean(alpha < 16))
    if transparent_fraction < 0.005:
        message = "Фон полностью непрозрачный: автоматический силуэт невозможен. Возможен прямоугольный рез."
        (warnings if allow_opaque else errors).append(message)
    if size_code not in SIZES_MM:
        errors.append(f"Размер {size_code} пока не поддерживается Печатником.")
    target_px = SIZES_MM.get(size_code, 180) / 25.4 * dpi
    if max(image.size) < target_px * 0.72:
        warnings.append("Исходник мал для выбранного размера; печать может потерять резкость.")
    if image.width < 20 or image.height < 20:
        errors.append("Файл слишком мал или повреждён.")
    return PreflightResult(asset_id, str(path), errors, warnings)


def _packing_mask(cut_mask: np.ndarray, dpi: int, gap_mm: float = 1.5) -> tuple[np.ndarray, int]:
    outer = fill_internal_holes(cut_mask)
    h_mm = max(1, math.ceil(outer.shape[0] * 25.4 / dpi))
    w_mm = max(1, math.ceil(outer.shape[1] * 25.4 / dpi))
    tiny = Image.fromarray((outer * 255).astype("uint8")).resize((w_mm, h_mm), Image.Resampling.NEAREST)
    radius = max(1, math.ceil(gap_mm))
    kernel = radius * 2 + 1
    tiny = Image.fromarray(np.pad(np.array(tiny), radius, mode="constant"))
    tiny = tiny.filter(ImageFilter.MaxFilter(kernel))
    return np.array(tiny) > 0, radius


def prepare_sticker(path: Path, asset_id: str, size_code: str, dpi: int = 300, bleed_mm: float = 0.75,
                    *, rectangular_cut: bool = False, material: MaterialProfile | None = None) -> PreparedSticker:
    source = Image.open(path).convert("RGBA")
    if rectangular_cut:
        cleaned = source
    else:
        cleaned = source
    scaled = scaled_to_frame(cleaned, SIZES_MM[size_code], dpi)
    raw_mask = np.array(scaled)[:, :, 3] > 24
    review_required = size_code == "A" and not rectangular_cut and needs_small_contour_review(raw_mask, dpi)
    cut_mask = (np.ones_like(raw_mask, dtype=bool) if rectangular_cut else
                cut_mask_for_size(raw_mask, size_code, dpi, safe_a=review_required,
                                  min_hole_mm_b=material.minimum_hole_mm_b if material else 2.2,
                                  min_hole_mm_c_plus=material.minimum_hole_mm_c_plus if material else 1.5))
    bleed_px = max(1, round(bleed_mm / 25.4 * dpi))
    pad_px = bleed_px + 2
    packing_mask, packing_pad_mm = _packing_mask(cut_mask, dpi)
    return PreparedSticker(asset_id, size_code, scaled, grow_bleed(scaled, bleed_px, pad_px), cut_mask,
                           packing_mask, pad_px, dpi, packing_pad_mm, review_required)


def _save_contour_preview(sticker: PreparedSticker, path: Path):
    scale = max(1, round(650 / max(sticker.image.size)))
    preview = Image.new("RGB", sticker.image.size, "white")
    preview.paste(sticker.image, (0, 0), sticker.image)
    preview = preview.resize((preview.width * scale, preview.height * scale), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(preview)
    for loop in trace_loops(sticker.cut_mask):
        if len(loop) > 2:
            draw.line([(x * scale, y * scale) for x, y in loop + [loop[0]]],
                      fill="#e40036", width=max(2, scale))
    preview.save(path)


class SheetPacker:
    """Масочный упаковщик: допускает пересечение рамок, если контуры не сталкиваются."""
    width_mm = 210
    height_mm = 297
    mark_inset_mm = 10
    bottom_mark_inset_mm = 25
    mark_length_mm = 20

    def _empty_sheet(self) -> np.ndarray:
        occupied = np.zeros((self.height_mm, self.width_mm), dtype=bool)
        occupied[:self.mark_inset_mm, :] = True
        occupied[-self.bottom_mark_inset_mm:, :] = True
        occupied[:, :self.mark_inset_mm] = True
        occupied[:, -self.mark_inset_mm:] = True
        corner = self.mark_inset_mm + self.mark_length_mm
        occupied[self.mark_inset_mm:corner, self.mark_inset_mm:corner] = True
        occupied[self.mark_inset_mm:corner, self.width_mm-corner:self.width_mm-self.mark_inset_mm] = True
        bottom = self.height_mm - self.bottom_mark_inset_mm
        occupied[bottom-self.mark_length_mm:bottom,
                 self.mark_inset_mm:corner] = True
        occupied[bottom-self.mark_length_mm:bottom,
                 self.width_mm-corner:self.width_mm-self.mark_inset_mm] = True
        return occupied

    @staticmethod
    def _place_on(occupied: np.ndarray, sticker: PreparedSticker):
        options = [(sticker, False), (sticker.rotated(), True)]
        best = None
        for candidate, rotated in options:
            mask = candidate.packing_mask_mm
            h, w = mask.shape
            if h >= occupied.shape[0] or w >= occupied.shape[1]:
                continue
            for y in range(0, occupied.shape[0] - h + 1):
                for x in range(0, occupied.shape[1] - w + 1):
                    region = occupied[y:y+h, x:x+w]
                    if not np.any(region & mask):
                        score = y * occupied.shape[1] + x
                        if best is None or score < best[0]:
                            best = (score, candidate, rotated, x, y)
                        break
                if best is not None and best[0] // occupied.shape[1] == y:
                    break
        if best is None:
            return None
        _, candidate, rotated, x, y = best
        mask = candidate.packing_mask_mm
        h, w = mask.shape
        occupied[y:y+h, x:x+w] |= mask
        return Placement(candidate, x, y, rotated)

    def pack(self, stickers: list[PreparedSticker]) -> list[list[Placement]]:
        # Большие и сложные формы первыми, маленькие заполняют оставшиеся карманы.
        pending = sorted(stickers, key=lambda item: int(item.packing_mask_mm.sum()), reverse=True)
        sheets: list[list[Placement]] = []
        occupancies: list[np.ndarray] = []
        for sticker in pending:
            placement = None
            for index, occupied in enumerate(occupancies):
                placement = self._place_on(occupied, sticker)
                if placement:
                    sheets[index].append(placement)
                    break
            if not placement:
                occupied = self._empty_sheet()
                placement = self._place_on(occupied, sticker)
                if not placement:
                    raise ValueError(f"{sticker.asset_id}/{sticker.size_code} не помещается в рабочую область A4")
                occupancies.append(occupied)
                sheets.append([placement])
        return sheets


def _font(size: int):
    for name in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _draw_marks(draw: ImageDraw.ImageDraw, dpi: int):
    px = lambda mm: round(mm / 25.4 * dpi)
    inset, length, width, height, bottom = px(10), px(20), px(210), px(297), px(25)
    stroke = max(2, px(0.45))
    corners = [
        ((inset, inset), (inset + length, inset), (inset, inset + length)),
        ((width-inset, inset), (width-inset-length, inset), (width-inset, inset+length)),
        ((inset, height-bottom), (inset+length, height-bottom), (inset, height-bottom-length)),
        ((width-inset, height-bottom), (width-inset-length, height-bottom), (width-inset, height-bottom-length)),
    ]
    for origin, horizontal, vertical in corners:
        draw.line([origin, horizontal], fill="black", width=stroke)
        draw.line([origin, vertical], fill="black", width=stroke)


def _translated_svg_paths(placement: Placement) -> list[tuple[float, str, float]]:
    loops = trace_loops(placement.sticker.cut_mask)
    paths = []
    mm_per_px = 25.4 / placement.sticker.dpi
    for loop in loops:
        closed = loop + [loop[0]]
        simplified = simplify(closed, 1.1)
        if len(simplified) < 4:
            continue
        origin_x = placement.x_mm + placement.sticker.packing_pad_mm
        origin_y = placement.y_mm + placement.sticker.packing_pad_mm
        coords = [(origin_x + x * mm_per_px, origin_y + y * mm_per_px) for x, y in simplified]
        area = abs(sum(coords[i][0] * coords[(i+1) % len(coords)][1] - coords[(i+1) % len(coords)][0] * coords[i][1]
                       for i in range(len(coords))) / 2)
        command = [f"M {coords[0][0]:.3f} {coords[0][1]:.3f}"]
        command.extend(f"L {x:.3f} {y:.3f}" for x, y in coords[1:])
        command.append("Z")
        length_mm = sum(math.dist(coords[i], coords[(i + 1) % len(coords)]) for i in range(len(coords)))
        paths.append((area, " ".join(command), length_mm))
    return paths


def render_order(order: Order, catalog: AssetCatalog, material: MaterialProfile, output_root: Path,
                 *, rectangular_assets: set[str] | None = None, size_rules: dict[str, dict] | None = None,
                 dpi: int = 300) -> dict:
    rectangular_assets = {value.upper() for value in (rectangular_assets or set())}
    checks: list[PreflightResult] = []
    stickers: list[PreparedSticker] = []
    size_rules = size_rules or {}
    for item in order.items:
        rule_warning = validate_size_rule(item.asset_id, item.size_code, size_rules)
        source = catalog.resolve(item.asset_id)
        rectangular = item.asset_id.upper() in rectangular_assets
        check = preflight(source, item.asset_id, item.size_code, dpi, allow_opaque=rectangular)
        if rule_warning:
            check.warnings.append(rule_warning)
        checks.append(check)
        if check.errors:
            continue
        prepared = prepare_sticker(source, item.asset_id, item.size_code, dpi, rectangular_cut=rectangular, material=material)
        if prepared.contour_review_required:
            check.warnings.append("Сложный контур A упрощён; проверьте красную обводку до печати.")
        stickers.extend([prepared] * item.quantity)
    if any(result.errors for result in checks):
        raise PreflightError(checks)

    sheets = SheetPacker().pack(stickers)
    if len(sheets) > 10:
        raise ValueError(f"Заказ занял {len(sheets)} листов. Производственный предел одного заказа — 10 листов.")
    out = Path(output_root) / order.order_id
    out.mkdir(parents=True, exist_ok=True)
    contour_previews = []
    seen_previews = set()
    for sticker in stickers:
        key = (sticker.asset_id, sticker.size_code)
        if sticker.contour_review_required and key not in seen_previews:
            seen_previews.add(key)
            preview_path = out / f"review-{sticker.asset_id}-{sticker.size_code}.png"
            _save_contour_preview(sticker, preview_path)
            contour_previews.append(str(preview_path))
    px = lambda mm: round(mm / 25.4 * dpi)
    page_files, cut_files, cut_dxf_files, cut_bounds, cut_length_mm_per_sheet, sheet_previews = [], [], [], [], [], []
    for sheet_no, placements in enumerate(sheets, 1):
        page = Image.new("RGB", (px(210), px(297)), "white")
        draw = ImageDraw.Draw(page)
        _draw_marks(draw, dpi)
        # Print-only dimensional check used by the verified direct-cut pilot.
        draw.line([(px(80), px(279)), (px(130), px(279))], fill="black", width=3)
        all_paths: list[tuple[float, str, float]] = []
        for placement in placements:
            sticker = placement.sticker
            x = px(placement.x_mm + sticker.packing_pad_mm) - sticker.pad_px
            y = px(placement.y_mm + sticker.packing_pad_mm) - sticker.pad_px
            page.paste(sticker.print_image.convert("RGB"), (x, y), sticker.print_image)
            all_paths.extend(_translated_svg_paths(placement))
        label = f"{order.order_id} · лист {sheet_no}/{len(sheets)} · {material.name}"
        draw.text((px(12), px(289)), label, fill="black", font=_font(max(12, px(2.5))))
        page_path = out / f"sheet-{sheet_no:02d}-print.png"
        page.save(page_path, dpi=(dpi, dpi), compress_level=3)
        page_files.append(str(page_path))

        # Малые внутренние пути идут первыми, самый большой внешний контур — последним.
        all_paths.sort(key=lambda item: item[0])
        review = page.copy()
        review_draw = ImageDraw.Draw(review)
        for _, path, _ in all_paths:
            points = [(px(x), px(y)) for x, y in path_points(path)]
            if len(points) > 2:
                review_draw.line(points + [points[0]], fill=(230, 0, 54), width=max(2, px(0.25)))
        preview_path = out / f"sheet-{sheet_no:02d}-review.png"
        review.save(preview_path)
        sheet_previews.append(str(preview_path))
        cut_length_mm_per_sheet.append(round(sum(path[2] for path in all_paths) * material.passes, 3))
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">\n'
               + "\n".join(f'  <path d="{path}" fill="none" stroke="#ff0000" stroke-width="0.15"/>' for _, path, _ in all_paths)
               + "\n</svg>\n")
        cut_path = out / f"sheet-{sheet_no:02d}-cut.svg"
        cut_path.write_text(svg, encoding="utf-8")
        cut_files.append(str(cut_path))
        dxf_path = out / f"sheet-{sheet_no:02d}-cut-basic-UNVERIFIED.dxf"
        dxf_path.write_text(render_dxf(all_paths), encoding="ascii")
        cut_dxf_files.append(str(dxf_path))
        cut_bounds.append(bounds(all_paths))

    # Многостраничный PDF сохраняет физический A4; нужен режим печати 100%.
    rgb_pages = [Image.open(path).convert("RGB") for path in page_files]
    pdf_path = out / f"{order.order_id}-print.pdf"
    if rgb_pages:
        rgb_pages[0].save(pdf_path, "PDF", resolution=dpi, save_all=True, append_images=rgb_pages[1:])
    occupied_area = sum(int(placement.sticker.packing_mask_mm.sum()) for sheet in sheets for placement in sheet)
    approximate_safe_area = len(sheets) * 174 * 257
    report = {
        "schema_version": 1, "order_id": order.order_id, "material_id": order.material_id,
        "sheet_count": len(sheets), "print_pdf": str(pdf_path), "print_pages": page_files,
        "sheet_previews": sheet_previews,
        "cut_files": cut_files,
        "cut_dxf_files": cut_dxf_files, "cut_bounds_mm": cut_bounds,
        "studio_basic_import_status": "unverified_scale_and_registration",
        "contour_previews": contour_previews,
        "contour_review_approved": False,
        "cut_length_mm_per_sheet": cut_length_mm_per_sheet,
        "planned_cut_length_mm": round(sum(cut_length_mm_per_sheet), 3),
        "preflight": [result.__dict__ for result in checks],
        "cut_settings": {"blade": material.blade, "force": material.force, "speed": material.speed, "passes": material.passes},
        "print_side_instruction": material.print_side_instruction,
        "estimated_sheet_utilization_percent": round(occupied_area / approximate_safe_area * 100, 1) if approximate_safe_area else 0,
        "registration_profile": {"left_mm": 10, "right_mm": 10, "top_mm": 10,
                                 "bottom_mm": 25, "length_mm": 20, "status": "physically_tested"},
        "status": "needs_contour_review",
    }
    (out / "job.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

