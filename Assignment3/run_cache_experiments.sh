#!/bin/bash

# Script to run all cache optimization experiments
# Each configuration runs in a separate gem5 process

GEM5_BIN="./build/X86/gem5.opt"
CONFIG_SCRIPT="configs/practice/Assignment3/cache_optimizations.py"
RESULTS_DIR="configs/practice/Assignment3/results"

# Create results directory
mkdir -p "$RESULTS_DIR"

# List of all configurations
CONFIGS=(
    "size_8kB"
    "size_16kB"
    "size_32kB"
    "size_64kB"
    "assoc_1"
    "assoc_2"
    "assoc_4"
    "assoc_8"
    "block_16B"
    "block_32B"
    "block_64B"
    "block_128B"
)

echo "=================================="
echo "Running Cache Optimization Experiments"
echo "=================================="
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
COMBINED_CSV="$RESULTS_DIR/all_experiments.csv"
echo "Combining results into $COMBINED_CSV"

# Create header
head -1 "$RESULTS_DIR/size_8kB_result.csv" > "$COMBINED_CSV"

# Append all data (skip header)
for config in "${CONFIGS[@]}"; do
    result_file="$RESULTS_DIR/${config}_result.csv"
    if [ -f "$result_file" ]; then
        tail -n +2 "$result_file" >> "$COMBINED_CSV"
    fi
done

echo "Done! Combined results: $COMBINED_CSV"

