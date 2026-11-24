"""Figures for research module 06, Images: convolution and residual networks (lessons 06.01-06.04).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs06.py [06.02 ...]
                                    all of them, or those whose name starts so (DIR keeps the runs)

Every curve, bar, map and number comes from the reference code (tracks/research), run as the page
runs it, or from the recorded long run the page shows:

  06.01  the engine's F.conv2d and _windows of the project at 06.01, on a 6 by 6 image of a 7
         and one 3 by 3 filter (the stepped figure: every window's products and sum);
         python3 -m experiments.conv (3 seeds): accuracy on moved digits, per seed;
         experiments.conv's own trained() and through() on seed 0, the test digit the page's run
         moves: the maps after the first convolution and after the second pooling, and the Linear
         layer's weights (the generator stops unless the two "largest difference 0" lines hold)
  06.02  python3 -m experiments.switch: the printed float64 table, and float32's losses from its
         log; the clock's timeline is a schematic
  06.03  CIFAR-10's first training record, read by data.cifar.read_records; data.augment.crop_flip
         on that image with np.random.default_rng(2) (the first seed whose four draws mirror two); python3 -m experiments.cifar (3 seeds)
  06.04  the networks of models/resnet.py (their layers and weights counted); the recorded long run,
         experiments/recorded/resnet/ (its logs, as committed); python3 -m experiments.resnet (the
         page's short run, 2 seeds)

MNIST and CIFAR-10 must be in the cache (python3 -m data.fetch mnist cifar10, in tracks/research),
and PyTorch installed. The runs take about three minutes in all on the machine in NOTES.md.
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
sys.path.insert(0, os.path.dirname(HERE))         # art/: steps.py, for the stepped figure
import figart  # noqa: E402
import figlib  # noqa: E402
import steps  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "06"


def in_project(at, code):
    """Run python code in the project as it stands at lesson `at`; the JSON it prints last."""
    d = figart.project(at)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d)
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"python in the project at {at} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def seeds_of(runs, label, key):
    """key of every seed's summary.json, under runs/<label>, in seed order."""
    return [figart.summary(d)[key] for d in figart.seed_dirs(os.path.join(runs, label))]


def comma(n):
    return f"{n:,}"


def grid(f, x, y, values, cell, lo=None, hi=None, cls="t", frame="m", signed=False, photo=False):
    """A map of numbers as squares of one fill class at an opacity from 0 (lo or below) to 1 (hi);
    signed: negative numbers in the foreground and positive in the accent, each scaled by the largest
    size; photo: brightness, so the opacity of the foreground runs the other way (1 at lo), which
    shows a photograph as it is on a light page and as its negative on a dark one (the theme's
    colours are all a figure has). Squares of equal opacity on a row are drawn as one path, to keep
    the file small."""
    rows = len(values)
    cols = len(values[0])
    flat = [v for row in values for v in row]
    if photo:
        values = [[-v for v in row] for row in values]
        lo, hi = -(max(flat) if hi is None else hi), -(min(flat) if lo is None else lo)
        flat = [-v for v in flat]
    if signed:
        top = max(abs(v) for v in flat) or 1
    else:
        lo = min(flat) if lo is None else lo
        hi = max(flat) if hi is None else hi
    paths = {}
    for i, row in enumerate(values):
        j = 0
        while j < cols:
            v = row[j]
            if signed:
                c, op = ("fa" if v > 0 else "t"), round(abs(v) / top, 1)
            else:
                c, op = cls, round(min(1.0, max(0.0, (v - lo) / ((hi - lo) or 1))), 1)
            k = j + 1
            while k < cols:
                w = row[k]
                if signed:
                    c2, op2 = ("fa" if w > 0 else "t"), round(abs(w) / top, 1)
                else:
                    c2, op2 = cls, round(min(1.0, max(0.0, (w - lo) / ((hi - lo) or 1))), 1)
                if (c2, op2) != (c, op):
                    break
                k += 1
            if op >= 0.05:
                paths.setdefault((c, op), []).append(f"M{x + j * cell:.1f} {y + i * cell:.1f}h{(k - j) * cell:.1f}"
                                                     f"v{cell:.1f}h{-(k - j) * cell:.1f}z")
            j = k
    for (c, op), parts in sorted(paths.items()):
        f.add(f'<path class="{c}" d="{"".join(parts)}" fill-opacity="{op}"/>')
    if frame:
        f.rect(x, y, cols * cell, rows * cell, frame, 0)


# ------------------------------------------------------------------ 06.01

SLIDE_IMAGE = [[0, 1, 1, 1, 1, 0],
               [0, 0, 0, 0, 1, 0],
               [0, 0, 0, 1, 0, 0],
               [0, 0, 0, 1, 0, 0],
               [0, 0, 1, 0, 0, 0],
               [0, 1, 0, 0, 0, 0]]
SLIDE_FILTER = [[-1, -1, 1],
                [-1, 1, -1],
                [1, -1, -1]]

SLIDE_CODE = f"""
import json
import numpy as np
import engine as torch
from engine.nn import functional as F
img = np.array({SLIDE_IMAGE}, dtype=np.float32)[None, None]
k = np.array({SLIDE_FILTER}, dtype=np.float32)[None, None]
out = F.conv2d(torch.from_numpy(img), torch.from_numpy(k))
win = F._windows(img, 3, 3, (1, 1))
print(json.dumps({{"out": out.numpy()[0, 0].tolist(), "windows": win[0, 0].tolist()}}))
"""


