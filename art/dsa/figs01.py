"""Figures for dsa module 01, Counting words: freq (lessons 01.01 to 01.03).

    python3 art/dsa/figs01.py

Each figure is drawn from a model of the few lines of lib/ and tools/freq/ it shows (the
array's push, the table's find, put and grow, the two hashes), and the script asserts that
the model's counts equal what the real bin/freq prints with DS_STATS=1 on the same input:
the project at the lesson is written with ./learn files and built first.

  01.01-doubling   freq's words array over the book's first 9 lines (up to "The Red-Headed
                   League"), and over the whole book: 7818 words, 11 grows, 8184 moves
  01.02-chain      printf 'the cat sat on the mat, the act\\n' | DS_STATS=1 bin/freq
                   -> stats: table: lookups 14, probes 4, inserts 6, resizes 0, moves 0
  01.03-resize     the book at 01.03: the first grow, at the 1025th different word, seen
                   through one old bucket; the whole book: resizes 3, moves 7168
  01.03-spread     where the book's 7818 words land in 8192 buckets, by sum and by FNV-1a
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
MOD = "01-freq"
BOOK = os.path.join(ROOT, "tracks", "dsa", "data", "book.txt")
M64 = (1 << 64) - 1

_built = {}


def project(at):
    if at not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="dsa-figs-"), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["make", "-s"], cwd=d, check=True)
        _built[at] = d
    return _built[at]


def stats(at, args, data):
    d = project(at)
    env = dict(os.environ, DS_STATS="1", LC_ALL="C")
    r = subprocess.run([os.path.join(d, "bin", "freq")] + args, input=data, cwd=d, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    out = {}
    for m in re.finditer(r"^stats: ([^:]+): (.*)$", r.stderr.decode(), re.M):
        out[m.group(1)] = {k: int(v) for k, v in (p.rsplit(" ", 1) for p in m.group(2).split(", "))}
    return out


def words_of(data):
    """next_word(): runs of A-Za-z, lowercased."""
    return [w.lower().decode() for w in re.findall(rb"[A-Za-z]+", data)]


class Arr:
    """lib/array.c's array_push: 8 to start, then twice the room; counts as DS_STATS does."""

    def __init__(self, st):
        self.len, self.cap, self.st = 0, 0, st

    def push(self):
        grew = None
        if self.len == self.cap:
            cap = 2 * self.cap if self.cap else 8
            grew = (self.cap, cap, self.len)
            self.st["grows"] += 1
            self.st["moves"] += self.len
            self.cap = cap
        self.st["pushes"] += 1
        self.len += 1
        return grew


def hash_sum(w):
    return sum(w.encode())


def hash_fnv1a(w):
    h = 14695981039346656037
    for c in w.encode():
        h ^= c
        h = (h * 1099511628211) & M64
    return h


class Table:
    """lib/table.c: chains through an entries array, new entries at the head of their bucket."""

    def __init__(self, hash_fn, grow, arr_st):
        self.hash, self.can_grow = hash_fn, grow
        self.nb = 1024
        self.buckets = [-1] * self.nb
        self.keys, self.hashes, self.next = [], [], []
        self.entries = Arr(arr_st)
        self.st = dict(lookups=0, probes=0, inserts=0, resizes=0, moves=0)
        self.on_grow = None

    def find(self, w, h, walk=None):
        self.st["lookups"] += 1
        i = self.buckets[h & (self.nb - 1)]
        while i >= 0:
            self.st["probes"] += 1
            if walk is not None:
                walk.append(i)
            if self.hashes[i] == h and self.keys[i] == w:
                return i
            i = self.next[i]
        return -1

    def get(self, w, walk=None):
        return self.find(w, self.hash(w), walk)

    def grow(self):
        if self.on_grow:
            self.on_grow(self)
        self.nb *= 2
        self.buckets = [-1] * self.nb
        for i, h in enumerate(self.hashes):
            b = h & (self.nb - 1)
            self.next[i] = self.buckets[b]
            self.buckets[b] = i
        self.st["resizes"] += 1
        self.st["moves"] += len(self.keys)

    def put(self, w, walk=None):
        h = self.hash(w)
        i = self.find(w, h, walk)
        if i >= 0:
            return i
        if self.can_grow and len(self.keys) >= self.nb:
            self.grow()
        b = h & (self.nb - 1)
        self.entries.push()
        self.keys.append(w)
        self.hashes.append(h)
        self.next.append(self.buckets[b])
        self.buckets[b] = len(self.keys) - 1
        self.st["inserts"] += 1
        return len(self.keys) - 1

    def chain(self, b):
        out, i = [], self.buckets[b]
        while i >= 0:
            out.append(i)
            i = self.next[i]
        return out


