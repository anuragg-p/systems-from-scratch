// gen.c: the code generator, the last phase. It walks the syntax tree and
// writes, on standard output, assembly for the machine of machine.c:
// RISC-V text as the GNU assembler takes it.
//
// Each variable has a slot of 8 bytes in memory, on the stack: a use of a
// variable is a load (ld) and an assignment a store (sd). The values of
// an expression are kept in t0 to t6, used as a stack: a node's value
// goes in the register of its depth, its left operand in the same one
// and its right operand one higher. A condition is one branch, taken
// when it is false. From 01.11 the improver may give a variable a
// register instead of a slot, and then its register is the operand.

#include <stdarg.h>
#include "mote.h"

static const char *T[] = {"t0", "t1", "t2", "t3", "t4", "t5", "t6"};
static int labels;            // the labels made so far: .L1, .L2, ...

static void into(Node *e, const char *dest, int depth);
static void stmts(Node *s);

// One instruction: its name, then its operands. On a load or a store the
// variable's name follows as a comment.
static void emit(Symbol *var, const char *op, const char *fmt, ...) {
  char text[96];
  int n = snprintf(text, sizeof text, "    %-4s ", op);
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(text + n, sizeof text - n, fmt, ap);
  va_end(ap);
  if (var)
    printf("%-26s# %.*s\n", text, var->len, var->name);
  else
    printf("%s\n", text);
}

// The register that holds e's value once the code written here has run.
static const char *operand(Node *e, int depth) {
  // @build 01.10 an operand: the register its value is in
  // Its value is computed into the register of its depth, t0 to t6; past
  // t6 there is none left (chapter 1 does not spill to memory).
  if (e->kind == N_VAR && e->sym->reg)    // a variable kept in a register: that one @from 01.11
    return e->sym->reg;                   // @from 01.11
  if (depth >= 7)
    error_tok(e->tok, "expression too deep");
  into(e, T[depth], depth);
  return T[depth];
  // @end
}

// Before a division by the value in register r: a check, so that a
// program that divides by zero stops with the line of the division.
static void check_divisor(const char *r, Token *op) {
  // @build 01.10 a check before each division
  int ok = ++labels;
  emit(NULL, "bnez", "%s, .L%d", r, ok);
  emit(NULL, "li", "a0, %d", op->line);
  emit(NULL, "call", "divzero");
  printf(".L%d:\n", ok);
  // @end
}

// e computed into the register dest; its parts use the registers from
// T[depth] up.
static void into(Node *e, const char *dest, int depth) {
  // @build 01.10 an expression into a register
  // A number is a li, a variable a load. An operator has its operands
  // computed first, the left one into its own depth and the right one
  // into the next, then one instruction combines them.
  static const char *op[] = {[N_ADD] = "add", [N_SUB] = "sub", [N_MUL] = "mul", [N_DIV] = "div"};
  if (e->kind == N_NUM) {
    emit(NULL, "li", "%s, %ld", dest, e->value);
  } else if (e->kind == N_VAR) {
    // @from 01.11
    if (e->sym->reg)
      emit(NULL, "mv", "%s, %s", dest, e->sym->reg);
    else
      emit(e->sym, "ld", "%s, %d(sp)", dest, e->sym->offset);
    // @else
    // emit(e->sym, "ld", "%s, %d(sp)", dest, e->sym->offset);
    // @end
  } else if (e->kind == N_NEG) {
    const char *a = operand(e->lhs, depth);
    emit(NULL, "neg", "%s, %s", dest, a);
  } else {
    const char *a = operand(e->lhs, depth), *b = operand(e->rhs, depth + 1);
    if (e->kind == N_DIV)
      check_divisor(b, e->tok);
    emit(NULL, op[e->kind], "%s, %s, %s", dest, a, b);
  }
  // @end
}

// The value in register r given to the variable v.
static void store(Symbol *v, const char *r) {
  // @from 01.11
  if (v->reg)
    emit(NULL, "mv", "%s, %s", v->reg, r);
  else
    emit(v, "sd", "%s, %d(sp)", r, v->offset);
  // @else
  // emit(v, "sd", "%s, %d(sp)", r, v->offset);
  // @end
}

// A branch to .L<label>, taken when the condition c is false: on the
// opposite comparison.
static void branch_unless(Node *c, int label) {
  // @build 01.10 a condition: one branch, on the opposite comparison
  static const char *opposite[] = {[N_EQ] = "bne", [N_NE] = "beq", [N_LT] = "bge",
                                   [N_GE] = "blt", [N_GT] = "ble", [N_LE] = "bgt"};
  const char *a = operand(c->lhs, 0), *b = operand(c->rhs, 1);
  emit(NULL, opposite[c->kind], "%s, %s, .L%d", a, b, label);
  // @end
}

static void stmt(Node *s) {
  // @build 01.10 a statement
  // read calls getint and stores a0; write moves the value to a0 and calls
  // putint. A while is a label, the branch out to its end label, the body
  // and a jump back. An if branches to its else part (or its end).
  if (s->kind == N_READ) {
    emit(NULL, "call", "getint");
    store(s->sym, "a0");
  } else if (s->kind == N_ASSIGN) {
    // @from 01.11
    // A variable in a register gets the value computed straight into it.
    if (s->sym->reg)
      into(s->lhs, s->sym->reg, 0);
    else
      store(s->sym, operand(s->lhs, 0));
    // @else
    // store(s->sym, operand(s->lhs, 0));
    // @end
  } else if (s->kind == N_WRITE) {
    const char *r = operand(s->lhs, 0);
    emit(NULL, "mv", "a0, %s", r);
    emit(NULL, "call", "putint");
  } else if (s->kind == N_IF) {
    int els = ++labels, end = s->els ? ++labels : els;
    branch_unless(s->cond, els);
    stmts(s->body);
    if (s->els) {
      emit(NULL, "j", ".L%d", end);
      printf(".L%d:\n", els);
      stmts(s->els);
    }
    printf(".L%d:\n", end);
  } else {
    int top = ++labels, end = ++labels;
    printf(".L%d:\n", top);
    branch_unless(s->cond, end);
    stmts(s->body);
    emit(NULL, "j", ".L%d", top);
    printf(".L%d:\n", end);
  }
  // @end
}

static void stmts(Node *s) {
  for (; s; s = s->next)
    stmt(s);
}

void generate(Node *prog) {
  // @build 01.10 the program: the frame, the statements, the exit
  // The variables in memory get slots 8 bytes apart, in the order of the
  // symbol table, and the stack pointer moves down by their size rounded
  // up to 16 (the stack stays aligned to 16 bytes, as RISC-V's calling
  // convention wants). The program ends with a call to exit.
  int n = 0;
  for (Symbol *s = symbols(); s; s = s->next) {
    if (s->reg)                           // a variable in a register has no slot @from 01.11
      continue;                           // @from 01.11
    s->offset = 8 * n++;
  }
  printf("main:\n");
  if (n)
    emit(NULL, "addi", "sp, sp, -%d", (8 * n + 15) / 16 * 16);
  stmts(prog);
  emit(NULL, "li", "a0, 0");
  emit(NULL, "call", "exit");
  // @end
}
