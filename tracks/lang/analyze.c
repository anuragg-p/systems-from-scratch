// analyze.c: semantic analysis, the third phase. It walks the parse tree
// once and makes of it the syntax tree: only what the program means is
// kept (the operators and their operands, the statements and their
// parts), and none of the tokens that only shape the text. On the way it
// enters each name in the symbol table, the first time the text gives it
// a value, and points every use of a name at its entry. And it checks the
// language's static rule: a name used in an expression must have been
// given a value earlier in the text.

#include "mote.h"

static Symbol *table, **last = &table;   // the entries in order, and where the next goes
static int count;

Symbol *symbols(void) {
  return table;
}

static Symbol *find(Token *name) {
  // @build 01.08 the symbol table: a name looked up
  for (Symbol *s = table; s; s = s->next)
    if (s->len == name->len && !strncmp(s->name, name->text, name->len))
      return s;
  return NULL;
  // @end
}

// The entry of a name that is given a value here: a new one, numbered
// after the last, if the name has none yet.
static Symbol *enter(Token *name) {
  // @build 01.08 the symbol table: a name entered
  Symbol *s = find(name);
  if (!s) {
    s = calloc(1, sizeof *s);
    *s = (Symbol){.index = ++count, .name = name->text, .len = name->len,
                  .line = name->line, .col = name->col};
    *last = s;
    last = &s->next;
  }
  return s;
  // @end
}

static Node *new_node(NodeKind kind, Token *tok) {
  Node *n = calloc(1, sizeof *n);
  n->kind = kind;
  n->tok = tok;
  return n;
}

// An operator token's kind of node.
static NodeKind kind_of(Token *op) {
  static const char *text[] = {"+", "-", "*", "/", "==", "!=", "<", ">", "<=", ">="};
  static const NodeKind kind[] = {N_ADD, N_SUB, N_MUL, N_DIV, N_EQ, N_NE, N_LT, N_GT, N_LE, N_GE};
  int i = 0;
  while (!equal(op, text[i]))
    i++;
  return kind[i];
}

// An expr, term or factor of the parse tree, as an expression.
static Node *expression(Parse *p) {
  // @build 01.08 an expression: the parse tree's chains made binary nodes
  // A factor is a number, a name (which must have an entry already: the
  // static rule), a parenthesis (which is only its expression now) or a
  // minus. An expr or a term is a chain, operand, operator, operand ...:
  // each operator makes a node of everything to its left and the operand
  // to its right, so that a - b - c is (a - b) - c.
  Parse *k = p->kids;
  if (!strcmp(p->rule, "factor")) {
    Token *t = k->tok;
    if (t->kind == T_NUMBER) {
      Node *n = new_node(N_NUM, t);
      n->value = t->value;
      return n;
    }
    if (t->kind == T_NAME) {
      Node *n = new_node(N_VAR, t);
      if (!(n->sym = find(t)))
        error_tok(t, "%.*s is used before anything gives it a value", t->len, t->text);
      return n;
    }
    if (equal(t, "("))
      return expression(k->next);
    Node *n = new_node(N_NEG, t);
    n->lhs = expression(k->next);
    return n;
  }
  Node *n = expression(k);
  for (Parse *op = k->next; op; op = op->next->next) {
    Node *b = new_node(kind_of(op->tok), op->tok);
    b->lhs = n;
    b->rhs = expression(op->next);
    n = b;
  }
  return n;
  // @end
}

static Node *condition(Parse *p) {
  Node *n = new_node(kind_of(p->kids->next->tok), p->kids->next->tok);
  n->lhs = expression(p->kids);
  n->rhs = expression(p->kids->next->next);
  return n;
}

// The stmt nodes among the siblings from p on, as a list of statements;
// *stop is the first sibling that is not a stmt.
static Node *statements(Parse *p, Parse **stop);

static Node *statement(Parse *p) {
  // @build 01.08 a statement: its parts, and the names it gives values
  // In "x := e", e is analyzed first and x entered after, so that
  // "x := x + 1" breaks the static rule when x has no value before it.
  Parse *k = p->kids, *rest;
  Token *t = k->tok;
  Node *n;
  if (t->kind == T_NAME) {
    n = new_node(N_ASSIGN, t);
    n->lhs = expression(k->next->next);
    n->sym = enter(t);
  } else if (equal(t, "read")) {
    n = new_node(N_READ, t);
    n->sym = enter(k->next->tok);
  } else if (equal(t, "write")) {
    n = new_node(N_WRITE, t);
    n->lhs = expression(k->next);
  } else {
    n = new_node(equal(t, "if") ? N_IF : N_WHILE, t);
    n->cond = condition(k->next);
    n->body = statements(k->next->next->next, &rest);
    if (equal(rest->tok, "else"))
      n->els = statements(rest->next, &rest);
  }
  return n;
  // @end
}

static Node *statements(Parse *p, Parse **stop) {
  Node head = {0}, *cur = &head;
  for (; p && p->rule; p = p->next)
    cur = cur->next = statement(p);
  *stop = p;
  return head.next;
}

Node *analyze(Parse *tree) {
  Parse *rest;
  return statements(tree->kids, &rest);
}
