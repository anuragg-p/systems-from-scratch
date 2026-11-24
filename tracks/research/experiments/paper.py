"""The paper: module 15's result written up from its logs (15.03).

Every number in the paper is read from the recorded runs' files, the
pilot's (experiments/recorded/pilot) and the experiment's
(experiments/recorded/depth): config.json for the settings, summary.json
for the scores, output.txt for the times, and the text's own bytes for its
hash. The question, the predictions and their rules, the smallest gap worth
finding, 08.03's numbers and what others published come from
experiments/question.py, where each was written before the runs, with
where it came from. The words around the numbers are fixed; which words
are used depends on the numbers.

The sections, in the order a reader needs them: the abstract in four
sentences; the problem, shown on an example; what the paper shows, each
point a claim its evidence could refute, with the section that holds the
evidence; the method, in enough detail to run it again; the result, with
its intervals; each prediction beside its outcome; what was not expected;
what others found, after the idea; the limits; the commands that make
every number again.

The paper is printed and written to <out>/paper/paper.txt.

    python3 -m experiments.paper
"""

import ast
import hashlib
import os
import re
import textwrap

import lab
from experiments import question as q

CONFIG = dict(pilot="experiments/recorded/pilot", depth="experiments/recorded/depth", width=100)

TITLE = "What learned positions are worth to a small GPT, block by block"
# Keys a run's config.json holds that are not settings to give again: what the runner adds, where it ran.
NOT_SETTINGS = {"name", "label", "seed"}
TEXT = "data/tinyshakespeare.txt"


# @build 15.03 defaults
# The settings an experiment declares and their defaults: its CONFIG =
# dict(key=value, ...) at the top of experiments/<name>.py, read from the
# source with Python's own parser (ast.parse; each value by
# ast.literal_eval), not imported: an experiment never imports another.
# root is the project's folder.
def defaults(name, root="."):
    with open(os.path.join(root, "experiments", f"{name}.py")) as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "CONFIG" for t in node.targets):
            return {kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords}
    raise ValueError(f"experiments/{name}.py declares no CONFIG")
# @end


# @build 15.03 command
# The command that makes a recorded run again, from its config.json
# (settings): python3 -m experiments.<name>, then every setting the script
# declares whose recorded value is not its default, as key=value (a list
# quoted, so that no shell reads its brackets), then out=, where it was
# written. What the runner added (the seed, the label) and what the script
# set itself (depth.py's rate for each model) are not settings: the script
# makes them again.
def command(settings, root="."):
    declared = defaults(settings["name"], root)
    words = ["python3", "-m", f"experiments.{settings['name']}"]
    for key, default in declared.items():
        value = settings.get(key, default)
        if key in NOT_SETTINGS or value == default:
            continue
        text = repr(value).replace(" ", "")
        words.append(f'"{key}={text}"' if isinstance(value, list) else f"{key}={text}")
    return " ".join(words + [f"out={settings['out']}"])
# @end


