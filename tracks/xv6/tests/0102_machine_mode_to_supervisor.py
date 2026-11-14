"""01.02 Machine mode and the drop to supervisor mode

Every hart runs start() in machine mode and arrives in main() through
mret. Hart 0 initializes the kernel; the others wait for it, then report
in. (03.01 proves they really are in supervisor mode.)
"""


def test(t):
    s = t.track.boot(t, cpus=3)
    s.expect(r"xv6 kernel is booting")
    seen = set()
    while len(seen) < 2:
        m = s.expect(r"hart (\d) starting")
        seen.add(m.group(1))
    t.check(seen == {"1", "2"}, f"expected harts 1 and 2 to start, saw {sorted(seen)}")
