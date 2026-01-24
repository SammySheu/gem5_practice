# Assignment 3 - Cache and Virtual Memory Optimization Experiments

## Building and Running

Compile the hello_world program:
```bash
gcc configs/practice/Assignment3/hello_world.c -o configs/practice/Assignment3/hello_world
```

Run a single cache optimization experiment:
```bash
./build/X86/gem5.opt configs/practice/Assignment3/cache_optimizations.py
```

Run a single virtual memory experiment:
```bash
./build/X86/gem5.opt configs/practice/Assignment3/virtual_memory.py
```

Run all cache optimization experiments (batch mode):
```bash
./configs/practice/Assignment3/run_cache_experiments.sh
```

Run all virtual memory experiments (batch mode):
```bash
./configs/practice/Assignment3/run_vm_experiments.sh
```

## Experiment Overview

This assignment explores cache and virtual memory optimization through systematic parameter sweeps.

### Cache Optimization Experiments

The cache optimization experiments test various cache parameter combinations to analyze their impact on performance:

1. **Cache Sizes**: Tests cache sizes of 8KB, 16KB, 32KB, and 64KB to observe how cache capacity affects hit rates and miss penalties.

2. **Associativity**: Evaluates associativity levels of 1 (direct-mapped), 2, 4, and 8 ways to study the trade-off between conflict misses and access latency.

3. **Block Sizes**: Examines block sizes of 16B, 32B, 64B, and 128B to understand the impact of spatial locality and transfer overhead.

Each experiment measures cache hit rates, miss counts, and performance metrics for L1 instruction cache, L1 data cache, and L2 cache.

### Virtual Memory Experiments

The virtual memory experiments investigate page size and TLB (Translation Lookaside Buffer) configurations:

1. **Page Sizes**: Tests page sizes of 4KB, 8KB, and 16KB to analyze the trade-off between page table size and TLB coverage.

2. **TLB Sizes**: Evaluates TLB sizes of 32, 64, and 128 entries to study the impact on TLB hit rates and translation overhead.

3. **TLB Associativity**: Examines TLB associativity levels of 2, 4, and 8 ways to understand conflict resolution in the TLB.

**Note**: In SE (Syscall Emulation) mode, TLB configuration is limited. TLBs use default gem5 parameters. For full TLB control, full-system (FS) mode is required.

## Results

All experiment results are stored in CSV format under `configs/practice/Assignment3/results/`:

- **Cache experiments**: Individual result files (e.g., `size_8kB_result.csv`, `assoc_4_result.csv`) and a combined file `all_experiments.csv`
- **Virtual memory experiments**: Individual result files (e.g., `page_4kB_vm_result.csv`, `tlb_64_vm_result.csv`) and a combined file `all_vm_experiments.csv`

Each result file contains metrics including hit rates, miss counts, and performance statistics for the tested configurations.
