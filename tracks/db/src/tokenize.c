/*
 * tokenize.c - SQL text to tokens.
 *
 * SQL is read as a sequence of tokens, not characters: a keyword, a name,
 * a number, a string, an operator. next_token() reads one token from the
 * text and says how long it is, so the next call starts just after it.
 * Spaces and comments are tokens too (TK_SPACE), for the caller to skip,
 * so that every byte of the input belongs to some token.
 */
#include <ctype.h>
#include <string.h>
#include <strings.h>

#include "db.h"

static const struct {
    const char *word;
    int type;
} keywords[] = {
    {"AND", TK_AND}, {"AS", TK_AS}, {"ASC", TK_ASC}, {"AUTOINCREMENT", TK_AUTOINCREMENT},
    {"BEGIN", TK_BEGIN}, {"BETWEEN", TK_BETWEEN}, {"BY", TK_BY}, {"CHECK", TK_CHECK},
    {"COLLATE", TK_COLLATE}, {"COMMIT", TK_COMMIT}, {"CONSTRAINT", TK_CONSTRAINT},
    {"CREATE", TK_CREATE}, {"DEFAULT", TK_DEFAULT}, {"DEFERRED", TK_DEFERRED},
    {"DELETE", TK_DELETE}, {"DESC", TK_DESC}, {"DISTINCT", TK_DISTINCT}, {"DROP", TK_DROP},
    {"END", TK_END}, {"EXCLUSIVE", TK_EXCLUSIVE}, {"EXISTS", TK_EXISTS},
    {"EXPLAIN", TK_EXPLAIN}, {"FOREIGN", TK_FOREIGN}, {"FROM", TK_FROM}, {"GLOB", TK_GLOB},
    {"GROUP", TK_GROUP}, {"HAVING", TK_HAVING}, {"IF", TK_IF}, {"IMMEDIATE", TK_IMMEDIATE},
    {"IN", TK_IN}, {"INDEX", TK_INDEX}, {"INSERT", TK_INSERT}, {"INTO", TK_INTO},
    {"IS", TK_IS}, {"ISNULL", TK_ISNULL}, {"JOIN", TK_JOIN}, {"KEY", TK_KEY},
    {"LIKE", TK_LIKE}, {"LIMIT", TK_LIMIT}, {"NOT", TK_NOT}, {"NOTNULL", TK_NOTNULL},
    {"NULL", TK_NULL}, {"OFFSET", TK_OFFSET}, {"ON", TK_ON}, {"OR", TK_OR},
    {"ORDER", TK_ORDER}, {"PLAN", TK_PLAN}, {"PRAGMA", TK_PRAGMA}, {"PRIMARY", TK_PRIMARY},
    {"QUERY", TK_QUERY}, {"REFERENCES", TK_REFERENCES}, {"REPLACE", TK_REPLACE},
    {"ROLLBACK", TK_ROLLBACK}, {"SELECT", TK_SELECT}, {"SET", TK_SET}, {"TABLE", TK_TABLE},
    {"TRANSACTION", TK_TRANSACTION}, {"UNION", TK_UNION}, {"UNIQUE", TK_UNIQUE},
    {"UPDATE", TK_UPDATE}, {"VALUES", TK_VALUES}, {"WHERE", TK_WHERE},
    {"WITHOUT", TK_WITHOUT},
};

#define NKEYWORDS (sizeof keywords / sizeof keywords[0])

/* Returns the keyword's token type if s[0..n) is a keyword (in any case),
 * otherwise TK_ID. */
int keyword_type(const char *s, int n)
{
    static unsigned char len[NKEYWORDS];
    if (len[0] == 0)
        for (size_t i = 0; i < NKEYWORDS; i++)
            len[i] = (unsigned char)strlen(keywords[i].word);
    int c = toupper((unsigned char)s[0]);
    for (size_t i = 0; i < NKEYWORDS; i++)
        if (len[i] == n && keywords[i].word[0] == c && strncasecmp(s, keywords[i].word, (size_t)n) == 0)
            return keywords[i].type;
    return TK_ID;
}

