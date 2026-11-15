"""Figures for research module 02, Tensors: a small PyTorch (lessons 02.01-02.05).

    python3 -B art/research/figs02.py            all of them
    python3 -B art/research/figs02.py 02.03      one lesson's

Every number drawn comes from the reference code as it stands at the figure's lesson: either a
run of the lesson's experiment (figart.experiment) or a few lines run against the project's own
engine at that lesson (at(), below), which print what the figure shows as JSON. Nothing here
computes a gradient, a softmax or a byte offset itself.

    02.01-objects    tanh(x * y + x) on three pairs: the Values the scalar engine makes, the
                     tensors the tensor engine makes, and the gradients backward gives
    02.01-overhead   experiments.speed at n = 1 .. 100000: time against n, both engines
    02.02-broadcast  (3, 1) + (1, 4): the copies the forward makes, the sums the backward makes
    02.03-matmul     x @ w on small whole numbers, and the two matrix products of its backward
    02.03-curves     experiments.groups_tensors: the hinge loss of its three seeds
    02.04-grad       cross-entropy of three scores: softmax p, the right class y, the gradient p - y
    02.05-names      a Sequential's modules and the names its weights get in state_dict
    02.05-file       the bytes of the checkpoint experiments.checkpoint writes, to scale
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figart  # noqa: E402
import figlib  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "02"


def at(lesson, code):
    """Run code (Python) in the project as it stands at lesson, with that project's engine on
    the path; it prints one JSON value, which is returned."""
    d = figart.project(lesson)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d)
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"figs02: the code at {lesson} failed:\n{r.stdout}{r.stderr}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def num(v, digits=3):
    """A number as a cell shows it: whole numbers without a point, others to 3 significant digits."""
    if float(v) == int(v) and abs(v) < 1e6:
        return str(int(v))
    return sig(float(v), digits)


def cells(f, x, y, values, cw, ch, cls="s f", tcls="t", dash=False, size=11, outline=None):
    """values (a list of rows) as a grid of cells at (x, y); outline: a class to draw one
    rectangle round the whole grid (one object). Returns (w, h)."""
    for i, row in enumerate(values):
        for j, v in enumerate(row):
            f.rect(x + j * cw, y + i * ch, cw, ch, cls, 0, dash=dash)
            if v is not None:
                f.text(x + j * cw + cw / 2, y + i * ch + ch / 2 + size * 0.36, v if isinstance(v, str) else num(v),
                       tcls, size, "middle", mono=True)
    w, h = cw * len(values[0]), ch * len(values)
    if outline:
        f.rect(x - 3, y - 3, w + 6, h + 6, outline, 4)
    return w, h


# ------------------------------------------------------------------ 02.01

OBJECTS = """
import json, engine as torch
x = torch.tensor([0.5, -1.0, 2.0], dtype=torch.float64, requires_grad=True)
y = torch.tensor([1.5, 0.25, -0.5], dtype=torch.float64, requires_grad=True)
m = x * y
u = m + x
out = u.tanh()
vals = [t.data.tolist() for t in (x, y, m, u, out)]
out.backward(torch.ones_like(out))
print(json.dumps({"vals": vals, "xg": x.grad.data.tolist(), "yg": y.grad.data.tolist()}))
"""


def objects0201():
    r = at("02.01", OBJECTS)
    heads = ["x", "y", "x * y", "x * y + x", "tanh"]
    cols = [list(c) for c in r["vals"]]
    f = Fig("objects0201", "tanh(x * y + x) on three pairs of numbers: 15 Values in the scalar engine, "
            "5 tensors in the tensor engine, then the gradients backward gives x and y", 392)
    left, step, cw, ch = 132, 100, 66, 22
    cx = [left + step * k + step / 2 for k in range(5)]
    for k, h in enumerate(heads):
        f.text(cx[k], 20, h, "t", 11.5, "middle", 600, mono=True)
    # the scalar engine: a Value per number per step, each its own object
    y0 = 38
    f.text(14, y0 + 30, "the scalar engine", "t", 12, weight=700)
    f.text(14, y0 + 46, "a Value per number:", "tm", 10.5)
    f.text(14, y0 + 60, "15 objects", "tm", 10.5)
    for i in range(3):
        for k in range(5):
            bx, by = cx[k] - cw / 2, y0 + i * (ch + 7)
            f.rect(bx, by, cw, ch, "s f", 4)
            f.text(cx[k], by + ch / 2 + 4, num(cols[k][i]), "t", 11, "middle", mono=True)
    # the tensor engine: one tensor per step, holding all three numbers
    y1 = y0 + 3 * (ch + 7) + 34
    f.text(14, y1 + 22, "the tensor engine", "ta", 12, weight=700)
    f.text(14, y1 + 38, "a tensor per step:", "tm", 10.5)
    f.text(14, y1 + 52, "5 objects", "tm", 10.5)
    for k in range(5):
        cells(f, cx[k] - cw / 2, y1, [[v] for v in cols[k]], cw, ch, "m f", "t", outline="a")
        f.text(cx[k], y1 + 3 * ch + 18, "shape (3,)", "tm", 10, "middle", mono=True)
    # backward: the gradients of x and y, starting from ones at the output
    y2 = y1 + 3 * ch + 50
    f.text(14, y2 + 22, "backward", "ta", 12, weight=700)
    f.text(14, y2 + 38, "from ones at out:", "tm", 10.5)
    f.text(14, y2 + 52, "x.grad and y.grad", "tm", 10.5)
    cells(f, cx[0] - cw / 2, y2, [[v] for v in r["xg"]], cw, ch, "a af", "ta", outline="a")
    cells(f, cx[1] - cw / 2, y2, [[v] for v in r["yg"]], cw, ch, "a af", "ta", outline="a")
    cells(f, cx[4] - cw / 2, y2, [[1.0], [1.0], [1.0]], cw, ch, "m f", "tm", outline="m")
    f.text(cx[0], y2 + 3 * ch + 18, "x.grad", "ta", 10.5, "middle", mono=True)
    f.text(cx[1], y2 + 3 * ch + 18, "y.grad", "ta", 10.5, "middle", mono=True)
    f.text(cx[4], y2 + 3 * ch + 18, "ones_like(out)", "tm", 10.5, "middle", mono=True)
    f.line(cx[4] - cw / 2 - 8, y2 + 1.5 * ch, cx[1] + cw / 2 + 10, y2 + 1.5 * ch, "a", arrow=True)
    f.text((cx[1] + cx[4]) / 2, y2 + 1.5 * ch - 7, "each step's rule, on every number at once", "ta", 10.5, "middle")
    return f


def overhead0201():
    ns = [1, 10, 100, 1000, 10000, 100000]
    scalar, tensor = [], []
    for n in ns:
        out = figart.experiment("speed", f"n={n}", at="02.01").out
        scalar.append(figart.value(out, r"scalar Values.*\(\s*(\d+) ns a number") * n / 1000)
        tensor.append(figart.value(out, r"one tensor.*\(\s*(\d+) ns a number") * n / 1000)
    f = Fig("overhead0201", "Forward and backward through tanh(x * y + x): microseconds against how many "
            "numbers, scalar Values and one tensor, log scales", 300)
    series = [figart.Series("scalar Values", ns, scalar, "s"),
              figart.Series("one tensor", ns, tensor, "a")]
    ax = figart.plot(f, (8, 6, 624, 288), series, xlabel="numbers (n)", ylabel="microseconds, forward and backward",
                     logx=True, logy=True, legend="right")
    for n, a, b in zip(ns, scalar, tensor):
        ax.dot(n, a, "s f", 3)
        ax.dot(n, b, "a fa", 3)
    k = ns.index(10000)
    for k in range(len(ns)):
        above = scalar[k] < tensor[k]                     # the tensor slower: say so over its point
        ax.note(ns[k], tensor[k], f"{sig(scalar[k] / tensor[k], 2)} x", "ta", 10.5, "start" if above else "middle",
                dx=6 if above else 0, dy=-8 if above else 17)
    return f


# ------------------------------------------------------------------ 02.02

BROADCAST = """
import json, numpy as np, engine as torch
a = torch.tensor([[1.0], [2.0], [3.0]], requires_grad=True)
b = torch.tensor([[10.0, 20.0, 30.0, 40.0]], requires_grad=True)
out = a + b
g = np.array([[1.0, 0.0, 2.0, 1.0], [0.0, 1.0, 1.0, 0.0], [2.0, 1.0, 0.0, 1.0]], dtype=np.float32)
out.backward(torch.tensor(g))
print(json.dumps({"a": a.data.tolist(), "b": b.data.tolist(), "out": out.data.tolist(), "g": g.tolist(),
                  "ag": a.grad.data.tolist(), "bg": b.grad.data.tolist(),
                  "shapes": [list(t.shape) for t in (a, b, out, a.grad, b.grad)]}))
