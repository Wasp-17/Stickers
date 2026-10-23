from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MaterialProfile:
    material_id: str
    name: str
    print_side_instruction: str
    printer_media_type: str
    quality: str
    blade: int
    force: int
    speed: int
    passes: int
    minimum_hole_mm_b: float
    minimum_hole_mm_c_plus: float
    calibrated: bool


def load_materials(path: Path) -> dict[str, MaterialProfile]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {item["material_id"]: MaterialProfile(**item) for item in payload["materials"]}

