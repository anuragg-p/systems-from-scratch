"""00.02 Measuring a database

The benchmark runs every workload on ./db and on sqlite3 and prints a
table of ops/sec and file size, stating the durability settings.
"""

import json
import os
import sys

WORKLOADS = ["insert, autocommit", "insert, one transaction", "point lookup by primary key",
             "range scan, 100 rows each", "lookup by secondary index", "update by key, one transaction",
             "delete by key, one transaction"]


def test(t):
    out_json = os.path.join(t.tmp, "bench.json")
    r = t.run([sys.executable, os.path.join(t.root, "bench", "bench.py"), "--quick",
               "--db", os.path.join(t.root, "db"), "--json", out_json], timeout=600)
    out = r.stdout
    for name in WORKLOADS + ["file size, bytes"]:
        t.check(name in out, f"the benchmark table has no row for {name!r}:\n{out}")
    for words in ["durability, the same on both sides", "synchronous=FULL", "fsync(2)", "warm-up", "median of 1"]:
        t.check(words in out, f"the benchmark must say {words!r}:\n{out}")
    with open(out_json) as f:
        res = json.load(f)
    t.check([w["name"] for w in res["workloads"]] == WORKLOADS, f"workloads: {[w['name'] for w in res['workloads']]}")
    for w in res["workloads"]:
        for e in ("db", "sqlite3"):
            t.check(w[e]["ops_per_sec"] > 0 and len(w[e]["seconds"]) == 1, f"{w['name']} {e}: {w[e]}")
    t.check(res["file_size"]["db"] > 0 and res["file_size"]["sqlite3"] > 0, f"file sizes: {res['file_size']}")
