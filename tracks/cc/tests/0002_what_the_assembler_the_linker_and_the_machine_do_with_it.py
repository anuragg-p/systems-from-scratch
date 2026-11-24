"""00.02 What the assembler, the linker and the machine do with it

ccrun FILE compiles FILE with ./cc, assembles it and rt/start.S, links them
with rt/link.ld, and runs the program on QEMU's bare virt machine; its exit
status is what main returned, the low 8 bits of it. It works from any
directory. A missing input file is one line on stderr. A missing tool is one
line that says what to install.
"""

import os
import stat


def test(t):
    tr = t.track
    for n in (0, 1, 42, 255):
        tr.write(t, f"n{n}.c", f"{n}\n")
        st, out, err = tr.script(t, "ccrun", f"n{n}.c")
        t.check((st, out, err) == (n, "", ""), f"ccrun on {n}: status {st}, {out!r} {err!r}")
    # A status is 8 bits, as on Unix: 256 is 0, 300 is 44.
    for n, want in ((256, 0), (300, 44)):
        tr.write(t, f"n{n}.c", f"{n}\n")
        st, _, _ = tr.script(t, "ccrun", f"n{n}.c")
        t.check(st == want, f"ccrun on {n}: status {st}, not {want}")
    # The fixture run() does what ccrun does.
    t.check(tr.run(t, "42\n") == (42, ""), "run() and ccrun agree")

    # From another directory, the file named from there.
    sub = os.path.join(t.tmp, "a", "b")
    os.makedirs(sub)
    tr.write(t, os.path.join("a", "seven.c"), "7\n")
    st, out, err = tr.script(t, "ccrun", "../seven.c", cwd=sub)
    t.check((st, err) == (7, ""), f"ccrun run from another directory: {st} {err!r}")

    # A missing file: one clean line.
    st, out, err = tr.script(t, "ccrun", "nosuch.c")
    t.check(st == 1 and err == "cannot open nosuch.c\n" and out == "", f"a missing file: {st} {out!r} {err!r}")
    st, out, err = tr.script(t, "ccrun")
    t.check(st == 2 and err.startswith("usage: ccrun"), f"no file: {st} {err!r}")

    # A missing tool: one line saying what. A PATH with only what ccrun needs besides the tools.
    bindir = os.path.join(t.tmp, "bin")
    os.makedirs(bindir)
    for tool in ("dirname", "mkdir"):
        for d in ("/usr/bin", "/bin"):
            if os.path.exists(os.path.join(d, tool)):
                os.symlink(os.path.join(d, tool), os.path.join(bindir, tool))
                break
    env = dict(os.environ, PATH=bindir)
    st, out, err = tr.script(t, "ccrun", "n42.c", env=env)
    t.check(st == 2 and err.count("\n") == 1 and "no RISC-V assembler" in err and "install" in err,
            f"no assembler: {st} {err!r}")
    fake = os.path.join(bindir, "riscv64-elf-as")
    with open(fake, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(fake, stat.S_IRWXU)
    st, out, err = tr.script(t, "ccrun", "n42.c", env=env)
    t.check(st == 2 and err == "ccrun: no qemu-system-riscv64: install QEMU\n", f"no QEMU: {st} {err!r}")
