/*
 * parse.c - tokens to a statement tree.
 *
 * A recursive descent parser: one function per piece of the grammar, each
 * looking at the current token to decide what comes next. Expressions use
 * precedence climbing, so 1 + 2 * 3 groups as 1 + (2 * 3) without a
 * function per precedence level.
 *
 * The subset of SQL it reads:
 *
 *   SELECT result, ... [FROM t [AS alias]] [WHERE e] [ORDER BY e [ASC|DESC], ...]
 *          [LIMIT n [OFFSET m]]
 *          where FROM may join tables: t, u ... or t [INNER|CROSS] JOIN u [ON e] ... @from 08.01
 *   INSERT INTO t [(col, ...)] VALUES (e, ...), ...
 *   UPDATE t SET col = e, ... [WHERE e]
 *   DELETE FROM t [WHERE e]
 *   CREATE TABLE [IF NOT EXISTS] t (col [type] [constraints], ...)
 *   CREATE INDEX [IF NOT EXISTS] i ON t (col, ...)
 *   DROP TABLE|INDEX [IF EXISTS] name
 *   BEGIN, COMMIT (or END), ROLLBACK
 *   PRAGMA name [= value]
 *   EXPLAIN [QUERY PLAN] statement
 *
 * It also recognises much of what sqlite3 writes into a schema (UNIQUE,
 * CHECK, COLLATE, REFERENCES, ...) and notes it in s->unsupported, so that
 * we can open its databases.
 * Such tables are then read-only to us (schema.c). @from 03.03
 */
#include <ctype.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "db.h"

/* Moves to the next token that is not whitespace or a comment. */
static void advance(Parser *ps)
{
    do {
        ps->z += next_token(ps->z, &ps->tok);
    } while (ps->tok.type == TK_SPACE);
}

/* Starts parsing sql, with parse-tree memory taken from arena. */
void parser_init(Parser *ps, const char *sql, Arena *arena)
{
    ps->sql = sql;
    ps->z = sql;
    ps->arena = arena;
    advance(ps);
}

static int at(Parser *ps, int type) { return ps->tok.type == type; }

/* Consumes the current token if it has the given type; returns whether
 * it did. */
static int accept(Parser *ps, int type)
{
    if (!at(ps, type))
        return 0;
    advance(ps);
    return 1;
}

/* Sets the error message for the current token and returns NULL, so
 * pointer-returning callers can `return syntax_error(ps);`. */
static void *syntax_error(Parser *ps)
{
    if (at(ps, TK_EOF))
        err("incomplete input");
    else
        err("near \"%.*s\": syntax error", ps->tok.n, ps->tok.s);
    return NULL;
}

/* Like accept(), but a mismatch is a syntax error. */
static int expect(Parser *ps, int type)
{
    if (accept(ps, type))
        return 1;
    syntax_error(ps);
    return 0;
}

/* Keywords that may still be used as names. */
static int is_name_token(int type)
{
    switch (type) {
    case TK_ID: case TK_KEY: case TK_PLAN: case TK_QUERY: case TK_TRANSACTION:
    case TK_DEFERRED: case TK_IMMEDIATE: case TK_EXCLUSIVE: case TK_REPLACE:
    case TK_BEGIN: case TK_END: case TK_EXPLAIN: case TK_PRAGMA:
        return 1;
    }
    return 0;
}

/* A name token's text: quotes stripped, doubled quotes undone. */
static const char *name_text(Parser *ps, Token t)
{
    if (t.n >= 2 && (t.s[0] == '"' || t.s[0] == '`' || t.s[0] == '[')) {
        char q = t.s[0] == '[' ? ']' : t.s[0];
        char *out = arena_alloc(ps->arena, (size_t)t.n);
        int k = 0;
        for (int i = 1; i < t.n - 1; i++) {
            out[k++] = t.s[i];
            if (t.s[i] == q && q != ']' && i + 1 < t.n - 1 && t.s[i + 1] == q)
                i++;
        }
        out[k] = 0;
        return out;
    }
    return arena_strndup(ps->arena, t.s, (size_t)t.n);
}

/* Reads a name; NULL (error set) if the current token cannot be one. */
static const char *parse_name(Parser *ps)
{
    if (!is_name_token(ps->tok.type))
        return syntax_error(ps);
    const char *s = name_text(ps, ps->tok);
    advance(ps);
    return s;
}

/* ------------------------------------------------------------ expressions */

/* A zeroed expression node; col and aff start at -1 (unresolved, no
 * affinity). */
static Expr *new_expr(Parser *ps, int op)
{
    Expr *e = arena_alloc(ps->arena, sizeof *e);
    e->op = op;
    e->col = -1;
    e->aff = -1;
    return e;
}

/* A node with operands a and b (b is NULL for unary operators). */
static Expr *binary(Parser *ps, int op, Expr *a, Expr *b)
{
    Expr *e = new_expr(ps, op);
    e->a = a;
    e->b = b;
    return e;
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    return (c | 0x20) - 'a' + 10;
}

static Expr *parse_binary(Parser *ps, int min_prec);

// @from 08.06
static Stmt *new_stmt(Parser *ps, int kind);
static int parse_select(Parser *ps, Stmt *s);

/* Parses a subquery into e, a node of type E_SUBQUERY, E_EXISTS or
 * E_IN/E_NOTIN: at the SELECT after a "(", the whole SELECT, then the ")".
 * Returns e, or NULL with the error set. */
static Expr *parse_subquery(Parser *ps, Expr *e)
{
    // @build 08.06 a SELECT in parentheses
    // The SELECT is a statement of its own (parse_select) in e->sub, with
    // its text, as written, in e->sub->sql for EXPLAIN. Its names are bound
    // later, with the query around it. At most MAX_OUTER levels of
    // subqueries, one inside another.
    if (ps->depth == MAX_OUTER)
        return err("too many levels of subqueries (at most %d)", MAX_OUTER), (Expr *)NULL;
    const char *start = ps->tok.s;
    e->sub = new_stmt(ps, S_SELECT);
    ps->depth++;
    int rc = parse_select(ps, e->sub);
    ps->depth--;
    if (rc < 0)
        return NULL;
    const char *end = ps->tok.s;
    while (end > start && (end[-1] == ' ' || end[-1] == '\t' || end[-1] == '\n' || end[-1] == '\r'))
        end--;
    e->sub->sql = arena_strndup(ps->arena, start, (size_t)(end - start));
    if (!expect(ps, TK_RP))
        return NULL;
    return e;
    // @end
}
// @end

