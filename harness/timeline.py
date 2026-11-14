"""The project as it stands at a lesson: which files exist by then, and what is in them.

Lessons are read on a path: the core lessons in order, and an optional module's lessons
after the whole core, on their own (another extension's code is never part of it).

When a file appears:
    - at the lesson track.py names for it in FILES_FROM = {"path or glob": "NN.LL"};
    - otherwise with the first lesson that has a @build region in it; the code outside its
      regions (includes, structs, helpers) comes along then;
    - a file with neither is unplaced: the site shows it throughout and `./learn check`
      reports it.

What a file holds at a lesson:
    - the marker and instruction comment lines of every region are left out;
    - a region of a lesson not reached yet is left out with the whole top-level C definition
      around it (its comment, signature and braces), unless that definition also holds code
      that is reached already, in which case only the region goes;
    - code outside the regions that a later lesson adds is marked with the lesson it comes
      with, in any file (C, assembly, Makefile, linker script, perl), with that file's
      comment leader (//, #, ;, -- or /* */):

          // @from 05.01
          virtio_disk_init();
          // @end

      or, for one line, "@from NN.LL" at the very end of its comment:

          #define SYS_fork 1   // @from 06.04

      A block may hold an "@else" part: the code that stands there *before* that lesson,
      commented out with the same leader, one leader per line:

          // @from 04.02
          scheduler();
          // @else
          // for(;;)
          //   asm volatile("wfi");
          // @end

      "@internal" ... "@end" marks code that is in the track's own build (test aids) but
      never part of the project a reader sees. Blocks may sit inside @build regions;
    - none of these markers is ever shown, and none changes the track's own build: the
      track as it stands in tracks/ is the project at the end of every path;
    - a file with no regions and no markers is shown whole from the lesson it appears in.

materialize() writes the project at a lesson into a directory (`./learn check-timeline`
builds and boots each one). Nothing else here runs anything or writes anywhere: it reads
the reference code in tracks/.
"""

import fnmatch
import os
import re
import shutil

from harness import core
from harness import workspace as ws

MAX_TREE = 3000

BLOCK_LEADER = r"(//|#|;|--|/\*)"
FROM_RE = re.compile(r"^\s*" + BLOCK_LEADER + r"\s*@from\s+(\d\d\.\d\d)\s*(\*/)?\s*$")
ELSE_RE = re.compile(r"^\s*" + BLOCK_LEADER + r"\s*@else\s*(\*/)?\s*$")
INTERNAL_RE = re.compile(r"^\s*" + BLOCK_LEADER + r"\s*@internal\s*(\*/)?\s*$")
BLOCK_END_RE = re.compile(r"^\s*" + BLOCK_LEADER + r"\s*@end\b")
LINE_FROM_RE = re.compile(r"^(.*?\S)\s+@from\s+(\d\d\.\d\d)\s*$")
EMPTY_COMMENT = re.compile(r"\s+(//|#|--)$")   # what a one-line marker leaves behind


# ---------------------------------------------------------------- the files a reader sees

def hidden_files(track):
    try:
        return tuple(getattr(track.module, "HIDDEN", ()))
    except Exception:
        return ()


def tree_files(root, hidden=()):
    """Relative paths of every file of the track a reader sees, sorted: the system's own files
    (no lessons, tests, track.py, build output or the track's own picture), minus dotfiles and
    the track's HIDDEN patterns (internal files that are built but not taught)."""
    out = []
    real_root = os.path.realpath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in ws.NOT_COPIED and not d.startswith("build") and not d.startswith("."))
        for fn in sorted(filenames):
            if fn.startswith(".") or fn in ws.NOT_COPIED or fn.startswith("build"):
                continue
            full = os.path.join(dirpath, fn)
            real = os.path.realpath(full)
            if not (real == real_root or real.startswith(real_root + os.sep)) or not os.path.isfile(real):
                continue  # a symlink pointing out of the tree, or not a regular file
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, p) for p in hidden) or rel in ws.TRACK_FILES:
                continue
            out.append(rel)
            if len(out) >= MAX_TREE:
                return sorted(out)
    return sorted(out)


