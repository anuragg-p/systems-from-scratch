"""00.01 From a number to a running program

./cc reads a file (or standard input for "-") and writes the assembly of a
program whose main returns what the file says, to standard output or to the
file -o names. A file that is not a number (at 00.01; an expression later)
is an error: exit status 1 and no assembly. The command line takes one file,
-o, --help, and nothing else. The compiler's own source uses six headers of
the C library and the functions LIBC_FUNCTIONS lists, and builds without a
warning under -std=c11 -Wall -Wextra -pedantic.

At 00.01 the assembly is li a0, N; ret (check-timeline holds the project at
00.01 to that, exactly). Here the finished compiler is tested, so its code
for a number is the code generator's: li t0, N; mv a0, t0; ret.
"""

import os
import subprocess


def test(t):
    tr = t.track
    want = "  .globl main\nmain:\n  li t0, 42\n  mv a0, t0\n  ret\n"
    t.check(tr.asm(t, "42\n") == want, f"the assembly for 42:\n{tr.asm(t, '42')}")
    t.check(tr.asm(t, "  \n 42  \n\n") == want, "spaces and newlines around the number change nothing")
    t.check(tr.asm(t, "42") == want, "a file without a newline at its end is the same")
    for n in (0, 7, 255, 4294967296):
        t.check(f"  li t0, {n}\n" in tr.asm(t, f"{n}\n"), f"li t0, {n}")
    st, out = tr.run(t, "42\n")
    t.check((st, out) == (42, ""), f"the program returns 42 and prints nothing: {st} {out!r}")

    # Not a number: an error, and no assembly.
    for bad in ("x\n", "4 2\n", "\n", "4x\n"):
        st, out, err = tr.compile(t, bad)
        t.check(st == 1 and out == "" and err.strip(), f"{bad!r}: status 1, a message, no assembly: {st} {out!r} {err!r}")

    # -o, standard input, the command line.
    src = tr.write(t, "n.c", "42\n")
    cc = tr.cc_path(t)
    r = subprocess.run([cc, "-o", "out.s", "n.c"], cwd=t.tmp, capture_output=True, text=True)
    with open(os.path.join(t.tmp, "out.s")) as f:
        got = f.read()
    t.check(r.returncode == 0 and r.stdout == "" and got == want, f"-o out.s: {r.returncode} {r.stdout!r} {got!r}")
    r = subprocess.run([cc, "-"], input="42\n", capture_output=True, text=True)
    t.check(r.returncode == 0 and r.stdout == want, f"- reads standard input: {r.returncode} {r.stdout!r}")
    r = subprocess.run([cc, "--help"], capture_output=True, text=True)
    t.check(r.returncode == 0 and "usage: cc" in r.stderr, f"--help: {r.returncode} {r.stderr!r}")
    for argv, what in (([], "no file"), (["-x", src], "an unknown option"), ([src, src], "two files"),
                       (["-o"], "-o with no name")):
        r = subprocess.run([cc] + argv, capture_output=True, text=True)
        t.check(r.returncode == 1 and r.stdout == "" and r.stderr, f"{what}: status 1 and a message: {r.returncode} {r.stderr!r}")
    r = subprocess.run([cc, "nosuch.c"], cwd=t.tmp, capture_output=True, text=True)
    t.check(r.returncode == 1 and r.stderr == "cannot open nosuch.c\n", f"a missing file: {r.returncode} {r.stderr!r}")

    # The compiler's own source: only what it will have when it compiles itself.
    problems = tr.libc_problems(t.root)
    t.check(not problems, "the compiler uses more of the C library than it may:\n" + "\n".join(problems))
    said = tr.warnings(t)
    t.check(not said, f"the compiler's source is not warning-free under -pedantic:\n{said}")
