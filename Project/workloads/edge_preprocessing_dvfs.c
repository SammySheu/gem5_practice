/*
 * Edge Pre-processing Workload -- Instrumented for Dynamic DVFS
 *
 * Same workload as edge_preprocessing.c but with gem5 m5_work_begin()
 * pseudo-instructions at each pipeline phase boundary. These cause
 * simulation exit events that the Python config script catches to
 * switch DVFS operating points per phase.
 *
 * Phase IDs (passed as workid to m5_work_begin):
 *   0 = Data generation      (compute-light, PRNG)
 *   1 = Moving average filter (compute-intensive, good cache locality)
 *   2 = Anomaly detection     (simple comparisons)
 *   3 = Cross-sensor fusion   (memory-heavy, strided access)
 *   4 = Aggregate statistics   (simple accumulation)
 *   5 = Normalize data         (simple arithmetic)
 *   6 = Per-sensor statistics  (moderate computation)
 *
 * Compile: aarch64-linux-gnu-gcc -O2 -static -o workloads/edge_preprocessing_dvfs_arm workloads/edge_preprocessing_dvfs.c -lm
 * Run:     gem5 edge_power_dvfs_dynamic.py --cpu-type=minor --binary=workloads/edge_preprocessing_dvfs_arm
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>

#define NUM_SENSORS 16
#define SAMPLES_PER_SENSOR 1024
#define TOTAL_SAMPLES (NUM_SENSORS * SAMPLES_PER_SENSOR)
#define FILTER_WINDOW 5
#define THRESHOLD 100
#define NUM_ROUNDS 3

/* ---- gem5 m5ops inline assembly for AArch64 ---- */

/*
 * m5_work_begin(workid, threadid): signals a phase transition to gem5.
 * Encoding: .inst 0xff000110 | (M5OP_WORK_BEGIN << 16)
 *   M5OP_WORK_BEGIN = 0x5a  =>  0xff5a0110
 * Arguments passed in x0 (workid) and x1 (threadid) per ARM64 ABI.
 */
static inline void gem5_work_begin(uint64_t workid, uint64_t threadid)
{
    register uint64_t x0 __asm__("x0") = workid;
    register uint64_t x1 __asm__("x1") = threadid;
    __asm__ __volatile__ (
        ".inst 0xff5a0110"
        : "+r"(x0), "+r"(x1)
    );
}

/* Phase IDs */
#define PHASE_GENERATE    0
#define PHASE_FILTER      1
#define PHASE_ANOMALY     2
#define PHASE_FUSION      3
#define PHASE_AGGREGATE   4
#define PHASE_NORMALIZE   5
#define PHASE_PER_SENSOR  6

/* ---- Data structures ---- */

typedef struct {
    int32_t sensor_id;
    float raw_value;
    float filtered_value;
    uint8_t anomaly_flag;
} SensorReading;

typedef struct {
    float min_value;
    float max_value;
    float sum;
    uint32_t anomaly_count;
    uint32_t total_samples;
} AggregateStats;

/* ---- Processing functions (identical to non-instrumented version) ---- */

void generate_sensor_data(SensorReading *readings, uint32_t seed) {
    for (int i = 0; i < TOTAL_SAMPLES; i++) {
        seed = (seed * 1103515245 + 12345) & 0x7fffffff;
        readings[i].sensor_id = i / SAMPLES_PER_SENSOR;
        readings[i].raw_value = (float)(seed % 200) - 50.0f;
        readings[i].filtered_value = 0.0f;
        readings[i].anomaly_flag = 0;
    }
}

void apply_moving_average_filter(SensorReading *readings, int num_readings) {
    for (int i = 0; i < num_readings; i++) {
        float sum = 0.0f;
        int count = 0;
        for (int j = -FILTER_WINDOW/2; j <= FILTER_WINDOW/2; j++) {
            int idx = i + j;
            if (idx >= 0 && idx < num_readings) {
                sum += readings[idx].raw_value;
                count++;
            }
        }
        readings[i].filtered_value = sum / count;
    }
}

