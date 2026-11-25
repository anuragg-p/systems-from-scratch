"""Figures for lang module 01, lessons 01.01 to 01.04 (plans/lang-01-lessons.md, "Figures:").

    python3 -B art/lang/figs_0101_0104.py [name-prefix ...]
        writes tracks/lang/lessons/01-introduction/figures/01.0N-*.svg

Every value drawn is from a real run of the project as the site shows it at the lesson (./learn
files lang --at NN.LL into a temporary directory, then make -s; project()), and is asserted there,
so a change to the code stops this script instead of reaching a figure. Nothing is written under
tracks/lang/ but the figures.

  01.01-five-ways         gcd on 1071 462 in the project at 01.11: by hand (the machine on gcd.s), set
                          apart, then the five ways, agree's five columns (mote0, motec's program,
                          mote's tree walk, mote -S and mote -S -O on the machine): each prints 21.
                          The lesson under each piece is archmap.OWNER's, so this figure and the map
                          cannot disagree.
  01.01-machine           gcd.s at 01.01 as the machine holds it (comments dropped, an address every
                          instruction); the registers it names, from machine.c's table; the
                          routines, from machine.c's routines[]; the moment drawn is the real one
                          before the first sub runs on 1071 462 (--trace): pc 24, ra 12
  01.01-gcd-run           stepped: --trace of gcd.s on 6 4 at 01.01, one step an instruction (17,
                          --count's number); every branch taken or not is checked against the
                          registers drawn
  01.02-c-and-assembly    programs/gcd.c and programs/gcd.s at 01.02, each line drawn checked against
                          its file; ./gcd and the machine both print 21
  01.02-growth            the chapters that add to what the language can say, each checked against
                          plans/lang-outline.md's module titles; chapter 1's words are mote0.c's
                          keywords[] at 01.03
  01.02-standard          gcd.mote, gcd.in and gcd.out at 01.02, as the files hold them; the five ways
                          to come are agree's at 01.11 (all ok on gcd), their lessons archmap.OWNER's
  01.03-stays             mote0 at 01.03 prints 21 reading gcd.mote and 1071 462 together; at 01.04
                          motec makes build/gcd with no input at all, and build/gcd prints 21
  01.03-reread            stepped: mote0 on gcd.mote with 6 4 at 01.03. mote0_reads() re-enacts
                          mote0.c's run() and skip() and gives the order in which lines are read;
                          its total must equal ./mote0 --count (25; and 88, 409, 844 on the three
                          programs' own input), and its order must equal what a copy of mote0.c that
                          prints each line it reads prints. A name is in the table from the step
                          that first gives it a value, at the top, as set() puts it at the list's
                          front
  01.04-stages            the stages of ./motec at 01.04, each run by hand: cc -E pastes rt.h in, nm
                          shows getint and putint undefined in gcd.o and defined in rt.o, the linked
                          program prints 21
  01.04-line-for-line     ./mote2c programs/gcd.mote at 01.04, line for line; each mote line's C line
                          worked out from mote2c.c's second pass and checked against the output
  01.04-when              the four decisions, checked against mote0.c (skip, find, the operators read
                          from the characters) and against the C mote2c writes

The maps are archmap.py's and module 01's cover is art/outlines/lang_art.py's. The drawing
primitives (Fig, the sanitizer check sane, steps) are the cc track's, art/cc/figlib.py, loaded
under their own module name as archmap.py loads them.
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


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_cc = _load("cc_figlib", os.path.join(ROOT, "art", "cc", "figlib.py"))
Fig, sane, steps, cw = _cc.Fig, _cc.sane, _cc.steps, _cc.cw
OWNER = _load("lang_archmap", os.path.join(HERE, "archmap.py")).OWNER

OUT = os.path.join(ROOT, "tracks", "lang", "lessons", "01-introduction", "figures")
LEARN = os.path.join(ROOT, "learn")


def sw(s, size):
    """A generous width for sans text (Figtree is narrower than this)."""
    return len(s) * size * 0.56


def lesson(key):
    """The lesson that builds a piece of the map (archmap.OWNER): one, for these pieces."""
    got = sorted(OWNER[key])
    assert len(got) == 1, (key, got)
    return got[0]


# ------------------------------------------------------------------ the project at a lesson

_TMP = []


def _tmp():
    if not _TMP:
        _TMP.append(tempfile.mkdtemp(prefix="lang-art-"))
        atexit.register(shutil.rmtree, _TMP[0], True)
    return _TMP[0]


@functools.lru_cache(None)
def project(at):
    """The project as the site shows it at lesson `at`, written by ./learn files and built, in a
    temporary directory removed when this script ends."""
    d = os.path.join(_tmp(), at)
    subprocess.run([LEARN, "files", "lang", "--at", at, d], check=True, stdout=subprocess.DEVNULL)
    r = subprocess.run(["make", "-s"], cwd=d, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"art/lang: make failed at {at}:\n{r.stdout}{r.stderr}")
    return d


def sh(d, args, stdin=None, merge=False):
    """Run args in directory d: (stdout, stderr, status); with merge, stderr goes into stdout in
    the order it was written."""
    r = subprocess.run(args, cwd=d, input=stdin, text=True, timeout=60, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT if merge else subprocess.PIPE)
    return r.stdout, r.stderr or "", r.returncode


def read(at, name):
    with open(os.path.join(project(at), name)) as fh:
        return fh.read()


def put(d, name, text):
    with open(os.path.join(d, name), "w") as fh:
        fh.write(text)
    return name


def ok(d, args, stdin=None):
    out, err, st = sh(d, args, stdin)
    assert st == 0, (args, out, err, st)
    return out


# ------------------------------------------------------------------ the machine's --trace

TRACE = re.compile(r"^(.*?)(?:\s+((?:\w+ = -?\d+)(?:  \w+ = -?\d+)*))?$")


def trace(at, prog, stdin):
    """./machine --trace on prog: ([(line, instruction text, {register: value changed})], output
    lines in order, with the index of the trace entry each came before)."""
    out, _, st = sh(project(at), ["./machine", "--trace", prog], stdin, merge=True)
    assert st == 0, out
    entries, printed = [], []
    for ln in out.splitlines():
        m = re.match(r"^\s*(\d+)  (\S.*)$", ln)
        if not m:
            printed.append((ln, len(entries)))
            continue
        t = TRACE.match(m[2])
        ch = dict((k, int(v)) for k, v in re.findall(r"(\w+) = (-?\d+)", t[2] or ""))
        entries.append((int(m[1]), t[1], ch, ln))
    return entries, printed


def listing(text):
    """A .s file as the machine reads it: [(file line, text without its comment)] for every line
    that has a label or an instruction."""
    rows = []
    for n, ln in enumerate(text.split("\n"), 1):
        s = ln.split("#")[0].rstrip()
        if s.strip():
            rows.append((n, s))
    return rows


# ------------------------------------------------------------------ mote0, re-enacted

def _tokens(s):
    toks = re.findall(r"\s*(\d+|[A-Za-z_]\w*|:=|==|!=|<=|>=|[-+*/()<>])", s)
    assert "".join(toks).replace(" ", "") == s.replace(" ", ""), s
    return toks


def _expr(toks, names):
    """An expression of mote0's grammar (expr, term, factor), C's division, on a list of tokens
    it consumes."""
    def factor():
        t = toks.pop(0)
        if t.isdigit():
            return int(t)
        if t == "(":
            v = expr()
            assert toks.pop(0) == ")"
            return v
        if t == "-":
            return -factor()
        return names[t]

    def term():
        v = factor()
        while toks and toks[0] in "*/":
            op, d = toks.pop(0), factor()
            v = v * d if op == "*" else abs(v) // abs(d) * (1 if (v < 0) == (d < 0) else -1)
        return v

    def expr():
        v = term()
        while toks and toks[0] in "+-":
            op, t = toks.pop(0), term()
            v = v + t if op == "+" else v - t
        return v
    return expr()


def _cond(s, names):
    toks = _tokens(s)
    k = next(i for i, t in enumerate(toks) if t in ("==", "!=", "<=", ">=", "<", ">"))
    a, b = _expr(toks[:k], names), _expr(toks[k + 1:], names)
    return {"==": a == b, "!=": a != b, "<=": a <= b, ">=": a >= b, "<": a < b, ">": a > b}[toks[k]], a, b


def mote0_reads(text, numbers):
    """mote0.c's run() and skip(), re-enacted on a program's text: [(line index, how, detail, the
    names after it)] for every line looked at, in order, and what it wrote. how is "comment",
    "read", "write", "assign", "while", "if", "else", "end" for a line run, "past" for a line read by
    skip() looking for an end (or an else): its detail is (first word, what skip() made of it:
    "open" a block inside, "close" the end of one, "found" what it was looking for, or "other",
    and whether an else would do)."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()                    # split() makes no line after the last line end
    n, names, out, reads, inp = len(lines), {}, [], [], list(numbers)

    def word(s):
        m = re.match(r"\s*([A-Za-z_]\w*)?", s)
        return m.group(1) or ""

    def note(at, how, detail=None):
        reads.append((at, how, detail, dict(names)))

    def skip(frm, to_else):
        depth = 0
        for at in range(frm + 1, n):
            w = word(lines[at])
            if w in ("while", "if"):
                depth += 1
                ev = "open"
            elif (w == "end" or (to_else and w == "else")) and depth == 0:
                ev = "found"
            elif w == "end":
                depth -= 1
                ev = "close"
            else:
                ev = "other"
            note(at, "past", (w, ev, to_else))
            if ev == "found":
                return at
        raise AssertionError("expected 'end'")

    opened, at = [], 0
    while at < n:
        s = lines[at].split("#")[0]
        w = word(s)
        if not s.strip():
            note(at, "comment")
            at += 1
        elif w in ("while", "if"):
            last = "do" if w == "while" else "then"
            body = s.strip()[len(w):].strip()
            assert body.endswith(last), s
            yes, a, b = _cond(body[:-len(last)].strip(), names)
            note(at, w, (body[:-len(last)].strip(), yes, a, b))
            if yes:
                opened.append(at if w == "while" else -1)
                at += 1
                continue
            to = skip(at, w == "if")
            if word(lines[to]) == "else":
                opened.append(-1)
            at = to + 1
        elif w == "else":
            note(at, "else")
            assert opened.pop() == -1
            at = skip(at, False) + 1
        elif w == "end":
            back = opened.pop()
            note(at, "end", back)
            at = back if back >= 0 else at + 1
        elif w == "read":
            name = s.split()[1]
            names[name] = inp.pop(0)
            note(at, "read", name)
            at += 1
        elif w == "write":
            v = _expr(_tokens(s.strip()[5:]), names)
            out.append(v)
            note(at, "write", v)
            at += 1
        else:
            name, e = s.split(":=")
            names[name.strip()] = _expr(_tokens(e.strip()), names)
            note(at, "assign", name.strip())
            at += 1
    assert not opened
    return lines, reads, out


