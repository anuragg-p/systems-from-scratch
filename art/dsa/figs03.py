"""Figures for dsa module 03, A text editor: edit (lessons 03.01-03.05).

    python3 art/dsa/figs03.py [NAME ...]

Every frame comes from a run of the real editor. The script writes the project as it stands at
each lesson (./learn files dsa --at NN.LL), builds it, and replays a short script of edits on a
12-byte file with bin/edit --replay, DS_TRACE=1 and DS_STATS=1. It makes the same edits here, on a
model of the few lines of lib/ the lesson builds, and stops with an error unless the model prints
the very same trace lines (every insert, erase, rotation and undo, with the structure's whole
state after it) and the same counts as the real program. The frames are drawn from the model,
which can also stop in the middle of a call (the gap carried across, a node not yet rotated).

The running example, the same in every lesson: the file "the cat sat\\n" (12 bytes), and

  03.01-shift   flat array   goto 4, type "fat ", goto 15, type "!"
  03.02-gap     gap buffer   goto 4, type "fat ", goto 15, type "!", back 1
  03.03-stacks  undo         on "the cat\\n": goto 4, type "fat ", goto end, back 4, undo, undo,
                             redo, goto 0, type ">", redo
  03.04-pieces  piece list   goto 4, type "fat ", goto 15, type "!", back 1, type "."
  03.05-tree    piece tree   the same edits as 03.04
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
MOD = "03-edit"

CAT = b"the cat sat\n"


# ------------------------------------------------------------------ the real program

_projects = {}
_tmp = tempfile.mkdtemp(prefix="figs03-")
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


def replay(at, text, script, algo=None):
    """bin/edit [--algo=algo] --replay of `script` (a list of lines) on a file holding `text`, in
    the project at `at`, with DS_TRACE=1 and DS_STATS=1: (stdout, the trace lines, the stats as
    {"gap buffer": {"bytes moved": 16, ...}, ...})."""
    d = project(at)
    path = os.path.join(d, "fig.txt")
    with open(path, "wb") as f:
        f.write(text)
    env = {k: v for k, v in os.environ.items() if not k.startswith("DS_")}
    env.update(LC_ALL="C", DS_STATS="1", DS_TRACE="1")
    argv = [os.path.join(d, "bin", "edit")] + ([f"--algo={algo}"] if algo else []) + ["--replay", "-", path]
    r = subprocess.run(argv, input="".join(s + "\n" for s in script).encode(), capture_output=True, cwd=d,
                       env=env)
    if r.returncode != 0:
        raise SystemExit(f"figs03: {argv}: exit {r.returncode}: {r.stderr.decode()}")
    trace, stats = [], {}
    for line in r.stderr.decode().splitlines():
        if line.startswith("trace: "):
            trace.append(line)
        m = re.match(r"stats: ([^:]+): (.*)$", line)
        if m:
            stats[m.group(1)] = {p.rsplit(" ", 1)[0]: int(p.rsplit(" ", 1)[1]) for p in m.group(2).split(", ")}
    return r.stdout, trace, stats


def same(what, mine, real):
    if mine != real:
        if isinstance(mine, list) and isinstance(real, list):
            for k, (a, b) in enumerate(zip(mine, real)):
                if a != b:
                    raise SystemExit(f"figs03: {what}: line {k + 1}:\n  model: {a}\n  real:  {b}")
            raise SystemExit(f"figs03: {what}: the model has {len(mine)} lines, the real program {len(real)}")
        raise SystemExit(f"figs03: {what}: the model gives {mine!r}, the real program {real!r}")


def cstr(b, cut=40):
    """Bytes as text.c's text_trace_bytes writes them."""
    out = []
    for c in b[:cut]:
        if c == 10:
            out.append("\\n")
        elif c == 9:
            out.append("\\t")
        elif c in (34, 92):
            out.append("\\" + chr(c))
        elif c < 32 or c >= 127:
            out.append("\\x%02x" % c)
        else:
            out.append(chr(c))
    return '"' + "".join(out) + ('"...' if len(b) > cut else '"')


# ------------------------------------------------------------------ models of lib/

class Flat:
    """flat.c: the text in one block, exactly as full as the file when opened."""
    name = "flat array"

    def __init__(self, text, events):
        self.data, self.cap, self.ev = bytearray(text), len(text), events
        self.st = {"bytes loaded": len(text), "inserts": 0, "erases": 0, "bytes moved": 0, "grows": 0,
                   "bytes copied": 0}
        self.trace = []

    def insert(self, pos, s):
        n, length = len(s), len(self.data)
        if length + n > self.cap:
            old = self.cap
            self.cap = max(2 * self.cap, length + n)
            self.st["grows"] += 1
            self.st["bytes copied"] += length
            self.ev.append(("grow", {"old": old, "cap": self.cap, "data": bytes(self.data)}))
        before = bytes(self.data)
        self.data[pos:pos] = s
        moved = length - pos
        self.st["inserts"] += 1
        self.st["bytes moved"] += moved
        self.trace.append(f"trace: flat array: insert {pos} {cstr(s)}: moved {moved} | {cstr(bytes(self.data))}")
        self.ev.append(("insert", {"pos": pos, "s": s, "moved": moved, "before": before, "data": bytes(self.data),
                                   "cap": self.cap, "st": dict(self.st)}))

    def erase(self, pos, n):
        moved = len(self.data) - pos - n
        del self.data[pos:pos + n]
        self.st["erases"] += 1
        self.st["bytes moved"] += moved
        self.trace.append(f"trace: flat array: erase {pos} {n}: moved {moved} | {cstr(bytes(self.data))}")

    def read(self, pos, n):
        return bytes(self.data[pos:pos + n])

    def text(self):
        return bytes(self.data)


GAP_MIN = 16


class Gap:
    """gap.c: one block, the text before the gap at its start, the text after it at its end."""
    name = "gap buffer"

    def __init__(self, text, events):
        self.cap = len(text) + GAP_MIN
        self.data = bytearray(text) + bytearray(GAP_MIN)
        self.gap, self.end, self.len, self.ev = len(text), self.cap, len(text), events
        self.st = {"bytes loaded": len(text), "inserts": 0, "erases": 0, "bytes moved": 0, "grows": 0,
                   "bytes copied": 0}
        self.trace = []

    def snap(self):
        return {"before": bytes(self.data[:self.gap]), "gapsize": self.end - self.gap,
                "after": bytes(self.data[self.end:]), "gap": self.gap, "end": self.end, "cap": self.cap,
                "st": dict(self.st)}

    def move_gap(self, pos):
        k = 0
        start = self.snap()
        if pos < self.gap:
            k = self.gap - pos
            self.data[self.end - k:self.end] = self.data[pos:self.gap]
            self.gap, self.end = pos, self.end - k
        elif pos > self.gap:
            k = pos - self.gap
            self.data[self.gap:self.gap + k] = self.data[self.end:self.end + k]
            self.gap, self.end = pos, self.end + k
        self.st["bytes moved"] += k
        if k:
            self.ev.append(("move", {"from": start, "to": self.snap(), "k": k, "pos": pos}))
        return k

    def grow(self, n):
        after = self.cap - self.end
        cap = max(2 * self.cap, self.len + n + GAP_MIN)
        data = bytearray(cap)
        data[:self.gap] = self.data[:self.gap]
        data[cap - after:] = self.data[self.end:]
        self.data, self.end, self.cap = data, cap - after, cap
        self.st["grows"] += 1
        self.st["bytes copied"] += self.len

    def line(self, what, moved):
        s = self.snap()
        return (f"trace: gap buffer: {what}: moved {moved} | {cstr(s['before'])} [{s['gapsize']}] "
                f"{cstr(s['after'])}")

    def insert(self, pos, s):
        n = len(s)
        moved = self.move_gap(pos)
        if self.end - self.gap < n:
            self.grow(n)
        start = self.snap()
        self.data[self.gap:self.gap + n] = s
        self.gap += n
        self.len += n
        self.st["inserts"] += 1
        self.trace.append(self.line(f"insert {pos} {cstr(s)}", moved))
        self.ev.append(("insert", {"from": start, "to": self.snap(), "pos": pos, "s": s, "moved": moved}))

    def erase(self, pos, n):
        moved = self.move_gap(pos)
        start = self.snap()
        gone = bytes(self.data[self.end:self.end + n])
        self.end += n
        self.len -= n
        self.st["erases"] += 1
        self.trace.append(self.line(f"erase {pos} {n}", moved))
        self.ev.append(("erase", {"from": start, "to": self.snap(), "pos": pos, "n": n, "gone": gone,
                                  "moved": moved}))

    def read(self, pos, n):
        return self.text()[pos:pos + n]

    def text(self):
        return bytes(self.data[:self.gap]) + bytes(self.data[self.end:])


