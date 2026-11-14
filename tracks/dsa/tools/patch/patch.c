/*
 * patch - apply a unified diff to the file it was made from.
 *
 *   patch [-p N] [-o OUTFILE] [-s] [-i PATCHFILE] [FILE [PATCHFILE]]
 *
 * The patch is read from PATCHFILE, or standard input. It is what "diff
 * -u" prints, for one file or several: for each, a "---" line and a "+++"
 * line naming the old file and the new, then hunks, each a header "@@
 * -l,n +k,m @@" and its lines: " " for a line kept, "-" for one deleted,
 * "+" for one inserted. Anything else between files ("diff -u a b",
 * "Index: x") is passed over.
 *
 * Each hunk's old lines, the kept and the deleted, must be in the file:
 * at the line the header says, or, when the file has gained or lost lines
 * above it since the diff was made, as near to that line as they are
 * found ("Hunk #2 succeeded at 40 (offset 3 lines)"). The hunk's new
 * lines, the kept and the inserted, take their place. When a hunk's lines
 * are nowhere to be found, the file is left as it was: patch says which
 * hunks do not apply, and exits with status 1. (The system's patch
 * applies the hunks that do apply, and saves the others to FILE.rej.)
 *
 *   FILE        the file to patch; without it, the file each "---" line
 *               names, or, when that does not exist, the "+++" line's
 *   -p N        strip N directories from the front of those names (a git
 *               diff names a/file and b/file: -p 1)
 *   -o OUTFILE  write the result there, not over the file ("-": standard
 *               output)
 *   -s          say nothing but errors
 *   -i FILE     read the patch from FILE
 *
 * Exit status 0 when every hunk applied, 1 when one did not, 2 for
 * trouble: a file that cannot be read or written, a patch that is not a
 * unified diff. DS_STATS=1 prints "stats: patch: files F, hunks H, failed
 * X, places tried P, lines compared C". DS_TRACE=1 prints each place tried.
 */
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "ds.h"
#include "diff.h"

/* One line of a hunk: its mark, and its text, with its newline unless a
 * "\ No newline at end of file" line followed it in the patch. */
typedef struct {
    char        op;
    const char *s;
    size_t      len;
} HunkLine;

/* A hunk: what its header says, where it is in the patch, its lines. */
typedef struct {
    size_t a, na;        /* from line a of the old file (from 1), na lines of it */
    size_t b, nb;        /* from line b of the new file, nb lines of it */
    size_t line;         /* its header's line in the patch */
    Array  lines;        /* HunkLine */
} Hunk;

/* The hunks for one file. */
typedef struct {
    char *old_name, *new_name;
    Array hunks;         /* Hunk */
} FilePatch;

static struct {
    long files, hunks, failed, places, compares;
} st;

static int quiet, tracing;

static void print_stats(void)
{
    ds_stats_print("patch", "files %ld, hunks %ld, failed %ld, places tried %ld, lines compared %ld",
                   st.files, st.hunks, st.failed, st.places, st.compares);
}

/* The whole of a file, or of standard input for "-", in memory. */
static char *slurp(const char *path, size_t *size)
{
    FILE *f = open_input(path);
    size_t cap = 1 << 16, n = 0;
    char *buf = xmalloc(cap);
    for (;;) {
        if (n == cap) {
            cap *= 2;
            char *bigger = xmalloc(cap);
            memcpy(bigger, buf, n);
            free(buf);
            buf = bigger;
        }
        size_t got = fread(buf + n, 1, cap - n, f);
        if (got == 0)
            break;
        n += got;
    }
    if (ferror(f))
        die("%s: %s", path, strerror(errno));
    close_input(f);
    *size = n;
    return buf;
}

static int starts(const DiffLine *l, const char *prefix)
{
    size_t n = strlen(prefix);
    return l->len >= n && memcmp(l->s, prefix, n) == 0;
}

/* The name on a "---" or "+++" line: after the mark, up to a tab (and the
 * time after it) or the end of the line. */
