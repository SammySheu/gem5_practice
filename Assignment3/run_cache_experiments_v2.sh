#!/bin/bash

# Script to run comprehensive cache optimization experiments using baseline_v2
# This script tests various combinations of cache size, associativity, and block size

set -e  # Exit on error

BASE_DIR="configs/practice/Assignment3"
BINARY="${BASE_DIR}/matrix_benchmark"
RESULTS_DIR="${BASE_DIR}/results_v2"
RESULTS_FILE="${RESULTS_DIR}/all_experiments_v2.csv"

echo "======================================================================"
echo "Cache Optimization Experiments - Version 2"
echo "Using configurable baseline_v2 cache classes"
echo "======================================================================"

# Step 1: Check if binary exists, if not compile it
echo ""
echo "Step 1: Checking/compiling matrix benchmark..."
echo "----------------------------------------------------------------------"
if [ ! -f "${BINARY}" ]; then
    if [ -f "${BASE_DIR}/matrix_benchmark.c" ]; then
        echo "Compiling matrix_benchmark.c..."
        gcc -O2 -static "${BASE_DIR}/matrix_benchmark.c" -o "${BINARY}" -lm
        echo "✓ Compiled successfully: ${BINARY}"
    else
        echo "✗ Error: matrix_benchmark.c not found!"
        exit 1
    fi
else
    echo "✓ Binary exists: ${BINARY}"
fi
ls -lh "${BINARY}"

