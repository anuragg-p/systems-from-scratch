"""Figures for kilo module 07, A language server client (lessons 07.01 to 07.07), an extension.

    python3 -B art/kilo/figs07.py [name-prefix ...]
                                       writes tracks/kilo/lessons/07-language-server/figures/07.0N-*.svg

Needs clangd on the PATH (Apple clangd 21 here) for the figures that show what clangd really
says (07.01-exec-fails, 07.03-tree, 07.05, 07.06, 07.07, and the cover, which covers.py draws
from capture_cover() here); without it each of those says so and is not written, and the others
are. The rest use the track's scripted server (tests/lsp_server.py), whose bytes are the same on
every run. Two things change from run to run, and the figures show them as they came: kilo's pid
(its initialize carries it as processId, so initialize is a byte longer or shorter with a pid of
five digits or four), and times.

Every byte, message, screen and descriptor here is from a real run, or from NOTES.md where the
measurement needed instrumentation that the generator does not repeat. The project at each
lesson is written with ./learn files kilo --at 07.0N and built with make; ./kilo runs on a
pseudo-terminal through the track's own fixture (edit() in tracks/kilo/track.py), on the
sample program of NOTES.md (sum.c and add.h, SUM_C and ADD_H) in a directory named "sam ple".
Runs with clangd that need the bytes on the wire go through PROXY, a small relay between kilo
and clangd that logs every frame (body and time) and changes nothing.

  07.01-fork-exec    stepped: the descriptor tables are NOTES.md's (07.01, a scratch build that
                     listed the open descriptors after each step), read from NOTES.md here; the
                     server's own list after exec (0 and 1 pipes, 2 /dev/null) is checked against
                     the scripted server's log of its descriptors, at 07.01
  07.01-exec-fails   the message lines from runs at 07.01: clangd started (its real pid), and
                     KILO_LSP=no-such-server; read(err)'s 0 and 4 bytes and errno 2 are NOTES.md's;
                     the 4 bytes drawn are errno 2 as an int on this machine (struct, its byte order)
  07.02-frame        the initialize message at 07.02 as the scripted server read it (its log);
                     the three cards: that request, the server's response to it, and kilo's
                     initialized notification at 07.05, all from the scripted server's log
  07.02-split-reads  stepped: the scripted server writes its reply in pieces of 10 and 30 bytes and
                     the rest; a scratch copy of the project at 07.02 (READ_PATCH) logs each read()
                     and each message taken off the buffer
  07.03-tree         clangd's real reply to the project at 07.03's initialize (through PROXY),
                     trimmed to the members kilo reads; the ready line from the same run
  07.03-descent      stepped: json.c at 07.03 with a trace of every reader call (JSON_PATCH) and a
                     small driver, on {"a":[1,"x"]}, and on 65 nested arrays for the cap
  07.03-escapes      the same driver's bytes for four strings
  07.04-two-ways     NOTES.md's wake-up counts and delays (scratch builds that counted, and timed
                     runs), checked against its words, and what the 2 wake-ups at 07.04 were;
                     where the key and the message fall in the second is drawn, not measured: the
                     message waits the measured median
  07.04-poll-set     stepped: the project at 07.04 with POLL_PATCH, which logs each poll()'s array
                     and what came back; the queue frame at 07.05 (the first lesson that sends more
                     than the pipe holds: a 300 KB file to a server that waits before reading)
  07.05-session      one session of kilo at 07.05 and clangd through PROXY (capture0705: the
                     nine keys " /* ok */" typed on row 3, then Ctrl-Q): every frame, its size and
                     its time
  07.05-pause        the same session: the times the nine keys were sent and the time the relay
                     got the one didChange, on one clock
  07.06-screen       kilo at 07.06 and clangd, through PROXY: the screen and the list that drew it
  07.06-columns      kilo at 07.06 and clangd, the line with two e-acutes: the range clangd sends
                     in utf-8 and, with PROXY taking utf-8 out of the offer, in utf-16; the cells
                     the terminal underlines (Screen with utf8=True)
  07.06-drawn-over   the bytes kilo at 07.06 wrote for the error's row (ed.raw), and the row
  07.07-jump         stepped: kilo at 07.07 and clangd through PROXY: Ctrl-G on total, Ctrl-G on
                     add, Ctrl-B, Ctrl-G with an unsaved change: screens, requests and replies
  07.07-uri          the uri of the add.h reply in the same run, and the path lspPath() makes of it
                     (checked: the file's own path); each outcome's message from that run, "no
                     definition found" from Ctrl-G on the empty row 3

Uris and paths are shown with the scratch directory above "sam ple" cut to "..." (trim_uri).

The maps, the cover and the icon are not made here (archmap.py, covers.py).
"""
import contextlib
import functools
import json
import os
import re
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import figlib  # noqa: E402
from figlib import Fig, write, fmt  # noqa: E402
import steps  # noqa: E402
from harness import core  # noqa: E402

figlib.LESSONS = os.path.join(ROOT, "tracks", "kilo", "lessons")
MOD = "07-language-server"
NOTES = os.path.join(ROOT, "tracks", "kilo", "NOTES.md")

SUM_C = ('#include <stdio.h>\n#include "add.h"\n\nint main(void) {\n\tint total = add(2, 3);\n'
         '\tprintf("%d\\n", total);\n\treturn 0;\n}\n')
ADD_H = "/* add.h: the one function sum.c calls. */\nstatic inline int add(int a, int b) {\n\treturn a + b;\n}\n"
DIR = "sam ple"
UP, DOWN, RIGHT, LEFT = "\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"
BACKSPACE = "\x7f"


def ctrl(ch):
    return chr(ord(ch.upper()) & 0x1f)


def notes_section(title):
    """The text of the section "### title" of NOTES.md's module 07 (to the next heading)."""
    with open(NOTES) as f:
        text = f.read()
    at = text.index("### " + title + "\n", text.index("## 07 A language server client"))
    end = re.search(r"\n#{2,3} ", text[at + 4:])
    return text[at:at + 4 + end.start()] if end else text[at:]


def check_sample():
    """SUM_C and ADD_H are NOTES.md's sample program (07, "How the screens below were captured"),
    whose block shows the two files side by side, tabs as four spaces."""
    block = notes_section("How the screens below were captured")
    for line in (SUM_C + ADD_H).split("\n"):
        assert line.replace("\t", "    ") in block, line


# ------------------------------------------------------------------ running the project

_built = {}


def project(at, patch=None, name="kilo.c"):
    """The project at lesson `at`, written by ./learn files and built; with patch, a list of
    (old, new) made to a scratch copy of its file `name` first."""
    key = (at, name, tuple(patch or ()))
    if key not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="kilo-figs07-"), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "kilo", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        if patch:
            path = os.path.join(d, name)
            with open(path) as f:
                src = f.read()
            for old, new in patch:
                assert src.count(old) == 1, (at, old)
                src = src.replace(old, new)
            with open(path, "w") as f:
                f.write(src)
        subprocess.run(["make", "-s"], cwd=d, check=True)
        _built[key] = d
    return _built[key]


def clangd():
    path = shutil.which("clangd")
    if not path:
        raise SystemExit("figs07: clangd is not installed (it is not on the PATH): the figures that show "
                         "what clangd says cannot be made")
    return path


# A relay between kilo and clangd, as KILO_LSP: it starts clangd, passes each frame on unchanged
# and logs it (direction, time on Python's monotonic clock, the body). With KILO_FIGS_UTF16=1 it
# takes "utf-8" out of the position encodings initialize offers, as an older client would.
PROXY = r'''#!{python}
import json, os, re, select, subprocess, time
log = open(os.environ["KILO_FIGS_LOG"], "a")
utf16 = os.environ.get("KILO_FIGS_UTF16") == "1"
srv = subprocess.Popen([os.environ["KILO_FIGS_CLANGD"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, bufsize=0)
bufs = {">": b"", "<": b""}


def frames(d, data):
    bufs[d] += data
    out = []
    while b"\r\n\r\n" in bufs[d]:
        head, rest = bufs[d].split(b"\r\n\r\n", 1)
        n = int(re.search(rb"(?i)content-length: *(\d+)", head).group(1))
        if len(rest) < n:
            break
        out.append(rest[:n])
        bufs[d] = rest[n:]
    return out


def put(fd, data):
    while data:
        data = data[os.write(fd, data):]


ins = [0, srv.stdout.fileno()]
while ins:
    ready, _, _ = select.select(ins, [], [])
    for fd in ready:
        data = os.read(fd, 65536)
        d = ">" if fd == 0 else "<"
        now = time.monotonic()
        if not data:
            ins.remove(fd)
            if fd == 0:
                srv.stdin.close()
            continue
        for body in frames(d, data):
            if d == ">" and utf16:
                body = body.replace(b'"positionEncodings":["utf-8","utf-16"]', b'"positionEncodings":["utf-16"]')
            log.write(json.dumps({"dir": d, "t": now, "len": len(body), "body": body.decode("utf-8", "replace")}) + "\n")
            log.flush()
            if d == ">":
                put(srv.stdin.fileno(), b"Content-Length: %d\r\n\r\n" % len(body) + body)
        if d == "<":
            put(1, data)
srv.wait()
'''


def proxy_env(directory, utf16=False):
    """(environment, log path) for kilo with clangd behind PROXY. The relay is named clangd, so
    kilo's messages name the server as they would without it."""
    os.makedirs(os.path.join(directory, "relay"), exist_ok=True)
    path = os.path.join(directory, "relay", "clangd")
    with open(path, "w") as f:
        f.write(PROXY.replace("{python}", sys.executable))
    os.chmod(path, 0o755)
    log = os.path.join(directory, "relay.log")
    env = dict(os.environ, KILO_LSP=path, KILO_FIGS_LOG=log, KILO_FIGS_CLANGD=clangd(),
               KILO_FIGS_UTF16="1" if utf16 else "0")
    return env, log


def frames_of(log):
    """PROXY's log: [{"dir", "t", "len", "body", "msg"}], msg the body as JSON."""
    out = []
    with open(log) as f:
        for line in f:
            e = json.loads(line)
            e["msg"] = json.loads(e["body"])
            out.append(e)
    return out


def what(e):
    """A frame's name: its method, or "reply N"."""
    m = e["msg"]
    return m.get("method") or f"reply {m.get('id')}"


@contextlib.contextmanager
def editor(at, rows, cols, lsp=None, env=None, patch=None, utf8=False, sum_c=SUM_C, name=None, files=None):
    """(t, ed): kilo at lesson `at` on a rows x cols pseudo-terminal, on sam ple/sum.c (sum_c)
    next to sam ple/add.h, or on name with files written first. lsp as track.py's edit()."""
    root = project(at, patch, "lsp.c")
    track = core.Track("kilo")
    t = core.TestContext(track, track.lessons[0], root=root)
    try:
        if files is None:
            files = {os.path.join(DIR, "sum.c"): sum_c, os.path.join(DIR, "add.h"): ADD_H}
            name = os.path.join(DIR, "sum.c")
        for fn, text in files.items():
            path = os.path.join(t.tmp, fn)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        if callable(env):
            env = env(t.tmp)
        ed = t.track.edit(t, None, name=name, rows=rows, cols=cols, lsp=lsp, env=env, utf8=utf8)
        yield t, ed
    finally:
        t.cleanup()


class Shot:
    """What a screen showed: its lines, its underlines, the cursor."""

    def __init__(self, ed):
        self.lines = ed.lines
        self.unders = ed.screen.unders()
        self.cursor = ed.cursor


def tmp_real(t):
    """t.tmp as realpath() has it (on macOS /var is /private/var): the start of every uri."""
    return os.path.realpath(t.tmp)


def wait_log(path, cond, what, timeout=30, ed=None):
    """Wait until cond(entries of the JSON-lines log at path) is true, reading the screen meanwhile
    (a terminal nobody reads blocks kilo's write)."""
    deadline = time.monotonic() + timeout
    while True:
        entries = []
        if os.path.exists(path):
            with open(path) as f:
                entries = [json.loads(l) for l in f if l.strip()]
        if cond(entries):
            return entries
        if time.monotonic() > deadline:
            raise SystemExit(f"figs07: no {what} within {timeout}s")
        if ed:
            ed.pump(0.05)
        else:
            time.sleep(0.05)


def trace_lines(path):
    try:
        with open(path) as f:
            return f.read().split("\n")[:-1]
    except OSError:
        return []


def tracer(fmt, *args):
    """A C statement that appends one line to the file $KILO_TRACE, if it is set."""
    a = "".join("," + x for x in args)
    return (' { FILE *tf_ = getenv("KILO_TRACE") ? fopen(getenv("KILO_TRACE"),"a") : NULL;'
            f' if (tf_) {{ fprintf(tf_,"{fmt}\\n"{a}); fclose(tf_); }} }}')


# ------------------------------------------------------------------ 07.01: captures

def notes_fds():
    """NOTES.md's descriptor table for 07.01: [(who, step, [(fd, cloexec)])], and the server's
    own list after exec, {fd: what}."""
    block = notes_section("07.01 Starting a server: fork, exec and three pipes")
    rows, server = [], None
    for line in block.split("\n"):
        m = re.match(r"^(kilo|child)\s{2,}(\S.*?)\s{2,}((?:\d+c? ?)+)$", line)
        if m:
            fds = [(int(x.rstrip("c")), x.endswith("c")) for x in m.group(3).split()]
            rows.append((m.group(1), m.group(2), fds))
        m = re.match(r"^server after exec: (.*) \(the scripted server's own list\)$", line)
        if m:
            server = {int(k): v for k, v in (p.split(" ", 1) for p in m.group(1).split(", "))}
    assert len(rows) == 13 and server, (rows, server)
    m = re.search(r"So in\[0\]=3, in\[1\]=4, out\[0\]=5, out\[1\]=6, err\[0\]=7, err\[1\]=8, /dev/null 9", block)
    assert m, "NOTES.md 07.01: the ends' numbers"
    assert "read(err) gave 4 bytes, an errno" in block and "errno 2 (No such file or directory), sizeof(int) = 4" in block
    return rows, server


