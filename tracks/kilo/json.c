/* json.c: just enough JSON for kilo's language server client.
 *
 * JSON (RFC 8259) is text: null, true, false, numbers, strings in double
 * quotes, arrays in [ ], objects of "key": value members in { }. Every
 * message a language server sends is one JSON object, and every message
 * kilo sends is one too.
 *
 * kilo writes its messages with printf-style formats; the one thing those
 * cannot do safely is put text inside quotes, which jsonQuote() is for.
 // @from 07.03
 * Reading is the other way round: jsonParse() turns a message into a tree,
 * and the getters at the end read it.
 // @end
 */

#include <stdlib.h>
#include <string.h>
#include "json.h"

// @from 07.03
/* ================================ Reading ================================ */

/* Where the reader is: the text left to read, how deep it is inside arrays
 * and objects, and how many values it has made. */
struct jsonReader {
    const char *p, *end;
    int depth;
    long values;
};

static json *jsonValue(struct jsonReader *r);

/* Skip the white space JSON allows between tokens. */
static void jsonSpace(struct jsonReader *r) {
    while (r->p < r->end && (*r->p == ' ' || *r->p == '\t' ||
                             *r->p == '\n' || *r->p == '\r')) r->p++;
}

/* A new value of a type, or NULL when there is no memory or the message
 * already holds JSON_MAX_VALUES of them. */
static json *jsonNew(struct jsonReader *r, enum jsonType type) {
    json *j;
    if (++r->values > JSON_MAX_VALUES) return NULL;
    j = calloc(1,sizeof(*j));
    if (j) j->type = type;
    return j;
}

/* Write code point cp as UTF-8 at out; returns how many bytes that took. */
static int jsonUtf8(unsigned long cp, char *out) {
    if (cp < 0x80) {
        out[0] = cp;
        return 1;
    } else if (cp < 0x800) {
        out[0] = 0xc0 | (cp >> 6);
        out[1] = 0x80 | (cp & 0x3f);
        return 2;
    } else if (cp < 0x10000) {
        out[0] = 0xe0 | (cp >> 12);
        out[1] = 0x80 | ((cp >> 6) & 0x3f);
        out[2] = 0x80 | (cp & 0x3f);
        return 3;
    }
    out[0] = 0xf0 | (cp >> 18);
    out[1] = 0x80 | ((cp >> 12) & 0x3f);
    out[2] = 0x80 | ((cp >> 6) & 0x3f);
    out[3] = 0x80 | (cp & 0x3f);
    return 4;
}

/* The four hex digits at p as a number, or -1 if they are not four hex
 * digits (or the text ends first). */
static long jsonHex4(const char *p, const char *end) {
    long v = 0;
    int i;
    if (end-p < 4) return -1;
    for (i = 0; i < 4; i++) {
        char c = p[i];
        v <<= 4;
        if (c >= '0' && c <= '9') v |= c-'0';
        else if (c >= 'a' && c <= 'f') v |= c-'a'+10;
        else if (c >= 'A' && c <= 'F') v |= c-'A'+10;
        else return -1;
    }
    return v;
}

/* Read a string, r->p at its opening quote. Returns its bytes, decoded and
 * ended by a '\0', with the length in *len; NULL if it is not a string. */
static char *jsonString(struct jsonReader *r, size_t *len) {
    // @build 07.03 a string
    // Find the closing quote first (a backslash takes the next character
    // with it), so one allocation holds the whole string: decoding never
    // makes it longer. Then copy it, a byte at a time, turning each escape
    // into what it stands for: \" \\ \/ \b \f \n \r \t, and \uXXXX as
    // UTF-8, with a pair of them (a surrogate pair) joined into one code
    // point. A lone surrogate, and \u0000, become U+FFFD. A raw byte below
    // 0x20 inside the quotes, or an escape JSON does not have, is an error.
    const char *p = r->p+1, *q = p;
    char *out, *o;

    while (q < r->end && *q != '"') {
        if (*q == '\\' && r->end-q < 2) return NULL;
        q += (*q == '\\') ? 2 : 1;
    }
    if (q >= r->end) return NULL;           /* no closing quote */
    out = o = malloc(q-p+1);
    if (out == NULL) return NULL;
    while (p < q) {
        unsigned char c = *p++;
        if (c < 0x20) goto bad;             /* JSON has no raw control bytes */
        if (c != '\\') {
            *o++ = c;
            continue;
        }
        switch (*p++) {
        case '"': *o++ = '"'; break;
        case '\\': *o++ = '\\'; break;
        case '/': *o++ = '/'; break;
        case 'b': *o++ = '\b'; break;
        case 'f': *o++ = '\f'; break;
        case 'n': *o++ = '\n'; break;
        case 'r': *o++ = '\r'; break;
        case 't': *o++ = '\t'; break;
        case 'u': {
            long cp = jsonHex4(p,q), lo;
            if (cp < 0) goto bad;
            p += 4;
            if (cp >= 0xd800 && cp <= 0xdbff) {
                /* A high surrogate: only with a low one after it is it a
                 * character, one past U+FFFF. */
                if (q-p >= 6 && p[0] == '\\' && p[1] == 'u' &&
                    (lo = jsonHex4(p+2,q)) >= 0xdc00 && lo <= 0xdfff) {
                    cp = 0x10000 + ((cp-0xd800) << 10) + (lo-0xdc00);
                    p += 6;
                } else {
                    cp = 0xfffd;
                }
            } else if ((cp >= 0xdc00 && cp <= 0xdfff) || cp == 0) {
                cp = 0xfffd;        /* a lone low surrogate; a '\0' */
            }
            o += jsonUtf8(cp,o);
            break;
        }
        default: goto bad;
        }
    }
    *o = '\0';
    *len = o-out;
    r->p = q+1;
    return out;

bad:
    free(out);
    return NULL;
    // @end
}

