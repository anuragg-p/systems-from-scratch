/*
 * matmul_driver.c - for the tests (not shown to learners): every matmul
 * variant on the shapes the test gives, held to matmul_ref.
 *
 * Reads commands from stdin, one a line, and answers each with one line.
 * a is m x k from rng_fill(SEED), b is k x n from rng_fill(SEED + 1). NAME
 * is "ref" or a name in matmul_variants.
 *
 *   check NAME M K N SEED     NAME's c against matmul_ref's, at the module's
 *                             tolerance (rtol 1e-4, atol 1e-3). c starts as
 *                             NaN, with canaries either side; a and b must
 *                             come back unchanged.
 *                             -> "ok ERR ALLOWED" (the worst element, %a)
 *                                or "fail WHAT"
 *   vsblas NAME M K N SEED    the same against matmul_blas's c
 *   identity NAME N SEED      a (n x n) times I, and I times a: both exactly a
 *                             -> "ok" or "fail WHAT"
 *   wrong WHICH M K N SEED    one of three wrong multiplies (lastcol: the last
 *                             column of c left 0; transposed: b read as if
 *                             stored by columns; dropterm: the last term of
 *                             every sum left out) through check_close
 *                             -> "caught BAD" or "missed"
 *   dump NAME M K N SEED      -> "c V1 .. V(M*N)" in %a
 *   tile M K N I0 I1 P0 P1 J0 J1 SEED
 *                             mul_add_tile on a c filled with a pattern: every
 *                             element outside rows [I0, I1) and columns [J0, J1)
 *                             exactly as it was, every one inside the pattern
 *                             plus the sum over p in [P0, P1), at the tolerance;
 *                             canaries either side; a and b unchanged
 *                             -> "ok" or "fail WHAT"
 *   rows M K N I0 I1 SEED     blocked_rows on rows [I0, I1) of a c filled with a
 *                             pattern: the other rows exactly as they were, those
 *                             rows matmul_ref's at the tolerance -> "ok" or "fail WHAT"
 *   offset F                  from now on a, b and c start F floats (0 to 7)
 *                             past an aligned address -> "offset F"
 *   blas                      -> "blas NAME" or "blas none"
 *   threads T                 sets matmul_thread_count -> "threads T"
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "check.h"
#include "matmul.h"
#include "rng.h"

#define RTOL 1e-4
#define ATOL 1e-3
#define CANARIES 16

/* How many floats past an aligned address a, b and c start: a variant
 * must work on matrices at any address. */
static int offset;

static void *must(void *p)
{
    if (p == NULL) {
        fprintf(stderr, "matmul_driver: out of memory\n");
        exit(1);
    }
    return p;
}

/* A matrix, and the block it was allocated in (to free). */
typedef struct {
    float *block, *x;
} matrix;

/* rows x cols floats, plus room before and after for canaries, starting
 * offset floats past what malloc gave. */
static matrix new_matrix(int rows, int cols)
{
    size_t size = (size_t)rows * (size_t)cols;
    matrix m;
    m.block = must(malloc((size + 2 * CANARIES + 8) * sizeof(float)));
    m.x = m.block + offset + CANARIES;
    return m;
}

static matmul_fn *variant(const char *name)
{
    if (strcmp(name, "ref") == 0)
        return matmul_ref;
    for (int v = 0; matmul_variants[v].name != NULL; v++)
        if (strcmp(matmul_variants[v].name, name) == 0)
            return matmul_variants[v].fn;
    return NULL;
}

/* ---------------------------------------------------------- three wrong multiplies */

