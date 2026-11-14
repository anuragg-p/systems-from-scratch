/*
 * git - a version control system's core, on the library of this track.
 *
 *   git [-C DIR] COMMAND [ARG ...]
 *
 *   init [-q] [-b BRANCH] [DIR]   a new, empty repository (the branch: main)
 *   hash-object [-w] [-t TYPE] [--stdin] [FILE ...]
 *                                 each file's object name; with -w, stored
 *   cat-file (-t | -s | -e | -p) NAME, or cat-file TYPE NAME
 *                                 an object's type, size, whether it is
 *                                 there, or its content
 *   add PATH ...                  files into the index (a directory: all     @from 10.02
 *                                 of it; "." for everything)                 @from 10.02
 *   ls-files [-s]                 the index: its paths, or with their        @from 10.02
 *                                 modes and blobs                            @from 10.02
 *   write-tree [--algo=NAME]      the index as trees; the top one's name     @from 10.02
 *   ls-tree [-r] [-t] NAME        a tree's entries (-r: every file below)    @from 10.02
 *   commit-tree TREE [-p PARENT ...] [-m MESSAGE ...]                        @from 10.03
 *                                 a commit of that tree; its name            @from 10.03
 *   commit [-q] [--allow-empty] -m MESSAGE                                  @from 10.03
 *                                 a commit of the index on HEAD's branch     @from 10.03
 *   log [--algo=NAME] [--oneline] [-n N] [NAME ...]                          @from 10.03
 *                                 the history, newest first                  @from 10.03
 *   branch [NAME [START]]         the branches, or a new one                 @from 10.03
 *   diff [--algo=NAME] [-U N] NAME NAME                                      @from 10.04
 *                                 what changed from one commit to another    @from 10.04
 *   merge-base [--algo=NAME] [--all] NAME NAME                               @from 10.04
 *                                 their best common ancestor                 @from 10.04
 *
 * -C DIR works in DIR, which must be the top of a repository: this git
 * never looks for one in the directories above (repo.c says why). A NAME
 * is an object's name, or its first 4 or more digits;
 * HEAD, a branch, and ~N, ^N or ^{tree} after any of them.        @from 10.03
 * Every error is status 2, with a message.
 *
 * The --algo options keep the obvious way runnable beside the better one:
 *   write-tree, commit   all (build every tree), cache (only those whose  @from 10.02
 *                        files changed, the default)                      @from 10.02
 *   log                  list (plain lists), heap (a heap and a hash      @from 10.03
 *                        table, the default)                              @from 10.03
 *   diff                 all (read everything), skip (pass over what is   @from 10.04
 *                        the same, the default)                           @from 10.04
 *   merge-base           rewalk (walk the history again for each          @from 10.04
 *                        commit), paint (one walk, the default)           @from 10.04
 *
 * DS_STATS=1 prints the counts of every structure used; DS_TRACE=1 each
 * step git takes (DS_TRACE=all the library's too).
 */
#include <dirent.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "git.h"

void object_stats(void);

/* The --algo=NAME of a command: the index of name in names, or an error
 * listing them. */
static int pick(const char *name, const char *const *names, int n)
{
    char have[200] = "";
    for (int i = 0; i < n; i++) {
        if (strcmp(name, names[i]) == 0)
            return i;
        strcat(strcat(have, i ? ", " : ""), names[i]);
    }
    die("no --algo '%s' (have: %s)", name, have);
}

static void unknown(const char *cmd, const char *arg)
{
    die("%s: unknown option %s", cmd, arg);
}

/* ------------------------------------------------------------ 10.01 */

static int cmd_init(int argc, char **argv)
{
    int quiet = 0;
    const char *branch = "main", *dir = NULL;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-q") == 0)
            quiet = 1;
        else if (strcmp(argv[i], "-b") == 0 && i + 1 < argc)
            branch = argv[++i];
        else if (argv[i][0] == '-')
            unknown("init", argv[i]);
        else if (dir == NULL)
            dir = argv[i];
        else
            die("usage: git init [-q] [-b BRANCH] [DIR]");
    }
    if (*branch == '\0' || branch[0] == '-' || strstr(branch, "..") || strcspn(branch, " ~^:?*[\\") != strlen(branch))
        die("'%s' is not a name a branch can have", branch);
    repo_init(dir, branch, quiet);
    return 0;
}

