"""Figures for cc module 02, Expressions (lessons 02.01 to 02.06).

    python3 -B art/cc/figs02.py [name-prefix ...]
                writes tracks/cc/lessons/02-expressions/figures/02.0N-*.svg

Every tree, instruction and value here is from a real run of ./cc in the project as the site shows
it at the lesson (./learn files cc --at 02.0N, make -s: figlib.project), and NOTES.md's transcripts
are asserted:

  02.01-grammar      the rule comments and the lines of expr, add and primary in parse.c at 02.01,
                     each line drawn checked against the file (a long one wrapped, the "-" branch
                     named, not repeated)
  02.01-descent      stepped: a scratch copy of 02.01 whose parse.c reports every call of expr, add
                     and primary (with the token it starts at and the one after what it read) and
                     every node new_binary and new_num make (trace()): one step a call or a return,
                     the node a call made joined to its return; the tree at the end is --tree's
  02.02-shape        --tree at 02.02 of 1 + 2 * 3 and (1 + 2) * 3; their values, 7 and 9, from
                     ./ccrun at 02.03, where the code is first made from the tree
  02.02-dropped      the same trace at 02.02 for (1 + 2) * 3: the calls nested as they ran and the
                     tokens each read itself; against the five nodes of --tree
  02.03-registers    stepped: ./cc at 02.03 on 1 + 2 * 3, the five instructions NOTES.md and the
                     outline cover give; gen() re-enacts codegen.c's walk, and must write the same
                     lines, which ties each instruction to its node; the registers by
                     figlib.simulate; t0 ends 7
  02.03-depth        the same walk: the register each node of 1 + 2 * 3 is computed into
  02.04-ladder       the rule comments of parse.c at 02.01 to 02.05: the levels from loosest to
                     tightest, each level's operators, and the first lesson whose parse.c has it
  02.04-tree         --tree at 02.04 of 6 % 4 << 2 | 1, each operator's level from the same
                     comments; ./ccrun gives 9
  02.05-two-from-four --tree at 02.05 of 1 < 2, 1 <= 2, 1 > 2 and 1 >= 2
  02.05-instructions ./cc at 02.05 on 1 == 2, 1 != 2, 1 < 2, 1 <= 2, -1, !1 and ~1, the
                     instructions after the operands' li; t0 by figlib.simulate
  02.06-spill        stepped: ./cc at 02.06 on try.c, NOTES.md's 23 instructions; gen() writes the
                     same; simulated from sp = stack_top (0x80010040, where _start leaves it):
                     t0 ends 4, sp back where it started; ./ccrun exits 4
  02.06-leaning      ./cc at 02.06 on the right-leaning try.c and the same seven subtractions
                     leaning left: the highest register each reaches and its spills (sd)
The maps, the cover and the icon are not made here (archmap.py; art/outlines/cc_art.py).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figlib as L  # noqa: E402
from figlib import Fig, write, steps  # noqa: E402

REG = ["t0", "t1", "t2", "t3", "t4", "t5"]
INSN = {"+": "add", "-": "sub", "*": "mul", "/": "div", "%": "rem", "&": "and", "|": "or", "^": "xor",
        "<<": "sll", ">>": "sra"}


# ------------------------------------------------------------------ the parser's trace

def trace(at, src):
    """Run --tree on src in a scratch copy of the project at `at` whose parse.c reports, on
    standard error, every call of its parsing functions and every node it makes. Returns the
    events [("enter", name, col), ("leave", name, node, col), ("make", node, label, lhs, rhs)]
    (node ids are addresses as text; label is the operator or the number) and the tree."""
    text = L.source(at, "parse.c")
    names = re.findall(r"^static Node \*(\w+)\(Token \*\*rest, Token \*tok\) \{$", text, re.M)
    assert names, at
    protos = "".join(f"static Node *{n}__real(Token **rest, Token *tok);\n" for n in names)
    protos += ("static Node *new_binary(NodeKind kind, Node *lhs, Node *rhs, Token *tok);\n"
               "static Node *new_num(long val, Token *tok);\n")
    edits = [("parse.c", '#include "cc.h"\n', '#include "cc.h"\n' + protos)]
    for n in names:
        edits.append(("parse.c", f"static Node *{n}(Token **rest, Token *tok) {{\n",
                      f"static Node *{n}__real(Token **rest, Token *tok) {{\n"))
    edits.append(("parse.c", "static Node *new_binary(NodeKind kind, Node *lhs, Node *rhs, Token *tok) {\n",
                  "static Node *new_binary__real(NodeKind kind, Node *lhs, Node *rhs, Token *tok) {\n"))
    edits.append(("parse.c", "static Node *new_num(long val, Token *tok) {\n",
                  "static Node *new_num__real(long val, Token *tok) {\n"))
    wrappers = "\n// the figures' trace\n"
    for n in names:
        wrappers += (f"static Node *{n}(Token **rest, Token *tok) {{\n"
                     f'  fprintf(stderr, "enter {n} %d\\n", tok->col);\n'
                     f"  Node *n = {n}__real(rest, tok);\n"
                     f'  fprintf(stderr, "leave {n} %p %d\\n", (void *)n, (*rest)->col);\n'
                     f"  return n;\n}}\n")
    wrappers += ("static Node *new_binary(NodeKind kind, Node *lhs, Node *rhs, Token *tok) {\n"
                 "  Node *n = new_binary__real(kind, lhs, rhs, tok);\n"
                 '  fprintf(stderr, "make %p %.*s %p %p\\n", (void *)n, tok->len, tok->loc, (void *)lhs, (void *)rhs);\n'
                 "  return n;\n}\n"
                 "static Node *new_num(long val, Token *tok) {\n"
                 "  Node *n = new_num__real(val, tok);\n"
                 '  fprintf(stderr, "make %p %ld - -\\n", (void *)n, val);\n'
                 "  return n;\n}\n")
    edits.append(("parse.c", None, wrappers))
    d = L.patched(at, "trace", edits)
    out, err, st = L.cc(at, src, "--tree", d=d)
    assert st == 0, err
    want, _ = L.tree(at, src)
    assert L.parse_tree(out) == want, (out, want)
    ev = []
    for ln in err.splitlines():
        p = ln.split()
        if p[0] == "enter":
            ev.append(("enter", p[1], int(p[2])))
        elif p[0] == "leave":
            ev.append(("leave", p[1], p[2], int(p[3])))
        else:
            ev.append(("make", p[1], p[2], p[3], p[4]))
    return ev, want


def forest(made):
    """The trees built so far, from make events: {node: (label, lhs, rhs)} -> roots in order."""
    kids = {c for _, (lab, l, r) in made.items() for c in (l, r) if c != "-"}
    return [n for n in made if n not in kids]


# ------------------------------------------------------------------ code generation, re-enacted

def gen(t, nreg=6):
    """codegen.c's gen_expr walk on a tree from figlib.parse_tree: [(line, node path, d)] for the
    expression's instructions, then mv a0, t0. The caller asserts the lines are ./cc's."""
    out = []

    def binary(op, rd, rs1, rs2, path):
        if op in INSN:
            out.append((f"{INSN[op]} {rd}, {rs1}, {rs2}", path))
        elif op == "==":
            out.extend([(f"xor {rd}, {rs1}, {rs2}", path), (f"seqz {rd}, {rd}", path)])
        elif op == "!=":
            out.extend([(f"xor {rd}, {rs1}, {rs2}", path), (f"snez {rd}, {rd}", path)])
        elif op == "<":
            out.append((f"slt {rd}, {rs1}, {rs2}", path))
        elif op == "<=":
            out.extend([(f"slt {rd}, {rs2}, {rs1}", path), (f"xori {rd}, {rd}, 1", path)])
        else:
            raise ValueError(op)

    def expr(t, d, path):
        op, val, kids = t
        if op == "num":
            out.append((f"li {REG[d]}, {val}", path))
            return
        if len(kids) == 1:
            expr(kids[0], d, path + (0,))
            out.append(({"-": f"neg {REG[d]}, {REG[d]}", "!": f"seqz {REG[d]}, {REG[d]}",
                         "~": f"not {REG[d]}, {REG[d]}"}[op], path))
            return
        expr(kids[0], d, path + (0,))
        if d + 1 == nreg:
            out.append(("addi sp, sp, -16", path))
            out.append((f"sd {REG[d]}, 0(sp)", path))
            expr(kids[1], d, path + (1,))
            out.append(("ld t6, 0(sp)", path))
            out.append(("addi sp, sp, 16", path))
            binary(op, REG[d], "t6", REG[d], path)
            return
        expr(kids[1], d + 1, path + (1,))
        binary(op, REG[d], REG[d], REG[d + 1], path)

    expr(t, 0, ())
    out.append(("mv a0, t0", None))
    return out


def checked_gen(at, src):
    """gen() of --tree's tree, asserted to be exactly what ./cc writes for src at `at`."""
    t, _ = L.tree(at, src)
    lines = L.asm(at, src)
    g = gen(t)
    assert lines[:2] == ["  .globl main", "main:"] and lines[-1] == "  ret", lines
    assert [ln.strip() for ln in lines[2:-1]] == [s for s, _ in g], (lines, g)
    return t, g, lines


