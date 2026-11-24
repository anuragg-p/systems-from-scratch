"""Module 15's question, what is already known about it, and what was predicted before any run (15.01).

    QUESTION            the question, in one sentence, and where it came from
    BEFORE              08.03's numbers, which raised it
    RELATED             what others have published on it: who, where, what they found
    Prediction          key, says (the prediction in words), measure, rule
    PREDICTIONS         the predictions, each with the rule that will decide it
    SMALLEST            the smallest gap worth finding, in bits per character
    LEVEL, POWER        the intervals' level, and how often a gap of SMALLEST should come out clear of 0
    ARMS                the two arms: no positions, learned positions
    pair(...)           the two arms of one seed, sharing every weight they have in common
    trained(...)        one arm trained (08.01's loop) and scored, its numbers written to its run
    judge(rule, ...)    "held", "did not hold" or "not settled", by a prediction's rule
    budget(...)         the minutes a plan of runs will take, from the seconds runs took
    read_runs(dir)      the runs a script wrote, read back: settings and numbers of every seed
    pack(dir)           a recorded run's folders made into one file, runs.jsonl; unpack(dir, into) gives them back
    choose(found)       each arm's rate at each depth, from the search's validation bits    # @from 15.02
    gaps(bits, depths)  the gap at each depth, its paired interval and Welch's              # @from 15.02
    results(dir)        depth.py's runs read back: the search, the runs, the control        # @from 15.02

08.03 found that a GPT of one block without positions cannot tell one
order of its window from another, that from the second block on the
causal mask lets order in, and that at four blocks learned positions
were worth 0.065 bits per character. So: how much are they worth as
blocks are added, and how many blocks does a GPT without them need
before it matches one with them? This file holds what was written down
before anything ran: the question, the predictions and their rules, the
smallest gap worth finding. pilot.py (15.01) runs the pilot that fixes
the number of seeds; depth.py (15.02) runs the experiment; paper.py
(15.03) writes the paper from the logs. Our numbers come from the runs'
logs; the numbers here are other people's, each with where it was
published, and 08.03's.
"""

import json
import os
import shutil
from collections import namedtuple

import torch

import lab
from experiments.language import train
from experiments.sequences import window_bits
from models.gpt import GPT

QUESTION = ("How much are learned positions worth to a GPT as blocks are added, and how many blocks does a GPT "
            "without positions need before it matches one with them, at the size and budget of 08.03, on Tiny "
            "Shakespeare?")

# 08.03's run (experiments/positions.py, its page): 4 blocks of 4 heads, width 64, windows of 32, 300 steps of 32,
# AdamW at 0.003, 3 seeds; bits per character on the test text, each character with 16 or more before it.
BEFORE = dict(blocks=4, none=3.407, learned=3.342, gap=0.065, t=-8.4, seeds=3, lr=0.003,
              order_one_block=3.55e-15, order_four_blocks=2.44)

# What was found published, read at the source (the search and what each says: NOTES.md, module 15).
Related = namedtuple("Related", "key cite where found")
RELATED = [
    Related("irie", "Irie, Zeyer, Schlueter and Ney (2019), Language Modeling with Deep Transformers, Interspeech 2019, "
                    "arXiv 1905.04226",
            "section 7.1 and table 9",
            "word-level models of 12, 24 and 42 layers on LibriSpeech: without positions the perplexity is lower than "
            "with sinusoidal ones at every depth (development set 60.5 against 63.1 at 12 layers, 56.6 against 58.0 "
            "at 24, 54.2 against 55.0 at 42); 'the positional encoding is not needed for multi-layer autoregressive "
            "self-attention models'"),
    Related("haviv", "Haviv, Ram, Press, Izsak and Levy (2022), Transformer Language Models without Positional "
                     "Encodings Still Learn Positional Information, Findings of EMNLP 2022, arXiv 2203.16634",
            "table 2 and section 5",
            "on the Pile, 125 million to 1.3 billion weights (12 to 24 layers): no positions against learned, "
            "perplexity 22.15 against 22.04 at 125M and 13.10 against 13.05 at 1.3B, 'these performance gaps "
            "diminish as the models scale up'; a probe finds the model without positions has no position in its "
            "first layer and 'becomes position-aware within four layers'"),
    Related("kazemnejad", "Kazemnejad, Padhi, Natesan Ramamurthy, Das and Reddy (2023), The Impact of Positional "
                          "Encoding on Length Generalization in Transformers, NeurIPS 2023, arXiv 2305.19466",
            "theorem 1",
            "'the first layer of f_theta can recover absolute positions' (with a beginning-of-sequence token at the "
            "start of every input), so that later layers can use them; models without positions generalise to longer "
            "inputs better than with any explicit positions, on reasoning and arithmetic tasks"),
    Related("chi", "Chi, Fan, Chen, Rudnicky and Ramadge (2023), Latent Positional Information is in the "
                   "Self-Attention Variance of Transformer Language Models Without Positional Embeddings, ACL 2023, "
                   "arXiv 2305.13571",
            "the abstract",
            "a model without positions, even untrained, 'inherently encodes strong positional information through "
            "the shrinkage of self-attention variance': the average over more earlier positions varies less"),
    Related("zuo", "Zuo, Guerzhoy and Guerzhoy (2024), Position Information Emerges in Causal Transformers Without "
                   "Positional Encodings via Similarity of Nearby Embeddings, COLING 2025, arXiv 2501.00073",
            "the abstract",
            "'nearby embeddings are more similar to each other than faraway embeddings, allowing the transformer to "
            "potentially reconstruct the positions of tokens', in trained and untrained models"),
]

