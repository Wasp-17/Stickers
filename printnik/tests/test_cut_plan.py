import json
import unittest
import uuid
from pathlib import Path

from printnik.cut_plan import CutPlanError, plan_svg, write_order_cut_plans


def svg(path: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="210mm" '
            'height="297mm" viewBox="0 0 210 297">'
            f'<path d="{path}"/></svg>')


class CutPlanTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(__file__).parent / "_work" / uuid.uuid4().hex
        self.folder.mkdir(parents=True)

    def test_closed_contour_produces_move_and_cut_draft(self):
        source = self.folder / "sheet-01-cut.svg"
        source.write_text(svg("M 10 20 L 11 20 L 11 21 L 10 20 Z"), encoding="utf-8")
        plan = plan_svg(source)
        self.assertEqual(plan["status"], "UNVERIFIED_OFFLINE_ONLY")
        self.assertEqual(plan["registration_transform"], "NOT_CALIBRATED")
        self.assertEqual(plan["contours"][0]["draft_moves"],
                         ["M 200,400", "D 220,400", "D 220,420", "D 200,400"])

    def test_rejects_unsupported_or_out_of_sheet_paths(self):
        source = self.folder / "sheet-01-cut.svg"
        for path in ("M 10 20 C 11 20 11 21 10 21 Z",
                     "M 10 20 L 211 20 L 10 21 Z",
                     "M 10 20 L 11 20 L 10 21"):
            source.write_text(svg(path), encoding="utf-8")
            with self.assertRaises(CutPlanError):
                plan_svg(source)

    def test_requires_review_and_writes_only_after_all_sheets_validate(self):
        folder = self.folder
        first = folder / "sheet-01-cut.svg"
        second = folder / "sheet-02-cut.svg"
        first.write_text(svg("M 10 20 L 11 20 L 10 21 Z"), encoding="utf-8")
        second.write_text(svg("M 10 20 L 211 20 L 10 21 Z"), encoding="utf-8")
        report = {"contour_review_approved": False, "cut_files": [str(first), str(second)]}
        job = folder / "job.json"
        job.write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaises(CutPlanError):
            write_order_cut_plans(folder)
        report["contour_review_approved"] = True
        job.write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaises(CutPlanError):
            write_order_cut_plans(folder)
        self.assertFalse((folder / "sheet-01-direct-cut-plan-UNVERIFIED.json").exists())
        second.write_text(svg("M 12 20 L 13 20 L 12 21 Z"), encoding="utf-8")
        paths = write_order_cut_plans(folder)
        self.assertEqual(len(paths), 2)
        self.assertEqual(json.loads(paths[0].read_text(encoding="utf-8"))["source_svg"], first.name)


if __name__ == "__main__":
    unittest.main()
