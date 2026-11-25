// @from 05.03
/*
 * plan.c - choosing how to read a table, and EXPLAIN.
 *
 * A query says which rows it wants, not how to find them. The planner
 * looks at the WHERE clause for conditions an index can answer:
 *
 *   rowid = 5, id = 5 (an INTEGER PRIMARY KEY)    go straight to the row
 *   a = 5, with an index on a                     go straight to the entries
 *   rowid > 5, id BETWEEN 1 AND 9                 a range of the table
 *   a > 5, with an index on a                     a range of the index
 *   anything else                                 read every row
 *
 * Whatever it picks, the whole WHERE clause is still checked on every row
 * the access path produces, so a plan can only be slower, never wrong.
 * That keeps the planner small: it never has to prove a condition is
 * fully answered by the index.
 * @from 08.01
 * A join reads its tables in the order they are written, a nested loop @from 08.01
 * per table, and checks each condition as soon as the row holds every @from 08.01
 * table it names. @from 08.01
 */
// @else
// /*
//  * plan.c - the plan of a query: a scan that reads every row of the table,
//  * under whatever operators the query needs on top of it, and EXPLAIN.
//  */
// @end
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "db.h"

// @from 05.03
/* Splits e into the terms ANDed together at its top, appending to out[n..max)
 * and returning the new count. Terms past max are dropped, which is safe:
 * the whole WHERE is still checked per row. */
static int conjuncts(Expr *e, Expr **out, int n, int max)
{
    if (!e || n >= max)
        return n;
    if (e->op == E_AND) {
        n = conjuncts(e->a, out, n, max);
        return conjuncts(e->b, out, n, max);
    }
    out[n++] = e;
    return n;
}

#define ROWID (-2)    /* "the column" is the rowid itself */

/* True if e names the column col, or the rowid when col is ROWID. An
 * INTEGER PRIMARY KEY column is the rowid under another name. */
static int is_column(Table *t, Expr *e, int col)
{
    if (col == ROWID)
        return e->op == E_ROWID || (e->op == E_COLUMN && t->rowid_col >= 0 && e->col == t->rowid_col);
    return e->op == E_COLUMN && e->col == col;
}

/* What the WHERE terms say about one column: an equality, and a lower and
 * an upper bound (the first of each found, all against constants). */
typedef struct Bounds {
    Expr *eq;
    Expr *lo, *hi;
    int lo_incl, hi_incl;
} Bounds;

/* Collects into b what terms[0..n) say about column col (or ROWID).
 * Comparisons written constant-first are flipped so the column is always
 * on the left. */
static void find_bounds(Table *t, Expr **terms, int n, int col, Bounds *b)
{
    memset(b, 0, sizeof *b);
    for (int i = 0; i < n; i++) {
        Expr *e = terms[i];
        if (e->op == E_BETWEEN && is_column(t, e->a, col) && is_constant(e->b) && is_constant(e->c)) {
            if (!b->lo) {
                b->lo = e->b;
                b->lo_incl = 1;
            }
            if (!b->hi) {
                b->hi = e->c;
                b->hi_incl = 1;
            }
            continue;
        }
        if (e->op != E_EQ && e->op != E_LT && e->op != E_LE && e->op != E_GT && e->op != E_GE)
            continue;
        int op = e->op;
        Expr *val;
        if (is_column(t, e->a, col) && is_constant(e->b)) {
            val = e->b;
        } else if (is_column(t, e->b, col) && is_constant(e->a)) {
            val = e->a;      /* 5 < x is x > 5 */
            op = op == E_LT ? E_GT : op == E_LE ? E_GE : op == E_GT ? E_LT : op == E_GE ? E_LE : op;
        } else {
            continue;
        }
        if (op == E_EQ && !b->eq) {
            b->eq = val;
        } else if ((op == E_GT || op == E_GE) && !b->lo) {
            b->lo = val;
            b->lo_incl = op == E_GE;
        } else if ((op == E_LT || op == E_LE) && !b->hi) {
            b->hi = val;
            b->hi_incl = op == E_LE;
        }
    }
}
// @end

