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
./build/X86/gem5.opt configs/practice/Assignment3/run_baseline_v2.py \
--l1i_size="16KiB" \
--l1d_size="64KiB" \
--l2_size="256KiB" \
--l1_assoc="2" \
--l2_assoc="8" \
--cache_line_size="64" \
--config_name="baseline" \
--output_dir="configs/practice/Assignment3/results_v2" \
--binary="configs/practice/Assignment3/matrix_benchmark"
```
![Screenshot](./results_v2/Screenshot%202026-01-25%20at%2010.31.33 AM.png)

Run a single virtual memory experiment:

```bash
./build/X86/gem5.opt configs/practice/Assignment3/virtual_memory.py tlb_64
```
![Screenshot](./results_v2/Screenshot%202026-01-25%20at%2011.49.23 AM.png)
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

Each result file contains metrics including hit rates, miss counts, and performance statistics for the tested configurations. For further analysis, please refer to [./results_v2/cache_analysis.md](./results_v2/cache_analysis.md) and [./results_v2/vm_analysis.md](./results_v2/vm_analysis.md)

## Conclusion

The cache experiments successfully showed that proper sizing and configuration can deliver substantial performance gains. I achieved 40.1% improvement over baseline by optimizing L1 and L2 cache parameters. The sweet spot we found was 64KB L1 D-cache with 8-way associativity and 256KB L2 cache, which effectively captured the 128KB working set of our matrix benchmark. Interestingly, increasing cache sizes beyond these thresholds provided minimal returns, which taught us that bigger isn't always better in architecture design.

The TLB experiments revealed an even more dramatic threshold effect. While 32 and 64-entry TLBs both struggled with around 77% hit rates, jumping to 128 entries suddenly achieved 99.997% hit rate with D-TLB misses dropping from 6.3 million to just 797. We could tell from this scenario that the real working set for our matrix operations needed roughly 100-120 TLB entries to avoid constant page table walks. However, we also learned that gem5's SE mode has significant limitations for VM experiments. The X86 architecture hardcodes page size at 4KB and uses fully associative TLBs, so only the TLB size parameter actually did anything. While initially frustrating, understanding these simulator limitations turned out to be just as valuable as the successful cache results. I can't wait to share this findout in our course forum.

---

## Troubleshooting and Methodology Refinement

Initially, I ran all experiments using a simple hello_world program as the workload. The cache experiments completed successfully, but something felt wrong. Every configuration showed with less than 0.3% variation. After examining the stats.txt output more carefully, I realized the hello_world binary only accessed about 2-3KB of memory total. This meant even the smallest cache I tested could hold the entire working set comfortably, so naturally there was no differentiation between configurations.

That's when I switched to the matrix multiplication benchmark, which has a much larger working set around 128KB. The difference was immediately obvious. now cache size changes produced measurable impacts on hit rates and simulation time. But then I noticed another issue: changing the block size parameter wasn't affecting anything either. After digging through the baseline_v2.py code, I discovered the block size wasn't actually being passed to the cache constructors. Once I fixed that bug and re-ran experiments, block size variations finally showed real differences.

The VM experiments presented a different challenge entirely. No matter how I configured page size or TLB associativity, every result came back identical. At first I thought I had another configuration bug, but after extensive debugging and reading gem5 documentation, I learned that X86 SE mode simply doesn't support these parameters Page size is hardcoded to 4KB and TLBs are fully associative by default. I even attempted switching to Full System mode by running x86-ubuntu-run.py, which successfully booted Ubuntu Linux. However, integrating our custom matrix benchmark into FS mode proved too complex for this project's scope, requiring custom disk images and significantly longer simulation times.