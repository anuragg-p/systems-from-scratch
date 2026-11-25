// @from 04.01
/*
 * exec.c - running statements.
 *
 * A query runs as a tree of operators, each with a next() that hands back
 * one row at a time, pulling rows from its child as it needs them (the
 * "Volcano" or iterator model):
 *
 *   Limit          stops after n rows @from 04.03
 *    Sort          pulls every row, sorts them, hands them out in order @from 04.03
 *     Filter       passes on only the rows WHERE is true for @from 04.02
 *      Scan        reads the table's B-tree
 *                  (or a range of it, or an index) @from 05.02
 *
 * No operator knows what is above or below it, so they combine freely,
 * and nothing is materialised unless an operator needs every row at once.
 * UPDATE and DELETE use the same operators to find their rows. @from 04.04
 */
// @else
// /*
//  * exec.c - running statements: each one the parser hands over is carried
//  * out here, and an error stops the rest of the input.
//  */
// @end
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "db.h"

// @from 04.01
/* Allocates a zeroed operator with its name (shown by EXPLAIN) and next(). */
static Op *new_op(Db *db, const char *name, int (*next)(Op *, Row **))
{
    Op *op = xcalloc(1, sizeof *op);
    op->db = db;
    op->name = name;
    op->next = next;
    return op;
}

// @from 08.04
static void aggregate_free(Op *op);
// @end
// @from 08.05
struct Set;
static void set_free(struct Set *s);
// @end

/* Frees op and every operator below it, with the cursors and buffers each
 * owns. */
void op_close(Op *op)
{
    while (op) {
        Op *child = op->child;
        cursor_close(&op->cur);
        cursor_close(&op->icur);  // @from 05.02
        buf_free(&op->key);  // @from 05.02
        // @from 08.04
        if (op->q)                      /* an Aggregate: its rows, and its aggregates' state */
            aggregate_free(op);
        // @end
        // @from 08.05
        set_free(op->set);              /* a Distinct's set of rows seen */
        free(op->dvals);
        // @end
        // @from 08.01
        if (op->table || op->inner)     /* a scan and a join allocate the row they hand out */
            free(op->row.cols);
        op_close(op->inner);
        if (op->hold.head) {
            arena_reset(&op->hold);
            free(op->hold.head);
        }
        // @else
        // if (op->table)              /* only a scan allocates the row it hands out */
        //     free(op->row.cols);
        // @end
        // @from 04.03
        free(op->rows);
        if (op->sort_arena.head) {
            arena_reset(&op->sort_arena);
            free(op->sort_arena.head);
        }
        // @end
        free(op);
        op = child;
    }
}

/* ------------------------------------------------------------ reading rows (04.01) */

/* Decodes the row at cursor c into row, which has room for t->ncols values:
 * one value per column of t. The record may be shorter than the table
 * (the row predates an ALTER TABLE ADD COLUMN); the missing columns take
 * their DEFAULT. The INTEGER PRIMARY KEY column is stored as NULL in the
 * record because its value is the rowid, so it is filled in from c. A
 * malformed record is fatal: the file is corrupt. */
void decode_row(Table *t, Cursor *c, Row *row)
{
    // @build 04.01 decode a row
    int n = record_decode(c->payload, c->npayload, row->cols, t->ncols);
    if (n < 0)
        fatal("database is corrupt: bad record in table %s, rowid %lld", t->name, (long long)c->rowid);
    for (int i = n; i < t->ncols; i++)
        row->cols[i] = t->cols[i].dflt_value;
    /* sqlite3 stores a whole-number float in a REAL column as an integer,
     * to save space; it is still a float. */
    for (int i = 0; i < n && i < t->ncols; i++) {
        if (t->cols[i].affinity == AFF_REAL && row->cols[i].type == V_INT) {
            row->cols[i].r = (double)row->cols[i].i;
            row->cols[i].type = V_REAL;
        }
    }
    row->ncols = t->ncols;
    row->rowid = c->rowid;
    if (t->rowid_col >= 0) {
        Value *v = &row->cols[t->rowid_col];
        memset(v, 0, sizeof *v);
        v->type = V_INT;
        v->i = c->rowid;
    }
    // @end
}

/* Returns every row of the table, in rowid order. */
static int scan_next(Op *op, Row **out)
{
    // @build 04.01 the table scan
    int more = op->started ? cursor_next(&op->cur) : cursor_first(&op->cur);
    op->started = 1;
    if (!more)
        return 0;
    decode_row(op->table, &op->cur, &op->row);
    *out = &op->row;
    return 1;
    // @end
}

/* SELECT without FROM: yields one row with no columns. */
static int one_next(Op *op, Row **out)
{
    if (op->started)
        return 0;
    op->started = 1;
    *out = &op->row;
    return 1;
}

/* Yields no rows (used when the database file is empty). */
static int nothing_next(Op *op, Row **out)
{
    (void)op;
    (void)out;
    return 0;
}

/* Yields the rows whose rowid lies in [lo_i, hi_i]; has_lo and has_hi say
 * which ends are bounded. The scan seeks to the lower bound, then ends at
 * the first rowid past the upper one. done set before the first call
 * means the range is empty. */
static int rowid_range_next(Op *op, Row **out)
{
    // @build 05.02 a range of rowids
    if (op->done)
        return 0;
    int more;
    if (!op->started) {
        op->started = 1;
        more = op->has_lo ? cursor_seek_rowid(&op->cur, op->lo_i) : cursor_first(&op->cur);
    } else {
        more = cursor_next(&op->cur);
    }
    if (!more || (op->has_hi && op->cur.rowid > op->hi_i)) {
        op->done = 1;
        return 0;
    }
    decode_row(op->table, &op->cur, &op->row);
    *out = &op->row;
    return 1;
    // @end
}

/* Yields the rows whose indexed column lies between the bounds, in index
 * order. Each index entry is a record of the indexed values followed by
 * the rowid; the row itself is fetched from the table by that rowid. The
 * scan seeks to the first entry not below the lower bound (comparing only
 * the first field) and stops at the first one above the upper bound. An
 * entry whose row is missing means the index is corrupt. */
static int index_range_next(Op *op, Row **out)
{
    Index *ix = op->acc.index;
    Value key[9];
    // @build 05.02 an index range
    if (op->done)
        return 0;
    int more;
    if (!op->started) {
        op->started = 1;
        more = op->has_lo ? cursor_seek_key(&op->icur, op->key.p, (u32)op->key.n, 1, -1) : cursor_first(&op->icur);
    } else {
        more = cursor_next(&op->icur);
    }
    if (!more) {
        op->done = 1;
        return 0;
    }
    int n = record_decode(op->icur.payload, op->icur.npayload, key, ix->ncols + 1);
    if (n != ix->ncols + 1 || key[ix->ncols].type != V_INT)
        fatal("database is corrupt: bad entry in index %s", ix->name);
    if (op->has_hi && value_compare(&key[0], &op->hi) > 0) {
        op->done = 1;
        return 0;
    }
    i64 rowid = key[ix->ncols].i;
    if (!cursor_seek_rowid(&op->cur, rowid) || op->cur.rowid != rowid)
        fatal("database is corrupt: index %s points at row %lld, which is not there", ix->name, (long long)rowid);
    decode_row(op->table, &op->cur, &op->row);
    *out = &op->row;
    return 1;
    // @end
}

// @from 05.02
/* Evaluates a constant bound with the column's affinity applied, copying
 * text and blobs into the statement arena so they last across rows. */
static int bound_value(Db *db, Expr *e, int aff, Value *v)
{
    if (eval(db, e, NULL, v) < 0)
        return -1;
    apply_affinity(v, aff, &db->stmt);
    if (v->type == V_TEXT || v->type == V_BLOB)     /* keep it past this row */
        v->s = arena_strndup(&db->stmt, v->s, (size_t)v->n);
    return 0;
}

/* A rowid bound as an integer, widened to whole numbers (WHERE re-checks
 * every row, so a wider range is only slower, never wrong). Returns 0 for
 * no usable bound on that side, 1 for a bound in *out, -1 if no row can
 * match. */
static int rowid_bound(Value v, int upper, i64 *out)
{
    if (v.type == V_NULL)
        return -1;                      /* x < NULL is never true */
    if (v.type == V_TEXT || v.type == V_BLOB)
        return upper ? 0 : -1;          /* every integer sorts below text */
    if (v.type == V_INT) {
        *out = v.i;
        return 1;
    }
    double r = upper ? ceil(v.r) : floor(v.r);
    if (r >= 9223372036854775807.0)
        return upper ? 0 : -1;
    if (r <= -9223372036854775807.0)
        return upper ? -1 : 0;
    *out = (i64)r;
    return 1;
}
// @end

// @from 05.02
/* Returns the operator that reads table t the way acc says (t NULL: the
 * one-row source for SELECT without FROM), or NULL if a bound cannot be
 * evaluated. */
Op *op_scan(Db *db, Table *t, Access *acc)
// @else
// /* Returns the operator that reads every row of table t, in rowid order
//  * (t NULL: the one-row source for SELECT without FROM). */
// Op *op_scan(Db *db, Table *t)
// @end
{
    if (!t) {
        Op *op = new_op(db, "Constant row", one_next);
        return op;
    }
    Op *op = new_op(db, "Scan", scan_next);
    op->table = t;
    op->acc = *acc;  // @from 05.02
    op->row.cols = xcalloc((size_t)t->ncols + 1, sizeof(Value));
    cursor_open(&op->cur, &db->pager, t->root, 1);
    if (db->pager.npages == 0) {
        op->next = nothing_next;     /* an empty file: no tables at all */
        return op;
    }
    // @from 05.02
    Arena *a = &db->stmt;
    if (acc->kind == ACCESS_SCAN) {
        op->detail = t->name;
        return op;
    }
    if (acc->kind == ACCESS_ROWID_EQ || acc->kind == ACCESS_ROWID_RANGE) {
        op->name = acc->kind == ACCESS_ROWID_EQ ? "Rowid lookup" : "Rowid range";
        Value v;
        if (acc->lo) {
            if (bound_value(db, acc->lo, AFF_INTEGER, &v) < 0)
                goto fail;
            int r = rowid_bound(v, 0, &op->lo_i);
            if (r < 0)
                op->done = 1;
            op->has_lo = r > 0;
        }
        if (acc->hi) {
            if (bound_value(db, acc->hi, AFF_INTEGER, &v) < 0)
                goto fail;
            int r = rowid_bound(v, 1, &op->hi_i);
            if (r < 0)
                op->done = 1;
            op->has_hi = r > 0;
        }
        op->next = rowid_range_next;
        char *d = arena_alloc(a, 300);
        snprintf(d, 300, "%s rowid %s", t->name,
                 acc->kind == ACCESS_ROWID_EQ ? "= ?" : acc->lo && acc->hi ? "between ? and ?" : acc->lo ? "> ?" : "< ?");
        op->detail = d;
        return op;
    }
    Index *ix = acc->index;
    int aff = t->cols[ix->cols[0]].affinity;
    op->name = acc->kind == ACCESS_INDEX_EQ ? "Index lookup" : "Index range";
    cursor_open(&op->icur, &db->pager, ix->root, 0);
    if (acc->lo) {
        Value v;
        if (bound_value(db, acc->lo, aff, &v) < 0)
            goto fail;
        if (v.type == V_NULL)
            op->done = 1;
        record_build(&op->key, &v, 1);
        op->has_lo = 1;
    }
    if (acc->hi) {
        if (bound_value(db, acc->hi, aff, &op->hi) < 0)
            goto fail;
        if (op->hi.type == V_NULL)
            op->done = 1;
        op->has_hi = 1;
    }
    op->next = index_range_next;
    char *d = arena_alloc(a, 300);
    snprintf(d, 300, "%s using %s (%s %s)", t->name, ix->name, t->cols[ix->cols[0]].name,
             acc->kind == ACCESS_INDEX_EQ ? "= ?" : acc->lo && acc->hi ? "between ? and ?" : acc->lo ? "> ?" : "< ?");
    op->detail = d;
    return op;
fail:
    op_close(op);
    return NULL;
    // @else
    // op->detail = t->name;
    // return op;
    // @end
}

// @from 08.03
/* Starts a join's inner scan again for the outer row now in outer, the
 * join's row. A scan starts from its first row. A lookup (its key, acc.lo,
 * is an expression of the tables before this one) evaluates the key on
 * outer, with the inner column's affinity applied as bound_value() does,
 * and goes to the rows it finds: rowids between the key rounded down and
 * up (rowid_bound()), or index entries equal to it. A NULL key finds
 * nothing. Returns 0, or -1 if the key cannot be evaluated. */
int scan_rebind(Op *scan, Row *outer)
{
    Access *acc = &scan->acc;
    scan->started = scan->done = 0;
    if (acc->kind == ACCESS_SCAN)
        return 0;
    // @build 08.03 start the inner side for this outer row
    // Evaluate the key on the outer row. A rowid lookup: give it INTEGER
    // affinity and set both rowid bounds from it, as op_scan() does for a
    // constant (no possible rowid: done). An index lookup: give it the
    // indexed column's affinity; NULL is done; else build the key the
    // seek starts at, and decode hi, the last value to take, back from
    // that record, so neither points into the row arena, which a Filter
    // above may reset while this inner loop runs.
    Db *db = scan->db;
    Value v;
    if (eval(db, acc->lo, outer, &v) < 0)
        return -1;
    if (acc->kind == ACCESS_ROWID_EQ) {
        apply_affinity(&v, AFF_INTEGER, &db->rowa);
        int lo = rowid_bound(v, 0, &scan->lo_i), hi = rowid_bound(v, 1, &scan->hi_i);
        scan->done = lo < 0 || hi < 0;
        scan->has_lo = lo > 0;
        scan->has_hi = hi > 0;
        return 0;
    }
    apply_affinity(&v, scan->table->cols[acc->index->cols[0]].affinity, &db->rowa);
    if (v.type == V_NULL) {
        scan->done = 1;
        return 0;
    }
    scan->key.n = 0;
    record_build(&scan->key, &v, 1);
    record_decode(scan->key.p, (u32)scan->key.n, &scan->hi, 1);
    scan->has_lo = scan->has_hi = 1;
    return 0;
    // @end
}
// @end

// @from 04.02
/* ------------------------------------------------------------ Filter (04.02) */

/* Passes on only the rows for which the predicate is true; false and NULL
 * both drop the row. The row arena is reset for each dropped row, so
 * whatever evaluating it allocated does not pile up. */
static int filter_next(Op *op, Row **out)
{
    // @build 04.02 keep the rows WHERE is true for
    for (;;) {
        int rc = op->child->next(op->child, out);
        if (rc <= 0)
            return rc;
        Value v;
        if (eval(op->db, op->pred, *out, &v) < 0)
            return -1;
        if (value_truth(&v) == 1)
            return 1;
        arena_reset(&op->db->rowa);
    }
    // @end
}

Op *op_filter(Db *db, Op *child, Expr *pred)
{
    Op *op = new_op(db, "Filter", filter_next);
    op->child = child;
    op->pred = pred;
    op->detail = expr_text(&db->stmt, pred);
    return op;
}
// @end

