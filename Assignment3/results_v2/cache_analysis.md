# Cache Memory Hierarchy Analysis Report
## gem5 Simulation Study

---

## Executive Summary

This report presents a comprehensive analysis of cache memory hierarchy design through systematic gem5 simulations. I use six parameter dimensions: 
* L1 data cache size
* L1 instruction cache size
* L2 cache size, 
* L1 associativity, 
* L2 associativity
* cache line size (block size).

The baseline configuration achieved 381.32ms simulation time while the optimized configurations achieved up to **40.1% performance improvement** (228.56ms) through cache parameter adjusting.

---

## 1. Baseline Configuration

**Configuration:**
- L1 I-Cache: 16KiB(8-128), 2-way(1-8) associative
- L1 D-Cache: 64KiB(8-128), 2-way(1-8) associative  
- L2 Cache: 256KiB(128-1024), 8-way(4-16) associative
- Cache Line Size: 64(32-128) bytes


## 2. Cache Line Size (Block Size) Impact

![Block Size Comparison](./block_size.png)
<!-- 
| Config | Size | Sim Time (s) | Change | D-Cache Hit Rate | Change |
|--------|------|--------------|--------|------------------|--------|
| block_32B | 32 Bytes | 0.288481 | -24.3% | 90.50% | +14.41% |
| **Baseline** | **64 Bytes** | **0.38132** | **0%** | **76.09%** | **0%** |
| block_128B | 128 Bytes | 0.40251 | +5.6% | 72.72% | -3.37% |
 -->

**Analysis:** Although larger blocks have better spatial locality exploitation, it hurt performance due to miss penalty. Below are some potential factors that lead to lower performance:
1. **Internal Fragmentation:** Fetching 128 bytes when only 64 are needed wastes bandwidth
2. **Cache Pollution:** Large blocks evict more useful data
3. **Conflict Increase:** Fewer total cache lines lead to more conflicts
4. **Memory Bus Pressure:** Larger transfers increase memory latency

**Recommendation:** For this specific workload, 32-byte blocks offer better L1 D-cache hit rate by reducing cache line conflicts. This outcome might be different if streaming applications are used for the workload because they provide larger blocks.

---

## 3. L1 Data Cache Size Impact
![L1 D-cache Comparison](./L1-D-cache_size.png)
<!-- 
| Config | Size | Sim Time (s) | Change | D-Cache Hit Rate | Change |
|--------|------|--------------|--------|------------------|--------|
| l1d_size_8KB | 8KiB | 0.424153 | +11.2% | 69.66% | -6.43% |
| l1d_size_16KB | 16KiB | 0.398892 | +4.6% | 73.45% | -2.64% |
| l1d_size_32KB | 32KiB | 0.38711 | +1.5% | 75.22% | -0.87% |
| **Baseline** | **64KiB** | **0.38132** | **0%** | **76.09%** | **0%** |
| l1d_size_128KB | 128KiB | 0.37902 | -0.6% | 76.46% | +0.37% | 
-->

**Analysis:**
Adjusting L1 Data Cache from 8KiB to 32KiB improve performance significantly. It reach sweet spot around 64KiB and doubling from 64KiB to 128KiB yields only 0.6% improvement. It seems that the workload has a relatively fixed working set, and in this scenario, the cache size optimization should target the 50-75th percentile of workload requirements.

---

## 4. L1 Instruction Cache Size Impact
![L1 I-cache Comparison](./L1-I-cache_size.png)
<!-- 
| Config | Size | Sim Time (s) | Change | I-Cache Hit Rate |
|--------|------|--------------|--------|----------------|
| l1i_size_8KB | 8KiB | 0.381349 | +0.006% | 100% |
| **Baseline** | **16KiB** | **0.38132** | **0%** | **100%** |
| l1i_size_32KB | 32KiB | 0.3813 | -0.005% | 100% |
| l1i_size_64KB | 64KiB | 0.381297 | -0.006% | 100% |
 -->
**Analysis:**
No matter how we change the size of I-cache, all variations' performance have only 0.01% difference. It indicates that the matrix benchmark has a small and tight instruction loop. No benefit for increasing I-cache beyond 16KiB.

**Architectural Insight:** Scientific computing often has small instruction footprints, while multimedia or OS kernels might require much larger instruction caches.

---

## 5. L2 Cache Size Impact
![L2 Cache Comparison](./L2-cache_size.png)
<!-- 
| Config | Size | Sim Time (s) | Change | L2 Hit Rate |
|--------|------|--------------|--------|-------------|
| l2_size_128KB | 128KiB | 0.432084 | +13.3% | 90.91% |
| **Baseline** | **256KiB** | **0.38132** | **0%** | **99.38%** |
| l2_size_512KB | 512KiB | 0.379223 | -0.5% | 99.76% |
| l2_size_1MB | 1MiB | 0.378762 | -0.7% | 99.85% |
 -->
**Analysis:**
Our baseline(256KiB for L2 Cache size) seems to capture most of the data that misses L1. Beyond than that, benefits of increasing L2 cache size is less than 1%. Decreasing L2 Cache Size from 256 KiB cause 13.3% slow down due to L2 miss penalty (DRAM access penalty)

---

## 6. L1 Associativity Impact
![L1 Associativity Comparison](./L1-Associativitiy.png)
<!-- 
| Config | Associativity | Sim Time (s) | Change | D-Cache Hit Rate | Change |
|--------|---------------|--------------|--------|------------------|--------|
| l1_assoc_1 | 1-way (Direct) | 0.412979 | +8.3% | 71.38% | -4.71% |
| **Baseline** | **2-way** | **0.38132** | **0%** | **76.09%** | **0%** |
| l1_assoc_4 | 4-way | 0.258285 | **-32.3%** | 94.56% | +18.47% |
| l1_assoc_8 | 8-way | 0.249465 | **-34.6%** | 95.89% | +19.80% |
 -->
**Analysis:**
1-way associativity shows 8.3% slowdown—conflict misses are significant. Jumping from 2-way to 4-way yields 32.3% speedup. 4-way to 8-way only adds 2.3% additional improvement. Hit rate has positive correlation with performance. This tell us that the sweet spot is 4-8 way associativity. Beyond 8-way, the hardware complexity (comparison logic, power consumption) outweighs benefits.

---

## 7. L2 Associativity Impact

| Config | Associativity | Sim Time (s) | Change | L2 Hit Rate | Change |
|--------|---------------|--------------|--------|-------------|-----------|
| l2_assoc_4 | 4-way | 0.479962 | +25.9% | 83.05% | 16.32% |
| **Baseline** | **8-way** | **0.38132** | **0%** | **99.38%** | **0** |
| l2_assoc_16 | 16-way | 0.381108 | -0.06% | 99.41% | 0.03% |

**Analysis:**
Since higher associativity allow more distinct addresses to be map in one set, it avoid conflict misses. Besides, L2 handle the miss of L1, so the cost of missing the access to DRAM is much higher. Not only does L2 require bigger size of cache, but also require higher associativity than L1 (8-16 way). 
