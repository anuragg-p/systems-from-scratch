"""Helpers for the cc track's lesson figures (art/cc/archmap.py, figs00.py, figs01.py, figs02.py).

Drawing: the Fig class of art/kilo/figlib.py, with text never under 10px and code set on a
monospace grid (code(): each run of a line at its own column, x = left + column * 0.6em, Geist
Mono's advance, so indentation, double spaces and a caret under a column survive SVG). Classes are
the .art ones from harness/web/app.css, nothing else, so dark mode works:
  s m a        stroke: foreground, muted, accent
  f fs af fa   fill: page, code background, accent-soft, accent
  t tm ta      text fill: foreground, muted, accent      mono: monospace

The project: every figure is drawn from the project as the site shows it at its lesson.
project(at) writes it with ./learn files cc --at NN.LL into a temporary directory and builds it
with make -s; cc(), tokens(), tree() and asm() run its ./cc on a source text; sh() runs anything
else there (./ccrun, ./same, the toolchain). patched(at, edits) is a scratch copy with some text
replaced, for a figure that needs to see inside a run (a trace) or a variant of the code. A
missing toolchain or QEMU stops the generator with one line (tools()).

simulate() runs the emitted instructions on a register file: the handful of RV64IM instructions
and pseudo-instructions the compiler writes in modules 00 to 02, and those of rt/start.S as
objdump prints them.

write() checks a figure before it lands: ASCII, kept whole by the site's sanitizer, and, for a
stepped figure, steppable within the site's limits (art/steps.py).
"""
import functools
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))      # art/, for steps
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True                  # read harness/, never write into it
import steps  # noqa: E402
from harness.web.art import sanitize  # noqa: E402

LESSONS = os.path.join(ROOT, "tracks", "cc", "lessons")
MODULES = {"00": "00-the-smallest-compiler", "01": "01-tokens", "02": "02-expressions"}
SW = 'stroke-width="1.5"'
EM = 0.6                 # the monospace advance, in em
MIN_TEXT = 10


def esc(s):
    return html.escape(s, quote=True)


def fmt(v):
    if isinstance(v, float):
        v = round(v, 2)
        if v == int(v):
            v = int(v)
    return str(v)


def cw(size):
    """The width of one monospace column at font size `size`."""
    return EM * size


def tw(s, size=12, mono=False):
    """Rough text width in px (Figtree about 0.54em, Geist Mono 0.6em)."""
    return len(s) * size * (EM if mono else 0.54)


