/*
 * matmul.c - matrix multiply one float at a time: the reference, and the
 * plain loops in the order the formula reads and in the order the cache
 * likes.
 *
 * The Makefile builds this file with the compiler's vectorizer off. Left
 * on, the compiler turns these loops into vector code by itself, and the
 * steps from one variant to the next would measure something else.
 */
#include "matmul.h"

/* c = a * b the slow way that is easy to believe: for each element of c,
 * the sum over p of a[i][p] * b[p][j], kept in a double. A double carries
 * 29 more bits than a float, so its rounding errors are hundreds of
 * millions of times smaller: next to a float sum, it is the exact answer
 * rounded once, at the end. */
void matmul_ref(const float *a, const float *b, float *c, int m, int k, int n)
{
    // @build 01.01 matmul_ref: each sum kept in a double
    for (int i = 0; i < m; i++)
        for (int j = 0; j < n; j++) {
            double sum = 0;
            for (int p = 0; p < k; p++)
                sum += (double)a[i * k + p] * b[p * n + j];
            c[i * n + j] = (float)sum;
        }
    // @end
}

/* The three loops in the order the formula reads: for each row i and
 * column j of c, the sum over p of a[i][p] * b[p][j], in a float. The
 * inner loop walks down a column of b, so each step jumps a whole row of
 * b (n floats) ahead in memory. */
void matmul_ijk(const float *a, const float *b, float *c, int m, int k, int n)
{
    // @build 01.01 matmul_ijk: three loops
    for (int i = 0; i < m; i++)
        for (int j = 0; j < n; j++) {
            float sum = 0;
            for (int p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
    // @end
}

/* The same sums with the two inner loops swapped. Row i of c is set to 0;
 * then for each p, a[i][p] times row p of b is added to it. The inner loop
 * now walks along a row of b and a row of c, the next float each step,
 * which is the order memory is fastest to read in. */
void matmul_ikj(const float *a, const float *b, float *c, int m, int k, int n)
{
    // @build 01.02 matmul_ikj: the inner loop along the rows
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++)
            c[i * n + j] = 0;
        for (int p = 0; p < k; p++) {
            float aip = a[i * k + p];
            for (int j = 0; j < n; j++)
                c[i * n + j] += aip * b[p * n + j];
        }
    }
    // @end
}
