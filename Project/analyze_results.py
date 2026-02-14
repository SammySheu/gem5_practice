#!/usr/bin/env python3
"""
Result Analysis Script for Edge Pre-processing Microprocessor Simulations
Phase 3: DVFS Optimization with Power-Performance-Energy Tradeoffs

This script analyzes simulation results from 12 configurations:
- MinorCPU vs O3CPU
- L1 only vs L1+L2
- 3 DVFS operating points (High/Balanced/Low-Power)
- Power consumption analysis (dynamic + static)
- Energy and Energy-Delay Product (EDP) calculations
- DVFS comparison tables showing V^2 scaling

Usage:
    python3 analyze_results.py
"""

import re
import sys
from pathlib import Path


# DVFS operating point definitions (must match edge_power_config.py)
DVFS_POINTS = {
    0: {'freq': '2GHz',   'voltage': '1.2V', 'voltage_val': 1.2, 'label': 'High-Perf'},
    1: {'freq': '1.2GHz', 'voltage': '1.0V', 'voltage_val': 1.0, 'label': 'Balanced'},
    2: {'freq': '600MHz', 'voltage': '0.8V', 'voltage_val': 0.8, 'label': 'Low-Power'},
}


class SimulationResults:
    """Container for simulation results from a single configuration."""

    def __init__(self, name, stats_file, perf_level=0):
        self.name = name
        self.stats_file = stats_file
        self.perf_level = perf_level

        # Performance metrics
        self.sim_seconds = 0.0
        self.sim_ticks = 0
        self.num_cycles = 0
        self.ipc = 0.0

        # Cache metrics
        self.l1i_accesses = 0
        self.l1i_misses = 0
        self.l1i_miss_rate = 0.0
        self.l1d_accesses = 0
        self.l1d_misses = 0
        self.l1d_miss_rate = 0.0
        self.l2_accesses = 0
        self.l2_misses = 0
        self.l2_miss_rate = 0.0

        # Branch prediction
        self.branches = 0
        self.branch_mispreds = 0
        self.branch_mispredict_rate = 0.0

        # Power metrics
        self.cpu_dynamic_power = 0.0
        self.cpu_static_power = 0.0
        self.icache_dynamic_power = 0.0
        self.icache_static_power = 0.0
        self.dcache_dynamic_power = 0.0
        self.dcache_static_power = 0.0
        self.l2_dynamic_power = 0.0
        self.l2_static_power = 0.0

        # Derived power metrics
        self.total_dynamic_power = 0.0
        self.total_static_power = 0.0
        self.total_power = 0.0
        self.total_energy = 0.0
        self.edp = 0.0

        # Parse stats file
        self.parse_stats()

    def parse_stats(self):
        """Parse gem5 stats.txt file, aggregating across all periodic dumps.

        gem5 periodic stat dumps reset between periods, so each dump covers
        one time window. We sum counters and time-weight power values across
        all dumps to get accurate totals.
        """
        if not Path(self.stats_file).exists():
            print(f"Warning: Stats file not found: {self.stats_file}")
            return

        with open(self.stats_file, 'r') as f:
            content = f.read()

        # Split into individual stat dumps
        dumps = re.split(r'-+ Begin Simulation Statistics -+\n', content)
        dumps = [d for d in dumps if d.strip()]  # Remove empty

        if not dumps:
            return

        # Accumulators for summing across dumps
        total_sim_seconds = 0.0
        total_sim_ticks = 0
        total_cycles = 0
        total_committed_insts = 0
        total_l1i_accesses = 0
        total_l1i_misses = 0
        total_l1d_accesses = 0
        total_l1d_misses = 0
        total_l2_accesses = 0
        total_l2_misses = 0
        total_branches = 0
        total_branch_mispreds = 0

        # Energy accumulators (power * time for each dump)
        energy_cpu_dyn = 0.0
        energy_cpu_st = 0.0
        energy_icache_dyn = 0.0
        energy_icache_st = 0.0
        energy_dcache_dyn = 0.0
        energy_dcache_st = 0.0
        energy_l2_dyn = 0.0
        energy_l2_st = 0.0

        for dump in dumps:
            dt = self._extract_stat(dump, r'simSeconds\s+([\d.]+)')
            if dt <= 0:
                continue

            total_sim_seconds += dt
            total_sim_ticks += self._extract_stat(dump, r'sim_ticks\s+([\d]+)')
            total_cycles += self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.numCycles\s+([\d]+)')

            # Sum committed instructions (commitStats0.numInsts)
            insts = self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.commitStats0\.numInsts\s+([\d]+)')
            total_committed_insts += insts

            # Cache counters
            total_l1i_accesses += self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.icache\.overallAccesses::total\s+([\d]+)')
            total_l1i_misses += self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.icache\.overallMisses::total\s+([\d]+)')
            total_l1d_accesses += self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.dcache\.overallAccesses::total\s+([\d]+)')
            total_l1d_misses += self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.dcache\.overallMisses::total\s+([\d]+)')
            total_l2_accesses += self._extract_stat(dump,
                r'system\.cpu_cluster\.l2cache\.overallAccesses::total\s+([\d]+)')
            total_l2_misses += self._extract_stat(dump,
                r'system\.cpu_cluster\.l2cache\.overallMisses::total\s+([\d]+)')

            # Branch prediction
            total_branches += self._extract_stat(dump,
                r'branchPred\.condPredicted\s+([\d]+)')
            total_branch_mispreds += self._extract_stat(dump,
                r'branchPred\.condIncorrect\s+([\d]+)')

            # Power: accumulate energy (power * time) per dump
            cpu_dyn = self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.power_model\.dynamicPower\s+([\d.eE+-]+)')
            cpu_st = self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.power_model\.staticPower\s+([\d.eE+-]+)')
            icache_dyn = self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.icache\.power_model\.dynamicPower\s+([\d.eE+-]+)')
            icache_st = self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.icache\.power_model\.staticPower\s+([\d.eE+-]+)')
            dcache_dyn = self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.dcache\.power_model\.dynamicPower\s+([\d.eE+-]+)')
            dcache_st = self._extract_stat(dump,
                r'system\.cpu_cluster\.cpus\.dcache\.power_model\.staticPower\s+([\d.eE+-]+)')
            l2_dyn = self._extract_stat(dump,
                r'system\.cpu_cluster\.l2cache\.power_model\.dynamicPower\s+([\d.eE+-]+)')
            l2_st = self._extract_stat(dump,
                r'system\.cpu_cluster\.l2cache\.power_model\.staticPower\s+([\d.eE+-]+)')

            energy_cpu_dyn += cpu_dyn * dt
            energy_cpu_st += cpu_st * dt
            energy_icache_dyn += icache_dyn * dt
            energy_icache_st += icache_st * dt
            energy_dcache_dyn += dcache_dyn * dt
            energy_dcache_st += dcache_st * dt
            energy_l2_dyn += l2_dyn * dt
            energy_l2_st += l2_st * dt

        # Store aggregated results
        self.sim_seconds = total_sim_seconds
        self.sim_ticks = total_sim_ticks
        self.num_cycles = total_cycles

        # IPC from totals
        if total_cycles > 0:
            self.ipc = total_committed_insts / total_cycles

        # Cache metrics
        self.l1i_accesses = total_l1i_accesses
        self.l1i_misses = total_l1i_misses
        if self.l1i_accesses > 0:
            self.l1i_miss_rate = self.l1i_misses / self.l1i_accesses

        self.l1d_accesses = total_l1d_accesses
        self.l1d_misses = total_l1d_misses
        if self.l1d_accesses > 0:
            self.l1d_miss_rate = self.l1d_misses / self.l1d_accesses

        self.l2_accesses = total_l2_accesses
        self.l2_misses = total_l2_misses
        if self.l2_accesses > 0:
            self.l2_miss_rate = self.l2_misses / self.l2_accesses

        # Branch prediction
        self.branches = total_branches
        self.branch_mispreds = total_branch_mispreds
        if self.branches > 0:
            self.branch_mispredict_rate = self.branch_mispreds / self.branches

        # Average power = total energy / total time
        if total_sim_seconds > 0:
            self.cpu_dynamic_power = energy_cpu_dyn / total_sim_seconds
            self.cpu_static_power = energy_cpu_st / total_sim_seconds
            self.icache_dynamic_power = energy_icache_dyn / total_sim_seconds
            self.icache_static_power = energy_icache_st / total_sim_seconds
            self.dcache_dynamic_power = energy_dcache_dyn / total_sim_seconds
            self.dcache_static_power = energy_dcache_st / total_sim_seconds
            self.l2_dynamic_power = energy_l2_dyn / total_sim_seconds
            self.l2_static_power = energy_l2_st / total_sim_seconds

        # Calculate derived power metrics
        self.total_dynamic_power = (self.cpu_dynamic_power +
                                    self.icache_dynamic_power +
                                    self.dcache_dynamic_power +
                                    self.l2_dynamic_power)
        self.total_static_power = (self.cpu_static_power +
                                   self.icache_static_power +
                                   self.dcache_static_power +
                                   self.l2_static_power)
        self.total_power = self.total_dynamic_power + self.total_static_power
        if self.sim_seconds > 0:
            self.total_energy = self.total_power * self.sim_seconds
            self.edp = self.total_energy * self.sim_seconds

    def _extract_stat(self, content, pattern):
        """Extract a single statistic using regex."""
        match = re.search(pattern, content)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return 0.0
        return 0.0

    def has_power_data(self):
        """Check if power data was extracted."""
        return self.total_power > 0.0

    def print_summary(self):
        """Print summary of results."""
        print(f"\n{'='*70}")
        print(f"Results: {self.name}")
        print(f"{'='*70}")

        print(f"\nPerformance Metrics:")
        print(f"  Simulation Time:     {self.sim_seconds:.6f} seconds")
        print(f"  Simulation Cycles:   {int(self.num_cycles):,}")
        print(f"  IPC:                 {self.ipc:.4f}")

        print(f"\nCache Performance:")
        print(f"  L1 I-cache:")
        print(f"    Accesses:          {int(self.l1i_accesses):,}")
        print(f"    Misses:            {int(self.l1i_misses):,}")
        print(f"    Miss Rate:         {self.l1i_miss_rate*100:.2f}%")
        print(f"  L1 D-cache:")
        print(f"    Accesses:          {int(self.l1d_accesses):,}")
        print(f"    Misses:            {int(self.l1d_misses):,}")
        print(f"    Miss Rate:         {self.l1d_miss_rate*100:.2f}%")

        if self.l2_accesses > 0:
            print(f"  L2 Cache:")
            print(f"    Accesses:          {int(self.l2_accesses):,}")
            print(f"    Misses:            {int(self.l2_misses):,}")
            print(f"    Miss Rate:         {self.l2_miss_rate*100:.2f}%")

        print(f"\nBranch Prediction:")
        print(f"  Total Branches:      {int(self.branches):,}")
        print(f"  Mispredictions:      {int(self.branch_mispreds):,}")
        print(f"  Mispredict Rate:     {self.branch_mispredict_rate*100:.2f}%")

        if self.has_power_data():
            print(f"\nPower Analysis:")
            print(f"  CPU:")
            print(f"    Dynamic Power:     {self.cpu_dynamic_power:.6f} W")
            print(f"    Static Power:      {self.cpu_static_power:.6f} W")
            print(f"  I-cache:")
            print(f"    Dynamic Power:     {self.icache_dynamic_power:.6f} W")
            print(f"    Static Power:      {self.icache_static_power:.6f} W")
            print(f"  D-cache:")
            print(f"    Dynamic Power:     {self.dcache_dynamic_power:.6f} W")
            print(f"    Static Power:      {self.dcache_static_power:.6f} W")
            if self.l2_dynamic_power > 0 or self.l2_static_power > 0:
                print(f"  L2 Cache:")
                print(f"    Dynamic Power:     {self.l2_dynamic_power:.6f} W")
                print(f"    Static Power:      {self.l2_static_power:.6f} W")
            print(f"  Total Dynamic Power: {self.total_dynamic_power:.6f} W")
            print(f"  Total Static Power:  {self.total_static_power:.6f} W")
            print(f"  Total Power:         {self.total_power:.6f} W")
            print(f"  Total Energy:        {self.total_energy:.9f} J")
            print(f"  EDP:                 {self.edp:.12f} J*s")