static char *name_of(const DiffLine *l)
{
    const char *s = l->s + 4, *end = l->s + l->len;
    const char *e = s;
    while (e < end && *e != '\t' && *e != '\n' && *e != '\r')
        e++;
    return xstrndup(s, (size_t)(e - s));
}

/* A number at *p, moving *p past it; 0 if there is none. */
static int number(const char **p, const char *end, size_t *n)
{
    const char *s = *p;
    *n = 0;
    while (s < end && *s >= '0' && *s <= '9')
        *n = *n * 10 + (size_t)(*s++ - '0');
    if (s == *p)
        return 0;
    *p = s;
    return 1;
}

/* "@@ -a[,na] +b[,nb] @@...": a count that is left out is 1. */
static int read_header(const DiffLine *l, Hunk *h)
{
    const char *p = l->s + 4, *end = l->s + l->len;
    if (!starts(l, "@@ -") || !number(&p, end, &h->a))
        return 0;
    h->na = 1;
    if (p < end && *p == ',' && (++p, !number(&p, end, &h->na)))
        return 0;
    if (end - p < 2 || p[0] != ' ' || p[1] != '+')
        return 0;
    p += 2;
    if (!number(&p, end, &h->b))
        return 0;
    h->nb = 1;
    if (p < end && *p == ',' && (++p, !number(&p, end, &h->nb)))
        return 0;
    return end - p >= 3 && memcmp(p, " @@", 3) == 0;
}

/* "\ No newline at end of file": the line before it had none. */
static void no_newline(Hunk *h)
{
    if (h->lines.len > 0) {
        HunkLine *last = array_at(&h->lines, h->lines.len - 1);
        if (last->len > 0 && last->s[last->len - 1] == '\n')
            last->len--;
    }
}

/* Read the hunk whose header is line i of the patch, into h: its lines
 * until there have been na old ones (kept or deleted) and nb new ones
 * (kept or inserted), as the header says. An empty line is an empty kept
 * line whose space was lost on the way (some editors and mailers take
 * spaces off the ends of lines). Returns the line after the hunk. */
static size_t read_hunk(const DiffText *p, size_t i, Hunk *h)
{
    // @build 06.04 read a hunk: its header, then lines until both counts are used up
    const DiffLine *L = (const DiffLine *)p->lines.data;
    size_t n = p->lines.len;
    if (!read_header(&L[i], h))
        die("line %zu of the patch: not a hunk header: %.*s", i + 1, (int)(L[i].len - 1), L[i].s);
    h->line = i + 1;
    array_init(&h->lines, sizeof(HunkLine));
    size_t old = 0, new = 0;
    for (i++; old < h->na || new < h->nb; i++) {
        if (i == n)
            die("line %zu of the patch: it ends inside the hunk of line %zu", i, h->line);
        char op = L[i].s[0];
        if (op == '\\') {
            no_newline(h);
            continue;
        }
        HunkLine *hl = array_push(&h->lines);
        if (op == '\n') {
            hl->op = ' ';
            hl->s = L[i].s;
            hl->len = L[i].len;
        } else if (op == ' ' || op == '-' || op == '+') {
            hl->op = op;
            hl->s = L[i].s + 1;
            hl->len = L[i].len - 1;
        } else {
            die("line %zu of the patch: the hunk of line %zu has %zu of its %zu old lines and %zu of "
                "its %zu new ones, and this is not one", i + 1, h->line, old, h->na, new, h->nb);
        }
        old += hl->op != '+';
        new += hl->op != '-';
        if (old > h->na || new > h->nb)
            die("line %zu of the patch: more lines than the hunk of line %zu says", i + 1, h->line);
    }
    if (i < n && L[i].s[0] == '\\') {
        no_newline(h);
        i++;
    }
    return i;
    // @end
}

