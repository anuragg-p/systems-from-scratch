"""01.02 Longest match

Every punctuator of C (but "..." and "##", which come with their lessons)
is one token, and where several could start at a character the longest
wins: ">>=" is one token, not ">>" and "=", and "a- >b" is not "a->b". A
character no punctuator starts is still an invalid token.
"""

PUNCTS = ["<<=", ">>=", "==", "!=", "<=", ">=", "->", "+=", "-=", "*=", "/=", "++", "--", "%=", "&=",
          "|=", "^=", "&&", "||", "<<", ">>",
          "+", "-", "*", "/", "%", "&", "|", "^", "~", "!", "=", "<", ">", "(", ")", "[", "]", "{", "}",
          ".", ",", ";", ":", "?", "#"]


def kinds(toks):
    return [f"{x.kind} {x.text}" for x in toks]


def test(t):
    tr = t.track
    for src, want in (("a>=b", ["ident a", "punct >=", "ident b"]),
                      ("a>>=b", ["ident a", "punct >>=", "ident b"]),
                      ("a- >b", ["ident a", "punct -", "punct >", "ident b"]),
                      ("a->b", ["ident a", "punct ->", "ident b"]),
                      ("1+++2", ["num 1", "punct ++", "punct +", "num 2"]),
                      ("x<<=<<<", ["ident x", "punct <<=", "punct <<", "punct <"]),
                      ("!==", ["punct !=", "punct ="]),
                      ("&&&", ["punct &&", "punct &"]),
                      ("a...b", ["ident a", "punct .", "punct .", "punct .", "ident b"])):
        got = kinds(tr.tokens(t, src))[:-1]
        t.check(got == want, f"{src!r}: {got}, not {want}")
    # Every punctuator alone is one token, with its column.
    toks = tr.tokens(t, " ".join(PUNCTS))
    got = [(x.kind, x.text) for x in toks[:-1]]
    t.check(got == [("punct", p) for p in PUNCTS], f"every punctuator, one token each:\n{got}")
    col = 1
    for p, x in zip(PUNCTS, toks):
        t.check(x.col == col, f"{p!r} at column {x.col}, not {col}")
        col += len(p) + 1
    for src in ("1 @ 2", "1 $", "`", "\\"):
        e = tr.error(t, src)
        t.check(e.msg == "invalid token", f"{src!r}: {e!r}")
    # The walker of module 01 knew + and - alone; now the parser takes them, and "+=" is not "+".
    e = tr.error(t, "1 += 2")
    t.check((e.msg, e.col) == ("extra token", 3), f"'1 += 2': {e!r}")