ORIG, ADD = "orig", "add"


class Pieces:
    """pieces.c: the file (never changed), the add buffer (only added to), and a list of spans."""
    name = "piece list"

    def __init__(self, text, events):
        self.orig, self.add = bytes(text), bytearray()
        self.list = [[ORIG, 0, len(text)]] if text else []
        self.len, self.ev = len(text), events
        self.st = {"bytes mapped": len(text), "bytes loaded": 0, "bytes added": 0, "inserts": 0, "erases": 0,
                   "pieces": len(self.list), "pieces walked": 0}
        self.trace = []

    def bytes_of(self, p):
        return (self.orig if p[0] == ORIG else bytes(self.add))[p[1]:p[1] + p[2]]

    def snap(self):
        return {"pieces": [tuple(p) for p in self.list], "add": bytes(self.add), "orig": self.orig}

    def find(self, pos):
        """(index of the piece holding pos or len(list), off): pieces.c's find()."""
        for i, p in enumerate(self.list):
            self.st["pieces walked"] += 1
            if pos < p[2]:
                return i, pos
            pos -= p[2]
        return len(self.list), pos

    def line(self, what, walked):
        ps = "".join(f" | {p[0]} {p[1]}+{p[2]} {cstr(self.bytes_of(p))}" for p in self.list)
        return f"trace: piece list: {what}: walked {walked}{ps}"

    def insert(self, pos, s):
        w0 = self.st["pieces walked"]
        start = len(self.add)
        self.add += s
        n = len(s)
        i, off = self.find(pos)
        prev = self.list[i - 1] if i > 0 else None
        if off == 0 and prev is not None and prev[0] == ADD and prev[1] + prev[2] == start:
            prev[2] += n
            how = "grow"
        elif off == 0:
            self.list.insert(i, [ADD, start, n])
            self.st["pieces"] += 1
            how = "between"
        else:
            x = self.list[i]
            rest = [x[0], x[1] + off, x[2] - off]
            x[2] = off
            self.list[i + 1:i + 1] = [[ADD, start, n], rest]
            self.st["pieces"] += 2
            how = "cut"
        self.len += n
        self.st["bytes added"] += n
        self.st["inserts"] += 1
        walked = self.st["pieces walked"] - w0
        self.trace.append(self.line(f"insert {pos} {cstr(s)}", walked))
        self.ev.append(("insert", dict(self.snap(), pos=pos, s=s, how=how, walked=walked, start=start)))

    def erase(self, pos, n):
        w0 = self.st["pieces walked"]
        left = n
        i, off = self.find(pos)
        if off > 0 and off + left < self.list[i][2]:
            x = self.list[i]
            self.list.insert(i + 1, [x[0], x[1] + off + left, x[2] - off - left])
            self.st["pieces"] += 1
            x[2] = off
            left = 0
        elif off > 0:
            x = self.list[i]
            left -= x[2] - off
            x[2] = off
            i += 1
        while left > 0 and left >= self.list[i][2]:
            left -= self.list[i][2]
            del self.list[i]
            self.st["pieces"] -= 1
        if left > 0:
            self.list[i][1] += left
            self.list[i][2] -= left
        self.len -= n
        self.st["erases"] += 1
        walked = self.st["pieces walked"] - w0
        self.trace.append(self.line(f"erase {pos} {n}", walked))
        self.ev.append(("erase", dict(self.snap(), pos=pos, n=n, walked=walked)))

    def read(self, pos, n):
        i, off = self.find(pos)
        out = b""
        while len(out) < n:
            out += self.bytes_of(self.list[i])[off:off + n - len(out)]
            off, i = 0, i + 1
        return out

    def text(self):
        return b"".join(self.bytes_of(p) for p in self.list)


class Node:
    __slots__ = ("left", "right", "height", "sum", "span")

    def __init__(self, span):
        self.left = self.right = None
        self.height, self.sum, self.span = 1, span[2], list(span)


def height(n):
    return n.height if n else 0


def tsum(n):
    return n.sum if n else 0


def update(n):
    n.height = 1 + max(height(n.left), height(n.right))
    n.sum = tsum(n.left) + n.span[2] + tsum(n.right)


