/*
 * bench.h - how long a function takes: warm up, repeat, keep the fastest.
 *
 * The first call is not timed: it pays for things that happen once (pages
 * of memory touched for the first time, caches still cold). Then the
 * function is called again and again, and the fastest run is the answer,
 * since anything else running on the machine can only ever add time.
 */
#ifndef BENCH_H
#define BENCH_H

typedef struct {
    double min_time;       /* go on until the timed runs add up to this many seconds (0: 0.5) */
    int min_runs;          /* and until there are at least this many (0: 5) */
    int max_runs;          /* but stop at this many, whatever the time (0: 1000) */
    double (*clock)(void); /* the clock, in seconds (0: bench_now) */
} bench_opts;

typedef struct {
    int runs;                   /* timed runs, not counting the first call */
    double min, median, total;  /* in seconds */
} bench_result;

double bench_now(void); /* seconds on a clock that only goes forward */
bench_result bench(void (*fn)(void *), void *arg, bench_opts o);

// @internal
_Noreturn void todo(const char *lesson, const char *what);
// @end

#endif
