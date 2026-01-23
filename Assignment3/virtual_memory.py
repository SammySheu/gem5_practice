#!/usr/bin/env python3

"""
Virtual memory configuration for gem5.
This script tests different page sizes and TLB configurations.
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

def create_system_with_vm(page_size='4kB', tlb_size=64, tlb_assoc=4):
    """Create a gem5 system with virtual memory enabled.
    
    Note: In SE (Syscall Emulation) mode, TLB configuration is limited.
    TLBs are created automatically and use default parameters.
    For full TLB control, full-system (FS) mode is required.
    """
    
    system = System()
    
    # Set up clock domain
    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = '1GHz'
    system.clk_domain.voltage_domain = VoltageDomain()
    
    # Set up memory
    system.mem_mode = 'timing'
    system.mem_ranges = [AddrRange('512MB')]
    
    # Create CPU with virtual memory support
    system.cpu = TimingSimpleCPU()
    
    # Note: In SE mode, TLBs are created automatically by the CPU
    # TLB configuration is handled internally for TimingSimpleCPU
    
    # Create memory bus
    system.membus = SystemXBar()
    
    # Create cache hierarchy
    system.cpu.icache = L1_ICache(size='16kB', assoc=2)
    system.cpu.dcache = L1_DCache(size='16kB', assoc=2)
    
    # Connect L1 caches to CPU
    system.cpu.icache.cpu_side = system.cpu.icache_port
    system.cpu.dcache.cpu_side = system.cpu.dcache_port
    
    # Create L2 cache bus
    system.l2bus = L2XBar()
    
    # Connect L1 caches to L2 bus
    system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
    system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports
    
    # L2 Cache
    system.l2cache = L2Cache(size='256kB', assoc=8)
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

def run_vm_simulation(config_name, page_size, tlb_size, tlb_assoc):
    """Run a simulation with specified virtual memory parameters."""
    
    print(f"\n{'='*60}")
    print(f"Virtual Memory Configuration: {config_name}")
    print(f"Page Size: {page_size}, TLB Size: {tlb_size}, TLB Associativity: {tlb_assoc}")
    print(f"{'='*60}")
    
    system = create_system_with_vm(page_size, tlb_size, tlb_assoc)
    
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
    exit_event = m5.simulate()
    
    # Dump statistics
    m5.stats.dump()
    
    # Parse statistics from m5out/stats.txt
    stats_file = 'm5out/stats.txt'
    stats = {
        'itlb_hits': 0,
        'itlb_misses': 0,
        'dtlb_hits': 0,
        'dtlb_misses': 0,
        'page_faults': 0
    }
    
    try:
        with open(stats_file, 'r') as f:
            itlb_accesses = 0
            dtlb_accesses = 0
            
            for line in f:
                # I-TLB statistics (instruction TLB)
                if 'system.cpu.mmu.itb.exAccesses' in line:
                    try:
                        itlb_accesses = int(line.split()[1])
                    except (ValueError, IndexError):
                        pass
                elif 'system.cpu.mmu.itb.exMisses' in line:
                    try:
                        stats['itlb_misses'] = int(line.split()[1])
                    except (ValueError, IndexError):
                        pass
                
                # D-TLB statistics (data TLB - read + write accesses)
                elif 'system.cpu.mmu.dtb.rdAccesses' in line:
                    try:
                        dtlb_accesses += int(line.split()[1])
                    except (ValueError, IndexError):
                        pass
                elif 'system.cpu.mmu.dtb.wrAccesses' in line:
                    try:
                        dtlb_accesses += int(line.split()[1])
                    except (ValueError, IndexError):
                        pass
                elif 'system.cpu.mmu.dtb.rdMisses' in line:
                    try:
                        stats['dtlb_misses'] += int(line.split()[1])
                    except (ValueError, IndexError):
                        pass
                elif 'system.cpu.mmu.dtb.wrMisses' in line:
                    try:
                        stats['dtlb_misses'] += int(line.split()[1])
                    except (ValueError, IndexError):
                        pass
            
            # Calculate hits from accesses and misses
            stats['itlb_hits'] = itlb_accesses - stats['itlb_misses']
            stats['dtlb_hits'] = dtlb_accesses - stats['dtlb_misses']
            
    except FileNotFoundError:
        print(f"Warning: Could not find {stats_file}")
    
    # Calculate hit rates
    itlb_total = stats['itlb_hits'] + stats['itlb_misses']
    itlb_hit_rate = (stats['itlb_hits'] / itlb_total * 100) if itlb_total > 0 else 0
    
    dtlb_total = stats['dtlb_hits'] + stats['dtlb_misses']
    dtlb_hit_rate = (stats['dtlb_hits'] / dtlb_total * 100) if dtlb_total > 0 else 0
    
    results = {
        'config': config_name,
        'page_size': page_size,
        'tlb_size': tlb_size,
        'tlb_assoc': tlb_assoc,
        'itlb_hits': stats['itlb_hits'],
        'itlb_misses': stats['itlb_misses'],
        'itlb_hit_rate': itlb_hit_rate,
        'dtlb_hits': stats['dtlb_hits'],
        'dtlb_misses': stats['dtlb_misses'],
        'dtlb_hit_rate': dtlb_hit_rate,
        'page_faults': stats['page_faults']
    }
    
    print(f"\nResults for {config_name}:")
    print(f"  I-TLB Hit Rate: {itlb_hit_rate:.2f}%")
    print(f"  D-TLB Hit Rate: {dtlb_hit_rate:.2f}%")
    print(f"  Page Faults: {stats['page_faults']}")
    
    return results

if __name__ == '__m5_main__':
    import argparse
    
    # Test configurations
    configurations = {
        # Page size variations
        'page_4kB': ('4kB', 64, 4),
        'page_8kB': ('8kB', 64, 4),
        'page_16kB': ('16kB', 64, 4),
        
        # TLB size variations
        'tlb_32': ('4kB', 32, 4),
        'tlb_64': ('4kB', 64, 4),  # Baseline
        'tlb_128': ('4kB', 128, 4),
        
        # TLB associativity variations
        'tlb_assoc_2': ('4kB', 64, 2),
        'tlb_assoc_4': ('4kB', 64, 4),  # Baseline
        'tlb_assoc_8': ('4kB', 64, 8),
    }
    
    parser = argparse.ArgumentParser(description='Run virtual memory experiments')
    parser.add_argument('config', nargs='?', default='tlb_64', 
                       choices=list(configurations.keys()),
                       help='Configuration name to run')
    
    args = parser.parse_args()
    config_name = args.config
    page_size, tlb_size, tlb_assoc = configurations[config_name]
    
    results = run_vm_simulation(config_name, page_size, tlb_size, tlb_assoc)
    
    # Save individual result
    import csv
    os.makedirs(os.path.join(base_folder, 'results'), exist_ok=True)
    result_file = f'{os.path.join(base_folder, "results")}/{config_name}_vm_result.csv'
    with open(result_file, 'w', newline='') as csvfile:
        fieldnames = ['config', 'page_size', 'tlb_size', 'tlb_assoc',
                     'itlb_hit_rate', 'dtlb_hit_rate', 'page_faults',
                     'itlb_hits', 'itlb_misses', 'dtlb_hits', 'dtlb_misses']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(results)
    print(f"\nResults saved to {result_file}")

