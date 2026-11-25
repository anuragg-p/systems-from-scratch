// @from 04.01
/*
 * expr.c - values and expressions.
 *
 * SQL values are dynamically typed: any column can hold NULL, an integer,
 * a float, text or a blob. A column's declared type only gives it an
 * "affinity", a preference applied when a value is stored or compared:
 * '42' put into an INTEGER column becomes the integer 42. NULL means
 * "unknown", so almost any operation on it gives NULL, and a condition
 * holds only when it is true - not false, and not NULL.
 *
 * These are SQLite's rules, followed closely enough that the same queries
 * give the same answers here and in sqlite3.
 */
// @else
// /*
//  * expr.c - SQL values, and the order they sort in.
//  *
//  * SQL values are dynamically typed: any column can hold NULL, an integer,
//  * a float, text or a blob, so values of different types must compare
//  * too. SQLite's order, followed here exactly, puts NULL first, then
//  * numbers, then text, then blobs.
//  */
// @end
#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "db.h"

/* ------------------------------------------------------------ comparing values */

/* Rank of a type in SQLite's sort order: NULL, numbers, text, blobs. */
static int type_class(int type)
{
    switch (type) {
    case V_NULL: return 0;
    case V_INT: case V_REAL: return 1;
    case V_TEXT: return 2;
    }
    return 3;
}

/* Returns -1, 0 or 1 as i is below, equal to or above r. The comparison
 * is exact: converting i to a double would lose precision above 2^53.
 * NaN sorts below every integer. */
static int cmp_int_real(i64 i, double r)
{
    if (isnan(r))
        return 1;
    if (r < -9223372036854775808.0)
        return 1;
    if (r >= 9223372036854775808.0)
        return -1;
    i64 y = (i64)r;               /* r with its fraction cut off, exactly */
    if (i != y)
        return i < y ? -1 : 1;
    double frac = r - (double)y;
    return frac > 0 ? -1 : frac < 0 ? 1 : 0;
}

/* SQLite's order: NULL < numbers < text < blobs. Numbers compare by
 * value, integers against floats exactly; text and blobs bytewise. */
int value_compare(const Value *a, const Value *b)
{
    int ca = type_class(a->type), cb = type_class(b->type);
    if (ca != cb)
        return ca < cb ? -1 : 1;
    switch (ca) {
    case 0:
        return 0;
    case 1:
        if (a->type == V_INT && b->type == V_INT)
            return a->i < b->i ? -1 : a->i > b->i;
        if (a->type == V_REAL && b->type == V_REAL)
            return a->r < b->r ? -1 : a->r > b->r;
        if (a->type == V_INT)
            return cmp_int_real(a->i, b->r);
        return -cmp_int_real(b->i, a->r);
    default: {
        int n = a->n < b->n ? a->n : b->n;
        int c = n ? memcmp(a->s, b->s, (size_t)n) : 0;
        if (c)
            return c < 0 ? -1 : 1;
        return a->n < b->n ? -1 : a->n > b->n;
    }
    }
}

// @from 04.01
/* ------------------------------------------------------------ numbers in text */

/* Reads a number from the start of s[0..n). Returns 0 if there is none,
 * 1 if there is one with something after it, 2 if all of s is a number
 * (spaces around it allowed). *v gets an integer if it is written as one
 * and fits, else a float. */
static int text_number(const char *s, int n, Value *v)
{
    int i = 0;
    while (i < n && isspace((unsigned char)s[i]))
        i++;
    int start = i, digits = 0, real = 0;
    if (i < n && (s[i] == '+' || s[i] == '-'))
        i++;
    while (i < n && isdigit((unsigned char)s[i]))
        i++, digits++;
    if (i < n && s[i] == '.') {
        real = 1;
        i++;
        while (i < n && isdigit((unsigned char)s[i]))
            i++, digits++;
    }
    if (digits == 0) {
        v->type = V_INT;
        v->i = 0;
        return 0;
    }
    if (i < n && (s[i] == 'e' || s[i] == 'E')) {
        int j = i + 1;
        if (j < n && (s[j] == '+' || s[j] == '-'))
            j++;
        if (j < n && isdigit((unsigned char)s[j])) {
            real = 1;
            i = j;
            while (i < n && isdigit((unsigned char)s[i]))
                i++;
        }
    }
    char tmp[400];
    int len = i - start < (int)sizeof tmp - 1 ? i - start : (int)sizeof tmp - 1;
    memcpy(tmp, s + start, (size_t)len);
    tmp[len] = 0;
    int end = i;
    while (end < n && isspace((unsigned char)s[end]))
        end++;
    int whole = end == n;
    if (!real) {
        errno = 0;
        long long x = strtoll(tmp, NULL, 10);
        if (errno != ERANGE) {
            v->type = V_INT;
            v->i = x;
            return whole ? 2 : 1;
        }
    }
    v->type = V_REAL;
    v->r = strtod(tmp, NULL);
    return whole ? 2 : 1;
}

/* Returns the value as a number, as arithmetic sees it: text and blobs
 * give the number they start with, or 0. */
static Value to_numeric(const Value *v)
{
    Value out = {0};
    switch (v->type) {
    case V_INT: case V_REAL:
        return *v;
    case V_TEXT: case V_BLOB:
        text_number(v->s, v->n, &out);
        return out;
    }
    return out;
}

