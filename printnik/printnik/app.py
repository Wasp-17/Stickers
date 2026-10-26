from __future__ import annotations

import json
import os
import sys
import threading
import traceback
import tkinter as tk
import winsound
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .catalog import AssetCatalog
from .calibration import create_calibration_package, create_registration_test_package
from .cameo_usb import (CameoConnectionError, position_over_control_line, probe_cameo,
                        probe_tool_up_smooth,
                        registration_geometry, run_kiss_test, scan_registration_marks,
                        validate_kiss_test_manifest, run_blade_check,
                        validate_blade_check_manifest, run_direct_cat_trial,
                        validate_direct_cat_manifest, run_direct_order_sheet)
from .cut_plan import CutPlanError, write_order_cut_plans
from .direct_cut import approved_file_hashes, prepare_direct_sheet
from .devices import open_folder, open_silhouette_bridge, send_pdf_to_printer
from .equipment import Device, DeviceKind, DeviceStatus, EquipmentScheduler
from .envelopes import create_envelopes_pdf
from .importer import import_payload, scan_inbox
from .materials import load_materials
from .models import Order, OrderItem, OrderStatus, STATUS_LABELS
from .production import PreflightError, render_order
from .registry import DeviceRegistry
from .prototype import SIZES_MM
from .size_rules import load_size_rules
from .storage import OrderStore


RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Printnik"
    OUTPUT_DIR = Path.home() / "Documents" / "Printnik" / "Jobs"
else:
    DATA_DIR = RESOURCE_DIR / "data"
    OUTPUT_DIR = RESOURCE_DIR / "jobs"
CONFIG_DIR = RESOURCE_DIR / "config"
WORKSPACE_DIR = RESOURCE_DIR.parent


class NewOrderDialog(tk.Toplevel):
    def __init__(self, parent, order_id: str, material_names: dict[str, str], asset_ids: list[str]):
        super().__init__(parent)
        self.title("Новый ручной заказ")
        self.geometry("720x520")
        self.transient(parent)
        self.grab_set()
        self.result = None
        self.material_names = material_names
        self.asset_ids = asset_ids

        form = ttk.Frame(self, padding=16)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="Номер заказа").grid(row=0, column=0, sticky="w")
        self.order_id = tk.StringVar(value=order_id)
        ttk.Entry(form, textvariable=self.order_id, width=28).grid(row=0, column=1, sticky="ew", padx=(10, 0))
        ttk.Label(form, text="Материал").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.material_display = tk.StringVar(value=next(iter(material_names.values())))
        ttk.Combobox(form, textvariable=self.material_display, values=list(material_names.values()), state="readonly") \
            .grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))

        ttk.Separator(form).grid(row=2, column=0, columnspan=4, sticky="ew", pady=16)
        ttk.Label(form, text="ID наклейки").grid(row=3, column=0, sticky="w")
        ttk.Label(form, text="Размер").grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="Количество").grid(row=3, column=2, sticky="w")
        self.asset_id = tk.StringVar(value=asset_ids[0] if asset_ids else "RK17-")
        self.size_code = tk.StringVar(value="B")
        self.quantity = tk.IntVar(value=1)
        ttk.Combobox(form, textvariable=self.asset_id, values=asset_ids, width=22).grid(row=4, column=0, sticky="ew")
        ttk.Combobox(form, textvariable=self.size_code, values=list(SIZES_MM), width=9, state="readonly").grid(row=4, column=1, sticky="w", padx=10)
        ttk.Spinbox(form, textvariable=self.quantity, from_=1, to=999, width=9).grid(row=4, column=2, sticky="w")
        ttk.Button(form, text="Добавить", command=self.add_item).grid(row=4, column=3, padx=(10, 0))

        self.items = ttk.Treeview(form, columns=("asset", "size", "qty"), show="headings", height=12)
        self.items.heading("asset", text="Наклейка")
        self.items.heading("size", text="Размер")
        self.items.heading("qty", text="Количество")
        self.items.column("asset", width=220)
        self.items.column("size", width=100, anchor="center")
        self.items.column("qty", width=120, anchor="center")
        self.items.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=(12, 0))
        ttk.Button(form, text="Удалить выбранное", command=self.remove_item).grid(row=6, column=0, sticky="w", pady=8)
        buttons = ttk.Frame(form)
        buttons.grid(row=7, column=0, columnspan=4, sticky="e", pady=(8, 0))
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(side="left", padx=5)
        ttk.Button(buttons, text="Создать заказ", command=self.accept).pack(side="left")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(5, weight=1)

    def add_item(self):
        asset = self.asset_id.get().strip().upper()
        if not asset or self.quantity.get() < 1:
            return
        self.items.insert("", "end", values=(asset, self.size_code.get(), self.quantity.get()))

    def remove_item(self):
        for item in self.items.selection():
            self.items.delete(item)

    def accept(self):
        values = [self.items.item(item, "values") for item in self.items.get_children()]
        if not values:
            messagebox.showwarning("Пустой заказ", "Добавьте хотя бы одну наклейку.", parent=self)
            return
        material_id = next(key for key, name in self.material_names.items() if name == self.material_display.get())
        self.result = Order(
            self.order_id.get().strip(), material_id,
            items=[OrderItem(str(asset), str(size), int(qty)) for asset, size, qty in values],
        )
        self.destroy()


class PrintnikApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Печатник 0.3")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self.option_add("*Font", ("Segoe UI", 10))
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.store = OrderStore(DATA_DIR / "printnik.db")
        self.materials = load_materials(CONFIG_DIR / "materials.json")
        self.size_rules = load_size_rules(CONFIG_DIR / "cut_size_rules.json")
        self.registry = DeviceRegistry(DATA_DIR / "equipment.json", CONFIG_DIR / "equipment.example.json")
        self.devices = self.registry.all()
        configured_catalog = self.store.get_setting("catalog_root")
        roots = [Path(configured_catalog)] if configured_catalog else []
        if not FROZEN:
            roots.append(WORKSPACE_DIR / "production")
        self.catalog = AssetCatalog(roots)
        self.catalog.refresh()
        self.current_order_id: str | None = None
        self.busy = False
        self._build()
        self.refresh_orders()
        self.refresh_blade_banner()
        if not self.catalog.ids():
            self.after(500, self._first_run_catalog)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build(self):
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 20))
        style.configure("Status.TLabel", font=("Segoe UI Semibold", 12))
        top = ttk.Frame(self, padding=(18, 14))
        top.pack(fill="x")
        ttk.Label(top, text="Печатник", style="Title.TLabel").pack(side="left")
        self.banner = ttk.Label(top, text="Готов", style="Status.TLabel")
        self.banner.pack(side="right")
        blade_controls = ttk.Frame(top)
        blade_controls.pack(side="right", padx=20)
        cutters = [item for item in self.devices if item["kind"] == "cutter"]
        self.cutter_ids = [item["device_id"] for item in cutters]
        self.cutter_choice = tk.StringVar(value=self.cutter_ids[0] if self.cutter_ids else "")
        self.cutter_dropdown = ttk.Combobox(blade_controls, textvariable=self.cutter_choice,
                                            values=self.cutter_ids, state="readonly", width=10)
        self.cutter_dropdown.pack(side="left", padx=4)
        self.cutter_choice.trace_add("write", lambda *_: self.refresh_blade_banner())
        self.blade_banner = ttk.Label(blade_controls, text="Нож: —", style="Status.TLabel")
        self.blade_banner.pack(side="left", padx=6)
        ttk.Button(blade_controls, text="Новый нож", command=self.replace_blade).pack(side="left", padx=4)
        ttk.Button(blade_controls, text="Статистика", command=self.show_blade_statistics).pack(side="left")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        orders_tab = ttk.Frame(notebook, padding=12)
        equipment_tab = ttk.Frame(notebook, padding=12)
        notebook.add(orders_tab, text="Заказы")
        notebook.add(equipment_tab, text="Материалы и оборудование")

        left = ttk.Frame(orders_tab)
        left.pack(side="left", fill="both", expand=True)
        toolbar = ttk.Frame(left)
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Button(toolbar, text="Новый ручной заказ", command=self.new_order).pack(side="left")
        ttk.Button(toolbar, text="Импортировать заказ", command=self.import_order).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Проверить входящие", command=self.check_inbox).pack(side="left")
        ttk.Button(toolbar, text="Конверты", command=self.print_envelopes).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Обновить", command=self.refresh_orders).pack(side="left", padx=8)
        self.orders = ttk.Treeview(left, columns=("id", "status", "material", "sheets"), show="headings")
        for key, title, width in (("id", "Заказ", 190), ("status", "Состояние", 220), ("material", "Материал", 210), ("sheets", "Листы", 70)):
            self.orders.heading(key, text=title)
            self.orders.column(key, width=width, anchor="center" if key == "sheets" else "w")
        self.orders.pack(fill="both", expand=True)
        self.orders.bind("<<TreeviewSelect>>", self.select_order)

        right = ttk.Frame(orders_tab, width=330, padding=(16, 0, 0, 0))
        right.pack(side="right", fill="y")
        ttk.Label(right, text="Выбранный заказ", font=("Segoe UI Semibold", 14)).pack(anchor="w")
        self.details = tk.Text(right, width=42, height=20, wrap="word", state="disabled", relief="flat", background="#f4f4f4")
        self.details.pack(fill="x", pady=(8, 12))
        self.prepare_btn = ttk.Button(right, text="1. Проверить и скомпоновать", command=self.prepare_selected)
        self.prepare_btn.pack(fill="x", pady=4)
        ttk.Button(right, text="Посмотреть все контуры реза", command=self.open_contour_previews).pack(fill="x", pady=4)
        ttk.Button(right, text="Утвердить контуры листов", command=self.approve_contours).pack(fill="x", pady=4)
        ttk.Button(right, text="План прямой резки (без отправки)", command=self.show_direct_cut_plan).pack(fill="x", pady=4)
        ttk.Button(right, text="2. Открыть листы для печати", command=self.print_selected).pack(fill="x", pady=4)
        ttk.Button(right, text="3. Открыть задание для плоттера", command=self.cut_selected).pack(fill="x", pady=4)
        self.direct_cut_button = ttk.Button(right, text="Пробный прямой рез одного листа", command=self.direct_cut_selected)
        self.direct_cut_button.pack(fill="x", pady=4)
        ttk.Button(right, text="4. Учесть рез листа", command=self.confirm_cut_sheet).pack(fill="x", pady=4)
        ttk.Button(right, text="Отметить заказ готовым", command=self.complete_selected).pack(fill="x", pady=4)
        ttk.Button(right, text="Открыть папку заказа", command=self.open_selected_folder).pack(fill="x", pady=(18, 4))
        ttk.Button(right, text="Предпросмотр листа", command=self.preview_selected).pack(fill="x", pady=4)
        ttk.Button(right, text="Аварийный перенос", command=self.emergency_transfer).pack(fill="x", pady=4)

        ttk.Label(equipment_tab, text="Материалы", font=("Segoe UI Semibold", 14)).pack(anchor="w")
        ttk.Button(equipment_tab, text="Создать калибровочный лист A/B", command=self.create_calibration).pack(anchor="e")
        ttk.Button(equipment_tab, text="Пробный лист регистрационных меток", command=self.create_registration_test).pack(anchor="e", pady=(4, 0))
        self.registration_scan_button = ttk.Button(equipment_tab, text="Проверить считывание меток (без резки)",
                                                   command=self.check_registration_marks)
        self.registration_scan_button.pack(anchor="e", pady=(4, 0))
        self.position_check_button = ttk.Button(equipment_tab, text="Проверить положение над полосой (без резки)",
                                                command=self.check_control_line_position)
        self.position_check_button.pack(anchor="e", pady=(4, 0))
        self.first_cut_button = ttk.Button(equipment_tab, text="Проверить глубину реза на том же листе",
                                           command=self.check_kiss_test)
        self.first_cut_button.pack(anchor="e", pady=(4, 0))
        self.direct_cat_button = ttk.Button(equipment_tab, text="Пробный плавный рез кота на новом листе",
                                            command=self.check_direct_cat_trial)
        self.direct_cat_button.pack(anchor="e", pady=(4, 0))
        self.blade_check_button = ttk.Button(equipment_tab, text="Проверить нож малым квадратом на том же листе",
                                             command=self.check_blade_on_cat_sheet)
        self.blade_check_button.pack(anchor="e", pady=(4, 0))
        self.smooth_motion_button = ttk.Button(equipment_tab, text="Проверить плавность движения (без резки)",
                                               command=self.check_smooth_motion)
        self.smooth_motion_button.pack(anchor="e", pady=(4, 0))
        material_tree = ttk.Treeview(equipment_tab, columns=("name", "side", "cut", "status"), show="headings", height=3)
        for key, title, width in (("name", "Материал", 260), ("side", "Загрузка", 430), ("cut", "Резка", 180), ("status", "Статус", 130)):
            material_tree.heading(key, text=title); material_tree.column(key, width=width)
        for material in self.materials.values():
            cut = f"нож {material.blade}, сила {material.force}, скорость {material.speed}, проходов {material.passes}"
            status = "Откалиброван" if material.calibrated else "Нужен тест"
            material_tree.insert("", "end", values=(material.name, material.print_side_instruction, cut, status))
        material_tree.pack(fill="x", pady=(8, 14))
        ttk.Label(equipment_tab, text="Оборудование", font=("Segoe UI Semibold", 14)).pack(anchor="w")
        device_buttons = ttk.Frame(equipment_tab)
        device_buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(device_buttons, text="Добавить устройство", command=self.add_device).pack(side="left")
        ttk.Button(device_buttons, text="Отметить откалиброванным", command=self.calibrate_device).pack(side="left", padx=8)
        self.cameo_check_button = ttk.Button(device_buttons, text="Проверить Cameo по USB", command=self.check_cameo_usb)
        self.cameo_check_button.pack(side="left", padx=8)
        ttk.Button(device_buttons, text="Указать папку производственного каталога", command=self.choose_catalog).pack(side="left", padx=8)
        self.device_tree = ttk.Treeview(equipment_tab, columns=("id", "name", "kind", "connection", "status"), show="headings", height=4)
        for key, title, width in (("id", "ID", 110), ("name", "Устройство", 280), ("kind", "Тип", 120), ("connection", "Подключение", 170), ("status", "Состояние", 180)):
            self.device_tree.heading(key, text=title); self.device_tree.column(key, width=width)
        self.device_tree.pack(fill="x", pady=(8, 8))
        self.refresh_devices()

    def on_close(self):
        if self.busy and not messagebox.askyesno("Подготовка выполняется", "Закрыть Печатник? Текущая подготовка будет прервана."):
            return
        self.store.close()
        self.destroy()

    def set_banner(self, text: str):
        self.banner.configure(text=text)
        self.update_idletasks()

    def refresh_blade_banner(self):
        cutter_id = self.cutter_choice.get()
        if not cutter_id:
            self.blade_banner.configure(text="Нож: плоттер не задан")
            return
        blade = self.store.ensure_blade(cutter_id)
        qualifier = " с начала учёта" if not blade["baseline_known"] else ""
        self.blade_banner.configure(
            text=f"{cutter_id} · нож №{blade['blade_id']}: {blade['length_mm'] / 1000:.1f} м{qualifier}"
        )

    def replace_blade(self):
        cutter_id = self.cutter_choice.get()
        if not cutter_id:
            return
        reason_choice = messagebox.askyesnocancel(
            "Установлен новый нож",
            f"Отметьте замену только после установки нового ножа в {cutter_id}.\n\n"
            "Да — старый затупился. Нет — заменён по другой причине. Отмена — ничего не менять.",
            parent=self,
        )
        if reason_choice is None:
            return
        self.store.replace_blade(cutter_id, "worn" if reason_choice else "other")
        self.refresh_blade_banner()
        self.show_blade_statistics()

    def show_blade_statistics(self):
        cutter_id = self.cutter_choice.get()
        if not cutter_id:
            messagebox.showinfo("Ножи", "Вначале добавьте плоттер.")
            return
        history = self.store.blade_history(cutter_id)
        lines = [f"Плоттер {cutter_id}", "Длина — подтверждённая или вручную оценённая резка с начала учёта."]
        benchmarks: dict[str, list[float]] = {}
        for blade in history:
            status = "установлен" if blade["retired_at"] is None else "заменён"
            lines.append(f"\nНож №{blade['blade_id']} · {status} · всего {blade['total_mm'] / 1000:.1f} м")
            if not blade["baseline_known"]:
                lines.append("  Ранее пройденная длина неизвестна; это только расход с начала учёта.")
            for material_id, usage in blade["by_material"].items():
                name = self.materials.get(material_id)
                lines.append(f"  {name.name if name else material_id}: {usage['length_mm'] / 1000:.1f} м")
            if (blade["retirement_reason"] == "worn" and blade["baseline_known"]
                    and len(blade["by_material"]) == 1 and blade["total_mm"] > 0):
                material_id = next(iter(blade["by_material"]))
                benchmarks.setdefault(material_id, []).append(blade["total_mm"] / 1000)
        if benchmarks:
            lines.append("\nОриентиры по ножам, заменённым из-за износа и работавшим на одном материале:")
            for material_id, values in benchmarks.items():
                name = self.materials.get(material_id)
                lines.append(f"  {name.name if name else material_id}: {sum(values) / len(values):.1f} м "
                             f"({len(values)} ножей; не гарантированный ресурс)")
        messagebox.showinfo("Учёт ножей", "\n".join(lines), parent=self)

    def refresh_orders(self):
        selected = self.current_order_id
        for row in self.orders.get_children():
            self.orders.delete(row)
        for order in self.store.list_orders():
            material = self.materials.get(order.material_id)
            iid = self.orders.insert("", "end", values=(order.order_id, STATUS_LABELS[order.status], material.name if material else order.material_id, order.sheet_count))
            if order.order_id == selected:
                self.orders.selection_set(iid)
        self.show_details()
        self.refresh_blade_banner()

    def select_order(self, _event=None):
        selection = self.orders.selection()
        if selection:
            self.current_order_id = str(self.orders.item(selection[0], "values")[0])
        self.show_details()

    def selected_order(self) -> Order | None:
        return self.store.get(self.current_order_id) if self.current_order_id else None

    def show_details(self):
        order = self.selected_order()
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        if order:
            material = self.materials[order.material_id]
            lines = [order.order_id, STATUS_LABELS[order.status], "", material.name, material.print_side_instruction, "", "Состав:"]
            lines.extend(f"  {item.asset_id} · {item.size_code} · {item.quantity} шт." for item in order.items)
            if order.sheet_count:
                lines.extend(["", f"Листов: {order.sheet_count}"])
                completed = self.store.completed_cut_sheets(order.order_id)
                lines.append(f"Рез подтверждён: {len(completed)}/{order.sheet_count} листов")
                if order.output_dir:
                    report_path = Path(order.output_dir) / "job.json"
                    if report_path.exists():
                        report = json.loads(report_path.read_text(encoding="utf-8"))
                        if "planned_cut_length_mm" in report:
                            lines.append(f"По макету: {report['planned_cut_length_mm'] / 1000:.1f} м реза")
                        if report.get("contour_previews") and not report.get("contour_review_approved"):
                            lines.append("Сложные контуры A ждут просмотра и утверждения")
            if order.error:
                lines.extend(["", "Ошибка:", order.error])
            assignment = self.store.get_assignment(order.order_id)
            if assignment and assignment.get("printer_segments"):
                lines.extend(["", "Оборудование:"])
                lines.append("  Печать: " + ", ".join(f"{s['device_id']} · листы {s['first_sheet']}–{s['last_sheet']}" for s in assignment["printer_segments"]))
                lines.append("  Резка: " + ", ".join(f"{s['device_id']} · листы {s['first_sheet']}–{s['last_sheet']}" for s in assignment["cutter_segments"]))
            self.details.insert("1.0", "\n".join(lines))
        self.details.configure(state="disabled")

    def new_order(self):
        names = {key: value.name for key, value in self.materials.items()}
        dialog = NewOrderDialog(self, self.store.next_order_id(), names, self.catalog.ids())
        self.wait_window(dialog)
        if dialog.result:
            if self.store.get(dialog.result.order_id):
                messagebox.showerror("Номер уже существует", "Измените номер заказа.")
                return
            self.store.save(dialog.result, "manual_order_created")
            self.current_order_id = dialog.result.order_id
            self.refresh_orders()

    def import_order(self):
        path = filedialog.askopenfilename(parent=self, title="Выберите файл заказа", filetypes=[("Заказ JSON", "*.json")])
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            order, created = import_payload(self.store, payload, f"file:{Path(path).name}")
            self.current_order_id = order.order_id
            self.refresh_orders()
            messagebox.showinfo("Импорт", "Заказ добавлен." if created else "Этот заказ уже был получен. Повторная печать не создана.")
        except Exception as exc:
            self._show_error("Заказ не импортирован", str(exc))

    def check_inbox(self):
        results = scan_inbox(self.store, DATA_DIR / "Inbox")
        self.refresh_orders()
        if not results:
            messagebox.showinfo("Входящие", f"Новых файлов нет.\n\nПапка: {DATA_DIR / 'Inbox'}")
        else:
            messagebox.showinfo("Входящие", "\n".join(f"{path.name}: {status}" for path, status in results))

    def print_envelopes(self):
        available = [order for order in self.store.list_orders() if order.address]
        selected = self.selected_order()
        if selected and selected.address:
            choice = messagebox.askyesnocancel("Конверты", "Да — только выбранный заказ.\nНет — все заказы с адресами.\nОтмена — ничего не печатать.")
            if choice is None:
                return
            orders = [selected] if choice else available
        else:
            orders = available
        if not orders:
            messagebox.showinfo("Конверты", "Пока нет заказов с сохранённым адресом.")
            return
        if not messagebox.askyesno("Печать конвертов", f"Подготовить {len(orders)} конверт(а/ов)? Установите чистые конверты в принтер."):
            return
        try:
            path = create_envelopes_pdf(orders, OUTPUT_DIR / "envelopes" / "envelopes-all.pdf")
            send_pdf_to_printer(path, self._assigned_printer_name(orders[0]))
            for order in orders:
                self.store.save(order, "envelope_print_dispatched", {"batch": str(path)})
            messagebox.showinfo("Конверты", "Задание отправлено. Для повторной печати можно снова запустить эту команду.")
        except Exception as exc:
            self._show_error("Конверты не напечатаны", str(exc))

    def refresh_devices(self):
        self.devices = self.registry.all()
        cutter_ids = [item["device_id"] for item in self.devices if item["kind"] == "cutter"]
        self.cutter_ids = cutter_ids
        self.cutter_dropdown.configure(values=cutter_ids)
        if self.cutter_choice.get() not in cutter_ids:
            self.cutter_choice.set(cutter_ids[0] if cutter_ids else "")
        for row in self.device_tree.get_children():
            self.device_tree.delete(row)
        labels = {"printer": "Принтер", "cutter": "Плоттер"}
        statuses = {"ready": "Готов", "busy": "Занят", "offline": "Отключён", "error": "Ошибка", "requires_calibration": "Нужна калибровка"}
        for device in self.devices:
            self.device_tree.insert("", "end", values=(device["device_id"], device["display_name"], labels.get(device["kind"], device["kind"]), device["connection"], statuses.get(device["status"], device["status"])))

    def check_cameo_usb(self):
        self.cameo_check_button.configure(state="disabled")
        self.set_banner("Проверка Cameo по USB...")

        def worker():
            try:
                result = probe_cameo()
                error = None
            except CameoConnectionError as exc:
                result, error = None, str(exc)

            def finish():
                if not self.winfo_exists():
                    return
                self.cameo_check_button.configure(state="normal")
                self.set_banner("Готов" if not error else "Cameo: проверка не удалась")
                if error:
                    messagebox.showerror("Связь с Cameo", error, parent=self)
                    return
                states = {"ready": "готов", "moving": "занят", "unloaded": "материал не загружен", "unknown": "неизвестно"}
                tool_names = {"0": "пусто", "1": "ручной нож", "2": "AutoBlade",
                              "3": "нож для глубокой резки", "4": "крафт-нож", "5": "роторный нож"}
                first_tool = result["tool_1"]
                second_tool = result["tool_2"]
                messagebox.showinfo(
                    "Связь с Cameo",
                    f"Плоттер ответил напрямую по USB.\n"
                    f"{result['firmware']}\n"
                    f"Состояние: {states.get(result['status'], result['status'])}.\n"
                    f"Гнездо 1: {tool_names.get(first_tool, 'код ' + first_tool)}.\n"
                    f"Гнездо 2: {tool_names.get(second_tool, 'код ' + second_tool)}.\n\n"
                    "Движение и резка не запускались.",
                    parent=self,
                )

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def check_registration_marks(self):
        manifest = filedialog.askopenfilename(
            parent=self, title="Выберите описание напечатанного пробного листа",
            filetypes=[("Пробный лист", "registration-test.json"), ("JSON", "*.json")],
        )
        if not manifest:
            return
        try:
            registration_geometry(Path(manifest))
        except CameoConnectionError as exc:
            messagebox.showerror("Пробный лист", str(exc), parent=self)
            return
        if not messagebox.askyesno(
            "Проверка меток без резки",
            "Загрузите напечатанный лист A4 в Cameo без коврика, как раньше, "
            "и дождитесь состояния «Готово». Закройте Silhouette Studio.\n\n"
            "После нажатия «Да» плоттер передвинет лист и оптический датчик, "
            "чтобы найти четыре метки. Нож и резка не включаются. Начать?",
            parent=self,
        ):
            return
        self.registration_scan_button.configure(state="disabled")
        self.set_banner("Cameo ищет регистрационные метки...")

        def worker():
            try:
                result = scan_registration_marks(Path(manifest))
                error = None
            except CameoConnectionError as exc:
                result, error = None, str(exc)

            def finish():
                if not self.winfo_exists():
                    return
                self.registration_scan_button.configure(state="normal")
                self.set_banner("Готов" if not error else "Поиск меток не завершён")
                if error:
                    messagebox.showerror("Поиск меток", error, parent=self)
                elif result["status"] == "found":
                    messagebox.showinfo("Поиск меток", "Cameo сообщил об успешном поиске меток. "
                                        "Нож и резка не включались. Сохраните этот лист для следующего опыта.",
                                        parent=self)
                else:
                    messagebox.showwarning("Поиск меток", "Cameo не подтвердил поиск всех меток. "
                                           f"Код ответа: {result['raw_response_hex']}. "
                                           "Нож и резка не включались.", parent=self)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def check_control_line_position(self):
        manifest = filedialog.askopenfilename(
            parent=self, title="Выберите описание успешного листа с нижним отступом 25 мм",
            filetypes=[("Пробный лист", "registration-test.json"), ("JSON", "*.json")],
        )
        if not manifest:
            return
        try:
            if registration_geometry(Path(manifest)) != (5240, 3800, 0, 0):
                raise CameoConnectionError("Нужен пробный лист с нижним отступом 25 мм")
        except CameoConnectionError as exc:
            messagebox.showerror("Пробный лист", str(exc), parent=self)
            return
        if not messagebox.askyesno(
            "Проверка положения без резки",
            "Загрузите успешный лист A4 с нижним отступом 25 мм без коврика и "
            "дождитесь состояния «Готово». Закройте Silhouette Studio.\n\n"
            "Плоттер снова найдёт четыре метки, затем поднимет инструмент и "
            "переместится к середине контрольной полосы 50 мм. "
            "Нож не опускается и резка не включается. Начать?",
            parent=self,
        ):
            return
        self.position_check_button.configure(state="disabled")
        self.set_banner("Cameo ищет метки и проверяет положение...")

        def worker():
            try:
                result = position_over_control_line(Path(manifest))
                error = None
            except CameoConnectionError as exc:
                result, error = None, str(exc)

            def finish():
                if not self.winfo_exists():
                    return
                self.position_check_button.configure(state="normal")
                self.set_banner("Готов" if not error else "Проверка положения не завершена")
                if error:
                    messagebox.showerror("Проверка положения", error, parent=self)
                elif result["status"] == "position_command_sent":
                    messagebox.showinfo(
                        "Проверка положения",
                        "Метки найдены. Команда перемещения с поднятым инструментом отправлена. "
                        "Посмотрите, остановилась ли головка над серединой полосы 50 мм. "
                        "Возможен небольшой сдвиг между датчиком и ножом; резки не было.", parent=self)
                else:
                    messagebox.showwarning("Проверка положения",
                                           "Cameo не подтвердил поиск всех меток. "
                                           f"Код ответа: {result['raw_response_hex']}. Движение к полосе не запускалось.",
                                           parent=self)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def check_kiss_test(self):
        manifest = filedialog.askopenfilename(
            parent=self, title="Выберите описание второго пробного реза на том же листе",
            filetypes=[("Пробный рез", "kiss-test-1.json"), ("JSON", "*.json")],
        )
        if not manifest:
            return
        try:
            validate_kiss_test_manifest(Path(manifest))
        except CameoConnectionError as exc:
            messagebox.showerror("Пробный рез", str(exc), parent=self)
            return
        if not messagebox.askyesno(
            "Проверка глубины реза",
            "В Cameo должен быть загружен ТОТ ЖЕ матовый лист с уже вырезанным "
            "квадратом 12 мм, без коврика. "
            "В первом гнезде — AutoBlade; Silhouette Studio закрыта.\n\n"
            "Печатник заново найдёт четыре метки и только после успеха "
            "вырежет ОДИН квадрат 10 × 10 мм на свободном месте правее первого. "
            "Нож 1, сила 4, скорость 4, один проход. Это новая проба, "
            "глубина ещё не подтверждена. Начать рез?",
            parent=self,
        ):
            return
        self.first_cut_button.configure(state="disabled")
        self.set_banner("Cameo ищет метки для пробного реза...")

        def worker():
            try:
                result = run_kiss_test(Path(manifest))
                error = None
            except CameoConnectionError as exc:
                result, error = None, str(exc)

            def finish():
                if not self.winfo_exists():
                    return
                self.first_cut_button.configure(state="normal")
                banner = {"cut_device_ready": "Плоттер готов; лист загружен",
                          "not_found": "Метки не найдены; рез не запускался"}
                self.set_banner(banner.get(result["status"], "Завершение реза не подтверждено")
                                if result else "Пробный рез не завершён")
                if error:
                    messagebox.showerror("Пробный рез", error, parent=self)
                elif result["status"] == "cut_device_ready":
                    messagebox.showinfo("Пробный рез",
                                        "Метки найдены. Команды одного квадрата отправлены, "
                                        "и Cameo снова сообщил состояние «Готово». "
                                        "Лист остаётся загруженным: осмотрите рез и выгрузите "
                                        "лист кнопкой на плоттере, когда будете готовы. "
                                        "Глубину реза нужно проверить вручную.", parent=self)
                elif result["status"] == "cut_completion_unconfirmed":
                    messagebox.showwarning("Пробный рез",
                                           "Команды квадрата отправлены, но Cameo не подтвердил "
                                           "завершение движения. Не повторяйте рез. Проверьте плоттер "
                                           "и дождитесь его полной остановки перед выгрузкой листа.", parent=self)
                else:
                    messagebox.showwarning("Пробный рез",
                                           "Cameo не нашёл все метки; рез не запускался. "
                                           f"Код ответа: {result['raw_response_hex']}.", parent=self)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def check_smooth_motion(self):
        manifest = filedialog.askopenfilename(
            parent=self, title="Выберите описание листа с котом для движения без резки",
            filetypes=[("Пробный лист с котом", "direct-cat-trial.json"), ("JSON", "*.json")],
        )
        if not manifest:
            return
        try:
            validate_direct_cat_manifest(Path(manifest))
        except CameoConnectionError as exc:
            messagebox.showerror("Проверка плавности", str(exc), parent=self)
            return
        if not messagebox.askyesno(
            "Проверка плавности без резки",
            "Загрузите тот же лист с котом без коврика, дождитесь состояния «Готово» "
            "и закройте Silhouette Studio.\n\n"
            "Печатник найдёт четыре метки, затем проведёт головку по пробному "
            "маршруту с ПОДНЯТЫМ ножом. Между командами движения не будет "
            "запросов состояния. В конце головка должна остановиться над полосой 50 мм. "
            "Резки не будет. Начать?",
            parent=self,
        ):
            return
        self.smooth_motion_button.configure(state="disabled")
        self.set_banner("Проверка плавности без резки...")

        def worker():
            try:
                result = probe_tool_up_smooth(Path(manifest))
                error = None
            except CameoConnectionError as exc:
                result, error = None, str(exc)

            def finish():
                if not self.winfo_exists():
                    return
                self.smooth_motion_button.configure(state="normal")
                self.set_banner("Cameo сообщил «Готово»" if result and result["status"] == "motion_device_ready"
                                else "Проверка плавности не подтверждена")
                if error:
                    messagebox.showerror("Проверка плавности", error, parent=self)
                elif result["status"] == "motion_device_ready":
                    messagebox.showinfo("Проверка плавности",
                                        "Команды маршрута без резки отправлены; Cameo сообщил «Готово». "
                                        "Проверьте, двигалась ли головка по всему маршруту и "
                                        "остановилась ли над полосой 50 мм. "
                                        "Сообщите, были ли паузы и мерцание панели.", parent=self)
                elif result["status"] == "not_found":
                    messagebox.showwarning("Проверка плавности",
                                           "Метки не найдены; движение по маршруту не запускалось.", parent=self)
                else:
                    messagebox.showwarning("Проверка плавности",
                                           "Завершение движения не подтверждено. Осмотрите плоттер "
                                           "перед следующим действием.", parent=self)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def check_direct_cat_trial(self):
        manifest = filedialog.askopenfilename(
            parent=self, title="Выберите описание плавного реза кота на новом листе",
            filetypes=[("Плавный рез кота", "cat-smooth-trial.json")],
        )
        if not manifest:
            return
        try:
            if Path(manifest).name != "cat-smooth-trial.json":
                raise CameoConnectionError("Выберите cat-smooth-trial.json для нового листа")
            validate_direct_cat_manifest(Path(manifest))
        except CameoConnectionError as exc:
            messagebox.showerror("Пробный контур кота", str(exc), parent=self)
            return
        if not messagebox.askyesno(
            "Пробный контур кота",
            "В Cameo должен быть загружен НОВЫЙ матовый лист с напечатанным котом "
            "из cat-gap-print.pdf, в фактическом размере. "
            "Лист загружен без коврика, печатной стороной вверх; "
            "в первом гнезде — AutoBlade; Silhouette Studio закрыта.\n\n"
            "Печатник найдёт четыре метки и вырежет ОДИН контур кота. "
            "Контур +0,6 мм наружу от изображения, в двух узких промежутках у головы "
            "уменьшен до 0,2–0,4 мм; нож 1, сила 4, "
            "скорость 4, один проход. Проверенный на напечатанном коте плавный "
            "контур будет отправлен пятью пакетами. "
            "Начать рез на новом листе?",
            parent=self,
        ):
            return
        self.direct_cat_button.configure(state="disabled")
        self.set_banner("Cameo ищет метки для пробного контура кота...")

        def worker():
            try:
                result = run_direct_cat_trial(Path(manifest))
                error = None
            except CameoConnectionError as exc:
                result, error = None, str(exc)

            def finish():
                if not self.winfo_exists():
                    return
                self.direct_cat_button.configure(state="normal")
                self.set_banner(
                    "Плоттер готов; лист загружен" if result and result["status"] == "cut_device_ready"
                    else "Пробный контур кота не подтверждён"
                )
                if error:
                    messagebox.showerror("Пробный контур кота", error, parent=self)
                elif result["status"] == "cut_device_ready":
                    messagebox.showinfo(
                        "Пробный контур кота",
                        "Метки найдены. Контур кота отправлен, Cameo снова сообщил «Готово». "
                        "Лист остаётся загруженным. Осмотрите рез, затем выгрузите лист "
                        "кнопкой на плоттере. Проверьте наклейку и подложку вручную.", parent=self)
                elif result["status"] == "not_found":
                    messagebox.showwarning("Пробный контур кота",
                                           "Не все метки найдены; рез не запускался.", parent=self)
                else:
                    messagebox.showwarning(
                        "Пробный контур кота",
                        "Завершение реза не подтверждено. Не повторяйте опыт; "
                        "проверьте плоттер и лист после полной остановки.", parent=self)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def check_blade_on_cat_sheet(self):
        manifest = filedialog.askopenfilename(
            parent=self, title="Выберите проверку ножа на листе с котом",
            filetypes=[("Проверка ножа", "cat-gap-blade-check.json")],
        )
        if not manifest:
            return
        try:
            validate_blade_check_manifest(Path(manifest))
        except CameoConnectionError as exc:
            messagebox.showerror("Проверка ножа", str(exc), parent=self)
            return
        if not messagebox.askyesno(
            "Проверка ножа",
            "Загрузите ТОТ ЖЕ матовый лист с котом без коврика, печатной стороной вверх. "
            "В первом гнезде должен быть плотно зафиксирован AutoBlade; Silhouette Studio закрыта.\n\n"
            "Печатник найдёт четыре метки и вырежет только ОДИН квадрат 10 × 10 мм "
            "в пустом месте внизу листа. Нож 1, сила 4, скорость 4, один проход. "
            "Повторный рез кота не запускается. Начать проверку?",
            parent=self,
        ):
            return
        self.blade_check_button.configure(state="disabled")
        self.set_banner("Проверка ножа: поиск меток...")

        def worker():
            try:
                result = run_blade_check(Path(manifest))
                error = None
            except CameoConnectionError as exc:
                result, error = None, str(exc)

            def finish():
                if not self.winfo_exists():
                    return
                self.blade_check_button.configure(state="normal")
                self.set_banner("Плоттер готов; лист загружен" if result and result["status"] == "cut_device_ready"
                                else "Проверка ножа не подтверждена")
                if error:
                    messagebox.showerror("Проверка ножа", error, parent=self)
                elif result["status"] == "cut_device_ready":
                    messagebox.showinfo(
                        "Проверка ножа",
                        "Команды квадрата отправлены; Cameo сообщил «Готово». "
                        "Лист остаётся загруженным. После остановки выгрузите его кнопкой плоттера "
                        "и вручную проверьте маленький квадрат и подложку.", parent=self)
                elif result["status"] == "not_found":
                    messagebox.showwarning("Проверка ножа", "Метки не найдены; рез не запускался.", parent=self)
                else:
                    messagebox.showwarning("Проверка ножа",
                                           "Завершение не подтверждено. Не повторяйте опыт; осмотрите лист.", parent=self)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def add_device(self):
        kind = simpledialog.askstring("Тип оборудования", "Введите: printer для принтера или cutter для плоттера", parent=self)
        if kind not in {"printer", "cutter"}:
            return
        device_id = simpledialog.askstring("ID", "Например PRN-02 или CUT-02", parent=self)
        name = simpledialog.askstring("Название", "Как показывать устройство?", parent=self)
        model = simpledialog.askstring("Модель", "Модель оборудования", parent=self) or "не указана"
        if not device_id or not name:
            return
        try:
            self.registry.add(device_id=device_id.strip().upper(), kind=kind, display_name=name, model=model, connection="usb")
            self.refresh_devices()
            messagebox.showinfo("Устройство добавлено", "До калибровки Печатник не будет назначать ему заказы.")
        except Exception as exc:
            self._show_error("Не удалось добавить устройство", str(exc))

    def calibrate_device(self):
        selection = self.device_tree.selection()
        if not selection:
            messagebox.showwarning("Выберите устройство", "Выберите строку оборудования.")
            return
        values = self.device_tree.item(selection[0], "values")
        device_id = str(values[0])
        device = next(item for item in self.registry.all() if item["device_id"] == device_id)
        material_hint = ", ".join(self.materials)
        text = simpledialog.askstring("Материалы", f"Разрешённые материалы через запятую:\n{material_hint}", parent=self,
                                      initialvalue=",".join(device.get("approved_materials", [])))
        if text is None:
            return
        materials = [part.strip() for part in text.split(",") if part.strip()]
        unknown = [item for item in materials if item not in self.materials]
        if unknown:
            messagebox.showerror("Неизвестный материал", ", ".join(unknown))
            return
        profiles = [] if device["kind"] == "printer" else ["outer_only", "internal_holes_b_plus"]
        if not messagebox.askyesno("Подтверждение калибровки", f"Физический тест {device['display_name']} для выбранных материалов действительно пройден?"):
            return
        self.registry.calibrate(device_id, materials, profiles)
        self.refresh_devices()

    def create_calibration(self):
        try:
            folder = OUTPUT_DIR / "calibration"
            create_calibration_package(folder)
            open_folder(folder)
            messagebox.showinfo("Калибровочный пакет", "Созданы PDF для печати, SVG резки и контрольная шкала 50 мм. Метки: 10 мм сверху и сбоку, 25 мм снизу.")
        except Exception as exc:
            self._show_error("Не удалось создать калибровочный лист", str(exc))

    def create_registration_test(self):
        raw = simpledialog.askstring(
            "Отступы регистрационных меток",
            "Введите четыре отступа в мм через запятую: слева, справа, сверху, снизу.\n"
            "Например: 10, 10, 10, 10. Это пробный лист без резки.",
            parent=self, initialvalue="10, 10, 10, 10",
        )
        if raw is None:
            return
        try:
            values = [float(part.strip().replace(",", ".")) for part in raw.split(",")]
            if len(values) != 4:
                raise ValueError("Нужны ровно четыре числа: слева, справа, сверху, снизу.")
            order = self.selected_order()
            image_source = None
            image_label = "local-art"
            if order and order.items:
                image_label = order.items[0].asset_id
                try:
                    image_source = self.catalog.resolve(image_label)
                except FileNotFoundError:
                    if order.output_dir:
                        report_path = Path(order.output_dir) / "job.json"
                        if report_path.exists():
                            report = json.loads(report_path.read_text(encoding="utf-8"))
                            for item in report.get("preflight", []):
                                if item.get("asset_id") == image_label and Path(item.get("source", "")).is_file():
                                    image_source = Path(item["source"])
                                    break
            if image_source is None:
                chosen = filedialog.askopenfilename(parent=self, title="Картинка для нижней части листа",
                                                    filetypes=[("Картинки", "*.png *.webp *.jpg *.jpeg")])
                if not chosen:
                    return
                image_source = Path(chosen)
            folder_name = "registration-" + "-".join(f"{value:g}" for value in values).replace(".", "p")
            folder_name += "-" + "".join(char for char in image_label if char.isalnum() or char in "-_")[:40]
            folder = OUTPUT_DIR / "experiments" / folder_name
            manifest = create_registration_test_package(folder, left_mm=values[0], right_mm=values[1],
                                                        top_mm=values[2], bottom_mm=values[3],
                                                        image_source=image_source)
            os.startfile(manifest["preview_png"])
            messagebox.showinfo("Пробный лист меток", "Создан пробный лист A4 с картинкой у нижней левой метки. "
                                "Открыт предпросмотр; PDF лежит в папке "
                                "эксперимента. Никаких команд плоттеру не отправлено. "
                                "Рабочий профиль заказов остаётся 10/10/10/25 мм.")
        except ValueError as exc:
            messagebox.showerror("Неверные отступы", str(exc))
        except OSError as exc:
            messagebox.showerror("Не удалось создать пробный лист", str(exc))

    def choose_catalog(self):
        path = filedialog.askdirectory(parent=self, title="Папка с MASTER/ART файлами")
        if path:
            self.store.set_setting("catalog_root", path)
            self.catalog = AssetCatalog([Path(path)])
            count = len(self.catalog.refresh())
            messagebox.showinfo("Каталог подключён", f"Найдено изображений: {count}")

    def _first_run_catalog(self):
        if messagebox.askyesno("Производственный каталог", "Печатник пока не видит MASTER/ART-файлы. Выбрать папку каталога сейчас?"):
            self.choose_catalog()

    def prepare_selected(self):
        order = self.selected_order()
        if not order or self.busy:
            return
        if order.status in {OrderStatus.PRINTING, OrderStatus.PRINTED_WAITING_CUT,
                            OrderStatus.LOADED_FOR_CUT, OrderStatus.CUTTING, OrderStatus.COMPLETE}:
            messagebox.showwarning("Макет уже используется", "Для изменённого макета создайте новый номер заказа, чтобы не потерять соответствие с напечатанными листами.")
            return
        if self.store.has_cut_records(order.order_id):
            messagebox.showwarning("Макет уже резали", "По этому заказу уже учтена резка. Создайте новый номер заказа для изменённого макета.")
            return
        self.busy = True
        self.set_banner("Подготовка заказа…")
        threading.Thread(target=self._prepare_worker, args=(order, set()), daemon=True).start()

    def _prepare_worker(self, order: Order, rectangular_assets: set[str]):
        try:
            report = render_order(order, self.catalog, self.materials[order.material_id], OUTPUT_DIR,
                                  rectangular_assets=rectangular_assets, size_rules=self.size_rules)
            order.sheet_count = report["sheet_count"]
            order.output_dir = str(OUTPUT_DIR / order.order_id)
            order.status = OrderStatus.PAUSED
            order.error = None
            self.store.save(order, "production_package_created", {"sheet_count": order.sheet_count})
            self._assign_equipment(order)
            warnings = [warning for check in report["preflight"] for warning in check["warnings"]]
            self.after(0, lambda: self._prepare_done(order, warnings))
        except PreflightError as exc:
            opaque = {result.asset_id for result in exc.results if any("непрозрачный" in value for value in result.errors)}
            self.after(0, lambda: self._handle_preflight(order, exc, opaque))
        except Exception as exc:
            order.status = OrderStatus.ERROR
            order.error = str(exc)
            self.store.save(order, "preparation_failed", {"traceback": traceback.format_exc()})
            self.after(0, lambda: self._show_error("Подготовка не выполнена", str(exc)))

    def _prepare_done(self, order: Order, warnings: list[str]):
        self.busy = False
        self.set_banner("Проверьте все контуры листов")
        self.refresh_orders()
        text = f"Заказ скомпонован: {order.sheet_count} лист(а/ов)."
        if warnings:
            text += "\n\nПредупреждения:\n• " + "\n• ".join(sorted(set(warnings)))
        text += "\n\nОткройте предпросмотры всех листов и утвердите красные линии до печати."
        messagebox.showinfo("Производственный пакет готов", text)

    def open_contour_previews(self):
        order = self.selected_order()
        if not order or not order.output_dir:
            return
        report = json.loads((Path(order.output_dir) / "job.json").read_text(encoding="utf-8"))
        paths = report.get("sheet_previews", []) + report.get("contour_previews", [])
        if not paths:
            messagebox.showwarning("Нет предпросмотров", "Подготовьте заказ этой версией Печатника.")
            return
        for path in paths:
            os.startfile(path)

    def approve_contours(self):
        order = self.selected_order()
        if not order or not order.output_dir:
            return
        report_path = Path(order.output_dir) / "job.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if not report.get("sheet_previews"):
            messagebox.showwarning("Нет предпросмотров", "Подготовьте заказ этой версией Печатника.")
            return
        if report.get("contour_review_approved"):
            return
        if not messagebox.askyesno("Утвердить контуры", "Вы просмотрели каждый печатный лист со всеми красными линиями реза?\n\n"
                                  "Утвердить именно эти контуры для печати и резки?"):
            return
        try:
            report["approved_files_sha256"] = approved_file_hashes(Path(order.output_dir), report)
        except CutPlanError as exc:
            messagebox.showerror("Не удалось утвердить листы", str(exc))
            return
        report["contour_review_approved"] = True
        report["status"] = "ready_to_print"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        order.status = OrderStatus.READY_TO_PRINT
        self.store.save(order, "sheet_contours_approved", {"previews": report["sheet_previews"]})
        self.refresh_orders()

    def show_direct_cut_plan(self):
        order = self.selected_order()
        if not order or not order.output_dir:
            messagebox.showwarning("Нет задания", "Сначала подготовьте заказ.")
            return
        try:
            paths = write_order_cut_plans(Path(order.output_dir))
            os.startfile(paths[0])
            messagebox.showinfo(
                "Черновой план прямой резки",
                f"Создано планов: {len(paths)}. Открыт первый; остальные лежат в папке заказа.\n\n"
                "Это только проверка последовательности движений. Начало координат и поиск меток "
                "ещё не откалиброваны; плоттеру ничего не отправлено.",
            )
        except (CutPlanError, OSError) as exc:
            messagebox.showerror("План не создан", str(exc))

    def _handle_preflight(self, order: Order, exc: PreflightError, opaque: set[str]):
        self.busy = False
        self.set_banner("Нужна проверка")
        if opaque:
            ids = ", ".join(sorted(opaque))
            if messagebox.askyesno("Непрозрачный фон", f"У {ids} нет прозрачного фона.\n\nВырезать эти изображения прямоугольником?"):
                self.busy = True
                self.set_banner("Подготовка прямоугольного реза…")
                threading.Thread(target=self._prepare_worker, args=(order, opaque), daemon=True).start()
                return
        order.status = OrderStatus.ERROR
        order.error = str(exc)
        self.store.save(order, "preflight_failed")
        self.refresh_orders()

    def _show_error(self, title: str, text: str):
        self.busy = False
        self.set_banner("Ошибка")
        self.refresh_orders()
        threading.Thread(target=self._alarm, daemon=True).start()
        messagebox.showerror(title, text)

    @staticmethod
    def _alarm():
        try:
            for frequency in (880, 660, 880):
                winsound.Beep(frequency, 280)
        except RuntimeError:
            winsound.MessageBeep(winsound.MB_ICONHAND)

    def _scheduler(self) -> EquipmentScheduler:
        devices = []
        for raw in self.registry.all():
            devices.append(Device(
                raw["device_id"], DeviceKind(raw["kind"]), DeviceStatus(raw["status"]),
                frozenset(raw.get("roles", [])), frozenset(raw.get("approved_materials", [])),
                frozenset(raw.get("approved_profiles", [])),
            ))
        scheduler = EquipmentScheduler(devices)
        for existing in self.store.list_assignments():
            for key in ("printer_segments", "cutter_segments"):
                for segment in existing.get(key, []):
                    device_id = segment.get("device_id")
                    if device_id in scheduler.queued_sheets:
                        scheduler.queued_sheets[device_id] += max(0, int(segment["last_sheet"]) - int(segment["first_sheet"]) + 1)
        return scheduler

    def _assigned_printer_name(self, order: Order) -> str | None:
        assignment = self.store.get_assignment(order.order_id) or {}
        segments = assignment.get("printer_segments", [])
        if not segments:
            return None
        device_id = segments[-1]["device_id"]
        device = next((item for item in self.registry.all() if item["device_id"] == device_id), None)
        return device.get("windows_printer_name") if device else None

    def _assign_equipment(self, order: Order):
        current = self.store.get_assignment(order.order_id) or {}
        payload_hash = current.get("payload_hash")
        profile = "internal_holes_b_plus"
        scheduler = self._scheduler()
        assignment = scheduler.assign_order(order.order_id, order.sheet_count, order.material_id, profile)
        payload = {
            "order_id": assignment.order_id, "total_sheets": assignment.total_sheets,
            "printer_segments": [segment.__dict__ for segment in assignment.printer_segments],
            "cutter_segments": [segment.__dict__ for segment in assignment.cutter_segments],
        }
        if payload_hash:
            payload["payload_hash"] = payload_hash
        self.store.save_assignment(order.order_id, payload)

    def emergency_transfer(self):
        order = self.selected_order()
        if not order:
            return
        assignment = self.store.get_assignment(order.order_id)
        if not assignment or "total_sheets" not in assignment:
            messagebox.showwarning("Нет назначения", "Сначала скомпонуйте заказ.")
            return
        kind_text = simpledialog.askstring("Аварийный перенос", "Что сломалось: printer или cutter?", parent=self)
        if kind_text not in {"printer", "cutter"}:
            return
        profile = "internal_holes_b_plus"
        candidates = [d["device_id"] for d in self.registry.all()
                      if d["kind"] == kind_text and d["status"] == "ready"
                      and order.material_id in d.get("approved_materials", [])
                      and (kind_text == "printer" or profile in d.get("approved_profiles", []))]
        new_id = simpledialog.askstring("Новое устройство", "Готовые устройства: " + ", ".join(candidates), parent=self)
        if not new_id:
            return
        new_id = new_id.strip().upper()
        if new_id not in candidates:
            messagebox.showerror("Перенос запрещён", "Устройство не готово либо не откалибровано для материала и профиля этого заказа.")
            return
        last = simpledialog.askinteger("Последний готовый лист", f"Последний достоверно обработанный лист (0–{order.sheet_count})", minvalue=0, maxvalue=order.sheet_count, parent=self)
        if last is None:
            return
        key = "printer_segments" if kind_text == "printer" else "cutter_segments"
        source = assignment[key][-1]
        source["last_sheet"] = last
        if last < order.sheet_count:
            assignment[key].append({"device_id": new_id.strip().upper(), "first_sheet": last + 1, "last_sheet": order.sheet_count, "reason": "emergency_transfer"})
        self.store.save_assignment(order.order_id, assignment)
        self.store.save(order, "emergency_transfer", {"kind": kind_text, "new_device": new_id, "last_confirmed_sheet": last})
        messagebox.showinfo("Перенос записан", f"Оставшиеся листы начнутся с № {last + 1}. Номер заказа сохранён.")

    def print_selected(self):
        order = self.selected_order()
        if not order or not order.output_dir:
            messagebox.showwarning("Сначала подготовьте заказ", "Нужен готовый производственный пакет.")
            return
        material = self.materials[order.material_id]
        report = json.loads((Path(order.output_dir) / "job.json").read_text(encoding="utf-8"))
        if not report.get("sheet_previews") or not report.get("contour_review_approved", False):
            messagebox.showwarning("Проверьте контуры", "Откройте и утвердите контуры всех листов перед печатью.")
            return
        if not messagebox.askyesno("Печать", f"{material.print_side_instruction}\n\n"
                                  f"В драйвере выберите: {material.printer_media_type}, качество «{material.quality}».\n"
                                  f"Листов: {order.sheet_count}. Откройте PDF и напечатайте на Epson в масштабе 100%. Продолжить?"):
            return
        try:
            os.startfile(report["print_pdf"])
            order.status = OrderStatus.PRINTING
            self.store.save(order, "print_pdf_opened", {"pdf": report["print_pdf"]})
            self.refresh_orders()
            if messagebox.askyesno("Печать", "Вы напечатали все листы из открытого PDF без ошибки, в масштабе 100%?"):
                order.status = OrderStatus.PRINTED_WAITING_CUT
                self.store.save(order, "print_confirmed")
                self.refresh_orders()
        except Exception as exc:
            self._show_error("Не удалось передать печать", str(exc))

    def cut_selected(self):
        order = self.selected_order()
        if not order or not order.output_dir:
            messagebox.showwarning("Нет задания", "Сначала подготовьте заказ.")
            return
        material = self.materials[order.material_id]
        report = json.loads((Path(order.output_dir) / "job.json").read_text(encoding="utf-8"))
        if not report.get("sheet_previews") or not report.get("contour_review_approved", False):
            messagebox.showwarning("Проверьте контуры", "Откройте и утвердите контуры всех листов перед резкой.")
            return
        if not report.get("cut_dxf_files"):
            messagebox.showwarning("Нет DXF", "Задание создано старой версией. Подготовьте его заново.")
            return
        try:
            open_silhouette_bridge(Path(order.output_dir))
            order.status = OrderStatus.PAUSED
            self.store.save(order, "silhouette_basic_pilot_opened")
            self.refresh_orders()
            first_bounds = report.get("cut_bounds_mm", [None])[0]
            bounds_text = (f"Контрольная рамка контуров первого листа: {first_bounds['width']:.2f} × {first_bounds['height']:.2f} мм, "
                           f"левый/верхний край {first_bounds['left']:.2f}/{first_bounds['top']:.2f} мм.\n"
                           if first_bounds else "")
            messagebox.showinfo(
                "Пробный импорт в Silhouette Basic",
                "Studio и папка заказа открыты. Импортируйте sheet-XX-cut-basic-UNVERIFIED.dxf, "
                "включите регистрационные метки A4 без коврика: 10 мм сверху/сбоку, 25 мм снизу.\n"
                + bounds_text + "После импорта проверьте размер и положение контуров относительно напечатанного листа. "
                "DXF может импортироваться с изменённым масштабом — резать без проверки нельзя.\n\n"
                + f"Последний успешный опыт: вылет {material.blade}, сила {material.force}, скорость {material.speed}, "
                + f"проходов {material.passes}. Настройки подтвердите на пробном листе.",
            )
        except Exception as exc:
            self._show_error("Не удалось открыть Silhouette Studio", str(exc))

    def direct_cut_selected(self):
        order = self.selected_order()
        if not order or not order.output_dir or self.busy:
            messagebox.showwarning("Нет готового листа", "Сначала подготовьте и напечатайте заказ.")
            return
        if order.status not in {OrderStatus.PRINTED_WAITING_CUT, OrderStatus.LOADED_FOR_CUT}:
            messagebox.showwarning("Лист ещё не напечатан", "Сначала подтвердите печать листа в Печатнике.")
            return
        sheet_no = simpledialog.askinteger("Прямой USB-рез", f"Номер листа (1–{order.sheet_count})",
                                           parent=self, minvalue=1, maxvalue=order.sheet_count,
                                           initialvalue=1)
        if sheet_no is None:
            return
        try:
            preview = prepare_direct_sheet(Path(order.output_dir), sheet_no)
        except CutPlanError as exc:
            messagebox.showerror("Прямой рез остановлен", str(exc))
            return
        if not messagebox.askyesno(
            "Пробный прямой рез",
            f"Заказ {preview.order_id}, лист {sheet_no}. Контуров: {preview.contour_count}.\n"
            f"Команд: {preview.command_count}. Печатный PDF и контуры совпали с утверждёнными.\n\n"
            "Проверь: это НОВЫЙ лист из этого PDF, контрольная линия 50 мм, "
            "та же матовая самоклейка без коврика, печатной стороной вверх. "
            "AutoBlade плотно закреплён в первом гнезде; Cameo показывает «Готово», "
            "Silhouette Studio закрыта.\n\n"
            "Печатник найдёт четыре метки и вырежет только выбранный лист "
            "(нож 1, сила 4, скорость 4, один проход). Повтор этой попытки будет заблокирован. Начать?",
            parent=self,
        ):
            return
        self.busy = True
        self.direct_cut_button.configure(state="disabled")
        self.set_banner(f"Пробный прямой рез листа {sheet_no}…")

        def worker():
            try:
                result = run_direct_order_sheet(Path(order.output_dir), sheet_no)
                error = None
            except CameoConnectionError as exc:
                result, error = None, str(exc)

            def finish():
                self.busy = False
                self.direct_cut_button.configure(state="normal")
                if error:
                    self._show_error("Прямой рез не подтверждён", error + "\n\nОсмотри лист перед любым повтором.")
                    return
                if result["status"] != "cut_device_ready":
                    self.set_banner("Поиск меток или завершение реза не подтверждены")
                    messagebox.showwarning("Прямой рез не подтверждён",
                                           "Осмотри лист. Повтор этого задания заблокирован.", parent=self)
                    return
                self.store.save(order, "direct_usb_sheet_sent", {"sheet_no": sheet_no,
                                "command_count": preview.command_count,
                                "print_sha256": preview.print_sha256,
                                "cut_sha256": preview.cut_sha256})
                self.set_banner("Рез отправлен; проверь наклейки и подложку")
                messagebox.showinfo("Прямой рез завершён",
                                    "Cameo сообщил «Готово». Выгрузи лист, проверь все наклейки и подложку. "
                                    "После осмотра нажми «Учесть рез листа». Повторная отправка заблокирована.",
                                    parent=self)

            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def confirm_cut_sheet(self):
        order = self.selected_order()
        if not order or not order.output_dir:
            messagebox.showwarning("Нет задания", "Сначала подготовьте заказ.")
            return
        report_path = Path(order.output_dir) / "job.json"
        if not report_path.exists():
            messagebox.showerror("Нет макета", "Не найден расчёт линий реза для заказа.")
            return
        report = json.loads(report_path.read_text(encoding="utf-8"))
        lengths = report.get("cut_length_mm_per_sheet")
        if not lengths or len(lengths) != order.sheet_count:
            messagebox.showerror("Нет расчёта", "Этот макет создан старой версией. Подготовьте его заново до резки.")
            return
        completed = self.store.completed_cut_sheets(order.order_id)
        next_sheet = next((number for number in range(1, order.sheet_count + 1) if number not in completed), 1)
        sheet_no = simpledialog.askinteger("Учесть рез листа", f"Номер листа (1–{order.sheet_count})",
                                           parent=self, initialvalue=next_sheet,
                                           minvalue=1, maxvalue=order.sheet_count)
        if sheet_no is None:
            return
        repeat = sheet_no in completed
        if repeat and not messagebox.askyesno("Повторная резка", f"Лист №{sheet_no} уже учтён. Он действительно вырезан повторно?"):
            return
        assignment = self.store.get_assignment(order.order_id) or {}
        cutter_id = next((segment["device_id"] for segment in assignment.get("cutter_segments", [])
                          if segment["first_sheet"] <= sheet_no <= segment["last_sheet"]), self.cutter_choice.get())
        if not cutter_id:
            messagebox.showerror("Плоттер не выбран", "Назначьте плоттер перед учётом резки.")
            return
        result = messagebox.askyesnocancel(
            "Результат резки", f"Лист №{sheet_no} · плоттер {cutter_id}\n"
            f"Длина по макету: {lengths[sheet_no - 1] / 1000:.2f} м.\n\n"
            "Да — весь лист прорезан. Нет — резка прервана. Отмена — не записывать.", parent=self,
        )
        if result is None:
            return
        fraction = 1.0
        if not result:
            percent = simpledialog.askfloat(
                "Прерванная резка", "Сколько примерно процентов линий нож успел пройти? (0–100)",
                parent=self, minvalue=0, maxvalue=100,
            )
            if percent is None:
                return
            fraction = percent / 100
        length_mm = round(lengths[sheet_no - 1] * fraction, 3)
        try:
            record = self.store.record_cut(order.order_id, sheet_no, cutter_id, order.material_id,
                                           length_mm, completed=bool(result), repeat=repeat)
        except ValueError as exc:
            messagebox.showerror("Рез не учтён", str(exc))
            return
        order.status = OrderStatus.CUTTING if result else OrderStatus.PAUSED
        self.store.save(order, "cut_recorded", {"sheet_no": sheet_no, "cutter_id": cutter_id,
                                                "length_mm": length_mm, "completed": bool(result),
                                                "attempt_no": record["attempt_no"]})
        self.refresh_orders()
        messagebox.showinfo("Рез учтён", f"Нож {cutter_id}: добавлено {length_mm / 1000:.2f} м.")

    def complete_selected(self):
        order = self.selected_order()
        if order and order.sheet_count < 1:
            messagebox.showwarning("Нет подготовленных листов", "Сначала подготовьте заказ.")
            return
        if order and self.store.completed_cut_sheets(order.order_id) != set(range(1, order.sheet_count + 1)):
            messagebox.showwarning("Есть неподтверждённые листы", "Подтвердите рез каждого листа перед завершением заказа.")
            return
        if order and messagebox.askyesno("Завершить заказ", f"Все листы {order.order_id} напечатаны и вырезаны?"):
            order.status = OrderStatus.COMPLETE
            self.store.save(order, "order_completed")
            self.refresh_orders()

    def open_selected_folder(self):
        order = self.selected_order()
        if order and order.output_dir:
            open_folder(Path(order.output_dir))

    def preview_selected(self):
        order = self.selected_order()
        if not order or not order.output_dir:
            messagebox.showwarning("Нет предпросмотра", "Сначала подготовьте заказ.")
            return
        report = json.loads((Path(order.output_dir) / "job.json").read_text(encoding="utf-8"))
        if report.get("print_pages"):
            os.startfile(report["print_pages"][0])


def main():
    app = PrintnikApp()
    app.mainloop()


if __name__ == "__main__":
    main()
