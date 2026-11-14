"""05.03 mkfs and the on-disk layout

mkfs lays out boot block, superblock, log, inodes, bitmap and data, and
copies README onto the disk; the kernel reads back the same layout.
"""

import os
import struct


def test(t):
    s = t.track.boot(t)
    m = s.expect_line(r"\[05\.03\] superblock: size (\d+) nblocks (\d+) ninodes (\d+) nlog (\d+) logstart (\d+) "
                      r"inodestart (\d+) bmapstart (\d+)", timeout=20)
    with open(s.image, "rb") as f:
        f.seek(1024)
        disk = struct.unpack("<8I", f.read(32))
    t.check(tuple(int(x) for x in m.groups()) == disk[1:], f"kernel read {m.groups()}, image has {disk[1:]}")
    size = int(s.expect(r"\[05\.03\] README is inode \d+, (\d+) bytes").group(1))
    t.check(size == os.path.getsize(os.path.join(t.root, "README.md")), "README on disk should match the host file")
    t.track.selftest(s, "05.03", timeout=20)
