"""Figures, cover and icon for db module 00, The workbench (lessons 00.01, 00.02).

    python3 art/db/figs00.py

Every number drawn here comes from a real run on the reference engine (Apple M4
Pro, macOS 26.6.2, sqlite3 3.54.1): the benchmark table in 00.02, the start-up
times it printed, and the autocommit timings of 00.02's Break it.
"""
import os

import figart
import figlib
from figlib import Fig, write, tw

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "db", "lessons")
MOD = "00-workbench"


def hair(f, x1, y1, x2, y2):
    """A 1px recessive gridline."""
    f.add(f'<line class="m" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke-width="1"/>')


def hbar(f, x, y, w, h, cls="fa", r=4):
    """A horizontal bar from a baseline at x: square at the baseline, rounded at the data end."""
    r = min(r, w / 2, h / 2)
    if w <= 0:
        return
    f.add(f'<path class="{cls}" d="M{x:.1f} {y:.1f} H{x + w - r:.1f} Q{x + w:.1f} {y:.1f} {x + w:.1f} {y + r:.1f} '
          f'V{y + h - r:.1f} Q{x + w:.1f} {y + h:.1f} {x + w - r:.1f} {y + h:.1f} H{x:.1f} Z"/>')


# ------------------------------------------------------------------ 00.01

def one_statement():
    f = Fig("f0001a", "One SELECT through the engine, file by file", 404)
    f.rect(24, 12, 592, 34, "s fs", 8)
    f.text(40, 34, "db> SELECT name FROM users WHERE id = 7;", "t", 13, mono=True)
    rows = [
        ("main.c", "the shell: read text until a ;  then hand it over", "00"),
        ("tokenize.c", None, "03"),
        ("parse.c", "a SELECT tree: column name, table users, id = 7", "03"),
        ("schema.c", "the catalog: users has columns id, name; data at page 2", "03"),
        ("plan.c", "id is the key: look up row 7, do not read every row", "05"),
        ("exec.c, expr.c", "run the plan: keep the column name, print it", "04"),
        ("btree.c", "search page 2, the root of users' tree, for key 7", "02"),
        ("record.c", "the row's bytes become the values 7 and 'ken'", "01"),
        ("pager.c", "page 2 from memory, or 4096 bytes read at offset 4096", "01"),
        ("journal.c, wal.c", "not used: a SELECT changes nothing", "06"),
    ]
    y0, rh, gap = 62, 26, 5
    for i, (name, what, mod) in enumerate(rows):
        y = y0 + i * (rh + gap)
        idle = name.startswith("journal")
        f.rect(48, y, 470, rh, "m f" if idle else "s f", 6, dash=idle)
        f.text(60, y + 17, name, "tm" if idle else "t", 12, weight=600, mono=True)
        f.rect(530, y + 3, 86, rh - 6, "m f" if idle else "a af", 10, dash=idle)
        f.text(573, y + 17, "module " + mod, "tm" if idle else "ta", 11, "middle", 600)
        if what is None:
            x = 196
            for tok in ("SELECT", "name", "FROM", "users", "WHERE", "id", "=", "7", ";"):
                w = tw(tok, 10.5, True) + 8
                f.rect(x, y + 5, w, rh - 10, "m fs", 3)
                f.text(x + w / 2, y + 17, tok, "t", 10.5, "middle", mono=True)
                x += w + 3
            continue
        f.text(196, y + 17, what, "tm", 11.5)
    yb = y0 + len(rows) * (rh + gap)
    f.line(32, 50, 32, yb + 4, "m", arrow=True)
    f.text(24, yb + 26, "learn.db", "t", 12, weight=600, mono=True)
    for k, label in enumerate(("page 1: the catalog", "page 2: users' rows")):
        x = 100 + k * 150
        f.rect(x, yb + 10, 140, 24, "a af" if k == 1 else "s f", 4)
        f.text(x + 70, yb + 26, label, "ta" if k == 1 else "t", 11, "middle")
    f.text(400, yb + 26, "two pages of 4096 bytes", "tm", 11)
    return f


