"""The dsa track's art: its home card and top-bar icon, and each module's cover and icon.

    python3 -B art/dsa/covers.py           write every file, then check each cover against the real
                                           programs and every file against the site's sanitizer
    python3 -B art/dsa/covers.py --quick   write every file, check it against the sanitizer only

Writes
    tracks/dsa/art.svg, icon.svg            the home page card (280x160) and the top-bar icon (20x20)
    tracks/dsa/lessons/NN-*/cover.svg       module NN's teaching diagram, 640x300
    tracks/dsa/lessons/NN-*/icon.svg        module NN's line icon, 20x20, currentColor

Covers style themselves only through the .art classes in harness/web/app.css:
    s m a        stroke: foreground, muted, accent
    f fs af fa   fill: page, code background, accent-soft, accent
    t tm ta      text fill: foreground, muted, accent      mono: monospace

Each cover draws the finished code's own structure on a small example (the lessons' own where
they have one), and every value it shows is worked out here from a model of that code. Without
--quick the script then writes the finished project (./learn files dsa --at <last lesson>),
builds it, runs the real tools on the same examples, and stops with an error unless they print
what the covers show:

  00  bin/paste -s --algo=strcat and --algo=end on the book, twice and four times over (DS_STATS)
  01  'the cat sat on the mat, the act' through bin/freq --hash=sum --no-grow, and bin/freq
  02  the eight words of figs02.py through bin/sort -S 100b: its runs and its heap's counts
  03  'the cat sat\\n', goto 4, type 'fat ': bin/edit --replay with the gap buffer and the tree
  04  'abbb' through bin/grep -E 'abab|abbb', --algo=nfa and --algo=dfa (DS_TRACE)
  05  bin/spell -p ca, -s and --distance on six words; --algo=bloom against the trie on the book
  06  lines 8-13 of the book against the copy the diff lessons use: bin/diff --algo=table
  07  figs07.py's cut-down copy of the track's Makefile, table.c touched, bin/make -j 2
  08  the cover's seven junctions as a map file, bin/route --algo=dijkstra and --algo=bfs
  09  abracadabra through bin/gzip --huffman and --lz77
  10  the two commits drawn, made with bin/git: every object name

The times on cover 00 are the growth harness's run that lesson 00.02's figure draws (figs00.py).
The script began as the outline's art, drawn before the code existed (art/outlines/dsa_art.py,
removed with the outline's art folder); the covers it drew wrong were drawn again from the code.
"""
import hashlib
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from figart import Art, esc  # noqa: E402
import figs00  # noqa: E402      the growth harness's measured times (RACE_STRCAT, RACE_END)
import figs07  # noqa: E402      MINI, the cut-down Makefile the make lessons use

TRACK = os.path.join(ROOT, "tracks", "dsa")
LESSONS = os.path.join(TRACK, "lessons")


def cell(a, x, y, w, h, s, cls="s f", tcls="t", size=12, rx=4, dash=False, weight=None, mono=True):
    """A box with one centred label: an array slot, a heap node, a buffer byte."""
    a.box(x, y, w, h, cls, rx=rx, dash=dash)
    if s:
        a.text(round(x + w / 2, 1), round(y + h / 2 + size * 0.35, 1), s, tcls, size, "middle", weight, mono)


def node(a, x, y, s, r=14, cls="s f", tcls="t", size=12, weight=600, mono=True):
    a.circle(x, y, r, cls)
    a.text(x, round(y + size * 0.35, 1), s, tcls, size, "middle", weight, mono)


def toward(x1, y1, x2, y2, r1, r2):
    """The segment between two circles' edges (centre to centre, shortened by each radius)."""
    d = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    return round(x1 + ux * r1, 1), round(y1 + uy * r1, 1), round(x2 - ux * r2, 1), round(y2 - uy * r2, 1)


def stats(err, name):
    """{count: number} from the 'stats: NAME: count N, count N' line of DS_STATS output."""
    m = re.search(rf"^stats: {re.escape(name)}: (.*)$", err, re.M)
    assert m, f"no stats line for {name}"
    return {k: int(v) for v, k in [(p.split(" ")[-1], " ".join(p.split(" ")[:-1])) for p in m.group(1).split(", ")]}


# =================================================================== 00 the workbench

# bin/paste -s --algo=strcat FILE with DS_STATS=1: (file, lines, bytes copied, bytes scanned); with
# --algo=end the bytes scanned are 0. two.txt is the book twice, four.txt two.txt twice (00.01).
PASTE = [("book.txt", 11922, 562403, 6659837313), ("two.txt", 23844, 1124807, 26729635601),
         ("four.txt", 47688, 2249615, 107099115105)]


def cover00():
    a = Art("d00", "One job done two ways: paste -s with strcat(), which reads all it has joined again "
                   "for each line, and with the end remembered; doubling the input tells them apart")
    a.text(24, 30, "one job: paste -s, a file's lines joined into one", size=12, weight=700)
    a.text(24, 49, "slow, --algo=strcat: strlen() finds the end again for each line", "tm", 10.5)
    a.text(24, 65, "fast, --algo=end: it remembers where the end is", "tm", 10.5)
    y0 = 98
    a.text(24, y0, "input", "tm", 10)
    a.text(132, y0, "lines", "tm", 10, "end")
    a.text(264, y0, "bytes strlen() read", "tm", 10, "end")
    a.text(340, y0, "fast", "tm", 10, "end")
    for k, (name, lines, copied, scanned) in enumerate(PASTE):
        y = y0 + 21 + k * 19
        last = k == len(PASTE) - 1
        a.text(24, y, name, size=11, mono=True)
        a.text(132, y, f"{lines:,}", size=11, anchor="end", mono=True)
        a.text(264, y, f"{scanned:,}", "ta" if last else "t", 11, "end", 700 if last else None, True)
        if k:
            a.text(272, y, f"x{scanned / PASTE[k - 1][3]:.2f}", "ta", 10.5, weight=600, mono=True)
        a.text(340, y, "0", size=11, anchor="end", mono=True)
    _, _, copied, scanned = PASTE[-1]
    a.text(24, 196, f"To copy {copied / 1e6:.1f} million bytes, the slow way read", "tm", 10.5)
    a.text(24, 212, f"{scanned / 1e9:.0f} billion: twice the lines, four times the reading.", "tm", 10.5)
    a.text(24, 236, "The fast way reads none of it again, however long", "tm", 10.5)
    a.text(24, 252, "the file: the same output, one line of add() apart.", "tm", 10.5)

    # the growth harness's times, on log-log axes: the slope is the power of n
    ns = sorted(figs00.RACE_STRCAT)
    assert ns == sorted(figs00.RACE_END) and all(b == 2 * a_ for a_, b in zip(ns, ns[1:]))
    px0, px1, py0, py1 = 394, 612, 44, 200
    lo, hi = -3.4, 1.0
    X = lambda k: round(px0 + 12 + k * (px1 - px0 - 24) / (len(ns) - 1), 1)  # noqa: E731
    Y = lambda t: round(py1 - (math.log10(t) - lo) / (hi - lo) * (py1 - py0), 1)  # noqa: E731
    a.line(px0, py1, px1, py1, "m")
    a.line(px0, py1, px0, py0 - 8, "m")
    for t, lab in ((0.001, "1 ms"), (0.01, "10 ms"), (0.1, "0.1 s"), (1, "1 s"), (10, "10 s")):
        a.line(px0 - 4, Y(t), px0, Y(t), "m")
        a.text(px0 - 8, Y(t) + 3.5, lab, "tm", 9.5, "end", mono=True)
    for k, n in enumerate(ns):
        a.line(X(k), py1, X(k), py1 + 4, "m")
        a.text(X(k), py1 + 16, f"{n // 1000}k" if n < 1000000 else f"{n / 1e6:.0f}M".replace(".0M", "M"),
               "tm", 9.5, "middle", mono=True)
    a.text(px0, 30, "seconds, log scale", "tm", 10.5)
    a.text(px1, py1 + 34, "words of text, log scale", "tm", 10.5, "end")
    sp = [(X(k), Y(figs00.RACE_STRCAT[n])) for k, n in enumerate(ns)]
    ep = [(X(k), Y(figs00.RACE_END[n])) for k, n in enumerate(ns)]
    a.path("M" + " L".join(f"{x} {y}" for x, y in sp), "a")
    a.path("M" + " L".join(f"{x} {y}" for x, y in ep), "s")
    for x, y in sp:
        a.circle(x, y, 3.5, "a fa")
    for x, y in ep:
        a.circle(x, y, 3.5, "s f")
    ratios = [figs00.RACE_STRCAT[b] / figs00.RACE_STRCAT[a_] for a_, b in zip(ns, ns[1:])][-3:]
    a.text(px0 + 14, 62, "--algo=strcat", "ta", 10.5, weight=700, mono=True)
    a.text(px0 + 14, 77, f"x{sum(ratios) / 3:.1f} a doubling: n^2", "ta", 10.5, weight=600)
    a.text(px1, py1 - 7, "--algo=end: start-up only", size=10, anchor="end", weight=600)
    s16, e16 = figs00.RACE_STRCAT[ns[0]] * 1000, figs00.RACE_END[ns[0]] * 1000
    a.text(24, 282, f"Double n and divide the times: a steady x4 is n^2, x2 is n. Small inputs hide it: at "
                    f"{ns[0]:,} words the two take {s16:.0f} ms and {e16:.0f} ms.", "tm", 11)
    return a


def check00(real):
    bad = []
    with open(os.path.join(real.dir, "data", "book.txt"), "rb") as f:
        book = f.read()
    for name, times in (("two.txt", 2), ("four.txt", 4)):
        with open(os.path.join(real.dir, name), "wb") as f:
            f.write(book * times)
    files = {"book.txt": "data/book.txt", "two.txt": "two.txt", "four.txt": "four.txt"}
    for name, lines, copied, scanned in PASTE:
        _, err = real.run(["bin/paste", "-s", "--algo=strcat", files[name]], stats=True)
        st = stats(err, "paste")
        if (st["lines"], st["bytes copied"], st["bytes scanned"]) != (lines, copied, scanned):
            bad.append(f"00: paste --algo=strcat {name}: {st}")
        _, err = real.run(["bin/paste", "-s", "--algo=end", files[name]], stats=True)
        st = stats(err, "paste")
        if (st["lines"], st["bytes copied"], st["bytes scanned"]) != (lines, copied, 0):
            bad.append(f"00: paste --algo=end {name}: {st}")
    return bad


# =================================================================== 01 freq

TEXT01 = b"the cat sat on the mat, the act\n"


def hash_sum(w):
    return sum(w)


def hash_fnv1a(w):
    h = 14695981039346656037
    for b in w:
        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


