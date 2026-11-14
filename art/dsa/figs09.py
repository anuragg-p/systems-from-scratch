"""Figures for dsa module 09, Making files smaller: gzip (lessons 09.01-09.04).

    python3 -B art/dsa/figs09.py

Every value in these figures comes from a real run of the project as it stands at the lesson
(./learn files dsa --at NN.LL into a temporary directory, then make), with DS_TRACE=1, which has
the code print one line a step on stderr (the formats are at the top of lib/huffman.h,
lib/inflate.h, lib/lz77.h and lib/deflate.h). Where a figure shows more than the trace says (the
bits of a file, the chains of the hash table), this script works it out again from the same
bytes, and checks its answer against the trace and the DS_STATS counts, so a figure cannot
disagree with the code.

  09.01-tree     stepped: Huffman's tree for "abracadabra", the two lightest trees joined until
                 one is left, then the code lengths read off it and numbered canonically
                 (printf abracadabra | bin/gzip --huffman)
  09.02-bits     stepped: a 29-byte file from the system's gzip, read bit by bit: the header,
                 the block's 3 bits, each code, the match that overlaps itself, the trailer
                 (printf 'hello hello hello\\n' | gzip -9 -n | bin/gunzip)
  09.03-chains   stepped: LZ77 over "abracadabra abracadabra", one token a frame, each match
                 found by walking the hash chain of its first three bytes
                 (printf 'abracadabra abracadabra' | bin/gzip --lz77)
  09.04-block    one block of "abracadabra" priced in the three forms deflate can write, the
                 parts of each, and the first block of the book in the same three
                 (printf abracadabra | bin/gzip -c --blocks=...; bin/gzip -c data/book.txt)
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import figlib  # noqa: E402
from figlib import Fig, tw  # noqa: E402
import steps  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
figlib.LESSONS = os.path.join(ROOT, "tracks", "dsa", "lessons")
MOD = "09-gzip"


# ------------------------------------------------------------------ running the real code

class Project:
    """The project at one lesson, written by ./learn files and built, in a temporary directory."""

    def __init__(self, tmp, lid):
        self.dir = os.path.join(tmp, lid)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", lid, self.dir], check=True,
                       capture_output=True)
        subprocess.run(["make", "-s"], cwd=self.dir, check=True, capture_output=True)

    def run(self, argv, stdin=b"", system=False):
        """(stdout bytes, the trace lines without "trace: ", {structure: {count: n}}) of bin/argv[0]
        (the system's own program when system), with DS_TRACE=1 and DS_STATS=1."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("DS_")}
        env.update(LC_ALL="C")
        if not system:
            env.update(DS_TRACE="1", DS_STATS="1")
        prog = argv[0] if system else os.path.join(self.dir, "bin", argv[0])
        r = subprocess.run([prog] + argv[1:], cwd=self.dir, input=stdin, capture_output=True, env=env)
        if r.returncode != 0:
            raise SystemExit(f"{' '.join(argv)}: exit {r.returncode}\n{r.stderr.decode()}")
        err = r.stderr.decode().splitlines()
        stats = {}
        for line in err:
            m = re.match(r"^stats: (\w+): (.*)$", line)
            if m:
                stats[m.group(1)] = {k: int(v) for k, v in re.findall(r"([a-z ]+?) (\d+)(?:, |$)", m.group(2))}
        return r.stdout, [l[7:] for l in err if l.startswith("trace: ")], stats

    def table(self, name):
        """A table of numbers from lib/inflate.c: deflate_length_base and the others."""
        with open(os.path.join(self.dir, "lib", "inflate.c")) as fh:
            src = fh.read()
        m = re.search(name + r"\[\d+\] = \{([^}]*)\}", src)
        return [int(x) for x in m.group(1).replace("\n", " ").split(",")]


def show(c):
    """A byte as the lessons write it: 'a', and a space or a newline by name."""
    return {" ": "space", "\n": "\\n"}.get(c, c)


# ------------------------------------------------------------------ Huffman's tree (09.01)

JOIN = re.compile(r"^huffman: join (\S+) (\d+) \+ (\S+) (\d+) = (n\d+) (\d+)$")
ROWS = re.compile(r"^'(.)'\s+(\d+)\s+(\d+)\s+([01]+)$")
TOTAL = re.compile(r"^(\d+) bytes, (\d+) different: (\d+) bits as bytes, (\d+) bits in these codes")


def tree0901(p):
    out, tr, stats = p.run(["gzip", "--huffman"], b"abracadabra")
    lines = out.decode().splitlines()
    rows = [ROWS.match(l).groups() for l in lines[1:-1]]
    total = TOTAL.match(lines[-1]).groups()
    count = {b: int(c) for b, c, _, _ in rows}
    canon = {b: code for b, _, _, code in rows}
    joins = [JOIN.match(l).groups() for l in tr if l.startswith("huffman: join")]
    assert stats["huffman"]["joins"] == len(joins) == len(rows) - 1

    # the forest: each tree a name; a leaf is "'a'", a join "n1"
    kids, weight = {}, {}
    for b in count:
        weight[f"'{b}'"] = count[b]

    def key(name):              # lighter() in lib/huffman.c: the count, then the leaf's byte, then the join's order
        return (weight[name], ord(name[1]) if name[0] == "'" else 256 + int(name[1:]))

    forest = sorted(weight, key=key)
    frames = [("tree of", list(forest), dict(kids), None, tr[0])]
    for a, ca, b, cb, j, cj in joins:
        assert forest[:2] == [a, b], (forest, a, b)          # the code joined the two lightest, as drawn
        assert weight[a] == int(ca) and weight[b] == int(cb) and int(cj) == weight[a] + weight[b]
        weight[j] = int(cj)
        kids[j] = (a, b)
        forest = sorted(forest[2:] + [j], key=key)
        frames.append(("join", list(forest), dict(kids), (a, b, j), f"huffman: join {a} {ca} + {b} {cb} = {j} {cj}"))
    root = forest[0]

    def depth_of(n, d=0, acc=None):
        acc = {} if acc is None else acc
        if n in kids:
            for k in kids[n]:
                depth_of(k, d + 1, acc)
        else:
            acc[n[1]] = d
        return acc

    depth = depth_of(root)
    assert all(depth[b] == int(bits) for b, _, bits, _ in rows), "a length is not the leaf's depth"
    assert sum(count[b] * depth[b] for b in count) == int(total[3])

    # the canonical code as a tree of its own: the leaves where the codes put them
    ckids, cleaf = {}, {}
    for b, code in canon.items():
        node = ""
        for bit in code:
            ckids.setdefault(node, [None, None])[int(bit)] = node + bit
            node += bit
        cleaf[node] = b

    f = Fig("f0901a", 'Huffman\'s tree for "abracadabra", built by gzip --huffman a join at a time, then its codes', 342)
    R, SLOT, GAP, TOP, DY = 17, 58, 16, 58, 60
    AX0, AX1 = 20, 384
    PX = 410

    def layout(tops, kidmap):
        """(x, y) of every node: each tree's leaves in slots, a parent over the middle of its children."""
        widths = []
        for t in tops:
            stack, n = [t], 0
            while stack:
                x = stack.pop()
                if x in kidmap:
                    stack += list(kidmap[x])
                else:
                    n += 1
            widths.append(n)
        span = sum(widths) * SLOT + GAP * (len(tops) - 1)
        x = AX0 + (AX1 - AX0 - span) / 2
        pos = {}

        def place(n, d):
            if n not in kidmap:
                nonlocal x
                pos[n] = (x + SLOT / 2, TOP + d * DY)
                x += SLOT
                return pos[n][0]
            xs = [place(k, d + 1) for k in kidmap[n]]
            pos[n] = ((xs[0] + xs[-1]) / 2, TOP + d * DY)
            return pos[n][0]

        for t in tops:
            place(t, 0)
            x += GAP
        return pos

    def edges(pos, kidmap, bits=False, hot=()):
        for n, ks in kidmap.items():
            if n not in pos:
                continue
            x1, y1 = pos[n]
            for i, k in enumerate(ks):
                x2, y2 = pos[k]
                dx, dy = x2 - x1, y2 - y1
                d = (dx * dx + dy * dy) ** 0.5
                cls = "a" if k in hot else "s"
                f.line(x1 + dx / d * R, y1 + dy / d * R, x2 - dx / d * R, y2 - dy / d * R, cls)
                if bits:
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                    f.text(mx + (-10 if dx < 0 else 10), my, str(i), "ta", 12, "middle", 700, mono=True)

    def node(name, x, y, label, sub, cls, tcls, subcls="tm"):
        f.circle(x, y, R, cls)
        f.text(x, y + 5, label, tcls, 14 if len(label) == 1 else 12.5, "middle", 700, mono=True)
        if sub:
            f.text(x, y + R + 14, sub, subcls, 11, "middle", mono=True)

    def panel_head(y, s):
        f.text(PX, y, s, "tm", 11)

    # the base: the panel's rule and the legend
    f.line(PX - 14, 22, PX - 14, 300, "m")
    ly = 330
    f.circle(28, ly - 4, 8, "s f")
    f.text(42, ly, "a tree in the heap, with its weight", "tm", 11)
    f.circle(264, ly - 4, 8, "a af")
    f.text(278, ly, "the two lightest, joined next", "tm", 11)
    f.circle(470, ly - 4, 8, "a fa")
    f.text(484, ly, "the join just made", "tm", 11)

    nb = len(rows)
    for k, (kind, tops, km, joined, line) in enumerate(frames):
        if kind == "tree of":
            cap = (f'abracadabra counted: {", ".join(f"{b} {count[b]}" for b in count)}. Each byte is a tree of one '
                   f"node, weighed by its count, in the heap, which hands back the lightest first: "
                   f"{tops[0][1]} and {tops[1][1]}.")
        else:
            a, b, j = joined
            last = len(tops) == 1
            cap = (f"The two lightest, {a} and {b}, are popped and joined under {j}, which weighs "
                   f"{weight[a]} + {weight[b]} = {weight[j]}, and {j} is pushed back."
                   + (" One tree is left: the code." if last else "")
                   + (" On equal weights the heap gives a byte before a join, the smaller byte first."
                      if not last and k == 2 else ""))
        with steps.step(f, cap):
            pos = layout(tops, km)
            nxt = tops[:2] if len(tops) > 1 else []
            hot = set(joined[:2]) if joined else set()
            edges(pos, km, hot=hot)
            for n, (x, y) in pos.items():
                if joined and n == joined[2]:
                    cls, tcls = "a fa", "f"
                elif n in nxt:
                    cls, tcls = "a af", "ta"
                else:
                    cls, tcls = "s f", "t"
                if n in km:
                    node(n, x, y, str(weight[n]), None, cls, tcls)
                    f.text(x + R + 4, y - R + 4, n, "ta" if joined and n == joined[2] else "tm", 10.5, mono=True)
                else:
                    node(n, x, y, n[1], str(weight[n]), cls, tcls)
            panel_head(40, "DS_TRACE=1 printed")
            f.text(PX, 60, line[9:] if line.startswith("huffman: ") else line, "t", 11.5, mono=True)
            panel_head(96, "in the heap, lightest first")
            for i, t in enumerate(tops):
                f.text(PX, 118 + i * 18, t, "ta" if t in nxt else "t", 12, weight=600 if t in nxt else None,
                       mono=True)
                f.text(PX + 56, 118 + i * 18, str(weight[t]), "ta" if t in nxt else "t", 12, "end", mono=True)
            panel_head(232, "trees in the heap")
            f.text(PX, 254, f"{len(tops)}", "t", 15, weight=700, mono=True)
            f.text(PX + 22, 254, f"after {k} join{'s' if k != 1 else ''} of {nb - 1}", "tm", 11.5)

    # the lengths: each leaf's depth, the paths of the tree
    tops = [root]
    pos = layout(tops, kids)
    paths = {}

    def walk(n, s):
        if n in kids:
            walk(kids[n][0], s + "0")
            walk(kids[n][1], s + "1")
        else:
            paths[n[1]] = s

    walk(root, "")
    lens = sorted(set(depth.values()))
    sums = " + ".join(f"{sum(count[b] for b in count if depth[b] == d)} x {d}" for d in lens)
    with steps.step(f, f"A byte's code is its path from the root, 0 left and 1 right, so its length is its depth: "
                       f"{', '.join(f'{b} {depth[b]}' for b in count)} bits. {sums} = {total[3]} bits, against "
                       f"{total[2]} as bytes."):
        edges(pos, kids, bits=True)
        for n, (x, y) in pos.items():
            if n in kids:
                node(n, x, y, str(weight[n]), None, "s f", "t")
            else:
                node(n, x, y, n[1], paths[n[1]], "a af", "ta", "ta")
        for d in lens:
            f.text(AX0, TOP + d * DY + 4, f"depth {d}", "tm", 10.5)
        panel_head(40, "the tree's own codes")
        for i, b in enumerate(sorted(count, key=lambda b: (depth[b], paths[b]))):
            f.text(PX, 62 + i * 18, b, "t", 12, weight=600, mono=True)
            f.text(PX + 24, 62 + i * 18, f"{count[b]} x {depth[b]} bits", "t", 11.5, mono=True)
            f.text(PX + 120, 62 + i * 18, paths[b], "ta", 12, mono=True)
        y = 62 + nb * 18 + 10
        f.text(PX, y, f"{sums}", "t", 11.5, mono=True)
        f.text(PX, y + 20, f"= {total[3]} bits", "ta", 13, weight=700, mono=True)
        f.text(PX, y + 40, f"as bytes: {total[0]} x 8 = {total[2]} bits", "tm", 11)

    # the canonical numbering, as bin/gzip printed it
    cpos = {}
    cx = {}

    def cplace(n, d):
        if n in cleaf:
            cx[n] = len(cx)
            cpos[n] = (AX0 + (AX1 - AX0 - nb * SLOT) / 2 + cx[n] * SLOT + SLOT / 2, TOP + d * DY)
            return cpos[n][0]
        xs = [cplace(k, d + 1) for k in ckids[n] if k is not None]
        cpos[n] = ((xs[0] + xs[-1]) / 2, TOP + d * DY)
        return cpos[n][0]

    cplace("", 0)
    first = {}
    for b in sorted(count, key=lambda b: (depth[b], b)):
        first.setdefault(depth[b], canon[b])
    def group(d):
        bs = sorted(b for b in count if depth[b] == d)
        return f"the {d}-bit code{'s' if len(bs) > 1 else ''} from {first[d]} ({', '.join(bs)})"

    with steps.step(f, "A file keeps only the lengths. gzip numbers the codes from them, the canonical code, in byte "
                       "order within each length: " + ", then ".join(group(d) for d in lens)
                       + f". The same lengths, so the same {total[3]} bits, and a reader can number them again."):
        for n, ks in ckids.items():
            x1, y1 = cpos[n]
            for i, k in enumerate(ks):
                if k is None:
                    continue
                x2, y2 = cpos[k]
                dx, dy = x2 - x1, y2 - y1
                d = (dx * dx + dy * dy) ** 0.5
                r2 = R if k in cleaf else 9
                f.line(x1 + dx / d * 9, y1 + dy / d * 9, x2 - dx / d * r2, y2 - dy / d * r2, "s")
                f.text((x1 + x2) / 2 + (-10 if dx < 0 else 10), (y1 + y2) / 2, str(i), "ta", 12, "middle", 700,
                       mono=True)
        for n, (x, y) in cpos.items():
            if n in cleaf:
                node(n, x, y, cleaf[n], n, "a af", "ta", "ta")
            else:
                f.circle(x, y, 8, "s f")
        for d in lens:
            f.text(AX0, TOP + d * DY + 4, f"depth {d}", "tm", 10.5)
        panel_head(40, "bin/gzip --huffman printed")
        cols = ((PX, "start"), (PX + 82, "end"), (PX + 122, "end"), (PX + 136, "start"))
        for (x, anchor), head in zip(cols, lines[0].split()):
            f.text(x, 62, head, "tm", 11, anchor, mono=True)
        for i, row in enumerate(rows):
            for (x, anchor), v in zip(cols, (f"'{row[0]}'",) + tuple(row[1:])):
                f.text(x, 80 + i * 18, v, "ta" if x == cols[3][0] else "t", 11.5, anchor, mono=True)
        y = 80 + nb * 18 + 6
        f.text(PX, y, f"{total[2]} bits as bytes,", "t", 11.5)
        f.text(PX, y + 18, f"{total[3]} bits in these codes", "ta", 11.5, weight=700)
    return f


# ------------------------------------------------------------------ reading bits (09.02, 09.04)

class Bits:
    """DEFLATE's bit order: from the lowest bit of each byte up. pos counts bits from the start."""

    def __init__(self, data):
        self.data, self.pos = data, 0

    def bit(self):
        b = self.data[self.pos // 8] >> (self.pos % 8) & 1
        self.pos += 1
        return b

    def num(self, k):                  # a number: its first bit is its lowest
        return sum(self.bit() << i for i in range(k))

    def code(self, table):             # a Huffman code: its first bit is its highest
        c, s = 0, ""
        for n in range(1, 16):
            b = self.bit()
            c, s = c << 1 | b, s + str(b)
            if (n, c) in table:
                return table[(n, c)], s
        raise ValueError("no code")


def canonical(lengths):
    """{(length, code): symbol} for code lengths, numbered as RFC 1951 3.2.2 (and huff_codes) do."""
    bl = [0] * 16
    for n in lengths:
        bl[n] += 1
    bl[0] = 0
    code, nxt = 0, [0] * 16
    for n in range(1, 16):
        code = (code + bl[n - 1]) << 1
        nxt[n] = code
    out = {}
    for s, n in enumerate(lengths):
        if n:
            out[(n, nxt[n])] = s
            nxt[n] += 1
    return out


FIXED_LIT = canonical([8] * 144 + [9] * 112 + [7] * 24 + [8] * 8)
FIXED_DIST = canonical([5] * 32)


def fixed_fields(p, data, at):
    """The fields of one fixed block that starts at bit at of data: [(start, bits, kind, what, value)],
    and the bytes it stands for."""
    lbase, lextra = p.table("deflate_length_base"), p.table("deflate_length_extra")
    dbase, dextra = p.table("deflate_dist_base"), p.table("deflate_dist_extra")
    r = Bits(data)
    r.pos = at
    last, kind = r.num(1), r.num(2)
    assert kind == 1, "not a fixed block"
    fields = [(at, 3, "head", f"last {last}, type {kind}: fixed", (last, kind))]
    out = bytearray()
    while True:
        s0 = r.pos
        sym, code = r.code(FIXED_LIT)
        if sym < 256:
            fields.append((s0, r.pos - s0, "lit", code, sym))
            out.append(sym)
            continue
        if sym == 256:
            fields.append((s0, r.pos - s0, "end", code, 256))
            return fields, bytes(out), r.pos
        k = sym - 257
        length = lbase[k] + r.num(lextra[k])
        fields.append((s0, r.pos - s0, "len", code, (sym, length)))
        s1 = r.pos
        dsym, dcode = r.code(FIXED_DIST)
        dist = dbase[dsym] + r.num(dextra[dsym])
        fields.append((s1, r.pos - s1, "dist", dcode, (dsym, dist, dextra[dsym])))
        for _ in range(length):
            out.append(out[-dist])


# ------------------------------------------------------------------ a gzip file, bit by bit (09.02)

TOKEN = re.compile(r'^(?:inflate|lz77): (\d+): (?:literal "(.*)"|match distance (\d+) length (\d+) "(.*)")$')


def unquote(s):
    return s.encode().decode("unicode_escape")


def bits0902(p):
    text = b"hello hello hello\n"
    gz, _, _ = p.run(["gzip", "-9", "-n"], text, system=True)
    back, tr, stats = p.run(["gunzip"], gz)
    assert back == text
    header, deflate, trailer = gz[:10], gz[10:-8], gz[-8:]
    assert header[:4] == b"\x1f\x8b\x08\x00", "a header with no name, as -n makes it"
    fields, out, end = fixed_fields(p, deflate, 0)
    assert out == text and (end + 7) // 8 == len(deflate)
    m = re.match(r"^inflate: end of block 1: (\d+) bits, (\d+) bytes$", tr[-1])
    assert int(m.group(1)) == end and int(m.group(2)) == len(text)
    toks = [TOKEN.match(l).groups() for l in tr if TOKEN.match(l)]
    mine = [(int(f[4][1]) if f[2] == "len" else None) for f in fields if f[2] in ("lit", "len")]
    assert len(toks) == len(mine)
    crc = int.from_bytes(trailer[:4], "little")
    size = int.from_bytes(trailer[4:], "little")
    import zlib
    assert crc == zlib.crc32(text) and size == len(text)
    assert stats["inflate"]["fixed blocks"] == 1

    f = Fig("f0902a", "A 29-byte gzip file from the system's gzip, read by bin/gunzip a field at a time", 372)
    BW = 20.5
    FX = (640 - BW * len(gz)) / 2
    FY = 34
    CW, CH = 17, 22
    ROWBITS = 32
    BX = (640 - CW * ROWBITS) / 2
    BY0, RDY = 120, 62
    nbits = len(deflate) * 8

    STYLE = {"hot": ("a fa", "f"), "done": ("s f", "t"), "later": ("m f", "tm"), "soft": ("a af", "ta")}

    def xtext(xs, y, chars, tcls, size):
        """One <text> whose characters each sit at their own x: a row of cells in one element."""
        f.add(f'<text class="{tcls} mono" x="{" ".join(f"{x:.1f}" for x in xs)}" y="{y}" font-size="{size}" '
              f'font-weight="600" text-anchor="middle">{figlib.esc(chars)}</text>')

    def runs(idx, state, cut):
        """(state, first, end) for the indexes idx, a run broken where the state changes or cut(i) says."""
        out = []
        for i in idx:
            s = state(i)
            if out and out[-1][0] == s and out[-1][2] == i and not cut(i):
                out[-1][2] = i + 1
            else:
                out.append([s, i, i + 1])
        return out

    def file_row(hot, done_to):
        def state(i):
            return "hot" if i in hot else ("done" if i < done_to else "later")
        for s, a, b in runs(range(len(gz)), state, lambda i: i in (10, len(gz) - 8)):
            cls, tcls = STYLE[s]
            f.rect(FX + a * BW, FY, (b - a) * BW - 2.5, 22, cls, 3, dash=s == "later")
            xs, chars = [], ""
            for i in range(a, b):
                c = FX + i * BW + (BW - 2.5) / 2
                xs += [c - 3.1, c + 3.1]
                chars += f"{gz[i]:02x}"
            xtext(xs, FY + 15, chars, tcls, 10)

    def bit_xy(i):
        return BX + (i % ROWBITS) * CW, BY0 + (i // ROWBITS) * RDY

    def bit_rows(hot, done_to):
        """Every bit of the DEFLATE data in the order it is read: a box a byte."""
        def state(i):
            return "hot" if hot[0] <= i < hot[1] else ("done" if i < done_to else "later")
        for s, a, b in runs(range(nbits), state, lambda i: i % 8 == 0):
            cls, tcls = STYLE[s]
            x, y = bit_xy(a)
            f.rect(x - 1, y, (b - a) * CW, CH, cls, 3, dash=s == "later")
            xtext([bit_xy(i)[0] + (CW - 2) / 2 for i in range(a, b)], y + 15.5,
                  "".join(str(deflate[i // 8] >> (i % 8) & 1) for i in range(a, b)), tcls, 11)

    # the base: what every frame has
    f.text(FX, FY - 12, "the file, byte by byte (hex)", "tm", 11)
    for a, b, label in ((0, 10, "header"), (10, len(gz) - 8, "DEFLATE data"), (len(gz) - 8, len(gz), "trailer")):
        x1, x2 = FX + a * BW, FX + b * BW - 2.5
        f.brace_h(x1, x2, FY + 30, "m")
        f.text((x1 + x2) / 2, FY + 46, label, "tm", 11, "middle")
    f.text(BX - 1, BY0 - 22, "the DEFLATE data, bit by bit in the order read: each byte from its lowest bit up",
           "tm", 11)
    for i in range(0, nbits, 8):
        x, y = bit_xy(i)
        f.text(x, y - 5, f"{deflate[i // 8]:02x}", "tm", 9.5, mono=True)
    f.text(24, 337, "output so far", "tm", 11)

    def field_labels(upto, hot_fields):
        for (s, n, kind, code, val) in fields[:upto]:
            label = {"head": "3 bits", "lit": show(chr(val)) if kind == "lit" else "", "end": "end",
                     "len": f"len {val[1] if kind == 'len' else ''}", "dist": f"dist {val[1] if kind == 'dist' else ''}"}[kind]
            # a field may run over the end of a row: label its first part
            row_end = (s // ROWBITS + 1) * ROWBITS
            e = min(s + n, row_end)
            x1, y = bit_xy(s)
            x2 = x1 + (e - s) * CW - 2
            hot = (s, n) in hot_fields
            f.brace_h(x1, x2, y + CH + 6, "a" if hot else "m")
            f.text((x1 + x2) / 2, y + CH + 20, label, "ta" if hot else "tm", 10.5, "middle", 600 if hot else None,
                   mono=True)

    def output(done, hot_from=None):
        if not done:
            f.text(110, 337, "nothing yet", "tm", 11.5)
            return
        hot_from = len(done) if hot_from is None else hot_from
        for s, a, b in runs(range(len(done)), lambda i: "soft" if i >= hot_from else "done", lambda i: False):
            cls, tcls = STYLE[s]
            f.rect(110 + a * 22, 320, (b - a) * 22 - 2, 24, cls, 3)
            xs, chars = [], ""
            for i in range(a, b):
                c, x = chr(done[i]), 110 + i * 22 + 10
                if c == " ":
                    f.line(x - 4, 337, x + 4, 337, "a" if s == "soft" else "m")
                elif c == "\n":
                    xs += [x - 3.5, x + 3.5]
                    chars += "\\n"
                else:
                    xs.append(x)
                    chars += c
            xtext(xs, 337, chars, tcls, 12)

    def note(s, y=306):
        f.text(24, y, s, "t", 11.5)

    # frame 1: the header
    flg, mtime, xfl, os_ = gz[3], int.from_bytes(gz[4:8], "little"), gz[8], gz[9]
    with steps.step(f, f"The header, 10 bytes: 1f 8b says gzip, 08 says DEFLATE, flags {flg:02x} (no name, no "
                       f"comment), the time {mtime} (none given), {xfl:02x} (the slowest level), {os_:02x} (Unix). "
                       f"The DEFLATE data starts at byte 10."):
        file_row(set(range(10)), 10)
        bit_rows((0, 0), 0)
        output(b"")

    # one frame a field, the five literals after "he" in one
    groups = []
    i = 0
    while i < len(fields):
        if fields[i][2] == "lit" and i >= 3:
            j = i
            while j < len(fields) and fields[j][2] == "lit":
                j += 1
            groups.append(list(range(i, j)))
            i = j
        elif fields[i][2] == "len":
            groups.append([i, i + 1])
            i += 2
        else:
            groups.append([i])
            i += 1
    made = bytearray()
    for g in groups:
        first, last = fields[g[0]], fields[g[-1]]
        span = (first[0], last[0] + last[1])
        before = len(made)
        kind = first[2]
        if kind == "head":
            cap = (f"The block's first 3 bits, read from the lowest bit of byte {deflate[0]:02x}: 1, the last block; "
                   f"then 1, 0, which is the number 1, lowest bit first: a block in the fixed codes.")
        elif kind == "lit" and len(g) == 1:
            made.append(first[4])
            cap = (f"The next bits, {first[3]}, are the fixed code of {first[4]}, '{show(chr(first[4]))}': a literal "
                   f"byte. A code is read a bit at a time until the bits so far are a code ({len(first[3])} here).")
        elif kind == "lit":
            for k in g:
                made.append(fields[k][4])
            cap = (f"{len(g)} more literals, 8 bits each: " + " ".join(f"'{show(chr(fields[k][4]))}'" for k in g)
                   + f". {len(made)} bytes out so far.")
        elif kind == "len":
            sym, length = first[4]
            dsym, dist, dx = last[4]
            for _ in range(length):
                made.append(made[-dist])
            cap = (f"{first[3]} is symbol {sym}: a match of length {length}. Then a distance: code {dsym} "
                   f"({last[3]}) and {dx} extra bit, {dist} back. {length} bytes from {dist} back: the copy "
                   f"overlaps the bytes it writes, so it goes a byte at a time.")
        elif kind == "end":
            cap = (f"{first[3]} is symbol 256, the end of the block, and the block was the last: {end} bits. "
                   f"The rest of the byte is padding.")
        with steps.step(f, cap):
            file_row(set(range(10 + span[0] // 8, 10 + (span[1] - 1) // 8 + 1)), 10 + span[0] // 8)
            bit_rows(span, span[0])
            field_labels(g[-1] + 1, {(fields[k][0], fields[k][1]) for k in g})
            output(bytes(made), before if kind != "head" else None)
            if kind == "len":
                note(f"match: length {length}, distance {dist}")
    assert bytes(made) == text

    with steps.step(f, f"The trailer: the CRC-32 of the {size} bytes, {crc:08x}, and their number, {size}, each "
                       f"lowest byte first. gunzip works both out from what it wrote; they agree, so it writes "
                       f"the output."):
        file_row(set(range(len(gz) - 8, len(gz))), len(gz) - 8)
        bit_rows((0, 0), nbits)
        field_labels(len(fields), set())
        output(bytes(made))
        note(f"CRC-32 {crc:08x}, size {size}: both match")
    return f


# ------------------------------------------------------------------ the hash chains (09.03)

def hash3(b, i):
    """lib/lz77.c's hash3: the three bytes at i, times a large odd number, the top 15 bits."""
    x = b[i] | b[i + 1] << 8 | b[i + 2] << 16
    return ((x * 2654435761) & 0xffffffff) >> 17


def chains0903(p):
    text = b"abracadabra abracadabra"
    out, tr, stats = p.run(["gzip", "--lz77"], text)
    toks = [TOKEN.match(l).groups() for l in tr]
    n = len(text)

    # match_hash again, with its chains, newest first
    head, prev, hashed = {}, {}, 0
    steps_, cands, comps = [], 0, 0
    pos = 0
    for t in toks:
        assert int(t[0]) == pos
        tried = []
        best, bdist = 0, 0
        mx = min(258, n - pos)
        if mx >= 3:
            while hashed < pos:
                h = hash3(text, hashed)
                prev[hashed] = head.get(h, -1)
                head[h] = hashed
                hashed += 1
            c = head.get(hash3(text, pos), -1)
            while c >= 0:
                cands += 1
                k = 0
                while k < mx:
                    comps += 1
                    if text[c + k] != text[pos + k]:
                        break
                    k += 1
                tried.append((c, k))
                if k > best:
                    best, bdist = k, pos - c
                    if k == mx:
                        break
                c = prev[c]
        table = {}
        for q in range(hashed):
            table.setdefault(hash3(text, q), []).insert(0, q)
        if t[1] is not None:
            assert best < 3
            steps_.append((pos, "lit", 1, 0, tried, table))
            pos += 1
        else:
            assert (bdist, best) == (int(t[2]), int(t[3])), (t, bdist, best)
            steps_.append((pos, "match", best, bdist, tried, table))
            pos += best
    assert pos == n
    assert stats["lz77"]["candidates"] == cands and stats["lz77"]["comparisons"] == comps

    f = Fig("f0903a", 'LZ77 over "abracadabra abracadabra": each match found on the hash chain of its first three bytes',
            336)
    W = 24
    X0 = (640 - W * n) / 2
    TY = 50
    f.text(24, 18, "printf 'abracadabra abracadabra' | DS_TRACE=1 bin/gzip --lz77", "tm", 11, mono=True)
    for i in range(n):
        f.text(X0 + i * W + (W - 3) / 2, TY - 8, str(i), "tm", 9.5, "middle", mono=True)
    TBY = 146

    def cells(pos, kind, length, dist):
        for i, c in enumerate(text.decode()):
            x = X0 + i * W
            if pos <= i < pos + length:
                cls, tcls = "a fa", "f"
            elif kind == "match" and pos - dist <= i < pos - dist + length:
                cls, tcls = "a af", "ta"
            elif i < pos:
                cls, tcls = "s f", "t"
            else:
                cls, tcls = "m f", "tm"
            f.rect(x, TY, W - 3, 28, cls, 3, dash=cls == "m f")
            if c == " ":
                f.line(x + 6, TY + 20, x + W - 9, TY + 20, tcls if tcls != "t" else "s")
            else:
                f.text(x + (W - 3) / 2, TY + 19, c, tcls, 13, "middle", 600, mono=True)
        if kind == "match":
            xa = X0 + (pos - dist) * W + (W - 3) / 2
            xb = X0 + pos * W + (W - 3) / 2
            f.path(f"M{xb:.1f} {TY + 32} C{xb:.1f} {TY + 58} {xa:.1f} {TY + 58} {xa:.1f} {TY + 34}", "a", arrow=True)
            f.text((xa + xb) / 2, TY + 66, f"distance {dist}, length {length}", "ta", 11.5, "middle", 700)
        else:
            x = X0 + pos * W + (W - 3) / 2
            f.text(x, TY + 48, "literal", "ta", 11.5, "middle", 700)

    def chain_table(table, look, tried):
        f.text(24, TBY - 12, "the hash table: for each hash, a chain of the places that had it, newest first", "tm", 11)
        rows = sorted(table.items(), key=lambda kv: kv[1][-1])
        for r, (h, places) in enumerate(rows):
            col, rr = divmod(r, 5)
            x, y = 24 + col * 300, TBY + rr * 26
            s = text[places[0]:places[0] + 3].decode()
            on = h == look
            f.rect(x, y, 290, 22, "a af" if on else "s f", 4)
            f.text(x + 8, y + 15.5, '"' + s + '"', "ta" if on else "t", 11.5, weight=600, mono=True)
            f.text(x + 58, y + 15.5, f"#{h}", "tm", 10.5, mono=True)
            for j, q in enumerate(places):
                bx = x + 112 + j * 96
                hit = [k for c, k in tried if c == q] if on else []
                f.rect(bx, y + 3, 22, 16, "a f" if hit else "s f", 3)
                f.text(bx + 11, y + 15, str(q), "ta" if hit else "t", 10.5, "middle", 600, mono=True)
                if j:
                    f.line(bx - 26, y + 11, bx - 3, y + 11, "m", arrow=True)
                if hit:
                    f.text(bx + 26, y + 15, f"{hit[0]} bytes", "ta", 10, mono=True)
        if not rows:
            f.text(24, TBY + 15, "empty: nothing has been seen yet", "tm", 11.5)

    toks_shown = []
    for k, (pos, kind, length, dist, tried, table) in enumerate(steps_):
        look = hash3(text, pos) if pos + 3 <= n else None
        s3 = text[pos:pos + 3].decode()
        if kind == "match":
            toks_shown.append(f"({dist},{length})")
            trys = ", ".join(f"place {c} gives {m} bytes" for c, m in tried)
            cap = (f'At {pos}: the chain of "{s3}" holds {", ".join(str(c) for c, _ in tried)}; tried nearest first, '
                   f"{trys}. The longest wins: a match, {dist} back, {length} bytes, "
                   f'"{text[pos:pos + length].decode()}".')
        else:
            toks_shown.append(show(chr(text[pos])) if text[pos] != 32 else "space")
            assert not tried and look is not None and not table.get(look)      # its chain is empty
            cap = (f'At {pos}: "{s3}" has not been seen before (its chain is empty), so '
                   f"'{show(chr(text[pos]))}' goes out as a literal."
                   + (" The places before it are in the table now, each at the head of the chain of its three bytes."
                      if k == 1 else ""))
        with steps.step(f, cap):
            cells(pos, kind, length, dist)
            chain_table(table, look, tried)
            f.text(24, 318, "tokens so far:", "tm", 11)
            x = 116
            for i, t in enumerate(toks_shown):
                last = i == len(toks_shown) - 1
                f.text(x, 318, t, "ta" if last else "t", 12, weight=700 if last else 500, mono=True)
                x += tw(t, 12, True) + 10
    return f, stats["lz77"]


# ------------------------------------------------------------------ one block, three ways (09.04)

DBLOCK = re.compile(r"^deflate: block (\d+)( \(last\))?: (\d+) bytes, (\d+) tokens: stored (\d+) bits, fixed (\d+) bits, "
                    r"dynamic (\d+) bits: (\w+)$")


def dynamic_parts(data):
    """The parts of the dynamic block at the start of data: [(what, bits)] up to the block's codes."""
    r = Bits(data)
    r.num(3)
    nlit, ndist, nclen = r.num(5) + 257, r.num(5) + 1, r.num(4) + 4
    order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
    cl = [0] * 19
    for i in range(nclen):
        cl[order[i]] = r.num(3)
    table = canonical(cl)
    a = r.pos
    got, items = 0, 0
    while got < nlit + ndist:
        sym, _ = r.code(table)
        items += 1
        got += 1 if sym < 16 else (3 + r.num(2) if sym == 16 else 3 + r.num(3) if sym == 17 else 11 + r.num(7))
    return nlit, ndist, nclen, items, [("3", 3), ("counts", 14), ("cl", 3 * nclen), ("lengths", r.pos - a)], r.pos


def block0904(p):
    priced = {}
    files = {}
    for form in ("stored", "fixed", "dynamic", "best"):
        gz, tr, stats = p.run(["gzip", "-c", f"--blocks={form}"], b"abracadabra")
        m = [DBLOCK.match(l) for l in tr if DBLOCK.match(l)]
        assert len(m) == 1
        priced[form] = m[0]
        files[form] = gz
        back, btr, _ = p.run(["gunzip", "-c"], gz)
        assert back == b"abracadabra"
        if form == "dynamic":
            dyn_trace = btr
    best = priced["best"]
    sb, fb, db = int(best.group(5)), int(best.group(6)), int(best.group(7))
    assert best.group(8) == "fixed" and files["best"] == files["fixed"]
    for form in ("stored", "fixed", "dynamic"):
        assert priced[form].group(5, 6, 7) == best.group(5, 6, 7)

    # stored: the 3 bits, the pad, LEN and NLEN, the bytes
    stored = [("3", 3), ("pad", (8 - 3 % 8) % 8), ("LEN", 16), ("NLEN", 16), ("11 bytes as they are", 88)]
    assert sum(b for _, b in stored) == sb
    # fixed: the fields as inflate reads them
    ff, out, end = fixed_fields(p, files["fixed"][10:-8], 0)
    assert out == b"abracadabra" and end == fb
    lits = sum(n for _, n, k, _, _ in ff if k == "lit")
    lenf = next(f for f in ff if f[2] == "len")
    distf = next(f for f in ff if f[2] == "dist")
    endf = next(f for f in ff if f[2] == "end")
    fixed = [("3", 3), (f"{sum(1 for x in ff if x[2] == 'lit')} literals, 8 bits each", lits),
             (f"len {lenf[4][1]}", lenf[1]), (f"dist {distf[4][1]}", distf[1]), ("end", endf[1])]
    assert sum(b for _, b in fixed) == fb
    # dynamic: the header's parts, then the symbols in the block's own codes
    nlit, ndist, nclen, items, parts, hdr_end = dynamic_parts(files["dynamic"][10:-8])
    m = re.search(r"header (\d+) bits, (\d+) literal/length codes .*?, (\d+) distance codes", " ".join(dyn_trace))
    assert int(m.group(1)) == hdr_end - 3 and int(m.group(2)) == nlit and int(m.group(3)) == ndist
    dynamic = [("3", 3), ("HLIT HDIST HCLEN", 14), (f"code-length code, {nclen} x 3", 3 * nclen),
               ("the lengths, run-length coded", parts[3][1]), ("the symbols", db - hdr_end)]
    assert sum(b for _, b in dynamic) == db

    # the book's first block
    _, btr, _ = p.run(["gzip", "-c", os.path.join(p.dir, "data", "book.txt")])
    blocks = [DBLOCK.match(l) for l in btr if DBLOCK.match(l)]
    b1, nblocks = blocks[0], len(blocks)
    bs, bf, bd = int(b1.group(5)), int(b1.group(6)), int(b1.group(7))
    assert b1.group(8) == "dynamic"

    f = Fig("f0904a", "One block priced three ways before it is written: abracadabra, and the first block of the book", 410)
    X0, X1 = 92, 560
    scale = (X1 - X0) / max(sb, fb, db)
    f.text(24, 22, 'printf abracadabra | DS_TRACE=1 bin/gzip -c: one block of 11 bytes, 8 tokens', "tm", 11, mono=True)

    def bar(y, name, segs, total, win):
        f.text(24, y + 17, name, "ta" if win else "t", 12.5, weight=700 if win else 600)
        x = X0
        below = 0
        for i, (label, bits) in enumerate(segs):
            w = bits * scale
            cls = "a af" if win else ("s fs" if i % 2 else "s f")
            f.rect(x, y, w, 26, cls, 2)
            inner = str(bits)
            if label not in ("3",) and tw(label, 10.5) + 8 < w:
                f.text(x + w / 2, y + 12, label, "ta" if win else "t", 10.5, "middle")
                f.text(x + w / 2, y + 23, inner, "ta" if win else "tm", 10, "middle", mono=True)
            elif tw(inner, 10, True) + 4 < w:
                f.text(x + w / 2, y + 17.5, inner, "ta" if win else "tm", 10, "middle", mono=True)
                if label != "3":
                    f.text(x + w / 2, y + 40 + (below % 2) * 12, label, "tm", 10, "middle")
                    below += 1
            else:
                f.text(x + w / 2, y - 4, inner, "tm", 9.5, "middle", mono=True)
            x += w
        f.text(x + 6, y + 17.5, f"{total} bits", "ta" if win else "t", 11.5, weight=700 if win else None, mono=True)

    win = best.group(8)
    bar(42, "stored", stored, sb, win == "stored")
    bar(106, "fixed", fixed, fb, win == "fixed")
    bar(170, "dynamic", dynamic, db, win == "dynamic")
    f.text(X0, 240, "3: the bits every block opens with, the last block or not, and its form", "tm", 10.5)
    f.text(X0, 255, f"dynamic: {nlit} + {ndist} code lengths, sent as {items} symbols of a third Huffman code",
           "tm", 10.5)
    f.text(X0, 274, f"fixed is the cheapest, {fb} bits ({(fb + 7) // 8} bytes once padded): that is the one written",
           "ta", 11, weight=600)

    BY = 314
    f.text(24, BY - 8, f"the book, block 1 of {nblocks}: {int(b1.group(3))} bytes, {int(b1.group(4))} tokens", "tm",
           11, mono=True)
    bscale = (520 - X0) / bs
    for i, (name, bits) in enumerate((("stored", bs), ("fixed", bf), ("dynamic", bd))):
        y = BY + i * 30
        win = name == b1.group(8)
        f.text(24, y + 15, name, "ta" if win else "t", 12, weight=700 if win else 600)
        f.rect(X0, y, bits * bscale, 20, "a af" if win else "s f", 2)
        f.text(X0 + bits * bscale + 6, y + 14.5, f"{bits} bits", "ta" if win else "t", 11.5,
               weight=700 if win else None, mono=True)
    return f


# ------------------------------------------------------------------ main

FIGS = [("09.01", "09.01-tree", tree0901, True), ("09.02", "09.02-bits", bits0902, True),
        ("09.03", "09.03-chains", lambda p: chains0903(p)[0], True), ("09.04", "09.04-block", block0904, False)]


def main():
    sys.dont_write_bytecode = True
    from archmap import check
    paths = []
    with tempfile.TemporaryDirectory(prefix="figs09-") as tmp:
        projects = {}
        for lid, name, fn, stepped in FIGS:
            if lid not in projects:
                projects[lid] = Project(tmp, lid)
            fig = fn(projects[lid])
            path = figlib.write(MOD, name, fig)
            with open(path) as fh:
                text = fh.read()
            if stepped:
                n = steps.check(text)
                print(f"{os.path.relpath(path, ROOT)}: {n} steps, {len(text)} bytes")
            else:
                print(f"{os.path.relpath(path, ROOT)}: {len(text)} bytes")
            paths.append(path)
    bad = check(paths)
    for b in bad:
        print("problem:", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
