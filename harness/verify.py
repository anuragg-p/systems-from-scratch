"""./learn verify: what a lesson says is what the project at that lesson does.

Internal, for authors, like check-timeline: learners never see it, and no page, lesson or
learner-facing help mentions it. The annotation syntax is documented once, for authors, in
README.md ("Verifying a lesson"); this docstring is the design.

What it checks, lesson by lesson:

  static (no build; also part of ./learn check)
    - every fenced block is accounted for: a terminal transcript declared with a `session`
      annotation, code the reader types (`patch ... @block`), a block of ./learn commands, a
      block declared `skip` with a reason, or else code quoted from the project, every line
      of which must be in the project as it stands at that lesson (timeline.Project);
    - `name()`, `file.c` and `path/file.c:name` in backticks name things that exist at the
      lesson, unless the sentence names the lesson they come with or an annotation says so;
    - ./learn commands name a track and an existing lesson, and only commands learners use;
    - no test/stub/workspace talk; front matter and section order as templates/lesson.md;
      figures referenced exist (unreferenced ones are reported, not failed);
    - every patch applies to the project at its lesson, and adds only lines the page shows;
    - the annotations themselves parse, and sit where they belong.

  replayed (builds and runs; ./learn verify only)
    - the lesson is read top to bottom in one terminal, as a reader would: a bash on a
      pseudo-terminal in a copy of the checkout's layout (build/verify/run/<track>/<id>/),
      where ./learn run, bench and files are the real commands (writing build/at/... under
      that copy), so `cd build/at/db/04.02`, shell variables and pipes all work;
    - a session block is replayed line by line: a line that starts with a prompt the
      terminal is showing ("$ ", "db> ", "   ...> ", "(qemu) ", ...) is typed, the rest is
      what must come back; the screen (escapes, carriage returns and line editing applied)
      is then compared with the block, exactly unless the annotation allows a difference;
    - patches change the reader's copy of the project, reverts undo them; facts run a
      command and compare its output with a number the prose states.

Results are cached under build/verify/cache/ by a hash of the lesson file, the project at
every lesson it uses, the verifier itself and the tools it found: a lesson that passed is not
run again until one of those changes (--fresh runs everything). Nothing is ever written under
work/ or tracks/.
"""

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time

from harness import core, timeline
from harness.web import markdown as md

HERE = os.path.dirname(os.path.abspath(__file__))
PENDING_FILE = "verify-pending.txt"     # tracks/<id>/lessons/: lessons not annotated yet

# ---------------------------------------------------------------- small helpers

WS = re.compile(r"\s+")
IDENT = re.compile(r"[A-Za-z_]\w*")
LESSON_REF = re.compile(r"(?<![\d.])(\d\d\.\d\d)(?![\d])")
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+.-]*)\s*$")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
FIGURE = re.compile(r"^\s{0,3}!\[([^\]\n]*)\]\(\s*([^)\s]+)\s*\)\s*$")
SPAN = re.compile(r"(`+)(.+?)\1")
LEARN_CMD = re.compile(r"\./learn((?:\s+[^\s`]+)*)")


def norm(text):
    return WS.sub(" ", text).strip()


def c_like(rel):
    return rel.endswith((".c", ".h", ".ld", ".S", ".s"))


def code_only(rel, line):
    """A line without its comment: C's // and /* */ for C-like files, " #" for the others."""
    if c_like(rel):
        return timeline.code_part(line)
    k = line.find(" #")
    return line[:k] if k >= 0 else ("" if line.lstrip().startswith("#") else line)


class Problem:
    """One thing wrong with a lesson: where (file and line), and what."""

    def __init__(self, path, line, message, warning=False):
        self.path, self.line, self.message, self.warning = path, line, message, warning

    def __str__(self):
        where = os.path.relpath(self.path, core.ROOT) if os.path.isabs(self.path) else self.path
        if where.startswith(".."):
            where = self.path
        return f"{where}:{self.line}: {self.message}"


class AnnotationError(Exception):
    pass


# ---------------------------------------------------------------- reading a lesson

class Note:
    """One <!-- verify: KIND options ... --> annotation."""

    def __init__(self, line, kind, opts, flags, body):
        self.line = line            # line number of "<!-- verify:" in the lesson
        self.kind = kind
        self.opts = opts            # name -> value
        self.flags = flags          # names given without a value
        self.body = body            # [(line number, text)] of the lines between header and -->
        self.block = None           # the fenced block it applies to, for block kinds
        self.expect = None          # session, file: what the block says comes back, once built

    def has(self, name):
        return name in self.flags or name in self.opts

    def at(self, lesson_id):
        """The lesson whose project this note works on: at=, or run='s --at, or the lesson's own."""
        if "at" in self.opts:
            return None if self.opts["at"] == "finished" else self.opts["at"]
        run = self.opts.get("run")
        if run:
            got = learn_at(run)
            if got is not False:
                return got
        return lesson_id


class Block:
    """One fenced code block: where it is, and its lines with the fence's indent taken off."""

    def __init__(self, start, end, lines, indent):
        self.start = start          # line number of the opening fence
        self.end = end              # line number of the closing fence
        self.lines = lines
        self.indent = indent
        self.notes = []
        self.role = None            # session, quote, skip, typed or command

    def line_no(self, k):
        return self.start + 1 + k

    @property
    def text(self):
        return "\n".join(self.lines)


KINDS = {
    "session": {"at", "run", "type", "fresh", "host", "send", "more", "before", "trimmed", "hangs", "panics",
                "build-fails", "exit", "timeout", "wait", "cwd", "terminal", "needs"},
    "file": {"path", "at", "trimmed"},
    "patch": {"file", "at", "append", "create", "old", "new"},
    "revert": {"file", "at"},
    "setup": {"at", "cwd", "terminal", "timeout"},
    "quote": {"at"},
    "skip": {"reason"},
    "fact": {"cmd", "expect", "at"},
    "mention": {"names", "at", "outside", "reason"},
}
BLOCK_KINDS = {"session", "quote", "skip", "file"}
FLAG_ONLY = {"fresh", "host", "more", "before", "trimmed", "append", "create", "outside"}

OPTION = re.compile(r'''([A-Za-z][\w-]*)(?:=("(?:[^"\\]|\\.)*"|'[^']*'|[^\s"']+))?''')


def parse_options(text):
    """'a=1 b="x y" c' -> ({a: 1, b: x y}, {c}). Raises AnnotationError on anything else."""
    opts, flags, i = {}, set(), 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        m = OPTION.match(text, i)
        if not m or (m.end() < len(text) and not text[m.end()].isspace()):
            raise AnnotationError(f"cannot read the options from {text[i:i + 30]!r}")
        name, value = m.group(1), m.group(2)
        if value is None:
            flags.add(name)
        else:
            if value[:1] == '"':          # \" and \\ are escapes; any other backslash is itself
                value = re.sub(r'\\(["\\])', r'\1', value[1:-1])
            elif value[:1] == "'":
                value = value[1:-1]
            opts[name] = value
        i = m.end()
    return opts, flags


class Doc:
    """A lesson file, read for verify: its blocks, annotations and prose, in order."""

    def __init__(self, path, lesson_id=None):
        self.path = path
        with open(path, encoding="utf-8", errors="replace") as f:
            self.text = f.read()
        self.lines = self.text.split("\n")
        self.id = lesson_id
        self.meta = {}
        self.meta_end = 0
        self.items = []             # Notes (actions) and Blocks, in the order they come
        self.blocks = []
        self.notes = []
        self.prose = []             # [(line number, text)]: lines outside blocks and comments
        self.errors = []            # Problems found while reading
        self._parse()

    def error(self, line, message):
        self.errors.append(Problem(self.path, line, message))

    def _parse(self):
        lines, n, i = self.lines, len(self.lines), 0
        if lines and lines[0].strip() == "---":
            for k in range(1, n):
                if lines[k].strip() == "---":
                    for line in lines[1:k]:
                        if ":" in line:
                            key, v = line.split(":", 1)
                            self.meta[key.strip()] = v.strip()
                    self.meta_end = k + 1
                    i = k + 1
                    break
        waiting = []                # block notes not yet given their block
        while i < n:
            line = lines[i]
            m = FENCE.match(line)
            if m:
                indent, fence = len(m.group(1)), m.group(2)
                body, j = [], i + 1
                while j < n and not md._closes(fence, lines[j]):
                    body.append(lines[j][indent:] if lines[j][:indent].strip() == "" else lines[j].lstrip())
                    j += 1
                if j >= n:
                    self.error(i + 1, "a fenced block that never closes")
                block = Block(i + 1, j + 1, body, indent)
                self.blocks.append(block)
                for note in waiting:
                    note.block = block
                    block.notes.append(note)
                waiting = []
                self.items.append(block)
                i = j + 1
                continue
            if line.lstrip().startswith("<!--"):
                j = i
                while j < n and "-->" not in (lines[j] if j > i else lines[j][lines[j].find("<!--") + 4:]):
                    j += 1
                if j >= n:
                    self.error(i + 1, "an HTML comment that never closes: the rest of the page would vanish")
                    return
                note = self._note(i, j)
                if note is not None:
                    self.notes.append(note)
                    if note.kind in BLOCK_KINDS or (note.kind == "patch" and any(t.strip() == "@block" for _, t in note.body)):
                        waiting.append(note)
                    else:
                        self.items.append(note)
                after = lines[j][lines[j].find("-->") + 3:]
                if after.strip():
                    self.prose.append((j + 1, after))
                i = j + 1
                continue
            if "<!--" in line:
                kept, still_open = md._uncomment_line(line, False)
                if "verify:" in line:
                    self.error(i + 1, "an annotation goes on lines of its own, before the block it is about")
                if still_open:
                    self.error(i + 1, "an HTML comment inside a line that does not close on it")
                line = kept
            if line.strip() and waiting:
                for note in waiting:
                    self.error(note.line, f"`{note.kind}` must come directly before the fenced block it is "
                                          f"about, but line {i + 1} is text")
                waiting = []
            self.prose.append((i + 1, line))
            i += 1
        for note in waiting:
            self.error(note.line, f"`{note.kind}` has no fenced block after it")

    def _note(self, i, j):
        """The annotation on lines i..j (indexes), or None for a comment that is not one."""
        first = self.lines[i].lstrip()[4:]
        if not first.lstrip().startswith("verify:"):
            if re.match(r"\s*verify\b", first):
                self.error(i + 1, "an annotation starts `<!-- verify: KIND`")
            return None
        head = first.lstrip()[len("verify:"):]
        body = []
        if i == j:
            head = head[:head.find("-->")]
        else:
            for k in range(i + 1, j + 1):
                text = self.lines[k]
                if k == j:
                    text = text[:text.find("-->")]
                    if not text.strip():
                        break
                body.append((k + 1, text))
        parts = head.strip().split(None, 1)
        if not parts:
            self.error(i + 1, "an annotation with no kind; kinds: " + ", ".join(sorted(KINDS)))
            return None
        kind = parts[0]
        if kind not in KINDS:
            self.error(i + 1, f"unknown annotation `{kind}`; kinds: " + ", ".join(sorted(KINDS)))
            return None
        try:
            opts, flags = parse_options(parts[1] if len(parts) > 1 else "")
        except AnnotationError as e:
            self.error(i + 1, str(e))
            return None
        unknown = sorted((set(opts) | flags) - KINDS[kind])
        if unknown:
            self.error(i + 1, f"`{kind}` does not take {', '.join(unknown)}; it takes "
                              + ", ".join(sorted(KINDS[kind])))
        for name in flags - FLAG_ONLY - {"hangs"}:
            if name in KINDS[kind]:
                self.error(i + 1, f"`{name}` needs a value: {name}=...")
        for name in set(opts) & FLAG_ONLY:
            self.error(i + 1, f"`{name}` is a flag: write it without a value")
        return Note(i + 1, kind, opts, flags, body)

    # ---- prose, as sentences and spans

    def paragraphs(self):
        """[(text joined with spaces, [(offset, line number)])] of the prose: a heading, a figure
        line and a list item each start one, a blank line ends one."""
        out, cur = [], None
        for number, line in self.prose:
            if number <= self.meta_end:
                continue
            if not line.strip():
                cur = None
                continue
            starts = HEADING.match(line) or FIGURE.match(line) or LIST_ITEM.match(line)
            if cur is None or starts:
                cur = ["", []]
                out.append(cur)
            if HEADING.match(line):
                text = HEADING.match(line).group(2)
            else:
                text = line.strip()
            if cur[0]:
                cur[0] += " "
            cur[1].append((len(cur[0]), number))
            cur[0] += text
            if HEADING.match(line):
                cur = None
        return [(t, offs) for t, offs in out]

    def visible_text(self):
        """Everything a reader sees, roughly: prose and block lines, comments gone."""
        return "\n".join([t for _, t in self.prose] + [b.text for b in self.blocks])


def line_at(offsets, pos):
    """The line number of offset pos in a joined paragraph."""
    got = offsets[0][1]
    for off, number in offsets:
        if off <= pos:
            got = number
    return got


