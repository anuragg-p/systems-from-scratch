#!/usr/bin/env python3
"""How a program's running time grows with its input.

    python3 bench/grow.py [options] COMMAND [ARG ...]
    ./learn bench dsa [--at NN.LL] [options] COMMAND [ARG ...]

It makes an input of n units with data/gen.py, runs COMMAND on it (the
input's path goes after the last ARG, or in place of an ARG that is {}),
and times it; then it doubles n and runs it again, until one run takes
longer than --limit seconds or n reaches --max. Each row says how long the
run took, and how many times longer than the run before: the ratio. If
twice the input takes twice as long, the ratio is 2, and the time grows as
n does. If it takes four times as long, the ratio is 4: the time grows as
n squared, and ten times the input takes a hundred times as long.

  --input KIND   the input: a kind of data/gen.py (default: text)
  --seed S       its seed (default 1)
  --start N      the first n (default 1000)
  --max N        the largest n (default 4194304)
  --limit S      stop after a run longer than S seconds (default 2)
  --repeat R     time each n R times and keep the fastest (default 3;
                 a run longer than a second is not repeated)
  --stdin        give the input on standard input, not as a file
  --json FILE    write the rows to FILE as well

COMMAND runs in this directory, with LC_ALL=C, its output thrown away:
bin/paste is this project's paste, paste the system's. An exit status of 0
or 1 is fine (look, grep and diff say 1 for "none" or "different"); 2 or
more, or a crash, stops the run. The times include starting the program,
so runs of a few milliseconds say little: a ratio is shown only when both
runs took 20 ms or more.
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_SECONDS = 0.02


def load_gen():
    import importlib.util
    path = os.path.join(os.path.dirname(HERE), "data", "gen.py")
    spec = importlib.util.spec_from_file_location("gen", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verdict(ratios):
    """What the ratios say: (the typical ratio, the power of n, words). ratios: those of the
    rows long enough to time; the last three count. (None, None, why) when there are none."""
    if not ratios:
        return None, None, "every run was too quick to time: try a larger --start, or --max"
    last = sorted(ratios[-3:])
    r = last[len(last) // 2]
    k = math.log2(r) if r > 0 else 0.0
    if k < 0.3:
        words = "about the same time whatever n is"
    elif 0.7 <= k <= 1.3:
        words = "about n: twice the input, twice the time"
    elif 1.7 <= k <= 2.3:
        words = "about n^2: twice the input, four times the time"
    elif 2.7 <= k <= 3.3:
        words = "about n^3: twice the input, eight times the time"
    else:
        words = f"about n^{k:.1f}"
    return r, k, words


def parse(argv):
    opts = {"input": "text", "seed": 1, "start": 1000, "max": 4194304, "limit": 2.0, "repeat": 3,
            "stdin": False, "json": None}
    i = 0
    while i < len(argv) and argv[i].startswith("--"):
        a = argv[i]
        if a == "--":
            i += 1
            break
        if a == "--stdin":
            opts["stdin"] = True
            i += 1
            continue
        name = a[2:]
        if name not in opts or i + 1 >= len(argv):
            raise SystemExit(f"grow.py: unknown option {a}\n\n{__doc__}")
        v = argv[i + 1]
        try:
            opts[name] = type(opts[name])(v) if opts[name] is not None else v
        except ValueError:
            raise SystemExit(f"grow.py: {a} {v}: not a number")
        i += 2
    if i >= len(argv):
        raise SystemExit(__doc__)
    return opts, argv[i:]


def time_once(argv, stdin_path, env):
    t0 = time.perf_counter()
    with open(stdin_path, "rb") if stdin_path else open(os.devnull, "rb") as inp:
        r = subprocess.run(argv, stdin=inp, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env)
    t = time.perf_counter() - t0
    if r.returncode not in (0, 1):
        err = r.stderr.decode("utf-8", "replace").strip()
        raise SystemExit(f"grow.py: {' '.join(argv)} failed (exit {r.returncode}):\n{err}")
    return t


def main(argv):
    opts, command = parse(argv)
    gen = load_gen()
    env = dict(os.environ, LC_ALL="C")
    env.pop("DS_STATS", None)
    rows = []
    shown = " ".join(command) + (" < input" if opts["stdin"] else " input")
    print(f"{shown}\ninput: {opts['input']} from data/gen.py, seed {opts['seed']}\n", flush=True)
    print(f"{'n':>9} {'bytes':>11} {'seconds':>9} {'ratio':>6}", flush=True)
    with tempfile.TemporaryDirectory(prefix="grow-") as tmp:
        n = opts["start"]
        while n <= opts["max"]:
            data = gen.make(opts["input"], n, opts["seed"])
            files = data if isinstance(data, (list, tuple)) else [data]
            paths = []
            for j, d in enumerate(files):
                p = os.path.join(tmp, f"input-{n}-{j + 1}")
                with open(p, "wb") as f:
                    f.write(d)
                paths.append(p)
            if opts["stdin"]:
                run, stdin_path = list(command), paths[0]
            elif "{}" in command:
                run, stdin_path = [x for c in command for x in (paths if c == "{}" else [c])], None
            else:
                run, stdin_path = list(command) + paths, None
            best = None
            for _ in range(max(1, opts["repeat"])):
                t = time_once(run, stdin_path, env)
                best = t if best is None else min(best, t)
                if t > 1.0:
                    break
            for p in paths:
                os.unlink(p)
            prev = rows[-1] if rows else None
            ratio = None
            if prev and prev["seconds"] >= MIN_SECONDS and best >= MIN_SECONDS:
                ratio = best / prev["seconds"]
            rows.append({"n": n, "bytes": sum(len(d) for d in files), "seconds": best, "ratio": ratio})
            print(f"{n:>9} {rows[-1]['bytes']:>11} {best:>9.3f} {'' if ratio is None else f'{ratio:.1f}':>6}",
                  flush=True)
            if best > opts["limit"]:
                break
            n *= 2
    r, k, words = verdict([row["ratio"] for row in rows if row["ratio"] is not None])
    print()
    if r is None:
        print(f"growth: {words}")
    else:
        print(f"growth: each doubling multiplies the time by about {r:.1f}: {words}")
    if opts["json"]:
        with open(opts["json"], "w") as f:
            json.dump({"command": command, "input": opts["input"], "seed": opts["seed"], "rows": rows,
                       "ratio": r, "power": k, "verdict": words}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
