"""00.02 Measuring growth

data/gen.py makes the same bytes for the same seed, on any machine, in the sizes asked for, with a
vocabulary that keeps growing; bench/grow.py runs a command on doubling inputs and reports n, bytes,
seconds and the ratio of each run to the one before, and reads the ratios as a power of n. The clock
itself is not tested: only what the harness does with it.
"""

import importlib.util
import json
import os
import re
import sys


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test(t):
    T = t.track
    gen = os.path.join(t.root, "data", "gen.py")
    grow = os.path.join(t.root, "bench", "grow.py")

    # the generator: the same seed, the same bytes; another seed, others; the size asked for
    one = T._exec([sys.executable, gen, "text", "3000", "--seed", "7"], None, T._env(), True, t.root, 60).raw
    two = T._exec([sys.executable, gen, "text", "3000", "--seed", "7"], None, T._env(), True, t.root, 60).raw
    other = T._exec([sys.executable, gen, "text", "3000", "--seed", "8"], None, T._env(), True, t.root, 60).raw
    t.check(one == two and one != other, "gen.py text 3000 --seed 7 must give the same bytes every time")
    t.check(len(re.findall(rb"[A-Za-z]+", one)) == 3000, "gen.py text 3000 must make 3000 words")
    t.check(all(b < 128 for b in one), "gen.py makes ASCII")
    g = load(gen, "gen_under_test")
    for kind in ("words", "lines", "sorted", "reversed", "same", "numbers", "fields", "dict"):
        data = g.make(kind, 500)
        lines = data.split(b"\n")
        t.check(data.endswith(b"\n") and len(lines) == 501, f"gen.py {kind} 500 must make 500 lines")
    for kind, want in (("sorted", sorted), ("reversed", lambda x: sorted(x, reverse=True))):
        lines = g.make(kind, 2000).split(b"\n")[:-1]
        t.check(lines == want(lines), f"gen.py {kind} is not in order")
    d = g.make("dict", 20000).split(b"\n")[:-1]
    t.check(d == sorted(set(d)) and len(d) == 20000, "gen.py dict 20000: 20000 different words, sorted")
    vocab = [len({w.lower() for w in re.findall(rb"[A-Za-z]+", g.make("text", n))}) for n in (20000, 40000)]
    t.check(vocab[1] > 1.4 * vocab[0], f"text's vocabulary must keep growing with n: {vocab}")

    # the harness: rows of doubling n, a ratio once both runs are long enough to time
    out = os.path.join(t.tmp, "rows.json")
    r = T._exec([sys.executable, grow, "--start", "500", "--max", "4000", "--repeat", "1", "--json", out,
                 "bin/paste", "-s", "--algo=end"], None, T._env(), True, t.root, 300)
    for words in ("bin/paste -s --algo=end input", "input: text from data/gen.py, seed 1", "n", "bytes",
                  "seconds", "ratio", "growth:"):
        t.check(words in r.out, f"grow.py's report has no {words!r}:\n{r.out}")
    with open(out) as f:
        rows = json.load(f)["rows"]
    t.check([row["n"] for row in rows] == [500, 1000, 2000, 4000], f"n must double from --start to --max: {rows}")
    t.check(all(rows[i]["bytes"] < rows[i + 1]["bytes"] for i in range(3)), f"the inputs must grow: {rows}")
    t.check(all(row["seconds"] > 0 for row in rows), f"every run is timed: {rows}")
    for row in rows[1:]:
        prev = rows[rows.index(row) - 1]["seconds"]
        long_enough = prev >= 0.02 and row["seconds"] >= 0.02
        t.check((row["ratio"] is not None) == long_enough, f"a ratio only between runs of 20 ms or more: {rows}")

    # the input in place of {}, or on standard input
    r = T._exec([sys.executable, grow, "--max", "1000", "--repeat", "1", "bin/freq", "-n", "3", "{}"], None,
                T._env(), True, t.root, 300)
    t.check("bin/freq -n 3 {} input" in r.out, f"grow.py with {{}}:\n{r.out}")
    r = T._exec([sys.executable, grow, "--max", "1000", "--repeat", "1", "--stdin", "bin/freq"], None,
                T._env(), True, t.root, 300)
    t.check("bin/freq < input" in r.out, f"grow.py --stdin:\n{r.out}")
    # a command that fails stops it, saying so
    r = T._exec([sys.executable, grow, "--max", "1000", "bin/paste"], None, T._env(), False, t.root, 300)
    t.check(r.rc != 0 and "failed" in r.err and "only paste -s" in r.err, f"grow.py on a failing command:\n{r}")

    # how the ratios are read
    v = load(grow, "grow_under_test").verdict
    t.check(v([3.9, 4.1, 4.0])[1] == 2.0 and "n^2" in v([3.9, 4.1, 4.0])[2], f"ratios of 4: {v([3.9, 4.1, 4.0])}")
    t.check("about n:" in v([2.0, 2.1, 1.9])[2], f"ratios of 2: {v([2.0, 2.1, 1.9])}")
    t.check("n^3" in v([8.0, 8.2, 7.9])[2], f"ratios of 8: {v([8.0, 8.2, 7.9])}")
    t.check(v([1.0, 1.1, 0.9])[2].startswith("about the same time"), f"ratios of 1: {v([1.0, 1.1, 0.9])}")
    t.check(v([4.0, 4.0, 2.0, 2.0, 2.0])[0] == 2.0, "only the last three ratios count")
    t.check(v([])[0] is None, "no ratios: no verdict")