class Table:
    """lib/table.c: entries in one array in the order added, nbuckets lists through next, a new
    entry at the head of its list. (No growing: these few words never fill 1024 buckets.)"""

    def __init__(self, hash_fn):
        self.hash, self.nb = hash_fn, 1024
        self.buckets = [-1] * self.nb
        self.keys, self.values, self.next, self.hashes = [], [], [], []
        self.lookups = self.probes = 0

    def find(self, w, h):
        self.lookups += 1
        i = self.buckets[h & (self.nb - 1)]
        while i >= 0:
            self.probes += 1
            if self.hashes[i] == h and self.keys[i] == w:
                return i
            i = self.next[i]
        return -1

    def get(self, w):
        return self.find(w, self.hash(w))

    def put(self, w):
        h = self.hash(w)
        i = self.find(w, h)
        if i >= 0:
            return i
        b = h & (self.nb - 1)
        self.keys.append(w)
        self.values.append(0)
        self.hashes.append(h)
        self.next.append(self.buckets[b])
        self.buckets[b] = len(self.keys) - 1
        return len(self.keys) - 1

    def bucket(self, i):
        return self.hashes[i] & (self.nb - 1)


def count01(hash_fn):
    """freq's count_table on TEXT01: a get for every word, a put for a new one."""
    t = Table(hash_fn)
    for w in re.findall(rb"[A-Za-z]+", TEXT01):
        w = w.lower()
        i = t.get(w)
        if i < 0:
            i = t.put(w)
        t.values[i] += 1
    return t


def cover01():
    a = Art("d01", "A hash table with chained buckets: a word's hash picks one of 1024 buckets, each bucket "
                   "is a list of entries kept in one array, and the buckets double once there are as many "
                   "entries as buckets")
    ts, tf = count01(hash_sum), count01(hash_fnv1a)
    assert ts.keys == tf.keys
    words = [w.decode() for w in ts.keys]
    a.text(24, 30, "printf 'the cat sat on the mat, the act\\n' | bin/freq", size=11.5, weight=600, mono=True)
    a.text(24, 50, f"{ts.lookups} lookups (a get for each word, a put for each new one): {ts.probes} entries "
                   f"compared by the sum, {tf.probes} by FNV-1a", "tm", 10.5)
    top, rh, h = 94, 24, 21
    tx, tw_ = 176, 206
    a.text(24, top - 22, "the sum's bucket (01.02)", "tm", 10)
    a.text(tx, top - 22, "entries: one Array, in the order added", "tm", 10)
    a.text(616, top - 22, "FNV-1a's bucket (01.03)", "tm", 10, "end")
    a.text(tx + 30, top - 6, "key", "tm", 9.5)
    a.text(tx + 120, top - 6, "count", "tm", 9.5)
    a.text(tx + tw_ - 26, top - 6, "next", "tm", 9.5, "middle")
    heads = {ts.buckets[b]: b for b in range(ts.nb) if ts.buckets[b] >= 0}
    chain = [i for i in range(len(words)) if ts.next[i] >= 0]
    assert len(chain) == 1
    first, second = chain[0], ts.next[chain[0]]
    for i, w in enumerate(words):
        y = top + i * rh
        hot = i in (first, second)
        a.box(tx, y, tw_, h, "a af" if hot else "s f", rx=4)
        a.text(tx + 12, y + 16, str(i), "ta" if hot else "tm", 11, "middle", mono=True)
        a.text(tx + 30, y + 16, w, "ta" if hot else "t", 12, weight=700 if hot else 600, mono=True)
        a.text(tx + 120, y + 15, str(ts.values[i]), "ta" if hot else "t", 11, mono=True)
        a.text(tx + tw_ - 26, y + 15, str(ts.next[i]), "ta" if hot else "tm", 11, "middle", mono=True)
        if i in heads:
            b = heads[i]
            cell(a, 24, y, 88, h, f"{b}", "a af" if hot else "s fs", "ta" if hot else "t", 11.5, rx=4,
                 weight=700 if hot else None)
            a.line(112, y + h / 2, tx - 3, y + h / 2, "a" if hot else "s", arrow=True)
        else:
            a.text(68, y + 15, f"in {ts.bucket(i)}'s list", "ta" if hot else "tm", 10, "middle")
        cell(a, 528, y, 88, h, f"{tf.bucket(i)}", "s f", "t", 11.5, rx=4)
    y1, y2 = top + first * rh + h / 2, top + second * rh + h / 2
    a.path(f"M{tx + tw_} {y1} C {tx + tw_ + 34} {y1}, {tx + tw_ + 34} {y2}, {tx + tw_ + 2} {y2}", "a", arrow=True)
    a.text(tx + tw_ + 34, (y1 + y2) / 2 + 4, "next", "ta", 10.5, weight=600)
    sw, sf = words[second], words[first]
    yb = top + len(words) * rh + 8
    a.text(24, yb + 4, f"'{sw}' and '{sf}' both add up to {hash_sum(sf.encode())}: one bucket, one list, "
                       f"'{sf}' at its head as the newer.", "tm", 10.5)
    a.text(616, yb + 4, "by FNV-1a, a list each", "tm", 10.5, "end")
    a.text(24, 272, "A new key goes at the head of its bucket's list. Once there are as many entries as "
                    "buckets, the buckets double", "tm", 11)
    a.text(24, 289, "and every entry is linked into its new bucket's list, from the hash it kept; the "
                    "entries never move.", "tm", 11)
    return a


def check01(real):
    bad = []
    for args, t in ((["--hash=sum", "--no-grow"], count01(hash_sum)), ([], count01(hash_fnv1a))):
        out, err = real.run(["bin/freq"] + args, TEXT01, stats=True)
        st = stats(err, "table")
        if (st["lookups"], st["probes"], st["inserts"], st["resizes"]) != (t.lookups, t.probes, len(t.keys), 0):
            bad.append(f"01: freq {args}: {st}")
        got = {w: int(n) for n, w in (ln.split() for ln in out.splitlines())}
        if got != {w.decode(): t.values[i] for i, w in enumerate(t.keys)}:
            bad.append(f"01: freq {args} counted {got}")
    return bad


# =================================================================== 02 sort

WORDS02 = ["to", "sherlock", "holmes", "she", "is", "always", "the", "woman"]   # figs02.py's eight
RUN02 = 3                    # lines a run holds at -S 100b (the real sort writes 3 runs of them)


class Heap:
    """lib/heap.c's min-heap: push at the end and sift up; pop the top, the last item down from the
    top; counting comparisons and moves as it does."""

    def __init__(self, less):
        self.v, self.less, self.comparisons, self.moves, self.pushes, self.pops = [], less, 0, 0, 0, 0

    def above(self, a, b):
        self.comparisons += 1
        return self.less(a, b)

    def push(self, x):
        self.v.append(x)
        i = len(self.v) - 1
        while i > 0:
            p = (i - 1) // 2
            if not self.above(x, self.v[p]):
                break
            self.v[i] = self.v[p]
            self.moves += 1
            i = p
        self.v[i] = x
        self.moves += 1
        self.pushes += 1

    def pop(self):
        top, last = self.v[0], self.v.pop()
        if self.v:
            v, n, i = self.v, len(self.v), 0
            while True:
                c = 2 * i + 1
                if c >= n:
                    break
                if c + 1 < n and self.above(v[c + 1], v[c]):
                    c += 1
                if not self.above(v[c], last):
                    break
                v[i] = v[c]
                self.moves += 1
                i = c
            v[i] = last
            self.moves += 1
        self.pops += 1
        return top


def merge02():
    """sort.c's merge_runs on the runs of WORDS02: every step, and the heap that did it."""
    runs = [sorted(WORDS02[i:i + RUN02], key=str.encode) for i in range(0, len(WORDS02), RUN02)]
    h = Heap(lambda x, y: (runs[x[0]][x[1]].encode(), x[0]) < (runs[y[0]][y[1]].encode(), y[0]))
    for r in range(len(runs)):
        h.push((r, 0))
    out, steps = [], []
    while h.v:
        steps.append((list(out), list(h.v)))
        r, k = h.pop()
        out.append(runs[r][k])
        if k + 1 < len(runs[r]):
            h.push((r, k + 1))
    assert out == sorted(WORDS02, key=str.encode)
    return runs, steps, h


def cover02():
    a = Art("d02", "Sorting a file bigger than memory: sorted runs on disk, merged through a heap of the runs, "
                   "the run with the smallest next line on top")
    runs, steps, _ = merge02()
    out, heap = steps[2]                                     # two lines out; the third is next
    top_run, top_k = heap[0]
    a.text(24, 30, f"printf '{' '.join(WORDS02)}' | tr ' ' '\\n' | bin/sort -S 100b", "t", 11, weight=600, mono=True)
    a.text(24, 52, "the runs on disk, each sorted", "tm", 10.5)
    cw, ch = 66, 26
    nxt = {r: k for r, k in heap}
    for i, r in enumerate(runs):
        y = 64 + i * 44
        a.text(24, y + 18, f"run {i + 1}", "ta" if i == top_run else "t", 11, weight=700 if i == top_run else None,
               mono=True)
        for k, w in enumerate(r):
            x = 74 + k * (cw + 4)
            done = k < nxt.get(i, len(r))
            head = nxt.get(i) == k
            foc = head and i == top_run
            cls = "a af" if foc else ("m" if done else ("s fs" if head else "s f"))
            cell(a, x, y, cw, ch, w, cls, "ta" if foc else ("tm" if done else "t"), 11.5, rx=5, dash=done,
                 weight=700 if head else None)
    a.text(74, 208, "dashed: written out already", "tm", 10.5)

    # the heap: one entry per run with lines left, the smallest next line on top
    hx = 382
    a.text(hx, 52, "the heap of runs", "tm", 10.5, "middle")
    pts = [(hx, 82), (hx - 58, 150), (hx + 58, 150)]
    bw, bh = 76, 26
    for k in range(1, len(heap)):
        (x1, y1), (x2, y2) = pts[0], pts[k]
        a.line(x1 + (-14 if k == 1 else 14), y1 + bh / 2, x2, y2 - bh / 2 - 1, "s")
    for k, (r, i) in enumerate(heap):
        x, y = pts[k]
        foc = k == 0
        cell(a, x - bw / 2, y - bh / 2, bw, bh, runs[r][i], "a af" if foc else "s fs", "ta" if foc else "t", 12,
             rx=13, weight=700)
        a.text(x, y + bh / 2 + 14, f"run {r + 1}", "ta" if foc else "tm", 10, "middle")
    a.text(hx, 208, "as an array: [" + ", ".join(runs[r][i] for r, i in heap) + "]", "tm", 10.5, "middle", mono=True)

    ox = 506
    a.text(ox, 52, "output", "tm", 10.5)
    for k, w in enumerate(out):
        cell(a, ox, 64 + k * 32, 76, ch, w, "s f", "t", 11.5, rx=5)
    ny = 64 + len(out) * 32
    cell(a, ox, ny, 76, ch, runs[top_run][top_k], "a af", "ta", 11.5, rx=5, weight=700)
    a.path(f"M{hx + bw / 2} 82 C {hx + 80} 82, {ox - 40} {ny + ch / 2}, {ox - 2} {ny + ch / 2}", "a", arrow=True)
    a.text(ox, ny + 50, f"pop {runs[top_run][top_k]}, the smallest;", "ta", 10.5, weight=600)
    a.text(ox, ny + 66, f"push {runs[top_run][top_k + 1]}, the next", "tm", 10.5)
    a.text(ox, ny + 82, f"line of run {top_run + 1}", "tm", 10.5)
    a.text(24, 252, "Sort what fits in memory into runs on disk, then merge them, 16 at a time at most: one heap "
                    "entry per run,", "tm", 11)
    a.text(24, 270, "so each line out costs about log2(runs) comparisons, and only one line a run is held "
                    "in memory.", "tm", 11)
    return a


