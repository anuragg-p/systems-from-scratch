/*
 * git.h - what the parts of git share.
 *
 *   repo.c     finding the repository (only where it is told: never above),
 *              its config, reading and replacing whole files
 *   object.c   objects: a type, a size and bytes, named by the SHA-1 of
 *              them, stored compressed under that name
 *   tree.c     trees: a directory as a list of names, modes and objects    @from 10.02
 *   index.c    the index: the sorted list of what the next commit holds    @from 10.02
 *   refs.c     names for commits: HEAD, branches, and NAME~1 and NAME^2    @from 10.03
 *   commit.c   commits, and walking them newest first for log               @from 10.03
 *   compare.c  two commits compared, and the best common ancestor         @from 10.04
 *   git.c      the commands
 */
#ifndef GIT_H
#define GIT_H

#include <sys/stat.h>

#include "ds.h"
#include "sha1sum.h"

/* ------------------------------------------------------------ repo.c */

/* git works in the top directory of a repository (the one -C names, or the
 * current one) and finds everything under .git there. */
typedef struct {
    int writable;        /* .git/config says "[dsa] ours = true": made by this git */
} Repo;

extern Repo repo;

/* The repository here, checked: .git a directory (not a file: no linked
 * worktrees), no packed objects, SHA-1 names. Dies with the reason if not. */
void repo_open(void);
/* Dies unless this git may change the repository: only one its own init
 * made (config "[dsa] ours = true"). */
void repo_must_write(const char *what);
/* A new repository in dir (made if need be): .git with HEAD on branch. */
void repo_init(const char *dir, const char *branch, int quiet);
/* section.key from .git/config (never from any other config file), or
 * NULL; malloc'd. */
char *config_get(const char *section, const char *key);

/* The whole of a file, with a NUL after it; NULL if there is no such
 * file. Dies on any other trouble. */
char *read_file(const char *path, size_t *size);
/* Replace path with these bytes: written to path.lock, then renamed over
 * it, so a reader sees the old file or the new one, never half of one. */
void write_file_locked(const char *path, const void *data, size_t n);
/* mkdir, and every directory above it that is missing. */
void make_dirs(const char *path);

/* DS_TRACE: anything but 0 traces git's own steps on stderr; "all" the
 * library's steps too (inflate, deflate, Myers). */
