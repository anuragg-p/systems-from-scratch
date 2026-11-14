"""The dsa track's architecture map, one copy per lesson.

    python3 -B art/dsa/archmap.py             writes tracks/dsa/lessons/<module>/figures/NN.LL-map.svg
                                              for every lesson written so far (its .md exists), skips
                                              the rest, and checks each file against the site's sanitizer
    python3 -B art/dsa/archmap.py --all DIR   writes every lesson's map under DIR/NN/ instead (a preview
                                              of the modules not written yet; DIR outside the repo or in build/)

The track is ten tools standing on one library the reader writes, so the map is a
grid: a column per module, its tool at the top; under the tools, one rail per
structure that more than one tool stands on, starting from the column that builds
it (a filled node) and running on to every tool that uses it again (a ring); under
the rails, the current module's lessons, one box each. The current module's column
is shaded down to that strip, so "where am I" is the shaded column and the accent
box in it.

In each lesson's copy, what that lesson builds is drawn in the accent colour (its
box in the strip, and the rail node or the use it brings), what earlier lessons
built is solid, and what is still to come is dashed and muted. A rail is solid as
far as its last use built so far and dashed beyond. 00.01, the tour of the whole
track, lights everything. Lessons reference it as

    ![Where NN.LL fits](figures/NN.LL-map.svg)

Everything is driven by the three tables below: MODULES (the tool of each column),
LESSONS (every lesson id, its title as the lesson's front matter has it, and its
piece in the strip) and RAILS (the shared structures: the lessons that build each
one, and the lesson that brings each use again, which that lesson lights too).
When the code changes which structures a tool calls, or from which lesson, change
RAILS to match (its comment says how each use was found) and run this again; it
reports a title that differs from the lesson's own and a lesson the table does
not have.
"""
import os
import re
import sys

import figlib
from figlib import Fig, tw, write

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LESSONS_DIR = os.path.join(ROOT, "tracks", "dsa", "lessons")

# A column per module: (tool, the module's second program or None).
MODULES = {
    "00": ("paste", None),
    "01": ("freq", None),
    "02": ("sort", "look"),
    "03": ("edit", None),
    "04": ("grep", None),
    "05": ("spell", None),
    "06": ("diff", "patch"),
    "07": ("make", None),
    "08": ("route", None),
    "09": ("gzip", "gunzip"),
    "10": ("git", None),
}
COL = {mid: i for i, mid in enumerate(MODULES)}