def node_regs(t, g):
    """The register each node's value ends in: the destination of the node's last instruction,
    and for a number the li's."""
    out = {}
    for s, p in g:
        if p is not None:
            out[p] = s.split()[1].rstrip(",")
    return out


# ------------------------------------------------------------------ 02.01

GRAMMAR_0201 = ["expr = add", 'add = primary ("+" primary | "-" primary)*', "primary = num"]


def grammar():
    src = L.source("02.01", "parse.c")
    rules = re.findall(r"^  // (\w+ = .*)$", src, re.M)
    assert rules == GRAMMAR_0201, rules
    flat = [ln.strip() for ln in src.splitlines()]
    # (function, its lines as drawn): each line is in parse.c as written, the one wrapped line once
    # joined; the "-" branch is named, not repeated
    funcs = [
        ("expr", ["static Node *expr(Token **rest, Token *tok) {", "  return add(rest, tok);", "}"]),
        ("add", ["static Node *add(Token **rest, Token *tok) {", "  Node *node = primary(&tok, tok);", "",
                 "  for (;;) {", "    Token *start = tok;", "", '    if (equal(tok, "+")) {',
                 "      node = new_binary(ND_ADD, node,", "          primary(&tok, tok->next), start);",
                 "      continue;", "    }", '    if (equal(tok, "-")) ...  the same, ND_SUB', "",
                 "    *rest = tok;", "    return node;", "  }", "}"]),
        ("primary", ["static Node *primary(Token **rest, Token *tok) {", "  if (tok->kind == TK_NUM) {",
                     "    Node *node = new_num(tok->val, tok);", "    *rest = tok->next;", "    return node;",
                     "  }", '  error_tok(tok, "expected an expression");', "}"]),
    ]
    for _, lines in funcs:
        k = 0
        while k < len(lines):
            ln = lines[k].strip()
            if ln.endswith("node,"):                         # the wrapped new_binary line
                ln = ln + " " + lines[k + 1].strip()
                k += 1
            if ln and "..." not in ln:
                assert ln in flat, ln
            elif "..." in ln:
                assert '    if (equal(tok, "-")) {' in src and "ND_SUB, node, primary(&tok, tok->next), start)" in src
            k += 1
    # the rules' comment lines are at the top of each function
    for name, rule in zip(("expr", "add", "primary"), rules):
        assert re.search(r"static Node \*" + name + r"\(Token \*\*rest, Token \*tok\) \{\n  // " + re.escape(rule),
                         src), name
    rh, size = 13.6, 10.5
    c = L.cw(size)
    cx0 = 268                                  # the code's left edge
    f = Fig("f0201a", "Three rules, three functions: each function reads exactly what its rule describes", 0)
    f.text(24, 18, "the rules, from parse.c's comments", "tm", 11.5)
    f.text(cx0, 18, "the functions in parse.c at 02.01", "tm", 11.5)
    y = 36
    # rule rows: where each use sits in the rule text, and which code line and call it becomes
    uses = {
        "expr": [("add", "add(rest, tok)", 1)],
        "add": [("primary", "primary(&tok, tok)", 1), ('"+" primary', "primary(&tok, tok->next)", 8),
                ('"-" primary', 'equal(tok, "-")', 11)],
        "primary": [("num", "TK_NUM", 1)],
    }
    rule_lines = {"expr": ["expr = add"], "add": ["add = primary", '  ("+" primary | "-" primary)*'],
                  "primary": ["primary = num"]}
    for (name, lines), rule in zip(funcs, rules):
        top = y
        h = len(lines) * rh + 10
        f.rect(cx0 - 8, top, 640 - 16 - cx0 + 8, h, "s fs", 6)
        line_y = [top + 15 + k * rh for k in range(len(lines))]
        for k, ln in enumerate(lines):
            if "..." in ln:
                head = ln.split("...")[0] + "..."
                sp = [(head.index(call), head.index(call) + len(call), "ta") for word, call, row in uses[name]
                      if row == k and call in head]
                f.code(cx0, line_y[k], head, size, "t", sp)
                f.text(cx0 + len(ln.split("...")[0] + "...") * c + 8, line_y[k], ln.split("...")[1].strip(), "tm",
                       10.5)
                continue
            spans = []
            for word, call, row in uses[name]:
                if row == k and call in ln:
                    a = ln.index(call)
                    spans.append((a, a + len(call), "ta"))
            hdr = ln.startswith("static Node *")
            if hdr:
                a = ln.index(name + "(")
                spans.append((a, a + len(name), "t"))
            f.code(cx0, line_y[k], ln, size, "t", spans, weight=None)
        # the rule, beside its function's first line
        rl = rule_lines[name]
        for i, r in enumerate(rl):
            f.code(24, line_y[0] + i * 17, r, 12, "t", spans=[(0, len(name), "t")] if i == 0 else (),
                   weight=None)
        f.code(24, line_y[0], name, 12, "t", weight=700)
        # rule -> function
        rx = 24 + len(rl[0]) * L.cw(12) + 8
        f.line(rx, line_y[0] - 4, cx0 - 12, line_y[0] - 4, "s", arrow=True)
        # each use of a rule name -> the call it becomes
        for word, call, row in uses[name]:
            ri = 0 if word in rl[0][len(name) + 3:] or len(rl) == 1 else 1
            r = rl[ri]
            a = r.index(word, len(name) + 3 if ri == 0 else 0)
            wx0, wx1 = 24 + a * L.cw(12), 24 + (a + len(word)) * L.cw(12)
            wy = line_y[0] + ri * 17 + 4
            f.line(wx0, wy, wx1, wy, "a")
            ty = line_y[row] - 4
            mid = (wx0 + wx1) / 2
            f.path(f"M{mid:.1f} {wy + 1} C{mid:.1f} {ty:.1f} {cx0 - 60} {ty:.1f} {cx0 - 12} {ty:.1f}", "a", arrow=True)
        y = top + h + 14
    f.h = y + 4
    return f