def slide0601():
    """The stepped figure: a 3 by 3 filter laid on every window of a 6 by 6 image, the output filling up."""
    d = in_project("06.01", SLIDE_CODE)
    out, wins = d["out"], d["windows"]
    n_out = len(out)
    for r in range(n_out):                         # every output number is its window's products, summed
        for c in range(n_out):
            s = sum(wins[r][c][i][j] * SLIDE_FILTER[i][j] for i in range(3) for j in range(3))
            if s != out[r][c]:
                raise SystemExit(f"conv2d at ({r}, {c}) gave {out[r][c]}, the products add up to {s}")
    best = max(v for row in out for v in row)
    f = Fig("slide0601", "A 3 by 3 filter laid on every 3 by 3 window of a 6 by 6 image of a 7: at each window "
                         "the nine products add up to one number of the output", 268)
    ic, kc, oc = 30, 26, 34                        # cell sizes: image, filter and products, output
    ix, iy = 20, 42
    kx, ky = 236, 42
    px, py = 236, 158
    ox, oy = 452, 42
    f.text(ix, 26, "the image, 6 by 6", "t", 12, weight=600)
    f.text(kx, 26, "the filter: 9 weights", "ta", 12, weight=600)
    f.text(px, py - 12, "pixel x weight, under the window", "tm", 11)
    f.text(ox, 26, "the output, 4 by 4", "t", 12, weight=600)
    for i, row in enumerate(SLIDE_IMAGE):
        for j, v in enumerate(row):
            if v:                                  # ink: the foreground, faint, under the cell's outline
                f.add(f'<rect class="t" x="{ix + j * ic}" y="{iy + i * ic}" width="{ic}" height="{ic}" '
                      f'fill-opacity="0.2"/>')
            f.rect(ix + j * ic, iy + i * ic, ic, ic, "s", 0)
            f.text(ix + j * ic + ic / 2, iy + i * ic + ic / 2 + 4, str(v), "t" if v else "tm", 11.5, "middle",
                   700 if v else None, mono=True)
    for i, row in enumerate(SLIDE_FILTER):
        for j, v in enumerate(row):
            f.rect(kx + j * kc, ky + i * kc, kc, kc, "a af", 0)
            f.text(kx + j * kc + kc / 2, ky + i * kc + kc / 2 + 4, str(v), "ta", 11.5, "middle", 600, mono=True)
    f.text(kx + 3 * kc + 10, ky + 16, "+1 on a stroke", "tm", 10.5)
    f.text(kx + 3 * kc + 10, ky + 30, "going up to", "tm", 10.5)
    f.text(kx + 3 * kc + 10, ky + 44, "the right,", "tm", 10.5)
    f.text(kx + 3 * kc + 10, ky + 58, "-1 around it", "tm", 10.5)
    f.text(ix, iy + 6 * ic + 22, "the same 9 weights at all 16 windows", "ta", 11)
    for r in range(n_out):
        for c in range(n_out):
            f.rect(ox + c * oc, oy + r * oc, oc, oc, "m f", 0, dash=True)
    order = [(r, c) for r in range(n_out) for c in range(n_out)]
    for k, (r, c) in enumerate(order):
        v = out[r][c]
        prods = [[int(wins[r][c][i][j] * SLIDE_FILTER[i][j]) for j in range(3)] for i in range(3)]
        if k == len(order) - 1:
            cap = (f"The last window: {int(v)}. The output is a picture again, a feature map: {int(best)} where the "
                   f"7 has the filter's stroke, lower everywhere else, from the same 9 weights at every window")
        elif v == best:
            cap = (f"Window at row {r}, column {c}: the products add up to {int(v)}, the most there is: "
                   f"the stroke the filter looks for is exactly here")
        else:
            cap = f"Window at row {r}, column {c}: the nine products add up to {int(v)}, output ({r}, {c})"
        with steps.step(f, cap):
            f.add(f'<rect class="a" x="{ix + c * ic}" y="{iy + r * ic}" width="{3 * ic}" height="{3 * ic}" '
                  f'stroke-width="3"/>')
            for i in range(3):
                for j in range(3):
                    p = prods[i][j]
                    f.rect(px + j * kc, py + i * kc, kc, kc, "s f", 0)
                    f.text(px + j * kc + kc / 2, py + i * kc + kc / 2 + 4, str(p), "t" if p else "tm", 11.5, "middle",
                           mono=True)
            f.text(px + 3 * kc + 10, py + 1.5 * kc + 4, "sum:", "tm", 11.5)
            f.text(px + 3 * kc + 44, py + 1.5 * kc + 5, str(int(v)), "ta", 15, weight=700, mono=True)
            for kk, (rr, cc) in enumerate(order[:k + 1]):
                lit = kk == k
                f.rect(ox + cc * oc, oy + rr * oc, oc, oc, "a af" if lit else "s f", 0)
                f.text(ox + cc * oc + oc / 2, oy + rr * oc + oc / 2 + 4.5, str(int(out[rr][cc])), "ta" if lit else "t",
                       13 if lit else 12, "middle", 700 if lit else None, mono=True)
    steps.check(f.svg())
    return f


