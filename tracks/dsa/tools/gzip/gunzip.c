/*
 * gunzip - a gzip file back into the bytes it holds.
 *
 *   gunzip [-c] [-f] [-k] [-t] [--algo=NAME] [file ...]
 *
 * Each FILE.gz becomes FILE, and FILE.gz is removed, as the system's
 * gunzip does. With no file, or "-", standard input goes to standard
 * output.
 *
 *   -c   write to standard output, and keep the .gz files
 *   -f   replace FILE if it is there already
 *   -k   keep the .gz files
 *   -t   test: inflate each file and check it, but write nothing
 *   --algo=NAME  how a Huffman code is read: table (the default), or bits,
 *        a bit at a time
 *
 * A file that is damaged, cut short or not gzip at all is an error that
 * says what is wrong, with status 2, and nothing is written for it. The
 * file is read, and inflated, whole in memory.
 *
 * DS_STATS=1 prints, besides the structures' own lines, "stats: gunzip:
 * files F, bytes in I, bytes out O".
 */
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "gz.h"
#include "inflate.h"

static long files, bytes_in, bytes_out;
static int to_stdout, force, keep, test;

static void print_stats(void)
{
    ds_stats_print("gunzip", "files %ld, bytes in %ld, bytes out %ld", files, bytes_in, bytes_out);
}

/* One file, or standard input for NULL or "-". */
static void gunzip_one(const char *path)
{
    // @build 09.02 one file: read it whole, unpack it, write the bytes it holds
    int std = path == NULL || strcmp(path, "-") == 0;
    char *target = NULL;
    if (!std && !to_stdout && !test) {
        size_t len = strlen(path);
        if (len <= 3 || strcmp(path + len - 3, ".gz") != 0)
            die("%s: does not end in .gz", path);
        target = xstrndup(path, len - 3);
        if (!force && access(target, F_OK) == 0)
            die("%s: already exists (-f replaces it)", target);
    }
    size_t n;
    unsigned char *in = read_all(path, &n);
    Array out;
    array_init(&out, 1);
    const char *err = gz_unpack(in, n, &out);
    if (err)
        die("%s: %s", std ? "stdin" : path, err);
    files++;
    bytes_in += (long)n;
    bytes_out += (long)out.len;
    if (target) {
        write_all(target, out.data, out.len);
        if (!keep && unlink(path) != 0)
            die("%s: %s", path, strerror(errno));
    } else if (!test) {
        fwrite(out.data, 1, out.len, stdout);
    }
    free(target);
    free(in);
    array_free(&out);
    // @end
}

int main(int argc, char **argv)
{
    progname = "gunzip";
    ds_stats_at_exit(print_stats);
    int i;
    for (i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strncmp(a, "--algo=", 7) == 0) {
            if (strcmp(a + 7, "table") == 0)
                inflate_decoder = INFLATE_TABLE;
            else if (strcmp(a + 7, "bits") == 0)
                inflate_decoder = INFLATE_BITS;
            else
                die("no --algo '%s' (have: table, bits)", a + 7);
            continue;
        }
        if (strcmp(a, "--") == 0) {
            i++;
            break;
        }
        if (a[0] == '-' && a[1] == '-')
            die("unknown option '%s'", a);
        if (a[0] == '-' && a[1] != '\0') {
            for (const char *c = a + 1; *c; c++) {
                if (*c == 'c')
                    to_stdout = 1;
                else if (*c == 'f')
                    force = 1;
                else if (*c == 'k')
                    keep = 1;
                else if (*c == 't')
                    test = 1;
                else
                    die("unknown option -%c (have: -c, -f, -k, -t)", *c);
            }
            continue;
        }
        break;
    }
    if (i == argc)
        gunzip_one(NULL);
    for (; i < argc; i++)
        gunzip_one(argv[i]);
    return ferror(stdout) ? 2 : 0;
}
