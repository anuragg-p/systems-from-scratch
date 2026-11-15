"""Figures for research module 01, Backpropagation: an autograd engine (lessons 01.01-01.04).

    python3 -B art/research/figs01.py            every figure of the module
    python3 -B art/research/figs01.py 01.02      one lesson's

Every number comes from the track's own code (tracks/research), never typed in here. The
experiments are run as the lessons run them (figart.experiment): nudge's table for the V of
01.01, two_groups' logs for 01.04's curves. Where a figure needs more than a script prints (the
backward pass node by node, which units of a network are off, where a trained network puts its
boundary), the generator imports the track's own Value, MLP, neuron, two_groups and train and
runs them here, then stops with an error unless what it got agrees with what the experiment
printed:

  01.01  f(x) = x^3 - 2x at x = 1.5 (experiments/nudge.py): its chords for h = 0.5, and the
         error table of `python3 -m experiments.nudge`
  01.02  the neuron of experiments/graph.py, with each node's _backward wrapped so that every
         call is a frame; checked against `python3 -m experiments.graph`'s table
  01.03  MLP(2, [4, 4, 1]) with seed 0 at the point (0.5, -1.5), as experiments/network.py
         builds it; checked against its "12 with no gradient"
  01.04  two_groups' default run and the same with sizes=[1] (curves from their logs), and
         seed 0 of each trained again here with the same data, seed and steps (checked against
         the accuracies the runs printed) for the boundaries
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
sys.path.insert(0, os.path.dirname(HERE))         # art/: steps
import figlib  # noqa: E402
import figart  # noqa: E402
import steps  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "01"


def track_code():
    """The track's own packages (engine, experiments, data), importable here."""
    if figlib.TRACK not in sys.path:
        sys.path.insert(0, figlib.TRACK)
    sys.dont_write_bytecode = True


def same(what, mine, real):
    if mine != real:
        raise SystemExit(f"figs01: {what}: computed here {mine!r}, the run printed {real!r}")


# ------------------------------------------------------------------ 01.01 the nudge

def chord0101():
    """f near x = 1.5: the tangent, and the two chords a nudge of h = 0.5 measures."""
    track_code()
    from engine import nudge
    from experiments import nudge as ex
    x0 = ex.CONFIG["x"]
    h = 0.5
    exact = ex.by_hand(x0, [x0, 2.0])[0]
    central = nudge.derivative(ex.f, x0, h)
    one = (ex.f(x0 + h) - ex.f(x0)) / h               # the one-sided estimate, as experiments/nudge.py has it
    lo, hi = 0.7, 2.3
    xs = [lo + (hi - lo) * i / 300 for i in range(301)]

    def through(px, py, m):
        return [py + m * (x - px) for x in xs]

    f = Fig("chord0101", f"The slope of f(x) = x^3 - 2x at x = {x0}, and the chords a nudge of h = {h} measures", 300)
    series = [
        figart.Series("f(x) = x^3 - 2x", xs, [ex.f(x) for x in xs], "s", width=2.25),
        figart.Series(f"tangent: slope {sig(exact)}", xs, through(x0, ex.f(x0), exact), "s", dash="1.5 3.5", width=1.5),
        figart.Series(f"central: slope {sig(central)}", xs, through(x0 - h, ex.f(x0 - h), central), "a"),
        figart.Series(f"one-sided: slope {sig(one)}", xs, through(x0, ex.f(x0), one), "s", dash="6 4", width=1.25),
    ]
    ax = figart.plot(f, (8, 8, 624, 286), series, xlabel="x", ylabel="f(x)", ylim=(-2, 7), xlim=(lo, hi),
                     xticks=[1, 1.5, 2], yticks=[-2, 0, 2, 4, 6])
    for x, name, dx, dy, anchor in ((x0 - h, "x - h", -8, -8, "end"), (x0, "x", 8, 17, "start"),
                                    (x0 + h, "x + h", 8, 17, "start")):
        ax.vline(x, None)
        ax.dot(x, ex.f(x), "a fa" if x != x0 else "s f", 3.5)
        ax.note(x, ex.f(x), name, "ta" if x != x0 else "t", 11, anchor, dx=dx, dy=dy)
    return f


