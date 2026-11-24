"""08.03 Where am I: position embeddings

Positions adds its row for each place and refuses a window longer than it has rows for; a GPT with
positions equals the same model computed again in float64 numpy (tests/support.py) to 1e-10, and,
with weights copied in by the mapping NOTES.md gives for GPT-2, transformers' GPT2LMHeadModel
(random weights, a small configuration) to 1e-10 in float64: the shapes 09.03 loads GPT-2 small
into. Without positions one block gives the last position the same scores for any order of the
characters before it (to float64 rounding); two blocks, or positions, do not; a later character
changes nothing before it. The short run: with learned positions the bits are lower; the shuffle
shows the same three cases; the model with positions stops past its context and the one without
gets worse past it; and the same seed gives the same bytes again.
"""

import os


def read(path):
    with open(path, "rb") as f:
        return f.read()


def mean(xs):
    return sum(xs) / len(xs)


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "positions", "seeds=2")
    none, learned = ([s["test_bits"] for s in T.summaries(r, f"blocks4-{k}")] for k in ("none", "positions"))
    t.check(mean(learned) < mean(none) - 0.03, f"learned positions should give lower bits: {learned} {none}")
    one = T.value(r.out, r"1 block, no positions +the largest change in a score: (\S+)")
    four = T.value(r.out, r"4 blocks, no positions +the largest change in a score: (\S+)")
    placed = T.value(r.out, r"4 blocks, learned positions +the largest change in a score: (\S+)")
    t.check(one < 1e-10 and four > 1e-3 and placed > 1e-3,
            f"shuffled: one block without positions the same scores, four blocks or positions not: {one} {four} {placed}")
    t.check("ValueError: 128 positions, but there are learned vectors for 32" in r.out,
            f"the model with positions should stop past its context:\n{r.out[-1500:]}")
    first = T.value(r.out, r"n = 4:\s+0 to  31: (\S+)")
    last = T.value(r.out, r"n = 4:.*64 to 127: (\S+)")
    t.check(last > first + 0.1, f"without positions, past the context it should get worse: {first} {last}")
    tiny = ["seeds=2", "steps=20", "layers=2", "orders=2", "longer=[2]"]
    a, b = T.experiment(t, "positions", *tiny), T.experiment(t, "positions", *tiny)
    for run in ("blocks2-none/seed1", "blocks2-positions/seed1"):
        for name in ("log.jsonl", "summary.json"):
            t.check(read(os.path.join(a.runs, run, name)) == read(os.path.join(b.runs, run, name)),
                    f"the same seed twice gave two different {run}/{name}")


def from_gpt2(theirs, layers, width):
    """transformers' GPT-2 weights (its state_dict, "transformer." taken off the names) under our names: the
    mapping 09.03 needs (NOTES.md, For module 09 and after). GPT-2's Conv1D layers keep their weight as
    (inputs, outputs), nn.Linear as (outputs, inputs): each is transposed, the square c_proj too. c_attn
    holds the queries', keys' and values' weights side by side, in that order."""
    out = {"tokens.weight": theirs["wte.weight"], "positions.weight": theirs["wpe.weight"],
           "norm.weight": theirs["ln_f.weight"], "norm.bias": theirs["ln_f.bias"]}
    for i in range(layers):
        h, b = f"h.{i}.", f"blocks.{i}."
        for ours, gpt2 in (("norm1", "ln_1"), ("norm2", "ln_2")):
            out[b + ours + ".weight"], out[b + ours + ".bias"] = theirs[h + gpt2 + ".weight"], theirs[h + gpt2 + ".bias"]
        w, bias = theirs[h + "attn.c_attn.weight"], theirs[h + "attn.c_attn.bias"]
        for j, name in enumerate(("query", "key", "value")):
            out[f"{b}attention.{name}.weight"] = w[:, j * width:(j + 1) * width].T
            out[f"{b}attention.{name}.bias"] = bias[j * width:(j + 1) * width]
        for ours, gpt2 in (("attention.out", "attn.c_proj"), ("mlp.up", "mlp.c_fc"), ("mlp.down", "mlp.c_proj")):
            out[b + ours + ".weight"], out[b + ours + ".bias"] = theirs[h + gpt2 + ".weight"].T, theirs[h + gpt2 + ".bias"]
    return out


def inside(S):
    import numpy as np
    import torch
    from experiments import positions
    from models.gpt import GPT, Positions

    torch.manual_seed(0)
    where = Positions(8, 5).double()
    x = torch.randn(2, 6, 5, dtype=torch.float64)
    assert torch.equal(where(x), x + where.weight[:6]) and where.weight.shape == (8, 5)
    try:
        where(torch.randn(1, 9, 5, dtype=torch.float64))
        raise AssertionError("9 positions with vectors for 8 should be refused")
    except ValueError as e:
        assert "9 positions" in str(e)

    gpt = GPT(65, 12, layers=2, heads=4, width=16).double()
    with torch.no_grad():
        for p in gpt.parameters():
            p.add_(0.3 * torch.randn_like(p))
    ids = torch.randint(0, 65, (2, 12))
    S.same(gpt(ids), S.gpt_numpy(gpt, ids.numpy(), 4), "GPT with positions against numpy", tol=1e-10)
    later = ids.clone()
    later[:, 9] = (later[:, 9] + 1) % 65
    with torch.no_grad():
        assert torch.equal(gpt(ids)[:, :9], gpt(later)[:, :9])
    assert list(dict(gpt.named_parameters()))[:2] == ["tokens.weight", "positions.weight"]

    rng = np.random.default_rng(0)
    for layers, placed, same in ((1, False, True), (2, False, False), (1, True, False)):
        torch.manual_seed(layers)
        model = GPT(65, 12, layers=layers, heads=4, width=16, positions=placed)
        with torch.no_grad():
            for p in model.parameters():
                p.add_(0.3 * torch.randn_like(p))
        worst = positions.shuffled(model, ids[0], 6, rng)
        assert (worst < 1e-12) == same, (layers, placed, worst)
        assert next(model.parameters()).dtype == torch.float32, "shuffled should leave the model as it was"

    try:
        import transformers
    except ImportError:
        print("transformers is not installed: the comparison with GPT-2's own code is left out")
        return
    import warnings
    warnings.filterwarnings("ignore")
    config = transformers.GPT2Config(vocab_size=65, n_positions=12, n_embd=16, n_layer=2, n_head=4, resid_pdrop=0.0,
                                     embd_pdrop=0.0, attn_pdrop=0.0, attn_implementation="eager")
    torch.manual_seed(2)
    reference = transformers.GPT2LMHeadModel(config).double().eval()
    with torch.no_grad():
        for p in reference.parameters():
            p.add_(0.3 * torch.randn_like(p))
    theirs = {k[len("transformer."):]: v for k, v in reference.state_dict().items() if k.startswith("transformer.")}
    ours = GPT(65, 12, layers=2, heads=4, width=16).double()
    ours.load_state_dict(from_gpt2(theirs, 2, 16))
    with torch.no_grad():
        S.same(ours(ids), reference(ids).logits, "our GPT against transformers' GPT2LMHeadModel", tol=1e-10)