/* Decides how a statement reads table t, given its WHERE clause, and fills
 * *acc. The first access path that applies wins, in this order:
 *   1. the rowid equals a constant          ACCESS_ROWID_EQ
 *   2. an index's first column equals one   ACCESS_INDEX_EQ
 *   3. the rowid has a bound                ACCESS_ROWID_RANGE
 *   4. an index's first column has a bound  ACCESS_INDEX_RANGE
 *   5. none of these                        ACCESS_SCAN
 * Always returns 0; the int return leaves room for planning errors. */
int choose_access(Table *t, Expr *where, Access *acc)
{
    memset(acc, 0, sizeof *acc);
    acc->kind = ACCESS_SCAN;
    Expr *terms[64];
    int n = conjuncts(where, terms, 0, 64);
    Bounds b;
    // @build 05.03 choose how to read the table
    find_bounds(t, terms, n, ROWID, &b);
    if (b.eq) {
        acc->kind = ACCESS_ROWID_EQ;
        acc->lo = acc->hi = b.eq;
        acc->lo_incl = acc->hi_incl = 1;
        return 0;
    }
    for (Index *ix = t->indexes; ix; ix = ix->next) {
        Bounds ib;
        find_bounds(t, terms, n, ix->cols[0], &ib);
        if (ib.eq) {
            acc->kind = ACCESS_INDEX_EQ;
            acc->index = ix;
            acc->lo = acc->hi = ib.eq;
            acc->lo_incl = acc->hi_incl = 1;
            return 0;
        }
    }
    if (b.lo || b.hi) {
        acc->kind = ACCESS_ROWID_RANGE;
        acc->lo = b.lo;
        acc->hi = b.hi;
        acc->lo_incl = b.lo_incl;
        acc->hi_incl = b.hi_incl;
        return 0;
    }
    for (Index *ix = t->indexes; ix; ix = ix->next) {
        Bounds ib;
        find_bounds(t, terms, n, ix->cols[0], &ib);
        if (ib.lo || ib.hi) {
            acc->kind = ACCESS_INDEX_RANGE;
            acc->index = ix;
            acc->lo = ib.lo;
            acc->hi = ib.hi;
            acc->lo_incl = ib.lo_incl;
            acc->hi_incl = ib.hi_incl;
            return 0;
        }
    }
    return 0;
    // @end
}

/* Returns 1 if ORDER BY still needs a sort given the order the access path
 * acc produces rows in, 0 if that order already satisfies it. */
int sort_needed(Table *t, Access *acc, OrderTerm *order, int norder)
{
    if (norder == 0)
        return 0;
    // @build 05.03 when the sort can go
    /* A table's B-tree yields rows in rowid order: a plan that reads the
     * table itself needs no sort when the first term is the rowid
     * ascending (rowids are unique, so later terms cannot matter). An
     * index yields rows by its first column, then rowid: an index plan
     * needs no sort for that column ascending alone, and an INDEX_EQ plan
     * (all keys equal) none for the rowid ascending alone. */
    Expr *e = order[0].e;
    int asc = !order[0].desc;
    if (acc->kind == ACCESS_SCAN || acc->kind == ACCESS_ROWID_EQ || acc->kind == ACCESS_ROWID_RANGE)
        return !(asc && is_column(t, e, ROWID));
    if (norder == 1 && asc && is_column(t, e, acc->index->cols[0]))
        return 0;
    if (norder == 1 && asc && acc->kind == ACCESS_INDEX_EQ && is_column(t, e, ROWID))
        return 0;
    return 1;
    // @end
}

// @from 04.03
/* Evaluates a LIMIT or OFFSET expression to an integer. It must be a
 * constant, since it is read once before any row is produced. */
static int const_int(Db *db, Expr *e, i64 *out)
{
    Value v;
    if (!is_constant(e))
        return err("LIMIT and OFFSET must be constants");
    if (eval(db, e, NULL, &v) < 0)
        return -1;
    apply_affinity(&v, AFF_INTEGER, &db->stmt);
    if (v.type != V_INT)
        return err("datatype mismatch");
    *out = v.i;
    return 0;
}
// @end

// @from 04.02
// @from 04.03
// @from 05.03
/* Builds the operator tree for reading table t (NULL: no FROM clause):
 * scan, then filter by WHERE, then sort if the access path's order does
 * not already satisfy ORDER BY, then LIMIT/OFFSET. A negative OFFSET counts
 * as 0. */
