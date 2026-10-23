const byId = id => document.getElementById(id);
const sheetPrice = 250;
const addressFields = {
  recipient:'delivery-recipient', phone:'delivery-phone', country:'delivery-country', postalCode:'delivery-postal-code',
  region:'delivery-region', city:'delivery-city', street:'delivery-street', house:'delivery-house', apartment:'delivery-apartment', comment:'delivery-comment',
};
let order = StickerStore.currentOrder();
let items = order.items;
let catalogById = new Map();
let sizeRules = null;
function sizeIssues() {
  if (!sizeRules) return ['Не удалось проверить правила размеров. Обнови страницу.'];
  return [...new Set(items.filter(item => item.size === 'A' && sizeRules[item.imageId]?.a_policy === 'min_a1')
    .map(item => `Для «${catalogById.get(item.imageId)?.display_name || item.imageId}» минимальный размер A1 (35 × 35 мм). Вернись в макет и измени размер.`))];
}
function sizeNotices() {
  if (!sizeRules) return [];
  return [...new Set(items.filter(item => item.size === 'A' && sizeRules[item.imageId]?.a_policy === 'recommend_a1')
    .map(item => `Для «${catalogById.get(item.imageId)?.display_name || item.imageId}» рекомендуем A1 (35 × 35 мм) для точного контура. ${sizeRules[item.imageId].reason}`))];
}
let pages = [];
let pendingDeleteId = null;
let currentStep = 1;

