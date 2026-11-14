/*
 * read.c - reading a makefile into a graph.
 *
 * A makefile is lines of four kinds, with comments (from # to the end of
 * the line) and blank lines between them:
 *
 *   NAME = VALUE        set a variable; NAME += VALUE adds to its value
 *   TARGETS: PREREQS    a rule: each target needs each prerequisite
 *   <tab>COMMAND        a line of the recipe of the rule above it
 *   include FILES       read these makefiles here; FILES may be a glob
 *
 * A line that ends with a backslash goes on on the next line. $(NAME) is
 * a variable's value. In a rule or an include it is expanded as the line
 * is read; a variable keeps its value as written, and a recipe is
 * expanded only when it runs, so a recipe sees what each variable holds
 * at the end of the makefile (a CFLAGS += further down counts). .PHONY: NAMES says which targets are not
 * files. That is the part of GNU make this track's own Makefile uses.
 * Everything else (other kinds of variable, functions, $@ and the other
 * automatic variables, pattern and suffix rules, conditionals) is an
 * ordinary error, never a guess.
 */
#include <errno.h>
#include <glob.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

#include "make.h"

long default_goal = -1;

/* ------------------------------------------------------------ variables */

typedef struct {
    char *value;            /* as written: expanded each time it is used */
    int   origin;           /* FROM_ENVIRONMENT, FROM_MAKEFILE, FROM_COMMAND_LINE */
    int   busy;             /* being expanded: met again inside itself, a loop */
} Var;

static Table var_index;     /* a name -> its index in vars */
static Array vars;          /* Var *: each one malloc'd, so a pointer to it stays good */
static int vars_ready;

static Var *find_var(const char *name, size_t len)
{
    if (!vars_ready) {
        table_init(&var_index);
        array_init(&vars, sizeof(Var *));
        vars_ready = 1;
    }
    long *i = table_get(&var_index, name, len);
    if (i != NULL)
        return *(Var **)array_at(&vars, (size_t)*i);
    /* not set in the makefile: the environment's, if it has one, as make
     * takes every environment variable as a variable of the makefile */
    char *n = xstrndup(name, len);
    const char *env = getenv(n);
    free(n);
    if (env == NULL)
        return NULL;
    Var *v = xmalloc(sizeof *v);
    v->value = xstrndup(env, strlen(env));
    v->origin = FROM_ENVIRONMENT;
    v->busy = 0;
    *(Var **)array_push(&vars) = v;
    *table_put(&var_index, name, len) = (long)vars.len - 1;
    return v;
}

/* NAME = VALUE: a value set on make's command line wins over the
 * makefile's, which wins over the environment's. */
void set_variable(const char *name, const char *value, int origin)
{
    size_t len = strlen(name);
    Var *v = find_var(name, len);
    if (v != NULL && v->origin > origin)
        return;
    if (v == NULL) {
        v = xmalloc(sizeof *v);
        v->busy = 0;
        *(Var **)array_push(&vars) = v;
        *table_put(&var_index, name, len) = (long)vars.len - 1;
    } else {
        free(v->value);
    }
    v->value = xstrndup(value, strlen(value));
    v->origin = origin;
}

/* NAME += VALUE: the old value, a space and the new one; just the new one
 * if there was none (GNU make 4; 3.81 adds the space anyway). */
static void append_variable(const char *name, const char *value)
{
    Var *v = find_var(name, strlen(name));
    if (v == NULL || v->value[0] == '\0') {
        set_variable(name, value, FROM_MAKEFILE);
        return;
    }
    if (v->origin > FROM_MAKEFILE || value[0] == '\0')
        return;
    size_t a = strlen(v->value), b = strlen(value);
    char *s = xmalloc(a + 1 + b + 1);
    memcpy(s, v->value, a);
    s[a] = ' ';
    memcpy(s + a + 1, value, b + 1);
    free(v->value);
    v->value = s;
    if (v->origin == FROM_ENVIRONMENT)
        v->origin = FROM_MAKEFILE;
}