# ---------------------------------------------------------------- the reading path

def reached(track, lid, at):
    """Is lesson lid part of what a reader has at lesson `at` (None: the end of the track)?"""
    if at is None or lid == at:
        return True
    if track.is_optional(at):
        return not track.is_optional(lid) or (core.module_id(lid) == core.module_id(at)
                                              and core.lesson_key(lid) <= core.lesson_key(at))
    return not track.is_optional(lid) and core.lesson_key(lid) <= core.lesson_key(at)


def previous(track, at, ids=()):
    """The lesson before `at` on its path, or None for the first one. ids: more lesson ids to
    count (lessons that have code but no doc yet)."""
    ids = sorted({l.id for l in track.lessons} | set(ids) | {at}, key=core.lesson_key)
    path = [i for i in ids if i != at and reached(track, i, at)]
    return path[-1] if path else None


# ---------------------------------------------------------------- C definitions

LABEL = re.compile(r"^[A-Za-z_]\w*:\s*(//.*|/\*.*)?$")   # a goto label, which C style puts at column 0


def is_c(path):
    return path.endswith((".c", ".h"))


def _col0(line):
    return line[:1] not in ("", " ", "\t")


def _not_code(line):
    """Blank, a comment, a preprocessor line, or a goto label: nothing that opens or closes a definition."""
    t = line.strip()
    return not t or t.startswith(("//", "/*", "*", "#")) or bool(LABEL.match(t))


def _marker(line):
    return bool(ws.BUILD_RE.match(line) or ws.END_RE.match(line) or ws.STUB_RE.match(line)
                or FROM_RE.match(line) or ELSE_RE.match(line) or INTERNAL_RE.match(line))


def definition_span(lines, region):
    """(first, last) line indexes of the top-level C definition around a region: the comment
    block directly above it, the signature (a return type on its own line too), through the
    closing brace at column 0. None when the region is not inside one (it is top-level code,
    or a shape this scan does not know)."""
    up = next((i for i in range(region.start - 1, -1, -1) if _col0(lines[i]) and not _not_code(lines[i])), None)
    if up is None or not lines[up].rstrip().endswith("{"):
        return None
    down = next((j for j in range(region.end + 1, len(lines)) if _col0(lines[j]) and not _not_code(lines[j])), None)
    if down is None or not lines[down].startswith("}"):
        return None
    first = up
    for k in range(up - 1, -1, -1):          # the rest of the signature: "void" above "kfree(void *pa)"
        t = lines[k].strip()
        if _not_code(lines[k]) or t.endswith((";", "}", "{")):
            break
        first = k
    if not _col0(lines[first]):
        return None
    while first > 0 and lines[first - 1].strip().startswith(("//", "/*", "*")) and not _marker(lines[first - 1]):
        first -= 1                           # the comment that introduces the definition
    return first, down


def functions(lines):
    """[(head, first, last)] for each top-level C function in lines: the position of the line its
    signature starts on, and of the first and last lines of its body (between the "{" that opens
    it and the "}" at column 0 that closes it; first > last for an empty body). Prototypes,
    macros, structs and initializers ("= {") are not functions. What the folds fold."""
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if _col0(line) and not _not_code(line) and "(" in line and "=" not in line.split("(")[0] \
                and not line.rstrip().endswith(";"):
            j = i                      # the signature may run on: the body opens at the first "{"
            while j < len(lines) and not lines[j].rstrip().endswith(("{", ";", "}")) and j - i < 8:
                j += 1
            if j < len(lines) and lines[j].rstrip().endswith("{") and "=" not in lines[j]:
                k = next((k for k in range(j + 1, len(lines)) if lines[k].startswith("}")), None)
                if k is not None:
                    out.append((i, j + 1, k - 1))
                    i = k + 1
                    continue
        i += 1
    return out


