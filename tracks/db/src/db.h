/*
 * db.h - everything the engine's files share.
 *
 * The engine is a stack of layers, each built on the one below:
 *
 *   main.c      the shell: a REPL and one-shot mode
 *   exec.c      running each statement the parser hands over      @from 03.02
 *   plan.c      the plan of a query, and EXPLAIN                  @from 04.01
 *   expr.c      SQL values, and expressions over them             @from 04.01
 *   schema.c    the catalog, kept in the sqlite_schema table      @from 03.03
 *   parse.c     SQL text -> a statement tree                      @from 03.02
 *   tokenize.c  SQL text -> tokens                                @from 03.01
 *   btree.c     tables and indexes as B-trees of pages            @from 02.01
 *   record.c    rows as bytes: varints and serial types           @from 01.03
 *   pager.c     the file as numbered pages
 *   journal.c   the rollback journal: atomic commit, recovery     @from 06.02
 *   wal.c       the write-ahead log                               @from 06.04
 *   util.c      errors, memory, crash injection, counters
 *
 * The database file is a real SQLite database file: the sqlite3 shell can
 * open what we write, and we can open what it writes. The format is the
 * published one: https://www.sqlite.org/fileformat.html
 */
#ifndef DB_H
#define DB_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int64_t i64;
typedef uint64_t u64;

/* ------------------------------------------------------------ util.c */

// @internal
/* Stands in for code a learner's workspace has cut out. Names the lesson
 * whose code is missing and stops the process before anything is written
 * to the database file. */
_Noreturn void todo(const char *lesson, const char *what);
// @end

/* Something is wrong that the engine cannot recover from (an I/O error, a
 * page that is not what the file says it is). Prints and exits. */
_Noreturn void fatal(const char *fmt, ...);

/* Sets the error message for the current statement and returns -1, so a
 * caller can write `return err("no such table: %s", name);`. */
int err(const char *fmt, ...);
extern char errmsg[512];

/* Crash injection. DB_CRASH=<point> in the environment kills the process
 * with SIGKILL the first time it reaches crash_point(<point>);
 * DB_CRASH=<point>:<n> on the n-th time. crash_armed() says whether the
 * next crash_point(<point>) would fire, for torn writes. */
void crash_point(const char *point);
int crash_armed(const char *point);

/* Counters, printed to stderr at exit when DB_STATS=1. */
struct stats {
    u64 pages_read, pages_written, cache_hits, cache_misses, evictions;
    u64 fsyncs, journal_pages, wal_frames, checkpoints;
    u64 splits, append_splits, merges;
};
extern struct stats stats;
void stats_print(void);

void *xmalloc(size_t n);
void *xcalloc(size_t n, size_t m);
void *xrealloc(void *p, size_t n);
char *xstrndup(const char *s, size_t n);

/* An arena hands out memory that is all freed at once, by arena_reset():
 * nothing allocated from it is freed on its own. */
typedef struct Arena {
    struct Chunk *head;
} Arena;
void *arena_alloc(Arena *a, size_t n);
char *arena_strndup(Arena *a, const char *s, size_t n);
void arena_reset(Arena *a);

/* A growable byte buffer. */
typedef struct Buf {
    u8 *p;
    size_t n, cap;
} Buf;
void buf_reserve(Buf *b, size_t n);
void buf_put(Buf *b, const void *data, size_t n);
void buf_free(Buf *b);

/* Big-endian integers, the byte order of every number in the file. */
static inline u32 get2(const u8 *p) { return (u32)p[0] << 8 | p[1]; }
static inline u32 get4(const u8 *p) { return (u32)p[0] << 24 | (u32)p[1] << 16 | (u32)p[2] << 8 | p[3]; }
static inline void put2(u8 *p, u32 v) { p[0] = (u8)(v >> 8); p[1] = (u8)v; }
static inline void put4(u8 *p, u32 v) { p[0] = (u8)(v >> 24); p[1] = (u8)(v >> 16); p[2] = (u8)(v >> 8); p[3] = (u8)v; }

int sys_fsync(int fd);                 /* fsync(2), counted */
int fsync_dir(const char *path);       /* fsync the directory holding path */

/* ------------------------------------------------------------ pager.c */

enum { JOURNAL_DELETE, JOURNAL_WAL, JOURNAL_OFF };