def gather(pilot_dir, depth_dir):
    """Everything the paper says, read from the two recorded folders: r, a dict."""
    r = {}
    found, runs, control, cfg = q.results(depth_dir)
    r.update(found=found, runs=runs, control=control, cfg=cfg, chosen=q.choose(found))
    r["depths"] = sorted({d for d, _ in runs})
    r["test"] = {k: [s["test_bits"] for s in v] for k, v in runs.items()}
    r["val"] = {k: [s["val_bits"] for s in v] for k, v in runs.items()}
    r["gaps"], r["val_gaps"] = q.gaps(r["test"], r["depths"]), q.gaps(r["val"], r["depths"])
    r["control_bits"] = {d: [s["test_bits"] for s in rows] for d, rows in control.items()}
    r["weights"] = {k: v[0]["weights"] for k, v in runs.items()}
    r["control_weights"] = {d: rows[0]["weights"] for d, rows in control.items()}
    r["seeds"] = sorted(s["seed"] for s in runs[r["depths"][0], "none"])
    r["verdicts"] = {}
    for p in q.PREDICTIONS:
        try:
            r["verdicts"][p.key] = q.judge(p.rule, {d: g[0] for d, g in r["gaps"].items()}, r["test"],
                                           r["control_bits"])
        except (KeyError, ZeroDivisionError):
            r["verdicts"][p.key] = ("not run", None)
    pilot = q.read_runs(pilot_dir)
    r["pilot_cfg"] = lab.Config(next(iter(pilot.values()))[0][0])
    r["pilot"] = {(int(label[6:].split("-")[0]), label.split("-")[1]): [s["val_bits"] for _, s in seeds]
                  for label, seeds in pilot.items()}
    r["pilot_sd"] = {d: lab.sd([a - b for a, b in zip(r["pilot"][d, "none"], r["pilot"][d, "learned"])])
                     for d in r["pilot_cfg"].depths}
    r["needed"] = max(3, lab.seeds_needed(q.SMALLEST, max(r["pilot_sd"].values()), q.LEVEL, q.POWER, paired=True))
    r["settings"] = {"pilot": next(iter(pilot.values()))[0][0],
                     "depth": next(c for label, seeds in q.read_runs(depth_dir).items()
                                   if not label.startswith(("search", "control")) for c, _ in seeds)}
    r["seconds"] = {name: seconds(os.path.join(d, "output.txt")) for name, d in (("pilot", pilot_dir),
                                                                                  ("depth", depth_dir))}
    with open(TEXT, "rb") as f:
        data = f.read()
    r["text"] = (len(data), hashlib.sha256(data).hexdigest())
    return r


def seconds(path):
    """The seconds a recorded run took, from the last line it printed (its output.txt), or None."""
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        found = re.findall(r"^(\d+) s of training and scoring", f.read(), re.M)
    return int(found[-1]) if found else None


def blocks(d):
    return f"{d} block{'s' * (d != 1)}"


def took(s):
    return "a time not recorded" if s is None else f"{s} s ({s / 60:.0f} minutes)"


def gap_text(r, d):
    """A depth's mean gap and its paired interval, as the paper prints it."""
    _, mean, (lo, hi), _, _ = r["gaps"][d]
    return f"{mean:.3f} bits ({lo:.3f} to {hi:.3f})"


def first_inside(r):
    """The first depth whose gap's paired interval reaches 0, or None."""
    return next((d for d in r["depths"] if r["gaps"][d][2][0] <= 0), None)


# @build 15.03 abstract
# The abstract in four sentences, as Peyton Jones's structure has it: the
# problem, what was done, what was found with its interval, and what
# follows. Every number from r, the results read back; the words that
# depend on a number (whether the gap closed, and where) are chosen by it.
def abstract(r):
    d0, d1 = r["depths"][0], r["depths"][-1]
    shut = first_inside(r)
    closes = (f"its interval reaches 0 from {blocks(shut)} on" if shut else
              "at every depth tried its interval stays above 0")
    deep, four = lab.mean(r["test"][d1, "none"]), lab.mean(r["test"][4, "learned"])
    return [f"Without position embeddings a GPT of one block cannot tell one order of its window from another, and "
            f"from the second block on its causal mask lets order in; at {q.BEFORE['blocks']} blocks learned "
            f"positions were worth {q.BEFORE['gap']} bits per character in an earlier run.",
            f"We measure what they are worth at {', '.join(map(str, r['depths'][:-1]))} and {d1} blocks of a "
            f"character-level GPT {r['cfg'].width} wide on Tiny Shakespeare, each model's learning rate chosen by "
            f"the same search on held-out text, each depth on {len(r['seeds'])} pairs of runs that share their "
            f"batches and starting weights, a number fixed by a pilot before the experiment ran.",
            f"The gap falls from {gap_text(r, d0)} at one block to {gap_text(r, d1)} at {d1} (95% intervals), and "
            f"{closes}.",
            f"Without positions {d1} blocks score {deep:.3f} bits against {four:.3f} for 4 blocks with them, and "
            f"the weights positions add, given to the model without them, close "
            f"{r['verdicts']['not_weights'][1]:.0%} of the gap at 4 blocks."]