def check02(real):
    runs, _, h = merge02()
    out, err = real.run(["bin/sort", "-S", "100b"], "".join(w + "\n" for w in WORDS02).encode(), stats=True)
    bad = []
    if out.split() != sorted(WORDS02, key=str.encode):
        bad.append(f"02: sort -S 100b printed {out.split()}")
    st = stats(err, "runs")
    if (st["written"], st["merges"]) != (len(runs), 1):
        bad.append(f"02: runs {st}")
    st = stats(err, "heap")
    if (st["pushes"], st["pops"], st["comparisons"], st["moves"]) != (h.pushes, h.pops, h.comparisons, h.moves):
        bad.append(f"02: heap {st}, the model {(h.pushes, h.pops, h.comparisons, h.moves)}")
    return bad


# =================================================================== 03 edit

TEXT03, AT03, TYPED03 = "the cat sat\n", 4, "fat "     # figs03.py's file and its first edit
GAP03 = 16                   # the gap a gap buffer has after loading the 12 bytes (the trace shows it)


def show(s):
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def trace03():
    """What the real editor's DS_TRACE prints for the edit: the gap buffer's lines, and the state of
    the piece tree and of the piece list after the last key."""
    gap, before, after = [], TEXT03[:AT03], TEXT03[AT03:]
    for k, c in enumerate(TYPED03):
        before += c
        gap.append(f'trace: gap buffer: insert {AT03 + k} "{show(c)}": moved {len(after) if k == 0 else 0} | '
                   f'"{show(before)}" [{GAP03 - k - 1}] "{show(after)}"')
    p = [f'orig 0+{AT03} "{show(TEXT03[:AT03])}"', f'add 0+{len(TYPED03)} "{show(TYPED03)}"',
         f'orig {AT03}+{len(TEXT03) - AT03} "{show(TEXT03[AT03:])}"']
    return gap, f"((. {p[0]} .) {p[1]} (. {p[2]} .))", " | ".join(p)


def cover03():
    a = Art("d03", "Two ways to hold the text: a gap buffer, whose gap goes to where the typing is, and a "
                   "piece table, which never moves a byte")
    cw = 18
    gw = 46

    def bytes_row(x, y, s, hot=(), size=11):
        for k, c in enumerate(s):
            on = k in hot
            cell(a, x + k * cw, y, cw, 24, "\\n" if c == "\n" else c.strip(), "a af" if on else "s f",
                 "ta" if on else "t", 9 if c == "\n" else size, rx=0)
        return x + len(s) * cw

    def gap(x, y, n):
        a.box(x, y, gw, 24, "m fs", rx=0, dash=True)
        a.text(x + gw / 2, y + 16, f"[{n}]", "tm", 10.5, "middle", mono=True)
        return x + gw

    a.text(24, 26, "gap buffer", size=12, weight=700)
    a.text(104, 26, f"'{show(TEXT03)}', then type '{TYPED03}' at {AT03}", "tm", 10.5)
    y1, y2 = 38, 84
    x = bytes_row(24, y1, TEXT03)
    gap(x, y1, GAP03)
    a.text(x + gw + 10, y1 + 16, "loaded: the gap at the end", "tm", 10.5)
    x = bytes_row(24, y2, TEXT03[:AT03])
    x = bytes_row(x, y2, TYPED03, hot=range(len(TYPED03)))
    gx = x
    x = gap(x, y2, GAP03 - len(TYPED03))
    bytes_row(x, y2, TEXT03[AT03:])
    # what the first key carried across: the bytes after the cursor, to the far side of the gap
    tail = len(TEXT03) - AT03
    a.path(f"M{24 + AT03 * cw + 2} {y1 + 27} V {y1 + 31} H {24 + len(TEXT03) * cw - 2} V {y1 + 27}", "s")
    a.line(24 + (AT03 + tail / 2) * cw, y1 + 31, x + tail * cw / 2, y2 - 3, "s", arrow=True)
    nx = x + tail * cw + 10
    a.text(nx, y2 - 2, f"the first key carries the {tail} bytes", "tm", 10.5)
    a.text(nx, y2 + 13, "after it across the gap, once; each", "tm", 10.5)
    a.text(nx, y2 + 28, "key after that fills a byte of the gap", "tm", 10.5)
    a.line(gx, y2 - 4, gx, y2 + 28, "a")

    # the piece table, the same edit: two buffers, and the pieces, in text order (03.04) and in a tree (03.05)
    a.text(24, 140, "piece table", size=12, weight=700)
    a.text(110, 140, "the same edit: two buffers, and the pieces that say how to read them", "tm", 10.5)
    ox, oy = 100, 152
    a.text(24, oy + 16, "original", "tm", 10.5)
    bytes_row(ox, oy, TEXT03)
    a.text(ox + len(TEXT03) * cw + 8, oy + 16, "the file, mapped: never changed", "tm", 10.5)
    ay = 262
    a.text(24, ay + 16, "add", "tm", 10.5)
    bytes_row(ox, ay, TYPED03, hot=range(len(TYPED03)))
    a.text(ox + len(TYPED03) * cw + 8, ay + 16, "only added to", "tm", 10.5)
    pieces = [("orig", 0, AT03), ("add", 0, len(TYPED03)), ("orig", AT03, len(TEXT03) - AT03)]
    pw, ph, py = 92, 26, 200
    a.text(24, py + 17, "pieces", "tm", 10.5)
    for k, (buf, s, n) in enumerate(pieces):
        px = ox + k * (pw + 22)
        foc = buf == "add"
        cell(a, px, py, pw, ph, f"{buf} {s}+{n}", "a af" if foc else "s fs", "ta" if foc else "t", 11.5, rx=6,
             weight=700)
        if k:
            a.line(px - 22, py + ph / 2, px - 2, py + ph / 2, "s", arrow=True)
        if buf == "orig":
            a.path(f"M{ox + s * cw + 2} {oy + 28} V {oy + 33} H {ox + (s + n) * cw - 2} V {oy + 28}", "s")
            a.line(round(ox + (s + n / 2) * cw, 1), oy + 33, px + pw / 2, py - 2, "s", arrow=True)
        else:
            a.line(px + pw / 2, py + ph, ox + len(TYPED03) * cw / 2, ay - 2, "a", arrow=True)
    # 03.05: the same pieces in a balanced tree, the list being its order from left to right
    tx = 476
    a.text(tx, 194, "in a balanced tree (03.05):", "tm", 10.5)
    tw2 = 66
    spots = [(tx + 2, 248), (tx + 40, 212), (tx + 78, 248)]
    for (x1, y1_), (x2, y2_) in ((spots[1], spots[0]), (spots[1], spots[2])):
        a.line(x1 + tw2 / 2 + (-14 if x2 < x1 else 14), y1_ + 22, x2 + tw2 / 2, y2_ - 1, "s")
    for (x_, y_), (buf, s, n) in zip(spots, pieces):
        foc = buf == "add"
        cell(a, x_, y_, tw2, 22, f"{buf} {s}+{n}", "a af" if foc else "s fs", "ta" if foc else "t", 10, rx=6,
             weight=700)
    a.add(f'<text class="t mono" x="{tx}" y="290" font-size="11">{esc(show(TEXT03[:AT03]))}'
          f'<tspan class="ta" font-weight="700">{esc(TYPED03)}</tspan>{esc(show(TEXT03[AT03:]))}</text>')
    return a


def check03(real):
    bad = []
    path = os.path.join(real.tmp, "cat.txt")
    with open(path, "w") as f:
        f.write(TEXT03)
    script = f"goto {AT03}\ntype {TYPED03}\n".encode()
    gap, tree, lst = trace03()
    _, err = real.run(["bin/edit", "--algo=gap", "--replay", "-", path], script, trace=True)
    got = [ln for ln in err.splitlines() if ln.startswith("trace: gap buffer:")]
    if got != gap:
        bad.append(f"03: gap buffer trace {got}")
    for algo, want in (("tree", tree), ("pieces", lst)):
        _, err = real.run(["bin/edit", f"--algo={algo}", "--replay", "-", path], script, trace=True)
        last = [ln for ln in err.splitlines() if re.match(r"trace: piece (tree|list): insert", ln)][-1]
        if not last.endswith("| " + want):
            bad.append(f"03: --algo={algo} trace {last}")
    return bad


# =================================================================== 04 grep

PATTERN04, LINE04 = "abab|abbb", "abbb"
# The machine nfa.c makes of PATTERN04, as DS_TRACE=1 prints it: state: split targets, a byte and the
# state it leads to, or the match.
NFA04 = {0: ("split", (1, 5)), 1: ("a", 2), 2: ("b", 3), 3: ("a", 4), 4: ("b", 9),
         5: ("a", 6), 6: ("b", 7), 7: ("b", 8), 8: ("b", 9), 9: ("match", None)}


def closure(states):
    out, todo = set(), list(states)
    while todo:
        s = todo.pop()
        if s in out:
            continue
        kind, to = NFA04[s]
        if kind == "split":
            todo.extend(to)
        else:
            out.add(s)
    return out


def sets04():
    """The live states before the first byte and after each one: grep -E finds a match anywhere in
    the line, so the start's states come in again at every byte."""
    start = closure({0})
    sets = [start]
    for c in LINE04:
        step = {NFA04[s][1] for s in sets[-1] if NFA04[s][0] == c}
        sets.append(closure(step) | start)
    return sets


def nfa_line(s):
    kind, to = NFA04[s]
    if kind == "split":
        return f"trace: nfa: state {s}: split -> {to[0]}, {to[1]}"
    if kind == "match":
        return f"trace: nfa: state {s}: match"
    return f"trace: nfa: state {s}: {kind} -> {to}"