typedef struct Page {
    u32 pgno;
    int dirty;
    u32 stmt_gen;                /* statement that last saved a copy of it */
    // @from 01.02
    struct Page *hnext;          /* hash chain */
    struct Page *prev, *next;    /* LRU list of clean pages; NULL while dirty */
    // @end
    struct Page *dnext;          /* dirty list */
    u8 *data;
} Page;

struct Wal;  // @from 06.04

typedef struct Pager {
    int fd;
    char *path;
    u32 page_size;
    u32 usable;                  /* page_size minus the reserved bytes at the end */
    u32 npages;                  /* pages in the database, with this transaction's growth */
    u32 npages_orig;             /* pages when the transaction began */
    int journal_mode;
    struct Wal *wal;  // @from 06.04

    // @from 01.02
    /* The page cache. */
    Page **hash;
    u32 nhash;
    u32 ncached;
    u32 cache_max;               /* clean pages kept; dirty pages are never evicted */
    Page lru;                    /* sentinel of the LRU list */
    // @end
    Page *dirty;                 /* every dirty page, newest first */
    u32 ndirty;

    /* Statement savepoint: copies of pages as they were before the
     * statement, so a failed statement inside BEGIN can be undone alone. */
    int stmt_active;
    u32 stmt_gen;
    u32 stmt_npages;
    struct Saved { u32 pgno; u8 *data; } *saved;
    u32 nsaved, saved_cap;
} Pager;

#define DEFAULT_PAGE_SIZE 4096
// @from 01.02
#define DEFAULT_CACHE_PAGES 500   /* 2 MB of 4 KB pages, like sqlite3's default cache_size=-2000 */
// @end
#define SQLITE_VERSION_STAMP 3046000

int pager_open(Pager *p, const char *path);
void pager_close(Pager *p);
u8 *pager_get(Pager *p, u32 pgno);      /* page data, to read */
u8 *pager_write(Pager *p, u32 pgno);    /* same, and marks the page dirty */
void pager_shrink(Pager *p);            /* evict clean pages down to cache_max */ // @from 01.02
void header_init(Pager *p);             /* give an empty file its page 1 */
int pager_commit(Pager *p);
void pager_rollback(Pager *p);
void pager_stmt_begin(Pager *p);
void pager_stmt_end(Pager *p);
void pager_stmt_rollback(Pager *p);
int pager_set_journal_mode(Pager *p, int mode);  // @from 06.02
void read_page(Pager *p, u32 pgno, u8 *buf);       /* straight from the database file */
void write_page(Pager *p, u32 pgno, const u8 *buf);
void pager_drop(Pager *p, u32 pgno);    /* forget a cached page (it was freed) */ // @from 01.02

// @from 06.02
/* ------------------------------------------------------------ journal.c */

int journal_commit(Pager *p, Page **pages, u32 n);
int journal_recover(Pager *p);  // @from 06.03
char *journal_path(Pager *p);
// @end

// @from 06.04
/* ------------------------------------------------------------ wal.c */

typedef struct Wal {
    int fd;
    char *path;
    int bigendian;               /* checksum byte order: magic 0x377f0683 */
    u32 salt1, salt2, ckpt_seq;
    u32 s0, s1;                  /* checksum of the last committed frame */
    u32 nframes;                 /* frames up to and including the last commit */
    u32 db_size;                 /* database size in pages after that commit */
    u32 *frame_of;               /* pgno -> newest frame holding it (1-based), 0 if none */
    u32 frame_of_cap;
} Wal;

int wal_open(Pager *p);
int wal_read(Pager *p, u32 pgno, u8 *buf);   /* 1 if the WAL has the page */
int wal_commit(Pager *p, Page **pages, u32 n);
int wal_checkpoint(Pager *p);
void wal_close(Pager *p, int checkpoint);
#define WAL_AUTOCHECKPOINT 1000   /* frames; the same default as sqlite3 */
// @end

// @from 01.03
/* ------------------------------------------------------------ record.c */

enum { V_NULL, V_INT, V_REAL, V_TEXT, V_BLOB };

/* One SQL value. Text and blobs point at bytes owned by someone else (a
 * page, a record buffer, an arena); s is not NUL-terminated. */
typedef struct Value {
    int type;
    i64 i;
    double r;
    const char *s;
    int n;
} Value;