// @else
// /* Builds the operator tree for reading table t (NULL: no FROM clause):
//  * scan, then filter by WHERE, then sort for ORDER BY, then LIMIT/OFFSET.
//  * A negative OFFSET counts as 0. */
// @end
// @else
// /* Builds the operator tree for reading table t (NULL: no FROM clause): a
//  * scan, with a filter on top of it for WHERE. A query with ORDER BY or
//  * LIMIT is refused. */
// @end
// @else
// /* Builds the operator tree for reading table t (NULL: no FROM clause),
//  * which is a scan alone: a query with WHERE, ORDER BY or LIMIT is
//  * refused. */
// @end
int plan_query(Db *db, Table *t, Expr *where, OrderTerm *order, int norder, Expr *limit, Expr *offset,
               Plan *plan)
{
    memset(plan, 0, sizeof *plan);
    // @from 05.03
    if (t && choose_access(t, where, &plan->acc) < 0)
        return -1;
    // @end
    // @from 05.02
    Op *op = op_scan(db, t, &plan->acc);
    // @else
    // Op *op = op_scan(db, t);
    // @end
    if (!op)
        return -1;
    // @from 04.02
    if (where)
        op = op_filter(db, op, where);
    // @else
    // if (where) {
    //     op_close(op);
    //     return err("WHERE is not supported");
    // }
    // @end
    // @from 04.03
    // @from 05.03
    if (norder && sort_needed(t, &plan->acc, order, norder)) {
    // @else
    // if (norder) {
    // @end
        plan->sorted = 1;
        op = op_sort(db, op, order, norder);
    }
    if (limit) {
        i64 l, o = 0;
        if (const_int(db, limit, &l) < 0 || (offset && const_int(db, offset, &o) < 0)) {
            op_close(op);
            return -1;
        }
        op = op_limit(db, op, l, o < 0 ? 0 : o);
    }
    // @else
    // if (norder || limit) {
    //     op_close(op);
    //     return err("%s is not supported", norder ? "ORDER BY" : "LIMIT");
    // }
    // @end
    plan->root = op;
    return 0;
}

// @from 08.01
/* ------------------------------------------------------------ joins (08.01) */

/* How many terms conjuncts() splits e into. */
static int count_terms(Expr *e)
{
    if (!e)
        return 0;
    return e->op == E_AND ? count_terms(e->a) + count_terms(e->b) : 1;
}

/* The first FROM item at which every value term e reads is in the row,
 * -1 if it reads none (a constant). A column of item k is there from item
 * k's join on (item 0's from its scan). Item 0's rowid is the exception:
 * below the first join the row is table 0's own, whose rowid is not in a
 * slot, so a term that reads it waits for item 1. */
static int last_table(Expr *e)
{
    if (!e)
        return -1;
    if (e->op == E_COLUMN)
        return e->tab == 0 && e->tcol == TCOL_ROWID ? 1 : e->tab;
    int k = last_table(e->a);
    int kb = last_table(e->b), kc = last_table(e->c);
    if (kb > k)
        k = kb;
    if (kc > k)
        k = kc;
    for (int i = 0; i < e->nlist; i++) {
        int kl = last_table(e->list[i]);
        if (kl > k)
            k = kl;
    }
    return k;
}

/* The AND of terms[0..n) whose last_table() is level (a constant counts
 * as 0), built in the statement arena; NULL if there are none. */
static Expr *terms_at(Db *db, Expr **terms, int n, int level)
{
    Expr *and = NULL;
    for (int i = 0; i < n; i++) {
        int k = last_table(terms[i]);
        if ((k < 0 ? 0 : k) != level)
            continue;
        if (!and) {
            and = terms[i];
            continue;
        }
        Expr *e = arena_alloc(&db->stmt, sizeof *e);
        e->op = E_AND;
        e->col = e->aff = -1;
        e->a = and;
        e->b = terms[i];
        and = e;
    }
    return and;
}

/* Returns the scan of FROM item it with access acc, its detail naming the
 * alias too (EXPLAIN shows which side of a self-join is which); NULL if a
 * bound cannot be evaluated. */
static Op *item_scan(Db *db, FromItem *it, Access *acc)
{
    Op *op = op_scan(db, it->t, acc);
    if (op && it->alias && acc->kind == ACCESS_SCAN) {
        size_t n = strlen(it->t->name) + strlen(it->alias) + 8;
        char *d = arena_alloc(&db->stmt, n);
        snprintf(d, n, "%s AS %s", it->t->name, it->alias);
        op->detail = d;
    }
    return op;
}

