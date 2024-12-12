

void __always_inline timespec_diff(const struct timespec *start, const struct timespec *end, struct timespec *result) {
    result->tv_sec = end->tv_sec - start->tv_sec;
    result->tv_nsec = end->tv_nsec - start->tv_nsec;

    // Handle negative nanoseconds
    if (result->tv_nsec < 0) {
        result->tv_sec -= 1;
        result->tv_nsec += 1000000000;
    }
}

int __always_inline timespec_compare(const struct timespec *first, const struct timespec *second) {
    if ((first->tv_sec > second->tv_sec) || 
        (first->tv_sec == second->tv_sec && first->tv_nsec > second->tv_nsec)) 
        return 1;
    else if (first->tv_sec == second->tv_sec && first->tv_nsec == second->tv_nsec)
        return 0;
    else   
        return -1;
}