static int cmd_hash_object(int argc, char **argv)
{
    // @build 10.01 hash-object: a file's bytes as a blob, its name printed, and stored with -w
    int write = 0, from_stdin = 0, type = OBJ_BLOB, i;
    for (i = 1; i < argc && argv[i][0] == '-' && argv[i][1]; i++) {
        if (strcmp(argv[i], "-w") == 0)
            write = 1;
        else if (strcmp(argv[i], "--stdin") == 0)
            from_stdin = 1;
        else if (strcmp(argv[i], "-t") == 0 && i + 1 < argc) {
            type = type_from_name(argv[i + 1], strlen(argv[i + 1]));
            if (type == OBJ_BAD)
                die("hash-object: no type '%s' (have: blob, tree, commit, tag)", argv[i + 1]);
            i++;
        } else
            unknown("hash-object", argv[i]);
    }
    if (write)
        repo_open();
    if (!from_stdin && i == argc)
        die("usage: git hash-object [-w] [-t TYPE] [--stdin] [FILE ...]");
    for (int k = from_stdin ? i - 1 : i; k < argc; k++) {
        size_t n;
        char *data;
        if (k < i) {                         /* --stdin: standard input, once */
            Array in;
            array_init(&in, 1);
            int c;
            while ((c = getchar()) != EOF)
                *(char *)array_push(&in) = (char)c;
            n = in.len;
            data = xstrndup(in.data ? in.data : "", n);
            array_free(&in);
        } else if ((data = read_file(argv[k], &n)) == NULL) {
            die("%s: no such file", argv[k]);
        }
        unsigned char name[20];
        char hex[41];
        if (write)
            object_write(type, data, n, name);
        else
            object_name(type, data, n, name);
        sha1_hex(name, hex);
        printf("%s\n", hex);
        free(data);
    }
    return 0;
    // @end
}

// @from 10.02
/* A tree's entries as ls-tree prints them: "100644 blob NAME<tab>path";
 * with recurse, the files of its subdirectories instead of them (and the
 * subdirectories too with show_trees). */
static void print_tree(const unsigned char name[20], const char *prefix, int recurse, int show_trees)
{
    Object o;
    Array entries;
    object_read(name, &o);
    tree_entries(name, &o, &entries);
    for (size_t i = 0; i < entries.len; i++) {
        TreeEntry *e = array_at(&entries, i);
        size_t plen = strlen(prefix);
        char *path = xmalloc(plen + e->len + 2);
        memcpy(path, prefix, plen);
        memcpy(path + plen, e->name, e->len);
        path[plen + e->len] = '\0';
        if (!recurse || e->mode != MODE_TREE || show_trees) {
            char hex[41];
            sha1_hex(e->oid, hex);
            printf("%06o %s %s\t", e->mode, mode_type(e->mode), hex);
            put_path(stdout, "", path, plen + e->len);
            putchar('\n');
        }
        if (recurse && e->mode == MODE_TREE) {
            strcat(path, "/");
            print_tree(e->oid, path, recurse, show_trees);
        }
        free(path);
    }
    array_free(&entries);
    object_free(&o);
}
// @end