class Fig:
    def __init__(self, key, title, height, width=640):
        self.key, self.title, self.h, self.w, self.out = key, title, height, width, []

    def add(self, s):
        self.out.append(s)

    def rect(self, x, y, w, h, cls="s f", rx=6, dash=False, sw=True, extra=""):
        d = ' stroke-dasharray="4 4"' if dash else ""
        s = f" {SW}" if sw else ""
        self.add(f'<rect class="{cls}" x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" '
                 f'rx="{fmt(rx)}"{s}{d}{extra}/>')

    box = rect

    def text(self, x, y, s, cls="t", size=12, anchor="start", weight=None, mono=False):
        assert size >= MIN_TEXT, (self.key, s, size)
        c = cls + (" mono" if mono else "")
        wt = f' font-weight="{weight}"' if weight else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text class="{c}" x="{fmt(x)}" y="{fmt(y)}" font-size="{fmt(size)}"{wt}{a}>{esc(s)}</text>')

    def rich(self, x, y, parts, size=12, anchor="start", weight=None, cls="t"):
        """Text whose parts flow one after another: parts is a list of (text, class, mono)."""
        assert size >= MIN_TEXT
        wt = f' font-weight="{weight}"' if weight else ""
        an = f' text-anchor="{anchor}"' if anchor != "start" else ""
        inner = "".join(f'<tspan class="{(c or cls) + (" mono" if mono else "")}">{esc(t)}</tspan>'
                        for t, c, mono in parts)
        self.add(f'<text class="{cls}" x="{fmt(x)}" y="{fmt(y)}" font-size="{fmt(size)}"{wt}{an}>{inner}</text>')

    def code(self, x, y, s, size=12, cls="t", spans=(), weight=None):
        """One line of code on the monospace grid: column c sits at x + c * 0.6em. spans is a list
        of (start, end, class) that recolour columns start..end-1. Runs split at two or more
        spaces, at a leading indent and at a change of class, each a tspan at its own column."""
        assert size >= MIN_TEXT
        kinds = [cls] * len(s)
        for st, en, c in spans:
            for i in range(st, min(en, len(s))):
                kinds[i] = c
        runs, i = [], 0
        while i < len(s):
            if s[i] == " ":
                i += 1
                continue
            j = i
            while j < len(s):
                if s[j] == " ":
                    if j + 1 < len(s) and s[j + 1] != " " and kinds[j + 1] == kinds[i]:
                        j += 1
                        continue
                    break
                if kinds[j] != kinds[i]:
                    break
                j += 1
            runs.append((i, s[i:j], kinds[i]))
            i = j
        if not runs:
            return
        c = cw(size)
        wt = f' font-weight="{weight}"' if weight else ""
        if len(runs) == 1 and runs[0][0] == 0:
            self.add(f'<text class="{runs[0][2]} mono" x="{fmt(x)}" y="{fmt(y)}" font-size="{fmt(size)}"{wt}>'
                     f'{esc(runs[0][1])}</text>')
            return
        inner = "".join(f'<tspan x="{fmt(round(x + col * c, 2))}"'
                        f'{"" if k == cls else " class=" + chr(34) + k + chr(34)}>{esc(t)}</tspan>'
                        for col, t, k in runs)
        self.add(f'<text class="{cls} mono" x="{fmt(x)}" y="{fmt(y)}" font-size="{fmt(size)}"{wt}>{inner}</text>')

    def _marker(self, cls):
        return {"a": "aa", "m": "am"}.get(cls.split()[0], "ah")

    def line(self, x1, y1, x2, y2, cls="s", arrow=False, dash=False, start=False, sw=None):
        m = f' marker-end="url(#{self.key}-{self._marker(cls)})"' if arrow else ""
        if start:
            m += f' marker-start="url(#{self.key}-{self._marker(cls)})"'
        d = ' stroke-dasharray="4 4"' if dash else ""
        w = f'stroke-width="{sw}"' if sw else SW
        self.add(f'<line class="{cls}" x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" {w} '
                 f'stroke-linecap="round"{m}{d}/>')

    def path(self, d, cls="s", arrow=False, dash=False, start=False, sw=None):
        m = f' marker-end="url(#{self.key}-{self._marker(cls)})"' if arrow else ""
        if start:
            m += f' marker-start="url(#{self.key}-{self._marker(cls)})"'
        da = ' stroke-dasharray="4 4"' if dash else ""
        w = f'stroke-width="{sw}"' if sw else SW
        self.add(f'<path class="{cls}" d="{d}" {w} stroke-linecap="round" stroke-linejoin="round"{m}{da}/>')

    def poly(self, pts, cls="s", arrow=False, dash=False, start=False):
        self.path("M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts), cls, arrow, dash, start)

    def circle(self, cx, cy, r, cls="s f", dash=False):
        d = ' stroke-dasharray="4 4"' if dash else ""
        self.add(f'<circle class="{cls}" cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}" {SW}{d}/>')

    def label_box(self, x, y, w, h, label, cls="s f", tcls="t", size=12, mono=True, rx=6, weight=None,
                  dash=False, sub=None, subcls="tm", subsize=10.5, submono=False):
        self.rect(x, y, w, h, cls, rx, dash)
        if sub is None:
            self.text(x + w / 2, y + h / 2 + size * 0.36, label, tcls, size, "middle", weight, mono)
        else:
            self.text(x + w / 2, y + h / 2 - 2, label, tcls, size, "middle", weight, mono)
            self.text(x + w / 2, y + h / 2 + subsize + 1, sub, subcls, subsize, "middle", None, submono)

    def chip(self, cx, y, s, cls="s f", tcls="t", size=12, mono=True, h=24, weight=None, w=None):
        """A pill centred on cx, its width from the text (monospace exact, sans estimated)."""
        w = w or round(tw(s, size, mono) + 18)
        self.rect(cx - w / 2, y, w, h, cls, h / 2)
        self.text(cx, y + h / 2 + size * 0.35, s, tcls, size, "middle", weight, mono)
        return w

    def brace_h(self, x1, x2, y, cls="m", up=False):
        """A flat bracket under (or over) a span."""
        d = -6 if up else 6
        self.path(f"M{fmt(x1)} {fmt(y - d)} L{fmt(x1)} {fmt(y)} L{fmt(x2)} {fmt(y)} L{fmt(x2)} {fmt(y - d)}", cls)

    def page(self, x, y, w, h, cls="s f", dash=False, fold=9):
        """A file: a rectangle with its top right corner folded."""
        self.path(f"M{fmt(x)} {fmt(y)} H{fmt(x + w - fold)} L{fmt(x + w)} {fmt(y + fold)} V{fmt(y + h)} H{fmt(x)} Z",
                  cls, dash=dash)
        self.path(f"M{fmt(x + w - fold)} {fmt(y)} V{fmt(y + fold)} H{fmt(x + w)}", cls.split()[0], dash=dash)

    def svg(self):
        def mk(name, cls):
            return (f'<marker id="{self.key}-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" '
                    f'markerHeight="7" orient="auto-start-reverse"><path class="{cls}" d="M1 1.5L8.5 5L1 8.5" {SW} '
                    f'stroke-linecap="round" stroke-linejoin="round"/></marker>')
        defs = "<defs>" + mk("ah", "s") + mk("aa", "a") + mk("am", "m") + "</defs>"
        body = "\n".join(self.out)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {fmt(self.h)}" fill="none">\n'
                f'<title>{esc(self.title)}</title>\n{defs}\n{body}\n</svg>\n')


