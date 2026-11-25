// machine.c: the machine the compiler aims at, written as a program. It
// reads a file of RISC-V assembly text, runs it from the label main, and
// ends with the status the program gives. The program reads this
// program's standard input and writes to its standard output.
//
//   ./machine [--count] [--trace] FILE.s
//
// The text is read twice: once for the labels, so that a branch can name
// a label further down, and once for the instructions, which go into an
// array. Then a loop runs them, one at a time. Memory is allocated with
// calloc and never freed: the machine runs one program and exits.

#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(long) == 8, "a register is a long, so a long must be 64 bits");

// The instructions, and what each takes after its name: r a register, n a
// number, l a label, m an address written as n(r).
enum {
  LI, MV, NEG, ADD, SUB, MUL, DIV, BEQ, BNE, BLT, BGE, BGT, BLE, BEQZ, BNEZ, J, CALL, RET,
  ADDI, LD, SD,  // @from 01.10
  NOPS
};
static const struct { const char *name, *takes; } ops[] = {
  [LI] = {"li", "rn"}, [MV] = {"mv", "rr"}, [NEG] = {"neg", "rr"},
  [ADD] = {"add", "rrr"}, [SUB] = {"sub", "rrr"}, [MUL] = {"mul", "rrr"}, [DIV] = {"div", "rrr"},
  [BEQ] = {"beq", "rrl"}, [BNE] = {"bne", "rrl"}, [BLT] = {"blt", "rrl"}, [BGE] = {"bge", "rrl"},
  [BGT] = {"bgt", "rrl"}, [BLE] = {"ble", "rrl"}, [BEQZ] = {"beqz", "rl"}, [BNEZ] = {"bnez", "rl"},
  [J] = {"j", "l"}, [CALL] = {"call", "l"}, [RET] = {"ret", ""},
  [ADDI] = {"addi", "rrn"}, [LD] = {"ld", "rm"}, [SD] = {"sd", "rm"},  // @from 01.10
};

// The 32 registers by their RISC-V names, x0 to x31 in order.
static const char *regs[32] = {
  "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
  "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6",
};
enum { ZERO, RA, SP, A0 = 10 };

// Routines that are part of the machine: a call to one of these names
// does its work and comes straight back.
enum { GETINT = 1, PUTINT, EXIT, DIVZERO };
static const char *routines[] = {
  [GETINT] = "getint", [PUTINT] = "putint", [EXIT] = "exit",
  [DIVZERO] = "divzero",  // @from 01.10
};
#define NROUTINES (int)(sizeof routines / sizeof *routines)

// An instruction: what it does, its registers in the order written, its
// number, the address it jumps to, and the line and text it came from.
typedef struct {
  int op, r[3], routine, line;
  long n, target;
  char *text;
} Insn;

typedef struct { char *name; int len; long address; } Label;

static const char *path;
static Insn *prog, *running;   // the program, and the instruction running
static int ninsns, nlabels;
static Label *labels;
static long x[32], before[32]; // the registers, and what they held before this instruction
static long count;             // how many instructions have run, for --count
static bool counting, tracing;
static int line;               // the line being read, or of the instruction running

#define MEMORY (1L << 20)                  // @from 01.10
static unsigned char memory[MEMORY];      // @from 01.10

// @internal
// Stands in for code a workspace has cut out: names the lesson whose code
// is missing, and stops with exit status 3.
_Noreturn void todo(const char *lesson, const char *what) {
  fprintf(stderr, "lang: %s: %s not written yet\n", lesson, what);
  exit(3);
}

// @end
static void trace(void);

static _Noreturn void error(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  fflush(stdout);
  fprintf(stderr, "machine: %s:%d: ", path, line);
  vfprintf(stderr, fmt, ap);
  fputc('\n', stderr);
  exit(1);
}

// The program ends: its last instruction traced, what it printed sent out,
// then the count if asked for.
static _Noreturn void stop(long status) {
  if (tracing)
    trace();
  fflush(stdout);
  if (counting)
    fprintf(stderr, "%ld instructions\n", count);
  exit((int)(status & 0xff));
}

