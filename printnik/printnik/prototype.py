from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZES_MM = {"A": 30, "A1": 35, "B": 50, "C": 75, "D": 100, "E": 125}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exterior_white_mask(rgba: np.ndarray) -> np.ndarray:
    rgb = rgba[:, :, :3].astype(np.int16)
    alpha = rgba[:, :, 3]
    # Светлые нейтральные пиксели; насыщенные цветные детали не затрагиваются.
    candidate = (
        (alpha > 0)
        & (rgb.min(axis=2) >= 218)
        & ((rgb.max(axis=2) - rgb.min(axis=2)) <= 28)
    )
    transparent = alpha <= 12
    h, w = alpha.shape
    seeds = np.zeros((h, w), dtype=bool)
    seeds[0, :] = candidate[0, :]
    seeds[-1, :] = candidate[-1, :]
    seeds[:, 0] |= candidate[:, 0]
    seeds[:, -1] |= candidate[:, -1]
    # Белая кайма часто отделена от края холста прозрачностью, поэтому стартуем
    # со всех светлых пикселей, непосредственно касающихся прозрачного фона.
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        shifted = np.roll(transparent, (dy, dx), axis=(0, 1))
        seeds |= candidate & shifted

    result = np.zeros((h, w), dtype=bool)
    q = deque(map(tuple, np.argwhere(seeds)))
    while q:
        y, x = q.popleft()
        if result[y, x] or not candidate[y, x]:
            continue
        result[y, x] = True
        if y: q.append((y - 1, x))
        if y + 1 < h: q.append((y + 1, x))
        if x: q.append((y, x - 1))
        if x + 1 < w: q.append((y, x + 1))
    return result


def remove_exterior_white(image: Image.Image) -> tuple[Image.Image, np.ndarray]:
    rgba = np.array(image.convert("RGBA"))
    removed = exterior_white_mask(rgba)
    rgba[removed, 3] = 0
    return Image.fromarray(rgba, "RGBA"), removed


def scaled_to_frame(image: Image.Image, frame_mm: float, dpi: int) -> Image.Image:
    bbox = image.getbbox()
    if not bbox:
        raise ValueError("После очистки изображение оказалось пустым")
    cropped = image.crop(bbox)
    max_px = round(frame_mm / 25.4 * dpi)
    ratio = min(max_px / cropped.width, max_px / cropped.height)
    size = (max(1, round(cropped.width * ratio)), max(1, round(cropped.height * ratio)))
    return cropped.resize(size, Image.Resampling.LANCZOS)


def grow_bleed(image: Image.Image, bleed_px: int, canvas_pad: int | None = None) -> Image.Image:
    data = np.array(image.convert("RGBA"))
    alpha = data[:, :, 3]
    pad = bleed_px + 2 if canvas_pad is None else canvas_pad
    data = np.pad(data, ((pad, pad), (pad, pad), (0, 0)), mode="constant")
    known = data[:, :, 3] > 16
    for _ in range(bleed_px):
        empty = ~known
        color_sum = np.zeros_like(data[:, :, :3], dtype=np.uint32)
        count = np.zeros(known.shape, dtype=np.uint16)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            src_known = np.roll(known, (dy, dx), axis=(0, 1))
            take = empty & src_known
            color_sum[take] += np.roll(data[:, :, :3], (dy, dx), axis=(0, 1))[take]
            count[take] += 1
        fill = empty & (count > 0)
        data[fill, :3] = (color_sum[fill] / count[fill, None]).astype(np.uint8)
        data[fill, 3] = 255
        known |= fill
    return Image.fromarray(data, "RGBA")