def cover04():
    a = Art("d04", "A regular expression as a machine: grep -E follows every live state at once, a byte at a "
                   "time, and each set of states becomes a DFA state the first time it is met")
    sets = sets04()
    match = [s for s, (k, _) in NFA04.items() if k == "match"][0]
    assert match in sets[-1]
    path = [0, 5, 6, 7, 8, match]
    a.text(24, 30, f"grep -E '{PATTERN04}'", size=12.5, weight=700, mono=True)
    pos = {0: (62, 146), match: (446, 146)}
    for k in range(4):
        pos[1 + k] = (136 + k * 76, 88)
        pos[5 + k] = (136 + k * 76, 204)
    r = 16
    a.line(24, 146, pos[0][0] - r - 2, 146, "s", arrow=True)
    a.text(24, 136, "start", "tm", 10)
    alive = set().union(*sets)
    for s, (kind, to) in NFA04.items():
        targets = to if kind == "split" else ((to,) if to is not None else ())
        for t in targets:
            x1, y1, x2, y2 = toward(*pos[s], *pos[t], r, r + 2)
            on = s in path and t in path
            a.line(x1, y1, x2, y2, "a" if on else ("s" if t in alive else "m"), arrow=True)
            if kind != "split":
                mx, my = (pos[s][0] + pos[t][0]) / 2, (pos[s][1] + pos[t][1]) / 2
                level = pos[s][1] == pos[t][1]
                dx, dy = (0, -8) if level else (12, -2 if pos[s][1] < pos[t][1] else 12)
                a.text(round(mx + dx, 1), round(my + dy, 1), kind, "ta" if on else "tm", 12, "middle", 600, mono=True)
    for s, (x, y) in pos.items():
        on = s in path
        dead = s not in alive
        a.circle(x, y, r, "a af" if on else ("m f" if dead else "s f"))
        if s == match:
            a.circle(x, y, r - 4, "a")
        a.text(x, y + 4.5, str(s), "ta" if on else ("tm" if dead else "t"), 12, "middle", 600, mono=True)
    a.text(pos[3][0], pos[3][1] - 26, "wants 'a', reads 'b': dropped", "tm", 10.5, "middle")
    a.text(pos[match][0], pos[match][1] + 34, "match", "ta", 11, "middle", 700)
    a.text(pos[0][0], pos[0][1] + 30, "split", "tm", 10, "middle")

    sx = 484
    a.text(sx, 30, f"reading '{LINE04}'", size=12, weight=700)
    a.text(sx, 46, "live states: a DFA state each", "tm", 10.5)
    for k, st in enumerate(sets):
        y = 58 + k * 40
        last = k == len(sets) - 1
        a.text(sx, y + 17, f"D{k}", "ta" if last else "tm", 11, weight=600, mono=True)
        cell(a, sx + 24, y, 92, 26, "{" + " ".join(str(s) for s in sorted(st)) + "}", "a af" if last else "s fs",
             "ta" if last else "t", 11.5, rx=6, weight=600)
        if k < len(LINE04):
            a.line(sx + 70, y + 26, sx + 70, y + 38, "s", arrow=True)
            a.text(sx + 80, y + 36, LINE04[k], "tm", 11.5, weight=600, mono=True)
    a.text(24, 262, f"States {sorted(sets[0])[0]} and {sorted(sets[0])[1]} stay live: a match may start at any "
                    "byte. No backtracking: each byte is read once,", "tm", 11)
    a.text(24, 280, "and the DFA keeps each set it has made in a hash table, so meeting it again costs one "
                    "lookup. Double ring: the match.", "tm", 11)
    return a


def check04(real):
    bad = []
    sets = sets04()
    nfa = [nfa_line(s) for s in sorted(NFA04)]
    want_nfa = nfa + ["trace: nfa: start 0", "trace: line: " + LINE04,
                      "trace: nfa: start: {" + " ".join(map(str, sorted(sets[0]))) + "}"]
    want_nfa += [f"trace: nfa: at {k} '{c}': {{{' '.join(map(str, sorted(sets[k + 1])))}}}"
                 for k, c in enumerate(LINE04)]
    out, err = real.run(["bin/grep", "-E", "--algo=nfa", PATTERN04], (LINE04 + "\n").encode(), trace=True)
    if out != LINE04 + "\n" or [ln for ln in err.splitlines() if ln.startswith("trace:")] != want_nfa:
        bad.append("04: grep --algo=nfa's trace differs: " + err)
    out, err = real.run(["bin/grep", "-E", "--algo=dfa", PATTERN04], (LINE04 + "\n").encode(), trace=True, stats=True)
    want = ["trace: dfa: start: D0 (built: {" + " ".join(map(str, sorted(sets[0]))) + "})"]
    want += [f"trace: dfa: at {k} '{c}': D{k} -> D{k + 1} (built: {{{' '.join(map(str, sorted(sets[k + 1])))}}})"
             for k, c in enumerate(LINE04)]
    if [ln for ln in err.splitlines() if ln.startswith("trace: dfa:")] != want:
        bad.append("04: grep --algo=dfa's trace differs: " + err)
    st = stats(err, "dfa")
    if (st["states built"], st["misses"]) != (len(sets), len(LINE04)):
        bad.append(f"04: dfa {st}")
    if "stats: table:" not in err:
        bad.append("04: the DFA used no hash table")
    return bad


# =================================================================== 05 spell

WORDS05 = ["car", "card", "care", "cat", "do", "dog"]
PREFIX05, TYPO05 = "ca", "cst"
# bin/spell on the book with DS_STATS=1: --algo=bloom (the default --fp of 0.01) against the trie.
BLOOM05 = {"keys": 60388, "bits": 578827, "hashes": 7, "bytes": 72354}
UNKNOWN05 = {"trie": 615, "bloom": 608}


def lev(s, t):
    prev = list(range(len(t) + 1))
    for i, cs in enumerate(s, 1):
        cur = [i]
        for j, ct in enumerate(t, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (cs != ct)))
        prev = cur
    return prev[-1]


def cover05():
    a = Art("d05", "A trie: a prefix is one walk from the root, every word below it is a completion, and a "
                   "word not on any path is a misspelling to suggest for")
    words, prefix, typo = WORDS05, PREFIX05, TYPO05
    trie = {}
    for w in words:
        n = trie
        for ch in w:
            n = n.setdefault(ch, {})
        n["$"] = True
    completions = sorted(w for w in words if w.startswith(prefix))
    best = min(lev(typo, w) for w in words)
    near = [w for w in words if lev(typo, w) == best]
    assert len(near) == 1

    pos = {"": (40, 150), "c": (112, 106), "d": (112, 226), "ca": (184, 106), "do": (184, 226),
           "car": (256, 70), "cat": (256, 166), "dog": (256, 226), "card": (328, 44), "care": (328, 100)}
    r = 15

    def walk(n, key):
        for ch, sub in n.items():
            if ch == "$":
                continue
            k = key + ch
            x1, y1, x2, y2 = toward(*pos[key], *pos[k], r, r)
            on = prefix.startswith(k) or k.startswith(prefix)
            a.line(x1, y1, x2, y2, "a" if on else "s")
            walk(sub, k)

    def get(key):
        n = trie
        for ch in key:
            n = n[ch]
        return n
    walk(trie, "")
    for key, (x, y) in pos.items():
        on = key and (prefix.startswith(key) or key.startswith(prefix))
        a.circle(x, y, r, "a af" if on else ("s fs" if not key else "s f"))
        if get(key).get("$"):
            a.circle(x, y, r - 4, "a" if on else "s")
        if key:
            a.text(x, y + 4.5, key[-1], "ta" if on else "t", 13, "middle", 700, mono=True)
    a.text(40, 182, "root", "tm", 10.5, "middle")
    for w in completions:
        x, y = pos[w]
        a.text(x + r + 6, y + 4, w, "ta", 10.5, mono=True)
    for w in ("do", "dog"):
        x, y = pos[w]
        a.text(x, y + r + 15, w, "tm", 10.5, "middle", mono=True)

    rx = 432
    a.text(rx, 34, f"spell -p {prefix}", size=12, weight=700, mono=True)
    a.text(rx, 52, f"walk {', '.join(prefix)}, then list the", "tm", 10.5)
    a.text(rx, 67, "words below it:", "tm", 10.5)
    a.text(rx, 86, "  ".join(completions), "ta", 11.5, weight=600, mono=True)
    a.text(rx, 124, f"spell -s: '{typo}'", size=12, weight=700, mono=True)
    a.text(rx, 142, f"after '{typo[0]}' there is no '{typo[1]}' branch:", "tm", 10.5)
    a.text(rx, 157, "not in the dictionary", "tm", 10.5)
    a.text(rx, 176, f"{typo}: {near[0]}", "ta", 11.5, weight=600, mono=True)
    a.text(rx, 192, f"edit distance {best}: {typo[1]} -> {near[0][1]}", "tm", 10.5)
    b = BLOOM05
    a.text(rx, 222, "Bloom filter", size=12, weight=700)
    a.text(rx, 240, f"the same check in {b['bits'] / b['keys']:.1f} bits a word,", "tm", 10.5)
    a.text(rx, 255, f"{b['bytes'] // 1000} KB, {b['hashes']} hashes: its 'no' is always", "tm", 10.5)
    let = UNKNOWN05["trie"] - UNKNOWN05["bloom"]
    a.text(rx, 270, f"right; its 'maybe' let {let} of the book's", "tm", 10.5)
    a.text(rx, 285, f"{UNKNOWN05['trie']} misspellings through", "tm", 10.5)
    a.text(24, 284, "Double ring: a word ends here.", "tm", 10.5)
    return a


def check05(real):
    bad = []
    d = os.path.join(real.tmp, "six.txt")
    with open(d, "w") as f:
        f.write("".join(w + "\n" for w in WORDS05))
    out, _ = real.run(["bin/spell", "-d", d, "-p", PREFIX05])
    if out.split() != sorted(w for w in WORDS05 if w.startswith(PREFIX05)):
        bad.append(f"05: spell -p {PREFIX05}: {out!r}")
    best = min(lev(TYPO05, w) for w in WORDS05)
    near = sorted(w for w in WORDS05 if lev(TYPO05, w) == best)
    out, _ = real.run(["bin/spell", "-s", "-d", d], (TYPO05 + "\n").encode())
    if out != f"{TYPO05}: {' '.join(near)}\n":
        bad.append(f"05: spell -s: {out!r}")
    out, _ = real.run(["bin/spell", "--distance", TYPO05, near[0]])
    if out.strip() != str(best):
        bad.append(f"05: spell --distance: {out!r}")
    _, err = real.run(["bin/spell", "--algo=bloom", "data/book.txt"], stats=True)
    st = stats(err, "bloom")
    if {k: st[k] for k in BLOOM05} != BLOOM05:
        bad.append(f"05: bloom {st}")
    if stats(err, "spell")["unknown"] != UNKNOWN05["bloom"]:
        bad.append(f"05: spell --algo=bloom found {stats(err, 'spell')['unknown']} unknown")
    _, err = real.run(["bin/spell", "data/book.txt"], stats=True)
    if stats(err, "spell")["unknown"] != UNKNOWN05["trie"]:
        bad.append(f"05: spell found {stats(err, 'spell')['unknown']} unknown")
    return bad