// @from 04.03
/* ------------------------------------------------------------ Sort and Limit (04.03) */

/* One buffered row of a Sort: its values and ORDER BY keys are copies that
 * live in the operator's own arena. */
typedef struct SortRow {
    Value *keys;
    Value *cols;
    int ncols;
    i64 rowid;
    i64 seq;             /* arrival order: equal keys keep it */
} SortRow;

/* qsort() takes no context argument, so the terms sort_cmp() orders by are
 * passed in these statics. */
static OrderTerm *sort_terms;
static int sort_nterms;

/* Orders by each ORDER BY key in turn; rows equal on all keys keep their
 * arrival order, which makes the sort stable. */
static int sort_cmp(const void *pa, const void *pb)
{
    const SortRow *a = pa, *b = pb;
    for (int i = 0; i < sort_nterms; i++) {
        int c = value_compare(&a->keys[i], &b->keys[i]);
        if (c)
            return sort_terms[i].desc ? -c : c;
    }
    return a->seq < b->seq ? -1 : a->seq > b->seq;
}

/* Returns a copy of v whose text or blob bytes live in arena a. */
static Value keep(Arena *a, Value v)
{
    if ((v.type == V_TEXT || v.type == V_BLOB) && v.n > 0)
        v.s = arena_strndup(a, v.s, (size_t)v.n);
    return v;
}

/* A sort cannot hand out its first row before it has seen the last, so the
 * first call drains the child into op->rows (copying each row and its
 * keys into the operator's arena, since the child's buffers are reused)
 * and sorts them; later calls walk the sorted array. */
static int sort_next(Op *op, Row **out)
{
    if (!op->started) {
        op->started = 1;
        Db *db = op->db;
        // @build 04.03 sort the rows
        i64 cap = 0;
        Row *r;
        int rc;
        while ((rc = op->child->next(op->child, &r)) == 1) {
            if (op->nrows == cap) {
                cap = cap ? 2 * cap : 256;
                op->rows = xrealloc(op->rows, (size_t)cap * sizeof(SortRow));
            }
            SortRow *s = &op->rows[op->nrows];
            s->keys = arena_alloc(&op->sort_arena, (size_t)op->norder * sizeof(Value));
            s->cols = arena_alloc(&op->sort_arena, (size_t)(r->ncols + 1) * sizeof(Value));
            for (int i = 0; i < op->norder; i++) {
                Value v;
                if (eval(db, op->order[i].e, r, &v) < 0)
                    return -1;
                s->keys[i] = keep(&op->sort_arena, v);
            }
            for (int i = 0; i < r->ncols; i++)
                s->cols[i] = keep(&op->sort_arena, r->cols[i]);
            s->ncols = r->ncols;
            s->rowid = r->rowid;
            s->seq = op->nrows;
            op->nrows++;
            arena_reset(&db->rowa);
        }
        if (rc < 0)
            return -1;
        sort_terms = op->order;
        sort_nterms = op->norder;
        qsort(op->rows, (size_t)op->nrows, sizeof(SortRow), sort_cmp);
        // @end
    }
    if (op->pos >= op->nrows)
        return 0;
    SortRow *s = &op->rows[op->pos++];
    op->row.cols = s->cols;
    op->row.ncols = s->ncols;
    op->row.rowid = s->rowid;
    *out = &op->row;
    return 1;
}

Op *op_sort(Db *db, Op *child, OrderTerm *order, int norder)
{
    Op *op = new_op(db, "Sort", sort_next);
    op->child = child;
    op->order = order;
    op->norder = norder;
    Buf b = {0};
    buf_put(&b, "by ", 3);
    for (int i = 0; i < norder; i++) {
        const char *s = expr_text(&db->stmt, order[i].e);
        if (i)
            buf_put(&b, ", ", 2);
        buf_put(&b, s, strlen(s));
        if (order[i].desc)
            buf_put(&b, " DESC", 5);
    }
    op->detail = arena_strndup(&db->stmt, (const char *)b.p, b.n);
    buf_free(&b);
    return op;
}

/* Skips the first op->offset rows, then passes on at most op->limit (a
 * negative limit means no limit). Once the limit is reached the child is
 * not asked for another row. */
static int limit_next(Op *op, Row **out)
{
    // @build 04.03 LIMIT and OFFSET
    int rc;
    while (op->seen < op->offset) {
        rc = op->child->next(op->child, out);
        if (rc <= 0)
            return rc;
        op->seen++;
        arena_reset(&op->db->rowa);
    }
    if (op->limit >= 0 && op->seen - op->offset >= op->limit)
        return 0;
    rc = op->child->next(op->child, out);
    if (rc == 1)
        op->seen++;
    return rc;
    // @end
}

Op *op_limit(Db *db, Op *child, i64 limit, i64 offset)
{
    Op *op = new_op(db, "Limit", limit_next);
    op->child = child;
    op->limit = limit;
    op->offset = offset;
    char *d = arena_alloc(&db->stmt, 64);
    snprintf(d, 64, "%lld offset %lld", (long long)limit, (long long)offset);
    op->detail = d;
    return op;
}
// @end

// @from 08.01
/* ------------------------------------------------------------ Join (08.01) */

/* What a LEFT JOIN adds to the nested loop, called with an inner row in
 * the join's row (have_inner) or when the inner side has run out for the
 * outer row in hand. An inner row is a match only if the join's own ON is
 * true for it; the outer row remembers that it had one. When the inner
 * side runs out and nothing matched, the outer row still goes up, once,
 * with every slot of the inner table NULL. Returns 1 to hand the row up,
 * 0 not to, -1 if ON cannot be evaluated. */
static int left_join(Op *op, int have_inner)
{
    // @build 08.02 the row with no match
    // With an inner row: evaluate ON on the joined row (no ON: every
    // inner row matches). Not true (false or NULL): this pair is not a
    // row of the answer; reset the row arena, as a Filter does for a
    // dropped row, and say no. True: note the match and say yes.
    // Without one: if the outer row matched nothing, set the inner
    // table's slots, its columns and its rowid, to NULL and say yes:
    // WHERE and the joins above see that row like any other.
    if (have_inner) {
        if (op->on) {
            Value v;
            if (eval(op->db, op->on, &op->row, &v) < 0)
                return -1;
            if (value_truth(&v) != 1) {
                arena_reset(&op->db->rowa);
                return 0;
            }
        }
        op->matched = 1;
        return 1;
    }
    if (op->matched)
        return 0;
    for (int i = op->lwidth; i < op->row.ncols; i++)
        memset(&op->row.cols[i], 0, sizeof(Value));     /* V_NULL */
    return 1;
    // @end
}

/* The nested loop: for each row of the left side (the outer loop), every
 * row of the inner table, each pair handed up as one joined row. The row
 * holds the tables side by side: the left side's values in the first
 * lwidth slots, then the inner table's columns, then its rowid.
 *
 * The outer row is kept for the whole inner loop, across many calls to the
 * inner side's next() and many output rows, and the statement loop may
 * evict pages between output rows (pager_shrink): so its text and blobs
 * are copied into the operator's own arena (keep()), which is emptied when
 * the next outer row comes. The inner row is not kept: it is good until
 * the next call, as a scan's row is. */
static int join_next(Op *op, Row **out)
{
    // @build 08.01 the nested loop
    // With no outer row in hand, pull one from the left side (none left:
    // the join is done), copy its values into the first slots, and start
    // the inner side again from its first row. When the left side is table
    // 0's own scan (op->table), its rowid is in the row, not in a slot:
    // put it in the slot after its columns. Then pull an inner row; when
    // the inner side runs out, drop the outer row and go round. Otherwise
    // copy the inner row's values and rowid in and hand the row up.
    for (;;) {
        if (!op->have_outer) {
            Row *l;
            int rc = op->child->next(op->child, &l);
            if (rc <= 0)
                return rc;
            arena_reset(&op->hold);
            int n = op->table ? op->table->ncols : op->lwidth;
            for (int i = 0; i < n; i++)
                op->row.cols[i] = keep(&op->hold, l->cols[i]);
            if (op->table) {
                memset(&op->row.cols[n], 0, sizeof(Value));
                op->row.cols[n].type = V_INT;
                op->row.cols[n].i = l->rowid;
            }
            op->have_outer = 1;
            op->matched = 0;  // @from 08.02
            // @from 08.03
            if (scan_rebind(op->inner, &op->row) < 0)
                return -1;
            // @else
            // op->inner->started = 0;
            // @end
        }
        Row *r;
        int rc = op->inner->next(op->inner, &r);
        if (rc < 0)
            return -1;
        if (rc == 0) {
            op->have_outer = 0;
            // @from 08.02
            if (op->leftjoin && left_join(op, 0)) {
                *out = &op->row;
                return 1;
            }
            // @end
            continue;
        }
        Value *slot = op->row.cols + op->lwidth;
        for (int i = 0; i < r->ncols; i++)
            slot[i] = r->cols[i];
        memset(&slot[r->ncols], 0, sizeof(Value));
        slot[r->ncols].type = V_INT;
        slot[r->ncols].i = r->rowid;
        // @from 08.02
        if (op->leftjoin && (rc = left_join(op, 1)) <= 0) {
            if (rc < 0)
                return -1;
            continue;
        }
        // @end
        *out = &op->row;
        return 1;
    }
    // @end
}

// @from 08.02
/* Returns the Join of left (the outer loop) with inner, a scan of item's
 * table, which takes the slots from item->base on. Its rows are width
 * values. left_table is table 0 when left hands up table 0's own rows (the
 * first join), NULL when it hands up joined rows; it is kept in op->table.
 * For a LEFT JOIN item it is a Left join, which checks the item's ON
 * itself (left_join()). */
// @else
// /* Returns the Join of left (the outer loop) with inner, a scan of item's
//  * table, which takes the slots from item->base on. Its rows are width
//  * values. left_table is table 0 when left hands up table 0's own rows (the
//  * first join), NULL when it hands up joined rows; it is kept in op->table. */
// @end
Op *op_join(Db *db, Op *left, Op *inner, FromItem *item, Table *left_table, int width)
{
    Op *op = new_op(db, "Join", join_next);
    op->child = left;
    op->inner = inner;
    op->table = left_table;
    op->lwidth = item->base;
    op->row.cols = xcalloc((size_t)width, sizeof(Value));
    op->row.ncols = width;
    // @from 08.02
    if (item->left) {
        op->name = "Left join";
        op->leftjoin = 1;
        op->on = item->on;
        if (item->on) {
            const char *on = expr_text(&db->stmt, item->on);
            size_t n = strlen(on) + 4;
            char *d = arena_alloc(&db->stmt, n);
            snprintf(d, n, "on %s", on);
            op->detail = d;
        }
    }
    // @end
    return op;
}
// @end

// @from 08.04
/* Frees what arena a holds, its last chunk too. */
static void arena_free(Arena *a)
{
    if (a->head) {
        arena_reset(a);
        free(a->head);
        a->head = NULL;
    }
}
// @end

// @from 08.05
/* ------------------------------------------------------------ a set of rows seen (08.05) */

/* A hash set of lists of values: the results SELECT DISTINCT has handed
 * up, or the values a DISTINCT aggregate has stepped. Two lists are the
 * same when value_compare() finds each pair of values equal, NULL equal
 * to NULL and 1 equal to 1.0, as they are in the record compare of the
 * temporary index sqlite3 uses for the same job. The table is open
 * addressing: a list sits in the slot its hash picks, or in the next free
 * one after it; it is never more than half full. */
typedef struct SetSlot {
    u64 hash;
    Value *vals;                 /* a copy of the list, in the set's arena; NULL: a free slot */
} SetSlot;

typedef struct Set {
    int nvals;                   /* values in each list */
    SetSlot *slots;
    size_t cap;                  /* slots, a power of two */
    size_t n;                    /* lists held */
    Arena arena;                 /* the lists, and their text and blobs */
} Set;

#define SET_MIN 16               /* slots of an empty set */

/* Returns a new, empty set of lists of nvals values. */
static Set *set_new(int nvals)
{
    Set *s = xcalloc(1, sizeof *s);
    s->nvals = nvals;
    s->cap = SET_MIN;
    s->slots = xcalloc(s->cap, sizeof *s->slots);
    return s;
}

/* Empties s, back to its first size (a set that grew for one big group
 * is not swept whole for each small one after it). */
static void set_clear(Set *s)
{
    arena_reset(&s->arena);
    if (s->cap != SET_MIN) {
        free(s->slots);
        s->cap = SET_MIN;
        s->slots = xcalloc(s->cap, sizeof *s->slots);
    } else {
        memset(s->slots, 0, s->cap * sizeof *s->slots);
    }
    s->n = 0;
}

static void set_free(Set *s)
{
    if (!s)
        return;
    arena_free(&s->arena);
    free(s->slots);
    free(s);
}

/* The hash of the list vals[0..n): FNV-1a over each value's type and
 * bytes. Equal lists must hash alike, so a number hashes by its value: a
 * real that is a whole number in range hashes as the integer it equals
 * (1.0 as 1, -0.0 as 0), any other real by its bits. */
static u64 set_hash(const Value *vals, int n)
{
    u64 h = 14695981039346656037ULL;
    for (int i = 0; i < n; i++) {
        const Value *v = &vals[i];
        u8 num[8];
        const u8 *p = num;
        size_t len = 0;
        int tag = v->type;
        if (v->type == V_INT || v->type == V_REAL) {
            double r = v->r;
            if (v->type == V_INT || (r == floor(r) && r >= -9223372036854775808.0 && r < 9223372036854775808.0)) {
                i64 x = v->type == V_INT ? v->i : (i64)r;
                tag = V_INT;
                memcpy(num, &x, 8);
            } else {
                memcpy(num, &r, 8);
            }
            len = 8;
        } else if (v->type == V_TEXT || v->type == V_BLOB) {
            p = (const u8 *)v->s;
            len = (size_t)v->n;
        }
        h = (h ^ (u8)tag) * 1099511628211ULL;
        for (size_t k = 0; k < len; k++)
            h = (h ^ p[k]) * 1099511628211ULL;
    }
    // @internal
    /* DB_SET_COLLIDE=1 (the tests) folds every hash into four values, so
     * that lists collide and lookups walk long runs of slots. */
    static int collide = -1;
    if (collide < 0)
        collide = getenv("DB_SET_COLLIDE") != NULL;
    if (collide)
        h &= 3;
    // @end
    return h;
}

/* True if the lists a and b of n values are the same list. */
static int same_list(const Value *a, const Value *b, int n)
{
    for (int i = 0; i < n; i++)
        if (value_compare(&a[i], &b[i]) != 0)
            return 0;
    return 1;
}

/* Puts the list vals into s unless an equal one is there already.
 * Returns 1 if it was new (a copy of it is now in s, text and blobs
 * too), 0 if it had been seen. */