def largest_component(mask: np.ndarray) -> np.ndarray:
    """Оставляет одну основную физическую наклейку, не создавая резы по соринкам."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    largest: list[tuple[int, int]] = []
    for sy, sx in zip(*np.nonzero(mask)):
        if seen[sy, sx]:
            continue
        component: list[tuple[int, int]] = []
        q = deque([(int(sy), int(sx))])
        seen[sy, sx] = True
        while q:
            y, x = q.popleft()
            component.append((y, x))
            for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        if len(component) > len(largest):
            largest = component
    result = np.zeros_like(mask, dtype=bool)
    if largest:
        ys, xs = zip(*largest)
        result[np.array(ys), np.array(xs)] = True
    return result


def fill_internal_holes(mask: np.ndarray) -> np.ndarray:
    """Стандартный профиль режет только наружную границу, без внутренних отверстий."""
    h, w = mask.shape
    outside = np.zeros_like(mask, dtype=bool)
    q = deque()
    for x in range(w):
        if not mask[0, x]: q.append((0, x))
        if not mask[h-1, x]: q.append((h-1, x))
    for y in range(h):
        if not mask[y, 0]: q.append((y, 0))
        if not mask[y, w-1]: q.append((y, w-1))
    while q:
        y, x = q.popleft()
        if outside[y, x] or mask[y, x]:
            continue
        outside[y, x] = True
        if y: q.append((y-1, x))
        if y+1 < h: q.append((y+1, x))
        if x: q.append((y, x-1))
        if x+1 < w: q.append((y, x+1))
    return ~outside


def _components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    """Возвращает связные области маски без внешних библиотек анализа изображений."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    result: list[list[tuple[int, int]]] = []
    for sy, sx in zip(*np.nonzero(mask)):
        if seen[sy, sx]:
            continue
        component: list[tuple[int, int]] = []
        q = deque([(int(sy), int(sx))])
        seen[sy, sx] = True
        while q:
            y, x = q.popleft()
            component.append((y, x))
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        result.append(component)
    return result


def _convex_hull(mask: np.ndarray) -> np.ndarray:
    """Bounding hull for measuring how concave a small silhouette is."""
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return mask.copy()
    points = sorted(set(zip(xs.tolist(), ys.tolist())))
    if len(points) < 3:
        return mask.copy()

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    lower = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    image = Image.new("1", (mask.shape[1], mask.shape[0]))
    ImageDraw.Draw(image).polygon(hull, fill=1)
    return np.array(image, dtype=bool)


def safe_outline(mask: np.ndarray, dpi: int) -> np.ndarray:
    """Suppress fragile A protrusions and narrow recesses before adding a small rim."""
    if not mask.any():
        return mask.copy()
    radius_px = max(1, round(0.8 / 25.4 * dpi))
    image = Image.fromarray((mask * 255).astype("uint8"))
    kernel = radius_px * 2 + 1
    opened = image.filter(ImageFilter.MinFilter(kernel)).filter(ImageFilter.MaxFilter(kernel))
    closing_px = max(radius_px, round(1.2 / 25.4 * dpi))
    closing_kernel = closing_px * 2 + 1
    closed = opened.filter(ImageFilter.MaxFilter(closing_kernel)).filter(ImageFilter.MinFilter(closing_kernel))
    rim_px = max(1, round(0.25 / 25.4 * dpi))
    expanded = closed.filter(ImageFilter.MaxFilter(rim_px * 2 + 1))
    softened = expanded.filter(ImageFilter.GaussianBlur(max(1, rim_px / 2)))
    return np.array(softened) >= 110


def needs_small_contour_review(raw_mask: np.ndarray, dpi: int) -> bool:
    """Flag fine A silhouettes for a visible, simplified-cut review."""
    components = _components(raw_mask)
    if len(components) > 1:
        meaningful = sorted((len(component) for component in components), reverse=True)
        if meaningful[1] >= max(3, round((0.5 / 25.4 * dpi) ** 2 * math.pi)):
            return True
    filled = fill_internal_holes(largest_component(raw_mask))
    if not filled.any():
        return False
    radius_px = max(1, round(0.8 / 25.4 * dpi))
    kernel = radius_px * 2 + 1
    image = Image.fromarray((filled * 255).astype("uint8"))
    opened = np.array(image.filter(ImageFilter.MinFilter(kernel)).filter(ImageFilter.MaxFilter(kernel))) > 0
    lost_fraction = np.count_nonzero(filled & ~opened) / np.count_nonzero(filled)
    hull = _convex_hull(filled)
    perimeter = len(boundary_edges(filled))
    hull_perimeter = max(1, len(boundary_edges(hull)))
    return lost_fraction >= 0.004 or perimeter / hull_perimeter >= 1.45


