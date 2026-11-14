"""04.04 Preemption

Six threads that never give up the CPU, on three harts. Only the timer
interrupt can move a hart from one to another - and it does: all six
run, and the sleeping test thread gets a hart back to stop them.
"""


def test(t):
    s = t.track.boot(t, cpus=3)
    m = s.expect(r"\[04\.04\] (\d+) spinners on (\d+) harts, none ever yields: (\d+) of them ran", timeout=20)
    n, harts, ran = (int(x) for x in m.groups())
    t.check(n > harts, "the test needs more spinners than harts to mean anything")
    t.check(ran == n, f"only {ran} of {n} spinners ever ran: no preemption")
    t.track.selftest(s, "04.04")