static char *skip(char *p) {
  while (*p == ' ' || *p == '\t')
    p++;
  return p;
}

// How long the word at p is: a name, a label or a number.
static int word(const char *p) {
  int n = 0;
  while (isalnum((unsigned char)p[n]) || p[n] == '_' || p[n] == '.')
    n++;
  return n;
}

static bool is(const char *p, int len, const char *name) {
  return len == (int)strlen(name) && !strncmp(p, name, len);
}

static Label *find(const char *p, int len) {
  for (int i = 0; i < nlabels; i++)
    if (labels[i].len == len && !strncmp(labels[i].name, p, len))
      return &labels[i];
  return NULL;
}

static char *expect(char *p, char c) {
  p = skip(p);
  if (*p != c)
    error("expected '%c'", c);
  return skip(p + 1);
}

// A register by its name; *p moves past it.
static int reg(char **p) {
  // @build 01.01 a register by its name
  // Take a word and look for it among the 32 names: where it is found is
  // the register's number.
  int len = word(*p);
  for (int i = 0; i < 32; i++)
    if (is(*p, len, regs[i])) {
      *p += len;
      return i;
    }
  if (!len)
    error("expected a register");
  error("unknown register '%.*s'", len, *p);
  // @end
}

// The first pass: the file split into lines, the labels recorded, and the
// text of each instruction kept for the second pass.
static char **find_labels(char *src) {
  // @build 01.01 the first pass: the labels
  // A line is a label ("name:"), an instruction, or both; "#" starts a
  // comment. Count the lines to size the arrays. Then for each line: end
  // it where its comment starts; record its label (a second label of the
  // same name is an error) with the address the next instruction will
  // have, 4 bytes after the one before; and keep what is left, if
  // anything, as the text of an instruction, with its line number.
  int nlines = 1;
  for (char *p = src; *p; p++)
    nlines += *p == '\n';
  labels = calloc(nlines, sizeof *labels);
  prog = calloc(nlines, sizeof *prog);
  char **texts = calloc(nlines, sizeof *texts);
  char *p = src;
  for (line = 1; *p; line++) {
    char *next = strchr(p, '\n');
    next = next ? (*next = '\0', next + 1) : p + strlen(p);
    char *hash = strchr(p, '#');
    if (hash)
      *hash = '\0';
    p = skip(p);
    int len = word(p);
    if (len && p[len] == ':') {
      if (find(p, len))
        error("label '%.*s' defined twice", len, p);
      labels[nlabels++] = (Label){p, len, 4L * ninsns};
      p = skip(p + len + 1);
    }
    for (char *e = p + strlen(p); e > p && isspace((unsigned char)e[-1]); )
      *--e = '\0';
    if (*p) {
      prog[ninsns].line = line;
      texts[ninsns++] = p;
    }
    p = next;
  }
  return texts;
  // @end
}

// The second pass: each instruction's text read into an Insn.
static void read_instructions(char **texts) {
  // @build 01.01 the second pass: each instruction
  // The text's first word is the instruction's name, which must be in
  // ops[]. Then come its operands, as ops[].takes says, a comma between
  // two: registers into r[] in the order written, a number (or the n of
  // n(r)) into n, a label's address into target, except that a call may
  // name one of the machine's routines instead. Nothing may follow.
  for (int i = 0; i < ninsns; i++) {
    Insn *in = &prog[i];
    char *p = in->text = texts[i], *end;
    line = in->line;
    int len = word(p), nr = 0;
    while (in->op < NOPS && !(ops[in->op].name && is(p, len, ops[in->op].name)))
      in->op++;
    if (in->op == NOPS)
      error("unknown instruction '%.*s'", len, p);
    p = skip(p + len);
    for (const char *t = ops[in->op].takes; *t; t++, p = skip(p)) {
      if (t != ops[in->op].takes)
        p = expect(p, ',');
      if (*t == 'r')
        in->r[nr++] = reg(&p);
      if (*t == 'n' || *t == 'm') {
        errno = 0;
        in->n = strtol(p, &end, 10);
        if (end == p)
          error("expected a number");
        if (errno == ERANGE)
          error("number too large: %.*s", (int)(end - p), p);
        p = end;
      }
      if (*t == 'm') {
        p = expect(p, '(');
        in->r[nr++] = reg(&p);
        p = expect(p, ')');
      }
      if (*t == 'l') {
        int n = word(p);
        Label *l = find(p, n);
        for (int r = 1; in->op == CALL && r < NROUTINES; r++)
          if (is(p, n, routines[r]))
            in->routine = r;
        if (!n)
          error("expected a label");
        if (!l && !in->routine)
          error("no label '%.*s'", n, p);
        in->target = l ? l->address : 0;
        p += n;
      }
    }
    if (*p)
      error("unexpected text after the instruction: '%s'", p);
  }
  // @end
}

