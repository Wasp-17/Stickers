"""Логика закрепления заказа за оборудованием и контролируемого переноса."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DeviceKind(StrEnum):
    PRINTER = "printer"
    CUTTER = "cutter"


class DeviceStatus(StrEnum):
    READY = "ready"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    REQUIRES_CALIBRATION = "requires_calibration"


@dataclass(frozen=True)
class Device:
    device_id: str
    kind: DeviceKind
    status: DeviceStatus = DeviceStatus.REQUIRES_CALIBRATION
    roles: frozenset[str] = frozenset()
    approved_materials: frozenset[str] = frozenset()
    approved_profiles: frozenset[str] = frozenset()

    def can_run(self, *, kind: DeviceKind, role: str, material: str, profile: str | None = None) -> bool:
        return (
            self.kind == kind
            and self.status in {DeviceStatus.READY, DeviceStatus.BUSY}
            and role in self.roles
            and material in self.approved_materials
            and (profile is None or profile in self.approved_profiles)
        )


@dataclass(frozen=True)
class ProductionSegment:
    device_id: str
    first_sheet: int
    last_sheet: int
    reason: str = "initial_assignment"


@dataclass
class DeviceAssignment:
    order_id: str
    total_sheets: int
    printer_segments: list[ProductionSegment] = field(default_factory=list)
    cutter_segments: list[ProductionSegment] = field(default_factory=list)

    @property
    def printer_id(self) -> str | None:
        return self.printer_segments[-1].device_id if self.printer_segments else None

    @property
    def cutter_id(self) -> str | None:
        return self.cutter_segments[-1].device_id if self.cutter_segments else None


class EquipmentScheduler:
    """Распределяет целые заказы; листы разделяются только при аварийном переносе."""

    def __init__(self, devices: list[Device]):
        self.devices = {device.device_id: device for device in devices}
        self.assignments: dict[str, DeviceAssignment] = {}
        self.queued_sheets: dict[str, int] = {device.device_id: 0 for device in devices}

    def _choose(self, *, kind: DeviceKind, role: str, material: str, profile: str | None = None) -> Device:
        candidates = [
            device for device in self.devices.values()
            if device.can_run(kind=kind, role=role, material=material, profile=profile)
        ]
        if not candidates:
            raise RuntimeError("Нет готового и откалиброванного устройства для задания")
        return min(candidates, key=lambda item: (self.queued_sheets[item.device_id], item.device_id))

    def assign_order(self, order_id: str, total_sheets: int, material: str, cut_profile: str) -> DeviceAssignment:
        if order_id in self.assignments:
            return self.assignments[order_id]
        printer = self._choose(kind=DeviceKind.PRINTER, role="stickers", material=material)
        cutter = self._choose(kind=DeviceKind.CUTTER, role="contour_cut", material=material, profile=cut_profile)
        assignment = DeviceAssignment(
            order_id=order_id,
            total_sheets=total_sheets,
            printer_segments=[ProductionSegment(printer.device_id, 1, total_sheets)],
            cutter_segments=[ProductionSegment(cutter.device_id, 1, total_sheets)],
        )
        self.assignments[order_id] = assignment
        self.queued_sheets[printer.device_id] += total_sheets
        self.queued_sheets[cutter.device_id] += total_sheets
        return assignment

    def emergency_transfer(
        self,
        order_id: str,
        *,
        kind: DeviceKind,
        new_device_id: str,
        last_confirmed_sheet: int,
        material: str,
        cut_profile: str | None = None,
        reason: str,
    ) -> ProductionSegment | None:
        assignment = self.assignments[order_id]
        if not 0 <= last_confirmed_sheet <= assignment.total_sheets:
            raise ValueError("Неверный номер последнего подтверждённого листа")
        if last_confirmed_sheet == assignment.total_sheets:
            return None
        role = "stickers" if kind == DeviceKind.PRINTER else "contour_cut"
        target = self.devices[new_device_id]
        if not target.can_run(kind=kind, role=role, material=material, profile=cut_profile):
            raise RuntimeError("Новое устройство не готово или не имеет подходящего профиля")
        segment = ProductionSegment(
            device_id=new_device_id,
            first_sheet=last_confirmed_sheet + 1,
            last_sheet=assignment.total_sheets,
            reason=reason,
        )
        segments = assignment.printer_segments if kind == DeviceKind.PRINTER else assignment.cutter_segments
        previous = segments[-1]
        segments[-1] = ProductionSegment(
            device_id=previous.device_id,
            first_sheet=previous.first_sheet,
            last_sheet=last_confirmed_sheet,
            reason=previous.reason,
        )
        segments.append(segment)
        self.queued_sheets[new_device_id] += segment.last_sheet - segment.first_sheet + 1
        return segment

