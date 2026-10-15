const { config, area, pack, validQuantity, fitAddition } = StickerLayout;
const byId = id => document.getElementById(id);
const sizeDescriptions = { A: 'до 15 × 15 мм', B: 'до 25 × 25 мм', C: 'до 50 × 50 мм', D: 'до 100 × 100 мм', E: 'по рабочей области A4' };
let stickers = [];
let stickerById = new Map();
const sources = new Map();
const cardsById = new Map();
let searchEngine = null;
let defaultSection = '';
let appliedCriteria = null;
let visibleStickers = [];
let allMatches = [];
let loadedResultCount = 0;
const resultPageSize = 40;
let selectedStickerId = null;
let selectedSize = null, items = [], pages = [], active = 0, nextId = 1;
let pendingSheetDeletion = null;
let lastAddition = null;
let additionFeedbackTimer = null;
let inspectedItemId = null;
let inspectedRefreshCheckout = false;
let inspectedApplyAll = false;
let pendingInspectorSize = null;
let catalogPreviewStickerId = null;
let catalogPreviewEffects = {};
let currentOrderLoaded = false;
let activeCartOrder = null;
const addressFields = {
  recipient: 'delivery-recipient', phone: 'delivery-phone', country: 'delivery-country', postalCode: 'delivery-postal-code',
  region: 'delivery-region', city: 'delivery-city', street: 'delivery-street', house: 'delivery-house',
  apartment: 'delivery-apartment', comment: 'delivery-comment',
};

function readDeliveryAddress() {
  const address = Object.fromEntries(Object.entries(addressFields).map(([key, id]) => [key, byId(id).value.trim()]));
  return Object.values(address).some(Boolean) ? address : '';
}

function fillDeliveryAddress(address) {
  if (!address) address = {};
  if (typeof address === 'string') address = { street: address };
  for (const [key, id] of Object.entries(addressFields)) byId(id).value = address[key] || '';
}

function addressLabel(address) {
  return [address.city, [address.street, address.house].filter(Boolean).join(', '), address.recipient].filter(Boolean).join(' · ');
}

function refreshSavedAddresses(selectedId = '') {
  const signedIn = StickerStore.signedIn();
  const addresses = signedIn ? StickerStore.addresses() : [];
  byId('save-address-field').hidden = !signedIn;
  byId('saved-address-field').hidden = !addresses.length;
  const select = byId('saved-address');
  select.replaceChildren(new Option('Заполнить новый адрес', ''));
  for (const saved of addresses) select.add(new Option(addressLabel(saved.address), saved.id));
  select.value = addresses.some(saved => saved.id === selectedId) ? selectedId : '';
}

function persistCurrentOrder() {
  if (!currentOrderLoaded) return;
  StickerStore.saveCurrentOrder(items, readDeliveryAddress(), pages.length, activeCartOrder);
}

function restoreCurrentOrder() {
  const saved = StickerStore.currentOrder();
  const restored = saved.items.filter(item =>
    Number.isSafeInteger(item.id) && item.id > 0 &&
    stickerById.has(item.imageId) &&
    Object.hasOwn(config.sizes, item.size) &&
    Number.isFinite(item.aspect) && item.aspect > 0
  );
  const packed = pack(restored);
  items = packed.ok ? restored : [];
  pages = packed.ok ? packed.pages : [];
  nextId = items.reduce((largest, item) => Math.max(largest, item.id), 0) + 1;
  fillDeliveryAddress(saved.address);
  activeCartOrder = saved.cartOrder;
  refreshSavedAddresses();
  currentOrderLoaded = true;
  render();
}

function setCartExpanded(expanded) {
  const details = byId('order-details');
  details.hidden = !expanded;
  byId('order-toggle').setAttribute('aria-expanded', String(expanded));
  byId('order-toggle').setAttribute('aria-label', expanded ? 'Скрыть состав корзины' : 'Показать состав корзины');
}
byId('order-toggle').onclick = () => {
  const expanded = byId('order-toggle').getAttribute('aria-expanded') === 'true';
  setCartExpanded(!expanded);
};
byId('order-close').onclick = () => {
  setCartExpanded(false);
  byId('order-toggle').focus();
};

function orderSnapshot() {
  return { items, address: readDeliveryAddress(), sheetCount: pages.length };
}

function cartMetadata(order) {
  return { id:order.id, number:order.number, name:order.name, createdAt:order.createdAt };
}

function clearLayoutOrder() {
  items = []; pages = []; active = 0; nextId = 1; activeCartOrder = null;
  fillDeliveryAddress('');
  StickerStore.clearCurrentOrder();
}

function sendCurrentToCart(announce = true) {
  if (!items.length) return null;
  const saved = StickerStore.putCartOrder(orderSnapshot(), activeCartOrder);
  clearLayoutOrder();
  render();
  if (announce) message(`${saved.name} отправлен в корзину. Лист-макет очищен.`, 'success');
  return saved;
}

function loadCartOrder(id) {
  if (items.length) StickerStore.putCartOrder(orderSnapshot(), activeCartOrder);
  const saved = StickerStore.takeCartOrder(id);
  if (!saved) { renderCartOrders(); return; }
  items = saved.items;
  const packed = pack(items);
  pages = packed.ok ? packed.pages : [];
  if (!packed.ok) items = [];
  active = 0;
  nextId = items.reduce((largest, item) => Math.max(largest, item.id), 0) + 1;
  activeCartOrder = cartMetadata(saved);
  fillDeliveryAddress(saved.address);
  setCartExpanded(false);
  render();
  message(`${saved.name} открыт для редактирования.`, 'success');
}

