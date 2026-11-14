"""The kilo track's architecture map, one copy per lesson.

    python3 -B art/kilo/archmap.py       writes tracks/kilo/lessons/<module>/figures/NN.LL-map.svg

The same map every time: the pieces of the editor one keypress passes through.
The terminal sends bytes down the left (read a key, the key handler), the handler
calls one of the four actions, an edit changes the rows, and the way back goes
up the right: the rows are rendered, drawn into the frame with the status bar,
and the frame goes to the terminal in one write(). main() is that loop:
editorRefreshScreen(), then editorProcessKeypress(), forever.

In each lesson's copy, the piece that lesson builds (or, for a lab, the pieces it
exercises) is drawn in the accent colour, the pieces built by earlier lessons
are drawn solid, and the pieces still to come are dashed and muted. Lessons
reference it as

    ![Where NN.LL fits](figures/NN.LL-map.svg)

The pieces and who builds them follow tracks/kilo/NOTES.md, "The lessons, and
how they divide the code": raw mode is 01.01's (and main()'s loop with
editorProcessKeypress comes with it, plain code a case per lesson), the window
size 01.03's, the frame (abuf and the one write) 02.01's, and so on.
"""
import os

import figlib
from figlib import Fig, write

figlib.LESSONS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              "tracks", "kilo", "lessons")

MODULES = {"00": "00-workbench", "01": "01-terminal", "02": "02-screen", "03": "03-viewer",
           "04": "04-editor", "05": "05-search"}

# The grid: five columns, four rows.
W, H = 106, 44
COLS = [14, 140, 266, 392, 518]
RIGHT = COLS[4] + W                      # 624
ROWS = [14, 80, 146, 212]


def cx(i):
    return COLS[i] + W / 2


# The pieces: key -> (name, what it does in a few words, x, y, w).
PIECES = {
    "term": ("terminal", "raw mode: bytes in, escape codes out", COLS[0], ROWS[0], COLS[3] + W - COLS[0]),
    "size": ("window size", "height, width", COLS[4], ROWS[0], W),
    "key": ("read a key", "bytes -> one key", COLS[0], ROWS[1], W),
    "status": ("status bar", "and messages", COLS[1], ROWS[1], W),
    "frame": ("frame", "built in memory, one write()", COLS[2], ROWS[1], RIGHT - COLS[2]),
    "handler": ("key handler", "a case per key", COLS[0], ROWS[2], COLS[3] + W - COLS[0]),
    "render": ("render", "tabs -> spaces", COLS[4], ROWS[2], W),
    "cursor": ("cursor", "move, scroll", COLS[0], ROWS[3], W),
    "find": ("find", "as you type", COLS[1], ROWS[3], W),
    "save": ("save", "rows -> the file", COLS[2], ROWS[3], W),
    "edit": ("edit", "insert, delete", COLS[3], ROWS[3], W),
    "rows": ("rows", "the file's lines", COLS[4], ROWS[3], W),
}
ALL = set(PIECES)

# (id, title, pieces this lesson builds, pieces it highlights if not the same: labs).
LESSONS = [
    ("00.01", "How a terminal editor works", set(), ALL),
    ("00.02", "What the terminal sends and understands", set(), {"term", "key", "frame"}),
    ("01.01", "Raw mode", {"term", "handler"}, None),
    ("01.02", "Reading a key", {"key"}, None),
    ("01.03", "The window size", {"size"}, None),
    ("02.01", "One frame, one write", {"frame"}, None),
    ("03.01", "Rows: opening a file", {"rows"}, None),
    ("03.02", "Moving the cursor, and scrolling", {"cursor"}, None),
    ("03.03", "Tabs", {"render"}, None),
    ("03.04", "The status bar and messages", {"status"}, None),
    ("04.01", "Inserting characters", {"edit"}, None),
    ("04.02", "Enter: splitting a line", {"edit"}, None),
    ("04.03", "Deleting, and joining lines", {"edit"}, None),
    ("04.04", "Saving", {"save"}, None),
    ("05.01", "Find as you type", {"find"}, None),
    ("05.02", "Next match, previous match, and going back", {"find"}, None),
]


def draw(lid, title, here, built):
    f = Fig("map" + lid.replace(".", ""), f"Where {lid} fits: {title}", 300)

    def state(k):
        return "here" if k in here else ("built" if k in built else "later")

    def link(a, b, pts, arrow=True):
        """A connector between two pieces, muted unless both are built or here."""
        live = state(a) != "later" and state(b) != "later"
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        f.path(d, "s" if live else "m", arrow=arrow, dash=not live)

    top = ROWS
    bot = [y + H for y in ROWS]
    # keys in, down the left: the terminal, read a key, the key handler
    link("term", "key", [(cx(0), bot[0] + 1), (cx(0), top[1] - 2)])
    link("key", "handler", [(cx(0), bot[1] + 1), (cx(0), top[2] - 2)])
    # the handler calls one action per key
    for i, k in enumerate(("cursor", "find", "save", "edit")):
        link("handler", k, [(cx(i), bot[2] + 1), (cx(i), top[3] - 2)])
    # an edit changes the rows; the way back goes up the right
    link("edit", "rows", [(COLS[3] + W + 1, ROWS[3] + H / 2), (COLS[4] - 2, ROWS[3] + H / 2)])
    link("rows", "render", [(cx(4), top[3] - 1), (cx(4), bot[2] + 2)])
    link("render", "frame", [(cx(4), top[2] - 1), (cx(4), bot[1] + 2)])
    link("status", "frame", [(COLS[1] + W + 1, ROWS[1] + H / 2), (COLS[2] - 2, ROWS[1] + H / 2)])
    # the window size, asked of the terminal, sizes the frame
    link("term", "size", [(COLS[3] + W + 1, ROWS[0] + H / 2), (COLS[4] - 2, ROWS[0] + H / 2)])
    link("size", "frame", [(cx(4), bot[0] + 1), (cx(4), top[1] - 2)])
    # the frame goes to the terminal in one write()
    link("frame", "term", [(cx(3) - 40, top[1] - 1), (cx(3) - 40, bot[0] + 2)])

    for k, (name, sub, x, y, w) in PIECES.items():
        s = state(k)
        if s == "here":
            f.rect(x, y, w, H, "a af", 8)
            f.text(x + w / 2, y + 20, name, "ta", 16, "middle", 700)
            f.text(x + w / 2, y + 36, sub, "ta", 11.5, "middle")
        elif s == "built":
            f.rect(x, y, w, H, "s f", 8)
            f.text(x + w / 2, y + 20, name, "t", 16, "middle", 600)
            f.text(x + w / 2, y + 36, sub, "tm", 11.5, "middle")
        else:
            f.rect(x, y, w, H, "m f", 8, dash=True)
            f.text(x + w / 2, y + 20, name, "tm", 16, "middle", 500)
            f.text(x + w / 2, y + 36, sub, "tm", 11.5, "middle")

    # legend
    ly = 288
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
