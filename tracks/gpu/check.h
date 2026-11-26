/*
 * check.h - is an answer close enough to the reference, and if not, where
 * is it furthest off?
 *
 * An element is good when |got - want| <= atol + rtol * |want|, the rule
 * numpy.isclose uses. atol is the error allowed near zero, rtol the error
 * allowed in proportion to the value. With both 0 the two must be equal.
 */
#ifndef CHECK_H
#define CHECK_H

#include <stddef.h>

typedef struct {
    size_t n, bad;       /* elements compared; elements outside the tolerance */
    size_t worst;        /* index of the element furthest outside (or closest to the limit) */
    float got, want;     /* that element */
    double err, allowed; /* |got - want| and atol + rtol * |want| for it */
} check_result;

check_result check_close(const float *got, const float *want, size_t n, double rtol, double atol);
int check_report(const char *name, check_result r); /* one line; returns 0 when r.bad == 0 */

// @internal
_Noreturn void todo(const char *lesson, const char *what);
// @end

#endif
