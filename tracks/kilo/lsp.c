/* lsp.c: kilo's language server client.
 *
 * A language server is a program that knows a language: clangd knows C. It
 * reads the file being edited the way a compiler would, and answers an
 * editor's questions about it: what is wrong with it, where a name is
 * defined. kilo starts one as a child process, with a pipe to its standard
 * input and another from its standard output, and the two talk over them.
 *
 * Whatever the server does (is slow, says something wrong, stops reading,
 * dies), kilo carries on as an editor: the server is a help, never a thing
 * the editor waits for.
 */

// @from 07.05
/* fork(), pipe() and the rest are POSIX, not C99, and realpath() is in
 * POSIX's X/Open part: on Linux, ask for them. macOS shows them anyway. */
#ifdef __linux__
#define _XOPEN_SOURCE 700
#endif
// @else
// /* fork(), pipe() and the rest are POSIX, not C99: on Linux, ask for
//  * them. macOS shows them anyway. */
// #ifdef __linux__
// #define _POSIX_C_SOURCE 200809L
// #endif
// @end

#include <ctype.h>          // @from 07.03
#include <errno.h>
#include <fcntl.h>
#include <poll.h>           // @from 07.04
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>        // @from 07.02
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include "json.h"           // @from 07.03
#include "lsp.h"

/* ================================= Limits ================================= */

#define LSP_STOP_MS 500             /* at exit, how long the server has to go */
// @from 07.02
#define LSP_HEADER_MAX 4096         /* bytes in a message's header */
#define LSP_BODY_MAX (16*1024*1024) /* bytes in its body */
#define LSP_READ_MAX (1024*1024)    /* bytes read from the server in one go */
// @end
#define LSP_QUEUE_MAX (8*1024*1024) /* bytes waiting for a server that does not read */ // @from 07.04
#define LSP_PAUSE_MS 300            /* no key for this long: the keys have paused */ // @from 07.05
#define LSP_DIAG_MAX 1000           /* diagnostics kept for one file */ // @from 07.06

/* ========================= The servers kilo knows ========================= */

/* A server: the files it is for (endings of their names), what the
 * protocol calls their language, and the command that starts it. */
struct lspServer {
    char **filematch;
    char *language;
    char *argv[4];
};

char *LSP_C_endings[] = {".c",".h",NULL};
char *LSP_CPP_endings[] = {".cpp",".hpp",".cc",NULL};

struct lspServer LSPDB[] = {
    { LSP_C_endings, "c", {"clangd",NULL} },
    { LSP_CPP_endings, "cpp", {"clangd",NULL} }
};

#define LSPDB_ENTRIES (sizeof(LSPDB)/sizeof(LSPDB[0]))

/* The server for a file's name: the first in LSPDB with an ending that
 * ends the name, or NULL. */
static struct lspServer *lspServerFor(const char *filename) {
    // @build 07.01 a server chosen by the file's name
    // For each server in LSPDB, each of its endings: if filename is longer
    // than the ending and ends with it, that is the server.
    size_t n = strlen(filename);
    unsigned int j, i;

    for (j = 0; j < LSPDB_ENTRIES; j++) {
        for (i = 0; LSPDB[j].filematch[i]; i++) {
            size_t m = strlen(LSPDB[j].filematch[i]);
            if (n > m && strcmp(filename+n-m,LSPDB[j].filematch[i]) == 0)
                return LSPDB+j;
        }
    }
    return NULL;
    // @end
}

/* =============================== The state =============================== */

// @from 07.02
/* Bytes that grow at the end and are used up from the front: what came
 * from the server and is not yet a whole message, or what is to go to it
 * and is not yet written. */
struct lspBuf {
    char *b;
    size_t off;             /* the bytes before off are used up */
    size_t len;             /* the bytes in b */
    size_t cap;             /* the room in b */
};

// @end
// @from 07.06
/* A diagnostic: from (line, col) to (endline, endcol), lines from 0 and
 * columns as bytes of the line, the way kilo counts them in chars. */
struct lspDiag {
    int line, col, endline, endcol;
    int severity;           /* 1 error, 2 warning, 3 information, 4 hint */
    char *message;          /* its first line */
};

// @end
/* Everything the client knows, in one place, as E is for the editor. */
struct lspState {
    pid_t pid;              /* the server, or 0 when none is running */
    int in;                 /* our end of the pipe to its standard input */
    int out;                /* our end of the pipe from its standard output */
    const char *name;       /* its command's name, for messages: "clangd" */
    const char *language;   /* what the protocol calls the file's language */
    // @from 07.02
    int redraw;             /* a message changed what the screen shows */
    struct lspBuf rx;      /* read from the server, not yet a whole message */
    struct lspBuf tx;       /* waiting to be written to it */
    int nextid;             /* the id of the last request sent */
    int initid;             /* the initialize request's, until it is answered */
    // @end
    // @from 07.03
    int ready;              /* initialize has been answered */
    int dropped;            /* messages that were not JSON, dropped */
    // @end
    // @from 07.05
    char *path;             /* the open file, as an absolute path */
    char *uri;              /* the same, as the protocol names it */
    char *text;             /* a copy of the text the server has, */
    size_t textlen;         /* its length, */
    int version;            /* and its version number */
    int changes;            /* does the server take changes? */
    int haschg;             /* is a didChange waiting whole in tx? */
    size_t chg, chglen;     /* where it starts, and its length */
    int shutid;             /* the shutdown request's id, until answered */
    int stopping;           /* kilo is exiting: draw nothing */
    // @end
    // @from 07.06
    int utf8;               /* positions count bytes, not UTF-16 code units */
    struct lspDiag *diag;   /* the diagnostics for the open file, */
    int ndiag;              /* how many, */
    int counts[5];          /* and how many of each severity, last said */
    size_t *lines;          /* where each line of the copy starts, */
    int nlines;             /* how many lines it has (0: not worked out) */
    int shownrow, shown;    /* the row and diagnostic last said at a pause */
    // @end
    // @from 07.07
    int hasdef;             /* can the server find definitions? */
    int defid;              /* the definition request's id, until answered */
    char *back;             /* where Ctrl-B goes: a file, */
    int backrow, backcol;   /* and a place in it */
    // @end
};

static struct lspState L;

/* Functions used before the place they are defined. */
static void lspStop(void);
static void lspInitialize(void);                                // @from 07.02
static void lspInitialized(json *result);                       // @from 07.03
// @from 07.05
static int lspRequest(const char *method, const char *params);
static void lspNotify(const char *method, const char *params);
static int lspWaitServer(long long deadline);
static void lspOpen(void);
static void lspNotFound(json *id);
static void lspPause(void);
static char *lspAbsolute(const char *name);
static char *lspUri(const char *path);
// @end
// @from 07.06
static void lspSetDiagnostics(struct lspDiag *list, int n);
static void lspDiagnostics(json *params);
static int lspShowDiagnostic(void);
// @end
static void lspDefinitionResult(json *result);                  // @from 07.07

/* Milliseconds from some fixed moment: for timeouts, which a change to the
 * clock must not stretch or cut. */
static long long lspNow(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC,&ts);
    return (long long)ts.tv_sec*1000 + ts.tv_nsec/1000000;
}

// @from 07.02
/* Say something in the message line, printf style, and have the screen
 * drawn again. A control byte would reach the terminal as it is, and what
 * a server sends can hold any: each becomes a '?'. */
