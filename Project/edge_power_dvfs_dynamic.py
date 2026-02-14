#!/usr/bin/env python3
"""
Dynamic Phase-Aware DVFS in SE Mode

Demonstrates that dynamic DVFS does NOT require full-system mode.
The workload is instrumented with gem5 m5_work_begin() pseudo-instructions
at each pipeline phase boundary. This config catches those exit events
and switches the CPU's V/f operating point per phase.

DVFS Policy:
  Phase 0 (data generation):      P1 Balanced  (1.2GHz / 1.0V) -- light compute
  Phase 1 (moving average filter): P0 High-Perf (2.0GHz / 1.2V) -- compute-intensive
  Phase 2 (anomaly detection):     P2 Low-Power (600MHz / 0.8V) -- simple comparisons
  Phase 3 (cross-sensor fusion):   P2 Low-Power (600MHz / 0.8V) -- memory-bound
  Phase 4 (aggregate stats):       P2 Low-Power (600MHz / 0.8V) -- simple accumulation
  Phase 5 (normalize data):        P2 Low-Power (600MHz / 0.8V) -- simple arithmetic
  Phase 6 (per-sensor stats):      P1 Balanced  (1.2GHz / 1.0V) -- moderate compute

Hypothesis: Only the filter phase (Phase 1) needs max performance.
Everything else can run at reduced V/f with negligible time penalty
(because those phases are memory-bound or lightweight).

Usage:
    gem5 edge_power_dvfs_dynamic.py --cpu-type=minor --binary=workloads/edge_preprocessing_dvfs_arm
    gem5 edge_power_dvfs_dynamic.py --cpu-type=o3 --l2-cache --binary=workloads/edge_preprocessing_dvfs_arm
"""

import argparse
import sys
import os

import m5
from m5.objects import *


# ==============================================================================
# DVFS Policy: phase_id -> performance level
# ==============================================================================

PHASE_NAMES = {
    0: 'Generate Data',
    1: 'Moving Avg Filter',
    2: 'Anomaly Detection',
    3: 'Cross-Sensor Fusion',
    4: 'Aggregate Stats',
    5: 'Normalize Data',
    6: 'Per-Sensor Stats',
}

DVFS_POLICY = {
    0: 1,  # Generate data      -> Balanced  (1.2GHz/1.0V)
    1: 0,  # Moving avg filter  -> High-Perf (2.0GHz/1.2V)
    2: 2,  # Anomaly detection  -> Low-Power (600MHz/0.8V)
    3: 2,  # Cross-sensor fusion-> Low-Power (600MHz/0.8V)
    4: 2,  # Aggregate stats    -> Low-Power (600MHz/0.8V)
    5: 2,  # Normalize data     -> Low-Power (600MHz/0.8V)
    6: 1,  # Per-sensor stats   -> Balanced  (1.2GHz/1.0V)
}

DVFS_LABELS = {0: 'P0 High-Perf', 1: 'P1 Balanced', 2: 'P2 Low-Power'}


# ==============================================================================
# Power Model Definitions (same as edge_power_config.py)
# ==============================================================================

class CpuPowerOn(MathExprPowerModel):
    def __init__(self, cpu_path, **kwargs):
        super().__init__(**kwargs)
        self.dyn = (
            "voltage * voltage * "
            "(2.0 * {}.ipc + "
            "0.003 * {}.dcache.overallMisses / simSeconds)".format(
                cpu_path, cpu_path)
        )
        self.st = "0.1 + (4.0 * 0.001 * temp)"

class CpuPowerClkGated(MathExprPowerModel):
    def __init__(self, cpu_path, **kwargs):
        super().__init__(**kwargs)
        self.dyn = (
            "voltage * voltage * "
            "(0.4 * {}.ipc + "
            "0.0006 * {}.dcache.overallMisses / simSeconds)".format(
                cpu_path, cpu_path)
        )
        self.st = "0.1 + (4.0 * 0.001 * temp)"

class CpuPowerSRAMRetention(MathExprPowerModel):
    def __init__(self, cpu_path, **kwargs):
        super().__init__(**kwargs)
        self.dyn = "0.005"
        self.st = "0.01 + (0.4 * 0.001 * temp)"

class CpuPowerOff(MathExprPowerModel):
    dyn = "0.0"
    st = "0.0"

class CpuPowerModel(PowerModel):
    def __init__(self, cpu_path, **kwargs):
        super().__init__(**kwargs)
        self.pm = [
            CpuPowerOn(cpu_path),
            CpuPowerClkGated(cpu_path),
            CpuPowerSRAMRetention(cpu_path),
            CpuPowerOff(),
        ]