# ------------------------------------------------------------------ checks and writing

def sane(svg, what):
    """svg, once the site's sanitizer (harness/web/art.py) has kept every element and every
    attribute of it; stop if it would refuse or cut any."""
    out = sanitize(svg)
    tags = re.findall(r"<(\w+)", svg)
    attrs = sorted(re.findall(r'\s([\w-]+)="', svg) + ["aria-hidden", "focusable"])
    if not out or re.findall(r"<(\w+)", out) != tags or sorted(re.findall(r'\s([\w-]+)="', out)) != attrs:
        raise SystemExit(f"the sanitizer would refuse or cut {what}")
    return svg


def write(name, fig, stepped=False):
    """Write fig as tracks/cc/lessons/<module of name>/figures/<name>.svg after the checks; return
    the path. stepped: it must step on the site (art/steps.py), and the frame count is printed."""
    text = fig.svg()
    try:
        text.encode("ascii")
    except UnicodeEncodeError as e:
        raise SystemExit(f"{name}: not ASCII: {e}")
    sane(text, name)
    note = ""
    if stepped:
        note = f"  ({steps.check(text)} steps)"
    elif sanitize(text) and re.search(r'<g class="step">', text):
        raise SystemExit(f"{name}: has step groups but is not meant to be stepped")
    d = os.path.join(LESSONS, MODULES[name[:2]], "figures")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name + ".svg")
    with open(p, "w") as f:
        f.write(text)
    print(os.path.relpath(p, ROOT) + note)
    return p


# ------------------------------------------------------------------ the project at a lesson

