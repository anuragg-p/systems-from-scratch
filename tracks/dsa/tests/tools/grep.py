"""grep: the lines of a text that match a pattern (module 04). T is track.py.

    FIXED, BOOK, SOURCE the table: fixed strings (grep -F), and regular expressions (grep -E) for
                        the book and for the project's own source. On every one of them, with
                        every set of FLAGS, macOS's BSD grep and GNU grep 3.11 print the same
                        bytes and exit with the same status; tools/grep/NOTES.md lists the
                        patterns left out because they do not, and why.
    FLAGS               the sets of -n -c -v -i the table is run with
    sources(t)          the project's own C files: lib/*.c lib/*.h tools/*/*.c, as paths
                        relative to the project
    check(t, args, files=(), algo=None, input=None)
                        bin/grep [--algo=algo] args files, and the system's grep args files: the
                        same output, the same exit status. Returns ours, run with DS_STATS=1
    table(t, mode, algo, cache=None)
                        check() for every pattern of the table, -F (FIXED, on the book and the
                        source) or -E (BOOK and SOURCE), each plain and with one set of FLAGS
                        (pattern k gets FLAGS[k % len(FLAGS)]), so every set is used
    oracle(t, algo, n, seed, args=())
                        n random patterns from a small grammar, each run with --algo=algo on
                        random lines, against Python's re on the same lines (a pattern of this
                        grammar means the same in both): fails at the first difference
    expo(n)             the classic: (pattern, line) = n optional a's then n a's, and n a's
    count(t, args, files, algo=None)
                        bin/grep -c ... as a number
"""

import glob
import os
import random
import re

from harness.core import Fail

PROGRAMS = {"grep": "04.01"}
FILES_FROM = {
    "tools/grep/tool.mk": "04.01",
    "tools/grep/gen.py": "04.01",
    "lib/strsearch.h": "04.01",
    "lib/re.h": "04.02",
    "lib/nfa.h": "04.03",
    "lib/dfa.h": "04.04",
}
HIDDEN = ["tools/grep/NOTES.md", "tools/grep/NOTICE.txt"]

FIXED = ["Holmes", "Sherlock Holmes", "the", "e", "said he", "zzzz", "Mr. ", "", "a.b", "watson", "I",
         "(", "[", "*", "\\", "--", "?", "Holmes's", "^", "$", "WATSON", "Baker Street", "it was", ".\"",
         "static", "die(", "->", "/*", "#include", "@build", "size_t", "{", "}", "x", "if (", "    "]

BOOK = [
    "Holmes", "H.lmes", "^.$", "^...$", "[0-9]+", "[A-Z][a-z]+ [A-Z][a-z]+", "[^a-zA-Z ,.]", "[]a]",
    "[^]a-z]", "[a-]", "[-a]", "[[:digit:]][[:digit:]]*", "[[:punct:]]$", "[[:space:]]$", "[[:alpha:]]+'s",
    "[[:upper:]][[:upper:]][[:upper:]]", "colou?r", "wa+s", "x*", "(ab)*c", "Wat(son)?", "o+h",
    "Holmes|Watson", "(Holmes|Watson), ", "^(The|A) ", "a|b|c", "^The", "mes$", "^$", "^[A-Z ]+$", "\\.$",
    "(^| )the( |$)", "^(.*)$", "a$|^b", "\\.", "\\(", "\\*", "\\[", "\\?", "((a|e)(b|c))+d", "(a*)*b",
    "(a|b)*c(d|e)", "q[^u]", "s)", "\\)$", "(Mr|Mrs)\\. [A-Z]", "^ +", " +$", "[aeiou][aeiou][aeiou]",
    "[^ ]+ing [^ ]+ly", "(x+x+)+y", "^([A-Za-z]+ )+[A-Za-z]+\\.$", "[.]", "[*+?]", "[\\]", "a{",
    "(very|rather|quite) [a-z]+", "\"[^\"]*\"", "[0-9][0-9]*\\.[0-9]", "^[^aeiou]*$", ".*", "", "()",
    "(()|a)b", "$^", "^$|^ ", "[[:lower:]]+-[[:lower:]]+", "Sherlock|Holmes|Watson|Lestrade|Baker",
    "[A-Z]+[a-z]*[A-Z]", "-", "[a-c]+[x-z]",
]