/* Integer conversion that saturates at the i64 limits for floats outside
 * the range. */
static i64 to_int(const Value *v)
{
    Value n = to_numeric(v);
    if (n.type == V_INT)
        return n.i;
    if (n.r >= 9223372036854775807.0)
        return INT64_MAX;
    if (n.r <= -9223372036854775808.0)
        return INT64_MIN;
    return (i64)n.r;
}

static double to_real(const Value *v)
{
    Value n = to_numeric(v);
    return n.type == V_INT ? (double)n.i : n.r;
}

// @from 08.04
/* What sum(), total() and avg() add for v, read as func.c's sumStep reads
 * its argument (sqlite3_value_numeric_type, then the integer or the
 * double): NULL stays NULL (it is skipped), an integer stays one, and so
 * does text that is all an integer; any other value is a real, text that
 * is all a number giving that number, and other text and blobs the
 * number they start with, or 0. */
Value sum_operand(const Value *v)
{
    Value out = {0};
    if (v->type == V_NULL || v->type == V_INT || v->type == V_REAL)
        return *v;
    if (v->type == V_TEXT && text_number(v->s, v->n, &out) == 2)
        return out;
    out.type = V_REAL;
    out.r = to_real(v);
    return out;
}
// @end

/* Returns 1 for true, 0 for false, -1 for NULL: how a condition reads
 * a value. */
int value_truth(const Value *v)
{
    if (v->type == V_NULL)
        return -1;
    if (v->type == V_INT)
        return v->i != 0;
    return to_real(v) != 0.0;
}

/* Formats r like sqlite3's "%!.15g": 15 significant digits, and always a
 * decimal point, so a float never prints like an integer. */
void format_real(double r, char *buf, size_t n)
{
    if (r == 0) {
        snprintf(buf, n, "0.0");
        return;
    }
    if (isinf(r)) {
        snprintf(buf, n, r < 0 ? "-Inf" : "Inf");
        return;
    }
    char tmp[64];
    snprintf(tmp, sizeof tmp, "%.15g", r);
    char *e = strchr(tmp, 'e');
    if (e) {
        if (!memchr(tmp, '.', (size_t)(e - tmp)))
            snprintf(buf, n, "%.*s.0%s", (int)(e - tmp), tmp, e);
        else
            snprintf(buf, n, "%s", tmp);
    } else if (!strchr(tmp, '.')) {
        snprintf(buf, n, "%s.0", tmp);
    } else {
        snprintf(buf, n, "%s", tmp);
    }
}

/* Makes a text value holding a copy of s[0..n) in arena a. */
static Value text_value(Arena *a, const char *s, int n)
{
    Value v = {0};
    v.type = V_TEXT;
    v.s = arena_strndup(a, s, (size_t)n);
    v.n = n;
    return v;
}

/* Returns the value as text, as || and text affinity see it. A blob keeps
 * its bytes and only changes type. */
static Value to_text(Arena *a, const Value *v)
{
    char buf[64];
    switch (v->type) {
    case V_INT:
        snprintf(buf, sizeof buf, "%lld", (long long)v->i);
        return text_value(a, buf, (int)strlen(buf));
    case V_REAL:
        format_real(v->r, buf, sizeof buf);
        return text_value(a, buf, (int)strlen(buf));
    case V_BLOB: {
        Value t = *v;
        t.type = V_TEXT;
        return t;
    }
    }
    return *v;
}

/* Applies a column's affinity to a value about to be stored in it, or
 * compared with it. Numeric affinities turn text that is entirely a number
 * into that number; REAL makes integers floats, while INTEGER and NUMERIC
 * turn whole-number floats into integers; TEXT turns numbers into text
 * (allocated from a). */
void apply_affinity(Value *v, int aff, Arena *a)
{
    switch (aff) {
    case AFF_INTEGER:
    case AFF_NUMERIC:
    case AFF_REAL:
        if (v->type == V_TEXT) {
            Value n;
            if (text_number(v->s, v->n, &n) == 2)
                *v = n;
        }
        if (aff == AFF_REAL && v->type == V_INT) {
            v->r = (double)v->i;
            v->type = V_REAL;
        } else if (aff != AFF_REAL && v->type == V_REAL && v->r == floor(v->r) &&
                   v->r >= -9223372036854775808.0 && v->r < 9223372036854775808.0) {
            v->i = (i64)v->r;
            v->type = V_INT;
        }
        break;
    case AFF_TEXT:
        if (v->type == V_INT || v->type == V_REAL)
            *v = to_text(a, v);
        break;
    }
}

/* ------------------------------------------------------------ resolving names */

static int is_rowid_name(const char *s)
{
    return strcasecmp(s, "rowid") == 0 || strcasecmp(s, "oid") == 0 || strcasecmp(s, "_rowid_") == 0;
}

// @from 08.06
/* Binds every column name in e to a column of t (whose name in this query
 * is alias, if it has one; t NULL: no table, as for INSERT's VALUES). A
 * name that is not a column but is rowid, oid or _rowid_ becomes E_ROWID.
 * It is resolve_names() on a scope of that one table, so a subquery in e
 * (in UPDATE's SET and WHERE, DELETE's WHERE, INSERT's VALUES) is bound
 * too, and can name t's columns. The scope lives in the statement's arena:
 * a subquery's scope points at it. Returns -1 with an error for an unknown
 * name. */