"""


def broadcast0202():
    r = at("02.02", BROADCAST)
    a, b, out, g = r["a"], r["b"], r["out"], r["g"]
    f = Fig("broadcast0202", "Forward, a of shape (3, 1) plus b of shape (1, 4): each is repeated to (3, 4). "
            "Backward, the gradient comes back as (3, 4) and is summed over the repeats", 318)
    cw, ch = 32, 22
    # forward
    f.text(14, 22, "forward: a + b", "t", 12, weight=700)
    y = 44
    xa, xb, xo = 40, 236, 444
    rows = len(out)
    cols = len(out[0])
    for i in range(rows):
        for j in range(cols):
            real = j == 0
            f.rect(xa + j * cw, y + i * ch, cw, ch, "s f" if real else "m f", 0, dash=not real)
            f.text(xa + j * cw + cw / 2, y + i * ch + 15, num(a[i][0]), "t" if real else "tm", 11, "middle", mono=True)
    for i in range(rows):
        for j in range(cols):
            real = i == 0
            f.rect(xb + j * cw, y + i * ch, cw, ch, "s f" if real else "m f", 0, dash=not real)
            f.text(xb + j * cw + cw / 2, y + i * ch + 15, num(b[0][j]), "t" if real else "tm", 11, "middle", mono=True)
    cells(f, xo, y, out, cw, ch)
    gw, gh = cw * cols, ch * rows
    f.text(xa + gw + 26, y + gh / 2 + 5, "+", "t", 15, "middle", mono=True)
    f.text(xb + gw + 30, y + gh / 2 + 5, "=", "t", 15, "middle", mono=True)
    f.text(xa, y + gh + 17, "a (3, 1), copied across", "tm", 10.5)
    f.text(xb, y + gh + 17, "b (1, 4), copied down", "tm", 10.5)
    f.text(xo, y + gh + 17, "a + b (3, 4)", "tm", 10.5)
    # backward
    y2 = 190
    f.text(14, y2 - 14, "backward: each copy's gradient goes back to the number it copied, and adds up",
           "t", 12, weight=700)
    xg = 236
    cells(f, xg, y2 + 12, g, cw, ch)
    f.text(xg, y2 + 12 + gh + 17, "out.grad (3, 4)", "tm", 10.5)
    # a.grad: the sum of each row, to the left
    xag = 64
    cells(f, xag, y2 + 12, [[v[0]] for v in r["ag"]], cw, ch, "a af", "ta")
    f.line(xg - 8, y2 + 12 + gh / 2, xag + cw + 10, y2 + 12 + gh / 2, "a", arrow=True)
    f.text((xg + xag + cw) / 2, y2 + 12 + gh / 2 - 8, "sum(1)", "ta", 10.5, "middle", mono=True)
    f.text(xag + cw / 2, y2 + 12 + gh + 17, "a.grad (3, 1)", "ta", 10.5, "middle", mono=True)
    # b.grad: the sum of each column, to the right
    xbg = 452
    cells(f, xbg, y2 + 12 + ch, [r["bg"][0]], cw, ch, "a af", "ta")
    f.line(xg + gw + 8, y2 + 12 + gh / 2, xbg - 10, y2 + 12 + gh / 2, "a", arrow=True)
    f.text((xg + gw + xbg) / 2, y2 + 12 + gh / 2 - 8, "sum(0)", "ta", 10.5, "middle", mono=True)
    f.text(xbg, y2 + 12 + 2 * ch + 17, "b.grad (1, 4)", "ta", 10.5, mono=True)
    f.text(14, 306, f"the {num(a[1][0])} in a was used in 4 places, so its gradient is the sum of 4 shares: "
           f"{' + '.join(num(v) for v in g[1])} = {num(r['ag'][1][0])}", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 02.03

MATMUL = """
import json, engine as torch
x = torch.tensor([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], requires_grad=True)
w = torch.tensor([[1.0, 0.0, -1.0], [2.0, 1.0, 0.0]], requires_grad=True)
out = x @ w
out.backward(torch.ones_like(out))
print(json.dumps({"x": x.data.tolist(), "w": w.data.tolist(), "out": out.data.tolist(),
                  "xT": x.T.data.tolist(), "wT": w.T.data.tolist(), "g": [[1.0] * 3] * 3,
                  "wg": w.grad.data.tolist(), "xg": x.grad.data.tolist()}))
