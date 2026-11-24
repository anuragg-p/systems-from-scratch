/* json.h: just enough JSON for kilo's language server client.
 *
 // @from 07.03
 * One writer helper, which quotes a string so it can go inside a message,
 * and a reader, which turns a message into a tree of values. Nothing here
 * knows of kilo or of the protocol the messages belong to.
 // @else
 // * One writer helper, which quotes a string so it can go inside a message.
 // * Nothing here knows of kilo or of the protocol the messages belong to.
 // @end
 */

#ifndef KILO_JSON_H
#define KILO_JSON_H

#include <stddef.h>

// @from 07.03
/* How deep arrays and objects may sit inside each other, and how many
 * values a message may hold, before the reader gives up on it. The reader
 * calls itself once per level, so the first is what bounds its stack. */
#define JSON_MAX_DEPTH 64
#define JSON_MAX_VALUES 1000000

/* The six kinds of JSON value. */
enum jsonType { JSON_NULL, JSON_BOOL, JSON_NUMBER, JSON_STRING, JSON_ARRAY, JSON_OBJECT };

/* One value. The elements of an array, and the members of an object, are a
 * list: the first is child, each one's next is the one after it. A member
 * of an object has its key as well. */
typedef struct json {
    enum jsonType type;
    double number;          /* JSON_NUMBER; JSON_BOOL: 1 for true, 0 for false */
    char *string;           /* JSON_STRING: the decoded bytes, with a '\0' after them */
    size_t len;             /* JSON_STRING: how many bytes, without the '\0' */
    char *key;              /* a member of an object: its key, decoded */
    struct json *child;     /* JSON_ARRAY, JSON_OBJECT: the first element */
    struct json *next;      /* the element after this one, or NULL */
} json;

json *jsonParse(const char *s, size_t len);
void jsonFree(json *j);

/* Reading a tree. Each takes NULL, or a value of the wrong type, and then
 * gives NULL or the default: a chain like
 *     jsonInt(jsonGet(jsonGet(msg,"params"),"version"),-1)
 * needs no check in between, whatever the message holds. */
json *jsonGet(json *j, const char *key);
int jsonIs(json *j, enum jsonType type);
int jsonInt(json *j, int dflt);
const char *jsonStr(json *j, const char *dflt);

// @end
char *jsonQuote(const char *s, size_t len);

// @internal
/* Stands in for code a workspace has cut out (see kilo.c). */
__attribute__((noreturn)) void kiloTodo(const char *lesson, const char *what);
// @end
#endif
