// @from 01.01
// main.c: the compiler's driver. It reads the command line and the input
// file, hands the text to each phase in turn, and writes out what the last
// one makes: the assembly of a program.
// @else
// // main.c: the whole compiler, for now. It reads a file that holds one
// // number and writes the RISC-V assembly of a program whose main returns
// // that number.
// @end
//
// Derived from chibicc by Rui Ueyama (https://github.com/rui314/chibicc,
// MIT; the licence is in LICENSE). It reads a file and writes assembly, and
// stops there: no assembler and no linker are run from here.

// @from 01.01
#include "cc.h"
// @else
// #include <ctype.h>
// #include <stdarg.h>
// #include <stdio.h>
// #include <stdlib.h>
// #include <string.h>
// @end

static char *opt_o;         // -o: the file the assembly goes to; standard output without it
static char *input_path;    // the file to compile; "-" is standard input
static bool opt_tokens;     // --tokens: print the tokens, and stop @from 01.01
static bool opt_tree;       // --tree: print the tree, and stop @from 02.01

// @from 01.01
// @else
// // Print a message and stop, with exit status 1 and no assembly.
// static void error(char *fmt, ...) {
//   va_list ap;
//   va_start(ap, fmt);
//   vfprintf(stderr, fmt, ap);
//   fprintf(stderr, "\n");
//   va_end(ap);
//   exit(1);
// }
//
// @end
// @internal
// Stands in for code a workspace has cut out: names the lesson whose code
// is missing, and stops with exit status 3.
_Noreturn void todo(char *lesson, char *what) {
  fprintf(stderr, "cc: %s: %s not written yet\n", lesson, what);
  exit(3);
}

// @end
static void usage(int status) {
  fprintf(stderr, "usage: cc");
  fprintf(stderr, " [--tokens]");    // @from 01.01
  fprintf(stderr, " [--tree]");      // @from 02.01
  fprintf(stderr, " [-o file] file\n");
  fprintf(stderr, "The assembly goes to standard output, or to the file -o names.\n");
  fprintf(stderr, "The file - is standard input.\n");
  exit(status);
}

// The command line: the options, and one file to compile.
static void parse_args(int argc, char **argv) {
  // @build 00.01 the command line
  // Go through argv[1] to argv[argc - 1]. --help prints the usage and exits
  // with 0. -o takes the next argument as the name of the output, and it is
  // an error for there to be none. Any other argument that starts with '-',
  // except "-" alone, is an error: "unknown argument: ...". Anything else is
  // the file to compile, and there must be exactly one.
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--help"))
      usage(0);

    if (!strcmp(argv[i], "-o")) {
      if (++i == argc)
        usage(1);
      opt_o = argv[i];
      continue;
    }

    // @from 01.01
    if (!strcmp(argv[i], "--tokens")) {
      opt_tokens = true;
      continue;
    }

    // @end
    // @from 02.01
    if (!strcmp(argv[i], "--tree")) {
      opt_tree = true;
      continue;
    }

    // @end
    if (argv[i][0] == '-' && argv[i][1] != '\0')
      error("unknown argument: %s", argv[i]);

    if (input_path)
      error("one file at a time: %s and %s", input_path, argv[i]);
    input_path = argv[i];
  }

  if (!input_path)
    usage(1);
  // @end
}

// The whole file in memory: one string, which ends in a newline and a '\0'
// whatever the file ends in. "-" is standard input.
static char *read_file(char *path) {
  // @build 00.01 reading the file
  // Open path for reading ("-": use stdin), or stop with "cannot open
  // PATH". Read it with fread in chunks into one buffer, made bigger with
  // realloc whenever the next chunk might not fit, until fread reads
  // nothing. Close it (but not stdin). If it is empty or does not end in
  // '\n', add one; then add the '\0', and return the buffer.
  FILE *fp;
  if (strcmp(path, "-") == 0) {
    fp = stdin;
  } else {
    fp = fopen(path, "r");
    if (!fp)
      error("cannot open %s", path);
  }

  char *buf = NULL;
  int len = 0;
  int cap = 0;
  for (;;) {
    // Room for a chunk, and for the '\n' and the '\0' at the end.
    if (cap - len < 4096 + 2) {
      cap = cap * 2 + 4096 + 2;
      buf = realloc(buf, cap);
    }
    int n = fread(buf + len, 1, cap - len - 2, fp);
    if (n == 0)
      break;
    len += n;
  }
  if (fp != stdin)
    fclose(fp);

  if (len == 0 || buf[len - 1] != '\n')
    buf[len++] = '\n';
  buf[len] = '\0';
  return buf;
  // @end
}

// Where the assembly goes: standard output, or the file -o names.
static FILE *open_file(char *path) {
  if (!path || strcmp(path, "-") == 0)
    return stdout;

  FILE *out = fopen(path, "w");
  if (!out)
    error("cannot open output file %s", path);
  return out;
}

