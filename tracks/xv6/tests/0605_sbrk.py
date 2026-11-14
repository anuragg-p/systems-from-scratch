"""06.05 sbrk and the user heap

Internal check: memory grows and shrinks, memory past the break faults,
and malloc builds on sbrk.
"""


def test(t):
    s = t.track.shell(t)
    for name in ("sbrkbasic", "sbrkfault", "mallocmany"):
        out = t.track.run(s, f"usertests {name}", timeout=60)
        t.check(f"{name}: OK" in out, out)