// @else
// /* Say something in the message line, printf style. A control byte would
//  * reach the terminal as it is, and what a server sends can hold any:
//  * each becomes a '?'. */
// @end
static void lspSay(const char *fmt, ...) {
    char msg[80];
    va_list ap;
    int i;

    va_start(ap,fmt);
    vsnprintf(msg,sizeof(msg),fmt,ap);
    va_end(ap);
    for (i = 0; msg[i]; i++)
        if ((unsigned char)msg[i] < 32 || msg[i] == 127) msg[i] = '?';
    editorSetStatusMessage("%s",msg);
    L.redraw = 1;                   // @from 07.02
}

// @from 07.02
/* Make room for n more bytes at the end of buf. Returns 0, or -1 when
 * there is no memory for them. */
static int lspBufRoom(struct lspBuf *buf, size_t n) {
    char *b;
    size_t cap;
    if (buf->len+n <= buf->cap) return 0;
    cap = (buf->len+n)*2;
    if ((b = realloc(buf->b,cap)) == NULL) return -1;
    buf->b = b;
    buf->cap = cap;
    return 0;
}

/* Add n bytes at s to the end of buf. Returns 0, or -1. */
static int lspBufAdd(struct lspBuf *buf, const char *s, size_t n) {
    if (lspBufRoom(buf,n) == -1) return -1;
    memcpy(buf->b+buf->len,s,n);
    buf->len += n;
    return 0;
}

/* Drop the used bytes from the front of buf, once they are at least half
 * of it (so each byte is moved about once). Returns how far the rest
 * moved. */
static size_t lspBufTrim(struct lspBuf *buf) {
    size_t moved = buf->off;
    if (buf->off == 0 || buf->off < buf->len/2) return 0;
    memmove(buf->b,buf->b+buf->off,buf->len-buf->off);
    buf->len -= buf->off;
    buf->off = 0;
    return moved;
}

/* printf into a new allocation, which the caller frees; NULL when there is
 * no memory. */
static char *lspFormat(const char *fmt, ...) {
    va_list ap;
    int n;
    char *s;

    va_start(ap,fmt);
    n = vsnprintf(NULL,0,fmt,ap);
    va_end(ap);
    if (n < 0 || (s = malloc(n+1)) == NULL) return NULL;
    va_start(ap,fmt);
    vsnprintf(s,n+1,fmt,ap);
    va_end(ap);
    return s;
}

// @end
/* ======================== Starting and stopping it ======================== */

/* Start argv[0] (looked for in PATH, as a shell does) with a pipe to its
 * standard input and one from its standard output, our ends in L.in and
 * L.out. Returns its pid, or -1 with errno saying why it did not start. */
static pid_t lspSpawn(char **argv) {
    // @build 07.01 fork, exec and the pipes
    // Make three pipes and mark all six ends close-on-exec: one for the
    // server's input, one for its output, and one for the child to send
    // back errno if execvp() fails. Hold SIGWINCH back, and fork(). The
    // child sets SIGWINCH to its default and lets it through again, makes
    // the first two pipes its standard input and output (dup2, which
    // leaves the copies open across exec), /dev/null its standard error,
    // and runs the command; if that returns, it writes errno into the
    // third pipe and exits. The parent lets SIGWINCH through, closes the
    // child's ends and reads the third pipe: nothing (end of file, the exec
    // closed it) means the server is running; an errno means it is not, so
    // reap the child and fail with it. Make our two ends non-blocking.
    int in[2], out[2], err[2];  /* each: [0] the end to read, [1] to write */
    int fds[6], e, j;
    ssize_t n;
    pid_t pid;
    sigset_t winch, old;

    if (pipe(in) == -1) return -1;
    if (pipe(out) == -1) {
        close(in[0]); close(in[1]);
        return -1;
    }
    if (pipe(err) == -1) {
        close(in[0]); close(in[1]); close(out[0]); close(out[1]);
        return -1;
    }
    fds[0] = in[0]; fds[1] = in[1]; fds[2] = out[0];
    fds[3] = out[1]; fds[4] = err[0]; fds[5] = err[1];
    for (j = 0; j < 6; j++) fcntl(fds[j],F_SETFD,FD_CLOEXEC);

    /* Until the exec the child runs kilo's code, kilo's resize handler too:
     * a resize then would draw a screen from the child, onto the terminal
     * or into the pipe. So SIGWINCH is held back across fork(); the child
     * takes the default action for it before letting it through (a mask
     * still blocking it would go on into the server, across exec), and the
     * parent lets it through after, when a resize that came meanwhile is
     * drawn as usual. */
    sigemptyset(&winch);
    sigaddset(&winch,SIGWINCH);
    sigprocmask(SIG_BLOCK,&winch,&old);
    pid = fork();
    if (pid == 0) {
        int null = open("/dev/null",O_WRONLY|O_CLOEXEC);
        signal(SIGWINCH,SIG_DFL);
        sigprocmask(SIG_SETMASK,&old,NULL);
        dup2(in[0],STDIN_FILENO);
        dup2(out[1],STDOUT_FILENO);
        if (null != -1) dup2(null,STDERR_FILENO); else close(STDERR_FILENO);
        execvp(argv[0],argv);
        e = errno;
        if (write(err[1],&e,sizeof(e)) == -1) {}
        _exit(127);
    }
    e = errno;
    sigprocmask(SIG_SETMASK,&old,NULL);
    close(in[0]); close(out[1]); close(err[1]);
    if (pid == -1) {
        close(in[1]); close(out[0]); close(err[0]);
        errno = e;
        return -1;
    }
    /* Wait for the exec: either the child's errno, or end of file. */
    while ((n = read(err[0],&e,sizeof(e))) == -1 && errno == EINTR);
    close(err[0]);
    if (n == sizeof(e)) {
        while (waitpid(pid,NULL,0) == -1 && errno == EINTR);
        close(in[1]); close(out[0]);
        errno = e;
        return -1;
    }
    L.in = in[1];
    L.out = out[0];
    fcntl(L.in,F_SETFL,fcntl(L.in,F_GETFL) | O_NONBLOCK);
    fcntl(L.out,F_SETFL,fcntl(L.out,F_GETFL) | O_NONBLOCK);
    return pid;
    // @end
}

/* Stop the server: close the pipes, give it ms milliseconds to exit, and
 * kill it if it has not; reap it either way, so no zombie is left. Returns
 * its status, as waitpid() gives it. */
static int lspEnd(int ms) {
    int status = 0;
    /* None running: nothing to stop. (waitpid(0) and kill(0) would mean
     * every process in kilo's group, kilo too.) */
    if (L.pid == 0) return 0;
    // @build 07.01 stop the server
    // Close both our ends: the server reads end of file, which tells it to
    // go. Every 10 ms see whether it has (waitpid with WNOHANG); once ms
    // have passed, send it SIGKILL and wait for that. Note that no server
    // is running.
    long long deadline = lspNow()+ms;
    struct timespec tick = {0, 10*1000*1000};
    pid_t r;

    close(L.in);
    close(L.out);
    L.in = L.out = -1;
    while (1) {
        r = waitpid(L.pid,&status,WNOHANG);
        if (r != 0 && !(r == -1 && errno == EINTR)) break;  /* reaped */
        if (lspNow() >= deadline) {
            kill(L.pid,SIGKILL);
            while (waitpid(L.pid,&status,0) == -1 && errno == EINTR);
            break;
        }
        nanosleep(&tick,NULL);
    }
    L.pid = 0;
    // @end
    // @from 07.02
    /* Forget what was on the way to it and from it. */
    free(L.rx.b);
    free(L.tx.b);
    memset(&L.rx,0,sizeof(L.rx));
    memset(&L.tx,0,sizeof(L.tx));
    L.initid = 0;
    // @end
    L.ready = 0;                    // @from 07.03
    // @from 07.05
    L.haschg = 0;
    L.shutid = 0;
    // @end
    lspSetDiagnostics(NULL,0);      // @from 07.06
    L.defid = 0;                    // @from 07.07
    return status;
}