function formatCartDate(value) {
  return new Intl.DateTimeFormat('ru', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' }).format(new Date(value));
}

function renderCartOrders() {
  const orders = StickerStore.cartOrders();
  const target = byId('order-items');
  target.replaceChildren();
  if (!orders.length) {
    const empty = document.createElement('p'); empty.className = 'cart-empty'; empty.textContent = 'Корзина пока пуста'; target.append(empty);
  }
  for (const order of orders) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'cart-order-button';
    const name = document.createElement('strong'); name.textContent = order.name;
    const details = document.createElement('span'); details.textContent = `${formatCartDate(order.createdAt)} · ${order.sheetCount || 1} лист. · ${order.items.length} накл.`;
    button.append(name, details); button.onclick = () => loadCartOrder(order.id); target.append(button);
  }
  byId('cart-count').textContent = String(orders.length);
}
function cancelSheetDeletion() {
  pendingSheetDeletion = null;
  byId('delete-confirmation').hidden = true;
}
byId('delete-sheet').onclick = () => {
  const current = pages[active];
  if (!current?.length) return;
  pendingSheetDeletion = { number: active + 1, ids: new Set(current.map(item => item.id)) };
  byId('delete-warning').textContent = `Удалить лист ${active + 1}? Из заказа будут удалены все наклейки этого листа (${current.length} шт.). Оставшиеся листы будут пересчитаны.`;
  byId('delete-confirmation').hidden = false;
  byId('cancel-delete-sheet').focus();
};
byId('cancel-delete-sheet').onclick = () => { cancelSheetDeletion(); byId('delete-sheet').focus(); };
byId('confirm-delete-sheet').onclick = () => {
  if (!pendingSheetDeletion) return;
  const { ids } = pendingSheetDeletion;
  items = items.filter(item => !ids.has(item.id));
  const result = pack(items);
  pages = result.ok ? result.pages : pages.map(page => page.filter(item => !ids.has(item.id))).filter(page => page.length);
  active = Math.min(active, Math.max(0, pages.length - 1));
  message(); render();
};
function message(text = '', tone = '', attention = false) {
  const catalogMessage = byId('message');
  catalogMessage.classList.remove('message-blink');
  catalogMessage.textContent = text;
  catalogMessage.dataset.attention = String(Boolean(text && attention));
  if (text && attention) {
    void catalogMessage.offsetWidth;
    catalogMessage.classList.add('message-blink');
  }
  byId('preview-message').textContent = text;
  byId('preview-message').dataset.tone = tone;
}
function moveAdditionFeedback(context = 'page') {
  const feedback = byId('addition-feedback');
  feedback.dataset.context = context;
  if (context === 'preview') byId('preview').querySelector('.preview-order-controls').append(feedback);
  else if (context === 'dialog') byId('overflow-dialog').querySelector('.dialog-actions').before(feedback);
  else document.body.append(feedback);
}
function hideAdditionFeedback(clearUndo = true) {
  clearTimeout(additionFeedbackTimer);
  additionFeedbackTimer = null;
  byId('addition-feedback').hidden = true;
  if (clearUndo) lastAddition = null;
}
function showAdditionFeedback(sticker, size, addedItems) {
  hideAdditionFeedback();
  lastAddition = { ids:new Set(addedItems.map(item => item.id)), name:sticker.name, size, count:addedItems.length };
  const previewOpen = byId('preview').open;
  const overflowOpen = byId('overflow-dialog').open;
  moveAdditionFeedback(previewOpen ? 'preview' : overflowOpen ? 'dialog' : 'page');
  byId('addition-feedback-text').textContent = `Добавлено: ${sticker.name} · ${size} × ${addedItems.length}`;
  byId('addition-feedback').hidden = false;
  additionFeedbackTimer = setTimeout(() => hideAdditionFeedback(), 6500);
}
function undoLastAddition() {
  if (!lastAddition) return;
  const addition = lastAddition;
  items = items.filter(item => !addition.ids.has(item.id));
  const result = pack(items);
  pages = result.ok ? result.pages : [];
  active = Math.min(active, Math.max(0, pages.length - 1));
  hideAdditionFeedback();
  if (byId('overflow-dialog').open) byId('overflow-dialog').close();
  render();
  message(`Отменено: ${addition.name} · ${addition.size} × ${addition.count}.`, 'success');
}
function syncSizeControls() {
  byId('selectedSizeText').textContent = selectedSize ? `${selectedSize} — ${sizeDescriptions[selectedSize]}` : 'не выбран';
  for (const containerId of ['sizes', 'preview-sizes']) {
    for (const child of byId(containerId).children) child.setAttribute('aria-pressed', String(child.textContent === selectedSize));
  }
}
function chooseSize(size) {
  selectedSize = selectedSize === size ? null : size;
  syncSizeControls();
  message();
}
for (const size of Object.keys(config.sizes)) {
  const button = document.createElement('button');
  button.id = 'size' + size; button.textContent = size; button.setAttribute('aria-pressed', 'false');
  button.title = `Размер ${size}: ${sizeDescriptions[size]}`;
  button.setAttribute('aria-label', `Размер ${size}: ${sizeDescriptions[size]}`);
  button.onclick = () => chooseSize(size);
  byId('sizes').append(button);
  const previewButton = document.createElement('button');
  previewButton.type = 'button'; previewButton.textContent = size; previewButton.setAttribute('aria-pressed', 'false');
  previewButton.title = `Размер ${size}: ${sizeDescriptions[size]}`;
  previewButton.setAttribute('aria-label', `Размер ${size}: ${sizeDescriptions[size]}`);
  previewButton.onclick = () => chooseSize(size);
  byId('preview-sizes').append(previewButton);
}
byId('quantity').oninput = () => {
  byId('quantity').removeAttribute('aria-invalid');
  const quantity = Number(byId('quantity').value);
  byId('preview-quantity').value = Number.isInteger(quantity) && quantity >= 1 && quantity <= 20 ? String(quantity) : '';
  message();
};
byId('preview-quantity').oninput = () => {
  byId('quantity').value = byId('preview-quantity').value;
  byId('preview-quantity').removeAttribute('aria-invalid');
  byId('quantity').removeAttribute('aria-invalid');
  message();
};
byId('quantity').addEventListener('keydown', event => {
  if (event.key !== 'Enter' || event.isComposing) return;
  event.preventDefault();
  if (!event.repeat) add();
});
function add() {
  if (!selectedStickerId) { message('По запросу нет наклеек.'); return; }
  if (!selectedSize) { message('Сначала выберите размер.', '', true); return; }
  const field = byId('preview').open ? byId('preview-quantity') : byId('quantity');
  const quantity = Number(field.value);
  const validPreviewQuantity = !byId('preview').open || quantity <= 20;
  if (!validQuantity(field.value) || !validPreviewQuantity) { field.setAttribute('aria-invalid', 'true'); message(byId('preview').open ? 'Выберите количество от 1 до 20.' : 'Введите целое количество от 1.'); return; }
  const sticker = stickerById.get(selectedStickerId);
  const source = sources.get(selectedStickerId);
  if (!source?.naturalWidth) { message('Изображение ещё загружается. Попробуйте снова.'); return; }
  const aspect = source.naturalWidth / source.naturalHeight;
  const effects = byId('preview').open && byId('preview').dataset.mode === 'catalog' ? catalogPreviewEffects : {};
  const result = fitAddition(items, { imageId: sticker.id, size: selectedSize, aspect, ...effects }, quantity, nextId);
  if (result.reason === 'oversize') { message('Эта наклейка не помещается в печатной области. Выберите меньший размер.'); return; }
  if (result.added.length) {
    const oldCount = pages.length;
    items.push(...result.added); nextId += result.added.length; pages = result.pages;
    if (pages.length > oldCount) active = pages.length - 1;
  }
  render();
  if (result.added.length && !result.remaining) {
    message();
  }
  if (result.remaining) {
    if (byId('preview').open) byId('preview').close();
    byId('overflow-message').textContent = `${sticker.name}, размер ${selectedSize}. Запрошено: ${quantity}. Добавлено в этот заказ: ${result.added.length}. Не помещается: ${result.remaining}.`;
    byId('overflow-checkout').disabled = items.length === 0;
    byId('overflow-dialog').showModal();
  }
  if (result.added.length) showAdditionFeedback(sticker, selectedSize, result.added);
}
function selectSticker(id) {
  selectedStickerId = id;
  byId('selected-sticker').textContent = id ? 'Выбрано: ' + stickerById.get(id).name : 'Наклейка не выбрана';
  for (const card of byId('sticker-grid').children) {
    const selected = card.dataset.stickerId === id;
    card.dataset.selected = String(selected);
    card.querySelector('button').setAttribute('aria-pressed', String(selected));
  }
  message();
}
function updatePreview(sticker, open = false) {
  if (!sticker) return;
  if (open || catalogPreviewStickerId !== sticker.id) catalogPreviewEffects = {};
  catalogPreviewStickerId = sticker.id;
  selectSticker(sticker.id);
  const preview = byId('preview');
  preview.dataset.mode = 'catalog';
  inspectedItemId = null;
  inspectedRefreshCheckout = false;
  byId('preview-order-controls').hidden = false;
  byId('preview-effects-controls').hidden = true;
  byId('preview-editor-toggle').setAttribute('aria-expanded', 'false');
  byId('preview-previous').hidden = false;
  byId('preview-next').hidden = false;
  const image = byId('preview-image');
  image.src = sticker.src;
  image.alt = sticker.name + ' — увеличенный просмотр';
  byId('preview-title').textContent = sticker.name;
  const index = visibleStickers.findIndex(item => item.id === sticker.id);
  byId('preview-position').textContent = index >= 0 ? `${index + 1} из ${visibleStickers.length}` : '';
  byId('preview-previous').disabled = index <= 0;
  byId('preview-next').disabled = index < 0 || index >= visibleStickers.length - 1;
  const characterButton = byId('preview-character');
  const characterName = sticker.entry.character_name;
  characterButton.hidden = !sticker.entry.character_id || !characterName;
  characterButton.textContent = characterName ? `Открыть коллекцию персонажа «${characterName}»` : '';
  byId('preview-effects-scope').textContent = 'Эффекты применятся к добавляемым экземплярам.';
  refreshPreviewEffects();
  syncSizeControls();
  if (open && !preview.open) {
    byId('preview-quantity').value = '';
    byId('preview-quantity').removeAttribute('aria-invalid');
    preview.showModal();
  }
}
function movePreview(offset) {
  const index = visibleStickers.findIndex(sticker => sticker.id === selectedStickerId);
  const target = visibleStickers[index + offset];
  if (target) updatePreview(target);
}
function createCard(sticker) {
  const card = document.createElement('article');
  card.className = 'card'; card.dataset.stickerId = sticker.id; card.hidden = true;
  cardsById.set(sticker.id, card);
  const button = document.createElement('button');
  button.className = 'image-button'; button.type = 'button';
  button.setAttribute('aria-label', 'Рассмотреть наклейку ' + sticker.name);
  const image = document.createElement('img');
  image.src = sticker.src; image.alt = sticker.name; image.draggable = false; image.loading = 'lazy'; image.decoding = 'async';
  sources.set(sticker.id, image);
  const heading = document.createElement('h2'); heading.textContent = sticker.name;
  const addButton = document.createElement('button');
  addButton.className = 'card-add'; addButton.type = 'button'; addButton.textContent = 'Добавить';
  addButton.setAttribute('aria-label', `Добавить наклейку «${sticker.name}» на лист-макет`);
  addButton.onclick = () => { selectSticker(sticker.id); add(); };
  button.append(image); card.append(button, heading, addButton); byId('sticker-grid').append(card);
  button.onclick = () => updatePreview(sticker, true);
}
function currentFilters() {
  return {
    section: byId('filter-section').value,
    character: byId('filter-character').value,
    role: byId('filter-role').value,
    mood: byId('filter-mood').value,
  };
}
function currentCriteria() {
  return { query: byId('search-query').value, filters: currentFilters() };
}
function criteriaChanged() {
  return JSON.stringify(currentCriteria()) !== JSON.stringify(appliedCriteria);
}
function markSearchPending() {
  if (!searchEngine) return;
  const pending = criteriaChanged();
  const hasExecutableQuery = Boolean(byId('search-query').value.trim() || byId('filter-section').value);
  byId('apply-search').disabled = !pending || !hasExecutableQuery;
  byId('clear-filters').disabled = !byId('search-query').value.trim() && !byId('filter-section').value && !byId('filter-character').value && !byId('filter-role').value && !byId('filter-mood').value;
  if (pending) byId('search-status').textContent = hasExecutableQuery
    ? 'Нажмите Enter или «Найти», чтобы применить изменения'
    : 'Сначала выберите раздел или воспользуйтесь поиском';
}

