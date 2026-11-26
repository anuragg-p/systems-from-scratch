/*
 * check.c - got against want, element by element, with a tolerance.
 */
#include <math.h>
#include <stdio.h>

#include "check.h"

/* How far an error is past its limit: err / allowed, so 1 is exactly at
 * the limit and anything above 1 is outside it. With nothing allowed, any
 * error at all is infinitely far. */
static double over(double err, double allowed)
{
    // @build 00.02 how far past the limit
    if (allowed > 0)
        return err / allowed;
    return err > 0 ? INFINITY : 0;
    // @end
}

/* Is an element with this error and allowance further outside than the
 * worst one so far? A NaN is further than anything; then the one further
 * past its limit; then, at the same distance, the larger error. A tie
 * keeps the earlier element. */
static int further(double err, double allowed, double worst_err, double worst_allowed)
{
    // @build 00.02 which of two elements is worse
    if (isnan(worst_err))
        return 0;
    if (isnan(err))
        return 1;
    double a = over(err, allowed), b = over(worst_err, worst_allowed);
    if (a != b)
        return a > b;
    return err > worst_err;
    // @end
}

/* Compare got[0..n) with want[0..n), and count the elements outside the
 * tolerance. An element is good when |got - want| <= atol + rtol * |want|.
 * A NaN on either side is bad (NaN is close to nothing, itself included);
 * an infinity is close only to the same infinity, so nothing is allowed
 * around an infinite want. Also finds the worst element, for the report. */
check_result check_close(const float *got, const float *want, size_t n, double rtol, double atol)
{
    // @build 00.02 check_close: each element against its allowance
    check_result r = {n, 0, 0, 0, 0, 0, 0};
    for (size_t i = 0; i < n; i++) {
        double g = got[i], w = want[i];
        double allowed = isfinite(w) ? atol + rtol * fabs(w) : 0;
        double err;
        if (isnan(g) || isnan(w))
            err = NAN;
        else if (g == w)
            err = 0;            /* equal: two infinities of the same sign too */
        else
            err = fabs(g - w);  /* infinite when one side is */
        if (!(err <= allowed))  /* written so that a NaN error is bad */
            r.bad++;
        if (i == 0 || further(err, allowed, r.err, r.allowed)) {
            r.worst = i;
            r.got = got[i];
            r.want = want[i];
            r.err = err;
            r.allowed = allowed;
        }
    }
    return r;
    // @end
}

/* Print one line about r under name: ok and the worst error, or FAIL and
 * the worst element. Returns 0 when every element was good, 1 if not. */
int check_report(const char *name, check_result r)
{
    // @build 00.02 check_report: one line
    if (r.n == 0) {
        printf("%s: ok, no elements to compare\n", name);
        return 0;
    }
    if (r.bad == 0) {
        printf("%s: ok, worst error %.3g at [%zu] of %zu (allowed %.3g)\n", name, r.err, r.worst, r.n,
               r.allowed);
        return 0;
    }
    printf("%s: FAIL, %zu of %zu wrong; worst at [%zu]: got %.9g, want %.9g (error %.3g, allowed %.3g)\n",
           name, r.bad, r.n, r.worst, r.got, r.want, r.err, r.allowed);
    return 1;
    // @end
}
