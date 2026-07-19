"""
test_phase3.py — Phase 3 milestone tagging test suite
=======================================================
Location: bindings/python/test_phase3.py

Run:
    cd F:\\universal_undo_runtime
    python bindings\\python\\test_phase3.py
"""

import sys
sys.path.insert(0, r"bindings\python")
from uur import Engine

passed = 0
failed = 0

def check(label, got, expected):
    global passed, failed
    ok = got == expected
    print(f"  {'✓' if ok else '✗'}  {label}")
    if not ok:
        print(f"       got:      {repr(got)}")
        print(f"       expected: {repr(expected)}")
    if ok: passed += 1
    else:  failed += 1

def check_not_none(label, got):
    global passed, failed
    ok = got is not None
    print(f"  {'✓' if ok else '✗'}  {label}")
    if not ok:
        print(f"       got: None")
    if ok: passed += 1
    else:  failed += 1

print()
print("=" * 60)
print("  Universal Undo Runtime — Phase 3 Milestone Tag Tests")
print("=" * 60)

# [ 1 ] Untagged commit — get_tag returns None
print("\n[ 1 ] Untagged commit produces no tag")
with Engine() as e:
    e.commit("text", "Hello")
    check("get_tag() is None for untagged step", e.get_tag(1), None)

# [ 2 ] Tagged commit — tag is retrievable
print("\n[ 2 ] Tagged commit stores milestone")
with Engine() as e:
    e.commit("func",    "def hello():",  tag="function:hello created")
    e.commit("func",    "def world():",  tag="function:world created")
    e.commit("package", "import numpy",  tag="package:numpy added")
    e.commit("func",    "def bye():")    # no tag

    check("step 1 tag correct",  e.get_tag(1), "function:hello created")
    check("step 2 tag correct",  e.get_tag(2), "function:world created")
    check("step 3 tag correct",  e.get_tag(3), "package:numpy added")
    check("step 4 tag is None",  e.get_tag(4), None)

# [ 3 ] goto_tag — jump by label
print("\n[ 3 ] goto_tag jumps directly to named milestone")
with Engine() as e:
    e.commit("code", "line 1")
    e.commit("code", "line 2",  tag="function:parse created")
    e.commit("code", "line 3")
    e.commit("code", "line 4",  tag="class:Handler added")
    e.commit("code", "line 5")

    val = e.goto_tag("function:parse created")
    check("goto_tag returns correct value",  val,    "line 2")
    check("step pointer is now 2",           e.step, 2)

    val = e.goto_tag("class:Handler added")
    check("goto_tag jumps to step 4",        val,    "line 4")
    check("step pointer is now 4",           e.step, 4)

    val = e.goto_tag("nonexistent tag")
    check("unknown tag returns None",        val,    None)
    check("step pointer unchanged after miss", e.step, 4)

# [ 4 ] tag + undo/redo still works
print("\n[ 4 ] Tags survive undo/redo")
with Engine() as e:
    e.commit("v", 1)
    e.commit("v", 2, tag="milestone:v2")
    e.commit("v", 3)

    e.undo()
    check("after undo, tag still readable",   e.get_tag(2), "milestone:v2")
    e.redo()
    check("after redo, tag still readable",   e.get_tag(2), "milestone:v2")

# [ 5 ] tag + goto by step still works
print("\n[ 5 ] goto(step) still works alongside tags")
with Engine() as e:
    e.commit("x", 10)
    e.commit("x", 20, tag="checkpoint:A")
    e.commit("x", 30)

    e.goto(1)
    check("goto(1) still works",   e.current, 10)
    e.goto(2)
    check("goto(2) still works",   e.current, 20)
    check("tag at step 2 intact",  e.get_tag(2), "checkpoint:A")

# [ 6 ] print_history shows tags
print("\n[ 6 ] print_history() shows TAG column")
with Engine() as e:
    e.commit("file", "main.py")
    e.commit("file", "utils.py",  tag="file:utils created")
    e.commit("file", "tests.py",  tag="file:tests added")
    e.goto(2)
    e.print_history()

# Summary
print("=" * 60)
total = passed + failed
print(f"  {passed}/{total} checks passed")
if failed == 0:
    print("  PHASE 3 TESTS: ALL PASSED  ✓")
else:
    print(f"  {failed} FAILED  ✗")
print("=" * 60)
print()

sys.exit(0 if failed == 0 else 1)
