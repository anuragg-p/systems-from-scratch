"""The db track's architecture map, one copy per lesson.

    python3 art/db/archmap.py            writes tracks/db/lessons/<module>/figures/NN.LL-map.svg

The same map every time: the layers one SELECT passes through, from SQL text
down to the file. In each lesson's copy, the piece that lesson builds (or, for
a lab, the pieces it exercises) is drawn in the accent colour, the pieces
built by earlier lessons are drawn solid, and the pieces still to come are
dashed and muted. Lessons reference it as

    ![Where NN.LL fits](figures/NN.LL-map.svg)
"""
import os

import figlib
from figlib import Fig, write

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "db", "lessons")

MODULES = {"00": "00-workbench", "01": "01-pages", "02": "02-btree", "03": "03-sql", "04": "04-queries",
           "05": "05-indexes", "06": "06-transactions", "07": "07-fast"}

# The pieces: key -> (name, what it does in a few words, x, y, w).
W, H = 106, 50
COLS = [14, 140, 266, 392, 518]
ROW_A, ROW_B, ROW_C = 16, 94, 172
PIECES = {
    "sql": ("SQL text", "the shell", COLS[0], ROW_A, W),
    "tok": ("tokenizer", "text -> words", COLS[1], ROW_A, W),
    "parse": ("parser", "words -> a tree", COLS[2], ROW_A, W),
    "plan": ("planner", "how to read", COLS[3], ROW_A, W),
    "exec": ("executor", "plan -> rows", COLS[4], ROW_A, W),
    "cat": ("catalog", "the tables", 329, ROW_B, W),
    "journal": ("journal, WAL", "safe commits", 44, ROW_B, 140),
    "rec": ("records", "row <-> bytes", COLS[4], ROW_C, W),
    "btree": ("B-tree", "find by key", COLS[3], ROW_C, W),
    "pager": ("pager", "pages, cache", COLS[2], ROW_C, W),
    "file": ("the file", "4096-byte pages", COLS[0], ROW_C, 232),
}
ALL = set(PIECES)

# (id, title, pieces this lesson builds, pieces it highlights if not the same: labs).
LESSONS = [
    ("00.01", "How a database works", {"sql"}, ALL),
    ("00.02", "Measuring a database", set(), ALL),
    ("01.01", "The database file as pages", {"pager", "file"}, None),
    ("01.02", "The page cache", {"pager"}, None),
    ("01.03", "Records: varints and serial types", {"rec"}, None),
    ("02.01", "A leaf page: cells and search", {"btree"}, None),
    ("02.02", "Insert and split", {"btree"}, None),
    ("02.03", "Interior pages and the root", {"btree"}, None),
    ("02.04", "Cursors and range scans", {"btree"}, None),
    ("02.05", "Delete and free pages", {"btree"}, None),
    ("03.01", "The tokenizer", {"tok"}, None),
    ("03.02", "The parser and the AST", {"parse"}, None),
    ("03.03", "The schema: CREATE TABLE and the catalog", {"cat"}, None),
    ("04.01", "INSERT and a full table scan", {"exec"}, None),
    ("04.02", "WHERE and expressions", {"exec"}, None),
    ("04.03", "ORDER BY and LIMIT", {"exec"}, None),
    ("04.04", "UPDATE and DELETE", {"exec"}, None),
    ("05.01", "An index is a B-tree", {"exec"}, {"exec", "btree"}),
    ("05.02", "Index lookups and range scans", {"exec"}, None),
    ("05.03", "Choosing a plan, and EXPLAIN", {"plan"}, None),
    ("06.01", "What a crash does to a half-written page", set(), {"pager", "file"}),
    ("06.02", "The rollback journal and atomic commit", {"journal"}, None),
    ("06.03", "Recovery", {"journal"}, None),
    ("06.04", "A write-ahead log", {"journal"}, None),
    ("07.01", "Reading the benchmark", set(), ALL),
    ("07.02", "Where the time goes", set(), {"btree", "pager", "journal"}),
    ("07.03", "One more optimisation, measured", {"btree"}, None),
]


