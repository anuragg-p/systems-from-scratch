// parse.c: the parser, the second phase. It reads the tokens by the
// grammar of the language, a function for each rule, and makes the parse
// tree: each function makes a node named after its rule, and hangs under
// it, in order, a node for every token it takes and every rule it calls.
// So the tree holds the whole derivation, every token included.
//
//   program = { stmt } .
//   stmt    = name ":=" expr | "read" name | "write" expr
//           | "if" cond "then" { stmt } [ "else" { stmt } ] "end"
//           | "while" cond "do" { stmt } "end" .
//   cond    = expr ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) expr .
//   expr    = term { ( "+" | "-" ) term } .
//   term    = factor { ( "*" | "/" ) factor } .
//   factor  = number | name | "(" expr ")" | "-" factor .
//
// Each rule's function decides what to do from the next token alone, and
// a token that fits no choice is a syntax error, at that token's place.

#include "mote.h"

static Token *tok;              // the next token

static Parse *stmt(void);
static Parse *expr(void);

static Parse *node(const char *rule) {
  Parse *n = calloc(1, sizeof *n);
  n->rule = rule;
  return n;
}

// kid hung under n, after the children it has.
static void add(Parse *n, Parse *kid) {
  Parse **p = &n->kids;
  while (*p)
    p = &(*p)->next;
  *p = kid;
}

// The next token is taken: a leaf under n.
static void take(Parse *n) {
  Parse *leaf = node(NULL);
  leaf->tok = tok;
  add(n, leaf);
  tok = tok->next;
}

static void expect(Parse *n, const char *text) {
  if (!equal(tok, text))
    error_tok(tok, "expected '%s'", text);
  take(n);
}

// Does the next token start a statement?
static bool starts_stmt(void) {
  return tok->kind == T_NAME || equal(tok, "read") || equal(tok, "write") || equal(tok, "if") ||
         equal(tok, "while");
}

// { stmt }: as many statements as there are, under n.
static void stmts(Parse *n) {
  while (starts_stmt())
    add(n, stmt());
}

static Parse *factor(void) {
  // @build 01.07 factor = number | name | "(" expr ")" | "-" factor
  Parse *n = node("factor");
  if (tok->kind == T_NUMBER || tok->kind == T_NAME) {
    take(n);
  } else if (equal(tok, "(")) {
    take(n);
    add(n, expr());
    expect(n, ")");
  } else if (equal(tok, "-")) {
    take(n);
    add(n, factor());
  } else {
    error_tok(tok, "expected a number, a name or '('");
  }
  return n;
  // @end
}

static Parse *term(void) {
  // @build 01.07 term = factor { ( "*" | "/" ) factor }
  Parse *n = node("term");
  add(n, factor());
  while (equal(tok, "*") || equal(tok, "/")) {
    take(n);
    add(n, factor());
  }
  return n;
  // @end
}

static Parse *expr(void) {
  // @build 01.07 expr = term { ( "+" | "-" ) term }
  Parse *n = node("expr");
  add(n, term());
  while (equal(tok, "+") || equal(tok, "-")) {
    take(n);
    add(n, term());
  }
  return n;
  // @end
}

static Parse *cond(void) {
  // @build 01.07 cond = expr comparison expr
  Parse *n = node("cond");
  add(n, expr());
  if (!(equal(tok, "==") || equal(tok, "!=") || equal(tok, "<") || equal(tok, ">") ||
        equal(tok, "<=") || equal(tok, ">=")))
    error_tok(tok, "expected a comparison");
  take(n);
  add(n, expr());
  return n;
  // @end
}

static Parse *stmt(void) {
  // @build 01.07 stmt: an assignment, read, write, if or while
  // The first token chooses: a name starts an assignment, each keyword
  // its own statement. A block's statements go on until a token that
  // cannot start one, which must then be the block's else or end.
  Parse *n = node("stmt");
  if (tok->kind == T_NAME) {
    take(n);
    expect(n, ":=");
    add(n, expr());
  } else if (equal(tok, "read")) {
    take(n);
    if (tok->kind != T_NAME)
      error_tok(tok, "expected a name");
    take(n);
  } else if (equal(tok, "write")) {
    take(n);
    add(n, expr());
  } else if (equal(tok, "if")) {
    take(n);
    add(n, cond());
    expect(n, "then");
    stmts(n);
    if (equal(tok, "else")) {
      take(n);
      stmts(n);
    }
    expect(n, "end");
  } else if (equal(tok, "while")) {
    take(n);
    add(n, cond());
    expect(n, "do");
    stmts(n);
    expect(n, "end");
  } else {
    error_tok(tok, "expected a statement");
  }
  return n;
  // @end
}

Parse *parse(Token *t) {
  // @build 01.07 program = { stmt }, to the end of the file
  // Anything left that does not start a statement is an error.
  tok = t;
  Parse *n = node("program");
  while (tok->kind != T_EOF)
    add(n, stmt());
  return n;
  // @end
}
