/*
 * add.h - out = a + b, element by element, written twice.
 *
 * add_ref is the plain version, simple enough to trust by reading it.
 * add is the version under test: the same arithmetic written another way,
 * which can be wrong in ways add_ref cannot. Every later kernel comes in a
 * pair like this one.
 */
#ifndef ADD_H
#define ADD_H

#include <stddef.h>

void add_ref(const float *a, const float *b, float *out, size_t n);
void add(const float *a, const float *b, float *out, size_t n);

// @internal
_Noreturn void todo(const char *lesson, const char *what);
// @end

#endif