int resolve_expr(Db *db, Expr *e, Table *t, const char *alias)
{
    Scope *sc = arena_alloc(&db->stmt, sizeof *sc);
    if (t) {
        FromItem *it = arena_alloc(&db->stmt, sizeof *it);
        it->table = t->name;
        it->alias = alias;
        it->t = t;
        sc->from = it;
        sc->nfrom = 1;
    }
    return resolve_names(db, e, sc);
}
// @else
// /* Binds every column name in e to a column of t (whose name in this query
//  * is alias, if it has one). A name that is not a column but is rowid, oid
//  * or _rowid_ becomes E_ROWID. Returns -1 with an error for an unknown
//  * name. */
// int resolve_expr(Expr *e, Table *t, const char *alias)
// {
//     if (!e)
//         return 0;
//     if (e->op == E_COLUMN) {
//         if (e->qual) {
//             int ok = t && (strcasecmp(e->qual, alias ? alias : t->name) == 0);
//             if (!ok)
//                 return err("no such column: %s.%s", e->qual, e->name);
//         }
//         if (t) {
//             for (int i = 0; i < t->ncols; i++) {
//                 if (strcasecmp(t->cols[i].name, e->name) == 0) {
//                     e->col = i;
//                     e->aff = t->cols[i].affinity;
//                     return 0;
//                 }
//             }
//             if (is_rowid_name(e->name)) {
//                 e->op = E_ROWID;
//                 e->aff = AFF_INTEGER;
//                 return 0;
//             }
//         }
//         return err("no such column: %s", e->name);
//     }
//     if (resolve_expr(e->a, t, alias) < 0 || resolve_expr(e->b, t, alias) < 0 || resolve_expr(e->c, t, alias) < 0)
//         return -1;
//     for (int i = 0; i < e->nlist; i++)
//         if (resolve_expr(e->list[i], t, alias) < 0)
//             return -1;
//     return 0;
// }
// @end

// @from 08.01
/* True if FROM item it answers to the qualifier q (q.c, q.*): to its alias
 * if it has one, else to its table's name, as the catalog has it or as the
 * query wrote it (they differ for sqlite_master, which the catalog calls
 * sqlite_schema). In any case, as in sqlite3. */
int answers_to(FromItem *it, const char *q)
{
    if (it->alias)
        return strcasecmp(q, it->alias) == 0;
    return strcasecmp(q, it->t->name) == 0 || strcasecmp(q, it->table) == 0;
}

// @from 08.06
/* e, a name, is in no table of scope sc, the FROM clause of a subquery:
 * binds it in the queries around it, the nearest first, as each binds its
 * own names, and counts in e->depth how many queries out its table is,
 * which is where eval() finds its row while the subquery runs. A subquery
 * that names anything outside itself is correlated: its answer can change
 * with the outer row. Returns 0, or -1 with the error the outermost query
 * gives ("no such column: x"). */
static int resolve_outer(Db *db, Expr *e, Scope *sc)
{
    // @build 08.06 a name from the query outside
    // Bind e in the scope outside (resolve_names() on sc->outer), which
    // looks further out itself if it must; its error is the error. Wherever
    // it was found, that is one query further out from here than from
    // there (e->depth one more); and the query of this scope reads a row
    // it does not own (sc->correlated). Return 0, or -1.
    if (resolve_names(db, e, sc->outer) < 0)
        return -1;
    e->depth++;
    sc->correlated = 1;
    return 0;
    // @end
}
// @end

/* Binds every column name in e to a table of scope sc, the tables of a
 * SELECT's FROM clause: e->tab is the FROM item, e->tcol the column in its
 * table (TCOL_ROWID for the rowid), and e->col the slot of the joined row
 * that eval() reads, the item's base plus the column (the rowid's slot is
 * the one after its columns). With one table in scope this binds exactly as
 * resolve_expr() does: the slot is the column, and a rowid name becomes
 * E_ROWID. Returns 0, or -1 with sqlite3's error for a name that no table
 * has ("no such column") or that two tables have ("ambiguous column
 * name"). */
