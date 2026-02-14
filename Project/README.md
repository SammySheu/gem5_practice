# Project - Edge Pre-processing Microprocessor with DVFS

Simulates an edge computing sensor pipeline on ARM, with explicit power modeling and DVFS (Dynamic Voltage and Frequency Scaling) optimization.

## Workload

The workload (`workloads/edge_preprocessing.c`) models a multi-sensor edge node that:
1. Generates data from 16 sensors × 1024 samples
2. Applies a moving-average filter (compute-intensive)
3. Performs anomaly detection, cross-sensor fusion, and normalization
4. Runs 3 rounds of the full pipeline

Two binaries are used:
- `edge_preprocessing_arm` — plain binary for static DVFS experiments
- `edge_preprocessing_dvfs_arm` — instrumented with `m5_work_begin()` pseudo-instructions at each phase boundary, enabling dynamic DVFS switching

## Building the Workload Binaries

```bash
# Static binary (used by run_all.sh)
aarch64-linux-gnu-gcc -static -O2 -o configs/practice/Project/workloads/edge_preprocessing_arm \
    configs/practice/Project/workloads/edge_preprocessing.c -lm

# DVFS-instrumented binary (used by run_dvfs_dynamic.sh)
aarch64-linux-gnu-gcc -static -O2 \
    -I/home/sammy/gem5/include \
    -o configs/practice/Project/workloads/edge_preprocessing_dvfs_arm \
    configs/practice/Project/workloads/edge_preprocessing_dvfs.c -lm
```

## Experiment 1: Static DVFS Sweep (12 configurations)

Runs all combinations of CPU type × cache hierarchy × DVFS level.

**Architecture configurations:**
| CPU | Cache | Output prefix |
|-----|-------|---------------|
| MinorCPU (in-order) | L1 only | `m5out_minor_l1` |
| MinorCPU (in-order) | L1 + L2 | `m5out_minor_l2` |
| O3CPU (out-of-order) | L1 only | `m5out_o3_l1` |
| O3CPU (out-of-order) | L1 + L2 | `m5out_o3_l2` |

**DVFS operating points:**
| Level | Frequency | Voltage | Label |
|-------|-----------|---------|-------|
| P0 | 2 GHz | 1.2 V | High Performance |
| P1 | 1.2 GHz | 1.0 V | Balanced |
| P2 | 600 MHz | 0.8 V | Low Power |

```bash
cd /home/sammy/gem5/configs/practice/Project
./run_all.sh
```

Results are written to `m5out_<arch>_perf<N>/`. Run a single configuration manually:

```bash
# Example: O3CPU with L2 cache at balanced DVFS
../../../build/ARM/gem5.opt --outdir=m5out_o3_l2_perf1 edge_power_config.py \
    --cpu-type=o3 --binary=workloads/edge_preprocessing_arm \
    --l2-cache --perf-level=1
```

Analyze all 12 results:

```bash
python3 analyze_results.py
```

## Experiment 2: Dynamic Phase-Aware DVFS (8 configurations)

Compares running at a fixed P0 (2 GHz/1.2 V) against a phase-aware policy that switches V/f at each pipeline phase boundary.

**Dynamic DVFS policy:**
| Phase | Name | DVFS Level |
|-------|------|------------|
| 0 | Generate Data | P1 Balanced |
| 1 | Moving Avg Filter | P0 High-Perf |
| 2 | Anomaly Detection | P2 Low-Power |
| 3 | Cross-Sensor Fusion | P2 Low-Power |
| 4 | Aggregate Stats | P2 Low-Power |
| 5 | Normalize Data | P2 Low-Power |
| 6 | Per-Sensor Stats | P1 Balanced |

Hypothesis: only the filter phase needs full speed; all other phases are memory-bound or lightweight enough to run at reduced V/f.

```bash
cd /home/sammy/gem5/configs/practice/Project
./run_dvfs_dynamic.sh
```

Results are written to `m5out_<arch>_static_p0/` and `m5out_<arch>_dynamic/`. Run a single pair manually:

```bash
# Static P0 baseline
../../../build/ARM/gem5.opt --outdir=m5out_minorcpu_l1_static_p0 edge_power_config.py \
    --cpu-type=minor --binary=workloads/edge_preprocessing_arm --perf-level=0

# Dynamic DVFS
../../../build/ARM/gem5.opt --outdir=m5out_minorcpu_l1_dynamic edge_power_dvfs_dynamic.py \
    --cpu-type=minor --binary=workloads/edge_preprocessing_dvfs_arm
```

Analyze the static vs dynamic comparison:

```bash
python3 analyze_dvfs_dynamic.py
```

## Key Design Decisions

| Aspect | Static config (`edge_power_config.py`) | Dynamic config (`edge_power_dvfs_dynamic.py`) |
|--------|----------------------------------------|-----------------------------------------------|
| DVFS control | Fixed `--perf-level` at startup | Per-phase switching via `DVFSHandler` |
| Binary | `edge_preprocessing_arm` (plain) | `edge_preprocessing_dvfs_arm` (instrumented) |
| Phase detection | N/A | `m5_work_begin()` triggers `workbegin` exit events |
| Stats | Periodic dumps (every 1 ms sim-time) | Periodic dumps across all phases |
| Power model | `MathExprPowerModel` on CPU + caches | Same power model |

## Cache Hierarchy

| Cache | Size | Associativity | Latency |
|-------|------|---------------|---------|
| L1 I-cache | 16 KB | 2-way | 1 cycle |
| L1 D-cache | 32 KB | 4-way | 2 cycles |
| L2 (optional) | 256 KB | 8-way | 12 cycles |
| DRAM | 4 GB (DDR4-2400) | — | — |

