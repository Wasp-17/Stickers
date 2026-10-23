import os
import traceback
from pathlib import Path

from printnik.app import main


if __name__ == "__main__":
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