def descent():
    src = L.source("02.01", "try.c")
    assert src == "5 + 20 - 4\n", src
    ev, want = trace("02.01", src)
    toks, _ = L.tokens("02.01", src)
    col_ix = {t[1]: i for i, t in enumerate(toks)}
    f = Fig("f0201b", "Parsing 5 + 20 - 4: the function running, the token it looks at, the tree so far", 300)
    tx, ty = 24, 40
    f.text(24, 20, "the tokens", "tm", 11.5)
    tok_x = []
    x = tx
    for t in toks:
        lab = t[3] if t[2] != "eof" else "EOF"
        w = max(30, L.tw(lab, 14, True) + 18)
        tok_x.append((x, w))
        f.rect(x, ty, w, 30, "s fs" if t[2] != "eof" else "m f", 5, dash=t[2] == "eof")
        f.text(x + w / 2, ty + 20, lab, "t" if t[2] != "eof" else "tm", 14 if t[2] != "eof" else 11, "middle", 600,
               mono=True)
        x += w + 10
    # the stack of calls, and the tree, in the places the final tree gives
    sx, sy0 = 24, 276               # the stack's floor: parse, which calls expr
    sw_, sh_ = 150, 30
    f.text(sx, 112, "the functions running, the last called on top", "tm", 11.5)
    f.rect(sx, sy0 - sh_, sw_, sh_, "s f", 6)
    f.text(sx + 12, sy0 - 10, "parse", "t", 13.5, weight=500, mono=True)
    f.text(330, 112, "the tree so far", "tm", 11.5)
    pos, edges = L.layout(want, 340, 150, 86, 52)
    final = {}
    # match the trace's nodes to --tree's: by building the final tree from the make events
    made_all = {e[1]: (e[2], e[3], e[4]) for e in ev if e[0] == "make"}
    root_ptr = next(e for e in reversed(ev) if e[0] == "leave" and e[1] == "expr")[2]

    def place(ptr, path):
        lab, l, r = made_all[ptr]
        final[ptr] = path
        if l != "-":
            place(l, path + (0,))
            place(r, path + (1,))
    place(root_ptr, ())
    at = {p: (x, y) for p, _, x, y in pos}
    labels = {p: L.label(*ov) for p, ov, x, y in pos}
    for ptr, path in final.items():
        assert labels[path] == made_all[ptr][0], (labels[path], made_all[ptr])

    def draw_state(stack, cur_col, made, hot):
        # the current token
        if cur_col is not None:
            k = col_ix[cur_col]
            x, w = tok_x[k]
            f.rect(x - 3, ty - 3, w + 6, 36, "a", 7)
            f.path(f"M{x + w / 2 - 6} {ty + 44} L{x + w / 2} {ty + 37} L{x + w / 2 + 6} {ty + 44}", "a")
        # the stack, bottom up, over parse
        for i, name in enumerate(["parse"] + stack):
            y = sy0 - sh_ - i * (sh_ + 6)
            if i == len(stack):
                f.rect(sx, y, sw_, sh_, "a af", 6)
                f.text(sx + 12, y + 20, name, "ta", 13.5, weight=700, mono=True)
            elif i:
                f.rect(sx, y, sw_, sh_, "s f", 6)
                f.text(sx + 12, y + 20, name, "t", 13.5, weight=500, mono=True)
        # the nodes made so far, and the edges between them
        for ptr in made:
            lab, l, r = made[ptr]
            if l != "-":
                for ch in (l, r):
                    (x1, y1), (x2, y2) = at[final[ptr]], at[final[ch]]
                    dd = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                    ux, uy = (x2 - x1) / dd, (y2 - y1) / dd
                    f.line(x1 + ux * 17, y1 + uy * 17, x2 - ux * 17, y2 - uy * 17, "s")
        for ptr in made:
            x, y = at[final[ptr]]
            h_ = ptr == hot
            f.circle(x, y, 17, "a af" if h_ else "s f")
            f.text(x, y + 5, made[ptr][0], "ta" if h_ else "t", 14, "middle", 700, mono=True)

    stack, made = [], {}
    i = 0
    while i < len(ev):
        e = ev[i]
        if e[0] == "enter":
            stack.append(e[1])
            who = "parse" if len(stack) == 1 else stack[-2]
            k = col_ix[e[2]]
            tokname = toks[k][3]
            if e[1] == "primary" and k > 0 and toks[k - 1][3] in ("+", "-"):
                cap = (f"add sees {toks[k - 1][3]}, steps past it, and calls primary for the operand after it, "
                       f"{tokname}.")
            else:
                cap = f"{who} calls {e[1]}, at the token {tokname}."
            with steps.step(f, cap):
                draw_state(stack, e[2], made, None)
            i += 1
        elif e[0] == "make" and e[3] == "-":
            # a number: made by primary, which then returns it
            made[e[1]] = (e[2], "-", "-")
            lv = ev[i + 1]
            assert lv[0] == "leave" and lv[1] == "primary" and lv[2] == e[1], lv
            stack.pop()
            nxt = toks[col_ix[lv[3]]]
            cap = (f"primary makes a num node, {e[2]}, and returns it; the next token is "
                   f"{nxt[3] if nxt[2] != 'eof' else 'the end of the file'}.")
            with steps.step(f, cap):
                draw_state(stack, lv[3], made, e[1])
            i += 2
        elif e[0] == "make":
            made[e[1]] = (e[2], e[3], e[4])
            lab_l, lab_r = made[e[3]][0], made[e[4]][0]
            left = "the tree so far" if made[e[3]][1] != "-" else lab_l
            cap = (f"add joins {left} and {lab_r} under a {e[2]} node: that node is now add's tree so far, the left "
                   "operand of whatever comes next.")
            with steps.step(f, cap):
                draw_state(stack, None, made, e[1])
            i += 1
        else:
            name, ptr, col = e[1], e[2], e[3]
            stack.pop()
            if name == "add":
                cap = "add sees the end of the file, not + or -: its loop ends, and it returns its tree, the - node."
            else:
                assert name == "expr" and i == len(ev) - 1, e
                cap = (f"expr returns that node to parse, which checks that the end of the file is next: the tree "
                       "--tree prints. It leans left because of the loop in add: each turn put the tree so far "
                       "on the left of a new node, so 5 + 20 - 4 is (5 + 20) - 4.")
            with steps.step(f, cap):
                draw_state(stack, col, made, ptr)
            i += 1
    return f


