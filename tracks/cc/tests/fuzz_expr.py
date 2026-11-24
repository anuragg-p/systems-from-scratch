"""Random expressions through ./cc, gcc and Python: a longer run than 02.06's test, by hand.

    python3 tracks/cc/tests/fuzz_expr.py [-n 5000] [--seed 1] [--depth 9] [--batch 20] [--jobs 8]
                                         [--root DIR] [--sanitize]

Each expression comes from exprgen.py with its value by C's rules for int (expressions C
leaves undefined are not made). They go in batches: one program per batch, the sum of
"(e) == (v)" over its expressions, built by ./cc and by gcc for the same machine and run on
QEMU, must return the batch's size from both; that checks every expression's whole 64-bit value
from ./cc and its 32-bit value from gcc. A batch that fails is checked an expression at a time
with the fixtures' value() (status as gcc's, and all 64 bits), and those that fail are printed.

--root is the project to test (default: the track itself, after make). --sanitize builds ./cc
with AddressSanitizer and UndefinedBehaviorSanitizer for the run, as CC_SANITIZE=1 does for the
tests. Exits 0 when everything agreed, 1 otherwise.
"""

import argparse
import importlib.util
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--depth", type=int, default=9)
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--root", default=os.path.dirname(HERE))
    ap.add_argument("--sanitize", action="store_true")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    if subprocess.run(["make", "-s"], cwd=root).returncode != 0:
        sys.exit("make failed")
    if a.sanitize:
        os.environ["CC_SANITIZE"] = "1"
    tr = load("cc_track", os.path.join(os.path.dirname(HERE), "track.py"))
    g = load("cc_exprgen", os.path.join(HERE, "exprgen.py"))
    tr.tools()

    t0 = time.time()
    trees = g.sample_trees(a.seed, a.n, a.depth)
    exprs = [(e, v) for _, e, v in trees]
    spills = sum(1 for t, _, _ in trees if g.registers(t) > 6)
    batches = [exprs[i:i + a.batch] for i in range(0, len(exprs), a.batch)]
    tmp = tempfile.mkdtemp(prefix="cc-fuzz-")
    free = queue.Queue()
    for i in range(a.jobs):
        free.put(tr.Scratch(root, os.path.join(tmp, f"w{i}")))

    def one_batch(batch):
        ctx = free.get()
        try:
            prog = " + ".join(f"(({e}) == ({tr.c_int(v)}))" for e, v in batch)
            try:
                ours = tr.run(ctx, prog)[0]
                gccs = tr.gcc_run(ctx, prog)[0]
                if ours == gccs == len(batch):
                    return []
            except tr.Fail:
                pass
            bad = []
            for e, v in batch:
                try:
                    tr.value(ctx, e, v)
                except tr.Fail as err:
                    bad.append(f"{e}\n    want {v}: {err}")
            # Each passed alone, but the batch, itself one expression whose terms sit a register
            # deeper, did not: that is a failure too.
            return bad or [f"the batch as one expression (each of its expressions passed alone):\n{prog}"]
        finally:
            free.put(ctx)

    failures = []
    done = 0
    with ThreadPoolExecutor(a.jobs) as pool:
        for bad in pool.map(one_batch, batches):
            failures += bad
            done += 1
            if done % 25 == 0 or done == len(batches):
                print(f"{done * a.batch if done < len(batches) else len(exprs)} of {len(exprs)} expressions, "
                      f"{len(failures)} failed, {time.time() - t0:.0f} s", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    for f in failures[:20]:
        print("FAIL", f)
    print(f"{len(exprs)} expressions (seed {a.seed}, depth {a.depth}; {spills} need more than six registers, "
          f"so spill), {len(failures)} failed, in {time.time() - t0:.1f} s")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