def sentences(text):
    """[(start, end)] of the sentences of a paragraph: code spans are not split."""
    masked = SPAN.sub(lambda m: "x" * len(m.group(0)), text)
    out, start = [], 0
    for m in re.finditer(r"[.!?](\s+|$)", masked):
        out.append((start, m.end()))
        start = m.end()
    if start < len(text):
        out.append((start, len(text)))
    return out


def learn_at(command):
    """The lesson a ./learn run/bench/files command works on: its --at, None for the finished
    track, or False when it is not such a command."""
    m = re.search(r"\./learn\s+(run|bench|files)\b(.*)", command)
    if not m:
        return False
    rest = m.group(2).split(" -- ")[0]
    a = re.search(r"--at(?:\s+|=)(\S+)", rest)
    return a.group(1) if a else None


# ---------------------------------------------------------------- the project at a lesson, read

class Index:
    """What the project at one lesson holds, for the static checks: its files, every line
    (whitespace-normalised, with and without comments), every identifier, and a digest."""

    def __init__(self, proj, at):
        self.at = at
        self.files = {}
        h = hashlib.sha256()
        for rel in proj.files_at(at):
            data = proj.content(rel, at)
            h.update(f"{rel}\0{len(data)}\0".encode())
            h.update(data)
            if b"\0" in data[:8192]:
                continue
            lines = data.decode("utf-8", errors="replace").split("\n")
            self.files[rel] = lines
        self.digest = h.hexdigest()
        self.norm = set()
        self.idents = set()
        self.file_idents = {}
        for rel, lines in self.files.items():
            ids = set()
            for line in lines:
                n = norm(line)
                if n:
                    self.norm.add(n)
                code = code_only(rel, line)
                c = norm(code)
                if c:
                    self.norm.add(c)
                ids.update(IDENT.findall(code))
            self.file_idents[rel] = ids
            self.idents |= ids
        self.basenames = {os.path.basename(r) for r in self.files}
        self._sorted = None

    def has_line(self, quoted):
        n = norm(unarrow(quoted))
        if not n or n in TRIVIAL:
            return True
        if n in self.norm:
            return True
        c = norm(timeline.code_part(unarrow(quoted)))
        if c and c in self.norm:
            return True
        if "..." in n:      # code left out inside the line: the parts must be there, in order
            rx = re.compile("^" + ".*".join(re.escape(p.strip()) for p in n.split("...")) + "$")
            if self._sorted is None:
                self._sorted = sorted(self.norm)
            return any(rx.search(x) for x in self._sorted)
        return False

    def has_file(self, name):
        return name in self.files if "/" in name else name in self.basenames

    def file_named(self, name):
        if name in self.files:
            return name
        return next((r for r in self.files if os.path.basename(r) == name and "/" not in name), None)


TRIVIAL = {"...", "{", "}", "};", "});", ")", "(", "*/", "/*", "*", "//", "// ...", "/* ... */", "# ...",
           "} ...", "...;", "......"}
# A note the lesson puts after a line of quoted code to point at it ("    <- delete this line",
# "  <- was: x"): not code, so quotes and file excerpts are compared without it.
ARROW = re.compile(r"\s+<-+\s.*$")


def unarrow(line):
    return ARROW.sub("", line)


# ---------------------------------------------------------------- what the screen shows

CSI = re.compile(r"\x1b\[([0-9;?]*)([ -/]*)([@-~])")
OSC = re.compile(r"\x1b\][^\x07\x1b]*(\x07|\x1b\\)")


def screen_lines(text):
    """The lines a terminal shows for text: carriage returns, backspaces, tabs and the line
    editing escapes (erase line, cursor left and right) applied, every other escape dropped.
    The last element is the line the cursor is on (kept with its trailing spaces)."""
    lines, cur, col, i, n = [], [], 0, 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\x1b":
            m = CSI.match(text, i)
            if m:
                arg = m.group(1)
                num = int(arg) if arg.isdigit() else 1
                op = m.group(3)
                if op == "K":
                    if arg in ("", "0"):
                        del cur[col:]
                    elif arg == "2":
                        cur = [" "] * col
                elif op == "D":
                    col = max(0, col - num)
                elif op == "C":
                    col += num
                elif op == "G":
                    col = max(0, num - 1)
                i = m.end()
                continue
            m = OSC.match(text, i)
            i = m.end() if m else i + 2
            continue
        if ch == "\r":
            col = 0
        elif ch == "\n":
            lines.append("".join(cur).rstrip())
            cur, col = [], 0
        elif ch == "\b":
            col = max(0, col - 1)
        elif ch == "\t":
            col = (col // 8 + 1) * 8
        elif ch < " " or ch == "\x7f":
            pass
        else:
            while len(cur) < col:
                cur.append(" ")
            if col < len(cur):
                cur[col] = ch
            else:
                cur.append(ch)
            col += 1
        i += 1
    last = "".join(cur).rstrip()
    lines.append(last + " " * max(0, col - len(last)))       # blanks only up to the cursor
    return lines


# ---------------------------------------------------------------- what the lesson says comes back

KIND_RX = {"int": r"-?\d+", "num": r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", "hex": r"[0-9a-fA-F]+",
           "addr": r"0x[0-9a-fA-F]+", "word": r"\S+", "any": r".*?"}
# What shells say about jobs and killed processes, which differs from shell to shell (bash's
# "[1] 4242" and "Killed: 9", zsh's "zsh: killed ..."): `ignore job-reports` drops these lines.
JOB_REPORTS = re.compile(
    r"\[\d+\][+-]?\s+(\d+|(Done|Running|Stopped|Killed|Terminated|Exit \d+|Segmentation fault|Abort trap|"
    r"Bus error|Interrupt)(: \d+)?(\s.*)?)"
    r"|(\S+: line \d+: +\d+ )?(Killed|Terminated|Segmentation fault|Abort trap|Bus error)(: \d+)?( \(core dumped\))?(\s.*)?"
    r"|zsh: (killed|terminated|segmentation fault|abort|bus error|interrupt|done)\s.*")


class Item:
    """One expected element of a transcript: a line (exact, or a regex), "..." (any number of
    lines), a group of lines in any order, or lines whose characters may be mixed. A line may be
    optional, typed by the reader with no prompt before it, or have keys pressed as it starts."""

    def __init__(self, kind, lines, text="", rx=None, members=None):
        self.kind = kind            # line, elide, group, mixed
        self.lines = lines          # the lesson's line numbers
        self.text = text
        self.rx = rx
        self.members = members or []
        self.optional = False
        self.typed = False
        self.output = False         # starts with a prompt, but is printed, never typed
        self.keys = None

    def fits(self, actual):
        a = actual.rstrip()
        if self.rx is not None:
            return self.rx.fullmatch(a) is not None
        if a == self.text.rstrip():
            return True
        # a typed line shows after whatever prompt the terminal had up ("$ ", "% ", "> ", none)
        return self.typed and bool(self.text.strip()) and a.endswith(self.text.strip())

    def shown(self):
        if self.kind == "group":
            return " / ".join(m.text for m in self.members) + "   (in any order)"
        if self.kind == "mixed":
            return "\\n".join(self.text.split("\n")) + "   (characters in any order)"
        return self.text


class Expect:
    """What a block says comes back: its items in order, lines that may come anywhere, lines of
    the output to leave out, and whether more output may come before or after it."""

    def __init__(self, items, anywhere=(), ignore=(), before=False, more=False):
        self.items = items
        self.anywhere = list(anywhere)
        self.ignore = list(ignore)
        self.before, self.more = before, more


RULE = re.compile(r"^\s*lines?\s+(\d+)(?:\s*-\s*(\d+))?\s+(unordered|mixed|optional|anywhere|typed|output)\s*$")
REGEX_RULE = re.compile(r"^\s*lines?\s+(\d+)(?:\s*-\s*(\d+))?\s+~ (.*)$")
KEYS_RULE = re.compile(r"^\s*line\s+(\d+)\s+keys\s+(\S.*?)\s*$")
VARY = re.compile(r'''^\s*vary\s+("(?:[^"\\]|\\.)*"|'[^']*'|\S+)\s+(\S.*?)\s*$''')
IGNORE = re.compile(r"^\s*ignore (.*)$")
RULES_HELP = ("rules: `lines N-M unordered|mixed|optional|anywhere|typed|output`, `line N ~ REGEX`, "
              "`line N keys KEYS`, `vary TEXT KIND`, `ignore REGEX|job-reports`")


def session_items(note, block, before=None, more=None):
    """The Expect of a session or file block, its rules applied. Raises AnnotationError."""
    lines = [l.expandtabs(8) for l in block.lines]
    if note.kind == "file":
        lines = [unarrow(l) for l in lines]
    groups, regexes, varies, flags, keys, ignore = {}, {}, [], {}, {}, []

    def span(m, number):
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        if not 1 <= a <= b <= len(lines):
            raise AnnotationError(f"line {number}: lines {a}-{b}: the block has {len(lines)} lines")
        return a, b

    for number, text in note.body:
        if not text.strip():
            continue
        m = REGEX_RULE.match(text)
        if m:
            a, b = span(m, number)
            try:
                rx = re.compile(m.group(3))
            except re.error as e:
                raise AnnotationError(f"line {number}: bad regex: {e}")
            for k in range(a, b + 1):
                regexes[k - 1] = rx
            continue
        m = RULE.match(text)
        if m:
            a, b = span(m, number)
            what = m.group(3)
            if what in ("unordered", "mixed"):
                if a == b and what == "unordered":
                    raise AnnotationError(f"line {number}: one line cannot be in any order")
                for k in range(a - 1, b):
                    if k in groups:
                        raise AnnotationError(f"line {number}: line {k + 1} is in two groups")
                groups.update({k: (what, a - 1, b - 1) for k in range(a - 1, b)})
            else:
                for k in range(a - 1, b):
                    flags.setdefault(k, set()).add(what)
            continue
        m = KEYS_RULE.match(text)
        if m:
            k = int(m.group(1))
            if not 1 <= k <= len(lines):
                raise AnnotationError(f"line {number}: line {k}: the block has {len(lines)} lines")
            keys[k - 1] = m.group(2)
            continue
        m = VARY.match(text)
        if m:
            what = m.group(1)
            if what[:1] in "\"'":
                what = what[1:-1]
            kind = m.group(2)
            if kind.startswith("/") and kind.endswith("/") and len(kind) > 1:
                rx = kind[1:-1]
            elif kind in KIND_RX:
                rx = KIND_RX[kind]
            else:
                raise AnnotationError(f"line {number}: vary takes one of {', '.join(KIND_RX)} or /regex/")
            if not any(what in l for l in lines):
                raise AnnotationError(f"line {number}: vary {what!r}: the block never shows it")
            varies.append((what, rx))
            continue
        m = IGNORE.match(text)
        if m:
            what = m.group(1).strip()
            if what == "job-reports":
                ignore.append(JOB_REPORTS)
            else:
                if what.startswith("/") and what.endswith("/") and len(what) > 1:
                    what = what[1:-1]
                try:
                    ignore.append(re.compile(what))
                except re.error as e:
                    raise AnnotationError(f"line {number}: bad regex: {e}")
            continue
        raise AnnotationError(f"line {number}: cannot read the rule {text.strip()!r}; " + RULES_HELP)
    varies.sort(key=lambda v: -len(v[0]))
    for k in set(flags) | set(keys):
        if k in groups:
            raise AnnotationError(f"line {k + 1} is in an unordered or mixed group: it cannot also be "
                                  + " or ".join(sorted(flags.get(k, set()) | ({"keys"} if k in keys else set()))))

    def line_item(k):
        text = lines[k]
        it = Item("line", [block.line_no(k)], text)
        if k in regexes:
            it.rx = regexes[k]
        else:
            hits = [(w, rx) for w, rx in varies if w in text]
            if hits:
                pattern = "|".join(re.escape(w) for w, _ in hits)
                parts, pos = [], 0
                for m in re.finditer(pattern, text):
                    parts.append(re.escape(text[pos:m.start()]))
                    parts.append("(?:" + dict(hits)[m.group(0)] + ")")
                    pos = m.end()
                parts.append(re.escape(text[pos:].rstrip()))
                it.rx = re.compile("".join(parts))
        f = flags.get(k, set())
        it.optional = "optional" in f
        it.typed = "typed" in f
        it.output = "output" in f
        it.keys = keys.get(k)
        return it

    first = next((k for k, l in enumerate(lines) if l.strip()), len(lines))
    last = max((k for k, l in enumerate(lines) if l.strip()), default=-1)
    for k in list(flags) + list(keys):
        if k < first or k > last:
            first, last = min(first, k), max(last, k)       # a rule on a blank line keeps it
    items, anywhere, k = [], [], first
    while k <= last:
        if k in groups:
            kind, a, b = groups[k]
            if kind == "unordered":
                items.append(Item("group", [block.line_no(x) for x in range(a, b + 1)],
                                  members=[line_item(x) for x in range(a, b + 1)]))
            else:
                items.append(Item("mixed", [block.line_no(x) for x in range(a, b + 1)],
                                  "\n".join(lines[a:b + 1])))
            k = b + 1
            continue
        if lines[k].strip() == "..." and k not in flags and k not in keys:
            items.append(Item("elide", [block.line_no(k)], "..."))
        elif "anywhere" in flags.get(k, set()):
            anywhere.append(line_item(k))
        else:
            items.append(line_item(k))
        k += 1
    if "trimmed" in note.flags:     # lines picked from the output, in order: anything between them
        spaced = []
        for it in items:
            if spaced and spaced[-1].kind != "elide" and it.kind != "elide":
                spaced.append(Item("elide", [], "..."))
            spaced.append(it)
        items = spaced
        before = more = True
    return Expect(items, anywhere, ignore,
                  before="before" in note.flags if before is None else before,
                  more="more" in note.flags if more is None else more)


class Match:
    def __init__(self, ok, item, actual, lines, anywhere=False):
        self.ok = ok
        self.anywhere = anywhere    # item is a line that may come anywhere, and came nowhere
        self.item = item            # the first Item that could not be matched, or None (the end)
        self.actual = actual        # index in lines of the line it was tried against
        self.lines = lines          # the output as compared: ignored lines left out


def match(expect, actual, more=None, before=None, prefix=False):
    """Do the expected items describe the lines actual: all of them, or with more a beginning of
    them, with before an end of them? A list of Items is an Expect with nothing else. prefix: a
    beginning of what is expected, for finding where the reader types next."""
    if not isinstance(expect, Expect):
        expect = Expect(list(expect))
    more = expect.more if more is None else more
    before = expect.before if before is None else before
    lines = [a for a in actual if not any(rx.fullmatch(a.rstrip()) for rx in expect.ignore)]
    for it in expect.anywhere:
        k = next((k for k, a in enumerate(lines) if it.fits(a)), None)
        if k is not None:
            lines = lines[:k] + lines[k + 1:]
        elif not it.optional and not prefix:
            return Match(False, it, len(lines), lines, anywhere=True)
    seq = list(expect.items)
    if before:
        seq.insert(0, Item("elide", [], "..."))
    if more:
        seq.append(Item("elide", [], "..."))
    memo = {}
    best = [(-1, 0)]
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 4 * (len(seq) + len(lines)) + 1000))

    def go(i, j):
        key = (i, j)
        if key in memo:
            return memo[key]
        if i > best[0][0] or (i == best[0][0] and j > best[0][1]):
            best[0] = (i, j)
        r = False
        if i == len(seq):
            r = j == len(lines)
        else:
            it = seq[i]
            if it.kind == "elide":
                for k in range(j, len(lines) + 1):       # a loop, not any(): no C recursion
                    if go(i + 1, k):
                        r = True
                        break
            elif it.kind == "line":
                r = j < len(lines) and it.fits(lines[j]) and go(i + 1, j + 1)
                if not r and it.optional:
                    r = go(i + 1, j)
            elif it.kind == "group":
                g = len(it.members)
                r = j + g <= len(lines) and fits_any_order(it.members, lines[j:j + g]) and go(i + 1, j + g)
            else:                                        # mixed: the same characters, on any number of lines
                want = sorted("".join(x.rstrip() for x in it.text.split("\n")))
                got = ""
                for k in range(j + 1, len(lines) + 1):
                    got += lines[k - 1].rstrip()
                    if len(got) > len(want):
                        break
                    if len(got) == len(want) and sorted(got) == want and go(i + 1, k):
                        r = True
                        break
        memo[key] = r
        return r

    ok = go(0, 0)
    bi, bj = best[0]
    item = seq[bi] if 0 <= bi < len(seq) else None
    if item is not None and item.kind == "elide" and not item.lines:
        item = None                 # an implied "..." (before, more) cannot be the culprit
    return Match(ok, item, bj, lines)