def mote0_order(at, prog, stdin):
    """The line numbers a copy of mote0.c at `at` reads, in order: the copy prints each line it
    looks at (where it counts it for --count)."""
    d = os.path.join(_tmp(), f"{at}-mote0-order")
    os.makedirs(d, exist_ok=True)
    src = read(at, "mote0.c")
    assert src.count("nread++;") == 2, "mote0.c counts lines in more places than run() and skip()"
    put(d, "mote0.c", src.replace("nread++;", 'nread++; fprintf(stderr, "@%d\\n", at + 1);'))
    shutil.copy(os.path.join(project(at), prog), os.path.join(d, "prog.mote"))
    ok(d, ["cc", "-std=c11", "-O1", "-w", "-o", "mote0", "mote0.c"])
    _, err, st = sh(d, ["./mote0", "prog.mote"], stdin)
    assert st == 0, err
    return [int(x) for x in re.findall(r"^@(\d+)$", err, re.M)]


# ------------------------------------------------------------------ writing

def write(name, fig, stepped=False):
    """Write fig as figures/<name>.svg after the checks: ASCII, kept whole by the site's
    sanitizer, and, for a stepped figure, steppable within the site's limits."""
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


# ================================================================== 01.01

GCD_IN = "1071 462\n"


def five_ways():
    d = project("01.11")
    assert read("01.11", "programs/gcd.in") == GCD_IN
    runs = {
        "by hand": sh(d, ["./machine", "programs/gcd.s"], GCD_IN),
        "mote0": sh(d, ["./mote0", "programs/gcd.mote"], GCD_IN),
        "tree walk": sh(d, ["./mote", "programs/gcd.mote"], GCD_IN),
    }
    ok(d, ["./motec", "programs/gcd.mote"])
    runs["motec"] = sh(d, ["build/gcd"], GCD_IN)
    put(d, "build/five.s", ok(d, ["./mote", "-S", "programs/gcd.mote"]))
    runs["the machine"] = sh(d, ["./machine", "build/five.s"], GCD_IN)
    improved = ok(d, ["./mote", "-S", "-O", "programs/gcd.mote"])
    # module 01's cover (art/outlines/lang_art.py) shows this line as the code the compiler writes
    assert "    sub  s1, s1, s2" in improved.split("\n"), improved
    put(d, "build/five-O.s", improved)
    runs["the machine, -O"] = sh(d, ["./machine", "build/five-O.s"], GCD_IN)
    runs["by hand, at 01.01"] = sh(project("01.01"), ["./machine", "programs/gcd.s"], GCD_IN)
    for way, (out, err, st) in runs.items():
        assert (out, st) == ("21\n", 0), (way, out, err, st)
    # the five ways are agree's five columns
    agreed = re.findall(r"(\S+(?: -O)?) ok", next(ln for ln in ok(d, ["./agree"]).splitlines()
                                                  if ln.startswith("gcd ")))
    assert agreed == ["mote0", "motec", "mote", "machine", "machine -O"], agreed
    answer = "21"

    front = [("scanner", "scanner"), ("parser", "parser"), ("analysis", "semantic")]
    rows = [  # (source, [(piece, map key or None for a tool that is not ours)]): by hand, then the five
        ("gcd.s", [("the machine", "machine")]),
        ("gcd.mote", [("first interpreter", "interp")]),
        ("gcd.mote", [("translator", "translator"), ("C compiler", None), ("your computer", None)]),
        ("gcd.mote", front + [("tree walk", "treewalk")]),
        ("gcd.mote", front + [("code generator", "codegen"), ("the machine", "machine")]),
        ("gcd.mote", front + [("improver", "improver"), ("code generator", "codegen"), ("the machine", "machine")]),
    ]
    assert len(rows) - 1 == len(agreed)
    assert lesson("gcds") == lesson("machine") == "01.01" and lesson("text") == "01.02"
    R0, P, BH, SIZE = 50, 48, 24, 11
    SX, SWD = 16, 64                    # the program's column
    C0, GAP = SX + SWD + 24, 16         # where the chains start; the room an arrow takes
    CHIP_W, CHIP_X = 34, 604            # the answer's column, centred on CHIP_X
    SEP = R0 + 38                       # the line that sets the row by hand apart
    R1 = SEP + 50                       # the first of the five ways
    ys = [R0] + [R1 + k * P for k in range(len(rows) - 1)]
    H = ys[-1] + 30
    f = Fig("f0101a", "gcd by hand, and five ways from its text", H)
    f.text(SX, 20, "the program", "tm", 11)
    f.text(C0, 20, "how it is run, and under each piece the lesson that builds it", "tm", 11)
    f.text(CHIP_X, 20, "prints", "tm", 11, "middle")
    # by hand: gcd.s, written for the machine directly
    f.page(SX, ys[0] - BH / 2, SWD, BH, "a af", fold=7)
    f.text(SX + SWD / 2 - 3, ys[0] + 4, "gcd.s", "ta", 11.5, "middle", 700, mono=True)
    f.text(SX + SWD / 2, ys[0] + 24, "by hand", "ta", 10.5, "middle", 600)
    f.text((C0 + 100 + CHIP_X - CHIP_W / 2) / 2, ys[0] - 7, "written for the machine directly",
           "ta", 11, "middle", 600)
    f.line(SX, SEP, 640 - SX, SEP, "m", dash=True)
    f.text(SX, SEP + 24, "five ways, from one text in your language", "t", 11.5, weight=700)
    # the five: one gcd.mote for all of them
    top, bot = ys[1] - BH / 2, ys[-1] + BH / 2
    f.page(SX, top, SWD, bot - top, "s f", fold=9)
    mid = (top + bot) / 2
    f.text(SX + SWD / 2, mid, "gcd.mote", "t", 11, "middle", 600, mono=True)
    f.text(SX + SWD / 2, mid + 15, lesson("text"), "tm", 10.5, "middle", mono=True)
    for k, ((source, chain), y) in enumerate(zip(rows, ys)):
        hot = k == 0
        x = C0
        f.line(SX + SWD + 1, y, x - 2, y, "a" if hot else "s", arrow=True)
        if k:
            f.text(SX + SWD + 10, y - 5, str(k), "tm", 10.5, "middle", 600, mono=True)
        for i, (label, key) in enumerate(chain):
            w = sw(label, SIZE) + 8
            if key is None:          # the computer's own: hollow, dashed, not ours
                f.rect(x, y - BH / 2, w, BH, "s", 6, dash=True)
                f.text(x + w / 2, y + 4, label, "t", SIZE, "middle", 500)
                f.text(x + w / 2, y + 24, "not ours", "tm", 10.5, "middle")
            else:
                f.rect(x, y - BH / 2, w, BH, "a af" if hot else "s f", 6)
                f.text(x + w / 2, y + 4, label, "ta" if hot else "t", SIZE, "middle", 700 if hot else 500)
                f.text(x + w / 2, y + 24, lesson(key), "ta" if hot else "tm", 10.5, "middle",
                       600 if hot else None, mono=True)
            x += w
            end = x + GAP if i < len(chain) - 1 else CHIP_X - CHIP_W / 2
            f.line(x + 1, y, end - 2, y, "a" if hot else "s", arrow=True)
            x += GAP
        assert x - GAP < CHIP_X - CHIP_W / 2 - 14, (k, x)       # room for the last arrow
        f.rect(CHIP_X - CHIP_W / 2, y - 13, CHIP_W, 26, "a af" if hot else "s f", 13)
        f.text(CHIP_X, y + 5, answer, "ta" if hot else "t", 13, "middle", 700, mono=True)
    return f


