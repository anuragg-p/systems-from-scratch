// gcd.c: the greatest common divisor of two numbers, in C: the program
// the language of this track starts from. It reads and writes with getint
// and putint (rt.h), as the machine's programs do.

#include "rt.h"

int main(void) {
  long i = getint();
  long j = getint();
  while (i != j) {
    if (i > j)
      i = i - j;
    else
      j = j - i;
  }
  putint(i);
  return 0;
}
