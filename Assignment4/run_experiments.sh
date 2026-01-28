#!/bin/bash
# Assignment 4: ILP Experiments Script

OUTPUT_BASE="configs/practice/Assignment4/results"
mkdir -p $OUTPUT_BASE

BENCHMARK="./configs/practice/Assignment4/benchmark"
CONFIG="configs/practice/Assignment4/my_o3_se.py"

echo "=========================================="
echo "ILP Assignment Experiments"
echo "=========================================="

# Experiment 1: Baseline with Branch Prediction
echo ""
echo "Experiment 1: Baseline (4-wide superscalar, simple branch predictor)"
build/X86/gem5.opt \
  $CONFIG \
  --cmd=$BENCHMARK \
  > ${OUTPUT_BASE}/baseline.log 2>&1
cp m5out/stats.txt ${OUTPUT_BASE}/baseline_stats.txt
echo "✓ Baseline complete"

# Experiment 2: No Branch Prediction
echo ""
echo "Experiment 2: Without Branch Prediction"
build/X86/gem5.opt \
  $CONFIG \
  --cmd=$BENCHMARK \
  --bp=none \
  > ${OUTPUT_BASE}/no_bp.log 2>&1
cp m5out/stats.txt ${OUTPUT_BASE}/no_bp_stats.txt
echo "✓ No branch prediction complete"

# Experiment 3: Single-issue (narrow pipeline)
echo ""
echo "Experiment 3: Single-issue Pipeline"
build/X86/gem5.opt \
  $CONFIG \
  --cmd=$BENCHMARK \
  --fetchWidth=1 --decodeWidth=1 --renameWidth=1 \
  --dispatchWidth=1 --issueWidth=1 --commitWidth=1 \
  > ${OUTPUT_BASE}/single_issue.log 2>&1
cp m5out/stats.txt ${OUTPUT_BASE}/single_issue_stats.txt
echo "✓ Single-issue complete"

# Experiment 4: Dual-issue
echo ""
echo "Experiment 4: Dual-issue Pipeline"
build/X86/gem5.opt \
  $CONFIG \
  --cmd=$BENCHMARK \
  --fetchWidth=2 --decodeWidth=2 --renameWidth=2 \
  --dispatchWidth=2 --issueWidth=2 --commitWidth=2 \
  > ${OUTPUT_BASE}/dual_issue.log 2>&1
cp m5out/stats.txt ${OUTPUT_BASE}/dual_issue_stats.txt
echo "✓ Dual-issue complete"

# Experiment 5: Baseline 4-wide (reference)
echo ""
echo "Experiment 5: 4-wide Superscalar (Reference)"
build/X86/gem5.opt \
  $CONFIG \
  --cmd=$BENCHMARK \
  > ${OUTPUT_BASE}/quad_issue.log 2>&1
cp m5out/stats.txt ${OUTPUT_BASE}/quad_issue_stats.txt
echo "✓ 4-wide complete"

# Experiment 6: 8-wide superscalar
echo ""
echo "Experiment 6: 8-wide Superscalar"
build/X86/gem5.opt \
  $CONFIG \
  --cmd=$BENCHMARK \
  --fetchWidth=8 --decodeWidth=8 --renameWidth=8 \
  --dispatchWidth=8 --issueWidth=8 --commitWidth=8 \
  > ${OUTPUT_BASE}/eight_issue.log 2>&1
cp m5out/stats.txt ${OUTPUT_BASE}/eight_issue_stats.txt
echo "✓ 8-wide complete"

# Experiment 7: SMT with 2 threads
echo ""
echo "Experiment 7: SMT with 2 threads"
build/X86/gem5.opt \
  $CONFIG \
  --cmd=$BENCHMARK \
  --threads=2 \
  > ${OUTPUT_BASE}/smt_2threads.log 2>&1
cp m5out/stats.txt ${OUTPUT_BASE}/smt_2threads_stats.txt
echo "✓ SMT 2-threads complete"

# Experiment 8: SMT with 4 threads
echo ""
echo "Experiment 8: SMT with 4 threads"
build/X86/gem5.opt \
  $CONFIG \
  --cmd=$BENCHMARK \
  --threads=4 \
  > ${OUTPUT_BASE}/smt_4threads.log 2>&1
cp m5out/stats.txt ${OUTPUT_BASE}/smt_4threads_stats.txt
echo "✓ SMT 4-threads complete"

echo ""
echo "=========================================="
echo "All experiments complete!"
echo "Results saved in: $OUTPUT_BASE/"
echo "=========================================="
