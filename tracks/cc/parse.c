// parse.c: the parser. It reads the list of tokens by recursive descent and
// builds the tree of the expression. Each rule of the grammar is a function
// of the same name, and the rule is written at the top of its function.
// There is one rule for each level of precedence: a function reads the
// operators of its own level and calls the next tighter level for their
// operands, so the shape of the tree comes out of the calls.
//
// Each function returns the node it built, and through rest the first token
// it did not use. Nothing else changes: there is no "current token" kept
// anywhere, so looking ahead is just following tok->next.
//
// Derived from chibicc's parse.c by Rui Ueyama
// (https://github.com/rui314/chibicc, MIT; the licence is in LICENSE).

#include "cc.h"

static Node *expr(Token **rest, Token *tok);
static Node *bitor(Token **rest, Token *tok);       // @from 02.04
static Node *bitxor(Token **rest, Token *tok);      // @from 02.04
static Node *bitand(Token **rest, Token *tok);      // @from 02.04
static Node *equality(Token **rest, Token *tok);    // @from 02.05
static Node *relational(Token **rest, Token *tok);  // @from 02.05
static Node *shift(Token **rest, Token *tok);       // @from 02.04
static Node *add(Token **rest, Token *tok);
static Node *mul(Token **rest, Token *tok);         // @from 02.02
static Node *unary(Token **rest, Token *tok);       // @from 02.05
static Node *primary(Token **rest, Token *tok);

// A new node of kind, made from tok.
static Node *new_node(NodeKind kind, Token *tok) {
  // @build 02.01 new_node
  // calloc one, so every field starts at zero; set kind and tok.
  Node *node = calloc(1, sizeof(Node));
  node->kind = kind;
  node->tok = tok;
  return node;
  // @end
}

// A binary operator's node: lhs kind rhs.
static Node *new_binary(NodeKind kind, Node *lhs, Node *rhs, Token *tok) {
  // @build 02.01 new_binary
  // A new node with the two children.
  Node *node = new_node(kind, tok);
  node->lhs = lhs;
  node->rhs = rhs;
  return node;
  // @end
}

// A unary operator's node: one child, in lhs.
static Node *new_unary(NodeKind kind, Node *expr, Token *tok) {
  // @build 02.05 new_unary
  // A new node with expr as its only child.
  Node *node = new_node(kind, tok);
  node->lhs = expr;
  return node;
  // @end
}

// A number's node.
static Node *new_num(long val, Token *tok) {
  // @build 02.01 new_num
  // A new ND_NUM node holding val.
  Node *node = new_node(ND_NUM, tok);
  node->val = val;
  return node;
  // @end
}

// A whole expression: its loosest level.
static Node *expr(Token **rest, Token *tok) {
  // @from 02.04
  // expr = bitor
  return bitor(rest, tok);
  // @else
  // // expr = add
  // return add(rest, tok);
  // @end
}

// The level of "|", the loosest of the operators that work on bits.
static Node *bitor(Token **rest, Token *tok) {
  // bitor = bitxor ("|" bitxor)*
  // @build 02.04 bitor
  // As add does for + and -: one operand, then as long as "|" follows,
  // another, each pair becoming an ND_BITOR node that leans left.
  Node *node = bitxor(&tok, tok);
  while (equal(tok, "|")) {
    Token *start = tok;
    node = new_binary(ND_BITOR, node, bitxor(&tok, tok->next), start);
  }
  *rest = tok;
  return node;
  // @end
}

// The level of "^".
static Node *bitxor(Token **rest, Token *tok) {
  // bitxor = bitand ("^" bitand)*
  // @build 02.04 bitxor
  // The same, for "^" and ND_BITXOR, with bitand for the operands.
  Node *node = bitand(&tok, tok);
  while (equal(tok, "^")) {
    Token *start = tok;
    node = new_binary(ND_BITXOR, node, bitand(&tok, tok->next), start);
  }
  *rest = tok;
  return node;
  // @end
}