// An address must have all 8 of its bytes, a to a + 7, in the memory.
static void check(long a) {
  // @build 01.10 memory: an address checked
  if (a < 0 || a > MEMORY - 8)
    error("address %ld is outside the memory", a);
  // @end
}

// The 8 bytes at address a, as one value. RISC-V is little-endian: the
// lowest byte of a value is at the lowest address.
static long load(long a) {
  // @build 01.10 memory: 8 bytes read
  check(a);
  unsigned long v = 0;
  for (int i = 7; i >= 0; i--)
    v = v << 8 | memory[a + i];
  return (long)v;
  // @end
}

static void store(long a, long v) {
  // @build 01.10 memory: 8 bytes written
  check(a);
  for (int i = 0; i < 8; i++)
    memory[a + i] = (unsigned char)((unsigned long)v >> (8 * i));
  // @end
}

// getint: the next whole number of the input, with an optional sign.
static long getint(void) {
  // @build 01.01 getint: a number from the input
  // Skip white space. At the end of the input the program stops with
  // "machine: getint: no more input", status 1; at anything that is not a
  // number, with "not a number". The digits are added up in an unsigned
  // long, so a number too large for 64 bits wraps around instead of being
  // undefined, as everything the machine computes does.
  int c;
  do
    c = getchar();
  while (isspace(c));
  bool minus = c == '-';
  if (c == '-' || c == '+')
    c = getchar();
  if (!isdigit(c)) {
    fflush(stdout);
    fprintf(stderr, "machine: getint: %s\n", c == EOF && !minus ? "no more input" : "not a number");
    stop(1);
  }
  unsigned long v = 0;
  for (; isdigit(c); c = getchar())
    v = v * 10 + (unsigned long)(c - '0');
  ungetc(c, stdin);
  return (long)(minus ? 0 - v : v);
  // @end
}

// The machine's own routines. They change a0 and nothing else.
static void routine(int r) {
  // @build 01.01 the routines of the machine
  // getint puts the next number of the input in a0; putint prints a0 and
  // a line end; exit ends the program with status a0.
  if (r == GETINT)
    x[A0] = getint();
  if (r == PUTINT)
    printf("%ld\n", x[A0]);
  if (r == EXIT)
    stop(x[A0]);
  // @from 01.10
  // divzero is what compiled code calls instead of dividing by zero; a0
  // holds the line of the program the division is on.
  if (r == DIVZERO) {
    fflush(stdout);
    fprintf(stderr, "line %ld: division by zero\n", x[A0]);
    stop(1);
  }
  // @end
  // @end
}

// --trace: the instruction that ran, its line, and what it changed.
static void trace(void) {
  // @build 01.01 --trace: each instruction and what it changed
  // The line number, the instruction's text, then each register whose
  // value is not what it was before, as "name = value"; when there are
  // changes the text is padded to 24 columns, so that they line up.
  char buf[1024] = "";
  int len = 0;
  for (int i = 0; i < 32; i++)
    if (x[i] != before[i])
      len += snprintf(buf + len, sizeof buf - len, "  %s = %ld", regs[i], x[i]);
  // @from 01.10
  if (running->op == SD)
    snprintf(buf + len, sizeof buf - len, "  mem[%ld] = %ld",
             (long)((unsigned long)before[running->r[1]] + (unsigned long)running->n), before[running->r[0]]);
  // @end
  fflush(stdout);
  fprintf(stderr, buf[0] ? "%4d  %-24s%s\n" : "%4d  %s%s\n", running->line, running->text, buf);
  // @end
}

