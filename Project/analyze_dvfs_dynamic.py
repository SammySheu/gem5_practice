#!/usr/bin/env python3
"""
Analysis: Dynamic Phase-Aware DVFS vs Static P0

Compares 4 arch configs x 2 modes (static P0 vs dynamic DVFS).
Shows that dynamic DVFS saves power with minimal performance cost.
"""

import re
from pathlib import Path


DVFS_POINTS = {
    0: {'freq': '2GHz',   'voltage': '1.2V', 'label': 'High-Perf'},
    1: {'freq': '1.2GHz', 'voltage': '1.0V', 'label': 'Balanced'},
    2: {'freq': '600MHz', 'voltage': '0.8V', 'label': 'Low-Power'},
}


class SimResult:
    """Parse and aggregate gem5 stats across all periodic dumps."""

    def __init__(self, name, stats_file):
        self.name = name
        self.stats_file = stats_file
        self.sim_seconds = 0.0
        self.num_cycles = 0
        self.num_insts = 0
        self.ipc = 0.0
        self.l1d_misses = 0
        self.l1d_accesses = 0
        self.l1d_miss_rate = 0.0
        self.cpu_dynamic_power = 0.0
        self.cpu_static_power = 0.0
        self.total_dynamic_power = 0.0
        self.total_static_power = 0.0
        self.total_power = 0.0
        self.total_energy = 0.0
        self.edp = 0.0
        self.parse()

    def parse(self):
        if not Path(self.stats_file).exists():
            print(f"  Warning: {self.stats_file} not found")
            return

        with open(self.stats_file) as f:
            content = f.read()

        dumps = re.split(r'-+ Begin Simulation Statistics -+\n', content)
        dumps = [d for d in dumps if d.strip()]

        total_time = 0.0
        total_cycles = 0
        total_insts = 0
        total_l1d_acc = 0
        total_l1d_miss = 0
        energy_cpu_dyn = 0.0
        energy_cpu_st = 0.0
        energy_icache_dyn = 0.0
        energy_icache_st = 0.0
        energy_dcache_dyn = 0.0
        energy_dcache_st = 0.0
        energy_l2_dyn = 0.0
        energy_l2_st = 0.0

        for dump in dumps:
            dt = self._get(dump, r'simSeconds\s+([\d.]+)')
            if dt <= 0:
                continue
            total_time += dt
            total_cycles += self._get(dump, r'cpu_cluster\.cpus\.numCycles\s+(\d+)')
            total_insts += self._get(dump, r'commitStats0\.numInsts\s+(\d+)')
            total_l1d_acc += self._get(dump, r'cpus\.dcache\.overallAccesses::total\s+(\d+)')
            total_l1d_miss += self._get(dump, r'cpus\.dcache\.overallMisses::total\s+(\d+)')

            cpu_d = self._get(dump, r'cpus\.power_model\.dynamicPower\s+([\d.eE+-]+)')
            cpu_s = self._get(dump, r'cpus\.power_model\.staticPower\s+([\d.eE+-]+)')
            ic_d = self._get(dump, r'icache\.power_model\.dynamicPower\s+([\d.eE+-]+)')
            ic_s = self._get(dump, r'icache\.power_model\.staticPower\s+([\d.eE+-]+)')
            dc_d = self._get(dump, r'dcache\.power_model\.dynamicPower\s+([\d.eE+-]+)')
            dc_s = self._get(dump, r'dcache\.power_model\.staticPower\s+([\d.eE+-]+)')
            l2_d = self._get(dump, r'l2cache\.power_model\.dynamicPower\s+([\d.eE+-]+)')
            l2_s = self._get(dump, r'l2cache\.power_model\.staticPower\s+([\d.eE+-]+)')

            energy_cpu_dyn += cpu_d * dt
            energy_cpu_st += cpu_s * dt
            energy_icache_dyn += ic_d * dt
            energy_icache_st += ic_s * dt
            energy_dcache_dyn += dc_d * dt
            energy_dcache_st += dc_s * dt
            energy_l2_dyn += l2_d * dt
            energy_l2_st += l2_s * dt

        self.sim_seconds = total_time
        self.num_cycles = total_cycles
        self.num_insts = total_insts
        if total_cycles > 0:
            self.ipc = total_insts / total_cycles
        self.l1d_accesses = total_l1d_acc
        self.l1d_misses = total_l1d_miss
        if total_l1d_acc > 0:
            self.l1d_miss_rate = total_l1d_miss / total_l1d_acc

        if total_time > 0:
            self.cpu_dynamic_power = energy_cpu_dyn / total_time
            self.cpu_static_power = energy_cpu_st / total_time
            self.total_dynamic_power = (energy_cpu_dyn + energy_icache_dyn +
                                        energy_dcache_dyn + energy_l2_dyn) / total_time
            self.total_static_power = (energy_cpu_st + energy_icache_st +
                                       energy_dcache_st + energy_l2_st) / total_time
            self.total_power = self.total_dynamic_power + self.total_static_power
            self.total_energy = self.total_power * total_time
            self.edp = self.total_energy * total_time

    def _get(self, text, pattern):
        m = re.search(pattern, text)
        return float(m.group(1)) if m else 0.0


