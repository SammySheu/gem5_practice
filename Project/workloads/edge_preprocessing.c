/*
 * Edge Pre-processing Workload
 * 
 * Simulates a typical edge computing scenario where sensor data is:
 * 1. Streamed from multiple sensors
 * 2. Filtered and normalized
 * 3. Aggregated and compressed
 * 4. Prepared for transmission to cloud
 * 
 * This workload emphasizes:
 * - Sequential memory access (streaming sensor data)
 * - Numerical operations (filtering, normalization)
 * - Conditional branches (threshold detection)
 * - Memory bandwidth sensitivity
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>

#define NUM_SENSORS 8
#define SAMPLES_PER_SENSOR 1024
#define TOTAL_SAMPLES (NUM_SENSORS * SAMPLES_PER_SENSOR)
#define FILTER_WINDOW 5
#define THRESHOLD 100

// Sensor data structure
typedef struct {
    int32_t sensor_id;
    float raw_value;
    float filtered_value;
    uint8_t anomaly_flag;
} SensorReading;

// Global statistics
typedef struct {
    float min_value;
    float max_value;
    float sum;
    uint32_t anomaly_count;
    uint32_t total_samples;
} AggregateStats;

// Initialize sensor data with pseudo-random values
void generate_sensor_data(SensorReading *readings) {
    uint32_t seed = 12345;
    
    for (int i = 0; i < TOTAL_SAMPLES; i++) {
        // Simple PRNG for reproducible results
        seed = (seed * 1103515245 + 12345) & 0x7fffffff;
        
        readings[i].sensor_id = i / SAMPLES_PER_SENSOR;
        readings[i].raw_value = (float)(seed % 200) - 50.0f;  // Range: -50 to 150
        readings[i].filtered_value = 0.0f;
        readings[i].anomaly_flag = 0;
    }
}

// Moving average filter (common in edge preprocessing)
void apply_moving_average_filter(SensorReading *readings, int num_readings) {
    for (int i = 0; i < num_readings; i++) {
        float sum = 0.0f;
        int count = 0;
        
        // Compute average over window
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

// Detect anomalies (threshold-based)
void detect_anomalies(SensorReading *readings, int num_readings) {
    for (int i = 0; i < num_readings; i++) {
        float deviation = fabs(readings[i].filtered_value - readings[i].raw_value);
        
        if (deviation > THRESHOLD || readings[i].filtered_value > 140.0f) {
            readings[i].anomaly_flag = 1;
        }
    }
}

// Normalize data for transmission
void normalize_data(SensorReading *readings, int num_readings, 
                   float min_val, float max_val) {
    float range = max_val - min_val;
    
    if (range < 0.001f) return;  // Avoid division by zero
    
    for (int i = 0; i < num_readings; i++) {
        readings[i].filtered_value = 
            (readings[i].filtered_value - min_val) / range;
    }
}

// Aggregate statistics across all sensors
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

// Per-sensor statistics
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
        printf("Sensor %d: Avg = %.4f\n", sensor, sensor_avg);
    }
}

int main() {
    printf("========================================\n");
    printf("Edge Pre-processing Workload\n");
    printf("========================================\n");
    printf("Configuration:\n");
    printf("  Sensors: %d\n", NUM_SENSORS);
    printf("  Samples per sensor: %d\n", SAMPLES_PER_SENSOR);
    printf("  Total samples: %d\n", TOTAL_SAMPLES);
    printf("  Filter window: %d\n", FILTER_WINDOW);
    printf("========================================\n\n");
    
    // Allocate sensor data
    SensorReading *readings = (SensorReading *)malloc(
        TOTAL_SAMPLES * sizeof(SensorReading));
    
    if (!readings) {
        printf("ERROR: Memory allocation failed!\n");
        return 1;
    }
    
    // Edge preprocessing pipeline
    printf("Step 1: Generating sensor data...\n");
    generate_sensor_data(readings);
    
    printf("Step 2: Applying moving average filter...\n");
    apply_moving_average_filter(readings, TOTAL_SAMPLES);
    
    printf("Step 3: Detecting anomalies...\n");
    detect_anomalies(readings, TOTAL_SAMPLES);
    
    printf("Step 4: Computing aggregate statistics...\n");
    AggregateStats stats;
    compute_aggregate_stats(readings, TOTAL_SAMPLES, &stats);
    
    printf("Step 5: Normalizing data...\n");
    normalize_data(readings, TOTAL_SAMPLES, stats.min_value, stats.max_value);
    
    printf("Step 6: Computing per-sensor statistics...\n");
    compute_per_sensor_stats(readings, TOTAL_SAMPLES);
    
    // Print results
    printf("\n========================================\n");
    printf("Aggregate Statistics:\n");
    printf("========================================\n");
    printf("  Min value: %.4f\n", stats.min_value);
    printf("  Max value: %.4f\n", stats.max_value);
    printf("  Average: %.4f\n", stats.sum / stats.total_samples);
    printf("  Anomalies detected: %u (%.2f%%)\n", 
           stats.anomaly_count,
           100.0f * stats.anomaly_count / stats.total_samples);
    printf("========================================\n");
    printf("Edge preprocessing completed successfully!\n");
    
    free(readings);
    return 0;
}