/* Read a number: the JSON grammar checked here, the value from strtod(). */
static json *jsonNumber(struct jsonReader *r) {
    // @build 07.03 a number
    // Check the text against JSON's grammar, which is narrower than
    // strtod()'s (no "+1", no ".5", no "1.", no "0x1", no "inf"): an
    // optional '-', then 0 or digits not starting with 0, then optionally
    // '.' and digits, then optionally e or E, a sign, and digits. Copy it
    // (at most 63 characters) to have a '\0' after it, and let strtod()
    // read its value.
    const char *p = r->p, *start = p;
    char buf[64];
    json *j;

    if (p < r->end && *p == '-') p++;
    if (p < r->end && *p == '0') {
        p++;
    } else if (p < r->end && *p >= '1' && *p <= '9') {
        while (p < r->end && *p >= '0' && *p <= '9') p++;
    } else {
        return NULL;
    }
    if (p < r->end && *p == '.') {
        p++;
        if (p >= r->end || *p < '0' || *p > '9') return NULL;
        while (p < r->end && *p >= '0' && *p <= '9') p++;
    }
    if (p < r->end && (*p == 'e' || *p == 'E')) {
        p++;
        if (p < r->end && (*p == '+' || *p == '-')) p++;
        if (p >= r->end || *p < '0' || *p > '9') return NULL;
        while (p < r->end && *p >= '0' && *p <= '9') p++;
    }
    if (p-start >= (long)sizeof(buf)) return NULL;
    memcpy(buf,start,p-start);
    buf[p-start] = '\0';
    if ((j = jsonNew(r,JSON_NUMBER)) == NULL) return NULL;
    j->number = strtod(buf,NULL);
    r->p = p;
    return j;
    // @end
}

/* Read an array or an object, r->p at its '[' or '{'. */
static json *jsonList(struct jsonReader *r) {
    // @build 07.03 arrays and objects
    // One more level deep, and no more than JSON_MAX_DEPTH. Then values
    // separated by commas up to the closing bracket, each added at the end
    // of the list; in an object each value comes after a string key and a
    // colon. A comma before the closing bracket is an error. On an error,
    // free what was read.
    int object = *r->p == '{';
    char close = object ? '}' : ']';
    json *list, *last = NULL, *item;

    if (++r->depth > JSON_MAX_DEPTH) return NULL;
    if ((list = jsonNew(r,object ? JSON_OBJECT : JSON_ARRAY)) == NULL) return NULL;
    r->p++;
    jsonSpace(r);
    if (r->p < r->end && *r->p == close) {
        r->p++;
        r->depth--;
        return list;
    }
    while (1) {
        char *key = NULL;
        size_t klen;
        jsonSpace(r);
        if (object) {
            if (r->p >= r->end || *r->p != '"') goto bad;
            if ((key = jsonString(r,&klen)) == NULL) goto bad;
            jsonSpace(r);
            if (r->p >= r->end || *r->p != ':') {
                free(key);
                goto bad;
            }
            r->p++;
        }
        if ((item = jsonValue(r)) == NULL) {
            free(key);
            goto bad;
        }
        item->key = key;
        if (last) last->next = item; else list->child = item;
        last = item;
        jsonSpace(r);
        if (r->p < r->end && *r->p == ',') {
            r->p++;
            continue;
        }
        if (r->p < r->end && *r->p == close) {
            r->p++;
            r->depth--;
            return list;
        }
        goto bad;
    }

bad:
    jsonFree(list);
    return NULL;
    // @end
}

/* Read one value, of whatever kind the next character says. */
static json *jsonValue(struct jsonReader *r) {
    // @build 07.03 one value
    // Skip white space, then look at the next character: a quote is a
    // string, '[' or '{' a list, '-' or a digit a number, and true, false
    // and null are spelt out whole. Anything else, or the end of the
    // text, is an error (NULL).
    static const char *words[] = {"null","true","false"};
    json *j;
    int i;

    jsonSpace(r);
    if (r->p >= r->end) return NULL;
    if (*r->p == '"') {
        if ((j = jsonNew(r,JSON_STRING)) == NULL) return NULL;
        if ((j->string = jsonString(r,&j->len)) == NULL) {
            free(j);
            return NULL;
        }
        return j;
    }
    if (*r->p == '[' || *r->p == '{') return jsonList(r);
    if (*r->p == '-' || (*r->p >= '0' && *r->p <= '9')) return jsonNumber(r);
    for (i = 0; i < 3; i++) {
        size_t n = strlen(words[i]);
        if ((size_t)(r->end-r->p) >= n && memcmp(r->p,words[i],n) == 0) {
            if ((j = jsonNew(r,i ? JSON_BOOL : JSON_NULL)) == NULL) return NULL;
            j->number = i == 1;
            r->p += n;
            return j;
        }
    }
    return NULL;
    // @end
}

