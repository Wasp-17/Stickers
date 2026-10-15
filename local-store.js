(function (root) {
  const keys = {
    account: 'stickers-local-account-v1',
    session: 'stickers-local-session-v1',
    order: 'stickers-current-order-v1',
    cartOrders: 'stickers-cart-orders-v1',
    cartSequence: 'stickers-cart-sequence-v1',
    drafts: 'stickers-order-drafts-v1',
    addresses: 'stickers-saved-addresses-v1',
  };

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
    return Array.isArray(saved) ? saved : [];
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

  function putCartOrder(order, metadata = null) {
    const now = new Date().toISOString();
    const number = metadata?.number || nextCartNumber();
    const saved = {
      id: metadata?.id || `cart-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      number,
      name: String(metadata?.name || '').trim() || `Заказ №${number}`,
      items: (order.items || []).map(({ id, imageId, size, aspect }) => ({ id, imageId, size, aspect })),
      address: order.address || '',
      sheetCount: order.sheetCount || 0,
      createdAt: metadata?.createdAt || now,
      updatedAt: now,
    };
    const next = [saved, ...cartOrders().filter(item => item.id !== saved.id)];
    saveCartOrders(next);
    return saved;
  }

  function takeCartOrder(id) {
    const order = cartOrders().find(item => item.id === id) || null;
    if (order) saveCartOrders(cartOrders().filter(item => item.id !== id));
    return order;
  }

  function renameCartOrder(id, name) {
    const next = cartOrders().map(order => order.id === id
      ? { ...order, name: String(name || '').trim() || order.name, updatedAt: new Date().toISOString() }
      : order);
    saveCartOrders(next);
  }

  function drafts() {
    const saved = read(keys.drafts, []);
    return Array.isArray(saved) ? saved : [];
  }

  function saveDrafts(value) {
    return write(keys.drafts, value);
  }

  function createDraft(order, name) {
    const draft = {
      id: `draft-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: String(name || '').trim() || 'Черновик заказа',
      items: order.items.map(({ id, imageId, size, aspect }) => ({ id, imageId, size, aspect })),
      address: order.address || '',
      sheetCount: order.sheetCount || 0,
      updatedAt: new Date().toISOString(),
    };
    const next = [draft, ...drafts()];
    saveDrafts(next);
    return draft;
  }

  function renameDraft(id, name) {
    const next = drafts().map(draft => draft.id === id
      ? { ...draft, name: String(name || '').trim() || draft.name, updatedAt: new Date().toISOString() }
      : draft);
    saveDrafts(next);
  }

  function removeDraft(id) {
    saveDrafts(drafts().filter(draft => draft.id !== id));
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
    return saved;
  }

  function saveAddresses(value) {
    return write(keys.addresses, value);
  }

  function removeAddress(id) {
    saveAddresses(addresses().filter(item => item.id !== id));
  }

  root.StickerStore = {
    keys, read, write, account, signedIn, currentOrder, saveCurrentOrder,
    cartOrders, saveCartOrders, putCartOrder, takeCartOrder, renameCartOrder,
    drafts, saveDrafts, createDraft, renameDraft, removeDraft, replaceCurrentOrder, clearCurrentOrder,
    addresses, saveAddress, saveAddresses, removeAddress,
  };
})(globalThis);