def fits_any_order(members, actual):
    left = list(actual)
    for m in members:
        k = next((k for k, a in enumerate(left) if m.fits(a)), None)
        if k is None:
            return False
        left.pop(k)
    return True


def mismatch(doc, m, what, block):
    """The message for a transcript that does not match: what the lesson says, what came back."""
    actual = m.lines
    if m.item is None:
        number = block.end - 1
    else:
        number = m.item.lines[0] if m.item.lines else block.start
    got = actual[m.actual] if m.actual < len(actual) else "(nothing more)"
    if m.item is None:
        head = f"{what}: the lesson's transcript ends here, but the project printed more"
    else:
        head = f"{what}: the lesson shows    {m.item.shown()!r}" + (" (anywhere)" if m.anywhere else "")
    out = [head, f"    the project printed {got!r}" + (f" (output line {m.actual + 1})" if m.actual < len(actual) else "")]
    lo, hi = max(0, m.actual - 3), min(len(actual), m.actual + 4)
    if actual:
        out.append("    output around it:")
        for k in range(lo, hi):
            out.append(f"    {'>' if k == m.actual else ' '}{k + 1:4} | {actual[k]}")
    return Problem(doc.path, number, "\n".join(out))


# ---------------------------------------------------------------- the reader's terminal

# The shell's prompts carry invisible markers (an OSC escape no screen shows): the primary one the
# last exit status and the directory, so the verifier knows when the shell itself, not a program
# it runs, is waiting, and where; the continuation one that a command goes on over another line.
# ./learn run and bench, replayed, mark the moment the system starts (after its build).
MARK = "\x1b]7779;"
HOST_PS1 = MARK + "rc=$?;cwd=$PWD\x07$ "
HOST_PS2 = MARK + "more\x07"
STARTED = MARK + "started\x07"
HOST_PROMPT = re.compile(r"\x1b\]7779;rc=(\d+);cwd=([^\x07]*)\x07\$ $")
HOST_INFO = re.compile(r"\x1b\]7779;rc=(\d+);cwd=([^\x07]*)\x07")
# bash's time keyword in zsh's one-line shape, as macOS readers see it (zsh puts the command first)
TIMEFORMAT = "  %2Us user %2Ss system %P%% cpu %3R total"


class Terminal:
    """A bash on a pseudo-terminal: the reader's terminal for one lesson, without job control (so
    every program it starts is in its process group, and nothing reports jobs)."""

    def __init__(self, cwd, env, prompts, quiet, settle):
        from harness.session import Session
        bash = shutil.which("bash", path=env.get("PATH"))
        argv = [bash, "--noediting", "--norc", "--noprofile", "-i"] if bash else ["sh", "-i"]
        self.s = Session(argv, name="terminal", cwd=cwd, env=env, pty=True)
        self.prompts = ["$ "] + [p for p in prompts if p != "$ "]
        self.quiet, self.settle = quiet, settle
        self.last = time.monotonic()
        if not self.wait_host(15):
            raise core.Fail("the terminal's shell never showed its prompt:\n" + self.raw()[-500:])
        since = len(self.raw())
        self.type("set +m")         # -i turns job control on whatever the arguments say
        if not self.wait_host(15, since):
            raise core.Fail("the terminal's shell does not take commands:\n" + self.raw()[-500:])

    @property
    def dead(self):
        return self.s.eof and self.s.proc.poll() is not None

    def raw(self):
        while self.s._pump(0):
            self.last = time.monotonic()
        return self.s.output

    def pump(self, seconds):
        if self.s._pump(seconds):
            self.last = time.monotonic()

    def at_host(self):
        return bool(HOST_PROMPT.search(self.raw()))

    def continuing(self):
        """The shell waits for the rest of a command begun on an earlier line."""
        return self.raw().endswith(HOST_PS2)

    def last_rc(self):
        got = HOST_INFO.findall(self.raw())
        return int(got[-1][0]) if got else None

    def cwd(self):
        got = HOST_INFO.findall(self.raw())
        return got[-1][1] if got else None

    def wait_host(self, seconds, since=0):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.at_host() and len(self.raw()) > since:
                return True
            if self.dead:
                return False
            self.pump(0.05)
        return self.at_host()

    def line_start(self):
        """Where the line the cursor is on begins: the shell's own prompt starts a line of its own
        even after a program that left the cursor mid-line (db> $ ), as a reader sees it."""
        raw = self.raw()
        if self.at_host():
            return raw.rfind(MARK + "rc=")
        return raw.rfind("\n") + 1

    def partial(self):
        raw = self.raw()
        return screen_lines(raw[self.line_start():])[-1]

    def prompt_shown(self, partial):
        return any(partial.endswith(p) for p in self.prompts) or self.continuing()

    def send(self, data):
        try:
            self.s.send(data)
        except OSError:             # the shell is gone (EIO): the caller finds the terminal dead
            self.s.eof = True

    def type(self, text):
        self.send(text + "\r")

    def keys(self, data):
        self.send(data)

    def wait(self, since, want_prompt, timeout, settle=None, until=None):
        """Wait until the terminal is ready for the next line: it printed something after `since`,
        shows a prompt, and has been quiet for a moment ("prompt"); or, when no prompt is wanted,
        has printed something (or started the system) and been quiet for `settle` seconds
        ("quiet"); or until() says so ("until"); or timeout ("timeout")."""
        settle = self.settle if settle is None else settle
        start = time.monotonic()
        while True:
            self.pump(0.05)
            now = time.monotonic()
            raw = self.s.output
            grown = len(raw) > since
            if until is not None and until():
                return "until"
            if grown and self.prompt_shown(self.partial()) and now - self.last >= self.quiet:
                return "prompt"
            # "host": a command typed at the shell, done when the shell is back, unless what it
            # started (./learn run) is a system that may never show a prompt
            want = want_prompt if want_prompt != "host" else STARTED not in raw[since:]
            if not want and raw[since:].strip() and now - self.last >= settle:
                return "quiet"
            if now - start > timeout:
                return "timeout"
            if self.dead:
                return "closed"

    def quiet_for(self, seconds, timeout):
        """Wait until nothing has been printed for `seconds` (at most timeout)."""
        end = time.monotonic() + timeout
        self.pump(0)
        while time.monotonic() - self.last < seconds and time.monotonic() < end:
            self.pump(0.05)

    def screen(self, start):
        """The lines shown since raw offset start, leading blank lines dropped; the last one is
        the line the cursor is on."""
        lines = screen_lines(self.raw()[start:])
        k = 0
        while k < len(lines) - 1 and not lines[k].strip():
            k += 1
        return lines[k:]

    def close(self):
        self.s.close()


KEYS = {"enter": "\r", "tab": "\t", "esc": "\x1b", "space": " ", "backspace": "\x7f"}
KEY_WORD = re.compile(r'"([^"]*)"|\'([^\']*)\'|(\S+)')


def parse_keys(spec):
    """'ctrl-a c' -> '\\x01c'; 'ctrl-p' -> '\\x10'; enter, tab, esc, space, backspace; "quoted
    text" as it is; other words as typed, with a space between two words in a row."""
    out, text_before = [], False
    for m in KEY_WORD.finditer(spec):
        if m.group(3) is None:
            out.append(m.group(1) if m.group(1) is not None else m.group(2))
            text_before = False
            continue
        word = m.group(3)
        k = re.fullmatch(r"ctrl-([a-z@\[\\\]^_])", word.lower())
        if k:
            out.append(chr(ord(k.group(1).upper()) & 0x1f))
            text_before = False
        elif word.lower() in KEYS:
            out.append(KEYS[word.lower()])
            text_before = False
        else:
            out.append((" " if text_before else "") + word)
            text_before = True
    return "".join(out)


# ---------------------------------------------------------------- patches

def patch_ops(note, block=None):
    """[(sign, text)] of a patch's body: "-" a line to find and delete, "+" a line to add, " " a
    line to find and keep; @block stands for the lines of the block after the annotation."""
    ops = []
    for number, text in note.body:
        if text.strip() == "@block":
            if block is None:
                raise AnnotationError(f"line {number}: @block, but no block follows")
            ops.append(("@", block.lines))
            continue
        if not text:
            ops.append((" ", ""))
            continue
        sign = text[0]
        if sign not in "-+ ":
            raise AnnotationError(f"line {number}: a patch line starts with -, + or a space (or is @block): {text!r}")
        ops.append((sign, text[1:]))
    return ops


