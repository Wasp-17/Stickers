const { config, area, pack, validQuantity, fitAddition } = StickerLayout;
const byId = id => document.getElementById(id);
const sizeDescriptions = { A: 'до 30 × 30 мм', A1: 'до 35 × 35 мм', B: 'до 50 × 50 мм', C: 'до 75 × 75 мм', D: 'до 100 × 100 мм', E: 'до 125 × 125 мм', F: 'по рабочей области A4' };
let sizeRules = {};
function sizeRule(imageId) { return sizeRules[imageId] || { a_policy:'standard' }; }
function sizeAllowed(imageId, size) { return !(size === 'A' && sizeRule(imageId).a_policy === 'min_a1'); }
function sizeAdvice(imageId) {
  const rule = sizeRule(imageId);
  if (rule.a_policy === 'min_a1') return `Для этой картинки минимальный размер A1 (35 × 35 мм). ${rule.reason}`;
  if (rule.a_policy === 'recommend_a1') return `Для точного контура рекомендуем A1 (35 × 35 мм). ${rule.reason}`;
  return '';
}
let stickers = [];
let stickerById = new Map();
const sources = new Map();
const cardsById = new Map();
let searchEngine = null;
let catalogFilterOptions = { characters:[], roles:[], moods:[] };
let catalogRankingStats = {};
let mixSeed = '';
let defaultSection = '';
let appliedCriteria = null;
let visibleStickers = [];
let allMatches = [];
let loadedResultCount = 0;
const resultPageSize = 60;
const exampleSheetPrice = 250;
let catalogReady = false;
let scrollStateFrame = 0;
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
let applyingHistoryState = false;
let pendingCartActionId = null;
let pendingOrderReset = null;
let pendingOrderSwitchId = null;
let pendingOrderSwitchMode = null;
const addressFields = {
  recipient: 'delivery-recipient', phone: 'delivery-phone', country: 'delivery-country', postalCode: 'delivery-postal-code',
  region: 'delivery-region', city: 'delivery-city', street: 'delivery-street', house: 'delivery-house',
  apartment: 'delivery-apartment', comment: 'delivery-comment',
};

function favoriteSet() {
  return new Set(StickerStore.favorites().map(item => item.imageId));
}

function setFavoriteButtonState(button, stickerId, favorites = favoriteSet()) {
  if (!button || !stickerId) return;
  const active = favorites.has(stickerId);
  const sticker = stickerById.get(stickerId);
  button.textContent = active ? '♥' : '♡';
  button.setAttribute('aria-pressed', String(active));
  button.setAttribute('aria-label', `${active ? 'Убрать' : 'Добавить'} наклейку «${sticker?.name || stickerId}» ${active ? 'из' : 'в'} избранного`);
  button.title = active ? 'Убрать из избранного' : 'Добавить в избранное';
}

function refreshFavoriteControls() {
  const favorites = favoriteSet();
  for (const [stickerId, card] of cardsById) setFavoriteButtonState(card.querySelector('.favorite-toggle'), stickerId, favorites);
  const preview = byId('preview');
  const previewButton = byId('preview-favorite');
  previewButton.hidden = preview.dataset.mode === 'edit';
  if (!previewButton.hidden) setFavoriteButtonState(previewButton, catalogPreviewStickerId || selectedStickerId, favorites);
}

function openFavoriteAuthDialog() {
  const returnTo = `catalog.html${window.location.search}`;
  byId('favorite-login-link').href = `index.html?account=login&return=${encodeURIComponent(returnTo)}`;
  byId('favorite-register-link').href = `index.html?account=register&return=${encodeURIComponent(returnTo)}`;
  byId('favorite-auth-dialog').showModal();
}

function toggleFavorite(stickerId) {
  if (!StickerStore.signedIn()) return openFavoriteAuthDialog();
  const result = StickerStore.toggleFavorite(stickerId);
  refreshFavoriteControls();
  const sticker = stickerById.get(stickerId);
  message(result?.favorite ? `«${sticker?.name}» добавлена в избранное.` : `«${sticker?.name}» удалена из избранного.`, 'success');
}

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
  const cartSource = saved.cartOrder?.id ? StickerStore.getCartOrder(saved.cartOrder.id) : null;
  activeCartOrder = cartSource ? cartMetadata(cartSource) : null;
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
  return { id:order.id, number:order.number, name:order.name, changedAt:order.changedAt };
}

function comparableAddress(address) {
  if (!address) return {};
  if (typeof address === 'string') address = { street:address };
  return Object.fromEntries(Object.keys(addressFields).map(key => [key, String(address[key] || '').trim()]));
}

function comparableItems(orderItems = []) {
  return orderItems.map(item => JSON.stringify({
    imageId:item.imageId,
    size:item.size,
    aspect:Number(item.aspect),
    mirrorHorizontal:Boolean(item.mirrorHorizontal),
    grayscale:Boolean(item.grayscale),
    sepia:Boolean(item.sepia),
    brightnessLevel:Number(item.brightnessLevel) || 0,
    saturationLevel:Number(item.saturationLevel) || 0,
  })).sort();
}

function activeCartOrderHasChanges() {
  if (!activeCartOrder?.id) return false;
  const saved = StickerStore.getCartOrder(activeCartOrder.id);
  if (!saved) return false;
  return JSON.stringify(comparableItems(items)) !== JSON.stringify(comparableItems(saved.items))
    || JSON.stringify(comparableAddress(readDeliveryAddress())) !== JSON.stringify(comparableAddress(saved.address));
}

function updateActiveOrderStatus() {
  const dirty = activeCartOrderHasChanges();
  const dirtyLabel = byId('active-order-dirty');
  const wasVisible = !dirtyLabel.hidden;
  byId('active-order-title').textContent = activeCartOrder ? `Редактируется: ${activeCartOrder.name}` : 'Новый заказ';
  if (!dirty) {
    dirtyLabel.classList.remove('order-dirty-blink');
    dirtyLabel.hidden = true;
  } else {
    dirtyLabel.hidden = false;
    if (!wasVisible) {
      dirtyLabel.classList.remove('order-dirty-blink');
      void dirtyLabel.offsetWidth;
      dirtyLabel.classList.add('order-dirty-blink');
    }
  }
  return dirty;
}

