const account = StickerStore.account();
const signedIn = StickerStore.signedIn();
const byId = id => document.getElementById(id);
const { config, pack, fitAddition } = StickerLayout;
let catalogById = new Map();
let pendingCartId = null;
let pendingAddressId = null;
let pendingCartOpenId = null;
let pendingCartOpenMode = null;
let favoriteSize = null;
let favoritesBusy = false;
const aspectCache = new Map();
const cabinetAddressFields = {
  recipient: 'cabinet-recipient', phone: 'cabinet-phone', country: 'cabinet-country', postalCode: 'cabinet-postal-code',
  region: 'cabinet-region', city: 'cabinet-city', street: 'cabinet-street', house: 'cabinet-house',
  apartment: 'cabinet-apartment', comment: 'cabinet-comment',
};

byId('signed-out-view').hidden = signedIn;
byId('cabinet-view').hidden = !signedIn;
byId('cabinet-logout').hidden = !signedIn;

function formatDate(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat('ru', { dateStyle:'medium', timeStyle:'short' }).format(new Date(value));
}

function formatAddress(address) {
  if (!address) return '';
  if (typeof address === 'string') return address;
  return [
    address.recipient,
    address.phone && `Телефон: ${address.phone}`,
    [address.postalCode, address.country].filter(Boolean).join(', '),
    [address.region, address.city].filter(Boolean).join(', '),
    [address.street, address.house && `дом ${address.house}`, address.apartment && `кв./офис ${address.apartment}`].filter(Boolean).join(', '),
    address.comment && `Комментарий: ${address.comment}`,
  ].filter(Boolean).join('\n');
}

function readCabinetAddress() {
  return Object.fromEntries(Object.entries(cabinetAddressFields).map(([key, id]) => [key, byId(id).value.trim()]));
}

function closeCabinetAddressForm() {
  byId('cabinet-address-form').reset();
  byId('cabinet-address-form').hidden = true;
  byId('open-address-form').hidden = false;
}

function groupItems(items) {
  const groups = new Map();
  for (const item of items) {
    const key = `${item.imageId}|${item.size}`;
    const group = groups.get(key) || {
      name: catalogById.get(item.imageId)?.display_name || item.imageId,
      size: item.size,
      count: 0,
    };
    group.count += 1;
    groups.set(key, group);
  }
  return [...groups.values()];
}

function renderCurrentOrder() {
  const order = StickerStore.currentOrder();
  const empty = order.items.length === 0;
  byId('favorites-to-layout').hidden = empty;
  byId('cabinet-order-empty').hidden = !empty;
  byId('cabinet-order-content').hidden = empty;
  byId('menu-order-count').textContent = String(order.items.length);
  byId('order-title').textContent = order.cartOrder?.name || 'Текущий заказ';
  byId('order-updated').textContent = order.updatedAt && !empty ? `Обновлён ${formatDate(order.updatedAt)}` : '';
  if (empty) return;

  const container = byId('cabinet-order-items');
  container.replaceChildren();
  for (const group of groupItems(order.items)) {
    const line = document.createElement('div');
    line.className = 'order-line';
    const name = document.createElement('strong'); name.textContent = group.name;
    const details = document.createElement('span'); details.textContent = `Размер ${group.size} × ${group.count}`;
    line.append(name, details); container.append(line);
  }
  byId('cabinet-sticker-total').textContent = `Наклеек: ${order.items.length}`;
  byId('cabinet-sheet-total').textContent = order.sheetCount ? `Листов: ${order.sheetCount}` : 'Листы пересчитаются в каталоге';
  const address = byId('cabinet-address');
  address.hidden = !order.address;
  address.querySelector('p').textContent = formatAddress(order.address);
}