/* The keyword spelling of a keyword token type, or "?" for any other. */
const char *token_name(int type)
{
    for (size_t i = 0; i < NKEYWORDS; i++)
        if (keywords[i].type == type)
            return keywords[i].word;
    return "?";
}

/* Bytes 0x80 and up count as name characters, so UTF-8 names pass through
 * untouched. */
static int is_id_start(int c) { return isalpha(c) || c == '_' || c >= 0x80; }
static int is_id_char(int c) { return isalnum(c) || c == '_' || c == '$' || c >= 0x80; }

/* A quoted string or name starting at u (u[0] is the quote: ' " ` or [).
 * Sets *type to TK_STRING ('...') or TK_ID (the others), or TK_ILLEGAL if
 * the closing quote never comes. Returns the length, quotes included; for
 * an unterminated one, the length up to the end of the text.
 *
 * The token ends at the same quote character, or at ] for [. Inside, a
 * doubled quote ('' in a string, "" in a name) stands for one quote
 * character and does not end the token; [...] has no such escape. */
static int scan_quoted(const unsigned char *u, int *type)
{
    int n = 1;
    // @build 03.01 strings and quoted names
    int close = u[0] == '[' ? ']' : u[0];
    for (;;) {
        if (u[n] == 0) {
            *type = TK_ILLEGAL;
            return n;
        }
        if (u[n] == close) {
            if (close != ']' && u[n + 1] == close) {
                n += 2;
                continue;
            }
            n++;
            *type = u[0] == '\'' ? TK_STRING : TK_ID;
            return n;
        }
        n++;
    }
    // @end
}

/* A number starting at u: digits, then maybe .digits, then maybe
 * e[+-]digits; or starting with the . (".5"). Sets *type to TK_INTEGER if
 * it is only digits, TK_FLOAT otherwise. Returns its length.
 *
 * An e not followed by digits is not part of the number. If name
 * characters run straight on (12abc), the whole run is one TK_ILLEGAL
 * token: a number must not touch a name. */
static int scan_number(const unsigned char *u, int *type)
{
    int n = 0;
    // @build 03.01 numbers
    *type = TK_INTEGER;
    while (isdigit(u[n]))
        n++;
    if (u[n] == '.') {
        *type = TK_FLOAT;
        n++;
        while (isdigit(u[n]))
            n++;
    }
    if ((u[n] == 'e' || u[n] == 'E') &&
        (isdigit(u[n + 1]) || ((u[n + 1] == '+' || u[n + 1] == '-') && isdigit(u[n + 2])))) {
        *type = TK_FLOAT;
        n += 2;
        while (isdigit(u[n]))
            n++;
    }
    if (is_id_char(u[n])) {
        while (is_id_char(u[n]))
            n++;
        *type = TK_ILLEGAL;
    }
    return n;
    // @end
}

/* Reads the token that starts at z into *t (type, s = z, n = length) and
 * returns its length. The first character or two decide what it is:
 *
 *   end of text (NUL)             TK_EOF, length 0
 *   spaces, tabs, newlines        TK_SPACE, the whole run
 *   -- to the end of the line, and C-style block comments
 *                                 TK_SPACE too (a block comment left open
 *                                 runs to the end of the text)
 *   ; ( ) , * + - / %             TK_SEMI TK_LP TK_RP TK_COMMA TK_STAR
 *                                 TK_PLUS TK_MINUS TK_SLASH TK_REM
 *   || = == != <> < <= > >=       TK_CONCAT, TK_EQ (both), TK_NE (both),
 *                                 TK_LT, TK_LE, TK_GT, TK_GE
 *   ' " ` [                       scan_quoted()
 *   a digit, or . then a digit    scan_number(); a lone . is TK_DOT
 *   x'...' or X'...'              TK_BLOB: an even number of hex digits
 *                                 between the quotes, else TK_ILLEGAL
 *   a letter or _, then letters, digits, _ or $
 *                                 keyword_type() of it: a keyword or TK_ID
 *   anything else (a lone | or !) TK_ILLEGAL, 1 character
 *
 * Spaces and comments are tokens, so every byte of the input belongs to
 * exactly one token. */
