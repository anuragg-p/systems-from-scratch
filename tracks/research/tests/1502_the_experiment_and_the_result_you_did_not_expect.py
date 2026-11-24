"""15.02 The experiment, and the result you did not expect

choose() takes the rate with the lowest validation bits and reads nothing else; gaps() gives the paired interval
and Welch's as lab.difference does; Wider keeps a block's MLP and adds units that start as GPT-2 starts, so with
their way out at zero the model computes what it did; widen() adds about the weights learned positions add;
search() gives both arms the same rates on the same seed and scores the validation text only. The recorded run
(experiments/recorded/depth) has every file: the search never read the test text, each arm ran at the rate its
search chose, every depth ran the pairs the pilot fixed, the control has about as many more weights as positions
add; and its result: positions worth most at one block, less at the deepest, beyond the noise at one block. The
default runs its small version and reads the record; the same seed gives the same bytes again.
"""

import json
import os
import re

DEPTH = "experiments/recorded/depth"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, os.path.join(t.root, DEPTH))
    r = T.experiment(t, "depth")
    t.check("6. The recorded run" in r.out and r.out.count("not run here") == 3,
            f"the default should run depths 1 and 2 (three predictions need depths it does not run) and read the "
            f"record:\n{r.out[-3000:]}")
    for label in ("blocks1-none", "blocks1-learned", "blocks2-none", "blocks2-learned"):
        t.check(len(T.summaries(r, label)) == 2, f"the default should run 2 fresh seeds of {label}")
    one = [a["test_bits"] - b["test_bits"] for a, b in zip(T.summaries(r, "blocks1-none"),
                                                         T.summaries(r, "blocks1-learned"))]
    t.check(all(g > 0.05 for g in one), f"positions should be worth more than 0.05 bits at one block: {one}")
    verdicts = re.findall(r"^   (\w+) +(held|did not hold|not settled|not run here)", r.out, re.M)
    t.check(len(verdicts) == 14, f"7 verdicts for the default's runs and 7 for the record's: {verdicts}")
    tiny = ["seeds=2", "steps=6", "every=2", "width=16", "context=16", "rates=[0.003]", "control=2"]
    a, b = T.experiment(t, "depth", *tiny), T.experiment(t, "depth", *tiny)
    for run in ("blocks1-none/seed2", "blocks2-learned/seed1", "control-blocks2-wider/seed1",
                "search-blocks2-none-lr0.003/seed0"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def runs_in(d):
    out = {}
    for label in sorted(os.listdir(d)):
        if os.path.isdir(os.path.join(d, label)):
            for seed in sorted(int(s[4:]) for s in os.listdir(os.path.join(d, label)) if s.startswith("seed")):
                run = os.path.join(d, label, f"seed{seed}")
                with open(os.path.join(run, "config.json")) as f:
                    c = json.load(f)
                with open(os.path.join(run, "summary.json")) as f:
                    s = json.load(f)
                with open(os.path.join(run, "log.jsonl")) as f:
                    rows = [json.loads(line) for line in f if line.strip()]
                out.setdefault(label, []).append((c, s, rows))
    return out


def mean(xs):
    return sum(xs) / len(xs)


def check_recorded(t, d):
    """The recorded experiment: every run, the choices made on validation only, and its result."""
    where = f"the recorded run ({DEPTH})"
    t.check(os.path.isdir(d) and all(os.path.isfile(os.path.join(d, f)) for f in ("output.txt", "bits.svg", "gap.svg")),
            f"no {where}, or no output.txt and figures")
    runs = runs_in(d)
    c = next(x for label, xs in runs.items() if not label.startswith(("search", "control")) for x in xs)[0]
    depths, rates = c["depths"], c["rates"]
    t.check(depths == [1, 2, 4, 6, 8] and len(rates) >= 3 and c["steps"] == 300 and c["control"] == 4,
            f"{where}: depths 1 to 8, 3 rates or more, 300 steps, the control at 4 blocks: {c}")
    found, chosen = {}, {}
    for dd in depths:
        for arm in ("none", "learned"):
            for rate in rates:
                label = f"search-blocks{dd}-{arm}-lr{rate:g}"
                t.check(label in runs and len(runs[label]) == 1, f"{where}: no {label}")
                (cs, s, rows), = runs[label]
                t.check(cs["seed"] == 0 and cs["lr"] == rate and set(s) == {"val_bits", "weights"},
                        f"{where}: {label} should be seed 0 at its rate, scored on validation only: {s}")
                found.setdefault((dd, arm), {})[rate] = s["val_bits"]
            chosen[dd, arm] = min(found[dd, arm], key=found[dd, arm].get)
    seeds, bits = None, {}
    for dd in depths:
        for arm in ("none", "learned"):
            xs = runs[f"blocks{dd}-{arm}"]
            seeds = seeds or [cc["seed"] for cc, _, _ in xs]
            t.check([cc["seed"] for cc, _, _ in xs] == seeds and seeds == list(range(1, len(seeds) + 1)),
                    f"{where}: blocks{dd}-{arm} should run the fresh seeds 1 to {len(seeds)}")
            for cc, s, rows in xs:
                t.check(cc["lr"] == chosen[dd, arm], f"{where}: blocks{dd}-{arm} seed {cc['seed']} at {cc['lr']}, "
                                                     f"its search chose {chosen[dd, arm]}")
                t.check({k: v for k, v in cc.items() if k not in ("label", "seed", "lr")} ==
                        {k: v for k, v in c.items() if k not in ("label", "seed", "lr")}, f"{where}: other settings")
                t.check(rows[0]["step"] == 0 and rows[-1]["step"] == c["steps"] - 1 and "test_bits" in s,
                        f"{where}: blocks{dd}-{arm} seed {cc['seed']}: its log and its test bits")
            bits[dd, arm] = [s["test_bits"] for _, s, _ in xs]
    control = runs[f"control-blocks{c['control']}-wider"]
    added = control[0][1]["weights"] - runs[f"blocks{c['control']}-none"][0][1]["weights"]
    positions = c["context"] * c["width"]
    t.check([cc["seed"] for cc, _, _ in control] == seeds and abs(added - positions) <= 0.02 * positions and
            all(cc["lr"] == chosen[c["control"], "none"] for cc, _, _ in control),
            f"{where}: the control, every seed, about {positions} more weights ({added}), at the rate chosen for no "
            f"positions")
    gaps = {dd: [a - b for a, b in zip(bits[dd, "none"], bits[dd, "learned"])] for dd in depths}
    m = {dd: mean(g) for dd, g in gaps.items()}
    t.check(m[1] > 0.1 and min(gaps[1]) > 0 and m[1] > 2 * m[8], f"{where}: the gap by depth: {m}")
    t.check(all(m[dd] < m[1] for dd in depths[1:]), f"{where}: positions worth most at one block: {m}")


def inside(S):
    import tempfile
    import torch
    import lab
    from experiments import depth, question as q
    from models.gpt import GPT, MLP

    # choose: the lowest validation bits, nothing else
    assert q.choose({(1, "none"): {0.001: 3.5, 0.003: 3.4, 0.01: 3.6}, (2, "learned"): {0.001: 3.2}}) == \
        {(1, "none"): 0.003, (2, "learned"): 0.001}
    # gaps: the paired interval and Welch's, as lab.difference gives them
    bits = {(1, "none"): [3.5, 3.6, 3.55, 3.52], (1, "learned"): [3.3, 3.42, 3.33, 3.31]}
    each, mean_, paired, welch, lower = q.gaps(bits, [1])[1]
    assert each == [a - b for a, b in zip(bits[1, "none"], bits[1, "learned"])] and lower == 4
    assert (mean_, *paired) == lab.difference(bits[1, "none"], bits[1, "learned"], paired=True)
    assert welch == lab.difference(bits[1, "none"], bits[1, "learned"])[1:]
    assert paired[1] - paired[0] < welch[1] - welch[0]          # these runs move together: pairs are narrower

    # Wider: the same function as the MLP it widens, once its extra units' way out is zero
    torch.manual_seed(0)
    mlp, x = MLP(16), torch.randn(3, 5, 16)
    wide = depth.Wider(mlp, 4, layers=2)
    assert wide.up.out_features == 68 and wide.down.in_features == 68
    assert torch.equal(wide.up.weight[:64], mlp.up.weight) and torch.equal(wide.down.weight[:, :64], mlp.down.weight)
    assert 0.01 < wide.up.weight[64:].std().item() < 0.03 and wide.up.bias[64:].abs().max().item() == 0
    with torch.no_grad():
        wide.down.weight[:, 64:] = 0
        assert torch.allclose(wide(x), mlp(x), atol=1e-6)
    cfg = lab.Config(context=32, width=64, heads=4)
    for layers in (1, 2, 4, 8):
        model = GPT(65, 32, layers, 4, 64, positions=False)
        before = sum(p.numel() for p in model.parameters())
        depth.widen(model, depth.extra_units(cfg, layers), layers)
        assert abs(sum(p.numel() for p in model.parameters()) - before - 32 * 64) <= 0.02 * 32 * 64, layers

    # search: every rate for both arms, seed 0, validation only
    cfg = lab.Config(depth.CONFIG, depths=[1], rates=[0.003, 0.01], steps=3, every=1, width=16, context=16,
                     out=tempfile.mkdtemp(), name="depth")
    texts = {s: (torch.arange(300) * 7) % 65 for s in ("train", "val", "test")}
    found = depth.search(65, cfg, torch.device("cpu"), texts)
    assert set(found) == {(1, "none"), (1, "learned")} and all(set(v) == {0.003, 0.01} for v in found.values())
    back = q.read_runs(os.path.join(cfg.out, "depth"))
    assert sorted(back) == sorted(f"search-blocks1-{a}-lr{r:g}" for a in ("none", "learned") for r in (0.003, 0.01))
    for seeds in back.values():
        (settings, summary), = seeds
        assert settings["seed"] == 0 and set(summary) == {"val_bits", "weights"}
    # results() reads the search back as search() returned it
    got, runs, control, rc = q.results(os.path.join(cfg.out, "depth"))
    assert got == found and runs == {} and control == {} and rc is None