/* Every file of the patch, and its hunks, into files (FilePatch). */
static void read_patch(const DiffText *p, Array *files)
{
    const DiffLine *L = (const DiffLine *)p->lines.data;
    size_t n = p->lines.len;
    FilePatch *fp = NULL;
    for (size_t i = 0; i < n;) {
        if (starts(&L[i], "--- ") && i + 1 < n && starts(&L[i + 1], "+++ ")) {
            fp = array_push(files);
            fp->old_name = name_of(&L[i]);
            fp->new_name = name_of(&L[i + 1]);
            array_init(&fp->hunks, sizeof(Hunk));
            i += 2;
        } else if (starts(&L[i], "@@ ")) {
            if (fp == NULL)
                die("line %zu of the patch: a hunk before any '---' and '+++' lines", i + 1);
            i = read_hunk(p, i, array_push(&fp->hunks));
        } else {
            i++;
        }
    }
}

/* Whether the hunk's old lines (kept and deleted) are the file's lines
 * from line at (from 0) on. */
static int fits(const Hunk *h, const DiffText *f, size_t at)
{
    const DiffLine *fl = (const DiffLine *)f->lines.data;
    const HunkLine *hl = (const HunkLine *)h->lines.data;
    st.places++;
    for (size_t k = 0, i = at; k < h->lines.len; k++) {
        if (hl[k].op == '+')
            continue;
        st.compares++;
        if (fl[i].len != hl[k].len || memcmp(fl[i].s, hl[k].s, hl[k].len) != 0) {
            if (tracing)
                fprintf(stderr, "trace: patch: hunk of line %zu at line %zu: line %zu differs\n",
                        h->line, at + 1, i + 1);
            return 0;
        }
        i++;
    }
    if (tracing)
        fprintf(stderr, "trace: patch: hunk of line %zu at line %zu: fits\n", h->line, at + 1);
    return 1;
}

/* Where a hunk applies, into *at: the line its header says, moved by
 * shift, as far as the hunk before it moved; or else the nearest place to
 * that where its old lines are, one line on, one back, two on, two back,
 * ..., never before from, where the hunk before it ended. 0 when there is
 * none. */
static int find(const Hunk *h, const DiffText *f, size_t from, long shift, size_t *at)
{
    // @build 06.04 find where a hunk applies: at its line, or the nearest place to it
    long want = (long)(h->na ? h->a - 1 : h->a) + shift;
    long lo = (long)from, hi = (long)f->lines.len - (long)h->na;   /* the first and last places */
    for (long d = 0; want + d <= hi || want - d >= lo; d++) {
        if (want + d >= lo && want + d <= hi && fits(h, f, (size_t)(want + d))) {
            *at = (size_t)(want + d);
            return 1;
        }
        if (d > 0 && want - d >= lo && want - d <= hi && fits(h, f, (size_t)(want - d))) {
            *at = (size_t)(want - d);
            return 1;
        }
    }
    return 0;
    // @end
}

/* One more line of the result: a line of the file or of a hunk, where it
 * is; nothing is copied until the result is written. */
static void put(Array *out, const char *s, size_t len)
{
    DiffLine *l = array_push(out);
    l->s = s;
    l->len = len;
    l->id = 0;
}

/* Apply fp's hunks to the text f, in order, into out (DiffLine, the lines
 * of the result): the file's lines up to where a hunk applies, then the
 * hunk's new lines in place of its old ones; after the last hunk, the
 * rest of the file. Returns how many hunks did not apply. */
