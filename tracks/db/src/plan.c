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
 * A LEFT JOIN's ON stays in its join, where it decides what matches; @from 08.02
 * WHERE is checked on the rows the join hands up. @from 08.02
 * An inner table whose column a condition sets equal to a value from @from 08.03
 * the tables before it is looked up, by rowid or an index, not scanned. @from 08.03
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
    // @from 08.06
    if (e->depth)
        return 0;        /* a column of a query outside: a constant here */
    // @end
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

// @from 08.06
/* True if a lookup of v in column col (or ROWID) finds every row for which
 * comparing col with v holds. The lookup gives v col's affinity
 * (bound_value()); the comparison gives each side the affinity the pair
 * calls for (eval_compare()). For v with no affinity, as any constant, that
 * is col's, and the two agree. From 08.06 v can be a name from the query
 * outside or a scalar subquery, which have their column's affinity, and
 * then they differ: when v's is numeric and col's is not ('5' = 5 holds
 * for a TEXT column, but a lookup of 5 finds no '5'), and when col's is
 * TEXT and v's BLOB (the comparison keeps v's 5 a number, the lookup makes
 * it '5'). Such a term is still checked on every row; it does not choose
 * the rows. v NULL: nothing to compare with. */
static int same_values(Table *t, int col, Expr *v)
{
    int aff = col == ROWID ? AFF_INTEGER : t->cols[col].affinity;
    if (!v || v->aff < 0 || aff == AFF_INTEGER || aff == AFF_REAL || aff == AFF_NUMERIC)
        return 1;
    if (v->aff == AFF_INTEGER || v->aff == AFF_REAL || v->aff == AFF_NUMERIC)
        return 0;
    return !(aff == AFF_TEXT && v->aff == AFF_BLOB);
}
// @end

/* Collects into b what terms[0..n) say about column col (or ROWID).
 * Comparisons written constant-first are flipped so the column is always
 * on the left. */
