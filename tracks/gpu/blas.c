/*
 * blas.c - matmul_blas: the same multiply, done by the system's BLAS.
 *
 * BLAS is the standard interface to linear algebra libraries; sgemm is its
 * single precision matrix multiply, C = alpha * A * B + beta * C. The
 * Makefile says which library this machine has: Accelerate on macOS
 * (BLAS_ACCELERATE), OpenBLAS on Linux when it is installed
 * (BLAS_OPENBLAS), or none.
 */
#include <stdio.h>
#include <stdlib.h>

#include "matmul.h"

#if defined(BLAS_ACCELERATE)
#include <Accelerate/Accelerate.h>
const char *blas_name = "Accelerate";
#elif defined(BLAS_OPENBLAS)
#include <cblas.h>
const char *blas_name = "OpenBLAS";
#else
const char *blas_name = NULL;
#endif

#if defined(BLAS_ACCELERATE) || defined(BLAS_OPENBLAS)

/* c = a * b by cblas_sgemm: row-major, neither matrix transposed, alpha 1
 * and beta 0 (c's old values are not used). Each leading dimension (the
 * distance from one row to the next) is the row's length, but BLAS wants
 * at least 1 even for a matrix with no columns, so a side of 0 is passed
 * as a row length of 1. */
void matmul_blas(const float *a, const float *b, float *c, int m, int k, int n)
{
    // @build 01.05 matmul_blas: one call to the library
    int lda = k > 1 ? k : 1, ldb = n > 1 ? n : 1, ldc = n > 1 ? n : 1;
    cblas_sgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, m, n, k, 1.0f, a, lda, b, ldb, 0.0f, c, ldc);
    // @end
}

#else

/* Built without a BLAS: mm leaves blas out (blas_name is NULL), so this is
 * never called. If it is, it says so and stops. */
void matmul_blas(const float *a, const float *b, float *c, int m, int k, int n)
{
    (void)a;  /* unused: there is nothing to call */
    (void)b;
    (void)c;
    (void)m;
    (void)k;
    (void)n;
    fprintf(stderr, "matmul_blas: this build has no BLAS library\n");
    exit(1);
}

#endif