def compare_configurations(results):
    """Compare multiple configurations and print analysis."""
    print("\n" + "="*70)
    print("Comparative Analysis")
    print("="*70)

    if len(results) < 2:
        print("Need at least 2 configurations for comparison.")
        return

    # Find baseline (MinorCPU L1, perf-level 0)
    baseline = None
    for r in results:
        if 'minor' in r.name.lower() and 'l2' not in r.name.lower() and r.perf_level == 0:
            baseline = r
            break
    if not baseline:
        baseline = results[0]

    # Performance comparison table
    print(f"\nBaseline: {baseline.name}")
    print(f"\n{'Configuration':<30} {'Time (s)':<12} {'Speedup':<10} {'IPC':<8} {'L1D Miss%':<10}")
    print("-" * 75)

    for r in results:
        speedup = baseline.sim_seconds / r.sim_seconds if r.sim_seconds > 0 else 0
        print(f"{r.name:<30} {r.sim_seconds:<12.6f} {f'{speedup:.2f}x':<10} "
              f"{r.ipc:<8.4f} {f'{r.l1d_miss_rate*100:.2f}%':<10}")

    # Power comparison (if available)
    has_power = any(r.has_power_data() for r in results)
    if has_power:
        print(f"\n{'Configuration':<30} {'Power (W)':<12} {'Energy (J)':<14} {'EDP (J*s)':<16}")
        print("-" * 75)
        for r in results:
            if r.has_power_data():
                print(f"{r.name:<30} {r.total_power:<12.4f} "
                      f"{r.total_energy:<14.6f} {r.edp:<16.9f}")
            else:
                print(f"{r.name:<30} {'N/A':<12} {'N/A':<14} {'N/A':<16}")

        # Power breakdown
        print(f"\n{'Configuration':<30} {'Dynamic (W)':<14} {'Static (W)':<14} {'Dyn/Total':<10}")
        print("-" * 75)
        for r in results:
            if r.has_power_data():
                dyn_ratio = r.total_dynamic_power / r.total_power if r.total_power > 0 else 0
                print(f"{r.name:<30} {r.total_dynamic_power:<14.4f} "
                      f"{r.total_static_power:<14.4f} {f'{dyn_ratio*100:.1f}%':<10}")


