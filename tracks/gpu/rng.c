/*
 * rng.c - xorshift64*: numbers from a seed, the same on every machine.
 */
#include <stdio.h>
#include <stdlib.h>

#include "rng.h"

// @internal
/* Stands in for code a workspace has cut out: names the lesson whose code
 * is missing, and stops with exit status 3. */
_Noreturn void todo(const char *lesson, const char *what)
{
    fprintf(stderr, "gpu: %s: %s not written yet\n", lesson, what);
    exit(3);
}

// @end
/* The next 32 random bits. The state is stirred by xorshift's three steps
 * (shift right 12, left 25, right 27, each time XORed back in); the bits
 * given out are the top half of the state times 0x2545F4914F6CDD1D, since
 * the multiply mixes every bit of the state into the high ones. This is
 * the generator llama2.c samples with, bit for bit.
 * A state of 0 is a trap: every step leaves it 0, so every number is 0.
 * Nothing here prevents it; the programs refuse a seed of 0. */
uint32_t rng_u32(uint64_t *state)
{
    // @build 00.01 xorshift64*: the next 32 bits
    uint64_t x = *state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    *state = x;
    return (uint32_t)((x * 0x2545F4914F6CDD1DULL) >> 32);
    // @end
}

/* The next number in [0, 1): the top 24 of 32 random bits, over 2^24. A
 * float holds 24 bits exactly, so every number it can give is exact. */
float rng_f32(uint64_t *state)
{
    // @build 00.01 a float in [0, 1)
    return (float)(rng_u32(state) >> 8) / 16777216.0f;
    // @end
}

/* Fill x[0..n) with numbers in [-1, 1), the same ones for the same seed.
 * The seed is the generator's first state, as in llama2.c, so it must not
 * be 0 (every number would be -1). */
void rng_fill(float *x, size_t n, uint64_t seed)
{
    // @build 00.01 an array from a seed
    uint64_t state = seed;
    for (size_t i = 0; i < n; i++)
        x[i] = 2 * rng_f32(&state) - 1;
    // @end
}
