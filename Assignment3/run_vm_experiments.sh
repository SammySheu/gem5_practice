#!/bin/bash

# Script to run all virtual memory experiments
# Each configuration runs in a separate gem5 process

GEM5_BIN="./build/X86/gem5.opt"
CONFIG_SCRIPT="configs/practice/Assignment3/virtual_memory.py"
RESULTS_DIR="configs/practice/Assignment3/results"

# Create results directory
mkdir -p "$RESULTS_DIR"

# List of all configurations
CONFIGS=(
    "page_4kB"
    "page_8kB"
    "page_16kB"
    "tlb_32"
    "tlb_64"
    "tlb_128"
    "tlb_assoc_2"
    "tlb_assoc_4"
    "tlb_assoc_8"
)

echo "=================================="
echo "Running Virtual Memory Experiments"
echo "=================================="
echo ""
echo "Note: In SE (Syscall Emulation) mode, TLB configuration is limited."
echo "TLBs use default gem5 parameters. For full TLB control, use FS mode."
echo ""

# Run each configuration
for config in "${CONFIGS[@]}"; do
    echo "Running configuration: $config"
    $GEM5_BIN "$CONFIG_SCRIPT" "$config" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "  ✓ Completed successfully"
    else
        echo "  ✗ Failed"
    fi
done

echo ""
echo "=================================="
echo "All experiments completed!"
echo "Results saved to $RESULTS_DIR/"
echo "=================================="

# Combine all results into one CSV file
COMBINED_CSV="$RESULTS_DIR/all_vm_experiments.csv"
echo "Combining results into $COMBINED_CSV"

# Create header
head -1 "$RESULTS_DIR/page_4kB_vm_result.csv" > "$COMBINED_CSV"

# Append all data (skip header)
for config in "${CONFIGS[@]}"; do
    result_file="$RESULTS_DIR/${config}_vm_result.csv"
    if [ -f "$result_file" ]; then
        tail -n +2 "$result_file" >> "$COMBINED_CSV"
    fi
done

echo "Done! Combined results: $COMBINED_CSV"