function clearLayoutOrder() {
  items = []; pages = []; active = 0; nextId = 1; activeCartOrder = null;
  fillDeliveryAddress('');
  StickerStore.clearCurrentOrder();
}

function finishOrderReset(text) {
  hideStickerInspector();
  hideAdditionFeedback();
  if (byId('preview').open) byId('preview').close();
  if (byId('checkout-dialog').open) byId('checkout-dialog').close();
  clearLayoutOrder();
  render();
  message(text, 'success');
}

function requestOrderReset() {
  if (!items.length && !activeCartOrder) return;
  if (activeCartOrder && !activeCartOrderHasChanges()) {
    finishOrderReset(`${activeCartOrder.name} закрыт. Сохранённый заказ остался в корзине.`);
    return;
  }
  pendingOrderReset = activeCartOrder ? 'cart-dirty' : 'new-order';
  byId('reset-order-title').textContent = activeCartOrder ? 'Сбросить несохранённые изменения?' : 'Сбросить новый заказ?';
  byId('reset-order-text').textContent = activeCartOrder
    ? `Изменения в «${activeCartOrder.name}» не были сохранены. В корзине останется исходный вариант заказа.`
    : 'Все наклейки будут удалены с листов-макетов. Это действие нельзя отменить.';
  byId('reset-order-dialog').showModal();
  byId('reset-order-cancel').focus();
}

function sendCurrentToCart(announce = true) {
  if (!items.length) return null;
  const replacing = Boolean(activeCartOrder);
  const saved = StickerStore.putCartOrder(orderSnapshot(), activeCartOrder);
  if (!saved) {
    showCartFullDialog();
    return null;
  }
  clearLayoutOrder();
  render();
  if (announce) message(replacing ? `${saved.name}: изменения сохранены в корзине. Лист-макет очищен.` : `${saved.name} отправлен в корзину. Лист-макет очищен.`, 'success');
  return saved;
}

function openCartOrderNow(id, notice = '') {
  const saved = StickerStore.getCartOrder(id);
  if (!saved) { renderCartOrders(); return; }
  items = saved.items.map(item => ({ ...item }));
  const packed = pack(items);
  pages = packed.ok ? packed.pages : [];
  if (!packed.ok) items = [];
  active = 0;
  nextId = items.reduce((largest, item) => Math.max(largest, item.id), 0) + 1;
  activeCartOrder = cartMetadata(saved);
  fillDeliveryAddress(saved.address && typeof saved.address === 'object' ? { ...saved.address } : saved.address);
  setCartExpanded(false);
  render();
  message(notice || `${saved.name} открыт для редактирования. Исходный вариант остаётся в корзине.`, 'success');
}

function closeOrderSwitchDialog() {
  pendingOrderSwitchId = null;
  pendingOrderSwitchMode = null;
  if (byId('order-switch-dialog').open) byId('order-switch-dialog').close();
}

function showOrderSwitchDialog(id, mode) {
  const target = StickerStore.getCartOrder(id);
  if (!target) return renderCartOrders();
  pendingOrderSwitchId = id;
  pendingOrderSwitchMode = mode;
  const isNew = mode === 'new-order';
  const cartFull = isNew && StickerStore.cartOrders().length >= StickerStore.limits.cartOrders;
  byId('order-switch-title').textContent = isNew ? 'Сохранить текущий заказ?' : 'Сохранить изменения?';
  byId('order-switch-copy').textContent = isNew
    ? `На листе-макете находится новый несохранённый заказ. После выбора действия будет открыт «${target.name}».`
    : `В заказе «${activeCartOrder.name}» есть несохранённые изменения. После выбора действия будет открыт «${target.name}».`;
  byId('order-switch-save').textContent = isNew ? 'Сохранить в корзине и открыть' : 'Сохранить изменения и открыть';
  byId('order-switch-discard').textContent = isNew ? 'Удалить текущий и открыть' : 'Отменить изменения и открыть';
  byId('order-switch-save').disabled = cartFull;
  byId('order-switch-limit').hidden = !cartFull;
  if (cartFull) byId('order-switch-limit-text').textContent = `Корзина заполнена: уже сохранено ${StickerStore.limits.cartOrders} заказов. Сначала удалите ненужный заказ.`;
  byId('order-switch-dialog').showModal();
  (cartFull ? byId('order-switch-cancel') : byId('order-switch-save')).focus();
}

function loadCartOrder(id) {
  const saved = StickerStore.getCartOrder(id);
  if (!saved) { renderCartOrders(); return; }
  if (activeCartOrder?.id === saved.id) {
    setCartExpanded(false);
    message(`${saved.name} уже открыт на листе-макете.`, 'success');
    return;
  }
  if (items.length && !activeCartOrder) {
    setCartExpanded(false);
    showOrderSwitchDialog(id, 'new-order');
    return;
  }
  if (activeCartOrderHasChanges()) {
    setCartExpanded(false);
    showOrderSwitchDialog(id, 'cart-dirty');
    return;
  }
  openCartOrderNow(id);
}

function showCartFullDialog() {
  byId('cart-full-copy').textContent = `В корзине уже ${StickerStore.limits.cartOrders} заказов. Удалите ненужные заказы, чтобы сохранить новый. Текущий заказ останется на листе-макете.`;
  const dialog = byId('cart-full-dialog');
  if (!dialog.open) dialog.showModal();
  byId('cart-full-open').focus();
}