static const char *where_file;
static long where_line;

/* An error in a makefile: "make: FILE:LINE: what", status 2. */
static _Noreturn void die_at(const char *file, long line, const char *fmt, ...)
{
    char msg[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(msg, sizeof msg, fmt, ap);
    va_end(ap);
    if (file != NULL)
        die("%s:%ld: %s", file, line, msg);
    die("%s", msg);
}

/* An error at the line being read or expanded. */
#define bad(...) die_at(where_file, where_line, __VA_ARGS__)

static void put(Array *out, const char *s, size_t n)
{
    for (size_t i = 0; i < n; i++)
        *(char *)array_push(out) = s[i];
}

/* The n bytes at s, expanded, onto the end of out (an Array of char). */
static void expand_into(Array *out, const char *s, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        if (s[i] != '$') {
            put(out, s + i, 1);
            continue;
        }
        if (++i == n)
            break;                          /* a $ at the very end: nothing */
        char open = s[i];
        if (open == '$') {
            put(out, "$", 1);
            continue;
        }
        if (open != '(' && open != '{') {
            char what[3] = {'$', open, '\0'};
            bad("'%s' is not supported: write $(NAME), ${NAME} or $$", what);
        }
        char close = open == '(' ? ')' : '}';
        size_t start = i + 1, depth = 1, j;
        for (j = start; j < n; j++) {
            if (s[j] == open)
                depth++;
            else if (s[j] == close && --depth == 0)
                break;
        }
        if (j == n)
            bad("an unterminated variable reference: no closing bracket");
        /* the name may be made of variables itself: $(CFLAGS_$(MODE)) */
        Array name;
        array_init(&name, 1);
        expand_into(&name, s + start, j - start);
        put(&name, "", 1);
        if (strpbrk(name.data, " \t:,=") != NULL)
            bad("'$(%s)' is not supported: no functions or substitutions, only $(NAME)", name.data);
        Var *v = find_var(name.data, name.len - 1);
        if (v != NULL) {
            if (v->busy)
                bad("the variable %s refers to itself", name.data);
            v->busy = 1;
            expand_into(out, v->value, strlen(v->value));
            v->busy = 0;
        }
        array_free(&name);
        i = j;
    }
}

char *expand(const char *text, const char *file, long line)
{
    const char *f = where_file;
    long l = where_line;
    where_file = file;
    where_line = line;
    Array out;
    array_init(&out, 1);
    expand_into(&out, text, strlen(text));
    put(&out, "", 1);
    where_file = f;
    where_line = l;
    char *s = xstrndup(out.data, out.len - 1);
    array_free(&out);
    return s;
}

/* ------------------------------------------------------------ the graph */

Target *target(Graph *g, long n)
{
    Node *node = graph_at(g, n);
    if (node->data == NULL) {
        node->data = xmalloc(sizeof(Target));
        memset(node->data, 0, sizeof(Target));
    }
    return node->data;
}

/* The words of s, split at blanks: an Array of char *, each a new string. */
static void split(const char *s, Array *words)
{
    array_init(words, sizeof(char *));
    for (;;) {
        while (*s == ' ' || *s == '\t')
            s++;
        if (*s == '\0')
            return;
        const char *e = s;
        while (*e && *e != ' ' && *e != '\t')
            e++;
        *(char **)array_push(words) = xstrndup(s, (size_t)(e - s));
        s = e;
    }
}

static void free_words(Array *words)
{
    for (size_t i = 0; i < words->len; i++)
        free(*(char **)array_at(words, i));
    array_free(words);
}

/* The rule whose recipe lines are being read. */
typedef struct {
    Array   targets;        /* long: its targets' nodes */
    Array   prereqs;        /* char *: its prerequisites, as written */
    Recipe *recipe;         /* NULL until its first recipe line */
} Rule;

