(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CatalogRanking = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function createSeed() {
    if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
      const values = new Uint32Array(2);
      crypto.getRandomValues(values);
      return `${values[0].toString(36)}${values[1].toString(36)}`;
    }
    return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 9)}`;
  }

  function hash(seed, value) {
    const text = `${seed}:${value}`;
    let result = 2166136261;
    for (let index = 0; index < text.length; index += 1) {
      result ^= text.charCodeAt(index);
      result = Math.imul(result, 16777619);
    }
    result += result << 13;
    result ^= result >>> 7;
    result += result << 3;
    result ^= result >>> 17;
    result += result << 5;
    return result >>> 0;
  }

  function semanticCategory(sticker) {
    const entry = sticker.entry || sticker;
    const fields = entry.field_concepts || {};
    return fields.role?.[0]
      || fields.mood?.[0]
      || fields.themes?.[0]
      || entry.character_id
      || entry.sections?.[0]
      || 'OTHER';
  }

  function diversify(items, maximumRun = 2, initialCategory = '', initialRun = 0) {
    const pending = [...items];
    const result = [];
    let lastCategory = initialCategory;
    let run = initialRun;
    while (pending.length) {
      let index = 0;
      if (lastCategory && run >= maximumRun) {
        const alternative = pending.findIndex(item => semanticCategory(item) !== lastCategory);
        if (alternative >= 0) index = alternative;
      }
      const [item] = pending.splice(index, 1);
      const category = semanticCategory(item);
      if (category === lastCategory) run += 1;
      else { lastCategory = category; run = 1; }
      result.push(item);
    }
    return { items:result, lastCategory, run };
  }

  function dateValue(sticker) {
    const entry = sticker.entry || sticker;
    const value = Date.parse(entry.added_at || entry.created_at || entry.published_at || '');
    return Number.isFinite(value) ? value : 0;
  }

  function statValue(stats, sticker) {
    const id = sticker.id || sticker.image_id || sticker.entry?.image_id;
    return stats?.[id] || {};
  }

  function hasPriority(sticker, stats) {
    const stat = statValue(stats, sticker);
    return Number(stat.paidOrders) > 0 || Number(stat.favoriteAdds) > 0 || dateValue(sticker) > 0;
  }

  function comparePriority(first, second, stats, seed) {
    const a = statValue(stats, first);
    const b = statValue(stats, second);
    return (Number(b.paidOrders) || 0) - (Number(a.paidOrders) || 0)
      || (Number(b.paidUnits) || 0) - (Number(a.paidUnits) || 0)
      || (Number(b.favoriteAdds) || 0) - (Number(a.favoriteAdds) || 0)
      || dateValue(second) - dateValue(first)
      || hash(seed, first.id || first.entry?.image_id) - hash(seed, second.id || second.entry?.image_id);
  }

  function rank(stickers, options = {}) {
    const seed = String(options.seed || 'catalog');
    const stats = options.stats || {};
    const reservedCount = Math.max(0, Math.min(12, Number(options.reservedCount) || 10));
    const maximumRun = Math.max(1, Number(options.maximumRun) || 2);
    const candidates = stickers.filter(sticker => hasPriority(sticker, stats));
    candidates.sort((a, b) => comparePriority(a, b, stats, seed));
    const reserved = candidates.slice(0, reservedCount);
    const reservedIds = new Set(reserved.map(sticker => sticker.id || sticker.entry?.image_id));
    const remaining = stickers.filter(sticker => !reservedIds.has(sticker.id || sticker.entry?.image_id));
    remaining.sort((a, b) => hash(seed, a.id || a.entry?.image_id) - hash(seed, b.id || b.entry?.image_id));
    const first = diversify(reserved, maximumRun);
    const rest = diversify(remaining, maximumRun, first.lastCategory, first.run);
    return [...first.items, ...rest.items];
  }

  return { createSeed, hash, semanticCategory, diversify, rank };
});
