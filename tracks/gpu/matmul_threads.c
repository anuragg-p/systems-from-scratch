/*
 * matmul_threads.c - blocked_rows on every core, the rows of c split
 * evenly between threads.
 *
 * Rows i0 to i1 of c depend only on the same rows of a, and on all of b:
 * they are a matrix multiply of their own, which a thread can do with no
 * other thread's help, writing nothing another thread writes.
 */
#define _DEFAULT_SOURCE /* sysconf's _SC_NPROCESSORS_ONLN, which a strict C11 build hides on Linux */

#include <pthread.h>
#include <unistd.h>

#include "matmul.h"

int matmul_thread_count = 0;

/* How many threads matmul_threads runs: matmul_thread_count when it is
 * above 0, otherwise the number of cores online; at most MAX_THREADS. */
int thread_count(void)
{
    // @build 01.05 how many threads
    int t = matmul_thread_count;
    if (t <= 0)
        t = (int)sysconf(_SC_NPROCESSORS_ONLN);
    if (t < 1)
        t = 1;
    if (t > MAX_THREADS)
        t = MAX_THREADS;
    return t;
    // @end
}

/* One thread's share of the work: the matrices, and its rows [i0, i1). */
struct share {
    const float *a, *b;
    float *c;
    int k, n, i0, i1;
};

/* What each thread runs: blocked_rows on its share. Returns nothing; the
 * share's rows of c are the result. */
static void *run_share(void *arg)
{
    // @build 01.05 one thread's share
    struct share *s = arg;
    blocked_rows(s->a, s->b, s->c, s->k, s->n, s->i0, s->i1);
    return NULL;
    // @end
}

/* c = a * b on thread_count() threads (never more than there are rows).
 * Thread t of T gets rows m * t / T up to m * (t + 1) / T. If a thread
 * cannot be started, its share is done here instead. Returns when every
 * thread has finished. */
void matmul_threads(const float *a, const float *b, float *c, int m, int k, int n)
{
    // @build 01.05 matmul_threads: the rows split between threads
    int count = thread_count();
    if (count > m)
        count = m;
    pthread_t threads[MAX_THREADS];
    struct share shares[MAX_THREADS];
    int started[MAX_THREADS];
    for (int t = 0; t < count; t++) {
        shares[t] = (struct share){a, b, c, k, n, m * t / count, m * (t + 1) / count};
        started[t] = pthread_create(&threads[t], NULL, run_share, &shares[t]) == 0;
        if (!started[t])
            run_share(&shares[t]);
    }
    for (int t = 0; t < count; t++)
        if (started[t])
            pthread_join(threads[t], NULL);
    // @end
}
