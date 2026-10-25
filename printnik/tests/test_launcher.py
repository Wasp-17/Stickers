import json
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


class LauncherTests(unittest.TestCase):
    def test_blade_check_worker_flag_is_routed_without_opening_app(self):
        root = Path(__file__).resolve().parents[1]
        folder = root / "tests" / "_work" / uuid.uuid4().hex
        folder.mkdir(parents=True)
        try:
            result = folder / "worker-result.json"
            missing_manifest = folder / "missing-blade-check.json"
            completed = subprocess.run(
                [sys.executable, str(root / "printnik_launcher.py"),
                 "--cameo-blade-check-worker",
                 f"--cameo-trial-manifest={missing_manifest}",
                 f"--cameo-probe-result={result}"],
                cwd=root, capture_output=True, timeout=10, check=False,
            )
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(result.read_text(encoding="utf-8"))
            self.assertIn("error", payload)
        finally:
            result.unlink(missing_ok=True)
            folder.rmdir()


if __name__ == "__main__":
    unittest.main()
