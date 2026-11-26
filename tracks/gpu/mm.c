/*
 * mm.c - the matmul program: every variant listed, checked and timed.
 *
 *   mm list                    the variants this build has
 *   mm check [name...]         each one against matmul_ref, on a fixed set of shapes
 *   mm time [-n N] [name...]   each one on n x n matrices: its fastest run, its
 *                              GFLOP/s, and how many times faster than ijk it is
 *   -t T                       (check and time) matmul_threads runs T threads    @from 01.05
 *
 * With no names, every variant; names pick some, which still run in the
 * table's order. n is 1000 unless -n gives another. a and b come from
 * rng_fill with seeds 1 and 2.
 */
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bench.h"
#include "check.h"
#include "matmul.h"
#include "rng.h"

/* mm time's n: a round size that is not a power of two. At a multiple of
 * a large power of two (1024, 2048) each step down a column of b is a
 * multiple of 4 KiB, and ijk runs several times slower than at sizes
 * around it: worth a look (mm time -n 1024 ijk), not the size to compare
 * the variants at. */
#define DEFAULT_N 1000
#define MAX_N 8192

/* How close a variant must come to matmul_ref: within ATOL + RTOL * |want|
 * for every element. A float sum of k products of numbers in [-1, 1) drifts
 * from the exact sum by some sqrt(k) rounding errors of its running total,
 * about 1e-4 at k = 2048; a real mistake (a term left out, a wrong index)
 * moves an element by about 0.3. */
#define RTOL 1e-4
#define ATOL 1e-3

/* The shapes mm check runs, as m, k, n: tiny ones, sides that are no
 * multiple of 4, 8 or a tile, and one large enough to have many tiles. */
static const int shapes[][3] = {
    {1, 1, 1}, {3, 5, 7}, {8, 8, 8}, {33, 31, 65}, {64, 64, 64}, {100, 200, 50}, {129, 65, 63}, {256, 256, 256},
};

/* Say how mm is used, and stop with status 2. */
_Noreturn static void usage(void)
{
    // @from 01.05
    fprintf(stderr, "usage: mm list\n"
                    "       mm check [-t T] [name...]\n"
                    "       mm time [-n N] [-t T] [name...]\n");
    // @else
    // fprintf(stderr, "usage: mm list\n"
    //                 "       mm check [name...]\n"
    //                 "       mm time [-n N] [name...]\n");
    // @end
    exit(2);
}

/* The whole number in text, from 1 to max; anything else stops mm with a
 * message saying what option wanted it. */
static int number(const char *option, const char *text, int max)
{
    char *end;
    errno = 0;
    long v = strtol(text, &end, 10);
    if (text[0] < '0' || text[0] > '9' || *end != '\0' || errno == ERANGE || v < 1 || v > max) {
        fprintf(stderr, "mm: %s wants a whole number from 1 to %d, not '%s'\n", option, max, text);
        exit(2);
    }
    return (int)v;
}

/* A rows x cols matrix, or stop: mm has nothing to do without it. */
static float *new_matrix(int rows, int cols)
{
    float *x = malloc((size_t)rows * (size_t)cols * sizeof *x);
    if (x == NULL) {
        fprintf(stderr, "mm: out of memory for a %d x %d matrix\n", rows, cols);
        exit(1);
    }
    return x;
}

/* The variant called name, as its index in matmul_variants, or -1. */
static int find(const char *name)
{
    for (int v = 0; matmul_variants[v].name != NULL; v++)
        if (strcmp(matmul_variants[v].name, name) == 0)
            return v;
    return -1;
}

/* Is the variant called name to run? Every one is when no names were
 * given; otherwise only those named. */
static int chosen(const char *name, char **names, int count)
{
    if (count == 0)
        return 1;
    for (int i = 0; i < count; i++)
        if (strcmp(names[i], name) == 0)
            return 1;
    return 0;
}

// @from 01.05
/* Is the variant called name missing from this build? Only blas can be:
 * it needs a BLAS library, and on Linux there may be none. If it is
 * missing, says so on stderr, and how to get one. */
static int missing(const char *name)
{
    if (strcmp(name, "blas") != 0 || blas_name != NULL)
        return 0;
    fprintf(stderr, "mm: blas: make found no BLAS library. On Debian or Ubuntu: "
                    "sudo apt install libopenblas-dev pkg-config, then make clean && make\n");
    return 1;
}

// @end
/* mm list: the name of every variant this build has, one a line. */
static int list(void)
{
    for (int v = 0; matmul_variants[v].name != NULL; v++) {
        const char *name = matmul_variants[v].name;
        // @from 01.05
        if (missing(name))
            continue;
        if (strcmp(name, "blas") == 0) {
            printf("blas (%s)\n", blas_name);
            continue;
        }
        // @end
        printf("%s\n", name);
    }
    return 0;
}

/* mm check: each chosen variant on every shape in shapes[], held to
 * matmul_ref within the tolerance above. c starts as NaN every time, so
 * an element a variant never sets cannot pass by luck. One line a variant:
 * the first shape it fails on, or if it fails on none, the largest. The
 * exit status is 1 if any variant failed. */
