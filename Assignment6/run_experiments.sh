#!/bin/bash
#
# Run DAXPY TLP design space exploration experiments.
#
# Sweeps FloatSimdFU (opLat + issueLat = 7) across multiple thread counts.
# Results are saved to results/ directory and summarized in results.csv.
#
# Usage: bash configs/practice/Assignment6/run_experiments.sh
#   (run from the gem5 root directory)

set -e

GEM5_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SCRIPT_DIR="${GEM5_ROOT}/configs/practice/Assignment6"
GEM5="${GEM5_ROOT}/build/ARM/gem5.opt"
CONFIG="${SCRIPT_DIR}/multicore_minor_daxpy.py"
BINARY="${SCRIPT_DIR}/daxpy_mt_arm"
RESULTS_DIR="${SCRIPT_DIR}/results"
CSV_FILE="${SCRIPT_DIR}/results.csv"
ARRAY_SIZE=10000

# FloatSimdFU combinations (opLat + issueLat = 7)
OP_LATS=(1 2 3 4 5 6)
ISSUE_LATS=(6 5 4 3 2 1)

# Thread counts to test
THREAD_COUNTS=(1 2 4 8)

# -----------------------------------------------------------------------
# Step 1: Compile the DAXPY binary if needed
# -----------------------------------------------------------------------
if [ ! -f "${BINARY}" ]; then
    echo "Compiling DAXPY binary..."
    aarch64-linux-gnu-gcc -static -O2 -pthread \
        -o "${BINARY}" "${SCRIPT_DIR}/daxpy_mt.c"
    echo "Binary compiled: ${BINARY}"
fi

# -----------------------------------------------------------------------
# Step 2: Setup results directory and CSV header
# -----------------------------------------------------------------------
mkdir -p "${RESULTS_DIR}"
echo "opLat,issueLat,num_threads,simTicks,simOps,numCycles,cpi,ipc" > "${CSV_FILE}"

# -----------------------------------------------------------------------
# Step 3: Run experiments
# -----------------------------------------------------------------------
total_runs=$(( ${#OP_LATS[@]} * ${#THREAD_COUNTS[@]} ))
current_run=0

for idx in "${!OP_LATS[@]}"; do
    op_lat=${OP_LATS[$idx]}
    issue_lat=${ISSUE_LATS[$idx]}

    for num_threads in "${THREAD_COUNTS[@]}"; do
        current_run=$((current_run + 1))
        run_name="oplat${op_lat}_isslat${issue_lat}_threads${num_threads}"
        outdir="${RESULTS_DIR}/${run_name}"

        echo ""
        echo "=== Run ${current_run}/${total_runs}: opLat=${op_lat} issueLat=${issue_lat} threads=${num_threads} ==="

        # Run gem5 simulation
        "${GEM5}" \
            --outdir="${outdir}" \
            "${CONFIG}" \
            --num-cores "${num_threads}" \
            --op-lat "${op_lat}" \
            --issue-lat "${issue_lat}" \
            --binary "${BINARY}" \
            --array-size "${ARRAY_SIZE}" \
            2>&1 | tee "${outdir}.log"

        # ---------------------------------------------------------------
        # Extract statistics from stats.txt
        # ---------------------------------------------------------------
        stats_file="${outdir}/stats.txt"
        if [ ! -f "${stats_file}" ]; then
            echo "WARNING: stats.txt not found for ${run_name}"
            echo "${op_lat},${issue_lat},${num_threads},N/A,N/A,N/A,N/A,N/A" >> "${CSV_FILE}"
            continue
        fi

        # Extract key metrics (aggregate across all CPUs)
        simTicks=$(grep "^simTicks" "${stats_file}" | head -1 | awk '{print $2}')
        simOps=$(grep "^simOps" "${stats_file}" | head -1 | awk '{print $2}')

        # Sum numCycles across all CPUs
        numCycles=$(grep "numCycles" "${stats_file}" | awk '{sum += $2} END {print sum}')

        # Calculate aggregate CPI and IPC
        if [ -n "${simOps}" ] && [ "${simOps}" -gt 0 ] 2>/dev/null; then
            cpi=$(echo "scale=4; ${numCycles} / ${simOps}" | bc 2>/dev/null || echo "N/A")
            ipc=$(echo "scale=4; ${simOps} / ${numCycles}" | bc 2>/dev/null || echo "N/A")
        else
            cpi="N/A"
            ipc="N/A"
        fi

        echo "${op_lat},${issue_lat},${num_threads},${simTicks},${simOps},${numCycles},${cpi},${ipc}" >> "${CSV_FILE}"
        echo "  simTicks=${simTicks} simOps=${simOps} numCycles=${numCycles} CPI=${cpi} IPC=${ipc}"
    done
done

echo ""
echo "=== All experiments complete ==="
echo "Results CSV: ${CSV_FILE}"
echo "Per-run stats: ${RESULTS_DIR}/"
echo ""
echo "--- Results Summary ---"
column -t -s',' "${CSV_FILE}"
