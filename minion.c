#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <stdbool.h>
#include <time.h>

#define PRINT_INTERVAL_SECONDS 5

volatile sig_atomic_t waiting = false;

void handle_sigusr1(int sig) {
    waiting = true;
}

void handle_sigusr2(int sig) {
    waiting = false;
}


void busyloop(int seconds) {
    clock_t start_time = clock();
    while ((clock() - start_time) < CLOCKS_PER_SEC * seconds) {
    }
}

int main(int argc, char *argv[]) {
    if (argc > 1) {
        int busy_time = atoi(argv[1]);
        if (busy_time > 0) {
            busyloop(busy_time);
            return 0;
        }
    }

    signal(SIGUSR1, handle_sigusr1);
    signal(SIGUSR2, handle_sigusr2);

    while (1) {
        while (waiting) {
            pause(); 
        }
    }

    return 0;
}
