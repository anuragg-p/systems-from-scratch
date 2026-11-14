"""Figures for dsa module 05, Checking spelling: spell (lessons 05.01-05.03).

    python3 -B art/dsa/figs05.py

Every value in these figures comes from a real run of the project as it stands at the lesson
(./learn files dsa --at NN.LL into a temporary directory, then make), with DS_TRACE=1, which has
the structures print one line a step on stderr (the formats are at the top of lib/trie.c,
lib/bloom.c and lib/edit.c). The figures are drawn from those lines alone, so they cannot
disagree with the code.

  05.01-trie     stepped: the dictionary car cart cat dog going into the trie, the text "cab"
                 checked against it, and -p ca completed from the node "ca" reaches
                 (printf 'cab\\n' | bin/spell -d small.txt; bin/spell -d small.txt -p ca)
  05.02-bits     stepped: the same four words into a Bloom filter sized for them at --fp=0.1
                 (23 bits, 4 places a word), then cat, cot and hat tested; hat is no word of the
                 dictionary, but its four bits were set by the others
                 (printf 'cat cot hat\\n' | bin/spell --algo=bloom --fp=0.1 -d small.txt)
  05.03-table    stepped: the table for kitten and sitting filled a row at a time, ending on 3
                 (bin/spell --distance kitten sitting)
  05.03-walk     the suggestion walk for "cst" within one edit over the same four words: the row
                 each node carries, the two subtrees left out, and cat found
                 (printf 'cst\\n' | bin/spell -s -e 1 -d small.txt)
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
MOD = "05-spell"
SMALL = "car\ncart\ncat\ndog\n"


# ------------------------------------------------------------------ running the real code

class Project:
    """The project at one lesson, written by ./learn files and built, in a temporary directory."""

    def __init__(self, tmp, lid):
        self.dir = os.path.join(tmp, lid)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", lid, self.dir], check=True,
                       capture_output=True)
        subprocess.run(["make", "-s"], cwd=self.dir, check=True, capture_output=True)
        with open(os.path.join(self.dir, "small.txt"), "w") as f:
            f.write(SMALL)

    def spell(self, args, stdin=""):
        """(stdout, the trace lines without "trace: ", the stats lines) of bin/spell args."""
        env = dict(os.environ, DS_TRACE="1", DS_STATS="1", LC_ALL="C")
        r = subprocess.run(["bin/spell"] + args, cwd=self.dir, input=stdin.encode(), capture_output=True, env=env)
        if r.returncode not in (0, 1):
            raise SystemExit(f"bin/spell {' '.join(args)}: exit {r.returncode}\n{r.stderr.decode()}")
        err = r.stderr.decode().splitlines()
        return (r.stdout.decode(), [l[7:] for l in err if l.startswith("trace: ")],
                [l for l in err if l.startswith("stats: ")])


# ------------------------------------------------------------------ the trie (05.01, 05.03)

ADD = re.compile(r'^trie: add "(\w+)": (\w) -> (\d+)( new)?(, a word)?$')
STEP = re.compile(r'^trie: (has|find) "(\w+)": (\w) -> (\d+|none)$')
ANSWER = re.compile(r'^trie: has "(\w+)": (yes|no)$')
EACH = re.compile(r'^trie: each "(\w+)" -> (\d+)(, a word)?$')
NEAR = re.compile(r'^trie: near "(\w+)" -> (\d+): ([\d ]+), min (\d+)(, pruned|, a word at (\d+))?$')


def build_tree(lines):
    """{node: (parent, letter)} and the set of nodes where a word ends, from the add lines."""
    nodes, words, at = {0: (None, "")}, set(), {}
    for line in lines:
        m = ADD.match(line)
        if not m:
            continue
        word, letter, node = m.group(1), m.group(2), int(m.group(3))
        parent = at.get(word, 0)
        if node in nodes:
            assert nodes[node] == (parent, letter), line
        else:
            assert m.group(4), line                       # a node not seen before is a new one
            nodes[node] = (parent, letter)
        at[word] = node
        if m.group(5):
            words.add(node)
    return nodes, words


def layout(nodes, x0, slot, y0, dy):
    """(x, y) of each node: leaves side by side in a-to-z order, parents over their children."""
    kids = {n: sorted((c for c, (p, _) in nodes.items() if p == n), key=lambda c: nodes[c][1]) for n in nodes}
    pos, nxt = {}, [0]

    def place(n, depth):
        if not kids[n]:
            x = nxt[0]
            nxt[0] += 1
        else:
            xs = [place(c, depth + 1) for c in kids[n]]
            x = (xs[0] + xs[-1]) / 2
        pos[n] = (x0 + x * slot, y0 + depth * dy)
        return x

    place(0, 0)
    return pos


def path_of(nodes, n):
    out = []
    while n is not None:
        out.append(n)
        n = nodes[n][0]
    return out[::-1]


def prefix_of(nodes, n):
    return "".join(nodes[p][1] for p in path_of(nodes, n))


R = 14


def draw_tree(f, nodes, pos, shown, words, path=(), here=None, new=(), dim=(), cut=(), labels=None):
    """The trie: shown nodes only. path: nodes drawn in the accent, here: the node the step ends on,
    new: nodes made in this step, dim: nodes drawn dashed (never visited), cut: nodes marked pruned."""
    for n in sorted(shown):
        p, letter = nodes[n]
        if p is None or p not in shown:
            continue
        (x1, y1), (x2, y2) = pos[p], pos[n]
        dx, dy = x2 - x1, y2 - y1
        d = (dx * dx + dy * dy) ** 0.5
        on = n in path and p in path
        cls = "a" if on else ("m" if n in dim else "s")
        f.line(x1 + dx / d * R, y1 + dy / d * R, x2 - dx / d * (R + (4 if n in words else 0)),
               y2 - dy / d * (R + (4 if n in words else 0)), cls, dash=n in dim)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        side = -1 if dx < -1 else 1
        lx = mx + side * 11 if abs(dx) > 1 else mx + 11
        f.text(lx, my + 4, letter, "ta" if on else ("tm" if n in dim else "t"), 13, "middle", 600, mono=True)
    for n in sorted(shown):
        x, y = pos[n]
        if n == here:
            cls, tcls = "a fa", "f"
        elif n in new:
            cls, tcls = "a af", "ta"
        elif n in path:
            cls, tcls = "a f", "ta"
        elif n in dim:
            cls, tcls = "m f", "tm"
        else:
            cls, tcls = "s f", "t"
        if n in words:
            f.add(f'<circle class="{cls.split()[0]}" cx="{x}" cy="{y}" r="{R + 4}" stroke-width="1.5"'
                  f'{" stroke-dasharray=" + chr(34) + "3 3" + chr(34) if n in dim else ""}/>')
        if n in dim:
            f.add(f'<circle class="{cls}" cx="{x}" cy="{y}" r="{R}" stroke-width="1.5" stroke-dasharray="3 3"/>')
        else:
            f.circle(x, y, R, cls)
        f.text(x, y + 4, str(n), tcls, 11, "middle", 600, mono=True)
        if n in cut:
            f.text(x, y + R + 18, "pruned", "ta", 10.5, "middle", 600)
        if labels and n in labels:
            for k, (s, cls2) in enumerate(labels[n]):
                f.text(x + R + 10, y - 3 + k * 13, s, cls2, 10.5, mono=True)


def letters(f, x, y, word, done, cur, miss=None, w=24):
    """The word's letters as boxes: those before cur done, cur in the accent, the rest to come."""
    for i, ch in enumerate(word):
        if miss is not None and i == miss:
            cls, tcls, dash = "a f", "ta", True
        elif i == cur:
            cls, tcls, dash = "a fa", "f", False
        elif i < done:
            cls, tcls, dash = "a af", "ta", False
        else:
            cls, tcls, dash = "m f", "tm", True
        f.rect(x + i * w, y, w - 3, 26, cls, 4, dash=dash)
        f.text(x + i * w + (w - 3) / 2, y + 18, ch, tcls, 13, "middle", 600, mono=True)


