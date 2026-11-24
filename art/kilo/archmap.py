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

# 07, a language server client. The editor now sits between two outside worlds: the terminal
# above, the server below, in three rows under the grid. Row 4 is the client's features, each
# under the core piece it works with: wait (poll(), 07.04) under the cursor's column, which read a
# key now calls before it reads; definition (07.07), which moves the cursor; JSON (07.03); sync
# (07.05), which sends the rows' text; diagnostics (07.06), which the frame draws as underlines.
# Row 5 is messages (07.02), the frames that go out and come in, across all five columns. Row 6 is
# the server, across the terminal's four columns, and start (fork, exec, pipes: 07.01) beside it,
# as the window size sits beside the terminal. read a key -> wait goes down the left margin (read
# a key, and wait, start 12 in to make room for it), diagnostics -> frame up the right margin (the
# frame gives up 12 at its right end); definition -> cursor and rows -> sync are elbows in the gap
# between rows 3 and 4, each at its own height so its arrowhead has room.
_R4, _R5, _R6 = ROWS[3] + PITCH, ROWS[3] + 2 * PITCH, ROWS[3] + 3 * PITCH
_MARGIN_L, _MARGIN_R = 7, RIGHT + 8      # the corridors down the left and up the right
_IN = 12                                 # what a piece gives up to make a corridor
_WAIT_X = (COLS[0] + _IN + COLS[0] + W) / 2


# 08, undo and redo. Two rows under the grid. Row 4: steps (08.03) under the cursor's column, which
# the key handler feeds with every key (undoKey); the saved point (08.04) under save, which sets it;
# redo (08.02); records (08.01) under rows, whose row functions make them. Row 5: the history,
# the two stacks of steps, across all five columns. The key handler -> steps goes down the left
# margin (the handler and the cursor start 12 in to make room for it, as read a key and wait do
# in 07), and history -> rows, the way an undo changes the rows, up the right margin (rows gives
# up 12 at its right end, as the frame does in 07). Redo takes a step from the history and gives
# it back: two short arrows side by side.
_UNDO_MID = (COLS[0] + _IN + COLS[0] + W) / 2        # the middle of steps, 12 in


def _down(x, top_row, bottom_row):
    """A short vertical from the bottom of a piece in one row to the top of the next."""
    return [(x, top_row + H + 1), (x, bottom_row - 2)]


