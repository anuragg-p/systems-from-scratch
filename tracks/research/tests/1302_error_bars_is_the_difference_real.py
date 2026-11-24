"""13.02 Error bars: is the difference real?

sem, t_density, t_cdf, t_quantile, interval and difference (paired and Welch's) against scipy when it is
installed, else against the t table and the formulas written out here; bootstrap against the same draws taken by
hand, and against mean +- 1.96 sem on a large sample; seeds_needed against simulated experiments at n seeds and
at one fewer; batch_sem growing on a series whose neighbours move together, to the standard error its
correlation gives; position_bits' mean equal to window_bits. The recorded run (experiments/recorded/errorbars)
has every file, and its verdict: four heads lower, the paired interval clear of 0. The default reproduces
08.02's models (seeds 0 to 2: 3.433 and 3.407, within 0.01), the two arms start from the same weights, the
paired interval narrower than Welch's, the difference on one test text far less noisy than either score; and the
same seed gives the same bytes again.
"""

import json
import os
import re

LONG = "experiments/recorded/errorbars"


def read(path):
    with open(path, "rb") as f:
        return f.read()


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, os.path.join(t.root, LONG))
    r = T.experiment(t, "errorbars")
    one, many = T.value(r.out, r"^   1 head    ([\d.]+) "), T.value(r.out, r"^   4 heads   ([\d.]+) ")
    t.check(abs(one - 3.433) < 0.01 and abs(many - 3.407) < 0.01,
            f"seeds 0 to 2 should be 08.02's models (3.433 and 3.407): {one}, {many}")
    t.check("starts both arms from the same weights: True" in r.out, "the arms of one seed should start the same")
    welch = T.value(r.out, r"as two independent sets \(Welch\): .* width ([\d.]+)")
    paired = T.value(r.out, r"as pairs, seed by seed: .* width ([\d.]+)")
    t.check(paired < welch, f"pairs should give the narrower interval: {paired} against {welch}")
    rows = re.findall(r"^ +(1 head|4 heads|4 minus 1)((?: +[\d.]+)+)$", r.out, re.M)
    sems = {name: [float(x) for x in values.split()] for name, values in rows}
    t.check(set(sems) == {"1 head", "4 heads", "4 minus 1"} and sems["4 minus 1"][-2] < sems["1 head"][-2] / 3,
            f"the difference on one text should be far less noisy than one model's score: {sems}")
    t.check(sems["1 head"][-2] > sems["1 head"][0], f"neighbouring windows move together: {sems['1 head']}")
    tiny = ["seeds=2", "steps=6", "layers=1", "width=16", "context=16", "every=2", "resamples=100"]
    a, b = T.experiment(t, "errorbars", *tiny), T.experiment(t, "errorbars", *tiny)
    for run in ("heads1/seed1", "heads4/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "heads1", "seed0", "config.json")) as f:
            cfg = json.load(f)
        settings = [f"{k}={cfg[k]!r}".replace(" ", "") for k in ("width", "context", "batch", "steps", "lr", "warmup",
                                                                   "weight_decay", "clip", "every", "seeds", "layers",
                                                                   "heads")]
        again = T.experiment(t, "errorbars", *settings, timeout=3 * 3600)
        check_recorded(t, again.runs, rerun=True)


def check_recorded(t, d, rerun=False):
    """The recorded run: both arms, every seed with its config, log and summary; what it printed; and its verdict."""
    where = "the rerun" if rerun else f"the recorded run ({LONG})"
    t.check(os.path.isdir(d), f"no {where}")
    if not rerun:
        t.check(os.path.isfile(os.path.join(d, "output.txt")), f"{where}: no output.txt, what the run printed")
    with open(os.path.join(d, "heads1", "seed0", "config.json")) as f:
        cfg = json.load(f)
    t.check(cfg["seeds"] >= 10, f"{where}: 10 seeds a side or more: {cfg['seeds']}")
    got = {}
    for heads in (1, cfg["heads"]):
        for seed in range(cfg["seeds"]):
            run = os.path.join(d, f"heads{heads}", f"seed{seed}")
            with open(os.path.join(run, "config.json")) as f:
                c = json.load(f)
            t.check({k: v for k, v in c.items() if k not in ("label", "seed", "out")} ==
                    {k: v for k, v in cfg.items() if k not in ("label", "seed", "out")} and c["seed"] == seed,
                    f"{where}: {run} was run with other settings")
            with open(os.path.join(run, "log.jsonl")) as f:
                rows = [json.loads(line) for line in f if line.strip()]
            t.check(rows[0]["step"] == 0 and rows[-1]["step"] == cfg["steps"] - 1, f"{where}: {run}/log.jsonl")
            with open(os.path.join(run, "summary.json")) as f:
                got.setdefault(heads, []).append(json.load(f)["test_bits"])
    diffs = [a - b for a, b in zip(got[cfg["heads"]], got[1])]
    n = len(diffs)
    m = sum(diffs) / n
    sd = (sum((x - m) ** 2 for x in diffs) / (n - 1)) ** 0.5
    t.check(m + 2.3 * sd / n ** 0.5 < 0, f"{where}: four heads should be lower, the paired interval clear of 0: {diffs}")


def inside(S):
    import math
    import numpy as np
    import torch
    import lab
    from lab import stats
    from experiments.errorbars import position_bits
    from experiments.sequences import window_bits
    from models.gpt import GPT

    try:
        from scipy import stats as sp
    except ImportError:
        sp = None
    rng = np.random.default_rng(0)
    xs = rng.normal(3.4, 0.02, 7).tolist()
    ys = rng.normal(3.38, 0.01, 5).tolist()
    assert abs(lab.sem(xs) - np.std(xs, ddof=1) / math.sqrt(7)) < 1e-15
    table = {(1, 0.975): 12.706205, (2, 0.975): 4.302653, (4, 0.975): 2.776445, (9, 0.975): 2.262157,
             (2, 0.8): 1.060660, (30, 0.975): 2.042272, (4, 0.995): 4.604095}
    for (df, p), want in table.items():
        assert abs(lab.t_quantile(p, df) - want) < 2e-6, (df, p, lab.t_quantile(p, df))
        assert abs(lab.t_quantile(1 - p, df) + want) < 2e-6
        assert abs(stats.t_cdf(want, df) - p) < 1e-7
    assert abs(stats.t_density(0.0, 1) - 1 / math.pi) < 1e-14 and stats.t_cdf(0.0, 3) == 0.5
    if sp is not None:
        for df in (1, 2, 2.5, 3, 7.3, 30, 400):
            for x in (-4.0, -1.0, 0.3, 2.0, 9.0):
                assert abs(stats.t_density(x, df) - sp.t.pdf(x, df)) < 1e-12 * (1 + sp.t.pdf(x, df))
                assert abs(stats.t_cdf(x, df) - sp.t.cdf(x, df)) < 1e-8
            for p in (0.6, 0.8, 0.95, 0.975, 0.995):
                assert abs(lab.t_quantile(p, df) - sp.t.ppf(p, df)) < 1e-6 * (1 + sp.t.ppf(p, df)), (df, p)
        lo, hi = lab.interval(xs)
        want = sp.t.interval(0.95, 6, loc=np.mean(xs), scale=sp.sem(xs))
        assert abs(lo - want[0]) < 1e-9 and abs(hi - want[1]) < 1e-9
        d, lo, hi = lab.difference(xs, ys)
        ci = sp.ttest_ind(xs, ys, equal_var=False).confidence_interval()
        assert abs(lo - ci.low) < 1e-9 and abs(hi - ci.high) < 1e-9 and abs(d - (np.mean(xs) - np.mean(ys))) < 1e-14
        d, lo, hi = lab.difference(xs[:5], ys, paired=True)
        ci = sp.ttest_rel(xs[:5], ys).confidence_interval()
        assert abs(lo - ci.low) < 1e-9 and abs(hi - ci.high) < 1e-9
    va, vb = lab.sem(xs) ** 2, lab.sem(ys) ** 2
    df = (va + vb) ** 2 / (va ** 2 / 6 + vb ** 2 / 4)
    d, lo, hi = lab.difference(xs, ys)
    assert abs((hi - lo) / 2 - lab.t_quantile(0.975, df) * math.sqrt(va + vb)) < 1e-12
    diffs = [a - b for a, b in zip(xs[:5], ys)]
    d, lo, hi = lab.difference(xs[:5], ys, paired=True)
    assert (lo, hi) == lab.interval(diffs) and abs(d - np.mean(diffs)) < 1e-14
    try:
        lab.difference(xs, ys, paired=True)
        raise AssertionError("pairs need as many runs a side")
    except ValueError:
        pass

    g = np.random.default_rng(5)
    got = lab.bootstrap([xs, ys], lambda a, b: a.mean() - b.mean(), g, 500)
    g = np.random.default_rng(5)
    a = np.array(xs)[g.integers(0, 7, (500, 7))].mean(1)
    b = np.array(ys)[g.integers(0, 5, (500, 5))].mean(1)
    assert np.allclose(got, np.quantile(a - b, [0.025, 0.975]), rtol=0, atol=1e-15), got
    big = np.random.default_rng(6).normal(0, 1, 4000)
    lo, hi = lab.bootstrap([big], np.mean, np.random.default_rng(7), 4000)
    half = 1.96 * big.std(ddof=1) / math.sqrt(4000)
    assert abs((hi - lo) / 2 - half) < 0.08 * half and abs((hi + lo) / 2 - big.mean()) < 0.2 * half

    # Experiments simulated at n seeds and at n - 1: how often the interval comes out clear of 0 (paired: the
    # differences' own interval; independent: Student's, with the two arms' variance pooled, 2 (n - 1) degrees of
    # freedom, which is what seeds_needed counts on).
    sim = np.random.default_rng(8)
    for size, sd, paired in ((1.0, 1.0, False), (0.6, 1.0, True), (0.026, 0.0129, False), (0.026, 0.0074, True)):
        n = lab.seeds_needed(size, sd, paired=paired)
        z = 1.959964 + 0.841621
        assert n >= (1 if paired else 2) * (z * sd / size) ** 2
        clear = {}
        for k in (n - 1, n):
            a = sim.normal(size, sd, (20000, k))
            if paired:
                half = lab.t_quantile(0.975, k - 1) * a.std(1, ddof=1) / math.sqrt(k)
                lo = a.mean(1) - half
            else:
                b = sim.normal(0, sd, (20000, k))
                pooled = np.sqrt((a.var(1, ddof=1) + b.var(1, ddof=1)) / 2)
                lo = a.mean(1) - b.mean(1) - lab.t_quantile(0.975, 2 * (k - 1)) * pooled * math.sqrt(2 / k)
            clear[k] = float((lo > 0).mean())
        assert clear[n] >= 0.79 and clear[n - 1] < 0.8, (size, paired, n, clear)

    series, phi = [0.0], 0.8
    for e in np.random.default_rng(9).normal(0, 1, 200000):
        series.append(phi * series[-1] + e)
    series = series[1:]
    assert abs(lab.batch_sem(series, 1) - lab.sem(series)) < 1e-15
    want = math.sqrt(1 / (1 - phi ** 2)) / math.sqrt(len(series)) * math.sqrt((1 + phi) / (1 - phi))
    assert lab.batch_sem(series, 1) < 0.5 * want and abs(lab.batch_sem(series, 500) - want) < 0.15 * want, \
        (lab.batch_sem(series, 1), lab.batch_sem(series, 500), want)

    torch.manual_seed(0)
    model = GPT(11, 12, layers=1, heads=2, width=8, positions=False).eval()
    ids = torch.randint(0, 11, (300,))
    for span, warm in ((7, 6), (5, 8), (12, 1)):
        bits = position_bits(model, ids, span, warm, batch=4)
        assert len(bits) == len(ids) - warm and bits.dtype == np.float64
        assert abs(bits.mean() - window_bits(model, ids, span, warm)) < 1e-5
