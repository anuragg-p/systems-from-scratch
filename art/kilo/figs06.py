"""Figures for kilo module 06, Syntax highlighting (lessons 06.01 to 06.05), an extension.

    python3 -B art/kilo/figs06.py      writes tracks/kilo/lessons/06-highlighting/figures/06.0N-*.svg

Every screen and every colour here is from a real run. The project at each lesson is written
with ./learn files kilo --at 06.0N and built with make; ./kilo runs on a pseudo-terminal of
16 x 56 through the track's own fixture (edit() in tracks/kilo/track.py), whose Screen keeps
the colour each cell was written in. The file is countdown.c (COUNTDOWN), the twelve lines the
lessons make with printf (PRINTF, checked here to make the same bytes).

  06.01-two-files  the same keys (Down 3, Right 8, Ctrl-A) in countdown.c and countdown.txt
  06.01-hl         row 4 after them: render, hl, and the bytes the frame sends for it
  06.02-screen     countdown.c at 06.02
  06.02-scan       stepped: row 7 scanned a character at a time. The frames come from scan()
                   below, a copy of editorUpdateSyntax at 06.02 in Python, which is asserted to
                   give the real editor's colours on every row of countdown.c (and at 06.03
                   and 06.04, with comments and keywords, the same)
  06.03-screen     countdown.c at 06.03, and whether each row ends inside a comment (hl_oc, from
                   the trace below)
  06.03-carry      stepped: / and then * typed at the start of row 4. The rows scanned, in their
                   order, with the state each starts and ends in, come from a scratch copy of the
                   project at 06.03 with two fprintf() calls added (TRACE_PATCH), which log every
                   scan to the file $KILO_TRACE; the colours of each row are the real screens'
  06.04-screen     countdown.c at 06.04
  06.04-words      how three word starts of rows 7 and 8 are tried against C_HL_keywords (scan())
  06.05-match      Ctrl-F order; then Down; then Escape: the screens, at 06.05

Terminal colours are drawn as fixed colours (TERM), the same values as the module's cover, each
at least 3.9:1 against both page backgrounds, and always named beside them. They are set on a
<tspan>: the site's .art rules override a fill on <text> or on a shape. The maps, the cover
and the icon are not made here.
"""
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
from figlib import Fig, write, esc, fmt  # noqa: E402
import steps  # noqa: E402
from harness import core  # noqa: E402

figlib.LESSONS = os.path.join(ROOT, "tracks", "kilo", "lessons")
MOD = "06-highlighting"
ROWS, COLS = 16, 56

# The terminal's colours as the figures draw them: (name, the n of ESC [ n m, fill).
TERM = {"r": ("red", 31, "#e03e3e"), "g": ("green", 32, "#2f8a3c"), "y": ("yellow", 33, "#9a7400"),
        "b": ("blue", 34, "#3a76d6"), "m": ("magenta", 35, "#c43fb0"), "c": ("cyan", 36, "#13899a")}

COUNTDOWN = ("/* countdown.c: 3, 2, 1,\n"
             "\n"
             "   and lift off. */\n"
             "#include <stdio.h>\n"
             "\n"
             "int main(void) {\n"
             "\tchar order[10] = \"lift off!\";\n"
             "\tfor (int i = 3; i > 0; i--)\n"
             "\t\tprintf(\"%d\\n\", i);\t// one a line\n"
             "\tputs(order);\t/* then the order */\n"
             "\treturn 0;\n"
             "}\n")
PRINTF = ("printf '/* countdown.c: 3, 2, 1,\\n\\n   and lift off. */\\n#include <stdio.h>\\n\\nint main(void) {\\n"
          "\\tchar order[10] = \"lift off!\";\\n\\tfor (int i = 3; i > 0; i--)\\n\\t\\tprintf(\"%%d\\\\n\", i);"
          "\\t// one a line\\n\\tputs(order);\\t/* then the order */\\n\\treturn 0;\\n}\\n'")
F = "\x06"                                   # Ctrl-F
DOWN, ESC = "\x1b[B", "\x1b"

_built = {}


def project(at, patch=None):
    """The project at lesson `at`, written by ./learn files and built; with patch, a list of
    (old, new) made to a scratch copy of its kilo.c first."""
    key = (at, tuple(patch or ()))
    if key not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="kilo-figs06-"), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "kilo", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        if patch:
            path = os.path.join(d, "kilo.c")
            with open(path) as f:
                src = f.read()
            for old, new in patch:
                assert src.count(old) == 1, (at, old)
                src = src.replace(old, new)
            with open(path, "w") as f:
                f.write(src)
        subprocess.run(["make", "-s"], cwd=d, check=True)
        _built[key] = d
    return _built[key]


class Shot:
    def __init__(self, ed):
        self.lines = ed.lines
        self.colors = ed.screen.colors()
        self.cursor = ed.cursor


def capture(at, keys=(), name="countdown.c", text=COUNTDOWN, patch=None, env=None, after_open=None):
    """[Shot after the file is open, Shot after each key in keys]: kilo at `at` on a 16 x 56
    pseudo-terminal, through track.py's edit()."""
    root = project(at, patch)
    track = core.Track("kilo")
    t = core.TestContext(track, track.lessons[0], root=root)
    try:
        kw = {"env": env} if env else {}
        ed = t.track.edit(t, text, name=name, rows=ROWS, cols=COLS, **kw)
        shots = [Shot(ed)]
        if after_open:
            after_open()
        for k in keys:
            ed.keys(k)
            shots.append(Shot(ed))
    finally:
        t.cleanup()
    return shots