def _up(x, top_row, bottom_row):
    return [(x, bottom_row - 1), (x, top_row + H + 2)]

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
    "07": {
        "dir": "07-language-server",
        "height": HEIGHT + 3 * PITCH,
        "move": {"key": (COLS[0] + _IN, ROWS[1], W - _IN),
                 "frame": (COLS[2], ROWS[1], RIGHT - COLS[2] - _IN)},
        "reroute": {},
        "pieces": {
            "wait": ("wait", "key or message", COLS[0] + _IN, _R4, W - _IN),
            "definition": ("definition", "ask, then jump", COLS[1], _R4, W),
            "json": ("JSON", "text -> a tree", COLS[2], _R4, W),
            "sync": ("sync", "the text as typed", COLS[3], _R4, W),
            "diagnostics": ("diagnostics", "underlines", COLS[4], _R4, W),
            "messages": ("messages", "frames out, frames in", COLS[0], _R5, RIGHT - COLS[0]),
            "server": ("server", "clangd, another process: JSON in, JSON out", COLS[0], _R6, COLS[3] + W - COLS[0]),
            "start": ("start", "fork, exec, pipes", COLS[4], _R6, W),
        },
        "links": [
            # read a key waits for a key or a message first: down the left margin
            ("key", "wait", [(COLS[0] + _IN - 1, _MID1), (_MARGIN_L, _MID1), (_MARGIN_L, _R4 + H / 2),
                             (COLS[0] + _IN - 2, _R4 + H / 2)]),
            # a jump moves the cursor; sync takes the rows' text: elbows between rows 3 and 4
            ("definition", "cursor", [(COLS[1] + 22, _R4 - 1), (COLS[1] + 22, _BOT[3] + 15), (cx(0), _BOT[3] + 15),
                                      (cx(0), _BOT[3] + 2)]),
            ("rows", "sync", [(cx(4), _BOT[3] + 1), (cx(4), _BOT[3] + 7), (cx(3) + 22, _BOT[3] + 7),
                              (cx(3) + 22, _R4 - 2)]),
            # the frame draws the diagnostics: up the right margin
            ("diagnostics", "frame", [(RIGHT + 1, _R4 + H / 2), (_MARGIN_R, _R4 + H / 2), (_MARGIN_R, _MID1),
                                      (RIGHT - _IN + 2, _MID1)]),
            # each feature sends or reads messages
            ("wait", "messages", _down(_WAIT_X, _R4, _R5)),
            ("definition", "messages", _down(cx(1), _R4, _R5)),
            ("sync", "messages", _down(cx(3), _R4, _R5)),
            ("messages", "json", _up(cx(2), _R4, _R5)),
            ("messages", "diagnostics", _up(cx(4), _R4, _R5)),
            # the two pipes: frames out, frames in
            ("messages", "server", _down(cx(1) + 52, _R5, _R6)),
            ("server", "messages", _up(cx(1) + 84, _R5, _R6)),
            # start runs the server
            ("start", "server", [(COLS[4] - 1, _R6 + H / 2), (COLS[3] + W + 2, _R6 + H / 2)]),
        ],
        "lessons": [
            ("07.01", "Starting a server: fork, exec and three pipes", {"start", "server"}),
            ("07.02", "Messages: Content-Length and JSON-RPC", {"messages"}),
            ("07.03", "Reading JSON: just enough of a parser", {"json"}),
            ("07.04", "Keys and the server at once: poll()", {"wait"}),
            ("07.05", "Telling the server what you see: didOpen and didChange", {"sync"}),
            ("07.06", "Diagnostics: errors as you type", {"diagnostics"}),
            ("07.07", "Go to definition", {"definition"}),
        ],
    },
    "08": {
        "dir": "08-undo",
        "height": HEIGHT + 2 * PITCH,
        "move": {"handler": (COLS[0] + _IN, ROWS[2], COLS[3] + W - COLS[0] - _IN),
                 "cursor": (COLS[0] + _IN, ROWS[3], W - _IN),
                 "rows": (COLS[4], ROWS[3], W - _IN)},
        "reroute": {},
        "pieces": {
            "steps": ("steps", "a run of keys", COLS[0] + _IN, _R4, W - _IN),
            "saved": ("saved point", "is the text the file?", COLS[2], _R4, W),
            "redo": ("redo", "a record, reversed", COLS[3], _R4, W),
            "records": ("records", "what a row was", COLS[4], _R4, W),
            "history": ("history", "steps to take back and to put back, 8 MB at most", COLS[0], _R5,
                        RIGHT - COLS[0]),
        },
        "links": [
            # every key goes to undoKey() first: down the left margin
            ("handler", "steps", [(COLS[0] + _IN - 1, ROWS[2] + H / 2), (_MARGIN_L, ROWS[2] + H / 2),
                                  (_MARGIN_L, _R4 + H / 2), (COLS[0] + _IN - 2, _R4 + H / 2)]),
            # save sets the saved point; a row about to change is recorded
            ("save", "saved", _down(cx(2), ROWS[3], _R4)),
            ("rows", "records", _down(cx(4), ROWS[3], _R4)),
            # into the history: steps, the saved point, records
            ("steps", "history", _down(_UNDO_MID, _R4, _R5)),
            ("saved", "history", _down(cx(2), _R4, _R5)),
            ("records", "history", _down(cx(4), _R4, _R5)),
            # redo takes a step from the history and gives it back
            ("history", "redo", _up(cx(3) - 10, _R4, _R5)),
            ("redo", "history", _down(cx(3) + 10, _R4, _R5)),
            # an undo changes the rows: up the right margin
            ("history", "rows", [(RIGHT + 1, _R5 + H / 2), (_MARGIN_R, _R5 + H / 2), (_MARGIN_R, ROWS[3] + H / 2),
                                 (RIGHT - _IN + 2, ROWS[3] + H / 2)]),
        ],
        "lessons": [
            ("08.01", "Remembering what a line was", {"records", "history"}),
            ("08.02", "Redo: a record that undoes itself", {"redo"}),
            ("08.03", "One Ctrl-Z, one thought: steps", {"steps"}),
            ("08.04", "The saved point, and a bound on memory", {"saved", "history"}),
        ],
    },
}

