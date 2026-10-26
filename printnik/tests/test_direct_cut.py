import hashlib
import json
import unittest
import uuid
from pathlib import Path

from printnik.cameo_usb import packetize_cut_path
from printnik.cut_plan import CutPlanError
from printnik.direct_cut import (VERIFIED_REGISTRATION, VERIFIED_SETTINGS,
                                 approved_file_hashes, compile_svg_commands,
                                 prepare_direct_sheet)


def square_svg(x=40, y=50):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" '
            f'height="297mm" viewBox="0 0 210 297">'
            f'<path d="M {x} {y} L {x+10} {y} L {x+10} {y+10} Z"/></svg>')


class DirectCutPlanTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(__file__).parent / "_work" / uuid.uuid4().hex
        self.folder.mkdir(parents=True)
        self.svg = self.folder / "sheet-01-cut.svg"
        self.svg.write_text(square_svg(), encoding="utf-8")
        self.pdf = self.folder / "TEST-print.pdf"
        self.pdf.write_bytes(b"test PDF identity")
        self.preview = self.folder / "sheet-01-review.png"
        self.preview.write_bytes(b"reviewed image identity")
        self.job = self.folder / "job.json"
        self.report = {
            "order_id": "TEST", "material_id": "matte_white", "sheet_count": 1,
            "print_pdf": str(self.pdf), "cut_files": [str(self.svg)],
            "sheet_previews": [str(self.preview)],
            "contour_review_approved": True,
            "cut_settings": VERIFIED_SETTINGS,
            "registration_profile": VERIFIED_REGISTRATION,
        }
        self.report["approved_files_sha256"] = approved_file_hashes(self.folder, self.report)
        self._save()

    def tearDown(self):
        for path in (self.job, self.svg, self.pdf, self.preview):
            path.unlink(missing_ok=True)
        self.folder.rmdir()

    def _save(self):
        self.job.write_text(json.dumps(self.report), encoding="utf-8")

    def test_verified_coordinate_mapping_and_file_identity(self):
        preview = prepare_direct_sheet(self.folder, 1)
        self.assertEqual(preview.contour_count, 1)
        self.assertEqual(preview.commands,
                         (b"M800,600\x03", b"D800,800\x03", b"D1000,800\x03",
                          b"D800,600\x03", b"M800,600\x03"))
        self.assertEqual(preview.print_sha256, hashlib.sha256(self.pdf.read_bytes()).hexdigest())
        self.assertEqual(preview.cut_sha256, hashlib.sha256(self.svg.read_bytes()).hexdigest())

    def test_unapproved_or_wrong_material_settings_cannot_form_preview(self):
        for field, value in (("contour_review_approved", False),
                             ("material_id", "glossy_white"),
                             ("cut_settings", {"blade": 3, "force": 10, "speed": 4, "passes": 1}),
                             ("registration_profile", {**VERIFIED_REGISTRATION, "bottom_mm": 20})):
            original = self.report[field]
            self.report[field] = value
            self._save()
            with self.assertRaises(CutPlanError):
                prepare_direct_sheet(self.folder, 1)
            self.report[field] = original
        self._save()

    def test_rejects_wrong_sheet_and_unsafe_geometry(self):
        with self.assertRaises(CutPlanError):
            prepare_direct_sheet(self.folder, 2)
        self.svg.write_text(square_svg(5, 50), encoding="utf-8")
        with self.assertRaises(CutPlanError):
            prepare_direct_sheet(self.folder, 1)

    def test_rejects_files_changed_after_approval(self):
        self.preview.write_bytes(b"changed preview")
        with self.assertRaises(CutPlanError):
            prepare_direct_sheet(self.folder, 1)

    @unittest.skipUnless(
        (Path(__file__).resolve().parents[1] / "experiments" / "mixed-sheet-pilot" /
         "PILOT-MIXED-20261025" / "sheet-01-cut.svg").exists(),
        "Private pilot sheet is absent from the public checkout",
    )
    def test_exact_stream_of_physically_verified_eight_cut_pilot(self):
        svg = (Path(__file__).resolve().parents[1] / "experiments" /
               "mixed-sheet-pilot" / "PILOT-MIXED-20261025" / "sheet-01-cut.svg")
        commands = compile_svg_commands(svg)
        packets = packetize_cut_path(commands)
        self.assertEqual(len(commands), 2809)
        self.assertEqual(sum(map(len, commands)), 28808)
        self.assertEqual(len(packets), 39)
        self.assertEqual(sum(map(len, packets[-1])), 410)
        self.assertEqual(hashlib.sha256(b"".join(commands)).hexdigest(),
                         "50e8b6892991381f8ae82303f3d88423d51a955c68b5f6ac1c4c3ada58e9ceea")


if __name__ == "__main__":
    unittest.main()
