"""Figures for kilo module 08, Undo and redo (lessons 08.01 to 08.04), an extension.

    python3 -B art/kilo/figs08.py [name-prefix ...]
                                       writes tracks/kilo/lessons/08-undo/figures/08.0N-*.svg

Every row, record, stack and number here is from a real run, checked against NOTES.md where it
states the same thing. The project at each lesson is written with ./learn files kilo --at 08.0N
and built with make, with TRACE_C put in a scratch copy first (trace_patch()): a function that
appends to $KILO_TRACE, after each record is made, after each record is put back or applied,
and before each screen is drawn, the rows of the file and every step on the undo and redo stacks
with its records (and, where the lesson has them, the cursor's two places, the saved point and the
byte count), and, from 08.03, the kind undoKey() gives each key. ./kilo runs on a pseudo-terminal
through the track's own fixture (edit() in tracks/kilo/track.py), on NOTES.md's notes.txt
(NOTES_TXT) on a 10 x 44 terminal, as NOTES.md captured its screens. The byte counts are the tree's
own build (tracks/kilo, copied and built with make), whose @internal undoCheck() logs the history's
count after every key when KILO_TEST_UNDO_LOG is set and takes its bound from KILO_TEST_UNDO_MAX,
as test 0804 and NOTES.md's measurements use it.

  08.01-records      the project at 08.01, NOTES.md's keys (Down, "and ", Enter, Backspace,
                     Backspace): the rows before and after three of them ("a", Enter in the middle
                     of the row, the first Backspace at the start of a row) and the records each made
  08.01-hooks        the project at 08.01's own source: which row functions each key function
                     calls, and every undoSave() in them (five row functions and the cut in
                     editorInsertNewline); editorOpen's U.off around its reading loop
  08.01-undo-enter   stepped: the same run: the rows before Enter and after it, and the rows after
                     each of the two records of Enter's step is put back, at the third Ctrl-Z
  08.02-swap         stepped: the project at 08.02, NOTES.md's keys, Ctrl-Z, Ctrl-R: the second
                     Backspace's one U_CHG record and its row, as the trace showed them each time
  08.02-two-stacks   stepped: the project at 08.02 on notes.txt: a, b, Ctrl-Z, Ctrl-Z, Ctrl-R, c:
                     both stacks after each key
  08.03-runs         the project at 08.03: the lesson's Run it, NOTES.md's keys, Ctrl-Z four times
                     (to "Nothing to undo"), then "so ", Down, Left three times, "and ": the kind
                     undoKey() gave each key, the steps and their records
  08.03-one-record   the tree's build: 60 characters typed into an empty row, as one step and with
                     Ctrl-L after each (60 steps): the bytes held, checked against NOTES.md
                     (Measurements: 57 and 5190)
  08.04-saved-point  stepped: the project at 08.04 on notes.txt: A, Ctrl-S, Ctrl-Z, Ctrl-R, then
                     Ctrl-Z and C: the stacks, the saved point and the status bar after each
  08.04-bound        the tree's build, test 0804's small bound: one Enter on an empty file is a step
                     of 56 bytes; with a bound of ten of them, 6 Enters, Ctrl-S, 6 more: the count,
                     the steps kept and the saved point after each key; and the real 8 MB: the
                     project at 08.04 on a row of 9 000 000 w's, X typed at its start, then Ctrl-Z
                     (NOTES.md, 08.04); the bytes that record needs are undoSave()'s sum, 24 for the
                     record, the row and its '\\0', 32 for the step

The maps, the cover and the icon are not made here (archmap.py, covers.py); covers.py draws the
cover from capture_cover() here.
"""
import functools
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import figlib  # noqa: E402
from figlib import Fig, write, fmt  # noqa: E402
import steps  # noqa: E402
from archmap import sane  # noqa: E402  the site's sanitizer keeps every element and attribute
from harness import core  # noqa: E402

figlib.LESSONS = os.path.join(ROOT, "tracks", "kilo", "lessons")
MOD = "08-undo"
TREE = os.path.join(ROOT, "tracks", "kilo")
NOTES = os.path.join(TREE, "NOTES.md")

NOTES_TXT = "undo keeps\nwhat each line was\nbefore it changed\n"
UP, DOWN, RIGHT, LEFT = "\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"
ENTER, BACKSPACE = "\r", "\x7f"
TYPES = {0: "U_CHG", 1: "U_INS", 2: "U_DEL"}
KINDS = {0: "other", 1: "typing", 2: "deleting"}


def ctrl(ch):
    return chr(ord(ch.upper()) & 0x1f)


CTRL_Z, CTRL_R, CTRL_S, CTRL_L = ctrl("z"), ctrl("r"), ctrl("s"), ctrl("l")
# NOTES.md's keys (08, "How the screens below were captured")
NOTES_KEYS = [("Down", DOWN), ("a", "a"), ("n", "n"), ("d", "d"), ("space", " "), ("Enter", ENTER),
              ("Backspace", BACKSPACE), ("Backspace", BACKSPACE)]


def notes_section(title):
    """The text of the section "### title" of NOTES.md's module 08 (to the next heading)."""
    with open(NOTES) as f:
        text = f.read()
    at = text.index("### " + title + "\n", text.index("## 08 Undo and redo"))
    end = re.search(r"\n#{2,3} ", text[at + 4:])
    return text[at:at + 4 + end.start()] if end else text[at:]


def flat(s):
    """NOTES.md's prose with its line breaks folded, to look for a phrase in it."""
    return " ".join(s.split())


def check_sample():
    """NOTES_TXT and NOTES_KEYS are NOTES.md's (08, "How the screens below were captured")."""
    block = notes_section("How the screens below were captured")
    assert "```\n" + NOTES_TXT + "```" in block, "notes.txt"
    assert "the keys Down, `and `, Enter, Backspace, Backspace" in flat(block)
    assert "on a 10x44 pseudo-terminal" in flat(block)


# ------------------------------------------------------------------ running the project

TRACE_C = r'''
/* figs08: the rows and the history, appended to $KILO_TRACE. */
void figsStep(FILE *fp, const char *name, struct undoStep *s) {
    int k;
    fprintf(fp,"%s %d"@CURSOR@"\n",name,s->numrec@CURSORARGS@);
    for (k = 0; k < s->numrec; k++) {
        if (s->rec[k].text) fprintf(fp," rec %d %d |%s|\n",s->rec[k].type,s->rec[k].at,s->rec[k].text);
        else fprintf(fp," rec %d %d -\n",s->rec[k].type,s->rec[k].at);
    }
}

void figsTrace(const char *what, struct undoStep *cur, int j) {
    char *path = getenv("KILO_TRACE");
    FILE *fp;
    int i;

    if (path == NULL || (fp = fopen(path,"a")) == NULL) return;
    fprintf(fp,"@ %s %d\n",what,j);
    for (i = 0; i < E.numrows; i++) fprintf(fp,"row %d |%s|\n",i,E.row[i].chars);
    for (i = 0; i < U.numundo; i++) figsStep(fp,"undo",&U.undo[i]);
    @REDO@
    if (cur) figsStep(fp,"cur",cur);
    fprintf(fp,"state open %d dirty %d cy %d cx %d@SAVED@\n",U.open,E.dirty,E.rowoff+E.cy,E.coloff+E.cx@SAVEDARGS@);
    fclose(fp);
}

'''


