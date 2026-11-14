"""10.03 Commits: walking a graph for log

A commit is a tree, its parents, an author, a committer and a message: ours, made from the same
tree, parents, people and dates as the real git's commit-tree and commit, has the same name. The
real git's log, cat-file and status agree with ours on a repository ours made, branches and a
merge included, and its fsck --strict passes; ours prints the real git's log, byte for byte, on
histories the real git made (merges, three time zones, commits from the same second) and on
generated ones of thousands of commits. log takes the newest commit off a heap each time and
keeps the names it has seen in a hash table: on a line of 2000 commits the table looks at a few
thousand entries where the list of names seen looks at about two million, and on 16 branches at
once the heap compares a few times per commit where the queue as a list is searched end to end.
Names: HEAD, branches, ~N, ^N, ^{tree}, and a commit's start. A commit whose parent is missing,
or that is damaged, is an ordinary error.
"""

import hashlib
import os
import zlib


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

    # commits ours makes have the real git's names
    repo = fx.new_repo(t, "ours")
    fx.ours(t, repo, ["init", "-q"])
    fx.write(repo, "a.txt", "one\n")
    fx.write(repo, "d/b.txt", "two\n")
    fx.ours(t, repo, ["add", "."])
    tree = fx.ours(t, repo, ["write-tree"]).out.strip()
    for args, inp in ((["-m", "one"], None), (["-m", "one", "-m", "two  "], None), ([], "from stdin"),
                      (["-m", "a\n\n\nb\n"], None)):
        mine = fx.ours(t, repo, ["commit-tree", tree] + args, input=inp, date="1700000000 +0530").out
        t.check(mine == fx.real(t, repo, ["commit-tree", tree] + args, input=inp, date="1700000000 +0530").out,
                f"commit-tree {args}: not the real git's commit")
    r = fx.ours(t, repo, ["commit", "-m", "  \n\nfirst  \n\n\n\nbody\t \n\n"], date="1700000000 +0530")
    t.check(r.out.startswith("[main (root-commit) ") and r.out.endswith("] first\n"), f"commit:\n{r}")
    twin = fx.new_repo(t, "twin")
    fx.real(t, twin, ["init", "-q"])
    fx.write(twin, "a.txt", "one\n")
    fx.write(twin, "d/b.txt", "two\n")
    fx.real(t, twin, ["add", "."])
    fx.real(t, twin, ["commit", "-q", "-m", "  \n\nfirst  \n\n\n\nbody\t \n\n"], date="1700000000 +0530")
    head = fx.real(t, repo, ["rev-parse", "HEAD"]).out
    t.check(head == fx.real(t, twin, ["rev-parse", "HEAD"]).out, "commit: not the real git's commit of the same")
    t.check(fx.real(t, repo, ["status", "--porcelain"]).out == "", "the real git's status after our commit")
    r = fx.ours(t, repo, ["commit", "-m", "again"], check=False)
    t.check(r.rc == 1 and r.out.startswith("nothing to commit"), f"commit with nothing changed:\n{r}")

    # a history with a branch and a merge, made by ours, read by the real git
    fx.write(repo, "a.txt", "one\nmore\n")
    fx.ours(t, repo, ["add", "a.txt"])
    fx.ours(t, repo, ["commit", "-q", "-m", "second"], date="1700000100 -0700")
    fx.ours(t, repo, ["branch", "side", "HEAD~1"])
    side_tree = fx.ours(t, repo, ["write-tree"]).out.strip()
    side = fx.ours(t, repo, ["commit-tree", side_tree, "-p", "side", "-m", "on side"], date="1700000050 +0000").out.strip()
    merge = fx.ours(t, repo, ["commit-tree", "HEAD^{tree}", "-p", "HEAD", "-p", side, "-m", "Merge side"],
                    date="1700000200 +0000").out.strip()
    fx.real(t, repo, ["update-ref", "refs/heads/side", side])
    fx.real(t, repo, ["update-ref", "refs/heads/main", merge])
    fx.real(t, repo, ["fsck", "--strict"])
    t.check(fx.ours(t, repo, ["branch"]).out == "* main\n  side\n", "branch")
    for args in (["log"], ["log", "--oneline"], ["log", "-n", "2"], ["log", "-3", "--oneline"], ["log", "side", "main~1"],
                 ["log", "--oneline", "HEAD^2"], ["log", "--oneline", "main^1"]):
        t.check(fx.ours(t, repo, args).out == fx.real(t, repo, args).out, f"{' '.join(args)}: not the real git's")
    for name in ("HEAD", "HEAD~1", "HEAD^2", "side~1", merge[:7], "HEAD^{tree}", "HEAD~1^{tree}"):
        t.check(fx.ours(t, repo, ["cat-file", "-p", name]).out == fx.real(t, repo, ["cat-file", "-p", name]).out,
                f"cat-file -p {name}")

    # histories the real git made
    theirs = fx.new_repo(t, "theirs")
    fx.real(t, theirs, ["init", "-q"])
    dates = ["1700000000 +0000", "1700003600 +0530", "1700003600 -0800", "1700003600 +0000", "1700007200 +0100"]
    for i, d in enumerate(dates):
        fx.write(theirs, "main.txt", f"main {i}\n")
        fx.real(t, theirs, ["add", "."])
        fx.real(t, theirs, ["commit", "-q", "-m", f"main {i}\n\nline\twith a tab\n\n  indented"], date=d)
        if i == 1:
            fx.real(t, theirs, ["branch", "topic"])
    fx.real(t, theirs, ["checkout", "-q", "topic"])
    for i, d in enumerate(dates[2:]):
        fx.write(theirs, "topic.txt", f"topic {i}\n")
        fx.real(t, theirs, ["add", "."])
        fx.real(t, theirs, ["commit", "-q", "-m", f"topic {i}"], date=d)
    fx.real(t, theirs, ["checkout", "-q", "main"])
    fx.real(t, theirs, ["merge", "-q", "--no-ff", "-m", "Merge topic", "topic"], date="1700009000 +0200")
    for args in (["log"], ["log", "--oneline"], ["log", "topic", "main~1"], ["log", "--oneline", "HEAD^2~1"]):
        t.check(fx.ours(t, theirs, args).out == fx.real(t, theirs, args).out,
                f"{' '.join(args)} on the real git's history: not the same")
        t.check(fx.ours(t, theirs, args + ["--algo=list"]).out == fx.real(t, theirs, args).out,
                f"{' '.join(args)} --algo=list on the real git's history")

    # the heap and the table against plain lists, on a long line and on 16 branches at once
    line, names = fx.gen_repo(t, "linear", 2000)
    want = fx.real(t, line, ["log", "--oneline"]).out
    rl = fx.ours(t, line, ["log", "--oneline", "--algo=list"], env={"DS_STATS": "1"})
    rh = fx.ours(t, line, ["log", "--oneline"], env={"DS_STATS": "1"})
    t.check(rl.out == want and rh.out == want, "log on 2000 commits: not the real git's")
    sl, sh = fx.stats(rl), fx.stats(rh)
    t.check(sl["log"]["seen probes"] == 2000 * 1999 // 2, f"a list of names seen, 2000 commits: {sl['log']}")
    t.check(sh["table"]["probes"] < 3 * 2000 and sh["table"]["inserts"] == 2000, f"a table of them: {sh['table']}")
    t.check(sh["heap"]["comparisons"] == 0, f"a line never has two commits in the queue: {sh['heap']}")
    wide, names = fx.gen_repo(t, "wide", 1600)
    want = fx.real(t, wide, ["log"]).out
    rl = fx.ours(t, wide, ["log", "--algo=list"], env={"DS_STATS": "1"})
    rh = fx.ours(t, wide, ["log"], env={"DS_STATS": "1"})
    t.check(rl.out == want and rh.out == want, "log of 16 branches: not the real git's")
    sl, sh = fx.stats(rl), fx.stats(rh)
    n = sh["log"]["commits"]
    t.check(sl["log"]["queue scans"] > 14 * n and sh["heap"]["comparisons"] < 9 * n,
            f"16 branches: the queue as a list {sl['log']}, as a heap {sh['heap']}")
    t.check(sh["heap"]["pushes"] == n == sh["heap"]["pops"], f"each commit through the heap once: {sh['heap']}")

    # DS_TRACE: each commit off the heap, with what is left in it
    r = fx.ours(t, repo, ["log", "--oneline"], env={"DS_TRACE": "1"})
    pops = [l for l in r.err.splitlines() if l.startswith("trace: log: pop")]
    m, s2, s1, root = (fx.real(t, repo, ["rev-parse", "--short=7", x]).out.strip() for x in ("HEAD", "HEAD^1", "HEAD^2", "HEAD~2"))
    t.check(pops == [f"trace: log: pop {m} 1700000200; heap: (empty)",
                     f"trace: log: pop {s2} 1700000100; heap: {s1} 1700000050",
                     f"trace: log: pop {s1} 1700000050; heap: {root} 1700000000",
                     f"trace: log: pop {root} 1700000000; heap: (empty)"], f"log's trace:\n{r.err}")
    t.check(f"trace: log: {root}, parent of {s1}: seen already" in r.err, f"log's trace:\n{r.err}")

    # names that name nothing, and damaged commits
    for name, msg in (("HEAD~9", "has 0 parents, so no parent 1"), ("HEAD^3", "has 2 parents, so no parent 3"),
                      ("nonesuch", "'nonesuch' names nothing"), ("HEAD^{tree}~1", "is a tree, not a commit")):
        r = fx.ours(t, repo, ["log", name], check=False)
        t.check(r.rc == 2 and msg in r.err, f"log {name}: {msg!r} wanted:\n{r}")
    empty = fx.new_repo(t, "empty")
    fx.ours(t, empty, ["init", "-q"])
    r = fx.ours(t, empty, ["log"], check=False)
    t.check(r.rc == 2 and r.err == "git: HEAD is on main, which has no commits yet\n", f"log of nothing:\n{r}")
    blob = fx.ours(t, repo, ["hash-object", "-w", "a.txt"]).out.strip()
    r = fx.ours(t, repo, ["log", blob], check=False)
    t.check(r.rc == 2 and "is a blob, not a commit" in r.err, f"log of a blob:\n{r}")
    ident = b"author A <a@example.com> 1700000000 +0000\ncommitter A <a@example.com> 1700000000 +0000\n"
    missing = "1" * 40
    bad = {"a parent that is missing": (b"tree " + tree.encode() + b"\nparent " + missing.encode() + b"\n" + ident + b"\nx\n",
                                        f"object {missing} is not in the repository"),
           "no tree": (ident + b"\nx\n", "it does not start with its tree"),
           "no committer": (b"tree " + tree.encode() + b"\nauthor A <a@example.com> 1 +0000\n\nx\n", "it has no committer"),
           "no date": (b"tree " + tree.encode() + b"\nauthor A <a> 1 +0000\ncommitter A <a>\n\nx\n", "its committer has no date"),
           "no end to its header": (b"tree " + tree.encode() + b"\nauthor A <a> 1 +0000", "its header has no end"),
           "a bad parent line": (b"tree " + tree.encode() + b"\nparent xyz\n" + ident + b"\nx\n", "a parent line")}
    for what, (data, msg) in bad.items():
        name = put_object(repo, b"commit", data)
        r = fx.ours(t, repo, ["log", name], check=False)
        t.check(r.rc == 2 and msg in r.err, f"a commit with {what}: {msg!r} wanted:\n{r}")