# The gap at a depth: a seed's test bits per character without positions minus the same seed's with learned
# positions (the pair shares its batches and every weight the two models have in common). Positive: positions help.
SMALLEST = 0.02          # the smallest gap worth finding: under a third of 08.03's 0.065
LEVEL = 0.95             # every interval is a 95% one
POWER = 0.8              # a true gap of SMALLEST comes out clear of 0 four times in five
ARMS = ("none", "learned")

Prediction = namedtuple("Prediction", "key says measure rule")

# Written on 2026-11-25 before the pilot or any run that scores a model, and committed so (git log has the time).
# Each rule fixes now what will count as held: by the means where it says so, else by the paired 95% interval.
PREDICTIONS = [
    Prediction("one_block", "Positions are worth the most to a GPT of one block, which cannot see order at all "
                            "without them.",
               "the mean gap at 1 block against the mean gap at every other depth",
               ("largest", 1)),
    Prediction("shrinks", "The gap shrinks as blocks are added: the mask gives a deeper model more of the order.",
               "the mean gap at each depth against the one before it",
               ("falls",)),
    Prediction("size_one", "At one block the gap is more than 0.1 bits per character.",
               "the gap at 1 block, its paired interval",
               ("above", 1, 0.1)),
    Prediction("again", "At four blocks, each arm with its own searched rate, the gap is about 08.03's 0.065.",
               "the mean gap at 4 blocks, within a factor of 2 of 0.065",
               ("about", 4, BEFORE["gap"], 2.0)),
    Prediction("not_closed", "No depth tried closes the gap: at the deepest, positions still help beyond the noise.",
               "the gap at the deepest depth, its paired interval",
               ("clear", "deepest")),
    Prediction("depth_no_substitute", "Twice the blocks do not buy what positions buy: no positions at 8 blocks is "
                                      "worse than learned positions at 4.",
               "test bits without positions at the deepest depth minus with them at 4, Welch's interval",
               ("worse", "deepest", 4)),
    Prediction("not_weights", "The positions' weights are not why they help: the same number of weights given to "
                              "the MLPs of a GPT without positions closes under a quarter of the gap.",
               "the share of the gap at 4 blocks the wider model without positions closes, by the means",
               ("closes_under", 4, 0.25)),
]


# @build 15.01 pair
# The two arms of one seed, for a fair pair: models/gpt.py's GPT of
# `layers` blocks (cfg's context, heads and width) without positions and
# with learned positions. Each is built after torch.manual_seed(seed), and
# then every weight the model without positions has is copied into the
# one with them, so the two start from the same weights everywhere but
# the table of positions, which only one has. The batches are paired by
# the seed too: both runs draw them from a Run's rng, which the seed
# makes. Returns {"none": model, "learned": model}, on the device dev.
def pair(V, cfg, layers, seed, dev):
    torch.manual_seed(seed)
    none = GPT(V, cfg.context, layers, cfg.heads, cfg.width, positions=False)
    torch.manual_seed(seed)
    learned = GPT(V, cfg.context, layers, cfg.heads, cfg.width, positions=True)
    missing, unexpected = learned.load_state_dict(none.state_dict(), strict=False)
    assert missing == ["positions.weight"] and not unexpected, (missing, unexpected)
    return {"none": none.to(dev), "learned": learned.to(dev)}
# @end


# @build 15.01 trained
# One arm, one run: model trained by 08.01's loop (experiments/language.py's
# train) on the training text, then scored as 08.03 scores, bits per
# character with each character read with context / 2 or more before it,
# on the validation text, and on the test text only when test is True. A
# choice is made on validation; the test text is read only by runs whose
# settings are already fixed. The numbers go to the run's summary.json
# (with the model's weights counted) and are returned as a dict.
def trained(model, cfg, run, dev, texts, test=False):
    train(model, cfg, run, dev, texts["train"])
    model.eval()
    warm = cfg.context // 2
    out = {"val_bits": window_bits(model, texts["val"], cfg.context - warm + 1, warm)}
    if test:
        out["test_bits"] = window_bits(model, texts["test"], cfg.context - warm + 1, warm)
    return run.finish(weights=sum(p.numel() for p in model.parameters()), **out)
