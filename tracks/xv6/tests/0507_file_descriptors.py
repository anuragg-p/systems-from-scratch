"""05.07 Open files

struct file is reference counted, the system-wide table is finite, and
devices are reached through devsw[].
"""


def test(t):
    s = t.track.boot(t)
    s.expect(r"\[05\.07\] hello through devsw\[CONSOLE\]", timeout=20)
    t.track.selftest(s, "05.07", timeout=20)