int varint_get(const u8 *p, u64 *v);
int varint_put(u8 *p, u64 v);
int varint_len(u64 v);
u32 serial_type(const Value *v);
u32 serial_size(u32 type);
void serial_get(u32 type, const u8 *p, Value *v);
void serial_put(u32 type, const Value *v, u8 *p);
void record_build(Buf *out, const Value *vals, int n);
int record_decode(const u8 *rec, u32 len, Value *out, int max);
int record_count(const u8 *rec, u32 len);
int record_compare(const u8 *a, u32 alen, const u8 *b, u32 blen, int nfields);  // @from 02.01
// @end

// @from 02.01
/* ------------------------------------------------------------ btree.c */
// @end

enum {
    PAGE_INDEX_INTERIOR = 2,
    PAGE_TABLE_INTERIOR = 5,
    PAGE_INDEX_LEAF = 10,
    PAGE_TABLE_LEAF = 13,
};

// @from 02.01
#define MAX_DEPTH 20

/* A position in a B-tree: the path of pages from the root down. At each
 * level, idx is the cell we are at; on the levels above the last, it is
 * the child we went down into (ncells means the right-most child). */
typedef struct Cursor {
    Pager *pager;
    u32 root;
    int intkey;                  /* a table (rowid keys) or an index */
    int depth;                   /* levels in the path; 0 = not positioned */
    u32 pgno[MAX_DEPTH];
    int idx[MAX_DEPTH];
    int valid;                   /* at an entry */
    i64 rowid;                   /* the entry's rowid (tables) */
    const u8 *payload;           /* the entry's payload (record) */
    u32 npayload;
    Buf buf;                     /* holds a payload that spilled to overflow pages */
} Cursor;

u32 btree_create(Pager *p, int intkey);  // @from 02.02
void btree_drop(Pager *p, u32 root);  // @from 02.05
void cursor_open(Cursor *c, Pager *p, u32 root, int intkey);  // @from 02.03
void cursor_close(Cursor *c);  // @from 02.03
int cursor_first(Cursor *c);  // @from 02.04
int cursor_next(Cursor *c);  // @from 02.04
int cursor_seek_rowid(Cursor *c, i64 rowid);  // @from 02.04
int cursor_seek_key(Cursor *c, const u8 *key, u32 n, int nfields, int bias);  // @from 02.04
void btree_insert(Cursor *c, i64 rowid, const u8 *payload, u32 n);  // @from 02.03
void btree_delete(Cursor *c);  // @from 02.05
i64 btree_max_rowid(Cursor *c);  // @from 02.03
u32 page_alloc(Pager *p);  // @from 02.02
void page_free(Pager *p, u32 pgno);  // @from 02.05
// @end

// @from 03.01
/* ------------------------------------------------------------ tokenize.c */

enum {
    TK_EOF, TK_ILLEGAL, TK_SPACE,
    TK_SEMI, TK_LP, TK_RP, TK_COMMA, TK_DOT, TK_STAR, TK_PLUS, TK_MINUS,
    TK_SLASH, TK_REM, TK_CONCAT, TK_EQ, TK_NE, TK_LT, TK_LE, TK_GT, TK_GE,
    TK_INTEGER, TK_FLOAT, TK_STRING, TK_BLOB, TK_ID,
    /* keywords */
    TK_FIRST_KEYWORD,
    TK_AND, TK_AS, TK_ASC, TK_BEGIN, TK_BETWEEN, TK_BY, TK_CHECK, TK_COLLATE,
    TK_COMMIT, TK_CONSTRAINT, TK_CREATE, TK_DEFAULT, TK_DEFERRED, TK_DELETE, TK_DESC,
    TK_DISTINCT, TK_DROP, TK_END, TK_EXCLUSIVE, TK_EXISTS, TK_EXPLAIN, TK_FOREIGN,
    TK_FROM, TK_GLOB, TK_GROUP, TK_HAVING, TK_IF, TK_IMMEDIATE, TK_IN, TK_INDEX,
    TK_INSERT, TK_INTO, TK_IS, TK_ISNULL, TK_JOIN, TK_KEY, TK_LIKE, TK_LIMIT,
    TK_NOT, TK_NOTNULL, TK_NULL, TK_OFFSET, TK_ON, TK_OR, TK_ORDER, TK_PLAN,
    TK_PRAGMA, TK_PRIMARY, TK_QUERY, TK_REFERENCES, TK_REPLACE, TK_ROLLBACK,
    TK_SELECT, TK_SET, TK_TABLE, TK_TRANSACTION, TK_UNION, TK_UNIQUE, TK_UPDATE,
    TK_VALUES, TK_WHERE, TK_WITHOUT, TK_AUTOINCREMENT,
};

