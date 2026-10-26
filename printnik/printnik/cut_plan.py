"""Offline, deliberately non-transmittable draft of Cameo cut moves.

The page-to-plotter origin, registration scan and command envelope still need
physical verification. Nothing in this module opens a device or sends bytes.
"""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path


PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0
UNITS_PER_MM = 20  # Candidate scale from the open Silhouette protocol notes.
_PATH = re.compile(r"\s*([ML])\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*|\s*(Z)\s*", re.I)


class CutPlanError(ValueError):
    pass


def _points(path_data: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    position = 0
    closed = False
    while position < len(path_data):
        match = _PATH.match(path_data, position)
        if not match:
            raise CutPlanError("Контур содержит неподдерживаемые команды SVG.")
        if closed:
            raise CutPlanError("После замыкания контура обнаружены дополнительные команды.")
        position = match.end()
        if match.group(4):
            closed = True
            break
        command = match.group(1).upper()
        if command != ("M" if not points else "L"):
            raise CutPlanError("Ожидался один замкнутый контур из M/L/Z.")
        point = (float(match.group(2)), float(match.group(3)))
        if not all(math.isfinite(value) for value in point):
            raise CutPlanError("Координата контура не является конечным числом.")
        if not (0 <= point[0] <= PAGE_WIDTH_MM and 0 <= point[1] <= PAGE_HEIGHT_MM):
            raise CutPlanError("Контур выходит за пределы листа A4.")
        points.append(point)
    if not closed or path_data[position:].strip():
        raise CutPlanError("Контур должен завершаться командой Z.")
    if points and points[-1] == points[0]:
        points.pop()
    if len(set(points)) < 3:
        raise CutPlanError("Контур содержит менее трёх разных точек.")
    return points


def plan_svg(svg_file: Path) -> dict:
    """Parse Printnik's A4 SVG into a reviewable sequence; never send it."""
    try:
        root = ET.parse(svg_file).getroot()
    except (ET.ParseError, OSError) as exc:
        raise CutPlanError(f"Не удалось прочитать SVG: {exc}") from exc
    if (root.tag != "{http://www.w3.org/2000/svg}svg"
            or root.attrib.get("width") != "210mm"
            or root.attrib.get("height") != "297mm"
            or root.attrib.get("viewBox") != "0 0 210 297"):
        raise CutPlanError("Ожидался лист A4 из Печатника с координатами в миллиметрах.")
    contours = []
    all_points = []
    for element in root:
        if element.tag != "{http://www.w3.org/2000/svg}path":
            raise CutPlanError("В SVG обнаружен неподдерживаемый элемент.")
        points = _points(element.attrib.get("d", ""))
        all_points.extend(points)
        scaled = [(round(x * UNITS_PER_MM), round(y * UNITS_PER_MM)) for x, y in points]
        if len(set(scaled)) < 3:
            raise CutPlanError("После перевода в шаги плоттера контур выродился.")
        instructions = [f"M {scaled[0][0]},{scaled[0][1]}"]
        instructions.extend(f"D {x},{y}" for x, y in scaled[1:])
        instructions.append(f"D {scaled[0][0]},{scaled[0][1]}")
        contours.append({"points_mm": [[x, y] for x, y in points],
                         "draft_moves": instructions})
    if not contours:
        raise CutPlanError("В SVG нет контуров реза.")
    xs, ys = zip(*all_points)
    return {
        "status": "UNVERIFIED_OFFLINE_ONLY",
        "warning": "Черновик. Не отправлять плоттеру: начало координат и регистрация меток ещё не проверены.",
        "source_svg": svg_file.name,
        "page_mm": [PAGE_WIDTH_MM, PAGE_HEIGHT_MM],
        "candidate_units_per_mm": UNITS_PER_MM,
        "registration_transform": "NOT_CALIBRATED",
        "bounds_mm": {"left": min(xs), "top": min(ys), "right": max(xs), "bottom": max(ys)},
        "contours": contours,
    }


def write_order_cut_plans(output_dir: Path) -> list[Path]:
    """Write JSON plans for reviewed sheets without connecting to the Cameo."""
    output_dir = Path(output_dir).resolve()
    report_path = output_dir / "job.json"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CutPlanError(f"Не удалось прочитать пакет заказа: {exc}") from exc
    if not report.get("contour_review_approved"):
        raise CutPlanError("Сначала просмотрите и утвердите контуры листов.")
    cut_files = report.get("cut_files")
    if not isinstance(cut_files, list) or not cut_files:
        raise CutPlanError("В пакете заказа нет контуров SVG.")
    plans = []
    for sheet_no, raw_path in enumerate(cut_files, 1):
        svg_file = Path(raw_path).resolve()
        if svg_file.parent != output_dir or svg_file.name != f"sheet-{sheet_no:02d}-cut.svg":
            raise CutPlanError("Файл контура не совпадает с выбранным пакетом заказа.")
        plans.append((output_dir / f"sheet-{sheet_no:02d}-direct-cut-plan-UNVERIFIED.json",
                      plan_svg(svg_file)))
    for destination, plan in plans:
        destination.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return [destination for destination, _ in plans]
