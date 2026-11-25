// mote0.c: the first interpreter. It runs a program straight from its
// text, a line at a time, with nothing worked out in advance: no tokens,
// no tree. An expression is worked out from its characters each time its
// line runs, a name is looked up in a table by comparing strings each
// time it is used, and the lines of a loop are read again on every pass.
//
// @from 01.05
//   ./mote0 [--count] [FILE]        with no FILE, a prompt
// @else
// //   ./mote0 [--count] FILE
// @end
//
// So that it can tell where a statement ends without a scanner, it wants
// one statement a line, with "while c do", "if c then", "else" and "end"
// each on a line of its own. Memory is allocated and never freed: the
// program runs and exits.

#include <ctype.h>
#include <limits.h>
#include <setjmp.h>                       // @from 01.05
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(long) == 8, "a value is a long, so a long must be 64 bits");

static char **lines;           // the program; lines[k] is line k + 1
static int nlines;
static int at;                 // the line running, as an index into lines
static const char *p;          // where that line is being read
static const char *file;       // the program's file; NULL at the prompt
static long nread;             // the lines looked at, for --count
static jmp_buf again;          // where an error at the prompt goes back to @from 01.05

// The table of names: a list, searched by comparing characters.
typedef struct Name Name;
struct Name { const char *s; int len; long value; Name *next; };
static Name *names;

static const char *keywords[] = {"read", "write", "if", "then", "else", "end", "while", "do"};

// @internal
// Stands in for code a workspace has cut out: names the lesson whose code
// is missing, and stops with exit status 3.
_Noreturn void todo(const char *lesson, const char *what) {
  fprintf(stderr, "lang: %s: %s not written yet\n", lesson, what);
  exit(3);
}

// @end
static long expr(void);

static _Noreturn void error(const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  fflush(stdout);
  // @from 01.05
  if (!file)
    fprintf(stderr, "line %d: ", at + 1);
  else
    fprintf(stderr, "%s:%d: ", file, at + 1);
  // @else
  // fprintf(stderr, "%s:%d: ", file, at + 1);
  // @end
  vfprintf(stderr, fmt, ap);
  fputc('\n', stderr);
  if (!file)                    // @from 01.05
    longjmp(again, 1);          // @from 01.05
  exit(1);
}

static void space(void) {
  while (*p == ' ' || *p == '\t' || *p == '\r')
    p++;
}

// The word at p, a name or a keyword: its length (0 when there is none),
// with *w where it starts. p moves past it.
static int word(const char **w) {
  space();
  *w = p;
  if (isalpha((unsigned char)*p) || *p == '_')
    while (isalnum((unsigned char)*p) || *p == '_')
      p++;
  return (int)(p - *w);
}

static bool is(const char *w, int len, const char *kw) {
  return len == (int)strlen(kw) && !strncmp(w, kw, len);
}

static bool keyword(const char *w, int len) {
  for (int i = 0; i < 8; i++)
    if (is(w, len, keywords[i]))
      return true;
  return false;
}

static Name *find(const char *s, int len) {
  // @build 01.03 a name looked up in the table
  // Compare the name with each entry, character by character: this is
  // what every use of a name costs.
  for (Name *n = names; n; n = n->next)
    if (n->len == len && !strncmp(n->s, s, len))
      return n;
  return NULL;
  // @end
}

static void set(const char *s, int len, long v) {
  // @build 01.03 a name given a value
  // A name the table does not have yet is added to it.
  Name *n = find(s, len);
  if (!n) {
    n = calloc(1, sizeof *n);
    *n = (Name){s, len, 0, names};
    names = n;
  }
  n->value = v;
  // @end
}

static void end_of_line(void) {
  space();
  if (*p && *p != '#')
    error("expected the end of the line");
}

// A number, a name's value, an expression in parentheses, or a minus and
// a factor.
static long factor(void) {
  // @build 01.03 a factor, from its characters
  // A number's digits are added up as they are read; it must fit in 63
  // bits. Negation is done on an unsigned long, which wraps around.
  space();
  if (isdigit((unsigned char)*p)) {
    unsigned long v = 0;
    for (; isdigit((unsigned char)*p); p++) {
      unsigned long d = (unsigned long)(*p - '0');
      if (v > (LONG_MAX - d) / 10)
        error("number too large");
      v = v * 10 + d;
    }
    return (long)v;
  }
  if (*p == '(') {
    p++;
    long v = expr();
    space();
    if (*p != ')')
      error("expected ')'");
    p++;
    return v;
  }
  if (*p == '-') {
    p++;
    return (long)(0 - (unsigned long)factor());
  }
  const char *w;
  int len = word(&w);
  if (!len || keyword(w, len))
    error("expected a number, a name or '('");
  Name *n = find(w, len);
  if (!n)
    error("%.*s has no value yet", len, w);
  return n->value;
  // @end
}

