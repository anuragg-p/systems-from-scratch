"""edit: a text editor whose text is held by the structure --algo names (module 03). T is track.py.

Replay (no terminal):

    ALGOS               every --algo, in the order the lessons bring them
    Model(data)         what any structure must make of a script: the text, the cursor and the
                        two undo stacks, in Python. m.run(script) returns what its print commands
                        printed; m.text is the text after it.
    replay(t, algo, script, path, env=None, check=True)
                        bin/edit --algo=algo --replay SCRIPT path, the script written to a file;
                        a Result
    check(t, script, path, algos=ALGOS, undo=True)
                        every structure in algos replays script on path and prints the bytes the
                        Model prints; returns {algo: stats} (each run with DS_STATS=1)
    random_script(seed, data, n, undo=True)
                        n random commands for a text that starts as data: goto (bytes, LINE:COL,
                        end), type, paste, back, delete, print, and undo and redo
    typing_script(at, keys), scattered_script(seed, length, edits)
                        what tools/edit/gen.py makes for the growth harness

The full-screen editor (a pseudo-terminal):

    edit(t, text=None, name="f.txt", algo=None, rows=24, cols=80, env=None)
                        write text to name in the scratch directory (None: leave it as it is,
                        or missing), start bin/edit [--algo=algo] name on a terminal of rows x
                        cols, and wait for its first screen; an Editor
    Editor              ed.keys(*parts) types each part and waits for the screen it draws;
                        ed.lines, ed.line(n), ed.cursor (row, col from 0), ed.status,
                        ed.message, ed.quit(), ed.saved(), ed.stats() (after quit, with
                        DS_STATS=1 in env)
    UP DOWN LEFT RIGHT DEL PAGE_UP PAGE_DOWN ESC ENTER BACKSPACE TAB, ctrl("q")
    Screen              a small VT100: what the program drew, as rows of text (from the kilo
                        track's track.py, which tests kilo the same way)

Run as a program, this file drives the editor for check-timeline's shell (which has no terminal):

    python3 edit.py drive ROWS COLS KEYS -- bin/edit ARGS...
                        start the program on a ROWS x COLS terminal, type KEYS ({enter} {esc}
                        {bs} {up} ... {ctrl-s}), wait for each screen, print the last one, and,
                        if the keys quit it, "[exit N]"
"""

import os
import re
import shlex
import signal
import struct
import subprocess
import sys
import time

try:
    from harness.core import Fail
except ImportError:          # run as a program (drive, below): no harness needed
    class Fail(Exception):
        pass

PROGRAMS = {"edit": "03.01"}
FILES_FROM = {
    "tools/edit/tool.mk": "03.01",
    "tools/edit/edit.c": "03.01",
    "tools/edit/LICENSE": "03.01",
    "tools/edit/gen.py": "03.01",
    "lib/text.h": "03.01",
    "lib/text.c": "03.01",
    "lib/flat.h": "03.01",
    "lib/gap.h": "03.02",
    "lib/undo.h": "03.03",
    "lib/pieces.h": "03.04",
    "lib/ptree.h": "03.05",
}
# Notes for the lesson writers, and what NOTICE is to say: not part of the project.
HIDDEN = ["tools/edit/NOTES.md", "tools/edit/NOTICE.txt"]

# The editor of module 03 is derived from antirez's kilo, by way of this course's kilo track.
# Not "derived" for the site: that would mark every lesson of the track as derived from kilo, and
# only module 03 is. The licence is printed whole on /credits all the same.
UPSTREAM = [{
    "name": "kilo",
    "url": "https://github.com/antirez/kilo",
    "licence": "BSD-2-Clause",
    "copyright": "Copyright (c) 2016, Salvatore Sanfilippo <antirez at gmail dot com>",
    "owes": "The editor of module 03, edit, is kilo as this course's kilo track builds it (terminal, "
            "keys, screen, search and saving), with its text moved behind lib/text.h. The structures "
            "that hold the text are this course's own.",
    "derived": False,
    "licence_file": "tools/edit/LICENSE",
}]

HERE = os.path.dirname(os.path.abspath(__file__))
ALGOS = ["array", "gap", "pieces", "tree"]
ALGO_LESSON = {"array": (3, 1), "gap": (3, 2), "pieces": (3, 4), "tree": (3, 5)}
NAMES = {"array": "flat array", "gap": "gap buffer", "pieces": "piece list", "tree": "piece tree"}


# ---------------------------------------------------------------- the model

