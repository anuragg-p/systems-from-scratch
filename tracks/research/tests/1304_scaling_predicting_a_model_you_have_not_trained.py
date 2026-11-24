"""13.04 Scaling: predicting a model you have not trained

power_law recovers a known exponent from made points exactly, and within its standard error from noisy ones;
power_interval's interval holds the law's own value, and the mean of k new runs, as often as its level says, over
made experiments; counted is every weight but the two embeddings, and for a GPT without biases' and norms'
sub-leading terms about 12 L W^2; predict fits all but the largest and judges the largest; read gives back the rows
lab.Run wrote. The recorded run (experiments/recorded/scaling) has every width and seed with its config, log and
summary, its curves, fit and what it printed, and no weights; the loss falls with the width; the fit is
re-made from the summaries. With TinyStories, the default: every size scored, the prediction printed both ways of
counting, the recorded run read; and the same seed gives the same bytes again.
"""

import json
import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, os.path.join(t.root, LONG))
    T.need(t, "tinystories")
    r = T.experiment(t, "scaling")
    t.check(r.out.count("predicted") >= 2 and "3. The recorded run" in r.out,
            f"the default should predict both ways and read the recorded run:\n{r.out[-2500:]}")
    for w in (16, 24, 32, 48):
        t.check(len(T.summaries(r, f"width{w}")) == 2, f"width {w}: 2 seeds")
    means = [sum(s["bits_per_token"] for s in T.summaries(r, f"width{w}")) / 2 for w in (16, 32, 48)]
    t.check(means[0] > means[-1], f"the widest should be below the narrowest: {means}")
    tiny = ["widths=[8,16]", "largest=24", "steps=4", "every=2", "held=4", "held_stories=10", "context=16"]
    a, b = T.experiment(t, "scaling", *tiny), T.experiment(t, "scaling", *tiny)
    for run in ("width8/seed1", "width24/seed0", "fit/seed0"):
        t.check(read(os.path.join(a.runs, run, "summary.json")) == read(os.path.join(b.runs, run, "summary.json")),
                f"the same seed twice gave two different {run}/summary.json")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "width32", "seed0", "config.json")) as f:
            cfg = json.load(f)
        settings = [f"{k}={cfg[k]!r}".replace(" ", "") for k in ("size", "layers", "heads", "widths", "largest",
                                                                   "context", "batch", "steps", "lr", "warmup",
                                                                   "weight_decay", "clip", "every", "seeds",
                                                                   "largest_seeds", "held", "held_stories")]
        again = T.experiment(t, "scaling", *settings, timeout=3 * 3600)
        check_recorded(t, again.runs, rerun=True)


LONG = "experiments/recorded/scaling"


def check_recorded(t, d, rerun=False):
    """The recorded run: every width and seed with its config, its log (the held-out curve) and its summary; the
    curves, the fit, what it printed; no weights; the loss falling with the width; the fit as its summaries give it."""
    where = "the rerun" if rerun else f"the recorded run ({LONG})"
    t.check(os.path.isdir(d), f"no {where}")
    names = ["curves.svg", "fit.svg"] + ([] if rerun else ["output.txt"])
    t.check(all(os.path.isfile(os.path.join(d, n)) for n in names), f"{where}: {names}")
    t.check(not any(n.endswith(".safetensors") for _, _, fs in os.walk(d) for n in fs), f"{where}: no weights")
    first = os.path.join(d, sorted(n for n in os.listdir(d) if n.startswith("width"))[0], "seed0", "config.json")
    with open(first) as f:
        cfg = json.load(f)
    t.check(len(cfg["widths"]) >= 4 and cfg["seeds"] >= 3 and cfg["largest_seeds"] >= 2 and cfg["steps"] >= 500 and
            cfg["largest"] >= 4 * min(cfg["widths"]), f"{where}: 4 sizes or more, 3 seeds, the largest at least 2: {cfg}")
    means, rows = [], []
    for w in cfg["widths"] + [cfg["largest"]]:
        bits = []
        for seed in range(cfg["largest_seeds"] if w == cfg["largest"] else cfg["seeds"]):
            run = os.path.join(d, f"width{w}", f"seed{seed}")
            with open(os.path.join(run, "config.json")) as f:
                c = json.load(f)
            t.check({k: v for k, v in c.items() if k not in ("label", "seed", "out")} ==
                    {k: v for k, v in cfg.items() if k not in ("label", "seed", "out")} and c["seed"] == seed,
                    f"{where}: {run} was run with other settings")
            with open(os.path.join(run, "log.jsonl")) as f:
                log = [json.loads(line) for line in f if line.strip()]
            t.check(log[0]["step"] == 0 and log[-1]["step"] == cfg["steps"] - 1 and all("held_bits" in x for x in log),
                    f"{where}: {run}/log.jsonl should hold the held-out curve")
            with open(os.path.join(run, "summary.json")) as f:
                s = json.load(f)
            t.check(s["width"] == w and s["tokens"] == cfg["steps"] * cfg["batch"] * cfg["context"],
                    f"{where}: {run}/summary.json")
            bits.append(s["bits_per_token"])
            rows.append(s)
        means.append(sum(bits) / len(bits))
    t.check(all(a > b for a, b in zip(means, means[1:])), f"{where}: the loss should fall with the width: {means}")
    if not rerun:
        with open(os.path.join(d, "fit", "seed0", "summary.json")) as f:
            fit = json.load(f)
        import math
        xs = [math.log(s["weights"]) for s in rows if s["width"] != cfg["largest"]]
        ys = [math.log(s["bits_per_token"]) for s in rows if s["width"] != cfg["largest"]]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        t.check(abs(-slope - fit["weights"]["law"]["alpha"]) < 1e-9 and fit["weights"]["law"]["alpha"] > 0,
                f"{where}: the fit should be the summaries' own: {-slope} against {fit['weights']['law']}")
        miss = {by: abs(fit[by]["got"] - fit[by]["predicted"]) for by in ("weights", "all_weights")}
        t.check(fit["weights"]["inside"] and miss["weights"] < miss["all_weights"],
                f"{where}: counted as the paper counts, the largest should land inside the interval, and nearer than "
                f"with every weight counted: {fit}")


