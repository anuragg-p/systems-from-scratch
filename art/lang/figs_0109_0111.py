"""Figures for lang lessons 01.09 to 01.11: the tree walk, target code, code improvement.

    python3 -B art/lang/figs_0109_0111.py [name-prefix ...]
                writes tracks/lang/lessons/01-introduction/figures/01.09-* to 01.11-*

Every tree, line, value and count drawn here comes from a run of the project as the site shows it
at the lesson (./learn files lang --at 01.LL into a temporary directory, make -s), and is asserted,
so a change to the code stops this script instead of leaving a figure that no longer matches:

  01.09-walk           stepped: ./mote --tree on gcd.mote, parsed back into a tree and walked here
                       on 6 4; the walk (every node visited, every test's result, every value
                       given) is asserted against a scratch copy of interp.c that reports them,
                       and its output against ./mote's, 2
  01.09-per-pass       one pass of gcd's loop on 1071 462: the lines mote0 reads and the names it
                       searches for, from a scratch copy of mote0.c that reports each (its total
                       held to ./mote0 --count, 88); the nodes the walker visits, from the copy of
                       interp.c above; every pass of each kind (i > j, and the other) the same
  01.10-slots          --symbols, the offsets and the frame from ./mote -S, sp and the two slots
                       from ./machine --trace of it on 6 4
  01.10-statement      stepped: the four lines ./mote -S writes for i := i - j; gen() re-enacts
                       gen.c and must write the whole listing as ./mote -S does, which ties each
                       line to its node; t0, t1 and the slots after each from ./machine --trace
                       on 6 4 (the statement's first run)
  01.10-while          gcd's loop beside its lines of ./mote -S, each source line beside the code
                       gen() says it became; the branch out and the jump back
  01.11-before-after   ./mote -S and ./mote -S -O of gcd.mote side by side, a row a statement
                       (gen() again, for both); the loads and stores marked; ./machine --count of
                       each on 1071 462, 142 and 61
  01.11-who-gets-a-register
                       primes.mote's variables, their counts and registers from a scratch copy of
                       improve.c that reports them (held to the name#k in --tree and to the -O
                       listing); the note for more than eleven from a 13-variable program run here
  01.11-three-counts   ./machine --count on gcd.s by hand, ./mote -S and ./mote -S -O of gcd.mote,
                       on 1071 462: 53, 142, 61, each printing 21; the 8 the improved program runs
                       beyond the hand-written one counted in its --trace (j .L4, a jump to a jump)

The drawing primitives (Fig, the sanitizer check sane, the stepped-figure check) are the cc
track's, art/cc/figlib.py, loaded under their own module name as art/lang/archmap.py loads them.
Everything else is in this file. Nothing is written under tracks/lang/ but the figures.
"""
import collections
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
Fig, sane, steps, cw, tw, fmt = _cc.Fig, _cc.sane, _cc.steps, _cc.cw, _cc.tw, _cc.fmt

OUT = os.path.join(ROOT, "tracks", "lang", "lessons", "01-introduction", "figures")
GCD_IN = "1071 462\n"
SMALL_IN = "6 4\n"


# ------------------------------------------------------------------ the project at a lesson

_TMP = []


def _scratch(tag):
    if not _TMP:
        _TMP.append(tempfile.mkdtemp(prefix="lang-art-"))
    d = os.path.join(_TMP[0], tag)
    shutil.rmtree(d, ignore_errors=True)
    return d


def _make(d):
    r = subprocess.run(["make", "-s"], cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"art/lang: make failed in {d}:\n{r.stdout}{r.stderr}")


@functools.lru_cache(None)
def project(at):
    """The project as the site shows it at lesson `at`, written by ./learn files and built."""
    d = _scratch(at)
    subprocess.run([os.path.join(ROOT, "learn"), "files", "lang", "--at", at, d], check=True,
                   stdout=subprocess.DEVNULL)
    _make(d)
    return d


_PATCHED = {}


def patched(at, tag, edits):
    """A built scratch copy of the project at `at` with each (file, old, new) edit made; old must
    occur exactly once. For a run that reports what the code does inside. Made once per tag."""
    if (at, tag) in _PATCHED:
        return _PATCHED[at, tag]
    d = _scratch(f"{at}-{tag}")
    shutil.copytree(project(at), d)
    # what the copy was built from may be no older, to the second, than the edit: build it all again
    subprocess.run(["make", "-s", "clean"], cwd=d, check=True, capture_output=True)
    for fn, old, new in edits:
        p = os.path.join(d, fn)
        with open(p) as f:
            text = f.read()
        if text.count(old) != 1:
            raise SystemExit(f"art/lang: patch {tag}: {old!r} occurs {text.count(old)} times in {fn} at {at}")
        with open(p, "w") as f:
            f.write(text.replace(old, new))
    _make(d)
    _PATCHED[at, tag] = d
    return d


def run(d, args, stdin=""):
    """args run in directory d: (stdout, stderr, status)."""
    r = subprocess.run(args, cwd=d, input=stdin, capture_output=True, text=True, timeout=60)
    return r.stdout, r.stderr, r.returncode


def ok(d, args, stdin=""):
    out, err, st = run(d, args, stdin)
    assert st == 0, (args, st, err)
    return out, err


def put(d, name, text):
    with open(os.path.join(d, name), "w") as f:
        f.write(text)
    return name


def source(at, name):
    with open(os.path.join(project(at), name)) as f:
        return f.read()


def kinds(at):
    """mote.h's NodeKind, in order: number -> name without N_."""
    body = re.search(r"typedef enum \{([^}]*)\} NodeKind;", source(at, "mote.h")).group(1)
    names = [n.strip()[2:] for n in body.split(",") if n.strip()]
    assert names[:2] == ["NUM", "VAR"] and "WHILE" in names, names
    return names


# ------------------------------------------------------------------ the syntax tree, from --tree

class N:
    """A node of the syntax tree as ./mote --tree prints it. kind: read assign write if while
    (statements), num var neg bin (expressions; op for bin and the comparisons)."""
    def __init__(self, kind, **kw):
        self.kind, self.op, self.name, self.idx, self.value = kind, None, None, None, None
        self.lhs = self.rhs = self.cond = None
        self.body, self.els = [], None
        self.__dict__.update(kw)

    def kids(self):
        """The children, as the figures draw them: a statement's expression, a condition's two
        sides, an if's then and else statements, a while's body."""
        if self.kind in ("if", "while"):
            return [self.cond] + self.body + (self.els or [])
        return [k for k in (self.lhs, self.rhs) if k is not None]

    def label(self):
        if self.kind == "read":
            return f"read {self.name}#{self.idx}"
        if self.kind == "assign":
            return f":= {self.name}#{self.idx}"
        if self.kind in ("write", "if", "while"):
            return self.kind
        if self.kind == "var":
            return f"{self.name}#{self.idx}"
        if self.kind == "num":
            return str(self.value)
        return self.op

    def walk(self):
        yield self
        for k in self.kids():
            yield from k.walk()


VAR = re.compile(r"^(\w+)#(\d+)$")


def parse_expr(toks):
    pos = [0]

    def e():
        t = toks[pos[0]]
        pos[0] += 1
        if t == "(":
            op = toks[pos[0]]
            pos[0] += 1
            a = e()
            if toks[pos[0]] == ")":
                pos[0] += 1
                assert op == "-", op
                return N("neg", op="-", lhs=a)
            b = e()
            assert toks[pos[0]] == ")", toks
            pos[0] += 1
            return N("bin", op=op, lhs=a, rhs=b)
        m = VAR.match(t)
        if m:
            return N("var", name=m[1], idx=int(m[2]))
        return N("num", value=int(t))

    x = e()
    assert pos[0] == len(toks), toks
    return x


