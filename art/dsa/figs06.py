"""Figures for dsa module 06, Comparing files: diff (lessons 06.01 to 06.04).

    python3 -B art/dsa/figs06.py

Every figure is drawn from the DS_TRACE=1 output of the real programs, run on the project as
./learn files writes it at the lesson (built first, in a temporary directory), so a figure cannot
disagree with the code. The pair is the one of Myers' paper and the module's cover: a.txt holds
the lines A B C A B B A, b.txt the lines C B A B A C.

  06.01-table    stepped: DS_TRACE=1 bin/diff a.txt b.txt at 06.01, the table's rows in the order
                 they are filled, bottom first ("trace: lcs: row 7: 0 0 0 0 0 0 0" ...)
  06.02-walk     stepped: the same at 06.02, the walk from L[0][0] ("trace: walk: at 0 0, L 4:
                 delete ...") and the script as hunks, at -U3 and -U0 ("trace: hunk: edits 0 to 8")
  06.03-search   stepped: the same at 06.03, Myers' search, round by round ("trace: myers: d 2 k 0:
                 down from (1,0) to (1,1), snake 1, reaches (2,2)") and the path walked back
  06.04-offset   still: bin/patch at 06.04 placing the hunk of diff -u old.txt new.txt in moved.txt,
                 old.txt with two lines put on top ("trace: patch: hunk of line 3 at line 1: ...")

The script also checks each trace against a model of what it claims (the table's rule in every
cell, a path that only goes diagonally where lines are equal) and each figure against the site's
own rules for stepped figures.
"""
import atexit
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
import figlib  # noqa: E402
from figlib import Fig, write  # noqa: E402
import steps  # noqa: E402

figlib.LESSONS = os.path.join(ROOT, "tracks", "dsa", "lessons")
MOD = "06-diff"
A, B = "ABCABBA", "CBABAC"

_built = {}


def project(at):
    """The project at a lesson, written by ./learn files and built, with the files the figures use."""
    if at not in _built:
        top = tempfile.mkdtemp(prefix="dsa-figs06-")
        atexit.register(shutil.rmtree, top, True)
        d = os.path.join(top, at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["make", "-s"], cwd=d, check=True, stdout=subprocess.DEVNULL)
        files = {"a.txt": "".join(c + "\n" for c in A), "b.txt": "".join(c + "\n" for c in B)}
        book = open(os.path.join(d, "data", "book.txt")).read().split("\n")
        old = book[7:13]                                   # sed -n 8,13p: the contents, I to VI
        new = [book[7]] + [l.replace("Mystery", "Murder") for l in book[9:14]]
        files["old.txt"] = "".join(l + "\n" for l in old)
        files["new.txt"] = "".join(l + "\n" for l in new)
        files["moved.txt"] = "A note at the top.\n\n" + files["old.txt"]
        for name, text in files.items():
            with open(os.path.join(d, name), "w") as f:
                f.write(text)
        _built[at] = d
    return _built[at]


def run(at, argv, trace=True):
    """(stdout, the trace lines) of a program of the project at a lesson."""
    d = project(at)
    env = dict(os.environ, LC_ALL="C")
    if trace:
        env["DS_TRACE"] = "1"
    r = subprocess.run([os.path.join(d, argv[0])] + argv[1:], cwd=d, env=env, capture_output=True, text=True)
    assert r.returncode in (0, 1), (argv, r.returncode, r.stderr)
    return r.stdout, [l[len("trace: "):] for l in r.stderr.splitlines() if l.startswith("trace: ")]


# ------------------------------------------------------------------ the table, as 06.01 traces it

def lcs_rows(at):
    """{row: [(value, equal)]} from 'trace: lcs: row i: ...', and the rows in trace order."""
    _, tr = run(at, ["bin/diff", "a.txt", "b.txt"])
    rows, order = {}, []
    for line in tr:
        m = re.match(r"lcs: row (\d+): (.*)$", line)
        if m:
            i = int(m.group(1))
            rows[i] = [(int(c.rstrip("=")), c.endswith("=")) for c in m.group(2).split()]
            order.append(i)
    n, m = len(A), len(B)
    assert sorted(rows) == list(range(n + 1)) and all(len(r) == m + 1 for r in rows.values())
    for i in range(n + 1):                       # the rule, in every cell, as diff.c states it
        for j in range(m + 1):
            v, eq = rows[i][j]
            if i == n or j == m:
                assert v == 0 and not eq
            elif A[i] == B[j]:
                assert eq and v == rows[i + 1][j + 1][0] + 1
            else:
                assert not eq and v == max(rows[i + 1][j][0], rows[i][j + 1][0])
    return rows, order, tr


