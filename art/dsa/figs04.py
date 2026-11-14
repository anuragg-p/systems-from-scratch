"""Figures for dsa module 04, Finding text: grep (lessons 04.01 to 04.04).

    python3 -B art/dsa/figs04.py

The project at each lesson is written with ./learn files and built, and every frame of a
stepped figure is made from what the real bin/grep prints with DS_TRACE=1 (and its counts
from DS_STATS=1), so a figure cannot say something the code does not do:

  04.01-horspool   sed -n 3284p data/book.txt | DS_TRACE=1 bin/grep -F woman
                   (and --algo=scan, for the last frame); the shift table is worked out
                   here as search_init() does, and checked against every shift in the trace
  04.02-tree       the tree of (a|b)*abb: a model of re.c's parser, checked against the
                   real node count (DS_STATS=1) and the pattern parts the backtracker's
                   trace names
  04.03-nfa        printf 'aabaaa\\n' | DS_TRACE=1 bin/grep -E --algo=nfa 'a?a?a?aaa': the
                   machine as the trace prints it, and the live states after each byte
  04.04-dfa        printf 'aabaaa\\naaa\\n' | DS_TRACE=1 bin/grep -E --algo=dfa 'a?a?a?aaa':
                   each set of NFA states made a DFA state the first time, reused after
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import figlib  # noqa: E402
from figlib import Fig, write  # noqa: E402
import steps  # noqa: E402

figlib.LESSONS = os.path.join(ROOT, "tracks", "dsa", "lessons")
MOD = "04-grep"

_built = {}


def project(at):
    if at not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="dsa-figs04-"), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["make", "-s"], cwd=d, check=True)
        _built[at] = d
    return _built[at]


def grep(at, args, data):
    """bin/grep at lesson `at` with DS_TRACE and DS_STATS: (stdout, trace lines, stats)."""
    d = project(at)
    env = dict(os.environ, DS_TRACE="1", DS_STATS="1", LC_ALL="C")
    r = subprocess.run([os.path.join(d, "bin", "grep")] + args, input=data, cwd=d, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert r.returncode in (0, 1), r
    err = r.stderr.decode()
    trace = [l[len("trace: "):] for l in err.splitlines() if l.startswith("trace: ")]
    st = {}
    for m in re.finditer(r"^stats: ([^:]+): (.*)$", err, re.M):
        st[m.group(1)] = {k: int(v) for k, v in (p.rsplit(" ", 1) for p in m.group(2).split(", "))}
    return r.stdout.decode(), trace, st


def book_line(n):
    with open(os.path.join(ROOT, "tracks", "dsa", "data", "book.txt"), "rb") as f:
        return f.read().split(b"\n")[n - 1] + b"\n"


# ------------------------------------------------------------------ 04.01

HORS = re.compile(r"^horspool: at (\d+): examined (\d+), (?:match|mismatch at (\d+), '(.+)' under the last byte, shift (\d+))$")
SCAN = re.compile(r"^scan: at (\d+): examined (\d+), (?:match|mismatch at (\d+), shift 1)$")


def horspool0401():
    line = book_line(3284)
    pat = "woman"
    m = len(pat)
    out, trace, st = grep("04.01", ["-F", pat], line)
    assert out.encode() == line
    _, strace, sst = grep("04.01", ["-F", "--algo=scan", pat], line)
    # search_init(): every byte shifts m, a byte of the pattern but its last m-1-i, the last place wins
    shift = {c: m for c in range(256)}
    for i in range(m - 1):
        shift[ord(pat[i])] = m - 1 - i
    text = line.decode().rstrip("\n")
    n = len(line)                      # the search runs over the whole text, newline and all
    steps_ = []
    pos = exm = skp = 0
    for t in trace:
        g = HORS.match(t)
        assert g, t
        at, ex = int(g.group(1)), int(g.group(2))
        pos += 1
        exm += ex
        if g.group(3) is None:
            steps_.append(dict(at=at, ex=ex, match=True, pos=pos, exm=exm, skp=skp))
            continue
        j, c, s = int(g.group(3)), g.group(4), int(g.group(5))
        assert c == text[at + m - 1] and s == shift[ord(c)] and ex == m - j, (t, shift[ord(c)])
        skp += min(s - 1, n - m - at)
        steps_.append(dict(at=at, ex=ex, match=False, j=j, c=c, s=s, pos=pos, exm=exm, skp=skp))
    assert (pos, exm, skp) == (st["search"]["positions"], st["search"]["examined"], st["search"]["skipped"]), st
    looked_s = {}
    for t in strace:
        g = SCAN.match(t)
        assert g, t
        at, ex = int(g.group(1)), int(g.group(2))
        for k in range(at, at + ex):
            looked_s[k] = looked_s.get(k, 0) + 1
    looked_h = {}
    for s_ in steps_:
        for k in range(s_["at"] + m - s_["ex"], s_["at"] + m):
            looked_h[k] = looked_h.get(k, 0) + 1
    assert sum(looked_s.values()) == sst["search"]["examined"]
    print("04.01 horspool:", [(s_["at"], s_["ex"], s_.get("s")) for s_ in steps_], st["search"], "scan", sst["search"])

    f = Fig("f0401a", "Horspool's search for woman along line 3284 of the book: compare from the pattern's "
            "last byte, and let the byte of the text under it say how far to move on", 276)
    f.text(24, 22, "sed -n 3284p data/book.txt | DS_TRACE=1 bin/grep -F woman", "t", 11, mono=True)
    # the shift table, worked out before the search
    f.text(24, 48, "the shift table: how far the byte under the pattern's last byte moves it on", "tm", 10.5)
    cells = [("w", shift[ord("w")]), ("o", shift[ord("o")]), ("m", shift[ord("m")]), ("a", shift[ord("a")])]
    x = 24
    for c, s in cells:
        f.rect(x, 58, 46, 22, "s fs", 4)
        f.text(x + 14, 73, c, "t", 12, "middle", 700, mono=True)
        f.text(x + 34, 73, str(s), "ta", 12, "middle", 600, mono=True)
        x += 52
    f.rect(x, 58, 200, 22, "s fs", 4)
    f.text(x + 10, 73, "n, and every other byte", "t", 11.5)
    f.text(x + 188, 73, str(shift[ord("n")]), "ta", 12, "end", 600, mono=True)
    CW, X0, TY, PY = 17, 72, 124, 158
    show = 32
    for k in range(0, show, 5):
        f.text(X0 + k * CW + (CW - 2) / 2, TY - 6, str(k), "tm", 9.5, "middle", mono=True)

    def name(ch):
        return "a space" if ch == " " else f"\"{ch}\""

    def row(y, label, style, chars=None, start=0):
        f.text(X0 - 8, y + 15, label, "tm", 10.5, "end")
        for k in range(start, start + len(chars) if chars else show):
            bc, tc = style(k)
            f.rect(X0 + k * CW, y, CW - 2, 22, bc, 3)
            ch = chars[k - start] if chars else text[k]
            if ch != " ":
                f.text(X0 + k * CW + (CW - 2) / 2, y + 15, ch, tc, 12, "middle", 600 if tc != "tm" else None,
                       mono=True)

    def counters(s_):
        f.text(616, 48, f"positions {s_['pos']}", "t", 11, "end", mono=True)
        f.text(616, 64, f"examined {s_['exm']}", "ta", 11, "end", 600, mono=True)
        f.text(616, 80, f"skipped {s_['skp']}", "t", 11, "end", mono=True)

    for s_ in steps_:
        at, ex = s_["at"], s_["ex"]
        lo = at + m - ex                       # the bytes compared: from the last back to this one
        if s_["match"]:
            cap = (f"At {at}: all {m} bytes are the same, compared from the last back to the first: a match. "
                   f"grep backs up to the start of the line and prints it.")
        else:
            c, s, j = s_["c"], s_["s"], s_["j"]
            if ex == 1:
                cmpd = f"At {at}: {name(c)} under the pattern's last byte is not \"{pat[-1]}\"."
            else:
                cmpd = f"At {at}: the last {ex - 1} bytes match, then {name(text[at + j])} is not \"{pat[j]}\"."
            if c not in pat:
                why = f"{name(c)} is not in the pattern at all: move on {s}, the whole length."
            elif c not in pat[:-1]:
                why = f"{name(c)} is in the pattern only as its last byte: move on {s}, the whole length."
            else:
                why = f"{name(c)} is in the pattern {s} from its end: move on {s}, which puts the pattern's {name(c)} under it."
            cap = cmpd + " " + why
        with steps.step(f, cap):
            counters(s_)

            def tstyle(k):
                if lo <= k < at + m:
                    return ("a af", "ta") if s_["match"] or k > lo else ("a fa", "f")
                return ("m f", "tm") if k < at else ("s f", "t")

            def pstyle(k):
                if k >= lo:
                    return ("a af", "ta") if s_["match"] or k > lo else ("a fa", "f")
                return "s f", "t"
            row(TY, "text", tstyle)
            row(PY, "pattern", pstyle, pat, at)
            if not s_["match"]:
                lx = X0 + (at + m - 1) * CW + (CW - 2) / 2
                f.line(lx, PY + 28, lx, PY + 40, "a")
                f.text(lx, PY + 54, f"{name(s_['c'])} under the last byte: shift {s_['s']}", "ta", 11,
                       "middle" if 150 < lx < 490 else ("start" if lx <= 150 else "end"), 600)
                x1 = X0 + at * CW + 2
                x2 = X0 + (at + s_["s"]) * CW + 2
                f.path(f"M{x1} {PY + 66} L{x1} {PY + 74} L{x2 - 3} {PY + 74}", "a", arrow=True)
                f.text(x1, PY + 92, f"next position: {at + s_['s']}", "tm", 10.5)
            else:
                f.text(X0 + at * CW, PY + 50, f"match at {at}", "ta", 12, weight=700)
    last = steps_[-1]["at"] + m
    with steps.step(f, f"The whole search: Horspool tried {st['search']['positions']} positions and compared "
                       f"{st['search']['examined']} bytes of text, {len(looked_h)} different ones; trying every "
                       f"position, the scan compares {sst['search']['examined']} to find the same match."):
        row(TY, "Horspool", lambda k: ("a af", "ta") if k in looked_h else
            (("m f", "tm") if k < last else ("s f", "t")))
        row(PY, "scan", lambda k: ("a af", "ta") if k in looked_s else (("m f", "tm") if k < last else ("s f", "t")))
        f.text(X0, PY + 50, f"Horspool: positions {st['search']['positions']}, examined {st['search']['examined']}",
               "ta", 12, weight=700, mono=True)
        f.text(X0, PY + 70, f"scan: positions {sst['search']['positions']}, examined {sst['search']['examined']}",
               "t", 12, mono=True)
        f.text(X0, PY + 92, "in the accent: the bytes each one compared; the others it never looked at", "tm",
               10.5)
    return f


# ------------------------------------------------------------------ 04.02

class Node:
    def __init__(self, op, src, kids=()):
        self.op, self.src, self.kids = op, src, list(kids)


def parse_model(pattern):
    """re.c's parser, for literals, ( ), |, * + ?: one function per level of the grammar."""
    pos = [0]
    depth = [0]
    P = pattern

    def atom():
        start = pos[0]
        c = P[pos[0]]
        pos[0] += 1
        if c == "(":
            depth[0] += 1
            r = alt()
            assert pos[0] < len(P)
            pos[0] += 1
            depth[0] -= 1
            r.src = P[start:pos[0]]
            return r
        assert c not in "*+?.[^$\\{"
        return Node(c, c)

    def repeat():
        start = pos[0]
        r = atom()
        while pos[0] < len(P) and P[pos[0]] in "*+?":
            op = {"*": "STAR", "+": "PLUS", "?": "QUEST"}[P[pos[0]]]
            pos[0] += 1
            r = Node(op, P[start:pos[0]], [r])
        return r

    def cat():
        start = pos[0]
        seq = None
        while pos[0] < len(P) and P[pos[0]] != "|" and not (P[pos[0]] == ")" and depth[0] > 0):
            r = repeat()
            seq = Node("CAT", P[start:pos[0]], [seq, r]) if seq else r
        return seq

    def alt():
        start = pos[0]
        a = cat()
        while pos[0] < len(P) and P[pos[0]] == "|":
            pos[0] += 1
            r = cat()
            a = Node("ALT", P[start:pos[0]], [a, r])
        return a

    return alt()


