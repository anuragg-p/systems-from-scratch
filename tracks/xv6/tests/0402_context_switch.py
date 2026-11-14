"""04.02 Context switch and the scheduler

Two kernel threads take turns 1000 times each, giving up the CPU with
yield() until it is their turn. Every hand-off goes through swtch() into
the scheduler and back out on another thread's stack.
"""


def test(t):
    s = t.track.boot(t)
    m = s.expect_line(r"\[04\.02\] ping and pong: (\d+) hand-offs, (\d+) yields, ran on harts ([0-9a-f]+) and ([0-9a-f]+)")
    t.check(int(m.group(1)) == 2000, f"expected 2000 hand-offs, got {m.group(1)}")
    t.check(int(m.group(2)) > 0, "the threads should have had to yield at least once")
    t.track.selftest(s, "04.02")
