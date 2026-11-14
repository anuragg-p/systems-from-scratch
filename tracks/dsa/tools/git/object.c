/*
 * object.c - git's objects: everything git keeps is one.
 *
 * An object is a type (blob for a file's bytes, tree for a directory,
 * commit, tag), a size, and the bytes. Its name is the SHA-1 of the three
 * together, "blob 6\0hello\n", written as 40 hexadecimal digits; it is
 * stored, compressed as a zlib stream, at .git/objects/ and then the first
 * two digits as a directory and the other 38 as the file's name.
 *
 * So the name says where to look, and the bytes found there can be checked
 * against it: the same bytes always have the same name, and are stored once
 * however many times they are written; other bytes have another name. An
 * object is never changed: a change is a new object.
 *
 * DS_STATS=1 prints, as git's own line, "stats: git: objects hashed H,
 * written W, already there E, read R".
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "git.h"
#include "zframe.h"

static struct {
    long hashed, written, there, read;
} st;

static void print_stats(void)
{
    ds_stats_print("git", "objects hashed %ld, written %ld, already there %ld, read %ld",
                   st.hashed, st.written, st.there, st.read);
}

/* Registered by main before anything else, so git's line comes first. */
void object_stats(void)
{
    ds_stats_at_exit(print_stats);
}

static const char *const names[] = {"bad", "commit", "tree", "blob", "tag"};

const char *type_name(int type)
{
    return type > OBJ_BAD && type <= OBJ_TAG ? names[type] : "bad";
}

int type_from_name(const char *s, size_t len)
{
    for (int t = OBJ_COMMIT; t <= OBJ_TAG; t++)
        if (strlen(names[t]) == len && memcmp(names[t], s, len) == 0)
            return t;
    return OBJ_BAD;
}

const char *short_hex(const unsigned char name[20])
{
    static char buf[4][41];
    static int next;
    char *b = buf[next++ % 4];
    sha1_hex(name, b);
    b[7] = '\0';
    return b;
}

/* .git/objects/xx/yyyy...: 54 bytes and a NUL. */
static void object_path(const unsigned char name[20], char path[64])
{
    char hex[41];
    sha1_hex(name, hex);
    memcpy(path, ".git/objects/", 13);
    memcpy(path + 13, hex, 2);
    path[15] = '/';
    memcpy(path + 16, hex + 2, 39);       /* 38 digits and the NUL */
}

void object_name(int type, const void *data, size_t n, unsigned char name[20])
{
    // @build 10.01 the name: the SHA-1 of a header ("blob 6" and a NUL) and the bytes
    char head[32];
    int hlen = snprintf(head, sizeof head, "%s %zu", type_name(type), n) + 1;   /* the NUL too */
    Sha1 s;
    sha1_init(&s);
    sha1_update(&s, head, (size_t)hlen);
    sha1_update(&s, data, n);
    sha1_final(&s, name);
    st.hashed++;
    // @end
}

int object_exists(const unsigned char name[20])
{
    char path[64];
    object_path(name, path);
    return access(path, F_OK) == 0;
}

static void forget(int first);

/* How git writes its loose objects: zlib at its fastest level (a short
 * search for matches: gzip -1's). */
static const DeflateOptions loose = {LZ77_HASH, 4, DEFLATE_BEST};

int object_write(int type, const void *data, size_t n, unsigned char name[20])
{
    // @build 10.01 store an object: under its name, compressed, and only once
    repo_must_write("writing an object");
    object_name(type, data, n, name);
    char path[64];
    object_path(name, path);
    if (access(path, F_OK) == 0) {
        st.there++;
        if (git_tracing())
            trace("object: %s of %zu bytes is %s: already there", type_name(type), n, path + 13);
        return 0;
    }
    Array raw, z;
    array_init(&raw, 1);
    array_init(&z, 1);
    char head[32];
    int hlen = snprintf(head, sizeof head, "%s %zu", type_name(type), n) + 1;
    for (int i = 0; i < hlen; i++)
        *(char *)array_push(&raw) = head[i];
    for (size_t i = 0; i < n; i++)
        *(char *)array_push(&raw) = ((const char *)data)[i];
    zframe_pack((const unsigned char *)raw.data, raw.len, &loose, &z);

    char dir[64], tmp[64];
    memcpy(dir, path, 15);
    dir[15] = '\0';
    if (mkdir(dir, 0777) != 0 && errno != EEXIST)
        die("%s: %s", dir, strerror(errno));
    snprintf(tmp, sizeof tmp, "%s/tmp_obj_XXXXXX", dir);
    int fd = mkstemp(tmp);
    if (fd < 0)
        die("%s: %s", tmp, strerror(errno));
    for (size_t done = 0; done < z.len;) {
        ssize_t put = write(fd, z.data + done, z.len - done);
        if (put < 0 && errno != EINTR)
            die("%s: %s", tmp, strerror(errno));
        done += put > 0 ? (size_t)put : 0;
    }
    if (fchmod(fd, 0444) != 0 || close(fd) != 0 || rename(tmp, path) != 0)
        die("%s: %s", path, strerror(errno));
    st.written++;
    forget(name[0]);
    if (git_tracing())
        trace("object: %s of %zu bytes is %s: written, %zu bytes compressed", type_name(type), n, path + 13, z.len);
    array_free(&raw);
    array_free(&z);
    return 1;
    // @end
}

