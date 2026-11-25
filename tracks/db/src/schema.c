/*
 * schema.c - the catalog.
 *
 * The database describes itself. Page 1 is the root of a table like any
 * other, sqlite_schema, with one row per table and index:
 *
 *   type      'table' or 'index' (sqlite3 also writes 'view' and 'trigger')
 *   name      the table's or index's name
 *   tbl_name  the table it belongs to (for a table, itself)
 *   rootpage  the page number of its B-tree's root
 *   sql       the CREATE statement that made it
 *
 * So the catalog in memory is rebuilt by reading that table and parsing
 * each CREATE statement again: the column names, types and constraints
 * are nowhere else. CREATE TABLE is "allocate a root page and insert a
 * row into sqlite_schema"; DROP TABLE is the reverse.
 *
 * Schema rows written by sqlite3 may use features we do not support
 * (UNIQUE, AUTOINCREMENT, triggers, ...). Such a table is still readable,
 * but writing to it could break what sqlite3 expects, so it is read-only.
 */
#include <ctype.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "db.h"

/* Returns the column affinity for a declared type, by SQLite's rules: the
 * first of INT, CHAR/CLOB/TEXT, BLOB (or no type), REAL/FLOA/DOUB that
 * occurs as a substring, else NUMERIC. */
int affinity_of(const char *type)
{
    char up[256];
    size_t n = strlen(type);
    if (n >= sizeof up)
        n = sizeof up - 1;
    for (size_t i = 0; i < n; i++)
        up[i] = (char)toupper((unsigned char)type[i]);
    up[n] = 0;
    if (strstr(up, "INT"))
        return AFF_INTEGER;
    if (strstr(up, "CHAR") || strstr(up, "CLOB") || strstr(up, "TEXT"))
        return AFF_TEXT;
    if (strstr(up, "BLOB") || n == 0)
        return AFF_BLOB;
    if (strstr(up, "REAL") || strstr(up, "FLOA") || strstr(up, "DOUB"))
        return AFF_REAL;
    return AFF_NUMERIC;
}

/* Case-insensitive lookups. sqlite_master is the old name of sqlite_schema. */
Table *find_table(Db *db, const char *name)
{
    if (strcasecmp(name, "sqlite_master") == 0)
        name = "sqlite_schema";
    for (Table *t = db->schema.tables; t; t = t->next)
        if (strcasecmp(t->name, name) == 0)
            return t;
    return NULL;
}

/* As find_table, for indexes; *owner (if non-NULL) receives the table. */
Index *find_index(Db *db, const char *name, Table **owner)
{
    for (Table *t = db->schema.tables; t; t = t->next)
        for (Index *ix = t->indexes; ix; ix = ix->next)
            if (strcasecmp(ix->name, name) == 0) {
                if (owner)
                    *owner = t;
                return ix;
            }
    return NULL;
}

/* Two reasons a table cannot be used are not a missing feature but SQL
 * the parser rejected. They already say what is wrong, so an error
 * quotes them without "which this engine does not support". */
static const char UNPARSED_TABLE[] = "SQL this engine cannot parse";
static const char UNPARSED_INDEX[] = "an index this engine cannot parse";

/* Reports why table t cannot be used (opaque) or written (read-only) and
 * returns -1 like err(). */
int table_refused(Table *t)
{
    const char *why = t->opaque ? t->opaque : t->readonly;
    const char *tail = why == UNPARSED_TABLE || why == UNPARSED_INDEX ? "" : ", which this engine does not support";
    if (t->opaque)
        return err("table %s uses %s%s", t->name, why, tail);
    return err("table %s is read-only here: it uses %s%s", t->name, why, tail);
}

/* Copies n bytes of s into the schema arena (an empty string if s is
 * NULL). */
static char *keep_str(Schema *sc, const char *s, int n)
{
    return s ? arena_strndup(&sc->arena, s, (size_t)n) : arena_strndup(&sc->arena, "", 0);
}

// @from 08.07
/* Returns the column number of the INTEGER PRIMARY KEY if constraint u of
 * CREATE TABLE s is one, else -1. A PRIMARY KEY of one column declared
 * exactly INTEGER is the rowid under another name and gets no index; on the
 * column as PRIMARY KEY DESC it is an ordinary column (build.c,
 * sqlite3AddPrimaryKey). */
