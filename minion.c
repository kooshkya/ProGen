#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <stdbool.h>
#include <time.h>
#include <sched.h>

#include "code_timing.h"
#include "timespec_tools.h"


#define MAX_INTERVALS 10

// records program start
struct timespec busyloop_start;

int run_count;
int stop_count;
struct timespec run_intervals[MAX_INTERVALS];
struct timespec stop_intervals[MAX_INTERVALS];

void __always_inline custom_sleep(const struct timespec *duration) {
    struct timespec rem = {.tv_nsec = 0, .tv_sec = 0};
    if (nanosleep(duration, &rem)) {
        printf("woke up prematurely! %ld secs %ld nsecs left!\n", rem.tv_sec, rem.tv_nsec);
    }
}

void __always_inline busyloop(const struct timespec *duration, const struct timespec *busyloop_start) {
    struct timespec now, diff, old;
    check_timer:
        old = now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        timespec_diff(busyloop_start, &now, &diff);
        if (timespec_compare(&diff, duration) >= 0) {
            printf("diff is %ld s %ld ns\n", diff.tv_sec, diff.tv_nsec);
            return;
        }
        goto check_timer;
}

void __always_inline start_busyloop_clock() {
    clock_gettime(CLOCK_MONOTONIC, &busyloop_start);
}

int parse_arguments(int argc, char* argv[]) {
    if (!(argc % 2)) {
        printf("You need double numbers (secs nsecs) for each run/stop stint\n");
        return 1;
    }
    if (argc == 1) {
        printf("You need at least one run interval!\n");
        return 2;
    }
    if (argc > MAX_INTERVALS * 4 + 1) {
        printf("You can use at most %d run/stop doubles\n", MAX_INTERVALS);
        return 3;
    }

    for (int i = 1; i < argc; i++) {
        switch(i % 4) {
            case 1:
                run_count++;
                run_intervals[(i - 1) / 4].tv_sec = strtol(argv[i], NULL, 10);
                break;
            case 2:
                run_intervals[(i - 2) / 4].tv_nsec = strtol(argv[i], NULL, 10);
                break;
            case 3:
                stop_count++;
                stop_intervals[(i - 3) / 4].tv_sec = strtol(argv[i], NULL, 10);
                break;
            case 0:
                stop_intervals[(i - 4) / 4].tv_nsec = strtol(argv[i], NULL, 10);
                break;
        }
    }
    return 0;
}

void run_main_loop() {
    for (int i = 0; i < run_count; i++) {
        busyloop(&run_intervals[i], &busyloop_start);
        if (i < stop_count)
            custom_sleep(&stop_intervals[i]);
        start_busyloop_clock();
    }
}

int main(int argc, char *argv[]) {
    start_busyloop_clock();
    int ret = parse_arguments(argc, argv);
    if (ret)
        return ret;

    run_main_loop();
    
    return 0;
}