def walk(n):
    yield n
    for k in n.kids:
        yield from walk(k)


def tree0402():
    pat = "(a|b)*abb"
    tree = parse_model(pat)
    nodes = list(walk(tree))
    _, trace, st = grep("04.02", ["-E", pat], b"abaabb\n")
    assert st["regex"]["nodes"] == len(nodes), (st, len(nodes))
    named = set()
    for t in trace:
        g = re.match(r"^backtrack: (?:at \d+: (?:'.' against|the end against) (.+): (?:yes|no)|back at \d+: (.+), the other way)$", t)
        if g:
            named.add(g.group(1) or g.group(2))
    srcs = {n.src for n in nodes}
    assert named and named <= srcs, (named, srcs)
    print("04.02 tree:", len(nodes), "nodes; the trace names", sorted(named))

    f = Fig("f0402a", "The tree the parser makes of (a|b)*abb: one function for each rule of the grammar, "
            "each node labelled with the part of the pattern it was made from", 340)
    f.text(24, 24, "grep -E '(a|b)*abb'", "t", 12, weight=600, mono=True)
    f.text(24, 44, f"stats: regex: nodes {st['regex']['nodes']}", "tm", 10.5, mono=True)
    # the grammar, loosest rule first
    rules = [
        ("parse_alt", "alternatives", "seq | seq | ...", "ALT"),
        ("parse_cat", "a sequence", "rep rep ...", "CAT"),
        ("parse_repeat", "a repetition", "atom * + ?", "STAR PLUS QUEST"),
        ("parse_atom", "an atom", "a . [..] ^ $ ( alt )", "a byte, ^, $"),
    ]
    GY = 76
    f.text(24, GY - 8, "the grammar, loosest rule first: a function each", "tm", 10.5)
    for i, (fn, what, form, makes) in enumerate(rules):
        y = GY + i * 58
        f.rect(24, y, 212, 44, "s f", 6)
        f.text(34, y + 17, fn, "t", 12, weight=700, mono=True)
        f.text(226, y + 17, makes, "ta", 10.5, "end", 600, mono=makes.isupper() or " " not in makes)
        f.text(34, y + 35, form, "t", 11.5, mono=True)
        if i < 3:
            f.line(130, y + 44, 130, y + 58, "s", arrow=True)
    f.path(f"M236 {GY + 3 * 58 + 32} C 262 {GY + 3 * 58 + 32}, 262 {GY + 18}, 238 {GY + 18}", "a", arrow=True)
    f.text(24, GY + 4 * 58 + 6, "each rule calls the next, tighter one;", "tm", 10.5)
    f.text(24, GY + 4 * 58 + 21, "a group, ( alt ), calls the first again", "ta", 10.5)
    f.text(616, 24, "each node: what it is, and the part", "tm", 10.5, "end")
    f.text(616, 39, "of the pattern it was parsed from", "tm", 10.5, "end")

    # the tree: a node's place, (x, level)
    place = {}
    spine = []
    n = tree
    while n.op == "CAT":
        spine.append(n)
        n = n.kids[0]
    LV = lambda k: 58 + k * 46        # noqa: E731
    xs = [530, 464, 398]
    for k, c in enumerate(spine):
        place[id(c)] = (xs[k], k)
        place[id(c.kids[1])] = (xs[k] + 66, k + 1)
    star = spine[-1].kids[0]
    place[id(star)] = (332, len(spine))
    alt_ = star.kids[0]
    place[id(alt_)] = (332, len(spine) + 1)
    place[id(alt_.kids[0])] = (296, len(spine) + 2)
    place[id(alt_.kids[1])] = (368, len(spine) + 2)
    assert len(place) == len(nodes)
    BH = 36

    def box(nd):
        x, k = place[id(nd)]
        y = LV(k)
        leaf = not nd.kids
        w = 34 if leaf else 92
        return x - w / 2, y, w

    for nd in nodes:
        x0, y0, w = box(nd)
        for kid in nd.kids:
            kx, ky, kw = box(kid)
            f.line(x0 + w / 2, y0 + BH, kx + kw / 2, ky, "m")
    for nd in nodes:
        x0, y0, w = box(nd)
        if not nd.kids:
            f.rect(x0, y0 + 4, w, BH - 8, "a af", 6)
            f.text(x0 + w / 2, y0 + 23, nd.op, "ta", 13, "middle", 700, mono=True)
        else:
            f.rect(x0, y0, w, BH, "s f", 6)
            f.text(x0 + w / 2, y0 + 15, nd.op, "t", 11.5, "middle", 700, mono=True)
            f.text(x0 + w / 2, y0 + 29, nd.src, "tm", 10.5, "middle", mono=True)
    return f