def apply_patch(text, ops, append=False):
    """text with the patch applied, or raise AnnotationError saying why it does not apply. A
    text of None is a file the patch creates: only + lines and @block."""
    if text is None:
        if any(s in "- " for s, _ in ops):
            raise AnnotationError("a patch that creates a file has only + lines (and @block)")
        text, append = "", True
    lines = text.split("\n")
    trailing = lines and lines[-1] == ""
    if trailing:
        lines.pop()
    old = [t for s, t in ops if s in "- "]
    if append:
        if old:
            raise AnnotationError("an append patch has only + lines (and @block)")
        k = len(lines)
        while k > 0 and not lines[k - 1].strip():
            k -= 1
        start, count = k, 0
    else:
        if not any(t.strip() for t in old):
            raise AnnotationError("a patch needs lines to find (- or context lines), or the append flag")
        want = [norm(t) for t in old]
        hits = [k for k in range(len(lines) - len(want) + 1)
                if all(norm(lines[k + m]) == want[m] for m in range(len(want)))]
        if not hits:
            first = next(t for t in old if t.strip())
            raise AnnotationError(f"the lines to change are not in the file (looking for {first.strip()!r}"
                                  + (" and what follows it)" if len(old) > 1 else ")"))
        if len(hits) > 1:
            raise AnnotationError(f"the lines to change are in the file {len(hits)} times "
                                  f"(lines {', '.join(str(h + 1) for h in hits[:5])}): add context lines")
        start, count = hits[0], len(want)
    new, m, indent = [], start, ""
    for sign, t in ops:
        if sign == " ":
            new.append(lines[m])
            indent = re.match(r"\s*", lines[m]).group(0)
            m += 1
        elif sign == "-":
            indent = re.match(r"\s*", lines[m]).group(0)
            m += 1
        elif sign == "+":
            new.append(t)
        else:
            body = list(t)
            own = min((len(x) - len(x.lstrip()) for x in body if x.strip()), default=0)
            new.extend((indent + x) if x.strip() and own == 0 else x for x in body)
    out = lines[:start] + new + lines[start + count:]
    return "\n".join(out) + ("\n" if trailing or append else "")


def apply_edit(text, old, new):
    """text with the one place that holds old changed to new (part of a line, or across lines).
    Raises AnnotationError when old is not there, or is there more than once."""
    if not old:
        raise AnnotationError("old= is empty")
    n = text.count(old)
    if n == 0:
        raise AnnotationError(f"{old!r} is not in the file")
    if n > 1:
        raise AnnotationError(f"{old!r} is in the file {n} times: make old= longer")
    return text.replace(old, new, 1)


COMMENTED = re.compile(r"^\s*(?://|#|;|--)\s?(.*?)\s*$|^\s*/\*\s?(.*?)\s*\*/\s*$")


def added_lines(ops):
    """[(line, what of it the page must show)] for a patch's + lines (not @block): the whole
    line; where it replaces a - line, only the words that changed ("0x88000000L"); where it is
    that line commented out, the line."""
    out, minus = [], []
    for s, t in ops:
        if s == "-":
            minus.append(t)
            continue
        if s == "+" and t.strip():
            old = minus.pop(0) if minus else None
            c = COMMENTED.match(t)
            if old is not None and c and norm(c.group(1) if c.group(1) is not None else c.group(2)) == norm(old):
                out.append((t, old))
            else:
                out.append((t, changed_words(old, t) if old is not None else t))
            continue
        minus = []
    return out


def changed_tokens(old, new):
    """The part of new that differs from old, widened to whole runs of non-blanks: "<= 0" for
    "x < 0" -> "x <= 0" gives "<=" ... "0" as the page writes it."""
    a, b = old, new
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    lo, hi = i, len(b) - j
    while lo > 0 and not b[lo - 1].isspace():
        lo -= 1
    while hi < len(b) and not b[hi].isspace():
        hi += 1
    return b[lo:hi] if hi > lo else b


def changed_words(old, new):
    """The part of new that differs from old, widened to whole words."""
    a, b = old.strip(), new.strip()
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    lo, hi = i, len(b) - j
    while lo > 0 and re.match(r"\w", b[lo - 1]):
        lo -= 1
    while hi < len(b) and re.match(r"\w", b[hi]):
        hi += 1
    part = b[lo:hi]
    return part if re.search(r"\w", part) else b        # a changed operator alone proves little


# ---------------------------------------------------------------- the static checks

FORBIDDEN = [
    (re.compile(r"\bstubs?\b(?!\s+resolvers?)", re.I), "talks about stubs"),
    (re.compile(r"\bexercises?\b", re.I), "calls something an exercise"),
    (re.compile(r"\bworkspaces?\b", re.I), "mentions a workspace"),
    (re.compile(r"--ref\b"), "mentions --ref"),
    (re.compile(r"\breference (code|solution|implementation|track)\b", re.I), "mentions the reference code"),
    (re.compile(r"\b(lesson|unit|internal|hidden|course)('s)? tests?\b", re.I), "talks about the tests"),
    (re.compile(r"\b(run|runs|running|ran) (the |its |every |all )?tests\b", re.I), "talks about the tests"),
    (re.compile(r"\btest (suite|harness|runner)s?\b", re.I), "talks about the tests"),
    (re.compile(r"\b(selftest|check-skeleton|check-timeline)\b"), "names an internal check"),
    (re.compile(r"\b(PASS|PASSED|FAIL|FAILED)\b"), "talks about tests passing or failing"),
]
LEARNER_COMMANDS = {"run", "bench", "files", "serve", "export", "map"}
SECTIONS = ["Where this fits", "The idea", "Run it", "How it works", "Break it"]
LAST_SECTIONS = {"Go deeper", "Read more in OSTEP"}
OPTIONAL_SECTIONS = {"Decide the boundary"}
CALL = re.compile(r"^([A-Za-z_]\w*)\(([^;{}`]*)\)$")
FILE = re.compile(r"^((?:[\w.-]+/)*[\w.-]+\.(?:c|h|S|ld|pl|py|sh))$")
FILE_NAME = re.compile(r"^((?:[\w.-]+/)*[\w.-]+\.(?:c|h|S|ld|pl|py|sh)):([A-Za-z_]\w*)$")
NOT_NAMES = {"if", "for", "while", "switch", "return", "sizeof", "defined", "do", "else", "case"}
NAME_LIST = re.compile(r"[^\s(]+\([^)]*\)|\S+")      # dup2(old, new) is one name
READER_COPY = re.compile(r"^build/at/([\w-]+)/(\d\d\.\d\d|finished)/(.+)$")


