// mote2c.c: the translator. It turns a program of the language into a C
// program that does the same, a line of C for each line of the program.
//
//   ./mote2c FILE.mote > FILE.c
//
// Two passes over the lines. The first collects every name a read or a
// ":=" gives a value, so that the C can declare them all at the top. The
// second writes the C. Expressions and conditions are copied as they are,
// since the language's operators are C's, and they are not checked: a
// mistake in one goes through, and the C compiler is the one to find it.
// Like mote0 it wants one statement a line.

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *file;
static char **lines;
static int nlines, line;               // line: the one being read, from 1
static const char **names;             // the names, in the order they first appear
static int *lens, nnames;

// @internal
// Stands in for code a workspace has cut out: names the lesson whose code
// is missing, and stops with exit status 3.
_Noreturn void todo(const char *lesson, const char *what) {
  fprintf(stderr, "lang: %s: %s not written yet\n", lesson, what);
  exit(3);
}

// @end
static _Noreturn void error(const char *msg) {
  fflush(stdout);
  fprintf(stderr, "%s:%d: %s\n", file, line, msg);
  exit(1);
}

static int word(const char *s) {
  int n = 0;
  if (isalpha((unsigned char)*s) || *s == '_')
    while (isalnum((unsigned char)s[n]) || s[n] == '_')
      n++;
  return n;
}

static int is(const char *s, int len, const char *kw) {
  return len == (int)strlen(kw) && !strncmp(s, kw, len);
}

static const char *skip(const char *s) {
  while (*s == ' ' || *s == '\t')
    s++;
  return s;
}

// A line's statement: where it starts (after the indentation), and its
// length, without a comment or the space after it.
static int code(const char *s, const char **start) {
  *start = s = skip(s);
  int n = 0;
  while (s[n] && s[n] != '#')
    n++;
  while (n > 0 && isspace((unsigned char)s[n - 1]))
    n--;
  return n;
}

static int keyword(const char *s, int n) {
  return is(s, n, "read") || is(s, n, "write") || is(s, n, "if") || is(s, n, "then") ||
         is(s, n, "else") || is(s, n, "end") || is(s, n, "while") || is(s, n, "do");
}

// The first pass: the names the program gives values to.
static void find_names(void) {
  // @build 01.04 the first pass: the names given values
  // A name is given a value by "read name" or "name := ...". Each is kept
  // once, in the order it first appears.
  names = calloc(nlines + 1, sizeof *names);
  lens = calloc(nlines + 1, sizeof *lens);
  for (line = 1; line <= nlines; line++) {
    const char *s;
    code(lines[line - 1], &s);
    int n = word(s);
    if (is(s, n, "read"))
      n = word(s = skip(s + n));
    else if (n && (keyword(s, n) || strncmp(skip(s + n), ":=", 2)))
      n = 0;
    int k = 0;
    while (k < nnames && !(lens[k] == n && !strncmp(names[k], s, n)))
      k++;
    if (n && k == nnames) {
      names[nnames] = s;
      lens[nnames++] = n;
    }
  }
  // @end
}

// "while c do" or "if c then" (kw and last): c is the text between the
// first word and the last, which must be `last` and a word of its own.
static void condition(const char *s, int n, const char *kw, const char *last) {
  const char *c = skip(s + strlen(kw));
  int end = n - (int)strlen(last);     // where `last` should start
  if (end < c - s || strncmp(s + end, last, strlen(last)) || isalnum((unsigned char)s[end - 1]) ||
      s[end - 1] == '_') {
    char msg[32];
    snprintf(msg, sizeof msg, "expected '%s'", last);
    error(msg);
  }
  int len = end - (int)(c - s);
  while (len > 0 && isspace((unsigned char)c[len - 1]))
    len--;
  printf("%s (%.*s) {\n", kw, len, c);
}

// The second pass: a line of C for each line of the program.
static void translate(const char *s, int n) {
  // @build 01.04 a line of C for each line
  // By the line's first word: "read x" is "x = getint();", "write e" is
  // "putint(e);", "x := e" is "x = e;", while and if open a C block and
  // end closes one; else closes one and opens the next.
  int w = word(s);
  const char *rest = skip(s + w);
  int r = n - (int)(rest - s);
  if (is(s, w, "read")) {
    int m = word(rest);
    if (!m)
      error("expected a name");
    if (m != r)
      error("expected the end of the line");
    printf("%.*s = getint();\n", m, rest);
  } else if (is(s, w, "write")) {
    printf("putint(%.*s);\n", r, rest);
  } else if (is(s, w, "while")) {
    condition(s, n, "while", "do");
  } else if (is(s, w, "if")) {
    condition(s, n, "if", "then");
  } else if (is(s, w, "else") || is(s, w, "end")) {
    if (r)
      error("expected the end of the line");
    puts(is(s, w, "else") ? "} else {" : "}");
  } else if (w && !keyword(s, w) && !strncmp(rest, ":=", 2)) {
    const char *e = skip(rest + 2);
    printf("%.*s = %.*s;\n", w, s, n - (int)(e - s), e);
  } else {
    error(w && !keyword(s, w) ? "expected ':='" : "expected a statement");
  }
  // @end
}

static char *read_file(const char *name) {
  FILE *f = fopen(name, "rb");
  if (!f) {
    fprintf(stderr, "mote2c: cannot open %s\n", name);
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
  if (argc != 2 || argv[1][0] == '-') {
    fprintf(stderr, "usage: mote2c FILE.mote\n");
    return 2;
  }
  file = argv[1];
  char *src = read_file(file);
  lines = calloc(strlen(src) + 1, sizeof *lines);
  for (char *s = src; *s; ) {
    lines[nlines++] = s;
    if (!(s = strchr(s, '\n')))
      break;
    *s++ = '\0';
  }
  find_names();

  // @build 01.04 the C program
  // A C main that declares every name as a long set to 0, then the lines,
  // each indented as it was, one level inside main. A line that is only a
  // comment is dropped; a blank line stays.
  printf("#include \"rt.h\"\n\nint main(void) {\n");
  for (int k = 0; k < nnames; k++)
    printf("    long %.*s = 0;\n", lens[k], names[k]);
  for (line = 1; line <= nlines; line++) {
    const char *s, *l = lines[line - 1];
    int n = code(l, &s);
    if (!n && *s == '#')
      continue;
    printf("    %.*s", (int)(s - l), l);
    if (n)
      translate(s, n);
    else
      printf("\n");
  }
  printf("    return 0;\n}\n");
  // @end
  return 0;
}
