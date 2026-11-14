"""10.02 Trees and the index: a directory as a hash

add puts each file in the index, a version 2 file in path order that the real git reads as ours
does (ls-files -s, ls-files, status); write-tree makes the same trees as the real git, in git's
order ("b c" before the directory "b", "a.txt" before "a"), each name standing for the whole
directory under it. Ours reads the real git's index, cached trees and optional extensions too.
After a change deep in the tree, the index forgets the cached trees of that file's directories
and no others: write-tree builds those again (one per level, as many as the real git's renamed
trees) and takes the rest from the cache, where --algo=all builds every tree; the top tree is the
same either way, and the real git's write-tree on our index agrees. Files gone from the work tree
leave the index. A damaged index, a tree with a mode git does not write or out of order, and a
tree cut short are ordinary errors.
"""

import hashlib
import os
import struct
import zlib


def tree_paths(fx, t, repo, rev):
    """{path: name} of every tree under rev (the top as ""), from the real git."""
    out = {"": fx.real(t, repo, ["rev-parse", rev + "^{tree}"]).out.strip()}
    for line in fx.real(t, repo, ["ls-tree", "-r", "-t", rev]).out.splitlines():
        meta, path = line.split("\t", 1)
        mode, kind, name = meta.split()
        if kind == "tree":
            out[path] = name
    return out


def put_object(repo, kind, data):
    raw = b"%s %d\x00" % (kind, len(data)) + data
    name = hashlib.sha1(raw).hexdigest()
    d = os.path.join(repo, ".git", "objects", name[:2])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name[2:]), "wb") as f:
        f.write(zlib.compress(raw))
    return name


