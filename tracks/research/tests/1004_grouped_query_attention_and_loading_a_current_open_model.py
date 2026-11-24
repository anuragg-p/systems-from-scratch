"""10.04 Grouped-query attention, and loading a current open model

SelfAttention with kv_heads equals each query head reading its group's key and value head, written out
(tests/support.py), and PyTorch's F.scaled_dot_product_attention with enable_gqa, and full attention whose
key and value weights repeat each group's; it refuses heads that do not share evenly; GPT(kv_heads=k) has
the weights that saves, is causal, and attention_maps rebuilds its first block. lab/safetensors.py's
bfloat16 is PyTorch's on all 65,536 bit patterns, and load_file reads a BF16 file the safetensors library
wrote. from_smollm puts transformers' LlamaForCausalLM (random weights, a small configuration: 6 heads on 2
key and value heads, rotary base 100000, RMSNorm, SwiGLU, tied, no biases) into GPT with its logits (1e-5,
float32 and float64); without kv_heads the weights do not fit. tokens/smollm.py cuts text as the tokenizers
library's Digits and ByteLevel pre-tokenizers do, and its Tokenizer reads a tokenizer.json written here.
With SmolLM2's files (python3 -m data.fetch smollm2; without them the test fails there with "missing:"
and that command): SmolLM2-135M loaded by models/smollm.py gives transformers' logits, from the same local
file and with no network, to 1e-4 of each logit in float32 (they were identical here, eager attention);
its tokenizer gives the ids of transformers' tokenizer on all of Tiny Shakespeare and an awkward text. The
short run: grouped-query attention within 0.1 bits of every head its own with fewer weights; SmolLM2's
configuration confirmed, its bits per character on the test text below GPT-2's 1.851; and the same
settings give the same bytes again.
"""

import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))


def read(path):
    with open(path, "rb") as f:
        return f.read()


def mean(xs):
    return sum(xs) / len(xs)


def test(t):
    T = t.track
    T.inside(t, __file__)
    T.need(t, "smollm2")    # without the files: "missing:", as 09.03
    out = T.inside(t, __file__, "with_data")
    print("      " + "\n      ".join(line for line in out.splitlines() if line.startswith("10.04")))
    r = T.experiment(t, "smollm")
    full, grouped = ([s["test_bits"] for s in T.summaries(r, k)] for k in ("4 key/value heads", "2 key/value heads"))
    t.check(abs(mean(grouped) - mean(full)) < 0.1, f"grouped-query attention should score near full heads: {grouped} {full}")
    wf, wg = (T.summaries(r, k)[0]["weights"] for k in ("4 key/value heads", "2 key/value heads"))
    t.check(wf - wg == 4 * 2 * (64 * 32 + 32), f"2 key/value heads should save 4 blocks of half their weights: {wf} {wg}")
    s = T.summaries(r, "smollm2")[0]
    t.check(s["test_bits_per_character"] < 1.8 and s["weights"] == 134515008 and s["tokens"] > 17000,
            f"SmolLM2 should be below GPT-2 (1.851) on the test text: {s}")
    t.check("every one as GPT is given it: True" in r.out and "decoded the same: True" in r.out and
            "272 tensors, all BF16" in r.out, f"the configuration and the tokenizer:\n{r.out[:3000]}")
    tiny = ["seeds=1", "steps=4", "layers=1", "width=16", "context=16", "test_tokens=300", "warm=16", "span=49",
            "greedy=4", "prompt_tokens=8", "length=4"]
    a, b = T.experiment(t, "smollm", *tiny), T.experiment(t, "smollm", *tiny)
    for run in ("2 key/value heads/seed0", "smollm2/seed0"):
        t.check(read(os.path.join(a.runs, run, "summary.json")) == read(os.path.join(b.runs, run, "summary.json")),
                f"the same settings twice gave two different {run}/summary.json")


