#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <stdbool.h>
#include <time.h>
#include <sched.h>

volatile sig_atomic_t waiting = false;

void handle_sigusr1(int sig) {
    if (!waiting)
        waiting = !waiting;
}

void handle_sigusr2(int sig) {
    sched_yield();
}

int main(int argc, char *argv[]) {
    signal(SIGUSR1, handle_sigusr1);
    signal(SIGUSR2, handle_sigusr2);

    while (1) {
        while (waiting) {
            pause(); 
            waiting = 0;
        }
    }

    return 0;
}