# Every lesson: (id, title, its piece in the module's strip). The rails it lights come from RAILS.
LESSONS = [
    ("00.01", "One job, done slow and done fast", "slow and fast"),
    ("00.02", "Measuring growth", "growth harness"),
    ("01.01", "A growable array", "growable array"),
    ("01.02", "A hash table", "hash table"),
    ("01.03", "Hash functions, collisions and resizing", "hashing, resizing"),
    ("02.01", "Insertion sort, and where it stops being enough", "insertion sort"),
    ("02.02", "Merge sort", "merge sort"),
    ("02.03", "Quicksort, and the input that breaks it", "quicksort"),
    ("02.04", "A heap, and the top ten without sorting everything", "heap"),
    ("02.05", "Sorting a file bigger than memory", "sorted runs"),
    ("02.06", "Binary search in a sorted file", "binary search"),
    ("03.01", "An editor, and its text in one array", "text in an array"),
    ("03.02", "The gap buffer", "gap buffer"),
    ("03.03", "Undo and redo: two stacks", "undo stacks"),
    ("03.04", "The piece table: a list of pieces", "piece table"),
    ("03.05", "The pieces in a balanced tree", "balanced tree"),
    ("04.01", "Searching for a string, and skipping ahead", "string search"),
    ("04.02", "Parsing a regular expression", "regex parser"),
    ("04.03", "The pattern as a machine: an NFA", "NFA"),
    ("04.04", "Caching the states: a DFA built as it runs", "DFA cache"),
    ("05.01", "A trie, and completing a prefix", "trie"),
    ("05.02", "A Bloom filter: the dictionary in far less memory", "Bloom filter"),
    ("05.03", "Edit distance, and \"did you mean\"", "edit distance"),
    ("06.01", "The longest common subsequence, as a table", "LCS table"),
    ("06.02", "From the table to hunks: unified output", "hunks"),
    ("06.03", "Myers: the shortest path of edits", "Myers"),
    ("06.04", "patch: applying a diff", "patch"),
    ("07.01", "A makefile as a graph", "graph"),
    ("07.02", "Depth-first search, and finding a cycle", "depth-first search"),
    ("07.03", "Topological order, and what is out of date", "topological order"),
    ("07.04", "Building in parallel: a queue of ready work", "ready queue"),
    ("08.01", "A road map as a graph", "road graph"),
    ("08.02", "Breadth-first search: the fewest junctions", "breadth-first search"),
    ("08.03", "Dijkstra, with a heap", "Dijkstra"),
    ("08.04", "A*: searching towards the goal", "A*"),
    ("09.01", "Huffman codes: a greedy tree", "Huffman tree"),
    ("09.02", "Inflate: reading a real gzip file", "inflate"),
    ("09.03", "LZ77: finding repeats with a hash table", "LZ77"),
    ("09.04", "Deflate: writing a file gunzip accepts", "deflate"),
    ("10.01", "Objects: a hash is a name", "objects by hash"),
    ("10.02", "Trees and the index: a directory as a hash", "trees, index"),
    ("10.03", "Commits: walking a graph for log", "commit graph"),
    ("10.04", "diff between commits, and the merge base", "diff, merge base"),
]

# The structures more than one tool stands on: (label, the lessons that build it, the module that
# builds it, its uses again: [(module, the lesson that brings the use, or None if not known yet)]).
# A use in the building module's own column is not drawn (the build node is there already). A use
# whose lesson is None shows as still to come until its module's last lesson, and solid from there
# on: the map never claims a use before the code has it. A use is a call in the tool's own code
# (tools/<name>/ and the lib/ files its module brings), and its lesson is the first one whose project
# (./learn files dsa --at NN.LL) has that call; a later lesson of the same tool using it again lights
# nothing new. Every use below was checked that way, on all 43 lessons:
#   array       sort.c 02.01, undo.c 03.03 (the two stacks), dfa.c 04.04 (the states), spell.c and
#               trie.c 05.01, diff.c 06.01 (the lines), depgraph.c and read.c 07.01, inflate.c and
#               gunzip.c 09.02, object.c and zframe.c 10.01; not paste (before it) or route, whose
#               graph and queue are blocks of its own
#   hash table  dfa.c 04.04 (a state by its NFA states), spell.c 05.01 (--algo=table; bloom.c takes
#               its FNV-1a at 05.02), diff.c 06.01 (equal lines, equal numbers), depgraph.c and
#               read.c 07.01 (a target or a variable by its name), commit.c 10.03 (the commits met);
#               not gzip: lz77.c's table of three-byte strings (09.03) is its own
#   sorting     spell.c 05.01 (merge sort), index.c 10.02 (merge sort; git.c's branch list at 10.03)
#   heap        freq.c 02.04 (--top=heap), route.c 08.03 (A* at 08.04), huffman.c 09.01, commit.c
#               10.03 (log; compare.c's merge-base at 10.04)
#   diff        compare.c 10.04 (diff_text, diff_myers and the hunks of 06.02, on two blobs)
#   deflate     zframe.c 10.01 (deflate_raw and inflate_raw, inside the zlib format)
# Nothing else of one module is called from another's: not spell's edit distance (diff fills a table
# of its own), not grep's, edit's, make's or route's structures.
RAILS = [
    ("array", ("01.01",), "01", [("02", "02.01"), ("03", "03.03"), ("04", "04.04"), ("05", "05.01"),
                                 ("06", "06.01"), ("07", "07.01"), ("09", "09.02"), ("10", "10.01")]),
    ("hash table", ("01.02", "01.03"), "01", [("04", "04.04"), ("05", "05.01"), ("06", "06.01"), ("07", "07.01"),
                                              ("10", "10.03")]),
    ("sorting", ("02.01", "02.02", "02.03"), "02", [("05", "05.01"), ("10", "10.02")]),
    ("heap", ("02.04",), "02", [("01", "02.04"), ("08", "08.03"), ("09", "09.01"), ("10", "10.03")]),
    ("diff", ("06.01", "06.02", "06.03"), "06", [("10", "10.04")]),
    ("deflate", ("09.02", "09.04"), "09", [("10", "10.01")]),
]
LIB_RAILS = 4                    # the first four are lib/; the rest are tools another tool reuses