// Factors multiplied and divided, left to right.
static long term(void) {
  // @build 01.03 a term: factors multiplied and divided
  // Division rounds toward zero, as C's does; by zero it is an error, and
  // the most negative number divided by -1 is itself, wrapped around.
  long v = factor();
  for (space(); *p == '*' || *p == '/'; space()) {
    char op = *p++;
    long d = factor();
    if (op == '*')
      v = (long)((unsigned long)v * (unsigned long)d);
    else if (d == 0)
      error("division by zero");
    else
      v = v == LONG_MIN && d == -1 ? LONG_MIN : v / d;
  }
  return v;
  // @end
}

// Terms added and subtracted, left to right.
static long expr(void) {
  // @build 01.03 an expression: terms added and subtracted
  long v = term();
  for (space(); *p == '+' || *p == '-'; space()) {
    char op = *p++;
    unsigned long t = (unsigned long)term();
    v = (long)(op == '+' ? (unsigned long)v + t : (unsigned long)v - t);
  }
  return v;
  // @end
}

// Two expressions compared.
static bool cond(void) {
  // @build 01.03 a condition: two expressions compared
  // The two-character comparisons are looked for first, so that "<=" is
  // not taken for "<" followed by "=".
  static const char *cmp[] = {"==", "!=", "<=", ">=", "<", ">"};
  long a = expr();
  space();
  int k = 0;
  while (k < 6 && strncmp(p, cmp[k], strlen(cmp[k])))
    k++;
  if (k == 6)
    error("expected a comparison");
  p += strlen(cmp[k]);
  long b = expr();
  return k == 0 ? a == b : k == 1 ? a != b : k == 2 ? a <= b : k == 3 ? a >= b : k == 4 ? a < b : a > b;
  // @end
}

// read: the next whole number of the input.
static long input(void) {
  // @build 01.03 read: a number from the input
  // As the machine's getint: white space skipped, a sign, digits that
  // wrap around; at the end of the input or at anything else, an error.
  int c;
  do
    c = getchar();
  while (isspace(c));
  bool minus = c == '-';
  if (c == '-' || c == '+')
    c = getchar();
  if (!isdigit(c))
    error(c == EOF && !minus ? "read: no more input" : "read: not a number");
  unsigned long v = 0;
  for (; isdigit(c); c = getchar())
    v = v * 10 + (unsigned long)(c - '0');
  ungetc(c, stdin);
  // @from 01.05
  // At the prompt a number is typed on a line of its own: the rest of that
  // line is not the next line of the program.
  if (!file)
    while ((c = getchar()) != '\n' && c != EOF)
      continue;
  // @end
  return (long)(minus ? 0 - v : v);
  // @end
}

// A statement that is not a block: read, write or an assignment, by its
// first word, w.
static void statement(const char *w, int len) {
  // @build 01.03 one statement, by its first word
  // Each checks that nothing is left on the line before it does anything.
  // In "x := e" the expression is worked out before x is given its value.
  if (is(w, len, "read")) {
    const char *name;
    int n = word(&name);
    if (!n || keyword(name, n))
      error("expected a name");
    end_of_line();
    set(name, n, input());
  } else if (is(w, len, "write")) {
    long v = expr();
    end_of_line();
    printf("%ld\n", v);
  } else if (len && !keyword(w, len)) {
    space();
    if (strncmp(p, ":=", 2))
      error("expected ':='");
    p += 2;
    long v = expr();
    end_of_line();
    set(w, len, v);
  } else {
    error("expected a statement");
  }
  // @end
}

// From the line after `from`, reads forward to the end that closes it,
// or, with to_else, to an else of its own if that comes first. The index
// of that line.
static int skip(int from, bool to_else) {
  // @build 01.03 reading forward to the matching end
  // Only each line's first word is looked at: a while or an if opens a
  // block inside, which its own end closes. Every line looked at counts.
  int depth = 0;
  for (at = from + 1; at < nlines; at++) {
    nread++;
    p = lines[at];
    const char *w;
    int len = word(&w);
    if (is(w, len, "while") || is(w, len, "if"))
      depth++;
    if ((is(w, len, "end") || (to_else && is(w, len, "else"))) && depth == 0)
      return at;
    if (is(w, len, "end"))
      depth--;
  }
  at = nlines - 1;
  error("expected 'end'");
  // @end
}

