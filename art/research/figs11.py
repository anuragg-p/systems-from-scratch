"""Figures for research module 11, Fast (lessons 11.01-11.06).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs11.py [11.02 ...]
                                    all of them, or those whose name starts so (DIR keeps the runs)

Every dot, bar, curve and number comes from the reference code (tracks/research), run as the page runs
it, from SmolLM2's fetched files, or from the recorded benchmark 11.06 reads. A time moves with the
machine's load, so a figure of times is one run's, drawn with the load the code printed beside it (the
pages' prose gives the times NOTES.md records, each with its load). Steps, bits and counts do not move;
where a figure computes one of those that a run prints, it stops if the two differ:

  11.01  python3 -m experiments.benchmark (the page's run): every seed's log and summary, times.json and
         what it printed (the steps and the ratio must be the summaries' and times.json's); the step timed
         in 3 rounds in the project at 11.01 (benchmark.py's step_timer, lab/bench.py's timings), twice:
         as the machine is, and with 10 more processes spinning beside it
  11.02  python3 -m experiments.profile (the page's run): its three parts as printed (the parts must add
         up to the step)
  11.03  python3 -m experiments.fused (the page's run); what autograd keeps for attention at 256 places,
         tensor by tensor, in the project at 11.03 (the totals must be fused.py's kept_bytes and the run's);
         the recorded benchmark's baseline and fused rows
  11.04  python3 -m experiments.precision (the page's run); one AdamW step's updates made as its part 1
         makes them, in the project at 11.04 (lost() and the bfloat16 count must give the run's shares);
         the recorded benchmark's ms a step
  11.05  python3 -m experiments.batches (the page's run); a batch of 32 cut into 4 parts in float64, and
         the gradient's length over 40 steps (batches.py's accumulated and norms), in the project at 11.05
         (the medians and the counts must be the run's)
  11.06  python3 -m experiments.cache (the page's run); written() step by step with SmolLM2 in the project
         at 11.06 (the same tokens with the cache and without); experiments/recorded/benchmark/ (every
         row's summaries and times.json, against its output.txt)

Needs PyTorch and SmolLM2's files (python3 -m data.fetch smollm2, in tracks/research). The runs take
about six minutes in all on the machine in NOTES.md, one of them on purpose on a busier machine;
RESEARCH_FIGS_CACHE keeps them between processes.
"""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
import figart  # noqa: E402
import figlib  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "11"
REC = os.path.join(figlib.TRACK, "experiments", "recorded", "benchmark")
ROWS = ["baseline", "angles kept", "fused attention", "bfloat16", "twice the batch and rate", "all together"]
TEXT = {"a": "ta", "s": "t", "m": "tm"}
_memo = {}


