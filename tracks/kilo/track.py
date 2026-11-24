"""Track kilo: a text editor in C, antirez's kilo rebuilt lesson by lesson (UPSTREAM).

The editor is one binary, ./kilo FILE (make builds it from kilo.c, from module 07 on lsp.c
and json.c too, and from module 09 script.c and Lua's library, lua/). It talks to a
terminal: raw mode in, VT100 escape codes out, nothing in between. So do the tests: each runs
./kilo on a pseudo-terminal of a fixed size, types keys into it, and checks the screen it drew
(its escape codes turned into a grid of text by Screen, below) or the file it saved. Module
07's client also talks to a language server: its tests give it a scripted one
(tests/lsp_server.py), and clangd where it is installed. Module 09's tests give the editor an
init.lua, and run kilo -l.

Fixtures the lesson tests use:

    edit(t, text=None, name="f.txt", rows=24, cols=80, winsize=None, ctty=True, timeout=20,
         asan=False, lsp=None, env=None, utf8=False, init=None)
                        write text to name in the test's scratch directory (None: leave
                        the file as it is, or missing), start ./kilo name on a terminal
                        of rows x cols, and wait for its first screen (at most timeout
                        seconds); an Editor. asan=True: kilo built with AddressSanitizer
                        where the compiler can (asan_build), so a memory error stops it.
                        lsp: the language server (module 07): None, none (KILO_LSP set
                        and empty); a string, the scripted server playing that scenario
                        ("" for its tiny language), its log in ed.lsp_log; "table", KILO_LSP
                        left out, so clangd for a C file; "env", KILO_LSP as env has it.
                        utf8=True: Screen counts a UTF-8 character as one cell
                        init: module 09's init file: None, none (KILO_INIT set and empty);
                        a string, Lua written to an init.lua; "env", as env has it
    run_script(t, lua, text=None, name="f.txt", script="script.lua", exe=None, env=None)
                        kilo -l script [name] in the scratch directory, with no terminal:
                        what subprocess.run() gives (module 09)
    asan_build(t, sanitize="address")
                        the tree built with -fsanitize=..., or None where it cannot be
    Editor              ed.keys(*parts) types each part and waits for the screen to settle
                        ed.lines, ed.line(n), ed.cursor (row, col from 0), ed.status,
                        ed.message, ed.reverse(n): what the screen shows
                        ed.colors(n), ed.color(n, text), ed.painted(n): the colour of each
                        character (Screen.colors), for the syntax highlighting (module 06)
                        ed.under(n), ed.underlined(n): what is underlined (module 07)
                        ed.wait_for(cond, what), ed.wait_message(regex), ed.wait_said(text):
                        wait for what a server causes, reading the screen meanwhile
                        ed.server_log(), ed.received(method), ed.wait_received(method):
                        what the scripted server got
                        ed.raw: every byte kilo wrote; ed.screen: the Screen
                        ed.resize(rows, cols), ed.termios(), ed.quit(), ed.saved()
    UP DOWN LEFT RIGHT HOME END DEL PAGE_UP PAGE_DOWN ESC ENTER BACKSPACE TAB, ctrl("q")
                        what those keys send
    lines_of(n)         text of n numbered lines, "line 1\\n" to "line n\\n"
    lua_quote(s)        s as a Lua string literal, any byte in it
    paint(text, codes)  a row with its colours written in: "[g:int] x = [r:10];"
    children(pid), alive(pid), clangd(), skipped(t, what)
                        a process's children (state "Z": a zombie), whether a process is
                        there, clangd's path or None, and a line saying part of a test
                        did not run (the harness has no SKIP)

With ctty=True (the default) the terminal is the editor's controlling terminal, as in a
real one: Ctrl-C would be SIGINT if raw mode left ISIG on, and a resize sends SIGWINCH.
winsize=(0, 0) gives a terminal whose size the kernel does not know; Screen then answers
ESC [ 6 n as a real terminal does, with its own rows x cols.

Tests are internal. A lesson's test runs the whole editor, so with that lesson's code cut
out it fails at the stub: "kilo: NN.LL: <what> not written yet", exit status 3.

check-timeline runs the project at each lesson on a pseudo-terminal too: timeline_run()
starts this file as a program ("relay", at the end) that holds the terminal and a Screen,
and takes commands on its standard input: keys to type, "screen" to print what the
screen shows, "colors" its colours, "underline" what is underlined, "until REGEX" to wait
for the screen to match, "size R C" to resize it. At module 07 it runs with the scripted
server, never clangd, so it is the same on every machine. At module 09 it runs with an
init.lua of its own (TIMELINE_INIT), and prepare() first copies lua/ into the project, which
the site does not show (supply_lua).
"""

import json
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
SOURCES = ["kilo.c", "lsp.c", "json.c", "script.c"]
STUBS = {".c": 'kiloTodo("{id}", "{title}");'}
# Not for learners: notes for the lesson writers, and the ./kilo the Makefile builds; and
# Lua (module 09), the one thing in the track we do not write: its source is in lua/,
# unchanged, and the reader fetches it (09.01 says how). supply_lua() below puts it into a
# project the harness writes out, before it is built.
HIDDEN = ["NOTES.md", "kilo", "lua/*"]
# When each file comes into the project the site shows (see harness/timeline.py): kilo.c
# comes with its first region (01.01), lsp.c (07.01), json.c (07.02) and script.c (09.01)
# with theirs; the files without regions are named here. What later lessons add to a file
# outside their regions is marked "@from NN.LL" in the file itself.
FILES_FROM = {
    "LICENSE": "00.01",          # kilo's licence goes with every copy of the project
    "Makefile": "01.01",
    "lsp.h": "07.01",            # module 07, the language server client
    "json.h": "07.02",
    "script.h": "09.01",         # module 09, the API and Lua
    "api.h": "09.02",
}