/* Builds the operator tree for the query q. With one table it is
 * plan_query()'s plan, exactly as before joins came. A join is planned
 * left-deep, in the order the tables are written: a scan of item 0, then
 * for each later item a Join with a scan of it, each condition checked as
 * soon as the row holds every table it names; then a Sort for ORDER BY
 * (always: the planner does not know a join's order), then LIMIT/OFFSET. */
int plan_select(Db *db, Query *q, Plan *plan)
{
    Stmt *s = q->s;
    Scope *sc = &q->scope;
    if (sc->nfrom <= 1) {
        if (plan_query(db, sc->nfrom ? sc->from[0].t : NULL, s->where, s->order, s->norder, s->limit, s->offset,
                       plan) < 0)
            return -1;
        plan->q = q;
        return 0;
    }
    memset(plan, 0, sizeof *plan);
    plan->q = q;
    plan->jacc = arena_alloc(&db->stmt, (size_t)sc->nfrom * sizeof(Access));
    /* Every condition: the terms ANDed in WHERE and in every ON. */
    int nterms = count_terms(s->where);
    for (int k = 0; k < sc->nfrom; k++)
        nterms += count_terms(sc->from[k].on);
    Expr **terms = arena_alloc(&db->stmt, (size_t)(nterms + 1) * sizeof(Expr *));
    int n = conjuncts(s->where, terms, 0, nterms);
    for (int k = 0; k < sc->nfrom; k++)
        n = conjuncts(sc->from[k].on, terms, n, nterms);
    Op *op = NULL;
    // @build 08.01 where each condition is checked
    // An inner join's ON means what WHERE means, so both are one list of
    // terms, and each term is checked as soon as it can be: in a Filter
    // right above the operator that brings the last table it names
    // (terms_at). Item 0 is read the way its own terms allow
    // (choose_access, as for one table); every later item is scanned
    // whole, once for each row the join below it hands up, and joined on.
    Expr *here = terms_at(db, terms, n, 0);
    if (choose_access(sc->from[0].t, here, &plan->jacc[0]) < 0)
        return -1;
    if (!(op = item_scan(db, &sc->from[0], &plan->jacc[0])))
        return -1;
    if (here)
        op = op_filter(db, op, here);
    for (int k = 1; k < sc->nfrom; k++) {
        FromItem *it = &sc->from[k];
        plan->jacc[k].kind = ACCESS_SCAN;
        Op *inner = item_scan(db, it, &plan->jacc[k]);
        if (!inner) {
            op_close(op);
            return -1;
        }
        op = op_join(db, op, inner, it, k == 1 ? sc->from[0].t : NULL, it->base + it->t->ncols + 1);
        if ((here = terms_at(db, terms, n, k)))
            op = op_filter(db, op, here);
    }
    // @end
    if (s->norder) {
        plan->sorted = 1;
        op = op_sort(db, op, s->order, s->norder);
    }
    if (s->limit) {
        i64 l, o = 0;
        if (const_int(db, s->limit, &l) < 0 || (s->offset && const_int(db, s->offset, &o) < 0)) {
            op_close(op);
            return -1;
        }
        op = op_limit(db, op, l, o < 0 ? 0 : o);
    }
    plan->root = op;
    return 0;
}
// @end

/* ------------------------------------------------------------ EXPLAIN */