def gcd_s_rows(at):
    """gcd.s as the machine holds it: [(file line, text, address or None for a label line)]."""
    rows, addr = [], 0
    for n, s in listing(read(at, "programs/gcd.s")):
        m = re.match(r"^(\w+):\s*(.*)$", s)
        assert m is None or not m[2], s           # gcd.s keeps its labels on lines of their own
        if m:
            rows.append((n, s, None))
        else:
            rows.append((n, s, addr))
            addr += 4
    return rows


def machine():
    at = "01.01"
    mc = read(at, "machine.c")
    regs = re.search(r"static const char \*regs\[32\] = \{(.*?)\};", mc, re.S)[1]
    regs = re.findall(r'"(\w+)"', regs)
    assert len(regs) == 32 and regs[0] == "zero"
    routines = re.findall(r'\[\w+\] = "(\w+)"', re.search(r"routines\[\] = \{(.*?)\};", mc, re.S)[1])
    assert routines == ["getint", "putint", "exit"], routines
    assert "if (r != ZERO)" in mc                  # what is written to zero is dropped
    rows = gcd_s_rows(at)
    used = set()
    for _, s, a in rows:
        if a is not None:
            used |= set(re.findall(r"\b\w+\b", s.strip().partition(" ")[2])) & set(regs)
    assert used == {"a0", "s1", "s2"}, used
    called = [s.split()[1] for _, s, a in rows if a is not None and s.split()[0] == "call"]
    assert sorted(set(called)) == sorted(routines), called
    entries, printed = trace(at, "programs/gcd.s", GCD_IN)
    assert [p for p, _ in printed] == ["21"]
    k = next(i for i, e in enumerate(entries) if e[1] == "sub  s1, s1, s2")
    state = {r: 0 for r in regs}
    state["ra"] = 4 * sum(1 for r in rows if r[2] is not None)
    for _, _, ch, _ in entries[:k]:
        state.update(ch)
    cur = next(r for r in rows if r[0] == entries[k][0])
    pc = cur[2]
    show = {"a0": state["a0"], "s1": state["s1"], "s2": state["s2"], "ra": state["ra"], "zero": 0}
    assert (show, pc) == ({"a0": 462, "s1": 1071, "s2": 462, "ra": 12, "zero": 0}, 24), (show, pc)
    out = read(at, "programs/gcd.in").split()

    H = 344
    f = Fig("f0101b", "The machine", H)
    # ---- registers
    f.text(16, 22, "registers", "tm", 11.5)
    ry = [52 + i * 32 for i in range(5)]
    for (name, v), y in zip(show.items(), ry):
        z = name == "zero"
        f.text(46, y + 4.5, name, "tm" if z else "t", 12.5, "end", 600, mono=True)
        f.rect(54, y - 12, 80, 24, "s fs", 5)
        f.text(94, y + 4.5, str(v), "tm" if z else "t", 12.5, "middle", 600, mono=True)
    f.text(94, ry[-1] + 26, "always 0", "tm", 10.5, "middle")
    py = ry[-1] + 58
    f.text(46, py + 4.5, "pc", "ta", 12.5, "end", 700, mono=True)
    f.rect(54, py - 12, 80, 24, "a af", 5)
    f.text(94, py + 4.5, str(pc), "ta", 12.5, "middle", 700, mono=True)
    f.text(16, py + 32, "next: pc + 4,", "ta", 11, weight=600)
    f.text(16, py + 47, "or where a jump goes", "ta", 11, weight=600)
    # ---- the program
    LX, LW, Y0, LP = 176, 248, 52, 15.5
    f.text(LX, 22, "gcd.s, as the machine holds it", "tm", 11.5)
    f.rect(LX, 32, LW, Y0 + (len(rows) - 1) * LP + 12 - 32, "s fs", 6)
    row_y = {}
    for i, (n, s, a) in enumerate(rows):
        y = Y0 + i * LP
        row_y[n] = y
        if a == pc:
            f.rect(LX + 4, y - 11, LW - 8, 15, "a af", 4)
        if a is None:
            f.code(LX + 12, y, s.strip(), 12, "tm")
        else:
            f.text(LX + 34, y, str(a), "ta" if a == pc else "tm", 11, "end", mono=True)
            f.code(LX + 44, y, s.strip(), 12, "ta" if a == pc else "t", weight=700 if a == pc else None)
    cy = row_y[cur[0]] - 4
    f.path(f"M136 {py} H156 V{cy} H{LX + 2}", "a", arrow=True)
    # ---- the routines, between the machine and the input and output
    RX, RW = 452, 72
    f.text(RX, 22, "routines of the machine", "tm", 11.5)
    calls = {}
    for n, s, a in rows:
        if a is not None and s.split()[0] == "call":
            calls.setdefault(s.split()[1], []).append((row_y[n] - 4, LX + 44 + len(s.strip()) * cw(12) + 6))
    box_y = {"getint": sum(y for y, _ in calls["getint"]) / len(calls["getint"]),
             "putint": calls["putint"][0][0], "exit": calls["exit"][0][0]}
    for r in routines:
        y = box_y[r]
        for ly, lx in calls[r]:
            f.line(lx, ly, RX - 2, y + (ly - y) * 0.35, "m")
        f.rect(RX, y - 12, RW, 24, "s f", 6)
        f.text(RX + RW / 2, y + 4.5, r, "t", 12, "middle", 600, mono=True)
    IX = 548
    y = box_y["getint"]
    f.text(IX + 34, y - 20, "input", "tm", 10.5, "middle")
    f.chip(IX + 34, y - 12, " ".join(out), "s fs", "t", 11.5, w=68)
    f.line(IX - 2, y, RX + RW + 3, y, "s", arrow=True)
    y = box_y["putint"]
    f.text(IX - 4, y - 20, "output, at the end", "tm", 10.5)
    f.chip(IX + 34, y - 12, "21", "s fs", "t", 11.5, w=40)
    f.line(RX + RW + 1, y, IX + 14 - 2, y, "s", arrow=True)
    y = box_y["exit"]
    f.chip(IX + 36, y - 12, "status 0", "s fs", "t", 11.5, w=76)
    f.line(RX + RW + 1, y, IX - 2, y, "s", arrow=True)
    return f