int resolve_names(Db *db, Expr *e, Scope *sc)
{
    (void)db;
    if (!e)
        return 0;
    if (e->op == E_COLUMN) {
        // @build 08.01 bind a name to its table
        // q.c looks only in the tables that answer to q (answers_to: the
        // alias if there is one, else the table's name). A bare c looks in
        // every table. One table with the column binds it;
        // two or more are ambiguous. None: a rowid name (rowid, oid,
        // _rowid_) means the rowid of the one table looked in, and is
        // ambiguous when there were several. Not one: return -1 with
        // "ambiguous column name: c" or "no such column: c" (q.c if it was
        // written so). Bound: set tab, tcol (TCOL_ROWID for the rowid), col
        // (the item's base plus the column; the rowid's slot is the one
        // after its columns) and aff (INTEGER for the rowid); with one
        // table a rowid name becomes E_ROWID instead, as resolve_expr()
        // makes it. Return 0.
        int hits = 0, looked = 0, k_hit = -1, c_hit = -1;
        for (int k = 0; k < sc->nfrom; k++) {
            FromItem *it = &sc->from[k];
            if (e->qual && !answers_to(it, e->qual))
                continue;
            looked++;
            if (hits == 0)
                k_hit = k;          /* the rowid's table, if no column turns up */
            for (int c = 0; c < it->t->ncols; c++) {
                if (strcasecmp(it->t->cols[c].name, e->name) == 0) {
                    if (hits++ == 0) {
                        k_hit = k;
                        c_hit = c;
                    }
                    break;
                }
            }
        }
        if (hits == 0 && looked > 0 && is_rowid_name(e->name)) {
            hits = looked;
            c_hit = TCOL_ROWID;
        }
        // @from 08.06
        if (hits == 0 && sc->outer)     /* a name of a query around this one (two here are ambiguous here) */
            return resolve_outer(db, e, sc);
        // @end
        if (hits != 1) {
            const char *what = hits ? "ambiguous column name" : "no such column";
            return e->qual ? err("%s: %s.%s", what, e->qual, e->name) : err("%s: %s", what, e->name);
        }
        FromItem *it = &sc->from[k_hit];
        e->tab = k_hit;
        e->tcol = c_hit;
        e->depth = 0;    /* found here (resolve_outer counts the steps out) */ // @from 08.06
        if (c_hit == TCOL_ROWID) {
            e->aff = AFF_INTEGER;
            e->col = it->base + it->t->ncols;  /* its slot, where a join's (or an Aggregate's) row has it */ // @from 08.06
            if (sc->nfrom == 1)
                e->op = E_ROWID;    /* one table: its rows carry the rowid */
            else
                e->col = it->base + it->t->ncols;
        } else {
            e->col = it->base + c_hit;
            e->aff = it->t->cols[c_hit].affinity;
        }
        return 0;
        // @end
    }
    // @from 08.06
    if ((e->op >= E_EQ && e->op <= E_ISNOT) || e->op == E_BETWEEN || e->op == E_NOTBETWEEN ||
        (e->sub && e->a && e->a->op == E_SUBQUERY))
        return resolve_row_values(db, e, sc);    /* where a subquery of several columns is a row value */
    if (e->sub)      /* a subquery: x of x IN (SELECT ...) is a name here, the SELECT a scope inside this one */
        return resolve_names(db, e->a, sc) < 0 ? -1 : resolve_subquery(db, e, sc);
    // @end
    if (resolve_names(db, e->a, sc) < 0 || resolve_names(db, e->b, sc) < 0 || resolve_names(db, e->c, sc) < 0)
        return -1;
    for (int i = 0; i < e->nlist; i++)
        if (resolve_names(db, e->list[i], sc) < 0)
            return -1;
    return 0;
}
// @end

// @from 08.06
/* Returns 1 if e depends on no row of its query, so it can be evaluated
 * once for the whole query. A name from a query outside is such a value:
 * the outer row does not change while this query runs. A correlated
 * subquery is not (it may read this query's row), nor is one not bound. */
// @else
// /* Returns 1 if e depends on no row at all, so it can be evaluated once. */
// @end
int is_constant(Expr *e)
{
    if (!e)
        return 1;
    // @from 08.06
    if (e->op == E_COLUMN || e->op == E_ROWID)
        return e->depth > 0;
    if (e->sub && (!e->q || e->correlated))
        return 0;
    // @else
    // if (e->op == E_COLUMN || e->op == E_ROWID)
    //     return 0;
    // @end
    if (!is_constant(e->a) || !is_constant(e->b) || !is_constant(e->c))
        return 0;
    for (int i = 0; i < e->nlist; i++)
        if (!is_constant(e->list[i]))
            return 0;
    return 1;
}

// @from 08.06
/* Returns 1 if e holds a subquery anywhere. */
int has_subquery(Expr *e)
{
    if (!e)
        return 0;
    if (e->sub || has_subquery(e->a) || has_subquery(e->b) || has_subquery(e->c))
        return 1;
    for (int i = 0; i < e->nlist; i++)
        if (has_subquery(e->list[i]))
            return 1;
    return 0;
}
// @end

/* ------------------------------------------------------------ evaluating */

/* Small setters that overwrite *v whole. set_real turns NaN into NULL, as
 * sqlite3 does. */
static void set_int(Value *v, i64 i)
{
    memset(v, 0, sizeof *v);
    v->type = V_INT;
    v->i = i;
}

static void set_null(Value *v)
{
    memset(v, 0, sizeof *v);
}

static void set_real(Value *v, double r)
{
    memset(v, 0, sizeof *v);
    if (isnan(r)) {
        v->type = V_NULL;
        return;
    }
    v->type = V_REAL;
    v->r = r;
}

// @from 04.02
/* True for the affinities that make a column compare as a number. */
static int is_numeric_aff(int aff)
{
    return aff == AFF_INTEGER || aff == AFF_REAL || aff == AFF_NUMERIC;
}
// @end

/* Evaluates the comparison op (E_EQ, E_NE, E_LT, E_LE, E_GT, E_GE, E_IS,
 * E_ISNOT) of a with b into *out: the integer 1 or 0, or NULL.
 *
 * NULL is handled first. For IS and IS NOT two NULLs are equal and a NULL
 * differs from anything else; for every other operator a NULL on either
 * side makes the answer NULL.
 *
 * Then SQLite's affinity rule: if one side is a column with a numeric
 * affinity and the other side is TEXT, BLOB or has none (aff -1), the
 * other side is converted with NUMERIC affinity; else if one side has TEXT
 * affinity and the other none, the other is converted to text. So for an
 * integer column x, x = '5' is true when x is 5. */
