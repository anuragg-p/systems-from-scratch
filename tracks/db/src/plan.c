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

/* ------------------------------------------------------------ EXPLAIN */

// @from 05.03
/* Prints the plan in the format of sqlite3's EXPLAIN QUERY PLAN. */
void explain_query_plan(Db *db, Stmt *s, Table *t, Plan *plan)
{
    (void)s;
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

/* Prints this engine's own operator tree for EXPLAIN, outermost first. */
void explain_tree(Db *db, Stmt *s, Plan *plan)
{
    (void)s;
    int depth = 0;
    for (Op *op = plan->root; op; op = op->child, depth++)
        fprintf(db->out, "%*s%s%s%s\n", 2 * depth, "", op->name, op->detail ? " " : "",
                op->detail ? op->detail : "");
}