function drawDraftPreview(target, draft) {
  let packed;
  try { packed = pack(draft.items); } catch { return; }
  if (!packed.ok || !packed.pages.length) return;
  for (const placement of packed.pages[0]) {
    const entry = catalogById.get(placement.imageId);
    if (!entry) continue;
    const image = document.createElement('img');
    image.src = entry.src; image.alt = '';
    image.style.left = `${placement.x / config.sheet.width * 100}%`;
    image.style.top = `${placement.y / config.sheet.height * 100}%`;
    image.style.width = `${placement.width / config.sheet.width * 100}%`;
    image.style.height = `${placement.height / config.sheet.height * 100}%`;
    image.style.transform = `rotate(${placement.rotated ? 90 : 0}deg)`;
    target.append(image);
  }
  if (packed.pages.length > 1) {
    const more = document.createElement('span');
    more.className = 'draft-more-sheets';
    more.textContent = `+${packed.pages.length - 1} лист.`;
    target.append(more);
  }
}

function draftButton(label, className, action, id) {
  const button = document.createElement('button');
  button.type = 'button'; button.textContent = label; button.className = className;
  button.addEventListener('click', () => action(id));
  return button;
}

function setCartOrdersMessage(text = '', tone = '') {
  const target = byId('cart-orders-message');
  target.textContent = text;
  target.dataset.tone = tone;
}

function renderCartOrders() {
  const orders = StickerStore.cartOrders();
  byId('menu-cart-count').textContent = String(orders.length);
  byId('cart-orders-empty').hidden = orders.length > 0;
  const list = byId('cart-orders-list');
  list.replaceChildren();
  for (const order of orders) {
    const card = document.createElement('article'); card.className = 'draft-card cart-order-card';
    const preview = document.createElement('div'); preview.className = 'draft-preview';
    preview.setAttribute('aria-label', `Первый лист заказа «${order.name}»`);
    drawDraftPreview(preview, order);
    const info = document.createElement('div'); info.className = 'draft-info';
    const title = document.createElement('h3'); title.textContent = order.name;
    const meta = document.createElement('p'); meta.className = 'draft-meta';
    meta.textContent = `${order.items.length} накл. · ${order.sheetCount || 1} лист. · Изменён ${formatDate(order.changedAt)}`;
    const buttons = document.createElement('div'); buttons.className = 'draft-buttons';
    buttons.append(
      draftButton('Открыть', 'continue-draft', activateCartOrder, order.id),
      draftButton('Переименовать', '', openCartRenameDialog, order.id),
    );
    const remove = document.createElement('button');
    remove.type = 'button'; remove.className = 'cart-order-delete'; remove.textContent = '×';
    remove.setAttribute('aria-label', `Удалить заказ «${order.name}» из корзины`);
    remove.title = 'Удалить заказ из корзины';
    remove.addEventListener('click', () => openCartDeleteDialog(order.id));
    info.append(title, meta, buttons); card.append(preview, info, remove); list.append(card);
  }
}

function comparableOrderItems(items = []) {
  return items.map(item => JSON.stringify({
    imageId:item.imageId, size:item.size, aspect:Number(item.aspect),
    mirrorHorizontal:Boolean(item.mirrorHorizontal), grayscale:Boolean(item.grayscale), sepia:Boolean(item.sepia),
    brightnessLevel:Number(item.brightnessLevel) || 0, saturationLevel:Number(item.saturationLevel) || 0,
  })).sort();
}

function comparableOrderAddress(address) {
  if (!address) return {};
  if (typeof address === 'string') return { street:address.trim() };
  return Object.fromEntries(Object.keys(address).sort().map(key => [key, String(address[key] || '').trim()]));
}

function currentCartOrderHasChanges(current) {
  if (!current.cartOrder?.id) return false;
  const saved = StickerStore.getCartOrder(current.cartOrder.id);
  if (!saved) return false;
  return JSON.stringify(comparableOrderItems(current.items)) !== JSON.stringify(comparableOrderItems(saved.items))
    || JSON.stringify(comparableOrderAddress(current.address)) !== JSON.stringify(comparableOrderAddress(saved.address));
}