# ------------------------------------------------------------------ 02.02

def shape():
    a, _ = L.tree("02.02", "1 + 2 * 3\n")
    b, _ = L.tree("02.02", "(1 + 2) * 3\n")
    assert a == ("+", None, [("num", 1, []), ("*", None, [("num", 2, []), ("num", 3, [])])]), a
    assert b == ("*", None, [("+", None, [("num", 1, []), ("num", 2, [])]), ("num", 3, [])]), b
    va, vb = L.tree_eval(a), L.tree_eval(b)
    assert (va, vb) == (7, 9) and L.ccrun("02.03", "1 + 2 * 3\n") == 7 and L.ccrun("02.03", "(1 + 2) * 3\n") == 9
    f = Fig("f0202a", "Precedence is the shape of the tree: the operator that binds tighter sits deeper", 262)
    for k, (src, t, v, x0) in enumerate((("1 + 2 * 3", a, va, 70), ("(1 + 2) * 3", b, vb, 390))):
        f.code(x0 + 90 - L.cw(16) * len(src) / 2, 34, src, 16, "t", weight=700)
        deep = (1,) if k == 0 else (0,)
        at = L.draw_tree(f, t, x0 + 20, 72, 70, 62, r=18, size=15,
                         cls_of=lambda p, op, deep=deep: ("a af", "ta") if p == deep else None)
        f.text(at[()][0], 240, f"= {v}", "t", 18, "middle", 700, mono=True)
        dx_, dy_ = at[deep]
        side = 1 if k == 0 else -1
        f.text(dx_ + side * 26, dy_ - 4, f"{L.label(*t[2][deep[0]][:2])} is deeper:", "ta", 12,
               "start" if side > 0 else "end", 700)
        f.text(dx_ + side * 26, dy_ + 11, "done first", "ta", 12, "start" if side > 0 else "end", 700)
    return f


def dropped():
    src = "(1 + 2) * 3\n"
    ev, want = trace("02.02", src)
    toks, _ = L.tokens("02.02", src)
    tok_at = {t[1]: t[3] for t in toks}
    # the calls as a tree: each call, its children and the tokens it read itself, by position
    root = {"name": "parse", "kids": [], "start": 1}
    stack = [root]
    for e in ev:
        if e[0] == "enter":
            node = {"name": e[1], "kids": [], "start": e[2]}
            stack[-1]["kids"].append(node)
            stack.append(node)
        elif e[0] == "leave":
            stack[-1]["end"] = e[3]
            stack.pop()
    cols = sorted(tok_at)

    def items(call):
        """The call's children and the tokens it read itself, in source order."""
        out = [(k["start"], "call", k) for k in call["kids"]]
        covered = set()
        for k in call["kids"]:
            covered |= {c for c in cols if k["start"] <= c < k["end"]}
        for c in cols:
            if call["start"] <= c < call["end"] and c not in covered and tok_at[c]:
                out.append((c, "tok", tok_at[c]))
        return sorted(out, key=lambda x: (x[0], x[1] == "call"))

    rows = []

    def walk(call, depth):
        rows.append((depth, "call", call["name"]))
        for _, kind, it in items(call):
            if kind == "call":
                walk(it, depth + 1)
            else:
                rows.append((depth + 1, "tok", it))

    walk(root["kids"][0], 0)
    calls = sum(1 for r in rows if r[1] == "call")
    assert calls == 11 and [r[2] for r in rows if r[1] == "tok"] == ["(", "1", "+", "2", ")", "*", "3"], rows
    f = Fig("f0202b", "What the tree keeps and what it drops: (1 + 2) * 3", 34 + len(rows) * 17 + 34)
    f.text(24, 20, f"the path the parser took: {calls} calls", "tm", 11.5)
    x0, y0, ind = 30, 44, 22
    for k, (depth, kind, it) in enumerate(rows):
        y = y0 + k * 17
        x = x0 + depth * ind
        if depth:                       # an elbow from the row's parent: the last row one level up
            pk = max(j for j in range(k) if rows[j][0] == depth - 1)
            f.path(f"M{x - ind + 5} {y0 + pk * 17 + 5} V{y - 4} H{x - 4}", "m")
        if kind == "call":
            f.code(x, y, it, 12, "tm")
        else:
            f.code(x, y, f'"{it}"' if it in "()+-*/" else it, 12, "tm", weight=700)
    # the tree it keeps
    tx = 400
    f.text(tx - 30, 20, "what --tree prints: 5 nodes", "t", 11.5, weight=700)
    L.draw_tree(f, want, tx, 90, 64, 70, r=19, size=15)
    f.text(tx - 30, 330, "no parentheses, and no expr, add,", "t", 12)
    f.text(tx - 30, 346, "mul or primary: the shape keeps", "t", 12)
    f.text(tx - 30, 362, "what they meant", "t", 12)
    f.line(300, 200, 352, 200, "m", arrow=True)
    return f


# ------------------------------------------------------------------ 02.03