int  git_tracing(void);
void trace_setup(void);
void trace(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

/* ------------------------------------------------------------ object.c */

enum { OBJ_BAD, OBJ_COMMIT, OBJ_TREE, OBJ_BLOB, OBJ_TAG };

const char *type_name(int type);
int type_from_name(const char *s, size_t len);    /* OBJ_BAD if it is none */

/* An object as read: its type, and its content, size bytes at data, which
 * point into buf (the whole object, header and all). */
typedef struct {
    int type;
    size_t size;
    const unsigned char *data;
    Array buf;
} Object;

/* The name of an object of this type and content. */
void object_name(int type, const void *data, size_t n, unsigned char name[20]);
/* Store it, unless an object of that name is there already: returns 1 if
 * it wrote it, 0 if it was there. Its name in name. */
int  object_write(int type, const void *data, size_t n, unsigned char name[20]);
int  object_exists(const unsigned char name[20]);
/* Read it, checked: dies naming it if it is missing or damaged. */
void object_read(const unsigned char name[20], Object *o);
void object_free(Object *o);

/* 40 hexadecimal digits, or the first 4 or more of an object's name: 0,
 * or -1 if arg is not that. Dies if the digits are the start of no
 * object's name, or of several. */
int  resolve_hex(const char *arg, size_t len, unsigned char name[20]);
/* What a name typed on the command line names; dies if nothing. */
void resolve(const char *arg, unsigned char name[20]);
/* The shortest start of name that is no other object's, 7 digits at least
 * (git's "abbreviated" names): out holds up to 41 bytes. */
void abbrev(const unsigned char name[20], char *out);
/* The same, 7 digits, without looking at the other objects (for traces). */
const char *short_hex(const unsigned char name[20]);

// @from 10.02
/* ------------------------------------------------------------ tree.c */

/* One entry of a tree: a mode (0100644 a file, 0100755 an executable,
 * 0120000 a symbolic link, 0160000 a submodule's commit, 040000 a
 * directory), a name, and the name of the object. */
typedef struct {
    uint32_t mode;
    const char *name;            /* not NUL-terminated: len bytes */
    size_t len;
    const unsigned char *oid;    /* 20 bytes */
} TreeEntry;

#define MODE_TREE 040000u

/* git's order of entries in a tree: by the bytes of the names, where a
 * directory's name counts as if it ended in '/'. */
int tree_cmp(const char *a, size_t alen, int adir, const char *b, size_t blen, int bdir);
/* The entries of the tree object o (named name), checked; TreeEntry,
 * pointing into o. Dies naming the tree if it is damaged. */
void tree_entries(const unsigned char name[20], const Object *o, Array *out);
/* "blob", "tree" or "commit": what an entry of this mode names. */
const char *mode_type(uint32_t mode);
/* The tree a name typed on the command line stands for: the tree of that
 * name.
 * Or a commit's name: that commit's tree.                              @from 10.03
 */
void tree_of(const char *arg, unsigned char tree[20]);
/* A path as git prints it: in double quotes, with C escapes, when it
 * holds a control character, '"', '\\' or a byte over 127. */
void put_path(FILE *f, const char *prefix, const char *path, size_t len);
int  path_needs_quotes(const char *path, size_t len);

/* ------------------------------------------------------------ index.c */

/* One file of the index: what stat() said of it when it was added (so a
 * later look can tell it has not changed without reading it), its mode,
 * and the name of its blob. */
typedef struct {
    uint32_t ctime_s, ctime_ns, mtime_s, mtime_ns, dev, ino, mode, uid, gid, size;
    unsigned char oid[20];
    char *path;                  /* NUL-terminated, len bytes, from the top directory */
    size_t len;
} IndexEntry;

/* The cached trees (the index's TREE extension): for each directory, how
 * many index entries are under it, and the tree they make, or count -1
 * if an entry under it changed since that tree was made. */
typedef struct CacheTree {
    char *name;                  /* the directory's own name; "" for the top */
    size_t len;
    long count;
    unsigned char oid[20];
    Array subs;                  /* struct CacheTree *: its subdirectories */
} CacheTree;

typedef struct {
    Array entries;               /* IndexEntry, sorted by path, byte by byte */
    CacheTree *cache;            /* NULL: none */
} Index;

void index_read(Index *ix);      /* .git/index; an empty index if there is none */
void index_write(Index *ix);
/* add: the files under each path (a file, a directory, or "." for all)
 * into the index, hashed and stored; index entries under a path whose
 * file is gone are taken out. */
void index_add(Index *ix, char **paths, size_t n);
/* The tree of the index, built bottom up and stored: with use_cache, only
 * the directories whose cached tree is gone are built again. */
void write_tree(Index *ix, int use_cache, unsigned char tree[20]);
// @end

// @from 10.03
/* ------------------------------------------------------------ refs.c */

/* The commit a ref names ("HEAD", "refs/heads/main"), following "ref: "
 * links: 0, or -1 if there is no such ref (or HEAD's branch has no
 * commit yet). */
int  ref_read(const char *ref, unsigned char name[20]);
/* The branch HEAD is on ("refs/heads/main", malloc'd), or NULL if HEAD
 * holds a commit's name itself. */
char *head_branch(void);
/* Point ref at name. */
void ref_write(const char *ref, const unsigned char name[20]);
/* Is this a name a branch may have? */
int  branch_name_ok(const char *name);
/* What a name typed on the command line names: an object's name or the
 * start of one, HEAD, a branch or a tag, then any of ~N (the Nth first
 * parent), ^N (the Nth parent) and ^{tree}. Dies if nothing. */
void rev_parse(const char *arg, unsigned char name[20]);

/* ------------------------------------------------------------ commit.c */

typedef struct Commit {
    unsigned char oid[20];
    unsigned char tree[20];
    Array parents;               /* unsigned char[20] each */
    long long time;              /* the committer's date, seconds since 1970 */
    long seq;                    /* the order commits were met in: breaks ties of time */
    int flags;                   /* merge-base's marks */                              // @from 10.04
    long walk;                   /* the last walk that met it (merge-base --algo=rewalk) */   // @from 10.04
    Object obj;                  /* the commit's text */
    const char *author;          /* "Name <email> 1700000000 +0530", in obj */
    size_t author_len;
    const char *msg;             /* the message, in obj */
    size_t msg_len;
} Commit;

/* Read and parse a commit; dies naming it if it is not one, or damaged. */
Commit *commit_read(const unsigned char name[20]);
void commit_free(Commit *c);
/* The same, kept: one Commit for each name, however often it is asked
 * for (the table of 01.02, from names to commits). */
Commit *commit_get(const unsigned char name[20]);
/* A new commit of tree with these parents (n of them, 20 bytes each) and
 * message; author and committer from the environment. */
void commit_create(const unsigned char tree[20], const unsigned char *parents, size_t n,
                   const char *msg, unsigned char name[20]);
/* The order of a history walk's queue (a Cmp for the heap): the commit
 * with the later committer's date first; of two from the same second, the
 * one met first. */
int commit_newer(const void *a, const void *b, void *ctx);
/* log: the commits reachable from the n starts, newest first. */
enum { LOG_LIST, LOG_HEAP };
void log_walk(const unsigned char *starts, size_t n, int algo, int oneline, long limit);
/* The message as "git commit" keeps it: trailing spaces and blank lines at
 * either end gone, runs of blank lines made one, a newline at the end. */
char *clean_message(const char *msg);
// @end

// @from 10.04
/* ------------------------------------------------------------ compare.c */

enum { WALK_ALL, WALK_SKIP };
/* diff: what changed from the tree a to the tree b, as git's patches. */
void diff_trees(const unsigned char a[20], const unsigned char b[20], int algo, long context);
enum { BASE_REWALK, BASE_PAINT };
/* merge-base: the best common ancestors of a and b, printed (all of them,
 * or the first); returns how many there are. */
size_t merge_base(const unsigned char a[20], const unsigned char b[20], int algo, int all);
// @end

#endif
