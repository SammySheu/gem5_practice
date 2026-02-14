#!/usr/bin/env python3
"""
Analyze gem5 DAXPY TLP experiment results and generate tables + plots.

Usage:
    python3 configs/practice/Assignment6/analyze_results.py
    python3 configs/practice/Assignment6/analyze_results.py --csv results_100k.csv --results-dir results_100k
    python3 configs/practice/Assignment6/analyze_results.py --csv results_1M.csv --results-dir results_1M
"""

import argparse
import csv
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

parser = argparse.ArgumentParser(description="Analyze gem5 DAXPY TLP experiment results")
parser.add_argument("--csv", default=os.path.join(SCRIPT_DIR, "results.csv"),
                    help="Path to results CSV file (default: %(default)s)")
parser.add_argument("--results-dir", default=os.path.join(SCRIPT_DIR, "results"),
                    help="Path to results directory with per-run stats (default: %(default)s)")
args = parser.parse_args()

CSV_FILE = args.csv
RESULTS_DIR = args.results_dir

# Derive plot directory from results-dir name (e.g. results_100k -> plots_100k)
results_basename = os.path.basename(RESULTS_DIR)
if results_basename.startswith("results"):
    plot_basename = "plots" + results_basename[len("results"):]
else:
    plot_basename = "plots"
PLOT_DIR = os.path.join(os.path.dirname(RESULTS_DIR), plot_basename)

print(f"CSV file:    {CSV_FILE}")
print(f"Results dir: {RESULTS_DIR}")
print(f"Plot dir:    {PLOT_DIR}")
print()

# ── Read CSV ──────────────────────────────────────────────────────────────
rows = []
with open(CSV_FILE) as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append({
            "opLat": int(r["opLat"]),
            "issueLat": int(r["issueLat"]),
            "threads": int(r["num_threads"]),
            "simTicks": int(r["simTicks"]),
            "simOps": int(r["simOps"]),
            "numCycles": int(r["numCycles"]),
            "cpi": float(r["cpi"]),
            "ipc": float(r["ipc"]),
        })

# ── Build lookup: (opLat, threads) → row ─────────────────────────────────
lookup = {(r["opLat"], r["threads"]): r for r in rows}

OP_LATS = [1, 2, 3, 4, 5, 6]
ISSUE_LATS = [6, 5, 4, 3, 2, 1]
THREADS = [1, 2, 4, 8]

# ── Per-CPU stats extraction from stats.txt ───────────────────────────────
def extract_per_cpu_stats(stats_path, num_cpus):
    """Extract per-CPU numCycles, committedOps, IPC, CPI from stats.txt."""
    per_cpu = {}
    with open(stats_path) as f:
        content = f.read()
    for line in content.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, val = parts[0], parts[1]
        # Single CPU uses "system.cpu.", multi uses "system.cpuN."
        for i in range(num_cpus):
            prefix = "system.cpu." if num_cpus == 1 else f"system.cpu{i}."
            cpu_key = 0 if num_cpus == 1 else i
            if cpu_key not in per_cpu:
                per_cpu[cpu_key] = {}
            if name == f"{prefix}numCycles":
                per_cpu[cpu_key]["numCycles"] = int(val)
            elif name == f"{prefix}commitStats0.numOps":
                per_cpu[cpu_key]["committedOps"] = int(val)
            elif name == f"{prefix}commitStats0.numInsts":
                per_cpu[cpu_key]["committedInsts"] = int(val)
            elif name == f"{prefix}commitStats0.ipc":
                per_cpu[cpu_key]["ipc"] = float(val)
            elif name == f"{prefix}commitStats0.cpi":
                per_cpu[cpu_key]["cpi"] = float(val)
    return per_cpu


# ══════════════════════════════════════════════════════════════════════════
# TABLE 1: Simulation Time (simTicks) across all configurations
# ══════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("TABLE 1: Simulation Time (simTicks) — lower is better")
print("=" * 78)
header = f"{'opLat/issueLat':>14s}"
for t in THREADS:
    header += f"  {'T=' + str(t):>12s}"
