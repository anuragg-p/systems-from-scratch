/* lsp_fuzz.c: random and mutated input for module 07's readers, for the tests.
 *
 *   cc -std=c99 -g -fsanitize=address,undefined -I <tree> -o lsp-fuzz lsp_fuzz.c
 *   ./lsp-fuzz frames|json|messages SECONDS [SEED]
 *
 * It includes the tree's json.c and lsp.c whole (so their static functions
 * are reachable), with stand-ins for the five kilo functions lsp.c calls.
 *   frames    lspFrame() on random bytes, on a stream of good messages cut
 *             into random pieces (each body must come out exactly), and on
 *             that stream mutated
 *   json      jsonParse() on mutations of a corpus of messages and on
 *             random bytes (each tree is walked and freed), on nesting far
 *             past the cap, and jsonQuote() then jsonParse() round trips;
 *             and the decoding of a few escapes, checked and printed
 *   messages  lspHandle() on mutated protocol messages (initialize results,
 *             diagnostics, definition results, requests from the server),
 *             with lspDrawRow() and lspShowDiagnostic() after each
 * Prints "ok" and the number of runs at the end; a sanitizer stops it with a
 * report at the first error. Not part of any project a reader sees. */

#ifdef __linux__
#define _POSIX_C_SOURCE 200809L
#endif
#include "json.c"
#include "lsp.c"
#include <assert.h>

/* ------------------------------------------------ stand-ins for kilo.c */

struct abuf { char *b; int len; };
static const char *TEXT = "#include <stdio.h>\n\tint total = add(2, 3);\n"
                          "\tprintf(\"\xc3\xa9t\xc3\xa9: %d\\n\", totl); \xf0\x9f\x98\x80 x\n"
                          "\x01\x7f\t\tz\n\n";
static char status[80];
static int cur_row, cur_col, jumps_fail;

void abAppend(struct abuf *ab, const char *s, int len) {
    char *n = realloc(ab->b,ab->len+len);
    if (n == NULL) return;
    memcpy(n+ab->len,s,len);
    ab->b = n;
    ab->len += len;
}
char *editorRowsToString(int *buflen) {
    *buflen = strlen(TEXT);
    return strdup(TEXT);
}
void editorSetStatusMessage(const char *fmt, ...) {
    va_list ap;
    va_start(ap,fmt);
    vsnprintf(status,sizeof(status),fmt,ap);
    va_end(ap);
}
void editorRefreshScreen(void) {}
void editorCursor(int *row, int *col) { *row = cur_row; *col = cur_col; }
int editorJump(const char *path, int row, int col) {
    (void)path; (void)row; (void)col;
    return jumps_fail ? -1 : 0;
}
__attribute__((noreturn)) void kiloTodo(const char *lesson, const char *what) {
    fprintf(stderr,"kilo: %s: %s not written yet\n",lesson,what);
    exit(3);
}

/* ------------------------------------------------ randomness */

static unsigned long long rng = 88172645463325252ULL;
static unsigned long long rnd(void) {
    rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17;
    return rng;
}
static int below(int n) { return n > 0 ? (int)(rnd() % (unsigned)n) : 0; }

/* Mutate len bytes at s into out (room for cap): flips, special bytes,
 * insertions, deletions, a cut. Returns the new length. */
static size_t mutate(const char *s, size_t len, char *out, size_t cap) {
    static const char special[] = "\"\\[]{}:,0123456789-+.eEu\xff\x80\xc3\xed\xf0 \t\r\n\0nulltrue";
    size_t n = len < cap ? len : cap, k;
    int times = 1+below(6), i;
    memcpy(out,s,n);
    for (i = 0; i < times; i++) {
        size_t at = n ? (size_t)below(n) : 0;
        switch (below(6)) {
        case 0: if (n) out[at] ^= 1 << below(8); break;
        case 1: if (n) out[at] = special[below(sizeof(special)-1)]; break;
        case 2: if (n < cap) { memmove(out+at+1,out+at,n-at); out[at] = special[below(sizeof(special)-1)]; n++; } break;
        case 3: if (n) { memmove(out+at,out+at+1,n-at-1); n--; } break;
        case 4: n = at; break;
        case 5: k = below(8); if (n+k < cap && at+k <= n) { memmove(out+at+k,out+at,n-at); n += k; } break;   /* a run doubled */
        }
    }
    return n;
}

static double elapsed(struct timespec *t0) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC,&t);
    return (t.tv_sec-t0->tv_sec) + (t.tv_nsec-t0->tv_nsec)/1e9;
}

/* ------------------------------------------------ frames */

