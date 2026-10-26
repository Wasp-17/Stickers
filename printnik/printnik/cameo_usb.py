"""Narrow USBPRINT controls for the confirmed Cameo 5 Alpha on Windows.

The first direct-cut experiment is limited to one fixed 12 mm square on a
separate matte sticker sheet. General order cut plans are never sent here.
"""

from __future__ import annotations

import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path

from .cut_plan import CutPlanError, plan_svg
from .direct_cut import prepare_direct_sheet


USBPRINT_GUID = uuid.UUID("28d78fad-5a12-11d1-ae5b-0000f803a8c2")
VID = "vid_3844"
PID = "pid_0001"
DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10
ERROR_NO_MORE_ITEMS = 259
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
FIRMWARE_QUERY = b"FG\x03"
STATUS_QUERY = b"\x1b\x05"
TOOL_QUERY = b"\x1b\x15"
TERMINATOR = b"\x03"
REGISTRATION_SETUP = (b"TB50,0\x03", b"TB99\x03", b"TB52,2\x03",
                      b"TB51,400\x03", b"TB53,10\x03", b"TB55,1\x03")
# The printed control line spans x=80..130 at y=45 mm. After registration,
# the upper-left mark at (10,10) is the device origin; M is tool-up travel.
CONTROL_LINE_MOVE = b"M700,1900\x03"
FIRST_CUT_GEOMETRY = (5240, 3800, 0, 0)
FIRST_CUT_SETUP = (
    b"TG0\x03",       # No cutting mat, as for the successful optical tests.
    b"J1\x03",        # AutoBlade in holder 1.
    b"FX10,1\x03",    # First-trial force; found too deep for kiss-cutting.
    b"TJ0\x03",
    b"!4,1\x03",      # Speed 4.
    b"FC0,1,1\x03",
    b"FE0,1\x03",
    b"FF1,0,1\x03",
    b"FF1,1,1\x03",
    b"FX10,1\x03",
    b"TJ3\x03",
    b"FC18,1,1\x03",  # 0.9 mm blade offset, 0.05 mm second component.
    b"TF3,1\x03",     # First-trial depth; found too deep for kiss-cutting.
)
# Coordinates are y,x relative to the upper-left mark at page (10,10).
# This 48 mm closed contour is the only permitted drawing command sequence.
FIRST_CUT_PATH = (
    b"M4700,800\x03", b"D4700,1040\x03", b"D4940,1040\x03",
    b"D4940,800\x03", b"D4700,800\x03", b"M4700,800\x03",
)
# Second trial uses blank space on the SAME printed sheet, 18 mm to the right
# of the first square. Depth and force are reduced; this is still an experiment,
# not a calibrated production kiss-cut setting.
KISS_TEST_SETUP = tuple(
    command.replace(b"FX10,1", b"FX4,1").replace(b"TF3,1", b"TF1,1")
    for command in FIRST_CUT_SETUP
)
KISS_TEST_PATH = (
    b"M4700,1400\x03", b"D4700,1600\x03", b"D4900,1600\x03",
    b"D4900,1400\x03", b"D4700,1400\x03", b"M4700,1400\x03",
)
MAX_CUT_PACKET_BYTES = 750
DIRECT_CAT_PRINT_SHA256 = "0c2339159cb2345b1cc5742186f6277250098a9541a0aa84c6e1f6daae44e305"
DIRECT_CAT_CUT_SHA256 = "5069b13f05f89702ac988e045718a73dff98ca73af239572570085b70f645af8"
CAT_GAP_PRINT_SHA256 = "6c654f84e8ee23dd4b45b63c1b720a5522f7d5f9d9b7030b0f16266e9eeffad8"
CAT_GAP_CUT_SHA256 = "f038d2e6c9e8455470a05ed26b472d5d2aaa299062f703f35b1843fb8134a0f2"
CAT_SMOOTH_CUT_SHA256 = "3c6fc2fc1efb2470a1b0813cdd7c90725433d36af82118f96e5de8f3af0f14c1"


class CameoConnectionError(RuntimeError):
    pass


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class InterfaceData(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


def _failure(action: str) -> CameoConnectionError:
    number = ctypes.get_last_error()
    return CameoConnectionError(f"{action}: ошибка Windows {number} ({ctypes.FormatError(number).strip()})")


def find_cameo_interface() -> str:
    """Find the exact Cameo 5 Alpha USBPRINT interface, never another printer."""
    if sys.platform != "win32":
        raise CameoConnectionError("Проверка USB рассчитана на Windows")
    setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
    setupapi.SetupDiGetClassDevsW.argtypes = [
        ctypes.POINTER(GUID), ctypes.c_wchar_p, ctypes.c_void_p, wintypes.DWORD
    ]
    setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
    setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GUID),
        wintypes.DWORD, ctypes.POINTER(InterfaceData)
    ]
    setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
    setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(InterfaceData), ctypes.c_void_p,
        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
    ]
    setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
    setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
    setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

    guid = GUID.from_buffer_copy(USBPRINT_GUID.bytes_le)
    devices = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if devices == INVALID_HANDLE_VALUE:
        raise _failure("Не удалось получить список USB-устройств")
    try:
        index = 0
        while True:
            item = InterfaceData()
            item.cbSize = ctypes.sizeof(item)
            if not setupapi.SetupDiEnumDeviceInterfaces(
                devices, None, ctypes.byref(guid), index, ctypes.byref(item)
            ):
                if ctypes.get_last_error() == ERROR_NO_MORE_ITEMS:
                    raise CameoConnectionError("Cameo 5 Alpha не найден по USB. Проверьте питание и кабель.")
                raise _failure("Не удалось прочитать USB-интерфейс")
            size = wintypes.DWORD()
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                devices, ctypes.byref(item), None, 0, ctypes.byref(size), None
            )
            if size.value < 8:
                raise CameoConnectionError("Windows вернула неверный размер USB-интерфейса")
            detail = ctypes.create_string_buffer(size.value)
            ctypes.cast(detail, ctypes.POINTER(wintypes.DWORD))[0] = (
                8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            )
            if not setupapi.SetupDiGetDeviceInterfaceDetailW(
                devices, ctypes.byref(item), detail, size.value, ctypes.byref(size), None
            ):
                raise _failure("Не удалось получить путь USB-интерфейса")
            path = ctypes.wstring_at(ctypes.addressof(detail) + 4)
            if VID in path.lower() and PID in path.lower():
                return path
            index += 1
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(devices)


