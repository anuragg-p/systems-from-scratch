/*
 * diff - compare two files line by line.
 *
 *   diff [option ...] file1 file2
 *
 * diff finds the fewest lines to delete from file1 and insert into it to
 * make it file2: the lines the two have in common, as many as can be kept
 * in order, stay. Exit status 0 when the files are the same, 1 when they
 * differ, 2 for trouble (a file that cannot be read, a bad option). A
 * file named - is standard input.
 *
 * When the files differ, it says so: "Files file1 and file2 differ".
 * Without -q, it prints instead what differs, as a unified diff, the      @from 06.02
 * format of "diff -u": two header lines with each file's name and the      @from 06.02
 * time it was last changed, then the changes as hunks. A hunk starts       @from 06.02
 * with "@@ -l,n +k,m @@": where it is in each file, from line l, for n     @from 06.02
 * lines of file1, and from line k, for m lines of file2; then its lines,   @from 06.02
 * each after one character: " " for a line both files have, "-" for one    @from 06.02
 * only file1 has, "+" for one only file2 has.                              @from 06.02
 *                                                                          @from 06.02
 *   -u      a unified diff, with 3 lines of context around each change     @from 06.02
 *           (what diff prints anyway: it has no other format)              @from 06.02
 *   -U N    a unified diff with N lines of context                         @from 06.02
 *   -q      only "Files file1 and file2 differ", and the exit status       @from 06.02
 *
 *   --algo=NAME   how the lines in common are found:
 *       table     a table of every line of file1 against every line of
 *                 file2: time and memory grow with the product of their
 *                 lengths
 *       myers     Myers' search for the fewest edits: its time grows with   @from 06.03
 *                 the files' lengths times the number of edits              @from 06.03
 *                 The default is the last of these.
 *
 * DS_STATS=1 prints, as well as the lines of the structures it uses,
 * "stats: diff: lines A and B, common C, deleted D, inserted I": the
 * lines of each file, and the lines kept, deleted and inserted.
 * At the end of it, ", hunks H": the hunks printed.                       @from 06.02
 * DS_TRACE=1 prints the steps of the algorithm on stderr, for files of
 * up to 200 lines (lib/diff.h).
 */
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#include "ds.h"
#include "diff.h"

static DiffText a, b;
static DiffScript script;
static size_t hunks;   // @from 06.02

static void print_stats(void)
{
    // @from 06.02
    ds_stats_print("diff", "lines %zu and %zu, common %zu, deleted %zu, inserted %zu, hunks %zu",
                   a.lines.len, b.lines.len, script.common, script.ndel, script.nins, hunks);
    // @else
    // ds_stats_print("diff", "lines %zu and %zu, common %zu, deleted %zu, inserted %zu",
    //                a.lines.len, b.lines.len, script.common, script.ndel, script.nins);
    // @end
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

/* One header line: "--- name<tab>2026-11-14 10:20:30.123456789 +0100", the
 * file's name and when it last changed, in the format GNU diff prints and
 * patch reads; for standard input, the time now. */
static void print_header(const char *mark, const char *path)
{
    // @build 06.02 a header line: the file's name, and when it last changed
    struct stat sb;
    struct timespec ts;
    if (strcmp(path, "-") != 0 && stat(path, &sb) == 0) {
#ifdef __APPLE__
        ts = sb.st_mtimespec;
#else
        ts = sb.st_mtim;
#endif
    } else {
        clock_gettime(CLOCK_REALTIME, &ts);
    }
    struct tm tm;
    localtime_r(&ts.tv_sec, &tm);
    char when[64], zone[16];
    strftime(when, sizeof when, "%Y-%m-%d %H:%M:%S", &tm);
    strftime(zone, sizeof zone, "%z", &tm);
    printf("%s %s\t%s.%09ld %s\n", mark, path, when, (long)ts.tv_nsec, zone);
    // @end
}

/* The value of --name=value, which must be one of names. */
static const char *pick(const char *name, const char *value, const char *const *names)
{
    char have[200] = "";
    for (int i = 0; names[i]; i++) {
        if (strcmp(value, names[i]) == 0)
            return names[i];
        strcat(strcat(have, i ? ", " : ""), names[i]);
    }
    die("no %s '%s' (have: %s)", name, value, have);
}

// @from 06.03
static const char *const algos[] = {"table", "myers", NULL};
// @else
// static const char *const algos[] = {"table", NULL};
// @end

int main(int argc, char **argv)
{
    progname = "diff";
    ds_stats_at_exit(print_stats);
    // @from 06.03
    const char *algo = "myers";
    // @else
    // const char *algo = "table";
    // @end
    // @from 06.02
    long context = 3;
    int brief = 0;
    // @end
    int i;
    for (i = 1; i < argc; i++) {
        const char *arg = argv[i];
        if (strncmp(arg, "--algo=", 7) == 0) {
            algo = pick("--algo", arg + 7, algos);
            continue;
        }
        // @from 06.02
        if (strcmp(arg, "-u") == 0)
            continue;
        if (strcmp(arg, "-q") == 0) {
            brief = 1;
            continue;
        }
        if (strncmp(arg, "-U", 2) == 0) {
            const char *v = arg[2] ? arg + 2 : (i + 1 < argc ? argv[++i] : "");
            char *end;
            context = strtol(v, &end, 10);
            if (*v == '\0' || *end != '\0' || context < 0)
                die("-U wants a number of lines, not '%s'", v);
            continue;
        }
        // @end
        if (strcmp(arg, "--") == 0) {
            i++;
            break;
        }
        if (arg[0] == '-' && arg[1] != '\0') {
            if (arg[1] == '-')
                die("unknown option '%s'", arg);
            die("unknown option %s", arg);
        }
        break;
    }
    if (argc - i != 2)
        die("usage: diff [option ...] file1 file2");
    const char *path1 = argv[i], *path2 = argv[i + 1];

    size_t size1, size2;
    char *data1 = slurp(path1, &size1);
    char *data2 = slurp(path2, &size2);
    diff_text(&a, data1, size1);
    diff_text(&b, data2, size2);
    // @from 06.03
    if (strcmp(algo, "myers") == 0)
        diff_myers(&script, &a, &b);
    else
        diff_table(&script, &a, &b);
    // @else
    // diff_table(&script, &a, &b);
    // @end

    if (script.ndel + script.nins == 0)
        return 0;
    // @from 06.02
    if (!brief) {
        print_header("---", path1);
        print_header("+++", path2);
        hunks = diff_unified(stdout, &a, &b, &script, (size_t)context);
        return ferror(stdout) ? 2 : 1;
    }
    // @end
    printf("Files %s and %s differ\n", path1, path2);
    return ferror(stdout) ? 2 : 1;
}