function formatCartDate(value) {
  return new Intl.DateTimeFormat('ru', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' }).format(new Date(value));
}

function preliminaryOrderPrice(order) {
  return Math.max(1, Number(order.sheetCount) || 0) * exampleSheetPrice;
}

function renderCartOrders() {
  const orders = StickerStore.cartOrders();
  const visibleOrders = orders.slice(0, 10);
  const target = byId('order-items');
  target.replaceChildren();
  if (!orders.length) {
    const empty = document.createElement('p'); empty.className = 'cart-empty'; empty.textContent = 'Корзина пока пуста'; target.append(empty);
  }
  for (const order of visibleOrders) {
    const row = document.createElement('article'); row.className = 'cart-order'; row.dataset.active = String(activeCartOrder?.id === order.id);
    const button = document.createElement('button'); button.type = 'button'; button.className = 'cart-order-button';
    button.title = 'Открыть заказ для продолжения редактирования.';
    const copy = document.createElement('span'); copy.className = 'cart-order-copy';
    const name = document.createElement('strong'); name.textContent = order.name;
    const identity = document.createElement('span'); identity.textContent = `№${order.number} · Изменён ${formatCartDate(order.changedAt)}`;
    const details = document.createElement('span'); details.textContent = `${order.items.length} накл. · ${order.sheetCount || 1} лист.`;
    const price = document.createElement('span'); price.className = 'cart-order-price';
    price.textContent = `Предварительно: ${new Intl.NumberFormat('ru-RU').format(preliminaryOrderPrice(order))} ₽`;
    copy.append(name, identity, details, price);
    if (activeCartOrder?.id === order.id) {
      const status = document.createElement('span'); status.className = 'cart-order-status'; status.textContent = 'Открыт на листе-макете'; copy.append(status);
    }
    const preview = document.createElement('span'); preview.className = 'cart-order-preview'; preview.setAttribute('aria-hidden', 'true');
    const previewItems = order.items.filter((item, index, list) => list.findIndex(candidate => candidate.imageId === item.imageId) === index).slice(0, 3);
    for (const item of previewItems) {
      const sticker = stickerById.get(item.imageId);
      if (!sticker) continue;
      const image = document.createElement('img'); image.src = sticker.src; image.alt = ''; image.loading = 'lazy';
      image.style.transform = item.mirrorHorizontal ? 'scaleX(-1)' : '';
      image.style.filter = stickerFilter(item);
      preview.append(image);
    }
    button.append(copy, preview);
    const menu = document.createElement('div'); menu.className = 'cart-order-menu'; menu.hidden = true;
    const menuToggle = document.createElement('button'); menuToggle.type = 'button'; menuToggle.className = 'cart-order-menu-toggle';
    menuToggle.textContent = '⋮'; menuToggle.title = 'Действия с заказом'; menuToggle.setAttribute('aria-label', `Действия с заказом «${order.name}»`);
    menuToggle.setAttribute('aria-haspopup', 'menu'); menuToggle.setAttribute('aria-expanded', 'false');
    const rename = document.createElement('button'); rename.type = 'button'; rename.textContent = 'Переименовать';
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'cart-delete-action'; remove.textContent = 'Удалить из корзины';
    menu.setAttribute('role', 'menu'); rename.setAttribute('role', 'menuitem'); remove.setAttribute('role', 'menuitem');
    menu.append(rename, remove); row.append(button, menuToggle, menu); target.append(row);
    button.onclick = () => loadCartOrder(order.id);
    const showMenu = event => {
      event.preventDefault(); event.stopPropagation(); closeCartMenus(); menu.hidden = false;
      const buttonRect = button.getBoundingClientRect();
      const preferredX = event.clientX || buttonRect.right - menu.offsetWidth;
      const preferredY = event.clientY || buttonRect.top + 8;
      menu.style.left = `${Math.max(8, Math.min(preferredX, window.innerWidth - menu.offsetWidth - 8))}px`;
      menu.style.top = `${Math.max(8, Math.min(preferredY, window.innerHeight - menu.offsetHeight - 8))}px`;
      menuToggle.setAttribute('aria-expanded', 'true');
      rename.focus();
    };
    menuToggle.onclick = event => {
      if (!menu.hidden) { event.stopPropagation(); closeCartMenus(); menuToggle.focus(); return; }
      showMenu(event);
    };
    rename.onclick = event => { event.stopPropagation(); openCartRename(order.id); };
    remove.onclick = event => { event.stopPropagation(); openCartDelete(order.id); };
  }
  const allOrdersLink = byId('cart-all-orders');
  allOrdersLink.hidden = orders.length <= 10;
  allOrdersLink.textContent = orders.length > 10 ? `••• Ещё ${orders.length - 10}` : '•••';
  byId('cart-count').textContent = String(orders.length);
}

function closeCartMenus() {
  for (const menu of document.querySelectorAll('.cart-order-menu')) menu.hidden = true;
  for (const toggle of document.querySelectorAll('.cart-order-menu-toggle')) toggle.setAttribute('aria-expanded', 'false');
}

function openCartRename(id) {
  const order = StickerStore.getCartOrder(id);
  if (!order) return;
  closeCartMenus(); pendingCartActionId = id;
  byId('cart-rename-input').value = order.name;
  byId('cart-rename-dialog').showModal();
  byId('cart-rename-input').select();
}

function openCartDelete(id) {
  const order = StickerStore.getCartOrder(id);
  if (!order) return;
  closeCartMenus(); pendingCartActionId = id;
  byId('cart-delete-text').textContent = `Удалить «${order.name}» из корзины?`;
  byId('cart-delete-dialog').showModal();
}

document.addEventListener('click', event => { if (!event.target.closest('.cart-order-menu')) closeCartMenus(); });
byId('cart-rename-cancel').onclick = () => { pendingCartActionId = null; byId('cart-rename-dialog').close(); };
byId('cart-rename-form').onsubmit = event => {
  event.preventDefault();
  const id = pendingCartActionId, name = byId('cart-rename-input').value.trim();
  if (!id || !name) return;
  StickerStore.renameCartOrder(id, name);
  if (activeCartOrder?.id === id) activeCartOrder = { ...activeCartOrder, name };
  pendingCartActionId = null; byId('cart-rename-dialog').close(); render();
  message(`Заказ переименован: ${name}.`, 'success');
};
byId('cart-delete-cancel').onclick = () => { pendingCartActionId = null; byId('cart-delete-dialog').close(); };
byId('cart-delete-confirm').onclick = () => {
  const id = pendingCartActionId;
  const removed = id ? StickerStore.removeCartOrder(id) : null;
  if (removed && activeCartOrder?.id === id) activeCartOrder = null;
  pendingCartActionId = null; byId('cart-delete-dialog').close(); render();
  if (removed) message(`${removed.name} удалён из корзины.`, 'success');
};
byId('order-switch-cancel').onclick = closeOrderSwitchDialog;
byId('order-switch-save').onclick = () => {
  const targetId = pendingOrderSwitchId, mode = pendingOrderSwitchMode;
  if (!targetId || !mode) return closeOrderSwitchDialog();
  const savedCurrent = mode === 'new-order'
    ? StickerStore.putCartOrder(orderSnapshot())
    : StickerStore.putCartOrder(orderSnapshot(), activeCartOrder);
  if (!savedCurrent) {
    closeOrderSwitchDialog();
    showCartFullDialog();
    return;
  }
  const target = StickerStore.getCartOrder(targetId);
  closeOrderSwitchDialog();
  openCartOrderNow(targetId, `${savedCurrent.name} ${mode === 'new-order' ? 'сохранён в корзине' : 'обновлён'}. ${target?.name || 'Выбранный заказ'} открыт для редактирования.`);
};
byId('order-switch-discard').onclick = () => {
  const targetId = pendingOrderSwitchId, mode = pendingOrderSwitchMode;
  if (!targetId || !mode) return closeOrderSwitchDialog();
  const previousName = activeCartOrder?.name || 'Текущий заказ';
  const target = StickerStore.getCartOrder(targetId);
  closeOrderSwitchDialog();
  openCartOrderNow(targetId, mode === 'new-order'
    ? `Новый несохранённый заказ удалён. ${target?.name || 'Выбранный заказ'} открыт для редактирования.`
    : `Изменения в «${previousName}» отменены; исходный заказ остался в корзине. ${target?.name || 'Выбранный заказ'} открыт для редактирования.`);
};
byId('reset-order').onclick = requestOrderReset;
byId('reset-order-cancel').onclick = () => {
  pendingOrderReset = null;
  byId('reset-order-dialog').close();
  byId('reset-order').focus();
};
byId('reset-order-confirm').onclick = () => {
  const mode = pendingOrderReset;
  const name = activeCartOrder?.name || '';
  pendingOrderReset = null;
  byId('reset-order-dialog').close();
  finishOrderReset(mode === 'cart-dirty'
    ? `Несохранённые изменения сброшены. Исходный заказ «${name}» остался в корзине.`
    : 'Новый заказ сброшен. Листы-макеты очищены.');
};
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
    for (const child of byId(containerId).children) {
      child.setAttribute('aria-pressed', String(child.textContent === selectedSize));
      child.disabled = Boolean(selectedStickerId && !sizeAllowed(selectedStickerId, child.textContent));
    }
  }
}
function chooseSize(size) {
  if (selectedStickerId && !sizeAllowed(selectedStickerId, size)) { message(sizeAdvice(selectedStickerId), '', true); return; }
  selectedSize = selectedSize === size ? null : size;
  syncSizeControls();
  message(selectedSize === 'A' && selectedStickerId ? sizeAdvice(selectedStickerId) : '');
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
  if (!sizeAllowed(sticker.id, selectedSize)) { message(sizeAdvice(sticker.id), '', true); return; }
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
    byId('overflow-next').textContent = result.reason === 'item-limit'
      ? `В одном заказе может быть не больше ${config.maxItems} наклеек. Сохраните текущий заказ в корзине и продолжите с новым листом-макетом — оплачивать заказ для этого не нужно.`
      : `В заказ добавлено всё, что удалось разместить в пределах ${config.maxSheets} листов. Сохраните его в корзине и продолжите с новым листом-макетом — оплачивать заказ для этого не нужно.`;
    byId('overflow-checkout').disabled = items.length === 0;
    byId('overflow-dialog').showModal();
  }
  if (result.added.length) showAdditionFeedback(sticker, selectedSize, result.added);
}
function selectSticker(id) {
  selectedStickerId = id;
  if (selectedSize && id && !sizeAllowed(id, selectedSize)) selectedSize = null;
  syncSizeControls();
  byId('selected-sticker').textContent = id ? 'Выбрано: ' + stickerById.get(id).name : 'Наклейка не выбрана';
  for (const card of byId('sticker-grid').children) {
    const selected = card.dataset.stickerId === id;
    card.dataset.selected = String(selected);
    card.querySelector('button').setAttribute('aria-pressed', String(selected));
  }
  message(id ? sizeAdvice(id) : '');
}
function updatePreview(sticker, open = false, historyMode = open ? 'push' : 'replace') {
  if (!sticker) return;
  if (catalogReady && !cardsById.has(sticker.id)) ensureStickerRendered(sticker.id);
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
  refreshFavoriteControls();
  syncSizeControls();
  if (open && !preview.open) {
    byId('preview-quantity').value = '';
    byId('preview-quantity').removeAttribute('aria-invalid');
    preview.showModal();
  }
  if (catalogReady && historyMode !== 'none') writeCatalogUrl(historyMode, sticker.id);
}
function movePreview(offset) {
  const index = visibleStickers.findIndex(sticker => sticker.id === selectedStickerId);
  const target = visibleStickers[index + offset];
  if (target) updatePreview(target);
}
function createCard(sticker) {
  const card = document.createElement('article');
  card.className = 'card'; card.dataset.stickerId = sticker.id;
  cardsById.set(sticker.id, card);
  const button = document.createElement('button');
  button.className = 'image-button'; button.type = 'button';
  button.setAttribute('aria-label', 'Рассмотреть наклейку ' + sticker.name);
  const image = document.createElement('img');
  image.src = sticker.src; image.alt = sticker.name; image.draggable = false; image.loading = 'lazy'; image.decoding = 'async';
  sources.set(sticker.id, image);
  const heading = document.createElement('h2'); heading.textContent = sticker.name;
  const favorite = document.createElement('button');
  favorite.className = 'favorite-toggle card-favorite'; favorite.type = 'button';
  favorite.onclick = () => toggleFavorite(sticker.id);
  const addButton = document.createElement('button');
  addButton.className = 'card-add'; addButton.type = 'button'; addButton.textContent = 'Добавить';
  addButton.setAttribute('aria-label', `Добавить наклейку «${sticker.name}» на лист-макет`);
  addButton.onclick = () => { selectSticker(sticker.id); add(); };
  button.append(image); card.append(button, favorite, heading, addButton);
  setFavoriteButtonState(favorite, sticker.id);
  button.onclick = () => updatePreview(sticker, true, 'push');
  return card;
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
  return {
    query: byId('search-query').value.trim(),
    filters: currentFilters(),
    scope: byId('search-scope').value,
    sort: byId('sort-results').value,
  };
}
function criteriaCanRun(criteria = currentCriteria()) {
  return Boolean(criteria.filters.section || criteria.query);
}
function searchesGlobally(criteria = currentCriteria()) {
  return Boolean(criteria.query && (criteria.scope === 'all' || !criteria.filters.section));
}
function optionLabel(id, value) {
  const option = byId(id).querySelector(`option[value="${CSS.escape(value)}"]`);
  return option?.textContent || value;
}
function replaceFilterOptions(id, options, emptyLabel, selected = '') {
  const select = byId(id);
  select.replaceChildren(new Option(emptyLabel, ''));
  addOptions(select, options);
  select.value = [...select.options].some(option => option.value === selected) ? selected : '';
}
function valuesForSection(section, field) {
  const values = new Set();
  for (const sticker of stickers) {
    if (!sticker.entry.sections?.includes(section)) continue;
    if (field === 'character') {
      if (sticker.entry.character_id) values.add(sticker.entry.character_id);
    } else {
      for (const value of sticker.entry.field_concepts?.[field] || []) values.add(value);
    }
  }
  return values;
}
function refreshDependentFilters(preserve = true) {
  const section = byId('filter-section').value;
  const current = {
    character: preserve ? byId('filter-character').value : '',
    role: preserve ? byId('filter-role').value : '',
    mood: preserve ? byId('filter-mood').value : '',
  };
  const definitions = [
    ['filter-character', 'characters', 'character', 'Все персонажи'],
    ['filter-role', 'roles', 'role', 'Все роли'],
    ['filter-mood', 'moods', 'mood', 'Все настроения'],
  ];
  for (const [id, optionsKey, field, label] of definitions) {
    const allowed = section ? valuesForSection(section, field) : new Set();
    const options = catalogFilterOptions[optionsKey].filter(option => allowed.has(option.value));
    replaceFilterOptions(id, options, label, current[field]);
    byId(id).disabled = !section;
  }
}
function currentFilterCount(criteria = currentCriteria()) {
  return Object.values(criteria.filters).filter(Boolean).length;
}
function previewMatchCount(criteria = currentCriteria()) {
  if (!searchEngine || !criteriaCanRun(criteria)) return 0;
  const effectiveFilters = searchesGlobally(criteria) ? {} : criteria.filters;
  return searchEngine.run(criteria.query, effectiveFilters).length;
}
function updateFilterSummary() {
  const criteria = currentCriteria();
  const count = currentFilterCount(criteria);
  const badge = byId('filter-count');
  badge.hidden = count === 0;
  badge.textContent = String(count);
  const filterApply = byId('apply-filters');
  const matches = previewMatchCount(criteria);
  filterApply.disabled = !criteria.filters.section || !criteriaChanged();
  filterApply.textContent = criteria.filters.section ? `Показать: ${matches}` : 'Показать наклейки';
}
function renderActiveFilterChips() {
  const host = byId('active-filter-chips');
  host.replaceChildren();
  const criteria = appliedCriteria;
  if (!criteria || searchesGlobally(criteria)) return;
  const definitions = [
    ['section', 'filter-section', 'Раздел'],
    ['character', 'filter-character', 'Персонаж'],
    ['role', 'filter-role', 'Роль'],
    ['mood', 'filter-mood', 'Настроение'],
  ];
  for (const [key, id, label] of definitions) {
    const value = criteria.filters[key];
    if (!value) continue;
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'filter-chip';
    chip.textContent = `${label}: ${optionLabel(id, value)} ×`;
    chip.setAttribute('aria-label', `Убрать фильтр «${label}: ${optionLabel(id, value)}»`);
    chip.onclick = () => {
      byId(id).value = '';
      if (key === 'section') refreshDependentFilters(false);
      appliedCriteria = null;
      applyCatalogSearch({ historyMode:'push', force:true });
    };
    host.append(chip);
  }
}
function criteriaChanged() {
  return JSON.stringify(currentCriteria()) !== JSON.stringify(appliedCriteria);
}
function markSearchPending() {
  if (!searchEngine) return;
  if (byId('search-query').value.trim() && !byId('filter-section').value) byId('search-scope').value = 'all';
  const pending = criteriaChanged();
  const hasExecutableQuery = criteriaCanRun();
  byId('apply-search').disabled = !pending || !hasExecutableQuery;
  byId('clear-filters').disabled = !byId('search-query').value.trim() && !byId('filter-section').value && !byId('filter-character').value && !byId('filter-role').value && !byId('filter-mood').value && byId('search-scope').value === 'selection' && byId('sort-results').value === 'relevance';
  if (pending) byId('search-status').textContent = hasExecutableQuery
    ? 'Нажмите Enter или «Найти», чтобы применить изменения'
    : 'Введите запрос или выберите обязательный раздел';
  updateFilterSummary();
}

