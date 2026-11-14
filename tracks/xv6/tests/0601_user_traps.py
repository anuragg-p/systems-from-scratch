"""06.01 The trampoline and user traps

Internal check: init and the shell run in user mode, and every system
call they make goes in through uservec and back out through userret.
"""


def test(t):
    s = t.track.shell(t)
    out = t.track.run(s, "echo user mode works")
    t.check("user mode works" in out, f"echo printed {out!r}")