@functools.cache
def capture0701():
    """The scripted server's own descriptors after exec, kilo's message with clangd, and with a
    command that does not exist: all at 07.01."""
    out = {}
    with editor("07.01", 10, 56, lsp="") as (t, ed):
        log = wait_log(ed.lsp_log, lambda es: any(e["event"] == "start" for e in es), "start of the server")
        out["server_fds"] = {int(k): v for k, v in next(e for e in log if e["event"] == "start")["fds"].items()}
        ed.quit()
    with editor("07.01", 10, 64, lsp="table") as (t, ed):
        clangd()
        ed.wait_message(r"^lsp: started clangd \(pid \d+\)$", timeout=30)
        out["started"] = ed.message
        ed.quit()
    with editor("07.01", 10, 64, lsp="env", env=lambda tmp: dict(os.environ, KILO_LSP="no-such-server")) as (t, ed):
        ed.wait_message(r"^lsp: cannot start no-such-server: No such file or directory$", timeout=10)
        out["failed"] = ed.message
        ed.quit()
    return out


# ------------------------------------------------------------------ 07.02: captures

# After each read() of the server's pipe, and each message taken off the front of the buffer:
# a line in $KILO_TRACE with the time (lspNow(), ms) and the bytes the buffer holds.
READ_PATCH = [
    ("            got += r;\n",
     "            got += r;\n" + tracer("read %ld held %lu at %lld", "(long)r", "(unsigned long)(L.rx.len-L.rx.off)",
                                    "lspNow()") + "\n"),
    ("        L.rx.off += n;\n",
     "        L.rx.off += n;\n" + tracer("frame %ld body %lu held %lu", "n", "(unsigned long)bodylen",
                                       "(unsigned long)(L.rx.len-L.rx.off)") + "\n"),
]
PIECES = ("def on_message(srv, msg):\n"
          "    if msg and msg.get('method') == 'initialize':\n"
          "        sent = []\n"
          "        real = srv.raw\n"
          "        srv.raw = sent.append\n"
          "        srv.default(msg)\n"
          "        srv.raw = real\n"
          "        srv.pieces(sent[0], [10, 30], gap=0.255)\n"
          "        return True\n")


@functools.cache
def capture0702():
    """The initialize frame at 07.02 and the reply, as the scripted server read and wrote them; the
    message line; then the reply in pieces of 10, 30 and the rest, as READ_PATCH saw it come."""
    out = {}
    with editor("07.02", 10, 56, lsp="") as (t, ed):
        ed.wait_message(r"^lsp: \d+ bytes from scripted-lsp: ", timeout=10)
        out["said"] = ed.message
        log = ed.server_log()
        rec = next(e for e in log if e["event"] == "recv")
        out["init_header"], out["init_body"] = rec["header"], rec["body"]
        out["reply"] = next(e for e in log if e["event"] == "send")["raw"]
        ed.quit()
    with editor("07.02", 10, 56, lsp=PIECES, patch=READ_PATCH,
                env=lambda tmp: dict(os.environ, KILO_TRACE=os.path.join(tmp, "trace"))) as (t, ed):
        ed.wait_message(r"^lsp: \d+ bytes from scripted-lsp: ", timeout=10)
        out["pieces_said"] = ed.message
        out["pieces"] = [e["raw"] for e in ed.server_log() if e["event"] == "send"]
        out["trace"] = trace_lines(os.path.join(t.tmp, "trace"))
        ed.quit()
    with editor("07.05", 10, 56, lsp="") as (t, ed):
        ed.wait_message(r"ready", timeout=10)
        recv = [e for e in ed.server_log() if e["event"] == "recv"]
        out["initialized"] = next(e["body"] for e in recv if (e["msg"] or {}).get("method") == "initialized")
        ed.quit()
    return out


# ------------------------------------------------------------------ 07.03: captures

@functools.cache
def capture0703():
    """clangd's reply to the initialize of the project at 07.03 (through PROXY), and what kilo said."""
    logs = {}

    def env(tmp):
        e, logs["log"] = proxy_env(tmp)
        return e
    with editor("07.03", 10, 56, lsp="env", env=env) as (t, ed):
        ed.wait_message(r"^lsp: clangd \S+ ready$", timeout=30)
        said = ed.message
        ed.quit()
        frames = frames_of(logs["log"])
    init = next(e for e in frames if e["dir"] == ">" and what(e) == "initialize")
    reply = next(e for e in frames if e["dir"] == "<" and e["msg"].get("id") == 1)
    return {"said": said, "init": init, "reply": reply}


# The reader with a line printed for every call of its four readers, as it starts and as it
# returns: where in the text it is, how deep, and (on return) whether it read a value.
JSON_PATCH = [
    ("#include <stdlib.h>\n", "#include <stdio.h>\n#include <stdlib.h>\n"),
    ("static json *jsonValue(struct jsonReader *r);\n",
     "static json *jsonValue(struct jsonReader *r);\n"
     "static json *jsonList(struct jsonReader *r);\n"
     "static json *jsonNumber(struct jsonReader *r);\n"
     "static char *jsonString(struct jsonReader *r, size_t *len);\n"
     "const char *jsonTraceStart;\n"
     "static void jsonTrace(const char *what, const char *name, struct jsonReader *r, int ok) {\n"
     "    printf(\"%s %s %ld %d %d\\n\", what, name, (long)(r->p - jsonTraceStart), r->depth, ok);\n"
     "}\n"),
    ("static json *jsonValue(struct jsonReader *r) {", "static json *jsonValueT(struct jsonReader *r) {"),
    ("static json *jsonList(struct jsonReader *r) {", "static json *jsonListT(struct jsonReader *r) {"),
    ("static json *jsonNumber(struct jsonReader *r) {", "static json *jsonNumberT(struct jsonReader *r) {"),
    ("static char *jsonString(struct jsonReader *r, size_t *len) {",
     "static char *jsonStringT(struct jsonReader *r, size_t *len);\n"
     "static char *jsonString(struct jsonReader *r, size_t *len) {\n"
     "    char *s; jsonTrace(\"enter\",\"jsonString\",r,1); s = jsonStringT(r,len);\n"
     "    jsonTrace(\"leave\",\"jsonString\",r,s != NULL); return s;\n"
     "}\n"
     "static char *jsonStringT(struct jsonReader *r, size_t *len) {"),
    ("/* Read the len bytes at s as one JSON value:",
     "static json *jsonValueT(struct jsonReader *r);\n"
     "static json *jsonListT(struct jsonReader *r);\n"
     "static json *jsonNumberT(struct jsonReader *r);\n"
     "#define WRAP(name) static json *name(struct jsonReader *r) { json *j;"
     " jsonTrace(\"enter\",#name,r,1); j = name##T(r); jsonTrace(\"leave\",#name,r,j != NULL); return j; }\n"
     "WRAP(jsonValue)\nWRAP(jsonList)\nWRAP(jsonNumber)\n\n"
     "/* Read the len bytes at s as one JSON value:"),
]
JSON_DRIVER = r"""#include <stdio.h>
#include <string.h>
#include "json.h"
extern const char *jsonTraceStart;
/* Parse argv[1]; print the trace, then "tree" or "NULL", and a string's bytes in hex. */
int main(int argc, char **argv) {
    json *j;
    size_t i;
    if (argc != 2) return 2;
    jsonTraceStart = argv[1];
    j = jsonParse(argv[1], strlen(argv[1]));
    printf("result %s\n", j ? "tree" : "NULL");
    if (j && j->type == JSON_STRING) {
        printf("bytes");
        for (i = 0; i < j->len; i++) printf(" %02X", (unsigned char)j->string[i]);
        printf("\n");
    }
    jsonFree(j);
    return 0;
}
"""


def json_run(text):
    """(trace lines, result, bytes): JSON_DRIVER with json.c at 07.03 and JSON_PATCH, on text."""
    d = project("07.03", JSON_PATCH, "json.c")
    exe = os.path.join(d, "jsontrace")
    if not os.path.exists(exe):
        with open(os.path.join(d, "jsontrace.c"), "w") as f:
            f.write(JSON_DRIVER)
        subprocess.run(["cc", "-std=c99", "-o", exe, "jsontrace.c", "json.c"], cwd=d, check=True)
    out = subprocess.run([exe, text], capture_output=True, text=True, check=True).stdout.split("\n")[:-1]
    trace = [l.split() for l in out if l.startswith(("enter ", "leave "))]
    result = next(l.split()[1] for l in out if l.startswith("result "))
    hexes = next((l.split()[1:] for l in out if l.startswith("bytes")), None)
    return [(w, name, int(at), int(depth), int(ok)) for w, name, at, depth, ok in trace], result, hexes


# ------------------------------------------------------------------ 07.04: captures

# Each poll() of lspWaitKey: the array as it is given (n entries: fd, events), then what came
# back (r, and each revents), and the bytes waiting to be written.
POLL_PATCH = [
    ("        r = poll(p,n,timeout);\n",
     "        " + tracer("call %d %d %d %d %d %d %d queue %lu", "n", "p[0].fd", "p[0].events", "p[1].fd", "p[1].events",
                       "n == 3 ? p[2].fd : -1", "n == 3 ? p[2].events : 0", "(unsigned long)(L.tx.len-L.tx.off)") + "\n"
     "        r = poll(p,n,timeout);\n"
     "        " + tracer("ret %d %d %d %d", "r", "p[0].revents", "p[1].revents", "n == 3 ? p[2].revents : 0") + "\n"),
]
LATE_INIT = ("def on_message(srv, msg):\n"
             "    if msg and msg.get('method') == 'initialize':\n"
             "        time.sleep(0.6)\n"
             "    return False\n")
SLOW_READER = ("def on_message(srv, msg):\n"
               "    if msg and msg.get('method') == 'initialize':\n"
               "        srv.default(msg)\n"
               "        time.sleep(1.0)\n"
               "        return True\n")
BIG = "".join(f"line {i:05d} of a file larger than the pipe\n" for i in range(7000))


def parse_poll(lines):
    """POLL_PATCH's lines as [(call, ret)]: call (n, [(fd, events)], queue), ret (r, [revents])."""
    out, call = [], None
    for l in lines:
        w = l.split()
        if w[0] == "call":
            n = int(w[1])
            ents = [(int(w[2]), int(w[3])), (int(w[4]), int(w[5])), (int(w[6]), int(w[7]))][:n]
            call = (n, ents, int(w[9]))
        elif w[0] == "ret":
            out.append((call, (int(w[1]), [int(x) for x in w[2:2 + call[0]]])))
    return out


@functools.cache
def capture0704():
    """The poll() calls of kilo at 07.04 with POLL_PATCH: idle, the server's answer, a key. Then at
    07.05 (with POLL_PATCH too) a 300 KB file opened on a server that waits a second before it
    reads: poll() asked about the server's input while the queue drains."""
    out = {}
    with editor("07.04", 10, 56, lsp=LATE_INIT, patch=POLL_PATCH, name="t.c", files={"t.c": "int x;\n"},
                env=lambda tmp: dict(os.environ, KILO_TRACE=os.path.join(tmp, "trace"))) as (t, ed):
        ed.wait_message(r"ready", timeout=10)
        ed.keys("x")
        out["at0704"] = parse_poll(trace_lines(os.path.join(t.tmp, "trace")))
        ed.keys(ctrl("s"))
        ed.quit()
    with editor("07.05", 10, 56, lsp=SLOW_READER, patch=POLL_PATCH, name="big.c", files={"big.c": BIG},
                env=lambda tmp: dict(os.environ, KILO_TRACE=os.path.join(tmp, "trace"))) as (t, ed):
        ed.wait_for(lambda: any((e.get("msg") or {}).get("method") == "textDocument/didOpen"
                                for e in ed.server_log() if e["event"] == "recv"), "didOpen at the server", 20)
        out["at0705"] = parse_poll(trace_lines(os.path.join(t.tmp, "trace")))
        out["didopen"] = next(len(e["body"].encode()) for e in ed.server_log() if e["event"] == "recv"
                              and (e.get("msg") or {}).get("method") == "textDocument/didOpen")
        ed.quit()
    return out


# ------------------------------------------------------------------ 07.05: captures

TYPED = " /* ok */"


@functools.cache
def capture0705():
    """The session of the project at 07.05 with clangd through PROXY, the lesson's keys: sum.c
    opened; once clangd has answered, the nine keys " /* ok */" typed quickly on the empty third
    row (about 35 ms apart, the times they were sent noted on this process's clock, which is the
    relay's too); then Ctrl-Q until kilo exits (the file is modified, so kilo asks for it three
    more times first). Returns the frames, the times the keys were sent, and the row typed on."""
    logs = {}

    def env(tmp):
        e, logs["log"] = proxy_env(tmp)
        return e

    def sent_(method):
        return lambda es: any(e["dir"] == ">" and f'"method":"{method}"' in e["body"][:80] for e in es)
    with editor("07.05", 10, 56, lsp="env", env=env) as (t, ed):
        ed.wait_message(r"^lsp: clangd \S+ ready$", timeout=30)
        wait_log(logs["log"], lambda es: any(e["dir"] == "<" and "publishDiagnostics" in e["body"][:80] for e in es),
                 "clangd's first diagnostics", ed=ed)
        ed.keys(DOWN, DOWN)
        ed.pump(0.6)
        keys = []
        for k in TYPED:
            keys.append(time.monotonic())
            ed.s.send(k)
            end = time.monotonic() + 0.035
            while time.monotonic() < end:
                ed.pump(0.005)
        wait_log(logs["log"], sent_("textDocument/didChange"), "didChange", ed=ed)
        wait_log(logs["log"], lambda es: sum(e["dir"] == "<" and "publishDiagnostics" in e["body"][:80]
                                             for e in es) >= 2, "the diagnostics after it", ed=ed)
        ed.pump(0.5)
        row = ed.line(2)
        quits = 0
        while ed.s.proc.poll() is None and quits < 3:
            ed.keys(ctrl("q"))
            quits += 1
        ed.quit()
        frames = frames_of(logs["log"])
    return {"frames": frames, "keys": keys, "row": row, "quits": quits + 1}