/* A literal, a name, a function call, or a parenthesized expression. */
static Expr *parse_primary(Parser *ps)
{
    Token t = ps->tok;
    Expr *e;
    switch (t.type) {
    case TK_INTEGER: {
        e = new_expr(ps, E_INT);
        char *s = arena_strndup(ps->arena, t.s, (size_t)t.n);
        errno = 0;
        unsigned long long v = strtoull(s, NULL, 10);
        if (errno == ERANGE || v > 9223372036854775807ULL) {
            e->op = E_REAL;       /* too big for an integer: sqlite3 makes it a float */
            e->v.type = V_REAL;
            e->v.r = strtod(s, NULL);
        } else {
            e->v.type = V_INT;
            e->v.i = (i64)v;
        }
        advance(ps);
        return e;
    }
    case TK_FLOAT:
        e = new_expr(ps, E_REAL);
        e->v.type = V_REAL;
        e->v.r = strtod(arena_strndup(ps->arena, t.s, (size_t)t.n), NULL);
        advance(ps);
        return e;
    case TK_STRING: {
        e = new_expr(ps, E_STR);
        /* The text between the quotes; a doubled '' is one quote. */
        char *out = arena_alloc(ps->arena, (size_t)t.n);
        int k = 0;
        for (int i = 1; i < t.n - 1; i++) {
            out[k++] = t.s[i];
            if (t.s[i] == '\'')
                i++;
        }
        e->v.type = V_TEXT;
        e->v.s = out;
        e->v.n = k;
        advance(ps);
        return e;
    }
    case TK_BLOB: {
        e = new_expr(ps, E_BLOB);
        /* x'...': t.n counts the x and both quotes. */
        int nhex = t.n - 3;
        char *out = arena_alloc(ps->arena, (size_t)(nhex / 2 + 1));
        for (int i = 0; i < nhex / 2; i++)
            out[i] = (char)(hexval(t.s[2 + 2 * i]) << 4 | hexval(t.s[3 + 2 * i]));
        e->v.type = V_BLOB;
        e->v.s = out;
        e->v.n = nhex / 2;
        advance(ps);
        return e;
    }
    case TK_NULL:
        advance(ps);
        return new_expr(ps, E_NULL);
    case TK_LP:
        advance(ps);
        // @from 08.06
        if (at(ps, TK_SELECT))
            return parse_subquery(ps, new_expr(ps, E_SUBQUERY));
        // @else
        // if (at(ps, TK_SELECT)) {
        //     err("subqueries are not supported");
        //     return NULL;
        // }
        // @end
        e = parse_binary(ps, 1);
        if (!e || !expect(ps, TK_RP))
            return NULL;
        return e;
    // @from 08.06
    case TK_EXISTS:              /* EXISTS (SELECT ...); NOT EXISTS is NOT of it */
        advance(ps);
        if (!expect(ps, TK_LP))
            return NULL;
        if (!at(ps, TK_SELECT))
            return syntax_error(ps);
        return parse_subquery(ps, new_expr(ps, E_EXISTS));
    // @end
    default:
        break;
    }
    if (!is_name_token(t.type))
        return syntax_error(ps);
    const char *name = name_text(ps, t);
    advance(ps);
    if (accept(ps, TK_LP)) {
        e = new_expr(ps, E_FUNC);
        e->name = name;
        if (at(ps, TK_STAR) || at(ps, TK_DISTINCT)) {
            err("aggregate functions are not supported: %s", name);
            return NULL;
        }
        Expr *args[16];
        int n = 0;
        if (!at(ps, TK_RP)) {
            do {
                if (n == 16)
                    return err("too many arguments to %s", name), (Expr *)NULL;
                if (!(args[n++] = parse_binary(ps, 1)))
                    return NULL;
            } while (accept(ps, TK_COMMA));
        }
        if (!expect(ps, TK_RP))
            return NULL;
        e->list = arena_alloc(ps->arena, (size_t)n * sizeof(Expr *) + 1);
        memcpy(e->list, args, (size_t)n * sizeof(Expr *));
        e->nlist = n;
        return e;
    }
    e = new_expr(ps, E_COLUMN);
    if (accept(ps, TK_DOT)) {
        e->qual = name;
        if (at(ps, TK_STAR))
            return syntax_error(ps);
        if (!(e->name = parse_name(ps)))
            return NULL;
    } else {
        e->name = name;
    }
    return e;
}

/* Prefix operators: - + NOT. NOT binds looser than comparisons, so
 * NOT a = b is NOT (a = b); - and + bind tighter than everything. */
static Expr *parse_unary(Parser *ps)
{
    if (accept(ps, TK_MINUS)) {
        if (at(ps, TK_INTEGER) && ps->tok.n == 19 && memcmp(ps->tok.s, "9223372036854775808", 19) == 0) {
            /* the one integer whose negation is in range but itself is not */
            Expr *e = new_expr(ps, E_INT);
            e->v.type = V_INT;
            e->v.i = INT64_MIN;
            advance(ps);
            return e;
        }
        Expr *a = parse_unary(ps);
        if (!a)
            return NULL;
        if (a->op == E_INT && a->v.i != 0) {    /* fold -5 into a literal */
            a->v.i = -a->v.i;
            return a;
        }
        if (a->op == E_REAL) {
            a->v.r = -a->v.r;
            return a;
        }
        return binary(ps, E_NEG, a, NULL);
    }
    if (accept(ps, TK_PLUS)) {
        Expr *a = parse_unary(ps);
        return a ? binary(ps, E_PLUS, a, NULL) : NULL;
    }
    if (accept(ps, TK_NOT)) {
        Expr *a = parse_binary(ps, 4);
        return a ? binary(ps, E_NOT, a, NULL) : NULL;
    }
    return parse_primary(ps);
}

/* Binding strength of the operator at the current token, or 0 if it is
 * not one. Higher binds tighter. A NOT here can only start NOT IN, NOT
 * BETWEEN, NOT LIKE or NOT NULL. */
static int op_prec(Parser *ps)
{
    switch (ps->tok.type) {
    case TK_OR:
        return 1;
    case TK_AND:
        return 2;
    case TK_EQ: case TK_NE: case TK_IS: case TK_IN: case TK_LIKE: case TK_BETWEEN:
    case TK_ISNULL: case TK_NOTNULL: case TK_NOT:
        return 4;
    case TK_LT: case TK_LE: case TK_GT: case TK_GE:
        return 5;
    case TK_PLUS: case TK_MINUS:
        return 6;
    case TK_STAR: case TK_SLASH: case TK_REM:
        return 7;
    case TK_CONCAT:
        return 8;
    }
    return 0;
}

