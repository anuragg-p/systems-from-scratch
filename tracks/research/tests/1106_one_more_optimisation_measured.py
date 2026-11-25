"""11.06 One more optimisation, measured

causal_mask with keys: the triangle moved right, the square one as before. self_attend and fused_attend of
new queries after kept keys equal the last rows of the whole computation (float64, 1e-12). Cache keeps keys
and values in order and refuses more than its size. A GPT read in pieces through its caches gives the
scores of the whole window, in float64 to 1e-12: learned positions (Positions from a start place), rotary
positions, grouped heads, written-out and fused attention, a piece at a time or several. cached_scores
gives model(ids[:, -context:])'s last scores at every length, also past the window, where it starts the
caches again. generate with the cache writes the same symbols as without, greedy and sampled (plain,
top-k, nucleus), on small GPTs of each kind; and with the downloads (python3 -m data.fetch gpt2 and
smollm2; without them those checks are skipped, said so), on GPT-2 small (learned positions) and
SmolLM2-135M (rotary, 3 key/value heads for 9). The recorded benchmark (experiments/recorded/benchmark,
the module's long run, benchmark.py with every row): every row and seed run with the same settings but
what its row changes, a log with the held-out curve to its end and a summary, times.json, the curves and
what it printed, no weights; the numbers the same where they must be (the angles kept: every log and
summary byte for byte the baseline's; fused attention: the baseline's curve to rounding), never its
speeds. The short run (it needs SmolLM2): the same symbols everywhere, the float64 scores within 1e-10,
and the table of times written.
"""

import json
import os
import re

LONG = "experiments/recorded/benchmark"
ROWS = {"baseline": {}, "angles-kept": {}, "fused-attention": {}, "bfloat16": {"precision": "bfloat16"},
        "twice-the-batch-and-rate": {"batch": 2, "lr": 2}, "all-together": {"batch": 2, "lr": 2}}


def read(path):
    with open(path, "rb") as f:
        return f.read()


def check_recorded(t, d):
    """The recorded benchmark's shape, and its numbers the same where they must be; not its speeds."""
    t.check(os.path.isdir(d), f"no recorded benchmark in {d}")
    for name in ("times.json", "curves.svg", "output.txt"):
        t.check(os.path.isfile(os.path.join(d, name)), f"the recorded benchmark: no {name}")
    t.check(not any(f.endswith(".safetensors") for _, _, fs in os.walk(d) for f in fs), "no weights are shipped")
    with open(os.path.join(d, "baseline", "seed0", "config.json")) as f:
        base = json.load(f)
    t.check(base["seeds"] >= 3 and base["steps"] >= 500, f"3 seeds a row or more, 500 steps or more: {base}")
    with open(os.path.join(d, "times.json")) as f:
        times = json.load(f)
    t.check(sorted(n.replace(" ", "-") for n in times) == sorted(ROWS), f"times.json's rows: {list(times)}")
    for row, changes in ROWS.items():
        for seed in range(base["seeds"]):
            run = os.path.join(d, row, f"seed{seed}")
            with open(os.path.join(run, "config.json")) as f:
                c = json.load(f)
            want = dict(base, label=row, seed=seed)
            for k, v in changes.items():
                want[k] = v if isinstance(v, str) else base[k] * v
            t.check({k: v for k, v in c.items() if k != "out"} == {k: v for k, v in want.items() if k != "out"},
                    f"{run} was run with other settings than its row's: {c}")
            with open(os.path.join(run, "log.jsonl")) as f:
                log = [json.loads(line) for line in f if line.strip()]
            with open(os.path.join(run, "summary.json")) as f:
                s = json.load(f)
            t.check(all("held_bits" in r for r in log) and s["steps"] == log[-1]["step"] + 1, f"{run}: its log and summary")
            if s["steps_to_target"] is not None:
                t.check(log[-1]["held_bits"] <= base["target"] < log[-2]["held_bits"],
                        f"{run} should stop at the first row that reaches the target")
    for seed in range(base["seeds"]):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(d, "baseline", f"seed{seed}", name)) ==
                    read(os.path.join(d, "angles-kept", f"seed{seed}", name)),
                    f"keeping the angles changes no number: seed {seed}'s {name} should be the baseline's")
        a, b = ([json.loads(line)["held_bits"] for line in open(os.path.join(d, row, f"seed{seed}", "log.jsonl"))]
                for row in ("baseline", "fused-attention"))
        n = min(len(a), len(b))
        t.check(max(abs(x - y) for x, y in zip(a[:n], b[:n])) < 0.02, f"fused attention: the baseline's curve, seed {seed}")


def test(t):
    T = t.track
    T.inside(t, __file__)
    check_recorded(t, os.path.join(t.root, LONG))
    have = [T.need(t, d, skip=True) for d in ("gpt2", "smollm2")]
    if any(have):
        out = T.inside(t, __file__, "with_data")
        print("      " + "\n      ".join(line for line in out.splitlines() if line.startswith("11.06")))
    T.need(t, "smollm2")
    r = T.experiment(t, "cache")
    answers = re.findall(r"^   (?:greedy|sampled|top-k=40|nucleus, p=0\.95) +(True|False)$", r.out, re.M)
    t.check(answers == ["True"] * 8, f"the same symbols with the cache and without: {answers}\n{r.out[:3000]}")
    t.check("the same tokens: True" in r.out, f"the timed writing should write the same tokens:\n{r.out[-2500:]}")
    worst = T.value(r.out, r"the largest difference (\S+)")
    t.check(worst < 1e-10, f"cached scores in float64: {worst}")
    t.check(len(re.findall(r"^ +\d+ +\S+ +\S+ +\S+ ms +\S+ +\S+ +\S+ ms +x", r.out, re.M)) == 4,
            f"the table of times:\n{r.out[-2000:]}")
    if os.environ.get("LEARN_RERUN_LONG"):
        with open(os.path.join(t.root, LONG, "baseline", "seed0", "config.json")) as f:
            cfg = json.load(f)
        with open(os.path.join(t.root, LONG, "times.json")) as f:
            rows = list(json.load(f))
        settings = [f"{k}={cfg[k]!r}".replace(" ", "") for k in ("layers", "heads", "width", "context", "kv_heads", "batch",
                                                                   "steps", "lr", "warmup", "weight_decay", "clip", "every",
                                                                   "held", "target", "seeds")]
        again = T.experiment(t, "benchmark", *settings, f"rows={rows!r}", "recorded=none", timeout=3 * 3600)
        out = again.runs
        with open(os.path.join(out, "output.txt"), "w") as f:
            f.write(again.out)
        check_recorded(t, out)


