/* Millimetre-based layout geometry. Printer margins, registration marks and
 * cut-contour rules still require Epson L8050 / Cameo 5 Alpha calibration.
 * Rectangles conservatively reserve space around future cut contours. */
(function (root) {
  const config = {
    sheet: { width: 210, height: 297 },
    margins: { top: 12, right: 12, bottom: 12, left: 12 },
    technicalHeight: 12, gap: 4, maxSheets: 7,
    // A-D are square bounding boxes. E uses the whole calibrated work area.
    sizes: { A: 15, B: 25, C: 50, D: 100, E: 'sheet' }
  };
  function validQuantity(value) {
    return String(value).trim() !== '' && Number.isSafeInteger(Number(value)) && Number(value) > 0;
  }
  function area(c = config) {
    return { x: c.margins.left, y: c.margins.top,
      w: c.sheet.width - c.margins.left - c.margins.right,
      h: c.sheet.height - c.margins.top - c.margins.bottom - c.technicalHeight };
  }
  function sizeBox(size, c = config) {
    const definition = c.sizes[size];
    if (definition === 'sheet') {
      const a = area(c);
      return { width: a.w, height: a.h };
    }
    if (!(definition > 0 && Number.isFinite(definition))) throw new Error('Invalid sticker size');
    return { width: definition, height: definition };
  }
  function dimensions(size, aspect, c = config) {
    if (!(aspect > 0 && Number.isFinite(aspect))) throw new Error('Invalid sticker aspect ratio');
    const box = sizeBox(size, c);
    const width = Math.min(box.width, box.height * aspect);
    return { width, height: width / aspect };
  }
  // MaxRects, largest first: a packing heuristic, not a global optimum.
  function pack(items, c = config) {
    const a = area(c), pages = [];
    const sorted = items.map(item => {
      const { width: w, height: h } = dimensions(item.size, item.aspect, c);
      return { ...item, w, h };
    }).sort((x, y) => y.w * y.h - x.w * x.h || x.id - y.id);
    for (const item of sorted) {
      let best;
      function search(page, index) {
        for (const f of page.free) for (const rotated of [false, true]) {
          const w = (rotated ? item.h : item.w) + c.gap, h = (rotated ? item.w : item.h) + c.gap;
          if (w > f.w + 1e-8 || h > f.h + 1e-8) continue;
          const score = Math.min(f.w - w, f.h - h);
          if (!best || score < best.score) best = { index, x: f.x, y: f.y, w, h, rotated, score };
        }
      }
      for (let i = 0; i < pages.length; i++) { search(pages[i], i); if (best) break; }
      if (!best) {
        if (pages.length >= c.maxSheets) return { ok: false, reason: 'limit' };
        const page = { free: [{ ...a, w: a.w + c.gap, h: a.h + c.gap }], placements: [] };
        search(page, pages.length);
        if (!best) return { ok: false, reason: 'oversize' };
        pages.push(page);
      }
      const page = pages[best.index], next = [];
      for (const f of page.free) {
        const r = best;
        if (r.x >= f.x + f.w || r.x + r.w <= f.x || r.y >= f.y + f.h || r.y + r.h <= f.y) { next.push(f); continue; }
        if (r.x > f.x) next.push({ ...f, w: r.x - f.x });
        if (r.x + r.w < f.x + f.w) next.push({ ...f, x: r.x + r.w, w: f.x + f.w - r.x - r.w });
        if (r.y > f.y) next.push({ ...f, h: r.y - f.y });
        if (r.y + r.h < f.y + f.h) next.push({ ...f, y: r.y + r.h, h: f.y + f.h - r.y - r.h });
      }
      page.free = next.filter((f, i) => !next.some((g, j) => i !== j && g.x <= f.x && g.y <= f.y && g.x + g.w >= f.x + f.w && g.y + g.h >= f.y + f.h && (j < i || g.x !== f.x || g.y !== f.y || g.w !== f.w || g.h !== f.h)));
      page.placements.push({ ...item, x: best.x, y: best.y, width: best.w - c.gap, height: best.h - c.gap, rotated: best.rotated });
    }
    return { ok: true, pages: pages.map(p => p.placements) };
  }
  function fitAddition(existing, sticker, quantity, nextId, c = config) {
    if (!validQuantity(quantity)) throw new Error('Invalid quantity');
    quantity = Number(quantity);
    const single = pack([{ ...sticker, id: nextId }], c);
    if (!single.ok) return { added: [], remaining: quantity, reason: single.reason };
    const a = area(c), stickerDimensions = dimensions(sticker.size, sticker.aspect, c);
    const stickerArea = stickerDimensions.width * stickerDimensions.height;
    const occupied = existing.reduce((sum, item) => {
      const itemDimensions = dimensions(item.size, item.aspect, c);
      return sum + itemDimensions.width * itemDimensions.height;
    }, 0);
    // Bound work by physical capacity, even for enormous requested quantities.
    const upper = Math.min(quantity, Math.max(0, Math.floor((a.w * a.h * c.maxSheets - occupied) / stickerArea + 1e-8)));
    // Descending search: heuristic packing need not be monotonic across counts.
    // Keep every existing item; accept the largest batch our packer can place.
    for (let count = upper; count > 0; count--) {
      const added = Array.from({ length: count }, (_, i) => ({ ...sticker, id: nextId + i }));
      const result = pack([...existing, ...added], c);
      if (result.ok) return { added, pages: result.pages, remaining: quantity - count };
    }
    return { added: [], remaining: quantity, reason: 'limit' };
  }
  const api = { config, area, sizeBox, dimensions, pack, validQuantity, fitAddition };
  if (typeof module !== 'undefined') module.exports = api;
  else root.StickerLayout = api;
})(globalThis);