# =================================================================== 06 diff

# The diff lessons' example (tools/diff/NOTES.md): lines 8-13 of the book, the contents I to VI, and
# a copy with II gone, "Mystery" made "Murder" in IV, and VII (line 14) added.
def lines06(book):
    old = book.split(b"\n")[7:13]
    new = [old[0], old[2], old[3].replace(b"Mystery", b"Murder"), old[4], old[5], book.split(b"\n")[13]]
    return [s.decode() for s in old], [s.decode() for s in new]


def lcs06(old, new):
    """lib/diff.c: L[i][j], the longest common subsequence of old from line i and new from line j,
    filled from the bottom right; then the walk from the top left, a delete first on a tie."""
    n, m = len(old), len(new)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            L[i][j] = L[i + 1][j + 1] + 1 if old[i] == new[j] else max(L[i + 1][j], L[i][j + 1])
    i = j = 0
    walk = [(0, 0)]
    edits = []
    while i < n or j < m:
        if i < n and j < m and old[i] == new[j]:
            edits.append((" ", old[i]))
            i, j = i + 1, j + 1
        elif j == m or (i < n and L[i + 1][j] >= L[i][j + 1]):
            edits.append(("-", old[i]))
            i += 1
        else:
            edits.append(("+", new[j]))
            j += 1
        walk.append((i, j))
    return L, walk, edits


def book06():
    with open(os.path.join(TRACK, "data", "book.txt"), "rb") as f:
        return f.read()


def cover06():
    a = Art("d06", "diff as dynamic programming: a table of the longest common subsequence of every pair of "
                   "the two files' ends, filled from the bottom right, and the walk from the top left that "
                   "becomes the edits")
    old, new = lines06(book06())
    L, walk, edits = lcs06(old, new)
    n, m = len(old), len(new)
    tag = lambda s: s.split()[0].rstrip(".")  # noqa: E731
    changed = [j for j, s in enumerate(new) if s not in old and tag(s) in [tag(o) for o in old]]
    assert len(changed) == 1
    cols = [tag(s) + ("*" if j in changed else "") for j, s in enumerate(new)]
    a.text(24, 26, "old: lines 8-13 of the book; new: II gone, IV changed, VII added", size=11.5, weight=600)
    x0, y0, cw, ch = 70, 58, 30, 21
    a.text(x0 + (m + 1) * cw / 2, y0 - 20, "new", "tm", 10, "middle")
    a.text(24, y0 + (n + 1) * ch / 2, "old", "tm", 10)
    for j in range(m):
        a.text(x0 + j * cw + cw / 2, y0 - 7, cols[j], "t", 10.5, "middle", 700, mono=True)
    on = set(walk)
    for i in range(n + 1):
        if i < n:
            a.text(x0 - 6, y0 + i * ch + 15, tag(old[i]), "t", 10.5, "end", 700, mono=True)
        for j in range(m + 1):
            hot = (i, j) in on
            a.add(f'<rect class="{"af" if hot else "f"}" x="{x0 + j * cw}" y="{y0 + i * ch}" width="{cw}" '
                  f'height="{ch}"/>')
            a.text(x0 + j * cw + cw / 2, y0 + i * ch + 15, str(L[i][j]), "ta" if hot else "tm", 11, "middle",
                   700 if hot else None, mono=True)
    for j in range(m + 2):
        a.line(x0 + j * cw, y0, x0 + j * cw, y0 + (n + 1) * ch, "m")
    for i in range(n + 2):
        a.line(x0, y0 + i * ch, x0 + (m + 1) * cw, y0 + i * ch, "m")
    a.box(x0, y0, (m + 1) * cw, (n + 1) * ch, "s", rx=0)
    bx, by = x0 + (m + 1) * cw, y0 + (n + 1) * ch
    a.path(f"M{bx + 8} {by - 4} C {bx + 14} {by - 40}, {bx + 4} {by - 70}, {bx + 6} {by - 96}", "m", arrow=True)
    a.text(bx + 4, by + 14, "filled from here", "tm", 10, "middle")

    dx = 316
    a.text(dx, 46, "the walk, as unified output", size=12, weight=700)
    a.text(dx, 64, f"@@ -1,{n} +1,{m} @@", "tm", 11, mono=True)
    for k, (op, s) in enumerate(edits):
        y = 81 + k * 15
        cls = "ta" if op == "+" else ("t" if op == "-" else "tm")
        if op != " ":
            a.text(dx, y, op, cls, 11, weight=700, mono=True)
        a.text(dx + 14, y, " ".join(s.split())[:44], cls, 11, weight=700 if op != " " else None, mono=True)
    yr = 238
    rules = [("diagonal", "the same line: keep it, +1"), ("down", "delete a line of old"),
             ("across", "insert a line of new")]
    for (h, t), x in zip(rules, (24, 250, 436)):
        a.text(x, yr, h, size=10.5, weight=700)
        a.text(x + 8 + len(h) * 6.2, yr, t, "tm", 10.5)
    nd = sum(op == "-" for op, _ in edits)
    ni = sum(op == "+" for op, _ in edits)
    a.text(dx, 81 + len(edits) * 15 + 6, f"{L[0][0]} lines in common: {nd} deleted, {ni} inserted", "ta", 11,
           weight=600)
    a.text(24, 270, "Cell (i, j): the longest common subsequence of old from line i on and new from line j on, "
                    "worked out from the cells", "tm", 11)
    a.text(24, 287, f"below and to the right. {cols[changed[0]]}: Mystery became Murder, a line that is not the "
                    "same, so a delete and an insert.", "tm", 11)
    return a


def check06(real):
    old, new = lines06(book06())
    L, walk, edits = lcs06(old, new)
    for name, lines in (("old.txt", old), ("new.txt", new)):
        with open(os.path.join(real.tmp, name), "w") as f:
            f.write("".join(s + "\n" for s in lines))
    out, err = real.run(["bin/diff", "--algo=table", os.path.join(real.tmp, "old.txt"),
                         os.path.join(real.tmp, "new.txt")], trace=True)
    bad = []
    rows = {int(i): v for i, v in re.findall(r"^trace: lcs: row (\d+): (.*)$", err, re.M)}
    for i, row in enumerate(L):
        if [int(c.rstrip("=")) for c in rows.get(i, "").split()] != row:
            bad.append(f"06: diff's row {i} is {rows.get(i)}, the model's {row}")
    at = [(int(i), int(j)) for i, j in re.findall(r"^trace: walk: at (\d+) (\d+),", err, re.M)]
    if at != walk[:-1]:
        bad.append(f"06: diff's walk {at}")
    body = [ln for ln in out.splitlines() if ln[:1] in " -+" and not ln.startswith(("---", "+++"))]
    if body != [op + s for op, s in edits]:
        bad.append(f"06: diff printed {body}")
    return bad


# =================================================================== 07 make

TOUCHED07 = "table.c"


def mini07():
    """figs07.MINI's rules: {target: [prerequisites]}, in order."""
    rules = {}
    for ln in figs07.MINI.splitlines():
        m = re.match(r"^([\w.]+):\s*(.*)$", ln)
        if m and m.group(1) != ".PHONY":
            rules[m.group(1)] = m.group(2).split()
    return rules


def build07(rules, touched):
    """What make does after touched changes: the targets out of date, in steps (a target starts
    once every prerequisite it has is done), and the targets checked and found up to date."""
    users = {}
    for t, deps in rules.items():
        for d in deps:
            users.setdefault(d, []).append(t)
    stale, todo = set(), [touched]
    while todo:
        for u in users.get(todo.pop(), []):
            if u not in stale:
                stale.add(u)
                todo.append(u)
    stale.discard("all")
    steps, left = [], set(stale)
    while left:
        ready = sorted(t for t in left if not (set(rules[t]) & left))
        steps.append(ready)
        left -= set(ready)
    fresh = sorted(t for t in rules if t not in stale and t != "all")
    return steps, fresh


def cover07():
    a = Art("d07", "make: the makefile is a graph; after an edit it rebuilds only what depends on the file "
                   "edited, each target after all it needs, and what is ready at once side by side")
    rules = mini07()
    steps, fresh = build07(rules, TOUCHED07)
    hot = {TOUCHED07} | {t for s in steps for t in s}
    a.text(24, 26, "the track's Makefile, cut down (07.01)", size=12, weight=700)
    lines = [f"{t}: {' '.join(d)}" for t, d in rules.items()]
    a.box(24, 36, 210, 14 * len(lines) + 10, "s fs", rx=8)
    for k, ln in enumerate(lines):
        a.text(36, 52 + k * 14, ln, size=10.5, mono=True)
    y = 36 + 14 * len(lines) + 30
    a.text(24, y, f"you edit {TOUCHED07}: make -j 2", "ta", 12, weight=700, mono=True)
    for k, s in enumerate(steps):
        a.text(24, y + 18 + k * 15, f"step {k + 1}", "tm", 10.5)
        a.text(76, y + 18 + k * 15, ", ".join(s) + (": at the same time" if len(s) > 1 else ""), size=10.5,
               mono=True)
    ys = y + 18 + len(steps) * 15 + 4
    a.text(24, ys, ", ".join(fresh[:-1]) + " and " + fresh[-1] + ": newer than", "tm", 10.5)
    a.text(24, ys + 15, "all they need, skipped", "tm", 10.5)

    srcs = ["freq.c", "util.c", "ds.h", "table.c", "sort.c"]
    objs = ["freq.o", "util.o", "table.o", "sort.o"]
    assert set(srcs) | set(objs) | {"libds.a", "freq", "sort", "all"} == set(rules) | {d for v in rules.values() for d in v}
    pos = {s: (300 + k * 76, 250) for k, s in enumerate(srcs)}
    pos.update({o: (318 + k * 90, 190) for k, o in enumerate(objs)})
    pos.update({"libds.a": (453, 134), "freq": (360, 82), "sort": (546, 82), "all": (453, 36)})
    nw, nh = 60, 24
    for t, deps in rules.items():
        for d in deps:
            (x1, y1), (x2, y2) = pos[d], pos[t]
            on = d in hot and t in hot
            a.line(round(x1 + (x2 - x1) * 0.12, 1), y1 - nh / 2, round(x2 + (x1 - x2) * 0.16, 1), y2 + nh / 2 + 2,
                   "a" if on else "m", arrow=True)
    step_of = {t: k + 1 for k, s in enumerate(steps) for t in s}
    for name, (x, y) in pos.items():
        on = name in hot
        cls = "a af" if on else ("s f" if name in srcs else "s fs")
        cell(a, x - nw / 2, y - nh / 2, nw, nh, name, cls, "ta" if on else "t", 11, rx=6, weight=700 if on else None)
        if name in step_of:
            a.text(x + nw / 2 + 6 if name != "freq" else x - nw / 2 - 6, y + 4, str(step_of[name]), "ta", 11,
                   "start" if name != "freq" else "end", 700)
    a.text(616, 290, "arrow: is needed to build", "tm", 10.5, "end")
    a.text(24, 290, "A depth-first search orders it; a cycle is an error.", "tm", 10.5)
    return a