def tree_box(f, t, x0, y0, dx, dy, hot=None, regs=None, r=17, size=14):
    """A tree, with the node at path `hot` in the accent and each node's register beside it."""
    pos = L.layout(t, x0, y0, dx, dy)
    at = L.draw_tree(f, t, x0, y0, dx, dy, r=r, size=size, pos=pos,
                     cls_of=lambda p, op: ("a af", "ta") if p == hot else None)
    if regs:
        for p, (x, y) in at.items():
            f.text(x + r + 4, y - r + 6, regs[p], "ta" if p == hot else "tm", 12, mono=True, weight=700 if p == hot else None)
    return at


def registers():
    src = "1 + 2 * 3\n"
    t, g, lines = checked_gen("02.03", src)
    ins = [s for s, _ in g][:-1]
    assert ins == ["li t0, 1", "li t1, 2", "li t2, 3", "mul t1, t1, t2", "add t0, t0, t1"], ins
    sim = L.simulate(ins)
    assert sim[-1][1]["t0"] == 7
    f = Fig("f0203a", "The code for 1 + 2 * 3, one instruction a step: the registers are a stack", 270)
    f.text(24, 20, "the tree", "tm", 11.5)
    f.text(250, 20, "./cc at 02.03, the expression's lines", "tm", 11.5)
    f.text(476, 20, "the registers", "tm", 11.5)
    tree_box(f, t, 40, 66, 64, 62)
    cx0, cy0, rh = 252, 46, 26
    f.rect(cx0 - 8, cy0 - 8, 188, rh * len(ins) + 50, "s fs", 6)
    for k, s in enumerate(ins):
        f.code(cx0 + 6, cy0 + 12 + k * rh, s, 13.5, "t")
    f.code(cx0 + 6, cy0 + 12 + len(ins) * rh + 4, "mv a0, t0", 12, "tm")
    rx, ry, rw, rh2 = 480, 46, 136, 34
    order = ["t2", "t1", "t0"]
    for i, reg in enumerate(order):
        f.rect(rx, ry + i * (rh2 + 6), rw, rh2, "s f", 4)
        f.code(rx - 6 - L.cw(13) * 2, ry + i * (rh2 + 6) + 22, reg, 13, "tm")
    f.text(rx + rw / 2, ry + 3 * (rh2 + 6) + 14, "t0 is the bottom", "tm", 11, "middle")
    live = set()
    for k, ((s, path), (_, regs, _)) in enumerate(zip(g, sim)):
        op = s.split()[0]
        d = REG.index(s.split()[1].rstrip(","))
        if op == "li":
            live.add(d)
            cap = (f"{s}: the number {s.split()[-1]} goes into {REG[d]}, the register at its depth, {d}. "
                   + ("It waits there while the right side is computed." if path and path[-1] == 0 else ""))
        else:
            live.discard(d + 1)
            cap = (f"{s}: the {'*' if op == 'mul' else '+'} node takes its two operands, {REG[d]} and {REG[d + 1]}, "
                   f"and leaves one value, {regs[REG[d]]}, in {REG[d]}. {REG[d + 1]} is free again.")
        if k == len(ins) - 1:
            cap += " t0 holds 7, the whole expression; mv a0, t0 then hands it to main's caller."
        with steps.step(f, cap.strip()):
            tree_box(f, t, 40, 66, 64, 62, hot=path)
            f.rect(cx0 - 2, cy0 - 5 + k * rh, 176, rh - 2, "a af", 4)
            f.code(cx0 + 6, cy0 + 12 + k * rh, s, 13.5, "ta", weight=700)
            for i, reg in enumerate(order):
                ri = REG.index(reg)
                if reg in regs and ri in live:
                    hot = ri == d
                    f.rect(rx + 1, ry + i * (rh2 + 6) + 1, rw - 2, rh2 - 2, "af" if hot else "fs", 3, sw=False)
                    f.text(rx + rw / 2, ry + i * (rh2 + 6) + 23, str(regs[reg]), "ta" if hot else "t", 16, "middle",
                           700, mono=True)
                elif reg in regs:
                    f.text(rx + rw / 2, ry + i * (rh2 + 6) + 22, f"{regs[reg]}, free", "tm", 12, "middle", mono=True)
    return f


def depth():
    src = "1 + 2 * 3\n"
    t, g, _ = checked_gen("02.03", src)
    regs = node_regs(t, g)
    assert regs == {(): "t0", (0,): "t0", (1,): "t1", (1, 0): "t1", (1, 1): "t2"}, regs
    f = Fig("f0203b", "A node's value goes in the register at its depth: left at the same depth, right one higher",
            252)
    # the schematic node
    nx, ny = 150, 64
    f.text(24, 20, "the rule, for any binary operator", "tm", 11.5)
    f.circle(nx, ny, 22, "a af")
    f.text(nx, ny + 5, "op", "ta", 14, "middle", 700, mono=True)
    for (cx, cy, lab, cls) in ((nx - 76, ny + 96, "d", "t"), (nx + 76, ny + 96, "d + 1", "ta")):
        f.line(nx + (cx - nx) * 0.26, ny + 20, cx - (cx - nx) * 0.2, cy - 22, "s")
        f.circle(cx, cy, 22, "s f")
        f.text(cx, cy + 5, "left" if cx < nx else "right", "t", 12, "middle", 600)
        f.code(cx - L.cw(13) * len(f"reg[{lab}]") / 2, cy + 44, f"reg[{lab}]", 13, cls, weight=700)
    f.code(nx + 30, ny - 4, "reg[d]", 13, "ta", weight=700)
    f.text(24, 238, "Below reg[d] are values still waiting: gen_expr never writes there.", "tm", 11.5)
    # the tree of 1 + 2 * 3 with its registers
    f.text(380, 20, "1 + 2 * 3, from ./cc at 02.03", "tm", 11.5)
    tree_box(f, t, 400, 60, 74, 66, regs=regs, r=18, size=15)
    return f


# ------------------------------------------------------------------ 02.04

def levels(at):
    """The parser's levels at lesson `at`, from its rule comments: [(name, operators)] from the
    loosest binary level down, then unary and primary when they exist."""
    rules = dict(m.groups() for m in re.finditer(r"^  // (\w+) = (.*)$", L.source(at, "parse.c"), re.M))
    chain, name = [], rules["expr"].split()[0]
    while True:
        rule = rules[name]
        ops = re.findall(r'"([^"]+)"', rule)
        chain.append((name, [o for o in ops if o not in "()"] if name != "primary" else []))
        nxt = "primary" if name == "unary" else rule.split()[0]     # unary = (...) unary | primary
        if name == "primary" or nxt not in rules:
            break
        name = nxt
    return chain