def in_project(at, code, busy=0):
    """Run python code in the project as it stands at lesson `at`, in a fresh python; the JSON it prints
    last. With busy=n, n processes that do nothing but spin are started 30 s before it and stopped after,
    so the code runs on a busier machine. Once per process; kept in RESEARCH_FIGS_CACHE when that is set
    (keyed by the code and the project's sources)."""
    key = (at, code, busy)
    if key in _memo:
        return _memo[key]
    cache = os.environ.get("RESEARCH_FIGS_CACHE")
    path = None
    if cache:
        tag = hashlib.sha256(repr((key, figart._sources_hash())).encode()).hexdigest()[:16]
        path = os.path.join(os.path.abspath(cache), f"project-{at}-{tag}.json")
        if os.path.isfile(path):
            with open(path) as f:
                _memo[key] = json.load(f)
            return _memo[key]
    d = figart.project(at)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d)
    spinners = [subprocess.Popen([sys.executable, "-c", "while True: pass"]) for _ in range(busy)]
    try:
        if busy:
            time.sleep(30)
        r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    finally:
        for p in spinners:
            p.kill()
            p.wait()
    if r.returncode != 0:
        raise SystemExit(f"python in the project at {at} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    _memo[key] = json.loads(r.stdout.strip().splitlines()[-1])
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(_memo[key], f)
    return _memo[key]


def mean(xs):
    return sum(xs) / len(xs)


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def welch(a, b):
    return (mean(a) - mean(b)) / math.sqrt(sd(a) ** 2 / len(a) + sd(b) ** 2 / len(b))


def same(what, ours, printed):
    """Stop the generator when a number it computed is not the one the run printed."""
    if ours != printed:
        raise SystemExit(f"{what}: computed here {ours!r}, the run printed {printed!r}")


def find(out, regex, flags=re.M):
    m = re.search(regex, out, flags)
    if not m:
        raise SystemExit(f"no {regex!r} in:\n{out[-1500:]}")
    return m


def label(name):
    return name.replace(" ", "-")


def chip(f, x, y, w, h, cls, s, tcls, size=10.5, weight=None, mono=False):
    """A filled box with one centred line, its text left out when it does not fit."""
    f.rect(x, y, w, h, cls, 2)
    if tw(s, size, mono) + 6 <= w:
        f.text(x + w / 2, y + h / 2 + size * 0.36, s, tcls, size, "middle", weight, mono)


def loglabel(v):
    """A tick on a log axis of ms or MiB: 0.1, 1, 10, 100, 1,000."""
    return f"{v:,.0f}" if v >= 1 else f"{v:g}"


# ================================================================== 11.01

def bench_run():
    return figart.experiment("benchmark", at="11.01")


STEP_CODE = r'''
import json, torch, lab
from lab import bench
from data import shakespeare
from experiments.benchmark import CONFIG, ALL_FOUR, step_timer
from models.gpt import GPT
cfg = lab.Config(CONFIG)
dev = lab.device(torch, cfg.device)
clock = lambda: lab.clock(torch, dev)
V = len(shakespeare.chars())
train_t = torch.from_numpy(shakespeare.split("train")).to(dev)
torch.manual_seed(0)
model = GPT(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
            kv_heads=cfg.kv_heads, **ALL_FOUR).to(dev)
step = step_timer(model, cfg, dev, train_t)
first = bench.load_average()
cold = bench.timings(step, clock, repeats=1, warmup=0)[0]
rounds, loads = [], []
for r in range(cfg.rounds):
    rounds.append(bench.timings(step, clock, repeats=cfg.repeats, warmup=1, number=cfg.number))
    loads.append(bench.load_average())
print(json.dumps({"cold": cold, "rounds": rounds, "loads": [first] + loads, "repeats": cfg.repeats,
                  "number": cfg.number}))
'''


def repeats1101():
    runs = [("as the machine was", in_project("11.01", STEP_CODE)),
            ("with 10 more processes spinning beside it", in_project("11.01", STEP_CODE, busy=10))]
    f = Fig("repeats1101", "One training step of the page's GPT timed in 3 rounds of 5 timings of 5 steps, as the "
                           "machine was and again with 10 more processes spinning beside it: every timing a ring, the "
                           "smallest, the median and the largest of the 15 marked, and the first step of each process "
                           "apart", 330)
    allms = [1000 * t for _, r in runs for rd in r["rounds"] for t in rd] + [1000 * r["cold"] for _, r in runs]
    bottom, top = min(allms) * 0.85, max(allms) * 1.1          # a log axis: one slow timing does not hide the rest
    x0, x1 = 104, 612
    X = lambda v: x0 + math.log(v / bottom) / math.log(top / bottom) * (x1 - x0)  # noqa: E731
    stats = []
    for k, (name, r) in enumerate(runs):
        y = 22 + k * 142
        ms = [1000 * t for rd in r["rounds"] for t in rd]
        lo, mid, hi = min(ms), median(ms), max(ms)
        stats.append((lo, mid, hi))
        load = f"load {min(r['loads']):.1f} to {max(r['loads']):.1f}"
        f.text(20, y, f"{name} ({load})", "ta" if k else "t", 12, weight=700)
        for i, rd in enumerate(r["rounds"]):
            yy = y + 22 + i * 15
            f.text(x0 - 10, yy + 3.5, f"round {i + 1}", "tm", 10, "end")
            for t in rd:
                f.circle(X(1000 * t), yy, 3.2, "s f")
        base = y + 76
        f.line(x0, base, x1, base, "m")
        for v in [t for t in (10, 15, 20, 30, 40, 50, 70, 100, 150, 200, 300, 500, 1000) if bottom <= t <= top]:
            f.line(X(v), base, X(v), base + 4, "m")
            f.text(X(v), base + 16, str(v), "tm", 10, "middle", mono=True)
        for v, cls in ((lo, "a"), (mid, "s"), (hi, "m")):
            f.line(X(v), y + 12, X(v), base, cls, dash=cls != "a")
        cx = X(1000 * r["cold"])
        f.rect(cx - 3.5, y + 18, 7, 7, "m fs", 1)
        f.text(cx, y + 14, "first step", "tm", 9.5, "middle")
        f.text(x0, base + 34, f"smallest {sig(lo)} ms", "ta", 10.5, weight=700, mono=True)
        f.text(x0 + 140, base + 34, f"median {sig(mid)}", "t", 10.5, mono=True)
        f.text(x0 + 250, base + 34, f"largest {sig(hi)}", "tm", 10.5, mono=True)
        f.text(x1, base + 34, f"the largest {hi / lo:.2f} times the smallest", "tm", 10.5, "end")
    (lo0, mid0, _), (lo1, mid1, _) = stats
    f.text(20, 322, f"ms a step, on a log scale. With the machine busier the smallest moved x{lo1 / lo0:.2f} and the median "
                    f"x{mid1 / mid0:.2f}.", "tm", 10.5)
    return f


def target_rows():
    """The page's run: for baseline and half the batch, each seed's log, steps and seconds to the target
    and ms a step, checked against what it printed."""
    r = bench_run()
    with open(os.path.join(r.runs, "times.json")) as fh:
        times = json.load(fh)
    target = figart.config(figart.seed_dirs(os.path.join(r.runs, "baseline"))[0])["target"]
    rows = {}
    for name in ("baseline", "half the batch"):
        dirs = figart.seed_dirs(os.path.join(r.runs, label(name)))
        steps = [figart.summary(d)["steps_to_target"] for d in dirs]
        m = find(r.out, rf"^   {re.escape(name)} +\S+ \+- \S+ \(min .*\) +(\d+) ")
        same(f"{name}'s steps", f"{mean(steps):.0f}", m.group(1))
        rows[name] = {"logs": [figart.read_log(d) for d in dirs], "steps": steps, "seconds": times[name]["seconds"],
                      "ms": times[name]["ms"]}
    ratio = mean(rows["half the batch"]["seconds"]) / mean(rows["baseline"]["seconds"])
    same("the ratio", f"x{ratio:.2f}", find(r.out, r"^   half the batch .* (x\d\.\d\d) \(t").group(1))
    load = float(find(r.out, r"seeds a row \(load ([\d.]+)\)").group(1))
    return rows, target, load


def target1101():
    rows, target, load = target_rows()
    f = Fig("target1101", "Half the batch against the baseline, 2 seeds each, the page's run: bits on the 32 "
                          "validation windows against the steps taken, and against the seconds of training (steps "
                          "times each seed's ms a step); the dot where each seed reaches the target", 300)
    style = {"baseline": "s", "half the batch": "a"}
    for p, (xlabel, xof) in enumerate((("steps", lambda st, ms: st + 1),
                                       ("seconds of training", lambda st, ms: (st + 1) * ms / 1000))):
        series = []
        for name, r in rows.items():
            for s, (log, ms) in enumerate(zip(r["logs"], r["ms"])):
                xs = [xof(row["step"], ms) for row in log]
                series.append(figart.Series(name if s == 0 else "", xs, [row["held_bits"] for row in log],
                                            style[name], dash=s == 1, width=1.5))
        x = 8 + p * 316
        xmax = 320 if p == 0 else 8.0
        ax = figart.plot(f, (x, 8, 308, 256), series, xlabel=xlabel, ylabel="bits, validation" if p == 0 else "",
                         xlim=(0, xmax), ylim=(2.8, 4.6), yticks=[3.0, 3.5, 4.0, 4.5], legend=None)
        ax.hline(target, f"the target, {target}", "m", side="left")
        for name, r in rows.items():
            for st, sec, ms in zip(r["steps"], r["seconds"], r["ms"]):
                ax.dot(st if p == 0 else sec, target, "a fa" if style[name] == "a" else "s f", 3.5)
            v = mean(r["steps"]) if p == 0 else mean(r["seconds"])
            ax.note(0.42 * xmax, 4.3 if name == "baseline" else 4.48, f"{name}: {v:.0f} steps" if p == 0 else
                    f"{name}: {v:.2f} s", TEXT[style[name]], 10.5, weight=600)
    f.text(16, 292, f"Steps are the same on any machine; the seconds are this run's (load {load:.1f}). Solid: seed 0, "
                    "dashed: seed 1.", "tm", 10.5)
    return f


def crossing1101():
    rows, target, _ = target_rows()
    base = rows["baseline"]
    log, steps, seconds = base["logs"][0], base["steps"][0], base["seconds"][0]
    k = next(i for i, row in enumerate(log) if row["held_bits"] <= target)
    (s0, b0), (s1, b1) = (log[k - 1]["step"], log[k - 1]["held_bits"]), (log[k]["step"], log[k]["held_bits"])
    frac = (b0 - target) / (b0 - b1)
    ours = s0 + 1 + frac * (s1 - s0)
    if abs(ours - steps) > 1e-9:
        raise SystemExit(f"the crossing: computed here {ours}, summary.json has {steps}")
    f = Fig("crossing1101", "bench.time_to on the baseline's seed 0: its held-out bits are logged every 10 steps, and "
                            "the target is crossed between two rows; the crossing is put on the straight line from one "
                            "to the other, in steps and in seconds alike", 300)
    near = [row for row in log if s0 - 30 <= row["step"] <= s1 + 30]
    lo = min(row["held_bits"] for row in near)
    hi = max(row["held_bits"] for row in near)
    ax = figart.Axes(f, 70, 30, 360, 200, (s0 - 32, s1 + 32), (lo - 0.02, hi + 0.02))
    ax.draw(xlabel="step (the row's step + 1 have been taken)", ylabel="bits, validation",
            xticks=[row["step"] for row in near][::2], yticks=None, xfmt=lambda v: str(int(v)))
    ax.hline(target, f"target {target}", "m", side="left")
    ax.curve([row["step"] for row in near], [row["held_bits"] for row in near], "m", width=1)
    ax.curve([s0, s1], [b0, b1], "a", width=2)
    for row in near:
        on = row["step"] in (s0, s1)
        ax.dot(row["step"], row["held_bits"], "a fa" if on else "s f", 4 if on else 3)
    ax.dot(ours - 1, target, "a fa", 5)
    ax.note(s0, b0, f"step {s0}: {b0:.4f}", "ta", 10.5, dx=8, dy=-8, weight=600)
    ax.note(s1, b1, f"step {s1}: {b1:.4f}", "ta", 10.5, dx=10, dy=4, weight=600)
    x = 460
    f.text(x, 50, "the crossing", "ta", 11.5, weight=700)
    f.text(x, 70, f"f = ({b0:.4f} - {target}) /", "t", 10.5, mono=True)
    f.text(x, 85, f"    ({b0:.4f} - {b1:.4f})", "t", 10.5, mono=True)
    f.text(x, 100, f"  = {frac:.3f}", "t", 10.5, mono=True)
    f.text(x, 124, f"steps: {s0} + 1 + f x {s1 - s0}", "t", 10.5, mono=True)
    f.text(x, 139, f"     = {ours:.1f}", "ta", 10.5, weight=700, mono=True)
    f.text(x, 163, "seconds: the same f between", "t", 10.5)
    f.text(x, 178, "the clock at the two rows", "t", 10.5)
    f.text(x, 193, f"     = {seconds:.2f} s", "ta", 10.5, weight=700, mono=True)
    f.text(20, 292, "A run under the target at its first row counts that row's steps; one that never reaches it, "
                    "None.", "tm", 10.5)
    return f


# ================================================================== 11.02

def prof_run():
    return figart.experiment("profile", at="11.02")


PARTS = ["data", "forward", "backward", "clipping", "optimiser"]
FORWARD = ["embedding", "norms", "attention: q, k, v and out", "attention: rotary", "attention: the rest", "MLP",
           "adds and dropout", "the last norm", "scores and loss"]


def profiled():
    out = prof_run().out
    shares = {m.group(1).strip(): float(m.group(2))
              for m in re.finditer(r"^ {3,5}(\S.*?) +(-?[\d.]+) +-?[\d.]+%$", out, re.M)}
    step = float(find(out, r"^   the step +([\d.]+)$").group(1))
    whole = sum(shares[k] for k in PARTS)
    if abs(whole - step) > 0.02:
        raise SystemExit(f"the parts add up to {whole}, the run printed {step}")
    fwd = sum(shares[k] for k in FORWARD)
    if abs(fwd - shares["forward"]) > 0.02:
        raise SystemExit(f"the forward pieces add up to {fwd}, the forward is {shares['forward']}")
    load = float(find(out, r"plain timers, the mean of \d+ steps on \w+ \(load ([\d.]+)\)").group(1))
    under = {m.group(1).strip(): tuple(float(m.group(k)) for k in (2, 3, 4)) for m in re.finditer(
        r"^   (\S.*?) +profiler +([\d.]+) +plain timers, under it +([\d.]+) +not under it +([\d.]+)$", out, re.M)}
    m = find(out, r"Under it a step takes ([\d.]+) ms by the plain timers \(([\d.]+) without it\):\n   it records "
                  r"([\d,]+) operations a step")
    ops = [(m2.group(1), int(m2.group(2)), float(m2.group(3)), float(m2.group(4)))
           for m2 in re.finditer(r"^   aten::(\S+) +(\d+) +([\d.]+) +([\d.]+)%$", out, re.M)]
    total = float(find(out, r"share of all ([\d.]+) ms of operations").group(1))
    places = {}
    for m3 in re.finditer(r"^   (attention|attention: rotary|MLP|norms|backward|optimiser) ([\d.]+): (.*)$", out, re.M):
        places[m3.group(1)] = (float(m3.group(2)), [(a, float(b), int(c.replace(",", "")))
                                                    for a, b, c in re.findall(r"(\S+) ([\d.]+) \(([\d,]+)\)", m3.group(3))])
    return {"shares": shares, "step": step, "load": load, "under": under, "under_step": float(m.group(1)),
            "ops_count": int(m.group(3).replace(",", "")), "ops": ops, "ops_total": total, "places": places, "out": out}


def step1102():
    p = profiled()
    s, step = p["shares"], p["step"]
    f = Fig("step1102", "One training step of the page's GPT taken apart by plain timers (hooks on its layers, the "
                        "clock around the rest), the mean of 10 steps: the forward pass by piece, the backward pass, "
                        "the clipping and the optimiser, as shares of the step", 300)
    x0, x1, y = 20, 620, 70
    X = lambda v: x0 + v / step * (x1 - x0)  # noqa: E731
    pieces = [("data", "m fs")] + [(k, "a af" if k.startswith("attention") else "s f") for k in FORWARD] + \
             [("backward", "s fs"), ("clipping", "m fs"), ("optimiser", "m fs")]
    at = 0.0
    spans = {}
    for k, cls in pieces:
        w = s[k]
        f.rect(X(at), y, X(at + w) - X(at), 34, cls, 0)
        spans[k] = (at, at + w)
        at += w
    fa, fb = s["data"], s["data"] + s["forward"]
    f.brace_h(X(fa), X(fb), y - 8, "s", up=True)
    f.text((X(fa) + X(fb)) / 2, y - 18, f"forward {s['forward']:.1f} ms, {100 * s['forward'] / step:.0f}%", "t", 11,
           "middle", 700)
    ba, bb = spans["backward"]
    f.brace_h(X(ba), X(bb), y - 8, "s", up=True)
    f.text((X(ba) + X(bb)) / 2, y - 18, f"backward {s['backward']:.1f} ms, {100 * s['backward'] / step:.0f}%", "t", 11,
           "middle", 700)
    oa, ob = spans["optimiser"]
    f.text(X(ob), y + 50, f"optimiser {s['optimiser']:.1f}", "tm", 10, "end")
    att = s["attention: q, k, v and out"] + s["attention: rotary"] + s["attention: the rest"]
    a0 = spans["attention: q, k, v and out"][0]
    f.brace_h(X(a0), X(a0 + att), y + 42, "a")
    f.text(X(a0), y + 62, f"attention {att:.1f} ms", "ta", 10.5, weight=700)
    rows = [(k, s[k]) for k in FORWARD]
    f.text(20, 162, "the forward pass, piece by piece (ms a step, share of the step)", "t", 11, weight=700)
    for i, (k, v) in enumerate(rows):
        col, row = divmod(i, 5)
        xx, yy = 20 + col * 310, 182 + row * 18
        tcls = "ta" if k.startswith("attention") else "t"
        f.text(xx, yy, k, tcls, 10.5, weight=600 if tcls == "ta" else None)
        f.text(xx + 230, yy, f"{v:.2f}", tcls, 10.5, "end", mono=True)
        f.text(xx + 284, yy, f"{100 * v / step:.1f}%", "tm", 10.5, "end", mono=True)
    f.text(20, 292, f"The step {step:.1f} ms with the timers (load {p['load']:.1f}); the backward pass takes "
                    f"{s['backward'] / s['forward']:.2f} times the forward's.", "tm", 10.5)
    return f


def profiler1102():
    p = profiled()
    keys = ["forward", "attention", "attention: rotary", "MLP", "norms", "backward", "optimiser"]
    f = Fig("profiler1102", "PyTorch's profiler beside the plain timers, ms a step for each piece: the timers on steps "
                            "without the profiler, the same timers on steps under it, and the profiler's own times for "
                            "those steps", 316)
    top = max(max(p["under"][k]) for k in keys) * 1.12
    x0, x1 = 150, 470
    X = lambda v: x0 + v / top * (x1 - x0)  # noqa: E731
    kinds = [("the plain timers, no profiler", "s f", "t", 2), ("the plain timers, under it", "s fs", "t", 1),
             ("the profiler", "a af", "ta", 0)]
    for i, k in enumerate(keys):
        y = 30 + i * 36
        f.text(x0 - 10, y + 15, k, "ta" if k.startswith("attention") else "t", 11, "end", 600)
        for j, (_, cls, tcls, col) in enumerate(kinds):
            v = p["under"][k][col]
            f.rect(x0, y + j * 9, X(v) - x0, 8, cls, 1, dash=j == 1)
        f.text(X(max(p["under"][k])) + 6, y + 14, f"{p['under'][k][2]:.2f} without, {p['under'][k][0]:.2f} under it",
               "tm", 9.5, mono=True)
    for v in range(0, int(top) + 1, 5):
        f.line(X(v), 282, X(v), 286, "m")
        f.text(X(v), 298, str(v), "tm", 10, "middle", mono=True)
    f.line(x0, 282, x1, 282, "m")
    xx = 420
    for j, (name, cls, tcls, _) in enumerate(kinds):
        f.rect(xx, 100 + j * 16, 12, 9, cls, 1, dash=j == 1)
        f.text(xx + 18, 108 + j * 16, name, tcls, 10.5)
    over = p["under_step"] - p["step"]
    f.text(20, 312, f"Under it a step took {p['under_step']:.1f} ms, not {p['step']:.1f} (+{100 * over / p['step']:.0f}%), "
                    f"for {p['ops_count']:,} operations a step; its pieces are the timers' under it.", "tm", 10.5)
    return f


def ops1102():
    p = profiled()
    att = p["places"]["attention"][1]
    sel = next(n for name, _, n in att if name == "select")
    back = p["places"]["backward"][1]
    bmmb = next((n, v) for name, v, n in back if name == "BmmBackward0")
    f = Fig("ops1102", "The operations with the most time of their own in a step, under the profiler: how many calls a "
                       "step and ms; in the accent, the ones attention's batched product and its backward pass make", 330)
    ops = p["ops"]
    top = max(v for _, _, v, _ in ops) * 1.1
    x0, x1 = 110, 290
    X = lambda v: x0 + v / top * (x1 - x0)  # noqa: E731
    lit = {"bmm", "select", "as_strided"}
    for i, (name, calls, ms, share) in enumerate(ops):
        y = 24 + i * 20
        on = name in lit
        f.text(x0 - 8, y + 11, name, "ta" if on else "t", 10.5, "end", 600 if on else None, mono=True)
        f.rect(x0, y + 2, X(ms) - x0, 12, "a af" if on else "s fs", 1)
        f.text(X(ms) + 6, y + 12, f"{ms:.2f} ms, {calls:,} calls", "ta" if on else "tm", 10, mono=True)
    x = 462
    lines = [("attention's scores and sums:", "t", 700), ("32 windows x 4 heads: 128", "t", None),
             ("matrices of 64 x 16 a block,", "t", None), ("one at a time on this CPU:", "t", None), None,
             (f"{sel:,} aten::select", "ta", 700), ("in attention's forward pass,", "ta", None), None,
             (f"{bmmb[0]:,} operations under", "ta", 700), (f"BmmBackward0, {bmmb[1]:.2f} ms,", "ta", None),
             ("in the backward pass.", "ta", None), None,
             ("Next: mul, sum, copy_, add_,", "t", 700), ("each a pass over memory:", "t", None),
             ("the turning, the norms, the", "t", None), ("gate, and their gradients.", "t", None)]
    y = 40
    for line in lines:
        if line is None:
            y += 6
            continue
        s, cls, wt = line
        f.text(x, y, s, cls, 10.5, weight=wt)
        y += 15
    f.text(20, 322, f"All operations' own time: {p['ops_total']:.1f} ms a step under the profiler.", "tm", 10.5)
    return f


def rotary1102():
    p = profiled()
    out = p["out"]
    m = find(out, r"The angles alone: ([\d.]+) microseconds a call, ([\d.]+) ms a step, ([\d.]+)% of it; the turning, "
                  r"forward and backward,\n   ([\d.]+) ms a block \(queries and keys\), ([\d.]+) ms a step, ([\d.]+)% of it")
    us, ang_ms, ang_pc, blk, turn_ms, turn_pc = (float(g) for g in m.groups())
    same_bits = find(out, r"bit for bit: (\w+)").group(1)
    timed = {}
    for name in ("made every call", "kept"):
        g = find(out, rf"^   {name} +a step ([\d.]+) ms \(median ([\d.]+), largest ([\d.]+), (\d+) repeats, load ([\d.]+)\)$")
        timed[name] = tuple(float(v) for v in g.groups())
    ratio = find(out, r"the smallest of each: ([+-][\d.]+) ms a step, x([\d.]+)").group(2)
    step = p["step"]
    f = Fig("rotary1102", "What 10.02 suspected, measured: rotary's angles made again on every call, against the "
                          "turning itself (forward and backward, every block's queries and keys), as shares of the "
                          "step; then the step with the angles kept against made every call", 300)
    x0, x1, y = 20, 620, 56
    X = lambda v: x0 + v / 100 * (x1 - x0)  # noqa: E731
    f.text(x0, 20, f"the step, {step:.1f} ms = 100%", "t", 11.5, weight=700)
    f.rect(x0, y, x1 - x0, 30, "m fs", 0)
    f.rect(X(0), y, X(turn_pc) - X(0), 30, "a af", 0)
    f.rect(X(0), y, max(2.0, X(ang_pc) - X(0)), 30, "a fa", 0)
    f.text(X(turn_pc) + 6, y + 19, "everything else", "tm", 10.5)
    f.line(X(ang_pc / 2), y + 30, X(ang_pc / 2) + 30, y + 58, "a")
    f.text(X(ang_pc / 2) + 34, y + 62, f"the angles: {ang_pc:.1f}% ({us:.1f} microseconds a call, 8 calls)", "ta",
           10.5, weight=700)
    f.brace_h(X(0), X(turn_pc), y - 6, "a", up=True)
    f.text(X(0), y - 14, f"the turning, forward and backward: {turn_pc:.1f}% ({turn_ms:.1f} ms)", "ta", 10.5,
           weight=700)
    f.text(x0, 160, "the step, smallest / median / largest of 15 timings (ms):", "t", 11, weight=700)
    lo = min(v[0] for v in timed.values()) * 0.9
    hi = max(v[2] for v in timed.values()) * 1.04
    ax = figart.Axes(f, 150, 172, 380, 70, (lo, hi), (-0.5, 1.5))
    ax.draw(xticks=figart.ticks(lo, hi), yticks=[], grid=False, frame=False)
    f.line(150, 242, 530, 242, "m")
    for i, (name, (a, b, c, n, load)) in enumerate(timed.items()):
        yy = ax.py(1 - i)
        cls = "a" if name == "kept" else "s"
        f.text(140, yy + 4, name, TEXT[cls], 10.5, "end", 600)
        f.line(ax.px(a), yy, ax.px(c), yy, cls)
        f.line(ax.px(a), yy - 5, ax.px(a), yy + 5, cls)
        f.line(ax.px(c), yy - 5, ax.px(c), yy + 5, cls)
        f.circle(ax.px(b), yy, 3.5, f"{cls} f")
        f.text(ax.px(c) + 8, yy + 4, f"{a:.1f} / {b:.1f} / {c:.1f}", TEXT[cls], 10, mono=True)
    f.text(x0, 280, f"Kept: the same weights after 3 steps, bit for bit: {same_bits}; the smallest step x{ratio} "
                    f"(load {timed['kept'][4]:.1f}).", "ta", 10.5, weight=600)
    f.text(x0, 296, "Nothing measurable is saved: the turning is the cost, not the angles.", "tm", 10.5)
    return f


# ================================================================== 11.03

def fused_run():
    return figart.experiment("fused", at="11.03")


def lengths():
    out = fused_run().out
    rows = [tuple(float(g) for g in m.groups()) for m in re.finditer(
        r"^ +(\d+) +([\d.]+) ms +([\d.]+) +([\d.]+) ms +([\d.]+) +x +([\d.]+) +([\d.]+)$", out, re.M)]
    load = float(find(out, r"8 windows x 4 heads of 16 on \w+ \(load ([\d.]+)\)").group(1))
    return rows, load


KEPT_CODE = r'''
import json, torch
from experiments.fused import kept_bytes
from models.gpt import self_attend, fused_attend
B, H, T, d = 8, 4, 256, 16
g = torch.Generator().manual_seed(0)
q, k, v = (torch.randn(B, H, T, d, generator=g).requires_grad_() for _ in range(3))
out = {}
for name, attend in (("written out", lambda: self_attend(q, k, v)[0]), ("fused", lambda: fused_attend(q, k, v))):
    seen = {}
    def pack(t):
        seen[t.untyped_storage().data_ptr()] = [list(t.shape), str(t.dtype)[6:], t.untyped_storage().nbytes()]
        return t
    with torch.autograd.graph.saved_tensors_hooks(pack, lambda t: t):
        attend()
    total, _ = kept_bytes(attend)
    out[name] = {"tensors": list(seen.values()), "total": total}
print(json.dumps(out))
'''


def kept1103():
    got = in_project("11.03", KEPT_CODE)
    rows, _ = lengths()
    at256 = next(r for r in rows if r[0] == 256)
    for name, col in (("written out", 2), ("fused", 4)):
        mib = sum(t[2] for t in got[name]["tensors"]) / 2 ** 20
        same(f"{name}'s bytes kept at 256", f"{got[name]['total'] / 2 ** 20:.2f}", f"{mib:.2f}")
        same(f"{name} kept at 256, against the run", f"{mib:.2f}", f"{at256[col]:.2f}")
    f = Fig("kept1103", "What autograd keeps for the backward pass of one attention, 8 windows x 4 heads of 16 at 256 "
                        "places, every tensor saved (each piece of memory once), to scale: written out, the (T, T) "
                        "weights; fused, a total for each row", 252)
    scale = (600 - 20) / (got["written out"]["total"] / 2 ** 20)
    B, H, T, d = 8, 4, 256, 16

    def what(shape, dtype):
        """What a saved tensor is, from its type and how many numbers it holds (the batched products save
        3-d views, 32 x 256 x 16, of the 8 x 4 x 256 x 16 queries)."""
        n = math.prod(shape)
        if dtype == "bool":
            return "mask"
        return {B * H * T * T: "weights", B * H * T * d: "qkv", B * H * T: "row totals"}.get(n, "x".join(map(str, shape)))
    for k, name in enumerate(("written out", "fused")):
        y = 44 + k * 96
        total = got[name]["total"] / 2 ** 20
        f.text(20, y - 12, f"{name}: {total:.2f} MiB", "ta" if name == "written out" else "t", 12, weight=700)
        x = 20.0
        n4 = 0
        notes = []
        for shape, dtype, nbytes in got[name]["tensors"]:
            w = max(3.0, nbytes / 2 ** 20 * scale)
            kind = what(shape, dtype)
            if kind == "qkv":
                n4 += 1
                kind = ["q", "k", "v", "out"][n4 - 1] if name == "fused" else ["q", "k", "v"][n4 - 1]
            cls, tcls = {"weights": ("a af", "ta"), "row totals": ("a af", "ta"), "mask": ("m fs", "tm")}.get(
                kind, ("s f", "t"))
            show = {"weights": f"the weights: {B} x {H} x {T} x {T}, {nbytes / 2 ** 20:.0f} MiB"}.get(kind, kind)
            chip(f, x, y, w - 1, 30, cls, show, tcls, 10.5, 600 if tcls == "ta" else None,
                 mono=kind in ("q", "k", "v", "out"))
            if w < tw(show, 10.5) + 6:
                notes.append((x + w / 2, kind, tcls))
            x += w
        for i, (cx, kind, tcls) in enumerate(notes):
            f.line(cx, y + 31, cx, y + 38 + 12 * i, "m")
            f.text(cx + 3, y + 48 + 12 * i, kind, tcls, 9.5, "end" if cx > 400 else "start")
    f.text(20, 216, f"q, k, v and out: {B} x {H} x {T} x {d} each, {B * H * T * d * 4 / 2 ** 20:.1f} MiB; the row totals "
                    f"{B} x {H} x {T}; the mask {T} x {T} booleans.", "tm", 10)
    f.text(20, 242, "Written out, the weights grow with the square of the length; fused, nothing kept is larger than "
                    "the queries.", "tm", 10.5)
    return f


def length1103():
    rows, load = lengths()
    T = [r[0] for r in rows]
    f = Fig("length1103", "Attention alone, forward and backward, against the window's length (8 windows x 4 heads of "
                          "16, both axes on log scales): the time, the smallest of 5 timings, and the memory autograd "
                          "keeps for the backward pass; written out against PyTorch's fused kernel", 300)
    left = [figart.Series("written out", T, [r[1] for r in rows], "s"),
            figart.Series("fused", T, [r[3] for r in rows], "a")]
    ax = figart.plot(f, (8, 8, 306, 256), left, xlabel="length (places)", ylabel="ms", logx=True, logy=True,
                     xticks=T, xfmt=lambda v: str(int(v)), yticks=[0.1, 1, 10, 100], yfmt=loglabel, legend=None,
                     ylim=(0.1, 100))
    for r in rows:
        ax.dot(r[0], r[1], "s f", 3)
        ax.dot(r[0], r[3], "a fa", 3)
    ax.note(T[-1], rows[-1][3], f"x{rows[-1][5]:.2f}", "ta", 10.5, "end", dx=-6, dy=-8, weight=700)
    ax.note(T[0], rows[0][3], f"x{rows[0][5]:.2f}", "ta", 10.5, dx=4, dy=14, weight=700)
    right = [figart.Series("written out", T, [r[2] for r in rows], "s"),
             figart.Series("fused", T, [r[4] for r in rows], "a"),
             figart.Series("the (T, T) weights alone", T, [r[6] for r in rows], "m", dash=True)]
    ax2 = figart.plot(f, (324, 8, 308, 256), right, xlabel="length (places)", ylabel="MiB kept", logx=True, logy=True,
                      xticks=T, xfmt=lambda v: str(int(v)), yticks=[0.1, 1, 10, 100], yfmt=loglabel, legend=None,
                      ylim=(0.1, 300))
    for r in rows:
        ax2.dot(r[0], r[2], "s f", 3)
        ax2.dot(r[0], r[4], "a fa", 3)
    ax2.note(T[-1], rows[-1][2], f"{rows[-1][2]:.0f}", "t", 10.5, "end", dx=-6, dy=-6)
    ax2.note(T[-1], rows[-1][4], f"{rows[-1][4]:.1f}", "ta", 10.5, "end", dx=-6, dy=14, weight=700)
    figart.legend(f, 360, 40, [("written out", "s"), ("fused", "a"), ("(T, T) weights", "m", True)], gap=15)
    f.text(16, 292, f"This run's times (load {load:.1f}); the memory kept is exact and the same on any machine.", "tm",
           10.5)
    return f


def recorded():
    """The recorded benchmark: each row's seeds' steps (summaries), seconds and ms a step (times.json), checked
    against its output.txt."""
    with open(os.path.join(REC, "times.json")) as fh:
        times = json.load(fh)
    with open(os.path.join(REC, "output.txt")) as fh:
        printed = fh.read()
    got = {}
    for name in ROWS:
        dirs = figart.seed_dirs(os.path.join(REC, label(name)))
        steps = [figart.summary(d)["steps_to_target"] for d in dirs]
        sec, ms = times[name]["seconds"], times[name]["ms"]
        m = find(printed, rf"^   {re.escape(name)} +(\S+) \+- (\S+) \(min (\S+), max (\S+), 3 seeds\) +(\d+) ")
        same(f"{name}'s mean seconds", sig(mean(sec)), m.group(1))
        same(f"{name}'s steps", f"{mean(steps):.0f}", m.group(5))
        seeds = find(printed, rf"^   {re.escape(name)} +(\d+), ([\d.]+) s +(\d+), ([\d.]+) s +(\d+), ([\d.]+) s$")
        same(f"{name} seed by seed", [f"{s:.0f}" for s in steps], [seeds.group(k) for k in (1, 3, 5)])
        got[name] = {"steps": steps, "seconds": sec, "ms": ms,
                     "logs": [figart.read_log(d) for d in dirs]}
    cfg = figart.config(figart.seed_dirs(os.path.join(REC, "baseline"))[0])
    load = float(find(printed, r"seeds a row \(load ([\d.]+)\)").group(1))
    return got, cfg, printed, load


def step1103():
    out = fused_run().out
    steps = [tuple(float(g.replace(",", "")) for g in m.groups()) for m in re.finditer(
        r"windows of +(\d+): written out +([\d.]+) ms, fused +([\d.]+) ms, x([\d.]+); ([\d,]+) tokens", out)]
    load = float(find(out, r"A whole training step of the baseline GPT .*\(load ([\d.]+)\)").group(1))
    bits = {n: float(find(out, rf"^   {n} +([\d.]+) \+-").group(1)) for n in ("written out", "fused")}
    diffs = find(out, r"seed by seed, fused less written out: (\S+), (\S+);").groups()
    rec, cfg, _, rload = recorded()
    f = Fig("step1103", "Fused attention in a whole step: a training step of the page's GPT at windows of 64 and 256 "
                        "(the smallest of 5 timings), the bits trained alike from the same seeds, and the recorded "
                        "benchmark's seconds to 2.4 bits, seed by seed", 300)
    x0, x1 = 120, 300
    top = max(s[1] for s in steps) * 1.1
    X = lambda v: x0 + v / top * (x1 - x0)  # noqa: E731
    f.text(20, 24, f"a training step, ms (load {load:.0f})", "t", 11.5, weight=700)
    for i, (T, a, b, ratio, _) in enumerate(steps):
        y = 44 + i * 64
        f.text(x0 - 10, y + 22, f"windows of {T:.0f}", "t", 11, "end", 600)
        f.rect(x0, y + 4, X(a) - x0, 16, "s f", 1)
        f.text(X(a) + 5, y + 16, f"{a:.1f} written out", "t", 10, mono=True)
        f.rect(x0, y + 24, X(b) - x0, 16, "a af", 1)
        f.text(X(b) + 5, y + 36, f"{b:.1f} fused", "ta", 10, mono=True)
        f.text(x0, y + 56, f"x{ratio:.2f}", "ta", 10.5, weight=700, mono=True)
    f.text(20, 200, "trained alike, 150 steps, 2 seeds:", "t", 11, weight=700)
    f.text(20, 218, f"written out {bits['written out']:.3f}, fused {bits['fused']:.3f} bits", "t", 10.5, mono=True)
    f.text(20, 234, f"seed by seed {diffs[0]}, {diffs[1]}:", "ta", 10.5, mono=True)
    f.text(20, 250, "float32 rounding, the same model", "ta", 10.5)
    a, b = rec["baseline"]["seconds"], rec["fused attention"]["seconds"]
    ax = figart.Axes(f, 420, 44, 190, 196, (-0.5, 1.5), (16, 25))
    ax.draw(xticks=[], yticks=[16, 18, 20, 22, 24], ylabel="seconds to 2.4 bits, recorded")
    for i, (name, vs, st) in enumerate((("baseline", a, "s"), ("fused", b, "a"))):
        X2 = ax.px(i)
        for s_, v in enumerate(vs):
            f.circle(X2 + 7 * (s_ - 1), ax.py(v), 3, f"{st} f")
        f.line(X2 - 14, ax.py(mean(vs)), X2 + 14, ax.py(mean(vs)), st)
        f.text(X2 + 18, ax.py(mean(vs)) + 4, sig(mean(vs)), TEXT[st], 10.5, mono=True)
        f.text(X2, ax.y + ax.h + 15, name, TEXT[st], 11, "middle", 600)
    f.text(515, 276, f"x{mean(b) / mean(a):.2f}, t = {welch(b, a):+.1f}", "ta", 10.5, "middle", 700)
    f.text(20, 292, f"The recorded benchmark: width {cfg['width']}, windows of {cfg['context']}, 3 seeds, from load "
                    f"{rload:.1f} at its start.", "tm", 10.5)
    return f


# ================================================================== 11.04

def prec_run():
    return figart.experiment("precision", at="11.04")


def precision_numbers():
    out = prec_run().out
    rates = [tuple(m.groups()) for m in re.finditer(
        r"rate (\S+): the median step (\S+), the median weight (\S+) \(float16's steps there (\S+)\);\n   ([\d.]+)% of the "
        r"updates would change nothing in float16, ([\d.]+)% in bfloat16", out)]
    if len(rates) != 2:
        raise SystemExit(f"precision: expected two rates, read {rates}")
    score = float(find(out, r"This model's largest score in its last block: ([\d.]+)\.").group(1))
    zeros = float(find(out, r"averages: ([\d.]+)% are 0 in float16").group(1))
    return {"rates": rates, "score": score, "zeros": zeros, "out": out}


def line1104():
    n = precision_numbers()
    (r0, step0, w, spacing, *_), (r1, step1, *_) = n["rates"]
    w, spacing, step0, step1 = float(w), float(spacing), float(step0), float(step1)
    f = Fig("line1104", "What sixteen bits hold, on a log scale from 1e-9 to 1e6, with this model's own numbers after 60 "
                        "steps: float16's range (normal, then fewer bits, then 0) and bfloat16's, which is float32's; "
                        "where Adam's eps, an update, a weight and a score fall", 380)
    x0, x1 = 30, 610
    lo, hi = -9, 6
    X = lambda v: x0 + (math.log10(v) - lo) / (hi - lo) * (x1 - x0)  # noqa: E731
    yb, y16 = 34, 94
    f.text(x0, 24, "bfloat16 (8 bits of exponent, 8 of precision): from 1.2e-38 to 3.4e38, off both ends", "t", 11,
           weight=700)
    f.rect(x0, yb, x1 - x0, 18, "s fs", 0)
    f.line(x0, yb + 9, x0 - 14, yb + 9, "s", arrow=True)
    f.line(x1, yb + 9, x1 + 14, yb + 9, "s", arrow=True)
    f.text(x0, 84, "float16 (5 bits of exponent, 11 of precision): normal from 6.1e-5 to 65,504, fewer bits down to "
                   "6e-8, then 0", "t", 11, weight=700)
    for a, b, cls in ((1e-9, 2 ** -25, "m f"), (2 ** -24, 2 ** -14, "s f"), (2 ** -14, 65504, "s fs"), (65504, 1e6, "m f")):
        f.rect(X(a), y16, X(b) - X(a), 18, cls, 0, dash=cls == "m f")
    f.text((X(1e-9) + X(2 ** -25)) / 2, y16 + 13, "0", "tm", 10, "middle", mono=True)
    f.text((X(65504) + X(1e6)) / 2, y16 + 13, "inf", "tm", 10, "middle", mono=True)
    f.text((X(2 ** -24) + X(2 ** -14)) / 2, y16 + 13, "fewer bits", "tm", 9.5, "middle")
    base = 140
    f.line(x0, base, x1, base, "m")
    for e in range(lo, hi + 1):
        f.line(X(10 ** e), base, X(10 ** e), base + 4, "m")
        if e % 3 == 0:
            f.text(X(10 ** e), base + 16, f"1e{e}" if e else "1", "tm", 10, "middle", mono=True)
    marks = [(n["score"], f"largest attention score: {n['score']:.3g}", "s"),
             (w, f"the median weight: {w:.2g}", "s"),
             (step0, f"an update at the full rate: {step0:.2g}", "s"),
             (spacing, f"float16's step at the median weight: {spacing:.2g}", "s"),
             (step1, f"an update late in a run: {step1:.2g}", "a"),
             (1e-8, "Adam's eps, 1e-8: 0 in float16", "a"),
             (math.exp(12), "e^12, in a softmax: inf in float16", "a")]
    for row, (v, text, cls) in enumerate(marks):   # the rightmost first: no leader crosses a label
        x = X(v)
        y = 182 + row * 22
        f.line(x, base + 6, x, y - 4, cls, dash=cls != "a")
        f.circle(x, base, 3.5, "a fa" if cls == "a" else "s f")
        right = x > 400
        f.line(x, y - 4, x + (-8 if right else 8), y - 4, cls)
        f.text(x + (-12 if right else 12), y, text, TEXT[cls], 10.5, "end" if right else "start",
               700 if cls == "a" else None)
    f.text(x0, 350, "Late in a run the update is under half float16's step at its weight: added to the weight in float16, "
                    "it changes", "tm", 10.5)
    f.text(x0, 366, "nothing. Adam's eps is 0, and a squared-gradient average of 0 then makes an update of 1e-3 / 0 = inf.",
           "tm", 10.5)
    return f


UPDATES_CODE = r'''
import json, math, numpy as np, torch, lab
from data import shakespeare
from experiments.language import train
from experiments.precision import CONFIG, ALL_FOUR, numbers, lost
from experiments.sequences import windows
from models.gpt import GPT
cfg = lab.Config(dict(CONFIG, out="runs-fig", name="precision"))
dev = lab.device(torch, cfg.device)
V = len(shakespeare.chars())
train_t = torch.from_numpy(shakespeare.split("train")).to(dev)
common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
              kv_heads=cfg.kv_heads, **ALL_FOUR)
torch.manual_seed(0)
model = GPT(**common).to(dev)
warm = lab.Config({**cfg, "steps": cfg.warm_steps, "every": cfg.warm_steps})
train(model, warm, lab.Run(warm, 0, label="warm"), dev, train_t)
opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=0.0)
x, y = windows(train_t, torch.from_numpy(np.random.default_rng(1).integers(0, len(train_t) - cfg.context,
                                                                           cfg.batch)).to(dev), cfg.context)
late = cfg.lr * 0.5 * (1 + math.cos(math.pi * 0.95))
out = []
for lr in (cfg.lr, late):
    n = numbers(model, opt, x, y, lr)
    keep = (n["w"] != 0) & (n["u"] != 0)
    ratio = np.log2(np.abs(n["w"][keep]) / np.abs(n["u"][keep]))
    edges = np.arange(-4, 24.5, 0.5)
    counts, _ = np.histogram(ratio, edges)
    w, u = torch.from_numpy(n["w"]).bfloat16(), torch.from_numpy(n["u"]).bfloat16()
    out.append({"lr": lr, "edges": edges.tolist(), "counts": counts.tolist(), "n": int(keep.sum()),
                "f16": 100 * lost(n["w"], n["u"]), "b16": 100 * ((w + u) == w)[w != 0].float().mean().item()})
print(json.dumps(out))
'''


def lost1104():
    n = precision_numbers()
    got = in_project("11.04", UPDATES_CODE)
    for g, printed in zip(got, n["rates"]):
        same(f"the share lost at rate {printed[0]}", (f"{g['f16']:.1f}", f"{g['b16']:.1f}"), (printed[4], printed[5]))
    f = Fig("lost1104", "One AdamW step of the page's GPT after 60 steps, at the full rate and at the rate near a run's "
                        "end: how many times smaller each update is than its weight (log2 of |weight| / |update|), "
                        "and the share of updates sixteen bits would lose", 330)
    for p, g in enumerate(got):
        x = 8 + p * 316
        edges, counts = g["edges"], g["counts"]
        top = max(counts) * 1.1
        ax = figart.Axes(f, x + 40, 58, 260, 168, (edges[0], edges[-1]), (0, top))
        ax.draw(xticks=[0, 4, 8, 11, 16, 20], yticks=[], xfmt=lambda v: str(int(v)),
                xlabel="log2(|weight| / |update|)", ylabel="")
        for a, b, c in zip(edges, edges[1:], counts):
            if c:
                cls = "a af" if a >= 11 else ("m fs" if a >= 8 else "s fs")
                f.rect(ax.px(a), ax.py(c), ax.px(b) - ax.px(a) - 0.5, ax.py(0) - ax.py(c), cls, 0)
        for v, name in ((8, "bfloat16"), (11, "float16")):
            ax.vline(v, None, "a" if v == 11 else "m")
            if v == 11:
                f.text(ax.px(v) + 3, ax.y - 5, f"about 2^{v}: {name}", "ta", 9.5)
            else:
                f.text(ax.px(v) - 3, ax.y - 5, f"{name}: about 2^{v}", "tm", 9.5, "end")
        f.text(x + 40, 30, f"rate {g['lr']:.2g}: {g['n']:,} updates", "t", 11.5, weight=700)
        f.text(x + 40, 286, f"lost in float16: {g['f16']:.1f}%", "ta", 11, weight=700)
        f.text(x + 40, 302, f"lost in bfloat16: {g['b16']:.1f}%", "t", 11)
    f.text(16, 324, "An update under half the spacing of the numbers at its weight leaves it as it was. The paper's "
                    "2048 is 2^11.", "tm", 10.5)
    return f


def speed1104():
    n = precision_numbers()
    out = n["out"]
    prod = find(out, r"One product, 2048 x 256 times 256 x 256: float32 ([\d.]+) ms, bfloat16 ([\d.]+) ms \(load ([\d.]+)\)")
    step = find(out, r"A training step: float32 ([\d.]+) ms \(median .*?\), bfloat16 ([\d.]+) ms \(median .*?\(load ([\d.]+)\)")
    tr = {k: float(find(out, rf"^   {k} +\S+ \+- \S+ \(min .*?\) +ms a step ([\d.]+)").group(1))
          for k in ("float32", "bfloat16")}
    rec, cfg, _, _ = recorded()
    rows = [("one product, 2048 x 256 by 256 x 256", float(prod.group(1)), float(prod.group(2))),
            ("a training step, the page's GPT", float(step.group(1)), float(step.group(2))),
            ("trained alike, 60 steps, ms a step", tr["float32"], tr["bfloat16"]),
            (f"the recorded benchmark, width {cfg['width']}", mean(rec["baseline"]["ms"]), mean(rec["bfloat16"]["ms"]))]
    f = Fig("speed1104", "Sixteen bits on this CPU, against float32, on a log scale: one matrix product, a training "
                         "step, the page's runs trained alike, and the recorded benchmark's step; autocast in bfloat16 "
                         "makes every one slower", 300)
    x0, x1 = 230, 520
    lo, hi = 0.05, 3000
    X = lambda v: x0 + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (x1 - x0)  # noqa: E731
    num = lambda v: f"{v:,.0f}" if v >= 100 else f"{v:.3g}"  # noqa: E731
    for i, (name, a, b) in enumerate(rows):
        y = 26 + i * 56
        f.text(x0 - 10, y + 18, name, "t", 10.5, "end", 600)
        f.rect(x0, y + 4, X(a) - x0, 16, "s f", 1)
        f.text(X(a) + 5, y + 16, f"{num(a)} ms float32", "t", 10, mono=True)
        f.rect(x0, y + 24, X(b) - x0, 16, "a af", 1)
        f.text(X(b) + 5, y + 36, f"{num(b)} bfloat16", "ta", 10, mono=True)
        f.text(x0 - 10, y + 36, f"x{b / a:.1f} slower", "ta", 10.5, "end", 700)
    base = 254
    f.line(x0, base, x1, base, "m")
    for v in (0.1, 1, 10, 100, 1000):
        f.line(X(v), base, X(v), base + 4, "m")
        f.text(X(v), base + 16, loglabel(v), "tm", 10, "middle", mono=True)
    f.text(x1 + 6, base + 4, "ms", "tm", 10.5)
    f.text(16, 292, f"This run at load {float(step.group(3)):.1f}; this PyTorch build says \"MKLDNN not found\": no fast "
                    "16-bit products on this CPU.", "tm", 10.5)
    return f


def angles1104():
    out = prec_run().out
    m = find(out, r"places \[([^\]]+)\] become \[([^\]]+)\]; angles 60 to 60\.875 radians\n   become \[([^\]]+)\]")
    places = [float(v) for v in m.group(1).split(",")]
    became = [float(v) for v in m.group(2).split(",")]
    angles = [60 + k / 8 for k in range(8)]
    rounded = [float(v) for v in m.group(3).split(",")]
    f = Fig("angles1104", "Rotary's places and angles in bfloat16 (8 bits of precision), as 10.02's Rotary made them "
                          "under autocast: each true value and the bfloat16 number it becomes; the numbers bfloat16 has "
                          "there as ticks", 300)

    def strip(y, lo, hi, step, true, got, title, fmtv):
        x0, x1 = 40, 600
        X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)  # noqa: E731
        f.text(x0, y - 34, title, "t", 11.5, weight=700)
        f.line(x0, y, x1, y, "m")
        v = lo
        while v <= hi + 1e-9:
            f.line(X(v), y - 5, X(v), y + 5, "s")
            f.text(X(v), y + 18, fmtv(v), "tm", 10, "middle", mono=True)
            v += step
        for a, b in zip(true, got):
            moved = abs(a - b) > 1e-9
            f.circle(X(a), y - 18, 3.5, "a fa" if moved else "s f")
            if moved:
                f.path(f"M{X(a):.1f} {y - 14} Q {(X(a) + X(b)) / 2:.1f} {y - 4} {X(b):.1f} {y - 6}", "a", arrow=True)
    strip(70, 252, 260, 2, places[:3], became[:3], f"places 255, 256, 257: bfloat16 has every 2nd number from 256 on, "
                                                    f"so 257 becomes {became[2]:.0f}", lambda v: f"{v:.0f}")
    strip(160, 59.75, 61.0, 0.25, angles, rounded, "angles 60 to 60.875 radians, in eighths: bfloat16 has quarters "
                                                  "there", lambda v: f"{v:g}")
    f.text(40, 230, f"Place 1001 becomes {became[4]:.0f}: from 512 on bfloat16 has every 8th number.", "t", 10.5)
    f.text(40, 252, "A query at place 257 was turned as if at 256, and an angle of 60 radians was out by up to an "
                    "eighth.", "t", 10.5)
    f.text(40, 274, "From 11.04 Rotary makes the angles in float32 and rounds only their cos and sin.", "ta", 10.5,
           weight=600)
    return f