int rowid_constraint(Stmt *s, const Unique *u)
{
    if (!u->primary_key || u->nnames != 1 || (u->column && u->desc))
        return -1;
    for (int i = 0; i < s->ndefs; i++)
        if (strcasecmp(s->defs[i].name, u->names[0]) == 0)
            return strcasecmp(s->defs[i].type, "INTEGER") == 0 ? i : -1;
    return -1;
}

static void add_index(Table *t, Index *ix);

/* Gives table t the automatic indexes sqlite3 makes for the UNIQUE and
 * PRIMARY KEY constraints of its CREATE TABLE s, in the order they are
 * written, each named sqlite_autoindex_<table>_<n> with n one more than
 * the indexes already made. The INTEGER PRIMARY KEY gets none (the table's
 * own B-tree is its index), nor does a constraint on the same columns in
 * the same order as an earlier one, and neither uses up a number (build.c,
 * sqlite3CreateIndex). sqlite3 works the names out again each time it opens
 * the file and calls a row it cannot match an orphan index, so they must
 * be exactly its names. Root pages are left 0 for the caller. */
static void auto_indexes(Schema *sc, Stmt *s, Table *t)
{
    // @build 08.07 an automatic index for a constraint
    // Go through s->uniques, the constraints in the order written. Skip
    // the one that is the INTEGER PRIMARY KEY (rowid_constraint() >= 0).
    // For each other, make an Index in sc's arena: on table t, unique,
    // its columns the constraint's names looked up in t (ix->cols[k] is
    // the column's number, ix->ncols how many). Skip it, using up no
    // number, if an earlier constraint's index (t->indexes so far) has the
    // same columns in the same order. Else name it
    // sqlite_autoindex_<table>_<n>, n counting
    // 1, 2, ... over the indexes made here, and add it to t (add_index()).
    // Its root page stays 0: the caller writes the B-tree. Nothing to
    // return.
    int n = 0;
    for (int i = 0; i < s->nuniques; i++) {
        Unique *u = &s->uniques[i];
        if (rowid_constraint(s, u) >= 0)
            continue;
        Index *ix = arena_alloc(&sc->arena, sizeof *ix);
        ix->table = t;
        ix->unique = 1;
        ix->ncols = u->nnames;
        for (int k = 0; k < u->nnames; k++)
            for (int c = 0; c < t->ncols; c++)
                if (strcasecmp(t->cols[c].name, u->names[k]) == 0)
                    ix->cols[k] = c;
        int repeat = 0;
        for (Index *o = t->indexes; o; o = o->next)
            if (o->ncols == ix->ncols && memcmp(o->cols, ix->cols, (size_t)ix->ncols * sizeof(int)) == 0)
                repeat = 1;
        if (repeat)
            continue;
        size_t len = strlen(t->name) + 32;
        char *name = arena_alloc(&sc->arena, len);
        snprintf(name, len, "sqlite_autoindex_%s_%d", t->name, ++n);
        ix->name = name;
        add_index(t, ix);
    }
    // @end
}
// @end

/* Builds a Table from a parsed CREATE TABLE. Features the engine cannot
 * maintain mark the table read-only (or opaque) instead of failing. */