// @from 07.02
/* The server closed its end of a pipe: it has exited, or is about to.
 * Reap it, and say how it ended. */
static void lspGone(void) {
    int status;
    if (L.pid == 0) return;
    status = lspEnd(100);
    if (WIFSIGNALED(status))
        lspSay("lsp: %s exited (signal %d)",L.name,WTERMSIG(status));
    else
        lspSay("lsp: %s exited (status %d)",L.name,WEXITSTATUS(status));
}

/* Stop a server that cannot be talked to any more, at once, and say why
 * (fmt has a %s for its name). */
static void lspKill(const char *fmt) {
    lspEnd(0);
    lspSay(fmt,L.name);
}

// @end
/* Start the language server for a file, if there is one for it. */
void lspStart(const char *filename) {
    // @build 07.01 start the server
    // The command: KILO_LSP when it is set and not empty, for any file
    // (set and empty: no server at all); else the server lspServerFor()
    // finds; with neither, return without a word, as for a file kilo has
    // nothing for. The language: the table's, or "plaintext". Start it
    // with lspSpawn(); if that fails, say why. Otherwise have lspStop()
    // run at exit, and say it started.
    struct lspServer *s = lspServerFor(filename);
    char *cmd = getenv("KILO_LSP"), *argv[2], **run = argv;

    if (cmd && cmd[0] == '\0') return;
    if (cmd) {
        argv[0] = cmd;
        argv[1] = NULL;
    } else if (s) {
        run = s->argv;
    } else {
        return;
    }
    L.language = s ? s->language : "plaintext";
    L.name = strrchr(run[0],'/') ? strrchr(run[0],'/')+1 : run[0];
    L.pid = lspSpawn(run);
    if (L.pid == -1) {
        L.pid = 0;
        lspSay("lsp: cannot start %s: %s",L.name,strerror(errno));
        return;
    }
    atexit(lspStop);
    lspSay("lsp: started %s (pid %d)",L.name,(int)L.pid);
    // @end
    // @from 07.05
    L.path = lspAbsolute(filename);
    L.uri = lspUri(L.path);
    // @end
    lspInitialize();                // @from 07.02
}

/* At exit (atexit() runs it before editorAtExit(), which was registered
 * first): stop the server, if one is running, within LSP_STOP_MS. */
static void lspStop(void) {
    long long deadline = lspNow()+LSP_STOP_MS, left;

    if (L.pid == 0) return;
    // @build 07.05 shutdown, then exit
    // If the server is ready, ask it to shut down (a request) and wait for
    // the answer; then tell it to exit (a notification) and wait until
    // that is written. Stop waiting at the deadline, whatever has happened.
    // Before it is ready there is nothing to say: just stop it.
    L.stopping = 1;
    if (L.ready) {
        L.shutid = lspRequest("shutdown",NULL);
        while (L.pid && L.shutid && lspWaitServer(deadline));
        if (L.pid) lspNotify("exit",NULL);
        while (L.pid && L.tx.off < L.tx.len && lspWaitServer(deadline));
    }
    // @end
    // @build 07.01 at exit
    // lspEnd() it, with what is left of the LSP_STOP_MS.
    left = deadline-lspNow();
    if (L.pid) lspEnd(left > 0 ? (int)left : 0);
    // @end
}

// @from 07.02
/* ================================ Messages ================================ */

/* One line of a header, n bytes at s, without its "\r\n": "Name: value".
 * Content-Length sets *length; any other header (Content-Type) is
 * ignored. Returns 0, or -1 if the line is damaged. */
static int lspHeaderLine(const char *s, size_t n, long *length) {
    const char *colon = memchr(s,':',n), *v, *end = s+n, *digits;
    long x = 0;

    if (colon == NULL || colon == s) return -1;
    if (colon-s != 14 || strncasecmp(s,"Content-Length",14) != 0) return 0;
    v = colon+1;
    while (v < end && (*v == ' ' || *v == '\t')) v++;
    digits = v;
    while (v < end && *v >= '0' && *v <= '9') {
        x = x*10 + (*v-'0');
        if (x > LSP_BODY_MAX) return -1;    /* too long, or absurd */
        v++;
    }
    if (v == digits) return -1;
    while (v < end && (*v == ' ' || *v == '\t')) v++;
    if (v != end) return -1;
    if (*length != -1 && *length != x) return -1;   /* two, that differ */
    *length = x;
    return 0;
}

/* Is a whole message at the front of buf, len bytes? A message is a
 * header, lines of "Name: value" each ended by "\r\n", then an empty line,
 * then a body of exactly Content-Length bytes: the JSON. Returns the whole
 * message's length, with its body at *body, *bodylen bytes long; 0 if more
 * bytes are needed; -1 if the header is damaged, longer than
 * LSP_HEADER_MAX, or has no Content-Length, or one over LSP_BODY_MAX.
 * After a -1 there is no telling where the next message starts. */
static long lspFrame(const char *buf, size_t len, size_t *body, size_t *bodylen) {
    // @build 07.02 take a message off the input
    // Walk the header a line at a time: find the "\r\n" that ends the line
    // (none yet: 0 if the header could still fit, else -1); an empty line
    // ends the header; any other goes to lspHeaderLine(). Then, with the
    // length known, 0 until all of the body is there.
    size_t p = 0, e;
    long length = -1;

    while (1) {
        for (e = p; e+1 < len && !(buf[e] == '\r' && buf[e+1] == '\n'); e++);
        if (e+1 >= len) return len >= LSP_HEADER_MAX ? -1 : 0;
        if (e+2 > LSP_HEADER_MAX) return -1;
        if (e == p) break;                      /* the empty line */
        if (lspHeaderLine(buf+p,e-p,&length) == -1) return -1;
        p = e+2;
    }
    if (length == -1) return -1;
    p = e+2;
    if (len-p < (size_t)length) return 0;
    *body = p;
    *bodylen = length;
    return p+length;
    // @end
}

/* Write the bytes waiting in L.tx, as many as the pipe takes now. */
static void lspFlush(void) {
    size_t moved;                   // @from 07.05

    if (L.pid == 0) return;
    // @build 07.02 write what the pipe takes
    // write() until L.tx is all written or the pipe is full (EAGAIN: the
    // rest waits for the next time). Any other failure (EPIPE: the server
    // closed its input) means the server has gone.
    while (L.tx.off < L.tx.len) {
        ssize_t n = write(L.in,L.tx.b+L.tx.off,L.tx.len-L.tx.off);
        if (n > 0) {
            L.tx.off += n;
            continue;
        }
        if (n == -1 && errno == EINTR) continue;
        if (n == -1 && (errno == EAGAIN || errno == EWOULDBLOCK)) break;
        lspGone();
        return;
    }
    // @end
    // @from 07.05
    /* A didChange that has begun to go can no longer be replaced; one still
     * waiting moves with the bytes around it. */
    if (L.haschg && L.tx.off > L.chg) L.haschg = 0;
    moved = lspBufTrim(&L.tx);
    if (L.haschg) L.chg -= moved;
    // @else
    // lspBufTrim(&L.tx);
    // @end
}

