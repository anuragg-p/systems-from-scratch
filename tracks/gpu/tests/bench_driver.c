/*
 * bench_driver.c - for the tests (not shown to learners): bench with a
 * clock the test scripts, so its arithmetic can be checked exactly.
 *
 * Reads cases from stdin, one a line:
 *   script MIN_TIME MIN_RUNS MAX_RUNS COUNT T1..TCOUNT
 *       bench on a function that does nothing, with a clock that returns
 *       T1, T2, ... in turn (running out is an error)
 *   real MIN_TIME MIN_RUNS MAX_RUNS
 *       the same with o.clock left 0, so bench_now
 * and prints, for each:
 *   runs R min M median D total T calls C clocks K first F
 * M, D and T in %a; C the calls of the function, K of the clock, F the
 * calls of the function made before the clock was first read. And
 *   steps COUNT
 *       prints "step S backwards B": the smallest step bench_now took in
 *       COUNT tries (%a, seconds), and how often it went back
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bench.h"

static double *script;
static int script_len, clocks, calls, first = -1;

static double scripted(void)
{
    if (clocks >= script_len) {
        fprintf(stderr, "bench_driver: the clock was read more than %d times\n", script_len);
        exit(1);
    }
    if (first < 0)
        first = calls;
    return script[clocks++];
}

static void nothing(void *arg)
{
    (void)arg;
    calls++;
}

/* bench_now read COUNT times: the smallest step it takes (its resolution, as
 * far as the program can see it), and whether it ever went back. */
static void steps(int count)
{
    double smallest = 1e9;
    int backwards = 0;
    for (int i = 0; i < count; i++) {
        double t0 = bench_now(), t1 = bench_now();
        while (t1 == t0)
            t1 = bench_now();
        if (t1 < t0)
            backwards++;
        else if (t1 - t0 < smallest)
            smallest = t1 - t0;
    }
    printf("step %a backwards %d\n", smallest, backwards);
}

int main(void)
{
    char kind[16];
    while (scanf("%15s", kind) == 1) {
        int count;
        if (strcmp(kind, "steps") == 0 && scanf("%d", &count) == 1) {
            steps(count);
            fflush(stdout);
            continue;
        }
        bench_opts o = {0, 0, 0, NULL};
        if (scanf("%lf %d %d", &o.min_time, &o.min_runs, &o.max_runs) != 3) {
            fprintf(stderr, "bench_driver: expected MIN_TIME MIN_RUNS MAX_RUNS\n");
            return 1;
        }
        clocks = calls = 0;
        first = -1;
        script_len = 0;
        if (strcmp(kind, "script") == 0) {
            if (scanf("%d", &script_len) != 1 || script_len < 0) {
                fprintf(stderr, "bench_driver: expected COUNT\n");
                return 1;
            }
            script = malloc(((size_t)script_len + 1) * sizeof *script);
            if (script == NULL)
                return 1;
            for (int i = 0; i < script_len; i++)
                if (scanf("%lf", &script[i]) != 1) {
                    fprintf(stderr, "bench_driver: expected %d clock readings\n", script_len);
                    return 1;
                }
            o.clock = scripted;
        } else if (strcmp(kind, "real") != 0) {
            fprintf(stderr, "bench_driver: unknown case %s\n", kind);
            return 1;
        }
        bench_result r = bench(nothing, NULL, o);
        printf("runs %d min %a median %a total %a calls %d clocks %d first %d\n", r.runs, r.min, r.median,
               r.total, calls, clocks, first);
        fflush(stdout);
        if (o.clock == scripted) {
            free(script);
            script = NULL;
        }
    }
    return 0;
}