LUA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lua")


def supply_lua(root):
    """Module 09 links Lua, built from lua/ beside kilo.c; the site hides lua/ (HIDDEN), so
    a project written out at a lesson of 09 has none. Copy the track's (its README and src/,
    without what a build left there) into root, when root's project has script.c and no
    lua/ yet. Nothing for any other project."""
    import shutil
    if not os.path.exists(os.path.join(root, "script.c")) or os.path.exists(os.path.join(root, "lua")):
        return
    shutil.copytree(LUA, os.path.join(root, "lua"),
                    ignore=shutil.ignore_patterns("*.o", "*.a", "lua", "luac", ".*"))


def build(t):
    t.run(["make", "-s"])


# ---------------------------------------------------------------- run it
#
# The track contract's optional hooks: prepare(root) returns the command that builds the
# tree, run_argv(root) the command that starts the system. Both run with cwd=root: the
# project as it stands at a lesson (./learn run kilo --at NN.LL writes it to
# build/at/kilo/NN.LL/), or the finished track.

def prepare(root):
    supply_lua(root)
    return ["make", "-s"]


def run_argv(root, args=()):
    """The editor on learn.txt, a file kept between runs (it does not exist until the first
    save); with args (./learn run kilo -- file.txt), on those instead."""
    return ["./kilo"] + (list(args) or ["learn.txt"])


# ---------------------------------------------------------------- the screen
#
# What a terminal does with the bytes kilo writes, as much of it as kilo uses: printable
# characters, "\r", "\n", backspace and tab, and the escape sequences ESC [ row ; col H
# (move), A B C D (move by), K and J (erase), m (reverse video on and off, underline on and
# off, and the foreground colour: 30 to 37, 39 for the default, 0 for everything off), ? 25 l
# / h (hide and show the cursor) and 6 n (report where the cursor is: answered in replies).

CSI = re.compile(rb"\x1b\[([0-9;?]*)([ -/]*)([@-~])")
CSI_CUT = re.compile(rb"\x1b(\[[0-9;?]*[ -/]*)?")
# A cell's colour as one letter: ESC [ 30 m to ESC [ 37 m. See Screen.colors().
COLOURS = {30: "k", 31: "r", 32: "g", 33: "y", 34: "b", 35: "m", 36: "c", 37: "w"}


class Screen:
    """A terminal screen of rows x cols, fed with what the program writes to it.

    lines()     the text of each row, trailing spaces dropped
    colors()    the colour of each character of lines(), one letter per cell (see there)
    unders()    which characters of lines() are underlined, "_" or "." per cell
    cursor      (row, col) of the cursor, counting from 0
    rev[r][c]   whether that cell was written in reverse video
    ul[r][c]    whether it was written underlined (ESC [ 4 m; ESC [ 24 m and 0 m end that)
    fg[r][c]    the foreground colour it was written in: 30 to 37, or None for the default
    frames      how many times the cursor has been shown again (ESC [ ? 25 h): kilo shows
                it once at the end of every screen it draws
    replies     what the terminal sends back (answers to ESC [ 6 n), not yet sent
    utf8        False: every byte from 0x20 up is a cell of its own (Latin-1), as all the
                tests up to module 07 have it; True: a UTF-8 character is one cell, as on a
                real terminal today (module 07's tests of text that is not ASCII)
    """

    def __init__(self, rows, cols, utf8=False):
        self.rows, self.cols = rows, cols
        self.utf8 = utf8
        self.grid = [[" "] * cols for _ in range(rows)]
        self.rev = [[False] * cols for _ in range(rows)]
        self.fg = [[None] * cols for _ in range(rows)]
        self.ul = [[False] * cols for _ in range(rows)]
        self.y = self.x = 0
        self.reverse = False
        self.underline = False
        self.colour = None
        self.cursor_shown = True
        self.frames = 0
        self.replies = []
        self.rest = b""          # an escape sequence cut in two between feeds

    def resize(self, rows, cols):
        grid = [[" "] * cols for _ in range(rows)]
        rev = [[False] * cols for _ in range(rows)]
        fg = [[None] * cols for _ in range(rows)]
        ul = [[False] * cols for _ in range(rows)]
        for r in range(min(rows, self.rows)):
            for c in range(min(cols, self.cols)):
                grid[r][c], rev[r][c], fg[r][c] = self.grid[r][c], self.rev[r][c], self.fg[r][c]
                ul[r][c] = self.ul[r][c]
        self.rows, self.cols, self.grid, self.rev, self.fg, self.ul = rows, cols, grid, rev, fg, ul
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

    def unders(self):
        """For each row, a mark per character of lines(): "_" where the cell is underlined,
        "." where it is not."""
        return ["".join("_" if self.ul[r][c] else "." for c in range(len(text)))
                for r, text in enumerate(self.lines())]

    def _linefeed(self):
        if self.y == self.rows - 1:
            self.grid.pop(0)
            self.rev.pop(0)
            self.fg.pop(0)
            self.ul.pop(0)
            self.grid.append([" "] * self.cols)
            self.rev.append([False] * self.cols)
            self.fg.append([None] * self.cols)
            self.ul.append([False] * self.cols)
        else:
            self.y += 1

    def _put(self, ch):
        if self.x >= self.cols:              # the last column is written: wrap now
            self.x = 0
            self._linefeed()
        self.grid[self.y][self.x] = ch
        self.rev[self.y][self.x] = self.reverse
        self.fg[self.y][self.x] = self.colour
        self.ul[self.y][self.x] = self.underline
        self.x += 1

    def _erase(self, row, start, end):
        for c in range(max(0, start), min(self.cols, end)):
            self.grid[row][c] = " "
            self.rev[row][c] = False
            self.fg[row][c] = None
            self.ul[row][c] = False

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
                    self.reverse, self.colour, self.underline = False, None, False
                elif a == 27:
                    self.reverse = False
                elif a == 7:
                    self.reverse = True
                elif a == 4:
                    self.underline = True
                elif a == 24:
                    self.underline = False
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
            elif self.utf8 and b >= 0xc0:
                k = 2 if b < 0xe0 else 3 if b < 0xf0 else 4
                if i + k > n and all(0x80 <= c < 0xc0 for c in data[i + 1:]):
                    self.rest = data[i:]                 # the rest of it is in the next feed
                    break
                try:
                    self._put(data[i:i + k].decode("utf-8"))
                    i += k
                    continue
                except UnicodeDecodeError:
                    self._put(chr(b))
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

    def dump_unders(self):
        """Every row with each underlined run in brackets, "x = [_:oops];": what the relay
        prints for "underline"."""
        return "[underline]\n" + "".join(paint(l, u) + "\n" for l, u in zip(self.lines(), self.unders())) \
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


