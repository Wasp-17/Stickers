(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CatalogSearch = api;
})(globalThis, function () {
  function normalize(value) {
    return String(value || '').normalize('NFC').trim().toLocaleUpperCase('ru').replaceAll('Ё', 'Е').replace(/\s+/g, ' ');
  }
  function words(value) {
    return normalize(value).match(/[A-ZА-Я0-9]+/g) || [];
  }
  function russianStem(word) {
    if (!/^[А-Я]+$/.test(word) || word.length < 4) return word;
    const endings = [
      'ИЯМИ','ЯМИ','АМИ','ЕГО','ОГО','ЕМУ','ОМУ','ИМИ','ЫМИ','ИХ','ЫХ','АЯ','ЯЯ','ОЕ','ЕЕ','ЫЕ','ИЕ','ОЙ','ЕЙ','ИЙ','ЫЙ',
      'ОВ','ЕВ','АМ','ЯМ','АХ','ЯХ','ОМ','ЕМ','УЮ','ЮЮ','ЫЙ','ОЮ','ЕЮ','ИЯ','ЬЯ','ИЯХ','ИЯМ','ИЮ','ЬЮ',
      'А','Я','Ы','И','У','Ю','Е','О','Й','Ь'
    ];
    for (const ending of endings) {
      if (word.endsWith(ending) && word.length - ending.length >= 3) return word.slice(0, -ending.length);
    }
    return word;
  }
  function distanceAtMostOne(left, right) {
    if (left === right) return 0;
    if (left.length < 4 || right.length < 4 || Math.abs(left.length - right.length) > 1) return 2;
    let prefix = 0;
    while (prefix < left.length && prefix < right.length && left[prefix] === right[prefix]) prefix += 1;
    if (left.length === right.length) {
      if (prefix + 1 < left.length && left[prefix] === right[prefix + 1] && left[prefix + 1] === right[prefix] && left.slice(prefix + 2) === right.slice(prefix + 2)) return 1;
      return left.slice(prefix + 1) === right.slice(prefix + 1) ? 1 : 2;
    }
    const longer = left.length > right.length ? left : right;
    const shorter = left.length > right.length ? right : left;
    return longer.slice(prefix + 1) === shorter.slice(prefix) ? 1 : 2;
  }
  function containsTokenSequence(target, query) {
    if (!query.length || query.length > target.length) return false;
    for (let start = 0; start <= target.length - query.length; start += 1) {
      if (query.every((token, index) => token === target[start + index])) return true;
    }
    return false;
  }
  function fuzzyTokenMatch(targetTokens, queryTokens) {
    if (!queryTokens.length || queryTokens.length > targetTokens.length) return null;
    const targetStems = targetTokens.map(russianStem);
    const queryStems = queryTokens.map(russianStem);
    const used = new Set();
    let edits = 0;
    for (const queryStem of queryStems) {
      let selected = -1;
      let selectedDistance = 2;
      for (let index = 0; index < targetStems.length; index += 1) {
        if (used.has(index)) continue;
        const distance = distanceAtMostOne(queryStem, targetStems[index]);
        if (distance < selectedDistance) {
          selected = index;
          selectedDistance = distance;
          if (distance === 0) break;
        }
      }
      if (selected < 0 || selectedDistance > 1 || edits + selectedDistance > 1) return null;
      used.add(selected);
      edits += selectedDistance;
    }
    return edits;
  }
  function lexicalTier(target, query, queryTokens) {
    if (!query) return null;
    if (target === query) return 'EXACT';
    const targetTokens = words(target);
    if (containsTokenSequence(targetTokens, queryTokens)) return 'WHOLE_WORD';
    const fuzzy = fuzzyTokenMatch(targetTokens, queryTokens);
    if (fuzzy === 0) return 'MORPHOLOGY';
    if (fuzzy === 1) return 'TYPO';
    if (query.length >= 4 && target.includes(query)) return 'SUBSTRING';
    return null;
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
      const queryTokens = words(query);
      const queryIds = query ? queryConcepts(query) : [];
      const results = [];
      for (const entry of normalizedEntries) {
        if (!exactFilter(entry, filters)) continue;
        if (!query) { results.push({ entry, score: 0, reasons: ['FILTER'] }); continue; }
        if (!hardRequirementPasses(entry, query, queryIds)) continue;
        let score = 0;
        const reasons = [];
        const nameTier = lexicalTier(entry.normalizedName, query, queryTokens);
        const nameScores = { EXACT:10000, WHOLE_WORD:8500, MORPHOLOGY:7600, TYPO:6800, SUBSTRING:5600 };
        if (nameTier) { score += nameScores[nameTier]; reasons.push(`DISPLAY_NAME_${nameTier}`); }
        let textTier = null;
        const tierOrder = ['EXACT','WHOLE_WORD','MORPHOLOGY','TYPO','SUBSTRING'];
        for (const text of entry.normalizedText) {
          const candidate = lexicalTier(text, query, queryTokens);
          if (candidate && (!textTier || tierOrder.indexOf(candidate) < tierOrder.indexOf(textTier))) textTier = candidate;
        }
        const textScores = { EXACT:2200, WHOLE_WORD:1900, MORPHOLOGY:1650, TYPO:1400, SUBSTRING:1100 };
        if (textTier) { score += textScores[textTier]; reasons.push(`DIRECT_TEXT_${textTier}`); }
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
  return { normalize, words, russianStem, distanceAtMostOne, createEngine };
});
