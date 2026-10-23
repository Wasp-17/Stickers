from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class OrderStatus(StrEnum):
    RECEIVED = "received"
    VALIDATED = "validated"
    COMPOSED = "composed"
    READY_TO_PRINT = "ready_to_print"
    PRINTING = "printing"
    PRINTED_WAITING_CUT = "printed_waiting_cut"
    LOADED_FOR_CUT = "loaded_for_cut"
    CUTTING = "cutting"
    COMPLETE = "complete"
    PAUSED = "paused"
    ERROR = "error"


STATUS_LABELS = {
    OrderStatus.RECEIVED: "Получен",
    OrderStatus.VALIDATED: "Проверен",
    OrderStatus.COMPOSED: "Скомпонован",
    OrderStatus.READY_TO_PRINT: "Готов к печати",
    OrderStatus.PRINTING: "Печатается",
    OrderStatus.PRINTED_WAITING_CUT: "Напечатан, ждёт резки",
    OrderStatus.LOADED_FOR_CUT: "Листы загружены в плоттер",
    OrderStatus.CUTTING: "Режется",
    OrderStatus.COMPLETE: "Готов",
    OrderStatus.PAUSED: "Приостановлен",
    OrderStatus.ERROR: "Ошибка",
}


@dataclass(frozen=True)
class OrderItem:
    asset_id: str
    size_code: str
    quantity: int


@dataclass
class Order:
    order_id: str
    material_id: str
    status: OrderStatus = OrderStatus.RECEIVED
    items: list[OrderItem] = field(default_factory=list)
    sheet_count: int = 0
    output_dir: str | None = None
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    source: str = "manual"
    address: dict | None = None

