import json
import unittest
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

from printnik.catalog import AssetCatalog
from printnik.calibration import create_calibration_package
from printnik.envelopes import create_envelopes_pdf
from printnik.dxf import bounds, render_dxf
from printnik.importer import import_payload
from printnik.materials import MaterialProfile
from printnik.models import Order, OrderItem, OrderStatus
from printnik.production import PreflightError, preflight, render_order
from printnik.size_rules import load_size_rules, validate_size_rule
from printnik.storage import OrderStore


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parent / "_work" / uuid.uuid4().hex
        self.root.mkdir(parents=True)

    def test_order_survives_store_reopen(self):
        db = self.root / "queue.db"
        store = OrderStore(db)
        order = Order("RK-2026-000001", "matte_white", items=[OrderItem("RK17-0105", "B", 2)])
        store.save(order)
        store.set_status(order.order_id, OrderStatus.READY_TO_PRINT)
        store.close()
        reopened = OrderStore(db)
        saved = reopened.get(order.order_id)
        reopened.close()
        self.assertEqual(saved.status, OrderStatus.READY_TO_PRINT)
        self.assertEqual(saved.items[0].quantity, 2)

    def test_opaque_asset_requires_explicit_rectangular_cut(self):
        source = self.root / "RK17-9998-ART.png"
        Image.new("RGB", (300, 300), "white").save(source)
        result = preflight(source, "RK17-9998", "B")
        self.assertTrue(result.errors)
        allowed = preflight(source, "RK17-9998", "B", allow_opaque=True)
        self.assertFalse(allowed.errors)

    def test_catalog_uses_only_production_files_and_prefers_master(self):
        assets = self.root / "assets"
        assets.mkdir()
        for name in ("RK17-9999_WEB.webp", "RK17-9999_ART.png", "RK17-9999_MASTER.png",
                     "RK17-9998_WEB.webp"):
            Image.new("RGBA", (30, 30), (0, 0, 0, 0)).save(assets / name)
        catalog = AssetCatalog([assets])
        self.assertTrue(catalog.resolve("RK17-9999").name.endswith("MASTER.png"))
        with self.assertRaisesRegex(FileNotFoundError, "MASTER/ART"):
            catalog.resolve("RK17-9998")

    def test_a1_size_policy_is_checked_before_production(self):
        rules = {"RK17-9999": {"a_policy": "min_a1", "reason": "Тонкие выступы"}}
        with self.assertRaisesRegex(ValueError, "минимальный размер A1"):
            validate_size_rule("RK17-9999", "A", rules)
        self.assertIsNone(validate_size_rule("RK17-9999", "A1", rules))
        self.assertIn("рекомендуем A1", validate_size_rule("RK17-9999", "A",
                      {"RK17-9999": {"a_policy": "recommend_a1", "reason": "Тонкие выступы"}}))
        project = Path(__file__).resolve().parents[2]
        self.assertEqual(load_size_rules(project / "catalog-data" / "cut_size_rules.json"),
                         load_size_rules(project / "printnik" / "config" / "cut_size_rules.json"))

    def test_dxf_contains_closed_contours_and_reference_bounds(self):
        paths = [(100.0, "M 10 20 L 60 20 L 60 40 L 10 40 Z", 140.0)]
        drawing = render_dxf(paths)
        self.assertIn("LWPOLYLINE\n100\nAcDbEntity", drawing)
        self.assertIn("90\n4\n70\n1", drawing)
        self.assertIn("10\n10.000\n20\n277.000", drawing)
        self.assertEqual(bounds(paths), {"left": 10.0, "top": 20.0, "width": 50.0, "height": 20.0})

    def test_render_order_creates_persistent_print_and_cut_package(self):
        assets = self.root / "assets"
        assets.mkdir()
        source = assets / "RK17-9999-ART.png"
        image = Image.new("RGBA", (220, 180), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((10, 10, 210, 170), fill="red")
        draw.ellipse((90, 65, 130, 105), fill=(0, 0, 0, 0))
        image.save(source)
        material = MaterialProfile("matte_white", "Матовая", "Вверх", "Epson Matte", "Высокий", 3, 10, 4, 1, 2.2, 1.5, True)
        order = Order("RK-TEST-1", "matte_white", items=[OrderItem("RK17-9999", "B", 2)])
        result = render_order(order, AssetCatalog([assets]), material, self.root / "jobs", dpi=100)
        self.assertEqual(result["sheet_count"], 1)
        self.assertTrue(Path(result["print_pdf"]).exists())
        self.assertTrue(Path(result["cut_files"][0]).exists())
        self.assertTrue(Path(result["cut_dxf_files"][0]).exists())
        self.assertIn("LWPOLYLINE", Path(result["cut_dxf_files"][0]).read_text(encoding="ascii"))
        self.assertTrue(Path(result["sheet_previews"][0]).exists())
        self.assertFalse(result["contour_review_approved"])
        self.assertGreater(result["cut_bounds_mm"][0]["width"], 0)
        payload = json.loads((self.root / "jobs" / order.order_id / "job.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["cut_settings"]["force"], 10)
        self.assertEqual(len(payload["cut_length_mm_per_sheet"]), 1)
        self.assertGreater(payload["cut_length_mm_per_sheet"][0], 0)
        self.assertAlmostEqual(payload["planned_cut_length_mm"], payload["cut_length_mm_per_sheet"][0])

    def test_blade_counter_tracks_confirmed_partial_repeat_and_replacement(self):
        store = OrderStore(self.root / "blades.db")
        store.save(Order("RK-TEST-BLADE", "glossy_white"))
        first = store.ensure_blade("CUT-01")
        self.assertEqual(first["length_mm"], 0)
        self.assertEqual(first["baseline_known"], 0)
        store.record_cut("RK-TEST-BLADE", 1, "CUT-01", "glossy_white", 1200,
                         completed=False)
        store.record_cut("RK-TEST-BLADE", 1, "CUT-01", "glossy_white", 3000,
                         completed=True)
        self.assertEqual(store.completed_cut_sheets("RK-TEST-BLADE"), {1})
        with self.assertRaisesRegex(ValueError, "уже учтён"):
            store.record_cut("RK-TEST-BLADE", 1, "CUT-01", "glossy_white", 3000,
                             completed=True)
        store.record_cut("RK-TEST-BLADE", 1, "CUT-01", "glossy_white", 3000,
                         completed=True, repeat=True)
        self.assertEqual(store.active_blade("CUT-01")["length_mm"], 7200)
        second = store.replace_blade("CUT-01", "worn")
        self.assertNotEqual(first["blade_id"], second["blade_id"])
        self.assertEqual(second["length_mm"], 0)
        self.assertEqual(second["baseline_known"], 1)
        store.close()
        reopened = OrderStore(self.root / "blades.db")
        history = reopened.blade_history("CUT-01")
        self.assertEqual(history[1]["total_mm"], 7200)
        self.assertEqual(history[1]["retirement_reason"], "worn")
        reopened.close()

    def test_complex_a_requires_visible_contour_approval(self):
        assets = self.root / "complex-a"
        assets.mkdir()
        source = assets / "RK17-9997-ART.png"
        image = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((35, 30, 165, 140), fill="blue")
        draw.rectangle((80, 140, 83, 185), fill="blue")
        image.save(source)
        material = MaterialProfile("glossy_white", "Глянцевая", "Вверх", "Глянцевая", "Стандартный",
                                   4, 12, 4, 1, 2.2, 1.5, True)
        order = Order("RK-TEST-COMPLEX-A", "glossy_white", items=[OrderItem("RK17-9997", "A", 1)])
        report = render_order(order, AssetCatalog([assets]), material, self.root / "jobs", dpi=100)
        self.assertEqual(report["status"], "needs_contour_review")
        self.assertFalse(report["contour_review_approved"])
        self.assertEqual(len(report["contour_previews"]), 1)
        self.assertTrue(Path(report["contour_previews"][0]).exists())

    def test_duplicate_import_does_not_create_second_order(self):
        store = OrderStore(self.root / "imports.db")
        payload = {"order_id": "RK-2026-77", "items": [{"asset_id": "RK17-9999", "size": "B", "quantity": 1}]}
        _, first = import_payload(store, payload, "test")
        _, second = import_payload(store, payload, "test-again")
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(len(store.list_orders()), 1)
        store.close()

    def test_envelope_pdf_contains_orders_with_address(self):
        order = Order("RK-2026-88", "matte_white", address={"recipient": "Иван Иванов", "postal_code": "123456", "address": "Москва, улица Тестовая, дом 1"})
        path = create_envelopes_pdf([order], self.root / "envelopes.pdf", dpi=100)
        self.assertTrue(path.exists())
        self.assertGreater(path.stat().st_size, 1000)

    def test_calibration_package_has_print_and_cut_files(self):
        result = create_calibration_package(self.root / "calibration", dpi=100)
        self.assertTrue(Path(result["print_pdf"]).exists())
        self.assertTrue(Path(result["cut_svg"]).exists())
        self.assertEqual(result["registration_inset_mm"], 10)
        svg = Path(result["cut_svg"]).read_text(encoding="utf-8")
        self.assertIn('width="40" height="36"', svg)


if __name__ == "__main__":
    unittest.main()
