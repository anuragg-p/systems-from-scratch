"""Figures for research module 03, Optimisers: from the plain step to AdamW (lessons 03.01-03.05).

    python3 -B art/research/figs03.py          (MNIST in the cache: python3 -m data.fetch mnist)
    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs03.py      keep the runs while drawing

Every curve and number comes from a run of the reference code: the experiments' own default runs
(figart.experiment: mnist_lr, adam, adamw, schedule, as the pages run them), and, where an
experiment only prints or draws what a figure needs, the experiment's own functions called in the
project as it stands at the lesson (call() below: momentum.valley and adam.valley for the paths,
lab.warmup_cosine for the rates, data.mnist for which pixels are always 0).

    03.01-rates      the batch loss of every step at the four rates of mnist_lr, seed 0
    03.02-valley     the paths of plain descent and momentum 0.8 in 03.02's valley
    03.03-one-rate   the valley's loss against the step, s = 50 and s = 5000, momentum and Adam
    03.03-race       the Adam paper's comparison: training cost after each pass, both models
    03.04-idle       the pixels that are 0 in every training image, and what happens to their weights
    03.05-schedules  the rate at each step of the five schedules, and the test error of each
"""
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figart  # noqa: E402
import figlib  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "03"


def call(at, code):
    """Run python code in the project as it stands at lesson `at` (its own engine, lab and
    experiments) and return what it printed, read as JSON."""
    root = figart.project(at)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=root)
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=root, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"at {at}:\n{code}\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    return json.loads(r.stdout)


# ---------------------------------------------------------------- 03.01

def rates0301():
    r = figart.experiment("mnist_lr")
    styles = {"0.01": ("m", False), "0.1": ("s", "5 3"), "0.5": ("s", False), "2": ("a", False)}
    series = []
    for lr, (style, dash) in styles.items():
        steps, loss = figart.column(figart.read_log(os.path.join(r.runs, f"lr{lr}", "seed0")), "loss")
        series.append(figart.Series(f"lr {lr}", [s + 1 for s in steps], loss, style, dash, width=1.4))
    f = Fig("rates0301", "The batch loss of every step of one pass over MNIST at four learning rates, seed 0: "
                         "at 2 it jumps within three steps and then sits near log(10)", 330)
    ax = figart.plot(f, (8, 6, 624, 320), series, xlabel="step (1 to 469, one pass; a log scale)",
                     ylabel="training loss of the batch", logx=True, logy=True, legend="right")
    ax.hline(math.log(10))
    ax.note(14, 30, "dashed: log(10) = 2.30, the loss of a guess", "tm")
    rows = figart.read_log(os.path.join(r.runs, "lr2", "seed0"))
    k = max(range(10), key=lambda i: rows[i]["loss"])
    ax.dot(rows[k]["step"] + 1, rows[k]["loss"], "a fa", 3.5)
    ax.note(rows[k]["step"] + 1, rows[k]["loss"], f"step {rows[k]['step'] + 1}: {sig(rows[k]['loss'])}", "ta",
            dx=8, dy=4)
    return f


# ---------------------------------------------------------------- 03.02