class PTree:
    """ptree.c: the same buffers, the pieces in an AVL tree, each node the length of text under it.
    Besides the trace, it records snapshots in the middle of a call: after a cut, at a node whose
    subtrees are two apart (before it is mended), and after each rotation."""
    name = "piece tree"

    def __init__(self, text, events):
        self.orig, self.add = bytes(text), bytearray()
        self.root = Node((ORIG, 0, len(text))) if text else None
        self.len, self.ev = len(text), events
        self.st = {"bytes mapped": len(text), "bytes loaded": 0, "bytes added": 0, "inserts": 0, "erases": 0,
                   "pieces": 1 if text else 0, "nodes visited": 0, "rotations": 0}
        self.trace, self.pending = [], []
        self.phase = None

    def bytes_of(self, span):
        return (self.orig if span[0] == ORIG else bytes(self.add))[span[1]:span[1] + span[2]]

    def label(self, span):
        return f"{span[0]} {span[1]}+{span[2]}"

    # a snapshot: the tree from the root as nested tuples (left, span, right), with true sums and
    # heights; `swap` puts a subtree's new root in place of its old one the first time the walk
    # meets it (the parent's link is set only when the recursion returns)
    def shape(self, swap=None):
        done = [False]

        def walk(n):
            if n is None:
                return None
            if swap and n is swap[0] and not done[0]:
                done[0] = True
                n = swap[1]
            left, right = walk(n.left), walk(n.right)
            s = (left[3] if left else 0) + n.span[2] + (right[3] if right else 0)
            h = 1 + max(left[4] if left else 0, right[4] if right else 0)
            return (left, tuple(n.span), right, s, h, id(n))
        return walk(self.root)

    def snapshot(self, kind, swap=None, **info):
        self.pending.append((kind, self.shape(swap), dict(info, phase=self.phase)))

    def find(self, n, pos):
        while n is not None:
            self.st["nodes visited"] += 1
            left = tsum(n.left)
            if pos < left:
                n = n.left
            elif pos < left + n.span[2]:
                return n, pos - left
            else:
                pos -= left + n.span[2]
                n = n.right
        return None, 0

    def rotate_right(self, n):
        x = n.left
        self.trace.append(f"trace: piece tree: rotate right at {self.label(n.span)}")
        n.left = x.right
        x.right = n
        update(n)
        update(x)
        self.st["rotations"] += 1
        return x

    def rotate_left(self, n):
        x = n.right
        self.trace.append(f"trace: piece tree: rotate left at {self.label(n.span)}")
        n.right = x.left
        x.left = n
        update(n)
        update(x)
        self.st["rotations"] += 1
        return x

    def balance(self, n):
        update(n)
        b = height(n.left) - height(n.right)
        if b > 1 or b < -1:
            self.snapshot("unbalanced", at=tuple(n.span), hl=height(n.left), hr=height(n.right))
        if b > 1:
            if height(n.left.left) < height(n.left.right):
                was = n.left
                n.left = self.rotate_left(n.left)
                self.snapshot("rotate", dir="left", at=tuple(was.span), up=tuple(n.left.span), inner=True)
            r = self.rotate_right(n)
            self.snapshot("rotate", swap=(n, r), dir="right", at=tuple(n.span), up=tuple(r.span), inner=False)
            return r
        if b < -1:
            if height(n.right.right) < height(n.right.left):
                was = n.right
                n.right = self.rotate_right(n.right)
                self.snapshot("rotate", dir="right", at=tuple(was.span), up=tuple(n.right.span), inner=True)
            r = self.rotate_left(n)
            self.snapshot("rotate", swap=(n, r), dir="left", at=tuple(n.span), up=tuple(r.span), inner=False)
            return r
        return n

    def insert_at(self, n, pos, x):
        if n is None:
            return x
        self.st["nodes visited"] += 1
        left = tsum(n.left)
        if pos <= left:
            n.left = self.insert_at(n.left, pos, x)
        else:
            n.right = self.insert_at(n.right, pos - left - n.span[2], x)
        return self.balance(n)

    def remove_min(self, n, out):
        self.st["nodes visited"] += 1
        if n.left is None:
            out.append(n)
            return n.right
        n.left = self.remove_min(n.left, out)
        return self.balance(n)

    def remove_at(self, n, pos):
        self.st["nodes visited"] += 1
        left = tsum(n.left)
        if pos < left:
            n.left = self.remove_at(n.left, pos)
        elif pos > left:
            n.right = self.remove_at(n.right, pos - left - n.span[2])
        else:
            left_t, right_t = n.left, n.right
            self.st["pieces"] -= 1
            if left_t is None:
                return right_t
            if right_t is None:
                return left_t
            out = []
            right_t = self.remove_min(right_t, out)
            nxt = out[0]
            nxt.left, nxt.right = left_t, right_t
            n = nxt
        return self.balance(n)

    def set_len(self, n, pos, length):
        self.st["nodes visited"] += 1
        left = tsum(n.left)
        if pos < left:
            self.set_len(n.left, pos, length)
        elif pos > left:
            self.set_len(n.right, pos - left - n.span[2], length)
        else:
            n.span[2] = length
        n.sum = tsum(n.left) + n.span[2] + tsum(n.right)

    def new_node(self, span):
        self.st["pieces"] += 1
        return Node(span)

    def cut(self, pos):
        if pos >= self.len:
            return
        n, off = self.find(self.root, pos)
        if off == 0:
            return
        rest = (n.span[0], n.span[1] + off, n.span[2] - off)
        whole = tuple(n.span)
        self.set_len(self.root, pos - off, off)
        self.phase = "cut"
        self.root = self.insert_at(self.root, pos, self.new_node(rest))
        self.snapshot("cut", piece=whole, at=pos, rest=rest)
        self.phase = None

    def tree_text(self, n):
        if n is None:
            return "."
        return (f"({self.tree_text(n.left)} {self.label(n.span)} {cstr(self.bytes_of(n.span))} "
                f"{self.tree_text(n.right)})")

    def line(self, what, visited):
        return f"trace: piece tree: {what}: visited {visited} | {self.tree_text(self.root)}"

    def insert(self, pos, s):
        v0 = self.st["nodes visited"]
        self.pending = []
        start = len(self.add)
        self.add += s
        n = len(s)
        before, off = self.find(self.root, pos - 1) if pos > 0 else (None, 0)
        if (before is not None and off + 1 == before.span[2] and before.span[0] == ADD
                and before.span[1] + before.span[2] == start):
            was = tuple(before.span)
            self.set_len(self.root, pos - before.span[2], before.span[2] + n)
            how = ("grow", was)
        else:
            self.cut(pos)
            self.phase = "insert"
            self.root = self.insert_at(self.root, pos, self.new_node((ADD, start, n)))
            self.phase = None
            how = ("node", (ADD, start, n))
        self.len += n
        self.st["bytes added"] += n
        self.st["inserts"] += 1
        visited = self.st["nodes visited"] - v0
        self.trace.append(self.line(f"insert {pos} {cstr(s)}", visited))
        self.snapshot("done")
        self.ev.append(("insert", {"pos": pos, "s": s, "how": how, "visited": visited, "steps": self.pending,
                                   "add": bytes(self.add), "st": dict(self.st)}))

    def erase(self, pos, n):
        v0 = self.st["nodes visited"]
        self.pending = []
        self.cut(pos)
        self.cut(pos + n)
        left = n
        gone = []
        while left > 0:
            x, _ = self.find(self.root, pos)
            gone.append(tuple(x.span))
            left -= x.span[2]
            self.phase = "remove"
            self.root = self.remove_at(self.root, pos)
            self.phase = None
        self.len -= n
        self.st["erases"] += 1
        visited = self.st["nodes visited"] - v0
        self.trace.append(self.line(f"erase {pos} {n}", visited))
        self.snapshot("done")
        self.ev.append(("erase", {"pos": pos, "n": n, "gone": gone, "visited": visited, "steps": self.pending,
                                  "add": bytes(self.add), "st": dict(self.st)}))

    def copy(self, n, frm, to):
        if n is None or frm >= to:
            return b""
        self.st["nodes visited"] += 1
        left = tsum(n.left)
        r = left + n.span[2]
        out = b""
        if frm < left:
            out += self.copy(n.left, frm, min(to, left))
        if frm < r and to > left:
            a, b = max(frm, left), min(to, r)
            out += self.bytes_of(n.span)[a - left:b - left]
        if to > r:
            out += self.copy(n.right, max(frm - r, 0), to - r)
        return out

    def read(self, pos, n):
        return self.copy(self.root, pos, pos + n)

    def text(self):
        """The whole text, for the model's own use: not counted, as the real program does not read it."""
        v = self.st["nodes visited"]
        out = self.copy(self.root, 0, self.len) if self.root else b""
        self.st["nodes visited"] = v
        return out

    @property
    def stats(self):
        return dict(self.st, height=height(self.root))