def nudge_table():
    """The error table of python3 -m experiments.nudge at 01.01: (hs, central, one-sided, best h)."""
    r = figart.experiment("nudge", at="01.01")
    rows = re.findall(r"^\s+(\d\.?\d*e[-+]\d+)\s+(\S+)\s+(\S+)$", r.out, re.M)
    hs, c, o = ([float(row[i]) for row in rows] for i in range(3))
    best = figart.value(r.out, r"closest central nudge: h = (\S+)")
    return hs, c, o, best


def v0101():
    hs, central, one, best = nudge_table()
    track_code()
    from engine import nudge
    default = nudge.derivative.__defaults__[0]
    f = Fig("v0101", "How far the nudge lands from the derivative 4.75, against the size of the nudge h", 330)
    pts = sorted(zip(hs, central, one))
    series = [figart.Series("central: (f(x+h) - f(x-h)) / 2h", [p[0] for p in pts], [p[1] for p in pts], "a"),
              figart.Series("one-sided: (f(x+h) - f(x)) / h", [p[0] for p in pts], [p[2] for p in pts], "s",
                            dash="5 4", width=1.25)]
    ax = figart.plot(f, (8, 8, 624, 318), series, xlabel="the nudge h (log scale)",
                     ylabel="how far the estimate is from 4.75 (log scale)", logx=True, logy=True, legend=None,
                     ylim=(1e-11, 3), yticks=[1e-10, 1e-8, 1e-6, 1e-4, 1e-2, 1])
    ax.note(1e-2, 1e-1, "one-sided", "t", 11, "end", dx=-6, dy=-4)
    ax.note(1e-2, 1e-4, "central", "ta", 11, "start", dx=8, dy=4, weight=600)
    ax.vline(best, None, "a")
    ax.note(best, 1e-11, f"closest: h = {figart.tick_label(best)}", "ta", 10.5, "start", dx=5, dy=-6)
    ax.vline(default, None)
    ax.note(default, 3, f"derivative()'s default, {figart.tick_label(default)}", "tm", 10.5, "end", dx=-5, dy=14)
    ax.note(1e-11, 1e-9, "too small: the digits of", "tm", 10.5, "middle")
    ax.note(1e-11, 1e-9, "f(x+h) - f(x-h) cancel", "tm", 10.5, "middle", dy=14)
    ax.note(1e-3, 1e-9, "too big: a chord,", "tm", 10.5, "middle")
    ax.note(1e-3, 1e-9, "not the tangent", "tm", 10.5, "middle", dy=14)
    return f


# ------------------------------------------------------------------ 01.02 the backward pass

# Where each node of the neuron sits, and its short name: (x, y) of its centre.
LAYOUT = {
    "x1": (56, 66), "w1": (56, 118), "x2": (56, 182), "w2": (56, 234),
    "x1*w1": (226, 92), "x2*w2": (226, 208), "s": (396, 150), "b": (396, 266),
    "n": (560, 208), "o": (560, 340),
}
OPS = {"x1*w1": (141, 92), "x2*w2": (141, 208), "s": (311, 150), "n": (478, 208), "o": (560, 274)}
SHORT = {"x1": "x1", "x2": "x2", "w1": "w1", "w2": "w2", "b": "b", "x1*w1": "x1*w1", "x2*w2": "x2*w2",
         "x1*w1 + x2*w2": "s", "n = ... + b": "n", "o = tanh(n)": "o"}