# ------------------------------------------------------------------ 07.06: captures

@functools.cache
def capture0706():
    """kilo at 07.06 and clangd through PROXY, on a 10 x 60 terminal: Backspace in the printf line's
    total, and the screen once the error is underlined and said; the frame's bytes for that row."""
    logs = {}

    def env(tmp):
        e, logs["log"] = proxy_env(tmp)
        return e
    with editor("07.06", 10, 60, lsp="env", env=env) as (t, ed):
        ed.wait_message(r"^lsp: clangd \S+ ready$", timeout=30)
        ed.keys(*[DOWN] * 5, *[RIGHT] * 20, BACKSPACE)
        ed.wait_for(lambda: "[_:totl]" in ed.under(5), "the underline", timeout=30)
        ed.wait_message(r"^6: error", timeout=30)
        shot = Shot(ed)
        raw = bytes(ed.raw)
        ed.keys(ctrl("s"))
        ed.quit()
        frames = frames_of(logs["log"])
        tmp = tmp_real(t)
    return {"shot": shot, "raw": raw, "frames": frames, "tmp": tmp}


@functools.cache
def capture_cover(rows=10, cols=38):
    """For the module's cover (covers.py): kilo at 07.07, the whole client without module 06, and
    clangd through PROXY, on a rows x cols terminal: Backspace in the printf line's total; the screen
    once the error is underlined and said, the didChange that carried it and the list that came
    back."""
    logs = {}

    def env(tmp):
        e, logs["log"] = proxy_env(tmp)
        return e
    with editor("07.07", rows, cols, lsp="env", env=env) as (t, ed):
        ed.wait_message(r"^lsp: clangd \S+ ready", timeout=30)
        ed.keys(*[DOWN] * 5, *[RIGHT] * 20, BACKSPACE)
        ed.wait_for(lambda: "[_:totl]" in ed.under(5), "the underline", timeout=30)
        ed.wait_message(r"^6: error", timeout=30)
        shot = Shot(ed)
        ed.keys(ctrl("s"))
        ed.quit()
        frames = frames_of(logs["log"])
    change = next(e for e in frames if what(e) == "textDocument/didChange")
    diags = [e for e in frames if what(e) == "textDocument/publishDiagnostics" and e["msg"]["params"]["diagnostics"]]
    return {"shot": shot, "change": change, "diags": diags[-1]}


ETE = "\u00e9t\u00e9"
SUM_ETE = SUM_C.replace('printf("%d\\n", total);', f'printf("{ETE}: %d\\n", totl);')


@functools.cache
def capture0706columns(utf16):
    """sum.c opened with the e-acute line and totl in it, kilo at 07.06 and clangd through PROXY
    (utf16: "utf-8" taken out of the offer): the error's range, and what the screen underlines."""
    logs = {}

    def env(tmp):
        e, logs["log"] = proxy_env(tmp, utf16=utf16)
        return e
    with editor("07.06", 10, 60, lsp="env", env=env, utf8=True, sum_c=SUM_ETE) as (t, ed):
        ed.wait_for(lambda: ed.underlined(5), "the underline", timeout=30)
        under = ed.underlined(5)
        line = ed.line(5)
        raw = bytes(ed.raw)
        ed.quit()
        frames = frames_of(logs["log"])
    init = next(e for e in frames if e["dir"] == ">" and what(e) == "initialize")
    reply = next(e for e in frames if e["dir"] == "<" and e["msg"].get("id") == 1)
    diags = [e for e in frames if what(e) == "textDocument/publishDiagnostics" and e["msg"]["params"]["diagnostics"]]
    err = next(d for d in diags[-1]["msg"]["params"]["diagnostics"] if d["severity"] == 1)
    return {"under": under, "line": line, "raw": raw, "range": err["range"],
            "encoding": reply["msg"]["result"]["capabilities"].get("positionEncoding"),
            "offered": init["msg"]["params"]["capabilities"]["general"]["positionEncodings"]}


# ------------------------------------------------------------------ 07.07: captures

@functools.cache
def capture0707():
    """kilo at 07.07 and clangd through PROXY, on a 10 x 64 terminal: Ctrl-G on total in the printf
    line, Ctrl-G on add, Ctrl-B, then Left and a space before add and Ctrl-G on add again; then
    Ctrl-S and Ctrl-G on the empty row 3, where nothing is defined: the lesson's keys. For each: the
    screen before the last key, after it, and the frames it sent and got."""
    logs = {}

    def env(tmp):
        e, logs["log"] = proxy_env(tmp)
        return e

    def count():
        return len(frames_of(logs["log"])) if os.path.exists(logs["log"]) else 0
    steps_ = []
    with editor("07.07", 10, 64, lsp="env", env=env) as (t, ed):
        ed.wait_message(r"^lsp: clangd \S+ ready", timeout=30)
        wait_log(logs["log"], lambda es: any(e["dir"] == "<" and "publishDiagnostics" in e["body"][:80] for e in es),
                 "the first diagnostics", ed=ed)
        ready = Shot(ed)

        def step(name, keys, cond, settle=0.4):
            n = count()
            before = Shot(ed)
            ed.keys(*keys[:-1])
            at = Shot(ed)
            ed.keys(keys[-1])
            ed.wait_for(cond, name, timeout=30)
            ed.pump(settle)
            steps_.append({"name": name, "before": before, "at": at, "after": Shot(ed),
                           "frames": frames_of(logs["log"])[n:]})
        # the lesson's keys (07.07, Run it): eighteen Rights to the second t of total, byte 18
        step("total", [*[DOWN] * 5, *[RIGHT] * 18, ctrl("g")], lambda: ed.cursor == (4, 12))
        step("add", [*[RIGHT] * 9, ctrl("g")], lambda: ed.status.startswith("sam ple/add.h"))
        step("back", [ctrl("b")], lambda: ed.status.startswith("sam ple/sum.c"))
        step("unsaved", [LEFT, " ", ctrl("g")], lambda: ed.message.startswith("Unsaved changes"))
        ed.keys(ctrl("s"))
        step("none", [UP, UP, ctrl("g")], lambda: ed.message == "lsp: no definition found")
        ed.quit()
        tmp = tmp_real(t)
    return {"ready": ready, "steps": steps_, "tmp": tmp}


# ------------------------------------------------------------------ drawing

class F7(Fig):
    """figlib.Fig whose text may hold a character past ASCII: it goes in as a character
    reference (&#233;), so the file stays ASCII."""

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        super().text(x, y, s, cls, size, anchor, weight, mono)
        self.out[-1] = self.out[-1].encode("ascii", "xmlcharrefreplace").decode()

    def bar(self, x, y, w, h, cls, rx=0):
        """A filled shape with no stroke."""
        self.add(f'<rect class="{cls}" x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(rx)}"/>')


def cwid(size):
    return size * 0.6


def mono(f, x, y, s, cls="t", size=11, weight=None):
    """s in monospace from x, each run of non-spaces at its own column (SVG collapses runs of
    spaces). Returns the x just past it."""
    cw = cwid(size)
    col = 0
    for word in s.split(" "):
        if word:
            f.text(x + col * cw, y, word, cls, size, weight=weight, mono=True)
        col += len(word) + 1
    return x + len(s) * cw


def wrap(s, width):
    out, line = [], ""
    for w in s.split():
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def notes(f, x, y, s, width, cls="tm", size=10.5, lh=14):
    lines = wrap(s, width)
    for k, line in enumerate(lines):
        f.text(x, y + k * lh, line, cls, size)
    return y + len(lines) * lh


def screen(f, x, y, shot, cw, rh, cols, rows=None, cursor=True, numbers=False, status=True, ghost=None):
    """A terminal screen from a Shot, in a rounded frame: the rows given (all by default); the
    status bar (the last row but one) in reverse video; each underlined run with a line under
    its cells; the cursor as an outlined cell; ghost, an earlier cursor (row, col), dashed.
    Returns {row: baseline}."""
    rows = list(range(len(shot.lines))) if rows is None else list(rows)
    n = len(shot.lines)
    size = cw / 0.6
    f.rect(x - 7, y - 4, cols * cw + 14, len(rows) * rh + 8, "s fs", 6)
    base = {}
    for k, r in enumerate(rows):
        b = y + k * rh + rh * 0.72
        base[r] = b
        line = shot.lines[r]
        if status and r == n - 2:
            f.bar(x - 1, y + k * rh + 1, cols * cw + 2, rh - 2, "t", 1.5)
            mono(f, x, b, line, "f", size)
        else:
            mono(f, x, b, line, "t", size)
        u = shot.unders[r]
        for m in re.finditer(r"_+", u):
            f.line(x + m.start() * cw + 0.5, b + 2.5, x + m.end() * cw - 0.5, b + 2.5, "s")
        if numbers and r < n - 2:
            f.text(x - 14, b, str(r + 1), "tm", 9.5, "end", mono=True)
    if cursor and shot.cursor[0] in base:
        r, c = shot.cursor
        f.rect(x + c * cw - 0.5, base[r] - rh * 0.72 + 1.5, cw + 1, rh - 3, "a", 1)
        if ghost is not None and ghost[0] in base:
            gr, gc = ghost
            gy = base[gr] - rh * 0.72 + 1.5
            f.add(f'<rect class="a" x="{fmt(x + gc * cw - 0.5)}" y="{fmt(gy)}" width="{fmt(cw + 1)}" '
                  f'height="{fmt(rh - 3)}" rx="1" stroke-width="1" stroke-dasharray="2 2"/>')
            # the jump, from where the cursor was to where it is
            f.line(x + gc * cw - 1, gy + 1, x + (c + 1) * cw + 2, base[r] + rh * 0.28 - 0.5, "a", arrow=True)
    return base


def trim_uri(s, tmp):
    """A uri or path with the scratch directory it was made in cut to "...": file:///.../sam%20ple."""
    return s.replace("file://" + tmp.replace(" ", "%20"), "file:///...").replace(tmp, "/...")


# ------------------------------------------------------------------ 07.01

ENDS = {3: ("in", "read"), 4: ("in", "write"), 5: ("out", "read"), 6: ("out", "write"), 7: ("err", "read"),
        8: ("err", "write")}