static void eval_compare(Db *db, int op, Value a, Value b, int aff_a, int aff_b, Value *out)
{
    // @build 04.02 compare two values
    if (op == E_IS || op == E_ISNOT) {
        if (a.type == V_NULL || b.type == V_NULL) {
            int same = a.type == V_NULL && b.type == V_NULL;
            set_int(out, op == E_IS ? same : !same);
            return;
        }
    } else if (a.type == V_NULL || b.type == V_NULL) {
        set_null(out);
        return;
    }
    if (is_numeric_aff(aff_a) && !is_numeric_aff(aff_b))
        apply_affinity(&b, AFF_NUMERIC, &db->rowa);
    else if (is_numeric_aff(aff_b) && !is_numeric_aff(aff_a))
        apply_affinity(&a, AFF_NUMERIC, &db->rowa);
    else if (aff_a == AFF_TEXT && aff_b == -1)
        apply_affinity(&b, AFF_TEXT, &db->rowa);
    else if (aff_b == AFF_TEXT && aff_a == -1)
        apply_affinity(&a, AFF_TEXT, &db->rowa);
    int c = value_compare(&a, &b);
    int r = 0;
    switch (op) {
    case E_EQ: case E_IS: r = c == 0; break;
    case E_NE: case E_ISNOT: r = c != 0; break;
    case E_LT: r = c < 0; break;
    case E_LE: r = c <= 0; break;
    case E_GT: r = c > 0; break;
    case E_GE: r = c >= 0; break;
    }
    set_int(out, r);
    // @end
}

/* AND and OR in SQL's three-valued logic, where NULL means "unknown": a
 * false side makes AND false and a true side makes OR true, whatever the
 * other side is; any other mix with an unknown side is unknown. So the
 * right side is evaluated only when the left one does not decide the
 * answer. Returns -1 if evaluating a side fails. */
static int eval_logic(Db *db, Expr *e, Row *row, Value *out)
{
    // @build 04.02 AND and OR
    Value a, b;
    if (eval(db, e->a, row, &a) < 0)
        return -1;
    int ta = value_truth(&a);
    if (e->op == E_AND && ta == 0) {
        set_int(out, 0);
        return 0;
    }
    if (e->op == E_OR && ta == 1) {
        set_int(out, 1);
        return 0;
    }
    if (eval(db, e->b, row, &b) < 0)
        return -1;
    int tb = value_truth(&b);
    if (e->op == E_AND) {
        if (tb == 0)
            set_int(out, 0);
        else if (ta == -1 || tb == -1)
            set_null(out);
        else
            set_int(out, 1);
    } else {
        if (tb == 1)
            set_int(out, 1);
        else if (ta == -1 || tb == -1)
            set_null(out);
        else
            set_int(out, 0);
    }
    return 0;
    // @end
}

/* Arithmetic on two values. Integers stay integers unless the result
 * overflows, when the operation is redone in floating point, as sqlite3
 * does. Division or remainder by zero gives NULL. */
static int eval_arith(int op, Value a, Value b, Value *out)
{
    if (a.type == V_NULL || b.type == V_NULL) {
        set_null(out);
        return 0;
    }
    Value x = to_numeric(&a), y = to_numeric(&b);
    if (x.type == V_INT && y.type == V_INT) {
        i64 r;
        switch (op) {
        case E_ADD:
            if (__builtin_add_overflow(x.i, y.i, &r))
                break;
            set_int(out, r);
            return 0;
        case E_SUB:
            if (__builtin_sub_overflow(x.i, y.i, &r))
                break;
            set_int(out, r);
            return 0;
        case E_MUL:
            if (__builtin_mul_overflow(x.i, y.i, &r))
                break;
            set_int(out, r);
            return 0;
        case E_DIV:
            if (y.i == 0) {
                set_null(out);
                return 0;
            }
            if (x.i == INT64_MIN && y.i == -1)
                break;
            set_int(out, x.i / y.i);
            return 0;
        case E_REM:
            if (y.i == 0) {
                set_null(out);
                return 0;
            }
            set_int(out, y.i == -1 ? 0 : x.i % y.i);
            return 0;
        }
        /* overflow: fall back to floats, as sqlite3 does */
    }
    double p = x.type == V_INT ? (double)x.i : x.r;
    double q = y.type == V_INT ? (double)y.i : y.r;
    switch (op) {
    case E_ADD: set_real(out, p + q); break;
    case E_SUB: set_real(out, p - q); break;
    case E_MUL: set_real(out, p * q); break;
    case E_DIV:
        if (q == 0)
            set_null(out);
        else
            set_real(out, p / q);
        break;
    case E_REM: {
        i64 ia = to_int(&x), ib = to_int(&y);
        if (ib == 0) {
            set_null(out);
            break;
        }
        if (ib == -1)
            ib = 1;
        set_real(out, (double)(ia % ib));
        break;
    }
    }
    return 0;
}

/* LIKE: % is any run of characters, _ any one; ASCII letters match either
 * case. Returns 1 on a match. */
static int like(const char *p, int pn, const char *s, int sn)
{
    int i = 0, j = 0;
    while (i < pn) {
        char c = p[i];
        if (c == '%') {
            while (i < pn && p[i] == '%')
                i++;
            if (i == pn)
                return 1;
            for (int k = j; k <= sn; k++)
                if (like(p + i, pn - i, s + k, sn - k))
                    return 1;
            return 0;
        }
        if (j >= sn)
            return 0;
        if (c != '_' && tolower((unsigned char)c) != tolower((unsigned char)s[j]))
            return 0;
        i++;
        j++;
    }
    return j == sn;
}