def trie0501(p):
    out1, tr1, _ = p.spell(["-d", "small.txt"], "cab\n")
    out2, tr2, _ = p.spell(["-d", "small.txt", "-p", "ca"])
    adds = [l for l in tr1 if l.startswith("trie: add")]
    assert adds == [l for l in tr2 if l.startswith("trie: add")]
    nodes, words = build_tree(adds)
    pos = layout(nodes, 70, 100, 62, 60)
    f = Fig("f0501a", "A trie built from car cart cat dog by spell, then a word checked and a prefix completed", 372)
    PX = 340

    # the base: the legend and the panel's frame
    f.line(PX - 18, 20, PX - 18, 330, "m")
    ly = 360
    f.circle(32, ly - 4, 8, "s f")
    f.text(46, ly, "a node, numbered in the order made", "tm", 11)
    f.circle(262, ly - 4, 8, "s f")
    f.add(f'<circle class="s" cx="262" cy="{ly - 4}" r="11" stroke-width="1.5"/>')
    f.text(280, ly, "a word ends here", "tm", 11)
    f.circle(408, ly - 4, 8, "a fa")
    f.text(422, ly, "where this step ends", "tm", 11)

    frames = []                       # (caption, shown, path, here, new, panel)
    shown, wset = {0}, set()

    def panel(head, cmd, word, done, cur, trace, printed=None, miss=None, note=None):
        return dict(head=head, cmd=cmd, word=word, done=done, cur=cur, trace=trace, printed=printed, miss=miss,
                    note=note)

    # adding: the first word a letter at a time, each later word in one step
    by_word = []
    for line in adds:
        m = ADD.match(line)
        if not by_word or by_word[-1][0] != m.group(1):
            by_word.append((m.group(1), []))
        by_word[-1][1].append((line, m))
    for wi, (word, ls) in enumerate(by_word):
        groups = [[x] for x in ls] if wi == 0 else [ls]
        for g in groups:
            made = []
            for line, m in g:
                node = int(m.group(3))
                if m.group(4):
                    made.append(node)
                    shown.add(node)
                if m.group(5):
                    wset.add(node)
            last = int(g[-1][1].group(3))
            k = len(ls) if wi else ls.index(g[0]) + 1
            had = [int(m.group(3)) for _, m in g if not m.group(4)]
            if wi == 0:
                l0 = g[0][1]
                cap = (f'Adding "{word}": the root has no child for {l0.group(2)}, so node {l0.group(3)} is made'
                       + (f'; "{word}" ends here, so node {l0.group(3)} is marked as a word.' if l0.group(5) else "."))
            else:
                share = "".join(nodes[n][1] for n in had)
                cap = (f'Adding "{word}": ' + (f'"{share}" is there already (nodes {", ".join(map(str, had))}); '
                                                if had else "nothing is shared; ")
                       + f'{"node" if len(made) == 1 else "nodes"} {", ".join(map(str, made))} '
                       + f'{"is" if len(made) == 1 else "are"} made, and node {last} is marked as a word.')
            frames.append((cap, set(shown), path_of(nodes, last), last, made, set(wset),
                           panel("reading the dictionary", f'add "{word}"', word, k, k - 1,
                                 [l[6:] for l, _ in g])))

    # checking the text: has "cab"
    hl = [l for l in tr1 if l.startswith("trie: has")]
    walked, miss = [], None
    for line in hl:
        m = STEP.match(line)
        if m and m.group(4) != "none":
            walked.append(int(m.group(4)))
        elif m:
            miss = m.group(3)
    ans = ANSWER.match(hl[-1])
    w = ans.group(1)
    frames.append((f'Checking the text "{w}": c and a lead to node {walked[-1]}, which has no child for {miss}: '
                   f'"{w}" is no word, and spell prints it.',
                   set(shown), [0] + walked, walked[-1], [], set(wset),
                   panel("checking the text", f'has "{w}"', w, len(walked), None, [l[6:] for l in hl],
                         printed=out1.split(), miss=len(walked))))
    stub = (walked[-1], miss)

    # completing a prefix: find, then each word below
    fl = [l for l in tr2 if l.startswith("trie: find")]
    walked = [int(STEP.match(l).group(4)) for l in fl]
    pre = STEP.match(fl[0]).group(2)
    frames.append((f'-p {pre}: the walk down the prefix ends at node {walked[-1]}. Every word that starts with '
                   f'"{pre}" is below it, and nothing else is.',
                   set(shown), [0] + walked, walked[-1], [], set(wset),
                   panel(f"completing -p {pre}", f'find "{pre}"', pre, len(pre), None, [l[6:] for l in fl], printed=[])))
    printed = []
    for line in [l for l in tr2 if l.startswith("trie: each")]:
        m = EACH.match(line)
        node = int(m.group(2))
        if m.group(3):
            printed.append(m.group(1))
        frames.append((f'Below node {walked[-1]}, children are taken from a to z: node {node} is "{m.group(1)}", '
                       f'a word, printed in its turn.',
                       set(shown), path_of(nodes, node), node, [], set(wset),
                       panel(f"completing -p {pre}", f'each "{m.group(1)}"', m.group(1), len(m.group(1)), None,
                             [line[6:]], printed=list(printed))))
    assert printed == out2.split(), (printed, out2)

    for k, (cap, shown_k, path, here, made, wk, pn) in enumerate(frames):
        with steps.step(f, cap):
            draw_tree(f, nodes, pos, shown_k, wk, path, here, made)
            if pn["miss"] is not None:
                x, y = pos[stub[0]]
                f.line(x, y + R + 2, x, y + R + 24, "a", dash=True)
                f.text(x, y + R + 40, stub[1] + ": none", "ta", 12, "middle", 600, mono=True)
            f.text(PX, 40, pn["head"], "tm", 11.5)
            f.text(PX, 64, pn["cmd"], "t", 15, weight=700, mono=True)
            letters(f, PX, 80, pn["word"], pn["done"], pn["cur"], pn["miss"])
            f.text(PX, 136, "DS_TRACE=1 printed", "tm", 11)
            for i, t in enumerate(pn["trace"]):
                f.text(PX, 156 + i * 17, t, "t", 11.5, mono=True)
            if pn["printed"] is not None:
                f.text(PX, 248, "spell printed", "tm", 11)
                if pn["printed"]:
                    for i, wd in enumerate(pn["printed"]):
                        f.text(PX + i * 64, 270, wd, "ta", 13, weight=600, mono=True)
                else:
                    f.text(PX, 270, "nothing yet", "tm", 12)
    return f