# ================================================================== 11.05

def batch_run():
    return figart.experiment("batches", at="11.05")


PARTS_CODE = r'''
import json, torch, lab
from data import shakespeare
from experiments.batches import CONFIG, accumulated
from experiments.sequences import bits, windows
from models.gpt import GPT
cfg = lab.Config(CONFIG)
V = len(shakespeare.chars())
train_t = torch.from_numpy(shakespeare.split("train"))
common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
              kv_heads=cfg.kv_heads, norm="rms", positions="rotary", mlp="swiglu")
torch.manual_seed(0)
model = GPT(**common).double()
x, y = windows(train_t, torch.arange(0, 32 * cfg.context, cfg.context), cfg.context)
with torch.no_grad():
    whole = bits(model(x), y).item()
    parts = [bits(model(a), b).item() for a, b in zip(x.chunk(4), y.chunk(4))]
one, four = accumulated(model, x, y, 1), accumulated(model, x, y, 4)
gap = max((a - b).abs().max().item() for a, b in zip(one, four))
size = max(g.abs().max().item() for g in one)
print(json.dumps({"whole": whole, "parts": parts, "gap": gap, "size": size, "n": len(x)}))
'''

NORMS_CODE = r'''
import json, torch, lab
from data import shakespeare
from experiments.batches import CONFIG, norms
cfg = lab.Config(CONFIG)
dev = lab.device(torch, cfg.device)
V = len(shakespeare.chars())
train_t = torch.from_numpy(shakespeare.split("train")).to(dev)
common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width,
              kv_heads=cfg.kv_heads, norm="rms", positions="rotary", mlp="swiglu")
print(json.dumps({b: norms(common, cfg, dev, train_t, b, cfg.norm_steps) for b in cfg.batches}))
'''


