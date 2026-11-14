"""07.01 Reading the benchmark

The full benchmark, against the baseline recorded in
tests/bench_baseline.json: this fails only if ./db has fallen behind
sqlite3 by a large factor (4x for speed, 1.5x for file size) compared
with when the baseline was taken. It compares ratios to sqlite3 on the
same machine, so a slower machine does not fail it.
"""

import json
import os
import sys

SPEED_SLACK = 4.0
SIZE_SLACK = 1.5


def test(t):
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "bench_baseline.json")) as f:
        base = json.load(f)
    out_json = os.path.join(t.tmp, "bench.json")
    t.run([sys.executable, os.path.join(t.root, "bench", "bench.py"), "--db", os.path.join(t.root, "db"),
           "--repeats", "1", "--json", out_json], timeout=1200)
    with open(out_json) as f:
        now = json.load(f)
    was = {w["name"]: w["ratio"] for w in base["workloads"]}
    problems = []
    for w in now["workloads"]:
        if w["name"] not in was:
            problems.append(f"{w['name']}: not in the baseline")
        elif w["ratio"] < was[w["name"]] / SPEED_SLACK:
            problems.append(f"{w['name']}: {w['ratio']:.2f}x sqlite3's speed, baseline {was[w['name']]:.2f}x")
    size, size_was = now["file_size"]["ratio"], base["file_size"]["ratio"]
    if size > size_was * SIZE_SLACK:
        problems.append(f"file size: {size:.2f}x sqlite3's, baseline {size_was:.2f}x")
    t.check(not problems, "./db regressed against the benchmark baseline:\n" + "\n".join(problems))
