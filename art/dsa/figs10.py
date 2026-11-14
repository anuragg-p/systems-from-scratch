"""Figures for dsa module 10, Capstone: git (lessons 10.01-10.04).

    python3 -B art/dsa/figs10.py

Every value in these figures comes from a real run of the project as it stands at the lesson
(./learn files dsa --at NN.LL into a temporary directory, then make), on a fresh repository made in
that temporary directory with a made-up author and committer and fixed dates, so every object's
name is the same on every run. DS_TRACE=1 has git print one line a step on stderr (the formats are
in tools/git/NOTES.md); the frames are drawn from those lines. Where a figure shows more than the
trace says (an object's bytes, a tree's entries), this script reads it again with the project's own
cat-file or from the object's file, and checks it with Python's hashlib and zlib, so a figure cannot
disagree with the code. The real git is not run here.

The repository is the lessons' running example: hello.txt, "b c", b/c, d/e/f.txt and d/g.txt;
"first" at 1700000000; "on a side branch" made on first with commit-tree at 1700000030; "second"
(d/e/f.txt gets a line) at 1700000060; "third" (hello.txt changed) at 1700000120; and "Merge side"
of third and the side branch, by commit-tree, at 1700000180.

  10.01-object   one object: "blob 6", a NUL and "hello\\n", its SHA-1, the path it is stored at,
                 and the 21 bytes of the file: the zlib header, one fixed DEFLATE block, Adler-32
  10.02-trees    stepped: d/e/f.txt changed; add forgets the cached trees above it, and write-tree
                 builds those again bottom up, renaming d/e, d and the top, while b keeps its name
  10.03-log      stepped: log of the merge, one commit off the heap a frame, with the heap and the
                 table of names seen
  10.04-diff     stepped: diff of first and second, the two trees walked side by side, what has the
                 same name on both sides passed over unopened
  10.04-base     the merge base of main and the side branch, painted from both tips, newest first
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import figlib  # noqa: E402
from figlib import Fig, tw  # noqa: E402
import steps  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
figlib.LESSONS = os.path.join(ROOT, "tracks", "dsa", "lessons")
MOD = "10-git"

T0 = 1700000000
IDENTITY = {"GIT_AUTHOR_NAME": "A U Thor", "GIT_AUTHOR_EMAIL": "author@example.com",
            "GIT_COMMITTER_NAME": "C O Mitter", "GIT_COMMITTER_EMAIL": "committer@example.com"}


# ------------------------------------------------------------------ running the real code

class Project:
    """The project at one lesson, written by ./learn files and built, in a temporary directory, and
    the repositories made with it, each a new directory beside it (never anywhere else)."""

    def __init__(self, tmp, lid):
        self.tmp = tmp
        self.dir = os.path.join(tmp, lid)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", lid, self.dir], check=True,
                       capture_output=True)
        subprocess.run(["make", "-s"], cwd=self.dir, check=True, capture_output=True)
        self.n = 0

    def repo(self):
        self.n += 1
        path = os.path.join(self.tmp, f"repo{self.n}-{os.path.basename(self.dir)}")
        os.makedirs(path)
        self.git(path, ["init", "-q"])
        return path

    def git(self, repo, args, when=0):
        """(stdout, the trace lines without "trace: ") of bin/git -C repo args, at T0 + when."""
        assert os.path.realpath(repo).startswith(os.path.realpath(self.tmp) + os.sep)
        env = {k: v for k, v in os.environ.items() if not k.startswith(("DS_", "GIT_"))}
        env.update(IDENTITY, LC_ALL="C", DS_TRACE="1", GIT_AUTHOR_DATE=f"{T0 + when} +0000",
                   GIT_COMMITTER_DATE=f"{T0 + when} +0000")
        r = subprocess.run([os.path.join(self.dir, "bin", "git"), "-C", repo] + args, capture_output=True, env=env)
        if r.returncode != 0:
            raise SystemExit(f"git {' '.join(args)}: exit {r.returncode}\n{r.stderr.decode()}")
        err = r.stderr.decode().splitlines()
        return r.stdout.decode(), [l[7:] for l in err if l.startswith("trace: ")]


def write(repo, path, data):
    p = os.path.join(repo, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(data)


FILES = {"hello.txt": "hello\n", "b c": "space\n", "b/c": "c\n", "d/e/f.txt": "deep\n", "d/g.txt": "g\n"}


def history(p, repo, merge=True):
    """The lessons' history, made as the lessons make it: {name: full commit name}."""
    for k, v in FILES.items():
        write(repo, k, v)
    p.git(repo, ["add", "."])
    p.git(repo, ["commit", "-q", "-m", "first"], 0)
    side = p.git(repo, ["commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "on a side branch"], 30)[0].strip()
    p.git(repo, ["branch", "side", side[:7]])
    write(repo, "d/e/f.txt", "deep\nchanged\n")
    p.git(repo, ["add", "d"])
    p.git(repo, ["commit", "-q", "-m", "second"], 60)
    write(repo, "hello.txt", "hello, world\n")
    p.git(repo, ["add", "hello.txt"])
    p.git(repo, ["commit", "-q", "-m", "third"], 120)
    if merge:
        m = p.git(repo, ["commit-tree", "HEAD^{tree}", "-p", "HEAD", "-p", "side", "-m", "Merge side"], 180)[0].strip()
        p.git(repo, ["branch", "merged", m[:7]])
    out = {}
    for line in p.git(repo, ["log", "--oneline", "merged" if merge else "main", "side"])[0].splitlines():
        h, msg = line.split(" ", 1)
        out[msg] = h
    return out


def show(c):
    return {" ": "space", "\n": "\\n", "\0": "\\0"}.get(c, c)


# ------------------------------------------------------------------ one object (10.01)

def object1001(p):
    repo = p.repo()
    write(repo, "hello.txt", "hello\n")
    out, tr = p.git(repo, ["hash-object", "-w", "hello.txt"])
    name = out.strip()
    m = re.match(r"^object: blob of (\d+) bytes is (\w\w)/(\w{38}): written, (\d+) bytes compressed$", tr[0])
    assert m and m.group(2) + m.group(3) == name, tr
    raw = b"blob 6\x00hello\n"
    assert hashlib.sha1(raw).hexdigest() == name
    with open(os.path.join(repo, ".git", "objects", name[:2], name[2:]), "rb") as f:
        stored = f.read()
    assert len(stored) == int(m.group(4)) and zlib.decompress(stored) == raw
    assert int.from_bytes(stored[-4:], "big") == zlib.adler32(raw)
    again, tr2 = p.git(repo, ["hash-object", "-w", "hello.txt"])
    assert again == out and tr2[0].endswith("already there"), tr2

    f = Fig("f1001a", "One object: a header and the file's bytes, named by their SHA-1 and stored under that "
                      "name, compressed", 352)
    X0 = 24
    # the object as it is hashed
    f.text(X0, 22, "bin/git hash-object -w hello.txt: the object is a header and the file's 6 bytes", "tm", 11)
    CW = 34
    cells = raw.decode()
    for i, c in enumerate(cells):
        head = i < 7
        x = X0 + i * CW
        f.rect(x, 34, CW - 4, 30, "a af" if head else "s f", 4)
        label = show(c) if c in " \n\0" else c
        if c == " ":
            f.line(x + 9, 54, x + CW - 13, 54, "a")
        else:
            f.text(x + (CW - 4) / 2, 54, label, "ta" if head else "t", 13 if len(label) == 1 else 11.5, "middle", 600,
                   mono=True)
    f.brace_h(X0, X0 + 7 * CW - 4, 72, "a")
    f.text(X0 + (7 * CW - 4) / 2, 88, "header: type, space, size, NUL", "ta", 11, "middle", 600)
    f.brace_h(X0 + 7 * CW, X0 + 13 * CW - 4, 72, "m")
    f.text(X0 + 7 * CW + (6 * CW - 4) / 2, 88, "hello.txt's bytes", "tm", 11, "middle")
    f.text(X0 + 13 * CW + 8, 46, f"{len(raw)} bytes", "t", 12, weight=600, mono=True)
    f.text(X0 + 13 * CW + 8, 61, "a tree or a commit", "tm", 10.5)
    f.text(X0 + 13 * CW + 8, 74, "starts the same way", "tm", 10.5)

    # its name
    f.line(X0 + 6 * CW, 98, X0 + 6 * CW, 122, "s", arrow=True)
    f.text(X0 + 6 * CW + 10, 114, "SHA-1 of those 13 bytes (one 64-byte block, padded)", "tm", 11)
    f.rect(X0, 128, 592, 30, "s fs", 6)
    f.text(X0 + 12, 148, "name", "tm", 11)
    nx = X0 + 64
    f.add(f'<text class="t mono" x="{nx}" y="148" font-size="13.5" font-weight="700">'
          f'<tspan class="ta">{name[:2]}</tspan>{name[2:]}</text>')
    f.text(X0 + 580, 148, "40 hex digits", "tm", 10.5, "end")

    # where it is stored
    f.line(X0 + 6 * CW, 162, X0 + 6 * CW, 184, "s", arrow=True)
    f.text(X0 + 6 * CW + 10, 177, "the first 2 digits a directory, the other 38 the file", "tm", 11)
    f.rect(X0, 190, 592, 30, "s f", 6)
    f.text(X0 + 12, 210, "path", "tm", 11)
    f.add(f'<text class="t mono" x="{nx}" y="210" font-size="12.5" font-weight="600">.git/objects/'
          f'<tspan class="ta">{name[:2]}/</tspan>{name[2:]}</text>')

    # the file's bytes
    f.text(X0, 244, f"the file there: {len(stored)} bytes, read-only, written once (the second hash-object "
                    f"-w finds it and stops)", "tm", 11)
    BW = 27.5
    groups = [(0, 2, "zlib header", "a af", "ta"), (2, len(stored) - 4, "DEFLATE, one fixed block (09.04)", "s f", "t"),
              (len(stored) - 4, len(stored), "Adler-32 of the 13", "a af", "ta")]
    for a, b, label, cls, tcls in groups:
        for i in range(a, b):
            x = X0 + i * BW
            f.rect(x, 254, BW - 3, 24, cls, 3)
            f.text(x + (BW - 3) / 2, 270.5, f"{stored[i]:02x}", tcls, 11, "middle", 600, mono=True)
        x1, x2 = X0 + a * BW, X0 + b * BW - 3
        f.brace_h(x1, x2, 286, "a" if tcls == "ta" else "m")
        f.text((x1 + x2) / 2, 302, label, tcls, 10.5, "middle", 600 if tcls == "ta" else None)
    f.text(X0, 322, f"78 01: DEFLATE with a 32 KB window, the fastest level; 78 x 256 + 01 = {0x7801} = 31 x "
                    f"{0x7801 // 31}", "tm", 10.5, mono=True)
    f.text(X0, 340, f"{stored[-4:].hex(' ')}: the Adler-32 of the 13 bytes before compression, most "
                    f"significant byte first", "tm", 10.5, mono=True)
    assert 0x7801 % 31 == 0
    return f


# ------------------------------------------------------------------ trees renamed up the path (10.02)

TREE_LINE = re.compile(r"^tree: (\S+) \((?:(\d+) entr(?:y|ies), )?(\d+) files? under it\): (\w{7}), (built|from the cache)$")


def tree_rows(p, repo, tree):
    """[(path, depth, kind, 7-digit name)] of a tree, as bin/git ls-tree -r -t prints it, the top first."""
    out, _ = p.git(repo, ["ls-tree", "-r", "-t", tree])
    rows = [("/", 0, "tree", tree[:7])]
    for line in out.splitlines():
        meta, path = line.split("\t")
        mode, kind, oid = meta.split()
        rows.append((path, path.count("/") + 1, kind, oid[:7]))
    return rows


def trees1002(p):
    repo = p.repo()
    for k, v in FILES.items():
        write(repo, k, v)
    p.git(repo, ["add", "."])
    out, tr1 = p.git(repo, ["write-tree"])
    old = out.strip()
    built1 = [TREE_LINE.match(l).groups() for l in tr1 if l.startswith("tree: ")]
    assert [b[4] for b in built1] == ["built"] * 4
    write(repo, "d/e/f.txt", "deep\nchanged\n")
    _, tradd = p.git(repo, ["add", "d/e/f.txt"])
    blob = re.match(r"^object: blob of 13 bytes is (\w\w)/(\w{5})\w+: written", tradd[0])
    newblob = blob.group(1) + blob.group(2)
    gone = [re.match(r"^index: d/e/f\.txt changed: the cached tree of (\S+) is gone$", l).group(1)
            for l in tradd if "cached tree" in l]
    assert gone == ["/", "d/", "d/e/"], gone
    out, tr2 = p.git(repo, ["write-tree"])
    new = out.strip()
    built2 = [TREE_LINE.match(l).groups() for l in tr2 if l.startswith("tree: ")]
    assert [(b[0], b[4]) for b in built2] == [("b/", "from the cache"), ("d/e/", "built"), ("d/", "built"),
                                              ("/", "built")], built2
    before = tree_rows(p, repo, old)
    after = tree_rows(p, repo, new)
    assert [r[:3] for r in before] == [r[:3] for r in after]
    oldname = {r[0]: r[3] for r in before}
    newname = {r[0]: r[3] for r in after}
    changed = {k for k in oldname if oldname[k] != newname[k]}
    assert changed == {"/", "d", "d/e", "d/e/f.txt"}, changed
    assert newname["d/e/f.txt"] == newblob
    key = {"/": "/", "b/": "b", "d/": "d", "d/e/": "d/e"}
    counts = {key[b[0]]: int(b[2]) for b in built1}

    f = Fig("f1002a", "One file changed deep in a directory: the trees above it renamed, one by one up to the top", 380)
    X0, RY, RH = 24, 46, 29
    RIGHT = 300                  # the boxes end here; a note goes after them
    rows = before
    dirs = ["/", "b", "d", "d/e"]

    def label(path):
        return "/ (the top)" if path == "/" else path.rsplit("/", 1)[-1] + ("/" if path in dirs else "")

    f.text(X0, 24, "the trees and blobs, as ls-tree -r -t lists them", "tm", 11)
    PX = 404
    f.text(PX, 24, "the index's cached trees (TREE)", "tm", 11)
    f.line(PX - 14, 14, PX - 14, 316, "m")
    STYLE = {"same": ("s f", "t", "tm", False), "gone": ("m f", "tm", "tm", True), "hot": ("a fa", "f", "f", False),
             "renamed": ("a af", "ta", "ta", False), "cached": ("a f", "ta", "ta", False)}
    # the legend, the same in every frame
    for i, (st, what) in enumerate((("hot", "new name, this step"), ("renamed", "new name, earlier"),
                                    ("cached", "taken from the cache"), ("gone", "cached tree gone"))):
        cls, _, _, dash = STYLE[st]
        y = 248 + i * 18
        f.rect(PX, y - 10, 18, 12, cls, 3, dash=dash)
        f.text(PX + 26, y, what, "tm", 10.5)

    def draw(state, names, notes, cache, trace):
        """state: path -> same, gone, hot, cached, renamed; names: path -> the name drawn."""
        for i, (path, depth, kind, _) in enumerate(rows):
            y = RY + i * RH
            x = X0 + depth * 20
            st = state.get(path, "same")
            cls, tcls, ncls, dash = STYLE[st]
            if depth:
                f.path(f"M{X0 + (depth - 1) * 20 + 8} {y - RH + 22} L{X0 + (depth - 1) * 20 + 8} {y + 11} L{x} {y + 11}",
                       "m")
            f.rect(x, y, RIGHT - x, 22, cls, 5, dash=dash)
            f.text(x + 8, y + 15.5, label(path), tcls, 12, weight=600 if kind == "tree" else None, mono=True)
            f.text(RIGHT - 70, y + 15.5, kind, ncls, 10.5, "end")
            f.text(RIGHT - 8, y + 15.5, names[path], tcls, 12, "end", 600, mono=True)
            if path in notes:
                f.text(RIGHT + 6, y + 15.5, notes[path], "ta" if st != "gone" else "tm", 10.5, weight=600)
        for i, d in enumerate(dirs):
            y = 40 + i * 32
            n, oid = cache[d]
            ok = oid is not None
            f.rect(PX, y, 212, 25, "s f" if ok else "m f", 5, dash=not ok)
            f.text(PX + 10, y + 16.5, "/" if d == "/" else d + "/", "t" if ok else "tm", 12, weight=600, mono=True)
            f.text(PX + 66, y + 16.5, f"{n} file{'s' if n != 1 else ''}" if ok else "-1", "tm", 11, mono=not ok)
            f.text(PX + 202, y + 16.5, oid if ok else "gone", "t" if ok else "tm", 12, "end", 600 if ok else None,
                   mono=ok)
        f.text(PX, 184, "each directory's last tree, with how", "tm", 10.5)
        f.text(PX, 198, "many index entries are under it;", "tm", 10.5)
        f.text(PX, 212, "-1 once one of them changes", "tm", 10.5)
        f.text(X0, 320, "DS_TRACE=1 printed", "tm", 10.5)
        for k, t in enumerate(trace):
            f.text(X0, 337 + k * 16, t, "t", 11, mono=True)

    names = dict(oldname)
    cache = {d: (counts[d], oldname[d]) for d in dirs}
    tr1t = [l for l in tr1 if l.startswith("tree: ")]
    frames = []
    frames.append(({}, dict(names), {}, dict(cache), [tr1t[-1]],
                   f"After add and write-tree: one tree for each directory, built bottom up, and the top one, "
                   f"{old[:7]}, stands for all five files. The index keeps each directory's tree."))
    names2 = dict(names, **{"d/e/f.txt": newblob})
    frames.append(({"d/e/f.txt": "hot"}, names2, {"d/e/f.txt": f"was {oldname['d/e/f.txt']}"}, dict(cache),
                   [l for l in tradd if l.startswith("index: update")],
                   f"d/e/f.txt gets a line, and add stores it: new bytes, so a new blob, {newblob}, and the "
                   f"file's index entry names it now."))
    cache3 = dict(cache, **{d: (cache[d][0], None) for d in ("/", "d", "d/e")})
    st3 = {"d/e/f.txt": "renamed", "/": "gone", "d": "gone", "d/e": "gone"}
    frames.append((st3, names2, {}, cache3, [l for l in tradd if "cached tree" in l],
                   "The same add forgets the cached tree of every directory above d/e/f.txt: the top, d and d/e. "
                   "b keeps its own, since nothing under it changed."))
    tr2t = [l for l in tr2 if l.startswith("tree: ")]
    st = dict(st3)
    nm = dict(names2)
    cache_now = dict(cache3)
    for k, (d, ents, under, oid, how) in enumerate(built2):
        path = key[d]
        if how == "from the cache":
            st = dict(st, **{path: "cached"})
            frames.append((dict(st), dict(nm), {path: "from the cache"}, dict(cache_now), [tr2t[k]],
                           f"write-tree, bottom up. b's cached tree is still good, so {oid} is taken as it is: "
                           f"no tree is built for b."))
            continue
        assert newname[path] == oid
        st = {kk: ("renamed" if vv in ("hot", "renamed") else vv) for kk, vv in st.items()}
        top = {"d/e": "d/e", "d": "d", "/": "The top"}[path]
        st[path] = "hot"
        nm[path] = oid
        cache_now[path] = (counts[path], oid)
        what = {"d/e": f"Its one entry, f.txt, names {newblob} now",
                "d": "It lists e by e's new name, and g.txt as before",
                "/": "It lists d by d's new name, and b c, b and hello.txt as before"}[path]
        tail = (" Three trees built, one from the cache: every tree on the path to f.txt has a new name, "
                "and nothing else does." if path == "/" else "")
        frames.append((st, dict(nm), {path: f"was {oldname[path]}"}, dict(cache_now), [tr2t[k]],
                       f"{top} built. {what}: its bytes changed, so its name did, "
                       f"{oldname[path]} becomes {oid}." + tail))
    for state, nms, notes, ch, trace, cap in frames:
        with steps.step(f, cap):
            draw(state, nms, notes, ch, trace)
    assert nm == newname
    return f, old, new


# ------------------------------------------------------------------ log, a commit off the heap at a time (10.03)

POP = re.compile(r"^log: pop (\w{7}) (\d+); heap: (.*)$")
PUSH = re.compile(r"^log: push (\w{7}) (\d+); heap: (.*)$")
SEEN = re.compile(r"^log: (\w{7}), parent of (\w{7}): seen already$")


def heap_of(s):
    if s == "(empty)":
        return []
    return [(h, int(t)) for h, t in (x.split() for x in s.split(", "))]


def log1003(p):
    repo = p.repo()
    names = history(p, repo)
    out, tr = p.git(repo, ["log", "--oneline", "merged"])
    printed = [l.split(" ", 1) for l in out.splitlines()]
    msg = {h: m for h, m in printed}
    abbr = {m: h for h, m in printed}
    assert abbr == names
    when = {}
    parents = {}
    for h in msg:
        text, _ = p.git(repo, ["cat-file", "-p", h])
        when[h] = int(re.search(r"^committer .* (\d+) \+0000$", text, re.M).group(1))
        parents[h] = [x[:7] for x in re.findall(r"^parent (\w{40})$", text, re.M)]
    # the events, as the trace has them
    events = []
    for l in tr:
        if POP.match(l):
            h, t, rest = POP.match(l).groups()
            events.append(["pop", h, int(t), heap_of(rest), [], []])
        elif PUSH.match(l):
            h, t, rest = PUSH.match(l).groups()
            events[-1][4].append(h)
            events[-1][3] = heap_of(rest)
        elif SEEN.match(l):
            events[-1][5].append(SEEN.match(l).group(1))
    assert [e[1] for e in events] == [h for h, _ in printed]
    for e in events:
        assert e[2] == when[e[1]] and sorted(e[4] + e[5]) == sorted(parents[e[1]])

    order = sorted(msg, key=lambda h: when[h])
    row = {h: (1 if msg[h] == "on a side branch" else 0) for h in msg}
    short = {"first": "first", "second": "second", "third": "third", "on a side branch": "side",
             "Merge side": "merge"}
    f = Fig("f1003a", "log of the merge: the newest commit off the heap each time, its parents onto it unless the "
                      "table has seen them", 340)
    X0, GW, BWD, BH = 24, 80, 62, 50
    ROWY = (44, 124)
    pos = {h: (X0 + i * GW, ROWY[row[h]]) for i, h in enumerate(order)}
    PX = 434
    f.text(X0, 24, "the history: each commit points at its parents, to the left", "tm", 11)
    f.line(PX - 14, 14, PX - 14, 300, "m")
    STYLE = {"popped": ("a fa", "f", "f"), "shown": ("s fs", "t", "tm"), "heap": ("a af", "ta", "ta"),
             "later": ("m f", "tm", "tm")}
    x = X0
    for st, what in (("popped", "popped, printed now"), ("shown", "printed"), ("heap", "on the heap"),
                     ("later", "not met yet")):
        cls, _, _ = STYLE[st]
        f.rect(x, 314, 18, 12, cls, 3, dash=st == "later")
        f.text(x + 26, 324, what, "tm", 10.5)
        x += 26 + tw(what, 10.5) + 26

    def edge(a, b, cls, dash=False):
        (x1, y1), (x2, y2) = pos[a], pos[b]
        if y1 == y2:
            f.line(x1 - 1, y1 + BH / 2, x2 + BWD + 3, y2 + BH / 2, cls, arrow=True, dash=dash)
        elif y1 < y2:                          # down from the child, then left to the parent
            cx, my = x1 + BWD / 2, y2 + BH / 2
            f.path(f"M{cx} {y1 + BH + 1} L{cx} {my - 8} Q{cx} {my} {cx - 8} {my} L{x2 + BWD + 3} {my}", cls,
                   arrow=True, dash=dash)
        else:                                  # left from the child, then up to the parent
            cx, my = x2 + BWD / 2, y1 + BH / 2
            f.path(f"M{x1 - 1} {my} L{cx + 8} {my} Q{cx} {my} {cx} {my - 8} L{cx} {y2 + BH + 3}", cls,
                   arrow=True, dash=dash)

    def draw(popped, heap, seen, shown, hot_edges, seen_edge):
        for a in msg:
            for b in parents[a]:
                if (a, b) == seen_edge:
                    edge(a, b, "a", dash=True)
                else:
                    edge(a, b, "a" if (a, b) in hot_edges else "m")
        inheap = {h for h, _ in heap}
        for h in msg:
            x, y = pos[h]
            st = ("popped" if h == popped else "shown" if h in shown else "heap" if h in inheap else "later")
            cls, tcls, mcls = STYLE[st]
            f.rect(x, y, BWD, BH, cls, 6, dash=st == "later")
            f.text(x + BWD / 2, y + 16, h, tcls, 11.5, "middle", 700, mono=True)
            f.text(x + BWD / 2, y + 30, short[msg[h]], mcls, 10.5, "middle")
            f.text(x + BWD / 2, y + 43, f"+{when[h] - T0} s", mcls, 10, "middle", mono=True)
        # printed so far
        f.text(X0, 206, "log --oneline has printed", "tm", 11)
        for i, h in enumerate(shown):
            last = h == popped
            f.text(X0, 226 + i * 17, f"{h} {msg[h]}", "ta" if last else "t", 12, weight=700 if last else None,
                   mono=True)
        if not shown:
            f.text(X0, 226, "nothing yet", "tm", 11.5)
        # the heap, as its array, the top first
        f.text(PX, 24, "the heap (02.04), newest on top", "tm", 11)
        for i, (h, t) in enumerate(heap):
            y = 36 + i * 30
            f.rect(PX, y, 182, 24, "a af", 5)
            f.text(PX + 8, y + 16.5, f"[{i}]", "tm", 10.5, mono=True)
            f.text(PX + 34, y + 16.5, h, "ta", 12, weight=700, mono=True)
            f.text(PX + 174, y + 16.5, f"+{t - T0} s", "ta", 11, "end", mono=True)
        if not heap:
            f.rect(PX, 36, 182, 24, "m f", 5, dash=True)
            f.text(PX + 91, 52, "empty", "tm", 11, "middle")
        # the table of names seen
        f.text(PX, 124, "seen: the hash table (01.02)", "tm", 11)
        for i, h in enumerate(seen):
            y = 134 + i * 26
            f.rect(PX, y, 86, 21, "s f", 4)
            f.text(PX + 43, y + 15, h, "t", 11.5, "middle", 600, mono=True)
        f.text(PX + 98, 150, f"{len(seen)} name{'s' if len(seen) != 1 else ''}", "t", 12, weight=600)
        f.text(PX + 98, 166, "each pushed", "tm", 10.5)
        f.text(PX + 98, 180, "once", "tm", 10.5)

    start = printed[0][0]
    frames = [(None, [(start, when[start])], [start], [], set(), None,
               f"log starts at the merge, {start}: it goes onto the heap, and its name into the table of names seen. "
               f"Nothing is printed yet.")]
    seen = [start]
    shown = []
    for kind, h, t, heap, pushed, already in events:
        shown = shown + [h]
        seen = seen + pushed
        if len(pushed) == 2:
            what = (f"both its parents are new: {pushed[0]} and {pushed[1]} go into the table and onto the heap, "
                    f"which keeps the newer, {heap[0][0]}, on top.")
        elif pushed:
            what = f"its parent {pushed[0]} is new: into the table, and onto the heap."
        elif already:
            what = (f"its parent {already[0]} is in the table already, reached through main, so it is not "
                    f"pushed again.")
        else:
            what = "it has no parent. The heap is empty, so log is done: each commit printed once, newest first."
        frames.append((h, heap, list(seen), list(shown), {(h, x) for x in pushed},
                       (h, already[0]) if already else None,
                       f"Pop {h} ({msg[h]}), the newest on the heap, and print it; " + what))
    for popped, heap, sn, sh, hot, se, cap in frames:
        with steps.step(f, cap):
            draw(popped, heap, sn, sh, hot, se)
    return f, names


# ------------------------------------------------------------------ diff: two trees side by side (10.04)

DIFF = re.compile(r"^diff: (\S+(?: \S+)?): (\w{7})(?: and (\w{7}))?(?: on both sides)?: (.*)$")


def diff1004(p):
    repo = p.repo()
    names = history(p, repo, merge=False)
    first, second = names["first"], names["second"]
    out, tr = p.git(repo, ["diff", first, second])
    walk = [DIFF.match(l).groups() for l in tr if l.startswith("diff: ")]
    old_tree = p.git(repo, ["cat-file", "-p", first])[0].split()[1]
    new_tree = p.git(repo, ["cat-file", "-p", second])[0].split()[1]
    before = tree_rows(p, repo, old_tree)
    after = tree_rows(p, repo, new_tree)
    assert [r[:3] for r in before] == [r[:3] for r in after]
    patch = out.splitlines()
    assert patch[0] == "diff --git a/d/e/f.txt b/d/e/f.txt", patch
    verdict = {}
    for path, x, y, what in walk:
        verdict[path.rstrip("/")] = (x, y or x, what)
    assert list(verdict) == ["b c", "b", "d", "d/e", "d/e/f.txt", "d/g.txt", "hello.txt"], verdict

    rows = before
    oldn = {r[0]: r[3] for r in before}
    newn = {r[0]: r[3] for r in after}
    f = Fig("f1004a", "diff of first and second: the two trees walked side by side, entries with the same name on "
                      "both sides passed over unopened", 384)
    X0, RY, RH = 24, 50, 28
    LX, RX, W = X0, 366, 250
    f.text(LX, 18, "bin/git diff main~2 main~1: the two top trees, walked in step, entry by entry", "tm", 11)
    f.text(LX, 38, f"first's tree, {old_tree[:7]}", "t", 11.5, weight=600)
    f.text(RX, 38, f"second's tree, {new_tree[:7]}", "t", 11.5, weight=600)
    x = LX
    for cls, dash, what in (("a fa", False, "compared now"), ("a af", False, "different: opened, or changed"),
                            ("s f", False, "read"), ("m f", True, "not read")):
        f.rect(x, 314, 18, 12, cls, 3, dash=dash)
        f.text(x + 26, 324, what, "tm", 10.5)
        x += 26 + tw(what, 10.5) + 26
    dirs = {"/", "b", "d", "d/e"}

    def label(path):
        return "/ (the top)" if path == "/" else path.rsplit("/", 1)[-1] + ("/" if path in dirs else "")

    def under(path, d):
        return path != d and path.startswith(d + "/")

    def draw(k, opened, done, unread):
        for i, (path, depth, kind, _) in enumerate(rows):
            y = RY + i * RH
            here = path == (order[k] if k is not None and k < len(order) else None)
            v = verdict.get(path)
            for side, X, nm in (("a", LX, oldn), ("b", RX, newn)):
                x = X + depth * 18
                if path in unread or (path != "/" and not any(path == c or under(path, c) for c in opened) and
                                      path.rsplit("/", 1)[0] not in opened and depth > 1):
                    cls, tcls, dash = "m f", "tm", True
                elif here:
                    cls, tcls, dash = ("a fa", "f", False)
                elif path in done:
                    same = v and v[2].startswith("the same")
                    cls, tcls, dash = ("s f", "t", False) if same else ("a af", "ta", False)
                else:
                    cls, tcls, dash = "s f", "t", False
                if depth:
                    px = X + (depth - 1) * 18 + 7
                    f.path(f"M{px} {y - RH + 22} L{px} {y + 11} L{x} {y + 11}", "m")
                f.rect(x, y, W - (x - X), 22, cls, 5, dash=dash)
                f.text(x + 7, y + 15.5, label(path), tcls, 11.5, weight=600 if kind == "tree" else None, mono=True)
                f.text(X + W - 8, y + 15.5, nm[path], tcls, 11.5, "end", 600, mono=True)
            if path in done or here:
                if v:
                    mark = "=" if v[2].startswith("the same") else "opened" if "opened" in v[2] else "changed"
                    f.text((LX + W + RX) / 2, y + 15.5, mark, "ta" if mark != "=" else "tm", 11 if mark != "=" else 14,
                           "middle", 700)

    order = list(verdict)
    opened = {"/"}
    done = {"/"}
    unread = {"b/c"}
    tr_diff = [l for l in tr if l.startswith("diff: ")]
    caps = {
        "b c": "b c: the same blob, 9495c3c, on both sides: passed over. Equal names, equal bytes.",
        "b": "b/ is 1933da3 on both sides: the same tree, so the same everything under it. Passed over, "
             "never opened: c is not read at all.",
        "d": "d/ is d61f885 here and 7ecc4e4 there: something under it differs. Both trees are opened and walked "
             "in step, the same way.",
        "d/e": "d/e/: 8588183 against cd21a79. Different again: opened.",
        "d/e/f.txt": "d/e/f.txt: blob 4cdb226 against 06654ae: a changed file. Its two blobs are read later, to "
                     "print the patch with module 06's diff.",
        "d/g.txt": "d/g.txt: 01058d8 on both sides: passed over.",
        "hello.txt": "hello.txt: ce01362 on both sides: passed over. Done: 6 trees read, 1 subtree and 3 files "
                     "passed over, 1 file changed.",
    }
    for path, v in verdict.items():
        assert (v[0] in caps[path]) and (v[1] in caps[path] or v[1] == v[0]), (path, v)
    with steps.step(f, f"diff reads the two top trees, {old_tree[:7]} and {new_tree[:7]}, and walks their entries "
                       f"side by side in git's order, as a merge of two sorted lists."):
        draw(None, opened, done, unread | {"b/c"})
        f.text(X0, 360, "the top trees differ, so the walk starts inside them", "tm", 11)
    for k, path in enumerate(order):
        if verdict[path][2].startswith("different"):
            opened = opened | {path}
        with steps.step(f, caps[path]):
            draw(k, opened, done, unread)
            f.text(X0, 352, "DS_TRACE=1 printed", "tm", 10.5)
            f.text(X0, 369, tr_diff[k], "t", 11, mono=True)
        done = done | {path}
    return f, (first, second, old_tree, new_tree)


# ------------------------------------------------------------------ the merge base, painted (10.04)

MB = re.compile(r"^merge-base: pop (\w{7}) (\d+), reached by (1|2|1 and 2)(, stale)?$")


def base1004(p):
    repo = p.repo()
    names = history(p, repo, merge=False)
    out, tr = p.git(repo, ["merge-base", "main", "side"])
    pops = [MB.match(l).groups() for l in tr if l.startswith("merge-base: pop")]
    base = out.strip()[:7]
    assert base == names["first"]
    msg = {h: m for m, h in names.items()}
    when = {h: int(t) for h, t, _, _ in pops}
    f = Fig("f1004b", "The merge base of main and side, painted: each commit marked with which tip reaches it, "
                      "newest first off the heap", 284)
    X0, GW, BWD, BH = 40, 140, 104, 40
    order = ["first", "on a side branch", "second", "third"]
    pos = {names["first"]: (X0, 70), names["on a side branch"]: (X0 + GW, 150), names["second"]: (X0 + GW, 70),
           names["third"]: (X0 + 2 * GW, 70)}
    f.text(X0 - 16, 24, "bin/git merge-base main side, with DS_TRACE=1: the commits in the order popped", "tm", 11)
    parents = {names["third"]: [names["second"]], names["second"]: [names["first"]],
               names["on a side branch"]: [names["first"]]}
    for a, ps in parents.items():
        for b in ps:
            (x1, y1), (x2, y2) = pos[a], pos[b]
            if y1 == y2:
                f.line(x1 - 1, y1 + BH / 2, x2 + BWD + 3, y2 + BH / 2, "m", arrow=True)
            else:
                f.path(f"M{x1 - 1} {y1 + BH / 2} C{x1 - 24} {y1 + BH / 2} {x2 + BWD + 24} {y2 + BH / 2} "
                       f"{x2 + BWD + 3} {y2 + BH / 2}", "m", arrow=True)
    seen_pop = []
    for k, (h, t, by, stale) in enumerate(pops):
        if h in seen_pop:
            continue
        seen_pop.append(h)
        x, y = pos[h]
        both = by == "1 and 2"
        f.rect(x, y, BWD, BH, "a fa" if both else "s f", 6)
        f.text(x + 10, y + 16, h, "f" if both else "t", 11.5, weight=700, mono=True)
        f.text(x + 10, y + 31, msg[h], "f" if both else "tm", 10.5)
        f.circle(x + BWD - 4, y - 2, 10, "a f")
        f.text(x + BWD - 4, y + 2, str(len(seen_pop)), "ta", 11, "middle", 700, mono=True)
        mark = {"1": "1: from main", "2": "2: from side", "1 and 2": "1 and 2: the merge base"}[by]
        f.text(x + BWD / 2, y + BH + 16, mark, "ta" if both else "t", 11, "middle", 700 if both else 600)
        f.text(x + BWD / 2, y + BH + 30, f"+{int(t) - T0} s", "tm", 10, "middle", mono=True)
        if both and [q[0] for q in pops].count(h) == 2:
            f.text(x + BWD / 2, y + BH + 44, "popped twice: both", "tm", 10.5, "middle")
            f.text(x + BWD / 2, y + BH + 57, "its children pushed it", "tm", 10.5, "middle")
    for tip, h in (("main", names["third"]), ("side", names["on a side branch"])):
        x, y = pos[h]
        f.rect(x + BWD + 14, y + 9, 44, 22, "s", 11)
        f.text(x + BWD + 36, y + 24, tip, "t", 11, "middle", 700, mono=True)
        f.line(x + BWD + 13, y + 20, x + BWD + 3, y + 20, "s", arrow=True)
    f.text(X0 - 16, 252, f"Reached by both: {base}, the newest commit both histories hold, so the merge base.",
           "t", 11.5)
    f.text(X0 - 16, 270, "Its marks go on to its parents as stale, and with nothing but stale commits left, the walk stops.",
           "t", 11.5)
    assert len(seen_pop) == 4 and pops[3][2] == "1 and 2" and pops[3][3]
    return f


# ------------------------------------------------------------------ main

def main():
    sys.dont_write_bytecode = True
    from archmap import check
    paths = []
    with tempfile.TemporaryDirectory(prefix="figs10-") as tmp:
        projects = {}

        def at(lid):
            if lid not in projects:
                projects[lid] = Project(tmp, lid)
            return projects[lid]

        figs = [("10.01-object", object1001(at("10.01")), False),
                ("10.02-trees", trees1002(at("10.02"))[0], True),
                ("10.03-log", log1003(at("10.03"))[0], True),
                ("10.04-diff", diff1004(at("10.04"))[0], True),
                ("10.04-base", base1004(at("10.04")), False)]
        for name, fig, stepped in figs:
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
