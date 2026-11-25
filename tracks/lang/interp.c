// interp.c: the interpreter built on the front end. It runs the program
// by walking its syntax tree: a statement does what it says, and an
// expression's value is worked out from its operands' values. Nothing is
// read from the text any more and no name is looked up: a variable's node
// points at its entry in the symbol table, and its value is kept there.
// It checks the language's dynamic rule as it goes: a variable must have
// a value at the moment it is used.

#include <ctype.h>
#include <limits.h>
#include "mote.h"

// read: the next whole number of the input, as the machine's getint
// reads it. An error is reported at the read.
static long input(Token *at) {
  // @build 01.09 read: a number from the input
  int c;
  do
    c = getchar();
  while (isspace(c));
  bool minus = c == '-';
  if (c == '-' || c == '+')
    c = getchar();
  if (!isdigit(c))
    error_tok(at, c == EOF && !minus ? "read: no more input" : "read: not a number");
  unsigned long v = 0;
  for (; isdigit(c); c = getchar())
    v = v * 10 + (unsigned long)(c - '0');
  ungetc(c, stdin);
  return (long)(minus ? 0 - v : v);
  // @end
}

static long eval(Node *e) {
  // @build 01.09 an expression's value
  // Operands left to right. The arithmetic is done on unsigned longs,
  // which wrap around; a long that overflowed would be undefined in C.
  // Division rounds toward zero; by zero it is an error, and the most
  // negative number divided by -1 is itself.
  if (e->kind == N_NUM)
    return e->value;
  if (e->kind == N_VAR) {
    if (!e->sym->has_value)
      error_tok(e->tok, "%.*s has no value yet", e->sym->len, e->sym->name);
    return e->sym->value;
  }
  unsigned long a = (unsigned long)eval(e->lhs);
  if (e->kind == N_NEG)
    return (long)(0 - a);
  unsigned long b = (unsigned long)eval(e->rhs);
  switch (e->kind) {
  case N_ADD: return (long)(a + b);
  case N_SUB: return (long)(a - b);
  case N_MUL: return (long)(a * b);
  default:
    if (b == 0)
      error_tok(e->tok, "division by zero");
    if ((long)a == LONG_MIN && (long)b == -1)
      return LONG_MIN;
    return (long)a / (long)b;
  }
  // @end
}

static bool test(Node *c) {
  // @build 01.09 a condition's truth
  long a = eval(c->lhs), b = eval(c->rhs);
  switch (c->kind) {
  case N_EQ: return a == b;
  case N_NE: return a != b;
  case N_LT: return a < b;
  case N_GT: return a > b;
  case N_LE: return a <= b;
  default:   return a >= b;
  }
  // @end
}

// Runs a list of statements, in order.
void interpret(Node *s) {
  // @build 01.09 the statements run
  // A variable gets its value in its symbol table entry. A while tests
  // its condition again before every pass, an if once.
  for (; s; s = s->next) {
    switch (s->kind) {
    case N_ASSIGN:
    case N_READ:
      s->sym->value = s->kind == N_READ ? input(s->tok) : eval(s->lhs);
      s->sym->has_value = true;
      break;
    case N_WRITE:
      printf("%ld\n", eval(s->lhs));
      break;
    case N_IF:
      interpret(test(s->cond) ? s->body : s->els);
      break;
    default:
      while (test(s->cond))
        interpret(s->body);
    }
  }
  // @end
}