/* The expression type of a plain binary operator token. */
static int binary_op(int tok)
{
    switch (tok) {
    case TK_OR: return E_OR;
    case TK_AND: return E_AND;
    case TK_EQ: return E_EQ;
    case TK_NE: return E_NE;
    case TK_LT: return E_LT;
    case TK_LE: return E_LE;
    case TK_GT: return E_GT;
    case TK_GE: return E_GE;
    case TK_PLUS: return E_ADD;
    case TK_MINUS: return E_SUB;
    case TK_STAR: return E_MUL;
    case TK_SLASH: return E_DIV;
    case TK_REM: return E_REM;
    case TK_CONCAT: return E_CONCAT;
    }
    return -1;
}

/* The operators that are not plain "left op right": IS [NOT], [NOT] IN
 * (...), [NOT] BETWEEN x AND y, [NOT] LIKE, ISNULL, NOTNULL, NOT NULL. */
static Expr *parse_special(Parser *ps, Expr *left)
{
    if (accept(ps, TK_ISNULL))
        return binary(ps, E_ISNULL, left, NULL);
    if (accept(ps, TK_NOTNULL))
        return binary(ps, E_NOTNULL, left, NULL);
    if (accept(ps, TK_IS)) {
        int op = accept(ps, TK_NOT) ? E_ISNOT : E_IS;
        Expr *right = parse_binary(ps, 5);
        return right ? binary(ps, op, left, right) : NULL;
    }
    int neg = accept(ps, TK_NOT);
    if (neg && accept(ps, TK_NULL))
        return binary(ps, E_NOTNULL, left, NULL);
    if (accept(ps, TK_BETWEEN)) {
        Expr *e = new_expr(ps, neg ? E_NOTBETWEEN : E_BETWEEN);
        e->a = left;
        if (!(e->b = parse_binary(ps, 5)) || !expect(ps, TK_AND) || !(e->c = parse_binary(ps, 5)))
            return NULL;
        return e;
    }
    if (accept(ps, TK_LIKE)) {
        Expr *right = parse_binary(ps, 5);
        return right ? binary(ps, neg ? E_NOTLIKE : E_LIKE, left, right) : NULL;
    }
    if (accept(ps, TK_IN)) {
        Expr *e = new_expr(ps, neg ? E_NOTIN : E_IN);
        e->a = left;
        // @from 08.06
        if (is_name_token(ps->tok.type))
            return err("IN with a table name is not supported"), (Expr *)NULL;
        if (!expect(ps, TK_LP))
            return NULL;
        if (at(ps, TK_SELECT))
            return parse_subquery(ps, e);
        // @else
        // if (!expect(ps, TK_LP))
        //     return NULL;
        // if (at(ps, TK_SELECT))
        //     return err("subqueries are not supported"), (Expr *)NULL;
        // @end
        Expr *items[256];
        int n = 0;
        if (!at(ps, TK_RP)) {
            do {
                if (n == 256)
                    return err("IN list too long"), (Expr *)NULL;
                if (!(items[n++] = parse_binary(ps, 1)))
                    return NULL;
            } while (accept(ps, TK_COMMA));
        }
        if (!expect(ps, TK_RP))
            return NULL;
        e->list = arena_alloc(ps->arena, (size_t)n * sizeof(Expr *) + 1);
        memcpy(e->list, items, (size_t)n * sizeof(Expr *));
        e->nlist = n;
        return e;
    }
    return syntax_error(ps);
}

/* Whether tok starts one of the forms parse_special() reads. */
static int is_special(int tok)
{
    return tok == TK_IS || tok == TK_IN || tok == TK_LIKE || tok == TK_BETWEEN ||
           tok == TK_ISNULL || tok == TK_NOTNULL || tok == TK_NOT;
}

/* Parses a run of binary operators by precedence climbing: an operator
 * takes as its right operand only what binds tighter than itself, so
 * 1 + 2 * 3 is 1 + (2 * 3) and 10 - 4 - 3 is (10 - 4) - 3. The result
 * holds only operators that bind at least as tightly as min_prec; a
 * weaker one is left for a caller further out. Returns NULL with the error
 * set on failure. */
static Expr *parse_binary(Parser *ps, int min_prec)
{
    Expr *left = parse_unary(ps);
    // @build 03.02 operators and precedence
    while (left) {
        int prec = op_prec(ps);
        if (prec == 0 || prec < min_prec)
            break;
        if (is_special(ps->tok.type)) {
            left = parse_special(ps, left);
            continue;
        }
        int op = binary_op(ps->tok.type);
        advance(ps);
        Expr *right = parse_binary(ps, prec + 1);
        if (!right)
            return NULL;
        left = binary(ps, op, left, right);
    }
    return left;
    // @end
}

/* Parses one full expression at the current token. */
Expr *parse_expr(Parser *ps)
{
    return parse_binary(ps, 1);
}

/* ------------------------------------------------------------ statements */

/* A zeroed statement of the given kind. */
static Stmt *new_stmt(Parser *ps, int kind)
{
    Stmt *s = arena_alloc(ps->arena, sizeof *s);
    s->kind = kind;
    return s;
}

// @from 08.01
/* True if the current token is the word w (in any case), which the
 * tokenizer reads as a name, not a keyword. */
static int at_word(Parser *ps, const char *w)
{
    return at(ps, TK_ID) && (size_t)ps->tok.n == strlen(w) && strncasecmp(ps->tok.s, w, (size_t)ps->tok.n) == 0;
}

/* True if the current token is a word that can start a join operator, or
 * USING. These are names to the tokenizer (a column may be called left),
 * so after a table name only this says they are not its alias. */
static int at_join_word(Parser *ps)
{
    static const char *words[] = {"INNER", "CROSS", "LEFT", "RIGHT", "FULL", "OUTER", "NATURAL", "USING"};
    for (size_t i = 0; i < sizeof words / sizeof words[0]; i++)
        if (at_word(ps, words[i]))
            return 1;
    return 0;
}

/* Reads a join operator that starts with a word: one to three words, then
 * JOIN. The words combine as in sqlite3 (sqlite3JoinType() in select.c):
 * INNER and CROSS give an inner join; LEFT, RIGHT, FULL (with or without
 * OUTER) and NATURAL are joins this engine does not have; any other mix is
 * an unknown join type. Returns 0 for an inner join, or -1 with the error
 * set. */
