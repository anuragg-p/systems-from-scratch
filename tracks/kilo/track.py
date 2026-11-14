"""Track kilo: a text editor in C, antirez's kilo rebuilt lesson by lesson (UPSTREAM).

The editor is one binary, ./kilo FILE (make builds it). It talks to a terminal: raw mode
in, VT100 escape codes out, nothing in between. So do the tests: each runs ./kilo on a
pseudo-terminal of a fixed size, types keys into it, and checks the screen it drew (its
escape codes turned into a grid of text by Screen, below) or the file it saved.

Fixtures the lesson tests use:

    edit(t, text=None, name="f.txt", rows=24, cols=80, winsize=None, ctty=True, timeout=20)
                        write text to name in the test's scratch directory (None: leave
                        the file as it is, or missing), start ./kilo name on a terminal
                        of rows x cols, and wait for its first screen (at most timeout
                        seconds); an Editor
    Editor              ed.keys(*parts) types each part and waits for the screen to settle
                        ed.lines, ed.line(n), ed.cursor (row, col from 0), ed.status,
                        ed.message, ed.reverse(n): what the screen shows
                        ed.raw: every byte kilo wrote; ed.screen: the Screen
                        ed.resize(rows, cols), ed.termios(), ed.quit(), ed.saved()
    UP DOWN LEFT RIGHT HOME END DEL PAGE_UP PAGE_DOWN ESC ENTER BACKSPACE TAB, ctrl("q")
                        what those keys send
    lines_of(n)         text of n numbered lines, "line 1\\n" to "line n\\n"

With ctty=True (the default) the terminal is the editor's controlling terminal, as in a
real one: Ctrl-C would be SIGINT if raw mode left ISIG on, and a resize sends SIGWINCH.
winsize=(0, 0) gives a terminal whose size the kernel does not know; Screen then answers
ESC [ 6 n as a real terminal does, with its own rows x cols.

Tests are internal. A lesson's test runs the whole editor, so with that lesson's code cut
out it fails at the stub: "kilo: NN.LL: <what> not written yet", exit status 3.

check-timeline runs the project at each lesson on a pseudo-terminal too: timeline_run()
starts this file as a program ("relay", at the end) that holds the terminal and a Screen,
and takes commands on its standard input: keys to type, "screen" to print what the
screen shows, "size R C" to resize it.
"""

import os
import re
import signal
import struct
import subprocess
import sys
import time

try:
    from harness.core import Fail
except ImportError:          # run as a program (the relay below): no harness needed
    class Fail(Exception):
        pass

TITLE = "A text editor in C, from scratch"
KIND = "editor"
SUMMARY = "Raw mode, escape codes, rows and a cursor, saving and search: a real editor in one C file."

# The code this track is built on (see harness/web/views.py, upstreams()). The site shows it
# on the overview, the home card and /credits, which prints licence_file whole; "derived":
# the code is derived from it, so every lesson page says so too. LICENSE comes with the
# project's files from the first lesson (FILES_FROM).
UPSTREAM = {
    "name": "kilo",
    "url": "https://github.com/antirez/kilo",
    "licence": "BSD-2-Clause",
    "copyright": "Copyright (c) 2016, Salvatore Sanfilippo <antirez at gmail dot com>",
    "owes": "The editor taught here is antirez's kilo, without its syntax highlighting, "
            "with this course's lessons and a few fixes.",
    "derived": True,
    "licence_file": "LICENSE",
    "chip": "based on kilo",
}

# Files that may hold "@build NN.LL" regions (see harness/workspace.py), and what replaces
# a region's code when a learner's workspace cuts it: kiloTodo() (@internal in kilo.c)
# puts the terminal back, prints "kilo: NN.LL: <title> not written yet" and exits 3.
SOURCES = ["kilo.c"]
STUBS = {".c": 'kiloTodo("{id}", "{title}");'}
# Not for learners: notes for the lesson writers, and the ./kilo the Makefile builds.
HIDDEN = ["NOTES.md", "kilo"]
# When each file comes into the project the site shows (see harness/timeline.py): kilo.c
# comes with its first region (01.01); the files without regions are named here. What later
# lessons add to kilo.c outside their regions is marked "@from NN.LL" in kilo.c itself.
FILES_FROM = {
    "LICENSE": "00.01",          # kilo's licence goes with every copy of the project
    "Makefile": "01.01",
}


