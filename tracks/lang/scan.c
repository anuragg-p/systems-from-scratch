// scan.c: the scanner, the compiler's first phase. It reads the text a
// character at a time and groups the characters into tokens: names,
// numbers, keywords and operators, each with the line and column it starts
// at. Spaces, tabs, line ends and comments only keep tokens apart, and
// none of them is kept. The list ends with an end-of-file token. From here
// on nothing needs a statement to be on a line of its own.

#include <ctype.h>
#include <limits.h>
#include <stdarg.h>
#include "mote.h"

static const char *file;       // the file's name, for messages

static const char *keywords[] = {"read", "write", "if", "then", "else", "end", "while", "do"};
// The operators, the two-character ones first: the longest match wins.
static const char *ops[] = {":=", "==", "!=", "<=", ">=", "<", ">", "+", "-", "*", "/", "(", ")"};

static _Noreturn void verror(int line, int col, const char *fmt, va_list ap) {
  fflush(stdout);
  fprintf(stderr, "%s:%d:%d: ", file, line, col);
  vfprintf(stderr, fmt, ap);
  fputc('\n', stderr);
  exit(1);
}

_Noreturn void error_tok(Token *tok, const char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  verror(tok->line, tok->col, fmt, ap);
}

bool equal(Token *tok, const char *text) {
  return (tok->kind == T_KEYWORD || tok->kind == T_OP) && tok->len == (int)strlen(text) &&
         !strncmp(tok->text, text, tok->len);
}

// A number: its digits, and its value, which must fit in 63 bits.
static void number(Token *t) {
  // @build 01.06 a number
  // Each digit is added to ten times the value so far, after checking
  // that the sum will still fit in a long.
  t->kind = T_NUMBER;
  unsigned long v = 0;
  for (; isdigit((unsigned char)t->text[t->len]); t->len++) {
    unsigned long d = (unsigned long)(t->text[t->len] - '0');
    if (v > (LONG_MAX - d) / 10)
      error_tok(t, "number too large");
    v = v * 10 + d;
  }
  t->value = (long)v;
  // @end
}

// A word: a name, or one of the keywords.
static void name(Token *t) {
  // @build 01.06 a name or a keyword
  // A letter or "_", then letters, digits and "_". The whole word is
  // taken before it is looked for among the keywords, so that "done" is a
  // name and not "do" followed by "ne".
  while (isalnum((unsigned char)t->text[t->len]) || t->text[t->len] == '_')
    t->len++;
  t->kind = T_NAME;
  for (int i = 0; i < 8; i++)
    if (t->len == (int)strlen(keywords[i]) && !strncmp(t->text, keywords[i], t->len))
      t->kind = T_KEYWORD;
  // @end
}

// An operator, or an error: no token starts with this character.
static void op(Token *t) {
  // @build 01.06 an operator
  for (int i = 0; i < 13; i++)
    if (!strncmp(t->text, ops[i], strlen(ops[i]))) {
      t->kind = T_OP;
      t->len = (int)strlen(ops[i]);
      return;
    }
  if (isprint((unsigned char)*t->text))
    error_tok(t, "unexpected character '%c'", *t->text);
  error_tok(t, "unexpected character (byte %d)", (unsigned char)*t->text);
  // @end
}

Token *scan(const char *path, const char *src) {
  // @build 01.06 the scanner: the text into tokens
  // line and col follow p. What is between tokens is passed over: spaces
  // and tabs, line ends, and comments, from "#" to the end of the line.
  // The first character of a token says what kind it is. The end of the
  // file is placed on the last line, after its last character: a line end
  // at the very end of the file ends that line and does not start another.
  file = path;
  Token head = {0}, *cur = &head;
  int line = 1, col = 1, last_col = 1;
  const char *p = src;
  for (;;) {
    if (*p == '\n') {
      last_col = col;
      line++, col = 1, p++;
    } else if (*p == ' ' || *p == '\t' || *p == '\r') {
      col++, p++;
    } else if (*p == '#') {
      while (*p && *p != '\n')
        col++, p++;
    } else {
      Token *t = calloc(1, sizeof *t);
      *t = (Token){.text = p, .line = line, .col = col};
      if (!*p) {
        t->kind = T_EOF;
        if (p > src && p[-1] == '\n')
          t->line = line - 1, t->col = last_col;
        cur->next = t;
        return head.next;
      }
      if (isdigit((unsigned char)*p))
        number(t);
      else if (isalpha((unsigned char)*p) || *p == '_')
        name(t);
      else
        op(t);
      p += t->len, col += t->len;
      cur = cur->next = t;
    }
  }
  // @end
}