/* The last column of c is never computed (left 0). */
static void wrong_lastcol(const float *a, const float *b, float *c, int m, int k, int n)
{
    for (int i = 0; i < m; i++)
        for (int j = 0; j < n; j++) {
            float sum = 0;
            for (int p = 0; j < n - 1 && p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}

/* b read as if it were stored column by column. */
static void wrong_transposed(const float *a, const float *b, float *c, int m, int k, int n)
{
    for (int i = 0; i < m; i++)
        for (int j = 0; j < n; j++) {
            float sum = 0;
            for (int p = 0; p < k; p++)
                sum += a[i * k + p] * b[j * k + p];
            c[i * n + j] = sum;
        }
}

/* Every sum without its last term. */
static void wrong_dropterm(const float *a, const float *b, float *c, int m, int k, int n)
{
    for (int i = 0; i < m; i++)
        for (int j = 0; j < n; j++) {
            float sum = 0;
            for (int p = 0; p < k - 1; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}

/* ---------------------------------------------------------- one run, guarded */

/* fn(a, b) into a c that starts as NaN with canaries either side. Returns
 * c, or a c with x NULL (and *what set) when fn wrote outside c or changed
 * a or b. */
static matrix guarded(matmul_fn *fn, const float *a, const float *b, int m, int k, int n, const char **what)
{
    size_t size = (size_t)m * (size_t)n, asize = (size_t)m * (size_t)k, bsize = (size_t)k * (size_t)n;
    matrix c = new_matrix(m, n);
    float *a0 = must(malloc((asize + 1) * sizeof *a0)), *b0 = must(malloc((bsize + 1) * sizeof *b0));
    memcpy(a0, a, asize * sizeof *a);
    memcpy(b0, b, bsize * sizeof *b);
    for (int i = 0; i < CANARIES; i++) {
        c.x[-1 - i] = 4321.0f + (float)i;
        c.x[size + (size_t)i] = 8765.0f + (float)i;
    }
    for (size_t i = 0; i < size; i++)
        c.x[i] = NAN;
    fn(a, b, c.x, m, k, n);
    *what = NULL;
    for (int i = 0; i < CANARIES && *what == NULL; i++) {
        if (c.x[-1 - i] != 4321.0f + (float)i)
            *what = "wrote before c[0]";
        else if (c.x[size + (size_t)i] != 8765.0f + (float)i)
            *what = "wrote past c[m * n - 1]";
    }
    if (*what == NULL && (memcmp(a0, a, asize * sizeof *a) != 0 || memcmp(b0, b, bsize * sizeof *b) != 0))
        *what = "changed a or b";
    free(a0);
    free(b0);
    if (*what != NULL) {
        free(c.block);
        c.block = c.x = NULL;
    }
    return c;
}

/* a and b for a shape and a seed. */
static void inputs(int m, int k, int n, unsigned long long seed, matrix *a, matrix *b)
{
    *a = new_matrix(m, k);
    *b = new_matrix(k, n);
    rng_fill(a->x, (size_t)m * k, seed);
    rng_fill(b->x, (size_t)k * n, seed + 1);
}

/* NAME's c against the c of truth (matmul_ref, or matmul_blas). */
static void against(const char *name, matmul_fn *truth, int m, int k, int n, unsigned long long seed)
{
    matmul_fn *fn = variant(name);
    if (fn == NULL) {
        printf("fail no variant %s\n", name);
        return;
    }
    matrix a, b;
    inputs(m, k, n, seed, &a, &b);
    const char *what;
    matrix want = guarded(truth, a.x, b.x, m, k, n, &what);
    if (want.x == NULL) {
        printf("fail the reference %s\n", what);
    } else {
        matrix got = guarded(fn, a.x, b.x, m, k, n, &what);
        if (got.x == NULL) {
            printf("fail %s\n", what);
        } else {
            check_result r = check_close(got.x, want.x, (size_t)m * n, RTOL, ATOL);
            if (r.bad == 0)
                printf("ok %a %a\n", r.err, r.allowed);
            else
                printf("fail %zu of %zu outside the tolerance; worst at [%zu]: got %.9g, want %.9g\n", r.bad,
                       r.n, r.worst, (double)r.got, (double)r.want);
        }
        free(got.block);
    }
    free(want.block);
    free(a.block);
    free(b.block);
}

/* a times I and I times a, both exactly a. */
static void identity(const char *name, int n, unsigned long long seed)
{
    matmul_fn *fn = variant(name);
    if (fn == NULL) {
        printf("fail no variant %s\n", name);
        return;
    }
    matrix a = new_matrix(n, n), eye = new_matrix(n, n);
    rng_fill(a.x, (size_t)n * n, seed);
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            eye.x[i * n + j] = i == j ? 1.0f : 0.0f;
    const char *what;
    matrix c = guarded(fn, a.x, eye.x, n, n, n, &what);
    matrix d = {NULL, NULL};
    if (c.x == NULL)
        printf("fail a * I %s\n", what);
    else if (check_close(c.x, a.x, (size_t)n * n, 0, 0).bad != 0)
        printf("fail a * I is not a\n");
    else if ((d = guarded(fn, eye.x, a.x, n, n, n, &what)).x == NULL)
        printf("fail I * a %s\n", what);
    else if (check_close(d.x, a.x, (size_t)n * n, 0, 0).bad != 0)
        printf("fail I * a is not a\n");
    else
        printf("ok\n");
    free(c.block);
    free(d.block);
    free(a.block);
    free(eye.block);
}

static void wrong(const char *which, int m, int k, int n, unsigned long long seed)
{
    matmul_fn *fn = NULL;
    if (strcmp(which, "lastcol") == 0)
        fn = wrong_lastcol;
    else if (strcmp(which, "transposed") == 0)
        fn = wrong_transposed;
    else if (strcmp(which, "dropterm") == 0)
        fn = wrong_dropterm;
    if (fn == NULL) {
        printf("fail no wrong multiply %s\n", which);
        return;
    }
    matrix a, b, want = new_matrix(m, n), got = new_matrix(m, n);
    inputs(m, k, n, seed, &a, &b);
    matmul_ref(a.x, b.x, want.x, m, k, n);
    fn(a.x, b.x, got.x, m, k, n);
    check_result r = check_close(got.x, want.x, (size_t)m * n, RTOL, ATOL);
    if (r.bad > 0)
        printf("caught %zu\n", r.bad);
    else
        printf("missed\n");
    free(a.block);
    free(b.block);
    free(want.block);
    free(got.block);
}

/* What c holds before a tile or rows are added to it: small numbers that
 * differ from their neighbours. */
static float pattern(size_t x)
{
    return (float)((int)(x % 13) - 6) * 0.125f;
}

/* A c of m x n floats holding the pattern, with canaries either side. */
static matrix patterned(int m, int n)
{
    size_t size = (size_t)m * (size_t)n;
    matrix c = new_matrix(m, n);
    for (int i = 0; i < CANARIES; i++) {
        c.x[-1 - i] = 4321.0f + (float)i;
        c.x[size + (size_t)i] = 8765.0f + (float)i;
    }
    for (size_t x = 0; x < size; x++)
        c.x[x] = pattern(x);
    return c;
}

/* Whether a call wrote over c's canaries, or changed a or b (a0 and b0 are
 * copies made before it): NULL, or what it did. */
static const char *damage(const matrix *c, size_t size, const float *a, const float *a0, size_t asize,
                          const float *b, const float *b0, size_t bsize)
{
    for (int i = 0; i < CANARIES; i++) {
        if (c->x[-1 - i] != 4321.0f + (float)i)
            return "wrote before c[0]";
        if (c->x[size + (size_t)i] != 8765.0f + (float)i)
            return "wrote past c[m * n - 1]";
    }
    if (memcmp(a, a0, asize * sizeof *a) != 0 || memcmp(b, b0, bsize * sizeof *b) != 0)
        return "changed a or b";
    return NULL;
}

/* Whether c[x] still holds the pattern, bit for bit. */
static int untouched(const float *c, size_t x)
{
    float was = pattern(x);
    return memcmp(&c[x], &was, sizeof was) == 0;
}

/* mul_add_tile on one tile of a patterned c. */
static void tile(int m, int k, int n, int i0, int i1, int p0, int p1, int j0, int j1, unsigned long long seed)
{
    size_t size = (size_t)m * n, asize = (size_t)m * k, bsize = (size_t)k * n;
    matrix a, b;
    inputs(m, k, n, seed, &a, &b);
    float *a0 = must(malloc((asize + 1) * sizeof *a0)), *b0 = must(malloc((bsize + 1) * sizeof *b0));
    memcpy(a0, a.x, asize * sizeof *a0);
    memcpy(b0, b.x, bsize * sizeof *b0);
    matrix c = patterned(m, n);
    float *got = must(malloc((size + 1) * sizeof *got)), *want = must(malloc((size + 1) * sizeof *want));
    size_t inside = 0;
    int bad_i = -1, bad_j = -1;

    mul_add_tile(a.x, b.x, c.x, k, n, i0, i1, p0, p1, j0, j1);
    const char *what = damage(&c, size, a.x, a0, asize, b.x, b0, bsize);
    for (int i = 0; i < m && what == NULL && bad_i < 0; i++)
        for (int j = 0; j < n && bad_i < 0; j++) {
            size_t x = (size_t)i * n + (size_t)j;
            if (i >= i0 && i < i1 && j >= j0 && j < j1) {
                double sum = pattern(x);
                for (int p = p0; p < p1; p++)
                    sum += (double)a.x[(size_t)i * k + (size_t)p] * b.x[(size_t)p * n + (size_t)j];
                got[inside] = c.x[x];
                want[inside++] = (float)sum;
            } else if (!untouched(c.x, x)) {
                bad_i = i;
                bad_j = j;
            }
        }
    if (what != NULL) {
        printf("fail %s\n", what);
    } else if (bad_i >= 0) {
        printf("fail changed c[%d][%d], outside the tile\n", bad_i, bad_j);
    } else {
        check_result r = check_close(got, want, inside, RTOL, ATOL);
        if (r.bad == 0)
            printf("ok\n");
        else
            printf("fail %zu of %zu in the tile outside the tolerance; worst got %.9g, want %.9g\n", r.bad, r.n,
                   (double)r.got, (double)r.want);
    }
    free(got);
    free(want);
    free(a0);
    free(b0);
    free(a.block);
    free(b.block);
    free(c.block);
}

/* blocked_rows on rows [i0, i1) of a patterned c. */
static void rows(int m, int k, int n, int i0, int i1, unsigned long long seed)
{
    size_t size = (size_t)m * n, asize = (size_t)m * k, bsize = (size_t)k * n;
    matrix a, b, ref = new_matrix(m, n);
    inputs(m, k, n, seed, &a, &b);
    matmul_ref(a.x, b.x, ref.x, m, k, n);
    float *a0 = must(malloc((asize + 1) * sizeof *a0)), *b0 = must(malloc((bsize + 1) * sizeof *b0));
    memcpy(a0, a.x, asize * sizeof *a0);
    memcpy(b0, b.x, bsize * sizeof *b0);
    matrix c = patterned(m, n);

    blocked_rows(a.x, b.x, c.x, k, n, i0, i1);
    const char *what = damage(&c, size, a.x, a0, asize, b.x, b0, bsize);
    int bad = -1;
    for (int i = 0; i < m && bad < 0; i++)
        for (int j = 0; j < n && (i < i0 || i >= i1) && bad < 0; j++)
            if (!untouched(c.x, (size_t)i * n + (size_t)j))
                bad = i;
    if (what != NULL) {
        printf("fail %s\n", what);
    } else if (bad >= 0) {
        printf("fail changed row %d, outside [%d, %d)\n", bad, i0, i1);
    } else {
        size_t first = (size_t)i0 * n, count = (size_t)(i1 - i0) * n;
        check_result r = check_close(c.x + first, ref.x + first, count, RTOL, ATOL);
        if (r.bad == 0)
            printf("ok\n");
        else
            printf("fail %zu of %zu in the rows outside the tolerance; worst got %.9g, want %.9g\n", r.bad,
                   r.n, (double)r.got, (double)r.want);
    }
    free(a0);
    free(b0);
    free(a.block);
    free(b.block);
    free(c.block);
    free(ref.block);
}

static void dump(const char *name, int m, int k, int n, unsigned long long seed)
{
    matmul_fn *fn = variant(name);
    if (fn == NULL) {
        printf("fail no variant %s\n", name);
        return;
    }
    matrix a, b, c = new_matrix(m, n);
    inputs(m, k, n, seed, &a, &b);
    fn(a.x, b.x, c.x, m, k, n);
    printf("c");
    for (int i = 0; i < m * n; i++)
        printf(" %a", (double)c.x[i]);
    printf("\n");
    free(a.block);
    free(b.block);
    free(c.block);
}

int main(void)
{
    char command[16], name[32];
    int m, k, n, t[6];
    unsigned long long seed;
    while (scanf("%15s", command) == 1) {
        if (strcmp(command, "check") == 0 && scanf("%31s %d %d %d %llu", name, &m, &k, &n, &seed) == 5)
            against(name, matmul_ref, m, k, n, seed);
        else if (strcmp(command, "vsblas") == 0 && scanf("%31s %d %d %d %llu", name, &m, &k, &n, &seed) == 5)
            against(name, matmul_blas, m, k, n, seed);
        else if (strcmp(command, "identity") == 0 && scanf("%31s %d %llu", name, &n, &seed) == 3)
            identity(name, n, seed);
        else if (strcmp(command, "wrong") == 0 && scanf("%31s %d %d %d %llu", name, &m, &k, &n, &seed) == 5)
            wrong(name, m, k, n, seed);
        else if (strcmp(command, "dump") == 0 && scanf("%31s %d %d %d %llu", name, &m, &k, &n, &seed) == 5)
            dump(name, m, k, n, seed);
        else if (strcmp(command, "offset") == 0 && scanf("%d", &n) == 1 && n >= 0 && n < 8) {
            offset = n;
            printf("offset %d\n", n);
        } else if (strcmp(command, "tile") == 0 &&
                   scanf("%d %d %d %d %d %d %d %d %d %llu", &m, &k, &n, &t[0], &t[1], &t[2], &t[3], &t[4], &t[5],
                         &seed) == 10)
            tile(m, k, n, t[0], t[1], t[2], t[3], t[4], t[5], seed);
        else if (strcmp(command, "rows") == 0 && scanf("%d %d %d %d %d %llu", &m, &k, &n, &t[0], &t[1], &seed) == 6)
            rows(m, k, n, t[0], t[1], seed);
        else if (strcmp(command, "blas") == 0)
            printf("blas %s\n", blas_name != NULL ? blas_name : "none");
        else if (strcmp(command, "threads") == 0 && scanf("%d", &n) == 1) {
            matmul_thread_count = n;
            printf("threads %d\n", n);
        } else {
            fprintf(stderr, "matmul_driver: cannot read command %s\n", command);
            return 1;
        }
        fflush(stdout);
    }
    return 0;
}
