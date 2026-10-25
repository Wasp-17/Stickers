import os
import sys
import traceback
from pathlib import Path

from printnik.app import main


if __name__ == "__main__":
    if any(flag in sys.argv for flag in ("--cameo-probe-worker", "--cameo-scan-worker",
                                       "--cameo-position-worker", "--cameo-kiss-test-worker",
                                       "--cameo-blade-check-worker",
                                       "--cameo-direct-cat-worker", "--cameo-status-burst-worker",
                                       "--cameo-tool-up-motion-worker", "--cameo-tool-up-smooth-worker")):
        from printnik.cameo_usb import main as cameo_probe_main
        raise SystemExit(cameo_probe_main())
    try:
        main()
    except Exception:
        folder = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Printnik"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "startup-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        try:
            from tkinter import messagebox
            messagebox.showerror("Печатник не запустился", f"Диагностика сохранена в:\n{folder / 'startup-error.log'}")
        except Exception:
            pass
        raise