/* Queue one message, its body len bytes at body, and write what the pipe
 * takes now; the rest waits in L.tx. */
static void lspSend(const char *body, size_t len) {
    char head[48];
    int hlen;

    /* The server may have gone in the middle of what kilo was doing: then
     * this, and so all that follows, is nothing. */
    if (L.pid == 0) return;
    // @build 07.04 a server that does not read
    // If more than LSP_QUEUE_MAX bytes are still waiting from before, the
    // server is not reading what it is sent: stop it, and send nothing.
    if (L.tx.len-L.tx.off > LSP_QUEUE_MAX) {
        lspKill("lsp: %s is not reading; stopped");
        return;
    }
    // @end
    // @build 07.02 write a message
    // The header is "Content-Length: ", the body's length in bytes, and
    // "\r\n" twice (the end of that line, and the empty line that ends the
    // header). Queue it and the body on L.tx, then lspFlush().
    hlen = snprintf(head,sizeof(head),"Content-Length: %lu\r\n\r\n",(unsigned long)len);
    if (lspBufAdd(&L.tx,head,hlen) == -1 || lspBufAdd(&L.tx,body,len) == -1) {
        lspKill("lsp: no memory for %s's messages; stopped");
        return;
    }
    lspFlush();
    // @end
}

/* Send a request: a method and its params (JSON text, or NULL for none),
 * with a new id, which it returns. The answer will carry the same id. */
static int lspRequest(const char *method, const char *params) {
    char *msg = lspFormat("{\"jsonrpc\":\"2.0\",\"id\":%d,\"method\":\"%s\"%s%s}",
        ++L.nextid,method,params ? ",\"params\":" : "",params ? params : "");
    if (msg) lspSend(msg,strlen(msg));
    free(msg);
    return L.nextid;
}

// @from 07.05
/* Send a notification: a message with no id, which is never answered. */
static void lspNotify(const char *method, const char *params) {
    char *msg = lspFormat("{\"jsonrpc\":\"2.0\",\"method\":\"%s\"%s%s}",
        method,params ? ",\"params\":" : "",params ? params : "");
    if (msg) lspSend(msg,strlen(msg));
    free(msg);
}

// @end
/* Act on one message from the server, its body len bytes at body. */
static void lspHandle(const char *body, size_t len) {
    // @from 07.03
    json *m = jsonParse(body,len), *id;
    const char *method;
    int n;

    if (m == NULL) {
        /* Not JSON. The header said where it ends, so the next message is
         * still found: drop this one and carry on. */
        L.dropped++;
        return;
    }
    method = jsonStr(jsonGet(m,"method"),NULL);
    id = jsonGet(m,"id");
    /* An answer has no method: the id says which request it answers. One
     * not sent, or no longer waited for, is ignored. */
    n = method ? 0 : jsonInt(id,0);
    if (n != 0 && n == L.initid) lspInitialized(jsonGet(m,"result"));
    if (n != 0 && n == L.shutid) L.shutid = 0;                          // @from 07.05
    if (n != 0 && n == L.defid) lspDefinitionResult(jsonGet(m,"result"));   // @from 07.07
    // @from 07.05
    /* A method and an id: a request from the server. */
    if (method && id) lspNotFound(id);
    // @end
    // @from 07.06
    /* A method alone: a notification. */
    if (method && !id && strcmp(method,"textDocument/publishDiagnostics") == 0)
        lspDiagnostics(jsonGet(m,"params"));
    // @end
    jsonFree(m);
    // @else
    // lspSay("lsp: %lu bytes from %s: %.*s",(unsigned long)len,L.name,
    //        (int)(len < 50 ? len : 50),body);
    // @end
}

/* Read what the server has written, and act on each whole message. */
static void lspRead(void) {
    // @build 07.02 read what the server wrote
    // read() onto L.rx until the pipe is empty (EAGAIN), or LSP_READ_MAX
    // bytes have come, so a server that writes without end cannot keep the
    // editor here. End of file or an error: the server has gone, but act
    // on what came before it first. Take each whole message off the front
    // of L.rx with lspFrame() and lspHandle() it; a damaged header cannot
    // be read past, so stop the server.
    char chunk[16384];
    size_t got = 0, body, bodylen;
    int gone = 0;
    long n;

    while (got < LSP_READ_MAX) {
        ssize_t r = read(L.out,chunk,sizeof(chunk));
        if (r > 0) {
            if (lspBufAdd(&L.rx,chunk,r) == -1) {
                lspKill("lsp: no memory for %s's messages; stopped");
                return;
            }
            got += r;
            continue;
        }
        if (r == -1 && errno == EINTR) continue;
        if (r == -1 && (errno == EAGAIN || errno == EWOULDBLOCK)) break;
        gone = 1;
        break;
    }
    while (L.pid && L.rx.off < L.rx.len &&
           (n = lspFrame(L.rx.b+L.rx.off,L.rx.len-L.rx.off,&body,&bodylen)) != 0) {
        if (n == -1) {
            lspKill("lsp: bad message from %s; stopped");
            return;
        }
        L.rx.off += n;
        lspHandle(L.rx.b+L.rx.off-n+body,bodylen);
    }
    if (L.pid == 0) return;
    lspBufTrim(&L.rx);
    if (gone) lspGone();
    // @end
}

/* Look at the server without waiting: write what the pipe to it takes,
 * read what it has written and act on it, and draw the screen again if
 * that changed what it shows. */
void lspPump(void) {
    if (L.pid) lspFlush();
    if (L.pid) lspRead();
    // @from 07.05
    if (L.redraw && !L.stopping) {
    // @else
    // if (L.redraw) {
    // @end
        L.redraw = 0;
        editorRefreshScreen();
    }
}

/* The first message: initialize, which says who kilo is and what it can
 * do. Nothing else may be sent until it is answered. */
static void lspInitialize(void) {
    // @build 07.02 send initialize
    // Ignore SIGPIPE first: writing to a server that has exited would
    // otherwise kill kilo; write() then fails with EPIPE instead. Then send
    // the request, keeping its id.
    struct sigaction sa;
    char params[512];

    sa.sa_handler = SIG_IGN;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    sigaction(SIGPIPE,&sa,NULL);
    snprintf(params,sizeof(params),
        "{\"processId\":%d,\"rootUri\":null,\"capabilities\":{"
            "\"general\":{\"positionEncodings\":[\"utf-8\",\"utf-16\"]},"  // @from 07.06
            "\"textDocument\":{"                                         // @from 07.05
                "\"publishDiagnostics\":{},"                             // @from 07.06
                "\"definition\":{\"linkSupport\":false},"                // @from 07.07
                "\"synchronization\":{\"didSave\":false}"                // @from 07.05
            "}"                                                          // @from 07.05
        "}}",(int)getpid());
    L.initid = lspRequest("initialize",params);
    // @end
}