function openCartOrderNow(id) {
  const order = StickerStore.getCartOrder(id);
  if (!order) return renderCartOrders();
  StickerStore.replaceCurrentOrder({
    ...order,
    cartOrder: { id:order.id, number:order.number, name:order.name, changedAt:order.changedAt },
  });
  window.location.href = 'catalog.html';
}

function closeAccountOrderSwitchDialog() {
  pendingCartOpenId = null;
  pendingCartOpenMode = null;
  if (byId('account-order-switch-dialog').open) byId('account-order-switch-dialog').close();
}

function showAccountOrderSwitchDialog(id, mode) {
  const target = StickerStore.getCartOrder(id);
  if (!target) return renderCartOrders();
  const current = StickerStore.currentOrder();
  const isNew = mode === 'new-order';
  const cartFull = isNew && StickerStore.cartOrders().length >= StickerStore.limits.cartOrders;
  pendingCartOpenId = id;
  pendingCartOpenMode = mode;
  byId('account-order-switch-title').textContent = isNew ? 'Сохранить текущий заказ?' : 'Сохранить изменения?';
  byId('account-order-switch-copy').textContent = isNew
    ? `На листе-макете находится новый несохранённый заказ. После выбора действия будет открыт «${target.name}».`
    : `В заказе «${current.cartOrder.name}» есть несохранённые изменения. После выбора действия будет открыт «${target.name}».`;
  byId('account-order-switch-save').textContent = isNew ? 'Сохранить в корзине и открыть' : 'Сохранить изменения и открыть';
  byId('account-order-switch-discard').textContent = isNew ? 'Удалить текущий и открыть' : 'Отменить изменения и открыть';
  byId('account-order-switch-save').disabled = cartFull;
  byId('account-order-switch-limit').hidden = !cartFull;
  if (cartFull) byId('account-order-switch-limit').textContent = `Корзина заполнена: уже сохранено ${StickerStore.limits.cartOrders} заказов. Сначала удалите ненужный заказ.`;
  byId('account-order-switch-dialog').showModal();
}

function activateCartOrder(id) {
  const current = StickerStore.currentOrder();
  if (current.cartOrder?.id === id) {
    setCartOrdersMessage('Этот заказ уже открыт на листе-макете.', 'success');
    return;
  }
  if (current.items.length && !current.cartOrder) return showAccountOrderSwitchDialog(id, 'new-order');
  if (currentCartOrderHasChanges(current)) return showAccountOrderSwitchDialog(id, 'cart-dirty');
  openCartOrderNow(id);
}

function openCartRenameDialog(id) {
  const order = StickerStore.cartOrders().find(item => item.id === id);
  if (!order) return;
  pendingCartId = id;
  byId('cart-name').value = order.name;
  byId('cart-name-dialog').showModal();
  byId('cart-name').select();
}

function openCartDeleteDialog(id) {
  const order = StickerStore.getCartOrder(id);
  if (!order) return;
  pendingCartId = id;
  byId('delete-cart-copy').textContent = `Удалить заказ «${order.name}» из корзины?`;
  byId('delete-cart-dialog').showModal();
}

function renderAddresses() {
  const defaultId = StickerStore.defaultAddressId();
  const addresses = StickerStore.addresses().sort((first, second) => Number(second.id === defaultId) - Number(first.id === defaultId));
  byId('menu-address-count').textContent = String(addresses.length);
  byId('addresses-empty').hidden = addresses.length > 0;
  const list = byId('addresses-list');
  list.replaceChildren();
  for (const saved of addresses) {
    const card = document.createElement('article'); card.className = 'address-card';
    const heading = document.createElement('h3');
    heading.textContent = saved.address.city || saved.address.country || 'Почтовый адрес';
    if (saved.id === defaultId) {
      const badge = document.createElement('span'); badge.className = 'default-address-badge'; badge.textContent = 'Основной'; heading.append(' ', badge);
    }
    const value = document.createElement('p'); value.textContent = formatAddress(saved.address);
    const actions = document.createElement('div'); actions.className = 'address-card-actions';
    if (saved.id !== defaultId) {
      const makeDefault = document.createElement('button'); makeDefault.type = 'button'; makeDefault.textContent = 'Сделать основным';
      makeDefault.addEventListener('click', () => { StickerStore.setDefaultAddress(saved.id); renderAddresses(); });
      actions.append(makeDefault);
    }
    const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Удалить адрес';
    remove.addEventListener('click', () => {
      pendingAddressId = saved.id;
      byId('delete-address-copy').textContent = `Адрес «${heading.textContent}» будет удалён из личного кабинета.`;
      byId('delete-address-dialog').showModal();
    });
    actions.append(remove); card.append(heading, value, actions); list.append(card);
  }
}

