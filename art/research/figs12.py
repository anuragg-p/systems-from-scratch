"""Figures for research module 12, Fine-tuning (lessons 12.01-12.04).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs12.py [12.02 ...]
                                    all of them, or those whose name starts so (DIR keeps the runs)

Every bar, curve and number comes from the reference code (tracks/research), run as the page runs it,
from GPT-2's and Banking77's fetched files, or from the recorded long run of 12.02:

  12.01  python3 -m experiments.classify (the page's run) and the same on all of the data (train=0
         test_per_class=0 "sizes=[100,300,1000,3000]", the run the page quotes); Banking77's parts and
         classes, a question's GPT-2 tokens and its bag of words, and GPT-2's vectors at END for the
         page's 3,000 training questions, in the project at 12.01; experiments/recorded/lora/full
  12.02  python3 -m experiments.lora (the page's run); a LoRA layer of rank 1 on a Linear layer of 4
         inputs and 3 outputs, and the peak memory of six training steps of each kind in fresh
         processes, in the project at 12.02; experiments/recorded/lora/ (its summaries and logs, and
         output.txt's table and step times)
  12.03  python3 -m experiments.instruct (the page's run, and its summaries' answers); the scored
         sets, the template's tokens and GPT-2's answers before tuning, in the project at 12.03
  12.04  python3 -m experiments.forgetting (the page's run, and its summaries);
         experiments/recorded/lora/ (summaries and logs)

Where a figure draws a number the page's run prints, it is computed here from the runs' files and
checked against what the run printed; a difference stops the script.

Needs PyTorch and the downloads (python3 -m data.fetch gpt2 banking77, in tracks/research). The runs
take about six minutes in all on the machine in NOTES.md; RESEARCH_FIGS_CACHE keeps them between
processes.
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

MOD = "12"
REC = os.path.join(figlib.TRACK, "experiments", "recorded", "lora")
METHODS = ["head", "lora1", "lora4", "lora8", "full"]
NAME = {"head": "the head alone", "lora1": "LoRA r = 1", "lora4": "LoRA r = 4", "lora8": "LoRA r = 8",
        "full": "every weight"}
TEXT = {"a": "ta", "s": "t", "m": "tm"}
_memo = {}


def in_project(at, code):
    """Run python code in the project as it stands at lesson `at`, in a fresh python; the JSON it prints
    last (once per process for the same code)."""
    if (at, code) in _memo:
        return _memo[at, code]
    d = figart.project(at)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d)
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"python in the project at {at} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    _memo[at, code] = json.loads(r.stdout.strip().splitlines()[-1])
    return _memo[at, code]


def mean(xs):
    return sum(xs) / len(xs)


def sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def welch(a, b):
    """Welch's t of a against b (lab.welch_t's)."""
    return (mean(a) - mean(b)) / math.sqrt(sd(a) ** 2 / len(a) + sd(b) ** 2 / len(b))


def need(cond, what):
    if not cond:
        raise SystemExit(f"figs12: {what}")


def summaries(d):
    return [figart.summary(x) for x in figart.seed_dirs(d)]


def spread_of(text):
    """lab.spread's line, '0.7732 +- 0.002703 (min 0.7701, max 0.7753, 3 seeds)': (mean, sd, min, max, n)."""
    m = re.match(r"(\S+) \+- (\S+) \(min (\S+), max (\S+), (\d+) seeds\)", text)
    return tuple(float(v) for v in m.groups()[:4]) + (int(m.group(5)),)


def same4(values, printed):
    """The mean of values, as lab.spread prints it with 4 significant digits, is printed."""
    need(sig(mean(values), 4) == printed, f"the summaries' mean {mean(values)} is not the printed {printed}")


def shown(s):
    """Text as a figure writes it, in ASCII: a line break as \\n, anything outside printable ASCII as its escape."""
    out = []
    for c in s:
        if c == "\n":
            out.append("\\n")
        elif 32 <= ord(c) < 127:
            out.append(c)
        else:
            out.append(ascii(c)[1:-1])
    return "".join(out)


def chip(f, x, y, s, cls="s f", tcls="t", size=10.5, h=20, pad=5, weight=None, dash=False):
    """A box round one piece of text in mono, its width from the text; the x after it."""
    w = max(tw(s, size, mono=True) + 2 * pad, 14)
    f.rect(x, y, w, h, cls, 3, dash=dash)
    f.text(x + w / 2, y + h / 2 + size * 0.36, s, tcls, size, "middle", weight, mono=True)
    return x + w


def cut(s, n):
    return s if len(s) <= n else s[:n - 3] + "..."


# ------------------------------------------------------------------ the runs

def cls_run():
    return figart.experiment("classify", at="12.01")


def cls_all():
    return figart.experiment("classify", "train=0", "test_per_class=0", "sizes=[100,300,1000,3000]", at="12.01")


def lora_run():
    return figart.experiment("lora", at="12.02")


def ins_run():
    return figart.experiment("instruct", at="12.03")


def fgt_run():
    return figart.experiment("forgetting", at="12.04")


def accuracies(r, label):
    return [s["test_accuracy"] for s in summaries(os.path.join(r.runs, label))]


def recorded():
    """The recorded run: {method: [(summary, log rows) for each seed]}, its table checked against output.txt."""
    out = {m: [(figart.summary(d), figart.read_log(d)) for d in figart.seed_dirs(os.path.join(REC, m))]
           for m in METHODS}
    with open(os.path.join(REC, "output.txt")) as fh:
        printed = fh.read()
    for m, seeds in out.items():
        line = re.search(rf"^   {m} +([\d,]+) +[\d.]+%   (\S+) \+-", printed, re.M)
        need(line.group(1) == f"{seeds[0][0]['trained']:,}", f"recorded {m}: trained {line.group(1)}")
        same4([s["test_accuracy"] for s, _ in seeds], line.group(2))
    return out


def step_times():
    """The recorded run's ms a step, each method's each seed, as output.txt has them; and its part 3, a step of
    every weight and of LoRA at rank 8 back to back, at the run's start: {"full": ms, "lora8": ms}."""
    with open(os.path.join(REC, "output.txt")) as fh:
        printed = fh.read()
    out = {}
    for m, seed, ms in re.findall(r"^   (\w+) seed (\d): test accuracy [\d.]+; \d+ s of training, (\d+) ms a step", printed,
                                  re.M):
        out.setdefault(m, []).append(int(ms))
    pair = {m: int(ms) for m, ms in re.findall(r"^   (full|lora8) +(\d+) ms a step; trains", printed, re.M)}
    return out, pair


# ------------------------------------------------------------------ 12.01

DATA_CODE = """
import json, numpy as np
from data import banking77
names = banking77.classes()
parts = {n: banking77.split(n) for n in ("train", "valid", "test")}
texts, labels = parts["test"]
show = ["card_arrival", "card_not_working", "card_payment_fee_charged", "transfer_fee_charged",
        "cash_withdrawal_charge", "pending_top_up"]
examples = [[c, next(t for t, l in zip(texts, labels) if l == names.index(c) and len(t) < 60)] for c in show]
counts = np.bincount(parts["train"][1], minlength=77)
print(json.dumps({"n": {k: len(v[0]) for k, v in parts.items()}, "rows": len(banking77._read("train.csv")[0]),
                  "classes": len(names), "train_counts": counts.tolist(),
                  "test_counts": np.bincount(labels, minlength=77).tolist(), "examples": examples,
                  "largest": names[int(counts.argmax())], "smallest": names[int(counts.argmin())]}))
"""


def data1201():
    d = in_project("12.01", DATA_CODE)
    out = cls_all().out
    n = d["n"]
    need(f"{n['train']:,} training questions, {n['test']:,} test questions, {d['classes']} intents" in out,
         "Banking77's sizes are not the all-data run's")
    big = max(d["train_counts"])
    need(f"{d['largest']}, is {big / n['train']:.2%}" in out, "the largest class is not the run's")
    left = d["rows"] - n["train"] - n["valid"]
    f = Fig("data1201", f"Banking77: six of its test questions and their intents; how its two files are cut into "
                        f"the parts this module uses; and the {d['classes']} intents' sizes in the part trained on", 404)
    f.text(20, 24, "A question, and its intent (one of 77)", "t", 11.5, weight=700)
    for i, (c, q) in enumerate(d["examples"]):
        y = 46 + i * 21
        f.text(20, y, '"' + q + '"', "t", 11)
        f.text(620, y, c, "ta", 10.5, "end", 600, mono=True)
    # the split
    y0 = 196
    f.text(20, y0, "The parts", "t", 11.5, weight=700)
    W = 250
    scale = W / d["rows"]
    y = y0 + 30
    f.text(20, y + 15, "train.csv", "tm", 10.5, mono=True)
    x = 92
    for label, k, cls, tcls in (("valid", n["valid"], "s fs", "t"), ("train", n["train"], "a af", "ta")):
        w = k * scale
        f.rect(x, y, w, 22, cls, 2)
        if label == "valid":
            f.text(x, y - 6, f"valid {k:,}", tcls, 10.5, weight=600)
        else:
            f.text(x + w / 2, y + 15, f"train {k:,}", tcls, 10.5, "middle", 600)
        x += w
    f.rect(x, y, max(left * scale, 2), 22, "m f", 1)
    f.text(x + 6, y + 15, f"{left} left out", "tm", 10, "start")
    f.text(92, y + 36, f"{d['rows']:,} questions; valid drawn by a seed, once;", "tm", 10)
    f.text(92, y + 50, "left out: the same as a scored question", "tm", 10)
    y += 70
    f.text(20, y + 15, "test.csv", "tm", 10.5, mono=True)
    w = n["test"] * scale
    f.rect(92, y, w, 22, "s f", 2)
    f.text(92 + w / 2, y + 15, f"test {n['test']:,}", "t", 10.5, "middle", 600)
    f.text(92 + w + 8, y + 10, f"{min(d['test_counts'])} of each intent,", "tm", 10)
    f.text(92 + w + 8, y + 23, "kept whole", "tm", 10)
    f.text(20, y + 50, "valid chooses the settings; every score is on test.", "tm", 10.5)
    # the class sizes
    counts = sorted(d["train_counts"], reverse=True)
    ax = figart.Axes(f, 440, y0 + 14, 180, 110, (-0.5, len(counts) - 0.5), (0, 180))
    ax.draw(xticks=[], yticks=[0, 40, 80, 120, 160], frame=False)
    bw = ax.w / len(counts)
    for i, c in enumerate(counts):
        f.rect(ax.x + i * bw + 0.2, ax.py(c), bw - 0.4, ax.py(0) - ax.py(c), "a af", 0, sw=False)
    f.line(ax.x, ax.py(0), ax.x + ax.w, ax.py(0), "m")
    f.text(410, y0, "questions of each intent in train", "t", 11.5, weight=700)
    f.text(ax.x + ax.w / 2, ax.y + ax.h + 14, "77 intents, largest first", "tm", 10, "middle")
    f.text(410, ax.y + ax.h + 32, f"largest {counts[0]}: {d['largest']}", "tm", 9.5)
    f.text(410, ax.y + ax.h + 46, f"smallest {counts[-1]}: {d['smallest']}", "tm", 9.5)
    f.text(410, ax.y + ax.h + 64, f"always the largest: {big / n['train']:.2%} of train,", "tm", 10)
    f.text(410, ax.y + ax.h + 78, f"{min(d['test_counts']) / n['test']:.2%} of test", "tm", 10)
    return f