void detect_anomalies(SensorReading *readings, int num_readings) {
    for (int i = 0; i < num_readings; i++) {
        float deviation = fabs(readings[i].filtered_value - readings[i].raw_value);
        if (deviation > THRESHOLD || readings[i].filtered_value > 140.0f) {
            readings[i].anomaly_flag = 1;
        }
    }
}

void cross_sensor_fusion(SensorReading *readings, float *fused_output) {
    for (int t = 0; t < SAMPLES_PER_SENSOR; t++) {
        float weighted_sum = 0.0f;
        float weight_total = 0.0f;
        for (int s = 0; s < NUM_SENSORS; s++) {
            int idx = s * SAMPLES_PER_SENSOR + t;
            float weight = 1.0f + 0.5f * (float)(NUM_SENSORS/2 - abs(s - NUM_SENSORS/2));
            weighted_sum += readings[idx].filtered_value * weight;
            weight_total += weight;
        }
        fused_output[t] = weighted_sum / weight_total;
    }

    printf("    Sensor correlations: ");
    for (int s = 0; s < NUM_SENSORS - 1; s++) {
        float sum_a = 0.0f, sum_b = 0.0f;
        float sum_ab = 0.0f, sum_a2 = 0.0f, sum_b2 = 0.0f;
        for (int t = 0; t < SAMPLES_PER_SENSOR; t++) {
            float a = readings[s * SAMPLES_PER_SENSOR + t].filtered_value;
            float b = readings[(s + 1) * SAMPLES_PER_SENSOR + t].filtered_value;
            sum_a += a; sum_b += b;
            sum_ab += a * b; sum_a2 += a * a; sum_b2 += b * b;
        }
        float n = (float)SAMPLES_PER_SENSOR;
        float num = n * sum_ab - sum_a * sum_b;
        float den = sqrtf((n * sum_a2 - sum_a * sum_a) * (n * sum_b2 - sum_b * sum_b));
        float corr = (den > 0.001f) ? (num / den) : 0.0f;
        if (s < 4) printf("r(%d,%d)=%.3f ", s, s+1, corr);
    }
    printf("...\n");
}

void normalize_data(SensorReading *readings, int num_readings,
                   float min_val, float max_val) {
    float range = max_val - min_val;
    if (range < 0.001f) return;
    for (int i = 0; i < num_readings; i++) {
        readings[i].filtered_value =
            (readings[i].filtered_value - min_val) / range;
    }
}

void compute_aggregate_stats(SensorReading *readings, int num_readings,
                            AggregateStats *stats) {
    stats->min_value = 1e9;
    stats->max_value = -1e9;
    stats->sum = 0.0f;
    stats->anomaly_count = 0;
    stats->total_samples = num_readings;
    for (int i = 0; i < num_readings; i++) {
        float val = readings[i].filtered_value;
        if (val < stats->min_value) stats->min_value = val;
        if (val > stats->max_value) stats->max_value = val;
        stats->sum += val;
        stats->anomaly_count += readings[i].anomaly_flag;
    }
}

void compute_per_sensor_stats(SensorReading *readings, int num_readings) {
    for (int sensor = 0; sensor < NUM_SENSORS; sensor++) {
        float sensor_sum = 0.0f;
        int sensor_samples = 0;
        for (int i = sensor * SAMPLES_PER_SENSOR;
             i < (sensor + 1) * SAMPLES_PER_SENSOR; i++) {
            sensor_sum += readings[i].filtered_value;
            sensor_samples++;
        }
        float sensor_avg = sensor_sum / sensor_samples;
        printf("    Sensor %2d: Avg = %.4f\n", sensor, sensor_avg);
    }
}

/* ---- Main with phase-boundary m5ops ---- */

