"""Figures for research module 08, The transformer: a GPT (lessons 08.01-08.05).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs08.py [08.02 ...]
                                    all of them, or those whose name starts so (DIR keeps the runs)

Every bar, curve, cell and number comes from the reference code (tracks/research), run as the page
runs it, or from the recorded long run the page shows:

  08.01  python3 -m experiments.self_attention (the page's run, 3 seeds): the footnote's table and the
         three scores of every seed; the mask and the stepped figure train seed 0's masked OneHead
         again in the project at 08.01 (the page's settings; its honest score must equal the run's
         seed 0) and read 12 characters of the test text with it
  08.02  python3 -m experiments.heads (the page's run): every seed's test bits, and seed 0's weights
         on the first 32 test characters from its summary.json; the block's and the heads' sizes
         from models/gpt.py at 08.02
  08.03  python3 -m experiments.positions (the page's run): the order test, the longer windows; the
         heads with positions train seed 0's model with learned positions again in the project at
         08.03 (its test bits must equal the run's seed 0) and read the same 32 characters
  08.04  python3 -m experiments.gpt (the page's short run): its ladder, its curves and summaries; the
         recorded long run, experiments/recorded/gpt/ (its logs and summaries, as committed)
  08.05  python3 -m experiments.sampling (the page's run, the small model it trains): every way's
         perplexity per seed; the distribution after the first prompt from that model, trained again
         in the project at 08.05 (its perplexity of the real text must equal the run's)

PyTorch must be installed; nothing needs a download. The runs take about four minutes in all on the
machine in NOTES.md.
"""
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
sys.path.insert(0, os.path.dirname(HERE))         # art/: steps.py, for the stepped figure
import figart  # noqa: E402
import figlib  # noqa: E402
import steps  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "08"
_memo = {}


def in_project(at, code):
    """Run python code in the project as it stands at lesson `at`; the JSON it prints last (once per
    process for the same code)."""
    if (at, code) in _memo:
        return _memo[at, code]
    d = figart.project(at)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d)
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"python in the project at {at} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    _memo[at, code] = json.loads(r.stdout.strip().splitlines()[-1])
    return _memo[at, code]


def shown(c):
    """A character as a figure writes it: the space as _, the newline as \\n."""
    return {" ": "_", "\n": "\\n"}.get(c, c)


def said(c):
    return {" ": "a space", "\n": "a newline"}.get(c, repr(c))


def seeds_of(d, key):
    return [figart.summary(x)[key] for x in figart.seed_dirs(d)]


def mean(xs):
    return sum(xs) / len(xs)


