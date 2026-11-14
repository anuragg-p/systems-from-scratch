"""Figures for dsa module 02, Putting things in order: sort (lessons 02.01-02.06).

    python3 art/dsa/figs02.py

Every frame comes from a run of the real code. The script writes the project as it stands at
each lesson (./learn files dsa --at NN.LL), builds it, and runs the lesson's tool on a tiny
input with DS_STATS=1. It replays the same few lines of the lesson's code here, step by step,
to draw the frames, and stops with an error unless the replay prints the same lines and counts
the same comparisons, moves, pushes, pops, runs and probes as the real program did.

The inputs:
  02.01-02.03  the first eight words of "A Scandal in Bohemia", line 29 of data/book.txt,
               lowercased, one to a line: to sherlock holmes she is always the woman
               (02.03 also sorts them already in order)
  02.04        freq -n 7 data/book.txt: the seven most common words, through a heap of seven
  02.05        the eight words again, sort -S 100b: runs of three lines at most
  02.06        the words of lines 29-30 of the book, lowercased, sort -u: 24 lines; look she
"""
import atexit
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))     # art/, for steps
import figlib  # noqa: E402
from figlib import Fig  # noqa: E402
import steps  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
figlib.LESSONS = os.path.join(ROOT, "tracks", "dsa", "lessons")
MOD = "02-sort"

WORDS = [b"to", b"sherlock", b"holmes", b"she", b"is", b"always", b"the", b"woman"]


# ------------------------------------------------------------------ the real programs

_projects = {}
_tmp = tempfile.mkdtemp(prefix="figs02-")
atexit.register(shutil.rmtree, _tmp, True)


def project(at):
    """The project as it stands at lesson `at`, built: its directory."""
    if at not in _projects:
        d = os.path.join(_tmp, at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", at, d], check=True,
                       capture_output=True, cwd=ROOT)
        subprocess.run(["make", "-s"], cwd=d, check=True, capture_output=True)
        _projects[at] = d
    return _projects[at]


def run(at, argv, data=None):
    """bin/<argv[0]> of the project at `at`, with DS_STATS=1: (stdout bytes, the stats lines
    as {"sort": {"comparisons": 18, ...}, ...})."""
    d = project(at)
    env = {k: v for k, v in os.environ.items() if not k.startswith("DS_")}
    env.update(LC_ALL="C", DS_STATS="1")
    r = subprocess.run([os.path.join(d, "bin", argv[0])] + list(argv[1:]), input=data,
                       stdin=None if data is not None else subprocess.DEVNULL,
                       capture_output=True, cwd=d, env=env)
    if r.returncode not in (0, 1):
        raise SystemExit(f"{argv}: exit {r.returncode}: {r.stderr.decode()}")
    stats = {}
    for line in r.stderr.decode().splitlines():
        m = re.match(r"stats: (\w+): (.*)$", line)
        if m:
            stats[m.group(1)] = {k: int(v) for v, k in
                                 ((p.rsplit(" ", 1)[1], p.rsplit(" ", 1)[0]) for p in m.group(2).split(", "))}
    return r.stdout, stats


def same(what, mine, real):
    if mine != real:
        raise SystemExit(f"figs02: {what}: the replay here gives {mine!r}, the real program {real!r}")


def lines_of(words):
    return b"".join(w + b"\n" for w in words)


def show(w):
    return w.decode("ascii")


def q(w):
    """A line named in a caption, in quotes."""
    return '"' + show(w) + '"'


# ------------------------------------------------------------------ drawing helpers

# A box: kind -> (box class, text class, dashed)
STYLE = {
    "n": ("s f", "t", False),        # plain
    "d": ("m f", "tm", False),       # done with, or out of play: muted
    "u": ("m f", "tm", True),        # empty, not there yet: dashed
    "a": ("a af", "ta", False),      # just moved or merged: accent-soft
    "A": ("a fa", "f", False),       # the item this step is about: accent
    "p": ("s fs", "t", False),       # set apart (code background)
}


def box(f, x, y, w, h, text, kind="n", size=11.5, mono=True, rx=4):
    cls, tcls, dash = STYLE[kind]
    f.rect(x, y, w, h, cls, rx, dash=dash)
    if text:
        f.text(x + w / 2, y + h / 2 + size * 0.36, text, tcls, size, "middle", 600 if kind == "A" else None, mono)


def row(f, x, y, items, kinds, w=64, gap=4, h=28, size=11.5):
    """Words left to right; returns the x of each box's centre."""
    xs = []
    for i, (t, k) in enumerate(zip(items, kinds)):
        bx = x + i * (w + gap)
        box(f, bx, y, w, h, t, k, size)
        xs.append(bx + w / 2)
    return xs


def indexes(f, x, y, n, w=64, gap=4, start=0):
    for i in range(n):
        f.text(x + i * (w + gap) + w / 2, y, str(start + i), "tm", 10, "middle", mono=True)


def bracket(f, x1, x2, y, label, cls="m", tcls="tm", up=False):
    f.brace_h(x1, x2, y, cls, up=up)
    f.text((x1 + x2) / 2, y + (-8 if up else 16), label, tcls, 10.5, "middle")