def lua_quote(s):
    """s as a Lua string literal, any byte (a str of Latin-1 characters) written so: "a\\010b"."""
    out = []
    for ch in s:
        o = ord(ch)
        if ch in '"\\':
            out.append("\\" + ch)
        elif 32 <= o < 127:
            out.append(ch)
        else:
            out.append(f"\\{o:03d}")
    return '"' + "".join(out) + '"'


# ---------------------------------------------------------------- the editor on a terminal

# Make the terminal the program's controlling terminal (as a login does), then run it.
CTTY = ("import fcntl, os, sys, termios\n"
        "fcntl.ioctl(0, termios.TIOCSCTTY, 0)\n"
        "os.execv(sys.argv[1], sys.argv[1:])\n")


class Editor:
    """./kilo on a pseudo-terminal, with a Screen showing what it drew."""

    def __init__(self, t, args, rows=24, cols=80, winsize=None, ctty=True, cwd=None, timeout=20,
                 exe=None, env=None, utf8=False):
        self.t = t
        self.ctty = ctty
        self.screen = Screen(rows, cols, utf8)
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

    def under(self, n):
        """Row n with each underlined run in brackets: "x = [_:oops];" (module 07)."""
        return paint(self.line(n), self.screen.unders()[n])

    def underlined(self, n):
        """The columns of row n that are underlined, trailing spaces too (lines() drops them)."""
        return [c for c in range(self.screen.cols) if self.screen.ul[n][c]]

    # ------------------------------------------------------------ what a server causes

    def wait_for(self, cond, what, timeout=10):
        """Wait until cond() is true, reading what kilo draws meanwhile: for what arrives when
        the language server sends it, not when a key is typed. Fail after timeout seconds."""
        deadline = time.monotonic() + timeout
        while not cond():
            self.pump(0.02)
            if self.s.proc.poll() is not None:
                while self.s._pump(0.05):
                    pass
                self.pump(0)
                if cond():
                    return
                raise Fail(f"kilo exited with status {self.s.proc.returncode} waiting for {what}: {self.tail()}")
            if time.monotonic() > deadline:
                raise Fail(f"no {what} within {timeout}s; the screen:\n{self.text()}\n"
                           f"the server's log:\n{self.log_text()}")
        self.pump(0.05)

    def wait_message(self, pattern, timeout=10):
        """Wait until the message line matches pattern (a regex); the match."""
        self.wait_for(lambda: re.search(pattern, self.message), f"message {pattern!r}", timeout)
        return re.search(pattern, self.message)

    def said(self, text):
        """Has the message line shown text, on any screen so far (a later message may have
        replaced it since)?"""
        return b"\x1b[0K" + text.encode() in self.raw

    def wait_said(self, text, timeout=10):
        """Wait until the message line has shown text (said())."""
        self.wait_for(lambda: self.said(text), f"the message {text!r}", timeout)

    def server_log(self):
        """What the scripted server logged (tests/lsp_server.py): a dict per event."""
        return lsp_log(self.lsp_log)

    def received(self, method=None):
        """The messages the scripted server received, as JSON (None for one that was not),
        those with this method only if one is given."""
        return [e["msg"] for e in self.server_log()
                if e["event"] == "recv" and (method is None or (e["msg"] or {}).get("method") == method)]

    def wait_received(self, method, count=1, timeout=10):
        """Wait until the scripted server has received count messages with this method."""
        self.wait_for(lambda: len(self.received(method)) >= count, f"{count} {method} at the server", timeout)
        return self.received(method)

    def log_text(self):
        try:
            return "\n".join(json.dumps(e)[:300] for e in self.server_log()[-12:])
        except (OSError, AttributeError, TypeError):
            return "(no log)"

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


