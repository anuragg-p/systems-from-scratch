"""Random programs of chapter 1's language, run every way there is, against the reference.

    python3 tracks/lang/tests/fuzz.py [N] [--seed S] [--size K] [--jobs J] [--root DIR]

Builds the project (make -s in DIR, default the track), makes N programs with proggen.sample
(seed S, about K statements each; every one ends "ok" in the reference), and runs each every way
whose program is there: mote0, motec and its program, mote, mote -S then machine, mote -S -O then
machine. Each must exit 0 and print exactly what the reference printed. Prints the first five
disagreements whole, then a count; exit status 1 if there is any.
"""

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
TRACK = os.path.dirname(HERE)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Ctx:
    def __init__(self, root, tmp):
        self.root, self.tmp = root, tmp
        os.makedirs(tmp, exist_ok=True)


def ways_there(root):
    have = os.path.exists
    out = []
    if have(os.path.join(root, "mote0.c")):
        out.append("mote0")
    if have(os.path.join(root, "motec")):
        out.append("motec")
    if have(os.path.join(root, "interp.c")):
        out.append("mote")
    if have(os.path.join(root, "gen.c")):
        out.append("machine")
    if have(os.path.join(root, "improve.c")):
        out.append("machine -O")
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("n", nargs="?", type=int, default=500)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--size", type=int, default=14)
    ap.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--root", default=TRACK)
    a = ap.parse_args(argv)
    track = load(os.path.join(TRACK, "track.py"), "lang_track")
    gen = load(os.path.join(HERE, "proggen.py"), "lang_proggen")
    r = subprocess.run(["make", "-s"], cwd=a.root, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"make failed:\n{r.stdout}{r.stderr}")
    have = ways_there(a.root)
    t0 = time.monotonic()
    cases = gen.sample(a.seed, a.n, a.size)
    tmp = tempfile.mkdtemp(prefix="lang-fuzz-")
    free = [Ctx(a.root, os.path.join(tmp, f"w{i}")) for i in range(a.jobs)]
    lock = threading.Lock()
    bad = []

    def one(case):
        text, text_in, want = case
        with lock:
            ctx = free.pop()
        try:
            got = track.ways(ctx, text, text_in, have)
            wrong = {w: r for w, r in got.items() if r[0] != 0 or r[1] != want}
            if wrong:
                with lock:
                    bad.append((text, text_in, want, wrong))
        except track.Fail as e:
            with lock:
                bad.append((text, text_in, want, {"(fixture)": (None, str(e), "")}))
        finally:
            with lock:
                free.append(ctx)

    with ThreadPoolExecutor(a.jobs) as pool:
        list(pool.map(one, cases))
    shutil.rmtree(tmp, ignore_errors=True)
    for text, text_in, want, wrong in bad[:5]:
        print("---- program\n" + text + "---- input\n" + text_in + "---- the reference prints\n" + want)
        for w, (st, out, err) in wrong.items():
            print(f"---- {w}: status {st}\n{out}{err}")
    print(f"{len(cases)} programs (seed {a.seed}, size {a.size}), {len(have)} ways each "
          f"({', '.join(have)}): {len(bad)} disagree, {time.monotonic() - t0:.1f} s")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
