#!/usr/bin/env python3
"""The benchmark: fixed workloads, run on ./db and on sqlite3, side by side.

    python3 bench/bench.py              (or: ./learn bench db)
    python3 bench/bench.py --quick      small and fast, to see that it works
    python3 bench/bench.py --wal        both engines in WAL mode instead
    options: --rows N  --repeats R  --db PATH  --sqlite PATH  --json FILE

Both engines get the same SQL text, fed to their shells on stdin, with the
same durability settings, which the output states. Every workload runs once
to warm up (the file system cache, the binaries), then --repeats times;
the table shows the median, and the spread of the runs is printed too.
Times are wall-clock for the whole process, start-up included (it is
measured and shown separately). Nothing is dropped or retried.
"""

import argparse
import json
import os
import platform
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

SCHEMA = "CREATE TABLE t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT);\n"
INDEX = "CREATE INDEX t_a ON t(a);\n"


def find_sqlite():
    """The newest sqlite3 we can find: $SQLITE3, Homebrew's, then PATH."""
    cands = []
    if os.environ.get("SQLITE3"):
        cands.append(os.environ["SQLITE3"])
    cands += ["/opt/homebrew/opt/sqlite/bin/sqlite3", "/usr/local/opt/sqlite/bin/sqlite3"]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        cands.append(os.path.join(d, "sqlite3"))
    cands.append("/usr/bin/sqlite3")
    best = None
    for c in cands:
        if not (os.path.isfile(c) and os.access(c, os.X_OK)):
            continue
        v = sqlite_version(c)
        if v and (best is None or v > best[0]):
            best = (v, c)
    return best[1] if best else None


def sqlite_version(path):
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", out)
    return tuple(int(x) for x in m.groups()) if m else None


def machine():
    cpu = platform.processor() or platform.machine()
    if sys.platform == "darwin":
        try:
            cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True,
                                 text=True, timeout=5).stdout.strip() or cpu
        except (OSError, subprocess.SubprocessError):
            pass
        osname = f"macOS {platform.mac_ver()[0]}"
    else:
        try:
            with open("/proc/cpuinfo") as f:
                m = re.search(r"model name\s*:\s*(.+)", f.read())
                cpu = m.group(1) if m else cpu
        except OSError:
            pass
        osname = f"{platform.system()} {platform.release()}"
    return f"{cpu}, {os.cpu_count()} cores, {osname}"


# ---------------------------------------------------------------- the workloads

def row(i):
    """Row i of the table: a is a scrambled number (distinct for every i up to
    a million), b a 34-byte text."""
    return i, (i * 7919) % 1000003, f"name {i:08d} xxxxxxxxxxxxxxxxxxxx"


def prelude(wal):
    mode = "WAL" if wal else "DELETE"
    return f"PRAGMA journal_mode={mode};\nPRAGMA synchronous=FULL;\nPRAGMA fullfsync=OFF;\n"


def inserts(lo, hi):
    return "".join("INSERT INTO t VALUES(%d, %d, '%s');\n" % row(i) for i in range(lo, hi))


