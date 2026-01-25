# Assignment 3 - Cache and Virtual Memory Optimization Experiments

## Building and Running

Compile the benchmark programs:
```bash
# Original simple benchmark
gcc configs/practice/Assignment3/hello_world.c -o configs/practice/Assignment3/hello_world

# New matrix benchmark (recommended for meaningful results)
gcc -O2 -static configs/practice/Assignment3/matrix_benchmark.c -o configs/practice/Assignment3/matrix_benchmark -lm
```
The added matrix_benchmark is a 128×128 matrix multiplication to stress cache hierarchy

optimization experiment:
```bash
./build/X86/gem5.opt configs/practice/Assignment3/cache_optimizations.py
# Run New Baseline for new matrix benchmark (to have meaningful results)
./build/X86/gem5.opt configs/practice/Assignment3/run_baseline_v2.py
```

Run a single virtual memory experiment:
```bash
./build/X86/gem5.opt configs/practice/Assignment3/virtual_memory.py
```

Run all cache optimization experiments (batch mode, data stored under [results_v2](./results_v2/)):
```bash
./configs/practice/Assignment3/run_cache_experiments.sh
# Run New Baseline for new matrix benchmark (to have meaningful results)
./configs/practice/Assignment3/run_cache_experiments_v2.sh
```

Run all virtual memory experiments (batch mode):
```bash
./configs/practice/Assignment3/run_vm_experiments.sh
```

## Experiment Overview

This assignment explores cache and virtual memory optimization through systematic parameter sweeps.

### Cache Optimization Experiments

The experiments test with different cache parameter combinations to analyze their impact on performance:

1. **Cache Sizes**: Adjust `L1 Data Cache (L1 D-Cache)`, `L1 Instruction Cache (L1 I-Cache)`, `L2 Cache` to see how cache capacity affects hit rates and miss penalties.

2. **Associativity**: Adjust associativity with `1 way (direct-mapped)`, `2 way`, `4 way`, and `8 ways` to study the trade-off between conflict misses and access latency.

3. **Block Sizes**: Adjust  block sizes of `16B`, `32B`, `64B`, and `128B` to understand the impact of spatial locality and transfer overhead.

Each experiment measures cache hit rates, miss counts, and performance metrics for L1 instruction cache, L1 data cache, and L2 cache.

### Virtual Memory Experiments

The virtual memory experiments investigate page size and TLB (Translation Lookaside Buffer) configurations:

1. **Page Sizes**: Tests page sizes of 4KB, 8KB, and 16KB to analyze the trade-off between page table size and TLB coverage.

2. **TLB Sizes**: Evaluates TLB sizes of 32, 64, and 128 entries to study the impact on TLB hit rates and translation overhead.

3. **TLB Associativity**: Examines TLB associativity levels of 2, 4, and 8 ways to understand conflict resolution in the TLB.

**Note**: In SE (Syscall Emulation) mode, TLB configuration is limited. TLBs use default gem5 parameters. For full TLB control, full-system (FS) mode is required.

## Results

All experiment results are stored in CSV format under [configs/practice/Assignment3/results_v2/](./results):

- **Cache experiments**: Individual result files (e.g., `baseline_result_v2.csv`) and a combined file [all_experiments.csv](./results_v2/all_experiments_v2.csv)
![Screenshot](./results_v2/Screenshot%202026-01-25%20at%208.24.34 AM.png)
- **Virtual memory experiments**: Individual result files (e.g., `page_4kB_vm_result.csv`, `tlb_64_vm_result.csv`) and a combined file `all_vm_experiments.csv`

Each result file contains metrics including hit rates, miss counts, and performance statistics for the tested configurations. For further analysis, please refer to [./results_v2/cache_analysis.md](./results_v2/cache_analysis.md)
