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
         on that image with np.random.default_rng(0); python3 -m experiments.cifar (3 seeds)
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


def grid(f, x, y, values, cell, lo=None, hi=None, cls="t", frame="m", signed=False):
    """A map of numbers as squares of one fill class at an opacity from 0 (lo or below) to 1 (hi);
    signed: negative numbers in the foreground and positive in the accent, each scaled by the largest
    size. Squares of equal opacity on a row are drawn as one path, to keep the file small."""
    rows = len(values)
    cols = len(values[0])
    flat = [v for row in values for v in row]
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


FIGS = [
    ("06.01-slide", slide0601),
    ("06.01-moved", moved0601),
    ("06.01-maps", maps0601),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