def repl_loop():
    f = Fig("f0001b", "The loop in main.c's repl()", 322)
    L, LW, R, RW, H = 40, 236, 356, 260, 34
    cx = L + LW / 2
    boxes = [
        (16, "print  db>  or  ...>", True),
        (72, "getline(): one line", True),
        (128, "buffer empty and the line starts with . ?", False),
        (184, "append the line to the buffer", False),
        (240, "sql_complete(buffer) ?", True),
    ]
    for y, label, mono in boxes:
        f.rect(L, y, LW, H, "s f", 8)
        f.text(cx, y + 21, label, "t", 11.5 if not mono else 12, "middle", mono=mono)
    for (y1, _, _), (y2, _, _) in zip(boxes, boxes[1:]):
        f.line(cx, y1 + H, cx, y2 - 2, "s", arrow=True)
    f.text(cx + 8, 178, "no", "tm", 11)
    # right column
    right = [
        (72, "end of input: run what is left", "exit 1 if a statement failed", "s fs"),
        (128, "dot_command()", ".tables  .schema  .help  .exit", "s f"),
        (240, "db_exec(buffer)", "then empty the buffer", "a af"),
    ]
    for y, label, sub, cls in right:
        f.rect(R, y, RW, H + 8, cls, 8)
        acc = cls.startswith("a")
        f.text(R + 14, y + 17, label, "ta" if acc else "t", 12, weight=600, mono=label.endswith(")"))
        f.text(R + 14, y + 33, sub, "tm", 10.5, mono=sub.startswith("."))
    for y, lab in ((89, "EOF"), (145, "yes"), (257, "yes")):
        f.line(L + LW, y, R - 2, y, "a" if lab == "yes" and y == 257 else "s", arrow=True)
        f.text((L + LW + R) / 2, y - 6, lab, "tm", 11, "middle")
    # back to the prompt: from dot_command and db_exec on the right
    f.path(f"M{R + RW} 149 H{R + RW + 12} V33 H{L + LW + 2}", "m", arrow=True)
    f.path(f"M{R + RW} 261 H{R + RW + 12} V149", "m")
    # sql_complete says no: keep reading, with the ...> prompt
    f.path(f"M{L} 257 H{L - 16} V33 H{L - 2}", "s", arrow=True)
    f.text(L - 20, 148, "no", "tm", 11, "end")
    f.text(L, 300, "A statement may span lines: only a ; outside quotes and comments ends it.", "tm", 11)
    return f


# ------------------------------------------------------------------ 00.02

def one_number():
    f = Fig("f0002a", "How one number in the benchmark table is made", 282)
    f.text(24, 22, "one workload on one engine: here range scan, 100 rows each, on ./db (full run)", "tm", 11)
    y, h = 40, 44
    steps = [(24, 120, "set-up", "copy base.db", "s fs"), (156, 74, "warm-up", "not timed", "s fs"),
             (242, 58, "run 1", "", "a af"), (306, 58, "run 2", "", "a af"), (370, 58, "run 3", "", "a af"),
             (440, 70, "median", "26.2 ms", "s f"), (522, 94, "ops/s", "1000 / median", "s f")]
    for x, w, top, sub, cls in steps:
        f.rect(x, y, w, h, cls, 6)
        acc = cls.startswith("a")
        f.text(x + w / 2, y + 19 if sub else y + 27, top, "ta" if acc else "t", 12, "middle", 600)
        if sub:
            f.text(x + w / 2, y + 35, sub, "tm", 10.5, "middle", mono=sub[0].isdigit() or sub.startswith("copy"))
    for x1, x2 in ((144, 156), (230, 242), (428, 440), (510, 522)):
        f.line(x1, y + h / 2, x2 - 2, y + h / 2, "s", arrow=True)
    f.brace_h(242, 428, y + h + 10, "m")
    f.text(335, y + h + 26, "timed: wall clock, the whole process", "tm", 10.5, "middle")
    f.text(616, y + h + 26, "38,170 ops/s", "t", 12, "end", 600, True)
    # one run, to scale
    ty, th = 168, 30
    X0, W, total, start = 24, 592, 26.2, 5.4
    ws = W * start / total
    f.text(24, ty - 12, "one timed run, to scale: ./db run.db < w3.sql (1,000 SELECTs on stdin)", "t", 12, weight=600)
    f.rect(X0, ty, ws, th, "s fs", 0)
    f.rect(X0 + ws, ty, W - ws, th, "a af", 0)
    f.text(X0 + ws / 2, ty + 19, "start-up", "t", 11, "middle")
    f.text(X0 + ws + (W - ws) / 2, ty + 19, "parse and run 1,000 SELECTs, print 100,000 rows", "ta", 11, "middle")
    f.text(X0, ty + th + 16, "0", "tm", 10.5, mono=True)
    f.text(X0 + ws, ty + th + 16, "5.4 ms", "tm", 10.5, "middle", mono=True)
    f.text(X0 + W, ty + th + 16, "26.2 ms", "tm", 10.5, "end", mono=True)
    f.text(24, 252, "start-up: start the process, open the file, exit; timed apart with an empty script", "tm", 11)
    f.text(24, 270, "sqlite3 gets the same w3.sql, on a copy of a base file it built itself", "tm", 11)
    return f


