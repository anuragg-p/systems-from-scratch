"""09.01 Huffman codes: a greedy tree

gzip --huffman prints the Huffman code of a file's bytes. "abracadabra" takes 23 bits, and its tree
is built by joining the two rarest each time. On the book the code is canonical, complete and prefix
free, and its total is the fewest bits any prefix code can take (the same as a Huffman tree built
here independently, with Python's heapq); building it takes one join per byte value but one, each
two pops and a push on the heap.
"""

from fractions import Fraction


def test(t):
    T = t.track
    fx = T.fixtures("gzip")

    r = T.run(t, "gzip", ["--huffman"], input="abracadabra", env={"DS_TRACE": "1", "DS_STATS": "1"})
    T.same(t, r.out, fx.ABRA, "gzip --huffman on abracadabra")
    joins = [l for l in r.err.splitlines() if l.startswith("trace: huffman: ")]
    t.check(joins == ["trace: huffman: tree of 5 symbols",
                      "trace: huffman: join 'c' 1 + 'd' 1 = n1 2",
                      "trace: huffman: join 'b' 2 + 'r' 2 = n2 4",
                      "trace: huffman: join n1 2 + n2 4 = n3 6",
                      "trace: huffman: join 'a' 5 + n3 6 = n4 11"], f"the joins, the two rarest each time:\n{r.err}")

    # the book: every byte value's count, a canonical code, and the fewest bits there are
    book = T.data(t, "book.txt")
    with open(book, "rb") as f:
        data = f.read()
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    r = T.run(t, "gzip", ["--huffman", book], env={"DS_STATS": "1"})
    rows, (total, different, plain, bits, nbytes) = fx.huffman_table(r.out)
    used = [b for b in range(256) if counts[b]]
    t.check(sorted(rows) == used, f"one row for each byte value in the book: {sorted(rows)}")
    for b, (count, length, code) in rows.items():
        t.check(count == counts[b] and len(code) == length, f"byte {b}: {rows[b]}, the book has {counts[b]}")
    lengths = [rows[b][1] if b in rows else 0 for b in range(256)]
    want = fx.canonical(lengths)
    for b in used:
        t.check(rows[b][2] == format(want[b][0], f"0{want[b][1]}b"),
                f"byte {b}: code {rows[b][2]}, the canonical code for these lengths is {want[b]}")
    t.check(sum(Fraction(1, 2 ** lengths[b]) for b in used) == 1, "the code is complete: no pattern of bits is spare")
    codes = sorted(rows[b][2] for b in used)
    t.check(all(not codes[i + 1].startswith(codes[i]) for i in range(len(codes) - 1)), "no code starts another")
    best = fx.huffman_cost(counts)
    t.check(bits == best == sum(counts[b] * lengths[b] for b in used),
            f"the book in {bits} bits; the fewest a prefix code can take is {best}")
    t.check(total == len(data) and different == len(used) and plain == 8 * len(data) and nbytes == (bits + 7) // 8,
            f"the summary: {r.out.splitlines()[-1]}")
    t.check(bits < 0.6 * plain, f"the book's bytes in a Huffman code take under 60% of their 8 bits: {bits}")
    s = T.stats(r.err)
    t.check(s["huffman"]["trees"] == 1 and s["huffman"]["joins"] == len(used) - 1, f"one join per symbol but one: {s}")
    t.check(s["heap"]["pushes"] == 2 * len(used) - 1 and s["heap"]["pops"] == 2 * (len(used) - 1),
            f"each join two pops and a push: {s}")

    # one byte value alone still gets a 1-bit code; nothing at all, no code
    r = T.run(t, "gzip", ["--huffman"], input="aaaa")
    t.check(r.out.splitlines()[1:] == ["'a'           4     1  0",
                                       "4 bytes, 1 different: 32 bits as bytes, 4 bits in these codes (1 bytes)"],
            f"gzip --huffman on aaaa:\n{r.out}")
    r = T.run(t, "gzip", ["--huffman"], input="")
    t.check(r.out.splitlines()[1:] == ["0 bytes, 0 different: 0 bits as bytes, 0 bits in these codes (0 bytes)"],
            f"gzip --huffman on nothing:\n{r.out}")
    # every byte value, binary included, shown as C writes it
    r = T.run(t, "gzip", ["--huffman"], input=bytes(range(256)) * 2 + b"\n\t'\\")
    rows, summary = fx.huffman_table(r.out)
    t.check(len(rows) == 256 and rows[10][0] == 3 and rows[0][0] == 2 and rows[39][0] == 3 and rows[92][0] == 3,
            f"all 256 byte values:\n{r.out[:600]}")
    r = T.run(t, "gzip", ["--huffman", "/no/such/file"], check=False)
    t.check(r.rc == 2 and r.err.startswith("gzip: /no/such/file: "), f"a missing file:\n{r}")