def backward_trace():
    """The neuron of experiments/graph.py built from the track's own Value, and o.backward() run
    with every node's _backward wrapped: (o, [(short name, Value)], frames), a frame being
    (the node whose _backward ran, the gradients before, the gradients after)."""
    track_code()
    from experiments import graph as G
    o, named = G.neuron(*[G.CONFIG[k] for k in G.NAMES])
    nodes = [(SHORT[n], v) for n, v in named]
    name = {id(v): n for n, v in nodes}
    frames = []

    def grads():
        return {n: v.grad for n, v in nodes}

    for n, v in nodes:
        if v._backward is not None:
            def wrapped(orig=v._backward, v=v):
                before = grads()
                orig()
                frames.append((name[id(v)], before, grads()))
            v._backward = wrapped
    o.backward()
    # The run's own table: every node's value and gradient, to 4 decimals.
    r = figart.experiment("graph", at="01.02")
    printed = {SHORT[m.group(1).strip()]: (m.group(2), m.group(3))
               for m in re.finditer(r"^(\S.*?)\s+(?:\S+)\s+(-?\d+\.\d{4})\s+(-?\d+\.\d{4})$", r.out, re.M)}
    same("01.02 nodes", sorted(printed), sorted(n for n, _ in nodes))
    for n, v in nodes:
        same(f"01.02 node {n}", (f"{v.data:.4f}", f"{v.grad:.4f}"), printed[n])
    return o, nodes, frames, name


def rule(n, v, name, after):
    """The chain rule at node n (its _backward just ran), with the numbers: one line per input."""
    a = v._prev
    g = sig(v.grad, 4)
    N = f"({n})" if "*" in n else n                   # (x1*w1).grad, not x1*w1.grad
    if v._op == "+":
        return [f"{name[id(p)]}.grad += {N}.grad = {sig(after[name[id(p)]], 4)}" for p in a]
    if v._op == "*":
        p, q = a
        g6 = sig(v.grad, 6)                           # six places, so that the product checks by hand
        return [f"{name[id(p)]}.grad += {name[id(q)]} x {N}.grad = {sig(q.data, 6)} x {g6} = {sig(after[name[id(p)]], 6)}",
                f"{name[id(q)]}.grad += {name[id(p)]} x {N}.grad = {sig(p.data, 6)} x {g6} = {sig(after[name[id(q)]], 6)}"]
    if v._op == "tanh":
        p = a[0]
        return [f"{name[id(p)]}.grad += (1 - {n}^2) x {n}.grad = (1 - {sig(v.data, 4)}^2) x {g} = "
                f"{sig(after[name[id(p)]], 4)}"]
    raise SystemExit(f"figs01: no rule drawn for {v._op!r}")


def draw_neuron(f, nodes, name, shown, here, op=None, grads=True):
    """The neuron's graph: a box per Value, a circle per operation. shown: {name: grad} of the
    nodes backward() has reached (the rest show no gradient yet); here: names lit, and op the
    node whose operation is lit with them."""
    spec, edges = {}, []
    for n, v in nodes:
        x, y = LAYOUT[n]
        spec[n] = ("value", x, y, n, v.data, shown.get(n))
        if v._prev:
            ox, oy = OPS[n]
            spec["op " + n] = ("op", ox, oy, v._op, None, None)
            edges += [(name[id(p)], "op " + n) for p in v._prev] + [("op " + n, n)]
    lit = set(here) | ({"op " + op} if op else set())
    figart.graph(f, spec, edges, here=lit, grads=grads, value_w=96)


def backward0102():
    o, nodes, frames, name = backward_trace()
    f = Fig("backward0102", "backward() over one neuron, o = tanh(x1 w1 + x2 w2 + b), one node at a time", 430)
    f.text(14, 18, "arrows: the forward pass, inputs to o.   backward(): the grads, from o back to the inputs",
           "tm", 11)
    value = {n: v for n, v in nodes}
    with steps.step(f, "The forward pass has run: each Value holds its number, the graph remembers how each "
                       "was made, and every grad is still 0."):
        draw_neuron(f, nodes, name, {}, [], grads=False)
    first = frames[0][1]
    with steps.step(f, f"backward() starts at the output: o.grad = {sig(first['o'])}, since o moves one for one "
                       f"with itself."):
        draw_neuron(f, nodes, name, {"o": first["o"]}, ["o"])
        f.text(14, 392, "o.grad = 1", "ta", 12, weight=600, mono=True)
    reached = {"o": first["o"]}
    for k, (n, before, after) in enumerate(frames):
        v = value[n]
        ins = [name[id(p)] for p in v._prev]
        for p in ins:
            reached[p] = after[p]
        lines = rule(n, v, name, after)
        if v._op == "tanh":
            cap = f"tanh passes it back: the slope of tanh at n is 1 - o^2, so n.grad = {sig(after[ins[0]], 4)}."
        elif v._op == "+":
            cap = (f"The + that made {n} passes {n}.grad back unchanged, to {ins[0]} and to {ins[1]}: "
                   f"{sig(v.grad, 4)} each.")
        else:
            cap = (f"The * that made {n}: each input gets ({n}).grad times the other input's value: "
                   f"{ins[0]}.grad = {sig(after[ins[0]], 4)}, {ins[1]}.grad = {sig(after[ins[1]], 4)}.")
        if k == len(frames) - 1:
            cap += " Every Value now holds d o / d itself, all from one pass."
        with steps.step(f, cap):
            draw_neuron(f, nodes, name, dict(reached), ins + [n], op=n)
            for i, line in enumerate(lines):
                f.text(14, 392 + 18 * i, line, "ta", 12, weight=600 if i == 0 else None, mono=True)
    steps.check(f.svg())
    return f