def parse_firmware(response: bytes) -> str:
    if not response.endswith(TERMINATOR):
        raise CameoConnectionError("Ответ о прошивке не завершён")
    firmware = response[:-1].decode("ascii", "replace").strip()
    if not firmware.upper().startswith("CAMEO 5 ALPHA "):
        raise CameoConnectionError(f"Неожиданный ответ о модели: {firmware!r}")
    return firmware


def parse_status(response: bytes) -> str:
    if not response.endswith(TERMINATOR):
        raise CameoConnectionError("Ответ о состоянии не завершён")
    states = {b"0": "ready", b"1": "moving", b"2": "unloaded"}
    return states.get(response[:-1], "unknown")


def parse_tool_setup(response: bytes) -> tuple[int, int]:
    """Return Cameo's two holder codes; code 2 identifies an AutoBlade."""
    if not response.endswith(TERMINATOR):
        raise CameoConnectionError("Ответ о ножах не завершён")
    try:
        parts = response[:-1].decode("ascii").strip().split(",")
        if len(parts) != 2:
            raise ValueError("expected two tool codes")
        codes = tuple(int(part.strip()) for part in parts)
    except (UnicodeError, ValueError) as exc:
        raise CameoConnectionError("Непонятный ответ о ножах Cameo") from exc
    if any(code < 0 or code > 99 for code in codes):
        raise CameoConnectionError("Неподдерживаемый код инструмента Cameo")
    return codes


@contextmanager
def _connection(allowed_extra: tuple[bytes, ...] = ()):
    path = find_cameo_interface()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.WriteFile.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
    ]
    kernel32.WriteFile.restype = wintypes.BOOL
    kernel32.ReadFile.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
    ]
    kernel32.ReadFile.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.CreateFileW(
        path, GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None
    )
    if handle == INVALID_HANDLE_VALUE:
        raise CameoConnectionError(
            f"Плоттер занят или недоступен ({ctypes.get_last_error()}). "
            "Сохраните работу и закройте Silhouette Studio, затем повторите проверку."
        )
    try:
        class Connection:
            def _write_validated(self, payload: bytes) -> None:
                written = wintypes.DWORD()
                buffer = ctypes.create_string_buffer(payload)
                if not kernel32.WriteFile(handle, buffer, len(payload), ctypes.byref(written), None):
                    raise _failure("Не удалось отправить запрос плоттеру")
                if written.value != len(payload):
                    raise CameoConnectionError("Запрос отправлен не полностью")

            def write(self, command: bytes) -> None:
                if not command or command not in (FIRMWARE_QUERY, STATUS_QUERY, TOOL_QUERY,
                                                   CONTROL_LINE_MOVE, *REGISTRATION_SETUP,
                                                   *FIRST_CUT_SETUP, *FIRST_CUT_PATH,
                                                   *KISS_TEST_SETUP, *KISS_TEST_PATH,
                                                   *allowed_extra) \
                        and not _is_registration_search(command):
                    raise CameoConnectionError("Команда не входит в разрешённый набор Cameo")
                self._write_validated(command)

            def write_batch(self, commands: tuple[bytes, ...], allowed: tuple[bytes, ...]) -> None:
                if not commands or any(command not in allowed for command in commands):
                    raise CameoConnectionError("Пакет содержит неподтверждённую команду")
                payload = b"".join(commands)
                if len(payload) > 4096:
                    raise CameoConnectionError("Пакет команд слишком велик")
                self._write_validated(payload)

            def read(self) -> bytes:
                answer = ctypes.create_string_buffer(256)
                received = wintypes.DWORD()
                if not kernel32.ReadFile(handle, answer, len(answer), ctypes.byref(received), None):
                    raise _failure("Не удалось прочитать ответ плоттера")
                return answer.raw[:received.value]

            def exchange(self, command: bytes) -> bytes:
                self.write(command)
                return self.read()

        yield Connection()
    finally:
        kernel32.CloseHandle(handle)


def _is_registration_search(command: bytes) -> bool:
    return command in {f"TB124,{(287 - bottom) * 20},3800,0,0\x03".encode("ascii")
                       for bottom in range(10, 26)}


def _query_worker() -> dict[str, str]:
    """Run in a child process so a stalled USB read can be timed out safely."""
    with _connection() as device:
        firmware = parse_firmware(device.exchange(FIRMWARE_QUERY))
        status = parse_status(device.exchange(STATUS_QUERY))
        tool_codes = parse_tool_setup(device.exchange(TOOL_QUERY))
        return {"firmware": firmware, "status": status,
                "tool_1": str(tool_codes[0]), "tool_2": str(tool_codes[1])}


