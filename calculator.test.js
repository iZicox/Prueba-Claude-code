const test = require('node:test');
const assert = require('node:assert/strict');
const { initialState, reduce, format } = require('./calculator.js');

function run(...actions) {
  return actions.reduce((s, a) => reduce(s, a), initialState());
}

const digits = (...ds) => ds.map((value) => ({ type: 'digit', value }));
const op = (value) => ({ type: 'operator', value });
const EQ = { type: 'equals' };

test('typing digits builds a number and leading zeros are dropped', () => {
  assert.equal(run(...digits('0', '0', '4', '2')).current, '42');
});

test('basic operations', () => {
  assert.equal(run(...digits('7'), op('+'), ...digits('5'), EQ).current, '12');
  assert.equal(run(...digits('7'), op('-'), ...digits('5'), EQ).current, '2');
  assert.equal(run(...digits('6'), op('*'), ...digits('7'), EQ).current, '42');
  assert.equal(run(...digits('8'), op('/'), ...digits('2'), EQ).current, '4');
});

test('decimals and floating point noise is cleaned up', () => {
  const s = run(...digits('0'), { type: 'decimal' }, ...digits('1'), op('+'), ...digits('0'), { type: 'decimal' }, ...digits('2'), EQ);
  assert.equal(s.current, '0.3');
});

test('a decimal point is not added twice', () => {
  const s = run(...digits('1'), { type: 'decimal' }, { type: 'decimal' }, ...digits('5'));
  assert.equal(s.current, '1.5');
});

test('chained operations are evaluated left to right', () => {
  const s = run(...digits('2'), op('+'), ...digits('3'), op('*'), ...digits('4'), EQ);
  assert.equal(s.current, '20');
});

test('pressing an operator twice replaces it instead of computing', () => {
  const s = run(...digits('9'), op('+'), op('*'), ...digits('3'), EQ);
  assert.equal(s.current, '27');
});

test('division by zero shows an error and the error clears on next digit', () => {
  const err = run(...digits('1'), op('/'), ...digits('0'), EQ);
  assert.equal(err.error, true);
  assert.equal(err.current, 'Error');
  assert.equal(reduce(err, digits('5')[0]).current, '5');
});

test('operators are ignored while in error state', () => {
  const err = run(...digits('1'), op('/'), ...digits('0'), EQ);
  assert.equal(reduce(err, op('+')), err);
});

test('clear resets everything', () => {
  assert.deepEqual(run(...digits('1'), op('+'), ...digits('2'), { type: 'clear' }), initialState());
});

test('sign toggle works on the current entry', () => {
  assert.equal(run(...digits('5'), { type: 'sign' }).current, '-5');
  assert.equal(run(...digits('5'), { type: 'sign' }, { type: 'sign' }).current, '5');
  assert.equal(run({ type: 'sign' }).current, '-0');
});

test('typing after a negative sign replaces the placeholder zero', () => {
  assert.equal(run({ type: 'sign' }, ...digits('0', '7')).current, '-7');
});

test('percent divides the current entry by 100', () => {
  assert.equal(run(...digits('5', '0'), { type: 'percent' }).current, '0.5');
});

test('backspace removes the last digit and falls back to 0', () => {
  assert.equal(run(...digits('1', '2', '3'), { type: 'backspace' }).current, '12');
  assert.equal(run(...digits('5'), { type: 'backspace' }).current, '0');
  assert.equal(run({ type: 'sign' }, ...digits('5'), { type: 'backspace' }).current, '0');
});

test('entry is capped at 12 digits', () => {
  const s = run(...digits('1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1', '1'));
  assert.equal(s.current, '111111111111');
});

test('format rounds to 12 significant digits', () => {
  assert.equal(format(1 / 3), '0.333333333333');
  assert.equal(format(Infinity), 'Error');
});