int main() {
    printf("========================================\n");
    printf("Edge Pre-processing Workload (DVFS-instrumented)\n");
    printf("========================================\n");
    printf("Configuration:\n");
    printf("  Sensors: %d\n", NUM_SENSORS);
    printf("  Samples per sensor: %d\n", SAMPLES_PER_SENSOR);
    printf("  Total samples: %d\n", TOTAL_SAMPLES);
    printf("  Working set: %d KB\n", (int)(TOTAL_SAMPLES * sizeof(SensorReading) / 1024));
    printf("  Filter window: %d\n", FILTER_WINDOW);
    printf("  Processing rounds: %d\n", NUM_ROUNDS);
    printf("========================================\n\n");

    SensorReading *readings = (SensorReading *)malloc(
        TOTAL_SAMPLES * sizeof(SensorReading));
    float *fused_output = (float *)malloc(
        SAMPLES_PER_SENSOR * sizeof(float));

    if (!readings || !fused_output) {
        printf("ERROR: Memory allocation failed!\n");
        return 1;
    }

    uint32_t total_anomalies = 0;
    float total_avg = 0.0f;

    for (int round = 0; round < NUM_ROUNDS; round++) {
        uint32_t seed = 12345 + round * 7919;
        printf("--- Round %d/%d (seed=%u) ---\n", round + 1, NUM_ROUNDS, seed);

        /* Phase 0: Generate sensor data */
        gem5_work_begin(PHASE_GENERATE, 0);
        printf("  Step 1: Generating sensor data...\n");
        generate_sensor_data(readings, seed);

        /* Phase 1: Moving average filter (compute-intensive) */
        gem5_work_begin(PHASE_FILTER, 0);
        printf("  Step 2: Applying moving average filter...\n");
        apply_moving_average_filter(readings, TOTAL_SAMPLES);

        /* Phase 2: Anomaly detection (lightweight) */
        gem5_work_begin(PHASE_ANOMALY, 0);
        printf("  Step 3: Detecting anomalies...\n");
        detect_anomalies(readings, TOTAL_SAMPLES);

        /* Phase 3: Cross-sensor fusion (memory-heavy) */
        gem5_work_begin(PHASE_FUSION, 0);
        printf("  Step 4: Cross-sensor fusion...\n");
        cross_sensor_fusion(readings, fused_output);

        /* Phase 4: Aggregate statistics */
        gem5_work_begin(PHASE_AGGREGATE, 0);
        printf("  Step 5: Computing aggregate statistics...\n");
        AggregateStats stats;
        compute_aggregate_stats(readings, TOTAL_SAMPLES, &stats);

        /* Phase 5: Normalize */
        gem5_work_begin(PHASE_NORMALIZE, 0);
        printf("  Step 6: Normalizing data...\n");
        normalize_data(readings, TOTAL_SAMPLES, stats.min_value, stats.max_value);

        /* Phase 6: Per-sensor stats */
        gem5_work_begin(PHASE_PER_SENSOR, 0);
        printf("  Step 7: Computing per-sensor statistics...\n");
        compute_per_sensor_stats(readings, TOTAL_SAMPLES);

        printf("  Round %d summary: anomalies=%u, avg=%.4f, range=[%.4f, %.4f]\n\n",
               round + 1, stats.anomaly_count,
               stats.sum / stats.total_samples,
               stats.min_value, stats.max_value);

        total_anomalies += stats.anomaly_count;
        total_avg += stats.sum / stats.total_samples;
    }

    printf("========================================\n");
    printf("Final Summary (%d rounds):\n", NUM_ROUNDS);
    printf("========================================\n");
    printf("  Total anomalies: %u\n", total_anomalies);
    printf("  Average value (across rounds): %.4f\n", total_avg / NUM_ROUNDS);
    printf("  Fused output sample [0]: %.4f\n", fused_output[0]);
    printf("========================================\n");
    printf("Edge preprocessing completed successfully!\n");

    free(readings);
    free(fused_output);
    return 0;
}
