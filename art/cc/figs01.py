"""Figures for cc module 01, Tokens (lessons 01.01 to 01.05).

    python3 -B art/cc/figs01.py [name-prefix ...]
                writes tracks/cc/lessons/01-tokens/figures/01.0N-*.svg

Every token, value, instruction and message here is from a real run of ./cc in the project as the
site shows it at the lesson (./learn files cc --at 01.0N, make -s: figlib.project), and NOTES.md's
transcripts are asserted:

  01.01-scan      stepped: --tokens of try.c (5 + 20 - 4) at 01.01: one step for each space the
                  scanner skips and each token it makes, in the order of the columns --tokens prints
  01.01-walker    ./cc try.c at 01.01, its instructions run (figlib.simulate) for a0 after each
                  group: 5, 25, 21; ./ccrun try.c exits 21
  01.02-longest   --tokens of 1>>=2 at 01.02, and in a scratch copy whose read_punct table has the
                  two-character punctuators before the three-character ones: 1 >> = 2. (Not the
                  design's a>>=b: at 01.02 a name is still an invalid token; names come at 01.03.)
  01.02-spaces    --tokens at 01.02 of 1->2, 1- >2, 1--2, 1 - -2, and 1 -> 2 for where a space
                  changes nothing (numbers for the design's a and b, as above)
  01.03-names     --tokens of NOTES.md's return x1 _y int2 float at 01.03; is_keyword's table has
                  37 names
  01.04-literals  --tokens of NOTES.md's lit.c line at 01.04; the string's bytes from a scratch copy
                  whose print_tokens also prints them: 61 09 62
  01.04-escapes   --tokens at 01.04 of a character constant for each escape read_escaped_char
                  knows, and '\\e' refused with "unknown escape sequence"
  01.05-caret     ./cc end.c and ./cc d.c at 01.05 (NOTES.md's printf lines): the two lines on
                  standard error, byte for byte
The maps, the cover and the icon are not made here (archmap.py; art/outlines/cc_art.py).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib as L  # noqa: E402
from figlib import Fig, write, steps  # noqa: E402

TOKENS_0101 = ["1:1 num 5 5", "1:3 punct +", "1:5 num 20 20", "1:8 punct -", "1:10 num 4 4", "1:11 eof"]


def token_chip(f, cx, y, text, cls="s fs", tcls="t", size=13, h=26, minw=26):
    w = max(minw, L.tw(text, size, True) + 16)
    f.rect(cx - w / 2, y, w, h, cls, 5)
    f.text(cx, y + h / 2 + size * 0.36, text, tcls, size, "middle", 600, mono=True)
    return w


def chips_row(f, x, y, texts, cls="s fs", tcls="t", size=13, gap=8, hot=()):
    """Token chips left to right from x; returns the x after the last."""
    for i, t in enumerate(texts):
        w = max(26, L.tw(t, size, True) + 16)
        hc = i in hot
        token_chip(f, x + w / 2, y, t, "a af" if hc else cls, "ta" if hc else tcls, size)
        x += w + gap
    return x - gap


def cells(f, x, y, text, w=30, h=34, size=15, cls_of=None, numbers=True, dot_spaces=True):
    """The characters of text, one cell each; column numbers from 1 over them. cls_of(i) ->
    (cell class, text class)."""
    for i, ch in enumerate(text):
        cc, tc = cls_of(i) if cls_of else ("s f", "t")
        f.rect(x + i * w, y, w, h, cc, 0)
        if ch == " ":
            if dot_spaces:
                f.circle(x + i * w + w / 2, y + h / 2, 1.6, "m fa" if tc == "ta" else "m")
        else:
            f.text(x + i * w + w / 2, y + h / 2 + size * 0.36, ch, tc, size, "middle", 600, mono=True)
        if numbers:
            f.text(x + i * w + w / 2, y - 7, str(i + 1), "tm", 10.5, "middle", mono=True)


# ------------------------------------------------------------------ 01.01

def scan():
    src = L.source("01.01", "try.c")
    assert src == "5 + 20 - 4\n", src
    toks, out = L.tokens("01.01", src)
    assert out.splitlines() == TOKENS_0101, out
    line = src.rstrip("\n")
    f = Fig("f0101a", "The scanner walking 5 + 20 - 4, a character at a time", 214)
    x0, y0, w, h = 24, 54, 32, 36
    f.text(x0, 20, "try.c, a cell a byte, columns from 1", "tm", 11.5)
    lx = 418
    f.text(lx, 20, "./cc --tokens try.c", "tm", 11.5, mono=True)
    n = len(line)
    # the newline the file ends with: where the end-of-file token sits
    cells(f, x0, y0, line, w, h)
    f.rect(x0 + n * w, y0, w, h, "m f", 0, dash=True)
    f.text(x0 + n * w + w / 2, y0 + h / 2 + 4.5, "\\n", "tm", 12, "middle", mono=True)
    f.text(x0 + n * w + w / 2, y0 - 7, str(n + 1), "tm", 10.5, "middle", mono=True)
    f.rect(lx - 10, 32, 640 - 16 - lx + 10, 20 * len(toks) + 18, "s fs", 6)

    by_col = {t[1]: t for t in toks}
    events, col = [], 1
    while col <= n + 1:
        if col in by_col:
            t = by_col[col]
            ln = len(t[3]) if t[2] != "eof" else 1
            events.append(("token", col, ln, t))
            col += ln if t[2] != "eof" else 1
            if t[2] == "eof":
                break
        else:
            assert line[col - 1] == " ", (col, line)
            events.append(("space", col, 1, None))
            col += 1
    made = []
    for kind, col, ln, t in events:
        if kind == "token":
            made.append(t)
        start = col - 1
        if kind == "space":
            cap = f"Column {col} is a space: the scanner steps over it and makes no token."
        elif t[2] == "eof":
            cap = (f"Column {col} is the newline at the end of the file: nothing more to read, so the scanner "
                   "makes the end-of-file token, there, and stops.")
        elif t[2] == "num":
            cap = (f"Column {col}: a digit, so the scanner reads the whole number, {t[3]} ({ln} "
                   f"character{'s' if ln > 1 else ''}), and makes a num token with the value {t[4]}.")
        else:
            cap = f"Column {col}: {t[3]} is a punctuator, one character: a punct token."
        with steps.step(f, cap):
            # what has been read, and the cells of this step
            for i in range(start + ln if kind != "token" or t[2] != "eof" else start):
                hot = start <= i < start + ln
                f.rect(x0 + i * w + 1, y0 + 1, w - 2, h - 2, "af" if hot else "fs", 0, sw=False)
                ch = line[i]
                if ch != " ":
                    f.text(x0 + i * w + w / 2, y0 + h / 2 + 15 * 0.36, ch, "ta" if hot else "tm", 15, "middle", 600,
                           mono=True)
                else:
                    f.circle(x0 + i * w + w / 2, y0 + h / 2, 1.6, "m")
            if kind == "token" and t[2] == "eof":
                f.rect(x0 + n * w, y0, w, h, "a af", 0)
                f.text(x0 + n * w + w / 2, y0 + h / 2 + 4.5, "\\n", "ta", 12, "middle", mono=True)
            # the marker under where the scanner stands
            mx0, mx1 = x0 + start * w + 3, x0 + (start + ln) * w - 3
            cls = "m" if kind == "space" else "a"
            f.brace_h(mx0, mx1, y0 + h + 10, cls)
            mid = (mx0 + mx1) / 2
            f.line(mid, y0 + h + 10, mid, y0 + h + 24, cls)
            f.text(mid, y0 + h + 40, "skipped" if kind == "space" else t[2], "tm" if kind == "space" else "ta", 12,
                   "middle", 700 if kind != "space" else None)
            for i, t2 in enumerate(made):
                last = i == len(made) - 1 and kind == "token"
                s = out.splitlines()[toks.index(t2)]
                f.code(lx, 56 + i * 20, s, 13, "ta" if last else "t", weight=700 if last else None)
    return f


def walker():
    src = L.source("01.01", "try.c")
    lines = L.asm("01.01", src)
    assert lines == ["  .globl main", "main:", "  li a0, 5", "  li t0, 20", "  add a0, a0, t0", "  li t0, 4",
                     "  sub a0, a0, t0", "  ret"], lines
    assert L.ccrun("01.01", src) == 21
    ins = L.instructions(lines)
    groups = [(["5"], ins[0:1]), (["+", "20"], ins[1:3]), (["-", "4"], ins[3:5])]
    sim = L.simulate(ins[:5])
    a0 = [sim[0][1]["a0"], sim[2][1]["a0"], sim[4][1]["a0"]]
    assert a0 == [5, 25, 21], a0
    f = Fig("f0101b", "What the compiler does with the tokens at 01.01: one total in a0, each number through t0", 236)
    centres = [92, 300, 516]
    f.text(24, 20, "the tokens of 5 + 20 - 4, and the lines ./cc writes for each group", "tm", 11.5)
    for k, ((toks, code), cx) in enumerate(zip(groups, centres)):
        tw_ = sum(max(26, L.tw(t, 14, True) + 16) for t in toks) + 8 * (len(toks) - 1)
        chips_row(f, cx - tw_ / 2, 36, toks, size=14)
        f.brace_h(cx - tw_ / 2 - 4, cx + tw_ / 2 + 4, 70, "m")
        f.line(cx, 70, cx, 82, "m", arrow=True)
        cwid = max(L.tw(c, 13, True) for c in code) + 24
        f.rect(cx - cwid / 2, 86, cwid, 16 + 20 * len(code), "s fs", 6)
        for i, c in enumerate(code):
            f.code(cx - cwid / 2 + 12, 104 + i * 20, c, 13, "t")
        y = 86 + 16 + 20 * 2 + 30
        f.rich(cx, y, [("a0", "ta", True), (f" = {a0[k]}", "ta", True)], 16, "middle", 700)
        if k:
            f.line(centres[k - 1] + 40, y - 5, cx - 40, y - 5, "a", arrow=True)
    f.text(24, 186 + 30, "Then ret: main returns a0, and ./ccrun try.c exits with 21. Anything but a number, + or - "
                         "stops it.", "tm", 11.5)
    return f


# ------------------------------------------------------------------ 01.02

REORDER = [("tokenize.c", '    "<<=", ">>=", "==", "!=", "<=", ">=", "->", "+=",\n',
            '    "==", "!=", "<=", ">=", "->", "+=",\n'),
           ("tokenize.c", '    "||", "<<", ">>",\n', '    "||", "<<", ">>", "<<=", ">>=",\n')]


def texts(toks):
    return [t[3] for t in toks if t[2] != "eof"]


def longest():
    src = "1>>=2\n"
    toks, _ = L.tokens("01.02", src)
    assert texts(toks) == ["1", ">>=", "2"], toks
    d = L.patched("01.02", "two-first", REORDER)
    toks2, _ = L.tokens("01.02", src, d=d)
    assert texts(toks2) == ["1", ">>", "=", "2"], toks2
    f = Fig("f0102a", "At a >, three candidates: the scanner takes the longest that matches", 270)
    x0, y0, w, h = 40, 46, 36, 38
    line = src.strip()
    f.text(24, 18, "the text 1>>=2, and the scanner at column 2", "tm", 11.5)
    cells(f, x0, y0, line, w, h, 16,
          cls_of=lambda i: ("a af", "ta") if 1 <= i <= 3 else ("s f", "t"))
    # the candidates: brackets under columns 2.., one per length
    cand = [(">>=", 3, "three characters: matches, and it is tried first: taken", True),
            (">>", 2, "two: also matches, never reached", False),
            (">", 1, "one: also matches, never reached", False)]
    for k, (t, ln, note, taken) in enumerate(cand):
        y = y0 + h + 18 + k * 26
        cls = "a" if taken else "m"
        f.path(f"M{x0 + w + 4} {y - 6} V{y} H{x0 + (1 + ln) * w - 4} V{y - 6}", cls)
        f.code(x0 + 5 * w + 14, y + 4, t, 13, "ta" if taken else "t", weight=700 if taken else None)
        f.text(x0 + 5 * w + 56, y + 4, note, "ta" if taken else "tm", 12, weight=700 if taken else None)
    # the two results
    ry = 196
    f.text(24, ry - 12, "read_punct as written: longest first", "t", 12, weight=700)
    chips_row(f, 24, ry, texts(toks), hot=(1,))
    rx = 330
    f.text(rx, ry - 12, "two characters tried before three", "t", 12, weight=700)
    xe = chips_row(f, rx, ry, texts(toks2))
    f.text(rx, ry + 46, "the = is left over, a token of its own", "tm", 11.5)
    f.text(24, ry + 46, "./cc --tokens at 01.02, both", "tm", 11.5)
    return f


SPACES = [("1->2", "one operator, ->"), ("1- >2", "a space inside it: two operators"),
          ("1--2", "--, as written: the longest match"), ("1 - -2", "the space between them: two minuses")]


def spaces():
    runs = {s: texts(L.tokens("01.02", s + "\n")[0]) for s, _ in SPACES + [("1 -> 2", "")]}
    assert runs["1->2"] == ["1", "->", "2"] and runs["1- >2"] == ["1", "-", ">", "2"], runs
    assert runs["1--2"] == ["1", "--", "2"] and runs["1 - -2"] == ["1", "-", "-", "2"], runs
    assert runs["1 -> 2"] == runs["1->2"], runs
    assert L.cc("02.06", "1--2\n")[2] == 1               # what the parser makes of it, at the end of module 02
    f = Fig("f0102b", "Where a space changes the tokens and where it does not", 300)
    x0, w, h = 24, 22, 28
    tx = 212
    f.text(x0, 18, "the text", "tm", 11.5)
    f.text(tx, 18, "its tokens, ./cc --tokens at 01.02", "tm", 11.5)
    ys = [34, 84, 164, 214]
    for (s, note), y in zip(SPACES, ys):
        # the spaces that matter: taken out one at a time, the tokens change
        hot = {i for i, ch in enumerate(s) if ch == " "
               and texts(L.tokens("01.02", s[:i] + s[i + 1:] + "\n")[0]) != runs[s]}
        cells(f, x0, y, s, w, h, 14, numbers=False,
              cls_of=lambda i, hot=hot: ("a af", "ta") if i in hot else ("s f", "t"))
        f.line(x0 + 7 * w, y + h / 2, tx - 8, y + h / 2, "m", arrow=True)
        xe = chips_row(f, tx, y + 1, runs[s], size=13, hot=())
        f.text(xe + 14, y + h / 2 + 4.5, note, "ta" if hot else "tm", 12, weight=700 if hot else None)
    assert [len([1 for i, ch in enumerate(s) if ch == " "]) for s, _ in SPACES] == [0, 1, 0, 2]
    f.text(x0, ys[1] + h + 26, "1 -> 2 gives the same three tokens as 1->2: a space between two tokens changes nothing.",
           "tm", 11.5)
    f.text(x0, ys[3] + h + 26, "1--2 scans as 1, --, 2 although 1 - -2 may be what was meant; the parser, in module 02, "
                               "rejects it.", "tm", 11.5)
    return f


# ------------------------------------------------------------------ 01.03

NAMES = "return x1 _y int2 float"


def names():
    toks, out = L.tokens("01.03", NAMES + "\n")
    assert out.splitlines() == ["1:1 keyword return", "1:8 ident x1", "1:11 ident _y", "1:14 ident int2",
                                "1:19 ident float", "1:24 eof"], out
    tok_c = L.source("01.03", "tokenize.c")
    table = re.search(r"static bool is_keyword\(Token \*tok\) \{.*?static char \*kw\[\] = \{(.*?)\};", tok_c, re.S)[1]
    kws = re.findall(r'"([^"]+)"', table)
    assert len(kws) == 37 and "float" not in kws and "return" in kws and "int" in kws, kws
    f = Fig("f0103a", "A name: a letter or underscore, then letters, digits and underscores; then the keyword list",
            262)
    # the two states
    s1x, s2x, sy, sw_, sh_ = 24, 178, 78, 126, 52
    f.line(s1x - 2, sy - 22, s1x + 24, sy - 2, "s", arrow=True)
    f.text(s1x - 2, sy - 28, "is_ident1", "tm", 11, mono=True)
    for x, title, chars in ((s1x, "the first character", "a-z A-Z _"), (s2x, "every one after it", "a-z A-Z _ 0-9")):
        f.rect(x, sy, sw_, sh_, "s f", 10)
        f.text(x + sw_ / 2, sy + 20, title, "t", 12, "middle", 700)
        f.text(x + sw_ / 2, sy + 39, chars, "t", 12.5, "middle", mono=True)
    f.line(s1x + sw_ + 1, sy + sh_ / 2, s2x - 2, sy + sh_ / 2, "s", arrow=True)
    # the loop on the second state
    lx = s2x + sw_ / 2
    f.path(f"M{lx - 22} {sy - 1} C{lx - 26} {sy - 34} {lx + 26} {sy - 34} {lx + 22} {sy - 2}", "s", arrow=True)
    f.text(lx + 30, sy - 22, "is_ident2", "tm", 11, mono=True)
    # anything else ends the name: then the lookup
    f.line(s2x + sw_ / 2, sy + sh_ + 1, s2x + sw_ / 2, 176, "a", arrow=True)
    f.text(s2x + sw_ / 2 - 8, sy + sh_ + 22, "anything else:", "tm", 11, "end")
    f.text(s2x + sw_ / 2 - 8, sy + sh_ + 36, "the name is complete", "tm", 11, "end")
    f.rect(s1x, 180, s2x + sw_ - s1x, 52, "a af", 8)
    f.text(s1x + 14, 201, "convert_keywords, after the whole file:", "ta", 12, weight=700)
    f.text(s1x + 14, 220, f"is it one of is_keyword's {len(kws)} names?", "ta", 12, weight=700)
    # the five names
    nx, kx = 344, 456
    f.text(nx, 20, "./cc --tokens at 01.03", "tm", 11.5)
    by = 40
    for k, t in enumerate(toks[:-1]):
        y = by + k * 42
        name, kind = t[3], t[2]
        token_chip(f, nx + 38, y, name, "s fs", "t", 13.5, minw=76)
        hot = kind == "keyword"
        f.line(nx + 80, y + 13, kx - 4, y + 13, "s", arrow=True)
        f.rect(kx, y, 74, 26, "s f", 13)
        f.text(kx + 37, y + 17.5, kind, "t", 12.5, "middle", 700 if hot else 500, mono=True)
        note = {"float": ("not a keyword", "of this compiler"), "int2": ("a whole name:", "int2, not int")}.get(name)
        if note:
            f.text(kx + 84, y + 10, note[0], "tm", 11)
            f.text(kx + 84, y + 24, note[1], "tm", 11)
    return f


# ------------------------------------------------------------------ 01.04

LIT = "/* a comment */ \"a\\tb\" '\\n' 0x1F 017 0b101 // the end\n"
BYTES = [("main.c", '      fprintf(out, " %d", tok->str_len);\n',
          '      fprintf(out, " %d", tok->str_len);\n'
          '    if (tok->kind == TK_STR)\n'
          '      for (int i = 0; i < tok->str_len; i++)\n'
          '        fprintf(out, " %02x", (unsigned char)tok->str[i]);\n')]


def literals():
    toks, out = L.tokens("01.04", LIT)
    assert out.splitlines() == ['1:17 str "a\\tb" 3', "1:24 num '\\n' 10", "1:29 num 0x1F 31", "1:34 num 017 15",
                                "1:38 num 0b101 5", "1:54 eof"], out
    d = L.patched("01.04", "bytes", BYTES)
    o2, e2, s2 = L.cc("01.04", LIT, "--tokens", d=d)
    m = re.search(r'^1:17 str "a\\tb" 3 ((?:[0-9a-f]{2} ?)+)$', o2, re.M)
    assert m, o2
    hexes = m[1].split()
    assert hexes == ["61", "09", "62"], hexes
    line = LIT.rstrip("\n")
    f = Fig("f0104a", "One line of source, and what each token on it stands for once the scanner has read it", 250)
    size = 14
    c = L.cw(size)
    x0 = (640 - len(line) * c) / 2
    ly = 66
    f.text(24, 18, "lit.c, and ./cc --tokens lit.c at 01.04", "tm", 11.5)
    kinds = [None] * len(line)
    # the comments: skipped
    for a, b in ((0, line.index("*/") + 2), (line.index("//"), len(line))):
        for i in range(a, b):
            kinds[i] = "tm"
        f.path(f"M{x0 + a * c + 1} {ly - 18} V{ly - 24} H{x0 + b * c - 1} V{ly - 18}", "m", dash=True)
        f.text(x0 + (a + b) / 2 * c, ly - 30, "a comment: skipped", "tm", 11.5, "middle")
    spans = []
    i = 0
    while i < len(line):
        j = i
        while j < len(line) and kinds[j] == kinds[i]:
            j += 1
        if kinds[i]:
            spans.append((i, j, kinds[i]))
        i = j
    f.code(x0, ly, line, size, "t", spans)
    # each token: a bracket under it, a leader to its box
    boxes = [("str", ["3 bytes:"], hexes), ("num", ["a character:"], ["10"]), ("num", ["hexadecimal"], ["31"]),
             ("num", ["octal"], ["15"]), ("num", ["binary"], ["5"])]
    bw, by = 108, 140
    gap = (640 - 32 - 5 * bw) / 4
    for k, (t, (kind, sub, vals)) in enumerate(zip(toks[:-1], boxes)):
        a = t[1] - 1
        b = a + len(t[3])
        assert line[a:b] == t[3] and t[2] == kind
        x1, x2 = x0 + a * c + 1, x0 + b * c - 1
        f.path(f"M{x1} {ly + 8} V{ly + 14} H{x2} V{ly + 8}", "s")
        bx = 16 + k * (bw + gap)
        f.poly([((x1 + x2) / 2, ly + 14), ((x1 + x2) / 2, ly + 30), (bx + bw / 2, by - 24), (bx + bw / 2, by - 2)],
               "s", arrow=True)
        f.rect(bx, by, bw, 66, "s f", 8)
        f.text(bx + 10, by + 18, kind, "t", 12, weight=700, mono=True)
        f.text(bx + 42, by + 18, sub[0], "tm", 11)
        if kind == "str":
            for i, hx in enumerate(vals):
                f.rect(bx + 10 + i * 30, by + 30, 26, 24, "a af", 3)
                f.text(bx + 23 + i * 30, by + 47, hx, "ta", 12.5, "middle", 700, mono=True)
        else:
            f.text(bx + 12, by + 52, vals[0], "ta", 19, weight=700, mono=True)
    f.text(24, 232, "The string's bytes in hex: a, a tab, b. The character constant is a number token: 10, the "
                    "newline's code.", "tm", 11.5)
    return f


ESCAPES = [("\\a", "alert"), ("\\b", "backspace"), ("\\t", "tab"), ("\\n", "newline"), ("\\v", "vertical tab"),
           ("\\f", "form feed"), ("\\r", "carriage return"), ("\\\\", "backslash"), ("\\'", "single quote"),
           ("\\\"", "double quote"), ("\\?", "question mark"), ("\\0", "octal, one digit"),
           ("\\101", "octal, three digits"), ("\\x41", "hexadecimal")]


def escapes():
    src = " ".join(f"'{e}'" for e, _ in ESCAPES) + "\n"
    toks, out = L.tokens("01.04", src)
    vals = [t[4] for t in toks if t[2] == "num"]
    assert [t[3] for t in toks if t[2] == "num"] == [f"'{e}'" for e, _ in ESCAPES], out
    assert vals == [7, 8, 9, 10, 11, 12, 13, 92, 39, 34, 63, 0, 65, 65], vals
    eo, ee, es = L.cc("01.04", "'\\e'\n")
    assert (ee, es) == ("unknown escape sequence\n", 1), (ee, es)
    f = Fig("f0104b", "The escapes the scanner knows, and the byte each one becomes", 276)
    f.text(24, 18, "a character constant for each, through ./cc --tokens at 01.04", "tm", 11.5)
    cols = [(24, ESCAPES[:7], vals[:7]), (334, ESCAPES[7:], vals[7:])]
    rh = 27
    for x, rows, vs in cols:
        f.text(x + 8, 42, "written", "tm", 11)
        f.text(x + 110, 42, "byte", "tm", 11, "end")
        f.text(x + 150, 42, "hex", "tm", 11, "end")
        f.text(x + 166, 42, "what it is", "tm", 11)
        for k, ((e, what), v) in enumerate(zip(rows, vs)):
            y = 50 + k * rh
            if k % 2 == 0:
                f.rect(x, y, 282, rh - 4, "fs", 4, sw=False)
            f.code(x + 8, y + 16.5, f"'{e}'", 13.5, "t", weight=700)
            f.text(x + 110, y + 16.5, str(v), "ta", 13.5, "end", 700, mono=True)
            f.text(x + 150, y + 16.5, f"{v:02x}", "tm", 12, "end", mono=True)
            f.text(x + 166, y + 16, what, "t", 12)
    y = 50 + 7 * rh + 12
    f.rect(24, y, 592, 28, "m f", 6, dash=True)
    f.code(34, y + 19, "'\\e'", 13.5, "tm", weight=700)
    f.text(84, y + 19, "anything else is refused: ./cc says unknown escape sequence, at the backslash", "tm", 12)
    return f


# ------------------------------------------------------------------ 01.05

def caret_lines(name, text):
    out, err, st = L.cc("01.05", text, name=name)
    assert st == 1, (name, st)
    lines = err.splitlines()
    assert len(lines) == 2, err
    return lines


def caret():
    end = caret_lines("end.c", "1 +\n\t2 +\n")
    d = caret_lines("d.c", "1 + $\n")
    assert end == ["end.c:2: \t2 +", "         \t   ^ expected a number"], end
    assert d == ["d.c:1: 1 + $", "           ^ invalid token"], d
    f = Fig("f0105a", "The two lines of an error: the caret's column, and a tab answered with a tab", 346)
    w, h, size = 21, 30, 15
    TAB = 6                               # the tab drawn as six cells wide: any width, the same in both lines
    x0, y1 = 24, 58
    y2 = y1 + h + 6
    f.text(24, 18, "./cc end.c at 01.05, standard error; the second line of end.c starts with a tab", "tm", 11.5)

    def row(y, s, hot_tab):
        """Draw s a cell a byte, a tab TAB cells wide; return the x of each byte's cell."""
        xs, x = [], x0
        for ch in s:
            xs.append(x)
            cw_ = w * TAB if ch == "\t" else w
            if ch == "\t":
                f.rect(x, y, cw_, h, "a af" if hot_tab else "s fs", 0)
                f.text(x + cw_ / 2, y + h / 2 + 4.5, "a tab", "ta" if hot_tab else "t", 12, "middle", 700)
            else:
                f.rect(x, y, cw_, h, "s f", 0)
                if ch == " ":
                    f.circle(x + w / 2, y + h / 2, 1.5, "m")
                else:
                    f.text(x + w / 2, y + h / 2 + size * 0.36, ch, "t", size, "middle", 600, mono=True)
            x += cw_
        return xs, x

    pre = end[0].index("\t")
    assert pre == len("end.c:2: ") == 9
    xs1, e1 = row(y1, end[0], True)
    cpos = end[1].index("^")
    xs2, _ = row(y2, end[1][:cpos], True)
    cx = xs2[-1] + w
    f.text(cx + w / 2, y2 + h / 2 + size * 0.36, "^", "ta", size + 2, "middle", 700, mono=True)
    f.text(cx + w + 6, y2 + h / 2 + 5, end[1][cpos + 1:].strip(), "t", 13, mono=True)
    # brackets over the first line and under the second
    f.path(f"M{x0} {y1 - 6} V{y1 - 12} H{xs1[pre] - 2} V{y1 - 6}", "s")
    f.text(x0, y1 - 18, f"the prefix: end.c:2: and a space, {pre} characters", "t", 12)
    yb = y2 + h + 8
    f.path(f"M{x0} {yb} V{yb + 6} H{xs2[pre] - 2} V{yb}", "s")
    f.text(x0, yb + 24, f"{pre} spaces, as many as", "t", 12)
    f.text(x0, yb + 39, "the prefix printed", "t", 12)
    tx1, tx2 = xs2[pre], xs2[pre] + w * TAB
    f.path(f"M{tx1 + 2} {yb} V{yb + 6} H{tx2 - 2} V{yb}", "a")
    f.text(tx1 + 6, yb + 24, "a tab, for the", "ta", 12, weight=700)
    f.text(tx1 + 6, yb + 39, "tab above it", "ta", 12, weight=700)
    sx1, sx2 = xs2[pre + 1], cx
    f.path(f"M{sx1 + 2} {yb} V{yb + 6} H{sx2 - 2} V{yb}", "s")
    n_sp = cpos - pre - 1
    f.text(sx1 + 4, yb + 24, f"{n_sp} spaces,", "t", 12)
    f.text(sx1 + 4, yb + 39, "for 2, space, +", "t", 12)
    f.text(x0, yb + 64, "A terminal's tab can be any width; a tab under a tab ends where the one above ends.", "tm", 11.5)
    # the second example: no tab
    y3 = 246
    f.text(24, y3 - 12, "./cc d.c: no tab in the line, so spaces only", "tm", 11.5)
    w2, h2 = 17, 24
    for r, s in enumerate((d[0], d[1][:d[1].index("^") + 1])):
        for i, ch in enumerate(s):
            x, y = x0 + i * w2, y3 + r * (h2 + 4)
            hot = ch == "^"
            f.rect(x, y, w2, h2, "s f", 0)
            if ch == " ":
                f.circle(x + w2 / 2, y + h2 / 2, 1.4, "m")
            else:
                f.text(x + w2 / 2, y + h2 / 2 + 4.5, ch, "ta" if hot else "t", 12.5, "middle", 700 if hot else 600,
                       mono=True)
    k = d[1].index("^")
    f.text(x0 + (k + 1) * w2 + 6, y3 + h2 + 4 + h2 / 2 + 4.5, d[1][k + 1:].strip(), "t", 12.5, mono=True)
    dp = d[0].index(" 1") + 1
    yb = y3 + 2 * h2 + 12
    f.path(f"M{x0} {yb} V{yb + 6} H{x0 + dp * w2 - 2} V{yb}", "s")
    f.text(x0, yb + 22, f"{dp} for the prefix", "t", 12)
    f.path(f"M{x0 + dp * w2 + 2} {yb} V{yb + 6} H{x0 + k * w2 - 2} V{yb}", "s")
    f.text(x0 + dp * w2 + 4, yb + 22, f"{k - dp} for 1, space, +, space", "t", 12)
    return f


FIGS = [
    ("01.01-scan", scan, True),
    ("01.01-walker", walker, False),
    ("01.02-longest", longest, False),
    ("01.02-spaces", spaces, False),
    ("01.03-names", names, False),
    ("01.04-literals", literals, False),
    ("01.04-escapes", escapes, False),
    ("01.05-caret", caret, False),
]


def main(argv):
    for name, fn, stepped in FIGS:
        if argv and not any(name.startswith(a) for a in argv):
            continue
        write(name, fn(), stepped)


if __name__ == "__main__":
    main(sys.argv[1:])