static int join_type(Parser *ps)
{
    enum { NATURAL = 1, LEFT = 2, OUTER = 4, RIGHT = 8, INNER = 16, CROSS = 32, BAD = 64 };
    static const struct { const char *word; int bits; } kw[] = {
        {"NATURAL", NATURAL}, {"LEFT", LEFT | OUTER}, {"OUTER", OUTER}, {"RIGHT", RIGHT | OUTER},
        {"FULL", LEFT | RIGHT | OUTER}, {"INNER", INNER}, {"CROSS", INNER | CROSS},
    };
    Token words[3];
    int n = 0, bits = 0;
    while (n < 3 && at(ps, TK_ID)) {
        int b = BAD;
        for (size_t i = 0; i < sizeof kw / sizeof kw[0]; i++)
            if (at_word(ps, kw[i].word))
                b = kw[i].bits;
        bits |= b;
        words[n++] = ps->tok;
        advance(ps);
    }
    if (!expect(ps, TK_JOIN))
        return -1;
    if ((bits & (INNER | OUTER)) == (INNER | OUTER) || (bits & BAD) || (bits & (OUTER | LEFT | RIGHT)) == OUTER) {
        char text[200];
        int k = 0;
        for (int i = 0; i < n; i++)
            k += snprintf(text + k, sizeof text - (size_t)k, "%s%.*s", i ? " " : "", words[i].n > 60 ? 60 : words[i].n,
                          words[i].s);
        return err("unknown join type: %s", text);
    }
    if (bits & NATURAL)
        return err("NATURAL JOIN is not supported");
    if ((bits & (LEFT | RIGHT)) == (LEFT | RIGHT))
        return err("FULL JOIN is not supported");
    if (bits & RIGHT)
        return err("RIGHT JOIN is not supported");
    if (bits & LEFT)
        return err("LEFT JOIN is not supported");
    return 0;
}

/* Parses the FROM clause, after the word FROM, into s->from and s->nfrom.
 * s->table and s->alias are set to the first table's, which is all that a
 * query on one table needs. Returns 0, or -1 with the error set. */
static int parse_from(Parser *ps, Stmt *s)
{
    FromItem items[MAX_FROM];
    int n = 0;
    // @build 08.01 the FROM clause
    // Read the first table, then one more for every comma or join operator
    // after it. A table is a name with an optional alias: AS and a name, or
    // a bare name that is not a join word. Every table but the first may
    // carry an ON (a comma join too, as in sqlite3). A join operator is
    // JOIN, or a join word: join_type() reads those. Refuse USING, a
    // parenthesis where a table should be (a subquery or a nested join),
    // and a 65th table.
    for (;;) {
        if (n == MAX_FROM)
            return err("at most %d tables in a join", MAX_FROM);
        FromItem *it = &items[n];
        memset(it, 0, sizeof *it);
        if (accept(ps, TK_LP))
            return err(at(ps, TK_SELECT) ? "subqueries in FROM are not supported"
                                         : "parenthesised joins are not supported");
        if (!(it->table = parse_name(ps)))
            return -1;
        if (accept(ps, TK_AS)) {
            if (!(it->alias = parse_name(ps)))
                return -1;
        } else if (at(ps, TK_ID) && !at_join_word(ps)) {
            it->alias = parse_name(ps);
        }
        if (accept(ps, TK_ON)) {
            if (n == 0)
                return err("a JOIN clause is required before ON");
            if (!(it->on = parse_expr(ps)))
                return -1;
        }
        if (at_word(ps, "USING"))
            return err(n == 0 ? "a JOIN clause is required before USING" : "USING is not supported");
        n++;
        if (accept(ps, TK_COMMA) || accept(ps, TK_JOIN))
            continue;
        if (!at_join_word(ps))
            break;
        if (join_type(ps) < 0)
            return -1;
    }
    // @end
    s->from = arena_alloc(ps->arena, (size_t)n * sizeof(FromItem));
    memcpy(s->from, items, (size_t)n * sizeof(FromItem));
    s->nfrom = n;
    s->table = items[0].table;
    s->alias = items[0].alias;
    return 0;
}
// @end

// @from 08.01
/* Parses a SELECT into s. Each result column is * (e NULL), x.* (e NULL,
 * star_of x) or an expression with an optional [AS] alias. The optional
 * clauses come in this order:
 *
 *   FROM table [[AS] alias], ...     s->from, s->nfrom (parse_from)
 *   WHERE expr                       s->where
 *   ORDER BY expr [ASC|DESC], ...    s->order, s->norder
 *   LIMIT expr [OFFSET expr]         s->limit, s->offset
 *
 * LIMIT a, b means LIMIT b OFFSET a. DISTINCT and GROUP BY are rejected
 * with a "not supported" error. Returns 0, or -1 with the error set. */