def inside(S):
    import math
    import tempfile
    import numpy as np
    import torch
    import lab
    from experiments import scaling
    from models.gpt import GPT

    xs = [1e3, 3e3, 1e4, 3e4, 1e5]
    law = lab.power_law(xs, [5.0 * x ** -0.3 for x in xs])
    assert abs(law["alpha"] - 0.3) < 1e-12 and abs(law["a"] - 5.0) < 1e-9 and law["s"] < 1e-12 and law["n"] == 5
    assert abs(law["mean_log_x"] - np.mean(np.log(xs))) < 1e-12
    guess, lo, hi = lab.power_interval(law, 1e6)
    assert abs(guess - 5.0 * 1e6 ** -0.3) < 1e-9 and hi - lo < 1e-9

    rng = np.random.default_rng(0)
    x = np.repeat([1e3, 4e3, 1.6e4, 6.4e4], 3)
    big, hits_law, hits_mean, ses, alphas = 1e6, 0, 0, [], []
    for _ in range(3000):
        y = 4.0 * x ** -0.1 * np.exp(rng.normal(0, 0.02, len(x)))
        law = lab.power_law(x.tolist(), y.tolist())
        alphas.append(law["alpha"])
        ses.append(law["alpha_se"])
        _, lo, hi = lab.power_interval(law, big)
        hits_law += lo <= 4.0 * big ** -0.1 <= hi
        new = np.mean(4.0 * big ** -0.1 * np.exp(rng.normal(0, 0.02, 2)))
        _, lo, hi = lab.power_interval(law, big, k=2)
        hits_mean += lo <= new <= hi
    assert abs(np.mean(alphas) - 0.1) < 0.002 and abs(np.std(alphas) / np.mean(ses) - 1) < 0.1, "alpha's error"
    assert abs(hits_law / 3000 - 0.95) < 0.015 and abs(hits_mean / 3000 - 0.95) < 0.015, (hits_law, hits_mean)
    _, lo, hi = lab.power_interval(law, big, level=0.5)
    _, lo95, hi95 = lab.power_interval(law, big)
    assert lo95 < lo < hi < hi95

    for positions in (True, False):
        model = GPT(50, 16, layers=3, heads=2, width=8, positions=positions)
        total = sum(p.numel() for p in model.parameters())
        assert scaling.counted(model) == total - 50 * 8 - (16 * 8 if positions else 0)
        assert scaling.counted(model) == 3 * (12 * 64 + 13 * 8) + 2 * 8
    model = GPT(4096, 256, layers=4, heads=4, width=256)
    assert abs(scaling.counted(model) / (12 * 4 * 256 ** 2) - 1) < 0.01

    rows = [dict(width=w, weights=n, all_weights=n + 1000, bits=7.0 * n ** -0.08, seed=0) for w, n in
            ((8, 1e3), (16, 4e3), (32, 1.6e4), (64, 6.4e4))]
    rows += [dict(r, bits=r["bits"] * 1.001, seed=1) for r in rows]
    got = scaling.predict(rows, 64)
    assert got["inside"] and abs(got["predicted"] - 7.0 * 6.4e4 ** -0.08 * 1.0005) < 1e-3 and got["law"]["n"] == 6
    assert got["runs"] == [7.0 * 6.4e4 ** -0.08, 7.0 * 6.4e4 ** -0.08 * 1.001]
    far = scaling.predict([dict(r, bits=r["bits"] * (1.2 if r["width"] == 64 else 1)) for r in rows], 64)
    assert not far["inside"] and far["got"] > far["high"]
    assert scaling.predict(rows, 64, "all_weights")["n"] == 6.4e4 + 1000

    with tempfile.TemporaryDirectory() as d:
        cfg = lab.Config(scaling.CONFIG, out=d, name="scaling")
        for r in rows:
            run = lab.Run(cfg, r["seed"], label=f"width{r['width']}")
            run.finish(width=r["width"], seed=r["seed"], weights=r["weights"], all_weights=r["all_weights"],
                       bits_per_token=r["bits"])
        lab.Run(cfg, 0, label="fit").finish()
        back, c = scaling.read(os.path.join(d, "scaling"))
        assert sorted(back, key=lambda r: (r["width"], r["seed"])) == sorted(rows, key=lambda r: (r["width"], r["seed"]))
        assert c.widths == cfg.widths and c.largest == cfg.largest
