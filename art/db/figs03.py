"""Figures and module art for db module 03 (SQL): lessons 03.01-03.03.

    python3 art/db/figs03.py

writes tracks/db/lessons/03-sql/figures/*.svg, cover.svg and icon.svg. Every offset,
length and name below was taken from the engine's source or from a file it wrote
(xxd of the file, a token dump of next_token(), the engine's own output).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from figlib import Fig, tw  # noqa: E402

MOD = os.path.join(HERE, "..", "..", "tracks", "db", "lessons", "03-sql")


def save(name, fig):
    d = os.path.join(MOD, "figures") if name not in ("cover", "icon") else MOD
    os.makedirs(d, exist_ok=True)
    s = fig if isinstance(fig, str) else fig.svg()
    s.encode("ascii")
    with open(os.path.join(d, name + ".svg"), "w") as f:
        f.write(s)


def place_rows(items, rows, pad=8):
    """items: (center x, width, payload). Greedy: each label goes in the first row where it fits."""
    used = [[] for _ in rows]
    out = []
    for cx, w, p in items:
        x1, x2 = cx - w / 2, cx + w / 2
        if x1 < 4:
            cx += 4 - x1
            x1, x2 = 4, w + 4
        if x2 > 636:
            cx -= x2 - 636
            x1, x2 = 636 - w, 636
        for r, y in enumerate(rows):
            if all(x2 + pad <= a or x1 >= b + pad for a, b in used[r]):
                used[r].append((x1, x2))
                out.append((cx, y, p))
                break
        else:
            raise SystemExit(f"no room for label {p}")
    return out


# ------------------------------------------------------------------ 03.01

SQL1 = "SELECT price*2 FROM fruit WHERE name <> 'it''s'; -- hi"
# From a dump of next_token() over SQL1 (offset, length, type); spaces left out.
TOKENS1 = [(0, 6, "TK_SELECT", "kw"), (7, 5, "TK_ID", ""), (12, 1, "TK_STAR", ""), (13, 1, "TK_INTEGER", ""),
           (15, 4, "TK_FROM", "kw"), (20, 5, "TK_ID", ""), (26, 5, "TK_WHERE", "kw"), (32, 4, "TK_ID", ""),
           (37, 2, "TK_NE", ""), (40, 7, "TK_STRING", ""), (47, 1, "TK_SEMI", ""), (49, 5, "TK_SPACE", "sp")]


def tokens():
    f = Fig("f0301a", "next_token() cutting a statement into tokens", 210)
    x0, cw = 26, 10.8
    n = len(SQL1)
    f.text(24, 18, "the text, one byte per cell; each call to next_token() returns the token that starts there", "tm", 11)
    f.rect(x0 - 4, 48, n * cw + 8, 30, "fs", 6, sw=False)
    for i, ch in enumerate(SQL1):
        cx = x0 + i * cw + cw / 2
        if ch == " ":
            f.circle(cx, 63, 1.4, "m")
        else:
            f.text(cx, 69, ch, "t", 15, "middle", mono=True)
    above = {"TK_STAR", "TK_SEMI"}
    row = {"TK_INTEGER": 124}
    for off, ln, name, kind in TOKENS1:
        a, b = x0 + off * cw + 1.5, x0 + (off + ln) * cw - 1.5
        cx = (a + b) / 2
        cls = "a" if kind == "kw" else "m" if kind == "sp" else "s"
        tcls = "ta" if kind == "kw" else "tm" if kind == "sp" else "t"
        wt = 600 if kind == "kw" else None
        if name in above:
            f.line(cx, 46, cx, 40, "m")
            f.text(cx, 36, name, tcls, 10.5, "middle", wt, True)
            f.brace_h(a, b, 88, cls)
            continue
        f.brace_h(a, b, 88, cls)
        y = row.get(name, 106)
        if y != 106:
            f.line(cx, 90, cx, y - 11, "m")
        f.text(cx, y, name, tcls, 10.5, "middle", wt, True)
    xe = x0 + n * cw
    f.line(xe, 44, xe, 80, "m")
    f.text(xe + 4, 36, "TK_EOF", "tm", 10.5, "end", None, True)
    # ruler of byte offsets
    f.line(x0, 146, xe, 146, "m")
    for i in list(range(0, n, 10)) + [n]:
        x = x0 + i * cw
        f.line(x, 142, x, 150, "m")
        f.text(x, 162, str(i), "tm", 9.5, "middle", mono=True)
    f.text(24, 186, "Each dot is a one-byte TK_SPACE token, and so is the comment: every byte belongs to some token.", "tm", 11)
    f.text(24, 202, "The parser's advance() skips TK_SPACE, so it sees 11 tokens and then TK_EOF (length 0, at byte 54).", "tm", 11)
    return f


FIRST = [
    ("\\0  (NUL)", "the end of the text", "TK_EOF, length 0"),
    ("space \\t \\n \\r", "the whole run of white space", "TK_SPACE"),
    ("--   /*", "a comment, to the newline or the */", "TK_SPACE"),
    ("; ( ) , * + %", "one byte", "TK_SEMI TK_LP TK_RP ..."),
    ("-   /", "one byte, unless a comment starts", "TK_MINUS TK_SLASH"),
    ("= ! < > |", "look at the next byte as well", "TK_EQ TK_NE TK_LE ..."),
    ("' \" ` [", "scan_quoted(): to the closing quote", "TK_STRING (') or TK_ID"),
    ("0-9, or . 0-9", "scan_number(): digits, then . and e parts", "TK_INTEGER or TK_FLOAT"),
    ("x'  X'", "hex digits, an even number, then '", "TK_BLOB"),
    ("a-z A-Z _", "letters, digits, _ $, then keyword_type()", "a keyword, or TK_ID"),
    ("anything else", "one byte (a lone ! or | too)", "TK_ILLEGAL"),
]


def first_byte():
    rh = 23
    f = Fig("f0301b", "How next_token() decides what a token is from its first byte", 60 + len(FIRST) * rh + 10)
    f.text(24, 22, "switch (u[0]) in next_token(): the first byte (sometimes two) picks the rule", "tm", 11)
    f.text(30, 46, "first byte", "tm", 10.5, weight=600)
    f.text(176, 46, "what next_token() does", "tm", 10.5, weight=600)
    f.text(430, 46, "token type", "tm", 10.5, weight=600)
    for i, (first, what, typ) in enumerate(FIRST):
        y = 56 + i * rh
        hot = "scan_" in what or "keyword_type" in what
        f.rect(24, y, 136, rh - 5, "a af" if hot else "s fs", 4)
        f.text(32, y + 13, first, "ta" if hot else "t", 11, mono=True)
        f.line(164, y + 9, 172, y + 9, "m")
        f.text(176, y + 13, what, "t", 11)
        f.text(430, y + 13, typ, "tm" if typ.startswith("a ") else "t", 10.5, mono=not typ.startswith("a "))
    return f


def doubled_quote():
    f = Fig("f0301c", "scan_quoted() on 'it''s', with and without the doubled-quote case", 264)
    text = "'it''s';"
    x0, cw = 196, 34

    def cells(y):
        for i, ch in enumerate(text):
            x = x0 + i * cw
            f.rect(x, y, cw, 28, "s f" if i < 7 else "m fs", 0)
            f.text(x + cw / 2, y + 19, ch, "t" if i < 7 else "tm", 15, "middle", mono=True)
            f.text(x + cw / 2, y + 42, str(i), "tm", 9.5, "middle", mono=True)

    # as written
    f.text(24, 34, "as written", "t", 12, weight=600)
    f.text(24, 52, "n starts at 1; at u[3] the", "tm", 10.5)
    f.text(24, 66, "next byte is a quote too:", "tm", 10.5)
    f.text(24, 80, "n += 2, and keep going", "tm", 10.5)
    y = 42
    cells(y)
    f.path(f"M{x0 + 3 * cw + cw / 2} {y - 2} C {x0 + 3 * cw + cw / 2} {y - 22}, {x0 + 5 * cw + cw / 2} {y - 22}, {x0 + 5 * cw + cw / 2} {y - 4}", "a", arrow=True)
    f.text(x0 + 4.5 * cw, y - 22, "n += 2", "ta", 10.5, "middle", 600, True)
    f.brace_h(x0 + 2, x0 + 7 * cw - 2, y + 54, "a")
    f.text(x0 + 3.5 * cw, y + 72, "one TK_STRING, 7 bytes; parse_primary() makes it it's", "ta", 11, "middle")
    # without
    y2 = 162
    f.text(24, y2 - 8, "without the case", "t", 12, weight=600)
    f.text(24, y2 + 10, "the quote at u[3] closes", "tm", 10.5)
    f.text(24, y2 + 24, "the string; u[4] opens", "tm", 10.5)
    f.text(24, y2 + 38, "another one", "tm", 10.5)
    cells(y2)
    f.brace_h(x0 + 2, x0 + 4 * cw - 2, y2 + 54, "s")
    f.brace_h(x0 + 4 * cw + 2, x0 + 7 * cw - 2, y2 + 54, "s")
    f.text(x0 + 2 * cw, y2 + 72, "TK_STRING 'it'", "t", 11, "middle", mono=True)
    f.text(x0 + 5.5 * cw, y2 + 72, "TK_STRING 's'", "t", 11, "middle", mono=True)
    f.text(x0 + 8 * cw + 18, y2 + 19, "Error: near \"'s'\":", "ta", 11, mono=True)
    f.text(x0 + 8 * cw + 18, y2 + 35, "syntax error", "ta", 11, mono=True)
    return f


# ------------------------------------------------------------------ 03.02

def ast():
    f = Fig("f0302a", "The tree parse_select() builds for one SELECT", 272)
    f.rect(24, 10, 592, 30, "fs", 8, sw=False)
    f.text(320, 30, "SELECT a FROM t WHERE a > 1 ORDER BY b LIMIT 3;", "t", 13, "middle", 600, True)
    f.label_box(250, 58, 140, 30, "Stmt S_SELECT", "s f", "t", 12, weight=700)
    kids = [(78, "cols[0]", "E_COLUMN a", "s f"), (199, "table", "\"t\"", "s fs"), (320, "where", "E_GT", "a af"),
            (441, "order[0]", "E_COLUMN b", "s f"), (562, "limit", "E_INT 3", "s f")]
    for cx, field, label, cls in kids:
        w = max(64, tw(label, 11.5, True) + 22)
        f.label_box(cx - w / 2, 140, w, 28, label, cls, "ta" if cls.startswith("a") else "t", 11.5,
                    weight=600 if cls.startswith("a") else None)
        f.line(320 + (cx - 320) * 0.25, 88, cx, 138, "s")
        f.text(cx + (8 if cx >= 320 else -8), 130, field, "tm", 10.5, "start" if cx >= 320 else "end", None, True)
    f.text(441, 184, "ascending", "tm", 10.5, "middle")
    f.label_box(236, 208, 84, 28, "E_COLUMN a", "s f", "t", 11.5)
    f.label_box(334, 208, 64, 28, "E_INT 1", "s f", "t", 11.5)
    f.line(310, 168, 280, 206, "s")
    f.line(330, 168, 364, 206, "s")
    f.text(24, 262, "offset stays NULL. The names a, b and t are only text here: the tree says nothing yet about which table t is.", "tm", 10.5)
    return f


LADDER = [("8", "||"), ("7", "*  /  %"), ("6", "+  -"), ("5", "<  <=  >  >="), ("4", "= != IS IN LIKE BETWEEN"),
          ("", "NOT x: x read with min_prec 4"), ("2", "AND"), ("1", "OR"), ("0", "anything else: stop")]


def climbing():
    f = Fig("f0302b", "How 1 + 2 * 3 - 4 groups, and the binding strengths op_prec() gives", 300)
    f.text(24, 20, "the tokens, with how tightly each operator binds", "tm", 11)
    toks = ["1", "+", "2", "*", "3", "-", "4"]
    prec = {"+": "6", "*": "7", "-": "6"}
    for i, t in enumerate(toks):
        x = 24 + i * 46
        op = t in prec
        f.rect(x, 30, 38, 28, "a af" if op else "s f", 5)
        f.text(x + 19, 49, t, "ta" if op else "t", 14, "middle", mono=True)
        if op:
            f.text(x + 19, 74, prec[t], "tm", 10.5, "middle", mono=True)
    nodes = {"-": (250, 112, "op"), "+": (170, 166, "op"), "4": (330, 166, ""), "1": (120, 220, ""),
             "*": (220, 220, "op"), "2": (180, 274, ""), "3": (260, 274, "")}
    edges = [("-", "+"), ("-", "4"), ("+", "1"), ("+", "*"), ("*", "2"), ("*", "3")]
    for a, b in edges:
        (x1, y1, _), (x2, y2, _) = nodes[a], nodes[b]
        f.line(x1, y1 + 13, x2, y2 - 13, "s")
    for name, (x, y, kind) in nodes.items():
        f.label_box(x - 18, y - 13, 36, 26, name, "a af" if kind else "s f", "ta" if kind else "t", 13)
    f.text(276, 117, "= 3", "t", 12, weight=600, mono=True)
    f.text(24, 112, "the tree", "tm", 11)
    f.text(250, 216, "* binds tighter than +,", "tm", 10.5)
    f.text(250, 231, "so 2 * 3 is grouped first", "tm", 10.5)
    f.text(24, 132, "- binds no tighter than +,", "tm", 10.5)
    f.text(24, 147, "so it takes 1 + 2 * 3 whole", "tm", 10.5)
    lx = 436
    f.text(lx, 96, "op_prec(): higher binds tighter", "tm", 10.5)
    for i, (p, ops) in enumerate(LADDER):
        y = 106 + i * 20
        if p:
            f.rect(lx, y, 180, 17, "s fs" if p != "0" else "m f", 3, dash=p == "0")
            f.text(lx + 10, y + 12.5, p, "ta", 10.5, "middle", 600, True)
            f.text(lx + 24, y + 12.5, ops, "t" if p != "0" else "tm", 10.5, mono=p != "0")
        else:
            f.text(lx + 24, y + 12.5, ops, "tm", 10)
    return f


def assoc():
    f = Fig("f0302c", "10 - 4 - 3 parsed with prec + 1, and with prec", 236)

    def tree(cx, title, sub, shape, val, cls):
        f.text(cx, 22, title, "t", 12, "middle", 600, True)
        f.text(cx, 40, sub, "tm", 10.5, "middle")
        top = (cx, 70)
        f.label_box(cx - 20, 56, 40, 26, "-", "a af", "ta", 14)
        if shape == "left":
            inner, leaf = (cx - 60, 124), (cx + 60, 124)
            f.label_box(inner[0] - 20, 110, 40, 26, "-", "a af", "ta", 14)
            f.label_box(leaf[0] - 20, 110, 40, 26, "3", "s f", "t", 13)
            kids = [(inner[0] - 44, "10"), (inner[0] + 44, "4")]
        else:
            leaf, inner = (cx - 60, 124), (cx + 60, 124)
            f.label_box(leaf[0] - 20, 110, 40, 26, "10", "s f", "t", 13)
            f.label_box(inner[0] - 20, 110, 40, 26, "-", "a af", "ta", 14)
            kids = [(inner[0] - 44, "4"), (inner[0] + 44, "3")]
        f.line(top[0] - 8, 82, inner[0] if shape == "left" else leaf[0], 109, "s")
        f.line(top[0] + 8, 82, leaf[0] if shape == "left" else inner[0], 109, "s")
        for kx, kv in kids:
            f.label_box(kx - 20, 164, 40, 26, kv, "s f", "t", 13)
            f.line(inner[0] + (-6 if kx < inner[0] else 6), 136, kx, 163, "s")
        f.text(cx, 214, val, cls, 12, "middle", 600, True)

    tree(170, "parse_binary(ps, prec + 1)", "as written: a - b - c is (a - b) - c", "left", "((10 - 4) - 3) = 3", "t")
    tree(470, "parse_binary(ps, prec)", "the right side takes the next - too", "right", "(10 - (4 - 3)) = 9", "ta")
    f.line(320, 20, 320, 220, "m", dash=True)
    return f


# ------------------------------------------------------------------ 03.03

def page1():
    f = Fig("f0303a", "Page 1 of schema.db after CREATE TABLE fruit and CREATE TABLE veg", 280)
    f.text(24, 18, "page 1 of schema.db, 4096 bytes (from xxd; not to scale)", "tm", 11)
    segs = [(0, 100, 150, "database header", "s fs", "t"), (100, 112, 84, "leaf header", "s f", "t"),
            (112, 3977, 120, "free", "m", "tm"), (3977, 4019, 108, "row 2: veg", "a af", "ta"),
            (4019, 4096, 128, "row 1: fruit", "a af", "ta")]
    x, y = 26, 30
    xs = {}
    for a, b, w, name, cls, tcls in segs:
        f.rect(x, y, w, 34, cls, 0, dash=name == "free")
        f.text(x + w / 2, y + 21, name, tcls, 11.5, "middle", 600 if tcls == "ta" else None)
        if a in (0, 100, 3977, 4019):
            f.text(x, y + 50, str(a), "tm", 9.5, "middle" if a else "start", mono=True)
        xs[name] = (x, w)
        x += w
    f.text(x, y + 50, "4096", "tm", 9.5, "end", mono=True)
    f.text(26, 108, "offset 40 of the header: the schema cookie, 2 (one bump per CREATE)", "tm", 10.5)
    f.text(616, 108, "the rows grow down from the end of the page", "tm", 10.5, "end")
    cols = [("type", 26), ("name", 76), ("tbl_name", 122), ("rootpage", 190), ("sql", 262)]
    for name, cx in cols:
        f.text(cx, 142, name, "tm", 10.5, weight=600, mono=True)
    f.line(24, 148, 616, 148, "m")
    rows = [("table", "fruit", "fruit", "2", "CREATE TABLE fruit(id INTEGER PRIMARY KEY, name TEXT)"),
            ("table", "veg", "veg", "3", "CREATE TABLE veg(name)")]
    for i, r in enumerate(rows):
        yy = 166 + i * 22
        for (name, cx), v in zip(cols, r):
            if name == "rootpage":
                f.text(cx + 26, yy, v, "ta", 12, "middle", 600, True)
            else:
                f.text(cx, yy, v, "t", 10 if name == "sql" else 11, mono=True)
    for i, (pg, what) in enumerate((("page 2", "fruit's B-tree: one empty leaf"), ("page 3", "veg's B-tree: one empty leaf"))):
        x0 = 26 + i * 300
        f.rect(x0, 236, 290, 30, "s f", 6)
        f.text(x0 + 12, 255, pg, "ta", 11.5, weight=600, mono=True)
        f.text(x0 + 70, 255, what, "t", 11)
    f.path("M226 162 C 246 162, 246 214, 170 234", "a", arrow=True)
    f.path("M226 184 C 246 196, 420 204, 470 234", "a", arrow=True)
    return f


STEPS3 = [
    ("read the statement", "parse_create()", "keep its text from the name on, for the catalog", None),
    ("check it can be honoured", "create_table()", "no unsupported feature, no reserved or taken name, no column twice", None),
    ("give the table a root page", "btree_create()", "an empty table leaf; the file grows by one page", "page 2 (new)"),
    ("write its catalog row", "schema_insert_row()", "table, fruit, fruit, 2, and the CREATE text", "page 1"),
    ("bump the schema cookie", "schema_bump_cookie()", "header offset 40: 0 -> 1", "page 1"),
    ("commit", "pager_commit()", "both dirty pages go to the file", "pages 1, 2"),
    ("rebuild the catalog in memory", "schema_load()", "from page 1, exactly as when the file is opened", None),
]


def create():
    f = Fig("f0303b", "What CREATE TABLE does, in order", 310)
    f.text(24, 22, "CREATE TABLE fruit(id INTEGER PRIMARY KEY, name TEXT);", "t", 12, mono=True, weight=600)
    f.text(24, 40, "on an empty file, which has just been given its page 1 and header", "tm", 10.5)
    f.line(40, 68, 40, 68 + (len(STEPS3) - 1) * 34, "m")
    for i, (title, fn, what, page) in enumerate(STEPS3):
        y = 68 + i * 34
        hot = page is not None
        f.circle(40, y, 5, "a fa" if hot else "s f")
        f.text(56, y + 4, title, "ta" if hot else "t", 12, weight=600)
        f.text(56 + tw(title, 12) + 14, y + 4, fn, "tm", 10.5, mono=True)
        f.text(56, y + 19, what, "tm", 10.5)
        if page:
            f.rect(512, y - 10, 104, 22, "a af", 5)
            f.text(564, y + 5, page, "ta", 11, "middle", 600)
            f.line(470, y, 508, y, "m", dash=True)
    f.text(564, 56, "what it changes", "tm", 10.5, "middle")
    return f


def catalog():
    f = Fig("f0303c", "schema_load(): the catalog in memory, rebuilt from the rows of page 1", 236)
    f.text(24, 20, "rows of sqlite_schema, on page 1", "tm", 11)
    f.text(334, 20, "the catalog in memory (after the built-in sqlite_schema)", "tm", 11)
    rows = [("fruit", "2", ["CREATE TABLE fruit(id INTEGER", "PRIMARY KEY, name TEXT)"]),
            ("veg", "3", ["CREATE TABLE veg(name)"])]
    tabs = [("fruit", "root 2; id is the rowid", [("id", "INTEGER", "affinity INTEGER"), ("name", "TEXT", "affinity TEXT")]),
            ("veg", "root 3; no rowid column", [("name", "(none)", "affinity BLOB")])]
    y = 32
    for (name, root, sql), (tname, sub, cl) in zip(rows, tabs):
        h = 32 + 16 * max(len(sql), len(cl))
        f.rect(24, y, 230, h, "s fs", 6)
        f.text(36, y + 18, f"table  {name}  root {root}", "t", 11, weight=600, mono=True)
        for k, line in enumerate(sql):
            f.text(36, y + 38 + 16 * k, line, "t", 10.5, mono=True)
        f.line(258, y + h / 2, 330, y + h / 2, "a", arrow=True)
        f.text(294, y + h / 2 - 8, "parse", "ta", 10.5, "middle", 600)
        f.rect(334, y, 282, h, "s f", 6)
        f.text(346, y + 18, tname, "t", 12, weight=700, mono=True)
        f.text(604, y + 18, sub, "tm", 10.5, "end")
        for k, (cn, ct, ca) in enumerate(cl):
            f.text(346, y + 38 + 16 * k, cn, "t", 10.5, mono=True)
            f.text(392, y + 38 + 16 * k, ct, "t", 10.5, mono=True)
            f.text(460, y + 38 + 16 * k, ca, "tm", 10.5, mono=True)
        y += h + 22
    f.text(24, 206, "Every open does this, and so does every CREATE and DROP: the column names, types and", "tm", 11)
    f.text(24, 222, "affinities are stored nowhere but in the CREATE text, so the engine parses it again.", "tm", 11)
    return f


# ------------------------------------------------------------------ module art

def cover():
    f = Fig("m03", "SQL text becomes tokens, a tree, and rows of the catalog on page 1", 300)
    f.rect(24, 22, 592, 40, "fs", 10, sw=False)
    f.text(44, 48, "SELECT name FROM fruit WHERE price > 0.5;", "t", 15, mono=True)
    f.text(24, 92, "tokens", "tm", 11)
    toks = [("SELECT", 1), ("name", 0), ("FROM", 1), ("fruit", 0), ("WHERE", 1), ("price", 0), (">", 0), ("0.5", 0), (";", 0)]
    x = 24
    for t, kw in toks:
        w = tw(t, 12, True) + 16
        f.rect(x, 102, w, 24, "a af" if kw else "s f", 12)
        f.text(x + w / 2, 118, t, "ta" if kw else "t", 12, "middle", 600 if kw else None, True)
        x += w + 8
    f.text(24, 160, "tree", "tm", 11)
    f.label_box(150, 150, 86, 26, "SELECT", "s f", "t", 12, weight=600)
    f.label_box(64, 214, 70, 26, "name", "s f", "t", 12)
    f.label_box(150, 214, 70, 26, "fruit", "s f", "t", 12)
    f.label_box(236, 214, 50, 26, ">", "a af", "ta", 13)
    f.label_box(196, 258, 60, 24, "price", "s f", "t", 11)
    f.label_box(266, 258, 50, 24, "0.5", "s f", "t", 11)
    for x2 in (99, 185, 261):
        f.line(193, 176, x2, 213, "s")
    f.line(255, 240, 226, 257, "s")
    f.line(267, 240, 291, 257, "s")
    f.text(380, 160, "catalog: sqlite_schema on page 1", "tm", 11)
    f.rect(380, 172, 236, 96, "s fs", 10)
    f.text(394, 196, "table fruit fruit 2", "t", 12, mono=True)
    f.text(394, 214, "CREATE TABLE fruit(...)", "tm", 11, mono=True)
    f.line(394, 228, 602, 228, "m")
    f.text(394, 250, "table veg veg 3", "t", 12, mono=True)
    f.path("M330 214 C 352 214, 356 200, 378 200", "a", arrow=True)
    f.text(354, 236, "fruit?", "ta", 11, "middle", 600, True)
    return f


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="10" cy="4.5" r="2"/><circle cx="5" cy="15.5" r="2"/><circle cx="15" cy="15.5" r="2"/>'
        '<path d="M9 6.3L6 13.7M11 6.3l3 7.4"/></svg>\n')


def main():
    for name, fn in (("03.01-tokens", tokens), ("03.01-first-byte", first_byte), ("03.01-doubled-quote", doubled_quote),
                     ("03.02-tree", ast), ("03.02-climbing", climbing), ("03.02-assoc", assoc),
                     ("03.03-page1", page1), ("03.03-create", create), ("03.03-catalog", catalog)):
        save(name, fn())
    save("cover", cover())
    save("icon", ICON)
    print("wrote module 03 figures, cover and icon to", os.path.normpath(MOD))


if __name__ == "__main__":
    main()