LESSON_IDS = ["02.01", "02.02", "02.03", "02.04", "02.05"]


def first_lesson():
    """{level: lesson}, {(level, operator): lesson}: the first lesson whose parse.c has each."""
    lv, op = {}, {}
    for lid in LESSON_IDS:
        for name, ops in levels(lid):
            lv.setdefault(name, lid)
            for o in ops:
                op.setdefault((name, o), lid)
    return lv, op


def ladder():
    full = levels("02.05")
    names_ = [n for n, _ in full]
    assert names_ == ["bitor", "bitxor", "bitand", "equality", "relational", "shift", "add", "mul", "unary",
                      "primary"], names_
    at = [n for n, _ in levels("02.04")]
    assert at == ["bitor", "bitxor", "bitand", "shift", "add", "mul", "primary"], at
    lv, opl = first_lesson()
    assert lv["mul"] == "02.02" and opl[("mul", "%")] == "02.04" and lv["add"] == "02.01", (lv, opl)
    f = Fig("f0204a", "C's binary operators from loosest to tightest, the function for each, and its lesson", 356)
    x0, y0, rh = 60, 46, 28
    f.text(x0 + 8, 22, "operators", "tm", 11.5)
    f.text(x0 + 200, 22, "the function", "tm", 11.5)
    f.text(x0 + 330, 22, "the lesson that brings it", "tm", 11.5)
    for k, (name, ops) in enumerate(full):
        y = y0 + k * rh
        lid = lv[name]
        tail = name in ("unary", "primary")
        if lid == "02.04":
            cls, tcls, dash = "a af", "ta", False
        elif lid == "02.05" and not tail:
            cls, tcls, dash = "m f", "tm", True
        elif tail:
            cls, tcls, dash = "m f", "tm", name == "unary"
        else:
            cls, tcls, dash = "s f", "t", False
        f.rect(x0, y, 520, rh - 5, cls, 5, dash=dash)
        if name == "mul":
            # % arrived later than * and /
            x = x0 + 12
            for o in ops:
                hot = opl[(name, o)] == "02.04"
                f.code(x, y + 16, o, 13.5, "ta" if hot else tcls, weight=700)
                x += (len(o) + 2) * L.cw(13.5)
            lesson = f"{lid}; % {opl[(name, '%')]}"
        elif name == "primary":
            f.text(x0 + 12, y + 16, "a number, or ( expr )", tcls, 12)
            lesson = lid
        else:
            f.code(x0 + 12, y + 16, "  ".join(ops), 13.5, tcls, weight=700)
            if name == "unary":
                f.text(x0 + 12 + (len("  ".join(ops)) + 2) * L.cw(13.5), y + 16, "one operand", tcls, 12)
            lesson = lid
        f.code(x0 + 200, y + 16, name, 13, tcls, weight=700 if tcls == "ta" else None)
        f.text(x0 + 330, y + 16, lesson, "ta" if "02.04" in lesson else tcls, 12.5, weight=700 if "02.04" in lesson else None)
    # loosest to tightest
    ax = 32
    f.line(ax, y0 + 4, ax, y0 + 8 * rh - 10, "m", arrow=True)
    f.text(ax, y0 - 4, "looser", "tm", 11, "middle")
    f.text(ax, y0 + 8 * rh + 6, "tighter", "tm", 11, "middle")
    yb = y0 + len(full) * rh + 16
    f.text(x0, yb, "Each function calls the next one down for its operands: a level lower binds tighter.", "tm", 11.5)
    return f


def ladder_tree():
    src = "6 % 4 << 2 | 1\n"
    t, out = L.tree("02.04", src)
    assert out.splitlines() == ["|", "  <<", "    %", "      num 6", "      num 4", "    num 2", "  num 1"], out
    assert L.ccrun("02.04", src) == 9
    of = {}
    for name, ops in levels("02.04"):
        for o in ops:
            of[o] = name
    f = Fig("f0204b", "6 % 4 << 2 | 1: three levels of the ladder in one tree", 330)
    f.code(320 - L.cw(16) * len(src.strip()) / 2, 30, src.strip(), 16, "t", weight=700)
    at = L.draw_tree(f, t, 150, 74, 92, 64, r=19, size=15)
    for p, (x, y) in at.items():
        op = L.label(*next((n[1] for n in L.layout(t, 150, 74, 92, 64)[0] if n[0] == p)))
        if op in of:
            f.text(x + 28, y + 5, of[op], "ta", 13, mono=True, weight=700)
    f.text(24, 316, "Looser levels sit higher in the tree: | is the last operator done, and ./ccrun gives 9.", "tm",
           11.5)
    return f


# ------------------------------------------------------------------ 02.05

def two_from_four():
    srcs = ["1 < 2", "1 <= 2", "1 > 2", "1 >= 2"]
    trees = [L.tree("02.05", s + "\n")[0] for s in srcs]
    n = lambda v: ("num", v, [])  # noqa: E731
    assert trees == [("<", None, [n(1), n(2)]), ("<=", None, [n(1), n(2)]), ("<", None, [n(2), n(1)]),
                     ("<=", None, [n(2), n(1)])], trees
    f = Fig("f0205a", "Four comparisons, two kinds of node: > and >= are < and <= with the sides swapped", 250)
    f.text(24, 20, "as written, and the tree ./cc --tree prints at 02.05", "tm", 11.5)
    for k, (s, t) in enumerate(zip(srcs, trees)):
        cx = 88 + k * 154
        swapped = ">" in s
        f.code(cx - L.cw(15) * len(s) / 2, 56, s, 15, "ta" if swapped else "t", weight=700)
        f.line(cx, 66, cx, 86, "m", arrow=True)
        L.draw_tree(f, t, cx - 36, 112, 72, 66, r=18, size=14,
                    cls_of=lambda p, op, sw=swapped: ("a af", "ta") if sw and p == () else None)
        if swapped:
            f.text(cx, 222, "the sides swapped", "ta", 12, "middle", 700)
        else:
            f.text(cx, 222, "as written", "tm", 12, "middle")
    return f


