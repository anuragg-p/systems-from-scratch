"""10.01 Objects: a hash is a name

An object's name is the SHA-1 of "type size", a NUL and its bytes: ours is Python's hashlib's on
every length across the block boundaries, and the real git's on the book, nothing, and binary
bytes. hash-object -w stores it once, compressed as a zlib stream (78 01 ... Adler-32) that
Python's zlib reads, at .git/objects/xx/...; the real git reads it and fsck --strict passes; the
same bytes again write nothing. Ours reads what the real git wrote at every compression level,
and the start of a name finds it. A damaged object (cut short, a bit flipped, a wrong header or
size, bytes that are another object's, junk after it) is an ordinary error, as is a packed or a
SHA-256 repository. This git never looks above the directory it is given, opens no .git file,
writes to no repository its own init did not make, and makes no repository twice.
"""

import os
import random
import zlib


def test(t):
    T = t.track
    fx = T.fixtures("git")
    rng = random.Random(1001)

    # the name: SHA-1 of the header and the bytes, on every length across the 64-byte blocks
    repo = fx.new_repo(t, "objects")
    fx.ours(t, repo, ["init", "-q"])
    datas = [bytes(rng.randrange(256) for _ in range(n)) for n in range(0, 200)] + [b"a" * 1000000]
    paths = [fx.write(repo, f"f{i}", d) for i, d in enumerate(datas)]
    r = fx.ours(t, repo, ["hash-object"] + [f"f{i}" for i in range(len(datas))], env={"DS_STATS": "1"})
    want = [fx.object_name(b"blob", d) for d in datas]
    t.check(r.out.split() == want, "hash-object: the names are not SHA-1 of the header and the bytes")
    s = fx.stats(r)
    total = sum(len(b"blob %d\x00" % len(d)) + len(d) for d in datas)
    blocks = sum((len(b"blob %d\x00" % len(d)) + len(d) + 8) // 64 + 1 for d in datas)
    t.check(s["sha1"] == {"blocks": blocks, "bytes": total},
            f"sha1: {s['sha1']}, but {len(datas)} objects of {total} bytes are {blocks} blocks with their padding")
    t.check(s["git"]["objects hashed"] == len(datas) and s["git"]["written"] == 0, f"hash-object without -w: {s['git']}")

    book = T.data(t, "book.txt")
    with open(book, "rb") as f:
        text = f.read()
    for name, data in (("book.txt", text), ("empty", b""), ("bytes", bytes(range(256)) * 4), ("nul", b"a\0b\n")):
        fx.write(repo, name, data)
        ours = fx.ours(t, repo, ["hash-object", name]).out
        t.check(ours == fx.real(t, repo, ["hash-object", name]).out, f"hash-object {name}: not the real git's name")

    # -w: stored once, as zlib, where the name says; the real git reads it and checks the repository
    r = fx.ours(t, repo, ["hash-object", "-w", "book.txt", "empty", "nul"], env={"DS_STATS": "1"})
    names = r.out.split()
    s = fx.stats(r)
    t.check(s["git"]["written"] == 3 and s["zlib"]["packed"] == 3, f"hash-object -w: {s['git']} {s['zlib']}")
    for n, data in zip(names, (text, b"", b"a\0b\n")):
        p = os.path.join(repo, ".git", "objects", n[:2], n[2:])
        with open(p, "rb") as f:
            z = f.read()
        t.check(z[:2] == b"\x78\x01", f"object {n}: a zlib header 78 01, not {z[:2].hex()}")
        t.check(zlib.decompress(z) == b"blob %d\x00" % len(data) + data, f"object {n}: not the header and the bytes")
        t.check(fx.real(t, repo, ["cat-file", "-p", n]).raw == data, f"the real git does not read {n} back")
        t.check(fx.ours(t, repo, ["cat-file", "-p", n]).raw == data, f"cat-file -p {n}")
    fx.real(t, repo, ["fsck", "--strict"])
    t.check(sorted(fx.objects(repo)) == sorted(names), f"objects: {fx.objects(repo)}")
    mtime = os.stat(os.path.join(repo, ".git", "objects", names[0][:2], names[0][2:])).st_mtime_ns
    s = fx.stats(fx.ours(t, repo, ["hash-object", "-w", "book.txt", "book.txt"], env={"DS_STATS": "1"}))
    t.check(s["git"]["written"] == 0 and s["git"]["already there"] == 2, f"the same bytes again: {s['git']}")
    t.check(os.stat(os.path.join(repo, ".git", "objects", names[0][:2], names[0][2:])).st_mtime_ns == mtime,
            "the object was written again")
    t.check(fx.ours(t, repo, ["cat-file", "-t", names[0]]).out == "blob\n", "cat-file -t")
    t.check(fx.ours(t, repo, ["cat-file", "-s", names[0]]).out == f"{len(text)}\n", "cat-file -s")
    t.check(fx.ours(t, repo, ["cat-file", "blob", names[0][:4]]).raw == text, "cat-file blob, by 4 digits")
    t.check(fx.ours(t, repo, ["cat-file", "-e", names[0]], check=False).rc == 0, "cat-file -e on an object there")
    r = fx.ours(t, repo, ["cat-file", "-e", "0" * 40], check=False)
    t.check(r.rc == 1 and r.out == r.err == "", f"cat-file -e on one not there:\n{r}")

    # the start of a name: unique, or an error naming how many share it
    many = [fx.write(repo, f"m{i}", b"%d\n" % i) for i in range(600)]
    made = fx.ours(t, repo, ["hash-object", "-w"] + [f"m{i}" for i in range(600)]).out.split()
    starts = {}
    for n in made:
        starts.setdefault(n[:4], []).append(n)
    shared = [k for k, v in starts.items() if len(v) > 1]
    t.check(shared, "600 objects and no two names start alike: the test needs more")
    r = fx.ours(t, repo, ["cat-file", "-p", shared[0]], check=False)
    t.check(r.rc == 2 and f"git: {shared[0]} is the start of 2 objects' names" in r.err, f"an ambiguous start:\n{r}")
    longer = starts[shared[0]][0][:12]
    t.check(fx.ours(t, repo, ["cat-file", "-t", longer]).out == "blob\n", "12 digits of a name")

    # what the real git wrote, at every level of compression, read by ours
    theirs = fx.new_repo(t, "theirs")
    fx.real(t, theirs, ["init", "-q"])
    fx.write(theirs, "book.txt", text)
    for level in ("0", "1", "6", "9"):
        n = fx.real(t, theirs, ["-c", f"core.looseCompression={level}", "hash-object", "-w", "--stdin"],
                    input=text + level.encode()).out.strip()
        t.check(fx.ours(t, theirs, ["cat-file", "-p", n]).raw == text + level.encode(), f"zlib level {level}")
    fx.real(t, theirs, ["add", "book.txt"])
    fx.real(t, theirs, ["commit", "-q", "-m", "the book"])
    for what in ("HEAD", "HEAD^{tree}"):
        n = fx.real(t, theirs, ["rev-parse", what]).out.strip()
        for flag in ("-t", "-s"):
            t.check(fx.ours(t, theirs, ["cat-file", flag, n]).out == fx.real(t, theirs, ["cat-file", flag, n]).out,
                    f"cat-file {flag} {what}")
    n = fx.real(t, theirs, ["rev-parse", "HEAD"]).out.strip()
    t.check(fx.ours(t, theirs, ["cat-file", "-p", n]).out == fx.real(t, theirs, ["cat-file", "-p", n]).out,
            "cat-file -p of the real git's commit")

    # damaged objects: an ordinary error every time
    good = fx.ours(t, repo, ["hash-object", "-w", "nul"]).out.strip()
    path = os.path.join(repo, ".git", "objects", good[:2], good[2:])
    with open(path, "rb") as f:
        z = f.read()
    raw = zlib.decompress(z)
    other = zlib.compress(b"blob 4\x00a\0c\n", 1)
    variants = [("cut at %d" % i, z[:i]) for i in range(len(z))]
    variants += [("bit %d flipped" % i, z[:i // 8] + bytes([z[i // 8] ^ (1 << (i % 8))]) + z[i // 8 + 1:])
                 for i in range(len(z) * 8)]
    variants += [("an unknown type", zlib.compress(b"blub 4\x00a\0b\n")),
                 ("a size that is wrong", zlib.compress(b"blob 9\x00a\0b\n")),
                 ("no size", zlib.compress(b"blob \x00a\0b\n")),
                 ("no NUL", zlib.compress(b"blob 4")),
                 ("nothing in it", zlib.compress(b"")),
                 ("another object's bytes", other),
                 ("junk after it", z + b"junk"),
                 ("a preset dictionary", bytes([0x78, 0xbb]) + z[2:]),
                 ("not zlib", b"blob 4\x00a\0b\n"),
                 ("a long size", zlib.compress(b"blob 99999999999999999999999999\x00a"))]
    os.chmod(path, 0o644)
    bad = 0
    for what, data in variants:
        with open(path, "wb") as f:
            f.write(data)
        r = fx.ours(t, repo, ["cat-file", "-p", good], check=False)
        if r.rc == 0 and r.raw == raw[raw.index(b"\0") + 1:]:
            continue                         # a flip zlib cannot see and the name does not care about
        t.check(r.rc == 2 and r.err.startswith(f"git: object {good} is damaged: "),
                f"a damaged object ({what}): not an ordinary error:\n{r}")
        bad += 1
    t.check(bad > len(variants) * 0.95, f"only {bad} of {len(variants)} damaged objects were noticed")
    os.remove(path)
    r = fx.ours(t, repo, ["cat-file", "-p", good], check=False)
    t.check(r.rc == 2 and r.err == f"git: object {good} is not in the repository\n", f"a missing object:\n{r}")

    # repositories this git does not read: packed, or named by SHA-256
    packed = fx.new_repo(t, "packed")
    fx.real(t, packed, ["init", "-q"])
    fx.write(packed, "a.txt", "a\n")
    fx.real(t, packed, ["add", "a.txt"])
    fx.real(t, packed, ["commit", "-q", "-m", "a"])
    fx.real(t, packed, ["repack", "-a", "-d", "-q"])
    r = fx.ours(t, packed, ["cat-file", "-t", "78981922613b2afb6025042ff6bd878ac1994e85"], check=False)
    t.check(r.rc == 2 and "this repository has packed objects" in r.err and "reads only loose objects" in r.err,
            f"a packed repository:\n{r}")
    sha256 = fx.new_repo(t, "sha256")
    fx.real(t, sha256, ["init", "-q", "--object-format=sha256"])
    r = fx.ours(t, sha256, ["cat-file", "-t", "78981922613b2afb6025042ff6bd878ac1994e85"], check=False)
    t.check(r.rc == 2 and "names its objects with sha256" in r.err, f"a SHA-256 repository:\n{r}")

    # never above the directory given, no .git file, no writing to a repository it did not make
    inside = os.path.join(repo, "sub")
    os.makedirs(inside)
    r = fx.ours(t, inside, ["cat-file", "-t", good], check=False)
    t.check(r.rc == 2 and "there is no .git here" in r.err and "never in the ones above" in r.err,
            f"run in a directory inside a repository:\n{r}")
    worktree = fx.new_repo(t, "worktree")
    fx.write(worktree, ".git", "gitdir: " + os.path.join(repo, ".git") + "\n")
    r = fx.ours(t, worktree, ["cat-file", "-t", names[0]], check=False)
    t.check(r.rc == 2 and ".git is a file" in r.err, f"a .git file:\n{r}")
    before = fx.objects(theirs)
    fx.write(theirs, "new.txt", "new\n")
    r = fx.ours(t, theirs, ["hash-object", "-w", "new.txt"], check=False)
    t.check(r.rc == 2 and "changes only repositories its own init made" in r.err, f"writing to the real git's:\n{r}")
    t.check(fx.objects(theirs) == before, "an object was written to a repository ours did not make")
    r = fx.ours(t, theirs, ["init"], check=False)
    t.check(r.rc == 2 and "is there already" in r.err, f"init where there is a repository:\n{r}")

    # DS_TRACE: each object, written or there already
    r = fx.ours(t, repo, ["hash-object", "-w", "--stdin"], input="hello\n", env={"DS_TRACE": "1"})
    want = "trace: object: blob of 6 bytes is ce/013625030ba8dba906f756967f9e9ca394464a: written, 21 bytes compressed\n"
    t.check(r.err == want, f"the trace:\n{r.err}")
    r = fx.ours(t, repo, ["hash-object", "-w", "--stdin"], input="hello\n", env={"DS_TRACE": "1"})
    t.check(r.err == "trace: object: blob of 6 bytes is ce/013625030ba8dba906f756967f9e9ca394464a: already there\n",
            f"the trace:\n{r.err}")