/* Read the len bytes at s as one JSON value: its tree, which the caller
 * frees with jsonFree(), or NULL if they are not exactly one value (white
 * space around it is allowed, anything else after it is not). */
json *jsonParse(const char *s, size_t len) {
    // @build 07.03 the whole message
    // Read one value from the start, then skip white space: if anything is
    // left, free the value and return NULL.
    struct jsonReader r;
    json *j;

    r.p = s;
    r.end = s+len;
    r.depth = 0;
    r.values = 0;
    j = jsonValue(&r);
    if (j == NULL) return NULL;
    jsonSpace(&r);
    if (r.p != r.end) {
        jsonFree(j);
        return NULL;
    }
    return j;
    // @end
}

/* Free a value and everything in it. */
void jsonFree(json *j) {
    // @build 07.03 free a tree
    // For each value in the list from j: free its children (one call per
    // level, so no deeper than the reader went), its string and its key,
    // and itself.
    while (j) {
        json *next = j->next;
        jsonFree(j->child);
        free(j->string);
        free(j->key);
        free(j);
        j = next;
    }
    // @end
}

/* The member of object j with this key (the first, if there are two), or
 * NULL. */
json *jsonGet(json *j, const char *key) {
    // @build 07.03 the getters
    // Each getter first checks that j is there and of the type it reads.
    // jsonGet: walk an object's members for the key. jsonInt: a number
    // that is a whole number and fits an int. jsonStr: a string's bytes.
    // Otherwise the default.
    if (j == NULL || j->type != JSON_OBJECT) return NULL;
    for (j = j->child; j; j = j->next)
        if (strcmp(j->key,key) == 0) return j;
    return NULL;
    // @end
}

/* Is j there, and of this type? */
int jsonIs(json *j, enum jsonType type) {
    return j != NULL && j->type == type;
}

/* A number that is a whole number and fits in an int, or dflt. */
int jsonInt(json *j, int dflt) {
    if (!jsonIs(j,JSON_NUMBER)) return dflt;
    /* Inside the range first: casting a double that is not would be
     * undefined. NaN fails both tests. */
    if (!(j->number >= -2147483648.0 && j->number <= 2147483647.0)) return dflt;
    if ((double)(int)j->number != j->number) return dflt;
    return (int)j->number;
}

/* A string's bytes, or dflt. */
const char *jsonStr(json *j, const char *dflt) {
    return jsonIs(j,JSON_STRING) ? j->string : dflt;
}

// @end
/* ================================ Writing ================================ */

/* The len bytes at s as a JSON string, quotes included, in a new
 * allocation the caller frees: a '"' or a '\' gets a backslash before it,
 * and a control byte is written as an escape. */
char *jsonQuote(const char *s, size_t len) {
    // @build 07.02 quote a string
    // Count the room first: 2 for the quotes, 2 for '"' and '\', 2 for
    // \n \t \r \b \f, 6 for any other byte below 0x20 (\u00XX), 1 for
    // the rest, which go as they are (UTF-8 included). Then write it.
    static const char hex[] = "0123456789abcdef";
    size_t i, n = 2;
    char *out, *o;

    for (i = 0; i < len; i++) {
        unsigned char c = s[i];
        if (c == '"' || c == '\\' || c == '\n' || c == '\t' || c == '\r' ||
            c == '\b' || c == '\f') n += 2;
        else if (c < 0x20) n += 6;
        else n += 1;
    }
    if ((out = o = malloc(n+1)) == NULL) return NULL;
    *o++ = '"';
    for (i = 0; i < len; i++) {
        unsigned char c = s[i];
        switch (c) {
        case '"': *o++ = '\\'; *o++ = '"'; break;
        case '\\': *o++ = '\\'; *o++ = '\\'; break;
        case '\n': *o++ = '\\'; *o++ = 'n'; break;
        case '\t': *o++ = '\\'; *o++ = 't'; break;
        case '\r': *o++ = '\\'; *o++ = 'r'; break;
        case '\b': *o++ = '\\'; *o++ = 'b'; break;
        case '\f': *o++ = '\\'; *o++ = 'f'; break;
        default:
            if (c < 0x20) {
                memcpy(o,"\\u00",4);
                o[4] = hex[c >> 4];
                o[5] = hex[c & 15];
                o += 6;
            } else {
                *o++ = c;
            }
        }
    }
    *o++ = '"';
    *o = '\0';
    return out;
    // @end
}
