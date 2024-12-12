#include <stdio.h>
#include <stdlib.h>
#include <sched.h>
#include <unistd.h>
#include <sys/types.h>
#include <errno.h>


int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <pid> <class_num>\n", argv[0]);
        return 1;
    }

    pid_t pid = atoi(argv[1]);  // Convert first argument to PID
    int class_num = atoi(argv[2]);  // Convert second argument to scheduler class number
    struct sched_param param;

    if (class_num < 1 || class_num > 7) { 
        fprintf(stderr, "Invalid class number\n");
        return 1;
    }

    // Set the class number as the scheduler policy
    int sched_policy = class_num;  // Use the provided class number as the scheduler


    int ret = sched_setscheduler(pid, sched_policy, &param);
    if (ret == -1) {
        perror("sched_setscheduler");
        return 1;
    }

    printf("Successfully changed scheduler class for PID %d to class number %d\n", pid, class_num);

    return 0;
}
