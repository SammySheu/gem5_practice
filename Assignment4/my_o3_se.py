# configs/practice/Assignment4/my_o3_se.py
from m5.objects import *
import m5
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--cmd", required=True, help="binary to run")
parser.add_argument("--args", default="", help="arguments for the binary")
parser.add_argument("--cpu-clock", default="1GHz")
parser.add_argument("--mem-size", default="512MB")

# Superscalar knobs (single-core)
parser.add_argument("--fetchWidth", type=int, default=4)
parser.add_argument("--decodeWidth", type=int, default=4)
parser.add_argument("--renameWidth", type=int, default=4)
parser.add_argument("--dispatchWidth", type=int, default=4)
parser.add_argument("--issueWidth", type=int, default=4)
parser.add_argument("--commitWidth", type=int, default=4)

# SMT knobs
parser.add_argument("--threads", type=int, default=1, help="num HW threads")
parser.add_argument("--smt", action="store_true", help="enable SMT policy knobs")

# Branch predictor
parser.add_argument("--bp", choices=["none", "simple"], default="simple")

args = parser.parse_args()

# -----------------------
# 1) System
# -----------------------
system = System()
system.clk_domain = SrcClockDomain(clock=args.cpu_clock, voltage_domain=VoltageDomain())
system.mem_mode = "timing"
system.mem_ranges = [AddrRange(args.mem_size)]

# Enable multi-threading support if requested
if args.threads > 1:
    system.multi_thread = True

# -----------------------
# 2) CPU (O3)
# -----------------------
system.cpu = X86O3CPU()

# Superscalar width settings
system.cpu.fetchWidth    = args.fetchWidth
system.cpu.decodeWidth   = args.decodeWidth
system.cpu.renameWidth   = args.renameWidth
system.cpu.dispatchWidth = args.dispatchWidth
system.cpu.issueWidth    = args.issueWidth
system.cpu.commitWidth   = args.commitWidth

# Enable multi-threading (SMT-ish) by setting numThreads
system.cpu.numThreads = args.threads

# Optional SMT policies (only meaningful when threads > 1)
if args.threads > 1 and args.smt:
    # Note: Some SMT policies may not be available in all gem5 versions
    # O3CPU will automatically handle multi-threading when numThreads > 1
    try:
        system.cpu.smtFetchPolicy = "RoundRobin"
        system.cpu.smtCommitPolicy = "RoundRobin"
        system.cpu.smtNumFetchingThreads = args.threads
    except AttributeError:
        # SMT policies not available in this gem5 version
        # SMT will still work with default policies
        print("Note: Using default SMT policies (advanced policies not available)")

# Branch predictor
if args.bp == "none":
    # Configure a minimal LocalBP that approximates "no prediction"
    # With only 1 entry and 1-bit counter, it can barely learn patterns
    from m5.objects import LocalBP
    system.cpu.branchPred.conditionalPredictor = LocalBP(
        localPredictorSize=1,  # Only 1 entry (no real history)
        localCtrBits=1         # 1-bit counter (weakly taken/not-taken)
    )
    print("Note: Using minimal LocalBP (1 entry, 1-bit) to simulate poor prediction")
else:
    # Use default branch predictor (Tournament/TAGE-based)
    pass

# -----------------------
# 3) Memory system: simple L1I/L1D + membus + DDR3
# (O3CPU w/o caches can work but is often awkward; minimal L1s is more stable)
# -----------------------
system.membus = SystemXBar()

system.cpu.icache = Cache(size="32kB", assoc=2, tag_latency=2, data_latency=2, response_latency=2, mshrs=4, tgts_per_mshr=8)
system.cpu.dcache = Cache(size="32kB", assoc=2, tag_latency=2, data_latency=2, response_latency=2, mshrs=8, tgts_per_mshr=8)

system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port

system.cpu.icache.mem_side = system.membus.cpu_side_ports
system.cpu.dcache.mem_side = system.membus.cpu_side_ports

system.cpu.createInterruptController()

# Connect interrupt controller ports for each thread
for i in range(args.threads):
    system.cpu.interrupts[i].pio = system.membus.mem_side_ports
    system.cpu.interrupts[i].int_requestor = system.membus.cpu_side_ports
    system.cpu.interrupts[i].int_responder = system.membus.mem_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

system.system_port = system.membus.cpu_side_ports

# -----------------------
# 4) Workload (SE mode)
# -----------------------
cmd = [args.cmd] + ([a for a in args.args.split()] if args.args else [])

system.workload = SEWorkload.init_compatible(args.cmd)

# If threads>1, create one process per thread (simplest SMT demo)
# Each thread needs its own Process instance to avoid memory mapping conflicts
if args.threads == 1:
    process = Process()
    process.cmd = cmd
    system.cpu.workload = process
else:
    # Create separate Process instances for each thread with unique PIDs
    processes = []
    for i in range(args.threads):
        p = Process()
        p.cmd = cmd
        p.pid = 100 + i  # Assign unique PIDs starting from 100
        processes.append(p)
    system.cpu.workload = processes

system.cpu.createThreads()

# -----------------------
# 5) Instantiate & run
# -----------------------
root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