function shuffled(itemsToShuffle) {
  const result = [...itemsToShuffle];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapWith = Math.floor(Math.random() * (index + 1));
    [result[index], result[swapWith]] = [result[swapWith], result[index]];
  }
  return result;
}

function renderResultPage() {
  visibleStickers = allMatches.slice(0, loadedResultCount);
  const visibleIds = new Set(visibleStickers.map(sticker => sticker.id));
  const grid = byId('sticker-grid');
  for (const sticker of visibleStickers) {
    const card = cardsById.get(sticker.id);
    card.hidden = false;
    grid.append(card);
  }
  for (const sticker of stickers) if (!visibleIds.has(sticker.id)) {
    const card = cardsById.get(sticker.id);
    card.hidden = true;
    grid.append(card);
  }
  if (!visibleIds.has(selectedStickerId)) selectSticker(visibleStickers[0]?.id || null);
  const remaining = allMatches.length - visibleStickers.length;
  byId('show-more-results').hidden = remaining <= 0;
  byId('show-more-results').textContent = remaining > 0 ? `Показать ещё (${remaining})` : 'Показать ещё';
  byId('search-status').textContent = allMatches.length
    ? `Найдено: ${allMatches.length} · показано: ${visibleStickers.length}`
    : 'Ничего не найдено';
}