typedef struct Token {
    int type;
    const char *s;
    int n;
} Token;

int next_token(const char *z, Token *t);
int keyword_type(const char *s, int n);
const char *token_name(int type);
int sql_complete(const char *sql);
// @end

// @from 03.02
/* ------------------------------------------------------------ parse.c */

enum {
    E_NULL, E_INT, E_REAL, E_STR, E_BLOB, E_COLUMN, E_ROWID,
    E_NEG, E_NOT, E_PLUS,
    E_OR, E_AND, E_EQ, E_NE, E_LT, E_LE, E_GT, E_GE, E_IS, E_ISNOT,
    E_ADD, E_SUB, E_MUL, E_DIV, E_REM, E_CONCAT,
    E_ISNULL, E_NOTNULL, E_BETWEEN, E_NOTBETWEEN, E_IN, E_NOTIN, E_LIKE, E_NOTLIKE,
    E_FUNC,
};

typedef struct Expr {
    int op;
    Value v;                     /* literals */
    const char *name;            /* column or function name */
    const char *qual;            /* table name before a dot, or NULL */
    int col;                     /* resolved column index (E_COLUMN) */
    // @from 08.01
    int tab;                     /* E_COLUMN: the FROM item it is bound to */
    int tcol;                    /* and its column in that item's table, or TCOL_ROWID */
    // @end
    int aff;                     /* a column's affinity, or -1: no affinity */
    struct Expr *a, *b, *c;      /* operands; c is BETWEEN's upper bound */
    struct Expr **list;          /* IN list and function arguments */
    int nlist;
} Expr;

typedef struct ColumnDef {
    const char *name;
    const char *type;            /* declared type, as written, or "" */
    int primary_key;
    int not_null;
    Expr *dflt;
} ColumnDef;

// @from 08.07
typedef struct Unique {          /* a UNIQUE or PRIMARY KEY constraint of CREATE TABLE */
    const char **names;          /* its columns, in the order written */
    int nnames;
    int primary_key;
    int column;                  /* written on a column, not after the columns */
    int desc;                    /* a column of it is DESC */
} Unique;
// @end

typedef struct OrderTerm {
    Expr *e;
    int desc;
} OrderTerm;

typedef struct ResultCol {
    Expr *e;                     /* NULL for * */
    const char *alias;
    const char *star_of;         /* the x of x.*, or NULL */ // @from 08.01
} ResultCol;

// @from 08.01
#define MAX_FROM 64              /* tables in one FROM clause: SQLite's limit */
#define TCOL_ROWID (-1)          /* Expr.tcol of a name bound to a table's rowid */

typedef struct FromItem {        /* one table of a FROM clause */
    const char *table, *alias;
    struct Expr *on;             /* its ON, or NULL */
    struct Table *t;             /* bound by select_resolve() */
    int base;                    /* where its columns start in the joined row */
} FromItem;
// @end

enum {
    S_SELECT, S_INSERT, S_UPDATE, S_DELETE, S_CREATE_TABLE, S_CREATE_INDEX,
    S_DROP_TABLE, S_DROP_INDEX, S_BEGIN, S_COMMIT, S_ROLLBACK, S_PRAGMA,
};

typedef struct Stmt {
    int kind;
    int explain;                 /* 1 = EXPLAIN, 2 = EXPLAIN QUERY PLAN */
    const char *table;           /* the table the statement is about */
    const char *alias;
    // @from 08.01
    FromItem *from;              /* SELECT: the FROM clause; from[0] is table and alias */
    int nfrom;
    // @end
    const char *name;            /* CREATE INDEX / DROP: the object */
    int if_exists, if_not_exists;
    /* SELECT */
    ResultCol *cols;
    int ncols;
    Expr *where;
    OrderTerm *order;
    int norder;
    Expr *limit, *offset;
    /* INSERT: column names, then rows of values */
    const char **names;
    int nnames;
    Expr ***rows;
    int nrows;
    /* UPDATE: SET names[i] = sets[i] */
    Expr **sets;
    /* CREATE TABLE */
    ColumnDef *defs;
    int ndefs;
    // @from 08.07
    Unique *uniques;             /* its UNIQUE and PRIMARY KEY constraints, in the order written */
    int nuniques;
    // @end
    const char *unsupported;     /* a feature we parsed but do not support */
    /* CREATE INDEX: names[] are the indexed columns; unique */
    int unique;
    /* PRAGMA name [= value] */
    const char *pragma_value;
    const char *sql;             /* CREATE: the text stored in sqlite_schema */
} Stmt;

