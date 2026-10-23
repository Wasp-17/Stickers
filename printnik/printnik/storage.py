from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .models import Order, OrderItem, OrderStatus


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class OrderStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self._migrate()

    def _migrate(self):
        self.db.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                material_id TEXT NOT NULL,
                status TEXT NOT NULL,
                items_json TEXT NOT NULL,
                sheet_count INTEGER NOT NULL DEFAULT 0,
                output_dir TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                event TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(order_id)
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS blades (
                blade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cutter_id TEXT NOT NULL,
                installed_at TEXT NOT NULL,
                retired_at TEXT,
                retirement_reason TEXT,
                baseline_known INTEGER NOT NULL DEFAULT 1
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_blade_per_cutter
                ON blades(cutter_id) WHERE retired_at IS NULL;
            CREATE TABLE IF NOT EXISTS cut_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                sheet_no INTEGER NOT NULL,
                attempt_no INTEGER NOT NULL,
                cutter_id TEXT NOT NULL,
                blade_id INTEGER NOT NULL,
                material_id TEXT NOT NULL,
                length_mm REAL NOT NULL CHECK(length_mm >= 0),
                completed INTEGER NOT NULL CHECK(completed IN (0, 1)),
                recorded_at TEXT NOT NULL,
                UNIQUE(order_id, sheet_no, attempt_no),
                FOREIGN KEY(blade_id) REFERENCES blades(blade_id)
            );
            """
        )
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(orders)").fetchall()}
        if "source" not in columns:
            self.db.execute("ALTER TABLE orders ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'")
        if "address_json" not in columns:
            self.db.execute("ALTER TABLE orders ADD COLUMN address_json TEXT")
        blade_columns = {row[1] for row in self.db.execute("PRAGMA table_info(blades)").fetchall()}
        if "baseline_known" not in blade_columns:
            self.db.execute("ALTER TABLE blades ADD COLUMN baseline_known INTEGER NOT NULL DEFAULT 0")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS assignments (
                order_id TEXT PRIMARY KEY,
                assignment_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(order_id)
            )"""
        )
        self.db.commit()

    def close(self):
        self.db.close()

    def _row_to_order(self, row) -> Order:
        items = [OrderItem(**value) for value in json.loads(row["items_json"])]
        return Order(
            order_id=row["order_id"], material_id=row["material_id"],
            status=OrderStatus(row["status"]), items=items,
            sheet_count=row["sheet_count"], output_dir=row["output_dir"],
            error=row["error"], created_at=row["created_at"], updated_at=row["updated_at"],
            source=row["source"] if "source" in row.keys() else "manual",
            address=json.loads(row["address_json"]) if "address_json" in row.keys() and row["address_json"] else None,
        )

    def list_orders(self) -> list[Order]:
        with self.lock:
            rows = self.db.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
        return [self._row_to_order(row) for row in rows]

    def get(self, order_id: str) -> Order | None:
        with self.lock:
            row = self.db.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
        return self._row_to_order(row) if row else None

    def save(self, order: Order, event: str = "order_saved", details: dict | None = None):
        now = utc_now()
        created = order.created_at or now
        items_json = json.dumps([item.__dict__ for item in order.items], ensure_ascii=False)
        with self.lock:
            self.db.execute(
            """INSERT INTO orders(order_id,material_id,status,items_json,sheet_count,output_dir,error,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(order_id) DO UPDATE SET material_id=excluded.material_id,status=excluded.status,
               items_json=excluded.items_json,sheet_count=excluded.sheet_count,output_dir=excluded.output_dir,
               error=excluded.error,updated_at=excluded.updated_at""",
            (order.order_id, order.material_id, order.status.value, items_json, order.sheet_count,
             order.output_dir, order.error, created, now),
            )
            self.db.execute("UPDATE orders SET source=?, address_json=? WHERE order_id=?",
                            (order.source, json.dumps(order.address, ensure_ascii=False) if order.address else None, order.order_id))
            self.db.execute(
            "INSERT INTO events(order_id,event,details_json,created_at) VALUES(?,?,?,?)",
            (order.order_id, event, json.dumps(details or {}, ensure_ascii=False), now),
            )
            self.db.commit()
        order.created_at, order.updated_at = created, now

    def set_status(self, order_id: str, status: OrderStatus, *, error: str | None = None):
        order = self.get(order_id)
        if not order:
            raise KeyError(order_id)
        order.status = status
        order.error = error
        self.save(order, "status_changed", {"status": status.value, "error": error})

    def next_order_id(self) -> str:
        year = datetime.now().year
        prefix = f"RK-{year}-"
        with self.lock:
            row = self.db.execute(
            "SELECT order_id FROM orders WHERE order_id LIKE ? ORDER BY order_id DESC LIMIT 1",
            (prefix + "%",),
            ).fetchone()
        number = int(row[0].split("-")[-1]) + 1 if row else 1
        return f"{prefix}{number:06d}"

    def get_setting(self, key: str, default: str = "") -> str:
        with self.lock:
            row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        with self.lock:
            self.db.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
            )
            self.db.commit()

    def save_assignment(self, order_id: str, assignment: dict):
        now = utc_now()
        with self.lock:
            self.db.execute(
                "INSERT INTO assignments(order_id,assignment_json,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(order_id) DO UPDATE SET assignment_json=excluded.assignment_json,updated_at=excluded.updated_at",
                (order_id, json.dumps(assignment, ensure_ascii=False), now),
            )
            self.db.commit()

    def get_assignment(self, order_id: str) -> dict | None:
        with self.lock:
            row = self.db.execute("SELECT assignment_json FROM assignments WHERE order_id=?", (order_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_assignments(self) -> list[dict]:
        with self.lock:
            rows = self.db.execute("SELECT assignment_json FROM assignments").fetchall()
        return [json.loads(row[0]) for row in rows]

    def active_blade(self, cutter_id: str) -> dict | None:
        with self.lock:
            row = self.db.execute(
                "SELECT b.*, COALESCE(SUM(c.length_mm), 0) AS length_mm "
                "FROM blades b LEFT JOIN cut_records c ON c.blade_id=b.blade_id "
                "WHERE b.cutter_id=? AND b.retired_at IS NULL GROUP BY b.blade_id",
                (cutter_id,),
            ).fetchone()
        return dict(row) if row else None

    def ensure_blade(self, cutter_id: str) -> dict:
        with self.lock:
            blade = self.active_blade(cutter_id)
            if blade:
                return blade
            self.db.execute("INSERT INTO blades(cutter_id,installed_at,baseline_known) VALUES(?,?,0)",
                            (cutter_id, utc_now()))
            self.db.commit()
            return self.active_blade(cutter_id)

    def replace_blade(self, cutter_id: str, reason: str) -> dict:
        if reason not in {"worn", "other"}:
            raise ValueError("Укажите причину замены ножа")
        with self.lock:
            current = self.active_blade(cutter_id)
            if current is None:
                return self.ensure_blade(cutter_id)
            now = utc_now()
            self.db.execute("UPDATE blades SET retired_at=?,retirement_reason=? WHERE blade_id=?",
                            (now, reason, current["blade_id"]))
            self.db.execute("INSERT INTO blades(cutter_id,installed_at,baseline_known) VALUES(?,?,1)",
                            (cutter_id, now))
            self.db.commit()
            return self.active_blade(cutter_id)

    def record_cut(self, order_id: str, sheet_no: int, cutter_id: str, material_id: str,
                   length_mm: float, *, completed: bool, repeat: bool = False) -> dict:
        if sheet_no < 1 or not 0 <= length_mm < 1_000_000_000:
            raise ValueError("Неверный номер листа или длина реза")
        with self.lock:
            order = self.db.execute("SELECT sheet_count FROM orders WHERE order_id=?", (order_id,)).fetchone()
            if order is None or (order["sheet_count"] and sheet_no > order["sheet_count"]):
                raise ValueError("Лист не принадлежит этому заказу")
            previous = self.db.execute(
                "SELECT COALESCE(MAX(attempt_no),0) AS attempts, MAX(completed) AS completed "
                "FROM cut_records WHERE order_id=? AND sheet_no=?", (order_id, sheet_no),
            ).fetchone()
            if previous["completed"] and not repeat:
                raise ValueError("Рез этого листа уже учтён; для повторной резки выберите повтор")
            blade = self.ensure_blade(cutter_id)
            attempt = previous["attempts"] + 1
            self.db.execute(
                "INSERT INTO cut_records(order_id,sheet_no,attempt_no,cutter_id,blade_id,material_id,length_mm,completed,recorded_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (order_id, sheet_no, attempt, cutter_id, blade["blade_id"], material_id,
                 length_mm, int(completed), utc_now()),
            )
            self.db.commit()
            return {"attempt_no": attempt, "blade_id": blade["blade_id"], "length_mm": length_mm}

    def completed_cut_sheets(self, order_id: str) -> set[int]:
        with self.lock:
            rows = self.db.execute(
                "SELECT DISTINCT sheet_no FROM cut_records WHERE order_id=? AND completed=1", (order_id,),
            ).fetchall()
        return {row[0] for row in rows}

    def has_cut_records(self, order_id: str) -> bool:
        with self.lock:
            row = self.db.execute("SELECT 1 FROM cut_records WHERE order_id=? LIMIT 1", (order_id,)).fetchone()
        return row is not None

    def blade_history(self, cutter_id: str | None = None) -> list[dict]:
        with self.lock:
            blades = self.db.execute(
                "SELECT * FROM blades WHERE (? IS NULL OR cutter_id=?) ORDER BY blade_id DESC",
                (cutter_id, cutter_id),
            ).fetchall()
            result = []
            for blade in blades:
                usage = self.db.execute(
                    "SELECT material_id, SUM(length_mm) AS length_mm, COUNT(*) AS attempts "
                    "FROM cut_records WHERE blade_id=? GROUP BY material_id", (blade["blade_id"],),
                ).fetchall()
                result.append({**dict(blade), "by_material": {row["material_id"]: dict(row) for row in usage},
                               "total_mm": sum(row["length_mm"] for row in usage)})
        return result

