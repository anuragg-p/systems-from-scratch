"""look: the lines of a sorted file that start with a string (module 02). T is track.py.

    reference(path, key)
                        what look must print: the lines of path that start with key
    check(t, key, path, algo=None)
                        bin/look [--algo=algo] key path against reference(), and against the
                        system's look where there is one (macOS has it; Linux, in util-linux
                        or bsdextrautils, often not); returns ours, run with DS_STATS=1
"""

from harness.core import Fail

PROGRAMS = {"look": "02.06"}
FILES_FROM = {"tools/look/tool.mk": "02.06"}


def reference(path, key):
    with open(path, "rb") as f:
        data = f.read()
    lines = data.split(b"\n")
    if lines[-1] == b"":                 # the newline at the end, or an empty file
        lines.pop()
    k = key.encode("utf-8", "surrogateescape")
    return "".join(l.decode("utf-8", "surrogateescape") + "\n" for l in lines if l.startswith(k))


def check(t, key, path, algo=None):
    args = ([f"--algo={algo}"] if algo else []) + [key, path]
    ours = T.run(t, "look", args, env={"DS_STATS": "1"}, check=False)
    want = reference(path, key)
    T.same(t, ours.out, want, f"look {key!r}")
    if ours.rc != (0 if want else 1):
        raise Fail(f"look {key!r} should exit {0 if want else 1}:\n{ours}")
    if T.have("look"):
        theirs = T.system(t, ["look", key, path], check=False)
        T.same(t, ours.out, theirs.out, f"look {key!r} (the system's)")
    return ours


def timeline_steps(k):
    if k < (2, 6):
        return []
    return [T.sh_step("printf 'a\\nab\\nabc\\nb\\n' > look.txt; bin/look ab look.txt", "ab\nabc\n"),
            T.sh_step("bin/look --algo=scan c look.txt", "", 1)]


def timeline_after(root, k):
    if k < (2, 6):
        return None
    words = T.sh(root, "tr -cs 'A-Za-z' '\\n' < data/book.txt | sort -u > words.txt")
    for key in ("Hol", "the", "zzz", "a"):
        for algo in ("binary", "scan"):
            got = T.run(root, "look", [f"--algo={algo}", key, "words.txt"], check=False).out
            if got != reference(f"{root}/words.txt", key):
                raise Fail(f"bin/look --algo={algo} {key} words.txt printed the wrong lines")
    return "look: the right lines from the book's sorted words"
