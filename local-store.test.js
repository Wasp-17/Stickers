const assert = require('node:assert/strict');

const memory = new Map();
global.localStorage = {
  getItem: key => memory.has(key) ? memory.get(key) : null,
  setItem: (key, value) => memory.set(key, String(value)),
  removeItem: key => memory.delete(key),
};

require('./local-store.js');

const sample = {
  items: [{ id: 1, imageId: 'RK17-0001', size: 'B', aspect: 1.25 }],
  address: 'Тестовый адрес', sheetCount: 1,
};

StickerStore.replaceCurrentOrder(sample);
assert.deepEqual(StickerStore.currentOrder().items, sample.items);

const cartOrder = StickerStore.putCartOrder(StickerStore.currentOrder());
assert.equal(cartOrder.number, 1);
assert.equal(cartOrder.name, 'Заказ №1');
assert.equal(StickerStore.cartOrders().length, 1);
StickerStore.renameCartOrder(cartOrder.id, 'Пять листов котов');
assert.equal(StickerStore.cartOrders()[0].name, 'Пять листов котов');
const openedCartOrder = StickerStore.takeCartOrder(cartOrder.id);
assert.equal(openedCartOrder.items.length, 1);
assert.equal(StickerStore.cartOrders().length, 0);
StickerStore.putCartOrder(openedCartOrder, openedCartOrder);
assert.equal(StickerStore.cartOrders()[0].number, 1);
StickerStore.saveCartOrders([]);

const draft = StickerStore.createDraft(StickerStore.currentOrder(), 'Первый вариант');
assert.equal(StickerStore.drafts().length, 1);
assert.equal(StickerStore.drafts()[0].name, 'Первый вариант');

StickerStore.renameDraft(draft.id, 'Подарок другу');
assert.equal(StickerStore.drafts()[0].name, 'Подарок другу');

StickerStore.clearCurrentOrder();
assert.equal(StickerStore.currentOrder().items.length, 0);

StickerStore.replaceCurrentOrder(StickerStore.drafts()[0]);
StickerStore.removeDraft(draft.id);
assert.equal(StickerStore.currentOrder().items.length, 1);
assert.equal(StickerStore.drafts().length, 0);

const address = { recipient: 'Тест', country: 'Украина', postalCode: '01001', city: 'Киев', street: 'Крещатик', house: '1' };
const savedAddress = StickerStore.saveAddress(address);
StickerStore.saveAddress(address);
assert.equal(StickerStore.addresses().length, 1);
StickerStore.removeAddress(savedAddress.id);
assert.equal(StickerStore.addresses().length, 0);

console.log('PASS: current order, draft flow and saved-address storage');