// @else
// /* Parses a SELECT into s. Each result column is * (e NULL; t.* reads as
//  * * too) or an expression with an optional [AS] alias. The optional
//  * clauses come in this order:
//  *
//  *   FROM table [[AS] alias]          s->table, s->alias
//  *   WHERE expr                       s->where
//  *   ORDER BY expr [ASC|DESC], ...    s->order, s->norder
//  *   LIMIT expr [OFFSET expr]         s->limit, s->offset
//  *
//  * LIMIT a, b means LIMIT b OFFSET a. DISTINCT, GROUP BY and joins are
//  * rejected with a "not supported" error. Returns 0, or -1 with the error
//  * set. */
// @end
static int parse_select(Parser *ps, Stmt *s)
{
    // @build 03.02 the SELECT statement
    if (!expect(ps, TK_SELECT))
        return -1;
    if (at(ps, TK_DISTINCT))
        return err("SELECT DISTINCT is not supported");
    if (at(ps, TK_ID) && ps->tok.n == 3 && strncasecmp(ps->tok.s, "ALL", 3) == 0)
        advance(ps);
    ResultCol cols[256];
    int n = 0;
    do {
        if (n == 256)
            return err("too many result columns");
        ResultCol *rc = &cols[n++];
        rc->e = NULL;
        rc->alias = NULL;
        rc->star_of = NULL;  // @from 08.01
        if (accept(ps, TK_STAR))
            continue;
        if (is_name_token(ps->tok.type)) {
            /* Looks ahead for t.*, and backs up if it is not one. */
            const char *save = ps->z;
            Token tok = ps->tok;
            advance(ps);
            // @from 08.01
            if (accept(ps, TK_DOT) && accept(ps, TK_STAR)) {
                rc->star_of = name_text(ps, tok);
                continue;
            }
            // @else
            // if (accept(ps, TK_DOT) && accept(ps, TK_STAR))
            //     continue;
            // @end
            ps->z = save;
            ps->tok = tok;
        }
        if (!(rc->e = parse_expr(ps)))
            return -1;
        if (accept(ps, TK_AS)) {
            if (!(rc->alias = parse_name(ps)))
                return -1;
        } else if (at(ps, TK_ID)) {
            rc->alias = parse_name(ps);
        }
    } while (accept(ps, TK_COMMA));
    s->cols = arena_alloc(ps->arena, (size_t)n * sizeof(ResultCol));
    memcpy(s->cols, cols, (size_t)n * sizeof(ResultCol));
    s->ncols = n;

    // @from 08.01
    if (accept(ps, TK_FROM) && parse_from(ps, s) < 0)
        return -1;
    // @else
    // if (accept(ps, TK_FROM)) {
    //     if (!(s->table = parse_name(ps)))
    //         return -1;
    //     if (accept(ps, TK_AS)) {
    //         if (!(s->alias = parse_name(ps)))
    //             return -1;
    //     } else if (at(ps, TK_ID)) {
    //         s->alias = parse_name(ps);
    //     }
    //     if (at(ps, TK_COMMA) || at(ps, TK_JOIN))
    //         return err("joins are not supported");
    // }
    // @end
    if (accept(ps, TK_WHERE) && !(s->where = parse_expr(ps)))
        return -1;
    if (at(ps, TK_GROUP))
        return err("GROUP BY is not supported");
    if (accept(ps, TK_ORDER)) {
        if (!expect(ps, TK_BY))
            return -1;
        OrderTerm terms[64];
        int k = 0;
        do {
            if (k == 64)
                return err("too many ORDER BY terms");
            if (!(terms[k].e = parse_expr(ps)))
                return -1;
            terms[k].desc = 0;
            if (accept(ps, TK_DESC))
                terms[k].desc = 1;
            else
                accept(ps, TK_ASC);
            k++;
        } while (accept(ps, TK_COMMA));
        s->order = arena_alloc(ps->arena, (size_t)k * sizeof(OrderTerm));
        memcpy(s->order, terms, (size_t)k * sizeof(OrderTerm));
        s->norder = k;
    }
    if (accept(ps, TK_LIMIT)) {
        if (!(s->limit = parse_expr(ps)))
            return -1;
        if (accept(ps, TK_OFFSET)) {
            if (!(s->offset = parse_expr(ps)))
                return -1;
        } else if (accept(ps, TK_COMMA)) {
            s->offset = s->limit;
            if (!(s->limit = parse_expr(ps)))
                return -1;
        }
    }
    return 0;
    // @end
}

/* Parses ( name, ... ) into an arena array. Returns 0, or -1 with the
 * error set. */
static int parse_name_list(Parser *ps, const char ***out, int *nout)
{
    const char *names[256];
    int n = 0;
    if (!expect(ps, TK_LP))
        return -1;
    do {
        if (n == 256)
            return err("too many columns");
        if (!(names[n++] = parse_name(ps)))
            return -1;
    } while (accept(ps, TK_COMMA));
    if (!expect(ps, TK_RP))
        return -1;
    *out = arena_alloc(ps->arena, (size_t)n * sizeof(char *));
    memcpy(*out, names, (size_t)n * sizeof(char *));
    *nout = n;
    return 0;
}

/* INSERT INTO t [(cols)] VALUES (...), ...: every row must have the
 * same number of terms, which is recorded in s->ncols. The rows are
 * collected in a growing heap array that is freed on every path. */
static int parse_insert(Parser *ps, Stmt *s)
{
    advance(ps);    /* INSERT */
    if (at(ps, TK_OR))
        return err("INSERT OR ... is not supported");
    if (!expect(ps, TK_INTO) || !(s->table = parse_name(ps)))
        return -1;
    if (at(ps, TK_LP) && parse_name_list(ps, &s->names, &s->nnames) < 0)
        return -1;
    if (at(ps, TK_SELECT))
        return err("INSERT ... SELECT is not supported");
    if (!expect(ps, TK_VALUES))
        return -1;
    int cap = 16, n = 0;
    Expr ***rows = xmalloc((size_t)cap * sizeof(Expr **));
    int width = -1;
    do {
        Expr *vals[1024];
        int k = 0;
        if (!expect(ps, TK_LP))
            goto fail;
        do {
            if (k == 1024) {
                err("too many values");
                goto fail;
            }
            if (!(vals[k++] = parse_expr(ps)))
                goto fail;
        } while (accept(ps, TK_COMMA));
        if (!expect(ps, TK_RP))
            goto fail;
        if (width >= 0 && k != width) {
            err("all VALUES must have the same number of terms");
            goto fail;
        }
        width = k;
        if (n == cap) {
            cap *= 2;
            rows = xrealloc(rows, (size_t)cap * sizeof(Expr **));
        }
        rows[n] = arena_alloc(ps->arena, (size_t)k * sizeof(Expr *));
        memcpy(rows[n], vals, (size_t)k * sizeof(Expr *));
        n++;
    } while (accept(ps, TK_COMMA));
    s->rows = arena_alloc(ps->arena, (size_t)n * sizeof(Expr **));
    memcpy(s->rows, rows, (size_t)n * sizeof(Expr **));
    s->nrows = n;
    s->ncols = width;
    free(rows);
    return 0;
fail:
    free(rows);
    return -1;
}

/* UPDATE t SET col = e, ... [WHERE e]. The column names go to s->names
 * and the expressions to s->sets, in step. */
static int parse_update(Parser *ps, Stmt *s)
{
    advance(ps);    /* UPDATE */
    if (at(ps, TK_OR))
        return err("UPDATE OR ... is not supported");
    if (!(s->table = parse_name(ps)) || !expect(ps, TK_SET))
        return -1;
    const char *names[256];
    Expr *sets[256];
    int n = 0;
    do {
        if (n == 256)
            return err("too many columns");
        if (!(names[n] = parse_name(ps)) || !expect(ps, TK_EQ) || !(sets[n] = parse_expr(ps)))
            return -1;
        n++;
    } while (accept(ps, TK_COMMA));
    s->names = arena_alloc(ps->arena, (size_t)n * sizeof(char *));
    s->sets = arena_alloc(ps->arena, (size_t)n * sizeof(Expr *));
    memcpy(s->names, names, (size_t)n * sizeof(char *));
    memcpy(s->sets, sets, (size_t)n * sizeof(Expr *));
    s->nnames = n;
    // @from 08.01
    if (at(ps, TK_FROM))
        return err("UPDATE ... FROM is not supported");
    // @end
    if (accept(ps, TK_WHERE) && !(s->where = parse_expr(ps)))
        return -1;
    return 0;
}