def trace_patch(src):
    """The (old, new) pairs that put figsTrace() into the project's kilo.c src, by what it has."""
    redo = "U.numredo" in src
    cursor = "row0, col0;" in src
    saved = "U.saved" in src
    c = TRACE_C.replace("@CURSOR@", '" c %d %d %d %d"' if cursor else "")
    c = c.replace("@CURSORARGS@", ",s->row0,s->col0,s->row1,s->col1" if cursor else "")
    c = c.replace("@REDO@", 'for (i = 0; i < U.numredo; i++) figsStep(fp,"redo",&U.redo[i]);' if redo else "")
    c = c.replace("@SAVED@", " saved %d bytes %zu" if saved else "")
    c = c.replace("@SAVEDARGS@", ",U.saved,U.bytes" if saved else "")
    head = "/* ============================== Undo and redo ============================= */\n"
    out = [(head, head + c),
           ("    s->rec = rec;\n", '    s->rec = rec;\n    figsTrace("save",NULL,-1);\n'),
           ("void editorRefreshScreen(void) {\n", 'void editorRefreshScreen(void) {\n    figsTrace("frame",NULL,-1);\n')]
    if redo:
        out += [("        undoApply(&s.rec[j]);\n", '        { undoApply(&s.rec[j]); figsTrace("undo",&s,j); }\n'),
                ("for (j = 0; j < s.numrec; j++) undoApply(&s.rec[j]);",
                 'for (j = 0; j < s.numrec; j++) { undoApply(&s.rec[j]); figsTrace("redo",&s,j); }')]
    else:
        out += [("        undoPut(&s.rec[j]);\n", '        { undoPut(&s.rec[j]); figsTrace("undo",&s,j); }\n')]
    if "U.kind = kind;" in src:
        out += [("    U.kind = kind;\n", '    U.kind = kind;\n    { FILE *fp = getenv("KILO_TRACE") ? '
                 'fopen(getenv("KILO_TRACE"),"a") : NULL; if (fp) { fprintf(fp,"@ key %d\\nkind %d\\n",c,kind); '
                 'fclose(fp); } }\n')]
    return out


_built = {}


def project(at):
    """The project at lesson `at`, written by ./learn files, with trace_patch() made to its
    kilo.c, and built."""
    if at not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="kilo-figs08-"), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "kilo", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        path = os.path.join(d, "kilo.c")
        with open(path) as f:
            src = f.read()
        for old, new in trace_patch(src):
            assert src.count(old) == 1, (at, old)
            src = src.replace(old, new)
        with open(path, "w") as f:
            f.write(src)
        subprocess.run(["make", "-s"], cwd=d, check=True)
        _built[at] = d
    return _built[at]


def tree():
    """The tree's own kilo (tracks/kilo, with its @internal test aids), copied and built."""
    if "tree" not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="kilo-figs08-"), "tree")
        os.makedirs(d)
        for fn in ("kilo.c", "lsp.c", "lsp.h", "json.c", "json.h", "script.c", "script.h", "api.h", "Makefile"):
            shutil.copy(os.path.join(TREE, fn), d)
        # module 09's Lua, which the tree's Makefile builds into liblua.a
        shutil.copytree(os.path.join(TREE, "lua"), os.path.join(d, "lua"),
                        ignore=shutil.ignore_patterns("*.o", "*.a", "lua", "luac"))
        subprocess.run(["make", "-s"], cwd=d, check=True)
        _built["tree"] = d
    return _built["tree"]


