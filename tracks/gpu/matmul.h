/*
 * matmul.h - matrix multiply, every way module 01 writes it.
 *
 * Every variant has the same signature and does the same arithmetic:
 * c[m][n] = a[m][k] * b[k][n], single precision, all three matrices stored
 * row by row (row i of a starts at a[i * k], of b at b[i * n]). c may hold
 * anything on entry: a variant sets every element of it, it never adds to
 * what is there. c must not overlap a or b. The indexes are ints, so each
 * matrix must have fewer than 2^31 elements (8 GiB of floats).
 */
#ifndef MATMUL_H
#define MATMUL_H

#include <stddef.h>

/* The truth the others are held to: three loops, each element summed in a
 * double. It is never timed as a contestant. */
void matmul_ref(const float *a, const float *b, float *c, int m, int k, int n);

void matmul_ijk(const float *a, const float *b, float *c, int m, int k, int n);
void matmul_ikj(const float *a, const float *b, float *c, int m, int k, int n);     // @from 01.02
void matmul_simd(const float *a, const float *b, float *c, int m, int k, int n);    // @from 01.03
void matmul_blocked(const float *a, const float *b, float *c, int m, int k, int n); // @from 01.04
void matmul_threads(const float *a, const float *b, float *c, int m, int k, int n); // @from 01.05
void matmul_blas(const float *a, const float *b, float *c, int m, int k, int n);    // @from 01.05

// @from 01.03
/* Add to c[i][j], for i in [i0, i1) and j in [j0, j1), the sum over p in
 * [p0, p1) of a[i][p] * b[p][j]. k and n are the whole row lengths of a and
 * of b and c. The kernel under matmul_simd, and under every variant after
 * it (matmul_simd.c). */
void mul_add_tile(const float *a, const float *b, float *c, int k, int n, int i0, int i1, int p0, int p1,
                  int j0, int j1);

// @end
// @from 01.04
/* Rows [i0, i1) of c = a * b, a tile at a time (matmul_blocked.c). */
void blocked_rows(const float *a, const float *b, float *c, int k, int n, int i0, int i1);

// @end
// @from 01.05
/* How many threads matmul_threads runs: matmul_thread_count when it is
 * above 0 (mm -t sets it), otherwise one for each core of the machine;
 * never more than MAX_THREADS. */
#define MAX_THREADS 256
extern int matmul_thread_count;
int thread_count(void);

/* The BLAS library matmul_blas calls ("Accelerate", "OpenBLAS"), or NULL
 * when make found none: matmul_blas is then not to be called. */
extern const char *blas_name;

// @end
/* Every variant mm can run, by name, in the order of the lessons; a name
 * of NULL ends the table. */
typedef void matmul_fn(const float *a, const float *b, float *c, int m, int k, int n);
static const struct {
    const char *name;
    matmul_fn *fn;
} matmul_variants[] = {
    {"ijk", matmul_ijk},
    {"ikj", matmul_ikj},         // @from 01.02
    {"simd", matmul_simd},       // @from 01.03
    {"blocked", matmul_blocked}, // @from 01.04
    {"threads", matmul_threads}, // @from 01.05
    {"blas", matmul_blas},       // @from 01.05
    {NULL, NULL},
};

// @internal
_Noreturn void todo(const char *lesson, const char *what);
// @end

#endif
