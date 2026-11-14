/*
 * commit.c - commits, and the history they make.
 *
 * A commit object is text: "tree" and the name of the tree it holds, a
 * "parent" line for each commit it was made on top of (none for the first,
 * two for a merge), who wrote it and when ("author"), who committed it and
 * when ("committer"), a blank line, and the message. Each commit names its
 * parents, never its children: the history is a graph whose arrows point
 * back in time, and the only way into it is from the newest commits.
 *
 * log starts at a commit and follows the arrows back, printing each commit
 * once, newest first. Two things make that work on a graph with merges:
 * a queue of commits found but not printed yet, from which the newest is
 * taken each time (the heap of 02.04, ordered by the committer's date),
 * and a set of the commits found already, so that a commit two paths lead
 * to is queued once (the hash table of 01.02, keyed by the commit's name).
 * --algo=list does both with plain lists, as one would first write them:
 * the queue is searched end to end for the newest, the set from the start
 * for the name.
 *
 * DS_STATS=1 prints "stats: log: commits C, queue scans Q, seen probes P":
 * the commits printed, the queue entries looked at to find the newest
 * (list), and the names compared to find one in the set (list); the heap's
 * and the table's own lines count theirs.
 */
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "git.h"

static struct {
    long commits, scans, probes;
} st;

static void print_stats(void)
{
    ds_stats_print("log", "commits %ld, queue scans %ld, seen probes %ld", st.commits, st.scans, st.probes);
}

static long next_seq;

/* "author A U Thor <a@example.com> 1700000000 +0530": the time, or -1. */
static long long ident_time(const char *s, size_t n)
{
    const char *gt = NULL;
    for (size_t i = n; i-- > 0;)
        if (s[i] == '>') {
            gt = s + i;
            break;
        }
    if (gt == NULL || gt + 2 > s + n || gt[1] != ' ')
        return -1;
    long long t = 0;
    const char *p = gt + 2;
    int digits = 0;
    for (; p < s + n && *p >= '0' && *p <= '9' && digits < 18; p++, digits++)
        t = t * 10 + (*p - '0');
    return digits > 0 ? t : -1;
}

Commit *commit_read(const unsigned char name[20])
{
    // @build 10.03 read a commit: its tree, its parents, its date and its message
    Commit *c = xmalloc(sizeof *c);
    memset(c, 0, sizeof *c);
    memcpy(c->oid, name, 20);
    array_init(&c->parents, 20);
    object_read(name, &c->obj);
    char hex[41];
    sha1_hex(name, hex);
    if (c->obj.type != OBJ_COMMIT)
        die("%s is a %s, not a commit", hex, type_name(c->obj.type));
    const char *p = (const char *)c->obj.data, *end = p + c->obj.size;
    int have_author = 0, have_committer = 0;
    if (end - p < 46 || memcmp(p, "tree ", 5) != 0 || p[45] != '\n' || sha1_unhex(p + 5, c->tree) != 0)
        die("commit %s is damaged: it does not start with its tree", hex);
    p += 46;
    while (p < end && *p != '\n') {          /* the header lines, up to the blank line */
        const char *nl = memchr(p, '\n', (size_t)(end - p));
        if (nl == NULL)
            die("commit %s is damaged: its header has no end", hex);
        size_t n = (size_t)(nl - p);
        if (n == 47 && memcmp(p, "parent ", 7) == 0) {
            if (have_author || sha1_unhex(p + 7, array_push(&c->parents)) != 0)
                die("commit %s is damaged: a parent line", hex);
        } else if (n > 7 && memcmp(p, "author ", 7) == 0) {
            c->author = p + 7;
            c->author_len = n - 7;
            have_author = 1;
        } else if (n > 10 && memcmp(p, "committer ", 10) == 0) {
            c->time = ident_time(p + 10, n - 10);
            if (c->time < 0)
                die("commit %s is damaged: its committer has no date", hex);
            have_committer = 1;
        }                                    /* encoding, gpgsig ...: not read */
        p = nl + 1;
    }
    if (!have_author || !have_committer)
        die("commit %s is damaged: it has no %s", hex, have_author ? "committer" : "author");
    c->msg = p < end ? p + 1 : end;
    c->msg_len = (size_t)(end - c->msg);
    c->seq = next_seq++;
    return c;
    // @end
}