def workloads(rows, quick):
    """(name, ops, setup, script): setup is "empty" (a new file with the
    table), "fresh" (a new file, nothing in it) or "base" (a copy of the
    file with every row and the index)."""
    rnd = random.Random(20261112)
    n_auto = 300 if quick else 10000
    n_scan = max(rows // 100, 10)
    n_change = max(rows // 10, 10)
    keys = [rnd.randint(1, rows) for _ in range(rows)]
    gone = rnd.sample(range(1, rows + 1), n_change)
    return [
        ("insert, autocommit", n_auto, "empty", inserts(1, n_auto + 1)),
        ("insert, one transaction", rows, "fresh", SCHEMA + "BEGIN;\n" + inserts(1, rows + 1) + "COMMIT;\n"),
        ("point lookup by primary key", rows, "base",
         "".join(f"SELECT * FROM t WHERE id = {k};\n" for k in keys)),
        ("range scan, 100 rows each", n_scan, "base",
         "".join(f"SELECT * FROM t WHERE id BETWEEN {k} AND {k + 99};\n" for k in keys[:n_scan])),
        ("lookup by secondary index", rows, "base",
         "".join(f"SELECT * FROM t WHERE a = {row(k)[1]};\n" for k in keys)),
        ("update by key, one transaction", n_change, "base",
         "BEGIN;\n" + "".join(f"UPDATE t SET b = 'changed {k}' WHERE id = {k};\n" for k in keys[:n_change]) + "COMMIT;\n"),
        ("delete by key, one transaction", n_change, "base",
         "BEGIN;\n" + "".join(f"DELETE FROM t WHERE id = {k};\n" for k in gone) + "COMMIT;\n"),
    ]


class Engine:
    def __init__(self, name, argv):
        self.name = name
        self.argv = argv

    def run(self, path, script_path, check=True):
        """Runs the script through the engine's shell and returns the seconds
        taken. With check, a non-zero exit or any output on stderr ends the
        benchmark."""
        with open(script_path, "rb") as f:
            t0 = time.perf_counter()
            r = subprocess.run(self.argv + [path], stdin=f, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            secs = time.perf_counter() - t0
        if check and (r.returncode != 0 or r.stderr.strip()):
            sys.exit(f"bench: {self.name} failed on {os.path.basename(script_path)} "
                     f"(exit {r.returncode}):\n{r.stderr.decode(errors='replace')[-2000:]}")
        return secs


def remove(path):
    for p in (path, path + "-journal", path + "-wal", path + "-shm"):
        if os.path.exists(p):
            os.unlink(p)


def copy_db(src, dst):
    remove(dst)
    shutil.copyfile(src, dst)


def main():
    ap = argparse.ArgumentParser(description="Benchmark ./db against sqlite3.")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--db", default=os.path.join(here, "db"))
    ap.add_argument("--sqlite", default=None)
    ap.add_argument("--rows", type=int, default=100000)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="2000 rows, one timed run")
    ap.add_argument("--wal", action="store_true", help="both engines in WAL mode")
    ap.add_argument("--json", default=None, help="also write the results here")
    args = ap.parse_args()
    if args.quick:
        args.rows = min(args.rows, 2000)
        args.repeats = 1
    sqlite = args.sqlite or find_sqlite()
    if not sqlite:
        sys.exit("bench: no sqlite3 found; install it or pass --sqlite PATH")
    if not os.path.exists(args.db):
        sys.exit(f"bench: no engine at {args.db}; build it first (make)")
    engines = [Engine("db", [os.path.abspath(args.db)]), Engine("sqlite3", [sqlite])]
    sver = subprocess.run([sqlite, "--version"], capture_output=True, text=True).stdout.split()[0]

    tmp = tempfile.mkdtemp(prefix="db-bench-")
    try:
        results = run_all(args, engines, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    mode = ("WAL (journal_mode=WAL; a checkpoint every 1000 pages)" if args.wal
            else "rollback journal (journal_mode=DELETE)")
    print(f"Benchmark: ./db against sqlite3 {sver} ({sqlite})")
    print(f"machine:   {machine()}")
    print(f"table:     t(id INTEGER PRIMARY KEY, a INTEGER, b TEXT), {args.rows} rows inserted in id order,")
    print("           an index on a; every statement is SQL text fed to the engine's shell on stdin")
    print(f"durability, the same on both sides: {mode}, synchronous=FULL:")
    print("           fsync(2) at every commit; F_FULLFSYNC off (fullfsync=OFF, sqlite3's default)")
    print(f"runs:      1 warm-up, then median of {args.repeats}; page size 4096, a 2000 KiB page cache each")
    print()
    print(f"{'workload':<32} {'ops':>8} {'db ops/s':>12} {'sqlite3 ops/s':>14} {'db/sqlite3':>11}"
          f"   {'spread db, sqlite3':>18}")
    for r in results["workloads"]:
        print(f"{r['name']:<32} {r['ops']:>8} {r['db']['ops_per_sec']:>12,.0f} "
              f"{r['sqlite3']['ops_per_sec']:>14,.0f} {r['ratio']:>10.2f}x"
              f"   {r['db']['spread']:>11.2f} {r['sqlite3']['spread']:>6.2f}")
    fs = results["file_size"]
    print(f"{'file size, bytes':<32} {'':>8} {fs['db']:>12,} {fs['sqlite3']:>14,} {fs['ratio']:>10.2f}x")
    print()
    print("spread: the slowest timed run over the fastest (1.00 when there is one run)")
    st = results["startup_ms"]
    print(f"process start-up, included in every time: db {st['db']:.1f} ms, sqlite3 {st['sqlite3']:.1f} ms")
    print("db/sqlite3 above 1 means ./db is faster; for file size, above 1 means ./db's file is bigger")
    results.update(sqlite3=sqlite, sqlite3_version=sver, machine=machine(), rows=args.rows,
                   repeats=args.repeats, wal=args.wal)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=1)


def run_all(args, engines, tmp):
    wal = args.wal
    work = workloads(args.rows, args.quick)
    scripts = {}
    for i, (name, ops, setup, sql) in enumerate(work):
        path = os.path.join(tmp, f"w{i}.sql")
        with open(path, "w") as f:
            f.write(prelude(wal) + sql)
        scripts[name] = path
    def script(name, text):
        path = os.path.join(tmp, name)
        with open(path, "w") as f:
            f.write(text)
        return path
    empty_s = script("empty.sql", prelude(wal) + SCHEMA)
    base_s = script("base.sql", prelude(wal) + SCHEMA + "BEGIN;\n" + inserts(1, args.rows + 1) + "COMMIT;\n" + INDEX)
    nothing_s = script("nothing.sql", "")

    out = {"workloads": [], "file_size": {}, "startup_ms": {}}
    base = {}
    for e in engines:
        # Set-up, not timed: the full table and its index, made by each engine itself.
        base[e.name] = os.path.join(tmp, f"base-{e.name}.db")
        remove(base[e.name])
        e.run(base[e.name], base_s)
        out["file_size"][e.name] = os.path.getsize(base[e.name])
        starts = []
        for _ in range(5):
            p = os.path.join(tmp, "startup.db")
            copy_db(base[e.name], p)
            starts.append(e.run(p, nothing_s))
        out["startup_ms"][e.name] = statistics.median(starts) * 1000
    out["file_size"]["ratio"] = out["file_size"]["db"] / out["file_size"]["sqlite3"]

    scratch = os.path.join(tmp, "run.db")
    for name, ops, setup, _ in work:
        entry = {"name": name, "ops": ops}
        for e in engines:
            def one():
                if setup == "base":
                    copy_db(base[e.name], scratch)
                else:
                    remove(scratch)
                    if setup == "empty":
                        e.run(scratch, empty_s)
                return e.run(scratch, scripts[name])
            one()                                   # warm-up
            times = [one() for _ in range(args.repeats)]
            med = statistics.median(times)
            entry[e.name] = {"seconds": times, "median": med, "ops_per_sec": ops / med,
                             "spread": max(times) / min(times)}
        entry["ratio"] = entry["db"]["ops_per_sec"] / entry["sqlite3"]["ops_per_sec"]
        out["workloads"].append(entry)
    return out


if __name__ == "__main__":
    main()