# ------------------------------------------------------------------ 04.03 and 04.04

MACH = re.compile(r"^nfa: state (\d+): (?:split -> (\d+), (\d+)|match|(.+) -> (\d+))$")


def machine(trace):
    """The NFA as the trace prints it: {id: (kind, out, out1, label)}, and its start."""
    states, start = {}, None
    for t in trace:
        g = MACH.match(t)
        if g:
            i = int(g.group(1))
            if g.group(2):
                states[i] = ("split", int(g.group(2)), int(g.group(3)), "")
            elif g.group(4):
                states[i] = ("char", int(g.group(5)), -1, g.group(4))
            else:
                states[i] = ("match", -1, -1, "")
        g = re.match(r"^nfa: start (\d+)$", t)
        if g:
            start = int(g.group(1))
    return states, start


def ids(s):
    return [int(x) for x in s.strip("{}").split()] if s.strip("{}") else []


def nfa_layout(states):
    """Places for a?^n a^n's machine: the splits and the a's that must be read on one line, the
    optional a's above it, between their split and the next."""
    pos, x = {}, 0
    for i in sorted(states):
        kind, out, out1, _ = states[i]
        above = any(k2 == "split" and o == i and states[i][1] == o1 for k2, o, o1, _ in
                    (states[j] for j in states))
        if above:
            pos[i] = (x - 0.5, 1)
        else:
            pos[i] = (x, 0)
            x += 1
    return pos, x