def parse_tree(text):
    """./mote --tree's output -> the list of top-level statements."""
    rows = []
    for ln in text.splitlines():
        ind = len(ln) - len(ln.lstrip(" "))
        assert ind % 2 == 0, ln
        rows.append((ind // 2, re.findall(r"\(|\)|[^\s()]+", ln)))
    pos = [0]

    def stmts(depth):
        out = []
        while pos[0] < len(rows) and rows[pos[0]][0] == depth and rows[pos[0]][1] != ["else"]:
            out.append(stmt(depth))
        return out

    def stmt(depth):
        _, toks = rows[pos[0]]
        pos[0] += 1
        head = toks[0]
        if head == "read":
            m = VAR.match(toks[1])
            assert len(toks) == 2 and m, toks
            return N("read", name=m[1], idx=int(m[2]))
        if head == ":=":
            m = VAR.match(toks[1])
            return N("assign", name=m[1], idx=int(m[2]), lhs=parse_expr(toks[2:]))
        if head == "write":
            return N("write", lhs=parse_expr(toks[1:]))
        assert head in ("if", "while"), toks
        s = N(head, cond=parse_expr(toks[1:]))
        s.body = stmts(depth + 1)
        if head == "if" and pos[0] < len(rows) and rows[pos[0]] == (depth, ["else"]):
            pos[0] += 1
            s.els = stmts(depth + 1)
        return s

    prog = stmts(0)
    assert pos[0] == len(rows), rows[pos[0]:]
    return prog


def all_nodes(prog):
    for s in prog:
        yield from s.walk()


# ------------------------------------------------------------------ 01.09: the walk, re-enacted

CMP = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, "<": lambda a, b: a < b,
       ">": lambda a, b: a > b, "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b}
KIND = {"num": "NUM", "var": "VAR", "neg": "NEG", "assign": "ASSIGN", "read": "READ", "write": "WRITE",
        "if": "IF", "while": "WHILE", "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "==": "EQ", "!=": "NE",
        "<": "LT", ">": "GT", "<=": "LE", ">=": "GE"}


def kind_of(n):
    return KIND[n.op] if n.kind == "bin" else KIND[n.kind]


def walk(prog, inputs):
    """interp.c's interpret, eval and test on the tree from --tree: (events, output). An event is
    (what, node, detail): ("visit", n, None) for every node the walk is at, ("test", cond, result),
    ("set", stmt, value), ("write", stmt, value)."""
    ev, out, vals, inp = [], [], {}, list(inputs)

    def ev_(e):
        ev.append(("visit", e, None))
        if e.kind == "num":
            return e.value
        if e.kind == "var":
            assert e.idx in vals, e.label()
            return vals[e.idx]
        a = ev_(e.lhs)
        if e.kind == "neg":
            return -a
        b = ev_(e.rhs)
        return {"+": a + b, "-": a - b, "*": a * b, "/": int(a / b) if b else None}[e.op]

    def test(c):
        ev.append(("visit", c, None))
        r = CMP[c.op](ev_(c.lhs), ev_(c.rhs))
        ev.append(("test", c, r))
        return r

    def interpret(ss):
        for s in ss:
            ev.append(("visit", s, None))
            if s.kind in ("read", "assign"):
                vals[s.idx] = inp.pop(0) if s.kind == "read" else ev_(s.lhs)
                ev.append(("set", s, vals[s.idx]))
            elif s.kind == "write":
                v = ev_(s.lhs)
                out.append(v)
                ev.append(("write", s, v))
            elif s.kind == "if":
                interpret(s.body if test(s.cond) else (s.els or []))
            else:
                while test(s.cond):
                    interpret(s.body)

    interpret(prog)
    return ev, out


INTERP_TRACE = [
    ("interp.c", "static long eval(Node *e) {\n",
     'static long eval(Node *e) {\n  fprintf(stderr, "visit %d\\n", (int)e->kind);\n'),
    ("interp.c", "static bool test(Node *c) {\n", "static bool test__real(Node *c) {\n"),
    ("interp.c", "// Runs a list of statements, in order.\n",
     "static bool test(Node *c) {\n"
     '  fprintf(stderr, "visit %d\\n", (int)c->kind);\n'
     "  bool r = test__real(c);\n"
     '  fprintf(stderr, "test %d\\n", (int)r);\n'
     "  return r;\n}\n\n// Runs a list of statements, in order.\n"),
    ("interp.c", "  for (; s; s = s->next) {\n    switch (s->kind) {\n",
     '  for (; s; s = s->next) {\n    fprintf(stderr, "visit %d\\n", (int)s->kind);\n    switch (s->kind) {\n'),
    ("interp.c", "      s->sym->has_value = true;\n",
     '      s->sym->has_value = true;\n      fprintf(stderr, "set %d %ld\\n", s->sym->index, s->sym->value);\n'),
]


def checked_walk(at, prog, stdin):
    """walk() on stdin's numbers, held event for event to interp.c's own, and its output to
    ./mote's."""
    d = patched(at, "walk", INTERP_TRACE)
    out, err = ok(d, ["./mote", "programs/gcd.mote"], stdin)
    real_out, _ = ok(project(at), ["./mote", "programs/gcd.mote"], stdin)
    assert out == real_out
    ev, printed = walk(prog, [int(x) for x in stdin.split()])
    assert out.split() == [str(v) for v in printed], (out, printed)
    names = kinds(at)
    mine = []
    for what, n, det in ev:
        if what == "visit":
            mine.append(f"visit {kind_of(n)}")
        elif what == "test":
            mine.append(f"test {int(det)}")
        elif what == "set":
            mine.append(f"set {n.idx} {det}")
    theirs = []
    for ln in err.splitlines():
        p = ln.split()
        theirs.append(f"visit {names[int(p[1])]}" if p[0] == "visit" else ln)
    assert mine == theirs, ("the walk differs from interp.c's", mine, theirs)
    return ev, printed


# ------------------------------------------------------------------ 01.10 and 01.11: gen.c, re-enacted

T = ["t0", "t1", "t2", "t3", "t4", "t5", "t6"]
INSN = {"+": "add", "-": "sub", "*": "mul", "/": "div"}
OPPOSITE = {"==": "bne", "!=": "beq", "<": "bge", ">=": "blt", ">": "ble", "<=": "bgt"}


def gen(prog, symbols, regs=None):
    """gen.c's generate on the tree: [(line, node, segment)] for the listing. symbols is
    [(index, name)] in the table's order; regs {index: register} as improve() gives them (-O).
    A segment is (statement, part): the lines a statement writes before its body ("head"), between
    an if's two branches ("else"), after its body ("tail"); and ("main", "head") and ("main",
    "tail") around the program."""
    regs = regs or {}
    out, labels, off = [], [0], {}
    n = 0
    for idx, _ in symbols:
        if idx in regs:
            continue
        off[idx] = 8 * n
        n += 1
    name_of = dict(symbols)
    seg = [None]

    def emit(var, op, operands, node):
        text = f"    {op:<4} {operands}"
        if var is not None:
            text = f"{text:<26}# {name_of[var]}"
        out.append((text, node, seg[0]))

    def label(k):
        out.append((f".L{k}:", None, seg[0]))

    def operand(e, depth):
        if e.kind == "var" and e.idx in regs:
            return regs[e.idx]
        assert depth < 7, "expression too deep"
        into(e, T[depth], depth)
        return T[depth]

    def into(e, dest, depth):
        if e.kind == "num":
            emit(None, "li", f"{dest}, {e.value}", e)
        elif e.kind == "var":
            if e.idx in regs:
                emit(None, "mv", f"{dest}, {regs[e.idx]}", e)
            else:
                emit(e.idx, "ld", f"{dest}, {off[e.idx]}(sp)", e)
        elif e.kind == "neg":
            emit(None, "neg", f"{dest}, {operand(e.lhs, depth)}", e)
        else:
            a, b = operand(e.lhs, depth), operand(e.rhs, depth + 1)
            assert e.op != "/", "gen(): division's check is not re-enacted here"
            emit(None, INSN[e.op], f"{dest}, {a}, {b}", e)

    def store(s, r):
        if s.idx in regs:
            emit(None, "mv", f"{regs[s.idx]}, {r}", s)
        else:
            emit(s.idx, "sd", f"{r}, {off[s.idx]}(sp)", s)

    def branch_unless(c, k):
        a, b = operand(c.lhs, 0), operand(c.rhs, 1)
        emit(None, OPPOSITE[c.op], f"{a}, {b}, .L{k}", c)

    def stmt(s):
        seg[0] = (s, "head")
        if s.kind == "read":
            emit(None, "call", "getint", s)
            store(s, "a0")
        elif s.kind == "assign":
            if s.idx in regs:
                into(s.lhs, regs[s.idx], 0)
            else:
                store(s, operand(s.lhs, 0))
        elif s.kind == "write":
            r = operand(s.lhs, 0)
            emit(None, "mv", f"a0, {r}", s)
            emit(None, "call", "putint", s)
        elif s.kind == "if":
            labels[0] += 1
            els = labels[0]
            if s.els:
                labels[0] += 1
            end = labels[0]
            branch_unless(s.cond, els)
            stmts(s.body)
            if s.els:
                seg[0] = (s, "else")
                emit(None, "j", f".L{end}", s)
                label(els)
                stmts(s.els)
            seg[0] = (s, "tail")
            label(end)
        else:
            labels[0] += 2
            top, end = labels[0] - 1, labels[0]
            label(top)
            branch_unless(s.cond, end)
            stmts(s.body)
            seg[0] = (s, "tail")
            emit(None, "j", f".L{top}", s)
            label(end)

    def stmts(ss):
        for s in ss:
            stmt(s)

    seg[0] = ("main", "head")
    out.append(("main:", None, seg[0]))
    if n:
        emit(None, "addi", f"sp, sp, -{(8 * n + 15) // 16 * 16}", None)
    stmts(prog)
    seg[0] = ("main", "tail")
    emit(None, "li", "a0, 0", None)
    emit(None, "call", "exit", None)
    return out


def symbols_of(at, d, prog_file):
    out, _ = ok(d, ["./mote", "--symbols", prog_file])
    rows = []
    for ln in out.splitlines():
        idx, name, place = ln.split()
        rows.append((int(idx), name, place))
    return rows


def checked_gen(at, prog_file="programs/gcd.mote", regs=None, prog=None):
    """gen() of --tree's tree (or of prog, that tree parsed already), held line for line to
    ./mote -S (or -S -O, with regs)."""
    d = project(at)
    if prog is None:
        tree_text, _ = ok(d, ["./mote", "--tree", prog_file])
        prog = parse_tree(tree_text)
    syms = symbols_of(at, d, prog_file)
    g = gen(prog, [(i, n) for i, n, _ in syms], regs)
    real, _ = ok(d, ["./mote", "-S"] + (["-O"] if regs else []) + [prog_file])
    assert real.splitlines() == [s for s, _, _ in g], ("gen() differs from ./mote -S", real, g)
    return prog, syms, g, real


def segments(g):
    """The listing cut into its segments, in order: [(segment, [lines])]."""
    out = []
    for s, node, sg in g:
        if out and out[-1][0] == sg:
            out[-1][1].append((s, node))
        else:
            out.append((sg, [(s, node)]))
    return out


def statement_lines(text):
    """gcd.mote's lines that are statements (or else and end): [(line number, text)]."""
    return [(k, ln) for k, ln in enumerate(text.splitlines(), 1) if ln.strip() and not ln.strip().startswith("#")]


def source_of_segments(segs, src_lines):
    """Each segment that is a statement's own: the source line it comes from (gcd.mote has one a
    line: read, read, while, if, :=, else, :=, end, end, write, in that order)."""
    want = [sg for sg, _ in segs if sg[0] != "main"]
    assert len(want) == len(src_lines), (len(want), src_lines)
    first = {"read": "read", "assign": None, "write": "write", "if": "if", "while": "while"}
    out = {}
    for sg, (k, ln) in zip(want, src_lines):
        s, part = sg
        w = ln.split()[0]
        if part == "head":
            assert (first[s.kind] or s.name) == w and (s.kind != "assign" or ln.split()[1] == ":="), (sg, ln)
        else:
            assert w == {"else": "else", "tail": "end"}[part], (sg, ln)
        out[sg] = (k, ln)
    return out


def trace(d, listing, stdin):
    """./machine --trace on the listing: (stdout, [(listing line, text, {changed: value})], the
    state {register or address: value} after each)."""
    put(d, "fig.s", listing)
    out, err = ok(d, ["./machine", "--trace", "fig.s"], stdin)
    rows, states, st = [], [], {"sp": 1 << 20}
    for ln in err.splitlines():
        m = re.match(r"^\s*(\d+)  (\S.*)$", ln)
        assert m, ln
        ch = dict((k, int(v)) for k, v in re.findall(r"  (mem\[\d+\]|\w+) = (-?\d+)", m[2]))
        text = re.split(r"  +(?:mem\[\d+\]|\w+) = ", m[2])[0].strip()
        st = dict(st)
        st.update(ch)
        rows.append((int(m[1]), text, ch))
        states.append(st)
    return out, rows, states


def count(d, listing, stdin):
    put(d, "fig.s", listing)
    out, err = ok(d, ["./machine", "--count", "fig.s"], stdin)
    m = re.match(r"^(\d+) instructions$", err.strip())
    assert m, err
    return out, int(m[1])


# ------------------------------------------------------------------ drawing helpers

def node_w(label, size=12, pad=14):
    return max(30, tw(label, size, mono=True) + pad)


def tree_layout(prog, x0, y0, dy, size=12, gap=8, top_gap=22, pad=14):
    """{node: (cx, cy, w)} for the statements of prog in a row and each one's subtree under it:
    each subtree as wide as its widest level needs, a parent over the middle of its children."""
    pos = {}

    def width(n):
        ks = n.kids()
        own = node_w(n.label(), size, pad) + gap
        return max(own, sum(width(k) for k in ks)) if ks else own

    def place(n, x, depth):
        w = width(n)
        ks = n.kids()
        if ks:
            total = sum(width(k) for k in ks)
            cx = x + (w - total) / 2
            xs = []
            for k in ks:
                xs.append(place(k, cx, depth + 1))
                cx += width(k)
            mid = (xs[0] + xs[-1]) / 2
        else:
            mid = x + w / 2
        pos[n] = (mid, y0 + depth * dy, node_w(n.label(), size, pad))
        return mid

    x = x0
    for s in prog:
        place(s, x, 0)
        x += width(s) + top_gap
    return pos, x - top_gap - x0


def draw_node(f, n, pos, state, size=12, h=24):
    """state: here (the walk is at it), used (read in this step), plain, quiet."""
    cx, cy, w = pos[n]
    cls, tcls, wt = {"here": ("a af", "ta", 700), "used": ("a f", "ta", 600), "plain": ("s f", "t", 600),
                     "quiet": ("m f", "tm", 500)}[state]
    f.rect(cx - w / 2, cy - h / 2, w, h, cls, 6)
    f.text(cx, cy + size * 0.36, n.label(), tcls, size, "middle", wt, mono=True)


def draw_edges(f, nodes, pos, cls_of=lambda a, b: "s", h=24):
    for n in nodes:
        for k in n.kids():
            (x1, y1, _), (x2, y2, _) = pos[n], pos[k]
            f.line(x1, y1 + h / 2, x2, y2 - h / 2, cls_of(n, k))


def write(name, fig, stepped=False):
    """Write fig as figures/<name>.svg after the checks (ASCII; kept whole by the site's sanitizer;
    a stepped one steps on the site, an ordinary one has no step groups); return the path."""
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


# ------------------------------------------------------------------ 01.09-walk

def walk_fig():
    at = "01.09"
    d = project(at)
    tree_text, _ = ok(d, ["./mote", "--tree", "programs/gcd.mote"])
    assert tree_text.splitlines() == ["read i#1", "read j#2", "while (!= i#1 j#2)", "  if (> i#1 j#2)",
                                      "    := i#1 (- i#1 j#2)", "  else", "    := j#2 (- j#2 i#1)", "write i#1"]
    prog = parse_tree(tree_text)
    syms = symbols_of(at, d, "programs/gcd.mote")
    assert [(i, n) for i, n, _ in syms] == [(1, "i"), (2, "j")], syms
    ev, printed = checked_walk(at, prog, SMALL_IN)
    assert printed == [2], printed

    f = Fig("w0109", "The walker on gcd.mote with 6 and 4: the node it is at, and the values in the symbol table",
            0)
    size = 12
    pos, width = tree_layout(prog, 0, 40, 50, size, top_gap=18)
    dx = (640 - width) / 2
    pos = {n: (x + dx, y, w) for n, (x, y, w) in pos.items()}
    nodes = list(all_nodes(prog))
    bottom = max(y for _, y, _ in pos.values())
    ip, wh, el = prog[2], prog[2].body[0], prog[2].body[0].els[0]

    # the base: the statement list's next arrows, the edges, the "else" on its edge, the panels' heads
    for a, b in zip(prog, prog[1:]):
        (x1, y1, w1), (x2, y2, w2) = pos[a], pos[b]
        f.line(x1 + w1 / 2 + 3, y1, x2 - w2 / 2 - 4, y2, "m", arrow=True)
    draw_edges(f, nodes, pos)
    (ex, ey, _), (cx_, cy_, _) = pos[wh], pos[el]
    f.text((ex + cx_) / 2 + 4, (ey + cy_) / 2 - 6, "else", "tm", 11)
    py = bottom + 46
    f.text(24, py, "the symbol table", "tm", 11.5)
    f.text(300, py, "now", "tm", 11.5)
    f.text(520, py, "output", "tm", 11.5)
    ty = py + 10
    rows = [(1, "i"), (2, "j")]
    rh = 26

    def panel(vals, changed, now, out, here, used):
        for n in nodes:
            st = "here" if n is here else "used" if n in used else "plain"
            draw_node(f, n, pos, st, size)
        for n, v in used.items():
            if n.kind == "var" and n is not here:
                cx, cy, _ = pos[n]
                f.text(cx, cy + 29, str(v), "ta", 12, "middle", 700, mono=True)
        # the table: index, name, value
        f.rect(16, ty, 240, rh * 2 + 2, "s f", 6)
        f.line(16, ty + rh + 1, 256, ty + rh + 1, "m")
        for k, (idx, name) in enumerate(rows):
            y = ty + 1 + k * rh
            hot = idx == changed
            if hot:
                f.rect(150, y + 3, 100, rh - 6, "af", 4, sw=False)
            f.text(30, y + 17.5, str(idx), "tm", 12, mono=True)
            f.text(56, y + 17.5, name, "t", 13, weight=700, mono=True)
            v = vals.get(idx)
            f.text(166, y + 17.5, "no value" if v is None else f"value {v}", "ta" if hot else "t" if v is not None else "tm",
                   12, weight=700 if hot else None, mono=v is not None)
        f.line(140, ty + 4, 140, ty + rh * 2 - 2, "m")
        for k, ln in enumerate(now):
            f.code(300, ty + 18 + k * 20, ln, 13, "ta" if k == 0 else "t", weight=700 if k == 0 else None)
        f.rect(520, ty, 104, rh * 2 + 2, "s fs", 6)
        if out:
            f.text(538, ty + 22, out, "ta", 15, weight=700, mono=True)

    vals, out = {}, ""
    with steps.step(f, "Before the walk: analysis has made an entry for i and for j, and neither has a value "
                       "yet. The walker starts at the first statement."):
        panel(vals, None, ["start"], out, None, {})
    k = 0
    while k < len(ev):
        what, n, _ = ev[k]
        assert what == "visit", ev[k]
        if n.kind in ("read", "assign", "write"):
            # the statement, and everything visited up to its set or write
            j = k + 1
            used = {}
            while ev[j][0] == "visit":
                used[ev[j][1]] = None
                j += 1
            kind, s, v = ev[j]
            assert s is n and kind in ("set", "write"), ev[j]
            for m_ in used:
                if m_.kind == "var":
                    used[m_] = vals[m_.idx]
            if n.kind == "read":
                vals[n.idx] = v
                cap = (f"read {n.name}#{n.idx}: the walker reads {v} from the input and keeps it in entry "
                       f"{n.idx} of the table, the one the node points at.")
                now = [f"read {n.name}", f"{n.name} = {v}"]
                changed = n.idx
            elif n.kind == "assign":
                e = n.lhs
                a, b = used[e.lhs], used[e.rhs]
                vals[n.idx] = v
                cap = (f":= {n.name}#{n.idx}: the walk goes down to the {e.op} node and its two names, takes "
                       f"{a} and {b} from their entries, and puts {v} in entry {n.idx}.")
                now = [f"{n.name} := {e.lhs.name} {e.op} {e.rhs.name}", f"{n.name} = {a} {e.op} {b} = {v}"]
                changed = n.idx
            else:
                out = str(v)
                cap = (f"write: i#1 points at entry 1, which holds {v}; the walker prints it. ./mote on 6 4 "
                       f"prints {printed[0]} too.")
                now = [f"write {n.lhs.name}", f"prints {v}"]
                changed = None
            with steps.step(f, cap):
                panel(vals, changed, now, out, n, {m_: used[m_] for m_ in used})
            k = j + 1
            continue
        if n.kind in ("if", "while"):
            k += 1          # the statement itself: its test is the next frame's
            continue
        # a test: the condition node, its two sides, the result
        c = n
        assert c.kind == "bin" and c.op in CMP, c.label()
        j = k + 1
        used = {}
        while ev[j][0] == "visit":
            used[ev[j][1]] = vals[ev[j][1].idx]
            j += 1
        assert ev[j][0] == "test" and ev[j][1] is c, ev[j]
        r = ev[j][2]
        a, b = used[c.lhs], used[c.rhs]
        if c is ip.cond:
            first = sum(1 for e_ in ev[:k] if e_[0] == "visit" and e_[1] is c) == 0
            if r:
                cap = (("while: " if first else "Back at the while: ") + f"its condition, i != j, is {a} != {b}: "
                       "true, so the walker runs the body.")
            else:
                cap = (f"Back at the while: {a} != {b} is false. The loop is done, and the walker goes on to the "
                       "next statement.")
            now = [f"while i != j", f"{a} != {b}: {'true' if r else 'false'}"]
        else:
            cap = (f"if: i > j is {a} > {b}: " + ("true, so the walker takes the first branch." if r else
                                                  "false, so it takes the else branch."))
            now = [f"if i > j", f"{a} > {b}: {'true' if r else 'false'}"]
        with steps.step(f, cap):
            panel(vals, None, now, out, c, used)
        k = j + 1
    f.h = ty + rh * 2 + 18
    return f


# ------------------------------------------------------------------ 01.09-per-pass

MOTE0_TRACE = [
    ("mote0.c", "static Name *find(const char *s, int len) {\n",
     'static Name *find(const char *s, int len) {\n  fprintf(stderr, "find %.*s\\n", len, s);\n'),
    ("mote0.c", "  for (at = from + 1; at < nlines; at++) {\n    nread++;\n",
     '  for (at = from + 1; at < nlines; at++) {\n    nread++;\n    fprintf(stderr, "past %d\\n", at + 1);\n'),
    ("mote0.c", "  for (at = first; at < nlines; ) {\n    nread++;\n",
     '  for (at = first; at < nlines; ) {\n    nread++;\n    fprintf(stderr, "line %d\\n", at + 1);\n'),
]


def mote0_passes(at, loop_line, stdin):
    """mote0 on gcd.mote: the passes of its loop, each [(line, read past?, [names searched])],
    from a copy of mote0.c that reports every line it looks at and every search of its table; the
    lines held to ./mote0 --count."""
    d = patched(at, "mote0", MOTE0_TRACE)
    out, err = ok(d, ["./mote0", "programs/gcd.mote"], stdin)
    real_out, real_err = ok(project(at), ["./mote0", "--count", "programs/gcd.mote"], stdin)
    assert out == real_out
    reads = []
    for ln in err.splitlines():
        what, arg = ln.split()
        if what in ("line", "past"):
            reads.append([int(arg), what == "past", []])
        else:
            reads[-1][2].append(arg)
    assert real_err.strip() == f"{len(reads)} lines read", (real_err, len(reads))
    starts = [k for k, r in enumerate(reads) if r[0] == loop_line and not r[1]]
    return [reads[a:b] for a, b in zip(starts, starts[1:])], len(reads)


def per_pass_fig():
    at = "01.09"
    d = project(at)
    src = source(at, "programs/gcd.mote")
    lines = src.splitlines()
    tree_text, _ = ok(d, ["./mote", "--tree", "programs/gcd.mote"])
    prog = parse_tree(tree_text)
    loop = prog[2]
    assert loop.kind == "while"
    loop_line = next(k for k, ln in enumerate(lines, 1) if ln.split()[:1] == ["while"])
    end_line = max(k for k, ln in enumerate(lines, 1) if ln.strip() == "end")
    assert (loop_line, end_line) == (4, 10), (loop_line, end_line)

    # mote: the walker's passes, from its events (held to interp.c's own)
    ev, printed = checked_walk(at, prog, GCD_IN)
    assert printed == [21]
    starts = [k for k, e in enumerate(ev) if e[0] == "visit" and e[1] is loop.cond]
    walks = [ev[a:b] for a, b in zip(starts, starts[1:])]
    kinds_ = [next(e[2] for e in w if e[0] == "test" and e[1] is loop.body[0].cond) for w in walks]
    assert len(walks) == 11 and kinds_.count(True) == 8, (len(walks), kinds_)
    visited = [[e[1] for e in w if e[0] == "visit"] for w in walks]

    # mote0: its passes on the same input
    passes, total = mote0_passes(at, loop_line, GCD_IN)
    assert total == 88 and len(passes) == len(walks), (total, len(passes))
    for kind in (True, False):
        mine = [(len(p), sum(len(r[2]) for r in p), len(v)) for p, v, k in zip(passes, visited, kinds_) if k == kind]
        assert len(set(mine)) == 1, ("passes of one kind differ", kind, mine)
    one = next(k for k, kk in enumerate(kinds_) if kk)
    other = next(k for k, kk in enumerate(kinds_) if not kk)
    p, v = passes[one], visited[one]
    n_lines, n_search, n_nodes = len(p), sum(len(r[2]) for r in p), len(v)
    assert (n_lines, n_search, n_nodes) == (len(passes[other]), sum(len(r[2]) for r in passes[other]),
                                            len(visited[other])), "the two kinds of pass count differently"
    assert (n_lines, n_search, n_nodes) == (7, 7, 11), (n_lines, n_search, n_nodes)
    assert [r[0] for r in p] == list(range(loop_line, end_line + 1)), p
    # the walker has no search: interp.c finds nothing by name
    interp = source(at, "interp.c")
    assert not re.search(r"\b(find|strcmp|strncmp|memcmp|lookup)\b", interp)

    f = Fig("p0109", "One pass of gcd's loop under each interpreter: the first reads lines and searches for "
                     "names; the walker follows pointers", 0)
    # ---- left: mote0
    lx, colw = 16, 284
    f.text(lx, 22, "mote0: one pass, i > j", "t", 13, weight=700)
    f.text(lx, 40, "the lines it reads, the names it searches for", "tm", 11.5)
    size = 12.5
    c = cw(size)
    y0, rh = 70, 26
    # the walker's tree, on the right, sets how low the counts go
    rx, rw = 322, 302
    pos, width = tree_layout([loop], 0, 84, 46, 11, gap=5, pad=12)
    assert width <= rw, width
    tree_bottom = max(y for _, y, _ in pos.values()) + 12
    yb = max(y0 + len(p) * rh, tree_bottom + 30) + 8
    for k, (num, past, found) in enumerate(p):
        y = y0 + k * rh
        text = lines[num - 1]
        f.rect(lx, y - 16, colw, rh - 4, "fs", 4, sw=False)
        f.text(lx + 22, y, str(num), "tm", 11, "end", mono=True)
        x = lx + 34
        # mark every name the line searched for: they are its names, in some order
        names = [(m.start(), m.group()) for m in re.finditer(r"\b[a-z_]\w*\b", text)
                 if m.group() not in ("while", "do", "if", "then", "else", "end", "read", "write")]
        if found:
            assert sorted(nm for _, nm in names) == sorted(found), (num, names, found)
            for col, nm in names:
                f.rect(x + col * c - 2, y - 13, len(nm) * c + 4, 18, "a af", 3)
        f.code(x, y, text, size, "tm" if past else "t")
        note = (f"{len(found)} searches" if found else "read past" if past else "read")
        f.text(lx + colw - 6, y, note, "ta" if found else "tm", 11, "end", weight=700 if found else None)
    for k, (n_, lab) in enumerate(((n_lines, "lines read"), (n_search, "searches of the table"))):
        f.text(lx + 4 + k * 110, yb + 22, str(n_), "ta", 24, weight=700, mono=True)
        f.text(lx + 4 + k * 110, yb + 40, lab, "t", 11.5)

    # ---- right: the walker
    f.text(rx, 22, "mote: the same pass", "t", 13, weight=700)
    f.text(rx, 40, "the nodes the walker visits", "tm", 11.5)
    dx = rx + (rw - width) / 2
    pos = {n: (x + dx, y, w) for n, (x, y, w) in pos.items()}
    sub = list(loop.walk())
    seen = set(v)
    assert seen <= set(sub) and loop not in seen
    draw_edges(f, sub, pos, lambda a, b: "a" if b in seen else "m")
    for n in sub:
        draw_node(f, n, pos, "here" if n in seen else "quiet", 11)
    f.text(rx, tree_bottom + 24, "i#1 and j#2 point at entries 1 and 2", "tm", 11.5)
    for k, (n_, lab) in enumerate(((n_nodes, "nodes visited"), (0, "searches"))):
        f.text(rx + 4 + k * 110, yb + 22, str(n_), "ta", 24, weight=700, mono=True)
        f.text(rx + 4 + k * 110, yb + 40, lab, "t", 11.5)
    f.line(rx - 11, 12, rx - 11, yb + 44, "m")
    f.h = yb + 58
    return f


# ------------------------------------------------------------------ 01.10

def slots_fig():
    at = "01.10"
    d = project(at)
    prog, syms, g, listing = checked_gen(at)
    assert [(i, n) for i, n, _ in syms] == [(1, "i"), (2, "j")]
    lines = listing.splitlines()
    assert lines[1].strip() == "addi sp, sp, -16", lines[:3]
    out, rows, states = trace(d, listing, SMALL_IN)
    assert out == "2\n"
    top = 1 << 20
    assert rows[0][1] == "addi sp, sp, -16" and states[0]["sp"] == top - 16, rows[0]
    sp = states[0]["sp"]
    offs = {}
    for s, node, _ in g:
        m = re.search(r"(ld|sd)\s+\w+, (\d+)\(sp\)\s+# (\w+)", s)
        if m:
            offs.setdefault(m[3], set()).add(int(m[2]))
    assert offs == {"i": {0}, "j": {8}}, offs
    # after the two reads: each value at sp + its offset
    k = next(k for k, r in enumerate(rows) if r[1].startswith("sd   a0, 8(sp)"))
    mem = states[k]
    assert mem[f"mem[{sp}]"] == 6 and mem[f"mem[{sp + 8}]"] == 4, mem

    f = Fig("s0110", "Where the variables of gcd.mote live: a slot each in the machine's memory, found from sp", 0)
    # memory, addresses growing downward: what is free above sp, the two slots, the end of memory
    mx, mw, cell = 300, 128, 46
    f.text(mx, 22, "the machine's memory, after the two reads on 6 4", "tm", 11.5)
    rest_y, rest_h = 36, 40
    sp_y = rest_y + rest_h
    end_y = sp_y + 2 * cell
    f.rect(mx, rest_y, mw, rest_h, "m f", 0, dash=True)
    f.text(mx + mw / 2, rest_y + 25, "free", "tm", 11.5, "middle")
    ax = mx + mw + 10                               # the addresses
    for k, (idx, name, _) in enumerate(syms):
        off = 8 * k
        assert offs[name] == {off}, (name, offs)
        y = sp_y + k * cell
        v = mem[f"mem[{sp + off}]"]
        f.rect(mx, y, mw, cell, "a af", 0)
        f.text(mx + 12, y + 28, f"{off}(sp)", "ta", 13, weight=700, mono=True)
        f.text(mx + mw - 12, y + 28, f"{name} = {v}", "t", 13, "end", mono=True)
        f.text(ax, y + 4, str(sp + off), "tm", 11, mono=True)
    f.text(ax, end_y + 4, str(top), "tm", 11, mono=True)
    f.line(mx - 8, end_y, mx + mw, end_y, "s", sw=2.5)
    f.text(mx + mw / 2, end_y + 22, "the end of memory: sp starts here", "tm", 11.5, "middle")
    # the symbol table, a row beside each slot, and an arrow from the row to its slot
    tx, tw_ = 16, 196
    f.text(tx + 8, sp_y - 10, "the symbol table", "tm", 11.5)
    f.rect(tx, sp_y, tw_, 2 * cell, "s f", 6)
    f.line(tx, sp_y + cell, tx + tw_, sp_y + cell, "m")
    for k, (idx, name, _) in enumerate(syms):
        y = sp_y + k * cell + 28
        f.text(tx + 14, y, str(idx), "tm", 12, mono=True)
        f.text(tx + 38, y, name, "t", 14, weight=700, mono=True)
        f.text(tx + tw_ - 12, y, f"offset 8 * {idx - 1} = {8 * k}", "t", 11.5, "end", mono=True)
        f.line(tx + tw_ + 4, y - 4, mx - 4, y - 4, "s", arrow=True)
    # sp, pointing at the first slot
    f.line(mx - 46, sp_y, mx - 4, sp_y, "a", arrow=True)
    f.text(mx - 52, sp_y + 5, "sp", "ta", 14, "end", 700, mono=True)
    # the frame: 16 bytes, made by addi
    bx = ax + 64
    f.path(f"M{bx - 6} {sp_y + 1} L{bx} {sp_y + 1} L{bx} {end_y - 1} L{bx - 6} {end_y - 1}", "a")
    f.code(bx + 10, sp_y + cell - 2, "addi sp, sp, -16", 11.5, "ta", weight=700)
    f.text(bx + 10, sp_y + cell + 15, "16 bytes, two slots", "t", 11.5)
    f.h = end_y + 36
    return f


def statement_fig():
    at = "01.10"
    d = project(at)
    prog, syms, g, listing = checked_gen(at)
    st = prog[2].body[0].body[0]
    assert st.kind == "assign" and st.label() == ":= i#1" and st.lhs.op == "-", st.label()
    mine = [(k, s, node) for k, (s, node, sg) in enumerate(g, 1) if sg == (st, "head")]
    texts = [s.strip() for _, s, _ in mine]
    assert [re.sub(r"\s+", " ", t) for t in texts] == ["ld t0, 0(sp) # i", "ld t1, 8(sp) # j", "sub t0, t0, t1",
                                                     "sd t0, 0(sp) # i"], texts
    assert [n for _, _, n in mine] == [st.lhs.lhs, st.lhs.rhs, st.lhs, st], "each line's node"
    out, rows, states = trace(d, listing, SMALL_IN)
    first = [r[0] for r in rows].index(mine[0][0])
    run_ = list(range(first, first + 4))
    assert [rows[k][0] for k in run_] == [m[0] for m in mine], "the statement's lines run in order"
    sp = states[0]["sp"]
    before = states[first - 1]
    after = [states[k] for k in run_]
    assert (before["t0"], before["t1"], before[f"mem[{sp}]"], before[f"mem[{sp + 8}]"]) == (6, 4, 6, 4), before
    assert after[2]["t0"] == 2 and after[3][f"mem[{sp}]"] == 2

    f = Fig("st0110", "i := i - j as the code generator writes it, an instruction a step: two loads, a subtraction, "
                      "a store", 236)
    f.text(24, 22, "the statement's tree", "tm", 11.5)
    f.text(212, 22, "./mote -S writes", "tm", 11.5)
    f.text(500, 22, "after it runs, on 6 4", "tm", 11.5)
    pos, width = tree_layout([st], 0, 62, 56, 13, gap=18)
    dx = 24 + (160 - width) / 2
    pos = {n: (x + dx, y, w) for n, (x, y, w) in pos.items()}
    sub = list(st.walk())
    draw_edges(f, sub, pos)
    lx, ly, lh = 212, 52, 30
    f.rect(lx - 8, ly - 20, 232, lh * 4 + 14, "s fs", 6)
    regs = [("t0", "t0"), ("t1", "t1"), ("0(sp)", f"mem[{sp}]"), ("8(sp)", f"mem[{sp + 8}]")]
    names = {"0(sp)": "i", "8(sp)": "j"}
    rx, ry, rw, rr = 524, 36, 100, 40
    for k, (lab, _) in enumerate(regs):
        y = ry + k * rr
        f.text(rx - 10, y + 22, f"{names[lab]}: {lab}" if lab in names else lab, "tm", 12, "end", mono=True)
    def dest(text):
        """What an instruction writes: its first register, or for sd the slot's address."""
        op, rest = text.split(None, 1)
        if op == "sd":
            return f"mem[{sp + int(re.search(r'(\d+)\(sp\)', rest)[1])}]"
        return rest.split(",")[0].strip()

    dests = [dest(t.strip()) for _, t, _ in mine]
    assert dests == ["t0", "t1", "t0", f"mem[{sp}]"], dests
    for k, (num, text, node) in enumerate(mine):
        op = text.split()[0]
        if op == "ld":
            cap = (f"{text.split('#')[0].strip()}: the walk is at {node.name}#{node.idx}, a use of a variable: a load "
                   f"from its slot into {T[k]}, the register at its depth.")
        elif op == "sub":
            cap = "sub t0, t0, t1: back at the - node, both operands are in registers: one instruction, result in t0."
        else:
            cap = ("sd t0, 0(sp): back at := i#1, the value is given to i: a store into its slot. "
                   "Nothing is kept in a register for the next statement.")
        with steps.step(f, cap):
            for n in sub:
                draw_node(f, n, pos, "here" if n is node else "plain", 13)
            for j in range(k + 1):
                y = ly + j * lh
                if j == k:
                    f.rect(lx - 4, y - 16, 224, lh - 6, "a af", 4)
                f.code(lx + 4, y, mine[j][1][4:], 13, "ta" if j == k else "t", weight=700 if j == k else None)
            s_ = after[k]
            prev = before if k == 0 else after[k - 1]
            for j, (lab, key) in enumerate(regs):
                y = ry + j * rr
                written = key == dests[k]
                # the trace changes nothing but what the instruction writes
                assert s_[key] == prev[key] or written, (k, key)
                assert set(rows[run_[k]][2]) <= {dests[k]}, rows[run_[k]]
                touched = key in dests[:k + 1]
                f.rect(rx, y, rw, rr - 8, "a af" if written else "s f", 4)
                f.text(rx + rw / 2, y + 22, str(s_[key]), "ta" if written else "t" if touched else "tm", 15,
                       "middle", 700 if written else None, mono=True)
    f.text(24, 226, "t0 and t1 held 6 and 4 already, from the if's test", "tm", 11.5)
    return f


def while_fig():
    at = "01.10"
    d = project(at)
    prog, syms, g, listing = checked_gen(at)
    src = source(at, "programs/gcd.mote")
    segs = segments(g)
    smap = source_of_segments(segs, statement_lines(src))
    loop = prog[2]
    # the loop's lines: from its head to its tail
    a = next(k for k, (sg, _) in enumerate(segs) if sg == (loop, "head"))
    b = next(k for k, (sg, _) in enumerate(segs) if sg == (loop, "tail"))
    part = segs[a:b + 1]
    head, tail = part[0][1], part[-1][1]
    assert [s for s, _ in head][0] == ".L1:" and head[-1][0].split()[:2] == ["beq", "t0,"], head
    assert [s for s, _ in tail] == ["    j    .L1", ".L2:"], tail
    assert head[-1][0].endswith(".L2"), head

    f = Fig("wh0110", "A while loop as a test and two jumps: the condition becomes one branch on its opposite, "
                      "past the loop", 0)
    sx, lx = 30, 236
    f.text(sx - 6, 22, "gcd.mote, lines 4 to 10", "tm", 11.5)
    f.text(lx, 22, "./mote -S, the loop's lines", "tm", 11.5)
    size, lh = 12, 17
    c = cw(size)
    xl = lx - 22                                    # the jump back runs down here
    y = 50
    row_of = {}
    for sg, lines_ in part:
        k, text = smap[sg]
        is_loop = sg[0] is loop
        y0 = y
        if is_loop:
            f.rect(lx - 6, y - 13, 200, lh * len(lines_) + 2, "af", 4, sw=False)
        f.text(sx, y, str(k), "tm", 11, "end", mono=True)
        f.code(sx + 10, y, text, size, "ta" if is_loop else "t", weight=700 if is_loop else None)
        for s, _ in lines_:
            row_of[s.strip()] = y
            lab = not s.startswith(" ")
            f.code(lx, y, s if lab else s[4:], size, "ta" if is_loop else "tm" if lab else "t",
                   weight=700 if is_loop else None)
            y += lh
        f.line(sx + 10 + c * len(text) + 8, y0 - 4, xl - 10, y0 - 4, "m", dash=True)
        y += 6
    # the branch out (right) and the jump back (left)
    beq = head[-1][0].strip()
    yb, yl2 = row_of[beq], row_of[".L2:"]
    yj, yl1 = row_of["j    .L1"], row_of[".L1:"]
    xr = lx + 236
    f.path(f"M{fmt(lx + c * len(beq) + 8)} {yb - 4} L{xr} {yb - 4} L{xr} {yl2 - 4} L{fmt(lx + c * 4 + 8)} {yl2 - 4}",
           "a", arrow=True)
    for j, t in enumerate(("the branch out:", "beq, the opposite", "of !=, to .L2,", "past the loop")):
        f.text(xr + 10, (yb + yl2) / 2 - 22 + j * 16, t, "ta", 11.5, weight=700 if j == 0 else None)
    f.path(f"M{lx - 8} {yj - 4} L{xl} {yj - 4} L{xl} {yl1 - 4} L{lx - 4} {yl1 - 4}", "a", arrow=True)
    f.text(lx + c * 8 + 16, yj, "back to the test", "ta", 11.5, weight=700)
    f.h = y + 10
    return f


# ------------------------------------------------------------------ 01.11

def before_after_fig():
    at = "01.11"
    d = project(at)
    prog, syms, g0, plain = checked_gen(at)
    _, _, g1, improved = checked_gen(at, regs={1: "s1", 2: "s2"}, prog=prog)
    src = source(at, "programs/gcd.mote")
    s0, s1 = segments(g0), segments(g1)
    assert [sg for sg, _ in s0] == [sg for sg, _ in s1]
    smap = source_of_segments(s0, statement_lines(src))
    n0 = sum(1 for s, _, _ in g0 if s.startswith(" "))
    n1 = sum(1 for s, _, _ in g1 if s.startswith(" "))
    ldsd = sum(1 for s, _, _ in g0 if s.split()[0] in ("ld", "sd"))
    assert (n0, n1, ldsd) == (26, 14, 13), (n0, n1, ldsd)
    assert not any(s.split()[0] in ("ld", "sd") for s, _, _ in g1)
    o0, c0 = count(d, plain, GCD_IN)
    o1, c1 = count(d, improved, GCD_IN)
    assert (o0, o1, c0, c1) == ("21\n", "21\n", 142, 61), (o0, o1, c0, c1)

    f = Fig("ba0111", "gcd.mote compiled twice: on the left every use is a load and every assignment a store; on "
                      "the right i and j live in s1 and s2", 0)
    sx, ax, bx = 16, 166, 440
    size, lh = 11.5, 15
    c = cw(size)
    f.text(sx, 22, "gcd.mote", "tm", 11.5)
    f.text(ax, 22, "./mote -S", "t", 12.5, weight=700)
    f.text(bx, 22, "./mote -S -O", "t", 12.5, weight=700)
    y = 46
    for k, ((sg, la), (_, lb)) in enumerate(zip(s0, s1)):
        rows = max(len(la), len(lb))
        if k % 2 == 1:
            f.rect(8, y - 12, 624, rows * lh + 4, "fs", 4, sw=False)
        if sg in smap:
            f.code(sx, y, smap[sg][1], 11, "tm")
        for j, (s, _) in enumerate(la):
            yy = y + j * lh
            if s.split()[0] in ("ld", "sd"):
                f.rect(ax + 4 * c - 4, yy - 11, (len(s) - 4) * c + 8, 14, "af", 3, sw=False)
                f.code(ax, yy, s, size, "ta", weight=700)
            else:
                f.code(ax, yy, s, size, "t")
        for j, (s, _) in enumerate(lb):
            yy = y + j * lh
            spans = [(m.start(), m.end(), "ta") for m in re.finditer(r"\bs[12]\b", s)]
            f.code(bx, yy, s, size, "t", spans=spans)
        y += rows * lh + 6
    y += 14
    f.line(ax, y - 10, 624, y - 10, "m")
    f.text(ax, y + 10, f"{n0} instructions, {ldsd} of them ld or sd", "t", 11.5)
    f.text(ax, y + 34, str(c0), "ta", 22, weight=700, mono=True)
    f.text(ax + 52, y + 34, "run on 1071 462", "t", 11.5)
    f.text(bx, y + 10, f"{n1} instructions, none ld or sd", "t", 11.5)
    f.text(bx, y + 34, str(c1), "ta", 22, weight=700, mono=True)
    f.text(bx + 36, y + 34, "run on 1071 462", "t", 11.5)
    f.h = y + 50
    return f


IMPROVE_TRACE = [
    ("improve.c", "void improve(Node *prog) {\n", "static void improve__real(Node *prog) {\n"),
    ("improve.c", "    best->reg = s[r];\n  }\n}\n",
     "    best->reg = s[r];\n  }\n}\n\nvoid improve(Node *prog) {\n  improve__real(prog);\n"
     "  for (Symbol *v = symbols(); v; v = v->next)\n"
     '    fprintf(stderr, "uses %d %.*s %d %s\\n", v->index, v->len, v->name, v->uses, v->reg ? v->reg : "-");\n'
     "}\n"),
]


def uses(at, prog_file):
    """[(index, name, uses, register or None)] as improve() decides them, from a copy of improve.c
    that reports them; its listing held to the real -S -O."""
    d = patched(at, "improve", IMPROVE_TRACE)
    if not os.path.exists(os.path.join(d, prog_file)):
        shutil.copy(os.path.join(project(at), prog_file), os.path.join(d, prog_file))
    out, err = ok(d, ["./mote", "-S", "-O", prog_file])
    real, _ = ok(project(at), ["./mote", "-S", "-O", prog_file])
    assert out == real
    rows = []
    for ln in err.splitlines():
        _, idx, name, n, reg = ln.split()
        rows.append((int(idx), name, int(n), None if reg == "-" else reg))
    return rows


def who_fig():
    at = "01.11"
    d = project(at)
    rows = uses(at, "programs/primes.mote")
    tree_text, _ = ok(d, ["./mote", "--tree", "programs/primes.mote"])
    for idx, name, n, _ in rows:
        assert len(re.findall(rf"\b{name}#{idx}\b", tree_text)) == n, (name, n)
    order = sorted(rows, key=lambda r: (-r[2], r[0]))
    assert [r[3] for r in order] == ["s1", "s2", "s3", "s4"], order
    assert [(r[1], r[2]) for r in order] == [("p", 8), ("d", 7), ("prime", 3), ("n", 2)], order
    listing, _ = ok(d, ["./mote", "-S", "-O", "programs/primes.mote"])
    assert "    call getint\n    mv   s4, a0\n    li   s1, 2\n" in listing     # read n; p := 2
    # more than eleven: a program with 13 variables, all used alike; the two of them improve()
    # reaches last keep their slots
    many = "read v0\n" + "".join(f"v{k} := v{k - 1} + 1\n" for k in range(1, 13)) + "write v12\n"
    put(d, "many.mote", many)
    mrows = uses(at, "many.mote")
    kept = [r[1] for r in mrows if r[3] is None]
    assert len(mrows) == 13 and sum(1 for r in mrows if r[3]) == 11 and kept == ["v11", "v12"], mrows
    mlist, _ = ok(d, ["./mote", "-S", "-O", "many.mote"])
    assert "# v11" in mlist and "# v12" in mlist and "# v10" not in mlist
    for opt in ([], ["-O"]):
        put(d, "many.s", ok(d, ["./mote", "-S"] + opt + ["many.mote"])[0])
        assert ok(d, ["./machine", "many.s"], "0\n")[0] == "12\n"

    f = Fig("wg0111", "Which variables get a register: counted by use, the most used first, eleven at most", 0)
    f.text(24, 22, "primes.mote: each variable's appearances in the tree", "tm", 11.5)
    f.text(560, 22, "register", "tm", 11.5, "middle")
    x0, y0, bh, gap = 96, 40, 26, 12
    unit = 40
    for k, (idx, name, n, reg) in enumerate(order):
        y = y0 + k * (bh + gap)
        f.text(x0 - 12, y + 18, name, "t", 14, "end", 700, mono=True)
        f.rect(x0, y, n * unit, bh, "a af", 3)
        f.text(x0 + n * unit + 8, y + 18, str(n), "t", 14, weight=700, mono=True)
        f.chip(560, y + 1, reg, "a af", "ta", 13, h=24, weight=700, w=48)
    ys = y0 + len(order) * (bh + gap) + 18
    f.text(24, ys, "s1 to s11: the eleven registers the improver hands out", "tm", 11.5)
    taken = {r[3] for r in order}
    for k in range(11):
        reg = f"s{k + 1}"
        x = 24 + k * 54
        hot = reg in taken
        f.rect(x, ys + 10, 48, 24, "a af" if hot else "m f", 12, dash=not hot)
        f.text(x + 24, ys + 26.5, reg, "ta" if hot else "tm", 12, "middle", 700 if hot else None, mono=True)
    f.text(24, ys + 58, "A twelfth variable gets none: it keeps its slot in memory, with ld and sd.", "t", 12)
    f.h = ys + 72
    return f


def three_counts_fig():
    at = "01.11"
    d = project(at)
    by_hand = source(at, "programs/gcd.s")
    plain, _ = ok(d, ["./mote", "-S", "programs/gcd.mote"])
    improved, _ = ok(d, ["./mote", "-S", "-O", "programs/gcd.mote"])
    res = []
    for lab, sub, listing in (("by hand", "gcd.s", by_hand), ("compiled", "mote -S", plain),
                              ("improved", "mote -S -O", improved)):
        out, n = count(d, listing, GCD_IN)
        assert out == "21\n", (lab, out)
        res.append((lab, sub, n))
    assert [n for _, _, n in res] == [53, 142, 61], res
    # the 8 beyond the hand-written program: the if's jump to its end, where the while's jump waits
    _, rows, _ = trace(d, improved, GCD_IN)
    lines = improved.splitlines()
    k4 = next(k for k, s in enumerate(lines, 1) if s.split() == ["j", ".L4"])
    assert lines[lines.index(".L4:") + 1].split() == ["j", ".L1"]
    twice = sum(1 for r in rows if r[0] == k4)
    assert twice == res[2][2] - res[0][2] == 8, twice
    insns = lambda t: sum(1 for s in t.splitlines() if s.startswith("    ") and not s.strip().startswith("#"))  # noqa
    assert insns(by_hand) == insns(improved) == 14

    f = Fig("tc0111", "Instructions run for the same answer, 21: by hand, compiled, and improved", 0)
    f.text(24, 22, "./machine --count on 1071 462; each prints 21", "tm", 11.5)
    x0, y0, bh, gap = 150, 42, 34, 22
    scale = 400 / max(n for _, _, n in res)
    for k, (lab, sub, n) in enumerate(res):
        y = y0 + k * (bh + gap)
        f.text(x0 - 14, y + 15, lab, "t", 13.5, "end", 700)
        f.text(x0 - 14, y + 30, sub, "tm", 11, "end", mono=True)
        f.rect(x0, y, n * scale, bh, "a af" if k else "s fs", 4)
        f.text(x0 + n * scale + 10, y + 23, str(n), "t", 17, weight=700, mono=True)
    y = y0 + 2 * (bh + gap)
    hx = x0 + res[0][2] * scale                    # where the hand-written count ends
    f.line(hx, y - 7, hx, y + bh + 7, "s", dash=True)
    f.text(x0 + res[2][2] * scale + 46, y + 15, f"{twice} more than by hand:", "tm", 11.5)
    f.text(x0 + res[2][2] * scale + 46, y + 30, "j .L4, a jump to a jump", "tm", 11.5)
    f.h = y + bh + 16
    return f


FIGS = [
    ("01.09-walk", walk_fig, True),
    ("01.09-per-pass", per_pass_fig, False),
    ("01.10-slots", slots_fig, False),
    ("01.10-statement", statement_fig, True),
    ("01.10-while", while_fig, False),
    ("01.11-before-after", before_after_fig, False),
    ("01.11-who-gets-a-register", who_fig, False),
    ("01.11-three-counts", three_counts_fig, False),
]


def main(argv):
    try:
        for name, fn, stepped in FIGS:
            if argv and not any(name.startswith(a) for a in argv):
                continue
            write(name, fn(), stepped)
    finally:
        for t in _TMP:
            shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    main(sys.argv[1:])
