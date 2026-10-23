const assert = require('node:assert/strict');

const memory = new Map();
global.localStorage = {
  getItem: key => memory.has(key) ? memory.get(key) : null,
  setItem: (key, value) => memory.set(key, String(value)),
  removeItem: key => memory.delete(key),
};
memory.set('stickers-order-drafts-v1', JSON.stringify([{ id:'old-draft' }]));
memory.set('stickers-current-order-v1', JSON.stringify({ items:[{ id:90, imageId:'RK17-0090', size:'E', aspect:1 }] }));
memory.set('stickers-cart-orders-v1', JSON.stringify([{ id:'old-e-order', number:9, name:'Старый E', items:[{ id:91, imageId:'RK17-0091', size:'E', aspect:1 }], changedAt:'2026-10-01T00:00:00.000Z' }]));

require('./local-store.js');
assert.equal(localStorage.getItem('stickers-order-drafts-v1'), null);
assert.equal(StickerStore.currentOrder().items[0].size, 'F');
assert.equal(StickerStore.cartOrders()[0].items[0].size, 'F');
StickerStore.saveCartOrders([]);
StickerStore.replaceCurrentOrder({ items:[{ id:92, imageId:'RK17-0092', size:'E', aspect:1 }] });
assert.equal(StickerStore.currentOrder().items[0].size, 'E');

const sample = {
  items: [{ id: 1, imageId: 'RK17-0001', size: 'B', aspect: 1.25, mirrorHorizontal:true, sepia:true, brightnessLevel:1 }],
  address: 'Тестовый адрес', sheetCount: 1,
};

StickerStore.replaceCurrentOrder(sample);
assert.deepEqual(StickerStore.currentOrder().items, sample.items);

const cartOrder = StickerStore.putCartOrder(StickerStore.currentOrder());
assert.equal(cartOrder.number, 1);
assert.equal(cartOrder.name, 'Заказ №1');
assert.ok(cartOrder.changedAt);
assert.equal(Object.hasOwn(cartOrder, 'createdAt'), false);
assert.equal(Object.hasOwn(cartOrder, 'updatedAt'), false);
assert.equal(cartOrder.items[0].mirrorHorizontal, true);
assert.equal(cartOrder.items[0].sepia, true);
assert.equal(StickerStore.cartOrders().length, 1);
StickerStore.renameCartOrder(cartOrder.id, 'Пять листов котов');
assert.equal(StickerStore.cartOrders()[0].name, 'Пять листов котов');
assert.ok(StickerStore.cartOrders()[0].changedAt);
const openedCartOrder = StickerStore.getCartOrder(cartOrder.id);
assert.equal(openedCartOrder.items.length, 1);
assert.equal(StickerStore.cartOrders().length, 1);
StickerStore.putCartOrder(openedCartOrder, openedCartOrder);
assert.equal(StickerStore.cartOrders()[0].number, 1);
StickerStore.putCartOrder({ ...openedCartOrder, items:[...openedCartOrder.items, { id:2, imageId:'RK17-0002', size:'A', aspect:1 }] }, openedCartOrder);
assert.equal(StickerStore.cartOrders().length, 1);
assert.equal(StickerStore.cartOrders()[0].items.length, 2);
assert.equal(StickerStore.removeCartOrder(cartOrder.id).id, cartOrder.id);
assert.equal(StickerStore.cartOrders().length, 0);
StickerStore.saveCartOrders([]);

localStorage.setItem(StickerStore.keys.cartOrders, JSON.stringify([{
  id:'legacy-cart', number:7, name:'Старый заказ', items:[], sheetCount:1,
  createdAt:'2026-10-01T10:00:00.000Z', updatedAt:'2026-10-02T10:00:00.000Z',
}]));
const migratedCart = StickerStore.cartOrders()[0];
assert.equal(migratedCart.changedAt, '2026-10-02T10:00:00.000Z');
assert.equal(Object.hasOwn(migratedCart, 'createdAt'), false);
assert.equal(Object.hasOwn(migratedCart, 'updatedAt'), false);
assert.equal(localStorage.getItem(StickerStore.keys.cartOrders).includes('createdAt'), false);
StickerStore.saveCartOrders([]);