class Undo:
    """undo.c: two stacks of edits."""

    def __init__(self, events):
        self.done, self.undone, self.typing, self.ev = [], [], False, events
        self.st = {"edits": 0, "undos": 0, "redos": 0, "bytes kept": 0}
        self.trace = []

    @staticmethod
    def shown(e):
        b = bytes(reversed(e["bytes"])) if e["backwards"] else bytes(e["bytes"])
        return b

    def line(self, what, e, how):
        self.trace.append(f"trace: undo: {what} {'erase' if e['erase'] else 'insert'} {e['pos']} "
                          f"{cstr(self.shown(e))}: {how} | done {len(self.done)}, undone {len(self.undone)}")

    def snap(self):
        return {"done": [(e["erase"], e["pos"], self.shown(e)) for e in self.done],
                "undone": [(e["erase"], e["pos"], self.shown(e)) for e in self.undone]}

    def note(self, erase, pos, s, typed):
        forgot = []
        while self.undone:
            e = self.undone.pop()
            forgot.append((e["erase"], e["pos"], self.shown(e)))
            self.st["bytes kept"] -= len(e["bytes"])
        top = self.done[-1] if self.done else None
        n = len(s)
        if (typed and self.typing and top is not None and top["erase"] == erase and
                (pos + n == top["pos"] if erase else top["pos"] + len(top["bytes"]) == pos)):
            top["bytes"] += bytes(reversed(s)) if erase else s
            self.st["bytes kept"] += n
            if erase:
                top["pos"] = pos
            self.line("note", top, "more of the same edit")
            how = "more"
        else:
            e = {"erase": erase, "pos": pos, "backwards": bool(typed and erase), "bytes": bytearray()}
            e["bytes"] += bytes(reversed(s)) if e["backwards"] else s
            self.st["bytes kept"] += n
            self.done.append(e)
            self.st["edits"] += 1
            self.line("note", e, "a new edit")
            how = "new"
        self.typing = typed
        self.ev.append(("note", dict(self.snap(), how=how, forgot=forgot)))

    def undo(self, text):
        self.typing = False
        if not self.done:
            self.ev.append(("undo-none", self.snap()))
            return None
        e = self.done.pop()
        if e["backwards"]:
            e["bytes"] = bytearray(reversed(e["bytes"]))
            e["backwards"] = False
        if e["erase"]:
            text.insert(e["pos"], bytes(e["bytes"]))
        else:
            text.erase(e["pos"], len(e["bytes"]))
        self.undone.append(e)
        self.st["undos"] += 1
        self.line("undo", e, "inserted again" if e["erase"] else "erased")
        self.ev.append(("undo", dict(self.snap(), edit=(e["erase"], e["pos"], bytes(e["bytes"])))))
        return (not e["erase"], e["pos"], bytes(e["bytes"]),
                e["pos"] + len(e["bytes"]) if e["erase"] else e["pos"])

    def redo(self, text):
        self.typing = False
        if not self.undone:
            self.ev.append(("redo-none", self.snap()))
            return None
        e = self.undone.pop()
        if e["erase"]:
            text.erase(e["pos"], len(e["bytes"]))
        else:
            text.insert(e["pos"], bytes(e["bytes"]))
        self.done.append(e)
        self.st["redos"] += 1
        self.line("redo", e, "erased again" if e["erase"] else "inserted again")
        self.ev.append(("redo", dict(self.snap(), edit=(e["erase"], e["pos"], bytes(e["bytes"])))))
        return (e["erase"], e["pos"], bytes(e["bytes"]),
                e["pos"] if e["erase"] else e["pos"] + len(e["bytes"]))


class Editor:
    """edit.c's replay(): the cursor is a byte of the text; every edit goes through the
    structure, and (from 03.03) is noted for undo. Each command's events are kept in turn."""

    def __init__(self, cls, text, with_undo):
        self.ev = []
        self.t = cls(text, self.ev)
        self.u = Undo(self.ev) if with_undo else None
        self.cursor = 0
        self.out = b""
        self.st = {"inserts": 0, "erases": 0, "bytes read": 0}
        self.commands = []          # (the command, its events, the text after it, the cursor)
        self.lines = []             # every trace line, in the order the real program prints them

    def insert(self, pos, s, typed):
        self.t.insert(pos, s)
        self._flush()
        self.st["inserts"] += 1
        if self.u:
            self.u.note(0, pos, s, typed)
            self._flush()

    def erase(self, pos, n, typed):
        s = self.t.read(pos, n)
        self.st["bytes read"] += len(s)
        self.t.erase(pos, n)
        self._flush()
        self.st["erases"] += 1
        if self.u:
            self.u.note(1, pos, s, typed)
            self._flush()

    def _flush(self):
        for src in (self.t, self.u):
            if src is not None and src.trace:
                self.lines += src.trace
                src.trace.clear()

    def run(self, script):
        self.lines = []
        for cmd in script:
            word, _, arg = cmd.partition(" ")
            start = len(self.ev)
            if self.u and word not in ("type", "back"):
                self.u.typing = False
            if word == "goto":
                self.cursor = len(self.t.text()) if arg == "end" else int(arg)
            elif word == "type":
                for c in arg.encode():
                    self.insert(self.cursor, bytes([c]), True)
                    self.cursor += 1
            elif word == "back":
                for _ in range(int(arg)):
                    if self.cursor == 0:
                        break
                    self.cursor -= 1
                    self.erase(self.cursor, 1, True)
            elif word in ("undo", "redo"):
                c = (self.u.undo if word == "undo" else self.u.redo)(self.t)
                self._flush()
                if c:
                    self.cursor = c[3]
            elif word == "print":
                self.out += self.t.text()
            else:
                raise SystemExit(f"figs03: the model has no command {word!r}")
            self.commands.append((cmd, self.ev[start:], self.t.text(), self.cursor))


def checked(at, cls, text, script, algo=None, with_undo=False):
    """The model's editor after `script`, checked against the real program at `at`."""
    out, trace, stats = replay(at, text, script, algo)
    ed = Editor(cls, text, with_undo)
    ed.run(script)
    same(f"{at} trace", ed.lines, trace)
    same(f"{at} output", ed.out, out)
    same(f"{at} {cls.name} stats", getattr(ed.t, "stats", ed.t.st), stats[cls.name])
    same(f"{at} edit stats", ed.st, stats["edit"])
    if with_undo:
        same(f"{at} undo stats", ed.u.st, stats["undo"])
    return ed




# ------------------------------------------------------------------ drawing helpers

STYLE = {
    "n": ("s f", "t", False),        # a byte of the text, a piece, a node
    "d": ("m f", "tm", False),       # out of play: muted
    "u": ("m f", "tm", True),        # empty room: dashed
    "a": ("a af", "ta", False),      # just moved: accent-soft
    "A": ("a fa", "f", False),       # what this step is about: accent
    "p": ("s fs", "t", False),       # set apart (code background)
}
MARK = {"n": "tm", "d": "tm", "u": "tm", "a": "ta", "A": "f", "p": "tm"}


def cell(f, x, y, w, h, c, kind="n", size=12):
    """One byte in a box: a newline as \\n, a space as a small open bracket at the foot."""
    cls, tcls, dash = STYLE[kind]
    f.rect(x, y, w, h, cls, 3, dash=dash)
    if c is None:
        return
    if c == 32:
        m, cx, by = MARK[kind], x + w / 2, y + h - 7
        f.add(f'<rect class="{m}" x="{cx - 4.5:g}" y="{by:g}" width="9" height="1.5"/>')
        f.add(f'<rect class="{m}" x="{cx - 4.5:g}" y="{by - 3.5:g}" width="1.5" height="5"/>')
        f.add(f'<rect class="{m}" x="{cx + 3:g}" y="{by - 3.5:g}" width="1.5" height="5"/>')
        return
    t = "\\n" if c == 10 else chr(c)
    sz = size if len(t) == 1 else size - 2.5
    f.text(x + w / 2, y + h / 2 + sz * 0.36, t, tcls, sz, "middle", 600 if kind == "A" else None, True)


def q(b):
    """Bytes in a caption, in quotes, as the trace shows them."""
    return cstr(b)


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def key_name(s):
    return "a space" if s == b" " else s.decode()


def header(f, left, right=None):
    f.text(24, 18, left, "ta", 11.5, weight=600, mono=True)
    if right:
        f.text(616, 18, right, "tm", 10.5, "end", mono=True)


# ------------------------------------------------------------------ 03.01 one array