// The level of "&".
static Node *bitand(Token **rest, Token *tok) {
  // @from 02.05
  // bitand = equality ("&" equality)*
  // @else
  // // bitand = shift ("&" shift)*
  // @end
  // @build 02.04 bitand
  // The same, for "&" and ND_BITAND, with the next level for the operands.
  // @from 02.05
  Node *node = equality(&tok, tok);
  // @else
  // Node *node = shift(&tok, tok);
  // @end
  while (equal(tok, "&")) {
    Token *start = tok;
    // @from 02.05
    node = new_binary(ND_BITAND, node, equality(&tok, tok->next), start);
    // @else
    // node = new_binary(ND_BITAND, node, shift(&tok, tok->next), start);
    // @end
  }
  *rest = tok;
  return node;
  // @end
}

// The level of "==" and "!=".
static Node *equality(Token **rest, Token *tok) {
  // equality = relational ("==" relational | "!=" relational)*
  // @build 02.05 equality
  // As add does, for "==" (ND_EQ) and "!=" (ND_NE), with relational for
  // the operands.
  Node *node = relational(&tok, tok);

  for (;;) {
    Token *start = tok;

    if (equal(tok, "==")) {
      node = new_binary(ND_EQ, node, relational(&tok, tok->next), start);
      continue;
    }

    if (equal(tok, "!=")) {
      node = new_binary(ND_NE, node, relational(&tok, tok->next), start);
      continue;
    }

    *rest = tok;
    return node;
  }
  // @end
}

// The level of "<", "<=", ">" and ">=". There are nodes for the first two
// only: a > b is b < a, and a >= b is b <= a.
static Node *relational(Token **rest, Token *tok) {
  // relational = shift ("<" shift | "<=" shift | ">" shift | ">=" shift)*
  // @build 02.05 relational
  // As add does, for "<" (ND_LT) and "<=" (ND_LE) with shift for the
  // operands; ">" makes an ND_LT and ">=" an ND_LE with the two operands the
  // other way round.
  Node *node = shift(&tok, tok);

  for (;;) {
    Token *start = tok;

    if (equal(tok, "<")) {
      node = new_binary(ND_LT, node, shift(&tok, tok->next), start);
      continue;
    }

    if (equal(tok, "<=")) {
      node = new_binary(ND_LE, node, shift(&tok, tok->next), start);
      continue;
    }

    if (equal(tok, ">")) {
      node = new_binary(ND_LT, shift(&tok, tok->next), node, start);
      continue;
    }

    if (equal(tok, ">=")) {
      node = new_binary(ND_LE, shift(&tok, tok->next), node, start);
      continue;
    }

    *rest = tok;
    return node;
  }
  // @end
}

// The level of "<<" and ">>".
static Node *shift(Token **rest, Token *tok) {
  // shift = add ("<<" add | ">>" add)*
  // @build 02.04 shift
  // As add does, for "<<" (ND_SHL) and ">>" (ND_SHR), with add for the
  // operands.
  Node *node = add(&tok, tok);

  for (;;) {
    Token *start = tok;

    if (equal(tok, "<<")) {
      node = new_binary(ND_SHL, node, add(&tok, tok->next), start);
      continue;
    }

    if (equal(tok, ">>")) {
      node = new_binary(ND_SHR, node, add(&tok, tok->next), start);
      continue;
    }

    *rest = tok;
    return node;
  }
  // @end
}

// Sums and differences, left to right: 1 - 2 - 3 is (1 - 2) - 3.
static Node *add(Token **rest, Token *tok) {
  // @from 02.02
  // add = mul ("+" mul | "-" mul)*
  // @else
  // // add = primary ("+" primary | "-" primary)*
  // @end
  // @build 02.01 add
  // Read one operand. Then, as long as the next token is "+" or "-", read
  // another and make a node (ND_ADD or ND_SUB, made from the operator's
  // token) whose left child is everything so far and whose right child is
  // the new operand. Set *rest to the first token after the last operand,
  // and return the node.
  // @from 02.02
  Node *node = mul(&tok, tok);
  // @else
  // Node *node = primary(&tok, tok);
  // @end

  for (;;) {
    Token *start = tok;

    if (equal(tok, "+")) {
      // @from 02.02
      node = new_binary(ND_ADD, node, mul(&tok, tok->next), start);
      // @else
      // node = new_binary(ND_ADD, node, primary(&tok, tok->next), start);
      // @end
      continue;
    }

    if (equal(tok, "-")) {
      // @from 02.02
      node = new_binary(ND_SUB, node, mul(&tok, tok->next), start);
      // @else
      // node = new_binary(ND_SUB, node, primary(&tok, tok->next), start);
      // @end
      continue;
    }

    *rest = tok;
    return node;
  }
  // @end
}