def draw_nfa(f, states, start, live, y0, x0=44, dx=58, r=13):
    pos, _ = nfa_layout(states)

    def xy(i):
        c, row = pos[i]
        return x0 + c * dx, y0 - row * 50

    f.line(x0 - 34, y0, x0 - r - 2, y0, "s", arrow=True)
    f.text(x0 - 36, y0 - 6, "start", "tm", 9.5)
    for i, (kind, out, out1, label) in states.items():
        x, y = xy(i)
        for o, lab in ((out, label), (out1, "")):
            if o < 0:
                continue
            ox, oy = xy(o)
            if oy == y:
                f.line(x + r, y, ox - r - 2, oy, "s", arrow=True)
                mx, my = (x + ox) / 2, y - 6
            else:
                d = 1 if ox > x else -1
                sx, sy = x + d * r * 0.7, y + (r * 0.7 if oy > y else -r * 0.7)
                ex, ey = ox - d * r * 0.7, oy + (r * 0.7 if y > oy else -r * 0.7)
                f.line(sx, sy, ex - d * 2, ey + (2 if y > oy else -2), "s", arrow=True)
                mx, my = (x + ox) / 2 + (8 if oy > y else -8), (y + oy) / 2 - 4
            if lab:
                f.text(mx, my, lab, "ta", 12, "middle", 700, mono=True)
    for i, (kind, out, out1, label) in states.items():
        x, y = xy(i)
        on = i in live
        if kind == "match":
            f.circle(x, y, r + 1, "a af" if on else "s f")
            f.circle(x, y, r - 3, "a fa" if on else "s")
            f.text(x, y + 4, str(i), "f" if on else "t", 11, "middle", 700, mono=True)
        elif kind == "split":
            f.circle(x, y, r - 3, "m f")
            f.text(x, y + 3.5, str(i), "tm", 9.5, "middle", mono=True)
        else:
            f.circle(x, y, r, "a fa" if on else "s f")
            f.text(x, y + 4, str(i), "f" if on else "t", 11, "middle", 700, mono=True)