/* DELETE FROM t [WHERE e]. */
static int parse_delete(Parser *ps, Stmt *s)
{
    advance(ps);    /* DELETE */
    if (!expect(ps, TK_FROM) || !(s->table = parse_name(ps)))
        return -1;
    if (accept(ps, TK_WHERE) && !(s->where = parse_expr(ps)))
        return -1;
    return 0;
}

/* Skips a balanced ( ... ) group, for constraints that only need to be
 * stepped over. */
static int skip_group(Parser *ps)
{
    if (!expect(ps, TK_LP))
        return -1;
    int depth = 1;
    while (depth > 0) {
        if (at(ps, TK_EOF) || at(ps, TK_ILLEGAL))
            return syntax_error(ps), -1;
        if (at(ps, TK_LP))
            depth++;
        else if (at(ps, TK_RP))
            depth--;
        advance(ps);
    }
    return 0;
}

/* Skips to the next , or ) at this level (the rest of a REFERENCES
 * clause). */
static int skip_clause(Parser *ps)
{
    while (!at(ps, TK_COMMA) && !at(ps, TK_RP)) {
        if (at(ps, TK_EOF) || at(ps, TK_ILLEGAL) || at(ps, TK_SEMI))
            return syntax_error(ps), -1;
        if (at(ps, TK_LP)) {
            if (skip_group(ps) < 0)
                return -1;
        } else {
            advance(ps);
        }
    }
    return 0;
}

// @from 08.07
/* Records a UNIQUE or PRIMARY KEY constraint on the columns names[0..n) of
 * CREATE TABLE s. They are kept in the order they are written, column
 * constraints and table constraints mixed, because sqlite3 numbers their
 * indexes in that order. A second PRIMARY KEY is an error, as in sqlite3.
 * Returns 0, or -1 with the error set. */
static int add_unique(Parser *ps, Stmt *s, const char **names, int n, int primary_key, int column, int desc)
{
    if (primary_key)
        for (int i = 0; i < s->nuniques; i++)
            if (s->uniques[i].primary_key)
                return err("table \"%s\" has more than one primary key", s->table);
    if (n > 8)
        s->unsupported = "a UNIQUE or PRIMARY KEY constraint on more than 8 columns";
    Unique *u = arena_alloc(ps->arena, (size_t)(s->nuniques + 1) * sizeof *u);
    if (s->nuniques)
        memcpy(u, s->uniques, (size_t)s->nuniques * sizeof *u);
    u[s->nuniques].names = arena_alloc(ps->arena, (size_t)n * sizeof(char *));
    memcpy(u[s->nuniques].names, names, (size_t)n * sizeof(char *));
    u[s->nuniques].nnames = n;
    u[s->nuniques].primary_key = primary_key;
    u[s->nuniques].column = column;
    u[s->nuniques].desc = desc;
    s->uniques = u;
    s->nuniques++;
    return 0;
}

/* A table constraint's columns, ( name [COLLATE c] [ASC|DESC], ... ), as a
 * UNIQUE or PRIMARY KEY constraint. A COLLATE makes the table one this
 * engine cannot write: its index would order text another way. Returns 0 or
 * -1 with the error set. */
static int parse_unique(Parser *ps, Stmt *s, int primary_key)
{
    const char *names[256];
    int n = 0, desc = 0;
    if (!expect(ps, TK_LP))
        return -1;
    do {
        if (n == 256)
            return err("too many columns");
        if (!(names[n++] = parse_name(ps)))
            return -1;
        if (accept(ps, TK_COLLATE)) {
            s->unsupported = "COLLATE";
            if (!parse_name(ps))
                return -1;
        }
        if (accept(ps, TK_DESC))
            desc = 1;
        else
            accept(ps, TK_ASC);
    } while (accept(ps, TK_COMMA));
    if (accept(ps, TK_AUTOINCREMENT))
        s->unsupported = "AUTOINCREMENT";
    if (!expect(ps, TK_RP))
        return -1;
    return add_unique(ps, s, names, n, primary_key, 0, desc);
}
// @end

/* One column of CREATE TABLE: name, declared type, then constraints in
 * any order. Constraints that this engine cannot enforce are parsed and
 * noted in s->unsupported, which makes the table read-only. */
static int parse_column_def(Parser *ps, Stmt *s, ColumnDef *d)
{
    memset(d, 0, sizeof *d);
    if (!(d->name = parse_name(ps)))
        return -1;
    /* The type: names, then maybe (n) or (n, m). Kept as written. */
    const char *start = NULL, *end = NULL;
    while (at(ps, TK_ID)) {
        if (!start)
            start = ps->tok.s;
        end = ps->tok.s + ps->tok.n;
        advance(ps);
    }
    if (start && at(ps, TK_LP)) {
        if (skip_group(ps) < 0)
            return -1;
        /* the current token is the one after ')': the type ends before it */
        end = ps->tok.s;
        while (end > start && isspace((unsigned char)end[-1]))
            end--;
    }
    d->type = start ? arena_strndup(ps->arena, start, (size_t)(end - start)) : "";
    for (;;) {
        if (accept(ps, TK_CONSTRAINT)) {
            if (!parse_name(ps))
                return -1;
        }
        if (accept(ps, TK_PRIMARY)) {
            if (!expect(ps, TK_KEY))
                return -1;
            d->primary_key = 1;
            // @from 08.07
            if (add_unique(ps, s, &d->name, 1, 1, 1, at(ps, TK_DESC)) < 0)
                return -1;
            // @end
            if (accept(ps, TK_DESC))
                s->unsupported = "PRIMARY KEY DESC";
            accept(ps, TK_ASC);
            if (accept(ps, TK_AUTOINCREMENT))
                s->unsupported = "AUTOINCREMENT";
        } else if (accept(ps, TK_NOT)) {
            if (!expect(ps, TK_NULL))
                return -1;
            d->not_null = 1;
        } else if (accept(ps, TK_NULL)) {
            /* allowed, means nothing */
        } else if (accept(ps, TK_UNIQUE)) {
            // @from 08.07
            if (add_unique(ps, s, &d->name, 1, 0, 1, 0) < 0)
                return -1;
            // @else
            // s->unsupported = "UNIQUE";
            // @end
        } else if (accept(ps, TK_CHECK)) {
            s->unsupported = "CHECK";
            if (skip_group(ps) < 0)
                return -1;
        } else if (accept(ps, TK_DEFAULT)) {
            if (at(ps, TK_LP)) {
                advance(ps);
                if (!(d->dflt = parse_expr(ps)) || !expect(ps, TK_RP))
                    return -1;
            } else if (!(d->dflt = parse_unary(ps))) {
                return -1;
            }
            // @from 08.06
            if (has_subquery(d->dflt))      /* sqlite3's words for it */
                return err("default value of column [%s] is not constant", d->name);
            // @end
        } else if (accept(ps, TK_COLLATE)) {
            s->unsupported = "COLLATE";
            if (!parse_name(ps))
                return -1;
        } else if (accept(ps, TK_REFERENCES)) {
            s->unsupported = "REFERENCES";
            if (skip_clause(ps) < 0)
                return -1;
        } else {
            break;
        }
    }
    return 0;
}

