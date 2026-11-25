"""01.03 An interpreter: the program run from its text

./mote0 [--count] FILE runs a program a line at a time, straight from its characters: names
in a table looked up by their text, a false condition read past to its end, a loop's lines
read again on every pass. --count prints "N lines read": every line looked at, comments and
lines only skipped included (gcd on 1071 462: 88; sum on 100: 409; primes on 30: 844), so a
comment in sum's loop costs 101 lines more: one a pass, and one when the loop is read past. Errors are FILE:LINE: message, status 1, found only
when the line is reached. It agrees with the reference on random programs.
"""

import os


def test(t):
    tr = t.track
    for name, count in (("gcd", 88), ("sum", 409), ("primes", 844)):
        path = os.path.join(t.root, "programs", name)
        with open(path + ".in") as f, open(path + ".out") as g:
            text_in, want = f.read(), g.read()
        got = tr.prog(t, "mote0", ["--count", path + ".mote"], text_in)
        t.check(got == (0, want, f"{count} lines read\n"), f"mote0 --count programs/{name}.mote: {got}")

    # The book's remark, as an experiment: a comment inside the loop is read on every pass (100
    # of them), and once more when the false condition reads past the loop to its end.
    with open(os.path.join(t.root, "programs", "sum.mote")) as f:
        sum_mote = f.read()
    commented = sum_mote.replace("    i := i + 1\n", "    # the next number\n    i := i + 1\n")
    got = tr.mote0(t, commented, "100\n", "--count")
    t.check(got == (0, "5050\n", "510 lines read\n"), f"sum with a comment in its loop: {got}, not 409 + 101")

    # Blocks: nested loops, if and else, an empty block, a loop that never runs.
    prog = """read n
total := 0
i := 0
while i < n do
    j := 0
    while j < i do
        if j - j / 2 * 2 == 0 then
            total := total + j
        else
            total := total - 1
        end
        j := j + 1
    end
    if i > 100 then
    end
    i := i + 1
end
while 1 > 2 do
    write 99
end
write total
write -(2 - 9) * (3 + 4) / 2
"""
    g = tr.gen()
    for n in (0, 1, 5, 12):
        want = g.evaluate(prog, f"{n}\n")
        got = tr.mote0(t, prog, f"{n}\n")
        t.check(got == (0, want[1], ""), f"the nested blocks, n = {n}: {got}, not {want}")
    t.check(tr.mote0(t, "write 9223372036854775807 + 1\nx := 0 - 9223372036854775807 - 1\nwrite x / -1\n"
                        "write x * -1\nwrite -7 / 2\n") ==
            (0, f"{-2 ** 63}\n{-2 ** 63}\n{-2 ** 63}\n-3\n", ""),
            "wrap-around, the most negative number by -1, rounding toward zero")
    t.check(tr.mote0(t, "read a\nread b\nwrite a + b\n", " -4\n\n+10 ") == (0, "6\n", ""), "read")

    # Only the lines reached are looked at: a mistake in a skipped line is not seen.
    t.check(tr.mote0(t, "if 1 > 2 then\n    x := 1 +\nend\nwrite 3\n") == (0, "3\n", ""),
            "a line only read past is never checked")

    # Errors, at the line, when it is reached; what was written before stays written.
    for src, text_in, line, msg in (
            ("write 1\nwrite y\n", "", 2, "y has no value yet"),
            ("write 1 / (2 - 2)\n", "", 1, "division by zero"),
            ("read x\n", "", 1, "read: no more input"),
            ("read x\n", "abc", 1, "read: not a number"),
            ("x := 1 +\n", "", 1, "expected a number, a name or '('"),
            ("x = 1\n", "", 1, "expected ':='"),
            ("while 1 < 2\nend\n", "", 1, "expected 'do'"),
            ("if 1 < 2\nend\n", "", 1, "expected 'then'"),
            ("if 1 then\nend\n", "", 1, "expected a comparison"),
            ("x := (1 + 2\n", "", 1, "expected ')'"),
            ("write 1 2\n", "", 1, "expected the end of the line"),
            ("read n while n > 0 do\n", "5", 1, "expected the end of the line"),
            ("read 5\n", "", 1, "expected a name"),
            ("read do\n", "", 1, "expected a name"),
            ("write 1\nend\n", "", 2, "expected a statement"),
            ("else\n", "", 1, "expected a statement"),
            ("while 1 < 2 do\nelse\nend\n", "", 2, "expected a statement"),
            ("then := 4\n", "", 1, "expected a statement"),
            ("write then\n", "", 1, "expected a number, a name or '('"),
            ("write 9223372036854775808\n", "", 1, "number too large"),
            ("x := 1\nwhile x < 2 do\n    x := x + 1\n", "", 3, "expected 'end'"),
            ("if 1 > 2 then\n    write 1\n", "", 2, "expected 'end'")):
        st, out, err = tr.mote0(t, src, text_in)
        name = f"t{t._lang_files}.mote"
        t.check(st == 1 and err == f"{name}:{line}: {msg}\n", f"{src!r}: {st} {err!r}, not line {line}: {msg}")
    t.check(tr.mote0(t, "write 1\nwrite y\n")[1] == "1\n", "what was written before an error stays written")

    for argv in (["a.mote", "b.mote"], ["--fast", "a.mote"]):
        st, out, err = tr.prog(t, "mote0", argv)
        t.check(st == 2 and err.startswith("usage: mote0"), f"mote0 {' '.join(argv)}: {st} {err!r}")
    t.check(tr.prog(t, "mote0", ["nosuch.mote"]) == (1, "", "mote0: cannot open nosuch.mote\n"), "a missing file")

    # Random programs, one statement a line, against the reference.
    for text, text_in, want in g.sample(103, 100):
        got = tr.mote0(t, text, text_in)
        t.check(got == (0, want, ""), f"mote0 and the reference differ on:\n{text}\ninput {text_in}\n"
                                      f"mote0: {got}\nreference: {want!r}")
