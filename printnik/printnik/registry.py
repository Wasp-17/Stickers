from __future__ import annotations

import json
from pathlib import Path


class DeviceRegistry:
    def __init__(self, path: Path, seed_path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(Path(seed_path).read_text(encoding="utf-8"), encoding="utf-8")

    def all(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))["devices"]

    def save(self, devices: list[dict]):
        self.path.write_text(json.dumps({"schema_version": 1, "devices": devices}, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, *, device_id: str, kind: str, display_name: str, model: str, connection: str):
        devices = self.all()
        if any(item["device_id"] == device_id for item in devices):
            raise ValueError("Такой ID оборудования уже существует")
        devices.append({
            "device_id": device_id, "kind": kind, "display_name": display_name,
            "model": model, "connection": connection,
            "roles": ["stickers"] if kind == "printer" else ["contour_cut"],
            "approved_materials": [], "approved_profiles": [],
            "status": "requires_calibration", "loaded_media": None,
        })
        self.save(devices)

    def calibrate(self, device_id: str, materials: list[str], profiles: list[str]):
        devices = self.all()
        matched = False
        for device in devices:
            if device["device_id"] == device_id:
                device["approved_materials"] = sorted(set(materials))
                device["approved_profiles"] = sorted(set(profiles))
                device["status"] = "ready"
                matched = True
        if not matched:
            raise KeyError(device_id)
        self.save(devices)

