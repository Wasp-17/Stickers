const account = StickerStore.account();
const signedIn = StickerStore.signedIn();
const byId = id => document.getElementById(id);
const { config, pack } = StickerLayout;
let catalogById = new Map();
let pendingDraftId = null;
let pendingCartId = null;
let pendingAddressId = null;
let nameDialogMode = 'create';
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

function defaultDraftName() {
  return `Черновик от ${new Intl.DateTimeFormat('ru', { day:'numeric', month:'long', hour:'2-digit', minute:'2-digit' }).format(new Date())}`;
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

function renderCartOrders() {
  const orders = StickerStore.cartOrders();
  byId('menu-cart-count').textContent = String(orders.length);
  byId('cart-orders-empty').hidden = orders.length > 0;
  const list = byId('cart-orders-list');
  list.replaceChildren();
  for (const order of orders) {
    const card = document.createElement('article'); card.className = 'draft-card';
    const preview = document.createElement('div'); preview.className = 'draft-preview';
    preview.setAttribute('aria-label', `Первый лист заказа «${order.name}»`);
    drawDraftPreview(preview, order);
    const info = document.createElement('div'); info.className = 'draft-info';
    const title = document.createElement('h3'); title.textContent = order.name;
    const meta = document.createElement('p'); meta.className = 'draft-meta';
    meta.textContent = `${order.items.length} накл. · ${order.sheetCount || 1} лист. · ${formatDate(order.createdAt)}`;
    const buttons = document.createElement('div'); buttons.className = 'draft-buttons';
    buttons.append(
      draftButton('Открыть', 'continue-draft', activateCartOrder, order.id),
      draftButton('Переименовать', '', openCartRenameDialog, order.id),
    );
    info.append(title, meta, buttons); card.append(preview, info); list.append(card);
  }
}

function activateCartOrder(id) {
  const current = StickerStore.currentOrder();
  if (current.items.length) StickerStore.putCartOrder(current, current.cartOrder);
  const order = StickerStore.takeCartOrder(id);
  if (!order) return renderCartOrders();
  StickerStore.replaceCurrentOrder({
    ...order,
    cartOrder: { id:order.id, number:order.number, name:order.name, createdAt:order.createdAt },
  });
  window.location.href = 'catalog.html';
}

function openCartRenameDialog(id) {
  const order = StickerStore.cartOrders().find(item => item.id === id);
  if (!order) return;
  pendingCartId = id;
  byId('cart-name').value = order.name;
  byId('cart-name-dialog').showModal();
  byId('cart-name').select();
}

function renderDrafts() {
  const drafts = StickerStore.drafts();
  byId('menu-draft-count').textContent = String(drafts.length);
  byId('drafts-empty').hidden = drafts.length > 0;
  const list = byId('drafts-list');
  list.replaceChildren();
  for (const draft of drafts) {
    const card = document.createElement('article'); card.className = 'draft-card';
    const preview = document.createElement('div'); preview.className = 'draft-preview';
    preview.setAttribute('aria-label', `Первый лист черновика «${draft.name}»`);
    drawDraftPreview(preview, draft);
    const info = document.createElement('div'); info.className = 'draft-info';
    const title = document.createElement('h3'); title.textContent = draft.name;
    const meta = document.createElement('p'); meta.className = 'draft-meta';
    meta.textContent = `${draft.items.length} накл. · ${draft.sheetCount || 1} лист. · ${formatDate(draft.updatedAt)}`;
    const buttons = document.createElement('div'); buttons.className = 'draft-buttons';
    buttons.append(
      draftButton('Продолжить', 'continue-draft', requestDraftActivation, draft.id),
      draftButton('Переименовать', '', openRenameDialog, draft.id),
      draftButton('Удалить', '', openDeleteDialog, draft.id),
    );
    info.append(title, meta, buttons); card.append(preview, info); list.append(card);
  }
}

function renderAddresses() {
  const addresses = StickerStore.addresses();
  byId('menu-address-count').textContent = String(addresses.length);
  byId('addresses-empty').hidden = addresses.length > 0;
  const list = byId('addresses-list');
  list.replaceChildren();
  for (const saved of addresses) {
    const card = document.createElement('article'); card.className = 'address-card';
    const heading = document.createElement('h3');
    heading.textContent = saved.address.city || saved.address.country || 'Почтовый адрес';
    const value = document.createElement('p'); value.textContent = formatAddress(saved.address);
    const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Удалить адрес';
    remove.addEventListener('click', () => {
      pendingAddressId = saved.id;
      byId('delete-address-copy').textContent = `Адрес «${heading.textContent}» будет удалён из личного кабинета.`;
      byId('delete-address-dialog').showModal();
    });
    card.append(heading, value, remove); list.append(card);
  }
}

function renderCabinet() {
  renderCurrentOrder();
  renderCartOrders();
  renderDrafts();
  renderAddresses();
}

function openNameDialog(mode, draft = null) {
  nameDialogMode = mode;
  pendingDraftId = draft?.id || null;
  byId('draft-name-title').textContent = mode === 'rename' ? 'Переименовать черновик' : 'Как назвать черновик?';
  byId('draft-name').value = draft?.name || defaultDraftName();
  byId('draft-name-dialog').showModal();
  byId('draft-name').select();
}

function openRenameDialog(id) {
  const draft = StickerStore.drafts().find(item => item.id === id);
  if (draft) openNameDialog('rename', draft);
}

function openDeleteDialog(id) {
  const draft = StickerStore.drafts().find(item => item.id === id);
  if (!draft) return;
  pendingDraftId = id;
  byId('delete-draft-copy').textContent = `Черновик «${draft.name}» будет удалён.`;
  byId('delete-draft-dialog').showModal();
}

function activateDraft(id) {
  const draft = StickerStore.drafts().find(item => item.id === id);
  if (!draft) return;
  StickerStore.replaceCurrentOrder(draft);
  StickerStore.removeDraft(id);
  window.location.href = 'catalog.html';
}

function requestDraftActivation(id) {
  if (!StickerStore.currentOrder().items.length) return activateDraft(id);
  pendingDraftId = id;
  byId('activate-draft-dialog').showModal();
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

byId('park-order').addEventListener('click', () => openNameDialog('create'));
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
byId('draft-name-form').addEventListener('submit', event => {
  event.preventDefault();
  const name = byId('draft-name').value.trim();
  if (!name) return;
  if (nameDialogMode === 'rename') StickerStore.renameDraft(pendingDraftId, name);
  else {
    const order = StickerStore.currentOrder();
    if (order.items.length) {
      StickerStore.createDraft(order, name);
      StickerStore.clearCurrentOrder();
    }
  }
  byId('draft-name-dialog').close();
  renderCabinet();
});
byId('cart-name-form').addEventListener('submit', event => {
  event.preventDefault();
  const name = byId('cart-name').value.trim();
  if (!name) return;
  StickerStore.renameCartOrder(pendingCartId, name);
  byId('cart-name-dialog').close();
  renderCartOrders();
});
byId('park-and-activate').addEventListener('click', () => {
  const current = StickerStore.currentOrder();
  if (current.items.length) StickerStore.createDraft(current, defaultDraftName());
  activateDraft(pendingDraftId);
});
byId('replace-and-activate').addEventListener('click', () => activateDraft(pendingDraftId));
byId('confirm-delete-draft').addEventListener('click', () => {
  StickerStore.removeDraft(pendingDraftId);
  byId('delete-draft-dialog').close();
  renderDrafts();
});
byId('confirm-delete-address').addEventListener('click', () => {
  StickerStore.removeAddress(pendingAddressId);
  byId('delete-address-dialog').close();
  renderAddresses();
});
for (const button of document.querySelectorAll('[data-close-dialog]')) {
  button.addEventListener('click', () => button.closest('dialog').close());
}
byId('cabinet-logout').addEventListener('click', () => {
  localStorage.removeItem(StickerStore.keys.session);
  window.location.href = 'index.html';
});

initCabinet();
