/*
 * look - print the lines of a sorted file that begin with a string.
 *
 *   look [--algo=binary|scan] string file
 *
 * The file must be sorted byte by byte, as LC_ALL=C sort sorts it. Then
 * the lines that begin with string all sit together, and the first of
 * them is the first line that is not smaller than string, when only as
 * many bytes of each line as string has are compared. look finds that
 * line, prints from it every line that begins with string, and exits 0
 * if there was one, 1 if there was none, as the system's look does.
 *
 *   --algo=binary  look at the middle line of the part of the file the
 *                  first match can be in: it says which half to keep.
 *                  About log2(lines) lines are looked at (the default)
 *   --algo=scan    look at every line from the top until that one
 *
 * The file is read in blocks of 4096 bytes, as a disk reads it. DS_STATS=1
 * prints "stats: look: probes P, blocks read B, lines printed L": lines
 * compared with string while searching, blocks read from the file, and
 * lines printed.
 */
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "ds.h"

#define BLOCK 4096

static int fd;
static off_t size;
static char block[BLOCK];
static off_t block_at = -1;     /* the offset of the block in memory, or -1 */
static ssize_t block_len;

static long probes, blocks, printed;

static void print_stats(void)
{
    ds_stats_print("look", "probes %ld, blocks read %ld, lines printed %ld", probes, blocks, printed);
}

/* The byte at off, from the block that holds it: read when it is not the
 * one in memory. */
static int byte_at(off_t off)
{
    if (block_at < 0 || off < block_at || off >= block_at + block_len) {
        block_at = off - off % BLOCK;
        block_len = pread(fd, block, BLOCK, block_at);
        if (block_len < 0)
            die("read error: %s", strerror(errno));
        blocks++;
        if (off >= block_at + block_len)
            return -1;
    }
    return (unsigned char)block[off - block_at];
}

/* The line that starts at off, into line (an Array of char, without the
 * newline); returns where the next line starts. */
static off_t line_at(off_t off, Array *line)
{
    array_clear(line);
    int c;
    while (off < size && (c = byte_at(off)) >= 0) {
        off++;
        if (c == '\n')
            break;
        *(char *)array_push(line) = (char)c;
    }
    return off;
}

/* The start of the first line that starts at or after off. */
static off_t line_start(off_t off)
{
    if (off == 0)
        return 0;
    for (off_t p = off - 1; p < size; p++)
        if (byte_at(p) == '\n')
            return p + 1;
    return size;
}

/* line against key, on no more than key's length: 0 when line begins with
 * key, less than 0 when it is smaller (or is a shorter start of key). */
static int compare(const Array *line, const char *key, size_t klen)
{
    size_t n = line->len < klen ? line->len : klen;
    int c = n ? memcmp(line->data, key, n) : 0;
    if (c != 0)
        return c;
    return line->len < klen ? -1 : 0;
}

/* --algo=scan: where the first line not smaller than key starts. */
static off_t find_scan(const char *key, size_t klen, Array *line)
{
    // @build 02.06 scan from the top, a line at a time
    off_t at = 0;
    while (at < size) {
        off_t next = line_at(at, line);
        probes++;
        if (compare(line, key, klen) >= 0)
            return at;
        at = next;
    }
    return size;
    // @end
}

/* --algo=binary: the same place, found by halving. Every line before lo
 * is smaller than key; the line at hi (if hi is not the end) is not. The
 * line nearest the middle of [lo, hi) decides which half to keep; when no
 * line starts in its second half, the line at lo does. */
static off_t find_binary(const char *key, size_t klen, Array *line)
{
    // @build 02.06 binary search: halve the part of the file it can be in
    off_t lo = 0, hi = size;
    while (lo < hi) {
        off_t at = line_start(lo + (hi - lo) / 2);
        if (at >= hi)
            at = lo;
        off_t next = line_at(at, line);
        probes++;
        if (compare(line, key, klen) < 0)
            lo = next;
        else
            hi = at;
    }
    return lo;
    // @end
}

int main(int argc, char **argv)
{
    progname = "look";
    ds_stats_at_exit(print_stats);
    int binary = 1;
    int i = 1;
    for (; i < argc && strncmp(argv[i], "--", 2) == 0; i++) {
        if (strcmp(argv[i], "--") == 0) {
            i++;
            break;
        }
        if (strcmp(argv[i], "--algo=binary") == 0)
            binary = 1;
        else if (strcmp(argv[i], "--algo=scan") == 0)
            binary = 0;
        else if (strncmp(argv[i], "--algo=", 7) == 0)
            die("no --algo '%s' (have: binary, scan)", argv[i] + 7);
        else
            die("unknown option '%s'", argv[i]);
    }
    if (argc - i != 2)
        die("usage: look [--algo=binary|scan] string file");
    const char *key = argv[i], *path = argv[i + 1];
    size_t klen = strlen(key);
    fd = open(path, O_RDONLY);
    struct stat sb;
    if (fd < 0 || fstat(fd, &sb) < 0)
        die("%s: %s", path, strerror(errno));
    size = sb.st_size;

    Array line;
    array_init(&line, 1);
    off_t at = binary ? find_binary(key, klen, &line) : find_scan(key, klen, &line);
    while (at < size) {
        at = line_at(at, &line);
        if (compare(&line, key, klen) != 0)
            break;
        fwrite(line.data, 1, line.len, stdout);
        putchar('\n');
        printed++;
    }
    close(fd);
    return printed > 0 ? 0 : 1;
}
