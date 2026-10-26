from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
PAYLOAD = RESOURCE_DIR / "payload" / "Printnik.exe"
if not PAYLOAD.exists() and not getattr(sys, "frozen", False):
    PAYLOAD = RESOURCE_DIR / "dist" / "Printnik.exe"
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / "Printnik"
TARGET = INSTALL_DIR / "Printnik.exe"


def create_shortcut(link: Path, target: Path):
    link.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "$w=New-Object -ComObject WScript.Shell;"
        f"$s=$w.CreateShortcut('{str(link).replace("'", "''")}');"
        f"$s.TargetPath='{str(target).replace("'", "''")}';"
        f"$s.WorkingDirectory='{str(target.parent).replace("'", "''")}';"
        "$s.Description='Локальная производственная программа Печатник';$s.Save()"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], check=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def install():
    if not PAYLOAD.exists():
        raise FileNotFoundError("В установщике отсутствует Printnik.exe")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PAYLOAD, TARGET)
    desktop = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop" / "Печатник.lnk"
    start_menu = Path(os.environ.get("APPDATA", Path.home())) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Печатник.lnk"
    create_shortcut(desktop, TARGET)
    create_shortcut(start_menu, TARGET)


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Установка Печатника")
        self.geometry("560x300")
        self.resizable(False, False)
        body = ttk.Frame(self, padding=28)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Печатник", font=("Segoe UI Semibold", 24)).pack(anchor="w")
        ttk.Label(body, text="Локальная программа подготовки, печати и контурной резки заказов.", wraplength=490).pack(anchor="w", pady=(8, 20))
        ttk.Label(body, text=f"Папка установки:\n{INSTALL_DIR}", wraplength=490).pack(anchor="w")
        self.status = ttk.Label(body, text="")
        self.status.pack(anchor="w", pady=14)
        ttk.Button(body, text="Установить или восстановить", command=self.run_install).pack(anchor="e")

    def run_install(self):
        try:
            self.status.configure(text="Установка…")
            self.update_idletasks()
            install()
            self.status.configure(text="Готово")
            if messagebox.askyesno("Печатник установлен", "Ярлык создан на рабочем столе. Запустить Печатник сейчас?"):
                subprocess.Popen([str(TARGET)])
            self.destroy()
        except Exception as exc:
            self.status.configure(text="Ошибка")
            messagebox.showerror("Установка не завершена", str(exc))


if __name__ == "__main__":
    Installer().mainloop()
