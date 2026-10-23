from __future__ import annotations

import json
from pathlib import Path

POLICIES = {"standard", "recommend_a1", "min_a1"}


def load_size_rules(path: Path) -> dict[str, dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("rules"), dict):
        raise ValueError("Неверный формат правил размеров")
    result = {}
    for asset_id, rule in payload["rules"].items():
        if not isinstance(rule, dict) or rule.get("a_policy") not in POLICIES:
            raise ValueError(f"Неверное правило размера у {asset_id}")
        if rule["a_policy"] != "standard" and not str(rule.get("reason", "")).strip():
            raise ValueError(f"У правила {asset_id} не указана причина")
        result[str(asset_id).upper()] = rule
    return result


def validate_size_rule(asset_id: str, size_code: str, rules: dict[str, dict]) -> str | None:
    rule = rules.get(asset_id.upper(), {})
    policy = rule.get("a_policy", "standard")
    if size_code == "A" and policy == "min_a1":
        raise ValueError(f"{asset_id}: размер A недоступен; минимальный размер A1 (35 × 35 мм). {rule['reason']}")
    if size_code == "A" and policy == "recommend_a1":
        return f"{asset_id}: рекомендуем A1 (35 × 35 мм) для точного контура. {rule['reason']}"
    return None