static size_t apply(const FilePatch *fp, const DiffText *f, Array *out, const char *name)
{
    // @build 06.04 apply the hunks in order: the lines before each, then its new lines
    const DiffLine *fl = (const DiffLine *)f->lines.data;
    size_t done = 0, failed = 0;     /* the file's lines before done are dealt with */
    long shift = 0;
    for (size_t k = 0; k < fp->hunks.len; k++) {
        const Hunk *h = array_at(&fp->hunks, k);
        size_t at, stated = h->na ? h->a - 1 : h->a;
        st.hunks++;
        if (!find(h, f, done, shift, &at)) {
            fprintf(stderr, "patch: %s: hunk #%zu (line %zu of the patch) does not apply: "
                    "its lines are not in the file\n", name, k + 1, h->line);
            failed++;
            continue;
        }
        shift = (long)at - (long)stated;
        if (shift != 0 && !quiet) {
            printf("Hunk #%zu succeeded at %zu (offset %ld line%s).\n", k + 1, at + 1, shift,
                   shift == 1 || shift == -1 ? "" : "s");
            fflush(stdout);
        }
        for (; done < at; done++)
            put(out, fl[done].s, fl[done].len);
        const HunkLine *hl = (const HunkLine *)h->lines.data;
        for (size_t j = 0; j < h->lines.len; j++)
            if (hl[j].op != '-')
                put(out, hl[j].s, hl[j].len);
        done = at + h->na;
    }
    for (; done < f->lines.len; done++)
        put(out, fl[done].s, fl[done].len);
    return failed;
    // @end
}

/* The result, to path: through a new file beside it, renamed over it once
 * it is whole, with the old file's permissions. */
static void write_result(const char *path, const Array *out, const struct stat *old)
{
    const DiffLine *l = (const DiffLine *)out->data;
    if (strcmp(path, "-") == 0) {
        for (size_t i = 0; i < out->len; i++)
            fwrite(l[i].s, 1, l[i].len, stdout);
        if (fflush(stdout) != 0)
            die("standard output: %s", strerror(errno));
        return;
    }
    size_t n = strlen(path);
    char *tmp = xmalloc(n + 8);
    memcpy(tmp, path, n);
    memcpy(tmp + n, ".XXXXXX", 8);
    int fd = mkstemp(tmp);
    if (fd < 0)
        die("%s: %s", tmp, strerror(errno));
    FILE *f = fdopen(fd, "wb");
    if (f == NULL)
        die("%s: %s", tmp, strerror(errno));
    for (size_t i = 0; i < out->len; i++)
        fwrite(l[i].s, 1, l[i].len, f);
    if (old != NULL)
        fchmod(fd, old->st_mode & 07777);
    if (ferror(f) | fclose(f) || rename(tmp, path) != 0) {
        int e = errno;
        unlink(tmp);
        die("%s: %s", path, strerror(e));
    }
    free(tmp);
}

/* name with its first p directories taken off. */
static const char *strip(const char *name, long p)
{
    const char *s = name;
    for (long i = 0; i < p; i++) {
        const char *slash = strchr(s, '/');
        if (slash == NULL)
            die("%s: -p %ld takes off more directories than it has", name, p);
        s = slash + 1;
    }
    return s;
}

/* The file to patch, when none is named: the old name if that file
 * exists, else the new one; "/dev/null" for a file the patch makes new
 * or deletes. */
static const char *target(const FilePatch *fp, long p)
{
    const char *old = strcmp(fp->old_name, "/dev/null") == 0 ? NULL : strip(fp->old_name, p);
    const char *new = strcmp(fp->new_name, "/dev/null") == 0 ? NULL : strip(fp->new_name, p);
    struct stat sb;
    if (old != NULL && (stat(old, &sb) == 0 || new == NULL))
        return old;
    if (new != NULL)
        return new;
    die("a file in the patch is /dev/null on both sides");
}

/* Patch one file: name, or out_path when given. Returns the hunks that
 * failed. */
