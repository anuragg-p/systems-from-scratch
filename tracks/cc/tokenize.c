// tokenize.c: the scanner. It turns the characters of the source into a
// list of tokens, each of which knows where in the source it came from. The
// error functions are here too, since an error is reported at a place in
// the source.
//
// Derived from chibicc's tokenize.c by Rui Ueyama
// (https://github.com/rui314/chibicc, MIT; the licence is in LICENSE).

#include "cc.h"

// The file being compiled: its name, for error messages, and its text.
static char *current_filename;
static char *current_input;

// Print a message and stop, with exit status 1. For an error that has no
// place in the source.
void error(char *fmt, ...) {
  // @build 01.01 error
  // Print fmt and its arguments to stderr as vfprintf does, then a
  // newline, and exit with status 1.
  va_list ap;
  va_start(ap, fmt);
  vfprintf(stderr, fmt, ap);
  fprintf(stderr, "\n");
  va_end(ap);
  exit(1);
  // @end
}

// An error at loc, a place on line line_no, in two lines: the file, the line
// number and the text of the line, then a caret under the place, and the
// message after it:
//
//   foo.c:10: x = y + 1;
//                 ^ expected ';'
//
// Every tab before the place is copied into the caret's line, so the caret
// lines up under the place however wide the terminal makes a tab.
static void verror_at(int line_no, char *loc, char *fmt, va_list ap) {
  // @build 01.05 pointing at the source
  // Find where the line holding loc starts (just after a '\n', or the start
  // of current_input) and where it ends (its '\n'). Print
  // "FILE:LINE: " and the line. Under it print as many spaces as that
  // prefix took (fprintf returns how many characters it wrote), then a tab
  // for each tab of the line before loc and a space for every other
  // character, then "^ ", the message, and a newline.
  char *line = loc;
  while (current_input < line && line[-1] != '\n')
    line--;

  char *end = loc;
  while (*end && *end != '\n')
    end++;

  int indent = fprintf(stderr, "%s:%d: ", current_filename, line_no);
  fprintf(stderr, "%.*s\n", (int)(end - line), line);

  fprintf(stderr, "%*s", indent, "");
  for (char *p = line; p < loc; p++)
    fputc(*p == '\t' ? '\t' : ' ', stderr);
  fprintf(stderr, "^ ");
  vfprintf(stderr, fmt, ap);
  fprintf(stderr, "\n");
  // @end
}

// An error at loc, a place in the source.
void error_at(char *loc, char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  // @from 01.05
  int line_no = 1;
  for (char *p = current_input; p < loc; p++)
    if (*p == '\n')
      line_no++;
  verror_at(line_no, loc, fmt, ap);
  // @else
  // (void)loc;     // the place is not shown yet: this says so to the compiler
  // vfprintf(stderr, fmt, ap);
  // fprintf(stderr, "\n");
  // @end
  va_end(ap);
  exit(1);
}

// An error at a token.
void error_tok(Token *tok, char *fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  // @from 01.05
  verror_at(tok->line_no, tok->loc, fmt, ap);
  // @else
  // (void)tok;     // the place is not shown yet: this says so to the compiler
  // vfprintf(stderr, fmt, ap);
  // fprintf(stderr, "\n");
  // @end
  va_end(ap);
  exit(1);
}

// Is tok the punctuator or keyword op? Its text must be op, all of it.
// (chibicc compares with memcmp, which may read tok->len bytes of op even
// when op is shorter; strncmp stops at op's '\0'.)
bool equal(Token *tok, char *op) {
  // @build 01.01 equal
  // True when the token's text, tok->len characters at tok->loc, is the
  // same as op and op has no more characters after them.
  return strncmp(tok->loc, op, tok->len) == 0 && op[tok->len] == '\0';
  // @end
}

// tok must be op: return the token after it, or stop with an error at it.
Token *skip(Token *tok, char *op) {
  // @build 01.01 skip
  // If tok is not op, an error at tok: "expected 'OP'". Else the next token.
  if (!equal(tok, op))
    error_tok(tok, "expected '%s'", op);
  return tok->next;
  // @end
}

// A new token of kind, for the characters from start up to end.
static Token *new_token(TokenKind kind, char *start, char *end) {
  // @build 01.01 new_token
  // calloc one, so every field starts at zero; set kind, loc and len.
  Token *tok = calloc(1, sizeof(Token));
  tok->kind = kind;
  tok->loc = start;
  tok->len = end - start;
  return tok;
  // @end
}