static Table *table_from(Schema *sc, Stmt *s, u32 root, const char *sql)
{
    Table *t = arena_alloc(&sc->arena, sizeof *t);
    t->name = s->table;
    t->root = root;
    t->sql = sql;
    t->ncols = s->ndefs;
    t->cols = arena_alloc(&sc->arena, (size_t)s->ndefs * sizeof(Column));
    t->rowid_col = -1;
    int pks = 0;
    for (int i = 0; i < s->ndefs; i++) {
        ColumnDef *d = &s->defs[i];
        Column *c = &t->cols[i];
        c->name = d->name;
        c->type = d->type;
        c->affinity = affinity_of(d->type);
        c->not_null = d->not_null;
        c->dflt = d->dflt;
        // @from 08.07
        // @else
        // if (d->primary_key) {
        //     pks++;
        //     /* Only a column declared exactly INTEGER becomes the rowid;
        //      * INT PRIMARY KEY is an ordinary column with a UNIQUE index. */
        //     if (strcasecmp(d->type, "INTEGER") == 0)
        //         t->rowid_col = i;
        //     else
        //         t->readonly = "a PRIMARY KEY that is not INTEGER PRIMARY KEY";
        // }
        // @end
    }
    // @from 08.07
    /* The INTEGER PRIMARY KEY is the rowid; every other UNIQUE or PRIMARY
     * KEY constraint is an index. A table that is read-only anyway gets
     * none: it is read by scanning. */
    int indexed = 0;
    for (int i = 0; i < s->nuniques; i++) {
        int col = rowid_constraint(s, &s->uniques[i]);
        if (col >= 0)
            t->rowid_col = col;
        else
            indexed = 1;
    }
    if (indexed && !s->unsupported)
        auto_indexes(sc, s, t);
    // @else
    // if (pks > 1) {
    //     t->rowid_col = -1;
    //     t->readonly = "a PRIMARY KEY of several columns";
    // }
    // @end
    if (s->unsupported)
        t->readonly = s->unsupported;
    if (s->unsupported && strcmp(s->unsupported, "WITHOUT ROWID") == 0)
        t->opaque = "WITHOUT ROWID";
    return t;
}

/* Appends to the end, keeping the order of sqlite_schema. */
static void add_table(Schema *sc, Table *t)
{
    Table **pp = &sc->tables;
    while (*pp)
        pp = &(*pp)->next;
    *pp = t;
}

// @from 05.01
/* Builds an Index from a parsed CREATE INDEX on table t; NULL if it is
 * one the engine cannot maintain (the table then becomes read-only). */
static Index *index_from(Schema *sc, Stmt *s, Table *t, u32 root)
{
    if (s->unsupported) {
        t->readonly = s->unsupported;
        return NULL;
    }
    Index *ix = arena_alloc(&sc->arena, sizeof *ix);
    ix->name = s->name;
    ix->table = t;
    ix->root = root;
    ix->ncols = s->nnames;
    ix->unique = s->unique;  // @from 08.07
    for (int i = 0; i < s->nnames; i++) {
        int c = -1;
        for (int k = 0; k < t->ncols; k++)
            if (strcasecmp(t->cols[k].name, s->names[i]) == 0)
                c = k;
        if (c < 0) {
            t->readonly = "an index on a column it does not have";
            return NULL;
        }
        ix->cols[i] = c;
    }
    return ix;
}

static void add_index(Table *t, Index *ix)
{
    Index **pp = &t->indexes;
    while (*pp)
        pp = &(*pp)->next;
    *pp = ix;
}
// @end

// @from 08.07
/* An index row with no sql is an automatic index: it gives the root page of
 * the one auto_indexes() made under that name, matched as sqlite3 matches it
 * (prepare.c, sqlite3InitCallback). A name that matches none, which sqlite3
 * calls an orphan index, makes the table read-only. */
static void auto_index_root(Table *t, const char *name, u32 root)
{
    for (Index *ix = t->indexes; ix; ix = ix->next)
        if (ix->unique && !ix->root && strcasecmp(ix->name, name) == 0) {
            ix->root = root;
            return;
        }
    if (!t->readonly && !t->opaque)
        t->readonly = "an automatic index that matches none of its constraints";
}

/* Drops the automatic indexes of t that no row of sqlite_schema gave a root
 * page (sqlite3 calls such a file malformed); the table becomes read-only. */
static void auto_index_check(Table *t)
{
    for (Index **pp = &t->indexes; *pp;) {
        if ((*pp)->root == 0) {
            *pp = (*pp)->next;
            if (!t->readonly)
                t->readonly = "a UNIQUE or PRIMARY KEY constraint whose index is missing";
        } else {
            pp = &(*pp)->next;
        }
    }
}
// @end

/* sqlite_schema itself is not described by any row, so its definition is
 * built in. */