def count(data, table=None, on_word=None):
    """freq's main loop: buf (an Array of char) and words (an Array of Word); count_list, or
    count_table with table. Returns (distinct words in order, counts, array stats)."""
    ast = dict(pushes=0, grows=0, moves=0)
    buf, words = Arr(ast), Arr(ast)
    order, counts = [], {}
    if table is not None:
        table.entries.st = ast
    for w in words_of(data):
        buf.len = 0
        for _ in w:
            buf.push()
        if w in counts:
            counts[w] += 1
            if table is not None:
                table.get(w)
            if on_word:
                on_word(w, None, words)
            continue
        if table is not None:
            table.get(w)
            table.put(w)
        counts[w] = 1
        order.append(w)
        grew = words.push()
        if on_word:
            on_word(w, grew, words)
    return order, counts, ast


# ------------------------------------------------------------------ 01.01

def doubling0101():
    book = open(BOOK, "rb").read()
    head = b"".join(book.splitlines(keepends=True)[:9])
    frames = []
    wst = dict(pushes=0, grows=0, moves=0)
    order = []

    def on_word(w, grew, words):
        if grew is None and w in order:
            return
        order.append(w)
        wst["pushes"] += 1
        if grew:
            wst["grows"] += 1
            wst["moves"] += grew[2]
        n = len(order)
        if grew or n == words.cap:
            frames.append((list(order), words.cap, grew, dict(wst)))

    order_h, _, ast = count(head, on_word=on_word)
    real = stats("01.01", [], head)
    assert real["array"] == ast and real["freq"]["distinct"] == len(order_h), (real, ast)
    _, _, ast_b = count(book)
    real_b = stats("01.01", [], book)
    assert real_b["array"] == ast_b, (real_b, ast_b)
    # the words array alone, over the whole book
    whole = dict(pushes=0, grows=0, moves=0)
    wa = Arr(whole)
    for _ in range(real_b["freq"]["distinct"]):
        wa.push()
    print("01.01 words array over the book:", whole, "cap", wa.cap, "| both arrays:", ast_b)
    frames = [fr for fr in frames if len(fr[0]) <= 17]

    f = Fig("f0101a", "freq's array of words filling up as the first lines of the book are read: when it is "
            "full it moves to a block twice as big", 300)
    f.text(24, 22, "the words array of bin/freq data/book.txt: one push for each different word", "tm", 10.5)
    CW, CH, X0 = 70, 22, 50

    def grid(y, cap, words, style):
        """cap slots, 8 to a row, from y; style(i) -> (box class, text class) for slot i."""
        for i in range(cap):
            r, c = divmod(i, 8)
            x, yy = X0 + c * (CW + 2), y + r * (CH + 3)
            if c == 0:
                f.text(X0 - 8, yy + 15, str(i), "tm", 9.5, "end", mono=True)
            if i < len(words):
                bc, tc = style(i)
                f.rect(x, yy, CW, CH, bc, 3)
                f.text(x + CW / 2, yy + 15, words[i], tc, 11 if len(words[i]) <= 8 else 10, "middle",
                       600 if tc == "f" else None, mono=True)
            else:
                f.rect(x, yy, CW, CH, "m f", 3, dash=True)
        return y + ((cap + 7) // 8) * (CH + 3)

    for ws, cap, grew, st in frames:
        n, w = len(ws), ws[-1]
        if n == 1:
            cap_text = f"\"{w}\": the array is empty and has no block yet, so the push first takes one of 8 slots."
        elif grew:
            cap_text = (f"\"{w}\", the {n}th different word, finds the block full: a new block of {cap}, "
                        f"the {grew[2]} words copied across, the old one freed.")
        else:
            cap_text = f"\"{w}\" is the {n}th different word: the block of {cap} is full."
        with steps.step(f, cap_text):
            f.text(24, 52, f"len {n}, cap {cap}", "t", 12, weight=600, mono=True)
            f.text(616, 52, f"pushes {st['pushes']}, grows {st['grows']}, moves {st['moves']}", "ta", 11.5,
                   "end", 600, mono=True)
            y = 70
            if grew and grew[0]:
                f.text(24, y + 10, f"old block, {grew[0]} slots: freed", "tm", 10.5)
                y = grid(y + 18, grew[0], ws[:-1], lambda i: ("m fs", "tm"))
                f.text(24, y + 14, f"copied, one memcpy() of {grew[2]} words", "ta", 10.5)
                y += 22
            label = f"block of {cap} slots" + (" (new)" if grew else "")
            f.text(24, y + 10, label, "t", 10.5, weight=600)
            last = n - 1

            def style(i, moved=grew[2] if grew else 0, last=last):
                if i == last:
                    return "a fa", "f"
                if i < moved:
                    return "a af", "ta"
                return "s f", "t"
            grid(y + 18, cap, ws, style)
    with steps.step(f, f"The whole book: {real_b['freq']['distinct']} different words of "
                       f"{real_b['freq']['words']}, in a block of {wa.cap}. {whole['grows']} grows copied "
                       f"{whole['moves']} words in all: fewer copies than words."):
        f.text(24, 52, f"len {real_b['freq']['distinct']}, cap {wa.cap}", "t", 12, weight=600, mono=True)
        f.text(616, 52, f"pushes {whole['pushes']}, grows {whole['grows']}, moves {whole['moves']}", "ta", 11.5,
               "end", 600, mono=True)
        caps, moved = [], 0
        c = 8
        while c <= wa.cap:
            caps.append(c)
            c *= 2
        # one bar per block the array has had, its width to scale
        top = caps[-1]
        y = 84
        for c in caps:
            w = max(3.0, 520 * c / top)
            f.rect(X0 + 40, y, round(w, 1), 12, "a af" if c != top else "a fa", 2)
            f.text(X0 + 32, y + 10, str(c), "tm", 10, "end", mono=True)
            y += 15
        f.text(X0 + 40, y + 16, "each block in turn, to scale: every grow copies what the last block held", "tm",
               10.5)
    return f


# ------------------------------------------------------------------ 01.02

def chain0102():
    text = b"the cat sat on the mat, the act\n"
    ast = dict(pushes=0, grows=0, moves=0)
    t = Table(hash_sum, False, ast)
    frames = []
    seen = []
    for w in words_of(text):
        walk = []
        i = t.get(w, walk)
        if i < 0:
            t.put(w, walk)
        frames.append((w, list(walk), i, dict(t.st), {b: t.chain(b) for b in range(t.nb) if t.buckets[b] >= 0},
                       list(t.keys)))
        seen.append(w)
    real = stats("01.02", [], text)["table"]
    assert real == t.st, (real, t.st)

    f = Fig("f0102a", "Counting the cat sat on the mat, the act with the first table: each word's bytes summed "
            "pick its bucket, and only that bucket's list is walked", 340)
    words = words_of(text)
    f.text(24, 22, "printf 'the cat sat on the mat, the act\\n' | DS_STATS=1 bin/freq", "t", 11, mono=True)
    used = sorted({hash_sum(w) & 1023 for w in words})
    BY = {b: 150 + k * 32 for k, b in enumerate(used)}
    f.text(24, 140, "bucket", "tm", 10)
    f.text(118, 140, "first", "tm", 10, "middle")
    f.text(170, 140, "its list, newest first: each entry's index, then its key", "tm", 10)
    for k, b in enumerate(used):
        y = BY[b]
        f.text(24, y + 15, str(b), "t", 12.5, mono=True)
    f.text(24, BY[used[-1]] + 46, f"{len(used)} of the 1024 buckets are used; the others hold -1, an empty list",
           "tm", 10.5)

    def entry(x, y, i, key, cls, tcls):
        f.rect(x, y, 92, 22, cls, 4)
        f.text(x + 8, y + 15, str(i), "tm" if tcls == "t" else tcls, 10, mono=True)
        f.text(x + 52, y + 16, key, tcls, 12.5, "middle", 600, mono=True)

    for k, (w, walk, found, st, chains, keys) in enumerate(frames):
        s = hash_sum(w)
        b = s & 1023
        if found >= 0:
            cap = (f"\"{w}\" sums to {s}, bucket {b}: its list is walked and \"{w}\" is found after "
                   f"{len(walk)} probe{'s' if len(walk) != 1 else ''}. Its count goes up; the table is not changed.")
        elif walk:
            other = keys[walk[0]]
            cap = (f"\"{w}\" sums to {s}, the same as \"{other}\": bucket {b}. \"{other}\" has the same hash but other "
                   f"bytes, so \"{w}\" is not there, and goes in at the head of the list.")
        else:
            cap = f"\"{w}\" sums to {s}, bucket {b}, which is empty: \"{w}\" is new and goes in as entry {len(keys) - 1}."
        with steps.step(f, cap):
            x = 24
            for j, ww in enumerate(words):
                cls = "ta" if j == k else ("t" if j < k else "tm")
                f.text(x, 48, ww, cls, 12, weight=700 if j == k else None, mono=True)
                x += len(ww) * 7.2 + 12
            parts = " + ".join(str(c) for c in w.encode())
            f.text(24, 76, f"\"{w}\": {parts} = {s}", "t", 11.5, mono=True)
            f.text(24, 96, f"{s} & 1023 = {b}: bucket {b}", "ta", 11.5, weight=600, mono=True)
            f.text(616, 76, f"lookups {st['lookups']}", "t", 11, "end", mono=True)
            f.text(616, 94, f"probes {st['probes']}", "ta", 11, "end", 600, mono=True)
            f.text(616, 112, f"inserts {st['inserts']}", "t", 11, "end", mono=True)
            for bb, ch in chains.items():
                y = BY[bb]
                hot = bb == b
                f.rect(100, y, 36, 22, "a af" if hot else "s f", 4)
                f.text(118, y + 15, str(ch[0]), "ta" if hot else "t", 11, "middle", mono=True)
                f.line(136, y + 11, 166, y + 11, "a" if hot else "s", arrow=True)
                x = 168
                for n_, i in enumerate(ch):
                    new = found < 0 and i == len(keys) - 1
                    if hot and (new or i == found):
                        cls, tcls = "a fa", "f"           # the entry this word is: found, or just added
                    elif hot and i in walk:
                        cls, tcls = "a af", "ta"          # compared with it on the way
                    else:
                        cls, tcls = "s f", "t"
                    entry(x, y, i, keys[i], cls, tcls)
                    if n_ + 1 < len(ch):
                        f.line(x + 92, y + 11, x + 118, y + 11, "s", arrow=True)
                    x += 120
                f.text(x - 20, y + 15, "-1", "tm", 10, mono=True)
    return f


# ------------------------------------------------------------------ 01.03

def resize0103():
    book = open(BOOK, "rb").read()
    snap = {}

    def on_grow(t):
        if not snap:
            snap["chains"] = {b: t.chain(b) for b in range(t.nb)}
            snap["keys"] = list(t.keys)
            snap["hashes"] = list(t.hashes)
            snap["st"] = dict(t.st)

    t = Table(hash_fnv1a, True, dict(pushes=0, grows=0, moves=0))
    t.on_grow = on_grow
    order, counts, _ = count(book, table=t)
    real = stats("01.03", [], book)["table"]
    assert real == t.st, (real, t.st)
    keys, hashes = snap["keys"], snap["hashes"]
    nxt = order[len(keys)]
    # one old bucket whose list splits both ways, three or four long
    b = next(b for b in range(1024)
             if len(snap["chains"][b]) in (3, 4)
             and len({(hashes[i] >> 10) & 1 for i in snap["chains"][b]}) == 2)
    old = snap["chains"][b]
    moving = sorted(old)                     # grow() walks the entries in array order
    print("01.03 resize: bucket", b, [(i, keys[i], (hashes[i] >> 10) & 1) for i in old], "next word", nxt)

    f = Fig("f0103a", "The table doubling from 1024 buckets to 2048 as the book's 1025th different word comes, "
            "seen through one old bucket", 330)
    f.text(24, 22, "bin/freq data/book.txt at 01.03: FNV-1a, and twice the buckets once there are as many entries",
           "tm", 10.5)

    def bits(h):
        s = format(h & 2047, "011b")
        return s[0], s[1:]

    def entry(x, y, i, cls="s f", tcls="t", show_bits=True):
        f.rect(x, y, 128, 40, cls, 4)
        f.text(x + 8, y + 16, keys[i], tcls, 11.5, weight=600, mono=True)
        f.text(x + 120, y + 16, str(i), "tm" if tcls == "t" else tcls, 9.5, "end", mono=True)
        if show_bits:
            hi, lo = bits(hashes[i])
            f.text(x + 8, y + 32, hi, "ta" if tcls != "f" else "f", 11, weight=700, mono=True)
            f.text(x + 17, y + 32, lo, "tm" if tcls == "t" else tcls, 11, mono=True)

    def row(y, label, sub, chain, styles=None):
        f.text(24, y + 18, label, "t", 11.5, weight=600, mono=True)
        f.text(24, y + 33, sub, "tm", 10)
        x = 128
        if not chain:
            f.text(x, y + 24, "-1 (empty)", "tm", 10.5, mono=True)
        for k, i in enumerate(chain):
            cls, tcls = styles(i) if styles else ("s f", "t")
            entry(x, y, i, cls, tcls)
            if k + 1 < len(chain):
                f.line(x + 128, y + 20, x + 146, y + 20, "s", arrow=True)
            x += 148

    YO, YA, YB = 84, 170, 236
    frames = [(f"1024 entries in 1024 buckets, and \"{nxt}\" is the 1025th different word: table_put() calls "
               f"grow() before it adds it. Old bucket {b} holds {len(old)} entries.", [], None)]
    frames.append((f"grow(): a new bucket array of 2048, every list empty. Each entry is linked in again, "
                   f"in the order of the entries array, at hash & 2047.", [], None))
    placed = []
    for i in moving:
        placed.append(i)
        nb = hashes[i] & 2047
        frames.append((f"Entry {i}, \"{keys[i]}\": bit 10 of its hash is {(hashes[i] >> 10) & 1}, so it goes to "
                       f"bucket {nb}, at the head of that list.", list(placed), i))
    frames.append((f"Done: all 1024 entries linked in again (resizes 1, moves 1024); none of them was copied. "
                   f"Then \"{nxt}\" is added to its own bucket.", list(placed), None))
    for cap, placed_now, cur in frames:
        with steps.step(f, cap):
            f.text(128, 54, "each entry: its word, its index in the array, and its hash & 2047 in binary;", "tm",
                   10.5)
            f.text(128, 70, "the first bit, bit 10, is the one the old bucket number did not use", "tm", 10.5)
            started = cap.startswith("grow") or bool(placed_now)
            row(YO, f"bucket {b}", "old, of 1024", old,
                lambda i: ("m fs", "tm") if started and (i in placed_now or cap.startswith("grow")) else ("s f", "t"))
            if started:
                for yy, nb in ((YA, b), (YB, b + 1024)):
                    ch = [i for i in reversed(placed_now) if hashes[i] & 2047 == nb]
                    row(yy, f"bucket {nb}", "new, of 2048", ch,
                        lambda i, cur=cur: ("a fa", "f") if i == cur else ("a af", "ta"))
            done = cap.startswith("Done")
            r, m = (1, 1024) if done else (0, 0)
            f.text(24, 306, f"resizes {r}, moves {m}", "ta" if done else "t", 11.5, weight=600, mono=True)
    sizes = [1024 * 2 ** k for k in range(t.st["resizes"] + 1)]
    with steps.step(f, f"The whole book: the table doubled {t.st['resizes']} times, to {sizes[-1]} buckets, and "
                       f"moved {t.st['moves']} entries in all, fewer than its {t.st['inserts']} words: "
                       f"{t.st['probes'] / t.st['lookups']:.2f} probes a lookup."):
        f.text(24, 54, f"all {t.st['inserts']} different words of the book: the buckets it has had, to scale", "t", 12,
               weight=600)
        y = 76
        for k, nb in enumerate(sizes):
            w = 360 * nb / sizes[-1]
            last = k == len(sizes) - 1
            f.text(24, y + 15, f"{nb}", "ta" if last else "t", 12, weight=600, mono=True)
            f.rect(76, y, round(w, 1), 22, "a fa" if last else "a af", 3)
            if k:
                f.text(616, y + 15, f"{sizes[k - 1]} entries moved", "tm", 10.5, "end")
            y += 34
        f.text(24, y + 20, f"lookups {t.st['lookups']}, probes {t.st['probes']}, inserts {t.st['inserts']}", "t",
               11.5, mono=True)
        f.text(24, 306, f"resizes {t.st['resizes']}, moves {t.st['moves']} = "
               + " + ".join(str(x) for x in sizes[:-1]), "ta", 11.5, weight=600, mono=True)
    return f


def spread0103():
    book = open(BOOK, "rb").read()
    order = list(dict.fromkeys(words_of(book)))
    real = {}
    for name, args in (("fnv1a", []), ("sum", ["--hash=sum"])):
        st = stats("01.03", args, book)["table"]
        real[name] = st["probes"] / st["lookups"]
    NB, BINS = 8192, 64
    per = NB // BINS
    fig = Fig("f0103b", "Where the book's 7818 different words land in 8192 buckets: summed, they pile into "
              "the first quarter; FNV-1a spreads them over all of it", 310)
    fig.text(24, 22, f"the book's {len(order)} different words, in 8192 buckets (the table's size at the end); "
             f"one bar for each {per} buckets", "tm", 10.5)
    data = {}
    for name, fn in (("sum", hash_sum), ("fnv1a", hash_fnv1a)):
        bins = [0] * BINS
        used, longest = {}, 0
        for w in order:
            bk = fn(w) & (NB - 1)
            used[bk] = used.get(bk, 0) + 1
            bins[bk // per] += 1
        data[name] = (bins, len(used), max(used.values()))
    top = max(max(data[n][0]) for n in data)
    X, BW, H = 24, 6, 84
    smax = max(hash_sum(w) for w in order)
    for name, label, y0 in (("sum", "hash_sum: the bytes added up", 150), ("fnv1a", "hash_fnv1a: FNV-1a", 284)):
        bins, nused, longest = data[name]
        fig.text(X, y0 - H - 12, label, "t", 12, weight=600, mono=True)
        fig.line(X, y0, X + BINS * BW, y0, "m")
        for j, c in enumerate(bins):
            if c:
                h = max(1.5, H * c / top)
                fig.rect(X + j * BW + 0.5, round(y0 - h, 1), BW - 1, round(h, 1), "fa", 1, sw=False)
        fig.text(X, y0 + 15, "bucket 0", "tm", 10, mono=True)
        fig.text(X + BINS * BW, y0 + 15, "8191", "tm", 10, "end", mono=True)
        sx = X + BINS * BW + 28
        fig.text(sx, y0 - 58, f"{nused} buckets used", "t", 12)
        fig.text(sx, y0 - 38, f"longest list: {longest}", "t", 12)
        fig.text(sx, y0 - 18, f"{real[name]:.2f} probes a lookup", "ta", 12, weight=600)
    xs = X + (smax / per) * BW
    fig.line(round(xs, 1), 150 - H, round(xs, 1), 150, "a", dash=True)
    fig.text(round(xs, 1) + 6, 150 - H + 10, f"no word sums to more than {smax}", "ta", 10.5)
    print("01.03 spread:", {n: data[n][1:] for n in data}, "max sum", smax, "probes/lookup", real)
    return fig


def main():
    for name, fn in (("01.01-doubling", doubling0101), ("01.02-chain", chain0102), ("01.03-resize", resize0103),
                     ("01.03-spread", spread0103)):
        fig = fn()
        text = fig.svg()
        if name != "01.03-spread":
            print(name, "steps:", steps.check(text))
        print(write(MOD, name, fig))


if __name__ == "__main__":
    main()