# ------------------------------------------------------------------ a model of the scanner

NORMAL, NONPRINT, COMMENT, MLCOMMENT, KEYWORD1, KEYWORD2, STRING, NUMBER, MATCH = range(9)
LETTER = {NORMAL: ".", NONPRINT: "#", COMMENT: "c", MLCOMMENT: "c", KEYWORD1: "y", KEYWORD2: "g",
          STRING: "m", NUMBER: "r", MATCH: "b"}
SPACE = " \t\n\v\f\r"
SEPS = ",.()+-/*=~%[];"


def keywords():
    """C_HL_keywords, read from the reference kilo.c."""
    with open(os.path.join(ROOT, "tracks", "kilo", "kilo.c")) as f:
        src = f.read()
    body = src[src.index("char *C_HL_keywords[] = {"):]
    body = body[:body.index("};")]
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    return re.findall(r'"([^"]*)"', body)


KEYWORDS = keywords()


def is_sep(c):
    return c == "\0" or c in SPACE or c in SEPS


def scan(render, starts_in, lesson, trace=None):
    """editorUpdateSyntax at lesson 06.0N on one row of a C file: (hl, ends inside a comment).
    trace, a list, gets (index, rule, class, prev_sep, in_string) for each character looked at."""
    n = len(render)
    hl = [NORMAL] * n
    com, strnum, kw = lesson >= "06.03", lesson >= "06.02", lesson >= "06.04"

    def at(k):
        return render[k] if k < n else "\0"
    i = 0
    while i < n and render[i] in SPACE:
        if trace is not None:
            trace.append((i, "skip", NORMAL, 1, ""))
        i += 1
    prev_sep, in_string, in_comment = 1, "", starts_in if com else 0

    def note(k, rule, cls):
        if trace is not None:
            trace.append((k, rule, cls, prev_sep, in_string))
    while i < n:
        c = render[i]
        if com:
            if prev_sep and not in_comment and c == "/" and at(i + 1) == "/":
                for k in range(i, n):
                    hl[k] = COMMENT
                break
            if in_comment:
                hl[i] = MLCOMMENT
                if c == "*" and at(i + 1) == "/":
                    hl[i + 1] = MLCOMMENT
                    i += 2
                    in_comment, prev_sep = 0, 1
                    continue
                prev_sep = 0
                i += 1
                continue
            elif not in_string and c == "/" and at(i + 1) == "*":
                hl[i] = hl[i + 1] = MLCOMMENT
                i += 2
                in_comment, prev_sep = 1, 0
                continue
        if strnum:
            if in_string:
                hl[i] = STRING
                if c == "\\" and at(i + 1) != "\0":
                    hl[i + 1] = STRING
                    i += 2
                    prev_sep = 0
                    continue
                rule = "in"
                if c == in_string:
                    in_string, rule = "", "close"
                note(i, rule, STRING)
                i += 1
                continue
            elif c in "\"'":
                in_string, hl[i], prev_sep = c, STRING, 0
                note(i, "open", STRING)
                i += 1
                continue
        if not (32 <= ord(c) < 127):
            hl[i] = NONPRINT
            i += 1
            prev_sep = 0
            continue
        if strnum and ((c.isdigit() and (prev_sep or hl[i - 1] == NUMBER))
                       or (c == "." and i > 0 and hl[i - 1] == NUMBER)):
            rule = "num" if prev_sep else "num+"
            hl[i], prev_sep = NUMBER, 0
            note(i, rule, NUMBER)
            i += 1
            continue
        if kw and prev_sep:
            hit = None
            for word in KEYWORDS:
                k2 = word.endswith("|")
                w = word[:-1] if k2 else word
                if render[i:i + len(w)] == w and is_sep(at(i + len(w))):
                    hit = (w, KEYWORD2 if k2 else KEYWORD1)
                    break
            if hit:
                for k in range(i, i + len(hit[0])):
                    hl[k] = hit[1]
                i += len(hit[0])
                prev_sep = 0
                continue
        prev_sep = 1 if is_sep(c) else 0
        note(i, "sep" if is_sep(c) else "plain", NORMAL)
        i += 1
    return hl, in_comment


def render_of(line):
    out = ""
    for ch in line:
        if ch == "\t":
            out += " "
            while len(out) % 8:
                out += " "
        else:
            out += ch
    return out


def model_screen(text, lesson):
    """[(render, colour letters, ends inside a comment)] for each row of a C file just opened."""
    out, oc = [], 0
    for line in text.split("\n")[:-1]:
        r = render_of(line)
        hl, oc = scan(r, oc, lesson)
        out.append((r, "".join(LETTER[h] for h in hl), oc))
    return out


def check_model(lesson, shot):
    for k, (r, letters, _) in enumerate(model_screen(COUNTDOWN, lesson)):
        assert shot.lines[k] == r.rstrip(), (lesson, k, shot.lines[k], r)
        assert shot.colors[k] == letters[:len(r.rstrip())], (lesson, k, shot.colors[k], letters)


# ------------------------------------------------------------------ drawing

