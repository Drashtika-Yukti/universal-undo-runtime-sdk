"""
uur.py  —  Python binding for Universal Undo Runtime
=====================================================
Location: bindings/python/uur.py

Wraps the 4 C-ABI functions from libuniversal_undo_runtime.dll
using only Python's built-in ctypes — no pip install needed.

Usage:
    import sys
    sys.path.insert(0, r"F:\\universal_undo_runtime\\bindings\\python")
    from uur import Engine

    with Engine() as e:
        e.commit("text", "Hello")
        e.commit("text", "Hello World")
        e.undo()            # → "Hello"
        e.goto(2)           # → "Hello World"
        e.print_history()
"""

import ctypes
import os
import sys
from pathlib import Path

# ── auto-add MSYS2 runtime DLLs on Windows ───────────────────────────────────
# libuniversal_undo_runtime.dll depends on libgcc_s_seh-1.dll, libstdc++-6.dll
# etc. which live in MSYS2. We add the most common paths automatically so the
# user doesn't have to set PATH manually every session.

def _ensure_msys2_on_path():
    if sys.platform != "win32":
        return
    candidates = [
        r"F:\Program_Files\MSYS2\ucrt64\bin",
        r"C:\msys64\ucrt64\bin",
        r"C:\msys64\mingw64\bin",
        r"C:\tools\msys64\ucrt64\bin",
    ]
    current = os.environ.get("PATH", "")
    for p in candidates:
        if Path(p).exists() and p not in current:
            os.add_dll_directory(p)          # Python 3.8+ Windows-specific
            os.environ["PATH"] = p + ";" + current
            break

_ensure_msys2_on_path()


# ── locate the DLL ────────────────────────────────────────────────────────────

def _find_dll() -> str:
    name = "libuniversal_undo_runtime.dll"

    # This file is at:  <repo>/bindings/python/uur.py
    # DLL is at:        <repo>/build/libuniversal_undo_runtime.dll
    here = Path(__file__).resolve().parent          # bindings/python/
    repo = here.parent.parent                        # repo root

    candidates = [
        repo  / "build" / name,
        here  / name,
        here.parent / name,
        Path(name),
    ]

    for p in candidates:
        if p.exists():
            return str(p)

    raise FileNotFoundError(
        f"\nCannot find {name}\n"
        f"Searched:\n" + "\n".join(f"  {p}" for p in candidates) + "\n\n"
        f"Pass explicitly:  Engine(dll_path=r'F:\\...\\build\\{name}')\n"
        f"Or add MSYS2 bin to PATH:\n"
        f"  $env:PATH = 'F:\\Program_Files\\MSYS2\\ucrt64\\bin;' + $env:PATH"
    )


# ── raw C-ABI structs & signatures ────────────────────────────────────────────

class _UndoRuntimeNode(ctypes.Structure):
    _fields_ = [
        ("entity_id",     ctypes.c_uint64),
        ("domain_type",   ctypes.c_uint8),
        ("payload_token", ctypes.c_uint32),
        ("prop_key",      ctypes.c_uint32),
        ("prop_val",      ctypes.c_uint32),
    ]


def _load_lib(dll_path: str):
    lib = ctypes.CDLL(dll_path)

    lib.uur_create_engine.restype  = ctypes.c_void_p
    lib.uur_create_engine.argtypes = []

    lib.uur_destroy_engine.restype  = None
    lib.uur_destroy_engine.argtypes = [ctypes.c_void_p]

    lib.uur_commit_transaction_block.restype  = None
    lib.uur_commit_transaction_block.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_UndoRuntimeNode),
        ctypes.c_size_t,
        ctypes.c_uint64,
    ]

    lib.uur_query_historical_token.restype  = ctypes.c_uint32
    lib.uur_query_historical_token.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint64,
        ctypes.c_uint64,
    ]

    # Phase 3: milestone tagging
    lib.uur_commit_tagged.restype  = None
    lib.uur_commit_tagged.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_UndoRuntimeNode),
        ctypes.c_size_t,
        ctypes.c_uint64,
        ctypes.c_char_p,
    ]
    lib.uur_query_tag.restype  = ctypes.c_char_p
    lib.uur_query_tag.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
    lib.uur_destroy_engine_tagged.restype  = None
    lib.uur_destroy_engine_tagged.argtypes = [ctypes.c_void_p]

    return lib


# ── snapshot record ───────────────────────────────────────────────────────────

class _Snapshot:
    def __init__(self, seq, entity_id, label, value):
        self.seq       = seq
        self.entity_id = entity_id
        self.label     = label
        self.value     = value


# ── Engine ────────────────────────────────────────────────────────────────────