def asan_build(t, sanitize="address"):
    """The tree under test (kilo.c, and lsp.c, json.c and script.c when they are there, with
    Lua's library from the build) built with AddressSanitizer, into the test's scratch
    directory (once per test): a memory error then stops kilo with a report and status 1,
    where the plain build would go on, often showing nothing. None where the compiler cannot
    build that (gcc on musl, for one). sanitize: what -fsanitize= gets ("address,undefined"
    for module 09's fuzz), a build of its own."""
    attr = "_kilo_asan" if sanitize == "address" else "_kilo_san_" + sanitize.replace(",", "_")
    if not hasattr(t, attr):
        exe = os.path.join(t.tmp, "kilo-" + sanitize.replace(",", "-"))
        files = [f for f in ("kilo.c", "lsp.c", "json.c", "script.c") if os.path.exists(os.path.join(t.root, f))]
        lua = ["-Ilua/src", "lua/src/liblua.a", "-lm"] if "script.c" in files else []
        try:
            r = subprocess.run([os.environ.get("CC", "cc"), "-std=c99", "-g", "-fsanitize=" + sanitize,
                                "-fno-omit-frame-pointer", "-o", exe] + files + lua,
                               cwd=t.root, capture_output=True, timeout=300)
            setattr(t, attr, exe if r.returncode == 0 else None)
        except (OSError, subprocess.TimeoutExpired):
            setattr(t, attr, None)
    return getattr(t, attr)


def edit(t, text=None, name="f.txt", rows=24, cols=80, asan=False, lsp=None, env=None, init=None, **kw):
    """./kilo name in the test's scratch directory, with text written there first (name may
    be in a folder, which is made then). asan=True: the AddressSanitizer build (asan_build)
    where there is one, else the plain one; ed.asan says which ran.

    lsp: the language server (module 07). None: none (KILO_LSP set and empty), so every test
    of the core and of module 06 runs the finished editor as it ran before module 07 existed.
    A string: the scripted server (lsp_server), the string its scenario ("" for none); ed.lsp_log
    is its log. "table": KILO_LSP left out, so kilo chooses by the file's name (clangd). "env":
    KILO_LSP as env has it.

    init: the Lua init file (module 09). None: none (KILO_INIT set and empty), so no test runs
    a developer's own init.lua. A string: Lua, written to init.lua in the scratch directory
    (in its folder initN/ for the Nth editor of the test after the first) and named by
    KILO_INIT. "env": KILO_INIT and the rest as env has them."""
    path = os.path.join(t.tmp, name)
    if text is not None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="latin-1", newline="") as f:
            f.write(text)
    exe = asan_build(t) if asan else None
    env = dict(env or os.environ)
    if exe:
        # Leaks are no error here: kilo frees nothing on the way out, as the original does.
        env.setdefault("ASAN_OPTIONS", "detect_leaks=0")
    if init is None:
        env["KILO_INIT"] = ""
    elif init != "env":
        t._kilo_inits = getattr(t, "_kilo_inits", 0) + 1
        idir = t.tmp if t._kilo_inits == 1 else os.path.join(t.tmp, f"init{t._kilo_inits}")
        os.makedirs(idir, exist_ok=True)
        ipath = os.path.join(idir, "init.lua")
        with open(ipath, "w", encoding="latin-1", newline="") as f:
            f.write(init)
        env["KILO_INIT"] = ipath
    log = None
    if lsp is None:
        env["KILO_LSP"] = ""
    elif lsp == "table":
        env.pop("KILO_LSP", None)
    elif lsp != "env":
        t._kilo_lsps = getattr(t, "_kilo_lsps", 0) + 1     # a log of its own for each editor
        env, log = lsp_env(t.tmp, lsp, env, name=f"lsp{t._kilo_lsps}")
    ed = Editor(t, [name], rows, cols, cwd=t.tmp, exe=exe, env=env, **kw)
    ed.path = path
    ed.asan = bool(exe)
    ed.lsp_log = log
    return ed


def run_script(t, lua, text=None, name="f.txt", script="script.lua", exe=None, env=None, timeout=60):
    """kilo -l (module 09): write lua to script in the scratch directory, and text to name
    (None: no file is named on the command line; "": the name is given, the file is not
    written), run `kilo -l script [name]` there with no terminal, and return what
    subprocess.run() gives (returncode, stdout, stderr as text, latin-1)."""
    with open(os.path.join(t.tmp, script), "w", encoding="latin-1", newline="") as f:
        f.write(lua)
    args = [script]
    if text is not None:
        if text:
            with open(os.path.join(t.tmp, name), "w", encoding="latin-1", newline="") as f:
                f.write(text)
        args.append(name)
    env = dict(env or os.environ)
    env.setdefault("KILO_INIT", "")
    env.setdefault("ASAN_OPTIONS", "detect_leaks=0")
    return subprocess.run([exe or os.path.join(t.root, "kilo"), "-l"] + args, cwd=t.tmp,
                          stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout,
                          env=env, encoding="latin-1")


# ---------------------------------------------------------------- a scripted language server
#
# tests/lsp_server.py plays a language server for module 07's tests and its timeline (see its
# docstring): a tiny language, or a scenario of exact replies, delays, garbage and deaths, and a
# log of every message it received. It is not part of any project a reader sees.