# Step 2: Create results directory
echo ""
echo "Step 2: Setting up results directory..."
echo "----------------------------------------------------------------------"
mkdir -p "${RESULTS_DIR}"
# Remove old individual result files if they exist
rm -f "${RESULTS_DIR}"/*_result.csv
echo "✓ Cleaned up old result files"
echo "✓ Results will be saved to: ${RESULTS_DIR}"

# Step 3: Run experiments
echo ""
echo "Step 3: Running cache experiments..."
echo "======================================================================"

# Counter for experiments
total_experiments=0
completed_experiments=0

# Function to run an experiment
run_experiment() {
    local name="$1"
    local l1i_size="$2"
    local l1d_size="$3"
    local l2_size="$4"
    local l1_assoc="$5"
    local l2_assoc="$6"
    local cache_line="$7"
    
    total_experiments=$((total_experiments + 1))
    
    echo ""
    echo "Experiment ${total_experiments}: ${name}"
    echo "----------------------------------------------------------------------"
    echo "  L1I: ${l1i_size}, L1D: ${l1d_size}, L2: ${l2_size}"
    echo "  L1 Assoc: ${l1_assoc}, L2 Assoc: ${l2_assoc}, Block: ${cache_line}B"
    echo ""
    
    if ./build/X86/gem5.opt "${BASE_DIR}/run_baseline_v2.py" \
        --l1i_size="${l1i_size}" \
        --l1d_size="${l1d_size}" \
        --l2_size="${l2_size}" \
        --l1_assoc="${l1_assoc}" \
        --l2_assoc="${l2_assoc}" \
        --cache_line_size="${cache_line}" \
        --config_name="${name}" \
        --output_dir="${RESULTS_DIR}" \
        --binary="${BINARY}"; then
        completed_experiments=$((completed_experiments + 1))
        echo "✓ ${name} completed successfully"
    else
        echo "✗ ${name} failed"
    fi
}

# BASELINE CONFIGURATION (for reference)
echo ""
echo ">>> BASELINE CONFIGURATION <<<"
run_experiment "baseline" "16KiB" "64KiB" "256KiB" 2 8 64

# ======================================================================
# EXPERIMENT SET 1: L1 DATA CACHE SIZE VARIATIONS
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 1: L1 Data Cache Size Variations"
echo "======================================================================"

run_experiment "l1d_size_8KB"   "16KiB"  "8KiB"   "256KiB" 2 8 64
run_experiment "l1d_size_16KB"  "16KiB"  "16KiB"  "256KiB" 2 8 64
run_experiment "l1d_size_32KB"  "16KiB"  "32KiB"  "256KiB" 2 8 64
run_experiment "l1d_size_128KB" "16KiB"  "128KiB" "256KiB" 2 8 64

# ======================================================================
# EXPERIMENT SET 2: L1 INSTRUCTION CACHE SIZE VARIATIONS
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 2: L1 Instruction Cache Size Variations"
echo "======================================================================"

run_experiment "l1i_size_8KB"   "8KiB"   "64KiB" "256KiB" 2 8 64
run_experiment "l1i_size_32KB"  "32KiB"  "64KiB" "256KiB" 2 8 64
run_experiment "l1i_size_64KB"  "64KiB"  "64KiB" "256KiB" 2 8 64

# ======================================================================
# EXPERIMENT SET 3: L2 CACHE SIZE VARIATIONS
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 3: L2 Cache Size Variations"
echo "======================================================================"

run_experiment "l2_size_128KB"  "16KiB" "64KiB" "128KiB" 2 8 64
run_experiment "l2_size_512KB"  "16KiB" "64KiB" "512KiB" 2 8 64
run_experiment "l2_size_1MB"    "16KiB" "64KiB" "1MiB"   2 8 64

# ======================================================================
# EXPERIMENT SET 4: L1 ASSOCIATIVITY VARIATIONS
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 4: L1 Associativity Variations"
echo "======================================================================"

run_experiment "l1_assoc_1"  "16KiB" "64KiB" "256KiB" 1 8 64  # Direct-mapped
run_experiment "l1_assoc_4"  "16KiB" "64KiB" "256KiB" 4 8 64
run_experiment "l1_assoc_8"  "16KiB" "64KiB" "256KiB" 8 8 64

# ======================================================================
# EXPERIMENT SET 5: L2 ASSOCIATIVITY VARIATIONS
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 5: L2 Associativity Variations"
echo "======================================================================"

run_experiment "l2_assoc_4"   "16KiB" "64KiB" "256KiB" 2 4  64
run_experiment "l2_assoc_16"  "16KiB" "64KiB" "256KiB" 2 16 64

# ======================================================================
# EXPERIMENT SET 6: CACHE LINE SIZE VARIATIONS
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 6: Cache Line Size Variations"
echo "======================================================================"

run_experiment "block_32B"   "16KiB" "64KiB" "256KiB" 2 8 32
run_experiment "block_128B"  "16KiB" "64KiB" "256KiB" 2 8 128

# ======================================================================
# EXPERIMENT SET 7: OPTIMIZED CONFIGURATIONS
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 7: Optimized Configurations"
echo "======================================================================"

run_experiment "optimized_1" "32KiB"  "128KiB" "512KiB" 4 16 64
run_experiment "optimized_2" "32KiB"  "128KiB" "1MiB"   4 16 64
run_experiment "optimized_3" "64KiB"  "128KiB" "1MiB"   8 16 128

# ======================================================================
# SUMMARY
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "Experiments Completed!"
echo "======================================================================"
echo ""
echo "Summary:"
echo "  Total experiments: ${total_experiments}"
echo "  Completed: ${completed_experiments}"
echo "  Failed: $((total_experiments - completed_experiments))"
echo ""

# ======================================================================
# COMBINE RESULTS
# ======================================================================
echo ""
echo "Combining individual results into ${RESULTS_FILE}..."
echo "----------------------------------------------------------------------"

# Find the first successful result file to get the header
first_result=$(find "${RESULTS_DIR}" -name "*_result.csv" -type f | head -n 1)

if [ -n "$first_result" ]; then
    # Create combined CSV with header
    head -1 "$first_result" > "${RESULTS_FILE}"
    
    # Append all data (skip headers)
    for result_file in "${RESULTS_DIR}"/*_result.csv; do
        if [ -f "$result_file" ]; then
            tail -n +2 "$result_file" >> "${RESULTS_FILE}"
        fi
    done
    
    echo "✓ Combined results saved to: ${RESULTS_FILE}"
    echo "✓ Individual results kept in: ${RESULTS_DIR}/*_result.csv"
else
    echo "✗ No result files found to combine"
fi

echo ""
echo "To view results:"
echo "  cat ${RESULTS_FILE}"
echo ""
echo "To analyze results:"
echo "  column -t -s, ${RESULTS_FILE} | less -S"
echo ""
echo "To sort by L1 D-Cache hit rate:"
echo "  (head -n 1 ${RESULTS_FILE} && tail -n +2 ${RESULTS_FILE} | sort -t, -k14 -rn) | column -t -s,"
echo ""
echo "To sort by simulation time (ticks):"
echo "  (head -n 1 ${RESULTS_FILE} && tail -n +2 ${RESULTS_FILE} | sort -t, -k8 -n) | column -t -s,"
echo ""