function plural(value, one, few, many) {
  const number = Math.abs(Number(value)) % 100, last = number % 10;
  return number > 10 && number < 20 ? many : last === 1 ? one : last > 1 && last < 5 ? few : many;
}
function stickerFilter(item) {
  const filters = [];
  if (item.grayscale) filters.push('grayscale(1)');
  if (item.sepia) filters.push('sepia(1)');
  if (item.brightnessLevel) filters.push(`brightness(${1 + item.brightnessLevel * .1})`);
  if (item.saturationLevel) filters.push(`saturate(${1 + item.saturationLevel * .25})`);
  return filters.join(' ');
}
function workingName() { return order.cartOrder?.name || 'Новый заказ'; }
function currentAddress() {
  return Object.fromEntries(Object.entries(addressFields).map(([key,id]) => [key, byId(id).value.trim()]));
}
function fillAddress(address = {}) {
  for (const [key,id] of Object.entries(addressFields)) byId(id).value = address?.[key] || '';
}
function saveOrderAddress() {
  order = { ...order, items, address:currentAddress(), sheetCount:pages.length };
  StickerStore.saveCurrentOrder(items, order.address, pages.length, order.cartOrder);
}
function formatAddress(address) {
  return [address.postalCode, address.country, address.region, address.city, address.street, address.house && `д. ${address.house}`, address.apartment && `кв./офис ${address.apartment}`].filter(Boolean).join(', ');
}
function validAddress(report = false) {
  const form = byId('delivery-form');
  if (!form.checkValidity()) {
    if (report) { form.reportValidity(); byId('address-feedback').textContent = 'Заполни обязательные поля адреса.'; }
    return false;
  }
  return true;
}
function setStep(step, historyMode = 'push') {
  if (!items.length) step = 1;
  if (step === 3 && !validAddress(false)) step = 2;
  currentStep = Math.max(1, Math.min(3, step));
  for (let value = 1; value <= 3; value++) {
    byId(`step-${value}`).hidden = value !== currentStep || !items.length;
    const button = document.querySelector(`[data-step-button="${value}"]`);
    button.classList.toggle('is-current', value === currentStep);
    button.classList.toggle('is-complete', value < currentStep);
    button.setAttribute('aria-current', value === currentStep ? 'step' : 'false');
  }
  if (currentStep === 3) renderConfirmation();
  const url = new URL(window.location.href); url.searchParams.set('step', String(currentStep));
  history[historyMode === 'replace' ? 'replaceState' : 'pushState']({ step:currentStep }, '', url);
  window.scrollTo({ top:0, behavior:'smooth' });
}
function position(element, placement) {
  Object.assign(element.style, { left:`${placement.x / StickerLayout.config.sheet.width * 100}%`, top:`${placement.y / StickerLayout.config.sheet.height * 100}%`, width:`${placement.width / StickerLayout.config.sheet.width * 100}%`, height:`${placement.height / StickerLayout.config.sheet.height * 100}%` });
}
function renderSheets() {
  const target = byId('checkout-sheets'); target.replaceChildren();
  const printable = StickerLayout.area();
  pages.forEach((placements,index) => {
    const card = document.createElement('article'); card.className = 'sheet-card';
    const label = document.createElement('span'); label.textContent = `Лист ${index + 1}`;
    const sheet = document.createElement('div'); sheet.className = 'sheet-preview';
    const border = document.createElement('div'); border.className = 'print-area'; position(border,{ x:printable.x,y:printable.y,width:printable.w,height:printable.h }); sheet.append(border);
    for (const placement of placements) {
      const entry = catalogById.get(placement.imageId); if (!entry) continue;
      const button = document.createElement('button'); button.type = 'button'; button.className = 'sheet-sticker'; position(button,placement);
      button.title = `Удалить «${entry.display_name}» из заказа`;
      const image = document.createElement('img'); image.src = entry.src; image.alt = entry.display_name; image.draggable = false;
      image.style.width = `${placement.rotated ? placement.height / placement.width * 100 : 100}%`;
      image.style.height = `${placement.rotated ? placement.width / placement.height * 100 : 100}%`;
      image.style.transform = `translate(-50%,-50%) rotate(${placement.rotated ? 90 : 0}deg) scaleX(${placement.mirrorHorizontal ? -1 : 1})`;
      image.style.filter = stickerFilter(placement); button.append(image);
      button.onclick = () => openDeleteDialog(placement.id,entry.display_name);
      sheet.append(button);
    }
    card.append(label,sheet); target.append(card);
  });
}
function variantKey(item) { return [item.imageId,item.size,Boolean(item.mirrorHorizontal),Boolean(item.grayscale),Boolean(item.sepia),item.brightnessLevel || 0,item.saturationLevel || 0].join('|'); }
function effectLabel(item) {
  const values = [];
  if (item.mirrorHorizontal) values.push('зеркально'); if (item.grayscale) values.push('ч/б'); if (item.sepia) values.push('сепия');
  if (item.brightnessLevel) values.push('светлее'); if (item.saturationLevel) values.push('насыщеннее');
  return values.length ? values.join(', ') : 'без обработки';
}
function renderComposition() {
  const groups = new Map();
  for (const item of items) { const key = variantKey(item); const group = groups.get(key); if (group) group.count++; else groups.set(key,{ item,count:1 }); }
  const target = byId('composition-list'); target.replaceChildren();
  for (const { item,count } of groups.values()) {
    const entry = catalogById.get(item.imageId); if (!entry) continue;
    const row = document.createElement('div'); row.className = 'composition-row';
    const image = document.createElement('img'); image.src = entry.src; image.alt = '';
    const copy = document.createElement('div'); copy.innerHTML = `<strong>${entry.display_name}</strong><small>Размер ${item.size} · ${effectLabel(item)}</small>`;
    const amount = document.createElement('span'); amount.textContent = `${count} шт.`;
    row.append(image,copy,amount); target.append(row);
  }
}
function renderSummary() {
  byId('working-order-name').textContent = `Рабочее название: ${workingName()}`;
  byId('summary-stickers').textContent = items.length;
  byId('summary-sheets').textContent = pages.length;
  byId('summary-price').textContent = `${pages.length * sheetPrice} ₽`;
  renderComposition(); renderSheets();
}
function renderConfirmation() {
  const issues = sizeIssues();
  byId('confirm-order').disabled = issues.length > 0;
  const feedback = byId('payment-feedback');
  feedback.className = 'payment-feedback';
  feedback.textContent = [...issues, ...sizeNotices()].join(' ');
  const address = currentAddress();
  byId('confirmation-recipient').textContent = address.recipient;
  byId('confirmation-address').textContent = formatAddress(address);
  byId('confirmation-phone').textContent = address.phone ? `Телефон: ${address.phone}` : 'Телефон не указан';
  byId('confirmation-stickers').textContent = `${items.length} ${plural(items.length,'наклейка','наклейки','наклеек')}`;
  byId('confirmation-sheets').textContent = `${pages.length} ${plural(pages.length,'лист','листа','листов')}`;
  byId('confirmation-name').textContent = workingName();
  byId('sheet-price-label').textContent = `${pages.length} ${plural(pages.length,'лист','листа','листов')} × ${sheetPrice} ₽`;
  byId('sheet-price').textContent = `${pages.length * sheetPrice} ₽`;
  byId('checkout-total').textContent = `${pages.length * sheetPrice} ₽ без доставки`;
}
function refreshPacking() {
  const result = StickerLayout.pack(items); pages = result.ok ? result.pages : [];
  order = { ...order, items, sheetCount:pages.length };
  StickerStore.saveCurrentOrder(items, order.address || '', pages.length, order.cartOrder);
  byId('empty-order').hidden = items.length > 0;
  byId('step-1').hidden = !items.length || currentStep !== 1;
  if (items.length) renderSummary();
}
function openDeleteDialog(id,name) {
  pendingDeleteId = id; byId('delete-sticker-copy').textContent = `«${name}» будет удалена только из текущего заказа.`; byId('delete-sticker-dialog').showModal();
}
function closeDeleteDialog() { pendingDeleteId = null; byId('delete-sticker-dialog').close(); }
function renderAccountAddressOptions(selected = '') {
  const signedIn = StickerStore.signedIn();
  byId('registration-offer').hidden = signedIn;
  byId('saved-address-field').hidden = !signedIn;
  byId('save-address-field').hidden = !signedIn;
  if (!signedIn) return;
  const select = byId('saved-address');
  select.replaceChildren(new Option('Заполнить новый адрес',''));
  const defaultId = StickerStore.defaultAddressId();
  StickerStore.addresses()
    .sort((first, second) => Number(second.id === defaultId) - Number(first.id === defaultId))
    .forEach(saved => select.add(new Option(`${saved.id === defaultId ? 'Основной — ' : ''}${saved.address.recipient || 'Адрес'} — ${saved.address.city || ''}, ${saved.address.street || ''}`,saved.id)));
  select.value = selected;
}
async function initialize() {
  try {
    const [response, rulesResponse] = await Promise.all([fetch('catalog-data/site_catalog.json'), fetch('catalog-data/cut_size_rules.json')]);
    if (!response.ok || !rulesResponse.ok) throw new Error('catalog');
    const [catalog, rules] = await Promise.all([response.json(), rulesResponse.json()]);
    if (rules.schema_version !== 1 || !rules.rules) throw new Error('size rules');
    catalogById = new Map(catalog.entries.map(entry => [entry.image_id,entry]));
    sizeRules = rules.rules;
  } catch { byId('composition-list').textContent = 'Не удалось загрузить сведения о наклейках.'; }
  const orderAddress = order.address && typeof order.address === 'object' ? order.address : {};
  const hasOrderAddress = Object.values(orderAddress).some(value => String(value || '').trim());
  const defaultSaved = StickerStore.signedIn() && !hasOrderAddress ? StickerStore.defaultAddress() : null;
  fillAddress(defaultSaved?.address || orderAddress);
  renderAccountAddressOptions(defaultSaved?.id || '');
  if (defaultSaved) saveOrderAddress();
  refreshPacking();
  const returnTarget = encodeURIComponent('checkout.html?step=2');
  byId('checkout-register').href = `index.html?account=register&return=${returnTarget}`;
  byId('checkout-login').href = `index.html?account=login&return=${returnTarget}`;
  const requested = Number(new URLSearchParams(location.search).get('step')) || 1;
  setStep(requested,'replace');
}

