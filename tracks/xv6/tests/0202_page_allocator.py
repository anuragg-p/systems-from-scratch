"""02.02 The page allocator

kalloc hands out every free page exactly once, page aligned and filled
with junk, and kfree takes each one back.
"""


def test(t):
    s = t.track.boot(t)
    m = s.expect(r"\[02\.02\] (\d+) pages of RAM, (\d+) used during boot, took all (\d+) and gave them back")
    total, used, took = (int(x) for x in m.groups())
    t.check(took == total - used, "kalloc should hand out every page that is still free")
    t.track.selftest(s, "02.02")