def moved0601():
    r = figart.experiment("conv", at="06.01")
    shifts = figart.config(figart.seed_dirs(os.path.join(r.runs, "fc"))[0])["shifts"]
    series = []
    for label, name, style in (("fc", "fully connected", "s"), ("conv", "convolutional", "a")):
        dirs = figart.seed_dirs(os.path.join(r.runs, label))
        per = [[figart.summary(d)[f"moved{k}"] for d in dirs] for k in shifts]
        weights = figart.summary(dirs[0])["weights"]
        series.append(figart.Series(f"{name}, {comma(weights)} weights", shifts, [sum(p) / len(p) for p in per], style,
                                    lo=[min(p) for p in per], hi=[max(p) for p in per]))
    f = Fig("moved0601", "Accuracy on 5000 test digits moved k pixels, after training on 10,000 digits as they are: "
                         "mean of 3 seeds, the band from the lowest seed to the highest", 290)
    ax = figart.plot(f, (8, 6, 624, 280), series, xlabel="pixels moved (k)", ylabel="test accuracy", ylim=(0, 1),
                     xticks=shifts, yticks=[0, 0.2, 0.4, 0.6, 0.8, 1], legend="top")
    ax.hline(0.1, "chance: 0.1", side="left")
    for s in series:
        for k, v in zip(s.xs, s.ys):
            ax.dot(k, v, "a fa" if s.style == "a" else "s f", 2.5)
            if s.style == "a":                    # above the line, to the right (left at the end)
                ax.note(k, v, sig(v), "ta", dx=6 if k < shifts[-1] else -6, dy=-8,
                        anchor="start" if k < shifts[-1] else "end")
            else:                                 # below it, to the left (right at the start)
                ax.note(k, v, sig(v), "t", dx=-6 if k else 6, dy=15, anchor="end" if k else "start")
    return f


MAPS_CODE = """
import json, sys, tempfile
import numpy as np
import engine as torch
import lab
from data import mnist
from experiments import conv
cfg = lab.config(conv.CONFIG, ["out=" + tempfile.mkdtemp()])
x, y = mnist.load("train", cfg.n_train)
xt, yt = mnist.load("test", cfg.n_test)
run, model, shape, order = conv.trained(cfg, "convolutional", 0, x, y, "conv")
digit, up = xt[:1], conv.moved(xt[:1], 4, conv.BLANK)
a1, b1 = conv.through(model, digit, 1)[0], conv.through(model, up, 1)[0]
a6, b6 = conv.through(model, digit, 6)[0], conv.through(model, up, 6)[0]
a8, b8 = conv.through(model, digit, 8)[0], conv.through(model, up, 8)[0]
ink = lambda a: np.clip(a * mnist.STD + mnist.MEAN, 0, 1).reshape(28, 28)
on, off = ink(digit) > 0.5, ink(digit) < 0.05      # the map that lights the stroke most against the blank
m1 = int(np.argmax([np.maximum(a, 0)[on].mean() - np.maximum(a, 0)[off].mean() for a in a1]))
m6 = int(np.argmax(a6.sum((1, 2))))
label = int(yt[0])
w = model[7].weight.detach().numpy()[label].reshape(16, 7, 7)[m6]
print(json.dumps({"digit": ink(digit).tolist(), "up": ink(up).tolist(), "label": label,
                  "conv": [np.maximum(a1[m1], 0).tolist(), np.maximum(b1[m1], 0).tolist()], "m1": m1,
                  "pool": [a6[m6].tolist(), b6[m6].tolist()], "m6": m6, "w": w.tolist(),
                  "diff1": float(np.abs(b1[:, 1:23] - a1[:, 5:27]).max()),
                  "diff6": float(np.abs(b6[:, 1:5] - a6[:, 2:6]).max()),
                  "scores": [a8.tolist(), b8.tolist()]}))
"""


