"""Figures for lang lessons 01.05 to 01.08 (plans/lang-01-lessons.md, the "Figures:" of each lesson).

    python3 -B art/lang/figs_0105_0108.py [name-prefix ...]
                writes tracks/lang/lessons/01-introduction/figures/01.0N-*.svg

Every figure is drawn from the project as the site shows it at its lesson: ./learn files lang --at
NN.LL into a temporary directory, built there with make -s (project()), and its own programs run on
it. What a figure draws is asserted against what they print, so a change to the code stops this
script instead of leaving a figure that no longer tells the truth. Nothing is written into tracks/lang
but the figures; the temporary directory goes when the script ends.

  01.05-prompt            stepped: ./mote0 at 01.05 with no file, the session x := 6 / while x > 4 do /
                          x := x - 1 / end / write x typed into it. Its stdout (the prompts and the 4)
                          is split by line; a scratch copy whose prompt() and set() also report on
                          stderr (patched()) gives, after each line, the depth, the lines run and the
                          names; its stdout must be the real one
  01.05-agree             ./agree at 01.05 (two ways, every row ok) and at 01.09, 01.10 and 01.11 (the
                          lesson each later way first appears in); the expected outputs are the .out
                          files of programs/
  01.06-phases            main.c at 01.11 (the options and the order of the calls), and the lesson
                          each phase's file first appears in (./learn files at 01.05 to 01.11);
                          --tokens works at 01.06 and --parse-tree is still a usage error there
  01.06-scan              stepped: --tokens of gcd.mote at 01.06, the five tokens of its line 4, the
                          first token of line 5; the operator table of scan.c, longest first
  01.06-chars-to-tokens   gcd.mote at 01.06, its tokens drawn over its text from --tokens (each
                          token's text checked against the characters at its line and column), and
                          the two counts, 170 characters and 29 tokens
  01.07-rule-and-function the while rule from parse.c's header comment and the lines of stmt() that
                          take it, each checked against parse.c at 01.07
  01.07-tree              --parse-tree at 01.07 of a file holding i := i - j: program, one stmt, and
                          under it 6 rule nodes and 5 leaves; the same subtree is in gcd.mote's
  01.07-descent           stepped: a scratch copy of 01.07 whose rule functions and take() report
                          each call, return and token taken; --parse-tree of write i - j; the tree
                          the trace builds must be the one the real parser prints
  01.08-two-trees         the parse tree of i := i - j as in 01.07-tree (from gcd.mote), and
                          --tree and --symbols of gcd.mote at 01.08: := i#1 (- i#1 j#2), entries 1
                          and 2
  01.08-gcd-tree          --tree and --symbols of gcd.mote at 01.08, the whole tree
  01.08-static            --tree at 01.08 on three small programs (two accepted, one refused at
                          2:11), and ./mote at 01.09 on the third, which stops at 4:7

The drawing primitives (Fig, sane, the steps module) are the cc track's, art/cc/figlib.py, loaded
under a module name of its own as art/lang/archmap.py does; every other helper is in this file.
"""
import atexit
import functools
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("cc_figlib", os.path.join(ROOT, "art", "cc", "figlib.py"))
_cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cc)
Fig, sane, tw, steps = _cc.Fig, _cc.sane, _cc.tw, _cc.steps

OUT = os.path.join(ROOT, "tracks", "lang", "lessons", "01-introduction", "figures")
LEARN = os.path.join(ROOT, "learn")
W = 640
CW = 0.6                       # the monospace advance, in em (Geist Mono)


def mw(s, size):
    """The width of s in monospace at font size `size`."""
    return len(s) * size * CW


# ------------------------------------------------------------------ the project at a lesson

_TMP = []


def _tmp():
    if not _TMP:
        d = tempfile.mkdtemp(prefix="lang-art-")
        atexit.register(shutil.rmtree, d, True)
        _TMP.append(d)
    return _TMP[0]


def _make(d):
    r = subprocess.run(["make", "-s"], cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"art/lang: make failed in {d}:\n{r.stdout}{r.stderr}")


@functools.lru_cache(None)
def files(at):
    """The project's files at lesson `at`, as ./learn files writes them (not built)."""
    d = os.path.join(_tmp(), "files-" + at)
    subprocess.run([LEARN, "files", "lang", "--at", at, d], check=True, stdout=subprocess.DEVNULL)
    return d


@functools.lru_cache(None)
def project(at):
    """The project as the site shows it at lesson `at`, built."""
    d = os.path.join(_tmp(), at)
    shutil.copytree(files(at), d)
    _make(d)
    return d


def patched(at, tag, edits):
    """A built copy of the project at `at` with each (file, old, new) edit made; old must occur
    exactly once (None: new is added at the end of the file)."""
    d = os.path.join(_tmp(), f"{at}-{tag}")
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(files(at), d)
    for fn, old, new in edits:
        p = os.path.join(d, fn)
        with open(p) as f:
            text = f.read()
        if old is None:
            with open(p, "w") as f:
                f.write(text + new)
            continue
        if text.count(old) != 1:
            raise SystemExit(f"art/lang: patch {tag}: {old!r} occurs {text.count(old)} times in {fn} at {at}")
        with open(p, "w") as f:
            f.write(text.replace(old, new))
    _make(d)
    return d


def source(at, name):
    with open(os.path.join(files(at), name)) as f:
        return f.read()


def sh(d, args, stdin=None):
    """Run args in d: (stdout, stderr, status)."""
    r = subprocess.run(args, cwd=d, capture_output=True, text=True, input=stdin, timeout=120)
    return r.stdout, r.stderr, r.returncode


def mote(at, src, *opts, name="t.mote", d=None):
    """./mote [opts] on a file holding src, in the project at `at`."""
    d = d or project(at)
    with open(os.path.join(d, name), "w") as f:
        f.write(src)
    return sh(d, ["./mote", *opts, name])


# ------------------------------------------------------------------ what the programs print

def tokens(text):
    """--tokens output -> [(line, col, kind, text)], eof last (text "")."""
    out = []
    for ln in text.splitlines():
        m = re.match(r"^(\d+):(\d+) (\w+)(?: (.*))?$", ln)
        assert m, ln
        out.append((int(m[1]), int(m[2]), m[3], m[4] or ""))
    return out