function setFavoritesMessage(text = '', tone = '') {
  const message = byId('favorites-message');
  message.textContent = text;
  message.dataset.tone = tone;
}

function favoriteCatalogUrl(entry) {
  const params = new URLSearchParams();
  if (entry.sections?.[0]) params.set('section', entry.sections[0]);
  if (entry.character_id) params.set('character', entry.character_id);
  params.set('sticker', entry.image_id);
  return `catalog.html?${params}`;
}

function loadImageAspect(entry) {
  if (aspectCache.has(entry.image_id)) return Promise.resolve(aspectCache.get(entry.image_id));
  return new Promise(resolve => {
    const image = new Image();
    image.onload = () => {
      const aspect = image.naturalWidth && image.naturalHeight ? image.naturalWidth / image.naturalHeight : 1;
      aspectCache.set(entry.image_id, aspect); resolve(aspect);
    };
    image.onerror = () => resolve(1);
    image.src = entry.src;
  });
}

function saveFavoriteOrder(items, current) {
  const packed = pack(items);
  if (!packed.ok) return false;
  StickerStore.replaceCurrentOrder({ ...current, items, sheetCount:packed.pages.length });
  renderCurrentOrder();
  return true;
}

async function addFavoriteToOrder(imageId) {
  if (favoritesBusy) return;
  if (!favoriteSize) return setFavoritesMessage('Сначала выбери размер наклейки.', 'error');
  const entry = catalogById.get(imageId);
  if (!entry) return setFavoritesMessage('Эта наклейка сейчас недоступна в каталоге.', 'error');
  favoritesBusy = true;
  try {
    const current = StickerStore.currentOrder();
    const nextId = current.items.reduce((largest, item) => Math.max(largest, item.id || 0), 0) + 1;
    const aspect = await loadImageAspect(entry);
    const result = fitAddition(current.items, { imageId, size:favoriteSize, aspect }, 1, nextId);
    if (!result.added.length) return setFavoritesMessage(`Наклейка не помещается в предел заказа: ${config.maxSheets} листов или ${config.maxItems} наклеек. Оформи или сохрани текущий заказ.`, 'error');
    saveFavoriteOrder([...current.items, ...result.added], current);
    setFavoritesMessage(`«${entry.display_name}» добавлена в заказ, размер ${favoriteSize}. Теперь можно перейти к листу-макету.`, 'success');
  } finally {
    favoritesBusy = false;
  }
}

async function addAllFavoritesToOrder() {
  if (favoritesBusy) return;
  const favorites = StickerStore.favorites().filter(item => catalogById.has(item.imageId));
  if (!favorites.length) return;
  if (!favoriteSize) return setFavoritesMessage('Сначала выбери общий размер для добавления.', 'error');
  favoritesBusy = true;
  byId('add-all-favorites').disabled = true;
  try {
    const current = StickerStore.currentOrder();
    let working = [...current.items];
    let nextId = working.reduce((largest, item) => Math.max(largest, item.id || 0), 0) + 1;
    let added = 0;
    for (const favorite of favorites) {
      const entry = catalogById.get(favorite.imageId);
      const aspect = await loadImageAspect(entry);
      const result = fitAddition(working, { imageId:favorite.imageId, size:favoriteSize, aspect }, 1, nextId);
      if (!result.added.length) continue;
      working.push(...result.added); nextId += result.added.length; added += result.added.length;
    }
    if (added) saveFavoriteOrder(working, current);
    setFavoritesMessage(added === favorites.length
      ? `Все избранные наклейки добавлены в заказ, размер ${favoriteSize}. Теперь можно перейти к листу-макету и при необходимости изменить размеры.`
      : `Добавлено ${added} из ${favorites.length}. Достигнут предел заказа: ${config.maxSheets} листов или ${config.maxItems} наклеек.`, added ? 'success' : 'error');
  } finally {
    favoritesBusy = false;
    byId('add-all-favorites').disabled = StickerStore.favorites().length === 0;
  }
}