def check07(real):
    rules = mini07()
    steps, fresh = build07(rules, TOUCHED07)
    d = os.path.join(real.tmp, "mini")
    os.makedirs(d)
    with open(os.path.join(d, "Makefile"), "w") as f:
        f.write(figs07.MINI)
    for s in ("freq.c", "sort.c", "util.c", "table.c", "ds.h"):
        open(os.path.join(d, s), "w").close()
    make = os.path.join(real.dir, "bin", "make")
    real.run([make, "-s"], cwd=d)
    t = os.stat(os.path.join(d, TOUCHED07)).st_mtime + 10
    os.utime(os.path.join(d, TOUCHED07), (t, t))
    _, err = real.run([make, "-j", "2"], cwd=d, trace=True, stats=True)
    bad = []
    started = re.findall(r"^trace: start (\S+)$", err, re.M)
    if [s for s in started if s != "all"] != [t for s in steps for t in s]:
        bad.append(f"07: make started {started}, the steps are {steps}")
    if sorted(re.findall(r"^trace: check (\S+): up to date$", err, re.M)) != fresh:
        bad.append(f"07: make found up to date {re.findall(r'check (\S+): up to date', err)}")
    if stats(err, "make")["most at once"] != max(len(s) for s in steps):
        bad.append(f"07: make ran at most {stats(err, 'make')['most at once']} at once")
    out, _ = real.run([make, "--graph"], cwd=d)
    got = {ln.split(":")[0]: ln.split(":")[1].split() for ln in out.splitlines() if not ln.startswith(".PHONY")}
    if {t: v for t, v in got.items() if v} != {t: v for t, v in rules.items() if v}:
        bad.append(f"07: make --graph {got}")
    return bad


# =================================================================== 08 route

POS08 = {"A": (52, 142), "B": (164, 68), "C": (164, 210), "D": (290, 142), "E": (300, 56), "F": (300, 220),
         "G": (420, 142)}
ROADS08 = [("A", "B", 5), ("A", "C", 2), ("A", "D", 12), ("B", "E", 4), ("B", "D", 4), ("C", "D", 6), ("C", "F", 3),
           ("D", "G", 6), ("E", "G", 7), ("F", "G", 5)]


def search08():
    """route's Dijkstra (ties to the smaller junction) and its breadth-first search, from A to G."""
    adj = {k: [] for k in POS08}
    for u, v, w in ROADS08:
        adj[u].append((v, w))
        adj[v].append((u, w))
    dist, prev, order, done = {"A": 0}, {}, [], set()
    heap = Heap(lambda x, y: x < y)
    heap.push((0, "A"))
    while heap.v:
        d, u = heap.pop()
        if u in done:
            continue
        done.add(u)
        order.append((u, d))
        if u == "G":
            break
        for v, w in adj[u]:
            if d + w < dist.get(v, 1e9):
                dist[v] = d + w
                prev[v] = u
                heap.push((d + w, v))
    best = ["G"]
    while best[-1] != "A":
        best.append(prev[best[-1]])
    best.reverse()
    bprev, q = {"A": None}, ["A"]
    while q:
        u = q.pop(0)
        for v, _ in sorted(adj[u]):
            if v not in bprev:
                bprev[v] = u
                q.append(v)
    few = ["G"]
    while bprev[few[-1]]:
        few.append(bprev[few[-1]])
    few.reverse()
    length = lambda p: sum(next(w for v, w in adj[x] if v == y) for x, y in zip(p, p[1:]))  # noqa: E731
    return adj, dist, order, best, few, length


def cover08():
    a = Art("d08", "Shortest paths on a road map: Dijkstra takes the nearest junction off a heap, again and "
                   "again, until it takes the goal")
    adj, dist, order, best, few, length = search08()
    pos = POS08
    on = set(zip(best, best[1:])) | set(zip(best[1:], best))
    r = 15
    lab_off = {("A", "B"): (-10, -6), ("A", "C"): (-10, 12), ("A", "D"): (0, -7), ("B", "E"): (0, -8),
               ("B", "D"): (10, -6), ("C", "D"): (10, 12), ("C", "F"): (0, 16), ("D", "G"): (0, -7),
               ("E", "G"): (10, -6), ("F", "G"): (10, 12)}
    for u, v, w in ROADS08:
        x1, y1, x2, y2 = toward(*pos[u], *pos[v], r, r)
        hot = (u, v) in on
        a.line(x1, y1, x2, y2, "a" if hot else "m")
        dx, dy = lab_off[(u, v)]
        mx, my = (pos[u][0] + pos[v][0]) / 2 + dx, (pos[u][1] + pos[v][1]) / 2 + dy
        a.text(round(mx, 1), round(my + 4, 1), str(w), "ta" if hot else "tm", 11, "middle", 700 if hot else None, mono=True)
    dpos = {"A": (0, -22), "B": (0, -22), "C": (0, 32), "D": (0, -22), "E": (0, -22), "F": (0, 32), "G": (0, -22)}
    for k, (x, y) in pos.items():
        hot = k in best
        node(a, x, y, k, r, "a af" if hot else "s f", "ta" if hot else "t", 12.5, 700, mono=False)
        ox, oy = dpos[k]
        a.text(x + ox, y + oy, str(dist[k]), "ta" if hot else "tm", 10.5, "middle", 600, mono=True)
    a.text(pos["A"][0], pos["A"][1] + r + 16, "start", "tm", 10.5, "middle")
    a.text(446, pos["G"][1] + 4, "goal", "tm", 10.5)
    px = 492
    a.text(px, 28, "off the heap, nearest first", size=12, weight=700)
    for k, (u, d) in enumerate(order):
        y = 50 + k * 17
        hot = u in best
        a.text(px, y, u, "ta" if hot else "t", 11.5, weight=700, mono=True)
        a.text(px + 18, y, str(d), "ta" if hot else "tm", 11.5, mono=True)
        if u == "G":
            a.text(px + 44, y, "goal: stop", "ta", 10.5)
    a.text(px, 192, "fewest roads (BFS)", "tm", 10.5)
    a.text(px, 208, f"{'-'.join(few)} = {length(few)}", size=11.5, mono=True)
    a.text(px, 232, "shortest (Dijkstra)", "ta", 10.5)
    a.text(px, 248, f"{'-'.join(best)} = {length(best)}", "ta", 11.5, weight=700, mono=True)
    a.text(24, 286, "Numbers on junctions: the distance from A. A* adds a guess of the distance left, so it "
                    "finishes fewer.", "tm", 11)
    return a


def check08(real):
    adj, dist, order, best, few, length = search08()
    names = list(POS08)
    path = os.path.join(real.tmp, "seven.map")
    with open(path, "w") as f:
        f.write(f"junctions {len(names)}\n" + "".join(f"{x} {y}\n" for x, y in POS08.values()))
        f.write(f"roads {len(ROADS08)}\n" + "".join(f"{names.index(u)} {names.index(v)} {w}\n" for u, v, w in ROADS08))
    bad = []
    for algo, want_order, route in (("dijkstra", order, best), ("bfs", None, few)):
        out, err = real.run(["bin/route", f"--algo={algo}", path, "0", str(names.index("G"))], trace=True)
        fin = [(names[int(j)], int(d)) for j, d in re.findall(rf"^trace: {algo}: finish (\d+) at (\d+)", err, re.M)]
        if want_order is not None and fin != want_order:
            bad.append(f"08: route --algo={algo} finished {fin}")
        m = re.search(r"^from \d+ to \d+: (\d+) metres", out, re.M)
        if not m or int(m.group(1)) != length(route):
            bad.append(f"08: route --algo={algo}: {out.splitlines()[:1]}")
        got = [names[int(ln.split()[1])] for ln in out.splitlines()[2:]]
        if got != route:
            bad.append(f"08: route --algo={algo} went {got}")
    return bad


# =================================================================== 09 gzip

TEXT09 = "abracadabra"


def huffman09():
    """huffman.c: the two lightest joined until one tree is left (ties to the leaf of the smaller
    byte, then the earlier join); a byte's length is its depth, and the codes are numbered from the
    lengths, in byte order (RFC 1951 3.2.2), as gzip --huffman prints them."""
    counts = {}
    for c in TEXT09:
        counts[c] = counts.get(c, 0) + 1
    h = Heap(lambda x, y: (x[0], x[1]) < (y[0], y[1]))
    for c in sorted(counts):
        h.push((counts[c], ord(c), c))
    joins = []
    while len(h.v) > 1:
        x, y = h.pop(), h.pop()
        t = (x[2], y[2])
        joins.append((x, y, x[0] + y[0], t))
        h.push((x[0] + y[0], 1000 + len(joins), t))
    root = h.v[0][2]
    lengths = {}

    def depth(t, k):
        if isinstance(t, str):
            lengths[t] = k
        else:
            depth(t[0], k + 1)
            depth(t[1], k + 1)
    depth(root, 0)
    code, codes = 0, {}
    for k, c in enumerate(sorted(counts, key=lambda c: (lengths[c], c))):
        if k:
            prev = sorted(counts, key=lambda c: (lengths[c], c))[k - 1]
            code = (code + 1) << (lengths[c] - lengths[prev])
        codes[c] = format(code, f"0{lengths[c]}b")
    return counts, joins, root, lengths, codes


def lz77_09():
    """The one repeat lz77.c finds: (position, distance, length), the longest earlier copy of at
    least 3 bytes."""
    best = None
    for p in range(len(TEXT09)):
        for s in range(p):
            k = 0
            while p + k < len(TEXT09) and TEXT09[s + k] == TEXT09[p + k]:
                k += 1
            if k >= 3 and (best is None or k > best[2]):
                best = (p, p - s, k)
        if best:
            return best