static void set(int r, long v) {
  if (r != ZERO)                 // what is written to zero is dropped
    x[r] = v;
}

// Runs the program from main until it stops.
static _Noreturn void run(void) {
  // @build 01.01 the run loop
  // pc is the address of the next instruction; instruction i is at 4 * i.
  // ra starts as the address just past the last instruction, so a ret
  // from a main that has called nothing ends the program, with status a0.
  // Each time round: the instruction at pc (running off the end, or going
  // where there is none, is an error), its registers' values, then what it
  // does. Sums are done on unsigned longs, which wrap around, so none is
  // undefined; div by zero gives -1, and the most negative number divided
  // by -1 gives itself, as RISC-V's div does.
  Label *m = find("main", 4);
  if (!m) {
    fprintf(stderr, "machine: %s: no label main to start at\n", path);
    exit(1);
  }
  long end = 4L * ninsns, pc = m->address;
  x[RA] = end;
  x[SP] = MEMORY;                      // @from 01.10
  for (;;) {
    if (pc == end)
      error("ran off the end of the program");
    if (pc < 0 || pc > end || pc % 4)
      error("no instruction at address %ld", pc);
    Insn *in = running = &prog[pc / 4];
    line = in->line;
    count++;
    memcpy(before, x, sizeof x);
    unsigned long b = (unsigned long)x[in->r[1]], c = (unsigned long)x[in->r[2]];
    long sa = x[in->r[0]], sb = (long)b, sc = (long)c, next = pc + 4;
    int d = in->r[0];
    switch (in->op) {
    case LI:   set(d, in->n); break;
    case MV:   set(d, sb); break;
    case NEG:  set(d, (long)(0 - b)); break;
    case ADD:  set(d, (long)(b + c)); break;
    case SUB:  set(d, (long)(b - c)); break;
    case MUL:  set(d, (long)(b * c)); break;
    case DIV:  set(d, sc == 0 ? -1 : sb == LONG_MIN && sc == -1 ? LONG_MIN : sb / sc); break;
    case BEQ:  if (sa == sb) next = in->target; break;
    case BNE:  if (sa != sb) next = in->target; break;
    case BLT:  if (sa < sb) next = in->target; break;
    case BGE:  if (sa >= sb) next = in->target; break;
    case BGT:  if (sa > sb) next = in->target; break;
    case BLE:  if (sa <= sb) next = in->target; break;
    case BEQZ: if (sa == 0) next = in->target; break;
    case BNEZ: if (sa != 0) next = in->target; break;
    case J:    next = in->target; break;
    case CALL:
      set(RA, next);
      if (in->routine)
        routine(in->routine);
      else
        next = in->target;
      break;
    case RET:
      if (x[RA] == end)
        stop(x[A0]);
      next = x[RA];
      break;
    // @from 01.10
    case ADDI: set(d, (long)(b + (unsigned long)in->n)); break;
    case LD:   set(d, load((long)(b + (unsigned long)in->n))); break;
    case SD:   store((long)(b + (unsigned long)in->n), sa); break;
    // @end
    }
    if (tracing)
      trace();
    pc = next;
  }
  // @end
}

static char *read_file(const char *name) {
  FILE *f = fopen(name, "rb");
  if (!f) {
    fprintf(stderr, "machine: cannot open %s\n", name);
    exit(1);
  }
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  rewind(f);
  char *buf = calloc(n + 1, 1);
  buf[fread(buf, 1, n, f)] = '\0';
  fclose(f);
  return buf;
}

int main(int argc, char **argv) {
  bool bad = false;
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--count"))
      counting = true;
    else if (!strcmp(argv[i], "--trace"))
      tracing = true;
    else if (argv[i][0] == '-' || path)
      bad = true;
    else
      path = argv[i];
  }
  if (bad || !path) {
    fprintf(stderr, "usage: machine [--count] [--trace] FILE.s\n");
    return 2;
  }
  read_instructions(find_labels(read_file(path)));
  run();
}