static long frames(double seconds) {
    struct timespec t0;
    long runs = 0;
    static char buf[1<<16], stream[1<<16], mut[1<<16];
    clock_gettime(CLOCK_MONOTONIC,&t0);
    while (elapsed(&t0) < seconds) {
        size_t len, body, bodylen, slen = 0, got, fed, i;
        long n;
        int nf, f, lens[16];

        /* Random bytes, sometimes after a plausible header. */
        len = below(6000);
        for (i = 0; i < len; i++) buf[i] = rnd();
        if (below(2)) {
            int h = snprintf(buf,sizeof(buf),"Content-Length: %d\r\n\r\n",below(3000));
            if ((size_t)h > len) len = h;
        }
        n = lspFrame(buf,len,&body,&bodylen);
        assert(n >= -1 && n <= (long)len);
        if (n > 0) assert(body+bodylen == (size_t)n);

        /* Good messages, cut into random pieces: each body comes out whole. */
        nf = 1+below(15);
        for (f = 0; f < nf; f++) {
            int bl = below(400), h;
            h = snprintf(stream+slen,sizeof(stream)-slen,"%sContent-Length: %d\r\n%s\r\n",
                         below(4) ? "" : "Content-Type: x\r\n",bl,below(4) ? "" : "X-Y: z\r\n");
            slen += h;
            for (i = 0; i < (size_t)bl; i++) stream[slen+i] = 'a'+(f+i)%26;
            slen += bl;
            lens[f] = bl;
        }
        got = 0; fed = 0; f = 0;
        while (fed < slen || got < fed) {
            size_t more = 1+below(300);
            if (fed+more > slen) more = slen-fed;
            fed += more;
            while ((n = lspFrame(stream+got,fed-got,&body,&bodylen)) > 0) {
                assert(f < nf && bodylen == (size_t)lens[f]);
                for (i = 0; i < bodylen; i++) assert(stream[got+body+i] == 'a'+(f+i)%26);
                got += n;
                f++;
            }
            assert(n == 0);
            if (fed == slen) break;
        }
        assert(f == nf && got == slen);

        /* The same, mutated: whatever comes off lies inside what was given. */
        len = mutate(stream,slen,mut,sizeof(mut));
        got = 0;
        while (got < len && (n = lspFrame(mut+got,len-got,&body,&bodylen)) > 0) {
            assert(got+body+bodylen <= len && body+bodylen == (size_t)n);
            got += n;
        }
        runs++;
    }
    return runs;
}

/* ------------------------------------------------ json */

static const char *corpus[] = {
    "{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"capabilities\":{\"positionEncoding\":\"utf-8\","
        "\"textDocumentSync\":{\"change\":2,\"openClose\":true}},\"serverInfo\":{\"name\":\"clangd\","
        "\"version\":\"Apple clangd version 21.0.0\"}}}",
    "{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/publishDiagnostics\",\"params\":{\"uri\":"
        "\"file:///tmp/a%20b/sum.c\",\"version\":3,\"diagnostics\":[{\"range\":{\"start\":{\"line\":5,"
        "\"character\":21},\"end\":{\"line\":5,\"character\":25}},\"severity\":1,\"message\":"
        "\"Use of undeclared identifier 'totl'; did you mean 'total'?\\n\\nsum.c:5:6: note: here\"}]}}",
    ("{\"id\":7,\"result\":[{\"uri\":\"file:///x.h\",\"range\":{\"start\":{\"line\":1,\"character\":18},"
        "\"end\":{\"line\":1,\"character\":21}}}]}"),
    "[1,-0,0.5,1e10,-2.5E-3,123456789012345678901234567890,true,false,null,\"\",[],{}]",
    "\"esc \\\" \\\\ \\/ \\b \\f \\n \\r \\t \\u00e9 \\ud83d\\ude00 \\ud83d \\udc00 \\u0000 x\"",
    "{\"a\":{\"b\":{\"c\":[[[[{\"d\":\"e\"}]]]]}},\"a\":2}",
    "  \t\r\n {\"k\" : [ 1 , 2 ] } \n",
};

static void walk(json *j, int depth) {
    for (; j; j = j->next) {
        assert(depth <= JSON_MAX_DEPTH);
        if (j->type == JSON_STRING) assert(strlen(j->string) == j->len);
        (void)jsonInt(j,0);
        (void)jsonStr(j,NULL);
        (void)jsonGet(j,"id");
        walk(j->child,depth+1);
    }
}

/* Check one decoding, and print it as bytes, for the notes. */
static void decodes(const char *text, const char *want, size_t wantlen) {
    json *j = jsonParse(text,strlen(text));
    size_t i;
    assert(j && j->type == JSON_STRING && j->len == wantlen && memcmp(j->string,want,wantlen) == 0);
    printf("%-18s ->",text);
    for (i = 0; i < j->len; i++) printf(" %02x",(unsigned char)j->string[i]);
    printf("\n");
    jsonFree(j);
}

