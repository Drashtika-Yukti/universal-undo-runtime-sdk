/**
 * uur.js — Node.js binding for Universal Undo Runtime
 * =====================================================
 * Location: bindings/nodejs/uur.js
 *
 * Uses koffi (fast FFI, no node-gyp, no compilation).
 * Install once:  npm install koffi
 *
 * Usage:
 *   const { Engine } = require('./uur');
 *
 *   const e = new Engine();
 *   e.commit('text', 'Hello');
 *   e.commit('text', 'Hello World');
 *   e.undo();           // → 'Hello'
 *   e.goto(2);          // → 'Hello World'
 *   e.printHistory();
 *   e.close();
 */

'use strict';

const koffi = require('koffi');
const path  = require('path');
const fs    = require('fs');

// ── locate DLL ───────────────────────────────────────────────────────────────

function findDll() {
  const name = 'libuniversal_undo_runtime.dll';

  // This file is at: <repo>/bindings/nodejs/uur.js
  // DLL is at:       <repo>/build/libuniversal_undo_runtime.dll
  const here = __dirname;
  const repo = path.resolve(here, '..', '..');

  const candidates = [
    path.join(repo,  'build', name),
    path.join(here,  name),
    path.join(here, '..', name),
  ];

  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }

  throw new Error(
    `Cannot find ${name}\nSearched:\n` +
    candidates.map(p => `  ${p}`).join('\n') + '\n\n' +
    `Pass explicitly: new Engine({ dllPath: 'F:\\\\...\\\\build\\\\${name}' })`
  );
}

// ── struct defined ONCE at module level (koffi registers types globally) ─────

const UndoRuntimeNode = koffi.struct('UndoRuntimeNode', {
  entity_id:     'uint64',
  domain_type:   'uint8',
  payload_token: 'uint32',
  prop_key:      'uint32',
  prop_val:      'uint32',
});

// ── load library & define signatures ─────────────────────────────────────────

function loadLib(dllPath) {
  const lib = koffi.load(dllPath);

  return {
    create:  lib.func('void* uur_create_engine()'),
    destroy: lib.func('void  uur_destroy_engine(void* engine)'),
    commit:  lib.func('void  uur_commit_transaction_block(void* engine, UndoRuntimeNode* nodes, size_t count, uint64 seq)'),
    query:   lib.func('uint32 uur_query_historical_token(void* engine, uint64 entity_id, uint64 seq)'),
  };
}

// ── Engine class ─────────────────────────────────────────────────────────────

const DEFAULT_ENTITY = BigInt('0xED170001');

class Engine {
  constructor({ dllPath } = {}) {
    const p      = dllPath || findDll();
    this._api    = loadLib(p);
    this._handle = this._api.create();

    if (!this._handle) throw new Error('uur_create_engine() returned NULL');

    this._snapshots = [];   // [{ seq, entityId, label, value }]
    this._ptr       = -1;
    this._seq       = 0n;   // BigInt for uint64
    this._status    = 'Engine ready.';
  }

  // ── internals ──────────────────────────────────────────────────────────────

  _nextSeq() { return ++this._seq; }

  _toToken(value) {
    // simple djb2 hash of the JSON string — fits uint32
    const s   = JSON.stringify(value) ?? String(value);
    let hash  = 5381;
    for (let i = 0; i < s.length; i++) {
      hash = ((hash << 5) + hash + s.charCodeAt(i)) >>> 0;
    }
    return hash;
  }

  _pushToEngine(snap) {
    const node = {
      entity_id:     snap.entityId,
      domain_type:   1,
      payload_token: this._toToken(snap.value),
      prop_key:      0,
      prop_val:      0,
    };
    this._api.commit(this._handle, node, 1, snap.seq);
  }

  _queryEngine(snap) {
    return this._api.query(this._handle, snap.entityId, snap.seq);
  }

  // ── public API ─────────────────────────────────────────────────────────────

  /** Record a new state. Accepts any JSON-serializable value. */
  commit(label, value, entityId = DEFAULT_ENTITY) {
    const seq  = this._nextSeq();
    const snap = { seq, entityId, label, value };

    // discard redo branch
    if (this._ptr < this._snapshots.length - 1) {
      this._snapshots = this._snapshots.slice(0, this._ptr + 1);
    }

    this._snapshots.push(snap);
    this._ptr = this._snapshots.length - 1;
    this._pushToEngine(snap);
    this._status = `Committed step ${this.step} → ${JSON.stringify(value)}`;
  }

  /** Step one back. Returns the restored value. */
  undo() {
    if (this._ptr <= 0) {
      this._status = 'Nothing left to undo.';
      return this.current;
    }
    this._ptr--;
    const snap    = this._snapshots[this._ptr];
    this._queryEngine(snap);
    this._status  = `UNDO → step ${this.step} [${JSON.stringify(snap.value)}]`;
    return snap.value;
  }

  /** Step one forward. Returns the restored value. */
  redo() {
    if (this._ptr >= this._snapshots.length - 1) {
      this._status = 'Already at latest state.';
      return this.current;
    }
    this._ptr++;
    const snap   = this._snapshots[this._ptr];
    this._queryEngine(snap);
    this._status = `REDO → step ${this.step} [${JSON.stringify(snap.value)}]`;
    return snap.value;
  }

  /**
   * Jump directly to any step.
   *   goto(1)   → first commit
   *   goto(6)   → sixth commit
   *   goto(-1)  → last commit
   */
  goto(step) {
    const total = this._snapshots.length;
    if (total === 0) { this._status = 'No history yet.'; return null; }

    if (step < 0) step = total + step + 1;

    if (step < 1 || step > total) {
      this._status = `Step ${step} out of range (1–${total}).`;
      return this.current;
    }

    this._ptr    = step - 1;
    const snap   = this._snapshots[this._ptr];
    this._queryEngine(snap);
    this._status = `GOTO step ${step} [${JSON.stringify(snap.value)}]`;
    return snap.value;
  }

  // ── properties ─────────────────────────────────────────────────────────────

  get current() {
    return this._ptr >= 0 ? this._snapshots[this._ptr].value : null;
  }

  get step() { return this._ptr + 1; }
  get totalSteps() { return this._snapshots.length; }
  get status() { return this._status; }

  get history() {
    return this._snapshots.map((s, i) => ({
      step:    i + 1,
      label:   s.label,
      value:   s.value,
      current: i === this._ptr,
    }));
  }

  printHistory() {
    console.log();
    console.log(`  ${'STEP'.padEnd(6)} ${'LABEL'.padEnd(20)} ${'VALUE'.padEnd(35)}`);
    console.log(`  ${'----'.padEnd(6)} ${'--------------------'.padEnd(20)} ${'---'.padEnd(35)}`);
    for (const h of this.history) {
      const marker = h.current ? '  ◄ YOU ARE HERE' : '';
      const val    = JSON.stringify(h.value).padEnd(35);
      console.log(`  ${String(h.step).padEnd(6)} ${h.label.padEnd(20)} ${val}${marker}`);
    }
    console.log();
  }

  // ── lifecycle ──────────────────────────────────────────────────────────────

  close() {
    if (this._handle) {
      this._api.destroy(this._handle);
      this._handle = null;
    }
  }
}

module.exports = { Engine };