print(header)
print("-" * 78)
for op, iss in zip(OP_LATS, ISSUE_LATS):
    line = f"{op}/{iss}:>14s"
    line = f"{'%d/%d' % (op, iss):>14s}"
    for t in THREADS:
        r = lookup[(op, t)]
        line += f"  {r['simTicks']:>12,d}"
    print(line)
print()

# ══════════════════════════════════════════════════════════════════════════
# TABLE 2: Parallel Speedup  (simTicks_1thread / simTicks_Nthreads)
# ══════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("TABLE 2: Parallel Speedup (relative to single-thread, same FU config)")
print("=" * 78)
header = f"{'opLat/issueLat':>14s}"
for t in THREADS:
    header += f"  {'T=' + str(t):>10s}"
print(header)
print("-" * 78)
speedups = {}
for op, iss in zip(OP_LATS, ISSUE_LATS):
    base = lookup[(op, 1)]["simTicks"]
    line = f"{'%d/%d' % (op, iss):>14s}"
    for t in THREADS:
        s = base / lookup[(op, t)]["simTicks"]
        speedups[(op, t)] = s
        line += f"  {s:>10.4f}"
    print(line)
print()

# ══════════════════════════════════════════════════════════════════════════
# TABLE 3: Parallel Efficiency  (Speedup / N)
# ══════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("TABLE 3: Parallel Efficiency (Speedup / NumThreads)")
print("=" * 78)
header = f"{'opLat/issueLat':>14s}"
for t in THREADS:
    header += f"  {'T=' + str(t):>10s}"
print(header)
print("-" * 78)
for op, iss in zip(OP_LATS, ISSUE_LATS):
    line = f"{'%d/%d' % (op, iss):>14s}"
    for t in THREADS:
        eff = speedups[(op, t)] / t
        line += f"  {eff:>10.4f}"
    print(line)
print()

# ══════════════════════════════════════════════════════════════════════════
# TABLE 4: IPC (aggregate: simOps / sum_numCycles)
# ══════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("TABLE 4: Aggregate IPC (simOps / total numCycles across all CPUs)")
print("=" * 78)
header = f"{'opLat/issueLat':>14s}"
for t in THREADS:
    header += f"  {'T=' + str(t):>10s}"
print(header)
print("-" * 78)
for op, iss in zip(OP_LATS, ISSUE_LATS):
    line = f"{'%d/%d' % (op, iss):>14s}"
    for t in THREADS:
        r = lookup[(op, t)]
        line += f"  {r['ipc']:>10.4f}"
    print(line)
print()

# ══════════════════════════════════════════════════════════════════════════
# TABLE 5: CPI (aggregate)
# ══════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("TABLE 5: Aggregate CPI (total numCycles / simOps)")
print("=" * 78)
header = f"{'opLat/issueLat':>14s}"
for t in THREADS:
    header += f"  {'T=' + str(t):>10s}"
print(header)
print("-" * 78)
for op, iss in zip(OP_LATS, ISSUE_LATS):
    line = f"{'%d/%d' % (op, iss):>14s}"
    for t in THREADS:
        r = lookup[(op, t)]
        line += f"  {r['cpi']:>10.4f}"
    print(line)
print()

# ══════════════════════════════════════════════════════════════════════════
# TABLE 6: Per-CPU IPC for selected configurations
# ══════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("TABLE 6: Per-CPU IPC for opLat=4/issueLat=3 (best single-thread config)")
print("=" * 78)
for t in THREADS:
    run_name = f"oplat4_isslat3_threads{t}"
    stats_path = os.path.join(RESULTS_DIR, run_name, "stats.txt")
    if not os.path.exists(stats_path):
        continue
    per_cpu = extract_per_cpu_stats(stats_path, t)
    print(f"\n  Threads = {t}:")
    print(f"  {'CPU':>6s}  {'Cycles':>10s}  {'CommitOps':>10s}  {'IPC':>8s}  {'CPI':>8s}")
    for cpu_id in sorted(per_cpu.keys()):
        v = per_cpu[cpu_id]
        cyc = v.get("numCycles", 0)
        ops = v.get("committedOps", 0)
        ipc = v.get("ipc", 0)
        cpi = v.get("cpi", 0)
        label = "cpu" if t == 1 else f"cpu{cpu_id}"
        print(f"  {label:>6s}  {cyc:>10,d}  {ops:>10,d}  {ipc:>8.4f}  {cpi:>8.4f}")