void commit_free(Commit *c)
{
    object_free(&c->obj);
    array_free(&c->parents);
    free(c);
}

// @from 10.04
static Table known;
static Array kept;                           /* Commit *: the value in known is the index here */
static int known_ready;

Commit *commit_get(const unsigned char name[20])
{
    if (!known_ready) {
        table_init(&known);
        array_init(&kept, sizeof(Commit *));
        known_ready = 1;
    }
    long *v = table_get(&known, name, 20);
    if (v != NULL)
        return *(Commit **)array_at(&kept, (size_t)*v);
    Commit *c = commit_read(name);
    *table_put(&known, name, 20) = (long)kept.len;
    *(Commit **)array_push(&kept) = c;
    return c;
}
// @end

/* ------------------------------------------------------------ writing one */

char *clean_message(const char *msg)
{
    size_t n = strlen(msg);
    char *out = xmalloc(n + 2);
    size_t o = 0;
    int blank_run = 0;
    for (const char *p = msg; *p;) {
        const char *nl = strchr(p, '\n');
        size_t len = nl ? (size_t)(nl - p) : strlen(p);
        size_t keep = len;
        while (keep > 0 && (p[keep - 1] == ' ' || p[keep - 1] == '\t' || p[keep - 1] == '\r'))
            keep--;
        if (keep == 0) {
            blank_run = 1;
        } else {
            if (blank_run && o > 0)
                out[o++] = '\n';
            blank_run = 0;
            memcpy(out + o, p, keep);
            o += keep;
            out[o++] = '\n';
        }
        p += len + (nl != NULL);
    }
    out[o] = '\0';
    return out;
}

/* "Name <email> 1700000000 +0530" for who ("AUTHOR" or "COMMITTER"),
 * from GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL and GIT_AUTHOR_DATE (or the
 * COMMITTER ones), else user.name and user.email in .git/config, and the
 * time now. */
static char *ident(const char *who)
{
    char var[32];
    const char *parts[] = {"NAME", "EMAIL", "DATE"};
    char *v[3];
    for (int i = 0; i < 3; i++) {
        snprintf(var, sizeof var, "GIT_%s_%s", who, parts[i]);
        const char *e = getenv(var);
        v[i] = e ? xstrndup(e, strlen(e)) : i < 2 ? config_get("user", i ? "email" : "name") : NULL;
    }
    if (v[0] == NULL || v[1] == NULL || strpbrk(v[0], "<>\n") || strpbrk(v[1], "<>\n"))
        die("who is committing? Set GIT_AUTHOR_NAME and GIT_AUTHOR_EMAIL (or user.name and user.email "
            "in .git/config): this git reads no other config");
    long long t;
    int tz;
    char sign = '+';
    if (v[2] == NULL) {
        time_t now = time(NULL);
        struct tm tm;
        localtime_r(&now, &tm);
        t = (long long)now;
        long off = tm.tm_gmtoff / 60;
        if (off < 0) {
            sign = '-';
            off = -off;
        }
        tz = (int)(off / 60 * 100 + off % 60);
    } else {
        const char *d = v[2] + (v[2][0] == '@');
        char *end;
        t = strtoll(d, &end, 10);
        if (end == d || *end != ' ' || (end[1] != '+' && end[1] != '-') || strlen(end) != 6 ||
            strspn(end + 2, "0123456789") != 4)
            die("GIT_%s_DATE is '%s': this git reads only \"SECONDS +HHMM\" (or with an @ first)", who, v[2]);
        sign = end[1];
        tz = atoi(end + 2);
    }
    size_t len = strlen(v[0]) + strlen(v[1]) + 48;
    char *out = xmalloc(len);
    snprintf(out, len, "%s <%s> %lld %c%04d", v[0], v[1], t, sign, tz);
    for (int i = 0; i < 3; i++)
        free(v[i]);
    return out;
}