// @from 08.04
/* Scalar functions. An aggregate call evaluated here was not found as one
 * (it is in a query that is not an aggregate query): an error. */
// @else
// /* Scalar functions. Aggregates are recognised only to refuse them with a
//  * clear error. */
// @end
static int eval_func(Db *db, Expr *e, Row *row, Value *out)
{
    Value args[16];
    for (int i = 0; i < e->nlist; i++)
        if (eval(db, e->list[i], row, &args[i]) < 0)
            return -1;
    const char *f = e->name;
    int n = e->nlist;
    if (strcasecmp(f, "count") == 0 || strcasecmp(f, "sum") == 0 || strcasecmp(f, "avg") == 0 ||
        strcasecmp(f, "total") == 0 || strcasecmp(f, "group_concat") == 0 ||
        ((strcasecmp(f, "min") == 0 || strcasecmp(f, "max") == 0) && n == 1))
        // @from 08.04
        return err("misuse of aggregate: %s()", f);
        // @else
        // return err("aggregate functions are not supported: %s", f);
        // @end
    if (strcasecmp(f, "typeof") == 0 && n == 1) {
        static const char *names[] = {"null", "integer", "real", "text", "blob"};
        const char *s = names[args[0].type];
        *out = text_value(&db->rowa, s, (int)strlen(s));
        return 0;
    }
    if (strcasecmp(f, "length") == 0 && n == 1) {
        Value v = args[0];
        if (v.type == V_NULL) {
            set_null(out);
        } else if (v.type == V_BLOB) {
            set_int(out, v.n);
        } else {
            Value t = to_text(&db->rowa, &v);
            int chars = 0;
            for (int i = 0; i < t.n; i++)
                if (((unsigned char)t.s[i] & 0xc0) != 0x80)
                    chars++;
            set_int(out, chars);
        }
        return 0;
    }
    if (strcasecmp(f, "abs") == 0 && n == 1) {
        Value v = args[0];
        if (v.type == V_NULL) {
            set_null(out);
            return 0;
        }
        Value x = to_numeric(&v);
        if (x.type == V_INT) {
            if (x.i == INT64_MIN)
                return err("integer overflow");
            set_int(out, x.i < 0 ? -x.i : x.i);
        } else {
            set_real(out, fabs(x.r));
        }
        return 0;
    }
    if ((strcasecmp(f, "lower") == 0 || strcasecmp(f, "upper") == 0) && n == 1) {
        if (args[0].type == V_NULL) {
            set_null(out);
            return 0;
        }
        Value t = to_text(&db->rowa, &args[0]);
        char *s = arena_strndup(&db->rowa, t.s, (size_t)t.n);
        for (int i = 0; i < t.n; i++)
            s[i] = (char)(f[0] == 'l' || f[0] == 'L' ? tolower((unsigned char)s[i]) : toupper((unsigned char)s[i]));
        *out = t;
        out->s = s;
        return 0;
    }
    if ((strcasecmp(f, "coalesce") == 0 && n >= 2) || (strcasecmp(f, "ifnull") == 0 && n == 2)) {
        set_null(out);
        for (int i = 0; i < n; i++) {
            if (args[i].type != V_NULL) {
                *out = args[i];
                break;
            }
        }
        return 0;
    }
    return err("no such function: %s", f);
}

/* Evaluates e against row (NULL when there is none, e.g. for constants)
 * into *out. Text results live in db->rowa, which the caller resets
 * between rows. Returns 0, or -1 with the error set. */
