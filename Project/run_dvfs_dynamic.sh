#!/bin/bash
#
# Run dynamic DVFS comparison: dynamic phase-aware vs static P0
# For each arch config, run:
#   1. Static P0 (2GHz/1.2V all phases) -- using non-instrumented binary
#   2. Dynamic DVFS (phase-aware switching) -- using instrumented binary
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=============================================="
echo "Dynamic DVFS Comparison"
echo "Static P0 vs Phase-Aware Dynamic DVFS"
echo "=============================================="

GEM5_PATH="../../../build/ARM/gem5.opt"
STATIC_BINARY="workloads/edge_preprocessing_arm"
DVFS_BINARY="workloads/edge_preprocessing_dvfs_arm"

if [ ! -f "$GEM5_PATH" ]; then
    echo -e "${RED}Error: gem5 binary not found at $GEM5_PATH${NC}"
    exit 1
fi

for bin in "$STATIC_BINARY" "$DVFS_BINARY"; do
    if [ ! -f "$bin" ]; then
        echo -e "${RED}Error: Binary not found: $bin${NC}"
        exit 1
    fi
done

# Arch configs: cpu_type:cache_flag:label
ARCH_CONFIGS=(
    "minor::MinorCPU L1"
    "minor:--l2-cache:MinorCPU L2"
    "o3::O3CPU L1"
    "o3:--l2-cache:O3CPU L2"
)

TOTAL=$((${#ARCH_CONFIGS[@]} * 2))
COUNT=0

for config in "${ARCH_CONFIGS[@]}"; do
    IFS=':' read -r cpu_type cache_flag label <<< "$config"

    dir_suffix=$(echo "$label" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')

    # --- Static P0 ---
    COUNT=$((COUNT + 1))
    outdir="m5out_${dir_suffix}_static_p0"
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${GREEN}[$COUNT/$TOTAL] $label -- Static P0 (2GHz/1.2V)${NC}"
    echo -e "${BLUE}=========================================${NC}"

    CMD="$GEM5_PATH --outdir=$outdir edge_power_config.py --cpu-type=$cpu_type --binary=$STATIC_BINARY --perf-level=0"
    if [ -n "$cache_flag" ]; then CMD="$CMD $cache_flag"; fi

    echo -e "${YELLOW}$CMD${NC}"
    time $CMD
    if [ $? -ne 0 ]; then echo -e "${RED}FAILED${NC}"; exit 1; fi
    echo -e "${GREEN}Complete${NC}"

    # --- Dynamic DVFS ---
    COUNT=$((COUNT + 1))
    outdir="m5out_${dir_suffix}_dynamic"
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${GREEN}[$COUNT/$TOTAL] $label -- Dynamic DVFS${NC}"
    echo -e "${BLUE}=========================================${NC}"

    CMD="$GEM5_PATH --outdir=$outdir edge_power_dvfs_dynamic.py --cpu-type=$cpu_type --binary=$DVFS_BINARY"
    if [ -n "$cache_flag" ]; then CMD="$CMD $cache_flag"; fi

    echo -e "${YELLOW}$CMD${NC}"
    time $CMD
    if [ $? -ne 0 ]; then echo -e "${RED}FAILED${NC}"; exit 1; fi
    echo -e "${GREEN}Complete${NC}"
done

echo ""
echo "=============================================="
echo "All $TOTAL Simulations Complete!"
echo "=============================================="
echo ""
echo "Compare results:"
echo "  python3 analyze_dvfs_dynamic.py"
echo ""