# The grid.
LEFT, RIGHT = 14, 626
X0 = 112                         # the columns start here; the rails' labels sit left of it
CW = (RIGHT - X0) / len(MODULES)
TOOL_Y, TOOL_H = 30, 40
RAIL_Y, RAIL_DY, RAIL_GAP = 100, 20, 18
STRIP_H = 42
PAD = 6                          # the shading's margin round the strip


def cx(mid):
    return X0 + CW * COL[mid] + CW / 2


def rail_y(i):
    return RAIL_Y + i * RAIL_DY + (RAIL_GAP if i >= LIB_RAILS else 0)


RAILS_END = rail_y(len(RAILS) - 1) + 14
STRIP_Y = RAILS_END + 26
HEIGHT = STRIP_Y + STRIP_H + 38


def order(lid):
    return [l[0] for l in LESSONS].index(lid)


def draw(lid, title, everything=False):
    """The map for lesson lid. everything: light every piece (the first lesson's tour)."""
    f = Fig("map" + lid.replace(".", ""), f"Where {lid} fits: {title}", HEIGHT)
    now = order(lid)
    mod = lid[:2]

    def lesson_state(l):
        """here, built or later, for something a lesson brings (l: a lesson id, or a module id)."""
        if everything:
            return "here"
        if len(l) == 2:                                   # a use whose lesson is not known yet
            last = [x[0] for x in LESSONS if x[0][:2] == l][-1]
            return "built" if l < mod or lid == last else "later"
        k = order(l)
        return "here" if k == now else ("built" if k < now else "later")

    def build_state(lids):
        states = {lesson_state(l) for l in lids}
        return "here" if "here" in states else ("built" if "built" in states else "later")

    # the strip's place: the current module's lessons, centred under its column where they fit
    mine = [l for l in LESSONS if l[0][:2] == mod]
    n = len(mine)
    gap = 8
    bw = min(150, (RIGHT - LEFT - gap * (n - 1)) / n)
    total = bw * n + gap * (n - 1)
    sx = min(max(cx(mod) - total / 2, LEFT), RIGHT - total)

    # the current module's column, shaded from its tool down and opening out round its strip
    x1, x2 = X0 + CW * COL[mod] + 1, X0 + CW * (COL[mod] + 1) - 1
    top, r = TOOL_Y - 24, 8
    lo, hi = sx - PAD, sx + total + PAD
    yt, yb = STRIP_Y - PAD, STRIP_Y + STRIP_H + PAD
    ym = (RAILS_END + yt) / 2
    d = (f"M{x1:.1f} {top + r} Q{x1:.1f} {top} {x1 + r:.1f} {top} L{x2 - r:.1f} {top} Q{x2:.1f} {top} {x2:.1f} {top + r} "
         f"L{x2:.1f} {RAILS_END} C{x2:.1f} {ym} {hi:.1f} {ym} {hi:.1f} {yt} "
         f"L{hi:.1f} {yb - r} Q{hi:.1f} {yb} {hi - r:.1f} {yb} L{lo + r:.1f} {yb} Q{lo:.1f} {yb} {lo:.1f} {yb - r} "
         f"L{lo:.1f} {yt} C{lo:.1f} {ym} {x1:.1f} {ym} {x1:.1f} {RAILS_END} Z")
    f.add(f'<path class="af" d="{d}"/>')

    # the tools
    f.text(LEFT, TOOL_Y - 10, "module", "tm", 10.5)
    f.text(LEFT, TOOL_Y + 25, "tools", "tm", 12)
    for mid, (tool, second) in MODULES.items():
        s = "here" if everything or mid == mod else ("built" if mid < mod else "later")
        bx, w = X0 + CW * COL[mid] + 2, CW - 4
        box, tcls = {"here": ("a f", "ta"), "built": ("s f", "t"), "later": ("m f", "tm")}[s]
        f.rect(bx, TOOL_Y, w, TOOL_H, box, 6, dash=s == "later")
        f.text(cx(mid), TOOL_Y - 10, mid, "ta" if s == "here" else "tm", 10, "middle", mono=True)
        if second:
            f.text(cx(mid), TOOL_Y + 18, tool, tcls, 12, "middle", 700 if s == "here" else 600, mono=True)
            f.text(cx(mid), TOOL_Y + 32, second, "ta" if s == "here" else "tm", 10, "middle", mono=True)
        else:
            f.text(cx(mid), TOOL_Y + 25, tool, tcls, 12, "middle", 700 if s == "here" else 600, mono=True)

    # the rails
    f.text(LEFT, RAIL_Y - 15, "the library", "tm", 11)
    f.text(LEFT, rail_y(LIB_RAILS) - 16, "from other tools", "tm", 11)
    for i, (label, builds, home, uses) in enumerate(RAILS):
        y = rail_y(i)
        nodes = [(home, build_state(builds), True)]
        for umid, ulid in uses:
            if umid != home:
                st = lesson_state(ulid or umid)
                # a use cannot come before the structure it uses
                if st != "later" and nodes[0][1] == "later":
                    st = "later"
                nodes.append((umid, st, False))
        nodes.sort(key=lambda n: COL[n[0]])
        lit = {n[1] for n in nodes}
        lab = "ta" if "here" in lit else ("t" if nodes and build_state(builds) != "later" else "tm")
        f.text(LEFT, y + 4.5, label, lab, 13, weight=600 if lab == "ta" else None)
        for a, b in zip(nodes, nodes[1:]):
            sa, sb = a[1], b[1]
            if "later" in (sa, sb):
                cls, dash = "m", True
            elif "here" in (sa, sb):
                cls, dash = "a", False
            else:
                cls, dash = "s", False
            ra = 5.5 if a[2] else 4.5
            rb = 5.5 if b[2] else 4.5
            f.line(cx(a[0]) + ra + 1, y, cx(b[0]) - rb - 1, y, cls, dash=dash)
        for m, st, is_home in nodes:
            if is_home:
                cls = {"here": "a fa", "built": "s t", "later": "m tm"}[st]
                f.circle(cx(m), y, 5.5, cls)
            else:
                cls = {"here": "a f", "built": "s f", "later": "m f"}[st]
                f.circle(cx(m), y, 4.5, cls)

    # the strip: the current module's lessons
    for k, (l, _, piece) in enumerate(mine):
        st = "here" if l == lid else ("built" if order(l) < now else "later")
        bx = sx + k * (bw + gap)
        box, tcls, icls = {"here": ("a af", "ta", "ta"), "built": ("s f", "t", "tm"), "later": ("m f", "tm", "tm")}[st]
        f.rect(bx, STRIP_Y, bw, STRIP_H, box, 8, dash=st == "later")
        f.text(bx + bw / 2, STRIP_Y + 16, l, icls, 10.5, "middle", mono=True)
        size = next(z for z in (14, 13.5, 13, 12.5, 12) if len(piece) * z * 0.58 <= bw - 10 or z == 12)
        f.text(bx + bw / 2, STRIP_Y + 33, piece, tcls, size, "middle", 700 if st == "here" else (600 if st == "built" else 500))

    # legend
    ly = HEIGHT - 12
    x = LEFT
    for cls, dash, label, tcls in (("a af", False, f"{lid}: this lesson", "ta"), ("s f", False, "built earlier", "t"),
                                   ("m f", True, "still to come", "tm")):
        f.rect(x, ly - 12, 20, 15, cls, 4, dash=dash)
        f.text(x + 27, ly, label, tcls, 13, weight=600 if tcls == "ta" else None)
        x += 27 + tw(label, 13) + 24
    x += 6
    f.circle(x + 5, ly - 4.5, 5, "s t")
    f.text(x + 15, ly, "built", "tm", 12)
    x += 15 + tw("built", 12) + 14
    f.circle(x + 4.5, ly - 4.5, 4, "s f")
    f.text(x + 14, ly, "used again", "tm", 12)
    return f


