"""01.05 The tools around a language: a prompt and a checker

./mote0 with no file is a prompt: "> " asks for a line and runs it; a while or an if holds
the lines, asked for with ". ", until its end; names keep their values; an error is "line N:
message" and the prompt comes back; at the prompt a read takes a line of its own; the end of
the input ends it with status 0. ./agree [DIR] runs every program with a .in and a .out each
way there is and prints a row each (ok or DIFFERS) and a line that sums up; status 1 if any
differs.
"""

import os
import shutil


def test(t):
    tr = t.track
    session = "x := 6\nwrite x * 7\nwhile x > 3 do\n  write x\n  x := x - 1\nend\nwrite y\nwrite x\n" \
              "read z\n41\nwrite z + 1\n\nif x > 100 then\nelse\n    write 0 - x\nend\n"
    want = "> > 42\n> . . . 6\n5\n4\n> > 3\n> > 42\n> > . . . -3\n> \n"
    st, out, err = tr.prog(t, "mote0", [], session)
    t.check((st, out, err) == (0, want, "line 7: y has no value yet\n"),
            f"a session at the prompt:\n{out}\n{err!r} (status {st})")
    st, out, err = tr.prog(t, "mote0", [], "write 1\nwrite 1 / 0\nend\nwrite 2\n")
    t.check((st, out, err) == (0, "> 1\n> > > 2\n> \n", "line 2: division by zero\nline 3: expected a statement\n"),
            f"errors at the prompt: {out!r} {err!r}")
    st, out, err = tr.prog(t, "mote0", [], "while 1 < 2 do\nwrite 1\n")
    t.check((st, out) == (0, "> . . \n"), f"a block not closed when the input ends is never run: {st} {out!r}")
    st, out, err = tr.prog(t, "mote0", [], "")
    t.check((st, out, err) == (0, "> \n", ""), f"no input at all: {st} {out!r} {err!r}")

    # agree, on the project's programs: every way, every one ok.
    st, out, err = tr.script(t, "agree", cwd=t.tmp)
    rows = out.split("\n")
    t.check(st == 0 and rows[:3] == ["gcd     mote0 ok  motec ok  mote ok  machine ok  machine -O ok",
                                     "primes  mote0 ok  motec ok  mote ok  machine ok  machine -O ok",
                                     "sum     mote0 ok  motec ok  mote ok  machine ok  machine -O ok"]
            and rows[3] == "3 programs, 5 ways each: all agree", f"./agree (status {st}):\n{out}{err}")
    t.check(os.path.exists(os.path.join(t.tmp, "build", "gcd.mote0.out")), "agree keeps what each way printed in build/")

    # A program whose expected output is wrong: every way differs, and agree says how many.
    progs = os.path.join(t.tmp, "progs")
    os.makedirs(progs)
    for f in ("gcd.mote", "gcd.in", "gcd.out", "sum.mote", "sum.in"):
        shutil.copy(os.path.join(t.root, "programs", f), progs)
    with open(os.path.join(progs, "sum.out"), "w") as f:
        f.write("5051\n")
    with open(os.path.join(progs, "a_long_name.mote"), "w") as f:
        f.write("write 1\n")                         # no .in and no .out: not one of agree's
    st, out, err = tr.script(t, "agree", progs, cwd=t.tmp)
    t.check(st == 1 and out == "gcd  mote0 ok  motec ok  mote ok  machine ok  machine -O ok\n"
                               "sum  mote0 DIFFERS  motec DIFFERS  mote DIFFERS  machine DIFFERS  machine -O DIFFERS\n"
                               "2 programs, 5 ways each: 5 differ\n", f"agree with a wrong .out (status {st}):\n{out}")
    os.remove(os.path.join(progs, "sum.mote"))
    with open(os.path.join(progs, "gcd.out"), "w") as f:
        f.write("22\n")
    st, out, err = tr.script(t, "agree", progs, cwd=t.tmp)
    t.check(st == 1 and out.endswith("1 program, 5 ways each: 5 differ\n"), f"one program: {out!r}")
