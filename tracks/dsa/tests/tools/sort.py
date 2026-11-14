"""sort: sorting lines as LC_ALL=C sort does (module 02). T is track.py.

    check(t, args, path, env=None, algo=None)
                        bin/sort [--algo=algo] args path and the system's sort args path must
                        print the same bytes; returns ours (a Result: DS_STATS=1 in env for the
                        counts)
    FLAGS               option sets on which the system's BSD and GNU sorts agree, for
                        differential tests
    random_lines(t, seed, n)
                        n short lines of few different bytes, blanks and digits: lines whose
                        keys tie, fields that are empty, numbers that are not numbers
"""

from harness.core import Fail

PROGRAMS = {"sort": "02.01"}
FILES_FROM = {"tools/sort/tool.mk": "02.01"}

FLAGS = [
    [], ["-r"], ["-n"], ["-rn"], ["-u"], ["-nu"], ["-ru"], ["-rnu"],
    ["-k2"], ["-k2,2"], ["-k2n"], ["-k2,2n"], ["-k2", "-n"], ["-k2,2", "-u"], ["-k2,2n", "-u"],
    ["-k1,1", "-k2,2nr"], ["-k2.2,2.3"], ["-k1.2"], ["-k3"], ["-r", "-k2,2"], ["-k2,2", "-r", "-u"],
    ["-n", "-k2,2", "-u"], ["-t", ",", "-k2"], ["-t", ",", "-k2,2n"], ["-t", ",", "-k2", "-u"],
    ["-k2,2r", "-k1,1"], ["-k3,3n", "-k1,1r"], ["-u", "-k1,1"], ["-t", " ", "-k2,2"], ["-k1.3,1.3"],
]


def check(t, args, path, env=None, algo=None):
    ours = T.run(t, "sort", ([f"--algo={algo}"] if algo else []) + list(args) + [path], env=env)
    theirs = T.system(t, ["sort"] + list(args) + [path])
    T.same(t, ours.out, theirs.out, f"sort {' '.join(args)}")
    return ours


def random_lines(t, seed, n):
    """Short lines from few bytes, so keys tie often: letters, digits, '-', '.', ',', blanks."""
    rng = T._gen_module(T._root(t)).Rand(seed)
    alphabet = "aAbB019-., \t"
    out = []
    for _ in range(n):
        out.append("".join(alphabet[rng.below(len(alphabet))] for _ in range(rng.below(9))))
    return "".join(l + "\n" for l in out)


def timeline_steps(k):
    have = ["insertion"] + (["merge"] if k >= (2, 2) else []) + (["quick-first", "quick"] if k >= (2, 3) else []) \
        + (["heap"] if k >= (2, 4) else [])
    if k < (2, 1):
        return []
    steps = [T.sh_step("printf 'b\\na\\nB\\n' | bin/sort", "B\na\nb\n"),
             T.sh_step("printf '10\\n9\\n-1\\n' | bin/sort -rn", "10\n9\n-1\n"),
             T.sh_step("printf 'x 2\\ny 1\\n' | bin/sort -k2", "y 1\nx 2\n"),
             T.sh_step("bin/sort --algo=bogo < /dev/null", f"sort: no --algo 'bogo' (have: {', '.join(have)})\n", 2)]
    if k < (2, 5):
        steps.append(T.sh_step("bin/sort -S 1K < /dev/null", "sort: unknown option -S\n", 2))
    else:
        steps.append(T.sh_step("printf 'b\\nc\\na\\n' | bin/sort -S 1b", "a\nb\nc\n"))
    return steps


def timeline_after(root, k):
    if k < (2, 1):
        return None
    book = T.data(root, "book.txt")
    for args in ([], ["-r"], ["-u", "-k2"], ["-n"]):
        ours = T.run(root, "sort", args + [book]).out
        if ours != T.system(root, ["sort"] + args + [book]).out:
            raise Fail(f"bin/sort {' '.join(args)} and the system's sort differ on data/book.txt")
    note = "sort: the system's bytes on the book"
    if k >= (2, 5):
        r = T.run(root, "sort", ["-S", "64K", book], env={"DS_STATS": "1"})
        if r.out != T.system(root, ["sort", book]).out:
            raise Fail("bin/sort -S 64K and the system's sort differ on data/book.txt")
        note += f", and with -S 64K in {T.stats(r.err)['runs']['written']} runs"
    return note