def unescape(text):
    """A script's TEXT as bytes: \\n \\t \\\\ \\xHH, the rest as it is."""
    out, i = bytearray(), 0
    raw = text.encode("latin-1")
    while i < len(raw):
        c = raw[i:i + 1]
        if c != b"\\":
            out += c
            i += 1
            continue
        nxt = raw[i + 1:i + 2]
        if nxt == b"n":
            out += b"\n"
        elif nxt == b"t":
            out += b"\t"
        elif nxt == b"\\":
            out += b"\\"
        elif nxt == b"x":
            out.append(int(raw[i + 2:i + 4], 16))
            i += 2
        else:
            raise ValueError(f"no escape {nxt!r}")
        i += 2
    return bytes(out)


def escape(data):
    """bytes as a script's TEXT."""
    out = []
    for b in data:
        c = chr(b)
        if c == "\n":
            out.append("\\n")
        elif c == "\t":
            out.append("\\t")
        elif c == "\\":
            out.append("\\\\")
        elif 32 <= b < 127:
            out.append(c)
        else:
            out.append(f"\\x{b:02x}")
    return "".join(out)


class Model:
    """A script's edits, made to a bytearray: what every structure must print."""

    def __init__(self, data):
        self.text = bytearray(data)
        self.cur = 0
        self.done, self.undone = [], []      # [erase, pos, bytes]
        self.typing = False
        self.edits = 0

    def note(self, erase, pos, b, typed):
        self.undone.clear()
        top = self.done[-1] if self.done else None
        if (typed and self.typing and top and top[0] == erase and
                (pos + len(b) == top[1] if erase else top[1] + len(top[2]) == pos)):
            if erase:
                top[1], top[2] = pos, b + top[2]
            else:
                top[2] = top[2] + b
        else:
            self.done.append([erase, pos, bytes(b)])
            self.edits += 1
        self.typing = typed

    def insert(self, pos, b, typed):
        self.text[pos:pos] = b
        self.note(0, pos, b, typed)

    def erase(self, pos, n, typed):
        b = bytes(self.text[pos:pos + n])
        del self.text[pos:pos + n]
        self.note(1, pos, b, typed)

    def undo(self):
        self.typing = False
        if not self.done:
            return False
        e = self.done.pop()
        if e[0]:
            self.text[e[1]:e[1]] = e[2]
            self.cur = e[1] + len(e[2])
        else:
            del self.text[e[1]:e[1] + len(e[2])]
            self.cur = e[1]
        self.undone.append(e)
        return True

    def redo(self):
        self.typing = False
        if not self.undone:
            return False
        e = self.undone.pop()
        if e[0]:
            del self.text[e[1]:e[1] + len(e[2])]
            self.cur = e[1]
        else:
            self.text[e[1]:e[1]] = e[2]
            self.cur = e[1] + len(e[2])
        self.done.append(e)
        return True

    def run(self, script):
        printed = bytearray()
        for line in script.split("\n"):
            if not line or line.startswith("#"):
                continue
            word, _, arg = line.partition(" ")
            if word not in ("type", "back"):
                self.typing = False
            if word == "goto":
                if arg == "end":
                    self.cur = len(self.text)
                elif ":" in arg:
                    ln, col = (int(x) for x in arg.split(":"))
                    lines = bytes(self.text).split(b"\n")
                    assert 1 <= ln <= len(lines) and 1 <= col <= len(lines[ln - 1]) + 1, line
                    self.cur = sum(len(x) + 1 for x in lines[:ln - 1]) + col - 1
                else:
                    assert int(arg) <= len(self.text), line
                    self.cur = int(arg)
            elif word == "type":
                for b in unescape(arg):
                    self.insert(self.cur, bytes([b]), True)
                    self.cur += 1
            elif word == "paste":
                b = unescape(arg)
                if b:
                    self.insert(self.cur, b, False)
                    self.cur += len(b)
            elif word == "back":
                for _ in range(int(arg)):
                    if self.cur == 0:
                        break
                    self.cur -= 1
                    self.erase(self.cur, 1, True)
            elif word == "delete":
                n = min(int(arg), len(self.text) - self.cur)
                if n:
                    self.erase(self.cur, n, False)
            elif word in ("undo", "redo"):
                for _ in range(int(arg) if arg else 1):
                    if not (self.undo() if word == "undo" else self.redo()):
                        break
            elif word == "print":
                printed += self.text
            elif word == "save":
                pass
            else:
                raise ValueError(f"the model has no command {word!r}")
        return bytes(printed)


