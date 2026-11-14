/*
 * gzip - making files smaller.
 *
 *   gzip --huffman [file]
 *   gzip --lz77 [--algo=NAME] [--chain=N] [file]                          @from 09.03
 *   gzip [-1 ... -9] [-c] [-f] [-k] [option ...] [file ...]                @from 09.04
 *
 * --huffman counts the bytes of the file (or standard input), builds a
 * Huffman code for them, and prints each byte's count, code length and
 * code, and the size the bytes would take in that code.
 * --lz77 parses the file into literals and matches, and prints how many   @from 09.03
 * there are of each:                                                      @from 09.03
 *   --algo=NAME  how a match is found: hash, on the chains of a hash      @from 09.03
 *                table (the default); scan, trying every place in the     @from 09.03
 *                window; or none, finding none                            @from 09.03
 *   --chain=N    with hash, try at most N places for a match (128 if not  @from 09.03
 *                given; 0 for no limit)                                   @from 09.03
 * Otherwise each FILE becomes FILE.gz, and FILE is removed, as the        @from 09.04
 * system's gzip does; with no file, or "-", standard input goes to        @from 09.04
 * standard output. Options:                                               @from 09.04
 *   -1 ... -9    how hard to look for matches: a chain of 4 places at -1, @from 09.04
 *                128 at -6 (the default), 4096 at -9                      @from 09.04
 *   -c           write to standard output, and keep the files             @from 09.04
 *   -f           replace FILE.gz if it is there already                   @from 09.04
 *   -k           keep the files                                           @from 09.04
 *   --blocks=NAME  best: each block in whichever form is smallest (the    @from 09.04
 *                default); or every block stored, fixed or dynamic        @from 09.04
 *   --algo, --chain  as for --lz77                                        @from 09.04
 *
 * DS_STATS=1 prints, besides the structures' own lines, "stats: gzip:
 * bytes in I, bytes out O".
 */
#include <errno.h>       // @from 09.04
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>    // @from 09.04
#include <unistd.h>      // @from 09.04

#include "huffman.h"
#include "gz.h"          // @from 09.03
#include "lz77.h"        // @from 09.03

static long bytes_in, bytes_out;

// @from 09.03
static int algo = LZ77_HASH;   /* --algo */
static int chain = 128;        /* --chain, or the level's */
// @end
// @from 09.04
static int to_stdout, force, keep;
static int blocks = DEFLATE_BEST;
static int xfl;                /* the header's XFL: 2 at -9, 4 at -1 */

/* The chain bound of each level, -1 to -9. */
static const int level_chain[10] = {0, 4, 8, 16, 32, 64, 128, 256, 1024, 4096};
// @end

static void print_stats(void)
{
    ds_stats_print("gzip", "bytes in %ld, bytes out %ld", bytes_in, bytes_out);
}

static void usage(void)
{
    fflush(stdout);
    fputs("gzip: usage: gzip --huffman [file]\n", stderr);
    fputs("       gzip --lz77 [--algo=NAME] [--chain=N] [file]\n", stderr);                // @from 09.03
    fputs("       gzip [-1 ... -9] [-c] [-f] [-k] [option ...] [file ...]\n", stderr);      // @from 09.04
    exit(2);
}

/* A byte as C writes it in quotes: 'a', '\n', '\x00'. */
static const char *show_byte(int b, char *buf, size_t size)
{
    if (b == '\n')
        snprintf(buf, size, "'\\n'");
    else if (b == '\t')
        snprintf(buf, size, "'\\t'");
    else if (b == '\'' || b == '\\')
        snprintf(buf, size, "'\\%c'", b);
    else if (b >= 32 && b < 127)
        snprintf(buf, size, "'%c'", b);
    else
        snprintf(buf, size, "'\\x%02x'", b);
    return buf;
}

/* --huffman: each byte's code, and what the bytes would take in it. */
static void show_huffman(const char *path)
{
    // @build 09.01 count the bytes, build their code, print it with the size it gives
    long counts[256] = {0}, total = 0;
    FILE *f = open_input(path);
    int c;
    while ((c = getc(f)) != EOF) {
        counts[c]++;
        total++;
    }
    close_input(f);
    unsigned char len[256];
    unsigned code[256];
    huff_lengths(counts, 256, len);
    huff_codes(len, 256, code);
    long long bits = 0;
    int used = 0;
    printf("byte      count  bits  code\n");
    for (int b = 0; b < 256; b++) {
        if (len[b] == 0)
            continue;
        char name[8];
        printf("%-6s %8ld  %4d  ", show_byte(b, name, sizeof name), counts[b], len[b]);
        for (int k = len[b] - 1; k >= 0; k--)
            putchar(code[b] >> k & 1 ? '1' : '0');
        putchar('\n');
        bits += (long long)counts[b] * len[b];
        used++;
    }
    printf("%ld bytes, %d different: %lld bits as bytes, %lld bits in these codes (%lld bytes)\n",
           total, used, 8 * (long long)total, bits, (bits + 7) / 8);
    bytes_in += total;
    // @end
}

/* --lz77: the file as literals and matches. */
static void show_lz77(const char *path)
{
    // @build 09.03 parse the input into literals and matches, and count them
    size_t n;
    unsigned char *in = read_all(path, &n);
    Lz77 z;
    lz77_init(&z, in, n, algo, chain);
    Lz77Token t[4096];
    size_t k, literals = 0, matches = 0, covered = 0;
    while ((k = lz77_parse(&z, t, 4096)) > 0) {
        for (size_t j = 0; j < k; j++) {
            if (t[j].dist == 0) {
                literals++;
            } else {
                matches++;
                covered += t[j].len;
            }
        }
    }
    printf("%zu bytes: %zu literals, %zu matches for the other %zu bytes\n", n, literals, matches, covered);
    bytes_in += (long)n;
    lz77_free(&z);
    free(in);
    // @end
}

