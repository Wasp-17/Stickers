(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CatalogSearch = api;
})(globalThis, function () {
  function normalize(value) {
    return String(value || '').normalize('NFC').trim().toLocaleUpperCase('ru').replaceAll('Ё', 'Е').replace(/\s+/g, ' ');
  }
  function createEngine(catalog, dictionary) {
    const concepts = new Map(dictionary.concepts.map(concept => [concept.concept_id, concept]));
    const byCanonical = new Map();
    for (const concept of dictionary.concepts) {
      const key = normalize(concept.canonical);
      if (!byCanonical.has(key)) byCanonical.set(key, []);
      byCanonical.get(key).push(concept.concept_id);
    }
    const morphology = new Map((dictionary.rules.morphology_resolutions || []).map(item => [normalize(item.surface), item.concept_id]));
    const adjacency = new Map();
    function connect(from, relation, to, constraints) {
      if (!adjacency.has(from)) adjacency.set(from, []);
      adjacency.get(from).push({ relation, to, constraints });
    }
    for (const edge of dictionary.relations) {
      connect(edge.from, edge.relation, edge.to, edge.constraints);
      if (['SYNONYM','COLLOQUIAL','RELATED'].includes(edge.relation)) connect(edge.to, edge.relation, edge.from, edge.constraints);
    }
    const normalizedEntries = catalog.entries.map((entry, order) => ({
      ...entry,
      order,
      conceptSet: new Set(entry.concept_ids),
      normalizedText: entry.search_text.map(normalize),
      normalizedName: normalize(entry.display_name),
    }));
    const characterNames = new Map(catalog.filters.characters.map(item => [normalize(item.label), item.value]));
    const relationScores = { SYNONYM: 430, COLLOQUIAL: 400, NARROWER: 280, BROADER: 180, RELATED: 80 };

    function queryConcepts(query) {
      const exact = byCanonical.get(query);
      if (exact) return [...exact];
      if (morphology.has(query)) return [morphology.get(query)];
      const padded = ` ${query} `;
      const found = [];
      for (const [canonical, ids] of byCanonical) {
        if (canonical.length >= 3 && padded.includes(` ${canonical} `)) found.push(...ids);
      }
      return [...new Set(found)];
    }
    function conditionalAllowed(edge, queryIds, entry) {
      if (!edge.constraints) return true;
      const context = new Set(edge.constraints.context_any_concept_ids || []);
      return queryIds.some(id => context.has(id)) || [...entry.conceptSet].some(id => context.has(id));
    }
    function exactFilter(entry, filters) {
      if (filters.section && !entry.sections.includes(filters.section)) return false;
      if (filters.character && entry.character_id !== filters.character) return false;
      if (filters.role && !(entry.field_concepts.role || []).includes(filters.role)) return false;
      if (filters.mood && !(entry.field_concepts.mood || []).includes(filters.mood)) return false;
      return true;
    }
    function hardRequirementPasses(entry, query, queryIds) {
      const characterId = characterNames.get(query);
      if (characterId && entry.character_id !== characterId) return false;
      if (!byCanonical.has(query)) return true;
      for (const id of queryIds) {
        const concept = concepts.get(id);
        if (concept.concept_type === 'THEME' && !(entry.field_concepts.themes || []).includes(id)) return false;
        if (concept.concept_type === 'SUBJECT') {
          const primary = new Set(entry.field_concepts.primary_subjects || []);
          if (primary.has(id)) continue;
          const narrower = (adjacency.get(id) || []).filter(edge => edge.relation === 'NARROWER').map(edge => edge.to);
          if (!narrower.some(candidate => primary.has(candidate))) return false;
        }
      }
      return true;
    }
    function run(rawQuery, filters = {}) {
      const query = normalize(rawQuery);
      const queryIds = query ? queryConcepts(query) : [];
      const results = [];
      for (const entry of normalizedEntries) {
        if (!exactFilter(entry, filters)) continue;
        if (!query) { results.push({ entry, score: 0, reasons: ['FILTER'] }); continue; }
        if (!hardRequirementPasses(entry, query, queryIds)) continue;
        let score = 0;
        const reasons = [];
        if (entry.normalizedName === query) { score += 1200; reasons.push('DISPLAY_NAME_EXACT'); }
        else if (entry.normalizedName.includes(query)) { score += 850; reasons.push('DISPLAY_NAME'); }
        if (entry.normalizedText.some(text => text === query)) { score += 700; reasons.push('DIRECT_TEXT_EXACT'); }
        else if (entry.normalizedText.some(text => text.includes(query))) { score += 520; reasons.push('DIRECT_TEXT'); }
        if (characterNames.get(query) === entry.character_id) { score += 900; reasons.push('CHARACTER'); }
        for (const queryId of queryIds) {
          if (entry.conceptSet.has(queryId)) { score += 600; reasons.push('DIRECT_CONCEPT'); continue; }
          let best = 0;
          let bestRelation = null;
          for (const edge of adjacency.get(queryId) || []) {
            if (!entry.conceptSet.has(edge.to) || !conditionalAllowed(edge, queryIds, entry)) continue;
            const edgeScore = relationScores[edge.relation] || 0;
            if (edgeScore > best) { best = edgeScore; bestRelation = edge.relation; }
          }
          if (best) { score += best; reasons.push(bestRelation); }
        }
        if (score > 0) results.push({ entry, score, reasons: [...new Set(reasons)] });
      }
      results.sort((a, b) => b.score - a.score || a.entry.order - b.entry.order);
      return results;
    }
    return { run, normalize };
  }
  return { normalize, createEngine };
});
