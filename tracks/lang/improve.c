// improve.c: the code improver, run between analysis and code generation
// when mote is given -O. It makes the one improvement of chapter 1: the
// variables used most are kept in registers, s1 to s11, instead of in
// memory, so that using one costs no load and giving it a value no store.
// It counts how often each variable appears in the syntax tree, as a
// target or an operand, and hands out the registers in that order. The
// code generator does the rest (gen.c, the paths for sym->reg).

#include "mote.h"

// Every appearance of every variable in the tree under n, counted in its
// symbol table entry.
static void count(Node *n) {
  // @build 01.11 each variable's uses, counted
  for (; n; n = n->next) {
    if (n->sym)
      n->sym->uses++;
    count(n->lhs);
    count(n->rhs);
    count(n->cond);
    count(n->body);
    count(n->els);
  }
  // @end
}

void improve(Node *prog) {
  // @build 01.11 the registers, to the most used
  // s1 to the variable used most, s2 to the next, and so on: a tie goes
  // to the lower index (the entries are looked at in order, and only a
  // count larger than the best so far wins). s0 is left alone: by
  // RISC-V's convention it is the frame pointer. Variables past the
  // eleventh stay in memory.
  static const char *s[] = {"s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11"};
  count(prog);
  for (int r = 0; r < 11; r++) {
    Symbol *best = NULL;
    for (Symbol *v = symbols(); v; v = v->next)
      if (!v->reg && (!best || v->uses > best->uses))
        best = v;
    if (!best)
      return;
    best->reg = s[r];
  }
  // @end
}