def parse_tree(text):
    """--parse-tree output -> (label, kind, kids): a rule node has kind None, a token's leaf its
    kind (name, number, keyword, op) and no kids."""
    rows = []
    for ln in text.splitlines():
        ind = len(ln) - len(ln.lstrip(" "))
        assert ind % 2 == 0, ln
        body = ln.strip()
        if " " in body:
            kind, tok = body.split(" ", 1)
            rows.append((ind // 2, tok, kind))
        else:
            rows.append((ind // 2, body, None))
    pos = [0]

    def node(depth):
        d, lab, kind = rows[pos[0]]
        assert d == depth, rows[pos[0]]
        pos[0] += 1
        kids = []
        while pos[0] < len(rows) and rows[pos[0]][0] == depth + 1:
            kids.append(node(depth + 1))
        assert not (kind and kids), lab
        return (lab, kind, kids)

    t = node(0)
    assert pos[0] == len(rows)
    return t


def leaves(t):
    lab, kind, kids = t
    return [(lab, kind)] if kind else [x for k in kids for x in leaves(k)]


def size(t):
    return 1 + sum(size(k) for k in t[2])


def sexpr(s):
    """An expression as --tree prints it, (- i#1 j#2), -> nested tuples: ("op", a, b), ("var",
    name, index), ("num", value)."""
    toks = re.findall(r"\(|\)|[^\s()]+", s)
    pos = [0]

    def one():
        t = toks[pos[0]]
        pos[0] += 1
        if t == "(":
            op = toks[pos[0]]
            pos[0] += 1
            args = []
            while toks[pos[0]] != ")":
                args.append(one())
            pos[0] += 1
            return ("op", op, *args)
        m = re.match(r"^(\w+)#(\d+)$", t)
        if m:
            return ("var", m[1], int(m[2]))
        return ("num", int(t))

    e = one()
    assert pos[0] == len(toks), s
    return e


def syntax_tree(text):
    """--tree output -> a list of statements: (kind, var or None, expr or None, body, else)."""
    rows = []
    for ln in text.splitlines():
        ind = len(ln) - len(ln.lstrip(" "))
        rows.append((ind // 2, ln.strip()))
    pos = [0]

    def block(depth):
        out = []
        while pos[0] < len(rows) and rows[pos[0]][0] == depth and rows[pos[0]][1] != "else":
            s = rows[pos[0]][1]
            pos[0] += 1
            word, _, rest = s.partition(" ")
            var = expr = None
            body, els = [], None
            if word in ("read", ":="):
                v, _, rest = rest.partition(" ")
                var = sexpr(v)
            if rest:
                expr = sexpr(rest)
            if word in ("if", "while"):
                body = block(depth + 1)
                if word == "if" and pos[0] < len(rows) and rows[pos[0]] == (depth, "else"):
                    pos[0] += 1
                    els = block(depth + 1)
            out.append((word, var, expr, body, els))
        return out

    prog = block(0)
    assert pos[0] == len(rows), rows[pos[0]:]
    return prog


def symbols(text):
    """--symbols output -> [(index, name, line, col)]."""
    out = []
    for ln in text.splitlines():
        m = re.match(r"^(\d+) (\w+) (\d+):(\d+)$", ln)
        assert m, ln
        out.append((int(m[1]), m[2], int(m[3]), int(m[4])))
    return out


# ------------------------------------------------------------------ drawing helpers of this file

def legend(f, y, items, x=24, size=11.5):
    """A row of key boxes: items are (box class, dashed, label, text class)."""
    for cls, dash, lab, tcls in items:
        f.rect(x, y - 11, 18, 13, cls, 3, dash=dash)
        f.text(x + 25, y, lab, tcls, size, weight=600 if tcls == "ta" else None)
        x += 25 + tw(lab, size) + 22
    return x


def caret(f, x, y, cls="a"):
    """A small upward caret whose tip is at (x, y)."""
    f.path(f"M{x - 6:.1f} {y + 7:.1f} L{x:.1f} {y:.1f} L{x + 6:.1f} {y + 7:.1f}", cls)


def write(name, fig, stepped=False):
    """Write fig as figures/<name>.svg after the checks (ASCII, kept whole by the site's sanitizer,
    and for a stepped figure steppable within the site's limits); return the path."""
    text = fig.svg()
    try:
        text.encode("ascii")
    except UnicodeEncodeError as e:
        raise SystemExit(f"{name}: not ASCII: {e}")
    sane(text, name)
    note = ""
    if stepped:
        note = f"  ({steps.check(text)} steps)"
    elif '<g class="step">' in text:
        raise SystemExit(f"{name}: has step groups but is not meant to be stepped")
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + ".svg")
    with open(p, "w") as fh:
        fh.write(text)
    print(os.path.relpath(p, ROOT) + note)
    return p


# ------------------------------------------------------------------ 01.05

SESSION = ["x := 6", "while x > 4 do", "x := x - 1", "end", "write x"]
PROMPTS = ("> ", ". ")


def session():
    """The session at ./mote0's prompt at 01.05: [(prompt it was typed at, line, output, depth
    after it, (first, last) lines run or None, [(name, value) set while they ran], {name: value}
    after it)], and the prompt printed after the last line."""
    text = "\n".join(SESSION) + "\n"
    out, err, st = sh(project("01.05"), ["./mote0"], text)
    assert st == 0 and err == "", (st, err)
    # stdout: a prompt before each line, then what that line printed; a last prompt, then the
    # line end the end of the input prints
    prompts, outputs, pos = [], [], 0
    for k in range(len(SESSION) + 1):
        assert out[pos:pos + 2] in PROMPTS, (out, pos)
        prompts.append(out[pos:pos + 2])
        pos += 2
        if k == len(SESSION):
            break
        o = ""
        while out[pos:pos + 2] not in PROMPTS:
            nl = out.index("\n", pos)
            o, pos = o + out[pos:nl + 1], nl + 1
        outputs.append(o)
    assert out[pos:] == "\n", out
    # the same session in a copy that reports the depth, the lines run, each value set and the names
    t = patched("01.05", "prompt", [
        ("mote0.c", "  n->value = v;\n}", '  n->value = v;\n  fprintf(stderr, "set %.*s %ld\\n", len, s, v);\n}'),
        ("mote0.c", "static void prompt(void) {",
         "static void trace_names(void) {\n  fprintf(stderr, \"names\");\n"
         "  for (Name *n = names; n; n = n->next)\n"
         "    fprintf(stderr, \" %.*s=%ld\", n->len, n->s, n->value);\n  fprintf(stderr, \"\\n\");\n}\n\n"
         "static void prompt(void) {"),
        ("mote0.c", "    if (depth > 0)\n      continue;\n    if (!setjmp(again))\n      run(first);\n"
                    "    first = nlines;\n    depth = 0;\n",
         "    fprintf(stderr, \"line %d %d\\n\", nlines, depth);\n"
         "    if (depth > 0) {\n      trace_names();\n      continue;\n    }\n"
         "    fprintf(stderr, \"run %d %d\\n\", first + 1, nlines);\n"
         "    if (!setjmp(again))\n      run(first);\n    first = nlines;\n    depth = 0;\n    trace_names();\n"),
    ])
    out2, err2, st2 = sh(t, ["./mote0"], text)
    assert (out2, st2) == (out, 0), (out2, err2)
    rows, cur = [], None
    for ln in err2.splitlines():
        w = ln.split()
        if w[0] == "line":
            cur = {"line": int(w[1]), "depth": int(w[2]), "ran": None, "sets": []}
        elif w[0] == "run":
            cur["ran"] = (int(w[1]), int(w[2]))
        elif w[0] == "set":
            cur["sets"].append((w[1], int(w[2])))
        else:
            assert w[0] == "names", ln
            cur["names"] = dict((kv.split("=")[0], int(kv.split("=")[1])) for kv in w[1:])
            rows.append(cur)
    assert [r["line"] for r in rows] == list(range(1, len(SESSION) + 1)), rows
    out_rows = [(prompts[k], SESSION[k], outputs[k], r["depth"], r["ran"], r["sets"], r["names"])
                for k, r in enumerate(rows)]
    # what the figure and its captions say
    assert prompts == ["> ", "> ", ". ", ". ", "> ", "> "], prompts
    assert [r[3] for r in out_rows] == [0, 1, 1, 0, 0]
    assert [r[4] for r in out_rows] == [(1, 1), None, None, (2, 4), (5, 5)]
    assert out_rows[0][5] == [("x", 6)] and out_rows[3][5] == [("x", 5), ("x", 4)] and out_rows[4][5] == []
    assert [r[6] for r in out_rows] == [{"x": 6}, {"x": 6}, {"x": 6}, {"x": 4}, {"x": 4}]
    assert [r[2] for r in out_rows] == ["", "", "", "", "4\n"]
    return out_rows, prompts[-1]


def prompt():
    rows, last_prompt = session()
    f = Fig("f0105a", "A session at the prompt", 0, W)
    TX, TY, TWD = 24, 34, 396                   # the session's box
    LH, B0 = 24, TY + 27                        # line height, first baseline
    PX = TX + 16                                # the prompt's column
    SZ = 14
    NX, NW = 448, 168                           # the names
    nlines = len(rows) + sum(r[2].count("\n") for r in rows) + 1
    TH = (nlines - 1) * LH + 40
    f.text(TX, 20, "what is typed at the prompt, and what it prints", "tm", 11.5)
    f.text(NX, 20, "the names after the line", "tm", 11.5)
    f.rect(TX, TY, TWD, TH, "s fs", 8)
    f.rect(NX, TY, NW, 64, "s f", 8)
    f.text(NX + 16, TY + 20, "name", "tm", 11)
    f.text(NX + 96, TY + 20, "value", "tm", 11)
    f.line(NX, TY + 30, NX + NW, TY + 30, "m")
    caps = [
        "x := 6 is a whole statement: it runs at once, x is 6, and > asks for the next line.",
        "while opens a block: the line is held, not run, and the prompt is now . until the block ends.",
        "x := x - 1 is held too. Nothing has run: x is still 6.",
        "end closes the block. The three held lines run as a file's lines would: x goes to 5, then 4.",
        "write x runs at once and prints 4. Between lines the names keep their values.",
    ]
    for k in range(len(rows)):
        prompt_, line, output, depth, ran, sets, names = rows[k]
        with steps.step(f, caps[k]):
            y = B0
            # the lines typed so far, each after the prompt it was typed at, then what it printed
            ys = []
            for i in range(k + 1):
                p_, ln, o, dep, rn, _, _ = rows[i]
                if i == k:
                    f.rect(TX + 6, y - 17, TWD - 12, 24, "af", 4, sw=False)
                f.text(PX, y, p_.strip(), "t", SZ, weight=700, mono=True)
                f.text(PX + mw("> ", SZ), y, ln, "ta" if i == k else "t", SZ, weight=700 if i == k else None,
                       mono=True)
                ys.append(y)
                y += LH
                for ol in o.splitlines():
                    f.text(PX, y, ol, "t", SZ, weight=700, mono=True)
                    y += LH
            # the prompt waiting for the next line, and the cursor
            nxt = rows[k + 1][0] if k + 1 < len(rows) else last_prompt
            f.text(PX, y, nxt.strip(), "t", SZ, weight=700, mono=True)
            f.rect(PX + mw("> ", SZ), y - 13, 8, 16, "fa", 1, sw=False)
            # held or run: the block's lines, bracketed
            first = next((i for i in range(k, -1, -1) if rows[i][0] == "> "), 0)
            if depth > 0 or (ran and ran[1] > ran[0]):
                a, b = (first, k) if depth > 0 else (ran[0] - 1, ran[1] - 1)
                bx = PX + mw("> while x > 4 do", SZ) + 26
                top, bot = ys[a] - 16, ys[b] + 6
                cls = "m" if depth > 0 else "a"
                f.path(f"M{bx - 6} {top} H{bx} V{bot} H{bx - 6}", cls)
                mid = (top + bot) / 2
                if depth > 0:
                    f.text(bx + 12, mid - 2, "held:", "t", 12, weight=600)
                    f.text(bx + 12, mid + 13, "not run yet", "tm", 12)
                else:
                    f.text(bx + 12, mid - 2, "run now,", "ta", 12, weight=700)
                    f.text(bx + 12, mid + 13, "as one block", "ta", 12)
            # the names
            for j, (nm, v) in enumerate(names.items()):
                ry = TY + 51 + j * 26
                f.text(NX + 16, ry, nm, "t", SZ, weight=700, mono=True)
                f.text(NX + 96, ry, str(v), "ta" if sets else "t", SZ, weight=700, mono=True)
            if len(sets) > 1:
                f.text(NX, TY + 92, "while the block ran:", "tm", 11.5)
                for j, (nm, v) in enumerate(sets):
                    f.text(NX + 16, TY + 114 + j * 20, f"{nm} = {v}", "ta", 13, weight=600, mono=True)
    f.h = TY + TH + 12
    return f


def agree_rows(at):
    """./agree in the project at `at`: [(program, [(way, result)])], and its last line."""
    out, err, st = sh(project(at), ["./agree"])
    assert st == 0 and err == "", (at, err)
    lines = out.splitlines()
    rows = []
    for ln in lines[:-1]:
        name, rest = ln.split(None, 1)
        cells = re.findall(r"(\S+(?: -O)?) (ok|DIFFERS)", rest)
        rows.append((name, cells))
    return rows, lines[-1]


def agree():
    rows, last = agree_rows("01.05")
    assert last == "3 programs, 2 ways each: all agree", last
    names = [r[0] for r in rows]
    assert names == ["gcd", "primes", "sum"], names
    assert all(c == [("mote0", "ok"), ("motec", "ok")] for _, c in rows), rows
    # the lesson each later way first appears in
    first = {"mote0": "01.05", "motec": "01.05"}
    for at in ("01.09", "01.10", "01.11"):
        r, _ = agree_rows(at)
        for way, res in r[0][1]:
            assert res == "ok", (at, way)
            first.setdefault(way, at)
    ways = [w for w, _ in agree_rows("01.11")[0][0][1]]
    assert ways == ["mote0", "motec", "mote", "machine", "machine -O"], ways
    assert first == {"mote0": "01.05", "motec": "01.05", "mote": "01.09", "machine": "01.10",
                     "machine -O": "01.11"}, first
    d = project("01.05")
    expect, inputs = {}, {}
    for n in names:
        with open(os.path.join(d, "programs", n + ".out")) as fh:
            expect[n] = fh.read().split("\n")[:-1]
        with open(os.path.join(d, "programs", n + ".in")) as fh:
            inputs[n] = fh.read().strip()
    assert expect["gcd"] == ["21"] and expect["sum"] == ["5050"] and len(expect["primes"]) == 10
    assert inputs == {"gcd": "1071 462", "primes": "30", "sum": "100"}, inputs

    f = Fig("f0105b", "agree: every program, every way", 0, W)
    X0, PW, EW = 24, 92, 104                    # the program column, the expected output column
    WX = X0 + PW + EW + 8                       # the first way's column
    CWD = (W - 24 - WX) / len(ways)
    HY, RY, RH = 26, 58, 46                     # header baselines, the rows' top, a row's height
    f.text(X0, HY, "program", "tm", 11.5)
    f.text(X0 + PW, HY, "expected", "tm", 11.5)
    f.text(X0 + PW, HY + 14, "programs/*.out", "tm", 10.5, mono=True)
    for j, w in enumerate(ways):
        cx = WX + j * CWD + CWD / 2
        now = first[w] == "01.05"
        f.text(cx, HY, w, "t" if now else "tm", 12.5, "middle", 700 if now else None, mono=True)
        f.text(cx, HY + 14, "now" if now else "from " + first[w], "ta" if now else "tm", 10.5, "middle",
               600 if now else None)
    f.line(X0, RY - 6, W - 24, RY - 6, "m")
    for i, n in enumerate(names):
        y = RY + i * RH
        f.text(X0, y + 19, n, "t", 13.5, weight=700, mono=True)
        f.text(X0, y + 34, "input " + inputs[n], "tm", 10.5)
        e = expect[n]
        shown = e[0] if len(e) == 1 else f"{e[0]} {e[1]} {e[2]} ... {e[-1]}"
        f.rect(X0 + PW - 6, y + 4, EW, 34, "s fs", 5)
        f.text(X0 + PW + 2, y + 25 if len(e) == 1 else y + 19, shown, "t", 12.5, weight=600, mono=True)
        if len(e) > 1:
            f.text(X0 + PW + 2, y + 33, f"{len(e)} lines", "tm", 10.5)
        res = dict(rows[i][1])
        for j, w in enumerate(ways):
            cx = WX + j * CWD + CWD / 2
            bw = CWD - 14
            if w in res:
                f.rect(cx - bw / 2, y + 6, bw, 30, "a af", 6)
                f.text(cx, y + 25, res[w], "ta", 13, "middle", 700, mono=True)
            else:
                f.rect(cx - bw / 2, y + 6, bw, 30, "m f", 6, dash=True)
    by = RY + len(names) * RH + 4
    f.line(X0, by, W - 24, by, "m")
    f.text(X0, by + 24, "ok: what the way printed is the row's .out, byte for byte (cmp)", "tm", 11.5)
    f.text(X0, by + 46, "./agree", "t", 12, weight=700, mono=True)
    f.text(X0 + mw("./agree  ", 12), by + 46, last, "t", 12, mono=True)
    f.h = by + 60
    return f


# ------------------------------------------------------------------ 01.06

LESSONS = ["01.05", "01.06", "01.07", "01.08", "01.09", "01.10", "01.11"]


def gcd_text(at):
    with open(os.path.join(files(at), "programs", "gcd.mote")) as fh:
        return fh.read()


def phases():
    # the lesson each phase's file first appears in
    first = {}
    for at in LESSONS:
        for fn in ("scan.c", "parse.c", "analyze.c", "interp.c", "gen.c", "improve.c"):
            if os.path.exists(os.path.join(files(at), fn)):
                first.setdefault(fn, at)
    assert first == {"scan.c": "01.06", "parse.c": "01.07", "analyze.c": "01.08", "interp.c": "01.09",
                     "gen.c": "01.10", "improve.c": "01.11"}, first
    # the driver at the end of the chapter: its options, and the phases called in this order
    main_c = source("01.11", "main.c")
    for opt in ("--tokens", "--parse-tree", "--tree", "--symbols", "-S"):
        assert f'"{opt}"' in main_c, opt
    body = main_c[main_c.index("int main(int argc, char **argv) {"):]
    at = [body.index(c) for c in ("scan(file", "parse(tok)", "analyze(tree)", "improve(prog)", "generate(prog)",
                                  "interpret(prog)")]
    assert at == sorted(at), at
    # at 01.06, --tokens is the one option; the parse tree is still to come
    out, err, st = mote("01.06", gcd_text("01.06"), "--tokens")
    assert st == 0 and out.endswith("11:8 eof\n"), (st, err)
    out, err, st = mote("01.06", gcd_text("01.06"), "--parse-tree")
    assert st == 2 and err == "usage: mote (--tokens) FILE\n", err

    f = Fig("f0106a", "The phases in the order the driver calls them", 0, W)
    R1, R2 = 62, 182                     # the two rows' middles
    BH = 40
    ST = {"here": ("a af", False, "ta", 700, "a"), "later": ("m f", True, "tm", 600, "m")}

    def phase(x, y, w, name, lesson):
        cls, dash, tc, wt, _ = ST["here" if lesson == "01.06" else "later"]
        f.rect(x, y - BH / 2, w, BH, cls, 8, dash=dash)
        f.text(x + w / 2, y - 2, name, tc, 13, "middle", wt)
        f.text(x + w / 2, y + 13, lesson, tc, 10.5, "middle", 600 if lesson == "01.06" else None, mono=True)
        return x + w

    def form(x1, x2, y, name, opt, now):
        s = "here" if now else "later"
        f.line(x1, y, x2, y, ST[s][4], arrow=True, dash=not now)
        f.text((x1 + x2) / 2, y - 8, name, "t" if now else "tm", 12, "middle", 600 if now else None)
        if opt:
            f.text((x1 + x2) / 2, y + 17, opt, "ta" if now else "tm", 10.5, "middle", 600 if now else None, mono=True)

    f.text(24, 18, "main.c, the driver: each phase is handed what the one before it made", "tm", 11.5)
    # row 1: characters, the scanner, tokens, the parser, the parse tree
    form(24, 128, R1, "characters", None, True)
    x = phase(130, R1, 104, "scanner", first["scan.c"])
    form(x + 2, 346, R1, "tokens", "--tokens", True)
    x = phase(348, R1, 96, "parser", first["parse.c"])
    form(x + 2, 582, R1, "parse tree", "--parse-tree", False)
    # ... wrapping round to row 2: semantic analysis, the syntax tree and the symbol table
    SX, SW_ = 24, 140
    f.path(f"M582 {R1} H604 V{R1 + 58} H{SX + SW_ / 2} V{R2 - BH / 2 - 2}", "m", arrow=True, dash=True)
    x = phase(SX, R2, SW_, "semantic analysis", first["analyze.c"])
    FX = 300                             # the fork
    form(x + 2, FX, R2, "syntax tree", "--tree", False)
    f.line(SX + SW_ / 2, R2 + BH / 2 + 2, SX + SW_ / 2, R2 + 62, "m", arrow=True, dash=True)
    f.rect(SX + 12, R2 + 64, SW_ - 24, 26, "m f", 5, dash=True)
    f.text(SX + SW_ / 2, R2 + 81, "symbol table", "tm", 12, "middle", 600)
    f.text(SX + SW_ + 10, R2 + 81, "--symbols", "tm", 10.5, mono=True)
    # the two ends: the tree walk; the improver, the code generator and the assembly
    TY_, IY = R2 - 34, R2 + 34
    f.path(f"M{FX} {R2} V{TY_} H{FX + 22}", "m", arrow=True, dash=True)
    f.path(f"M{FX} {R2} V{IY} H{FX + 22}", "m", arrow=True, dash=True)
    x = phase(FX + 24, TY_, 100, "tree walk", first["interp.c"])
    f.line(x + 2, TY_, x + 30, TY_, "m", arrow=True, dash=True)
    f.text(x + 36, TY_ + 4, "the program runs", "tm", 12)
    x = phase(FX + 24, IY, 84, "improver", first["improve.c"])
    f.line(x + 2, IY, x + 18, IY, "m", arrow=True, dash=True)
    x = phase(x + 20, IY, 116, "code generator", first["gen.c"])
    f.line(x + 2, IY, x + 20, IY, "m", arrow=True, dash=True)
    f.text(x + 24, IY + 4, "assembly", "tm", 12, weight=600)
    f.text(x + 24, IY + 21, "-S", "tm", 10.5, mono=True)
    # legend
    ly = R2 + 128
    x = legend(f, ly, [("a af", False, "01.06: this lesson", "ta"), ("m f", True, "still to come", "tm")])
    f.text(x, ly, "--tokens", "ta", 10.5, weight=600, mono=True)
    f.text(x + mw("--tokens ", 10.5), ly, "prints what is on its arrow, then stops", "tm", 11.5)
    f.h = ly + 14
    return f


def gcd_tokens(at="01.06"):
    text = gcd_text(at)
    out, err, st = mote(at, text, "--tokens")
    assert st == 0, err
    toks = tokens(out)
    lines = text.split("\n")
    for ln, col, kind, s in toks[:-1]:
        assert lines[ln - 1][col - 1:col - 1 + len(s)] == s, (ln, col, s)
    return text, toks


def scan_steps():
    text, toks = gcd_tokens()
    line = text.split("\n")[3]
    assert line == "while i != j do", line
    mine = [t for t in toks if t[0] == 4]
    assert mine == [(4, 1, "keyword", "while"), (4, 7, "name", "i"), (4, 9, "op", "!="), (4, 12, "name", "j"),
                    (4, 14, "keyword", "do")], mine
    nxt = toks[toks.index(mine[-1]) + 1]
    assert nxt == (5, 5, "keyword", "if"), nxt
    ops = re.search(r"static const char \*ops\[\] = \{(.*)\};", source("01.06", "scan.c"))[1]
    ops = re.findall(r'"([^"]+)"', ops)
    assert [len(o) for o in ops] == sorted((len(o) for o in ops), reverse=True) and "!=" in ops, ops

    f = Fig("f0106b", "The scanner on one line of gcd.mote", 0, W)
    CX0, CWD_, CY, CH = 68, 30, 46, 36           # the cells: left, width, top, height
    n = len(line) + 1                            # the characters and the line end
    f.text(24, 18, "line 4 of gcd.mote, a character to a cell, with its column", "tm", 11.5)
    for c in range(n):
        f.text(CX0 + c * CWD_ + CWD_ / 2, CY - 6, str(c + 1), "tm", 10.5, "middle", mono=True)
    LY = CY + CH + 84                             # the tokens' list
    f.text(24, LY - 22, "the tokens so far, as --tokens prints them", "tm", 11.5)
    f.text(420, LY - 22, "where the scanner is", "tm", 11.5)

    def cell(c, state):
        x = CX0 + c * CWD_
        cls, dash, tc, wt = {"unread": ("m f", False, "tm", None), "token": ("s fs", False, "t", 600),
                             "new": ("a af", False, "ta", 700), "passed": ("m f", True, "tm", None)}[state]
        f.rect(x + 1.5, CY, CWD_ - 3, CH, cls, 4, dash=dash)
        cx, cy = x + CWD_ / 2, CY + CH / 2
        if c == len(line):                       # the line end
            f.path(f"M{cx + 5} {cy - 7} V{cy + 2} H{cx - 6}", "m" if state != "unread" else "m")
            f.path(f"M{cx - 2.5} {cy - 1.5} L{cx - 6} {cy + 2} L{cx - 2.5} {cy + 5.5}", "m")
        elif line[c] == " ":
            f.circle(cx, cy + 2, 1.2, "m")
        else:
            f.text(cx, cy + 6, line[c], tc, 17, "middle", wt, mono=True)

    caps = [
        "w is a letter, so name() takes the whole word, while, and then finds it among the keywords: "
        "a keyword, at 4:1.",
        "The space only keeps tokens apart: it is passed over. i is a word but not a keyword: a name, at 4:7.",
        "! is not a digit, a letter or _, so op() tries the operators, the two-character ones first: != is "
        "one token, at 4:9.",
        "Another space, then j: a name, at 4:12.",
        "do: a keyword, at 4:14, the last token of the line.",
        "The line end is passed over too: the line goes to 5 and the column back to 1. Nothing of the spaces "
        "or the line end is kept; the next token is if, at 5:5.",
    ]
    for k in range(len(mine) + 1):
        with steps.step(f, caps[k]):
            done = mine[:k + 1]
            end = done[-1][1] - 1 + len(done[-1][3]) if k < len(mine) else n   # the column index p is at
            for c in range(n):
                tok = next((t for t in done if t[1] - 1 <= c < t[1] - 1 + len(t[3])), None)
                if tok is not None:
                    st = "new" if k < len(mine) and tok == done[-1] else "token"
                else:
                    st = "passed" if c < end else "unread"
                cell(c, st)
            # where p is
            if k < len(mine):
                px = CX0 + end * CWD_ + CWD_ / 2
                caret(f, px, CY + CH + 6)
                f.text(px, CY + CH + 27, "p", "ta", 13, "middle", 700, mono=True)
                at_line, at_col = 4, end + 1
            else:
                at_line, at_col = 5, 1
            # the tokens made so far
            for j, (ln, col, kind, s) in enumerate(done):
                new = k < len(mine) and j == k
                f.text(24, LY + j * 22, f"{ln}:{col} {kind} {s}", "ta" if new else "t", 13.5,
                       weight=700 if new else None, mono=True)
            if k == len(mine):
                f.text(24, LY + len(done) * 22, f"{nxt[0]}:{nxt[1]} {nxt[2]} {nxt[3]}", "tm", 13.5, mono=True)
                f.text(24 + mw(f"{nxt[0]}:{nxt[1]} {nxt[2]} {nxt[3]}  ", 13.5), LY + len(done) * 22,
                       "next, on line 5", "tm", 11.5)
            # the scanner's place: line and col, which every token is given
            f.rect(420, LY - 12, 196, 52, "s f", 6)
            f.text(436, LY + 8, "line", "tm", 12)
            f.text(476, LY + 8, str(at_line), "t", 14, weight=700, mono=True)
            f.text(516, LY + 8, "col", "tm", 12)
            f.text(548, LY + 8, str(at_col), "t", 14, weight=700, mono=True)
            f.text(436, LY + 29, "line and col follow p", "tm", 11)
    f.h = LY + 6 * 22 + 4
    return f


def chars_to_tokens():
    text, toks = gcd_tokens()
    assert len(text) == 170 and text.isascii(), len(text)
    real = toks[:-1]
    assert len(real) == 29 and toks[-1] == (11, 8, "eof", ""), (len(real), toks[-1])
    lines = text.split("\n")
    assert lines[-1] == "" and len(lines) == 12
    lines = lines[:-1]
    f = Fig("f0106c", "gcd.mote as the scanner leaves it", 0, W)
    SZ, LH = 13, 22
    C = mw("x", SZ)
    X0, Y0 = 52, 46
    f.text(24, 18, "programs/gcd.mote, every character", "tm", 11.5)
    for i, ln in enumerate(lines):
        y = Y0 + i * LH
        f.text(X0 - 12, y, str(i + 1), "tm", 10.5, "end", mono=True)
        mine = [t for t in real if t[0] == i + 1]
        for _, col, kind, s in mine:
            f.rect(X0 + (col - 1) * C - 2, y - 14, len(s) * C + 4, 19, "a af", 3, sw=False)
        covered = {c for _, col, _, s in mine for c in range(col - 1, col - 1 + len(s))}
        hash_at = ln.find("#")
        spans = []
        if hash_at >= 0:
            spans.append((hash_at, len(ln), "tm"))
        f.code(X0, y, ln, SZ, "t", spans)
        for c, ch in enumerate(ln):
            if ch == " " and c not in covered and (hash_at < 0 or c < hash_at):
                f.circle(X0 + c * C + C / 2, y - 4, 1.1, "m")
        # the line end
        ex = X0 + len(ln) * C + 4
        f.path(f"M{ex + 8} {y - 11} V{y - 4} H{ex + 1}", "m")
        f.path(f"M{ex + 3.5} {y - 6.5} L{ex + 1} {y - 4} L{ex + 3.5} {y - 1.5}", "m")
    # the counts
    RX = 492
    f.text(RX, 74, str(len(text)), "t", 28, weight=700, mono=True)
    f.text(RX, 94, "characters", "t", 12.5, weight=600)
    f.text(RX, 110, "line ends and spaces too", "tm", 11)
    f.line(RX + 24, 124, RX + 24, 158, "a", arrow=True)
    f.text(RX + 36, 146, "scan", "ta", 12, weight=600)
    f.text(RX, 192, str(len(real)), "ta", 28, weight=700, mono=True)
    f.text(RX, 212, "tokens", "ta", 12.5, weight=700)
    f.text(RX, 228, f"then eof, at {toks[-1][0]}:{toks[-1][1]}", "tm", 11)
    # legend
    ly = Y0 + len(lines) * LH + 12
    f.rect(24, ly - 11, 22, 14, "a af", 3, sw=False)
    f.text(52, ly, "a token", "t", 11.5)
    f.circle(120, ly - 4, 1.1, "m")
    f.text(128, ly, "a space", "tm", 11.5)
    ex = 192
    f.path(f"M{ex + 8} {ly - 11} V{ly - 4} H{ex + 1}", "m")
    f.path(f"M{ex + 3.5} {ly - 6.5} L{ex + 1} {ly - 4} L{ex + 3.5} {ly - 1.5}", "m")
    f.text(ex + 16, ly, "a line end", "tm", 11.5)
    f.text(278, ly, "#", "tm", 12, weight=700, mono=True)
    f.text(290, ly, "a comment", "tm", 11.5)
    f.text(374, ly, "grey: read once, and not kept", "tm", 11.5)
    f.h = ly + 12
    return f


# ------------------------------------------------------------------ 01.07

def rule_and_function():
    src = source("01.07", "parse.c")
    assert re.search(r'^//\s+\| "while" cond "do" \{ stmt \} "end" \.$', src, re.M), "the while rule"
    code = ['} else if (equal(tok, "while")) {', '  take(n);', '  add(n, cond());', '  expect(n, "do");',
            '  stmts(n);', '  expect(n, "end");']
    stmt_fn = src[src.index("static Parse *stmt(void) {"):]
    stmt_fn = stmt_fn[:stmt_fn.index("\n}\n")]
    assert "\n".join("  " + c for c in code) in stmt_fn, "stmt()'s while branch"
    inset = ["while (starts_stmt())", "  add(n, stmt());"]
    assert "static void stmts(Parse *n) {\n  " + inset[0] + "\n    " + inset[1].strip() + "\n}" in src

    f = Fig("f0107a", "A rule of the grammar and its function", 0, W)
    SZ, CSZ = 13.5, 12.5
    PX, CX, NX = 24, 176, 470                 # the pieces, the code, the notes
    f.text(PX, 20, "the rule, from the comment at the top of parse.c", "tm", 11.5)
    rule = 'stmt = ... | "while" cond "do" { stmt } "end"'
    spans = [(5, 12, "tm")]
    for part in ("cond", "{ stmt }"):
        a = rule.index(part)
        spans.append((a, a + len(part), "ta"))
    f.code(PX, 46, rule, SZ, "t", spans)
    f.text(PX, 84, "each piece", "tm", 11.5)
    f.text(CX, 84, "the lines of stmt() in parse.c that take it", "tm", 11.5)
    f.line(PX, 92, W - 24, 92, "m")
    # rows: (piece, is a name, [(code line, part to mark, note)])
    rows = [
        ('"while"', False, [(code[0], '"while"', "the next token chooses"), (code[1], "take(n)", "taken: a leaf")]),
        ("cond", True, [(code[2], "cond()", "a call: a node of its own")]),
        ('"do"', False, [(code[3], 'expect(n, "do")', "taken, or an error")]),
        ("{ stmt }", True, [(code[4], "stmts(n)", "a loop of calls:")]),
        ('"end"', False, [(code[5], 'expect(n, "end")', "taken, or an error")]),
    ]
    y = 118
    for piece, is_name, lines in rows:
        pw = mw(piece, SZ) + 18
        f.rect(PX, y - 17, pw, 24, "a af" if is_name else "s fs", 5)
        f.text(PX + 9, y, piece, "ta" if is_name else "t", SZ, weight=700, mono=True)
        f.line(PX + pw + 4, y - 5, CX - 10, y - 5, "a" if is_name else "s", arrow=True)
        for k, (ln, part, note) in enumerate(lines):
            a = ln.index(part)
            f.code(CX, y + k * 21, ln, CSZ, "tm", [(a, a + len(part), "ta" if is_name else "t mono")])
            f.text(NX, y + k * 21, note, "ta" if is_name else "t", 11.5)
        y += 21 * len(lines)
        if piece == "{ stmt }":
            # stmts(): the loop that { } is
            for k, ln in enumerate(inset):
                f.code(NX + 8, y + k * 18, ln, 11, "tm")
            y += 18 * len(inset)
        y += 12
    ly = y + 14
    f.line(PX, ly - 26, W - 24, ly - 26, "m")
    f.rect(PX, ly - 12, 46, 18, "a af", 4)
    f.text(PX + 23, ly + 1, "cond", "ta", 11, "middle", 700, mono=True)
    f.text(PX + 54, ly + 1, "a name: a call of that rule's function", "t", 11.5)
    x = PX + 54 + tw("a name: a call of that rule's function", 11.5) + 24
    f.rect(x, ly - 12, 40, 18, "s fs", 4)
    f.text(x + 20, ly + 1, '"do"', "t", 11, "middle", 700, mono=True)
    f.text(x + 48, ly + 1, "a quoted word: a token to take", "t", 11.5)
    f.h = ly + 14
    return f


def ptree_pos(t, leaf_x, row_y, leaf_y):
    """{path: (x, y)} for a parse tree from parse_tree(): the leaves at leaf_x(i) in order, all on the
    row leaf_y; a rule node at row_y(depth), over the middle of its first and last child."""
    pos = {}
    n = [0]

    def walk(t, path, depth):
        lab, kind, kids = t
        if kind:
            pos[path] = (leaf_x(n[0]), leaf_y)
            n[0] += 1
        else:
            xs = [walk(k, path + (i,), depth + 1) for i, k in enumerate(kids)]
            pos[path] = ((xs[0] + xs[-1]) / 2, row_y(depth))
        return pos[path][0]

    walk(t, (), 0)
    return pos


def ptree_nodes(t, path=()):
    yield path, t
    for i, k in enumerate(t[2]):
        yield from ptree_nodes(k, path + (i,))


def node_box(t, rsize, lsize):
    """(width, height) of a node's box: a rule's pill, a token's box."""
    lab, kind, _ = t
    if kind:
        return max(mw(lab, lsize) + 16, 30), lsize + 14
    return mw(lab, rsize) + 16, rsize + 10


def draw_ptree(f, t, pos, rsize=12.5, lsize=15, kinds=True, show=None, style=None, edge=None):
    """Draw a parse tree at the positions pos. style(path, node) -> (box class, text class, weight,
    dashed) or None for the plain look (a rule plain, a token in the accent); edge(parent, child) ->
    (class, dashed) or None for a plain line. show: the paths to draw (all by default)."""
    nodes = dict(ptree_nodes(t))
    show = set(nodes) if show is None else show
    for p in show:
        if not p or p[:-1] not in show:
            continue
        (x1, y1), (x2, y2) = pos[p[:-1]], pos[p]
        _, h1 = node_box(nodes[p[:-1]], rsize, lsize)
        _, h2 = node_box(nodes[p], rsize, lsize)
        cls, dash = (edge(p[:-1], p) if edge else None) or ("s", False)
        f.line(x1, y1 + h1 / 2, x2, y2 - h2 / 2, cls, dash=dash)
    for p in sorted(show):
        lab, kind, _ = nodes[p]
        x, y = pos[p]
        w, h = node_box(nodes[p], rsize, lsize)
        st = (style(p, nodes[p]) if style else None) or (("a af", "ta", 700, False) if kind else
                                                       ("s f", "t", 600, False))
        f.rect(x - w / 2, y - h / 2, w, h, st[0], 5 if kind else h / 2, dash=st[3])
        size = lsize if kind else rsize
        f.text(x, y + size * 0.36, lab, st[1], size, "middle", st[2], mono=True)
        if kind and kinds:
            f.text(x, y + h / 2 + 14, kind, "tm", 10.5, "middle")


def one_stmt_tree(at, src):
    out, err, st = mote(at, src, "--parse-tree")
    assert st == 0, err
    t = parse_tree(out)
    assert t[0] == "program" and len(t[2]) == 1, t
    return t[2][0], t


def assign_tree(at="01.07"):
    """The parse tree of i := i - j: the stmt of a file holding that line, which is also the stmt
    of line 6 of gcd.mote."""
    s, _ = one_stmt_tree(at, "i := i - j\n")
    out, err, st = mote(at, gcd_text(at), "--parse-tree")
    assert st == 0, err
    g = parse_tree(out)
    assert any(n == s for _, n in ptree_nodes(g)), "i := i - j in gcd.mote's tree"
    assert leaves(s) == [("i", "name"), (":=", "op"), ("i", "name"), ("-", "op"), ("j", "name")], leaves(s)
    rules = sorted(n[0] for _, n in ptree_nodes(s) if not n[1])
    assert rules == ["expr", "factor", "factor", "stmt", "term", "term"], rules
    return s


def tree_0107():
    s = assign_tree()
    nl = len(leaves(s))
    nr = size(s) - nl
    f = Fig("f0107b", "The parse tree of i := i - j", 0, W)
    LY = 264
    pos = ptree_pos(s, lambda i: 64 + i * 98, lambda d: 30 + d * 54, LY)
    draw_ptree(f, s, pos)
    RX = 516
    f.text(RX, 112, f"{nr} rule nodes", "t", 13, weight=700)
    f.text(RX, 129, "each says which", "tm", 11.5)
    f.text(RX, 144, "rule was used", "tm", 11.5)
    f.text(RX, LY - 4, f"{nl} tokens", "ta", 13, weight=700)
    f.text(RX, LY + 13, "the leaves,", "tm", 11.5)
    f.text(RX, LY + 28, "left to right", "tm", 11.5)
    f.h = LY + 44
    return f


# the trace of the parser on write i - j: (event, function, token index); for take, the token taken
DESCENT = [("enter", "parse", 0), ("enter", "stmt", 0), ("take", None, 0), ("enter", "expr", 1),
           ("enter", "term", 1), ("enter", "factor", 1), ("take", None, 1), ("leave", "factor", 2),
           ("leave", "term", 2), ("take", None, 2), ("enter", "term", 3), ("enter", "factor", 3),
           ("take", None, 3), ("leave", "factor", 4), ("leave", "term", 4), ("leave", "expr", 4),
           ("leave", "stmt", 4), ("leave", "parse", 4)]
# the frames: the events each shows the end of, and its caption
DESCENT_FRAMES = [
    ([0], "parse makes the program node. The next token, write, is not the end of the file, so it calls stmt."),
    ([1, 2], "stmt makes its node and looks at one token: write chooses the write statement. stmt takes it, "
             "and write is a leaf."),
    ([3], "stmt calls expr for the expression after write. expr's node is made, not yet hung under stmt's."),
    ([4], "expr calls term for its first operand."),
    ([5, 6], "term calls factor, which sees a name, i, and takes it."),
    ([7], "factor returns, and term hangs its node under its own. The next token, -, is not * or /: term "
          "is done."),
    ([8], "term returns, and expr hangs it. The next token is -, one of + and -, so expr goes on."),
    ([9], "expr takes - as a leaf of its own."),
    ([10], "expr calls term for the operand after the -."),
    ([11, 12], "term calls factor, which takes the name j."),
    ([13], "factor returns, and term hangs it. Next is the end of the file, not * or /."),
    ([14], "term returns, and expr hangs it. The end of the file is not + or -: expr is done."),
    ([15], "expr returns, and stmt hangs it: the write statement is whole."),
    ([16], "stmt returns, and parse hangs it under program."),
    ([17], "parse sees the end of the file and stops. The leaves, left to right, are the tokens."),
]


def parse_trace(at, src):
    """--parse-tree of src in a copy of the project at `at` whose rule functions and take() report
    each call, return and token taken on stderr: ([(event, function, token index)], tokens, tree);
    the tree it prints must be the real one."""
    fns = ["factor", "term", "expr", "cond", "stmt"]
    edits = [("parse.c", '#include "mote.h"\n',
              '#include "mote.h"\n\nstatic Parse *factor(void);\nstatic Parse *term(void);\n'
              'static Parse *cond(void);\nstatic void take(Parse *n);\n')]
    tail = "\n// the figures' trace\n"
    for fn in fns:
        edits.append(("parse.c", f"static Parse *{fn}(void) {{\n", f"static Parse *{fn}__real(void) {{\n"))
        tail += (f"static Parse *{fn}(void) {{\n"
                 f'  fprintf(stderr, "enter {fn} %d:%d\\n", tok->line, tok->col);\n'
                 f"  Parse *n = {fn}__real();\n"
                 f'  fprintf(stderr, "leave {fn} %d:%d\\n", tok->line, tok->col);\n'
                 "  return n;\n}\n")
    edits.append(("parse.c", "Parse *parse(Token *t) {\n", "static Parse *parse__real(Token *t) {\n"))
    edits.append(("parse.c", "static void take(Parse *n) {\n", "static void take__real(Parse *n) {\n"))
    tail += ("Parse *parse(Token *t) {\n"
             '  fprintf(stderr, "enter parse %d:%d\\n", t->line, t->col);\n'
             "  Parse *n = parse__real(t);\n"
             '  fprintf(stderr, "leave parse %d:%d\\n", tok->line, tok->col);\n'
             "  return n;\n}\n"
             "static void take(Parse *n) {\n"
             '  fprintf(stderr, "take %d:%d\\n", tok->line, tok->col);\n'
             "  take__real(n);\n}\n")
    edits.append(("parse.c", None, tail))
    d = patched(at, "trace", edits)
    out, err, st = mote(at, src, "--parse-tree", d=d)
    assert st == 0, err
    real, err2, st2 = mote(at, src, "--parse-tree")
    assert st2 == 0 and out == real, (out, real)
    tout, _, _ = mote(at, src, "--tokens")
    toks = tokens(tout)
    ix = {(t[0], t[1]): i for i, t in enumerate(toks)}
    ev = []
    for ln in err.splitlines():
        w = ln.split()
        lc = tuple(int(v) for v in w[-1].split(":"))
        ev.append((w[0], w[1] if w[0] != "take" else None, ix[lc]))
    return ev, toks, parse_tree(real)


def descent():
    src = "write i - j\n"
    ev, toks, real = parse_trace("01.07", src)
    assert ev == DESCENT, ev
    assert [t[3] for t in toks] == ["write", "i", "-", "j", ""] and toks[-1][2] == "eof", toks
    # the run, node by node: node id -> [label, kind, parent id, hung under it yet]
    nodes, kids, stack, states = {}, {}, [], []
    nxt = 0
    for e, fn, i in ev:
        if e == "enter":
            nid = len(nodes)
            nodes[nid] = ["program" if fn == "parse" else fn, None, stack[-1] if stack else None, False, fn]
            kids[nid] = []
            stack.append(nid)
            nxt, hot = i, nid
        elif e == "take":
            nid = len(nodes)
            nodes[nid] = [toks[i][3], toks[i][2], stack[-1], True, None]
            kids[nid] = []
            kids[stack[-1]].append(nid)
            nxt, hot = i + 1, nid
        else:
            nid = stack.pop()
            assert nodes[nid][4] == fn
            if stack:
                nodes[nid][3] = True
                kids[stack[-1]].append(nid)
            nxt, hot = i, nid
        states.append(({k: list(v) for k, v in nodes.items()}, list(stack), nxt, hot))

    def build(nid):
        lab, kind = nodes[nid][:2]
        return (lab, kind, [build(k) for k in kids[nid]])
    assert build(0) == real, (build(0), real)
    path_of = {}

    def paths(nid, path):
        path_of[nid] = path
        for i, k in enumerate(kids[nid]):
            paths(k, path + (i,))
    paths(0, ())
    assert [e for fr, _ in DESCENT_FRAMES for e in fr] == list(range(len(ev)))

    f = Fig("f0107c", "The parser on write i - j", 0, W)
    TY = 32
    f.text(24, 18, "the tokens; the marked one is next", "tm", 11.5)
    tok_x = []
    x = 24
    for t in toks:
        lab = t[3] if t[2] != "eof" else "eof"
        w = max(34, mw(lab, 14) + 18)
        tok_x.append((x, w))
        x += w + 10
    SX, SW_, SH, FLOOR = 24, 116, 28, 348
    f.text(SX, 112, "the functions running,", "tm", 11.5)
    f.text(SX, 127, "the last called on top", "tm", 11.5)
    f.text(196, 112, "the parse tree so far", "tm", 11.5)
    pos = ptree_pos(real, lambda i: 252 + i * 104, lambda d: 140 + d * 38, 336)
    for fr, cap in DESCENT_FRAMES:
        nodes_now, stack_now, nxt_now, hot = states[fr[-1]]
        with steps.step(f, cap):
            for k, (t, (x, w)) in enumerate(zip(toks, tok_x)):
                eof = t[2] == "eof"
                if k == nxt_now:
                    f.rect(x - 3, TY - 3, w + 6, 36, "a", 7)
                    caret(f, x + w / 2, TY + 38)
                f.rect(x, TY, w, 30, "m f" if eof else "s fs", 5, dash=eof)
                f.text(x + w / 2, TY + 20, t[3] if not eof else "eof", "tm" if eof else "t", 12 if eof else 14,
                       "middle", 600, mono=True)
            for j, nid in enumerate(stack_now):
                y = FLOOR - (j + 1) * (SH + 6)
                top = j == len(stack_now) - 1
                f.rect(SX, y, SW_, SH, "a af" if top else "s f", 6)
                f.text(SX + 12, y + 19, nodes_now[nid][4], "ta" if top else "t", 13, weight=700 if top else 500,
                       mono=True)
            running = set(stack_now)
            show = {path_of[n] for n in nodes_now}
            by_path = {path_of[n]: n for n in nodes_now}

            def style(p, node):
                nid = by_path[p]
                if nid == hot and (nid in running or node[1]):
                    return ("a af", "ta", 700, False)
                if nid in running:
                    return ("a f", "ta", 600, False)
                return ("s fs", "t", 600, False) if node[1] else ("s f", "t", 500, False)

            def edge(pp, cp):
                return ("s", False) if nodes_now[by_path[cp]][3] else ("a", True)
            draw_ptree(f, real, pos, rsize=12, lsize=14, kinds=False, show=show, style=style, edge=edge)
    f.h = 362
    return f


# ------------------------------------------------------------------ 01.08

def gcd_syntax(at="01.08"):
    """--tree and --symbols of gcd.mote at `at`: (statements, entries)."""
    out, err, st = mote(at, gcd_text(at), "--tree")
    assert st == 0, err
    assert out == ("read i#1\nread j#2\nwhile (!= i#1 j#2)\n  if (> i#1 j#2)\n    := i#1 (- i#1 j#2)\n  else\n"
                   "    := j#2 (- j#2 i#1)\nwrite i#1\n"), out
    sout, err, st = mote(at, gcd_text(at), "--symbols")
    assert st == 0, err
    syms = symbols(sout)
    assert syms == [(1, "i", 2, 6), (2, "j", 3, 6)], syms
    return syntax_tree(out), syms


def var_style(index):
    """Entry 1 in the accent, entry 2 plain: the box class and the text class of a name."""
    return ("a af", "ta") if index == 1 else ("s fs", "t")


def two_trees():
    s = assign_tree("01.08")
    prog, syms = gcd_syntax()
    asg = prog[2][3][0][3][0]                   # while -> if -> its then statement
    assert asg == (":=", ("var", "i", 1), ("op", "-", ("var", "i", 1), ("var", "j", 2)), [], None), asg
    _, var, e, _, _ = asg
    f = Fig("f0108a", "From the parse tree to the syntax tree", 0, W)
    # left: the parse tree of 01.07, small and muted
    f.text(24, 20, f"the parse tree: {size(s)} nodes", "tm", 11.5)
    pos = ptree_pos(s, lambda i: 38 + i * 46, lambda d: 64 + d * 38, 226)
    draw_ptree(f, s, pos, rsize=10.5, lsize=12, kinds=False,
               style=lambda p, n: ("m fs", "tm", 600, False) if n[1] else ("m f", "tm", 500, False),
               edge=lambda a, b: ("m", False))
    # analysis
    f.line(268, 196, 318, 196, "s", arrow=True)
    f.text(293, 186, "analysis", "t", 11.5, "middle", 600)
    # right: the syntax tree, four nodes, and the symbol table its names point into
    f.text(338, 20, "the syntax tree: 4 nodes", "t", 11.5, weight=700)
    AX, AY = 430, 62                            # :=
    MX_, MY = 430, 124                          # -
    IX_, JX_, VY = 388, 472, 184                # the names
    TBX, TBY, TBW, RH = 360, 236, 140, 26       # the table
    # edges
    f.line(AX, AY + 14, MX_, MY - 16, "s")
    for vx in (IX_, JX_):
        dx, dy = vx - MX_, VY - 13 - MY
        dd = (dx * dx + dy * dy) ** 0.5
        f.line(MX_ + dx / dd * 16, MY + dy / dd * 16, vx, VY - 13, "s")
    # the pointers into the table
    f.path(f"M{AX - 34} {AY} H{TBX - 26} V{TBY + RH / 2} H{TBX - 3}", "a", arrow=True)
    f.line(IX_, VY + 14, IX_, TBY - 3, "a", arrow=True)
    f.path(f"M{JX_ + 20} {VY} H{TBX + TBW + 24} V{TBY + RH * 1.5} H{TBX + TBW + 3}", "a", arrow=True)
    # nodes
    f.rect(AX - 34, AY - 14, 68, 28, "s f", 6)
    f.rich(AX, AY + 5, [(":= ", "t", True), ("i#1", "ta", True)], 13, "middle", 700)
    f.circle(MX_, MY, 16, "s f")
    f.text(MX_, MY + 5, e[1], "t", 14, "middle", 700, mono=True)
    for (_, nm, ix), vx in zip(e[2:], (IX_, JX_)):
        bc, tc = var_style(ix)
        f.rect(vx - 20, VY - 13, 40, 26, bc, 5)
        f.text(vx, VY + 5, f"{nm}#{ix}", tc, 13, "middle", 700, mono=True)
    # the table
    f.rect(TBX, TBY, TBW, RH * 2, "s f", 5)
    for k, (ix, nm, ln, col) in enumerate(syms):
        y = TBY + k * RH
        bc, tc = var_style(ix)
        if ix == 1:
            f.rect(TBX + 3, y + 3, TBW - 6, RH - 6, "af", 3, sw=False)
        f.text(TBX + 14, y + 18, str(ix), tc, 13, weight=700, mono=True)
        f.text(TBX + 40, y + 18, nm, tc, 13, weight=700, mono=True)
        f.text(TBX + 72, y + 18, f"{ln}:{col}", tc, 12.5, mono=True)
    f.line(TBX, TBY + RH, TBX + TBW, TBY + RH, "m")
    f.text(TBX, TBY + RH * 2 + 20, "the symbol table", "t", 11.5, weight=700)
    f.text(TBX, TBY + RH * 2 + 36, "entry, name, where it is first given a value", "tm", 11)
    f.h = TBY + RH * 2 + 48
    return f


def gcd_tree():
    prog, syms = gcd_syntax()
    f = Fig("f0108b", "The syntax tree of gcd.mote", 0, W)
    # the tree as nodes: (kind, label parts, kids, else index); kinds: stmt, op, var
    def expr_node(e):
        if e[0] == "op":
            return ("op", e[1], [expr_node(a) for a in e[2:]], None)
        if e[0] == "var":
            return ("var", e, [], None)
        return ("num", e, [], None)

    def stmt_node(s_):
        word, var, e, body, els = s_
        kids, el = [], None
        if e is not None:
            kids.append(expr_node(e))
        kids += [stmt_node(b) for b in body]
        if els:
            el = len(kids)
            kids += [stmt_node(b) for b in els]
        return ("stmt", (word, var), kids, el)

    top = [stmt_node(s_) for s_ in prog]
    SZ = 12.5

    def width(n):
        kind, lab = n[0], n[1]
        if kind == "stmt":
            word, var = lab
            return mw(word + (f" {var[1]}#{var[2]}" if var else ""), SZ) + 16
        if kind == "op":
            return 30
        return mw(f"{lab[1]}#{lab[2]}", SZ) + 8

    GAP, TOPGAP = 11, 26
    pos, edges = {}, []
    cur = [24.0]
    ROW = [44 + d * 58 for d in range(6)]

    def place(n, path, depth):
        if not n[2]:
            w = width(n)
            x = cur[0] + w / 2
            cur[0] += w + (GAP if depth else TOPGAP)       # room for the next arrows on the top row
        else:
            xs = [place(k, path + (i,), depth + 1) for i, k in enumerate(n[2])]
            for i in range(len(n[2])):
                edges.append((path, path + (i,), i == n[3]))
            x = (xs[0] + xs[-1]) / 2
        pos[path] = (x, ROW[depth], n)
        return x

    for i, n in enumerate(top):
        place(n, (i,), 0)
    right = cur[0] - GAP
    assert right <= W - 24, right
    # the edges, then the statement list's next arrows, then the nodes
    for a, b, is_else in edges:
        (x1, y1, n1), (x2, y2, n2) = pos[a], pos[b]
        r1 = 15 if n1[0] == "op" else 13
        r2 = 15 if n2[0] == "op" else 13
        f.line(x1, y1 + r1, x2, y2 - r2, "s")
        if is_else:
            mx, my = (x1 + x2) / 2, (y1 + r1 + y2 - r2) / 2
            f.text(mx + 8, my + 2, "else", "tm", 11, weight=600)
    for i in range(len(top) - 1):
        (x1, y1, n1), (x2, _, n2) = pos[(i,)], pos[(i + 1,)]
        f.line(x1 + width(n1) / 2 + 2, y1, x2 - width(n2) / 2 - 3, y1, "m", arrow=True)
    for path, (x, y, n) in pos.items():
        kind, lab = n[0], n[1]
        w = width(n)
        if kind == "stmt":
            word, var = lab
            f.rect(x - w / 2, y - 13, w, 26, "s f", 6)
            parts = [(word, "t", True)]
            if var:
                parts += [(" ", "t", True), (f"{var[1]}#{var[2]}", var_style(var[2])[1], True)]
            f.rich(x, y + 4.5, parts, SZ, "middle", 700)
        elif kind == "op":
            f.circle(x, y, 15, "s f")
            f.text(x, y + 4.5, lab, "t", SZ, "middle", 700, mono=True)
        else:
            bc, tc = var_style(lab[2])
            f.rect(x - w / 2, y - 13, w, 26, bc, 5)
            f.text(x, y + 4.5, f"{lab[1]}#{lab[2]}", tc, SZ, "middle", 700, mono=True)
    f.text(24, 18, "the statements, in order", "tm", 11.5)
    # the symbol table, under the two reads
    TBX, TBY, TBW, RH = 24, 112, 142, 26
    f.text(TBX, TBY - 10, "the symbol table", "t", 11.5, weight=700)
    f.rect(TBX, TBY, TBW, RH * 2, "s f", 5)
    for k, (ix, nm, ln, col) in enumerate(syms):
        y = TBY + k * RH
        bc, tc = var_style(ix)
        if ix == 1:
            f.rect(TBX + 3, y + 3, TBW - 6, RH - 6, "af", 3, sw=False)
        f.text(TBX + 14, y + 18, str(ix), tc, 13, weight=700, mono=True)
        f.text(TBX + 40, y + 18, nm, tc, 13, weight=700, mono=True)
        f.text(TBX + 72, y + 18, f"{ln}:{col}", tc, 12.5, mono=True)
    f.line(TBX, TBY + RH, TBX + TBW, TBY + RH, "m")
    nuses = {1: 0, 2: 0}
    for _, (_, _, n) in pos.items():
        if n[0] == "var":
            nuses[n[1][2]] += 1
        elif n[0] == "stmt" and n[1][1]:
            nuses[n[1][1][2]] += 1
    assert nuses == {1: 7, 2: 6}, nuses
    f.text(TBX, TBY + RH * 2 + 20, f"i#1: entry 1, {nuses[1]} times", "ta", 11.5, weight=600)
    f.text(TBX, TBY + RH * 2 + 36, f"j#2: entry 2, {nuses[2]} times", "t", 11.5, weight=600)
    f.h = max(y for _, (_, y, _) in pos.items()) + 26
    return f


STATIC = [
    ("ok.mote", ["read n", "m := 1", "write n + m"]),
    ("early.mote", ["read n", "write n + m", "m := 1"]),
    ("maybe.mote", ["if 1 > 2 then", "    x := 1", "end", "write x"]),
]


def static():
    res = []
    for name, lines in STATIC:
        out, err, st = mote("01.08", "\n".join(lines) + "\n", "--tree", name=name)
        res.append((out, err, st))
    (ok_out, _, ok_st), (_, early_err, early_st), (maybe_out, _, maybe_st) = res
    assert ok_st == 0 and ok_out == "read n#1\n:= m#2 1\nwrite (+ n#1 m#2)\n", ok_out
    assert early_st == 1 and early_err == "early.mote:2:11: m is used before anything gives it a value\n", early_err
    assert maybe_st == 0 and maybe_out == "if (> 1 2)\n  := x#1 1\nwrite x#1\n", maybe_out
    sy = [symbols(mote("01.08", "\n".join(lines) + "\n", "--symbols", name=name)[0])
          for name, lines in (STATIC[0], STATIC[2])]
    assert sy == [[(1, "n", 1, 6), (2, "m", 2, 1)], [(1, "x", 2, 5)]], sy
    run_out, run_err, run_st = mote("01.09", "\n".join(STATIC[2][1]) + "\n", name="maybe.mote")
    assert run_st == 1 and run_out == "" and run_err == "maybe.mote:4:7: x has no value yet\n", run_err
    m = re.match(r"^early\.mote:(\d+):(\d+): (.*)$", early_err.strip())
    e_line, e_col, e_msg = int(m[1]), int(m[2]), m[3]
    # where each card's names are first given a value: from --symbols, and for the refused program
    # from its text (its m := 1 is the same statement as the first program's, one line lower)
    given = [[(ln, col, nm) for _, nm, ln, col in sy[0]],
             [(1, 6, "n"), (3, 1, "m")],
             [(ln, col, nm) for _, nm, ln, col in sy[1]]]
    assert STATIC[1][1][2].startswith("m :=") and STATIC[1][1][0] == "read n"

    f = Fig("f0108c", "The static rule", 0, W)
    CWD_, GAPX, CY = 184, 20, 52
    SZ, LH = 13, 22
    C = mw("x", SZ)
    heads = [("accepted", "t"), ("refused", "ta"), ("accepted", "t")]
    for k, (name, lines) in enumerate(STATIC):
        x0 = 24 + k * (CWD_ + GAPX)
        f.text(x0, 20, heads[k][0], heads[k][1], 13, weight=700)
        f.text(x0 + tw(heads[k][0], 13) + 8, 20, name, "tm", 11, mono=True)
        h = len(lines) * LH + 18
        f.rect(x0, CY - 18, CWD_, h, "s fs", 6)
        cx = x0 + 30
        for i, ln in enumerate(lines):
            y = CY + i * LH
            f.text(x0 + 18, y, str(i + 1), "tm", 10.5, "end", mono=True)
            f.code(cx, y, ln, SZ, "t")
        # where each name is first given a value
        for ln, col, nm in given[k]:
            y = CY + (ln - 1) * LH
            f.line(cx + (col - 1) * C, y + 4, cx + (col - 1 + len(nm)) * C, y + 4, "a", sw=2.5)
        # the refused use
        if k == 1:
            y = CY + (e_line - 1) * LH
            bx = cx + (e_col - 1) * C
            f.rect(bx - 3, y - 15, C + 6, 21, "a", 4)
            caret(f, bx + C / 2, y + 9)
        x_ = x0
        y0 = CY - 18 + h + 22
        if k == 0:
            f.text(x_, y0, "--tree:", "tm", 11)
            for i, ln in enumerate(ok_out.splitlines()):
                f.code(x_, y0 + 18 + i * 16, ln, 11, "t")
        elif k == 1:
            f.text(x_, y0, f"{e_line}:{e_col}:", "ta", 12, weight=700, mono=True)
            words = e_msg.split()
            f.text(x_ + mw(f"{e_line}:{e_col}: ", 12), y0, " ".join(words[:3]), "ta", 12, weight=600)
            f.text(x_, y0 + 17, " ".join(words[3:]), "ta", 12, weight=600)
            f.text(x_, y0 + 40, "m is given a value only", "tm", 11.5)
            f.text(x_, y0 + 55, "on the line below its use", "tm", 11.5)
        else:
            f.text(x_, y0, "--tree:", "tm", 11)
            for i, ln in enumerate(maybe_out.splitlines()):
                f.code(x_, y0 + 18 + i * 16, ln, 11, "t")
            yb = y0 + 18 + 3 * 16 + 8
            f.text(x_, yb, "left for the running program:", "t", 11.5, weight=600)
            f.text(x_, yb + 16, "lesson 01.09 stops it at 4:7,", "tm", 11.5)
            f.text(x_, yb + 31, "x has no value yet", "tm", 11.5)
    ly = 300
    f.line(24, ly - 4, 52, ly - 4, "a", sw=2.5)
    f.text(60, ly, "where the text first gives the name a value", "t", 11.5)
    f.h = ly + 12
    return f


# ------------------------------------------------------------------ main

FIGS = {
    "01.05-prompt": (prompt, True),
    "01.05-agree": (agree, False),
    "01.06-phases": (phases, False),
    "01.06-scan": (scan_steps, True),
    "01.06-chars-to-tokens": (chars_to_tokens, False),
    "01.07-rule-and-function": (rule_and_function, False),
    "01.07-tree": (tree_0107, False),
    "01.07-descent": (descent, True),
    "01.08-two-trees": (two_trees, False),
    "01.08-gcd-tree": (gcd_tree, False),
    "01.08-static": (static, False),
}


def main():
    want = sys.argv[1:]
    for name, (fn, stepped) in FIGS.items():
        if want and not any(name.startswith(w) for w in want):
            continue
        write(name, fn(), stepped)


if __name__ == "__main__":
    main()