static int check(char **names, int count)
{
    // @build 01.01 mm check
    int status = 0;
    int shape_count = (int)(sizeof shapes / sizeof shapes[0]);
    for (int v = 0; matmul_variants[v].name != NULL; v++) {
        const char *name = matmul_variants[v].name;
        if (!chosen(name, names, count))
            continue;
        if (missing(name)) // @from 01.05
            continue;      // @from 01.05
        for (int s = 0; s < shape_count; s++) {
            int m = shapes[s][0], k = shapes[s][1], n = shapes[s][2];
            float *a = new_matrix(m, k), *b = new_matrix(k, n);
            float *want = new_matrix(m, n), *got = new_matrix(m, n);
            rng_fill(a, (size_t)m * k, 1);
            rng_fill(b, (size_t)k * n, 2);
            matmul_ref(a, b, want, m, k, n);
            for (int i = 0; i < m * n; i++)
                got[i] = NAN;
            matmul_variants[v].fn(a, b, got, m, k, n);
            check_result r = check_close(got, want, (size_t)m * n, RTOL, ATOL);
            free(a);
            free(b);
            free(want);
            free(got);
            if (r.bad > 0 || s == shape_count - 1) {
                char label[64];
                snprintf(label, sizeof label, "%-7s %dx%dx%d", name, m, k, n);
                if (check_report(label, r) != 0)
                    status = 1;
                break;
            }
        }
    }
    return status;
    // @end
}

/* What one timed call of a variant needs: square matrices of side n. */
struct mm_args {
    matmul_fn *fn;
    const float *a, *b;
    float *c;
    int n;
};

/* One call of a variant, in the form bench calls a function. */
static void run_variant(void *arg)
{
    // @build 01.01 one call of a variant, as bench calls it
    struct mm_args *x = arg;
    x->fn(x->a, x->b, x->c, x->n, x->n, x->n);
    // @end
}

/* mm time: each chosen variant on n x n matrices. For each, its fastest
 * run; its speed in GFLOP/s, counting 2 n^3 operations (a multiply and an
 * add for each of the n terms of each of the n^2 sums); and how many
 * times faster than ijk it ran, when ijk was timed too (it runs first). */
static int time_variants(int n, char **names, int count)
{
    // @build 01.01 mm time
    float *a = new_matrix(n, n), *b = new_matrix(n, n), *c = new_matrix(n, n);
    rng_fill(a, (size_t)n * n, 1);
    rng_fill(b, (size_t)n * n, 2);
    double operations = 2.0 * n * n * n;
    double ijk = 0; /* ijk's fastest run, once it has been timed */
    printf("n = %d\n", n);
    if (chosen("threads", names, count))         // @from 01.05
        printf("threads = %d\n", thread_count()); // @from 01.05
    printf("%-8s %10s %10s %7s\n", "variant", "min ms", "GFLOP/s", "vs ijk");
    for (int v = 0; matmul_variants[v].name != NULL; v++) {
        const char *name = matmul_variants[v].name;
        if (!chosen(name, names, count))
            continue;
        if (missing(name)) // @from 01.05
            continue;      // @from 01.05
        struct mm_args args = {matmul_variants[v].fn, a, b, c, n};
        bench_opts o = {0, 0, 0, NULL};
        bench_result r = bench(run_variant, &args, o);
        if (strcmp(name, "ijk") == 0)
            ijk = r.min;
        if (r.min > 0)
            printf("%-8s %10.3f %10.2f", name, r.min * 1e3, operations / r.min / 1e9);
        else
            printf("%-8s %10.3f %10s", name, r.min * 1e3, "-");
        if (ijk > 0 && r.min > 0)
            printf(" %6.1fx\n", ijk / r.min);
        else
            printf(" %7s\n", "-");
    }
    free(a);
    free(b);
    free(c);
    return 0;
    // @end
}

int main(int argc, char **argv)
{
    if (argc < 2)
        usage();
    const char *command = argv[1];
    int n = DEFAULT_N;
    char **names = malloc((size_t)argc * sizeof *names);
    int count = 0;
    if (names == NULL)
        return 1;
    for (int i = 2; i < argc; i++) {
        if (strcmp(argv[i], "-n") == 0 && i + 1 < argc && strcmp(command, "time") == 0)
            n = number("-n", argv[++i], MAX_N);
        else if (strcmp(argv[i], "-t") == 0 && i + 1 < argc && strcmp(command, "list") != 0) // @from 01.05
            matmul_thread_count = number("-t", argv[++i], MAX_THREADS);                     // @from 01.05
        else if (argv[i][0] == '-')
            usage();
        else if (find(argv[i]) < 0) {
            fprintf(stderr, "mm: no variant called '%s' (mm list names them)\n", argv[i]);
            exit(2);
        } else
            names[count++] = argv[i];
    }
    int status;
    if (strcmp(command, "list") == 0 && count == 0)
        status = list();
    else if (strcmp(command, "check") == 0)
        status = check(names, count);
    else if (strcmp(command, "time") == 0)
        status = time_variants(n, names, count);
    else
        usage();
    free(names);
    return status;
}
