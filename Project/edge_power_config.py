#!/usr/bin/env python3
"""
Edge Pre-processing Microprocessor Simulation with Power Modeling
Phase 3: DVFS Optimization with Power-Performance-Energy Tradeoffs

This configuration implements:
- MinorCPU (in-order baseline) vs O3CPU (out-of-order comparison)
- Explicit power modeling with multiple power states
- ARM ISA (ARMv8-A 64-bit)
- Configurable cache hierarchy (L1 only or L1+L2)
- DVFS operating points for power-performance exploration

Usage:
    gem5 edge_power_config.py --cpu-type=minor --binary=workloads/edge_preprocessing_arm
    gem5 edge_power_config.py --cpu-type=o3 --l2-cache --perf-level=2
"""

import argparse
import sys
import os

import m5
from m5.objects import *


# ==============================================================================
# DVFS Operating Points
# ==============================================================================

DVFS_POINTS = {
    0: {'freq': '2GHz',    'voltage': '1.2V', 'label': 'High Performance'},
    1: {'freq': '1.2GHz',  'voltage': '1.0V', 'label': 'Balanced'},
    2: {'freq': '600MHz',  'voltage': '0.8V', 'label': 'Low Power'},
}


# ==============================================================================
# Power Model Definitions
# ==============================================================================

class CpuPowerOn(MathExprPowerModel):
    """Power model for CPU in ON state (active processing)."""
    def __init__(self, cpu_path, **kwargs):
        super().__init__(**kwargs)
        # Dynamic power: IPC-dependent + cache miss penalty
        self.dyn = (
            "voltage * voltage * "
            "(2.0 * {}.ipc + "
            "0.003 * {}.dcache.overallMisses / simSeconds)".format(
                cpu_path, cpu_path)
        )
        # Static power: Temperature-dependent leakage
        self.st = "0.1 + (4.0 * 0.001 * temp)"


class CpuPowerClkGated(MathExprPowerModel):
    """Power model for CPU in CLK_GATED state (clock gating active)."""
    def __init__(self, cpu_path, **kwargs):
        super().__init__(**kwargs)
        # Reduced dynamic power (20% of ON state)
        self.dyn = (
            "voltage * voltage * "
            "(0.4 * {}.ipc + "
            "0.0006 * {}.dcache.overallMisses / simSeconds)".format(
                cpu_path, cpu_path)
        )
        # Same leakage as ON state
        self.st = "0.1 + (4.0 * 0.001 * temp)"


class CpuPowerSRAMRetention(MathExprPowerModel):
    """Power model for CPU in SRAM_RETENTION state (cache drowsy mode)."""
    def __init__(self, cpu_path, **kwargs):
        super().__init__(**kwargs)
        # Minimal dynamic power
        self.dyn = "0.005"
        # Reduced leakage: ~10% of ON state
        self.st = "0.01 + (0.4 * 0.001 * temp)"


class CpuPowerOff(MathExprPowerModel):
    """Power model for CPU in OFF state (power gating active)."""
    dyn = "0.0"
    st = "0.0"


class CpuPowerModel(PowerModel):
    """Complete CPU power model combining all power states."""
    def __init__(self, cpu_path, **kwargs):
        super().__init__(**kwargs)
        self.pm = [
            CpuPowerOn(cpu_path),            # State 0: ON
            CpuPowerClkGated(cpu_path),      # State 1: CLK_GATED
            CpuPowerSRAMRetention(cpu_path), # State 2: SRAM_RETENTION
            CpuPowerOff(),                   # State 3: OFF
        ]


class CachePowerOn(MathExprPowerModel):
    """Power model for cache in ON state."""
    def __init__(self, cache_path, **kwargs):
        super().__init__(**kwargs)
        # Dynamic: Access-dependent
        self.dyn = (
            "voltage * voltage * 0.00005 * "
            "({}.overallAccesses / simSeconds)".format(cache_path)
        )
        # Static: SRAM leakage
        self.st = "0.05 + (2.0 * 0.001 * temp)"


class CachePowerDrowsy(MathExprPowerModel):
    """Power model for cache in drowsy/retention mode."""
    def __init__(self, cache_path, **kwargs):
        super().__init__(**kwargs)
        self.dyn = "0.001"
        self.st = "0.005 + (0.2 * 0.001 * temp)"


class CachePowerOff(MathExprPowerModel):
    """Power model for cache powered off."""
    dyn = "0.0"
    st = "0.0"


