"""06.02 System calls

Internal check: arguments reach the kernel (paths, buffers, counts) and
results come back in a0.
"""


def test(t):
    s = t.track.shell(t)
    out = t.track.run(s, "ls README")
    t.check("README" in out, f"ls printed {out!r}")
    out = t.track.run(s, "usertests badptr")
    t.check("badptr: OK" in out, out)
