from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def load_devices(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["devices"]


def open_folder(path: Path):
    os.startfile(str(Path(path)))


def send_pdf_to_printer(path: Path, printer_name: str | None = None):
    """Передаёт PDF обработчику печати Windows; повторный вызов всегда явный."""
    if printer_name:
        try:
            os.startfile(str(Path(path)), "printto", arguments=f'"{printer_name}"', show_cmd=0)
            return
        except OSError:
            pass
    os.startfile(str(Path(path)), "print")


def find_silhouette_studio() -> Path | None:
    candidates = [
        Path(r"C:\Program Files\Silhouette America\Silhouette Studio\Silhouette Studio.exe"),
        Path(r"C:\Program Files (x86)\Silhouette America\Silhouette Studio\Silhouette Studio.exe"),
    ]
    return next((path for path in candidates if path.exists()), None)


def open_silhouette_bridge(job_dir: Path):
    studio = find_silhouette_studio()
    if not studio:
        raise FileNotFoundError("Silhouette Studio не найден")
    subprocess.Popen([str(studio)])
    subprocess.Popen(["explorer.exe", str(Path(job_dir))])