# the table's place on the page, in 06.01 and 06.02
TX, TY, CW, CH = 74, 92, 34, 26


def cell_xy(i, j):
    return TX + j * CW, TY + i * CH


def table_frame(f, title_cmd):
    """The parts of the table that never change: the command, the headers, the grid."""
    n, m = len(A), len(B)
    cmd, _, files = title_cmd.partition("|")
    f.text(24, 22, cmd.strip(), "t", 11.5, mono=True)
    if files:
        f.text(616, 22, files.strip(), "tm", 10.5, "end", mono=True)
    f.text(TX + (m + 1) * CW / 2, TY - 44, "b, line j", "tm", 10.5, "middle")
    f.text(24, TY - 8, "a, line i", "tm", 10.5)
    for j in range(m + 1):
        x = TX + j * CW + CW / 2
        f.text(x, TY - 24, str(j), "tm", 10, "middle", mono=True)
        f.text(x, TY - 8, B[j] if j < m else "end", "t" if j < m else "tm", 12.5 if j < m else 10, "middle",
               700 if j < m else None, mono=True)
    for i in range(n + 1):
        y = TY + i * CH + CH / 2 + 4.5
        f.text(TX - 32, y, str(i), "tm", 10, "end", mono=True)
        f.text(TX - 12, y, A[i] if i < n else "end", "t" if i < n else "tm", 12.5 if i < n else 10, "end",
               700 if i < n else None, mono=True)


def table_grid(f):
    n, m = len(A), len(B)
    for j in range(1, m + 1):
        f.line(TX + j * CW, TY, TX + j * CW, TY + (n + 1) * CH, "m")
    for i in range(1, n + 1):
        f.line(TX, TY + i * CH, TX + (m + 1) * CW, TY + i * CH, "m")
    f.rect(TX, TY, (m + 1) * CW, (n + 1) * CH, "s", 0)


def table_cell(f, i, j, v, eq, cls_text="t", weight=None):
    x, y = cell_xy(i, j)
    if eq:
        f.rect(x + 1.5, y + 1.5, CW - 3, CH - 3, "af", 2, sw=False)
        f.line(x + CW - 3, y + CH - 3, x + CW - 9, y + CH - 9, "a")     # from the lower right
    f.text(x + CW / 2, y + CH / 2 + 4.5, str(v), "ta" if eq and cls_text == "t" else cls_text, 12, "middle",
           weight, mono=True)