# db's medians from two real runs of `./learn bench db` on the same machine:
# --quick (2,000 rows, start-up 2.8 ms) and the full run (100,000 rows, start-up 5.4 ms).
SHARE = [  # workload, ops quick, ops/s quick, ops full, ops/s full
    ("insert, autocommit", 300, 4179, 10000, 3323),
    ("insert, one transaction", 2000, 264345, 100000, 965586),
    ("point lookup by primary key", 2000, 287934, 100000, 608984),
    ("range scan, 100 rows each", 20, 4236, 1000, 38170),
    ("lookup by secondary index", 2000, 269141, 100000, 396036),
    ("update by key, one transaction", 200, 24351, 10000, 181430),
    ("delete by key, one transaction", 200, 46261, 10000, 123257),
]
START_QUICK, START_FULL = 2.8, 5.4


def startup_share():
    f = Fig("f0002b", "How much of each timed run is process start-up", 300)
    X0, W = 236, 360
    pct = lambda v: X0 + W * v / 70.0
    f.text(24, 22, "./db: start-up time / median time of one run", "tm", 11)
    # legend
    f.circle(330, 18, 4.5, "a f")
    f.text(340, 22, "--quick, 2,000 rows", "t", 11)
    f.circle(470, 18, 4.5, "a fa")
    f.text(480, 22, "full run, 100,000 rows", "t", 11)
    top, rh = 46, 30
    for t in (0, 20, 40, 60):
        hair(f, pct(t), top - 6, pct(t), top + rh * len(SHARE) - 6)
        f.text(pct(t), top + rh * len(SHARE) + 10, f"{t}%", "tm", 10.5, "middle", mono=True)
    for i, (name, oq, rq, of, rf) in enumerate(SHARE):
        y = top + i * rh + 8
        q = 100 * START_QUICK / (1000 * oq / rq)
        u = 100 * START_FULL / (1000 * of / rf)
        f.text(X0 - 12, y + 4, name, "t", 11.5, "end")
        f.line(pct(u), y, pct(q), y, "m")
        f.circle(pct(q), y, 4.5, "a f")
        f.circle(pct(u), y, 4.5, "a fa")
        if name.startswith("range"):
            f.text(pct(q) + 10, y + 4, f"{q:.0f}%", "t", 11, mono=True)
            f.text(pct(u) - 10, y + 4, f"{u:.0f}%", "t", 11, "end", mono=True)
    f.text(24, 288, "start-up 2.8 ms in the quick run, 5.4 ms in the full run; time per run = ops / (ops/s)", "tm", 11)
    return f


# Break it: 1,000 autocommit INSERTs, five runs each, median ops/s (00.02).
FSYNC = [("./db, fsync(2) at every commit", 3126, "4,561 3,146 2,984 3,002 3,126"),
         ("./db, sys_fsync() made a no-op", 6042, "3,513 5,910 6,042 7,544 7,803"),
         ("sqlite3, fullfsync=OFF", 3332, "3,605 2,737 1,770 4,040 3,332"),
         ("sqlite3, fullfsync=ON", 78, "79 77 78 78 78")]