def fork_exec0701():
    rows, server = notes_fds()
    cap = capture0701()
    assert cap["server_fds"] == {0: "pipe", 1: "pipe", 2: "devnull"}, cap["server_fds"]
    assert server == {0: "pipe", 1: "pipe", 2: "/dev/null"}, server
    row = {(who, step): fds for who, step, fds in rows}
    kilo_before = row[("kilo", "before")]
    kilo_pipes = row[("kilo", "FD_CLOEXEC on all six")]
    assert [fd for fd, _ in row[("kilo", "pipe(err)")]] == [fd for fd, _ in kilo_pipes]
    kilo_fork = row[("kilo", "after fork")]
    child_fork = row[("child", "after fork, open(/dev/null)")]
    kilo_closed = row[("kilo", "closed in[0] out[1] err[1]")]
    child_dup = row[("child", "dup2(null,2), then execvp")]
    assert row[("kilo", "read(err) gave 0 bytes")] == kilo_closed
    kilo_end = row[("kilo", "closed err[0]")]

    def labels(fds, dup=False, execd=False):
        out = {}
        for fd, c in fds:
            if fd in ENDS:
                p, e = ENDS[fd]
                out[fd] = (f"{p}, {e} end", c, (p, e))
            elif fd == 9:
                out[fd] = ("/dev/null", c, None)
            elif execd:
                out[fd] = {0: ("in, read end", c, ("in", "read")), 1: ("out, write end", c, ("out", "write")),
                           2: ("/dev/null", c, None)}[fd]
            elif dup:
                out[fd] = {0: ("in, read end (from 3)", c, ("in", "read")),
                           1: ("out, write end (from 6)", c, ("out", "write")),
                           2: ("/dev/null (from 9)", c, None)}[fd]
            else:
                out[fd] = ("the terminal", c, None)
        return out

    frames = [
        ("kilo alone: descriptors 0, 1 and 2 are the terminal.",
         labels(kilo_before), None, None),
        ("Three pipe() calls: in is 3 (its read end) and 4 (its write end), out 5 and 6, err 7 and 8. "
         "FD_CLOEXEC on all six: exec will close them.",
         labels(kilo_pipes), None, None),
        ("fork(): the child has a copy of every descriptor, so each pipe now has four, two in each "
         "process. The child opens /dev/null as 9.",
         labels(kilo_fork), labels(child_fork), "the child, still kilo"),
        ("The child dup2()s in's read end to 0, out's write end to 1 and /dev/null to 2: copies without "
         "close-on-exec. kilo closes 3, 6 and 8, the ends it does not use.",
         labels(kilo_closed), labels(child_dup, dup=True), "the child, still kilo"),
        ("execvp(): the child is clangd, with 0, 1 and 2 alone; exec closed 3 to 9, err's write end 8 "
         "with them, so kilo's read(7) gets 0 bytes, and kilo closes 7. kilo keeps 4 and 5.",
         labels(kilo_end), labels([(0, False), (1, False), (2, False)], execd=True), "clangd, after exec"),
    ]

    f = F7("f0701a", "kilo's descriptors and its child's as the server starts: three pipes, fork, dup2, "
           "exec; at the end the child is clangd, reading 0 and writing 1, and kilo holds 4 and 5", 372)
    f.text(24, 22, "the descriptors open in each process after each step: a build of 07.01 that listed them",
           "tm", 11)
    KX, CX, TW = 24, 432, 184           # the two tables
    Y0, RH = 66, 26
    T1, T2 = 262, 378                   # the tubes, left and right ends
    mid = [Y0 + k * RH + 9 for k in range(10)]
    TUBE = {"in": (mid[3] + mid[4]) / 2, "out": (mid[5] + mid[6]) / 2, "err": (mid[7] + mid[8]) / 2}
    # which end of each tube is which: kilo writes in, the server writes out and err
    WRITE_LEFT = {"in": True, "out": False, "err": False}
    f.text(24, 352, "c: close-on-exec (FD_CLOEXEC): exec closes it", "tm", 10.5)

    def table(x, title, labs):
        f.text(x, Y0 - 14, title, "t", 12.5, weight=700)
        for fd in range(10):
            y = Y0 + fd * RH
            if fd not in labs:
                continue
            lab, c, end = labs[fd]
            f.rect(x, y, TW, 18, "s f", 3)
            f.text(x + 10, y + 13, str(fd), "t", 11.5, weight=700, mono=True)
            f.text(x + 26, y + 13, lab, "t", 10.5)
            if c:
                f.text(x + TW - 8, y + 13, "c", "ta", 11, "end", 700, mono=True)

    def tubes(holders, drawn=None):
        """holders: {pipe: [(side, fd, end)]}: a tube for each pipe some process still holds, and a
        connector from each descriptor (those in drawn, if given) to the end it holds."""
        for p, ty in TUBE.items():
            hs = holders.get(p, [])
            if not hs:
                continue
            f.rect(T1, ty - 7, T2 - T1, 14, "m fs", 7)
            left_to_right = WRITE_LEFT[p]
            c = (T1 + T2) / 2
            for a, b in ((T1 + 10, c - 16), (c + 16, T2 - 10)):
                f.line(*((a, ty, b, ty) if left_to_right else (b, ty, a, ty)), "a", arrow=True)
            f.text(c, ty + 3.5, p, "ta", 10.5, "middle", 700, mono=True)
            for side, fd, end in hs:
                if drawn is not None and (side, fd) not in drawn:
                    continue
                y = mid[fd]
                edge = KX + TW if side == "kilo" else CX
                at_left = (end == "write") == left_to_right       # this end of the tube is on the left
                tx = T1 if at_left else T2
                near = (side == "kilo") == at_left
                if near:
                    f.path(f"M{fmt(edge + 1 if side == 'kilo' else edge - 1)} {fmt(y)} L{fmt(tx)} {fmt(ty)}", "s")
                    f.circle(tx, ty, 2, "s fa")
                else:
                    # an end held on the far side: along to the tube's far end, into its side
                    sx = T1 + 22 if at_left else T2 - 22
                    sy = ty - 7 if y < ty else ty + 7
                    x0 = edge + 1 if side == "kilo" else edge - 1
                    f.path(f"M{fmt(x0)} {fmt(y)} L{fmt(sx)} {fmt(y)} L{fmt(sx)} {fmt(sy)}", "m", dash=True)

    for k, (cap_, kl, cl, ctitle) in enumerate(frames):
        with steps.step(f, cap_):
            table(KX, "kilo", kl)
            if cl is not None:
                table(CX, ctitle, cl)
            else:
                f.rect(CX, Y0, TW, 3 * RH - 8, "m f", 3, dash=True)
                f.text(CX + TW / 2, Y0 + 3 * RH / 2 - 2, "no child yet", "tm", 10.5, "middle")
            holders = {}
            for side, labs in (("kilo", kl), ("child", cl or {})):
                for fd, (lab, c, end) in labs.items():
                    if end:
                        holders.setdefault(end[0], []).append((side, fd, end[1]))
            drawn = None
            if k == 3:
                # After dup2 the child's 0 and 1 are the ends the server will use; its 3 to 9 stay
                # open only until exec. Their lines would cross 0's and 1's: they are left out.
                drawn = {("kilo", fd) for fd in kl} | {("child", 0), ("child", 1), ("child", 6), ("child", 8)}
                f.text(CX, Y0 + 10 * RH + 8, "3 to 9 stay open until exec closes them", "tm", 10.5)
            tubes(holders, drawn)
    return f


def exec_fails0701():
    cap = capture0701()
    block = notes_section("07.01 Starting a server: fork, exec and three pipes")
    assert "kilo   read(err) gave 0 bytes" in block and "read(err) gave 4 bytes, an errno" in block
    err = struct.pack("=i", 2)                       # errno 2, ENOENT, as an int on this machine
    assert len(err) == 4
    f = F7("f0701b", "How kilo learns whether exec worked: the third pipe. When exec works it closes the "
           "child's end and read() returns 0 bytes; when it fails the child writes errno into it", 316)
    PW = 286
    for k, (title, child, wrote, got, note) in enumerate((
            ("exec works", "clangd", None, "read(7) returns 0: end of file",
             "exec closed the write end, 8, which is close-on-exec: no byte can ever come. clangd runs."),
            ("exec fails", "still kilo's code", err, "read(7) returns 4 bytes: errno 2",
             "ENOENT, no such file or directory. The child _exit(127)s; kilo reaps it at once."))):
        x = 24 + k * (PW + 20)
        f.text(x, 24, title, "t", 13, weight=700)
        f.rect(x, 38, 120, 40, "s f", 6)
        f.text(x + 60, 55, "the child", "t", 11, "middle", 600)
        f.text(x + 60, 70, child, "ta" if k == 0 else "tm", 10.5, "middle", mono=k == 0)
        f.rect(x + PW - 110, 38, 110, 40, "s f", 6)
        f.text(x + PW - 55, 55, "kilo", "t", 11, "middle", 600)
        f.text(x + PW - 55, 70, "read(7, &e, 4)", "tm", 10.5, "middle", mono=True)
        py = 124                                     # the err pipe, the child's end on the left
        f.rect(x + 30, py - 12, PW - 60, 24, "m fs", 12)
        f.text(x + 44, py + 4, "err", "ta", 10.5, weight=700, mono=True)
        f.text(x + 44 if wrote is None else x + 56, 102, "8", "t", 10.5, "end", 700, mono=True)
        f.text(x + PW - 51, 102, "7", "t", 10.5, weight=700, mono=True)
        f.line(x + PW - 55, py - 13, x + PW - 55, 81, "s", arrow=True)
        if wrote is None:
            f.line(x + 60, 80, x + 60, py - 13, "s")
            f.line(x + 50, 92, x + 70, 104, "a")
            f.line(x + 50, 104, x + 70, 92, "a")
            f.text(x + 76, 102, "closed by exec", "ta", 10.5, weight=600)
        else:
            f.line(x + 60, 80, x + 60, py - 13, "s", arrow=True)
            f.text(x + 66, 102, "write(8, &errno, 4)", "tm", 10, mono=True)
            cx0 = x + PW / 2 - 2 * 25 + 6
            for i, b in enumerate(wrote):
                f.rect(cx0 + i * 25, py - 9, 23, 18, "a af", 3)
                f.text(cx0 + i * 25 + 11.5, py + 4, f"{b:02X}", "ta", 10.5, "middle", 700, mono=True)
            f.text(x + PW / 2 + 6, py + 30, f"errno 2 as an int: 4 bytes, {sys.byteorder}-endian", "tm", 10,
                   "middle")
        f.text(x, 182, got, "t", 11.5, weight=600)
        notes(f, x, 200, note, 48)
    # what kilo says, on the message line
    f.text(24, 248, "and the message line kilo shows (07.01, a terminal 64 columns wide)", "tm", 10.5)
    for k, (said, label) in enumerate(((cap["started"], "exec works"), (cap["failed"], "exec fails"))):
        y = 258 + k * 27
        f.rect(24, y, 440, 21, "s fs", 4)
        f.text(32, y + 14.5, said, "t", 10.5, mono=True)
        f.text(476, y + 14.5, label, "tm", 10.5)
    return f


# ------------------------------------------------------------------ 07.02

def byte_glyph(f, x, y, b, slot, cls="t", size=11):
    """One byte at its slot: a character, or \\r \\n as small marks in the accent."""
    if b in "\r\n":
        f.rect(x + 0.5, y - size * 0.78, slot - 1, size * 0.95, "a af", 1.5)
        f.text(x + slot / 2, y - 1.5, "\\r" if b == "\r" else "\\n", "ta", size * 0.55, "middle", 700, mono=True)
    elif b != " ":
        f.text(x + slot / 2, y, b, cls, size, "middle", mono=True)


def frame0702():
    cap = capture0702()
    head, body = cap["init_header"], cap["init_body"]
    m = re.fullmatch(r"Content-Length: (\d+)", head)
    assert m and int(m.group(1)) == len(body.encode()), (head, len(body))
    n = len(body)
    msg = json.loads(body)
    reply = cap["reply"].split("\r\n\r\n", 1)[1]
    rmsg = json.loads(reply)
    note = json.loads(cap["initialized"])
    f = F7("f0702a", f"The initialize message at 07.02, byte by byte: a header line, an empty line, then "
           f"exactly {n} bytes of JSON; and the three shapes a JSON-RPC message takes", 352)
    f.text(24, 22, f"the first message kilo sends, as the server read it: {len(head) + 4 + n} bytes", "tm", 11)
    # the header and the empty line, a cell a byte
    cells = head + "\r\n\r\n"
    CW_, x0, y0 = 22, 24, 34
    for i, ch in enumerate(cells):
        x = x0 + i * CW_
        crlf = ch in "\r\n"
        f.rect(x, y0, CW_ - 2, 26, "a af" if crlf else "s f", 3)
        if crlf:
            f.text(x + (CW_ - 2) / 2, y0 + 17.5, "\\r" if ch == "\r" else "\\n", "ta", 10.5, "middle", 700, mono=True)
        elif ch != " ":
            f.text(x + (CW_ - 2) / 2, y0 + 18, ch, "t", 12.5, "middle", mono=True)
    hx2 = x0 + (len(head) + 2) * CW_ - 2
    f.brace_h(x0, hx2, y0 + 34)
    f.text(x0, y0 + 52, f"the header: one line, {head}, ended by \\r\\n", "t", 10.5)
    f.brace_h(hx2 + 2, x0 + len(cells) * CW_ - 2, y0 + 34, "a")
    f.text(x0 + len(cells) * CW_ - 2, y0 + 52, "an empty line:", "ta", 10.5, "end", 600)
    f.text(x0 + len(cells) * CW_ - 2, y0 + 66, "the header ends", "ta", 10.5, "end", 600)
    # the body, in two rows
    by = 128
    half = (n + 1) // 2
    size = 11
    cw = cwid(size)
    f.rect(x0, by - 16, half * cw + 16, 46, "s fs", 5)
    for k, part in enumerate((body[:half], body[half:])):
        f.text(x0 + 8, by + k * 18, part, "t", size, mono=True)
    f.brace_h(x0, x0 + half * cw + 16, by + 38)
    f.text(x0, by + 56, f"the body: exactly {n} bytes of JSON, the count the header gave; then the next "
           f"message's header", "t", 10.5)
    # the three shapes
    cy, cwd = 216, 186
    shapes = [
        ("a request", msg, ["jsonrpc", "id", "method", "params"], {"id", "method"},
         "kilo's initialize: answered, with its id"),
        ("a response", rmsg, ["jsonrpc", "id", "result"], {"id"},
         "the server's answer: the request's id, and a result (or an error); no method"),
        ("a notification", note, ["jsonrpc", "method", "params"], {"method"},
         "kilo's initialized, at 07.05: no id, so never answered"),
    ]
    for k, (title, m_, keys, accent, what) in enumerate(shapes):
        x = 24 + k * (cwd + 17)
        assert list(m_) == keys, (list(m_), keys)
        f.text(x, cy, title, "t", 12, weight=700)
        f.rect(x, cy + 8, cwd, 16 * len(keys) + 12, "s f", 5)
        for j, key in enumerate(keys):
            v = json.dumps(m_[key], separators=(",", ":"))
            if len(v) > 16:
                v = v[:1] + "..." + v[-1:]
            f.text(x + 10, cy + 26 + j * 16, f'"{key}":{v}', "ta" if key in accent else "t", 10, mono=True,
                   weight=700 if key in accent else None)
        notes(f, x, cy + 16 * len(keys) + 38, what, 34, size=10, lh=13)
    return f