# ------------------------------------------------------------------ the Bloom filter (05.02)

BADD = re.compile(r'^bloom: add "(\w+)":((?: \d+)+)$')
BTEST = re.compile(r'^bloom: test "(\w+)": (.*): (yes|no)$')


def bits0502(p):
    out, tr, stats = p.spell(["--algo=bloom", "--fp=0.1", "-d", "small.txt"], "cat cot hat\n")
    st = next(s for s in stats if s.startswith("stats: bloom:"))
    m_bits = int(re.search(r"bits (\d+)", st).group(1))
    k = int(re.search(r"hashes (\d+)", st).group(1))
    dictionary = SMALL.split()
    f = Fig("f0502a", f"A Bloom filter of {m_bits} bits, {k} places a word: four words go in, three are tested", 364)
    W = 25
    X0 = (640 - m_bits * W) / 2
    BY = 62

    f.text(24, 22, f"--fp=0.1 for {len(dictionary)} words: bloom_init makes the filter m = {m_bits} bits "
                   f"(a prime), k = {k} places a word", "tm", 11)
    for i in range(m_bits):
        f.text(X0 + i * W + (W - 3) / 2, BY - 8, str(i), "tm", 9.5, "middle", mono=True)
    f.text(24, 250, "added: the bits each word set", "tm", 11)
    f.text(372, 250, "tested", "tm", 11)
    ly = 350
    for x, cls, tcls, v, label in ((24, "m f", "tm", "0", "a bit still 0"), (150, "s fs", "t", "1", "a bit set to 1"),
                                    (278, "a af", "ta", "1", "a bit of this step's word")):
        f.rect(x, ly - 14, 18, 18, cls, 3)
        f.text(x + 9, ly, v, tcls, 11, "middle", 600, mono=True)
        f.text(x + 26, ly, label, "tm", 11)

    on, added, tested, frames = set(), [], [], []
    setters = {}
    frames.append((f"An empty filter: {m_bits} bits, all 0. Each word will set {k} of them.", None, [], [], set(),
                   False))
    for line in tr:
        m = BADD.match(line)
        if m:
            word, places = m.group(1), [int(x) for x in m.group(2).split()]
            assert len(places) == k
            already = [b for b in places if b in on]
            on |= set(places)
            for b in places:
                setters.setdefault(b, []).append(word)
            added.append((word, places))
            cap = (f'Adding "{word}": its hash picks bits {", ".join(map(str, places))}, and all {k} are set to 1'
                   + (f" ({', '.join(map(str, sorted(set(already))))} {'was' if len(set(already)) == 1 else 'were'} 1 already)."
                      if already else "."))
            frames.append((cap, ("add", word, places), list(added), [], set(on), False))
            continue
        m = BTEST.match(line)
        if m:
            word, looked, yes = m.group(1), [], m.group(3) == "yes"
            for part in m.group(2).split(", "):
                b, state = part.split()
                looked.append((int(b), state == "on"))
                assert (int(b) in on) == (state == "on"), line
            tested.append((word, yes))
            if not yes:
                off = looked[-1][0]
                cap = (f'Testing "{word}": bit {off} is 0. "{word}" was never added, certainly: spell prints it. '
                       f"The test stops at the first 0.")
            elif word in dictionary:
                cap = f'Testing "{word}": all {k} of its bits are 1. "{word}" is probably a word, and it is one.'
            else:
                cap = (f'Testing "{word}": all {k} bits are 1, so the filter says probably a word. It is not: '
                       f"other words set those bits. A false positive.")
            frames.append((cap, ("test", word, looked, yes), list(added), list(tested), set(on),
                           word not in dictionary and yes))

    assert out.split() == [w for w, y in tested if not y]

    for cap, act, adds, tests, onk, fpos in frames:
        with steps.step(f, cap):
            hit = {}
            if act and act[0] == "add":
                hit = {b: True for b in act[2]}
            elif act:
                hit = {b: v for b, v in act[2]}
            for i in range(m_bits):
                x = X0 + i * W
                if i in hit and hit[i] and act[0] == "add":
                    cls, tcls = "a af", "ta"
                elif i in hit and hit[i]:
                    cls, tcls = "a af", "ta"
                elif i in hit:
                    cls, tcls = "a f", "ta"
                elif i in onk:
                    cls, tcls = "s fs", "t"
                else:
                    cls, tcls = "m f", "tm"
                f.rect(x, BY, W - 3, 28, cls, 3, dash=i in hit and not hit[i])
                f.text(x + (W - 3) / 2, BY + 19, "1" if i in onk else "0", tcls, 12, "middle", 600, mono=True)
            if act:
                word = act[1]
                bw = max(70, tw(word, 15, True) + 30)
                bx, by = 320 - bw / 2, 150
                f.rect(bx, by, bw, 32, "a af" if act[0] == "add" else "s f", 6)
                f.text(320, by + 21, word, "ta" if act[0] == "add" else "t", 15, "middle", 700, mono=True)
                f.text(bx - 10, by + 21, "add" if act[0] == "add" else "test", "tm", 11.5, "end")
                for b in hit:
                    cx = X0 + b * W + (W - 3) / 2
                    f.line(320 + (cx - 320) * 0.18, by - 2, cx, BY + 32, "a" if hit[b] else "a", arrow=True,
                           dash=not hit[b])
                if act[0] == "test":
                    if not act[3]:
                        res, cls = f"bit {act[2][-1][0]} is 0: certainly not a word", "ta"
                    elif fpos:
                        res, cls = "all 1: probably a word (it is not)", "ta"
                    else:
                        res, cls = "all 1: probably a word", "t"
                    f.text(320, by + 52, res, cls, 12, "middle", 600)
                    if fpos:
                        who = "; ".join(f"{b} by {' and '.join(setters[b])}" for b, _ in act[2])
                        f.text(320, by + 70, "set " + who, "tm", 10.5, "middle", mono=True)
                else:
                    f.text(320, by + 52, "bits " + " ".join(map(str, act[2])), "tm", 11.5, "middle", mono=True)
            # what has gone in, and what has been tested
            for i, (w, pl) in enumerate(adds):
                y = 268 + i * 16
                f.text(24, y, w, "t", 11, weight=600, mono=True)
                f.text(70, y, " ".join(map(str, pl)), "t", 11, mono=True)
            for i, (w, yes) in enumerate(tests):
                y = 268 + i * 16
                wrong = yes and w not in dictionary
                verdict = ("probably a word" if yes and w in dictionary else
                           "probably a word: wrong" if yes else "certainly not: printed")
                f.text(372, y, w, "ta" if wrong else "t", 11, weight=600, mono=True)
                f.text(410, y, verdict, "ta" if wrong else "t", 11)
    return f