# ------------------------------------------------------------------ 02.01 insertion sort

def insertion_trace(v):
    """sort_insertion, step by step: [(i, j, comparisons this step, in all, the array after)]."""
    v = list(v)
    comps = moves = 0
    out = []
    for i in range(1, len(v)):
        x, j, c = v[i], i, 0
        while j > 0:
            comps += 1
            c += 1
            if v[j - 1] > x:
                v[j] = v[j - 1]
                moves += 1
                j -= 1
            else:
                break
        v[j] = x
        moves += 1
        out.append((i, j, c, comps, list(v)))
    return out, comps, moves


def insertion0201():
    trace, comps, moves = insertion_trace(WORDS)
    out, st = run("02.01", ["sort"], lines_of(WORDS))
    same("02.01 output", lines_of(trace[-1][4]), out)
    same("02.01 comparisons", comps, st["sort"]["comparisons"])
    same("02.01 moves", moves, st["sort"]["moves"])

    f = Fig("f0201a", "Insertion sort on eight lines: each line in turn slides left past the bigger ones before it", 186)
    X, W, G = 84, 64, 4
    f.text(24, 22, "the array of lines, one insertion at a time", "tm", 11)

    def pos(i):
        return X + i * (W + G)

    with steps.step(f, "The eight lines as read. v[0..1), the first line alone, is in order: there is nothing to compare it with."):
        indexes(f, X, 48, 8)
        f.text(24, 74, "as read", "t", 11, weight=600)
        row(f, X, 56, [show(w) for w in WORDS], ["n"] + ["d"] * 7)
        bracket(f, pos(0), pos(1) - G, 92, "in order")
    prev = list(WORDS)
    for i, j, c, total, after in trace:
        x = prev[i]
        moved = i - j
        what = (f"{q(x)} slides left past {moved} line{'s' if moved != 1 else ''}" if moved
                else f"{q(x)} stays where it is")
        stop = "reaching the front" if j == 0 else f"and stops at {q(after[j - 1])}"
        cap = (f"i = {i}: {what}, {stop}: {c} comparison{'s' if c != 1 else ''}, {total} in all. "
               f"v[0..{i + 1}) is in order.")
        if not moved:
            cap = (f"i = {i}: {q(x)} is not smaller than {q(prev[i - 1])}, so it stays: "
                   f"{c} comparison, {total} in all. v[0..{i + 1}) is in order.")
        with steps.step(f, cap):
            indexes(f, X, 48, 8)
            f.text(24, 74, "before", "t", 11, weight=600)
            kinds = ["n"] * i + ["A"] + ["d"] * (7 - i)
            row(f, X, 56, [show(w) for w in prev], kinds)
            f.text(24, 150, "after", "t", 11, weight=600)
            kinds = ["n"] * j + ["A"] + ["a"] * moved + ["n"] * 0 + ["d"] * (7 - i)
            row(f, X, 132, [show(w) for w in after], kinds)
            bracket(f, pos(0), pos(i + 1) - G, 168, f"in order: v[0..{i + 1})")
            # where x went: from its old box down to its new one
            sx, ex = pos(i) + W / 2, pos(j) + W / 2
            if moved:
                f.path(f"M{sx} 86 C {sx} 112, {ex} 104, {ex} 130", "a", arrow=True)
                for k in range(j, i):
                    f.line(pos(k) + W / 2 + 6, 86, pos(k + 1) + W / 2 - 6, 130, "m", arrow=True)
            else:
                f.line(sx, 86, sx, 130, "a", arrow=True)
        prev = after
    return f


# ------------------------------------------------------------------ 02.02 merge sort

def merge_trace(v):
    """merge_sort top-down: [(lo, mid, hi, comparisons in this merge, in all, the array after)]."""
    v = list(v)
    aux = [None] * len(v)
    st = {"c": 0, "m": 0}
    out = []

    def merge(lo, mid, hi):
        aux[lo:hi] = v[lo:hi]
        i, j, c = lo, mid, 0
        for k in range(lo, hi):
            if i == mid:
                v[k] = aux[j]
                j += 1
            elif j == hi:
                v[k] = aux[i]
                i += 1
            else:
                c += 1
                if aux[j] < aux[i]:
                    v[k] = aux[j]
                    j += 1
                else:
                    v[k] = aux[i]
                    i += 1
        st["m"] += hi - lo
        st["c"] += c
        out.append((lo, mid, hi, c, st["c"], list(v)))

    def sort(lo, hi):
        if hi - lo < 2:
            return
        mid = lo + (hi - lo) // 2
        sort(lo, mid)
        sort(mid, hi)
        merge(lo, mid, hi)

    sort(0, len(v))
    return out, st["c"], st["m"]


