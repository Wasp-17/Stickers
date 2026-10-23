(function (root) {
  const keys = {
    account: 'stickers-local-account-v1',
    session: 'stickers-local-session-v1',
    order: 'stickers-current-order-v1',
    cartOrders: 'stickers-cart-orders-v1',
    cartSequence: 'stickers-cart-sequence-v1',
    addresses: 'stickers-saved-addresses-v1',
    defaultAddress: 'stickers-default-address-v1',
    favorites: 'stickers-favorites-v1',
    catalogStats: 'stickers-catalog-stats-v1',
    catalogStatEvents: 'stickers-catalog-stat-events-v1',
    paidStatOrders: 'stickers-paid-stat-orders-v1',
    sizeScale: 'stickers-size-scale-v2',
  };
  const limits = { cartOrders: 30 };
  try { localStorage.removeItem('stickers-order-drafts-v1'); } catch {}

  function read(key, fallback = null) {
    try {
      const value = localStorage.getItem(key);
      return value === null ? fallback : JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  function write(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  }

  function migrateSizeScale() {
    try {
      if (localStorage.getItem(keys.sizeScale) === 'A30-B50-C75-D100-E125-Fsheet') return;
      const migrateItems = items => Array.isArray(items)
        ? items.map(item => item?.size === 'E' ? { ...item, size:'F' } : item)
        : items;
      const order = read(keys.order);
      if (order?.items) write(keys.order, { ...order, items:migrateItems(order.items) });
      const orders = read(keys.cartOrders);
      if (Array.isArray(orders)) write(keys.cartOrders, orders.map(order => ({ ...order, items:migrateItems(order.items) })));
      localStorage.setItem(keys.sizeScale, 'A30-B50-C75-D100-E125-Fsheet');
    } catch {}
  }

  migrateSizeScale();

  function account() {
    return read(keys.account);
  }

  function signedIn() {
    return Boolean(account() && localStorage.getItem(keys.session) === 'active');
  }

  function currentOrder() {
    const saved = read(keys.order, {});
    return {
      items: Array.isArray(saved.items) ? saved.items : [],
      address: saved.address && typeof saved.address === 'object' ? saved.address : (saved.address || ''),
      sheetCount: Number.isSafeInteger(saved.sheetCount) ? saved.sheetCount : 0,
      updatedAt: saved.updatedAt || null,
      cartOrder: saved.cartOrder && typeof saved.cartOrder === 'object' ? saved.cartOrder : null,
    };
  }

  function saveCurrentOrder(items, address = '', sheetCount = 0, cartOrder = null) {
    const safeItems = items.map(({ id, imageId, size, aspect, mirrorHorizontal, grayscale, sepia, brightnessLevel, saturationLevel }) => ({
      id, imageId, size, aspect,
      ...(mirrorHorizontal ? { mirrorHorizontal:true } : {}),
      ...(grayscale ? { grayscale:true } : {}),
      ...(sepia ? { sepia:true } : {}),
      ...(brightnessLevel ? { brightnessLevel } : {}),
      ...(saturationLevel ? { saturationLevel } : {}),
    }));
    return write(keys.order, { items: safeItems, address, sheetCount, cartOrder, updatedAt: new Date().toISOString() });
  }

  function cartOrders() {
    const saved = read(keys.cartOrders, []);
    if (!Array.isArray(saved)) return [];
    let migrated = false;
    const normalized = saved.map(order => {
      const { createdAt, updatedAt, ...current } = order;
      const changedAt = order.changedAt || updatedAt || createdAt || new Date().toISOString();
      if (!order.changedAt || createdAt || updatedAt) migrated = true;
      return { ...current, changedAt };
    });
    if (migrated) write(keys.cartOrders, normalized);
    return normalized;
  }

  function saveCartOrders(value) {
    return write(keys.cartOrders, value);
  }

  function nextCartNumber() {
    const largestSaved = cartOrders().reduce((largest, order) => Math.max(largest, Number(order.number) || 0), 0);
    const next = Math.max(largestSaved, Number(read(keys.cartSequence, 0)) || 0) + 1;
    write(keys.cartSequence, next);
    return next;
  }

  function copyOrderItems(items) {
    return (items || []).map(({ id, imageId, size, aspect, mirrorHorizontal, grayscale, sepia, brightnessLevel, saturationLevel }) => ({
      id, imageId, size, aspect,
      ...(mirrorHorizontal ? { mirrorHorizontal:true } : {}),
      ...(grayscale ? { grayscale:true } : {}),
      ...(sepia ? { sepia:true } : {}),
      ...(brightnessLevel ? { brightnessLevel } : {}),
      ...(saturationLevel ? { saturationLevel } : {}),
    }));
  }

  function putCartOrder(order, metadata = null) {
    const orders = cartOrders();
    const replacesExisting = Boolean(metadata?.id && orders.some(item => item.id === metadata.id));
    if (!replacesExisting && orders.length >= limits.cartOrders) return null;
    const now = new Date().toISOString();
    const number = metadata?.number || nextCartNumber();
    const saved = {
      id: metadata?.id || `cart-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      number,
      name: String(metadata?.name || '').trim() || `Заказ №${number}`,
      items: copyOrderItems(order.items),
      address: order.address || '',
      sheetCount: order.sheetCount || 0,
      changedAt: now,
    };
    const next = [saved, ...orders.filter(item => item.id !== saved.id)];
    saveCartOrders(next);
    return saved;
  }

  function takeCartOrder(id) {
    const order = cartOrders().find(item => item.id === id) || null;
    if (order) saveCartOrders(cartOrders().filter(item => item.id !== id));
    return order;
  }

  function getCartOrder(id) {
    return cartOrders().find(item => item.id === id) || null;
  }

  function removeCartOrder(id) {
    const existing = getCartOrder(id);
    if (existing) saveCartOrders(cartOrders().filter(order => order.id !== id));
    return existing;
  }

  function renameCartOrder(id, name) {
    const orders = cartOrders();
    const existing = orders.find(order => order.id === id);
    if (!existing) return null;
    const renamed = { ...existing, name: String(name || '').trim() || existing.name, changedAt: new Date().toISOString() };
    saveCartOrders([renamed, ...orders.filter(order => order.id !== id)]);
    return renamed;
  }

  function replaceCurrentOrder(order) {
    return write(keys.order, {
      items: order.items || [], address: order.address || '', sheetCount: order.sheetCount || 0,
      cartOrder: order.cartOrder || null,
      updatedAt: new Date().toISOString(),
    });
  }

  function clearCurrentOrder() {
    return replaceCurrentOrder({ items: [], address: '', sheetCount: 0 });
  }

  function addresses() {
    const saved = read(keys.addresses, []);
    return Array.isArray(saved) ? saved : [];
  }

  function saveAddress(address) {
    const comparable = JSON.stringify(address);
    const existing = addresses().find(item => JSON.stringify(item.address) === comparable);
    if (existing) return existing;
    const saved = {
      id: `address-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      address: { ...address }, createdAt: new Date().toISOString(),
    };
    saveAddresses([saved, ...addresses()]);
    if (!defaultAddressId()) setDefaultAddress(saved.id);
    return saved;
  }

  function saveAddresses(value) {
    return write(keys.addresses, value);
  }

  function removeAddress(id) {
    const wasDefault = defaultAddressId() === id;
    saveAddresses(addresses().filter(item => item.id !== id));
    if (wasDefault) {
      const next = addresses()[0];
      if (next) setDefaultAddress(next.id);
      else localStorage.removeItem(keys.defaultAddress);
    }
  }

  function defaultAddressId() {
    const id = read(keys.defaultAddress, '');
    return typeof id === 'string' && addresses().some(item => item.id === id) ? id : '';
  }

  function defaultAddress() {
    const id = defaultAddressId();
    return id ? addresses().find(item => item.id === id) || null : null;
  }

  function setDefaultAddress(id) {
    if (!addresses().some(item => item.id === id)) return false;
    return write(keys.defaultAddress, id);
  }

  function favorites() {
    if (!signedIn()) return [];
    const saved = read(keys.favorites, []);
    if (!Array.isArray(saved)) return [];
    const seen = new Set();
    return saved.filter(item => {
      const imageId = typeof item === 'string' ? item : item?.imageId;
      if (!imageId || seen.has(imageId)) return false;
      seen.add(imageId);
      return true;
    }).map(item => typeof item === 'string'
      ? { imageId:item, addedAt:new Date(0).toISOString() }
      : { imageId:item.imageId, addedAt:item.addedAt || new Date(0).toISOString() })
      .sort((first, second) => String(second.addedAt).localeCompare(String(first.addedAt)));
  }

  function catalogStats() {
    const saved = read(keys.catalogStats, {});
    return saved && typeof saved === 'object' && !Array.isArray(saved) ? saved : {};
  }

  function catalogStatEvents() {
    const saved = read(keys.catalogStatEvents, []);
    return Array.isArray(saved) ? saved : [];
  }

  function recordCatalogEvent(imageId, type, amount = 1, metadata = {}) {
    if (!imageId || !['favorite_add','favorite_remove','paid_order'].includes(type)) return null;
    const safeAmount = Math.max(1, Number(amount) || 1);
    const stats = catalogStats();
    const current = { paidOrders:0, paidUnits:0, favoriteAdds:0, ...(stats[imageId] || {}) };
    if (type === 'favorite_add') current.favoriteAdds += 1;
    if (type === 'favorite_remove') current.favoriteAdds = Math.max(0, current.favoriteAdds - 1);
    if (type === 'paid_order') {
      current.paidOrders += 1;
      current.paidUnits += safeAmount;
    }
    current.updatedAt = new Date().toISOString();
    stats[imageId] = current;
    write(keys.catalogStats, stats);
    const event = {
      id:`stat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      imageId, type, amount:safeAmount, occurredAt:current.updatedAt, ...metadata,
    };
    write(keys.catalogStatEvents, [...catalogStatEvents(), event].slice(-2000));
    return event;
  }

  function recordPaidOrder(orderId, items) {
    if (!orderId || !Array.isArray(items)) return false;
    const processed = read(keys.paidStatOrders, []);
    if (Array.isArray(processed) && processed.includes(orderId)) return false;
    const quantities = new Map();
    for (const item of items) {
      if (!item?.imageId) continue;
      quantities.set(item.imageId, (quantities.get(item.imageId) || 0) + Math.max(1, Number(item.quantity) || 1));
    }
    for (const [imageId, amount] of quantities) recordCatalogEvent(imageId, 'paid_order', amount, { orderId });
    write(keys.paidStatOrders, [...(Array.isArray(processed) ? processed : []), orderId].slice(-5000));
    return true;
  }

  function addFavorite(imageId) {
    if (!signedIn() || !imageId) return null;
    const existing = favorites();
    const found = existing.find(item => item.imageId === imageId);
    if (found) return found;
    const saved = { imageId, addedAt:new Date().toISOString() };
    write(keys.favorites, [saved, ...existing]);
    recordCatalogEvent(imageId, 'favorite_add');
    return saved;
  }

  function removeFavorite(imageId) {
    if (!signedIn()) return false;
    const existing = favorites();
    const next = existing.filter(item => item.imageId !== imageId);
    if (next.length === existing.length) return false;
    write(keys.favorites, next);
    recordCatalogEvent(imageId, 'favorite_remove');
    return true;
  }

  function isFavorite(imageId) {
    return favorites().some(item => item.imageId === imageId);
  }

  function toggleFavorite(imageId) {
    if (!signedIn()) return null;
    if (isFavorite(imageId)) {
      removeFavorite(imageId);
      return { favorite:false };
    }
    return { favorite:true, entry:addFavorite(imageId) };
  }

  root.StickerStore = {
    keys, limits, read, write, account, signedIn, currentOrder, saveCurrentOrder,
    cartOrders, saveCartOrders, putCartOrder, takeCartOrder, getCartOrder, removeCartOrder, renameCartOrder,
    replaceCurrentOrder, clearCurrentOrder,
    addresses, saveAddress, saveAddresses, removeAddress, defaultAddressId, defaultAddress, setDefaultAddress,
    favorites, addFavorite, removeFavorite, isFavorite, toggleFavorite,
    catalogStats, catalogStatEvents, recordCatalogEvent, recordPaidOrder,
  };
})(globalThis);
