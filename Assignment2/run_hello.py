import m5
from m5.objects import *
from m5.util import addToPath

addToPath("../../../configs")

from common.Caches import *

# Create the system
system = System()
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

# Memory configuration
system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")]
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]

# CPU configuration
system.cpu = TimingSimpleCPU()
system.cpu.icache = L1_ICache(size="32kB")
system.cpu.dcache = L1_DCache(size="32kB")

# Connecting CPU and Memory
system.membus = SystemXBar()

# Connect CPU ports to cache cpu_side
system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port

# Connect cache mem_side to memory bus
system.cpu.icache.mem_side = system.membus.cpu_side_ports
system.cpu.dcache.mem_side = system.membus.cpu_side_ports

# Connect memory controller to memory bus
system.mem_ctrl.port = system.membus.mem_side_ports

# Connect system port to memory bus
system.system_port = system.membus.cpu_side_ports

# Create interrupt controller
system.cpu.createInterruptController()

# For X86, connect interrupts to the memory bus
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

# Setting up workload
system.workload = SEWorkload.init_compatible("hello")

# Create a process for the hello program
process = Process()
process.cmd = ["hello"]
system.cpu.workload = process
system.cpu.createThreads()

# Simulation Configuration
root = Root(full_system=False, system=system)
m5.instantiate()
print("Beginning simulation!")
exit_event = m5.simulate()
print("Exiting @ tick {} because {}".format(
m5.curTick(), exit_event.getCause()))