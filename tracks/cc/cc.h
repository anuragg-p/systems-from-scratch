// cc.h: what the files of the compiler share. The token and the tree node,
// and every function that one file calls in another.
//
// Derived from chibicc's chibicc.h by Rui Ueyama
// (https://github.com/rui314/chibicc, MIT; the licence is in LICENSE).
//
// These six headers are all of the C library the compiler uses. It has to
// compile itself one day, on a machine whose C library is one we write, so
// it asks for little: no others, and only some functions of these.

#include <ctype.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct Node Node;   // @from 02.01

//
// tokenize.c
//

// What kind of token it is.
typedef enum {
  TK_IDENT,   // an identifier: x, main @from 01.03
  TK_PUNCT,   // a punctuator: + - == ->
  TK_KEYWORD, // a keyword: int, return @from 01.03
  TK_STR,     // a string literal: "hi\n" @from 01.04
  TK_NUM,     // an integer, or a character constant: 42, 0x2a, 'a'
  TK_EOF,     // the end of the file
} TokenKind;

// One token: its kind, and where in the source its text is. Tokens are a
// linked list, in the order of the source.
typedef struct Token Token;
struct Token {
  TokenKind kind; // its kind
  Token *next;    // the token after it
  long val;       // TK_NUM: its value
  char *loc;      // where its text starts in the source
  int len;        // how many characters of the source it is
  char *str;      // TK_STR: its bytes, escapes decoded, and a '\0' after them @from 01.04
  int str_len;    // TK_STR: how many bytes str holds, not counting the '\0' @from 01.04
  int line_no;    // its line, from 1
  int col;        // its column, from 1, in bytes: a tab is one
};

_Noreturn void error(char *fmt, ...);
_Noreturn void error_at(char *loc, char *fmt, ...);
_Noreturn void error_tok(Token *tok, char *fmt, ...);
bool equal(Token *tok, char *op);
Token *skip(Token *tok, char *op);
void convert_keywords(Token *tok);          // @from 01.03
Token *tokenize(char *filename, char *p);

// @internal
_Noreturn void todo(char *lesson, char *what);
// @end
// @from 02.01

//
// parse.c
//

// What kind of node it is: an operator, or a number.
typedef enum {
  ND_ADD,     // +
  ND_SUB,     // -
  ND_MUL,     // * @from 02.02
  ND_DIV,     // / @from 02.02
  ND_NEG,     // unary - @from 02.05
  ND_MOD,     // % @from 02.04
  ND_BITAND,  // & @from 02.04
  ND_BITOR,   // | @from 02.04
  ND_BITXOR,  // ^ @from 02.04
  ND_SHL,     // << @from 02.04
  ND_SHR,     // >> @from 02.04
  ND_EQ,      // == @from 02.05
  ND_NE,      // != @from 02.05
  ND_LT,      // < (and >, with the sides swapped) @from 02.05
  ND_LE,      // <= (and >=, with the sides swapped) @from 02.05
  ND_NOT,     // ! @from 02.05
  ND_BITNOT,  // ~ @from 02.05
  ND_NUM,     // an integer
} NodeKind;

// One node of the tree. An operator's operands are its children: lhs and
// rhs, or lhs alone for a unary operator.
struct Node {
  NodeKind kind;  // its kind
  Node *lhs;      // the left operand, or the only one
  Node *rhs;      // the right operand
  Token *tok;     // the token it was made from, for error messages
  long val;       // ND_NUM: its value
};

Node *parse(Token *tok);
// @end
// @from 02.03

//
// codegen.c
//

void codegen(Node *node, FILE *out);
// @end