static int cmd_cat_file(int argc, char **argv)
{
    // @build 10.01 cat-file: an object's type, its size, or its bytes
    if (argc != 3)
        die("usage: git cat-file (-t | -s | -e | -p) NAME, or git cat-file TYPE NAME");
    const char *how = argv[1];
    repo_open();
    unsigned char name[20];
    if (strcmp(how, "-e") == 0) {            /* there or not: no message either way */
        if (resolve_hex(argv[2], strlen(argv[2]), name) == 0 && strlen(argv[2]) == 40)
            return object_exists(name) ? 0 : 1;
    }
    resolve(argv[2], name);
    Object o;
    object_read(name, &o);
    if (strcmp(how, "-e") == 0)
        return 0;
    if (strcmp(how, "-t") == 0) {
        printf("%s\n", type_name(o.type));
    } else if (strcmp(how, "-s") == 0) {
        printf("%zu\n", o.size);
    } else if (strcmp(how, "-p") == 0 && o.type == OBJ_TREE) {
        // @from 10.02
        print_tree(name, "", 0, 0);
        // @else
        // die("%s is a tree, which this git cannot show", argv[2]);
        // @end
    } else if (strcmp(how, "-p") == 0 || type_from_name(how, strlen(how)) == o.type) {
        fwrite(o.data, 1, o.size, stdout);
    } else if (type_from_name(how, strlen(how)) != OBJ_BAD) {
        die("%s is a %s, not a %s", argv[2], type_name(o.type), how);
    } else {
        unknown("cat-file", how);
    }
    object_free(&o);
    return 0;
    // @end
}

// @from 10.02
/* ------------------------------------------------------------ 10.02 */

static const char *const tree_algos[] = {"all", "cache"};

/* A path as the index keeps it: no "./" in front, no '/' at the end, never
 * outside the repository; "." is everything (""). */
static char *pathspec(const char *arg)
{
    if (arg[0] == '/')
        die("%s: give paths from the top of the repository, not from /", arg);
    while (arg[0] == '.' && arg[1] == '/')
        arg += 2;
    size_t n = strlen(arg);
    while (n > 0 && arg[n - 1] == '/')
        n--;
    if (n == 1 && arg[0] == '.')
        n = 0;
    char *p = xstrndup(arg, n);
    if (strcmp(p, "..") == 0 || strncmp(p, "../", 3) == 0 || strstr(p, "/../") != NULL ||
        (n >= 3 && strcmp(p + n - 3, "/..") == 0))
        die("%s is outside the repository", arg);
    return p;
}

static int cmd_add(int argc, char **argv)
{
    if (argc < 2)
        die("usage: git add PATH ...");
    for (int i = 1; i < argc; i++)
        if (argv[i][0] == '-' && argv[i][1])
            unknown("add", argv[i]);
    repo_open();
    repo_must_write("add");
    char **paths = xmalloc((size_t)argc * sizeof *paths);
    for (int i = 1; i < argc; i++)
        paths[i - 1] = pathspec(argv[i]);
    Index ix;
    index_read(&ix);
    index_add(&ix, paths, (size_t)argc - 1);
    index_write(&ix);
    return 0;
}

static int cmd_ls_files(int argc, char **argv)
{
    int stage = argc == 2 && strcmp(argv[1], "-s") == 0;
    if (argc > 2 || (argc == 2 && !stage))
        die("usage: git ls-files [-s]");
    repo_open();
    Index ix;
    index_read(&ix);
    for (size_t i = 0; i < ix.entries.len; i++) {
        IndexEntry *e = array_at(&ix.entries, i);
        if (stage) {
            char hex[41];
            sha1_hex(e->oid, hex);
            printf("%06o %s 0\t", e->mode, hex);
        }
        put_path(stdout, "", e->path, e->len);
        putchar('\n');
    }
    return 0;
}

static int cmd_write_tree(int argc, char **argv)
{
    int algo = 1;
    for (int i = 1; i < argc; i++) {
        if (strncmp(argv[i], "--algo=", 7) == 0)
            algo = pick(argv[i] + 7, tree_algos, 2);
        else
            unknown("write-tree", argv[i]);
    }
    repo_open();
    repo_must_write("write-tree");
    Index ix;
    unsigned char tree[20];
    char hex[41];
    index_read(&ix);
    write_tree(&ix, algo == 1, tree);
    index_write(&ix);                        /* the cached trees, made good again */
    sha1_hex(tree, hex);
    printf("%s\n", hex);
    return 0;
}

static int cmd_ls_tree(int argc, char **argv)
{
    int recurse = 0, show_trees = 0, i;
    for (i = 1; i < argc && argv[i][0] == '-'; i++) {
        if (strcmp(argv[i], "-r") == 0)
            recurse = 1;
        else if (strcmp(argv[i], "-t") == 0)
            show_trees = 1;
        else
            unknown("ls-tree", argv[i]);
    }
    if (i + 1 != argc)
        die("usage: git ls-tree [-r] [-t] NAME");
    repo_open();
    unsigned char tree[20];
    tree_of(argv[i], tree);
    print_tree(tree, "", recurse, show_trees || !recurse);
    return 0;
}
// @end

