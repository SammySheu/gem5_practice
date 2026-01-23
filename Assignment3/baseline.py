#!/usr/bin/env python3

"""
Baseline gem5 configuration for x86 architecture with default cache settings.
This configuration establishes a baseline for comparison with optimized configurations.
"""

import m5
from m5.objects import *

# Define cache classes
class L1_ICache(Cache):
    size = '16kB'
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20

class L1_DCache(Cache):
    size = '16kB'
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20
    
class L2Cache(Cache):
    size = '256kB'
    assoc = 8
    tag_latency = 20
    data_latency = 20
    response_latency = 20
    mshrs = 20
    tgts_per_mshr = 12

# Create the system
system = System()

# Set up clock domain
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = '1GHz'
system.clk_domain.voltage_domain = VoltageDomain()

# Set up memory
system.mem_mode = 'timing'
system.mem_ranges = [AddrRange('512MB')]

# Create CPU
system.cpu = TimingSimpleCPU()

# Create memory bus
system.membus = SystemXBar()

# Create cache hierarchy (default settings)
# L1 Instruction Cache
system.cpu.icache = L1_ICache()

# L1 Data Cache
system.cpu.dcache = L1_DCache()

# Connect L1 caches to CPU
system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port

# Create L2 cache bus
system.l2bus = L2XBar()

# Connect L1 caches to L2 bus
system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports

# L2 Cache (default settings)
system.l2cache = L2Cache()
system.l2cache.cpu_side = system.l2bus.mem_side_ports
system.l2cache.mem_side = system.membus.cpu_side_ports

# Create memory controller
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# Connect system port to memory bus
system.system_port = system.membus.cpu_side_ports

# Create interrupt controller for X86
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

# Set up workload
binary_path = 'configs/practice/Assignment3/Part2/benchmarks/hello_world'
system.workload = SEWorkload.init_compatible(binary_path)

# Create process
process = Process()
process.cmd = [binary_path]
system.cpu.workload = process
system.cpu.createThreads()

# Set up root
root = Root(full_system=False, system=system)

# Instantiate configuration
m5.instantiate()

# Run simulation
print("Starting baseline simulation...")
exit_event = m5.simulate()

print(f"Simulation completed: {exit_event.getCause()}")
print("\n=== Baseline Cache Statistics ===")

# Dump all statistics
m5.stats.dump()

