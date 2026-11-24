"""Figures for research module 14, Reproduce a paper: grokking (lessons 14.01-14.04).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs14.py [14.02 ...]
                                    all of them, or those whose name starts so (DIR keeps the runs)

Every curve, cell and number comes from the reference code (tracks/research), run as the page runs it,
or from the recorded runs the pages read; the paper's numbers come from experiments/predictions.py,
where each is written with its place in the paper:

  14.01  data/modular.py in the project at 14.01: the table of x/y mod 97 and seed 0's split at the
         paper's 50%, one equation as its tokens; experiments/predictions.py's CLAIMS (the claims table,
         and figure 4's chance line and peak as read there); ln 97 from p
  14.02  python3 -m experiments.grokking (the page's run, 35%, 350 steps, 3 seeds) and the same with
         batch=543 (the page's Break it); experiments/recorded/ablations/fraction0.5-decay1-start1 (the
         paper's 50%, recorded)
  14.03  experiments/recorded/grokking/ (the recorded long run: its logs); the layer norms' part of the
         weights' norm from models/gpt.py's GPT as it starts; figure 1's caption as quoted in CLAIMS
  14.04  experiments/recorded/ablations/ (its logs); the report's outcomes and verdicts, computed by
         experiments/report.py in the project at 14.04

PyTorch must be installed; nothing needs a download. The runs take about three minutes in all on the
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
import figart  # noqa: E402
import figlib  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "14"
REC = os.path.join(figlib.TRACK, "experiments", "recorded")
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


def logs(d):
    """Every seed's log under d, in seed order."""
    return [figart.read_log(x) for x in figart.seed_dirs(d)]


