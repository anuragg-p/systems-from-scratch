/*
 * repo.c - which repository git works on, what its config says, and
 * reading and replacing whole files in it.
 *
 * A deliberate difference from the real git: this one looks for the
 * repository only in the directory it is given (-C DIR, or the current
 * one) and never walks up into the directories above. The real git, run
 * in a/b/c, uses the first .git it finds in c, b, a or above; this one,
 * run anywhere inside another repository, says there is none. It also
 * ignores GIT_DIR, GIT_WORK_TREE and every other GIT_ variable but the
 * author's and committer's, and reads no config but .git/config.
 *
 * And it changes only repositories its own init made: init writes
 * "[dsa] ours = true" into .git/config, and every command that writes
 * checks for it. It reads any repository of loose objects; it changes
 * none that it did not make.
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>

#include "git.h"

Repo repo;

/* ------------------------------------------------------------ files */

char *read_file(const char *path, size_t *size)
{
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        if (errno == ENOENT || errno == ENOTDIR)
            return NULL;
        die("%s: %s", path, strerror(errno));
    }
    struct stat sb;
    if (fstat(fd, &sb) != 0)
        die("%s: %s", path, strerror(errno));
    if (!S_ISREG(sb.st_mode))
        die("%s: not a file", path);
    size_t cap = (size_t)sb.st_size + 1, n = 0;
    char *buf = xmalloc(cap);
    for (;;) {
        if (n + 1 == cap) {                  /* it grew while we read it */
            char *bigger = xmalloc(cap * 2);
            memcpy(bigger, buf, n);
            free(buf);
            buf = bigger;
            cap *= 2;
        }
        ssize_t got = read(fd, buf + n, cap - 1 - n);
        if (got < 0) {
            if (errno == EINTR)
                continue;
            die("%s: %s", path, strerror(errno));
        }
        if (got == 0)
            break;
        n += (size_t)got;
    }
    close(fd);
    buf[n] = '\0';
    *size = n;
    return buf;
}

static void write_all(int fd, const void *data, size_t n, const char *path)
{
    const char *p = data;
    while (n > 0) {
        ssize_t put = write(fd, p, n);
        if (put < 0) {
            if (errno == EINTR)
                continue;
            die("%s: %s", path, strerror(errno));
        }
        p += put;
        n -= (size_t)put;
    }
}

void write_file_locked(const char *path, const void *data, size_t n)
{
    char lock[PATH_MAX];
    if (snprintf(lock, sizeof lock, "%s.lock", path) >= (int)sizeof lock)
        die("%s: the path is too long", path);
    int fd = open(lock, O_WRONLY | O_CREAT | O_EXCL, 0666);
    if (fd < 0) {
        if (errno == EEXIST)
            die("%s exists: another git is at work here, or one stopped half way (remove it if not)", lock);
        die("%s: %s", lock, strerror(errno));
    }
    write_all(fd, data, n, lock);
    if (close(fd) != 0 || rename(lock, path) != 0) {
        int e = errno;
        unlink(lock);
        die("%s: %s", path, strerror(e));
    }
}

void make_dirs(const char *path)
{
    char buf[PATH_MAX];
    size_t n = strlen(path);
    if (n == 0 || n >= sizeof buf)
        die("%s: not a directory this git can make", path);
    memcpy(buf, path, n + 1);
    for (size_t i = 1; i <= n; i++) {
        if (buf[i] != '/' && buf[i] != '\0')
            continue;
        char c = buf[i];
        buf[i] = '\0';
        if (mkdir(buf, 0777) != 0 && errno != EEXIST)
            die("%s: %s", buf, strerror(errno));
        buf[i] = c;
    }
}

/* ------------------------------------------------------------ tracing */

static int tracing = 0;

void trace_setup(void)
{
    const char *s = getenv("DS_TRACE");
    tracing = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    /* The library's parts read DS_TRACE themselves: inflate would print
     * every byte of every object. They see it only with DS_TRACE=all. */
    if (s != NULL && strcmp(s, "all") != 0)
        unsetenv("DS_TRACE");
}

int git_tracing(void)
{
    return tracing;
}

void trace(const char *fmt, ...)
{
    va_list ap;
    fflush(stdout);
    fputs("trace: ", stderr);
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
    fputc('\n', stderr);
}

/* ------------------------------------------------------------ config */

/* .git/config, as git writes it: "[section]" or "[section "sub"]" lines,
 * then "key = value" lines; # and ; start comments; a value may be
 * quoted. Names are not case-sensitive. A key under a subsection is never
 * returned (this git asks only for plain ones). */
