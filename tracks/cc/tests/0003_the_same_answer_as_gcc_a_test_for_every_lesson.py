"""00.03 The same answer as gcc: a test for every lesson

same FILE builds FILE with ./cc and with gcc for the same machine (the
expression wrapped in a main for gcc), runs both on QEMU, and prints
"same: status N" (exit 0) when the statuses and the outputs agree, or both
and "differ" (exit 1) when they do not. CC_UNDER_TEST names another compiler
to test in ./cc's place.
"""

import os
import stat


def test(t):
    tr = t.track
    for src, n in (("42\n", 42), ("0\n", 0), ("5 + 20 - 4\n", 21)):
        tr.write(t, "f.c", src)
        st, out, err = tr.script(t, "same", "f.c")
        t.check((st, out) == (0, f"same: status {n}\n"), f"same on {src!r}: {st} {out!r} {err!r}")
    t.check(tr.same(t, "42") == 42, "the fixture same() agrees")

    # A compiler that writes the wrong program: same notices.
    fake = os.path.join(t.tmp, "wrongcc")
    with open(fake, "w") as f:
        f.write("#!/bin/sh\n# cc -o OUT FILE, writing a program that returns 7 whatever FILE says\n"
                "printf '  .globl main\\nmain:\\n  li a0, 7\\n  ret\\n' > \"$2\"\n")
    os.chmod(fake, stat.S_IRWXU)
    tr.write(t, "f.c", "42\n")
    st, out, err = tr.script(t, "same", "f.c", env=dict(os.environ, CC_UNDER_TEST=fake))
    t.check(st == 1 and out == "ours: status 7\ngcc: status 42\ndiffer\n", f"a wrong compiler: {st} {out!r} {err!r}")
    # And one that agrees by luck, on 7.
    tr.write(t, "f.c", "7\n")
    st, out, err = tr.script(t, "same", "f.c", env=dict(os.environ, CC_UNDER_TEST=fake))
    t.check((st, out) == (0, "same: status 7\n"), f"the wrong compiler on 7: {st} {out!r}")

    st, out, err = tr.script(t, "same", "nosuch.c")
    t.check(st == 2 and err == "same: cannot open nosuch.c\n", f"a missing file: {st} {err!r}")