def source(at):
    """The project at `at`'s kilo.c as ./learn files writes it (no trace)."""
    d = tempfile.mkdtemp(prefix="kilo-figs08-src-")
    try:
        subprocess.run([os.path.join(ROOT, "learn"), "files", "kilo", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        with open(os.path.join(d, "kilo.c")) as f:
            return f.read()
    finally:
        shutil.rmtree(d, ignore_errors=True)


class Step:
    """One step as the trace showed it: its records [(type, at, text or None)], and the cursor's
    two places (row0, col0, row1, col1) where the lesson keeps them."""

    def __init__(self, numrec, cursor):
        self.numrec, self.cursor, self.recs = numrec, cursor, []


def parse_trace(path):
    """$KILO_TRACE as a list of events: {"what", "j", "rows", "undo", "redo", "cur", "state"}, or
    {"what": "key", "c", "kind"}."""
    events = []
    try:
        with open(path, encoding="latin-1") as f:
            lines = f.read().split("\n")
    except OSError:
        return events
    e = None
    for line in lines:
        if line.startswith("@ "):
            what, j = line[2:].split()
            e = {"what": what, "j": int(j), "rows": [], "undo": [], "redo": [], "cur": None, "state": {}}
            if what == "key":
                e["c"] = int(j)
            events.append(e)
        elif line.startswith("kind "):
            e["kind"] = int(line.split()[1])
        elif line.startswith("row "):
            m = re.match(r"row (\d+) \|(.*)\|$", line)
            assert int(m.group(1)) == len(e["rows"])
            e["rows"].append(m.group(2))
        elif re.match(r"(undo|redo|cur) ", line):
            w = line.split()
            cursor = tuple(int(x) for x in w[3:7]) if len(w) > 2 and w[2] == "c" else None
            s = Step(int(w[1]), cursor)
            if w[0] == "cur":
                e["cur"] = s
            else:
                e[w[0]].append(s)
            last = s
        elif line.startswith(" rec "):
            m = re.match(r" rec (\d) (-?\d+) (?:\|(.*)\||-)$", line)
            last.recs.append((TYPES[int(m.group(1))], int(m.group(2)), m.group(3)))
        elif line.startswith("state "):
            w = line.split()
            e["state"] = {w[i]: int(w[i + 1]) for i in range(1, len(w) - 1, 2)}
    return events


class Shot:
    """What a screen showed: its lines and the cursor."""

    def __init__(self, ed):
        self.lines = list(ed.lines)
        self.cursor = ed.cursor
        self.status = ed.status
        self.message = ed.message


def run(at, keys, text=NOTES_TXT, name="notes.txt", rows=10, cols=44, env=None, trace=True):
    """kilo at lesson `at` (or "tree": the tree's own build) on a rows x cols pseudo-terminal,
    on `name` holding text; keys a list of (label, bytes), each sent as one key (or a list of
    keys sent one by one) and waited for. Returns [(label, Shot, trace events since the key
    before)], the first entry ("open", the screen as opened). trace=False: no $KILO_TRACE."""
    root = tree() if at == "tree" else project(at)
    track = core.Track("kilo")
    t = core.TestContext(track, track.lessons[0], root=root)
    out = []
    try:
        tpath = os.path.join(t.tmp, "trace.log")
        e = dict(env or os.environ)
        e.pop("KILO_TRACE", None)
        if trace:
            e["KILO_TRACE"] = tpath
        ed = t.track.edit(t, text, name=name, rows=rows, cols=cols, env=e)
        seen = 0

        def take(label):
            nonlocal seen
            evs = parse_trace(tpath)
            out.append((label, Shot(ed), evs[seen:]))
            seen = len(evs)
        take("open")
        for label, k in keys:
            for one in (k if isinstance(k, list) else [k]):
                ed.keys(one)
            take(label)
    finally:
        t.cleanup()                         # kilo is stopped with its session
    return out


def last_frame(evs):
    """The last "frame" event of a key's trace: the state the screen after it was drawn from."""
    fr = [e for e in evs if e["what"] == "frame"]
    assert fr, "no frame"
    return fr[-1]


# ------------------------------------------------------------------ captures

@functools.cache
def capture_notes(at, extra=()):
    """NOTES.md's run at lesson `at`: the keys, then the keys in extra."""
    return run(at, NOTES_KEYS + list(extra))


@functools.cache
def capture_cover():
    """For the module's cover (covers.py): the project at 08.02, where every key is a step and
    Ctrl-R redoes, on notes.txt: Down, then a, n, d. The rows, and the undo stack: three steps of
    one U_CHG each. Then Ctrl-Z and Ctrl-R: the top record's text after each, to check the swap
    the cover draws."""
    cap = run("08.02", [("Down", DOWN), ("a", "a"), ("n", "n"), ("d", "d"), ("Ctrl-Z", CTRL_Z), ("Ctrl-R", CTRL_R)])
    fr = [last_frame(evs) for _, _, evs in cap]
    after, undone, redone = fr[4], fr[5], fr[6]
    assert [len(s.recs) for s in after["undo"]] == [1, 1, 1] and not after["redo"]
    top = after["undo"][-1].recs[0]
    assert top[:2] == ("U_CHG", 1) and undone["redo"][-1].recs[0][2] == after["rows"][1]
    assert undone["rows"][1] == top[2] and redone["rows"] == after["rows"]
    assert redone["undo"][-1].recs[0] == top
    return {"rows": after["rows"], "steps": [s.recs[0] for s in after["undo"]], "keys": ["a", "n", "d"]}


def undo_counts(log):
    out = []
    with open(log) as f:
        for line in f:
            w = line.split()
            out.append({w[i]: int(w[i + 1]) for i in range(0, len(w) - 1, 2)})
    return out


def tree_counts(text, keys, max_bytes=None, name="m.txt", rows=10, cols=44):
    """The tree's build with KILO_TEST_UNDO_LOG (and KILO_TEST_UNDO_MAX): the run, and the
    undo log's counts, one entry per key."""
    d = tempfile.mkdtemp(prefix="kilo-figs08-log-")
    try:
        log = os.path.join(d, "undo.log")
        env = dict(os.environ, KILO_TEST_UNDO_LOG=log)
        env.pop("KILO_TEST_UNDO_MAX", None)
        if max_bytes is not None:
            env["KILO_TEST_UNDO_MAX"] = str(max_bytes)
        shots = run("tree", keys, text=text, name=name, rows=rows, cols=cols, env=env)
        return shots, undo_counts(log)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def cleanup():
    """Remove the projects built for the captures."""
    for d in {os.path.dirname(p) for p in _built.values()}:
        shutil.rmtree(d, ignore_errors=True)
    _built.clear()


# ------------------------------------------------------------------ drawing

class F8(Fig):
    def bar(self, x, y, w, h, cls, rx=0):
        """A filled shape with no stroke."""
        self.add(f'<rect class="{cls}" x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(rx)}"/>')


def cwid(size):
    return size * 0.6


def mono(f, x, y, s, cls="t", size=11, weight=None):
    """s in monospace from x, each run of non-spaces at its own column (SVG collapses runs of
    spaces). Returns the x just past it."""
    cw = cwid(size)
    col = 0
    for word in s.split(" "):
        if word:
            f.text(x + col * cw, y, word, cls, size, weight=weight, mono=True)
        col += len(word) + 1
    return x + len(s) * cw


def space_marks(f, x, y, s, size, cls="m"):
    """A small open box on the baseline under each trailing space of s drawn from x: a space a
    reader must see."""
    cw = cwid(size)
    n = len(s) - len(s.rstrip(" "))
    for i in range(len(s) - n, len(s)):
        x0 = x + i * cw + cw * 0.18
        f.add(f'<path class="{cls}" d="M{fmt(x0)} {fmt(y - 3)} L{fmt(x0)} {fmt(y)} L{fmt(x0 + cw * 0.64)} {fmt(y)} '
              f'L{fmt(x0 + cw * 0.64)} {fmt(y - 3)}" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"/>')


def quoted(f, x, y, s, cls="t", size=11, weight=None):
    """s in double quotes, its trailing spaces marked. Returns the x just past it."""
    end = mono(f, x, y, '"' + s + '"', cls, size, weight)
    space_marks(f, x + cwid(size), y, s, size)
    return end


def wrap(s, width):
    out, line = [], ""
    for w in s.split():
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


def notes(f, x, y, s, width, cls="tm", size=10.5, lh=14):
    lines = wrap(s, width)
    for k, line in enumerate(lines):
        f.text(x, y + k * lh, line, cls, size)
    return y + len(lines) * lh


def rows_panel(f, x, y, rows, size=10.5, lh=15, accent=(), dim=(), cursor=None, label=True):
    """A file's rows, one under another, each with its index (E.row[i]) on the left; rows in
    accent drawn in the accent, rows in dim muted; cursor (row, col) as an outlined cell.
    Returns the y of the next row's baseline."""
    cw = cwid(size)
    for i, r in enumerate(rows):
        b = y + i * lh
        if label:
            f.text(x - 8, b, str(i), "tm", 9.5, "end", mono=True)
        cls = "ta" if i in accent else ("tm" if i in dim else "t")
        if i in accent:
            f.bar(x - 3, b - lh * 0.72, max(len(r), 1) * cw + 6, lh - 1.5, "af", 2)
        mono(f, x, b, r, cls, size)
        space_marks(f, x, b, r, size, "a" if i in accent else "m")
    if cursor is not None:
        r, c = cursor
        b = y + r * lh
        f.rect(x + c * cw - 0.5, b - lh * 0.72 + 1, cw + 1, lh - 3, "a", 1)
    return y + len(rows) * lh


def record_card(f, x, y, w, rec, cls="s f", tcls="t", size=10, used=False, index=None, h=34):
    """One record: its type and row on the first line, its text (in quotes, or "no text") on
    the second."""
    typ, at, text = rec
    f.rect(x, y, w, h, cls, 5, dash=used and cls.startswith("m"))
    hx = x + 8
    if index is not None:
        f.text(hx, y + 14, f"[{index}]", "tm", 9.5, mono=True)
        hx += 24
    f.text(hx, y + 14, f"{typ} at {at}", "ta" if cls.startswith("a") else tcls, size, weight=700, mono=True)
    if used:
        f.text(x + 8, y + 28, "used up: the row has its text", "tm", 9.5)
    elif text is None:
        f.text(x + 8, y + 28, "no text: the row was not there", "tm", 9.5)
    else:
        quoted(f, x + 8, y + 28, text, tcls, size)


def key_cap(f, x, y, label, w=None, cls="s f", tcls="t", size=10.5):
    """A key drawn as a key cap. Returns its width."""
    w = w or max(22, len(label) * size * 0.56 + 14)
    f.rect(x, y, w, 22, cls, 5)
    f.text(x + w / 2, y + 15, label, tcls, size, "middle", 600)
    return w


# ------------------------------------------------------------------ 08.01

def notes0801():
    """The run at 08.01, NOTES.md's keys then Ctrl-Z until "Nothing to undo", checked against
    NOTES.md's screens (08.01)."""
    cap = capture_notes("08.01", tuple([("Ctrl-Z", CTRL_Z)] * 8))
    text = notes_section("08.01 Remembering what a line was")
    block = flat(text)
    shots = [s for _, s, _ in cap]
    first = shots[len(NOTES_KEYS)]
    assert first.lines[1] == "andwhat each line was" and first.cursor == (1, 3), first.lines
    assert "|andwhat each line was" in text and "[cursor 2,4]" in text
    z = shots[len(NOTES_KEYS) + 1:]
    assert z[0].lines[1] == "and what each line was" and "Ctrl-Z 1: `and what each line was`" in block
    assert z[1].lines[1:3] == ["and", "what each line was"] and z[1].status.startswith("notes.txt - 4 lines (modified)")
    assert "Ctrl-Z 2: `and` and `what each line was` on two rows" in block
    assert [s.lines[1] for s in z[2:7]] == ["and what each line was", "andwhat each line was", "anwhat each line was",
                                            "awhat each line was", "what each line was"]
    assert z[7].message == "Nothing to undo" and z[7].cursor == (1, 3) and "|Nothing to undo" in text
    return cap


def made_by(frames, k):
    """The records key k made: the step it added to the undo stack (a key a step: 08.01, 08.02)."""
    before, after = frames[k - 1]["undo"], frames[k]["undo"]
    assert len(after) == len(before) + 1 and all(a.recs == b.recs for a, b in zip(before, after))
    return after[-1].recs


def records0801():
    cap = notes0801()
    keys = [lab for lab, _, _ in cap]
    frames = [last_frame(evs) for _, _, evs in cap]
    cases = [(keys.index("a"), "a", "a character typed"),
             (keys.index("Enter"), "Enter", "in the middle of row 1"),
             (keys.index("Backspace"), "Backspace", "at the start of row 2")]
    assert made_by(frames, cases[0][0]) == [("U_CHG", 1, "what each line was")]
    assert [r[:2] for r in made_by(frames, cases[1][0])] == [("U_INS", 2), ("U_CHG", 1)]
    assert [r[:2] for r in made_by(frames, cases[2][0])] == [("U_CHG", 1), ("U_DEL", 2)]

    f = F8("f0801a", "Three keys at 08.01 and the records each one makes, in the order they are made: a "
           "character typed, Enter in the middle of a row, Backspace at the start of one", 344)
    f.text(24, 22, "kilo at 08.01 on notes.txt, keys Down, \"and \", Enter, Backspace: three of them, with the "
           "records each made", "tm", 11)
    XK, XB, XA, XR, WR = 24, 132, 296, 450, 166
    f.text(XK, 48, "the key", "tm", 10.5)
    f.text(XB, 48, "the rows before", "tm", 10.5)
    f.text(XA, 48, "the rows after", "tm", 10.5)
    f.text(XR, 48, "its records, in order", "tm", 10.5)
    y = 60
    for k, label, sub in cases:
        recs = made_by(frames, k)
        before, after = frames[k - 1], frames[k]
        f.line(24, y, 616, y, "m")
        y += 10
        key_cap(f, XK, y, label, cls="a af", tcls="ta")
        f.text(XK, y + 38, sub, "tm", 10)
        kept = {at for typ, at, _ in recs if typ != "U_INS"}
        changed = {at for typ, at, _ in recs if typ != "U_DEL"}
        cur = (before["state"]["cy"], before["state"]["cx"])
        rows_panel(f, XB + 10, y + 12, before["rows"], 10, accent=kept, cursor=cur)
        rows_panel(f, XA + 10, y + 12, after["rows"], 10, accent=changed)
        for j, rec in enumerate(recs):
            record_card(f, XR, y - 2 + j * 38, WR, rec, "a af", index=j)
        y += max(len(before["rows"]), len(after["rows"]), len(recs) * 2.55) * 15 + 6
    notes(f, 24, y + 14, "In the accent: before, the rows the records keep; after, the rows the key changed or "
          "made. The outlined cell is the cursor; a mark under a space, a space at the end of a row.", 104,
          "tm", 10.5)
    return f


def func_body(src, name):
    m = re.search(r"^\w[\w \*]*\b" + name + r"\([^)]*\) \{\n(.*?)^\}", src, re.S | re.M)
    assert m, name
    return m.group(1)


ROWF = ["editorRowInsertChar", "editorInsertRow", "editorDelRow", "editorRowAppendString", "editorRowDelChar"]
KEYF = ["editorInsertChar", "editorInsertNewline", "editorDelChar"]


@functools.cache
def hooks_source():
    """From kilo.c at 08.01: which row functions each key function calls, the record each row
    function makes, and the cut; checked against NOTES.md ("Hooks in core code")."""
    src = source("08.01")
    calls = {k: [r for r in ROWF if re.search(r"\b" + r + r"\(", func_body(src, k))] for k in KEYF}
    assert calls == {"editorInsertChar": ["editorRowInsertChar", "editorInsertRow"],
                     "editorInsertNewline": ["editorInsertRow"],
                     "editorDelChar": ["editorDelRow", "editorRowAppendString", "editorRowDelChar"]}, calls
    saves = {r: re.findall(r"undoSave\((U_\w+),", func_body(src, r)) for r in ROWF}
    assert all(len(v) == 1 for v in saves.values()), saves
    cut = re.findall(r"undoSave\((U_\w+),(\w+)\);\s*/\* the row is cut here", func_body(src, "editorInsertNewline"))
    assert cut == [("U_CHG", "filerow")], cut
    assert sum(len(re.findall(r"undoSave\(U_", func_body(src, k))) for k in KEYF) == 1
    assert len(re.findall(r"^\s+undoSave\(U_", src, re.M)) == 6        # five row functions, one cut
    assert re.search(r"U\.off = 1;.*editorInsertRow\(.*U\.off = 0;", func_body(src, "editorOpen"), re.S)
    keys = func_body(src, "editorProcessKeypress")
    assert re.search(r"case ENTER:.*?\n\s+editorInsertNewline\(\);", keys)
    assert re.search(r"case BACKSPACE:.*?\n\s+case CTRL_H:.*?\n\s+case DEL_KEY:\n\s+editorDelChar\(\);", keys)
    assert re.search(r"default:.*?editorInsertChar\(c\);", keys, re.S)
    hooks = flat(notes_section("Hooks in core code"))
    assert "`editorInsertRow`, after its `at > E.numrows` guard: `undoSave(U_INS,at);`" in hooks
    assert "every change to the text goes through those five functions and the one cut in editorInsertNewline" in hooks
    return calls, {r: v[0] for r, v in saves.items()}


def hooks0801():
    calls, saves = hooks_source()
    f = F8("f0801b", "The three key functions that edit, the five row functions they call, and the six places a "
           "record is made: one in each row function, and the cut in editorInsertNewline", 272)
    f.text(24, 22, "kilo.c at 08.01: who calls whom, and where undoSave() keeps a record (each accent mark)",
           "tm", 11)
    size = 9.5
    cw = cwid(size)
    pad, gap = 8, 6
    widths = [len(r) * cw + 2 * pad for r in ROWF]
    x0 = 24 + (592 - sum(widths) - gap * (len(ROWF) - 1)) / 2
    RY, RH = 160, 42

    def mark(x, y, typ, tail=""):
        """An accent mark: a dot and the record undoSave() keeps there, centred on x."""
        w = (len(typ) + len(tail)) * cwid(9.5) + 9
        f.circle(x - w / 2 + 2.5, y - 3.3, 2.6, "a fa")
        f.text(x - w / 2 + 9, y, typ + tail, "ta", 9.5, weight=700, mono=True)
    box = {}
    x = x0
    for r, w in zip(ROWF, widths):
        box[r] = (x, w)
        f.rect(x, RY, w, RH, "s f", 6)
        f.text(x + w / 2, RY + 17, r, "t", size, "middle", 600, mono=True)
        mark(x + w / 2, RY + 33, saves[r])
        x += w + gap
    KY, KH = 50, 40
    subs = {"editorInsertChar": "the default case", "editorInsertNewline": "Enter",
            "editorDelChar": "Backspace, Ctrl-H, Delete"}
    kbox = {}
    for k in KEYF:
        w = len(k) * cwid(11) + 30
        xs = [box[r][0] for r in calls[k]] + [box[r][0] + box[r][1] for r in calls[k]]
        kbox[k] = ((min(xs) + max(xs)) / 2 - w / 2, w)
    order = sorted(KEYF, key=lambda k: kbox[k][0])
    for a, b in zip(order, order[1:]):
        ax, aw = kbox[a]
        bx, bw = kbox[b]
        if ax + aw + 14 > bx:
            kbox[b] = (ax + aw + 14, bw)
    for k in KEYF:
        x, w = kbox[k]
        h = KH + (14 if k == "editorInsertNewline" else 0)
        f.rect(x, KY, w, h, "s fs", 6)
        f.text(x + w / 2, KY + 17, k, "t", 11, "middle", 700, mono=True)
        f.text(x + w / 2, KY + 31, subs[k], "tm", 9.5, "middle")
        if k == "editorInsertNewline":
            # the cut: it keeps the row itself, just before it cuts it by hand
            mark(x + w / 2, KY + 46, "U_CHG", " the cut")
        n = len(calls[k])
        for i, r in enumerate(calls[k]):
            rx, rw = box[r]
            sx = x + w / 2 + (i - (n - 1) / 2) * min(30, (w - 20) / max(n - 1, 1))
            f.line(sx, KY + h + 1, rx + rw / 2, RY - 2, "s", arrow=True)
    y = RY + RH + 24
    y = notes(f, 24, y, "Each keeps its record first, then changes the row. Enter in the middle of a row makes "
              "two records (U_INS of the new row, then U_CHG at the cut), a join two (U_CHG of the row above, "
              "then U_DEL).", 104, "tm", 10.5)
    notes(f, 24, y + 6, "editorOpen() reads the file through editorInsertRow() too, with U.off = 1: no record "
          "of that.", 104, "tm", 10.5)
    return f


def undo_enter0801():
    cap = notes0801()
    keys = [lab for lab, _, _ in cap]
    frames = [last_frame(evs) for _, _, evs in cap]
    k = keys.index("Enter")
    before, after = frames[k - 1], frames[k]
    recs = made_by(frames, k)
    # the third Ctrl-Z takes Enter's step back (the first two take the Backspaces')
    z3 = [i for i, lab in enumerate(keys) if lab == "Ctrl-Z"][2]
    assert frames[z3 - 1]["rows"] == after["rows"], "the rows before the third Ctrl-Z are as Enter left them"
    puts = [e for e in cap[z3][2] if e["what"] == "undo"]
    assert [e["j"] for e in puts] == [1, 0] and [r[:2] for r in puts[0]["cur"].recs] == [r[:2] for r in recs]
    assert puts[1]["rows"] == before["rows"]

    f = F8("f0801c", "Enter in the middle of a row makes one step of two records; Ctrl-Z puts them back last "
           "to first: the U_CHG gives the row its text back, then the U_INS deletes the row it inserted", 176)
    f.text(24, 22, "kilo at 08.01 on notes.txt: Enter in the middle of row 1, and the Ctrl-Z that takes it back",
           "tm", 11)
    XR, YR, LH, SZ = 44, 72, 18, 11.5
    XS, WS = 340, 276
    f.text(24, 50, "the rows", "tm", 10.5)
    f.text(XS, 50, "Enter's step: its records, in the order they were made", "tm", 10.5)

    def step_cards(state):
        """state per record: None (not made yet), "made", "applying", "used"."""
        if state[0] is None:
            f.rect(XS, 60, WS, 72, "m f", 6, dash=True)
            f.text(XS + WS / 2, 100, "no step yet", "tm", 10.5, "middle")
            return
        for j, (rec, st) in enumerate(zip(recs, state)):
            y = 60 + j * 40
            if st == "applying":
                record_card(f, XS, y, WS, rec, "a af", index=j, used=rec[0] == "U_CHG")
            elif st == "used":
                record_card(f, XS, y, WS, rec, "m f", "tm", index=j, used=True)
            else:
                record_card(f, XS, y, WS, rec, "s f", index=j)
        f.text(XS, 158, "Ctrl-Z applies them last to first: [1], then [0].", "tm", 10.5)

    with steps.step(f, "Before Enter: \"and \" typed at the start of row 1, and the cursor just after it."):
        rows_panel(f, XR, YR, before["rows"], SZ, LH, cursor=(before["state"]["cy"], before["state"]["cx"]))
        step_cards([None])
    with steps.step(f, "Enter: editorInsertRow() keeps U_INS of row 2, the row it is about to insert; then "
                       "editorInsertNewline() keeps U_CHG of row 1 just before it cuts it. One key, one step, "
                       "two records."):
        rows_panel(f, XR, YR, after["rows"], SZ, LH, accent={1, 2},
                   cursor=(after["state"]["cy"], after["state"]["cx"]))
        step_cards(["made", "made"])
    with steps.step(f, "Ctrl-Z (the third here: the first two took back the Backspaces) starts with the last "
                       "record: U_CHG gives row 1 its text back. For a moment the rest of the line is in the "
                       "file twice."):
        rows_panel(f, XR, YR, puts[0]["rows"], SZ, LH, accent={1})
        step_cards(["made", "applying"])
    with steps.step(f, "Then U_INS: the row it inserted, row 2, is deleted, and the text is as it was before "
                       "Enter. At 08.01 the step is then freed: nothing redoes it yet."):
        rows_panel(f, XR, YR, puts[1]["rows"], SZ, LH)
        f.text(XR, YR + 3 * LH + 4, "row 2, \"what each line was\", deleted", "ta", 10.5)
        step_cards(["applying", "used"])
    return f


# ------------------------------------------------------------------ 08.02

def notes0802():
    """The run at 08.02, NOTES.md's keys, then Ctrl-Z and Ctrl-R."""
    cap = capture_notes("08.02", (("Ctrl-Z", CTRL_Z), ("Ctrl-R", CTRL_R)))
    block = flat(notes_section("08.02 Redo: a record that undoes itself"))
    assert "Ctrl-R 1 to 7 give the screens back in the other order" in block
    return cap


def swap0802():
    cap = notes0802()
    frames = [last_frame(evs) for _, _, evs in cap]
    bs2, z, r = len(NOTES_KEYS), len(NOTES_KEYS) + 1, len(NOTES_KEYS) + 2
    assert [lab for lab, _, _ in cap][bs2:] == ["Backspace", "Ctrl-Z", "Ctrl-R"]
    states = []
    for i, where in ((bs2, "undo"), (z, "redo"), (r, "undo")):
        st = frames[i][where][-1]
        assert len(st.recs) == 1 and st.recs[0][:2] == ("U_CHG", 1), st.recs
        states.append((frames[i]["rows"], st.recs[0][2], where))
    (rows0, rec0, _), (rows1, rec1, _), (rows2, rec2, _) = states
    assert rec0 == rows1[1] == rec2 and rec1 == rows0[1] == rows2[1], states
    assert cap[z][1].lines[1] == "and what each line was" and cap[r][1].lines[1] == "andwhat each line was"
    diff = [i for i, (a, b) in enumerate(zip(rec0, rows0[1] + " ")) if a != b][0]

    f = F8("f0802a", "One U_CHG record and its row: Ctrl-Z swaps their texts, and Ctrl-R, applying the same "
           "record again, swaps them back", 236)
    f.text(24, 22, "kilo at 08.02 on notes.txt, after Down, \"and \", Enter, Backspace, Backspace: the last key's "
           "step, one record", "tm", 11)
    SZ = 12.5
    cw = cwid(SZ)
    BW = 250
    XL, XR_, Y = 24, 366, 74

    def panel(x, title, sub, text, cls):
        f.text(x, Y - 12, title, "t", 12, weight=700)
        f.text(x + BW, Y - 12, sub, "tm", 10.5, "end")
        f.rect(x, Y, BW, 46, cls, 7)
        tx = x + 14
        if text[diff] == " ":           # the space one text has and the other has not
            f.bar(tx + (diff + 1) * cw - 1, Y + 14, cw + 2, 19, "af", 2)
            space_marks(f, tx + cwid(SZ), Y + 29, text[:diff + 1], SZ, "a")
        quoted(f, tx, Y + 29, text, "t", SZ)

    def swap_arrows(label):
        a, b = XL + BW + 8, XR_ - 8
        f.path(f"M{fmt(b)} {fmt(Y + 14)} L{fmt(a)} {fmt(Y + 14)}", "a", arrow=True)
        f.path(f"M{fmt(a)} {fmt(Y + 32)} L{fmt(b)} {fmt(Y + 32)}", "a", arrow=True)
        f.text((a + b) / 2, Y + 64, label, "ta", 11.5, "middle", 700)

    def frame(rows, rec, where, label=None):
        panel(XL, "E.row[1]", "the row", rows[1], "s f")
        panel(XR_, "U_CHG at 1", f"on the {where} stack", rec, "a af")
        if label:
            swap_arrows(label)
    with steps.step(f, "After the second Backspace: its step is one record, U_CHG of row 1, holding the row "
                       "as it was, \"and what each line was\". The row is \"andwhat each line was\"."):
        frame(rows0, rec0, "undo")
        f.text(XL, Y + 82, "the record keeps what the row was; the row has the change", "tm", 10.5)
    with steps.step(f, "Ctrl-Z: undoApply() takes the row's text into the record, then puts the record's text "
                       "in the row. The two texts have changed places. The record is still U_CHG, and its step "
                       "goes on the redo stack."):
        frame(rows1, rec1, "redo", "Ctrl-Z")
        f.text(XL, Y + 82, "the record now keeps what Ctrl-Z took: the change itself", "tm", 10.5)
    with steps.step(f, "Ctrl-R applies the same record again: the same swap. The row has the change back, the "
                       "record what the row was, and the step goes back on the undo stack, as before Ctrl-Z."):
        frame(rows2, rec2, "undo", "Ctrl-R")
        f.text(XL, Y + 82, "as before Ctrl-Z: undo and redo are one act, applying a record", "tm", 10.5)
    notes(f, 24, 196, "The other two types change too as they are applied: U_INS deletes its row and becomes "
          "U_DEL with that row's text; U_DEL inserts its text and becomes U_INS.", 104, "tm", 10.5)
    return f


def stack_card(f, x, y, w, step, cls="s f", tcls="t", label=None):
    rec = step.recs[0]
    f.rect(x, y, w, 30, cls, 5, dash=cls.startswith("m"))
    f.text(x + 8, y + 13, f"{rec[0]} at {rec[1]}", "ta" if cls.startswith("a") else tcls, 9.5, weight=700,
           mono=True)
    quoted(f, x + 8, y + 25, rec[2], tcls, 9.5)
    if label:
        f.text(x + w - 8, y + 13, label, "ta" if cls.startswith("a") else "tm", 9.5, "end")


def two_stacks0802():
    keys = [("a", "a"), ("b", "b"), ("Ctrl-Z", CTRL_Z), ("Ctrl-Z", CTRL_Z), ("Ctrl-R", CTRL_R), ("c", "c")]
    cap = run("08.02", keys)
    frames = [last_frame(evs) for _, _, evs in cap]
    for fr in frames:
        assert all(len(s.recs) == 1 for s in fr["undo"] + fr["redo"])
    sizes = [(len(fr["undo"]), len(fr["redo"])) for fr in frames]
    assert sizes == [(0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (1, 1), (2, 0)], sizes
    assert frames[-1]["rows"][0] == "aucndo keeps" and cap[-1][1].cursor == (0, 3)

    f = F8("f0802b", "The undo stack and the redo stack as a, b, Ctrl-Z, Ctrl-Z, Ctrl-R and c are pressed: "
           "Ctrl-Z moves a step from one to the other, Ctrl-R moves it back, and a new edit empties the redo "
           "stack", 236)
    f.text(24, 22, "kilo at 08.02 on notes.txt, row 0: every key a step; each step here is one record", "tm", 11)
    XU, XD, SW_, BASE = 64, 352, 224, 176
    f.text(XU, BASE + 22, "the undo stack: Ctrl-Z takes its top", "tm", 10.5)
    f.text(XD, BASE + 22, "the redo stack: Ctrl-R takes its top", "tm", 10.5)
    f.line(XU - 8, BASE + 6, XU + SW_ + 8, BASE + 6, "s")
    f.line(XD - 8, BASE + 6, XD + SW_ + 8, BASE + 6, "s")
    captions = [
        "a: undoSave() keeps row 0 as it was, \"undo keeps\", in a new step on the undo stack.",
        "b: another step, keeping \"aundo keeps\". The redo stack is empty.",
        "Ctrl-Z: the top step comes off the undo stack, is applied (its record now holds \"abundo keeps\") and "
        "goes on the redo stack.",
        "Ctrl-Z again: the next step moves too. On the redo stack the step undone last is on top.",
        "Ctrl-R: the top of the redo stack is applied and moves back to the undo stack: the a is back.",
        "c: a new edit. Its record opens a new step, and undoSave() frees the redo stack first: the b can never "
        "be redone. (At 08.02 undo and redo leave the cursor where b left it, so the c goes in after \"au\".)",
    ]
    for i, (lab, cap_) in enumerate(zip([k for k, _ in keys], captions), 1):
        fr, prev = frames[i], frames[i - 1]
        with steps.step(f, cap_):
            key_cap(f, 24, 40, lab, cls="a af", tcls="ta")
            f.text(110, 56, "E.row[0]", "tm", 10.5)
            rows_panel(f, 170, 56, fr["rows"][:1], 12, label=False, cursor=(0, fr["state"]["cx"]))
            moved = None
            if lab == "Ctrl-Z":
                moved = ("redo", len(fr["redo"]) - 1)
            elif lab == "Ctrl-R":
                moved = ("undo", len(fr["undo"]) - 1)
            elif fr["undo"]:
                moved = ("undo", len(fr["undo"]) - 1)
            for side, x in (("undo", XU), ("redo", XD)):
                for j, st in enumerate(fr[side]):
                    hot = moved == (side, j)
                    stack_card(f, x, BASE - (j + 1) * 36, SW_, st, "a af" if hot else "s f")
            if lab == "c" and prev["redo"]:
                for j, st in enumerate(prev["redo"]):
                    stack_card(f, XD, BASE - (j + 1) * 36, SW_, st, "m f", "tm", "freed")
    return f


# ------------------------------------------------------------------ 08.03

def key_steps(cap):
    """For each key of a run at 08.03 or later: (label, kind, step) where step is the number of
    the step its edits went into (1 = the oldest), or None (a key that closed the open step and
    made no record). Kinds are what undoKey() gave the key, from the trace."""
    out = []
    for i, (lab, _, evs) in enumerate(cap[1:], 1):
        kinds = [e["kind"] for e in evs if e["what"] == "key"]
        assert len(kinds) == 1, (lab, kinds)
        fr = last_frame(evs)
        st = fr["state"]
        out.append((lab, KINDS[kinds[0]], len(fr["undo"]) if st["open"] else None))
    return out


SECOND_KEYS = [("s", "s"), ("o", "o"), ("space", " "), ("Down", DOWN), ("Left", LEFT), ("Left", LEFT),
               ("Left", LEFT), ("a", "a"), ("n", "n"), ("d", "d"), ("space", " ")]


def runs0803():
    # 08.03's Run it: NOTES.md's keys, Ctrl-Z until "Nothing to undo", then its second half
    a = capture_notes("08.03", tuple([("Ctrl-Z", CTRL_Z)] * 4 + SECOND_KEYS))
    ka = key_steps(a[:9])
    kb = key_steps([a[12]] + a[13:])
    assert a[12][1].message == "Nothing to undo", a[12][1].message
    assert [k for _, k, _ in ka] == ["other", "typing", "typing", "typing", "typing", "other", "deleting",
                                     "deleting"], ka
    assert [k for _, k, _ in kb] == ["typing"] * 3 + ["other"] * 4 + ["typing"] * 4, kb
    assert [s for _, _, s in ka] == [None, 1, 1, 1, 1, 2, 3, 3] and \
        [s for _, _, s in kb] == [1, 1, 1, None, None, None, None, 2, 2, 2, 2], (ka, kb)
    block = flat(notes_section("08.03 One Ctrl-Z, one thought: steps"))
    assert "Three steps: `and ` (typing), Enter (other), the two Backspaces (deleting)." in block
    recs_a = [len(s.recs) for s in last_frame(a[8][2])["undo"]]
    end = last_frame(a[-1][2])
    recs_b = [len(s.recs) for s in end["undo"]]
    assert recs_a == [1, 2, 3] and recs_b == [1, 1], (recs_a, recs_b)
    # the second half, as the lesson and NOTES.md (Screens the lessons show) have it: a U_CHG of
    # row 1 keeping "what each line was", then one of row 2 keeping "before it changed"
    assert end["rows"][1:3] == ["so what each line was", "and before it changed"], end["rows"]
    assert [r for s in end["undo"] for r in s.recs] == [("U_CHG", 1, "what each line was"),
                                                        ("U_CHG", 2, "before it changed")]
    assert "`so `, Down, Left three times, `and ` gives `so what each line was` and `and before it changed`" \
        in flat(notes_section("Added by the lesson writer (2026-11-24)"))

    f = F8("f0803a", "Keys on a time line, each with the kind undoKey() gives it, and the steps they make: a step "
           "is a run of keys of one kind, and any other key ends it", 288)
    f.text(24, 22, "kilo at 08.03: the kind undoKey() gives each key, and the steps on the undo stack", "tm", 11)
    def line(y, title, keys, recs, total, x=24, gap=10):
        f.text(24, y, title, "t", 11.5, weight=700)
        f.text(616, y, total, "ta", 11.5, "end", 700)
        spans = {}
        for lab, kind, step in keys:
            label = {"space": "space"}.get(lab, lab)
            w = max(34, len(label) * 10.5 * 0.56 + 14)
            hot = step is not None
            key_cap(f, x, y + 40, label, w, "s f" if hot else "m f", "t" if hot else "tm")
            f.text(x + w / 2, y + 76, kind, "ta" if kind != "other" else "tm", 9.5, "middle", 600)
            if step is not None:
                lo, hi = spans.get(step, (x, x + w))
                spans[step] = (min(lo, x), max(hi, x + w))
            else:
                f.text(x + w / 2, y + 30, "no step", "tm", 9, "middle")
            x += w + gap
        for step, (lo, hi) in spans.items():
            f.brace_h(lo + 1, hi - 1, y + 33, "a", up=True)
            n = recs[step - 1]
            f.text((lo + hi) / 2, y + 22, f"step {step}: {n} record{'s' if n != 1 else ''}", "ta", 10, "middle", 600)
    line(48, "Down, \"and \", Enter, Backspace, Backspace on notes.txt", ka, recs_a,
         f"{len(ka)} keys, {len(recs_a)} steps")
    line(160, "then, after Ctrl-Z to \"Nothing to undo\": \"so \", Down, Left three times, \"and \"", kb, recs_b,
         f"{len(kb)} keys, {len(recs_b)} steps")
    notes(f, 24, 266, "undoKey(c), before each key acts, closes the open step when the key is \"other\" or of "
          "another kind than the keys before it. A key that closes it and changes nothing makes no step.",
          104, "tm", 10.5)
    return f


def one_record0803():
    _, one = tree_counts("\n", [("type", "x" * 60)])
    _, many = tree_counts("\n", [("type", ("x" + CTRL_L) * 60)])
    b1, b60 = one[-1]["bytes"], many[-1]["bytes"]
    assert (one[-1]["undo"], one[-1]["records"]) == (1, 1) and (many[-1]["undo"], many[-1]["records"]) == (60, 60)
    m = flat(notes_section("Measurements"))
    lim = flat(notes_section("Limits"))
    assert f"as one step (a run of typing, 08.03), {b1} bytes held: one step (32), one record (24) and the " \
           "empty row it kept (1)" in m, b1
    assert f"{b60} bytes: 60 steps and records (3360), and the row as it was before each character, 1 to 60 " \
           "bytes with its '\\0' (1830)" in m, b60
    assert "plus 24 bytes per record (sizeof struct undoRecord) and 32 per step (sizeof struct undoStep)" in lim
    STEP, REC = 32, 24
    assert b1 == STEP + REC + 1 and b60 == 60 * (STEP + REC) + sum(range(1, 61))

    f = F8("f0803b", f"The bytes the history holds after a line of 60 characters is typed into an empty row: "
           f"{b1} as one step of one record, {b60} as 60 steps", 214)
    f.text(24, 22, "the bytes kilo's history holds after the last key, a line of 60 characters typed into an empty "
           "row", "tm", 11)
    X0, W = 24, 560
    scale = W / b60
    f.text(X0, 56, "60 characters as one step: a run of typing (08.03)", "t", 11.5, weight=700)
    f.rect(X0, 64, b1 * scale, 22, "a af", 2)
    f.text(X0 + b1 * scale + 10, 79, f"{b1} bytes", "ta", 12, weight=700, mono=True)
    f.text(X0 + b1 * scale + 82, 79, f"one step ({STEP}), one record ({REC}), the empty row it kept (1)", "tm", 10.5)
    f.text(X0, 120, "the same 60 with Ctrl-L after each: 60 steps (and any typing at 08.01 and 08.02)", "t",
           11.5, weight=700)
    s1 = 60 * (STEP + REC)
    f.rect(X0, 128, s1 * scale, 22, "s fs", 2)
    f.rect(X0 + s1 * scale, 128, (b60 - s1) * scale, 22, "a af", 2)
    f.text(X0 + s1 * scale / 2, 143, f"60 steps and records: {s1}", "t", 10.5, "middle")
    f.text(X0 + (s1 + (b60 - s1) / 2) * scale, 143, f"the rows: {b60 - s1}", "ta", 10.5, "middle")
    f.text(X0 + b60 * scale + 6, 143, f"{b60}", "ta", 12, weight=700, mono=True)
    f.text(X0, 168, "the row kept before each character: 1 byte (its '\\0'), then 2, ... up to 60: "
           "1 + 2 + ... + 60 = 1830", "tm", 10.5)
    f.text(X0, 196, "One record a run: the row is kept once, before its first change; undoSave() leaves the "
           "rest out.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 08.04

def saved_point0804():
    keys = [("A", "A"), ("Ctrl-S", CTRL_S), ("Ctrl-Z", CTRL_Z), ("Ctrl-R", CTRL_R), ("Ctrl-Z, C", [CTRL_Z, "C"])]
    cap = run("08.04", keys)
    frames = [last_frame(evs) for _, _, evs in cap]
    got = [(len(fr["undo"]), len(fr["redo"]), fr["state"]["saved"]) for fr in frames]
    assert got == [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 1, 1), (1, 0, 1), (1, 0, -1)], got
    mod = ["(modified)" in s.status for _, s, _ in cap]
    assert mod == [False, True, False, True, False, True], mod
    assert cap[2][1].message == "49 bytes written on disk"
    block = flat(notes_section("08.04 The saved point, and a bound on memory"))
    assert "|49 bytes written on disk" in block and "C, a new edit below the save" in block
    sp = flat(notes_section("The saved point (08.04)"))
    assert "After every undo and redo, E.dirty = (U.numundo != U.saved)" in sp

    f = F8("f0804a", "The undo stack and the saved point after typing A, saving, Ctrl-Z, Ctrl-R, and Ctrl-Z with C "
           "typed: the file is unmodified exactly when the stack stands at a saved point it can reach", 272)
    f.text(24, 22, "kilo at 08.04 on notes.txt, row 0: the stacks, U.saved, and the status bar kilo drew", "tm", 11)
    XS, WS, BASE, CH = 148, 210, 150, 34
    f.line(XS - 10, BASE + 4, XS + WS + 10, BASE + 4, "s")
    f.text(XS + WS / 2, BASE + 20, "the undo stack (redo, dashed, above it)", "tm", 10, "middle")
    captions = [
        "Opened: no steps, and the saved point at 0: the text is the file when the undo stack holds 0 steps.",
        "A typed: one step on the undo stack. 1 is not 0: \"(modified)\".",
        "Ctrl-S: the file is written, and the saved point is 1, the steps under the text on disk.",
        "Ctrl-Z: the step goes to the redo stack; the undo stack holds 0, the saved point is 1: \"(modified)\" "
        "is back.",
        "Ctrl-R: the step comes back, the stack is at 1 again, and \"(modified)\" goes.",
        "Ctrl-Z, then C: a new edit below the saved point. The redo stack, the way back to it, is freed, and "
        "U.saved is -1: out of reach. Modified until the next save, though the stack is 1 high again.",
    ]
    lastpos = 0
    for i, ((lab, shot, _), fr, cap_) in enumerate(zip(cap, frames, captions)):
        with steps.step(f, cap_):
            key_cap(f, 24, 44, "opened" if lab == "open" else lab, cls="a af", tcls="ta")
            for j, st in enumerate(fr["undo"]):
                stack_card(f, XS, BASE - (j + 1) * CH, WS, st, "s f")
            for j, st in enumerate(reversed(fr["redo"])):
                stack_card(f, XS, BASE - (len(fr["undo"]) + j + 1) * CH, WS, st, "m f", "tm", "redo")
            saved = fr["state"]["saved"]
            pos = saved if saved >= 0 else lastpos
            lastpos = pos
            y = BASE - pos * CH + (2 if pos == 0 else 0)
            live = saved >= 0
            f.path(f"M{fmt(XS - 22)} {fmt(y - 6)} L{fmt(XS - 12)} {fmt(y)} L{fmt(XS - 22)} {fmt(y + 6)} Z",
                   "a" if live else "m")
            if live:
                f.add(f'<path class="a fa" d="M{fmt(XS - 22)} {fmt(y - 6)} L{fmt(XS - 12)} {fmt(y)} '
                      f'L{fmt(XS - 22)} {fmt(y + 6)} Z" stroke-width="1.5" stroke-linejoin="round"/>')
            f.text(XS - 28, y - 2, "saved point", "ta" if live else "tm", 10, "end", 600)
            f.text(XS - 28, y + 11, f"U.saved {saved}", "ta" if live else "tm", 10, "end", mono=True)
            if not live:
                f.text(XS - 28, y + 24, "out of reach", "tm", 10, "end")
            n = len(fr["undo"])
            f.text(400, 98, "E.row[0]", "tm", 10.5)
            rows_panel(f, 460, 98, fr["rows"][:1], 11, label=False)
            f.text(400, 122, f"U.numundo {n}, U.saved {saved}", "t", 10.5, mono=True)
            f.text(400, 140, "E.dirty: modified" if fr["state"]["dirty"] else "E.dirty 0: not modified",
                   "ta", 10.5, weight=600)
            # the bottom of kilo's screen: the status bar in reverse video, and the message line
            size, cw = 9.6, cwid(9.6)
            x0, y0 = 30, 190
            f.rect(x0 - 7, y0 - 4, 44 * cw + 14, 2 * 15 + 8, "s fs", 6)
            f.bar(x0 - 1, y0 + 1, 44 * cw + 2, 13, "t", 1.5)
            mono(f, x0, y0 + 10.8, shot.status, "f", size)
            mono(f, x0, y0 + 25.8, shot.message, "t", size)
            f.text(x0 + 44 * cw + 16, y0 + 11, "the status bar", "tm", 10)
            f.text(x0 + 44 * cw + 16, y0 + 26, "and the message line", "tm", 10)
    notes(f, 24, 252, "After every undo and redo, E.dirty = (U.numundo != U.saved). Between them it counts "
          "changes, as in the core.", 104, "tm", 10.5)
    return f


def bound0804():
    _, one = tree_counts("", [("Enter", ENTER)], name="h.txt")
    step = one[-1]["bytes"]
    assert step == 32 + 24, step
    bound = 10 * step
    keys = [("Enter", ENTER)] * 6 + [("Ctrl-S", CTRL_S)] + [("Enter", ENTER)] * 6
    _, counts = tree_counts("", keys, max_bytes=bound, name="i.txt")
    assert len(counts) == len(keys), len(counts)
    last = counts[-1]
    assert (last["undo"], last["saved"], last["bytes"]) == (10, 4, bound), last
    assert all(c["bytes"] <= bound for c in counts)
    assert [c["undo"] for c in counts] == [1, 2, 3, 4, 5, 6, 6, 7, 8, 9, 10, 10, 10]
    assert [c["saved"] for c in counts] == [0] * 6 + [6] * 5 + [5, 4]
    # the real bound, NOTES.md's 08.04: a row of 9 000 000 w's, X at its start
    big = run("08.04", [("Down", DOWN), ("X", "X"), ("Ctrl-Z", CTRL_Z)], text="short\n" + "w" * 9000000 + "\n",
              name="big.txt", trace=False)
    assert big[2][1].message == "undo: change too big to remember" and big[2][1].lines[1].startswith("Xwww")
    assert big[3][1].message == "Nothing to undo" and big[3][1].lines[1].startswith("Xwww")
    nb = flat(notes_section("08.04 The saved point, and a bound on memory"))
    assert "A file of two rows, `short` and 9 000 000 w's, X typed at the start of the second row" in nb
    assert "and Ctrl-Z then says `Nothing to undo`; the X stays" in nb
    lim = notes_section("Limits")
    assert "| UNDO_MAX_BYTES | 8 MB (8388608) |" in lim
    MAX = 8388608
    need = 24 + 9000000 + 1 + 32

    f = F8("f0804b", f"The history against its bound: with a bound of {bound} bytes, twelve one-record steps keep "
           f"the newest ten, the two oldest dropped and the saved point taken down with them; and kilo's own 8 MB "
           f"against a row bigger than all of it", 318)
    f.text(24, 22, f"kilo with UNDO_MAX_BYTES made {bound}: Enter six times, Ctrl-S, Enter six times more, on an "
           f"empty file", "tm", 11)
    CW, X0, Y = 40, 90, 74
    for i in range(12):
        x = X0 + i * (CW + 4)
        dropped = i < 2
        y = Y + (18 if dropped else 0)
        f.rect(x, y, CW, 30, "m f" if dropped else "s f", 4, dash=dropped)
        f.text(x + CW / 2, y + 13, str(i + 1), "tm" if dropped else "t", 10.5, "middle", 700)
        f.text(x + CW / 2, y + 25, "U_INS", "tm", 8.5, "middle", mono=True)
    f.text(X0 - 8, Y + 30, "dropped,", "tm", 10, "end")
    f.text(X0 - 8, Y + 43, "oldest first", "tm", 10, "end")
    x2 = X0 + 2 * (CW + 4)
    f.brace_h(x2, X0 + 12 * (CW + 4) - 4, Y - 8, "a", up=True)
    f.text((x2 + X0 + 12 * (CW + 4)) / 2, Y - 16, f"kept: 10 steps x {step} bytes ({32} + {24}) = {bound}, the bound",
           "ta", 10.5, "middle", 700)
    sx = X0 + 6 * (CW + 4) - 2
    f.line(sx, Y - 2, sx, Y + 44, "a")
    f.text(sx + 6, Y + 46, "saved after step 6: U.saved was 6, now 4", "ta", 10.5)
    f.text(24, Y + 82, "Each new record past the bound drops the oldest steps first; the bytes held never pass "
           f"{bound}.", "tm", 10.5)
    # kilo's own bound against one row bigger than all of it
    y = 196
    f.text(24, y, "kilo's own bound, UNDO_MAX_BYTES: 8 MB", "t", 11.5, weight=700)
    scale = 560 / need
    f.rect(24, y + 10, MAX * scale, 16, "s fs", 2)
    f.text(30, y + 22, f"{MAX} bytes", "t", 10.5, mono=True)
    f.rect(24, y + 32, need * scale, 16, "a af", 2)
    f.text(30, y + 44, f"{need}: X on a row of 9 000 000 w's needs its record and a step", "ta", 10.5)
    mono(f, 24, y + 72, big[2][1].message, "ta", 11, 700)
    f.text(24 + len(big[2][1].message) * cwid(11) + 12, y + 72, "the change is made, and not remembered; "
           "Ctrl-Z: Nothing to undo", "tm", 10.5)
    f.text(24, y + 96, "So the history is emptied: no undo can lead back past a change it did not keep.", "tm", 10.5)
    return f


FIGS = [
    ("08.01-records", records0801, False),
    ("08.01-hooks", hooks0801, False),
    ("08.01-undo-enter", undo_enter0801, True),
    ("08.02-swap", swap0802, True),
    ("08.02-two-stacks", two_stacks0802, True),
    ("08.03-runs", runs0803, False),
    ("08.03-one-record", one_record0803, False),
    ("08.04-saved-point", saved_point0804, True),
    ("08.04-bound", bound0804, False),
]


def main():
    check_sample()
    only = sys.argv[1:]
    try:
        for name, fn, stepped in FIGS:
            if only and not any(name.startswith(o) for o in only):
                continue
            fig = fn()
            text = fig.svg()
            text.encode("ascii")
            sane(text, name)
            if stepped:
                print(name, "steps:", steps.check(text))
            print(write(MOD, name, fig))
    finally:
        cleanup()


if __name__ == "__main__":
    main()