/* One file into FILE.gz, or standard input (NULL or "-") to standard output. */
static void gzip_one(const char *path)
{
    // @build 09.04 one file: deflate it into a gzip file beside it
    int std = path == NULL || strcmp(path, "-") == 0;
    char *target = NULL;
    const char *name = NULL;
    long mtime = 0;
    if (!std) {
        size_t len = strlen(path);
        struct stat sb;
        if (len > 3 && strcmp(path + len - 3, ".gz") == 0)
            die("%s: already ends in .gz", path);
        if (stat(path, &sb) != 0)
            die("%s: %s", path, strerror(errno));
        mtime = (long)sb.st_mtime;
        name = strrchr(path, '/') ? strrchr(path, '/') + 1 : path;
        if (!to_stdout) {
            target = xmalloc(len + 4);
            memcpy(target, path, len);
            memcpy(target + len, ".gz", 4);
            if (!force && access(target, F_OK) == 0)
                die("%s: already exists (-f replaces it)", target);
        }
    }
    if (target == NULL && !force && isatty(1))
        die("compressed data is not written to a terminal (-f writes it anyway)");
    size_t n;
    unsigned char *in = read_all(path, &n);
    Array out;
    array_init(&out, 1);
    DeflateOptions opt = {algo, chain, blocks};
    gz_pack(in, n, name, mtime, xfl, &opt, &out);
    bytes_in += (long)n;
    bytes_out += (long)out.len;
    if (target) {
        write_all(target, out.data, out.len);
        if (!keep && unlink(path) != 0)
            die("%s: %s", path, strerror(errno));
    } else {
        fwrite(out.data, 1, out.len, stdout);
    }
    free(target);
    free(in);
    array_free(&out);
    // @end
}

// @from 09.03
/* A count: digits only. */
static int count(const char *option, const char *s)
{
    char *end;
    long v = strtol(s, &end, 10);
    if (*s == '\0' || *end != '\0' || v < 0 || v > 1000000)
        die("%s wants a count, not '%s'", option, s);
    return (int)v;
}
// @end

int main(int argc, char **argv)
{
    progname = "gzip";
    ds_stats_at_exit(print_stats);
    const char *mode = NULL;        /* what to print instead of compressing, if anything */
    int i;
    for (i = 1; i < argc; i++) {
        const char *a = argv[i];
        if (strcmp(a, "--huffman") == 0) {
            mode = "huffman";
            continue;
        }
        // @from 09.03
        if (strcmp(a, "--lz77") == 0) {
            mode = "lz77";
            continue;
        }
        if (strncmp(a, "--algo=", 7) == 0) {
            if (strcmp(a + 7, "hash") == 0)
                algo = LZ77_HASH;
            else if (strcmp(a + 7, "scan") == 0)
                algo = LZ77_SCAN;
            else if (strcmp(a + 7, "none") == 0)
                algo = LZ77_NONE;
            else
                die("no --algo '%s' (have: hash, scan, none)", a + 7);
            continue;
        }
        if (strncmp(a, "--chain=", 8) == 0) {
            chain = count("--chain", a + 8);
            continue;
        }
        // @end
        // @from 09.04
        if (strncmp(a, "--blocks=", 9) == 0) {
            const char *b = a + 9;
            if (strcmp(b, "best") == 0)
                blocks = DEFLATE_BEST;
            else if (strcmp(b, "stored") == 0)
                blocks = DEFLATE_STORED;
            else if (strcmp(b, "fixed") == 0)
                blocks = DEFLATE_FIXED;
            else if (strcmp(b, "dynamic") == 0)
                blocks = DEFLATE_DYNAMIC;
            else
                die("no --blocks '%s' (have: best, stored, fixed, dynamic)", b);
            continue;
        }
        if (a[0] == '-' && a[1] != '-' && a[1] != '\0') {
            for (const char *c = a + 1; *c; c++) {
                if (*c >= '1' && *c <= '9') {
                    chain = level_chain[*c - '0'];
                    xfl = *c == '9' ? 2 : *c == '1' ? 4 : 0;
                } else if (*c == 'c') {
                    to_stdout = 1;
                } else if (*c == 'f') {
                    force = 1;
                } else if (*c == 'k') {
                    keep = 1;
                } else {
                    usage();
                }
            }
            continue;
        }
        // @end
        if (strcmp(a, "--") == 0) {
            i++;
            break;
        }
        if (a[0] == '-' && a[1] == '-')
            die("unknown option '%s'", a);
        if (a[0] == '-' && a[1] != '\0')
            usage();
        break;
    }
    if (mode && argc - i > 1)
        die("--%s takes one file", mode);
    if (mode && strcmp(mode, "huffman") == 0) {
        show_huffman(i < argc ? argv[i] : NULL);
        return ferror(stdout) ? 2 : 0;
    }
    // @from 09.03
    if (mode && strcmp(mode, "lz77") == 0) {
        show_lz77(i < argc ? argv[i] : NULL);
        return ferror(stdout) ? 2 : 0;
    }
    // @end
    // @from 09.04
    if (i == argc)
        gzip_one(NULL);
    for (; i < argc; i++)
        gzip_one(argv[i]);
    return ferror(stdout) ? 2 : 0;
    // @else
    // usage();
    // @end
}
