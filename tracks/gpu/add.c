/*
 * add.c - the plain version of out = a + b, and the version under test.
 */
#include "add.h"

/* out[i] = a[i] + b[i] for every i, one element at a time. */
void add_ref(const float *a, const float *b, float *out, size_t n)
{
    // @build 00.01 add_ref: one element at a time
    for (size_t i = 0; i < n; i++)
        out[i] = a[i] + b[i];
    // @end
}

/* The same sums, four elements a pass; then the last n % 4 elements (the
 * tail) one at a time. The test is i + 4 <= n, not i < n - 3: n is
 * unsigned, and n - 3 for n below 3 is a huge number. */
void add(const float *a, const float *b, float *out, size_t n)
{
    // @build 00.01 add: four at a time, then the tail
    size_t i = 0;
    for (; i + 4 <= n; i += 4) {
        out[i] = a[i] + b[i];
        out[i + 1] = a[i + 1] + b[i + 1];
        out[i + 2] = a[i + 2] + b[i + 2];
        out[i + 3] = a[i + 3] + b[i + 3];
    }
    for (; i < n; i++)
        out[i] = a[i] + b[i];
    // @end
}
