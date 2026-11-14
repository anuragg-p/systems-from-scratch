"""06.04 patch: applying a diff

bin/patch makes the second file of the first, byte for byte, with the system's diff (at -U 3, 1 and
0) and with ours, on every pair. A hunk whose lines have moved is found where they are, and patch
says by how much; when a hunk's lines are nowhere, the file is left as it was and the exit status
is 1. Names come from the headers, with -p; -o writes elsewhere; /dev/null makes a file new.
Anything that is not a unified diff is exit status 2.
"""

import os


def test(t):
    T = t.track
    fx = T.fixtures("diff")
    work = os.path.join(t.tmp, "work")

    def ours(diff, old, args=()):
        with open(old, "rb") as f, open(work, "wb") as w:
            w.write(f.read())
        p = T.write(t, "change.diff", diff)
        return T.run(t, "patch", list(args) + ["-s", work, p], env={"DS_STATS": "1"}, check=False)

    applied = 0
    for name, (a, b) in fx.cases(t).items():
        want = fx.read(b)
        diffs = [("ours", T.run(t, "diff", [a, b], check=False).raw),
                 ("ours -U0", T.run(t, "diff", ["-U0", a, b], check=False).raw)]
        for c in ("3", "1", "0"):
            diffs.append((f"the system's -U {c}", fx.system_diff(t, a, b, ["-U", c]).raw))
        for what, diff in diffs:
            r = ours(diff, a)
            t.check(r.rc == 0 and fx.read(work) == want, f"{name}: bin/patch with {what} diff:\n{r}")
            applied += 1
    t.check(applied >= 150, f"only {applied} patches tried")

    # lines added above the hunks: found further on, and said so
    a, b = T.gen(t, "versions", 300, seed=3)
    diff = T.run(t, "diff", [a, b], check=False).raw
    moved = T.write(t, "moved", b"one\ntwo\nthree\n" + fx.read(a))
    r = ours(diff, moved, ["-o", "-"])
    t.check(r.rc == 0 and r.raw == b"one\ntwo\nthree\n" + fx.read(b), f"three lines added above:\n{r}")
    r = T.run(t, "patch", ["-o", os.path.join(t.tmp, "out"), moved, T.write(t, "c.diff", diff)], check=False)
    t.check(r.rc == 0 and "(offset 3 lines)" in r.out, f"patch says how far a hunk moved:\n{r}")
    s = T.stats(ours(diff, moved).err)["patch"]
    t.check(s["places tried"] > s["hunks"], f"a moved hunk is looked for in more than one place: {s}")

    # a hunk whose lines are not there: nothing changes, exit 1
    lines = fx.lines(fx.read(a))
    first = fx.parse(diff)[0]
    lines[first.a - 1 if first.na else first.a] = b"not the line the hunk wants\n"
    broken = b"".join(lines)
    with open(work, "wb") as f:
        f.write(broken)
    r = T.run(t, "patch", [work, T.write(t, "c.diff", diff)], check=False)
    t.check(r.rc == 1 and "does not apply" in r.err and fx.read(work) == broken,
            f"a hunk that does not apply leaves the file as it was:\n{r}")

    # names from the headers, with -p; a new file from /dev/null; the patch on standard input
    os.makedirs(os.path.join(t.tmp, "tree", "src"))
    T.write(t, "tree/src/x.txt", "a\nb\nc\n")
    patch = ("diff --git a/src/x.txt b/src/x.txt\n--- a/src/x.txt\n+++ b/src/x.txt\n@@ -1,3 +1,3 @@\n a\n-b\n+B\n c\n"
             "--- /dev/null\n+++ b/src/new.txt\n@@ -0,0 +1,2 @@\n+new\n+file\n")
    os.mkdir(os.path.join(t.tmp, "empty"))
    bin_patch = os.path.join(t.root, "bin", "patch")
    r = T._exec([bin_patch, "-p1"], patch, T._env(), False, os.path.join(t.tmp, "empty"), 60)
    t.check(r.rc == 2 and os.listdir(os.path.join(t.tmp, "empty")) == [],
            f"run where there is no src/x.txt:\n{r}")
    r = T._exec([bin_patch, "-p", "1"], patch, T._env(), False, os.path.join(t.tmp, "tree"), 60)
    t.check(r.rc == 0 and r.out == "patching file src/x.txt\npatching file src/new.txt\n"
            and fx.read(os.path.join(t.tmp, "tree/src/x.txt")) == b"a\nB\nc\n"
            and fx.read(os.path.join(t.tmp, "tree/src/new.txt")) == b"new\nfile\n", f"patch -p1:\n{r}")

    # not a unified diff, a hunk cut short, a missing file: exit 2
    for text in ("just some text\n", "--- a\n+++ b\n@@ -1,3 +1,3 @@\n a\n-b\n", "--- a\n+++ b\n@@ -1 +1 @@\n*x\n+y\n",
                 "--- a\n+++ b\n@@ -x +1 @@\n-a\n+b\n"):
        r = T.run(t, "patch", [work], input=text, check=False)
        t.check(r.rc == 2 and r.err.startswith("patch: ") and fx.read(work) == broken, f"patch < {text!r}:\n{r}")
    r = T.run(t, "patch", ["/no/such/file"], input=diff, check=False)
    t.check(r.rc == 2, f"patch /no/such/file:\n{r}")
    r = T.run(t, "patch", [work], input="", check=False)
    t.check(r.rc == 0 and r.out == "", f"an empty patch changes nothing:\n{r}")