int next_token(const char *z, Token *t)
{
    const unsigned char *u = (const unsigned char *)z;
    int n = 0, type = TK_ILLEGAL;
    // @build 03.01 read one token
    switch (u[0]) {
    case 0:
        type = TK_EOF;
        break;
    case ' ': case '\t': case '\n': case '\r': case '\f': case '\v':
        n = 1;
        while (isspace(u[n]))
            n++;
        type = TK_SPACE;
        break;
    case '-':
        n = 1;
        type = TK_MINUS;
        if (u[1] == '-') {
            while (u[n] && u[n] != '\n')
                n++;
            type = TK_SPACE;
        }
        break;
    case '/':
        n = 1;
        type = TK_SLASH;
        if (u[1] == '*') {
            n = 2;
            while (u[n] && !(u[n] == '*' && u[n + 1] == '/'))
                n++;
            if (u[n])
                n += 2;
            type = TK_SPACE;
        }
        break;
    case ';': type = TK_SEMI; n = 1; break;
    case '(': type = TK_LP; n = 1; break;
    case ')': type = TK_RP; n = 1; break;
    case ',': type = TK_COMMA; n = 1; break;
    case '*': type = TK_STAR; n = 1; break;
    case '+': type = TK_PLUS; n = 1; break;
    case '%': type = TK_REM; n = 1; break;
    case '|':
        n = 1;
        if (u[1] == '|') {
            type = TK_CONCAT;
            n = 2;
        }
        break;
    case '=':
        type = TK_EQ;
        n = u[1] == '=' ? 2 : 1;
        break;
    case '!':
        n = 1;
        if (u[1] == '=') {
            type = TK_NE;
            n = 2;
        }
        break;
    case '<':
        type = u[1] == '=' ? TK_LE : u[1] == '>' ? TK_NE : TK_LT;
        n = type == TK_LT ? 1 : 2;
        break;
    case '>':
        type = u[1] == '=' ? TK_GE : TK_GT;
        n = type == TK_GE ? 2 : 1;
        break;
    case '\'': case '"': case '`': case '[':
        n = scan_quoted(u, &type);
        break;
    case '.':
        if (!isdigit(u[1])) {
            type = TK_DOT;
            n = 1;
            break;
        }
        n = scan_number(u, &type);
        break;
    case '0': case '1': case '2': case '3': case '4':
    case '5': case '6': case '7': case '8': case '9':
        n = scan_number(u, &type);
        break;
    default:
        if ((u[0] == 'x' || u[0] == 'X') && u[1] == '\'') {
            n = 2;
            while (isxdigit(u[n]))
                n++;
            int even = (n - 2) % 2 == 0;
            if (u[n] == '\'' && even) {
                type = TK_BLOB;
                n++;
            } else {
                while (u[n] && u[n] != '\'')
                    n++;
                if (u[n])
                    n++;
                type = TK_ILLEGAL;
            }
        } else if (is_id_start(u[0])) {
            n = 1;
            while (is_id_char(u[n]))
                n++;
            type = keyword_type(z, n);
        } else {
            n = 1;
        }
        break;
    }
    // @end
    t->type = type;
    t->s = z;
    t->n = n;
    return n;
}

/* Returns 1 if sql holds one or more complete statements, that is, ends
 * with a semicolon that is not inside a string, a name or a comment. The
 * shell keeps reading lines until this holds. */
int sql_complete(const char *sql)
{
    Token t;
    int last = TK_SPACE, seen = 0;
    const char *z = sql;
    for (;;) {
        z += next_token(z, &t);
        if (t.type == TK_EOF)
            break;
        if (t.type == TK_ILLEGAL && (*t.s == '\'' || *t.s == '"' || *t.s == '`' || *t.s == '['))
            return 0;    /* an unclosed string or name: keep reading */
        if (t.type == TK_SPACE) {
            if (t.n >= 2 && t.s[0] == '/' && t.s[1] == '*' &&
                (t.n < 4 || t.s[t.n - 1] != '/' || t.s[t.n - 2] != '*'))
                return 0;    /* an unclosed comment */
            continue;
        }
        last = t.type;
        seen = 1;
    }
    return seen && last == TK_SEMI;
}