# @end


def deepest(gaps):
    return max(gaps)


# @build 15.01 judge
# A prediction's rule applied to the results: gaps {depth: [the gap of
# each seed]}, bits {(depth, arm): [test bits of each seed]}, control
# {depth: [test bits of the wider model without positions, each seed]}.
# A depth may be "deepest". Returns (verdict, our number):
#   ("largest", d)       held if the mean gap at d is above the mean at every other depth
#   ("falls",)           held if the mean gap is lower at each depth than at the one before
#   ("above", d, x)      the gap's paired interval at d: held if all of it is above x, did not
#                        hold if all of it is below, else not settled
#   ("clear", d)         held if the gap's paired interval at d is all above 0; else it did
#                        not hold: the gap there is inside the noise (or reversed)
#   ("about", d, x, f)   held if the mean gap at d is within a factor f of x
#   ("worse", d, e)      bits without positions at d minus with them at e, Welch's interval:
#                        held if above 0, did not hold if below, else not settled
#   ("closes_under", d, s)  the share of the mean gap at d that the wider model without
#                        positions closes: held if under s
def judge(rule, gaps, bits, control, level=LEVEL):
    kind, args = rule[0], [deepest(gaps) if a == "deepest" else a for a in rule[1:]]
    means = {d: lab.mean(g) for d, g in gaps.items()}
    if kind == "largest":
        d, = args
        return ("held" if all(means[d] > m for e, m in means.items() if e != d) else "did not hold"), means[d]
    if kind == "falls":
        order = [means[d] for d in sorted(means)]
        return ("held" if all(a > b for a, b in zip(order, order[1:])) else "did not hold"), order
    if kind == "above":
        d, x = args
        lo, hi = lab.interval(gaps[d], level)
        return ("held" if lo > x else "did not hold" if hi < x else "not settled"), (means[d], lo, hi)
    if kind == "clear":
        d, = args
        lo, hi = lab.interval(gaps[d], level)
        return ("held" if lo > 0 else "did not hold"), (means[d], lo, hi)
    if kind == "about":
        d, x, f = args
        return ("held" if x / f <= means[d] <= x * f else "did not hold"), means[d]
    if kind == "worse":
        d, e = args
        diff, lo, hi = lab.difference(bits[d, "none"], bits[e, "learned"], level=level)
        return ("held" if lo > 0 else "did not hold" if hi < 0 else "not settled"), (diff, lo, hi)
    if kind == "closes_under":
        d, s = args
        share = (lab.mean(bits[d, "none"]) - lab.mean(control[d])) / means[d]
        return ("held" if share < s else "did not hold"), share
    raise ValueError(f"no rule {kind!r}")
# @end


# @build 15.01 budget
# The minutes a plan takes: `runs` runs of each arm at each of `depths`,
# a run at depth d taking seconds[d] where it was measured, and elsewhere
# the straight line through the measured depths (least squares, so two
# measured depths or more), since a block adds the same work to a step.
# Returns (minutes, {depth: seconds a run}).
def budget(seconds, depths, runs, arms=len(ARMS)):
    xs, ys = list(seconds), [seconds[d] for d in seconds]
    mx, my = lab.mean(xs), lab.mean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    per = {d: seconds[d] if d in seconds else my + slope * (d - mx) for d in depths}
    return sum(per[d] * arms * runs for d in depths) / 60, per
# @end


# @build 15.01 read_runs
# Every run a script wrote under directory, read back from the files 00.02's
# Run leaves: {label: [(settings, summary) of each seed, in seed order]},
# the settings from config.json (every setting the run used, its seed among
# them) and the numbers from summary.json. A recorded run may be packed
# (pack): its files are read from runs.jsonl instead, the same text.
def read_runs(directory):
    out = {}
    for label, seed, files in runs_in(directory):
        out.setdefault(label, []).append((json.loads(files["config.json"]), json.loads(files["summary.json"])))
    return out
# @end


PACKED = "runs.jsonl"
RUN_FILES = ("config.json", "log.jsonl", "summary.json")


def runs_in(directory):
    """Every run under directory as (label, seed, {file name: its text}), by label and then seed: from the folders
    00.02's Run writes (label/seed<k>/...), or from a pack of them (runs.jsonl)."""
    packed = os.path.join(directory, PACKED)
    if os.path.isfile(packed):
        with open(packed) as f:
            return [(r["label"], r["seed"], r["files"]) for r in map(json.loads, f) if r]
    out = []
    for label in sorted(os.listdir(directory)):
        d = os.path.join(directory, label)
        if not os.path.isdir(d):
            continue
        for seed in sorted(int(s[4:]) for s in os.listdir(d) if s.startswith("seed")):
            files = {}
            for name in RUN_FILES:
                with open(os.path.join(d, f"seed{seed}", name)) as f:
                    files[name] = f.read()
            out.append((label, seed, files))
    return out