class CachePowerModel(PowerModel):
    """Complete cache power model for all power states."""
    def __init__(self, cache_path, **kwargs):
        super().__init__(**kwargs)
        self.pm = [
            CachePowerOn(cache_path),      # ON
            CachePowerDrowsy(cache_path),  # CLK_GATED
            CachePowerDrowsy(cache_path),  # SRAM_RETENTION
            CachePowerOff(),               # OFF
        ]


# ==============================================================================
# Cache Definitions (based on learning_gem5 examples)
# ==============================================================================

class L1ICache(Cache):
    """L1 Instruction Cache"""
    assoc = 2
    tag_latency = 1
    data_latency = 1
    response_latency = 1
    mshrs = 4
    tgts_per_mshr = 20
    size = '16kB'

    def connectCPU(self, cpu):
        """Connect to CPU icache port"""
        self.cpu_side = cpu.icache_port

    def connectBus(self, bus):
        """Connect to memory bus"""
        self.mem_side = bus.cpu_side_ports


class L1DCache(Cache):
    """L1 Data Cache"""
    assoc = 4
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20
    size = '32kB'
    writeback_clean = False

    def connectCPU(self, cpu):
        """Connect to CPU dcache port"""
        self.cpu_side = cpu.dcache_port

    def connectBus(self, bus):
        """Connect to memory bus"""
        self.mem_side = bus.cpu_side_ports


class L2Cache(Cache):
    """L2 Unified Cache"""
    size = '256kB'
    assoc = 8
    tag_latency = 12
    data_latency = 12
    response_latency = 12
    mshrs = 20
    tgts_per_mshr = 12
    writeback_clean = False

    def connectCPUSideBus(self, bus):
        self.cpu_side = bus.mem_side_ports

    def connectMemSideBus(self, bus):
        self.mem_side = bus.cpu_side_ports


# ==============================================================================
# System Configuration Functions
# ==============================================================================

def create_system(args):
    """Create the system based on command-line arguments."""

    # Create base system
    system = System()

    # Set up system-level voltage and clock domains
    system.voltage_domain = VoltageDomain(voltage='1.2V')
    system.clk_domain = SrcClockDomain(
        clock='2GHz',
        voltage_domain=system.voltage_domain
    )

    # Set memory mode and ranges
    system.mem_mode = 'timing'
    system.mem_ranges = [AddrRange('4GB')]

    # Create CPU cluster with multi-V/f DVFS domain
    system.cpu_cluster = CpuCluster()
    system.cpu_cluster.voltage_domain = VoltageDomain(
        voltage=['1.2V', '1.0V', '0.8V']
    )
    system.cpu_cluster.clk_domain = SrcClockDomain(
        clock=['2GHz', '1.2GHz', '600MHz'],
        voltage_domain=system.cpu_cluster.voltage_domain,
        domain_id=0,
        init_perf_level=args.perf_level
    )

    # Create CPU inside the cluster
    if args.cpu_type == 'minor':
        system.cpu_cluster.generate_cpus(MinorCPU, 1)
    elif args.cpu_type == 'o3':
        system.cpu_cluster.generate_cpus(ArmO3CPU, 1)
    else:
        print(f"Error: Unknown CPU type '{args.cpu_type}'")
        sys.exit(1)

    # generate_cpus() already calls createThreads() and createInterruptController()
    cpu = system.cpu_cluster.cpus[0]

    # Configure O3 parameters after generation
    if args.cpu_type == 'o3':
        cpu.numROBEntries = 128
        cpu.numPhysIntRegs = 128
        cpu.numPhysFloatRegs = 128
        cpu.LQEntries = 32
        cpu.SQEntries = 32

    # Enable power gating on idle and declare possible power states
    cpu.power_gating_on_idle = True
    cpu.pwr_gating_latency = 300
    cpu.power_state.possible_states = ['ON', 'CLK_GATED', 'SRAM_RETENTION', 'OFF']

    # Create caches
    cpu.icache = L1ICache()
    cpu.icache.size = '16kB'
    cpu.icache.assoc = 2
    cpu.icache.power_state.possible_states = ['ON', 'CLK_GATED', 'SRAM_RETENTION', 'OFF']

    cpu.dcache = L1DCache()
    cpu.dcache.size = '32kB'
    cpu.dcache.assoc = 4
    cpu.dcache.power_state.possible_states = ['ON', 'CLK_GATED', 'SRAM_RETENTION', 'OFF']

    # Connect caches to CPU
    cpu.icache.connectCPU(cpu)
    cpu.dcache.connectCPU(cpu)

    # Optional L2 cache (inside cluster so power model finds SubSystem)
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

    # DVFS handler
    system.dvfs_handler = DVFSHandler(
        domains=[system.cpu_cluster.clk_domain],
        enable=True,
        transition_latency='50us'
    )

    # Create memory controller
    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR4_2400_8x8()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports

    # Connect system port
    system.system_port = system.membus.cpu_side_ports

    # Set up workload
    system.workload = SEWorkload.init_compatible(args.binary)

    process = Process()
    process.cmd = [args.binary]
    cpu.workload = process

    return system


