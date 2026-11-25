"""01.06 The phases of a compiler, and the first: a scanner

./mote --tokens FILE prints the tokens a line each, LINE:COL KIND TEXT, KIND being name,
number, keyword or op, and the end of the file last ("eof", on the last line after its last
character). Spaces, tabs, line ends and comments only keep tokens apart, so a statement may run
over lines and a line may hold several. The longest operator wins; a word is taken whole before
it is looked for among the keywords. Errors are FILE:LINE:COL: message, status 1 ("unexpected
character", "number too large"); a wrong command line is the usage, status 2.
"""


def toks(tr, t, src):
    st, out, err = tr.mote(t, src, "--tokens")
    if st != 0:
        raise tr.Fail(f"--tokens failed on {src!r}: {st} {err}")
    return out.split("\n")[:-1]


def test(t):
    tr = t.track
    import os
    st, out, err = tr.prog(t, "mote", ["--tokens", os.path.join(t.root, "programs", "gcd.mote")])
    t.check((st, out.split("\n")[:-1]) == (0, tr.GCD_TOKENS), f"--tokens programs/gcd.mote:\n{out}{err}")

    got = toks(tr, t, "x:=y<=z<w>=1>2==3!=4+5-6*7/(8)")
    want = ["1:1 name x", "1:2 op :=", "1:4 name y", "1:5 op <=", "1:7 name z", "1:8 op <", "1:9 name w",
            "1:10 op >=", "1:12 number 1", "1:13 op >", "1:14 number 2", "1:15 op ==", "1:17 number 3",
            "1:18 op !=", "1:20 number 4", "1:21 op +", "1:22 number 5", "1:23 op -", "1:24 number 6",
            "1:25 op *", "1:26 number 7", "1:27 op /", "1:28 op (", "1:29 number 8", "1:30 op )", "1:31 eof"]
    t.check(got == want, f"every operator, by longest match, with no spaces:\n{got}")
    got = toks(tr, t, "read write if then else end while do done _x x_1 Do")
    want = ["1:1 keyword read", "1:6 keyword write", "1:12 keyword if", "1:15 keyword then", "1:20 keyword else",
            "1:25 keyword end", "1:29 keyword while", "1:35 keyword do", "1:38 name done", "1:43 name _x",
            "1:46 name x_1", "1:50 name Do", "1:52 eof"]
    t.check(got == want, f"keywords and names:\n{got}")
    got = toks(tr, t, "\tx # a comment: while @\n\n  := # more\n12 9223372036854775807")
    want = ["1:2 name x", "3:3 op :=", "4:1 number 12", "4:4 number 9223372036854775807", "4:23 eof"]
    t.check(got == want, f"tabs are a column, comments and blank lines are nothing:\n{got}")
    for src, eof in (("", "1:1 eof"), ("x", "1:2 eof"), ("x\n", "1:2 eof"), ("x\n\n", "2:1 eof"),
                     ("x\r\n", "1:3 eof"), ("# only a comment\n", "1:17 eof")):
        got = toks(tr, t, src)
        t.check(got[-1] == eof, f"the end of {src!r} is {got[-1]}, not {eof}")
    got = toks(tr, t, "read n while n > 0 do write n n := n - 1 end")
    t.check(len(got) == 16 and got[-1] == "1:45 eof", f"several statements on one line are tokens like any: {got}")

    for src, line, col, msg in (("x := 1 @ 2\n", 1, 8, "unexpected character '@'"),
                                ("x\n  = 1\n", 2, 3, "unexpected character '='"),
                                ("x : 1\n", 1, 3, "unexpected character ':'"),
                                ("x := !1\n", 1, 6, "unexpected character '!'"),
                                ("write 9223372036854775808\n", 1, 7, "number too large"),
                                ("\n\n   99999999999999999999999\n", 3, 4, "number too large")):
        st, out, err = tr.mote(t, src, "--tokens")
        t.check(st == 1 and out == "" and err == f"t{t._lang_files}.mote:{line}:{col}: {msg}\n",
                f"{src!r}: {st} {err!r}, not {line}:{col}: {msg}")

    for argv in ([], ["--tokens"], ["--bogus", "x.mote"], ["--tokens", "a.mote", "b.mote"],
                 ["--tokens", "--tree", "a.mote"]):
        st, out, err = tr.prog(t, "mote", argv)
        t.check(st == 2 and err.startswith("usage: mote ") and "--tokens" in err, f"mote {' '.join(argv)}: {st} {err!r}")
    st, out, err = tr.prog(t, "mote", ["--tokens", "nosuch.mote"])
    t.check((st, err) == (1, "mote: cannot open nosuch.mote\n"), f"a missing file: {st} {err!r}")