def valley0302():
    got = call("03.02", "import json\nfrom experiments.momentum import CONFIG, valley\n"
                        "c = CONFIG\n"
                        "print(json.dumps({mu: valley(c['steep'], c['lr'], mu, c['start'], c['threshold'], "
                        "c['max_steps']) for mu in c['mus']}))")
    cfg = call("03.02", "import json\nfrom experiments.momentum import CONFIG\nprint(json.dumps(CONFIG))")
    steep = cfg["steep"]
    f = Fig("valley0302", f"Plain gradient descent and momentum 0.8 in the valley (w0^2 + {steep:g} w1^2) / 2 "
                          f"from (-4, 1) at lr {cfg['lr']:g}: one zigzags and crawls, the other runs along the floor",
            352)
    panels = [("0.0", "plain descent", "s"), ("0.8", "momentum 0.8", "a")]
    x0, x1, y0, y1 = -4.3, 1.3, -1.15, 1.15
    left, right, h = 20, 620, 132
    for k, (mu, name, cls) in enumerate(panels):
        top = 26 + k * (h + 34)
        X = lambda u: left + (u - x0) / (x1 - x0) * (right - left)
        Y = lambda v: top + h - (v - y0) / (y1 - y0) * h
        f.rect(left, top, right - left, h, "m", 0, sw=False)
        for c in (0.05, 0.4, 1.5, 3.5, 6.5, 10.5, 16):
            rx, ry = math.sqrt(2 * c), math.sqrt(2 * c / steep)
            pts = [(rx * math.cos(2 * math.pi * i / 200), ry * math.sin(2 * math.pi * i / 200)) for i in range(201)]
            seg = []
            for (u, v) in pts:
                if x0 <= u <= x1 and y0 <= v <= y1:
                    seg.append((X(u), Y(v)))
                elif seg:
                    f.polyline(seg, "m", False, 0.75)
                    seg = []
            if seg:
                f.polyline(seg, "m", False, 0.75)
        steps, path = got[mu]
        pts = [(X(u), Y(v)) for u, v in path]
        f.polyline(pts, cls, False, 1.4)
        for x, y in pts[1:]:
            f.circle(x, y, 1.6, f"{cls} {'fa' if cls == 'a' else 'fs'}")
        f.circle(pts[0][0], pts[0][1], 3.2, "s f")
        f.circle(X(0), Y(0), 2.6, "s fs")
        f.text(left, top - 8, f"{name}: {steps} steps to a loss below {cfg['threshold']:g}",
               "ta" if cls == "a" else "t", 12, weight=700)
        if k == 0:
            f.text(X(0) + 6, Y(0) - 6, "the bottom", "tm", 10.5)
            f.text(pts[0][0] + 8, pts[0][1] + 4, "start", "tm", 10.5)
    f.text(left, 26 + 2 * (h + 34) - 8, f"w0 runs left to right, w1 up and down; the walls are {steep:g} times steeper "
                                         "across (w1) than along (w0)", "tm", 10.5)
    return f


# ---------------------------------------------------------------- 03.03

