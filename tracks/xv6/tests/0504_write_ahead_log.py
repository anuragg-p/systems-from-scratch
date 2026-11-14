"""05.04 The write-ahead log

A committed transaction leaves the on-disk log empty. (To watch recovery
work, build with -DLOGCRASH=2 and reboot: see the lesson.)
"""


def test(t):
    s = t.track.boot(t)
    s.expect(r"\[05\.04\] recovery at boot replayed 0 blocks", timeout=20)
    t.track.selftest(s, "05.04", timeout=20)