def twice0102():
    """A Value used twice: b = a * a. The two lines of __mul__'s _backward each add a share to
    a.grad, because self and other are the same Value; the run gives their sum."""
    track_code()
    from engine.value import Value
    a = Value(3.0)
    b = a * a
    b.backward()
    share = a.data * b.grad                           # other.data * out.grad, and self.data * out.grad
    same("01.02 a * a: the two shares add up to a.grad", 2 * share, a.grad)
    same("01.02 a * a: d/da of a^2 is 2a", a.grad, 2 * a.data)
    f = Fig("twice0102", "A Value used twice gets a share of the gradient from each use, and the shares add", 206)
    spec = {"a": ("value", 112, 70, "a", a.data, a.grad), "op": ("op", 300, 70, "*", None, None),
            "b": ("value", 500, 70, "b = a * a", b.data, b.grad)}
    for d in ("M160 60 C 210 34, 250 42, 284 62", "M160 80 C 210 106, 250 98, 284 78"):
        f.path(d, "s", arrow=True)
    figart.graph(f, spec, [("op", "b")], value_w=128)
    f.text(214, 28, "a, as self", "tm", 10.5, "middle")
    f.text(214, 124, "a, as other", "tm", 10.5, "middle")
    x = 24
    f.text(x, 152, f"self.grad  += other.data x out.grad:  a.grad += {sig(a.data)} x {sig(b.grad)} = {sig(share)}",
           "ta", 11.5, mono=True)
    f.text(x, 170, f"other.grad += self.data x out.grad:   a.grad += {sig(a.data)} x {sig(b.grad)}, "
                   f"now {sig(a.grad)}", "ta", 11.5, mono=True)
    f.text(x, 190, f"a.grad = {sig(a.grad)}: the derivative of a^2 is 2a = {sig(2 * a.data)}", "t", 11.5, weight=600)
    return f


# ------------------------------------------------------------------ 01.03 a network