// @end
// @from 07.03
/* The answer to initialize: what the server is, and what it can do. */
static void lspInitialized(json *result) {
    // @build 07.03 the server is ready
    // A result that is not an object means initialize failed: stop the
    // server. Otherwise it is ready: say so, with the name and version in
    // result.serverInfo (the name alone with no version; the command's name
    // with no serverInfo). A version is often a sentence ("Apple clangd
    // version 21.0.0 (...)"): show its first word that starts with a
    // digit, or else its first word.
    json *info = jsonGet(result,"serverInfo");
    const char *name = jsonStr(jsonGet(info,"name"),L.name);
    const char *version = jsonStr(jsonGet(info,"version"),""), *v = version;
    int vlen;

    L.initid = 0;
    if (!jsonIs(result,JSON_OBJECT)) {
        lspKill("lsp: %s did not initialize; stopped");
        return;
    }
    while (*v && !(isdigit((unsigned char)*v) && (v == version || v[-1] == ' '))) v++;
    if (*v == '\0') v = version;
    vlen = strcspn(v," ");
    L.ready = 1;
    // @from 07.07
    lspSay("lsp: %s%s%.*s ready | Ctrl-G = definition | Ctrl-B = back",
           name,vlen ? " " : "",vlen,v);
    // @else
    // lspSay("lsp: %s%s%.*s ready",name,vlen ? " " : "",vlen,v);
    // @end
    // @end
    // @build 07.05 tell the server what is open
    // Read the capabilities that matter: textDocumentSync (a number, or an
    // object with the number in change) of 0 means the server takes no
    // changes. Then send initialized, and open the file with lspOpen().
    json *caps = jsonGet(result,"capabilities");
    json *sync = jsonGet(caps,"textDocumentSync");
    // @from 07.06
    /* utf-16 unless it says otherwise (the protocol's default). */
    L.utf8 = strcmp(jsonStr(jsonGet(caps,"positionEncoding"),"utf-16"),"utf-8") == 0;
    // @end
    // @from 07.07
    json *def = jsonGet(caps,"definitionProvider");
    L.hasdef = jsonIs(def,JSON_OBJECT) || (jsonIs(def,JSON_BOOL) && def->number);
    // @end

    if (jsonIs(sync,JSON_OBJECT)) sync = jsonGet(sync,"change");
    L.changes = jsonInt(sync,1) != 0;
    lspNotify("initialized","{}");
    lspOpen();
    // @end
}

// @end
// @from 07.04
/* =========================== Keys and the server =========================== */

/* Wait until a key has come in on fd, and look after the server while
 * waiting: kilo calls this before it reads a key. */
void lspWaitKey(int fd) {
    // @build 07.04 the keyboard and the server at once
    // With no server, return at once. Otherwise poll() the keyboard and the
    // server's output, and its input too while there is something to
    // write; no timeout. A poll() a resize interrupts (EINTR) is simply
    // done again: the resize handler has drawn the screen. After each
    // wakeup lspPump(), which writes, reads and draws what it can without
    // waiting; then, if a key is there, return.
    struct pollfd p[3];
    long long pause = lspNow()+LSP_PAUSE_MS;    // @from 07.05
    int paused = 0;                             // @from 07.05

    while (L.pid) {
        int n = 2, timeout = -1, r;
        p[0].fd = fd;
        p[0].events = POLLIN;
        p[1].fd = L.out;
        p[1].events = POLLIN;
        if (L.tx.off < L.tx.len) {
            p[2].fd = L.in;
            p[2].events = POLLOUT;
            n = 3;
        }
        // @from 07.05
        /* Until the keys pause, wait no longer than the pause has left. */
        if (!paused) {
            long long left = pause-lspNow();
            timeout = left > 0 ? (int)left : 0;
        }
        // @end
        r = poll(p,n,timeout);
        if (r == -1 && errno == EINTR) continue;
        if (r == -1) return;
        // @from 07.05
        if (r == 0 && !paused) {
            paused = 1;
            lspPause();
        }
        // @end
        lspPump();
        if (r > 0 && p[0].revents) {
            L.defid = 0;    /* a key cancels a jump still to come */ // @from 07.07
            return;
        }
    }
    // @end
}

// @end
// @from 07.05
/* ========================== The text on the server ========================== */

/* The file's absolute path, in a new allocation: realpath() for a file
 * that exists, else the current directory and the name. */
static char *lspAbsolute(const char *name) {
    char cwd[4096], *real = realpath(name,NULL);
    if (real) return real;
    if (name[0] == '/' || getcwd(cwd,sizeof(cwd)) == NULL) return strdup(name);
    return lspFormat("%s/%s",cwd,name);
}

/* A path as the protocol names a file, in a new allocation: "file://" and
 * the path, each byte that is not a letter, a digit, '-', '.', '_', '~' or
 * '/' written as '%' and two hex digits (a space is %20). Nothing in it
 * then needs quoting in JSON either. */
static char *lspUri(const char *path) {
    // @build 07.05 a path as a URI
    // Room for "file://" and three bytes for each byte of the path; then
    // copy, escaping the bytes the comment above says.
    static const char hex[] = "0123456789ABCDEF";
    char *uri = malloc(7+3*strlen(path)+1), *u = uri;

    if (uri == NULL) return NULL;
    memcpy(u,"file://",7);
    u += 7;
    for (; *path; path++) {
        unsigned char c = *path;
        if (isalnum(c) || strchr("-._~/",c)) {
            *u++ = c;
        } else {
            *u++ = '%';
            *u++ = hex[c >> 4];
            *u++ = hex[c & 15];
        }
    }
    *u = '\0';
    return uri;
    // @end
}

/* Tell the server the file is open, with its text as it is now, version
 * 1; that text is the copy from now on. */
static void lspOpen(void) {
    // @build 07.05 open the file on the server
    // Take the text with editorRowsToString() as the copy, version 1, and
    // send didOpen with the uri, the language, the version and the text,
    // quoted with jsonQuote().
    int len;
    char *quoted, *params;

    free(L.text);
    L.text = editorRowsToString(&len);
    L.textlen = len;
    L.version = 1;
    quoted = jsonQuote(L.text,L.textlen);
    params = lspFormat("{\"textDocument\":{\"uri\":\"%s\",\"languageId\":\"%s\","
                       "\"version\":1,\"text\":%s}}",L.uri,L.language,quoted);
    if (quoted && params) lspNotify("textDocument/didOpen",params);
    free(quoted);
    free(params);
    // @end
    L.nlines = 0;                   /* the copy's lines are to be found again */ // @from 07.06
}

/* Queue a didChange. One already waiting in L.tx, of which nothing has
 * been written yet, is replaced: it is out of date, and a server that
 * reads slowly would otherwise be sent every version of the file. */
static void lspSendChange(const char *body, size_t len) {
    // @build 07.05 a newer change replaces one still waiting
    // With none waiting, note where this one starts, send it, and (if
    // lspFlush() did not already begin it) how long it is. Otherwise build
    // its header and put header and body where the old one was, moving
    // what came after it.
    char head[48];
    size_t hlen, end;

    if (L.pid == 0) return;
    if (!L.haschg) {
        L.chg = L.tx.len;
        L.haschg = 1;
        lspSend(body,len);
        if (L.haschg) L.chglen = L.tx.len-L.chg;
        return;
    }
    hlen = snprintf(head,sizeof(head),"Content-Length: %lu\r\n\r\n",(unsigned long)len);
    if (lspBufRoom(&L.tx,hlen+len) == -1) {
        lspKill("lsp: no memory for %s's messages; stopped");
        return;
    }
    end = L.chg+L.chglen;
    memmove(L.tx.b+L.chg+hlen+len,L.tx.b+end,L.tx.len-end);
    memcpy(L.tx.b+L.chg,head,hlen);
    memcpy(L.tx.b+L.chg+hlen,body,len);
    L.tx.len = L.tx.len-L.chglen+hlen+len;
    L.chglen = hlen+len;
    lspFlush();
    // @end
}