function sortMatches(results, sort) {
  if (sort === 'name') {
    const collator = new Intl.Collator('ru', { sensitivity:'base', numeric:true });
    return [...results].sort((a, b) => collator.compare(a.name, b.name) || a.entry.order - b.entry.order);
  }
  if (sort === 'catalog') return [...results].sort((a, b) => a.entry.order - b.entry.order);
  return results;
}

function arrangeMatches(matches, criteria) {
  if (criteria.query || criteria.sort !== 'relevance') return sortMatches(matches, criteria.sort);
  return CatalogRanking.rank(matches, {
    seed:mixSeed,
    stats:catalogRankingStats,
    reservedCount:10,
    maximumRun:2,
  });
}

function urlState(sticker = '') {
  const criteria = appliedCriteria || currentCriteria();
  return {
    ...criteria,
    shown: loadedResultCount > resultPageSize ? loadedResultCount : 0,
    sticker,
    mix:mixSeed,
  };
}

function replaceHistoryScroll() {
  history.replaceState({ ...(history.state || {}), catalog:true, scrollY:window.scrollY }, '', window.location.href);
}

function writeCatalogUrl(mode = 'push', sticker = '') {
  const search = CatalogState.write(window.location.search, urlState(sticker));
  const url = `${window.location.pathname}${search}${window.location.hash}`;
  if (mode === 'push') {
    replaceHistoryScroll();
    history.pushState({ catalog:true, scrollY:0, previewEntry:Boolean(sticker) }, '', url);
  } else if (mode === 'replace') {
    history.replaceState({ ...(history.state || {}), catalog:true, scrollY:window.scrollY, previewEntry:Boolean(sticker) }, '', url);
  }
}

