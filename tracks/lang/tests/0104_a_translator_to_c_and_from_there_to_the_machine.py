"""01.04 A translator: to C, and from there to the machine

./mote2c FILE.mote writes C: #include "rt.h", a main that declares every name a read or a ":="
gives a value (in the order they first appear) as a long set to 0, then a line of C for each
line, indentation kept, comments dropped, expressions copied as they are. It checks the form of
each statement and nothing else: a mistake in an expression goes through to the C compiler.
./motec FILE.mote translates into build/NAME.c, compiles with cc -O1 -fwrapv and links with
rt.o into build/NAME; a step that fails ends it with its status. Its programs agree with the
reference, except where C's int is narrower than the language's numbers (documented here).
"""

import os

GCD_C = """#include "rt.h"

int main(void) {
    long i = 0;
    long j = 0;
    i = getint();
    j = getint();
    while (i != j) {
        if (i > j) {
            i = i - j;
        } else {
            j = j - i;
        }
    }
    putint(i);
    return 0;
}
"""


def test(t):
    tr = t.track
    st, out, err = tr.prog(t, "mote2c", [os.path.join(t.root, "programs", "gcd.mote")])
    t.check((st, out, err) == (0, GCD_C, ""), f"mote2c programs/gcd.mote:\n{out}{err}")

    src = "# a comment\nread b\n\na := b * 2    # double\nif a > b then\n\twrite a\nend\nb := a\n"
    want = ('#include "rt.h"\n\nint main(void) {\n    long b = 0;\n    long a = 0;\n    b = getint();\n\n'
            '    a = b * 2;\n    if (a > b) {\n    \tputint(a);\n    }\n    b = a;\n    return 0;\n}\n')
    got = tr.mote2c(t, src)
    t.check(got == (0, want, ""), f"names in the order they appear, comments dropped, indentation kept:\n{got[1]}")

    # motec: the program runs, from build/ in the directory motec was run in.
    st, out, err = tr.motec(t, "read a\nread b\nwrite a * b\n", "6 7\n")
    t.check((st, out) == (0, "42\n"), f"motec: {st} {out!r} {err!r}")
    made = os.path.join(t.tmp, "build", f"t{t._lang_files}")
    t.check(os.path.exists(made + ".c") and os.path.exists(made), "motec leaves build/NAME.c and build/NAME")
    with open(os.path.join(t.root, "programs", "gcd.in")) as f:
        gcd_in = f.read()
    with open(os.path.join(t.root, "programs", "gcd.mote")) as f:
        t.check(tr.motec(t, f.read(), gcd_in)[:2] == (0, "21\n"), "motec on gcd.mote: 21")

    # A mistake in an expression goes through mote2c, and the C compiler finds it.
    st, out, err = tr.mote2c(t, "x := 1 +\nwrite x\n")
    t.check(st == 0 and "    x = 1 +;\n" in out, f"mote2c copies the expression as it is: {st}\n{out}")
    st, out, err = tr.motec(t, "x := 1 +\nwrite x\n")
    t.check(st == 1 and "error" in err and f"t{t._lang_files}.c" in err,
            f"motec stops with the C compiler's status, which complains about the C file: {st}\n{err}")

    # What mote2c does check: the form of each statement, by its first word.
    for src, line, msg in (("read\n", 1, "expected a name"), ("read x y\n", 1, "expected the end of the line"),
                           ("while x < 1\nend\n", 1, "expected 'do'"), ("if x < 1 thenx\nend\n", 1, "expected 'then'"),
                           ("x = 1\n", 1, "expected ':='"), ("then\n", 1, "expected a statement"),
                           ("x := 1\n5 := x\n", 2, "expected a statement"), ("end x\n", 1, "expected the end of the line")):
        st, out, err = tr.mote2c(t, src)
        t.check(st == 1 and err == f"t{t._lang_files}.mote:{line}: {msg}\n", f"{src!r}: {st} {err!r}, not {msg!r}")
    st, out, err = tr.script(t, "motec")
    t.check(st == 2 and err.startswith("usage: motec"), f"motec with no file: {st} {err!r}")
    st, out, err = tr.script(t, "motec", "nosuch.mote")
    t.check(st == 1 and "mote2c: cannot open nosuch.mote" in err, f"motec on a missing file: {st} {err!r}")

    # -fwrapv: the language's sums wrap around, and so do the C's.
    t.check(tr.motec(t, "x := 9223372036854775807\nwrite x + 1\nwrite x * x\n")[:2] == (0, f"{-2 ** 63}\n1\n"),
            "motec's programs wrap around (-fwrapv)")
    # Where C differs: 18 and 1000000007 are each an int in C, so their product is worked out in
    # 32 bits. The language's numbers are 64-bit, and mote0 says 18000000126.
    st, out, err = tr.motec(t, "write 18 * 1000000007\nx := 18\nwrite x * 1000000007\n")
    t.check((st, out) == (0, "820130942\n18000000126\n"), f"C's int in an expression of numbers alone: {out!r}")
    t.check(tr.mote0(t, "write 18 * 1000000007\n")[1] == "18000000126\n", "mote0 works in 64 bits")

    # Random programs, against the reference (none with a part made of numbers alone that
    # overflows an int: proggen.sample leaves those out).
    for text, text_in, want in tr.gen().sample(104, 25):
        got = tr.motec(t, text, text_in)
        t.check(got == (0, want, ""), f"motec and the reference differ on:\n{text}\ninput {text_in}\n"
                                      f"motec: {got}\nreference: {want!r}")