LSP_SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "lsp_server.py")
LSP_NAME = "scripted-lsp"


def lsp_command(directory):
    """Write the scripted server's command into directory: one executable file, as KILO_LSP
    takes it, that runs tests/lsp_server.py with this Python (a #! line, so no shell and no
    descriptor of its own is in between). Its path."""
    path = os.path.join(directory, LSP_NAME)
    with open(path, "w") as f:
        f.write(f"#!{sys.executable}\nimport runpy\nrunpy.run_path({LSP_SERVER!r}, run_name='__main__')\n")
    os.chmod(path, 0o755)
    return path


def lsp_env(directory, scenario="", env=None, name="lsp"):
    """(environment, log path) for kilo with the scripted server, playing scenario (Python, see
    tests/lsp_server.py; "" for none), its files in directory."""
    env = dict(env or os.environ)
    log = os.path.join(directory, f"{name}.log")
    env["KILO_LSP"] = lsp_command(directory)
    env["KILO_TEST_LSP_LOG"] = log
    env.pop("KILO_TEST_LSP_SCENARIO", None)
    if scenario:
        spath = os.path.join(directory, f"{name}-scenario.py")
        with open(spath, "w") as f:
            f.write(scenario)
        env["KILO_TEST_LSP_SCENARIO"] = spath
    return env, log


def lsp_log(path):
    """The scripted server's log: a dict per line, [] before it has written one."""
    try:
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]
    except OSError:
        return []


def children(pid):
    """[(pid, state)] of the processes whose parent is pid; state "Z" for a zombie (a child
    that has exited and was never waited for). /proc on Linux, ps elsewhere."""
    out = []
    if os.path.isdir("/proc/self"):
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            try:
                with open(f"/proc/{d}/stat") as f:
                    fields = f.read().rsplit(")", 1)[1].split()
            except OSError:
                continue
            if int(fields[1]) == pid:
                out.append((int(d), fields[0]))
        return out
    r = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,stat="], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and int(parts[1]) == pid:
            out.append((int(parts[0]), parts[2][:1]))
    return out


def alive(pid):
    """Is there a process pid (a zombie counts: it is there until it is waited for)?"""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def clangd():
    """The path of clangd, or None where it is not installed."""
    import shutil
    return shutil.which("clangd")


def skipped(t, what):
    """Say that part of a test did not run (the harness has no word for that): one line on the
    test run's output, before the lesson's PASS or FAIL."""
    print(f"   {t.lesson.id}  skipped: {what}", flush=True)


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


# A project with module 07's language server client in it runs on TIMELINE_LSP_TEXT, with the
# scripted server (tests/lsp_server.py, its tiny language: "oops" is an error, the definition
# of a name is its "int NAME"), never clangd: the timeline is the same on every machine.
TIMELINE_LSP_TEXT = ("/* kilo at a lesson */\n"
                     "int total = 0;\n"
                     "int main(void) {\n"
                     "\ttotal = total + oops;\n"
                     "\treturn total;\n"
                     "}\n")


def has_lsp(root):
    """Does the project at root have module 07's language server client in it?"""
    return os.path.exists(os.path.join(root, "lsp.c"))


# A project with module 09's Lua in it runs on learn.txt with this init.lua (KILO_INIT), which
# uses what the lesson has: from 09.04 Ctrl-T comments the cursor's row or not; from 09.05 the
# words are counted on TextChanged; from 09.06 every number on the screen is red; from 09.07
# Ctrl-O asks for a line to go to.
TIMELINE_INIT = r"""
local n = 0
for _ in pairs(kilo.api or {}) do n = n + 1 end
print('init.lua: ' .. n .. ' functions')
if kilo.keymap then
  kilo.keymap.set('<C-t>', function()
    local row = kilo.api.get_cursor()[1]
    local line = kilo.api.get_lines(row, row + 1)[1]
    if line:sub(1, 3) == '-- ' then line = line:sub(4) else line = '-- ' .. line end
    kilo.api.set_lines(row, row + 1, {line})
  end)
end
if kilo.api and kilo.api.create_autocmd then
  kilo.api.create_autocmd('TextChanged', function()
    local words = 0
    for _, line in kilo.lines() do
      for _ in line:gmatch('%S+') do words = words + 1 end
    end
    kilo.api.message(words .. ' words')
  end)
end
if kilo.api and kilo.api.add_highlight then
  local ns = kilo.api.create_namespace('numbers')
  local function paint()
    kilo.api.clear_namespace(ns)
    local top, rows = kilo.api.get_view()[1], kilo.api.get_size()[1]
    local last = math.min(top + rows, kilo.api.line_count())
    if last <= top then return end
    for i, line in ipairs(kilo.api.get_lines(top, last)) do
      for s, e in line:gmatch('()%d+()') do
        kilo.api.add_highlight(ns, top + i - 1, s - 1, e - 1, 'red')
      end
    end
  end
  for _, event in ipairs({'BufReadPost', 'TextChanged', 'CursorMoved'}) do
    kilo.api.create_autocmd(event, paint)
  end
end
if kilo.api and kilo.api.input then
  kilo.api.set_keymap('<C-o>', function()
    local n = tonumber(kilo.api.input('Go to line: ') or '')
    if n and n >= 1 and n <= kilo.api.line_count() then kilo.api.set_cursor({math.floor(n) - 1, 0}) end
  end)
end
"""

