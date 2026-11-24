// codegen.c: the code generator. It walks the tree and writes RISC-V
// assembly for it: RV64 with multiply and divide (rv64im), every value 64
// bits wide, and the assembler's usual pseudo-instructions (li, mv, ret and
// the like, each one or two real instructions).
//
// The values of an expression live in the temporary registers t0 to t5,
// used as a stack: gen_expr(node, d) leaves the node's value in reg[d], and
// may use the registers above it but never those below, which hold values
// still waiting for their operator. A binary operator puts its left operand
// at d and its right one at d + 1, then combines them into reg[d].
//
// This file is not chibicc's: chibicc writes x86-64, pushing every value on
// the machine's stack and popping it back. It keeps chibicc's names
// (codegen, gen_expr, println).

#include "cc.h"

// The registers that hold the values of an expression, as a stack: reg[0]
// is the bottom.
// t6 is not one of them: it is kept spare, for spill(). @from 02.06
static char *reg[] = {"t0", "t1", "t2", "t3", "t4", "t5"};
#define NREG ((int)(sizeof(reg) / sizeof(*reg)))

static FILE *output_file;

static void gen_expr(Node *node, int d);
static void spill(Node *node, int d);   // @from 02.06

// One line of assembly: printf's format and arguments, then a newline. An
// instruction starts with two spaces; a label starts the line.
static void println(char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  vfprintf(output_file, fmt, ap);
  va_end(ap);
  fprintf(output_file, "\n");
}

// The instruction (or two) for a binary operator: rd = rs1 op rs2.
static void gen_binary(Node *node, char *rd, char *rs1, char *rs2) {
  // @build 02.03 gen_binary
  // One instruction for each operator: ND_ADD add, ND_SUB sub, ND_MUL mul,
  // ND_DIV div (signed, rounding toward zero, as C does). Any other kind:
  // "invalid expression", at the node's token.
  switch (node->kind) {
  case ND_ADD:
    println("  add %s, %s, %s", rd, rs1, rs2);
    return;
  case ND_SUB:
    println("  sub %s, %s, %s", rd, rs1, rs2);
    return;
  case ND_MUL:
    println("  mul %s, %s, %s", rd, rs1, rs2);
    return;
  case ND_DIV:
    println("  div %s, %s, %s", rd, rs1, rs2);
    return;
  // @from 02.04
  case ND_MOD:
    println("  rem %s, %s, %s", rd, rs1, rs2);
    return;
  case ND_BITAND:
    println("  and %s, %s, %s", rd, rs1, rs2);
    return;
  case ND_BITOR:
    println("  or %s, %s, %s", rd, rs1, rs2);
    return;
  case ND_BITXOR:
    println("  xor %s, %s, %s", rd, rs1, rs2);
    return;
  case ND_SHL:
    println("  sll %s, %s, %s", rd, rs1, rs2);
    return;
  case ND_SHR:
    println("  sra %s, %s, %s", rd, rs1, rs2);
    return;
  // @end
  // @from 02.05
  case ND_EQ:
    // Equal when nothing is left after xor.
    println("  xor %s, %s, %s", rd, rs1, rs2);
    println("  seqz %s, %s", rd, rd);
    return;
  case ND_NE:
    println("  xor %s, %s, %s", rd, rs1, rs2);
    println("  snez %s, %s", rd, rd);
    return;
  case ND_LT:
    println("  slt %s, %s, %s", rd, rs1, rs2);
    return;
  case ND_LE:
    // a <= b is not (b < a).
    println("  slt %s, %s, %s", rd, rs2, rs1);
    println("  xori %s, %s, 1", rd, rd);
    return;
  // @end
  default:
    break;
  }
  error_tok(node->tok, "invalid expression");
  // @end
}

// Code that leaves the value of node in reg[d]. It may use reg[d] and the
// registers above it; the ones below hold values still needed.
static void gen_expr(Node *node, int d) {
  // @build 02.03 gen_expr
  // A number: li reg[d] with its value. A binary operator: its left operand
  // at d, its right one at d + 1, then gen_binary into reg[d]. If d + 1 is
  // past the last register, call spill(node, d) instead of the right
  // operand and the instruction.
  switch (node->kind) {
  case ND_NUM:
    println("  li %s, %ld", reg[d], node->val);
    return;
  // @from 02.05
  case ND_NEG:
    gen_expr(node->lhs, d);
    println("  neg %s, %s", reg[d], reg[d]);
    return;
  case ND_NOT:
    gen_expr(node->lhs, d);
    println("  seqz %s, %s", reg[d], reg[d]);
    return;
  case ND_BITNOT:
    gen_expr(node->lhs, d);
    println("  not %s, %s", reg[d], reg[d]);
    return;
  // @end
  default:
    break;
  }

  gen_expr(node->lhs, d);
  if (d + 1 == NREG) {
    // @from 02.06
    spill(node, d);
    return;
    // @else
    // error_tok(node->tok, "out of registers: the expression is too deep");
    // @end
  }
  gen_expr(node->rhs, d + 1);
  gen_binary(node, reg[d], reg[d], reg[d + 1]);
  // @end
}

// The rest of a binary operator whose left operand is in the last register,
// reg[d], so that none is left for its right one. The left operand goes to
// the stack, which gives reg[d] back for the right one; then it comes back
// into t6 for the one instruction that needs it. The stack pointer moves by
// 16 bytes, not 8, because the calling convention keeps it a multiple of 16.
static void spill(Node *node, int d) {
  // @build 02.06 spill
  // Make room on the stack (addi sp, sp, -16) and store reg[d] there (sd).
  // Compute the right operand into reg[d]: gen_expr at the same d, which
  // may spill again, deeper. Load the left operand back into t6 (ld) and
  // give the room back (addi sp, sp, 16). Then gen_binary into reg[d], with
  // t6 on the left and reg[d] on the right.
  println("  addi sp, sp, -16");
  println("  sd %s, 0(sp)", reg[d]);
  gen_expr(node->rhs, d);
  println("  ld t6, 0(sp)");
  println("  addi sp, sp, 16");
  gen_binary(node, reg[d], "t6", reg[d]);
  // @end
}

// The assembly of a program whose main returns the value of node.
void codegen(Node *node, FILE *out) {
  // @build 02.03 codegen
  // Write to out: main made global, its label, the expression at depth 0,
  // its value moved into a0 (where a function returns its value), and ret.
  output_file = out;
  println("  .globl main");
  println("main:");
  gen_expr(node, 0);
  println("  mv a0, %s", reg[0]);
  println("  ret");
  // @end
}
