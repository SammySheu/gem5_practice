/*
 * Multi-threaded DAXPY kernel for gem5 SE mode simulation.
 *
 * Performs: y[i] = a * x[i] + y[i]  (double precision)
 *
 * Usage: ./daxpy_mt <num_threads> [array_size]
 *   num_threads: number of threads (must match gem5 --num-cores)
 *   array_size:  number of elements (default: 10000)
 *
 * Note: In gem5 SE mode, the main thread must act as one of the
 * worker threads. Only (num_threads - 1) pthreads are created.
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
} thread_arg_t;

void *daxpy_worker(void *arg)
{
    thread_arg_t *targ = (thread_arg_t *)arg;
    int tid = targ->tid;

    /* Each thread handles a strided portion of the arrays */
    for (int i = tid; i < array_size; i += num_threads) {
        y[i] = a * x[i] + y[i];
    }
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

    printf("DAXPY: %d threads, %d elements\n", num_threads, array_size);

    /* Allocate arrays */
    x = (double *)malloc(array_size * sizeof(double));
    y = (double *)malloc(array_size * sizeof(double));
    if (!x || !y) {
        fprintf(stderr, "Allocation error\n");
        return 2;
    }

    /* Initialize arrays */
    for (int i = 0; i < array_size; i++) {
        x[i] = (double)i;
        y[i] = (double)(array_size - i);
    }

    if (num_threads == 1) {
        /* Single-threaded: just run directly */
        thread_arg_t arg = { .tid = 0 };
        daxpy_worker(&arg);
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
            if (pthread_create(&threads[i], NULL, daxpy_worker, &args[i]) != 0) {
                fprintf(stderr, "Error creating thread %d\n", i);
                return 3;
            }
        }

        /* Main thread runs as the last worker (SE mode requirement) */
        args[num_threads - 1].tid = num_threads - 1;
        daxpy_worker(&args[num_threads - 1]);

        /* Wait for all worker threads */
        for (int i = 0; i < num_threads - 1; i++) {
            pthread_join(threads[i], NULL);
        }

        free(threads);
        free(args);
    }

    /* Validate a few results */
    int errors = 0;
    for (int i = 0; i < array_size && errors < 10; i++) {
        double expected = a * (double)i + (double)(array_size - i);
        if (y[i] != expected) {
            fprintf(stderr, "Error: y[%d] = %f, expected %f\n", i, y[i], expected);
            errors++;
        }
    }

    if (errors == 0) {
        printf("DAXPY completed successfully. Validation passed.\n");
    } else {
        printf("DAXPY completed with %d errors.\n", errors);
    }

    free(x);
    free(y);
    return 0;
}