def gcd_run():
    at = "01.01"
    rows = gcd_s_rows(at)
    entries, printed = trace(at, "programs/gcd.s", "6 4\n")
    _, err, st = sh(project(at), ["./machine", "--count", "programs/gcd.s"], "6 4\n")
    count = int(re.search(r"(\d+) instructions", err)[1])
    assert st == 0 and count == len(entries) == 17, (count, len(entries))
    assert printed == [("2", len(entries) - 3)], printed      # before putint's own trace line
    by_line = {n: (s, a) for n, s, a in rows}
    order = [n for n, s, a in rows if a is not None]          # the instructions, in address order

    H = 330
    f = Fig("f0101c", "gcd.s on 6 and 4", H)
    LX, LW, Y0, LP = 16, 252, 50, 15
    f.rich(LX, 22, [("gcd.s", "t", True), ("  on 6 4", "tm", False)], 11.5, weight=600)
    f.rect(LX, 32, LW, Y0 + (len(rows) - 1) * LP + 11 - 32, "s fs", 6)
    row_y = {}
    for i, (n, s, a) in enumerate(rows):
        y = Y0 + i * LP
        row_y[n] = y
        f.text(LX + 26, y, str(n), "tm", 10.5, "end", mono=True)
        f.code(LX + 36, y, s, 12, "tm" if a is None else "t")
    PX = 300
    f.text(PX + 10, 22, "registers after the step", "tm", 11.5)
    reg_y = {"s1": 52, "s2": 84, "a0": 116}
    for r, y in reg_y.items():
        f.text(PX + 40, y + 4.5, r, "t", 13, "end", 600, mono=True)
        f.rect(PX + 50, y - 12, 96, 24, "s fs", 5)
    IOX = 548
    f.text(IOX, 34, "input", "tm", 10.5, "middle")
    f.chip(IOX, 40, "6 4", "s fs", "t", 12, w=60)
    f.text(IOX, 98, "output", "tm", 10.5, "middle")
    f.rect(IOX - 30, 104, 60, 24, "s fs", 12)
    f.text(PX + 10, 162, "instructions run", "tm", 11.5)
    f.text(PX + 10, 228, "what --trace prints", "tm", 11.5)

    regs = {"s1": 0, "s2": 0, "a0": 0, "ra": 4 * len(order)}
    shown_out = []
    lead = min(len(e[3]) - len(e[3].lstrip()) for e in entries)
    for k, (n, text, ch, raw) in enumerate(entries):
        s, a = by_line[n]
        assert " ".join(s.split()) == " ".join(text.split()), (s, text)
        before = dict(regs)
        regs.update(ch)
        op = text.split()[0]
        nxt = entries[k + 1][0] if k + 1 < len(entries) else None
        fall = order[order.index(n) + 1] if order.index(n) + 1 < len(order) else None
        taken = nxt is not None and nxt != fall
        if op in ("beq", "ble"):
            x_, y_ = before["s1"], before["s2"]
            assert taken == (x_ == y_ if op == "beq" else x_ <= y_), (k, text, before)
            target = text.split(",")[-1].strip()
            if op == "beq":
                cap = (f"beq: s1 and s2 are both {x_}: jump to {target}." if taken else
                       f"beq: s1 is {x_}, s2 is {y_}, not equal: no jump, on to the next line.")
            else:
                cap = (f"ble: s1 ({x_}) is not more than s2 ({y_}): jump to {target}." if taken else
                       f"ble: s1 ({x_}) is more than s2 ({y_}): no jump, on to the next line.")
        elif op == "j":
            assert taken
            cap = f"j: back to {text.split()[1]}, whatever the registers hold."
        elif op == "call" and text.split()[1] == "getint":
            cap = f"call getint: the next number of the input, {ch['a0']}, arrives in a0; ra holds the way back."
        elif op == "call" and text.split()[1] == "putint":
            shown_out.append(printed[0][0])
            cap = f"call putint: a0 ({regs['a0']}) is printed. That is the answer."
        elif op == "call":
            assert k == len(entries) - 1
            cap = f"call exit: the run ends with status a0, {regs['a0']}, after {count} instructions."
        elif op == "sub":
            (d_, v), = ch.items()
            x1, x2 = [before[r.strip()] for r in text.split(",")[1:]]
            assert v == x1 - x2, (text, before, ch)
            cap = f"sub: {d_} = {x1} - {x2} = {v}: the larger number loses the smaller."
        elif op == "mv":
            (d_, v), = ch.items()
            cap = f"mv: {d_} takes a copy of {text.split(',')[1].strip()}, {v}."
        elif op == "li":
            cap = f"li: a0 = {ch['a0']}, the status to end with."
        else:
            raise AssertionError(text)
        with steps.step(f, cap):
            y = row_y[n]
            f.rect(LX + 4, y - 11, LW - 8, 15, "a af", 4)
            f.text(LX + 26, y, str(n), "ta", 10.5, "end", 700, mono=True)
            f.code(LX + 36, y, s, 12, "ta", weight=700)
            for r, yy in reg_y.items():
                hot = r in ch
                if hot:
                    f.rect(PX + 50, yy - 12, 96, 24, "a af", 5)
                f.text(PX + 98, yy + 4.5, str(regs[r]), "ta" if hot else "t", 13, "middle", 700 if hot else 500,
                       mono=True)
            if shown_out:
                f.text(IOX, 120.5, shown_out[0], "ta" if op == "call" and "putint" in text else "t", 13, "middle",
                       700, mono=True)
            f.text(PX + 10, 194, f"{k + 1}", "ta", 20, weight=700, mono=True)
            f.text(PX + 10 + len(str(k + 1)) * cw(20) + 8, 194, f"of {count}", "tm", 12)
            f.code(PX + 10, 250, raw[lead:], 11, "t")
    return f


# ================================================================== 01.02

def c_and_assembly():
    at = "01.02"
    c = read(at, "programs/gcd.c").split("\n")
    s_text = read(at, "programs/gcd.s")
    assert "i is kept in s1 and j in s2" in s_text
    asm = [t for _, t in listing(s_text)]
    want_asm = ["main:", "    call getint", "    mv   s1, a0", "    call getint", "    mv   s2, a0", "loop:",
                "    beq  s1, s2, done", "    ble  s1, s2, smaller", "    sub  s1, s1, s2", "    j    loop",
                "smaller:", "    sub  s2, s2, s1", "    j    loop", "done:", "    mv   a0, s1", "    call putint",
                "    li   a0, 0", "    call exit"]
    assert asm == want_asm, asm
    # the C lines, at the row of the first instruction each stands for, and the rows it stands for
    c_rows = [("int main(void) {", 0, [0]), ("  long i = getint();", 1, [1, 2]), ("  long j = getint();", 3, [3, 4]),
              ("  while (i != j) {", 6, [6]), ("    if (i > j)", 7, [7]), ("      i = i - j;", 8, [8]),
              ("    else", 10, [10]), ("      j = j - i;", 11, [11]), ("  }", 12, []),
              ("  putint(i);", 14, [14, 15]), ("  return 0;", 16, [16, 17]), ("}", 18, [])]
    k = c.index("int main(void) {")
    assert [ln for ln, _, _ in c_rows] == c[k:k + len(c_rows)], c[k:]
    loop_rows = [6, 9, 12]                       # the while: its test, and the two jumps back
    assert [asm[r].split()[0] for r in loop_rows] == ["beq", "j", "j"]
    assert ok(project(at), ["./gcd"], GCD_IN) == "21\n"
    assert ok(project(at), ["./machine", "programs/gcd.s"], GCD_IN) == "21\n"
    regs = {"s1", "s2", "a0"}
    labels = {t[:-1] for t in asm if t.endswith(":")}

    Y0, P = 52, 16
    H = Y0 + 18 * P + 44
    f = Fig("f0102a", "gcd.c beside gcd.s", H)
    CX, AX = 24, 304
    f.rich(CX, 24, [("gcd.c", "t", True), (", its main", "tm", False)], 11.5, weight=600)
    f.rich(AX, 24, [("gcd.s", "t", True), (", lesson 01.01", "tm", False)], 11.5, weight=600)
    for i, t in enumerate(asm):
        spans = []
        for m in re.finditer(r"\b\w+\b:?", t):
            if m[0] in regs or m[0].rstrip(":") in labels:
                spans.append((m.start(), m.end(), "tm"))
        f.code(AX, Y0 + i * P, t, 12.5, "t", spans)
    for t, r, rs in c_rows:
        y = Y0 + r * P
        f.code(CX, y, t, 12.5, "t")
        if not rs:
            continue
        x1 = CX + len(t) * cw(12.5) + 8
        if len(rs) == 1:
            f.line(x1, y - 4, AX - 8, y - 4, "m")
        else:
            yb = Y0 + rs[-1] * P
            f.line(x1, y - 4, AX - 12, y - 4, "m")
            f.path(f"M{AX - 6} {y - 9} H{AX - 12} V{yb + 1} H{AX - 6}", "m")
    # the while's comb, on the right of the instructions
    bx = AX + 24 * cw(12.5) + 14
    ys = [Y0 + r * P - 4 for r in loop_rows]
    for i, y in enumerate(ys):
        x0 = AX + len(asm[loop_rows[i]]) * cw(12.5) + 8
        f.line(x0, y, bx, y, "m")
    f.line(bx, ys[0], bx, ys[-1], "m")
    lx = bx + 10
    f.code(lx, ys[0] + 4, "while (i != j)", 11, "t")
    f.text(lx, ys[0] + 20, "its test, and the", "tm", 11)
    f.text(lx, ys[0] + 34, "two jumps back", "tm", 11)
    f.rich(CX, H - 14, [("grey", "tm", False), (": the registers and labels chosen by hand in 01.01. "
                                               "The C compiler chooses them now.", "t", False)], 11.5)
    return f