def table0601():
    rows, order, _ = lcs_rows("06.01")
    n, m = len(A), len(B)
    out, _ = run("06.01", ["bin/diff", "a.txt", "b.txt"], trace=False)
    f = Fig("f0601a", "The table for a = ABCABBA and b = CBABAC, filled a row at a time from the bottom: "
            "each cell is the length of the longest common subsequence of a from line i and b from line j", 330)
    table_frame(f, "DS_TRACE=1 bin/diff a.txt b.txt | a.txt: A B C A B B A, b.txt: C B A B A C")
    PX = 356
    f.text(PX, TY - 44, "L[i][j], when a[i] and b[j] are equal:", "t", 11)
    f.text(PX + 8, TY - 26, "L[i+1][j+1] + 1", "ta", 11.5, weight=600, mono=True)
    f.text(PX, TY - 6, "otherwise, the larger of below and right:", "t", 11)
    f.text(PX + 8, TY + 12, "max(L[i+1][j], L[i][j+1])", "t", 11.5, weight=600, mono=True)
    f.rect(PX, TY + 30, 16, 13, "af", 2, sw=False)
    f.line(PX + 13, TY + 40, PX + 7, TY + 34, "a")
    f.text(PX + 24, TY + 41, "the two lines are equal here", "tm", 10.5)

    def worked(i):
        """One cell of row i worked out, for the panel: an equal one and an unequal one."""
        out = []
        for j in range(m):
            v, eq = rows[i][j]
            if eq and not any(o[1] for o in out):
                out.append((j, True, f"L[{i}][{j}]: {A[i]} = {B[j]}: L[{i + 1}][{j + 1}] + 1 = "
                                     f"{rows[i + 1][j + 1][0]} + 1 = {v}"))
            elif not eq and not any(not o[1] for o in out):
                out.append((j, False, f"L[{i}][{j}]: {A[i]} is not {B[j]}: max({rows[i + 1][j][0]}, "
                                      f"{rows[i][j + 1][0]}) = {v}"))
        return sorted(out)

    for k, r in enumerate(order):
        line = "row %d: %s" % (r, " ".join(f"{v}{'=' if eq else ''}" for v, eq in rows[r]))
        if r == n:
            cap = (f"Row {n} first: no line of a is left there, so nothing is in common with any end of b, and "
                   f"every cell is 0. Column {m}, the end of b, is 0 in every row for the same reason.")
        elif r == 0:
            cap = (f"Row 0 last. L[0][0] = {rows[0][0][0]}: a and b have {rows[0][0][0]} lines in common, so "
                   f"diff deletes {n} - {rows[0][0][0]} = {n - rows[0][0][0]} of a's lines and inserts "
                   f"{m} - {rows[0][0][0]} = {m - rows[0][0][0]}.")
        else:
            eqs = [j for j in range(m) if rows[r][j][1]]
            which = " and ".join(str(j) for j in eqs) if eqs else "none"
            cap = (f"Row {r}, a's line \"{A[r]}\": equal to b's lines {which}, which take 1 more than the cell "
                   f"to their lower right; every other cell takes the larger of the cells below and to its right.")
        with steps.step(f, cap):
            for i in range(r, n + 1):
                for j in range(m + 1):
                    v, eq = rows[i][j]
                    if i == r:
                        x, y = cell_xy(i, j)
                        if not eq:
                            f.rect(x + 1.5, y + 1.5, CW - 3, CH - 3, "fs", 2, sw=False)
                    table_cell(f, i, j, v, eq, "t" if i > r or eq else "t", 700 if i == r else None)
            x, y = cell_xy(r, 0)
            f.rect(x, y, (m + 1) * CW, CH, "a", 0)
            if r == 0:
                f.rect(TX + 2, TY + 2, CW - 4, CH - 4, "a fa", 3)
                f.text(TX + CW / 2, TY + CH / 2 + 4.5, str(rows[0][0][0]), "f", 12.5, "middle", 700, mono=True)
            f.text(PX, TY + 84, f"the program prints, filling row {r}:", "tm", 10.5)
            f.text(PX, TY + 102, "trace: lcs: " + line, "ta", 10.5, weight=600, mono=True)
            if 0 < r < n:
                for t, (j, eq, text) in enumerate(worked(r)):
                    f.text(PX, TY + 134 + t * 20, text, "t", 10.5, mono=True)
                    cx, cy = cell_xy(r, j)
                    f.rect(cx + 2, cy + 2, CW - 4, CH - 4, "a fa", 3)
                    f.text(cx + CW / 2, cy + CH / 2 + 4.5, str(rows[r][j][0]), "f", 12.5, "middle", 700, mono=True)
            elif r == n:
                f.text(PX, TY + 134, f"rows {n - 1} to 0 are still to fill", "tm", 10.5)
            else:
                f.text(PX, TY + 134, f"L[0][0] = {rows[0][0][0]}: all of a against all of b", "t",
                       10.5, mono=True)
                f.text(PX, TY + 154, f"{(n + 1) * (m + 1)} cells of 4 bytes: stats: lcs: cells "
                       f"{(n + 1) * (m + 1)}, bytes {4 * (n + 1) * (m + 1)}", "tm", 10.5)
    table_grid(f)
    assert out.strip() == "Files a.txt and b.txt differ", out
    return f


# ------------------------------------------------------------------ the walk and the hunks, 06.02