// Products and quotients, left to right. They bind tighter than sums
// because add calls mul for its operands, not the other way round.
static Node *mul(Token **rest, Token *tok) {
  // @from 02.05
  // mul = unary ("*" unary | "/" unary | "%" unary)*
  // @end
  // @from 02.04
  // @from 02.05
  // @else
  // // mul = primary ("*" primary | "/" primary | "%" primary)*
  // @end
  // @else
  // // mul = primary ("*" primary | "/" primary)*
  // @end
  // @build 02.02 mul
  // As add does, for "*" (ND_MUL) and "/" (ND_DIV), with primary for the
  // operands.
  // @from 02.05
  Node *node = unary(&tok, tok);
  // @else
  // Node *node = primary(&tok, tok);
  // @end

  for (;;) {
    Token *start = tok;

    if (equal(tok, "*")) {
      // @from 02.05
      node = new_binary(ND_MUL, node, unary(&tok, tok->next), start);
      // @else
      // node = new_binary(ND_MUL, node, primary(&tok, tok->next), start);
      // @end
      continue;
    }

    if (equal(tok, "/")) {
      // @from 02.05
      node = new_binary(ND_DIV, node, unary(&tok, tok->next), start);
      // @else
      // node = new_binary(ND_DIV, node, primary(&tok, tok->next), start);
      // @end
      continue;
    }

    // @from 02.04
    if (equal(tok, "%")) {
      // @from 02.05
      node = new_binary(ND_MOD, node, unary(&tok, tok->next), start);
      // @else
      // node = new_binary(ND_MOD, node, primary(&tok, tok->next), start);
      // @end
      continue;
    }

    // @end
    *rest = tok;
    return node;
  }
  // @end
}

// The operators in front of an operand: +x, -x, !x and ~x. They bind
// tighter than any binary operator, and -!x is -(!x).
static Node *unary(Token **rest, Token *tok) {
  // unary = ("+" | "-" | "!" | "~") unary | primary
  // @build 02.05 unary
  // "+": the operand itself, no node. "-", "!" and "~": an ND_NEG, ND_NOT
  // or ND_BITNOT node over the operand, which is a unary again. Anything
  // else: a primary.
  if (equal(tok, "+"))
    return unary(rest, tok->next);

  if (equal(tok, "-"))
    return new_unary(ND_NEG, unary(rest, tok->next), tok);

  if (equal(tok, "!"))
    return new_unary(ND_NOT, unary(rest, tok->next), tok);

  if (equal(tok, "~"))
    return new_unary(ND_BITNOT, unary(rest, tok->next), tok);

  return primary(rest, tok);
  // @end
}

// The smallest pieces of an expression.
static Node *primary(Token **rest, Token *tok) {
  // @from 02.02
  // primary = "(" expr ")" | num
  // @else
  // // primary = num
  // @end
  // @build 02.01 primary
  // A number token: an ND_NUM node, and *rest is the token after it.
  // Anything else: "expected an expression", at the token.
  // @from 02.02
  if (equal(tok, "(")) {
    Node *node = expr(&tok, tok->next);
    *rest = skip(tok, ")");
    return node;
  }

  // @end
  if (tok->kind == TK_NUM) {
    Node *node = new_num(tok->val, tok);
    *rest = tok->next;
    return node;
  }

  error_tok(tok, "expected an expression");
  // @end
}

// The whole input: one expression, and then the end of the file.
Node *parse(Token *tok) {
  // @build 02.01 parse
  // An expr; then anything but the end of the file is an error at it:
  // "extra token".
  Node *node = expr(&tok, tok);
  if (tok->kind != TK_EOF)
    error_tok(tok, "extra token");
  return node;
  // @end
}
