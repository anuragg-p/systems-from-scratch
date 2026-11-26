/*
 * matmul_simd.c - matrix multiply a vector of floats at a time, and the
 * kernel every faster variant after it reuses.
 *
 * vec is one of the compiler's vector types: LANES floats that a single
 * operation adds or multiplies, lane by lane. LANES is the width of the
 * machine's own vector registers: 8 floats (256 bits) on x86-64 with AVX2,
 * which the Makefile's -march=native turns on where the machine has it;
 * 4 floats (128 bits) otherwise, which on arm64 is a NEON register and on
 * x86-64 without AVX2 an SSE one. The loops are written once, in LANES.
 */
#include <string.h>

#include "matmul.h"

#if defined(__AVX2__)
#define LANES 8
#else
#define LANES 4
#endif

typedef float vec __attribute__((vector_size(LANES * sizeof(float))));

/* The LANES floats at p, which need not be aligned to anything. memcpy is
 * the way C reads bytes as another type; the compiler makes it one vector
 * load. */
static vec load(const float *p)
{
    // @build 01.03 a vector of floats in
    vec v;
    memcpy(&v, p, sizeof v);
    return v;
    // @end
}

/* v's floats written to p, which need not be aligned either. */
static void store(float *p, vec v)
{
    // @build 01.03 a vector of floats out
    memcpy(p, &v, sizeof v);
    // @end
}

/* x in every lane. */
static vec splat(float x)
{
    // @build 01.03 one float in every lane
    vec v;
    for (int lane = 0; lane < LANES; lane++)
        v[lane] = x;
    return v;
    // @end
}

/* Add to c[i][j], for i in [i0, i1) and j in [j0, j1), the sum over p in
 * [p0, p1) of a[i][p] * b[p][j]. For each row i, j goes LANES columns a
 * step, as vectors, and the columns left over at the end (fewer than
 * LANES) one at a time. p goes four values a step: each vector of c is
 * loaded once, has four products added to it, and is stored once, where
 * one value of p a step would load and store it four times. Values of p
 * left over (fewer than four) are done one at a time. */
void mul_add_tile(const float *a, const float *b, float *c, int k, int n, int i0, int i1, int p0, int p1,
                  int j0, int j1)
{
    // @build 01.03 mul_add_tile: a vector of columns and four values of p a step
    for (int i = i0; i < i1; i++) {
        float *ci = c + i * n;
        int p = p0;
        for (; p + 4 <= p1; p += 4) {
            float s0 = a[i * k + p], s1 = a[i * k + p + 1];
            float s2 = a[i * k + p + 2], s3 = a[i * k + p + 3];
            const float *b0 = b + p * n, *b1 = b0 + n, *b2 = b1 + n, *b3 = b2 + n;
            vec a0 = splat(s0), a1 = splat(s1), a2 = splat(s2), a3 = splat(s3);
            int j = j0;
            for (; j + LANES <= j1; j += LANES) {
                vec cv = load(ci + j);
                cv += a0 * load(b0 + j);
                cv += a1 * load(b1 + j);
                cv += a2 * load(b2 + j);
                cv += a3 * load(b3 + j);
                store(ci + j, cv);
            }
            for (; j < j1; j++) {
                float cj = ci[j];
                cj += s0 * b0[j];
                cj += s1 * b1[j];
                cj += s2 * b2[j];
                cj += s3 * b3[j];
                ci[j] = cj;
            }
        }
        for (; p < p1; p++) {
            float s = a[i * k + p];
            const float *bp = b + p * n;
            vec av = splat(s);
            int j = j0;
            for (; j + LANES <= j1; j += LANES)
                store(ci + j, load(ci + j) + av * load(bp + j));
            for (; j < j1; j++)
                ci[j] += s * bp[j];
        }
    }
    // @end
}

/* c = a * b in vectors: c set to 0, then one mul_add_tile whose ranges are
 * the part of the product to do; here, all of it. */
void matmul_simd(const float *a, const float *b, float *c, int m, int k, int n)
{
    // @build 01.03 matmul_simd: c set to 0, then the whole product at once
    for (size_t x = 0; x < (size_t)m * (size_t)n; x++)
        c[x] = 0;
    mul_add_tile(a, b, c, k, n, 0, m, 0, k, 0, n);
    // @end
}
