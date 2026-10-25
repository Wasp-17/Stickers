import unittest
import json
import uuid
from pathlib import Path
from unittest.mock import patch

from printnik.cameo_usb import (CONTROL_LINE_MOVE, FIRST_CUT_PATH, FIRST_CUT_SETUP,
                               KISS_TEST_PATH, KISS_TEST_SETUP, TOOL_QUERY,
                               CameoConnectionError, _first_cut_worker, _kiss_test_worker,
                               _position_worker, _query_worker, _scan_worker, parse_firmware,
                               parse_registration_result, parse_status, parse_tool_setup,
                               registration_commands, registration_geometry,
                               validate_first_cut_manifest, validate_kiss_test_manifest,
                               validate_direct_cat_manifest, validate_blade_check_manifest,
                               _blade_check_worker, _direct_cat_worker, packetize_cut_path,
                               _status_burst_worker, _tool_up_motion_worker)


class CameoUsbTests(unittest.TestCase):
    def test_read_only_probe_identifies_tool_holders(self):
        self.assertEqual(parse_tool_setup(b"    2,    0\x03"), (2, 0))
        with self.assertRaises(CameoConnectionError):
            parse_tool_setup(b"2,0")
        from contextlib import nullcontext
        class FakeDevice:
            def __init__(self):
                self.commands = []
            def exchange(self, command):
                self.commands.append(command)
                return {b"FG\x03": b"CAMEO 5 ALPHA V1.03\x03",
                        b"\x1b\x05": b"2\x03", TOOL_QUERY: b"2,0\x03"}[command]
        device = FakeDevice()
        with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)):
            result = _query_worker()
        self.assertEqual(result["tool_1"], "2")
        self.assertEqual(result["status"], "unloaded")
        self.assertEqual(device.commands, [b"FG\x03", b"\x1b\x05", TOOL_QUERY])

    def test_status_burst_only_reads_firmware_and_status(self):
        from contextlib import nullcontext
        class FakeDevice:
            def __init__(self):
                self.commands = []
            def exchange(self, command):
                self.commands.append(command)
                return (b"CAMEO 5 ALPHA V1.03\x03" if command == b"FG\x03"
                        else b"0\x03")
        device = FakeDevice()
        with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)), \
             patch("printnik.cameo_usb.time.sleep"):
            result = _status_burst_worker()
        self.assertEqual(result["status"], "read_only_complete")
        self.assertEqual(device.commands, [b"FG\x03"] + [b"\x1b\x05"] * 20)

    def test_firmware_must_identify_the_expected_plotter(self):
        self.assertEqual(parse_firmware(b"CAMEO 5 ALPHA V1.03    \x03"), "CAMEO 5 ALPHA V1.03")
        with self.assertRaises(CameoConnectionError):
            parse_firmware(b"OTHER DEVICE\x03")

    def test_status_codes_do_not_confuse_busy_or_unloaded_with_ready(self):
        self.assertEqual(parse_status(b"0\x03"), "ready")
        self.assertEqual(parse_status(b"1\x03"), "moving")
        self.assertEqual(parse_status(b"2\x03"), "unloaded")
        self.assertEqual(parse_status(b"9\x03"), "unknown")
        with self.assertRaises(CameoConnectionError):
            parse_status(b"0")

    def test_only_exact_four_corner_test_geometry_is_accepted(self):
        folder = Path(__file__).parent / "_work" / uuid.uuid4().hex
        folder.mkdir(parents=True)
        try:
            manifest = folder / "registration-test.json"
            data = {"status": "experimental_unverified", "cut_file": None,
                    "page_mm": [210, 297], "length_mm": 20,
                    "offsets_mm": {"left_mm": 10, "right_mm": 10,
                                   "top_mm": 10, "bottom_mm": 10},
                    "mark_origins_mm": [[10, 10], [200, 10], [10, 287], [200, 287]]}
            manifest.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(registration_geometry(manifest), (5540, 3800, 0, 0))
            data["offsets_mm"]["bottom_mm"] = 17
            data["mark_origins_mm"][2:] = [[10, 280], [200, 280]]
            manifest.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(registration_geometry(manifest), (5400, 3800, 0, 0))
            data["cut_file"] = "cut.svg"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CameoConnectionError):
                registration_geometry(manifest)
        finally:
            manifest.unlink(missing_ok=True)
            folder.rmdir()

    def test_scan_command_sequence_has_no_cut_or_blade_command(self):
        commands = registration_commands((5540, 3800, 0, 0))
        self.assertEqual(commands[-1], b"TB124,5540,3800,0,0\x03")
        self.assertEqual(registration_commands((5400, 3800, 0, 0))[-1],
                         b"TB124,5400,3800,0,0\x03")
        self.assertFalse(any(command.startswith((b"D", b"M", b"TF", b"FX", b"FO"))
                             for command in commands))
        with self.assertRaises(CameoConnectionError):
            registration_commands((5540, 3800, 0, 1))

    def test_scan_refuses_unloaded_media_before_motion(self):
        class FakeDevice:
            def __init__(self):
                self.writes = []
            def exchange(self, command):
                return b"CAMEO 5 ALPHA V1.03\x03" if command == b"FG\x03" else b"2\x03"
            def write(self, command):
                self.writes.append(command)

        from contextlib import nullcontext
        device = FakeDevice()
        with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)):
            with self.assertRaises(CameoConnectionError):
                _scan_worker((5540, 3800, 0, 0))
        self.assertEqual(device.writes, [])

    def test_registration_response_requires_complete_success_code(self):
        self.assertEqual(parse_registration_result(b"    0\x03"), "found")
        self.assertEqual(parse_registration_result(b"    1\x03"), "not_found")
        with self.assertRaises(CameoConnectionError):
            parse_registration_result(b"    0")

    def test_position_move_occurs_only_after_successful_mark_search(self):
        class FakeDevice:
            def __init__(self, registration_reply):
                self.registration_reply = registration_reply
                self.writes = []
            def exchange(self, command):
                return b"CAMEO 5 ALPHA V1.03\x03" if command == b"FG\x03" else b"0\x03"
            def write(self, command):
                self.writes.append(command)
            def read(self):
                return self.registration_reply

        from contextlib import nullcontext
        for reply, expected in ((b"    0\x03", "position_command_sent"),
                                (b"    10\x03", "not_found")):
            device = FakeDevice(reply)
            with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)):
                result = _position_worker((5240, 3800, 0, 0))
            self.assertEqual(result["status"], expected)
            self.assertEqual(CONTROL_LINE_MOVE in device.writes, expected == "position_command_sent")
            self.assertFalse(any(command.startswith((b"D", b"TF", b"FX", b"FO"))
                                 for command in device.writes))
        with self.assertRaises(CameoConnectionError):
            _position_worker((5340, 3800, 0, 0))

    def test_first_cut_never_draws_before_valid_tool_and_four_marks(self):
        from contextlib import nullcontext
        class FakeDevice:
            def __init__(self, tool_reply, mark_reply):
                self.tool_reply, self.mark_reply = tool_reply, mark_reply
                self.writes = []
            def exchange(self, command):
                return {b"FG\x03": b"CAMEO 5 ALPHA V1.03\x03",
                        b"\x1b\x05": b"0\x03", TOOL_QUERY: self.tool_reply}[command]
            def write(self, command):
                self.writes.append(command)
            def read(self):
                return self.mark_reply

        for tool_reply, mark_reply, expected in (
            (b"0,0\x03", b"    0\x03", "error"),
            (b"2,0\x03", b"    10\x03", "not_found"),
            (b"2,0\x03", b"    0\x03", "cut_device_ready"),
        ):
            device = FakeDevice(tool_reply, mark_reply)
            with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)), \
                 patch("printnik.cameo_usb.time.sleep"):
                if expected == "error":
                    with self.assertRaises(CameoConnectionError):
                        _first_cut_worker()
                else:
                    self.assertEqual(_first_cut_worker()["status"], expected)
            if expected == "cut_device_ready":
                self.assertEqual(device.writes[:len(FIRST_CUT_SETUP)], list(FIRST_CUT_SETUP))
                self.assertEqual([command for command in device.writes if command in FIRST_CUT_PATH],
                                 list(FIRST_CUT_PATH))
                self.assertEqual(sum(command.startswith(b"D") for command in device.writes), 4)
            else:
                self.assertFalse(any(command.startswith(b"D") for command in device.writes))

    def test_first_cut_manifest_rejects_changed_geometry(self):
        from printnik.calibration import create_first_cut_test_package
        path = Path(__file__).parent / "_work" / uuid.uuid4().hex
        path.mkdir(parents=True)
        try:
            create_first_cut_test_package(path)
            manifest = path / "first-cut.json"
            validate_first_cut_manifest(manifest)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["cut_path_mm"][1][0] = 63
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CameoConnectionError):
                validate_first_cut_manifest(manifest)
        finally:
            for name in ("first-cut.json", "registration-test.json", "first-cut-print.pdf",
                         "first-cut-preview.png"):
                (path / name).unlink(missing_ok=True)
            path.rmdir()

    def test_reduced_depth_trial_is_confined_to_new_square(self):
        from contextlib import nullcontext
        class FakeDevice:
            def __init__(self):
                self.writes = []
            def exchange(self, command):
                return {b"FG\x03": b"CAMEO 5 ALPHA V1.03\x03",
                        b"\x1b\x05": b"0\x03", TOOL_QUERY: b"2,0\x03"}[command]
            def write(self, command):
                self.writes.append(command)
            def read(self):
                return b"    0\x03"
        device = FakeDevice()
        with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)), \
             patch("printnik.cameo_usb.time.sleep"):
            self.assertEqual(_kiss_test_worker()["status"], "cut_device_ready")
        self.assertIn(b"FX4,1\x03", KISS_TEST_SETUP)
        self.assertIn(b"TF1,1\x03", KISS_TEST_SETUP)
        self.assertNotIn(b"FX10,1\x03", KISS_TEST_SETUP)
        self.assertNotIn(b"TF3,1\x03", KISS_TEST_SETUP)
        self.assertEqual([command for command in device.writes if command in KISS_TEST_PATH],
                         list(KISS_TEST_PATH))
        self.assertEqual(sum(command.startswith(b"D") for command in device.writes), 4)

    def test_second_trial_rejects_changed_pressure_or_position(self):
        import shutil
        source = Path(__file__).resolve().parents[1] / "experiments" / "first-cut-matte-25"
        path = Path(__file__).parent / "_work" / uuid.uuid4().hex
        path.mkdir(parents=True)
        names = ("first-cut.json", "first-cut-print.pdf", "first-cut-attempt.json",
                 "kiss-test-1.json")
        try:
            for name in names:
                shutil.copyfile(source / name, path / name)
            manifest = path / "kiss-test-1.json"
            validate_kiss_test_manifest(manifest)
            for key, value in (("blade", 3), ("target_box_mm", [50, 245, 60, 255])):
                data = json.loads(manifest.read_text(encoding="utf-8"))
                data[key] = value
                manifest.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(CameoConnectionError):
                    validate_kiss_test_manifest(manifest)
                shutil.copyfile(source / "kiss-test-1.json", manifest)
        finally:
            for name in names:
                (path / name).unlink(missing_ok=True)
            path.rmdir()

    def test_cat_trial_is_bound_to_exact_print_and_contour(self):
        import shutil
        source = Path(__file__).resolve().parents[1] / "experiments" / "direct-cat-matte-25"
        path = Path(__file__).parent / "_work" / uuid.uuid4().hex
        path.mkdir(parents=True)
        names = ("direct-cat-trial.json", "direct-cat-print.pdf", "direct-cat-cut.svg")
        try:
            for name in names:
                shutil.copyfile(source / name, path / name)
            manifest = path / names[0]
            commands = validate_direct_cat_manifest(manifest)
            self.assertEqual(len(commands), 344)
            self.assertEqual(sum(command.startswith(b"D") for command in commands), 342)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["force"] = 10
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CameoConnectionError):
                validate_direct_cat_manifest(manifest)
            shutil.copyfile(source / names[0], manifest)
            (path / names[2]).write_bytes((path / names[2]).read_bytes() + b" ")
            with self.assertRaises(CameoConnectionError):
                validate_direct_cat_manifest(manifest)
        finally:
            for name in names:
                (path / name).unlink(missing_ok=True)
            path.rmdir()

    def test_corrected_cat_trial_is_bound_to_its_own_print_and_contour(self):
        import shutil
        source = Path(__file__).resolve().parents[1] / "experiments" / "cat-gap-correction-matte-25"
        path = Path(__file__).parent / "_work" / uuid.uuid4().hex
        path.mkdir(parents=True)
        names = ("cat-gap-trial.json", "cat-gap-print.pdf", "cat-gap-cut.svg")
        try:
            for name in names:
                shutil.copyfile(source / name, path / name)
            manifest = path / names[0]
            commands = validate_direct_cat_manifest(manifest)
            self.assertEqual(len(commands), 400)
            self.assertEqual(sum(command.startswith(b"D") for command in commands), 398)
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["contour_offset_mm"]["head_gaps"] = "0.6"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CameoConnectionError):
                validate_direct_cat_manifest(manifest)
            shutil.copyfile(source / names[0], manifest)
            (path / names[1]).write_bytes((path / names[1]).read_bytes() + b" ")
            with self.assertRaises(CameoConnectionError):
                validate_direct_cat_manifest(manifest)
        finally:
            for name in names:
                (path / name).unlink(missing_ok=True)
            path.rmdir()

    def test_blade_check_requires_failed_cat_sheet_and_is_only_one_square(self):
        import shutil
        from contextlib import nullcontext
        source = Path(__file__).resolve().parents[1] / "experiments" / "cat-gap-correction-matte-25"
        path = Path(__file__).parent / "_work" / uuid.uuid4().hex
        path.mkdir(parents=True)
        names = ("cat-gap-blade-check.json", "cat-gap-print.pdf", "cat-gap-attempt.json")
        try:
            for name in names:
                shutil.copyfile(source / name, path / name)
            manifest = path / names[0]
            validate_blade_check_manifest(manifest)

            class FakeDevice:
                def __init__(self, marks):
                    self.marks, self.writes = marks, []
                def exchange(self, command):
                    return {b"FG\x03": b"CAMEO 5 ALPHA V1.03\x03",
                            b"\x1b\x05": b"0\x03", TOOL_QUERY: b"2,0\x03"}[command]
                def write(self, command):
                    self.writes.append(command)
                def read(self):
                    return self.marks

            for marks, expected_cuts in ((b"    10\x03", 0), (b"    0\x03", 4)):
                device = FakeDevice(marks)
                with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)), \
                     patch("printnik.cameo_usb.time.sleep"):
                    _blade_check_worker(manifest)
                self.assertEqual(sum(command.startswith(b"D") for command in device.writes),
                                 expected_cuts)

            data = json.loads((path / names[2]).read_text(encoding="utf-8"))
            data["physical_result"] = "sticker_cut"
            (path / names[2]).write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CameoConnectionError):
                validate_blade_check_manifest(manifest)
        finally:
            for name in names:
                (path / name).unlink(missing_ok=True)
            path.rmdir()

    def test_cat_retry_requires_failed_first_cut_and_successful_blade_check(self):
        import shutil
        source = Path(__file__).resolve().parents[1] / "experiments" / "cat-gap-correction-matte-25"
        path = Path(__file__).parent / "_work" / uuid.uuid4().hex
        path.mkdir(parents=True)
        names = ("cat-gap-retry.json", "cat-gap-trial.json", "cat-gap-print.pdf",
                 "cat-gap-cut.svg", "cat-gap-attempt.json", "cat-gap-blade-check-attempt.json")
        try:
            for name in names:
                shutil.copyfile(source / name, path / name)
            manifest = path / names[0]
            self.assertEqual(len(validate_direct_cat_manifest(manifest)), 400)
            blade_record = path / names[-1]
            data = json.loads(blade_record.read_text(encoding="utf-8"))
            data["physical_result"] = "backing_cut"
            blade_record.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CameoConnectionError):
                validate_direct_cat_manifest(manifest)
        finally:
            for name in names:
                (path / name).unlink(missing_ok=True)
            path.rmdir()

    def test_cat_trial_only_cuts_after_valid_tool_and_marks(self):
        from contextlib import nullcontext
        source = Path(__file__).resolve().parents[1] / "experiments" / "direct-cat-matte-25"
        manifest = source / "direct-cat-trial.json"

        class FakeDevice:
            def __init__(self, tool, marks):
                self.tool, self.marks, self.writes, self.events, self.batches = tool, marks, [], [], []
            def exchange(self, command):
                self.events.append(command)
                return {b"FG\x03": b"CAMEO 5 ALPHA V1.03\x03",
                        b"\x1b\x05": b"0\x03", TOOL_QUERY: self.tool}[command]
            def write(self, command):
                self.writes.append(command)
                self.events.append(command)
            def write_batch(self, commands, allowed):
                self.asserted_allowed = allowed
                self.batches.append(tuple(commands))
                self.events.append(b"".join(commands))
            def read(self):
                return self.marks

        for tool, marks, outcome in ((b"0,0\x03", b"    0\x03", "error"),
                                     (b"2,0\x03", b"    10\x03", "not_found"),
                                     (b"2,0\x03", b"    0\x03", "cut_device_ready")):
            device = FakeDevice(tool, marks)
            with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)), \
                 patch("printnik.cameo_usb.time.sleep"):
                if outcome == "error":
                    with self.assertRaises(CameoConnectionError):
                        _direct_cat_worker(manifest)
                else:
                    self.assertEqual(_direct_cat_worker(manifest)["status"], outcome)
            self.assertEqual(sum(c.startswith(b"D") for batch in device.batches for c in batch),
                             342 if outcome == "cut_device_ready" else 0)
            if outcome == "cut_device_ready":
                expected = validate_direct_cat_manifest(manifest)
                self.assertEqual(tuple(command for batch in device.batches for command in batch), expected)
                self.assertEqual(tuple(device.batches), packetize_cut_path(expected))
                self.assertTrue(all(sum(map(len, batch)) <= 750 for batch in device.batches))
                first_batch = next(i for i, command in enumerate(device.events)
                                   if command.startswith(b"M"))
                last_batch = max(i for i, command in enumerate(device.events)
                                 if command.startswith((b"M", b"D")))
                self.assertEqual(sum(command == b"\x1b\x05"
                                     for command in device.events[first_batch:last_batch + 1]), 0)

    def test_batched_cat_trial_requires_exact_new_sheet_files(self):
        import shutil
        source = Path(__file__).resolve().parents[1] / "experiments" / "cat-batched-matte-25"
        path = Path(__file__).parent / "_work" / uuid.uuid4().hex
        path.mkdir(parents=True)
        names = ("cat-gap-batch-trial.json", "cat-gap-print.pdf", "cat-gap-cut.svg")
        try:
            for name in names:
                shutil.copyfile(source / name, path / name)
            manifest = path / names[0]
            commands = validate_direct_cat_manifest(manifest)
            self.assertEqual(len(commands), 400)
            self.assertEqual([sum(map(len, packet)) for packet in packetize_cut_path(commands)],
                             [748, 748, 748, 748, 748, 660])
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["force"] = 10
            manifest.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CameoConnectionError):
                validate_direct_cat_manifest(manifest)
        finally:
            for name in names:
                (path / name).unlink(missing_ok=True)
            path.rmdir()

    def test_smooth_cat_trial_uses_physically_verified_path(self):
        import shutil
        source = Path(__file__).resolve().parents[1] / "experiments" / "cat-smooth-matte-25"
        path = Path(__file__).parent / "_work" / uuid.uuid4().hex
        path.mkdir(parents=True)
        names = ("cat-smooth-trial.json", "cat-gap-print.pdf", "cat-smooth-cut.svg")
        try:
            for name in names:
                shutil.copyfile(source / name, path / name)
            commands = validate_direct_cat_manifest(path / names[0])
            self.assertEqual(len(commands), 323)
            self.assertEqual([sum(map(len, packet)) for packet in packetize_cut_path(commands)],
                             [748, 748, 748, 748, 561])
            self.assertEqual(commands[0], commands[-1])
            data = json.loads((path / names[0]).read_text(encoding="utf-8"))
            data["simplification_max_deviation_mm"] = 0.2
            (path / names[0]).write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CameoConnectionError):
                validate_direct_cat_manifest(path / names[0])
        finally:
            for name in names:
                (path / name).unlink(missing_ok=True)
            path.rmdir()

    def test_tool_up_motion_uses_only_m_after_marks(self):
        from contextlib import nullcontext
        source = Path(__file__).resolve().parents[1] / "experiments" / "direct-cat-matte-25"
        manifest = source / "direct-cat-trial.json"

        class FakeDevice:
            def __init__(self, mark_reply):
                self.mark_reply, self.writes = mark_reply, []
            def exchange(self, command):
                return (b"CAMEO 5 ALPHA V1.03\x03" if command == b"FG\x03"
                        else b"0\x03")
            def write(self, command):
                self.writes.append(command)
            def read(self):
                return self.mark_reply

        for reply, status in ((b"    10\x03", "not_found"),
                              (b"    0\x03", "motion_device_ready")):
            device = FakeDevice(reply)
            with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)), \
                 patch("printnik.cameo_usb.time.sleep"):
                self.assertEqual(_tool_up_motion_worker(manifest)["status"], status)
            self.assertFalse(any(command.startswith((b"D", b"TF", b"FX"))
                                 for command in device.writes))
            self.assertEqual(sum(command.startswith(b"M") for command in device.writes),
                             86 if status == "motion_device_ready" else 0)

    def test_smooth_tool_up_motion_does_not_poll_between_moves(self):
        from contextlib import nullcontext
        source = Path(__file__).resolve().parents[1] / "experiments" / "direct-cat-matte-25"
        manifest = source / "direct-cat-trial.json"

        class FakeDevice:
            def __init__(self):
                self.events = []
            def exchange(self, command):
                self.events.append(command)
                return b"CAMEO 5 ALPHA V1.03\x03" if command == b"FG\x03" else b"0\x03"
            def write(self, command):
                self.events.append(command)
            def read(self):
                return b"    0\x03"

        device = FakeDevice()
        with patch("printnik.cameo_usb._connection", return_value=nullcontext(device)), \
             patch("printnik.cameo_usb.time.sleep"):
            result = _tool_up_motion_worker(manifest, interleaved_status=False)
        self.assertEqual(result["status"], "motion_device_ready")
        move_indices = [i for i, event in enumerate(device.events) if event.startswith(b"M")]
        self.assertEqual(len(move_indices), 87)
        self.assertEqual(device.events[move_indices[-1]], CONTROL_LINE_MOVE)
        self.assertTrue(all(event.startswith(b"M") for event in
                            device.events[move_indices[0]:move_indices[-1] + 1]))
        self.assertFalse(any(event.startswith((b"D", b"TF", b"FX"))
                             for event in device.events))


if __name__ == "__main__":
    unittest.main()
