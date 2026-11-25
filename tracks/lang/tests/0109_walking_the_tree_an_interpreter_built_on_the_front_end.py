"""01.09 Walking the tree: an interpreter built on the front end

./mote FILE, with no option, runs the program by walking its syntax tree, a variable's value in
its symbol table entry. It prints what mote0 prints, for the programs and for random ones held to
the reference. The dynamic rule is checked as it runs: "FILE:LINE:COL: x has no value yet" at
the use; division by zero at the "/"; read errors at the read; all status 1, after what was
written. Sums wrap around; the most negative number divided by -1 is itself.
"""

import os


def test(t):
    tr = t.track
    for name in ("gcd", "sum", "primes"):
        path = os.path.join(t.root, "programs", name)
        with open(path + ".in") as f, open(path + ".out") as g:
            text_in, want = f.read(), g.read()
        got = tr.prog(t, "mote", [path + ".mote"], text_in)
        t.check(got == (0, want, ""), f"mote programs/{name}.mote: {got}")

    t.check(tr.mote(t, "write 9223372036854775807 + 1\nx := 0 - 9223372036854775807 - 1\nwrite x / -1\n"
                       "write x * -1\nwrite -7 / 2\nwrite 7 / -2\nwrite -x\n") ==
            (0, f"{-2 ** 63}\n{-2 ** 63}\n{-2 ** 63}\n-3\n-3\n{-2 ** 63}\n", ""),
            "wrap-around, the most negative number by -1, rounding toward zero")
    t.check(tr.mote(t, "read a read b write a + b while a > 0 do a := a - 1 write a end",
                    input=" -4\n\n+10 ")[:2] == (0, "6\n"), "a program need not keep to one statement a line")

    for src, text_in, line, col, msg in (
            ("write 1\nif 1 > 2 then\n  x := 1\nend\nwrite x\n", "", 5, 7, "x has no value yet"),
            ("read a\nb := 0\nwrite a / b\n", "5", 3, 9, "division by zero"),
            ("write 1\nread x\n", "", 2, 1, "read: no more input"),
            ("read x\n", "abc", 1, 1, "read: not a number"),
            ("read x\n", "-", 1, 1, "read: not a number")):
        st, out, err = tr.mote(t, src, input=text_in)
        t.check(st == 1 and err == f"t{t._lang_files}.mote:{line}:{col}: {msg}\n" and out == ("1\n" if "write 1" in src else ""),
                f"{src!r}: {st} {out!r} {err!r}, not {line}:{col}: {msg}")
    # A syntax error stops everything before anything runs: nothing is written.
    st, out, err = tr.mote(t, "write 1\nwrite 2 +\n")
    t.check((st, out) == (1, ""), f"a syntax error, before anything runs: {st} {out!r}")

    g = tr.gen()
    for text, text_in, want in g.sample(109, 200):
        got = tr.mote(t, text, input=text_in)
        t.check(got == (0, want, ""), f"mote and the reference differ on:\n{text}\ninput {text_in}\n"
                                      f"mote: {got}\nreference: {want!r}")