def dvfs_comparison(results):
    """DVFS-specific comparison tables showing V^2 scaling trends."""
    print("\n" + "="*70)
    print("DVFS Power-Performance-Energy Analysis")
    print("="*70)

    # Group results by architecture config
    arch_groups = {}
    for r in results:
        # Extract arch key (e.g. "MinorCPU L1" from "MinorCPU L1 P0")
        # We stored perf_level, so we can group by name prefix
        parts = r.name.rsplit(' ', 1)
        arch_key = parts[0] if len(parts) > 1 else r.name
        if arch_key not in arch_groups:
            arch_groups[arch_key] = {}
        arch_groups[arch_key][r.perf_level] = r

    for arch_name, levels in sorted(arch_groups.items()):
        if len(levels) < 2:
            continue

        print(f"\n--- {arch_name} ---")
        print(f"{'Level':<8} {'V/f':<18} {'Time (s)':<12} {'IPC':<8} "
              f"{'Power (W)':<12} {'Energy (J)':<14} {'EDP (J*s)':<16}")
        print("-" * 95)

        perf0 = levels.get(0)

        for pl in sorted(levels.keys()):
            r = levels[pl]
            dvfs = DVFS_POINTS[pl]
            vf_str = f"{dvfs['voltage']}/{dvfs['freq']}"

            edp_str = f"{r.edp:.9f}" if r.edp > 0 else "N/A"
            energy_str = f"{r.total_energy:.6f}" if r.total_energy > 0 else "N/A"
            power_str = f"{r.total_power:.4f}" if r.has_power_data() else "N/A"

            print(f"P{pl:<7} {vf_str:<18} {r.sim_seconds:<12.6f} {r.ipc:<8.4f} "
                  f"{power_str:<12} {energy_str:<14} {edp_str:<16}")

        # Show V^2 scaling analysis
        if perf0 and perf0.has_power_data() and perf0.cpu_dynamic_power > 0:
            print(f"\n  V^2 scaling check (dynamic power relative to P0):")
            for pl in sorted(levels.keys()):
                r = levels[pl]
                if not r.has_power_data():
                    continue
                v0 = DVFS_POINTS[0]['voltage_val']
                v = DVFS_POINTS[pl]['voltage_val']
                expected_ratio = (v / v0) ** 2
                actual_ratio = (r.cpu_dynamic_power / perf0.cpu_dynamic_power
                                if perf0.cpu_dynamic_power > 0 else 0)
                print(f"    P{pl}: V^2 expected ratio = {expected_ratio:.3f}, "
                      f"actual CPU dyn ratio = {actual_ratio:.3f}")

        # EDP comparison
        edp_levels = {pl: r for pl, r in levels.items() if r.edp > 0}
        if len(edp_levels) >= 2:
            best_pl = min(edp_levels, key=lambda pl: edp_levels[pl].edp)
            best = edp_levels[best_pl]
            p0 = edp_levels.get(0)
            if p0 and best_pl != 0:
                improvement = (1 - best.edp / p0.edp) * 100
                print(f"\n  Best EDP: P{best_pl} ({DVFS_POINTS[best_pl]['label']}) "
                      f"-- {improvement:.1f}% better than P0 (High-Perf)")


