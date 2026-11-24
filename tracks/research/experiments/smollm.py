"""Grouped-query attention, and loading a current open model.

Every head of 08.02's attention has its own queries, keys and values.
Ainslie et al. (2023) let a group of query heads share one key head and
one value head (models/gpt.py, SelfAttention's kv_heads): "Grouped-query
attention divides query heads into G groups, each of which shares a
single key head and value head." Their reason is speed when writing:
each new token reads every key and value kept so far, and fewer heads
of them is less to read ("reducing the size of the key-value cache and
therefore amount of data that needs to be loaded"); their claim, for a
multi-head model given grouped heads and trained a little more, "uptrained
GQA achieves quality close to multi-head attention with comparable speed
to MQA" (one key head for all, multi-query). Here the heads are grouped
from the start. Then a model of today that
has every piece of module 10: SmolLM2-135M (Allal et al. 2025), its
published weights in our GPT (models/smollm.py) and its tokenizer
(tokens/smollm.py).

1. 08.04's GPT with 4 query heads on 4 (every head its own), then fewer,
   key and value heads: weights, the numbers a token leaves behind to be
   read later, bits per character on the test text, ms a training step.
2. SmolLM2-135M's config.json beside GPT's arguments; its file read
   (bfloat16, widened to float32) into GPT; what it expects next.
3. Its tokenizer beside GPT-2's: the pieces, the vocabulary, the special
   symbols, bytes a token on the test text.
4. Bits per character on Tiny Shakespeare's test text beside GPT-2's
   and 08.04's GPT, with the weights of each.
5. A passage after a prompt from the test text, with 08.05's samplers.

    python3 -m experiments.smollm

Parts 2 to 5 need SmolLM2's files: python3 -m data.fetch smollm2 (271 MB, once).
"""

import json

import torch
import torch.nn.functional as F

import lab
from data import fetch, shakespeare
from experiments.language import compare, generate
from experiments.sequences import per_character, window_bits
from lab import safetensors
from models import smollm
from models.gpt import GPT
from tokens import smollm as tokens

CONFIG = dict(layers=4, heads=4, width=64, context=64, batch=32, steps=150, lr=0.003, warmup=50, weight_decay=0.1,
              clip=1.0, every=50, seeds=3, kv=[4, 2], prompt="To be, or not to be,", shown=5, greedy=16, warm=64,
              span=961, test_tokens=0, prompt_tokens=16, length=40,
              methods=[["greedy", 0.0, 0, None], ["top-k=40", 1.0, 40, None], ["nucleus, p=0.95", 1.0, 0, 0.95]],
              device="cpu")