def check_tokens(model, prompt, n, what):
    import torch
    from experiments.language import generate
    for temperature, k, p in ((0.0, None, None), (1.0, None, None), (1.0, 40, None), (0.8, None, 0.9)):
        a, b = (generate(model, prompt, n, torch.Generator().manual_seed(3), temperature, k, p, cache=c)
                for c in (False, True))
        assert torch.equal(a, b), f"{what}: with the cache and without, other symbols ({temperature}, {k}, {p})"


def inside(S):
    import torch
    from experiments.language import cached_scores
    from models.gpt import GPT, Cache, causal_mask, fused_attend, self_attend

    assert torch.equal(causal_mask(5), torch.ones(5, 5, dtype=torch.bool).tril())
    assert causal_mask(2, keys=5).tolist() == [[True] * 4 + [False], [True] * 5]
    assert causal_mask(1, keys=3).tolist() == [[True, True, True]]
    torch.manual_seed(0)
    q, k, v = (torch.randn(2, 3, 9, 4, dtype=torch.float64) for _ in range(3))
    whole = self_attend(q, k, v)[0]
    for n in (1, 3):
        S.same(self_attend(q[..., -n:, :], k, v)[0], whole[..., -n:, :], f"self_attend, {n} after the kept", tol=1e-12)
        S.same(fused_attend(q[..., -n:, :], k, v), whole[..., -n:, :], f"fused_attend, {n} after the kept", tol=1e-12)

    cache = Cache(6)
    assert len(cache) == 0
    a, b = cache.add(k[..., :2, :], v[..., :2, :])
    assert len(cache) == 2 and torch.equal(a, k[..., :2, :])
    a, b = cache.add(k[..., 2:5, :], v[..., 2:5, :])
    assert len(cache) == 5 and torch.equal(a, k[..., :5, :]) and torch.equal(b, v[..., :5, :])
    try:
        cache.add(k[..., :2, :], v[..., :2, :])
    except ValueError as e:
        assert "cannot take 2 more after 5" in str(e)
    else:
        raise AssertionError("a full cache should refuse more")

    kinds = [dict(), dict(positions="rotary", kv_heads=2, norm="rms", mlp="swiglu"), dict(positions="rotary", base=500.0),
             dict(fused=True), dict(positions="rotary", kv_heads=1, fused=True)]
    for kw in kinds:
        torch.manual_seed(1)
        model = GPT(65, 24, layers=2, heads=4, width=16, **kw).double().eval()
        ids = torch.randint(0, 65, (3, 24))
        with torch.no_grad():
            want = model(ids)
            for pieces in ([7] + [1] * 17, [1] * 24, [5, 6, 13], [24]):
                caches = [Cache(24) for _ in model.blocks]
                got, at = [], 0
                for n in pieces:
                    got.append(model(ids[:, at:at + n], caches))
                    at += n
                S.same(torch.cat(got, 1), want, f"GPT {kw} read through its caches in pieces {pieces[:4]}", tol=1e-12)
            state, ctx = None, model.context
            longer = torch.randint(0, 65, (2, 40))
            for n in range(3, 41):
                got, state = cached_scores(model, longer[:, :n], state)
                S.same(got, model(longer[:, :n][:, -ctx:])[:, -1], f"cached_scores {kw} at {n}", tol=1e-12)
        small = GPT(65, 24, layers=2, heads=4, width=16, **kw).eval()
        check_tokens(small, torch.randint(0, 65, (2, 5)), 30, f"a small GPT {kw}")
    try:
        GPT(65, 8, layers=1, heads=2, width=8)(torch.zeros(1, 3, dtype=torch.long), [Cache(10)])
        GPT(65, 8, layers=1, heads=2, width=8).positions(torch.zeros(1, 3, 8), 6)
    except ValueError as e:
        assert "9 positions, but there are learned vectors for 8" in str(e), e
    else:
        raise AssertionError("learned positions past the table should be refused")


def with_data(S):
    import torch
    from data import fetch
    from models import gpt2, smollm
    from tokens import gpt2 as gpt2_tokens, smollm as smollm_tokens

    text = "PROSPERO:\n'Tis time\nI should inform thee farther. Lend thy hand,"
    for name, M, Tok in (("gpt2", gpt2, gpt2_tokens), ("smollm2", smollm, smollm_tokens)):
        if fetch.missing(name):
            print(f"11.06 {name}: not fetched, skipped")
            continue
        model = M.load(torch.device("cpu"))
        tok = Tok.load()
        prompt = torch.tensor([tok.encode(text)])
        check_tokens(model, prompt, 24, name)
        print(f"11.06 {name}: the same tokens with the cache and without, greedy and sampled (24 after "
              f"{prompt.shape[1]})")