def maps0601():
    d = in_project("06.01", MAPS_CODE)
    r = figart.experiment("conv", at="06.01")
    if d["diff1"] != 0 or d["diff6"] != 0 or r.out.count("largest difference 0\n") != 2:
        raise SystemExit(f"the moved maps are not the same numbers moved: {d['diff1']}, {d['diff6']}\n{r.out}")
    pred = [max(range(10), key=lambda k: s[k]) for s in d["scores"]]
    printed = figart.value(r.out, r"predicted (\d) and \d")
    if pred[0] != printed or pred[1] != figart.value(r.out, r"predicted \d and (\d)"):
        raise SystemExit(f"the predictions {pred} are not the ones the run printed:\n{r.out}")
    f = Fig("maps0601", "A test digit and the same digit moved 4 pixels up, through the trained convolutional "
                        "network (seed 0): the same maps one place higher, read by the Linear layer's other weights",
            404)
    cell, small = 3, 12
    cols = [20, 146, 272, 404, 536]
    y1, y2 = 60, 240
    heads = [("the digit", "28 by 28 pixels"), ("convolution 1", f"map {d['m1'] + 1} of 8, 28 by 28"),
             ("pooling 2", f"map {d['m6'] + 1} of 16, 7 by 7"),
             (f"Linear weights, a {d['label']}", f"on map {d['m6'] + 1}: one a place"), ("scores", "for 10 digits")]
    for x, (a, b) in zip(cols, heads):
        f.text(x, 20, a, "t", 11.5, weight=600)
        f.text(x, 35, b, "tm", 10.5)
    top = max(max(row) for m in d["conv"] for row in m)
    ptop = max(max(row) for m in d["pool"] for row in m)
    wy = (y1 + y2) / 2
    for k, (y, name) in enumerate(((y1, "as it is"), (y2, "moved 4 up"))):
        img = d["digit"] if k == 0 else d["up"]
        grid(f, cols[0], y, img, cell, 0, 1, "t")
        f.text(cols[0] + 42, y + 84 + 16, name, "ta" if k else "t", 11, "middle", 600)
        grid(f, cols[1], y, d["conv"][k], cell, 0, top, "fa")
        grid(f, cols[2], y, d["pool"][k], small, 0, ptop, "fa")
        f.line(cols[0] + 88, y + 42, cols[1] - 6, y + 42, "s", arrow=True)
        f.line(cols[1] + 88, y + 42, cols[2] - 6, y + 42, "s", arrow=True)
        into = wy + (30 if k == 0 else 54)
        f.path(f"M{cols[2] + 88} {y + 42} L{cols[3] - 8} {into}", "s", arrow=True)
        f.path(f"M{cols[3] + 90} {into} L{cols[4] - 8} {y + 26}", "s", arrow=True)
        sc = d["scores"][k]
        p = max(range(10), key=lambda j: sc[j])
        f.text(cols[4], y + 30, f"predicted: {p}", "ta" if p != d["label"] else "t", 13, weight=700)
        f.text(cols[4], y + 48, f"top score {sc[p]:.1f}", "tm", 10.5)
        f.text(cols[4], y + 62, f"for a {d['label']}: {sc[d['label']]:.1f}", "tm", 10.5)
    grid(f, cols[3], wy, d["w"], small, signed=True)
    f.text(cols[3], wy + 84 + 16, "accent: above 0", "tm", 10.5)
    f.text(cols[3], wy + 84 + 30, "the others: below 0", "tm", 10.5)
    my = (y1 + 84 + y2) / 2 + 4
    f.text(cols[1], my - 7, "the same numbers,", "ta", 10.5)
    f.text(cols[1], my + 7, "4 rows higher", "ta", 10.5)
    f.text(cols[2], my - 7, "the same numbers,", "ta", 10.5)
    f.text(cols[2], my + 7, "1 cell higher", "ta", 10.5)
    f.text(20, 378, "Convolution and pooling move the features with the digit, exactly: the largest difference is 0.",
           "tm", 10.5)
    f.text(20, 394, "The Linear layer has a weight of its own for every place, so the moved features meet other "
                    "weights.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 06.02

def switch_table(out):
    """The float64 table switch prints: [(parameter, shape, gradient, after the step)]."""
    rows = []
    for line in out.splitlines():
        m = __import__("re").match(r"^   (\d+\.\w+) +(\(.*?\)) +(\S+) +(\S+)$", line)
        if m:
            rows.append((m.group(1), m.group(2), float(m.group(3)), float(m.group(4))))
    if len(rows) != 8:
        raise SystemExit(f"switch: expected 8 parameters in its table, read {len(rows)}:\n{out}")
    return rows


def import0602():
    """One line names the library; the rest of the script is the same on either."""
    r = figart.experiment("switch", at="06.02")
    loss = figart.value(r.out, r"the loss: (\S+)")
    worst = max(max(g, a) for _, _, g, a in switch_table(r.out))
    f = Fig("import0602", "The same script on either library: one line names it, and every name after that line is "
                          "the same on both", 262)
    x0, y0, lh = 20, 34, 19
    lines = [("import engine as torch", "a"), ("nn = torch.nn", "t"), ("F = torch.nn.functional", "t"),
             ("model = nn.Sequential(nn.Conv2d(3, 32, 3), ...)", "t"),
             ("opt = torch.optim.SGD(model.parameters(), lr=0.01)", "t"),
             ("loss = F.cross_entropy(model(x), y)", "t"), ("loss.backward()", "t"), ("opt.step()", "t")]
    w = 372
    f.rect(x0, y0, w, 26 + lh * len(lines), "s fs", 6)
    f.text(x0, y0 - 10, "a training step, as the scripts of modules 00 to 06.01 write it", "tm", 11)
    for i, (s, cls) in enumerate(lines):
        f.text(x0 + 12, y0 + 22 + i * lh, s, "ta" if cls == "a" else "t", 11, weight=700 if cls == "a" else None,
               mono=True)
    bx, bw = 430, 190
    ya, yb, bh = 30, 118, 62
    f.label_box(bx, ya, bw, bh, "the engine", "s f", "t", 12.5, False, weight=700,
                sub="numpy, on the CPU only")
    f.label_box(bx, yb, bw, bh, "PyTorch", "a af", "ta", 12.5, False, weight=700,
                sub="the CPU, or a GPU: cuda, mps")
    sy = y0 + 22 - 4
    f.path(f"M{x0 + 12 + tw('import engine as torch', 11, True) + 8:.1f} {sy} L{bx - 8} {ya + bh / 2}", "s", arrow=True)
    f.path(f"M{x0 + 12 + tw('import engine as torch', 11, True) + 8:.1f} {sy + 4} L{bx - 8} {yb + bh / 2}", "a",
           arrow=True, dash=True)
    f.text(bx + bw / 2, yb + bh + 18, "import torch", "ta", 11.5, "middle", 700, mono=True)
    f.text(x0, 232, f"Built by one function from the same weights and fed the same batch, the two take a training "
                    f"step that agrees to {sig(loss, 2)}", "tm", 11)
    f.text(x0, 248, f"in the loss and to {sig(worst, 2)} in every gradient and weight, in float64: the same arithmetic, "
                    f"added up in another order.", "tm", 11)
    return f


def same0602():
    r = figart.experiment("switch", at="06.02")
    rows = switch_table(r.out)
    f = Fig("same0602", "Engine against PyTorch. Left: float64, one step, the largest relative difference of each "
                        "parameter (3 seeds). Right: float32, the same 10 steps, the difference in the loss", 300)
    ax = figart.Axes(f, 52, 30, 300, 220, (-0.5, len(rows) - 0.5), (1e-19, 1e-15), False, True)
    ax.draw(xticks=[], yticks=[1e-19, 1e-18, 1e-17, 1e-16, 1e-15], frame=False)
    f.line(ax.x, ax.y + ax.h, ax.x + ax.w, ax.y + ax.h, "m")
    f.text(ax.x - 6, 22, "float64: relative difference", "tm", 11)
    bw = 13
    for i, (name, _, g, a) in enumerate(rows):
        for k, (v, cls) in enumerate(((g, "s fs"), (a, "a af"))):
            top = ax.py(v)
            f.rect(ax.px(i) - bw + k * bw, top, bw - 1, ax.y + ax.h - top, cls, 1)
        f.text(ax.px(i), ax.y + ax.h + 14, name.replace(".weight", ".w").replace(".bias", ".b"), "tm", 10, "middle",
               mono=True)
    ax.hline(2 ** -52, "float64's step at 1: 2.2e-16", side="left")
    for k, (label, cls, tcls) in enumerate((("gradient", "s fs", "t"), ("weight after the step", "a af", "ta"))):
        f.rect(ax.x + ax.w - 140, ax.y + 4 + 16 * k, 10, 10, cls, 1)
        f.text(ax.x + ax.w - 125, ax.y + 13 + 16 * k, label, tcls, 10.5)
    log = figart.read_log(os.path.join(r.runs, "float32", "seed0"))
    steps_, diff = [row["step"] for row in log], [abs(row["engine"] - row["PyTorch"]) for row in log]
    floor = 1e-8
    ax2 = figart.Axes(f, 408, 30, 216, 220, (-0.5, steps_[-1] + 0.5), (floor, 1e-4), False, True)
    ax2.draw(xlabel="step", xticks=[0, 2, 4, 6, 8, 10], yticks=[1e-8, 1e-7, 1e-6, 1e-5, 1e-4])
    f.text(ax2.x - 6, 22, "float32: |engine - PyTorch|, the loss", "tm", 11)
    ax2.hline(2 ** -22, "float32's step at 2.3", side="left")
    for s, d in zip(steps_, diff):
        if d > 0:
            ax2.dot(s, d, "a fa", 3)
        else:
            f.text(ax2.px(s), ax2.y + ax2.h - 6, "=", "ta", 12, "middle", 700, mono=True)
    ax2.curve([s for s, d in zip(steps_, diff) if d > 0], [d for d in diff if d > 0], "a", width=1.25)
    f.text(ax2.x + 4, ax2.y + ax2.h - 20, "=: the same float32", "ta", 10)
    return f


def clock0602():
    """Why lab.clock waits: a GPU works through a queue while Python goes on (a schematic)."""
    f = Fig("clock0602", "A GPU works through a queue while Python goes on: a clock read without waiting times "
                         "the asking, lab.clock waits for the device first", 236)
    x0, x1 = 120, 610
    yp, yg = 58, 118
    f.text(20, yp + 5, "Python", "t", 12, weight=700)
    f.text(20, yg + 5, "the GPU", "ta", 12, weight=700)
    f.line(x0, yp, x1, yp, "m")
    f.line(x0, yg, x1, yg, "m")
    asks = [x0 + 10 + 34 * i for i in range(6)]
    for i, x in enumerate(asks):
        f.rect(x, yp - 9, 26, 18, "s fs", 3)
        f.text(x + 13, yp + 4, f"k{i + 1}", "t", 10, "middle", mono=True)
    gx = x0 + 40
    for i in range(6):
        f.rect(gx + 70 * i, yg - 10, 64, 20, "a af", 3)
        f.text(gx + 70 * i + 32, yg + 4, f"k{i + 1}", "ta", 10.5, "middle", mono=True)
        f.line(asks[i] + 13, yp + 9, gx + 70 * i + 10, yg - 11, "m", arrow=True)
    t_ask = asks[-1] + 30
    t_done = gx + 70 * 6
    for x, label, cls in ((t_ask, "a clock read here: the time to queue the work", "tm"),
                          (t_done, "lab.clock: wait, then read", "ta")):
        f.line(x, yp - 24, x, yg + 34, "m" if cls == "tm" else "a", dash=True)
    f.text(t_ask - 4, yg + 48, "time.perf_counter() here:", "tm", 10.5, "end")
    f.text(t_ask - 4, yg + 62, "the time to ask, not to do", "tm", 10.5, "end")
    f.text(t_done - 4, yg + 48, "torch.mps.synchronize() first,", "ta", 10.5, "end")
    f.text(t_done - 4, yg + 62, "then the clock: the work, done", "ta", 10.5, "end")
    f.text(20, 214, "k1 ... k6: one training step's operations (kernels). On the CPU each is done when its line returns, "
                    "so there is nothing to wait for.", "tm", 10.5)
    f.text(20, 230, "Schematic: the widths are not measured.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 06.03

RECORD_CODE = """
import json
import numpy as np
from data import cifar, fetch
raw = np.fromfile(fetch.path("cifar10", "data_batch_1.bin"), dtype=np.uint8)
x, y = cifar.read_records(fetch.path("cifar10", "data_batch_1.bin"))
with open(fetch.path("cifar10", "batches.meta.txt")) as f:
    names = [line.strip() for line in f if line.strip()]
img = x[0]
assert raw[0] == y[0] and (raw[1:3073].reshape(3, 32, 32) == img).all()
print(json.dumps({"bytes": int(raw.size), "label": int(y[0]), "name": names[int(y[0])],
                  "head": raw[:8].tolist(), "green": raw[1025:1029].tolist(), "blue": raw[2049:2053].tolist(),
                  "planes": (img / 255).round(2).tolist()}))
"""


def record0603():
    d = in_project("06.03", RECORD_CODE)
    if d["bytes"] != 10000 * 3073:
        raise SystemExit(f"data_batch_1.bin: {d['bytes']} bytes, not 10,000 records of 3073")
    f = Fig("record0603", f"CIFAR-10's first training record, as data_batch_1.bin holds it: a label byte, then "
                          f"1024 bytes of red, 1024 of green, 1024 of blue, each 32 rows of 32", 292)
    x0, x1, y0, h = 20, 620, 34, 30
    lw = 46
    cw = (x1 - x0 - lw) / 3
    f.text(x0, 20, "one record: 3073 bytes, and the next record starts straight after it", "tm", 11)
    f.rect(x0, y0, lw, h, "a af", 2)
    f.text(x0 + lw / 2, y0 + 19, str(d["label"]), "ta", 13, "middle", 700, mono=True)
    f.text(x0 + lw / 2, y0 + h + 15, "label", "ta", 10.5, "middle")
    starts = (d["head"][1:5], d["green"], d["blue"])
    for k, (name, first) in enumerate(zip(("red", "green", "blue"), starts)):
        bx = x0 + lw + k * cw
        f.rect(bx, y0, cw, h, "s fs", 2)
        f.text(bx + 8, y0 + 19, " ".join(str(v) for v in first) + " ...", "t", 11, mono=True)
        f.text(bx + cw / 2, y0 + h + 15, f"{name}: 1024 bytes, row by row", "tm", 10.5, "middle")
    cell = 3
    py = 120
    f.text(x0, py - 18, f"the same 3072 bytes as an array of shape (3, 32, 32), each byte 0 to 255; "
                        f"label {d['label']} is {d['name']}", "t", 11.5, weight=600)
    for k, name in enumerate(("red", "green", "blue")):
        gx = x0 + k * 130
        grid(f, gx, py, d["planes"][k], cell, 0, 1, "t", photo=True)
        f.text(gx + 48, py + 96 + 16, name, "t", 11, "middle")
    nx = x0 + 3 * 130 + 10
    for i, line in enumerate(("read_records: the file as bytes,", "in rows of 3073; the first byte of",
                              "a row is its label, the rest its", "pixels, reshaped to (3, 32, 32).",
                              "", "load: scaled to 0..1, then each", "channel standardised with the",
                              "training set's mean and sd")):
        f.text(nx, py + 10 + 14 * i, line, "tm", 10.5)
    return f


CROPS_CODE = """
import json
import numpy as np
from data import cifar
from data.augment import crop_flip
x, y = cifar.load("train", 1)
batch = np.repeat(x[:1], 4, axis=0)
out = crop_flip(batch, 4, np.random.default_rng(2))
rng = np.random.default_rng(2)                    # the same draws, in crop_flip's order
down, across, flip = rng.integers(0, 9, 4), rng.integers(0, 9, 4), rng.random(4) < 0.5
padded = np.pad(batch, ((0, 0), (0, 0), (4, 4), (4, 4)))
for i in range(4):
    want = padded[i, :, down[i]:down[i] + 32, across[i]:across[i] + 32]
    assert np.array_equal(out[i], want[:, :, ::-1] if flip[i] else want), i
gray = lambda a: np.clip((a * cifar.STD[:, None, None] + cifar.MEAN[:, None, None]).mean(0), 0, 1).round(2).tolist()
print(json.dumps({"image": gray(x[0]), "padded": gray(padded[0]), "crops": [gray(o) for o in out],
                  "down": down.tolist(), "across": across.tolist(), "flip": flip.tolist(),
                  "name": cifar.CLASSES[int(y[0])]}))
"""


def crops0603():
    d = in_project("06.03", CROPS_CODE)
    f = Fig("crops0603", f"CIFAR-10's first training image, a {d['name']}, padded by 4 pixels of the average colour, "
                         f"and four crops and mirror images crop_flip made of it (the mean of the three channels "
                         f"drawn)", 236)
    cell = 2.6
    x0, y0 = 20, 44
    f.text(x0, 24, "as it is, 32 by 32", "t", 11, weight=600)
    grid(f, x0, y0, d["image"], cell, 0, 1, "t", photo=True)
    px = x0 + 32 * cell + 34
    f.text(px, 24, "padded, 40 by 40", "t", 11, weight=600)
    grid(f, px, y0, d["padded"], cell, 0, 1, "t", photo=True)
    f.line(x0 + 32 * cell + 6, y0 + 16 * cell, px - 6, y0 + 16 * cell, "s", arrow=True)
    for i in range(4):                               # each crop's window on the padded image
        f.add(f'<rect class="a" x="{px + d["across"][i] * cell:.1f}" y="{y0 + d["down"][i] * cell:.1f}" '
              f'width="{32 * cell:.1f}" height="{32 * cell:.1f}" stroke-width="1.25" stroke-dasharray="3 2"/>')
    cx = px + 40 * cell + 30
    gap = (620 - cx - 4 * 32 * cell) / 3
    f.text(cx, 24, "what four passes see: a new crop, mirrored half the time", "ta", 11, weight=600)
    for i, crop in enumerate(d["crops"]):
        gx = cx + i * (32 * cell + gap)
        grid(f, gx, y0, crop, cell, 0, 1, "t", photo=True)
        dr, dc = d["down"][i] - 4, d["across"][i] - 4
        if d["flip"][i]:                         # the mirror image moves the other way across
            dc = -dc
        moved =", ".join(p for p in ((f"{abs(dr)} {'up' if dr > 0 else 'down'}" if dr else ""),
                                      (f"{abs(dc)} {'left' if dc > 0 else 'right'}" if dc else "")) if p) or "centred"
        f.text(gx + 16 * cell, y0 + 32 * cell + 15, f"pass {i + 1}", "ta", 10.5, "middle", 600)
        f.text(gx + 16 * cell, y0 + 32 * cell + 29, moved, "tm", 10, "middle")
        f.text(gx + 16 * cell, y0 + 32 * cell + 42, "mirrored" if d["flip"][i] else "not mirrored", "tm", 10, "middle")
    f.text(x0, 214, "The dashed squares are the four windows on the padded image. A window that starts at its top "
                    "left shows the picture moved", "tm", 10.5)
    f.text(x0, 228, "4 pixels down and right; where the window passes the edge, the padding comes in.", "tm", 10.5)
    return f


def gap0603():
    r = figart.experiment("cifar", at="06.03")
    ways = [("fc", "fully\nconnected", "s"), ("conv", "convolu-\ntional", "s"), ("conv-augmented", "crops and\nflips", "a")]
    f = Fig("gap0603", "Accuracy on the 2000 training images and on 2000 test images, three ways, three seeds each: "
                       "a ring per seed, the bar their mean, the whisker from the lowest seed to the highest", 270)
    for i, (key, title) in enumerate((("test_accuracy", "test accuracy"), ("train_accuracy", "training accuracy"))):
        groups = [(name, seeds_of(r.runs, label, key), style) for label, name, style in ways]
        figart.seeds_chart(f, (10 + 315 * i, 8, 305, 256), groups, ylabel=title, ylim=(0.3, 1) if i else (0.3, 0.55))
    return f


# ------------------------------------------------------------------ 06.04

COUNT_CODE = """
import json
from models.resnet import layers, resnet
out = []
for n in (1, 3, 9):
    for residual in (False, True):
        m = resnet(n, residual)
        out.append([n, residual, layers(m), sum(p.numel() for p in m.parameters())])
print(json.dumps(out))
"""

PAPER_WEIGHTS = {20: "0.27M", 56: "0.85M"}      # He et al., table 6 (# params), as the page quotes it


def resnet0604():
    counts = in_project("06.04", COUNT_CODE)
    by = {}
    for n, residual, nl, w in counts:
        by.setdefault(nl, set()).add(w)
    if any(len(ws) != 1 for ws in by.values()):
        raise SystemExit(f"plain and residual should have the same weights: {counts}")
    f = Fig("resnet0604", "He et al.'s network for CIFAR-10, 6n + 2 layers with weights: plain, or with a shortcut "
                          "around every pair of convolutions (the residual network)", 330)
    y, h = 40, 44
    parts = [("image", "3 x 32 x 32", "m f", 62), ("conv 3 x 3", "16 maps", "s f", 70),
             ("stage 1", "n blocks: 16 maps,\n32 by 32", "a af", 104), ("stage 2", "n blocks: 32 maps,\n16 by 16", "a af", 104),
             ("stage 3", "n blocks: 64 maps,\n8 by 8", "a af", 104), ("mean", "of each map:\n64 numbers", "s f", 70),
             ("Linear", "10 scores", "s f", 58)]
    gap = (620 - 20 - sum(p[3] for p in parts)) / (len(parts) - 1)
    x = 20
    centres = []
    for name, sub, cls, w in parts:
        f.rect(x, y, w, h, cls, 6, dash=cls.startswith("m"))
        tcls = "ta" if cls.startswith("a") else "t"
        f.text(x + w / 2, y + 17, name, tcls, 11.5, "middle", 700)
        for k, line in enumerate(sub.split("\n")):
            f.text(x + w / 2, y + 31 + 11 * k, line, "tm", 9.5, "middle")
        centres.append((x, w))
        x += w + gap
    for (xa, wa), (xb, _) in zip(centres, centres[1:]):
        f.line(xa + wa + 1, y + h / 2, xb - 1, y + h / 2, "s", arrow=True)
    f.text(20, y - 14, "batch norm after every convolution, then relu; the first convolution of stages 2 and 3 "
                       "steps 2 pixels, halving the maps", "tm", 10.5)
    # one block, plain and residual, under stage 2's first block
    by_, bh = 126, 26
    f.text(20, by_, "a block: two 3 by 3 convolutions", "t", 11.5, weight=700)
    for k, (title, res) in enumerate((("plain", False), ("residual", True))):
        bx = 20 + k * 312
        yy = by_ + 36                              # the chain's centre line is yy + 22
        f.text(bx, yy - 12, title, "ta" if res else "t", 11, weight=700)
        chain = [("x", 20), ("conv, BN, relu", 96), ("conv, BN", 66)] + ([("+", 24)] if res else []) + [("relu", 40)]
        cx = bx
        plus = None
        for i, (label, w) in enumerate(chain):
            if i:
                f.line(cx - 10, yy + 22, cx - 2, yy + 22, "s", arrow=True)
            if label == "x":
                f.text(cx + 6, yy + 26, "x", "t", 12, weight=700, mono=True)
            elif label == "+":
                f.circle(cx + 12, yy + 22, 11, "a af")
                f.text(cx + 12, yy + 27, "+", "ta", 14, "middle", 700, mono=True)
                plus = cx + 12
            else:
                f.rect(cx, yy + 22 - bh / 2, w, bh, "s f", 5)
                f.text(cx + w / 2, yy + 26, label, "t", 10.5, "middle")
            cx += w + 12
        if res:
            f.path(f"M{bx + 9} {yy + 13} L{bx + 9} {yy - 4} L{plus} {yy - 4} L{plus} {yy + 10}", "a", arrow=True)
            f.text((bx + 9 + plus) / 2 + 20, yy - 9, "the shortcut: x itself", "ta", 10.5, "middle", 600)
    # option A, where a block halves the maps and doubles them
    oy = 236
    f.text(20, oy, "Where a block halves the maps and doubles their number, the shortcut is the paper's option A, "
                   "with no weights:", "t", 11)
    f.text(20, oy + 17, "every second pixel of every second row, x[:, :, ::2, ::2], then as many maps of zeros as "
                        "the block adds. So plain and residual", "tm", 10.5)
    f.text(20, oy + 32, "networks of one depth have exactly the same weights:", "tm", 10.5)
    tx = 20
    rows = [(nl, list(by[nl])[0]) for nl in sorted(by)]
    for i, (nl, w) in enumerate(rows):
        n = (nl - 2) // 6
        s = f"n = {n}: {nl} layers, {comma(w)} weights" + (f" (paper: {PAPER_WEIGHTS[nl]})" if nl in PAPER_WEIGHTS else "")
        f.text(tx, oy + 56 + 16 * i, s, "ta" if nl in PAPER_WEIGHTS else "t", 11, mono=True)
    return f


def long_runs():
    """The recorded long run: {(kind, depth): seed folders}, its config."""
    d = os.path.join(figlib.TRACK, "experiments", "recorded", "resnet")
    cfg = figart.config(figart.seed_dirs(os.path.join(d, "plain20"))[0])
    out = {}
    for kind in ("plain", "residual"):
        for depth in cfg["depths"]:
            out[kind, depth] = figart.seed_dirs(os.path.join(d, f"{kind}{depth}"))
    return out, cfg


def long0604():
    runs, cfg = long_runs()
    shallow, deep = cfg["depths"]
    f = Fig("long0604", f"The recorded long run: training error (dashed, counted during each pass on its crops and "
                        f"flips) and test error (solid) after each pass, {shallow} and {deep} layers, mean of "
                        f"{cfg['seeds']} seeds, the band from the lowest seed to the highest", 300)
    for i, kind in enumerate(("plain", "residual")):
        series = []
        for depth, style in ((shallow, "s"), (deep, "a")):
            for key, dash in (("train_error", True), ("test_error", False)):
                xs, mean, lo, hi = figart.over_seeds(runs[kind, depth], key, x="epoch")
                label = f"{depth} layers" if not dash else ""
                series.append(figart.Series(label, xs, mean, style, dash, lo if dash else None, hi if dash else None))
        ax = figart.plot(f, (8 + 316 * i, 6, 308, 288), series, xlabel="pass over the training images",
                         ylabel=f"{kind}: error %", ylim=(45, 95), yticks=[50, 60, 70, 80, 90],
                         xticks=list(range(1, cfg["epochs"] + 1)), legend="end")
    return f


def short0604():
    r = figart.experiment("resnet", at="06.04")
    cfg = figart.config(figart.seed_dirs(os.path.join(r.runs, "plain8"))[0])
    shallow, deep = cfg["depths"]
    groups = []
    for kind, style in (("plain", "s"), ("residual", "a")):
        for depth in (shallow, deep):
            groups.append((f"{kind}\n{depth} layers", seeds_of(r.runs, f"{kind}{depth}", "train_error"), style))
    f = Fig("short0604", f"The page's short run: training error after {cfg['epochs']} passes over {cfg['n_train']} "
                         f"images, {cfg['seeds']} seeds each: a ring per seed, the bar their mean", 260)
    figart.seeds_chart(f, (8, 4, 624, 252), groups, ylabel="training error %", ylim=(70, 90))
    return f


FIGS = [
    ("06.01-slide", slide0601),
    ("06.01-moved", moved0601),
    ("06.01-maps", maps0601),
    ("06.02-import", import0602),
    ("06.02-same", same0602),
    ("06.02-clock", clock0602),
    ("06.03-record", record0603),
    ("06.03-crops", crops0603),
    ("06.03-gap", gap0603),
    ("06.04-resnet", resnet0604),
    ("06.04-long", long0604),
    ("06.04-short", short0604),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