SOURCE = [
    "^static ", "die\\(\"", "->(next|len)", "[a-z_]+\\(void\\)", "^#include \"[a-z]+\\.h\"",
    "@build [0-9][0-9]\\.[0-9][0-9]", "/\\*.*\\*/", "^}$", "\\{$", "[^ ]  +", "x[0-9a-f]+", "//.*$",
    "^[a-z].*\\(", "(int|long|size_t) [a-z]+ = 0;", "\\[[0-9]+\\]", "'\\\\.'", "[<>]=?", "\\|\\|",
    "(&&|\\|\\|)", "^ +\\* ", "^$", "\t", "return [a-z]+;$", "@(from|end|else)",
]

FLAGS = [["-n"], ["-c"], ["-v"], ["-i"], ["-in"], ["-vc"], ["-vn"], ["-ic"]]


def sources(t):
    root = T._root(t)
    return sorted(glob.glob("lib/*.[ch]", root_dir=root)) + sorted(glob.glob("tools/*/*.c", root_dir=root))


_theirs = {}


def check(t, args, files=(), algo=None, input=None, cache=None):
    """bin/grep against the system's grep: the same bytes out, the same exit status."""
    argv = list(args) + list(files)
    extra = ([f"--algo={algo}"] if algo else []) + ([f"--cache={cache}"] if cache else [])
    ours = T.run(t, "grep", extra + argv, input=input, env={"DS_STATS": "1"}, check=False)
    key = (T._root(t), tuple(argv), input)
    if key not in _theirs:
        _theirs[key] = T.system(t, ["grep"] + argv, input=input, check=False)
    theirs = _theirs[key]
    what = f"grep {' '.join(extra + argv)[:200]}"
    T.same(t, ours.out, theirs.out, what)
    if ours.rc != theirs.rc:
        raise Fail(f"{what}: exits {ours.rc}, the system's grep {theirs.rc}:\n{ours}")
    return ours


def table(t, mode, algo, cache=None):
    src = sources(t)
    book = [T.data(t, "book.txt")]
    if mode == "-F":
        work = [(p, files) for p in FIXED for files in (book, src)]
    else:
        work = [(p, book) for p in BOOK] + [(p, src) for p in SOURCE]
    for k, (p, files) in enumerate(work):
        for flags in ([], FLAGS[k % len(FLAGS)]):
            if p == "" and flags == ["-vc"]:
                flags = ["-v"]      # GNU grep 3.11 prints no count at all for -vc '' (BSD and ours: 0)
            check(t, [mode] + flags + ["--", p], files, algo=algo, cache=cache)
    return len(work)


def count(t, args, files, algo=None):
    r = T.run(t, "grep", ([f"--algo={algo}"] if algo else []) + ["-c"] + list(args) + list(files), check=False)
    return int(r.out.strip())


def expo(n):
    return "a?" * n + "a" * n, "a" * n


# ---------------------------------------------------------------- random patterns, and Python's re

ALPHABET = "abc"


def _pattern(rng, depth=0):
    """A random pattern of this grammar: what grep -E and Python's re both read the same way."""
    r = rng.random()
    if depth > 3 or r < 0.3:
        c = rng.random()
        if c < 0.55:
            return rng.choice(ALPHABET)
        if c < 0.7:
            return "."
        if c < 0.85:
            neg = "^" if rng.random() < 0.3 else ""
            body = "".join(rng.sample(ALPHABET, rng.randint(1, 2)))
            return f"[{neg}{body}]"
        return rng.choice(["^", "$"])
    if r < 0.55:
        return "".join(_pattern(rng, depth + 1) for _ in range(rng.randint(2, 3)))
    if r < 0.75:
        return _pattern(rng, depth + 1) + "|" + _pattern(rng, depth + 1)
    inner = _pattern(rng, depth + 1)
    if inner in ("^", "$"):
        inner = "a"
    return f"({inner})" + rng.choice("*+?")