typedef struct Parser {
    const char *sql;             /* the whole input */
    const char *z;               /* where the next token starts */
    Token tok;                   /* the current token (not yet consumed) */
    Arena *arena;
} Parser;

void parser_init(Parser *ps, const char *sql, Arena *arena);
int parse_statement(Parser *ps, Stmt **out);   /* 1 = a statement, 0 = end of input, -1 = error */
Expr *parse_expr(Parser *ps);
// @end

// @from 03.03
/* ------------------------------------------------------------ schema.c */

enum { AFF_BLOB, AFF_TEXT, AFF_NUMERIC, AFF_INTEGER, AFF_REAL };

typedef struct Column {
    const char *name;
    const char *type;
    int affinity;
    int not_null;
    Expr *dflt;
    Value dflt_value;            /* dflt, evaluated: what rows stored before the column existed read as */
} Column;

struct Table;

typedef struct Index {
    const char *name;
    struct Table *table;
    u32 root;
    int ncols;
    int cols[8];                 /* column numbers in the table */
    int unique;                  /* no two rows hold the same values in its columns, NULLs aside */ // @from 08.07
    struct Index *next;
} Index;

typedef struct Table {
    const char *name;
    u32 root;
    int ncols;
    Column *cols;
    int rowid_col;               /* the INTEGER PRIMARY KEY column, or -1 */
    const char *readonly;        /* why we must not write it (features we lack), or NULL */
    const char *opaque;          /* we cannot even read it: why */
    const char *sql;
    Index *indexes;
    struct Table *next;
} Table;

typedef struct Schema {
    Arena arena;
    Table *tables;               /* the first one is sqlite_schema itself */
} Schema;

struct Db;
int schema_load(struct Db *db);
Table *find_table(struct Db *db, const char *name);
Index *find_index(struct Db *db, const char *name, Table **owner);
int affinity_of(const char *type);
int create_table(struct Db *db, Stmt *s);
int create_index(struct Db *db, Stmt *s);  // @from 05.01
int rowid_constraint(Stmt *s, const Unique *u);  /* the INTEGER PRIMARY KEY's column, or -1 */ // @from 08.07
int drop_object(struct Db *db, Stmt *s);
int table_refused(Table *t);    /* sets the error for a table we cannot write or read; returns -1 */
void schema_insert_row(struct Db *db, const char *type, const char *name, const char *tbl, u32 root, const char *sql);
void schema_bump_cookie(struct Db *db);
// @end

// @from 02.01
/* ------------------------------------------------------------ expr.c */
// @end

// @from 04.01
typedef struct Row {
    Value *cols;                 /* one per table column */
    int ncols;
    i64 rowid;
} Row;
// @end

int value_compare(const Value *a, const Value *b);  // @from 02.01
// @from 04.01
int value_truth(const Value *v);          /* 1 true, 0 false, -1 NULL */
void apply_affinity(Value *v, int aff, Arena *a);
int eval(struct Db *db, Expr *e, Row *row, Value *out);
void print_value(FILE *f, const Value *v);
void format_real(double r, char *buf, size_t n);
const char *expr_text(Arena *a, Expr *e);  // @from 04.02
int resolve_expr(Expr *e, Table *t, const char *alias);
// @from 08.01
/* The tables a query's names can refer to: its FROM clause. */
typedef struct Scope {
    FromItem *from;
    int nfrom;
} Scope;
int answers_to(FromItem *it, const char *q);
int resolve_names(struct Db *db, Expr *e, Scope *sc);
// @end
int is_constant(Expr *e);

/* ------------------------------------------------------------ plan.c, exec.c */

// @from 05.02
enum { ACCESS_SCAN, ACCESS_ROWID_EQ, ACCESS_ROWID_RANGE, ACCESS_INDEX_EQ, ACCESS_INDEX_RANGE };