def first(rows, key, level=0.99):
    """The first measured step at which rows[key] is level or more (arithmetic.first_step's rule)."""
    return next((r["step"] for r in rows if r[key] >= level), None)


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if len(xs) % 2 else (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2


def figure_logs():
    return logs(os.path.join(REC, "grokking"))


def ablation(fraction, decay, start):
    return logs(os.path.join(REC, "ablations", f"fraction{fraction:g}-decay{decay:g}-start{start:g}"))


def chance_line(ax, p=97, label=True, side="right"):
    ax.hline(1 / p, f"a guess: 1/{p} = {1 / p:.4f}" if label else None, side=side)


def acc_panel(f, box, runs, xmax, title, tcls="t", ylabel=True, mark=True, chance=True, xticks=None):
    """Training (dashed, foreground) and validation (accent) accuracy of each seed's log on a log step axis;
    with mark, a dot where each first reached 99%. Returns the Axes."""
    x, y, w, h = box
    ax = figart.Axes(f, x, y, w, h, (1, xmax), (0, 1), True, False)
    ax.draw(xlabel="step (log scale)", ylabel="accuracy" if ylabel else "", yticks=[0, 0.25, 0.5, 0.75, 1],
            xticks=xticks or [t for t in (1, 10, 100, 1000, 10000) if t <= xmax])
    f.text(x, y - 22, title, tcls, 11.5, weight=700)
    if chance:
        ax.hline(1 / 97, None)
    for k, rows in enumerate(runs):
        rows = [r for r in rows if r["step"] >= 1]
        xs = [r["step"] for r in rows]
        width = 2 if k == 0 else 1.4
        ax.curve(xs, [r["train_acc"] for r in rows], "s", dash=True, width=width)
        ax.curve(xs, [r["val_acc"] for r in rows], "a", width=width)
        if mark:
            for key, cls in (("train_acc", "s f"), ("val_acc", "a fa")):
                s = first(rows, key)
                if s is not None:
                    ax.dot(s, 0.99, cls, 3.5)
    return ax


# ------------------------------------------------------------------ 14.01

TABLE_CODE = """
import json
from data import modular
p, op = 97, "/"
rows = modular.equations(p, op)
train, val = modular.split(p, op, 0.5, 0)
print(json.dumps({"train": [[int(t[0]), int(t[2])] for t in train.tolist()], "n": len(rows), "k": len(train),
                  "c": {f"{a},{b}": int(c) for a, b, c in rows.tolist() if a < 12 and b < 12},
                  "lowest_b": int(rows[:, 1].min()), "p": p}))
"""


def table1401():
    d = in_project("14.01", TABLE_CODE)
    p, n, k, b0 = d["p"], d["n"], d["k"], d["lowest_b"]
    train = {(a, b) for a, b in d["train"]}
    f = Fig("table1401", f"x / y mod {p} as a table, a row for each a and a column for each b: seed 0's split at the "
                         f"paper's 50%, the training equations filled and the held-out ones a question mark; left, the "
                         f"corner a = 0 to 11, b = 1 to 11, with each c", 330)
    # the corner, with its numbers
    cw, ch, x0, y0 = 21, 17.5, 46, 64
    f.text(16, 20, "the corner: c = a / b mod 97", "t", 11.5, weight=700)
    f.text(16, 36, "filled: an equation to train on; ?: held out", "tm", 10.5)
    bs = list(range(b0, 12))
    f.text(x0 - 5, y0 - 6, "a\\b", "tm", 9.5, "end", mono=True)
    for j, b in enumerate(bs):
        f.text(x0 + j * cw + cw / 2, y0 - 6, str(b), "tm", 10, "middle", mono=True)
    for a in range(12):
        Y = y0 + a * ch
        f.text(x0 - 5, Y + 12.5, str(a), "tm", 10, "end", mono=True)
        for j, b in enumerate(bs):
            X = x0 + j * cw
            if (a, b) in train:
                f.add(f'<rect class="fa" x="{X:.1f}" y="{Y:.1f}" width="{cw}" height="{ch}" fill-opacity="0.3"/>')
                f.text(X + cw / 2, Y + 12.5, str(d["c"][f"{a},{b}"]), "t", 9.5, "middle", mono=True)
            else:
                f.text(X + cw / 2, Y + 12.5, "?", "tm", 9.5, "middle", mono=True)
    f.rect(x0, y0, len(bs) * cw, 12 * ch, "m", 0)
    # the whole table, one small cell per equation
    X0, Y0, cw2, ch2 = 340, 64, 2.85, 2.35
    cols = p - b0
    f.text(X0, 20, f"the whole table: {n} equations", "t", 11.5, weight=700)
    f.text(X0, 36, f"{k} to train on (filled), {n - k} held out", "tm", 10.5)
    parts = []
    for a, b in sorted(train):
        parts.append(f"M{X0 + (b - b0) * cw2:.2f} {Y0 + a * ch2:.2f}h{cw2}v{ch2}h{-cw2}z")
    f.add(f'<path class="fa" d="{"".join(parts)}" fill-opacity="0.85"/>')
    f.rect(X0, Y0, cols * cw2, p * ch2, "m", 0)
    f.rect(X0, Y0, len(bs) * cw2, 12 * ch2, "s", 0)
    f.text(X0 + cols * cw2 / 2, Y0 - 6, f"b = {b0} to {p - 1}", "tm", 10, "middle", mono=True)
    f.text(X0 - 5, Y0 + 8, "a = 0", "tm", 10, "end", mono=True)
    f.text(X0 - 5, Y0 + p * ch2, str(p - 1), "tm", 10, "end", mono=True)
    f.text(X0 - 6, Y0 + 12 * ch2 + 14, "the corner", "t", 10, "end")
    f.line(X0 - 4, Y0 + 12 * ch2 + 4, X0, Y0 + 12 * ch2, "s")
    f.text(16, 320, f"No equation is in both halves, and every one is in one; another seed draws another half.",
           "tm", 10.5)
    return f


TOKENS_CODE = """
import json
from data import modular
p, op = 97, "/"
rows = modular.equations(p, op)
row = rows[(rows[:, 0] == 20) & (rows[:, 1] == 15)]
names = modular.names(p)
toks = modular.tokens(row, p, op)[0].tolist()
print(json.dumps({"tokens": toks, "names": [names[t] for t in toks], "V": len(names), "p": p,
                  "symbols": {s: p + i for i, s in enumerate(modular.SYMBOLS)}}))
"""


def tokens1401():
    d = in_project("14.01", TOKENS_CODE)
    toks, names, V, p = d["tokens"], d["names"], d["V"], d["p"]
    a, b, c = toks[0], toks[2], toks[4]
    assert (c * b) % p == a
    f = Fig("tokens1401", f"One equation as the model sees it: five tokens, a symbol each; the model reads the first "
                          f"four and is scored on its guess at the fifth", 236)
    x0, bw, gap, y = 40, 70, 16, 44
    xs = [x0 + i * (bw + gap) for i in range(5)]
    f.text(16, 20, "the equation " + " ".join(names) + ", as the paper writes it: <x><op><y><=><x o y>", "t", 11.5,
           weight=700)
    for i, (t, s) in enumerate(zip(toks, names)):
        lit = i == 4
        f.label_box(xs[i], y, bw, 34, s, "a af" if lit else "s fs", "ta" if lit else "t", 15, True, weight=700)
        f.text(xs[i] + bw / 2, y + 52, f"token {t}", "ta" if lit else "tm", 10.5, "middle", mono=True)
    f.brace_h(xs[0], xs[3] + bw, y + 64, "s")
    f.text((xs[0] + xs[3] + bw) / 2, y + 82, "what the model reads", "t", 11, "middle", 600)
    f.text(xs[4] + bw / 2, y + 82, "what it must guess", "ta", 11, "middle", 600)
    # the guess
    gy = 146
    boxes = [(16, 180, "the GPT reads " + " ".join(names[:4]), None, "s fs", "t"),
             (222, 186, f"{V} scores at its last position", None, "s f", "t"),
             (434, 190, "its guess: the highest", f"its loss: -ln p({c})", "a af", "ta")]
    for k, (bx, bw2, label, sub, cls, tcls) in enumerate(boxes):
        f.label_box(bx, gy, bw2, 34, label, cls, tcls, 10.5, False, weight=600, sub=sub, subcls="ta", subsize=10)
        if k:
            f.line(boxes[k - 1][0] + boxes[k - 1][1] + 2, gy + 17, bx - 3, gy + 17, "s", arrow=True)
    f.text(16, 202, f"Why {c}: {c} x {b} = {c * b} = {c * b // p} x {p} + {a}, so {c} times {b} is {a} mod {p}, and "
                    f"{a} / {b} = {c}.", "t", 10.5)
    sym = d["symbols"]
    f.text(16, 220, f"Tokens 0 to {p - 1} are the residues; " + ", ".join(f"{s} is {n}" for s, n in sym.items())
           + ": nothing says that 5 comes after 4.", "tm", 10.5)
    return f


CLAIMS_CODE = """
import json
from experiments.predictions import CLAIMS
print(json.dumps([c._asdict() for c in CLAIMS]))
"""


def claims():
    return in_project("14.01", CLAIMS_CODE)


def claim(key):
    return next(c for c in claims() if c["key"] == key)


def paper_number(c):
    """The paper's number of a claim, from its words in predictions.py: (low, high) for "about x" or "about x to
    y", None when the paper gives only a bound or a direction."""
    m = re.match(r"about ([\d.]+)(?: to ([\d.]+))?", c["paper"])
    if not m:
        return None
    lo = float(m.group(1))
    return lo, float(m.group(2) or lo)


def rule_text(rule):
    kind, x = rule
    return f"within 3x of {x:g}" if kind == "about" else f"{kind} {x:g}"


def scored1401():
    c = claim("loss_rises")
    m = re.search(r"a peak of about ([\d.]+) against its chance line, about ([\d.]+)", c["paper"])
    peak, line = float(m.group(1)), float(m.group(2))
    p = 97
    guess = math.log(p)
    f = Fig("scored1401", f"Where the loss is taken: the paper's text scores the answer only; the authors' code scores "
                          f"every token after =, the end token too, which halves the loss of a guess", 250)
    rows = [("the paper's text (appendix A.1.2): \"loss and accuracy only on the answer part\"; ours",
             ["a", "/", "b", "=", "c"], [4], f"a guess: ln {p} = {guess:.3f}"),
            ("the authors' code (openai/grok): every token after =",
             ["<eos>", "a", "/", "b", "=", "c", "<eos>"], [5, 6],
             f"a guess: ({guess:.3f} + 0) / 2 = {guess / 2:.3f}")]
    for r, (title, seq, scored, note) in enumerate(rows):
        y = 40 + r * 96
        f.text(16, y - 12, title, "t", 11.5, weight=700)
        x = 30
        for i, s in enumerate(seq):
            w = 52 if s.startswith("<") else 40
            lit = i in scored
            f.label_box(x, y, w, 28, s, "a af" if lit else "s fs", "ta" if lit else "t", 12, True, weight=600)
            if lit:
                f.text(x + w / 2, y + 44, "scored", "ta", 10, "middle")
            x += w + 8
        f.text(x + 10, y + 19, note, "ta" if r == 1 else "t", 11, weight=600)
    f.text(16, 226, f"Figure 4's chance line is about {line:g}: half of ln {p}, as the code scores it. Its peak, about "
                    f"{peak:g}, is so about {peak / line:.0f} times its own", "tm", 10.5)
    f.text(16, 242, f"chance line; our runs score c alone and set their loss beside {guess:.3f}.", "tm", 10.5)
    return f


def claims1401():
    cs = claims()
    groups = [("x/y mod 97", "figure 1's run: x/y mod 97, 50% of the equations, Adam without weight decay, 10^6 "
                             "steps"),
              ("S5", "the paper's other runs: the product in the group S5, AdamW with weight decay 1"),
              ("113", "Nanda et al. (2023): x + y mod 113, 30% of the pairs, one layer, full batch")]

    def group(c):
        s = c["setting"]
        return 2 if "113" in s else (0 if s.startswith("x/y") else 1)
    rh, gh = 21, 22
    n = len(cs) + len(groups)
    f = Fig("claims1401", "The claims as predictions, written down before any run: where each is in the paper, the "
                          "paper's number, and the rule that will say whether ours held", 56 + len(cs) * rh
            + len(groups) * gh + 30)
    cols = [(16, "claim"), (118, "where in the paper"), (330, "the paper's number"), (470, "held if ours is")]
    for x, h in cols:
        f.text(x, 22, h, "tm", 10.5, weight=600)
    f.line(16, 30, 624, 30, "m")
    y = 34
    for gi, (_, title) in enumerate(groups):
        y += gh
        f.text(16, y - 6, title, "tm", 10.5)
        for c in [c for c in cs if group(c) == gi]:
            y += rh
            lit = c["key"] == "late"
            tcls = "ta" if lit else "t"
            f.text(16, y - 6, c["key"], tcls, 11, weight=700 if lit else 600, mono=True)
            where = c["where"].replace(", its caption", "").replace("Nanda et al. (2023), ", "")
            f.text(118, y - 6, where, tcls, 10.5)
            paper = re.split(r" \(|, | at ", c["paper"])[0]
            f.text(330, y - 6, paper, tcls, 10.5, mono=True)
            f.text(470, y - 6, rule_text(c["rule"]), tcls, 10.5, mono=True)
    del n
    f.text(16, y + 22, "about: within a factor of 3 either way (a number read off a log axis); below, above: the "
                       "direction.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 14.02

def short_run():
    return figart.experiment("grokking", at="14.02")


def one_run():
    return figart.experiment("grokking", "batch=543", at="14.02")


def short1402():
    r = short_run()
    ours = logs(r.runs)
    paper = ablation(0.5, 1.0, 1.0)
    f = Fig("short1402", "Accuracy on the training equations (dashed) and on the held-out ones (solid), 3 seeds, a dot "
                         "where each first reached 99%: the page's run at 35% of the equations, and the recorded runs "
                         "of 14.04 at the paper's 50%", 300)
    steps = max(row["step"] for rows in ours for row in rows)
    ax = acc_panel(f, (56, 48, 250, 200), ours, steps, f"35% of the equations, {steps} steps: the page's run",
                   "ta", xticks=[1, 10, 100, steps])
    ends = [rows[-1] for rows in ours]
    ax.note(1.5, 0.62, f"at step {steps}: training {min(e['train_acc'] for e in ends):.2f} to "
                       f"{max(e['train_acc'] for e in ends):.2f},", "t", 10)
    ax.note(1.5, 0.52, f"held out {min(e['val_acc'] for e in ends):.3f} to {max(e['val_acc'] for e in ends):.3f}",
            "ta", 10)
    last = max(rows[-1]["step"] for rows in paper)
    ax2 = acc_panel(f, (380, 48, 250, 200), paper, last, "50%, the paper's fraction: 14.04's runs", "t",
                    ylabel=False)
    t99 = [first(rows, "train_acc") for rows in paper]
    v99 = [first(rows, "val_acc") for rows in paper]
    both = [f"{t}/{v}" for t, v in zip(t99, v99) if t is not None]
    ax2.note(1.5, 0.86, "99% on both:", "t", 10)
    ax2.note(1.5, 0.86, ", ".join(both), "t", 10, dy=13)
    stuck = [rows for rows in paper if first(rows, "val_acc") is None]
    if stuck:
        e = stuck[0][-1]
        ax2.note(1.5, 0.62, "one seed stuck:", "tm", 10)
        ax2.note(1.5, 0.62, f"{e['train_acc']:.2f}, {e['val_acc']:.2f} at {e['step']}", "tm", 10, dy=13)
    figart.legend(f, 56, 292, [("training equations", "s", True), ("held-out equations", "a", False)], across=True)
    return f


def batches1402():
    r, b = short_run(), one_run()
    cfg = figart.config(figart.seed_dirs(r.runs)[0])
    total = in_project("14.02", "import json; from data import modular; print(json.dumps(len(modular.equations(97, '/'))))")
    n = round(cfg["fraction"] * total)
    f = Fig("batches1402", f"One pass over the {n} training equations, cut into batches of 512 (the paper's) and of "
                           f"543; and the training accuracy each gives, 3 seeds", 300)
    x0, W = 120, 380
    for k, (size, cls) in enumerate(((cfg["batch"], "s"), (figart.config(figart.seed_dirs(b.runs)[0])["batch"], "a"))):
        y = 30 + k * 46
        full, rest = divmod(n, size)
        f.text(x0 - 10, y + 15, f"batches of {size}", "ta" if cls == "a" else "t", 11, "end", 600)
        for i in range(full + (rest > 0)):
            m = size if i < full else rest
            X = x0 + i * size / n * W
            f.rect(X, y, max(m / n * W - 2, 2.5), 20, f"{cls} {'af' if cls == 'a' else 'fs'}", 2)
        f.text(x0 + W + 6, y + 15, f"{full} x {size} + {rest}", "ta" if cls == "a" else "t", 10.5, mono=True)
        if rest:
            f.text(x0 + W, y + 34, f"the last: {rest} equation{'s' * (rest > 1)}", "ta" if cls == "a" else "tm",
                   10, "end")
    ax = figart.Axes(f, 120, 130, 340, 120, (1, cfg["steps"]), (0, 1), True, False)
    ax.draw(xlabel="step (log scale)", ylabel="training accuracy", yticks=[0, 0.5, 1],
            xticks=[1, 10, 100, cfg["steps"]])
    for runs, cls in ((logs(r.runs), "s"), (logs(b.runs), "a")):
        for k, rows in enumerate(runs):
            rows = [x for x in rows if x["step"] >= 1]
            ax.curve([x["step"] for x in rows], [x["train_acc"] for x in rows], cls, width=2 if k == 0 else 1.3)
    ends = {name: [rows[-1]["train_acc"] for rows in logs(d.runs)] for name, d in (("512", r), ("543", b))}
    f.text(476, 150, "after 350 steps:", "t", 10.5, weight=600)
    f.text(476, 168, f"512: {sum(ends['512']) / 3:.3f}", "t", 10.5, mono=True)
    f.text(476, 184, f"543: {sum(ends['543']) / 3:.4f}", "ta", 10.5, mono=True)
    f.text(476, 200, "(mean of 3 seeds)", "tm", 10)
    return f


# ------------------------------------------------------------------ 14.03

def figure1403():
    runs = figure_logs()
    cfg = figart.config(figart.seed_dirs(os.path.join(REC, "grokking"))[0])
    t99 = [first(rows, "train_acc") for rows in runs]
    v99 = [first(rows, "val_acc") for rows in runs]
    f = Fig("figure1403", f"The recorded run: accuracy on the training equations (dashed) and the held-out ones "
                          f"(solid), {len(runs)} seeds, {cfg['steps']} steps of x/y mod {cfg['p']} at "
                          f"{cfg['fraction']:.0%}, measured {cfg['per_decade']} times a decade; a dot where each first "
                          f"reached 99%", 330)
    ax = acc_panel(f, (60, 44, 400, 220), runs, cfg["steps"], "memorised, then generalised", "t",
                   xticks=[1, 10, 100, 1000, cfg["steps"]])
    ax.hline(0.99, None)
    tm, vm = median(t99), median(v99)
    y = ax.py(0.5)
    f.line(ax.px(tm), y, ax.px(vm), y, "a", arrow=True)
    later = [v / t for t, v in zip(t99, v99)]
    ax.note(1.5, 0.62, "the held-out equations pass 99%", "ta", 10.5, weight=600)
    ax.note(1.5, 0.62, f"{min(later):.1f} to {max(later):.1f} times later", "ta", 10.5, dy=15, weight=600)
    x = ax.x + ax.w + 14
    f.text(x, 60, "first at 99%", "t", 11, weight=700)
    for k, (t, v) in enumerate(zip(t99, v99)):
        f.text(x, 80 + k * 32, f"seed {k}: training {t}", "t", 10.5)
        f.text(x, 94 + k * 32, f"held out {v}, x{v / t:.1f}", "ta", 10.5)
    at = [next(r["val_acc"] for r in rows if r["step"] == t) for rows, t in zip(runs, t99)]
    f.text(x, 186, "held out, when training", "tm", 10.5)
    f.text(x, 200, f"passed 99%: {min(at):.3f} to {max(at):.3f}", "tm", 10.5)
    f.text(x, 222, f"a guess: {1 / cfg['p']:.4f}", "tm", 10.5)
    figart.legend(f, 60, 320, [("training equations", "s", True), ("held-out equations", "a", False)], across=True)
    return f


def loss1403():
    runs = figure_logs()
    cfg = figart.config(figart.seed_dirs(os.path.join(REC, "grokking"))[0])
    guess = math.log(cfg["p"])
    f = Fig("loss1403", f"The losses of the same run, in nats: the held-out loss climbs above a guess's ln "
                        f"{cfg['p']} after training passes 99%, peaks, and falls once the held-out equations are "
                        f"learned; a dot at each seed's peak", 326)
    ax = figart.Axes(f, 60, 40, 430, 220, (1, cfg["steps"]), (0, 6.5), True, False)
    ax.draw(xlabel="step (log scale)", ylabel="loss (nats)", yticks=[0, 1, 2, 3, 4, 5, 6],
            xticks=[1, 10, 100, 1000, cfg["steps"]])
    t99 = [first(rows, "train_acc") for rows in runs]
    v99 = [first(rows, "val_acc") for rows in runs]
    a, b = ax.px(min(t99)), ax.px(max(v99))
    f.add(f'<rect class="fs" x="{a:.1f}" y="{ax.y}" width="{b - a:.1f}" height="{ax.h}" fill-opacity="0.7"/>')
    f.text((a + b) / 2, ax.y + 14, "between the two 99% steps", "tm", 10, "middle")
    ax.hline(guess, None)
    ax.note(1.2, guess, f"a guess: ln {cfg['p']} = {guess:.3f}", "tm", 10.5, dy=15)
    for k, rows in enumerate(runs):
        rows = [r for r in rows if r["step"] >= 1]
        xs = [r["step"] for r in rows]
        width = 2 if k == 0 else 1.4
        ax.curve(xs, [r["train_loss"] for r in rows], "s", dash=True, width=width)
        ax.curve(xs, [r["val_loss"] for r in rows], "a", width=width)
    x = ax.x + ax.w + 14
    f.text(x, 56, "the held-out loss", "t", 11, weight=700)
    f.text(x, 70, "at its peak", "t", 11, weight=700)
    for k, rows in enumerate(runs):
        peak = max(rows, key=lambda r: r["val_loss"])
        ax.dot(peak["step"], peak["val_loss"], "a fa", 3.5)
        f.text(x, 92 + k * 30, f"seed {k}: {peak['val_loss']:.2f}", "ta", 10.5)
        f.text(x, 106 + k * 30, f"step {peak['step']}, x{peak['val_loss'] / guess:.2f}", "tm", 10.5)
    ends = [rows[-1] for rows in runs]
    f.text(x, 196, f"at step {ends[0]['step']}:", "t", 10.5)
    f.text(x, 210, f"{min(e['val_loss'] for e in ends):.3f} to {max(e['val_loss'] for e in ends):.3f}", "t", 10.5)
    figart.legend(f, 60, 318, [("training loss", "s", True), ("held-out loss", "a", False)], across=True)
    return f


NORM_CODE = """
import json, math
import torch
from models.gpt import GPT
torch.manual_seed(0)
m = GPT(101, 4, layers=2, heads=4, width=128)
sq = {n: (p.detach() ** 2).sum().item() for n, p in m.named_parameters()}
norms = sum(v for n, v in sq.items() if "norm" in n)
print(json.dumps({"all": math.sqrt(sum(sq.values())), "norms": math.sqrt(norms), "rest": math.sqrt(sum(sq.values()) - norms),
                  "ones": int(sum(p.numel() for n, p in m.named_parameters() if "norm" in n and n.endswith("weight")))}))
"""


def norm1403():
    runs = figure_logs()
    cfg = figart.config(figart.seed_dirs(os.path.join(REC, "grokking"))[0])
    d = in_project("14.03", NORM_CODE)
    if f"{d['all']:.4f}" != f"{runs[0][0]['norm']:.4f}":
        raise SystemExit(f"the GPT built here starts at {d['all']}, the recorded seed 0 at {runs[0][0]['norm']}")
    f = Fig("norm1403", f"The weights' norm over the same run, 3 seeds, a dot where the held-out accuracy reached 99%; "
                        f"most of it, from the start, is the layer norms' {d['ones']} ones", 294)
    ax = figart.Axes(f, 60, 40, 430, 190, (1, cfg["steps"]), (21, 29.5), True, False)
    ax.draw(xlabel="step (log scale)", ylabel="the weights' norm", yticks=[22, 24, 26, 28],
            xticks=[1, 10, 100, 1000, cfg["steps"]])
    ax.hline(d["norms"], f"the layer norms' {d['ones']} ones alone: {d['norms']:.1f}", side="left")
    for k, rows in enumerate(runs):
        rows = [r for r in rows if r["step"] >= 1]
        ax.curve([r["step"] for r in rows], [r["norm"] for r in rows], "a", width=2 if k == 0 else 1.4)
        v = first(rows, "val_acc")
        at = next(r["norm"] for r in rows if r["step"] == v)
        ax.dot(v, at, "a fa", 3.5)
    x = ax.x + ax.w + 14
    f.text(x, 56, "the norm", "t", 11, weight=700)
    f.text(x, 76, f"at the start {runs[0][0]['norm']:.1f}:", "t", 10.5)
    f.text(x, 90, f"layer norms {d['norms']:.1f},", "tm", 10.5)
    f.text(x, 104, f"the rest {d['rest']:.1f}", "tm", 10.5)
    f.text(x, 126, "at the held-out 99%:", "t", 10.5)
    vals = []
    for rows in runs:
        v = first(rows, "val_acc")
        before = [r["norm"] for r in rows if r["step"] <= v]
        vals.append((before[-1], before[-1] / max(before)))
    f.text(x, 140, ", ".join(f"{a:.1f}" for a, _ in vals), "ta", 10.5)
    f.text(x, 154, "of its highest before:", "tm", 10.5)
    f.text(x, 168, ", ".join(f"{r:.2f}" for _, r in vals), "ta", 10.5)
    f.text(60, 286, f"The norm is the square root of a sum of squares: {d['norms']:.1f}^2 + {d['rest']:.1f}^2 = "
                    f"{d['all']:.1f}^2, so a change in the rest moves it little.", "tm", 10.5)
    return f


def later1403():
    runs = figure_logs()
    t99 = [first(rows, "train_acc") for rows in runs]
    v99 = [first(rows, "val_acc") for rows in runs]
    memo, late = claim("memorise"), claim("late")
    t_paper = 10 ** int(re.search(r"< 10\^(\d)", memo["says"]).group(1))
    v_paper = 10 ** int(re.search(r"close to 10\^(\d)", late["says"]).group(1))
    f = Fig("later1403", "Memorised to generalised on one log axis: our three seeds against the paper's figure 1 as "
                         "its caption gives it (training close to perfect at under 10^3 steps, validation close to "
                         "10^6)", 210)
    ax = figart.Axes(f, 150, 30, 450, 120, (100, 2e6), (0, 3), True, False)
    ax.draw(xlabel="step (log scale)", yticks=[], xticks=[100, 1000, 10000, 100000, 1000000], grid=False)
    for k, (t, v) in enumerate(zip(t99, v99)):
        y = ax.py(2.55 - k * 0.32)
        f.line(ax.px(t), y, ax.px(v), y, "a")
        f.circle(ax.px(t), y, 3.5, "s f")
        f.circle(ax.px(v), y, 3.5, "a fa")
        f.text(ax.px(v) + 8, y + 4, f"seed {k}: {t} -> {v}, x{v / t:.1f}", "ta", 10)
    f.text(ax.x - 10, ax.py(2.25) + 4, "ours (recorded)", "ta", 11, "end", 600)
    y = ax.py(0.7)
    f.line(ax.px(t_paper), y, ax.px(v_paper), y, "s", dash=True)
    f.circle(ax.px(t_paper), y, 3.5, "s f")
    f.circle(ax.px(v_paper), y, 3.5, "s fs")
    f.text(ax.px(t_paper) + 6, y - 8, f"under {t_paper}", "t", 10)
    f.text(ax.px(v_paper) - 6, y - 8, f"close to {v_paper:,}", "t", 10, "end")
    f.text(ax.x - 10, y + 4, "the paper's figure 1", "t", 11, "end", 600)
    f.text(16, 196, "Each line runs from the step training passed 99% to the step the held-out equations did. The "
                    "paper's: about 1000 times.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 14.04

def steps_chart(f, box, groups, ylim, xlabel, budget, title):
    """One column per setting: each seed's step to 99% on training (ring) and held out (dot), a run that never
    got there as an arrow over the budget; the held-out median as a bar."""
    x, y, w, h = box
    ax = figart.Axes(f, x, y, w, h, (-0.5, len(groups) - 0.5), ylim, False, True)
    ax.draw(xticks=[], yticks=[t for t in (100, 200, 500, 1000, 2000, 5000, 10000) if ylim[0] <= t <= ylim[1]],
            ylabel="step (log scale)")
    f.text(x, y - 24, title, "t", 11.5, weight=700)
    ax.hline(budget, f"the budget: {budget} steps", side="right")
    for i, (label, runs, style) in enumerate(groups):
        X = ax.px(i)
        f.text(X, y + h + 16, label, "ta" if style == "a" else "t", 11, "middle", 600)
        t99 = [first(rows, "train_acc") for rows in runs]
        v99 = [first(rows, "val_acc") for rows in runs]
        for k, (t, v) in enumerate(zip(t99, v99)):
            dx = (k - 1) * 9
            if t is not None:
                f.circle(X + dx - 18, ax.py(t), 3, "s f")
            if v is not None:
                f.circle(X + dx + 18, ax.py(v), 3.5, "a fa")
            else:
                Y = ax.py(budget)
                f.line(X + dx + 18, Y + 18, X + dx + 18, Y - 8, "a", arrow=True)
        never = sum(v is None for v in v99)
        got = sorted(v for v in v99 if v is not None)
        order = sorted(v99, key=lambda s: math.inf if s is None else s)
        med = order[len(order) // 2]
        if med is not None:
            f.line(X + 4, ax.py(med), X + 32, ax.py(med), "a")
            f.text(X + 36, ax.py(med) + 4, str(med), "ta", 10, mono=True)
        if never:
            f.text(X + 18, ax.py(budget) - 14, f"never: {never}", "ta", 10, "middle")
        del got
    return ax


def decay1404():
    decays = [0.0, 0.3, 1.0]
    groups = [(f"weight decay {d:g}", ablation(0.4, d, 1.0), "a" if d == 0 else "s") for d in decays]
    f = Fig("decay1404", "Steps to 99% at 40% of the equations, by weight decay, 3 seeds each: on the training "
                         "equations (rings, left) and the held-out ones (dots, right), the bar the held-out median; "
                         "an arrow: never, within 6000 steps", 300)
    ax = steps_chart(f, (70, 44, 400, 214), groups, (150, 12000), "weight decay", 6000,
                     "the weight decay of AdamW (03.04)")
    best = [max(r["val_acc"] for r in rows) for rows in groups[0][1]]
    x = 500
    f.text(x, 60, "without it, the best", "t", 10.5, weight=600)
    f.text(x, 74, "held-out accuracy in", "t", 10.5, weight=600)
    f.text(x, 88, "6000 steps:", "t", 10.5, weight=600)
    f.text(x, 104, ", ".join(f"{b:.3f}" for b in best), "ta", 10.5, mono=True)
    f.text(x, 126, "every seed memorised", "tm", 10.5)
    f.text(x, 140, f"by step {max(first(r, 'train_acc') for r in groups[0][1])}", "tm", 10.5)
    f.circle(x + 4, 186, 3, "s f")
    f.text(x + 14, 190, "training 99%", "t", 10.5)
    f.circle(x + 4, 206, 3.5, "a fa")
    f.text(x + 14, 210, "held out 99%", "ta", 10.5)
    del ax
    return f


def fraction1404():
    fracs = [0.35, 0.4, 0.5]
    runs = {fr: ablation(fr, 1.0, 1.0) for fr in fracs}
    f = Fig("fraction1404", "Steps to 99% by the fraction of the equations trained on, weight decay 1, 3 seeds each, "
                            "on a log scale both ways: rings training, dots held out, the line through the held-out "
                            "medians at 35% and 50%", 300)
    ax = figart.Axes(f, 70, 44, 380, 210, (0.33, 0.58), (150, 12000), True, True)
    ax.draw(xticks=fracs, yticks=[200, 500, 1000, 2000, 5000, 10000], xlabel="fraction of the equations (log scale)",
            ylabel="step (log scale)", xfmt=lambda v: f"{v:.0%}")
    ax.hline(6000, "the budget: 6000 steps", side="left")
    meds = {}
    for fr in fracs:
        t99 = [first(r, "train_acc") for r in runs[fr]]
        v99 = [first(r, "val_acc") for r in runs[fr]]
        X = ax.px(fr)
        for k, (t, v) in enumerate(zip(t99, v99)):
            dx = (k - 1) * 6
            if t is not None:
                f.circle(X + dx - 3, ax.py(t), 3, "s f")
            if v is not None:
                f.circle(X + dx + 3, ax.py(v), 3.5, "a fa")
            else:
                Y = ax.py(6000)
                f.line(X + dx + 3, Y + 18, X + dx + 3, Y - 8, "a", arrow=True)
        order = sorted(v99, key=lambda s: math.inf if s is None else s)
        meds[fr] = order[len(order) // 2]
    lo, hi = min(fracs), max(fracs)
    k = math.log(meds[lo] / meds[hi]) / math.log(hi / lo)
    f.line(ax.px(lo), ax.py(meds[lo]), ax.px(hi), ax.py(meds[hi]), "a", dash=True)
    ax.note(lo, meds[lo], f"median {meds[lo]}", "ta", 10, dx=8, dy=-6)
    ax.note(hi, meds[hi], f"median {meds[hi]}", "ta", 10, dx=10, dy=4)
    x = 480
    f.text(x, 76, "held-out steps grow as", "t", 10.5, weight=600)
    f.text(x, 92, "1 / fraction^k:", "t", 10.5, weight=600)
    f.text(x, 110, f"k = {k:.2f} here", "ta", 11, weight=700, mono=True)
    pk = paper_number(claim("less_data"))
    f.text(x, 128, f"about {pk[0]:g} in figure 1 (center)", "t", 10.5)
    f.text(x, 142, "(S5, 30% to 50%)", "tm", 10.5)
    tm = {fr: median([first(r, "train_acc") or 6000 for r in runs[fr]]) for fr in (lo, hi)}
    f.text(x, 170, "training 99%, median:", "t", 10.5)
    f.text(x, 184, f"{tm[lo]} at {lo:.0%}, {tm[hi]} at {hi:.0%}", "tm", 10.5)
    return f


def start1404():
    own, big = ablation(0.5, 1.0, 1.0), ablation(0.5, 1.0, 10.0)
    f = Fig("start1404", "At the paper's 50% of the equations, weight decay 1, 3 seeds each: the GPT as it starts "
                         "(every weight with sd 0.02, as GPT-2's) against every weight but the layer norms' 10 times "
                         "larger; dashed training, solid held out, a dot at each 99%", 352)
    budget = max(r[-1]["step"] for r in own + big)
    acc_panel(f, (56, 50, 250, 200), own, budget, "the GPT's own start", "t", xticks=[1, 10, 100, 1000])
    acc_panel(f, (380, 50, 250, 200), big, budget, "10 times larger", "ta", ylabel=False, xticks=[1, 10, 100, 1000])
    for x0, runs in ((56, own), (380, big)):
        t99 = [first(r, "train_acc") for r in runs]
        v99 = [first(r, "val_acc") for r in runs]
        later = ", ".join("never" if not (t and v) else f"{v / t:.1f}" for t, v in zip(t99, v99))
        f.text(x0, 306, f"times later: {later}", "ta" if runs is big else "t", 10.5, weight=600)
        n0 = [r[0]["norm"] for r in runs]
        nv = [next((x["norm"] for x in r if x["step"] == v), None) for r, v in zip(runs, v99)]
        f.text(x0, 324, f"the norm: {min(n0):.1f} at the start,", "tm", 10.5)
        f.text(x0, 340, ", ".join("-" if v is None else f"{v:.1f}" for v in nv) + " at the held-out 99%", "tm", 10.5)
    return f


REPORT_CODE = """
import json
from experiments.arithmetic import read_runs, read_seeds
from experiments.predictions import CLAIMS, verdict
from experiments.report import outcomes
got = outcomes(read_seeds("experiments/recorded/grokking"), read_runs("experiments/recorded/ablations"))
print(json.dumps([dict(key=c.key, where=c.where, paper=c.paper, rule=list(c.rule), value=got[c.key][0],
                       more=got[c.key][1], each=got[c.key][2], verdict=verdict(c.rule, got[c.key][0], got[c.key][1]))
                  for c in CLAIMS]))
"""


def report():
    return in_project("14.04", REPORT_CODE)


def size_held(c):
    """Whether a claim that held by a direction rule also held in size: the paper's number no more than 3 times
    further from the rule's line than ours, on a log scale (the factor 'about' allows). None for a claim whose
    paper gives no positive number, or whose rule is not a direction."""
    kind, line = c["rule"]
    pn = paper_number(c)
    if kind == "about" or pn is None or pn[0] <= 0 or c["value"] is None:
        return None
    p = math.sqrt(pn[0] * pn[1])
    return abs(math.log(p / line)) <= 3 * abs(math.log(c["value"] / line))


def verdicts1404():
    rows = report()
    for c in rows:
        c["kind"] = c["verdict"]
        if c["verdict"] == "held" and size_held(c) is False:
            c["kind"] = "held in direction only"
    rh = 25
    f = Fig("verdicts1404", "The report's ten claims: ours (dot) and the paper's number (ring) on a log scale of "
                            "their own, with the rule's line; held, held in direction only (the direction its rule "
                            "asked for, a size far from the paper's), or did not hold", 64 + len(rows) * rh + 40)
    x0, x1 = 150, 470
    f.text(16, 22, "claim", "tm", 10.5, weight=600)
    f.text(x0, 22, "ours (dot), the paper's (ring), the rule's line (dashed)", "tm", 10.5, weight=600)
    f.text(488, 22, "verdict", "tm", 10.5, weight=600)
    f.line(16, 30, 624, 30, "m")
    tally = {}
    for i, c in enumerate(rows):
        y = 50 + i * rh
        kind = c["kind"]
        tally[kind] = tally.get(kind, 0) + 1
        cls = {"held": "t", "held in direction only": "tm", "did not hold": "ta"}[kind]
        f.text(16, y + 4, c["key"], cls, 11, weight=700 if kind == "did not hold" else 600, mono=True)
        line = c["rule"][1]
        pn = paper_number(c)
        vals = [line, c["value"]] + ([math.sqrt(pn[0] * pn[1])] if pn and pn[0] > 0 else [])
        if c["rule"][0] == "about":
            vals += [line / 3, line * 3]
        lo, hi = min(vals) / 2.2, max(vals) * 2.2
        X = lambda v: x0 + (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)) * (x1 - x0)  # noqa: E731
        f.line(x0, y, x1, y, "m")
        f.line(X(line), y - 8, X(line), y + 8, "m", dash=True)
        if c["rule"][0] == "about":
            f.rect(X(line / 3), y - 6, X(line * 3) - X(line / 3), 12, "m fs", 2)
        if pn and pn[0] > 0:
            if pn[1] > pn[0]:
                f.line(X(pn[0]), y, X(pn[1]), y, "s")
            f.circle(X(math.sqrt(pn[0] * pn[1])), y, 4.5, "s f")
        elif pn:
            f.text(x1, y - 6, "the paper: about 0", "tm", 9.5, "end")
        f.circle(X(c["value"]), y, 3.5, "a fa" if kind == "did not hold" else ("s t" if cls == "t" else "m tm"))
        f.text(X(c["value"]) + (8 if X(c["value"]) < x1 - 40 else -8), y - 6, sig(c["value"]),
               "ta" if kind == "did not hold" else "t", 9.5, "start" if X(c["value"]) < x1 - 40 else "end", mono=True)
        f.text(488, y + 4, kind, cls, 10.5, weight=700 if kind != "held in direction only" else 600)
    y = 50 + len(rows) * rh + 4
    f.text(16, y, ", ".join(f"{kind}: {n}" for kind, n in sorted(tally.items(), key=lambda kv: -kv[1]))
           + f", of {len(rows)} claims. The report's own lines print held for both of the middle kind.", "tm", 10.5)
    return f


FIGS = [
    ("14.01-table", table1401),
    ("14.01-tokens", tokens1401),
    ("14.01-scored", scored1401),
    ("14.01-claims", claims1401),
    ("14.02-short", short1402),
    ("14.02-batches", batches1402),
    ("14.03-figure", figure1403),
    ("14.03-loss", loss1403),
    ("14.03-norm", norm1403),
    ("14.03-later", later1403),
    ("14.04-decay", decay1404),
    ("14.04-fraction", fraction1404),
    ("14.04-start", start1404),
    ("14.04-verdicts", verdicts1404),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