def function_bodies(lines):
    """[(first, last)] of every function body in lines that has one (see functions)."""
    return [(a, b) for _, a, b in functions(lines) if a <= b]


def function_name(lines):
    """The name a definition's first lines declare ("kfree" from "kfree(void *pa)"), or ""."""
    for line in lines:
        if _col0(line) and not _not_code(line):
            m = re.search(r"([A-Za-z_]\w*)\s*\(", line)
            if m:
                return m.group(1)
    return ""


def code_part(line):
    """A C line without its comments (a "//" to the end, a "/* */" or the start of an unclosed
    "/*"), quotes respected, right-stripped: what decides whether the line ends in "{" or ";"."""
    out, quote, i = [], None, 0
    while i < len(line):
        ch = line[i]
        if quote:
            out.append(line[i:i + 2] if ch == "\\" else ch)
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif line.startswith("//", i):
            break
        elif line.startswith("/*", i):
            j = line.find("*/", i + 2)
            if j < 0:
                break
            i = j + 2
            continue
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _comment_line(line):
    return line.strip().startswith(("//", "/*", "*"))


def units(lines, c=True):
    """[(first, head, last)] of the top-level pieces of a file, in order: first is the line a
    piece starts on (its comment, when one sits directly above it), head its first line of code,
    last its last line. In C a piece is a function or a struct, union, enum or initializer
    (through the "}" at column 0 that closes it), a declaration or prototype (through its ";"),
    or a preprocessor line with its continuations; a comment with no code directly under it is a
    piece of its own (head == first). In any other file a piece is a run of non-blank lines.
    What "The code" shows of a file a lesson adds to: whole pieces, never half of one."""
    out, n, i = [], len(lines), 0
    if not c:
        while i < n:
            if not lines[i].strip():
                i += 1
                continue
            j = i
            while j + 1 < n and lines[j + 1].strip():
                j += 1
            out.append((i, i, j))
            i = j + 1
        return out
    while i < n:
        if not lines[i].strip():
            i += 1
            continue
        first = head = i
        if _col0(lines[i]) and lines[i].startswith(("//", "/*")):
            while head < n and lines[head].strip() and _comment_line(lines[head]):
                code = lines[head].split("/*", 1)
                if len(code) == 2 and "*/" not in code[1]:   # a /* block: on to the line that closes it
                    while head + 1 < n and "*/" not in lines[head + 1]:
                        head += 1
                    head += 1
                head += 1
            if head >= n or not lines[head].strip() or not _col0(lines[head]):
                out.append((first, first, min(head, n) - 1))     # a comment on its own
                i = head
                continue
        line = lines[head]
        if line.startswith("#"):
            last = head
            while last + 1 < n and lines[last].rstrip().endswith("\\"):
                last += 1
        elif not _col0(line) or LABEL.match(line.strip()):
            last = head                                         # code a piece of this shape does not cover
        else:
            last, k = head, head
            while k < n and k - head <= 8:
                code = code_part(lines[k])
                if code.endswith("{"):
                    last = next((m for m in range(k + 1, n) if lines[m].startswith("}")), k)
                    break
                if code.endswith(";") or (code.endswith("}") and code.count("{") == code.count("}")):
                    last = k
                    break
                k += 1
        out.append((first, head, last))
        i = last + 1
    return out


# ---------------------------------------------------------------- @from and @internal

class Block:
    """One @from (kind "from") or @internal (kind "internal") block in one file."""

    def __init__(self, path, kind, lesson, leader, start, alt, end):
        self.path = path
        self.kind = kind
        self.lesson = lesson        # None for @internal
        self.leader = leader
        self.start = start          # index of the @from / @internal line
        self.alt = alt              # index of the @else line, or None
        self.end = end              # index of the @end line

    @property
    def line(self):
        return self.start + 1