static void find_bounds(Table *t, Expr **terms, int n, int col, Bounds *b)
{
    memset(b, 0, sizeof *b);
    for (int i = 0; i < n; i++) {
        Expr *e = terms[i];
        // @from 08.06
        if (!same_values(t, col, e->a) || !same_values(t, col, e->b) || !same_values(t, col, e->c))
            continue;    /* still checked on every row, but it does not choose the rows */
        // @end
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

// @from 08.06
static int sub_reads(Expr *e);
// @end

/* The first FROM item at which every value term e reads is in the row,
 * -1 if it reads none (a constant). A column of item k is there from item
 * k's join on (item 0's from its scan). Item 0's rowid is the exception:
 * below the first join the row is table 0's own, whose rowid is not in a
 * slot, so a term that reads it waits for item 1. */
static int last_table(Expr *e)
{
    if (!e)
        return -1;
    // @from 08.06
    if (e->depth)
        return -1;       /* a name from the query outside: a constant here */
    if (e->sub) {        /* a subquery: the items of this query its names read */
        int k = last_table(e->a), ks = sub_reads(e);
        return ks > k ? ks : k;
    }
    // @end
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

// @from 08.06
static int query_reads(Query *q, int d);

/* last_table() of e for the query d levels out from e's own: the items of
 * that query its names with depth d read (item 0's rowid counting as 1, as
 * there), through subqueries inside it too; -1 for none. */
static int reads_at(Expr *e, int d)
{
    if (!e)
        return -1;
    if (e->op == E_COLUMN || e->op == E_ROWID) {
        if (e->depth != d)
            return -1;   /* a name of a query nearer, or further out */
        return e->op == E_COLUMN && e->tab == 0 && e->tcol == TCOL_ROWID ? 1 : e->tab;
    }
    int k = reads_at(e->a, d);
    int kb = reads_at(e->b, d), kc = reads_at(e->c, d);
    k = kb > k ? kb : k;
    k = kc > k ? kc : k;
    for (int i = 0; i < e->nlist; i++) {
        int kl = reads_at(e->list[i], d);
        k = kl > k ? kl : k;
    }
    if (e->sub) {
        int ks = query_reads(e->q, d + 1);
        k = ks > k ? ks : k;
    }
    return k;
}

/* reads_at() of every expression of the query q: its result columns, WHERE,
 * ONs, ORDER BY, GROUP BY and HAVING (LIMIT and OFFSET can name nothing). */
static int query_reads(Query *q, int d)
{
    Stmt *s = q->s;
    int k = reads_at(s->where, d);
    for (int i = 0; i < q->ncols; i++) {
        int kc = reads_at(q->cols[i], d);
        k = kc > k ? kc : k;
    }
    for (int i = 0; i < s->nfrom; i++) {
        int ko = reads_at(s->from[i].on, d);
        k = ko > k ? ko : k;
    }
    for (int i = 0; i < s->norder; i++) {
        int ko = reads_at(s->order[i].e, d);
        k = ko > k ? ko : k;
    }
    for (int i = 0; i < s->ngroup; i++) {
        int kg = reads_at(s->group[i], d);
        k = kg > k ? kg : k;
    }
    int kh = reads_at(s->having, d);
    return kh > k ? kh : k;
}

/* The items of the query subquery e stands in that its SELECT reads (its
 * names one level out, and two levels out from a subquery inside it, ...),
 * as last_table() counts them; -1 if none: it is a constant there. This is
 * how sqlite3 checks an ON clause too (select.c, selectCheckOnClausesExpr
 * walks into the subqueries of the ON and finds each column's FROM clause
 * by its cursor). */
static int sub_reads(Expr *e)
{
    return query_reads(e->q, 1);
}
// @end

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

/* Returns the scan of FROM item it with access acc; NULL if a bound cannot
 * be evaluated. A full scan's detail names the alias too ("Scan orders AS
 * o"), so EXPLAIN tells the sides of a self-join apart when both are
 * scanned; a lookup or a range keeps op_scan()'s detail, which names only
 * the table ("Rowid lookup orders rowid = ?"). */
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

// @from 08.03
/* The highest FROM item whose columns (or rowid) e reads, -1 if none. A
 * lookup key for item k must read only items before k: they are all in the
 * join's row, table 0's rowid too, when the inner side starts again. */
static int key_item(Expr *e)
{
    if (!e)
        return -1;
    // @from 08.06
    if (e->depth)
        return -1;       /* a name from the query outside: a constant here */
    if (e->sub) {        /* a subquery reads the items its names read */
        int ka = key_item(e->a), ks = sub_reads(e);
        return ks > ka ? ks : ka;
    }
    // @end
    int k = e->op == E_COLUMN ? e->tab : -1;
    int ka = key_item(e->a), kb = key_item(e->b), kc = key_item(e->c);
    k = ka > k ? ka : k;
    k = kb > k ? kb : k;
    k = kc > k ? kc : k;
    for (int i = 0; i < e->nlist; i++) {
        int kl = key_item(e->list[i]);
        k = kl > k ? kl : k;
    }
    return k;
}

/* If term is column = key, with the column col of FROM item k (TCOL_ROWID:
 * the rowid, or the INTEGER PRIMARY KEY of t, item k's table) and a key that
 * reads only items before k, either way round, returns the key; else NULL. */
static Expr *join_key(Table *t, Expr *term, int k, int col)
{
    if (term->op != E_EQ)
        return NULL;
    for (int side = 0; side < 2; side++) {
        Expr *c = side ? term->b : term->a, *key = side ? term->a : term->b;
        // @from 08.06
        if (c->op != E_COLUMN || c->depth || c->tab != k || key_item(key) >= k)
            continue;    /* (a column of a query outside is a constant, not item k's) */
        // @else
        // if (c->op != E_COLUMN || c->tab != k || key_item(key) >= k)
        //     continue;
        // @end
        if (c->tcol == col || (col == TCOL_ROWID && t->rowid_col >= 0 && c->tcol == t->rowid_col))
            return key;
    }
    return NULL;
}

/* Whether an index on a column of affinity aff can answer column = key: it
 * can only if comparing the two leaves the column's stored values as they
 * are. A numeric column always can (the key is what gets converted). A TEXT
 * or BLOB column cannot when the key is a column of numeric affinity: the
 * comparison would then turn the column's values into numbers ('1.0' and
 * ' 1' equal 1), which no lookup of one key finds. This is sqlite3's
 * sqlite3IndexAffinityOk() (expr.c) on SQLite's comparison affinity, as
 * eval_compare() applies it. */
static int index_affinity_ok(int aff, Expr *key)
{
    if (aff == AFF_INTEGER || aff == AFF_REAL || aff == AFF_NUMERIC)
        return 1;
    return key->aff != AFF_INTEGER && key->aff != AFF_REAL && key->aff != AFF_NUMERIC;
}

/* Decides how FROM item k (k >= 1) of the join q is read for each row the
 * join below it hands up, and fills *acc. It looks for a term column = key
 * whose column is item k's and whose key reads only the items before k (or
 * nothing), among item k's own ON if it is a LEFT JOIN (whose rows only its
 * ON may narrow), else among terms[0..nterms), the WHERE and inner-join ON
 * terms. The first rule that applies wins:
 *   1. the column is the rowid or the INTEGER PRIMARY KEY   ACCESS_ROWID_EQ
 *   2. the column is the first column of an index, and      ACCESS_INDEX_EQ
 *      index_affinity_ok()
 *   3. none of these                                         ACCESS_SCAN
 * The key goes in acc->lo and acc->hi; scan_rebind() evaluates it for each
 * outer row. The term itself is still checked (in its Filter, or in the
 * LEFT JOIN's ON): the lookup only narrows what is read. Always returns 0. */
int choose_join_access(Query *q, int k, Expr **terms, int nterms, Access *acc)
{
    FromItem *it = &q->scope.from[k];
    Table *t = it->t;
    Expr *own[64], *key = NULL;
    memset(acc, 0, sizeof *acc);
    acc->kind = ACCESS_SCAN;
    // @build 08.03 choose how to read the inner table
    // A LEFT JOIN item looks only at the terms of its own ON (conjuncts()
    // into own). First the rowid: any term rowid = key (join_key() with
    // TCOL_ROWID also takes the INTEGER PRIMARY KEY) makes it a rowid
    // lookup. Then each index in turn, by its first column: a term on that
    // column whose key index_affinity_ok() allows makes it an index
    // lookup. Set kind, index, lo = hi = the key, both bounds inclusive.
    if (it->left) {
        nterms = conjuncts(it->on, own, 0, 64);
        terms = own;
    }
    for (int i = 0; i < nterms && !key; i++)
        key = join_key(t, terms[i], k, TCOL_ROWID);
    if (key) {
        acc->kind = ACCESS_ROWID_EQ;
    } else {
        for (Index *ix = t->indexes; ix && !key; ix = ix->next) {
            for (int i = 0; i < nterms && !key; i++) {
                key = join_key(t, terms[i], k, ix->cols[0]);
                if (key && !index_affinity_ok(t->cols[ix->cols[0]].affinity, key))
                    key = NULL;
            }
            if (key) {
                acc->kind = ACCESS_INDEX_EQ;
                acc->index = ix;
            }
        }
    }
    if (key) {
        acc->lo = acc->hi = key;
        acc->lo_incl = acc->hi_incl = 1;
    }
    return 0;
    // @end
}
// @end

// @from 08.04
// @from 08.05
/* Puts on top of op, which hands up the rows of q's FROM that pass WHERE,
 * the rest of the query: for an aggregate query the Aggregate (over a
 * Sort on the GROUP BY terms, which makes each group a run of rows, and
 * under a Filter for HAVING); a Distinct for SELECT DISTINCT; then a Sort
 * for ORDER BY (always, but for the one row of an aggregate query without
 * GROUP BY: the order the rows come in is not known), then LIMIT/OFFSET.
 * Sets plan->root; returns 0, or -1 with the error set. */
// @else
// /* Puts on top of op, which hands up the rows of q's FROM that pass WHERE,
//  * the rest of the query: for an aggregate query the Aggregate, whose one
//  * row needs no sort; for any other a Sort for ORDER BY (always: the order
//  * the rows come in is not known); then LIMIT/OFFSET. Sets plan->root;
//  * returns 0, or -1 with the error set. */
// @end
static int plan_top(Db *db, Query *q, Plan *plan, Op *op)
{
    Stmt *s = q->s;
    if (q->aggregate) {
        // @from 08.05
        if (s->ngroup) {
            /* Ascending, unless ORDER BY has as many terms: then each term
             * takes the direction of the ORDER BY term in its place, as in
             * sqlite3 (select.c, sqlite3CopySortOrder). It decides the order
             * of the rows that ORDER BY finds equal. */
            OrderTerm *by = arena_alloc(&db->stmt, (size_t)s->ngroup * sizeof(OrderTerm));
            for (int j = 0; j < s->ngroup; j++) {
                by[j].e = s->group[j];
                by[j].desc = s->norder == s->ngroup && s->order[j].desc;
            }
            op = op_sort(db, op, by, s->ngroup);
        }
        // @end
        op = op_aggregate(db, op, q);
        // @from 08.05
        if (s->having)
            op = op_filter(db, op, s->having);
        // @end
    }
    // @from 08.05
    if (s->distinct)
        op = op_distinct(db, op, q->cols, q->ncols);
    // @end
    /* An aggregate query without GROUP BY has one row, which needs no
     * sort: sqlite3 drops its ORDER BY too (select.c, sSort.pOrderBy = 0). */
    // @from 08.05
    if (s->norder && !(q->aggregate && !s->ngroup)) {
    // @else
    // if (s->norder && !q->aggregate) {
    // @end
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

// @from 08.04
/* Builds the operator tree for the query q. A query of one table that is
 * no more than the core's (no aggregate, GROUP BY or DISTINCT) gets
 * plan_query()'s plan, exactly as before joins came; any other query of
 * one table gets the scan and filter of that plan, with the rest on top
 * (plan_top). A join is planned left-deep, in the order the tables are
 * written: a scan of item 0, then for each later item a Join with a scan
 * of it, each condition checked as soon as the row holds every table it
 * names; then the rest (plan_top). */
// @else
// /* Builds the operator tree for the query q. With one table it is
//  * plan_query()'s plan, exactly as before joins came. A join is planned
//  * left-deep, in the order the tables are written: a scan of item 0, then
//  * for each later item a Join with a scan of it, each condition checked as
//  * soon as the row holds every table it names; then a Sort for ORDER BY
//  * (always: the planner does not know a join's order), then LIMIT/OFFSET. */
// @end
int plan_select(Db *db, Query *q, Plan *plan)
{
    Stmt *s = q->s;
    Scope *sc = &q->scope;
    // @from 08.04
    // @from 08.05
    if (sc->nfrom <= 1 && !q->aggregate && !s->distinct) {
    // @else
    // if (sc->nfrom <= 1 && !q->aggregate) {
    // @end
    // @else
    // if (sc->nfrom <= 1) {
    // @end
        if (plan_query(db, sc->nfrom ? sc->from[0].t : NULL, s->where, s->order, s->norder, s->limit, s->offset,
                       plan) < 0)
            return -1;
        plan->q = q;
        return 0;
    }
    // @from 08.04
    if (sc->nfrom <= 1) {
        if (plan_query(db, sc->nfrom ? sc->from[0].t : NULL, s->where, NULL, 0, NULL, NULL, plan) < 0)
            return -1;
        plan->q = q;
        return plan_top(db, q, plan, plan->root);
    }
    // @end
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
        // @from 08.02
        if (!sc->from[k].left)          /* a LEFT JOIN checks its own ON (left_join()) */
            n = conjuncts(sc->from[k].on, terms, n, nterms);
        // @else
        // n = conjuncts(sc->from[k].on, terms, n, nterms);
        // @end
    Op *op = NULL;
    // @build 08.01 where each condition is checked
    // An inner join's ON means what WHERE means, so both are one list of
    // terms, and each term is checked as soon as it can be: in a Filter
    // right above the operator that brings the last table it names
    // (terms_at). Item 0 is read the way its own terms allow
    // (choose_access, as for one table); every later item is scanned
    // whole, once for each row the join below it hands up, and joined on.
    // @from 08.02
    for (int k = 1; k < sc->nfrom; k++)
        if (sc->from[k].left && last_table(sc->from[k].on) > k)
            return err("ON clause references tables to its right");
    // @end
    Expr *here = terms_at(db, terms, n, 0);
    if (choose_access(sc->from[0].t, here, &plan->jacc[0]) < 0)
        return -1;
    if (!(op = item_scan(db, &sc->from[0], &plan->jacc[0])))
        return -1;
    if (here)
        op = op_filter(db, op, here);
    for (int k = 1; k < sc->nfrom; k++) {
        FromItem *it = &sc->from[k];
        // @from 08.03
        choose_join_access(q, k, terms, n, &plan->jacc[k]);
        Access unbound = plan->jacc[k];     /* op_scan() must not evaluate the key */
        unbound.lo = unbound.hi = NULL;
        Op *inner = item_scan(db, it, &unbound);
        // @else
        // plan->jacc[k].kind = ACCESS_SCAN;
        // Op *inner = item_scan(db, it, &plan->jacc[k]);
        // @end
        if (!inner) {
            op_close(op);
            return -1;
        }
        inner->acc = plan->jacc[k];  // @from 08.03
        op = op_join(db, op, inner, it, k == 1 ? sc->from[0].t : NULL, it->base + it->t->ncols + 1);
        if ((here = terms_at(db, terms, n, k)))
            op = op_filter(db, op, here);
    }
    // @end
    // @from 08.04
    return plan_top(db, q, plan, op);
    // @else
    // if (s->norder) {
    //     plan->sorted = 1;
    //     op = op_sort(db, op, s->order, s->norder);
    // }
    // if (s->limit) {
    //     i64 l, o = 0;
    //     if (const_int(db, s->limit, &l) < 0 || (s->offset && const_int(db, s->offset, &o) < 0)) {
    //         op_close(op);
    //         return -1;
    //     }
    //     op = op_limit(db, op, l, o < 0 ? 0 : o);
    // }
    // plan->root = op;
    // return 0;
    // @end
}
// @end

/* ------------------------------------------------------------ EXPLAIN */

// @from 05.03
/* Prints the plan in the format of sqlite3's EXPLAIN QUERY PLAN. */
void explain_query_plan(Db *db, Stmt *s, Table *t, Plan *plan)
{
    (void)s;
    // @from 08.04
    // @from 08.05
    if (plan->q && (plan->q->aggregate || plan->q->s->distinct)) {
    // @else
    // if (plan->q && plan->q->aggregate) {
    // @end
        explain_select_plan(db, plan);
        return;
    }
    // @end
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
        // @from 08.02
        fprintf(db->out, "%s%s%s\n", k == sc->nfrom - 1 && !plan->sorted ? "`--" : "|--", line,
                it->left ? " LEFT-JOIN" : "");
        // @else
        // fprintf(db->out, "%s%s\n", k == sc->nfrom - 1 && !plan->sorted ? "`--" : "|--", line);
        // @end
    }
    if (plan->sorted)
        fprintf(db->out, "`--USE TEMP B-TREE FOR ORDER BY\n");
}

// @from 08.04
/* Prints EXPLAIN QUERY PLAN lines one behind: the line held is printed
 * when the next one comes, so that the last one can be told apart. */
static void plan_line(Db *db, char *held, size_t n, const char *line)
{
    if (held[0])
        fprintf(db->out, "|--%s\n", held);
    snprintf(held, n, "%s", line);
}

// @from 08.05
/* EXPLAIN QUERY PLAN of a query with aggregates or DISTINCT, in sqlite3's
 * words and order: with no GROUP BY, first a temporary B-tree for each
 * DISTINCT aggregate; a line per table of the FROM, named by its alias if
 * it has one; then the temporary B-trees of GROUP BY (and the DISTINCT
 * aggregates after it), of SELECT DISTINCT and of ORDER BY. */
// @else
// /* EXPLAIN QUERY PLAN of a query with aggregates, in sqlite3's words: a
//  * line per table of the FROM, named by its alias if it has one. */
// @end
void explain_select_plan(Db *db, Plan *plan)
{
    Query *q = plan->q;
    Scope *sc = &q->scope;
    char held[300] = "", line[300];
    fprintf(db->out, "QUERY PLAN\n");
    // @from 08.05
    static const char *fn_names[] = {"count", "count", "sum", "total", "avg", "min", "max"};
    Stmt *s = q->s;
    for (int k = 0; k < q->naggs && !s->ngroup; k++) {
        if (q->aggs[k].distinct) {
            snprintf(line, sizeof line, "USE TEMP B-TREE FOR %s(DISTINCT)", fn_names[q->aggs[k].fn]);
            plan_line(db, held, sizeof held, line);
        }
    }
    // @end
    if (sc->nfrom == 0)
        plan_line(db, held, sizeof held, "SCAN CONSTANT ROW");
    for (int k = 0; k < sc->nfrom; k++) {
        FromItem *it = &sc->from[k];
        access_line(line, sizeof line, it->alias ? it->alias : it->t->name, it->t,
                    sc->nfrom == 1 ? &plan->acc : &plan->jacc[k]);
        if (it->left)
            strncat(line, " LEFT-JOIN", sizeof line - strlen(line) - 1);
        plan_line(db, held, sizeof held, line);
    }
    // @from 08.05
    if (s->ngroup) {
        plan_line(db, held, sizeof held, "USE TEMP B-TREE FOR GROUP BY");
        for (int k = 0; k < q->naggs; k++) {
            if (q->aggs[k].distinct) {
                snprintf(line, sizeof line, "USE TEMP B-TREE FOR %s(DISTINCT)", fn_names[q->aggs[k].fn]);
                plan_line(db, held, sizeof held, line);
            }
        }
    }
    if (s->distinct)
        plan_line(db, held, sizeof held, "USE TEMP B-TREE FOR DISTINCT");
    // @end
    if (plan->sorted)
        plan_line(db, held, sizeof held, "USE TEMP B-TREE FOR ORDER BY");
    fprintf(db->out, "`--%s\n", held);
}
// @end

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