# At 09.09 timeline_after runs this with kilo -l on a copy of learn.txt.
TIMELINE_UPPER = r"""
local n = 0
for row, line in kilo.lines() do
  local up = line:upper()
  if up ~= line then
    kilo.api.set_lines(row, row + 1, {up})
    n = n + 1
  end
end
kilo.api.save()
print(n .. ' lines upper-cased')
"""


def has_script(root):
    """Does the project at root have module 09's Lua in it?"""
    return os.path.exists(os.path.join(root, "script.c"))


def timeline_run(root):
    with open(os.path.join(root, TIMELINE_FILE), "w") as f:
        f.write(TIMELINE_TEXT)
    name = TIMELINE_FILE
    if has_script(root):
        init = os.path.join(root, "init.lua")
        with open(init, "w") as f:
            f.write(TIMELINE_INIT)
        return ["env", f"KILO_INIT={init}", sys.executable, os.path.abspath(__file__), "relay", "24", "80",
                "--", "./kilo", name]
    if highlights(root):
        with open(os.path.join(root, TIMELINE_C_FILE), "w") as f:
            f.write(TIMELINE_C_TEXT)
        name = TIMELINE_C_FILE
    relay = [sys.executable, os.path.abspath(__file__), "relay", "24", "80", "--", "./kilo"]
    if has_lsp(root):
        with open(os.path.join(root, TIMELINE_C_FILE), "w") as f:
            f.write(TIMELINE_LSP_TEXT)
        return (["env", f"KILO_LSP={lsp_command(root)}", f"KILO_TEST_LSP_LOG={os.path.join(root, 'lsp.log')}"]
                + relay + [TIMELINE_C_FILE])
    return relay + [name]


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
    if lesson_id.startswith("07."):
        return _lsp_steps(k)
    if lesson_id.startswith("09."):
        return _script_steps(k)
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


def _lsp_steps(k):
    """Steps for the project at a lesson of module 07, on TIMELINE_C_FILE with the scripted
    server: the message each lesson's code leads to, and from 07.05 what typing does; at
    07.06 the error underlined and its message, the cursor on its row; at 07.07 Ctrl-G and
    Ctrl-B."""
    S, U = "screen", "underline"
    lines = TIMELINE_LSP_TEXT.replace("\t", " " * 8).split("\n")
    text = {i: lines[i] for i in range(6)} | {i: "~" for i in range(6, 22)}
    bar = re.compile(r"learn\.c - 6 lines +1/6")
    if k < (7, 2):
        said = r"lsp: started scripted-lsp \(pid \d+\)"
    elif k < (7, 3):
        # The raw reply, its first bytes, as much of it as the message line holds.
        said = r"lsp: \d+ bytes from scripted-lsp: " + re.escape('{"jsonrpc":"2.0","id":1,"result":') + ".*"
    elif k < (7, 6):
        said = re.escape("lsp: scripted 1.0 ready")
    else:
        said = re.escape("lsp: 1 error")      # the counts, from the diagnostics after didOpen

    def until(row23, cursor, first=False):
        """A step that waits for what the server causes: the message line, the cursor (and,
        on the first screen, the status bar as the file opens)."""
        return (f"until \\n{row23}\\n\\[cursor {cursor[0]},{cursor[1]}\\]",
                _screen(24, text | {23: re.compile(row23)} | ({22: bar} if first else {}), cursor=cursor))
    steps = [until(said, (1, 1), first=True),
             # Keys are read as before: the cursor moves, past the tab.
             ("keys {down}{down}{down}{right}", SENT), (S, _screen(24, text, cursor=(4, 9)))]
    if k >= (7, 5):
        # Typing changes the text; at the pause the server is sent it (timeline_after reads
        # what it got). With the copy the server has, positions stay right.
        steps += [("keys x", SENT),
                  (S, _screen(24, text | {3: "        xtotal = total + oops;"}, cursor=(4, 10))),
                  ("keys {bs}", SENT), (S, _screen(24, text, cursor=(4, 9)))]
    if k >= (7, 6):
        # The error underlined where the screen shows it, past the tab; the cursor is on its
        # row, so the message line says what it is (when the list for the last change came,
        # and at the pause).
        under = {i: text[i] for i in range(6)} | {3: "        total = total + [_:oops];"}
        steps += [(U, _colors(24, under).replace(r"\[colors\]", r"\[underline\]")),
                  until(re.escape("4: error: use of undeclared identifier 'oops'"), (4, 9))]
    if k >= (7, 7):
        # Ctrl-G on "total" in "return total;": to "int total"; Ctrl-B back; Ctrl-B forth.
        steps += [("keys {down}{right}{right}{right}{right}{right}{right}{right}", SENT),
                  (S, _screen(24, text, cursor=(5, 16))),
                  ("keys {ctrl-g}", SENT), until(".*", (2, 5)),
                  ("keys {ctrl-b}", SENT), (S, _screen(24, text, cursor=(5, 16))),
                  ("keys {ctrl-b}", SENT), (S, _screen(24, text, cursor=(2, 5)))]
    return steps


