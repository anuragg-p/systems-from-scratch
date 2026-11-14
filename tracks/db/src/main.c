/*
 * main.c - the shell.
 *
 *   ./db file.db                 a REPL: type SQL ending in ;, or a dot-command
 *   ./db file.db "select ..."    run the SQL (or one dot-command) and exit,
 *                                non-zero on an error
 *   ./db -interactive file.db    a REPL with prompts even on a pipe
 *
 * Results print like sqlite3's default "list" mode: one row per line, @from 04.01
 * columns separated by |, NULL as nothing. @from 04.01
 * A dot-command is a line that starts with a dot; .help lists them.
 *
 * Environment variables:
 *   DB_STATS=1         prints the engine's counters to stderr at exit
 *   DB_CRASH=<point>   kills the process (SIGKILL) at a named point of a
 *                      commit; <point>:<n> kills it the n-th time the
 *                      point is reached
 *   DB_CACHE_PAGES=<n> sizes the page cache (default 500 pages) @from 01.02
 *   DB_PAGE_SIZE=<n>   page size of a newly created file (a power of two,
 *                      512 to 65536; default 4096)
 */
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>

#include "db.h"

static Db db;
static int interactive;

// @from 03.02
// @else
// /* Without a SQL front end the shell can only open the file: every
//  * statement is refused. */
// int db_open(Db *db, const char *path)
// {
//     memset(db, 0, sizeof *db);
//     if (pager_open(&db->pager, path) < 0) {
//         fprintf(stderr, "Error: %s\n", errmsg);
//         return -1;
//     }
//     return 0;
// }
//
// int db_exec(Db *db, const char *sql)
// {
//     (void)db;
//     (void)sql;
//     fflush(stdout);
//     fprintf(stderr, "Error: SQL is not supported\n");
//     return -1;
// }
//
// void db_close(Db *db)
// {
//     pager_close(&db->pager);
// }
// @end

static void print_stats(void)
{
    stats_print();
}

// @from 03.03
/* .tables: user tables, one per line; sqlite_* internals are hidden. */
static void cmd_tables(void)
{
    for (Table *t = db.schema.tables; t; t = t->next)
        if (strncasecmp(t->name, "sqlite_", 7) != 0)
            printf("%s\n", t->name);
}

/* .schema [table]: the CREATE statements, all of them or one table's. */
static void cmd_schema(const char *only)
{
    if (!only || !*only) {
        // @from 04.02
        db_exec(&db, "SELECT sql || ';' FROM sqlite_schema WHERE sql IS NOT NULL");
        // @else
        // for (Table *t = db.schema.tables; t; t = t->next)
        //     if (t->root != 1)
        //         cmd_schema(t->name);
        // @end
    } else {
        /* The table's CREATE, then its indexes', found by scanning
         * sqlite_schema (root page 1) for rows of type "index" whose
         * tbl_name is this table. */
        for (Table *t = db.schema.tables; t; t = t->next) {
            if (strcasecmp(t->name, only) != 0 || !t->sql || t->root == 1)
                continue;
            printf("%s;\n", t->sql);
            Cursor c;
            Value v[5];
            cursor_open(&c, &db.pager, 1, 1);
            for (int more = cursor_first(&c); more; more = cursor_next(&c)) {
                if (record_decode(c.payload, c.npayload, v, 5) < 5 || v[0].type != V_TEXT)
                    continue;
                if (v[0].n == 5 && memcmp(v[0].s, "index", 5) == 0 && v[2].type == V_TEXT &&
                    (size_t)v[2].n == strlen(only) && strncasecmp(v[2].s, only, (size_t)v[2].n) == 0 &&
                    v[4].type == V_TEXT)
                    printf("%.*s;\n", v[4].n, v[4].s);
            }
            cursor_close(&c);
        }
    }
}
// @end

