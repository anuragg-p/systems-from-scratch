"""00.02 Running and debugging the kernel

Internal check: the normal (not SELFTEST) build that `./learn run` and
the Run it panel use builds and boots to a shell.
"""


def test(t):
    build = t.track.prepare(t.root)
    if build:
        t.run(build)
    s = t.spawn(t.track.run_argv(t.root), name="qemu", fail_on=[r"panic: "])
    s.expect(r"xv6 kernel is booting", timeout=20)
    s.expect(r"init: starting sh", timeout=20)
    s.expect(r"\$ ", timeout=10)
