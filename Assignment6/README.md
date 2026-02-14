# Assignment 6 - Thread-Level Parallelism (TLP) in Shared-Memory Multiprocessors

## Building and Running

Compile the benchmark programs:
```bash
# This is the original daxpy config. It only parallel DAXPY, which is not sufficient if we want to see significant performance improvement
# parallel DAXPY which serial init/validate
aarch64-linux-gnu-gcc -static -O2 -pthread \
    -o configs/practice/Assignment6/daxpy_mt_arm \
    configs/practice/Assignment6/daxpy_mt.c

# Scalable DAXPY (fully parallel: init + DAXPY + validate)
# Not only parallel DAXPY but also init and validate,
aarch64-linux-gnu-gcc -static -O2 -pthread \
    -o configs/practice/Assignment6/daxpy_mt_scalable_arm \
    configs/practice/Assignment6/daxpy_mt_scalable.c
```

Run a single experiment:
```bash
# This command is included in run_experiments.sh.
# I put this command here is to showcase how to run single experiment
./build/ARM/gem5.opt configs/practice/Assignment6/multicore_minor_daxpy.py \
  --num-cores 2 --op-lat 3 --issue-lat 4 \
  --binary configs/practice/Assignment6/daxpy_mt_scalable_arm \
  --array-size 10000 # 2 cores, opLat=3, issueLat=4, array size 10000

./build/ARM/gem5.opt configs/practice/Assignment6/multicore_minor_daxpy.py \
  --num-cores 8 --op-lat 6 --issue-lat 1 \
  --binary configs/practice/Assignment6/daxpy_mt_scalable_arm \
  --array-size 100000 # 8 cores, opLat=6, issueLat=1
```

Run all experiments in batch mode (results stored under [results_50k](./results_50k/) and [results_50k.csv](./results_50k.csv)):
```bash
# 50,000 elements (results stored under results_50k/)
./configs/practice/Assignment6/run_experiments_50k.sh
```

Analyze results and generate plots:
```bash
# Since we have result folder and csv file (created after executing run_experiments.sh), we could analyze the result set by
python3 configs/practice/Assignment6/analyze_results.py \
    --csv configs/practice/Assignment6/results_50k.csv \
    --results-dir configs/practice/Assignment6/results_50k
```


## Key differences between daxpy_mt and daxpy_mt_scalable

| Feature | `daxpy_mt.c` | `daxpy_mt_scalable.c` |
|---|---|---|
| Array partitioning | Strided (interleaved) | Contiguous block per thread |
| Initialization phase | Serial (main thread) | Parallel (each thread inits its block) |
| DAXPY phase | Parallel | Parallel |
| Validation phase | Serial (main thread) | Parallel (each thread validates its block) |
| Amdahl serial fraction | High (init + validate) | Minimal |