def module_dirs(base):
    """{"02": "02-sort", ...}: the module folders that exist under base."""
    out = {}
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return out
    for name in names:
        m = re.match(r"^(\d\d)-", name)
        if m and os.path.isdir(os.path.join(base, name)):
            out[m.group(1)] = name
    return out


def lesson_titles(folder):
    """{"02.04": its title}: the lessons written in one module folder, from their front matter."""
    out = {}
    for name in sorted(os.listdir(folder)):
        m = re.match(r"^(\d\d\.\d\d)-.*\.md$", name)
        if m:
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                t = re.search(r"^title:\s*(.*?)\s*$", fh.read().split("\n---", 1)[0], re.M)
            out[m.group(1)] = t.group(1) if t else ""
    return out


def check(paths):
    """Each file must be ASCII and come through the site's sanitizer with every element kept."""
    sys.path.insert(0, ROOT)
    sys.dont_write_bytecode = True        # read harness/, never write into it
    from harness.web.art import sanitize
    bad = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        if not text.isascii():
            bad.append(f"{p}: not ASCII")
        clean = sanitize(text, "x")
        if not clean:
            bad.append(f"{p}: rejected by sanitize")
        elif clean.count("<") - clean.count("</") != text.count("<") - text.count("</"):
            bad.append(f"{p}: sanitize dropped an element")
    return bad