# ---------------------------------------------------------------- scripts

class _Rand:
    """data/gen.py's splitmix64, for scripts that are the same on every machine."""
    MASK = (1 << 64) - 1

    def __init__(self, seed):
        self.state = seed & self.MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & self.MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self.MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self.MASK
        return z ^ (z >> 31)

    def below(self, n):
        return self.next() % n


WORDS = ["the", "piece", "gap", "tree", "a", "cursor", "Holmes", "x", "editor", "undo"]


def _bytes(rng, k):
    """k random bytes of text: words, spaces, newlines, now and then a tab, a backslash or 0xff."""
    out = bytearray()
    while len(out) < k:
        r = rng.below(20)
        if r < 12:
            out += WORDS[rng.below(len(WORDS))].encode()
        elif r < 16:
            out += b" "
        elif r < 18:
            out += b"\n"
        elif r == 18:
            out += b"\t"
        else:
            out += b"\\\xff"[rng.below(2):][:1]
    return bytes(out[:k])


def random_script(seed, data, n, undo=True):
    """n random commands for a text that starts as data. The positions are always good: the script
    is made by running it on a Model as it goes."""
    rng = _Rand(seed)
    m = Model(data)
    lines = []
    kinds = ["goto", "goto", "type", "type", "type", "paste", "back", "delete", "print"]
    if undo:
        kinds += ["undo", "undo", "redo"]
    for _ in range(n):
        kind = kinds[rng.below(len(kinds))]
        if kind == "goto":
            r = rng.below(6)
            if r == 0:
                line = "goto end"
            elif r == 1:
                rows = bytes(m.text).split(b"\n")
                ln = 1 + rng.below(len(rows))
                line = f"goto {ln}:{1 + rng.below(len(rows[ln - 1]) + 1)}"
            else:
                line = f"goto {rng.below(len(m.text) + 1)}"
        elif kind in ("type", "paste"):
            line = f"{kind} {escape(_bytes(rng, 1 + rng.below(12 if kind == 'type' else 60)))}"
        elif kind in ("back", "delete"):
            line = f"{kind} {rng.below(8 if kind == 'back' else 40)}"
        elif kind in ("undo", "redo"):
            line = kind if rng.below(2) else f"{kind} {1 + rng.below(4)}"
        else:
            line = "print"
        lines.append(line)
        m.run(line)
    lines.append("print")
    return "\n".join(lines) + "\n"


def typing_script(at, keys, seed=1):
    """Type `keys` keys at byte `at`: words and spaces, a newline now and then, a word taken back
    with Backspace now and then. One goto, and then nothing but typing."""
    rng = _Rand(seed)
    lines, typed = [f"goto {at}"], 0
    while typed < keys:
        w = WORDS[rng.below(len(WORDS))] + (" " if rng.below(8) else "\\n")
        lines.append(f"type {w}")
        typed += len(unescape(w))
        if rng.below(10) == 0:
            lines.append("back 2")
            typed += 2
    return "\n".join(lines) + "\n"


def scattered_script(seed, length, edits):
    """`edits` words typed at random places of a text that starts `length` bytes long."""
    rng = _Rand(seed)
    lines = []
    for _ in range(edits):
        w = WORDS[rng.below(len(WORDS))] + " "
        lines.append(f"goto {rng.below(length + 1)}")
        lines.append(f"type {w}")
        length += len(w)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- replay

def replay(t, algo, script, path, env=None, check=True):
    sp = T.write(t, f"script-{abs(hash(script)) % 10**8}.txt", script)
    args = ([f"--algo={algo}"] if algo else []) + ["--replay", sp, path]
    return T.run(t, "edit", args, env=env, check=check)


def check(t, script, path, algos=ALGOS):
    """Every structure in algos, on the same script and file, prints what the Model prints."""
    with open(path, "rb") as f:
        want = Model(f.read()).run(script)
    got = {}
    for algo in algos:
        r = replay(t, algo, script, path, env={"DS_STATS": "1"})
        if r.raw != want:
            a, b = r.raw, want
            i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
            raise Fail(f"--algo={algo}: the replay printed {len(a)} bytes, the model {len(b)}; first "
                       f"difference at byte {i}: {a[max(0, i - 20):i + 20]!r} against {b[max(0, i - 20):i + 20]!r}")
        got[algo] = T.stats(r.err)
    return got


# ---------------------------------------------------------------- the screen
#
# What a terminal does with the bytes the editor writes, as much of it as kilo uses (this is
# the kilo track's Screen, which tests kilo the same way).