def build(t):
    t.run(["make", "-s"])


# ---------------------------------------------------------------- run it
#
# The track contract's optional hooks: prepare(root) returns the command that builds the
# tree, run_argv(root) the command that starts the system. Both run with cwd=root: the
# project as it stands at a lesson (./learn run kilo --at NN.LL writes it to
# build/at/kilo/NN.LL/), or the finished track.

def prepare(root):
    return ["make", "-s"]


def run_argv(root, args=()):
    """The editor on learn.txt, a file kept between runs (it does not exist until the first
    save); with args (./learn run kilo -- file.txt), on those instead."""
    return ["./kilo"] + (list(args) or ["learn.txt"])


# ---------------------------------------------------------------- the screen
#
# What a terminal does with the bytes kilo writes, as much of it as kilo uses: printable
# characters, "\r", "\n", backspace and tab, and the escape sequences ESC [ row ; col H
# (move), A B C D (move by), K and J (erase), m (reverse video on and off), ? 25 l / h
# (hide and show the cursor) and 6 n (report where the cursor is: answered in replies).

CSI = re.compile(rb"\x1b\[([0-9;?]*)([ -/]*)([@-~])")
CSI_CUT = re.compile(rb"\x1b(\[[0-9;?]*[ -/]*)?")


class Screen:
    """A terminal screen of rows x cols, fed with what the program writes to it.

    lines()     the text of each row, trailing spaces dropped
    cursor      (row, col) of the cursor, counting from 0
    rev[r][c]   whether that cell was written in reverse video
    frames      how many times the cursor has been shown again (ESC [ ? 25 h): kilo shows
                it once at the end of every screen it draws
    replies     what the terminal sends back (answers to ESC [ 6 n), not yet sent
    """

    def __init__(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.grid = [[" "] * cols for _ in range(rows)]
        self.rev = [[False] * cols for _ in range(rows)]
        self.y = self.x = 0
        self.reverse = False
        self.cursor_shown = True
        self.frames = 0
        self.replies = []
        self.rest = b""          # an escape sequence cut in two between feeds

    def resize(self, rows, cols):
        grid = [[" "] * cols for _ in range(rows)]
        rev = [[False] * cols for _ in range(rows)]
        for r in range(min(rows, self.rows)):
            for c in range(min(cols, self.cols)):
                grid[r][c], rev[r][c] = self.grid[r][c], self.rev[r][c]
        self.rows, self.cols, self.grid, self.rev = rows, cols, grid, rev
        self.y, self.x = min(self.y, rows - 1), min(self.x, cols - 1)

    @property
    def cursor(self):
        return self.y, min(self.x, self.cols - 1)

    def lines(self):
        return ["".join(row).rstrip() for row in self.grid]

    def _linefeed(self):
        if self.y == self.rows - 1:
            self.grid.pop(0)
            self.rev.pop(0)
            self.grid.append([" "] * self.cols)
            self.rev.append([False] * self.cols)
        else:
            self.y += 1

    def _put(self, ch):
        if self.x >= self.cols:              # the last column is written: wrap now
            self.x = 0
            self._linefeed()
        self.grid[self.y][self.x] = ch
        self.rev[self.y][self.x] = self.reverse
        self.x += 1

    def _erase(self, row, start, end):
        for c in range(max(0, start), min(self.cols, end)):
            self.grid[row][c] = " "
            self.rev[row][c] = False

    def _csi(self, params, final):
        private = params.startswith("?")
        args = [int(a) if a.isdigit() else 0 for a in params.lstrip("?").split(";")] if params else []

        def arg(k, default):
            return (args[k] if k < len(args) else 0) or default
        x = min(self.x, self.cols - 1)
        if final in "Hf":
            self.y = min(max(arg(0, 1), 1), self.rows) - 1
            self.x = min(max(arg(1, 1), 1), self.cols) - 1
        elif final == "A":
            self.y = max(0, self.y - arg(0, 1))
        elif final == "B":
            self.y = min(self.rows - 1, self.y + arg(0, 1))
        elif final == "C":
            self.x = min(self.cols - 1, x + arg(0, 1))
        elif final == "D":
            self.x = max(0, x - arg(0, 1))
        elif final == "K":
            mode = args[0] if args else 0
            if mode == 0:
                self._erase(self.y, x, self.cols)
            elif mode == 1:
                self._erase(self.y, 0, x + 1)
            else:
                self._erase(self.y, 0, self.cols)
        elif final == "J":
            mode = args[0] if args else 0
            if mode == 0:
                self._erase(self.y, x, self.cols)
                for r in range(self.y + 1, self.rows):
                    self._erase(r, 0, self.cols)
            elif mode == 1:
                for r in range(0, self.y):
                    self._erase(r, 0, self.cols)
                self._erase(self.y, 0, x + 1)
            else:
                for r in range(self.rows):
                    self._erase(r, 0, self.cols)
        elif final == "m":
            for a in args or [0]:
                if a == 0 or a == 27:
                    self.reverse = False
                elif a == 7:
                    self.reverse = True
        elif final in "hl" and private and 25 in args:
            self.cursor_shown = final == "h"
            if final == "h":
                self.frames += 1
        elif final == "n" and args == [6]:
            self.replies.append(f"\x1b[{self.y + 1};{x + 1}R".encode())

    def feed(self, data):
        data = self.rest + data
        self.rest = b""
        i, n = 0, len(data)
        while i < n:
            b = data[i]
            if b == 0x1b:
                m = CSI.match(data, i)
                if m:
                    self._csi(m.group(1).decode(), m.group(3).decode())
                    i = m.end()
                    continue
                if CSI_CUT.fullmatch(data, i):
                    self.rest = data[i:]
                    break
                i += 2                           # ESC and one more byte: kilo sends none of these
                continue
            if b == 13:
                self.x = 0
            elif b == 10:
                self._linefeed()
            elif b == 8:
                self.x = max(0, min(self.x, self.cols - 1) - 1)
            elif b == 9:
                self.x = min(self.cols - 1, (self.x // 8 + 1) * 8)
            elif b >= 32 and b != 127:
                self._put(chr(b))
            i += 1

    def dump(self):
        """The screen as text: what the relay prints for "screen"."""
        r, c = self.cursor
        return "[screen]\n" + "".join(l + "\n" for l in self.lines()) + f"[cursor {r + 1},{c + 1}]\n"


# ---------------------------------------------------------------- keys

UP, DOWN, RIGHT, LEFT = "\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"
HOME, END = "\x1b[H", "\x1b[F"
DEL, PAGE_UP, PAGE_DOWN = "\x1b[3~", "\x1b[5~", "\x1b[6~"
ESC, ENTER, BACKSPACE, TAB = "\x1b", "\r", "\x7f", "\t"


def ctrl(ch):
    """What Ctrl and a letter send: ctrl("q") is "\\x11"."""
    return chr(ord(ch.upper()) & 0x1f)


def lines_of(n, fmt="line {}"):
    return "".join(fmt.format(i) + "\n" for i in range(1, n + 1))


# ---------------------------------------------------------------- the editor on a terminal

# Make the terminal the program's controlling terminal (as a login does), then run it.
CTTY = ("import fcntl, os, sys, termios\n"
        "fcntl.ioctl(0, termios.TIOCSCTTY, 0)\n"
        "os.execv(sys.argv[1], sys.argv[1:])\n")


class Editor:
    """./kilo on a pseudo-terminal, with a Screen showing what it drew."""

    def __init__(self, t, args, rows=24, cols=80, winsize=None, ctty=True, cwd=None, timeout=20):
        self.t = t
        self.ctty = ctty
        self.screen = Screen(rows, cols)
        exe = os.path.join(t.root, "kilo")
        argv = ([sys.executable, "-c", CTTY] if ctty else []) + [exe] + list(args)
        self.s = t.spawn(argv, name="kilo", cwd=cwd or t.tmp, pty=True,
                         size=(rows, cols) if winsize is None else winsize)
        self.fed = 0
        self.last = time.monotonic()
        self.wait_frame(0, timeout=timeout)

    # ------------------------------------------------------------ reading

    @property
    def raw(self):
        return self.s.buf

    def pump(self, timeout=0.02):
        self.s._pump(timeout)
        if len(self.s.buf) > self.fed:
            self.screen.feed(self.s.buf[self.fed:])
            self.fed = len(self.s.buf)
            self.last = time.monotonic()
            while self.screen.replies:
                self.s.send(self.screen.replies.pop(0))

    def tail(self):
        """What a stub said is missing, or else the last of what kilo wrote, escapes taken out."""
        m = re.search(rb"kilo: \d\d\.\d\d: [^\r\n]* not written yet", self.s.buf)
        if m:
            return m.group(0).decode("utf-8", "replace")
        text = CSI.sub(b"", self.s.buf[-600:]).decode("utf-8", "replace")
        return " | ".join(l.strip() for l in text.replace("\r", "\n").split("\n") if l.strip())[-300:]

    def wait_frame(self, before, timeout=10, quiet=0.15):
        """Wait until kilo has finished a screen after the `before`-th one, and then written
        nothing more for `quiet` seconds."""
        deadline = time.monotonic() + timeout
        while True:
            self.pump(0.02)
            now = time.monotonic()
            if self.screen.frames > before and not self.screen.rest and now - self.last >= quiet:
                return
            if self.s.proc.poll() is not None:
                while self.s._pump(0.05):
                    pass
                self.pump(0)
                raise Fail(f"kilo exited with status {self.s.proc.returncode}: {self.tail()}")
            if now > deadline:
                raise Fail(f"kilo drew no new screen within {timeout}s; it shows:\n{self.text()}")

    def keys(self, *parts):
        """Type each part (one key or several), waiting after each for the screen it draws."""
        for p in parts:
            before = self.screen.frames
            self.s.send(p)
            self.wait_frame(before)

    # ------------------------------------------------------------ what the screen shows

    @property
    def lines(self):
        return self.screen.lines()

    def line(self, n):
        return self.screen.lines()[n]

    def text(self):
        return "\n".join(f"{i:2} |{l}" for i, l in enumerate(self.lines))

    @property
    def cursor(self):
        return self.screen.cursor

    @property
    def status(self):
        return self.line(self.screen.rows - 2)

    @property
    def message(self):
        return self.line(self.screen.rows - 1)

    def reverse(self, n):
        """Is every cell of row n in reverse video?"""
        return all(self.screen.rev[n])

    # ------------------------------------------------------------ the terminal

    def termios(self):
        """The terminal's settings now (tcgetattr on the pseudo-terminal)."""
        import termios
        return termios.tcgetattr(self.s.master)

    def resize(self, rows, cols):
        """Change the window's size, as dragging its corner does, and wait for the screen."""
        import fcntl
        import termios
        before = self.screen.frames
        self.screen.resize(rows, cols)
        fcntl.ioctl(self.s.master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        if not self.ctty:          # the kernel signals only a terminal's own processes
            os.kill(self.s.proc.pid, signal.SIGWINCH)
        self.wait_frame(before)

    def quit(self, timeout=10):
        """Press Ctrl-Q and wait for kilo to exit; its exit status."""
        self.s.send(ctrl("q"))
        rc = self.s.wait_exit(timeout)
        self.pump(0)
        return rc

    def saved(self):
        with open(self.path, encoding="latin-1", newline="") as f:
            return f.read()


def edit(t, text=None, name="f.txt", rows=24, cols=80, **kw):
    """./kilo name in the test's scratch directory, with text written there first."""
    path = os.path.join(t.tmp, name)
    if text is not None:
        with open(path, "w", encoding="latin-1", newline="") as f:
            f.write(text)
    ed = Editor(t, [name], rows, cols, cwd=t.tmp, **kw)
    ed.path = path
    return ed


# ---------------------------------------------------------------- the project at each lesson
#
# Internal: ./learn check-timeline kilo builds the project as the site shows it at each
# lesson (harness/timeline.py) and runs it through the relay on a 24 x 80 terminal, on a
# file of 40 lines (TIMELINE_TEXT) that timeline_run() writes. timeline_boot() types what
# that lesson can do and checks the screen; keys whose lesson is still ahead must change
# nothing. timeline_after() then checks the file: untouched until 04.04, saved after.

TIMELINE_FILE = "learn.txt"
TIMELINE_TEXT = "kilo at a lesson\n\tafter a tab\n" + "".join(f"line {i}\n" for i in range(3, 41))
TIMELINE_FAIL = [r"\[kilo exited", r"not written yet", r"\[relay: "]


def timeline_run(root):
    with open(os.path.join(root, TIMELINE_FILE), "w") as f:
        f.write(TIMELINE_TEXT)
    return [sys.executable, os.path.abspath(__file__), "relay", "24", "80", "--", "./kilo", TIMELINE_FILE]


def _screen(rows, want, cursor=None):
    """A regex for the relay's dump of a screen `rows` high: want maps a row (from 0;
    negative from the bottom) to the text it must hold, exactly, or to an re.Pattern it
    must match; the other rows may hold anything."""
    parts = []
    for i in range(rows):
        w = want.get(i, want.get(i - rows))
        if w is None:
            parts.append(r".*\n")
        elif isinstance(w, re.Pattern):
            parts.append(w.pattern + r"\n")
        else:
            parts.append(re.escape(w) + r"\n")
    tail = rf"\[cursor {cursor[0]},{cursor[1]}\]" if cursor else r"\[cursor \d+,\d+\]"
    return r"\[screen\]\n" + "".join(parts) + tail


def _file_rows(first, count, top=0):
    """want entries: screen rows top.. show the timeline file's lines from `first` (from 1),
    as the screen draws them (a tab is spaces up to column 8)."""
    lines = TIMELINE_TEXT.split("\n")
    return {top + k: lines[first - 1 + k].replace("\t", " " * 8) for k in range(count)}


SENT = r"\[sent\]"


def timeline_boot(lesson_id):
    """(command for the relay, regex to wait for) steps for the editor as it stands at a
    lesson: what that lesson's code can do, and nothing for keys whose lesson is ahead."""
    from harness.core import lesson_key
    k = lesson_key(lesson_id)
    if k < (1, 1):
        return []
    S = "screen"
    if k < (2, 1):
        # No screen yet: each key's code, one per line. The terminal does not echo what
        # is typed; Enter arrives as 13; an arrow is three bytes until 01.02 reads it as one
        # key, 1002; Ctrl-C is just 3. 01.03 measures the window first.
        codes = ["97 ('a')", "13"] + (["1002"] if k >= (1, 2) else ["27", "91 ('[')", "65 ('A')"]) + ["3", "120 ('x')"]
        if k >= (1, 3):
            codes = ["This window has 24 rows and 80 columns."] + codes
        return [("keys a{enter}{up}{ctrl-c}x", SENT),
                (S, _screen(24, dict(enumerate(codes)) | {len(codes): ""}, cursor=(len(codes) + 1, 1)))]
    status_bar = k >= (3, 4)
    text_rows = 22 if status_bar else 23     # before 03.04 the bottom line stays empty
    steps = []
    if k < (3, 1):
        # Tildes, the welcome a third of the way down, and nothing for any key.
        want = {i: "~" for i in range(23)} | {7: re.compile(r"~ {22}Kilo editor -- version 0\.0\.1"), 23: ""}
        steps += [(S, _screen(24, want, cursor=(1, 1))),
                  ("keys x{enter}{down}{right}{ctrl-s}{ctrl-f}{bs}", SENT), (S, _screen(24, want, cursor=(1, 1))),
                  ("size 30 100", r"\[size 30 100\]"),
                  (S, _screen(30, {i: "~" for i in range(29)} | {9: re.compile(r"~ +Kilo editor -- version 0\.0\.1"),
                                                                  29: ""}, cursor=(1, 1)))]
        return steps
    # From 03.01: the file, from its first line.
    rows = _file_rows(1, text_rows)
    if k < (3, 3):
        # Until 03.03 a tab goes to the terminal as it is: the cursor jumps to column 8 and
        # what was on the screen under the jump stays there ("line 20 after a tab").
        rows[1] = re.compile(r".{8}after a tab")
    if status_bar:
        rows[22] = _bar()
    else:
        rows[23] = ""
    first = dict(rows)
    if status_bar:
        first[22] = _bar(at=1)
        first[23] = ("HELP: Ctrl-Q = quit" if k < (4, 4) else "HELP: Ctrl-S = save | Ctrl-Q = quit"
                     if k < (5, 1) else "HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F = find")
    steps.append((S, _screen(24, first, cursor=(1, 1))))
    if k < (3, 2):
        steps += [("keys {down}{right}{pgdn}", SENT), (S, _screen(24, rows, cursor=(1, 1)))]
        return steps
    # 03.02: the cursor moves, and the view scrolls with it. On the tab's line the cursor
    # is one column past the tab's byte until 03.03 counts the tab's width.
    steps += [("keys {down}{right}", SENT), (S, _screen(24, rows, cursor=(2, 9 if k >= (3, 3) else 2))),
              ("keys {down}{right}{right}", SENT), (S, _screen(24, rows, cursor=(3, 4)))]
    if k < (4, 1):
        # Page Down: the cursor to the bottom line, then a screenful down: the view stops
        # with the row just past the end of the file on the bottom line. Page Up: back.
        down = _file_rows(42 - text_rows, text_rows - 1) | {text_rows - 1: "~"}
        if status_bar:
            down[22] = _bar(at=41)
        steps += [("keys {pgdn}", SENT), (S, _screen(24, down, cursor=(text_rows, 1))),
                  ("keys {pgup}", SENT), (S, _screen(24, rows, cursor=(1, 1)))]
        if status_bar:
            steps += [("size 30 100", r"\[size 30 100\]"),
                      (S, _screen(30, _file_rows(1, 28) | {28: _bar(at=1)}, cursor=(1, 1)))]
        return steps
    # 04.01: typing inserts; the status bar says (modified). Keys whose lesson is ahead, and
    # Home and End (bound to nothing), change nothing.
    typed = dict(rows) | {0: "abckilo at a lesson", 22: _bar(at=1, modified=True)}
    ahead = "{home}{end}" + ("{ctrl-f}" if k < (5, 1) else "") + ("{ctrl-s}" if k < (4, 4) else "") + \
        ("{bs}{del}" if k < (4, 3) else "") + ("{enter}" if k < (4, 2) else "")
    steps += [("keys {pgup}{left}{left}{left}abc", SENT), (S, _screen(24, typed, cursor=(1, 4))),
              (f"keys {ahead}", SENT), (S, _screen(24, typed, cursor=(1, 4)))]
    if k >= (4, 2):
        # 04.02: Enter splits the line at the cursor.
        split = _file_rows(1, 21, top=1) | {0: "abc", 22: _bar(lines=41, at=2, modified=True)}
        steps += [("keys {enter}", SENT), (S, _screen(24, split, cursor=(2, 1)))]
    if k >= (4, 3):
        # 04.03: Backspace at the start of a line joins it to the one above; then it deletes.
        joined = dict(typed) | {0: "abkilo at a lesson"}
        steps += [("keys {bs}{bs}", SENT), (S, _screen(24, joined, cursor=(1, 3)))]
    if k >= (4, 4):
        # 04.04: Ctrl-Q with unsaved changes warns; Ctrl-S saves (timeline_after reads it).
        steps += [("keys {ctrl-q}", SENT),
                  (S, _screen(24, joined | {23: "WARNING!!! File has unsaved changes. Press Ctrl-Q 3 more times to quit."},
                              cursor=(1, 3))),
                  ("keys {ctrl-s}", SENT),
                  (S, _screen(24, joined | {22: _bar(at=1), 23: f"{len(TIMELINE_TEXT) + 2} bytes written on disk"},
                              cursor=(1, 3)))]
    if k >= (5, 1):
        # 05.01: Ctrl-F searches as you type: the first row with "line 3" goes to the top.
        hint = "(Use ESC/Arrows/Enter)" if k >= (5, 2) else "(Use ESC/Enter)"
        found = _file_rows(3, 22) | {22: _bar(at=3), 23: f"Search: line 3 {hint}"}
        steps += [("keys {ctrl-f}line 3", SENT), (S, _screen(24, found, cursor=(1, 1)))]
        if k >= (5, 2):
            # 05.02: Down goes on to the next match, Up back, Escape to where the search began.
            steps += [("keys {down}", SENT),
                      (S, _screen(24, _file_rows(30, 11) | {11: "~", 22: _bar(at=30), 23: f"Search: line 3 {hint}"},
                                  cursor=(1, 1))),
                      ("keys {up}", SENT), (S, _screen(24, found, cursor=(1, 1))),
                      ("keys {esc}", SENT), (S, _screen(24, joined | {22: _bar(at=1), 23: ""}, cursor=(1, 3)))]
        else:
            steps += [("keys {enter}", SENT), (S, _screen(24, {0: "line 3", 22: _bar(at=3), 23: ""}, cursor=(1, 1)))]
    return steps


def _bar(lines=40, at=None, modified=False):
    """The status bar on an 80-column screen (or wider): name, lines, row of the cursor."""
    return re.compile(rf"learn\.txt - {lines} lines{r' \(modified\)' if modified else ''} +"
                      rf"{at if at is not None else r'\d+'}/{lines}")


def timeline_after(root, lesson_id):
    """The file the run worked on: untouched until 04.04, saved with the edits after."""
    from harness.core import lesson_key
    with open(os.path.join(root, TIMELINE_FILE)) as f:
        got = f.read()
    if lesson_key(lesson_id) < (4, 4):
        if got != TIMELINE_TEXT:
            raise Fail(f"{TIMELINE_FILE} changed before there is a save: {got[:80]!r}")
        return f"{TIMELINE_FILE} untouched"
    if got != "ab" + TIMELINE_TEXT:
        raise Fail(f"{TIMELINE_FILE} was not saved with the edits: {got[:80]!r}")
    return f"{TIMELINE_FILE} saved, {len(got)} bytes"


# ---------------------------------------------------------------- the relay
#
#   python3 track.py relay ROWS COLS -- ./kilo FILE
#
# Runs the program on a pseudo-terminal of ROWS x COLS and keeps a Screen of what it draws.
# Each line on standard input is a command:
#
#   keys TEXT       type TEXT; {name} is a key: enter esc tab bs del up down left right
#                   home end pgup pgdn, or ctrl-x. Prints "[sent]".
#   screen          wait until the program has been quiet for a moment, then print the
#                   screen (Screen.dump: "[screen]", its rows, "[cursor R,C]").
#   size R C        resize the terminal and send the program SIGWINCH. Prints "[size R C]".
#
# When the program exits it prints the screen as it was left and "[kilo exited with status N]",
# and exits too.

KEY_NAMES = {"enter": "\r", "esc": "\x1b", "tab": "\t", "bs": "\x7f", "del": DEL, "up": UP,
             "down": DOWN, "left": LEFT, "right": RIGHT, "home": HOME, "end": END,
             "pgup": PAGE_UP, "pgdn": PAGE_DOWN}


def key_chunks(spec):
    """'ab{up}{ctrl-s}' -> ['ab', '\\x1b[A', '\\x13']: the bytes to send, with a lone Escape
    in a chunk of its own (sent together with what follows, it would read as a sequence)."""
    out = []
    for part in re.split(r"(\{[a-z]+(?:-[a-z@\[\]\\^_])?\})", spec):
        if not part:
            continue
        m = re.fullmatch(r"\{([a-z]+)(?:-(.))?\}", part)
        if m and m.group(1) == "ctrl" and m.group(2):
            out.append(ctrl(m.group(2)))
        elif m and m.group(1) in KEY_NAMES and not m.group(2):
            out.append(KEY_NAMES[m.group(1)])
        else:
            out.append(part)
    return out


def relay(args):
    import fcntl
    import pty
    import select
    import termios
    rows, cols = int(args[0]), int(args[1])
    argv = args[args.index("--") + 1:]
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    p = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    screen = Screen(rows, cols)
    state = {"last": time.monotonic(), "eof": False}

    def say(text):
        os.write(1, text.encode())

    def pump(timeout):
        if state["eof"]:
            time.sleep(timeout)
            return
        r, _, _ = select.select([master], [], [], timeout)
        if not r:
            return
        try:
            data = os.read(master, 65536)
        except OSError:
            data = b""
        if not data:
            state["eof"] = True
            return
        screen.feed(data)
        state["last"] = time.monotonic()
        for reply in screen.replies:
            os.write(master, reply)
        screen.replies.clear()

    def finish():
        deadline = time.monotonic() + 2
        while not state["eof"] and time.monotonic() < deadline:
            pump(0.05)
        say(screen.dump() + f"[kilo exited with status {p.wait()}]\n")
        return 1

    # Keys typed before the program has put the terminal in raw mode would be echoed by the
    # terminal and then thrown away (TCSAFLUSH): wait for raw mode (no ECHO) first.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and termios.tcgetattr(master)[3] & termios.ECHO:
        if p.poll() is not None:
            return finish()
        pump(0.02)
    pump(0.2)

    pending, stdin_open = b"", True
    while True:
        if p.poll() is not None:
            return finish()
        r, _, _ = select.select([master] + ([0] if stdin_open else []), [], [], 0.05)
        if master in r:
            pump(0)
        if stdin_open and 0 in r:
            chunk = os.read(0, 4096)
            if not chunk:
                stdin_open = False
            pending += chunk
        while b"\n" in pending:
            line, pending = pending.split(b"\n", 1)
            cmd = line.decode("utf-8", "replace").rstrip("\r")
            if cmd.startswith("keys "):
                for c in key_chunks(cmd[5:]):
                    try:
                        os.write(master, c.encode("latin-1"))
                    except OSError:              # the program has gone
                        return finish()
                    pump(0.35 if c == "\x1b" else 0.02)
                state["last"] = time.monotonic()     # "screen" waits for quiet from here on
                say("[sent]\n")
            elif cmd == "screen":
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and (time.monotonic() - state["last"] < 0.4 or screen.rest):
                    pump(0.05)
                    if p.poll() is not None:
                        return finish()
                say(screen.dump())
            elif cmd.startswith("size "):
                r_, c_ = (int(x) for x in cmd.split()[1:3])
                screen.resize(r_, c_)
                before = screen.frames
                fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", r_, c_, 0, 0))
                os.kill(p.pid, signal.SIGWINCH)
                deadline = time.monotonic() + 5      # a program that redraws: wait for it
                while screen.frames == before and time.monotonic() < deadline and p.poll() is None:
                    pump(0.05)
                say(f"[size {r_} {c_}]\n")
            elif cmd.strip():
                say(f"[relay: no command {cmd!r}]\n")


if __name__ == "__main__":
    if sys.argv[1:2] == ["relay"]:
        sys.exit(relay(sys.argv[2:]))
    sys.exit("usage: track.py relay ROWS COLS -- PROGRAM ARGS...")
