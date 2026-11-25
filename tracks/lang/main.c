// main.c: the compiler's driver, and the picture of its phases. It reads
// the file and hands it to each phase in turn: scan, parse, analyze, and
// then interpret, or with -S generate (improve first, with -O). Each
// printing option stops after the phase whose result it prints. The
// printers are here, so that each phase's own file holds only the phase.
//
//   ./mote [--tokens | --parse-tree | --tree | --symbols | -S [-O]] FILE

#include "mote.h"

// What mote is asked to do, after which phase it stops.
enum {
  RUN, TOKENS,
  PARSE_TREE,                     // @from 01.07
  TREE, SYMBOLS,                  // @from 01.08
  ASM,                            // @from 01.10
  NMODES
};
static const char *option[] = {
  [TOKENS] = "--tokens",
  [PARSE_TREE] = "--parse-tree",  // @from 01.07
  [TREE] = "--tree", [SYMBOLS] = "--symbols",  // @from 01.08
  [ASM] = "-S",                   // @from 01.10
};
static int mode = RUN;
static bool improved;             // -O @from 01.11
static const char *kinds[] = {"name", "number", "keyword", "op", "eof"};

// @internal
// Stands in for code a workspace has cut out: names the lesson whose code
// is missing, and stops with exit status 3.
_Noreturn void todo(const char *lesson, const char *what) {
  fprintf(stderr, "lang: %s: %s not written yet\n", lesson, what);
  exit(3);
}

// @end
static _Noreturn void usage(void) {
  // @from 01.09
  fprintf(stderr, "usage: mote [--tokens");
  // @else
  // fprintf(stderr, "usage: mote (--tokens");
  // @end
  fprintf(stderr, " | --parse-tree");               // @from 01.07
  fprintf(stderr, " | --tree | --symbols");         // @from 01.08
  fprintf(stderr, " | -S");                         // @from 01.10
  fprintf(stderr, " [-O]");                         // @from 01.11
  // @from 01.09
  fprintf(stderr, "] FILE\n");
  // @else
  // fprintf(stderr, ") FILE\n");
  // @end
  exit(2);
}

// The command line: at most one option, and the file.
static const char *options(int argc, char **argv) {
  // @build 01.06 the command line
  const char *file = NULL;
  for (int i = 1; i < argc; i++) {
    int m = 1;
    while (m < NMODES && strcmp(argv[i], option[m]))
      m++;
    if (m < NMODES && mode == RUN)
      mode = m;
    else if (!strcmp(argv[i], "-O"))      // @from 01.11
      improved = true;                    // @from 01.11
    else if (argv[i][0] == '-' || file)
      usage();
    else
      file = argv[i];
  }
  if (!file)
    usage();
  if (improved && mode != ASM)            // -O goes with -S @from 01.11
    usage();                              // @from 01.11
  // @from 01.09
  // @else
  // if (mode == RUN)                     // no option: there is no interpreter yet
  //   usage();
  // @end
  return file;
  // @end
}

static char *read_file(const char *name) {
  FILE *f = fopen(name, "rb");
  if (!f) {
    fprintf(stderr, "mote: cannot open %s\n", name);
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

// --tokens: a token a line, LINE:COL KIND TEXT, the end of the file last.
static void print_tokens(Token *t) {
  // @build 01.06 printing the tokens
  for (; t; t = t->next)
    printf("%d:%d %s%s%.*s\n", t->line, t->col, kinds[t->kind], t->len ? " " : "", t->len, t->text);
  // @end
}

// @from 01.07
// --parse-tree: a node a line, two spaces deeper for each level; a rule
// by its name, a token as KIND TEXT.
static void print_parse(Parse *n, int depth) {
  // @build 01.07 printing the parse tree
  for (; n; n = n->next) {
    if (n->rule)
      printf("%*s%s\n", 2 * depth, "", n->rule);
    else
      printf("%*s%s %.*s\n", 2 * depth, "", kinds[n->tok->kind], n->tok->len, n->tok->text);
    print_parse(n->kids, depth + 1);
  }
  // @end
}

// @end
// @from 01.08
static void print_var(Symbol *s) {
  printf("%.*s#%d", s->len, s->name, s->index);
}

// An expression in prefix form: (- i#1 j#2); a variable with its index.
static void print_expr(Node *e) {
  // @build 01.08 printing an expression, in prefix form
  static const char *op[] = {[N_NEG] = "-", [N_ADD] = "+", [N_SUB] = "-", [N_MUL] = "*",
                             [N_DIV] = "/", [N_EQ] = "==", [N_NE] = "!=", [N_LT] = "<",
                             [N_GT] = ">", [N_LE] = "<=", [N_GE] = ">="};
  if (e->kind == N_NUM) {
    printf("%ld", e->value);
  } else if (e->kind == N_VAR) {
    print_var(e->sym);
  } else {
    printf("(%s ", op[e->kind]);
    print_expr(e->lhs);
    if (e->rhs) {
      printf(" ");
      print_expr(e->rhs);
    }
    printf(")");
  }
  // @end
}

// --tree: a statement a line, indented by how deep it is nested, its
// expressions on its line.
static void print_tree(Node *s, int depth) {
  // @build 01.08 printing the syntax tree
  for (; s; s = s->next) {
    printf("%*s", 2 * depth, "");
    if (s->kind == N_READ || s->kind == N_ASSIGN) {
      printf(s->kind == N_READ ? "read " : ":= ");
      print_var(s->sym);
    } else {
      printf(s->kind == N_WRITE ? "write" : s->kind == N_IF ? "if" : "while");
    }
    if (s->lhs || s->cond) {
      printf(" ");
      print_expr(s->lhs ? s->lhs : s->cond);
    }
    printf("\n");
    print_tree(s->body, depth + 1);
    if (s->els) {
      printf("%*selse\n", 2 * depth, "");
      print_tree(s->els, depth + 1);
    }
  }
  // @end
}

// --symbols: INDEX NAME LINE:COL, the place the text first gives it a value.
static void print_symbols(void) {
  // @build 01.08 printing the symbol table
  for (Symbol *s = symbols(); s; s = s->next)
    printf("%d %.*s %d:%d\n", s->index, s->len, s->name, s->line, s->col);
  // @end
}

// @end
int main(int argc, char **argv) {
  const char *file = options(argc, argv);
  // @build 01.06 the phases, in order
  // Each phase takes what the one before it made.
  Token *tok = scan(file, read_file(file));
  if (mode == TOKENS) {
    print_tokens(tok);
    return 0;
  }
  // @from 01.07
  Parse *tree = parse(tok);
  if (mode == PARSE_TREE) {
    print_parse(tree, 0);
    return 0;
  }
  // @end
  // @from 01.08
  Node *prog = analyze(tree);
  if (mode == TREE) {
    print_tree(prog, 0);
    return 0;
  }
  if (mode == SYMBOLS) {
    print_symbols();
    return 0;
  }
  // @end
  // @from 01.10
  if (mode == ASM) {
    // @from 01.11
    if (improved)
      improve(prog);
    // @end
    generate(prog);
    return 0;
  }
  // @end
  interpret(prog);                        // @from 01.09
  // @end
  return 0;
}