static int set_add(Set *s, const Value *vals)
{
    int n = s->nvals;
    // @build 08.05 a row not seen before
    // Hash the list (set_hash) and look from the slot its low bits pick,
    // one slot at a time, for a list with that hash whose values all
    // compare equal (same_list): found means seen before. A free slot ends
    // the search: the list is new, and a copy of it (keep() for text and
    // blobs, into the set's arena) goes in that slot. Once more than half
    // the slots are taken, double them and move each list to the slot its
    // hash picks in the new table, so runs of taken slots stay short.
    u64 h = set_hash(vals, n);
    size_t mask = s->cap - 1, i;
    for (i = h & mask; s->slots[i].vals; i = (i + 1) & mask)
        if (s->slots[i].hash == h && same_list(s->slots[i].vals, vals, n))
            return 0;
    Value *copy = arena_alloc(&s->arena, (size_t)n * sizeof(Value));
    for (int k = 0; k < n; k++)
        copy[k] = keep(&s->arena, vals[k]);
    s->slots[i].hash = h;
    s->slots[i].vals = copy;
    if (2 * ++s->n > s->cap) {
        size_t cap = 2 * s->cap;
        SetSlot *slots = xcalloc(cap, sizeof *slots);
        for (size_t j = 0; j < s->cap; j++) {
            if (!s->slots[j].vals)
                continue;
            size_t k = s->slots[j].hash & (cap - 1);
            while (slots[k].vals)
                k = (k + 1) & (cap - 1);
            slots[k] = s->slots[j];
        }
        free(s->slots);
        s->slots = slots;
        s->cap = cap;
    }
    return 1;
    // @end
}
// @end

// @from 08.04
/* ------------------------------------------------------------ Aggregate (08.04) */

/* Empties aggregate a's running state, for a new group. */
static void agg_clear(Agg *a)
{
    a->n = a->isum = 0;
    a->rsum = a->rerr = 0.0;
    a->approx = a->overflow = 0;
    memset(&a->best, 0, sizeof a->best);
    arena_reset(&a->hold);
    // @from 08.05
    if (a->seen)
        set_clear(a->seen);
    // @end
}

/* Adds r to a's double sum, keeping the part each addition rounds away
 * in a->rerr: the Kahan-Babushka-Neumaier sum of SQLite's func.c, which
 * makes ten 0.1s add up to exactly 1.0. */
static void kbn_add(Agg *a, double r)
{
    double s = a->rsum, t = s + r;
    if (fabs(s) > fabs(r))
        a->rerr += (s - t) + r;
    else
        a->rerr += (r - t) + s;
    a->rsum = t;
}

/* Adds the integer i to a's double sum. One past 2^52 a double cannot hold
 * every integer, so a big one goes in as two parts that it can. */
static void kbn_add_int(Agg *a, i64 i)
{
    if (i <= -4503599627370496LL || i >= 4503599627370496LL) {
        i64 low = i % 16384;
        kbn_add(a, (double)(i - low));
        kbn_add(a, (double)low);
    } else {
        kbn_add(a, (double)i);
    }
}

/* Switches a's sum from exact integers to the double sum, starting it
 * from the integer sum so far. */
static void kbn_start(Agg *a)
{
    i64 i = a->isum;
    if (i <= -4503599627370496LL || i >= 4503599627370496LL) {
        i64 low = i % 16384;
        a->rsum = (double)(i - low);
        a->rerr = (double)low;
    } else {
        a->rsum = (double)i;
        a->rerr = 0.0;
    }
    a->approx = 1;
}

/* Steps aggregate a with v, its argument's value on one more row (count(*)
 * has none: v is NULL). For min() and max(), returns 1 if this row did not
 * set the value, which decides whether a bare column comes from it; the
 * others return 0. */
static int agg_step(Agg *a, Value v)
{
    // @build 08.04 step: one more row
    // count(*) counts every row, count(x) every x that is not NULL. sum,
    // total and avg add v as sum_operand() reads it (NULL adds nothing):
    // exactly, in isum, while every value is an integer and the sum fits;
    // from the first value that is not an integer, or the first overflow,
    // in the compensated double sum (kbn_start, then kbn_add or
    // kbn_add_int). An overflow is remembered, and forgotten when a real
    // comes after it, as in func.c. min and max keep the first value no
    // later one beats (value_compare), copied into a->hold; NULL never
    // wins, and a row that does not set the value returns 1.
    switch (a->fn) {
    case AGG_COUNT_STAR:
        a->n++;
        return 0;
    case AGG_COUNT:
        if (v.type != V_NULL)
            a->n++;
        return 0;
    case AGG_SUM: case AGG_TOTAL: case AGG_AVG: {
        Value x = sum_operand(&v);
        if (x.type == V_NULL)
            return 0;
        a->n++;
        if (!a->approx) {
            i64 s;
            if (x.type == V_INT && !__builtin_add_overflow(a->isum, x.i, &s)) {
                a->isum = s;
                return 0;
            }
            a->overflow = x.type == V_INT;
            kbn_start(a);
        } else if (x.type == V_REAL) {
            a->overflow = 0;
        }
        if (x.type == V_INT)
            kbn_add_int(a, x.i);
        else
            kbn_add(a, x.r);
        return 0;
    }
    }
    if (v.type == V_NULL)
        return a->best.type != V_NULL;
    if (a->best.type != V_NULL) {
        int c = value_compare(&a->best, &v);
        if (a->fn == AGG_MAX ? c >= 0 : c <= 0)
            return 1;
    }
    arena_reset(&a->hold);
    a->best = keep(&a->hold, v);
    return 0;
    // @end
}

/* Sets *out to aggregate a's answer over the rows it was stepped with.
 * Returns 0, or -1 with the error set (sum's integer overflow). */
static int agg_finish(Agg *a, Value *out)
{
    // @build 08.04 finish: the answer
    // count: the count. sum: NULL when no value was added, the integer
    // sum when every value was an integer, else the double sum plus its
    // error term (the sum alone if the error term is no longer finite),
    // and "integer overflow" if the integers overflowed with no real after
    // them. total: the same, always a real, 0.0 for nothing. avg: that
    // real over the count, NULL for nothing. min, max: the value kept,
    // NULL if none. A real that is NaN is NULL.
    double r = a->approx ? a->rsum + (isfinite(a->rerr) ? a->rerr : 0.0) : (double)a->isum;
    memset(out, 0, sizeof *out);
    switch (a->fn) {
    case AGG_COUNT_STAR: case AGG_COUNT:
        out->type = V_INT;
        out->i = a->n;
        return 0;
    case AGG_SUM:
        if (a->n == 0)
            return 0;
        if (a->approx && a->overflow)
            return err("integer overflow");
        if (!a->approx) {
            out->type = V_INT;
            out->i = a->isum;
            return 0;
        }
        break;
    case AGG_AVG:
        if (a->n == 0)
            return 0;
        r /= (double)a->n;
        break;
    case AGG_TOTAL:
        break;
    default:
        *out = a->best;
        return 0;
    }
    if (!isnan(r)) {
        out->type = V_REAL;
        out->r = r;
    }
    return 0;
    // @end
}

/* Makes r the group's own row, what a bare column reads: a copy of its
 * values in op->grp, which always holds the query's width of values. A
 * row of one table holds only its columns and carries its rowid beside
 * them; the copy puts that rowid in the slot after the columns, where the
 * Aggregate's rows keep it. */
static void take_row(Op *op, Row *r)
{
    int w = op->q->width;
    arena_reset(&op->grpa);
    memset(op->grp.cols, 0, (size_t)w * sizeof(Value));
    for (int i = 0; i < r->ncols && i < w; i++)
        op->grp.cols[i] = keep(&op->grpa, r->cols[i]);
    if (r->ncols < w) {
        op->grp.cols[r->ncols].type = V_INT;
        op->grp.cols[r->ncols].i = r->rowid;
    }
    op->grp.ncols = w;
    op->grp.rowid = r->rowid;
    // @from 08.05
    /* The group's first row: keep its GROUP BY values, which a result
     * column that is a GROUP BY term shows (group_keys). The Sort below
     * evaluated the same terms on this row, so they cannot fail here. */
    if (op->ingroup == 0) {
        arena_reset(&op->keya);
        for (int j = 0; j < op->q->s->ngroup; j++) {
            Value v;
            if (eval(op->db, op->q->s->group[j], r, &v) < 0)
                memset(&v, 0, sizeof v);
            op->keys[j] = keep(&op->keya, v);
        }
    }
    // @end
}

/* Finishes the current group into op->row: the group's own row (all NULL
 * for a group of no rows, the one row of an empty input), then each
 * aggregate's answer, all copied into op->outa so that they outlast the
 * state, which is cleared for the next group. Returns 0, or -1 with the
 * error set. */
static int group_done(Op *op)
{
    Query *q = op->q;
    int w = q->width;
    for (int i = 0; i < w; i++) {
        if (op->ingroup)
            op->row.cols[i] = keep(&op->outa, op->grp.cols[i]);
        else
            memset(&op->row.cols[i], 0, sizeof(Value));
    }
    op->row.rowid = op->ingroup ? op->grp.rowid : 0;
    for (int k = 0; k < q->naggs; k++) {
        Value v;
        if (agg_finish(&q->aggs[k], &v) < 0)
            return -1;
        op->row.cols[w + k] = keep(&op->outa, v);
        agg_clear(&q->aggs[k]);
    }
    // @from 08.05
    for (int j = 0; j < q->s->ngroup; j++)
        op->row.cols[w + q->naggs + j] = keep(&op->outa, op->keys[j]);
    op->row.ncols = w + q->naggs + q->s->ngroup;
    // @else
    // op->row.ncols = w + q->naggs;
    // @end
    op->ingroup = 0;
    return 0;
}

// @from 08.05
/* Returns 1 if row r starts a new group, 0 if it is one more row of the
 * current one, -1 with the error set. */
static int new_group(Op *op, Row *r)
{
    Stmt *s = op->q->s;
    // @build 08.05 a new group starts
    // The rows come sorted by the GROUP BY terms, so a group is a run of
    // rows on which every term has the same value. Evaluate each term on r
    // and on the group's own row (op->grp: any row of the group has the
    // group's values) and compare them with value_compare(), as the sort
    // did: two NULLs are equal, and so are 1 and 1.0. One that differs
    // means r starts a new group.
    for (int j = 0; j < s->ngroup; j++) {
        Value a, b;
        if (eval(op->db, s->group[j], r, &a) < 0 || eval(op->db, s->group[j], &op->grp, &b) < 0)
            return -1;
        if (value_compare(&a, &b) != 0)
            return 1;
    }
    return 0;
    // @end
}

/* For a DISTINCT aggregate: returns 1 if v is new to the current group
 * (it is now remembered), 0 if the group has stepped an equal value. */
static int distinct_new(Agg *a, Value v)
{
    // @build 08.05 DISTINCT inside an aggregate
    // Each value steps the aggregate once per group. Keep the values it
    // has stepped in a set of its own, made the first time one comes
    // (agg_clear() empties it when a group starts), and say whether v was
    // new to it (set_add). NULL is a value like any other here: the first
    // one is stepped, and the aggregates skip it themselves.
    if (!a->seen)
        a->seen = set_new(1);
    return set_add(a->seen, &v);
    // @end
}
// @end

// @from 08.05
/* Hands up one row per group: the group's own row (q->width values), then
 * one value per aggregate, which the E_AGG nodes above read by slot, then
 * the GROUP BY values of the group's first row. Without GROUP BY the whole
 * input is one group, and an empty input gives that row too; with GROUP BY
 * the input comes sorted by the group's key and each run of rows with the
 * same key is a group. */
// @else
// /* Hands up one row: the group's own row (q->width values), then one
//  * value per aggregate, which the E_AGG nodes above read by slot. All the
//  * input is one group, and an empty input gives its row too. */
// @end
static int aggregate_next(Op *op, Row **out)
{
    Db *db = op->db;
    Query *q = op->q;
    // @build 08.04 one row from many
    // Pull rows from the child until it runs out. On each row step every
    // aggregate, in order: evaluate its argument on the row, agg_step().
    // Then the row becomes the group's own row (take_row) if it is the
    // group's first, or, when the query has a min() or max(), whenever
    // the last of those took it (op->hit clear): the rules sqlite3's
    // bytecode follows. Reset db->rowa after each row. When the child is
    // done, finish the group (group_done) and hand up its row; later calls
    // hand up nothing. The row handed up lives in op->outa until the next
    // call.
    if (op->done)
        return 0;
    arena_reset(&op->outa);
    for (;;) {
        Row *r;
        int rc = op->child->next(op->child, &r);
        if (rc < 0)
            return -1;
        // @from 08.05
        if (rc == 0 && q->s->ngroup && !op->ingroup) {
            op->done = 1;
            return 0;                     /* GROUP BY over no rows: no groups */
        }
        int starts = 0;
        if (rc == 1 && q->s->ngroup && op->ingroup && (starts = new_group(op, r)) < 0)
            return -1;
        if (starts && group_done(op) < 0)    /* finish the group r ends; r starts the next */
            return -1;
        // @end
        if (rc == 0) {
            op->done = 1;
            if (group_done(op) < 0)
                return -1;
            *out = &op->row;
            return 1;
        }
        for (int k = 0; k < q->naggs; k++) {
            Agg *a = &q->aggs[k];
            Value v = {0};
            if (a->arg && eval(db, a->arg, r, &v) < 0)
                return -1;
            // @from 08.05
            if (a->distinct && !distinct_new(a, v))
                continue;                 /* the group has had this value */
            // @end
            if (a->fn == AGG_MIN || a->fn == AGG_MAX)
                op->hit = agg_step(a, v);
            else
                agg_step(a, v);
        }
        if (op->ingroup == 0 || (q->minmax && !op->hit))
            take_row(op, r);
        op->ingroup++;
        arena_reset(&db->rowa);
        // @from 08.05
        if (starts) {
            *out = &op->row;              /* the group r ended */
            return 1;
        }
        // @end
    }
    // @end
}

/* Returns the Aggregate of q over child: its rows are the group's own row
 * (q->width values), then one value per aggregate of q. The aggregates'
 * state is cleared here, so a plan made again for the same query starts
 * afresh. */
Op *op_aggregate(Db *db, Op *child, Query *q)
{
    Op *op = new_op(db, "Aggregate", aggregate_next);
    op->child = child;
    op->q = q;
    // @from 08.05
    op->row.cols = xcalloc((size_t)(q->width + q->naggs + q->s->ngroup) + 1, sizeof(Value));
    op->keys = xcalloc((size_t)q->s->ngroup + 1, sizeof(Value));
    // @else
    // op->row.cols = xcalloc((size_t)(q->width + q->naggs) + 1, sizeof(Value));
    // @end
    op->grp.cols = xcalloc((size_t)q->width + 1, sizeof(Value));
    Buf b = {0};
    for (int k = 0; k < q->naggs; k++) {
        const char *s = expr_text(&db->stmt, q->aggs[k].call);
        if (k)
            buf_put(&b, ", ", 2);
        buf_put(&b, s, strlen(s));
        agg_clear(&q->aggs[k]);
    }
    // @from 08.05
    for (int j = 0; j < q->s->ngroup; j++) {
        const char *s = expr_text(&db->stmt, q->s->group[j]);
        buf_put(&b, j ? ", " : b.n ? " by " : "by ", j ? 2 : b.n ? 4 : 3);
        buf_put(&b, s, strlen(s));
    }
    // @end
    op->detail = b.n ? arena_strndup(&db->stmt, (const char *)b.p, b.n) : NULL;
    buf_free(&b);
    return op;
}