def walk0602():
    rows, _, tr = lcs_rows("06.02")
    n, m = len(A), len(B)
    walk = []
    for line in tr:
        mm = re.match(r'walk: at (\d+) (\d+), L (\d+): (keep|delete|insert) "(.*?)"(?:: (.*))?$', line)
        if mm:
            walk.append((int(mm.group(1)), int(mm.group(2)), int(mm.group(3)), mm.group(4), mm.group(5),
                         mm.group(6), line))
    out3, tr3 = run("06.02", ["bin/diff", "a.txt", "b.txt"])
    out0, tr0 = run("06.02", ["bin/diff", "-U0", "a.txt", "b.txt"])
    hunks3 = [tuple(map(int, re.match(r"hunk: edits (\d+) to (\d+)", l).groups())) for l in tr3
              if l.startswith("hunk:")]
    hunks0 = [tuple(map(int, re.match(r"hunk: edits (\d+) to (\d+)", l).groups())) for l in tr0
              if l.startswith("hunk:")]
    body3 = out3.split("\n")[2:-1]
    body0 = out0.split("\n")[2:-1]
    # a path from corner to corner, diagonal only where the lines are equal
    i = j = 0
    for (wi, wj, L, op, text, why, _) in walk:
        assert (wi, wj) == (i, j) and L == rows[i][j][0]
        if op == "keep":
            assert A[i] == B[j] == text
            i, j = i + 1, j + 1
        elif op == "delete":
            assert A[i] == text
            i += 1
        else:
            assert B[j] == text
            j += 1
    assert (i, j) == (n, m)
    mark = {"keep": " ", "delete": "-", "insert": "+"}

    f = Fig("f0602a", "The walk from L[0][0] to the far corner of the table for ABCABBA and CBABAC, and the "
            "edit script it reads off, printed as hunks", 330)
    table_frame(f, "DS_TRACE=1 bin/diff a.txt b.txt | at 06.02: the table, then the walk")
    for ii in range(n + 1):
        for jj in range(m + 1):
            v, eq = rows[ii][jj]
            table_cell(f, ii, jj, v, eq, "tm")
    table_grid(f)
    PX = 356

    def path(upto, current=True):
        """The cells the walk has stood on, as a chain of boxes; the one deciding now filled."""
        pts = [(w[0], w[1]) for w in walk[:upto + 1]]
        pts.append(walk[upto + 1][:2] if upto + 1 < len(walk) else (n, m))
        for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
            x0, y0 = cell_xy(a0, b0)
            dy, dx = (a1 - a0) * (CH / 2 - 3), (b1 - b0) * (CW / 2 - 3)
            f.line(x0 + CW / 2 + dx, y0 + CH / 2 + dy, x0 + CW / 2 + dx + (b1 - b0) * 6,
                   y0 + CH / 2 + dy + (a1 - a0) * 6, "a")
        for t, (a0, b0) in enumerate(pts):
            x0, y0 = cell_xy(a0, b0)
            now = current and t == len(pts) - 2
            f.rect(x0 + 3, y0 + 3, CW - 6, CH - 6, "a fa" if now else "a f", 3)
            f.text(x0 + CW / 2, y0 + CH / 2 + 4.5, str(rows[a0][b0][0]), "f" if now else "ta", 12, "middle", 700,
                   mono=True)

    def script(upto, y0, hl=None, x=PX):
        f.text(x, y0, "the script so far" if upto + 1 < len(walk) else "the script", "tm", 10.5)
        for k, w in enumerate(walk[:upto + 1]):
            op = mark[w[3]]
            cls = "ta" if (hl is None and k == upto) or (hl is not None and k in hl) else ("t" if op != " " else "tm")
            f.text(x + 4, y0 + 20 + k * 17, f"{k}", "tm", 10, mono=True)
            f.text(x + 22, y0 + 20 + k * 17, f"{op} {w[4]}", cls, 12, weight=600 if op != " " else None, mono=True)

    for k, w in enumerate(walk):
        wi, wj, L, op, text, why, line = w
        if op == "keep":
            cap = (f"At ({wi}, {wj}), L {L}: a's line {wi} and b's line {wj} are both \"{text}\": keep it, and "
                   f"step to the lower right.")
        elif why == "a is done":
            cap = f"At ({wi}, {wj}): a is done, so what is left of b is inserted: \"{text}\". The walk is at the corner."
        elif op == "delete":
            below, right = re.match(r"below (\d+) >= right (\d+)", why).groups()
            tie = " a tie, and a tie deletes:" if below == right else ""
            cap = (f"At ({wi}, {wj}), L {L}: \"{A[wi]}\" is not \"{B[wj]}\". Below {below}, right {right}:{tie} "
                   f"step down, deleting a's \"{text}\".")
        else:
            below, right = re.match(r"below (\d+) < right (\d+)", why).groups()
            cap = (f"At ({wi}, {wj}), L {L}: \"{A[wi]}\" is not \"{B[wj]}\". Below {below}, right {right}: "
                   f"right holds more in common, so step right, inserting b's \"{text}\".")
        with steps.step(f, cap):
            path(k)
            f.text(24, 316, "trace: " + line, "ta", 10.5, weight=600, mono=True)
            script(k, TY - 44)
    # the script as hunks: -U3 (one), then -U0
    for name, hunks, body, ctx in (("-U3", hunks3, body3, 3), ("-U0", hunks0, body0, 0)):
        if ctx == 3:
            cap = (f"bin/diff a.txt b.txt: with 3 lines of context the changes are never more than 6 unchanged "
                   f"lines apart, so the whole script is one hunk, edits {hunks[0][0]} to {hunks[0][1]}: "
                   f"7 lines of a from line 1, 6 of b from line 1.")
        else:
            cap = (f"bin/diff -U0 a.txt b.txt: no context, so every run of changes is a hunk of its own, "
                   f"{len(hunks)} of them. A count of 0 names the line before: +1,0 is no lines of b, just "
                   f"after b's line 1.")
        with steps.step(f, cap):
            path(len(walk) - 1, current=False)
            inside = {e for h in hunks for e in range(h[0], h[1] + 1)}
            script(len(walk) - 1, TY - 44, hl=inside if ctx == 3 else {e for e in inside if walk[e][3] != "keep"})
            HX = PX + 96
            f.text(HX, TY - 44, f"bin/diff {name}: the hunks", "tm", 10.5)
            for t, l in enumerate(body):
                hdr = l.startswith("@@")
                f.text(HX, TY - 24 + t * 17, l, "ta" if hdr else ("t" if l[:1] in "-+" else "tm"), 12,
                       weight=600 if hdr or l[:1] in "-+" else None, mono=True)
            # brackets: which edits each hunk covers
            for h in hunks:
                ya = TY - 44 + 20 + h[0] * 17 - 12
                yb = TY - 44 + 20 + h[1] * 17 + 4
                f.path(f"M{PX - 4} {ya} L{PX - 9} {ya} L{PX - 9} {yb} L{PX - 4} {yb}", "a")
            f.text(24, 316, "trace: hunk: " + ", then ".join(f"edits {a} to {b}" for a, b in hunks), "ta", 10.5,
                   weight=600, mono=True)
    return f