// Does p start with q?
static bool startswith(char *p, char *q) {
  // @build 01.02 startswith
  // Compare the first strlen(q) characters of p with q.
  return strncmp(p, q, strlen(q)) == 0;
  // @end
}

// Can c start an identifier: a letter or '_'?
static bool is_ident1(char c) {
  // @build 01.03 is_ident1
  // 'a' to 'z', 'A' to 'Z', or '_'.
  return ('a' <= c && c <= 'z') || ('A' <= c && c <= 'Z') || c == '_';
  // @end
}

// Can c be in an identifier after its first character: a letter, '_' or a
// digit?
static bool is_ident2(char c) {
  // @build 01.03 is_ident2
  // What is_ident1 takes, and '0' to '9'.
  return is_ident1(c) || ('0' <= c && c <= '9');
  // @end
}

// The value of a hexadecimal digit.
static int from_hex(char c) {
  // @build 01.04 from_hex
  // '0' to '9' are 0 to 9; 'a' to 'f' and 'A' to 'F' are 10 to 15.
  if ('0' <= c && c <= '9')
    return c - '0';
  if ('a' <= c && c <= 'f')
    return c - 'a' + 10;
  return c - 'A' + 10;
  // @end
}

// How long the punctuator at p is (3, 2 or 1), or 0 if p does not start
// one. The longest that fits wins: ">>=" is one token, not ">>" and "=".
static int read_punct(char *p) {
  // @build 01.02 read_punct
  // Try every punctuator of three characters, then every one of two, in a
  // table, and return the length of the first that p starts with. Else, if
  // *p is one of the single characters C uses, 1; else 0.
  static char *kw[] = {
    "<<=", ">>=", "==", "!=", "<=", ">=", "->", "+=",
    "-=", "*=", "/=", "++", "--", "%=", "&=", "|=", "^=", "&&",
    "||", "<<", ">>",
  };

  for (int i = 0; i < (int)(sizeof(kw) / sizeof(*kw)); i++)
    if (startswith(p, kw[i]))
      return strlen(kw[i]);

  return *p && strchr("+-*/%&|^~!=<>()[]{}.,;:?#", *p) ? 1 : 0;
  // @end
}

// Is tok a keyword? It is still an identifier, as the scanner found it.
static bool is_keyword(Token *tok) {
  // @build 01.03 is_keyword
  // Compare it with every keyword of the language, in a table.
  static char *kw[] = {
    "return", "if", "else", "for", "while", "int", "sizeof", "char",
    "struct", "union", "short", "long", "void", "typedef", "_Bool",
    "enum", "static", "goto", "break", "continue", "switch", "case",
    "default", "extern", "do", "signed", "unsigned", "const", "volatile",
    "auto", "register", "restrict", "__restrict", "__restrict__",
    "_Noreturn", "inline", "__attribute__",
  };

  for (int i = 0; i < (int)(sizeof(kw) / sizeof(*kw)); i++)
    if (equal(tok, kw[i]))
      return true;
  return false;
  // @end
}

// The character an escape sequence stands for. p is just past the
// backslash; *new_pos is set to just past the sequence. The compiler that
// compiles this file decides what '\n' is here: the values come from it,
// not from this code (chibicc's comment on this cites Ken Thompson's
// "Reflections on Trusting Trust").
static int read_escaped_char(char **new_pos, char *p) {
  // @build 01.04 read_escaped_char
  // One to three octal digits: their value. 'x' and one or more hex
  // digits: their value; 'x' with none is "invalid hex escape sequence". A
  // value over 255 is "escape sequence out of range". a b t n v f r: the
  // control characters C names so; \ ' " ?: themselves. Anything else is
  // "unknown escape sequence", at the backslash.
  char *start = p - 1;

  if ('0' <= *p && *p <= '7') {
    // An octal number: one to three digits.
    int c = *p++ - '0';
    if ('0' <= *p && *p <= '7') {
      c = (c << 3) + (*p++ - '0');
      if ('0' <= *p && *p <= '7')
        c = (c << 3) + (*p++ - '0');
    }
    if (c > 255)
      error_at(start, "escape sequence out of range");
    *new_pos = p;
    return c;
  }

  if (*p == 'x') {
    // A hexadecimal number: as many digits as there are.
    p++;
    if (!isxdigit(*p))
      error_at(p, "invalid hex escape sequence");

    int c = 0;
    for (; isxdigit(*p); p++) {
      c = (c << 4) + from_hex(*p);
      if (c > 255)
        error_at(start, "escape sequence out of range");
    }
    *new_pos = p;
    return c;
  }

  *new_pos = p + 1;

  switch (*p) {
  case 'a': return '\a';
  case 'b': return '\b';
  case 't': return '\t';
  case 'n': return '\n';
  case 'v': return '\v';
  case 'f': return '\f';
  case 'r': return '\r';
  case '\\': case '\'': case '"': case '?': return *p;
  }
  error_at(start, "unknown escape sequence");
  // @end
}

