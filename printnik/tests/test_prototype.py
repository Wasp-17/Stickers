import unittest
import uuid
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from printnik.prototype import cut_mask_for_size, fill_internal_holes, largest_component, needs_small_contour_review, prepare, remove_exterior_white


class PrototypeTests(unittest.TestCase):
    def test_standard_cut_profile_keeps_one_filled_physical_sticker(self):
        mask = np.zeros((20, 20), dtype=bool)
        mask[2:15, 2:15] = True
        mask[6:9, 6:9] = False
        mask[18, 18] = True
        result = fill_internal_holes(largest_component(mask))
        self.assertTrue(result[7, 7])
        self.assertFalse(result[18, 18])

    def test_size_a_and_b_keep_visible_hole(self):
        mask = np.zeros((120, 120), dtype=bool)
        mask[5:115, 5:115] = True
        mask[45:75, 45:75] = False
        self.assertFalse(cut_mask_for_size(mask, "A", 100)[60, 60])
        self.assertFalse(cut_mask_for_size(mask, "B", 100)[60, 60])

    def test_size_a_outlines_thin_drips_instead_of_tracing_them(self):
        mask = np.zeros((80, 80), dtype=bool)
        mask[15:65, 15:65] = True
        mask[65:75, 38:40] = True  # fragile thin drip
        cut_a = cut_mask_for_size(mask, "A", 100, safe_a=True)
        cut_b = cut_mask_for_size(mask, "B", 100)
        self.assertTrue(cut_a[40, 40])
        self.assertFalse(cut_a[70, 38])
        self.assertTrue(cut_b[70, 38])
        self.assertTrue(needs_small_contour_review(mask, 100))

    def test_size_b_keeps_meaningful_detached_piece_but_ignores_dust(self):
        mask = np.zeros((150, 150), dtype=bool)
        mask[10:100, 10:100] = True
        mask[110:125, 110:125] = True
        mask[140, 140] = True
        result = cut_mask_for_size(mask, "B", 100)
        self.assertTrue(result[115, 115])
        self.assertFalse(result[140, 140])

    def test_size_a_detached_piece_requires_review(self):
        mask = np.zeros((150, 150), dtype=bool)
        mask[10:100, 10:100] = True
        mask[110:125, 110:125] = True
        self.assertTrue(needs_small_contour_review(mask, 100))
        self.assertFalse(cut_mask_for_size(mask, "A", 100, safe_a=True)[115, 115])

    def test_external_white_is_removed_but_internal_white_survives(self):
        image = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((5, 5, 74, 74), fill="white")
        draw.ellipse((12, 12, 67, 67), fill="red")
        draw.ellipse((30, 30, 49, 49), fill="white")
        cleaned, _ = remove_exterior_white(image)
        data = np.array(cleaned)
        self.assertEqual(data[7, 40, 3], 0)
        self.assertEqual(data[40, 40, 3], 255)

    def test_prepare_writes_package_without_modifying_source(self):
        root = Path(__file__).parent / "_work" / uuid.uuid4().hex
        root.mkdir(parents=True)
        source = root / "source.png"
        image = Image.new("RGBA", (40, 30), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle((5, 5, 34, 24), fill="blue")
        image.save(source)
        before = source.read_bytes()
        result = prepare(source, root / "out", "TEST-1", "A", 100, 0.75)
        self.assertEqual(before, source.read_bytes())
        self.assertEqual(result["status"], "candidate_requires_approval")
        for name in ("cleaned.png", "print_with_bleed.png", "cut.svg", "comparison.png", "manifest.json"):
            self.assertTrue((root / "out" / name).exists())
            with Image.open(root / "out" / "print_with_bleed.png") as printed:
                self.assertEqual(result["canvas_px"], {"width": printed.width, "height": printed.height})


if __name__ == "__main__":
    unittest.main()