def oracle(t, algo, n, seed, args=(), cache=None):
    """n random patterns against Python's re (bytes, so -i folds ASCII only)."""
    rng = random.Random(seed)
    icase = "-i" in args
    for _ in range(n):
        pat = _pattern(rng)
        lines = ["".join(rng.choice(ALPHABET + "ABx") for _ in range(rng.randint(0, 8))) for _ in range(30)]
        text = "".join(l + "\n" for l in lines)
        rx = re.compile(pat.encode(), re.I if icase else 0)
        want = "".join(f"{i + 1}:{l}\n" for i, l in enumerate(lines) if rx.search(l.encode()))
        extra = [f"--algo={algo}"] + ([f"--cache={cache}"] if cache else [])
        r = T.run(t, "grep", extra + ["-n", "-E"] + list(args) + ["--", pat], input=text, check=False)
        if r.out != want or r.rc != (0 if want else 1):
            for i, l in enumerate(lines):
                got = f"{i + 1}:{l}\n" in r.out
                if got != bool(rx.search(l.encode())):
                    raise Fail(f"grep -E --algo={algo} {' '.join(args)} {pat!r} on the line {l!r}: "
                               f"{'matched' if got else 'did not match'}, Python's re "
                               f"{'did not' if got else 'did'} (exit {r.rc}: {r.err.strip()[:200]})")
            raise Fail(f"grep -E --algo={algo} {pat!r}: exit {r.rc}, want {0 if want else 1}:\n{r}")


# ---------------------------------------------------------------- the timeline

def timeline_steps(k):
    if k < (4, 1):
        return []
    steps = [T.sh_step("printf 'one\\ntwo\\nthree\\n' | bin/grep -F -n o", "1:one\n2:two\n"),
             T.sh_step("printf 'one\\ntwo\\n' | bin/grep -F --algo=scan -c -v w", "1\n"),
             T.sh_step("printf 'one\\n' | bin/grep -F zzz", "", 1),
             T.sh_step("bin/grep -F x no-such-file", "grep: no-such-file: No such file or directory\n", 2)]
    if k < (4, 2):
        return steps + [
            T.sh_step("printf 'one\\n' | bin/grep 'o.e'",
                      "grep: regular expressions are not supported: -F searches for 'o.e' as it is\n", 2),
            T.sh_step("bin/grep -E x < /dev/null", "grep: unknown option -E\n", 2)]
    steps += [T.sh_step("printf 'colour\\ncolor\\ncolr\\n' | bin/grep -E 'colou?r'", "colour\ncolor\n"),
              T.sh_step("printf 'one\\n' | bin/grep 'o(n|x)e'", "one\n"),
              T.sh_step("bin/grep -E 'a{2}' < /dev/null", "grep: intervals such as {2,3} are not supported\n", 2)]
    if k < (4, 3):
        return steps + [T.sh_step("bin/grep -E --algo=nfa x < /dev/null",
                                  "grep: no --algo 'nfa' for a regular expression (have: backtrack)\n", 2)]
    steps.append(T.sh_step("printf 'aab\\n' | bin/grep -E --algo=nfa '(a|b)*b'", "aab\n"))
    if k < (4, 4):
        return steps + [T.sh_step("bin/grep -E --algo=dfa x < /dev/null",
                                  "grep: no --algo 'dfa' for a regular expression (have: backtrack, nfa)\n", 2),
                        T.sh_step("bin/grep --cache=5 x < /dev/null", "grep: unknown option '--cache=5'\n", 2)]
    return steps + [T.sh_step("printf 'aab\\nba\\n' | bin/grep -E --algo=dfa --cache=1 '(a|b)*b$'", "aab\n")]


def timeline_after(root, k):
    if k < (4, 1):
        return None
    book = [T.data(root, "book.txt")]
    for algo in ("scan", "horspool"):
        for p in ("Holmes", "Sherlock Holmes", "zzz"):
            for flags in ([], ["-n"], ["-c", "-v"], ["-i"]):
                check(root, ["-F"] + flags + [p], book, algo=algo)
    if k < (4, 2):
        return "grep: -F on the book, as the system's grep"
    algos = ["backtrack"] + (["nfa"] if k >= (4, 3) else []) + (["dfa"] if k >= (4, 4) else [])
    for algo in algos:
        for p in ("Holmes|Watson", "^[A-Z ]+$", "w[aeiou]+n", "(^| )the( |$)"):
            for flags in ([], ["-n"], ["-c", "-v"], ["-i"]):
                check(root, ["-E"] + flags + [p], book, algo=algo)
    return f"grep: -F and -E ({', '.join(algos)}) on the book, as the system's grep"