// Runs the lines from `first` to the last.
static void run(int first) {
  // @build 01.03 the run, a line at a time
  // open[] holds the blocks that are open: for a while, the line it is on,
  // to go back to at its end; for an if, -1. A false condition reads
  // forward with skip(). An end of a while goes back to the while's line,
  // whose condition is worked out again from its text. An else reached
  // after the then part has run reads forward to its end.
  int *open = calloc(nlines - first + 1, sizeof *open), depth = 0;
  for (at = first; at < nlines; ) {
    nread++;
    p = lines[at];
    const char *w;
    int len = word(&w);
    space();
    if (!len && (!*p || *p == '#')) {
      at++;
    } else if (is(w, len, "while") || is(w, len, "if")) {
      bool loop = *w == 'w', yes = cond();
      const char *k;
      int klen = word(&k);
      if (!is(k, klen, loop ? "do" : "then"))
        error(loop ? "expected 'do'" : "expected 'then'");
      end_of_line();
      if (yes) {
        open[depth++] = loop ? at : -1;
        at++;
        continue;
      }
      int to = skip(at, !loop);
      p = lines[to];
      klen = word(&k);
      if (is(k, klen, "else")) {
        end_of_line();
        open[depth++] = -1;
      }
      at = to + 1;
    } else if (is(w, len, "else")) {
      end_of_line();
      if (!depth || open[depth - 1] >= 0)
        error("expected a statement");
      depth--;
      at = skip(at, false) + 1;
    } else if (is(w, len, "end")) {
      end_of_line();
      if (!depth)
        error("expected a statement");
      int back = open[--depth];
      at = back >= 0 ? back : at + 1;
    } else {
      statement(w, len);
      at++;
    }
  }
  if (depth) {
    at = nlines - 1;
    error("expected 'end'");
  }
  // @end
}

// @from 01.05
// A line of standard input without its line end; NULL at the end.
static char *read_line(void) {
  int cap = 64, len = 0, c;
  char *s = malloc(cap);
  while ((c = getchar()) != EOF && c != '\n') {
    if (len + 1 == cap)
      s = realloc(s, cap *= 2);
    s[len++] = (char)c;
  }
  s[len] = '\0';
  return c == EOF && len == 0 ? NULL : s;
}

// @end
// The prompt: lines typed one at a time, each run when it is whole.
static void prompt(void) {
  // @build 01.05 the prompt
  // "> " asks for a line. A while or an if opens a block: until its end,
  // the lines are held and ". " asks for the next. Then the lines are run,
  // as the end of a file's lines. An error goes back to the prompt with
  // longjmp, and the names keep their values. The end of the input ends
  // the session.
  int depth = 0, first = nlines;
  for (;;) {
    fputs(depth > 0 ? ". " : "> ", stdout);
    fflush(stdout);
    char *line = read_line();
    if (!line) {
      putchar('\n');
      return;
    }
    lines = realloc(lines, (nlines + 1) * sizeof *lines);
    lines[nlines++] = line;
    p = line;
    const char *w;
    int len = word(&w);
    depth += is(w, len, "while") || is(w, len, "if") ? 1 : is(w, len, "end") ? -1 : 0;
    if (depth > 0)
      continue;
    if (!setjmp(again))
      run(first);
    first = nlines;
    depth = 0;
  }
  // @end
}

// The file split into lines, each ending where its line end was.
static void split(char *src) {
  // @build 01.03 the lines of the file
  int n = 1;
  for (char *s = src; *s; s++)
    n += *s == '\n';
  lines = calloc(n, sizeof *lines);
  for (char *s = src; *s; ) {
    lines[nlines++] = s;
    s = strchr(s, '\n');
    if (!s)
      break;
    *s++ = '\0';
  }
  // @end
}

static char *read_file(const char *name) {
  FILE *f = fopen(name, "rb");
  if (!f) {
    fprintf(stderr, "mote0: cannot open %s\n", name);
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
  bool count = false, bad = false;
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--count"))
      count = true;
    else if (argv[i][0] == '-' || file)
      bad = true;
    else
      file = argv[i];
  }
  // @from 01.05
  if (!bad && !file) {
    prompt();
    return 0;
  }
  // @end
  if (bad || !file) {
    // @from 01.05
    fprintf(stderr, "usage: mote0 [--count] [FILE]\n");
    // @else
    // fprintf(stderr, "usage: mote0 [--count] FILE\n");
    // @end
    return 2;
  }
  split(read_file(file));
  run(0);
  if (count) {
    fflush(stdout);
    fprintf(stderr, "%ld lines read\n", nread);
  }
  return 0;
}
