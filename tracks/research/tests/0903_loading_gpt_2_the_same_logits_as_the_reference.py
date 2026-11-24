"""09.03 Loading GPT-2: the same logits as the reference

lab/safetensors.py's load_file reads a large file in place, holding about one copy of it (a file
of 96 MB, measured in a fresh python), and still refuses a bad file; from_gpt2 puts transformers'
GPT-2 weights (a small configuration, random weights) into GPT with the logits of transformers'
GPT2LMHeadModel to 1e-10 in float64; a square weight left untransposed loads and gives other
logits, a non-square one is refused; loops and perplexity against direct computations. With
GPT-2's files (python3 -m data.fetch gpt2; without them the rest is skipped, with a line that says
so): GPT-2 small loaded by models/gpt2.py gives transformers' logits, from the same local file and
with no network, to 1e-4 of each logit in float32 (they were identical here, eager attention), and
without the transpose of attn.c_proj they are far off. The short run: the wrong mapping ruins the
bits, GPT-2's bits per character on the test text are below 08.04's GPT's, greedy text is far
likelier to the model than sampled text and loops, a lower temperature, top-k and the nucleus are
likelier than pure sampling; and the same settings give the same bytes again.
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
    big = os.path.join(t.tmp, "big.safetensors")
    T.py(t, ["-c", f"import numpy as np\nfrom lab import safetensors\nsafetensors.save_file({{'a': np.ones((4000, 6000), "
                   f"np.float32), 'b': np.arange(10, dtype=np.float32)}}, {big!r})"])
    T.py(t, ["-c", MEMORY.format(path=big)])
    os.remove(big)
    if not T.need(t, "gpt2", skip=True):
        return
    out = T.inside(t, __file__, "with_data")
    print("      " + "\n      ".join(line for line in out.splitlines() if line.startswith("09.03")))
    r = T.experiment(t, "gpt2")
    scores = T.summaries(r, "scores")[0]
    t.check(scores["wrong_bits_per_character"] > scores["right_bits_per_character"] + 1,
            f"attn.c_proj untransposed should ruin the model: {scores}")
    t.check(scores["test_bits_per_character"] < 2.0 and scores["tokens"] > 17000,
            f"GPT-2 should be well below 08.04's GPT (2.226) on the test text: {scores}")
    ppl = {k: mean(T.summaries(r, k)[0]["perplexity"]) for k in ("text", "greedy", "pure_sampling", "sampling-t0.7",
                                                                  "top-k40", "nucleus-p0.95")}
    t.check(ppl["greedy"] < ppl["pure_sampling"] / 4 and mean(T.summaries(r, "greedy")[0]["repetition"]) >= 25,
            f"greedy: far likelier to the model than sampling, and looping: {ppl}")
    for k in ("sampling-t0.7", "top-k40", "nucleus-p0.95"):
        t.check(ppl[k] < ppl["pure_sampling"], f"{k}: likelier to the model than pure sampling: {ppl}")
    t.check("loads, no complaint" in r.out and "' not' 0.109" in r.out, f"what the model expects:\n{r.out[:1200]}")
    tiny = ["test_tokens=300", "warm=16", "wrong_windows=1", "prompts=2", "prompt_tokens=8", "length=6", "seeds=1",
            "greedy=4"]
    a, b = T.experiment(t, "gpt2", *tiny), T.experiment(t, "gpt2", *tiny)
    for run in ("scores/seed0", "greedy/seed0", "nucleus-p0.95/seed0"):
        t.check(read(os.path.join(a.runs, run, "summary.json")) == read(os.path.join(b.runs, run, "summary.json")),
                f"the same settings twice gave two different {run}/summary.json")


# load_file on a file of 96 MB written by another python, in a fresh python: what the process holds at its peak,
# beyond what it held before, must be about one copy of the file (it was four copies before 09.03: 2.1 GB for
# GPT-2's 548 MB).
MEMORY = """
import os, resource, sys
import numpy as np
from lab import safetensors
unit = 1 if sys.platform == "darwin" else 1024
size = os.path.getsize({path!r})
before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit
got = safetensors.load_file({path!r})
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit
assert got["a"].sum() == 24e6 and got["b"][-1] == 9 and got["a"].flags.writeable
assert peak - before < 1.3 * size, f"load_file held {{(peak - before) / size:.2f}} times the file at its peak"
print(f"{{(peak - before) / size:.2f}}")
"""


def inside(S):
    import tempfile
    import numpy as np
    import torch
    from experiments.language import loops
    from experiments.gpt2 import perplexity
    from lab import safetensors
    from models.gpt import GPT
    from models.gpt2 import from_gpt2

    with tempfile.TemporaryDirectory() as d:
        arrays = {"z": np.arange(12, dtype=np.float64).reshape(3, 4), "a": np.array([1, 2], np.int64),
                  "m": np.array([True, False]), "e": np.zeros((0, 2), np.float32)}
        safetensors.save_file(arrays, f"{d}/x.safetensors")
        back = safetensors.load_file(f"{d}/x.safetensors")
        assert set(back) == set(arrays) and all(np.array_equal(back[k], v) and back[k].dtype == v.dtype
                                                for k, v in arrays.items())
        raw = read(f"{d}/x.safetensors")
        for bad in (raw[:-3], raw + b"\0" * 8, raw[:6]):
            with open(f"{d}/bad.safetensors", "wb") as f:
                f.write(bad)
            try:
                safetensors.load_file(f"{d}/bad.safetensors")
                raise AssertionError(f"a bad file of {len(bad)} bytes should be refused")
            except ValueError:
                pass

    assert loops([1, 2, 1, 2, 1, 2]) and loops([5, 1, 2, 3, 1, 2, 3, 1, 2, 3]) and not loops([1, 2, 1, 2, 3])
    assert not loops([7, 7]) and not loops([])

    torch.manual_seed(0)
    small = GPT(70, 16, layers=2, heads=2, width=8).double().eval()
    prompts, more = torch.randint(0, 70, (3, 5)), torch.randint(0, 70, (3, 6))
    rows = torch.cat([prompts, more], 1)
    with torch.no_grad():
        logp = torch.log_softmax(small(rows), -1)
    want = -sum(logp[b, 4 + i, more[b, i]].item() for b in range(3) for i in range(6)) / 18 / np.log(2)
    assert abs(perplexity(small, prompts, more) - 2 ** want) < 1e-9 * 2 ** want

    try:
        import transformers
    except ImportError:
        print("09.03 transformers is not installed: the comparison with GPT-2's own code is left out")
        return
    import warnings
    warnings.filterwarnings("ignore")
    config = transformers.GPT2Config(vocab_size=70, n_positions=16, n_embd=12, n_layer=2, n_head=3, resid_pdrop=0.0,
                                     embd_pdrop=0.0, attn_pdrop=0.0, attn_implementation="eager")
    torch.manual_seed(1)
    reference = transformers.GPT2LMHeadModel(config).double().eval()
    with torch.no_grad():
        for p in reference.parameters():
            p.add_(0.3 * torch.randn_like(p))
    theirs = {k[len("transformer."):]: v.numpy() for k, v in reference.state_dict().items() if k.startswith("transformer.")}
    ids = torch.randint(0, 70, (2, 16))
    ours = GPT(70, 16, layers=2, heads=3, width=12).double().eval()
    ours.load_state_dict({k: torch.from_numpy(np.ascontiguousarray(v)) for k, v in from_gpt2(theirs, 2, 12).items()})
    with torch.no_grad():
        S.same(ours(ids), reference(ids).logits, "from_gpt2: our GPT against transformers' GPT2LMHeadModel", tol=1e-10)
    wrong = from_gpt2(theirs, 2, 12)
    wrong["blocks.1.attention.out.weight"] = theirs["h.1.attn.c_proj.weight"]
    ours.load_state_dict({k: torch.from_numpy(np.ascontiguousarray(v)) for k, v in wrong.items()})
    with torch.no_grad():
        assert (ours(ids) - reference(ids).logits).abs().max() > 1e-3, "a square weight untransposed loads, and is wrong"
    wrong = from_gpt2(theirs, 2, 12)
    wrong["blocks.0.mlp.up.weight"] = theirs["h.0.mlp.c_fc.weight"]
    try:
        ours.load_state_dict({k: torch.from_numpy(np.ascontiguousarray(v)) for k, v in wrong.items()})
        raise AssertionError("a non-square weight untransposed should be refused")
    except RuntimeError as e:
        assert "size mismatch" in str(e)


def with_data(S):
    import tempfile
    import warnings
    import numpy as np
    import torch
    from data import fetch, shakespeare
    from lab import safetensors
    from models import gpt2 as M
    from models.gpt import GPT
    from tokens import gpt2

    warnings.filterwarnings("ignore")
    import transformers
    transformers.logging.set_verbosity_error()
    path = fetch.path("gpt2", "model.safetensors")
    ours = M.load(torch.device("cpu"))
    assert sum(p.numel() for p in ours.parameters()) == 124439808 and not ours.training
    with tempfile.TemporaryDirectory() as d:
        transformers.GPT2Config().save_pretrained(d)
        os.symlink(path, os.path.join(d, "model.safetensors"))
        reference = transformers.GPT2LMHeadModel.from_pretrained(d, local_files_only=True,
                                                                attn_implementation="eager").eval()
    tok = gpt2.load()
    inputs = {"1,024 tokens of Tiny Shakespeare": torch.tensor([tok.encode(shakespeare.load()[:6000])[:1024]]),
              "4 rows of 64 random tokens": torch.randint(0, 50257, (4, 64), generator=torch.Generator().manual_seed(0))}
    with torch.no_grad():
        for name, x in inputs.items():
            a, b = ours(x), reference(x).logits
            S.same(a, b, f"GPT-2's logits, {name}", tol=1e-4)
            print(f"09.03 {name}: the largest difference from transformers' logits {(a - b).abs().max().item():.3g} "
                  f"(logits up to {b.abs().max().item():.0f})")
    tensors = safetensors.load_file(path)
    wrong = M.from_gpt2(tensors, 12, 768)
    for i in range(12):
        wrong[f"blocks.{i}.attention.out.weight"] = tensors[f"h.{i}.attn.c_proj.weight"]
    bad = GPT(**M.CONFIG).eval()
    bad.load_state_dict({k: torch.from_numpy(v) for k, v in wrong.items()})
    x = inputs["4 rows of 64 random tokens"]
    with torch.no_grad():
        far = (bad(x) - reference(x).logits).abs().max().item()
    assert far > 10, f"without the transpose of attn.c_proj the logits should be far off: {far}"
    print(f"09.03 without the transpose of attn.c_proj: the largest difference {far:.3g}")