int eval(Db *db, Expr *e, Row *row, Value *out)
{
    Value a, b, c;
    switch (e->op) {
    case E_NULL:
        set_null(out);
        return 0;
    case E_INT: case E_REAL: case E_STR: case E_BLOB:
        *out = e->v;
        return 0;
    case E_AGG:                  /* the Aggregate operator put its answer in a slot */ // @from 08.04
    case E_COLUMN:
        // @from 08.06
        if (e->depth)        /* a name from a query outside: that query's row */
            row = e->depth <= db->nouter ? db->outer[db->nouter - e->depth] : NULL;
        // @end
        if (!row || e->col < 0 || e->col >= row->ncols)
            return err("no such column: %s", e->name);
        *out = row->cols[e->col];
        return 0;
    case E_ROWID:
        // @from 08.06
        if (e->depth) {
            row = e->depth <= db->nouter ? db->outer[db->nouter - e->depth] : NULL;
            if (row && e->col >= 0 && e->col < row->ncols) {
                *out = row->cols[e->col];    /* an Aggregate's row: its slot, NULL for no rows */
                return 0;
            }
        }
        // @end
        if (!row)
            return err("no such column: rowid");
        set_int(out, row->rowid);
        return 0;
    case E_NEG:
        if (eval(db, e->a, row, &a) < 0)
            return -1;
        if (a.type == V_NULL) {
            set_null(out);
            return 0;
        }
        a = to_numeric(&a);
        if (a.type == V_INT && a.i != INT64_MIN)
            set_int(out, -a.i);
        else
            set_real(out, -(a.type == V_INT ? (double)a.i : a.r));
        return 0;
    case E_PLUS:
        return eval(db, e->a, row, out);
    case E_NOT:
        if (eval(db, e->a, row, &a) < 0)
            return -1;
        if (value_truth(&a) < 0)
            set_null(out);
        else
            set_int(out, !value_truth(&a));
        return 0;
    // @from 04.02
    case E_AND: case E_OR:
        return eval_logic(db, e, row, out);
    case E_EQ: case E_NE: case E_LT: case E_LE: case E_GT: case E_GE: case E_IS: case E_ISNOT:
        if (eval(db, e->a, row, &a) < 0 || eval(db, e->b, row, &b) < 0)
            return -1;
        eval_compare(db, e->op, a, b, e->a->aff, e->b->aff, out);
        return 0;
    // @else
    // case E_AND: case E_OR:
    //     return err("AND and OR are not supported");
    // case E_EQ: case E_NE: case E_LT: case E_LE: case E_GT: case E_GE: case E_IS: case E_ISNOT:
    //     return err("comparisons are not supported");
    // @end
    case E_ADD: case E_SUB: case E_MUL: case E_DIV: case E_REM:
        if (eval(db, e->a, row, &a) < 0 || eval(db, e->b, row, &b) < 0)
            return -1;
        return eval_arith(e->op, a, b, out);
    case E_CONCAT: {
        if (eval(db, e->a, row, &a) < 0 || eval(db, e->b, row, &b) < 0)
            return -1;
        if (a.type == V_NULL || b.type == V_NULL) {
            set_null(out);
            return 0;
        }
        Value x = to_text(&db->rowa, &a), y = to_text(&db->rowa, &b);
        char *s = arena_alloc(&db->rowa, (size_t)(x.n + y.n + 1));
        memcpy(s, x.s, (size_t)x.n);
        memcpy(s + x.n, y.s, (size_t)y.n);
        memset(out, 0, sizeof *out);
        out->type = V_TEXT;
        out->s = s;
        out->n = x.n + y.n;
        return 0;
    }
    case E_ISNULL: case E_NOTNULL:
        if (eval(db, e->a, row, &a) < 0)
            return -1;
        set_int(out, (a.type == V_NULL) == (e->op == E_ISNULL));
        return 0;
    // @from 04.02
    case E_BETWEEN: case E_NOTBETWEEN: {
        if (eval(db, e->a, row, &a) < 0 || eval(db, e->b, row, &b) < 0 || eval(db, e->c, row, &c) < 0)
            return -1;
        Value lo, hi;
        eval_compare(db, E_GE, a, b, e->a->aff, e->b->aff, &lo);
        eval_compare(db, E_LE, a, c, e->a->aff, e->c->aff, &hi);
        int tl = value_truth(&lo), th = value_truth(&hi);
        int t = (tl == 0 || th == 0) ? 0 : (tl < 0 || th < 0) ? -1 : 1;
        if (t < 0)
            set_null(out);
        else
            set_int(out, e->op == E_BETWEEN ? t : !t);
        return 0;
    }
    case E_IN: case E_NOTIN: {
        // @from 08.06
        if (e->sub)
            return eval_subquery(db, e, row, out);
        // @end
        if (eval(db, e->a, row, &a) < 0)
            return -1;
        if (a.type == V_NULL && e->nlist > 0) {   /* NULL IN () is false, as in sqlite3 */
            set_null(out);
            return 0;
        }
        int found = 0, saw_null = 0;
        for (int i = 0; i < e->nlist && !found; i++) {
            Value item, r;
            if (eval(db, e->list[i], row, &item) < 0)
                return -1;
            eval_compare(db, E_EQ, a, item, e->a->aff, -1, &r);
            if (r.type == V_NULL)
                saw_null = 1;
            else if (r.i)
                found = 1;
        }
        if (!found && saw_null)
            set_null(out);
        else
            set_int(out, e->op == E_IN ? found : !found);
        return 0;
    }
    // @else
    // case E_BETWEEN: case E_NOTBETWEEN: case E_IN: case E_NOTIN:
    //     return err("comparisons are not supported");
    // @end
    case E_LIKE: case E_NOTLIKE: {
        if (eval(db, e->a, row, &a) < 0 || eval(db, e->b, row, &b) < 0)
            return -1;
        if (a.type == V_NULL || b.type == V_NULL) {
            set_null(out);
            return 0;
        }
        Value x = to_text(&db->rowa, &a), p = to_text(&db->rowa, &b);
        int m = like(p.s, p.n, x.s, x.n);
        set_int(out, e->op == E_LIKE ? m : !m);
        return 0;
    }
    case E_FUNC:
        return eval_func(db, e, row, out);
    // @from 08.06
    case E_SUBQUERY: case E_EXISTS:
        return eval_subquery(db, e, row, out);
    // @end
    }
    return err("internal error: unknown expression %d", e->op);
}

/* ------------------------------------------------------------ printing */

/* Prints v as the shell shows it: NULL as nothing, floats via
 * format_real, text and blobs as raw bytes. */
void print_value(FILE *f, const Value *v)
{
    char buf[64];
    switch (v->type) {
    case V_NULL:
        break;
    case V_INT:
        fprintf(f, "%lld", (long long)v->i);
        break;
    case V_REAL:
        format_real(v->r, buf, sizeof buf);
        fputs(buf, f);
        break;
    default:
        fwrite(v->s, 1, (size_t)v->n, f);
        break;
    }
}