def apply_power_models(system):
    """Apply power models to CPU and caches."""

    print("Applying power models...")

    cpu = system.cpu_cluster.cpus[0]

    # CPU power model
    cpu.power_state.default_state = "ON"
    cpu.power_model = CpuPowerModel(cpu.path())
    print(f"  Applied CPU power model to: {cpu.path()}")

    # I-cache power model
    cpu.icache.power_state.default_state = "ON"
    cpu.icache.power_model = CachePowerModel(cpu.icache.path())
    print(f"  Applied cache power model to: {cpu.icache.path()}")

    # D-cache power model
    cpu.dcache.power_state.default_state = "ON"
    cpu.dcache.power_model = CachePowerModel(cpu.dcache.path())
    print(f"  Applied cache power model to: {cpu.dcache.path()}")

    # L2 cache power model (if present)
    if hasattr(system.cpu_cluster, 'l2cache'):
        l2 = system.cpu_cluster.l2cache
        l2.power_state.default_state = "ON"
        l2.power_model = CachePowerModel(l2.path())
        print(f"  Applied cache power model to: {l2.path()}")


# ==============================================================================
# Main Simulation Setup
# ==============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Edge Pre-processing Microprocessor Simulation with Power Modeling',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument('--cpu-type', type=str, default='minor',
                       choices=['minor', 'o3'],
                       help='CPU type: minor (in-order) or o3 (out-of-order)')

    parser.add_argument('--l2-cache', action='store_true',
                       help='Enable L2 cache (256 KB, 8-way)')

    parser.add_argument('--binary', type=str,
                       default='workloads/edge_preprocessing_arm',
                       help='Path to ARM binary to execute')

    parser.add_argument('--power-models', action=argparse.BooleanOptionalAction,
                       default=True,
                       help='Enable power modeling (use --no-power-models to disable)')

    parser.add_argument('--stat-freq', type=float, default=0.001,
                       help='Frequency (in seconds) to dump stats')

    parser.add_argument('--perf-level', type=int, default=0,
                       choices=[0, 1, 2],
                       help='DVFS performance level: 0=High(2GHz/1.2V), '
                            '1=Balanced(1.2GHz/1.0V), 2=LowPower(600MHz/0.8V)')

    return parser.parse_args()


def main():
    """Main simulation entry point."""
    args = parse_arguments()

    # Validate binary exists
    if not os.path.exists(args.binary):
        print(f"Error: Binary '{args.binary}' not found!")
        print(f"Current directory: {os.getcwd()}")
        sys.exit(1)

    # Get DVFS point info
    dvfs = DVFS_POINTS[args.perf_level]

    # Print configuration
    print("="*80)
    print("Edge Pre-processing Microprocessor Simulation")
    print("Phase 3: DVFS Optimization")
    print("="*80)
    print(f"CPU Type: {args.cpu_type.upper()}")
    print(f"L2 Cache: {'Enabled' if args.l2_cache else 'Disabled'}")
    print(f"Binary: {args.binary}")
    print(f"Power Models: {'Enabled' if args.power_models else 'Disabled'}")
    print(f"Stat Dump Frequency: {args.stat_freq} seconds")
    print(f"DVFS Perf Level: {args.perf_level} ({dvfs['label']})")
    print(f"  Frequency: {dvfs['freq']}")
    print(f"  Voltage: {dvfs['voltage']}")
    print("="*80)

    # Create system
    system = create_system(args)

    # Create root object
    root = Root(full_system=False, system=system)

    # Apply power models if enabled
    if args.power_models:
        apply_power_models(system)

    # Instantiate simulation
    m5.instantiate()

    # Set up periodic stat dumps
    m5.stats.reset()
    m5.stats.periodicStatDump(m5.ticks.fromSeconds(args.stat_freq))

    # Run simulation
    print("\nStarting simulation...")
    exit_event = m5.simulate()

    # Print results
    print("\n" + "="*80)
    print("Simulation Complete!")
    print("="*80)
    print(f"Simulated time: {m5.curTick() / 1e12:.6f} seconds")
    print(f"Exit reason: {exit_event.getCause()}")
    print(f"DVFS Level: {args.perf_level} ({dvfs['label']}, {dvfs['freq']}, {dvfs['voltage']})")
    print("="*80)


if __name__ == '__m5_main__':
    main()