def shift0301():
    script = ["goto 4", "type fat ", "goto 15", "type !"]
    ed = checked("03.01", Flat, CAT, script)
    events = [e for _, evs, _, _ in ed.commands for e in evs]

    CW, CG, X0 = 20, 2, 64
    RY1, RY2, RH = 46, 116, 28
    f = Fig("f0301a", 'Typing "fat " at byte 4 of "the cat sat\\n" in one array: every key moves every byte after it',
            186)

    def px(i):
        return X0 + i * (CW + CG)

    def row(y, data, cap, kinds, label):
        f.text(X0 - 10, y + 18, label, "tm", 10.5, "end")
        for i in range(cap):
            cell(f, px(i), y, CW, RH, data[i] if i < len(data) else None,
                 kinds.get(i, "n") if i < len(data) else "u", 11.5)

    def index(y, cap):
        for i in range(0, cap, 2):
            f.text(px(i) + CW / 2, y, str(i), "tm", 9, "middle", mono=True)

    def counters(st):
        return f"bytes moved {st['bytes moved']}  grows {st['grows']}  bytes copied {st['bytes copied']}"

    with steps.step(f, 'The file is opened: its 12 bytes are read into a block exactly as big. The cursor is at '
                       'byte 4, before "cat".'):
        header(f, "the file, read into one block", counters({"bytes moved": 0, "grows": 0, "bytes copied": 0}))
        index(RY1 - 6, 12)
        row(RY1, CAT, 12, {}, "block")
        f.line(px(4) - 1, RY1 - 3, px(4) - 1, RY1 + RH + 3, "a")
        f.text(px(4) - 1, RY1 + RH + 16, "cursor", "ta", 10, "middle")
        f.text(px(12) + 8, RY1 + 18, "12 of 12 bytes in use", "tm", 10.5)

    total = 0
    keys = 0
    for kind, ev in events:
        if kind == "grow":
            g = ev
            with steps.step(f, f"The first key, f, needs one byte more, and the block is full: the text moves to a "
                               f"block twice as big, {g['cap']} bytes, copying all {len(g['data'])} of them (grows 1). "
                               f"The {g['cap'] - len(g['data'])} bytes of room are for the keys to come."):
                header(f, "the block is full: a new one, twice as big",
                       counters({"bytes moved": 0, "grows": 1, "bytes copied": len(g["data"])}))
                row(RY1, g["data"], g["old"], {}, "old")
                index(RY2 - 6, g["cap"])
                row(RY2, g["data"], g["cap"], {i: "a" for i in range(len(g["data"]))}, "new")
                for i in range(len(g["data"])):
                    f.line(px(i) + CW / 2, RY1 + RH + 3, px(i) + CW / 2, RY2 - 14, "m", arrow=True)
            continue
        pos, s, moved = ev["pos"], ev["s"], ev["moved"]
        total += moved
        keys += 1
        before, data = ev["before"], ev["data"]
        if moved == 1:
            cap = (f'goto 15, then "!": only the newline after the cursor moves up: moved 1. A key costs as many '
                   f'bytes as there are after it, wherever the text is kept in one array: {total} moved in all.')
        else:
            cap = (f"Key {keys}, {key_name(s)}, at byte {pos}: the {moved} bytes from {pos} to the end move up one "
                   f"place to open a hole, and {key_name(s)} goes into it: moved {moved}, {total} in all.")
            if keys == 4:
                cap += " Four keys, and each moved every byte after it."
        with steps.step(f, cap):
            header(f, f"insert {pos} {q(s)}", counters(ev["st"]))
            row(RY1, before, ev["cap"], {i: "a" for i in range(pos, len(before))}, "before")
            index(RY2 - 6, ev["cap"])
            kinds = {i + 1: "a" for i in range(pos, len(before))}
            kinds[pos] = "A"
            row(RY2, data, ev["cap"], kinds, "after")
            for i in range(pos, len(before)):
                f.line(px(i) + CW / 2, RY1 + RH + 3, px(i + 1) + CW / 2, RY2 - 14, "a", arrow=True)
            x = px(pos) + CW / 2
            f.line(x, RY2 + RH + 16, x, RY2 + RH + 4, "a", arrow=True)
            f.text(x, RY2 + RH + 28, "in", "ta", 10, "middle")
            f.brace_h(px(pos + 1), px(len(data)) - CG, RY2 + RH + 8, "a")
            f.text((px(pos + 1) + px(len(data)) - CG) / 2 + (8 if moved == 1 else 0), RY2 + RH + 24,
                   f"moved {moved}", "ta", 10, "start" if moved == 1 else "middle")
    same("03.01 bytes moved", total, ed.t.st["bytes moved"])
    return f


# ------------------------------------------------------------------ 03.02 the gap