/* Frees what op_aggregate() and the aggregates' state hold. */
static void aggregate_free(Op *op)
{
    free(op->row.cols);
    free(op->grp.cols);
    arena_free(&op->grpa);
    arena_free(&op->outa);
    // @from 08.05
    free(op->keys);
    arena_free(&op->keya);
    // @end
    for (int k = 0; k < op->q->naggs; k++) {
        Agg *a = &op->q->aggs[k];
        arena_free(&a->hold);
        // @from 08.05
        set_free(a->seen);
        a->seen = NULL;
        // @end
    }
}
// @end

// @from 08.05
/* ------------------------------------------------------------ Distinct (08.05) */

/* Passes on a row only if its result, the values of the result
 * expressions on it, has not been handed up before: SELECT DISTINCT keeps
 * the first row of each result, in the order the rows come. */
static int distinct_next(Op *op, Row **out)
{
    for (;;) {
        int rc = op->child->next(op->child, out);
        if (rc <= 0)
            return rc;
        for (int i = 0; i < op->ndcols; i++)
            if (eval(op->db, op->dcols[i], *out, &op->dvals[i]) < 0)
                return -1;
        if (set_add(op->set, op->dvals))
            return 1;
        arena_reset(&op->db->rowa);
    }
}

/* Returns the Distinct over child for the result expressions cols. */
Op *op_distinct(Db *db, Op *child, Expr **cols, int ncols)
{
    Op *op = new_op(db, "Distinct", distinct_next);
    op->child = child;
    op->dcols = cols;
    op->ndcols = ncols;
    op->dvals = xcalloc((size_t)ncols + 1, sizeof(Value));
    op->set = set_new(ncols);
    Buf b = {0};
    for (int i = 0; i < ncols; i++) {
        const char *s = expr_text(&db->stmt, cols[i]);
        if (i)
            buf_put(&b, ", ", 2);
        buf_put(&b, s, strlen(s));
    }
    op->detail = arena_strndup(&db->stmt, (const char *)b.p, b.n);
    buf_free(&b);
    return op;
}
// @end

// @from 05.01
/* ------------------------------------------------------------ indexes (05.01) */

/* Builds into out the key of row in index ix: the indexed columns' values,
 * then the rowid, as one record. The rowid makes every entry unique and is
 * how a lookup gets back to the row. */
void index_key(Index *ix, Row *row, Buf *out)
{
    Value vals[9];
    // @build 05.01 an index entry
    for (int i = 0; i < ix->ncols; i++)
        vals[i] = row->cols[ix->cols[i]];
    memset(&vals[ix->ncols], 0, sizeof vals[0]);
    vals[ix->ncols].type = V_INT;
    vals[ix->ncols].i = row->rowid;
    out->n = 0;
    record_build(out, vals, ix->ncols + 1);
    // @end
}

/* Inserts the entry for row into index ix. */
static void index_add(Db *db, Index *ix, Row *row)
{
    Buf k = {0};
    Cursor c;
    index_key(ix, row, &k);
    cursor_open(&c, &db->pager, ix->root, 0);
    btree_insert(&c, 0, k.p, (u32)k.n);
    cursor_close(&c);
    buf_free(&k);
}

/* Deletes the entry for row from index ix, using the row's current values
 * to find it. A missing entry means the index is corrupt. */
static void index_remove(Db *db, Index *ix, Row *row)
{
    Buf k = {0};
    Cursor c;
    index_key(ix, row, &k);
    cursor_open(&c, &db->pager, ix->root, 0);
    if (!cursor_seek_key(&c, k.p, (u32)k.n, ix->ncols + 1, -1) ||
        record_compare(c.payload, c.npayload, k.p, (u32)k.n, ix->ncols + 1) != 0)
        fatal("database is corrupt: index %s has no entry for row %lld", ix->name, (long long)row->rowid);
    btree_delete(&c);
    cursor_close(&c);
    buf_free(&k);
}

// @from 08.07
/* ------------------------------------------------------------ UNIQUE (08.07) */

/* Sets the error sqlite3 gives for a row that breaks index ix's constraint,
 * its columns as table.column joined by ", " (a PRIMARY KEY says the same:
 * build.c, sqlite3UniqueConstraint), and returns -1. */
static int unique_failed(Index *ix)
{
    char cols[400];
    size_t n = 0;
    cols[0] = 0;
    for (int i = 0; i < ix->ncols && n < sizeof cols; i++)
        n += (size_t)snprintf(cols + n, sizeof cols - n, "%s%s.%s", i ? ", " : "", ix->table->name,
                              ix->table->cols[ix->cols[i]].name);
    return err("UNIQUE constraint failed: %s", cols);
}
// @end

/* Returns 1 if index ix already has an entry with row's values in its
 * columns for a row other than self, so writing row would break the
 * constraint; 0 if not. An entry is (columns..., rowid): the lookup
 * compares only the first ncols fields, and the rowid is read from the
 * entry found. */
static int unique_taken(Db *db, Index *ix, Row *row, i64 self)
{
    // @build 08.07 look before you write
    /* A NULL in any of the columns never conflicts: NULL equals nothing,
     * not even NULL (vdbe.c, OP_NoConflict). The walk goes past the first
     * equal entry because it may be self's own. */
    Value vals[8];
    for (int i = 0; i < ix->ncols; i++) {
        vals[i] = row->cols[ix->cols[i]];
        if (vals[i].type == V_NULL)
            return 0;
    }
    Buf k = {0};
    record_build(&k, vals, ix->ncols);
    Cursor c;
    cursor_open(&c, &db->pager, ix->root, 0);
    int taken = 0;
    for (int more = cursor_seek_key(&c, k.p, (u32)k.n, ix->ncols, -1); more && !taken; more = cursor_next(&c)) {
        if (record_compare(c.payload, c.npayload, k.p, (u32)k.n, ix->ncols) != 0)
            break;
        Value e[9];
        if (record_decode(c.payload, c.npayload, e, ix->ncols + 1) != ix->ncols + 1 || e[ix->ncols].type != V_INT)
            fatal("database is corrupt: bad entry in index %s", ix->name);
        taken = e[ix->ncols].i != self;
    }
    cursor_close(&c);
    buf_free(&k);
    return taken;
    // @end
}

// @from 08.07
static int index_changes(Index *ix, Row *old, Value *newv, i64 newid);

/* Returns 0 if row can be written to its table without breaking a UNIQUE
 * or PRIMARY KEY constraint, else sets the error for the first it breaks
 * and returns -1. ix is the table's list of indexes. sqlite3 keeps that
 * list newest first and checks it in that order (build.c, sqlite3CreateIndex;
 * insert.c, sqlite3GenerateConstraintChecks), so of two constraints a row
 * breaks, the one declared last is reported, and an index CREATE UNIQUE
 * INDEX made after the table before either. This list is oldest first, so
 * the rest of it is checked before ix. For an UPDATE, old is the row being
 * replaced: its own entries do not count, and an index whose entry the
 * update leaves as it is is not checked. */
static int check_unique(Db *db, Index *ix, Row *row, Row *old)
{
    if (!ix)
        return 0;
    if (check_unique(db, ix->next, row, old) < 0)
        return -1;
    if (!ix->unique || (old && !index_changes(ix, old, row->cols, row->rowid)))
        return 0;
    if (unique_taken(db, ix, row, old ? old->rowid : row->rowid))
        return unique_failed(ix);
    return 0;
}
// @end

/* Fills a new, empty index with an entry for every row of its table. */
int index_build(Db *db, Index *ix)
{
    Table *t = ix->table;
    Cursor c;
    Row row;
    row.cols = xcalloc((size_t)t->ncols + 1, sizeof(Value));
    cursor_open(&c, &db->pager, t->root, 1);
    // @build 05.01 fill a new index
    /* index_add() touches only the index's pages, so the table cursor c
     * stays valid. */
    for (int more = cursor_first(&c); more; more = cursor_next(&c)) {
        decode_row(t, &c, &row);
        // @from 08.07
        /* CREATE UNIQUE INDEX over rows that already break it fails as an
         * INSERT would; the statement is undone, so nothing of it is left. */
        if (ix->unique && unique_taken(db, ix, &row, row.rowid)) {
            cursor_close(&c);
            free(row.cols);
            return unique_failed(ix);
        }
        // @end
        index_add(db, ix, &row);
    }
    // @end
    cursor_close(&c);
    free(row.cols);
    return 0;
}
// @end

/* ------------------------------------------------------------ INSERT (04.01) */

/* Returns 0 if t can be modified, else reports why and returns -1. */
static int writable(Db *db, Table *t)
{
    (void)db;
    if (t->root == 1)
        return err("table %s may not be modified", t->name);
    if (t->opaque || t->readonly)
        return table_refused(t);
    return 0;
}

/* Stores one row and adds it to every index. vals has a value for every
 * column, with affinity applied. rowid_val is the rowid the statement
 * asked for (the INTEGER PRIMARY KEY's value, or a value given for the
 * rowid itself), or NULL to take one more than the largest in the table.
 * Returns 0, or -1 with the error set (datatype mismatch, UNIQUE or NOT
 * NULL failure) before anything has been written. */
static int insert_row(Db *db, Table *t, Value *vals, Value rowid_val)
{
    Cursor c;
    Buf rec = {0};
    int rc = 0;
    cursor_open(&c, &db->pager, t->root, 1);
    // @build 04.01 insert a row
    i64 rowid;
    const char *keyname = t->rowid_col >= 0 ? t->cols[t->rowid_col].name : "rowid";
    if (rowid_val.type != V_NULL) {
        if (rowid_val.type != V_INT) {
            rc = err("datatype mismatch");
            goto done;
        }
        rowid = rowid_val.i;
        if (cursor_seek_rowid(&c, rowid) && c.rowid == rowid) {
            rc = err("UNIQUE constraint failed: %s.%s", t->name, keyname);
            goto done;
        }
    } else {
        i64 max = btree_max_rowid(&c);
        if (max == INT64_MAX) {
            rc = err("database or disk is full");
            goto done;
        }
        rowid = max + 1;
    }
    /* The INTEGER PRIMARY KEY column's value is the rowid. */
    if (t->rowid_col >= 0) {
        memset(&vals[t->rowid_col], 0, sizeof(Value));
        vals[t->rowid_col].type = V_INT;
        vals[t->rowid_col].i = rowid;
    }
    for (int i = 0; i < t->ncols; i++) {
        if (t->cols[i].not_null && vals[i].type == V_NULL) {
            rc = err("NOT NULL constraint failed: %s.%s", t->name, t->cols[i].name);
            goto done;
        }
    }
    // @from 08.07
    Row cand = {vals, t->ncols, rowid};
    if (check_unique(db, t->indexes, &cand, NULL) < 0) {
        rc = -1;
        goto done;
    }
    // @end
    /* The record stores NULL for the INTEGER PRIMARY KEY column: the rowid
     * already holds its value. */
    Value saved = {0};
    if (t->rowid_col >= 0) {
        saved = vals[t->rowid_col];
        memset(&vals[t->rowid_col], 0, sizeof(Value));
    }
    record_build(&rec, vals, t->ncols);
    if (t->rowid_col >= 0)
        vals[t->rowid_col] = saved;
    btree_insert(&c, rowid, rec.p, (u32)rec.n);
    // @from 05.01
    Row row = {vals, t->ncols, rowid};
    for (Index *ix = t->indexes; ix; ix = ix->next)
        index_add(db, ix, &row);
    // @end
done:
    // @end
    cursor_close(&c);
    buf_free(&rec);
    return rc;
}

/* True for the names sqlite3 accepts for the rowid. */
static int is_rowid_name(const char *s)
{
    return strcasecmp(s, "rowid") == 0 || strcasecmp(s, "oid") == 0 || strcasecmp(s, "_rowid_") == 0;
}

/* Returns the number of column name in t (case-insensitive), or -1. */
static int column_index(Table *t, const char *name)
{
    for (int i = 0; i < t->ncols; i++)
        if (strcasecmp(t->cols[i].name, name) == 0)
            return i;
    return -1;
}

/* Executes INSERT: maps the value lists onto the table's columns, fills
 * unlisted columns from their DEFAULT, applies affinity, and stores each
 * row with insert_row(). */
static int exec_insert(Db *db, Stmt *s)
{
    Table *t = find_table(db, s->table);
    if (!t)
        return err("no such table: %s", s->table);
    if (writable(db, t) < 0)
        return -1;
    int map[1024];
    int nmap = s->nnames ? s->nnames : t->ncols;
    if (s->nnames) {
        for (int i = 0; i < s->nnames; i++) {
            int c = column_index(t, s->names[i]);
            if (c < 0 && is_rowid_name(s->names[i]))
                c = -2;    /* the rowid itself */
            if (c == -1)
                return err("table %s has no column named %s", t->name, s->names[i]);
            map[i] = c;
        }
    } else {
        for (int i = 0; i < t->ncols; i++)
            map[i] = i;
    }
    if (s->ncols != nmap) {
        if (s->nnames)
            return err("%d values for %d columns", s->ncols, nmap);
        return err("table %s has %d columns but %d values were supplied", t->name, t->ncols, s->ncols);
    }
    Value *vals = arena_alloc(&db->stmt, (size_t)(t->ncols + 1) * sizeof(Value));
    // @from 08.06
    /* A subquery in VALUES may read t, and sqlite3 works out every row
     * before it stores the first (insert.c: a SELECT that reads the table
     * goes through a temporary table). So every value with a subquery in
     * it is worked out here first, before anything is written. Its
     * subqueries name no table outside them (VALUES has none), so they
     * keep their answers for the second time, in the loop below. */
    for (int r = 0; s->nrows > 1 && r < s->nrows; r++) {
        for (int i = 0; i < nmap; i++) {
            Value v;
            if (has_subquery(s->rows[r][i]) &&
                (resolve_expr(db, s->rows[r][i], NULL, NULL) < 0 || eval(db, s->rows[r][i], NULL, &v) < 0))
                return -1;
        }
        arena_reset(&db->rowa);
    }
    // @end
    for (int r = 0; r < s->nrows; r++) {
        int given[1024] = {0};
        Value rowid = {0};
        for (int i = 0; i < nmap; i++) {
            Value v;
            // @from 08.06
            if (resolve_expr(db, s->rows[r][i], NULL, NULL) < 0 || eval(db, s->rows[r][i], NULL, &v) < 0)
            // @else
            // if (resolve_expr(s->rows[r][i], NULL, NULL) < 0 || eval(db, s->rows[r][i], NULL, &v) < 0)
            // @end
                return -1;
            if (map[i] == -2) {
                apply_affinity(&v, AFF_INTEGER, &db->rowa);
                rowid = v;
                continue;
            }
            vals[map[i]] = v;
            given[map[i]] = 1;
        }
        for (int i = 0; i < t->ncols; i++) {
            if (!given[i]) {
                memset(&vals[i], 0, sizeof vals[i]);
                if (t->cols[i].dflt && eval(db, t->cols[i].dflt, NULL, &vals[i]) < 0)
                    return -1;
            }
            apply_affinity(&vals[i], t->cols[i].affinity, &db->rowa);
        }
        if (t->rowid_col >= 0 && vals[t->rowid_col].type != V_NULL)
            rowid = vals[t->rowid_col];
        if (insert_row(db, t, vals, rowid) < 0)
            return -1;
        arena_reset(&db->rowa);
    }
    return 0;
}

