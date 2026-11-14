"""04.03 Sleep and wakeup

A producer and a consumer pass 1000 numbers through a one-slot mailbox,
each sleeping while it cannot proceed. No number is lost or duplicated,
so the sum is exactly 1000 * 1001 / 2.
"""


def test(t):
    s = t.track.boot(t)
    m = s.expect(r"\[04\.03\] 1000 items through a one-slot mailbox: sum (\d+), (\d+) sleeps")
    t.check(int(m.group(1)) == 500500, f"sum should be 500500, got {m.group(1)}")
    t.check(int(m.group(2)) > 0, "the threads should have slept")
    t.track.selftest(s, "04.03")
