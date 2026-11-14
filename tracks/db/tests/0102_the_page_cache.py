"""01.02 The page cache

Pages read once are served from memory; a cache far smaller than the
table still gives right answers, evicting cold pages as it goes.
"""


def test(t):
    tr = t.track
    f = tr.path(t)
    rows = "".join(f"INSERT INTO t VALUES({i}, 'row {i} {'x' * 60}');\n" for i in range(1, 3001))
    tr.db(t, f, f"CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT);\nBEGIN;\n{rows}COMMIT;\n")
    npages = int(tr.db(t, f, "PRAGMA page_count;").out)
    want = tr.sqlite(t, f, "SELECT id, v FROM t;").out

    one = tr.db(t, f, "SELECT id, v FROM t;", env={"DB_STATS": "1"})
    two = tr.db(t, f, "SELECT id, v FROM t;\nSELECT id, v FROM t;", env={"DB_STATS": "1"})
    t.check(one.out == want and two.out == want * 2, "a full scan returned different rows from sqlite3")
    s1, s2 = tr.stats(one.err), tr.stats(two.err)
    t.check(s1["cache misses"] >= npages - 1, f"the first scan must read every page: {s1}")
    t.check(s2["cache misses"] == s1["cache misses"],
            f"with room for the whole table, the second scan must hit the cache every time: "
            f"one scan {s1['cache misses']} misses, two scans {s2['cache misses']}")
    t.check(s2["cache hits"] > s1["cache hits"], f"the second scan should be served from the cache: {s1} vs {s2}")

    small = tr.db(t, f, "SELECT id, v FROM t;\nSELECT id, v FROM t;", env={"DB_STATS": "1", "DB_CACHE_PAGES": "10"})
    t.check(small.out == want * 2, "with a 10-page cache, a scan returned different rows")
    s3 = tr.stats(small.err)
    t.check(s3["evictions"] > 0, f"a 10-page cache over a {npages}-page table must evict: {s3}")
    t.check(s3["cache misses"] >= 2 * (npages - 10), f"a 10-page cache cannot keep the table between scans: {s3}")