def network0103():
    track_code()
    from engine.value import MLP
    from experiments import network as N
    sizes, point = N.CONFIG["sizes"], N.CONFIG["point"]
    model = MLP(2, sizes, seed=0)
    out = model(point)
    for p in model.parameters():
        p.grad = 0.0
    out.backward()
    zero = sum(1 for p in model.parameters() if p.grad == 0)
    r = figart.experiment("network", at="01.03")
    same("01.03 seed 0 weights with no gradient", zero, int(figart.value(r.out, r"^seed 0: .*?, (\d+) with no gradient")))
    same("01.03 seed 0 weights", len(model.parameters()), int(figart.value(r.out, r"^seed 0: (\d+) weights")))
    # which units are off at the point: run the layers one at a time, as MLP.__call__ does
    off, x = [], point
    for layer in model.layers:
        x = layer(x)
        off.append([not n.linear and v.data <= 0 for n, v in zip(layer.neurons, x)])
    full = [2] + list(sizes)
    f = Fig("network0103", f"MLP(2, {sizes}) with seed 0 at the point {tuple(point)}: its weights, and the units "
                           f"whose relu is off there", 300)
    box = (8, 34, 430, 230)
    xs = figart.network(f, box, full, max_units=5, here=(1, 2),
                        names=["the point", "layer 1", "layer 2", "output"])
    # mark the units that are off: a dashed ring, and the units' x, y as network() places them
    bh = box[3] - (16 + 14)
    for li, flags in enumerate(off):
        k = full[li + 1]
        gap = bh / 5
        y0 = box[1] + bh / 2 - gap * (k - 1) / 2
        for j, is_off in enumerate(flags):
            if is_off:
                cx, cy = xs[li + 1], y0 + gap * j
                f.add(f'<circle class="m f" cx="{cx:.1f}" cy="{cy:.1f}" r="9" stroke-width="1.5" stroke-dasharray="3 3"/>')
                f.text(cx, cy + 3.5, "0", "tm", 10, "middle", mono=True)
    for i in range(len(full) - 1):
        nin, nout = full[i], full[i + 1]
        mid = (xs[i] + xs[i + 1]) / 2
        f.text(mid, 22, f"{nout * (nin + 1)}", "ta", 13, "middle", 700, True)
        f.text(mid, box[1] + box[3] + 14, f"{nout} x ({nin} + 1)", "tm", 10.5, "middle", mono=True)
    f.text(8, 22, "weights:", "tm", 11)
    # the key, and one neuron spelled out
    x0 = 470
    f.text(x0, 50, "one unit:", "tm", 11)
    f.text(x0, 70, "relu(w1 x1 + ... + b)", "t", 12, mono=True)
    f.text(x0, 88, "a weight per input, and a bias", "tm", 10.5)
    f.text(x0, 106, "the output unit has no relu", "tm", 10.5)
    f.add(f'<circle class="m f" cx="{x0 + 9}" cy="140" r="9" stroke-width="1.5" stroke-dasharray="3 3"/>')
    f.text(x0 + 9, 143.5, "0", "tm", 10, "middle", mono=True)
    f.text(x0 + 26, 138, "off at this point: its sum", "tm", 10.5)
    f.text(x0 + 26, 152, "is not above 0, so it gives 0", "tm", 10.5)
    total = len(model.parameters())
    f.text(x0, 192, f"{' + '.join(str(full[i + 1] * (full[i] + 1)) for i in range(len(full) - 1))} = {total}",
           "ta", 13, weight=700, mono=True)
    f.text(x0, 210, "weights in all", "tm", 10.5)
    f.text(x0, 240, f"{zero} of them get no gradient", "t", 11.5, weight=600)
    f.text(x0, 256, "here: they sit behind a unit", "tm", 10.5)
    f.text(x0, 270, "that is off", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 01.04 training

class _Quiet:
    """Stands in for lab.Run when training is redone here: train() logs to it, nothing kept."""

    def log(self, **_):
        pass


def trained(sizes, seed, cfg):
    """seed's model trained again here exactly as experiments/two_groups.py trains it: its data,
    the model, and the training accuracy."""
    import numpy as np
    from data.points import two_groups
    from engine.value import MLP
    from experiments import two_groups as T
    rng = np.random.default_rng(seed)                 # what lab.Run(cfg, seed).rng is
    x, y = two_groups(cfg["n_train"], cfg["noise"], rng)
    model = MLP(2, sizes, seed=seed)
    T.train(model, x, y, cfg["steps"], cfg["lr"], _Quiet())
    _, acc = T.hinge_loss(model, x, y)
    return x, y, model, acc


def contour(score, xlim, ylim, nx, ny):
    """Segments where score(a, b) = 0, by marching squares on an nx by ny grid: [((a, b), (a, b))]."""
    gx = [xlim[0] + (xlim[1] - xlim[0]) * i / nx for i in range(nx + 1)]
    gy = [ylim[0] + (ylim[1] - ylim[0]) * j / ny for j in range(ny + 1)]
    v = [[score(a, b) for a in gx] for b in gy]
    segs = []

    def cut(p, q, vp, vq):
        t = vp / (vp - vq)
        return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))

    for j in range(ny):
        for i in range(nx):
            corners = [((gx[i], gy[j]), v[j][i]), ((gx[i + 1], gy[j]), v[j][i + 1]),
                       ((gx[i + 1], gy[j + 1]), v[j + 1][i + 1]), ((gx[i], gy[j + 1]), v[j + 1][i])]
            pts = []
            for k in range(4):
                (p, vp), (q, vq) = corners[k], corners[(k + 1) % 4]
                if (vp > 0) != (vq > 0):
                    pts.append(cut(p, q, vp, vq))
            for k in range(0, len(pts) - 1, 2):
                segs.append((pts[k], pts[k + 1]))
    return segs