def merge0202():
    trace, comps, moves = merge_trace(WORDS)
    out, st = run("02.02", ["sort"], lines_of(WORDS))
    same("02.02 output", lines_of(trace[-1][5]), out)
    same("02.02 comparisons", comps, st["sort"]["comparisons"])
    same("02.02 moves", moves, st["sort"]["moves"])

    f = Fig("f0202a", "Merge sort on eight lines: sorted runs of 1, 2, 4 and 8, each merged from two of the row above", 256)
    X, W, G = 84, 64, 4
    LEVEL_Y = {1: 34, 2: 96, 4: 158, 8: 220}
    LABEL = {1: "runs of 1", 2: "runs of 2", 4: "runs of 4", 8: "all 8"}

    def pos(i):
        return X + i * (W + G)

    def draw(done, last):
        """done: {(lo, hi): words}; last: the (lo, hi) just merged, or None."""
        for size, y in LEVEL_Y.items():
            f.text(24, y + 18, LABEL[size], "t" if size == 1 else "tm", 11, weight=600 if size == 1 else None)
            for lo in range(0, 8, size):
                hi = lo + size
                if size == 1:
                    row(f, pos(lo), y, [show(WORDS[lo])], ["n"])
                    continue
                if (lo, hi) in done:
                    kinds = ["A" if (lo, hi) == last else "n"] * size
                    if (lo, hi) == last:
                        kinds = ["a"] * size
                    f.rect(pos(lo) - 3, y - 3, pos(hi) - G - pos(lo) + 6, 34, "a" if (lo, hi) == last else "m", 6)
                    row(f, pos(lo), y, [show(w) for w in done[(lo, hi)]], kinds)
                else:
                    f.rect(pos(lo), y, pos(hi) - G - pos(lo), 28, "m", 4, dash=True)
            if size > 1:
                for lo in range(0, 8, size):
                    hi, mid = lo + size, lo + size // 2
                    live = (lo, hi) in done
                    cls = "a" if (lo, hi) == last else ("m" if live else "m")
                    up = LEVEL_Y[size // 2] + 30
                    for a, b in ((lo, mid), (mid, hi)):
                        cx = (pos(a) + pos(b) - G) / 2
                        tx = (pos(lo) + pos(hi) - G) / 2 + (-14 if a == lo else 14)
                        f.line(cx, up, tx, y - 4, cls, arrow=(lo, hi) == last, dash=not live)

    with steps.step(f, "The eight lines as read: each line alone is a sorted run of one."):
        draw({}, None)
    done = {}
    for lo, mid, hi, c, total, after in trace:
        done[(lo, hi)] = after[lo:hi]
        a, b = f"v[{lo}..{mid})", f"v[{mid}..{hi})"
        why = ""
        if c < hi - lo - 1:
            why = " (one side ran out first, so the rest of the other is copied without comparing)"
        with steps.step(f, f"merge {a} and {b} into v[{lo}..{hi}): {c} comparison{'s' if c != 1 else ''}, "
                           f"{total} in all{why}."):
            draw(done, (lo, hi))
    return f


# ------------------------------------------------------------------ 02.03 quicksort

def quick_first_trace(v):
    """quick_first as sort.c has it: [(lo, hi, m, comparisons this pass, in all, before, after)]."""
    v = list(v)
    st = {"c": 0, "m": 0}
    out = []

    def swap(i, j):
        v[i], v[j] = v[j], v[i]
        st["m"] += 2

    def qs(lo, hi):
        while hi - lo > 1:
            before = list(v)
            pivot = v[lo]
            m = lo
            c = 0
            for i in range(lo + 1, hi):
                c += 1
                if v[i] < pivot:
                    m += 1
                    swap(m, i)
            swap(lo, m)
            st["c"] += c
            out.append((lo, hi, m, c, st["c"], before, list(v)))
            if m - lo < hi - m - 1:
                qs(lo, m)
                lo = m + 1
            else:
                qs(m + 1, hi)
                hi = m

    qs(0, len(v))
    return out, st["c"], st["m"], v


def quick0203():
    trace, comps, moves, result = quick_first_trace(WORDS)
    trace_total = comps
    out, st = run("02.03", ["sort", "--algo=quick-first"], lines_of(WORDS))
    same("02.03 output", lines_of(result), out)
    same("02.03 comparisons", comps, st["sort"]["comparisons"])
    same("02.03 moves", moves, st["sort"]["moves"])
    in_order = sorted(WORDS)
    strace, scomps, smoves, sresult = quick_first_trace(in_order)
    out, st = run("02.03", ["sort", "--algo=quick-first"], lines_of(in_order))
    same("02.03 sorted output", lines_of(sresult), out)
    same("02.03 sorted comparisons", scomps, st["sort"]["comparisons"])
    same("02.03 sorted moves", smoves, st["sort"]["moves"])
    same("02.03 sorted comparisons are n(n-1)/2", scomps, 8 * 7 // 2)

    f = Fig("f0203a", "Quicksort with the first line as the pivot: one partition, then every pass on input already in order", 190)
    X, W, G = 84, 64, 4

    def pos(i):
        return X + i * (W + G)

    def frame(before, after, lo, hi, m, c, total, note):
        pivot = before[lo]
        indexes(f, X, 48, 8)
        f.text(24, 74, "before", "t", 11, weight=600)
        kinds = []
        for k in range(8):
            if k < lo or k >= hi:
                kinds.append("d")
            elif k == lo:
                kinds.append("A")
            else:
                kinds.append("a" if before[k] < pivot else "n")
        f.rect(pos(lo) - 3, 53, pos(hi) - G - pos(lo) + 6, 34, "a", 6)
        row(f, X, 56, [show(w) for w in before], kinds)
        f.text(24, 22, f"this pass: v[{lo}..{hi}), pivot {show(pivot)}", "ta", 11, weight=600)
        f.text(24, 150, "after", "t", 11, weight=600)
        kinds = []
        for k in range(8):
            if k < lo or k >= hi:
                kinds.append("d")
            elif k == m:
                kinds.append("A")
            elif k < m:
                kinds.append("a")
            else:
                kinds.append("n")
        row(f, X, 132, [show(w) for w in after], kinds)
        if m > lo:
            bracket(f, pos(lo), pos(m) - G, 168, f"smaller: {m - lo}")
        if hi - m - 1 > 0:
            bracket(f, pos(m + 1), pos(hi) - G, 168, f"not smaller: {hi - m - 1}")
        sx, ex = pos(lo) + W / 2, pos(m) + W / 2
        if m != lo:
            f.path(f"M{sx} 90 C {sx} 114, {ex} 104, {ex} 128", "a", arrow=True)
            f.path(f"M{ex - 10} 90 C {ex - 10} 114, {sx + 10} 104, {sx + 10} 128", "m", arrow=True)
        else:
            f.line(sx, 90, sx, 128, "a", arrow=True)
        f.text(616, 22, note, "tm", 10.5, "end")

    lo, hi, m, c, total, before, after = trace[0]
    smaller = m - lo
    with steps.step(f, f"The first line, {q(before[lo])}, is the pivot. Each of the other {hi - lo - 1} is compared "
                       f"with it: {smaller} are smaller and gather on the left, {hi - m - 1} is not. Then the pivot "
                       f"swaps into place {m}, its place in the sorted output for good."):
        frame(before, after, lo, hi, m, c, total, "input: the lines as read")
    for k, (lo, hi, m, c, total, before, after) in enumerate(strace):
        left = hi - m - 1
        cap = (f"In order already, pass {k + 1}: the pivot, {q(before[lo])}, is the smallest line left. "
               f"{c} comparisons find nothing smaller, so it stays where it is and {left} line"
               f"{'s are' if left != 1 else ' is'} left for the next pass: {total} comparisons in all.")
        if left == 1:
            cap = (f"In order already, pass {k + 1}: the pivot, {q(before[lo])}, is smaller than the one line "
                   f"after it, which is in order by itself. {total} comparisons in all: 7 + 6 + 5 + 4 + 3 + 2 + 1, "
                   f"n(n-1)/2 for n = 8, where the lines as read took {trace_total}.")
        with steps.step(f, cap):
            frame(before, after, lo, hi, m, c, total, "input: the lines already in order")
    return f


# ------------------------------------------------------------------ 02.04 the heap

def book_words():
    with open(os.path.join(project("02.04"), "data", "book.txt"), "rb") as fh:
        data = fh.read()
    counts = {}
    for w in re.findall(rb"[A-Za-z]+", data):
        w = w.lower()
        counts[w] = counts.get(w, 0) + 1
    return list(counts.items())         # in the order each was first seen, as freq's words array


def heap0204():
    N = 7
    words = book_words()
    st = {"pushes": 0, "pops": 0, "comparisons": 0, "moves": 0, "rank": 0}
    events = []

    def rank(a, b):
        st["rank"] += 1
        return (a > b) - (a < b)        # (count, word): count first, then the word byte by byte

    def above(a, b):
        st["comparisons"] += 1
        return rank(a, b) < 0           # a min-heap: dir 1

    h = []

    def snap(note, kinds, extra=None):
        if record[0]:
            events.append((note, list(h), dict(kinds), extra))

    def sift_up(i):
        x = h[i]
        while i > 0:
            parent = (i - 1) // 2
            if not above(x, h[parent]):
                snap(f"up_stop {i} {parent}", {i: "A", parent: "a"}, ("stop", x))
                break
            h[i] = h[parent]
            st["moves"] += 1
            h[parent] = x       # (the C code writes x once at the end; drawn in place here)
            snap(f"up {i} {parent}", {parent: "A", i: "a"}, ("up", x))
            i = parent
        h[i] = x
        st["moves"] += 1

    def sift_down(n, i):
        x = h[i]
        while True:
            child = 2 * i + 1
            if child >= n:
                snap(f"down_leaf {i}", {i: "A"}, ("leaf", x))
                break
            if child + 1 < n and above(h[child + 1], h[child]):
                child += 1
            if not above(h[child], x):
                snap(f"down_stop {i} {child}", {i: "A", child: "a"}, ("stop", x))
                break
            h[i] = h[child]
            st["moves"] += 1
            h[child] = x
            snap(f"down {i} {child}", {child: "A", i: "a"}, ("down", x))
            i = child
        h[i] = x
        st["moves"] += 1

    def push(w):
        h.append(w)
        snap("push", {len(h) - 1: "A"}, ("push", w))
        sift_up(len(h) - 1)
        st["pushes"] += 1

    def pop():
        top = h[0]
        last = h.pop()
        if h:
            h[0] = last
            snap("pop", {0: "A"}, ("pop", top))
            sift_down(len(h), 0)
        st["pops"] += 1
        return top

    record = [False]
    chosen = None
    for idx, (w, c) in enumerate(words):
        item = (c, w)
        if len(h) < N:
            push(item)
        elif rank(item, h[0]) > 0:
            # draw the first replacement whose sift down goes all the way to the bottom
            if chosen is None and N == 7:
                before = list(h)
                record[0] = True
                events.clear()
                pop()
                push(item)
                record[0] = False
                if sum(1 for e in events if e[0].startswith("down ")) == 2:
                    chosen = (before, item, list(events))
                continue
            pop()
            push(item)
    best = []
    while h:
        best.append(pop())
    best.reverse()
    out, real = run("02.04", ["freq", "-n", str(N), "data/book.txt"])
    mine = b"".join(b"%7d %s\n" % (c, w) for c, w in best)
    same("02.04 output", mine, out)
    for k in ("pushes", "pops", "comparisons", "moves"):
        same(f"02.04 heap {k}", st[k], real["heap"][k])
    same("02.04 rank comparisons", st["rank"], real["freq"]["rank comparisons"])
    if chosen is None:
        raise SystemExit("figs02: 02.04: no replacement sifts down two levels")
    before, item, events = chosen

    f = Fig("f0204a", "freq's heap of the seven best words so far, the worst of them on top: one word replaces the top and sifts down", 324)
    # the tree: levels 0, 1, 2 at these centres
    TX = {0: 320, 1: 170, 2: 470, 3: 95, 4: 245, 5: 395, 6: 545}
    TY = {0: 52, 1: 52 + 62, 2: 52 + 62, 3: 52 + 124, 4: 52 + 124, 5: 52 + 124, 6: 52 + 124}
    BW, BH = 116, 30
    AX, AW, AG, AY = 24, 80, 4, 262

    def label(it):
        c, w = it
        return f"{show(w)} {c}"

    def draw(hp, kinds):
        for i in range(1, 7):
            p = (i - 1) // 2
            live = i < len(hp)
            f.line(TX[p], TY[p] + BH / 2 + 2, TX[i], TY[i] - BH / 2 - 2, "m", dash=not live)
        for i in range(7):
            x, y = TX[i] - BW / 2, TY[i] - BH / 2
            if i < len(hp):
                box(f, x, y, BW, BH, label(hp[i]), kinds.get(i, "n"), 11.5)
                f.text(x + BW + 4, y + 11, str(i), "tm", 9.5, mono=True)
            else:
                box(f, x, y, BW, BH, "", "u")
        f.text(24, 250, "the same heap as an array: the children of i are at 2i+1 and 2i+2", "tm", 10.5)
        for i in range(7):
            x = AX + i * (AW + AG)
            f.text(x + AW / 2, AY + 46, str(i), "tm", 9.5, "middle", mono=True)
            if i < len(hp):
                c, w = hp[i]
                k = kinds.get(i, "n")
                cls, tcls, dash = STYLE[k]
                f.rect(x, AY, AW, 32, cls, 4, dash=dash)
                f.text(x + AW / 2, AY + 13, show(w), tcls, 11, "middle", 600 if k == "A" else None, True)
                f.text(x + AW / 2, AY + 26, str(c), tcls if k != "n" else "tm", 10, "middle", None, True)
            else:
                f.rect(x, AY, AW, 32, "m f", 4, dash=True)

    def say(it):
        return f'"{show(it[1])}" ({it[0]})'

    new = item
    with steps.step(f, f"Seven words are in the heap, the worst of them, {say(before[0])}, on top. The next word, "
                       f"{say(new)}, ranks above it: it belongs among the best seven, and the top must go."):
        draw(before, {0: "A"})
        f.text(250, 20, f"next word: {label(new)}", "ta", 11, weight=600)
    out_label = None
    for note, hp, kinds, extra in events:
        kind, x = extra
        at = [k for k, v in kinds.items() if v == "A"][0]
        if kind == "pop":
            out_label = label(x)
            cap = (f"Pop: the top, {say(x)}, comes out, and the last item, {say(hp[0])}, moves into the root. "
                   f"The rule that no item ranks above its children is broken at the root.")
        elif kind == "down":
            frm = [k for k, v in kinds.items() if v == "a"][0]
            cap = (f"Sift down: {say(x)} is compared with the lower ranked of its two children, {say(hp[frm])}, "
                   f"which ranks below it, so the two swap: {say(x)} moves from {frm} to {at}.")
        elif kind == "leaf":
            cap = (f"{say(x)} has reached {at}, which has no children (2 * {at} + 1 is past the end): "
                   f"the rule holds everywhere again.")
        elif note.startswith("down_stop"):
            cap = f"{say(x)} ranks above both its children: it stays at {at}, and the rule holds again."
        elif kind == "push":
            cap = f"Push: {say(x)} goes in at the end, at {at}, as a child of {say(hp[(at - 1) // 2])}."
        elif note.startswith("up_stop"):
            p = (at - 1) // 2
            cap = (f"Sift up: {say(x)} is compared with its parent, {say(hp[p])}, and ranks above it, so it stays. "
                   f"The heap holds the seven best words so far, the worst of them, {say(hp[0])}, on top.")
        elif kind == "up":
            cap = f"Sift up: {say(x)} ranks below its parent, so the two swap: it moves to {at}."
        else:
            raise SystemExit(f"figs02: 02.04: no caption for {note}")
        with steps.step(f, cap):
            draw(hp, kinds)
            if out_label:
                f.text(24, 20, f"out: {out_label}", "tm", 11, weight=600)
            pushed = kind == "push" or note.startswith("up")
            f.text(250, 20, f"{'in' if pushed else 'waiting'}: {label(new)}", "ta", 11, weight=600)
    return f


# ------------------------------------------------------------------ 02.05 runs and their merge

def line_bytes(w):
    return 16 + len(w) + 1 + 8          # its Line header, the bytes and a NUL, its pointer


def runs0205():
    CAP = 100
    held, cur = 0, []
    sort_comps = sort_moves = 0
    spills = []                         # (the lines as read, the run as written)
    for w in WORDS:
        size = line_bytes(w)
        if held + size > CAP and cur:
            t, c, m = merge_trace(cur)
            run_out = t[-1][5] if t else list(cur)
            sort_comps += c
            sort_moves += m
            spills.append((list(cur), run_out))
            cur, held = [], 0
        cur.append(w)
        held += size
    t, c, m = merge_trace(cur)
    sort_comps += c
    sort_moves += m
    spills.append((list(cur), t[-1][5] if t else list(cur)))

    # merge_runs: a heap of runs by their next line; on a tie the earlier run first
    st = {"pushes": 0, "pops": 0, "comparisons": 0, "moves": 0}
    frames = []
    pos = [0] * len(spills)
    h = []

    def key(r):
        return (spills[r][1][pos[r]], r)

    def above(a, b):
        st["comparisons"] += 1
        return key(a) < key(b)

    def sift_up(i):
        x = h[i]
        while i > 0:
            p = (i - 1) // 2
            if not above(x, h[p]):
                break
            h[i] = h[p]
            st["moves"] += 1
            i = p
        h[i] = x
        st["moves"] += 1

    def sift_down(n, i):
        x = h[i]
        while True:
            c = 2 * i + 1
            if c >= n:
                break
            if c + 1 < n and above(h[c + 1], h[c]):
                c += 1
            if not above(h[c], x):
                break
            h[i] = h[c]
            st["moves"] += 1
            i = c
        h[i] = x
        st["moves"] += 1

    def push(r):
        h.append(r)
        sift_up(len(h) - 1)
        st["pushes"] += 1

    def pop():
        top = h[0]
        last = h.pop()
        if h:
            h[0] = last
            sift_down(len(h), 0)
        st["pops"] += 1
        return top

    for r in range(len(spills)):
        push(r)
    written = []
    frames.append(("heap", list(h), list(pos), list(written), None))
    while h:
        r = pop()
        written.append((spills[r][1][pos[r]], r))
        pos[r] += 1
        if pos[r] < len(spills[r][1]):
            push(r)
        frames.append(("pop", list(h), list(pos), list(written), r))

    out, real = run("02.05", ["sort", "-S", f"{CAP}b"], lines_of(WORDS))
    same("02.05 output", lines_of([w for w, _ in written]), out)
    same("02.05 runs", (len(spills), 1), (real["runs"]["written"], real["runs"]["merges"]))
    same("02.05 sort comparisons", sort_comps, real["sort"]["comparisons"])
    for k in st:
        same(f"02.05 heap {k}", st[k], real["heap"][k])

    f = Fig("f0205a", "sort -S 100b on eight lines: three sorted runs written to files, then merged through a heap", 300)
    IX, RX, OX = 24, 196, 470
    RW, BH = 76, 24
    run_x = [RX + k * (RW + 10) for k in range(len(spills))]

    def draw(nspilled, hp, ps, written, last):
        f.text(IX, 22, "the input, as read", "tm", 10.5)
        k = 0
        for r, (read, _) in enumerate(spills):
            for j, w in enumerate(read):
                y = 32 + k * (BH + 4) + r * 8
                box(f, IX, y, 120, BH, show(w), "n" if r >= nspilled else ("a" if r == nspilled - 1 and ps is None else "d"), 11)
                k += 1
            top = 32 + (k - len(read)) * (BH + 4) + r * 8
            f.text(IX + 128, top + len(read) * (BH + 4) / 2 + 2, f"{sum(line_bytes(w) for w in read)} b", "tm", 9.5,
                   mono=True)
        f.text(RX, 22, "runs, sorted, in files", "tm", 10.5)
        for r, (_, out_) in enumerate(spills):
            x = run_x[r]
            f.text(x + RW / 2, 46, f"run {r + 1}", "t" if r < nspilled else "tm", 10.5, "middle", 600)
            for j, w in enumerate(out_):
                y = 56 + j * (BH + 4)
                if r >= nspilled:
                    box(f, x, y, RW, BH, "", "u")
                    continue
                if ps is None:
                    kind = "a" if r == nspilled - 1 else "n"
                else:
                    kind = "d" if j < ps[r] else ("A" if j == ps[r] and r in hp else "n")
                box(f, x, y, RW, BH, show(w), kind, 11)
        if hp is not None:
            f.text(RX, 186, "the heap: one entry per run, by its next line", "tm", 10.5)
            hx = {0: RX + 86, 1: RX + 20, 2: RX + 152}
            hy = {0: 200, 1: 246, 2: 246}
            for i in range(1, 3):
                if i < len(hp):
                    f.line(hx[0] + 33, hy[0] + 24, hx[i] + 33, hy[i] - 1, "m")
            for i, r in enumerate(hp):
                box(f, hx[i], hy[i], 66, 24, f"run {r + 1}", "a" if i == 0 else "p", 10.5)
                f.text(hx[i] + 33, hy[i] + 36, show(spills[r][1][ps[r]]), "tm", 10, "middle", mono=True)
        f.text(OX, 22, "the output", "tm", 10.5)
        if written:
            for j, (w, r) in enumerate(written):
                y = 32 + j * (BH + 4)
                box(f, OX, y, 100, BH, show(w), "A" if j == len(written) - 1 and last is not None else "n", 11)
                f.text(OX + 108, y + 16, f"run {r + 1}", "tm", 9.5)
        else:
            box(f, OX, 32, 100, BH, "", "u")

    nread = 0
    for r, (read, out_) in enumerate(spills):
        nread += len(read)
        held = sum(line_bytes(w) for w in read)
        if r < len(spills) - 1:
            nxt = spills[r + 1][0][0]
            first = ("Each line costs its bytes, a NUL, and 24 bytes of header and pointer. " if r == 0 else "")
            cap = (f"{first}{len(read)} lines are held, {held} bytes; the next, {q(nxt)}, would make "
                   f"{held + line_bytes(nxt)}, past the {CAP} that -S allows. So the {len(read)} are sorted, "
                   f"written out as run {r + 1}, and let go.")
        else:
            cap = (f"The input ends with {len(read)} lines held, {held} bytes: they are sorted and written "
                   f"as run {r + 1}. No more than {CAP} bytes of lines were ever in memory at once.")
        with steps.step(f, cap):
            draw(r + 1, None, None, [], None)
    for kind, hp, ps, written, last in frames:
        if kind == "heap":
            cap = ("The merge opens the three runs and pushes each into a heap, ordered by its first line: "
                   f"run {hp[0] + 1}, whose next line is {q(spills[hp[0]][1][0])}, is on top.")
        else:
            w = written[-1][0]
            nxt = ""
            if ps[last] < len(spills[last][1]):
                nxt = f" Its next line, {q(spills[last][1][ps[last]])}, puts run {last + 1} back in the heap."
            else:
                nxt = f" Run {last + 1} is used up and leaves the heap."
            cap = f"Pop: run {last + 1} has the smallest next line, {q(w)}, and it is written out.{nxt}"
            if not hp:
                cap = (f"Pop: {q(w)}, the last line, from run {last + 1}. Every run is used up: "
                       f"the output is the eight lines in order, the same bytes as sort without -S.")
        with steps.step(f, cap):
            draw(len(spills), hp, ps, written, last)
    return f


# ------------------------------------------------------------------ 02.06 binary search

def look0206():
    with open(os.path.join(project("02.06"), "data", "book.txt"), "rb") as fh:
        text = b"\n".join(fh.read().split(b"\n")[28:30])
    words = sorted({w.lower() for w in re.findall(rb"[A-Za-z]+", text)})
    data = lines_of(words)
    key = b"she"
    size = len(data)

    def line_at(off):
        end = data.index(b"\n", off) if b"\n" in data[off:] else size
        return data[off:end], min(end + 1, size)

    def line_start(off):
        if off == 0:
            return 0
        for p in range(off - 1, size):
            if data[p:p + 1] == b"\n":
                return p + 1
        return size

    def compare(line):
        n = min(len(line), len(key))
        c = (line[:n] > key[:n]) - (line[:n] < key[:n])
        if c != 0:
            return c
        return -1 if len(line) < len(key) else 0

    probes = []
    lo, hi = 0, size
    while lo < hi:
        mid = lo + (hi - lo) // 2
        at = line_start(mid)
        if at >= hi:
            at = lo
        line, nxt = line_at(at)
        c = compare(line)
        probes.append((lo, hi, mid, at, line, c))
        if c < 0:
            lo = nxt
        else:
            hi = at
    found = lo
    printed = []
    after = found
    while after < size:
        line, nxt = line_at(after)
        if compare(line) != 0:
            break
        printed.append(line)
        after = nxt

    d = project("02.06")
    path = os.path.join(d, "fig.txt")
    with open(path, "wb") as fh:
        fh.write(data)
    out, real = run("02.06", ["look", key.decode(), "fig.txt"])
    same("02.06 output", lines_of(printed), out)
    same("02.06 probes", len(probes), real["look"]["probes"])
    same("02.06 lines printed", len(printed), real["look"]["lines printed"])
    if len(words) != 24:
        raise SystemExit(f"figs02: 02.06: {len(words)} words, the lesson says 24")

    offs = []
    o = 0
    for w in words:
        offs.append(o)
        o += len(w) + 1
    RH, Y0, LX = 13.6, 40, 150
    f = Fig("f0206a", "look she on a sorted file of 24 lines: each probe halves the part of the file the first match can be in", 376)

    def y_of(off):
        """The y of a byte offset: lines are rows; an offset inside a line is placed within its row."""
        for i, s in enumerate(offs):
            e = offs[i + 1] if i + 1 < len(offs) else size
            if s <= off < e:
                return Y0 + i * RH + (off - s) / (e - s) * RH
        return Y0 + len(offs) * RH

    def draw(lo, hi, probe=None, done=False):
        f.text(100, 24, "byte", "tm", 10, "end", mono=True)
        f.text(LX, 24, "line", "tm", 10, mono=True)
        for i, (s, w) in enumerate(zip(offs, words)):
            y = Y0 + i * RH
            inside = lo <= s < hi
            hit = probe is not None and s == probe[3]
            cls = "ta" if hit else ("t" if inside else "tm")
            if done and w in printed:
                cls = "ta"
            f.text(100, y + 10.5, str(s), "tm", 10, "end", mono=True)
            f.text(LX, y + 10.5, show(w), cls, 11, weight=600 if (hit or (done and w in printed)) else None,
                   mono=True)
        # the part the first match can be in: [lo, hi)
        ylo, yhi = y_of(lo), y_of(hi) if hi < size else Y0 + len(offs) * RH
        if hi > lo:
            f.rect(LX - 10, ylo, 112, max(yhi - ylo, 3), "a", 4)
        if hi > lo:
            f.line(LX - 24, ylo, LX - 14, ylo, "a")
            f.text(LX - 28, ylo + 4, "lo", "ta", 10.5, "end", 600, True)
            f.line(LX - 24, yhi, LX - 14, yhi, "a")
            f.text(LX - 28, yhi + 4, "hi", "ta", 10.5, "end", 600, True)
        else:
            f.line(LX + 128, ylo, LX + 108, ylo, "a", arrow=True)
            f.text(LX + 132, ylo + 4, f"lo = hi = {lo}", "ta", 10.5, weight=600, mono=True)
        if probe is not None:
            ym = y_of(probe[2])
            f.line(LX + 128, ym, LX + 108, ym, "m", arrow=True)
            f.text(LX + 132, ym + 4, f"middle byte {probe[2]}", "tm", 10)

    def side(lines):
        for k, (t, cls) in enumerate(lines):
            f.text(390, 64 + k * 20, t, cls, 11.5)

    with steps.step(f, f"The file: {len(words)} words, sorted, {size} bytes. The first line that begins with "
                       f"{q(key)} could be anywhere: lo = 0, hi = {size}, the whole file."):
        draw(0, size)
        side([(f"look {show(key)}: where is the first line", "t"),
              (f"not smaller than {show(key)}?", "t"),
              ("every line before lo is smaller;", "tm"),
              ("the line at hi, if any, is not", "tm")])
    for k, (lo, hi, mid, at, line, c) in enumerate(probes):
        newlo, newhi = (line_at(at)[1], hi) if c < 0 else (lo, at)
        verdict = "smaller" if c < 0 else ("a match" if c == 0 else "bigger")
        moved = (f"so the match is after it: lo = {newlo}" if c < 0 else
                 f"so the first match is at it or before: hi = {newhi}")
        start = f"the middle byte, {mid}, is inside a line: the probe is the next line, at {at}"
        if at == mid:
            start = f"the middle byte, {mid}, starts a line"
        if line_start(mid) >= hi:
            start = f"no line starts after the middle byte, {mid}, before hi: the probe is the line at lo, {at}"
        cap = f"Probe {k + 1}: {start}: {q(line)}, which is {verdict}, {moved}."
        with steps.step(f, cap):
            draw(newlo, newhi, (lo, hi, mid, at))
            side([(f"probe {k + 1}: byte {mid} -> line at {at}", "t"),
                  (f"{show(line)}: {verdict}", "ta"),
                  (f"lo = {newlo}, hi = {newhi}", "t"),
                  (f"{k + 1} lines compared so far", "tm")])
    with steps.step(f, f"lo = hi = {found}: the search is over after {len(probes)} probes. From there look prints "
                       f"every line that begins with {q(key)}: {', '.join(q(p) for p in printed)}; the next line, "
                       f"{q(line_at(after)[0]) if after < size else 'the end'}, does not."):
        draw(found, found, None, done=True)
        side([(f"{len(probes)} probes for {len(words)} lines", "t"),
              ("printed:", "t")] + [(show(p), "ta") for p in printed])
    return f


FIGS = [
    ("02.01-insertion", insertion0201),
    ("02.02-merges", merge0202),
    ("02.03-partition", quick0203),
    ("02.04-sift", heap0204),
    ("02.05-runs", runs0205),
    ("02.06-halving", look0206),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        fig = fn()
        n = steps.check(fig.svg())
        print(figlib.write(MOD, name, fig), f"({n} steps)")


if __name__ == "__main__":
    main()
