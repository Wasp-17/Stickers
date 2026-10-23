const assert = require('node:assert/strict');
const { config, area, dimensions, pack, validQuantity, fitAddition } = require('./layout');
for (const value of ['', ' ', '0', '-1', '1.5', 'abc', 'Infinity', '9007199254740992']) assert.equal(validQuantity(value), false, value);
for (const value of ['1', '25', '1000']) assert.equal(validQuantity(value), true, value);
function check(items, c = config) {
  const result = pack(items, c); assert.equal(result.ok, true);
  assert.equal(result.pages.flat().length, items.length);
  assert.equal(new Set(result.pages.flat().map(p => p.id)).size, items.length);
  const a = area(c), e = 1e-7;
  for (const page of result.pages) for (const [i, p] of page.entries()) {
    assert(p.x >= a.x - e && p.y >= a.y - e);
    assert(p.x + p.width <= a.x + a.w + e && p.y + p.height <= a.y + a.h + e);
    for (const q of page.slice(i + 1)) assert(p.x + p.width + c.gap <= q.x + e || q.x + q.width + c.gap <= p.x + e || p.y + p.height + c.gap <= q.y + e || q.y + q.height + c.gap <= p.y + e, 'Cutting gap violated');
  }
  return result;
}
const make = (n, size = 'F') => Array.from({ length: n }, (_, id) => ({ id, size, aspect: 1 }));
assert.deepEqual(dimensions('A', 1), { width: 30, height: 30 });
assert.deepEqual(dimensions('A1', 1), { width: 35, height: 35 });
assert.deepEqual(dimensions('B', .5), { width: 25, height: 50 });
assert.deepEqual(dimensions('C', 2), { width: 75, height: 37.5 });
assert.deepEqual(dimensions('D', 1), { width: 100, height: 100 });
assert.deepEqual(dimensions('E', 1), { width: 125, height: 125 });
assert.deepEqual(dimensions('F', 1), { width: 186, height: 186 });
assert.equal(check([]).pages.length, 0);
assert.equal(check(make(9)).pages.length, 9);
assert.equal(check(make(10)).pages.length, 10);
assert.equal(pack(make(11)).reason, 'limit');
const smallSquareLimit = Array.from({ length:config.maxItems }, (_, id) => ({ id, size:'A', aspect:1 }));
const smallSquarePacked = check(smallSquareLimit);
assert.equal(smallSquarePacked.pages.length, 10);
assert(smallSquarePacked.pages.every(page => page.length === 35));
assert.equal(pack([...smallSquareLimit, { id:config.maxItems, size:'A', aspect:10 }]).reason, 'item-limit');
const thinItemLimit = fitAddition([], { size:'A', aspect:10 }, config.maxItems + 50, 0);
assert.equal(thinItemLimit.added.length, config.maxItems);
assert.equal(thinItemLimit.remaining, 50);
assert.equal(thinItemLimit.reason, 'item-limit');
for (let seed = 1; seed <= 30; seed++) check(Array.from({ length: 60 }, (_, id) => ({ id, size: 'ABC'[(id * 7 + seed) % 3], aspect: [0.7, 1, 1.5, 2][(id + seed) % 4] })));
const rotated = check([{ id: 1, size: 'D', aspect: .25 }], { ...config, sheet: { width: 130, height: 65 } });
assert.equal(rotated.pages[0][0].rotated, true);
assert.throws(() => pack([{ id: 1, size: 'Z', aspect: 1 }]), /Invalid sticker size/);
assert.throws(() => pack([{ id: 1, size: 'A', aspect: 0 }]), /Invalid sticker aspect ratio/);
const sticker = { size: 'F', aspect: 1 };
for (const [existingCount, requested, accepted] of [[0, 50, 10], [9, 50, 1], [10, 1, 0], [0, 10, 10], [0, Number.MAX_SAFE_INTEGER, 10], [9, 2, 1]]) {
  const existing = make(existingCount), before = JSON.stringify(existing);
  const result = fitAddition(existing, sticker, requested, existingCount);
  assert.equal(result.added.length, accepted);
  assert.equal(result.remaining, requested - accepted);
  assert.equal(JSON.stringify(existing), before);
  check([...existing, ...result.added]);
}
const mixed = [...make(10, 'A'), ...make(3, 'D').map(p => ({ ...p, id: p.id + 10 }))];
const partial = fitAddition(mixed, sticker, 100, 13);
assert(partial.added.length > 0 && partial.remaining > 0);
check([...mixed, ...partial.added]);
assert.equal(pack([...mixed, ...partial.added, { ...sticker, id: 9999 }]).ok, false);
console.log('PASS: physical size boxes, proportional fitting, quantities, margins/gaps, rotation, 10-sheet and 350-item limits, partial additions, existing order preservation, huge quantities, mixed sizes, exact remainder');