class Engine:
    """
    High-level Python interface to the Universal Undo Runtime.

    Methods:
        commit(label, value)        record a new state
        undo()                      step one back
        redo()                      step one forward
        goto(step)                  jump to any step directly
        print_history()             pretty-print the full timeline

    Properties:
        current                     value at current pointer
        step                        current step number (1-based)
        total_steps                 total steps in history
        status                      last operation description
        history                     full history as list of dicts
    """

    _DEFAULT_ENTITY = 0xED170001

    def __init__(self, dll_path: str = None):
        path          = dll_path or _find_dll()
        self._lib     = _load_lib(path)
        self._engine  = self._lib.uur_create_engine()

        if not self._engine:
            raise RuntimeError("uur_create_engine() returned NULL")

        self._snapshots: list = []
        self._ptr             = -1
        self._seq             = 0
        self._status          = "Engine ready."

    # ── internals ─────────────────────────────────────────────────────────────

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _make_node(self, entity_id: int, value) -> _UndoRuntimeNode:
        try:
            token = hash(value) & 0xFFFFFFFF
        except TypeError:
            token = hash(str(value)) & 0xFFFFFFFF
        return _UndoRuntimeNode(
            entity_id=entity_id, domain_type=1,
            payload_token=token, prop_key=0, prop_val=0
        )

    def _push_to_engine(self, snap: _Snapshot, tag: str = None):
        node = self._make_node(snap.entity_id, snap.value)
        arr  = (_UndoRuntimeNode * 1)(node)
        if tag:
            self._lib.uur_commit_tagged(
                self._engine, arr, 1, snap.seq,
                tag.encode("utf-8")
            )
        else:
            self._lib.uur_commit_transaction_block(
                self._engine, arr, 1, snap.seq
            )

    def _query_engine(self, snap: _Snapshot):
        return self._lib.uur_query_historical_token(
            self._engine, snap.entity_id, snap.seq
        )

    # ── public API ────────────────────────────────────────────────────────────

    def commit(self, label: str, value=None, entity_id: int = None, tag: str = None):
        """Record a new state. Any Python value is accepted.
        
        Pass tag='some label' to mark this step as a named milestone.
        Example: tag='function:calculate_total created'
        """
        eid = entity_id or self._DEFAULT_ENTITY
        seq = self._next_seq()
        snap = _Snapshot(seq=seq, entity_id=eid, label=label, value=value)

        # discard redo branch if we're not at the tip
        if self._ptr < len(self._snapshots) - 1:
            self._snapshots = self._snapshots[: self._ptr + 1]

        self._snapshots.append(snap)
        self._ptr = len(self._snapshots) - 1
        self._push_to_engine(snap, tag=tag)
        tag_info = f"  [milestone: {tag}]" if tag else ""
        self._status = f"Committed step {self.step} → {repr(value)}{tag_info}"

    def undo(self):
        """Step one back. Returns the restored value."""
        if self._ptr <= 0:
            self._status = "Nothing left to undo."
            return self.current
        self._ptr -= 1
        snap = self._snapshots[self._ptr]
        self._query_engine(snap)
        self._status = f"UNDO → step {self.step}  [{repr(snap.value)}]"
        return snap.value

    def redo(self):
        """Step one forward. Returns the restored value."""
        if self._ptr >= len(self._snapshots) - 1:
            self._status = "Already at latest state."
            return self.current
        self._ptr += 1
        snap = self._snapshots[self._ptr]
        self._query_engine(snap)
        self._status = f"REDO → step {self.step}  [{repr(snap.value)}]"
        return snap.value

    def goto(self, step: int):
        """
        Jump directly to any step.
            goto(1)   first commit
            goto(6)   sixth commit
            goto(-1)  last commit
        """
        total = len(self._snapshots)
        if total == 0:
            self._status = "No history yet."
            return None

        if step < 0:
            step = total + step + 1

        if step < 1 or step > total:
            self._status = f"Step {step} out of range (1–{total})."
            return self.current

        self._ptr = step - 1
        snap      = self._snapshots[self._ptr]
        self._query_engine(snap)
        self._status = f"GOTO step {step}  [{repr(snap.value)}]"
        return snap.value

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def current(self):
        return self._snapshots[self._ptr].value if self._ptr >= 0 else None

    @property
    def step(self) -> int:
        return self._ptr + 1

    @property
    def total_steps(self) -> int:
        return len(self._snapshots)

    @property
    def status(self) -> str:
        return self._status

    @property
    def history(self) -> list:
        return [
            {
                "step":    i + 1,
                "label":   s.label,
                "value":   s.value,
                "current": i == self._ptr,
            }
            for i, s in enumerate(self._snapshots)
        ]

    def get_tag(self, step: int = None) -> str | None:
        """Return the milestone tag for a step (default: current step).
        Returns None if no tag was set for that step."""
        if step is None:
            step = self.step
        if step < 1 or step > len(self._snapshots):
            return None
        snap   = self._snapshots[step - 1]
        result = self._lib.uur_query_tag(self._engine, snap.seq)
        if result is None:
            return None
        return result.decode("utf-8")

    def goto_tag(self, tag: str):
        """Jump directly to the first step with this milestone tag.
        Returns the value at that step, or None if tag not found."""
        for i, snap in enumerate(self._snapshots):
            result = self._lib.uur_query_tag(self._engine, snap.seq)
            if result and result.decode("utf-8") == tag:
                self._ptr    = i
                self._status = f"GOTO TAG '{tag}'  → step {self.step}"
                self._query_engine(snap)
                return snap.value
        self._status = f"Tag '{tag}' not found."
        return None

    def print_history(self):
        print(f"\n  {'STEP':<6} {'LABEL':<20} {'VALUE':<30} {'TAG'}")
        print(f"  {'-'*4:<6} {'-'*20:<20} {'-'*30} {'-'*25}")
        for h in self.history:
            marker = " ◄" if h["current"] else ""
            tag    = self.get_tag(h["step"]) or ""
            tag_str = f"[{tag}]" if tag else ""
            print(f"  {h['step']:<6} {str(h['label']):<20} {repr(h['value']):<30} {tag_str}{marker}")
        print()

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def close(self):
        if self._engine:
            self._lib.uur_destroy_engine_tagged(self._engine)
            self._engine = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __repr__(self):
        return (f"<UndoEngine step={self.step}/{self.total_steps} "
                f"current={repr(self.current)}>")
