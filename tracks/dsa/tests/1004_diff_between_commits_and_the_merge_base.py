"""10.04 diff between commits, and the merge base

diff between two commits prints what changed as git does: the same files, header lines and blob
names as the real git's diff --no-renames, for files changed, added, deleted, emptied, made
executable, turned into directories and back, symbolic links, names with spaces and tabs, a last
line without a newline, and binary files; as many lines added and taken away in each file as the
real git's --minimal; and the real git apply takes the patch (at -U3, -U1 and -U0) and makes the
second commit's tree of the first's. Two trees are walked side by side and what is the same is
passed over unopened: on 3000 files with one changed, a few trees and two blobs are read, where
--algo=all reads all of them, with the same patch. merge-base finds the real git's best common
ancestors (a fork, an ancestor, a criss-cross with two, two histories with none), painting both
histories in one walk, where --algo=rewalk walks one history again for every commit of the other.
"""

import hashlib
import os
import re
import zlib

HEADER = ("diff --git", "new file mode", "deleted file mode", "old mode", "new mode", "index ", "--- ", "+++ ",
          "Binary files")


def headers(text):
    return [l for l in text.splitlines() if l.startswith(HEADER)]


def numstat(patch):
    """{path: (added, deleted)} counted from a patch's hunks, its own way."""
    out, path, inhunk = {}, None, False
    for l in patch.splitlines():
        if l.startswith("diff --git "):
            m = re.match(r'diff --git (?:"a/(.*)"|a/(.*)) (?:"b/.*"|b/.*)$', l)
            path, inhunk = (m.group(1) or m.group(2)).replace("\\t", "\t"), False
            out.setdefault(path, [0, 0])
        elif l.startswith("@@ "):
            inhunk = True
        elif l.startswith("Binary files"):
            out[path] = ["-", "-"]
        elif inhunk and l.startswith("+"):
            out[path][0] += 1
        elif inhunk and l.startswith("-"):
            out[path][1] += 1
    return {p: tuple(v) for p, v in out.items()}


