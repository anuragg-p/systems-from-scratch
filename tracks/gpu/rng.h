/*
 * rng.h - numbers from a seed, the same on every machine.
 *
 * The generator is xorshift64*, the one llama2.c samples with: 64 bits of
 * state, stirred by three shifts for each number, and a multiply that
 * mixes the state into the 32 bits given out. Integer arithmetic only, so
 * the same seed gives the same numbers with any compiler on any machine:
 * that is what lets a lesson print them, and a test in another language
 * compute them again. The seed is the first state, and must not be 0.
 */
#ifndef RNG_H
#define RNG_H

#include <stddef.h>
#include <stdint.h>

uint32_t rng_u32(uint64_t *state);                /* the next 32 random bits */
float rng_f32(uint64_t *state);                   /* the next number in [0, 1), 24 random bits */
void rng_fill(float *x, size_t n, uint64_t seed); /* x[0..n) in [-1, 1), from seed (not 0) */

// @internal
/* Stands in for code a workspace has cut out (rng.c). */
_Noreturn void todo(const char *lesson, const char *what);
// @end

#endif