HEAD_CODE = """
import json, torch
from models import gpt2 as M
from models.gpt import GPT
from tokens import gpt2
tok = gpt2.load()
ids = tok.encode(QUESTION) + [gpt2.END]
with torch.device("meta"):
    body = GPT(**M.CONFIG)
print(json.dumps({"pieces": [tok.decode([i]) for i in ids], "ids": ids, "body": sum(p.numel() for p in body.parameters()),
                  "layers": len(body.blocks), "width": body.tokens.weight.shape[1], "end": gpt2.END}))
"""


def example():
    m = re.search(r"For example '(.*)': (\w+)", cls_run().out)
    return m.group(1), m.group(2)


def head1201():
    q, intent = example()
    d = in_project("12.01", HEAD_CODE.replace("QUESTION", repr(q)))
    out = cls_run().out
    classes = 77
    head = d["width"] * classes + classes
    need(f"Trained: the head's {head:,} weights of {head + d['body']:,}" in out, "the head's count is not the run's")
    f = Fig("head1201", f"Where the head reads: a question and END through GPT-2's {d['layers']} blocks, frozen; the "
                        f"causal mask lets the vector at END read every token of the question; the head, the one "
                        f"part trained, reads that vector standardised", 330)
    pieces = [shown(p) if p != "<|endoftext|>" else "END" for p in d["pieces"]]
    xs, x = [], 24
    for p in pieces:
        w = max(tw(p, 10.5, True) + 10, 26)
        xs.append((x, w))
        x += w + 6
    yb = 266
    for (x, w), p, i in zip(xs, pieces, d["ids"]):
        last = p == "END"
        f.rect(x, yb, w, 22, "a af" if last else "s f", 3)
        f.text(x + w / 2, yb + 15, p, "ta" if last else "t", 10.5, "middle", 700 if last else None, mono=True)
        f.text(x + w / 2, yb + 36, str(i), "tm", 9, "middle", mono=True)
    bx0, bx1 = 14, max(xs[-1][0] + xs[-1][1] + 10, 330)
    need(bx1 < 430, f"the question's tokens are too wide for the figure: {bx1}")
    f.rect(bx0, 78, bx1 - bx0, 150, "m fs", 8)
    f.text(bx0 + 10, 96, f"GPT-2's body: {d['layers']} blocks, width {d['width']}", "t", 11.5, weight=700)
    f.text(bx0 + 10, 112, f"frozen: {d['body']:,} weights, not trained", "tm", 10.5)
    ex, ew = xs[-1]
    cx = ex + ew / 2
    for (x, w), p in zip(xs, pieces):
        f.line(x + w / 2, yb - 2, x + w / 2, 232, "m")
        f.line(x + w / 2, 226, cx, 132 if p != "END" else 132, "m" if p != "END" else "a")
    f.line(cx, 132, cx, 58, "a", arrow=True)
    f.text(cx - 8, 150, "END's vector", "ta", 10.5, "end", 600)
    f.text(cx - 8, 164, "has read them all", "ta", 10.5, "end")
    # the vector and the head, down the right side
    f.rect(cx - 22, 30, 44, 26, "a af", 3)
    f.text(cx, 47, f"{d['width']}", "ta", 10.5, "middle", 700, mono=True)
    rx = 448
    f.line(cx + 22, 43, rx - 4, 43, "a", arrow=True)
    f.label_box(rx, 26, 176, 34, "(v - center) / spread", "a af", "ta", 10.5, True, 5, 600)
    f.text(rx + 88, 76, "center, spread: fixed from the", "tm", 10, "middle")
    f.text(rx + 88, 89, "training questions' vectors", "tm", 10, "middle")
    f.line(rx + 88, 96, rx + 88, 112, "a", arrow=True)
    f.label_box(rx, 114, 176, 38, "head", "a af", "ta", 11, True, 5, 700, sub=f"Linear {d['width']} -> {classes}")
    f.text(rx + 88, 170, f"{head:,} weights, trained", "ta", 10.5, "middle", 600)
    f.line(rx + 88, 176, rx + 88, 192, "a", arrow=True)
    f.text(rx + 88, 208, f"{classes} scores; the highest:", "t", 10.5, "middle")
    f.text(rx + 88, 224, intent, "ta", 10.5, "middle", 700, mono=True)
    f.text(20, 320, f"The ids under the tokens are GPT-2's; END is {d['end']}, <|endoftext|>, put after every question.",
           "tm", 10.5)
    return f


BAG_CODE = """
import json, numpy as np
from data import banking77
from experiments.classify import bag, subset, words
texts, labels = banking77.split("train")
texts = [texts[i] for i in subset(3000, labels, np.random.default_rng(0))]
vocab = {}
for t in texts:
    for w in words(t):
        vocab.setdefault(w, len(vocab))
q = QUESTION
x = bag([q, SHUFFLED], vocab)
print(json.dumps({"vocab": len(vocab), "words": words(q), "cols": [vocab.get(w) for w in words(q)],
                  "same": x[0].tolist() == x[1].tolist(), "lit": int((x[0] > 0).sum())}))
"""


def bag1201():
    q, intent = example()
    shuffled = " ".join(reversed(q.split()))
    d = in_project("12.01", BAG_CODE.replace("QUESTION", repr(q)).replace("SHUFFLED", repr(shuffled)))
    out = cls_run().out
    need(f"A bag of words ({d['vocab']:,} training words)" in out, "the bag's vocabulary is not the run's")
    need(d["same"], "a question and its words reversed should make the same bag")
    classes = 77
    weights = d["vocab"] * classes + classes
    f = Fig("bag1201", f"The baseline: a question as a bag of words, one count for each of the {d['vocab']:,} words of "
                       f"the training questions, read by a Linear layer; the order of the words is gone", 232)
    f.text(20, 24, f'"{q}"', "t", 11.5, weight=700)
    x = 20
    for w in d["words"]:
        x = chip(f, x, 36, w, "s f", "t") + 5
    f.text(x + 6, 50, "words(): letters, digits, ', in lower case", "tm", 10)
    # the counts strip
    x0, W, y = 20, 600, 92
    f.text(x0, y - 8, f"its counts: a row of {d['vocab']:,} numbers, one for each training word, in the order "
                      f"first seen", "tm", 10.5)
    f.rect(x0, y, W, 22, "s fs", 2)
    for w, c in zip(d["words"], d["cols"]):
        if c is None:
            continue
        cxp = x0 + W * (c + 0.5) / d["vocab"]
        f.rect(cxp - 1.5, y, 3, 22, "a fa", 0, sw=False)
    f.text(x0, y + 38, "  ".join(f"{w}: {c}" for w, c in zip(d["words"], d["cols"]) if c is not None), "ta", 10,
           mono=True)
    f.text(x0 + W, y + 38, "(word: its column)", "tm", 10, "end")
    f.text(x0, y + 58, f"{d['lit']} of the {d['vocab']:,} are 1, the rest 0. The same words in any order make the "
                       f"same row:", "tm", 10.5)
    f.text(x0, y + 74, f'"{shuffled}" too.', "tm", 10.5, mono=True)
    f.label_box(x0, y + 92, 236, 34, f"Linear {d['vocab']:,} -> {classes}", "s f", "t", 11, True, 5, 700,
                sub=f"{weights:,} weights, all trained")
    f.line(x0 + 238, y + 109, x0 + 270, y + 109, "s", arrow=True)
    f.text(x0 + 278, y + 105, f"{classes} scores; trained as the head is, at its own rate,", "t", 10.5)
    f.text(x0 + 278, y + 121, "chosen on valid (AdamW 0.03)", "t", 10.5)
    return f


