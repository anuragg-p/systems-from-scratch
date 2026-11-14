"""05.02 The buffer cache

A second bread of a block costs no disk read; reading NBUF other blocks
evicts it; and a process that wants a buffer another process holds
sleeps until it is released.
"""


def test(t):
    s = t.track.boot(t)
    s.expect(r"\[05\.02\] disk reads for block 200: first bread 1, second 0, after \d+ other blocks 1", timeout=20)
    t.track.selftest(s, "05.02", timeout=20)