# ------------------------------------------------------------------ the edit-distance table (05.03)

ROW = re.compile(r"^edit: row (\d+) (.): ([\d ]+)$")


def table0503(p):
    a, b = "kitten", "sitting"
    out, tr, _ = p.spell(["--distance", a, b])
    rows = []
    for line in tr:
        m = ROW.match(line)
        if m:
            assert int(m.group(1)) == len(rows)
            rows.append([int(x) for x in m.group(3).split()])
    assert len(rows) == len(b) + 1 and all(len(r) == len(a) + 1 for r in rows)
    dist = rows[-1][-1]
    assert int(out) == dist and f"edit: distance {dist}" in tr

    # the cheapest alignment, back from the last cell (diagonal first when it ties)
    path, i, j = [(len(b), len(a))], len(b), len(a)
    while i or j:
        if i and j and rows[i][j] == rows[i - 1][j - 1] + (a[j - 1] != b[i - 1]):
            i, j = i - 1, j - 1
        elif i and rows[i][j] == rows[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1
        path.append((i, j))
    path = path[::-1]
    on_path = {}
    for (i0, j0), (i1, j1) in zip(path, path[1:]):
        on_path[i1] = (i1, j1, i0, j0)

    f = Fig("f0503a", f"The edit-distance table for {a} and {b}, filled a row at a time: the answer is {dist}", 330)
    CW, CH = 36, 28
    TX, TY = 76, 56
    f.text(TX + CW * (len(a) + 1) / 2, 20, f"a = {a}: a column for each letter", "tm", 11, "middle")
    ym = TY + CH * (len(b) + 1) / 2
    f.add(f'<text class="tm" x="30" y="{ym}" font-size="11" text-anchor="middle" '
          f'transform="rotate(-90 30 {ym})">b = {b}: a row for each letter</text>')
    f.text(TX + CW / 2, TY - 10, "-", "tm", 12, "middle", mono=True)
    for j, ch in enumerate(a):
        f.text(TX + CW * (j + 1) + CW / 2, TY - 10, ch, "t", 13, "middle", 600, mono=True)
    f.text(TX - 14, TY + CH / 2 + 4, "-", "tm", 12, "middle", mono=True)
    for i, ch in enumerate(b):
        f.text(TX - 14, TY + CH * (i + 1) + CH / 2 + 4, ch, "t", 13, "middle", 600, mono=True)
    for i in range(len(b) + 1):
        for j in range(len(a) + 1):
            f.rect(TX + CW * j, TY + CH * i, CW - 3, CH - 3, "m f", 3, dash=True)
    PX = 372

    def cell(i, j, cls, tcls, v=None):
        f.rect(TX + CW * j, TY + CH * i, CW - 3, CH - 3, cls, 3)
        f.text(TX + CW * j + (CW - 3) / 2, TY + CH * i + CH / 2 + 3, str(rows[i][j] if v is None else v), tcls, 12.5,
               "middle", 600, mono=True)

    for r in range(len(rows) + 1):
        final = r == len(rows)
        if r == 0:
            cap = (f"Row 0, before any letter of {b}: from nothing to the first j letters of {a} is j insertions: "
                   + " ".join(map(str, rows[0])) + ".")
        elif not final:
            i1, j1, i0, j0 = on_path[r]
            cap = (f"Row {r}, for the letter {b[r - 1]} of {b}: it starts at {r} ({r} deletion{'s' if r > 1 else ''}), "
                   f"and each other cell "
                   f"is the cheapest of three, from the row above and the cell to its left: "
                   + " ".join(map(str, rows[r])) + ".")
        else:
            cap = (f"The last cell is the distance: {dist}. Back from it, the cheapest way: "
                   f"k to s, e to i, and a g on the end.")
        with steps.step(f, cap):
            last = len(rows) - 1 if final else r
            for i in range(last + 1):
                for j in range(len(a) + 1):
                    if final and (i, j) in path:
                        cls, tcls = ("a fa", "f") if (i, j) == path[-1] else ("a af", "ta")
                    elif i == r:
                        cls, tcls = "a f", "ta"
                    else:
                        cls, tcls = "s f", "t"
                    cell(i, j, cls, tcls)
            f.text(PX, 40, "row 0" if r == 0 else ("the answer" if final else f"row {r}: b's letter {b[r - 1]}"),
                   "t", 14, weight=700)
            if r == 0:
                f.text(PX, 64, "j letters from nothing: j insertions", "tm", 11.5)
                f.text(PX, 82, "0 1 2 3 4 5 6", "t", 12, mono=True)
            elif not final:
                ii, jj = on_path[r][:2]          # the cell of this row on the cheapest path
                assert ii == r and jj >= 1
                up = rows[ii - 1][jj] + 1
                left = rows[ii][jj - 1] + 1
                same = a[jj - 1] == b[ii - 1]
                diag = rows[ii - 1][jj - 1] + (0 if same else 1)
                best = min(up, left, diag)
                assert best == rows[ii][jj]
                cell(ii, jj, "a fa", "f")
                for (ni, nj), v in (((ii - 1, jj), up), ((ii, jj - 1), left), ((ii - 1, jj - 1), diag)):
                    f.rect(TX + CW * nj - 3, TY + CH * ni - 3, CW + 3, CH + 3, "a" if v == best else "m", 5,
                           dash=v != best)
                f.text(PX, 64, f"the cell for {b[:ii]} and {a[:jj]}:", "tm", 11.5)
                lines = [(f"above, plus 1", up), (f"left, plus 1", left),
                         (f"diagonal, plus {0 if same else 1} ({a[jj - 1]} {'=' if same else 'vs'} {b[ii - 1]})", diag)]
                for k2, (s, v) in enumerate(lines):
                    f.text(PX, 88 + k2 * 20, s, "ta" if v == best else "t", 12)
                    f.text(PX + 214, 88 + k2 * 20, str(v), "ta" if v == best else "t", 12.5, "end", 600, mono=True)
                f.line(PX, 146, PX + 214, 146, "m")
                f.text(PX, 164, "the smallest", "t", 12, weight=600)
                f.text(PX + 214, 164, str(best), "ta", 12.5, "end", 700, mono=True)
            else:
                f.text(PX, 64, f"distance({a}, {b}) = {dist}", "ta", 12.5, weight=600, mono=True)
                edits = []
                for (i0, j0), (i1, j1) in zip(path, path[1:]):
                    if i1 > i0 and j1 > j0:
                        if a[j1 - 1] != b[i1 - 1]:
                            edits.append(f"{a[j1 - 1]} to {b[i1 - 1]}: replace")
                    elif i1 > i0:
                        edits.append(f"{b[i1 - 1]} on the end: insert")
                    else:
                        edits.append(f"{a[j1 - 1]} left out: delete")
                for k2, s in enumerate(edits):
                    f.text(PX, 92 + k2 * 20, s, "t", 12)
                f.text(PX, 104 + len(edits) * 20, "each step of the path is one edit,", "tm", 11)
                f.text(PX, 120 + len(edits) * 20, "or a letter kept (diagonal, +0)", "tm", 11)
            f.text(PX, 232, "rows filled: " + str(min(r, len(rows) - 1) + 1) + " of " + str(len(rows)), "tm", 11)
            f.text(PX, 250, "rows kept in memory: 2", "tm", 11)
    f.text(24, 316, "Each cell: the distance between the first i letters of b and the first j letters of a.", "tm", 11)
    return f


def walk0503(p):
    out, tr, _ = p.spell(["-s", "-e", "1", "-d", "small.txt"], "cst\n")
    nodes, words = build_tree(tr)
    word = re.match(r"^(\w+):", out).group(1)
    pos = layout(nodes, 60, 150, 70, 64)
    visited, labels, cut, found = {0}, {}, set(), []
    labels[0] = [("- " + " ".join(word), "tm"), ("0 " + " ".join(str(i + 1) for i in range(len(word))), "t")]
    for line in tr:
        m = NEAR.match(line)
        if not m:
            continue
        node = int(m.group(2))
        assert prefix_of(nodes, node) == m.group(1)
        visited.add(node)
        row, mn = m.group(3), int(m.group(4))
        tag = ""
        cls = "t"
        if m.group(5) == ", pruned":
            cut.add(node)
            tag, cls = f"min {mn}: pruned", "ta"
        elif m.group(6):
            found.append(m.group(1))
            tag, cls = f"a word at {m.group(6)}", "ta"
        else:
            tag = f"min {mn}"
        labels[node] = [(row, "t"), (tag, cls)]
    assert out.split()[1:] == found, (out, found)
    dim = set(nodes) - visited
    f = Fig("f0503b", f'Suggestions for "{word}" within one edit: the walk down the trie, a row of the table at each node',
            344)
    f.text(24, 22, f'printf \'{word}\\n\' | bin/spell -s -e 1 -d small.txt   (car cart cat dog)', "tm", 11, mono=True)
    draw_tree(f, nodes, pos, set(nodes), words, path=[], dim=dim, labels=labels)
    for n in found:
        node = next(k for k in nodes if prefix_of(nodes, k) == n)
        x, y = pos[node]
        f.add(f'<circle class="a" cx="{x}" cy="{y}" r="{R + 4}" stroke-width="2.5"/>')
    X = 486
    f.text(X, 60, "each node's row:", "t", 12, weight=600)
    f.text(X, 78, "the distances from the", "tm", 11)
    f.text(X, 92, f'starts of "{word}" to the', "tm", 11)
    f.text(X, 106, "letters on the way down", "tm", 11)
    f.text(X, 134, "last cell within 1, and a", "tm", 11)
    f.text(X, 148, "word ends: a suggestion", "tm", 11)
    f.text(X, 176, "no cell within 1: pruned,", "tm", 11)
    f.text(X, 190, "nothing below is visited", "tm", 11)
    f.text(X, 218, "dashed: never visited", "tm", 11)
    f.text(X, 252, "spell printed", "tm", 11)
    f.text(X, 272, out.strip(), "ta", 13, weight=600, mono=True)
    return f


# ------------------------------------------------------------------ main

FIGS = [("05.01", "05.01-trie", trie0501, True), ("05.02", "05.02-bits", bits0502, True),
        ("05.03", "05.03-table", table0503, True), ("05.03", "05.03-walk", walk0503, False)]


def main():
    sys.dont_write_bytecode = True
    from archmap import check
    paths = []
    with tempfile.TemporaryDirectory(prefix="figs05-") as tmp:
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