document.querySelectorAll('[data-step-button]').forEach(button => button.onclick = () => {
  const step = Number(button.dataset.stepButton);
  if (step === 3 && !validAddress(true)) return setStep(2);
  setStep(step);
});
document.querySelectorAll('[data-go-step]').forEach(button => button.onclick = () => setStep(Number(button.dataset.goStep)));
document.querySelectorAll('[data-close-dialog]').forEach(button => button.onclick = closeDeleteDialog);
byId('to-delivery').onclick = () => setStep(2);
byId('delivery-form').addEventListener('input', () => { byId('address-feedback').textContent = ''; saveOrderAddress(); });
byId('delivery-form').onsubmit = event => {
  event.preventDefault(); if (!validAddress(true)) return;
  saveOrderAddress();
  if (StickerStore.signedIn() && byId('save-address').checked) {
    const saved = StickerStore.saveAddress(currentAddress()); renderAccountAddressOptions(saved.id); byId('save-address').checked = false;
  }
  setStep(3);
};
byId('saved-address').onchange = () => {
  const saved = StickerStore.addresses().find(value => value.id === byId('saved-address').value);
  fillAddress(saved?.address || {}); saveOrderAddress();
};
byId('confirm-delete-sticker').onclick = () => {
  if (pendingDeleteId !== null) items = items.filter(item => item.id !== pendingDeleteId);
  closeDeleteDialog(); refreshPacking();
};
byId('confirm-order').onclick = () => {
  if (sizeIssues().length) { renderConfirmation(); return; }
  saveOrderAddress();
  const feedback = byId('payment-feedback'); feedback.className = 'payment-feedback is-success';
  feedback.textContent = 'Данные заказа проверены. Сейчас оплата ещё не подключена, поэтому официальный номер заказа пока не присваивается. После подключения оплаты он появится здесь только после её подтверждения.';
};
window.addEventListener('popstate', event => setStep(Number(event.state?.step) || Number(new URLSearchParams(location.search).get('step')) || 1,'replace'));
initialize();
