#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <stdbool.h>
#include <time.h>
#include <sched.h>

#include "timespec_tools.h"


#define MAX_INTERVALS 10

// records program start
struct timespec busyloop_start;

int run_count;
int stop_count;
struct timespec runs[MAX_INTERVALS];
struct timespec stops[MAX_INTERVALS];

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

int main(int argc, char *argv[]) {
    start_busyloop_clock();

    if (!(argc % 2))
        printf("You need double numbers (secs nsecs) for each run/stop stint\n");
    if (argc > MAX_INTERVALS * 4 + 1)
        printf("You can use at most %d run/stop doubles\n", MAX_INTERVALS);

    if (argc > 1) { // means program has been configured with run/stop intervals
        for (int i = 1; i < argc; i++) {
            switch(i % 4) {
                case 1:
                    run_count++;
                    runs[(i - 1) / 4].tv_sec = strtol(argv[i], NULL, 10);
                    break;
                case 2:
                    runs[(i - 2) / 4].tv_nsec = strtol(argv[i], NULL, 10);
                    break;
                case 3:
                    stop_count++;
                    stops[(i - 3) / 4].tv_sec = strtol(argv[i], NULL, 10);
                    break;
                case 0:
                    stops[(i - 4) / 4].tv_nsec = strtol(argv[i], NULL, 10);
                    break;
            }
        }

        for (int i = 0; i < run_count; i++) {
            busyloop(&runs[i], &busyloop_start);
            if (i < stop_count)
                custom_sleep(&stops[i]);
            start_busyloop_clock();
        }
    } else {    // means program should run indefinitely
        // TODO run indefinitely
    }
}