function renderFavorites() {
  const favorites = StickerStore.favorites();
  byId('menu-favorites-count').textContent = String(favorites.length);
  byId('favorites-empty').hidden = favorites.length > 0;
  byId('add-all-favorites').disabled = favorites.length === 0 || favoritesBusy;
  const list = byId('favorites-list');
  list.replaceChildren();
  for (const favorite of favorites) {
    const entry = catalogById.get(favorite.imageId);
    if (!entry) continue;
    const card = document.createElement('article'); card.className = 'favorite-card';
    const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'favorite-remove'; remove.textContent = '♥';
    remove.title = 'Убрать из избранного'; remove.setAttribute('aria-label', `Убрать наклейку «${entry.display_name}» из избранного`);
    remove.onclick = () => { StickerStore.removeFavorite(entry.image_id); renderFavorites(); setFavoritesMessage(`«${entry.display_name}» удалена из избранного.`, 'success'); };
    const preview = document.createElement('a'); preview.className = 'favorite-preview'; preview.href = favoriteCatalogUrl(entry);
    preview.setAttribute('aria-label', `Рассмотреть наклейку «${entry.display_name}» в каталоге`);
    const image = document.createElement('img'); image.src = entry.src; image.alt = entry.display_name; image.loading = 'lazy'; preview.append(image);
    const title = document.createElement('h3'); title.textContent = entry.display_name;
    const meta = document.createElement('p'); meta.className = 'favorite-meta';
    const section = entry.sections?.[0] || 'БЕЗ РАЗДЕЛА';
    const sectionLink = document.createElement('a'); sectionLink.href = `catalog.html?section=${encodeURIComponent(section)}`; sectionLink.textContent = section;
    meta.append(sectionLink);
    if (entry.character_name) {
      meta.append(' · ');
      const characterLink = document.createElement('a'); characterLink.href = `catalog.html?section=${encodeURIComponent(section)}&character=${encodeURIComponent(entry.character_id || '')}`; characterLink.textContent = entry.character_name; meta.append(characterLink);
    }
    const actions = document.createElement('div'); actions.className = 'favorite-actions';
    const open = document.createElement('a'); open.href = favoriteCatalogUrl(entry); open.textContent = 'Рассмотреть'; open.className = 'plain-button';
    const add = document.createElement('button'); add.type = 'button'; add.textContent = 'Добавить 1'; add.className = 'primary-button'; add.onclick = () => addFavoriteToOrder(entry.image_id);
    actions.append(open, add); card.append(preview, remove, title, meta, actions); list.append(card);
  }
}

function renderCabinet() {
  renderCurrentOrder();
  renderCartOrders();
  renderAddresses();
  renderFavorites();
}

async function initCabinet() {
  if (!signedIn) return;
  const initial = (account.name || 'Я').trim().charAt(0).toLocaleUpperCase('ru-RU') || 'Я';
  byId('cabinet-avatar').textContent = initial;
  byId('cabinet-title').textContent = account.name;
  byId('cabinet-email').textContent = account.email;
  try {
    const response = await fetch('catalog-data/site_catalog.json');
    if (!response.ok) throw new Error('catalog unavailable');
    const catalog = await response.json();
    catalogById = new Map(catalog.entries.map(entry => [entry.image_id, entry]));
  } catch (error) {
    console.error(error);
  }
  renderCabinet();
}