/* How a statement reads its table: which B-tree, and the bounds. */
typedef struct Access {
    int kind;
    Index *index;
    Expr *lo, *hi;               /* constant bounds, or NULL */
    int lo_incl, hi_incl;
} Access;
// @end

typedef struct Op Op;
struct Op {
    const char *name;            /* for EXPLAIN: the operator's name, "Scan" for one */
    const char *detail;          /* and what it works on */
    int (*next)(Op *op, Row **out);   /* 1 = a row, 0 = no more, -1 = error */
    Op *child;
    struct Db *db;
    Table *table;
    Row row;                     /* the row a scan produces */
    Cursor cur;                  /* the table's cursor */
    Cursor icur;                 /* an index's cursor */ // @from 05.02
    int started, done;
    Access acc;  // @from 05.02
    // @from 05.02
    int has_lo, has_hi;          /* range scans: which bounds there are */
    i64 lo_i, hi_i;              /* rowid bounds, inclusive */
    Value hi;                    /* index scans: the upper bound, inclusive */
    Buf key;                     /* index scans: the lower bound, as a key */
    // @end
    Expr *pred;                  /* Filter */ // @from 04.02
    // @from 04.03
    OrderTerm *order;            /* Sort */
    int norder;
    struct SortRow *rows;
    i64 nrows, pos;
    Arena sort_arena;
    i64 limit, offset, seen;     /* Limit */
    // @end
    // @from 08.01
    Op *inner;                   /* Join: the table it reads once per outer row */
    Arena hold;                  /* Join: the outer row's text and blobs, kept */
    int have_outer;              /* Join: an outer row is in the first lwidth slots */
    int lwidth;                  /* Join: slots taken by the tables before the inner one */
    // @end
};

// @from 08.01
/* A SELECT, bound and ready to plan. */
typedef struct Query {
    Stmt *s;
    Scope scope;
    Expr **cols;                 /* the result expressions, * expanded */
    int ncols;
    int width;                   /* values in a row of its FROM: every table's columns and rowid */
} Query;
// @end

typedef struct Plan {
    Op *root;
    Access acc;  // @from 05.02
    int sorted;                  /* a Sort operator is in the plan */ // @from 04.03
    // @from 08.01
    Query *q;                    /* the query it answers */
    Access *jacc;                /* a join: how each FROM item is read */
    // @end
} Plan;

int choose_access(Table *t, Expr *where, Access *acc);  // @from 05.03
int sort_needed(Table *t, Access *acc, OrderTerm *order, int norder);  // @from 05.03
int plan_query(struct Db *db, Table *t, Expr *where, OrderTerm *order, int norder,
               Expr *limit, Expr *offset, Plan *plan);
void explain_query_plan(struct Db *db, Stmt *s, Table *t, Plan *plan);  // @from 05.03
void explain_tree(struct Db *db, Stmt *s, Plan *plan);
// @from 08.01
int plan_select(struct Db *db, Query *q, Plan *plan);
void explain_join_plan(struct Db *db, Plan *plan);
// @end
// @from 05.02
Op *op_scan(struct Db *db, Table *t, Access *acc);
// @else
// Op *op_scan(struct Db *db, Table *t);
// @end
Op *op_filter(struct Db *db, Op *child, Expr *pred);  // @from 04.02
Op *op_sort(struct Db *db, Op *child, OrderTerm *order, int norder);  // @from 04.03
Op *op_limit(struct Db *db, Op *child, i64 limit, i64 offset);  // @from 04.03
Op *op_join(struct Db *db, Op *left, Op *inner, FromItem *item, Table *left_table, int width);  // @from 08.01
void op_close(Op *op);
// @end

typedef struct Db {
    Pager pager;
    Schema schema;  // @from 03.03
    // @from 03.02
    int in_txn;                  /* inside BEGIN ... COMMIT */
    Arena stmt;                  /* this statement's parse tree and plan */
    // @end
    Arena rowa;                  /* values computed for the current row */ // @from 04.01
    FILE *out;  // @from 03.02
} Db;

int db_open(Db *db, const char *path);
void db_close(Db *db);
int db_exec(Db *db, const char *sql);
void index_key(Index *ix, Row *row, Buf *out);  // @from 05.01
int index_build(Db *db, Index *ix);  // @from 05.01
void decode_row(Table *t, Cursor *c, Row *row);  // @from 04.01

#endif