// @from 05.03
/* Prints the plan in the format of sqlite3's EXPLAIN QUERY PLAN. */
void explain_query_plan(Db *db, Stmt *s, Table *t, Plan *plan)
{
    (void)s;
    // @from 08.01
    if (plan->q && plan->q->scope.nfrom > 1) {
        explain_join_plan(db, plan);
        return;
    }
    // @end
    char lines[2][300];
    int n = 0;
    Access *a = &plan->acc;
    if (!t) {
        snprintf(lines[n++], sizeof lines[0], "SCAN CONSTANT ROW");
    } else if (a->kind == ACCESS_SCAN) {
        snprintf(lines[n++], sizeof lines[0], "SCAN %s", t->name);
    } else {
        const char *col = "rowid";
        char how[200];
        if (a->kind == ACCESS_INDEX_EQ || a->kind == ACCESS_INDEX_RANGE) {
            col = t->cols[a->index->cols[0]].name;
            snprintf(how, sizeof how, "INDEX %s", a->index->name);
        } else {
            snprintf(how, sizeof how, "INTEGER PRIMARY KEY");
        }
        char cond[200];
        if (a->kind == ACCESS_ROWID_EQ || a->kind == ACCESS_INDEX_EQ)
            snprintf(cond, sizeof cond, "%s=?", col);
        else if (a->lo && a->hi)
            snprintf(cond, sizeof cond, "%s>? AND %s<?", col, col);
        else
            snprintf(cond, sizeof cond, "%s%s?", col, a->lo ? ">" : "<");
        snprintf(lines[n++], sizeof lines[0], "SEARCH %s USING %s (%s)", t->name, how, cond);
    }
    if (plan->sorted)
        snprintf(lines[n++], sizeof lines[0], "USE TEMP B-TREE FOR ORDER BY");
    fprintf(db->out, "QUERY PLAN\n");
    for (int i = 0; i < n; i++)
        fprintf(db->out, "%s%s\n", i == n - 1 ? "`--" : "|--", lines[i]);
}
// @end

// @from 08.01
/* Writes into out sqlite3's EXPLAIN QUERY PLAN line for reading table t,
 * named name in the query, the way a says: SCAN, or SEARCH with the index
 * and the condition it answers. */
static void access_line(char *out, size_t n, const char *name, Table *t, Access *a)
{
    if (a->kind == ACCESS_SCAN) {
        snprintf(out, n, "SCAN %s", name);
        return;
    }
    const char *col = "rowid";
    char how[200], cond[200];
    if (a->kind == ACCESS_INDEX_EQ || a->kind == ACCESS_INDEX_RANGE) {
        col = t->cols[a->index->cols[0]].name;
        snprintf(how, sizeof how, "INDEX %s", a->index->name);
    } else {
        snprintf(how, sizeof how, "INTEGER PRIMARY KEY");
    }
    if (a->kind == ACCESS_ROWID_EQ || a->kind == ACCESS_INDEX_EQ)
        snprintf(cond, sizeof cond, "%s=?", col);
    else if (a->lo && a->hi)
        snprintf(cond, sizeof cond, "%s>? AND %s<?", col, col);
    else
        snprintf(cond, sizeof cond, "%s%s?", col, a->lo ? ">" : "<");
    snprintf(out, n, "SEARCH %s USING %s (%s)", name, how, cond);
}

/* EXPLAIN QUERY PLAN of a join, in sqlite3's format: one line per FROM
 * item, outer loop first, each named by its alias if it has one, then the
 * sort if there is one. */
void explain_join_plan(Db *db, Plan *plan)
{
    Scope *sc = &plan->q->scope;
    char line[300];
    fprintf(db->out, "QUERY PLAN\n");
    for (int k = 0; k < sc->nfrom; k++) {
        FromItem *it = &sc->from[k];
        access_line(line, sizeof line, it->alias ? it->alias : it->t->name, it->t, &plan->jacc[k]);
        fprintf(db->out, "%s%s\n", k == sc->nfrom - 1 && !plan->sorted ? "`--" : "|--", line);
    }
    if (plan->sorted)
        fprintf(db->out, "`--USE TEMP B-TREE FOR ORDER BY\n");
}

/* Prints op and the operators under it, depth levels in: a join's two
 * inputs come under it, its outer side first. */
static void explain_op(Db *db, Op *op, int depth)
{
    for (; op; op = op->child, depth++) {
        fprintf(db->out, "%*s%s%s%s\n", 2 * depth, "", op->name, op->detail ? " " : "",
                op->detail ? op->detail : "");
        if (op->inner) {
            explain_op(db, op->child, depth + 1);
            explain_op(db, op->inner, depth + 1);
            return;
        }
    }
}
// @end

/* Prints this engine's own operator tree for EXPLAIN, outermost first. */
void explain_tree(Db *db, Stmt *s, Plan *plan)
{
    (void)s;
    // @from 08.01
    explain_op(db, plan->root, 0);
    // @else
    // int depth = 0;
    // for (Op *op = plan->root; op; op = op->child, depth++)
    //     fprintf(db->out, "%*s%s%s%s\n", 2 * depth, "", op->name, op->detail ? " " : "",
    //             op->detail ? op->detail : "");
    // @end
}