def gap0302():
    script = ["goto 4", "type fat ", "goto 15", "type !", "back 1"]
    ed = checked("03.02", Gap, CAT, script)
    events = [e for _, evs, _, _ in ed.commands for e in evs]

    CW, CG, X0 = 18, 2, 64
    RY1, RY2, RH = 46, 116, 28
    f = Fig("f0302a", "A gap buffer: the gap goes to the cursor once, and then each key fills one byte of it", 186)

    def px(i):
        return X0 + i * (CW + CG)

    def row(y, s, kinds, label):
        """The block as it is: the text before the gap, the gap, the text after it."""
        f.text(X0 - 10, y + 18, label, "tm", 10.5, "end")
        for i, c in enumerate(s["before"]):
            cell(f, px(i), y, CW, RH, c, kinds.get(i, "n"), 11)
        g0, g1 = s["gap"], s["end"]
        if g1 > g0:
            f.rect(px(g0), y, px(g1) - CG - px(g0), RH, "m f", 3, dash=True)
            if g1 - g0 >= 3:
                f.text((px(g0) + px(g1) - CG) / 2, y + 18, f"gap {g1 - g0}", "tm", 10.5, "middle")
        for j, c in enumerate(s["after"]):
            cell(f, px(g1 + j), y, CW, RH, c, kinds.get(g1 + j, "n"), 11)

    def index(y, cap):
        for i in range(0, cap, 4):
            f.text(px(i) + CW / 2, y, str(i), "tm", 9, "middle", mono=True)

    def moved(n):
        return f"bytes moved {n}"

    def carry(src, dst):
        """The bytes carried across the gap: a bracket on each side and one arrow."""
        a0, a1, b0, b1 = px(src[0]), px(src[-1]) + CW, px(dst[0]), px(dst[-1]) + CW
        f.brace_h(a0, a1, RY1 + RH + 6, "a")
        f.brace_h(b0, b1, RY2 - 6, "a", up=True)
        ax, bx = (a0 + a1) / 2, (b0 + b1) / 2
        f.path(f"M{ax:g} {RY1 + RH + 8} C {ax:g} {RY1 + RH + 30}, {bx:g} {RY2 - 30}, {bx:g} {RY2 - 9}", "a",
               arrow=True)

    first = events[0][1]["from"]
    with steps.step(f, f"The file is opened: its 12 bytes at the start of a block of {first['cap']}, and the gap, "
                       f"{first['end'] - first['gap']} bytes of room, after them. The cursor is at byte 4."):
        header(f, "the file, then the gap", moved(0))
        index(RY1 - 6, first["cap"])
        row(RY1, first, {}, "block")
        f.line(px(4) - 1, RY1 - 3, px(4) - 1, RY1 + RH + 3, "a")
        f.text(px(4) - 1, RY1 + RH + 16, "cursor", "ta", 10, "middle")

    total = 0
    k = 0
    while k < len(events):
        kind, ev = events[k]
        a, b = ev["from"], ev["to"]
        if kind == "move" and k + 1 < len(events) and events[k + 1][0] == "erase":
            k += 1
            continue                        # drawn with the erase it is for
        if kind == "move":
            n, pos = ev["k"], ev["pos"]
            total += n
            if pos < a["gap"]:
                src, dst = list(range(pos, a["gap"])), list(range(b["end"], b["end"] + n))
                how = "cross from before the gap to after it"
                what = q(a["before"][pos:])
            else:
                src, dst = list(range(a["end"], a["end"] + n)), list(range(a["gap"], a["gap"] + n))
                how = "cross from after the gap to before it"
                what = q(a["after"][:n])
            cap = (f"An edit at byte {pos}, and the gap is at {a['gap']}: first the gap moves there. The {n} bytes "
                   f"between, {what}, {how}: moved {n}, {total} in all.")
            with steps.step(f, cap):
                header(f, f"the gap moves to {pos}", moved(total))
                row(RY1, a, {i: "a" for i in src}, "before")
                index(RY1 - 6, a["cap"])
                row(RY2, b, {i: "a" for i in dst}, "after")
                carry(src, dst)
            k += 1
            continue
        if kind == "insert":
            group = [ev]
            if ev["moved"] == 0 and ev["s"] == b"t":
                while k + 1 < len(events) and events[k + 1][0] == "insert" and events[k + 1][1]["moved"] == 0:
                    k += 1
                    group.append(events[k][1])
            a, b = group[0]["from"], group[-1]["to"]
            if len(group) > 1:
                cap = (f"Two more keys, t and a space: each goes into the gap, which gets a byte shorter each time, "
                       f"and nothing else moves. \"fat \" is typed: {total} bytes moved in all, every one of them "
                       f"for the first key.")
            elif ev["moved"]:
                cap = (f"Then {key_name(ev['s'])} goes into the gap's first byte, and the gap is a byte shorter: "
                       f"{b['end'] - b['gap']}.")
            else:
                cap = (f"Key {key_name(ev['s'])} at byte {ev['pos']}: the gap is there already. The key goes into "
                       f"it, the gap is a byte shorter ({b['end'] - b['gap']}), and nothing moves: moved 0.")
            with steps.step(f, cap):
                header(f, "  ".join(f"insert {g['pos']} {q(g['s'])}" for g in group), moved(total))
                index(RY1 - 6, b["cap"])
                row(RY1, a, {}, "before")
                row(RY2, b, {g["pos"]: "A" for g in group}, "after")
                for g in group:
                    x = px(g["pos"]) + CW / 2
                    f.line(x, RY1 + RH + 4, x, RY2 - 4, "a", arrow=True)
            k += 1
            continue
        # an erase, with the move of the gap it needed
        mv = events[k - 1][1] if k > 0 and events[k - 1][0] == "move" else None
        n = mv["k"] if mv else 0
        total += n
        a = mv["from"] if mv else a
        cap = (f"Backspace: the byte before the cursor, {q(ev['gone'])}, is erased. The gap first steps back over it "
               f"({plural(n, 'byte')} moved), then simply widens to take it in: the gap is "
               f"{b['end'] - b['gap']} again. Six edits, {total} bytes moved in all.")
        with steps.step(f, cap):
            header(f, f"erase {ev['pos']} {ev['n']}", moved(total))
            index(RY1 - 6, b["cap"])
            row(RY1, a, {a["gap"] - 1: "A"}, "before")
            row(RY2, b, {}, "after")
            x = px(a["gap"] - 1) + CW / 2
            f.line(x, RY1 + RH + 4, x, RY2 - 4, "a", arrow=True)
            f.text(x + 8, RY2 + RH + 16, "the erased byte is now part of the gap", "ta", 10)
        k += 1
    same("03.02 bytes moved", total, ed.t.st["bytes moved"])
    return f


# ------------------------------------------------------------------ 03.03 two stacks

def stacks0303():
    text = b"the cat\n"
    script = ["goto 4", "type fat ", "goto end", "back 4", "undo", "undo", "redo", "goto 0", "type >", "redo"]
    ed = checked("03.03", Gap, text, script, with_undo=True)

    f = Fig("f0303a", "Undo and redo as two stacks of edits: what was done, and what was undone", 224)
    SX = {"done": 96, "undone": 356}
    SW, SH, SY = 200, 30, 186

    def edit_label(e):
        erase, pos, b = e
        return f"{'erase' if erase else 'insert'} {pos} {q(b)}"

    def draw(cmd, txt, snap, hot=None, gone=None):
        header(f, cmd)
        f.text(24, 50, "the text", "tm", 10.5)
        f.rect(84, 34, 260, 26, "s fs", 4)
        f.text(94, 52, q(txt), "t", 12.5, mono=True)
        for name in ("done", "undone"):
            x = SX[name]
            f.text(x + SW / 2, SY + 24, "done: what undo takes" if name == "done" else "undone: what redo takes",
                   "t", 11, "middle", 600)
            f.path(f"M{x - 6} {SY - 3 * (SH + 4) - 4} L{x - 6} {SY + 4} L{x + SW + 6} {SY + 4} "
                   f"L{x + SW + 6} {SY - 3 * (SH + 4) - 4}", "m")
            items = snap[name]
            for k, e in enumerate(items):
                y = SY - (k + 1) * (SH + 4)
                kind = "A" if hot == (name, k) else "n"
                cls, tcls, _ = STYLE[kind]
                f.rect(x, y, SW, SH, cls, 4)
                f.text(x + SW / 2, y + SH / 2 + 4.5, edit_label(e), tcls, 12, "middle",
                       600 if kind == "A" else None, True)
            if items:
                f.text(x + SW + 12, SY - len(items) * (SH + 4) + SH / 2 + 4, "top", "tm", 10)
            else:
                f.text(x + SW / 2, SY - 14, "empty", "tm", 10.5, "middle")
        if gone:
            x, y = SX["undone"], SY - 3 * (SH + 4)
            f.rect(x, y, SW, SH, "m f", 4, dash=True)
            f.text(x + SW / 2, y + SH / 2 + 4.5, edit_label(gone), "tm", 12, "middle", None, True)
            f.line(x + 8, y + SH / 2, x + SW - 8, y + SH / 2, "a")
            f.text(x + SW / 2, y - 6, "forgotten", "ta", 10, "middle")

    first = True
    for cmd, evs, txt, cursor in ed.commands:
        notes = [e for e in evs if e[0] in ("note", "undo", "redo", "undo-none", "redo-none")]
        if not notes:
            continue
        kind, ev = notes[-1]
        if kind == "note":
            forgot = [g for e in notes for g in e[1]["forgot"]]
            top = len(ev["done"]) - 1
            if cmd == "type fat " and first:
                first = False
                k0, e0 = notes[0]
                with steps.step(f, 'goto 4, and the first key, f: a change to the text, noted as a new edit on top '
                                   'of the done stack: insert 4 "f".'):
                    draw("type f", b"the f" + text[4:], e0, ("done", 0))
                cap = (f"Three more keys, a, t and a space, each typed where the last one ended, join the same "
                       f"edit. Four keys, one edit: {edit_label(ev['done'][top])}.")
                cmd = "the keys a, t and a space"
            elif cmd.startswith("back"):
                cap = (f"goto end, then Backspace four times: a new edit, an erase, and each Backspace after the "
                       f"first adds its byte to it. The edit keeps the bytes it took out, {q(ev['done'][top][2])}, "
                       f"so that they can be put back.")
            elif forgot:
                cap = (f'goto 0 and type ">": a new edit. It empties the undone stack first: '
                       f'{edit_label(forgot[0])} was undone in a text that has changed since, and can no longer '
                       f'be redone.')
            else:
                cap = f"{cmd}: {edit_label(ev['done'][top])}."
            with steps.step(f, cap):
                draw(cmd, txt, ev, ("done", top), forgot[0] if forgot else None)
        elif kind in ("undo", "redo"):
            e = ev["edit"]
            if kind == "undo":
                what = "inserted again" if e[0] else "erased"
                cap = (f"undo: the top of done, {edit_label(e)}, comes off; its opposite is done to the text "
                       f"({q(e[2])} {what}); and it goes on top of undone.")
                hot = ("undone", len(ev["undone"]) - 1)
            else:
                cap = (f"redo: the top of undone, {edit_label(e)}, comes off, is done to the text again, and goes "
                       f"back on top of done.")
                hot = ("done", len(ev["done"]) - 1)
            with steps.step(f, cap):
                draw(kind, txt, ev, hot)
        else:
            u = ed.u.st
            with steps.step(f, f"redo: the undone stack is empty, so there is nothing to redo, and the text stays "
                               f"as it is. {u['edits']} edits made, {u['undos']} undone, {u['redos']} redone; the "
                               f"stacks keep {u['bytes kept']} bytes."):
                draw("redo", txt, ev)
    return f