def print_optimization_summary(results):
    """Print the optimization story and recommendations."""
    print("\n" + "="*70)
    print("Optimization Summary & Recommendations")
    print("="*70)

    power_results = [r for r in results if r.has_power_data() and r.edp > 0]
    if not power_results:
        print("No power data available for optimization analysis.")
        return

    # Find best EDP overall
    best_edp = min(power_results, key=lambda r: r.edp)
    # Find lowest power
    lowest_power = min(power_results, key=lambda r: r.total_power)
    # Find fastest
    fastest = min(power_results, key=lambda r: r.sim_seconds)

    print(f"\n1. Best Performance (lowest latency):")
    print(f"   {fastest.name}")
    print(f"   Time: {fastest.sim_seconds:.6f}s, Power: {fastest.total_power:.4f}W, "
          f"Energy: {fastest.total_energy:.6f}J")

    print(f"\n2. Lowest Power Consumption:")
    print(f"   {lowest_power.name}")
    print(f"   Time: {lowest_power.sim_seconds:.6f}s, Power: {lowest_power.total_power:.4f}W, "
          f"Energy: {lowest_power.total_energy:.6f}J")

    print(f"\n3. Best Energy-Delay Product (optimal tradeoff):")
    print(f"   {best_edp.name}")
    print(f"   Time: {best_edp.sim_seconds:.6f}s, Power: {best_edp.total_power:.4f}W, "
          f"Energy: {best_edp.total_energy:.6f}J, EDP: {best_edp.edp:.9f}J*s")

    # Compare P0 vs P1 for the best arch config
    # Extract arch from best_edp name
    arch_key = best_edp.name.rsplit(' ', 1)[0]
    same_arch = [r for r in power_results if r.name.startswith(arch_key)]
    p0 = next((r for r in same_arch if r.perf_level == 0), None)

    if p0 and best_edp.perf_level != 0:
        power_save = (1 - best_edp.total_power / p0.total_power) * 100
        energy_save = (1 - best_edp.total_energy / p0.total_energy) * 100
        edp_save = (1 - best_edp.edp / p0.edp) * 100
        time_cost = (best_edp.sim_seconds / p0.sim_seconds - 1) * 100

        dvfs_label = DVFS_POINTS[best_edp.perf_level]['label']
        print(f"\n4. DVFS Optimization Story:")
        print(f"   Running {arch_key} at {dvfs_label} "
              f"({DVFS_POINTS[best_edp.perf_level]['voltage']}/{DVFS_POINTS[best_edp.perf_level]['freq']}) "
              f"vs High-Perf (1.2V/2GHz):")
        print(f"   - Power reduction:  {power_save:.1f}%")
        print(f"   - Energy savings:   {energy_save:.1f}%")
        print(f"   - EDP improvement:  {edp_save:.1f}%")
        print(f"   - Performance cost: +{time_cost:.1f}% execution time")
        print(f"   This is the optimal operating point for edge computing.")