GROWTH = [  # (chapter, what the language gains, the outline's module title, section 1.2's family)
    (1, "numbers, variables, loops", "Introduction", ("von Neumann", "imperative")),
    (3, "functions and scopes", "Names, scopes and bindings", None),
    (6, "control flow", "Control flow", None),
    (7, "types", "Type systems", None),
    (8, "records, arrays", "Composite types", None),
    (9, "exceptions, coroutines", "Subroutines and control abstraction", None),
    (10, "objects", "Data abstraction and object orientation", ("object-oriented", "imperative")),
    (11, "functional programming", "Functional languages", ("functional", "declarative")),
    (12, "logic programming", "Logic languages", ("logic", "declarative")),
    (13, "threads", "Concurrency", None),
    (14, "scripting", "Scripting languages", ("scripting", "imperative")),
]


def growth():
    with open(os.path.join(ROOT, "plans", "lang-outline.md")) as fh:
        outline = fh.read()
    titles = {int(m[1]): m[2].strip() for m in re.finditer(r"^## Module (\d\d) - (.*)$", outline, re.M)}
    for ch, _, title, _ in GROWTH:
        assert titles[ch] == title, (ch, titles.get(ch), title)
    mc = read("01.03", "mote0.c")
    kws = re.findall(r'"(\w+)"', re.search(r"keywords\[\] = \{(.*?)\};", mc)[1])
    assert kws == ["read", "write", "if", "then", "else", "end", "while", "do"], kws
    first = set(re.findall(r"^\s*([a-z]+)", read("01.03", "programs/gcd.mote"), re.M))
    assert {"read", "while", "if", "else", "end", "write"} <= first, first      # numbers, variables, a loop

    P, TOP = 27, 52
    n = len(GROWTH)
    H = TOP + (n - 1) * P + 30
    f = Fig("f0102b", "What your language can say, chapter by chapter", H)
    RL, RR = 62, 92                  # the ladder's two rails
    TX, FX = 108, 300
    f.text(16, 22, "chapter", "tm", 11)
    f.text(TX, 22, "what your language can say", "tm", 11)
    f.text(FX, 22, "section 1.2's family, where it arrives", "tm", 11)
    ys = [TOP + (n - 1 - i) * P for i in range(n)]
    f.line(RL, TOP - 16, RL, ys[0] + 14, "s")
    f.line(RR, TOP - 16, RR, ys[0] + 14, "s")
    for (ch, what, _, fam), y in zip(GROWTH, ys):
        hot = ch == 1
        f.line(RL, y - 4, RR, y - 4, "a" if hot else "s", sw=3 if hot else 2)
        f.text(RL - 12, y, str(ch), "ta" if hot else "t", 12.5, "end", 700 if hot else 500, mono=True)
        f.text(TX, y, what, "ta" if hot else "t", 12.5, weight=700 if hot else 500)
        if fam:
            name, group = fam
            w = sw(name, 11) + 16
            f.rect(FX, y - 14.5, w, 20, "a af" if hot else "s f", 10)
            f.text(FX + w / 2, y - 0.5, name, "ta" if hot else "t", 11, "middle", 600)
            f.text(FX + w + 8, y - 0.5, group, "ta" if hot else "tm", 11)
    return f


def standard():
    at = "01.02"
    prog = read(at, "programs/gcd.mote").rstrip("\n").split("\n")
    gin = read(at, "programs/gcd.in")
    gout = read(at, "programs/gcd.out")
    assert gin == GCD_IN and gout == "21\n"
    agree = ok(project("01.11"), ["./agree"])
    row = next(ln for ln in agree.splitlines() if ln.startswith("gcd "))
    ways = re.findall(r"(\S+(?: -O)?) ok", row)
    assert ways == ["mote0", "motec", "mote", "machine", "machine -O"], row
    slots = [(lesson("interp"), "first interpreter"), (lesson("translator"), "translator to C"),
             (lesson("treewalk"), "tree walk"), (lesson("codegen"), "code generator"),
             (lesson("improver"), "improver")]
    assert [s for s, _ in slots] == ["01.03", "01.04", "01.09", "01.10", "01.11"]

    H = 326
    f = Fig("f0102c", "The standard: a program, its input, its output", H)
    size, lh = 11, 14.5
    PW = max(len(ln) for ln in prog) * cw(size) + 30
    PX, PY = 16, 32
    PH = 24 + len(prog) * lh
    f.page(PX, PY, PW, PH, "s fs", fold=10)
    f.text(PX + 10, PY - 10, "gcd.mote", "t", 12, weight=700, mono=True)
    for i, ln in enumerate(prog):
        f.code(PX + 10, PY + 20 + i * lh, ln, size, "tm" if ln.lstrip().startswith("#") else "t")
    CX, CWD = PX + PW + 32, 640 - 16 - (PX + PW + 32)
    f.text(CX, PY - 10, "gcd.in", "t", 12, weight=700, mono=True)
    f.page(CX, PY, CWD, 34, "s fs", fold=9)
    f.code(CX + 10, PY + 21.5, gin.strip(), 13, "t")
    OY = PY + 72
    f.text(CX, OY - 10, "gcd.out", "ta", 12, weight=700, mono=True)
    f.page(CX, OY, CWD, 34, "a af", fold=9)
    f.code(CX + 10, OY + 21.5, gout.strip(), 13, "ta", weight=700)
    # the five ways to come, all pointing at gcd.out
    SY, SH, gap = 252, 40, 10
    sw_ = (640 - 32 - gap * 4) / 5
    BUS = SY - 16
    bus_x = CX + CWD - 34
    for i, (lid, name) in enumerate(slots):
        x = 16 + i * (sw_ + gap)
        f.rect(x, SY, sw_, SH, "m f", 6, dash=True)
        f.text(x + sw_ / 2, SY + 16, lid, "t", 12, "middle", 600, mono=True)
        f.text(x + sw_ / 2, SY + 31, name, "tm", 11, "middle")
        f.line(x + sw_ / 2, SY - 2, x + sw_ / 2, BUS, "a")
    f.line(16 + sw_ / 2, BUS, bus_x, BUS, "a")
    f.line(bus_x, BUS, bus_x, OY + 34 + 3, "a", arrow=True)
    f.text(bus_x - 10, (BUS + OY + 34) / 2 + 4, "what each prints", "ta", 11, "end", 600)
    f.text(bus_x - 10, (BUS + OY + 34) / 2 + 19, "must be this, byte for byte", "ta", 11, "end", 600)
    f.text(16, H - 12, "the ways to come, each running gcd.mote on gcd.in, and the lesson that builds it",
           "tm", 11)
    return f


# ================================================================== 01.03

