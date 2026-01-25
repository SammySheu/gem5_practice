#!/usr/bin/env python3

"""
Main simulation script using configurable baseline_v2 cache classes.
This script allows full control over cache parameters via command-line arguments.
"""

import m5
from m5.objects import *
import sys
import os
import argparse

# Import cache classes from baseline_v2
import baseline_v2
from baseline_v2 import L1ICache, L1DCache, L2Cache

# Add the common scripts to our path
m5.util.addToPath("../../")
from common import SimpleOpts

def create_system(opts):
    """Create a gem5 system with specified cache parameters from command line."""
    
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
    
    # Set system cache line size if specified
    if hasattr(opts, 'cache_line_size') and opts.cache_line_size:
        system.cache_line_size = int(opts.cache_line_size)
    
    # Create memory bus
    system.membus = SystemXBar()
    
    # Create cache hierarchy with parameters from command line
    # L1 Instruction Cache
    system.cpu.icache = L1ICache(opts)
    system.cpu.icache.connectCPU(system.cpu)
    
    # L1 Data Cache
    system.cpu.dcache = L1DCache(opts)
    system.cpu.dcache.connectCPU(system.cpu)
    
    # Create L2 cache bus
    system.l2bus = L2XBar()
    
    # Connect L1 caches to L2 bus
    system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
    system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports
    
    # L2 Cache
    system.l2cache = L2Cache(opts)
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
    
    return system

def run_simulation(opts):
    """Run a simulation with specified cache parameters."""
    
    # Print configuration
    print(f"\n{'='*70}")
    print(f"Cache Configuration:")
    print(f"{'='*70}")
    if hasattr(opts, 'l1i_size') and opts.l1i_size:
        print(f"  L1 I-Cache Size: {opts.l1i_size}")
    else:
        print(f"  L1 I-Cache Size: 16KiB (default)")
    
    if hasattr(opts, 'l1d_size') and opts.l1d_size:
        print(f"  L1 D-Cache Size: {opts.l1d_size}")
    else:
        print(f"  L1 D-Cache Size: 64KiB (default)")
    
    if hasattr(opts, 'l2_size') and opts.l2_size:
        print(f"  L2 Cache Size: {opts.l2_size}")
    else:
        print(f"  L2 Cache Size: 256KiB (default)")
    
    if hasattr(opts, 'l1_assoc') and opts.l1_assoc:
        print(f"  L1 Associativity: {opts.l1_assoc}")
    else:
        print(f"  L1 Associativity: 2 (default)")
    
    if hasattr(opts, 'l2_assoc') and opts.l2_assoc:
        print(f"  L2 Associativity: {opts.l2_assoc}")
    else:
        print(f"  L2 Associativity: 8 (default)")
    
    if hasattr(opts, 'cache_line_size') and opts.cache_line_size:
        print(f"  Cache Line Size: {opts.cache_line_size} bytes")
    else:
        print(f"  Cache Line Size: 64 bytes (default)")
    print(f"{'='*70}\n")
    
    system = create_system(opts)
    
    # Set up workload
    binary_path = opts.binary if hasattr(opts, 'binary') and opts.binary else 'configs/practice/Assignment3/matrix_benchmark'
    
    if not os.path.exists(binary_path):
        print(f"Error: Binary not found at {binary_path}")
        print("Please compile the benchmark first:")
        print("  gcc -O2 -static configs/practice/Assignment3/matrix_benchmark.c -o configs/practice/Assignment3/matrix_benchmark -lm")
        sys.exit(1)
    
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
    
    print("Running simulation...")
    print("-" * 70)
    
    # Run simulation
    exit_event = m5.simulate()
    
    print(f"\nSimulation completed: {exit_event.getCause()}")
    
    # Dump statistics
    m5.stats.dump()
    
    # Parse and display statistics
    parse_and_display_stats(opts)