StickerStore.clearCurrentOrder();
assert.equal(StickerStore.currentOrder().items.length, 0);

StickerStore.replaceCurrentOrder(sample);
assert.equal(StickerStore.currentOrder().items.length, 1);

const address = { recipient: 'Тест', country: 'Украина', postalCode: '01001', city: 'Киев', street: 'Крещатик', house: '1' };
const savedAddress = StickerStore.saveAddress(address);
StickerStore.saveAddress(address);
assert.equal(StickerStore.addresses().length, 1);
assert.equal(StickerStore.defaultAddressId(), savedAddress.id);
assert.deepEqual(StickerStore.defaultAddress().address, address);
const secondAddress = StickerStore.saveAddress({ ...address, street:'Владимирская' });
assert.equal(StickerStore.setDefaultAddress(secondAddress.id), true);
assert.equal(StickerStore.defaultAddressId(), secondAddress.id);
StickerStore.removeAddress(secondAddress.id);
assert.equal(StickerStore.defaultAddressId(), savedAddress.id);
StickerStore.removeAddress(savedAddress.id);
assert.equal(StickerStore.addresses().length, 0);
assert.equal(StickerStore.defaultAddress(), null);

assert.equal(StickerStore.addFavorite('RK17-0001'), null);
localStorage.setItem(StickerStore.keys.account, JSON.stringify({ name:'Тест' }));
localStorage.setItem(StickerStore.keys.session, 'active');
StickerStore.addFavorite('RK17-0001');
StickerStore.addFavorite('RK17-0001');
StickerStore.addFavorite('RK17-0002');
assert.deepEqual(StickerStore.favorites().map(item => item.imageId), ['RK17-0002', 'RK17-0001']);
assert.equal(StickerStore.catalogStats()['RK17-0001'].favoriteAdds, 1);
assert.equal(StickerStore.isFavorite('RK17-0001'), true);
assert.deepEqual(StickerStore.toggleFavorite('RK17-0001'), { favorite:false });
assert.equal(StickerStore.isFavorite('RK17-0001'), false);
assert.equal(StickerStore.catalogStats()['RK17-0001'].favoriteAdds, 0);
assert.equal(StickerStore.recordPaidOrder('paid-1', [{ imageId:'RK17-0002', quantity:3 }, { imageId:'RK17-0002', quantity:2 }]), true);
assert.equal(StickerStore.recordPaidOrder('paid-1', [{ imageId:'RK17-0002', quantity:99 }]), false);
assert.equal(StickerStore.catalogStats()['RK17-0002'].paidOrders, 1);
assert.equal(StickerStore.catalogStats()['RK17-0002'].paidUnits, 5);
assert.ok(StickerStore.catalogStatEvents().some(event => event.type === 'paid_order'));

assert.equal(StickerStore.limits.cartOrders, 30);
const fullCart = Array.from({ length:StickerStore.limits.cartOrders }, (_, index) => ({
  id:`limit-${index + 1}`, number:index + 1, name:`Заказ №${index + 1}`,
  items:[{ id:index + 1, imageId:'RK17-0001', size:'A', aspect:1 }], sheetCount:1,
  changedAt:'2026-10-18T00:00:00.000Z',
}));
StickerStore.saveCartOrders(fullCart);
const fullCartBefore = JSON.stringify(StickerStore.cartOrders());
assert.equal(StickerStore.putCartOrder(sample), null);
assert.equal(JSON.stringify(StickerStore.cartOrders()), fullCartBefore);
const updatedAtLimit = StickerStore.putCartOrder({ ...fullCart[29], sheetCount:2 }, fullCart[29]);
assert.equal(updatedAtLimit.id, fullCart[29].id);
assert.equal(updatedAtLimit.sheetCount, 2);
assert.equal(StickerStore.cartOrders().length, StickerStore.limits.cartOrders);
StickerStore.saveCartOrders([]);

console.log('PASS: current order, 30-order cart limit, cart editing, retired drafts, addresses and favorites');