def boundary0104():
    track_code()
    from experiments import two_groups as T
    cfg = dict(T.CONFIG)
    deep = figart.experiment("two_groups")
    line = figart.experiment("two_groups", "sizes=[1]")
    panels = []
    for sizes, r, title in (([1], line, "no hidden layer: MLP(2, [1])"),
                            (cfg["sizes"], deep, f"two hidden layers: MLP(2, {cfg['sizes']})")):
        x, y, model, acc = trained(sizes, 0, cfg)
        same(f"01.04 seed 0 accuracy, sizes {sizes}", f"{acc:.2f}",
             re.search(r"^seed 0: .*accuracy \S+ -> (\S+),", r.out, re.M).group(1))
        panels.append((x, y, model, acc, title))
    f = Fig("boundary0104", "Seed 0's fifty training points and where each model, trained, puts the line "
                            "between the groups", 300)
    xlim, ylim = (-1.4, 2.4), (-1.0, 1.6)
    w, h = 296, 196
    for k, (x, y, model, acc, title) in enumerate(panels):
        X, Y = 8 + k * (w + 32), 40
        ax = figart.Axes(f, X, Y, w, h, xlim, ylim)
        f.rect(X, Y, w, h, "m", 0)
        f.text(X, Y - 22, title, "ta" if k == 1 else "t", 12, weight=600)
        f.text(X, Y - 7, f"{round(acc * len(y))} of {len(y)} training points on the right side", "tm", 10.5)
        segs = contour(lambda a, b: model([a, b]).data, xlim, ylim, 76, 52)
        d = " ".join(f"M{ax.px(p[0]):.1f} {ax.py(p[1]):.1f}L{ax.px(q[0]):.1f} {ax.py(q[1]):.1f}" for p, q in segs)
        f.add(f'<path class="a" d="{d}" stroke-width="2" stroke-linecap="round"/>')
        for (a, b), g in zip(x, y):
            if ax.inside(float(a), float(b)):
                f.circle(ax.px(float(a)), ax.py(float(b)), 3.2, "s fa" if g == 1 else "s f")
    ly = 40 + h + 26
    f.circle(14, ly - 4, 3.2, "s f")
    f.text(24, ly, "group 0", "t", 11)
    f.circle(90, ly - 4, 3.2, "s fa")
    f.text(100, ly, "group 1", "t", 11)
    f.line(170, ly - 4, 192, ly - 4, "a")
    f.text(198, ly, "score = 0: above it on one side, below on the other", "t", 11)
    return f


def loss0104():
    deep = figart.experiment("two_groups")
    line = figart.experiment("two_groups", "sizes=[1]")
    f = Fig("loss0104", "The hinge loss over 80 steps, three seeds each: a straight line stalls, a network with "
                        "hidden layers keeps going down", 300)
    series = []
    for r, label, style, dash in ((line, "no hidden layer", "s", "5 4"), (deep, "two hidden layers of 8", "a", False)):
        xs, mean, lo, hi = figart.over_seeds(figart.seed_dirs(r.runs), "loss")
        series.append(figart.Series(label + " (3 seeds)", xs, mean, style, dash, lo, hi))
    figart.plot(f, (8, 8, 624, 286), series, xlabel="step", ylabel="hinge loss on the 50 training points (log scale)",
                logy=True, legend="top")
    return f


FIGURES = {
    "01.01": [("01.01-chord", chord0101), ("01.01-v", v0101)],
    "01.02": [("01.02-backward", backward0102), ("01.02-twice", twice0102)],
    "01.03": [("01.03-network", network0103)],
    "01.04": [("01.04-boundary", boundary0104), ("01.04-loss", loss0104)],
}


def main(argv):
    want = argv or list(FIGURES)
    for lid in want:
        for name, make in FIGURES[lid]:
            print(write(MOD, name, make()))


if __name__ == "__main__":
    main(sys.argv[1:])