def instructions():
    rows = [("1 == 2", "=="), ("1 != 2", "!="), ("1 < 2", "<"), ("1 <= 2", "<="), ("-1", "-"), ("!1", "!"),
            ("~1", "~")]
    f = Fig("f0205b", "What each comparison and unary operator becomes", 0)
    f.text(24, 20, "written", "tm", 11.5)
    f.text(120, 20, "./cc at 02.05: after the operands are loaded", "tm", 11.5)
    f.text(520, 20, "t0 after", "tm", 11.5)
    y = 36
    want = {"==": ["xor t0, t0, t1", "seqz t0, t0"], "!=": ["xor t0, t0, t1", "snez t0, t0"],
            "<": ["slt t0, t0, t1"], "<=": ["slt t0, t1, t0", "xori t0, t0, 1"], "-": ["neg t0, t0"],
            "!": ["seqz t0, t0"], "~": ["not t0, t0"]}
    notes = {"==": "equal when nothing is left after xor", "!=": "not equal: something is left",
             "<": "the one comparison RISC-V has", "<=": "a <= b is not (b < a)", "-": "0 minus it",
             "!": "1 if it is 0, else 0", "~": "every bit flipped"}
    for k, (s, op) in enumerate(rows):
        t, g, lines = checked_gen("02.05", s + "\n")
        assert t[0] == op, (s, t)
        ins = L.instructions(lines)
        body = [x for x in ins if x.split()[0] not in ("li", "mv", "ret")]
        assert body == want[op], (s, body)
        t0 = L.simulate(ins)[-1][1]["t0"]
        assert t0 == L.tree_eval(t), (s, t0)
        h = 12 + 20 * len(body)
        if k % 2 == 0:
            f.rect(16, y - 2, 608, h + 8, "fs", 5, sw=False)
        f.code(24, y + 17, s, 15, "t", weight=700)
        for i, b in enumerate(body):
            f.code(120, y + 17 + i * 20, b, 13.5, "ta", weight=700)
        f.text(290, y + 17, notes[op], "tm", 11.5)
        f.text(560, y + 17, str(t0), "t", 15, "end", 700, mono=True)
        y += h + 10
    f.text(24, y + 14, "The operands: li t0, 1 and li t1, 2 for the binary ones, li t0, 1 for the unary ones.", "tm",
           11.5)
    f.h = y + 26
    return f


# ------------------------------------------------------------------ 02.06

def spill():
    src = L.source("02.06", "try.c")
    assert src == "9 - (8 - (7 - (6 - (5 - (4 - (3 - 2))))))\n", src
    t, g, lines = checked_gen("02.06", src)
    ins = [s for s, _ in g]
    assert len(ins) == 24 and ins.count("addi sp, sp, -16") == 2 and ins[-1] == "mv a0, t0", ins
    assert L.ccrun("02.06", src) == 4
    sp0 = 0x80010040
    sim = L.simulate(ins, sp=sp0)
    assert sim[-1][1]["t0"] == 4 and sim[-1][1]["sp"] == sp0, sim[-1]
    f = Fig("f0206a", "9 - (8 - (7 - (6 - (5 - (4 - (3 - 2)))))): six registers fill, then the stack takes the rest",
            412)
    f.text(24, 20, "./cc try.c at 02.06", "tm", 11.5)
    lx, ly, rh = 24, 40, 14.4
    f.rect(lx - 6, ly - 6, 174, rh * len(ins) + 10, "s fs", 6)
    for k, s in enumerate(ins):
        f.code(lx + 6, ly + 10 + k * rh, s, 11.5, "t")
    # registers t0..t5 as a stack (t0 at the bottom), t6 apart
    rx, rw, rh2 = 214, 100, 30
    order = list(reversed(REG))
    f.text(rx, 20, "the registers", "tm", 11.5)
    for i, reg in enumerate(order):
        y = 40 + i * (rh2 + 5)
        f.rect(rx + 28, y, rw, rh2, "s f", 4)
        f.code(rx, y + 20, reg, 13, "tm")
    ty6 = 40 + 6 * (rh2 + 5) + 22
    f.rect(rx + 28, ty6, rw, rh2, "s f", 4, dash=True)
    f.code(rx, ty6 + 20, "t6", 13, "tm")
    f.text(rx + 28, ty6 + rh2 + 16, "the spare, never on the stack", "tm", 10.5)
    # memory under where sp started, higher addresses up: a 16-byte slot a spill, the value in its low
    # 8 bytes, at 0(sp)
    mx, mw, my0, slot_h = 400, 140, 50, 64

    def ymem(a):
        return my0 + (sp0 - a) / 16 * slot_h

    f.text(mx - 26, 20, "memory, under where sp started", "tm", 11.5)
    slots = [sp0 - 16, sp0 - 32]          # each slot's lowest address, where sd puts the value
    for a in slots:
        y = ymem(a + 16)
        f.rect(mx, y, mw, slot_h, "s f", 0)
        f.path(f"M{mx} {y + slot_h / 2} H{mx + mw}", "m", dash=True)
        f.text(mx + mw - 6, y + 20, "8 bytes, unused", "tm", 10.5, "end")
    for a in [sp0] + slots:
        f.code(mx + mw + 6, ymem(a) + 4, f"{a:#x}", 11, "tm")
    ny = ymem(slots[-1]) + 24
    for i, ln in enumerate(("Each spill moves sp down 16, not 8:", "the calling convention keeps sp a",
                            "multiple of 16.")):
        f.text(mx - 26, ny + i * 14, ln, "tm", 11)

    # the steps: the six li together, then one instruction a step
    groups = [list(range(0, 6))] + [[k] for k in range(6, len(ins))]
    live, mem = set(), []
    prev_regs = {}
    for grp in groups:
        for k in grp:
            s = ins[k]
            op = s.split()[0]
            if op == "li":
                live.add(s.split()[1].rstrip(","))
            elif op == "sd":
                live.discard(s.split()[1].rstrip(","))
                mem.append(k)
            elif op == "ld":
                live.add("t6")
                mem.pop()
            elif op in ("sub",):
                a = [x.strip() for x in s[4:].split(",")]
                live.discard(a[2] if a[1] != "t6" else "t6")
                if a[1] == "t6":
                    live.discard("t6")
                live.add(a[0])
        _, regs, memv = sim[grp[-1]]
        last = ins[grp[-1]]
        op = last.split()[0]
        if len(grp) > 1:
            cap = ("Six li: 9, 8, 7, 6, 5 and 4 fill t0 to t5, each the left operand of a subtraction still waiting "
                   "for its right side. There is no register left for 3.")
        elif op == "addi" and "-16" in last:
            cap = (f"addi sp, sp, -16: room on the stack. sp moves down to {regs['sp']:#x}." +
                   (" The left operand in t5 has to go there, so t5 can take the right side." if len(mem) == 0 else
                    " Inside the right side, the same again: t5 is the last register."))
        elif op == "sd":
            cap = (f"sd t5, 0(sp): {memv[regs['sp']]} is stored in memory at sp. t5 is free for the right operand.")
        elif op == "li":
            cap = (f"{last}: the right operand goes into t5, the same register, at the same depth."
                   + (" It is the deepest leaf: the stack has two values." if "2" in last.split()[-1] else ""))
        elif op == "ld":
            cap = f"ld t6, 0(sp): the waiting value, {regs['t6']}, comes back from memory into t6, the spare."
        elif op == "addi":
            cap = f"addi sp, sp, 16: the room is given back; sp is {regs['sp']:#x} again" + \
                  (", where it started." if regs["sp"] == sp0 else ".")
        elif op == "sub" and "t6" in last:
            cap = f"{last}: t6 (the left operand) minus t5 (the right) is {regs['t5']}, into t5. t6 is free."
        elif op == "sub":
            a = [x.strip() for x in last[4:].split(",")]
            cap = f"{last}: {regs[a[0]]} into {a[0]}; {a[2]} is free. The stack of registers unwinds."
        else:
            cap = f"{last}: a0 = {regs['a0']}, the status: 9 - (8 - (7 - (6 - (5 - (4 - (3 - 2)))))) is 4."
        with steps.step(f, cap):
            for k in grp:
                f.rect(lx, ly - 1 + k * rh, 162, rh - 0.5, "a af", 2, sw=False)
                f.code(lx + 6, ly + 10 + k * rh, ins[k], 11.5, "ta", weight=700)
            changed = {r for r in REG + ["t6", "a0"] if regs.get(r) != prev_regs.get(r)}
            for i, reg in enumerate(order + ["t6"]):
                y = 40 + i * (rh2 + 5) if reg != "t6" else ty6
                if reg in regs and (reg in live or reg in changed):
                    hot = reg in changed
                    f.rect(rx + 29, y + 1, rw - 2, rh2 - 2, "af" if hot else "fs", 3, sw=False)
                    f.text(rx + 28 + rw / 2, y + 21, str(regs[reg]), "ta" if hot else "t", 15, "middle", 700,
                           mono=True)
                elif reg in regs:
                    f.text(rx + 28 + rw / 2, y + 20, f"{regs[reg]}, free", "tm", 11.5, "middle", mono=True)
            for j, a in enumerate(slots):
                y = ymem(a) - slot_h / 2          # the low half: a to a + 8
                if a in memv and j < len(mem):
                    hot = op == "sd" and a == regs["sp"]
                    f.rect(mx + 1, y + 1, mw - 2, slot_h / 2 - 2, "af" if hot else "fs", 0, sw=False)
                    f.text(mx + 14, y + 22, str(memv[a]), "ta" if hot else "t", 15, weight=700, mono=True)
                elif a in memv:
                    f.text(mx + 14, y + 21, f"{memv[a]}, given back", "tm", 11.5, mono=True)
            spy = ymem(regs["sp"])
            f.line(mx - 28, spy, mx - 3, spy, "a", arrow=True)
            f.code(mx - 50, spy + 4, "sp", 13, "ta", weight=700)
            if op == "mv":
                f.rect(rx + 28, ty6 + rh2 + 26, rw, 26, "a af", 4)
                f.code(rx + 38, ty6 + rh2 + 44, f"a0 = {regs['a0']}", 13, "ta", weight=700)
        prev_regs = regs
    return f


