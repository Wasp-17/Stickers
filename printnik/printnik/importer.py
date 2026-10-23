from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import Order, OrderItem
from .prototype import SIZES_MM
from .storage import OrderStore


def payload_hash(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def order_from_payload(payload: dict, source: str) -> Order:
    order_id = str(payload.get("public_order_id") or payload.get("order_id") or "").strip()
    if not order_id:
        raise ValueError("В задании нет номера заказа")
    items = []
    for raw in payload.get("items", []):
        size = str(raw.get("size") or raw.get("size_code") or "").upper()
        if size not in SIZES_MM:
            raise ValueError(f"Неверный размер у {raw.get('asset_id', 'позиции')}")
        quantity = int(raw.get("quantity", 0))
        if quantity < 1:
            raise ValueError("Количество должно быть больше нуля")
        items.append(OrderItem(str(raw["asset_id"]).upper(), size, quantity))
    if not items:
        raise ValueError("В заказе нет наклеек")
    return Order(order_id, str(payload.get("material_id", "matte_white")), items=items,
                 source=source, address=payload.get("address"))


def import_payload(store: OrderStore, payload: dict, source: str) -> tuple[Order, bool]:
    order = order_from_payload(payload, source)
    digest = payload_hash(payload)
    existing = store.get(order.order_id)
    if existing:
        # Один ID не превращается в повторную печать. Другой payload требует ручной проверки.
        previous = store.get_assignment(order.order_id) or {}
        if previous.get("payload_hash") not in (None, digest):
            raise ValueError(f"Заказ {order.order_id} уже существует с другим содержимым")
        return existing, False
    store.save(order, "order_imported", {"source": source, "payload_hash": digest})
    store.save_assignment(order.order_id, {"payload_hash": digest})
    return order, True


def scan_inbox(store: OrderStore, inbox: Path) -> list[tuple[Path, str]]:
    inbox.mkdir(parents=True, exist_ok=True)
    processed = inbox / "processed"
    rejected = inbox / "rejected"
    processed.mkdir(exist_ok=True)
    rejected.mkdir(exist_ok=True)
    results = []
    for path in sorted(inbox.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            _, created = import_payload(store, payload, f"inbox:{path.name}")
            destination = processed / path.name
            path.replace(destination)
            results.append((destination, "добавлен" if created else "повтор подтверждён"))
        except Exception as exc:
            destination = rejected / path.name
            path.replace(destination)
            (destination.with_suffix(destination.suffix + ".error.txt")).write_text(str(exc), encoding="utf-8")
            results.append((destination, f"ошибка: {exc}"))
    return results