"""


def matmul0203():
    r = at("02.03", MATMUL)
    f = Fig("matmul0203", "x @ w, and its backward: two more matrix products, each giving a gradient "
            "the shape of its own tensor", 372)
    cw, ch = 30, 20
    rows = [
        ("forward", "out = x @ w", [("x", r["x"], "s"), ("w", r["w"], "s"), ("out", r["out"], "s")]),
        ("gradient of w", "w.grad = x.T @ out.grad", [("x.T", r["xT"], "s"), ("out.grad", r["g"], "m"),
                                                      ("w.grad", r["wg"], "a")]),
        ("gradient of x", "x.grad = out.grad @ w.T", [("out.grad", r["g"], "m"), ("w.T", r["wT"], "s"),
                                                      ("x.grad", r["xg"], "a")]),
    ]
    y = 14
    for title, formula, mats in rows:
        f.text(14, y + 12, title, "ta" if title != "forward" else "t", 12, weight=700)
        f.text(14, y + 28, formula, "tm", 10.5, mono=True)
        x = 200
        top = y + 4
        for k, (name, vals, style) in enumerate(mats):
            cls, tcls = {"s": ("s f", "t"), "m": ("m f", "tm"), "a": ("a af", "ta")}[style]
            w, h = cells(f, x, top, vals, cw, ch, cls, tcls, size=10.5)
            shape = f"({len(vals)}, {len(vals[0])})"
            f.text(x + w / 2, top + h + 15, f"{name} {shape}", tcls, 10.5, "middle", mono=True)
            if k < 2:
                f.text(x + w + 20, top + h / 2 + 5, "@" if k == 0 else "=", "t", 14, "middle", mono=True)
                x += w + 40
        y += 116
    f.text(14, 362, f"with out.grad all ones, each number of w.grad adds up a column of x "
           f"({' + '.join(num(v[0]) for v in r['x'])} = {num(r['wg'][0][0])}), "
           f"each of x.grad a row of w ({' + '.join(num(v) for v in r['w'][0])} = {num(r['xg'][0][0])})",
           "tm", 10.5)
    return f


def curves0203():
    r = figart.experiment("groups_tensors", at="02.03")
    f = Fig("curves0203", "The hinge loss of the two groups, trained as matrices: 2-16-16-1, 200 points, "
            "1000 steps, three seeds", 260)
    series = []
    for i, d in enumerate(figart.seed_dirs(r.runs)):
        xs, ys = figart.column(figart.read_log(d), "loss")
        series.append(figart.Series(f"seed {i}", xs, ys, "a" if i == 0 else "m", dash=False if i == 0 else (True if i == 1 else "2 3")))
    figart.plot(f, (8, 6, 624, 248), series, xlabel="step", ylabel="hinge loss", ylim=(0, None), legend="right")
    return f


# ------------------------------------------------------------------ 02.04

GRAD = """
import json, engine as torch
F = torch.nn.functional
s = torch.tensor([[2.0, 1.0, 0.1]], dtype=torch.float64, requires_grad=True)
loss = F.cross_entropy(s, torch.tensor([0]))
loss.backward()
p = F.softmax(s.detach(), 1)
print(json.dumps({"s": s.data[0].tolist(), "p": p.data[0].tolist(), "g": s.grad.data[0].tolist(),
                  "loss": loss.item()}))
