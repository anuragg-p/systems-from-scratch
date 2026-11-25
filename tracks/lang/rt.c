// rt.c: getint and putint for programs written in C, with the machine's
// behaviour: getint skips white space and reads an optional sign and
// digits; at the end of the input it stops the program with "getint: no
// more input" and status 1.

#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include "rt.h"

// @internal
// Stands in for code a workspace has cut out: names the lesson whose code
// is missing, and stops with exit status 3.
_Noreturn void todo(const char *lesson, const char *what) {
  fprintf(stderr, "lang: %s: %s not written yet\n", lesson, what);
  exit(3);
}

// @end
long getint(void) {
  // @build 01.02 getint: a number from the input
  // As the machine's getint: skip white space; a sign, then digits. At the
  // end of the input, "getint: no more input" and status 1; at anything
  // else that is not a number, "getint: not a number". The digits are
  // added up in an unsigned long, which wraps around where a long would
  // overflow.
  int c;
  do
    c = getchar();
  while (isspace(c));
  bool minus = c == '-';
  if (c == '-' || c == '+')
    c = getchar();
  if (!isdigit(c)) {
    fflush(stdout);
    fprintf(stderr, "getint: %s\n", c == EOF && !minus ? "no more input" : "not a number");
    exit(1);
  }
  unsigned long v = 0;
  for (; isdigit(c); c = getchar())
    v = v * 10 + (unsigned long)(c - '0');
  ungetc(c, stdin);
  return (long)(minus ? 0 - v : v);
  // @end
}

void putint(long n) {
  // @build 01.02 putint: a number written
  printf("%ld\n", n);
  // @end
}
