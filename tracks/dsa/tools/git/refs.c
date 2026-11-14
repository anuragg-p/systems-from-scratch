/*
 * refs.c - names for commits.
 *
 * A branch is a file, .git/refs/heads/main, holding the 40-digit name of
 * a commit and a newline; committing on it writes the new commit's name
 * there. HEAD (.git/HEAD) says which branch is checked out, as "ref:
 * refs/heads/main", or holds a commit's name itself (a "detached" HEAD).
 * Branches the real git has packed are in .git/packed-refs, a line each.
 *
 * On the command line, after any name: ~N is the Nth first parent (main~2
 * is main's parent's parent), ^N the Nth parent (a merge's second parent
 * is main^2; ^ alone is ^1), ^{tree} the commit's tree.
 */
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

#include "git.h"

/* The name in a ref's file: 40 digits, and a newline or nothing. */
static int parse_name(const char *text, size_t n, unsigned char name[20])
{
    if (n < 40 || (n > 40 && !(n == 41 && text[40] == '\n')))
        return -1;
    return sha1_unhex(text, name);
}

/* The name packed-refs gives ref, if it has it. */
static int packed_ref(const char *ref, unsigned char name[20])
{
    size_t size;
    char *text = read_file(".git/packed-refs", &size);
    if (text == NULL)
        return -1;
    int found = -1;
    size_t want = strlen(ref);
    for (char *line = text; line < text + size && found < 0;) {
        char *end = memchr(line, '\n', (size_t)(text + size - line));
        if (end == NULL)
            end = text + size;
        if (end - line == 41 + (long)want && line[40] == ' ' && memcmp(line + 41, ref, want) == 0)
            found = sha1_unhex(line, name);
        line = end + 1;
    }
    free(text);
    return found;
}

int ref_read(const char *ref, unsigned char name[20])
{
    // @build 10.03 read a ref: a name, or a link to another ref to read
    char path[PATH_MAX];
    for (int depth = 0; depth < 5; depth++) {
        if (snprintf(path, sizeof path, ".git/%s", ref) >= (int)sizeof path)
            die("%.40s...: a ref name too long", ref);
        size_t n;
        char *text = read_file(path, &n);
        if (text == NULL)
            return packed_ref(ref, name);
        if (n > 5 && memcmp(text, "ref: ", 5) == 0) {
            static char next[PATH_MAX];
            size_t len = strcspn(text + 5, "\n");
            if (len == 0 || len >= sizeof next || strstr(text + 5, "..") != NULL)
                die("%s is damaged: it points at no ref", path);
            memcpy(next, text + 5, len);
            next[len] = '\0';
            free(text);
            ref = next;
            continue;
        }
        if (parse_name(text, n, name) != 0)
            die("%s is damaged: it holds no object's name", path);
        free(text);
        return 0;
    }
    die("%s: refs that point at refs, five deep or more", ref);
    // @end
}

char *head_branch(void)
{
    size_t n;
    char *text = read_file(".git/HEAD", &n);
    if (text == NULL)
        die("this repository has no HEAD");
    if (n > 5 && memcmp(text, "ref: ", 5) == 0) {
        size_t len = strcspn(text + 5, "\n");
        char *b = xstrndup(text + 5, len);
        free(text);
        if (strncmp(b, "refs/", 5) != 0 || strstr(b, "..") != NULL)
            die(".git/HEAD is damaged: it points at '%s'", b);
        return b;
    }
    free(text);
    return NULL;
}

int branch_name_ok(const char *name)
{
    size_t n = strlen(name);
    if (n == 0 || name[0] == '-' || name[0] == '/' || name[n - 1] == '/' || name[n - 1] == '.' ||
        strstr(name, "..") != NULL || strstr(name, "//") != NULL || strstr(name, "@{") != NULL ||
        (n >= 5 && strcmp(name + n - 5, ".lock") == 0) || strcmp(name, "HEAD") == 0)
        return 0;
    for (const char *p = name; *p; p++)
        if ((unsigned char)*p <= ' ' || *p == 0x7f || strchr("~^:?*[\\", *p) != NULL)
            return 0;
    return 1;
}