def one_rate0303():
    runs = [("momentum", 50.0, 0.03), ("momentum", 5000.0, 0.03), ("momentum", 50.0, 0.0003),
            ("momentum", 5000.0, 0.0003), ("adam", 50.0, 0.1), ("adam", 5000.0, 0.1)]
    got = call("03.03", "import json\nfrom experiments.adam import CONFIG, valley\n"
                        f"runs = {runs!r}\n"
                        "out = []\n"
                        "for name, s, lr in runs:\n"
                        "    n, path = valley(name, s, lr, 1.0, CONFIG['max_steps'], CONFIG['valley_momentum'])\n"
                        "    out.append([n, [(u * u + s * v * v) / 2 for u, v in path]])\n"
                        "print(json.dumps(out))")
    style = {("momentum", 0.03): ("m", "momentum, lr 0.03"), ("momentum", 0.0003): ("s", "momentum, lr 0.0003"),
             ("adam", 0.1): ("a", "Adam, lr 0.1")}
    series = []
    for (name, s, lr), (n, losses) in zip(runs, got):
        cls, label = style[name, lr]
        losses = [v if v < 1e7 else float("inf") for v in losses]        # past the top: the curve stops there
        # every step of the first 150 (the log axis spreads them out), then evenly: under 400 points, so
        # the plot draws each one rather than thinning the early wiggles away
        keep = [i for i in range(len(losses)) if i < 150 or i % max(1, len(losses) // 200) == 0 or i == len(losses) - 1]
        xs, losses = [i + 1 for i in keep], [losses[i] for i in keep]
        series.append(figart.Series(f"{label}, s = {s:g}", xs, losses, cls, "5 3" if s > 100 else False, width=1.5))
    f = Fig("onerate0303", "The valley's loss against the step at s = 50 and s = 5000: momentum's rate for s = 50 "
                           "diverges at 5000, the rate that survives 5000 crawls, Adam at one rate takes about "
                           "the same steps at both", 330)
    ax = figart.plot(f, (8, 6, 624, 320), series, xlabel="step (a log scale)", ylabel="loss of the valley",
                     logx=True, logy=True, ylim=(1e-5, 1e6), xlim=(1, 6000), legend="right")
    ax.hline(1e-4, "the floor: 0.0001", "m", side="left")
    for (name, s, lr), (n, losses) in zip(runs, got):
        if n is None:
            ax.note(1, 1e6, f"{name}, lr {lr:g}, s = {s:g}: diverged at once (off the top)", "tm", dx=8, dy=16)
    return f


def race0303():
    r = figart.experiment("adam")
    f = Fig("race0303", "The Adam paper's comparison at laptop size: training cost after each pass, each "
                        "optimiser at the best rate of its grid, 3 seeds (the band is min to max)", 300)
    best = re.findall(r"^  pass 1: adam \(lr (\S+)\) \S+  nesterov \(lr (\S+)\)", r.out, re.M)
    for k, model in enumerate(("logistic", "mlp")):
        a_lr, s_lr = best[k]
        series = []
        for opt, lr, style in (("nesterov", s_lr, "s"), ("adam", a_lr, "a")):
            dirs = figart.seed_dirs(os.path.join(r.runs, f"{model}-{opt}-lr{lr}"))
            xs, mean, lo, hi = figart.over_seeds(dirs, "cost", x="epoch")
            series.append(figart.Series(f"{'Adam' if opt == 'adam' else 'Nesterov'} {lr}", xs, mean, style,
                                        lo=lo, hi=hi))
        title = "logistic regression" if model == "logistic" else "network 784-256-256-10"
        f.text(8 + k * 320, 16, title, "t", 12, weight=700)
        figart.plot(f, (8 + k * 320, 28, 304, 268), series, xlabel="passes over the data", ylabel="training cost",
                    legend="end", xticks=[1, 2, 3])
    return f


# ---------------------------------------------------------------- 03.04

def idle0304():
    r = figart.experiment("adamw")
    idle = call("03.04", "import json\nfrom data import mnist\nx, _ = mnist.load('train', None, False)\n"
                         "print(json.dumps((x.max(0) == 0).tolist()))")
    cfg = call("03.04", "import json\nfrom experiments.adamw import CONFIG\nprint(json.dumps(CONFIG))")
    found = re.findall(r"^ +(Adam \+ L2|AdamW) +wd (\S+) *: after one pass, idle pixels' weights at +(\S+)% of their "
                       r"starting size, the others' at +(\S+)%", r.out, re.M)
    n_idle = int(figart.value(r.out, r"^2\. (\d+) of 784 pixels"))
    if n_idle != sum(idle):
        raise SystemExit(f"adamw says {n_idle} idle pixels, the data has {sum(idle)}")
    f = Fig("idle0304", f"Left: the {n_idle} pixels that are 0 in every training image. Right: their weights after "
                        f"one pass of logistic regression at lr {cfg['lr']:g}, as a share of where they started", 300)
    cell, gx, gy = 8, 16, 46
    f.text(gx, 24, f"{n_idle} of 784 pixels are always 0", "ta", 12, weight=700)
    f.text(gx, 38, "the image, 28 by 28", "tm", 10.5)
    for i, dead in enumerate(idle):
        if dead:
            f.rect(gx + (i % 28) * cell, gy + (i // 28) * cell, cell, cell, "fa", 0, sw=False)
    for i in range(29):
        dash = i % 7 != 0
        f.add(f'<line class="m" x1="{gx + i * cell}" y1="{gy}" x2="{gx + i * cell}" y2="{gy + 28 * cell}" '
              f'stroke-width="{0.4 if dash else 0.9}"/>')
        f.add(f'<line class="m" x1="{gx}" y1="{gy + i * cell}" x2="{gx + 28 * cell}" y2="{gy + i * cell}" '
              f'stroke-width="{0.4 if dash else 0.9}"/>')
    f.rect(gx, gy, 28 * cell, 28 * cell, "m", 0)
    # the bars
    bx, bw, top = 350, 160, 46
    f.text(bx - 88, 24, "their weights after one pass", "t", 12, weight=700)
    f.text(bx - 88, 38, "(the weights the data moves, in brackets)", "tm", 10.5)
    steps = math.ceil(60000 / 128)
    for k, (name, wd, idle_pct, busy_pct) in enumerate(found):
        y = top + 14 + k * 54
        cls = "a" if name == "AdamW" else "s"
        f.text(bx - 88, y + 12, f"{name}", "ta" if cls == "a" else "t", 11.5, weight=700)
        f.text(bx - 88, y + 26, f"wd {wd}", "tm", 10.5, mono=True)
        f.rect(bx, y, bw, 18, "m", 2)
        w = bw * float(idle_pct) / 100
        if w > 0.5:
            f.rect(bx, y, w, 18, f"{cls} {'af' if cls == 'a' else 'fs'}", 2)
        f.text(bx + bw + 8, y + 13, f"{idle_pct}%", "ta" if cls == "a" else "t", 11.5, mono=True)
        f.text(bx + bw + 8 + tw(f"{idle_pct}%", 11.5, True) + 6, y + 13, f"({busy_pct}%)", "tm", 10.5, mono=True)
        if name == "AdamW":
            want = 100 * (1 - cfg["lr"] * float(wd)) ** steps
            x = bx + bw * want / 100
            f.line(x, y - 4, x, y + 22, "a", dash=True)
            f.text(bx, y + 34, f"(1 - lr x wd)^{steps} = {want:.1f}%", "ta", 10.5, mono=True)
        elif k == 0:
            f.text(bx, y + 34, "wd x w goes through Adam's division", "tm", 10.5)
        else:
            f.text(bx, y + 34, "the same, at 100 times the wd", "tm", 10.5)
    f.text(bx, top + 4, "0", "tm", 10.5, "middle", mono=True)
    f.text(bx + bw, top + 4, "100%", "tm", 10.5, "middle", mono=True)
    return f


# ---------------------------------------------------------------- 03.05

def schedules0305():
    r = figart.experiment("schedule")
    cfg = call("03.05", "import json\nfrom experiments.schedule import CONFIG\nprint(json.dumps(CONFIG))")
    total = cfg["epochs"] * math.ceil(60000 / cfg["batch"])
    rates = call("03.05", "import json, lab\n"
                          f"runs, total = {cfg['runs']!r}, {total}\n"
                          "out = []\n"
                          "for kind, lr, warmup in runs:\n"
                          "    f = lab.warmup_cosine(warmup, total)\n"
                          "    out.append([lr if kind == 'constant' else lr * f(k) for k in range(total)])\n"
                          "print(json.dumps(out))")
    labels = [f"{kind} {lr:g}" + (f", warmup {w}" if w else "") for kind, lr, w in cfg["runs"]]
    styles = ["m", "m", "s", "s", "a"]
    dashes = [False, "5 3", False, "5 3", False]
    f = Fig("schedules0305", "Top: the learning rate at each step of the five schedules. Bottom: the test error "
                             "of each after two passes, 3 seeds, and the worst batch loss of its first 300 steps", 520)
    series = [figart.Series(lab, range(total), ys, st, da, width=1.6) for lab, ys, st, da in
              zip(labels, rates, styles, dashes)]
    ax = figart.plot(f, (8, 6, 624, 230), series, xlabel="step (two passes of 469)", ylabel="learning rate",
                     ylim=(0, 0.0105), legend="right")
    ax.vline(200, None, "a")
    ax.note(200, 0, "warmup ends", "ta", dx=5, dy=-5)
    groups = []
    for (kind, lr, w), lab, st in zip(cfg["runs"], labels, styles):
        sums = [figart.summary(d) for d in figart.seed_dirs(os.path.join(r.runs, f"{kind}-lr{lr:g}-w{w}"))]
        worst = sum(s["worst_early_loss"] for s in sums) / len(sums)
        name = lab.replace(", warmup", "\n+ warmup").replace("constant", "const.")
        groups.append((name + f"\nworst {worst:.4g}", [s["test_error"] for s in sums], st))
    figart.seeds_chart(f, (8, 250, 624, 266), groups, ylabel="test error (%)")
    return f


def main():
    print(write(MOD, "03.01-rates", rates0301()))
    print(write(MOD, "03.02-valley", valley0302()))
    print(write(MOD, "03.03-one-rate", one_rate0303()))
    print(write(MOD, "03.03-race", race0303()))
    print(write(MOD, "03.04-idle", idle0304()))
    print(write(MOD, "03.05-schedules", schedules0305()))


if __name__ == "__main__":
    main()