// @from 04.04
/* ------------------------------------------------------------ UPDATE and DELETE (04.04) */

/* Collects into *out (caller frees) the rowids of the rows WHERE picks,
 * found with the planner. UPDATE and DELETE gather them first because
 * changing rows while a scan walks the same B-tree would move them under
 * it. */
static int collect_rowids(Db *db, Table *t, Expr *where, i64 **out, i64 *nout)
{
    Plan plan;
    if (plan_query(db, t, where, NULL, 0, NULL, NULL, &plan) < 0)
        return -1;
    i64 cap = 64, n = 0;
    i64 *ids = xmalloc((size_t)cap * sizeof(i64));
    Row *row;
    int rc;
    while ((rc = plan.root->next(plan.root, &row)) == 1) {
        if (n == cap) {
            cap *= 2;
            ids = xrealloc(ids, (size_t)cap * sizeof(i64));
        }
        ids[n++] = row->rowid;
        arena_reset(&db->rowa);
        if ((n & 255) == 0)
            pager_shrink(&db->pager);
    }
    op_close(plan.root);
    if (rc < 0) {
        free(ids);
        return -1;
    }
    *out = ids;
    *nout = n;
    return 0;
}

/* Copies row's values into the row arena, so they outlive the page they
 * were decoded from. */
static void keep_row(Db *db, Row *row)
{
    for (int i = 0; i < row->ncols; i++)
        row->cols[i] = keep(&db->rowa, row->cols[i]);
}
// @end

// @from 05.01
/* Returns 1 if changing old into (newv, newid) changes its entry in ix. Most
 * updates leave the indexed columns alone, and then the index need not
 * be touched at all. */
static int index_changes(Index *ix, Row *old, Value *newv, i64 newid)
{
    if (newid != old->rowid)
        return 1;
    for (int i = 0; i < ix->ncols; i++) {
        Value *a = &old->cols[ix->cols[i]], *b = &newv[ix->cols[i]];
        if (a->type != b->type || value_compare(a, b) != 0)
            return 1;
    }
    return 0;
}
// @end

// @from 08.07
/* Orders rowids, for qsort(). */
static int rowid_cmp(const void *pa, const void *pb)
{
    i64 a = *(const i64 *)pa, b = *(const i64 *)pb;
    return a < b ? -1 : a > b;
}

/* Does sqlite3 change these rows in rowid order? It changes them in the
 * order its scan finds them, unless the scan reads an index the UPDATE
 * changes (or the rowid changes): then it collects the rowids first and
 * visits them in rowid order (update.c, ONEPASS_OFF). With a UNIQUE
 * column the order decides whether SET a = a + 1 fails. cols[i] is the
 * column SET i assigns, -2 for the rowid itself. */
static int update_in_rowid_order(Table *t, Expr *where, int *cols, int ncols)
{
    Access acc;
    choose_access(t, where, &acc);
    if (acc.kind != ACCESS_INDEX_EQ && acc.kind != ACCESS_INDEX_RANGE)
        return 0;                    /* the table itself: rowid order already */
    for (int i = 0; i < ncols; i++) {
        if (cols[i] == -2 || cols[i] == t->rowid_col)
            return 1;
        for (int k = 0; k < acc.index->ncols; k++)
            if (acc.index->cols[k] == cols[i])
                return 1;
    }
    return 0;
}
// @end

/* Executes UPDATE. Each SET expression is evaluated against the OLD row.
 * The new rowid is the old one, or the new INTEGER PRIMARY KEY value; if it
 * changed, no other row may have it. A row leaves the indexes whose entry
 * changes (and the table, if its rowid changes) before the new record is
 * stored and added back to those same indexes. btree_insert() replaces a
 * row with the same rowid. */
static int exec_update(Db *db, Stmt *s)
{
    Table *t = find_table(db, s->table);
    if (!t)
        return err("no such table: %s", s->table);
    if (writable(db, t) < 0)
        return -1;
    int cols[256];
    for (int i = 0; i < s->nnames; i++) {
        cols[i] = column_index(t, s->names[i]);
        if (cols[i] < 0 && is_rowid_name(s->names[i]))
            cols[i] = t->rowid_col >= 0 ? t->rowid_col : -2;
        if (cols[i] == -1)
            return err("no such column: %s", s->names[i]);
        // @from 08.06
        if (resolve_expr(db, s->sets[i], t, NULL) < 0)
        // @else
        // if (resolve_expr(s->sets[i], t, NULL) < 0)
        // @end
            return -1;
    }
    // @from 08.06
    if (resolve_expr(db, s->where, t, NULL) < 0)
    // @else
    // if (resolve_expr(s->where, t, NULL) < 0)
    // @end
        return -1;
    i64 *ids, n;
    if (collect_rowids(db, t, s->where, &ids, &n) < 0)
        return -1;
    // @from 08.07
    if (update_in_rowid_order(t, s->where, cols, s->nnames))
        qsort(ids, (size_t)n, sizeof *ids, rowid_cmp);
    // @end
    Value *oldv = xcalloc((size_t)t->ncols + 1, sizeof(Value));
    Value *newv = xcalloc((size_t)t->ncols + 1, sizeof(Value));
    Buf rec = {0};
    Cursor c;
    cursor_open(&c, &db->pager, t->root, 1);
    int rc = 0;
    // @build 04.04 UPDATE
    /* The old row is copied out (keep_row) because the page it was decoded
     * from is about to change. */
    for (i64 k = 0; k < n && rc == 0; k++) {
        if (!cursor_seek_rowid(&c, ids[k]) || c.rowid != ids[k])
            continue;
        Row old = {oldv, t->ncols, ids[k]};
        decode_row(t, &c, &old);
        keep_row(db, &old);
        memcpy(newv, oldv, (size_t)t->ncols * sizeof(Value));
        i64 newid = old.rowid;
        for (int i = 0; i < s->nnames && rc == 0; i++) {
            Value v;
            if (eval(db, s->sets[i], &old, &v) < 0) {
                rc = -1;
                break;
            }
            if (cols[i] == -2) {
                apply_affinity(&v, AFF_INTEGER, &db->rowa);
                if (v.type != V_INT)
                    rc = err("datatype mismatch");
                else
                    newid = v.i;
                continue;
            }
            apply_affinity(&v, t->cols[cols[i]].affinity, &db->rowa);
            newv[cols[i]] = v;
        }
        if (rc)
            break;
        if (t->rowid_col >= 0) {
            Value *v = &newv[t->rowid_col];
            if (v->type != V_INT) {
                rc = err("datatype mismatch");
                break;
            }
            newid = v->i;
        }
        if (newid != old.rowid) {
            if (cursor_seek_rowid(&c, newid) && c.rowid == newid) {
                rc = err("UNIQUE constraint failed: %s.%s", t->name,
                         t->rowid_col >= 0 ? t->cols[t->rowid_col].name : "rowid");
                break;
            }
        }
        for (int i = 0; i < t->ncols; i++) {
            if (t->cols[i].not_null && newv[i].type == V_NULL) {
                rc = err("NOT NULL constraint failed: %s.%s", t->name, t->cols[i].name);
                break;
            }
        }
        if (rc)
            break;
        // @from 08.07
        Row cand = {newv, t->ncols, newid};
        if (check_unique(db, t->indexes, &cand, &old) < 0) {
            rc = -1;
            break;
        }
        // @end
        // @from 05.01
        for (Index *ix = t->indexes; ix; ix = ix->next)
            if (index_changes(ix, &old, newv, newid))
                index_remove(db, ix, &old);
        // @end
        if (newid != old.rowid) {
            if (cursor_seek_rowid(&c, old.rowid) && c.rowid == old.rowid)
                btree_delete(&c);
        }
        Value saved = {0};
        if (t->rowid_col >= 0) {
            saved = newv[t->rowid_col];
            memset(&newv[t->rowid_col], 0, sizeof(Value));
        }
        rec.n = 0;
        record_build(&rec, newv, t->ncols);
        if (t->rowid_col >= 0)
            newv[t->rowid_col] = saved;
        btree_insert(&c, newid, rec.p, (u32)rec.n);
        // @from 05.01
        Row nrow = {newv, t->ncols, newid};
        for (Index *ix = t->indexes; ix; ix = ix->next)
            if (index_changes(ix, &old, newv, newid))
                index_add(db, ix, &nrow);
        // @end
        arena_reset(&db->rowa);
    }
    // @end
    cursor_close(&c);
    buf_free(&rec);
    free(oldv);
    free(newv);
    free(ids);
    return rc;
}

/* Executes DELETE. With indexes, each row's entries are removed before the
 * row goes, since its values are what find them. */
static int exec_delete(Db *db, Stmt *s)
{
    Table *t = find_table(db, s->table);
    if (!t)
        return err("no such table: %s", s->table);
    if (writable(db, t) < 0)
        return -1;
    // @from 08.06
    if (resolve_expr(db, s->where, t, NULL) < 0)
    // @else
    // if (resolve_expr(s->where, t, NULL) < 0)
    // @end
        return -1;
    i64 *ids, n;
    if (collect_rowids(db, t, s->where, &ids, &n) < 0)
        return -1;
    Value *vals = xcalloc((size_t)t->ncols + 1, sizeof(Value));
    Cursor c;
    cursor_open(&c, &db->pager, t->root, 1);
    // @build 04.04 DELETE
    for (i64 k = 0; k < n; k++) {
        if (!cursor_seek_rowid(&c, ids[k]) || c.rowid != ids[k])
            continue;
        // @from 05.01
        if (t->indexes) {
            Row row = {vals, t->ncols, ids[k]};
            decode_row(t, &c, &row);
            keep_row(db, &row);
            for (Index *ix = t->indexes; ix; ix = ix->next)
                index_remove(db, ix, &row);
            if (!cursor_seek_rowid(&c, ids[k]) || c.rowid != ids[k])
                fatal("internal error: row %lld vanished", (long long)ids[k]);
        }
        // @end
        btree_delete(&c);
        arena_reset(&db->rowa);
    }
    // @end
    cursor_close(&c);
    free(vals);
    free(ids);
    return 0;
}

/* ------------------------------------------------------------ SELECT */

/* Prints one result row, columns separated by '|'. */
static void print_row(Db *db, Value *vals, int n)
{
    for (int i = 0; i < n; i++) {
        if (i)
            fputc('|', db->out);
        print_value(db->out, &vals[i]);
    }
    fputc('\n', db->out);
}

// @from 04.03
/* Returns the expression ORDER BY e stands for: ORDER BY 2 and ORDER BY
 * alias name a result column; anything else is e itself. */
static Expr *order_target(Stmt *s, Table *t, Expr *e, Expr **cols, int ncols)
{
    (void)t;
    if (e->op == E_INT && e->v.i >= 1 && e->v.i <= ncols)
        return cols[e->v.i - 1];
    if (e->op == E_COLUMN && !e->qual) {
        for (int i = 0; i < s->ncols; i++)
            if (s->cols[i].alias && strcasecmp(s->cols[i].alias, e->name) == 0 && s->cols[i].e)
                return s->cols[i].e;
    }
    return e;
}
// @end

// @from 08.01
/* The name a FROM item goes by in a join's * and its errors: its alias if
 * it has one, else its table's name. */
static const char *item_name(FromItem *it)
{
    return it->alias ? it->alias : it->t->name;
}

/* True if column col of FROM item k is ambiguous when * names it: another
 * item answers to item k's name and has a column called that too. sqlite3
 * writes such a column as main.<name>.<col>, which cannot tell them apart. */
static int star_ambiguous(Stmt *s, int k, const char *col)
{
    for (int j = 0; j < s->nfrom; j++) {
        if (j == k || !answers_to(&s->from[j], item_name(&s->from[k])))
            continue;
        for (int c = 0; c < s->from[j].t->ncols; c++)
            if (strcasecmp(s->from[j].t->cols[c].name, col) == 0)
                return 1;
    }
    return 0;
}

/* sqlite3's ordinal ending for n: 1st, 2nd, 3rd, 4th, 11th, 21st, ... */
static const char *ordinal(int n)
{
    int x = n % 10;
    if (x >= 4 || (n / 10) % 10 == 1)
        x = 0;
    return (const char *[]){"th", "st", "nd", "rd"}[x];
}

/* What ORDER BY term i (from 0) of a join stands for, as sqlite3 reads it
 * (resolveOrderGroupBy() in resolve.c): a bare name that is the name of a
 * result column (its alias, or the column a * stands for) is the first
 * such column; a number k is result column k, and there must be one;
 * anything else is an expression of its own. names[k] is result column k's
 * name, or NULL. Sets *out; returns 0, or -1 with the error set. */
static int join_order_target(Expr *e, int i, Expr **cols, const char **names, int ncols, Expr **out)
{
    *out = e;
    if (e->op == E_COLUMN && !e->qual) {
        for (int k = 0; k < ncols; k++) {
            if (names[k] && strcasecmp(names[k], e->name) == 0) {
                *out = cols[k];
                return 0;
            }
        }
    }
    if (e->op == E_INT) {
        if (e->v.i < 1 || e->v.i > ncols)
            return err("%d%s ORDER BY term out of range - should be between 1 and %d", i + 1, ordinal(i + 1), ncols);
        *out = cols[e->v.i - 1];
    }
    return 0;
}

// @from 08.04
/* The aggregate function e calls (AGG_COUNT_STAR ... AGG_MAX), or -1 if e
 * is no aggregate call; -2 with the error set for an aggregate called
 * with the wrong number of arguments, or one this engine lacks. count()
 * is count(*); min() and max() of two or more values are not aggregates
 * but sqlite3's scalar min and max. */
static int agg_fn(Expr *e)
{
    static const struct { const char *name; int fn; } fns[] = {
        {"count", AGG_COUNT}, {"sum", AGG_SUM}, {"total", AGG_TOTAL}, {"avg", AGG_AVG},
        {"min", AGG_MIN}, {"max", AGG_MAX},
    };
    if (e->op != E_FUNC)
        return -1;
    if (strcasecmp(e->name, "group_concat") == 0 || strcasecmp(e->name, "string_agg") == 0) {
        err("%s is not supported", e->name);
        return -2;
    }
    for (size_t i = 0; i < sizeof fns / sizeof fns[0]; i++) {
        if (strcasecmp(e->name, fns[i].name) != 0)
            continue;
        if (fns[i].fn == AGG_COUNT && e->nlist == 0)
            return AGG_COUNT_STAR;
        if (e->nlist == 1)
            return fns[i].fn;
        if ((fns[i].fn == AGG_MIN || fns[i].fn == AGG_MAX) && e->nlist > 1)
            return -1;
        err("wrong number of arguments to function %s()", e->name);
        return -2;
    }
    return -1;
}