def stays():
    d3, d4 = project("01.03"), project("01.04")
    assert ok(d3, ["./mote0", "programs/gcd.mote"], GCD_IN) == "21\n"
    ok(d4, ["./motec", "programs/gcd.mote"], "")              # no input at all: it only translates
    assert os.path.isfile(os.path.join(d4, "build", "gcd"))
    assert ok(d4, ["build/gcd"], GCD_IN) == "21\n"
    nums = GCD_IN.strip()

    H = 282
    f = Fig("f0103a", "An interpreter stays", H)
    BH = 30
    # ---- above: the interpreter, this lesson
    f.text(16, 22, "lesson 01.03: an interpreter", "ta", 11.5, weight=700)
    y = 66
    f.page(24, y - 13, 80, 26, "s f", fold=8)
    f.text(60, y + 4, "gcd.mote", "t", 11.5, "middle", 600, mono=True)
    MX, MW = 148, 104
    f.line(106, y, MX - 2, y, "a", arrow=True)
    f.rect(MX, y - BH / 2 - 4, MW, BH + 8, "a af", 8)
    f.text(MX + MW / 2, y + 0, "mote0", "ta", 13, "middle", 700, mono=True)
    f.text(MX + MW / 2, y + 14, "runs the text", "ta", 10.5, "middle", 600)
    iy = y + 52
    f.chip(MX + MW / 2, iy - 12, nums, "s fs", "t", 11.5, w=80)
    f.line(MX + MW / 2, iy - 14, MX + MW / 2, y + BH / 2 + 7, "a", arrow=True)
    AX = 596
    f.line(MX + MW + 1, y, AX - 22, y, "a", arrow=True)
    f.rect(AX - 20, y - 13, 40, 26, "a af", 13)
    f.text(AX, y + 5, "21", "ta", 13, "middle", 700, mono=True)
    f.text((MX + MW + AX - 20) / 2, y - 8, "mote0 stays: it is what runs", "ta", 11, "middle", 600)
    f.text(MX + MW / 2 + 50, iy + 4, "the input goes in with the program", "ta", 11, weight=600)
    # ---- below, muted: lesson 01.04's translator
    top = 166
    f.line(16, top - 18, 624, top - 18, "m", dash=True)
    f.text(16, top, "lesson 01.04: a translator", "tm", 11.5, weight=700)
    y = top + 44
    f.page(24, y - 13, 80, 26, "m f", dash=True, fold=8)
    f.text(60, y + 4, "gcd.mote", "tm", 11.5, "middle", 600, mono=True)
    f.line(106, y, MX - 2, y, "m", arrow=True, dash=True)
    f.rect(MX, y - BH / 2 - 4, MW, BH + 8, "m f", 8, dash=True)
    f.text(MX + MW / 2, y + 0, "motec", "tm", 13, "middle", 700, mono=True)
    f.text(MX + MW / 2, y + 14, "translates", "tm", 10.5, "middle")
    DX = 296                              # first the translation; later, the run
    f.line(DX, top + 14, DX, H - 8, "m", dash=True)
    f.text(DX - 8, top + 14, "first", "tm", 11, "end")
    f.text(DX + 8, top + 14, "later", "tm", 11)
    GX, GW = 380, 96
    f.line(MX + MW + 1, y, GX - 2, y, "m", arrow=True, dash=True)
    f.page(GX, y - 15, GW, 30, "m f", dash=True, fold=8)
    f.text(GX + GW / 2, y + 4, "build/gcd", "tm", 11.5, "middle", 600, mono=True)
    iy = y + 50
    f.chip(GX + GW / 2, iy - 12, nums, "m f", "tm", 11.5, w=80)
    f.line(GX + GW / 2, iy - 14, GX + GW / 2, y + 17, "m", arrow=True, dash=True)
    f.line(GX + GW + 1, y, AX - 22, y, "m", arrow=True, dash=True)
    f.rect(AX - 20, y - 13, 40, 26, "m f", 13, dash=True)
    f.text(AX, y + 5, "21", "tm", 13, "middle", 700, mono=True)
    f.text(MX + MW / 2, iy + 2, "gone before the run", "tm", 11, "middle")
    return f


def _mote_caption(lines, at, how, detail, names, k, total, before):
    ln = at + 1
    text = " ".join(lines[at].split())
    if how == "comment":
        return f"Line {ln} is a comment: read, and nothing to do."
    if how == "read" and detail not in before:
        where = ("goes into the table of names" if not before else
                 "goes in at the top: the table is a list, and a new name goes at its front")
        return f"Line {ln}, read {detail}: {detail} is {names[detail]}. {detail} is new, so it {where}."
    if how == "read":
        return f"Line {ln}, read {detail}: {detail} is now {names[detail]}."
    if how in ("while", "if"):
        cond, yes, a, b = detail
        shown = re.sub(r"\b([a-z_]\w*)\b", lambda m: str(names[m[1]]), cond)
        if how == "while":
            return (f"Line {ln}: {cond} is {shown}, true: into the loop's lines." if yes else
                    f"Line {ln}: {cond} is {shown}, false: mote0 reads ahead for the loop's end.")
        return (f"Line {ln}: {cond} is {shown}, true: the lines after then run." if yes else
                f"Line {ln}: {cond} is {shown}, false: mote0 reads ahead for the else.")
    if how == "assign":
        assert detail in before, (ln, detail)     # every name drawn is first given a value by read
        return f"Line {ln}, {text}: each name found in the table by its letters; {detail} is now {names[detail]}."
    if how == "else":
        return f"Line {ln}, else: the then lines are done, so mote0 reads ahead past the else lines."
    if how == "end":
        return (f"Line {ln}, end of the while: back to line {detail + 1}, whose condition is read again."
                if detail >= 0 else f"Line {ln}, end of the if: on to the next line.")
    if how == "write":
        return f"Line {ln}, write i: prints {detail}. {total} lines read, for a program of {len(lines)}."
    assert how == "past"
    w, ev, to_else = detail
    if ev == "found":
        return (f"Line {ln} is the else it was looking for: the lines after it run." if w == "else" else
                f"Line {ln} is the end it was looking for: on to line {ln + 1}.")
    if ev == "open":
        return f"Line {ln} starts an {w} inside, counted: the next end is that {w}'s, not the one wanted."
    if ev == "close":
        return f"Line {ln} is the end of the block inside, counted off: still looking."
    return f"Line {ln} is read only to pass over it: mote0 is looking for an end{' or an else' if to_else else ''}."


