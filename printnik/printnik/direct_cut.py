"""Offline compilation of reviewed A4 sheets for the physically tested Cameo path.

This module never opens the USB device. The existing Studio route remains the
only order-cut action until a separate physical test approves this integration.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .cut_plan import CutPlanError, plan_svg


VERIFIED_SETTINGS = {"blade": 1, "force": 4, "speed": 4, "passes": 1}
VERIFIED_REGISTRATION = {
    "left_mm": 10, "right_mm": 10, "top_mm": 10,
    "bottom_mm": 25, "length_mm": 20, "status": "physically_tested",
}
MAX_CONTOURS = 8
MAX_POINTS_PER_CONTOUR = 500
MAX_COMMANDS = 3000


@dataclass(frozen=True)
class DirectSheetPreview:
    order_id: str
    sheet_no: int
    contour_count: int
    command_count: int
    print_sha256: str
    cut_sha256: str
    commands: tuple[bytes, ...]


def compile_svg_commands(svg_file: Path) -> tuple[bytes, ...]:
    """Use the exact coordinate transform and command order of the eight-cut pilot."""
    plan = plan_svg(svg_file)
    contours = plan["contours"]
    if not 1 <= len(contours) <= MAX_CONTOURS:
        raise CutPlanError(f"Для первого прямого задания допустимо 1–{MAX_CONTOURS} контуров.")
    commands: list[bytes] = []
    for contour in contours:
        points = contour["points_mm"]
        if not 3 <= len(points) <= MAX_POINTS_PER_CONTOUR:
            raise CutPlanError("Контур слишком подробный для проверенного USB-маршрута.")
        if any(not (11 <= x <= 199 and 11 <= y <= 245) for x, y in points):
            raise CutPlanError("Контур вышел за проверенную область листа с метками.")
        coords = [(round((y - 10) * 20), round((x - 10) * 20)) for x, y in points]
        if len(set(coords)) < 3:
            raise CutPlanError("Контур выродился после перевода в шаги плоттера.")
        first = f"M{coords[0][0]},{coords[0][1]}\x03".encode("ascii")
        commands.append(first)
        commands.extend(f"D{y},{x}\x03".encode("ascii") for y, x in coords[1:])
        commands.append(f"D{coords[0][0]},{coords[0][1]}\x03".encode("ascii"))
        commands.append(first)
    if len(commands) > MAX_COMMANDS:
        raise CutPlanError("В задании больше команд, чем в проверенном пробном листе.")
    return tuple(commands)


def approved_file_hashes(output_dir: Path, report: dict) -> dict:
    """Fingerprint the PDF, all cut lines and the previews the operator saw."""
    output_dir = Path(output_dir).resolve()
    order_id = report.get("order_id")
    count = report.get("sheet_count")
    cuts = report.get("cut_files")
    previews = report.get("sheet_previews")
    if (not isinstance(order_id, str) or not order_id or type(count) is not int or
            not 1 <= count <= 10 or not isinstance(cuts, list) or len(cuts) != count or
            not isinstance(previews, list) or len(previews) != count):
        raise CutPlanError("В пакете заказа неполный список печати и контуров.")
    pdf = Path(report.get("print_pdf", "")).resolve()
    if pdf.parent != output_dir or pdf.name != f"{order_id}-print.pdf":
        raise CutPlanError("Печатный PDF не принадлежит выбранному заказу.")
    files = [pdf]
    for sheet_no, (raw_cut, raw_preview) in enumerate(zip(cuts, previews), 1):
        cut = Path(raw_cut).resolve()
        preview = Path(raw_preview).resolve()
        if (cut.parent != output_dir or cut.name != f"sheet-{sheet_no:02d}-cut.svg" or
                preview.parent != output_dir or preview.name != f"sheet-{sheet_no:02d}-review.png"):
            raise CutPlanError("Контур или предпросмотр не принадлежит выбранному заказу.")
        files.extend((cut, preview))
    try:
        digests = [hashlib.sha256(path.read_bytes()).hexdigest() for path in files]
    except OSError as exc:
        raise CutPlanError("Не найден печатный PDF, контур или предпросмотр листа.") from exc
    return {"print_pdf": digests[0],
            "cut_files": digests[1::2], "sheet_previews": digests[2::2]}


def prepare_direct_sheet(output_dir: Path, sheet_no: int) -> DirectSheetPreview:
    """Validate one approved production sheet without sending or saving commands."""
    output_dir = Path(output_dir).resolve()
    try:
        report = json.loads((output_dir / "job.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CutPlanError(f"Не удалось прочитать пакет заказа: {exc}") from exc
    if not report.get("contour_review_approved"):
        raise CutPlanError("Сначала просмотрите и утвердите контуры всех листов.")
    if report.get("material_id") != "matte_white":
        raise CutPlanError("Прямой USB-рез пока проверен только для белой матовой самоклейки.")
    if report.get("cut_settings") != VERIFIED_SETTINGS:
        raise CutPlanError("Для пробного USB-реза нужны настройки AutoBlade 1, сила 4, скорость 4, один проход.")
    if report.get("registration_profile") != VERIFIED_REGISTRATION:
        raise CutPlanError("Регистрационные метки листа не совпадают с проверенным профилем.")
    if report.get("approved_files_sha256") != approved_file_hashes(output_dir, report):
        raise CutPlanError("Печатный лист или контур изменился после утверждения. Подготовьте заказ заново.")
    cut_files = report.get("cut_files")
    count = report.get("sheet_count")
    if (type(sheet_no) is not int or type(count) is not int or
            not isinstance(cut_files, list) or len(cut_files) != count or
            not 1 <= sheet_no <= count <= 10):
        raise CutPlanError("Номер листа или список контуров заказа неверен.")
    svg_file = Path(cut_files[sheet_no - 1]).resolve()
    pdf_file = Path(report.get("print_pdf", "")).resolve()
    if (svg_file.parent != output_dir or svg_file.name != f"sheet-{sheet_no:02d}-cut.svg" or
            pdf_file.parent != output_dir or pdf_file.name != f"{report.get('order_id')}-print.pdf"):
        raise CutPlanError("Печатный лист или контур не принадлежит выбранному заказу.")
    commands = compile_svg_commands(svg_file)
    approved = report["approved_files_sha256"]
    return DirectSheetPreview(
        order_id=report["order_id"], sheet_no=sheet_no,
        contour_count=sum(command.startswith(b"M") for command in commands) // 2,
        command_count=len(commands), print_sha256=approved["print_pdf"],
        cut_sha256=approved["cut_files"][sheet_no - 1], commands=commands,
    )
