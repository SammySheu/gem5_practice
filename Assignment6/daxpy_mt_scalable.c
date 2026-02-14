/*
 * Fully parallel multi-threaded DAXPY kernel for gem5 SE mode simulation.
 *
 * Performs: y[i] = a * x[i] + y[i]  (double precision)
 *
 * Unlike daxpy_mt.c, ALL three phases (init, DAXPY, validate) are
 * parallelized. Each thread owns a contiguous block of elements and
 * performs all phases on its block. This eliminates the serial fraction
 * that limited speedup due to Amdahl's Law.
 *
 * Usage: ./daxpy_mt_scalable <num_threads> [array_size]
 *   num_threads: number of threads (must match gem5 --num-cores)
 *   array_size:  number of elements (default: 10000)
 */

#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

/* Shared data */
static double *x;
static double *y;
static double a = 2.5;
static int array_size;
static int num_threads;

typedef struct {
    int tid;
    int errors;
} thread_arg_t;

void *worker(void *arg)
{
    thread_arg_t *targ = (thread_arg_t *)arg;
    int tid = targ->tid;

    /* Block partitioning: each thread owns a contiguous chunk */
    int chunk = array_size / num_threads;
    int start = tid * chunk;
    int end = (tid == num_threads - 1) ? array_size : start + chunk;

    /* Phase 1: Init this block */
    for (int i = start; i < end; i++) {
        x[i] = (double)i;
        y[i] = (double)(array_size - i);
    }

    /* Phase 2: DAXPY on this block */
    for (int i = start; i < end; i++) {
        y[i] = a * x[i] + y[i];
    }

    /* Phase 3: Validate this block */
    int local_errors = 0;
    for (int i = start; i < end; i++) {
        double expected = a * (double)i + (double)(array_size - i);
        if (y[i] != expected) {
            if (local_errors < 10) {
                fprintf(stderr, "Error: y[%d] = %f, expected %f\n",
                        i, y[i], expected);
            }
            local_errors++;
        }
    }

    targ->errors = local_errors;
    return NULL;
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <num_threads> [array_size]\n", argv[0]);
        return 1;
    }

    num_threads = atoi(argv[1]);
    if (num_threads < 1) {
        fprintf(stderr, "Error: num_threads must be >= 1\n");
        return 1;
    }

    array_size = 10000;
    if (argc >= 3) {
        array_size = atoi(argv[2]);
        if (array_size <= 0) {
            fprintf(stderr, "Error: array_size must be > 0\n");
            return 1;
        }
    }

    printf("DAXPY (scalable): %d threads, %d elements\n", num_threads, array_size);

    /* Allocate arrays */
    x = (double *)malloc(array_size * sizeof(double));
    y = (double *)malloc(array_size * sizeof(double));
    if (!x || !y) {
        fprintf(stderr, "Allocation error\n");
        return 2;
    }

    int total_errors = 0;

    if (num_threads == 1) {
        /* Single-threaded: just run directly */
        thread_arg_t arg = { .tid = 0, .errors = 0 };
        worker(&arg);
        total_errors = arg.errors;
    } else {
        /* Multi-threaded: create (num_threads - 1) pthreads */
        pthread_t *threads = (pthread_t *)malloc((num_threads - 1) * sizeof(pthread_t));
        thread_arg_t *args = (thread_arg_t *)malloc(num_threads * sizeof(thread_arg_t));
        if (!threads || !args) {
            fprintf(stderr, "Allocation error\n");
            return 2;
        }

        /* Launch worker threads (tid 0 to num_threads-2) */
        for (int i = 0; i < num_threads - 1; i++) {
            args[i].tid = i;
            args[i].errors = 0;
            if (pthread_create(&threads[i], NULL, worker, &args[i]) != 0) {
                fprintf(stderr, "Error creating thread %d\n", i);
                return 3;
            }
        }

        /* Main thread runs as the last worker (SE mode requirement) */
        args[num_threads - 1].tid = num_threads - 1;
        args[num_threads - 1].errors = 0;
        worker(&args[num_threads - 1]);

        /* Wait for all worker threads and sum errors */
        for (int i = 0; i < num_threads - 1; i++) {
            pthread_join(threads[i], NULL);
            total_errors += args[i].errors;
        }
        total_errors += args[num_threads - 1].errors;

        free(threads);
        free(args);
    }

    if (total_errors == 0) {
        printf("DAXPY completed successfully. Validation passed.\n");
    } else {
        printf("DAXPY completed with %d errors.\n", total_errors);
    }

    free(x);
    free(y);
    return 0;
}
