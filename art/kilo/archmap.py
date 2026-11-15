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

Extensions (optional modules, EXTENSIONS below). An extension stands on the
finished core and on no other extension, so its lessons' maps show the whole
core as built plus that extension's own pieces, and nothing of any other
extension (as xv6's maps count an extension built only inside itself; kilo's
core maps stay as they were, with no slot kept for one). Its pieces go where
the code puts them, which may move a core piece aside or send a connector
another way: an entry says so, and the core lessons' maps never see it. Adding
an extension is adding its entry.
"""
import os
import re
import sys

import figlib
from figlib import Fig, write

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
figlib.LESSONS = os.path.join(ROOT, "tracks", "kilo", "lessons")
sys.path.insert(0, ROOT)
from harness.web.art import sanitize  # noqa: E402

MODULES = {"00": "00-workbench", "01": "01-terminal", "02": "02-screen", "03": "03-viewer",
           "04": "04-editor", "05": "05-search"}

# The grid: five columns, four rows.
W, H = 106, 44
COLS = [14, 140, 266, 392, 518]
RIGHT = COLS[4] + W                      # 624
ROWS = [14, 80, 146, 212]
HEIGHT = 300
PITCH = ROWS[1] - ROWS[0]                # 66: an extension's row under the grid is ROWS[3] + PITCH


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


def core_links():
    """The connectors between the core's pieces, in drawing order: (from, to, points)."""
    top = ROWS
    bot = [y + H for y in ROWS]
    return [
        # keys in, down the left: the terminal, read a key, the key handler
        ("term", "key", [(cx(0), bot[0] + 1), (cx(0), top[1] - 2)]),
        ("key", "handler", [(cx(0), bot[1] + 1), (cx(0), top[2] - 2)]),
        # the handler calls one action per key
        *[("handler", k, [(cx(i), bot[2] + 1), (cx(i), top[3] - 2)])
          for i, k in enumerate(("cursor", "find", "save", "edit"))],
        # an edit changes the rows; the way back goes up the right
        ("edit", "rows", [(COLS[3] + W + 1, ROWS[3] + H / 2), (COLS[4] - 2, ROWS[3] + H / 2)]),
        ("rows", "render", [(cx(4), top[3] - 1), (cx(4), bot[2] + 2)]),
        ("render", "frame", [(cx(4), top[2] - 1), (cx(4), bot[1] + 2)]),
        ("status", "frame", [(COLS[1] + W + 1, ROWS[1] + H / 2), (COLS[2] - 2, ROWS[1] + H / 2)]),
        # the window size, asked of the terminal, sizes the frame
        ("term", "size", [(COLS[3] + W + 1, ROWS[0] + H / 2), (COLS[4] - 2, ROWS[0] + H / 2)]),
        ("size", "frame", [(cx(4), bot[0] + 1), (cx(4), top[1] - 2)]),
        # the frame goes to the terminal in one write()
        ("frame", "term", [(cx(3) - 40, top[1] - 1), (cx(3) - 40, bot[0] + 2)]),
    ]


# ---------------------------------------------------------------- extensions
#
# One entry per optional module:
#   dir       its lessons' directory under tracks/kilo/lessons/
#   height    the map's height: HEIGHT + PITCH when a piece needs a row under the grid,
#             at y = ROWS[3] + PITCH (the legend moves down with it)
#   move      core pieces it draws elsewhere: key -> (x, y, w)
#   reroute   core connectors it changes: (from, to) -> [(from, to, points)], [] to drop one
#   pieces    its own pieces, as PIECES
#   links     its own connectors, as core_links()
#   lessons   (id, title, pieces that lesson builds), in order
#
# 06, syntax highlighting. editorUpdateRow makes a row's render, then calls
# editorUpdateSyntax, which gives every character of render a class (hl); the
# frame reads hl and sends a colour where it changes. So "highlight" goes between
# render and the frame, on the way up the right: the frame gives up the right-hand
# column to it and takes the colours from it, and the window size reaches the frame
# round it. The syntax it reads (chosen by the file's name, with its comment marks
# and keywords) is part of the same piece. 06.05's code is in editorFind: the match
# coloured in its row, the row's colours put back after; it hangs off find, in a
# row of its own under the grid.

_BOT = [y + H for y in ROWS]
_MID1 = ROWS[1] + H / 2                  # the frame's row, half way down
_ELBOW = (_BOT[0] + ROWS[1]) / 2          # between the terminal's row and the frame's

