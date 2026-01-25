#!/bin/bash

# Script to run all virtual memory experiments
# Each configuration runs in a separate gem5 process

set -e  # Exit on error

BASE_DIR="configs/practice/Assignment3"
GEM5_BIN="./build/X86/gem5.opt"
CONFIG_SCRIPT="${BASE_DIR}/virtual_memory.py"
RESULTS_DIR="${BASE_DIR}/results_v2"
RESULTS_FILE="${RESULTS_DIR}/all_vm_experiments.csv"

echo "======================================================================"
echo "Virtual Memory Experiments - Version 2"
echo "Testing TLB configurations"
echo "======================================================================"
echo ""
echo "IMPORTANT: X86 Architecture Limitations in SE Mode:"
echo "  - Page size is HARDCODED to 4KB (cannot be changed)"
echo "  - TLB associativity is FIXED to fully associative"
echo "  - Only TLB SIZE can be varied"
echo ""
echo "Expected Results:"
echo "  - Page size experiments will show IDENTICAL results (all use 4KB)"
echo "  - TLB size experiments SHOULD show DIFFERENT results"
echo "  - TLB assoc experiments will show IDENTICAL results (all fully assoc)"
echo "======================================================================"

# Step 1: Create results directory
echo ""
echo "Step 1: Setting up results directory..."
echo "----------------------------------------------------------------------"
mkdir -p "${RESULTS_DIR}"
# Remove old individual VM result files if they exist
# rm -f "${RESULTS_DIR}"/*_vm_result.csv
# echo "✓ Cleaned up old VM result files"
echo "✓ Results will be saved to: ${RESULTS_DIR}"

# Step 2: Run experiments
echo ""
echo "Step 2: Running virtual memory experiments..."
echo "======================================================================"
echo ""

# Counter for experiments
total_experiments=0
completed_experiments=0

# Function to run an experiment
run_vm_experiment() {
    local config_name="$1"
    
    total_experiments=$((total_experiments + 1))
    
    echo ""
    echo "Experiment ${total_experiments}: ${config_name}"
    echo "----------------------------------------------------------------------"
    
    if ${GEM5_BIN} "${CONFIG_SCRIPT}" "${config_name}" > /dev/null 2>&1; then
        completed_experiments=$((completed_experiments + 1))
        echo "✓ ${config_name} completed successfully"
    else
        echo "✗ ${config_name} failed"
    fi
}

# ======================================================================
# EXPERIMENT SET 1: PAGE SIZE VARIATIONS (Expected: IDENTICAL results)
# ======================================================================
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 1: Page Size Variations (will be identical for X86)"
echo "======================================================================"

run_vm_experiment "page_4kB"
run_vm_experiment "page_8kB"
run_vm_experiment "page_16kB"

# ======================================================================
# EXPERIMENT SET 2: TLB SIZE VARIATIONS (Expected: DIFFERENT results)
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 2: TLB Size Variations (SHOULD show differences)"
echo "======================================================================"

run_vm_experiment "tlb_32"
run_vm_experiment "tlb_64"
run_vm_experiment "tlb_128"

# ======================================================================
# EXPERIMENT SET 3: TLB ASSOCIATIVITY VARIATIONS (Expected: IDENTICAL results)
# ======================================================================
echo ""
echo ""
echo "======================================================================"
echo "EXPERIMENT SET 3: TLB Associativity Variations (will be identical for X86)"
echo "======================================================================"

run_vm_experiment "tlb_assoc_2"
run_vm_experiment "tlb_assoc_4"
run_vm_experiment "tlb_assoc_8"

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
first_result=$(find "${RESULTS_DIR}" -name "*_vm_result.csv" -type f | head -n 1)

if [ -n "$first_result" ]; then
    # Create combined CSV with header
    head -1 "$first_result" > "${RESULTS_FILE}"
    
    # Append all data (skip headers)
    for result_file in "${RESULTS_DIR}"/*_vm_result.csv; do
        if [ -f "$result_file" ]; then
            tail -n +2 "$result_file" >> "${RESULTS_FILE}"
        fi
    done
    
    echo "✓ Combined results saved to: ${RESULTS_FILE}"
    echo "✓ Individual results kept in: ${RESULTS_DIR}/*_vm_result.csv"
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
echo "To sort by I-TLB hit rate:"
echo "  (head -n 1 ${RESULTS_FILE} && tail -n +2 ${RESULTS_FILE} | sort -t, -k5 -rn) | column -t -s,"
echo ""
echo "To sort by D-TLB hit rate:"
echo "  (head -n 1 ${RESULTS_FILE} && tail -n +2 ${RESULTS_FILE} | sort -t, -k6 -rn) | column -t -s,"
echo ""