function applyCatalogSearch() {
  if (!searchEngine) return;
  const criteria = currentCriteria();
  const { query, filters } = criteria;
  if (!query.trim() && !filters.section) {
    allMatches = [];
    loadedResultCount = 0;
    renderResultPage();
    appliedCriteria = null;
    byId('apply-search').disabled = true;
    byId('search-status').textContent = 'Сначала выберите раздел или воспользуйтесь поиском';
    return;
  }
  if (!criteriaChanged()) return;
  const effectiveFilters = query.trim() ? {} : filters;
  const matches = searchEngine.run(query, effectiveFilters).map(result => stickerById.get(result.entry.image_id));
  allMatches = query.trim() ? matches : shuffled(matches);
  loadedResultCount = Math.min(resultPageSize, allMatches.length);
  renderResultPage();
  appliedCriteria = criteria;
  byId('apply-search').disabled = true;
  byId('clear-filters').disabled = !query.trim() && !filters.section && !filters.character && !filters.role && !filters.mood;
}
function addOptions(select, options) {
  for (const item of options) {
    const option = document.createElement('option');
    option.value = typeof item === 'string' ? item : item.value;
    option.textContent = typeof item === 'string' ? item : item.label;
    select.append(option);
  }
}
async function loadCatalog() {
  byId('search-status').textContent = 'Загружаем каталог…';
  try {
    const [catalogResponse, dictionaryResponse] = await Promise.all([
      fetch('catalog-data/site_catalog.json'),
      fetch('catalog-data/global_search_dictionary.v1.json'),
    ]);
    if (!catalogResponse.ok || !dictionaryResponse.ok) throw new Error('catalog data unavailable');
    const [catalog, dictionary] = await Promise.all([catalogResponse.json(), dictionaryResponse.json()]);
    stickers = catalog.entries.map(entry => ({ id:entry.image_id, name:entry.display_name, src:entry.src, entry }));
    stickerById = new Map(stickers.map(sticker => [sticker.id, sticker]));
    searchEngine = CatalogSearch.createEngine(catalog, dictionary);
    addOptions(byId('filter-section'), catalog.filters.sections);
    defaultSection = '';
    addOptions(byId('filter-character'), catalog.filters.characters);
    addOptions(byId('filter-role'), catalog.filters.roles);
    addOptions(byId('filter-mood'), catalog.filters.moods);
    for (const sticker of stickers) createCard(sticker);
    const incoming = new URLSearchParams(window.location.search);
    const incomingQuery = incoming.get('q') || '';
    if (incomingQuery) {
      byId('search-query').value = incomingQuery;
      byId('filter-section').value = '';
      for (const id of ['filter-character','filter-role','filter-mood']) byId(id).value = '';
    } else {
      const incomingControls = {
        section: 'filter-section', character: 'filter-character', role: 'filter-role', mood: 'filter-mood',
      };
      for (const [parameter, id] of Object.entries(incomingControls)) {
        const value = incoming.get(parameter);
        if (value && [...byId(id).options].some(option => option.value === value)) byId(id).value = value;
      }
    }
    applyCatalogSearch();
    restoreCurrentOrder();
  } catch (error) {
    console.error(error);
    byId('search-status').textContent = 'Не удалось загрузить каталог. Обновите страницу.';
  }
}
byId('search-query').addEventListener('input', markSearchPending);
byId('search-query').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); applyCatalogSearch(); }
});
for (const id of ['filter-section','filter-character','filter-role','filter-mood']) {
  byId(id).addEventListener('change', markSearchPending);
  byId(id).addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); applyCatalogSearch(); }
  });
}
byId('apply-search').onclick = applyCatalogSearch;
byId('show-more-results').onclick = () => {
  loadedResultCount = Math.min(loadedResultCount + resultPageSize, allMatches.length);
  renderResultPage();
};
byId('clear-filters').onclick = () => {
  byId('search-query').value = '';
  byId('filter-section').value = '';
  for (const id of ['filter-character','filter-role','filter-mood']) byId(id).value = '';
  applyCatalogSearch();
};
byId('preview-add').onclick = add;
byId('undo-addition').onclick = undoLastAddition;
byId('close-preview').onclick = () => byId('preview').close();
byId('preview-previous').onclick = () => movePreview(-1);
byId('preview-next').onclick = () => movePreview(1);
byId('preview').addEventListener('keydown', event => {
  if (byId('preview').dataset.mode === 'edit') return;
  if (event.key !== 'Enter' || event.isComposing) return;
  const activeControl = document.activeElement;
  const quantity = byId('preview-quantity').value;
  if (!activeControl?.closest('.preview-order-controls') || !selectedSize || !validQuantity(quantity) || Number(quantity) > 20) return;
  event.preventDefault();
  event.stopPropagation();
  if (!event.repeat) add();
}, { capture:true });
byId('preview').addEventListener('keydown', event => {
  if (byId('preview').dataset.mode === 'edit') return;
  if (event.key === 'ArrowLeft' && !byId('preview-previous').disabled) {
    event.preventDefault(); movePreview(-1);
  }
  if (event.key === 'ArrowRight' && !byId('preview-next').disabled) {
    event.preventDefault(); movePreview(1);
  }
});
byId('preview-character').onclick = () => {
  const sticker = stickerById.get(selectedStickerId);
  if (!sticker?.entry.character_id) return;
  byId('preview').close();
  byId('search-query').value = '';
  byId('filter-section').value = sticker.entry.sections[0] || '';
  byId('filter-character').value = sticker.entry.character_id;
  byId('filter-role').value = '';
  byId('filter-mood').value = '';
  applyCatalogSearch();
  byId('search-status').textContent = `Коллекция персонажа «${sticker.entry.character_name}»: ${visibleStickers.length}`;
};
byId('layout-checkout').onclick = openCheckout;
byId('send-to-cart').onclick = () => sendCurrentToCart();
byId('close-checkout').onclick = () => byId('checkout-dialog').close();
byId('back-to-layout').onclick = () => byId('checkout-dialog').close();
for (const id of Object.values(addressFields)) byId(id).addEventListener('input', () => {
  byId('checkout-feedback').textContent = '';
  byId('saved-address').value = '';
  persistCurrentOrder();
});
byId('saved-address').addEventListener('change', () => {
  const saved = StickerStore.addresses().find(item => item.id === byId('saved-address').value);
  if (saved) fillDeliveryAddress(saved.address);
  else fillDeliveryAddress('');
  persistCurrentOrder();
});
byId('checkout-form').onsubmit = event => {
  event.preventDefault();
  if (!byId('checkout-form').checkValidity()) { byId('checkout-form').reportValidity(); return; }
  const address = readDeliveryAddress();
  if (StickerStore.signedIn() && byId('save-address').checked) {
    const saved = StickerStore.saveAddress(address);
    refreshSavedAddresses(saved.id);
    byId('save-address').checked = false;
  }
  persistCurrentOrder();
  byId('checkout-feedback').textContent = 'Адрес заполнен и сохранён с текущим заказом. Отправка заказа пока не подключена.';
};
byId('close-overflow').onclick = () => byId('overflow-dialog').close();
byId('overflow-checkout').onclick = () => { byId('overflow-dialog').close(); openCheckout(); };
for (const dialogId of ['preview','overflow-dialog']) byId(dialogId).addEventListener('close', () => {
  if (!byId('addition-feedback').hidden && byId('addition-feedback').dataset.context !== 'page') moveAdditionFeedback('page');
});
byId('preview').addEventListener('close', () => {
  byId('preview-effects-controls').hidden = true;
  byId('preview-editor-toggle').setAttribute('aria-expanded', 'false');
  if (byId('preview').dataset.mode === 'edit') {
    inspectedItemId = null;
    inspectedRefreshCheckout = false;
    inspectedApplyAll = false;
  } else {
    catalogPreviewEffects = {};
  }
});
function position(element, placement) {
  Object.assign(element.style, { left: placement.x / config.sheet.width * 100 + '%', top: placement.y / config.sheet.height * 100 + '%', width: placement.width / config.sheet.width * 100 + '%', height: placement.height / config.sheet.height * 100 + '%' });
}
function stickerFilter(item) {
  const filters = [];
  if (item.grayscale) filters.push('grayscale(1)');
  if (item.sepia) filters.push('sepia(1)');
  if (item.brightnessLevel) filters.push(`brightness(${1 + item.brightnessLevel * .1})`);
  if (item.saturationLevel) filters.push(`saturate(${1 + item.saturationLevel * .25})`);
  return filters.join(' ');
}
function inspectedItem() { return items.find(candidate => candidate.id === inspectedItemId); }
function matchingItems(item = inspectedItem()) { return item ? items.filter(candidate => candidate.imageId === item.imageId) : []; }
function sameStickerVariant(first, second) {
  return first.imageId === second.imageId
    && first.size === second.size
    && Boolean(first.mirrorHorizontal) === Boolean(second.mirrorHorizontal)
    && Boolean(first.grayscale) === Boolean(second.grayscale)
    && Boolean(first.sepia) === Boolean(second.sepia)
    && (Number(first.brightnessLevel) || 0) === (Number(second.brightnessLevel) || 0)
    && (Number(first.saturationLevel) || 0) === (Number(second.saturationLevel) || 0);
}
function matchingVariantItems(item = inspectedItem()) {
  if (!item) return [];
  return [item, ...items.filter(candidate => candidate.id !== item.id && sameStickerVariant(candidate, item))];
}
function stickerEffectsLabel(item) {
  const effects = [];
  if (item.mirrorHorizontal) effects.push('зеркально');
  if (item.grayscale) effects.push('чёрно-белая');
  if (item.sepia) effects.push('сепия');
  if (item.brightnessLevel) effects.push(`светлее +${item.brightnessLevel * 10}%`);
  if (item.saturationLevel) effects.push(`насыщеннее +${item.saturationLevel * 25}%`);
  return effects.length ? effects.join(', ') : 'без эффектов';
}
function hideStickerInspector(clearSelection = true) {
  const inspector = byId('sticker-inspector');
  inspector.hidden = true;
  byId('inspector-settings-panel').hidden = true;
  byId('inspector-delete-panel').hidden = true;
  byId('inspector-info-panel').hidden = true;
  byId('inspector-settings').setAttribute('aria-expanded', 'false');
  byId('inspector-delete').setAttribute('aria-expanded', 'false');
  byId('inspector-info').setAttribute('aria-expanded', 'false');
  document.body.append(inspector);
  if (clearSelection) {
    inspectedItemId = null;
    inspectedRefreshCheckout = false;
    inspectedApplyAll = false;
  }
}
function refreshStickerInspector() {
  const item = inspectedItem();
  if (!item) { hideStickerInspector(); return; }
  const sticker = stickerById.get(item.imageId);
  const group = matchingItems(item);
  const variantGroup = matchingVariantItems(item);
  const image = byId('inspector-image');
  image.src = sticker.src;
  image.alt = `${sticker.name}, размер ${item.size}`;
  image.style.transform = item.mirrorHorizontal ? 'scaleX(-1)' : '';
  image.style.filter = stickerFilter(item);
  byId('inspector-name').textContent = sticker.name;
  byId('inspector-summary').textContent = `Размер ${item.size} · Таких в заказе: ${group.length}`;
  const sheetIndex = pages.findIndex(page => page.some(placement => placement.id === item.id));
  byId('inspector-info-section').textContent = sticker.entry.sections.join(', ') || 'не указан';
  byId('inspector-info-character').textContent = sticker.entry.character_name || 'не указан';
  byId('inspector-info-size').textContent = `${item.size} — ${sizeDescriptions[item.size]}`;
  byId('inspector-info-count').textContent = `${group.length} шт.`;
  byId('inspector-info-sheet').textContent = sheetIndex >= 0 ? String(sheetIndex + 1) : '—';
  byId('inspector-info-effects').textContent = stickerEffectsLabel(item);
  byId('scope-one').textContent = `По количеству (${variantGroup.length})`;
  byId('scope-all').textContent = `Все такие (${group.length})`;
  byId('scope-one').setAttribute('aria-pressed', String(!inspectedApplyAll));
  byId('scope-all').setAttribute('aria-pressed', String(inspectedApplyAll));
  byId('inspector-quantity').value = String(inspectedApplyAll ? group.length : 1);
  byId('inspector-quantity').disabled = inspectedApplyAll;
  pendingInspectorSize ||= item.size;
  for (const button of byId('inspector-sizes').children) button.setAttribute('aria-pressed', String(button.dataset.size === pendingInspectorSize));
}
function openStickerInspector(placement, anchor, refreshCheckout = false) {
  inspectedItemId = placement.id;
  inspectedRefreshCheckout = refreshCheckout;
  inspectedApplyAll = false;
  pendingInspectorSize = placement.size;
  const inspector = byId('sticker-inspector');
  (refreshCheckout ? byId('checkout-dialog') : document.body).append(inspector);
  const rect = anchor.getBoundingClientRect();
  const width = 380, height = 470;
  inspector.style.left = `${Math.max(8, Math.min(window.innerWidth - width - 8, rect.left + rect.width / 2 - 190))}px`;
  inspector.style.top = `${Math.max(8, Math.min(window.innerHeight - height - 8, rect.top + rect.height / 2 - 180))}px`;
  inspector.hidden = false;
  byId('inspector-message').textContent = '';
  refreshStickerInspector();
}
function removeOrderItem(itemId, refreshCheckout = false) {
  if (inspectedItemId === itemId) hideStickerInspector();
  items = items.filter(item => item.id !== itemId);
  const result = pack(items);
  pages = result.ok ? result.pages : [];
  active = Math.min(active, Math.max(0, pages.length - 1));
  message(); render();
  if (!refreshCheckout) return;
  if (!items.length) { byId('checkout-dialog').close(); message('В заказе не осталось наклеек.'); return; }
  renderCheckoutContents();
}
function draw(target, placements, miniature = false, removable = false) {
  const printable = area(), border = document.createElement('div');
  border.className = 'print-area'; position(border, { x:printable.x, y:printable.y, width:printable.w, height:printable.h }); target.append(border);
  for (const placement of placements) {
    const interactive = !miniature || removable;
    const element = document.createElement(interactive ? 'button' : 'span'); element.className = 'placed';
    if (interactive) element.type = 'button';
    position(element, placement);
    const sticker = stickerById.get(placement.imageId);
    const img = document.createElement('img'); img.src = sticker.src; img.alt = interactive ? `${sticker.name}, размер ${placement.size}` : ''; img.draggable = false;
    img.style.width = (placement.rotated ? placement.height / placement.width * 100 : 100) + '%'; img.style.height = (placement.rotated ? placement.width / placement.height * 100 : 100) + '%';
    img.style.transform = `translate(-50%, -50%) rotate(${placement.rotated ? 90 : 0}deg) scaleX(${placement.mirrorHorizontal ? -1 : 1})`;
    img.style.filter = stickerFilter(placement); element.append(img);
    if (interactive) {
      element.title = `${sticker.name}, размер ${placement.size}. Нажмите — открыть инструменты`;
      element.onclick = () => openStickerInspector(placement, element, removable);
    }
    target.append(element);
  }
}
function applyInspectorScope(applyAll) {
  inspectedApplyAll = applyAll;
  const item = inspectedItem();
  pendingInspectorSize = item?.size || null;
  refreshStickerInspector();
}
byId('scope-one').onclick = () => applyInspectorScope(false);
byId('scope-all').onclick = () => applyInspectorScope(true);
byId('inspector-settings').onclick = () => {
  const panel = byId('inspector-settings-panel');
  panel.hidden = !panel.hidden;
  byId('inspector-delete-panel').hidden = true;
  byId('inspector-info-panel').hidden = true;
  byId('inspector-settings').setAttribute('aria-expanded', String(!panel.hidden));
  byId('inspector-delete').setAttribute('aria-expanded', 'false');
  byId('inspector-info').setAttribute('aria-expanded', 'false');
};
byId('inspector-delete').onclick = () => {
  byId('inspector-delete-panel').hidden = false;
  byId('inspector-settings-panel').hidden = true;
  byId('inspector-info-panel').hidden = true;
  byId('inspector-delete').setAttribute('aria-expanded', 'true');
  byId('inspector-settings').setAttribute('aria-expanded', 'false');
  byId('inspector-info').setAttribute('aria-expanded', 'false');
};
byId('inspector-info').onclick = () => {
  const panel = byId('inspector-info-panel');
  panel.hidden = !panel.hidden;
  byId('inspector-settings-panel').hidden = true;
  byId('inspector-delete-panel').hidden = true;
  byId('inspector-info').setAttribute('aria-expanded', String(!panel.hidden));
  byId('inspector-settings').setAttribute('aria-expanded', 'false');
  byId('inspector-delete').setAttribute('aria-expanded', 'false');
};
byId('inspector-find-catalog').onclick = () => {
  const selected = inspectedItem();
  if (!selected) return;
  const stickerId = selected.imageId;
  hideStickerInspector();
  if (byId('checkout-dialog').open) byId('checkout-dialog').close();
  byId('search-query').value = stickerId;
  for (const id of ['filter-section','filter-character','filter-role','filter-mood']) byId(id).value = '';
  appliedCriteria = null;
  applyCatalogSearch();
  const card = cardsById.get(stickerId);
  if (!card) return;
  selectSticker(stickerId);
  card.classList.remove('catalog-highlight');
  void card.offsetWidth;
  card.classList.add('catalog-highlight');
  card.scrollIntoView({ behavior:'smooth', block:'center' });
  setTimeout(() => card.classList.remove('catalog-highlight'), 3300);
};
byId('inspector-cancel-delete').onclick = () => { byId('inspector-delete-panel').hidden = true; byId('inspector-delete').setAttribute('aria-expanded', 'false'); };
byId('inspector-confirm-delete').onclick = () => {
  const id = inspectedItemId, refreshCheckout = inspectedRefreshCheckout;
  if (id !== null) removeOrderItem(id, refreshCheckout);
};
function addOneInspectedCopy() {
  const selected = inspectedItem();
  if (!selected) return;
  const copy = { ...selected, id:nextId };
  const candidate = [...items, copy];
  const packed = pack(candidate);
  if (!packed.ok) {
    byId('inspector-message').textContent = 'Ещё одна наклейка не помещается в предел семи листов.';
    byId('inspector-settings-panel').hidden = false;
    byId('inspector-settings').setAttribute('aria-expanded', 'true');
    return;
  }
  const refreshCheckout = inspectedRefreshCheckout;
  items = candidate; pages = packed.pages; nextId += 1;
  active = Math.max(0, pages.findIndex(page => page.some(placement => placement.id === copy.id)));
  render();
  if (refreshCheckout) renderCheckoutContents();
  refreshStickerInspector();
  message('Добавлена ещё одна такая же наклейка.', 'success');
}
byId('inspector-add-one').onclick = addOneInspectedCopy;
for (const size of Object.keys(config.sizes)) {
  const button = document.createElement('button');
  button.type = 'button'; button.textContent = size; button.dataset.size = size;
  button.title = `Размер ${size}: ${sizeDescriptions[size]}`;
  button.setAttribute('aria-label', `Выбрать размер ${size}: ${sizeDescriptions[size]}`);
  button.setAttribute('aria-pressed', 'false');
  button.onclick = () => { pendingInspectorSize = size; refreshStickerInspector(); };
  byId('inspector-sizes').append(button);
}
function applyInspectorQuantityAndSize() {
  const selected = inspectedItem();
  if (!selected) return;
  const refreshCheckout = inspectedRefreshCheckout;
  const group = matchingItems(selected);
  let targets = group;
  if (!inspectedApplyAll) {
    const desired = Number(byId('inspector-quantity').value);
    const variantGroup = matchingVariantItems(selected);
    if (!Number.isSafeInteger(desired) || desired < 1) {
      byId('inspector-message').textContent = 'Введите целое количество от 1.'; return;
    }
    if (desired > variantGroup.length) {
      byId('inspector-message').textContent = `Полностью одинаковых наклеек сейчас только ${variantGroup.length}.`;
      return;
    }
    targets = variantGroup.slice(0, desired);
  }
  const targetIds = new Set(targets.map(item => item.id));
  const candidate = items.map(item => ({ ...item, ...(targetIds.has(item.id) ? { size:pendingInspectorSize || item.size } : {}) }));
  const packed = pack(candidate);
  if (!packed.ok) { byId('inspector-message').textContent = 'Изменение не помещается в предел семи листов.'; return; }
  items = candidate; pages = packed.pages;
  active = Math.max(0, pages.findIndex(page => page.some(placement => placement.id === selected.id)));
  render();
  if (refreshCheckout) renderCheckoutContents();
  byId('inspector-message').textContent = inspectedApplyAll
    ? `Изменены все такие наклейки: ${targets.length}.`
    : `Изменено: ${targets.length}. Общее количество не изменилось.`;
  refreshStickerInspector();
}
byId('inspector-apply').onclick = applyInspectorQuantityAndSize;
byId('inspector-quantity').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); applyInspectorQuantityAndSize(); } });