# 09, an API, and Lua on top of it. Three rows under the grid, as in 07. Row 4 is kilo.c's side of
# the API, each piece under the core piece it hangs from: keymaps (09.04) in the cursor's column,
# since the key handler offers every key to the scripts first (editorScriptKey); the prompt (Ctrl-E,
# and input(): 09.01, 09.07) under find, which has the other prompt; events (09.05) under save,
# which fires two of them; the API (09.02), the table of typed functions, under edit; highlights
# (09.06) under rows, drawn over the frame's rows. Row 5 is script.c: Lua, the interpreter and the
# one dispatcher, across four columns, and the guards (memory, Ctrl-C: 09.08) beside it. Row 6 is
# outside the editor: the scripts (init.lua, plugins: 09.01, 09.10), and no screen (kilo -l: 09.09).
# The key handler -> keymaps goes down the left margin (the handler and the cursor start 12 in, as
# in 08), highlights -> frame up the right margin (the frame gives up 12, as in 07). API <-> rows is
# an elbow in the gap between rows 3 and 4 with a head at each end (a script reads the rows and
# changes them: a fourth item "both" in a link), and no screen -> Lua one in the gap between rows 5
# and 6; API -> highlights is a short horizontal between the two neighbours. API -> prompt (input()
# runs the editor's prompt) is not drawn: events sits between them in row 4, and every way round
# crosses a line of events' column (save -> events above it, events -> Lua below). 09.08 highlights
# read a key with the guards: keys typed while a script runs are kept for editorReadKey(). The
# labels are cut to what a piece holds: "key -> a function" for keymaps, "save, change, key" for
# events, "typed functions" for the API.
_GAP34 = _BOT[3] + 11                    # half way between rows 3 and 4
_GAP56 = _R5 + H + (_R6 - _R5 - H) / 2   # half way between rows 5 and 6
_KEYMAP_MID = (COLS[0] + _IN + COLS[0] + W) / 2