CSI = re.compile(rb"\x1b\[([0-9;?]*)([ -/]*)([@-~])")
CSI_CUT = re.compile(rb"\x1b(\[[0-9;?]*[ -/]*)?")


class Screen:
    """A terminal screen of rows x cols, fed with what the program writes to it.

    lines()     the text of each row, trailing spaces dropped
    cursor      (row, col) of the cursor, counting from 0
    frames      how many times the cursor has been shown again (ESC [ ? 25 h): the editor shows
                it once at the end of every screen it draws
    replies     what the terminal sends back (answers to ESC [ 6 n), not yet sent
    """

    def __init__(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.grid = [[" "] * cols for _ in range(rows)]
        self.y = self.x = 0
        self.frames = 0
        self.replies = []
        self.rest = b""

    @property
    def cursor(self):
        return self.y, min(self.x, self.cols - 1)

    def lines(self):
        return ["".join(row).rstrip() for row in self.grid]

    def _linefeed(self):
        if self.y == self.rows - 1:
            self.grid.pop(0)
            self.grid.append([" "] * self.cols)
        else:
            self.y += 1

    def _put(self, ch):
        if self.x >= self.cols:
            self.x = 0
            self._linefeed()
        self.grid[self.y][self.x] = ch
        self.x += 1

    def _erase(self, row, start, end):
        for c in range(max(0, start), min(self.cols, end)):
            self.grid[row][c] = " "

    def _csi(self, params, final):
        private = params.startswith("?")
        args = [int(a) if a.isdigit() else 0 for a in params.lstrip("?").split(";")] if params else []

        def arg(k, default):
            return (args[k] if k < len(args) else 0) or default
        x = min(self.x, self.cols - 1)
        if final in "Hf":
            self.y = min(max(arg(0, 1), 1), self.rows) - 1
            self.x = min(max(arg(1, 1), 1), self.cols) - 1
        elif final == "K":
            mode = args[0] if args else 0
            if mode == 0:
                self._erase(self.y, x, self.cols)
            elif mode == 1:
                self._erase(self.y, 0, x + 1)
            else:
                self._erase(self.y, 0, self.cols)
        elif final in "hl" and private and 25 in args:
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
                i += 2
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
        r, c = self.cursor
        return "".join(l + "\n" for l in self.lines()) + f"[cursor {r + 1},{c + 1}]\n"


UP, DOWN, RIGHT, LEFT = "\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"
HOME, END = "\x1b[H", "\x1b[F"
DEL, PAGE_UP, PAGE_DOWN = "\x1b[3~", "\x1b[5~", "\x1b[6~"
ESC, ENTER, BACKSPACE, TAB = "\x1b", "\r", "\x7f", "\t"


def ctrl(ch):
    """What Ctrl and a letter send: ctrl("q") is "\\x11"."""
    return chr(ord(ch.upper()) & 0x1f)


# ---------------------------------------------------------------- the editor on a terminal

class Editor:
    """bin/edit on a pseudo-terminal, with a Screen showing what it drew."""

    def __init__(self, t, argv, rows=24, cols=80, cwd=None, env=None, timeout=20):
        from harness.session import Session
        self.screen = Screen(rows, cols)
        full = dict(os.environ, LC_ALL="C", TERM="xterm")
        full.update(env or {})
        self.s = t.spawn(argv, name="edit", cwd=cwd, env=full, pty=True, size=(rows, cols)) if t else \
            Session(argv, name="edit", cwd=cwd, env=full, pty=True, size=(rows, cols))
        self.fed = 0
        self.last = time.monotonic()
        self.wait_frame(0, timeout=timeout)

    def pump(self, timeout=0.02):
        self.s._pump(timeout)
        if len(self.s.buf) > self.fed:
            self.screen.feed(self.s.buf[self.fed:])
            self.fed = len(self.s.buf)
            self.last = time.monotonic()
            while self.screen.replies:
                self.s.send(self.screen.replies.pop(0))

    def tail(self):
        m = re.search(rb"edit: \d\d\.\d\d: [^\r\n]* not written yet", self.s.buf)
        if m:
            return m.group(0).decode("utf-8", "replace")
        text = CSI.sub(b"", self.s.buf[-600:]).decode("utf-8", "replace")
        return " | ".join(l.strip() for l in text.replace("\r", "\n").split("\n") if l.strip())[-300:]

    def wait_frame(self, before, timeout=10, quiet=0.15):
        """Wait until the editor has finished a screen after the before-th, and then written
        nothing for `quiet` seconds."""
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
                raise Fail(f"edit exited with status {self.s.proc.returncode}: {self.tail()}")
            if now > deadline:
                raise Fail(f"edit drew no new screen within {timeout}s; it shows:\n{self.text()}")

    def keys(self, *parts):
        """Type each part, waiting after each for the screen it draws. A lone Escape is sent
        alone and waited on (sent with what follows, it would read as a sequence)."""
        for p in parts:
            before = self.screen.frames
            self.s.send(p)
            self.wait_frame(before, quiet=0.3 if p == ESC else 0.15)

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

    def quit(self, timeout=10):
        """Ctrl-Q (and three more, if there are unsaved changes), then wait for the exit; its
        status."""
        self.s.send(ctrl("q"))
        for _ in range(3):
            time.sleep(0.2)
            if self.s.proc.poll() is not None:
                break
            self.s.send(ctrl("q"))
        rc = self.s.wait_exit(timeout)
        self.pump(0)
        return rc

    def stats(self):
        """The DS_STATS=1 lines the editor printed as it exited."""
        raw = self.s.buf.decode("utf-8", "replace")
        return T.stats(raw[raw.find("stats: "):].replace("\r", ""))

    def saved(self):
        with open(self.path, "rb") as f:
            return f.read()


def edit(t, text=None, name="f.txt", algo=None, rows=24, cols=80, env=None, args=()):
    """bin/edit [--algo=algo] name in the test's scratch directory, with text written there first."""
    path = os.path.join(t.tmp, name)
    if text is not None:
        with open(path, "wb") as f:
            f.write(text.encode("latin-1") if isinstance(text, str) else text)
    argv = [os.path.join(t.root, "bin", "edit")] + ([f"--algo={algo}"] if algo else []) + list(args) + [name]
    ed = Editor(t, argv, rows, cols, cwd=t.tmp, env=env)
    ed.path = path
    return ed


# ---------------------------------------------------------------- drive, for the timeline

KEY_NAMES = {"enter": ENTER, "esc": ESC, "tab": TAB, "bs": BACKSPACE, "del": DEL, "up": UP, "down": DOWN,
             "left": LEFT, "right": RIGHT, "home": HOME, "end": END, "pgup": PAGE_UP, "pgdn": PAGE_DOWN}


def key_chunks(spec):
    """'ab{up}{ctrl-s}' -> ['ab', '\\x1b[A', '\\x13']."""
    out = []
    for part in re.split(r"(\{[a-z]+(?:-[a-z])?\})", spec):
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


def drive(args):
    """python3 edit.py drive ROWS COLS KEYS -- PROGRAM ARGS: the last screen, and the exit. The
    harness's Session runs the terminal: it is in the checkout this file is part of."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE)))))
    rows, cols, spec = int(args[0]), int(args[1]), args[2]
    argv = args[args.index("--") + 1:]
    ed = Editor(None, argv, rows, cols, cwd=os.getcwd())
    try:
        for chunk in key_chunks(spec):
            if chunk == ctrl("q"):
                ed.s.send(chunk)
                time.sleep(0.3)
                if ed.s.proc.poll() is not None:
                    break
                ed.wait_frame(ed.screen.frames - 1)
                continue
            ed.keys(chunk)
        sys.stdout.write(ed.screen.dump())
        if ed.s.proc.poll() is not None:
            ed.s.wait_exit(5)
            sys.stdout.write(f"[exit {ed.s.proc.returncode}]\n")
    finally:
        ed.s.close()
    return 0


def drive_step(rows, cols, keys, argv, screen, cursor, exit=None):
    """A timeline step: the editor driven on a terminal from the timeline's shell, and the screen
    it must show (its rows; the cursor as (row, col) from 1)."""
    cmd = " ".join(shlex.quote(a) for a in [sys.executable, os.path.join(HERE, "edit.py"), "drive", str(rows),
                                            str(cols), keys, "--"] + list(argv))
    out = "".join(r + "\n" for r in screen) + f"[cursor {cursor[0]},{cursor[1]}]\n"
    if exit is not None:
        out += f"[exit {exit}]\n"
    return T.sh_step(cmd + " < /dev/null", out)


# ---------------------------------------------------------------- the project at each lesson

def algos_at(k):
    return [a for a in ALGOS if ALGO_LESSON[a] <= k]


def timeline_steps(k):
    if k < (3, 1):
        return []
    have = algos_at(k)
    steps = [T.sh_step("printf 'world\\n' > e.txt; printf 'type Hello, \\nprint\\n' | bin/edit --replay - e.txt",
                       "Hello, world\n"),
             T.sh_step("printf 'goto 9\\n' | bin/edit --replay - e.txt", "edit: script line 1: goto 9: the text is 6 bytes\n", 2),
             T.sh_step("bin/edit e.txt < /dev/null",
                       "edit: e.txt: standard input and output must be a terminal (or use --replay SCRIPT)\n", 2)]
    if k < (3, 2):
        steps.append(T.sh_step("bin/edit --algo=gap --replay - e.txt < /dev/null", "edit: unknown option '--algo=gap'\n", 2))
    else:
        nxt = {(3, 2): "pieces", (3, 3): "pieces", (3, 4): "tree"}.get(k, "rope")
        steps.append(T.sh_step(f"bin/edit --algo={nxt} --replay - e.txt < /dev/null",
                               f"edit: no --algo '{nxt}' (have: {', '.join(have)})\n", 2))
    flags = [[]] if k < (3, 2) else [[f"--algo={a}"] for a in have]
    for f in flags:
        steps.append(T.sh_step(f"printf 'goto end\\nback 1\\ntype !\\\\n\\nprint\\n' | "
                               f"bin/edit {' '.join(f + ['--replay'])} - e.txt", "world!\n"))
    if k < (3, 3):
        steps.append(T.sh_step("printf 'type x\\nundo\\n' | bin/edit --replay - e.txt",
                               "edit: script line 2: unknown command 'undo'\n", 2))
    else:
        steps.append(T.sh_step("printf 'type abc\\nundo\\nprint\\nredo\\nprint\\n' | bin/edit --replay - e.txt",
                               "world\nabcworld\n"))
    # The full-screen editor on an 8 x 40 terminal, with each structure there is: typing, and
    # Ctrl-S saves. Then typing and Ctrl-Z: undone from 03.03, a message before it.
    for f in flags:
        algo = NAMES[f[0][7:]] if f else "flat array"
        argv = ["bin/edit"] + f + ["e.txt"]
        steps += [T.sh_step("printf 'world\\n' > e.txt", ""),
                  drive_step(8, 40, "Hello, {ctrl-s}", argv,
                             ["Hello, world"] + ["~"] * 5 + [status_bar(40, "e.txt", 1, 1, algo=algo),
                                                            "13 bytes written on disk"], (1, 8)),
                  T.sh_step("cat e.txt", "Hello, world\n")]
        if k < (3, 3):
            steps.append(drive_step(8, 40, "abc{ctrl-z}", argv,
                                    ["abcHello, world"] + ["~"] * 5 +
                                    [status_bar(40, "e.txt", 1, 1, True, algo=algo),
                                     "Nothing to undo: this editor keeps no hi"], (1, 4)))
        else:
            steps.append(drive_step(8, 40, "abc{ctrl-z}", argv,
                                    ["Hello, world"] + ["~"] * 5 +
                                    [status_bar(40, "e.txt", 1, 1, True, algo=algo),
                                     "HELP: Ctrl-S = save | Ctrl-Q = quit | Ct"], (1, 1)))
    return steps


def status_bar(cols, name, lines, row, modified=False, algo="gap buffer"):
    """The status bar of a screen cols wide: name, lines, (modified); the structure and row/lines."""
    left = f"{name} - {lines} lines {'(modified)' if modified else ''}"
    right = f"{algo} {row}/{lines}"
    return left + " " * (cols - len(left) - len(right)) + right


def timeline_after(root, k):
    if k < (3, 1):
        return None
    book = T.data(root, "book.txt")
    with open(book, "rb") as f:
        data = f.read()
    script = random_script(7, data, 300, undo=k >= (3, 3))
    want = Model(data).run(script)
    sp = os.path.join(root, "timeline-script.txt")
    with open(sp, "w") as f:
        f.write(script)
    for algo in algos_at(k):
        args = ([f"--algo={algo}"] if k >= (3, 2) else []) + ["--replay", sp, book]
        got = T.run(root, "edit", args).raw
        if got != want:
            raise Fail(f"bin/edit {' '.join(args)}: not what the model makes of the script")
    return f"edit: {len(algos_at(k))} structure(s) agree with the model on 300 random edits of the book"


if __name__ == "__main__":
    if sys.argv[1:2] == ["drive"]:
        sys.exit(drive(sys.argv[2:]))
    sys.exit("usage: edit.py drive ROWS COLS KEYS -- PROGRAM ARGS...")