def reread():
    at = "01.03"
    d = project(at)
    text = read(at, "programs/gcd.mote")
    lines, reads, out = mote0_reads(text, [6, 4])
    count = int(re.search(r"(\d+) lines read", sh(d, ["./mote0", "--count", "programs/gcd.mote"], "6 4\n")[1])[1])
    assert len(reads) == count == 25 and out == [2], (len(reads), count, out)
    assert [a + 1 for a, *_ in reads] == mote0_order(at, "programs/gcd.mote", "6 4\n")
    for p, want in (("gcd", 88), ("sum", 409), ("primes", 844)):
        inp = read(at, f"programs/{p}.in")
        o, err, st = sh(d, ["./mote0", "--count", f"programs/{p}.mote"], inp)
        got = int(re.search(r"(\d+) lines read", err)[1])
        _, r_, out_ = mote0_reads(read(at, f"programs/{p}.mote"), [int(x) for x in inp.split()])
        assert st == 0 and got == len(r_) == want and "".join(f"{v}\n" for v in out_) == o, (p, got, len(r_))

    H = 304
    f = Fig("f0103b", "mote0 reading gcd.mote", H)
    LX, LW, Y0, LP, SIZE = 16, 404, 54, 19, 11
    f.rich(LX, 22, [("gcd.mote", "t", True), ("  on 6 4", "tm", False)], 11.5, weight=600)
    f.rect(LX, 34, LW, Y0 + 10 * LP + 12 - 34, "s fs", 6)
    for i, ln in enumerate(lines):
        y = Y0 + i * LP
        f.text(LX + 22, y, str(i + 1), "tm", 10.5, "end", mono=True)
        f.code(LX + 32, y, ln, SIZE, "tm" if ln.lstrip().startswith("#") else "t")
    # The table of names is mote0's list: set() adds a name the first time it is given a value, at
    # the front. So a name is drawn from the step that first gives it a value, newest at the top.
    setter = re.search(r"static void set\(.*?\n\}", read(at, "mote0.c"), re.S)[0]
    assert "(Name){s, len, 0, names};" in setter and "names = n;" in setter, setter
    TX = LX + LW + 12
    f.text(TX + 22, 22, "times read", "tm", 11, "middle")
    RX = 512
    f.text(RX, 22, "table of names", "tm", 11)
    slot_y = [56, 84]
    assert len(reads[-1][3]) <= len(slot_y)
    f.text(RX, 130, "lines read", "tm", 11)
    f.text(RX, 196, "output", "tm", 11)
    f.rect(RX, 204, 60, 24, "s fs", 12)
    ly = H - 16
    f.rect(LX, ly - 11, 22, 14, "a af", 4)
    f.text(LX + 30, ly, "the line runs", "t", 11)
    f.rect(LX + 130, ly - 11, 22, 14, "a", 4, dash=True)
    f.text(LX + 160, ly, "read only to pass over it", "t", 11)

    tally = [0] * len(lines)
    printed = []
    for k, (at_, how, detail, names) in enumerate(reads):
        tally[at_] += 1
        if how == "write":
            printed.append(str(detail))
        before = reads[k - 1][3] if k else {}
        cap = _mote_caption(lines, at_, how, detail, names, k, len(reads), before)
        with steps.step(f, cap):
            y = Y0 + at_ * LP
            past = how == "past"
            f.rect(LX + 4, y - 13, LW - 8, 18, "a" if past else "a af", 4, dash=past)
            f.text(LX + 22, y, str(at_ + 1), "ta", 10.5, "end", 700, mono=True)
            f.code(LX + 32, y, lines[at_], SIZE, "ta", weight=700)
            for i, c in enumerate(tally):
                if not c:
                    continue
                yy = Y0 + i * LP
                hot = i == at_
                for t in range(c):
                    x = TX + 4 + t * 6
                    f.line(x, yy - 10, x, yy + 1, "a" if hot and t == c - 1 else "s", sw=2)
                f.text(TX + 4 + c * 6 + 6, yy, str(c), "ta" if hot else "tm", 10.5, weight=700 if hot else None,
                       mono=True)
            if not names:
                f.text(RX + 8, slot_y[0] + 4.5, "empty", "tm", 11)
            for nm, yy in zip(reversed(list(names)), slot_y):       # the list's order, newest first
                hot = how in ("read", "assign") and detail == nm
                f.text(RX + 8, yy + 4.5, nm, "ta" if hot else "t", 13, "middle", 600, mono=True)
                f.rect(RX + 22, yy - 12, 80, 24, "a af" if hot else "s fs", 5)
                f.text(RX + 62, yy + 4.5, str(names[nm]), "ta" if hot else "t", 13, "middle", 700 if hot else 500,
                       mono=True)
            f.text(RX, 160, str(k + 1), "ta", 20, weight=700, mono=True)
            if printed:
                f.text(RX + 30, 220.5, printed[0], "ta" if how == "write" else "t", 13, "middle", 700, mono=True)
    return f


# ================================================================== 01.04

def stages():
    at = "01.04"
    d = project(at)
    motec = read(at, "motec")
    for step in ('"$here/mote2c" "$1" > "build/$name.c"',
                 '${CC:-cc} -O1 -fwrapv -I"$here" -c -o "build/$name.o" "build/$name.c"',
                 '${CC:-cc} -o "build/$name" "build/$name.o" "$here/rt.o"'):
        assert step in motec, step
    c = ok(d, ["./mote2c", "programs/gcd.mote"])
    ok(d, ["./motec", "programs/gcd.mote"])
    assert read(at, "build/gcd.c") == c
    pre = ok(d, ["cc", "-E", "-I.", "build/gcd.c"])
    assert "long getint(void);" in pre and "void putint(long n);" in pre and "#include" not in pre
    ok(d, ["cc", "-S", "-O1", "-fwrapv", "-I.", "-o", "build/stages.s", "build/gcd.c"])
    ok(d, ["cc", "-c", "-o", "build/stages.o", "build/stages.s"])
    nm_o, nm_rt = ok(d, ["nm", "build/stages.o"]), ok(d, ["nm", "rt.o"])
    for r in ("getint", "putint"):
        assert re.search(rf"^\s+U _?{r}$", nm_o, re.M), nm_o
        assert re.search(rf"^[0-9a-f]+ T _?{r}$", nm_rt, re.M), nm_rt
    ok(d, ["cc", "-o", "build/stages", "build/stages.o", "rt.o"])
    assert ok(d, ["build/stages"], GCD_IN) == ok(d, ["build/gcd"], GCD_IN) == "21\n"

    H = 284
    f = Fig("f0104a", "From gcd.mote to a program", H)
    f.rich(16, 22, [("./motec", "t", True), (" runs every stage below, one after another", "tm", False)], 11.5)
    BH, PH, GAP = 40, 34, 32
    Y1, Y2 = 74, 176

    def tool(x, y, name, cmd, ours=False):
        w = max(sw(name, 12) + 22, len(cmd) * cw(10.5) + 18, 78)
        if ours:
            f.rect(x, y - BH / 2, w, BH, "a af", 8)
            f.text(x + w / 2, y - 2, name, "ta", 12.5, "middle", 700, mono=True)
            f.text(x + w / 2, y + 13, cmd, "ta", 10.5, "middle", 600)
        else:
            f.rect(x, y - BH / 2, w, BH, "s", 8, dash=True)
            f.text(x + w / 2, y - 2, name, "t", 12, "middle", 600)
            f.text(x + w / 2, y + 13, cmd, "tm", 10.5, "middle", mono=True)
        return w

    def file(x, y, name, mono=True):
        w = (len(name) * cw(11.5) if mono else sw(name, 11.5)) + 26
        f.page(x, y - PH / 2, w, PH, "s f", fold=8)
        f.text(x + w / 2 - 3, y + 4, name, "t", 11.5, "middle", 600, mono=mono)
        return w

    # row 1, left to right
    x = 24
    w = file(x, Y1, "gcd.mote")
    f.line(x + w + 1, Y1, x + w + GAP - 2, Y1, "a", arrow=True)
    x += w + GAP
    w = tool(x, Y1, "mote2c", "translator", ours=True)
    f.line(x + w + 1, Y1, x + w + GAP - 2, Y1, "a", arrow=True)
    x += w + GAP
    w = file(x, Y1, "build/gcd.c")
    f.line(x + w + 1, Y1, x + w + GAP - 2, Y1, "s", arrow=True)
    x += w + GAP
    w = tool(x, Y1, "preprocessor", "cc -E")
    f.line(x + w + 1, Y1, x + w + GAP - 2, Y1, "s", arrow=True)
    x += w + GAP
    w = tool(x, Y1, "compiler", "cc -S")
    cx = x + w / 2
    assert x + w <= 624, x + w
    f.line(cx, Y1 + BH / 2 + 1, cx, Y2 - PH / 2 - 2, "s", arrow=True)
    # row 2, right to left, under the compiler
    aw = sw("assembly", 11.5) + 26
    xa = cx - aw / 2
    file(xa, Y2, "assembly", mono=False)
    x = xa
    for kind, name, cmd in (("tool", "assembler", "cc -c"), ("file", "gcd.o", None), ("tool", "linker", "cc"),
                            ("file", "build/gcd", None)):
        w = (max(sw(name, 12) + 22, len(cmd) * cw(10.5) + 18, 78) if kind == "tool"
             else len(name) * cw(11.5) + 26)
        f.line(x - 1, Y2, x - GAP + 2, Y2, "s", arrow=True)
        x -= GAP + w
        if kind == "tool":
            tool(x, Y2, name, cmd)
        else:
            file(x, Y2, name)
        if name == "gcd.o":
            f.text(x + w / 2, Y2 + PH / 2 + 16, "getint, putint", "tm", 10.5, "middle", mono=True)
            f.text(x + w / 2, Y2 + PH / 2 + 30, "still missing", "tm", 10.5, "middle")
        if name == "linker":
            lx = x + w / 2
    assert x >= 16, x
    ry = Y2 + 68
    rw = len("rt.o") * cw(11.5) + 26
    f.page(lx - rw / 2, ry - PH / 2, rw, PH, "s f", fold=8)
    f.text(lx - 3, ry + 4, "rt.o", "t", 11.5, "middle", 600, mono=True)
    f.line(lx, ry - PH / 2 - 1, lx, Y2 + BH / 2 + 2, "s", arrow=True)
    f.rich(lx - rw / 2 - 10, ry + 4, [("has ", "tm", False), ("getint, putint", "t", True)], 10.5, "end")
    return f