# ------------------------------------------------------------------ 03.04 the piece list

def pieces0304():
    script = ["goto 4", "type fat ", "goto 15", "type !", "back 1", "type ."]
    ed = checked("03.04", Pieces, CAT, script, algo="pieces", with_undo=True)
    events = [e for _, evs, _, _ in ed.commands for e in evs if e[0] in ("insert", "erase")]

    CW, CG, BX = 22, 2, 150
    f = Fig("f0304a", "A piece table: the file and the add buffer never move; only the list of pieces changes", 262)

    def buffers(add, hot_add=(), used=()):
        f.text(24, 54, "original: the file", "t", 11, weight=600)
        f.text(24, 68, "never changed", "tm", 10)
        for i, c in enumerate(CAT):
            cell(f, BX + i * (CW + CG), 42, CW, 26, c, "n", 11.5)
        for i in range(0, 12, 4):
            f.text(BX + i * (CW + CG) + CW / 2, 38, str(i), "tm", 9, "middle", mono=True)
        f.text(24, 104, "add: what is typed", "t", 11, weight=600)
        f.text(24, 118, "only added to", "tm", 10)
        for i in range(8):
            if i < len(add):
                kind = "A" if i in hot_add else ("n" if i in used else "d")
                cell(f, BX + i * (CW + CG), 92, CW, 26, add[i], kind, 11.5)
            else:
                cell(f, BX + i * (CW + CG), 92, CW, 26, None, "u")
            f.text(BX + i * (CW + CG) + CW / 2, 130, str(i), "tm", 9, "middle", mono=True)

    def pieces(ps, add, hot=()):
        f.text(24, 158, "the pieces, in order", "t", 11, weight=600)
        PG, PY = 16, 168
        x = 24
        for k, (buf, start, length) in enumerate(ps):
            b = (CAT if buf == ORIG else add)[start:start + length]
            pw = max(92, figlib.tw(q(b), 11, True) + 16)
            kind = "A" if k in hot else ("a" if buf == ADD else "n")
            cls, tcls, _ = STYLE[kind]
            f.rect(x, PY, pw, 44, cls, 5)
            f.text(x + pw / 2, PY + 18, f"{buf} {start}+{length}", tcls, 11.5, "middle", 600, True)
            f.text(x + pw / 2, PY + 35, q(b), tcls, 11, "middle", None, True)
            if k + 1 < len(ps):
                f.line(x + pw + 2, PY + 22, x + pw + PG - 2, PY + 22, "s", arrow=True)
            x += pw + PG
        text = b"".join((CAT if b == ORIG else add)[s:s + l] for b, s, l in ps)
        f.text(24, 242, "read in order, the text:", "tm", 10.5)
        f.text(156, 242, q(text), "t", 12, mono=True)
        f.text(616, 242, f"pieces {len(ps)}", "tm", 10.5, "end", mono=True)

    def used_add(ps):
        return {i for b, s, l in ps if b == ADD for i in range(s, s + l)}

    with steps.step(f, "The file is opened by mapping it: nothing is read or copied. The text is one piece, "
                       "orig 0+12: 12 bytes of the original, from its byte 0. The add buffer is empty."):
        header(f, "open")
        buffers(b"")
        pieces([(ORIG, 0, 12)], b"")

    k = 0
    while k < len(events):
        kind, ev = events[k]
        ps, add = ev["pieces"], ev["add"]
        if kind == "insert" and ev["how"] == "grow":
            group = [ev]
            while k + 1 < len(events) and events[k + 1][0] == "insert" and events[k + 1][1]["how"] == "grow":
                k += 1
                group.append(events[k][1])
            ev = group[-1]
            ps, add = ev["pieces"], ev["add"]
            keys = ", ".join(key_name(g["s"]) for g in group[:-1]) + " and " + key_name(group[-1]["s"])
            hot = [i for i, p in enumerate(ps) if p[0] == ADD and p[1] + p[2] == len(add)]
            p = ps[hot[0]]
            cap = (f"{keys}: each goes on the end of the add buffer. The piece before the cursor ends at the end of "
                   f"the add buffer, so it only gets longer, to {p[0]} {p[1]}+{p[2]}: no new piece. Walked "
                   f"{ev['walked']} pieces for each key.")
            hot_add = range(group[0]["start"], len(add))
            head = "  ".join(f"insert {g['pos']} {q(g['s'])}" for g in group)
        elif kind == "insert":
            s = ev["s"]
            hot = [i for i, p in enumerate(ps) if p[0] == ADD and p[1] == ev["start"]]
            if ev["how"] == "cut":
                left, right = ps[hot[0] - 1], ps[hot[0] + 1]
                cap = (f"{q(s)} at byte {ev['pos']}: the byte goes on the end of the add buffer, at {ev['start']}. "
                       f"The piece that byte {ev['pos']} is inside is cut in two, {left[0]} {left[1]}+{left[2]} and "
                       f"{right[0]} {right[1]}+{right[2]}, and a new piece, add {ev['start']}+1, goes between them. "
                       f"Walked {plural(ev['walked'], 'piece')} to find the place.")
            else:
                prev = ps[hot[0] - 1]
                cap = (f"{q(s)} at byte {ev['pos']}: it goes on the end of the add buffer, at {ev['start']}. The "
                       f"piece before the cursor, {prev[0]} {prev[1]}+{prev[2]}, is not the end of the add buffer "
                       f"(the ! is), so it cannot grow: a new piece, add {ev['start']}+1. The ! stays in the add "
                       f"buffer, in no piece.")
            hot_add = [ev["start"]]
            head = f"insert {ev['pos']} {q(s)}"
        else:
            hot, hot_add = [], []
            cap = (f"Backspace: erase byte {ev['pos']}. The piece add 4+1, the !, is taken out of the list. The ! "
                   f"itself stays where it is in the add buffer: no byte is ever taken out of a buffer. Walked "
                   f"{ev['walked']}.")
            head = f"erase {ev['pos']} {ev['n']}"
        with steps.step(f, cap):
            header(f, head)
            buffers(add, hot_add, used_add(ps))
            pieces(ps, add, hot)
        k += 1
    return f


# ------------------------------------------------------------------ 03.05 the tree

