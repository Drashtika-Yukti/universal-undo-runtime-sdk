// test_uur.go — Go binding test suite
// =====================================
// Location: bindings/go/test_uur.go
//
// Build & run:
//   set CC=x86_64-w64-mingw32-gcc
//   set CGO_ENABLED=1
//   go run test_uur.go uur.go

package main

import (
	"fmt"
	"os"
	"reflect"
)

// ── test helpers ─────────────────────────────────────────────────────────────

var passed, failed int

func check(label string, got, expected interface{}) {
	ok := reflect.DeepEqual(got, expected)
	if ok {
		fmt.Printf("  ✓  %s\n", label)
		passed++
	} else {
		fmt.Printf("  ✗  %s\n", label)
		fmt.Printf("       got:      %v\n", got)
		fmt.Printf("       expected: %v\n", expected)
		failed++
	}
}

func section(title string) {
	fmt.Printf("\n[ %s ]\n", title)
}

// ── tests ─────────────────────────────────────────────────────────────────────

func main() {
	fmt.Println()
	fmt.Println("============================================================")
	fmt.Println("  Universal Undo Runtime — Go Binding Test Suite")
	fmt.Println("============================================================")

	// [ 1 ] Basic commit
	section("1 Basic commit")
	{
		e := NewEngine()
		e.Commit("text", "Hello")
		e.Commit("text", "Hello World")
		e.Commit("text", "Hello World!")
		check("step count is 3", e.TotalSteps(), 3)
		check("current is last", e.Current(), "Hello World!")
		check("step number is 3", e.Step(), 3)
		e.Close()
	}

	// [ 2 ] Undo
	section("2 Undo")
	{
		e := NewEngine()
		e.Commit("text", "A")
		e.Commit("text", "AB")
		e.Commit("text", "ABC")
		check("undo once → AB", e.Undo(), "AB")
		check("step is 2", e.Step(), 2)
		check("undo twice → A", e.Undo(), "A")
		check("step is 1", e.Step(), 1)
		check("undo past start → A", e.Undo(), "A")
		check("step stays at 1", e.Step(), 1)
		e.Close()
	}

	// [ 3 ] Redo
	section("3 Redo")
	{
		e := NewEngine()
		e.Commit("text", "X")
		e.Commit("text", "XY")
		e.Commit("text", "XYZ")
		e.Undo()
		e.Undo()
		check("redo once → XY", e.Redo(), "XY")
		check("redo twice → XYZ", e.Redo(), "XYZ")
		check("redo past end → XYZ", e.Redo(), "XYZ")
		e.Close()
	}

	// [ 4 ] Goto
	section("4 Goto — jump directly to any step")
	{
		e := NewEngine()
		vals := []int{10, 20, 30, 40, 50, 60}
		for _, v := range vals {
			e.Commit("score", v)
		}
		check("goto(1) → 10", e.Goto(1), 10)
		check("goto(6) → 60", e.Goto(6), 60)
		check("goto(3) → 30", e.Goto(3), 30)
		check("goto(-1) → 60", e.Goto(-1), 60)
		check("goto(99) stays at 60", e.Goto(99), 60)
		e.Close()
	}

	// [ 5 ] Branch discard
	section("5 Branch discard")
	{
		e := NewEngine()
		e.Commit("text", "one")
		e.Commit("text", "two")
		e.Commit("text", "three")
		e.Undo()
		e.Commit("text", "NEW")
		check("total steps is 3", e.TotalSteps(), 3)
		check("current is NEW", e.Current(), "NEW")
		check("redo does nothing", e.Redo(), "NEW")
		e.Close()
	}

	// [ 6 ] Multiple types
	section("6 Works with multiple Go types")
	{
		e := NewEngine()
		e.Commit("number", 42)
		e.Commit("float", 3.14)
		e.Commit("string", "hello")
		e.Commit("bool", true)
		check("current is true", e.Current(), true)
		e.Undo()
		check("undo → hello", e.Current(), "hello")
		e.Goto(1)
		check("goto(1) → 42", e.Current(), 42)
		e.Close()
	}

	// [ 7 ] PrintHistory
	section("7 PrintHistory output")
	{
		e := NewEngine()
		e.Commit("file", "doc.txt")
		e.Commit("file", "report.pdf")
		e.Commit("file", "final.docx")
		e.Goto(2)
		e.PrintHistory()
		e.Close()
	}

	// Summary
	total := passed + failed
	fmt.Println("============================================================")
	fmt.Printf("  %d/%d checks passed\n", passed, total)
	if failed == 0 {
		fmt.Println("  ALL TESTS PASSED  ✓")
	} else {
		fmt.Printf("  %d FAILED  ✗\n", failed)
	}
	fmt.Println("============================================================")
	fmt.Println()

	if failed > 0 {
		os.Exit(1)
	}
}