// Where the string literal whose characters start at p ends: its closing
// double quote. A backslash hides the character after it.
static char *string_literal_end(char *p) {
  // @build 01.04 string_literal_end
  // Walk to the next '"', stepping over the character after each
  // backslash. Reaching a newline or the end of the input first is an error
  // at the opening quote: "unclosed string literal".
  char *start = p;
  for (; *p != '"'; p++) {
    if (*p == '\n' || *p == '\0')
      error_at(start - 1, "unclosed string literal");
    if (*p == '\\')
      p++;
  }
  return p;
  // @end
}

// A string literal, from the double quote at start: a TK_STR token whose str
// holds the bytes it stands for, its escapes decoded.
static Token *read_string_literal(char *start) {
  // @build 01.04 read_string_literal
  // Find the closing quote. calloc a buffer as long as the text between the
  // quotes and one more (no string decodes longer). Copy the characters
  // into it, each escape sequence as the one byte read_escaped_char says.
  // The token runs from the opening quote to just past the closing one.
  char *end = string_literal_end(start + 1);
  char *buf = calloc(1, end - start);
  int len = 0;

  for (char *p = start + 1; p < end;) {
    if (*p == '\\')
      buf[len++] = read_escaped_char(&p, p + 1);
    else
      buf[len++] = *p++;
  }

  Token *tok = new_token(TK_STR, start, end + 1);
  tok->str = buf;
  tok->str_len = len;
  return tok;
  // @end
}

// A character constant, from the single quote at start: a TK_NUM token whose
// value is the character's, 'a' is 97.
static Token *read_char_literal(char *start) {
  // @build 01.04 read_char_literal
  // One character, or one escape sequence, then the closing quote. A
  // newline or the end of the input first: "unclosed character constant";
  // nothing in it: "empty character constant"; more than one character
  // before the closing quote on the same line: "a character constant holds
  // one character". A value over 127 is "not supported yet": what it is
  // depends on whether char is signed, which this compiler does not know yet.
  char *p = start + 1;
  if (*p == '\n' || *p == '\0')
    error_at(start, "unclosed character constant");
  if (*p == '\'')
    error_at(start, "empty character constant");

  int c;
  if (*p == '\\')
    c = read_escaped_char(&p, p + 1);
  else
    c = (unsigned char)*p++;

  if (*p != '\'') {
    while (*p != '\'' && *p != '\n' && *p != '\0')
      p++;
    if (*p == '\'')
      error_at(start, "a character constant holds one character");
    error_at(start, "unclosed character constant");
  }
  if (c > 127)
    error_at(start, "a character constant above 127 is not supported yet");

  Token *tok = new_token(TK_NUM, start, p + 1);
  tok->val = c;
  return tok;
  // @end
}

// @from 01.04
// A number: digits in base 10, or with a prefix 0x (base 16), 0b (base 2)
// or 0 (base 8).
// @else
// // A number: decimal digits.
// @end
static Token *read_int_literal(char *start) {
  // @build 01.01 read_int_literal
  // strtoul reads the digits and says where they stop. A letter, a digit
  // or '_' right after them is an error: "invalid numeric constant". The
  // token is the digits; its value is what strtoul read.
  char *p = start;

  // @from 01.04
  int base = 10;
  if (p[0] == '0' && (p[1] == 'x' || p[1] == 'X') && isxdigit(p[2])) {
    p += 2;
    base = 16;
  } else if (p[0] == '0' && (p[1] == 'b' || p[1] == 'B') && (p[2] == '0' || p[2] == '1')) {
    p += 2;
    base = 2;
  } else if (*p == '0') {
    base = 8;
  }

  long val = strtoul(p, &p, base);
  // @else
  // long val = strtoul(p, &p, 10);
  // @end
  if (isalnum(*p) || *p == '_')
    error_at(start, "invalid numeric constant");

  Token *tok = new_token(TK_NUM, start, p);
  tok->val = val;
  return tok;
  // @end
}

