"""01.03 Identifiers and keywords

An identifier is a letter or '_' followed by letters, digits and '_'. The
scanner reads every one as an identifier, then marks those that are keywords
of the language, the whole list the finished compiler knows. float and
double are not keywords of this compiler (it has no floating point). An
identifier in an expression is an error from the parser, until variables.
"""

KEYWORDS = ["return", "if", "else", "for", "while", "int", "sizeof", "char", "struct", "union", "short",
            "long", "void", "typedef", "_Bool", "enum", "static", "goto", "break", "continue", "switch",
            "case", "default", "extern", "do", "signed", "unsigned", "const", "volatile", "auto",
            "register", "restrict", "__restrict", "__restrict__", "_Noreturn", "inline", "__attribute__"]
NOT_KEYWORDS = ["x", "x1", "_y", "_", "__", "Int", "integer", "returnx", "_Bool2", "float", "double",
                "_Alignof", "typeof", "asm", "_Generic", "main", "a_b_c9"]


def test(t):
    tr = t.track
    got = [repr(x) for x in tr.tokens(t, "return x1 _y")]
    t.check(got == ["1:1 keyword return", "1:8 ident x1", "1:11 ident _y", "1:13 eof"], f"{got}")
    toks = tr.tokens(t, " ".join(KEYWORDS))[:-1]
    bad = [x.text for x in toks if x.kind != "keyword"]
    t.check(not bad and [x.text for x in toks] == KEYWORDS, f"not keywords: {bad}")
    toks = tr.tokens(t, " ".join(NOT_KEYWORDS))[:-1]
    bad = [(x.kind, x.text) for x in toks if x.kind != "ident"]
    t.check(not bad and [x.text for x in toks] == NOT_KEYWORDS, f"should be identifiers: {bad}")
    # Next to other tokens, and across lines.
    got = [repr(x) for x in tr.tokens(t, "a+b1\n_c-return")]
    t.check(got == ["1:1 ident a", "1:2 punct +", "1:3 ident b1", "2:1 ident _c", "2:3 punct -",
                    "2:4 keyword return", "2:10 eof"], f"{got}")
    # A digit cannot start one: 1x is a bad number.
    e = tr.error(t, "1x")
    t.check(e.msg == "invalid numeric constant", f"'1x': {e!r}")
    e = tr.error(t, "x + 1")
    t.check((e.msg, e.col) == ("expected an expression", 1), f"'x + 1': {e!r}")
