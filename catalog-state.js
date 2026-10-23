(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CatalogState = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const filterKeys = ['section', 'character', 'role', 'mood'];
  const knownKeys = ['q', ...filterKeys, 'scope', 'sort', 'shown', 'sticker', 'mix'];

  function read(search) {
    const params = new URLSearchParams(search || '');
    const filters = Object.fromEntries(filterKeys.map(key => [key, params.get(key) || '']));
    const shown = Number.parseInt(params.get('shown') || '', 10);
    return {
      query: params.get('q') || '',
      filters,
      scope: params.get('scope') === 'all' ? 'all' : 'selection',
      sort: ['relevance', 'name', 'catalog'].includes(params.get('sort')) ? params.get('sort') : 'relevance',
      shown: Number.isSafeInteger(shown) && shown > 0 ? shown : 0,
      sticker: params.get('sticker') || '',
      mix: /^[a-z0-9_-]{1,32}$/i.test(params.get('mix') || '') ? params.get('mix') : '',
    };
  }

  function write(search, state) {
    const params = new URLSearchParams(search || '');
    for (const key of knownKeys) params.delete(key);
    const query = String(state.query || '').trim();
    if (query) params.set('q', query);
    for (const key of filterKeys) if (state.filters?.[key]) params.set(key, state.filters[key]);
    if (query && state.scope === 'all') params.set('scope', 'all');
    if (state.sort && state.sort !== 'relevance') params.set('sort', state.sort);
    if (Number.isSafeInteger(state.shown) && state.shown > 0) params.set('shown', String(state.shown));
    if (state.sticker) params.set('sticker', state.sticker);
    if (state.mix) params.set('mix', String(state.mix));
    const value = params.toString();
    return value ? `?${value}` : '';
  }

  return { filterKeys, read, write };
});
