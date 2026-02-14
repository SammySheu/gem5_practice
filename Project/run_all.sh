#!/bin/bash
#
# Run all simulation configurations for comparison
# Phase 3: Edge Pre-processing Microprocessor with DVFS
#
# This script runs 12 configurations:
# 4 architecture configs (MinorCPU/O3CPU x L1/L2) x 3 DVFS levels
#

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=============================================="
echo "Running All Simulation Configurations"
echo "Phase 3: DVFS Optimization"
echo "=============================================="
echo "DVFS Levels:"
echo "  0 = High Performance (2GHz / 1.2V)"
echo "  1 = Balanced         (1.2GHz / 1.0V)"
echo "  2 = Low Power        (600MHz / 0.8V)"
echo "=============================================="

# Check if gem5 binary exists
GEM5_PATH="../../../build/ARM/gem5.opt"
if [ ! -f "$GEM5_PATH" ]; then
    echo -e "${RED}Error: gem5 binary not found at $GEM5_PATH${NC}"
    echo "Please build gem5 first:"
    echo "  cd /home/sammy/gem5"
    echo "  scons build/ARM/gem5.opt -j\$(nproc)"
    exit 1
fi

# Check if workload binary exists
WORKLOAD="workloads/edge_preprocessing_arm"
if [ ! -f "$WORKLOAD" ]; then
    echo -e "${RED}Error: Workload binary not found at $WORKLOAD${NC}"
    exit 1
fi

# Configuration list: cpu_type:cache_type:base_dir:description
ARCH_CONFIGS=(
    "minor:l1:m5out_minor_l1:MinorCPU L1-only"
    "minor:l2:m5out_minor_l2:MinorCPU L1+L2"
    "o3:l1:m5out_o3_l1:O3CPU L1-only"
    "o3:l2:m5out_o3_l2:O3CPU L1+L2"
)

PERF_LEVELS=(0 1 2)
PERF_LABELS=("High-Perf" "Balanced" "Low-Power")

TOTAL=$((${#ARCH_CONFIGS[@]} * ${#PERF_LEVELS[@]}))
COUNT=0

# Run each configuration at each DVFS level
for config in "${ARCH_CONFIGS[@]}"; do
    IFS=':' read -r cpu_type cache_type base_dir description <<< "$config"

    for i in "${!PERF_LEVELS[@]}"; do
        perf_level=${PERF_LEVELS[$i]}
        perf_label=${PERF_LABELS[$i]}
        output_dir="${base_dir}_perf${perf_level}"
        COUNT=$((COUNT + 1))

        echo ""
        echo -e "${BLUE}=========================================${NC}"
        echo -e "${GREEN}[$COUNT/$TOTAL] $description @ $perf_label (perf-level=$perf_level)${NC}"
        echo -e "${BLUE}=========================================${NC}"

        # Build command
        CMD="$GEM5_PATH --outdir=$output_dir edge_power_config.py --cpu-type=$cpu_type --binary=$WORKLOAD --stat-freq=0.001 --perf-level=$perf_level"

        # Add L2 flag if needed
        if [ "$cache_type" == "l2" ]; then
            CMD="$CMD --l2-cache"
        fi

        # Run simulation
        echo -e "${YELLOW}Running: $CMD${NC}"
        time $CMD

        if [ $? -ne 0 ]; then
            echo -e "${RED}Simulation failed!${NC}"
            exit 1
        fi

        echo -e "${GREEN}Complete${NC}"
    done
done

echo ""
echo "=============================================="
echo "All $TOTAL Simulations Complete!"
echo "=============================================="
echo ""
echo "Results directories:"
for config in "${ARCH_CONFIGS[@]}"; do
    IFS=':' read -r cpu_type cache_type base_dir description <<< "$config"
    echo "  $description:"
    for perf_level in "${PERF_LEVELS[@]}"; do
        echo "    - ${base_dir}_perf${perf_level}/"
    done
done
echo ""
echo "To compare results, run:"
echo "  python3 analyze_results.py"
echo ""