def inside(S):
    import tempfile
    import numpy as np
    import torch
    import torch.nn.functional as F
    from experiments.language import attention_maps
    from lab import safetensors
    from models.gpt import GPT, SelfAttention
    from models.smollm import from_smollm
    from tokens import gpt2, smollm

    torch.manual_seed(0)
    x = torch.randn(2, 9, 12, dtype=torch.float64)
    a = SelfAttention(12, heads=6, kv_heads=2).double()
    assert a.key.weight.shape == a.value.weight.shape == (4, 12) and a.query.weight.shape == (12, 12)
    p = {k: v.numpy() for k, v in a.state_dict().items()}
    S.same(a(x), S.attention10_numpy(x.numpy(), p, "", 6, 2), "SelfAttention, 6 heads on 2, against the loops", tol=1e-12)
    q, k, v = a.qkv(x)
    assert q.shape == k.shape == v.shape == (2, 6, 9, 2) and torch.equal(k[:, 0], k[:, 2]) and torch.equal(v[:, 3], v[:, 5])
    try:
        kk, vv = (f(x).view(2, 9, 2, 2).transpose(1, 2) for f in (a.key, a.value))
        fused = F.scaled_dot_product_attention(q, kk, vv, is_causal=True, enable_gqa=True)
        S.same(a(x), a.out(fused.transpose(1, 2).reshape(2, 9, 12)), "against scaled_dot_product_attention(enable_gqa)",
               tol=1e-12)
    except TypeError:
        print("10.04 this torch's scaled_dot_product_attention has no enable_gqa: not compared")
    full = SelfAttention(12, heads=6).double()
    rows = torch.tensor([2 * (h // 3) + j for h in range(6) for j in range(2)])   # query head h reads key head h // 3
    full.load_state_dict({"query.weight": a.query.weight, "query.bias": a.query.bias, "out.weight": a.out.weight,
                          "out.bias": a.out.bias, "key.weight": a.key.weight[rows], "key.bias": a.key.bias[rows],
                          "value.weight": a.value.weight[rows], "value.bias": a.value.bias[rows]})
    S.same(full(x), a(x), "full heads whose keys and values repeat each group's", tol=1e-12)
    try:
        SelfAttention(12, heads=6, kv_heads=4)
        raise AssertionError("6 query heads on 4 key and value heads should be refused")
    except ValueError:
        pass

    V, ctx, L, W = 65, 16, 2, 16
    base, grouped = GPT(V, ctx, L, 4, W), GPT(V, ctx, L, 4, W, kv_heads=1)
    assert sum(p.numel() for p in base.parameters()) - sum(p.numel() for p in grouped.parameters()) == L * 2 * (W * W + W) * 3 // 4
    grouped = grouped.double()
    with torch.no_grad():
        for p in grouped.parameters():
            p.add_(0.3 * torch.randn_like(p))
    ids = torch.randint(0, V, (2, ctx))
    S.same(grouped(ids), S.gpt10_numpy(grouped, ids.numpy(), 4, kv_heads=1), "GPT(kv_heads=1) against numpy", tol=1e-10)
    later = ids.clone()
    later[:, 9:] = (later[:, 9:] + 1) % V
    with torch.no_grad():
        assert torch.equal(grouped(ids)[:, :9], grouped(later)[:, :9]), "a later character should change nothing before it"
    maps = attention_maps(grouped, ids)
    b0 = grouped.blocks[0].attention
    with torch.no_grad():
        h = grouped.blocks[0].norm1(grouped.embed(ids))
        S.same(b0.out((maps[0] @ b0.qkv(h)[2]).transpose(1, 2).reshape(2, ctx, W)), b0(h), "attention_maps, grouped",
               tol=1e-12)

    bits = np.arange(65536, dtype=np.uint16)
    ours = safetensors.bfloat16(bits)
    theirs = torch.from_numpy(bits.view(np.int16)).view(torch.bfloat16).float().numpy()
    assert ours.dtype == np.float32 and np.array_equal(ours.view(np.uint32), theirs.view(np.uint32)), \
        "bfloat16 should widen every bit pattern as PyTorch does"
    with tempfile.TemporaryDirectory() as d:
        from safetensors.torch import save_file
        made = {"w": torch.randn(3, 5).to(torch.bfloat16), "b": torch.randn(4), "i": torch.arange(6)}
        save_file(made, f"{d}/x.safetensors")
        back = safetensors.load_file(f"{d}/x.safetensors")
        assert back["w"].dtype == np.float32 and np.array_equal(back["w"], made["w"].float().numpy())
        assert np.array_equal(back["b"], made["b"].numpy()) and np.array_equal(back["i"], made["i"].numpy())

    split_against_tokenizers()
    tokenizer_on_a_file(gpt2, smollm)

    try:
        import transformers
    except ImportError:
        print("10.04 transformers is not installed: the comparison with its Llama is left out")
        return
    import warnings
    warnings.filterwarnings("ignore")
    transformers.logging.set_verbosity_error()
    config = transformers.LlamaConfig(vocab_size=70, hidden_size=24, intermediate_size=64, num_hidden_layers=2,
                                      num_attention_heads=6, num_key_value_heads=2, rms_norm_eps=1e-5,
                                      rope_theta=100000.0, max_position_embeddings=32, tie_word_embeddings=True,
                                      attention_bias=False, mlp_bias=False, hidden_act="silu",
                                      attn_implementation="eager")
    torch.manual_seed(1)
    reference = transformers.LlamaForCausalLM(config).eval()
    with torch.no_grad():
        for p in reference.parameters():
            p.add_(0.3 * torch.randn_like(p))
    theirs = {k: v.numpy() for k, v in reference.state_dict().items() if k.startswith("model.")}
    small = dict(vocab=70, context=32, layers=2, heads=6, width=24, dropout=0.0, bias=False, positions="rotary",
                 norm="rms", base=100000.0, mlp="swiglu", hidden=64, kv_heads=2)
    ours = GPT(**small).eval()
    ours.load_state_dict({k: torch.from_numpy(np.ascontiguousarray(v)) for k, v in from_smollm(theirs, 2).items()})
    ids = torch.randint(0, 70, (3, 32))
    with torch.no_grad():
        S.same(ours(ids), reference(ids).logits, "from_smollm: our GPT against transformers' LlamaForCausalLM, float32",
               tol=1e-5)
        S.same(ours.double()(ids), reference.double()(ids).logits, "the same in float64", tol=1e-5)
    try:
        GPT(**{**small, "kv_heads": None}).load_state_dict(
            {k: torch.from_numpy(np.ascontiguousarray(v)) for k, v in from_smollm(theirs, 2).items()})
        raise AssertionError("without kv_heads the key and value weights should not fit")
    except RuntimeError as e:
        assert "size mismatch" in str(e)


def split_against_tokenizers():
    """tokens/smollm.py's split against the tokenizers library's own pre-tokenizers, built here as SmolLM2's
    tokenizer.json names them (Digits with individual_digits, then ByteLevel with its regex): the same pieces on
    09.02's awkward text and 2,000 random strings of characters this Python's Unicode knows."""
    import unicodedata
    import numpy as np
    import support as S
    from tokens import gpt2, smollm
    try:
        from tokenizers import pre_tokenizers as pre
    except ImportError:
        print("10.04 the tokenizers library is not installed: split is not compared with its pre-tokenizers")
        return
    cut = pre.Sequence([pre.Digits(individual_digits=True), pre.ByteLevel(add_prefix_space=False, use_regex=True)])
    symbols = gpt2.byte_symbols()
    pool, _ = S.unicode_pool()
    known = [ch for ch in pool if unicodedata.category(ch) != "Cn"]
    texts = runpy.run_path(os.path.join(HERE, "0902_gpt_2_s_tokenizer_the_same_ids_as_tiktoken.py"))["corpus"]()
    texts += S.unicode_strings(np.random.default_rng(1), 2000, 60, known) + ["Hey 123 friend!", " 2019,  12  ", "\u00bd!"]
    for s in texts:
        ours = ["".join(symbols[b] for b in piece.encode("utf-8")) for piece in smollm.split(s)]
        assert ours == [piece for piece, _ in cut.pre_tokenize_str(s)], ascii(s)
        assert "".join(smollm.split(s)) == s
    assert smollm.split(" in 2019") == [" in", " ", "2", "0", "1", "9"] and gpt2.split(" in 2019") == [" in", " 2019"]


def tokenizer_on_a_file(gpt2, smollm):
    """A tokenizer.json written here: two special symbols, the bytes but 0xc3, three merges; encode and decode, a
    missing byte left out, merges out of order and another way of cutting refused."""
    import json
    import tempfile
    symbols = gpt2.byte_symbols()
    vocab = {"<|endoftext|>": 0, "<|x|>": 1}
    for c in symbols:
        if c != symbols[0xC3]:
            vocab[c] = len(vocab)
    n = len(vocab)
    vocab.update({"ab": n, "abc": n + 1, "\u0120ab": n + 2})
    spec = {"version": "1.0", "normalizer": None, "pre_tokenizer": smollm.Tokenizer.CUTS,
            "added_tokens": [{"id": 0, "content": "<|endoftext|>"}, {"id": 1, "content": "<|x|>"}],
            "model": {"type": "BPE", "vocab": vocab, "merges": ["a b", "ab c", "\u0120 ab"]}}
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "t.json"), "w", encoding="utf-8") as f:
            json.dump(spec, f)
        tok = smollm.Tokenizer(os.path.join(d, "t.json"))
        assert tok.specials == {"<|endoftext|>": 0, "<|x|>": 1} and tok.first[0xC3] is None and tok.first[0xFF] == n - 1
        ids = tok.encode("abc abcab ab 12")
        g = vocab["\u0120"]
        assert ids == [n + 1, g, n + 1, n, n + 2, g, vocab["1"], vocab["2"]], ids
        assert tok.decode(ids) == "abc abcab ab 12" and tok.decode([0]) == "<|endoftext|>"
        assert tok.encode("a\xffb") == [vocab["a"], vocab[symbols[0xBF]], vocab["b"]], "0xc3 0xbf: the 0xc3 is left out"
        assert tok.decode(tok.encode("a\xffb")) == "a\ufffdb"
        for name, change in (("order", {"merges": ["ab c", "a b", "\u0120 ab"]}), ("cut", None)):
            bad = json.loads(json.dumps(spec))
            if change:
                bad["model"].update(change)
            else:
                bad["pre_tokenizer"] = {"type": "ByteLevel", "add_prefix_space": False, "trim_offsets": True,
                                        "use_regex": True}
            with open(os.path.join(d, "bad.json"), "w", encoding="utf-8") as f:
                json.dump(bad, f)
            try:
                smollm.Tokenizer(os.path.join(d, "bad.json"))
                raise AssertionError(f"a tokenizer.json with another {name} should be refused")
            except (ValueError, KeyError):
                pass


def with_data(S):
    import unicodedata
    import warnings
    import numpy as np
    import torch
    from data import fetch, shakespeare
    from models import smollm as M
    from tokens import smollm

    warnings.filterwarnings("ignore")
    import transformers
    transformers.logging.set_verbosity_error()
    folder = os.path.dirname(fetch.path("smollm2", "model.safetensors"))
    ours = M.load(torch.device("cpu"))
    assert sum(p.numel() for p in ours.parameters()) == 134515008 and not ours.training
    reference = transformers.AutoModelForCausalLM.from_pretrained(folder, local_files_only=True, torch_dtype=torch.float32,
                                                                  attn_implementation="eager").eval()
    tok = smollm.load()
    inputs = {"1,024 tokens of Tiny Shakespeare": torch.tensor([tok.encode(shakespeare.load()[:6000])[:1024]]),
              "4 rows of 64 random tokens": torch.randint(0, 49152, (4, 64), generator=torch.Generator().manual_seed(0))}
    with torch.no_grad():
        for name, x in inputs.items():
            a, b = ours(x), reference(x).logits
            S.same(a, b, f"SmolLM2's logits, {name}", tol=1e-4)
            print(f"10.04 {name}: the largest difference from transformers' logits {(a - b).abs().max().item():.3g} "
                  f"(logits up to {b.abs().max().item():.0f})")
    del ours, reference

    theirs = transformers.AutoTokenizer.from_pretrained(folder, local_files_only=True)
    text = shakespeare.load()
    ids = tok.encode(text)
    assert ids == theirs(text, add_special_tokens=False)["input_ids"] and tok.decode(ids) == text
    pool, _ = S.unicode_pool()
    known = [ch for ch in pool if unicodedata.category(ch) != "Cn"]
    texts = runpy.run_path(os.path.join(HERE, "0902_gpt_2_s_tokenizer_the_same_ids_as_tiktoken.py"))["corpus"]()
    texts += S.unicode_strings(np.random.default_rng(0), 3000, 60, known) + ["x\U00040000y", "a\x04b", " in 2019"]
    lost = 0
    for s in texts:
        got = tok.encode(s)
        assert got == theirs(s, add_special_tokens=False, split_special_tokens=True)["input_ids"], ascii(s)
        if tok.decode(got) != s:
            lost += 1
            assert any(tok.first[b] is None for b in s.encode("utf-8")), ascii(s)
    print(f"10.04 the same ids as transformers' {type(theirs).__name__} on Tiny Shakespeare ({len(ids):,} tokens) and "
          f"{len(texts):,} awkward strings; {lost} of them do not decode back, each holding a byte SmolLM2 has no symbol for")