def cut_mask_for_size(raw_mask: np.ndarray, size_code: str, dpi: int, *, min_hole_mm_a: float = 2.8,
                      safe_a: bool = False, min_hole_mm_b: float = 2.2,
                      min_hole_mm_c_plus: float = 1.5) -> np.ndarray:
    """Создаёт физическую маску реза с размерным правилом внутренних полостей.

    Заметные полости сохраняются и в A. Для сложного A оператору предлагается
    обводной внешний контур; мелкие отверстия всегда заполняются.
    """
    components = sorted(_components(raw_mask), key=len, reverse=True)
    body = np.zeros_like(raw_mask, dtype=bool)
    detached_min_mm = 3.0 if size_code in {"A", "A1"} else 1.5
    detached_min_area = math.pi * ((detached_min_mm / 2) / 25.4 * dpi) ** 2
    for index, component in enumerate(components):
        ys, xs = zip(*component)
        diameter_px = min(max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        if index == 0 or (not safe_a and len(component) >= detached_min_area
                          and diameter_px * 25.4 / dpi >= detached_min_mm):
            body[np.array(ys), np.array(xs)] = True
    filled = fill_internal_holes(body)
    holes = filled & ~body
    min_diameter_mm = (min_hole_mm_a if size_code in {"A", "A1"} else
                       min_hole_mm_b if size_code == "B" else min_hole_mm_c_plus)
    min_area_px = math.pi * ((min_diameter_mm / 2) / 25.4 * dpi) ** 2
    result = safe_outline(filled, dpi) if size_code == "A" and safe_a else filled.copy()
    for component in _components(holes):
        ys, xs = zip(*component)
        diameter_px = min(max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        if len(component) >= min_area_px and diameter_px * 25.4 / dpi >= min_diameter_mm:
            result[np.array(ys), np.array(xs)] = False
    return result


def boundary_edges(mask: np.ndarray):
    h, w = mask.shape
    edges = []
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys.tolist(), xs.tolist()):
        if y == 0 or not mask[y - 1, x]: edges.append(((x, y), (x + 1, y)))
        if x == w - 1 or not mask[y, x + 1]: edges.append(((x + 1, y), (x + 1, y + 1)))
        if y == h - 1 or not mask[y + 1, x]: edges.append(((x + 1, y + 1), (x, y + 1)))
        if x == 0 or not mask[y, x - 1]: edges.append(((x, y + 1), (x, y)))
    return edges


def trace_loops(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    outgoing: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for a, b in boundary_edges(mask):
        outgoing.setdefault(a, []).append(b)
    loops = []
    while outgoing:
        start = next(iter(outgoing))
        loop = [start]
        current = start
        while True:
            choices = outgoing.get(current)
            if not choices:
                break
            nxt = choices.pop()
            if not choices:
                del outgoing[current]
            current = nxt
            if current == start:
                break
            loop.append(current)
        if len(loop) > 8 and current == start:
            loops.append(loop)
    return loops


def point_line_distance(p, a, b):
    if a == b:
        return math.dist(p, a)
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def simplify(points, epsilon):
    if len(points) < 3:
        return points
    a, b = points[0], points[-1]
    distances = [point_line_distance(p, a, b) for p in points[1:-1]]
    if not distances or max(distances) <= epsilon:
        return [a, b]
    idx = distances.index(max(distances)) + 1
    return simplify(points[: idx + 1], epsilon)[:-1] + simplify(points[idx:], epsilon)


def save_svg(mask: np.ndarray, path: Path, dpi: int, epsilon: float = 1.1) -> list[list[tuple[int, int]]]:
    loops = trace_loops(mask)
    simplified = []
    for loop in loops:
        closed = loop + [loop[0]]
        candidate = simplify(closed, epsilon)
        if len(candidate) >= 4:
            simplified.append(candidate)
    h, w = mask.shape
    mm_per_px = 25.4 / dpi
    paths = []
    for loop in simplified:
        commands = [f"M {loop[0][0] * mm_per_px:.3f} {loop[0][1] * mm_per_px:.3f}"]
        commands.extend(f"L {x * mm_per_px:.3f} {y * mm_per_px:.3f}" for x, y in loop[1:])
        commands.append("Z")
        paths.append(" ".join(commands))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w*mm_per_px:.3f}mm" '
        f'height="{h*mm_per_px:.3f}mm" viewBox="0 0 {w*mm_per_px:.3f} {h*mm_per_px:.3f}">\n'
        + "\n".join(f'  <path d="{d}" fill="none" stroke="#ff0066" stroke-width="0.15"/>' for d in paths)
        + "\n</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")
    return simplified