/* If the text is not what the server has, send it whole: didChange, with
 * the next version number. It becomes the copy. */
static void lspSendText(void) {
    // @build 07.05 send the text, if it changed
    // Nothing to do before the server is ready, or if it takes no changes.
    // Take the text with editorRowsToString(); if it is the copy, byte for
    // byte, that is all. Otherwise it is the new copy, one version on, and
    // goes to the server in a didChange that holds all of it.
    int len;
    char *text, *quoted, *msg;

    if (!L.ready || !L.changes) return;
    text = editorRowsToString(&len);
    if ((size_t)len == L.textlen && memcmp(text,L.text,len) == 0) {
        free(text);
        return;
    }
    free(L.text);
    L.text = text;
    L.textlen = len;
    L.version++;
    quoted = jsonQuote(text,len);
    msg = lspFormat("{\"jsonrpc\":\"2.0\",\"method\":\"textDocument/didChange\","
                    "\"params\":{\"textDocument\":{\"uri\":\"%s\",\"version\":%d},"
                    "\"contentChanges\":[{\"text\":%s}]}}",L.uri,L.version,quoted);
    if (quoted && msg) lspSendChange(msg,strlen(msg));
    free(quoted);
    free(msg);
    // @end
    L.nlines = 0;                   // @from 07.06
}

/* The keys have paused (LSP_PAUSE_MS without one): bring the server up to
 * date. */
static void lspPause(void) {
    lspSendText();
    lspShowDiagnostic();            // @from 07.06
}

/* Answer a request from the server. kilo does none of the things a server
 * may ask of an editor, and says so, as the protocol has it: error -32601,
 * "method not found", with the request's id. */
static void lspNotFound(json *id) {
    // @build 07.05 answer the server's requests
    // The id goes back as it came: a string quoted again, a whole number
    // that fits an int as one; anything else as null.
    char num[16], *quoted = NULL, *msg;
    const char *text = "null";

    if (jsonIs(id,JSON_STRING)) {
        text = quoted = jsonQuote(id->string,id->len);
    } else if (jsonIs(id,JSON_NUMBER) && jsonInt(id,0) == id->number) {
        snprintf(num,sizeof(num),"%d",jsonInt(id,0));
        text = num;
    }
    msg = lspFormat("{\"jsonrpc\":\"2.0\",\"id\":%s,\"error\":"
                    "{\"code\":-32601,\"message\":\"method not found\"}}",text ? text : "null");
    if (msg) lspSend(msg,strlen(msg));
    free(quoted);
    free(msg);
    // @end
}

/* At exit: wait for the server's input or output, or the deadline; then
 * write and read what can be. Returns 0 once the deadline has passed. */
static int lspWaitServer(long long deadline) {
    struct pollfd p[2];
    long long left = deadline-lspNow();
    int n = 1;

    if (left <= 0) return 0;
    p[0].fd = L.out;
    p[0].events = POLLIN;
    if (L.tx.off < L.tx.len) {
        p[1].fd = L.in;
        p[1].events = POLLOUT;
        n = 2;
    }
    if (poll(p,n,(int)left) == -1 && errno != EINTR) return 0;
    lspPump();
    return 1;
}

// @end
// @from 07.06
/* ============================== Diagnostics ============================== */

static const char *lspSeverity[] = {"", "error", "warning", "info", "hint"};

/* The bytes of line `line` of the copy (from 0; its last line is the empty
 * one after the final newline): *s and *len. Returns 0, or -1 when the
 * copy has no such line. */
static int lspLine(int line, const char **s, size_t *len) {
    // @build 07.06 a line of the copy
    // The first time after the copy changes, note where every line
    // starts, in L.lines (one more entry at the end, where a line after
    // the last would start, so every line ends one byte before the next
    // starts). Then a line is a lookup.
    size_t i;
    int n = 1;

    if (L.text == NULL) return -1;
    if (L.nlines == 0) {
        for (i = 0; i < L.textlen; i++) if (L.text[i] == '\n') n++;
        free(L.lines);
        if ((L.lines = malloc(sizeof(size_t)*(n+1))) == NULL) return -1;
        L.lines[0] = 0;
        n = 1;
        for (i = 0; i < L.textlen; i++) if (L.text[i] == '\n') L.lines[n++] = i+1;
        L.lines[n] = L.textlen+1;
        L.nlines = n;
    }
    if (line < 0 || line >= L.nlines) return -1;
    *s = L.text+L.lines[line];
    *len = L.lines[line+1]-1-L.lines[line];
    return 0;
    // @end
}

/* How many bytes the UTF-8 character at s takes, n bytes there at most; a
 * byte that does not start a whole, well formed one counts alone. */
static int lspCharLen(const char *s, size_t n) {
    unsigned char c = s[0];
    int len = c < 0x80 ? 1 : (c >> 5) == 6 ? 2 : (c >> 4) == 14 ? 3 : (c >> 3) == 30 ? 4 : 1;
    int i;
    if ((size_t)len > n) return 1;
    for (i = 1; i < len; i++) if (((unsigned char)s[i] >> 6) != 2) return 1;
    return len;
}

/* A column as the server counts it (units into line `line` of the copy)
 * as a byte of that line; past its end, its end. -1 if there is no such
 * line. In utf-8 the two are the same. In UTF-16 a character up to U+FFFF
 * is one unit, one past it (four bytes of UTF-8) is two. */
static int lspColumn(int line, int units) {
    // @build 07.06 from the server's columns to bytes
    // In utf-8: units, but no more than the line's length. In UTF-16: walk
    // the line a character at a time (lspCharLen), counting its units,
    // and stop before the character that would take the count past units.
    const char *s;
    size_t len, i = 0;
    long u = 0;

    if (lspLine(line,&s,&len) == -1) return -1;
    if (units < 0) units = 0;
    if (L.utf8) return (size_t)units < len ? units : (int)len;
    while (i < len) {
        int n = lspCharLen(s+i,len-i), w = n == 4 ? 2 : 1;
        if (u+w > units) break;
        u += w;
        i += n;
    }
    return i;
    // @end
}

/* Make list (n diagnostics, NULL for none) the file's, freeing the old. */
static void lspSetDiagnostics(struct lspDiag *list, int n) {
    struct lspDiag *was = L.diag;
    int had = L.ndiag, j;
    sigset_t winch, old;

    /* lspDrawRow() reads the list, and the resize handler draws the screen
     * in the middle of whatever was going on: hold SIGWINCH back while the
     * list and its length change. */
    sigemptyset(&winch);
    sigaddset(&winch,SIGWINCH);
    sigprocmask(SIG_BLOCK,&winch,&old);
    L.diag = list;
    L.ndiag = n;
    sigprocmask(SIG_SETMASK,&old,NULL);
    for (j = 0; j < had; j++) free(was[j].message);
    free(was);
    L.redraw = 1;
}

/* A URI as a path, in a new allocation; NULL if it is not a file:// URI
 * with an absolute path, or is not well formed. */
