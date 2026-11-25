// mote.h: what the phases of the compiler share. Each phase is a file and
// a function: scan (scan.c) makes tokens of the text, parse (parse.c) a
// parse tree of the tokens, analyze (analyze.c) a syntax tree and a
// symbol table of the parse tree; then interpret (interp.c) runs the
// syntax tree, or generate (gen.c) writes assembly for it, after improve
// (improve.c) has given variables registers. main.c calls them in order.
// Memory is allocated with calloc and never freed: the compiler runs once
// and exits.

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(long) == 8, "a value is a long, so a long must be 64 bits");

// @internal
_Noreturn void todo(const char *lesson, const char *what);
// @end

// A token: a word, a number or an operator, and where it starts.
typedef enum { T_NAME, T_NUMBER, T_KEYWORD, T_OP, T_EOF } TokenKind;
typedef struct Token Token;
struct Token {
  TokenKind kind;
  const char *text;     // where it is in the source
  int len;
  long value;           // a number's value
  int line, col;        // where it starts, from 1 (a tab is one column)
  Token *next;
};
Token *scan(const char *file, const char *src);
bool equal(Token *tok, const char *text);           // a keyword or an operator, by its text
// An error at a place in the source: FILE:LINE:COL: message, and status 1.
_Noreturn void error_tok(Token *tok, const char *fmt, ...);

// @from 01.07
// A node of the parse tree: a use of a rule (rule is its name) or a token
// (rule is NULL). kids is the first of its children, next its next sibling.
typedef struct Parse Parse;
struct Parse {
  const char *rule;
  Token *tok;
  Parse *kids, *next;
};
Parse *parse(Token *tok);

// @end
// @from 01.08
// An entry of the symbol table: a name, numbered from 1 in the order the
// text first gives it a value, and where that is.
typedef struct Symbol Symbol;
struct Symbol {
  int index;
  const char *name;
  int len;
  int line, col;
  long value;           // the interpreter's: the value, and whether it has one @from 01.09
  bool has_value;       // @from 01.09
  int offset;           // the code generator's: where in memory it is kept @from 01.10
  int uses;             // the improver's: how often it appears @from 01.11
  const char *reg;      // and the register it is kept in, or NULL @from 01.11
  Symbol *next;
};

// A node of the syntax tree: an expression, a condition or a statement.
typedef enum {
  N_NUM, N_VAR, N_NEG, N_ADD, N_SUB, N_MUL, N_DIV,
  N_EQ, N_NE, N_LT, N_GT, N_LE, N_GE,
  N_ASSIGN, N_READ, N_WRITE, N_IF, N_WHILE,
} NodeKind;
typedef struct Node Node;
struct Node {
  NodeKind kind;
  Token *tok;           // where it is in the source, for messages
  long value;           // a number's value
  Symbol *sym;          // a variable's entry; for read and :=, the one given a value
  Node *lhs, *rhs;      // the operands, or a condition's two sides; for write and :=, lhs
  Node *cond, *body, *els;  // if and while
  Node *next;           // the next statement
};
Node *analyze(Parse *tree);
Symbol *symbols(void);

// @end
void interpret(Node *prog);         // @from 01.09
void generate(Node *prog);          // @from 01.10
void improve(Node *prog);           // @from 01.11