def scan_blocks(path, text):
    """(blocks, marks) of one file: its @from and @internal blocks, and {line index: lesson}
    for the lines that end in "@from NN.LL". Fail when the markers do not pair up."""
    blocks, marks, stack = [], {}, []
    for i, line in enumerate(text.split("\n")):
        if ws.BUILD_RE.match(line):
            stack.append(["build", i, None, None, None])
        elif FROM_RE.match(line):
            m = FROM_RE.match(line)
            stack.append(["from", i, m.group(2), m.group(1), None])
        elif INTERNAL_RE.match(line):
            stack.append(["internal", i, None, INTERNAL_RE.match(line).group(1), None])
        elif ELSE_RE.match(line):
            if not stack or stack[-1][0] != "from" or stack[-1][4] is not None:
                raise core.Fail(f"{path}:{i + 1}: @else outside a @from block")
            stack[-1][4] = i
        elif BLOCK_END_RE.match(line):
            if not stack:
                raise core.Fail(f"{path}:{i + 1}: @end with nothing open")
            kind, start, lesson, leader, alt = stack.pop()
            if kind != "build":
                blocks.append(Block(path, kind, lesson, leader, start, alt, i))
        else:
            m = LINE_FROM_RE.match(line)
            if m:
                marks[i] = m.group(2)
    if stack:
        raise core.Fail(f"{path}:{stack[-1][1] + 1}: @{stack[-1][0]} has no @end")
    return sorted(blocks, key=lambda b: b.start), marks


def unmark(line):
    """A line with its one-line "@from NN.LL" marker taken off."""
    m = LINE_FROM_RE.match(line)
    return EMPTY_COMMENT.sub("", m.group(1)) if m else line


def uncomment(line, leader):
    """A line of an @else part as code: its leader (and one space after it) taken out."""
    m = re.match(r"^(\s*)" + re.escape(leader) + r" ?(.*?)(\s*\*/)?$" if leader == "/*" else
                 r"^(\s*)" + re.escape(leader) + r" ?(.*)$", line)
    return m.group(1) + m.group(2) if m else line


def unmarked(lines):
    """Code as it stands at the end of every path: without @from and @internal markers, @else
    parts or @internal code. lines: a whole file, or a region's code."""
    try:
        blocks, marks = scan_blocks("", "\n".join(lines))
    except core.Fail:
        return list(lines)
    gone = set()
    for b in blocks:
        gone.update({b.start, b.end})
        if b.kind == "internal":
            gone.update(range(b.start, b.end + 1))
        elif b.alt is not None:
            gone.update(range(b.alt, b.end + 1))
    return [unmark(l) if i in marks else l for i, l in enumerate(lines) if i not in gone]


# ---------------------------------------------------------------- the project at a lesson

