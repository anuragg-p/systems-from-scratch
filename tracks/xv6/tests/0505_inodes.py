"""05.05 Inodes

A file bigger than NDIRECT blocks spills into the indirect block, reads
back intact, and frees every block when its last link goes.
"""


def test(t):
    s = t.track.boot(t)
    s.expect(r"\[05\.05\] /bigfile: 32 blocks \(12 direct, 20 via the indirect block\) took 33 disk blocks", timeout=20)
    t.track.selftest(s, "05.05", timeout=20)