PREFIXES = ("riscv64-elf-", "riscv64-unknown-elf-", "riscv64-linux-gnu-")


@functools.lru_cache(None)
def tools():
    """The RISC-V tool prefix (riscv64-elf- or another, as ccrun looks for them); stop with one
    line if there is no toolchain or no QEMU."""
    for p in PREFIXES:
        if shutil.which(p + "as") and shutil.which(p + "gcc"):
            break
    else:
        raise SystemExit("art/cc: no RISC-V toolchain (riscv64-elf-as and riscv64-elf-gcc, or another prefix "
                         "ccrun knows): install it to draw these figures")
    if not shutil.which("qemu-system-riscv64"):
        raise SystemExit("art/cc: no qemu-system-riscv64: install QEMU to draw these figures")
    return p


_TMP = []


def _scratch(tag):
    if not _TMP:
        _TMP.append(tempfile.mkdtemp(prefix="cc-art-"))
    d = os.path.join(_TMP[0], tag)
    shutil.rmtree(d, ignore_errors=True)
    return d


def _make(d):
    r = subprocess.run(["make", "-s"], cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"art/cc: make failed in {d}:\n{r.stdout}{r.stderr}")


@functools.lru_cache(None)
def project(at):
    """The project as the site shows it at lesson `at`, written by ./learn files and built."""
    tools()
    d = _scratch(at)
    subprocess.run([os.path.join(ROOT, "learn"), "files", "cc", "--at", at, d], check=True,
                   stdout=subprocess.DEVNULL)
    _make(d)
    return d


def patched(at, tag, edits):
    """A scratch copy of the project at `at` with each (file, old, new) edit made (old must occur
    exactly once; None appends new at the end), built; for a trace or a variant of the code.
    Returns its directory."""
    src = project(at)
    d = _scratch(f"{at}-{tag}")
    shutil.copytree(src, d, ignore=shutil.ignore_patterns("build", "*.o", "cc"))
    for fn, old, new in edits:
        p = os.path.join(d, fn)
        with open(p) as f:
            text = f.read()
        if old is None:
            with open(p, "w") as f:
                f.write(text + new)
            continue
        if text.count(old) != 1:
            raise SystemExit(f"art/cc: patch for {tag}: {old!r} occurs {text.count(old)} times in {fn} at {at}")
        with open(p, "w") as f:
            f.write(text.replace(old, new))
    _make(d)
    return d


def source(at, name):
    """A file of the project at `at`, as text."""
    with open(os.path.join(project(at), name)) as f:
        return f.read()


def sh(d, args, env=None, timeout=60):
    """Run args in directory d: (stdout, stderr, status)."""
    e = dict(os.environ)
    e.update(env or {})
    r = subprocess.run(args, cwd=d, capture_output=True, text=True, env=e, timeout=timeout)
    return r.stdout, r.stderr, r.returncode


def put(d, name, text):
    with open(os.path.join(d, name), "w") as f:
        f.write(text)
    return name


def cc(at, src, *opts, name="t.c", d=None):
    """./cc [opts] on a file holding src, in the project at `at` (or directory d)."""
    d = d or project(at)
    put(d, name, src)
    return sh(d, ["./cc", *opts, name])


def tokens(at, src, d=None):
    """--tokens of src: [(line, col, kind, text, value or None)], the eof token last."""
    out, err, st = cc(at, src, "--tokens", d=d)
    assert st == 0, (at, src, err)
    toks = []
    for ln in out.splitlines():
        m = re.match(r"^(\d+):(\d+) (\w+)(?: (.*))?$", ln)
        assert m, ln
        line, col, kind, rest = int(m[1]), int(m[2]), m[3], m[4]
        val = None
        if kind in ("num", "str"):
            rest, val = rest.rsplit(" ", 1)
            val = int(val)
        toks.append((line, col, kind, rest or "", val))
    return toks, out