def checker(size):
    w, h = size
    tile = 18
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            c = 238 if ((x // tile + y // tile) % 2 == 0) else 210
            arr[y, x] = (c, c, c, 255)
    return Image.fromarray(arr, "RGBA")


def composite_checker(image, size):
    bg = checker(size)
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    pos = ((size[0] - copy.width)//2, (size[1]-copy.height)//2)
    bg.alpha_composite(copy, pos)
    return bg


def comparison(source, cleaned, loops, out_path):
    panel = (520, 560)
    canvas = Image.new("RGB", (panel[0]*3, panel[1]+70), "white")
    titles = ["ИСХОДНИК", "БЕЗ ВНЕШНЕЙ БЕЛОЙ ПОДЛОЖКИ", "ЛИНИЯ РЕЗА ПО ЦВЕТНОЙ ГРАНИЦЕ"]
    images = [source, cleaned, cleaned]
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default(size=22)
    draw = ImageDraw.Draw(canvas)
    for i, (title, image) in enumerate(zip(titles, images)):
        rendered = composite_checker(image, panel)
        if i == 2:
            overlay = ImageDraw.Draw(rendered)
            scale = min(panel[0]/image.width, panel[1]/image.height)
            ox = (panel[0]-image.width*scale)/2
            oy = (panel[1]-image.height*scale)/2
            for loop in loops:
                pts = [(ox+x*scale, oy+y*scale) for x,y in loop]
                if len(pts) > 2: overlay.line(pts, fill=(255, 0, 90, 255), width=3, joint="curve")
        canvas.paste(rendered.convert("RGB"), (i*panel[0], 70))
        box = draw.textbbox((0,0), title, font=font)
        draw.text((i*panel[0]+(panel[0]-(box[2]-box[0]))/2, 22), title, fill="#222", font=font)
    canvas.save(out_path, quality=95)


def prepare(input_path: Path, output: Path, asset_id: str, size_code: str, dpi: int, bleed_mm: float):
    output.mkdir(parents=True, exist_ok=True)
    source = Image.open(input_path).convert("RGBA")
    cleaned_original, removed = remove_exterior_white(source)
    if size_code == "F":
        raise ValueError("Размер F будет рассчитан после калибровки рабочей области A4")
    scaled = scaled_to_frame(cleaned_original, SIZES_MM[size_code], dpi)
    scaled.save(output / "cleaned.png")
    raw_mask = np.array(scaled)[:, :, 3] > 24
    mask = cut_mask_for_size(raw_mask, size_code, dpi)
    bleed_px = max(1, round(bleed_mm / 25.4 * dpi))
    canvas_pad = bleed_px + 2
    padded_mask = np.pad(mask, canvas_pad, mode="constant")
    loops = save_svg(padded_mask, output / "cut.svg", dpi)
    bleed = grow_bleed(scaled, bleed_px, canvas_pad)
    bleed.save(output / "print_with_bleed.png")
    preview_loops = [[(x-canvas_pad, y-canvas_pad) for x, y in loop] for loop in loops]
    comparison(source, scaled, preview_loops, output / "comparison.png")
    manifest = {
        "schema_version": 1,
        "asset_id": asset_id,
        "source": str(input_path.resolve()),
        "source_sha256": sha256(input_path),
        "size": size_code,
        "frame_mm": SIZES_MM[size_code],
        "dpi": dpi,
        "bleed_mm": bleed_mm,
        "canvas_px": {"width": bleed.width, "height": bleed.height},
        "cut_origin_offset_px": canvas_pad,
        "removed_exterior_pixels": int(removed.sum()),
        "cut_paths": len(loops),
        "status": "candidate_requires_approval"
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(prog="printnik")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="создать опытный производственный пакет")
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--asset-id", required=True)
    p.add_argument("--size", choices=list(SIZES_MM) + ["F"], default="B")
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--bleed-mm", type=float, default=0.75)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.input, args.output, args.asset_id, args.size, args.dpi, args.bleed_mm)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

