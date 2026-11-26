/*
 * wb.c - the workbench: add, shown, checked against add_ref, and timed.
 *
 *   wb show [-n N] [-s SEED]    n, the seed, and the first values of a, b and add(a, b)
 *   wb check [-n N] [-s SEED]   add against add_ref, every element    @from 00.02
 *   wb time [-n N]              add's fastest run, and the bytes it moves a second    @from 00.03
 *
 * a comes from rng_fill with the seed (1 unless -s gives another, and
 * never 0), b with the seed + 1. n is 1003 unless -n gives another: four
 * elements a pass leave a tail of three.
 * wb time's n is 2^24 unless -n gives another, and its seeds are 1 and 2.    @from 00.03
 */
#include <errno.h>
#include <math.h>   // @from 00.02
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "add.h"
#include "bench.h"  // @from 00.03
#include "check.h"  // @from 00.02
#include "rng.h"

#define MAX_N (1 << 28)
#define MAX_SEED 4294967295u /* b's seed, one more, must not wrap around to 0 */

/* Say how wb is used, and stop with status 2. */
_Noreturn static void usage(void)
{
    fprintf(stderr, "usage: wb show [-n N] [-s SEED]\n");
    fprintf(stderr, "       wb check [-n N] [-s SEED]\n");  // @from 00.02
    fprintf(stderr, "       wb time [-n N]\n");             // @from 00.03
    exit(2);
}

/* The whole number in text, from min to max; anything else stops wb with
 * a message saying what option wanted it. */
static uint64_t number(const char *option, const char *text, uint64_t min, uint64_t max)
{
    char *end;
    errno = 0;
    unsigned long long v = strtoull(text, &end, 10);
    if (text[0] < '0' || text[0] > '9' || *end != '\0' || errno == ERANGE || v < min || v > max) {
        fprintf(stderr, "wb: %s wants a whole number from %llu to %llu, not '%s'\n", option,
                (unsigned long long)min, (unsigned long long)max, text);
        exit(2);
    }
    return v;
}

/* n floats, or stop: wb has nothing to do without them. */
static float *new_array(size_t n)
{
    float *x = malloc(n * sizeof *x);
    if (x == NULL) {
        fprintf(stderr, "wb: out of memory for %zu floats\n", n);
        exit(1);
    }
    return x;
}

/* One line of wb show: the name, then the first four values of x (fewer
 * when n is less than four). */
static void print_row(const char *name, const float *x, size_t n)
{
    // @build 00.01 a row of values
    printf("%-4s", name);
    for (size_t i = 0; i < n && i < 4; i++)
        printf(" %10.6f", x[i]);
    printf("\n");
    // @end
}

/* wb show: n and the seed, then the first values of a, b and add(a, b). */
static int show(size_t n, uint64_t seed)
{
    // @build 00.01 wb show
    float *a = new_array(n), *b = new_array(n), *out = new_array(n);
    rng_fill(a, n, seed);
    rng_fill(b, n, seed + 1);
    add(a, b, out, n);
    printf("n = %zu, seed = %llu\n", n, (unsigned long long)seed);
    print_row("a", a, n);
    print_row("b", b, n);
    print_row("add", out, n);
    free(a);
    free(b);
    free(out);
    return 0;
    // @end
}

/* wb check: add against add_ref on the same a and b, every element. A sum
 * of two floats is rounded the same way however the loop around it is
 * written, so nothing at all is allowed here: rtol and atol are both 0.
 * add's output starts as NaN, so an element add never writes cannot pass
 * by luck. The exit status is 0 when every element agrees. */
static int check(size_t n, uint64_t seed)
{
    // @build 00.02 wb check
    float *a = new_array(n), *b = new_array(n), *want = new_array(n), *got = new_array(n);
    rng_fill(a, n, seed);
    rng_fill(b, n, seed + 1);
    add_ref(a, b, want, n);
    for (size_t i = 0; i < n; i++)
        got[i] = NAN;
    add(a, b, got, n);
    int status = check_report("add", check_close(got, want, n, 0, 0));
    free(a);
    free(b);
    free(want);
    free(got);
    return status;
    // @end
}

// @from 00.03
/* What one timed call of add needs. */
struct add_args {
    const float *a, *b;
    float *out;
    size_t n;
};

// @end
/* One call of add, in the form bench calls a function: one pointer in. */
static void run_add(void *arg)
{
    // @build 00.03 one call of add, as bench calls it
    struct add_args *x = arg;
    add(x->a, x->b, x->out, x->n);
    // @end
}

/* wb time: add's fastest run on n elements and the median run, and the
 * bytes it moves a second at its fastest: for each element two floats
 * read and one written, 12 bytes. */
static int time_add(size_t n)
{
    // @build 00.03 wb time
    float *a = new_array(n), *b = new_array(n), *out = new_array(n);
    rng_fill(a, n, 1);
    rng_fill(b, n, 2);
    struct add_args args = {a, b, out, n};
    bench_opts o = {0, 0, 0, NULL};
    bench_result r = bench(run_add, &args, o);
    printf("add: n = %zu, %d runs, min %.4g ms, median %.4g ms", n, r.runs, r.min * 1e3, r.median * 1e3);
    if (r.min > 0)
        printf(", %.1f GB/s\n", 12.0 * (double)n / r.min / 1e9);
    else
        printf(", too fast for the clock: try a larger -n\n");
    free(a);
    free(b);
    free(out);
    return 0;
    // @end
}

int main(int argc, char **argv)
{
    if (argc < 2)
        usage();
    size_t n = 0;      /* 0: the command's own default */
    uint64_t seed = 1;
    for (int i = 2; i < argc; i++) {
        if (strcmp(argv[i], "-n") == 0 && i + 1 < argc) {
            n = number("-n", argv[++i], 1, MAX_N);
        } else if (strcmp(argv[i], "-s") == 0 && i + 1 < argc && strcmp(argv[i + 1], "0") == 0) {
            fprintf(stderr, "wb: -s 0: xorshift's state 0 never changes, so every number would be the same; "
                            "a seed is 1 to %llu\n", (unsigned long long)MAX_SEED);
            exit(2);
        } else if (strcmp(argv[i], "-s") == 0 && i + 1 < argc) {
            seed = number("-s", argv[++i], 1, MAX_SEED);
        } else {
            usage();
        }
    }
    if (strcmp(argv[1], "show") == 0)
        return show(n ? n : 1003, seed);
    if (strcmp(argv[1], "check") == 0)     // @from 00.02
        return check(n ? n : 1003, seed);  // @from 00.02
    if (strcmp(argv[1], "time") == 0)      // @from 00.03
        return time_add(n ? n : 1 << 24);  // @from 00.03
    usage();
}
