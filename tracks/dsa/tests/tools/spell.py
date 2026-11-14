"""spell: the words of a text that are not in the dictionary (module 05). T is track.py.

There is no system spell to compare with on most machines, so spell is held to plain models here
(Python sets and lists) and, where the system has the tools, to them: the unknown words to a
pipeline of tr, grep, sort and comm, and completions to look (the system's, or bin/look).

    DICT                the dictionary spell reads when -d names none (relative to the project)
    dictionary(t, path=None)
                        its words as spell reads them, in file order: lowercased, and lines with
                        anything but letters left out
    text_words(path)    the words of a text as spell reads them: runs of A-Za-z, lowercased
    unknown(t, path, words=None)
                        what spell prints for a text: its words of two letters or more that are not
                        in the dictionary (a set of words), once each, in byte order
    pipeline(t, path)   the same from the system's tools: tr | tr | grep .. | sort -u | comm -23
    check(t, path, args=(), words=None)
                        bin/spell args path against unknown() (and pipeline(), for the default
                        dictionary); returns its Result, run with DS_STATS=1
    complete(t, prefix, args=(), words=None)
                        bin/spell args -p prefix against the dictionary's words that start with it
                        (and look's, for the default dictionary); returns the Result
    distance(a, b)      the edit distance, the straightforward way: the whole table
    nearest(word, words, e=2, n=5)
                        what -s prints for word: the words at the smallest distance found up to e,
                        in byte order, the first n (0: all)
    nonwords(count, words, seed)
                        count different strings of 2 to 10 letters that are not in words, sorted
    bloom_formula(n, m, k)
                        the chance of a false positive, (1 - e^(-kn/m))^k
"""

import math
import random
import re

from harness.core import Fail

PROGRAMS = {"spell": "05.01"}
FILES_FROM = {
    "tools/spell/tool.mk": "05.01",
    "tools/spell/words.txt": "05.01",
    "tools/spell/NOTICE.txt": "05.01",
    "tools/spell/gen.py": "05.03",
    "lib/trie.h": "05.01",
    "lib/bloom.h": "05.02",
    "lib/edit.h": "05.03",
}
HIDDEN = ["tools/spell/NOTES.md"]

DICT = "tools/spell/words.txt"
PIPELINE = ("tr -cs 'A-Za-z' '\\n' < \"$0\" | tr 'A-Z' 'a-z' | grep .. | sort -u | comm -23 - \"$1\"")
LETTERS = re.compile(rb"^[A-Za-z]+$")


def dictionary(t, path=None):
    path = path or f"{T._root(t)}/{DICT}"
    out = []
    with open(path, "rb") as f:
        for line in f.read().split(b"\n"):
            line = line[:-1] if line.endswith(b"\r") else line
            if LETTERS.match(line):
                out.append(line.decode("ascii").lower())
    return out


def text_words(path):
    with open(path, "rb") as f:
        return [w.decode("ascii").lower() for w in re.findall(rb"[A-Za-z]+", f.read())]


def unknown(t, path, words=None):
    have = set(words if words is not None else dictionary(t))
    return sorted({w for w in text_words(path) if len(w) > 1 and w not in have})


def pipeline(t, path):
    return T.sh(t, PIPELINE, [path, f"{T._root(t)}/{DICT}"]).out.splitlines()


def check(t, path, args=(), words=None):
    """bin/spell args path, against the model and (default dictionary) the pipeline."""
    r = T.run(t, "spell", list(args) + [path], env={"DS_STATS": "1"})
    want = unknown(t, path, words)
    T.same(t, r.out, "".join(w + "\n" for w in want), f"spell {' '.join(args)} {path} (the model)")
    if words is None and not any(a.startswith("-d") for a in args):
        T.same(t, r.out, "".join(w + "\n" for w in pipeline(t, path)),
               f"spell {' '.join(args)} {path} (tr | sort -u | comm -23)")
    return r