def main(argv):
    preview = None
    if argv[:1] == ["--all"] and len(argv) == 2:
        preview = os.path.abspath(argv[1])
    elif argv:
        print(__doc__.strip().split("\n\n")[1])
        return 2
    figlib.LESSONS = preview or LESSONS_DIR
    dirs = {mid: mid for mid in MODULES} if preview else module_dirs(LESSONS_DIR)
    assert [l[0][:2] for l in LESSONS] == sorted(l[0][:2] for l in LESSONS), "LESSONS out of order"
    assert set(l[0][:2] for l in LESSONS) == set(MODULES), "a module without lessons, or lessons without a module"
    for _, builds, home, uses in RAILS:
        assert all(b[:2] == home for b in builds) and all(m in MODULES for m, _ in uses)
    written = {}
    if not preview:
        for mid, name in dirs.items():
            written.update(lesson_titles(os.path.join(LESSONS_DIR, name)))
    paths, skipped, bad = [], [], []
    for lid, title, _ in LESSONS:
        if not preview and lid not in written:
            skipped.append(lid)
            continue
        if not preview and written[lid] != title:
            bad.append(f"{lid}: the lesson's title is {written[lid]!r}, this table says {title!r}")
        paths.append(write(dirs[lid[:2]], f"{lid}-map", draw(lid, title, everything=lid == LESSONS[0][0])))
    bad += [f"{lid}: a lesson this table does not have" for lid in written if lid not in {l[0] for l in LESSONS}]
    for p in paths:
        print(os.path.relpath(p, ROOT) if p.startswith(ROOT) else p)
    if skipped:
        print(f"skipped {len(skipped)} lessons not written yet: {skipped[0]} to {skipped[-1]}")
    bad += check(paths)
    for b in bad:
        print("problem:", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