// @from 10.03
/* ------------------------------------------------------------ 10.03 */

static const char *const log_algos[] = {"list", "heap"};

/* -m MESSAGE options, git's way: each a paragraph after a blank line,
 * ending in a newline. */
static char *messages(char *msg, const char *more)
{
    size_t n = msg ? strlen(msg) : 0, m = strlen(more);
    char *out = xmalloc(n + m + 3);
    out[0] = '\0';
    if (msg) {
        strcpy(out, msg);
        strcat(out, "\n");
        free(msg);
    }
    strcat(out, more);
    if (m > 0 && more[m - 1] != '\n')
        strcat(out, "\n");
    return out;
}

static int cmd_commit_tree(int argc, char **argv)
{
    Array parents;
    char *msg = NULL;
    const char *tree_arg = NULL;
    array_init(&parents, 20);
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-p") == 0 && i + 1 < argc) {
            repo_open();
            unsigned char p[20];
            resolve(argv[++i], p);
            memcpy(array_push(&parents), p, 20);
        } else if (strcmp(argv[i], "-m") == 0 && i + 1 < argc) {
            msg = messages(msg, argv[++i]);
        } else if (argv[i][0] == '-') {
            unknown("commit-tree", argv[i]);
        } else if (tree_arg == NULL) {
            tree_arg = argv[i];
        } else {
            die("usage: git commit-tree TREE [-p PARENT ...] [-m MESSAGE ...]");
        }
    }
    if (tree_arg == NULL)
        die("usage: git commit-tree TREE [-p PARENT ...] [-m MESSAGE ...]");
    repo_open();
    repo_must_write("commit-tree");
    if (msg == NULL) {                       /* the message from standard input */
        Array in;
        array_init(&in, 1);
        int c;
        while ((c = getchar()) != EOF)
            *(char *)array_push(&in) = (char)c;
        msg = xstrndup(in.data ? in.data : "", in.len);
        array_free(&in);
    }
    unsigned char tree[20], name[20];
    char hex[41];
    tree_of(tree_arg, tree);
    for (size_t i = 0; i < parents.len; i++)
        commit_free(commit_read(array_at(&parents, i)));     /* each must be a commit */
    commit_create(tree, (unsigned char *)parents.data, parents.len, msg, name);
    sha1_hex(name, hex);
    printf("%s\n", hex);
    return 0;
}

static int cmd_commit(int argc, char **argv)
{
    int quiet = 0, allow_empty = 0, algo = 1;
    char *msg = NULL;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-m") == 0 && i + 1 < argc)
            msg = messages(msg, argv[++i]);
        else if (strcmp(argv[i], "-q") == 0)
            quiet = 1;
        else if (strcmp(argv[i], "--allow-empty") == 0)
            allow_empty = 1;
        else if (strncmp(argv[i], "--algo=", 7) == 0)
            algo = pick(argv[i] + 7, tree_algos, 2);
        else
            unknown("commit", argv[i]);
    }
    if (msg == NULL)
        die("commit: give the message with -m (this git starts no editor)");
    char *clean = clean_message(msg);
    if (*clean == '\0')
        die("commit: the message is empty");
    repo_open();
    repo_must_write("commit");
    Index ix;
    unsigned char tree[20], parent[20], name[20];
    index_read(&ix);
    write_tree(&ix, algo == 1, tree);
    char *branch = head_branch();
    int has_parent = ref_read("HEAD", parent) == 0;
    if (!has_parent && ix.entries.len == 0 && !allow_empty) {
        printf("nothing to commit: the index is empty (git add puts files in it)\n");
        return 1;
    }
    if (has_parent && !allow_empty) {
        Commit *p = commit_read(parent);
        int same = memcmp(p->tree, tree, 20) == 0;
        commit_free(p);
        if (same) {
            index_write(&ix);
            printf("nothing to commit: the index is HEAD's tree\n");
            return 1;
        }
    }
    commit_create(tree, has_parent ? parent : NULL, has_parent ? 1 : 0, clean, name);
    ref_write(branch ? branch : "HEAD", name);
    index_write(&ix);
    if (!quiet) {
        char abbr[41];
        abbrev(name, abbr);
        size_t subject = strcspn(clean, "\n");
        printf("[%s%s %s] %.*s\n", branch ? branch + (strncmp(branch, "refs/heads/", 11) ? 0 : 11) : "detached HEAD",
               has_parent ? "" : " (root-commit)", abbr, (int)subject, clean);
    }
    return 0;
}