def _lsp_after(root, lesson_id):
    """At module 07: the C file untouched (nothing saves), and the scripted server's log of
    what kilo sent it, lesson by lesson."""
    from harness.core import lesson_key
    k = lesson_key(lesson_id)
    with open(os.path.join(root, TIMELINE_C_FILE), encoding="latin-1", newline="") as f:
        if f.read() != TIMELINE_LSP_TEXT:
            raise Fail(f"{TIMELINE_C_FILE} changed, with no save")
    log = lsp_log(os.path.join(root, "lsp.log"))
    start = [e for e in log if e["event"] == "start"]
    got = [e["msg"] for e in log if e["event"] == "recv"]
    methods = [(m or {}).get("method") for m in got]
    if not start or start[0]["fds"] != {"0": "pipe", "1": "pipe", "2": "devnull"}:
        raise Fail(f"the server did not start with two pipes and /dev/null: {start}")
    if k < (7, 2):
        if got:
            raise Fail(f"at 07.01 kilo sends nothing, but the server got {methods}")
        return "the server started, with descriptors 0 1 2 only"
    if methods[:1] != ["initialize"] or got[0]["id"] != 1:
        raise Fail(f"the first message is not initialize, id 1: {methods[:3]}")
    if k < (7, 5):
        if methods != ["initialize"]:
            raise Fail(f"before 07.05 kilo sends only initialize: {methods}")
        return "the server got initialize"
    opened = [m["params"]["textDocument"] for m in got if (m or {}).get("method") == "textDocument/didOpen"]
    changes = [m["params"] for m in got if (m or {}).get("method") == "textDocument/didChange"]
    if methods[:3] != ["initialize", "initialized", "textDocument/didOpen"] or opened[0]["text"] != TIMELINE_LSP_TEXT \
            or opened[0]["version"] != 1:
        raise Fail(f"initialize, initialized, didOpen with the text, version 1: {methods[:3]} {opened[:1]}")
    want = [(TIMELINE_LSP_TEXT.replace("\ttotal", "\txtotal"), 2), (TIMELINE_LSP_TEXT, 3)]
    seen = [(c["contentChanges"][0]["text"], c["textDocument"]["version"]) for c in changes]
    if seen[:2] != want:
        raise Fail(f"didChange at each pause, whole, versions 2 and 3: {[(t[:40], v) for t, v in seen]}")
    note = f"the server got {', '.join(sorted(set(m for m in methods if m)))}"
    if k >= (7, 7) and not any(m == "textDocument/definition" for m in methods):
        raise Fail("no definition request")
    return note


def _script_steps(k):
    """Steps for the project at a lesson of module 09, on learn.txt with TIMELINE_INIT: what
    init.lua says, a line at the Ctrl-E prompt, and from each lesson on what it brings: the
    API's reads, a header put in with set_lines, Ctrl-T (Lua) commenting a row, the words
    counted on TextChanged, the numbers coloured and the status bar set, Ctrl-O asking for a
    line, a loop that never ends stopped by Ctrl-C."""
    S = "screen"
    rows = _file_rows(1, 22)
    bar = {22: re.compile(r"learn\.txt - 40 lines +1/40")}
    count = 24 if k >= (9, 7) else 21 if k >= (9, 6) else 15 if k >= (9, 5) else 12 if k >= (9, 4) \
        else 9 if k >= (9, 3) else 6 if k >= (9, 2) else 0
    steps = [(S, _screen(24, rows | bar | {23: f"init.lua: {count} functions"}, cursor=(1, 1))),
             ("keys {ctrl-e}1+1{enter}", SENT), (S, _screen(24, rows | {23: "2"}, cursor=(1, 1))),
             ("keys {ctrl-e}nosuch(){enter}", SENT),
             (S, _screen(24, rows | {23: "lua:1: attempt to call a nil value (global 'nosuch')"}, cursor=(1, 1))),
             ("keys {ctrl-e}x = 1{esc}", SENT), (S, _screen(24, rows | {23: ""}, cursor=(1, 1)))]
    if k < (9, 2):
        return steps
    # 09.02: the API's reads; a tab in a message is a space.
    steps += [("keys {ctrl-e}kilo.api.line_count(){enter}", SENT), (S, _screen(24, rows | {23: "40"})),
              ("keys {ctrl-e}kilo.api.get_lines(1, 2)[1]{enter}", SENT), (S, _screen(24, rows | {23: " after a tab"}))]
    if k < (9, 3):
        return steps
    # 09.03: a header put in above the cursor's row: the cursor stays on its line, one down.
    # From 09.05 the words are counted after each change (85 with the header).
    words = (lambda n: f"{n} words") if k >= (9, 5) else (lambda n: "")
    header = {0: "-- header"} | _file_rows(1, 21, top=1) | \
        {22: re.compile(r"learn\.txt - 41 lines \(modified\) +2/41")}
    steps += [("keys {ctrl-e}kilo.api.set_lines(0, 0, {'-- header'}){enter}", SENT),
              (S, _screen(24, header | {23: words(85)}, cursor=(2, 1)))]
    if k < (9, 4):
        return steps
    # 09.04: Ctrl-T, a Lua function, comments the cursor's row, and again takes it back.
    steps += [("keys {ctrl-t}", SENT), (S, _screen(24, header | {1: "-- kilo at a lesson", 23: words(86)}, cursor=(2, 1))),
              ("keys {ctrl-t}", SENT), (S, _screen(24, header | {23: words(85)}, cursor=(2, 1)))]
    if k >= (9, 5):
        # 09.05: typing counts the words again; moving does not.
        steps += [("keys x", SENT), (S, _screen(24, header | {1: "xkilo at a lesson", 23: "85 words"}, cursor=(2, 2))),
                  ("keys {bs}{down}", SENT),
                  (S, _screen(24, header | {22: re.compile(r"learn\.txt - 41 lines \(modified\) +3/41"),
                                            23: "85 words"}, cursor=(3, 1)))]
    if k >= (9, 6):
        # 09.06: the numbers on the screen in red (every line N); the status bar a script's.
        colored = {i: f"line [r:{i}]" for i in range(3, 22)}
        steps += [("colors", _colors(24, colored)),
                  ("keys {ctrl-e}kilo.api.set_statusline('my status'){enter}", SENT),
                  (S, _screen(24, header | {22: re.compile(r"my status +3/41"), 23: ""}))]
    if k >= (9, 7):
        # 09.07: Ctrl-O asks for a line, and goes there.
        steps += [("keys {ctrl-o}", SENT), (S, _screen(24, {23: "Go to line:"})),
                  ("keys 30{enter}", SENT), (S, _screen(24, {21: "line 29", 22: re.compile(r"my status +30/41")},
                                                       cursor=(22, 1)))]
    if k >= (9, 8):
        # 09.08: a loop that never ends, at the prompt; Ctrl-C stops it, and the editor goes on.
        steps += [("keys {ctrl-e}while true do end{enter}", SENT), ("keys {ctrl-c}", SENT),
                  (S, _screen(24, {21: "line 29", 23: "lua:1: interrupted"}, cursor=(22, 1)))]
    return steps