def test(t):
    T = t.track
    fx = T.fixtures("git")
    files = {"hello.txt": "hello\n", "b c": "space\n", "b/c": "c\n", "a.txt": "x\n", "a/x": "y\n", "a0": "z\n",
             "a-b": "w\n", "run.sh": "#!/bin/sh\n", "empty": "", "d/e/f/g.txt": "deep\n", "d/e/h.txt": "h\n",
             "d/k.txt": "k\n", "t\tab": "tab\n", "caf\u00e9": "accent\n", "q\"uote": "q\n"}

    def fill(repo):
        for p, data in files.items():
            fx.write(repo, p, data)
        os.chmod(os.path.join(repo, "run.sh"), 0o755)
        os.symlink("hello.txt", os.path.join(repo, "link"))

    ours_repo, theirs = fx.new_repo(t, "ours"), fx.new_repo(t, "theirs")
    fx.ours(t, ours_repo, ["init", "-q"])
    fx.real(t, theirs, ["init", "-q"])
    fill(ours_repo)
    fill(theirs)
    r = fx.ours(t, ours_repo, ["add", "."], env={"DS_STATS": "1"})
    s = fx.stats(r)
    t.check(s["index"]["files hashed"] == len(files) + 1 and s["sort"]["comparisons"] > 0,
            f"add: every file hashed, and the paths sorted (02.02): {s}")
    fx.real(t, theirs, ["add", "."])

    # the index: the real git reads ours as its own
    for args in (["ls-files", "-s"], ["ls-files"]):
        mine = fx.ours(t, ours_repo, args).out
        t.check(mine == fx.real(t, ours_repo, args).out, f"{' '.join(args)}: the real git reads our index otherwise")
        t.check(mine == fx.real(t, theirs, args).out, f"{' '.join(args)}: not what the real git's add makes")
        t.check(mine == fx.ours(t, theirs, args).out, f"{' '.join(args)}: ours reads the real git's index otherwise")
    version, entries, tree = fx.parse_index(ours_repo)
    paths = [p.encode("utf-8", "surrogateescape") for _, _, p in entries]
    t.check(version == 2 and paths == sorted(paths) and tree is None, f"the index: version {version}, {paths}")
    t.check(fx.real(t, ours_repo, ["status", "--porcelain"]).out == fx.real(t, theirs, ["status", "--porcelain"]).out,
            "status before the first commit")

    # trees: the same as the real git's, in git's order
    r = fx.ours(t, ours_repo, ["write-tree"], env={"DS_STATS": "1"})
    top = r.out.strip()
    t.check(top == fx.real(t, theirs, ["write-tree"]).out.strip(), "write-tree: not the real git's tree")
    t.check(top == fx.real(t, ours_repo, ["write-tree"]).out.strip(), "the real git's write-tree on our index")
    s = fx.stats(r)
    t.check(s["write-tree"] == {"trees built": 6, "from the cache": 0}, f"write-tree: {s['write-tree']}")
    listing = fx.ours(t, ours_repo, ["cat-file", "-p", top]).out
    t.check(listing == fx.real(t, theirs, ["cat-file", "-p", top]).out, f"cat-file -p of a tree:\n{listing}")
    names = [l.split("\t", 1)[1] for l in listing.splitlines()]
    t.check(names.index("b c") < names.index("b") and names.index("a.txt") < names.index("a") < names.index("a0"),
            f"git's order: {names}")
    for args in (["ls-tree", "-r", top], ["ls-tree", "-r", "-t", top], ["ls-tree", top]):
        t.check(fx.ours(t, ours_repo, args).out == fx.real(t, theirs, args).out, f"{' '.join(args)}")
    fx.real(t, ours_repo, ["fsck", "--strict"])
    version, entries, tree = fx.parse_index(ours_repo)
    t.check(tree is not None and all(c >= 0 for _, c, _, _ in tree) and tree[0][1] == len(entries),
            f"the cached trees after write-tree: {tree}")

    # the real git's index, with its cached trees and the untracked cache (an optional extension)
    fx.real(t, theirs, ["commit", "-q", "-m", "all of it"])
    fx.real(t, theirs, ["-c", "core.untrackedCache=true", "update-index", "--untracked-cache"])
    fx.real(t, theirs, ["-c", "core.untrackedCache=true", "status", "--porcelain"])
    with open(os.path.join(theirs, ".git", "index"), "rb") as f:
        idx = f.read()
    t.check(b"TREE" in idx and b"UNTR" in idx, "the real git's index has no TREE and UNTR extensions to read")
    t.check(fx.ours(t, theirs, ["ls-files", "-s"]).out == fx.real(t, theirs, ["ls-files", "-s"]).out,
            "ours on the real git's index with extensions")

    # a change deep down: the trees above it, and no others, are built again
    fx.ours(t, ours_repo, ["commit", "-q", "-m", "all of it"])
    before = tree_paths(fx, t, ours_repo, "HEAD")
    fx.write(ours_repo, "d/e/f/g.txt", "deeper\n")
    r = fx.ours(t, ours_repo, ["add", "d/e/f/g.txt"], env={"DS_TRACE": "1"})
    gone = [l for l in r.err.splitlines() if "the cached tree" in l]
    t.check(gone == ["trace: index: d/e/f/g.txt changed: the cached tree of / is gone",
                     "trace: index: d/e/f/g.txt changed: the cached tree of d/ is gone",
                     "trace: index: d/e/f/g.txt changed: the cached tree of d/e/ is gone",
                     "trace: index: d/e/f/g.txt changed: the cached tree of d/e/f/ is gone"], f"add's trace:\n{r.err}")
    _, _, tree = fx.parse_index(ours_repo)
    invalid = sorted(p for p, c, _, _ in tree if c < 0)
    t.check(invalid == ["", "d/", "d/e/", "d/e/f/"], f"the cached trees forgotten: {invalid}")
    index = os.path.join(ours_repo, ".git", "index")
    with open(index, "rb") as f:
        kept = f.read()
    theirs_tree = fx.real(t, ours_repo, ["write-tree"]).out.strip()      # it rewrites the index: put ours back
    with open(index, "wb") as f:
        f.write(kept)
    r = fx.ours(t, ours_repo, ["commit", "-q", "-m", "deeper"], env={"DS_STATS": "1", "DS_TRACE": "1"})
    s = fx.stats(r)
    t.check(s["write-tree"] == {"trees built": 4, "from the cache": 2}, f"write-tree after one deep change: {s}")
    t.check(fx.real(t, ours_repo, ["rev-parse", "HEAD^{tree}"]).out.strip() == theirs_tree,
            "the real git's write-tree, on our index with the cached trees forgotten, makes another tree")
    t.check("trace: tree: d/e/f/ (1 entry, 1 file under it): " in r.err and
            "trace: tree: a/ (1 file under it): " in r.err, f"write-tree's trace:\n{r.err}")
    after = tree_paths(fx, t, ours_repo, "HEAD")
    renamed = sorted(p for p in after if before.get(p) != after[p])
    t.check(renamed == ["", "d", "d/e", "d/e/f"], f"the trees renamed by one deep change: {renamed}")
    t.check(fx.real(t, ours_repo, ["status", "--porcelain"]).out == "", "status after the commit")
    s = fx.stats(fx.ours(t, ours_repo, ["write-tree", "--algo=all"], env={"DS_STATS": "1"}))
    t.check(s["write-tree"] == {"trees built": 6, "from the cache": 0}, f"write-tree --algo=all: {s}")

    # a big tree: one change costs its depth, not the size of the tree
    big, names = fx.gen_repo(t, "tree", 3000)
    fx.ours(t, big, ["add", "."])
    s = fx.stats(fx.ours(t, big, ["write-tree"], env={"DS_STATS": "1"}))
    dirs = len({p.rsplit("/", k)[0] for p in fx.real(t, big, ["ls-files"]).out.splitlines()
                for k in range(1, p.count("/") + 1)} | {""})
    t.check(s["write-tree"]["trees built"] == dirs and s["git"]["written"] == 0,
            f"3000 files in {dirs} directories: {s}")
    fx.write(big, names["changed"], "changed again\n")
    fx.ours(t, big, ["add", "."])
    s = fx.stats(fx.ours(t, big, ["write-tree"], env={"DS_STATS": "1"}))
    depth = names["changed"].count("/") + 1
    t.check(s["write-tree"]["trees built"] == depth and s["write-tree"]["from the cache"] >= 7,
            f"one file {depth - 1} directories down: {s['write-tree']}")
    t.check(fx.ours(t, big, ["write-tree"]).out == fx.real(t, big, ["write-tree"]).out, "write-tree on a big tree")

    # a file gone, a path that names nothing, a repository ours did not make
    os.remove(os.path.join(ours_repo, "a0"))
    fx.ours(t, ours_repo, ["add", "a0"])
    t.check("a0" not in fx.ours(t, ours_repo, ["ls-files"]).out.split("\n"), "add of a file gone")
    r = fx.ours(t, ours_repo, ["add", "nonesuch"], check=False)
    t.check(r.rc == 2 and r.err == "git: pathspec 'nonesuch' did not match any files\n", f"add nonesuch:\n{r}")
    r = fx.ours(t, theirs, ["add", "."], check=False)
    t.check(r.rc == 2 and "changes only repositories its own init made" in r.err, f"add in the real git's:\n{r}")
    with open(os.path.join(ours_repo, ".git", "index.lock"), "w"):
        pass
    r = fx.ours(t, ours_repo, ["add", "."], check=False)
    t.check(r.rc == 2 and "index.lock exists" in r.err, f"add while the index is locked:\n{r}")
    os.remove(os.path.join(ours_repo, ".git", "index.lock"))

    # a damaged index: an ordinary error, never a crash
    path = os.path.join(ours_repo, ".git", "index")
    with open(path, "rb") as f:
        good = f.read()

    def resum(d):
        return d + hashlib.sha1(d).digest()

    body = good[:-20]
    first = 12
    variants = [("cut at %d" % n, good[:n]) for n in range(0, len(good), 7)]
    variants += [("a byte changed at %d" % n, good[:n] + bytes([good[n] ^ 0x40]) + good[n + 1:])
                 for n in range(0, len(good), 13)]
    variants += [("version 4", resum(body[:4] + struct.pack(">I", 4) + body[8:])),
                 ("version 9", resum(body[:4] + struct.pack(">I", 9) + body[8:])),
                 ("more entries than it has", resum(body[:8] + struct.pack(">I", 1000) + body[12:])),
                 ("a mode git does not write", resum(body[:first + 24] + struct.pack(">I", 0o100664) + body[first + 28:])),
                 ("a required extension", resum(body + b"link" + struct.pack(">I", 0))),
                 ("an extension past the end", resum(body + b"ZZZZ" + struct.pack(">I", 99))),
                 ("cached trees that cannot be read", resum(body + b"TREE" + struct.pack(">I", 3) + b"x\0z"))]
    _, entries, _ = fx.parse_index(ours_repo)
    # the first two entries swapped: out of order
    step0 = (62 + len(entries[0][2].encode("utf-8", "surrogateescape")) + 8) & ~7
    step1 = (62 + len(entries[1][2].encode("utf-8", "surrogateescape")) + 8) & ~7
    e0, e1 = body[12:12 + step0], body[12 + step0:12 + step0 + step1]
    variants.append(("out of order", resum(body[:12] + e1 + e0 + body[12 + step0 + step1:])))
    for what, data in variants:
        with open(path, "wb") as f:
            f.write(data)
        r = fx.ours(t, ours_repo, ["ls-files", "-s"], check=False)
        t.check(r.rc == 2 and r.err.startswith("git: the index"), f"an index {what}: not an ordinary error:\n{r}")
    with open(path, "wb") as f:
        f.write(good)

    # damaged trees
    blob = fx.ours(t, ours_repo, ["hash-object", "-w", "hello.txt"]).out.strip()
    oid = bytes.fromhex(blob)
    trees = {"a mode git does not write": (b"100664 x\x00" + oid, "has mode 100664, which git does not write"),
             "a zero-padded mode": (b"040000 x\x00" + oid, "an entry without a mode git writes"),
             "out of order": (b"100644 b\x00" + oid + b"100644 a\x00" + oid, "out of git's order"),
             "a directory after its file": (b"40000 b\x00" + oid + b"100644 b c\x00" + oid, "out of git's order"),
             "cut short": (b"100644 x\x00" + oid[:10], "ends in the middle of an entry"),
             "a slash in a name": (b"100644 a/b\x00" + oid, "an entry named 'a/b'"),
             "no mode": (b"x\x00" + oid, "an entry without a mode git writes")}
    for what, (data, msg) in trees.items():
        name = put_object(ours_repo, b"tree", data)
        r = fx.ours(t, ours_repo, ["ls-tree", name], check=False)
        t.check(r.rc == 2 and msg in r.err, f"a tree with {what}: {msg!r} wanted:\n{r}")