def ctext(f, x, y, s, code, size, cls="t"):
    """Text s at x, y in monospace: in the page's colour (code "."), the page's background ("#",
    on a reverse-video cell) or a terminal colour (a TERM letter), set on a tspan."""
    if code == ".":
        f.text(x, y, s, cls, size, mono=True)
    elif code == "#":
        f.text(x, y, s, "f", size, mono=True)
    else:
        f.add(f'<text class="mono" x="{fmt(x)}" y="{fmt(y)}" font-size="{fmt(size)}">'
              f'<tspan fill="{TERM[code][2]}">{esc(s)}</tspan></text>')


def runs(line, codes):
    """(start, end, code) for each run of one colour in a row."""
    out, i = [], 0
    while i < len(line):
        j = i
        while j < len(line) and codes[j] == codes[i]:
            j += 1
        out.append((i, j, codes[i]))
        i = j
    return out


def draw_row(f, x, base, line, codes, cw, rh, size=None):
    """One row of a screen: reverse-video runs on a filled bar, every other run in its colour,
    each word placed at its own column (SVG would collapse the spaces between them)."""
    size = size or cw / 0.6
    for a, b, code in runs(line, codes):
        assert code == "." or code == "#" or code in TERM, code
        if code == "#":
            f.rect(x + a * cw, base - rh * 0.72, (b - a) * cw, rh - 2, "t", 0, sw=False)
        col = a
        for part in line[a:b].split(" "):
            if part:
                ctext(f, x + col * cw, base, part, code, size)
            col += len(part) + 1


def screen(f, x, y, shot, cw, rh, rows=None, cursor=True, numbers=True, first=None):
    """A terminal screen from a Shot: the rows given (screen rows from 0), in a frame."""
    rows = list(range(ROWS)) if rows is None else list(rows)
    f.rect(x - 7, y - 4, COLS * cw + 14, len(rows) * rh + 8, "s fs", 6)
    for k, r in enumerate(rows):
        base = y + k * rh + rh * 0.72
        if cursor and shot.cursor[0] == r:
            c = shot.cursor[1]
            f.rect(x + c * cw - 0.5, y + k * rh + 1.5, cw + 1, rh - 3, "a", 1)
        draw_row(f, x, base, shot.lines[r], shot.colors[r], cw, rh)
        if numbers:
            f.text(x - 14, base, str((first or 1) + r), "tm", 9.5, "end", mono=True)
    return len(rows) * rh


def legend(f, x, y, items, size=11, step=None):
    """One line of colour keys: each colour's name in that colour, then what it marks."""
    for code, what in items:
        name, n, _ = TERM[code]
        ctext(f, x, y, name, code, size)
        x += len(name) * size * 0.6 + 4
        label = f"(ESC [{n}m): {what}"
        f.text(x, y, label, "tm", size - 0.5)
        x += figlib.tw(label, size - 0.5) + (step or 22)


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
    for k, line in enumerate(wrap(s, width)):
        f.text(x, y + k * lh, line, cls, size)


# ------------------------------------------------------------------ 06.01

def two_files0601():
    keys = (DOWN * 3, "\x1b[C" * 8, "\x01")
    c = capture("06.01", keys)[-1]
    t = capture("06.01", keys, name="countdown.txt")[-1]
    core_c = capture("05.02", keys)[-1]
    assert c.lines[3] == "#includeA <stdio.h>" and c.colors[3][8] == "#" and c.cursor == (3, 9)
    assert t.lines[3] == "#include <stdio.h>" and t.cursor == (3, 9) and set(t.colors[3]) == {"."}
    assert t.lines[:14] == core_c.lines[:14]
    f = Fig("f0601a", "The same keys in countdown.c and countdown.txt at 06.01: in the C file the byte "
            "Ctrl-A typed is drawn as a reverse-video A; in the text file it goes to the terminal as it is", 382)
    f.text(24, 22, "kilo at 06.01 on a terminal 16 rows by 56 columns, after Down 3 times, Right 8 times and Ctrl-A",
           "tm", 11)
    cw, rh = 7.0, 17
    x = 52
    for y, shot, title, bytes_, note in (
            (64, c, "countdown.c: a language kilo knows", "#include ESC[7m A ESC[0m <stdio.h>",
             "the byte 1 is class 1, HL_NONPRINT: drawn as A ('@' + 1) in reverse video, one cell"),
            (234, t, "countdown.txt: no language, so no classes but 0", "#include \\x01 <stdio.h>",
             "the byte 1 goes to the terminal, which draws nothing for it: the cursor, which counts it, "
             "is drawn on the < instead of the space")):
        f.text(x - 7, y - 14, title, "t", 12, weight=600)
        f.text(x + COLS * cw + 7, y - 14, "rows 1 to 6 of 16", "tm", 10, "end")
        screen(f, x, y, shot, cw, rh, rows=range(6))
        by = y + 6 * rh + 22
        f.text(x - 7, by, "row 4 as the frame sends it:", "tm", 10.5)
        f.text(x + 160, by, bytes_, "ta", 11, mono=True, weight=600)
        notes(f, x - 7, by + 18, note, 96)
    return f