static size_t patch_file(const FilePatch *fp, const char *name, const char *out_path)
{
    struct stat sb;
    int exists = stat(name, &sb) == 0;
    int makes = strcmp(fp->old_name, "/dev/null") == 0;
    size_t size = 0;
    char *data = NULL;
    if (exists)
        data = slurp(name, &size);
    else if (!makes)
        die("%s: %s", name, strerror(errno));
    if (makes && size > 0) {
        fprintf(stderr, "patch: %s: the patch makes this file, and it is there already\n", name);
        return fp->hunks.len;
    }
    if (!quiet) {
        printf("patching file %s\n", name);
        fflush(stdout);              /* before any error about it, on stderr */
    }
    st.files++;
    DiffText f;
    diff_text(&f, data ? data : "", size);
    Array out;
    array_init(&out, sizeof(DiffLine));
    size_t failed = apply(fp, &f, &out, name);
    st.failed += (long)failed;
    if (failed > 0) {
        fprintf(stderr, "patch: %s: %zu of %zu hunk%s did not apply: the file is not changed\n", name,
                failed, fp->hunks.len, fp->hunks.len == 1 ? "" : "s");
    } else if (out_path == NULL && strcmp(fp->new_name, "/dev/null") == 0 && out.len == 0) {
        if (unlink(name) != 0)
            die("%s: %s", name, strerror(errno));
    } else {
        write_result(out_path ? out_path : name, &out, exists ? &sb : NULL);
    }
    array_free(&out);
    diff_text_free(&f);
    free(data);
    return failed;
}

int main(int argc, char **argv)
{
    progname = "patch";
    ds_stats_at_exit(print_stats);
    const char *s = getenv("DS_TRACE");
    tracing = s != NULL && *s != '\0' && strcmp(s, "0") != 0;
    long p = 0;
    const char *out_path = NULL, *patch_path = NULL;
    int i;
    for (i = 1; i < argc; i++) {
        const char *arg = argv[i];
        if (strcmp(arg, "--") == 0) {
            i++;
            break;
        }
        if (arg[0] != '-' || arg[1] == '\0')
            break;
        if (strcmp(arg, "-s") == 0) {
            quiet = 1;
            continue;
        }
        if (arg[1] == 'p' || arg[1] == 'o' || arg[1] == 'i') {
            const char *v = arg[2] ? arg + 2 : (i + 1 < argc ? argv[++i] : NULL);
            if (v == NULL)
                die("%s wants a value", arg);
            if (arg[1] == 'o') {
                out_path = v;
            } else if (arg[1] == 'i') {
                patch_path = v;
            } else {
                char *end;
                p = strtol(v, &end, 10);
                if (*v == '\0' || *end != '\0' || p < 0)
                    die("-p wants a number of directories, not '%s'", v);
            }
            continue;
        }
        if (arg[1] == '-')
            die("unknown option '%s'", arg);
        die("unknown option %s", arg);
    }
    const char *file = i < argc ? argv[i++] : NULL;
    if (i < argc && patch_path == NULL)
        patch_path = argv[i++];
    if (i < argc)
        die("usage: patch [-p N] [-o OUTFILE] [-s] [-i PATCHFILE] [FILE [PATCHFILE]]");

    size_t size;
    char *data = slurp(patch_path, &size);
    DiffText text;
    diff_text(&text, data, size);
    Array files;
    array_init(&files, sizeof(FilePatch));
    read_patch(&text, &files);
    size_t nhunks = 0;
    for (size_t k = 0; k < files.len; k++)
        nhunks += ((FilePatch *)array_at(&files, k))->hunks.len;
    if (nhunks == 0 && size == 0)
        return 0;                    /* an empty patch, as diff prints for files the same */
    if (nhunks == 0)
        die("no hunks in the patch: it is not a unified diff");
    if (file != NULL && files.len > 1)
        die("the patch changes %zu files: name none, and patch takes their names from it", files.len);
    if (out_path != NULL && files.len > 1)
        die("-o: the patch changes %zu files, and -o can take one", files.len);

    size_t failed = 0;
    for (size_t k = 0; k < files.len; k++) {
        const FilePatch *fp = array_at(&files, k);
        failed += patch_file(fp, file ? file : target(fp, p), out_path);
    }
    if (fflush(stdout) != 0)
        die("standard output: %s", strerror(errno));
    return failed > 0 ? 1 : 0;
}