/* A rule: each target is a node of the graph (added if new), and needs
 * each prerequisite, a node too. A target may have several rules: what
 * each one says it needs is added to what it needed already. */
static void add_rule(Graph *g, Rule *r, Array *targets, Array *prereqs)
{
    // @build 07.01 a rule into the graph: targets and prerequisites become nodes, needs become edges
    for (size_t i = 0; i < targets->len; i++) {
        long t = graph_node(g, *(char **)array_at(targets, i));
        target(g, t)->rule = 1;
        *(long *)array_push(&r->targets) = t;
        for (size_t j = 0; j < prereqs->len; j++)
            graph_edge(g, t, graph_node(g, *(char **)array_at(prereqs, j)));
    }
    // @end
}

/* GNU make lists what a target needs with the rule that has its recipe
 * first, then the others' prerequisites in the order of the makefile: so
 * a recipe can count on its own rule's first prerequisite coming first.
 * The order matters to make: it builds them in that order. */
static void put_first(Graph *g, long t, Rule *r)
{
    Node *node = graph_at(g, t);
    Array old = node->needs;
    array_init(&node->needs, sizeof(long));
    for (size_t i = 0; i < r->prereqs.len; i++) {
        long p = graph_find(g, *(char **)array_at(&r->prereqs, i));
        int seen = 0;
        for (size_t k = 0; k < node->needs.len; k++)
            seen |= *(long *)array_at(&node->needs, k) == p;
        if (!seen)
            *(long *)array_push(&node->needs) = p;
    }
    for (size_t i = 0; i < old.len; i++) {
        long p = *(long *)array_at(&old, i);
        int seen = 0;
        for (size_t k = 0; k < node->needs.len; k++)
            seen |= *(long *)array_at(&node->needs, k) == p;
        if (!seen)
            *(long *)array_push(&node->needs) = p;
    }
    array_free(&old);
}

/* The rule's first recipe line has come: the recipe is its targets'. */
static void start_recipe(Graph *g, Rule *r, const char *file, long line)
{
    r->recipe = xmalloc(sizeof(Recipe));
    array_init(&r->recipe->lines, sizeof(char *));
    r->recipe->file = file;
    r->recipe->line = line;
    for (size_t i = 0; i < r->targets.len; i++) {
        long t = *(long *)array_at(&r->targets, i);
        Target *x = target(g, t);
        if (x->recipe != NULL) {
            fprintf(stderr, "make: %s:%ld: warning: overriding recipe for target '%s'\n", file, line,
                    graph_at(g, t)->name);
            fprintf(stderr, "make: %s:%ld: warning: ignoring old recipe for target '%s'\n",
                    x->recipe->file, x->recipe->line, graph_at(g, t)->name);
        }
        x->recipe = r->recipe;
        put_first(g, t, r);
    }
}

static void end_rule(Rule *r)
{
    array_free(&r->targets);
    free_words(&r->prereqs);
}

/* ------------------------------------------------------------ the lines */

/* Where the first ':' or '=' of line is, outside any $(...): the place
 * that says what kind of line it is; NULL if it has neither. */
static const char *separator(const char *line)
{
    int depth = 0;
    for (const char *p = line; *p; p++) {
        if (*p == '$' && (p[1] == '(' || p[1] == '{')) {
            depth++;
            p++;
        } else if (depth > 0 && (*p == ')' || *p == '}')) {
            depth--;
        } else if (depth == 0 && (*p == ':' || *p == '=')) {
            return p;
        }
    }
    return NULL;
}

static const char *const unsupported[] = {
    "-include", "sinclude", "ifeq", "ifneq", "ifdef", "ifndef", "else", "endif", "define",
    "endef", "export", "unexport", "override", "vpath", "undefine", "private", "load", NULL,
};

static void read_file(Graph *g, const char *path, const char *from, long from_line);

