from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import Order


def _font(size: int, bold: bool = False):
    names = [r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
             r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def address_lines(address: dict) -> list[str]:
    recipient = address.get("recipient") or address.get("full_name") or address.get("name") or ""
    postal = address.get("postal_code") or address.get("index") or ""
    value = address.get("formatted") or address.get("address") or ""
    if not value:
        parts = [address.get(key, "") for key in ("region", "city", "street", "house", "apartment")]
        value = ", ".join(str(part) for part in parts if part)
    result = [str(recipient).strip()] if recipient else []
    result.extend(textwrap.wrap(str(value), width=42))
    if postal:
        result.append(f"Индекс: {postal}")
    return result


def create_envelopes_pdf(orders: list[Order], output: Path, dpi: int = 300) -> Path:
    pages = []
    width, height = round(220 / 25.4 * dpi), round(110 / 25.4 * dpi)
    for order in orders:
        if not order.address:
            continue
        page = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(page)
        title = _font(round(4.0 / 25.4 * dpi), bold=True)
        body = _font(round(3.7 / 25.4 * dpi))
        x, y = round(95 / 25.4 * dpi), round(35 / 25.4 * dpi)
        draw.text((x, y), "ПОЛУЧАТЕЛЬ", fill="black", font=title)
        y += round(9 / 25.4 * dpi)
        for line in address_lines(order.address):
            draw.text((x, y), line, fill="black", font=body)
            y += round(6 / 25.4 * dpi)
        draw.text((round(10 / 25.4 * dpi), height - round(12 / 25.4 * dpi)), order.order_id, fill="#555", font=body)
        pages.append(page)
    if not pages:
        raise ValueError("Нет заказов с сохранённым адресом")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(output, "PDF", resolution=dpi, save_all=True, append_images=pages[1:])
    return output

