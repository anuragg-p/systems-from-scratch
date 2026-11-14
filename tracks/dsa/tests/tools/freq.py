"""freq: the most common words in a text (module 01). T is track.py.

    pipeline(t, path)   the shell pipeline freq replaces, run on path: [(count, word)], most
                        common first, ties in reverse byte order (what sort -rn leaves). The
                        empty "word" tr makes of a text that starts with a non-letter is left out.
    counts(text)        freq's output, parsed the same way
    check(t, path, args=(), n=None)
                        bin/freq args path against the pipeline (the first n of it, or all with
                        -n 0); returns freq's Result
"""

from harness.core import Fail

PROGRAMS = {"freq": "01.01"}
FILES_FROM = {"tools/freq/tool.mk": "01.01"}

PIPELINE = "tr -cs 'A-Za-z' '\\n' < \"$0\" | tr 'A-Z' 'a-z' | sort | uniq -c | sort -rn"


def counts(text):
    out = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            out.append((int(parts[0]), parts[1]))
        elif len(parts) != 1:
            raise Fail(f"not a count and a word: {line!r}")
    return out


def pipeline(t, path):
    return counts(T.sh(t, PIPELINE, [path]).out)


def check(t, path, args=(), n=None):
    """bin/freq [-n n] args path, compared with the pipeline."""
    argv = list(args) + (["-n", str(n)] if n is not None else []) + [path]
    r = T.run(t, "freq", argv)
    want = pipeline(t, path)
    if n is None:
        want = want[:10]
    elif n > 0:
        want = want[:n]
    got = counts(r.out)
    if got != want:
        for i, (a, b) in enumerate(zip(got + [None] * len(want), want + [None] * len(got))):
            if a != b:
                raise Fail(f"bin/freq {' '.join(argv)} and the pipeline differ at line {i + 1} "
                           f"({len(got)} lines against {len(want)}):\n  freq:     {a}\n  pipeline: {b}")
    return r


def timeline_steps(k):
    if k < (1, 1):
        return []
    steps = [T.sh_step("printf 'The cat; the dog.\\n' | bin/freq", "      2 the\n      1 dog\n      1 cat\n")]
    if k < (1, 2):
        steps.append(T.sh_step("bin/freq --algo=table < /dev/null", "freq: unknown option '--algo=table'\n", 2))
    else:
        steps += [T.sh_step("printf 'b a b\\n' | bin/freq --algo=list", "      2 b\n      1 a\n"),
                  T.sh_step("bin/freq --algo=tree < /dev/null",
                            "freq: no --algo 'tree' (have: list, table)\n", 2)]
    if k < (1, 3):
        steps.append(T.sh_step("bin/freq --hash=sum < /dev/null", "freq: unknown option '--hash=sum'\n", 2))
    else:
        steps.append(T.sh_step("printf 'b a b\\n' | bin/freq --hash=sum --no-grow", "      2 b\n      1 a\n"))
    if k < (2, 4):
        steps.append(T.sh_step("bin/freq --top=heap < /dev/null", "freq: unknown option '--top=heap'\n", 2))
    else:
        steps.append(T.sh_step("printf 'b a b\\n' | bin/freq --top=select -n 1", "      2 b\n"))
    return steps


def timeline_after(root, k):
    if k < (1, 1):
        return None
    book = T.data(root, "book.txt")
    check(root, book, n=0)
    if k >= (1, 2):
        check(root, book, ["--algo=list"], n=50)
    return "freq: the pipeline's counts on the book"
