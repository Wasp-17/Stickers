from pathlib import Path
import unittest

from printnik.production import prepare_sticker
from printnik.prototype import trace_loops


class FirefighterContourTests(unittest.TestCase):
    def test_opaque_white_gap_and_collar_are_cut_at_order_size(self):
        source = (Path(__file__).resolve().parents[2] / "production" /
                  "RK17-0105_0132_READY" / "MASTER" / "RK17-0132_MASTER.png")
        sticker = prepare_sticker(source, "RK17-0132", "C")
        self.assertFalse(sticker.cut_mask[280, 55])  # extinguisher/hose cavity
        self.assertFalse(sticker.cut_mask[290, 380])  # collar notch on viewer's right
        self.assertTrue(sticker.cut_mask[215, 195])   # other collar side unchanged
        self.assertTrue(sticker.cut_mask[300, 100])   # extinguisher still intact
        loops = trace_loops(sticker.cut_mask)
        self.assertEqual(len(loops), 2)
        self.assertTrue(any(min(x for x, _ in loop) <= 35 and
                            max(x for x, _ in loop) <= 76 and
                            min(y for _, y in loop) >= 245 and
                            max(y for _, y in loop) <= 335 for loop in loops))


if __name__ == "__main__":
    unittest.main()