# @end


# @build 15.03 verdicts
# Each prediction of question.py beside its outcome: its words, the rule
# written before any run, our number (judge's, in r["verdicts"]) and what
# it is a number of, and the verdict. Lines of text.
def verdicts(r):
    out = []
    for p in q.PREDICTIONS:
        v, ours = r["verdicts"][p.key]
        if isinstance(ours, (list, tuple)):
            ours = ", ".join(f"{x:.3f}" for x in ours)
        elif isinstance(ours, float):
            ours = f"{ours:.3f}"
        out += [f"{p.key}: {p.says}", f"   rule: {q.rule_text(p.rule)}", f"   ours: {ours} ({p.measure})",
                f"   {v}", ""]
    return out
# @end


def para(text, width, indent=""):
    return textwrap.fill(text, width, initial_indent=indent, subsequent_indent=" " * len(indent))


def paper(r, cfg):
    """The paper, as lines of text, wrapped to cfg.width columns."""
    w, c, pc = cfg.width, r["cfg"], r["pilot_cfg"]
    d0, d1 = r["depths"][0], r["depths"][-1]
    out = [TITLE, "", para(f"Written by experiments/paper.py from the logs of {cfg.pilot} and {cfg.depth}: runs on "
                           f"one laptop's CPU.", w), ""]
    out += ["Abstract", "", para(" ".join(abstract(r)), w), ""]

    out += ["1. The problem", "", para(
        f"Take 32 characters of Shakespeare and a GPT of one block without position embeddings, and put the 31 "
        f"characters before the last in another order. Its scores for the next character do not move: in the "
        f"earlier run the largest change over five orders was {q.BEFORE['order_one_block']:.3g}, rounding. With "
        f"four blocks they moved by up to {q.BEFORE['order_four_blocks']}. In one block the last position weighs "
        f"a set of characters, and a weighted sum does not care in what order its terms come; from the second "
        f"block on, each position reads what the first block saw at the positions up to it, and the causal mask "
        f"made those views differ. So a GPT without positions sees some of the order, and at four blocks learned "
        f"positions were worth only {q.BEFORE['gap']} bits per character ({q.BEFORE['none']} against "
        f"{q.BEFORE['learned']}, {q.BEFORE['seeds']} seeds). How much are they worth as blocks are added, and how "
        f"many blocks does a GPT without them need to match one with them?", w), ""]

    shut = first_inside(r)
    closes = (f"from {blocks(shut)} on its 95% interval reaches 0" if shut else
              f"at no depth tried does its 95% interval reach 0")
    out += ["2. What this paper shows", ""]
    for line in [
        f"The gap at {', '.join(map(str, r['depths']))} blocks, each on {len(r['seeds'])} pairs of runs, each "
        f"model's rate searched alike (section 4): {gap_text(r, d0)} at one block, {gap_text(r, d1)} at {d1}; "
        f"{closes}.",
        f"Blocks against positions: without positions {d1} blocks score {lab.mean(r['test'][d1, 'none']):.3f} bits, "
        f"with them 4 blocks {lab.mean(r['test'][4, 'learned']):.3f} (section 4).",
        f"Not the weights: the {r['weights'][4, 'learned'] - r['weights'][4, 'none']} weights positions add at 4 "
        f"blocks, put into the MLPs of the model without them instead, close "
        f"{r['verdicts']['not_weights'][1]:.0%} of the gap (section 4).",
        "Seven predictions written before any run, and which held (section 5)."]:
        out.append(para(line, w, "- "))
    out.append("")

    extra = r["control_weights"][4] - r["weights"][4, "none"]
    out += ["3. Method", ""]
    for line in [
        f"Model. The GPT of the track's module 08: pre-norm blocks of attention and an MLP, GELU, a last layer norm, "
        f"the output tied to the embeddings, GPT-2's start (every weight drawn with sd 0.02); width {c.width}, "
        f"{c.heads} heads, windows of {c.context} characters, 1 to {d1} blocks. With learned positions it has a "
        f"table of {c.context} x {c.width} = {c.context * c.width} more weights, added to the embeddings.",
        f"Data. Tiny Shakespeare, {r['text'][0]:,} bytes, one byte a character: the first 90% to train on, the next "
        f"5% to choose on (validation), the last 5% to report on (test), split by position. Scores are bits per "
        f"character, each character read with {c.context // 2} or more before it.",
        f"Training. AdamW, weight decay {c.weight_decay} on the matrices and embeddings, the rate warmed up over "
        f"{c.warmup} steps then a cosine to 0, the gradient clipped to {c.clip}; {c.steps} steps of {c.batch} "
        f"windows.",
        f"Search. At every depth both models ran at each of the rates {', '.join(f'{x:g}' for x in c.rates)} on "
        f"seed 0, and each kept the rate with the lowest validation bits.",
        f"Pairs. Seeds 1 to {len(r['seeds'])} at the rates chosen: one seed gives both models the same batches and "
        f"the same start for every weight they share; only the table of positions is not shared.",
        f"Seeds. A pilot before the experiment ran {pc.seeds} pairs at {' and '.join(map(blocks, pc.depths))}, rate "
        f"{pc.lr:g}, scored on validation only. Its largest standard deviation of a depth's gaps, "
        f"{max(r['pilot_sd'].values()):.4f}, and the smallest gap worth finding, {q.SMALLEST} bits, ask for "
        f"{r['needed']} pairs for a true gap of that size to come out clear of 0 four times in five.",
        f"Control. At 4 blocks the model without positions again, with every MLP {extra // (4 * (2 * c.width + 1))} "
        f"hidden units wider ({extra} weights, as many as positions add, within a few), at the rate chosen for the "
        f"model without positions, on the same seeds.",
        f"Statistics. Each pair's gap, no positions minus learned; the mean with a {q.LEVEL:.0%} paired t interval, "
        f"and Welch's interval on the same runs beside it.",
        f"Cost. The pilot took {took(r['seconds']['pilot'])} and the experiment {took(r['seconds']['depth'])} on "
        f"one laptop's CPU, with other work running."]:
        out += [para(line, w), ""]

    out += ["4. Results", "", para(
        f"Bits per character on the test text, the mean over {len(r['seeds'])} seeds; the gap is no positions minus "
        f"learned, pair by pair, with its {q.LEVEL:.0%} interval as pairs and by Welch's; 'lower' counts the pairs "
        f"in which positions helped; the last column is the gap on the validation text.", w), ""]
    out.append(f"{'blocks':>6s}  {'none':>6s}  {'learned':>7s}  {'gap':>6s}  {'paired':>16s}  {'Welch':>16s}"
               f"  {'lower':>6s}  {'validation':>10s}")
    for d in r["depths"]:
        each, mean, (plo, phi), (wlo, whi), lower = r["gaps"][d]
        out.append(f"{d:6d}  {lab.mean(r['test'][d, 'none']):6.3f}  {lab.mean(r['test'][d, 'learned']):7.3f}  "
                   f"{mean:6.3f}  {plo:6.3f} to {phi:6.3f}  {wlo:6.3f} to {whi:6.3f}  {f'{lower}/{len(each)}':>6s}  "
                   f"{r['val_gaps'][d][1]:10.3f}")
    out.append("")
    out += [para("The rates chosen (no positions, learned): " + "; ".join(
        f"{blocks(d)} {r['chosen'][d, 'none']:g}, {r['chosen'][d, 'learned']:g}" for d in r["depths"]) + ".", w), ""]
    for d, bits in r["control_bits"].items():
        diff, lo, hi = lab.difference(bits, r["test"][d, "learned"], paired=True)
        out += [para(f"The control at {blocks(d)}: {lab.mean(bits):.3f} bits, against "
                     f"{lab.mean(r['test'][d, 'none']):.3f} without the extra weights and "
                     f"{lab.mean(r['test'][d, 'learned']):.3f} with positions; its gap to positions {diff:.3f} "
                     f"({lo:.3f} to {hi:.3f}).", w), ""]
    out += [para(f"Figures: {cfg.depth}/bits.svg, each model's bits against blocks; {cfg.depth}/gap.svg, the gap "
                 f"with both intervals.", w), ""]

    out += ["5. The predictions, written before any run", ""] + verdicts(r)

    out += ["6. What was not expected", ""]
    missed = [p for p in q.PREDICTIONS if r["verdicts"][p.key][0] != "held"]
    if not missed:
        out += [para("Every prediction held by its rule.", w), ""]
    for p in missed:
        out += [para(f"{p.key} ({r['verdicts'][p.key][0]}): {p.says}", w, "- ")]
    out += [""] + [para(line, w) + "\n" for line in surprises(r)]

    out += ["7. What others found", ""]
    for rel in q.RELATED:
        out += [para(f"{rel.cite} ({rel.where}): {rel.found}.", w, "- ")]
    out += ["", para(
        f"Not found in that search: the gap block by block from one block up, in a small model, at a fixed budget. "
        f"The search was a few queries of the web and arXiv and the papers they led to, not a survey.", w), ""]

    out += ["8. Limits", ""]
    for line in [
        f"One size ({c.width} wide, {c.heads} heads, windows of {c.context}), one text, one budget ({c.steps} steps): "
        f"a model trained longer, or wider, or on another text may give another curve.",
        f"Each rate was chosen on one seed; a rate that was lucky on seed 0 runs on every later seed.",
        f"The windows start at random places in the text and have no token that marks a start, which the proof of "
        f"Kazemnejad et al. uses.",
        "The runs record their settings and seeds, not the machine or the library's version; the last digits can "
        "differ on another machine."]:
        out.append(para(line, w, "- "))
    out.append("")

    out += ["9. To make every number again", ""]
    out += [para(f"The text: {TEXT}, {r['text'][0]:,} bytes, SHA-256 {r['text'][1]}. From the project's top:", w), ""]
    out += ["   " + command(r["settings"]["pilot"]), "   " + command(r["settings"]["depth"]),
            "   python3 -m experiments.paper", ""]
    out.append(para("Each run's config.json holds every setting it used and its seed; the commands above are made "
                    "from them.", w))
    return out