def registration_geometry(manifest_path: Path) -> tuple[int, int, int, int]:
    """Accept the controlled A4 experiment with a 10–25 mm lower offset."""
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CameoConnectionError("Не удалось прочитать описание пробного листа") from exc
    if manifest.get("status") != "experimental_unverified" or manifest.get("cut_file") is not None:
        raise CameoConnectionError("Это не отдельный пробный лист без резки")
    if manifest.get("page_mm") != [210, 297] or manifest.get("length_mm") != 20:
        raise CameoConnectionError("Ожидается пробный лист A4 с метками длиной 20 мм")
    offsets = manifest.get("offsets_mm", {})
    if any(offsets.get(side) != 10 for side in ("left_mm", "right_mm", "top_mm")):
        raise CameoConnectionError("Пробный поиск рассчитан на отступы 10 мм слева, справа и сверху")
    bottom = offsets.get("bottom_mm")
    if type(bottom) not in (int, float) or not float(bottom).is_integer() or not 10 <= bottom <= 25:
        raise CameoConnectionError("Нижний отступ для поиска должен быть целым числом от 10 до 25 мм")
    bottom = int(bottom)
    origins = [[10, 10], [200, 10], [10, 297 - bottom], [200, 297 - bottom]]
    if manifest.get("mark_origins_mm") != origins:
        raise CameoConnectionError("Координаты меток не совпадают с пробным листом")
    # Cameo units: 20 per mm. Y spacing precedes X spacing in TB124.
    return (287 - bottom) * 20, 3800, 0, 0


def registration_commands(geometry: tuple[int, int, int, int]) -> tuple[bytes, ...]:
    valid = {((287 - bottom) * 20, 3800, 0, 0) for bottom in range(10, 26)}
    if geometry not in valid:
        raise CameoConnectionError("Непроверенная геометрия поиска меток")
    return (*REGISTRATION_SETUP, f"TB124,{geometry[0]},3800,0,0\x03".encode("ascii"))


def parse_registration_result(response: bytes) -> str:
    if not response.endswith(TERMINATOR):
        raise CameoConnectionError("Ответ поиска меток не завершён")
    if response[:-1].strip() == b"0":
        return "found"
    if len(response) > 80:
        raise CameoConnectionError("Неверный ответ поиска меток")
    return "not_found"


def _scan_worker(geometry: tuple[int, int, int, int]) -> dict[str, str]:
    with _connection() as device:
        firmware = parse_firmware(device.exchange(FIRMWARE_QUERY))
        status = parse_status(device.exchange(STATUS_QUERY))
        if status != "ready":
            raise CameoConnectionError("Для поиска меток загрузите лист и дождитесь состояния «Готово»")
        for command in registration_commands(geometry):
            device.write(command)
        answer = device.read()
        return {"firmware": firmware, "status": parse_registration_result(answer),
                "raw_response_hex": answer.hex()}


def _position_worker(geometry: tuple[int, int, int, int]) -> dict[str, str]:
    """Find the tested marks, then move the raised tool above the control line."""
    if geometry != (5240, 3800, 0, 0):
        raise CameoConnectionError("Проверка положения рассчитана только на лист с нижним отступом 25 мм")
    with _connection() as device:
        firmware = parse_firmware(device.exchange(FIRMWARE_QUERY))
        status = parse_status(device.exchange(STATUS_QUERY))
        if status != "ready":
            raise CameoConnectionError("Загрузите лист и дождитесь состояния «Готово»")
        for command in registration_commands(geometry):
            device.write(command)
        answer = device.read()
        if parse_registration_result(answer) != "found":
            return {"firmware": firmware, "status": "not_found", "raw_response_hex": answer.hex()}
        device.write(CONTROL_LINE_MOVE)
        return {"firmware": firmware, "status": "position_command_sent",
                "raw_response_hex": answer.hex()}


def validate_first_cut_manifest(manifest_path: Path) -> None:
    """Reject anything except the fixed 12 mm matte trial printed for this step."""
    path = Path(manifest_path)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CameoConnectionError("Не удалось прочитать описание пробного реза") from exc
    required = {
        "status": "first_cut_prepared_not_sent", "usb_cut_enabled": True,
        "page_mm": [210, 297], "length_mm": 20,
        "offsets_mm": {"left_mm": 10, "right_mm": 10, "top_mm": 10, "bottom_mm": 25},
        "mark_origins_mm": [[10, 10], [200, 10], [10, 272], [200, 272]],
        "target_box_mm": [50, 245, 62, 257],
        "cut_path_mm": [[50, 245], [62, 245], [62, 257], [50, 257], [50, 245]],
        "cut_length_mm": 48, "material_id": "matte_white",
    }
    if any(manifest.get(key) != value for key, value in required.items()):
        raise CameoConnectionError("Нужен строго подготовленный лист для первого пробного реза")
    if path.name != "first-cut.json" or not (path.parent / "first-cut-print.pdf").is_file():
        raise CameoConnectionError("Не найден печатный файл этого пробного листа")


def _wait_for_ready(device, timeout: float = 60) -> str:
    """Wait for two successive idle reports after queued movement commands."""
    deadline = time.monotonic() + timeout
    consecutive_ready = 0
    state = "unknown"
    while time.monotonic() < deadline:
        time.sleep(0.2)
        state = parse_status(device.exchange(STATUS_QUERY))
        if state == "ready":
            consecutive_ready += 1
            if consecutive_ready >= 2:
                return "ready"
        else:
            consecutive_ready = 0
        if state in ("unloaded", "unknown"):
            return state
    return state


def _square_cut_worker(setup: tuple[bytes, ...], path: tuple[bytes, ...]) -> dict[str, str]:
    """One fixed square only; nothing is cut unless four marks are confirmed."""
    with _connection() as device:
        firmware = parse_firmware(device.exchange(FIRMWARE_QUERY))
        status = parse_status(device.exchange(STATUS_QUERY))
        if status != "ready":
            raise CameoConnectionError("Загрузите матовый лист и дождитесь состояния «Готово»")
        tool_1, _tool_2 = parse_tool_setup(device.exchange(TOOL_QUERY))
        if tool_1 != 2:
            raise CameoConnectionError("В гнезде 1 должен быть AutoBlade; рез не запускался")
        for command in setup:
            device.write(command)
        for command in registration_commands(FIRST_CUT_GEOMETRY):
            device.write(command)
        answer = device.read()
        if parse_registration_result(answer) != "found":
            return {"firmware": firmware, "status": "not_found", "raw_response_hex": answer.hex()}
        for command in path:
            device.write(command)
        # A successful USB write only means the cutter received the commands.
        # Poll the machine before saying its motion has finished. Keep the sheet
        # loaded so the operator can inspect it and choose when to unload it.
        state = _wait_for_ready(device)
        return {"firmware": firmware,
                "status": "cut_device_ready" if state == "ready" else "cut_completion_unconfirmed",
                "raw_response_hex": answer.hex()}