def parts1105():
    got = in_project("11.05", PARTS_CODE)
    out = batch_run().out
    same("the gradient's largest difference at 4 parts", f"{got['gap']:.2g}", find(out, r"4 parts ([\d.e+-]+),").group(1))
    f = Fig("parts1105", "Accumulation as arithmetic: a batch of 32 windows cut into 4 parts of 8, each part's mean bits "
                         "divided by 4 and its backward pass adding into the same gradients; the page's GPT at its "
                         "start, in float64", 300)
    n, k = got["n"], 4
    x0, y0, cw = 30, 40, 18
    f.text(x0, 26, f"one batch: {n} windows of 64 characters", "t", 11.5, weight=700)
    for i in range(n):
        part = i // (n // k)
        gx = x0 + i * cw + part * 8
        f.rect(gx, y0, cw - 3, 22, "a af" if part == 0 else "s f", 2)
    for p, b in enumerate(got["parts"]):
        cx = x0 + (p + 0.5) * (n // k) * cw + p * 8
        f.brace_h(x0 + p * (n // k) * cw + p * 8, x0 + (p + 1) * (n // k) * cw + p * 8 - 3, y0 + 30, "s")
        f.text(cx, y0 + 52, f"part {p + 1}: {b:.4f} bits", "ta" if p == 0 else "t", 10.5, "middle", 600, mono=True)
        f.text(cx, y0 + 68, "/ 4, backward", "tm", 10, "middle")
        f.line(cx, y0 + 76, cx, y0 + 104, "s", arrow=True)
    f.rect(x0, y0 + 108, n * cw + 3 * 8 - 3, 34, "s fs", 4)
    f.text(x0 + (n * cw + 24) / 2, y0 + 130, "the same .grad of every weight, added into four times", "t", 11, "middle",
           600)
    s = sum(got["parts"]) / k
    f.text(x0, 214, f"the four parts' bits / 4, added: {s:.6f}", "t", 11, mono=True)
    f.text(x0, 232, f"the whole batch's mean bits:     {got['whole']:.6f}", "t", 11, mono=True)
    f.text(x0, 256, f"every gradient against the whole batch's, the largest difference: {got['gap']:.2g} (the largest "
                    f"gradient {got['size']:.3g})", "ta", 11, weight=700)
    f.text(x0, 286, "Equal parts, so the mean of the means is the mean. A part takes a part's time: no speed.", "tm",
           10.5)
    return f


def batch_numbers():
    out = batch_run().out
    rate = [(int(m.group(1)), m.group(2), float(m.group(3)), float(m.group(4).replace(",", ""))) for m in re.finditer(
        r"^   batch +(\d+)( in \d+ parts of \d+)? +([\d.]+) ms a step +([\d,]+) tokens a second$", out, re.M)]
    load1 = float(find(out, r"the smallest of \d+ timings \(load ([\d.]+)\)").group(1))
    race = [(int(m.group(1)), float(m.group(2)), float(m.group(3)), int(m.group(4)), int(m.group(5)), float(m.group(6)))
            for m in re.finditer(r"^   batch (\d+), rate ([\d.]+) +([\d.]+) \+- .*? s +(\d+) steps +(\d+)k tokens +([\d.]+) "
                                 r"ms a step$", out, re.M)]
    load3 = float(find(out, r"scaled with the batch \(load ([\d.]+)\)").group(1))
    clipped = {int(m.group(1)): (float(m.group(2)), float(m.group(3)), int(m.group(4))) for m in re.finditer(
        r"^   batch +(\d+): median ([\d.]+), last 10 ([\d.]+); clipped (\d+) of", out, re.M)}
    free = find(out, r"^   batch 16, rate [\d.]+, no clip +\S+ \+- .*? s +(\d+) steps")
    withclip = find(out, r"^   batch 16, rate [\d.]+, clip [\d.]+ +\S+ \+- .*? s +(\d+) steps")
    return {"rate": rate, "load1": load1, "race": race[:4], "load3": load3, "clipped": clipped,
            "free": int(free.group(1)), "clip": int(withclip.group(1))}


def batch1105():
    n = batch_numbers()
    f = Fig("batch1105", "Larger batches on this CPU: tokens a second against the batch (and the batch of 128 "
                         "accumulated from 4 parts of 32), then the steps, the tokens and the seconds each batch takes "
                         "to 3.2 bits, 2 seeds", 330)
    plain = [r for r in n["rate"] if not r[1]]
    acc = next(r for r in n["rate"] if r[1])
    ax = figart.Axes(f, 70, 30, 220, 200, (6, 170), (0, max(r[3] for r in n["rate"]) * 1.15), logx=True)
    ax.draw(xticks=[8, 16, 32, 64, 128], yticks=[0, 40000, 80000, 120000], xfmt=lambda v: str(int(v)),
            yfmt=lambda v: f"{v / 1000:.0f}k", xlabel="batch (windows of 64)", ylabel="tokens a second")
    ax.curve([r[0] for r in plain], [r[3] for r in plain], "a")
    for r in plain:
        ax.dot(r[0], r[3], "a fa", 3.5)
    ax.dot(acc[0], acc[3], "s f", 4.5)
    ax.note(acc[0], acc[3], "128 in 4 parts", "t", 10, "end", dx=-8, dy=4)
    first, last = plain[0], plain[-1]
    ax.note(last[0], last[3], f"x{last[3] / first[3]:.1f} from 8", "ta", 10.5, "end", dx=-8, dy=-6, weight=700)
    f.text(70, 284, f"the smallest of 3 timings (load {n['load1']:.1f})", "tm", 10)
    rows = n["race"]
    names = [f"{b}" + (" x2 rate" if lr > 0.0031 else "") for b, lr, *_ in rows]
    panels = [("steps", [r[3] for r in rows], "{:.0f}"), ("tokens (k)", [r[4] for r in rows], "{:.0f}"),
              ("seconds", [r[2] for r in rows], "{:.2f}")]
    for p, (title, vals, fmtv) in enumerate(panels):
        x = 330 + p * 100
        f.text(x, 30, title, "t", 11, weight=700)
        top = max(vals) * 1.15
        for i, (name, v) in enumerate(zip(names, vals)):
            y = 44 + i * 48
            w = v / top * 84
            cls, tcls = ("a af", "ta") if p == 2 else ("s fs", "t")
            f.rect(x, y, w, 18, cls, 1)
            f.text(x, y + 32, f"{fmtv.format(v)}", tcls, 10.5, mono=True, weight=700 if p == 2 else None)
            if p == 0:
                f.text(x - 6, y + 13, name, "t", 10, "end", 600)
    f.text(330, 248, "batch (rate 0.003; x2: 0.006)", "tm", 10)
    f.text(330, 266, f"to 3.2 bits (load {n['load3']:.1f})", "tm", 10)
    f.text(16, 300, "A larger batch takes fewer steps and more tokens; in seconds the batches come out about level.",
           "tm", 10.5)
    f.text(16, 318, "Steps and tokens are the same on any machine; the seconds are this run's.", "tm", 10.5)
    return f


def clip1105():
    n = batch_numbers()
    got = in_project("11.05", NORMS_CODE)
    series = []
    styles = {"16": "a", "32": "s", "64": "m"}
    for b, vals in got.items():
        same(f"batch {b}'s median gradient length", f"{median(vals):.3f}", f"{n['clipped'][int(b)][0]:.3f}")
        same(f"batch {b}'s steps clipped", sum(v > 1.0 for v in vals), n["clipped"][int(b)][2])
        series.append(figart.Series(f"batch {b}: clipped {n['clipped'][int(b)][2]} of {len(vals)}",
                                    list(range(1, len(vals) + 1)), vals, styles[b]))
    f = Fig("clip1105", "The gradient's length before the clip at each of the first 40 steps of a run, at batches of 16, "
                        "32 and 64 (warmup over 50 steps, the clip at 1): early in training nearly every step is "
                        "cut", 300)
    ax = figart.plot(f, (8, 8, 624, 254), series, xlabel="step", ylabel="the gradient's length", ylim=(0, None),
                     legend="right", xticks=[1, 10, 20, 30, 40])
    ax.hline(1.0, "the clip: 1.0", "a", side="left")
    f.text(16, 292, f"Batch 16 without the clip took {n['free']} steps to 3.2 bits, with it {n['clip']} "
                    f"({100 * (n['free'] / n['clip'] - 1):.0f}% more without).", "tm", 10.5)
    return f


# ================================================================== 11.06

def cache_run():
    return figart.experiment("cache", at="11.06")


WRITTEN_CODE = r'''
import json, torch, lab
from data import shakespeare
from experiments.cache import CONFIG, written
from models import smollm
from tokens import smollm as tokens
cfg = lab.Config(CONFIG)
dev = lab.device(torch, cfg.device)
clock = lambda: lab.clock(torch, dev)
model = smollm.load(dev)
tok = tokens.load()
text = shakespeare.load()
ids = torch.tensor([tok.encode(text[int(0.95 * len(text)):])[:cfg.prompt_tokens]], device=dev)
n = max(cfg.lengths)
plain, t0 = written(model, ids, n, clock, False)
kept, t1 = written(model, ids, n, clock, True)
from lab import bench
print(json.dumps({"without": t0, "with": t1, "same": bool(torch.equal(plain, kept)), "prompt": cfg.prompt_tokens,
                  "load": bench.load_average()}))
'''


def cache_numbers():
    out = cache_run().out
    waste = [(int(m.group(1)), float(m.group(2)), float(m.group(3))) for m in re.finditer(
        r"a window of +(\d+): +([\d.]+) ms a step, .* of which ([\d.]+)% are positions", out)]
    per = int(find(out, r"SmolLM2 keeps ([\d,]+) numbers a token").group(1).replace(",", ""))
    kib = int(find(out, r"(\d+) KiB in float32").group(1))
    full = find(out, r"a full window of (\d+) tokens ([\d,]+) MiB, where 9 key/value heads would keep ([\d,]+) MiB")
    gpt2 = int(find(out, r"GPT-2 small keeps ([\d,]+) a token").group(1).replace(",", ""))
    table = [tuple(float(v) for v in m.groups()) for m in re.finditer(
        r"^ +(\d+) +([\d.]+) +([\d.]+) +([\d.]+) ms +([\d.]+) +([\d.]+) +([\d.]+) ms +x +([\d.]+)$", out, re.M)]
    load = float(find(out, r"without and with the cache \(load ([\d.]+)\)").group(1))
    return {"waste": waste, "per": per, "kib": kib, "window": int(full.group(1)),
            "mib": int(full.group(2).replace(",", "")), "mib9": int(full.group(3).replace(",", "")), "gpt2": gpt2,
            "table": table, "load": load}


def waste1106():
    n = cache_numbers()
    f = Fig("waste1106", "Writing without a cache and with one: every step without reads the whole window again and "
                         "keeps one position's scores; with a cache each step reads the new symbol only, after the "
                         "keys and values kept; and what SmolLM2 keeps, with its grouped heads", 330)
    P, S, cw = 4, 6, 20
    for p, (title, cached) in enumerate((("without a cache", False), ("with a cache", True))):
        x0 = 24 + p * 300
        f.text(x0, 24, title, "ta" if cached else "t", 12, weight=700)
        for s in range(S):
            y = 40 + s * 24
            f.text(x0 + 46, y + 15, f"step {s + 1}", "tm", 10, "end")
            T = P + s
            for i in range(T):
                x = x0 + 54 + i * cw
                last = i == T - 1
                if cached and not last:
                    f.rect(x, y, cw - 3, 18, "s fs", 2, dash=True)
                elif last:
                    f.rect(x, y, cw - 3, 18, "a af", 2)
                else:
                    f.rect(x, y, cw - 3, 18, "s f", 2)
                    f.line(x + 3, y + 15, x + cw - 6, y + 3, "m")
        yy = 40 + S * 24 + 14
        if cached:
            f.text(x0, yy, "computed: the new symbol only (accent);", "t", 10.5)
            f.text(x0, yy + 15, "its query reads every kept key and value (dashed)", "t", 10.5)
        else:
            f.text(x0, yy, "computed: every position again; kept: the", "t", 10.5)
            f.text(x0, yy + 15, "last one's scores (accent), the rest thrown", "t", 10.5)
            f.text(x0, yy + 30, "away (crossed)", "t", 10.5)
    y = 250
    thrown = ", ".join(f"{T}: {pc:.1f}%" for T, _, pc in n["waste"])
    f.text(24, y, f"Thrown away without a cache, by the window's length: {thrown}", "t", 10.5)
    f.text(24, y + 20, f"SmolLM2 keeps {n['per']:,} numbers a token: keys and values, 3 heads of 64, 30 blocks, {n['kib']} "
                       f"KiB in float32;", "ta", 10.5, weight=600)
    f.text(24, y + 36, f"its full window of {n['window']:,} tokens {n['mib']} MiB, where a key and value head for each of "
                       f"its 9 query heads would keep {n['mib9']:,}.", "ta", 10.5, weight=600)
    f.text(24, y + 56, f"GPT-2 small, 12 heads of 64 in 12 blocks, every head its own: {n['gpt2']:,} a token.", "tm", 10.5)
    return f


def written1106():
    n = cache_numbers()
    got = in_project("11.06", WRITTEN_CODE)
    if not got["same"]:
        raise SystemExit("written(): the tokens with the cache and without differ")
    steps = {}
    for k in ("without", "with"):
        t = got[k]
        steps[k] = [1000 * (b - a) for a, b in zip([0.0] + t[:-1], t)]
    L = list(range(1, len(got["without"]) + 1))
    f = Fig("written1106", "Greedy writing with SmolLM2-135M after 16 tokens of the test text, one row: the time of each "
                           "step against the tokens written so far, without a cache and with one, and the tokens a "
                           "second over the whole length written", 300)
    left = [figart.Series("without a cache", L, steps["without"], "s", width=1.2),
            figart.Series("with a cache", L, steps["with"], "a", width=1.2)]
    ax = figart.plot(f, (8, 8, 330, 256), left, xlabel="tokens written", ylabel="ms a step", legend=None,
                     xticks=[1, 64, 128, 192, 256], ylim=(0, None))
    del ax
    right = [figart.Series("without", L, [l / t for l, t in zip(L, got["without"])], "s"),
             figart.Series("with", L, [l / t for l, t in zip(L, got["with"])], "a")]
    ax2 = figart.plot(f, (350, 8, 282, 256), right, xlabel="tokens written", ylabel="tokens a second", legend=None,
                      xticks=[1, 64, 128, 192, 256], ylim=(0, None))
    for length in (32, 64, 128, 256):
        a, b = got["without"][length - 1], got["with"][length - 1]
        ax2.dot(length, length / b, "a fa", 3)
        ax2.dot(length, length / a, "s f", 3)
        ax2.note(length, length / b, f"x{a / b:.1f}", "ta", 10, "middle", dy=-9, weight=700)
    figart.legend(f, 80, 40, [("without a cache", "s"), ("with a cache", "a")], gap=15)
    f.text(16, 292, f"One run of written(), load {got['load']:.1f} at its end; the same tokens both ways: "
                    f"{got['same']}.", "tm", 10.5)
    return f


def table1106():
    rec, cfg, printed, load = recorded()
    base = rec["baseline"]["seconds"]
    f = Fig("table1106", "The recorded benchmark: seconds of training to 2.4 bits on 64 validation windows for each row, "
                         "a ring per seed, the bar their mean; beside it the steps it took and ms a step, and the ratio "
                         "to the baseline with Welch's t", 330)
    x0, x1 = 186, 390
    lo, hi = 16, 30
    X = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)  # noqa: E731
    f.text(x0, 24, "seconds to the target", "t", 11, weight=700)
    f.text(442, 24, "steps", "t", 11, "end", 700)
    f.text(500, 24, "ms a step", "t", 11, "end", 700)
    f.text(626, 24, "against", "t", 11, "end", 700)
    for i, name in enumerate(ROWS):
        y = 48 + i * 38
        r = rec[name]
        sec = r["seconds"]
        style = "s" if name == "baseline" else ("m" if name in ("angles kept", "twice the batch and rate", "bfloat16")
                                                else "a")
        f.text(x0 - 12, y + 4, name, TEXT[style], 11, "end", 600)
        f.line(x0, y, x1, y, "m")
        if mean(sec) > hi:
            f.line(x0, y, x1 + 8, y, "a", arrow=True)
            f.text(x1 - 4, y - 7, f"{sig(mean(sec))} s: {', '.join(f'{v:.0f}' for v in sec)}", "ta", 10, "end", 700,
                   mono=True)
        else:
            for v in sec:
                f.circle(X(v), y, 3.2, f"{style} f")
            f.line(X(mean(sec)), y - 9, X(mean(sec)), y + 9, style)
        f.text(442, y + 4, f"{mean(r['steps']):.0f}", TEXT[style], 10.5, "end", mono=True)
        f.text(500, y + 4, f"{mean(r['ms']):.1f}", TEXT[style], 10.5, "end", mono=True)
        if name != "baseline":
            f.text(626, y + 4, f"x{mean(sec) / mean(base):.2f} (t {welch(sec, base):+.1f})", TEXT[style], 10.5, "end",
                   mono=True)
    base_y = 48 + len(ROWS) * 38 - 12
    for v in range(lo, hi + 1, 2):
        f.line(X(v), base_y, X(v), base_y + 4, "m")
        f.text(X(v), base_y + 16, str(v), "tm", 10, "middle", mono=True)
    f.text(16, 302, f"Width {cfg['width']}, windows of {cfg['context']}, batches of {cfg['batch']}, AdamW {cfg['lr']}, "
                    f"3 seeds a row, on this laptop's CPU, from load {load:.1f};", "tm", 10.5)
    f.text(16, 318, "the bfloat16 row and the last two ran with other work back on the machine (NOTES.md).", "tm", 10.5)
    return f


FIGS = [
    ("11.01-repeats", repeats1101),
    ("11.01-target", target1101),
    ("11.01-crossing", crossing1101),
    ("11.02-step", step1102),
    ("11.02-profiler", profiler1102),
    ("11.02-ops", ops1102),
    ("11.02-rotary", rotary1102),
    ("11.03-kept", kept1103),
    ("11.03-length", length1103),
    ("11.03-step", step1103),
    ("11.04-line", line1104),
    ("11.04-lost", lost1104),
    ("11.04-speed", speed1104),
    ("11.04-angles", angles1104),
    ("11.05-parts", parts1105),
    ("11.05-batch", batch1105),
    ("11.05-clip", clip1105),
    ("11.06-waste", waste1106),
    ("11.06-written", written1106),
    ("11.06-table", table1106),
]


def main():
    only = sys.argv[1:]
    todo = [(name, fn) for name, fn in FIGS if not only or any(name.startswith(o) for o in only)]
    # 11.01-repeats makes the machine busy on purpose (and the load average stays up for a minute or two after),
    # so it runs last: every other figure's run is taken at the load the machine had.
    for name, fn in sorted(todo, key=lambda t: t[0] == "11.01-repeats"):
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