void commit_create(const unsigned char tree[20], const unsigned char *parents, size_t n,
                   const char *msg, unsigned char name[20])
{
    // @build 10.03 a commit: its tree, its parents, who and when, and the message
    char hex[41];
    char *author = ident("AUTHOR"), *committer = ident("COMMITTER");
    size_t size = 64 + n * 48 + strlen(author) + strlen(committer) + strlen(msg) + 32;
    char *text = xmalloc(size);
    size_t o = 0;
    sha1_hex(tree, hex);
    o += (size_t)snprintf(text + o, size - o, "tree %s\n", hex);
    for (size_t i = 0; i < n; i++) {
        sha1_hex(parents + 20 * i, hex);
        o += (size_t)snprintf(text + o, size - o, "parent %s\n", hex);
    }
    o += (size_t)snprintf(text + o, size - o, "author %s\ncommitter %s\n\n%s", author, committer, msg);
    object_write(OBJ_COMMIT, text, o, name);
    free(text);
    free(author);
    free(committer);
    // @end
}

/* ------------------------------------------------------------ log */

static const char *const days[] = {"Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};
static const char *const months[] = {"Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"};

/* A date as git log prints it, "Tue Nov 14 22:16:40 2023 +0000": the
 * time as it was where it was written, by its own zone. */
static void put_date(long long t, const char *zone, size_t zlen)
{
    int tz = 0;
    if (zlen == 5 && (zone[0] == '+' || zone[0] == '-'))
        tz = (zone[0] == '-' ? -1 : 1) * ((zone[1] - '0') * 600 + (zone[2] - '0') * 60 + (zone[3] - '0') * 10 + (zone[4] - '0'));
    time_t local = (time_t)(t + tz * 60);
    struct tm tm;
    gmtime_r(&local, &tm);
    printf("%s %s %d %02d:%02d:%02d %d %.*s\n", days[tm.tm_wday], months[tm.tm_mon], tm.tm_mday,
           tm.tm_hour, tm.tm_min, tm.tm_sec, tm.tm_year + 1900, (int)zlen, zone);
}

/* A message line as log prints it: four spaces in, tabs out to every
 * eighth column of the message. */
static void put_line(const char *p, size_t n)
{
    fputs("    ", stdout);
    size_t col = 0;
    for (size_t i = 0; i < n; i++) {
        if (p[i] == '\t') {
            do
                putchar(' ');
            while (++col % 8 != 0);
        } else {
            putchar(p[i]);
            col++;
        }
    }
    putchar('\n');
}

static void show(const Commit *c, int oneline, int first)
{
    char abbr[41];
    st.commits++;
    if (oneline) {
        abbrev(c->oid, abbr);
        printf("%s ", abbr);
        const char *p = c->msg, *end = c->msg + c->msg_len;
        int words = 0;                       /* the subject: the first paragraph, lines joined */
        while (p < end && *p != '\n') {
            const char *nl = memchr(p, '\n', (size_t)(end - p));
            size_t n = nl ? (size_t)(nl - p) : (size_t)(end - p);
            printf("%s%.*s", words++ ? " " : "", (int)n, p);
            p += n + (nl != NULL);
        }
        putchar('\n');
        return;
    }
    char hex[41];
    sha1_hex(c->oid, hex);
    printf("%scommit %s\n", first ? "" : "\n", hex);
    if (c->parents.len > 1) {
        fputs("Merge:", stdout);
        for (size_t i = 0; i < c->parents.len; i++) {
            abbrev(array_at(&c->parents, i), abbr);
            printf(" %s", abbr);
        }
        putchar('\n');
    }
    const char *a = c->author, *gt = NULL;
    for (size_t i = c->author_len; i-- > 0 && gt == NULL;)
        if (a[i] == '>')
            gt = a + i;
    if (gt == NULL)
        gt = a + c->author_len - 1;
    printf("Author: %.*s\n", (int)(gt + 1 - a), a);
    const char *when = gt + 2 <= a + c->author_len ? gt + 2 : a + c->author_len;
    const char *sp = memchr(when, ' ', (size_t)(a + c->author_len - when));
    fputs("Date:   ", stdout);
    put_date(ident_time(a, c->author_len) < 0 ? 0 : ident_time(a, c->author_len), sp ? sp + 1 : "+0000",
             sp ? (size_t)(a + c->author_len - sp - 1) : 5);
    putchar('\n');
    const char *p = c->msg, *end = c->msg + c->msg_len;
    while (p < end) {
        const char *nl = memchr(p, '\n', (size_t)(end - p));
        size_t n = nl ? (size_t)(nl - p) : (size_t)(end - p);
        put_line(p, n);
        p += n + (nl != NULL);
    }
}

/* The heap's order: the newest commit first; of two from the same second,
 * the one met first. */
int commit_newer(const void *a, const void *b, void *ctx)
{
    const Commit *x = a, *y = b;
    if (x->time != y->time)
        return x->time > y->time ? -1 : 1;
    return x->seq < y->seq ? -1 : x->seq > y->seq;
}

static void trace_heap(const char *what, const Commit *c, const Heap *h)
{
    char line[2048];
    size_t o = 0;
    line[0] = '\0';
    for (size_t i = 0; i < h->items.len && o < sizeof line - 64; i++) {
        const Commit *q = ((Commit **)h->items.data)[i];
        o += (size_t)snprintf(line + o, sizeof line - o, "%s%s %lld", i ? ", " : "", short_hex(q->oid), q->time);
    }
    trace("log: %s %s %lld; heap: %s", what, short_hex(c->oid), c->time, h->items.len ? line : "(empty)");
}

/* The queue a heap, the set a hash table. */
static void walk_heap(const unsigned char *starts, size_t n, int oneline, long limit)
{
    // @build 10.03 log: the newest commit off the heap, its parents onto it unless seen already
    Heap queue;
    Table seen;
    heap_init(&queue, commit_newer, NULL);
    table_init(&seen);
    for (size_t i = 0; i < n; i++) {
        if (table_get(&seen, starts + 20 * i, 20) != NULL)
            continue;
        table_put(&seen, starts + 20 * i, 20);
        heap_push(&queue, commit_read(starts + 20 * i));
    }
    for (long shown = 0; heap_len(&queue) > 0 && (limit < 0 || shown < limit); shown++) {
        Commit *c = heap_pop(&queue);
        if (git_tracing())
            trace_heap("pop", c, &queue);
        show(c, oneline, shown == 0);
        for (size_t i = 0; i < c->parents.len; i++) {
            const unsigned char *p = array_at(&c->parents, i);
            if (table_get(&seen, p, 20) != NULL) {
                if (git_tracing())
                    trace("log: %s, parent of %s: seen already", short_hex(p), short_hex(c->oid));
                continue;
            }
            table_put(&seen, p, 20);
            Commit *pc = commit_read(p);
            heap_push(&queue, pc);
            if (git_tracing())
                trace_heap("push", pc, &queue);
        }
        commit_free(c);
    }
    // @end
}

/* Is p in the list of names seen? If not, it is now. */
static int seen_before(Array *seen, const unsigned char *p)
{
    for (size_t j = 0; j < seen->len; j++) {
        st.probes++;
        if (memcmp(array_at(seen, j), p, 20) == 0)
            return 1;
    }
    memcpy(array_push(seen), p, 20);
    return 0;
}

/* The queue and the set as plain lists. */
static void walk_list(const unsigned char *starts, size_t n, int oneline, long limit)
{
    // @build 10.03 log, the obvious way: the queue searched for the newest, a list of the names seen
    Array queue, seen;
    array_init(&queue, sizeof(Commit *));
    array_init(&seen, 20);
    for (size_t i = 0; i < n; i++)
        if (!seen_before(&seen, starts + 20 * i))
            *(Commit **)array_push(&queue) = commit_read(starts + 20 * i);
    for (long shown = 0; queue.len > 0 && (limit < 0 || shown < limit); shown++) {
        size_t best = 0;
        for (size_t i = 1; i < queue.len; i++) {
            st.scans++;
            if (commit_newer(*(Commit **)array_at(&queue, i), *(Commit **)array_at(&queue, best), NULL) < 0)
                best = i;
        }
        Commit *c = *(Commit **)array_at(&queue, best);
        *(Commit **)array_at(&queue, best) = *(Commit **)array_at(&queue, queue.len - 1);
        array_pop(&queue);
        show(c, oneline, shown == 0);
        for (size_t i = 0; i < c->parents.len; i++) {
            const unsigned char *p = array_at(&c->parents, i);
            if (!seen_before(&seen, p))
                *(Commit **)array_push(&queue) = commit_read(p);
        }
        commit_free(c);
    }
    // @end
}

void log_walk(const unsigned char *starts, size_t n, int algo, int oneline, long limit)
{
    ds_stats_at_exit(print_stats);
    if (algo == LOG_LIST)
        walk_list(starts, n, oneline, limit);
    else
        walk_heap(starts, n, oneline, limit);
}
