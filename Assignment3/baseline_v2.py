# Copyright (c) 2015 Jason Power
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Configurable cache classes for gem5 cache optimization experiments

This file contains L1 I/D and L2 cache classes with full command-line
configurability for size, associativity, and block size parameters.
All cache parameters can be specified via command-line arguments.
"""

import m5
from m5.objects import Cache

# Add the common scripts to our path
m5.util.addToPath("../../")

from common import SimpleOpts

# Some specific options for caches
# For all options see src/mem/cache/BaseCache.py


class L1Cache(Cache):
    """Configurable L1 Cache with command-line options"""

    # Default parameters
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20

    # Add command-line options for L1 cache parameters
    SimpleOpts.add_option(
        "--l1_assoc", 
        help="L1 cache associativity. Default: 2"
    )
    SimpleOpts.add_option(
        "--cache_line_size",
        help="Cache line/block size in bytes. Default: 64"
    )

    def __init__(self, options=None):
        super().__init__()
        if options:
            # Set associativity if specified
            if hasattr(options, 'l1_assoc') and options.l1_assoc:
                self.assoc = int(options.l1_assoc)

    def connectBus(self, bus):
        """Connect this cache to a memory-side bus"""
        self.mem_side = bus.cpu_side_ports

    def connectCPU(self, cpu):
        """Connect this cache's port to a CPU-side port
        This must be defined in a subclass"""
        raise NotImplementedError


class L1ICache(L1Cache):
    """Configurable L1 instruction cache"""

    # Set the default size
    size = "16KiB"

    SimpleOpts.add_option(
        "--l1i_size", 
        help=f"L1 instruction cache size. Default: {size}"
    )

    def __init__(self, opts=None):
        super().__init__(opts)
        if opts and hasattr(opts, 'l1i_size') and opts.l1i_size:
            self.size = opts.l1i_size

    def connectCPU(self, cpu):
        """Connect this cache's port to a CPU icache port"""
        self.cpu_side = cpu.icache_port


class L1DCache(L1Cache):
    """Configurable L1 data cache"""

    # Set the default size
    size = "64KiB"

    SimpleOpts.add_option(
        "--l1d_size", 
        help=f"L1 data cache size. Default: {size}"
    )

    def __init__(self, opts=None):
        super().__init__(opts)
        if opts and hasattr(opts, 'l1d_size') and opts.l1d_size:
            self.size = opts.l1d_size

    def connectCPU(self, cpu):
        """Connect this cache's port to a CPU dcache port"""
        self.cpu_side = cpu.dcache_port


class L2Cache(Cache):
    """Configurable L2 Cache with command-line options"""

    # Default parameters
    size = "256KiB"
    assoc = 8
    tag_latency = 20
    data_latency = 20
    response_latency = 20
    mshrs = 20
    tgts_per_mshr = 12

    # Add command-line options for L2 cache parameters
    SimpleOpts.add_option(
        "--l2_size", 
        help=f"L2 cache size. Default: {size}"
    )
    SimpleOpts.add_option(
        "--l2_assoc", 
        help=f"L2 cache associativity. Default: {assoc}"
    )

    def __init__(self, opts=None):
        super().__init__()
        if opts:
            # Set size if specified
            if hasattr(opts, 'l2_size') and opts.l2_size:
                self.size = opts.l2_size
            
            # Set associativity if specified
            if hasattr(opts, 'l2_assoc') and opts.l2_assoc:
                self.assoc = int(opts.l2_assoc)

    def connectCPUSideBus(self, bus):
        self.cpu_side = bus.mem_side_ports

    def connectMemSideBus(self, bus):
        self.mem_side = bus.cpu_side_ports