// --tokens: one line a token, with where it starts (line:column), its kind
// and its text, and after a number its value.
static void print_tokens(Token *tok, FILE *out) {
  // @build 01.01 printing the tokens
  // For every token, the end-of-file one too, print "LINE:COL KIND TEXT",
  // KIND being num, punct, ident, keyword, str or eof; then, for a number,
  // its value in decimal; then a newline. The end of the file has no text.
  for (;; tok = tok->next) {
    char *kind = "";
    switch (tok->kind) {
    case TK_IDENT: kind = "ident"; break;       // @from 01.03
    case TK_PUNCT: kind = "punct"; break;
    case TK_KEYWORD: kind = "keyword"; break;   // @from 01.03
    case TK_STR: kind = "str"; break;           // @from 01.04
    case TK_NUM: kind = "num"; break;
    case TK_EOF: kind = "eof"; break;
    }

    fprintf(out, "%d:%d %s", tok->line_no, tok->col, kind);
    if (tok->len > 0)
      fprintf(out, " %.*s", tok->len, tok->loc);
    if (tok->kind == TK_NUM)
      fprintf(out, " %ld", tok->val);
    // @from 01.04
    // A string: how many bytes it stands for once its escapes are decoded.
    if (tok->kind == TK_STR)
      fprintf(out, " %d", tok->str_len);
    // @end
    fprintf(out, "\n");

    if (tok->kind == TK_EOF)
      return;
  }
  // @end
}

// @from 01.01
// @from 02.03
// @else
// // The value of a number token; any other token is an error.
// static long get_number(Token *tok) {
//   if (tok->kind != TK_NUM)
//     error_tok(tok, "expected a number");
//   return tok->val;
// }
//
// @end
// @end
// --tree: the tree, one node a line, each child two spaces further in than
// its parent, the left one first. A node is its operator, or "num" and the
// number.
static void print_tree(Node *node, int depth, FILE *out) {
  // @build 02.01 printing the tree
  // Print depth * 2 spaces, the node's operator ("+", or "num" and its
  // value), and a newline. Then the left child and the right child, if the
  // node has them, each at depth + 1.
  char *op = "";
  switch (node->kind) {
  case ND_ADD: op = "+"; break;
  case ND_SUB: op = "-"; break;
  case ND_MUL: op = "*"; break;         // @from 02.02
  case ND_DIV: op = "/"; break;         // @from 02.02
  case ND_NEG: op = "-"; break;         // @from 02.05
  case ND_MOD: op = "%"; break;         // @from 02.04
  case ND_BITAND: op = "&"; break;      // @from 02.04
  case ND_BITOR: op = "|"; break;       // @from 02.04
  case ND_BITXOR: op = "^"; break;      // @from 02.04
  case ND_SHL: op = "<<"; break;        // @from 02.04
  case ND_SHR: op = ">>"; break;        // @from 02.04
  case ND_EQ: op = "=="; break;         // @from 02.05
  case ND_NE: op = "!="; break;         // @from 02.05
  case ND_LT: op = "<"; break;          // @from 02.05
  case ND_LE: op = "<="; break;         // @from 02.05
  case ND_NOT: op = "!"; break;         // @from 02.05
  case ND_BITNOT: op = "~"; break;      // @from 02.05
  case ND_NUM: op = "num"; break;
  }

  fprintf(out, "%*s%s", depth * 2, "", op);
  if (node->kind == ND_NUM)
    fprintf(out, " %ld", node->val);
  fprintf(out, "\n");

  if (node->lhs)
    print_tree(node->lhs, depth + 1, out);
  if (node->rhs)
    print_tree(node->rhs, depth + 1, out);
  // @end
}

int main(int argc, char **argv) {
  parse_args(argc, argv);
  char *src = read_file(input_path);
  FILE *out = open_file(opt_o);

  // @from 01.01
  Token *tok = tokenize(input_path, src);
  if (opt_tokens) {
    print_tokens(tok, out);
    return 0;
  }

  // @from 02.01
  Node *node = parse(tok);
  if (opt_tree) {
    print_tree(node, 0, out);
    return 0;
  }

  // @end
  // @from 02.03
  codegen(node, out);
  // @else
  // // A number, then any number of "+ number" and "- number". The total
  // // is kept in a0, where main returns it; each new number goes through t0.
  // fprintf(out, "  .globl main\n");
  // fprintf(out, "main:\n");
  // fprintf(out, "  li a0, %ld\n", get_number(tok));
  // tok = tok->next;
//
  // while (tok->kind != TK_EOF) {
  //   if (equal(tok, "+")) {
  //     fprintf(out, "  li t0, %ld\n", get_number(tok->next));
  //     fprintf(out, "  add a0, a0, t0\n");
  //     tok = tok->next->next;
  //     continue;
  //   }
//
  //   tok = skip(tok, "-");
  //   fprintf(out, "  li t0, %ld\n", get_number(tok));
  //   fprintf(out, "  sub a0, a0, t0\n");
  //   tok = tok->next;
  // }
//
  // fprintf(out, "  ret\n");
  // @end
  // @else
  // // The file must hold one number in decimal, with nothing but spaces and
  // // newlines around it.
  // char *p = src;
  // while (isspace(*p))
  //   p++;
  // if (!isdigit(*p))
  //   error("expected a number");
  // unsigned long val = strtoul(p, &p, 10);
  // while (isspace(*p))
  //   p++;
  // if (*p)
  //   error("expected the end of the file after the number");
//
  // fprintf(out, "  .globl main\n");
  // fprintf(out, "main:\n");
  // fprintf(out, "  li a0, %lu\n", val);
  // fprintf(out, "  ret\n");
  // @end
  return 0;
}