static long jsonfuzz(double seconds) {
    struct timespec t0;
    long runs = 0;
    static char mut[1<<16], deep[300000];
    size_t i;
    json *j;

    decodes("\"\\n\"","\n",1);
    decodes("\"\\u00e9\"","\xc3\xa9",2);
    decodes("\"\\ud83d\\ude00\"","\xf0\x9f\x98\x80",4);
    decodes("\"\\ud83d\"","\xef\xbf\xbd",3);
    decodes("\"\\ud83dx\"","\xef\xbf\xbdx",4);
    decodes("\"\\udc00\"","\xef\xbf\xbd",3);
    decodes("\"\\u0000\"","\xef\xbf\xbd",3);
    assert(jsonParse("\"a\nb\"",5) == NULL);        /* a raw control byte */
    assert(jsonParse("\"\\x\"",4) == NULL);         /* an escape JSON has not */
    assert(jsonParse("\"\\u12\"",6) == NULL);       /* too few hex digits */
    assert(jsonParse("01",2) == NULL && jsonParse("+1",2) == NULL && jsonParse("1.",2) == NULL);
    assert(jsonParse("[1,]",4) == NULL && jsonParse("{\"a\":1,}",8) == NULL);
    assert(jsonParse("1 2",3) == NULL && jsonParse("",0) == NULL);
    /* Nesting: the cap is an error, not a deep stack. */
    for (i = 0; i < sizeof(deep); i++) deep[i] = '[';
    assert(jsonParse(deep,sizeof(deep)) == NULL);
    for (i = 0; i < 64; i++) deep[i] = '[';
    for (i = 64; i < 128; i++) deep[i] = ']';
    j = jsonParse(deep,128);
    assert(j != NULL);
    jsonFree(j);
    for (i = 0; i < 65; i++) deep[i] = '[';
    for (i = 65; i < 130; i++) deep[i] = ']';
    assert(jsonParse(deep,130) == NULL);
    printf("depth 64 parses, 65 and 300000 do not\n");

    clock_gettime(CLOCK_MONOTONIC,&t0);
    while (elapsed(&t0) < seconds) {
        const char *base = corpus[below(sizeof(corpus)/sizeof(corpus[0]))];
        size_t len = mutate(base,strlen(base),mut,sizeof(mut)), qlen;
        char *q;
        if ((j = jsonParse(mut,len))) {
            walk(j,0);
            jsonFree(j);
        }
        len = below(200);
        for (i = 0; i < len; i++) mut[i] = rnd();
        if ((j = jsonParse(mut,len))) jsonFree(j);
        /* A round trip: any bytes but '\0', quoted then read, come back the same. */
        for (i = 0; i < len; i++) if (mut[i] == 0) mut[i] = 1;
        q = jsonQuote(mut,len);
        qlen = strlen(q);
        j = jsonParse(q,qlen);
        assert(j && j->type == JSON_STRING && j->len == len && memcmp(j->string,mut,len) == 0);
        jsonFree(j);
        free(q);
        runs++;
    }
    return runs;
}

/* ------------------------------------------------ messages */

static int sink[2], source[2], piped;
static const char *PATH = "/tmp/lsp-fuzz/sum.c";

/* A server for lsp.c to have: a child that only sleeps (lspEnd() may kill
 * it), and pipes that go nowhere much. */
static void serve(void) {
    pid_t parent = getpid();
    if (L.pid == 0) {
        if (piped) close(sink[0]);
        piped = 1;
        L.pid = fork();
        if (L.pid == 0) {
            while (getppid() == parent) sleep(1);
            _exit(0);
        }
        if (pipe(sink) == -1 || pipe(source) == -1) exit(2);
        fcntl(sink[0],F_SETFL,O_NONBLOCK);
        fcntl(sink[1],F_SETFL,O_NONBLOCK);
        fcntl(source[0],F_SETFL,O_NONBLOCK);
        L.in = sink[1];
        L.out = source[0];
        close(source[1]);
        L.name = "fuzz";
        L.language = "c";
    }
    if (L.path == NULL || strcmp(L.path,PATH) != 0) {    /* a jump went elsewhere: come back */
        free(L.path);
        free(L.uri);
        L.path = strdup(PATH);
        L.uri = lspUri(L.path);
    }
    /* What kilo wrote is read and thrown away, so the queue never fills. */
    while (read(sink[0],status,sizeof(status)) > 0);
    if (!L.ready) {
        L.ready = 1;
        L.changes = 1;
        L.hasdef = 1;
        lspOpen();
    }
}

