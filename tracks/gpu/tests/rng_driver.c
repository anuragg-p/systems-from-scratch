/*
 * rng_driver.c - for the tests (not shown to learners): the generator's
 * numbers, for the test to hold to its own and to llama2.c's.
 *
 * Reads lines "STATE COUNT" from stdin; for each prints three lines, each
 * from a fresh state STATE:
 *   u32 V1 .. VCOUNT          rng_u32, in decimal
 *   f32 F1 .. FCOUNT          rng_f32, in %a
 *   fill X1 .. XCOUNT         rng_fill(x, COUNT, STATE), in %a
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "rng.h"

int main(void)
{
    unsigned long long seed;
    int count;
    while (scanf("%llu %d", &seed, &count) == 2 && count >= 0) {
        uint64_t state = seed;
        printf("u32");
        for (int i = 0; i < count; i++)
            printf(" %lu", (unsigned long)rng_u32(&state));
        state = seed;
        printf("\nf32");
        for (int i = 0; i < count; i++)
            printf(" %a", (double)rng_f32(&state));
        float *x = malloc(((size_t)count + 1) * sizeof *x);
        if (x == NULL)
            return 1;
        rng_fill(x, (size_t)count, seed);
        printf("\nfill");
        for (int i = 0; i < count; i++)
            printf(" %a", (double)x[i]);
        printf("\n");
        fflush(stdout);
        free(x);
    }
    return 0;
}
