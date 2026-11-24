/* api.h: the editor's API, what a script can ask of kilo.
 *
 * kilo.c defines the functions and the table of them (API, in its section
 * "The API"); script.c hands each one to Lua as kilo.api.NAME. Between the
 * two are only the types below: kilo.c knows nothing of Lua, and script.c
 * nothing of the editor's rows. Neovim's API is built the same way, around
 * its own small set of types (Object). */

#ifndef KILO_API_H
#define KILO_API_H

#include <stddef.h>

#define API_MAX_ARGS 5              /* the most arguments a function may take */

/* The types the API speaks. Rows and columns count from 0, a column is a
 * byte of its row, and a range of rows [start, end) holds start but not
 * end. */
typedef enum {
    API_NIL,            /* no value: a function that returns nothing */
    API_BOOLEAN,
    API_INTEGER,
    API_STRING,         /* bytes and their length; any byte, '\0' too */
    API_LINES,          /* a list of strings: rows of the file */
    API_POSITION,       /* a row and a column */
    API_FUNCTION        /* a script's function, kept as a reference */ // @from 09.04
} ApiType;

typedef struct {
    char *s;            /* followed by a '\0' that len does not count */
    size_t len;
} ApiString;

/* One value: its type, and the member of u that type uses. */
typedef struct {
    ApiType type;
    union {
        int boolean;
        long long integer;
        ApiString string;
        struct { ApiString *line; int count; } lines;
        struct { long long row, col; } position;
        int function;   /* the reference script.c made: never 0 */ // @from 09.04
    } u;
} ApiValue;

/* How a function says it failed: set, and why. The caller puts the
 * function's name in front. */
typedef struct {
    int set;
    char msg[160];
} ApiError;

/* A function of the API. Its arguments have been checked against its entry
 * in the table, so it reads them without checks: args[i].type is the
 * table's. What it returns (a string, lines) it has allocated, and whoever
 * called it frees, with apiFree(). The arguments are not its own: it keeps
 * nothing that points into them. */
typedef ApiValue (*ApiFn)(ApiValue *args, int nargs, ApiError *err);

/* An entry of the table: the name a script calls it by, its arguments'
 * types and names, the type it returns (API_NIL: none), the function, and a
 * line saying what it does. */
typedef struct {
    const char *name;
    ApiType args[API_MAX_ARGS];
    const char *argnames[API_MAX_ARGS];
    int nargs;
    ApiType ret;
    ApiFn fn;
    const char *help;
} ApiFunc;

extern const ApiFunc API[];         /* the table, ended by an entry with no name */

const char *apiTypeName(ApiType type);
void apiFree(ApiValue *v);

#endif