class CachePowerOn(MathExprPowerModel):
    def __init__(self, cache_path, **kwargs):
        super().__init__(**kwargs)
        self.dyn = (
            "voltage * voltage * 0.00005 * "
            "({}.overallAccesses / simSeconds)".format(cache_path)
        )
        self.st = "0.05 + (2.0 * 0.001 * temp)"

class CachePowerDrowsy(MathExprPowerModel):
    def __init__(self, cache_path, **kwargs):
        super().__init__(**kwargs)
        self.dyn = "0.001"
        self.st = "0.005 + (0.2 * 0.001 * temp)"

class CachePowerOff(MathExprPowerModel):
    dyn = "0.0"
    st = "0.0"

class CachePowerModel(PowerModel):
    def __init__(self, cache_path, **kwargs):
        super().__init__(**kwargs)
        self.pm = [
            CachePowerOn(cache_path),
            CachePowerDrowsy(cache_path),
            CachePowerDrowsy(cache_path),
            CachePowerOff(),
        ]


# ==============================================================================
# Cache Definitions
# ==============================================================================

class L1ICache(Cache):
    assoc = 2; tag_latency = 1; data_latency = 1; response_latency = 1
    mshrs = 4; tgts_per_mshr = 20; size = '16kB'
    def connectCPU(self, cpu): self.cpu_side = cpu.icache_port
    def connectBus(self, bus):  self.mem_side = bus.cpu_side_ports

class L1DCache(Cache):
    assoc = 4; tag_latency = 2; data_latency = 2; response_latency = 2
    mshrs = 4; tgts_per_mshr = 20; size = '32kB'; writeback_clean = False
    def connectCPU(self, cpu): self.cpu_side = cpu.dcache_port
    def connectBus(self, bus):  self.mem_side = bus.cpu_side_ports

class L2Cache(Cache):
    size = '256kB'; assoc = 8; tag_latency = 12; data_latency = 12
    response_latency = 12; mshrs = 20; tgts_per_mshr = 12
    writeback_clean = False
    def connectCPUSideBus(self, bus): self.cpu_side = bus.mem_side_ports
    def connectMemSideBus(self, bus): self.mem_side = bus.cpu_side_ports


# ==============================================================================
# System Creation
# ==============================================================================

def create_system(args):
    system = System()
    system.voltage_domain = VoltageDomain(voltage='1.2V')
    system.clk_domain = SrcClockDomain(clock='2GHz',
                                        voltage_domain=system.voltage_domain)
    system.mem_mode = 'timing'
    system.mem_ranges = [AddrRange('4GB')]

    # Enable exit on every m5_work_begin pseudo-instruction
    system.exit_on_work_items = True

    # CPU cluster with multi-V/f DVFS domain
    system.cpu_cluster = CpuCluster()
    system.cpu_cluster.voltage_domain = VoltageDomain(
        voltage=['1.2V', '1.0V', '0.8V']
    )
    system.cpu_cluster.clk_domain = SrcClockDomain(
        clock=['2GHz', '1.2GHz', '600MHz'],
        voltage_domain=system.cpu_cluster.voltage_domain,
        domain_id=0,
        init_perf_level=0  # Start at high-perf
    )

    if args.cpu_type == 'minor':
        system.cpu_cluster.generate_cpus(MinorCPU, 1)
    elif args.cpu_type == 'o3':
        system.cpu_cluster.generate_cpus(ArmO3CPU, 1)
    else:
        print(f"Error: Unknown CPU type '{args.cpu_type}'")
        sys.exit(1)

    cpu = system.cpu_cluster.cpus[0]

    if args.cpu_type == 'o3':
        cpu.numROBEntries = 128
        cpu.numPhysIntRegs = 128
        cpu.numPhysFloatRegs = 128
        cpu.LQEntries = 32
        cpu.SQEntries = 32

    cpu.power_gating_on_idle = True
    cpu.pwr_gating_latency = 300
    cpu.power_state.possible_states = ['ON', 'CLK_GATED', 'SRAM_RETENTION', 'OFF']

    cpu.icache = L1ICache()
    cpu.icache.power_state.possible_states = ['ON', 'CLK_GATED', 'SRAM_RETENTION', 'OFF']
    cpu.dcache = L1DCache()
    cpu.dcache.power_state.possible_states = ['ON', 'CLK_GATED', 'SRAM_RETENTION', 'OFF']

    cpu.icache.connectCPU(cpu)
    cpu.dcache.connectCPU(cpu)

    if args.l2_cache:
        system.cpu_cluster.l2bus = L2XBar()
        cpu.icache.connectBus(system.cpu_cluster.l2bus)
        cpu.dcache.connectBus(system.cpu_cluster.l2bus)
        system.cpu_cluster.l2cache = L2Cache()
        system.cpu_cluster.l2cache.power_state.possible_states = [
            'ON', 'CLK_GATED', 'SRAM_RETENTION', 'OFF'
        ]
        system.cpu_cluster.l2cache.connectCPUSideBus(system.cpu_cluster.l2bus)
        system.membus = SystemXBar()
        system.cpu_cluster.l2cache.connectMemSideBus(system.membus)
    else:
        system.membus = SystemXBar()
        cpu.icache.connectBus(system.membus)
        cpu.dcache.connectBus(system.membus)

    system.dvfs_handler = DVFSHandler(
        domains=[system.cpu_cluster.clk_domain],
        enable=True,
        transition_latency='50us'
    )

    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR4_2400_8x8()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports
    system.system_port = system.membus.cpu_side_ports

    system.workload = SEWorkload.init_compatible(args.binary)
    process = Process()
    process.cmd = [args.binary]
    cpu.workload = process

    return system


