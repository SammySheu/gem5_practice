#!/usr/bin/env python3

"""
Multi-core ARM MinorCPU configuration for DAXPY TLP experiments.

Explores the FloatSimdFU design space by varying opLat and issueLat.

Usage:
    build/ARM/gem5.opt configs/practice/Assignment6/multicore_minor_daxpy.py \
        --num-cores 4 --op-lat 3 --issue-lat 4 \
        --binary configs/practice/Assignment6/daxpy_mt_arm
"""

import argparse
import sys

import m5
from m5.objects import *

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Multi-core MinorCPU DAXPY simulation"
)
parser.add_argument(
    "--num-cores", type=int, default=2,
    help="Number of CPU cores (default: 2)"
)
parser.add_argument(
    "--op-lat", type=int, default=6,
    help="FloatSimdFU operation latency in cycles (default: 6)"
)
parser.add_argument(
    "--issue-lat", type=int, default=1,
    help="FloatSimdFU issue latency in cycles (default: 1)"
)
parser.add_argument(
    "--binary", type=str, required=True,
    help="Path to the DAXPY binary"
)
parser.add_argument(
    "--array-size", type=int, default=10000,
    help="Array size for DAXPY (default: 10000)"
)

args = parser.parse_args()

# ---------------------------------------------------------------------------
# Cache definitions
# ---------------------------------------------------------------------------
class L1ICache(Cache):
    size = "32KiB"
    assoc = 2
    tag_latency = 1
    data_latency = 1
    response_latency = 1
    mshrs = 4
    tgts_per_mshr = 8

class L1DCache(Cache):
    size = "32KiB"
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 1
    mshrs = 16
    tgts_per_mshr = 16

class L2Cache(Cache):
    size = "256KiB"
    assoc = 8
    tag_latency = 10
    data_latency = 10
    response_latency = 5
    mshrs = 20
    tgts_per_mshr = 12

# ---------------------------------------------------------------------------
# Custom FU pool with parameterized FloatSimdFU
# ---------------------------------------------------------------------------
def create_fu_pool(op_lat, issue_lat):
    """Create a MinorFUPool with custom FloatSimdFU latencies."""
    float_simd = MinorDefaultFloatSimdFU()
    float_simd.opLat = op_lat
    float_simd.issueLat = issue_lat

    pool = MinorFUPool()
    pool.funcUnits = [
        MinorDefaultIntFU(),
        MinorDefaultIntFU(),
        MinorDefaultIntMulFU(),
        MinorDefaultIntDivFU(),
        float_simd,
        MinorDefaultPredFU(),
        MinorDefaultMemFU(),
        MinorDefaultMiscFU(),
    ]
    return pool

# ---------------------------------------------------------------------------
# System setup
# ---------------------------------------------------------------------------
system = System()
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()
system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MiB")]
system.multi_thread = False

# Memory bus
system.membus = SystemXBar()

# L2 bus (shared across all cores)
system.l2bus = L2XBar()

# Shared L2 cache
system.l2cache = L2Cache()
system.l2cache.cpu_side = system.l2bus.mem_side_ports
system.l2cache.mem_side = system.membus.cpu_side_ports

# ---------------------------------------------------------------------------
# Create CPUs
# ---------------------------------------------------------------------------
num_cores = args.num_cores
system.cpu = [MinorCPU(cpu_id=i) for i in range(num_cores)]

for i, cpu in enumerate(system.cpu):
    # Assign custom FU pool with specified FloatSimdFU latencies
    cpu.executeFuncUnits = create_fu_pool(args.op_lat, args.issue_lat)

    # Private L1 caches per core
    cpu.icache = L1ICache()
    cpu.dcache = L1DCache()

    # Connect L1 caches to CPU ports
    cpu.icache.cpu_side = cpu.icache_port
    cpu.dcache.cpu_side = cpu.dcache_port

    # Connect L1 caches to shared L2 bus
    cpu.icache.mem_side = system.l2bus.cpu_side_ports
    cpu.dcache.mem_side = system.l2bus.cpu_side_ports

    # Interrupt controller (required for ARM)
    cpu.createInterruptController()

# ---------------------------------------------------------------------------
# Workload and process
# ---------------------------------------------------------------------------
binary = args.binary
system.workload = SEWorkload.init_compatible(binary)

# Single process shared across all CPUs (threads share address space)
process = Process()
process.cmd = [binary, str(num_cores), str(args.array_size)]
process.executable = binary

for cpu in system.cpu:
    cpu.workload = process
    cpu.createThreads()

# Memory controller
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# System port
system.system_port = system.membus.cpu_side_ports

# ---------------------------------------------------------------------------
# Instantiate and run
# ---------------------------------------------------------------------------
root = Root(full_system=False, system=system)
m5.instantiate()

print(f"=== DAXPY Simulation ===")
print(f"Cores: {num_cores}")
print(f"FloatSimdFU: opLat={args.op_lat}, issueLat={args.issue_lat}")
print(f"Array size: {args.array_size}")
print(f"========================")

exit_event = m5.simulate()

print(f"\nSimulation done: {exit_event.getCause()}")
m5.stats.dump()