def hl0601():
    keys = (DOWN * 3, "\x1b[C" * 8, "\x01")
    shot = capture("06.01", keys)[-1]
    render = "#include\x01 <stdio.h>"
    hl, _ = scan(render, 0, "06.01")
    letters = "".join(LETTER[h] for h in hl)
    assert shot.lines[3] == render.replace("\x01", "A") and shot.colors[3] == letters
    f = Fig("f0601b", "Row 4 with a Ctrl-A in it: its render, the class of each byte in hl, and how the frame "
            "draws each run of one class; the classes the module brings, and the colour of each", 470)
    f.text(24, 22, "a row keeps hl beside render: one class for every byte, worked out when render is made",
           "tm", 11)
    bw, x0 = 26, 76
    y = 52
    f.text(x0 - 12, y + 16, "render", "t", 11.5, "end", 600, mono=True)
    f.text(x0 - 12, y + 52, "hl", "t", 11.5, "end", 600, mono=True)
    for k, ch in enumerate(render):
        np_ = ch == "\x01"
        f.rect(x0 + k * bw, y, bw - 3, 24, "a af" if np_ else "s f", 3)
        f.text(x0 + k * bw + (bw - 3) / 2, y + 16, "\\1" if np_ else ch, "ta" if np_ else "t", 11.5, "middle",
               mono=True)
        f.rect(x0 + k * bw, y + 36, bw - 3, 24, "a af" if np_ else "m fs", 3)
        f.text(x0 + k * bw + (bw - 3) / 2, y + 52, str(hl[k]), "ta" if np_ else "t", 11.5, "middle", 700 if np_ else None,
               mono=True)
        if k % 5 == 0:
            f.text(x0 + k * bw + (bw - 3) / 2, y - 6, str(k), "tm", 9, "middle", mono=True)
    f.text(x0 + len(render) * bw + 4, y + 16, "19 bytes", "tm", 10.5)
    f.text(x0 + len(render) * bw + 4, y + 52, "19 classes", "tm", 10.5)
    # the runs, and what the frame sends for each
    ry = y + 98
    f.text(24, ry, "the frame walks the row a byte at a time; it sends an escape code only where the class changes",
           "tm", 10.5)
    parts = [(0, 8, "#include", "class 0: the byte itself, in the default colour"),
             (8, 9, "ESC[7m A ESC[0m", "class 1: reverse video, A for the byte 1, then all back to normal"),
             (9, 19, " <stdio.h>", "class 0 again: the bytes themselves")]
    for k, (a, b, sent, what) in enumerate(parts):
        yy = ry + 26 + k * 22
        f.text(x0 - 12, yy, f"{a}..{b - 1}", "tm", 10, "end", mono=True)
        f.text(x0, yy, sent, "ta" if b - a == 1 else "t", 11, mono=True, weight=600)
        f.text(x0 + 150, yy, what, "tm", 10.5)
    sy = ry + 26 + 3 * 22 + 6
    f.text(x0 - 12, sy + 4, "drawn", "tm", 10, "end")
    draw_row(f, x0, sy + 4, shot.lines[3], shot.colors[3], 8.4, 18)
    # the classes
    ty = sy + 44
    f.text(24, ty, "the classes, HL_*, and how editorSyntaxToColor() turns each into a colour", "t", 11.5, weight=600)
    table = [("0", "HL_NORMAL", None, "the terminal's default colour", "06.01"),
             ("1", "HL_NONPRINT", None, "reverse video, a letter or ?", "06.01"),
             ("6", "HL_STRING", "m", "", "06.02"),
             ("7", "HL_NUMBER", "r", "", "06.02"),
             ("2, 3", "HL_COMMENT, HL_MLCOMMENT", "c", "", "06.03"),
             ("4", "HL_KEYWORD1", "y", "", "06.04"),
             ("5", "HL_KEYWORD2", "g", "", "06.04"),
             ("8", "HL_MATCH", "b", "", "06.05")]
    for k, (num, name, code, what, lid) in enumerate(table):
        yy = ty + 22 + k * 19
        now = lid == "06.01"
        f.text(48, yy, num, "t" if now else "tm", 11, "middle", mono=True)
        f.text(72, yy, name, "t" if now else "tm", 11, mono=True)
        if code:
            cname, n, _ = TERM[code]
            ctext(f, 290, yy, cname, code, 11)
            f.text(290 + len(cname) * 6.6 + 6, yy, f"ESC [{n}m", "tm", 10.5, mono=True)
        else:
            f.text(290, yy, what, "t", 10.5)
        f.text(616, yy, "here" if now else f"comes with {lid}", "ta" if now else "tm", 10.5, "end",
               600 if now else None)
    return f


# ------------------------------------------------------------------ 06.02

def screen0602():
    shot = capture("06.02")[0]
    check_model("06.02", shot)
    f = Fig("f0602a", "countdown.c at 06.02: numbers red, strings magenta, and the digits in the comment red too, "
            "since comments are not known yet", 394)
    f.text(24, 22, "kilo at 06.02, countdown.c on a terminal 16 rows by 56 columns", "tm", 11)
    cw, rh = 8.4, 17.5
    x, y = 58, 42
    screen(f, x, y, shot, cw, rh)
    ly = y + ROWS * rh + 26
    legend(f, 24, ly, [("r", "a number"), ("m", "a string, quotes and all")])
    f.text(24, ly + 20, "Row 1's 3, 2 and 1 are red: to this lesson's scanner a comment is ordinary text, and each "
           "digit follows a separator.", "tm", 10.5)
    return f


