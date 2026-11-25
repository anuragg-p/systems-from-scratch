"""01.02 Your language, and the programs you want it to run

rt.c gives C programs getint and putint with the machine's behaviour: white space skipped, a
sign, digits that wrap around; "getint: no more input" (or "not a number") and status 1. make
gcd builds ./gcd from programs/gcd.c and rt.o, and it gives math.gcd. The programs of the
language, gcd, sum and primes, each have a .in and a .out, and each .out is what the reference
(tests/proggen.py, in Python) prints for the program on its .in. gcd.mote is the plan's text.
"""

import math
import os
import random
import subprocess

GCD_MOTE = """# gcd.mote: the greatest common divisor of two numbers
read i
read j
while i != j do
    if i > j then
        i := i - j
    else
        j := j - i
    end
end
write i
"""


def test(t):
    tr = t.track
    r = subprocess.run(["make", "-s", "gcd"], cwd=t.root, capture_output=True, text=True)
    t.check(r.returncode == 0 and os.path.exists(os.path.join(t.root, "gcd")), f"make gcd:\n{r.stdout}{r.stderr}")
    rng = random.Random(102)
    for a, b in [(1071, 462), (1, 1), (12, 18), (2 ** 33, 6)] + [(rng.randint(1, 5000), rng.randint(1, 5000))
                                                               for _ in range(30)]:
        got = tr.prog(t, "gcd", [], f"{a} {b}\n")
        t.check(got == (0, f"{math.gcd(a, b)}\n", ""), f"./gcd on {a} {b}: {got}")
    t.check(tr.prog(t, "gcd", [], "+12\n\t18") == (0, "6\n", ""), "getint takes a + sign and any white space")
    t.check(tr.prog(t, "gcd", [], "") == (1, "", "getint: no more input\n"), "./gcd with no input")
    t.check(tr.prog(t, "gcd", [], "12 x") == (1, "", "getint: not a number\n"), "./gcd on '12 x'")

    # rt.o linked into a program of our own: every number of the input, back out.
    src = tr.write(t, "echo.c", '#include "rt.h"\nint main(void) {\n  for (;;)\n    putint(getint());\n}\n')
    exe = os.path.join(t.tmp, "echo")
    r = subprocess.run(["cc", "-I", t.root, "-o", exe, src, os.path.join(t.root, "rt.o")], capture_output=True,
                       text=True)
    t.check(r.returncode == 0, f"a C program linked with rt.o:\n{r.stderr}")
    r = subprocess.run([exe], input=" -5 +7 9223372036854775807 9223372036854775808 18446744073709551617 -0",
                       capture_output=True, text=True)
    want = ["-5", "7", str(2 ** 63 - 1), str(-2 ** 63), "1", "0"]
    t.check((r.returncode, r.stdout.split(), r.stderr) == (1, want, "getint: no more input\n"),
            f"getint and putint: {r.returncode} {r.stdout.split()} {r.stderr!r}")

    # The programs, and what they should print: the reference says.
    g = tr.gen()
    with open(os.path.join(t.root, "programs", "gcd.mote")) as f:
        t.check(f.read() == GCD_MOTE, "programs/gcd.mote is the plan's text")
    for name, first in (("gcd", "21\n"), ("sum", "5050\n"), ("primes", "2\n3\n5\n")):
        texts = []
        for ext in (".mote", ".in", ".out"):
            path = os.path.join(t.root, "programs", name + ext)
            t.check(os.path.exists(path), f"programs/{name}{ext} is missing")
            with open(path) as f:
                texts.append(f.read())
        how, out = g.evaluate(texts[0], texts[1])
        t.check(how == "ok" and out == texts[2] and out.startswith(first),
                f"programs/{name}.out is not what the reference prints ({how}):\n{out}")
        t.check(not g.c_int_overflow(g.parse(texts[0])), f"{name}.mote must mean the same in C (motec)")
    t.check(texts[2] == "".join(f"{p}\n" for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29)), "the primes up to 30")