// Mark every identifier that is a keyword as one.
void convert_keywords(Token *tok) {
  // @build 01.03 convert_keywords
  // Walk the list up to the end of the file, and give every token
  // is_keyword says yes to the kind TK_KEYWORD.
  for (Token *t = tok; t->kind != TK_EOF; t = t->next)
    if (is_keyword(t))
      t->kind = TK_KEYWORD;
  // @end
}

// Give every token its line and column, in one walk over the text: the
// tokens are in the order of the text, so each is found in its turn.
static void add_line_numbers(Token *tok) {
  // @build 01.01 add_line_numbers
  // Walk p through current_input counting lines from 1, and remember where
  // the current line starts. When p reaches the next token's loc, that
  // token's line is the count and its column is p minus the line's start,
  // plus 1. Stop after the last token.
  char *p = current_input;
  char *line = p;
  int n = 1;

  for (;;) {
    while (tok && p == tok->loc) {
      tok->line_no = n;
      tok->col = p - line + 1;
      tok = tok->next;
    }
    if (!tok || !*p)
      return;
    if (*p == '\n') {
      n++;
      line = p + 1;
    }
    p++;
  }
  // @end
}

// The text p, of the file filename, as a list of tokens that ends in a
// TK_EOF token.
Token *tokenize(char *filename, char *p) {
  // @build 01.01 tokenize
  // Remember filename and p for the error messages. Then, until the end of
  // p: skip spaces and newlines; read a number with read_int_literal; read
  // a '+' or a '-' as a token of one character; anything else is an error
  // at it, "invalid token". Each token goes on the end of the list. Last,
  // the end-of-file token, then every token's line and column.
  current_filename = filename;
  current_input = p;
  Token head = {0};
  Token *cur = &head;

  while (*p) {
    // @from 01.04
    // A line comment: up to the end of the line.
    if (startswith(p, "//")) {
      p += 2;
      while (*p && *p != '\n')
        p++;
      continue;
    }

    // A block comment: up to the first "*/".
    if (startswith(p, "/*")) {
      char *q = p + 2;
      while (*q && !startswith(q, "*/"))
        q++;
      if (!*q)
        error_at(p, "unclosed block comment");
      p = q + 2;
      continue;
    }

    // @end
    // Spaces, tabs and newlines only keep tokens apart.
    if (isspace(*p)) {
      p++;
      continue;
    }

    // A number.
    if (isdigit(*p)) {
      cur = cur->next = read_int_literal(p);
      p += cur->len;
      continue;
    }

    // @from 01.04
    // A string literal.
    if (*p == '"') {
      cur = cur->next = read_string_literal(p);
      p += cur->len;
      continue;
    }

    // A character constant: a number, to the parser.
    if (*p == '\'') {
      cur = cur->next = read_char_literal(p);
      p += cur->len;
      continue;
    }

    // @end
    // @from 01.03
    // An identifier, or a keyword: those are picked out at the end.
    if (is_ident1(*p)) {
      char *start = p;
      do {
        p++;
      } while (is_ident2(*p));
      cur = cur->next = new_token(TK_IDENT, start, p);
      continue;
    }

    // @end
    // @from 01.02
    // A punctuator: the longest one that starts here.
    int punct_len = read_punct(p);
    if (punct_len) {
      cur = cur->next = new_token(TK_PUNCT, p, p + punct_len);
      p += cur->len;
      continue;
    }
    // @else
    // // A plus or a minus.
    // if (*p == '+' || *p == '-') {
    //   cur = cur->next = new_token(TK_PUNCT, p, p + 1);
    //   p++;
    //   continue;
    // }
    // @end

    error_at(p, "invalid token");
  }

  // The end of the file sits on the newline that ends its last line, so an
  // error there shows that line, not an empty one after it.
  char *end = (p > current_input && p[-1] == '\n') ? p - 1 : p;
  cur = cur->next = new_token(TK_EOF, end, end);
  add_line_numbers(head.next);
  convert_keywords(head.next);   // @from 01.03
  return head.next;
  // @end
}