def line_for_line():
    at = "01.04"
    mote = read(at, "programs/gcd.mote").rstrip("\n").split("\n")
    c = ok(project(at), ["./mote2c", "programs/gcd.mote"]).rstrip("\n").split("\n")
    m2c = read(at, "mote2c.c")
    assert 'printf("#include \\"rt.h\\"\\n\\nint main(void) {\\n");' in m2c
    assert 'printf("    long %.*s = 0;\\n", lens[k], names[k]);' in m2c
    # mote2c's second pass: after the header and the declarations, a line of C for each line of the
    # program, but a line that is only a comment, which gives none
    names = []
    for ln in mote:
        m = re.match(r"^\s*(?:read\s+([a-z_]\w*)|([a-z_]\w*)\s*:=)", ln)
        if m and (m[1] or m[2]) not in names:
            names.append(m[1] or m[2])
    head = ["#include \"rt.h\"", "", "int main(void) {"] + [f"    long {n} = 0;" for n in names]
    assert c[:len(head)] == head and c[-2:] == ["    return 0;", "}"], c
    pairs, k = [], len(head)
    for i, ln in enumerate(mote):
        if ln.strip().startswith("#"):
            continue
        pairs.append((i, k))
        k += 1
    assert k == len(c) - 2, (k, len(c))
    want = {"read": r"^\s*(\w+) = getint\(\);$", "write": r"^\s*putint\(.*\);$", "while": r"^\s*while \(.*\) \{$",
            "if": r"^\s*if \(.*\) \{$", "else": r"^\s*\} else \{$", "end": r"^\s*\}$"}
    for i, j in pairs:
        w = mote[i].split()[0]
        assert re.match(want.get(w, r"^\s*\w+ = .*;$"), c[j]), (mote[i], c[j])
        assert len(mote[i]) - len(mote[i].lstrip()) + 4 == len(c[j]) - len(c[j].lstrip()), (mote[i], c[j])
    decl = list(range(3, len(head)))

    Y0, P, SIZE = 52, 17, 12
    shift = pairs[0][1] - pairs[0][0] - 1        # each line of gcd.mote one row above its C
    H = Y0 + (len(c) - 1) * P + 22
    f = Fig("f0104b", "gcd.mote and its C, line for line", H)
    MX, CX = 24, 330
    f.rich(MX, 24, [("gcd.mote", "t", True)], 11.5, weight=600)
    f.rich(CX, 24, [("./mote2c", "t", True), (" writes", "tm", False)], 11.5, weight=600)
    lim = (CX - 170 - MX) / cw(SIZE)
    for i, ln in enumerate(mote):
        y = Y0 + (i + shift) * P
        if ln.strip().startswith("#"):
            short = ln[:ln.index(":") + 1] + " ..." if len(ln) > lim else ln
            f.code(MX, y, short, SIZE, "tm")
            f.text(MX + len(short) * cw(SIZE) + 14, y, "a comment: no C at all", "tm", 11)
        else:
            assert len(ln) <= lim, ln
            f.code(MX, y, ln, SIZE, "t")
    frame = {0, 1, 2, len(c) - 2, len(c) - 1}
    for j, ln in enumerate(c):
        y = Y0 + j * P
        cls = "a" if j in decl else ("tm" if j in frame else "t")
        f.code(CX, y, ln, SIZE, "ta" if j in decl else cls, weight=600 if j in decl else None)
    x0 = MX + max(len(mote[i]) for i, _ in pairs) * cw(SIZE) + 10
    for i, j in pairs:
        y1, y2 = Y0 + (i + shift) * P - 4, Y0 + j * P - 4
        f.line(x0, y1, CX - 10, y2, "m")
    bx = CX + max(len(c[j]) for j in decl) * cw(SIZE) + 12
    yt, yb = Y0 + decl[0] * P - 13, Y0 + decl[-1] * P + 4
    f.path(f"M{bx} {yt} H{bx + 6} V{yb} H{bx}", "a")
    f.text(bx + 14, (yt + yb) / 2 + 4, "from the first pass", "ta", 11.5, weight=700)
    return f


def when():
    m0 = read("01.03", "mote0.c")
    for frag in ("int to = skip(at, !loop);",          # where the loop ends: read for, during the run
                 "Name *n = find(w, len);",            # where i is: looked up by its letters, each use
                 "*p == '+' || *p == '-'",             # what - means: read from the characters, each time
                 "(op == '+' ? (unsigned long)v + t : (unsigned long)v - t)"):   # the subtraction
        assert frag in m0, frag
    _, reads, _ = mote0_reads(read("01.03", "programs/gcd.mote"), [1071, 462])
    sub_line = next(i for i, ln in enumerate(read("01.03", "programs/gcd.mote").split("\n")) if "i := i - j" in ln)
    runs = sum(1 for a, how, *_ in reads if a == sub_line and how == "assign")
    assert runs > 1, runs
    c = ok(project("01.04"), ["./mote2c", "programs/gcd.mote"])
    for frag in ("long i = 0;", "while (i != j) {", "i = i - j;"):
        assert frag in c, frag

    decisions = [[("where the loop ends", None)], [("where ", None), ("i", "mono"), (" is", None)],
                 [("what ", None), ("-", "mono"), (" means here", None)], [("the subtraction itself", None)]]
    H = 318
    f = Fig("f0104c", "What is decided when", H)
    L1, L2, LW = 158, 400, 224         # the lanes
    HY = 24
    f.text(L1 + LW / 2 - 6, HY, "before the run", "t", 12, "middle", 700)
    f.text(L2 + LW / 2, HY, "during the run, each time round", "t", 12, "middle", 700)
    TOP = 36
    R1, R2, RH = TOP, TOP + 140, 132
    for lx in (L1, L2):
        f.rect(lx - 6, TOP, LW, R2 + RH - TOP, "m fs", 10)
    f.line(16, R2 - 4, 624, R2 - 4, "m")

    pw = max(sum(len(t) * (cw(11.5) if k_ else 11.5 * 0.56) for t, k_ in dec) for dec in decisions) + 22

    def pill(cx, y, parts, hot):
        w = pw
        f.rect(cx - w / 2, y, w, 24, "a af" if hot else "s f", 12)
        f.rich(cx, y + 16, [(t, "ta" if hot else "t", k_ == "mono") for t, k_ in parts], 11.5, "middle",
               600 if hot else 500)

    # row 1: mote0
    f.text(16, R1 + 30, "mote0", "t", 13.5, weight=700, mono=True)
    f.text(16, R1 + 47, "lesson 01.03", "tm", 11)
    f.text(L1 + LW / 2 - 6, R1 + 70, "nothing", "tm", 12, "middle")
    for i, dec in enumerate(decisions):
        pill(L2 + LW / 2 - 6, R1 + 12 + i * 29, dec, False)
    # row 2: compiled
    f.text(16, R2 + 26, "build/gcd", "t", 13.5, weight=700, mono=True)
    f.text(16, R2 + 43, "mote2c, then the", "tm", 11)
    f.text(16, R2 + 57, "C compiler: 01.04", "tm", 11)
    for i, dec in enumerate(decisions[:3]):
        pill(L1 + LW / 2 - 6, R2 + 12 + i * 29, dec, True)
    pill(L2 + LW / 2 - 6, R2 + 12 + 3 * 29, decisions[3], False)
    return f


FIGS = [
    ("01.01-five-ways", five_ways, False),
    ("01.01-machine", machine, False),
    ("01.01-gcd-run", gcd_run, True),
    ("01.02-c-and-assembly", c_and_assembly, False),
    ("01.02-growth", growth, False),
    ("01.02-standard", standard, False),
    ("01.03-stays", stays, False),
    ("01.03-reread", reread, True),
    ("01.04-stages", stages, False),
    ("01.04-line-for-line", line_for_line, False),
    ("01.04-when", when, False),
]


def main(argv):
    for name, fn, stepped in FIGS:
        if argv and not any(name.startswith(a) for a in argv):
            continue
        write(name, fn(), stepped)


if __name__ == "__main__":
    main(sys.argv[1:])