def _first_cut_worker() -> dict[str, str]:
    return _square_cut_worker(FIRST_CUT_SETUP, FIRST_CUT_PATH)


def _kiss_test_worker() -> dict[str, str]:
    return _square_cut_worker(KISS_TEST_SETUP, KISS_TEST_PATH)


def _blade_check_worker(manifest_path: Path) -> dict[str, str]:
    validate_blade_check_manifest(manifest_path)
    return _square_cut_worker(KISS_TEST_SETUP, KISS_TEST_PATH)


def validate_direct_cat_manifest(manifest_path: Path) -> tuple[bytes, ...]:
    """Accept only a pinned cat print/contour pair for a one-time trial."""
    path = Path(manifest_path)
    if path.name not in ("direct-cat-trial.json", "cat-gap-trial.json",
                         "cat-gap-retry.json", "cat-gap-batch-trial.json",
                         "cat-smooth-trial.json"):
        raise CameoConnectionError("Нужно описание подготовленного листа с котом")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CameoConnectionError("Не удалось прочитать описание листа с котом") from exc
    expected = {
        "status": "direct_cat_trial_prepared_not_sent",
        "source_order": "RK-2026-000001", "asset_id": "RK17-0105", "size_code": "B",
        "material_id": "matte_white", "page_mm": [210, 297],
        "offsets_mm": {"left_mm": 10, "right_mm": 10, "top_mm": 10, "bottom_mm": 25},
        "mark_origins_mm": [[10, 10], [200, 10], [10, 272], [200, 272]],
        "source_outward_mm": 0.6, "translation_mm": [60.0, 115.0],
        "cut_bounds_mm": [90.381, 126.381, 122.004, 177.647],
        "cut_point_count": 342,
        "print_pdf": "direct-cat-print.pdf", "print_sha256": DIRECT_CAT_PRINT_SHA256,
        "cut_svg": "direct-cat-cut.svg", "cut_sha256": DIRECT_CAT_CUT_SHA256,
        "blade": 1, "force": 4, "speed": 4, "passes": 1,
        "usb_cut_enabled": True,
    }
    if path.name in ("cat-gap-trial.json", "cat-gap-retry.json", "cat-gap-batch-trial.json",
                     "cat-smooth-trial.json"):
        expected.update({
            "status": "cat_gap_trial_prepared_not_sent",
            "contour_offset_mm": {"outer": 0.6, "head_gaps": "locally 0.2-0.4"},
            "cut_point_count": 398,
            "print_pdf": "cat-gap-print.pdf", "print_sha256": CAT_GAP_PRINT_SHA256,
            "cut_svg": "cat-gap-cut.svg", "cut_sha256": CAT_GAP_CUT_SHA256,
        })
        del expected["source_outward_mm"]
    if path.name == "cat-gap-batch-trial.json":
        expected["status"] = "cat_gap_batch_trial_prepared_not_sent"
    if path.name == "cat-smooth-trial.json":
        expected.update({
            "status": "cat_smooth_trial_prepared_not_sent",
            "cut_point_count": 321,
            "cut_svg": "cat-smooth-cut.svg",
            "cut_sha256": CAT_SMOOTH_CUT_SHA256,
            "source_cut_sha256": CAT_GAP_CUT_SHA256,
            "simplification_max_deviation_mm": 0.1,
            "protected_head_y_mm": 155,
        })
    if path.name == "cat-gap-retry.json":
        expected.update({
            "status": "cat_gap_retry_prepared_not_sent",
            "previous_attempt": "cat-gap-attempt.json",
            "blade_check_attempt": "cat-gap-blade-check-attempt.json",
        })
        try:
            prior = json.loads((path.parent / expected["previous_attempt"]).read_text(encoding="utf-8"))
            blade_check = json.loads((path.parent / expected["blade_check_attempt"]).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CameoConnectionError("Нет записей первой пробы и проверки ножа; повторный рез остановлен") from exc
        if (prior.get("status") != "cut_device_ready" or
                prior.get("physical_result") != "no_cut_or_visible_score" or
                blade_check.get("status") != "cut_device_ready" or
                blade_check.get("physical_result") != "sticker_cut_backing_intact"):
            raise CameoConnectionError("Результаты первой пробы и проверки ножа не позволяют повторить рез")
        validate_direct_cat_manifest(path.with_name("cat-gap-trial.json"))
    if manifest != expected:
        raise CameoConnectionError("Описание листа или параметры реза не совпадают с проверенным опытом")
    pdf = path.parent / expected["print_pdf"]
    svg = path.parent / expected["cut_svg"]
    try:
        pdf_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
        svg_hash = hashlib.sha256(svg.read_bytes()).hexdigest()
    except OSError as exc:
        raise CameoConnectionError("Не найден печатный лист или контур кота") from exc
    if pdf_hash != expected["print_sha256"] or svg_hash != expected["cut_sha256"]:
        raise CameoConnectionError("Печатный лист или контур кота изменён; рез отключён")
    try:
        plan = plan_svg(svg)
    except CutPlanError as exc:
        raise CameoConnectionError("Контур кота не удалось проверить") from exc
    if len(plan["contours"]) != 1 or len(plan["contours"][0]["points_mm"]) != expected["cut_point_count"]:
        raise CameoConnectionError("Ожидался один проверенный контур кота")
    points = plan["contours"][0]["points_mm"]
    if any(not (90 <= x <= 123 and 126 <= y <= 179) for x, y in points):
        raise CameoConnectionError("Контур кота вышел за пределы пробной области")
    coords = [(round((y - 10) * 20), round((x - 10) * 20)) for x, y in points]
    path_commands = [f"M{coords[0][0]},{coords[0][1]}\x03".encode("ascii")]
    path_commands += [f"D{y},{x}\x03".encode("ascii") for y, x in coords[1:]]
    path_commands += [f"D{coords[0][0]},{coords[0][1]}\x03".encode("ascii"),
                      path_commands[0]]
    return tuple(path_commands)


def packetize_cut_path(commands: tuple[bytes, ...]) -> tuple[tuple[bytes, ...], ...]:
    """Keep whole commands in USB writes small enough for the proven buffer size."""
    if not commands or any(not command.endswith(TERMINATOR) for command in commands):
        raise CameoConnectionError("Контур содержит незавершённую команду")
    packets: list[tuple[bytes, ...]] = []
    current: list[bytes] = []
    size = 0
    for command in commands:
        if len(command) > MAX_CUT_PACKET_BYTES:
            raise CameoConnectionError("Команда контура слишком длинная")
        if current and size + len(command) > MAX_CUT_PACKET_BYTES:
            packets.append(tuple(current))
            current = []
            size = 0
        current.append(command)
        size += len(command)
    if current:
        packets.append(tuple(current))
    return tuple(packets)


def _direct_cat_worker(manifest_path: Path) -> dict[str, str]:
    path_commands = validate_direct_cat_manifest(manifest_path)
    with _connection(path_commands) as device:
        firmware = parse_firmware(device.exchange(FIRMWARE_QUERY))
        if parse_status(device.exchange(STATUS_QUERY)) != "ready":
            raise CameoConnectionError("Загрузите напечатанный лист с котом и дождитесь состояния «Готово»")
        tool_1, _tool_2 = parse_tool_setup(device.exchange(TOOL_QUERY))
        if tool_1 != 2:
            raise CameoConnectionError("В гнезде 1 должен быть AutoBlade; рез не запускался")
        for command in KISS_TEST_SETUP:
            device.write(command)
        for command in registration_commands(FIRST_CUT_GEOMETRY):
            device.write(command)
        answer = device.read()
        if parse_registration_result(answer) != "found":
            return {"firmware": firmware, "status": "not_found", "raw_response_hex": answer.hex()}
        # Whole-command packets kept both circles and the physically verified
        # 321-point printed cat smooth, with no display flicker.
        for packet in packetize_cut_path(path_commands):
            device.write_batch(packet, path_commands)
        state = _wait_for_ready(device, timeout=120)
        return {"firmware": firmware,
                "status": "cut_device_ready" if state == "ready" else "cut_completion_unconfirmed",
                "raw_response_hex": answer.hex()}


def _direct_order_worker(output_dir: Path, sheet_no: int) -> dict:
    """One approved sheet, using the exact setup and transport of the pilot."""
    try:
        preview = prepare_direct_sheet(output_dir, sheet_no)
    except CutPlanError as exc:
        raise CameoConnectionError(str(exc)) from exc
    packets = packetize_cut_path(preview.commands)
    with _connection(preview.commands) as device:
        firmware = parse_firmware(device.exchange(FIRMWARE_QUERY))
        if parse_status(device.exchange(STATUS_QUERY)) != "ready":
            raise CameoConnectionError("Загрузите утверждённый лист и дождитесь состояния «Готово»")
        tool_1, _ = parse_tool_setup(device.exchange(TOOL_QUERY))
        if tool_1 != 2:
            raise CameoConnectionError("В гнезде 1 должен быть AutoBlade; рез не запускался")
        for command in KISS_TEST_SETUP:
            device.write(command)
        for command in registration_commands(FIRST_CUT_GEOMETRY):
            device.write(command)
        answer = device.read()
        if parse_registration_result(answer) != "found":
            return {"firmware": firmware, "status": "not_found",
                    "raw_response_hex": answer.hex(), "sent_packet_count": 0}
        sent = 0
        for packet in packets:
            device.write_batch(packet, preview.commands)
            sent += 1
        # The first, denser sheet can take much longer than the verified
        # 2,809-command pilot. Keep waiting for the cutter after the last write.
        state = _wait_for_ready(device, timeout=900 if preview.command_count > 3000 else 300)
        return {"firmware": firmware,
                "status": "cut_device_ready" if state == "ready" else "cut_completion_unconfirmed",
                "raw_response_hex": answer.hex(), "sent_packet_count": sent,
                "packet_count": len(packets), "command_count": preview.command_count}


def _status_burst_worker() -> dict[str, str | list[str]]:
    """Read-only diagnostic: twenty status requests, with no motion commands."""
    with _connection() as device:
        firmware = parse_firmware(device.exchange(FIRMWARE_QUERY))
        statuses = []
        for _ in range(20):
            statuses.append(parse_status(device.exchange(STATUS_QUERY)))
            time.sleep(0.2)
        return {"firmware": firmware, "statuses": statuses, "status": "read_only_complete"}


def _tool_up_motion_worker(manifest_path: Path, *, interleaved_status: bool = True) -> dict[str, str]:
    """Replay a sparse, vetted cat route with M only; never lower the blade."""
    cut_path = validate_direct_cat_manifest(manifest_path)
    points = cut_path[:-2:4]
    moves = tuple(b"M" + command[1:] for command in points)
    if len(moves) != 86 or any(not command.startswith(b"M") for command in moves):
        raise CameoConnectionError("Пробный маршрут без ножа изменён; движение отключено")
    with _connection(moves) as device:
        firmware = parse_firmware(device.exchange(FIRMWARE_QUERY))
        if parse_status(device.exchange(STATUS_QUERY)) != "ready":
            raise CameoConnectionError("Загрузите пробный лист с котом и дождитесь «Готово»")
        for command in registration_commands(FIRST_CUT_GEOMETRY):
            device.write(command)
        answer = device.read()
        if parse_registration_result(answer) != "found":
            return {"firmware": firmware, "status": "not_found", "raw_response_hex": answer.hex()}
        if interleaved_status:
            for index, command in enumerate(moves, 1):
                device.write(command)
                if index % 20 == 0 and _wait_for_ready(device, timeout=120) != "ready":
                    return {"firmware": firmware, "status": "motion_completion_unconfirmed",
                            "raw_response_hex": answer.hex()}
        else:
            for command in moves:
                device.write(command)
            # End at a visibly different, safe location so the operator can
            # distinguish a full route from the first move alone.
            device.write(CONTROL_LINE_MOVE)
        state = _wait_for_ready(device, timeout=120)
        return {"firmware": firmware,
                "status": "motion_device_ready" if state == "ready" else "motion_completion_unconfirmed",
                "raw_response_hex": answer.hex()}


def _run_worker(mode: str, timeout: float, geometry: tuple[int, int, int, int] | None = None,
                manifest_path: Path | None = None, sheet_no: int | None = None) -> dict:
    if sys.platform != "win32":
        raise CameoConnectionError("Проверка USB рассчитана на Windows")
    descriptor, result_path = tempfile.mkstemp(prefix="printnik-cameo-", suffix=".json")
    os.close(descriptor)
    worker_arg = {"scan": "--cameo-scan-worker", "position": "--cameo-position-worker",
                  "kiss_test": "--cameo-kiss-test-worker",
                  "blade_check": "--cameo-blade-check-worker",
                  "direct_cat": "--cameo-direct-cat-worker",
                  "direct_order": "--cameo-direct-order-worker",
                  "status_burst": "--cameo-status-burst-worker",
                  "tool_up_motion": "--cameo-tool-up-motion-worker",
                  "tool_up_smooth": "--cameo-tool-up-smooth-worker",
                  "probe": "--cameo-probe-worker"}[mode]
    command = ([sys.executable, worker_arg] if getattr(sys, "frozen", False)
               else [sys.executable, "-m", "printnik.cameo_usb", worker_arg])
    if mode in ("scan", "position"):
        if geometry is None:
            raise CameoConnectionError("Не заданы координаты поиска меток")
        registration_commands(geometry)
        command.append(f"--cameo-scan-height={geometry[0]}")
    if mode in ("direct_cat", "tool_up_motion", "tool_up_smooth", "blade_check"):
        if manifest_path is None:
            raise CameoConnectionError("Не выбран пробный лист с котом")
        command.append(f"--cameo-trial-manifest={Path(manifest_path).resolve()}")
    if mode == "direct_order":
        if manifest_path is None or type(sheet_no) is not int or sheet_no < 1:
            raise CameoConnectionError("Не задан лист заказа для прямого реза")
        command.append(f"--cameo-order-dir={Path(manifest_path).resolve()}")
        command.append(f"--cameo-sheet-no={sheet_no}")
    command.append(f"--cameo-probe-result={result_path}")
    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        Path(result_path).unlink(missing_ok=True)
        raise CameoConnectionError(f"Плоттер не ответил за {timeout:g} секунд. "
                                    "Проверьте состояние устройства и закройте Studio.") from exc
    try:
        payload_text = Path(result_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CameoConnectionError("Проверка USB завершилась без ответа. Проверьте подключение Cameo.") from exc
    finally:
        Path(result_path).unlink(missing_ok=True)
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise CameoConnectionError("Не удалось прочитать результат проверки USB") from exc
    if result.returncode != 0:
        raise CameoConnectionError(payload.get("error", "Проверка USB завершилась ошибкой"))
    return payload


def probe_cameo(timeout: float = 20) -> dict[str, str]:
    """Get firmware and status without moving the device or changing drivers."""
    result = _run_worker("probe", timeout)
    return {"firmware": result["firmware"], "status": result["status"],
            "tool_1": result["tool_1"], "tool_2": result["tool_2"]}


def probe_status_burst(timeout: float = 30) -> dict[str, str | list[str]]:
    """Read twenty status reports without sending a movement or knife command."""
    return _run_worker("status_burst", timeout)


def probe_tool_up_motion(manifest_path: Path, timeout: float = 300) -> dict[str, str]:
    """No-cut movement diagnostic on the already printed cat sheet."""
    validate_direct_cat_manifest(manifest_path)
    return _run_worker("tool_up_motion", timeout, manifest_path=manifest_path)


def probe_tool_up_smooth(manifest_path: Path, timeout: float = 300) -> dict[str, str]:
    """Repeat the same tool-up route without status requests mid-path."""
    validate_direct_cat_manifest(manifest_path)
    return _run_worker("tool_up_smooth", timeout, manifest_path=manifest_path)


def scan_registration_marks(manifest_path: Path, timeout: float = 120) -> dict[str, str]:
    """Search four printed marks; never send a knife/cut command."""
    geometry = registration_geometry(manifest_path)
    result = _run_worker("scan", timeout, geometry)
    return {"firmware": result["firmware"], "status": result["status"],
            "raw_response_hex": result["raw_response_hex"]}


def position_over_control_line(manifest_path: Path, timeout: float = 120) -> dict[str, str]:
    """Move tool-up to the line midpoint, but only after a successful 25 mm scan."""
    geometry = registration_geometry(manifest_path)
    if geometry != (5240, 3800, 0, 0):
        raise CameoConnectionError("Нужен пробный лист с нижним отступом 25 мм")
    result = _run_worker("position", timeout, geometry)
    return {"firmware": result["firmware"], "status": result["status"],
            "raw_response_hex": result["raw_response_hex"]}


def run_first_cut_test(manifest_path: Path, timeout: float = 180) -> dict[str, str]:
    """The first settings cut the backing and must never be reused."""
    raise CameoConnectionError("Первый профиль прорезал подложку и отключён. "
                               "Используйте отдельный опыт с меньшей глубиной.")


def validate_kiss_test_manifest(manifest_path: Path) -> None:
    """Bind the lower-force trial to the already printed and inspected sheet."""
    path = Path(manifest_path)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        first = json.loads((path.parent / "first-cut.json").read_text(encoding="utf-8"))
        previous = json.loads((path.parent / "first-cut-attempt.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CameoConnectionError("Не найдены данные первого реза этого листа") from exc
    validate_first_cut_manifest(path.parent / "first-cut.json")
    required = {
        "status": "kiss_test_prepared_not_sent", "usb_cut_enabled": True,
        "page_mm": [210, 297], "material_id": "matte_white",
        "offsets_mm": first["offsets_mm"],
        "source_print": "first-cut-print.pdf", "source_first_cut": "first-cut.json",
        "target_box_mm": [80, 245, 90, 255],
        "cut_path_mm": [[80, 245], [90, 245], [90, 255], [80, 255], [80, 245]],
        "cut_length_mm": 40, "blade": 1, "force": 4, "speed": 4, "passes": 1,
    }
    if path.name != "kiss-test-1.json" or any(manifest.get(key) != value for key, value in required.items()):
        raise CameoConnectionError("Нужен подготовленный опыт с ножом 1 и силой 4")
    if previous.get("status") != "cut_commands_sent" or \
            not (path.parent / "first-cut-print.pdf").is_file():
        raise CameoConnectionError("Первый рез на этом листе не подтверждён")


def validate_blade_check_manifest(manifest_path: Path) -> None:
    """Bind a tiny blank-area control cut to the untouched failed cat sheet."""
    path = Path(manifest_path)
    if path.name != "cat-gap-blade-check.json":
        raise CameoConnectionError("Нужно описание проверки ножа на листе с котом")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        previous = json.loads((path.parent / "cat-gap-attempt.json").read_text(encoding="utf-8"))
        pdf_hash = hashlib.sha256((path.parent / "cat-gap-print.pdf").read_bytes()).hexdigest()
    except (OSError, ValueError) as exc:
        raise CameoConnectionError("Не найдены данные напечатанного листа и неудачного реза") from exc
    expected = {
        "status": "cat_gap_blade_check_prepared_not_sent",
        "material_id": "matte_white", "page_mm": [210, 297],
        "mark_origins_mm": [[10, 10], [200, 10], [10, 272], [200, 272]],
        "source_print": "cat-gap-print.pdf", "source_print_sha256": CAT_GAP_PRINT_SHA256,
        "previous_attempt": "cat-gap-attempt.json",
        "previous_physical_result": "no_cut_or_visible_score",
        "target_box_mm": [80, 245, 90, 255],
        "cut_path_mm": [[80, 245], [90, 245], [90, 255], [80, 255], [80, 245]],
        "blade": 1, "force": 4, "speed": 4, "passes": 1,
        "usb_cut_enabled": True,
    }
    if manifest != expected or pdf_hash != CAT_GAP_PRINT_SHA256 or \
            previous.get("physical_result") != "no_cut_or_visible_score":
        raise CameoConnectionError("Проверка ножа не соответствует напечатанному листу")


def run_blade_check(manifest_path: Path, timeout: float = 180) -> dict[str, str]:
    validate_blade_check_manifest(manifest_path)
    attempt_path = Path(manifest_path).with_name("cat-gap-blade-check-attempt.json")
    try:
        with attempt_path.open("x", encoding="utf-8") as file:
            json.dump({"started_at": datetime.now(timezone.utc).isoformat(), "status": "started"},
                      file, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise CameoConnectionError("Эта проверка ножа уже запускалась; повтор остановлен") from exc
    except OSError as exc:
        raise CameoConnectionError("Не удалось сохранить запись о проверке; рез не запускался") from exc
    try:
        result = _run_worker("blade_check", timeout, manifest_path=manifest_path)
        record = {"finished_at": datetime.now(timezone.utc).isoformat(), **result}
    except CameoConnectionError as exc:
        record = {"finished_at": datetime.now(timezone.utc).isoformat(),
                  "status": "error", "error": str(exc)}
        try:
            attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        raise
    try:
        attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise CameoConnectionError("Команды могли быть отправлены, но результат не сохранился; осмотрите лист") from exc
    return result


def run_kiss_test(manifest_path: Path, timeout: float = 180) -> dict[str, str]:
    """One 10 mm blank-area square using reduced depth and force."""
    validate_kiss_test_manifest(manifest_path)
    attempt_path = Path(manifest_path).with_name("kiss-test-1-attempt.json")
    try:
        with attempt_path.open("x", encoding="utf-8") as file:
            json.dump({"started_at": datetime.now(timezone.utc).isoformat(),
                       "status": "started"}, file, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise CameoConnectionError("Этот опыт уже запускался; повтор остановлен.") from exc
    except OSError as exc:
        raise CameoConnectionError("Не удалось сохранить запись о пробном резе; рез не запускался") from exc
    try:
        result = _run_worker("kiss_test", timeout)
        record = {"finished_at": datetime.now(timezone.utc).isoformat(), **result}
    except CameoConnectionError as exc:
        record = {"finished_at": datetime.now(timezone.utc).isoformat(),
                  "status": "error", "error": str(exc)}
        try:
            attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass  # The exclusive started marker still prevents an unsafe retry.
        raise
    try:
        attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise CameoConnectionError("Команды могли быть отправлены, но запись результата не сохранилась. "
                                    "Осмотрите лист перед любым повтором.") from exc
    return {"firmware": result["firmware"], "status": result["status"],
            "raw_response_hex": result["raw_response_hex"]}


def run_direct_cat_trial(manifest_path: Path, timeout: float = 600) -> dict[str, str]:
    """Send one reviewed cat contour and block accidental retries."""
    validate_direct_cat_manifest(manifest_path)
    attempt_path = Path(manifest_path).with_name(Path(manifest_path).stem.removesuffix("-trial") + "-attempt.json")
    try:
        with attempt_path.open("x", encoding="utf-8") as file:
            json.dump({"started_at": datetime.now(timezone.utc).isoformat(),
                       "status": "started"}, file, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise CameoConnectionError("Этот контур уже отправлялся. Осмотрите лист; повтор остановлен.") from exc
    except OSError as exc:
        raise CameoConnectionError("Не удалось сохранить запись о резе; рез не запускался") from exc
    try:
        result = _run_worker("direct_cat", timeout, manifest_path=manifest_path)
        record = {"finished_at": datetime.now(timezone.utc).isoformat(), **result}
    except CameoConnectionError as exc:
        record = {"finished_at": datetime.now(timezone.utc).isoformat(),
                  "status": "error", "error": str(exc)}
        try:
            attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        raise
    try:
        attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise CameoConnectionError("Команды могли быть отправлены, но результат не сохранился. "
                                    "Осмотрите лист перед повтором.") from exc
    return result


def run_direct_order_sheet(output_dir: Path, sheet_no: int, timeout: float = 600) -> dict:
    """Send one approved sheet once; an uncertain result still blocks repeats."""
    output_dir = Path(output_dir).resolve()
    try:
        preview = prepare_direct_sheet(output_dir, sheet_no)
    except CutPlanError as exc:
        raise CameoConnectionError(str(exc)) from exc
    attempt_path = output_dir / f"sheet-{sheet_no:02d}-direct-attempt.json"
    record = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "started_unsafe_to_repeat", "order_id": preview.order_id,
        "sheet_no": sheet_no, "print_sha256": preview.print_sha256,
        "cut_sha256": preview.cut_sha256, "command_count": preview.command_count,
    }
    try:
        with attempt_path.open("x", encoding="utf-8") as file:
            json.dump(record, file, ensure_ascii=False, indent=2)
    except FileExistsError as exc:
        raise CameoConnectionError("Этот лист уже отправлялся. Осмотрите его; повтор остановлен.") from exc
    except OSError as exc:
        raise CameoConnectionError("Не удалось записать попытку; рез не запускался") from exc
    try:
        worker_timeout = max(timeout, 1500 if preview.command_count > 3000 else 600)
        result = _run_worker("direct_order", worker_timeout, manifest_path=output_dir, sheet_no=sheet_no)
        record.update(result)
    except CameoConnectionError as exc:
        record.update(status="error_after_attempt_started", error=str(exc))
        raise
    finally:
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        try:
            attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            raise CameoConnectionError("Результат отправки не сохранился. Не повторяйте рез без осмотра листа.") from exc
    return result


def main() -> int:
    try:
        if "--cameo-status-burst-worker" in sys.argv:
            payload = _status_burst_worker()
        elif "--cameo-tool-up-motion-worker" in sys.argv or "--cameo-tool-up-smooth-worker" in sys.argv:
            trial_arg = next((arg for arg in sys.argv if arg.startswith("--cameo-trial-manifest=")), None)
            if trial_arg is None:
                raise CameoConnectionError("Не указан пробный лист с котом")
            payload = _tool_up_motion_worker(
                Path(trial_arg.split("=", 1)[1]),
                interleaved_status="--cameo-tool-up-motion-worker" in sys.argv,
            )
        elif "--cameo-direct-cat-worker" in sys.argv:
            trial_arg = next((arg for arg in sys.argv if arg.startswith("--cameo-trial-manifest=")), None)
            if trial_arg is None:
                raise CameoConnectionError("Не указан пробный лист с котом")
            payload = _direct_cat_worker(Path(trial_arg.split("=", 1)[1]))
        elif "--cameo-direct-order-worker" in sys.argv:
            folder_arg = next((arg for arg in sys.argv if arg.startswith("--cameo-order-dir=")), None)
            sheet_arg = next((arg for arg in sys.argv if arg.startswith("--cameo-sheet-no=")), None)
            if folder_arg is None or sheet_arg is None:
                raise CameoConnectionError("Не указан утверждённый лист заказа")
            try:
                sheet_no = int(sheet_arg.split("=", 1)[1])
            except ValueError as exc:
                raise CameoConnectionError("Неверный номер листа заказа") from exc
            payload = _direct_order_worker(Path(folder_arg.split("=", 1)[1]), sheet_no)
        elif "--cameo-kiss-test-worker" in sys.argv:
            payload = _kiss_test_worker()
        elif "--cameo-blade-check-worker" in sys.argv:
            trial_arg = next((arg for arg in sys.argv if arg.startswith("--cameo-trial-manifest=")), None)
            if trial_arg is None:
                raise CameoConnectionError("Не указана проверка ножа")
            payload = _blade_check_worker(Path(trial_arg.split("=", 1)[1]))
        elif "--cameo-scan-worker" in sys.argv or "--cameo-position-worker" in sys.argv:
            height_arg = next((arg for arg in sys.argv if arg.startswith("--cameo-scan-height=")), None)
            if height_arg is None:
                raise CameoConnectionError("Не задана высота поиска меток")
            try:
                height = int(height_arg.split("=", 1)[1])
            except ValueError as exc:
                raise CameoConnectionError("Неверная высота поиска меток") from exc
            geometry = (height, 3800, 0, 0)
            registration_commands(geometry)
            payload = (_position_worker(geometry) if "--cameo-position-worker" in sys.argv
                       else _scan_worker(geometry))
        else:
            payload = _query_worker()
        exit_code = 0
    except CameoConnectionError as exc:
        payload = {"error": str(exc)}
        exit_code = 1
    result_arg = next((arg for arg in sys.argv if arg.startswith("--cameo-probe-result=")), None)
    if result_arg:
        Path(result_arg.split("=", 1)[1]).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