function setControlValue(id, value) {
  const control = byId(id);
  control.value = [...control.options].some(option => option.value === value) ? value : '';
}

function fillControlsFromUrl(state) {
  byId('search-query').value = state.query;
  setControlValue('filter-section', state.filters.section);
  refreshDependentFilters(false);
  const ids = { character:'filter-character', role:'filter-role', mood:'filter-mood' };
  for (const [key, id] of Object.entries(ids)) setControlValue(id, state.filters[key]);
  byId('search-scope').value = state.scope;
  byId('sort-results').value = state.sort;
}

function updateGlobalSuggestion(criteria) {
  const button = byId('search-all-suggestion');
  button.hidden = true;
  if (allMatches.length || !criteria.query || criteria.scope === 'all' || !Object.values(criteria.filters).some(Boolean)) return;
  const count = searchEngine.run(criteria.query, {}).length;
  if (!count) return;
  button.textContent = `Найдено во всём каталоге: ${count} · Показать`;
  button.hidden = false;
}

function renderResultPage() {
  visibleStickers = allMatches.slice(0, loadedResultCount);
  const visibleIds = new Set(visibleStickers.map(sticker => sticker.id));
  const grid = byId('sticker-grid');
  const fragment = document.createDocumentFragment();
  for (const sticker of visibleStickers) {
    const card = cardsById.get(sticker.id) || createCard(sticker);
    fragment.append(card);
  }
  grid.replaceChildren(fragment);
  if (!visibleIds.has(selectedStickerId)) selectSticker(visibleStickers[0]?.id || null);
  const remaining = allMatches.length - visibleStickers.length;
  byId('show-more-results').hidden = remaining <= 0;
  byId('show-more-results').textContent = remaining > 0 ? `Показать ещё ${Math.min(resultPageSize, remaining)}` : 'Показать ещё';
  const criteria = appliedCriteria || currentCriteria();
  const globalResults = searchesGlobally(criteria);
  const place = globalResults ? 'во всём каталоге' : 'в выбранной подборке';
  byId('search-status').textContent = allMatches.length
    ? `Найдено ${place}: ${allMatches.length} · показано: ${visibleStickers.length}`
    : `В ${place === 'во всём каталоге' ? 'каталоге' : 'выбранной подборке'} ничего не найдено`;
  updateGlobalSuggestion(criteria);
}

