const assert = require('node:assert/strict');
const State = require('./catalog-state');

assert.deepEqual(State.read('?section=%D0%9A%D0%9E%D0%A2%D0%AB&q=%D0%BE%D0%B9&scope=all&sort=name&shown=80&sticker=RK17-0008&mix=shared42'), {
  query:'ой', filters:{ section:'КОТЫ', character:'', role:'', mood:'' }, scope:'all', sort:'name', shown:80, sticker:'RK17-0008', mix:'shared42',
});
assert.equal(State.write('?qa=cache', {
  query:'ой', filters:{ section:'КОТЫ', character:'RK17', role:'', mood:'' }, scope:'selection', sort:'catalog', shown:40, sticker:'', mix:'shared42',
}), '?qa=cache&q=%D0%BE%D0%B9&section=%D0%9A%D0%9E%D0%A2%D0%AB&character=RK17&sort=catalog&shown=40&mix=shared42');
assert.equal(State.write('?q=old&scope=all&sort=name&shown=80&sticker=x&qa=1', {
  query:'', filters:{ section:'', character:'', role:'', mood:'' }, scope:'selection', sort:'relevance', shown:0, sticker:'', mix:'',
}), '?qa=1');
assert.equal(State.read('?shown=-1&scope=other&sort=random').shown, 0);
assert.equal(State.read('?mix=%3Cscript%3E').mix, '');
console.log('PASS: catalog URL state parsing and serialization');