print()

# ══════════════════════════════════════════════════════════════════════════
# TABLE 7: Best FU config ranking by simTicks for each thread count
# ══════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("TABLE 7: FU Configuration Ranking by Simulation Time (per thread count)")
print("=" * 78)
for t in THREADS:
    configs = [(op, iss, lookup[(op, t)]["simTicks"])
               for op, iss in zip(OP_LATS, ISSUE_LATS)]
    configs.sort(key=lambda x: x[2])
    print(f"\n  Threads = {t}:")
    print(f"  {'Rank':>4s}  {'opLat/issueLat':>14s}  {'simTicks':>14s}  {'vs Best':>10s}")
    best_ticks = configs[0][2]
    for rank, (op, iss, ticks) in enumerate(configs, 1):
        pct = (ticks - best_ticks) / best_ticks * 100
        print(f"  {rank:>4d}  {'%d/%d' % (op, iss):>14s}  {ticks:>14,d}  {'+%.2f%%' % pct:>10s}")
print()

# ══════════════════════════════════════════════════════════════════════════
# TABLE 8: FloatSimdFU instruction breakdown (from issuedInstType)
# ══════════════════════════════════════════════════════════════════════════
print("=" * 78)
print("TABLE 8: Float/SIMD Instruction Mix (single-thread, opLat=4/issueLat=3)")
print("=" * 78)
stats_path = os.path.join(RESULTS_DIR, "oplat4_isslat3_threads1", "stats.txt")
if os.path.exists(stats_path):
    with open(stats_path) as f:
        content = f.read()
    float_stats = {}
    total_issued = 0
    for line in content.splitlines():
        parts = line.split()
        if len(parts) >= 2 and "issuedInstType_0::" in parts[0]:
            itype = parts[0].split("::")[-1]
            count = int(parts[1])
            if count > 0:
                if itype in ("FloatCmp", "FloatCvt", "FloatMultAcc", "FloatMult",
                             "FloatAdd", "FloatDiv", "FloatSqrt", "FloatMisc",
                             "SimdAdd", "SimdAlu", "SimdCmp", "SimdMisc",
                             "SimdMult", "SimdShift", "SimdFloatAdd",
                             "SimdFloatCmp", "SimdFloatMult", "SimdFloatDiv"):
                    float_stats[itype] = count
                if itype == "total":
                    total_issued = count
    print(f"  {'Instruction Type':>20s}  {'Count':>8s}  {'% of Total':>10s}")
    print(f"  {'-'*20}  {'-'*8}  {'-'*10}")
    float_total = 0
    for itype, count in sorted(float_stats.items(), key=lambda x: -x[1]):
        pct = count / total_issued * 100 if total_issued else 0
        print(f"  {itype:>20s}  {count:>8,d}  {pct:>9.2f}%")
        float_total += count
    print(f"  {'─'*20}  {'─'*8}  {'─'*10}")
    pct = float_total / total_issued * 100 if total_issued else 0
    print(f"  {'Float/SIMD Total':>20s}  {float_total:>8,d}  {pct:>9.2f}%")
    print(f"  {'All Issued (total)':>20s}  {total_issued:>8,d}  {'100.00%':>10s}")
print()