/* True if a and b are the same expression, as sqlite3 tells two aggregate
 * calls apart (expr.c, sqlite3ExprCompare): the same operators, literals
 * and functions, names bound to the same slot. */
static int same_expr(Expr *a, Expr *b)
{
    if (!a || !b)
        return a == b;
    int op = a->op == E_AGG ? E_FUNC : a->op;
    if (op != (b->op == E_AGG ? E_FUNC : b->op) || a->nlist != b->nlist)
        return 0;
    if (op == E_INT || op == E_REAL || op == E_STR || op == E_BLOB)
        return a->v.type == b->v.type && value_compare(&a->v, &b->v) == 0;
    if (op == E_COLUMN && a->col != b->col)
        return 0;
    if (op == E_FUNC && strcasecmp(a->name, b->name) != 0)
        return 0;
    if (a->sub != b->sub)  /* subqueries: only copies of one (GROUP BY 1) are the same */ // @from 08.06
        return 0;  // @from 08.06
    if (a->distinct != b->distinct)  // @from 08.05
        return 0;  // @from 08.05
    if (!same_expr(a->a, b->a) || !same_expr(a->b, b->b) || !same_expr(a->c, b->c))
        return 0;
    for (int i = 0; i < a->nlist; i++)
        if (!same_expr(a->list[i], b->list[i]))
            return 0;
    return 1;
}

/* Lists the call e of aggregate function fn in q->aggs, unless the same
 * call is there already, and returns its number. */
static int agg_add(Db *db, Query *q, Expr *e, int fn)
{
    for (int k = 0; k < q->naggs; k++)
        if (same_expr(q->aggs[k].call, e))
            return k;
    if ((q->naggs & (q->naggs - 1)) == 0) {      /* 0, 1, 2, 4, ...: full, make it twice as big */
        Agg *aggs = arena_alloc(&db->stmt, (size_t)(q->naggs ? 2 * q->naggs : 1) * sizeof(Agg));
        if (q->naggs)
            memcpy(aggs, q->aggs, (size_t)q->naggs * sizeof(Agg));
        q->aggs = aggs;
    }
    Agg *a = &q->aggs[q->naggs];
    memset(a, 0, sizeof *a);
    a->fn = fn;
    a->call = e;
    a->arg = fn == AGG_COUNT_STAR ? NULL : e->list[0];
    a->distinct = e->distinct;  // @from 08.05
    if (fn == AGG_MIN || fn == AGG_MAX)
        q->minmax = 1;
    return q->naggs++;
}

// @from 08.06
static void names_in_query(Query *q, int d, int *mine, int *outside);

/* Notes in *mine whether e names a column of the query d levels out from
 * its own (a name of depth d), in *outside whether it names one of a query
 * further out; through the subqueries in it too. */
static void names_in(Expr *e, int d, int *mine, int *outside)
{
    if (!e)
        return;
    if (e->op == E_COLUMN || e->op == E_ROWID) {
        if (e->depth == d)
            *mine = 1;
        else if (e->depth > d)
            *outside = 1;
        return;
    }
    names_in(e->a, d, mine, outside);
    names_in(e->b, d, mine, outside);
    names_in(e->c, d, mine, outside);
    for (int i = 0; i < e->nlist; i++)
        names_in(e->list[i], d, mine, outside);
    if (e->sub)
        names_in_query(e->q, d + 1, mine, outside);
}

/* names_in() over every expression of the query q. */
static void names_in_query(Query *q, int d, int *mine, int *outside)
{
    Stmt *s = q->s;
    for (int i = 0; i < q->ncols; i++)
        names_in(q->cols[i], d, mine, outside);
    names_in(s->where, d, mine, outside);
    for (int k = 0; k < s->nfrom; k++)
        names_in(s->from[k].on, d, mine, outside);
    for (int i = 0; i < s->norder; i++)
        names_in(s->order[i].e, d, mine, outside);
    for (int i = 0; i < s->ngroup; i++)
        names_in(s->group[i], d, mine, outside);
    names_in(s->having, d, mine, outside);
}

/* True if the arguments of aggregate call e name columns of queries
 * around its own and none of its own. sqlite3 makes such a call an
 * aggregate of the nearest query it names (resolve.c, the TK_FUNCTION
 * case: sqlite3ReferencesSrcList() decides, one name context out at a
 * time), so `SELECT (SELECT count(c.id)) FROM customers c` is one row, 4.
 * This engine does not move an aggregate out of its subquery. */
static int outer_aggregate(Expr *e)
{
    int mine = 0, outside = 0;
    for (int i = 0; i < e->nlist; i++)
        names_in(e->list[i], 0, &mine, &outside);
    return outside && !mine;
}
// @end

/* Finds the aggregate calls in e, an expression of query q. misuse is NULL
 * where aggregates may be (what is evaluated above the Aggregate: the
 * result columns, ORDER BY of an aggregate query), else the error an
 * aggregate there is, which names it ("misuse of aggregate function %s()"
 * in WHERE, LIMIT and inside another aggregate). Each call is listed once
 * in q->aggs (agg_add) and its node becomes E_AGG, read from the slot past
 * the FROM's values where the Aggregate hands up its answer. Returns 0, or
 * -1 with the error set. */
static int find_aggs(Db *db, Query *q, Expr *e, const char *misuse)
{
    // @build 08.04 find the aggregates
    // A node that is E_AGG already was found through a node a result
    // column shares (ORDER BY 2), or is a copy of one: fine where
    // aggregates may be, an error where they may not. A call agg_fn()
    // knows is an aggregate: an error under misuse; else its arguments
    // are searched with misuse set (an aggregate inside an aggregate is
    // an error), it is listed, and its node rewritten in place: op E_AGG,
    // col q->width + its number (name and arguments stay, for EXPLAIN).
    // Anything else: search its operands and arguments.
    if (!e)
        return 0;
    // @from 08.06
    if (e->sub)          /* a subquery's aggregates are its own (outer_aggregate()); x of x IN is ours */
        return find_aggs(db, q, e->a, misuse);
    // @end
    if (e->op == E_AGG)
        return misuse ? err(misuse, e->name) : 0;
    int fn = agg_fn(e);
    if (fn == -2)
        return -1;
    if (fn >= 0) {
        // @from 08.06
        if (outer_aggregate(e))
            return err("aggregates of a query outside the subquery are not supported: %s()", e->name);
        // @end
        if (misuse)
            return err(misuse, e->name);
        for (int i = 0; i < e->nlist; i++)
            if (find_aggs(db, q, e->list[i], "misuse of aggregate function %s()") < 0)
                return -1;
        // @from 08.05
        if (e->distinct && e->nlist != 1)
            return err("DISTINCT aggregates must have exactly one argument");
        // @end
        e->col = q->width + agg_add(db, q, e, fn);
        e->op = E_AGG;
        return 0;
    }
    if (find_aggs(db, q, e->a, misuse) < 0 || find_aggs(db, q, e->b, misuse) < 0 ||
        find_aggs(db, q, e->c, misuse) < 0)
        return -1;
    for (int i = 0; i < e->nlist; i++)
        if (find_aggs(db, q, e->list[i], misuse) < 0)
            return -1;
    return 0;
    // @end
}

/* In e, an expression evaluated on the Aggregate's rows, a rowid of the
 * query's one table becomes the column in the slot it has there (slot),
 * so that it is NULL for the row an empty input gives, as in sqlite3. The
 * arguments of an aggregate are left alone: they are evaluated on the
 * table's own rows. */
static void rowid_from_slot(Expr *e, int slot)
{
    if (!e || e->op == E_AGG)
        return;
    if (e->op == E_ROWID) {
        if (e->depth)    /* the rowid of a query outside: its own row has it */ // @from 08.06
            return;  // @from 08.06
        e->op = E_COLUMN;
        e->col = slot;
        e->tcol = TCOL_ROWID;
        return;
    }
    rowid_from_slot(e->a, slot);
    rowid_from_slot(e->b, slot);
    rowid_from_slot(e->c, slot);
    for (int i = 0; i < e->nlist; i++)
        rowid_from_slot(e->list[i], slot);
}
// @end

// @from 08.05
/* Returns a copy of e, every node of it, in the statement arena. */
static Expr *copy_expr(Db *db, Expr *e)
{
    if (!e)
        return NULL;
    Expr *c = arena_alloc(&db->stmt, sizeof *c);
    *c = *e;
    c->a = copy_expr(db, e->a);
    c->b = copy_expr(db, e->b);
    c->c = copy_expr(db, e->c);
    if (e->nlist) {
        c->list = arena_alloc(&db->stmt, (size_t)e->nlist * sizeof(Expr *));
        for (int i = 0; i < e->nlist; i++)
            c->list[i] = copy_expr(db, e->list[i]);
    }
    return c;
}

/* In *pe, an expression of GROUP BY or HAVING, a bare name that no table
 * of the FROM has a column of (nor is a rowid's name) but that is the
 * alias of a result column becomes a copy of that column's expression,
 * as sqlite3 reads such a name (resolve.c, lookupName: the alias is the
 * last place it looks). */
static void use_aliases(Db *db, Query *q, Expr **pe)
{
    Expr *e = *pe;
    if (!e)
        return;
    if (e->op == E_COLUMN && !e->qual && !(q->scope.nfrom && (strcasecmp(e->name, "rowid") == 0 ||
        strcasecmp(e->name, "oid") == 0 || strcasecmp(e->name, "_rowid_") == 0))) {
        for (int k = 0; k < q->scope.nfrom; k++) {
            Table *t = q->scope.from[k].t;
            for (int c = 0; c < t->ncols; c++)
                if (strcasecmp(t->cols[c].name, e->name) == 0)
                    return;
        }
        for (int i = 0; i < q->s->ncols; i++) {
            ResultCol *rc = &q->s->cols[i];
            if (rc->e && rc->alias && strcasecmp(rc->alias, e->name) == 0) {
                *pe = copy_expr(db, rc->e);
                return;
            }
        }
        return;
    }
    use_aliases(db, q, &e->a);
    use_aliases(db, q, &e->b);
    use_aliases(db, q, &e->c);
    for (int i = 0; i < e->nlist; i++)
        use_aliases(db, q, &e->list[i]);
}

/* Binds q's GROUP BY terms as sqlite3 reads them (resolve.c,
 * resolveOrderGroupBy): a whole number k is result column k, and there
 * must be one; anything else is an expression, whose bare names may be
 * result columns' aliases (use_aliases). A term that is a result column
 * is a copy of it: the result column is read above the Aggregate, the
 * term below it. An aggregate in a term is an error. Returns 0, or -1
 * with the error set. */
static int group_resolve(Db *db, Query *q)
{
    Stmt *s = q->s;
    for (int i = 0; i < s->ngroup; i++) {
        Expr *e = s->group[i];
        if (e->op == E_INT) {
            if (e->v.i < 1 || e->v.i > q->ncols)
                return err("%d%s GROUP BY term out of range - should be between 1 and %d", i + 1, ordinal(i + 1),
                           q->ncols);
            s->group[i] = copy_expr(db, q->cols[e->v.i - 1]);
        } else {
            use_aliases(db, q, &s->group[i]);
            if (resolve_names(db, s->group[i], &q->scope) < 0)
                return -1;
        }
        if (find_aggs(db, q, s->group[i], "aggregate functions are not allowed in the GROUP BY clause") < 0)
            return -1;
    }
    return 0;
}

/* True if e reads nothing but GROUP BY terms and constants, so that it has
 * the same value on every row of a group (expr.c,
 * sqlite3ExprIsConstantOrGroupBy). */
static int group_constant(Stmt *s, Expr *e)
{
    if (!e)
        return 1;
    if (e->sub)          /* a subquery counts as varying, as in sqlite3 */ // @from 08.06
        return 0;  // @from 08.06
    for (int j = 0; j < s->ngroup; j++)
        if (same_expr(e, s->group[j]))
            return 1;
    if (e->op == E_COLUMN || e->op == E_ROWID || e->op == E_AGG)
        return 0;
    if (!group_constant(s, e->a) || !group_constant(s, e->b) || !group_constant(s, e->c))
        return 0;
    for (int i = 0; i < e->nlist; i++)
        if (!group_constant(s, e->list[i]))
            return 0;
    return 1;
}

/* Appends to *out, ANDed, each term of e (split at its ANDs) that is not a
 * HAVING term sqlite3 checks in WHERE instead: one that reads only GROUP BY
 * terms and constants and is not the literal 0 (select.c, havingToWhere,
 * which moves it so an index can find the rows). Those go to the end of
 * q's WHERE. The rows that come out are the same, but a group the term
 * rules out is never finished, so its sum cannot overflow, and of a group
 * whose rows differ in a way the key does not (1 and 1.0) only the rows the
 * term keeps are counted. */
static void having_to_where(Db *db, Stmt *s, Expr *e, Expr **out)
{
    if (e->op == E_AND) {
        having_to_where(db, s, e->a, out);
        having_to_where(db, s, e->b, out);
        return;
    }
    Expr **to = out;
    if (!(e->op == E_INT && e->v.i == 0) && group_constant(s, e))
        to = &s->where;
    if (*to) {
        Expr *and = arena_alloc(&db->stmt, sizeof *and);
        and->op = E_AND;
        and->col = and->aff = -1;
        and->a = *to;
        and->b = e;
        e = and;
    }
    *to = e;
}

/* A result column that is the same expression as a GROUP BY term, and more
 * than a column's name, shows that term's value on the group's first row,
 * which the Aggregate hands up after the aggregates' answers: sqlite3
 * points such a column at the register holding the group's key (select.c,
 * sqlite3ExprToRegister). It differs from evaluating the column on the
 * group's own row only when a min() or max() made a later row that, and
 * the key looks different there (1.0 against 1). Call it with every
 * aggregate found. */
static void group_keys(Db *db, Query *q)
{
    Stmt *s = q->s;
    for (int j = 0; j < s->ngroup; j++) {
        int col = -1;
        for (int i = 0; i < q->ncols; i++)
            if (same_expr(s->group[j], q->cols[i]))
                col = i;                  /* the last one, as resolveOrderGroupBy() does */
        if (col < 0 || q->cols[col]->op == E_COLUMN || q->cols[col]->op == E_ROWID)
            continue;
        Expr *k = arena_alloc(&db->stmt, sizeof *k);
        k->op = E_COLUMN;
        k->name = expr_text(&db->stmt, q->cols[col]);
        k->col = q->width + q->naggs + j;
        k->aff = q->cols[col]->aff;
        q->cols[col] = k;
    }
}
// @end

// @from 08.04
// @from 08.05
/* Finds q's aggregates (find_aggs) and decides whether q is an aggregate
 * query: it is if its result columns call an aggregate, or it has GROUP
 * BY (group_resolve binds its terms). Its ORDER BY may call aggregates
 * then (and HAVING, which only an aggregate query may have), but WHERE,
 * ON, LIMIT and OFFSET never. The errors are sqlite3's texts: an aggregate
 * in the ORDER BY of a query that is not an aggregate query, or in an ON
 * of one that is, gets the shorter "misuse of aggregate: f()". Above the
 * Aggregate the one table's rowid is read from its slot (rowid_from_slot),
 * and a result column that is a GROUP BY term from its own (group_keys).
 * Returns 0, or -1 with the error set. */