def cover09():
    a = Art("d09", "Huffman's greedy tree gives common bytes short codes; LZ77 writes a repeat as a pointer back "
                   "to its earlier copy")
    counts, joins, root, lengths, codes = huffman09()
    bits = sum(len(codes[c]) for c in TEXT09)
    a.text(24, 30, "printf abracadabra | bin/gzip --huffman", size=11.5, weight=600, mono=True)
    a.text(24, 64, "byte", "tm", 10)
    a.text(96, 64, "count", "tm", 10, "end")
    a.text(134, 64, "bits", "tm", 10, "end")
    a.text(148, 64, "code", "tm", 10)
    for k, c in enumerate(sorted(counts)):
        y = 84 + k * 18
        a.text(30, y, f"'{c}'", size=12, weight=700, mono=True)
        a.text(90, y, str(counts[c]), "tm", 12, "end", mono=True)
        a.text(128, y, str(lengths[c]), "tm", 12, "end", mono=True)
        a.text(148, y, codes[c], "ta", 12, weight=600, mono=True)
    a.text(24, 190, "the tree gives each byte its length;", "tm", 10.5)
    a.text(24, 205, "the codes are then numbered in order", "tm", 10.5)

    xs, ys, leaves = {}, {}, []
    jn = {id(t): k + 1 for k, (_, _, _, t) in enumerate(joins)}

    def place(t, d):
        ys[id(t)] = 50 + d * 52
        if isinstance(t, str):
            leaves.append(t)
            xs[id(t)] = 262 + (len(leaves) - 1) * 50
        else:
            place(t[0], d + 1)
            place(t[1], d + 1)
            xs[id(t)] = (xs[id(t[0])] + xs[id(t[1])]) / 2

    def weight(t):
        return counts[t] if isinstance(t, str) else weight(t[0]) + weight(t[1])
    place(root, 0)

    def draw(t):
        x, y = xs[id(t)], ys[id(t)]
        if isinstance(t, str):
            cell(a, x - 19, y - 14, 38, 28, f"{t} {counts[t]}", "s fs", "t", 12, rx=6, weight=700)
            return
        for ch in t:
            cx, cy = xs[id(ch)], ys[id(ch)]
            x1, y1, x2, y2 = toward(x, y, cx, cy, 14, 16 if isinstance(ch, str) else 14)
            a.line(x1, y1, x2, y2, "s")
            draw(ch)
        node(a, x, y, str(weight(t)), 14, "s f", "t", 11, 600)
        a.text(x + 18, y - 10, f"n{jn[id(t)]}", "tm", 9.5, mono=True)
    draw(root)
    mx = 486
    a.text(mx, 30, "join the two lightest,", size=11.5, weight=700)
    a.text(mx, 45, "until one tree is left", size=11.5, weight=700)

    def nm(x):
        return f"'{x[2]}'" if isinstance(x[2], str) else f"n{x[1] - 1000}"
    for k, (x, y, s, _) in enumerate(joins):
        a.text(mx, 70 + k * 18, f"{nm(x)} {x[0]} + {nm(y)} {y[0]} = n{k + 1} {s}", size=11, mono=True)
    a.text(mx, 168, f"{bits} bits instead of", "ta", 11.5, weight=700)
    a.text(mx, 184, f"{8 * len(TEXT09)} as bytes", "ta", 11.5, weight=700)

    p, dist, length = lz77_09()
    a.text(24, 252, "LZ77", size=12, weight=700)
    a.add(f'<text class="t mono" x="72" y="252" font-size="12">{esc(TEXT09[:p])}'
          f'<tspan class="ta" font-weight="700">[distance {dist}, length {length}]</tspan></text>')
    a.text(372, 252, f"the second '{TEXT09[p:p + length]}' points at the first", "tm", 10.5)
    a.text(24, 282, "DEFLATE does both: LZ77 finds the repeats, then Huffman codes what is left.", "tm", 11)
    return a


def check09(real):
    counts, joins, root, lengths, codes = huffman09()
    out, err = real.run(["bin/gzip", "--huffman"], TEXT09.encode(), trace=True)
    bad = []
    rows = {c: (int(n), int(b), code) for c, n, b, code in re.findall(r"^'(.)'\s+(\d+)\s+(\d+)\s+([01]+)$", out, re.M)}
    if rows != {c: (counts[c], lengths[c], codes[c]) for c in counts}:
        bad.append(f"09: gzip --huffman: {rows}")
    js = re.findall(r"^trace: huffman: join .* = n\d+ (\d+)$", err, re.M)
    if [int(s) for s in js] != [s for _, _, s, _ in joins]:
        bad.append(f"09: gzip's joins {js}")
    _, err = real.run(["bin/gzip", "--lz77"], TEXT09.encode(), trace=True)
    p, dist, length = lz77_09()
    m = re.findall(r"^trace: lz77: (\d+): match distance (\d+) length (\d+)", err, re.M)
    if [tuple(map(int, t)) for t in m] != [(p, dist, length)]:
        bad.append(f"09: gzip --lz77 matches {m}")
    return bad


# =================================================================== 10 git

WHO10 = "Ada <ada@example.com>"


def git_id(kind, body):
    return hashlib.sha1(f"{kind} {len(body)}\0".encode() + body).hexdigest()


def objects10():
    main_c = git_id("blob", b"int main(void) { return 0; }\n")
    r1 = git_id("blob", b"hello\n")
    r2 = git_id("blob", b"hello, world\n")

    def entry(mode, name, h):
        return f"{mode} {name}\0".encode() + bytes.fromhex(h)
    src = git_id("tree", entry("100644", "main.c", main_c))
    t1 = git_id("tree", entry("100644", "README", r1) + entry("40000", "src", src))
    t2 = git_id("tree", entry("100644", "README", r2) + entry("40000", "src", src))
    c1 = git_id("commit", f"tree {t1}\nauthor {WHO10} 1700000000 +0000\ncommitter {WHO10} 1700000000 +0000\n\nfirst\n".encode())
    c2 = git_id("commit", f"tree {t2}\nparent {c1}\nauthor {WHO10} 1700000600 +0000\n"
                          f"committer {WHO10} 1700000600 +0000\n\nsay hello, world\n".encode())
    return {"mc": main_c, "r1": r1, "r2": r2, "src": src, "t1": t1, "t2": t2, "c1": c1, "c2": c2}


def cover10():
    a = Art("d10", "git's object graph: commits point at trees, trees at blobs and trees, each named by the "
                   "SHA-1 of its content")
    ids = objects10()
    bw, bh = 120, 42
    objs = {
        "c2": (24, 48, "commit", '"say hello, world"'), "c1": (24, 180, "commit", '"first"'),
        "t2": (184, 48, "tree", "README, src/"), "t1": (184, 180, "tree", "README, src/"),
        "r2": (344, 22, "blob", '"hello, world\\n"'), "src": (344, 114, "tree", "main.c"),
        "r1": (344, 206, "blob", '"hello\\n"'), "mc": (496, 114, "blob", "int main(void)..."),
    }
    shared = {"src", "mc"}
    for key, (x, y, kind, sub) in objs.items():
        foc = key in shared
        a.box(x, y, bw, bh, "a af" if foc else ("s fs" if kind == "commit" else "s f"), rx=8)
        a.add(f'<text class="{"ta" if foc else "t"} mono" x="{x + 10}" y="{y + 17}" font-size="11.5">'
              f'<tspan font-weight="700">{kind}</tspan> {ids[key][:7]}</text>')
        a.text(x + 10, y + 33, sub, "ta" if foc else "tm", 10, mono=kind == "blob")

    def arrow(f, t, cls="s", fy=None, ty=None):
        (fx0, fy0), (tx0, ty0) = objs[f][:2], objs[t][:2]
        x1, y1 = fx0 + bw, fy if fy is not None else fy0 + bh / 2
        x2, y2 = tx0 - 2, ty if ty is not None else ty0 + bh / 2
        a.path(f"M{x1} {y1} C {x1 + 20} {y1}, {x2 - 20} {y2}, {x2} {y2}", cls, arrow=True)
    arrow("c2", "t2")
    arrow("c1", "t1")
    arrow("t2", "r2", fy=60)
    arrow("t2", "src", "a", fy=80, ty=130)
    arrow("t1", "src", "a", fy=188, ty=144)
    arrow("t1", "r1", fy=212)
    arrow("src", "mc", "a")
    a.line(84, 90, 84, 178, "s", arrow=True)
    a.text(94, 128, "parent", "tm", 10.5)
    a.text(94, 143, "git log", "tm", 10.5)
    a.text(94, 158, "walks these", "tm", 10.5)
    a.box(24, 12, 46, 22, "s", rx=11)
    a.text(47, 27, "main", size=11, anchor="middle", weight=700, mono=True)
    a.line(47, 34, 47, 46, "s", arrow=True)
    a.text(556, 196, "src/ did not change:", "ta", 10.5, "middle", 600)
    a.text(556, 211, "both trees name it", "ta", 10.5, "middle")
    a.text(556, 226, "by the same hash", "ta", 10.5, "middle")
    a.text(24, 270, "An object is named by the SHA-1 of its content: what did not change keeps its name and is "
                    "stored once,", "tm", 11)
    a.text(24, 286, "and a change renames every object above it, up to the commit. This git and the real one "
                    "give these same ids.", "tm", 11)
    return a


def check10(real):
    ids = objects10()
    d = os.path.join(real.tmp, "repo")
    os.makedirs(os.path.join(d, "src"))
    with open(os.path.join(d, "src", "main.c"), "w") as f:
        f.write("int main(void) { return 0; }\n")
    with open(os.path.join(d, "README"), "w") as f:
        f.write("hello\n")
    tool = os.path.join(real.dir, "bin", "git")
    name, email = WHO10[:-1].split(" <")
    env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": name,
           "GIT_COMMITTER_EMAIL": email}
    real.run([tool, "init"], cwd=d)
    real.run([tool, "add", "README", "src/main.c"], cwd=d)
    when = {"GIT_AUTHOR_DATE": "1700000000 +0000", "GIT_COMMITTER_DATE": "1700000000 +0000"}
    real.run([tool, "commit", "-m", "first"], cwd=d, env=dict(env, **when))
    with open(os.path.join(d, "README"), "w") as f:
        f.write("hello, world\n")
    real.run([tool, "add", "README"], cwd=d)
    when = {"GIT_AUTHOR_DATE": "1700000600 +0000", "GIT_COMMITTER_DATE": "1700000600 +0000"}
    real.run([tool, "commit", "-m", "say hello, world"], cwd=d, env=dict(env, **when))
    def show(spec):
        out, _ = real.run([tool, "cat-file", "-p", spec], cwd=d)
        return {m.group(2): m.group(1) for m in re.finditer(r"([0-9a-f]{40})\s+(\S+)$", out, re.M)} | \
               {m.group(1): m.group(2) for m in re.finditer(r"^(tree|parent) ([0-9a-f]{40})$", out, re.M)}
    out, _ = real.run([tool, "log"], cwd=d)
    head, first = show("HEAD"), show("HEAD~1")
    got = {"c2": re.match(r"commit ([0-9a-f]{40})", out).group(1), "c1": head.get("parent"),
           "t2": head.get("tree"), "t1": first.get("tree")}
    now, then = show("HEAD^{tree}"), show("HEAD~1^{tree}")
    got.update({"r2": now.get("README"), "r1": then.get("README"), "src": now.get("src")})
    got["mc"] = show(got["src"]).get("main.c") if got["src"] else None
    if then.get("src") != got["src"]:
        got["src"] = f"{got['src']} and {then.get('src')}"
    return [f"10: {k} is {got[k]!r} in this git, {v} on the cover" for k, v in ids.items() if got[k] != v]