# Test bits per character, from the track's own runs (their pages), and the weights of each model.
OTHERS = [("08.04's GPT, its long run (dropout 0.2)", 2.226, 2731200), ("GPT-2 small (09.03)", 1.851, 124439808)]
GPT2_BYTES_PER_TOKEN = 3.099              # 09.02: GPT-2's tokenizer on Tiny Shakespeare's test text
# config.json's names for GPT's arguments (models/smollm.py's CONFIG).
NAMES = [("hidden_size", "width"), ("num_hidden_layers", "layers"), ("num_attention_heads", "heads"),
         ("num_key_value_heads", "kv_heads"), ("intermediate_size", "hidden"), ("rope_theta", "base"),
         ("vocab_size", "vocab"), ("max_position_embeddings", "context")]


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    V = len(shakespeare.chars())
    train_t, test_t = (torch.from_numpy(shakespeare.split(s)).to(dev) for s in ("train", "test"))
    start = lab.clock(torch, dev)

    variants = {f"{k} key/value heads": {"kv_heads": k} for k in cfg.kv}
    common = dict(vocab=V, context=cfg.context, layers=cfg.layers, heads=cfg.heads, width=cfg.width)
    got = compare(variants, common, cfg, dev, train_t, test_t)
    d = cfg.width // cfg.heads
    print(f"1. 08.04's GPT ({cfg.layers} blocks of {cfg.heads} query heads of {d} numbers, windows of {cfg.context}), "
          f"{cfg.steps} steps of {cfg.batch}, {cfg.seeds} seeds;\n   kept a token: the keys and values each block "
          f"keeps of it for later tokens to read; bits per character on the test text:")
    first = got[next(iter(variants))]
    for (name, r), k in zip(got.items(), cfg.kv):
        print(f"   {name:19s} {r['weights']:>9,} weights   kept a token {2 * k * d * cfg.layers:4d}   "
              f"bits {lab.spread(r['bits'], 4)}\n   {'':55s}ms a step {lab.spread(r['ms'], 3)}")
        if r is not first:
            print(f"   {'':19s} against {cfg.kv[0]}: bits {lab.mean(r['bits']) - lab.mean(first['bits']):+.4f}, "
                  f"t = {lab.welch_t(r['bits'], first['bits']):+.1f}; time a step "
                  f"x{lab.mean(r['ms']) / lab.mean(first['ms']):.3f}; {first['weights'] - r['weights']:,} weights fewer")

    fetch.need("smollm2")
    with open(fetch.path("smollm2", "config.json")) as f:
        theirs = json.load(f)
    C = smollm.CONFIG
    print(f"\n2. SmolLM2-135M. Its config.json ({theirs['architectures'][0]}) beside GPT's arguments "
          f"(models/smollm.py):")
    for a, b in NAMES:
        print(f"   {a:24s} {theirs[a]:>8}   {b}={C[b]!r}")
    print(f"   {'rms_norm_eps':24s} {theirs['rms_norm_eps']:>8}   norm={C['norm']!r} (RMSNorm's eps 1e-05)\n"
          f"   {'hidden_act':24s} {theirs['hidden_act']:>8}   mlp={C['mlp']!r}\n"
          f"   {'rope_interleaved':24s} {str(theirs['rope_interleaved']):>8}   positions={C['positions']!r} "
          f"(pairs i and i + d / 2)\n"
          f"   {'attention_bias':24s} {str(theirs['attention_bias']):>8}   bias={C['bias']!r}\n"
          f"   {'tie_word_embeddings':24s} {str(theirs['tie_word_embeddings']):>8}   (GPT's output is its embedding)")
    same = all(theirs[a] == C[b] for a, b in NAMES) and theirs["rms_norm_eps"] == 1e-5 and theirs["hidden_act"] == "silu"
    print(f"   every one as GPT is given it: {same}")
    clock = lab.clock(torch, dev)
    path = fetch.path("smollm2", "model.safetensors")
    header, _ = safetensors.read_header(path)
    model = smollm.load(dev)
    loaded = lab.clock(torch, dev) - clock
    kinds = sorted({v["dtype"] for k, v in header.items() if k != "__metadata__"})
    size = sum(p.numel() for p in model.parameters())
    print(f"   {len(header) - 1} tensors, all {', '.join(kinds)}, read and widened to float32; {size:,} weights in "
          f"GPT; {loaded:.1f} s.\n   Its keys and values: {C['kv_heads']} heads of {C['width'] // C['heads']} for "
          f"{C['heads']} query heads, {2 * C['kv_heads'] * C['width'] // C['heads'] * C['layers']:,} numbers kept a "
          f"token where 9 would keep {2 * C['width'] * C['layers']:,}")
    tok = tokens.load()
    with torch.no_grad():
        chances = F.softmax(model(torch.tensor([tok.encode(cfg.prompt)], device=dev))[0, -1], dim=-1)
    top = chances.topk(cfg.shown)
    print(f"   After {cfg.prompt!r}, its {cfg.shown} likeliest next tokens:\n   " +
          "   ".join(f"{tok.decode([int(i)])!r} {p:.3f}" for p, i in zip(top.values.tolist(), top.indices.tolist())))
    drawn = generate(model, torch.tensor([tok.encode(cfg.prompt)], device=dev), cfg.greedy, None, temperature=0)
    print(f"   Greedy, {cfg.greedy} tokens: {cfg.prompt + tok.decode(drawn[0].tolist())!r}")

    text = shakespeare.load()
    test_text = text[int(0.95 * len(text)):]
    ids = tok.encode(test_text)
    missing = [b for b in range(256) if tok.first[b] is None]
    print(f"\n3. Its tokenizer (tokenizer.json): {len(tok.table):,} symbols: {len(tok.specials)} special ("
          f"{', '.join(list(tok.specials)[:3])}, ...),\n   {256 - len(missing)} of the 256 bytes (none for "
          f"{', '.join(f'{b:#04x}' for b in missing[:8])}, ... {len(missing)} in all), {len(tok.merges):,} merges. "
          f"GPT-2's: 50,257, 1 special, 256 bytes, 50,000 merges.")
    for s in (" in 2019, 1234567890", "x\U00040000y"):
        print(f"   {s!r}: pieces {tokens.split(s)}, tokens {tok.encode(s)}, decoded {tok.decode(tok.encode(s))!r}")
    print(f"   The test text, {len(test_text):,} characters: {len(ids):,} tokens, {len(test_text) / len(ids):.3f} bytes "
          f"a token (GPT-2's {GPT2_BYTES_PER_TOKEN}); decoded the same: {tok.decode(ids) == test_text}")

    test = torch.tensor(ids[:cfg.test_tokens] if cfg.test_tokens else ids, device=dev)
    b = window_bits(model, test, cfg.span, cfg.warm, batch=4)
    ours = per_character(b, test.tolist(), tok.table, cfg.warm)
    lab.Run(cfg, 0, label="smollm2").finish(test_bits_per_token=b, test_bits_per_character=ours, tokens=len(test),
                                            weights=size)
    print(f"\n4. Bits on the test text, each token read with {cfg.warm} or more before it (windows of "
          f"{cfg.span + cfg.warm - 1}): {b:.3f} a token, {ours:.3f} a character. Beside:")
    for name, value, n in OTHERS:
        print(f"   {name:42s} {value:.3f}   {n:>11,} weights")
    print(f"   {'SmolLM2-135M':42s} {ours:.3f}   {size:>11,} weights")

    starts = [i + 2 for i in range(len(test_text) - 2) if test_text[i:i + 2] == "\n\n"]
    prompt = torch.tensor([tok.encode(test_text[starts[len(starts) // 2]:])[:cfg.prompt_tokens]], device=dev)
    print(f"\n5. After {tok.decode(prompt[0].tolist())!r} (a speech of the test text), {cfg.length} tokens, seed 0:")
    for name, temperature, k, p in cfg.methods:
        drawn = generate(model, prompt, cfg.length, torch.Generator().manual_seed(0), temperature, k, p)
        print(f"   {name + ':':17s} {tok.decode(drawn[0].tolist())!r}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of training, loading, scoring and sampling on {dev.type}")


if __name__ == "__main__":
    main()