// @else
// /* Finds q's aggregates (find_aggs) and decides whether q is an aggregate
//  * query: it is if its result columns call an aggregate. Its ORDER BY may
//  * call aggregates then, but WHERE, ON, LIMIT and OFFSET never. The errors
//  * are sqlite3's texts: an aggregate in the ORDER BY of a query that is not
//  * an aggregate query, or in an ON of one that is, gets the shorter
//  * "misuse of aggregate: f()". Above the Aggregate the one table's rowid
//  * is read from its slot (rowid_from_slot). Returns 0, or -1 with the
//  * error set. */
// @end
static int resolve_aggregates(Db *db, Query *q)
{
    Stmt *s = q->s;
    const char *misuse = "misuse of aggregate function %s()", *shorter = "misuse of aggregate: %s()";
    for (int i = 0; i < q->ncols; i++)
        if (find_aggs(db, q, q->cols[i], NULL) < 0)
            return -1;
    // @from 08.05
    if (group_resolve(db, q) < 0)
        return -1;
    q->aggregate = q->naggs > 0 || s->ngroup > 0;
    if (s->having) {
        if (!q->aggregate)
            return err("HAVING clause on a non-aggregate query");
        use_aliases(db, q, &s->having);
        if (resolve_names(db, s->having, &q->scope) < 0 || find_aggs(db, q, s->having, NULL) < 0)
            return -1;
        if (s->ngroup) {
            Expr *having = s->having;
            s->having = NULL;
            having_to_where(db, s, having, &s->having);
        }
    }
    // @else
    // q->aggregate = q->naggs > 0;
    // @end
    if (find_aggs(db, q, s->where, misuse) < 0)
        return -1;
    for (int k = 0; k < q->scope.nfrom; k++)
        if (find_aggs(db, q, q->scope.from[k].on, q->aggregate ? shorter : misuse) < 0)
            return -1;
    for (int i = 0; i < s->norder; i++)
        if (find_aggs(db, q, s->order[i].e, q->aggregate ? NULL : shorter) < 0)
            return -1;
    if (find_aggs(db, q, s->limit, misuse) < 0 || find_aggs(db, q, s->offset, misuse) < 0)
        return -1;
    group_keys(db, q);  // @from 08.05
    if (q->aggregate && q->scope.nfrom == 1) {
        int slot = q->scope.from[0].t->ncols;
        for (int i = 0; i < q->ncols; i++)
            rowid_from_slot(q->cols[i], slot);
        for (int i = 0; i < s->norder; i++)
            rowid_from_slot(s->order[i].e, slot);
        rowid_from_slot(s->having, slot);  // @from 08.05
    }
    return 0;
}
// @end

/* Makes the SELECT s ready to plan, into q. Binds each FROM item to its
 * table (no such table; a table this engine cannot read is refused) and
 * gives it its place in the joined row: its columns and then its rowid,
 * from base on. Expands * into every item's columns, left to right, and
 * x.* into item x's; binds the names in the result columns, WHERE, each
 * ON, ORDER BY, LIMIT and OFFSET (resolve_names()). With one table ORDER
 * BY reads its terms as the core always has (order_target()); a join reads
 * them as sqlite3 does (join_order_target()). outer is the query this one
 * is inside, NULL for a statement's own. Returns 0, or -1 with the error
 * set. */
static int select_resolve(Db *db, Stmt *s, Scope *outer, Query *q)
{
    (void)outer;
    memset(q, 0, sizeof *q);
    q->s = s;
    q->scope.from = s->from;
    q->scope.nfrom = s->nfrom;
    q->scope.outer = outer;  // @from 08.06
    for (int k = 0; k < s->nfrom; k++) {
        FromItem *it = &s->from[k];
        it->t = find_table(db, it->table);
        if (!it->t)
            return err("no such table: %s", it->table);
        if (it->t->opaque)
            return table_refused(it->t);
        it->base = q->width;
        q->width += it->t->ncols + 1;
    }
    Table *t = s->nfrom ? s->from[0].t : NULL;
    /* How many result columns: a * counts the columns it stands for. */
    int n = 0;
    for (int i = 0; i < s->ncols; i++) {
        ResultCol *rc = &s->cols[i];
        if (rc->e) {
            n++;
            continue;
        }
        int seen = 0;
        for (int k = 0; k < s->nfrom; k++) {
            if (!rc->star_of || answers_to(&s->from[k], rc->star_of)) {
                n += s->from[k].t->ncols;
                seen = 1;
            }
        }
        if (!seen)
            return rc->star_of ? err("no such table: %s", rc->star_of) : err("no tables specified");
    }
    if (n == 0)
        return err(t ? "no columns" : "no tables specified");
    Expr **cols = arena_alloc(&db->stmt, (size_t)n * sizeof(Expr *));
    const char **names = arena_alloc(&db->stmt, (size_t)n * sizeof(char *));
    n = 0;
    for (int i = 0; i < s->ncols; i++) {
        ResultCol *rc = &s->cols[i];
        if (rc->e) {
            if (resolve_names(db, rc->e, &q->scope) < 0)
                return -1;
            names[n] = rc->alias;
            cols[n++] = rc->e;
            continue;
        }
        for (int k = 0; k < s->nfrom; k++) {
            FromItem *it = &s->from[k];
            if (rc->star_of && !answers_to(it, rc->star_of))
                continue;
            for (int c = 0; c < it->t->ncols; c++) {
                Expr *e = arena_alloc(&db->stmt, sizeof *e);
                e->op = E_COLUMN;
                e->name = it->t->cols[c].name;
                e->col = it->base + c;
                e->aff = it->t->cols[c].affinity;
                e->tab = k;
                e->tcol = c;
                if (s->nfrom > 1) {
                    e->qual = item_name(it);
                    if (star_ambiguous(s, k, e->name))
                        return err("ambiguous column name: main.%s.%s", e->qual, e->name);
                }
                names[n] = e->name;
                cols[n++] = e;
            }
        }
    }
    if (resolve_names(db, s->where, &q->scope) < 0)
        return -1;
    for (int k = 0; k < s->nfrom; k++)
        if (resolve_names(db, s->from[k].on, &q->scope) < 0)
            return -1;
    for (int i = 0; i < s->norder; i++) {
        Expr *e = s->order[i].e;
        if (s->nfrom <= 1)
            s->order[i].e = order_target(s, t, e, cols, n);
        else if (join_order_target(e, i, cols, names, n, &s->order[i].e) < 0)
            return -1;
        if (s->order[i].e == e && resolve_names(db, e, &q->scope) < 0)
            return -1;      /* a result column is bound already */
    }
    Scope none = {0};
    if (resolve_names(db, s->limit, &none) < 0 || resolve_names(db, s->offset, &none) < 0)
        return -1;
    q->cols = cols;
    q->ncols = n;
    // @from 08.04
    /* With every name bound: which calls are aggregates, and whether this
     * is an aggregate query. */
    if (resolve_aggregates(db, q) < 0)
        return -1;
    // @end
    return 0;
}
// @end

// @from 08.06
/* ------------------------------------------------------------ subqueries (08.06) */

/* Binds subquery e, which stands in scope sc: its SELECT is made ready as
 * any query is (select_resolve), with sc as the scope around it, where a
 * name its own tables lack is looked for. A scalar or IN subquery must
 * give one column, and sqlite3's words for it say "columns" whatever the
 * number. A scalar subquery compares with its column's affinity, as that
 * column would (sqlite3ExprAffinity in sqlite3's expr.c, TK_SELECT). Bound
 * once: INSERT binds each row's values twice when it has a subquery.
 * Returns 0, or -1 with the error set. */
int resolve_subquery(Db *db, Expr *e, Scope *sc)
{
    if (e->q)
        return 0;
    Query *q = arena_alloc(&db->stmt, sizeof *q);
    if (select_resolve(db, e->sub, sc, q) < 0)
        return -1;
    if (e->op != E_EXISTS && q->ncols != 1)
        return err("sub-select returns %d columns - expected 1", q->ncols);
    if (e->op == E_EXISTS) {
        /* Whether there is a row does not depend on their order, and sqlite3
         * drops DISTINCT too (select.c, IgnorableDistinct: "All of these
         * destinations are also able to ignore the ORDER BY clause"), so
         * that EXISTS (SELECT DISTINCT ... LIMIT 1 OFFSET 5) counts every
         * row. */
        e->sub->norder = 0;
        e->sub->distinct = 0;
    }
    e->q = q;
    e->correlated = q->scope.correlated;
    if (e->op == E_SUBQUERY)
        e->aff = q->cols[0]->aff;
    return 0;
}

static int numeric_aff(int aff)
{
    return aff == AFF_INTEGER || aff == AFF_REAL || aff == AFF_NUMERIC;
}

/* The affinity x IN (SELECT y ...) compares with, given x's and y's (-1:
 * none), applied to x and to every y (sqlite3's expr.c, exprINAffinity
 * and sqlite3CompareAffinity): when both are columns, NUMERIC if either is
 * numeric, else none (BLOB); when one is, its affinity; else none. It
 * comes to what eval_compare() does for x = y. */
static int in_affinity(int ax, int ay)
{
    if (ax >= 0 && ay >= 0)
        return numeric_aff(ax) || numeric_aff(ay) ? AFF_NUMERIC : AFF_BLOB;
    return ax >= 0 ? ax : ay;
}

/* For qsort(): the order of values. */
static int value_cmp(const void *a, const void *b)
{
    return value_compare(a, b);
}

/* Is x in the set kept on e, an IN subquery that has run once? Returns 1
 * yes, 0 no, -1 unknown: SQL's NULL. */
static int set_lookup(Expr *e, Value x)
{
    // @build 08.06 IN a set that may hold NULL
    // x NULL: unknown when there is anything at all to compare it with,
    // a NULL included; no for an empty set. Else look for x by bisection
    // in the sorted values (value_compare): found is yes. Not found: no,
    // unless the set holds a NULL, which might have been x: unknown. So
    // x NOT IN a set with a NULL is never true. These are sqlite3's
    // answers (expr.c, sqlite3ExprCodeIN: steps 2 to 6).
    if (x.type == V_NULL)
        return e->nset > 0 || e->has_null ? -1 : 0;
    int lo = 0, hi = e->nset;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        int c = value_compare(&e->set[mid], &x);
        if (c == 0)
            return 1;
        if (c < 0)
            lo = mid + 1;
        else
            hi = mid;
    }
    return e->has_null ? -1 : 0;
    // @end
}

/* Runs the query of subquery e once, on row, the row of the query e stands
 * in (NULL if there is none), into *out:
 *   E_SUBQUERY   the first row's value, NULL if there is no row
 *   E_EXISTS     1 if there is a row, else 0
 *   E_IN/NOTIN   correlated: 1, 0 or NULL as x (with the comparison's
 *                affinity aff applied) is in its rows; run once: nothing,
 *                but every value is kept on e, sorted, for set_lookup()
 * Returns 0, or -1 with the error set. */
static int run_subquery(Db *db, Expr *e, Row *row, Value x, int aff, Value *out)
{
    Query *q = e->q;
    int in = e->op == E_IN || e->op == E_NOTIN;
    Arena rowa = db->rowa, stmt = db->stmt;     /* the caller's */
    Arena *keepa = e->correlated ? &rowa : &db->once;
    Value *set = NULL;
    int nset = 0, cap = 0, any = 0, nulls = 0, found = 0, rc;
    Plan plan;
    Row *r;
    memset(out, 0, sizeof *out);
    memset(&plan, 0, sizeof plan);
    // @build 08.06 run the query inside
    // Push row, where a name from the query outside reads it, and give the
    // run arenas of its own: its operators reset db->rowa, and its plan must
    // not pile up in the statement's arena run after run. Plan the query
    // and pull rows - and never call pager_shrink(): the caller's row
    // points into pages. A scalar subquery stops at its first row, EXISTS
    // too; IN run once takes every value, with the comparison's affinity;
    // correlated, it stops at x (or at any row, for a NULL x). What must
    // outlive the run is copied out (keep()) first: into db->once if it is
    // kept for the statement, else into the caller's row arena. Then close
    // the plan, give the arenas back and pop the row.
    memset(&db->rowa, 0, sizeof db->rowa);
    memset(&db->stmt, 0, sizeof db->stmt);
    db->outer[db->nouter++] = row;
    rc = plan_select(db, q, &plan);
    while (rc == 0 && !found && (rc = plan.root->next(plan.root, &r)) == 1) {
        Value v;
        rc = 0;
        any = 1;
        if (e->op == E_EXISTS)
            break;
        if ((rc = eval(db, q->cols[0], r, &v)) < 0)
            break;
        if (!in) {
            *out = keep(keepa, v);
            break;
        }
        if (v.type == V_NULL) {
            nulls = 1;
        } else {
            apply_affinity(&v, aff, &db->rowa);
            if (e->correlated) {
                found = x.type != V_NULL && value_compare(&v, &x) == 0;
            } else {
                if (nset == cap) {
                    cap = cap ? 2 * cap : 64;
                    set = xrealloc(set, (size_t)cap * sizeof *set);
                }
                set[nset++] = keep(&db->once, v);
            }
        }
        if (e->correlated && x.type == V_NULL)
            break;
        arena_reset(&db->rowa);
    }
    op_close(plan.root);
    db->nouter--;
    arena_free(&db->rowa);
    arena_free(&db->stmt);
    db->rowa = rowa;
    db->stmt = stmt;
    if (rc < 0) {
        free(set);
        return -1;
    }
    if (e->op == E_EXISTS) {
        out->type = V_INT;
        out->i = any;
    } else if (in && e->correlated) {
        /* the answers of set_lookup(), from what the scan saw */
        if (found || !(nulls || (x.type == V_NULL && any))) {
            out->type = V_INT;
            out->i = found;
        }
    } else if (in) {
        qsort(set, (size_t)nset, sizeof *set, value_cmp);
        e->set = arena_alloc(&db->once, (size_t)nset * sizeof *set + 1);
        memcpy(e->set, set, (size_t)nset * sizeof *set);
        e->nset = nset;
        e->has_null = nulls;
    }
    free(set);
    return 0;
    // @end
}

/* Evaluates subquery e on row, the row of the query it stands in (NULL if
 * there is none), into *out:
 *   (SELECT ...)          its first row's value; NULL if there is no row
 *   EXISTS (SELECT ...)   1 if it has a row, else 0
 *   x IN (SELECT ...)     1 if x is one of its values, 0 if not, NULL if
 *                         a NULL leaves that unknown; NOT IN the opposite
 * One that names no table outside itself runs the first time it is needed
 * and its answer is kept for the rest of the statement (SQLite: OP_Once),
 * for IN the whole set; a correlated one runs again every time, since its
 * outer row has changed. Returns 0, or -1 with the error set. */