function previewEffectState() {
  return byId('preview').dataset.mode === 'catalog' ? catalogPreviewEffects : (inspectedItem() || {});
}
function refreshPreviewEffects() {
  const state = previewEffectState();
  const image = byId('preview-image');
  image.style.transform = state.mirrorHorizontal ? 'scaleX(-1)' : '';
  image.style.filter = stickerFilter(state);
  byId('edit-mirror').setAttribute('aria-pressed', String(Boolean(state.mirrorHorizontal)));
  byId('edit-grayscale').setAttribute('aria-pressed', String(Boolean(state.grayscale)));
  byId('edit-sepia').setAttribute('aria-pressed', String(Boolean(state.sepia)));
  byId('edit-brightness').setAttribute('aria-pressed', String(Boolean(state.brightnessLevel)));
  byId('edit-brightness').textContent = state.brightnessLevel ? `Светлее +${state.brightnessLevel * 10}%` : 'Светлее';
  byId('edit-saturation').setAttribute('aria-pressed', String(Boolean(state.saturationLevel)));
  byId('edit-saturation').textContent = state.saturationLevel ? `Насыщеннее +${state.saturationLevel * 25}%` : 'Насыщеннее';
}
function mutatePreviewEffects(mutator) {
  if (byId('preview').dataset.mode === 'catalog') {
    mutator(catalogPreviewEffects); refreshPreviewEffects(); return;
  }
  const selected = inspectedItem();
  if (!selected) return;
  const targets = inspectedApplyAll ? matchingItems(selected) : [selected];
  for (const item of targets) mutator(item);
  const packed = pack(items); pages = packed.ok ? packed.pages : pages;
  render(); if (inspectedRefreshCheckout) renderCheckoutContents(); refreshPreviewEffects();
}
byId('edit-mirror').onclick = () => { const next = !previewEffectState().mirrorHorizontal; mutatePreviewEffects(item => { item.mirrorHorizontal = next; }); };
byId('edit-grayscale').onclick = () => { const next = !previewEffectState().grayscale; mutatePreviewEffects(item => { item.grayscale = next; item.sepia = false; }); };
byId('edit-sepia').onclick = () => { const next = !previewEffectState().sepia; mutatePreviewEffects(item => { item.sepia = next; item.grayscale = false; }); };
byId('edit-brightness').onclick = () => { const next = ((Number(previewEffectState().brightnessLevel) || 0) + 1) % 3; mutatePreviewEffects(item => { item.brightnessLevel = next; }); };
byId('edit-saturation').onclick = () => { const next = ((Number(previewEffectState().saturationLevel) || 0) + 1) % 3; mutatePreviewEffects(item => { item.saturationLevel = next; }); };
byId('edit-reset').onclick = () => mutatePreviewEffects(item => {
  delete item.mirrorHorizontal; delete item.grayscale; delete item.sepia; delete item.brightnessLevel; delete item.saturationLevel;
});
function openPlacedEffectsEditor() {
  const item = inspectedItem();
  if (!item) return;
  const sticker = stickerById.get(item.imageId);
  hideStickerInspector(false);
  const preview = byId('preview'); preview.dataset.mode = 'edit';
  byId('preview-order-controls').hidden = true;
  byId('preview-effects-controls').hidden = false;
  byId('preview-editor-toggle').setAttribute('aria-expanded', 'true');
  byId('preview-character').hidden = true;
  byId('preview-previous').hidden = true; byId('preview-next').hidden = true;
  byId('preview-image').src = sticker.src;
  byId('preview-image').alt = `${sticker.name}, размер ${item.size}`;
  byId('preview-title').textContent = sticker.name;
  const count = matchingItems(item).length;
  byId('preview-position').textContent = `Размер ${item.size} · Раздел: ${sticker.entry.sections.join(', ') || 'не указан'}`;
  byId('preview-effects-scope').textContent = inspectedApplyAll ? `Изменения применяются ко всем таким наклейкам: ${count}.` : 'Изменения применяются только к выбранному экземпляру.';
  refreshPreviewEffects();
  preview.showModal();
}
byId('inspector-more').onclick = openPlacedEffectsEditor;
byId('preview-editor-toggle').onclick = () => {
  const panel = byId('preview-effects-controls');
  panel.hidden = !panel.hidden;
  byId('preview-editor-toggle').setAttribute('aria-expanded', String(!panel.hidden));
};
document.addEventListener('pointerdown', event => {
  const inspector = byId('sticker-inspector');
  if (inspector.hidden || inspector.contains(event.target) || event.target.closest('.placed')) return;
  hideStickerInspector();
});
document.addEventListener('keydown', event => { if (event.key === 'Escape' && !byId('sticker-inspector').hidden) hideStickerInspector(); });
function fillOrderSummary(target) {
  target.replaceChildren();
  for (const sticker of stickers) for (const size of Object.keys(config.sizes)) {
    const count = items.filter(item => item.imageId === sticker.id && item.size === size).length;
    if (count) { const line = document.createElement('div'); line.textContent = `${sticker.name} · ${size} × ${count}`; target.append(line); }
  }
  if (!items.length) target.textContent = 'Пока нет выбранных наклеек';
}
function renderCheckoutContents() {
  fillOrderSummary(byId('checkout-items'));
  byId('checkout-totals').textContent = `Наклеек: ${items.length} · Листов: ${pages.length}`;
  const sheets = byId('checkout-sheets'); sheets.replaceChildren();
  pages.forEach((page, index) => {
    const card = document.createElement('figure'); card.className = 'checkout-sheet-card';
    const preview = document.createElement('div'); preview.className = 'mini-sheet checkout-sheet';
    preview.setAttribute('aria-label', 'Лист ' + (index + 1)); draw(preview, page, true, true);
    const caption = document.createElement('figcaption'); caption.textContent = `Лист ${index + 1} · ${page.length} шт.`;
    card.append(preview, caption); sheets.append(card);
  });
  byId('checkout-feedback').textContent = '';
}
function openCheckout() {
  if (!items.length) return;
  refreshSavedAddresses(byId('saved-address').value);
  renderCheckoutContents();
  byId('checkout-dialog').showModal();
}
function render() {
  cancelSheetDeletion();
  byId('delete-sheet').disabled = !pages[active]?.length;
  byId('sheet-title').textContent = pages.length ? 'Лист ' + (active + 1) : 'Лист-макет';
  byId('sheet-count').textContent = pages.length ? `Листов: ${pages.length}` : '';
  const sheet = byId('sheet-layout'); sheet.replaceChildren(); draw(sheet, pages[active] || []);
  if (!items.length) { const empty = document.createElement('p'); empty.className = 'empty-sheet'; empty.textContent = 'Здесь появятся выбранные наклейки'; sheet.append(empty); }
  const technical = document.createElement('div'); technical.className = 'technical'; technical.textContent = 'Место для технических отметок'; position(technical, { x:config.margins.left, y:config.sheet.height - config.margins.bottom - config.technicalHeight, width:area().w, height:config.technicalHeight }); sheet.append(technical);
  const list = byId('sheet-list'); list.replaceChildren();
  pages.forEach((page, index) => {
    if (index === active) return;
    const button = document.createElement('button'); button.className = 'sheet-tab'; button.setAttribute('aria-label', 'Открыть лист ' + (index + 1));
    const mini = document.createElement('span'); mini.className = 'mini-sheet'; draw(mini, page, true); button.append(mini, 'Лист ' + (index + 1)); button.onclick = () => { active = index; render(); }; list.append(button);
  });
  renderCartOrders();
  byId('layout-checkout').disabled = items.length === 0;
  byId('send-to-cart').disabled = items.length === 0;
  persistCurrentOrder();
}
render();
loadCatalog();