/* include FILES: each file in turn, a glob giving its matches in order. */
static void include(Graph *g, const char *words, const char *file, long line)
{
    char *x = expand(words, file, line);
    Array names;
    split(x, &names);
    free(x);
    for (size_t i = 0; i < names.len; i++) {
        const char *name = *(char **)array_at(&names, i);
        glob_t gl;
        /* no match: the name itself, which then cannot be opened */
        if (glob(name, GLOB_NOCHECK, NULL, &gl) != 0)
            die_at(file, line, "include: cannot read the pattern %s", name);
        for (size_t k = 0; k < gl.gl_pathc; k++)
            read_file(g, gl.gl_pathv[k], file, line);
        globfree(&gl);
    }
    free_words(&names);
}

/* One logical line that is not part of a recipe: a variable, a rule or an
 * include. *rule is the rule being read, or NULL; a rule line starts a new
 * one, and any other line ends it. */
static void makefile_line(Graph *g, char *line, int tab, Rule **rule, const char *file, long lineno)
{
    where_file = file;
    where_line = lineno;
    char *hash = strchr(line, '#');
    if (hash != NULL)
        *hash = '\0';
    char *s = line;
    while (*s == ' ' || *s == '\t')
        s++;
    if (*s == '\0')
        return;                             /* blank, or a comment: the rule goes on */
    if (*rule != NULL) {
        end_rule(*rule);
        free(*rule);
        *rule = NULL;
    }

    size_t w = strcspn(s, " \t");
    if (w == 7 && strncmp(s, "include", 7) == 0) {
        include(g, s + 7, file, lineno);
        return;
    }
    for (int i = 0; unsupported[i]; i++)
        if (strlen(unsupported[i]) == w && strncmp(s, unsupported[i], w) == 0 && s[w] != ':' && s[w] != '=')
            bad("'%s' is not supported", unsupported[i]);

    const char *sep = separator(s);
    if (sep == NULL)
        bad(tab ? "a recipe line before the first rule" : "missing separator");

    if (*sep == '=') {
        /* NAME = VALUE, or NAME += VALUE */
        int append = sep > s && sep[-1] == '+';
        if (sep > s && (sep[-1] == '?' || sep[-1] == '!')) {
            char op[3] = {sep[-1], '=', '\0'};
            bad("'%s' is not supported: only = and +=", op);
        }
        const char *e = append ? sep - 1 : sep;
        while (e > s && (e[-1] == ' ' || e[-1] == '\t'))
            e--;
        char *name = xstrndup(s, (size_t)(e - s));
        if (*name == '\0' || strpbrk(name, " \t") != NULL)
            bad("'%s' is not supported", name);
        const char *value = sep + 1;
        while (*value == ' ' || *value == '\t')
            value++;
        /* the value keeps any blanks at its end, before a comment, as GNU make's does */
        if (append)
            append_variable(name, value);
        else
            set_variable(name, value, FROM_MAKEFILE);
        free(name);
        return;
    }

    /* TARGETS: PREREQS */
    if (sep[1] == '=')
        bad("':=' is not supported: only = and +=");
    if (sep[1] == ':')
        bad("'::' is not supported: double-colon rules");
    const char *rest = sep + 1;
    const char *more = separator(rest);
    if (more != NULL && *more == '=')
        bad("'TARGET: NAME = VALUE' is not supported: target-specific variables");
    if (strpbrk(rest, ";|") != NULL)
        bad("'%s' is not supported: a recipe on the rule's line, or order-only prerequisites",
            strchr(rest, ';') ? ";" : "|");
    char *left = xstrndup(s, (size_t)(sep - s));
    char *tx = expand(left, file, lineno), *px = expand(rest, file, lineno);
    free(left);
    Array targets, prereqs;
    split(tx, &targets);
    split(px, &prereqs);
    free(tx);
    free(px);
    if (targets.len == 0)
        bad("a rule with no target");

    Rule *r = xmalloc(sizeof *r);
    array_init(&r->targets, sizeof(long));
    r->prereqs = prereqs;
    r->recipe = NULL;
    *rule = r;
    for (size_t i = 0; i < targets.len; i++) {
        const char *t = *(char **)array_at(&targets, i);
        if (strchr(t, '%') != NULL)
            bad("'%s' is not supported: pattern rules", t);
        if (t[0] == '.' && strchr(t, '/') == NULL && strcmp(t, ".PHONY") != 0)
            bad("'%s' is not supported: special targets and suffix rules", t);
    }
    if (strcmp(*(char **)array_at(&targets, 0), ".PHONY") == 0) {
        if (targets.len != 1)
            bad(".PHONY must be the only target of its rule");
        for (size_t j = 0; j < prereqs.len; j++)
            target(g, graph_node(g, *(char **)array_at(&prereqs, j)))->phony = 1;
    } else {
        add_rule(g, r, &targets, &prereqs);
        const char *first = *(char **)array_at(&targets, 0);
        if (default_goal < 0 && (first[0] != '.' || strchr(first, '/') != NULL))
            default_goal = graph_find(g, first);
    }
    free_words(&targets);
}