def real_numstat(fx, t, repo, a, b):
    out = {}
    for l in fx.real(t, repo, ["diff", "--numstat", "--no-renames", "--minimal", a, b]).out.splitlines():
        add, dele, path = l.split("\t", 2)
        if path.startswith('"'):
            path = path[1:-1].replace("\\t", "\t")
        prev = out.get(path)
        cur = (add, dele) if add == "-" else (int(add), int(dele))
        out[path] = cur if prev is None else (prev[0] + cur[0], prev[1] + cur[1])
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
    repo = fx.new_repo(t, "repo")
    fx.ours(t, repo, ["init", "-q"])
    with open(T.data(t, "book.txt"), "rb") as f:
        book = f.read().split(b"\n")
    before = {"a.txt": b"\n".join(book[100:300]) + b"\n", "no-eol": b"one\ntwo", "space name.txt": b"s\n",
              "t\tab": b"tab\n", "old.txt": b"old\n", "gone/dir/x.txt": b"x\n", "run.sh": b"#!/bin/sh\n",
              "both.sh": b"echo 1\n", "fd": b"a file\n", "df/inner.txt": b"in a directory\n",
              "keep/a/b/c.txt": b"c\n", "keep/a/d.txt": b"d\n", "keep/e.txt": b"e\n", "becomes-link": b"text\n",
              "bin.dat": b"\x00binary\x01\x02"}
    for p, d in before.items():
        fx.write(repo, p, d)
    os.symlink("a.txt", os.path.join(repo, "link"))
    fx.ours(t, repo, ["add", "."])
    fx.ours(t, repo, ["commit", "-q", "-m", "before"])
    lines = book[100:300]
    lines[10] = b"a line changed"
    del lines[50:53]
    lines.insert(150, b"a line added")
    fx.write(repo, "a.txt", b"\n".join(lines) + b"\n")
    fx.write(repo, "no-eol", b"one\nthree")
    fx.write(repo, "space name.txt", b"s\nt\n")
    fx.write(repo, "t\tab", b"tab\ntab\n")
    fx.write(repo, "new.txt", b"new\n")
    fx.write(repo, "new empty", b"")
    fx.write(repo, "dir/new/deep.txt", b"deep\n")
    for p in ("old.txt", "gone/dir/x.txt", "fd", "df/inner.txt", "link", "becomes-link"):
        os.remove(os.path.join(repo, p))
    os.rmdir(os.path.join(repo, "gone/dir"))
    os.rmdir(os.path.join(repo, "gone"))
    os.rmdir(os.path.join(repo, "df"))
    fx.write(repo, "fd/inner.txt", b"now a directory\n")
    fx.write(repo, "df", b"now a file\n")
    os.symlink("no-eol", os.path.join(repo, "link"))
    os.symlink("a.txt", os.path.join(repo, "becomes-link"))
    os.chmod(os.path.join(repo, "run.sh"), 0o755)
    fx.write(repo, "both.sh", b"echo 2\n")
    os.chmod(os.path.join(repo, "both.sh"), 0o755)
    fx.ours(t, repo, ["add", "."])
    fx.ours(t, repo, ["commit", "-q", "-m", "after"], date="1700000100 +0000")
    fx.write(repo, "bin.dat", b"\x00binary\x01\x03")
    fx.ours(t, repo, ["add", "bin.dat"])
    fx.ours(t, repo, ["commit", "-q", "-m", "binary"], date="1700000200 +0000")

    # the patch: git's headers, the real git's counts, and git apply makes the second tree of the first
    mine = fx.ours(t, repo, ["diff", "HEAD~2", "HEAD~1"]).out
    theirs = fx.real(t, repo, ["diff", "--no-renames", "HEAD~2", "HEAD~1"]).out
    t.check(headers(mine) == headers(theirs), "diff: not the real git's files and header lines:\n" +
            "\n".join(a + "  |  " + b for a, b in zip(headers(mine), headers(theirs)) if a != b)[:2000])
    t.check(numstat(mine) == real_numstat(fx, t, repo, "HEAD~2", "HEAD~1"),
            f"lines added and deleted: {numstat(mine)}, the real git's {real_numstat(fx, t, repo, 'HEAD~2', 'HEAD~1')}")
    want = fx.real(t, repo, ["rev-parse", "HEAD~1^{tree}"]).out.strip()
    for args, apply in (([], []), (["-U1"], []), (["-U0"], ["--unidiff-zero"])):
        patch = fx.ours(t, repo, ["diff"] + args + ["HEAD~2", "HEAD~1"]).raw
        fx.real(t, repo, ["read-tree", "HEAD~2"])
        fx.real(t, repo, ["apply", "--cached", "--check"] + apply, input=patch)
        fx.real(t, repo, ["apply", "--cached"] + apply, input=patch)
        t.check(fx.real(t, repo, ["write-tree"]).out.strip() == want, f"git apply {' '.join(args)}: not the second tree")
    fx.real(t, repo, ["read-tree", "HEAD"])
    mine = fx.ours(t, repo, ["diff", "HEAD~1", "HEAD"]).out
    t.check(mine == fx.real(t, repo, ["diff", "HEAD~1", "HEAD"]).out, f"a binary file:\n{mine}")
    t.check(fx.ours(t, repo, ["diff", "HEAD", "HEAD"]).out == "", "a commit against itself")

    # skip what is the same, against reading everything: the same patch
    r_skip = fx.ours(t, repo, ["diff", "HEAD~2", "HEAD~1"], env={"DS_STATS": "1", "DS_TRACE": "1"})
    r_all = fx.ours(t, repo, ["diff", "--algo=all", "HEAD~2", "HEAD~1"], env={"DS_STATS": "1"})
    t.check(r_skip.out == r_all.out, "diff --algo=all and skip print different patches")
    t.check("trace: diff: keep/: " in r_skip.err and "on both sides: the same, passed over" in r_skip.err,
            f"diff's trace:\n{r_skip.err}")
    big, names = fx.gen_repo(t, "tree", 3000)
    want = fx.real(t, big, ["diff", "main~1", "main"]).out
    r_skip = fx.ours(t, big, ["diff", "main~1", "main"], env={"DS_STATS": "1"})
    r_all = fx.ours(t, big, ["diff", "--algo=all", "main~1", "main"], env={"DS_STATS": "1"})
    t.check(r_skip.out == want and r_all.out == want, "3000 files, one changed: not the real git's patch")
    sk, al = fx.stats(r_skip)["diff"], fx.stats(r_all)["diff"]
    depth = names["changed"].count("/") + 1
    t.check(sk["trees read"] == 2 * depth and sk["blobs read"] == 2 and sk["files changed"] == 1 and
            sk["subtrees skipped"] >= 7 and sk["bytes compared"] == 0, f"skip: {sk}")
    # every file of both, and the changed file's two blobs again to print them
    t.check(al["blobs read"] == 2 * 3000 + 2 and al["trees read"] > 50 * sk["trees read"] and
            al["entries compared"] == 3000, f"all: {al}")

    # merge-base: the real git's answers, on the real git's histories
    h = fx.new_repo(t, "history")
    fx.real(t, h, ["init", "-q"])
    clock = [1700000000]

    def commit(msg):
        fx.write(h, "f.txt", msg + "\n")
        fx.real(t, h, ["add", "f.txt"])
        clock[0] += 60
        fx.real(t, h, ["commit", "-q", "-m", msg], date=f"{clock[0]} +0000")

    for i in range(3):
        commit(f"trunk {i}")
    fx.real(t, h, ["branch", "a"])
    fx.real(t, h, ["branch", "b"])
    for side in ("a", "b"):
        fx.real(t, h, ["checkout", "-q", side])
        commit(f"{side} 1")
    fx.real(t, h, ["checkout", "-q", "a"])                   # a criss-cross: each merges the other
    clock[0] += 60
    fx.real(t, h, ["merge", "-q", "-s", "ours", "-m", "a takes b", "b~0"], date=f"{clock[0]} +0000")
    fx.real(t, h, ["checkout", "-q", "b"])
    clock[0] += 60
    fx.real(t, h, ["merge", "-q", "-s", "ours", "-m", "b takes a", "a~1"], date=f"{clock[0]} +0000")
    commit("b 2")
    fx.real(t, h, ["checkout", "-q", "a"])
    commit("a 2")
    fx.real(t, h, ["checkout", "-q", "--orphan", "lonely"])
    commit("another root")
    pairs = [("a", "b"), ("a", "a~2"), ("main", "a"), ("a~1", "b~1"), ("main", "main"), ("a", "lonely"),
             ("main~1", "b")]
    for x, y in pairs:
        r_real = fx.real(t, h, ["merge-base", "--all", x, y], check=False)
        r_one = fx.real(t, h, ["merge-base", x, y], check=False)
        for algo in ("rewalk", "paint"):
            r = fx.ours(t, h, ["merge-base", "--all", f"--algo={algo}", x, y], check=False)
            t.check(r.rc == r_real.rc and sorted(r.out.split()) == sorted(r_real.out.split()),
                    f"merge-base --all --algo={algo} {x} {y}: {r.out.split()} (rc {r.rc}), "
                    f"the real git's {r_real.out.split()} (rc {r_real.rc})")
            r = fx.ours(t, h, ["merge-base", f"--algo={algo}", x, y], check=False)
            t.check(r.rc == r_one.rc and r.out == r_one.out, f"merge-base --algo={algo} {x} {y}: {r.out!r}, "
                    f"the real git's {r_one.out!r}")
    t.check(len(fx.real(t, h, ["merge-base", "--all", "a", "b"]).out.split()) == 2,
            "the criss-cross should have two merge bases")

    # one walk that paints, against a walk of one history for each commit of the other
    fork, names = fx.gen_repo(t, "fork", 150)
    r_paint = fx.ours(t, fork, ["merge-base", "left", "right"], env={"DS_STATS": "1"})
    r_rewalk = fx.ours(t, fork, ["merge-base", "--algo=rewalk", "left", "right"], env={"DS_STATS": "1"})
    t.check(r_paint.out == r_rewalk.out == names["base"] + "\n" == fx.real(t, fork, ["merge-base", "left", "right"]).out,
            "merge-base of the fork")
    p, w = fx.stats(r_paint)["merge-base"], fx.stats(r_rewalk)["merge-base"]
    t.check(p["commits visited"] <= 2 * 150 + 4 and p["walks"] == 0, f"paint: {p}")
    t.check(w["commits visited"] >= 150 * 150 and w["walks"] == 151, f"rewalk: {w}")
    r = fx.ours(t, h, ["merge-base", "a~1", "b~1"], env={"DS_TRACE": "1"})
    t.check(re.search(r"^trace: merge-base: pop [0-9a-f]{7} \d+, reached by 1 and 2, stale$", r.err, re.M),
            f"merge-base's trace:\n{r.err}")

    # a parent that is missing, and names that are not commits
    tree = fx.real(t, repo, ["rev-parse", "HEAD^{tree}"]).out.strip()
    ident = b"author A <a@example.com> 1700000000 +0000\ncommitter A <a@example.com> 1700000000 +0000\n"
    orphan = put_object(repo, b"commit", b"tree " + tree.encode() + b"\nparent " + b"2" * 40 + b"\n" + ident + b"\nx\n")
    r = fx.ours(t, repo, ["merge-base", orphan, "HEAD"], check=False)
    t.check(r.rc == 2 and f"object {'2' * 40} is not in the repository" in r.err, f"a missing parent:\n{r}")
    r = fx.ours(t, repo, ["diff", "HEAD", "nonesuch"], check=False)
    t.check(r.rc == 2 and "'nonesuch' names nothing" in r.err, f"diff with a name of nothing:\n{r}")
    blob = fx.ours(t, repo, ["hash-object", "-w", "new.txt"]).out.strip()
    r = fx.ours(t, repo, ["diff", "HEAD", blob], check=False)
    t.check(r.rc == 2 and "is a blob, not a tree" in r.err, f"diff with a blob:\n{r}")
