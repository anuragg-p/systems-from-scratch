xv6 from scratch
================

This file was copied onto the disk by mkfs when the kernel was built.
If you can read it with cat, then the whole path works: the shell ran
cat with fork and exec, cat called open and read, the kernel walked the
directory tree, read inodes and blocks through the buffer cache, and
the virtio driver fetched them from the disk image.

Try: ls, cat README, echo hi | wc, mkdir d, ls d, usertests
Control-P lists processes. Control-a x quits QEMU.
