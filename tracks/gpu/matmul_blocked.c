/*
 * matmul_blocked.c - mul_add_tile a tile at a time, so that the pieces of
 * a, b and c in use stay in the cache.
 *
 * matmul_simd does the whole product in one call: for each row of c it
 * runs through all of b, which for a large b no cache holds. Here the
 * product is cut into tiles of MM_BLOCK rows, MM_BLOCK values of p and
 * MM_BLOCK columns, and the tile of b in use is read MM_BLOCK times (once
 * for each row of the tile) while it is still in the cache.
 */
#include <stddef.h>

#include "matmul.h"

/* The side of a tile. A tile of 128 x 128 floats is 64 KiB. */
#define MM_BLOCK 128

/* Rows [i0, i1) of c = a * b, a tile at a time: those rows of c set to 0,
 * then mul_add_tile on each tile, MM_BLOCK rows at a time, and within them
 * MM_BLOCK values of p by MM_BLOCK columns at a time. The last tile along
 * a side may be smaller. */
void blocked_rows(const float *a, const float *b, float *c, int k, int n, int i0, int i1)
{
    // @build 01.04 blocked_rows: the rows, a tile at a time
    for (size_t x = (size_t)i0 * (size_t)n; x < (size_t)i1 * (size_t)n; x++)
        c[x] = 0;
    for (int r0 = i0; r0 < i1; r0 += MM_BLOCK) {
        int r1 = r0 + MM_BLOCK < i1 ? r0 + MM_BLOCK : i1;
        for (int p0 = 0; p0 < k; p0 += MM_BLOCK) {
            int p1 = p0 + MM_BLOCK < k ? p0 + MM_BLOCK : k;
            for (int j0 = 0; j0 < n; j0 += MM_BLOCK) {
                int j1 = j0 + MM_BLOCK < n ? j0 + MM_BLOCK : n;
                mul_add_tile(a, b, c, k, n, r0, r1, p0, p1, j0, j1);
            }
        }
    }
    // @end
}

/* c = a * b, a tile at a time: blocked_rows over all of c's rows. */
void matmul_blocked(const float *a, const float *b, float *c, int m, int k, int n)
{
    // @build 01.04 matmul_blocked: every row
    blocked_rows(a, b, c, k, n, 0, m);
    // @end
}