class Verifier:
    """One run of ./learn verify (or of check's static part): the caches, the options."""

    def __init__(self, fresh=False, keep=False, allow_missing=False, out=None, timeout=30.0):
        self.fresh, self.keep, self.allow_missing = fresh, keep, allow_missing
        self.out = out or sys.stdout
        self.timeout = timeout
        self._projects = {}
        self._indexes = {}
        self._lock = threading.Lock()
        self._index_locks = {}
        self._tools = {}

    # ---- the project, read

    def project(self, track):
        with self._lock:
            if track.root not in self._projects:
                self._projects[track.root] = timeline.Project(track)
            return self._projects[track.root]

    def index(self, track, at):
        key = (track.root, at)
        with self._lock:
            if key in self._indexes:
                return self._indexes[key]
            lock = self._index_locks.setdefault(key, threading.Lock())
        with lock:
            with self._lock:
                if key in self._indexes:
                    return self._indexes[key]
            idx = Index(self.project(track), at)
            with self._lock:
                self._indexes[key] = idx
            return idx

    def lesson_ids(self, track):
        return {l.id for l in track.lessons}

    def known_at(self, track, at):
        return at is None or at in self.lesson_ids(track) | self.project(track).lesson_ids()

    def comes_with(self, track, at, test):
        """The first lesson after `at` on its path whose project passes test(index), or None."""
        if at is None:
            return None
        ids = sorted(self.lesson_ids(track) | self.project(track).lesson_ids(), key=core.lesson_key)
        ids = [i for i in ids if core.lesson_key(i) > core.lesson_key(at) and timeline.reached(track, at, i)]
        for lid in ids:
            if test(self.index(track, lid)):
                return lid
        return None

    # ---- the static checks

    def static(self, track, lesson, doc=None, figures=True):
        """Problems (errors and warnings) the lesson has that need no build. figures=False leaves
        the figure checks to ./learn check's own."""
        doc = doc or Doc(lesson.doc, lesson.id)
        out = list(doc.errors)
        out += self.check_structure(doc, lesson)
        out += self.check_words(doc)
        out += self.check_learn_commands(track, doc)
        if figures:
            out += self.check_figures(doc, lesson)
        out += self.check_blocks(track, doc, lesson)
        out += self.check_patches(track, doc, lesson)
        out += self.check_setups(track, doc, lesson)
        out += self.check_mentions(track, doc, lesson)
        out += self.check_facts(track, doc, lesson)
        return out

    def check_structure(self, doc, lesson):
        out = []
        p = doc.path
        for key in ("id", "title", "labels"):
            if key not in doc.meta:
                out.append(Problem(p, 1, f"front matter has no `{key}:` line"))
        if doc.meta.get("id") and doc.meta["id"] != lesson.id:
            out.append(Problem(p, 2, f"front matter says id {doc.meta['id']}, the file name {lesson.id}"))
        heads = [(n, HEADING.match(t)) for n, t in doc.prose if n > doc.meta_end and HEADING.match(t)]
        h1 = [(n, m.group(2)) for n, m in heads if len(m.group(1)) == 1]
        want = f"{lesson.id} {doc.meta.get('title', lesson.title)}"
        if not h1:
            out.append(Problem(p, doc.meta_end + 1, f"no `# {want}` heading"))
        elif h1[0][1] != want:
            out.append(Problem(p, h1[0][0], f"the heading should be `# {want}`"))
        h2 = [(n, m.group(2)) for n, m in heads if len(m.group(1)) == 2]
        names = [t for _, t in h2]
        core_names = [t for t in names if t not in OPTIONAL_SECTIONS]
        if core_names[:len(SECTIONS)] != SECTIONS or len(core_names) != len(SECTIONS) + 1 \
                or core_names[-1] not in LAST_SECTIONS:
            n = h2[0][0] if h2 else doc.meta_end + 1
            out.append(Problem(p, n, "sections should be " + ", ".join(SECTIONS)
                               + " (Decide the boundary may sit after How it works), then Go deeper or "
                               "Read more in OSTEP; this lesson has " + (", ".join(names) or "none")))
        for n, t in h2:
            if t in OPTIONAL_SECTIONS and "How it works" in names and n < h2[names.index("How it works")][0]:
                out.append(Problem(p, n, f"`{t}` comes after How it works"))
        return out

    def check_words(self, doc):
        out = []
        for text, offsets in doc.paragraphs():
            masked = SPAN.sub(lambda m: " " * len(m.group(0)), text)
            masked = re.sub(r"\]\([^)]*\)", "]", masked)          # link targets are not prose
            for rx, what in FORBIDDEN:
                for m in rx.finditer(masked):
                    out.append(Problem(doc.path, line_at(offsets, m.start()),
                                       f"learner-facing text {what}: {text[max(0, m.start() - 20):m.end() + 20]!r}"))
        return out

    def check_learn_commands(self, track, doc):
        """Every ./learn command a lesson shows is one learners use, on a lesson that exists."""
        from harness import cli
        tracks = {t.id: t for t in core.discover_tracks()}
        tracks.setdefault(track.id, track)
        out = []
        places = [(n, t) for n, t in doc.prose]
        for b in doc.blocks:
            places += [(b.line_no(k), l) for k, l in enumerate(b.lines)]
        for n, text in places:
            for m in LEARN_CMD.finditer(text):
                words = m.group(1).split()
                if not words:
                    continue
                if words[0] not in LEARNER_COMMANDS:
                    out.append(Problem(doc.path, n, f"`./learn {words[0]}` is not a command learners use"))
                    continue
                if words[0] not in ("run", "bench", "files") or len(words) == 1:
                    continue                # the command named, not a command line
                args = [w.strip("`'\".,;:)") for w in words[1:]]
                try:
                    tid, at, _fresh, _extra = cli.run_options(args, "usage", loose=words[0] == "bench")
                except SystemExit:
                    out.append(Problem(doc.path, n, f"`./learn {' '.join(words)}` is not a valid command"))
                    continue
                t = tracks.get(tid)
                if t is None:
                    out.append(Problem(doc.path, n, f"`./learn {words[0]} {tid}`: there is no track {tid}"))
                    continue
                if at is not None and not self.known_at(t, at):
                    out.append(Problem(doc.path, n, f"`./learn {words[0]} {tid} --at {at}`: {tid} has no lesson {at}"))
                elif at is not None and words[0] != "files" and not cli._has_code(t, self.project(t), at):
                    out.append(Problem(doc.path, n, f"`./learn {words[0]} {tid} --at {at}`: {tid} has no code to run yet at {at}"))
        return out

    def check_figures(self, doc, lesson):
        from harness.web import art
        out = [Problem(doc.path, n, what) for n, what in art.figure_problems(doc.path)]
        folder = os.path.join(os.path.dirname(doc.path), "figures")
        used = set()
        for _, t in doc.prose:
            m = FIGURE.match(t)
            if m:
                used.add(os.path.basename(m.group(2)))
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder)):
                if name.startswith(lesson.id + "-") and name not in used:
                    out.append(Problem(doc.path, 1, f"figures/{name} is not used by this lesson", warning=True))
        return out

    def check_blocks(self, track, doc, lesson):
        out = []
        for b in doc.blocks:
            kinds = [n.kind for n in b.notes]
            patches = [n for n in b.notes if n.kind == "patch"]
            roles = [k for k in kinds if k in BLOCK_KINDS]
            if len(roles) > 1 or (roles and patches):
                out.append(Problem(doc.path, b.start, "a block takes one of session, file, quote, skip or a patch's @block, "
                                                      "not " + " and ".join(kinds)))
                continue
            if patches:
                b.role = "typed"
                continue
            if roles == ["skip"]:
                note = b.notes[0]
                b.role = "skip"
                if not note.opts.get("reason", "").strip():
                    out.append(Problem(doc.path, note.line, 'skip needs reason="why this block is not checked"'))
                continue
            if roles == ["session"]:
                b.role = "session"
                note = b.notes[0]
                try:
                    note.expect = session_items(note, b)
                except AnnotationError as e:
                    out.append(Problem(doc.path, note.line, f"session: {e}"))
                at = note.at(lesson.id)
                if not self.known_at(track, at):
                    out.append(Problem(doc.path, note.line, f"session: {track.id} has no lesson {at}"))
                for name in ("hangs", "timeout", "wait", "exit", "terminal"):
                    v = note.opts.get(name)
                    if v is not None and not re.fullmatch(r"-?\d+(\.\d+)?", v):
                        out.append(Problem(doc.path, note.line, f"session: {name}= takes a number"))
                out += self.check_cwd(doc, note)
                continue
            if roles == ["file"]:
                b.role = "file"
                note = b.notes[0]
                path = note.opts.get("path", "")
                if not path or os.path.isabs(path) or ".." in path.split("/"):
                    out.append(Problem(doc.path, note.line, "file needs path= inside the project"))
                try:
                    note.expect = session_items(note, b, before=True, more=True)
                except AnnotationError as e:
                    out.append(Problem(doc.path, note.line, f"file: {e}"))
                if note.expect is not None and any(it.keys or it.typed for it in note.expect.items):
                    out.append(Problem(doc.path, note.line, "file: a file is read, not typed: no keys or typed lines"))
                if not self.known_at(track, note.at(lesson.id)):
                    out.append(Problem(doc.path, note.line, f"file: {track.id} has no lesson {note.at(lesson.id)}"))
                continue
            at = lesson.id
            if roles == ["quote"]:
                at = b.notes[0].at(lesson.id)
                if not self.known_at(track, at):
                    out.append(Problem(doc.path, b.notes[0].line, f"quote: {track.id} has no lesson {at}"))
                    continue
            nonblank = [l for l in b.lines if l.strip()]
            if not roles and nonblank and all(re.match(r"^(\$ )?\./learn\s", l.strip()) for l in nonblank):
                b.role = "command"          # ./learn lines for the reader to type: checked above
                continue
            b.role = "quote"
            idx = self.index(track, at)
            missing = [(k, l) for k, l in enumerate(b.lines) if not idx.has_line(l)]
            if not missing:
                continue
            first = next((l for l in b.lines if l.strip()), "")
            prompts = ["$ "] + list(getattr(track.module, "VERIFY_PROMPTS", []))
            if not roles and any(first.startswith(p) for p in prompts):
                out.append(Problem(doc.path, b.start, "this block looks like a terminal transcript: annotate it "
                                                      "<!-- verify: session ... --> (or skip it with a reason)"))
                continue
            where = "the finished project" if at is None else f"the project at {at}"
            for k, l in missing[:6]:
                later = self.comes_with(track, at, lambda i, l=l: i.has_line(l))
                why = f"; it comes with {later}" if later else "; it is in no lesson's project"
                out.append(Problem(doc.path, b.line_no(k), f"quoted code not in {where}{why}: {l.strip()!r}"))
            if len(missing) > 6:
                out.append(Problem(doc.path, b.start, f"... and {len(missing) - 6} more lines of this block"))
            if len(missing) == len([l for l in b.lines if norm(l) and norm(l) not in TRIVIAL]) and not roles:
                out.append(Problem(doc.path, b.start, "none of this block is code from the project: if it is "
                                                      "something else, annotate it (session, a patch's @block, or "
                                                      'skip reason="...")'))
        return out

    def check_cwd(self, doc, note):
        cwd = note.opts.get("cwd")
        if cwd is not None and cwd != "project" and (os.path.isabs(cwd) or ".." in cwd.split("/")):
            return [Problem(doc.path, note.line, f"{note.kind}: cwd= takes `project` or a path inside the checkout")]
        return []

    def check_setups(self, track, doc, lesson):
        """Every setup step reads, and every block it replays exists and can be replayed."""
        out = []
        for note in doc.notes:
            if note.kind != "setup":
                continue
            out += self.check_cwd(doc, note)
            if not self.known_at(track, note.at(lesson.id)):
                out.append(Problem(doc.path, note.line, f"setup: {track.id} has no lesson {note.at(lesson.id)}"))
            steps = [(n, t) for n, t in note.body if t.strip()]
            if not steps and "cwd" not in note.opts:
                out.append(Problem(doc.path, note.line, "setup has no steps: `$ command`, `keys KEYS` or "
                                                        "`replay NN.LL BLOCK`, one per line"))
            for number, text in steps:
                m = SETUP_STEP.match(text)
                if not m:
                    out.append(Problem(doc.path, number, f"setup: cannot read the step {text.strip()!r}; steps: "
                                                         "`$ command`, `keys KEYS`, `replay NN.LL BLOCK`"))
                    continue
                if m.group("lesson"):
                    try:
                        other, odoc, block = replay_target(track, m.group("lesson"), m.group("which"))
                    except AnnotationError as e:
                        out.append(Problem(doc.path, number, f"setup: {e}"))
                        continue
                    if other.id == lesson.id and odoc.path == doc.path and block.start > note.line:
                        out.append(Problem(doc.path, number, "setup: replay a block that comes later in this lesson? "
                                                             "the reader has not got there yet"))
                    self.check_blocks(track, odoc, other)
                    if block.role not in ("session", "typed"):
                        out.append(Problem(doc.path, number, f"setup: block at {os.path.basename(odoc.path)}:"
                                                             f"{block.start} is {block.role or 'quoted code'}: only a "
                                                             "session or code the reader types can be replayed"))
        return out

    def check_patches(self, track, doc, lesson):
        """Every patch applies, in order, to the project at its lesson (reverts undoing them), and
        adds only lines the page shows."""
        out, files = [], {}
        visible = {norm(l) for l in doc.visible_text().split("\n")}
        visible_all = norm(doc.visible_text())
        for note in doc.notes:
            if note.kind not in ("patch", "revert"):
                continue
            at = note.at(lesson.id)
            if not self.known_at(track, at):
                out.append(Problem(doc.path, note.line, f"{note.kind}: {track.id} has no lesson {at}"))
                continue
            proj = self.project(track)
            if note.kind == "revert":
                for key in [k for k in files if k[0] == at and note.opts.get("file") in (None, k[1])]:
                    del files[key]
                continue
            rel = note.opts.get("file")
            if not rel:
                out.append(Problem(doc.path, note.line, "patch needs file=path (inside the project)"))
                continue
            if "old" in note.opts or "new" in note.opts:      # a change inside a line: old= new=
                if note.body or "old" not in note.opts or "new" not in note.opts or "create" in note.flags \
                        or "append" in note.flags:
                    out.append(Problem(doc.path, note.line, "patch with old= takes new= too, and no body or flags"))
                    continue
                if rel not in proj.files_at(at) and (at, rel) not in files:
                    out.append(Problem(doc.path, note.line, f"patch: there is no {rel} in the project at {at or 'the end'}"))
                    continue
                text = files.get((at, rel))
                if text is None:
                    text = proj.content(rel, at).decode("utf-8", errors="replace")
                try:
                    files[(at, rel)] = apply_edit(text, note.opts["old"], note.opts["new"])
                except AnnotationError as e:
                    out.append(Problem(doc.path, note.line, f"patch {rel} at {at or 'the end'}: {e}"))
                    continue
                if note.opts["new"].strip():        # the new text, or the part of it that changed
                    shown = [note.opts["new"], changed_tokens(note.opts["old"], note.opts["new"])]
                else:
                    shown = [note.opts["old"]]
                if not any(norm(x) and norm(x) in visible_all for x in shown):
                    out.append(Problem(doc.path, note.line, f"patch changes to {note.opts['new']!r}, which the page "
                                                            "never shows the reader" if note.opts["new"].strip() else
                                                            f"patch deletes {note.opts['old']!r}, which the page never "
                                                            "shows the reader"))
                continue
            create = "create" in note.flags
            there = rel in proj.files_at(at) or (at, rel) in files
            if not there and not create:
                out.append(Problem(doc.path, note.line, f"patch: there is no {rel} in the project at {at or 'the end'}"
                                                        " (the create flag makes a new file)"))
                continue
            if there and create and (at, rel) not in files:
                out.append(Problem(doc.path, note.line, f"patch create: {rel} is in the project at {at or 'the end'} already"))
                continue
            try:
                ops = patch_ops(note, note.block)
                text = files.get((at, rel))
                if text is None and not create:
                    text = proj.content(rel, at).decode("utf-8", errors="replace")
                files[(at, rel)] = apply_patch(text, ops, append="append" in note.flags)
            except AnnotationError as e:
                out.append(Problem(doc.path, note.line, f"patch {rel} at {at or 'the end'}: {e}"))
                continue
            for line, shown in added_lines(ops):
                if norm(line) in TRIVIAL or norm(line) in visible or norm(line) in visible_all:
                    continue
                bare = norm(line).rstrip(";").rstrip()          # shown without its semicolon
                if bare and bare in visible_all:
                    continue
                if norm(shown) and (norm(shown) in visible_all or norm(shown).rstrip(";").rstrip() in visible_all):
                    continue
                out.append(Problem(doc.path, note.line, f"patch adds {line.strip()!r}, which the page never "
                                                        "shows the reader"))
        return out

    def check_mentions(self, track, doc, lesson):
        """`name()`, `file.c` and `file.c:name` in the prose exist at the lesson, or at the lesson
        the sentence names, or as a `mention` annotation declares."""
        declared = {}
        out = []
        for note in doc.notes:
            if note.kind != "mention":
                continue
            names = NAME_LIST.findall(note.opts.get("names", ""))
            if not names:
                out.append(Problem(doc.path, note.line, 'mention needs names="..."'))
            if "outside" in note.flags:
                if not note.opts.get("reason", "").strip():
                    out.append(Problem(doc.path, note.line, 'mention outside needs reason="..."'))
                for name in names:
                    declared[name] = "outside"
            elif "at" in note.opts:
                at = note.at(lesson.id)
                if not self.known_at(track, at):
                    out.append(Problem(doc.path, note.line, f"mention: {track.id} has no lesson {at}"))
                    continue
                for name in names:
                    declared[name] = at
                    if not self.exists(track, at, name):
                        out.append(Problem(doc.path, note.line, f"mention: {name} is not in the project at {at or 'the end'}"))
            else:
                out.append(Problem(doc.path, note.line, "mention takes at=NN.LL or outside"))
        for note in doc.notes:
            if note.kind == "patch" and "create" in note.flags and note.opts.get("file"):
                declared.setdefault(note.opts["file"], "made")
                declared.setdefault(os.path.basename(note.opts["file"]), "made")
        ids = self.lesson_ids(track) | self.project(track).lesson_ids()
        for text, offsets in doc.paragraphs():
            sents = sentences(text)
            for m in SPAN.finditer(text):
                span = m.group(2).strip()
                copy = READER_COPY.match(span)
                kind = mention_kind(span)
                if (kind is None and not copy) or span in declared:
                    continue
                if copy:                    # build/at/<track>/<lesson>/<file>: that file, at that lesson
                    tid, at, rel = copy.group(1), copy.group(2), copy.group(3)
                    at = None if at == "finished" else at
                    if tid != track.id:
                        continue
                    if not self.known_at(track, at):
                        out.append(Problem(doc.path, line_at(offsets, m.start()), f"`{span}`: {tid} has no lesson {at}"))
                    elif rel not in declared and not self.index(track, at).has_file(rel):
                        later = self.comes_with(track, at, lambda i, r=rel: i.has_file(r))
                        out.append(Problem(doc.path, line_at(offsets, m.start()),
                                           f"`{span}`: there is no {rel} in the project at {at or 'the end'}"
                                           + (f"; it comes with {later}" if later else "")))
                    continue
                if self.exists(track, lesson.id, span):
                    continue
                sent = next((text[a:b] for a, b in sents if a <= m.start() < b), text)
                named = [r for r in LESSON_REF.findall(SPAN.sub(" ", sent)) if r in ids and r != lesson.id]
                if any(self.exists(track, r, span) for r in named):
                    continue
                later = self.comes_with(track, lesson.id, lambda i, s=span: exists_in(i, s))
                q = "'" if '"' in span else '"'
                why = (f"; it comes with {later}: say so in the sentence (\"... in {later}\") or annotate "
                       f"<!-- verify: mention names={q}{span}{q} at={later} -->") if later else \
                    (f"; not in any lesson's project: if it is not this project's, annotate "
                     f"<!-- verify: mention names={q}{span}{q} outside reason=\"...\" -->")
                if named:
                    why = f" (nor at {', '.join(named)}, which the sentence names)" + why
                out.append(Problem(doc.path, line_at(offsets, m.start()),
                                   f"`{span}` is not in the project at {lesson.id}{why}"))
        return out

    def exists(self, track, at, span):
        return exists_in(self.index(track, at), span)

    def check_facts(self, track, doc, lesson):
        out = []
        for note in doc.notes:
            if note.kind != "fact":
                continue
            if not note.opts.get("cmd") or "expect" not in note.opts:
                out.append(Problem(doc.path, note.line, "fact needs cmd='...' and expect=..."))
                continue
            at = note.at(lesson.id)
            if not self.known_at(track, at):
                out.append(Problem(doc.path, note.line, f"fact: {track.id} has no lesson {at}"))
            after = following_paragraph(doc, note)
            if norm(note.opts["expect"]) not in norm(after):
                out.append(Problem(doc.path, note.line, f"fact: the text after it does not say {note.opts['expect']!r}"))
        return out


