"""09.03 LZ77: finding repeats with a hash table

gzip --lz77 parses a file into literals and matches that rebuild it exactly, each match 3 to 258
bytes from at most 32768 back. The hash chains with no bound find the very matches the scan of the
whole window finds, with a fiftieth of the comparisons or less; with the default bound of 128
places, nearly the same bytes in matches, with fewer comparisons still. Repeats more than 32 KB
back are out of reach; on two letters at random a short bound cuts the long chains, for shorter
matches.
"""

import random


def test(t):
    T = t.track
    fx = T.fixtures("gzip")

    def lz77(path, *args):
        r = T.run(t, "gzip", ["--lz77", *args, path], env={"DS_STATS": "1", "DS_TRACE": "1"})
        with open(path, "rb") as f:
            data = f.read()
        toks = fx.tokens(r.err, "lz77")
        t.check(fx.rebuild(toks) == data, f"gzip --lz77 {' '.join(args)}: the tokens do not rebuild the input")
        s = T.stats(r.err)["lz77"]
        lits = sum(1 for tk in toks if tk[1] == 0)
        covered = sum(tk[2] for tk in toks if tk[1])
        t.check(r.out == f"{len(data)} bytes: {lits} literals, {len(toks) - lits} matches for the other {covered} bytes\n",
                f"the summary: {r.out!r}")
        t.check(s["literals"] == lits and s["matches"] == len(toks) - lits and s["match bytes"] == covered,
                f"the counts and the tokens agree: {s}")
        return toks, s

    text = T.gen(t, "text", 3000)
    scan, s_scan = lz77(text, "--algo=scan")
    hashed, s_hash = lz77(text, "--algo=hash", "--chain=0")
    t.check(scan == hashed, "with no bound on the chains, the hash table finds the very matches the scan finds")
    t.check(s_hash["comparisons"] * 50 < s_scan["comparisons"],
            f"the same matches for a fiftieth of the comparisons or less: {s_hash['comparisons']} against "
            f"{s_scan['comparisons']}")
    bounded, s_b = lz77(text)
    t.check(s_b["match bytes"] >= 0.98 * s_scan["match bytes"] and s_b["comparisons"] <= s_hash["comparisons"],
            f"the default bound of 128: nearly the same bytes in matches, for fewer comparisons: {s_b} {s_scan}")
    none, s_none = lz77(text, "--algo=none")
    t.check(s_none["matches"] == 0 and s_none["comparisons"] == 0, f"--algo=none finds nothing: {s_none}")

    # the book, too big for the scan: the default bound against no bound
    book = T.data(t, "book.txt")
    _, s_all = lz77(book, "--chain=0")
    _, s_128 = lz77(book)
    t.check(s_128["match bytes"] >= 0.99 * s_all["match bytes"] and s_128["comparisons"] < s_all["comparisons"],
            f"the book: a bound of 128 keeps 99% of the bytes in matches, for fewer comparisons: {s_128} {s_all}")

    # the window: a repeat 20000 bytes back is found, one 40000 back is not
    rng = random.Random(77)
    for size, reach in ((20000, True), (40000, False)):
        block = bytes(rng.randrange(256) for _ in range(size))
        toks, s = lz77(T.write(t, f"twice-{size}.bin", block + block), "--chain=0")
        far = [tk for tk in toks if tk[1] >= size]
        t.check(bool(far) == reach and (s["match bytes"] > 0.99 * size) == reach,
                f"a block of {size} bytes twice: {'found' if reach else 'out of reach'}: {s}")
        t.check(all(tk[1] <= 32768 for tk in toks), "no match from more than 32768 back")

    # two letters at random: every three bytes come back every few bytes, so the chains are long and
    # the matches short. A bound cuts the chains, tries no more places than it says, and pays in matches.
    ab = T.write(t, "ab.txt", bytes(rng.choice(b"ab") for _ in range(30000)))
    _, s4 = lz77(ab, "--chain=4")
    _, s_all = lz77(ab, "--chain=0")
    t.check(s4["chains cut"] > 0 and s4["candidates"] <= 4 * (s4["literals"] + s4["matches"]),
            f"--chain=4 on two letters at random: {s4}")
    t.check(s4["comparisons"] * 50 < s_all["comparisons"] and s4["matches"] > 2 * s_all["matches"],
            f"a fiftieth of the comparisons, for matches less than half as long: {s4} {s_all}")
    r = T.run(t, "gzip", ["--lz77", "--algo=tree"], check=False)
    t.check(r.rc == 2 and "no --algo 'tree' (have: hash, scan, none)" in r.err, f"--algo=tree:\n{r}")
    r = T.run(t, "gzip", ["--lz77", "--chain=x"], check=False)
    t.check(r.rc == 2 and "--chain wants a count" in r.err, f"--chain=x:\n{r}")