SPREAD_CODE = """
import json, numpy as np, torch
from data import banking77
from experiments.classify import subset
from experiments.tuning import vectors
from models import gpt2 as M
from models.classifier import Classifier
from tokens import gpt2
tok = gpt2.load()
texts, labels = banking77.split("train")
at = subset(3000, labels, np.random.default_rng(0))
seqs = [tok.encode(texts[i]) + [gpt2.END] for i in at]
dev = torch.device("cpu")
model = Classifier(M.load(dev), 77)
v = vectors(model, seqs, gpt2.END, dev)
model.standardise(v)
one = [k for k, i in enumerate(at) if texts[i] == QUESTION][0]
print(json.dumps({"sd": v.std(0).tolist(), "mean": v.mean(0).tolist(), "raw": v[one].tolist(),
                  "std": ((v[one] - model.center) / model.spread).tolist()}))
"""


def spread1201():
    q, intent = example()
    d = in_project("12.01", SPREAD_CODE.replace("QUESTION", repr(q)))
    r = cls_run()
    out = r.out
    sds, means = d["sd"], d["mean"]
    med = sorted(sds)[len(sds) // 2 - 1: len(sds) // 2 + 1]
    need(f"most numbers vary by about {mean(med):.3f}" in out, f"the median spread {mean(med)} is not the run's")
    big = sorted(range(len(sds)), key=lambda i: -sds[i])[:3]
    need(", ".join(f"number {i} by {sds[i]:.2f} around {means[i]:.1f}" for i in big) in out,
         "the three widest numbers are not the run's")
    raw, std = accuracies(r, "frozen-raw"), accuracies(r, "frozen")
    f = Fig("spread1201", f"GPT-2's 768 numbers at END for one question ('{q}'): as they come, a few numbers in the "
                          f"tens and hundreds and the rest near 0; standardised over the 3,000 training questions, all "
                          f"on one scale; and the training loss of the same head on each, 3 seeds", 430)

    def strip(x0, y0, w, h, vals, lim, ticks, title, cls):
        ax = figart.Axes(f, x0, y0, w, h, (0, len(vals)), lim)
        ax.draw(xticks=[0, 256, 512, 768], yticks=ticks, xlabel="number (0 to 767)")
        y = ax.py(0)
        path = "".join(f"M{ax.px(i + 0.5):.1f} {y:.1f}V{ax.py(max(min(v, lim[1]), lim[0])):.1f}"
                       for i, v in enumerate(vals))
        f.path(path, cls)
        f.text(x0, y0 - 10, title, "t", 11.5, weight=700)
        return ax
    low = min(d["raw"])
    need(low > -100, f"a number of the raw vector below the figure's range: {low}")
    ax = strip(58, 40, 240, 130, d["raw"], (-100, 200), [-100, 0, 100, 200], "as GPT-2 gives them", "s")
    ax.note(d["raw"].index(low) + 0.5, low, str(d["raw"].index(low)), "t", 10, "middle", dy=13, weight=600)
    for i in big:
        ax.note(i + 0.5, d["raw"][i], str(i), "t", 10, "middle", dy=-5, weight=600)
    ax2 = strip(380, 40, 240, 130, d["std"], (-6, 6), [-6, -3, 0, 3, 6], "standardised", "a")
    for i in big:
        ax2.note(i + 0.5, -5.5, str(i), "ta", 9.5, "middle", dy=0)
    f.text(58, 222, f"Over the 3,000 training questions most numbers vary by about {mean(med):.3f}; number {big[0]} "
                    f"sits near {means[big[0]]:.1f} and varies by {sds[big[0]]:.2f}.", "tm", 10.5)
    f.text(58, 238, "Standardised: each number less its mean there, over its spread there (center and spread, fixed "
                    "before training).", "tm", 10.5)
    # the loss curves
    series = []
    for label, style, name in (("frozen-raw", "s", "as they come"), ("frozen", "a", "standardised")):
        xs, m, lo, hi = figart.over_seeds(figart.seed_dirs(os.path.join(r.runs, label)), "loss")
        series.append(figart.Series(name, xs, m, style, lo=lo, hi=hi))
    ax3 = figart.plot(f, (10, 252, 440, 176), series, xlabel="step (batches of 64)", ylabel="training loss of the head",
                      ylim=(0, 13), yticks=[0, 4, 8, 12], legend="right")
    ax3.hline(math.log(77), "ln 77: knowing nothing", "m", side="right")
    first = [figart.read_log(x)[0]["loss"] for x in figart.seed_dirs(os.path.join(r.runs, "frozen-raw"))]
    ax3.note(0, max(first), f"first batch {min(first):.1f} to {max(first):.1f}", "t", 10, "start", dx=8, dy=4)
    f.text(468, 330, "test accuracy, 3 seeds:", "t", 10.5, weight=700)
    f.text(468, 348, f"as they come  {mean(raw):.3f}", "t", 10.5, mono=True)
    f.text(468, 364, f"standardised  {mean(std):.3f}", "ta", 10.5, weight=700, mono=True)
    f.text(468, 382, "the same head, the same", "tm", 10.5)
    f.text(468, 396, "rate (AdamW 0.003), the", "tm", 10.5)
    f.text(468, 410, "same 500 steps", "tm", 10.5)
    same4(raw, re.search(r"as they come, .*test accuracy\n   (\S+) \+-", out).group(1))
    same4(std, re.search(r"standardised \(each.*\n   test accuracy (\S+) \+-", out).group(1))
    return f


def columns(f, box, groups, ylim, yticks, ylabel=""):
    """figart.seeds_chart's columns (a ring per seed, the bar their mean, the whisker min to max), with each mean
    written to 3 decimals left of its bar, so a column at the right edge keeps its number inside the box."""
    bx, by, bw, bh = box
    lines = max(len(g[0].split("\n")) for g in groups)
    ax = figart.Axes(f, bx + 40, by + 22, bw - 44, bh - 30 - 14 * lines, (-0.5, len(groups) - 0.5), ylim)
    ax.draw(xticks=[], yticks=yticks, ylabel=ylabel)
    for i, (label, vs, style) in enumerate(groups):
        X = ax.px(i)
        for k, line in enumerate(label.split("\n")):
            f.text(X, ax.y + ax.h + 15 + 14 * k, line, TEXT[style] if k == 0 else "tm", 10.5, "middle",
                   600 if style == "a" and k == 0 else None)
        ax.whisker(i, vs, style, cap=5, mean=False)
        for v in vs:
            f.circle(X, ax.py(v), 2.5, f"{style} f")
        m = mean(vs)
        f.line(X - 12, ax.py(m), X + 12, ax.py(m), style)
        last = i == len(groups) - 1
        f.text(X - 16 if last else X + 16, ax.py(m) + 3.5, f"{m:.3f}", TEXT[style], 10, "end" if last else "start",
               600 if style == "a" else None, mono=True)
    return ax


def models1201():
    r, a = cls_run(), cls_all()
    page = {k: accuracies(r, k) for k in ("bag", "small", "frozen-raw", "frozen")}
    alld = {k: accuracies(a, k) for k in ("bag", "small", "frozen")}
    full = [s["test_accuracy"] for s, _ in recorded()["full"]]
    for run, got in ((r, page), (a, alld)):
        same4(got["bag"], re.search(r"Linear layer, 500 steps of 64, AdamW 0.03:\n   test accuracy (\S+) \+-",
                                    run.out).group(1))
        same4(got["small"], re.search(r"AdamW 0.003:\n   test accuracy (\S+) \+-", run.out).group(1))
    largest = float(re.search(r"always guessing it scores ([\d.]+)%", r.out).group(1)) / 100
    f = Fig("models1201", "Test accuracy of each model, a ring per seed, the bar their mean, the whisker min to max: in "
                          "the page's run (3,000 questions to train on, 770 to test) and on all of Banking77 (8,997 and "
                          "all 3,080); every weight fine-tuned is 12.02's recorded run", 330)
    f.text(14, 18, "the page's run: 3,000 and 770", "t", 11.5, weight=700)
    ax = columns(f, (8, 22, 308, 278),
                 [("bag of\nwords", page["bag"], "s"), ("08's GPT\nfrom nothing", page["small"], "s"),
                  ("frozen,\nas they come", page["frozen-raw"], "m"), ("frozen,\nstandardised", page["frozen"], "a")],
                 (0, 0.9), [0, 0.2, 0.4, 0.6, 0.8], "test accuracy")
    ax.hline(largest, f"always the largest class: {largest:.3f}", "m", side="left")
    f.text(332, 18, "all of the data: 8,997 and 3,080", "t", 11.5, weight=700)
    columns(f, (326, 22, 310, 278),
            [("bag of\nwords", alld["bag"], "s"), ("08's GPT\nfrom nothing", alld["small"], "s"),
             ("frozen,\nstandardised", alld["frozen"], "a"), ("every weight\nfine-tuned", full, "a")],
            (0.74, 0.92), [0.75, 0.8, 0.85, 0.9], "test accuracy")
    f.text(20, 322, "The frozen body is GPT-2's with a new head; 08's GPT is trained from nothing on the questions alone.",
           "tm", 10.5)
    return f


def fewer1201():
    r = cls_run()
    sizes = [100, 300, 1000, 3000]
    got = {}
    for who in ("bag", "frozen"):
        got[who] = [accuracies(r, f"{who}-{n}") for n in sizes[:-1]] + [accuracies(r, who)]
    for n, b, fz in zip(sizes, got["bag"], got["frozen"]):
        line = re.search(rf"^ +{n:,} +(\S+) \+- .*?  +(\S+) \+-", r.out, re.M)
        need(sig(mean(b)) == line.group(1) and sig(mean(fz)) == line.group(2), f"fewer questions at {n}: {line.groups()}")
    f = Fig("fewer1201", "Test accuracy against the number of labelled questions trained on (a random part of the 3,000 "
                         "for each seed; 770 test questions): the bag of words and GPT-2's frozen body with a head, 3 "
                         "seeds each, the whisker min to max", 300)
    ax = figart.Axes(f, 70, 30, 400, 210, (70, 4300), (0.1, 0.9), logx=True)
    ax.draw(xticks=sizes, yticks=[0.1, 0.3, 0.5, 0.7, 0.9], xfmt=lambda v: f"{int(v):,}",
            xlabel="labelled questions trained on", ylabel="test accuracy")
    for who, style, anchor, dx, dy in (("bag", "s", "end", -9, -8), ("frozen", "a", "start", 9, 15)):
        ms = [mean(v) for v in got[who]]
        ax.curve(sizes, ms, style, width=2)
        for n, v, m in zip(sizes, got[who], ms):
            ax.whisker(n, v, style, cap=4, mean=False)
            ax.dot(n, m, "a fa" if style == "a" else "s f", 3.5)
            a, x = (anchor, dx) if n < 3000 else ("end", -9)
            ax.note(n, m, f"{m:.3f}", TEXT[style], 10, a, dx=x, dy=dy, weight=600)
    figart.legend(f, 492, 60, [("bag of words", "s"), ("frozen body, head", "a")])
    f.text(492, 110, "The bag of words is", "tm", 10.5)
    f.text(492, 124, "ahead at every size,", "tm", 10.5)
    f.text(492, 138, "once its rate is its", "tm", 10.5)
    f.text(492, 152, "own (chosen on valid).", "tm", 10.5)
    f.text(20, 290, "77 intents: 100 questions is about one of each.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 12.02

def counts():
    """Part 1 of the page's run: {rank: (A and B, the formula, % of the body, % with the head)}."""
    out = lora_run().out
    rows = {int(m.group(1)): (int(m.group(2).replace(",", "")), int(m.group(3).replace(",", "")), m.group(4), m.group(5))
            for m in re.finditer(r"^ +(\d) +([\d,]+) +([\d,]+) +([\d.]+)% +([\d.]+)%$", out, re.M)}
    need(sorted(rows) == [1, 4, 8], f"lora: the counts' rows {rows}")
    total = int(re.search(r"GPT-2 small: ([\d,]+) weights", out).group(1).replace(",", ""))
    return rows, total


def adapter1202():
    rows, total = counts()
    d, layers = 768, 12
    for r, (n, formula, pb, ph) in rows.items():
        need(n == formula == 2 * 2 * layers * d * r, f"rank {r}: {n} {formula}")
        need(f"{100 * n / total:.3f}" == pb and f"{100 * (n + d * 77 + 77) / total:.3f}" == ph, f"rank {r}: {pb} {ph}")
    f = Fig("adapter1202", "One weight of GPT-2, W_q of a block (768 x 768), frozen, and LoRA's change beside it: B (768 "
                           "x r) times A (r x 768), started at 0; what it trains at ranks 1, 4 and 8, for one matrix and "
                           "for W_q and W_v of all 12 blocks", 300)
    x0, y0, S = 24, 52, 150
    f.text(x0, 30, "h = W x + (alpha / r) B A x", "t", 11.5, weight=700, mono=True)
    f.rect(x0, y0, S, S, "m fs", 3)
    f.text(x0 + S / 2, y0 + S / 2 - 4, "W", "t", 16, "middle", 700, mono=True)
    f.text(x0 + S / 2, y0 + S / 2 + 14, "frozen", "tm", 10.5, "middle")
    f.text(x0 + S / 2, y0 + S + 16, f"{d} x {d} = {d * d:,}", "tm", 10.5, "middle", mono=True)
    f.text(x0 + S + 14, y0 + S / 2 + 6, "+", "t", 18, "middle", 700)
    bx = x0 + S + 30
    f.rect(bx, y0, 14, S, "a af", 2)
    f.text(bx + 7, y0 - 6, "B", "ta", 12, "middle", 700, mono=True)
    f.text(bx + 7, y0 + S + 16, f"{d} x r", "ta", 10, "middle", mono=True)
    f.text(bx + 24, y0 + S / 2 + 4, "x", "t", 12, "middle", mono=True)
    ax_ = bx + 34
    f.rect(ax_, y0 + S / 2 - 7, S, 14, "a af", 2)
    f.text(ax_ + S / 2, y0 + S / 2 - 12, "A", "ta", 12, "middle", 700, mono=True)
    f.text(ax_ + S / 2, y0 + S / 2 + 24, f"r x {d}", "ta", 10, "middle", mono=True)
    f.text(ax_ + S / 2, y0 + S / 2 + 44, "A: random; B: all 0,", "tm", 10, "middle")
    f.text(ax_ + S / 2, y0 + S / 2 + 58, "so B A starts at 0", "tm", 10, "middle")
    f.text(bx, y0 + S + 34, "(r drawn wider than it is: at r = 8, B is 1 % as wide as W)", "tm", 9.5)
    # the table
    tx = 384
    cols = [tx, tx + 24, tx + 88, tx + 156, tx + 206]
    heads = ["r", "one matrix", "all 24", "of GPT-2", "and head"]
    for c, h in zip(cols, heads):
        f.text(c, 30, h, "tm", 10, "start")
    for k, (r, (n, _, pb, ph)) in enumerate(sorted(rows.items())):
        y = 56 + k * 26
        cls = "ta" if r == 8 else "t"
        f.text(cols[0] + 6, y, str(r), cls, 11, "middle", 700, mono=True)
        f.text(cols[1], y, f"{2 * d * r:,}", cls, 11, mono=True)
        f.text(cols[2], y, f"{n:,}", cls, 11, mono=True)
        f.text(cols[3], y, f"{pb}%", cls, 11, mono=True)
        f.text(cols[4], y, f"{ph}%", cls, 11, mono=True)
    f.text(tx, 150, f"one matrix: 2 x {d} x r (A and B)", "tm", 10.5)
    f.text(tx, 166, f"all 24: W_q and W_v of {layers} blocks,", "tm", 10.5)
    f.text(tx, 180, f"2 x 24 x {d} x r, the paper's count", "tm", 10.5)
    f.text(tx, 196, f"of GPT-2: of its {total:,}", "tm", 10.5)
    f.text(tx, 210, f"and head: with the classifier's {d * 77 + 77:,}", "tm", 10.5)
    f.text(24, 284, "alpha / r scales the change: alpha = 8 at every rank, so r = 1's B A counts 8 times, r = 8's once.",
           "tm", 10.5)
    return f


MERGE_CODE = """
import json, torch
from torch import nn
from models.lora import LoRA
lin = nn.Linear(4, 3, bias=False)
with torch.no_grad():
    lin.weight.copy_(torch.tensor([[1., 0., 2., -1.], [0., 1., 0., 1.], [2., -1., 1., 0.]]))
layer = LoRA(lin, 1, 2)
x = torch.ones(1, 4)
start = (layer(x) - lin(x)).abs().max().item()
with torch.no_grad():
    layer.A.copy_(torch.tensor([[1., 2., 0., -1.]]))
    layer.B.copy_(torch.tensor([[0.5], [0.], [-1.]]))
    merged = lin.weight + layer.delta()
    print(json.dumps({"W": lin.weight.tolist(), "A": layer.A.tolist(), "B": layer.B.tolist(), "scale": layer.scale,
                      "merged": merged.tolist(), "x": x[0].tolist(), "adapter": layer(x)[0].tolist(),
                      "Wx": lin(x)[0].tolist(), "Ax": (x @ layer.A.T)[0].tolist(), "mergedx": (x @ merged.T)[0].tolist(),
                      "start": start}))
"""


def merge1202():
    d = in_project("12.02", MERGE_CODE)
    need(d["adapter"] == d["mergedx"], f"the merge: {d['adapter']} {d['mergedx']}")
    need(d["start"] == 0, "a LoRA layer should start as its Linear layer exactly")
    out = lora_run().out
    m = re.search(r"class scores (\S+), from its scores for the next token (\S+)\.", out)
    scores, logits = m.group(1), m.group(2)
    m0 = re.search(r"not yet trained: the largest difference from GPT-2's own scores, on 8 questions, (\S+)\.", out)
    f = Fig("merge1202", "The merge as arithmetic, on a Linear layer of 4 inputs and 3 outputs with a LoRA of rank 1 "
                         "and alpha 2: W + (alpha / r) B A is one matrix, and it gives the adapter's outputs; in GPT-2, "
                         "trained 10 steps at rank 8, the same up to float32 rounding", 316)
    num = lambda v: f"{v:g}"  # noqa: E731
    W = [[num(v) for v in row] for row in d["W"]]
    y0 = 46
    figart.tensor(f, 20, y0, W, cell=(28, 22), label="W", shape=False)
    f.text(140, y0 + 38, "+", "t", 16, "middle", 700)
    f.text(160, y0 + 38, f"{d['scale']:g} x", "t", 12, "start", mono=True)
    figart.tensor(f, 192, y0, [[num(v)] for v in (r[0] for r in d["B"])], cell=(34, 22), label="B", here={(i, 0) for i in range(3)},
                  shape=False)
    f.text(236, y0 + 38, "x", "t", 12, "middle", mono=True)
    figart.tensor(f, 248, y0 + 22, [[num(v) for v in d["A"][0]]], cell=(28, 22), label="A", here={(0, j) for j in range(4)},
                  shape=False)
    f.text(372, y0 + 38, "=", "t", 16, "middle", 700)
    figart.tensor(f, 390, y0, [[num(v) for v in row] for row in d["merged"]], cell=(30, 22), label="W' (merged)",
                  here={(i, j) for i in range(3) for j in range(4) if d["merged"][i][j] != d["W"][i][j]}, shape=False)
    f.text(520, y0 + 14, "lit: what", "tm", 10)
    f.text(520, y0 + 28, "B A changed", "tm", 10)
    y = 150
    xs = ", ".join(num(v) for v in d["x"])
    f.text(20, y, f"x = [{xs}]", "t", 11.5, weight=700, mono=True)
    f.text(20, y + 24, f"the adapter:  W x + {d['scale']:g} B (A x)", "t", 11, mono=True)
    f.text(330, y + 24, f"= [{', '.join(num(v) for v in d['Wx'])}] + {d['scale']:g} B [{num(d['Ax'][0])}]", "tm", 11,
           mono=True)
    f.text(20, y + 46, "merged:       W' x", "ta", 11, weight=700, mono=True)
    f.text(330, y + 46, f"= [{', '.join(num(v) for v in d['mergedx'])}]", "ta", 11, weight=700, mono=True)
    f.text(330, y + 24 + 0, "", "tm", 11)
    f.text(20, y + 68, f"the adapter's output: [{', '.join(num(v) for v in d['adapter'])}], the same.", "tm", 10.5)
    f.text(20, 270, f"GPT-2, adapted at rank 8: before training the scores differ from GPT-2's by {m0.group(1)} (B is 0).",
           "t", 10.5)
    f.text(20, 288, f"Trained 10 steps, then merged: class scores differ by {scores}, next-token scores (up to a few "
                    f"hundred) by {logits}.", "t", 10.5)
    f.text(20, 304, "Rounding: float32 keeps about 7 digits, and the merged weight adds in another order.", "tm", 10.5)
    return f


def table1202():
    rec = recorded()
    full = [s["test_accuracy"] for s, _ in rec["full"]]
    f = Fig("table1202", "The recorded run (600 steps of 16 questions, 3 seeds, all of Banking77's test set): test "
                         "accuracy against the weights trained, on a log scale, a ring per seed, the bar their mean; "
                         "Welch's t against every weight trained", 330)
    ax = figart.Axes(f, 70, 34, 470, 230, (3e4, 4e8), (0.815, 0.91), logx=True)
    ax.draw(xticks=[1e5, 1e6, 1e7, 1e8], yticks=[0.82, 0.84, 0.86, 0.88, 0.9], xfmt=lambda v: f"{v:.0e}".replace("+0", ""),
            xlabel="weights trained (with the head's 59,213)", ylabel="test accuracy")
    for m in METHODS:
        accs = [s["test_accuracy"] for s, _ in rec[m]]
        n = rec[m][0][0]["trained"]
        style = "s" if m == "full" else ("m" if m == "head" else "a")
        X = ax.px(n)
        for v in accs:
            f.circle(X, ax.py(v), 3, f"{style} f")
        f.line(X - 9, ax.py(mean(accs)), X + 9, ax.py(mean(accs)), style)
        lines = [NAME[m], f"{mean(accs):.4f}"] + ([f"t {welch(accs, full):+.1f}"] if m != "full" else [])
        side, dx = ("end", -14) if m in ("lora4",) else ("start", 14)
        if m == "lora1":
            side, dx = "end", -14
        if m == "full":
            side, dx = "end", -14
        for k, s in enumerate(lines):
            f.text(X + dx, ax.py(mean(accs)) + 4 + (k - 1) * 13 + (26 if m == "lora1" else 0) - (30 if m == "lora4" else 0),
                   s, TEXT[style], 10, side, 600 if k == 0 else None, mono=k > 0)
    f.text(560, 60, "The head alone:", "tm", 10)
    f.text(560, 74, "the body frozen.", "tm", 10)
    f.text(560, 102, "LoRA: under 0.3%", "ta", 10)
    f.text(560, 116, "of the weights,", "ta", 10)
    f.text(560, 130, "within 1.1 to 1.4", "ta", 10)
    f.text(560, 144, "points of every", "ta", 10)
    f.text(560, 158, "weight trained.", "ta", 10)
    f.text(20, 322, "|t| of 3 or more: beyond the noise of 3 seeds. Every method's rate was chosen on validation.",
           "tm", 10.5)
    return f


def curves1202():
    rec = recorded()
    f = Fig("curves1202", "The recorded run on its 1,000 validation questions every 150 steps: each method's accuracy "
                          "(the mean of 3 seeds, the band min to max), and each LoRA rank's less every weight's, seed by "
                          "seed (the same seed: the same head, the same batches): ahead early, behind from step 450", 330)
    series = []
    for m, style, dash in (("head", "m", False), ("lora1", "a", "2 3"), ("lora4", "a", "6 3"), ("lora8", "a", False),
                           ("full", "s", False)):
        xs, mu, lo, hi = figart.over_seeds(figart.seed_dirs(os.path.join(REC, m)), "valid")
        series.append(figart.Series(NAME[m], xs, mu, style, dash, lo=lo if m in ("lora8", "full") else None,
                                    hi=hi if m in ("lora8", "full") else None))
    figart.plot(f, (8, 10, 318, 290), series, xlabel="step (16 questions each)", ylabel="validation accuracy",
                ylim=(0, 0.95), yticks=[0, 0.2, 0.4, 0.6, 0.8], legend=None, xticks=[0, 150, 300, 450, 600])
    figart.legend(f, 196, 168, [(NAME[m], st, da) for m, st, da in (("full", "s", False), ("lora8", "a", False),
                                                                     ("lora4", "a", "6 3"), ("lora1", "a", "2 3"),
                                                                     ("head", "m", False))], gap=15)
    ax = figart.Axes(f, 404, 32, 216, 220, (90, 660), (-0.045, 0.125))
    ax.draw(xticks=[150, 300, 450, 599], yticks=[-0.04, -0.02, 0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12],
            xlabel="step", ylabel="LoRA less every weight, by seed")
    ax.hline(0, None, "s", dash=False)
    full = {s: dict(zip(*figart.column(rows, "valid"))) for s, (_, rows) in enumerate(rec["full"])}
    means = {}
    for k, (m, dx) in enumerate((("lora1", -12), ("lora4", 0), ("lora8", 12))):
        for step in (150, 300, 450, 599):
            diffs = [dict(zip(*figart.column(rows, "valid")))[step] - full[s][step] for s, (_, rows) in enumerate(rec[m])]
            for v in diffs:
                f.circle(ax.px(step) + dx, ax.py(v), 2.2, "a f")
            means.setdefault(step, []).extend(diffs)
            f.line(ax.px(step) + dx - 4, ax.py(mean(diffs)), ax.px(step) + dx + 4, ax.py(mean(diffs)), "a")
    for step, v in means.items():
        top = max(v) if mean(v) > 0 else min(v)
        ax.note(step, top, f"{mean(v):+.3f}", "ta", 10, "middle", dy=-9 if mean(v) > 0 else 17, weight=600)
    f.text(ax.x + ax.w - 6, ax.y + 14, "above 0: LoRA ahead", "tm", 10, "end")
    f.text(404, 306, "at each step ranks 1, 4, 8 left to right;", "tm", 10)
    f.text(404, 320, "the number: all nine seeds' mean", "tm", 10)
    return f


MEM_CODE = """
import json, os, resource, time
import numpy as np, torch
import torch.nn.functional as F
from data import banking77
from experiments.tuning import pad
from models import gpt2 as M
from models.classifier import Classifier
from models.lora import adapt
from tokens import gpt2
mib = lambda: resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (2 ** 20 if os.uname().sysname == "Darwin" else 2 ** 10)
dev = torch.device("cpu")
tok = gpt2.load()
texts, labels = banking77.split("train")
seqs = [tok.encode(t) + [gpt2.END] for t in texts[:400]]
before = mib()
model = Classifier(M.load(dev), 77)
loaded = mib()
if METHOD == "lora":
    adapt(model.body, 8, 8)
opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-5)
rng = np.random.default_rng(1)
for i in range(6):
    at = rng.choice(len(seqs), 16)
    loss = F.cross_entropy(model(*pad([seqs[j] for j in at], gpt2.END, dev)), torch.from_numpy(labels[at]))
    opt.zero_grad()
    loss.backward()
    opt.step()
print(json.dumps({"before": before, "loaded": loaded, "peak": mib()}))
"""


def cost1202():
    out = lora_run().out
    keep = {m.group(1): (float(m.group(3).replace(",", "")), float(m.group(4).replace(",", "")))
            for m in re.finditer(r"^   (full|lora8) +\d+ ms a step; trains ([\d,]+) weights: their gradients and AdamW's "
                                 r"two averages are ([\d,.]+) MB\n +beside the ([\d,]+) MB", out, re.M)}
    need(set(keep) == {"full", "lora8"}, f"lora: part 3's memory lines {keep}")
    mem = {m: in_project("12.02", MEM_CODE.replace("METHOD", repr(m))) for m in ("full", "lora")}
    share = (mem["lora"]["peak"] - mem["lora"]["loaded"]) / (mem["full"]["peak"] - mem["full"]["loaded"])
    need(4000 < mem["full"]["peak"] < 4400 and 2150 < mem["lora"]["peak"] < 2450 and 0.34 < share < 0.39,
         f"the memory measured, {mem}, is not what 12.02's page says (about 4,200 and 2,300 MiB, 35 to 38%)")
    times, pair = step_times()
    f = Fig("cost1202", "What training costs, every weight against LoRA at rank 8: the numbers kept to train beside the "
                        "weights (computed), the process's peak memory over 6 steps of 16 questions (measured in a fresh "
                        "process each), and the recorded run's ms a step, each seed, as the machine's load rose", 330)
    # A: numbers kept
    f.text(14, 24, "kept to train, MB", "t", 11.5, weight=700)
    ax = figart.Axes(f, 60, 40, 150, 210, (-0.6, 1.6), (0, 2250))
    ax.draw(xticks=[], yticks=[0, 500, 1000, 1500, 2000])
    for i, (m, name, cls, tcls) in enumerate((("full", "every", "s", "t"), ("lora8", "LoRA", "a", "ta"))):
        g, w = keep[m]
        X = ax.px(i)
        f.rect(X - 20, ax.py(w), 40, ax.py(0) - ax.py(w), "m fs", 1)
        f.text(X, ax.py(w / 2) + 4, "W", "tm", 10, "middle", mono=True)
        f.rect(X - 20, ax.py(w + g), 40, max(ax.py(w) - ax.py(w + g), 1.5), f"{cls} {'fa' if cls == 'a' else 'fs'}", 1)
        f.text(X, ax.py(w + g) - 6, f"+{g:,.1f}", tcls, 10, "middle", 700, mono=True)
        f.text(X, ax.py(0) + 15, name, tcls, 10.5, "middle", 600)
    f.text(14, 284, "grey: the weights,", "tm", 10)
    f.text(14, 298, "about 500 MB; on top:", "tm", 10)
    f.text(14, 312, "gradients, AdamW's two", "tm", 10)
    f.text(14, 326, "averages (12 bytes each)", "tm", 10)
    # B: measured
    f.text(234, 24, "peak memory, MiB", "t", 11.5, weight=700)
    ax2 = figart.Axes(f, 278, 40, 130, 210, (-0.6, 1.6), (0, 4800))
    ax2.draw(xticks=[], yticks=[0, 1000, 2000, 3000, 4000])
    for i, (m, name, cls, tcls) in enumerate((("full", "every", "s", "t"), ("lora", "LoRA", "a", "ta"))):
        X = ax2.px(i)
        v = mem[m]
        f.rect(X - 18, ax2.py(v["loaded"]), 36, ax2.py(0) - ax2.py(v["loaded"]), "m fs", 1)
        f.rect(X - 18, ax2.py(v["peak"]), 36, ax2.py(v["loaded"]) - ax2.py(v["peak"]), f"{cls} {'fa' if cls == 'a' else 'fs'}",
               1)
        f.text(X, ax2.py(v["peak"]) - 6, f"{v['peak']:,.0f}", tcls, 10, "middle", 700, mono=True)
        f.text(X, ax2.py(0) + 15, name, tcls, 10.5, "middle", 600)
    added = {m: mem[m]["peak"] - mem[m]["loaded"] for m in mem}
    f.text(234, 284, f"grey: GPT-2 loaded, {mem['full']['loaded']:,.0f};", "tm", 10)
    f.text(234, 298, f"training adds {added['full']:,.0f} against", "tm", 10)
    f.text(234, 312, f"{added['lora']:,.0f}: LoRA's is {added['lora'] / added['full']:.0%}", "tm", 10)
    # C: time
    f.text(436, 24, "ms a step, recorded", "t", 11.5, weight=700)
    ax3 = figart.Axes(f, 476, 40, 150, 210, (-0.6, 3.6), (0, 800))
    ax3.draw(xticks=[], yticks=[0, 200, 400, 600, 800])
    for i, m in enumerate(("lora1", "lora4", "lora8", "full")):
        style = "s" if m == "full" else "a"
        X = ax3.px(i)
        for k, v in enumerate(times[m]):
            f.circle(X, ax3.py(v), 3, f"{style} f")
        f.text(X, ax3.py(0) + 15, {"lora1": "r1", "lora4": "r4", "lora8": "r8", "full": "all"}[m], TEXT[style], 10.5,
               "middle", 600, mono=True)
    f.text(436, 284, "each seed, as the load rose", "tm", 10)
    f.text(436, 298, "from 9 to 25. Back to back at", "tm", 10)
    f.text(436, 312, f"its start: r8 {pair['lora8']}, all {pair['full']} ms,", "tm", 10)
    f.text(436, 326, f"x{pair['lora8'] / pair['full']:.2f}. The head alone: 1 ms", "tm", 10)
    return f


# ------------------------------------------------------------------ 12.03

TEMPLATE_CODE = """
import json
from data import instructions as I
from tokens import gpt2
tok = gpt2.load()
prompt, reply = tok.encode(I.chat(PROMPT)), tok.encode(I.reply(ANSWER))
print(json.dumps({"prompt": [tok.decode([i]) for i in prompt], "reply": [tok.decode([i]) for i in reply],
                  "whole": tok.encode(I.chat(PROMPT) + I.reply(ANSWER)) == prompt + reply}))
"""


def template1203():
    out = ins_run().out
    m = re.search(r"An example in the template, (\d+) \+ (\d+) tokens.*\n\n      <\|user\|>\n      (.*)\n      "
                  r"<\|assistant\|>\n      (.*)\n      <\|end\|>", out)
    np_, nr, prompt, answer = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
    d = in_project("12.03", TEMPLATE_CODE.replace("PROMPT", repr(prompt)).replace("ANSWER", repr(answer)))
    need(len(d["prompt"]) == np_ and len(d["reply"]) == nr and d["whole"], "the template's tokens are not the run's")
    f = Fig("template1203", f"One example through the chat template, token by token in GPT-2's tokenizer: {np_} tokens "
                            f"of prompt, read and not scored, and {nr} of reply, each scored by the model's guess at "
                            f"the position before it; the markers are ordinary text to GPT-2", 246)
    toks = [(p, False) for p in d["prompt"]] + [(p, True) for p in d["reply"]]
    x, y, k = 20, 40, 0
    lines = []
    for p, mine in toks:
        s = shown(p).replace(" ", "_")
        w = max(tw(s, 10.5, True) + 10, 18)
        if x + w > 620:
            x, y = 20, y + 56
        cls, tcls = ("a af", "ta") if mine else ("s fs", "t")
        f.rect(x, y, w, 22, cls, 3)
        f.text(x + w / 2, y + 15, s, tcls, 10.5, "middle", 700 if mine else None, mono=True)
        f.text(x + w / 2, y + 36, str(k), "tm", 9, "middle", mono=True)
        if mine:
            f.path(f"M{x - 4:.1f} {y - 4} Q {x + w / 2 - 4:.1f} {y - 16} {x + w / 2:.1f} {y - 2}", "a", arrow=True)
        lines.append((x, y, w))
        x += w + 4
        k += 1
    f.text(20, 24, "_ is a space, \\n a line break", "tm", 10)
    yb = y + 64
    f.rect(20, yb - 11, 14, 14, "s fs", 3)
    f.text(40, yb, "the prompt: the user's marker, the question, the assistant's marker", "t", 10.5)
    f.rect(20, yb + 7, 14, 14, "a af", 3)
    f.text(40, yb + 18, "the reply: the answer, a line break, the end marker; the loss is the mean of -ln p of these "
                        f"{nr},", "ta", 10.5)
    f.text(40, yb + 34, "each guessed from every token before it (the arrows): answer_loss", "ta", 10.5)
    return f


SETS_CODE = """
import json
import lab
from data import instructions as I
from experiments.instruct import CONFIG, scored_sets
sets = scored_sets(lab.Config(CONFIG))
parts = I._parts()
print(json.dumps({"sets": sets, "cut": {k: [len(v[0]), len(v[1])] for k, v in parts.items()},
                  "words": len(I.words()), "ways": {t: I.TASKS[t][2] for t in I.TASKS}, "trained": I.TRAINED}))
"""


def held1203():
    d = in_project("12.03", SETS_CODE)
    out = ins_run().out
    need(f"Words: {d['words']:,} of Tiny Shakespeare's" in out, "the words' count is not the run's")
    f = Fig("held1203", "What is trained on and what is scored: five tasks in three wordings each, on four fifths of "
                        "the words and of the number tasks' instances; scored on instances never trained on, in the "
                        "trained wordings and in a fourth, and on a sixth task never trained", 350)
    f.text(20, 24, "trained: 5 tasks x 3 wordings x the training instances", "t", 11.5, weight=700)
    ways = d["ways"]["larger"]
    for k, w in enumerate(ways):
        cls = "ta" if k == len(ways) - 1 else "t"
        f.text(32, 46 + k * 16, w.format(a="a", b="b"), cls, 10.5, mono=True)
        f.text(330, 46 + k * 16, "held out" if k == len(ways) - 1 else "trained", cls, 10, weight=600)
    f.text(420, 46, "the cut, once (seed 0):", "t", 10.5, weight=700)
    for k, (kind, label) in enumerate((("word", "words"), ("pair", "pairs a, b"), ("digits", "triples of digits"))):
        tr, he = d["cut"][kind]
        f.text(420, 64 + k * 16, f"{label}: {tr:,} / {he:,}", "t", 10.5, mono=True)
    f.text(420, 64 + 3 * 16, "train / held out", "tm", 10)
    cols = [("held-out instances,", "trained wordings", "seen"), ("held-out instances,", "the held-out wording", "wording"),
            ("a task never", "trained: smaller", "task")]
    for c, (t1, t2, key) in enumerate(cols):
        x = 20 + c * 206
        f.rect(x, 128, 196, 196, "a af" if c else "s fs", 6)
        f.text(x + 10, 148, t1, "ta" if c else "t", 11, weight=700)
        f.text(x + 10, 162, t2, "ta" if c else "t", 11, weight=700)
        rows = d["sets"][key]
        picks = rows[::max(1, len(rows) // 5)][:5]
        for k, (task, prompt, answer) in enumerate(picks):
            y = 186 + k * 27
            f.text(x + 10, y, cut(prompt, 30), "t", 9.5, mono=True)
            f.text(x + 186, y + 12, "-> " + answer, "ta" if c else "t", 9.5, "end", 600, mono=True)
        f.text(x + 98, 340, f"{len(rows)} scored", "tm", 10, "middle")
    return f


ANSWERS_CODE = """
import json, torch
import lab
from data import instructions as I
from experiments.instruct import CONFIG, scored_sets
from experiments.tuning import answers
from models import gpt2 as M
from tokens import gpt2
cfg = lab.Config(CONFIG)
sets = scored_sets(cfg)
rows = [sets[name][i] for name in sets for i in range(0, len(sets[name]), max(1, len(sets[name]) // 2))][:cfg.shown]
tok = gpt2.load()
end = tok.encode("\\n" + I.END)
model = M.load(torch.device("cpu"))
drawn = answers(model, [tok.encode(I.chat(p)) for _, p, _ in rows], cfg.longest + len(end), end, torch.device("cpu"))
print(json.dumps({"rows": rows, "before": [tok.decode(x) for x in drawn]}))
"""


def answers1203():
    d = in_project("12.03", ANSWERS_CODE)
    out = ins_run().out
    after = re.findall(r"^      '(.*)' -> '(.*)'(?:   \(right: '(.*)'\))?$", out, re.M)
    need([p for p, _, _ in after] == [p for _, p, _ in d["rows"]], "the decoded prompts are not the run's")
    seed = re.search(r"Decoded on to the end marker \(seed (\d)\)", out).group(1)
    f = Fig("answers1203", f"The same six prompts, greedy, each written until it holds a line break and the end marker "
                           f"or 9 tokens: GPT-2 as it is, which goes on with the user's turn; and after 80 LoRA steps "
                           f"(seed {seed}), which answers in the template and stops", 340)
    f.text(20, 22, "prompt (in the template)", "t", 11, weight=700)
    f.text(258, 22, "GPT-2 as it is", "t", 11, weight=700)
    f.text(458, 22, "after tuning", "ta", 11, weight=700)
    for k, ((task, prompt, answer), before, (_, got, right)) in enumerate(zip(d["rows"], d["before"], after)):
        y = 46 + k * 46
        if k:
            f.line(20, y - 16, 620, y - 16, "m")
        f.text(20, y, cut(prompt, 36), "t", 10, mono=True)
        f.text(20, y + 15, f"{task}; right: {answer}", "tm", 9.5)
        f.text(258, y, cut(shown(before), 30), "tm", 10, mono=True)
        ok = not right
        f.text(458, y, cut(got, 24), "ta" if ok else "t", 10, weight=700 if ok else None, mono=True)
        f.text(458, y + 15, "right" if ok else "wrong", "ta" if ok else "tm", 9.5, weight=600 if ok else None)
    f.text(20, 330, "\\n is a line break. Only the first line is scored: the answer, against the right one, exactly.",
           "tm", 10.5)
    return f


def match1203():
    r = ins_run()
    d = in_project("12.03", SETS_CODE)
    out = r.out
    tasks = d["trained"]
    per, kinds = {t: [] for t in tasks}, {k: [] for k in ("seen", "wording", "task")}
    for s in summaries(r.runs):
        for k in kinds:
            got = [g == a for g, (_, _, a) in zip(s["answers"][k], d["sets"][k])]
            kinds[k].append(mean(got))
            need(abs(mean(got) - s[k]) < 1e-12, f"{k}: {mean(got)} {s[k]}")
        for t in tasks:
            per[t].append(mean([g == a for g, (task, _, a) in zip(s["answers"]["seen"], d["sets"]["seen"]) if task == t]))
    printed = re.search(r"By task, held-out instances, trained wordings: (.*)$", out, re.M).group(1)
    need(printed == ", ".join(f"{t} {mean(v):.2f}" for t, v in per.items()), f"by task: {printed}")
    before = [float(re.search(rf"^   {re.escape(w)} +([\d.]+)$", out, re.M).group(1))
              for w in ("held-out instances, trained wordings", "held-out instances, the held-out wording",
                        "a task never trained (smaller)")]
    f = Fig("match1203", "Exact match, 60 answers a set: GPT-2 as it is and after 80 steps of LoRA (a ring per seed, the "
                         "bar their mean), by kind of held-out; and by task, on held-out instances in the trained "
                         "wordings (12 a task)", 320)
    groups = [("instances", "seen"), ("wording", "wording"), ("task", "task")]
    ax = figart.Axes(f, 60, 40, 220, 220, (-0.5, 2.5), (0, 1))
    ax.draw(xticks=[], yticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0], ylabel="exact match")
    for i, (label, k) in enumerate(groups):
        X = ax.px(i)
        f.rect(X - 22, ax.py(before[i]) - 1, 14, 2, "s fs", 0, sw=False)
        f.circle(X - 15, ax.py(before[i]), 3, "s f")
        for v in kinds[k]:
            f.circle(X + 10, ax.py(v), 3, "a f")
        f.line(X + 2, ax.py(mean(kinds[k])), X + 18, ax.py(mean(kinds[k])), "a")
        f.text(X + 22, ax.py(mean(kinds[k])) + 4, f"{mean(kinds[k]):.3f}", "ta", 10, "start", 600, mono=True)
        f.text(X, ax.y + ax.h + 15, label, "t", 10.5, "middle")
    f.text(ax.x, ax.y + ax.h + 32, "held out: the instances, the wording,", "tm", 10)
    f.text(ax.x, ax.y + ax.h + 46, "or the task; grey GPT-2 (0), accent after", "tm", 10)
    ax2 = figart.Axes(f, 360, 40, 260, 220, (-0.5, 4.5), (0, 1))
    ax2.draw(xticks=[], yticks=[0, 0.2, 0.4, 0.6, 0.8, 1.0])
    for i, t in enumerate(tasks):
        X = ax2.px(i)
        for v in per[t]:
            f.circle(X, ax2.py(v), 3, "a f")
        m = mean(per[t])
        f.rect(X - 14, ax2.py(m), 28, ax2.py(0) - ax2.py(m), "a af", 1)
        f.text(X, ax2.py(m) - 7, f"{m:.2f}", "ta", 10, "middle", 600, mono=True)
        f.text(X, ax2.y + ax2.h + 15, t, "t", 10.5, "middle", mono=True)
    f.text(ax2.x, ax2.y + ax2.h + 32, "by task, after (the bar: the mean of 2 seeds)", "tm", 10)
    return f


# ------------------------------------------------------------------ 12.04

def bits1204():
    rec = recorded()
    out = fgt_run().out
    base = {k: mean([s[k] for s, _ in rec["head"]]) for k in ("shakespeare_bits", "stories_bits")}
    for m in METHODS:
        line = re.search(rf"^   {m} +([\d.]+) +([\d.]+) +([\d.]+) +(\S+) +\(3 seeds\)$", out, re.M)
        need(f"{mean([s['shakespeare_bits'] for s, _ in rec[m]]):.4f}" == line.group(2) and
             f"{mean([s['stories_bits'] for s, _ in rec[m]]):.4f}" == line.group(3), f"forgetting part 1, {m}")
    f = Fig("bits1204", f"What each fine-tune of 12.02's recorded run did to GPT-2 on text it was not tuned on: bits per "
                        f"character on Tiny Shakespeare's test text and bits per byte on 50 held-out TinyStories, less "
                        f"GPT-2's own ({base['shakespeare_bits']:.4f} and {base['stories_bits']:.4f}); a ring per seed, "
                        f"the bar their mean", 290)
    rows = ["lora1", "lora4", "lora8", "full"]
    for p, (key, title, lim, ticks) in enumerate((("shakespeare_bits", "Shakespeare's test text", (-0.08, 0.08),
                                                   [-0.08, -0.04, 0, 0.04, 0.08]),
                                                  ("stories_bits", "50 held-out TinyStories", (-0.01, 0.04),
                                                   [0, 0.02, 0.04]))):
        x0 = 120 + p * 262
        ax = figart.Axes(f, x0, 40, 220, 4 * 46, lim, (4, 0))
        ax.draw(xticks=ticks, yticks=[], xfmt=lambda v: f"{v:+.2f}" if v else "0", xlabel="less GPT-2's (worse ->)")
        f.text(x0, 28, title, "t", 11.5, weight=700)
        f.line(ax.px(0), ax.y, ax.px(0), ax.y + ax.h, "s")
        for i, m in enumerate(rows):
            y = ax.y + 23 + i * 46
            style = "s" if m == "full" else "a"
            if p == 0:
                f.text(x0 - 10, y + 4, NAME[m], TEXT[style], 11, "end", 600)
            vals = [s[key] - base[key] for s, _ in rec[m]]
            for v in vals:
                f.circle(ax.px(v), y, 3, f"{style} f")
            mu = mean(vals)
            f.line(ax.px(mu), y - 9, ax.px(mu), y + 9, style)
            f.text(ax.px(max(vals)) + 8, y + 4, f"{mu:+.3f}", TEXT[style], 10, "start", 600, mono=True)
    f.text(20, 280, "Right of the line: the fine-tuned model finds the text less likely than GPT-2 did.", "tm", 10.5)
    return f


def along1204():
    rec = recorded()
    out = fgt_run().out
    levels = [0.8, 0.85, 0.88]

    def at_accuracy(rows, level):
        for a, b in zip(rows, rows[1:]):
            if a["valid"] < level <= b["valid"]:
                t = (level - a["valid"]) / (b["valid"] - a["valid"])
                return a["untuned_bits"] + t * (b["untuned_bits"] - a["untuned_bits"])
        return rows[0]["untuned_bits"] if rows and rows[0]["valid"] >= level else None
    for m in METHODS:
        cells = []
        for level in levels:
            got = [b for b in (at_accuracy(rows, level) for _, rows in rec[m]) if b is not None]
            cells.append(f"{mean(got):8.4f} ({len(got)}/3)" if got else "never")
        line = re.search(rf"^   {m} +(.*?)   [\d.]+, [\d.]+$", out, re.M).group(1)
        need(" ".join(c.strip() for c in cells) == " ".join(line.split()), f"along, {m}: {cells} {line}")
    gpt2 = rec["head"][0][1][0]["untuned_bits"]
    f = Fig("along1204", f"Along the recorded run: at each evaluation (steps 0, 150, 300, 450, 599), validation accuracy "
                         f"against the bits per character on the first 2,048 tokens of Shakespeare's test text, the mean "
                         f"of 3 seeds; GPT-2 itself {gpt2:.4f} there", 330)
    ax = figart.Axes(f, 66, 36, 410, 230, (0, 0.92), (1.80, 1.86))
    ax.draw(xticks=[0, 0.2, 0.4, 0.6, 0.8], yticks=[1.80, 1.81, 1.82, 1.83, 1.84, 1.85, 1.86],
            xlabel="validation accuracy", ylabel="bits per character, untuned text")
    ax.hline(gpt2, None, "m", dash=True)
    ax.note(0.3, gpt2, f"GPT-2 itself, {gpt2:.4f}", "tm", 10, "middle", dy=14)
    for lv in levels:
        ax.vline(lv, None, "m", dash=True)
    for m, style, dash in (("lora1", "a", "2 3"), ("lora4", "a", "6 3"), ("lora8", "a", False), ("full", "s", False)):
        acc = [mean(v) for v in zip(*[[r["valid"] for r in rows] for _, rows in rec[m]])]
        bits = [mean(v) for v in zip(*[[r["untuned_bits"] for r in rows] for _, rows in rec[m]])]
        ax.curve(acc, bits, style, dash, 2)
        for x, y in zip(acc, bits):
            ax.dot(x, y, "a fa" if style == "a" else "s f", 2.5)
    figart.legend(f, 494, 60, [(NAME[m], st, da) for m, st, da in (("lora1", "a", "2 3"), ("lora4", "a", "6 3"),
                                                                    ("lora8", "a", False), ("full", "s", False))])
    f.text(494, 146, "dashed upright lines:", "tm", 10)
    f.text(494, 160, "0.80, 0.85, 0.88, where", "tm", 10)
    f.text(494, 174, "the run's part 2 reads", "tm", 10)
    f.text(494, 188, "each method's bits", "tm", 10)
    f.text(20, 316, "At the same accuracy every weight trained is near GPT-2's bits; LoRA is 0.02 to 0.03 above them.",
           "tm", 10.5)
    return f


def moved1204():
    rec = recorded()
    fg = fgt_run()
    base = {k: mean([s[k] for s, _ in rec["head"]]) for k in ("shakespeare_bits", "stories_bits")}
    before = float(re.search(r"GPT-2 before: exact match [\d.]+, Shakespeare ([\d.]+) bits", fg.out).group(1))
    ins = {m: summaries(os.path.join(fg.runs, m)) for m in ("lora", "full")}
    for m in ins:
        line = re.search(rf"^   {m} +.*\) +(\S+)$", fg.out, re.M).group(1)
        need(sig(mean([s["moved"] for s in ins[m]])) == line, f"moved, {m}: {line}")
    f = Fig("moved1204", "How far each fine-tune moved the weights (the length of the change over the length of the "
                         "weights) against what it did to the untuned bits: the classifier of 12.02 on Shakespeare and "
                         "on TinyStories, and 12.04's instruction model on the first 1,024 tokens of Shakespeare; a "
                         "point per seed", 332)
    panels = (("classifier, Shakespeare", "shakespeare_bits", (-0.08, 0.08)),
              ("classifier, TinyStories", "stories_bits", (-0.01, 0.04)),
              ("instructions, Shakespeare", None, (-0.13, 0.03)))
    for p, (title, key, lim) in enumerate(panels):
        x0 = 56 + p * 200
        ax = figart.Axes(f, x0, 36, 160, 200, (0, 0.016), lim)
        ax.draw(xticks=[0, 0.005, 0.01, 0.015], yticks=[v for v in (-0.12, -0.08, -0.04, 0, 0.02, 0.04, 0.08)
                                                        if lim[0] <= v <= lim[1]],
                xfmt=lambda v: f"{v:g}" if v else "0", xlabel="moved")
        f.text(x0, 24, title, "t", 11, weight=700)
        ax.hline(0, None, "s", dash=False)
        if key:
            for m in ("lora1", "lora4", "lora8", "full"):
                style = "s" if m == "full" else "a"
                for s, _ in rec[m]:
                    ax.dot(s["moved"], s[key] - base[key], f"{style} f", 3)
        else:
            for m in ("lora", "full"):
                style = "s" if m == "full" else "a"
                for s in ins[m]:
                    ax.dot(s["moved"], s["shakespeare"] - before, f"{style} f", 3)
    f.text(20, 290, "Above the line: less likely than GPT-2 found it. Accent: LoRA (every rank); foreground: every weight.",
           "tm", 10.5)
    f.text(20, 306, "LoRA moved the weights further in all three; it cost more bits on one text and fewer on another.",
           "tm", 10.5)
    f.text(20, 322, "The bits are differences from GPT-2's own on the same text.", "tm", 10.5)
    return f


def instruct1204():
    fg = fgt_run()
    out = fg.out
    m = re.search(r"GPT-2 before: exact match ([\d.]+), Shakespeare ([\d.]+) bits", out)
    ex0, bits0 = float(m.group(1)), float(m.group(2))
    ins = {k: summaries(os.path.join(fg.runs, k)) for k in ("lora", "full")}
    for k in ins:
        line = re.search(rf"^   {k} +(\S+) \+- .*?  +(\S+) \+- ", out, re.M)
        need(sig(mean([s["exact"] for s in ins[k]])) == line.group(1)
             and sig(mean([s["shakespeare"] for s in ins[k]]), 4) == line.group(2), f"instruct1204 {k}: {line.groups()}")
    t = welch([s["shakespeare"] for s in ins["lora"]], [s["shakespeare"] for s in ins["full"]])
    f = Fig("instruct1204", "12.04's instruction model: GPT-2 tuned 30 steps of 8 on the five tasks, with LoRA and with "
                            "every weight, 2 seeds each: exact match on 20 held-out instances, and bits per character on "
                            "the first 1,024 tokens of Shakespeare's test text, beside GPT-2 as it is", 290)
    ax = figart.Axes(f, 60, 40, 200, 190, (-0.5, 1.5), (0, 0.6))
    ax.draw(xticks=[], yticks=[0, 0.2, 0.4, 0.6], ylabel="exact match")
    ax.hline(ex0, f"GPT-2: {ex0:.1f}", "m", side="right")
    ax2 = figart.Axes(f, 380, 40, 220, 190, (-0.5, 1.5), (1.68, 1.84))
    ax2.draw(xticks=[], yticks=[1.68, 1.72, 1.76, 1.8, 1.84], ylabel="bits per character")
    ax2.hline(bits0, f"GPT-2: {bits0:.4f}", "m", side="right")
    for i, (k, name, style) in enumerate((("lora", "LoRA", "a"), ("full", "every weight", "s"))):
        for a, key in ((ax, "exact"), (ax2, "shakespeare")):
            vals = [s[key] for s in ins[k]]
            X = a.px(i)
            for v in vals:
                f.circle(X, a.py(v), 3, f"{style} f")
            f.line(X - 12, a.py(mean(vals)), X + 12, a.py(mean(vals)), style)
            f.text(X + 16, a.py(mean(vals)) + 4, f"{mean(vals):.3f}" if key == "exact" else f"{mean(vals):.4f}",
                   TEXT[style], 10, "start", 600, mono=True)
            f.text(X, a.y + a.h + 15, name, TEXT[style], 10.5, "middle", 600)
    f.text(380, 270, f"LoRA against every weight: t = {t:+.1f}", "t", 10.5)
    f.text(20, 270, "The same exact match; every weight trained made", "tm", 10.5)
    f.text(20, 284, "Shakespeare more likely, not less.", "tm", 10.5)
    return f


FIGS = [
    ("12.01-data", data1201),
    ("12.01-head", head1201),
    ("12.01-bag", bag1201),
    ("12.01-spread", spread1201),
    ("12.01-models", models1201),
    ("12.01-fewer", fewer1201),
    ("12.02-adapter", adapter1202),
    ("12.02-merge", merge1202),
    ("12.02-table", table1202),
    ("12.02-curves", curves1202),
    ("12.02-cost", cost1202),
    ("12.03-template", template1203),
    ("12.03-held", held1203),
    ("12.03-answers", answers1203),
    ("12.03-match", match1203),
    ("12.04-bits", bits1204),
    ("12.04-along", along1204),
    ("12.04-moved", moved1204),
    ("12.04-instruct", instruct1204),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
