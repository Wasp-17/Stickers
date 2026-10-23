const assert = require('node:assert/strict');
const Ranking = require('./catalog-ranking');

const sample = Array.from({ length:120 }, (_, index) => ({
  id:`S-${index + 1}`,
  entry:{ image_id:`S-${index + 1}`, field_concepts:{ role:[`ROLE_${index % 4}`] } },
}));
const first = Ranking.rank(sample, { seed:'shared-link' });
const same = Ranking.rank(sample, { seed:'shared-link' });
const other = Ranking.rank(sample, { seed:'new-visit' });
assert.deepEqual(first.map(item => item.id), same.map(item => item.id));
assert.notDeepEqual(first.map(item => item.id), other.map(item => item.id));
assert.equal(new Set(first.map(item => item.id)).size, sample.length);

const stats = {
  'S-90':{ paidOrders:8, paidUnits:20, favoriteAdds:1 },
  'S-80':{ paidOrders:2, paidUnits:3, favoriteAdds:50 },
  'S-70':{ paidOrders:0, favoriteAdds:500 },
};
const ranked = Ranking.rank(sample, { seed:'priority', stats, reservedCount:10 });
assert.equal(ranked[0].id, 'S-90');
assert.ok(ranked.slice(0, 10).some(item => item.id === 'S-80'));
assert.ok(ranked.slice(0, 10).some(item => item.id === 'S-70'));
for (let index = 2; index < ranked.length; index += 1) {
  const categories = ranked.slice(index - 2, index + 1).map(Ranking.semanticCategory);
  assert.equal(new Set(categories).size === 1, false);
}
console.log('PASS: stable shared shuffle, new-visit seed, no duplicates, reserved popularity and semantic diversity');
