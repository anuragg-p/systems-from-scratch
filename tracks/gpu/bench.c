/*
 * bench.c - warm up, repeat, keep the fastest run.
 */
#define _DEFAULT_SOURCE /* clock_gettime, which a strict C11 build hides on Linux */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "bench.h"

/* Seconds since some fixed moment, on a clock that only goes forward and
 * that nothing adjusts. CLOCK_MONOTONIC_RAW, because macOS's
 * CLOCK_MONOTONIC moves in whole microseconds, too coarse for a run that
 * takes less than one; this one counts to tens of nanoseconds on both
 * macOS and Linux. */
double bench_now(void)
{
    // @build 00.03 bench_now: a clock that only goes forward
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
    // @end
}

/* For qsort: the order of two times. */
static int earlier(const void *x, const void *y)
{
    // @build 00.03 the order of two times
    double a = *(const double *)x, b = *(const double *)y;
    return (a > b) - (a < b);
    // @end
}

/* Time fn(arg). One call first, not timed (the warm-up). Then timed calls
 * until there are at least o.min_runs of them and they add up to at least
 * o.min_time seconds, or there are o.max_runs. A field of o that is 0 (or
 * less) takes its default. Returns the number of timed runs, the fastest,
 * the median (the middle run, or the mean of the two middle ones) and the
 * total. */
bench_result bench(void (*fn)(void *), void *arg, bench_opts o)
{
    // @build 00.03 bench: warm up, repeat, sort the times
    if (o.min_time <= 0)
        o.min_time = 0.5;
    if (o.min_runs <= 0)
        o.min_runs = 5;
    if (o.max_runs <= 0)
        o.max_runs = 1000;
    if (o.clock == NULL)
        o.clock = bench_now;
    double *times = malloc((size_t)o.max_runs * sizeof *times);
    if (times == NULL) {
        fprintf(stderr, "bench: out of memory\n");
        exit(1);
    }

    fn(arg);
    bench_result r = {0, 0, 0, 0};
    while (r.runs < o.max_runs && (r.runs < o.min_runs || r.total < o.min_time)) {
        double start = o.clock();
        fn(arg);
        double t = o.clock() - start;
        times[r.runs++] = t;
        r.total += t;
    }

    qsort(times, (size_t)r.runs, sizeof *times, earlier);
    r.min = times[0];
    if (r.runs % 2 == 1)
        r.median = times[r.runs / 2];
    else
        r.median = (times[r.runs / 2 - 1] + times[r.runs / 2]) / 2;
    free(times);
    return r;
    // @end
}
