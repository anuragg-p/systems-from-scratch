"""Track kilo: a text editor in C, antirez's kilo rebuilt lesson by lesson (UPSTREAM).

The editor is one binary, ./kilo FILE (make builds it). It talks to a terminal: raw mode
in, VT100 escape codes out, nothing in between. So do the tests: each runs ./kilo on a
pseudo-terminal of a fixed size, types keys into it, and checks the screen it drew (its
escape codes turned into a grid of text by Screen, below) or the file it saved.

Fixtures the lesson tests use:

    edit(t, text=None, name="f.txt", rows=24, cols=80, winsize=None, ctty=True, timeout=20,
         asan=False)
                        write text to name in the test's scratch directory (None: leave
                        the file as it is, or missing), start ./kilo name on a terminal
                        of rows x cols, and wait for its first screen (at most timeout
                        seconds); an Editor. asan=True: kilo built with AddressSanitizer
                        where the compiler can (asan_build), so a memory error stops it
    Editor              ed.keys(*parts) types each part and waits for the screen to settle
                        ed.lines, ed.line(n), ed.cursor (row, col from 0), ed.status,
                        ed.message, ed.reverse(n): what the screen shows
                        ed.colors(n), ed.color(n, text), ed.painted(n): the colour of each
                        character (Screen.colors), for the syntax highlighting (module 06)
                        ed.raw: every byte kilo wrote; ed.screen: the Screen
                        ed.resize(rows, cols), ed.termios(), ed.quit(), ed.saved()
    UP DOWN LEFT RIGHT HOME END DEL PAGE_UP PAGE_DOWN ESC ENTER BACKSPACE TAB, ctrl("q")
                        what those keys send
    lines_of(n)         text of n numbered lines, "line 1\\n" to "line n\\n"
    paint(text, codes)  a row with its colours written in: "[g:int] x = [r:10];"

With ctty=True (the default) the terminal is the editor's controlling terminal, as in a
real one: Ctrl-C would be SIGINT if raw mode left ISIG on, and a resize sends SIGWINCH.
winsize=(0, 0) gives a terminal whose size the kernel does not know; Screen then answers
ESC [ 6 n as a real terminal does, with its own rows x cols.

Tests are internal. A lesson's test runs the whole editor, so with that lesson's code cut
out it fails at the stub: "kilo: NN.LL: <what> not written yet", exit status 3.

check-timeline runs the project at each lesson on a pseudo-terminal too: timeline_run()
starts this file as a program ("relay", at the end) that holds the terminal and a Screen,
and takes commands on its standard input: keys to type, "screen" to print what the
screen shows, "colors" its colours, "size R C" to resize it.
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
    "owes": "The editor taught here is antirez's kilo, its syntax highlighting as an optional "
            "module, with this course's lessons and a few fixes.",
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
# (move), A B C D (move by), K and J (erase), m (reverse video on and off, and the
# foreground colour: 30 to 37, 39 for the default, 0 for everything off), ? 25 l / h
# (hide and show the cursor) and 6 n (report where the cursor is: answered in replies).

CSI = re.compile(rb"\x1b\[([0-9;?]*)([ -/]*)([@-~])")
CSI_CUT = re.compile(rb"\x1b(\[[0-9;?]*[ -/]*)?")
# A cell's colour as one letter: ESC [ 30 m to ESC [ 37 m. See Screen.colors().
COLOURS = {30: "k", 31: "r", 32: "g", 33: "y", 34: "b", 35: "m", 36: "c", 37: "w"}


class Screen:
    """A terminal screen of rows x cols, fed with what the program writes to it.

    lines()     the text of each row, trailing spaces dropped
    colors()    the colour of each character of lines(), one letter per cell (see there)
    cursor      (row, col) of the cursor, counting from 0
    rev[r][c]   whether that cell was written in reverse video
    fg[r][c]    the foreground colour it was written in: 30 to 37, or None for the default
    frames      how many times the cursor has been shown again (ESC [ ? 25 h): kilo shows
                it once at the end of every screen it draws
    replies     what the terminal sends back (answers to ESC [ 6 n), not yet sent
    """

    def __init__(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.grid = [[" "] * cols for _ in range(rows)]
        self.rev = [[False] * cols for _ in range(rows)]
        self.fg = [[None] * cols for _ in range(rows)]
        self.y = self.x = 0
        self.reverse = False
        self.colour = None
        self.cursor_shown = True
        self.frames = 0
        self.replies = []
        self.rest = b""          # an escape sequence cut in two between feeds

    def resize(self, rows, cols):
        grid = [[" "] * cols for _ in range(rows)]
        rev = [[False] * cols for _ in range(rows)]
        fg = [[None] * cols for _ in range(rows)]
        for r in range(min(rows, self.rows)):
            for c in range(min(cols, self.cols)):
                grid[r][c], rev[r][c], fg[r][c] = self.grid[r][c], self.rev[r][c], self.fg[r][c]
        self.rows, self.cols, self.grid, self.rev, self.fg = rows, cols, grid, rev, fg
        self.y, self.x = min(self.y, rows - 1), min(self.x, cols - 1)

    @property
    def cursor(self):
        return self.y, min(self.x, self.cols - 1)

    def lines(self):
        return ["".join(row).rstrip() for row in self.grid]

    def colors(self):
        """For each row, a letter per character of lines(): "." in the default colour, else
        k r g y b m c w for ESC [ 30 m to 37 m (black, red, green, yellow, blue, magenta, cyan,
        white); in reverse video, "#" for the default colour, else the letter in capitals."""
        out = []
        for r, text in enumerate(self.lines()):
            codes = []
            for c in range(len(text)):
                code = COLOURS.get(self.fg[r][c], ".")
                if self.rev[r][c]:
                    code = "#" if code == "." else code.upper()
                codes.append(code)
            out.append("".join(codes))
        return out

    def _linefeed(self):
        if self.y == self.rows - 1:
            self.grid.pop(0)
            self.rev.pop(0)
            self.fg.pop(0)
            self.grid.append([" "] * self.cols)
            self.rev.append([False] * self.cols)
            self.fg.append([None] * self.cols)
        else:
            self.y += 1

    def _put(self, ch):
        if self.x >= self.cols:              # the last column is written: wrap now
            self.x = 0
            self._linefeed()
        self.grid[self.y][self.x] = ch
        self.rev[self.y][self.x] = self.reverse
        self.fg[self.y][self.x] = self.colour
        self.x += 1

    def _erase(self, row, start, end):
        for c in range(max(0, start), min(self.cols, end)):
            self.grid[row][c] = " "
            self.rev[row][c] = False
            self.fg[row][c] = None

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
                if a == 0:
                    self.reverse, self.colour = False, None
                elif a == 27:
                    self.reverse = False
                elif a == 7:
                    self.reverse = True
                elif 30 <= a <= 37:
                    self.colour = a
                elif a == 39:
                    self.colour = None
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

    def dump_colors(self):
        """Every row with its colours (colors()), each run of one colour other than the
        default in brackets after its letter, "[g:int] x = [r:10];" (paint()): what the relay
        prints for "colors"."""
        return "[colors]\n" + "".join(paint(l, c) + "\n" for l, c in zip(self.lines(), self.colors())) \
            + "[end]\n"


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

    def __init__(self, t, args, rows=24, cols=80, winsize=None, ctty=True, cwd=None, timeout=20,
                 exe=None, env=None):
        self.t = t
        self.ctty = ctty
        self.screen = Screen(rows, cols)
        exe = exe or os.path.join(t.root, "kilo")
        argv = ([sys.executable, "-c", CTTY] if ctty else []) + [exe] + list(args)
        self.s = t.spawn(argv, name="kilo", cwd=cwd or t.tmp, pty=True, env=env,
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

    def colors(self, n):
        """The colour of each character of row n, one letter each (Screen.colors)."""
        return self.screen.colors()[n]

    def color(self, n, text, start=0):
        """The colours of the first `text` in row n at or after column start (Screen.colors);
        Fail if row n does not hold it."""
        at = self.line(n).find(text, start)
        if at < 0:
            raise Fail(f"row {n} does not hold {text!r}: {self.line(n)!r}")
        return self.colors(n)[at:at + len(text)]

    def painted(self, n):
        """Row n with each run of one colour other than the default in brackets, after its
        letter: "[g:int] x = [r:10];". For messages and notes."""
        return paint(self.line(n), self.colors(n))

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


def paint(text, codes):
    """text with each run of one colour (codes: Screen.colors) other than "." in brackets,
    after its letter: paint("int x", "ggg..") is "[g:int] x"."""
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and codes[j] == codes[i]:
            j += 1
        out.append(text[i:j] if codes[i] == "." else f"[{codes[i]}:{text[i:j]}]")
        i = j
    return "".join(out)


def asan_build(t):
    """kilo.c of the tree under test built with AddressSanitizer, into the test's scratch
    directory (once per test): a memory error then stops kilo with a report and status 1,
    where the plain build would go on, often showing nothing. None where the compiler cannot
    build that (gcc on musl, for one)."""
    if not hasattr(t, "_kilo_asan"):
        exe = os.path.join(t.tmp, "kilo-asan")
        try:
            r = subprocess.run([os.environ.get("CC", "cc"), "-std=c99", "-g", "-fsanitize=address",
                                "-fno-omit-frame-pointer", "-o", exe, "kilo.c"],
                               cwd=t.root, capture_output=True, timeout=300)
            t._kilo_asan = exe if r.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            t._kilo_asan = None
    return t._kilo_asan


def edit(t, text=None, name="f.txt", rows=24, cols=80, asan=False, **kw):
    """./kilo name in the test's scratch directory, with text written there first (name may
    be in a folder, which is made then). asan=True: the AddressSanitizer build (asan_build)
    where there is one, else the plain one; ed.asan says which ran."""
    path = os.path.join(t.tmp, name)
    if text is not None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="latin-1", newline="") as f:
            f.write(text)
    exe = asan_build(t) if asan else None
    if exe:
        # Leaks are no error here: kilo frees nothing on the way out, as the original does.
        kw.setdefault("env", dict(os.environ, ASAN_OPTIONS="detect_leaks=0"))
    ed = Editor(t, [name], rows, cols, cwd=t.tmp, exe=exe, **kw)
    ed.path = path
    ed.asan = bool(exe)
    return ed


# ---------------------------------------------------------------- the project at each lesson
#
# Internal: ./learn check-timeline kilo builds the project as the site shows it at each
# lesson (harness/timeline.py) and runs it through the relay on a 24 x 80 terminal, on a
# file of 40 lines (TIMELINE_TEXT) that timeline_run() writes. timeline_boot() types what
# that lesson can do and checks the screen; keys whose lesson is still ahead must change
# nothing. timeline_after() then checks the file: untouched until 04.04, saved after.
#
# A project with the syntax highlighting of module 06 in it (an extension) is run on a
# small C file instead (TIMELINE_C_FILE), and its colours are checked too ("colors").

TIMELINE_FILE = "learn.txt"
TIMELINE_TEXT = "kilo at a lesson\n\tafter a tab\n" + "".join(f"line {i}\n" for i in range(3, 41))
TIMELINE_FAIL = [r"\[kilo exited", r"not written yet", r"\[relay: "]
TIMELINE_C_FILE = "learn.c"
TIMELINE_C_TEXT = ("/* kilo at a lesson\n"
                   "\n"
                   "   still a comment */ int n = 7;\n"
                   "int main(void) {\n"
                   "\tchar *s = \"a string\";  // a comment\n"
                   "\treturn 42;\n"
                   "}\n"
                   "x\x01y\n")


def highlights(root):
    """Does the project at root have module 06's syntax highlighting in it?"""
    try:
        with open(os.path.join(root, "kilo.c"), errors="replace") as f:
            return "editorSelectSyntaxHighlight" in f.read()
    except OSError:
        return False


def timeline_run(root):
    with open(os.path.join(root, TIMELINE_FILE), "w") as f:
        f.write(TIMELINE_TEXT)
    name = TIMELINE_FILE
    if highlights(root):
        with open(os.path.join(root, TIMELINE_C_FILE), "w") as f:
            f.write(TIMELINE_C_TEXT)
        name = TIMELINE_C_FILE
    return [sys.executable, os.path.abspath(__file__), "relay", "24", "80", "--", "./kilo", name]


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
    if lesson_id.startswith("06."):
        return _highlight_steps(k)
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


def _colors(rows, want):
    """A regex for the relay's dump of a screen's colours (Screen.dump_colors), `rows` high:
    want as for _screen(), each row written as paint() writes it."""
    parts = []
    for i in range(rows):
        w = want.get(i, want.get(i - rows))
        if w is None:
            parts.append(r".*\n")
        elif isinstance(w, re.Pattern):
            parts.append(w.pattern + r"\n")
        else:
            parts.append(re.escape(w) + r"\n")
    return r"\[colors\]\n" + "".join(parts) + r"\[end\]"


def _highlight_steps(k):
    """Steps for the project at a lesson of module 06, on TIMELINE_C_FILE: each lesson's
    colours on the first screen, and what the others leave plain. From 06.03, // typed in
    front of the comment's opening ends the comment for the rows below it, and two
    Backspaces bring it back; at 06.05 a search colours its match until Escape."""
    S, C = "screen", "colors"
    lines = TIMELINE_C_TEXT.replace("\t", " " * 8).replace("\x01", "A").split("\n")
    text = {i: lines[i] for i in range(8)} | {i: "~" for i in range(8, 22)}
    text[23] = "HELP: Ctrl-S = save | Ctrl-Q = quit | Ctrl-F = find"
    bar = re.compile(r"learn\.c - 8 lines +1/8")
    # Each row as Screen.dump_colors shows it at this lesson: nothing is coloured until the
    # lesson that brings its class; non-printable characters are in reverse from 06.01.
    n7 = "[r:7]" if k >= (6, 2) else "7"
    n42 = "[r:42]" if k >= (6, 2) else "42"
    string = '[m:"a string"]' if k >= (6, 2) else '"a string"'
    kw = (lambda w, c: f"[{c}:{w}]") if k >= (6, 4) else (lambda w, c: w)
    if k >= (6, 3):
        paint0, paint2, line_comment = "[c:/* kilo at a lesson]", "   [c:still a comment */]", "[c:// a comment]"
    else:
        paint0, paint2, line_comment = "/* kilo at a lesson", "   still a comment */", "// a comment"
    painted = {0: paint0, 1: "", 2: f"{paint2} {kw('int', 'g')} n = {n7};",
               3: f"{kw('int', 'g')} main({kw('void', 'g')}) {{",
               4: f"        {kw('char', 'g')} *s = {string};  {line_comment}",
               5: f"        {kw('return', 'y')} {n42};", 6: "}", 7: "x[#:A]y",
               22: re.compile(r"\[#:learn\.c - 8 lines +1/8\]"), 23: text[23]}
    steps = [(S, _screen(24, text | {22: bar}, cursor=(1, 1))), (C, _colors(24, painted))]
    if k >= (6, 3):
        # // in front of the comment's opening: row 0 is a // comment now, and the rows that
        # were inside the other comment are plain. Two Backspaces: as before.
        modified = re.compile(r"\[#:learn\.c - 8 lines \(modified\) +1/8\]")
        commented = painted | {0: "[c:///* kilo at a lesson]",
                               2: f"   still a comment */ {kw('int', 'g')} n = {n7};", 22: modified}
        steps += [("keys //", SENT), (C, _colors(24, commented)),
                  ("keys {bs}{bs}", SENT), (C, _colors(24, painted | {22: modified}))]
    if k >= (6, 5):
        # The search colours its match blue, over the number's red; Escape puts it back.
        found = {0: f"        {kw('return', 'y')} [b:42];", 1: "}", 2: "x[#:A]y", 3: "~",
                 23: "Search: 42 (Use ESC/Arrows/Enter)"}
        steps += [("keys {ctrl-f}42", SENT), (C, _colors(24, found)),
                  ("keys {esc}", SENT), (C, _colors(24, {5: painted[5], 23: ""}))]
    return steps


def timeline_after(root, lesson_id):
    """The file the run worked on: untouched until 04.04, saved with the edits after; at
    module 06, the C file, untouched (nothing there saves)."""
    from harness.core import lesson_key
    if lesson_id.startswith("06."):
        with open(os.path.join(root, TIMELINE_C_FILE), encoding="latin-1", newline="") as f:
            got = f.read()
        if got != TIMELINE_C_TEXT:
            raise Fail(f"{TIMELINE_C_FILE} changed, with no save: {got[:80]!r}")
        return f"{TIMELINE_C_FILE} untouched"
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
#   colors          the same wait, then the rows with their colours (Screen.dump_colors:
#                   "[colors]", each row as paint() writes it, "[end]").
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
            elif cmd in ("screen", "colors"):
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and (time.monotonic() - state["last"] < 0.4 or screen.rest):
                    pump(0.05)
                    if p.poll() is not None:
                        return finish()
                say(screen.dump() if cmd == "screen" else screen.dump_colors())
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