def surprises(r):
    """What the numbers say that no prediction asked about: words chosen by the numbers, every number from r."""
    out = []
    gaps = {d: r["gaps"][d][1] for d in r["depths"]}
    order = sorted(r["depths"])
    rises = [(a, b) for a, b in zip(order, order[1:]) if gaps[b] > gaps[a]]
    if rises:
        out.append("The gap does not fall at every step: " + "; ".join(
            f"{gaps[a]:.3f} at {blocks(a)}, {gaps[b]:.3f} at {blocks(b)}" for a, b in rises) + ".")
    edges = [(d, arm) for (d, arm), rate in r["chosen"].items() if rate in (min(r["cfg"].rates), max(r["cfg"].rates))]
    if edges:
        out.append("The search chose a rate at an end of its range for " + ", ".join(
            f"{arm} at {blocks(d)} ({r['chosen'][d, arm]:g})" for d, arm in sorted(edges)) +
            ": a wider range might have found a better one.")
    for d in r["depths"]:
        each, mean, paired, welch, lower = r["gaps"][d]
        if paired[0] > 0 >= welch[0]:
            out.append(f"At {blocks(d)} the pairs decide what Welch's interval does not: {paired[0]:.3f} to "
                       f"{paired[1]:.3f} against {welch[0]:.3f} to {welch[1]:.3f}.")
    return out


def main():
    cfg = lab.config(CONFIG)
    r = gather(cfg.pilot, cfg.depth)
    text = "\n".join(paper(r, cfg))
    print(text)
    path = os.path.join(cfg.out, cfg.name, "paper.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text + "\n")
    print(f"\nthe paper in {path}")


if __name__ == "__main__":
    main()
