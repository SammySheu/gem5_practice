from m5.objects import *
from m5.util import addToPath
from m5.objects.X86CPU import X86MinorCPU
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--cmd", required=True, help="binary to run")
args = parser.parse_args()

# 1) 建立系統
system = System()
system.clk_domain = SrcClockDomain(clock="1GHz", voltage_domain=VoltageDomain())
system.mem_mode = "timing"          # MinorCPU 需要 timing mode
system.mem_ranges = [AddrRange("512MB")]

# 2) CPU: MinorCPU (X86)
system.cpu = X86MinorCPU()

# 3) 匯流排 + 記憶體控制器（直接連接，不使用 cache）
system.membus = SystemXBar()
system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports

# 為 X86 建立並連接 interrupt controller
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# 5) Workload (SE mode)
process = Process()
process.cmd = [args.cmd]
system.cpu.workload = process
system.cpu.createThreads()

system.system_port = system.membus.cpu_side_ports

# 設定系統層級的 workload（重要！）
system.workload = SEWorkload.init_compatible(args.cmd)

root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