def main():
    """Main analysis function."""
    print("="*70)
    print("Edge Pre-processing Microprocessor - Results Analysis")
    print("Phase 3: DVFS Optimization")
    print("="*70)

    # Define all 12 configurations
    configs = [
        ("MinorCPU L1 P0", "m5out_minor_l1_perf0/stats.txt", 0),
        ("MinorCPU L1 P1", "m5out_minor_l1_perf1/stats.txt", 1),
        ("MinorCPU L1 P2", "m5out_minor_l1_perf2/stats.txt", 2),
        ("MinorCPU L2 P0", "m5out_minor_l2_perf0/stats.txt", 0),
        ("MinorCPU L2 P1", "m5out_minor_l2_perf1/stats.txt", 1),
        ("MinorCPU L2 P2", "m5out_minor_l2_perf2/stats.txt", 2),
        ("O3CPU L1 P0",    "m5out_o3_l1_perf0/stats.txt",    0),
        ("O3CPU L1 P1",    "m5out_o3_l1_perf1/stats.txt",    1),
        ("O3CPU L1 P2",    "m5out_o3_l1_perf2/stats.txt",    2),
        ("O3CPU L2 P0",    "m5out_o3_l2_perf0/stats.txt",    0),
        ("O3CPU L2 P1",    "m5out_o3_l2_perf1/stats.txt",    1),
        ("O3CPU L2 P2",    "m5out_o3_l2_perf2/stats.txt",    2),
    ]

    # Load results
    results = []
    for name, stats_file, perf_level in configs:
        if Path(stats_file).exists():
            r = SimulationResults(name, stats_file, perf_level)
            results.append(r)
            r.print_summary()
        else:
            print(f"\nWarning: {stats_file} not found. Skipping {name}.")

    # Comparative analysis
    if results:
        compare_configurations(results)
        dvfs_comparison(results)
        print_optimization_summary(results)
    else:
        print("\nNo simulation results found. Please run simulations first.")

    print("\n" + "="*70)
    print("Analysis complete!")
    print("="*70)


if __name__ == '__main__':
    main()
