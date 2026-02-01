#!/usr/bin/env python3
"""
Edge Pre-processing Microprocessor Simulation with Power Modeling
Phase 2 Implementation: ARM-based gem5 simulation with MathExprPowerModel

This configuration implements the architectural specifications from Phase 1:
- MinorCPU (in-order baseline) vs O3CPU (out-of-order comparison)
- Explicit power modeling with multiple power states
- ARM ISA (ARMv8-A 64-bit)
- Configurable cache hierarchy (L1 only or L1+L2)

Usage:
    gem5 edge_power_config.py --cpu-type=minor --binary=workloads/edge_preprocessing_arm
    gem5 edge_power_config.py --cpu-type=o3 --binary=workloads/edge_preprocessing_arm --l2-cache
"""

import argparse
import sys
import os

import m5
from m5.objects import *


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
    
    # Set up voltage and clock domains
    system.voltage_domain = VoltageDomain(voltage='1.2V')
    system.clk_domain = SrcClockDomain(
        clock='2GHz',
        voltage_domain=system.voltage_domain
    )
    
    # Set memory mode and ranges
    system.mem_mode = 'timing'
    system.mem_ranges = [AddrRange('4GB')]
    
    # Create CPU
    if args.cpu_type == 'minor':
        system.cpu = MinorCPU()
    elif args.cpu_type == 'o3':
        system.cpu = ArmO3CPU()
        # Configure O3 parameters (using gem5 parameter names)
        system.cpu.numROBEntries = 128
        system.cpu.numPhysIntRegs = 128
        system.cpu.numPhysFloatRegs = 128
        system.cpu.LQEntries = 32
        system.cpu.SQEntries = 32
        # Note: Issue queues configured via instQueues (using defaults)
    else:
        print(f"Error: Unknown CPU type '{args.cpu_type}'")
        sys.exit(1)
    
    # Create interrupt controller for ARM
    system.cpu.createInterruptController()
    
    # Create caches
    
    system.cpu.icache = L1ICache()
    system.cpu.icache.size = '16kB'
    system.cpu.icache.assoc = 2
    system.cpu.dcache = L1DCache()
    system.cpu.dcache.size = '32kB'
    system.cpu.dcache.assoc = 4
    
    # Connect caches and create memory bus
    system.cpu.icache.connectCPU(system.cpu)
    system.cpu.dcache.connectCPU(system.cpu)
    
    # Optional L2 cache
    if args.l2_cache:
        system.l2bus = L2XBar()
        system.cpu.icache.connectBus(system.l2bus)
        system.cpu.dcache.connectBus(system.l2bus)
        
        system.l2cache = L2Cache()
        system.l2cache.connectCPUSideBus(system.l2bus)
        
        system.membus = SystemXBar()
        system.l2cache.connectMemSideBus(system.membus)
    else:
        system.membus = SystemXBar()
        system.cpu.icache.connectBus(system.membus)
        system.cpu.dcache.connectBus(system.membus)
    
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
    system.cpu.workload = process
    system.cpu.createThreads()
    
    return system


def apply_power_models(root):
    """Apply power models to CPU after system is built."""
    
    print("Applying power models...")
    
    # Apply power model to CPU only
    # (Cache power modeling requires additional subsystem configuration)
    for cpu in root.system.descendants():
        if not isinstance(cpu, BaseCPU):
            continue
        cpu.power_state.default_state = "ON"
        cpu.power_model = CpuPowerModel(cpu.path())
        print(f"  Applied CPU power model to: {cpu.path()}")


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
    
    parser.add_argument('--power-models', action='store_true', default=False,
                       help='Enable power modeling (requires full-system mode)')
    
    parser.add_argument('--stat-freq', type=float, default=0.001,
                       help='Frequency (in seconds) to dump stats')
    
    return parser.parse_args()


def main():
    """Main simulation entry point."""
    args = parse_arguments()
    
    # Validate binary exists
    if not os.path.exists(args.binary):
        print(f"Error: Binary '{args.binary}' not found!")
        print(f"Current directory: {os.getcwd()}")
        sys.exit(1)
    
    # Print configuration
    print("="*80)
    print("Edge Pre-processing Microprocessor Simulation")
    print("Phase 2: ARM with Power Modeling")
    print("="*80)
    print(f"CPU Type: {args.cpu_type.upper()}")
    print(f"L2 Cache: {'Enabled' if args.l2_cache else 'Disabled'}")
    print(f"Binary: {args.binary}")
    print(f"Power Models: {'Enabled' if args.power_models else 'Disabled'}")
    print(f"Stat Dump Frequency: {args.stat_freq} seconds")
    print("="*80)
    
    # Create system
    system = create_system(args)
    
    # Create root object
    root = Root(full_system=False, system=system)
    
    # Apply power models if enabled
    if args.power_models:
        apply_power_models(root)
    
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
    print("="*80)


if __name__ == '__m5_main__':
    main()