void object_read(const unsigned char name[20], Object *o)
{
    // @build 10.01 read an object: inflate it, read its header, and check it has this name
    char path[64], hex[41];
    object_path(name, path);
    sha1_hex(name, hex);
    size_t size, used;
    char *file = read_file(path, &size);
    if (file == NULL)
        die("object %s is not in the repository", hex);
    array_init(&o->buf, 1);
    const char *err = zframe_unpack((const unsigned char *)file, size, &o->buf, &used);
    if (err != NULL)
        die("object %s is damaged: %s", hex, err);
    if (used != size)
        die("object %s is damaged: %zu bytes after its zlib stream", hex, size - used);
    free(file);
    const char *b = o->buf.data;
    size_t n = o->buf.len;
    const char *sp = n > 0 ? memchr(b, ' ', n < 8 ? n : 8) : NULL;
    if (sp == NULL || (o->type = type_from_name(b, (size_t)(sp - b))) == OBJ_BAD)
        die("object %s is damaged: its header does not start with a type", hex);
    size_t i = (size_t)(sp - b) + 1, declared = 0;
    for (size_t digits = 0; i < n && b[i] >= '0' && b[i] <= '9' && digits < 18; i++, digits++)
        declared = declared * 10 + (size_t)(b[i] - '0');
    if (i >= n || b[i] != '\0' || b[i - 1] == ' ')
        die("object %s is damaged: its header has no size", hex);
    i++;
    if (n - i != declared)
        die("object %s is damaged: its header says %zu bytes, and it has %zu", hex, declared, n - i);
    unsigned char real[20];
    sha1(b, n, real);
    if (memcmp(real, name, 20) != 0) {
        char rhex[41];
        sha1_hex(real, rhex);
        die("object %s is damaged: its bytes are the object %s", hex, rhex);
    }
    o->size = declared;
    o->data = (const unsigned char *)b + i;
    st.read++;
    if (git_tracing())
        trace("object: read %s %s, %zu bytes", type_name(o->type), hex, o->size);
    // @end
}

void object_free(Object *o)
{
    array_free(&o->buf);
    o->data = NULL;
    o->size = 0;
}

/* ------------------------------------------------------------ names a person types */

/* The objects whose names start with two hexadecimal digits: the names of
 * the files in .git/objects/xx, read once and kept. */
static Array known[256];      /* char[39] each: 38 digits and a NUL */
static unsigned char loaded[256];

/* A new object in .git/objects/xx: read the directory again next time. */
static void forget(int first)
{
    if (loaded[first]) {
        array_free(&known[first]);
        loaded[first] = 0;
    }
}

static Array *objects_under(const char *two)
{
    unsigned char b[20] = {0};
    char hex[41];
    memcpy(hex, two, 2);
    memset(hex + 2, '0', 38);
    hex[40] = '\0';
    if (sha1_unhex(hex, b) != 0)
        return NULL;
    Array *a = &known[b[0]];
    if (!loaded[b[0]]) {
        loaded[b[0]] = 1;
        array_init(a, 39);
        char dir[32];
        snprintf(dir, sizeof dir, ".git/objects/%c%c", hex[0], hex[1]);
        DIR *d = opendir(dir);
        if (d != NULL) {
            struct dirent *de;
            while ((de = readdir(d)) != NULL) {
                unsigned char tmp[20];
                char full[41];
                if (strlen(de->d_name) != 38)
                    continue;
                memcpy(full, hex, 2);
                memcpy(full + 2, de->d_name, 39);
                if (sha1_unhex(full, tmp) != 0)
                    continue;
                for (int k = 2; k < 40; k++)     /* kept in lower case, as sha1_hex writes */
                    if (full[k] >= 'A' && full[k] <= 'F')
                        full[k] = (char)(full[k] - 'A' + 'a');
                memcpy(array_push(a), full + 2, 39);
            }
            closedir(d);
        }
    }
    return a;
}

int resolve_hex(const char *arg, size_t len, unsigned char name[20])
{
    char want[41];
    if (len < 4 || len > 40)
        return -1;
    for (size_t i = 0; i < len; i++) {
        char c = arg[i];
        if (c >= 'A' && c <= 'F')
            c = (char)(c - 'A' + 'a');
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')))
            return -1;
        want[i] = c;
    }
    want[len] = '\0';
    if (len == 40)
        return sha1_unhex(want, name);
    Array *a = objects_under(want);
    int found = 0;
    for (size_t i = 0; a && i < a->len; i++) {
        const char *tail = array_at(a, i);
        if (strncmp(tail, want + 2, len - 2) == 0) {
            char full[41];
            memcpy(full, want, 2);
            memcpy(full + 2, tail, 39);
            if (found++ == 0)
                sha1_unhex(full, name);
        }
    }
    if (found == 0)
        die("%.*s is the start of no object's name here", (int)len, arg);
    if (found > 1)
        die("%.*s is the start of %d objects' names: give more of it", (int)len, arg, found);
    return 0;
}

void resolve(const char *arg, unsigned char name[20])
{
    // @from 10.03
    rev_parse(arg, name);
    // @else
    // if (resolve_hex(arg, strlen(arg), name) != 0)
    //     die("%s: not an object's name (40 hexadecimal digits, or the first 4 or more of them)", arg);
    // @end
}

void abbrev(const unsigned char name[20], char *out)
{
    char hex[41];
    sha1_hex(name, hex);
    Array *a = objects_under(hex);
    size_t need = 7;
    for (size_t i = 0; a && i < a->len; i++) {
        const char *tail = array_at(a, i);
        if (strcmp(tail, hex + 2) == 0)
            continue;
        size_t k = 0;
        while (k < 38 && tail[k] == hex[2 + k])
            k++;
        if (2 + k + 1 > need)
            need = 2 + k + 1;
    }
    memcpy(out, hex, need);
    out[need] = '\0';
}