int eval_subquery(Db *db, Expr *e, Row *row, Value *out)
{
    if (!e->q)
        return err("internal error: subquery not bound");
    int in = e->op == E_IN || e->op == E_NOTIN, aff = -1;
    Value x = {0};
    if (in) {
        if (eval(db, e->a, row, &x) < 0)
            return -1;
        aff = in_affinity(e->a->aff, e->q->cols[0]->aff);
        apply_affinity(&x, aff, &db->rowa);
    }
    if (e->cached) {
        *out = e->answer;
    } else {
        if (run_subquery(db, e, row, x, aff, out) < 0)
            return -1;
        if (!e->correlated) {
            e->answer = *out;
            e->cached = 1;
        }
    }
    if (in && !e->correlated) {         /* its set is kept: look x up in it */
        int t = set_lookup(e, x);
        memset(out, 0, sizeof *out);
        if (t >= 0) {
            out->type = V_INT;
            out->i = t;
        }
    }
    if (e->op == E_NOTIN && out->type == V_INT)
        out->i = !out->i;
    return 0;
}
// @end

// @from 08.01
/* Executes SELECT: makes it ready (select_resolve), plans it, then streams
 * the plan's rows through the result expressions. */
// @else
// /* Executes SELECT: expands *, resolves names, plans, then streams the
//  * plan's rows through the result expressions. */
// @end
static int exec_select(Db *db, Stmt *s)
{
    // @from 08.01
    Query q;
    if (select_resolve(db, s, NULL, &q) < 0)
        return -1;
    Table *t = q.scope.nfrom ? q.scope.from[0].t : NULL;
    Expr **cols = q.cols;
    int n = q.ncols;
    // @else
    // Table *t = NULL;
    // if (s->table) {
    //     t = find_table(db, s->table);
    //     if (!t)
    //         return err("no such table: %s", s->table);
    //     if (t->opaque)
    //         return table_refused(t);
    // }
    // /* Expand * and resolve every name. */
    // int n = 0;
    // for (int i = 0; i < s->ncols; i++)
    //     n += s->cols[i].e ? 1 : (t ? t->ncols : 0);
    // if (n == 0)
    //     return err(t ? "no columns" : "no tables specified");
    // Expr **cols = arena_alloc(&db->stmt, (size_t)n * sizeof(Expr *));
    // n = 0;
    // for (int i = 0; i < s->ncols; i++) {
    //     if (s->cols[i].e) {
    //         if (resolve_expr(s->cols[i].e, t, s->alias) < 0)
    //             return -1;
    //         cols[n++] = s->cols[i].e;
    //         continue;
    //     }
    //     for (int c = 0; c < t->ncols; c++) {
    //         Expr *e = arena_alloc(&db->stmt, sizeof *e);
    //         e->op = E_COLUMN;
    //         e->name = t->cols[c].name;
    //         e->col = c;
    //         e->aff = t->cols[c].affinity;
    //         cols[n++] = e;
    //     }
    // }
    // if (resolve_expr(s->where, t, s->alias) < 0)
    //     return -1;
    // @end
    // @from 04.03
    // @from 08.01
    // @else
    // for (int i = 0; i < s->norder; i++) {
    //     s->order[i].e = order_target(s, t, s->order[i].e, cols, n);
    //     if (resolve_expr(s->order[i].e, t, s->alias) < 0)
    //         return -1;
    // }
    // @end
    // @end
    // @from 08.01
    // @else
    // if (resolve_expr(s->limit, NULL, NULL) < 0 || resolve_expr(s->offset, NULL, NULL) < 0)
    //     return -1;
    // @end
    Plan plan;
    // @from 08.01
    if (plan_select(db, &q, &plan) < 0)
    // @else
    // if (plan_query(db, t, s->where, s->order, s->norder, s->limit, s->offset, &plan) < 0)
    // @end
        return -1;
    // @from 05.03
    if (s->explain == 2) {
        explain_query_plan(db, s, t, &plan);
        op_close(plan.root);
        return 0;
    }
    // @else
    // if (s->explain == 2) {
    //     op_close(plan.root);
    //     return err("EXPLAIN QUERY PLAN is not supported");
    // }
    // @end
    if (s->explain == 1) {
        explain_tree(db, s, &plan);
        op_close(plan.root);
        return 0;
    }
    Value *out = xmalloc((size_t)n * sizeof(Value));
    Row *row;
    int rc;
    i64 count = 0;
    while ((rc = plan.root->next(plan.root, &row)) == 1) {
        for (int i = 0; i < n; i++)
            if (eval(db, cols[i], row, &out[i]) < 0) {
                rc = -1;
                break;
            }
        if (rc < 0)
            break;
        print_row(db, out, n);
        arena_reset(&db->rowa);
        if ((++count & 255) == 0)
            pager_shrink(&db->pager);    /* no page pointer is held between rows */
    }
    free(out);
    op_close(plan.root);
    return rc < 0 ? -1 : 0;
}

// @from 04.04
/* EXPLAIN [QUERY PLAN] of UPDATE and DELETE: how they find their rows. */
static int explain_write(Db *db, Stmt *s)
{
    Table *t = find_table(db, s->table);
    if (!t)
        return err("no such table: %s", s->table);
    // @from 08.06
    if (resolve_expr(db, s->where, t, NULL) < 0)
    // @else
    // if (resolve_expr(s->where, t, NULL) < 0)
    // @end
        return -1;
    Plan plan;
    if (plan_query(db, t, s->where, NULL, 0, NULL, NULL, &plan) < 0)
        return -1;
    // @from 05.03
    if (s->explain == 2)
        explain_query_plan(db, s, t, &plan);
    else
        explain_tree(db, s, &plan);
    // @else
    // if (s->explain == 2) {
    //     op_close(plan.root);
    //     return err("EXPLAIN QUERY PLAN is not supported");
    // }
    // explain_tree(db, s, &plan);
    // @end
    op_close(plan.root);
    return 0;
}
// @end
// @end

/* ------------------------------------------------------------ PRAGMA */

/* Executes the PRAGMAs this engine supports: with a value it sets, without
 * one it prints. */
static int exec_pragma(Db *db, Stmt *s)
{
    Pager *p = &db->pager;
    const char *v = s->pragma_value;
    const char *name = s->name;
    if (strcasecmp(name, "journal_mode") == 0) {
        static const char *names[] = {"delete", "wal", "off"};
        // @from 06.02
        if (v) {
            int mode;
            if (strcasecmp(v, "delete") == 0)
                mode = JOURNAL_DELETE;
            // @from 06.04
            else if (strcasecmp(v, "wal") == 0)
                mode = JOURNAL_WAL;
            // @end
            else if (strcasecmp(v, "off") == 0)
                mode = JOURNAL_OFF;
            // @from 06.04
            else
                return err("journal_mode %s is not supported (delete, wal or off)", v);
            // @else
            // else
            //     return err("journal_mode %s is not supported (delete or off)", v);
            // @end
            if (db->in_txn)
                return err("cannot change the journal mode from within a transaction");
            if (pager_set_journal_mode(p, mode) < 0)
                return -1;
        }
        // @else
        // if (v && strcasecmp(v, "off") != 0)
        //     return err("journal_mode %s is not supported (off)", v);
        // @end
        fprintf(db->out, "%s\n", names[p->journal_mode]);
        return 0;
    }
    if (strcasecmp(name, "page_size") == 0) {
        if (v) {
            u32 ps = (u32)atoi(v);
            if (p->npages == 0 && ps >= 512 && ps <= 65536 && (ps & (ps - 1)) == 0)
                p->page_size = p->usable = ps;
            return 0;
        }
        fprintf(db->out, "%u\n", p->page_size);
        return 0;
    }
    if (strcasecmp(name, "page_count") == 0) {
        fprintf(db->out, "%u\n", p->npages);
        return 0;
    }
    if (strcasecmp(name, "freelist_count") == 0) {
        fprintf(db->out, "%u\n", p->npages ? get4(pager_get(p, 1) + 36) : 0);
        return 0;
    }
    if (strcasecmp(name, "schema_version") == 0) {
        fprintf(db->out, "%u\n", p->npages ? get4(pager_get(p, 1) + 40) : 0);
        return 0;
    }
    if (strcasecmp(name, "cache_size") == 0) {
        if (v) {
            long n = atol(v);
            if (n < 0)
                n = -n * 1024 / (long)p->page_size;
            p->cache_max = n > 10 ? (u32)n : 10;
            return 0;
        }
        fprintf(db->out, "%u\n", p->cache_max);
        return 0;
    }
    if (strcasecmp(name, "synchronous") == 0) {
        /* This engine always syncs as sqlite3 does with synchronous=FULL. */
        if (v && strcasecmp(v, "full") != 0 && strcmp(v, "2") != 0)
            return err("only synchronous=FULL is supported");
        if (!v)
            fprintf(db->out, "2\n");
        return 0;
    }
    if (strcasecmp(name, "fullfsync") == 0) {
        /* fsync(2), never F_FULLFSYNC: sqlite3's default. */
        if (v && strcasecmp(v, "off") != 0 && strcmp(v, "0") != 0 && strcasecmp(v, "false") != 0)
            return err("only fullfsync=OFF is supported");
        if (!v)
            fprintf(db->out, "0\n");
        return 0;
    }
    return err("unknown pragma: %s", name);
}

/* ------------------------------------------------------------ statements */

/* True for statements that change the database file. */
static int is_write(int kind)
{
    return kind == S_INSERT || kind == S_UPDATE || kind == S_DELETE || kind == S_CREATE_TABLE ||
           kind == S_CREATE_INDEX || kind == S_DROP_TABLE || kind == S_DROP_INDEX;
}

/* Dispatches a write statement to its executor. */
static int run_write(Db *db, Stmt *s)
{
    switch (s->kind) {
    // @from 04.01
    case S_INSERT: return exec_insert(db, s);
    // @else
    // case S_INSERT: return err("INSERT is not supported");
    // @end
    // @from 04.04
    case S_UPDATE: return exec_update(db, s);
    case S_DELETE: return exec_delete(db, s);
    // @else
    // case S_UPDATE: return err("UPDATE is not supported");
    // case S_DELETE: return err("DELETE is not supported");
    // @end
    // @from 03.03
    case S_CREATE_TABLE: return create_table(db, s);
    // @else
    // case S_CREATE_TABLE: return err("CREATE TABLE is not supported");
    // @end
    // @from 05.01
    case S_CREATE_INDEX: return create_index(db, s);
    // @else
    // case S_CREATE_INDEX: return err("CREATE INDEX is not supported");
    // @end
    // @from 03.03
    default: return drop_object(db, s);
    // @else
    // default: return err("DROP is not supported");
    // @end
    }
}

// @from 03.03
/* Runs one parsed statement. Transaction control and reads run directly; a
 * write outside BEGIN is a transaction of its own, committed here or
 * rolled back on error. After a failed write the catalog is reloaded, so
 * it matches the file as the rollback left it; the error message is kept
 * across the reload. */
// @else
// /* Runs one parsed statement. Transaction control and reads run directly; a
//  * write outside BEGIN is a transaction of its own, committed here or
//  * rolled back on error. */
// @end
static int run_stmt(Db *db, Stmt *s)
{
    Pager *p = &db->pager;
    pager_shrink(p);
    switch (s->kind) {
    case S_BEGIN:
        if (db->in_txn)
            return err("cannot start a transaction within a transaction");
        db->in_txn = 1;
        return 0;
    case S_COMMIT:
        if (!db->in_txn)
            return err("cannot commit - no transaction is active");
        db->in_txn = 0;
        return pager_commit(p);
    case S_ROLLBACK:
        if (!db->in_txn)
            return err("cannot rollback - no transaction is active");
        db->in_txn = 0;
        pager_rollback(p);
        // @from 03.03
        return schema_load(db);
        // @else
        // return 0;
        // @end
    case S_PRAGMA:
        return exec_pragma(db, s);
    // @from 04.01
    case S_SELECT:
        return exec_select(db, s);
    // @else
    // case S_SELECT:
    //     return err("SELECT is not supported");
    // @end
    }
    // @from 04.04
    if (s->explain) {
        if (s->kind == S_UPDATE || s->kind == S_DELETE)
            return explain_write(db, s);
        return 0;
    }
    // @else
    // if (s->explain)
    //     return err("EXPLAIN is only supported for SELECT");
    // @end
    if (!is_write(s->kind))
        return err("internal error: statement kind %d", s->kind);
    /* A write. Outside BEGIN it is a transaction of its own; inside, it
     * can still fail alone, so the pager keeps what it changes. */
    if (p->npages == 0)
        header_init(p);
    /* A one-row INSERT checks everything before it writes anything, so if
     * it fails there is nothing to undo; any other write may fail after
     * changing some rows. */
    int savepoint = db->in_txn && !(s->kind == S_INSERT && s->nrows == 1);
    if (savepoint)
        pager_stmt_begin(p);
    int rc = run_write(db, s);
    if (rc < 0) {
        if (savepoint)
            pager_stmt_rollback(p);
        else if (!db->in_txn)
            pager_rollback(p);
        /* else a one-row INSERT inside BEGIN failed before it wrote anything */
        // @from 03.03
        char keep[sizeof errmsg];
        memcpy(keep, errmsg, sizeof keep);
        schema_load(db);
        memcpy(errmsg, keep, sizeof keep);
        // @end
        return -1;
    }
    if (db->in_txn)
        pager_stmt_end(p);
    else if (pager_commit(p) < 0)
        return -1;
    // @from 03.03
    if (s->kind != S_INSERT && s->kind != S_UPDATE && s->kind != S_DELETE)
        return schema_load(db);
    // @end
    return 0;
}

/* Prints the last error message on stderr. */
static void report(Db *db)
{
    fflush(db->out);
    fprintf(stderr, "Error: %s\n", errmsg);
}

/* Runs every statement in sql in order, stopping at the first error
 * (reported on stderr). Returns 0 or -1. */
int db_exec(Db *db, const char *sql)
{
    Parser ps;
    parser_init(&ps, sql, &db->stmt);
    for (;;) {
        Stmt *s;
        int rc = parse_statement(&ps, &s);
        if (rc == 0)
            break;
        if (rc > 0)
            rc = run_stmt(db, s);
        arena_reset(&db->rowa);  // @from 04.01
        arena_reset(&db->stmt);    /* the parser keeps nothing in it between statements */
        arena_reset(&db->once);    /* nor do subqueries keep answers */ // @from 08.06
        if (rc < 0) {
            report(db);
            return -1;
        }
    }
    return 0;
}

// @from 03.03
/* Opens the database file at path and loads the catalog. Returns 0 or -1. */
// @else
// /* Opens the database file at path. Returns 0 or -1. */
// @end
int db_open(Db *db, const char *path)
{
    memset(db, 0, sizeof *db);
    db->out = stdout;
    // @from 03.03
    if (pager_open(&db->pager, path) < 0 || schema_load(db) < 0) {
    // @else
    // if (pager_open(&db->pager, path) < 0) {
    // @end
        report(db);
        return -1;
    }
    return 0;
}

/* Closes the database; an open transaction is rolled back. */
void db_close(Db *db)
{
    if (db->in_txn)
        pager_rollback(&db->pager);
    pager_close(&db->pager);
}