# ------------------------------------------------------------------ Myers' search, 06.03

GX, GY, GS = 60, 92, 34          # the edit graph: point (x, y) at (GX + x*GS, GY + y*GS)


def gp(x, y):
    return GX + x * GS, GY + y * GS


def search0603():
    out, tr = run("06.03", ["bin/diff", "a.txt", "b.txt"])
    n, m = len(A), len(B)
    rounds, path, D = {}, [], None
    for line in tr:
        mm = re.match(r"myers: d (\d+) k (-?\d+): (?:start \(0,0\)|(down|right) from \((\d+),(\d+)\) to "
                      r"\((\d+),(\d+)\)), snake (\d+), reaches \((\d+),(\d+)\)$", line)
        if mm:
            d, k = int(mm.group(1)), int(mm.group(2))
            g = mm.groups()
            edit = None if g[2] is None else (g[2], (int(g[3]), int(g[4])), (int(g[5]), int(g[6])))
            rounds.setdefault(d, []).append((k, edit, int(g[7]), (int(g[8]), int(g[9]))))
            continue
        mm = re.match(r"myers: \((\d+),(\d+)\) reached with d (\d+)$", line)
        if mm:
            D = int(mm.group(3))
            continue
        mm = re.match(r"myers: path \((\d+),(\d+)\) (keep|delete|insert)$", line)
        if mm:
            path.append((int(mm.group(1)), int(mm.group(2)), mm.group(3)))
    assert D == max(rounds) and rounds[D][-1][3] == (n, m)
    for d, pts in rounds.items():              # each point is one edit and a snake from round d-1
        for k, edit, snake, (x, y) in pts:
            assert x - y == k
            sx, sy = (0, 0) if edit is None else edit[2]
            for s in range(snake):
                assert A[sx + s] == B[sy + s]
            assert (sx + snake, sy + snake) == (x, y)
    x = y = 0
    for px, py, op in path:                    # the path: from (0,0), diagonal only where equal
        assert (px, py) == (x, y)
        if op == "keep":
            assert A[x] == B[y]
            x, y = x + 1, y + 1
        elif op == "delete":
            x += 1
        else:
            y += 1
    assert (x, y) == (n, m) and sum(op != "keep" for _, _, op in path) == D

    f = Fig("f0603a", "Myers' search on the edit graph of ABCABBA and CBABAC: in each round d, the furthest "
            "point d edits can reach on each diagonal, until one is the far corner", 430)
    f.text(24, 22, "DS_TRACE=1 bin/diff a.txt b.txt", "t", 11.5, mono=True)
    f.text(616, 22, "at 06.03: Myers' search, the default", "tm", 10.5, "end", mono=True)
    f.text(GX + n * GS / 2, GY - 40, "a, x: a step right deletes a line of a", "tm", 10.5, "middle")
    yl = GY + m * GS / 2
    f.add(f'<text class="tm" x="22" y="{yl}" font-size="10.5" text-anchor="middle" '
          f'transform="rotate(-90 22 {yl})">b, y: a step down inserts</text>')
    for x in range(n):
        f.text(GX + x * GS + GS / 2, GY - 10, A[x], "t", 12.5, "middle", 700, mono=True)
    for x in range(n + 1):
        f.text(GX + x * GS, GY - 24, str(x), "tm", 9.5, "middle", mono=True)
    for y in range(m):
        f.text(GX - 10, GY + y * GS + GS / 2 + 4.5, B[y], "t", 12.5, "end", 700, mono=True)
    for y in range(m + 1):
        f.text(GX - 26, GY + y * GS + 3.5, str(y), "tm", 9.5, "end", mono=True)
    for x in range(n + 1):
        f.line(GX + x * GS, GY, GX + x * GS, GY + m * GS, "m")
    for y in range(m + 1):
        f.line(GX, GY + y * GS, GX + n * GS, GY + y * GS, "m")
    for x in range(n):
        for y in range(m):
            if A[x] == B[y]:
                x0, y0 = gp(x, y)
                f.add(f'<line class="s" x1="{x0 + 4}" y1="{y0 + 4}" x2="{x0 + GS - 4}" y2="{y0 + GS - 4}" '
                      f'stroke-width="1.25" stroke-dasharray="2 3" stroke-linecap="round" opacity="0.55"/>')
    # below the grid: where points past the last line of b land
    yb = GY + m * GS
    for y in (m + 1, m + 2):
        f.line(GX, GY + y * GS, GX + n * GS, GY + y * GS, "m", dash=True)
        f.text(GX - 26, GY + y * GS + 3.5, str(y), "tm", 9.5, "end", mono=True)
    f.text(GX + n * GS + 8, yb + 1.5 * GS + 4, "past the end of b", "tm", 10)
    f.text(GX + n * GS + 8, GY + 10, "dashed:", "tm", 10)
    f.text(GX + n * GS + 8, GY + 24, "a free step,", "tm", 10)
    f.text(GX + n * GS + 8, GY + 38, "lines equal", "tm", 10)
    PX = 392
    kept_top = GY - 44

    def kept(upto):
        """The kept points, round by round: x on each diagonal, as the code keeps them."""
        f.text(PX, kept_top, "kept: x on each diagonal k", "tm", 10.5)
        KX, KW = PX + 34, 18
        for k in range(-D, D + 1):
            f.text(KX + (k + D) * KW, kept_top + 18, str(k), "tm", 9.5, "middle", mono=True)
        for d in range(upto + 1):
            yy = kept_top + 36 + d * 17
            f.text(PX, yy, f"d {d}", "ta" if d == upto else "tm", 10.5, weight=600 if d == upto else None, mono=True)
            for k, edit, snake, (x, y) in rounds[d]:
                f.text(KX + (k + D) * KW, yy, str(x), "ta" if d == upto else "t", 11.5, "middle",
                       700 if d == upto else None, mono=True)
        return kept_top + 36 + D * 17 + 16

    def draw_round(d, cls):
        for k, edit, snake, (x, y) in rounds[d]:
            if edit is not None:
                (sx, sy) = edit[2]
                f.line(*gp(*edit[1]), *gp(sx, sy), cls, arrow=snake == 0 and cls == "a")
            else:
                sx, sy = 0, 0
            if snake:
                f.line(*gp(sx, sy), *gp(x, y), cls, arrow=cls == "a")

    def points(d, current, last=False):
        for k, edit, snake, (x, y) in rounds[d]:
            cx, cy = gp(x, y)
            if current:
                f.circle(cx, cy, 4.5, "a fa")
                f.text(cx + 6, cy + 14, f"k {k}", "ta", 10, weight=600, mono=True)
            else:
                f.circle(cx, cy, 3.5 if last else 3, "s f" if last else "m f")

    def round_table(d, ty):
        """Round d as the trace says it: each diagonal's edit, its snake, the point reached."""
        f.text(PX, ty, f"round {d}, from the trace:", "tm", 10.5)
        cols = ((PX + 14, "k", "end"), (PX + 22, "edit from", "start"), (PX + 118, "snake", "middle"),
                (PX + 150, "reaches", "start"))
        for x, head, anchor in cols:
            f.text(x, ty + 18, head, "tm", 9.5, anchor)
        for t, (k, edit, snake, (x, y)) in enumerate(rounds[d]):
            yy = ty + 34 + t * 15
            how = "start" if edit is None else f"{edit[0]} ({edit[1][0]},{edit[1][1]})"
            past = y > m
            for (cx, _, anchor), val in zip(cols, (str(k), how, str(snake), f"({x},{y})")):
                f.text(cx, yy, val, "tm" if past else "t", 10.5, anchor, mono=True)

    for d in sorted(rounds):
        pts = rounds[d]
        if d == 0:
            k, edit, snake, (x, y) = pts[0]
            cap = (f"Round d = 0: no edit yet. From (0,0) the search follows diagonal 0 while the lines are equal: "
                   f"A is not C, so the snake is {snake} long and (0,0) is as far as no edits go.")
        else:
            reach = ", ".join(f"k {k} ({x},{y})" for k, _, _, (x, y) in pts)
            past = [(x, y) for _, _, _, (x, y) in pts if y > m]
            note = (f" {' and '.join(f'({x},{y})' for x, y in past)} {'are' if len(past) > 1 else 'is'} past the "
                    f"end of b: kept, never on a path." if past else "")
            if d == D:
                cap = (f"Round d = {d}: diagonal {pts[-1][0]} reaches ({n},{m}), the far corner, and the search "
                       f"stops: the shortest script has {D} edits.{note}")
            else:
                cap = (f"Round d = {d}: one more edit from round {d - 1}'s points, down or right, whichever lands "
                       f"further on, then a free snake: {reach}.{note}")
        with steps.step(f, cap):
            for dd in range(d):
                draw_round(dd, "m")
            for dd in range(d):
                points(dd, False, last=dd == d - 1)
            draw_round(d, "a")
            points(d, True)
            round_table(d, kept(d) + 4)
    ops = {"keep": " ", "delete": "-", "insert": "+"}
    with steps.step(f, f"The walk back from ({n},{m}): each round's point came from round d-1's on diagonal k+1 or "
                       f"k-1, by the same rule. The path is {D} edits and {len(path) - D} kept lines, a shortest "
                       f"script."):
        for dd in range(D + 1):
            points(dd, False)
        pts = [(px, py) for px, py, _ in path] + [(n, m)]
        f.path("M" + " L".join(f"{gp(x, y)[0]} {gp(x, y)[1]}" for x, y in pts), "a")
        for (x, y) in pts:
            f.circle(*gp(x, y), 3.5, "a fa")
        ty = kept(D)
        f.text(PX, ty + 4, "the script, from the path:", "tm", 10.5)
        f.text(PX, ty + 24, "  ".join(f"{ops[op]}{A[x] if op != 'insert' else B[y]}" for x, y, op in path), "ta",
               12, weight=600, mono=True)
        kept_lines = "".join(A[x] for x, y, op in path if op == "keep")
        f.text(PX, ty + 44, f"kept: {kept_lines}, {len(kept_lines)} lines, as many as", "t", 10.5)
        f.text(PX, ty + 60, "the table's walk kept", "t", 10.5)
    body = out.split("\n")[2:-1]
    assert body[0] == "@@ -1,7 +1,6 @@", body
    return f


