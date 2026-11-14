xv6's own usertests (authors only)
==================================

An internal check of the kernel with xv6's real test program. Never shown:
nothing here is part of the project a reader sees, and the course's own
user/usertests.c (15 tests, shown in lesson 07.03 and on the reader's disk)
is a different, smaller program that stays as it is.

Source
------

usertests.c is user/usertests.c from xv6 for RISC-V, MIT PDOS,
https://github.com/mit-pdos/xv6-riscv, at commit
7e95e76a19a7168c8db63f3ea40c6641f9ead93e (branch riscv, 2025-08-04), the
last commit before xv6 merged lazy page allocation (3259cfc8), and so before
sbrk's eager/lazy flag (4a92b85b) and sleep() -> pause() (f5dea58c): the
system calls this track's kernel has. The file is git blob
7df0278252c8f72dcfa61be1b570b412e5ac40cc, last changed upstream in
a3f3a04f9135. Fetched from
https://raw.githubusercontent.com/mit-pdos/xv6-riscv/7e95e76a19a7168c8db63f3ea40c6641f9ead93e/user/usertests.c

Licence: MIT, Copyright (c) 2006-2024 Frans Kaashoek, Robert Morris, Russ
Cox, Massachusetts Institute of Technology. The full text is in
tracks/xv6/LICENSE. The root NOTICE lists this file too.

Changes from upstream
---------------------

Every change is marked "systems-from-scratch" in usertests.c.

1. Four regression tests backported from later xv6 commits, for bugs the
   kernel had (fixed in the same change, as upstream fixed them):
     pipezero, with pipezeroread   fa2ddcb7ca87a77af579380a6eafd5aff163b44f
                                   (fix: ffe25cbdc831, zero-length pipe read)
     killzero                      06aad25c735fd3159bdfae5680be4eab7b1668b2
                                   (fix: bd77f8e71cde, kill(0))
     partial_write                 0f4aa0604b12247bb2e06f06f365b397eefdeddf
                                   (fix: fb0fed836c71, writei)
     unlinkcwd                     9da28f56db5fde666ce26d3eac824a599a5155c1
                                   (fix: same commit, namex and create)
   The functions are upstream's text at fa2ddcb7ca87, placed and listed in
   quicktests[] where upstream has them: pipezero after exectest,
   killzero after killstatus, the other two at the end.
2. In pipezero, pause(50) is sleep(50): this kernel has the call under
   its older name.

Otherwise the file is byte for byte upstream's at 7e95e76a19a7. It builds
with the track's compiler flags (-Wall -Werror, gcc 15) against the
track's user library.

Skipped tests: none (SKIP in run.py is empty). A test for a feature the
kernel does not have goes in SKIP with the reason, rather than out of
usertests.c.

Running it
----------

    python3 tracks/xv6/tests/upstream/run.py             quick set (usertests -q, 64 tests)
                                                         on the finished kernel, about 80s
    python3 tracks/xv6/tests/upstream/run.py --core      the core-only kernel instead
    python3 tracks/xv6/tests/upstream/run.py --both      both kernels
    python3 tracks/xv6/tests/upstream/run.py --slow      the slow tests too (bigdir, manywrites,
                                                         badwrite, execout, diskfull,
                                                         outofinodes): about 4 minutes more
    ... --keep-going                                     after a failure, run the tests after
                                                         it one at a time
    ... --only copyin,sbrkfail                           just these, one at a time

./learn test xv6 --ref runs the default (quick set, finished kernel) as part
of the 07.03 check, tests/0703_utilities.py. It does so only on the track's
own code, not in a learner's workspace or a cut-out copy.

How it works
------------

run.py writes the project as the site shows it (harness/timeline.py) to
tracks/xv6/build-upstream/finished/ (the end of the track: the core and both
extensions) or build-upstream/core/ (the project at the last core lesson),
rewriting only files that changed, and builds it with its own Makefile plus
upstream.mk. That builds the normal kernel and fs.img, as a reader's make
does, and build/upstream/fs.img: the same programs and README with xv6's
usertests in place of the track's (its tests exec echo and open README, cat
and init). It boots that kernel under QEMU with that image (snapshot=on, so
every run starts from the same files), types `usertests -q`, and reads the
report test by test. A test still running after its timeout (90s quick, 600s
slow) is reported as hung; a kernel panic stops the run. usertests itself
stops at its first failure, and checks at the end that no free page was lost.