def parse_tree(text):
    """--tree output -> nested (op, value or None, [children])."""
    rows = []
    for ln in text.splitlines():
        ind = len(ln) - len(ln.lstrip(" "))
        assert ind % 2 == 0, ln
        parts = ln.strip().split(" ")
        op = parts[0]
        val = int(parts[1]) if op == "num" else None
        rows.append((ind // 2, op, val))
    pos = [0]

    def node(depth):
        d, op, val = rows[pos[0]]
        assert d == depth, (rows[pos[0]], depth)
        pos[0] += 1
        kids = []
        while pos[0] < len(rows) and rows[pos[0]][0] == depth + 1:
            kids.append(node(depth + 1))
        return (op, val, kids)

    t = node(0)
    assert pos[0] == len(rows)
    return t


def tree(at, src, d=None):
    out, err, st = cc(at, src, "--tree", d=d)
    assert st == 0, (at, src, err)
    return parse_tree(out), out


def asm(at, src, d=None):
    """./cc's assembly for src: the list of lines, as written (two spaces before instructions)."""
    out, err, st = cc(at, src, d=d)
    assert st == 0, (at, src, err)
    return out.splitlines()


def ccrun(at, src):
    d = project(at)
    put(d, "t.c", src)
    out, err, st = sh(d, ["./ccrun", "t.c"])
    return st


def tree_eval(t):
    op, val, kids = t
    if op == "num":
        return val
    v = [tree_eval(k) for k in kids]
    if len(v) == 1:
        return {"-": lambda a: -a, "!": lambda a: int(not a), "~": lambda a: ~a}[op](v[0])
    a, b = v
    return {"+": a + b, "-": a - b, "*": a * b, "/": int(a / b) if b else None, "%": a - b * int(a / b) if b else None,
            "<<": a << b, ">>": a >> b, "&": a & b, "|": a | b, "^": a ^ b, "==": int(a == b), "!=": int(a != b),
            "<": int(a < b), "<=": int(a <= b)}[op]


# ------------------------------------------------------------------ running the instructions

MASK = (1 << 64) - 1


def s64(v):
    v &= MASK
    return v - (1 << 64) if v >> 63 else v


def _imm(s):
    return int(s, 0)


def simulate(lines, regs=None, mem=None, sp=0x80010040):
    """Run the instructions in `lines` (assembly as ./cc writes it, or objdump's mnemonic and
    operands), one after another with no jumps taken unless asked: returns [(line, regs after, mem
    after)] for each instruction. regs maps names to signed 64-bit values; mem maps addresses to
    8-byte values. Labels and directives are skipped."""
    r = dict(regs or {})
    r.setdefault("sp", sp)
    r["zero"] = 0
    m = dict(mem or {})
    out = []
    for raw in lines:
        s = raw.strip()
        if not s or s.endswith(":") or s.startswith("."):
            continue
        op, _, rest = s.partition(" ")
        a = [x.strip() for x in rest.split(",")] if rest.strip() else []
        g = lambda x: r.get(x, 0)  # noqa: E731
        if op == "li":
            r[a[0]] = s64(_imm(a[1]))
        elif op == "mv":
            r[a[0]] = g(a[1])
        elif op in ("add", "sub", "mul", "div", "rem", "and", "or", "xor", "sll", "sra", "slt"):
            x, y = g(a[1]), g(a[2])
            v = {"add": x + y, "sub": x - y, "mul": x * y,
                 "div": (abs(x) // abs(y)) * (1 if (x < 0) == (y < 0) else -1) if y else -1,
                 "rem": (x - y * ((abs(x) // abs(y)) * (1 if (x < 0) == (y < 0) else -1))) if y else x,
                 "and": x & y, "or": x | y, "xor": x ^ y, "sll": x << (y & 63), "sra": x >> (y & 63),
                 "slt": int(x < y)}[op]
            r[a[0]] = s64(v)
        elif op in ("addi", "xori", "andi", "slli", "addiw"):
            x, i = g(a[1]), _imm(a[2])
            if op == "slli":
                v = x << i
            elif op == "addiw":
                v = (x + i) & 0xffffffff
                v = v - (1 << 32) if v >> 31 else v
            else:
                v = {"addi": x + i, "xori": x ^ i, "andi": x & i}[op]
            r[a[0]] = s64(v)
        elif op == "lui":
            v = (_imm(a[1]) << 12) & 0xffffffff
            r[a[0]] = s64(v - (1 << 32) if v >> 31 else v)
        elif op == "zext.b":
            r[a[0]] = g(a[1]) & 0xff
        elif op in ("seqz", "snez", "neg", "not"):
            x = g(a[1])
            r[a[0]] = {"seqz": int(x == 0), "snez": int(x != 0), "neg": s64(-x), "not": s64(~x)}[op]
        elif op in ("sd", "sw", "ld"):
            mo = re.match(r"^(-?\w+)\((\w+)\)$", a[1])
            addr = g(mo[2]) + _imm(mo[1])
            if op == "ld":
                r[a[0]] = m[addr]
            else:
                m[addr] = g(a[0]) if op == "sd" else g(a[0]) & 0xffffffff
        elif op in ("ret", "beqz", "jal", "auipc", "j"):
            raise ValueError(f"simulate: {op} needs the caller's pc (see figs00.run_start)")
        else:
            raise ValueError(f"simulate: no {op}")
        r["zero"] = 0
        out.append((s, dict(r), dict(m)))
    return out


def instructions(lines):
    """The instruction lines of ./cc's output before its ret, stripped (no directives or labels)."""
    out = [s.strip() for s in lines if s.strip() and not s.strip().endswith(":") and not s.strip().startswith(".")]
    assert out[-1] == "ret", out
    return out[:-1]


# ------------------------------------------------------------------ trees

def layout(t, x0, y0, dx, dy):
    """Positions for a tree's nodes: leaves one dx apart left to right (in order), each parent
    over the middle of its children, a level dy down. Returns ([(node id, (op, val), x, y)],
    [(parent id, child id)]); a node id is its path from the root, a tuple of child indexes."""
    nodes, edges = [], []
    n = [0]

    def walk(t, path, depth):
        op, val, kids = t
        if not kids:
            x = x0 + n[0] * dx
            n[0] += 1
        else:
            xs = [walk(k, path + (i,), depth + 1) for i, k in enumerate(kids)]
            for i in range(len(kids)):
                edges.append((path, path + (i,)))
            x = sum(xs) / len(xs) if len(xs) > 1 else xs[0]
        nodes.append((path, (op, val), x, y0 + depth * dy))
        return x

    walk(t, (), 0)
    return nodes, edges


def label(op, val):
    return str(val) if op == "num" else op


def draw_tree(f, t, x0, y0, dx, dy, r=15, cls_of=None, size=13, edge_cls_of=None, pos=None):
    """Draw a tree (from parse_tree) as circles joined by lines. cls_of(path, op) -> (shape class,
    text class) or None for the plain look; pos: positions from layout() to use instead. Returns
    {path: (x, y)}."""
    nodes, edges = pos or layout(t, x0, y0, dx, dy)
    at = {p: (x, y) for p, _, x, y in nodes}
    for a, b in edges:
        (x1, y1), (x2, y2) = at[a], at[b]
        d = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        ec = edge_cls_of(a, b) if edge_cls_of else "s"
        f.line(x1 + ux * r, y1 + uy * r, x2 - ux * r, y2 - uy * r, ec)
    for p, (op, val), x, y in nodes:
        sc, tc = (cls_of(p, op) if cls_of else None) or ("s f", "t")
        f.circle(x, y, r, sc)
        lab = label(op, val)
        f.text(x, y + size * 0.36, lab, tc, size if len(lab) < 3 else size - 2, "middle", 600, mono=True)
    return at