function ensureStickerRendered(stickerId) {
  if (cardsById.has(stickerId)) return;
  const index = allMatches.findIndex(sticker => sticker.id === stickerId);
  if (index < 0) return;
  loadedResultCount = Math.min(allMatches.length, Math.max(loadedResultCount, Math.ceil((index + 1) / resultPageSize) * resultPageSize));
  renderResultPage();
}

function resetCatalogCards() {
  cardsById.clear();
  sources.clear();
  byId('sticker-grid').replaceChildren();
}

function applyCatalogSearch(options = {}) {
  if (!searchEngine) return;
  const { historyMode = 'push', shown = 0, restoreScroll = null, force = false } = options;
  const criteria = currentCriteria();
  const { query, filters } = criteria;
  if (!query) {
    criteria.scope = 'selection';
    byId('search-scope').value = 'selection';
  } else if (!filters.section) {
    criteria.scope = 'all';
    byId('search-scope').value = 'all';
  }
  if (!criteriaCanRun(criteria)) {
    allMatches = [];
    loadedResultCount = 0;
    resetCatalogCards();
    renderResultPage();
    appliedCriteria = null;
    byId('apply-search').disabled = true;
    byId('search-all-suggestion').hidden = true;
    byId('search-status').textContent = 'Введите название, тему или роль либо выберите обязательный раздел.';
    renderActiveFilterChips();
    updateFilterSummary();
    if (historyMode !== 'none') writeCatalogUrl(historyMode);
    return;
  }
  if (!force && !criteriaChanged()) return;
  if (!mixSeed || historyMode === 'push') mixSeed = CatalogRanking.createSeed();
  const effectiveFilters = searchesGlobally(criteria) ? {} : filters;
  const matches = searchEngine.run(query, effectiveFilters).map(result => stickerById.get(result.entry.image_id));
  allMatches = arrangeMatches(matches, criteria);
  loadedResultCount = Math.min(Math.max(resultPageSize, shown || 0), allMatches.length);
  resetCatalogCards();
  appliedCriteria = criteria;
  renderResultPage();
  byId('apply-search').disabled = true;
  byId('clear-filters').disabled = !query && !filters.section && !filters.character && !filters.role && !filters.mood && criteria.scope === 'selection' && criteria.sort === 'relevance';
  renderActiveFilterChips();
  updateFilterSummary();
  if (historyMode !== 'none') writeCatalogUrl(historyMode);
  if (restoreScroll !== null) requestAnimationFrame(() => window.scrollTo({ top:restoreScroll, behavior:'instant' }));
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
    const [catalogResponse, dictionaryResponse, rulesResponse] = await Promise.all([
      fetch('catalog-data/site_catalog.json'),
      fetch('catalog-data/global_search_dictionary.v1.json'),
      fetch('catalog-data/cut_size_rules.json'),
    ]);
    if (!catalogResponse.ok || !dictionaryResponse.ok || !rulesResponse.ok) throw new Error('catalog data unavailable');
    const [catalog, dictionary, rules] = await Promise.all([catalogResponse.json(), dictionaryResponse.json(), rulesResponse.json()]);
    if (rules.schema_version !== 1 || !rules.rules || typeof rules.rules !== 'object') throw new Error('size rules unavailable');
    sizeRules = rules.rules;
    stickers = catalog.entries.map(entry => ({ id:entry.image_id, name:entry.display_name, src:entry.src, entry }));
    stickerById = new Map(stickers.map(sticker => [sticker.id, sticker]));
    searchEngine = CatalogSearch.createEngine(catalog, dictionary);
    catalogRankingStats = catalog.ranking_stats && typeof catalog.ranking_stats === 'object' ? catalog.ranking_stats : {};
    addOptions(byId('filter-section'), catalog.filters.sections);
    defaultSection = '';
    catalogFilterOptions = {
      characters: catalog.filters.characters,
      roles: catalog.filters.roles,
      moods: catalog.filters.moods,
    };
    const incoming = CatalogState.read(window.location.search);
    mixSeed = incoming.mix || CatalogRanking.createSeed();
    fillControlsFromUrl(incoming);
    if (incoming.query && !incoming.filters.section) byId('search-scope').value = 'all';
    catalogReady = true;
    applyCatalogSearch({ historyMode:'replace', shown:incoming.shown, force:true, restoreScroll:history.state?.scrollY ?? null });
    if (incoming.sticker && stickerById.has(incoming.sticker) && allMatches.some(sticker => sticker.id === incoming.sticker)) {
      ensureStickerRendered(incoming.sticker);
      updatePreview(stickerById.get(incoming.sticker), true, 'none');
    }
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
byId('filter-section').addEventListener('change', () => {
  refreshDependentFilters(false);
  byId('search-scope').value = byId('filter-section').value ? 'selection' : (byId('search-query').value.trim() ? 'all' : 'selection');
  markSearchPending();
});
for (const id of ['filter-character','filter-role','filter-mood','search-scope']) {
  byId(id).addEventListener('change', markSearchPending);
  byId(id).addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.isComposing) { event.preventDefault(); applyCatalogSearch(); }
  });
}
byId('sort-results').addEventListener('change', () => {
  if (criteriaCanRun()) applyCatalogSearch({ historyMode:'push', force:true });
  else markSearchPending();
});
byId('apply-search').onclick = applyCatalogSearch;
byId('apply-filters').onclick = () => {
  applyCatalogSearch();
  byId('catalog-filters').hidden = true;
  byId('filter-toggle').setAttribute('aria-expanded', 'false');
};
byId('filter-toggle').onclick = () => {
  const panel = byId('catalog-filters');
  panel.hidden = !panel.hidden;
  byId('filter-toggle').setAttribute('aria-expanded', String(!panel.hidden));
  if (!panel.hidden) byId('filter-section').focus();
};
document.addEventListener('click', event => {
  if (event.target.closest('.catalog-search')) return;
  byId('catalog-filters').hidden = true;
  byId('filter-toggle').setAttribute('aria-expanded', 'false');
});
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || byId('catalog-filters').hidden) return;
  byId('catalog-filters').hidden = true;
  byId('filter-toggle').setAttribute('aria-expanded', 'false');
  byId('filter-toggle').focus();
});
byId('show-more-results').onclick = () => {
  loadedResultCount = Math.min(loadedResultCount + resultPageSize, allMatches.length);
  renderResultPage();
  writeCatalogUrl('replace', byId('preview').open && byId('preview').dataset.mode === 'catalog' ? selectedStickerId : '');
};
byId('clear-filters').onclick = () => {
  byId('search-query').value = '';
  byId('filter-section').value = '';
  refreshDependentFilters(false);
  byId('search-scope').value = 'selection';
  byId('sort-results').value = 'relevance';
  appliedCriteria = null;
  applyCatalogSearch({ historyMode:'push', force:true });
};
byId('search-all-suggestion').onclick = () => {
  byId('search-scope').value = 'all';
  applyCatalogSearch({ historyMode:'push', force:true });
};

