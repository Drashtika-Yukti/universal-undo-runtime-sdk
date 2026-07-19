// uur.go — Go binding for Universal Undo Runtime
// ================================================
// Location: bindings/go/uur.go
//
// Uses cgo to call the C ABI directly.
// Requires: libuniversal_undo_runtime.dll in build/
//
// Build:
//   set CGO_ENABLED=1
//   set CC=x86_64-w64-mingw32-gcc
//   go build ./...
//
// Usage:
//   engine := uur.NewEngine("../../build/libuniversal_undo_runtime.dll")
//   defer engine.Close()
//
//   engine.Commit("text", "Hello")
//   engine.Commit("text", "Hello World")
//   engine.Undo()       // → "Hello"
//   engine.Goto(2)      // → "Hello World"
//   engine.PrintHistory()

package main

/*
#cgo CFLAGS:  -I../../include
#cgo LDFLAGS: -L../../build -luniversal_undo_runtime

#include "universal_undo_runtime.h"
#include <stdlib.h>
*/
import "C"
import (
	"fmt"
	"unsafe"
)

const defaultEntity = C.uint64_t(0xED170001)

// Snapshot holds one point in history.
type Snapshot struct {
	Seq      uint64
	EntityID uint64
	Label    string
	Value    interface{}
}

// Engine is the high-level Go interface to the Universal Undo Runtime.
type Engine struct {
	handle    *C.UniversalUndoEngine
	snapshots []Snapshot
	ptr       int
	seq       uint64
	Status    string
}

// NewEngine creates and returns a new Engine.
func NewEngine() *Engine {
	h := C.uur_create_engine()
	if h == nil {
		panic("uur_create_engine() returned NULL")
	}
	return &Engine{
		handle: h,
		ptr:    -1,
		Status: "Engine ready.",
	}
}

// ── internals ────────────────────────────────────────────────────────────────

func (e *Engine) nextSeq() uint64 {
	e.seq++
	return e.seq
}

func simpleHash(v interface{}) C.uint32_t {
	s := fmt.Sprintf("%v", v)
	var h uint32 = 5381
	for _, c := range []byte(s) {
		h = ((h << 5) + h) + uint32(c)
	}
	return C.uint32_t(h)
}

func (e *Engine) pushToEngine(snap Snapshot) {
	node := C.UndoRuntimeNode{
		entity_id:     C.uint64_t(snap.EntityID),
		domain_type:   C.uint8_t(1),
		payload_token: simpleHash(snap.Value),
		prop_key:      0,
		prop_val:      0,
	}
	C.uur_commit_transaction_block(
		e.handle,
		(*C.UndoRuntimeNode)(unsafe.Pointer(&node)),
		C.size_t(1),
		C.uint64_t(snap.Seq),
	)
}

func (e *Engine) queryEngine(snap Snapshot) uint32 {
	return uint32(C.uur_query_historical_token(
		e.handle,
		C.uint64_t(snap.EntityID),
		C.uint64_t(snap.Seq),
	))
}

// ── public API ────────────────────────────────────────────────────────────────

// Commit records a new state. Value can be any type.
func (e *Engine) Commit(label string, value interface{}) {
	seq := e.nextSeq()
	snap := Snapshot{Seq: seq, EntityID: uint64(defaultEntity), Label: label, Value: value}

	// discard redo branch
	if e.ptr < len(e.snapshots)-1 {
		e.snapshots = e.snapshots[:e.ptr+1]
	}

	e.snapshots = append(e.snapshots, snap)
	e.ptr = len(e.snapshots) - 1
	e.pushToEngine(snap)
	e.Status = fmt.Sprintf("Committed step %d → %v", e.Step(), value)
}

// Undo steps one back and returns the restored value.
func (e *Engine) Undo() interface{} {
	if e.ptr <= 0 {
		e.Status = "Nothing left to undo."
		return e.Current()
	}
	e.ptr--
	snap := e.snapshots[e.ptr]
	e.queryEngine(snap)
	e.Status = fmt.Sprintf("UNDO → step %d [%v]", e.Step(), snap.Value)
	return snap.Value
}

// Redo steps one forward and returns the restored value.
func (e *Engine) Redo() interface{} {
	if e.ptr >= len(e.snapshots)-1 {
		e.Status = "Already at latest state."
		return e.Current()
	}
	e.ptr++
	snap := e.snapshots[e.ptr]
	e.queryEngine(snap)
	e.Status = fmt.Sprintf("REDO → step %d [%v]", e.Step(), snap.Value)
	return snap.Value
}

// Goto jumps directly to any step (1-based, negative indexing supported).
func (e *Engine) Goto(step int) interface{} {
	total := len(e.snapshots)
	if total == 0 {
		e.Status = "No history yet."
		return nil
	}
	if step < 0 {
		step = total + step + 1
	}
	if step < 1 || step > total {
		e.Status = fmt.Sprintf("Step %d out of range (1–%d).", step, total)
		return e.Current()
	}
	e.ptr = step - 1
	snap := e.snapshots[e.ptr]
	e.queryEngine(snap)
	e.Status = fmt.Sprintf("GOTO step %d [%v]", step, snap.Value)
	return snap.Value
}

// Current returns the value at the current history pointer.
func (e *Engine) Current() interface{} {
	if e.ptr < 0 {
		return nil
	}
	return e.snapshots[e.ptr].Value
}

// Step returns the current step number (1-based).
func (e *Engine) Step() int { return e.ptr + 1 }

// TotalSteps returns the total number of committed steps.
func (e *Engine) TotalSteps() int { return len(e.snapshots) }

// PrintHistory pretty-prints the full timeline.
func (e *Engine) PrintHistory() {
	fmt.Printf("\n  %-6s %-20s %-35s\n", "STEP", "LABEL", "VALUE")
	fmt.Printf("  %-6s %-20s %-35s\n", "----", "--------------------", "---")
	for i, s := range e.snapshots {
		marker := ""
		if i == e.ptr {
			marker = "  ◄ YOU ARE HERE"
		}
		fmt.Printf("  %-6d %-20s %-35v%s\n", i+1, s.Label, s.Value, marker)
	}
	fmt.Println()
}

// Close shuts down the engine and frees resources.
func (e *Engine) Close() {
	if e.handle != nil {
		C.uur_destroy_engine(e.handle)
		e.handle = nil
	}
}