def tree0305():
    script = ["goto 4", "type fat ", "goto 15", "type !", "back 1", "type ."]
    ed = checked("03.05", PTree, CAT, script, algo="tree", with_undo=True)
    events = [e for _, evs, _, _ in ed.commands for e in evs if e[0] in ("insert", "erase")]

    f = Fig("f0305a", "The pieces in an AVL tree: each node knows the length of the text under it, and a rotation "
                      "mends a side that has grown two taller", 292)
    NW, NH = 100, 50
    LY = {0: 60, 1: 128, 2: 196, 3: 264}

    def layout(t):
        """Each node at its place in the text from left to right, and its depth down."""
        order = []

        def walk(n, d, parent):
            if n is None:
                return
            walk(n[0], d + 1, n)
            order.append((n, d, parent))
            walk(n[2], d + 1, n)
        walk(t, 0, None)
        step = min(116, 600 / max(len(order), 1))
        x0 = 320 - step * (len(order) - 1) / 2
        xs = {n[5]: (x0 + i * step, LY[d]) for i, (n, d, _) in enumerate(order)}
        return [(n, xs[n[5]][0], xs[n[5]][1], xs[p[5]] if p else None) for n, d, p in order]

    add_now = [b""]

    def draw(t, hot=(), soft=(), note=""):
        header(f, note)
        nodes = layout(t)
        for n, x, y, p in nodes:
            if p:
                f.line(p[0], p[1] + NH / 2, x, y - NH / 2, "m")
        for n, x, y, p in nodes:
            span = n[1]
            kind = "A" if span in hot else ("a" if span in soft else ("p" if span[0] == ADD else "n"))
            cls, tcls, _ = STYLE[kind]
            f.rect(x - NW / 2, y - NH / 2, NW, NH, cls, 6)
            f.text(x, y - 9, f"{span[0]} {span[1]}+{span[2]}", tcls, 11, "middle", 600, True)
            b = (CAT if span[0] == ORIG else add_now[0])[span[1]:span[1] + span[2]]
            f.text(x, y + 5, q(b), tcls, 10.5, "middle", None, True)
            f.text(x, y + 19, f"under it: {n[3]}", tcls if kind == "A" else ("ta" if kind == "a" else "tm"), 9.5,
                   "middle", None, True)
            f.text(x + NW / 2 + 4, y - NH / 2 + 9, f"h{n[4]}", "tm", 9.5, "start", None, True)

    def find_span(t, span):
        if t is None:
            return None
        if t[1] == span:
            return t
        return find_span(t[0], span) or find_span(t[2], span)

    def parent_of(t, span):
        for side in (0, 2):
            if t[side] is not None and t[side][1] == span:
                return t[1], "left" if side == 0 else "right"
        for side in (0, 2):
            if t[side] is not None:
                r = parent_of(t[side], span)
                if r:
                    return r
        return None

    def name(span):
        return f"{span[0]} {span[1]}+{span[2]}"

    with steps.step(f, "The file is opened, mapped as in 03.04: the tree is one node, its piece orig 0+12, with 12 "
                       "bytes of text under it. h is a node's height: 1 for a node with no children."):
        draw((None, (ORIG, 0, 12), None, 12, 1, 0), note="open")
    for kind, ev in events:
        add_now[0] = ev["add"]
        st = ev["steps"]
        what = f"insert {ev['pos']} {q(ev['s'])}" if kind == "insert" else f"erase {ev['pos']} {ev['n']}"
        if kind == "insert" and ev["how"][0] == "grow":
            if ev["s"] != b" ":
                continue
            t = st[-1][1]
            with steps.step(f, "a, t and a space: each is typed just after the piece add 0+1, which ends at the end "
                               "of the add buffer, so that piece only gets longer, to add 0+4. No node is added; "
                               "the lengths on the path down to it are worked out again: 16 under the root now."):
                draw(t, hot=[find_span(t, (ADD, 0, 4))[1]], note='insert 5 "a"  6 "t"  7 " "')
            continue
        if kind == "insert" and ev["s"] == b".":
            rots = [i for k2, _, i in st if k2 == "rotate"]
            t = st[-1][1]
            par, side = parent_of(t, (ADD, 5, 1)) or (None, None)
            with steps.step(f, f'"." at byte 15: no piece to cut, and a new node, add 5+1, goes in after orig 4+7. '
                               f"orig 11+1 above them is then two higher on its left, and this time the inner side "
                               f"is on the left: rotate {rots[0]['dir']} at {name(rots[0]['at'])}, then "
                               f"{rots[1]['dir']} at {name(rots[1]['at'])}. Five pieces, height 3."):
                draw(t, hot=[(ADD, 5, 1)], note=what)
            continue
        for sk, shape, info in st:
            if sk == "cut":
                piece, rest = info["piece"], info["rest"]
                keep = piece[2] - rest[2]
                if ev["pos"] == 4:
                    cap = (f"{q(ev['s'])} at byte 4: first the piece byte 4 is inside, {name(piece)}, is cut there. "
                           f"It keeps its first {keep} bytes, and the rest, {name(rest)}, is a new node just after "
                           f"it in the text: its right child.")
                else:
                    cap = (f"{q(ev['s'])} at byte {ev['pos']}: down from the root by the lengths on the left. The "
                           f"root, add 0+4, has 4 bytes on its left and 4 of its own, so byte {ev['pos']} is byte "
                           f"{ev['pos'] - 8} of its right side: inside {name(piece)}, which is cut there into "
                           f"{name((piece[0], piece[1], keep))} and {name(rest)}, its right child.")
                with steps.step(f, cap):
                    draw(shape, hot=[rest], note=what)
            elif sk == "unbalanced":
                at = info["at"]
                new = ev["how"][1]
                par, side = parent_of(shape, new)
                cap = (f"The new piece, {name(new)}, goes in as a node at byte {ev['pos']}: the {side} child of "
                       f"{name(par)}. On the way back up, at {name(at)}, the two sides are {info['hl']} and "
                       f"{info['hr']} high: two apart, which breaks the rule.")
                with steps.step(f, cap):
                    draw(shape, hot=[new], soft=[at], note=what)
            elif sk == "rotate":
                at, up = info["at"], info["up"]
                if info["inner"]:
                    cap = (f"The taller side, {name(at)}, is itself taller on its inner side, and one rotation would "
                           f"only move that across. So first rotate {info['dir']} at {name(at)}: {name(up)} goes up "
                           f"and {name(at)} down to its {info['dir']}. The order of the pieces is the same.")
                else:
                    cap = (f"Then rotate {info['dir']} at {name(at)}: {name(up)} goes up in its place, and "
                           f"{name(at)} down to its {info['dir']}. The two sides are now the same height, the "
                           f"pieces are in the same order, and only the two nodes that turned have their lengths "
                           f"worked out again.")
                with steps.step(f, cap):
                    draw(shape, hot=[up], soft=[at], note=f"{what}: rotate {info['dir']}")
            elif sk == "done" and kind == "erase":
                gone = ev["gone"][0]
                cap = (f"Backspace: erase byte {ev['pos']}. Its piece, {name(gone)}, is a node of its own, so that "
                       f"node is taken out. It had two children, so the first node after it in the text, the "
                       f"leftmost of its right side, orig 11+1, takes its place.")
                with steps.step(f, cap):
                    draw(shape, note=what)
    return f


FIGS = [
    ("03.01-shift", shift0301),
    ("03.02-gap", gap0302),
    ("03.03-stacks", stacks0303),
    ("03.04-pieces", pieces0304),
    ("03.05-tree", tree0305),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        fig = fn()
        n = steps.check(fig.svg())
        print(os.path.relpath(figlib.write(MOD, name, fig), ROOT), f"({n} steps)")


if __name__ == "__main__":
    main()