byId('save-order-to-cart').addEventListener('click', () => {
  const current = StickerStore.currentOrder();
  if (!current.items.length) return;
  const saved = StickerStore.putCartOrder(current, current.cartOrder);
  if (!saved) {
    setCartOrdersMessage(`Корзина заполнена: в ней уже ${StickerStore.limits.cartOrders} заказов. Удалите ненужный заказ, чтобы сохранить новый.`, 'error');
    window.location.hash = 'cart-orders';
    return;
  }
  StickerStore.clearCurrentOrder();
  setCartOrdersMessage(`${saved.name} сохранён в корзине.`, 'success');
  renderCabinet();
});
for (const size of Object.keys(config.sizes)) {
  const button = document.createElement('button');
  button.type = 'button'; button.textContent = size; button.dataset.size = size; button.setAttribute('aria-pressed', 'false');
  button.setAttribute('aria-label', `Выбрать размер ${size} для добавления избранных наклеек`);
  button.addEventListener('click', () => {
    favoriteSize = size;
    for (const candidate of byId('favorite-sizes').children) candidate.setAttribute('aria-pressed', String(candidate === button));
    setFavoritesMessage();
  });
  byId('favorite-sizes').append(button);
}
byId('add-all-favorites').addEventListener('click', addAllFavoritesToOrder);
byId('open-address-form').addEventListener('click', () => {
  byId('cabinet-address-form').hidden = false;
  byId('open-address-form').hidden = true;
  byId('cabinet-recipient').focus();
});
byId('cancel-address-form').addEventListener('click', closeCabinetAddressForm);
byId('cabinet-address-form').addEventListener('submit', event => {
  event.preventDefault();
  if (!event.currentTarget.checkValidity()) {
    event.currentTarget.reportValidity();
    return;
  }
  StickerStore.saveAddress(readCabinetAddress());
  closeCabinetAddressForm();
  renderAddresses();
});
byId('cart-name-form').addEventListener('submit', event => {
  event.preventDefault();
  const name = byId('cart-name').value.trim();
  if (!name) return;
  StickerStore.renameCartOrder(pendingCartId, name);
  byId('cart-name-dialog').close();
  renderCartOrders();
});
byId('confirm-delete-cart').addEventListener('click', () => {
  StickerStore.removeCartOrder(pendingCartId);
  pendingCartId = null;
  byId('delete-cart-dialog').close();
  renderCartOrders();
});
byId('confirm-delete-address').addEventListener('click', () => {
  StickerStore.removeAddress(pendingAddressId);
  byId('delete-address-dialog').close();
  renderAddresses();
});
byId('account-order-switch-cancel').addEventListener('click', closeAccountOrderSwitchDialog);
byId('account-order-switch-save').addEventListener('click', () => {
  const targetId = pendingCartOpenId, mode = pendingCartOpenMode;
  if (!targetId || !mode) return closeAccountOrderSwitchDialog();
  const current = StickerStore.currentOrder();
  const saved = StickerStore.putCartOrder(current, mode === 'new-order' ? null : current.cartOrder);
  if (!saved) {
    closeAccountOrderSwitchDialog();
    setCartOrdersMessage(`Корзина заполнена: в ней уже ${StickerStore.limits.cartOrders} заказов. Удалите ненужный заказ, затем повторите действие. Текущий заказ сохранён на листе-макете.`, 'error');
    window.location.hash = 'cart-orders';
    return;
  }
  closeAccountOrderSwitchDialog();
  openCartOrderNow(targetId);
});
byId('account-order-switch-discard').addEventListener('click', () => {
  const targetId = pendingCartOpenId;
  if (!targetId) return closeAccountOrderSwitchDialog();
  closeAccountOrderSwitchDialog();
  openCartOrderNow(targetId);
});
for (const button of document.querySelectorAll('[data-close-dialog]')) {
  button.addEventListener('click', () => button.closest('dialog').close());
}
byId('cabinet-logout').addEventListener('click', () => {
  localStorage.removeItem(StickerStore.keys.session);
  window.location.href = 'index.html';
});

initCabinet();