def split_reads0702():
    cap = capture0702()
    data = "".join(cap["pieces"])
    sizes = [len(p.encode()) for p in cap["pieces"]]
    trace = [l.split() for l in cap["trace"]]
    reads = [(int(w[1]), int(w[3]), int(w[5])) for w in trace if w[0] == "read"]
    frame = next(w for w in trace if w[0] == "frame")
    assert [r for r, _, _ in reads] == sizes, (reads, sizes)
    assert [h for _, h, _ in reads] == [sum(sizes[:k + 1]) for k in range(len(sizes))]
    total, bodylen, left = int(frame[1]), int(frame[3]), int(frame[5])
    hlen = data.index("\r\n\r\n") + 4
    assert total == len(data) and bodylen == total - hlen and left == 0
    gaps = [reads[k][2] - reads[k - 1][2] for k in (1, 2)]
    f = F7("f0702b", "The server's answer to initialize arriving in three pieces, 10 and 30 bytes and the "
           "rest: what kilo's buffer holds after each read(), and the message taken off its front once "
           "it is whole", 300)
    f.text(24, 22, f"the scripted server writes its {total}-byte answer to kilo at 07.02 in pieces of {sizes[0]}, "
           f"{sizes[1]} and {sizes[2]} bytes, 0.255 s apart", "tm", 11)
    # the message's bytes in rows: a slot a byte, \r and \n wider so they can be read
    slot, x0, y0, lh, right = 7.8, 28, 68, 30, 612
    at, x, y = [], x0, y0
    for ch in data:
        w = 15 if ch in "\r\n" else slot
        if x + w > right:
            x, y = x0, y + lh
        at.append((x, y, w))
        x += w

    def span(a, b, cls, dash=False, fill=None):
        """A box round bytes a to b-1, a piece per row."""
        k = a
        while k < b:
            r0 = at[k][1]
            j = k
            while j < b and at[j][1] == r0:
                j += 1
            xa, xb = at[k][0], at[j - 1][0] + at[j - 1][2]
            if fill:
                f.bar(xa - 1, r0 - 13, xb - xa + 2, 18, fill, 2)
            if cls:
                f.rect(xa - 1, r0 - 13, xb - xa + 2, 18, cls, 2, dash=dash)
            k = j

    def draw(held, ends, gone=0):
        if held:
            span(0, held, None, fill="af")
        if held + gone < len(data):
            span(held + gone, len(data), "m", dash=True)
        for i, ch in enumerate(data):
            byte_glyph(f, at[i][0], at[i][1], ch, at[i][2], "t" if i < held else "tm", 11)
        if gone:
            xe, ye, we = at[gone - 1]
            f.text(xe + we + 8, ye, "<- taken off the front", "ta", 10.5, weight=600)
        for k, e in enumerate(ends):
            xe, ye, we = at[e - 1]
            f.line(xe + we + 0.5, ye - 16, xe + we + 0.5, ye + 7, "a")
            f.text(xe + we + 3, ye - 17, f"read {k + 1}", "ta", 9.5, weight=600)

    def gauge(held, label):
        """The buffer's length, on a scale of the whole message."""
        gy, gx, gw = 192, 24, 592
        f.rect(gx, gy, gw, 16, "s f", 3)
        if held:
            f.rect(gx, gy, gw * held / total, 16, "a af", 3)
        for e in (reads[0][1], reads[1][1], total):
            xe = gx + gw * e / total
            f.line(xe, gy + 16, xe, gy + 21, "m")
            f.text(xe, gy + 32, str(e), "tm", 9.5, "end" if e == total else "middle", mono=True)
        f.text(gx, gy - 8, label, "ta", 13, weight=700, mono=True)

    sy = 248
    with steps.step(f, f"read() returns {reads[0][0]} bytes: the buffer holds {reads[0][1]}, \"Content-Le\". "
                       "No \\r\\n yet, so not even the header is whole: lspFrame() says 0, wait for more."):
        draw(reads[0][1], [reads[0][1]])
        gauge(reads[0][1], f"L.rx: {reads[0][1]} bytes")
        f.text(24, sy, "lspFrame() returns 0: no line end yet, wait for more", "t", 11.5)
    body_have = reads[1][1] - hlen
    with steps.step(f, f"{gaps[0] / 1000:.3f} s later read() returns {reads[1][0]} more: {reads[1][1]} held. "
                       f"The header is whole, Content-Length {bodylen}, but only {body_have} bytes of the "
                       f"body have come: 0, wait."):
        draw(reads[1][1], [reads[0][1], reads[1][1]])
        gauge(reads[1][1], f"L.rx: {reads[1][1]} bytes")
        f.text(24, sy, f"lspFrame() returns 0: the header says {bodylen} bytes of body; {body_have} are here",
               "t", 11.5)
    with steps.step(f, f"{gaps[1] / 1000:.3f} s later read() returns the other {reads[2][0]}: {reads[2][1]} held, "
                       f"the whole message. lspFrame() returns {total}: a {hlen}-byte header and a "
                       f"{bodylen}-byte body."):
        draw(reads[2][1], [r[1] for r in reads])
        gauge(reads[2][1], f"L.rx: {reads[2][1]} bytes")
        f.text(24, sy, f"lspFrame() returns {total}: a whole message, a {hlen}-byte header and a {bodylen}-byte body",
               "t", 11.5)
    with steps.step(f, f"The message is taken off the front: {left} bytes are left, and the buffer starts where "
                       "the next message will. lspHandle() gets the body, and 07.02 says how long it was."):
        draw(0, [], gone=total)
        gauge(0, f"L.rx: {left} bytes")
        f.text(24, sy, f"taken off the front: {total} bytes; lspHandle(body, {bodylen})", "t", 11.5)
        f.rect(24, sy + 12, 380, 21, "s fs", 4)
        f.text(31, sy + 26.5, cap["pieces_said"], "t", 10, mono=True)
        f.text(414, sy + 26.5, "the message line, 56 columns", "tm", 10)
    return f


# ------------------------------------------------------------------ 07.03

def tree0703():
    cap = capture0703()
    body = cap["reply"]["body"]
    m = cap["reply"]["msg"]
    assert list(m) == ["id", "jsonrpc", "result"] and list(m["result"]) == ["capabilities", "serverInfo"], list(m)
    caps = m["result"]["capabilities"]
    info = m["result"]["serverInfo"]
    name, version = info["name"], info["version"]
    ver = next(w for w in version.split() if w[:1].isdigit())
    assert cap["said"] == f"lsp: {name} {ver} ready", cap["said"]
    ckeys = list(caps)
    f = F7("f0703a", f"clangd's answer to initialize, {len(body.encode())} bytes, trimmed to what kilo reads at "
           "07.03, and the tree jsonParse() makes of it: result, serverInfo, name is the path to \"clangd\"", 338)
    f.text(24, 22, f"clangd's answer to kilo at 07.03 ({len(body.encode())} bytes), trimmed", "tm", 11)
    vcut = version[:version.index(" (")] + " (...)"
    size, lh = 10, 17
    lines = [
        ('{"id":1,', None),
        (' "jsonrpc":"2.0",', None),
        (' "result":{', "result"),
        ('  "capabilities":{', None),
        (f'   "{ckeys[0]}":{json.dumps(caps[ckeys[0]])},', None),
        (f'   ... {len(ckeys) - 2} more members ...', "more"),
        (f'   "{ckeys[-1]}":{json.dumps(caps[ckeys[-1]])}}},', None),
        ('  "serverInfo":{', "serverInfo"),
        (f'   "name":"{name}",', "name"),
        (f'   "version":"{vcut}"}}}}}}', None),
    ]
    y = 52
    for text, mark in lines:
        if mark == "more":
            mono(f, 24, y, text, "tm", size)
        else:
            mono(f, 24, y, text, "ta" if mark in ("result", "serverInfo", "name") else "t", size,
                 weight=700 if mark else None)
        y += lh
    notes(f, 24, y + 8, f"\"version\" is all of \"{version}\"", 52, "tm", 10, 13)
    # the tree: a node per value, its children below it, each with its key
    nodes = [
        (0, "{ }", "the message", True),
        (1, '"id": 1', "number", False),
        (1, '"jsonrpc": "2.0"', "string", False),
        (1, '"result": { }', "object", True),
        (2, '"capabilities": { }', f"{len(ckeys)} members", False),
        (2, '"serverInfo": { }', "object", True),
        (3, f'"name": "{name}"', "string", True),
        (3, '"version": "Apple..."', "string", False),
    ]
    tx, ty, step_, ind = 338, 44, 30, 24
    pos = []
    for k, (lvl, label, kind, on) in enumerate(nodes):
        x, y = tx + lvl * ind, ty + k * step_
        pos.append((x, y))
        w = cwid(10.5) * len(label) + 16
        f.rect(x, y, w, 20, "a af" if on else "s f", 4)
        f.text(x + 8, y + 14, label, "ta" if on else "t", 10.5, mono=True, weight=700 if on else None)
        f.text(x + w + 6, y + 14, kind, "tm", 9.5)
    # parent lines: from each node down its left side to each child
    for k, (lvl, *_r) in enumerate(nodes):
        kids = []
        for j in range(k + 1, len(nodes)):
            if nodes[j][0] <= lvl:
                break
            if nodes[j][0] == lvl + 1:
                kids.append(j)
        if not kids:
            continue
        x0 = pos[k][0] + 10
        for j in kids:
            on = nodes[k][3] and nodes[j][3]
            f.path(f"M{fmt(x0)} {fmt(pos[k][1] + 21)} L{fmt(x0)} {fmt(pos[j][1] + 10)} L{fmt(pos[j][0] - 1)} "
                   f"{fmt(pos[j][1] + 10)}", "a" if on else "m")
    gy = ty + len(nodes) * step_ + 14
    f.text(tx, gy, "kilo reads the name with", "tm", 10)
    f.text(tx, gy + 16, 'jsonStr(jsonGet(jsonGet(result,', "t", 10, mono=True)
    f.text(tx, gy + 30, f'"serverInfo"),"name"),L.name): "{name}"', "t", 10, mono=True)
    f.text(24, 284, "and says, on the message line:", "tm", 10.5)
    f.rect(24, 292, 260, 21, "s fs", 4)
    f.text(32, 306.5, cap["said"], "t", 10.5, mono=True)
    return f


DESCENT = '{"a":[1,"x"]}'


def stacks(trace):
    """The reader's calls as the trace has them: after each event, the stack, a list of
    (function, where it started, depth inside it)."""
    out, st = [], []
    for w, name, at, depth, ok in trace:
        if w == "enter":
            st.append((name, at, depth + 1 if name == "jsonList" else depth))
        else:
            assert st and st[-1][0] == name, (st, name)
            st.pop()
        out.append(list(st))
    return out


def descent0703():
    trace, result, _ = json_run(DESCENT)
    assert result == "tree"
    st = stacks(trace)
    ev = [(w, n, a) for w, n, a, _, _ in trace]

    def at(w, n, a):
        return ev.index((w, n, a))
    deep = "[" * 65 + "]" * 65
    dtrace, dres, _ = json_run(deep)
    assert dres == "NULL"
    dst = stacks(dtrace)
    cap_i = next(i for i, e in enumerate(dtrace) if e[:2] == ("leave", "jsonList") and e[4] == 0)
    capped = dtrace[cap_i]
    assert capped[2] == 64 and capped[3] == 65, capped           # at 64, depth 65: NULL
    before = dst[cap_i - 1]                                       # the stack as that call ran
    assert json_run("[" * 64 + "]" * 64)[1] == "tree"            # 64 deep is read

    frames = [
        (at("enter", "jsonList", 0), 0,
         "jsonParse() calls jsonValue() at 0. It sees '{' and calls jsonList(): an object, one level deep."),
        (at("enter", "jsonString", 1), 1,
         "In an object each member starts with a key: jsonString() at 1 reads \"a\". Then a ':' must follow."),
        (at("enter", "jsonList", 5), 5,
         "The member's value: jsonValue() at 5 sees '[' and calls jsonList() again, for the array inside: "
         "two levels deep."),
        (at("enter", "jsonNumber", 6), 6,
         "jsonValue() at 6 sees a digit: jsonNumber() reads 1, the array's first element."),
        (at("enter", "jsonString", 8), 8,
         "After the ',', jsonValue() at 8 sees a quote: jsonString() reads \"x\"."),
        (at("leave", "jsonList", 12), 11,
         "The ']' at 11 ends the array: its jsonList() returns it, the depth is one again, and the object's "
         "loop goes on."),
        (at("leave", "jsonValue", 13), 12,
         "The '}' at 12 ends the object. jsonValue() returns the tree to jsonParse(), at 13: nothing is left "
         "after the value, so the message is one value."),
    ]
    f = F7("f0703b", "The reader's calls on {\"a\":[1,\"x\"]}: where in the text it is, and the calls on the "
           "C stack, one more for each value inside another; then the depth cap at 64", 340)
    f.text(24, 22, "json.c at 07.03, with a line printed as each of its readers starts and returns", "tm", 11)
    CW_, X0, Y0 = 30, 40, 56
    SX, SY, SH = 24, 316, 24                     # the stack: bottom left, growing up

    def text_cells(s, pos):
        for i, ch in enumerate(s):
            x = X0 + i * CW_
            f.rect(x, Y0, CW_ - 3, 26, "a af" if i == pos else "s f", 3)
            f.text(x + (CW_ - 3) / 2, Y0 + 18, ch, "ta" if i == pos else "t", 13, "middle", 600, mono=True)
            f.text(x + (CW_ - 3) / 2, Y0 - 6, str(i), "tm", 9, "middle", mono=True)
        if pos >= len(s):
            x = X0 + len(s) * CW_
            f.rect(x, Y0, CW_ - 3, 26, "a", 3, dash=True)
            f.text(x + (CW_ - 3) / 2, Y0 - 6, str(len(s)), "ta", 9, "middle", mono=True)
            f.text(x + CW_ + 2, Y0 + 18, "the end", "ta", 10.5, weight=600)

    def stack(calls, top_note="", gap=None):
        rows = [("jsonParse", 0, 0)] + calls
        y = SY
        for k, (name, start, depth) in enumerate(rows):
            if gap and k == gap[0]:
                y -= SH
                f.text(SX + 85, y + 15, gap[1], "tm", 10, "middle")
            y -= SH
            top = k == len(rows) - 1
            f.rect(SX, y, 170, SH - 4, "a af" if top else "s f", 3)
            f.text(SX + 8, y + 14, name + "()", "ta" if top else "t", 10.5, mono=True, weight=700 if top else None)
            if name != "jsonParse":
                f.text(SX + 162, y + 14, f"at {start}", "tm", 10, "end", mono=True)
            if name == "jsonList":
                f.text(SX + 178, y + 14, f"depth {depth}" + (top_note if top else ""), "ta" if top else "t", 10.5,
                       mono=True, weight=600)
        f.text(SX, SY + 14, "the calls on the C stack, the latest on top", "tm", 10)

    for i, pos, caption in frames:
        with steps.step(f, caption):
            text_cells(DESCENT, pos)
            calls = st[i] if trace[i][0] == "enter" else st[i]
            stack(calls)
    with steps.step(f, "The cap: 65 '[' one inside another. Each level is two more calls on the C stack; "
                       "64 levels read, but the 65th jsonList() makes the depth 65, more than 64, and returns "
                       "NULL, and so does every call under it: no tree, and the message is dropped."):
        for i in range(65):
            x = X0 + i * 8
            on = i == 64
            f.rect(x, Y0, 7, 26, "a af" if on else "s f", 1.5, sw=False)
            f.text(x + 3.5, Y0 + 17, "[", "ta" if on else "t", 9, "middle", mono=True)
        for i in (0, 64):
            f.text(X0 + i * 8 + 3.5, Y0 - 6, str(i), "ta" if i == 64 else "tm", 9, "middle", mono=True)
        f.text(X0 + 65 * 8 + 6, Y0 + 17, "then 65 ]", "tm", 10.5)
        assert [c[:2] for c in before[-4:]] == [("jsonValue", 63), ("jsonList", 63), ("jsonValue", 64),
                                                ("jsonList", 64)] and before[-1][2] == 65, before[-4:]
        stack(before[:2] + before[-4:], top_note=" > 64: NULL", gap=(3, f"... {len(before) - 6} more calls ..."))
    return f


