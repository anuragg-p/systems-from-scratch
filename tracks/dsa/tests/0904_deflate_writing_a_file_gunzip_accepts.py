"""09.04 Deflate: writing a file gunzip accepts

What gzip writes, the system's gzip -t accepts and the system's gunzip, ours and Python's zlib all
read back to the same bytes: text, binary, noise, long runs, nothing, one byte, every level, and
every block forced stored, fixed or dynamic. Each block takes the smallest of the three forms: the
book in dynamic blocks, noise stored. The book comes out within 5% of the system's gzip -6 and
-9. A text whose byte counts grow as the Fibonacci numbers needs codes longer than 15 bits; its
codes are limited to 15 (the tree built again from flattened counts) and it still reads back.
The example traces in lib/deflate.h and lib/inflate.h are what the programs print. gzip FILE makes
FILE.gz and removes FILE, as the system's does.
"""

import os
import random
import re


def test(t):
    T = t.track
    fx = T.fixtures("gzip")
    book = T.data(t, "book.txt")
    with open(book, "rb") as f:
        text = f.read()
    rng = random.Random(1951)
    files = {
        "the book": book,
        "lines": T.gen(t, "lines", 20000),
        "noise": T.write(t, "noise.bin", bytes(rng.randrange(256) for _ in range(150000))),
        "zeros": T.write(t, "zeros.bin", bytes(1000000)),
        "nothing": T.write(t, "empty.txt", b""),
        "one byte": T.write(t, "one.txt", b"x"),
        "every byte": T.write(t, "bytes.bin", bytes(range(256)) * 300),
        "two letters": T.write(t, "ab.txt", bytes(rng.choice(b"ab") for _ in range(100000))),
    }
    for what, path in files.items():
        fx.roundtrip(t, path)

    # each block the cheapest of the three forms; forced, each form on its own still reads back
    s = T.stats(fx.roundtrip(t, book).err)["deflate"]
    t.check(s["dynamic blocks"] > 0 and s["stored blocks"] == 0, f"the book: dynamic blocks: {s}")
    s = T.stats(fx.roundtrip(t, files["noise"]).err)["deflate"]
    t.check(s["stored blocks"] > 0 and s["dynamic blocks"] == 0, f"noise: stored blocks: {s}")
    sizes = {}
    for form in ("stored", "fixed", "dynamic", "best"):
        for what in ("the book", "noise", "nothing", "zeros"):
            r = fx.roundtrip(t, files[what], [f"--blocks={form}"])
            sizes[form, what] = len(r.raw)
            s = T.stats(r.err)["deflate"]
            if form != "best":
                others = sum(v for k, v in s.items() if k.endswith("blocks") and not k.startswith(form))
                t.check(s[f"{form} blocks"] > 0 and others == 0, f"--blocks={form} on {what}: {s}")
    for what in ("the book", "noise", "nothing", "zeros"):
        t.check(sizes["best", what] <= min(sizes[f, what] for f in ("stored", "fixed", "dynamic")),
                f"{what}: best is the smallest: {[(f, sizes[f, what]) for f in ('stored', 'fixed', 'dynamic', 'best')]}")

    # every level, and the slow scan and no LZ77 at all, on part of the book
    part = T.write(t, "part.txt", text[:20000])
    for level in range(1, 10):
        fx.roundtrip(t, part, [f"-{level}"])
    fx.roundtrip(t, part, ["--algo=scan"])
    fx.roundtrip(t, part, ["--algo=none"])

    # sizes: the same range as the system's gzip
    for level in (6, 9):
        ours = len(T.run(t, "gzip", [f"-{level}", "-c", book]).raw)
        theirs = len(T.system(t, ["gzip", f"-{level}", "-c", book]).raw)
        t.check(ours < 1.05 * theirs, f"gzip -{level} on the book: {ours} bytes, the system's {theirs}")

    # Fibonacci counts, 1, 2, 3, 5, ... for 18 byte values: a tree 17 deep for the letters alone, and
    # with the end of block's 1 as well, 18 deep, too deep for DEFLATE; the code is cut to 15 bits at
    # most, and still reads back
    fib = [1, 2]
    while len(fib) < 18:
        fib.append(fib[-1] + fib[-2])
    data = bytearray()
    for i, n in enumerate(fib):
        data += bytes([65 + i]) * n
    rng.shuffle(data)
    path = T.write(t, "fib.txt", bytes(data))
    rows, _ = fx.huffman_table(T.run(t, "gzip", ["--huffman", path]).out)
    t.check(max(v[1] for v in rows.values()) > 15, "without a limit its Huffman code is longer than 15 bits")
    r = fx.roundtrip(t, path, ["--algo=none", "--blocks=dynamic"])
    s = T.stats(r.err)
    t.check(s["huffman"]["rebuilds"] > 0 and s["deflate"]["dynamic blocks"] == 1, f"built again, flatter: {s}")
    back = T.run(t, "gunzip", ["-c"], input=r.raw, env={"DS_TRACE": "1"})
    longest = [int(n) for n in re.findall(r"literal/length codes \(longest (\d+) bits\)", back.err)]
    t.check(len(longest) == 1 and longest[0] <= 15, f"the literal/length code read back: {longest}")

    # the example traces in lib/deflate.h's and lib/inflate.h's comments are what the programs
    # print for abracadabra (a fixed block by choice; a dynamic one when forced)
    abra = T.write(t, "abra.txt", b"abracadabra")
    heads = {}
    for name in ("deflate.h", "inflate.h"):
        with open(os.path.join(T._root(t), "lib", name)) as f:
            heads[name] = f.read()
    said = [l for l in T.run(t, "gzip", ["-c", abra], env={"DS_TRACE": "1"}).err.splitlines()
            if l.startswith("trace: deflate: ")]
    t.check(len(said) == 1 and f" *   {said[0]}\n" in heads["deflate.h"],
            f"lib/deflate.h's example trace is not what gzip prints for abracadabra: {said}")
    dyn = T.run(t, "gzip", ["-c", "--blocks=dynamic", abra]).raw
    said = [l for l in T.run(t, "gunzip", ["-c"], input=dyn, env={"DS_TRACE": "1"}).err.splitlines()
            if l.startswith(("trace: inflate: block", "trace: inflate: end")) or " match " in l]
    t.check(len(said) == 3 and all(f" *   {l}\n" in heads["inflate.h"] for l in said),
            f"lib/inflate.h's example trace is not what gunzip prints for a dynamic abracadabra: {said}")

    # the files: x becomes x.gz, x goes; -k keeps it; x.gz there already, or a .gz, is an error
    path = T.write(t, "story.txt", text[:5000])
    T.run(t, "gzip", [path])
    t.check(os.path.exists(path + ".gz") and not os.path.exists(path), "gzip x: x.gz, and no x")
    T.run(t, "gunzip", [path + ".gz"])
    t.check(open(path, "rb").read() == text[:5000], "and gunzip x.gz gives x back")
    T.run(t, "gzip", ["-k", path])
    t.check(os.path.exists(path) and os.path.exists(path + ".gz"), "-k keeps x")
    r = T.run(t, "gzip", [path], check=False)
    t.check(r.rc == 2 and "already exists" in r.err, f"gzip over an x.gz that is there:\n{r}")
    r = T.run(t, "gzip", ["-f", path + ".gz"], check=False)
    t.check(r.rc == 2 and "already ends in .gz" in r.err, f"gzip on a .gz:\n{r}")
    T.run(t, "gzip", ["-f", path])
    gz = open(path + ".gz", "rb").read()
    t.check(gz[3] & 8 and b"story.txt\x00" in gz[:30], "the header keeps the file's name")
    r = T.run(t, "gzip", ["--blocks=huge"], check=False)
    t.check(r.rc == 2 and "no --blocks 'huge'" in r.err, f"--blocks=huge:\n{r}")
    r = T.run(t, "gzip", ["-x"], check=False)
    t.check(r.rc == 2 and "usage: gzip" in r.err, f"gzip -x:\n{r}")