def parse_and_display_stats(opts):
    """Parse statistics from m5out/stats.txt and display results."""
    
    stats_file = 'm5out/stats.txt'
    stats = {}
    sim_ticks = 0
    sim_seconds = 0
    
    try:
        with open(stats_file, 'r') as f:
            for line in f:
                if 'simTicks' in line and 'system.cpu.dtb.walker.walkRequestLatency_ticks::total' not in line:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == 'simTicks':
                        sim_ticks = int(parts[1])
                elif 'simSeconds' in line:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == 'simSeconds':
                        sim_seconds = float(parts[1])
                elif 'system.cpu.dcache.overallHits::total' in line:
                    stats['dcache_hits'] = int(line.split()[1])
                elif 'system.cpu.dcache.overallMisses::total' in line:
                    stats['dcache_misses'] = int(line.split()[1])
                elif 'system.cpu.icache.overallHits::total' in line:
                    stats['icache_hits'] = int(line.split()[1])
                elif 'system.cpu.icache.overallMisses::total' in line:
                    stats['icache_misses'] = int(line.split()[1])
                elif 'system.l2cache.overallHits::total' in line:
                    stats['l2_hits'] = int(line.split()[1])
                elif 'system.l2cache.overallMisses::total' in line:
                    stats['l2_misses'] = int(line.split()[1])
    except FileNotFoundError:
        print(f"Warning: Could not find {stats_file}")
        return
    
    # Calculate hit rates
    icache_total = stats.get('icache_hits', 0) + stats.get('icache_misses', 0)
    icache_hit_rate = (stats.get('icache_hits', 0) / icache_total * 100) if icache_total > 0 else 0
    
    dcache_total = stats.get('dcache_hits', 0) + stats.get('dcache_misses', 0)
    dcache_hit_rate = (stats.get('dcache_hits', 0) / dcache_total * 100) if dcache_total > 0 else 0
    
    l2_total = stats.get('l2_hits', 0) + stats.get('l2_misses', 0)
    l2_hit_rate = (stats.get('l2_hits', 0) / l2_total * 100) if l2_total > 0 else 0
    
    # Display results
    print(f"\n{'='*70}")
    print(f"Simulation Results:")
    print(f"{'='*70}")
    print(f"  Simulation Time: {sim_ticks:,} ticks ({sim_seconds:.6f} seconds)")
    print(f"\n  L1 Instruction Cache:")
    print(f"    Hits: {stats.get('icache_hits', 0):,}")
    print(f"    Misses: {stats.get('icache_misses', 0):,}")
    print(f"    Hit Rate: {icache_hit_rate:.2f}%")
    print(f"\n  L1 Data Cache:")
    print(f"    Hits: {stats.get('dcache_hits', 0):,}")
    print(f"    Misses: {stats.get('dcache_misses', 0):,}")
    print(f"    Hit Rate: {dcache_hit_rate:.2f}%")
    print(f"\n  L2 Cache:")
    print(f"    Hits: {stats.get('l2_hits', 0):,}")
    print(f"    Misses: {stats.get('l2_misses', 0):,}")
    print(f"    Hit Rate: {l2_hit_rate:.2f}%")
    print(f"{'='*70}\n")
    
    # Save results to CSV if config_name specified
    if hasattr(opts, 'config_name') and opts.config_name:
        save_results_csv(opts, stats, sim_ticks, sim_seconds, 
                        icache_hit_rate, dcache_hit_rate, l2_hit_rate)

def save_results_csv(opts, stats, sim_ticks, sim_seconds, 
                     icache_hit_rate, dcache_hit_rate, l2_hit_rate):
    """Save results to individual CSV file."""
    import csv
    
    # Create results dictionary
    results = {
        'config': opts.config_name if hasattr(opts, 'config_name') and opts.config_name else 'default',
        'l1i_size': opts.l1i_size if hasattr(opts, 'l1i_size') and opts.l1i_size else '16KiB',
        'l1d_size': opts.l1d_size if hasattr(opts, 'l1d_size') and opts.l1d_size else '64KiB',
        'l2_size': opts.l2_size if hasattr(opts, 'l2_size') and opts.l2_size else '256KiB',
        'l1_assoc': opts.l1_assoc if hasattr(opts, 'l1_assoc') and opts.l1_assoc else 2,
        'l2_assoc': opts.l2_assoc if hasattr(opts, 'l2_assoc') and opts.l2_assoc else 8,
        'cache_line_size': opts.cache_line_size if hasattr(opts, 'cache_line_size') and opts.cache_line_size else 64,
        'sim_ticks': sim_ticks,
        'sim_seconds': sim_seconds,
        'icache_hits': stats.get('icache_hits', 0),
        'icache_misses': stats.get('icache_misses', 0),
        'icache_hit_rate': f'{icache_hit_rate:.2f}',
        'dcache_hits': stats.get('dcache_hits', 0),
        'dcache_misses': stats.get('dcache_misses', 0),
        'dcache_hit_rate': f'{dcache_hit_rate:.2f}',
        'l2_hits': stats.get('l2_hits', 0),
        'l2_misses': stats.get('l2_misses', 0),
        'l2_hit_rate': f'{l2_hit_rate:.2f}'
    }
    
    # Determine output directory and filename
    if hasattr(opts, 'output_dir') and opts.output_dir:
        output_dir = opts.output_dir
    else:
        output_dir = 'configs/practice/Assignment3/results_v2'
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate individual result filename
    config_name = opts.config_name if hasattr(opts, 'config_name') and opts.config_name else 'default'
    result_file = os.path.join(output_dir, f'{config_name}_result.csv')
    
    # Write individual result file
    with open(result_file, 'w', newline='') as csvfile:
        fieldnames = list(results.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(results)
    
    print(f"Results saved to {result_file}")

if __name__ == '__m5_main__':
    # Add custom arguments
    SimpleOpts.add_option(
        '--binary',
        help='Path to binary to execute. Default: configs/practice/Assignment3/matrix_benchmark'
    )
    SimpleOpts.add_option(
        '--config_name',
        help='Configuration name for this experiment (used for individual result filename)'
    )
    SimpleOpts.add_option(
        '--output_dir',
        help='Output directory for individual result files. Default: configs/practice/Assignment3/results_v2'
    )
    
    # Parse arguments
    args = SimpleOpts.parse_args()
    
    # Run simulation
    run_simulation(args)