static int cmd_log(int argc, char **argv)
{
    int algo = 1, oneline = 0;
    long limit = -1;
    Array starts;
    array_init(&starts, 20);
    repo_open();
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strncmp(a, "--algo=", 7) == 0) {
            algo = pick(a + 7, log_algos, 2);
        } else if (strcmp(a, "--oneline") == 0) {
            oneline = 1;
        } else if ((strcmp(a, "-n") == 0 && i + 1 < argc) || (a[0] == '-' && a[1] >= '0' && a[1] <= '9')) {
            const char *v = a[1] == 'n' ? argv[++i] : a + 1;
            char *end;
            limit = strtol(v, &end, 10);
            if (*v == '\0' || *end != '\0' || limit < 0)
                die("log: -n wants a number, not '%s'", v);
        } else if (a[0] == '-') {
            unknown("log", a);
        } else {
            resolve(a, array_push(&starts));
        }
    }
    if (starts.len == 0) {
        if (ref_read("HEAD", array_push(&starts)) != 0) {
            char *b = head_branch();
            die("HEAD is on %s, which has no commits yet",
                b ? b + (strncmp(b, "refs/heads/", 11) ? 0 : 11) : "nothing");
        }
    }
    for (size_t i = 0; i < starts.len; i++)
        commit_free(commit_read(array_at(&starts, i)));      /* each must be a commit */
    log_walk((unsigned char *)starts.data, starts.len, algo == 0 ? LOG_LIST : LOG_HEAP, oneline, limit);
    return 0;
}

static int by_name(const void *a, const void *b, void *ctx)
{
    return strcmp(a, b);
}

static int cmd_branch(int argc, char **argv)
{
    repo_open();
    if (argc == 1) {                         /* list them, the one HEAD is on starred */
        char *head = head_branch();
        Array names;
        array_init(&names, sizeof(char *));
        DIR *d = opendir(".git/refs/heads");
        struct dirent *de;
        while (d != NULL && (de = readdir(d)) != NULL)
            if (de->d_name[0] != '.')
                *(char **)array_push(&names) = xstrndup(de->d_name, strlen(de->d_name));
        if (d != NULL)
            closedir(d);
        sort_merge((void **)names.data, names.len, by_name, NULL);
        for (size_t i = 0; i < names.len; i++) {
            char *n = *(char **)array_at(&names, i);
            int on = head && strncmp(head, "refs/heads/", 11) == 0 && strcmp(head + 11, n) == 0;
            printf("%s %s\n", on ? "*" : " ", n);
        }
        return 0;
    }
    if (argc > 3 || argv[1][0] == '-')
        die("usage: git branch [NAME [START]]");
    if (!branch_name_ok(argv[1]) || strchr(argv[1], '/') != NULL)
        die("'%s' is not a name a branch can have here", argv[1]);
    repo_must_write("branch");
    char ref[300];
    unsigned char name[20];
    snprintf(ref, sizeof ref, "refs/heads/%s", argv[1]);
    if (ref_read(ref, name) == 0)
        die("a branch named '%s' is there already", argv[1]);
    resolve(argc == 3 ? argv[2] : "HEAD", name);
    commit_free(commit_read(name));
    ref_write(ref, name);
    return 0;
}
// @end

// @from 10.04
/* ------------------------------------------------------------ 10.04 */

static const char *const diff_algos[] = {"all", "skip"};
static const char *const base_algos[] = {"rewalk", "paint"};

