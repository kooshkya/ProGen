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

int main() {
    signal(SIGUSR1, handle_sigusr1);
    signal(SIGUSR2, handle_sigusr2);

    printf("Process PID: %d\n", getpid());
    printf("Send SIGUSR1 to put the process to sleep.\n");
    printf("Send SIGUSR2 to wake the process up.\n");
    
    clock_t last_print = 0;
    while (1) {
        clock_t now = clock(); 

        while (waiting) {
            printf("Going to sleep or staying asleep after a signal at %ld ticks\n", now);
            pause();
            if (!waiting)
                printf("Running after a sleep at %ld ticks\n", now);
            else
                printf("Signal received but staying asleep\n");
        }

        if (!last_print || now - last_print >= PRINT_INTERVAL_SECONDS * CLOCKS_PER_SEC) {
            printf("Working... PID: %d at %ld ticks\n", getpid(), now);
            fflush(stdout);
            last_print = now;
        }
    }

    return 0;
}