static Table *builtin_schema_table(Schema *sc)
{
    static const char *names[] = {"type", "name", "tbl_name", "rootpage", "sql"};
    static const char *types[] = {"text", "text", "text", "int", "text"};
    Table *t = arena_alloc(&sc->arena, sizeof *t);
    t->name = "sqlite_schema";
    t->root = 1;
    t->ncols = 5;
    t->rowid_col = -1;
    t->cols = arena_alloc(&sc->arena, 5 * sizeof(Column));
    for (int i = 0; i < 5; i++) {
        t->cols[i].name = names[i];
        t->cols[i].type = types[i];
        t->cols[i].affinity = affinity_of(types[i]);
    }
    t->sql = "CREATE TABLE sqlite_schema(type text, name text, tbl_name text, rootpage int, sql text)";
    return t;
}

/* Parses one CREATE statement into the schema arena; NULL if it does not
 * parse. */
static Stmt *parse_schema_sql(Schema *sc, const char *sql)
{
    Parser ps;
    Stmt *s;
    parser_init(&ps, sql, &sc->arena);
    if (parse_statement(&ps, &s) != 1)
        return NULL;
    return s;
}

// @from 04.01
/* A row stored before ALTER TABLE ADD COLUMN (in sqlite3) has no value
 * for the new column, and reads as its DEFAULT, with the column's
 * affinity, as in sqlite3. Evaluated once per catalog load, so reading
 * such a row costs a copy, not an evaluation. */
static void column_default(Db *db, Column *col)
{
    Value v;
    memset(&v, 0, sizeof v);
    if (col->dflt && is_constant(col->dflt) && eval(db, col->dflt, NULL, &v) < 0)
        memset(&v, 0, sizeof v);
    if ((v.type == V_TEXT || v.type == V_BLOB) && v.n > 0)
        v.s = arena_strndup(&db->schema.arena, v.s, (size_t)v.n);
    apply_affinity(&v, col->affinity, &db->schema.arena);
    col->dflt_value = v;
}
// @end

/* Rebuilds the catalog from sqlite_schema. Tables are added as they are
 * met; indexes and triggers are applied afterwards, once their table is
 * known. */
int schema_load(Db *db)
{
    Schema *sc = &db->schema;
    arena_reset(&sc->arena);
    sc->tables = NULL;
    add_table(sc, builtin_schema_table(sc));
    if (db->pager.npages == 0)
        return 0;

    /* Indexes and triggers name their table, which may come later in
     * sqlite_schema: remember them for a second pass. */
    struct Later { char *type, *name, *tbl, *sql; u32 root; } *later = NULL;
    int nlater = 0, cap = 0;
    Cursor c;
    Value v[5];
    cursor_open(&c, &db->pager, 1, 1);
    // @build 03.03 read the catalog
    /* Text is copied with keep_str: the cursor's bytes change as it moves.
     * A table whose SQL does not parse is still listed, but opaque. */
    for (int more = cursor_first(&c); more; more = cursor_next(&c)) {
        int n = record_decode(c.payload, c.npayload, v, 5);
        if (n < 5)
            fatal("database is corrupt: bad row in sqlite_schema");
        char *type = keep_str(sc, v[0].s, v[0].type == V_TEXT ? v[0].n : 0);
        char *name = keep_str(sc, v[1].s, v[1].type == V_TEXT ? v[1].n : 0);
        char *tbl = keep_str(sc, v[2].s, v[2].type == V_TEXT ? v[2].n : 0);
        u32 root = v[3].type == V_INT ? (u32)v[3].i : 0;
        char *sql = v[4].type == V_TEXT ? keep_str(sc, v[4].s, v[4].n) : NULL;
        if (strcmp(type, "table") == 0) {
            Stmt *s = sql ? parse_schema_sql(sc, sql) : NULL;
            Table *t;
            if (!s || s->kind != S_CREATE_TABLE) {
                t = arena_alloc(&sc->arena, sizeof *t);
                t->name = name;
                t->root = root;
                t->sql = sql;
                t->rowid_col = -1;
                t->opaque = UNPARSED_TABLE;
            } else {
                t = table_from(sc, s, root, sql);
                t->name = name;
            }
            add_table(sc, t);
        } else {
            if (nlater == cap) {
                cap = cap ? 2 * cap : 16;
                later = xrealloc(later, (size_t)cap * sizeof *later);
            }
            later[nlater++] = (struct Later){type, name, tbl, sql, root};
        }
    }
    /* An index with no sql was made by sqlite3 for a UNIQUE or PRIMARY KEY
     * constraint; views are ignored. */
    for (int i = 0; i < nlater; i++) {
        Table *t = find_table(db, later[i].tbl);
        if (!t || t->root == 1)
            continue;
        if (strcmp(later[i].type, "index") == 0) {
            if (!later[i].sql) {
                // @from 08.07
                auto_index_root(t, later[i].name, later[i].root);
                // @else
                // t->readonly = "a UNIQUE or PRIMARY KEY constraint";
                // @end
                continue;
            }
            Stmt *s = parse_schema_sql(sc, later[i].sql);
            if (!s || s->kind != S_CREATE_INDEX) {
                t->readonly = UNPARSED_INDEX;
                continue;
            }
            // @from 05.01
            Index *ix = index_from(sc, s, t, later[i].root);
            if (ix) {
                ix->name = later[i].name;
                add_index(t, ix);
            }
            // @else
            // t->readonly = "indexes";
            // @end
        } else if (strcmp(later[i].type, "trigger") == 0) {
            t->readonly = "triggers";
        }
    }
    // @from 08.07
    for (Table *t = sc->tables; t; t = t->next)
        auto_index_check(t);
    // @end
    // @end
    cursor_close(&c);
    free(later);
    // @from 04.01
    for (Table *t = sc->tables; t; t = t->next)
        for (int i = 0; i < t->ncols; i++)
            column_default(db, &t->cols[i]);
    // @end
    return 0;
}