class Project:
    """One track's files and regions, read once; answers what stands at any lesson."""

    def __init__(self, track):
        self.track = track
        self.files = tree_files(track.root, hidden_files(track))
        try:
            explicit = dict(getattr(track.module, "FILES_FROM", {}) or {})
        except Exception:
            explicit = {}
        self.explicit = {k: v for k, v in explicit.items() if isinstance(k, str) and isinstance(v, str)}
        self.regions = {}
        self._text = {}
        try:
            for r in ws.scan_tree(track.module, track.root):
                self.regions.setdefault(r.path, []).append(r)
        except Exception:
            pass
        self.blocks = {}        # path -> [Block]
        self.marks = {}         # path -> {line index: lesson}
        self.block_errors = []
        for rel in self.files:
            try:
                data = self.text(rel)
            except OSError:
                continue
            if b"@from" not in data and b"@internal" not in data or b"\0" in data[:8192]:
                continue
            try:
                blocks, marks = scan_blocks(rel, data.decode("utf-8", errors="replace"))
            except core.Fail as e:
                self.block_errors.append(str(e))
                continue
            if blocks:
                self.blocks[rel] = blocks
            if marks:
                self.marks[rel] = marks

    def placed(self, rel):
        """The lesson FILES_FROM names for rel (an exact path wins over a glob), or None."""
        if rel in self.explicit:
            return self.explicit[rel]
        return next((v for k, v in self.explicit.items() if fnmatch.fnmatch(rel, k)), None)

    def intro(self, rel):
        """The lesson rel appears with on the core path (or its first extension's), or None if unplaced."""
        got = self.placed(rel)
        if got:
            return got
        ids = sorted({r.lesson for r in self.regions.get(rel, [])},
                     key=lambda l: (self.track.is_optional(l), core.lesson_key(l)))
        return ids[0] if ids else None

    def present(self, rel, at):
        if at is None:
            return True
        got = self.placed(rel)
        if got:
            return reached(self.track, got, at)
        regs = self.regions.get(rel)
        if not regs:
            return True                      # unplaced: shown throughout; check reports it
        return any(reached(self.track, r.lesson, at) for r in regs)

    def files_at(self, at):
        return [f for f in self.files if self.present(f, at)]

    def status(self, rel, at):
        """"new" when rel appears at lesson `at`, "changed" when `at` adds code to it, else None."""
        if at is None or not self.present(rel, at) or self.intro(rel) is None:
            return None                      # unplaced files are never new or changed
        before = previous(self.track, at, self.lesson_ids())
        if before is None or not self.present(rel, before):
            return "new"
        if any(r.lesson == at for r in self.regions.get(rel, [])) or at in self.marked(rel):
            return "changed"
        return None

    def marked(self, rel):
        """The lessons that @from markers in rel name."""
        return ({b.lesson for b in self.blocks.get(rel, []) if b.kind == "from"}
                | set(self.marks.get(rel, {}).values()))

    def lesson_ids(self):
        """Every lesson id the track mentions: lessons, regions, and FILES_FROM."""
        ids = {r.lesson for rs in self.regions.values() for r in rs}
        ids |= {lid for rel in set(self.blocks) | set(self.marks) for lid in self.marked(rel)}
        return ids | {v for v in self.explicit.values() if re.match(r"^\d\d\.\d\d$", v)}

    def whole(self, rel):
        """True for a file with no regions and no markers: shown whole, as the track has it."""
        return not self.regions.get(rel) and not self.blocks.get(rel) and not self.marks.get(rel)

    def text(self, rel):
        if rel not in self._text:
            with open(os.path.join(self.track.root, rel), "rb") as f:
                self._text[rel] = f.read()
        return self._text[rel]

    def lines_at(self, rel, at, limit=None):
        """(lines of the file, [indexes to show], {indexes of lesson `at`'s own code}) at lesson
        `at`. The indexes keep the file's own line numbers (index + 1)."""
        data = self.text(rel)[:limit] if limit else self.text(rel)
        text = data.decode("utf-8", errors="replace")
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        try:
            regions = ws.scan_text(rel, "\n".join(lines)) if rel in self.regions else []
        except core.Fail:
            regions = []
        try:
            blocks, marks = (scan_blocks(rel, "\n".join(lines))
                             if rel in self.blocks or rel in self.marks else ([], {}))
        except core.Fail:
            blocks, marks = [], {}
        hidden, band = set(), set()
        for b in blocks:
            hidden.update({b.start, b.end} | ({b.alt} if b.alt is not None else set()))
            if b.kind == "internal":
                hidden.update(range(b.start, b.end + 1))
                continue
            body_end = b.end if b.alt is None else b.alt
            if reached(self.track, b.lesson, at):
                if b.alt is not None:
                    hidden.update(range(b.alt, b.end + 1))
                if b.lesson == at:
                    band.update(range(b.start + 1, body_end))
            else:
                hidden.update(range(b.start, body_end + 1))
                for i in range(body_end + 1, b.end):
                    lines[i] = uncomment(lines[i], b.leader)
        for i, lid in marks.items():
            lines[i] = unmark(lines[i])
            if not reached(self.track, lid, at):
                hidden.add(i)
            elif lid == at:
                band.add(i)
        for r in regions:
            hidden.update(range(r.start, r.instr_end))
            hidden.add(r.end)
            if r.lesson == at:
                band.update(range(r.instr_end, r.end))
            if reached(self.track, r.lesson, at):
                continue
            span = definition_span(lines, r) if is_c(rel) else None
            if span and not any(reached(self.track, o.lesson, at) for o in regions if span[0] <= o.start and o.end <= span[1]):
                hidden.update(range(span[0], span[1] + 1))
            else:
                hidden.update(range(r.start, r.end + 1))
        shown = []
        for i in range(len(lines)):
            if i in hidden:
                continue
            # one blank line where code was left out between two blank lines, not two
            if not lines[i].strip() and shown and not lines[shown[-1]].strip() and shown[-1] != i - 1:
                continue
            shown.append(i)
        # no blank line left hanging inside braces where code was left out:
        # "{", (gone), "", ... or ..., "", (gone), "}"
        for k in range(len(shown) - 1, -1, -1):
            i = shown[k]
            if lines[i].strip() or k == 0 or k == len(shown) - 1:
                continue
            before, after = shown[k - 1], shown[k + 1]
            if ((lines[before].rstrip().endswith("{") and before != i - 1)
                    or (lines[after].strip().startswith("}") and after != i + 1)):
                del shown[k]
        while shown and not lines[shown[0]].strip():
            shown.pop(0)
        while shown and not lines[shown[-1]].strip():
            shown.pop()
        return lines, shown, band

    def content(self, rel, at):
        """The bytes of rel as it stands at lesson `at`: what materialize() writes for it."""
        if self.whole(rel):
            return self.text(rel)
        lines, shown, _band = self.lines_at(rel, at)
        return ("\n".join(lines[i] for i in shown) + "\n").encode("utf-8", errors="replace")

    def materialize(self, at, dest):
        """Write the project as it stands at lesson `at` (None: the end of the track) under dest,
        as the site shows it: the files there by then, each holding only what is reached.
        Returns the paths written, relative to dest."""
        out = []
        for rel in self.files_at(at):
            target = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(target) or dest, exist_ok=True)
            with open(target, "wb") as f:
                f.write(self.content(rel, at))
            shutil.copymode(os.path.join(self.track.root, rel), target)
            out.append(rel)
        return out

    def problems(self):
        """What `./learn check` reports about when files appear."""
        out = list(self.block_errors)
        ids = {l.id for l in self.track.lessons} | {r.lesson for rs in self.regions.values() for r in rs}
        for pattern, lid in self.explicit.items():
            if not re.match(r"^\d\d\.\d\d$", lid) or lid not in ids:
                out.append(f"FILES_FROM[{pattern!r}]: {lid!r} is not a lesson of this track")
            elif not any(f == pattern or fnmatch.fnmatch(f, pattern) for f in self.files):
                out.append(f"FILES_FROM[{pattern!r}]: matches no file")
        for f in self.files:
            got = self.placed(f)
            if got is None and not self.regions.get(f):
                out.append(f"{f}: no lesson introduces it (add it to FILES_FROM in track.py)")
            elif got:
                early = [r.lesson for r in self.regions.get(f, []) if not reached(self.track, got, r.lesson)]
                if early:
                    out.append(f"{f}: FILES_FROM says {got}, but {early[0]} already has code in it")
        for f in self.files:
            marked = [(b.line, b.lesson) for b in self.blocks.get(f, []) if b.kind == "from"]
            marked += [(i + 1, lid) for i, lid in self.marks.get(f, {}).items()]
            for n, lid in sorted(marked):
                if lid not in ids:
                    out.append(f"{f}:{n}: @from {lid}: not a lesson of this track")
                elif self.intro(f) and not self.present(f, lid):
                    out.append(f"{f}:{n}: @from {lid}, but the file only comes with {self.intro(f)}")
        return out