/* Read the makefile at path into g; from and from_line: the include line
 * that names it, if any. */
static void read_file(Graph *g, const char *path, const char *from, long from_line)
{
    FILE *f = fopen(path, "rb");
    if (f == NULL) {
        if (from != NULL)
            die("%s:%ld: %s: %s", from, from_line, path, strerror(errno));
        die("%s: %s", path, strerror(errno));
    }
    Array text;
    array_init(&text, 1);
    int c;
    while ((c = getc(f)) != EOF)
        *(char *)array_push(&text) = (char)c;
    fclose(f);
    const char *file = xstrndup(path, strlen(path));   /* kept: recipes point at it */
    const char *t = text.data;
    size_t size = text.len, p = 0;
    long lineno = 0;
    Rule *rule = NULL;
    Array line;
    array_init(&line, 1);

    while (p < size) {
        long first = lineno + 1;
        /* a recipe line: one that starts with a tab, under a rule */
        int tab = t[p] == '\t';
        int recipe = tab && rule != NULL;
        array_clear(&line);
        for (;;) {
            size_t e = p;
            while (e < size && t[e] != '\n')
                e++;
            lineno++;
            size_t bs = 0;
            while (e - bs > p && t[e - bs - 1] == '\\')
                bs++;
            int more = bs % 2 == 1 && e < size;
            if (recipe) {
                /* kept as written, backslash and newline too: the shell joins them */
                put(&line, t + p, e - p);
                if (more)
                    put(&line, "\n", 1);
            } else {
                /* the backslash, the newline and the blanks around them: one space */
                size_t n = e - p - (more ? 1 : 0);
                put(&line, t + p, n);
                if (more) {
                    while (line.len > 0 && (line.data[line.len - 1] == ' ' || line.data[line.len - 1] == '\t'))
                        line.len--;
                    put(&line, " ", 1);
                }
            }
            p = e < size ? e + 1 : e;
            if (!more)
                break;
            if (recipe) {
                if (p < size && t[p] == '\t')
                    p++;                    /* a continued recipe line's own tab goes */
            } else {
                while (p < size && (t[p] == ' ' || t[p] == '\t'))
                    p++;
            }
        }
        put(&line, "", 1);
        if (recipe) {
            if (rule->targets.len == 0)
                continue;                   /* under .PHONY: nothing to run */
            if (rule->recipe == NULL)
                start_recipe(g, rule, file, first);
            *(char **)array_push(&rule->recipe->lines) = xstrndup(line.data + 1, line.len - 2);
        } else {
            makefile_line(g, line.data, tab, &rule, file, first);
        }
    }
    if (rule != NULL) {
        end_rule(rule);
        free(rule);
    }
    array_free(&line);
    array_free(&text);
}

void read_makefile(Graph *g, const char *path)
{
    read_file(g, path, NULL, 0);
}