/* Appends a row describing a table or index to sqlite_schema. */
void schema_insert_row(Db *db, const char *type, const char *name, const char *tbl, u32 root, const char *sql)
{
    Value v[5];
    memset(v, 0, sizeof v);
    const char *texts[3] = {type, name, tbl};
    for (int i = 0; i < 3; i++) {
        v[i].type = V_TEXT;
        v[i].s = texts[i];
        v[i].n = (int)strlen(texts[i]);
    }
    v[3].type = V_INT;
    v[3].i = root;
    // @from 08.07
    if (sql) {                   /* an automatic index has none: NULL */
        v[4].type = V_TEXT;
        v[4].s = sql;
        v[4].n = (int)strlen(sql);
    }
    // @else
    // v[4].type = V_TEXT;
    // v[4].s = sql;
    // v[4].n = (int)strlen(sql);
    // @end
    Buf rec = {0};
    record_build(&rec, v, 5);
    Cursor c;
    cursor_open(&c, &db->pager, 1, 1);
    i64 rowid = btree_max_rowid(&c) + 1;
    btree_insert(&c, rowid, rec.p, (u32)rec.n);
    cursor_close(&c);
    buf_free(&rec);
}

/* The schema cookie (header offset 40) tells other connections that the
 * schema changed. It is bumped on every CREATE and DROP. */
void schema_bump_cookie(Db *db)
{
    u8 *h = pager_write(&db->pager, 1);
    put4(h + 40, get4(h + 40) + 1);
}

/* Tables and indexes share one namespace. */
static int name_taken(Db *db, const char *name)
{
    return find_table(db, name) || find_index(db, name, NULL);
}

/* Executes CREATE TABLE: refuses what the engine cannot honour, then
 * allocates an empty table B-tree and records it in sqlite_schema. The
 * caller reloads the catalog afterwards. */
int create_table(Db *db, Stmt *s)
{
    // @build 03.03 CREATE TABLE
    if (s->unsupported)
        return err("%s is not supported", s->unsupported);
    if (strncasecmp(s->table, "sqlite_", 7) == 0)
        return err("object name reserved for internal use: %s", s->table);
    for (int i = 0; i < s->ndefs; i++)
        for (int k = 0; k < i; k++)
            if (strcasecmp(s->defs[i].name, s->defs[k].name) == 0)
                return err("duplicate column name: %s", s->defs[i].name);
    if (name_taken(db, s->table)) {
        if (s->if_not_exists)
            return 0;
        if (find_table(db, s->table))
            return err("table %s already exists", s->table);
        return err("there is already an index named %s", s->table);
    }
    u32 root = btree_create(&db->pager, 1);
    schema_insert_row(db, "table", s->table, s->table, root, s->sql);
    // @from 08.07
    /* sqlite3 makes the automatic indexes right after the table: their
     * root pages come next, and their rows in sqlite_schema have no sql. */
    Table *t = table_from(&db->schema, s, root, s->sql);
    for (Index *ix = t->indexes; ix; ix = ix->next)
        schema_insert_row(db, "index", ix->name, s->table, btree_create(&db->pager, 0), NULL);
    // @end
    schema_bump_cookie(db);
    return 0;
    // @end
}

