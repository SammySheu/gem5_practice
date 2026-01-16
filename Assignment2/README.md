# Assignment 2 - Hello World Simulation

## Building and Running

Compile the hello program:
```bash
gcc configs/practice/Assignment2/hello.c -o configs/practice/Assignment2/hello
```

Run with the deprecated example configuration:
```bash
./build/X86/gem5.opt configs/deprecated/example/se.py -c configs/practice/Assignment2/hello
```

Run with the custom Python configuration:
```bash
./build/X86/gem5.opt configs/practice/Assignment2/run_hello.py
```

## Configuration Changes

The Python script is provided so we can manually configure the simulation. I tried to make it work, and below is a summary of what I've changed:

1. **Memory Controller Architecture**: The old version directly assigned `DDR3_1600_8x8()` to `system.mem_ctrl`, which is incompatible because we are using v25.1. The new implementation creates a `MemCtrl()` wrapper object first and then assigns the DRAM interface as a child component (`system.mem_ctrl.dram`).

2. **Cache and Bus Connectivity**: Instead of using the deprecated `.slave` port designation, my implementation explicitly defines both CPU-side and memory-side interfaces, creating a proper hierarchy: CPU → Cache (cpu_side) → Cache (mem_side) → Memory Bus → Memory Controller.

3. **Interrupt Controller Configuration**: The Interrupt Controller is used to manage and prioritize routing interrupt requests (IRQs). I explicitly set up connections for PIO (Programmed I/O) and interrupt request/response pathways, which are necessary for proper interrupt handling in X86 simulations.

4. **Process Management**: The workload initialization has been refined by creating an explicit `Process()` object with a command specification (`process.cmd = ["hello"]`), providing clearer process management and better separation between system-level and process-level workload configurations.

## Performance Notes

Since we are using our own configuration, the simulation ticks more than in the previous one, about 4 times as much as the original one.
