"""09.02 Inflate: reading a real gzip file

gunzip gives back the very bytes the system's gzip compressed, at every level from -1 to -9, and
what Python's zlib wrote at every level and strategy (stored, fixed and dynamic blocks, small
windows, flushes), Info-ZIP's zip where there is one, and gzip headers with every optional field,
several members in one file included. Reading codes a bit at a time gives the same bytes, with
every bit walked; the table reads most symbols with one look. Damaged data is an error that says
what is wrong, status 2 and no output, never a crash: a file cut short in its header, all through
its data and in its trailer, random damage, and hand-made blocks with a match before the start, a
reserved block type, bad lengths and codes.
"""

import os
import random
import zlib


def test(t):
    T = t.track
    fx = T.fixtures("gzip")

    def gunzip(data, args=(), check=True):
        return T.run(t, "gunzip", list(args) + ["-c"], input=data, check=check)

    def same(data, gz, what, args=()):
        r = gunzip(gz, args, check=False)
        t.check(r.rc == 0 and r.raw == data, f"{what}: bin/gunzip {' '.join(args)} gave {len(r.raw)} bytes, "
                                             f"not the {len(data)} that went in:\n{r.err[-500:]}")
        return r

    book = T.data(t, "book.txt")
    with open(book, "rb") as f:
        text = f.read()
    rng = random.Random(9)
    noise = bytes(rng.randrange(256) for _ in range(70000))
    inputs = {"the book": text, "nothing": b"", "one byte": b"x", "zeros": bytes(300000),
              "noise": noise, "lines": open(T.gen(t, "lines", 20000), "rb").read()}

    # the system's gzip, every level
    for what, data in inputs.items():
        path = T.write(t, "in.bin", data)
        for level in range(1, 10):
            same(data, T.system(t, ["gzip", f"-{level}", "-c", path]).raw, f"{what}, the system's gzip -{level}")

    # Python's zlib, every way: the three block types all turn up
    kinds = {"stored blocks": 0, "fixed blocks": 0, "dynamic blocks": 0}
    for what, gz in fx.zlib_variants(text[:200000]):
        r = T.run(t, "gunzip", ["-c"], input=gz, env={"DS_STATS": "1"}, check=False)
        t.check(r.rc == 0 and r.raw == text[:200000], f"{what}: not the bytes that went in:\n{r.err[-300:]}")
        for k in kinds:
            kinds[k] += T.stats(r.err)["inflate"][k]
    t.check(all(kinds.values()), f"every kind of block read: {kinds}")

    raw = fx.zip_deflate(t, book)
    if raw is not None:
        same(text, fx.member(raw, text), "Info-ZIP's zip -9")

    # the optional header fields, and several members
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = c.compress(text) + c.flush()
    for fields in ({"name": b"book.txt"}, {"comment": b"a comment\nof two lines"}, {"extra": b"AP\x02\x00hi"},
                   {"hcrc": True}, {"name": b"x", "comment": b"y", "extra": b"", "hcrc": True}, {"flg": 1}):
        same(text, fx.member(raw, text, **fields), f"a header with {fields}")
    one, two = fx.member(raw, text), T.system(t, ["gzip", "-c"], input=b"and more\n").raw
    same(text + b"and more\n" + text, one + two + one, "three members")
    t.check(T.system(t, ["gunzip", "-c"], input=one + two).raw == text + b"and more\n", "the system's agrees")

    # a bit at a time: the same bytes, every bit of every code walked; the table does it in a look
    gz = T.system(t, ["gzip", "-9", "-c", book]).raw
    r1 = T.run(t, "gunzip", ["-c", "--algo=bits"], input=gz, env={"DS_STATS": "1"})
    r2 = T.run(t, "gunzip", ["-c"], input=gz, env={"DS_STATS": "1"})
    t.check(r1.raw == text == r2.raw, "--algo=bits and --algo=table give the book back")
    bits, table = T.stats(r1.err)["inflate"], T.stats(r2.err)["inflate"]
    t.check(bits["symbols"] == table["symbols"] == table["table lookups"] and bits["table lookups"] == 0,
            f"the same symbols, each looked up once with the table: {bits} {table}")
    t.check(bits["bits walked"] > 4 * bits["symbols"], f"a bit at a time: several bits a symbol: {bits}")
    t.check(table["bits walked"] * 20 < bits["bits walked"],
            f"the table: only the codes over 9 bits are walked, a twentieth of the bits or less: {table}")

    # the files: x.gz becomes x and goes; -k keeps it; -t writes nothing; x there already is an error
    gzpath = T.write(t, "book.txt.gz", gz)
    target = gzpath[:-3]
    T.run(t, "gunzip", [gzpath])
    t.check(open(target, "rb").read() == text and not os.path.exists(gzpath), "gunzip x.gz: x, and no x.gz")
    T.write(t, "book.txt.gz", gz)
    r = T.run(t, "gunzip", [gzpath], check=False)
    t.check(r.rc == 2 and "already exists" in r.err, f"gunzip over a file that is there:\n{r}")
    T.run(t, "gunzip", ["-f", "-k", gzpath])
    t.check(open(gzpath, "rb").read() == gz, "-k keeps the .gz")
    r = T.run(t, "gunzip", ["-t", gzpath])
    t.check(r.out == "", "-t writes nothing")
    r = T.run(t, "gunzip", [T.write(t, "plain.txt", "x")], check=False)
    t.check(r.rc == 2 and "does not end in .gz" in r.err, f"gunzip on a name without .gz:\n{r}")
    r = T.run(t, "gunzip", ["--algo=tree"], check=False)
    t.check(r.rc == 2 and "no --algo 'tree' (have: table, bits)" in r.err, f"gunzip --algo=tree:\n{r}")

    # damage: an ordinary error, status 2, nothing written, never a crash
    def bad(data, want, what):
        r = gunzip(data, check=False)
        t.check(r.rc == 2 and r.raw == b"" and r.err.startswith("gunzip: stdin: ") and want in r.err,
                f"{what}: wanted an error with {want!r}:\n{r}")

    small = T.system(t, ["gzip", "-9", "-c"], input=text[:3000]).raw
    cuts = set(range(0, 40)) | set(range(40, len(small) - 20, 5)) | set(range(len(small) - 20, len(small)))
    for n in sorted(cuts):
        r = gunzip(small[:n], check=False)
        t.check(r.rc == 2 and r.raw == b"" and r.err.startswith("gunzip: stdin: "), f"cut to {n} bytes:\n{r}")
    rng = random.Random(1952)
    for i in range(150):
        d = bytearray(small)
        for _ in range(1 + i % 4):
            d[rng.randrange(10, len(d))] ^= 1 << rng.randrange(8)
        r = gunzip(bytes(d), check=False)
        t.check(r.rc == 2 or (r.rc == 0 and r.raw == text[:3000]), f"damage {i}:\n{r}")

    member = fx.member
    bad(b"", "empty, not a gzip file", "nothing")
    bad(b"not gzip", "not in gzip format (it starts 6e 6f, not 1f 8b)", "not gzip")
    bad(small[:5], "the file ends inside the gzip header", "half a header")
    bad(small[:2] + b"\x07" + small[3:], "compression method 7, not 8 (deflate)", "method 7")
    bad(small[:3] + b"\x20" + small[4:], "flag bits 0x20 set, which RFC 1952 reserves", "a reserved flag")
    bad(small[:-8] + bytes([small[-8] ^ 1]) + small[-7:], "the data's CRC-32 is", "a wrong CRC-32")
    bad(small[:-4] + b"\x00\x00\x00\x00", "the data is 3000 bytes (modulo 2^32), but the trailer says 0", "a wrong size")
    bad(small[:-3], "the file ends before the trailer", "half a trailer")
    bad(small + b"junk", "4 bytes after the end of the gzip data, not another member", "junk after it")
    h = member(raw, text, hcrc=True)
    bad(h[:10] + bytes([h[10] ^ 1]) + h[11:], "the header's CRC-16 is", "a wrong header CRC")
    bad(member(raw, text, name=b"no end")[:16], "the file ends inside the gzip header", "a name with no end")

    fixed = fx.fixed_codes()
    lit, dist = fixed["lit"], fixed["dist"]

    def block(*items, final=1, btype=1):
        b = fx.Bits().put(final, 1).put(btype, 2)
        for it in items:
            if it[0] == "lit":
                b.code(*lit[it[1]])
            elif it[0] == "dist":
                b.code(*dist[it[1]])
            else:
                b.put(it[1], it[2])
        return b

    ok = block(("lit", ord("a")), ("lit", ord("b")), ("lit", 260), ("dist", 1), ("lit", 256)).bytes()
    same(b"abababab", member(ok, b"abababab"), "a match that overlaps what it copies (2 back, 6 long)")
    bad(member(block(("lit", ord("a")), ("lit", 257), ("dist", 1), ("lit", 256)).bytes(), b"aaaa"),
        "a match 2 bytes back, but only 1 bytes have been written", "a distance before the start")
    bad(member(block(("lit", 257), ("dist", 0), ("lit", 256)).bytes(), b"aaa"),
        "a match 1 bytes back, but only 0 bytes have been written", "a match before anything")
    bad(member(block(("lit", 286)).bytes(), b""), "length code 286, which DEFLATE does not use", "length 286")
    bad(member(block(("lit", 97), ("lit", 257), ("dist", 30)).bytes(), b""),
        "distance code 30, which DEFLATE does not use", "distance 30")
    bad(member(block(btype=3).bytes(), b""), "a block of type 3, which DEFLATE reserves", "block type 3")
    bad(member(block(("lit", 97), ("lit", 256), final=0).bytes(), b"a")[:-8], "the data ends",
        "no last block")
    stored = fx.Bits().put(1, 1).put(0, 2).align()
    bad(member(stored.put(5, 16).put(0, 16).bytes() + b"hello", b"hello"),
        "a stored block's length 5 and its check 0 do not match", "NLEN wrong")
    stored = fx.Bits().put(1, 1).put(0, 2).align()
    bad(member(stored.put(100, 16).put(100 ^ 0xFFFF, 16).bytes() + b"hello", b"hello"),
        "a stored block of 100 bytes, but the data ends after", "LEN past the end")

    def dyn(nlit, ndist, clens, *items):
        b = fx.Bits().put(1, 1).put(2, 2).put(nlit - 257, 5).put(ndist - 1, 5).put(len(clens) - 4, 4)
        for n in clens:
            b.put(n, 3)
        order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
        lengths = [0] * 19
        for i, n in enumerate(clens):
            lengths[order[i]] = n
        codes = fx.canonical(lengths)
        for sym, extra, k in items:
            b.code(*codes[sym])
            b.put(extra, k)
        return member(b.bytes(), b"")

    five = [5] * 19                                    # every code-length symbol a 5-bit code
    bad(dyn(287, 1, five), "a block with 287 literal/length codes; DEFLATE has 286", "HLIT 287")
    bad(dyn(257, 31, five), "a block with 31 distance codes; DEFLATE has 30", "HDIST 31")
    bad(dyn(257, 1, [1] * 19), "the code-length code has more codes than its lengths allow", "over-subscribed")
    bad(dyn(257, 1, five, (16, 0, 2)), "a repeat of the code length before, with none before it", "16 first")
    bad(dyn(257, 1, five, (18, 127, 7), (18, 127, 7), (18, 127, 7)),
        "code lengths that run past the 258 the block says", "zeros past the end")
    bad(dyn(257, 1, five, (18, 127, 7), (18, 108, 7)), "a block with no code for its end (256)", "no end code")
    bad(dyn(257, 1, five, (18, 127, 7), (18, 105, 7), (1, 0, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0)),
        "the literal/length code has more codes than its lengths allow", "an over-subscribed literal code")
    # 255 zeros, then 256 and one length symbol of 2 bits: an incomplete code, and bits that are no code
    toks = (18, 127, 7), (18, 106, 7), (2, 0, 0), (2, 0, 0), (0, 0, 0)
    b = dyn(258, 1, five, *toks)
    bad(b[:-8] + b"\xff" + b[-7:], "bits that are no literal/length code", "an incomplete code read past its codes")
