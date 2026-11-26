/*
 * check_driver.c - for the tests (not shown to learners): check_close and
 * check_report on cases the test gives.
 *
 * Reads commands from stdin, one a line; numbers as strtod reads them
 * (decimal, hex floats, nan, inf, -inf):
 *   close RTOL ATOL N G1..GN W1..WN
 *       prints "N BAD WORST GOT WANT ERR ALLOWED", the floats in %a
 *   report NAME RTOL ATOL N G1..GN W1..WN
 *       prints check_report's line for NAME, then "status S"
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "check.h"

static void *must(void *p)
{
    if (p == NULL) {
        fprintf(stderr, "check_driver: out of memory\n");
        exit(1);
    }
    return p;
}

/* RTOL ATOL N, then N got and N want values: the case's result. */
static check_result read_case(void)
{
    double rtol, atol, v;
    size_t n;
    if (scanf("%lf %lf %zu", &rtol, &atol, &n) != 3) {
        fprintf(stderr, "check_driver: expected RTOL ATOL N\n");
        exit(1);
    }
    float *got = must(malloc((n + 1) * sizeof *got)), *want = must(malloc((n + 1) * sizeof *want));
    for (size_t i = 0; i < 2 * n; i++) {
        if (scanf("%lf", &v) != 1) {
            fprintf(stderr, "check_driver: expected %zu values\n", 2 * n);
            exit(1);
        }
        if (i < n)
            got[i] = (float)v;
        else
            want[i - n] = (float)v;
    }
    /* n = 0 passes pointers that must not be read: NULL, so a read crashes. */
    check_result r = check_close(n ? got : NULL, n ? want : NULL, n, rtol, atol);
    free(got);
    free(want);
    return r;
}

int main(void)
{
    char command[16], name[64];
    while (scanf("%15s", command) == 1) {
        if (strcmp(command, "close") == 0) {
            check_result r = read_case();
            printf("%zu %zu %zu %a %a %a %a\n", r.n, r.bad, r.worst, (double)r.got, (double)r.want, r.err,
                   r.allowed);
        } else if (strcmp(command, "report") == 0 && scanf("%63s", name) == 1) {
            check_result r = read_case();
            int status = check_report(name, r);
            printf("status %d\n", status);
        } else {
            fprintf(stderr, "check_driver: unknown command %s\n", command);
            return 1;
        }
        fflush(stdout);
    }
    return 0;
}