def shade(f, x, y, w, h, op, cls="fa"):
    op = round(max(0.0, min(1.0, op)), 2)
    if op >= 0.03:
        f.add(f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill-opacity="{op}"/>')


def weight_map(f, x, y, w, cell):
    """A head's weights, a row per position and a column per position it may see, darker for more: the
    cells of each shade (the square root of the weight, to a tenth) drawn as one path, to keep the file
    small."""
    n = len(w)
    paths = {}
    for i in range(n):
        for j in range(i + 1):
            op = round(min(1.0, w[i][j] ** 0.5), 1)
            if op >= 0.1:
                paths.setdefault(op, []).append(f"M{x + j * cell:.1f} {y + i * cell:.1f}h{cell}v{cell}h{-cell}z")
    for op, parts in sorted(paths.items()):
        f.add(f'<path class="fa" d="{"".join(parts)}" fill-opacity="{op}"/>')
    f.rect(x, y, n * cell, n * cell, "m", 0)


# ------------------------------------------------------------------ the runs

def sa_run():
    return figart.experiment("self_attention", at="08.01")


def heads_run():
    return figart.experiment("heads", at="08.02")


def pos_run():
    return figart.experiment("positions", at="08.03")


def gpt_run():
    return figart.experiment("gpt", at="08.04")


def sampling_run():
    return figart.experiment("sampling", at="08.05")


def ladder_rows():
    """Part 1 of the page's gpt run: [(name, bits)], module 07's ladder as the run printed it."""
    part = gpt_run().out.split("1. Module 07's ladder")[1].split("\n\n")[0]
    rows = [(m.group(1).strip(), float(m.group(2))) for m in re.finditer(r"^   (.+?) +(\d\.\d{3})$", part, re.M)]
    if len(rows) != 11:
        raise SystemExit(f"gpt: expected 11 rows of the ladder, read {len(rows)}")
    return rows


def rung(name):
    return next(b for n, b in ladder_rows() if n.startswith(name))


# ------------------------------------------------------------------ 08.01

LINE = "Not in my house"
SHOWN = 12

ONEHEAD_CODE = """
import json, tempfile
import torch
import lab
from data import shakespeare
from experiments import self_attention as sa
from experiments.language import train
from models.gpt import self_attend
cfg = lab.config(sa.CONFIG, ["out=" + tempfile.mkdtemp()])
V = len(shakespeare.chars())
dev = torch.device("cpu")
train_t, test_t = (torch.from_numpy(shakespeare.split(s)) for s in ("train", "test"))
text = shakespeare.decode(shakespeare.split("test"))
start = text.index(%r)
ids = test_t[start:start + %d][None]
run = lab.Run(cfg, 0, label="masked")
torch.manual_seed(0)
model = sa.OneHead(V, cfg.width, **sa.KINDS["masked"])
train(model, cfg, run, dev, train_t)
model.eval()
past = sa.last_bits(model, test_t, cfg.context)
with torch.no_grad():
    a = model.attention
    w = self_attend(*a.qkv(model.tokens(ids)), a.mask, a.scale)[1][0]
    p = torch.softmax(model(ids)[0], dim=-1)
vocab = shakespeare.chars()
rows = []
for i in range(ids.shape[1]):
    top = p[i].topk(3)
    nxt = text[start + i + 1]
    rows.append({"weights": w[i].tolist(), "guesses": [[vocab[int(j)], float(v)] for v, j in zip(top.values, top.indices)],
                 "next": nxt, "p_next": float(p[i, vocab.index(nxt)])})
print(json.dumps({"past": past, "window": text[start:start + %d], "rows": rows}))
""" % (LINE, SHOWN, SHOWN)


def onehead():
    """Seed 0's masked OneHead, trained again as the page trains it, reading SHOWN test characters."""
    d = in_project("08.01", ONEHEAD_CODE)
    page = seeds_of(os.path.join(sa_run().runs, "masked"), "past_bits")[0]
    if f"{d['past']:.6f}" != f"{page:.6f}":
        raise SystemExit(f"the OneHead trained here scores {d['past']}, the page's seed 0 {page}")
    return d


def mask0801():
    d = onehead()
    win, rows = d["window"], d["rows"]
    n = len(win)
    cell = 21
    f = Fig("mask0801", f"The mask as a table, on {n} characters of a line of the test text: 0 where a row may "
                        f"look, -inf above the diagonal; and the weights of the page's trained model (seed 0) after "
                        f"the softmax, exactly 0 above the diagonal", 356)
    panels = ((34, "added to the scores: the mask", "t"), (352, "the weights after the softmax (seed 0)", "ta"))
    y0 = 66
    for k, (x0, title, tcls) in enumerate(panels):
        f.text(x0, 20, title, tcls, 11.5, weight=600)
        for j, c in enumerate(win):
            f.text(x0 + j * cell + cell / 2, y0 - 8, shown(c), "tm", 10.5, "middle", mono=True)
        for i, c in enumerate(win):
            f.text(x0 - 5, y0 + i * cell + 14, shown(c), "tm", 10.5, "end", mono=True)
            for j in range(n):
                X, Y = x0 + j * cell, y0 + i * cell
                if j > i:
                    f.rect(X, Y, cell, cell, "m fs", 0, sw=False)
                    f.text(X + cell / 2, Y + 13.5, "-inf" if k == 0 else "0", "tm", 7.5 if k == 0 else 9, "middle",
                           mono=True)
                elif k == 0:
                    f.text(X + cell / 2, Y + 14, "0", "t", 9.5, "middle", mono=True)
                else:
                    w = rows[i]["weights"][j]
                    shade(f, X, Y, cell, cell, 0.6 * w ** 0.6)
                    s = "1" if w > 0.995 else f"{w:.2f}"[1:]
                    f.text(X + cell / 2, Y + 14, s, "t", 8.5, "middle", mono=True)
        f.rect(x0, y0, n * cell, n * cell, "m", 0)
        f.text(x0 - 5, y0 - 8, "i \\ j", "tm", 9.5, "end")
    yb = y0 + n * cell + 22
    f.text(34, yb, "row i: the position that asks; column j: the position it looks at; _ is a space.", "tm", 10.5)
    f.text(34, yb + 15, f"Each row of weights adds up to 1 over the positions it may see; the first row's 1 is all on "
                        f"itself.", "tm", 10.5)
    return f


def step0801():
    """The stepped figure: the trained OneHead reading its window a position at a time."""
    d = onehead()
    win, rows = d["window"], d["rows"]
    n = len(win)
    f = Fig("step0801", f"The page's trained model (seed 0) reading {n} characters of the test text a position at a "
                        f"time: the weights of each row over the positions it may see, and its three likeliest next "
                        f"characters", 268)
    x0, cw, gap = 32, 40, 8
    xs = [x0 + i * (cw + gap) for i in range(n)]
    base, top = 132, 52
    f.text(x0, 22, "weights over the positions it may see", "ta", 11.5, weight=600)
    f.line(xs[0] - 4, base, xs[-1] + cw + 4, base, "m")
    for i, c in enumerate(win):
        f.rect(xs[i], 140, cw, 26, "m f", 3, dash=True)
        f.text(xs[i] + cw / 2, 158, shown(c), "tm", 12.5, "middle", mono=True)
        f.text(xs[i] + cw / 2, 180, f"position {i}" if i == 0 else str(i), "tm", 9.5, "middle")
    f.text(x0, 206, "its three likeliest next characters", "tm", 11)
    for t, r in enumerate(rows):
        w = r["weights"]
        best = max(range(t + 1), key=lambda j: w[j])
        g = r["guesses"]
        right = [x for x in g if x[0] == r["next"]]
        cap = (f"Position {t}, {said(win[t])}: its weight is on the {t + 1} position{'s' * (t > 0)} up to it, the most, "
               f"{w[best]:.2f}, on position {best} ({said(win[best])}); its likeliest next character is {said(g[0][0])} "
               f"({g[0][1]:.2f}), and what came next, {said(r['next'])}, has "
               f"{r['p_next']:.2f}" + (" (among its three likeliest)." if right else "."))
        with steps.step(f, cap):
            for j in range(t + 1):
                h = (base - top) * w[j]
                if h > 0.5:
                    f.rect(xs[j] + 6, base - h, cw - 12, h, "a af" if j == best else "s fs", 1)
                if w[j] >= 0.05:
                    f.text(xs[j] + cw / 2, base - h - 4, f"{w[j]:.2f}", "ta" if j == best else "tm", 9.5, "middle",
                           mono=True)
            for j in range(t + 1):
                lit = j == t
                f.rect(xs[j], 140, cw, 26, "a af" if lit else "s f", 3)
                f.text(xs[j] + cw / 2, 158, shown(win[j]), "ta" if lit else "t", 12.5, "middle", 700 if lit else None,
                       mono=True)
            for j in range(t + 1, n):
                f.text(xs[j] + cw / 2, 128, "-inf", "tm", 9, "middle", mono=True)
            for k, (c, v) in enumerate(g):
                X = x0 + k * 150
                ok = c == r["next"]
                f.rect(X, 216, max(2, 110 * v), 14, "a af" if ok else "s fs", 2)
                f.text(X, 246, f"{shown(c)!r} {v:.2f}", "ta" if ok else "t", 11.5, weight=700 if ok else None,
                       mono=True)
            f.text(x0 + 450, 228, f"what came: {shown(r['next'])!r}", "t", 11.5, weight=600, mono=True)
            f.text(x0 + 450, 244, f"its chance {r['p_next']:.2f}", "tm", 10.5)
    f.text(x0, 262, "accent: the character that came next, when it is among the three; _ is a space", "tm", 10.5)
    steps.check(f.svg())
    return f


def footnote_rows():
    """Part 1's table: [(d, sd, largest, gradient, sd, largest, gradient)] without and with the division."""
    rows = []
    for m in re.finditer(r"^ +(\d+) +([\d.]+) +([\d.]+) +(\S+) +([\d.]+) +([\d.]+) +(\S+)$", sa_run().out, re.M):
        rows.append(tuple([int(m.group(1))] + [float(m.group(k)) for k in range(2, 8)]))
    if len(rows) != 4:
        raise SystemExit(f"self_attention: expected 4 rows in part 1, read {len(rows)}")
    return rows


def scale0801():
    rows = footnote_rows()
    ds = [r[0] for r in rows]
    cfg = figart.config(figart.seed_dirs(os.path.join(sa_run().runs, "masked"))[0])
    T = cfg["context"]
    f = Fig("scale0801", "The footnote at four sizes: the spread of the scores and the largest softmax weight over 32 "
                         "positions, without and with the division by sqrt(d)", 288)
    panels = [("the scores' sd", 1, (0.7, 45), True, [1, 2, 4, 8, 16, 32]),
              (f"the largest weight (of {T})", 2, (0, 1), False, [0, 0.25, 0.5, 0.75, 1]),
              ("the gradient back", 3, (0, 0.3), False, [0, 0.1, 0.2, 0.3])]
    for k, (title, col, ylim, logy, yt) in enumerate(panels):
        x = 50 + k * 205
        ax = figart.Axes(f, x, 48, 150, 170, (11, 1500), ylim, True, logy)
        ax.draw(xticks=ds, yticks=yt, xlabel="d", xfmt=lambda v: str(int(v)))
        f.text(x - 6, 38, title, "t", 11.5, weight=600)
        for style, off in (("s", 0), ("a", 3)):
            vals = [r[col + off] for r in rows]
            ax.curve(ds, vals, style, width=2)
            for dd, v in zip(ds, vals):
                ax.dot(dd, v, f"{style} {'fa' if style == 'a' else 'f'}", 3)
        if col == 1:
            for dd, v in zip(ds, [r[1] for r in rows]):
                ax.note(dd, v, f"{v:.3g}", "t", 9.5, "start" if dd == ds[0] else "end", dx=7 if dd == ds[0] else -5,
                        dy=4 if dd == ds[0] else -5)
        if col == 2:
            ax.hline(1 / T, f"equal: 1/{T}", side="right")
            ax.note(ds[-1], rows[-1][2], f"{rows[-1][2]:.3f}", "t", 9.5, "end", dx=-6, dy=-5)
            ax.note(ds[-1], rows[-1][5], f"{rows[-1][5]:.3f}", "ta", 9.5, "end", dx=-6, dy=-6)
        if col == 3:
            ax.note(ds[-1], rows[-1][3], f"{rows[-1][3]:.3g}", "t", 9.5, "end", dx=-6, dy=12)
            ax.note(ds[0], rows[0][3], f"{rows[0][3]:.3g}", "t", 9.5, "start", dx=6, dy=-4)
    figart.legend(f, 50, 274, [("without the division: q . k", "s", False),
                               ("divided by sqrt(d): q . k / sqrt(d)", "a", False)], across=True)
    return f


def honest0801():
    r = sa_run()
    groups = []
    for key, name in (("train_bits", "training batch"), ("test_bits", "test, as trained"),
                      ("past_bits", "test, past only")):
        for label, kind, style in (("masked", "masked", "a"), ("no mask", "no_mask", "s")):
            groups.append((f"{label}\n{name}", seeds_of(os.path.join(r.runs, kind), key), style))
    f = Fig("honest0801", "Three seeds of each: bits per character on the last training batch, on the test text read "
                          "as in training, and on the test text with each character from the 32 before it only: a "
                          "ring per seed, the bar their mean", 300)
    ax = figart.seeds_chart(f, (8, 4, 624, 292), groups, ylabel="bits per character (lower is better)",
                            ylim=(3.1, 4.4), yticks=[3.2, 3.4, 3.6, 3.8, 4.0, 4.2, 4.4])
    pairs = rung("pairs")
    ax.hline(pairs, f"07.01's pairs: {pairs:.3f}", side="left")
    for k in (1.5, 3.5):
        X = ax.px(k)
        f.line(X, ax.y, X, ax.y + ax.h, "m", dash=True)
    return f


# ------------------------------------------------------------------ 08.02

BLOCK_CODE = """
import json
from models.gpt import Block, SelfAttention
b = Block(64, 4)
size = lambda m: sum(p.numel() for p in m.parameters())
print(json.dumps({"norm": size(b.norm1), "attention": size(b.attention), "mlp": size(b.mlp), "block": size(b),
                  "up": list(b.mlp.up.weight.shape), "one_head": size(SelfAttention(64, 1))}))
"""


def sizes0802():
    d = in_project("08.02", BLOCK_CODE)
    cfg = figart.config(figart.seed_dirs(os.path.join(heads_run().runs, "blocks4-heads4"))[0])
    if cfg["width"] != 64 or cfg["heads"] != 4:
        raise SystemExit(f"heads: the page's run is not width 64 with 4 heads: {cfg}")
    return d, cfg


def block0802():
    d, cfg = sizes0802()
    W, H = cfg["width"], cfg["heads"]
    inner = d["up"][0]
    f = Fig("block0802", f"One block at the page's sizes: the residual stream, {W} numbers per position, runs straight "
                         f"through; attention and the MLP each read a layer-normalised copy and add their result back",
            262)
    ys = 196
    f.line(22, ys, 626, ys, "a", arrow=True)
    f.text(22, ys + 24, f"x: the residual stream, {W} numbers at each position", "ta", 11, weight=600)
    f.text(626, ys + 24, "to the next block", "tm", 10.5, "end")

    def branch(tap, add, norm_x, box_x, box_w, name, sub, count, note):
        f.path(f"M{tap} {ys} V 96 H {norm_x}", "s", arrow=True)
        f.label_box(norm_x + 2, 80, 80, 32, "layer norm", "s f", "t", 11, False)
        f.text(norm_x + 42, 126, f"{d['norm']} weights", "tm", 9.5, "middle", mono=True)
        f.line(norm_x + 84, 96, box_x - 2, 96, "s", arrow=True)
        f.label_box(box_x, 70, box_w, 52, name, "s fs", "t", 12, False, weight=700, sub=sub, subsize=10)
        f.text(box_x + box_w / 2, 136, f"{count:,} weights", "tm", 9.5, "middle", mono=True)
        f.path(f"M{box_x + box_w} 96 H {add} V {ys - 12}", "s", arrow=True)
        f.circle(add, ys, 10, "a af")
        f.text(add, ys + 4.5, "+", "ta", 14, "middle", 700, mono=True)
        f.text((tap + add) / 2, 40, note, "ta", 11, "middle", 600)
        f.text(add - 6, ys - 22, "dropout, in training", "tm", 9, "end")
    branch(52, 316, 64, 160, 146, "attention", f"{H} heads of {W // H}, causal", d["attention"],
           "between positions")
    branch(342, 598, 354, 450, 138, "MLP", f"{W} -> {inner} -> {W}, GELU", d["mlp"], "each position alone")
    f.text(22, 252, f"x = x + attention(norm1(x)); x = x + mlp(norm2(x)): {d['block']:,} weights in all; the stream "
                    f"itself is only ever added to.", "tm", 10.5)
    return f


def heads_weights():
    r = heads_run()
    s = figart.summary(figart.seed_dirs(os.path.join(r.runs, "blocks4-heads4"))[0])
    return s["weights"], s["window"]


def looks_printed(out):
    """Part 4 of heads' or positions' output: {block: [(back, own, before)] per head}."""
    got = {}
    for m in re.finditer(r"^   block (\d): (.*)$", out, re.M):
        nums = [float(v) for v in m.group(2).split()]
        got[int(m.group(1))] = [tuple(nums[k:k + 3]) for k in range(0, len(nums), 3)]
    return got


def heads0802():
    d, cfg = sizes0802()
    W, H = cfg["width"], cfg["heads"]
    weights, _ = heads_weights()
    if d["attention"] != d["one_head"]:
        raise SystemExit("one head and four do not have the same weights")
    f = Fig("heads0802", f"The width of {W} cut into {H} heads of {W // H}: each head its own slice of the queries, "
                         f"keys and values and its own weights over the window; the same four Linear layers, "
                         f"{d['attention']:,} weights, either way", 296)
    c = 8.5
    x0, y0 = 48, 46
    f.text(x0, 24, f"one position's query, {W} numbers (its key and value are cut the same way)", "t", 11.5,
           weight=600)
    per = W // H
    for k in range(W):
        h = k // per
        X = x0 + k * c + h * 4
        f.rect(X, y0, c, 18, "a af" if h % 2 == 0 else "s fs", 0, sw=False)
    for h in range(H):
        X = x0 + h * (per * c + 4)
        f.rect(X, y0, per * c, 18, "a" if h % 2 == 0 else "s", 0)
        f.brace_h(X, X + per * c, y0 + 26, "m")
        f.text(X + per * c / 2, y0 + 44, f"head {h + 1}: numbers {h * per} to {h * per + per - 1}", "t", 10.5,
               "middle")
    cell = 3.2
    for h in range(H):
        X = x0 + h * (per * c + 4) + (per * c - 32 * cell) / 2
        weight_map(f, X, 118, weights[0][h], cell)
    f.text(x0, 112, "each head's own weights over the window (block 1 of the page's 4-block model, seed 0)", "tm",
           10.5)
    f.text(x0, 246, f"each head scores, masks and sums on its own, its scores divided by sqrt({per}) = "
                    f"{math.sqrt(per):g};", "tm", 10.5)
    f.text(x0, 261, f"the {H} results, side by side again, are {W} numbers, and out mixes them", "tm", 10.5)
    f.text(x0, 282, f"one head over all {W}: the same query, key, value and out layers, "
                    f"{d['one_head']:,} weights; {H} heads: {d['attention']:,}", "t", 10.5, weight=600)
    return f


def depth0802():
    r = heads_run()
    rows = [("1 attention\nlayer", "stack1-heads1", "s"), ("4 attention\nlayers", "stack4-heads1", "s"),
            ("1 block\n4 heads", "blocks1-heads4", "a"), ("4 blocks\n4 heads", "blocks4-heads4", "a"),
            ("4 blocks\n1 head", "blocks4-heads1", "s")]
    groups = [(label, seeds_of(os.path.join(r.runs, d), "test_bits"), style) for label, d, style in rows]
    n = len(groups[0][1])
    f = Fig("depth0802", f"Bits per character on the test text, {n} seeds each: 08.01's attention stacked, blocks on the "
                         f"residual stream, and one head against four at the same weights: a ring per seed, the bar "
                         f"their mean", 300)
    ax = figart.seeds_chart(f, (8, 4, 624, 292), groups, ylabel="bits per character on the test text",
                            ylim=(3.3, 4.95), yticks=[3.4, 3.6, 3.8, 4.0, 4.2, 4.4, 4.6, 4.8])
    for name, label in (("pairs", "07.01's pairs"), ("single", "single characters")):
        v = rung(name)
        ax.hline(v, f"{label}: {v:.3f}", side="right")
    for k in (1.5, 3.5):
        f.line(ax.px(k), ax.y, ax.px(k), ax.y + ax.h, "m", dash=True)
    return f


def looks0802():
    weights, window = heads_weights()
    chars = in_project("08.02", "import json; from data import shakespeare; print(json.dumps(shakespeare.chars()))")
    text = "".join(chars[i] for i in window)
    printed = looks_printed(heads_run().out)
    n = len(window)
    cell = 3.5
    f = Fig("looks0802", "The weights of seed 0's four heads in block 1 and in block 3, reading the first 32 characters "
                         "of the test text: a row for each position, a column for each position it may see, darker for "
                         "more weight", 410)
    f.text(30, 20, "the window: " + "".join(shown(c) for c in text), "t", 10.5, mono=True)
    for r, b in enumerate((0, 2)):
        y = 50 + r * 175
        f.text(30, y, f"block {b + 1}", "ta" if b == 0 else "t", 11.5, weight=700)
        for h in range(4):
            X = 30 + h * 152
            weight_map(f, X, y + 10, weights[b][h], cell)
            back, own, before = printed[b + 1][h]
            f.text(X, y + 10 + n * cell + 14, f"head {h + 1}: {back:.1f} back", "t", 10)
            f.text(X, y + 10 + n * cell + 27, f"own {own:.2f}, one before {before:.2f}", "tm", 9.5)
    f.text(30, 400, "Averages over 575 windows (the run's part 4); equal weights would be 11.8 back and 0.04 on each.",
           "tm", 10.5)
    if "575 windows" not in heads_run().out or "11.8 back on average, 0.04 on each" not in heads_run().out:
        raise SystemExit("heads: part 4 is not the one the figure quotes")
    return f


# ------------------------------------------------------------------ 08.03

POS_CODE = """
import json, tempfile
import torch
import lab
from data import shakespeare
from experiments import positions as P
from experiments.language import attention_maps, train
from experiments.sequences import window_bits
from models.gpt import GPT
cfg = lab.config(P.CONFIG, ["out=" + tempfile.mkdtemp()])
V = len(shakespeare.chars())
dev = torch.device("cpu")
train_t, test_t = (torch.from_numpy(shakespeare.split(s)) for s in ("train", "test"))
run = lab.Run(cfg, 0, label="blocks4-positions")
torch.manual_seed(0)
model = GPT(V, cfg.context, cfg.layers, cfg.heads, cfg.width, positions=True)
train(model, cfg, run, dev, train_t)
model.eval()
warm = cfg.context // 2
got = window_bits(model, test_t, cfg.context - warm + 1, warm)
maps = attention_maps(model, test_t[None, :cfg.context])
print(json.dumps({"bits": got, "weights": [[[[round(w, 4) for w in r] for r in h] for h in m[0].tolist()] for m in maps],
                  "tokens": list(model.tokens.weight.shape), "positions": list(model.positions.weight.shape)}))
"""


def positioned():
    d = in_project("08.03", POS_CODE)
    page = seeds_of(os.path.join(pos_run().runs, "blocks4-positions"), "test_bits")[0]
    if f"{d['bits']:.6f}" != f"{page:.6f}":
        raise SystemExit(f"the GPT with positions trained here scores {d['bits']}, the page's seed 0 {page}")
    return d


def why0803():
    f = Fig("why0803", "Why the mask lets order in, on a window of four: block 1 at each position sums only the "
                       "characters up to it, so after a swap of the first two, positions 0 and 1 sum something new "
                       "and block 2's last position reads something new", 336)
    orders = (("one order", "abcx"), ("the first two swapped", "bacx"))
    cw = 92
    for k, (title, w) in enumerate(orders):
        x0 = 30 + k * 310
        f.text(x0, 22, title, "t", 11.5, weight=700)
        for i, c in enumerate(w):
            X = x0 + i * (cw / 1.4)
            f.rect(X, 34, 40, 24, "s f", 3)
            f.text(X + 20, 51, c, "t", 12.5, "middle", 700, mono=True)
            f.text(X + 20, 72, f"position {i}" if i == 0 else str(i), "tm", 9.5, "middle")
        f.text(x0, 96, "block 1, at each position: its query, over the keys it may see", "tm", 10.5)
        for i in range(4):
            Y = 106 + i * 30
            diff = i < 2
            f.rect(x0, Y, 284, 24, "a af" if diff else "s f", 4)
            f.text(x0 + 8, Y + 16, f"position {i}: query {w[i]}, over {{{', '.join(sorted(w[:i + 1]))}}}",
                   "ta" if diff else "t", 10.5, mono=True)
        f.line(x0 + 142, 230, x0 + 142, 250, "s", arrow=True)
        f.rect(x0, 254, 284, 26, "a af", 4)
        f.text(x0 + 142, 271, "block 2, last position: reads all four", "ta", 11, "middle", 600)
    f.text(30, 302, "Accent: what differs between the two orders. Positions 2 and 3 sum the same set either way; "
                    "0 and 1 do not.", "tm", 10.5)
    f.text(30, 317, "With one block, every key and value the last position weighs comes from one character alone: "
                    "the same set either way.", "tm", 10.5)
    f.text(30, 332, "Without the mask, every position of block 1 would sum all four, and block 2 too would see one "
                    "set.", "tm", 10.5)
    return f


def add0803():
    d = positioned()
    (V, W), (T, _) = d["tokens"], d["positions"]
    win = LINE[:6]
    f = Fig("add0803", f"Learned positions at the page's sizes: the character's row of the embedding table and the "
                       f"position's row of the position table, {W} numbers each, added into the start of the residual "
                       f"stream", 312)
    figart.shape_box(f, 60, 54, 120, 170, V, W, "", "s fs")
    f.text(120, 34, "the embedding table", "t", 11.5, "middle", 600)
    f.text(120, 244, f"{V} x {W} = {V * W:,} weights", "tm", 10, "middle", mono=True)
    figart.shape_box(f, 230, 54, 120, 100, T, W, "", "a af")
    f.text(290, 34, "the position table", "ta", 11.5, "middle", 600)
    f.text(290, 174, f"{T} x {W} = {T * W:,} weights", "tm", 10, "middle", mono=True)
    f.text(290, 190, f"a row for each place, 0 to {T - 1}", "tm", 10, "middle")
    f.rect(68, 92, 104, 8, "s f", 1)
    f.text(120, 114, f"the row of {win[0]!r}", "t", 10, "middle")
    f.rect(238, 62, 104, 8, "a f", 1)
    f.text(290, 84, "row 0", "ta", 10, "middle")
    f.path("M172 96 H 200 V 196 H 392 V 128", "s", arrow=True)
    f.path("M342 66 H 392 V 104", "a", arrow=True)
    f.circle(392, 116, 10, "a af")
    f.text(392, 120.5, "+", "ta", 14, "middle", 700, mono=True)
    f.line(403, 116, 416, 110, "a", arrow=True)
    for i, c in enumerate(win):
        Y = 100 + i * 26
        X = 420
        f.rect(X, Y, 26, 20, "s f", 3)
        f.text(X + 13, Y + 14.5, shown(c), "t", 11.5, "middle", 600, mono=True)
        f.text(X + 34, Y + 14.5, f"+  place {i}", "ta", 11, mono=True)
        f.text(X + 120, Y + 14.5, f"-> {W} numbers", "t", 11, mono=True)
    f.text(420, 268, "each position starts the stream as", "tm", 10.5)
    f.text(420, 283, "its character's row plus its place's row", "tm", 10.5)
    f.text(60, 302, f"Past place {T - 1} the table has no row: a longer window is refused.", "tm", 10.5)
    return f


def order0803():
    out = pos_run().out
    rows = [(m.group(1).strip(), float(m.group(2))) for m in
            re.finditer(r"^   (\d blocks?, [a-z ]+?) +the largest change in a score: (\S+)$", out, re.M)]
    if len(rows) != 3:
        raise SystemExit(f"positions: expected 3 rows in part 1, read {rows}")
    f = Fig("order0803", "The order test: the largest change in the last position's scores over 5 shuffles of the 31 "
                         "characters before it, on a log scale, for the run's three trained models", 244)
    x0, x1 = 230, 580
    ax = figart.Axes(f, x0, 30, x1 - x0, 150, (1e-16, 10), (-0.5, 2.5), True, False)
    for e in range(-16, 2, 3):
        X = ax.px(10.0 ** e)
        f.line(X, ax.y, X, ax.y + ax.h, "m", dash=True)
        f.text(X, ax.y + ax.h + 16, f"1e{e}" if e else "1", "tm", 10, "middle", mono=True)
    f.text((x0 + x1) / 2, ax.y + ax.h + 34, "the largest change in a score (log scale)", "tm", 11, "middle")
    for i, (name, v) in enumerate(rows):
        y = ax.y + 18 + i * 44
        one = name.startswith("1 block")
        f.text(x0 - 10, y + 12, name, "t" if one else "ta", 12, "end", 600)
        f.rect(x0, y, ax.px(v) - x0, 18, "s fs" if one else "a af", 2)
        f.text(ax.px(v) + 6, y + 13, sig(v), "t" if one else "ta", 11, mono=True)
    f.text(x0 - 10, ax.y + 6, "trained, float64:", "tm", 10.5, "end")
    f.text(24, 236, "One block: rounding in the last of float64's 16 digits. Four blocks: order, through the mask, and "
                    "more with positions.", "tm", 10.5)
    return f


def longer0803():
    out = pos_run().out
    series = {}
    for m in re.finditer(r"^   n = (\d): (.*)$", out, re.M):
        series[int(m.group(1))] = [(int(a), int(b), float(v)) for a, b, v in
                                   re.findall(r"(\d+) to +(\d+): (\S+)", m.group(2))]
    refused = re.search(r"learned positions, reading only the last (\d+) characters before each \(as trained\): (\S+) ",
                        out)
    T, alone = int(refused.group(1)), float(refused.group(2))
    f = Fig("longer0803", f"The model without positions (seed 0) reading windows longer than any it trained on: bits per "
                          f"character at each part of the window, for windows of {T}, {2 * T} and {4 * T}", 276)
    ax = figart.Axes(f, 60, 44, 420, 180, (0, 4 * T), (3.35, 3.72))
    ax.draw(xticks=[0, T, 2 * T, 3 * T, 4 * T], yticks=[3.4, 3.5, 3.6, 3.7], xlabel="position in the window")
    f.text(54, 34, "bits per character", "tm", 11.5)
    ax.vline(T)
    ax.note(T, 3.70, f"the longest trained on: {T}", "tm", 10.5, "start", dx=5)
    styles = {1: "m", 2: "s", 4: "a"}
    for n, parts in sorted(series.items()):
        st = styles.get(n, "s")
        for a, b, v in parts:
            f.line(ax.px(a), ax.py(v), ax.px(b + 1), ax.py(v), st)
            if n == 4 or a == 0:
                pass
        for a, b, v in parts:
            if n == 4:
                ax.note((a + b + 1) / 2, v, f"{v:.3f}", "ta", 10, "middle", dy=-6)
            elif n == 2 and a > 0:
                ax.note((a + b + 1) / 2, v, f"{v:.3f}", "t", 10, "middle", dy=14)
            elif n == 1:
                ax.note((a + b + 1) / 2, v, f"{v:.3f}", "tm", 10, "middle", dy=14)
    items = [(f"windows of {T * n}", styles[n], False) for n in sorted(series)]
    figart.legend(f, 500, 70, items)
    f.text(500, 140, "with learned positions:", "t", 10.5, weight=600)
    f.text(500, 155, f"no row past {T - 1}, refused;", "tm", 10.5)
    f.text(500, 170, f"the last {T} before each: {alone:.3f}", "tm", 10.5)
    return f


def looks0803():
    d = positioned()
    without, window = heads_weights()
    chars = in_project("08.02", "import json; from data import shakespeare; print(json.dumps(shakespeare.chars()))")
    n = len(window)
    cell = 3.5
    printed = {"without": looks_printed(heads_run().out)[1], "with": looks_printed(pos_run().out)[1]}
    f = Fig("looks0803", "The weights of seed 0's four heads in block 1, reading the first 32 characters of the test "
                         "text, without positions (08.02's model) and with them", 410)
    f.text(30, 20, "the window: " + "".join(shown(chars[i]) for i in window), "t", 10.5, mono=True)
    for r, (name, w, key) in enumerate((("no positions (08.02)", without[0], "without"),
                                        ("learned positions", d["weights"][0], "with"))):
        y = 50 + r * 175
        f.text(30, y, f"block 1, {name}", "t" if r == 0 else "ta", 11.5, weight=700)
        for h in range(4):
            X = 30 + h * 152
            weight_map(f, X, y + 10, w[h], cell)
            back, own, before = printed[key][h]
            f.text(X, y + 10 + n * cell + 14, f"head {h + 1}: {back:.1f} back", "t", 10)
            f.text(X, y + 10 + n * cell + 27, f"own {own:.2f}, one before {before:.2f}", "tm", 9.5)
    f.text(30, 400, "The numbers are averages over 575 windows of the test text, the runs' part 4.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 08.04

def curves_panel(f, box, dirs, title, ylim, yticks, every_lowest=False):
    x, y, w, h = box
    rows = [figart.read_log(d) for d in dirs]
    steps_ = max(r[-1]["step"] for r in rows)
    ax = figart.Axes(f, x, y, w, h, (0, steps_), ylim)
    ax.draw(xticks=None, yticks=yticks, xlabel="step")
    f.text(x - 6, y - 8, title, "t", 11.5, weight=700)
    for k, r in enumerate(rows):
        xs, tr = figart.column(r, "bits")
        _, va = figart.column(r, "held_bits")
        ax.curve(xs, tr, "s" if k == 0 else "m", dash=True, width=1.5)
        ax.curve(xs, va, "a" if k == 0 else "a", width=2 if k == 0 else 1.5)
        if every_lowest:
            s = figart.summary(dirs[k])
            ax.dot(s["lowest_step"], s["lowest_held_bits"], "a fa", 3.5)
            f.text(x + w - 4, y + 30 + 13 * k, f"lowest, seed {k}: {s['lowest_held_bits']:.3f} at step "
                   f"{s['lowest_step']}", "ta", 9.5, "end")
    return ax


def short0804():
    r = gpt_run()
    f = Fig("short0804", "The page's short run: bits per character of the training batch (dashed) and of the 64 "
                         "validation windows (solid), every 50 steps, two seeds each without dropout and with 0.2: "
                         "every validation curve still falling at the end", 290)
    for k, dropout in enumerate(("0.0", "0.2")):
        dirs = figart.seed_dirs(os.path.join(r.runs, f"dropout{dropout}"))
        curves_panel(f, (60 + k * 300, 40, 250, 190), dirs, f"dropout {dropout}", (3.2, 4.4), [3.2, 3.6, 4.0, 4.4])
    figart.legend(f, 60, 282, [("training batch", "s", True), ("validation windows", "a", False)], across=True)
    return f


def recorded():
    return os.path.join(figlib.TRACK, "experiments", "recorded", "gpt")


def curves0804():
    d = recorded()
    f = Fig("curves0804", "The recorded long run: bits per character of the training batch (dashed) and of the 64 "
                          "validation windows (solid) every 100 steps, two seeds without dropout and two with 0.2; each "
                          "seed's lowest validation point marked", 316)
    for k, dropout in enumerate(("0.0", "0.2")):
        dirs = figart.seed_dirs(os.path.join(d, f"dropout{dropout}"))
        ax = curves_panel(f, (60 + k * 300, 40, 250, 210), dirs, f"dropout {dropout}", (1.3, 2.7),
                          [1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6], every_lowest=True)
        end = [figart.read_log(x)[-1] for x in dirs]
        gap = [e["held_bits"] - e["bits"] for e in end]
        f.text(ax.x + ax.w - 4, ax.y + 14, f"gap at the end: {gap[0]:.2f}, {gap[1]:.2f}", "tm", 9.5, "end")
    figart.legend(f, 60, 308, [("training batch (seed 0, then seed 1 paler)", "s", True),
                               ("validation windows", "a", False)], across=True)
    return f


def ladder0804():
    rows = ladder_rows()
    r = gpt_run()
    d = recorded()
    gpts = []
    for name, base, label in (("the GPT, 1 minute", r.runs, "dropout"), ("the GPT, long run", d, "dropout")):
        for dropout in ("0.0", "0.2"):
            vals = seeds_of(os.path.join(base, f"{label}{dropout}"), "test_bits")
            gpts.append((f"{name}, dropout {dropout}", vals))
    short = {"every character equally likely": "equal chances", "single characters": "single characters",
             "pairs (add-k 0.1)": "pairs (07.01)"}
    names = []
    for n, b in rows:
        s = short.get(n, n)
        s = s.replace(" (the best on validation)", "").replace("deleted interpolation, contexts up to 7",
                                                               "deleted interpolation, up to 7")
        s = s.replace("07.02's network and interpolation, half each", "07.02's network + interpolation")
        names.append((s, b))
    f = Fig("ladder0804", "Module 07's ladder on the test text, with the GPT on it: the page's one-minute run and the "
                          "recorded long run, without dropout and with 0.2, a ring per seed", 34 + 18 * 15 + 56)
    x0, x1 = 316, 600
    lo, hi = 2.15, 3.65
    n = len(names) + len(gpts)
    ax = figart.Axes(f, x0, 34, x1 - x0, 18 * n + 8, (lo, hi), (n, 0))
    ax.draw(xticks=[2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6], yticks=[], xlabel="bits per character on the test text")
    best = min(b for _, b in rows)
    f.line(ax.px(best), ax.y, ax.px(best), ax.y + ax.h, "a", dash=True)
    f.text(ax.px(best), ax.y - 6, f"module 07's best: {best:.3f}", "ta", 9.5, "middle")
    for i, (s, b) in enumerate(names + [(g, mean(v)) for g, v in gpts]):
        y = ax.y + 14 + i * 18
        gpt = i >= len(names)
        f.text(x0 - 8, y + 4, s, "ta" if gpt else "t", 10.5, "end", 600 if gpt else None)
        if b > hi:
            f.line(x1 - 30, y, x1 - 4, y, "m", arrow=True)
            f.text(x1 - 34, y + 4, f"{b:.3f}", "tm", 9.5, "end", mono=True)
            continue
        if gpt:
            for v in gpts[i - len(names)][1]:
                f.circle(ax.px(v), y, 3.5, "a f")
            f.line(ax.px(b), y - 6, ax.px(b), y + 6, "a")
            f.text(ax.px(max(gpts[i - len(names)][1])) + 8, y + 4, f"{b:.3f}", "ta", 9.5, mono=True)
        else:
            f.circle(ax.px(b), y, 3.5, "s fs")
            f.text(ax.px(b) + 8, y + 4, f"{b:.3f}", "t", 9.5, mono=True)
    return f


# ------------------------------------------------------------------ 08.05

SAMPLE_CODE = """
import json, tempfile
import torch
import torch.nn.functional as F
import lab
from data import shakespeare
from experiments import sampling as S
from experiments.language import train, top_k, top_p
from models.gpt import GPT
cfg = lab.config(S.CONFIG, ["out=" + tempfile.mkdtemp()])
V = len(shakespeare.chars())
dev = torch.device("cpu")
train_t = torch.from_numpy(shakespeare.split("train"))
test = shakespeare.split("test")
run = lab.Run(cfg, 0, label="model")
torch.manual_seed(0)
model = GPT(V, cfg.context, cfg.layers, cfg.heads, cfg.width)
train(model, cfg, run, dev, train_t)
model.eval()
text = torch.from_numpy(S.speeches(test, cfg.prompt, cfg.prompts, cfg.length))
prompts, human = text[:, :cfg.prompt], text[:, cfg.prompt:]
people = S.continuation_bits(model, prompts, human)
with torch.no_grad():
    scores = model(prompts[:1])[0, -1]
vocab = shakespeare.chars()
methods = {m[0]: m[1:] for m in cfg.methods}
def chances(s):
    return F.softmax(s, dim=-1).tolist()
t = [m[1] for m in cfg.methods if m[1] not in (0, 1.0)][-1]
k = [m[2] for m in cfg.methods if m[2]][0]
p = [m[3] for m in cfg.methods if m[3]][0]
print(json.dumps({"people": 2 ** people, "prompt": shakespeare.decode(prompts[0].tolist()), "next": vocab[int(human[0, 0])],
                  "vocab": vocab, "t": t, "k": k, "p": p, "plain": chances(scores), "temperature": chances(scores / t),
                  "top_k": chances(top_k(scores, k)), "top_p": chances(top_p(scores, p))}))
"""


def cuts0805():
    d = in_project("08.05", SAMPLE_CODE)
    out = sampling_run().out
    if "so a small one trained here" not in out:
        raise SystemExit("sampling: the page's run did not train its own model")
    printed = figart.value(out, r"^   the text itself +(\S+)")
    if f"{d['people']:.4g}" != f"{printed:.4g}":
        raise SystemExit(f"the model trained here gives the text {d['people']}, the page's run {printed}")
    vocab, plain = d["vocab"], d["plain"]
    order = sorted(range(len(vocab)), key=lambda j: -plain[j])
    shown_n = 14
    keep = {name: sum(1 for v in d[name] if v > 0) for name in ("top_k", "top_p")}
    rows = [("plain sampling", "plain", f"all {len(vocab)} characters, as they are", "s"),
            (f"temperature {d['t']}", "temperature", f"all {len(vocab)}, the likely ones likelier", "s"),
            (f"top-k = {d['k']}", "top_k", f"the {keep['top_k']} likeliest, scaled to add up to 1", "a"),
            (f"nucleus, p = {d['p']}", "top_p", f"the fewest reaching {d['p']}: {keep['top_p']}", "a")]
    f = Fig("cuts0805", f"One real distribution: the chances the page's model gives the character after "
                        f"{d['prompt']!r}, in order, and what each way of choosing keeps of them", 64 + 70 * 4 + 30)
    f.text(24, 22, f"after {d['prompt']!r} the text has {d['next']!r}; the model's {shown_n} likeliest characters, "
                   f"in order:", "t", 11, mono=False)
    x0, bw = 150, 22
    for k, j in enumerate(order[:shown_n]):
        f.text(x0 + k * bw + bw / 2, 48, shown(vocab[j]), "ta" if vocab[j] == d["next"] else "t", 11, "middle", 700,
               mono=True)
    f.text(x0 + shown_n * bw + 6, 48, f"+ {len(vocab) - shown_n} more", "tm", 10)
    top = max(max(d[name]) for _, name, _, _ in rows)
    for r, (title, name, note, style) in enumerate(rows):
        base = 64 + 70 * (r + 1) - 8
        f.text(24, base - 30, title, "ta" if style == "a" else "t", 11.5, weight=700)
        f.line(x0 - 4, base, x0 + shown_n * bw + 4, base, "m")
        for k, j in enumerate(order[:shown_n]):
            v = d[name][j]
            h = 54 * v / top
            if v > 0:
                f.rect(x0 + k * bw + 3, base - h, bw - 6, max(h, 0.8), "a af" if style == "a" else "s fs", 1)
            else:
                f.text(x0 + k * bw + bw / 2, base - 3, "0", "tm", 9, "middle", mono=True)
            if k < 3:
                f.text(x0 + k * bw + bw / 2, base - h - 3, f"{v:.2f}"[1:] if v < 1 else "1", "tm", 8.5, "middle",
                       mono=True)
        f.text(x0 + shown_n * bw + 14, base - 22, note, "tm", 10)
        rest = sum(d[name][j] for j in order[shown_n:])
        f.text(x0 + shown_n * bw + 14, base - 8, f"the other {len(vocab) - shown_n}: {rest:.3f} together", "tm", 10)
    f.text(24, 64 + 70 * 4 + 22, "The bars of each row are its chances after the cut, on one scale.", "tm", 10.5)
    return f


def perplexity0805():
    r = sampling_run()
    out = r.out
    table = out.split("\nPrompt 1")[0]
    names = [m.group(1) for m in re.finditer(r"^   ((?:greedy|pure sampling|sampling, t=\S+|top-k=\S+|nucleus, p=\S+)) ",
                                             table, re.M)]
    if len(names) != 6:
        raise SystemExit(f"sampling: expected 6 ways in the table, read {names}")
    groups = []
    for name in names:
        label = name.replace(", ", "-").replace("=", "").replace(" ", "_")
        s = figart.summary(os.path.join(r.runs, label, "seed0"))
        loops = mean(s["repetition"])
        style = "a" if name.startswith("nucleus") else "s"
        groups.append((f"{name}\nloops {loops:.0f}%", s["perplexity"], style))
    text = figart.value(out, r"^   the text itself +(\S+)")
    f = Fig("perplexity0805", "Perplexity of what each way of choosing wrote, to the model that wrote it, beside the "
                              "real text after the same 16 prompts (the dashed line): a ring per seed, the bar their "
                              "mean; and the passages that end in a loop", 300)
    ax = figart.seeds_chart(f, (8, 4, 624, 292), groups, ylabel="perplexity, 2 to the bits per character",
                            ylim=(0, 10.5), yticks=[0, 2, 4, 6, 8, 10])
    ax.hline(text, f"the real text: {text:.3f}", cls="s", side="right")
    return f


FIGS = [
    ("08.01-mask", mask0801),
    ("08.01-step", step0801),
    ("08.01-scale", scale0801),
    ("08.01-honest", honest0801),
    ("08.02-block", block0802),
    ("08.02-heads", heads0802),
    ("08.02-depth", depth0802),
    ("08.02-looks", looks0802),
    ("08.03-why", why0803),
    ("08.03-add", add0803),
    ("08.03-order", order0803),
    ("08.03-longer", longer0803),
    ("08.03-looks", looks0803),
    ("08.04-short", short0804),
    ("08.04-curves", curves0804),
    ("08.04-ladder", ladder0804),
    ("08.05-cuts", cuts0805),
    ("08.05-perplexity", perplexity0805),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