def apply_power_models(system):
    cpu = system.cpu_cluster.cpus[0]
    cpu.power_state.default_state = "ON"
    cpu.power_model = CpuPowerModel(cpu.path())
    cpu.icache.power_state.default_state = "ON"
    cpu.icache.power_model = CachePowerModel(cpu.icache.path())
    cpu.dcache.power_state.default_state = "ON"
    cpu.dcache.power_model = CachePowerModel(cpu.dcache.path())
    if hasattr(system.cpu_cluster, 'l2cache'):
        l2 = system.cpu_cluster.l2cache
        l2.power_state.default_state = "ON"
        l2.power_model = CachePowerModel(l2.path())


# ==============================================================================
# Main: Dynamic DVFS Simulation Loop
# ==============================================================================

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Dynamic Phase-Aware DVFS Simulation (SE mode)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--cpu-type', type=str, default='minor',
                       choices=['minor', 'o3'])
    parser.add_argument('--l2-cache', action='store_true')
    parser.add_argument('--binary', type=str,
                       default='workloads/edge_preprocessing_dvfs_arm')
    return parser.parse_args()


def main():
    args = parse_arguments()

    if not os.path.exists(args.binary):
        print(f"Error: Binary '{args.binary}' not found!")
        sys.exit(1)

    print("="*80)
    print("Dynamic Phase-Aware DVFS Simulation (SE Mode)")
    print("="*80)
    print(f"CPU Type: {args.cpu_type.upper()}")
    print(f"L2 Cache: {'Enabled' if args.l2_cache else 'Disabled'}")
    print(f"Binary: {args.binary}")
    print(f"\nDVFS Policy:")
    for phase_id in sorted(DVFS_POLICY.keys()):
        level = DVFS_POLICY[phase_id]
        print(f"  Phase {phase_id} ({PHASE_NAMES[phase_id]:<22s}) -> {DVFS_LABELS[level]}")
    print("="*80)

    system = create_system(args)
    root = Root(full_system=False, system=system)
    apply_power_models(system)

    m5.instantiate()

    # Run simulation with dynamic DVFS switching
    print("\nStarting simulation with dynamic DVFS...")
    dvfs_handler = root.system.dvfs_handler
    phase_transitions = 0

    while True:
        exit_event = m5.simulate()
        cause = exit_event.getCause()

        if cause == "workbegin":
            # Get phase ID from exit code
            phase_id = exit_event.getCode()
            perf_level = DVFS_POLICY.get(phase_id, 0)

            print(f"  [tick {m5.curTick():>15,}] Phase {phase_id} "
                  f"({PHASE_NAMES.get(phase_id, '?')}) -> {DVFS_LABELS[perf_level]}")

            # Switch V/f via DVFSHandler (non-overloaded wrapper)
            dvfs_handler.setPerfLevel(0, perf_level)
            phase_transitions += 1
        else:
            # Simulation ended (workload exited)
            break

    print("\n" + "="*80)
    print("Simulation Complete!")
    print("="*80)
    print(f"Simulated time: {m5.curTick() / 1e12:.6f} seconds")
    print(f"Exit reason: {cause}")
    print(f"Phase transitions: {phase_transitions}")
    print(f"  (3 rounds x 7 phases = 21 expected)")
    print("="*80)


if __name__ == '__m5_main__':
    main()
