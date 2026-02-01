# Assignment 4 - Instruction-Level Parallelism (ILP) Experiments

## Building and Running

Compile the benchmark program:
```bash
gcc -O2 -static configs/practice/Assignment4/benchmark.c -o configs/practice/Assignment4/benchmark
```

The benchmark is a simple loop with conditional branches designed to stress the branch predictor and ILP mechanisms.

Run a single experiment:
```bash
# Baseline 4-wide superscalar with branch prediction
./build/X86/gem5.opt configs/practice/Assignment4/my_o3_se.py \
  --cmd=configs/practice/Assignment4/benchmark

# Single-issue (scalar) pipeline
./build/X86/gem5.opt configs/practice/Assignment4/my_o3_se.py \
  --cmd=configs/practice/Assignment4/benchmark \
  --fetchWidth=1 --decodeWidth=1 --renameWidth=1 \
  --dispatchWidth=1 --issueWidth=1 --commitWidth=1

# 8-wide superscalar
./build/X86/gem5.opt configs/practice/Assignment4/my_o3_se.py \
  --cmd=configs/practice/Assignment4/benchmark \
  --fetchWidth=8 --decodeWidth=8 --renameWidth=8 \
  --dispatchWidth=8 --issueWidth=8 --commitWidth=8

# SMT with 2 threads
./build/X86/gem5.opt configs/practice/Assignment4/my_o3_se.py \
  --cmd=configs/practice/Assignment4/benchmark \
  --threads=2
```

Run all experiments in batch mode (results stored under [results](./results/)):
```bash
./configs/practice/Assignment4/run_experiments.sh
```

## Experiment Overview

This assignment explores Instruction-Level Parallelism (ILP) through systematic experiments on an out-of-order (O3) processor model. The experiments investigate how processor microarchitecture features affect performance on a branch-intensive workload.

### 1. Branch Prediction Impact

**Experiment**: Compare performance with and without branch prediction

- **Baseline**: Since we are using O3CPU, it has Tournament as its default perdictor. It is based on a 4-wide superscalar processor
- **No Branch Prediction**: Minimal predictor (1-entry, 1-bit counter) that simulates poor prediction


### 2. Superscalar Width Variations

**Experiment**: Vary the pipeline width to understand ILP extraction limits

Pipeline configurations tested:
- **Single-issue (1-wide)**: Classic scalar pipeline, processes 1 instruction per stage per cycle
- **Dual-issue (2-wide)**: Can fetch/decode/execute/commit up to 2 instructions per cycle
- **Quad-issue (4-wide)**: Baseline 4-wide superscalar (reference configuration)
- **Octa-issue (8-wide)**: Aggressive 8-wide superscalar

All width parameters are adjusted together:
- `fetchWidth`: Instructions fetched per cycle
- `decodeWidth`: Instructions decoded per cycle
- `renameWidth`: Instructions renamed per cycle (register renaming)
- `dispatchWidth`: Instructions dispatched to execution units per cycle
- `issueWidth`: Instructions issued to functional units per cycle
- `commitWidth`: Instructions committed (retired) per cycle

### 3. Simultaneous Multithreading (SMT)

**Experiment**: Evaluate SMT performance with multiple hardware threads sharing pipeline resources

Configurations tested:
- **SMT with 2 threads**: Two concurrent threads sharing the 4-wide pipeline
- **SMT with 4 threads**: Four concurrent threads sharing the 4-wide pipeline

Each thread runs an independent instance of the benchmark with unique process IDs. The O3 CPU dynamically schedules instructions from multiple threads to maximize throughput and resource utilization.


## Benchmark Characteristics

The benchmark (`benchmark.c`) is a simple but effective workload for ILP analysis:

```c
volatile int sum = 0;
for (int i = 0; i < 1000; i++) {
    if (i & 1) sum += i;  // branch + integer operation
    else       sum -= i;
}
```


## Configuration Details

The O3 CPU configuration (`my_o3_se.py`) includes:

**Processor**:
- X86 O3CPU (out-of-order superscalar)
- 1 GHz clock frequency
- Configurable pipeline widths (1, 2, 4, or 8-wide)
- Configurable number of hardware threads (1, 2, or 4)

**Cache Hierarchy**:
- L1 Instruction Cache: 32 KB, 2-way set-associative
- L1 Data Cache: 32 KB, 2-way set-associative
- No L2/L3 cache (to isolate CPU pipeline effects)

**Memory**:
- 512 MB DDR3-1600 DRAM
- System crossbar interconnect

**Branch Prediction**:
- Default: Tournament predictor (hybrid of local and global predictors)
- Alternative: Minimal 1-entry, 1-bit predictor (simulates no prediction)

## Results

All experiment results are stored in the [results](./results/) directory:

- **Baseline**: `baseline_stats.txt` - 4-wide with branch prediction (reference)
- **No Branch Prediction**: `no_bp_stats.txt` - Impact of poor branch prediction
- **Single-issue**: `single_issue_stats.txt` - Scalar pipeline performance
- **Dual-issue**: `dual_issue_stats.txt` - 2-wide superscalar
- **Quad-issue**: `quad_issue_stats.txt` - 4-wide superscalar (same as baseline)
- **Eight-issue**: `eight_issue_stats.txt` - 8-wide superscalar
- **SMT 2-threads**: `smt_2threads_stats.txt` - 2-way SMT
- **SMT 4-threads**: `smt_4threads_stats.txt` - 4-way SMT

## Troubleshooting

### Common Issues

**Problem**: SMT experiments show identical per-thread results
- **Solution**: gem5's SMT implementation shares resources dynamically. Identical workloads may see similar performance. Try different per-thread workloads for more realistic contention.

**Problem**: 8-wide doesn't show 2× speedup over 4-wide
- **Solution**: This is expected! ILP is limited by true data dependencies, branch mispredictions, and functional unit availability. The benchmark's dependency chains prevent perfect scaling.

**Problem**: "No branch prediction" mode still shows some correct predictions
- **Solution**: The minimal predictor (1-entry, 1-bit) can still learn simple patterns. It's not perfect prediction, but it's much worse than the default predictor. Check misprediction rates to see the difference.