// @from 05.01
/* Executes CREATE INDEX: records the index in sqlite_schema, then fills
 * it from the table's existing rows. */
int create_index(Db *db, Stmt *s)
{
    if (s->unsupported)
        return err("%s are not supported", s->unsupported);
    if (strncasecmp(s->name, "sqlite_", 7) == 0)
        return err("object name reserved for internal use: %s", s->name);
    Table *t = find_table(db, s->table);
    if (!t)
        return err("no such table: main.%s", s->table);
    if (t->root == 1)
        return err("table %s may not be indexed", t->name);
    if (t->opaque || t->readonly)
        return table_refused(t);
    if (name_taken(db, s->name)) {
        if (s->if_not_exists)
            return 0;
        if (find_index(db, s->name, NULL))
            return err("index %s already exists", s->name);
        return err("there is already a table named %s", s->name);
    }
    for (int i = 0; i < s->nnames; i++) {
        int found = 0;
        for (int k = 0; k < t->ncols; k++)
            if (strcasecmp(t->cols[k].name, s->names[i]) == 0)
                found = 1;
        if (!found)
            return err("no such column: %s", s->names[i]);
    }
    u32 root = btree_create(&db->pager, 0);
    schema_insert_row(db, "index", s->name, t->name, root, s->sql);
    schema_bump_cookie(db);
    Index *ix = index_from(&db->schema, s, t, root);
    if (!ix)
        return err("cannot build index %s", s->name);
    return index_build(db, ix);
}
// @end

/* Executes DROP TABLE or DROP INDEX. DROP TABLE removes the table and
 * every index on it; DROP INDEX one index. Their pages go to the freelist
 * and their rows leave sqlite_schema. */
int drop_object(Db *db, Stmt *s)
{
    int table = s->kind == S_DROP_TABLE;
    if (table) {
        Table *t = find_table(db, s->name);
        if (!t) {
            if (s->if_exists)
                return 0;
            return err("no such table: %s", s->name);
        }
        if (t->root == 1)
            return err("table %s may not be dropped", t->name);
    } else {
        // @from 08.07
        Index *ix = find_index(db, s->name, NULL);
        if (ix && strncasecmp(ix->name, "sqlite_autoindex_", 17) == 0)
            return err("index associated with UNIQUE or PRIMARY KEY constraint cannot be dropped");
        // @end
        if (!find_index(db, s->name, NULL)) {
            if (s->if_exists)
                return 0;
            return err("no such index: %s", s->name);
        }
    }
    /* Matching rows are collected first and deleted after the scan, so the
     * cursor is not disturbed while it walks. */
    i64 ids[1024];
    u32 roots[1024];
    int n = 0;
    Cursor c;
    Value v[5];
    cursor_open(&c, &db->pager, 1, 1);
    for (int more = cursor_first(&c); more; more = cursor_next(&c)) {
        if (record_decode(c.payload, c.npayload, v, 5) < 5)
            fatal("database is corrupt: bad row in sqlite_schema");
        const Value *key = table ? &v[2] : &v[1];
        int match = key->type == V_TEXT && (int)strlen(s->name) == key->n &&
                    strncasecmp(key->s, s->name, (size_t)key->n) == 0;
        if (!table)
            match = match && v[0].type == V_TEXT && v[0].n == 5 && memcmp(v[0].s, "index", 5) == 0;
        if (match && n < 1024) {
            ids[n] = c.rowid;
            roots[n] = v[3].type == V_INT ? (u32)v[3].i : 0;
            n++;
        }
    }
    for (int i = 0; i < n; i++) {
        if (roots[i] > 1)
            btree_drop(&db->pager, roots[i]);
        if (cursor_seek_rowid(&c, ids[i]) && c.rowid == ids[i])
            btree_delete(&c);
    }
    cursor_close(&c);
    schema_bump_cookie(db);
    return 0;
}