/* CREATE TABLE or CREATE [UNIQUE] INDEX. Besides the parse tree, s->sql
 * gets the text sqlite_schema stores: the fixed prefix plus the
 * statement's own text from the name on, without trailing whitespace. */
static int parse_create(Parser *ps, Stmt **out)
{
    advance(ps);    /* CREATE */
    int unique = accept(ps, TK_UNIQUE);
    int kind;
    if (accept(ps, TK_TABLE)) {
        kind = S_CREATE_TABLE;
        if (unique)
            return syntax_error(ps), -1;
    } else if (accept(ps, TK_INDEX)) {
        kind = S_CREATE_INDEX;
    } else {
        if (at(ps, TK_ID))
            return err("CREATE %.*s is not supported", ps->tok.n, ps->tok.s);
        return syntax_error(ps), -1;
    }
    Stmt *s = *out = new_stmt(ps, kind);
    s->unique = unique;
    if (accept(ps, TK_IF)) {
        if (!expect(ps, TK_NOT) || !expect(ps, TK_EXISTS))
            return -1;
        s->if_not_exists = 1;
    }
    const char *name_start = ps->tok.s;
    if (kind == S_CREATE_TABLE) {
        if (!(s->table = parse_name(ps)))
            return -1;
        if (at(ps, TK_AS))
            return err("CREATE TABLE ... AS is not supported");
        if (!expect(ps, TK_LP))
            return -1;
        ColumnDef defs[256];
        int n = 0;
        for (;;) {
            if (at(ps, TK_PRIMARY) || at(ps, TK_UNIQUE) || at(ps, TK_CHECK) || at(ps, TK_FOREIGN) ||
                at(ps, TK_CONSTRAINT))
                break;
            if (n == 256)
                return err("too many columns");
            if (parse_column_def(ps, s, &defs[n++]) < 0)
                return -1;
            if (!accept(ps, TK_COMMA))
                goto close;
        }
        /* Table constraints follow the columns. A single-column PRIMARY
         * KEY marks that column. */
        do {
            if (accept(ps, TK_CONSTRAINT) && !parse_name(ps))
                return -1;
            if (accept(ps, TK_PRIMARY)) {
                // @from 08.07
                if (!expect(ps, TK_KEY) || parse_unique(ps, s, 1) < 0)
                    return -1;
                // @else
                // const char **names;
                // int nn;
                // if (!expect(ps, TK_KEY) || parse_name_list(ps, &names, &nn) < 0)
                //     return -1;
                // if (nn != 1) {
                //     s->unsupported = "a PRIMARY KEY of several columns";
                // } else {
                //     for (int i = 0; i < n; i++)
                //         if (strcasecmp(defs[i].name, names[0]) == 0)
                //             defs[i].primary_key = 1;
                // }
                // @end
            } else if (accept(ps, TK_UNIQUE)) {
                // @from 08.07
                if (parse_unique(ps, s, 0) < 0)
                    return -1;
                // @else
                // s->unsupported = "UNIQUE";
                // if (skip_group(ps) < 0)
                //     return -1;
                // @end
            } else if (accept(ps, TK_CHECK)) {
                s->unsupported = "CHECK";
                if (skip_group(ps) < 0)
                    return -1;
            } else if (accept(ps, TK_FOREIGN)) {
                s->unsupported = "FOREIGN KEY";
                if (skip_clause(ps) < 0)
                    return -1;
            } else {
                return syntax_error(ps), -1;
            }
        } while (accept(ps, TK_COMMA));
    close:
        if (!expect(ps, TK_RP))
            return -1;
        // @from 08.07
        // @else
        // /* Only a column declared exactly INTEGER can be the primary key:
        //  * it becomes the rowid. sqlite3 backs any other primary key with
        //  * an automatic index, which this engine does not keep. */
        // int npk = 0;
        // for (int i = 0; i < n; i++) {
        //     if (!defs[i].primary_key)
        //         continue;
        //     if (++npk > 1)
        //         s->unsupported = "a PRIMARY KEY of several columns";
        //     else if (strcasecmp(defs[i].type, "INTEGER") != 0)
        //         s->unsupported = "a PRIMARY KEY that is not INTEGER PRIMARY KEY";
        // }
        // @end
        if (accept(ps, TK_WITHOUT)) {
            s->unsupported = "WITHOUT ROWID";
            if (!parse_name(ps))
                return -1;
        }
        if (n == 0)
            return syntax_error(ps), -1;
        s->defs = arena_alloc(ps->arena, (size_t)n * sizeof(ColumnDef));
        memcpy(s->defs, defs, (size_t)n * sizeof(ColumnDef));
        s->ndefs = n;
        // @from 08.07
        /* A constraint names columns of this table. Only the INTEGER PRIMARY
         * KEY may say DESC (it has no index): any other would need an index
         * kept in descending order, which this engine does not keep. */
        for (int i = 0; i < s->nuniques; i++) {
            Unique *u = &s->uniques[i];
            for (int k = 0; k < u->nnames; k++) {
                int found = 0;
                for (int c = 0; c < n; c++)
                    if (strcasecmp(defs[c].name, u->names[k]) == 0)
                        found = 1;
                if (!found)
                    return err("no such column: %s", u->names[k]);
            }
            if (u->desc && !u->column && rowid_constraint(s, u) < 0)
                s->unsupported = "DESC index columns";
        }
        // @end
    } else {
        if (!(s->name = parse_name(ps)) || !expect(ps, TK_ON) || !(s->table = parse_name(ps)))
            return -1;
        if (!expect(ps, TK_LP))
            return -1;
        const char *names[8];
        int n = 0;
        do {
            if (n == 8)
                return err("an index may have at most 8 columns");
            if (!is_name_token(ps->tok.type)) {
                s->unsupported = "indexes on expressions";
                if (skip_clause(ps) < 0)
                    return -1;
                continue;
            }
            names[n++] = parse_name(ps);
            if (accept(ps, TK_COLLATE)) {
                s->unsupported = "COLLATE";
                if (!parse_name(ps))
                    return -1;
            }
            if (accept(ps, TK_DESC))
                s->unsupported = "DESC index columns";
            accept(ps, TK_ASC);
        } while (accept(ps, TK_COMMA));
        if (!expect(ps, TK_RP))
            return -1;
        if (accept(ps, TK_WHERE)) {
            s->unsupported = "partial indexes";
            if (!parse_expr(ps))
                return -1;
        }
        // @from 08.07
        // @else
        // if (unique)
        //     s->unsupported = "UNIQUE indexes";
        // @end
        s->names = arena_alloc(ps->arena, (size_t)(n + 1) * sizeof(char *));
        memcpy(s->names, names, (size_t)n * sizeof(char *));
        s->nnames = n;
    }
    /* The statement ends where the current token (; or end of input) starts. */
    const char *end = ps->tok.s;
    while (end > name_start && (end[-1] == ' ' || end[-1] == '\t' || end[-1] == '\n' || end[-1] == '\r'))
        end--;
    const char *prefix = kind == S_CREATE_TABLE ? "CREATE TABLE " : unique ? "CREATE UNIQUE INDEX " : "CREATE INDEX ";
    size_t plen = strlen(prefix), blen = (size_t)(end - name_start);
    char *sql = arena_alloc(ps->arena, plen + blen + 1);
    memcpy(sql, prefix, plen);
    memcpy(sql + plen, name_start, blen);
    sql[plen + blen] = 0;
    s->sql = sql;
    return 0;
}