// @from 04.02
/* SQL spelling of a binary operator, for expr_text. */
static const char *op_text(int op)
{
    switch (op) {
    case E_OR: return "OR";
    case E_AND: return "AND";
    case E_EQ: return "=";
    case E_NE: return "!=";
    case E_LT: return "<";
    case E_LE: return "<=";
    case E_GT: return ">";
    case E_GE: return ">=";
    case E_IS: return "IS";
    case E_ISNOT: return "IS NOT";
    case E_ADD: return "+";
    case E_SUB: return "-";
    case E_MUL: return "*";
    case E_DIV: return "/";
    case E_REM: return "%";
    case E_CONCAT: return "||";
    case E_LIKE: return "LIKE";
    case E_NOTLIKE: return "NOT LIKE";
    }
    return "?";
}

/* Appends e to b as SQL. Binary operators are parenthesised. */
static void expr_write(Buf *b, Expr *e)
{
    char tmp[64];
    switch (e->op) {
    case E_NULL:
        buf_put(b, "NULL", 4);
        return;
    case E_INT:
        snprintf(tmp, sizeof tmp, "%lld", (long long)e->v.i);
        buf_put(b, tmp, strlen(tmp));
        return;
    case E_REAL:
        format_real(e->v.r, tmp, sizeof tmp);
        buf_put(b, tmp, strlen(tmp));
        return;
    case E_STR:
        buf_put(b, "'", 1);
        for (int i = 0; i < e->v.n; i++) {
            buf_put(b, e->v.s + i, 1);
            if (e->v.s[i] == '\'')
                buf_put(b, "'", 1);
        }
        buf_put(b, "'", 1);
        return;
    case E_BLOB:
        buf_put(b, "x'", 2);
        for (int i = 0; i < e->v.n; i++) {
            snprintf(tmp, sizeof tmp, "%02x", (unsigned char)e->v.s[i]);
            buf_put(b, tmp, 2);
        }
        buf_put(b, "'", 1);
        return;
    case E_COLUMN:
        // @from 08.01
        if (e->qual) {              /* as written: in a join, which table */
            buf_put(b, e->qual, strlen(e->qual));
            buf_put(b, ".", 1);
        }
        // @end
        buf_put(b, e->name, strlen(e->name));
        return;
    case E_ROWID:
        buf_put(b, "rowid", 5);
        return;
    case E_NEG: case E_PLUS: case E_NOT:
        buf_put(b, e->op == E_NEG ? "-" : e->op == E_PLUS ? "+" : "NOT ", e->op == E_NOT ? 4 : 1);
        expr_write(b, e->a);
        return;
    case E_ISNULL: case E_NOTNULL:
        expr_write(b, e->a);
        buf_put(b, e->op == E_ISNULL ? " IS NULL" : " IS NOT NULL", e->op == E_ISNULL ? 8 : 12);
        return;
    case E_BETWEEN: case E_NOTBETWEEN:
        expr_write(b, e->a);
        buf_put(b, e->op == E_BETWEEN ? " BETWEEN " : " NOT BETWEEN ", e->op == E_BETWEEN ? 9 : 13);
        expr_write(b, e->b);
        buf_put(b, " AND ", 5);
        expr_write(b, e->c);
        return;
    // @from 08.06
    case E_SUBQUERY: case E_EXISTS:      /* the SELECT as it was written */
        buf_put(b, e->op == E_EXISTS ? "EXISTS (" : "(", e->op == E_EXISTS ? 8 : 1);
        buf_put(b, e->sub->sql, strlen(e->sub->sql));
        buf_put(b, ")", 1);
        return;
    // @end
    case E_IN: case E_NOTIN:
        expr_write(b, e->a);
        buf_put(b, e->op == E_IN ? " IN (" : " NOT IN (", e->op == E_IN ? 5 : 9);
        // @from 08.06
        if (e->sub)
            buf_put(b, e->sub->sql, strlen(e->sub->sql));
        // @end
        for (int i = 0; i < e->nlist; i++) {
            if (i)
                buf_put(b, ", ", 2);
            expr_write(b, e->list[i]);
        }
        buf_put(b, ")", 1);
        return;
    case E_AGG:                  /* written as the call it was */ // @from 08.04
    case E_FUNC:
        buf_put(b, e->name, strlen(e->name));
        buf_put(b, "(", 1);
        // @from 08.04
        if (e->distinct)  // @from 08.05
            buf_put(b, "DISTINCT ", 9);  // @from 08.05
        if (e->star)
            buf_put(b, "*", 1);
        // @end
        for (int i = 0; i < e->nlist; i++) {
            if (i)
                buf_put(b, ", ", 2);
            expr_write(b, e->list[i]);
        }
        buf_put(b, ")", 1);
        return;
    }
    buf_put(b, "(", 1);
    expr_write(b, e->a);
    buf_put(b, " ", 1);
    const char *o = op_text(e->op);
    buf_put(b, o, strlen(o));
    buf_put(b, " ", 1);
    expr_write(b, e->b);
    buf_put(b, ")", 1);
}

/* Returns e written back as SQL, in arena a, for EXPLAIN. */
const char *expr_text(Arena *a, Expr *e)
{
    Buf b = {0};
    expr_write(&b, e);
    const char *s = arena_strndup(a, (const char *)b.p, b.n);
    buf_free(&b);
    return s;
}
// @end
// @end