history.scrollRestoration = 'manual';
window.addEventListener('scroll', () => {
  if (!catalogReady || scrollStateFrame) return;
  scrollStateFrame = requestAnimationFrame(() => {
    scrollStateFrame = 0;
    replaceHistoryScroll();
  });
}, { passive:true });
window.addEventListener('popstate', event => {
  if (!catalogReady) return;
  const state = CatalogState.read(window.location.search);
  mixSeed = state.mix || CatalogRanking.createSeed();
  applyingHistoryState = true;
  fillControlsFromUrl(state);
  appliedCriteria = null;
  applyCatalogSearch({ historyMode:'none', shown:state.shown, force:true, restoreScroll:event.state?.scrollY ?? 0 });
  if (!state.mix) writeCatalogUrl('replace', state.sticker);
  const preview = byId('preview');
  const sticker = stickerById.get(state.sticker);
  if (sticker && allMatches.some(item => item.id === sticker.id)) updatePreview(sticker, true, 'none');
  else if (preview.open && preview.dataset.mode === 'catalog') preview.close();
  applyingHistoryState = false;
});
window.addEventListener('beforeunload', replaceHistoryScroll);
byId('preview-add').onclick = add;
byId('undo-addition').onclick = undoLastAddition;
function closePreviewWithHistory() {
  const preview = byId('preview');
  if (!preview.open) return;
  if (preview.dataset.mode !== 'catalog') { preview.close(); return; }
  if (history.state?.previewEntry) history.back();
  else {
    applyingHistoryState = true;
    preview.close();
    applyingHistoryState = false;
    writeCatalogUrl('replace');
  }
}
byId('close-preview').onclick = closePreviewWithHistory;
byId('preview').addEventListener('cancel', event => {
  if (byId('preview').dataset.mode !== 'catalog') return;
  event.preventDefault();
  closePreviewWithHistory();
});
byId('preview').addEventListener('close', () => {
  if (!catalogReady || applyingHistoryState || byId('preview').dataset.mode !== 'catalog') return;
  if (CatalogState.read(window.location.search).sticker) writeCatalogUrl('replace');
});
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
  applyingHistoryState = true;
  byId('preview').close();
  applyingHistoryState = false;
  byId('search-query').value = '';
  byId('filter-section').value = sticker.entry.sections[0] || '';
  refreshDependentFilters(false);
  byId('filter-character').value = sticker.entry.character_id;
  byId('filter-role').value = '';
  byId('filter-mood').value = '';
  byId('search-scope').value = 'selection';
  appliedCriteria = null;
  mixSeed = CatalogRanking.createSeed();
  applyCatalogSearch({ historyMode:'replace', force:true });
  byId('search-status').textContent = `Коллекция персонажа «${sticker.entry.character_name}»: ${visibleStickers.length}`;
};
byId('preview-favorite').onclick = () => toggleFavorite(catalogPreviewStickerId || selectedStickerId);
byId('favorite-auth-close').onclick = () => byId('favorite-auth-dialog').close();
byId('layout-checkout').onclick = () => { window.location.href = 'checkout.html?step=1'; };
byId('send-to-cart').onclick = () => sendCurrentToCart();
byId('close-checkout').onclick = () => byId('checkout-dialog').close();
byId('back-to-layout').onclick = () => byId('checkout-dialog').close();
for (const id of Object.values(addressFields)) byId(id).addEventListener('input', () => {
  byId('checkout-feedback').textContent = '';
  byId('saved-address').value = '';
  updateActiveOrderStatus();
  persistCurrentOrder();
});
byId('saved-address').addEventListener('change', () => {
  const saved = StickerStore.addresses().find(item => item.id === byId('saved-address').value);
  if (saved) fillDeliveryAddress(saved.address);
  else fillDeliveryAddress('');
  updateActiveOrderStatus();
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
  updateActiveOrderStatus();
  persistCurrentOrder();
  byId('checkout-feedback').textContent = 'Адрес заполнен и сохранён с текущим заказом. Отправка заказа пока не подключена.';
};
byId('close-overflow').onclick = () => byId('overflow-dialog').close();
byId('overflow-checkout').onclick = () => { byId('overflow-dialog').close(); window.location.href = 'checkout.html?step=1'; };
byId('overflow-save-cart').onclick = () => {
  byId('overflow-dialog').close();
  hideAdditionFeedback();
  const saved = sendCurrentToCart(false);
  if (saved) message(`${saved.name} сохранён в корзине. Лист-макет свободен — можно продолжать набор.`, 'success');
};
byId('cart-full-stay').onclick = () => byId('cart-full-dialog').close();
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
  for (const button of byId('inspector-sizes').children) {
    button.setAttribute('aria-pressed', String(button.dataset.size === pendingInspectorSize));
    button.disabled = !sizeAllowed(item.imageId, button.dataset.size);
  }
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
  refreshDependentFilters(false);
  byId('search-scope').value = 'all';
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
    byId('inspector-message').textContent = packed.reason === 'item-limit'
      ? `В одном заказе может быть не больше ${config.maxItems} наклеек.`
      : `Ещё одна наклейка не помещается в предел ${config.maxSheets} листов.`;
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
  if (!sizeAllowed(selected.imageId, pendingInspectorSize || selected.size)) {
    byId('inspector-message').textContent = sizeAdvice(selected.imageId); return;
  }
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
  if (!packed.ok) { byId('inspector-message').textContent = `Изменение не помещается в предел ${config.maxSheets} листов.`; return; }
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
  byId('preview-favorite').hidden = true;
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
  updateActiveOrderStatus();
  byId('sheet-title').textContent = pages.length ? 'Лист ' + (active + 1) : 'Лист-макет';
  byId('sheet-count').textContent = pages.length ? `Листов: ${pages.length}` : '';
  const sheet = byId('sheet-layout'); sheet.replaceChildren(); draw(sheet, pages[active] || []);
  if (!items.length) { const empty = document.createElement('p'); empty.className = 'empty-sheet'; empty.textContent = 'Здесь появятся выбранные наклейки'; sheet.append(empty); }
  const technical = document.createElement('div'); technical.className = 'technical'; technical.textContent = 'Место для технических отметок'; position(technical, { x:config.margins.left, y:config.sheet.height - config.margins.bottom - config.technicalHeight, width:area().w, height:config.technicalHeight }); sheet.append(technical);
  const list = byId('sheet-list'); list.replaceChildren();
  pages.forEach((page, index) => {
    if (index === active) return;
    const button = document.createElement('button'); button.className = 'sheet-tab'; button.setAttribute('aria-label', 'Открыть лист ' + (index + 1));
    button.title = 'Открыть лист ' + (index + 1);
    const mini = document.createElement('span'); mini.className = 'mini-sheet'; draw(mini, page, true);
    const number = document.createElement('span'); number.className = 'sheet-tab-number'; number.textContent = index + 1;
    button.append(mini, number); button.onclick = () => { active = index; render(); }; list.append(button);
  });
  renderCartOrders();
  byId('layout-checkout').disabled = items.length === 0;
  byId('send-to-cart').disabled = items.length === 0;
  byId('reset-order').disabled = items.length === 0 && !activeCartOrder;
  byId('send-to-cart').textContent = activeCartOrder ? 'Сохранить изменения и отправить в корзину' : 'Отправить в корзину';
  persistCurrentOrder();
}
render();
loadCatalog();