# ══════════════════════════════════════════════════════════════════════════
# Generate plots (if matplotlib available)
# ══════════════════════════════════════════════════════════════════════════
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    os.makedirs(PLOT_DIR, exist_ok=True)
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(OP_LATS)))

    # ── Plot 1: Simulation Time vs Threads ────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    for idx, (op, iss) in enumerate(zip(OP_LATS, ISSUE_LATS)):
        ticks = [lookup[(op, t)]["simTicks"] / 1e6 for t in THREADS]
        ax.plot(THREADS, ticks, "o-", color=colors[idx],
                label=f"opLat={op}, issueLat={iss}")
    ax.set_xlabel("Number of Threads")
    ax.set_ylabel("Simulation Time (million ticks)")
    ax.set_title("Simulation Time vs. Thread Count")
    ax.set_xticks(THREADS)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "sim_time_vs_threads.png"), dpi=150)
    plt.close(fig)

    # ── Plot 2: Speedup vs Threads ────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(THREADS, THREADS, "k--", alpha=0.3, label="Ideal (linear)")
    for idx, (op, iss) in enumerate(zip(OP_LATS, ISSUE_LATS)):
        su = [speedups[(op, t)] for t in THREADS]
        ax.plot(THREADS, su, "o-", color=colors[idx],
                label=f"opLat={op}, issueLat={iss}")
    ax.set_xlabel("Number of Threads")
    ax.set_ylabel("Speedup")
    ax.set_title("Parallel Speedup vs. Thread Count")
    ax.set_xticks(THREADS)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "speedup_vs_threads.png"), dpi=150)
    plt.close(fig)

    # ── Plot 3: Simulation Time vs opLat (grouped by threads) ─────────
    fig, ax = plt.subplots(figsize=(8, 5))
    thread_colors = {1: "tab:blue", 2: "tab:orange", 4: "tab:green", 8: "tab:red"}
    for t in THREADS:
        ticks = [lookup[(op, t)]["simTicks"] / 1e6 for op in OP_LATS]
        ax.plot(OP_LATS, ticks, "o-", color=thread_colors[t],
                label=f"{t} thread(s)")
    ax.set_xlabel("opLat (issueLat = 7 − opLat)")
    ax.set_ylabel("Simulation Time (million ticks)")
    ax.set_title("Effect of opLat on Simulation Time")
    ax.set_xticks(OP_LATS)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "sim_time_vs_oplat.png"), dpi=150)
    plt.close(fig)

    # ── Plot 4: Aggregate IPC vs Threads ──────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    for idx, (op, iss) in enumerate(zip(OP_LATS, ISSUE_LATS)):
        ipcs = [lookup[(op, t)]["ipc"] for t in THREADS]
        ax.plot(THREADS, ipcs, "o-", color=colors[idx],
                label=f"opLat={op}, issueLat={iss}")
    ax.set_xlabel("Number of Threads")
    ax.set_ylabel("Aggregate IPC")
    ax.set_title("Aggregate IPC vs. Thread Count")
    ax.set_xticks(THREADS)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "ipc_vs_threads.png"), dpi=150)
    plt.close(fig)

    # ── Plot 5: Bar chart — best config comparison ────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(THREADS))
    width = 0.12
    for idx, (op, iss) in enumerate(zip(OP_LATS, ISSUE_LATS)):
        ticks = [lookup[(op, t)]["simTicks"] / 1e6 for t in THREADS]
        ax.bar(x + idx * width, ticks, width, color=colors[idx],
               label=f"{op}/{iss}")
    ax.set_xlabel("Number of Threads")
    ax.set_ylabel("Simulation Time (million ticks)")
    ax.set_title("Simulation Time by FU Config and Thread Count")
    ax.set_xticks(x + width * 2.5)
    ax.set_xticklabels([str(t) for t in THREADS])
    ax.legend(title="opLat/issueLat", fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, "bar_sim_time.png"), dpi=150)
    plt.close(fig)

    print(f"Plots saved to {PLOT_DIR}/")

except ImportError:
    print("matplotlib not available — skipping plot generation.")
    print("Install with: pip install matplotlib")

print("\nAnalysis complete.")
