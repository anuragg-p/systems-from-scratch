"""02.03 Spinlocks and multiple harts

Three harts increment one counter 100000 times each. With the lock the
total is exact. Without it, increments are lost - the race the lock
exists to stop.
"""


def test(t):
    s = t.track.boot(t, cpus=3)
    m = s.expect_line(r"\[02\.03\] (\d+) harts x (\d+) increments: with the lock (\d+), without it (\d+)")
    harts, rounds, locked, racy = (int(x) for x in m.groups())
    t.check(harts == 3, f"expected all 3 harts to take part, got {harts}")
    t.check(locked == harts * rounds, f"locked counter should be {harts * rounds}, got {locked}")
    t.check(racy <= harts * rounds, "the unlocked counter cannot gain increments")
    t.track.selftest(s, "02.03")