# =================================================================== the track's own art

def track_art():
    """The home page card, 280x160: a heap drawn as a tree and as the array that stores it, the
    children of i at 2i+1 and 2i+2 as lib/heap.c keeps them."""
    sw = 'stroke-width="1.5"'
    vals = [2, 5, 3, 9, 7, 8, 4]
    assert all(vals[i] <= vals[c] for i in range(7) for c in (2 * i + 1, 2 * i + 2) if c < 7)
    hot = [0, 2, 6]
    pts = [(140, 22), (92, 56), (188, 56), (68, 90), (116, 90), (164, 90), (212, 90)]
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 160">']
    for c in range(1, 7):
        p = (c - 1) // 2
        x1, y1, x2, y2 = toward(*pts[p], *pts[c], 10, 10)
        if not (p in hot and c in hot):
            out.append(f'<path class="m" d="M{x1} {y1}L{x2} {y2}" {sw} stroke-linecap="round"/>')
    for i, (x, y) in enumerate(pts):
        cls = "a af" if i in hot else "s f"
        out.append(f'<circle class="{cls}" cx="{x}" cy="{y}" r="10" stroke-width="1.75"/>')
        out.append(f'<text class="{"ta" if i in hot else "t"} mono" x="{x}" y="{y + 3.5}" font-size="10" '
                   f'text-anchor="middle" font-weight="600">{vals[i]}</text>')
    seg = []
    for p, c in zip(hot, hot[1:]):
        x1, y1, x2, y2 = toward(*pts[p], *pts[c], 10, 10)
        seg.append(f"M{x1} {y1}L{x2} {y2}")
    out.append(f'<path class="a draw" d="{"".join(seg)}" pathLength="1" stroke-width="2.25" stroke-linecap="round"/>')
    cw, x0, y0 = 24, 56, 118
    for i, v in enumerate(vals):
        x = x0 + i * cw
        cls = "a af" if i in hot else "s f"
        out.append(f'<rect class="{cls}" x="{x}" y="{y0}" width="{cw}" height="20" rx="2" stroke-width="1.5"/>')
        out.append(f'<text class="{"ta" if i in hot else "t"} mono" x="{x + cw / 2}" y="{y0 + 14}" font-size="10" '
                   f'text-anchor="middle" font-weight="600">{v}</text>')
        out.append(f'<text class="tm mono" x="{x + cw / 2}" y="{y0 + 33}" font-size="7.5" text-anchor="middle">{i}</text>')
    out.append(f'<text class="tm mono" x="{x0 - 6}" y="{y0 + 14}" font-size="8" text-anchor="end">a[]</text>')
    out.append(f'<text class="tm mono" x="{x0 + 7 * cw + 6}" y="{y0 + 14}" font-size="8">children of i:</text>')
    out.append(f'<text class="tm mono" x="{x0 + 7 * cw + 6}" y="{y0 + 25}" font-size="8">2i+1, 2i+2</text>')
    out.append("</svg>\n")
    return "\n".join(out)


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{}</svg>\n')

TRACK_ICON = ('<rect x="7.5" y="2.5" width="5" height="5" rx="1"/><rect x="2.5" y="12.5" width="5" height="5" rx="1"/>'
              '<rect x="12.5" y="12.5" width="5" height="5" rx="1"/><path d="M8.75 7.5L6.25 12.5M11.25 7.5l2.5 5"/>')

MODULES = {
    "00": (cover00, check00, '<path d="M3 3v14h14"/><path d="M6 14.5c4.5 0 7.5-3.5 9.5-10"/>'
                             '<path d="M6 14.5h.01M11.7 11.9h.01M15.5 4.5h.01" stroke-width="2.6"/>'),
    "01": (cover01, check01, '<rect x="9.5" y="2.5" width="8" height="15" rx="1.5"/><path d="M9.5 6.25h8M9.5 10h8M9.5 13.75h8"/>'
                             '<path d="M2.5 11.9h4.5M5.25 10.15l1.75 1.75-1.75 1.75"/>'),
    "02": (cover02, check02, '<path d="M4 16.5v-2M8 16.5v-5M12 16.5v-8M16 16.5V3.5" stroke-width="2.25"/>'),
    "03": (cover03, check03, '<path d="M2.5 5h7M2.5 10h4.5M2.5 15h7"/><path d="M13.5 3.5v13M11.75 3.5h3.5M11.75 16.5h3.5"/>'),
    "04": (cover04, check04, '<circle cx="5" cy="11" r="2.75"/><circle cx="15" cy="11" r="2.75"/><circle cx="15" cy="11" r="1"/>'
                             '<path d="M7.75 11h4.25M10.5 9.5l1.5 1.5-1.5 1.5"/><path d="M3.4 8.75C2.6 4.75 7.4 4.75 6.6 8.75"/>'),
    "05": (cover05, check05, '<circle cx="10" cy="3.75" r="1.75"/><circle cx="5.5" cy="10" r="1.75"/><circle cx="14.5" cy="10" r="1.75"/>'
                             '<circle cx="3" cy="16.25" r="1.75"/><circle cx="8" cy="16.25" r="1.75"/>'
                             '<path d="M9 5.2l-2.5 3.4M11 5.2l2.5 3.4M4.8 11.6l-1.1 3M6.2 11.6l1.1 3"/>'),
    "06": (cover06, check06, '<path d="M10 3.5v7M6.5 7h7M6.5 15.5h7"/>'),
    "07": (cover07, check07, '<circle cx="10" cy="3.75" r="1.75"/><circle cx="4.5" cy="10" r="1.75"/><circle cx="15.5" cy="10" r="1.75"/>'
                             '<circle cx="10" cy="16.25" r="1.75"/><path d="M8.8 5.1l-3.1 3.5M11.2 5.1l3.1 3.5M5.7 11.4l3.1 3.5M14.3 11.4l-3.1 3.5"/>'),
    "08": (cover08, check08, '<circle cx="4.5" cy="15.5" r="2"/><circle cx="15.5" cy="4.5" r="2"/>'
                             '<path d="M6.5 15.5H11a2.5 2.5 0 000-5H9a2.5 2.5 0 010-5h4.5"/>'),
    "09": (cover09, check09, '<path d="M10 2.5v5M7.5 5l2.5 2.5L12.5 5M10 17.5v-5M7.5 15l2.5-2.5 2.5 2.5M3 10h14"/>'),
    "10": (cover10, check10, '<circle cx="6" cy="4.5" r="2"/><circle cx="6" cy="15.5" r="2"/><circle cx="14" cy="6.5" r="2"/>'
                             '<path d="M6 6.5v7M14 8.5c0 3.5-8 2.5-8 5"/>'),
}


# =================================================================== writing and checking

def module_dirs():
    """{"02": ".../tracks/dsa/lessons/02-sort", ...}"""
    out = {}
    for name in sorted(os.listdir(LESSONS)):
        m = re.match(r"^(\d\d)-", name)
        if m and os.path.isdir(os.path.join(LESSONS, name)):
            out[m.group(1)] = os.path.join(LESSONS, name)
    return out


def files():
    """{path: svg text} for every file this script owns."""
    out = {os.path.join(TRACK, "art.svg"): track_art(), os.path.join(TRACK, "icon.svg"): ICON.format(TRACK_ICON)}
    dirs = module_dirs()
    assert set(dirs) == set(MODULES), (sorted(dirs), sorted(MODULES))
    for mid, (cover, _, icon) in MODULES.items():
        out[os.path.join(dirs[mid], "cover.svg")] = cover().svg()
        out[os.path.join(dirs[mid], "icon.svg")] = ICON.format(icon)
    return out


def check_svg(out):
    """Each file must be ASCII and come through the site's sanitizer with every element kept."""
    sys.dont_write_bytecode = True        # read harness/, never write into it
    sys.path.insert(0, ROOT)
    from harness.web.art import sanitize
    bad = []
    for path, text in out.items():
        rel = os.path.relpath(path, ROOT)
        if not text.isascii():
            bad.append(f"{rel}: not ASCII")
        clean = sanitize(text, "x")
        if not clean:
            bad.append(f"{rel}: rejected by sanitize")
        elif clean.count("<") - clean.count("</") != text.count("<") - text.count("</"):
            bad.append(f"{rel}: sanitize dropped an element")
    return bad


class Real:
    """The finished project as ./learn files writes it, built, to run the real tools in."""

    def __init__(self):
        last = max(m.group(1) for d in module_dirs().values() for f in os.listdir(d)
                   for m in [re.match(r"^(\d\d\.\d\d)-.*\.md$", f)] if m)
        self.tmp = tempfile.mkdtemp(prefix="dsa-covers-")
        self.dir = os.path.join(self.tmp, "project")
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", last, self.dir], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["make", "-s", "-j8"], cwd=self.dir, check=True, stdout=subprocess.DEVNULL)

    def run(self, argv, data=b"", cwd=None, env=None, stats=False, trace=False, ok=(0, 1)):
        e = {k: v for k, v in os.environ.items() if k not in ("DS_STATS", "DS_TRACE") and not k.startswith("GIT_")}
        e["LC_ALL"] = "C"
        if stats:
            e["DS_STATS"] = "1"
        if trace:
            e["DS_TRACE"] = "1"
        e.update(env or {})
        r = subprocess.run(argv, input=data, capture_output=True, cwd=cwd or self.dir, env=e)
        if r.returncode not in ok:
            raise RuntimeError(f"{' '.join(argv)}: exit {r.returncode}: {r.stderr.decode()[-400:]}")
        return r.stdout.decode(), r.stderr.decode()

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def main(argv):
    if argv not in ([], ["--quick"]):
        print(__doc__.strip().split("\n\n")[1])
        return 2
    out = files()
    for path, text in out.items():
        with open(path, "w") as f:
            f.write(text)
        print(os.path.relpath(path, ROOT))
    bad = check_svg(out)
    if not argv:
        real = Real()
        try:
            for mid, (_, check, _) in MODULES.items():
                bad += check(real)
        finally:
            real.close()
        print("checked every cover against the real programs" if not bad else "")
    for b in bad:
        print("problem:", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