char *config_get(const char *section, const char *key)
{
    size_t size;
    char *text = read_file(".git/config", &size);
    if (text == NULL)
        return NULL;
    char *found = NULL;
    char sect[64] = "";
    int plain = 0;                       /* in a section without a subsection */
    char *line = text;
    while (line < text + size) {
        char *end = memchr(line, '\n', (size_t)(text + size - line));
        if (end == NULL)
            end = text + size;
        *end = '\0';
        char *p = line;
        while (*p == ' ' || *p == '\t')
            p++;
        if (*p == '[') {
            size_t n = 0;
            p++;
            while (*p && *p != ']' && *p != ' ' && *p != '"' && n + 1 < sizeof sect)
                sect[n++] = *p++;
            sect[n] = '\0';
            plain = *p == ']';
        } else if (*p && *p != '#' && *p != ';' && plain && strcasecmp(sect, section) == 0) {
            char *k = p;
            while (*p && *p != '=' && *p != ' ' && *p != '\t')
                p++;
            size_t klen = (size_t)(p - k);
            while (*p == ' ' || *p == '\t')
                p++;
            if (klen == strlen(key) && strncasecmp(k, key, klen) == 0) {
                char *v = xmalloc(strlen(p) + 5);
                size_t n = 0;
                int quoted = 0;
                if (*p == '=') {
                    p++;
                    while (*p == ' ' || *p == '\t')
                        p++;
                    for (; *p; p++) {
                        if (*p == '"') {
                            quoted = !quoted;
                        } else if (*p == '\\' && p[1]) {
                            p++;
                            v[n++] = *p == 'n' ? '\n' : *p == 't' ? '\t' : *p;
                        } else if (!quoted && (*p == '#' || *p == ';')) {
                            break;
                        } else {
                            v[n++] = *p;
                        }
                    }
                    while (n > 0 && (v[n - 1] == ' ' || v[n - 1] == '\t' || v[n - 1] == '\r'))
                        n--;
                } else {
                    memcpy(v, "true", 4);    /* a key alone is a boolean that is true */
                    n = 4;
                }
                v[n] = '\0';
                free(found);
                found = v;                   /* the last one wins */
            }
        }
        line = end + 1;
    }
    free(text);
    return found;
}

/* ------------------------------------------------------------ the repository */

void repo_open(void)
{
    struct stat sb;
    if (lstat(".git", &sb) != 0)
        die("not a git repository: there is no .git here (this git looks only in the directory "
            "it is given, never in the ones above it)");
    if (S_ISREG(sb.st_mode))
        die(".git is a file, not a directory: a linked worktree or a submodule, which this git does not open");
    if (!S_ISDIR(sb.st_mode))
        die(".git is not a directory");
    if (stat(".git/objects", &sb) != 0 || !S_ISDIR(sb.st_mode))
        die("not a git repository: .git has no objects directory");
    DIR *d = opendir(".git/objects/pack");
    if (d != NULL) {
        struct dirent *de;
        while ((de = readdir(d)) != NULL) {
            size_t n = strlen(de->d_name);
            if (n > 5 && strcmp(de->d_name + n - 5, ".pack") == 0)
                die("this repository has packed objects (.git/objects/pack/%s), and this git reads only "
                    "loose objects", de->d_name);
        }
        closedir(d);
    }
    char *v = config_get("core", "repositoryformatversion");
    if (v != NULL && strcmp(v, "0") != 0 && strcmp(v, "1") != 0)
        die("this repository's format is version %s, and this git knows versions 0 and 1", v);
    free(v);
    v = config_get("extensions", "objectformat");
    if (v != NULL && strcasecmp(v, "sha1") != 0)
        die("this repository names its objects with %s (extensions.objectformat), and this git "
            "only with SHA-1", v);
    free(v);
    v = config_get("extensions", "refstorage");
    if (v != NULL && strcasecmp(v, "files") != 0)
        die("this repository keeps its refs as %s (extensions.refstorage), and this git only as files", v);
    free(v);
    v = config_get("dsa", "ours");
    repo.writable = v != NULL && strcmp(v, "true") == 0;
    free(v);
}

void repo_must_write(const char *what)
{
    if (!repo.writable)
        die("%s: this git changes only repositories its own init made (.git/config has no "
            "\"[dsa] ours = true\"); it reads this one, but will not write to it", what);
}

static void write_new(const char *path, const char *text)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0666);
    if (fd < 0)
        die("%s: %s", path, strerror(errno));
    write_all(fd, text, strlen(text), path);
    close(fd);
}

void repo_init(const char *dir, const char *branch, int quiet)
{
    // @build 10.01 a new repository: .git, its objects and refs, HEAD and the config
    if (dir != NULL) {
        make_dirs(dir);
        if (chdir(dir) != 0)
            die("%s: %s", dir, strerror(errno));
    }
    struct stat sb;
    if (lstat(".git", &sb) == 0)
        die("%s/.git is there already: this git does not make a repository twice", dir ? dir : ".");
    const char *dirs[] = {".git", ".git/objects", ".git/refs", ".git/refs/heads", ".git/refs/tags"};
    for (size_t i = 0; i < sizeof dirs / sizeof dirs[0]; i++)
        if (mkdir(dirs[i], 0777) != 0)
            die("%s: %s", dirs[i], strerror(errno));
    char head[300];
    snprintf(head, sizeof head, "ref: refs/heads/%s\n", branch);
    write_new(".git/HEAD", head);
    write_new(".git/config",
              "[core]\n"
              "\trepositoryformatversion = 0\n"
              "\tfilemode = true\n"
              "\tbare = false\n"
              "# Made by the git of the dsa track (tracks/dsa/tools/git), which changes\n"
              "# only repositories that say this:\n"
              "[dsa]\n"
              "\tours = true\n");
    if (!quiet) {
        char where[PATH_MAX];
        if (realpath(".git", where) == NULL)
            die(".git: %s", strerror(errno));
        printf("Initialized empty Git repository in %s/\n", where);
    }
    // @end
}