def mention_kind(span):
    if FILE_NAME.match(span):
        return "file:name"
    if FILE.match(span):
        return "file"
    m = CALL.match(span)
    if m and m.group(1) not in NOT_NAMES:
        return "call"
    return None


def exists_in(idx, span):
    m = FILE_NAME.match(span)
    if m:
        rel = idx.file_named(m.group(1))
        return rel is not None and m.group(2) in idx.file_idents.get(rel, ())
    m = FILE.match(span)
    if m:
        return idx.has_file(m.group(1))
    m = CALL.match(span)
    if m:
        return m.group(1) in idx.idents
    return True


def following_paragraph(doc, note):
    """The prose from the annotation to the next blank line (or the end of its paragraph)."""
    end = note.body[-1][0] + 1 if note.body else note.line
    out = []
    for n, t in doc.prose:
        if n <= end:
            continue
        if not t.strip():
            if out:
                break
            continue
        out.append(t)
    return " ".join(out)


# ---------------------------------------------------------------- replaying a lesson

SHIM = '''#!{python}
# ./learn, as ./learn verify replays it: run, bench and files, in this copy of the checkout.
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, {repo!r})
from harness import verify
sys.exit(verify.shim(sys.argv[1:], os.path.dirname(os.path.abspath(__file__))))
'''


def shim(args, top):
    """./learn inside a replay: the real run, bench and files, writing under top/build/, and
    marking (invisibly) the moment the system starts, once it is built."""
    from harness import cli
    if not args or args[0] not in ("run", "bench", "files"):
        print("(./learn verify replays only ./learn run, bench and files)", file=sys.stderr)
        return 2
    cli.SHOWN_FROM = top
    os.environ["LEARN_BUILD_DIR"] = os.path.join(top, "build")

    def started():
        sys.stdout.write(STARTED)
        sys.stdout.flush()
    cli.RUN_HOOK = started
    return cli.main(args)


SETUP_STEP = re.compile(r"^\s*(\$ (?P<cmd>.+)|keys (?P<keys>.+)|replay (?P<lesson>\d\d\.\d\d) (?P<which>.+))\s*$")


def replay_target(track, lesson_id, which):
    """(lesson, Doc, Block) that `replay LESSON WHICH` names: WHICH is the block's number in the
    lesson (1 is its first fenced block) or, quoted, the block's first line. Raises AnnotationError."""
    lesson = next((l for l in track.lessons if l.id == lesson_id and l.doc), None)
    if lesson is None:
        raise AnnotationError(f"replay: {track.id} has no lesson {lesson_id}")
    doc = Doc(lesson.doc, lesson.id)
    which = which.strip()
    if which.isdigit():
        k = int(which)
        if not 1 <= k <= len(doc.blocks):
            raise AnnotationError(f"replay: {lesson_id} has {len(doc.blocks)} blocks, not {k}")
        return lesson, doc, doc.blocks[k - 1]
    if which[:1] in "\"'" and which[-1:] == which[:1]:
        which = which[1:-1]
    hits = [b for b in doc.blocks if next((l for l in b.lines if l.strip()), "").strip() == which.strip()]
    if len(hits) != 1:
        raise AnnotationError(f"replay: {len(hits)} blocks of {lesson_id} start with {which!r}")
    return lesson, doc, hits[0]