ESCAPES = [('"\\n"', "a newline: one byte"),
           ('"\\u00e9"', "U+00E9, \u00e9: two bytes of UTF-8"),
           ('"\\ud83d\\ude00"', "U+1F600, \U0001F600: a pair of \\u escapes, one character, four bytes"),
           ('"\\ud83d"', "half a pair, alone: U+FFFD, the replacement character \ufffd")]


def escapes0703():
    f = F7("f0703c", "Four strings as they are written in a message and the bytes the reader makes of them: "
           "a newline, an e-acute, an emoji from a pair of escapes, and half a pair alone", 196)
    f.text(24, 22, "the text in the message, and the bytes jsonString() at 07.03 makes of it", "tm", 11)
    W = 140
    for k, (text, what) in enumerate(ESCAPES):
        _, result, hexes = json_run(text)
        assert result == "tree" and hexes, (text, result)
        x = 24 + k * (W + 10)
        f.rect(x, 36, W, 28, "s fs", 4)
        f.text(x + W / 2, 55, text, "t", 11.5, "middle", 600, mono=True)
        f.line(x + W / 2, 68, x + W / 2, 86, "s", arrow=True)
        bw = 26
        bx = x + W / 2 - len(hexes) * (bw + 3) / 2
        for i, h in enumerate(hexes):
            f.rect(bx + i * (bw + 3), 90, bw, 24, "a af", 3)
            f.text(bx + i * (bw + 3) + bw / 2, 106.5, h, "ta", 11, "middle", 700, mono=True)
        notes(f, x, 136, what, 24, "t", 10.5, 14)
    return f


# ------------------------------------------------------------------ 07.04

def notes0704():
    """NOTES.md's measurements for 07.04 (scratch builds that counted wake-ups; the server's log and
    the test's reads of the terminal for the delays), checked word for word."""
    block = notes_section("07.04 Keys and the server at once: poll()")
    text = " ".join(block.split())
    for s in ("53 wakeups at 07.03 (about 10 a second, one per 0.1 s timeout), 2 at 07.04", "Idle for 5 s",
              "counted over the whole run, from kilo's start to the Ctrl-Q that ends it",
              "they are the server's answer to initialize", "the Ctrl-Q that ended the run",
              "none in the 5 idle seconds between",
              "07.03 min 1.4 ms, median 45.5 ms, max 100.3 ms", "07.04 min 0.1 ms, median 0.2 ms, max 0.7 ms",
              "20 runs each"):
        assert s in text, s
    return {"wake": (53, 2, 5), "old": (1.4, 45.5, 100.3), "new": (0.1, 0.2, 0.7), "runs": 20}


def two_ways0704():
    m = notes0704()
    old_med, new_med = m["old"][1] / 1000, m["new"][1] / 1000
    f = F7("f0704a", "One second of kilo with a key and a message from the server: before 07.04 it wakes every "
           "0.1 s to look, and the message waits for the next look; with poll() it sleeps until one of "
           "them comes", 312)
    f.text(24, 22, "the same second twice, a key and then a message; each dot is kilo waking up, the open ones "
           "for the key", "tm", 11)
    X0, X1 = 70, 616
    S = X1 - X0                                   # px for 1 s

    def tx(t):
        return X0 + t * S
    key_t, ticks = 0.25, []
    t = 0.0
    while t < 1.0 - 1e-9:                         # read() times out 0.1 s after it starts, or returns a key
        ticks.append(round(t, 4))
        t = key_t if t < key_t < t + 0.1 else t + 0.1
    seen = next(x for x in ticks if x > 0.6)      # the look the message waits for
    msg_t = round(seen - old_med, 4)

    def axis(y, title, sub):
        f.text(24, y - 50, title, "t", 12, weight=700)
        f.text(24 + figlib.tw(title, 12) * 1.08 + 10, y - 50, sub, "tm", 10.5)
        f.line(X0, y, X1, y, "m")
        for k in range(11):
            f.line(tx(k / 10), y - 3, tx(k / 10), y + 3, "m")
        for k in (0, 5, 10):
            f.text(tx(k / 10), y + 16, f"{k / 10:g} s", "tm", 9.5, "middle")
        f.text(X0 - 8, y + 4, "kilo", "tm", 10, "end")

    def key(y):
        f.line(tx(key_t), y - 22, tx(key_t), y - 6, "s", arrow=True)
        f.text(tx(key_t), y - 26, "a key", "t", 10.5, "middle", 600)

    def message(y, at, seen_at, wait):
        f.line(tx(at), y - 22, tx(at), y - 6, "a", arrow=True)
        f.text(tx(at) - 4, y - 26, "the server's message", "ta", 10.5, "end", 600)
        if wait:
            f.path(f"M{fmt(tx(at))} {y + 8} L{fmt(tx(at))} {y + 12} L{fmt(tx(seen_at))} {y + 12} "
                   f"L{fmt(tx(seen_at))} {y + 8}", "a")

    y1 = 100
    axis(y1, "07.02, 07.03", "read() on the keyboard waits 0.1 s at most; then kilo looks at the server")
    for t in ticks:
        f.circle(tx(t), y1, 3.2, "s fa" if t != key_t else "s f")
    key(y1)
    message(y1, msg_t, seen, True)
    f.text(tx(seen) + 6, y1 + 30, f"seen at the next look: {m['old'][1]} ms later (the median of "
           f"{m['runs']} runs), up to {m['old'][2]:g} ms", "ta", 10.5, "end" if seen > 0.5 else "start")
    f.text(24, y1 + 52, f"idle, it wakes about 10 times a second, with nothing to do: {m['wake'][0]} times in "
           f"a run left idle for {m['wake'][2]} s", "t", 11)

    y2 = 240
    axis(y2, "07.04", "poll() sleeps until the keyboard or the server has something")
    f.circle(tx(key_t), y2, 3.2, "s f")
    f.circle(tx(msg_t + new_med), y2, 3.2, "s fa")
    key(y2)
    message(y2, msg_t, msg_t + new_med, False)
    f.text(tx(msg_t) + 2, y2 + 30, f"seen at once: {m['new'][1]} ms later (the median), up to {m['new'][2]} ms",
           "ta", 10.5, "middle")
    f.text(24, y2 + 52, f"idle, it does not wake: {m['wake'][1]} times in that run, for the server's answer to "
           "initialize and for the Ctrl-Q that ended it", "t", 11)
    return f


POLL_NAMES = {select.POLLIN: "POLLIN", select.POLLOUT: "POLLOUT"}


