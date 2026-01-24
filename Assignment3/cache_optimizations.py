#!/usr/bin/env python3

"""
Cache optimization configurations for gem5.
This script tests various cache parameter combinations:
- Cache sizes: 8KB, 16KB, 32KB, 64KB
- Associativity: 1 (direct-mapped), 2, 4, 8, fully associative
- Block sizes: 16B, 32B, 64B, 128B
"""

import m5
from m5.objects import *
import sys
import os

base_folder = os.path.dirname(os.path.abspath(__file__))
# Define cache classes
class L1_ICache(Cache):
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20

class L1_DCache(Cache):
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20
    
class L2Cache(Cache):
    tag_latency = 20
    data_latency = 20
    response_latency = 20
    mshrs = 20
    tgts_per_mshr = 12

def create_system(cache_size='16kB', associativity=2, block_size=64):
    """Create a gem5 system with specified cache parameters."""
    
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
    
    # Create cache hierarchy with specified parameters
    # L1 Instruction Cache
    system.cpu.icache = L1_ICache(size=cache_size, assoc=associativity)
    
    # L1 Data Cache
    system.cpu.dcache = L1_DCache(size=cache_size, assoc=associativity)
    
    # Connect L1 caches to CPU
    system.cpu.icache.cpu_side = system.cpu.icache_port
    system.cpu.dcache.cpu_side = system.cpu.dcache_port
    
    # Create L2 cache bus
    system.l2bus = L2XBar()
    
    # Connect L1 caches to L2 bus
    system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
    system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports
    
    # L2 Cache (scaled proportionally)
    l2_size = f'{int(cache_size.split("k")[0]) * 16}kB'
    system.l2cache = L2Cache(size=l2_size, assoc=associativity * 4)
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

def run_simulation(config_name, cache_size, associativity, block_size):
    """Run a simulation with specified cache parameters."""
    
    print(f"\n{'='*60}")
    print(f"Configuration: {config_name}")
    print(f"Cache Size: {cache_size}, Associativity: {associativity}, Block Size: {block_size}B")
    print(f"{'='*60}")
    
    system = create_system(cache_size, associativity, block_size)
    
    # Set up workload
    binary_path = 'configs/practice/Assignment3/hello_world'
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
    exit_event = m5.simulate()
    
    # Dump statistics
    m5.stats.dump()
    
    # Parse statistics from m5out/stats.txt
    stats_file = 'm5out/stats.txt'
    stats = {}
    
    try:
        with open(stats_file, 'r') as f:
            for line in f:
                if 'system.cpu.dcache.overallHits::total' in line:
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
        stats = {'icache_hits': 0, 'icache_misses': 0, 'dcache_hits': 0, 
                'dcache_misses': 0, 'l2_hits': 0, 'l2_misses': 0}
    
    # Calculate hit rates
    icache_total = stats.get('icache_hits', 0) + stats.get('icache_misses', 0)
    icache_hit_rate = (stats.get('icache_hits', 0) / icache_total * 100) if icache_total > 0 else 0
    
    dcache_total = stats.get('dcache_hits', 0) + stats.get('dcache_misses', 0)
    dcache_hit_rate = (stats.get('dcache_hits', 0) / dcache_total * 100) if dcache_total > 0 else 0
    
    l2_total = stats.get('l2_hits', 0) + stats.get('l2_misses', 0)
    l2_hit_rate = (stats.get('l2_hits', 0) / l2_total * 100) if l2_total > 0 else 0
    
    results = {
        'config': config_name,
        'cache_size': cache_size,
        'associativity': associativity,
        'block_size': block_size,
        'icache_hits': stats.get('icache_hits', 0),
        'icache_misses': stats.get('icache_misses', 0),
        'icache_hit_rate': icache_hit_rate,
        'dcache_hits': stats.get('dcache_hits', 0),
        'dcache_misses': stats.get('dcache_misses', 0),
        'dcache_hit_rate': dcache_hit_rate,
        'l2_hits': stats.get('l2_hits', 0),
        'l2_misses': stats.get('l2_misses', 0),
        'l2_hit_rate': l2_hit_rate
    }
    
    print(f"\nResults for {config_name}:")
    print(f"  L1 I-Cache Hit Rate: {icache_hit_rate:.2f}%")
    print(f"  L1 D-Cache Hit Rate: {dcache_hit_rate:.2f}%")
    print(f"  L2 Cache Hit Rate: {l2_hit_rate:.2f}%")
    
    return results

if __name__ == '__m5_main__':
    import argparse
    
    # Test configurations
    configurations = {
        # Cache size variations (baseline: 16kB, assoc=2, block=64B)
        'size_8kB': ('8kB', 2, 64),
        'size_16kB': ('16kB', 2, 64),  # Baseline
        'size_32kB': ('32kB', 2, 64),
        'size_64kB': ('64kB', 2, 64),
        
        # Associativity variations (baseline: 16kB, assoc=2, block=64B)
        'assoc_1': ('16kB', 1, 64),    # Direct-mapped
        'assoc_2': ('16kB', 2, 64),    # Baseline
        'assoc_4': ('16kB', 4, 64),
        'assoc_8': ('16kB', 8, 64),
        
        # Block size variations (baseline: 16kB, assoc=2, block=64B)
        'block_16B': ('16kB', 2, 16),
        'block_32B': ('16kB', 2, 32),
        'block_64B': ('16kB', 2, 64),  # Baseline
        'block_128B': ('16kB', 2, 128),
    }
    
    parser = argparse.ArgumentParser(description='Run cache optimization experiments')
    parser.add_argument('config', nargs='?', default='size_16kB', 
                       choices=list(configurations.keys()),
                       help='Configuration name to run')
    
    args = parser.parse_args()
    config_name = args.config
    cache_size, associativity, block_size = configurations[config_name]
    
    results = run_simulation(config_name, cache_size, associativity, block_size)
    
    # Save individual result
    import csv
    os.makedirs(os.path.join(base_folder, 'results'), exist_ok=True)
    result_file = f'{os.path.join(base_folder, "results")}/{config_name}_result.csv'
    with open(result_file, 'w', newline='') as csvfile:
        fieldnames = ['config', 'cache_size', 'associativity', 'block_size',
                     'icache_hit_rate', 'dcache_hit_rate', 'l2_hit_rate',
                     'icache_hits', 'icache_misses', 'dcache_hits', 'dcache_misses',
                     'l2_hits', 'l2_misses']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(results)
    print(f"\nResults saved to {result_file}")

