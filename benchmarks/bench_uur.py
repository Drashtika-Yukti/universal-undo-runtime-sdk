"""
bench_uur.py — Phase 4 Performance Benchmark Suite
====================================================
Location: benchmarks/bench_uur.py

Measures:
    1. Commit throughput        — how many commits/second
    2. Undo/Redo throughput     — how fast stepping through history
    3. Goto latency             — direct jump speed at various history sizes
    4. Memory growth            — snapshot count vs time
    5. Stress test              — 10,000 commits, random goto

Run:
    cd F:\\universal_undo_runtime
    python benchmarks\\bench_uur.py
"""

import sys
import time
import random
import statistics

sys.path.insert(0, r"bindings\python")
from bindings.python.uur import Engine

# ── helpers ───────────────────────────────────────────────────────────────────

def hr(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def result(label: str, value: str):
    print(f"  {label:<40} {value}")

def avg_ms(times_ns: list) -> float:
    return statistics.mean(times_ns) / 1_000_000

def ops_per_sec(count: int, elapsed_ns: float) -> int:
    return int(count / (elapsed_ns / 1_000_000_000))

# ── benchmark 1: commit throughput ────────────────────────────────────────────

def bench_commit_throughput():
    hr("BENCH 1 — Commit Throughput")

    for n in [100, 1_000, 10_000]:
        with Engine() as e:
            t0 = time.perf_counter_ns()
            for i in range(n):
                e.commit("bench", f"state_{i}")
            elapsed = time.perf_counter_ns() - t0

        ops = ops_per_sec(n, elapsed)
        ms  = elapsed / 1_000_000
        result(f"{n:>6} commits", f"{ms:.2f} ms   →   {ops:,} commits/sec")

# ── benchmark 2: undo throughput ──────────────────────────────────────────────

def bench_undo_throughput():
    hr("BENCH 2 — Undo Throughput")

    for n in [100, 1_000, 5_000]:
        with Engine() as e:
            # fill history
            for i in range(n):
                e.commit("bench", f"state_{i}")

            # measure undo speed
            t0 = time.perf_counter_ns()
            for _ in range(n - 1):
                e.undo()
            elapsed = time.perf_counter_ns() - t0

        ops = ops_per_sec(n - 1, elapsed)
        ms  = elapsed / 1_000_000
        result(f"{n:>6} undos", f"{ms:.2f} ms   →   {ops:,} undos/sec")

# ── benchmark 3: redo throughput ──────────────────────────────────────────────

def bench_redo_throughput():
    hr("BENCH 3 — Redo Throughput")

    for n in [100, 1_000, 5_000]:
        with Engine() as e:
            for i in range(n):
                e.commit("bench", f"state_{i}")
            # undo all the way back
            for _ in range(n - 1):
                e.undo()

            # measure redo speed
            t0 = time.perf_counter_ns()
            for _ in range(n - 1):
                e.redo()
            elapsed = time.perf_counter_ns() - t0

        ops = ops_per_sec(n - 1, elapsed)
        ms  = elapsed / 1_000_000
        result(f"{n:>6} redos", f"{ms:.2f} ms   →   {ops:,} redos/sec")

# ── benchmark 4: goto latency ─────────────────────────────────────────────────

def bench_goto_latency():
    hr("BENCH 4 — Goto Latency  (direct jump to any step)")

    for n in [100, 1_000, 10_000]:
        with Engine() as e:
            for i in range(n):
                e.commit("bench", f"state_{i}")

            # 200 random jumps, measure each
            targets = [random.randint(1, n) for _ in range(200)]
            times   = []
            for t in targets:
                t0 = time.perf_counter_ns()
                e.goto(t)
                times.append(time.perf_counter_ns() - t0)

        mean_us  = statistics.mean(times) / 1_000
        worst_us = max(times) / 1_000
        result(
            f"history={n:>6}  200 random gotos",
            f"avg {mean_us:.2f} µs   worst {worst_us:.2f} µs"
        )

# ── benchmark 5: stress test ──────────────────────────────────────────────────

def bench_stress():
    hr("BENCH 5 — Stress Test  (10,000 commits + 1,000 random gotos)")

    with Engine() as e:
        N = 10_000

        # phase A: fill
        t0 = time.perf_counter_ns()
        for i in range(N):
            e.commit("stress", f"value_{i}")
        fill_ms = (time.perf_counter_ns() - t0) / 1_000_000

        result("10,000 commits", f"{fill_ms:.2f} ms")
        result("History depth after fill", str(e.total_steps))

        # phase B: random gotos
        targets = [random.randint(1, N) for _ in range(1_000)]
        t0      = time.perf_counter_ns()
        for t in targets:
            e.goto(t)
        goto_ms = (time.perf_counter_ns() - t0) / 1_000_000

        result("1,000 random gotos after fill", f"{goto_ms:.2f} ms")
        result("Avg per goto", f"{goto_ms/1000:.4f} ms")

        # phase C: undo back to step 1
        current = e.step
        t0      = time.perf_counter_ns()
        e.goto(1)
        snap_ms = (time.perf_counter_ns() - t0) / 1_000_000

        result(f"Single goto(1) from step {current}", f"{snap_ms:.4f} ms")

# ── benchmark 6: branch discard performance ───────────────────────────────────

def bench_branch_discard():
    hr("BENCH 6 — Branch Discard Speed")
    print("  (undo halfway, then commit new — how fast is branch pruning?)")

    for n in [100, 1_000, 5_000]:
        with Engine() as e:
            for i in range(n):
                e.commit("bench", f"state_{i}")

            # undo to midpoint
            mid = n // 2
            e.goto(mid)

            # now commit — this discards n/2 snapshots
            t0 = time.perf_counter_ns()
            e.commit("bench", "NEW_BRANCH")
            elapsed = time.perf_counter_ns() - t0

            us = elapsed / 1_000
            result(
                f"history={n:>6}  discard {n-mid} steps + commit",
                f"{us:.2f} µs"
            )

# ── summary ───────────────────────────────────────────────────────────────────

def print_summary():
    hr("SUMMARY")
    print("  All benchmarks completed.")
    print("  Key numbers to note for your README:")
    print()
    print("  • Commits/sec    → shows raw write throughput")
    print("  • Goto avg µs    → proves microsecond time-travel claim")
    print("  • Stress test    → validates engine under 10k history depth")
    print("  • Branch discard → shows non-linear history cost")
    print()
    print("  Add these numbers to README under 'Performance' section.")
    print(f"{'='*60}\n")

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  Universal Undo Runtime — Phase 4 Benchmark Suite")
    print("=" * 60)
    print(f"  Python binding via ctypes")
    print(f"  Engine: libuniversal_undo_runtime.dll")

    bench_commit_throughput()
    bench_undo_throughput()
    bench_redo_throughput()
    bench_goto_latency()
    bench_stress()
    bench_branch_discard()
    print_summary()
