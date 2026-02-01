# Edge Pre-processing Microprocessor - gem5 Implementation

**Course Project: Designing and Implementing a Microprocessor Using gem5 Simulation Software**

This project implements a low-power microprocessor architecture for edge computing applications, comparing in-order (MinorCPU) and out-of-order (O3CPU) execution strategies with comprehensive power modeling using gem5's MathExprPowerModel framework.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Building and Running](#building-and-running)
- [Workload Characteristics](#workload-characteristics)
- [Results Analysis](#results-analysis)
- [Online Resources](@online-resources)

---

## Project Overview

### Target Application: Edge Computing Pre-processing

Edge computing shifts data processing from centralized cloud platforms to energy-constrained devices near sensors and actuators. This project targets an **edge pre-processing server** that sits between sensor arrays and the cloud, responsible for:

- **Reducing bandwidth**: Lightweight sensor fusion and filtering
- **Improving responsiveness**: Processing data closer to the source
- **Power efficiency**: Operating under strict power budgets

### Design Space Exploration

The project compares **two CPU architectures** across **two cache configurations**:

- **CPU Models**: MinorCPU (in-order) vs. O3CPU (out-of-order)
- **Cache Hierarchy**: L1 only vs. L1+L2
- **Total configurations**: 4 (2 × 2)

---

## Building and Running

### Prerequisites
1. If gem5 hasn't been built yet, please refer to [REPO README](../README.md)

2. As I decided to switch from X86 to ARM, we have to make sure it has ARM executable file
   ```bash
   cd /gem5
   scons build/ARM/gem5.opt -j$(nproc)
   ```

3. **Compile the workload binary:**
   
   ```bash

   aarch64-linux-gnu-gcc -O2 -static configs/practice/Project/workloads/edge_preprocessing.c \
       -o configs/practice/Project/workloads/edge_preprocessing_arm -lm
   ```

### Running Simulations

#### Manually Run Simulation
**Minor Config**
```bash
./build/ARM/gem5.opt \
    --outdir=configs/practice/Project/m5out_minor_l2 \
    configs/practice/Project/edge_power_config.py \
    --cpu-type=minor \
    --stat-freq=0.0001 \
    --l2-cache \
    --binary=configs/practice/Project/workloads/edge_preprocessing_arm
```

**O3 Config**
```bash
./build/ARM/gem5.opt \
    --outdir=configs/practice/Project/m5out_o3_l2 \
    configs/practice/Project/edge_power_config.py \
    --cpu-type=o3 \
    --stat-freq=0.0001 \
    --l2-cache \
    --binary=configs/practice/Project/workloads/edge_preprocessing_arm
```

---
## Workload Characteristics

### Edge Pre-processing Pipeline

The benchmark (`edge_preprocessing.c`) implements a realistic edge computing workload:

1. **Generate Sensor Data**: 8 sensors × 1024 samples (simulating IoT devices)
2. **Moving Average Filter**: Streaming memory access with small sliding window
3. **Anomaly Detection**: Branch-intensive threshold comparisons
4. **Normalization**: Floating-point division and multiplication
5. **Statistical Aggregation**: Min/max/sum computations with loop dependencies

---

## Results Analysis

### Output Directories

After running simulations, results are stored in:

```
configs/practice/Project/
├── m5out_minor_l1/     # MinorCPU, L1 only
├── m5out_minor_l2/     # MinorCPU, L1+L2
├── m5out_o3_l1/        # O3CPU, L1 only
└── m5out_o3_l2/        # O3CPU, L1+L2
```

Each directory contains:
- **stats.txt**: Performance, cache, branch, and power statistics
- **config.ini**: Full configuration parameters
- **config.json**: JSON configuration export


#### Cache Performance

```bash
# Extract L1 D-cache miss rate
grep "system.cpu.dcache.overallMissRate" m5out_*/stats.txt

# Extract L1 I-cache miss rate
grep "system.cpu.icache.overallMissRate" m5out_*/stats.txt

# Extract L2 cache statistics (if enabled)
grep "system.l2.overallMissRate" m5out_*/stats.txt
```

#### Branch Prediction

```bash
# Extract Branch misprediction rate
grep "branchPred.condPredicted" m5out_*/stats.txt
grep "branchPred.condIncorrect" m5out_*/stats.txt
```

#### Power Analysis

```bash
# Extract CPU power state distribution
grep "system.cpu.power_state.stateResidency" m5out_*/stats.txt

# Extract Cache power states
grep "dcache.power_state" m5out_*/stats.txt
```


### Analyzing Results

Base on above extract commands, I write a script to compare the results.

```bash
python analyze_results.py
```

This generates:
- Performance comparison (IPC, execution time)
- Cache statistics (hit rates, miss rates)
- Branch prediction accuracy
- Power consumption estimates
- Energy-delay product (EDP) analysis

---

## Online Resources

**gem5 Documentation**:
- gem5 Official Documentation: https://www.gem5.org/documentation/
- gem5 ARM Power Modelling Guide: https://www.gem5.org/documentation/learning_gem5/part2/arm_power_modelling/
- gem5 Learning Resources: https://www.gem5.org/documentation/learning_gem5/