# ------------------------------------------------------------------ patch, 06.04

def offset0604():
    d = project("06.04")
    diff = subprocess.run(["diff", "-u", "old.txt", "new.txt"], cwd=d, capture_output=True, text=True).stdout
    with open(os.path.join(d, "change.diff"), "w") as fh:
        fh.write(diff)
    out, tr = run("06.04", ["bin/patch", "-s", "-o", "-", "moved.txt", "change.diff"])
    tries = []
    for line in tr:
        mm = re.match(r"patch: hunk of line (\d+) at line (\d+): (?:line (\d+) differs|(fits))$", line)
        tries.append((int(mm.group(2)), int(mm.group(3)) if mm.group(3) else None))
    hunk = diff.split("\n")[2:-1]
    moved = open(os.path.join(d, "moved.txt")).read().split("\n")[:-1]
    result = out.split("\n")[:-1]
    olds = [l for l in hunk[1:] if l[:1] in " -"]
    assert tries[-1][1] is None and len(tries) == 3, tries

    def short(s):
        s = s.strip()
        mm = re.match(r"([IVX]+)\.\s+(.*)$", s)
        return f"{mm.group(1)}. {mm.group(2)}" if mm else (s or "(empty line)")

    def roman(s):
        mm = re.match(r"\s*([IVX]+)\.", s)
        return mm.group(1) if mm else "?"

    f = Fig("f0604a", "patch looking for where a hunk's old lines are: the header says line 1, the file has two "
            "lines more at the top, and the lines are found at line 3", 330)
    f.text(24, 22, "DS_TRACE=1 bin/patch moved.txt change.diff", "t", 11.5, mono=True)
    f.text(616, 22, "moved.txt: old.txt, two lines put on top", "tm", 10.5, "end")
    # the hunk
    HX, Y0, LH = 24, 74, 20
    f.text(HX, Y0 - 22, "change.diff: its one hunk", "tm", 10.5)
    f.text(HX, Y0, hunk[0], "ta", 11.5, weight=600, mono=True)
    for t, l in enumerate(hunk[1:]):
        cls = "t" if l[0] in "-+" else "tm"
        f.text(HX, Y0 + (t + 1) * LH, f"{l[0]} {roman(l[1:])}" + (" Murder" if "Murder" in l else
                                                                  " Mystery" if "Mystery" in l else ""),
               cls, 11.5, weight=600 if l[0] in "-+" else None, mono=True)
    f.text(HX, Y0 + (len(hunk)) * LH + 8, "its old lines, ' ' and '-':", "tm", 10)
    f.text(HX, Y0 + (len(hunk)) * LH + 22, f"{len(olds)}, from line 1", "tm", 10)
    # the file, numbered
    FX = 166
    f.text(FX, Y0 - 22, "moved.txt", "tm", 10.5)
    for t, l in enumerate(moved):
        y = Y0 + t * LH
        f.text(FX + 12, y, str(t + 1), "tm", 10, "end", mono=True)
        f.text(FX + 20, y, short(l), "t", 10, mono=True)
    # the places tried, each a column: the hunk's old lines laid against the file from that line
    TXs = [390, 442, 494]
    for c, (at, bad) in enumerate(tries):
        x = TXs[c]
        fits = bad is None
        f.text(x + 22, Y0 - 22, f"at {at}", "ta" if fits else "t", 10.5, "middle", 600)
        top = Y0 + (at - 1) * LH - 14
        f.rect(x, top, 44, len(olds) * LH, "a af" if fits else "m", 4, dash=not fits)
        for t, ol in enumerate(olds):
            fl = at - 1 + t
            line_no = fl + 1
            compared = fits or line_no <= bad
            same = compared and (line_no != bad)
            y = Y0 + fl * LH
            f.text(x + 8, y, roman(ol[1:]), "ta" if fits else ("t" if compared else "tm"), 10.5,
                   weight=600 if compared else None, mono=True)
            if compared:
                f.text(x + 38, y, "=" if same else "x", "ta" if same else "t", 11, "end", 700, mono=True)
        below = Y0 + (at - 1 + len(olds)) * LH + 2
        if fits:
            f.text(x + 22, below, "fits", "ta", 9.5, "middle", 600)
        else:
            f.text(x + 22, below, f"line {bad}", "tm", 9.5, "middle")
            f.text(x + 22, below + 12, "differs", "tm", 9.5, "middle")
    # the result
    f.text(616, Y0 - 22, "the result", "tm", 10.5, "end")
    for t, l in enumerate(result):
        new = "VII" in l or "Murder" in l
        label = roman(l) + (" Murder" if "Murder" in l else "") if roman(l) != "?" else ("note" if l else "(empty)")
        f.text(616, Y0 + t * LH, label, "ta" if new else "t", 11, "end", 600 if new else None, mono=True)
    for t, line in enumerate(tr):
        f.text(FX, 258 + t * 15, "trace: " + line, "tm" if "differs" in line else "ta", 10,
               weight=None if "differs" in line else 600, mono=True)
    shift = tries[-1][0] - 1
    f.text(FX, 312, f"patching file moved.txt, then: Hunk #1 succeeded at {tries[-1][0]} (offset {shift} lines).",
           "t", 10.5, mono=True)
    return f


def main():
    for name, fn, stepped in (("06.01-table", table0601, True), ("06.02-walk", walk0602, True),
                              ("06.03-search", search0603, True), ("06.04-offset", offset0604, False)):
        fig = fn()
        text = fig.svg()
        if stepped:
            print(name, "steps:", steps.check(text))
        print(write(MOD, name, fig))


if __name__ == "__main__":
    main()