def fsync_bars():
    f = Fig("f0002c", "Autocommit inserts per second, by how a commit is flushed", 236)
    f.text(24, 22, "1,000 INSERTs, each its own transaction: median of 5 runs, operations per second", "tm", 11)
    X0, W, vmax = 240, 300, 8000
    top, rh, bh = 44, 40, 20
    for t in (0, 2000, 4000, 6000, 8000):
        x = X0 + W * t / vmax
        hair(f, x, top - 6, x, top + rh * len(FSYNC) - 8)
        f.text(x, top + rh * len(FSYNC) + 8, f"{t:,}", "tm", 10.5, "middle", mono=True)
    for i, (name, med, runs) in enumerate(FSYNC):
        y = top + i * rh
        f.text(X0 - 12, y + 14, name, "t", 11.5, "end")
        hbar(f, X0, y, max(W * med / vmax, 2), bh, "fa")
        f.text(X0 + W * med / vmax + 8, y + 15, f"{med:,}", "t", 12, weight=600, mono=True)
        f.text(X0 - 12, y + 29, runs, "tm", 10, "end", mono=True)
    f.text(24, 226, "fsync(2) on macOS leaves the data in the drive's cache; F_FULLFSYNC (fullfsync=ON) flushes it", "tm", 11)
    return f


# ------------------------------------------------------------------ cover and icon

def cover():
    a = figart.Art("m00db", "The engine, the file it writes, sqlite3 on the same file, and the benchmark")
    a.box(24, 56, 120, 54)
    a.text(40, 79, "src/*.c", mono=True, size=13)
    a.text(40, 97, "13 files of C", "tm", 11)
    a.line(144, 83, 194, 83, arrow=True)
    a.text(169, 74, "make", "tm", 11, "middle", mono=True)
    a.box(196, 56, 104, 54, "a af")
    a.text(212, 79, "./db", "ta", 13, weight=700, mono=True)
    a.text(212, 97, "REPL, one-shot", "tm", 11)
    # the file: a stack of pages
    for k in range(3):
        a.box(386 - k * 6, 40 + k * 6, 112, 80, "s f", rx=6)
    a.text(386 - 12 + 12, 76, "learn.db", mono=True, size=13, weight=600)
    a.text(386 - 12 + 12, 94, "4096-byte pages", "tm", 11)
    a.text(386 - 12 + 12, 110, "SQLite format 3", "tm", 10.5, mono=True)
    a.line(300, 83, 370, 83, "a", arrow=True)
    a.box(528, 56, 88, 54)
    a.text(544, 79, "sqlite3", mono=True, size=13, weight=600)
    a.text(544, 97, "the real one", "tm", 11)
    a.line(528, 83, 500, 83, arrow=True)
    a.text(335, 74, "reads, writes", "ta", 11, "middle")
    a.text(572, 44, "opens the same file", "tm", 11, "middle")
    # the benchmark
    a.box(196, 196, 316, 70, "s fs", rx=12)
    a.text(212, 220, "bench/bench.py", mono=True, size=13, weight=600)
    a.text(212, 240, "the same SQL into both shells, timed", "tm", 11)
    a.text(212, 256, "ops/s per workload, and the file size", "tm", 11)
    a.path("M248 196 C 248 160, 248 140, 248 112", "s", arrow=True)
    a.path("M480 196 C 480 160, 572 150, 572 112", "s", arrow=True)
    a.text(24, 288, "each later lesson is one piece of ./db; this is how the whole is run and measured", "tm", 11)
    return a


ICON = ('<path d="M2.75 13.5a7.25 7.25 0 0 1 14.5 0"/><path d="M10 13.5l3.5-4.5"/>'
        '<path d="M2.75 16.75h14.5"/>')


FIGS = [
    ("00.01-one-statement", one_statement),
    ("00.01-repl-loop", repl_loop),
    ("00.02-one-number", one_number),
    ("00.02-startup-share", startup_share),
    ("00.02-fsync", fsync_bars),
]


def main():
    for name, fn in FIGS:
        print(write(MOD, name, fn()))
    d = os.path.join(figlib.LESSONS, MOD)
    s = cover().svg()
    s.encode("ascii")
    with open(os.path.join(d, "cover.svg"), "w") as fh:
        fh.write(s)
    with open(os.path.join(d, "icon.svg"), "w") as fh:
        fh.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
                 'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + ICON + "</svg>\n")
    print(os.path.join(d, "cover.svg"), os.path.join(d, "icon.svg"))


if __name__ == "__main__":
    main()
