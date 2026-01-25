/*
 * Matrix multiplication benchmark for cache analysis
 * This program creates memory access patterns that stress different cache parameters
 */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define SIZE 128  // 128x128 matrices = 64KB of data (with doubles)

// Matrix multiplication - cache-unfriendly version (for testing)
void matrix_multiply_ijk(double **a, double **b, double **c, int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            c[i][j] = 0.0;
            for (int k = 0; k < n; k++) {
                c[i][j] += a[i][k] * b[k][j];
            }
        }
    }
}

// Array sum - simple sequential access
double array_sum(double *arr, int n) {
    double sum = 0.0;
    for (int i = 0; i < n; i++) {
        sum += arr[i];
    }
    return sum;
}

// Strided access - tests spatial locality
double strided_access(double *arr, int n, int stride) {
    double sum = 0.0;
    for (int i = 0; i < n; i += stride) {
        sum += arr[i];
    }
    return sum;
}

// Random access - tests cache associativity
double random_access(double *arr, int n, int seed) {
    double sum = 0.0;
    srand(seed);
    for (int i = 0; i < 1000; i++) {
        int idx = rand() % n;
        sum += arr[idx];
    }
    return sum;
}

int main() {
    printf("Starting cache benchmark...\n");
    
    // Allocate matrices
    double **A = (double **)malloc(SIZE * sizeof(double *));
    double **B = (double **)malloc(SIZE * sizeof(double *));
    double **C = (double **)malloc(SIZE * sizeof(double *));
    
    for (int i = 0; i < SIZE; i++) {
        A[i] = (double *)malloc(SIZE * sizeof(double));
        B[i] = (double *)malloc(SIZE * sizeof(double));
        C[i] = (double *)malloc(SIZE * sizeof(double));
    }
    
    // Initialize matrices
    printf("Initializing matrices (%dx%d)...\n", SIZE, SIZE);
    for (int i = 0; i < SIZE; i++) {
        for (int j = 0; j < SIZE; j++) {
            A[i][j] = (double)(i + j);
            B[i][j] = (double)(i - j);
            C[i][j] = 0.0;
        }
    }
    
    // Test 1: Matrix multiplication (stresses all cache levels)
    printf("Running matrix multiplication...\n");
    matrix_multiply_ijk(A, B, C, SIZE);
    printf("Matrix multiply result[0][0] = %f\n", C[0][0]);
    
    // Test 2: Sequential array access
    double *large_array = (double *)malloc(SIZE * SIZE * sizeof(double));
    for (int i = 0; i < SIZE * SIZE; i++) {
        large_array[i] = (double)i * 1.5;
    }
    
    printf("Running sequential access test...\n");
    double sum1 = array_sum(large_array, SIZE * SIZE);
    printf("Sequential sum = %f\n", sum1);
    
    // Test 3: Strided access (tests block size impact)
    printf("Running strided access test...\n");
    double sum2 = strided_access(large_array, SIZE * SIZE, 8);
    printf("Strided sum (stride=8) = %f\n", sum2);
    
    // Test 4: Random access (tests associativity)
    printf("Running random access test...\n");
    double sum3 = random_access(large_array, SIZE * SIZE, 42);
    printf("Random sum = %f\n", sum3);
    
    // Multiple iterations to generate more cache activity
    printf("Running repeated iterations...\n");
    for (int iter = 0; iter < 3; iter++) {
        matrix_multiply_ijk(A, B, C, SIZE);
        sum1 = array_sum(large_array, SIZE * SIZE);
        sum2 = strided_access(large_array, SIZE * SIZE, 16);
        sum3 = random_access(large_array, SIZE * SIZE, iter + 100);
    }
    
    printf("Benchmark complete!\n");
    printf("Final results: matrix[63][63]=%f, sums=%f,%f,%f\n", 
           C[63][63], sum1, sum2, sum3);
    
    // Cleanup
    for (int i = 0; i < SIZE; i++) {
        free(A[i]);
        free(B[i]);
        free(C[i]);
    }
    free(A);
    free(B);
    free(C);
    free(large_array);
    
    return 0;
}

