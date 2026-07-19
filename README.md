# Universal Undo Runtime — SDK

**Non-linear undo/redo engine for any application. Callable from C, C++, Python, Node.js, Go, or any language with C FFI.**

---

## The problem every developer hits

Every application that needs undo builds the same thing from scratch — a linear stack of states. It works until you need branching history, concurrent writes, or real performance. Then it falls apart.

## What this solves

Universal Undo Runtime is a production-frozen engine that gives your application:

- **Non-linear branching history** — like Git, but for your application's state
- **Direct time-travel** — jump to any step instantly, not just step back one at a time
- **Named milestones** — tag important steps and jump to them by name
- **Microsecond queries** — 4µs average to jump anywhere in a 10,000-step history
- **Any language** — one C ABI, bindings for Python, Node.js, Go included
- **Replication-ready** — built-in frame queue for distributed sync (Phase 5)

---

## Quickstart — Python

```python
from uur import Engine

with Engine() as e:
    e.commit("text", "Hello")
    e.commit("text", "Hello World",  tag="milestone:first sentence")
    e.commit("text", "Hello World!")

    e.undo()           # → "Hello World"
    e.redo()           # → "Hello World!"
    e.goto(1)          # → "Hello"  (jump directly, no stepping)
    e.goto_tag("milestone:first sentence")  # → "Hello World"

    e.print_history()
```

Output:
```
  STEP   LABEL      VALUE              TAG
  1      text       'Hello'
  2      text       'Hello World'      [milestone:first sentence]  ◄ YOU ARE HERE
  3      text       'Hello World!'
```

---

## Quickstart — Node.js

```js
const { Engine } = require('./uur');

const e = new Engine();
e.commit('score', 100);
e.commit('score', 200, { tag: 'milestone:level 2' });
e.commit('score', 300);

e.goto(2);              // jump to step 2 directly
console.log(e.current); // 200
e.close();
```

---

## Quickstart — Go

```go
e := NewEngine()
defer e.Close()

e.Commit("state", "idle")
e.Commit("state", "running")
e.Commit("state", "done")

e.Undo()              // → "running"
e.Goto(1)             // → "idle"
e.PrintHistory()
```

---

## Installation

**Requirements:** Windows x64, Python 3.9+, Node.js 18+, or Go 1.21+

1. Download `libuniversal_undo_runtime.dll` and `universal_undo_runtime.h` from [Releases](../../releases)
2. Place them in your project folder
3. Copy the binding file for your language from `bindings/`

**Python** — no pip install needed, uses built-in `ctypes`:
```python
import sys
sys.path.insert(0, 'path/to/bindings/python')
from uur import Engine
```

**Node.js** — requires `koffi`:
```bash
npm install koffi
```

**Go** — requires CGO and MinGW:
```bash
set CGO_ENABLED=1
set CC=x86_64-w64-mingw32-gcc
```

---

## API reference

### Core — all languages

| Function | Description |
|----------|-------------|
| `commit(label, value)` | Record a new state |
| `commit(label, value, tag="...")` | Record with a named milestone |
| `undo()` | Step one back, returns restored value |
| `redo()` | Step one forward, returns restored value |
| `goto(step)` | Jump directly to any step (1-based, negative supported) |
| `goto_tag(name)` | Jump directly to a named milestone |
| `get_tag(step)` | Get the milestone label for a step |
| `print_history()` | Pretty-print full timeline |
| `current` | Value at current position |
| `step` | Current step number |
| `total_steps` | Total steps in history |

### C ABI — for other languages

```c
UniversalUndoEngine* uur_create_engine(void);
void                 uur_destroy_engine(UniversalUndoEngine* engine);
void                 uur_commit_transaction_block(engine, nodes, count, sequence_id);
uint32_t             uur_query_historical_token(engine, entity_id, sequence_id);
void                 uur_commit_tagged(engine, nodes, count, sequence_id, tag);
const char*          uur_query_tag(engine, sequence_id);
bool                 uur_pop_replication_frame(engine, out_frame);
```

---

## Performance (Windows x64, Phase 4 benchmarks)

| Operation | Result |
|-----------|--------|
| Commit throughput | ~147,000 / sec |
| Undo / Redo throughput | ~620,000 / sec |
| Goto — avg latency (10,000-step history) | **4 µs** |
| Stress: 10,000 commits + 1,000 random gotos | 121 ms total |
| Branch discard (2,500 steps pruned) | 136 µs |

---

## What can I store?

Anything your language can represent. The engine stores tokens — your binding handles the actual values.

| Type | Python | Node.js | Go |
|------|--------|---------|-----|
| Strings | ✅ | ✅ | ✅ |
| Numbers | ✅ | ✅ | ✅ |
| Dicts / Objects | ✅ | ✅ | ✅ |
| Lists / Arrays | ✅ | ✅ | ✅ |
| Booleans | ✅ | ✅ | ✅ |
| Any type | ✅ | ✅ | ✅ |

---

## Who is this for

- **Editor developers** — add non-linear undo to any text editor, code editor, or design tool
- **Game developers** — track game state, scene edits, or level editor history
- **Collaborative tool builders** — foundation for shared history across users (Phase 5)
- **Any developer** who is tired of writing their own undo stack from scratch

---

## Repository structure

```
universal-undo-runtime-sdk/
├── include/
│   └── universal_undo_runtime.h     ← drop this in your project
├── bindings/
│   ├── python/
│   │   ├── uur.py                   ← Python binding
│   │   └── test_uur.py
│   ├── nodejs/
│   │   ├── uur.js                   ← Node.js binding
│   │   ├── test_uur.js
│   │   └── package.json
│   └── go/
│       ├── uur.go                   ← Go binding
│       ├── test_uur.go
│       └── go.mod
├── benchmarks/
│   └── bench_uur.py
├── tests/
│   ├── harness.c
│   ├── tagged_harness.c
│   └── replication_harness.c
├── demo_editor.c                    ← interactive demo (compile with gcc)
└── README.md
```

The compiled DLL is attached to each [Release](../../releases). The engine source is closed.

---

## Running the tests

```powershell
$env:PATH = "F:\Program_Files\MSYS2\ucrt64\bin;" + $env:PATH

# Python
python bindings\python\test_uur.py

# Node.js
cd bindings\nodejs && npm install && node test_uur.js

# Go
cd bindings\go
set CGO_ENABLED=1 && set CC=x86_64-w64-mingw32-gcc
go run test_uur.go uur.go
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE)

The engine binary (`libuniversal_undo_runtime.dll`) is distributed as a compiled artifact. Source is closed.

---

## Links

- [Releases](../../releases) — download the DLL
- [ROADMAP](ROADMAP.md) — what's coming next
- [Source repo](https://github.com/Drashtika-Yukti/universal-undo-runtime) — private