def draw(lid, title, here, built):
    f = Fig("map" + lid.replace(".", ""), f"Where {lid} fits: {title}", 290)

    def state(k):
        return "here" if k in here else ("built" if k in built else "later")

    def center(k):
        _, _, x, y, w = PIECES[k]
        return x + w / 2, y + H / 2

    def link(a, b, pts, arrow=True):
        """A connector between two pieces, muted unless both are built or here."""
        live = state(a) != "later" and state(b) != "later"
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        f.path(d, "s" if live else "m", arrow=arrow, dash=not live)

    # the flow of one SELECT
    for a, b in (("sql", "tok"), ("tok", "parse"), ("parse", "plan"), ("plan", "exec")):
        xa = PIECES[a][2] + W
        xb = PIECES[b][2]
        link(a, b, [(xa + 1, ROW_A + H / 2), (xb - 2, ROW_A + H / 2)])
    link("exec", "rec", [(COLS[4] + W / 2, ROW_A + H + 1), (COLS[4] + W / 2, ROW_C - 2)])
    link("rec", "btree", [(COLS[4] - 1, ROW_C + H / 2), (COLS[3] + W + 2, ROW_C + H / 2)])
    link("btree", "pager", [(COLS[3] - 1, ROW_C + H / 2), (COLS[2] + W + 2, ROW_C + H / 2)])
    link("pager", "file", [(COLS[2] - 1, ROW_C + H / 2), (COLS[0] + 232 + 2, ROW_C + H / 2)])
    # the catalog: consulted by the parser and the planner, kept in a B-tree
    link("cat", "parse", [(352, ROW_B - 1), (330, ROW_A + H + 1)], arrow=False)
    link("cat", "plan", [(414, ROW_B - 1), (436, ROW_A + H + 1)], arrow=False)
    link("cat", "btree", [(420, ROW_B + H + 1), (432, ROW_C - 1)], arrow=False)
    # commits: the pager writes through the journal or the WAL
    link("pager", "journal", [(292, ROW_C - 1), (292, ROW_B + H / 2), (44 + 140 + 2, ROW_B + H / 2)])
    link("journal", "file", [(114, ROW_B + H + 1), (114, ROW_C - 2)])

    for k, (name, sub, x, y, w) in PIECES.items():
        s = state(k)
        if s == "here":
            f.rect(x, y, w, H, "a af", 8)
            f.text(x + w / 2, y + 23, name, "ta", 16, "middle", 700)
            f.text(x + w / 2, y + 40, sub, "ta", 11.5, "middle")
        elif s == "built":
            f.rect(x, y, w, H, "s f", 8)
            f.text(x + w / 2, y + 23, name, "t", 16, "middle", 600)
            f.text(x + w / 2, y + 40, sub, "tm", 11.5, "middle")
        else:
            f.rect(x, y, w, H, "m f", 8, dash=True)
            f.text(x + w / 2, y + 23, name, "tm", 16, "middle", 500)
            f.text(x + w / 2, y + 40, sub, "tm", 11.5, "middle")

    # legend
    ly = 262
    x = 16
    for cls, dash, label, tcls in (("a af", False, f"{lid}: this lesson", "ta"), ("s f", False, "built earlier", "t"),
                                   ("m f", True, "still to come", "tm")):
        f.rect(x, ly - 13, 22, 16, cls, 4, dash=dash)
        f.text(x + 30, ly, label, tcls, 14, weight=600 if tcls == "ta" else None)
        x += 30 + len(label) * 14 * 0.56 + 28
    return f


def main():
    built = set()
    for lid, title, builds, highlight in LESSONS:
        here = highlight if highlight is not None else builds
        print(write(MODULES[lid[:2]], f"{lid}-map", draw(lid, title, here, built - here)))
        built |= builds


if __name__ == "__main__":
    main()
