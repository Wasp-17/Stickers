from __future__ import annotations

import re


def path_points(path: str) -> list[tuple[float, float]]:
    return [(float(x), float(y)) for x, y in
            re.findall(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", path)]


def bounds(paths: list[tuple[float, str, float]]) -> dict[str, float] | None:
    points = [point for _, path, _ in paths for point in path_points(path)]
    if not points:
        return None
    xs, ys = zip(*points)
    return {"left": round(min(xs), 3), "top": round(min(ys), 3),
            "width": round(max(xs) - min(xs), 3), "height": round(max(ys) - min(ys), 3)}


def render_dxf(paths: list[tuple[float, str, float]], page_height_mm: float = 297) -> str:
    """DXF R13 polylines for Studio Basic; the operator must verify import scale."""
    tokens = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1012",
              "9", "$INSUNITS", "70", "4", "0", "ENDSEC",
              "0", "SECTION", "2", "ENTITIES"]
    for _, path, _ in paths:
        points = path_points(path)
        if len(points) < 3:
            continue
        tokens.extend(["0", "LWPOLYLINE", "100", "AcDbEntity", "8", "CUT",
                       "100", "AcDbPolyline", "90", str(len(points)), "70", "1"])
        for x, y in points:
            tokens.extend(["10", f"{x:.3f}", "20", f"{page_height_mm - y:.3f}"])
    tokens.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(tokens) + "\n"