def poll_set0704():
    cap = capture0704()
    calls = cap["at0704"]
    by_rev = {tuple(ret[1]): (call, ret) for call, ret in calls}
    msg_call, msg_ret = by_rev[(0, select.POLLIN)]
    key_call, key_ret = by_rev[(select.POLLIN, 0)]
    assert msg_call[0] == 2 and msg_call[1] == [(0, select.POLLIN), (5, select.POLLIN)] and msg_call[2] == 0
    assert key_call == msg_call
    q = cap["at0705"]
    k = next(i for i, (call, ret) in enumerate(q) if call[0] == 3 and ret[1][2] == select.POLLOUT)
    qcall, qret = q[k]
    after = q[k + 1][0][2]
    assert qcall[1][2] == (4, select.POLLOUT) and after < qcall[2], (qcall, after)
    wrote = qcall[2] - after
    WHAT = {0: "the keyboard", 5: "the server's output", 4: "the server's input"}

    f = F7("f0704b", "The array kilo gives poll(): the keyboard, the server's output, and the server's input "
           "only while bytes wait to be written; and what comes back in revents", 270)
    f.text(24, 22, "lspWaitKey()'s struct pollfd p[], from a build of 07.04 that logged each poll()", "tm", 11)
    COLS_ = [(24, "p[i]"), (70, "fd"), (106, "what it is"), (276, "events"), (372, "revents")]
    Y0, RH = 58, 34
    for x, h in COLS_:
        f.text(x, Y0 - 10, h, "tm", 10.5)

    def table(call, ret, n_note=""):
        n, ents, queue = call
        for i in range(3):
            y = Y0 + i * RH
            if i < n:
                fd, ev = ents[i]
                rev = ret[1][i] if ret else None
                hot = bool(rev)
                f.rect(24, y, 440, RH - 8, "a af" if hot else "s f", 4)
                f.text(32, y + 17, f"p[{i}]", "t", 11, mono=True)
                f.text(70, y + 17, str(fd), "t", 12, weight=700, mono=True)
                f.text(106, y + 17, WHAT[fd], "t", 11)
                f.text(276, y + 17, POLL_NAMES[ev], "t", 11, mono=True)
                f.text(372, y + 17, "-" if rev is None else (POLL_NAMES[rev] if rev else "0"),
                       "ta" if hot else "tm", 11, mono=True, weight=700 if hot else None)
            else:
                f.rect(24, y, 440, RH - 8, "m f", 4, dash=True)
                f.text(32, y + 17, "p[2]", "tm", 11, mono=True)
                f.text(70, y + 17, "4", "tm", 12, mono=True)
                f.text(106, y + 17, "the server's input: not asked, nothing waits", "tm", 11)
        f.text(484, Y0 + 10, f"n = {n}", "t", 12, weight=700, mono=True)
        f.text(484, Y0 + 30, "entries", "tm", 10.5)
        # the queue of bytes waiting to be written to the server
        f.text(484, Y0 + 62, "L.tx", "t", 11, weight=700, mono=True)
        f.text(484, Y0 + 78, f"{queue} bytes", "ta" if queue else "tm", 11, mono=True, weight=700 if queue else None)
        f.text(484, Y0 + 92, "waiting", "tm", 10.5)

    with steps.step(f, "Idle: two entries, the keyboard (fd 0) and the server's output (fd 5), both POLLIN. "
                       "Nothing waits to be written, so fd 4 is not in the array. poll() sleeps, no timeout."):
        table(msg_call, None)
        f.text(24, 186, "poll(p, 2, -1): asleep until one of them has something", "t", 11.5, weight=600)
    with steps.step(f, "A key: poll() returns 1, p[0].revents POLLIN. lspPump() looks after the server, and "
                       "lspWaitKey() returns: editorReadKey() reads the key at once."):
        table(key_call, key_ret)
        f.text(24, 186, f"poll() returns {key_ret[0]}: the keyboard has a byte", "t", 11.5, weight=600)
    with steps.step(f, "The server's message: p[1].revents POLLIN. lspPump() reads it and acts on it, here "
                       "the answer to initialize (\"lsp: scripted 1.0 ready\"), draws, and kilo polls again."):
        table(msg_call, msg_ret)
        f.text(24, 186, f"poll() returns {msg_ret[0]}: the server wrote; lspPump() reads it, then poll() again",
               "t", 11.5, weight=600)
    with steps.step(f, f"Bytes waiting (at 07.05: a {cap['didopen']}-byte didOpen, more than the pipe holds, "
                       f"to a server that has not read yet): p[2] asks fd 4 for POLLOUT. It comes: lspFlush() "
                       f"writes {wrote} bytes, and {after} still wait."):
        table(qcall, qret)
        f.text(484, Y0 + 110, f"then {after}", "ta", 11, mono=True)
        f.text(24, 186, f"poll() returns {qret[0]}: the pipe to the server has room; lspFlush() writes {wrote} "
               "bytes", "t", 11.5, weight=600)
        f.text(24, 204, f"at 07.05, a {cap['didopen']}-byte didOpen to a server that waits a second before it "
               "reads", "tm", 10.5)
    f.text(24, 252, f"POLLIN ({select.POLLIN}): something to read; POLLOUT ({select.POLLOUT}): room to write. "
           "revents is set by poll() when it returns.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 07.05

def session0705():
    cap = capture0705()
    frames, keys = cap["frames"], cap["keys"]
    t0 = frames[0]["t"]
    names = [(e["dir"], what(e)) for e in frames]
    assert names == [(">", "initialize"), ("<", "reply 1"), (">", "initialized"), (">", "textDocument/didOpen"),
                     ("<", "textDocument/publishDiagnostics"), (">", "textDocument/didChange"),
                     ("<", "textDocument/publishDiagnostics"), ("<", "textDocument/publishDiagnostics"),
                     (">", "shutdown"), ("<", "reply 2"), (">", "exit")], names
    assert cap["row"] == TYPED and cap["quits"] == 4
    pid = frames[0]["msg"]["params"]["processId"]
    f = F7("f0705a", "kilo at 07.05 and clangd, every message of a session: the handshake, the file opened, one "
           "didChange for nine keys, and shutdown and exit at Ctrl-Q; the size of each body", 412)
    f.text(24, 22, "kilo at 07.05 and clangd 21 on sum.c, through a relay that logged every message", "tm", 11)
    KX, SX = 200, 520
    top, bottom = 52, 392
    f.text(KX, top - 8, "kilo", "t", 12.5, "middle", 700)
    f.text(SX, top - 8, "clangd", "t", 12.5, "middle", 700)
    f.text(24, top - 8, "s", "tm", 10)
    for x in (KX, SX):
        f.line(x, top, x, bottom, "m")
    y = top + 18
    gaps = {5: f"the nine keys \"{TYPED}\" typed on row 3", 8: "Ctrl-Q, four times: the file is modified"}

    def label(e):
        m = e["msg"]
        w = what(e)
        if w == "initialize":
            return f"initialize, id 1 (processId {pid})"
        if w.startswith("reply"):
            return f"the answer to id {m['id']}" + (", result null" if m.get("result", 0) is None else "")
        if w in ("textDocument/didOpen", "textDocument/didChange"):
            return f"{w.split('/')[1]}, version {m['params']['textDocument']['version']}"
        if w == "textDocument/publishDiagnostics":
            return "publishDiagnostics (kilo reads these at 07.06)"
        return w
    for i, e in enumerate(frames):
        if i in gaps:
            f.text((KX + SX) / 2, y + 2, gaps[i], "tm", 10.5, "middle")
            y += 24
        right = e["dir"] == ">"
        muted = what(e) == "textDocument/publishDiagnostics"
        a, b = (KX + 2, SX - 3) if right else (SX - 2, KX + 3)
        f.line(a, y, b, y, "m" if muted else "s", arrow=True, dash=muted)
        f.text((KX + SX) / 2, y - 5, label(e), "tm" if muted else "t", 10.5, "middle")
        f.text(SX + 12 if right else KX - 12, y + 4, f"{e['len']} bytes", "tm" if muted else "ta", 10.5,
               "start" if right else "end", 600 if not muted else None, mono=True)
        f.text(24, y + 4, f"{e['t'] - t0:.3f}", "tm", 9.5, mono=True)
        y += 26
    assert y <= bottom + 20, y
    last = max(keys)
    change = next(e for e in frames if what(e) == "textDocument/didChange")
    f.text(24, 404, f"times from kilo's first message; the didChange left {1000 * (change['t'] - last):.0f} ms "
           "after the last of the nine keys", "tm", 10.5)
    return f


def pause0705():
    cap = capture0705()
    keys = cap["keys"]
    changes = [e for e in cap["frames"] if what(e) == "textDocument/didChange"]
    assert len(changes) == 1 and len(keys) == len(TYPED)
    ch = changes[0]
    t0 = keys[0]
    ms = [1000 * (k - t0) for k in keys]
    cms = 1000 * (ch["t"] - t0)
    after = cms - ms[-1]
    f = F7("f0705b", f"Nine keys typed quickly, and the 300 ms pause that starts again at each: one didChange, "
           f"{after:.0f} ms after the last key", 300)
    f.text(24, 22, f"\"{TYPED}\" typed on row 3 of sum.c, kilo at 07.05 and clangd; ms from the first key",
           "tm", 11)
    X0, PX = 60, 0.8                                   # x of 0 ms, px per ms
    end = 700

    def tx(t):
        return X0 + t * PX
    ay = 236
    f.line(X0, ay, tx(end), ay, "m")
    for t in range(0, end + 1, 100):
        f.line(tx(t), ay - 3, tx(t), ay + 3, "m")
        f.text(tx(t), ay + 17, str(t), "tm", 9.5, "middle", mono=True)
    f.text(tx(end) + 6, ay + 4, "ms", "tm", 9.5)
    # the keys, and the pause each starts
    ky, by = 58, 84
    for i, (t, k) in enumerate(zip(ms, TYPED)):
        f.rect(tx(t) - 7, ky - 13, 14, 17, "s f", 3)
        if k == " ":
            f.path(f"M{fmt(tx(t) - 3.5)} {ky - 4} L{fmt(tx(t) - 3.5)} {ky - 1} L{fmt(tx(t) + 3.5)} {ky - 1} "
                   f"L{fmt(tx(t) + 3.5)} {ky - 4}", "s")
        else:
            f.text(tx(t), ky, k, "t", 11, "middle", 600, mono=True)
        y = by + i * 12
        stop = ms[i + 1] if i + 1 < len(ms) else t + 300
        last_ = i + 1 == len(ms)
        f.line(tx(t), ky + 6, tx(t), y - 3, "m")
        f.rect(tx(t), y - 3, (stop - t) * PX, 6, "a af" if last_ else "m fs", 2)
        if not last_:
            f.line(tx(stop), y - 5, tx(stop), y + 5, "s")
    f.text(tx(ms[-1]) + 300 * PX / 2, by + 8 * 12 - 8, "300 ms with no key", "ta", 10.5, "middle", 600)
    f.text(tx(ms[3]), by + 9 * 12 + 14, "each key starts the 300 ms again", "tm", 10.5)
    # the one message
    f.line(tx(cms), by + 8 * 12 + 4, tx(cms), ay - 6, "a", arrow=True)
    f.text(tx(cms) - 6, 196, f"didChange, version {ch['msg']['params']['textDocument']['version']}, "
           f"{ch['len']} bytes", "ta", 11, "end", 700)
    f.text(tx(cms) - 6, 211, f"{after:.0f} ms after the last key: the whole text", "ta", 10.5, "end")
    f.text(24, 286, f"{len(keys)} keys, 1 message", "t", 14, weight=700)
    f.text(160, 286, f"the keys came {ms[-1] / (len(ms) - 1):.0f} ms apart on average", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 07.06

def diag_lines(m, tmp, cut0=27, cut1=21):
    """clangd's publishDiagnostics m as lines of text, trimmed (its two messages cut short), in the
    order clangd wrote its members: [(text, which range it shows or None)]."""
    p = m["params"]
    assert list(p) == ["diagnostics", "uri", "version"], list(p)
    d0, d1 = p["diagnostics"]
    assert list(d0) == ["code", "message", "range", "severity", "source"] and list(d1) == ["message", "range", "severity"]

    def rng(d, k):
        r = d["range"]
        assert list(r) == ["end", "start"]
        e, s = r["end"], r["start"]
        return [(f'   "range":{{"end":{{"character":{e["character"]},"line":{e["line"]}}},', k),
                (f'    "start":{{"character":{s["character"]},"line":{s["line"]}}}}},', k)]
    return ([('{"jsonrpc":"2.0",', None),
             (f' "method":"{m["method"]}",', None),
             (' "params":{"diagnostics":[', None),
             (f'  {{"code":"{d0["code"]}",', None),
             (f'   "message":"{d0["message"][:cut0]}...",', None)]
            + rng(d0, 0)
            + [(f'   "severity":{d0["severity"]},"source":"{d0["source"]}"}},', None),
               (f'  {{"message":"{d1["message"][:cut1]}...",', None)]
            + rng(d1, 1)
            + [(f'   "severity":{d1["severity"]}}}],', None),
               (f'  "uri":"{trim_uri(p["uri"], tmp)}",', None),
               (f'  "version":{p["version"]}}}}}', None)])


def screen0706():
    cap = capture0706()
    shot = cap["shot"]
    diags = [e for e in cap["frames"] if what(e) == "textDocument/publishDiagnostics" and
             e["msg"]["params"]["diagnostics"]]
    e = diags[-1]
    d0 = e["msg"]["params"]["diagnostics"][0]
    s, en = d0["range"]["start"], d0["range"]["end"]
    row = SUM_C.split("\n")[s["line"]].replace("total);", "totl);")         # the row with the a deleted
    assert row[s["character"]:en["character"]] == "totl"
    render_col = len(row[:s["character"]].replace("\t", " " * 8))
    assert shot.unders[s["line"]][render_col:render_col + en["character"] - s["character"]] == "____", shot.unders
    assert shot.lines[-1].startswith(f"{s['line'] + 1}: error: {d0['message'][:20]}"), shot.lines[-1]
    f = F7("f0706a", f"kilo at 07.06 after the a of total is deleted: totl underlined on row {s['line'] + 1}, the "
           f"error on the message line, and the list from clangd that put them there, {e['len']} bytes", 300)
    f.text(24, 22, "kilo at 07.06, a terminal 10 x 60, and clangd's publishDiagnostics (trimmed)", "tm", 11)
    cw, rh, x, y = 5.3, 14, 30, 42
    base = screen(f, x, y, shot, cw, rh, 60, cursor=True)
    lines = diag_lines(e["msg"], cap["tmp"], cut0=28)
    jx, jy, jl = 370, 44, 13.2
    yr = None
    for k, (text, which) in enumerate(lines):
        yy = jy + k * jl
        mono(f, jx, yy, text, "ta" if which == 0 else ("tm" if which == 1 else "t"), 9,
             weight=700 if which == 0 else None)
        if which == 0 and yr is None:
            yr = yy
    # from the range to the underline it makes
    r = s["line"]
    ux0, ux1 = x + render_col * cw, x + (render_col + 4) * cw
    uy = base[r] + 2.5
    f.path(f"M{fmt(jx - 4)} {fmt(yr + 6)} C{fmt(jx - 70)} {fmt(yr + 50)}, {fmt(ux1 + 50)} {fmt(uy + 26)}, "
           f"{fmt((ux0 + ux1) / 2)} {fmt(uy + 4)}", "a", arrow=True)
    f.text(x + 30 * cw + 6, uy - 2.5, "underlined", "ta", 10.5, weight=700)
    by = 238
    notes(f, 24, by, f"Lines and characters count from 0: line {r} is the screen's row {r + 1}, and characters "
          f"{s['character']} to {en['character']} are bytes of the row, the tab one of them, so totl starts in "
          f"column {render_col} on the screen. The second diagnostic, a note of severity 3 on line "
          f"{e['msg']['params']['diagnostics'][1]['range']['start']['line']}, underlines total.", 112, "tm", 10.5)
    return f


def columns0706():
    u8 = capture0706columns(False)
    u16 = capture0706columns(True)
    assert u8["encoding"] == "utf-8" and u8["offered"] == ["utf-8", "utf-16"]
    assert u16["encoding"] == "utf-16" and u16["offered"] == ["utf-16"]
    chars = SUM_ETE.split("\n")[5]
    assert u8["range"]["start"]["line"] == u16["range"]["start"]["line"] == 5
    b0, b1 = u8["range"]["start"]["character"], u8["range"]["end"]["character"]
    w0, w1 = u16["range"]["start"]["character"], u16["range"]["end"]["character"]
    raw = chars.encode()
    assert raw[b0:b1] == b"totl" and len(chars[:chars.index("totl")].encode("utf-16-le")) // 2 == w0
    cells = u8["under"]
    m = re.search(rb"\r\x1b\[(\d+)C\x1b\[4mtotl\x1b\[0m", u8["raw"])
    assert m and int(m.group(1)) == cells[0] and u16["under"] == cells, (m, cells)
    # per character: its bytes, utf-16 units, render columns (a tab to the next multiple of 8)
    per, rc, bc, wc = [], 0, 0, 0
    for ch in chars:
        nb = len(ch.encode())
        nw = len(ch.encode("utf-16-le")) // 2
        nr = 8 - rc % 8 if ch == "\t" else nb
        per.append((ch, bc, nb, wc, nw, rc, nr))
        bc, wc, rc = bc + nb, wc + nw, rc + nr
    r0 = next(r for ch, b, nb, w, nw, r, nr in per if b == b0)
    f = F7("f0706b", "One line with two e-acutes, counted three ways: the bytes kilo keeps, the UTF-16 units of "
           "the protocol's default, and the columns of render; where totl starts in each", 268)
    f.text(24, 22, "row 6 of sum.c with \u00e9t\u00e9 in it; clangd's error range for totl, and where kilo draws it",
           "tm", 11)
    U, X0 = 15.5, 62
    xs, x = [], X0
    for ch, b, nb, w, nw, r, nr in per:
        wd = max(nr, nb) * U
        xs.append((x, wd))
        x += wd
    y0 = 52
    for (ch, b, nb, w, nw, r, nr), (x, wd) in zip(per, xs):
        hot = b0 <= b < b1
        f.rect(x + 1, y0, wd - 2, 24, "a af" if hot else "s fs", 3)
        label = "tab" if ch == "\t" else ch
        f.text(x + wd / 2, y0 + 16.5, label, "ta" if hot else "t", 11 if ch == "\t" else 12.5, "middle",
               600, mono=ch != "\t")

    def ruler(y, title, sub, units, mark, unit_of):
        f.text(24, y - 8, title, "t", 11, weight=700)
        f.text(24 + figlib.tw(title, 11) * 1.1 + 8, y - 8, sub, "tm", 10)
        for (ch, b, nb, w, nw, r, nr), (x, wd) in zip(per, xs):
            n, start = unit_of(ch, b, nb, w, nw, r, nr)
            cw_ = wd / n
            for j in range(n):
                k = start + j
                hot = mark[0] <= k < mark[1]
                f.rect(x + j * cw_ + 0.75, y, cw_ - 1.5, 17, "a af" if hot else "m f", 2)
                if hot or k % 5 == 0 or k == mark[0]:
                    f.text(x + j * cw_ + cw_ / 2, y + 12, str(k), "ta" if hot else "tm", 8.5, "middle",
                           700 if k == mark[0] else None, mono=True)
        f.text(X0 - 8, y + 12, units, "tm", 9.5, "end")
    ruler(108, "bytes of the row", f"what kilo keeps; clangd's characters with utf-8: {b0} to {b1}", "byte",
          (b0, b1), lambda ch, b, nb, w, nw, r, nr: (nb, b))
    ruler(152, "UTF-16 units", f"clangd's characters when kilo does not offer utf-8: {w0} to {w1}", "unit",
          (w0, w1), lambda ch, b, nb, w, nw, r, nr: (nw, w))
    ruler(196, "columns of render", f"the tab to the next multiple of 8: {r0} to {r0 + 4}", "column",
          (r0, r0 + 4), lambda ch, b, nb, w, nw, r, nr: (nr, r))
    f.text(24, 238, f"The terminal draws each \u00e9 in one cell: totl is in cells {cells[0]} to {cells[-1]}, so "
           f"kilo moves there with ESC [ {cells[0]} C, not {r0},", "t", 10.5)
    f.text(24, 254, "and underlines the same four cells whichever count clangd used (a terminal 10 x 60 "
           "that knows UTF-8).", "t", 10.5)
    return f


def drawn_over0706():
    cap = capture0706()
    shot = cap["shot"]
    raw = cap["raw"]
    row = shot.lines[5]
    i = raw.rfind(row.encode() + b"\x1b[0K")
    assert i > 0
    j = raw.index(b"\r\n", i + len(row)) + 2
    data = raw[i:j].decode()
    m = re.fullmatch(r"(.*)\x1b\[0K\r\x1b\[(\d+)C\x1b\[4m(\w+)\x1b\[0m\r\n", data)
    assert m and m.group(1) == row and m.group(3) == "totl", data
    n = int(m.group(2))
    assert shot.unders[5][n:n + 4] == "____" and "_" not in shot.unders[5][:n] + shot.unders[5][n + 4:]
    f = F7("f0706c", f"The bytes kilo at 07.06 writes for the error's row: the row as always, then back to its "
           f"start, {n} cells right, underline on, totl again, underline off", 296)
    f.text(24, 22, "the frame's bytes for row 6, from what kilo wrote to the terminal", "tm", 11)
    size = 11
    cw = cwid(size)
    x, y = 24, 56
    toks = [(row, "t", 1), ("ESC[0K", "ta", 1), ("\\r", "a", 2), (f"ESC[{n}C", "a", 2), ("ESC[4m", "a", 2),
            ("totl", "a", 2), ("ESC[0m", "a", 2), ("\\r\\n", "tm", 3)]
    spans = {}
    for s_, cls, part in toks:
        x0 = x
        if s_ == row:
            lead = len(s_) - len(s_.lstrip(" "))
            for k in range(lead):
                cx = x + k * cw + cw * 0.18
                f.path(f"M{fmt(cx)} {fmt(y - 2.5)} L{fmt(cx)} {y} L{fmt(cx + cw * 0.64)} {y} L{fmt(cx + cw * 0.64)} "
                       f"{fmt(y - 2.5)}", "m")
            x = mono(f, x + lead * cw, y, s_[lead:], "t", size)
        else:
            tcls = {"t": "t", "ta": "ta", "a": "ta", "tm": "tm"}[cls]
            x = mono(f, x, y, s_, tcls, size, weight=700 if cls == "a" else None)
        spans.setdefault(part, [x0, x])[1] = x
        x += 5
    a, b = spans[1]
    f.brace_h(a, b - 2, y + 10)
    f.text(a, y + 28, "first pass: the row, and erase to its end", "t", 10.5)
    a, b = spans[2]
    f.brace_h(a, b, y + 10, "a")
    f.text(a, y + 28, "second pass: over the same cells", "ta", 10.5, weight=600)
    # what the terminal does with them: the row, the cursor's way back, the underline
    cw2, rh = 9.0, 22
    tx, ty = 34, 132
    for k in (0, 8, 16, n, 32):
        f.text(tx + k * cw2 + cw2 / 2, ty - 8, str(k), "ta" if k == n else "tm", 9, "middle",
               700 if k == n else None, mono=True)
    for k, (label, under) in enumerate((("after the first pass", False), ("after the second: totl underlined", True))):
        yy = ty + k * 56
        f.rect(tx - 6, yy, 33 * cw2 + 12, rh, "s fs", 4)
        mono(f, tx, yy + 15.5, row, "t", 15)
        f.text(tx + 33 * cw2 + 16, yy + 15.5, label, "ta" if under else "tm", 10.5, weight=600 if under else None)
        if under:
            f.line(tx + n * cw2 + 0.5, yy + 18.5, tx + (n + 4) * cw2 - 0.5, yy + 18.5, "s")
    # the cursor's way: \r to column 0, then ESC [ n C
    ay = ty + 36
    f.path(f"M{fmt(tx + 29 * cw2)} {ay} L{fmt(tx)} {ay}", "a", arrow=True)
    f.text(tx + 30 * cw2, ay + 4, "\\r", "ta", 10.5, weight=700, mono=True)
    f.path(f"M{fmt(tx)} {ay + 8} L{fmt(tx + n * cw2)} {ay + 8}", "a", arrow=True)
    f.text(tx + n * cw2 + 6, ay + 12, f"ESC[{n}C", "ta", 10.5, weight=700, mono=True)
    f.text(24, 268, "The row's own drawing is not touched: the underline is drawn over it. In the finished "
           "project, with module 06,", "tm", 10.5)
    f.text(24, 283, "the string is coloured by the first pass and totl drawn again in the default colour.",
           "tm", 10.5)
    return f


# ------------------------------------------------------------------ 07.07

def trimmed_frames(st, tmp):
    """The frames of a step, each as (direction, short text)."""
    out = []
    for e in st["frames"]:
        m = e["msg"]
        w = what(e)
        if w == "textDocument/definition":
            p = m["params"]["position"]
            out.append((">", f'definition, id {m["id"]}: "position":{{"line":{p["line"]},"character":{p["character"]}}}'))
        elif w.startswith("reply"):
            r = m["result"]
            if r:
                loc = r[0]
                rg = loc["range"]
                assert list(loc) == ["range", "uri"] and list(rg) == ["end", "start"]
                out.append(("<", f'the answer to id {m["id"]}: [{{"range":{{"end":{{"character":{rg["end"]["character"]},'
                                 f'"line":{rg["end"]["line"]}}},'))
                out.append(("", f'  "start":{{"character":{rg["start"]["character"]},"line":{rg["start"]["line"]}}}}},'))
                out.append(("", f'  "uri":"{trim_uri(loc["uri"], tmp)}"}}]'))
            else:
                out.append(("<", f'the answer to id {m["id"]}: {json.dumps(r)}'))
        elif w in ("textDocument/didClose", "textDocument/didOpen", "textDocument/didChange"):
            td = m["params"]["textDocument"]
            v = f", version {td['version']}" if "version" in td else ""
            out.append((">", f'{w.split("/")[1]} {trim_uri(td["uri"], tmp).rsplit("/", 1)[1]}{v}'))
    return out


def jump0707():
    cap = capture0707()
    tmp = cap["tmp"]
    st = {s_["name"]: s_ for s_ in cap["steps"]}
    tot, add, back, uns = st["total"], st["add"], st["back"], st["unsaved"]
    assert tot["after"].cursor == (4, 12) and add["after"].cursor == (1, 18) and back["after"].cursor == (4, 21)
    assert add["after"].lines[-2].startswith("sam ple/add.h") and uns["after"].lines[-1].startswith("Unsaved changes")
    req = [e for e in tot["frames"] if what(e) == "textDocument/definition"][0]["msg"]["params"]["position"]
    f = F7("f0707a", "Ctrl-G on total, Ctrl-G on add, Ctrl-B, and Ctrl-G with a change unsaved, in kilo at 07.07 "
           "with clangd: the screen after each, and the messages it sent and got", 344)
    f.text(24, 22, "kilo at 07.07 on sam ple/sum.c, a terminal 10 x 64, and clangd; the uris cut short", "tm", 11)
    cw, rh, x, y = 5.4, 14.5, 30, 42

    def frame(s_, title, sub, ghost=None):
        screen(f, x, y, s_["after"], cw, rh, 64, ghost=ghost)
        f.text(398, 50, title, "t", 12.5, weight=700)
        notes(f, 398, 68, sub, 36, "tm", 10.5, 14)
        fy = 212
        for d, text in trimmed_frames(s_, tmp):
            if d:
                f.text(24, fy, "kilo >" if d == ">" else "clangd <", "ta" if d == ">" else "t", 10, weight=700)
            mono(f, 84, fy, text, "t", 9.6)
            fy += 15
    with steps.step(f, f"Ctrl-G with the cursor on total in the printf line: kilo asks for line {req['line']}, "
                       f"character {req['character']}. The answer is in this file, line 4, character 5: the cursor "
                       "moves to int total."):
        frame(tot, "Ctrl-G on total", "The answer is the same file: the cursor moves (the dashed box is where "
              "it was).", ghost=tot["at"].cursor)
    with steps.step(f, "Nine Rights, and Ctrl-G on add: the answer is add.h, line 1, character 18. kilo reads add.h "
                       "in place of sum.c, and tells clangd: didClose sum.c, didOpen add.h."):
        frame(add, "Ctrl-G on add", "The answer is another file: kilo reads add.h in place of sum.c.")
    with steps.step(f, "Ctrl-B: back to where the jump came from, sum.c with the cursor on add again. No question "
                       "for clangd, only didClose add.h and didOpen sum.c."):
        frame(back, "Ctrl-B", "Back where the last jump came from: no question, two notifications.")
    with steps.step(f, "Left, a space before add, not saved, then Ctrl-G on add: the change goes first, then the "
                       "question; the answer is add.h again, but kilo will not read it over unsaved changes."):
        frame(uns, "Ctrl-G, unsaved", "A change not saved: sum.c stays, and the message line says why.")
    return f


def uri0707():
    cap = capture0707()
    tmp = cap["tmp"]
    st = {s_["name"]: s_ for s_ in cap["steps"]}
    reply = next(e for e in st["add"]["frames"] if what(e).startswith("reply"))
    uri = reply["msg"]["result"][0]["uri"]
    path = urllib.parse.unquote(uri[len("file://"):])
    assert uri.startswith("file:///") and path == os.path.join(tmp, DIR, "add.h"), (uri, path)
    none = st["none"]
    nreply = next(e for e in none["frames"] if what(e).startswith("reply"))
    tot = st["total"]
    f = F7("f0707b", "The uri clangd answers with and the path kilo makes of it, %20 a space; then what kilo "
           "does with the answer: nothing found, the same file, or another file, unless changes are unsaved", 346)
    f.text(24, 22, "the uri in clangd's answer to Ctrl-G on add (the directory above sam ple cut short)", "tm", 11)
    tu = trim_uri(uri, tmp)
    tp = trim_uri(path, tmp)
    size = 13
    cw = cwid(size)
    x, y = 40, 56
    a = tu.index("%20")
    f.text(x, y, f'"{tu[:a]}', "t", size, mono=True)
    f.text(x + (a + 1) * cw, y, "%20", "ta", size, weight=700, mono=True)
    f.text(x + (a + 4) * cw, y, f'{tu[a + 3:]}"', "t", size, mono=True)
    f.line(x + (a + 2.5) * cw, y + 6, x + (a + 2.5) * cw, y + 26, "a", arrow=True)
    f.text(x + (a + 2.5) * cw + 8, y + 21, "lspPath(): \"file://\" off, and each % and two hex digits one byte: "
           "0x20, a space", "tm", 10.5)
    y2 = y + 46
    f.text(x, y2, f'"{tp[:a - 7]}', "t", size, mono=True)
    f.rect(x + (a - 6) * cw, y2 - 12, cw, 16, "a af", 2)
    f.text(x + (a - 5) * cw, y2, f'{tp[a - 6:]}"', "t", size, mono=True)
    # the decision: a chain of questions down the left, what kilo does on the right
    assert none["after"].lines[-1] == "lsp: no definition found"
    said = st["unsaved"]["after"].lines[-1]
    assert said == "Unsaved changes: save first (Ctrl-S), then try again"
    f.text(24, 140, "then what kilo does with the answer", "tm", 10.5)
    QX, QW, OX, OW, BH = 24, 200, 290, 326, 36
    rows = [
        ("a uri and a line?", "lspDefinitionResult()", "no", "lsp: no definition found",
         f"Ctrl-G on the empty row 3: the answer is {json.dumps(nreply['msg']['result'])}", True),
        ("the file that is open?", "lspSameFile()", "yes", "move the cursor there",
         f"Ctrl-G on total: to row {tot['after'].cursor[0] + 1}, column {tot['after'].cursor[1] + 1}", False),
        ("changes not saved?", "editorJump()", "yes", said[:said.index(" (")],
         said[said.index(" (") + 1:], True),
        (None, None, None, "read it in place of this one", "didClose the old file, didOpen the new: add.h", False),
    ]
    for k, (q, qsub, ans, out, osub, msg) in enumerate(rows):
        y = 150 + k * 50
        if q:
            f.rect(QX, y, QW, BH, "s fs", 6)
            f.text(QX + 10, y + 15, q, "t", 11, weight=700)
            f.text(QX + 10, y + 29, qsub, "tm", 9.5, mono=True)
            f.line(QX + QW + 2, y + BH / 2, OX - 3, y + BH / 2, "s", arrow=True)
            f.text((QX + QW + OX) / 2, y + BH / 2 - 5, ans, "tm", 10, "middle")
            # the other answer: down to the next question, or to the last outcome
            f.line(QX + 40, y + BH + 2, QX + 40, y + 48, "s", arrow=True)
            f.text(QX + 46, y + BH + 11, {"no": "yes", "yes": "no"}[ans], "tm", 10)
            ox = OX
        else:
            ox = QX
        w = OX + OW - ox
        f.rect(ox, y, w, BH, "a af" if msg else "s f", 6)
        f.text(ox + 10, y + 15, out, "ta" if msg else "t", 10.5 if msg else 11, weight=700, mono=msg)
        f.text(ox + 10, y + 29, osub, "ta" if msg else "tm", 9.5, mono=msg and k == 2)
    return f


FIGS = [
    ("07.01-fork-exec", fork_exec0701, True),
    ("07.01-exec-fails", exec_fails0701, False),
    ("07.02-frame", frame0702, False),
    ("07.02-split-reads", split_reads0702, True),
    ("07.03-tree", tree0703, False),
    ("07.03-descent", descent0703, True),
    ("07.03-escapes", escapes0703, False),
    ("07.04-two-ways", two_ways0704, False),
    ("07.04-poll-set", poll_set0704, True),
    ("07.05-session", session0705, False),
    ("07.05-pause", pause0705, False),
    ("07.06-screen", screen0706, False),
    ("07.06-columns", columns0706, False),
    ("07.06-drawn-over", drawn_over0706, False),
    ("07.07-jump", jump0707, True),
    ("07.07-uri", uri0707, False),
]


def cleanup():
    """Remove the projects built for the captures."""
    for d in {os.path.dirname(p) for p in _built.values()}:
        shutil.rmtree(d, ignore_errors=True)
    _built.clear()


def main():
    check_sample()
    only = sys.argv[1:]
    try:
        for name, fn, stepped in FIGS:
            if only and not any(name.startswith(o) for o in only):
                continue
            try:
                fig = fn()
            except SystemExit as e:              # clangd missing: say which figure, go on with the rest
                print(f"{name} not made: {e}")
                continue
            text = fig.svg()
            if stepped:
                print(name, "steps:", steps.check(text))
            print(write(MOD, name, fig))
    finally:
        cleanup()


if __name__ == "__main__":
    main()
