#!/usr/bin/env python3
"""Test repositories of a given shape and size, written straight to disk.

    python3 tools/git/gen.py SHAPE N DIR [--seed S]

makes the repository DIR (which must not exist yet, or be empty), and
prints the names of its branches. Every byte is the same on every run and
every machine: the objects are written by Python's own SHA-1 and zlib, the
dates are 1700000000 and a minute more for each commit after.

  linear  N commits in a line on main, each changing one file
  wide    16 branches of N/16 commits each from one first commit, made
          in turn so their dates interleave, all joined by one merge with
          16 parents: main; log takes from 16 lines at once
  fork    N commits on main, then N more on each of two branches from
          there: left and right (main is left); their merge base is main's
          Nth commit
  tree    one commit of N files in directories eight to a level, then one
          more that changes the last of them (main~1 and main), the files
          of the second written out too, with no index: run "git add ."

The repository's config says "[dsa] ours = true": the track's git may
add to it. The real git reads it as any other: loose objects, no packs.
"""

import hashlib
import os
import sys
import zlib

START = 1700000000


class Repo:
    def __init__(self, path):
        if os.path.exists(path) and os.listdir(path):
            raise SystemExit(f"gen.py: {path} is not empty")
        self.git = os.path.join(path, ".git")
        self.path = path
        for d in ("objects", "refs/heads", "refs/tags"):
            os.makedirs(os.path.join(self.git, d), exist_ok=True)
        with open(os.path.join(self.git, "HEAD"), "w") as f:
            f.write("ref: refs/heads/main\n")
        with open(os.path.join(self.git, "config"), "w") as f:
            f.write("[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n"
                    "[dsa]\n\tours = true\n")
        self.clock = START

    def put(self, kind, data):
        raw = b"%s %d\x00" % (kind, len(data)) + data
        name = hashlib.sha1(raw).hexdigest()
        d = os.path.join(self.git, "objects", name[:2])
        p = os.path.join(d, name[2:])
        if not os.path.exists(p):
            os.makedirs(d, exist_ok=True)
            with open(p, "wb") as f:
                f.write(zlib.compress(raw, 1))
        return name

    def blob(self, data):
        return self.put(b"blob", data)

    def tree(self, entries):
        """entries: {name: blob name, or a dict for a subdirectory}; returns the tree's name."""
        items = []
        for name, v in entries.items():
            if isinstance(v, dict):
                items.append((name.encode() + b"/", b"40000 " + name.encode(), self.tree(v)))
            else:
                items.append((name.encode(), b"100644 " + name.encode(), v))
        items.sort()                    # git's order: a directory's name as if it ended in '/'
        return self.put(b"tree", b"".join(head + b"\x00" + bytes.fromhex(h) for _, head, h in items))

    def commit(self, tree, parents, msg):
        when = b"%d +0000" % self.clock
        self.clock += 60
        text = b"tree " + tree.encode() + b"\n"
        text += b"".join(b"parent " + p.encode() + b"\n" for p in parents)
        text += b"author A U Thor <author@example.com> " + when + b"\n"
        text += b"committer C O Mitter <committer@example.com> " + when + b"\n\n" + msg.encode() + b"\n"
        return self.put(b"commit", text)

    def ref(self, branch, name):
        with open(os.path.join(self.git, "refs", "heads", branch), "w") as f:
            f.write(name + "\n")


def _line_of(repo, branch, parent, n, seed, files):
    """n commits after parent, each changing one of files (a dict), on a branch."""
    for i in range(n):
        files = dict(files)
        files["%s.txt" % branch] = repo.blob(b"%s %d %d\n" % (branch.encode(), seed, i))
        parent = repo.commit(repo.tree(files), [parent] if parent else [], "%s %d" % (branch, i))
    return parent, files


def make_repo(shape, n, path, seed=1):
    """Write the repository; returns {branch: commit name}."""
    repo = Repo(path)
    base = {"README": repo.blob(b"a repository made by gen.py, seed %d\n" % seed),
            "src": {"lib.c": repo.blob(b"int lib(void) { return %d; }\n" % seed)}}
    out = {}
    if shape == "linear":
        out["main"], _ = _line_of(repo, "main", None, n, seed, base)
    elif shape == "wide":
        root, files = _line_of(repo, "root", None, 1, seed, base)
        per = max(1, n // 16)
        tips = [root] * 16
        for i in range(per):                 # a commit on each branch in turn: their dates interleave
            for b in range(16):
                f = dict(files)
                f["b%02d.txt" % b] = repo.blob(b"b%02d %d %d\n" % (b, seed, i))
                tips[b] = repo.commit(repo.tree(f), [tips[b]], "b%02d %d" % (b, i))
        merged = dict(files)
        for b in range(16):
            merged["b%02d.txt" % b] = repo.blob(b"b%02d %d %d\n" % (b, seed, per - 1))
            out["b%02d" % b] = tips[b]
        out["main"] = repo.commit(repo.tree(merged), tips, "Merge 16 branches")
    elif shape == "fork":
        trunk, files = _line_of(repo, "main", None, n, seed, base)
        out["base"] = trunk
        out["left"], _ = _line_of(repo, "left", trunk, n, seed, files)
        out["right"], _ = _line_of(repo, "right", trunk, n, seed, files)
        out["main"] = out["left"]
    elif shape == "tree":
        names = []

        def dirs_for(i):
            parts, k = [], i // 8
            while k > 0:
                parts.append("d%d" % (k % 8))
                k //= 8
            return parts

        for i in range(n):
            names.append("/".join(dirs_for(i) + ["f%d.txt" % i]))

        def content(i, version):
            return b"file %d\nseed %d\n" % (i, seed) + (b"changed\n" if version else b"")

        def build(version):
            top = {}
            for i, name in enumerate(names):
                d = top
                parts = name.split("/")
                for p in parts[:-1]:
                    d = d.setdefault(p, {})
                d[parts[-1]] = repo.blob(content(i, version and i == n - 1))
            return top

        first = repo.commit(repo.tree(build(False)), [], "all %d files" % n)
        out["main"] = repo.commit(repo.tree(build(True)), [first], "change %s" % names[-1])
        for i, name in enumerate(names):
            p = os.path.join(path, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(content(i, i == n - 1))
        out["changed"] = names[-1]
    else:
        raise SystemExit(f"gen.py: no shape {shape!r} (have: linear, wide, fork, tree)")
    for b, name in out.items():
        if b != "changed":
            repo.ref(b, name)
    return out


def main(argv):
    seed = 1
    if "--seed" in argv:
        i = argv.index("--seed")
        seed = int(argv[i + 1])
        del argv[i:i + 2]
    if len(argv) != 3:
        raise SystemExit(__doc__)
    for k, v in make_repo(argv[0], int(argv[1]), argv[2], seed).items():
        print(k, v)


if __name__ == "__main__":
    main(sys.argv[1:])
