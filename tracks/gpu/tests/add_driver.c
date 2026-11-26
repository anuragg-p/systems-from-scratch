/*
 * add_driver.c - for the tests (not shown to learners): add against
 * add_ref, bit for bit, with canaries either side of add's output.
 *
 * Reads lines "N SEED" from stdin; for each, fills a and b from rng_fill
 * (SEED and SEED + 1), runs add_ref and add, and prints one line:
 *   ok N
 *   fail N <what>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "add.h"
#include "rng.h"

#define CANARIES 16

/* Floats that no sum of two numbers in [-1, 1) can be. */
static void fill_canaries(float *x, int count)
{
    for (int i = 0; i < count; i++)
        x[i] = 1234.5f + (float)i;
}

static void *must(void *p)
{
    if (p == NULL) {
        fprintf(stderr, "add_driver: out of memory\n");
        exit(1);
    }
    return p;
}

int main(void)
{
    size_t n;
    unsigned long long seed;
    while (scanf("%zu %llu", &n, &seed) == 2) {
        float *a = must(malloc((n + 1) * sizeof *a)), *b = must(malloc((n + 1) * sizeof *b));
        float *a0 = must(malloc((n + 1) * sizeof *a)), *b0 = must(malloc((n + 1) * sizeof *b));
        float *want = must(malloc((n + 1) * sizeof *want));
        float *space = must(malloc((n + 2 * CANARIES) * sizeof *space));
        float guard[2 * CANARIES];
        float *got = space + CANARIES;
        rng_fill(a, n, seed);
        rng_fill(b, n, seed + 1);
        memcpy(a0, a, n * sizeof *a);
        memcpy(b0, b, n * sizeof *b);
        add_ref(a, b, want, n);
        fill_canaries(space, CANARIES);
        fill_canaries(space + CANARIES + n, CANARIES);
        for (size_t i = 0; i < n; i++)
            got[i] = -1234.5f;
        add(a, b, got, n);

        const char *what = NULL;
        size_t where = 0;
        for (size_t i = 0; i < n && what == NULL; i++)
            if (memcmp(&got[i], &want[i], sizeof got[i]) != 0) {
                what = "differs from add_ref at";
                where = i;
            }
        fill_canaries(guard, CANARIES);
        fill_canaries(guard + CANARIES, CANARIES);
        if (what == NULL && memcmp(space, guard, CANARIES * sizeof *space) != 0)
            what = "wrote before out[0]";
        if (what == NULL && memcmp(space + CANARIES + n, guard + CANARIES, CANARIES * sizeof *space) != 0)
            what = "wrote past out[n - 1]";
        if (what == NULL && (memcmp(a, a0, n * sizeof *a) != 0 || memcmp(b, b0, n * sizeof *b) != 0))
            what = "changed a or b";
        if (what == NULL)
            printf("ok %zu\n", n);
        else if (strcmp(what, "differs from add_ref at") == 0)
            printf("fail %zu %s %zu: got %a, want %a\n", n, what, where, got[where], want[where]);
        else
            printf("fail %zu %s\n", n, what);
        fflush(stdout);
        free(a);
        free(b);
        free(a0);
        free(b0);
        free(want);
        free(space);
    }
    return 0;
}