static int cmd_diff(int argc, char **argv)
{
    int algo = 1;
    long context = 3;
    const char *names[2];
    int n = 0;
    for (int i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strncmp(a, "--algo=", 7) == 0) {
            algo = pick(a + 7, diff_algos, 2);
        } else if (strncmp(a, "-U", 2) == 0) {
            const char *v = a[2] ? a + 2 : (i + 1 < argc ? argv[++i] : "");
            char *end;
            context = strtol(v, &end, 10);
            if (*v == '\0' || *end != '\0' || context < 0)
                die("diff: -U wants a number of lines, not '%s'", v);
        } else if (a[0] == '-') {
            unknown("diff", a);
        } else if (n < 2) {
            names[n++] = a;
        } else {
            n = 3;
        }
    }
    if (n != 2)
        die("usage: git diff [--algo=NAME] [-U N] NAME NAME (two commits or trees)");
    repo_open();
    unsigned char a[20], b[20];
    tree_of(names[0], a);
    tree_of(names[1], b);
    diff_trees(a, b, algo == 0 ? WALK_ALL : WALK_SKIP, context);
    return 0;
}

static int cmd_merge_base(int argc, char **argv)
{
    int algo = 1, all = 0, n = 0;
    unsigned char c[2][20];
    repo_open();
    for (int i = 1; i < argc; i++) {
        if (strncmp(argv[i], "--algo=", 7) == 0)
            algo = pick(argv[i] + 7, base_algos, 2);
        else if (strcmp(argv[i], "--all") == 0)
            all = 1;
        else if (argv[i][0] == '-')
            unknown("merge-base", argv[i]);
        else if (n < 2)
            resolve(argv[i], c[n++]);
        else
            n = 3;
    }
    if (n != 2)
        die("usage: git merge-base [--algo=NAME] [--all] NAME NAME");
    return merge_base(c[0], c[1], algo == 0 ? BASE_REWALK : BASE_PAINT, all) > 0 ? 0 : 1;
}
// @end

/* ------------------------------------------------------------ the commands */

static const struct {
    const char *name;
    int (*run)(int argc, char **argv);
} commands[] = {
    {"init", cmd_init},
    {"hash-object", cmd_hash_object},
    {"cat-file", cmd_cat_file},
    {"add", cmd_add},                        // @from 10.02
    {"ls-files", cmd_ls_files},              // @from 10.02
    {"write-tree", cmd_write_tree},          // @from 10.02
    {"ls-tree", cmd_ls_tree},                // @from 10.02
    {"commit-tree", cmd_commit_tree},        // @from 10.03
    {"commit", cmd_commit},                  // @from 10.03
    {"log", cmd_log},                        // @from 10.03
    {"branch", cmd_branch},                  // @from 10.03
    {"diff", cmd_diff},                      // @from 10.04
    {"merge-base", cmd_merge_base},          // @from 10.04
};

#define NCOMMANDS (sizeof commands / sizeof commands[0])

static void usage(const char *why)
{
    char have[400] = "";
    for (size_t i = 0; i < NCOMMANDS; i++)
        strcat(strcat(have, i ? ", " : ""), commands[i].name);
    if (why != NULL)
        die("no command '%s' (have: %s)", why, have);
    die("usage: git [-C DIR] COMMAND [ARG ...] (commands: %s)", have);
}

int main(int argc, char **argv)
{
    progname = "git";
    object_stats();
    trace_setup();
    int i = 1;
    while (i < argc && argv[i][0] == '-') {
        if (strcmp(argv[i], "-C") == 0 && i + 1 < argc) {
            if (chdir(argv[i + 1]) != 0)
                die("cannot work in %s: %s", argv[i + 1], strerror(errno));
            i += 2;
        } else {
            die("unknown option %s", argv[i]);
        }
    }
    if (i == argc)
        usage(NULL);
    for (size_t k = 0; k < NCOMMANDS; k++)
        if (strcmp(argv[i], commands[k].name) == 0) {
            int rc = commands[k].run(argc - i, argv + i);
            fflush(stdout);
            return ferror(stdout) ? 2 : rc;
        }
    usage(argv[i]);
}