void ref_write(const char *ref, const unsigned char name[20])
{
    // @build 10.03 point a ref at a commit: a new file, renamed over the old one
    char path[PATH_MAX], hex[42];
    repo_must_write("moving a ref");
    if (snprintf(path, sizeof path, ".git/%s", ref) >= (int)sizeof path)
        die("%.40s...: a ref name too long", ref);
    char *slash = strrchr(path, '/');
    *slash = '\0';
    make_dirs(path);
    *slash = '/';
    sha1_hex(name, hex);
    hex[40] = '\n';
    write_file_locked(path, hex, 41);
    if (git_tracing())
        trace("ref: %s is now %s", ref, short_hex(name));
    // @end
}

/* A name, without anything after it: an object's name or the start of one,
 * HEAD, refs/..., or a tag or branch. */
static void rev_base(const char *arg, size_t len, unsigned char name[20])
{
    char ref[PATH_MAX];
    if (len == 40 && resolve_hex(arg, len, name) == 0)
        return;
    if (len == 0 || len + 12 >= sizeof ref)
        die("'%.*s' names nothing", (int)len, arg);
    const char *tries[] = {"%.*s", "refs/%.*s", "refs/tags/%.*s", "refs/heads/%.*s"};
    for (size_t t = 0; t < 4; t++) {
        snprintf(ref, sizeof ref, tries[t], (int)len, arg);
        if (t == 0 && strcmp(ref, "HEAD") != 0 && strncmp(ref, "refs/", 5) != 0)
            continue;
        if (strstr(ref, "..") != NULL)
            break;
        if (ref_read(ref, name) == 0)
            return;
        if (t == 0 && strcmp(ref, "HEAD") == 0) {
            char *b = head_branch();
            if (b == NULL)
                die("HEAD names no commit");
            die("HEAD is on %s, which has no commits yet", b + (strncmp(b, "refs/heads/", 11) == 0 ? 11 : 0));
        }
    }
    if (resolve_hex(arg, len, name) == 0)
        return;
    die("'%.*s' names nothing: not an object's name, a branch or a tag", (int)len, arg);
}

void rev_parse(const char *arg, unsigned char name[20])
{
    // @build 10.03 a name on the command line: a ref or an object, then ~N, ^N and ^{tree} after it
    size_t base = strcspn(arg, "~^");
    rev_base(arg, base, name);
    const char *p = arg + base;
    while (*p) {
        char op = *p++;
        if (op == '^' && strncmp(p, "{tree}", 6) == 0) {
            Object o;
            object_read(name, &o);
            if (o.type == OBJ_COMMIT) {
                Commit *c = commit_read(name);
                memcpy(name, c->tree, 20);
                commit_free(c);
            } else if (o.type != OBJ_TREE) {
                die("%s: %s is a %s, which has no tree", arg, short_hex(name), type_name(o.type));
            }
            object_free(&o);
            p += 6;
            continue;
        }
        long k = 1;
        if (*p >= '0' && *p <= '9') {
            char *end;
            k = strtol(p, &end, 10);
            if (k > 1000000)
                die("%s: %ld generations is more than this git will look", arg, k);
            p = end;
        }
        if (op == '^' && k == 0)
            continue;                        /* ^0: the commit itself */
        for (long step = 0; step < (op == '~' ? k : 1); step++) {
            Commit *c = commit_read(name);
            size_t which = op == '~' ? 0 : (size_t)k - 1;
            if (which >= c->parents.len)
                die("%s: %s has %zu parent%s, so no parent %zu", arg, short_hex(name), c->parents.len,
                    c->parents.len == 1 ? "" : "s", which + 1);
            memcpy(name, array_at(&c->parents, which), 20);
            commit_free(c);
        }
    }
    // @end
}