def complete(t, prefix, args=(), words=None):
    """bin/spell args -p prefix, against the words that start with it, and look's."""
    r = T.run(t, "spell", list(args) + ["-p", prefix], env={"DS_STATS": "1"}, check=False)
    p = prefix.lower()
    want = sorted({w for w in (words if words is not None else dictionary(t)) if w.startswith(p)})
    T.same(t, r.out, "".join(w + "\n" for w in want), f"spell {' '.join(args)} -p {prefix!r}")
    if r.rc != (0 if want else 1):
        raise Fail(f"spell -p {prefix!r} should exit {0 if want else 1}:\n{r}")
    if words is None and not any(a.startswith("-d") for a in args):
        dict_path = f"{T._root(t)}/{DICT}"
        if T.have("look"):
            theirs = T.system(t, ["look", p, dict_path], check=False)
        else:
            theirs = T.run(t, "look", [p, dict_path], check=False)
        T.same(t, r.out, theirs.out, f"spell -p {prefix!r} (look)")
    return r


def distance(a, b):
    """Levenshtein's distance by the whole table: d[i][j] for the first i of b, first j of a."""
    d = [[0] * (len(a) + 1) for _ in range(len(b) + 1)]
    for j in range(len(a) + 1):
        d[0][j] = j
    for i in range(1, len(b) + 1):
        d[i][0] = i
        for j in range(1, len(a) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[j - 1] != b[i - 1]))
    return d[len(b)][len(a)]


def nearest(word, words, e=2, n=5):
    """The words -s prints for word (the distance is at least the difference in length, so words
    further apart than e in length are not worth the table)."""
    near = [(distance(word, w), w) for w in set(words) if abs(len(w) - len(word)) <= e]
    near = [(d, w) for d, w in near if d <= e]
    if not near:
        return []
    best = min(d for d, _ in near)
    out = sorted(w for d, w in near if d == best)
    return out if n == 0 else out[:n]


def nonwords(count, words, seed):
    have = set(words)
    rng = random.Random(seed)
    out = set()
    while len(out) < count:
        w = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(2, 10)))
        if w not in have:
            out.add(w)
    return sorted(out)


def bloom_formula(n, m, k):
    return (1 - math.exp(-k * n / m)) ** k


# ---------------------------------------------------------------- the project at each lesson

SENTENCE = "printf 'The cat sat on teh mat.\\n' | "


def timeline_steps(k):
    if k < (5, 1):
        return []
    steps = [T.sh_step(SENTENCE + "bin/spell", "teh\n"),
             T.sh_step(SENTENCE + "bin/spell --algo=list", "teh\n"),
             T.sh_step("bin/spell -p zygot < /dev/null", "zygote\nzygotes\n"),
             T.sh_step("bin/spell --algo=table -p zygot < /dev/null", "zygote\nzygotes\n"),
             T.sh_step("bin/spell -p qqq < /dev/null", "", 1)]
    if k < (5, 2):
        steps.append(T.sh_step("bin/spell --algo=bloom < /dev/null",
                               "spell: no --algo 'bloom' (have: list, table, trie)\n", 2))
    else:
        steps += [T.sh_step(SENTENCE + "bin/spell --algo=bloom", "teh\n"),
                  T.sh_step("bin/spell --algo=bloom -p ca < /dev/null",
                            "spell: a Bloom filter holds no words to list: -p needs --algo=trie, table "
                            "or list\n", 2)]
    if k < (5, 3):
        steps.append(T.sh_step("bin/spell -s < /dev/null", "spell: unknown option '-s'\n", 2))
    else:
        steps += [T.sh_step("printf 'speling\\n' | bin/spell -s", "speling: spelling spewing\n"),
                  T.sh_step("printf 'speling\\n' | bin/spell -s --near=scan --algo=list",
                            "speling: spelling spewing\n"),
                  T.sh_step("bin/spell --distance kitten sitting < /dev/null", "3\n")]
    return steps


def timeline_after(root, k):
    if k < (5, 1):
        return None
    book = T.data(root, "book.txt")
    for algo in ("trie", "table"):
        got = T.run(root, "spell", [f"--algo={algo}", book]).out.splitlines()
        if got != pipeline(root, book):
            raise Fail(f"bin/spell --algo={algo} on the book: not what tr | sort -u | comm -23 prints")
    words = dictionary(root)
    for prefix in ("hol", "zygot", "qu", "xyzzy"):
        got = T.run(root, "spell", ["-p", prefix], check=False).out.splitlines()
        if got != [w for w in words if w.startswith(prefix)]:
            raise Fail(f"bin/spell -p {prefix}: the wrong words")
    return "spell: the book's unknown words as comm finds them, and completions"