/* A line starting with a dot. Returns 1 to exit the shell. */
static int dot_command(char *line)
{
    char *cmd = strtok(line, " \t\r\n");
    char *arg = strtok(NULL, " \t\r\n");  // @from 03.03
    if (!cmd)
        return 0;
    if (strcmp(cmd, ".exit") == 0 || strcmp(cmd, ".quit") == 0)
        return 1;
    // @from 03.03
    if (strcmp(cmd, ".tables") == 0)
        cmd_tables();
    else if (strcmp(cmd, ".schema") == 0)
        cmd_schema(arg);
    else if (strcmp(cmd, ".help") == 0)
        printf(".tables          list the tables\n"
               ".schema [table]  show the CREATE statements\n"
               ".exit            leave\n");
    // @else
    // if (strcmp(cmd, ".help") == 0)
    //     printf(".exit            leave\n");
    // @end
    else
        fprintf(stderr, "Error: unknown command: %s (try .help)\n", cmd);
    return 0;
}

/* Runs SQL read from stdin until EOF or .exit. A statement may span
 * lines. Dot-commands are recognized only at the start of a statement.
 * Returns 1 if the script should exit non-zero. */
static int repl(void)
{
    char *line = NULL;
    size_t cap = 0;
    Buf sql = {0};
    int failed = 0;
    if (interactive)
        printf("db: a SQL database, from scratch. Statements end with ;  .help for help\n");
    for (;;) {
        if (interactive) {
            fputs(sql.n ? "   ...> " : "db> ", stdout);
            fflush(stdout);
        }
        ssize_t n = getline(&line, &cap, stdin);
        if (n < 0)
            break;
        if (sql.n == 0) {
            char *p = line;
            while (*p == ' ' || *p == '\t')
                p++;
            if (*p == '.') {
                if (dot_command(p))
                    break;
                fflush(stdout);
                continue;
            }
            if (*p == '\n' || *p == 0)
                continue;
        }
        buf_put(&sql, line, (size_t)n);
        buf_put(&sql, "", 1);           /* keep it a C string */
        sql.n--;
        // @from 03.01
        /* It runs once it ends with a semicolon that is not inside a
         * string, a quoted name or a comment. */
        if (sql_complete((const char *)sql.p)) {
        // @else
        // /* It runs once its text holds a semicolon, wherever that is:
        //  * even one inside a string ends it. */
        // if (strchr((const char *)sql.p, ';')) {
        // @end
            if (db_exec(&db, (const char *)sql.p) < 0)
                failed = 1;
            sql.n = 0;
            if (interactive)
                fflush(stdout);
        }
    }
    if (sql.n) {
        buf_put(&sql, "", 1);
        if (db_exec(&db, (const char *)sql.p) < 0)
            failed = 1;
    }
    free(line);
    buf_free(&sql);
    /* As in sqlite3, a script that hit an error exits 1; a person at the
     * prompt saw the errors already. */
    return failed && !interactive;
}

int main(int argc, char **argv)
{
    int i = 1;
    if (i < argc && strcmp(argv[i], "-interactive") == 0) {
        interactive = 1;
        i++;
    }
    if (i >= argc || argc - i > 2) {
        fprintf(stderr, "usage: db [-interactive] FILE [SQL]\n");
        return 2;
    }
    const char *path = argv[i];
    const char *oneshot = i + 1 < argc ? argv[i + 1] : NULL;
    if (getenv("DB_STATS") && strcmp(getenv("DB_STATS"), "1") == 0)
        atexit(print_stats);
    if (!oneshot && isatty(0))
        interactive = 1;
    if (db_open(&db, path) < 0)
        return 1;
    int rc = 0;
    if (oneshot && oneshot[0] == '.') {
        char *cmd = xstrndup(oneshot, strlen(oneshot));
        dot_command(cmd);
        free(cmd);
    } else if (oneshot) {
        rc = db_exec(&db, oneshot) < 0;
    } else {
        rc = repl();
    }
    fflush(stdout);
    db_close(&db);
    return rc;
}