def main():
    print("="*75)
    print("Dynamic Phase-Aware DVFS vs Static P0 -- Results Comparison")
    print("="*75)

    configs = [
        ("MinorCPU L1", "minorcpu_l1"),
        ("MinorCPU L2", "minorcpu_l2"),
        ("O3CPU L1",    "o3cpu_l1"),
        ("O3CPU L2",    "o3cpu_l2"),
    ]

    pairs = []
    for label, dir_key in configs:
        static_file = f"m5out_{dir_key}_static_p0/stats.txt"
        dynamic_file = f"m5out_{dir_key}_dynamic/stats.txt"

        s = SimResult(f"{label} Static-P0", static_file)
        d = SimResult(f"{label} Dynamic",   dynamic_file)

        if s.sim_seconds > 0 and d.sim_seconds > 0:
            pairs.append((label, s, d))
        else:
            if s.sim_seconds == 0:
                print(f"  Skipping {label}: static stats missing")
            if d.sim_seconds == 0:
                print(f"  Skipping {label}: dynamic stats missing")

    if not pairs:
        print("\nNo results found. Run simulations first with run_dvfs_dynamic.sh")
        return

    # --- Summary table ---
    print(f"\n{'Config':<16} {'Mode':<12} {'Time (ms)':<11} {'IPC':<8} "
          f"{'Power (W)':<12} {'Energy (J)':<12} {'EDP (J*s)':<12}")
    print("-" * 85)

    for label, s, d in pairs:
        print(f"{label:<16} {'Static P0':<12} {s.sim_seconds*1000:<11.3f} {s.ipc:<8.4f} "
              f"{s.total_power:<12.0f} {s.total_energy:<12.3f} {s.edp:<12.6f}")
        print(f"{'':<16} {'Dynamic':<12} {d.sim_seconds*1000:<11.3f} {d.ipc:<8.4f} "
              f"{d.total_power:<12.0f} {d.total_energy:<12.3f} {d.edp:<12.6f}")

    # --- Delta table ---
    print(f"\n{'Config':<16} {'Time Delta':<14} {'Power Delta':<14} "
          f"{'Energy Delta':<14} {'EDP Delta':<14}")
    print("-" * 75)

    for label, s, d in pairs:
        time_delta = (d.sim_seconds / s.sim_seconds - 1) * 100 if s.sim_seconds > 0 else 0
        power_delta = (d.total_power / s.total_power - 1) * 100 if s.total_power > 0 else 0
        energy_delta = (d.total_energy / s.total_energy - 1) * 100 if s.total_energy > 0 else 0
        edp_delta = (d.edp / s.edp - 1) * 100 if s.edp > 0 else 0

        time_str = f"{time_delta:+.1f}%"
        power_str = f"{power_delta:+.1f}%"
        energy_str = f"{energy_delta:+.1f}%"
        edp_str = f"{edp_delta:+.1f}%"

        print(f"{label:<16} {time_str:<14} {power_str:<14} {energy_str:<14} {edp_str:<14}")

    # --- Analysis ---
    print(f"\n{'='*75}")
    print("Analysis")
    print(f"{'='*75}")

    for label, s, d in pairs:
        time_overhead = (d.sim_seconds / s.sim_seconds - 1) * 100
        power_saving = (1 - d.total_power / s.total_power) * 100
        energy_saving = (1 - d.total_energy / s.total_energy) * 100
        edp_change = (d.edp / s.edp - 1) * 100

        print(f"\n{label}:")
        print(f"  Performance overhead: {time_overhead:+.1f}% execution time")
        print(f"  Power saving:        {power_saving:+.1f}%")
        print(f"  Energy saving:       {energy_saving:+.1f}%")
        print(f"  EDP change:          {edp_change:+.1f}%")

        if abs(time_overhead) < 10 and power_saving > 10:
            print(f"  -> SUCCESS: Significant power savings with minimal performance cost!")
        elif time_overhead > 10:
            print(f"  -> Performance overhead is notable. Policy may need tuning.")

    print(f"\n{'='*75}")
    print("Conclusion")
    print(f"{'='*75}")
    print("Dynamic phase-aware DVFS in SE mode adapts V/f per workload phase.")
    print("Compute-intensive phases (filter) run at full speed (2GHz/1.2V),")
    print("while memory-bound and lightweight phases run at reduced V/f,")
    print("saving power with minimal performance impact.")
    print(f"{'='*75}")


if __name__ == '__main__':
    main()