class Replay:
    """One lesson, replayed: its terminals, its copy of the checkout, its patches."""

    def __init__(self, v, track, doc, lesson, top, tools):
        self.v, self.track, self.doc, self.lesson, self.top = v, track, doc, lesson, top
        mod = track.module
        self.prompts = list(getattr(mod, "VERIFY_PROMPTS", []))
        self.quit_keys = list(getattr(mod, "VERIFY_QUIT", []))
        self.quiet = float(getattr(mod, "VERIFY_QUIET", 0.2))
        self.settle = float(getattr(mod, "VERIFY_SETTLE", 1.0))
        self.panic = getattr(mod, "VERIFY_PANIC", "panic: ")
        self.terms = {}             # terminal number -> Terminal (a reader may open a second one)
        self.back = {}              # terminal number -> where a cwd= block found it, to go back to
        self.originals = {}         # (at, file) -> its text before the first patch (None: it made it)
        self.problems = []
        self.missing = set()        # tools a session needs= that this machine does not have
        self.transcripts = []
        self.raw = ""               # what the terminals showed, escapes and all
        dirs = []
        for path in tools.values():
            d = os.path.dirname(path) if path else None
            if d and d not in dirs:
                dirs.append(d)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("DB_", "LEARN_", "BASH_FUNC_"))
               and k not in ("PROMPT_COMMAND", "PS1", "PS2", "PS4", "ENV", "BASH_ENV", "CDPATH",
                             "MAKEFLAGS", "MFLAGS", "MAKELEVEL", "SCREEN", "TIMEFORMAT")}
        env.update(PS1=HOST_PS1, PS2=HOST_PS2, TERM="dumb", LC_ALL="C", LANG="C", TIMEFORMAT=TIMEFORMAT,
                   BASH_SILENCE_DEPRECATION_WARNING="1", HISTFILE="/dev/null",
                   LEARN_TRACKS_DIR=core.TRACKS_DIR, LEARN_BUILD_DIR=os.path.join(top, "build"),
                   SCREEN="none", PYTHONDONTWRITEBYTECODE="1",
                   PATH=os.pathsep.join(dirs + [env.get("PATH", "/usr/bin:/bin")]))
        self.env = env

    def fail(self, line, message):
        self.problems.append(Problem(self.doc.path, line, message))

    def project_root(self, at):
        return os.path.join(self.top, "build", "at", self.track.id, at or "finished")

    def ensure_project(self, at):
        from harness import cli
        try:
            cli.project_dir(self.track, at, need_code=False, top=os.path.join(self.top, "build"))
        except SystemExit as e:
            raise core.Fail(str(e))
        return self.project_root(at)

    def build(self, root, line, at=False):
        """Build the reader's copy (unless at= names a lesson with no code to build yet)."""
        import subprocess
        from harness import cli
        if at is not False and not cli._has_code(self.track, self.v.project(self.track), at):
            return True
        argv = self.track.module.prepare(root) if hasattr(self.track.module, "prepare") else None
        if not argv:
            return True
        r = subprocess.run(argv, cwd=root, env=self.env, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            self.fail(line, "the project does not build:\n" + (r.stdout + r.stderr)[-1500:])
            return False
        return True

    # ---- the terminals

    def terminal(self, n=1):
        t = self.terms.get(n)
        if t is not None and t.dead:
            self.close(n)
            t = None
        if t is None:
            learn = os.path.join(self.top, "learn")
            if not os.path.exists(learn):
                with open(learn, "w") as f:
                    f.write(SHIM.format(python=sys.executable, repo=core.ROOT))
                os.chmod(learn, 0o755)
            t = self.terms[n] = Terminal(self.top, self.env, self.prompts, self.quiet, self.settle)
        return t

    def quit(self, n=1):
        """Back to the shell's prompt, as a reader would leave whatever is running."""
        t = self.terms.get(n)
        if t is None:
            return
        if not t.dead and t.at_host():
            return
        for keys in self.quit_keys + ["\x03", "\x04"]:
            if t.dead:
                break
            t.keys(keys)
            if t.wait_host(5):
                return
        self.close(n)               # a new terminal, in the checkout, as a reader would open one
        self.terminal(n)

    def close(self, n=None):
        for k in ([n] if n is not None else sorted(self.terms)):
            t = self.terms.pop(k, None)
            if t is not None:
                try:
                    self.raw += t.raw()
                except OSError:
                    pass
                t.close()

    def hidden(self, t, command, timeout, line):
        """Type a command at the shell's prompt that the page does not show, and wait for it."""
        since = len(t.raw())
        t.type(command)
        if t.wait(since, True, timeout) == "timeout" or not t.at_host():
            self.fail(line, f"`{command}` did not come back to the prompt")
            return False
        return True

    def enter(self, n, note, at, timeout):
        """The terminal for a block or setup: first back where the last cwd= block found it (its
        cd was the block's own, unseen), then into this one's cwd=, remembering where it was.
        False when the cwd= cannot be entered (a problem is recorded)."""
        t = self.terminal(n)
        prev = self.back.get(n)
        if prev is not None and t.at_host():
            del self.back[n]
            if os.path.realpath(t.cwd() or prev) != os.path.realpath(prev):
                self.hidden(t, "cd " + shell_quote(prev), timeout, note.line)
        cwd = note.opts.get("cwd")
        if cwd is not None:
            root = self.ensure_project(at) if cwd == "project" else os.path.join(self.top, cwd)
            if cwd == "project" and not self.build(root, note.line, at):
                return False
            here = t.cwd() or self.top
            if not self.hidden(t, "cd " + shell_quote(root), timeout, note.line):
                return False
            self.back.setdefault(n, here)
        return True

    def to_checkout(self, t, timeout, line):
        """./learn works from the top of the checkout: go there first, as a reader would."""
        if os.path.realpath(t.cwd() or self.top) != os.path.realpath(self.top):
            self.hidden(t, "cd " + shell_quote(self.top), timeout, line)

    # ---- reading the lesson

    def run(self):
        for item in self.doc.items:
            try:
                self.step(item, self.lesson.id)
            except core.Fail as e:
                line = item.line if isinstance(item, Note) else item.start
                self.fail(line, str(e))
            except Exception as e:      # a bug in the verifier, or a terminal that broke: say where
                line = item.line if isinstance(item, Note) else item.start
                self.fail(line, f"the replay broke here: {type(e).__name__}: {e}")
        return self.problems

    def step(self, item, home, compare=True):
        if isinstance(item, Note):
            if item.kind == "patch":
                self.patch(item, home)
            elif item.kind == "revert":
                self.revert(item, home)
            elif item.kind == "fact":
                self.fact(item, home)
            elif item.kind == "setup":
                self.setup(item, home)
        elif item.role == "typed":
            for note in item.notes:
                self.patch(note, home)
        elif item.role == "session":
            self.session(item.notes[0], item, home, compare)
        elif item.role == "file" and compare:
            self.file_block(item.notes[0], item, home)

    # ---- the steps

    def touch_wait(self):
        """make (3.81 on macOS) compares whole seconds: write a change in a second after
        everything already built, or it may keep the stale binary."""
        time.sleep(1.02 - (time.time() % 1.0))

    def patch(self, note, home):
        self.quit()
        at = note.at(home)
        root = self.ensure_project(at)
        rel = note.opts.get("file", "")
        path = os.path.join(root, rel)
        text = None
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        elif "create" not in note.flags:
            self.fail(note.line, f"patch: there is no {rel} in the reader's copy of the project at {at or 'the end'}")
            return
        self.originals.setdefault((at, rel), text)
        try:
            if "old" in note.opts:
                new = apply_edit(text or "", note.opts["old"], note.opts.get("new", ""))
            else:
                new = apply_patch(text, patch_ops(note, note.block), append="append" in note.flags)
        except AnnotationError as e:
            self.fail(note.line, f"patch {rel} at {at or 'the end'}: {e}")
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.touch_wait()
        with open(path, "w") as f:
            f.write(new)

    def revert(self, note, home):
        self.quit()
        at = note.at(home)
        for (a, rel), text in list(self.originals.items()):
            if a == at and note.opts.get("file") in (None, rel):
                path = os.path.join(self.project_root(a), rel)
                self.touch_wait()
                if text is None:            # a file the patch made: gone again
                    if os.path.exists(path):
                        os.unlink(path)
                else:
                    with open(path, "w") as f:
                        f.write(text)
                del self.originals[(a, rel)]

    def fact(self, note, home):
        import subprocess
        at = note.at(home)
        root = self.ensure_project(at)
        if not self.build(root, note.line):
            return
        cmd = note.opts["cmd"]
        try:
            r = subprocess.run(["sh", "-c", cmd], cwd=root, env=self.env, capture_output=True, text=True,
                               timeout=float(self.v.timeout) * 4)
        except subprocess.TimeoutExpired:
            self.fail(note.line, f"fact: `{cmd}` did not finish")
            return
        got = r.stdout.strip()
        if got != note.opts["expect"].strip():
            self.fail(note.line, f"fact: the lesson says {note.opts['expect']!r}; `{cmd}` in the project at "
                                 f"{at or 'the end'} printed {got!r}" + (f"\n    stderr: {r.stderr.strip()[:300]}"
                                                                          if r.stderr.strip() else ""))

    def setup(self, note, home):
        """What the page says to do but shows no block for, done in the terminal unseen."""
        o = note.opts
        n = int(o.get("terminal", 1))
        timeout = float(o.get("timeout", self.v.timeout))
        at = note.at(home)
        self.quit(n)
        if not self.enter(n, note, at, timeout):
            return
        for number, text in note.body:
            if not text.strip():
                continue
            m = SETUP_STEP.match(text)
            t = self.terminal(n)
            if m.group("cmd"):
                cmd = m.group("cmd")
                if cmd.startswith("./learn "):
                    self.to_checkout(t, timeout, number)
                since = len(t.raw())
                t.type(cmd)
                got = t.wait(since, "host", timeout)
                if got == "timeout":
                    self.fail(number, f"setup: `{cmd}` did not finish or show a prompt in {timeout:g}s")
                    return
                if t.at_host() and t.last_rc():
                    tail = "\n".join(t.screen(since)[-6:])
                    self.fail(number, f"setup: `{cmd}` failed (exit status {t.last_rc()}):\n    " +
                              tail.replace("\n", "\n    "))
                    return
            elif m.group("keys"):
                since = len(t.raw())
                t.keys(parse_keys(m.group("keys")))
                t.wait(since, True, timeout)
            else:
                try:
                    lesson, doc, block = replay_target(self.track, m.group("lesson"), m.group("which"))
                except AnnotationError as e:
                    self.fail(number, f"setup: {e}")
                    return
                self.v.check_blocks(self.track, doc, lesson)       # gives the block its role
                if block.role not in ("session", "typed"):
                    self.fail(number, f"setup: replay: that block of {lesson.id} is not a session or code typed in")
                    return
                self.step(block, at, compare=False)

    def file_block(self, note, block, home):
        """A block that is an excerpt of a file the project has or its build writes."""
        exp = note.expect
        if exp is None:
            return
        at = note.at(home)
        root = self.ensure_project(at)
        if not self.build(root, note.line):
            return
        path = os.path.join(root, note.opts["path"])
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = [l.expandtabs(8).rstrip() for l in f.read().split("\n")]
        except OSError:
            self.fail(note.line, f"file: the project at {at or 'the end'} has no {note.opts['path']} after its build")
            return
        m = match(exp, lines)
        if not m.ok:
            self.problems.append(mismatch(self.doc, m, f"file {note.opts['path']} at {at or 'the end'}", block))

    def session(self, note, block, home=None, compare=True):
        home = home or self.lesson.id
        exp = note.expect
        if exp is None:
            return                  # its annotation is broken: the static check said why
        items = exp.items
        o, fl = note.opts, note.flags
        for tool in o.get("needs", "").split():
            if not shutil.which(tool, path=self.env["PATH"]):
                self.missing.add(tool)
                return
        n = int(o.get("terminal", 1))
        timeout = float(o.get("timeout", self.v.timeout))
        settle = float(o["wait"]) if "wait" in o else None
        at = note.at(home)
        what = f"session at {at or 'the end'}"
        t = self.terminal(n)
        first = next((l for l in block.lines if l.strip()), "")
        if "fresh" in fl:
            self.quit(n)
            shutil.rmtree(self.project_root(at), ignore_errors=True)
            self.originals = {k: v for k, v in self.originals.items() if k[0] != at}
        restart = ("run" in o or "host" in fl or "cwd" in o or first.startswith("$ ./learn ")
                   or (first.startswith("$ ") and "$ " not in self.prompts and not t.at_host()))
        if restart:
            self.quit(n)
        if not self.enter(n, note, at, timeout):
            return
        t = self.terminal(n)
        if o.get("run", "").startswith("./learn ") or first.startswith("$ ./learn "):
            self.to_checkout(t, timeout, note.line)
        prompts_ahead = any(prompt_line(it, t) for it in items)
        waited = ""
        box = {"seg": None}
        state = {"cur": 0, "pos": 0}
        done = set()

        def pending():
            return any((it.keys and (i, "keys") not in done) or (it.typed and (i, "type") not in done)
                       for i, it in enumerate(items) if i >= state["cur"] and it.kind == "line")

        def event():
            lines = t.screen(box["seg"])
            return self.next_event(exp, state["cur"], lines[:-1], state["pos"], lines[-1], t, done)

        def finished():
            lines = t.screen(box["seg"])
            return match(exp, [l.rstrip() for l in lines[:-1]] + [lines[-1].rstrip()]).ok

        # Start-up waits stop at once when the screen reaches the first key or typed line: output
        # that never pauses (a clock ticking) must not run past it.
        early = event if pending() else None
        if "run" in o:
            start = len(t.raw())
            t.type(o["run"])
            box["seg"] = self.after_echo(t, start, timeout, banner=o["run"].startswith("./learn "))
            # The system is ready once it shows a prompt or, when none is coming, has been quiet a
            # while after printing something or starting; with wait=, quiet counts from the command.
            plain = "send" not in o and "type" not in o
            got = t.wait(start if "wait" in o else box["seg"], prompts_ahead and plain, timeout, settle,
                         until=early if plain else None)
            if got == "timeout":
                waited = f"\n    (after `{o['run']}`, waited {timeout:g}s: no prompt, and never quiet after printing)"
        if "send" in o:                                      # keys pressed first, such as Control-a c
            box["seg"] = len(t.raw())
            t.keys(parse_keys(o["send"]))
            if t.wait(box["seg"], prompts_ahead or "type" in o, timeout, settle,
                      until=early if "type" not in o else None) == "timeout":
                waited += f"\n    (after the keys {o['send']}, waited {timeout:g}s for a prompt)"
        if "type" in o:                                      # a line typed that the block leaves out
            start = len(t.raw())
            t.type(o["type"])
            box["seg"] = self.after_echo(t, start, timeout)
            if t.wait(box["seg"], prompts_ahead, timeout, settle, until=early) == "timeout" and prompts_ahead:
                waited += f"\n    (after typing {o['type']!r}, waited {timeout:g}s for a prompt)"
        partial = t.partial()
        seg = box["seg"]
        if seg is None:
            seg = len(t.raw())
            if partial.strip() and first.startswith(partial):    # the block starts at the line showing
                seg = t.line_start()
        elif "type" not in o and partial.strip() and first.startswith(partial) and t.prompt_shown(partial):
            seg = max(seg, t.line_start())                   # not before what the command printed
        box["seg"] = seg

        # The block, line by line: type what the reader types, press what they press, when the
        # screen has shown everything the block shows before it.
        idle_until = time.monotonic() + timeout
        while True:
            lines = t.screen(seg)
            complete, partial = lines[:-1], lines[-1]
            ev = self.next_event(exp, state["cur"], complete, state["pos"], partial, t, done)
            if ev is None:
                if pending() and time.monotonic() < idle_until and not t.dead:
                    t.pump(0.05)
                    continue
                break
            i, kind, payload = ev
            since = len(t.raw())
            at_host = t.at_host()
            done.add((i, kind))
            if kind == "keys":
                t.keys(payload)
                state["cur"], state["pos"] = i, len(complete)
                later = items[i + 1:]       # line i is under way: what comes after it may prompt
            else:
                t.type(payload)
                state["cur"], state["pos"] = i + 1, len(complete) + 1
                later = items[i + 1:]
            if at_host and kind == "type":
                # a command typed at the shell: done when the shell, or a system it started, is
                # waiting again (or quiet, once ./learn has started one that never prompts)
                want = "host"
                until = None
            else:
                want = any(prompt_line(it, t) for it in later)
                until = event if pending() else (finished if exp.more else None)
            got = t.wait(since, want, timeout, settle, until=until)
            if got == "timeout" and want is True:
                waited += f"\n    (after {'the keys' if kind == 'keys' else 'typing'} {payload!r}, waited {timeout:g}s for a prompt)"
            idle_until = time.monotonic() + timeout
        hangs = note.has("hangs")
        if hangs:                   # nothing more for this long: what the block shows is all there is
            secs = float(o.get("hangs") or 3)
            since = len(t.raw())
            end = time.monotonic() + secs
            while time.monotonic() < end:
                t.pump(0.05)
            if len(t.raw()) > since and not t.prompt_shown(t.partial()):
                self.fail(block.start, f"{what}: the lesson says it hangs here, but it went on printing")
        if "panics" in o:
            want = self.panic + o["panics"]
            end = time.monotonic() + timeout
            while want not in "\n".join(t.screen(seg)) and time.monotonic() < end:
                t.pump(0.05)
            if want not in "\n".join(t.screen(seg)):
                self.fail(block.start, f"{what}: the lesson says it panics with {want!r}, but it never printed that")
            else:
                t.quiet_for(self.settle if settle is None else settle, timeout)   # the rest of the dying words
        if not compare:
            return
        lines = t.screen(seg)
        actual = [l.rstrip() for l in lines[:-1]] + ([lines[-1].rstrip()] if lines[-1].strip() else [])
        while actual and not actual[-1]:
            actual.pop()
        last = items[-1].text.rstrip() if items and items[-1].kind == "line" else None
        if actual and actual[-1] in {p.rstrip() for p in t.prompts} and actual[-1] != last:
            if hangs:
                self.fail(block.start, f"{what}: the lesson says it hangs here, but a prompt came back")
                return
            actual.pop()            # the prompt waiting for the next line, which the block leaves out
            while actual and not actual[-1]:
                actual.pop()
        self.transcripts.append((block.start, "\n".join(actual)))
        m = match(exp, actual)
        if not m.ok:
            p = mismatch(self.doc, m, what, block)
            p.message += waited
            if not actual and t.at_host() and not first.startswith("$ "):
                p.message += "\n    (nothing is running in the terminal here: start it with run=\"...\")"
            self.problems.append(p)
        if "build-fails" in o:
            text = "\n".join(actual)
            if "build failed" not in text or o["build-fails"] not in text:
                self.fail(block.start, f"{what}: the lesson says the build fails with {o['build-fails']!r}, "
                                       "but " + ("it built" if "build failed" not in text else "it never printed that"))
        if "exit" in o:
            rc = t.last_rc()
            if rc != int(o["exit"]):
                self.fail(block.start, f"{what}: the lesson says the last command exits with {o['exit']}, "
                                       f"but it exited with {rc}")

    def after_echo(self, t, start, timeout, banner=False):
        """Where the output of a line typed at start begins: after its echo and, for ./learn,
        after its own "Running ..." line, which a block that does not show the command leaves out."""
        end = time.monotonic() + timeout
        while True:
            seg = t.raw()[start:]
            k1 = seg.find("\n")
            if k1 >= 0:
                if not banner:
                    return start + k1 + 1
                k2 = seg.find("\n", k1 + 1)
                if k2 >= 0:
                    line = screen_lines(seg[k1 + 1:k2])[0]
                    if line.startswith(("Running ", "Benchmarking ", "Wrote ")) or " is already in " in line:
                        return start + k2 + 1
                    return start + k1 + 1
                if t.at_host() or time.monotonic() > end:
                    return start + k1 + 1
            elif time.monotonic() > end or t.dead:
                return start + len(seg)
            t.pump(0.05)

    def next_event(self, exp, cur, complete, pos, partial, t, done):
        """(index, "type" or "keys", what) of the next thing the reader does, once everything the
        block shows before it is on the screen; or None. A line is typed when it starts with the
        prompt the terminal is showing (or the shell waits for the rest of a command), or when a
        rule says the reader types it; keys are pressed as their line starts."""
        items = exp.items
        cont = t.continuing()
        sub = Expect([], exp.anywhere, exp.ignore)
        for i in range(cur, len(items)):
            it = items[i]
            if it.kind != "line":
                continue

            def before_ok():
                sub.items = items[cur:i]
                return match(sub, complete[pos:], more=False, before=exp.before and cur == 0, prefix=True).ok
            if it.keys and (i, "keys") not in done:
                if it.text.startswith(partial.rstrip()) or not partial.strip():
                    if before_ok():
                        return i, "keys", parse_keys(it.keys)
                continue
            if (i, "type") in done or it.rx is not None or it.output:
                continue
            if it.typed:
                if it.text.startswith(partial) and partial and it.text[len(partial):].strip():
                    typed = it.text[len(partial):].rstrip()
                else:
                    typed = it.text.strip()
                if before_ok():
                    return i, "type", typed
                continue
            if it.text.startswith(partial) and it.text[len(partial):].strip() and \
                    (cont or t.prompt_shown(partial)) and before_ok():
                return i, "type", it.text[len(partial):].rstrip()
        return None


def prompt_line(item, t):
    return item.kind == "line" and any(item.text.startswith(p) for p in t.prompts)


def shell_quote(path):
    return "'" + path.replace("'", "'\\''") + "'"


# ---------------------------------------------------------------- running it

def verifier_version():
    h = hashlib.sha256()
    for name in ("verify.py", "session.py", "timeline.py", "cli.py", "workspace.py", "core.py"):
        try:
            with open(os.path.join(HERE, name), "rb") as f:
                h.update(f.read())
        except OSError:
            pass
    return h.hexdigest()


def pending(track):
    """Lessons listed in tracks/<id>/lessons/verify-pending.txt: not annotated yet."""
    path = os.path.join(track.root, "lessons", PENDING_FILE)
    out = {}
    try:
        with open(path) as f:
            for n, line in enumerate(f, 1):
                line = line.split("#", 1)[0].strip()
                if line:
                    out[line] = n
    except OSError:
        pass
    return out


def tools_of(track):
    hook = getattr(track.module, "verify_tools", None)
    try:
        return dict(hook()) if hook else {}
    except Exception as e:      # a broken hook: say so, as a missing tool
        return {f"verify_tools ({e})": None}


def needs_replay(doc):
    return any(isinstance(i, Note) and i.kind in ("patch", "revert", "fact", "setup") for i in doc.items) or \
        any(b.role in ("session", "typed", "file") for b in doc.blocks)


def replayed(track, doc):
    """[(lesson, Doc)] of the other lessons whose blocks the lesson's setups replay."""
    out = []
    for note in doc.notes:
        if note.kind != "setup":
            continue
        for _, text in note.body:
            m = SETUP_STEP.match(text)
            if m and m.group("lesson"):
                try:
                    lesson, odoc, _ = replay_target(track, m.group("lesson"), m.group("which"))
                except AnnotationError:
                    continue
                out.append((lesson, odoc))
    return out


def ats_of(doc, lesson_id, track=None):
    """Every lesson whose project the lesson uses: its own, at= and run=, ./learn commands, and
    those of the blocks its setups replay."""
    out = {lesson_id}
    for note in doc.notes:
        out.add(note.at(lesson_id))
        for _, text in note.body:
            got = learn_at(text)
            if got is not False:
                out.add(got)
    for b in doc.blocks:
        for l in b.lines:
            got = learn_at(l)
            if got is not False:
                out.add(got)
    if track is not None:
        for _, odoc in replayed(track, doc):
            out |= ats_of(odoc, lesson_id)
    return out


_port_locks = {}
_port_guard = threading.Lock()


def host_ports(doc):
    """Ports on 127.0.0.1 a lesson's runs take (make qemu UDPFWD=2000): two lessons that take
    the same one cannot run at the same time."""
    return sorted({int(p) for p in re.findall(r"UDPFWD=(\d+)", doc.text)})


class Result:
    def __init__(self, track, lesson):
        self.track, self.lesson = track, lesson
        self.status = "ok"
        self.problems, self.warnings = [], []
        self.seconds = 0.0
        self.counts = {}
        self.note = ""


def verify_lesson(v, track, lesson, static_only=False):
    r = Result(track, lesson)
    t0 = time.monotonic()
    doc = Doc(lesson.doc, lesson.id)
    found = v.static(track, lesson, doc)
    r.problems = [p for p in found if not p.warning]
    r.warnings = [p for p in found if p.warning]
    roles = [b.role or "quote" for b in doc.blocks]
    r.counts = {"blocks": len(doc.blocks), "sessions": roles.count("session"), "quoted": roles.count("quote"),
                "files": roles.count("file"), "setups": sum(1 for n in doc.notes if n.kind == "setup"),
                "skips": roles.count("skip"), "typed": roles.count("typed"),
                "patches": sum(1 for n in doc.notes if n.kind == "patch"),
                "facts": sum(1 for n in doc.notes if n.kind == "fact")}
    if static_only or doc.errors or not needs_replay(doc):    # a broken annotation: nothing to replay
        r.status = "FAIL" if r.problems else ("ok" if not static_only else "static ok")
        r.seconds = time.monotonic() - t0
        return r
    tools = v._tools.setdefault(track.id, tools_of(track))
    missing = sorted(name for name, path in tools.items() if not path)
    if missing:
        r.status = "missing"
        r.note = "cannot verify: missing " + ", ".join(missing)
        r.seconds = time.monotonic() - t0
        return r
    h = hashlib.sha256()
    h.update(verifier_version().encode())
    with open(os.path.join(track.root, "track.py"), "rb") as f:
        h.update(f.read())
    h.update(doc.text.encode())
    for other, odoc in replayed(track, doc):               # a page whose blocks the setups replay
        h.update(f"{other.id}\n".encode() + odoc.text.encode())
    for at in sorted(ats_of(doc, lesson.id, track), key=lambda a: a or "~"):
        if v.known_at(track, at):
            h.update(f"{at}:{v.index(track, at).digest}\n".encode())
    for name, path in sorted(tools.items()):
        try:
            st = os.stat(path)
            h.update(f"{name}={path}:{st.st_size}:{st.st_mtime_ns}\n".encode())
        except OSError:
            h.update(f"{name}={path}\n".encode())
    key = h.hexdigest()
    cache = os.path.join(build_dir(), "cache", track.id, lesson.id + ".json")
    if not v.fresh:
        try:
            with open(cache) as f:
                got = json.load(f)
            if got.get("key") == key and got.get("ok"):
                r.status = "cached"
                r.counts = got.get("counts", r.counts)
                r.seconds = time.monotonic() - t0
                return r
        except (OSError, ValueError):
            pass
    top = os.path.join(build_dir(), "run", track.id, lesson.id)
    shutil.rmtree(top, ignore_errors=True)
    os.makedirs(top)
    rp = Replay(v, track, doc, lesson, top, tools)
    with _port_guard:
        locks = [_port_locks.setdefault(p, threading.Lock()) for p in host_ports(doc)]
    for lock in locks:
        lock.acquire()
    try:
        seen = {(p.line, p.message) for p in r.problems}
        r.problems = r.problems + [p for p in rp.run() if (p.line, p.message) not in seen]
    finally:
        rp.close()
        for lock in reversed(locks):
            lock.release()
    r.seconds = time.monotonic() - t0
    with open(os.path.join(top, "transcripts.txt"), "w") as f:
        for line, text in rp.transcripts:
            f.write(f"==== what the terminal showed for the block at line {line}\n{text}\n")
        f.write("==== the whole terminal\n" + "\n".join(screen_lines(rp.raw)) + "\n")
    if rp.missing and not r.problems:
        r.status = "missing"
        r.note = "cannot verify: missing " + ", ".join(sorted(rp.missing)) + " (a session needs it)"
        shutil.rmtree(top, ignore_errors=True)
        return r
    if r.problems:
        r.status = "FAIL"
        shown = os.path.relpath(top, core.ROOT)
        r.note = f"its terminal (transcripts.txt) and files are kept in {top if shown.startswith('..') else shown}/"
    else:
        if not v.keep:
            shutil.rmtree(top, ignore_errors=True)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w") as f:
            json.dump({"key": key, "ok": True, "seconds": round(r.seconds, 1), "counts": r.counts}, f)
    return r


def build_dir():
    return os.path.join(os.environ.get("LEARN_VERIFY_DIR") or os.path.join(core.ROOT, "build"), "verify")


def describe(r):
    c = r.counts
    bits = [f"{c.get('sessions', 0)} sessions", f"{c.get('quoted', 0)} quoted"]
    for k in ("files", "typed", "patches", "setups", "facts", "skips"):
        if c.get(k):
            bits.append(f"{c[k]} {k}")
    return ", ".join(bits)


def static_problems(tracks=None):
    """For ./learn check: (problems, notes) of every lesson that is not pending, no builds."""
    v = Verifier()
    problems, notes = [], []
    for track in tracks or core.discover_tracks():
        pend = pending(track)
        ids = {l.id for l in track.lessons}
        for lid, n in pend.items():
            if lid not in ids:
                problems.append(f"{os.path.relpath(os.path.join(track.root, 'lessons', PENDING_FILE), core.ROOT)}:"
                                f"{n}: {lid} is not a lesson of {track.id}")
        for l in track.lessons:
            if l.doc and l.id not in pend:
                problems.extend(str(p) for p in v.static(track, l, figures=False) if not p.warning)
        left = [l for l in pend if l in ids]
        if left:
            notes.append(f"verify: {track.id} has {len(left)} lessons not annotated yet "
                         f"(tracks/{track.id}/lessons/{PENDING_FILE})")
    return problems, notes


USAGE = ("usage: learn verify [track] [ids...] [--jobs N] [--fresh] [--static] [--report] "
         "[--allow-missing] [--keep]")


def main(args):
    jobs, flags, pos = 1, set(), []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--jobs", "-j"):
            if i + 1 >= len(args) or not args[i + 1].isdigit():
                sys.exit(USAGE)
            jobs = max(1, int(args[i + 1]))
            i += 2
            continue
        if a.startswith("--jobs="):
            jobs = max(1, int(a.split("=", 1)[1]))
        elif a in ("--fresh", "--static", "--report", "--allow-missing", "--keep"):
            flags.add(a)
        elif a.startswith("-"):
            sys.exit(USAGE)
        else:
            pos.append(a)
        i += 1
    tracks = core.discover_tracks()
    if pos and not re.match(r"^\d", pos[0]):
        tracks = [t for t in tracks if t.id == pos[0]]
        if not tracks:
            sys.exit(f"no track named {pos[0]!r}")
        pos = pos[1:]
    if "--report" in flags:
        return report(tracks, pos)
    v = Verifier(fresh="--fresh" in flags, keep="--keep" in flags, allow_missing="--allow-missing" in flags)
    todo, skipped = [], []
    for track in tracks:
        pend = pending(track)
        for l in track.lessons:
            if not l.doc:
                continue
            if pos:
                if any(l.id.startswith(p) for p in pos):
                    todo.append((track, l))
            elif l.id in pend:
                skipped.append((track, l))
            else:
                todo.append((track, l))
    if not todo:
        print("verify: no lessons to check" + (f" ({len(skipped)} pending)" if skipped else ""))
        return 0
    static_only = "--static" in flags
    print(f"verify: {len(todo)} lessons" + (" (static checks only)" if static_only else "")
          + (f", {jobs} at a time" if jobs > 1 else ""), flush=True)
    t0 = time.monotonic()
    bad = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(verify_lesson, v, tr, l, static_only) for tr, l in todo]
        for f in futures:
            r = f.result()
            title = r.lesson.title if len(r.lesson.title) <= 34 else r.lesson.title[:31] + "..."
            print(f"   {r.track.id:<4} {r.lesson.id}  {title:<34} {r.status:<9} {r.seconds:5.1f}s  {describe(r)}",
                  flush=True)
            for p in r.problems:
                print("      " + str(p).replace("\n", "\n      "))
            for p in r.warnings:
                print("      warning: " + str(p))
            if r.note:
                print("      " + r.note)
            if r.status == "FAIL" or (r.status == "missing" and not v.allow_missing):
                bad.append(f"{r.track.id}/{r.lesson.id}")
    took = time.monotonic() - t0
    tail = f"; {len(skipped)} lessons pending annotation (./learn verify --report)" if skipped else ""
    print(f"\nverify: {'ok' if not bad else 'problems in ' + ' '.join(bad)} ({took:.1f}s{tail})")
    return 1 if bad else 0