def scan0602():
    shot = capture("06.02")[0]
    check_model("06.02", shot)
    line = COUNTDOWN.split("\n")[6]
    render = render_of(line)
    trace = []
    hl, _ = scan(render, 0, "06.02", trace)
    assert shot.lines[6] == render and shot.colors[6] == "".join(LETTER[h] for h in hl)
    assert [k for k, *_ in trace] == list(range(len(render)))
    # group the characters by the rule that coloured them
    groups = []
    for k, rule, cls, ps, ins in trace:
        if groups and groups[-1]["rule"] == rule:
            groups[-1]["end"] = k + 1
            groups[-1]["ps"], groups[-1]["ins"] = ps, ins
        else:
            groups.append(dict(rule=rule, start=k, end=k + 1, cls=cls, ps=ps, ins=ins))
    rules = [g["rule"] for g in groups]
    assert rules == ["skip", "plain", "sep", "plain", "sep", "num", "num+", "sep", "open", "in", "close", "sep"], rules

    def cap(g):
        s = render[g["start"]:g["end"]]
        q = f"\"{s}\"" if len(s) > 1 else f"'{s}'"
        return {
            "skip": "Spaces at the start, here the tab's 8, are skipped and stay normal (class 0). "
                    "prev_sep starts at 1: a word may start at the first character.",
            "plain": (f"{q}: no quote, no digit, no separator. Normal, and prev_sep = 0: each letter after "
                      f"the first is inside a word." if g["start"] == 8 else
                      f"{q}: a word again, normal. This lesson has no keywords: a word is never coloured."),
            "sep": f"{q}: separator{'s' if len(s) > 1 else ''}, so normal, and prev_sep = 1: a word may start "
                   f"after {'them' if len(s) > 1 else 'it'}." + (" The end of render: the row is done." if
                                                                g["end"] == len(render) else ""),
            "num": f"'{s}' is a digit and prev_sep is 1: a number starts here. Class 7, HL_NUMBER, red.",
            "num+": f"'{s}' is a digit right after a number (the class before it is 7): the number goes on.",
            "open": "A double quote opens a string: in_string holds the quote that will close it. "
                    "The quote itself is class 6, HL_STRING, magenta.",
            "in": f"{q}: inside a string every character is string, the space and the ! too. The scan only "
                  f"looks for the closing quote, or a backslash.",
            "close": "The same quote again: it is string too, and it closes the string (in_string = 0).",
        }[g["rule"]]

    f = Fig("f0602b", "Row 7 of countdown.c scanned left to right by editorUpdateSyntax at 06.02: the class "
            "each character gets, and the two things the scan keeps as it goes", 300)
    f.text(24, 22, "row 7, as render holds it: the tab is 8 spaces. One box per byte of render; under it, its class in hl",
           "tm", 11)
    bw, x0, y = 16, 40, 64
    for k, ch in enumerate(render):
        f.rect(x0 + k * bw, y, bw - 2, 22, "s f", 2)
        if ch != " ":
            f.text(x0 + k * bw + (bw - 2) / 2, y + 15, ch, "t", 11.5, "middle", mono=True)
        if k % 5 == 0:
            f.text(x0 + k * bw + (bw - 2) / 2, y - 6, str(k), "tm", 9, "middle", mono=True)
    f.text(x0 - 8, y + 15, "render", "tm", 10, "end")
    f.text(x0 - 8, y + 47, "hl", "tm", 10, "end")
    f.text(24, 168, "the scan's state after the characters in the box", "tm", 10.5)
    done = [None] * len(render)
    for g in groups:
        for k in range(g["start"], g["end"]):
            done[k] = trace[k][2]
        with steps.step(f, cap(g)):
            a, b = g["start"], g["end"]
            f.rect(x0 + a * bw - 2, y - 3, (b - a) * bw + 2, 28, "a", 4)
            for k, cls in enumerate(done):
                cx = x0 + k * bw + (bw - 2) / 2
                if cls is None:
                    f.text(cx, y + 47, "-", "tm", 10, "middle", mono=True)
                else:
                    code = LETTER[cls]
                    if code == ".":
                        f.text(cx, y + 47, str(cls), "t", 11, "middle", mono=True)
                    else:
                        f.add(f'<text class="mono" x="{fmt(cx)}" y="{y + 47}" font-size="11" font-weight="700" '
                              f'text-anchor="middle"><tspan fill="{TERM[code][2]}">{cls}</tspan></text>')
            ps, ins = g["ps"], g["ins"]
            f.text(40, 194, f"prev_sep = {ps}", "ta", 13, weight=700, mono=True)
            f.text(200, 194, "a word may start next" if ps else "inside a word, or a string", "tm", 10.5)
            f.text(40, 218, f"in_string = {repr(ins) if ins else 0}", "ta", 13, weight=700, mono=True)
            f.text(200, 218, "inside a string that a \" closes" if ins else "not inside a string", "tm", 10.5)
            # the row as the screen will draw it, so far: each character under its box
            f.text(x0 - 8, 262, "drawn", "tm", 10, "end")
            for k in range(b):
                ch = shot.lines[6][k]
                if ch != " ":
                    code = shot.colors[6][k]
                    cx = x0 + k * bw + (bw - 2) / 2
                    if code == ".":
                        f.text(cx, 262, ch, "t", 13, "middle", mono=True)
                    else:
                        f.add(f'<text class="mono" x="{fmt(cx)}" y="262" font-size="13" text-anchor="middle">'
                              f'<tspan fill="{TERM[code][2]}">{esc(ch)}</tspan></text>')
    f.text(24, 290, "class 0 normal, 6 string (magenta), 7 number (red)", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 06.03

TRACE_PATCH = [
    ("    if (row->idx > 0 && editorRowHasOpenComment(&E.row[row->idx-1]))\n        in_comment = 1;\n",
     "    if (row->idx > 0 && editorRowHasOpenComment(&E.row[row->idx-1]))\n        in_comment = 1;\n"
     "    if (getenv(\"KILO_TRACE\")) { FILE *tf = fopen(getenv(\"KILO_TRACE\"),\"a\");"
     " fprintf(tf,\"scan %d starts %d\\n\",row->idx,in_comment); fclose(tf); }\n"),
    ("    int oc = in_comment;\n",
     "    int oc = in_comment;\n"
     "    if (getenv(\"KILO_TRACE\")) { FILE *tf = fopen(getenv(\"KILO_TRACE\"),\"a\");"
     " fprintf(tf,\"scan %d ends %d was %d\\n\",row->idx,oc,row->hl_oc); fclose(tf); }\n"),
]


def traced(keys):
    """Shots and the trace of every scan, for countdown.c at 06.03 with TRACE_PATCH, the keys typed
    after it opens: (shots, scans at open, scans after each key)."""
    log = os.path.join(tempfile.mkdtemp(prefix="kilo-figs06-trace-"), "trace")
    env = dict(os.environ, KILO_TRACE=log)
    marks = []

    def mark():
        marks.append(os.path.getsize(log))
    shots = capture("06.03", keys, patch=TRACE_PATCH, env=env, after_open=mark)
    with open(log) as f:
        text = f.read()
    opened, rest = text[:marks[0]], text[marks[0]:]

    def parse(s):
        out = []
        for m in re.finditer(r"scan (\d+) starts (\d)\nscan \1 ends (\d) was (\d)\n", s):
            out.append(tuple(int(g) for g in m.groups()))
        assert "".join(m.group(0) for m in re.finditer(r"scan (\d+) starts (\d)\nscan \1 ends (\d) was (\d)\n", s)) == s
        return out
    return shots, parse(opened), parse(rest)


def screen0603():
    shot = capture("06.03")[0]
    check_model("06.03", shot)
    _, opened, _ = traced(())
    ends = {}
    for row, _, end, _ in opened:
        ends[row] = end
    model = model_screen(COUNTDOWN, "06.03")
    assert [ends[k] for k in range(12)] == [m[2] for m in model]
    f = Fig("f0603a", "countdown.c at 06.03: comments cyan, and for each row whether it ends inside a /* */ "
            "comment, which the row below starts from", 404)
    f.text(24, 22, "kilo at 06.03, countdown.c on a terminal 16 rows by 56 columns", "tm", 11)
    cw, rh = 7.4, 17.5
    x, y = 52, 58
    screen(f, x, y, shot, cw, rh)
    cx = x + COLS * cw + 30
    f.text(cx, y - 26, "ends inside", "t", 11, weight=600)
    f.text(cx, y - 12, "a comment?", "t", 11, weight=600)
    for r in range(12):
        base = y + r * rh + rh * 0.72
        yes = ends[r]
        f.text(cx, base, "yes" if yes else "no", "ta" if yes else "tm", 11, weight=700 if yes else None, mono=True)
    f.text(cx, y + 12 * rh + rh * 0.72, "(hl_oc)", "tm", 10, mono=True)
    ly = y + ROWS * rh + 26
    legend(f, 24, ly, [("c", "a comment, // to the end of the row or /* to */"), ("r", "a number"),
                       ("m", "a string")], step=14)
    f.text(24, ly + 20, "Row 2 is empty, yet it ends inside the comment: it started inside one, and nothing on it "
           "closed it.", "tm", 10.5)
    return f


def carry0603():
    keys = (DOWN * 3, "/", "*")
    shots, opened, after = traced(keys)
    plain = capture("06.03", keys)
    for a, b in zip(shots, plain):
        assert a.lines == b.lines and a.colors == b.colors
    s0, s_slash, s_star = shots[0], shots[2], shots[3]
    # the scans each key made: Down makes none
    per_key, cut = [], 0
    # after holds the scans of "/" then of "*": split where row 3 is scanned again
    starts = [k for k, sc in enumerate(after) if sc[0] == 3]
    assert len(starts) == 2 and starts[0] == 0, after
    slash, star = after[:starts[1]], after[starts[1]:]
    assert slash == [(3, 0, 0, 0)], slash
    assert [sc[0] for sc in star] == [3, 4, 5, 6, 7, 8, 9], star
    assert all(sc[2] == 1 and sc[3] == 0 for sc in star[:-1]) and star[-1][2:] == (0, 0), star
    ends0 = {row: end for row, _, end, _ in opened}

    f = Fig("f0603b", "/ and then * typed at the start of row 4 of countdown.c at 06.03: the rows scanned again, "
            "one after another, until a row ends the way it did before", 336)
    f.text(24, 22, "hl of each row as the scan leaves it; the screen is drawn once, after the key", "tm", 11)
    cw, rh = 6.6, 19
    x, y = 58, 66
    cx1, cx2 = 452, 540
    f.text(cx1, y - 14, "starts", "t", 10.5, weight=600)
    f.text(cx2, y - 14, "ends inside a comment", "t", 10.5, weight=600)

    def frame(rows_text, rows_colors, ends, scanned, current, starts=None, was=None):
        f.rect(x - 7, y - 4, 53 * cw + 14, 12 * rh + 8, "s fs", 6)
        for r in range(12):
            base = y + r * rh + rh * 0.72
            if r == current:
                f.rect(x - 7, y + r * rh, 53 * cw + 14, rh, "a af", 0, sw=False)
                f.text(x - 30, base, ">", "ta", 12, "middle", 700, mono=True)
            f.text(x - 14, base, str(r + 1), "ta" if r == current else "tm", 9.5, "end", mono=True)
            draw_row(f, x, base, rows_text[r], rows_colors[r], cw, rh)
            if r == current and starts is not None:
                f.text(cx1, base, "inside" if starts else "outside", "ta", 10.5, weight=600, mono=True)
            end = ends[r]
            if r == current and was is not None and was != end:
                f.text(cx2, base, f"{'yes' if was else 'no'} -> {'yes' if end else 'no'}", "ta", 10.5,
                       weight=700, mono=True)
            elif r == current and was is not None:
                f.text(cx2, base, f"{'yes' if end else 'no'}, as before", "ta", 10.5, weight=700, mono=True)
            else:
                f.text(cx2, base, "yes" if end else "no", "t" if r in scanned else "tm", 10.5, mono=True)

    texts = lambda shot: [shot.lines[r] for r in range(12)]  # noqa: E731
    cols = lambda shot: [shot.colors[r] for r in range(12)]  # noqa: E731
    with steps.step(f, "Before: rows 1 and 2 end inside the comment that row 1 opens; row 3 closes it, and "
                       "every row after that ends outside one."):
        frame(texts(s0), cols(s0), ends0, set(), None)
    with steps.step(f, "/ typed at the start of row 4: the row is scanned again. \"/#\" opens nothing, and the "
                       "row ends outside a comment, as before: nothing below it is touched."):
        frame(texts(s_slash), cols(s_slash), ends0, {3}, 3, starts=0, was=0)
    ends = dict(ends0)
    text_now, col_now = texts(s_slash), cols(s_slash)
    words = {3: "Now \"/*\" opens a comment that does not close on this row: it ends inside one, where it "
                "ended outside before. So the row below starts differently: it is next.",
             4: "Row 5, empty, starts inside the comment and has nothing to close it: it ends inside, and it "
                "did not before. On to row 6.",
             5: "Row 6 is all comment now: every character cyan, and it ends inside. Changed: on to row 7.",
             6: "Row 7: the string and the number are part of the comment too. Changed: on to row 8.",
             7: "Row 8 the same. On to row 9.",
             8: "Row 9: the // after the tab is inside the comment, so it is part of it; it opens nothing. "
                "Ends inside: on to row 10.",
             9: "Row 10: \"/*\" inside a comment opens nothing, and \"*/\" closes it. The row ends outside a "
                "comment, as it did before: the scan stops here."}
    for row, st, end, was in star:
        text_now[row], col_now[row] = s_star.lines[row], s_star.colors[row]
        ends[row] = end
        first = "* typed: row 4 is scanned again. " if row == 3 else ""
        with steps.step(f, first + words[row]):
            frame(text_now, col_now, ends, set(range(3, row + 1)), row, starts=st, was=was)
    with steps.step(f, "The frame is drawn: rows 4 to 10 in the comment's colour. Rows 11 and 12 were not "
                       "scanned again, and keep their colours: nothing above them ends differently."):
        frame(texts(s_star), cols(s_star), ends, set(range(3, 10)), None)
    legend(f, 24, 324, [("c", "comment"), ("r", "number"), ("m", "string")], size=10.5, step=16)
    return f


# ------------------------------------------------------------------ 06.04

def screen0604():
    shot = capture("06.04")[0]
    check_model("06.04", shot)
    f = Fig("f0604a", "countdown.c at 06.04, every class coloured: keywords yellow, types green, comments cyan, "
            "strings magenta, numbers red", 410)
    f.text(24, 22, "kilo at 06.04, countdown.c on a terminal 16 rows by 56 columns", "tm", 11)
    cw, rh = 8.4, 17.5
    x, y = 58, 42
    screen(f, x, y, shot, cw, rh)
    ly = y + ROWS * rh + 26
    legend(f, 24, ly, [("y", "a keyword"), ("g", "a type"), ("c", "a comment")], step=24)
    legend(f, 24, ly + 20, [("m", "a string"), ("r", "a number")], step=24)
    f.text(24, ly + 40, "printf, puts, main and order are names the list does not hold: they stay in the default "
           "colour.", "tm", 10.5)
    return f


def words0604():
    shot = capture("06.04")[0]
    check_model("06.04", shot)
    f = Fig("f0604b", "Three places in rows 7 and 8 where a word may start, and how each is tried against the "
            "keyword list", 330)
    f.text(24, 22, "at a word start (prev_sep is 1) each word of C_HL_keywords is tried in turn; the first that "
           "fits wins", "tm", 11)
    r7, r8 = render_of(COUNTDOWN.split("\n")[6]), render_of(COUNTDOWN.split("\n")[7])
    cases = [(r7, 8, "char", "char|", "g",
              "\"char|\": the | marks a type. c h a r match, and the space after them is a separator",
              "HL_KEYWORD2, green"),
             (r7, 13, "or", "or", None,
              "\"or\" (a C++ keyword) matches o r, but d comes next: no separator, so no keyword. Nothing "
              "else in the list fits",
              "normal; and d e r are inside a word now, so no keyword can start there"),
             (r8, 8, "for", "for", "y",
              "\"for\": f o r match, and the space after them is a separator",
              "HL_KEYWORD1, yellow")]
    cw = 13
    y = 56
    for row, at, word, entry, code, why, result in cases:
        hl, _ = scan(row, 0, "06.04")
        x0 = 40
        f.text(24, y, f"row {7 if row is r7 else 8}, column {at}:", "tm", 10.5)
        seg = row[at:at + 12]
        for k, ch in enumerate(seg):
            inword = k < len(word)
            nxt = k == len(word)
            cls = "a af" if inword else ("s f" if nxt else "m f")
            f.rect(x0 + k * cw, y + 10, cw - 2, 20, cls, 2)
            if ch != " ":
                letter = LETTER[hl[at + k]]
                ctext(f, x0 + k * cw + 1.5, y + 24, ch, letter if letter != "#" else ".", 11)
        nx = x0 + len(word) * cw + (cw - 2) / 2
        f.text(nx, y + 44, "next", "tm", 9.5, "middle")
        f.text(x0 + 13 * cw + 14, y + 24, f"tried: \"{entry}\"", "t", 11, weight=600, mono=True)
        notes(f, x0 + 13 * cw + 14, y + 42, why, 58, "tm", 10.5, 14)
        if code:
            ctext(f, x0, y + 64, "-> " + result, code, 11)
            assert shot.colors[6 if row is r7 else 7][at:at + len(word)] == code * len(word)
        else:
            f.text(x0, y + 64, "-> " + result, "t", 10.5)
            assert shot.colors[6][at:at + 5] == "....."
        y += 88
    return f


# ------------------------------------------------------------------ 06.05

def match0605():
    shots = capture("06.05", (F, "order", DOWN, ESC))
    a, b, c = shots[2], shots[3], shots[4]
    assert a.colors[0][13:18] == "bbbbb" and b.colors[0][13:18] == "bbbbb"
    assert "b" not in "".join(c.colors) and c.lines[6].startswith("        char order")
    assert b.lines[0].count("order") == 2 and b.colors[0].count("b") == 5
    f = Fig("f0605a", "Ctrl-F order, then Down, then Escape, at 06.05: the match is blue while it is the match, "
            "and its row gets its own colours back as soon as it is not", 470)
    f.text(24, 22, "kilo at 06.05, countdown.c on a terminal 16 rows by 56 columns; the top of the screen and "
           "the message line", "tm", 11)
    cw, rh = 6.4, 16.5
    x = 50
    nx = x + COLS * cw + 22
    y = 62
    panels = [(a, "Ctrl-F, then order", range(4), 7,
               "Row 7's classes are copied to saved_hl first. Then the 5 of order, after a tab, are "
               "made class 8: blue over green and default."),
              (b, "Down: the next match", range(3), 10,
               "Row 7 gets its saved classes back. Row 10's are saved, and its first order is blue; "
               "the one in the comment is not."),
              (c, "Escape: the search ends", range(6, 10), 1,
               "Row 10 gets its classes back, and the view goes back to where it was. Nothing is "
               "blue.")]
    for shot, title, rows, first, note in panels:
        f.text(x - 7, y - 12, title, "t", 12, weight=600)
        h = screen(f, x, y, shot, cw, rh, rows=rows, first=first)
        msg = shot.lines[ROWS - 1] or "(the message line is empty)"
        f.text(x, y + h + 18, msg, "tm" if not shot.lines[ROWS - 1] else "t", 10, mono=bool(shot.lines[ROWS - 1]))
        notes(f, nx, y + 6, note, 30, "tm", 10.5, 14)
        y += h + 58
    legend(f, 24, y - 16, [("b", "the match, class 8"), ("g", "a type"), ("m", "a string"), ("r", "a number")],
           size=10.5, step=12)
    return f


FIGS = [
    ("06.01-two-files", two_files0601, False),
    ("06.01-hl", hl0601, False),
    ("06.02-screen", screen0602, False),
    ("06.02-scan", scan0602, True),
    ("06.03-screen", screen0603, False),
    ("06.03-carry", carry0603, True),
    ("06.04-screen", screen0604, False),
    ("06.04-words", words0604, False),
    ("06.05-match", match0605, False),
]


def main():
    out = subprocess.run(["bash", "-c", PRINTF], capture_output=True, text=True, check=True).stdout
    assert out == COUNTDOWN, "the lessons' printf does not make countdown.c"
    only = sys.argv[1:]
    for name, fn, stepped in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        fig = fn()
        text = fig.svg()
        if stepped:
            print(name, "steps:", steps.check(text))
        print(write(MOD, name, fig))
    for d in {os.path.dirname(p) for p in _built.values()}:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