LEFT = "((((((9 - 8) - 7) - 6) - 5) - 4) - 3) - 2\n"


def subtree(t, path):
    for i in path:
        t = t[2][i]
    return t


def leaning():
    right_src = L.source("02.06", "try.c")
    tr, gr, lr = checked_gen("02.06", right_src)
    tl, gl, ll = checked_gen("02.06", LEFT)
    used = lambda g: sorted({r for s, _ in g for r in re.findall(r"\bt\d\b", s)})  # noqa: E731
    spills = lambda g: sum(1 for s, _ in g if s.startswith("sd "))  # noqa: E731
    assert used(gr) == ["t0", "t1", "t2", "t3", "t4", "t5", "t6"] and spills(gr) == 2, (used(gr), spills(gr))
    assert used(gl) == ["t0", "t1"] and spills(gl) == 0, used(gl)
    f = Fig("f0206b", "The same seven subtractions two ways: leaning right, every register and two spills; leaning "
                      "left, two registers", 412)
    for k, (src, t, g) in enumerate(((right_src, tr, gr), (LEFT, tl, gl))):
        x0 = 30 if k == 0 else 340
        f.code(x0 + (k * 0), 22, src.strip(), 10.5, "t", weight=700)
        regs = node_regs(t, g)
        spilled = {p + (0,) for s, p in g if s.startswith("sd ")}     # the left operand of a spilling node
        pos = L.layout(t, x0 + 16, 58, 35, 34)
        at = L.draw_tree(f, t, 0, 0, 0, 0, r=13, size=12, pos=pos,
                         cls_of=lambda p, op, sp=spilled: ("a af", "ta") if p in sp else None)
        for p, (x, y) in at.items():
            # the register on the side away from the edge up to the parent
            side = 1 if not p else (-1 if at[p[:-1]][0] > x else 1)
            dy = -6 if subtree(t, p)[2] else 5
            f.text(x + side * 16, y + dy, regs[p], "ta" if p in spilled else "tm", 11, "start" if side > 0 else "end",
                   weight=700 if p in spilled else None, mono=True)
        top = max(used(g), key=lambda r: int(r[1:]) if r != "t6" else -1)
        yb = 58 + 7 * 34 + 44
        if k == 0:
            f.text(x0, yb, f"reaches {top}, the last register: {spills(g)} spills", "t", 12.5, weight=700)
            f.text(x0, yb + 17, "the shaded ones go to memory and come back", "ta", 11.5)
            f.text(x0, yb + 32, "through t6", "ta", 11.5)
        else:
            f.text(x0, yb, f"reaches {top}: no spill, at any length", "t", 12.5, weight=700)
            f.text(x0, yb + 17, "each result waits in t0 while the next", "tm", 11.5)
            f.text(x0, yb + 32, "number goes into t1", "tm", 11.5)
    f.text(30, 400, "By each node: the register its value is computed into, from ./cc at 02.06.", "tm", 11.5)
    return f


FIGS = [
    ("02.01-grammar", grammar, False),
    ("02.01-descent", descent, True),
    ("02.02-shape", shape, False),
    ("02.02-dropped", dropped, False),
    ("02.03-registers", registers, True),
    ("02.03-depth", depth, False),
    ("02.04-ladder", ladder, False),
    ("02.04-tree", ladder_tree, False),
    ("02.05-two-from-four", two_from_four, False),
    ("02.05-instructions", instructions, False),
    ("02.06-spill", spill, True),
    ("02.06-leaning", leaning, False),
]


def main(argv):
    for name, fn, stepped in FIGS:
        if argv and not any(name.startswith(a) for a in argv):
            continue
        write(name, fn(), stepped)


if __name__ == "__main__":
    main(sys.argv[1:])