def line_row(f, s, at, y, x0=44, cw=24, label="the line"):
    f.text(x0 - 10, y + 16, label, "tm", 10, "end")
    for k, c in enumerate(s):
        cur = k == at
        done = at is not None and k < at
        f.rect(x0 + k * cw, y, cw - 3, 24, "a fa" if cur else ("s fs" if done else "s f"), 4)
        f.text(x0 + k * cw + (cw - 3) / 2, y + 16, c, "f" if cur else ("tm" if done else "t"), 13, "middle", 700, mono=True)


NFA_LINE = re.compile(r"^nfa: (?:start|at (\d+) '(.)'): (\{[\d ]*\})$")


def nfa0403():
    pat, line = "a?a?a?aaa", "aabaaa"
    out, trace, st = grep("04.03", ["-E", "--algo=nfa", pat], (line + "\n").encode())
    assert out == line + "\n"
    states, start = machine(trace)
    assert len(states) == st["nfa"]["states"] and start == 0
    frames = []
    for t in trace:
        g = NFA_LINE.match(t)
        if g:
            frames.append((None if g.group(1) is None else int(g.group(1)), g.group(2), ids(g.group(3))))
    assert len(frames) == len(line) + 1
    assert sum(len(fr[2]) for fr in frames) == st["nfa"]["live"] and max(len(fr[2]) for fr in frames) == st["nfa"]["peak"]
    print("04.03 nfa:", frames, st["nfa"])
    # what each frame says, checked against the trace so the words cannot drift from it
    req = sorted(i for i, s in states.items() if s[0] == "char" and nfa_layout(states)[0][i][1] == 0)
    opt = sorted(i for i, s in states.items() if s[0] == "char" and nfa_layout(states)[0][i][1] == 1)
    match_id = next(i for i, s in states.items() if s[0] == "match")
    f = Fig("f0403a", "The machine for a?a?a?aaa reading aabaaa: after each byte, the states it could be in "
            "at once", 300)
    f.text(24, 22, "printf 'aabaaa\\n' | DS_TRACE=1 bin/grep -E --algo=nfa 'a?a?a?aaa'", "t", 11, mono=True)
    f.text(24, 42, "the machine, from the trace: splits (small, read nothing) and states that read one a",
           "tm", 10.5)
    summed = 0
    for k, (at, c, live) in enumerate(frames):
        summed += len(live)
        base = sorted(opt + req[:1])
        if at is None:
            cap = (f"Before the first byte: from the start, every split is followed both ways, so the states "
                   f"that can read the first a are {', '.join(map(str, live[:-1]))} and {live[-1]}.")
            assert live == base
        elif c != "a":
            cap = (f"\"{c}\" at {at}: no live state reads it, so every partial match dies at once; the start is "
                   f"added again, and the live states are the first four again. Nothing is tried twice.")
            assert live == base
        elif match_id in live:
            cap = (f"\"a\" at {at}: state {req[-1]} reads it and leads to {match_id}, the match state. The line "
                   f"matches; grep prints it and stops reading.")
        else:
            moved = [i for i in live if i not in base]
            cap = (f"\"a\" at {at}: each live state that reads a steps on; that brings in {moved[-1]}, "
                   f"and the start, added again, keeps {', '.join(map(str, opt))} and {req[0]} live: "
                   f"{len(live)} states.")
        with steps.step(f, cap):
            draw_nfa(f, states, start, set(live), 130)
            line_row(f, line, at, 188, x0=96)
            f.text(96, 244, "live: {" + " ".join(map(str, live)) + "}", "ta", 13, weight=700, mono=True)
            f.text(96, 266, f"{len(live)} live states, {summed} summed so far (the trace's work); the machine has "
                   f"{len(states)}", "tm", 10.5)
            if at is not None:
                f.text(96 + at * 24 + 10, 226, "^", "ta", 12, "middle", 700, mono=True)
    return f


