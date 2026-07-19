/**
 * test_uur.js — Node.js binding test suite
 * ==========================================
 * Install: npm install koffi
 * Run:     node test_uur.js
 */

'use strict';

const { Engine } = require('./uur');

let passed = 0;
let failed = 0;

function check(label, got, expected) {
  const ok  = JSON.stringify(got) === JSON.stringify(expected);
  const sym = ok ? '✓' : '✗';
  console.log(`  ${sym}  ${label}`);
  if (!ok) {
    console.log(`       got:      ${JSON.stringify(got)}`);
    console.log(`       expected: ${JSON.stringify(expected)}`);
    failed++;
  } else {
    passed++;
  }
}

console.log('\n============================================================');
console.log('  Universal Undo Runtime — Node.js Binding Test Suite');
console.log('============================================================');

// [ 1 ] Basic commit
console.log('\n[ 1 ] Basic commit');
{
  const e = new Engine();
  e.commit('text', 'Hello');
  e.commit('text', 'Hello World');
  e.commit('text', 'Hello World!');
  check('step count is 3',  e.totalSteps, 3);
  check('current is last',  e.current,    'Hello World!');
  check('step number is 3', e.step,       3);
  e.close();
}

// [ 2 ] Undo
console.log('\n[ 2 ] Undo');
{
  const e = new Engine();
  e.commit('text', 'A');
  e.commit('text', 'AB');
  e.commit('text', 'ABC');
  check('undo once → AB',         e.undo(), 'AB');
  check('step is 2',              e.step,   2);
  check('undo twice → A',         e.undo(), 'A');
  check('undo past start → A',    e.undo(), 'A');
  e.close();
}

// [ 3 ] Redo
console.log('\n[ 3 ] Redo');
{
  const e = new Engine();
  e.commit('text', 'X');
  e.commit('text', 'XY');
  e.commit('text', 'XYZ');
  e.undo(); e.undo();
  check('redo once → XY',         e.redo(), 'XY');
  check('redo twice → XYZ',       e.redo(), 'XYZ');
  check('redo past end → XYZ',    e.redo(), 'XYZ');
  e.close();
}

// [ 4 ] Goto
console.log('\n[ 4 ] Goto');
{
  const e = new Engine();
  [10, 20, 30, 40, 50, 60].forEach((v, i) => e.commit('score', v));
  check('goto(1) → 10',           e.goto(1),   10);
  check('goto(6) → 60',           e.goto(6),   60);
  check('goto(3) → 30',           e.goto(3),   30);
  check('goto(-1) → 60',          e.goto(-1),  60);
  check('goto(99) stays at 60',   e.goto(99),  60);
  e.close();
}

// [ 5 ] Branch discard
console.log('\n[ 5 ] Branch discard');
{
  const e = new Engine();
  e.commit('text', 'one');
  e.commit('text', 'two');
  e.commit('text', 'three');
  e.undo();
  e.commit('text', 'NEW');
  check('total steps is 3',       e.totalSteps, 3);
  check('current is NEW',         e.current,    'NEW');
  check('redo does nothing',      e.redo(),     'NEW');
  e.close();
}

// [ 6 ] Any JS type
console.log('\n[ 6 ] Works with any JS value type');
{
  const e = new Engine();
  e.commit('number', 42);
  e.commit('obj',    { x: 1, y: 2 });
  e.commit('array',  [1, 2, 3]);
  e.commit('bool',   true);
  check('current is true',        e.current,   true);
  e.undo();
  check('undo → array',           e.current,   [1, 2, 3]);
  e.goto(1);
  check('goto(1) → 42',           e.current,   42);
  e.close();
}

// [ 7 ] printHistory
console.log('\n[ 7 ] printHistory() output');
{
  const e = new Engine();
  e.commit('file', 'doc.txt');
  e.commit('file', 'report.pdf');
  e.commit('file', 'final.docx');
  e.goto(2);
  e.printHistory();
  e.close();
}

// Summary
console.log('============================================================');
console.log(`  ${passed + failed} checks  —  ${passed} passed  ${failed} failed`);
if (failed === 0) console.log('  ALL TESTS PASSED  ✓');
console.log('============================================================\n');

process.exit(failed > 0 ? 1 : 0);
