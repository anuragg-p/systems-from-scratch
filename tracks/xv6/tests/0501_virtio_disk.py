"""05.01 The virtio block device

The driver reads the superblock straight off the disk, and a block it
writes really lands in the disk image file on the host.
"""


def test(t):
    s = t.track.boot(t)
    s.expect(r"\[05\.01\] read block 1 from the device: magic 10203040", timeout=20)
    t.track.selftest(s, "05.01", timeout=20)
    s.close()
    with open(s.image, "rb") as f:
        f.seek(1999 * 1024)
        t.check(f.read(30) == b"written by the 05.01 self-test", "block 1999 of the image should hold the pattern")