EXTENSIONS["09"] = {
    "dir": "09-api-and-lua",
    "height": HEIGHT + 3 * PITCH,
    "move": {"handler": (COLS[0] + _IN, ROWS[2], COLS[3] + W - COLS[0] - _IN),
             "cursor": (COLS[0] + _IN, ROWS[3], W - _IN),
             "frame": (COLS[2], ROWS[1], RIGHT - COLS[2] - _IN)},
    "reroute": {},
    "pieces": {
        "keymaps": ("keymaps", "key -> a function", COLS[0] + _IN, _R4, W - _IN),
        "prompt": ("prompt", "Ctrl-E, input()", COLS[1], _R4, W),
        "events": ("events", "save, change, key", COLS[2], _R4, W),
        "api": ("API", "typed functions", COLS[3], _R4, W),
        "highlights": ("highlights", "colour over a row", COLS[4], _R4, W),
        "lua": ("Lua", "the interpreter, and the dispatcher", COLS[0], _R5, COLS[3] + W - COLS[0]),
        "guards": ("guards", "memory, Ctrl-C", COLS[4], _R5, W),
        "scripts": ("scripts", "init.lua, plugins", COLS[0], _R6, COLS[3] + W - COLS[0]),
        "noscreen": ("no screen", "kilo -l", COLS[4], _R6, W),
    },
    "links": [
        # every key is offered to the scripts first: down the left margin
        ("handler", "keymaps", [(COLS[0] + _IN - 1, ROWS[2] + H / 2), (_MARGIN_L, ROWS[2] + H / 2),
                                (_MARGIN_L, _R4 + H / 2), (COLS[0] + _IN - 2, _R4 + H / 2)]),
        # a save fires BufWritePre and BufWritePost
        ("save", "events", _down(cx(2), ROWS[3], _R4)),
        # the API reads the rows and changes them: landing at the rows' left end, so that it runs over
        # the gap between the columns and not along the top of highlights
        ("api", "rows", [(cx(3) + 30, _R4 - 2), (cx(3) + 30, _GAP34), (COLS[4] + 14, _GAP34),
                         (COLS[4] + 14, _BOT[3] + 2)], "both"),
        # a script's highlights are put through the API (add_highlight): its neighbour in row 4
        ("api", "highlights", [(COLS[3] + W + 1, _R4 + H / 2), (COLS[4] - 2, _R4 + H / 2)]),
        # the frame draws the highlights: up the right margin
        ("highlights", "frame", [(RIGHT + 1, _R4 + H / 2), (_MARGIN_R, _R4 + H / 2), (_MARGIN_R, _MID1),
                                 (RIGHT - _IN + 2, _MID1)]),
        # a key, a line at the prompt and an event each call into Lua
        ("keymaps", "lua", _down(_KEYMAP_MID, _R4, _R5)),
        ("prompt", "lua", _down(cx(1), _R4, _R5)),
        ("events", "lua", _down(cx(2), _R4, _R5)),
        # a script's call reaches the API through the dispatcher
        ("lua", "api", _up(cx(3), _R4, _R5)),
        # the guards watch Lua: its memory, and the keyboard while it runs
        ("guards", "lua", [(COLS[4] - 1, _R5 + H / 2), (COLS[3] + W + 2, _R5 + H / 2)]),
        # the scripts go into Lua, and Lua calls their functions
        ("scripts", "lua", _up(cx(1) + 52, _R5, _R6)),
        ("lua", "scripts", _down(cx(1) + 84, _R5, _R6)),
        # kilo -l runs one script through the same Lua, with no screen
        ("noscreen", "lua", [(cx(4), _R6 - 1), (cx(4), _GAP56), (cx(3) + 22, _GAP56), (cx(3) + 22, _R5 + H + 2)]),
    ],
    "lessons": [
        ("09.01", "A second language inside the editor: embedding Lua", {"lua", "prompt", "scripts"}),
        ("09.02", "The API is a table", {"api"}),
        ("09.03", "Changing the text from a script: set_lines", {"api"}),
        ("09.04", "Any key can run a Lua function", {"keymaps"}),
        ("09.05", "Events: autocommands", {"events"}),
        ("09.06", "Drawing from a script: highlights and the status bar", {"highlights"}),
        ("09.07", "Asking, opening, leaving: input(), open(), quit()", {"prompt", "api"}),
        ("09.08", "Scripts that go wrong", {"guards", "key"}),     # keys typed while a script runs are kept
        ("09.09", "The editor without its screen", {"noscreen"}),
        ("09.10", "Features as scripts", {"scripts"}),
    ],
}


def draw(lid, title, here, built, ext=None):
    """The map for lesson lid: the pieces in here in the accent, those in built solid, the
    rest dashed. ext: the extension the lesson belongs to (an EXTENSIONS entry), or None."""
    ext = ext or {}
    f = Fig("map" + lid.replace(".", ""), f"Where {lid} fits: {title}", ext.get("height", HEIGHT))

    def state(k):
        return "here" if k in here else ("built" if k in built else "later")

    def link(a, b, pts, arrow=True, both=False):
        """A connector between two pieces, muted unless both are built or here; both: a head at
        each end."""
        live = state(a) != "later" and state(b) != "later"
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        f.path(d, "s" if live else "m", arrow=arrow, dash=not live, start=both)

    reroute = ext.get("reroute", {})
    for a, b, pts in core_links():
        for a2, b2, pts2 in reroute.get((a, b), [(a, b, pts)]):
            link(a2, b2, pts2)
    for a, b, pts, *heads in ext.get("links", []):
        link(a, b, pts, both=heads == ["both"])

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