"""


def bars(f, x, y, w, h, values, lo, hi, title, sub, style="s", labels=("0", "1", "2"), fmt=None):
    """A small bar chart of three values on a shared zero line, in the box (x, y, w, h)."""
    f.text(x + w / 2, y + 12, title, {"a": "ta", "s": "t", "m": "tm"}[style], 12, "middle", 600, mono=True)
    f.text(x + w / 2, y + 27, sub, "tm", 10.5, "middle")
    top, bot = y + 46, y + h - 22
    def py(v):
        return top + (hi - v) / (hi - lo) * (bot - top)
    zero = py(0)
    f.line(x + 6, zero, x + w - 6, zero, "m")
    n = len(values)
    bw = (w - 24) / n
    for i, v in enumerate(values):
        bx = x + 12 + i * bw + bw * 0.18
        y1, y2 = sorted((py(v), zero))
        cls = {"a": "a af", "s": "s fs", "m": "m fs"}[style]
        if abs(y2 - y1) > 0.5:
            f.rect(bx, y1, bw * 0.64, y2 - y1, cls, 1)
        txt = (fmt or num)(v)
        f.text(bx + bw * 0.32, (y1 - 5) if v >= 0 else (y2 + 13), txt, {"a": "ta", "s": "t", "m": "tm"}[style],
               10.5, "middle", mono=True)
        f.text(bx + bw * 0.32, bot + 16, labels[i], "tm", 10, "middle", mono=True)


def grad0204():
    r = at("02.04", GRAD)
    f = Fig("grad0204", "Cross-entropy of three scores with class 0 the right one: the softmax p, the "
            "right answer y, and the gradient of the loss with respect to the scores, p - y", 250)
    w = 150
    gap = (640 - 4 * w) / 5
    xs = [gap + k * (w + gap) for k in range(4)]
    lo, hi = -0.8, 2.2
    four = lambda v: f"{v:.4f}"  # noqa: E731
    bars(f, xs[0], 6, w, 236, r["s"], lo, hi, "s", "the scores", "s")
    bars(f, xs[1], 6, w, 236, r["p"], lo, hi, "p = softmax(s)", "add up to 1", "s", fmt=four)
    bars(f, xs[2], 6, w, 236, [1.0, 0.0, 0.0], lo, hi, "y", "class 0 is right", "m")
    bars(f, xs[3], 6, w, 236, r["g"], lo, hi, "s.grad", "p - y", "a", fmt=four)
    f.text(xs[2] + w + gap / 2, 124, "=", "t", 14, "middle", mono=True)
    f.text(xs[1] + w + gap / 2, 124, "-", "t", 14, "middle", mono=True)
    return f


# ------------------------------------------------------------------ 02.05

NAMES = """
import json, engine as torch
nn = torch.nn
torch.manual_seed(0)
net = nn.Sequential(nn.Linear(2, 16), nn.ReLU(), nn.Linear(16, 16), nn.ReLU(), nn.Linear(16, 2))
mods = [(name, type(m).__name__, m.extra_repr()) for name, m in net.named_modules() if name]
params = [(k, list(v.shape)) for k, v in net.state_dict().items()]
print(json.dumps({"mods": mods, "params": params}))
"""


def names0205():
    r = at("02.05", NAMES)
    f = Fig("names0205", "nn.Sequential of five modules, and the names state_dict gives their weights: "
            "the module's name, a dot, the attribute's name", 300)
    f.text(14, 22, "model = nn.Sequential(...)", "t", 12, weight=700, mono=True)
    f.text(420, 22, "model.state_dict()", "ta", 12, weight=700, mono=True)
    y = 40
    box_h, gap = 38, 12
    where = {}
    for name, kind, extra in r["mods"]:
        has = kind == "Linear"
        f.rect(14, y, 300, box_h, "s f" if has else "m f", 5)
        f.text(26, y + 16, f"{name}", "ta" if has else "tm", 12, weight=700, mono=True)
        f.text(46, y + 16, kind, "t" if has else "tm", 12, mono=True)
        if has:
            parts = dict(p.split("=") for p in extra.split(", "))
            f.text(46, y + 31, f"in {parts['in_features']}, out {parts['out_features']}", "tm", 10.5)
            f.text(304, y + 16, ".weight", "t", 10.5, "end", mono=True)
            f.text(304, y + 31, ".bias", "t", 10.5, "end", mono=True)
            where[name] = (y + 12, y + 27)
        y += box_h + gap
    yy = 40
    rows = {}
    for k, shape in r["params"]:
        f.rect(420, yy, 206, 24, "a af", 4)
        f.text(430, yy + 16, k, "ta", 11.5, weight=600, mono=True)
        f.text(616, yy + 16, "(" + ", ".join(map(str, shape)) + ("," if len(shape) == 1 else "") + ")",
               "tm", 10.5, "end", mono=True)
        rows[k] = yy + 12
        yy += 30
    for k, ty in rows.items():
        mod, attr = k.split(".")
        sy = where[mod][0 if attr == "weight" else 1] - 4
        f.path(f"M308 {sy:.1f} C 360 {sy:.1f}, 368 {ty:.1f}, 416 {ty:.1f}", "m", arrow=True)
    f.text(420, yy + 14, "ReLU has no weights, so 1 and 3", "tm", 10.5)
    f.text(420, yy + 28, "have no names here", "tm", 10.5)
    return f


def file0205():
    r = figart.experiment("checkpoint", at="02.05")
    path = os.path.join(r.runs, "seed0", "model.safetensors")
    with open(path, "rb") as fh:
        raw = fh.read()
    n = int.from_bytes(raw[:8], "little")
    header = json.loads(raw[8:8 + n])
    meta = header.pop("__metadata__", {})
    total = len(raw)
    f = Fig("file0205", f"The checkpoint experiments.checkpoint writes, {total} bytes, to scale: the header's "
            f"length, the header, then every tensor's numbers back to back", 316)
    X0, X1 = 14, 626
    scale = (X1 - X0) / total
    y, h = 74, 40
    f.text(14, 22, "model.safetensors", "t", 12, weight=700, mono=True)
    f.text(626, 22, f"{total} bytes", "tm", 11, "end", mono=True)
    # the three parts, to scale
    xh = X0 + 8 * scale
    xd = X0 + (8 + n) * scale
    f.rect(X0, y, xh - X0, h, "a fa", 0)
    f.rect(xh, y, xd - xh, h, "a af", 0)
    f.text((xh + xd) / 2, y + 17, "header", "ta", 11.5, "middle", 600)
    f.text((xh + xd) / 2, y + 31, f"{n} bytes of JSON", "ta", 10, "middle")
    order = sorted(header.items(), key=lambda kv: kv[1]["data_offsets"][0])
    small = []
    for k, (name, spec) in enumerate(order):
        b0, b1 = spec["data_offsets"]
        x0, x1 = xd + b0 * scale, xd + b1 * scale
        f.rect(x0, y, x1 - x0, h, "s fs", 0)
        if x1 - x0 > 80:
            f.text((x0 + x1) / 2, y + 17, name, "t", 10.5, "middle", mono=True)
            f.text((x0 + x1) / 2, y + 31, f"{b1 - b0} bytes", "tm", 10, "middle")
        else:
            small.append((name, (x0 + x1) / 2, b1 - b0))
    # the small tensors are named over the bar, with a line down to their place
    left = [t for t in small if t[1] < (X0 + X1) / 2]
    right = [t for t in small if t[1] >= (X0 + X1) / 2]
    for group, x_from, x_to in ((left, xd - 40, xd + 200), (right, X1 - 150, X1 - 10)):
        if not group:
            continue
        slots = [x_from + (x_to - x_from) * (i + 0.5) / len(group) for i in range(len(group))]
        for (name, cx, nb), sx in zip(group, slots):
            f.text(sx, y - 24, name, "t", 10.5, "middle", mono=True)
            f.text(sx, y - 12, f"{nb} bytes", "tm", 9.5, "middle")
            f.line(sx, y - 9, cx, y - 1, "m")
    f.text(X0, y + h + 16, "8 bytes: the header's length", "ta", 10.5)
    f.text(xd, y + h + 16, f"data: {total - 8 - n} bytes, {(total - 8 - n) // 4} float32 numbers", "t", 10.5)
    # the bytes themselves
    y2 = 162
    f.text(14, y2, "the first bytes of each part, as they are in the file", "t", 12, weight=700)
    hexs = " ".join(f"{c:02x}" for c in raw[:8])
    f.text(14, y2 + 24, hexs, "ta", 11, mono=True)
    f.text(14 + tw(hexs, 11, True) + 14, y2 + 24, f"-> {n}, little-endian", "tm", 10.5)
    text = raw[8:8 + 54].decode("ascii")
    f.text(14, y2 + 46, text + " ...", "t", 11, mono=True)
    pad = len(raw[8:8 + n]) - len(raw[8:8 + n].rstrip(b" "))
    f.text(14, y2 + 64, f"... ending in {pad} space{'s' if pad != 1 else ''}, so the numbers start at byte "
           f"{8 + n}, a multiple of 8", "tm", 10.5)
    first = order[0]
    hexd = " ".join(f"{c:02x}" for c in raw[8 + n:8 + n + 8])
    import struct
    v0, v1 = struct.unpack("<2f", raw[8 + n:8 + n + 8])
    f.text(14, y2 + 90, hexd, "t", 11, mono=True)
    f.text(14 + tw(hexd, 11, True) + 14, y2 + 90, f"-> {first[0]}[0] = {v0:.4f}, {first[0]}[1] = {v1:.4f}: "
           "4 bytes a number, little-endian", "tm", 10.5)
    f.text(14, y2 + 118, "names in the header are in sorted order, so 0.bias comes before 0.weight; "
           f"metadata: {json.dumps(meta)}", "tm", 10.5)
    f.text(14, y2 + 136, "nothing in the file is code: loading it reads numbers, and runs nothing", "tm", 10.5)
    return f


FIGURES = [
    ("02.01-objects", objects0201), ("02.01-overhead", overhead0201),
    ("02.02-broadcast", broadcast0202),
    ("02.03-matmul", matmul0203), ("02.03-curves", curves0203),
    ("02.04-grad", grad0204),
    ("02.05-names", names0205), ("02.05-file", file0205),
]


def main():
    want = sys.argv[1:]
    for name, make in FIGURES:
        if want and not any(name.startswith(w) for w in want):
            continue
        print(write(MOD, name, make()))


if __name__ == "__main__":
    main()