# @build 15.01 pack
# A recorded run made into one file: every run folder under directory
# (label/seed<k>/ with config.json, log.jsonl and summary.json), in order
# of label and seed, written as one line of runs.jsonl, {"label", "seed",
# "files": each file's text, verbatim}; checked by reading it back, then
# the folders removed. A record of hundreds of runs is then one file, and
# nothing in it is lost: unpack writes the folders again, byte for byte.
def pack(directory):
    runs = runs_in(directory)
    with open(os.path.join(directory, PACKED), "w") as f:
        for label, seed, files in runs:
            f.write(json.dumps({"label": label, "seed": seed, "files": files}) + "\n")
    assert runs_in(directory) == runs
    for label in {label for label, _, _ in runs}:
        shutil.rmtree(os.path.join(directory, label))
    return len(runs)
# @end


def unpack(directory, into):
    """A packed record's run folders written again under into, byte for byte as the runs wrote them."""
    for label, seed, files in runs_in(directory):
        os.makedirs(os.path.join(into, label, f"seed{seed}"), exist_ok=True)
        for name, text in files.items():
            with open(os.path.join(into, label, f"seed{seed}", name), "w") as f:
                f.write(text)


# @build 15.02 choose
# Each arm's rate at each depth: the one whose run scored the lowest
# validation bits in the search, found {(depth, arm): {rate: validation
# bits}}. Nothing else is read, so the test text cannot move a choice.
# Returns {(depth, arm): rate}.
def choose(found):
    return {key: min(scores, key=scores.get) for key, scores in found.items()}
# @end


# @build 15.02 gaps
# The comparison at each depth, from bits {(depth, arm): [bits of each
# seed]} of paired runs: the gap of each seed (none minus learned), its
# mean, the paired interval (13.02's difference with paired=True) and
# Welch's (the same runs taken as two independent sets), and on how many
# seeds learned positions were lower. Returns {depth: (gaps, mean,
# (low, high) paired, (low, high) Welch, lower)}.
def gaps(bits, depths, level=LEVEL):
    out = {}
    for d in depths:
        none, learned = bits[d, "none"], bits[d, "learned"]
        each = [a - b for a, b in zip(none, learned, strict=True)]
        mean, plo, phi = lab.difference(none, learned, paired=True, level=level)
        _, wlo, whi = lab.difference(none, learned, level=level)
        out[d] = (each, mean, (plo, phi), (wlo, whi), sum(g > 0 for g in each))
    return out
# @end


# @from 15.02
def results(directory):
    """depth.py's runs read back by their labels: the search {(depth, arm): {rate: validation bits}}, the runs
    {(depth, arm): [summary of each seed, with its rate and seed]}, the control {depth: [the same]}, and the settings
    of one run (the first of the runs)."""
    found, runs, control, cfg = {}, {}, {}, None
    for label, seeds in read_runs(directory).items():
        parts = label.split("-")
        for settings, summary in seeds:
            row = dict(summary, lr=settings["lr"], seed=settings["seed"])
            if parts[0] == "search":
                found.setdefault((int(parts[1][6:]), parts[2]), {})[settings["lr"]] = summary["val_bits"]
            elif parts[0] == "control":
                control.setdefault(int(parts[1][6:]), []).append(row)
            else:
                runs.setdefault((int(parts[0][6:]), parts[1]), []).append(row)
                cfg = cfg or lab.Config(settings)
    return found, runs, control, cfg
# @end


def rule_text(rule):
    """A rule in words, for a table."""
    kind = rule[0]
    args = ["the deepest" if a == "deepest" else (f"{a} block{'s' * (a != 1)}" if isinstance(a, int) else a)
            for a in rule[1:]]
    return {"largest": lambda d: f"held if the mean gap at {d} is the largest",
            "falls": lambda: "held if the mean gap falls at every step of depth",
            "above": lambda d, x: f"held if the gap's interval at {d} is all above {x:g}",
            "clear": lambda d: f"held if the gap's interval at {d} is all above 0",
            "about": lambda d, x, f: f"held if the mean gap at {d} is within {x / f:.3g} to {x * f:.3g}",
            "worse": lambda d, e: f"held if Welch's interval (none at {d}, learned at {e}) is above 0",
            "closes_under": lambda d, s: f"held if it closes under {s:.0%} of the gap at {d}"}[kind](*args)
