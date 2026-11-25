"""01.07 The parser: tokens into a tree

./mote --parse-tree FILE prints the parse tree a node a line, two spaces deeper for each level:
a node for each use of a rule (program, stmt, cond, expr, term, factor) and under it, in order,
a node for every token it took (KIND TEXT) and every rule it called. Its leaves, read in order,
are the tokens. gcd.mote's tree has 64 nodes for its 11 lines. A syntax error is FILE:LINE:COL:
message at the token where it was found, status 1, before anything runs; so mote finds the
mistakes mote0 never reads.
"""

import os


def leaves(lines):
    return [l.strip() for l in lines if l.strip().split(" ")[0] in ("name", "number", "keyword", "op")]


def test(t):
    tr = t.track
    st, out, err = tr.mote(t, "read n while n > 0 do write n n := n - 1 end\n", "--parse-tree")
    t.check((st, out.split("\n")[:-1]) == (0, tr.FLOW_PARSE), f"--parse-tree of the loop:\n{out}{err}")

    gcd = os.path.join(t.root, "programs", "gcd.mote")
    st, out, err = tr.prog(t, "mote", ["--parse-tree", gcd])
    lines = out.split("\n")[:-1]
    t.check(st == 0 and len(lines) == 64, f"gcd.mote's parse tree has 64 nodes, not {len(lines)}")
    st, toks, err = tr.prog(t, "mote", ["--tokens", gcd])
    t.check(leaves(lines) == [l.split(" ", 1)[1] for l in toks.split("\n")[:-2]],
            "the parse tree's leaves, in order, are the tokens")
    for l in lines:
        ind = len(l) - len(l.lstrip(" "))
        t.check(ind % 2 == 0 and l.strip(), f"a node is indented two spaces a level: {l!r}")

    # Precedence and grouping come from the rules: * is deeper than +, parentheses go deeper still.
    st, out, err = tr.mote(t, "write 1 + 2 * -(3)\n", "--parse-tree")
    want = ["program", "  stmt", "    keyword write", "    expr", "      term", "        factor",
            "          number 1", "      op +", "      term", "        factor", "          number 2",
            "        op *", "        factor", "          op -", "          factor", "            op (",
            "            expr", "              term", "                factor", "                  number 3",
            "            op )"]
    t.check(out.split("\n")[:-1] == want, f"1 + 2 * -(3):\n{out}")
    st, out, err = tr.mote(t, "if 1 < 2 then else end\n", "--parse-tree")
    t.check(out.split("\n")[:-1] == ["program", "  stmt", "    keyword if", "    cond", "      expr", "        term",
                                     "          factor", "            number 1", "      op <", "      expr",
                                     "        term", "          factor", "            number 2", "    keyword then",
                                     "    keyword else", "    keyword end"], f"empty blocks:\n{out}")

    for src, line, col, msg in (("while x < 1\n    x := 1\nend\n", 2, 5, "expected 'do'"),
                                ("if x then end\n", 1, 6, "expected a comparison"),
                                ("if 1 < 2 write 1 end\n", 1, 10, "expected 'then'"),
                                ("while 1 < 2 do\n  write 1\n", 2, 10, "expected 'end'"),
                                ("x 1\n", 1, 3, "expected ':='"),
                                ("read 5\n", 1, 6, "expected a name"),
                                ("x := 1 +\nwrite x\n", 2, 1, "expected a number, a name or '('"),
                                ("x := (1 + 2\n", 1, 12, "expected ')'"),
                                ("write 1\nend\n", 2, 1, "expected a statement"),
                                ("then := 1\n", 1, 1, "expected a statement"),
                                ("write do\n", 1, 7, "expected a number, a name or '('"),
                                ("while 1 < 2 do else end\n", 1, 16, "expected 'end'")):
        st, out, err = tr.mote(t, src, "--parse-tree")
        t.check(st == 1 and out == "" and err == f"t{t._lang_files}.mote:{line}:{col}: {msg}\n",
                f"{src!r}: {st} {err!r}, not {line}:{col}: {msg}")

    # mote0 runs a line only when it reaches it; mote parses the whole program first.
    src = "write 1\nif 1 > 2 then\n    x := 1 +\nend\n"
    t.check(tr.mote0(t, src)[:2] == (0, "1\n"), "mote0 never reads the mistake")
    st, out, err = tr.mote(t, src, "--parse-tree")
    t.check((st, err) == (1, f"t{t._lang_files}.mote:4:1: expected a number, a name or '('\n"),
            f"mote finds it before anything runs: {st} {err!r}")