DFA_LINE = re.compile(r"^dfa: (?:start:|at (\d+) '(.)': D(\d+) ->) D(\d+) \((built: (\{[\d ]*\})|hit|found)\)$")


def dfa0404():
    pat, data = "a?a?a?aaa", "aabaaa\naaa\n"
    out, trace, st = grep("04.04", ["-E", "--algo=dfa", pat], data.encode())
    assert out == data
    states, start = machine(trace)
    lines = data.split("\n")[:2]
    ev, which = [], -1
    for t in trace:
        if t.startswith("line: "):
            which += 1
            continue
        g = DFA_LINE.match(t)
        if g:
            ev.append(dict(line=which, at=None if g.group(1) is None else int(g.group(1)), c=g.group(2),
                           frm=None if g.group(3) is None else int(g.group(3)), to=int(g.group(4)),
                           how=g.group(5).split(":")[0], set=ids(g.group(6)) if g.group(6) else None))
    built = [e for e in ev if e["how"] == "built"]
    assert len(built) == st["dfa"]["states built"]
    assert sum(1 for e in ev if e["frm"] is not None and e["how"] == "hit") == st["dfa"]["hits"]
    assert sum(1 for e in ev if e["frm"] is not None and e["how"] != "hit") == st["dfa"]["misses"]
    # the NFA's own lists for the same line (04.03): each DFA state is one of them
    _, ntrace, _ = grep("04.03", ["-E", "--algo=nfa", pat], (lines[0] + "\n").encode())
    nsets = [ids(NFA_LINE.match(t).group(3)) for t in ntrace if NFA_LINE.match(t)]
    sets = {}
    for e in ev:
        if e["set"] is not None:
            sets[e["to"]] = e["set"]
    for e, ns in zip([e for e in ev if e["line"] == 0], nsets):
        assert sets[e["to"]] == ns, (e, ns)
    print("04.04 dfa:", [(e["line"], e["at"], e["frm"], e["to"], e["how"]) for e in ev], st["dfa"])
    match_id = next(i for i, s in states.items() if s[0] == "match")

    f = Fig("f0404a", "The DFA for a?a?a?aaa built while it reads aabaaa and then aaa: each set of NFA states "
            "becomes a state the first time it comes, and is reused after", 318)
    f.text(24, 22, "printf 'aabaaa\\naaa\\n' | DS_TRACE=1 bin/grep -E --algo=dfa 'a?a?a?aaa'", "t", 11, mono=True)
    DX = {0: 104, 1: 238, 2: 372, 3: 506}
    DY = 98
    f.text(24, 46, "each DFA state is a set of the NFA's states (04.03), and keeps where each byte took it",
           "tm", 10.5)

    def draw_dfa(known, edges, cur, how):
        for (a, c), b in edges.items():
            hot = cur is not None and cur[0] == a and cur[1] == c
            cls = "a" if hot else "s"
            if b == a + 1:
                f.line(DX[a] + 24, DY, DX[b] - 26, DY, cls, arrow=True)
                f.text((DX[a] + DX[b]) / 2, DY - 7, c, "ta" if hot else "t", 12, "middle", 700, mono=True)
            else:
                f.path(f"M{DX[a]} {DY + 22} C {DX[a]} {DY + 58}, {DX[b]} {DY + 58}, {DX[b]} {DY + 25}", cls,
                       arrow=True)
                f.text((DX[a] + DX[b]) / 2, DY + 62, c, "ta" if hot else "t", 12, "middle", 700, mono=True)
        for d in range(4):
            if d not in known:
                f.circle(DX[d], DY, 22, "m f")
                continue
            on = cur is not None and cur[2] == d
            isnew = on and how == "built"
            if match_id in known[d]:
                f.circle(DX[d], DY, 23, "a af" if on else "s f")
                f.circle(DX[d], DY, 18, "a fa" if on else "s")
            else:
                f.circle(DX[d], DY, 22, "a fa" if on else "s f")
            f.text(DX[d], DY + 5, f"D{d}", "f" if on else "t", 13, "middle", 700, mono=True)
            f.text(DX[d], DY - 32, "{" + " ".join(map(str, known[d])) + "}",
                   "ta" if isnew else "tm", 10.5, "middle", 600 if isnew else None, mono=True)
        f.line(DX[0] - 56, DY, DX[0] - 25, DY, "s", arrow=True)
        f.text(DX[0] - 58, DY - 6, "start", "tm", 9.5)

    known, edges = {}, {}
    hits = misses = nbuilt = 0
    groups = []
    for e in ev:
        if e["line"] == 1 and e["frm"] is not None and groups and groups[-1][0] == "line2":
            groups[-1][1].append(e)
        elif e["line"] == 1:
            groups.append(("line2", [e]))
        else:
            groups.append(("one", [e]))
    for kind, es in groups:
        for e in es:
            if e["how"] == "built":
                known[e["to"]] = e["set"]
                nbuilt += 1
            if e["frm"] is not None:
                if e["how"] == "hit":
                    hits += 1
                else:
                    misses += 1
                    edges[(e["frm"], e["c"])] = e["to"]
        e = es[-1]
        if kind == "line2":
            cap = (f"The next line, {lines[1]}: start in D{es[0]['to']}, and every byte is a hit, one lookup in "
                   f"the state's table. The NFA does no work at all; D{e['to']} matches.")
            assert all(x["how"] == "hit" for x in es)
        elif e["frm"] is None:
            cap = (f"Line {lines[0]}: before the first byte the NFA's start states, {{{' '.join(map(str, e['set']))}}}, "
                   f"are a set never seen: it is built as D{e['to']}, with every transition unknown.")
        elif e["how"] == "built":
            cap = (f"\"{e['c']}\" at {e['at']}: D{e['frm']} has no transition on it yet: worked out from the NFA, "
                   f"it leads to a new set, built as D{e['to']}" +
                   (", which holds the match state." if match_id in e["set"] else ", and kept in D%d's table." % e["frm"]))
        elif e["how"] == "found":
            cap = (f"\"{e['c']}\" at {e['at']}: worked out from the NFA, it leads to {{{' '.join(map(str, known[e['to']]))}}}: "
                   f"the hash table has that set already, as D{e['to']}. No new state.")
        else:
            cap = (f"\"{e['c']}\" at {e['at']}: D{e['frm']} has been through \"{e['c']}\" before: one lookup, "
                   f"D{e['to']}. A hit: no NFA work.")
        with steps.step(f, cap):
            cur = (e["frm"], e["c"], e["to"]) if e["frm"] is not None else (None, None, e["to"])
            draw_dfa(known, edges, cur, e["how"])
            if kind == "line2":
                line_row(f, lines[1], len(lines[1]) - 1, 196, x0=104, label="next line")
            else:
                line_row(f, lines[0], e["at"], 196, x0=104, label="line 1")
            f.text(104, 252, f"hits {hits}, misses {misses}, states built {nbuilt}", "ta", 12, weight=700, mono=True)
            how = {"built": "built: a new set of NFA states, a new state",
                   "found": "found: worked out from the NFA, the set already a state",
                   "hit": "hit: the state's table had it"}[es[-1]["how"]]
            f.text(104, 274, how, "t", 11)
            f.text(104, 296, "D0 to D3 are found by their sets in the hash table of 01.02", "tm", 10.5)
    assert (hits, misses, nbuilt) == (st["dfa"]["hits"], st["dfa"]["misses"], st["dfa"]["states built"])
    return f


def main():
    for name, fn, stepped in (("04.01-horspool", horspool0401, True), ("04.02-tree", tree0402, False),
                              ("04.03-nfa", nfa0403, True), ("04.04-dfa", dfa0404, True)):
        fig = fn()
        text = fig.svg()
        if stepped:
            print(name, "steps:", steps.check(text))
        print(write(MOD, name, fig))


if __name__ == "__main__":
    main()