static const char *messages[] = {
    "{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/publishDiagnostics\",\"params\":{\"uri\":"
        "\"file:///tmp/lsp-fuzz/sum.c\",\"version\":1,\"diagnostics\":[{\"range\":{\"start\":{\"line\":2,"
        "\"character\":21},\"end\":{\"line\":2,\"character\":25}},\"severity\":1,\"message\":\"m\"},"
        "{\"range\":{\"start\":{\"line\":1,\"character\":0},\"end\":{\"line\":3,\"character\":9}},"
        "\"severity\":3,\"message\":\"two\\nlines\"},{\"range\":{\"start\":{\"line\":4,\"character\":0},"
        "\"end\":{\"line\":4,\"character\":0}}}]}}",
    "{\"jsonrpc\":\"2.0\",\"id\":5,\"result\":[{\"uri\":\"file:///tmp/lsp-fuzz/sum.c\",\"range\":"
        "{\"start\":{\"line\":1,\"character\":5},\"end\":{\"line\":1,\"character\":10}}}]}",
    "{\"jsonrpc\":\"2.0\",\"id\":5,\"result\":{\"targetUri\":\"file:///tmp/lsp%2Dfuzz/add.h\","
        "\"targetSelectionRange\":{\"start\":{\"line\":1,\"character\":18},\"end\":{\"line\":1,\"character\":21}}}}",
    "{\"jsonrpc\":\"2.0\",\"id\":5,\"result\":null}",
    "{\"jsonrpc\":\"2.0\",\"id\":\"abc\",\"method\":\"workspace/configuration\",\"params\":{}}",
    "{\"jsonrpc\":\"2.0\",\"id\":9,\"method\":\"window/workDoneProgress/create\"}",
    "{\"jsonrpc\":\"2.0\",\"id\":4,\"result\":{\"capabilities\":{\"positionEncoding\":\"utf-16\","
        "\"textDocumentSync\":0,\"definitionProvider\":{}},\"serverInfo\":{\"name\":\"x\"}}}",
};

static long messagesfuzz(double seconds) {
    struct timespec t0;
    long runs = 0;
    static char mut[1<<16];
    const char *rows[] = {"#include <stdio.h>","\tint total = add(2, 3);",
                          "\tprintf(\"\xc3\xa9t\xc3\xa9: %d\\n\", totl); \xf0\x9f\x98\x80 x",
                          "\x01\x7f\t\tz",""};
    char render[256];
    clock_gettime(CLOCK_MONOTONIC,&t0);
    while (elapsed(&t0) < seconds) {
        const char *base = messages[below(sizeof(messages)/sizeof(messages[0]))];
        size_t len = mutate(base,strlen(base),mut,sizeof(mut));
        int r;
        serve();
        L.utf8 = below(2);
        L.defid = 5;
        L.initid = below(2) ? 4 : 0;
        L.version = below(3);
        cur_row = below(7)-1;
        cur_col = below(60)-2;
        jumps_fail = below(2);
        lspHandle(mut,len);
        if (L.pid == 0) continue;           /* stopped: serve() starts another */
        lspShowDiagnostic();
        switch (below(8)) {
        case 0: lspDefinition(); break;
        case 1: lspBack(); break;
        case 2: lspPause(); break;
        }
        if (L.pid == 0) continue;
        for (r = 0; r < 5; r++) {
            struct abuf ab = {NULL,0};
            const char *c = rows[r];
            int i, n = 0, size = strlen(c);
            for (i = 0; i < size && n < 200; i++) {
                if (c[i] == '\t') do render[n++] = ' '; while (n%8);
                else render[n++] = c[i];
            }
            lspDrawRow(&ab,r,c,size,render,n,below(3) ? 0 : below(20),1+below(80));
            free(ab.b);
        }
        runs++;
    }
    return runs;
}

int main(int argc, char **argv) {
    double seconds = argc > 2 ? atof(argv[2]) : 3;
    long runs;
    rng ^= argc > 3 ? strtoull(argv[3],NULL,10) : (unsigned long long)time(NULL);
    printf("seed %llu\n",rng);
    if (argc > 1 && strcmp(argv[1],"frames") == 0) runs = frames(seconds);
    else if (argc > 1 && strcmp(argv[1],"json") == 0) runs = jsonfuzz(seconds);
    else if (argc > 1 && strcmp(argv[1],"messages") == 0) runs = messagesfuzz(seconds);
    else {
        fprintf(stderr,"usage: lsp-fuzz frames|json|messages SECONDS [SEED]\n");
        return 2;
    }
    if (L.pid) lspEnd(0);
    printf("ok %ld runs\n",runs);
    return 0;
}