EXTENSIONS = {
    "06": {
        "dir": "06-highlighting",
        "height": HEIGHT + PITCH,
        "move": {"frame": (COLS[2], ROWS[1], COLS[3] + W - COLS[2])},
        "reroute": {
            ("render", "frame"): [("render", "highlight", [(cx(4), ROWS[2] - 1), (cx(4), _BOT[1] + 2)]),
                                  ("highlight", "frame", [(COLS[4] - 1, _MID1), (COLS[3] + W + 2, _MID1)])],
            ("size", "frame"): [("size", "frame", [(cx(4), _BOT[0] + 1), (cx(4), _ELBOW),
                                                   (cx(3) + 30, _ELBOW), (cx(3) + 30, ROWS[1] - 2)])],
        },
        "pieces": {
            "highlight": ("highlight", "chars -> colours", COLS[4], ROWS[1], W),
            "match": ("match", "blue while found", COLS[1], ROWS[3] + PITCH, W),
        },
        "links": [("find", "match", [(cx(1), _BOT[3] + 1), (cx(1), ROWS[3] + PITCH - 2)])],
        "lessons": [
            ("06.01", "A colour for every character", {"highlight"}),
            ("06.02", "Numbers and strings", {"highlight"}),
            ("06.03", "Comments, on one line and across many", {"highlight"}),
            ("06.04", "Keywords", {"highlight"}),
            ("06.05", "Showing the match", {"match"}),
        ],
    },
}


def draw(lid, title, here, built, ext=None):
    """The map for lesson lid: the pieces in here in the accent, those in built solid, the
    rest dashed. ext: the extension the lesson belongs to (an EXTENSIONS entry), or None."""
    ext = ext or {}
    f = Fig("map" + lid.replace(".", ""), f"Where {lid} fits: {title}", ext.get("height", HEIGHT))

    def state(k):
        return "here" if k in here else ("built" if k in built else "later")

    def link(a, b, pts, arrow=True):
        """A connector between two pieces, muted unless both are built or here."""
        live = state(a) != "later" and state(b) != "later"
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        f.path(d, "s" if live else "m", arrow=arrow, dash=not live)

    reroute = ext.get("reroute", {})
    for a, b, pts in core_links():
        for a2, b2, pts2 in reroute.get((a, b), [(a, b, pts)]):
            link(a2, b2, pts2)
    for a, b, pts in ext.get("links", []):
        link(a, b, pts)

    move = ext.get("move", {})
    pieces = [(k, (name, sub) + move.get(k, (x, y, w))) for k, (name, sub, x, y, w) in PIECES.items()]
    pieces += list(ext.get("pieces", {}).items())
    for k, (name, sub, x, y, w) in pieces:
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
    ly = f.h - 12
    x = 16
    for cls, dash, label, tcls in (("a af", False, f"{lid}: this lesson", "ta"), ("s f", False, "built earlier", "t"),
                                   ("m f", True, "still to come", "tm")):
        f.rect(x, ly - 13, 22, 16, cls, 4, dash=dash)
        f.text(x + 30, ly, label, tcls, 14, weight=600 if tcls == "ta" else None)
        x += 30 + len(label) * 14 * 0.56 + 28
    return f


def sane(svg, what):
    """svg, once the site's sanitizer (harness/web/art.py) has kept every element and every
    attribute of it; stop if it would refuse or cut any."""
    out = sanitize(svg)
    tags = re.findall(r"<(\w+)", svg)
    attrs = sorted(re.findall(r'\s([\w-]+)="', svg) + ["aria-hidden", "focusable"])
    if not out or re.findall(r"<(\w+)", out) != tags or sorted(re.findall(r'\s([\w-]+)="', out)) != attrs:
        raise SystemExit(f"the sanitizer would refuse or cut {what}")
    return svg


def check(fig):
    sane(fig.svg(), fig.title)
    return fig


def main():
    built = set()
    for lid, title, builds, highlight in LESSONS:
        here = highlight if highlight is not None else builds
        print(write(MODULES[lid[:2]], f"{lid}-map", check(draw(lid, title, here, built - here))))
        built |= builds
    for mid, ext in EXTENSIONS.items():
        built = set(ALL)                     # the whole core, and the extension so far
        for lid, title, builds in ext["lessons"]:
            assert lid[:2] == mid, lid
            print(write(ext["dir"], f"{lid}-map", check(draw(lid, title, builds, built - builds, ext))))
            built |= builds


if __name__ == "__main__":
    main()