static char *lspPath(const char *uri) {
    // @build 07.06 a URI as a path
    // Only "file://" followed by '/'. Each '%' and two hex digits becomes
    // the byte they spell; a '%' without two, or one that spells '\0',
    // makes it no path.
    static const char hex[] = "0123456789abcdef";
    char *path, *p;
    const char *h, *l;

    if (strncmp(uri,"file://",7) != 0 || uri[7] != '/') return NULL;
    uri += 7;
    if ((path = p = malloc(strlen(uri)+1)) == NULL) return NULL;
    while (*uri) {
        if (*uri != '%') {
            *p++ = *uri++;
            continue;
        }
        if (uri[1] == '\0' || (h = strchr(hex,tolower((unsigned char)uri[1]))) == NULL ||
            uri[2] == '\0' || (l = strchr(hex,tolower((unsigned char)uri[2]))) == NULL ||
            (h == hex && l == hex)) {
            free(path);
            return NULL;
        }
        *p++ = (h-hex)*16 + (l-hex);
        uri += 3;
    }
    *p = '\0';
    return path;
    // @end
}

/* Is path the open file? The same string, or the same file once
 * realpath() has followed every link in both. */
static int lspSameFile(const char *path) {
    char *a, *b;
    int same;

    if (strcmp(path,L.path) == 0) return 1;
    a = realpath(path,NULL);
    b = realpath(L.path,NULL);
    same = a && b && strcmp(a,b) == 0;
    free(a);
    free(b);
    return same;
}

/* textDocument/publishDiagnostics: the server's diagnostics for a file,
 * all of them, which replace those it sent before. */
static void lspDiagnostics(json *params) {
    // @build 07.06 the server's diagnostics
    // Ignore them unless they are for the open file (lspPath(), then
    // lspSameFile()), and unless their version, if they have one, is the
    // last one sent. Read each one: its range's lines, and its columns as
    // bytes (lspColumn(): past the end of a line is its end); one with a
    // line the copy does not have is dropped, and an end before the start
    // is the start. Count each by severity (1 when it has none), keep at
    // most LSP_DIAG_MAX, each with the first line of its message. Make
    // them the file's, and note the counts as said. Then, if the cursor's
    // row has one, say what it is (lspShowDiagnostic()); if not, and the
    // counts are not the ones said last, say them: "lsp: 2 errors, 1
    // warning", or "lsp: no problems".
    json *list = jsonGet(params,"diagnostics"), *d, *version = jsonGet(params,"version");
    const char *uri = jsonStr(jsonGet(params,"uri"),NULL);
    struct lspDiag *nd;
    int n = 0, counts[5] = {0,0,0,0,0}, j;
    char *path, msg[80];
    size_t mlen;

    if (uri == NULL || (path = lspPath(uri)) == NULL) return;
    j = lspSameFile(path);
    free(path);
    if (!j) return;
    if (version && jsonInt(version,-1) < L.version) return;
    if (!jsonIs(list,JSON_ARRAY)) return;
    if ((nd = malloc(sizeof(*nd)*LSP_DIAG_MAX)) == NULL) return;
    for (d = list->child; d; d = d->next) {
        json *range = jsonGet(d,"range");
        json *start = jsonGet(range,"start"), *end = jsonGet(range,"end");
        const char *text = jsonStr(jsonGet(d,"message"),"");
        struct lspDiag x;

        x.line = jsonInt(jsonGet(start,"line"),-1);
        x.endline = jsonInt(jsonGet(end,"line"),-1);
        x.col = lspColumn(x.line,jsonInt(jsonGet(start,"character"),0));
        x.endcol = lspColumn(x.endline,jsonInt(jsonGet(end,"character"),0));
        if (x.col == -1 || x.endcol == -1) continue;
        if (x.endline < x.line || (x.endline == x.line && x.endcol < x.col)) {
            x.endline = x.line;
            x.endcol = x.col;
        }
        x.severity = jsonInt(jsonGet(d,"severity"),1);
        if (x.severity < 1 || x.severity > 4) x.severity = 1;
        counts[x.severity]++;
        if (n == LSP_DIAG_MAX) continue;
        mlen = strcspn(text,"\r\n");
        if ((x.message = malloc(mlen+1)) == NULL) continue;
        memcpy(x.message,text,mlen);
        x.message[mlen] = '\0';
        nd[n++] = x;
    }
    lspSetDiagnostics(nd,n);
    L.shown = -1;
    j = memcmp(counts,L.counts,sizeof(counts)) != 0;   /* have they changed? */
    memcpy(L.counts,counts,sizeof(counts));
    /* The one where the cursor is says more than the counts. */
    if (lspShowDiagnostic() || !j) return;
    strcpy(msg,"lsp: no problems");
    for (j = 1, mlen = 5; j <= 4; j++) {
        if (counts[j] == 0) continue;
        snprintf(msg+mlen,sizeof(msg)-mlen,"%s%d %s%s",mlen > 5 ? ", " : "",counts[j],
                 lspSeverity[j],counts[j] > 1 && j != 3 ? "s" : "");
        mlen = strlen(msg);
    }
    lspSay("%s",msg);
    // @end
}

/* When a list arrives, and at a pause: if the cursor is on a row with a
 * diagnostic, say what it is, "12: error: ...": the one under the cursor,
 * or the row's first. Returns 1 if it said something. */
static int lspShowDiagnostic(void) {
    // @build 07.06 the diagnostic under the cursor
    // Find the cursor (editorCursor()), and the diagnostics that cover its
    // row; prefer one that covers its column. Say nothing (and return 0)
    // if there is none, or if it is the one already said for this row.
    int row, col, j, best = -1;
    struct lspDiag *d;

    editorCursor(&row,&col);
    for (j = 0; j < L.ndiag; j++) {
        d = L.diag+j;
        if (row < d->line || row > d->endline) continue;
        if (best == -1) best = j;
        if ((row > d->line || col >= d->col) && (row < d->endline || col <= d->endcol)) {
            best = j;
            break;
        }
    }
    if (best == -1 || (row == L.shownrow && best == L.shown)) return 0;
    L.shownrow = row;
    L.shown = best;
    d = L.diag+best;
    lspSay("%d: %s: %s",d->line+1,lspSeverity[d->severity],d->message);
    return 1;
    // @end
}

/* Called by editorRefreshScreen() after it has drawn file row filerow
 * (chars, size bytes; render, rsize bytes; from column coloff, cols wide):
 * underline the parts of it that diagnostics cover, by drawing over them. */
void lspDrawRow(struct abuf *ab, int filerow, const char *chars, int size,
                const char *render, int rsize, int coloff, int cols)
{
    // @build 07.06 underline the diagnostics
    // For each diagnostic that covers the row: the bytes of chars it
    // covers on this row, as columns of render (a tab reaches the next
    // multiple of 8, as editorUpdateRow() has it); an empty range is one
    // column. Cut that to the columns on the screen. Then "\r" back to the
    // row's start, ESC [ n C to the range's first cell (n: the cells before
    // it, where a UTF-8 character takes one), ESC [ 4 m, the same bytes of
    // render again (a space past its end; for a control byte ESC [ C,
    // leaving its cell as it was drawn), and ESC [ 0 m.
    int j, k;

    for (j = 0; j < L.ndiag; j++) {
        struct lspDiag *d = L.diag+j;
        int from, to, a = 0, b = 0, cells = 0, n;
        char buf[32];

        if (filerow < d->line || filerow > d->endline) continue;
        from = filerow == d->line ? d->col : 0;
        to = filerow == d->endline ? d->endcol : size;
        if (from > size) from = size;
        if (to > size) to = size;
        if (to < from) to = from;
        for (k = 0; k < to; k++) {          /* bytes of chars to columns of render */
            if (k == from) a = b;
            b += chars[k] == '\t' ? 8-b%8 : 1;
        }
        if (from == to) {                   /* empty: the one column at from */
            a = b;
            b = a+1;
        }
        if (a < coloff) a = coloff;
        if (b > coloff+cols) b = coloff+cols;
        if (a >= b) continue;
        for (k = coloff; k < a; k++)
            if (k >= rsize || ((unsigned char)render[k] & 0xc0) != 0x80) cells++;
        abAppend(ab,"\r",1);
        if (cells > 0) {
            n = snprintf(buf,sizeof(buf),"\x1b[%dC",cells);
            abAppend(ab,buf,n);
        }
        abAppend(ab,"\x1b[4m",4);
        for (k = a; k < b; k++) {
            unsigned char c = k < rsize ? render[k] : ' ';
            if (c < 32 || c == 127) abAppend(ab,"\x1b[C",3);
            else abAppend(ab,(char *)&c,1);
        }
        abAppend(ab,"\x1b[0m",4);
    }
    // @end
}