/* PRAGMA name [= value] or PRAGMA name(value). The value is kept as
 * text in s->pragma_value, with a leading - if it had one. */
static int parse_pragma(Parser *ps, Stmt *s)
{
    advance(ps);    /* PRAGMA */
    if (!(s->name = parse_name(ps)))
        return -1;
    int paren = 0;
    if (accept(ps, TK_EQ) || (paren = accept(ps, TK_LP))) {
        Token t = ps->tok;
        int neg = 0;
        if (accept(ps, TK_MINUS)) {
            neg = 1;
            t = ps->tok;
        }
        if (t.type == TK_STRING) {
            s->pragma_value = arena_strndup(ps->arena, t.s + 1, (size_t)(t.n - 2));
        } else if (t.type == TK_INTEGER || is_name_token(t.type) || t.type == TK_ON ||
                   t.type == TK_DELETE || t.type == TK_NULL) {
            char *v = arena_alloc(ps->arena, (size_t)t.n + 2);
            if (neg)
                v[0] = '-';
            memcpy(v + neg, t.s, (size_t)t.n);
            s->pragma_value = v;
        } else {
            return syntax_error(ps), -1;
        }
        advance(ps);
        if (paren && !expect(ps, TK_RP))
            return -1;
    }
    return 0;
}

/* Parses the next statement into *out. Returns 1 for a statement, 0 at
 * the end of input (*out is NULL), -1 on error with the message set. Empty
 * statements (stray semicolons) are skipped; a statement must be followed
 * by a semicolon or the end of input. */
int parse_statement(Parser *ps, Stmt **out)
{
    *out = NULL;
    while (accept(ps, TK_SEMI))
        ;
    if (at(ps, TK_EOF))
        return 0;
    if (at(ps, TK_ILLEGAL))
        return syntax_error(ps), -1;
    int explain = 0;
    if (accept(ps, TK_EXPLAIN)) {
        explain = 1;
        if (accept(ps, TK_QUERY)) {
            if (!expect(ps, TK_PLAN))
                return -1;
            explain = 2;
        }
    }
    Stmt *s = NULL;
    int rc;
    switch (ps->tok.type) {
    case TK_SELECT:
        s = new_stmt(ps, S_SELECT);
        rc = parse_select(ps, s);
        break;
    case TK_INSERT:
        s = new_stmt(ps, S_INSERT);
        rc = parse_insert(ps, s);
        break;
    case TK_REPLACE:
        return err("REPLACE is not supported");
    case TK_UPDATE:
        s = new_stmt(ps, S_UPDATE);
        rc = parse_update(ps, s);
        break;
    case TK_DELETE:
        s = new_stmt(ps, S_DELETE);
        rc = parse_delete(ps, s);
        break;
    case TK_CREATE:
        rc = parse_create(ps, &s);
        break;
    case TK_DROP:
        advance(ps);
        if (accept(ps, TK_TABLE)) {
            s = new_stmt(ps, S_DROP_TABLE);
        } else if (accept(ps, TK_INDEX)) {
            s = new_stmt(ps, S_DROP_INDEX);
        } else {
            return syntax_error(ps), -1;
        }
        if (accept(ps, TK_IF)) {
            if (!expect(ps, TK_EXISTS))
                return -1;
            s->if_exists = 1;
        }
        rc = (s->name = parse_name(ps)) ? 0 : -1;
        break;
    case TK_BEGIN:
        advance(ps);
        s = new_stmt(ps, S_BEGIN);
        if (!accept(ps, TK_DEFERRED) && !accept(ps, TK_IMMEDIATE))
            accept(ps, TK_EXCLUSIVE);
        accept(ps, TK_TRANSACTION);
        rc = 0;
        break;
    case TK_COMMIT:
    case TK_END:
        advance(ps);
        s = new_stmt(ps, S_COMMIT);
        accept(ps, TK_TRANSACTION);
        rc = 0;
        break;
    case TK_ROLLBACK:
        advance(ps);
        s = new_stmt(ps, S_ROLLBACK);
        accept(ps, TK_TRANSACTION);
        rc = 0;
        break;
    case TK_PRAGMA:
        s = new_stmt(ps, S_PRAGMA);
        rc = parse_pragma(ps, s);
        break;
    default:
        return syntax_error(ps), -1;
    }
    if (rc < 0)
        return -1;
    if (!at(ps, TK_SEMI) && !at(ps, TK_EOF))
        return syntax_error(ps), -1;
    accept(ps, TK_SEMI);
    s->explain = explain;
    *out = s;
    return 1;
}