def report(tracks, pos):
    """Every skip and its reason, every name declared outside the project, every allowance a
    session makes, the pending lessons and the figures nothing uses."""
    v = Verifier()
    for track in tracks:
        pend = pending(track)
        print(f"== {track.id}")
        for l in track.lessons:
            if not l.doc or (pos and not any(l.id.startswith(p) for p in pos)):
                continue
            if l.id in pend:
                print(f"   {l.id}  pending: not annotated yet")
                continue
            doc = Doc(l.doc, l.id)
            rel = os.path.relpath(l.doc, core.ROOT)
            lines = []
            for note in doc.notes:
                if note.kind == "skip":
                    lines.append(f"{rel}:{note.line}: skip: {note.opts.get('reason', '(no reason)')}")
                elif note.kind == "setup":
                    steps = "; ".join(t.strip() for _, t in note.body if t.strip())
                    lines.append(f"{rel}:{note.line}: setup (not on the page): {steps}")
                elif note.kind == "mention" and "outside" in note.flags:
                    lines.append(f"{rel}:{note.line}: outside the project: {note.opts.get('names', '')} - "
                                 f"{note.opts.get('reason', '(no reason)')}")
                elif note.kind in ("session", "file"):
                    # keys and typed lines are what the reader does; everything else is an allowance
                    allow = [t.strip() for _, t in note.body if t.strip() and not KEYS_RULE.match(t)
                             and not re.match(r"^\s*lines?\s+[\d\s-]+typed\s*$", t)]
                    allow += [f for f in ("more", "before") if f in note.flags]
                    if allow:
                        lines.append(f"{rel}:{note.line}: {note.kind} allows: " + "; ".join(allow))
            for p in v.check_figures(doc, l):
                if p.warning:
                    lines.append(str(p))
            print(f"   {l.id}  " + (f"{len(lines)} to read" if lines else "nothing skipped or allowed"))
            for line in lines:
                print("      " + line)
    return 0
