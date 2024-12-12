#include <time.h>

#define TIMER_START(timer) \
    struct timespec timer##_start, timer##_end; \
    clock_gettime(CLOCK_MONOTONIC, &timer##_start);  // Start the timer

#define TIMER_STOP(timer) \
    clock_gettime(CLOCK_MONOTONIC, &timer##_end);  // Stop the timer

#define TIMER_PRINT(timer) \
    do { \
        long seconds = timer##_end.tv_sec - timer##_start.tv_sec; \
        long nanoseconds = timer##_end.tv_nsec - timer##_start.tv_nsec; \
        if (nanoseconds < 0) { \
            seconds--; \
            nanoseconds += 1000000000; \
        } \
        printf("Elapsed time for " #timer ": %ld seconds and %ld nanoseconds\n", seconds, nanoseconds); \
    } while(0);  // Print the measured time