// @end
// @from 07.07
/* ============================ Go to definition ============================ */

/* The other way from lspColumn(): byte col of line `line` of the copy as
 * the server counts columns. 0 when there is no such line. */
static int lspUnits(int line, int col) {
    // @build 07.07 from bytes to the server's columns
    // In utf-8: col, but no more than the line's length. In UTF-16: count
    // the units of the characters before col.
    const char *s;
    size_t len;
    int i = 0, u = 0;

    if (lspLine(line,&s,&len) == -1) return 0;
    if ((size_t)col > len) col = len;
    if (L.utf8) return col;
    while (i < col) {
        int n = lspCharLen(s+i,len-i);
        u += n == 4 ? 2 : 1;
        i += n;
    }
    return u;
    // @end
}

/* Make the file at path (absolute) the open one, the cursor on row: kilo
 * reads it in place of the old (editorJump()), and the server is told,
 * didClose for the old and didOpen for the new. Returns 0, or -1 if kilo
 * did not (unsaved changes, or a file it cannot read). */
static int lspSwitch(const char *path, int row) {
    // @build 07.07 another file
    // Give editorJump() the path from the current directory when the file
    // is under it (that is what the status bar shows), else the whole
    // path. Then, with a server that is ready, didClose the old uri. The
    // new path, uri and language are the client's; the old file's
    // diagnostics go; didOpen the new one.
    char cwd[4096], *params;
    const char *shown = path;
    struct lspServer *s;
    size_t n;

    if (getcwd(cwd,sizeof(cwd)) && (n = strlen(cwd)) > 1 &&
        strncmp(path,cwd,n) == 0 && path[n] == '/') shown = path+n+1;
    if (editorJump(shown,row,0) == -1) return -1;
    if (L.ready && (params = lspFormat("{\"textDocument\":{\"uri\":\"%s\"}}",L.uri))) {
        lspNotify("textDocument/didClose",params);
        free(params);
    }
    free(L.path);
    free(L.uri);
    L.path = strdup(path);
    L.uri = lspUri(L.path);
    s = lspServerFor(path);
    L.language = s ? s->language : "plaintext";
    lspSetDiagnostics(NULL,0);
    memset(L.counts,0,sizeof(L.counts));
    if (L.ready) lspOpen();
    return 0;
    // @end
}

/* Move the cursor to row `line` of the file at path: to `units` as the
 * server counts columns when units >= 0, else to byte col. Where the
 * cursor was is remembered first, for Ctrl-B. Returns 0, or -1. */
static int lspGoTo(const char *path, int line, int units, int col) {
    // @build 07.07 jump
    // Note the file and the cursor (editorCursor()). If path is another
    // file, lspSwitch() to it, or fail. Find the column (lspColumn(), on
    // the copy, which is now of that file), and editorJump() there, in the
    // open file. The noted place becomes Ctrl-B's.
    char *here = strdup(L.path);
    int row, c;

    editorCursor(&row,&c);
    L.redraw = 1;           /* the cursor moves, or editorJump() says why not */
    if (!lspSameFile(path) && lspSwitch(path,line) == -1) {
        free(here);
        return -1;
    }
    if (units >= 0 && (col = lspColumn(line,units)) == -1) col = 0;
    editorJump(NULL,line,col);
    free(L.back);
    L.back = here;
    L.backrow = row;
    L.backcol = c;
    return 0;
    // @end
}

/* Ctrl-G: ask the server where the name under the cursor is defined. The
 * answer comes later, to lspDefinitionResult(). */
void lspDefinition(void) {
    // @build 07.07 ask for the definition
    // Say why not if there is no server, it is not ready, or it cannot
    // find definitions. Otherwise send any change first (the server must
    // see the text the cursor is in), then textDocument/definition at the
    // cursor, its column in the server's units; keep the request's id.
    int row, col;
    char *params;

    if (L.pid == 0) {
        lspSay("lsp: no server");
        return;
    }
    if (!L.ready) {
        lspSay("lsp: not ready");
        return;
    }
    if (!L.hasdef) {
        lspSay("lsp: %s cannot find definitions",L.name);
        return;
    }
    lspSendText();
    editorCursor(&row,&col);
    params = lspFormat("{\"textDocument\":{\"uri\":\"%s\"},"
                       "\"position\":{\"line\":%d,\"character\":%d}}",
                       L.uri,row,lspUnits(row,col));
    if (params) L.defid = lspRequest("textDocument/definition",params);
    free(params);
    // @end
}

/* The answer to textDocument/definition: a Location, an array of them (the
 * first is taken), or a LocationLink; or null, or an empty array. */
static void lspDefinitionResult(json *result) {
    // @build 07.07 where it is
    // Take the uri and range.start, or a LocationLink's targetUri and
    // targetSelectionRange.start. Without a uri kilo can read as a path,
    // or a line and a character, there is no definition to go to: say so.
    // Else lspGoTo() it.
    json *loc = jsonIs(result,JSON_ARRAY) ? result->child : result, *range;
    const char *uri = jsonStr(jsonGet(loc,"uri"),NULL);
    char *path;
    int line, units;

    L.defid = 0;
    range = jsonGet(loc,"range");
    if (uri == NULL) {
        uri = jsonStr(jsonGet(loc,"targetUri"),NULL);
        range = jsonGet(loc,"targetSelectionRange");
    }
    line = jsonInt(jsonGet(jsonGet(range,"start"),"line"),-1);
    units = jsonInt(jsonGet(jsonGet(range,"start"),"character"),-1);
    if (uri == NULL || line < 0 || units < 0 || (path = lspPath(uri)) == NULL) {
        lspSay("lsp: no definition found");
        return;
    }
    lspGoTo(path,line,units,0);
    free(path);
    // @end
}

/* Ctrl-B: back to where the last jump came from, and remember where that
 * was, so another Ctrl-B comes back. */
void lspBack(void) {
    // @build 07.07 back
    // With no place remembered, say so. Else lspGoTo() it, by its byte
    // column, with a copy of its path (lspGoTo() replaces it).
    char *path;

    if (L.back == NULL) {
        lspSay("lsp: no place to go back to");
        return;
    }
    if ((path = strdup(L.back)) == NULL) return;
    lspGoTo(path,L.backrow,-1,L.backcol);
    free(path);
    // @end
}

// @end