def _script_after(root, lesson_id):
    """At module 09: learn.txt untouched (nothing there saves); from 09.02 kilo --api-info,
    a line per function of the lesson's API; at 09.09 kilo -l upper-cases a copy of it."""
    from harness.core import lesson_key
    k = lesson_key(lesson_id)
    with open(os.path.join(root, TIMELINE_FILE)) as f:
        if f.read() != TIMELINE_TEXT:
            raise Fail(f"{TIMELINE_FILE} changed, with no save")
    notes = [f"{TIMELINE_FILE} untouched"]
    if k >= (9, 2):
        r = subprocess.run(["./kilo", "--api-info"], cwd=root, capture_output=True, text=True, timeout=20,
                           stdin=subprocess.DEVNULL)
        want = 24 if k >= (9, 7) else 21 if k >= (9, 6) else 15 if k >= (9, 5) else 12 if k >= (9, 4) \
            else 9 if k >= (9, 3) else 6
        lines = r.stdout.splitlines()
        if r.returncode != 0 or len(lines) != want or not lines[1].startswith("get_lines(start: integer, end: integer)"):
            raise Fail(f"--api-info: status {r.returncode}, {len(lines)} lines, not {want}: {lines[:2]}")
        notes.append(f"--api-info {want} functions")
    if k >= (9, 9):
        with open(os.path.join(root, "upper.lua"), "w") as f:
            f.write(TIMELINE_UPPER)
        with open(os.path.join(root, "copy.txt"), "w") as f:
            f.write(TIMELINE_TEXT)
        r = subprocess.run(["./kilo", "-l", "upper.lua", "copy.txt"], cwd=root, capture_output=True, text=True,
                           timeout=20, stdin=subprocess.DEVNULL, env=dict(os.environ, KILO_INIT=""))
        with open(os.path.join(root, "copy.txt")) as f:
            got = f.read()
        if (r.returncode, r.stdout, r.stderr) != (0, "40 lines upper-cased\n", "") or got != TIMELINE_TEXT.upper():
            raise Fail(f"kilo -l upper.lua: {r.returncode} {r.stdout!r} {r.stderr!r} {got[:40]!r}")
        notes.append("kilo -l upper-cased 40 lines")
    return ", ".join(notes)


def timeline_after(root, lesson_id):
    """The file the run worked on: untouched until 04.04, saved with the edits after; at
    module 06, the C file, untouched (nothing there saves); at module 07 that too, and what
    the scripted server was sent; at module 09, learn.txt untouched, --api-info and kilo -l."""
    from harness.core import lesson_key
    if lesson_id.startswith("07."):
        return _lsp_after(root, lesson_id)
    if lesson_id.startswith("09."):
        return _script_after(root, lesson_id)
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
#   underline       the same, with each underlined run in brackets (Screen.dump_unders:
#                   "[underline]", "x = [_:oops];", "[end]"), for module 07.
#   until REGEX     wait (10 s at most) until the screen's dump matches REGEX, then print it as
#                   "screen" does: for what a language server causes, when it comes.
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
            elif cmd in ("screen", "colors", "underline"):
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and (time.monotonic() - state["last"] < 0.4 or screen.rest):
                    pump(0.05)
                    if p.poll() is not None:
                        return finish()
                say(screen.dump() if cmd == "screen" else screen.dump_colors() if cmd == "colors"
                    else screen.dump_unders())
            elif cmd.startswith("until "):
                # What a language server causes comes when it comes: wait (10 s at most) for the
                # screen's dump to match, then for quiet, as "screen" does.
                rx = re.compile(cmd[len("until "):])
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and not (rx.search(screen.dump()) and not screen.rest
                                                           and time.monotonic() - state["last"] >= 0.2):
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
