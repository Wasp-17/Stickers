from __future__ import annotations

import re
from pathlib import Path


ID_RE = re.compile(r"(RK17-\d{4})", re.IGNORECASE)


class AssetCatalog:
    def __init__(self, roots: list[Path]):
        self.roots = [Path(root) for root in roots]
        self._index: dict[str, Path] | None = None

    def refresh(self) -> dict[str, Path]:
        candidates: dict[str, list[tuple[int, Path]]] = {}
        priorities = {"MASTER": 0, "ART": 1}
        for root in self.roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in {".png", ".webp", ".jpg", ".jpeg"}:
                    continue
                match = ID_RE.search(path.name)
                if not match:
                    continue
                name = path.stem.upper()
                role = next((key for key in priorities if re.search(rf"(?:^|[_-]){key}(?:$|[_-])", name)), None)
                if role is None:
                    continue
                priority = priorities[role]
                candidates.setdefault(match.group(1).upper(), []).append((priority, path))
        self._index = {asset_id: sorted(paths, key=lambda item: (item[0], len(str(item[1]))))[0][1]
                       for asset_id, paths in candidates.items()}
        return self._index

    def resolve(self, asset_id: str) -> Path:
        index = self._index if self._index is not None else self.refresh()
        key = asset_id.strip().upper()
        if key not in index:
            raise FileNotFoundError(f"Не найден проверенный MASTER/ART для {key}; WEB и исходники для производства не используются")
        return index[key]

    def ids(self) -> list[str]:
        index = self._index if self._index is not None else self.refresh()
        return sorted(index)

