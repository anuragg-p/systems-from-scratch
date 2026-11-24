"""Loading GPT-2: OpenAI's weights in the GPT of module 08, and what the real model does.

1. GPT-2 small read from its file (lab/safetensors.py) into models/gpt.py's
   GPT, renamed and transposed (models/gpt2.py): what it expects next.
2. The mapping matters: with one square weight left the wrong way round
   the file still loads, without a complaint, and the model is ruined.
3. Bits per character on Tiny Shakespeare's test text, a model we never
   trained on it, beside module 07's ladder and 08.04's GPT.
4. 08.05's measurements again, on the real model and on word pieces, as
   Holtzman et al. (2020) made them with GPT-2 Large: greedy, sampling,
   temperature, top-k and the nucleus; the model's perplexity of what it
   wrote beside its perplexity of the text, and how often it loops.

    python3 -m experiments.gpt2

Needs GPT-2's files: python3 -m data.fetch gpt2 (549 MB, once).
"""

import time

import numpy as np
import torch
import torch.nn.functional as F

import lab
from data import fetch, shakespeare
from experiments.language import generate, loops
from experiments.sequences import bits, per_character, window_bits
from lab import safetensors
from models.gpt import GPT
from models.gpt2 import CONFIG as GPT2
from models.gpt2 import from_gpt2
from tokens import gpt2

CONFIG = dict(warm=64, prompt="The meaning of life is", hello="Hello, I'm a language model,", shown=5, greedy=20,
              wrong_windows=2, test_tokens=0, prompts=8, prompt_tokens=16, length=40, seeds=2,
              methods=[["greedy", 0.0, 0, None], ["pure sampling", 1.0, 0, None], ["sampling, t=0.9", 0.9, 0, None],
                       ["sampling, t=0.7", 0.7, 0, None], ["top-k=40", 1.0, 40, None], ["nucleus, p=0.95", 1.0, 0, 0.95]],
              device="cpu")
# Test bits per character from modules 07 and 08 (their pages; 07's count models are 08.04's ladder, computed again).
LADDER = [("every character equally likely (07.01)", 6.022), ("pairs (07.01)", 3.599),
          ("deleted interpolation, contexts up to 7 (07.02)", 2.409),
          ("07.02's network, its long run", 2.346), ("07.02's network and interpolation, mixed (long run, 8)", 2.283),
          ("08.04's GPT, its long run (dropout 0.2)", 2.226)]


# @build 09.03 perplexity
# The model's perplexity of continuations after their prompts ((batch, n)
# and (batch, P), the two together inside its window): 2 to its bits per
# token of every continuation token, each read with its prompt and the
# continuation before it.
def perplexity(model, prompts, continuations):
    rows = torch.cat([prompts, continuations], dim=1)
    with torch.no_grad():
        scores = model(rows[:, :-1])[:, prompts.shape[1] - 1:]
    return 2 ** bits(scores, continuations).item()
# @end


def speeches(tok, test_text, n, prompt, length):
    """n speeches of the test text (the text after a blank line), evenly spread, as tokens: each one's first
    prompt tokens and the length after them."""
    starts = [i + 2 for i in range(len(test_text) - 2) if test_text[i:i + 2] == "\n\n"]
    rows = []
    for s in starts[::max(1, len(starts) // (4 * n))]:
        ids = tok.encode(test_text[s:s + 40 * (prompt + length)])
        if len(ids) >= prompt + length:
            rows.append(ids[:prompt + length])
    picked = [rows[int(j)] for j in np.linspace(0, len(rows) - 1, n)]
    return torch.tensor(picked)


def main():
    cfg = lab.config(CONFIG)
    dev = lab.device(torch, cfg.device)
    fetch.need("gpt2")
    tok = gpt2.load()
    start = lab.clock(torch, dev)
    tensors = safetensors.load_file(fetch.path("gpt2", "model.safetensors"))
    model = GPT(**GPT2)
    model.load_state_dict({name: torch.from_numpy(a) for name, a in from_gpt2(tensors, 12, 768).items()})
    model.to(dev).eval()
    loaded = lab.clock(torch, dev) - start
    size = sum(p.numel() for p in model.parameters())
    print(f"1. GPT-2 small: {len(tensors)} tensors read from its file, {size:,} weights in GPT(vocab=50257, "
          f"context=1024, layers=12,\n   heads=12, width=768), {loaded:.1f} s. After {cfg.prompt!r}, its "
          f"{cfg.shown} likeliest next tokens:")
    with torch.no_grad():
        chances = F.softmax(model(torch.tensor([tok.encode(cfg.prompt)], device=dev))[0, -1], dim=-1)
    top = chances.topk(cfg.shown)
    print("   " + "   ".join(f"{tok.decode([int(i)])!r} {p:.3f}" for p, i in zip(top.values.tolist(), top.indices.tolist())))
    drawn = generate(model, torch.tensor([tok.encode(cfg.hello)], device=dev), cfg.greedy, None, temperature=0)
    print(f"   Greedy, {cfg.greedy} tokens: {cfg.hello + tok.decode(drawn[0].tolist())!r}")

    text = shakespeare.load()
    test_text = text[int(0.95 * len(text)):]
    test = torch.tensor(tok.encode(test_text), device=dev)
    if cfg.test_tokens:
        test = test[:cfg.test_tokens]
    span = GPT2["context"] - cfg.warm + 1
    first = test[:cfg.wrong_windows * span + cfg.warm]
    right = per_character(window_bits(model, first, span, cfg.warm, batch=4), first.tolist(), tok.table, cfg.warm)
    wrong = from_gpt2(tensors, 12, 768)
    for i in range(12):
        wrong[f"blocks.{i}.attention.out.weight"] = tensors[f"h.{i}.attn.c_proj.weight"]
    model.load_state_dict({name: torch.from_numpy(a) for name, a in wrong.items()})
    ruined = per_character(window_bits(model, first, span, cfg.warm, batch=4), first.tolist(), tok.table, cfg.warm)
    model.load_state_dict({name: torch.from_numpy(a) for name, a in from_gpt2(tensors, 12, 768).items()})
    del tensors, wrong
    print(f"\n2. attn.c_proj, a square 768 x 768 weight in each block, left as the file has it: it loads, no complaint;\n"
          f"   on the first {len(first):,} tokens of the test text it scores {ruined:.3f} bits per character, against "
          f"{right:.3f} transposed.")

    b = window_bits(model, test, span, cfg.warm, batch=4)
    ours = per_character(b, test.tolist(), tok.table, cfg.warm)
    lab.Run(cfg, 0, label="scores").finish(test_bits_per_token=b, test_bits_per_character=ours, tokens=len(test),
                                           right_bits_per_character=right, wrong_bits_per_character=ruined)
    print(f"\n3. Tiny Shakespeare's test text, {len(test_text):,} characters, {len(test):,} GPT-2 tokens ("
          f"{len(test_text) / len(test):.2f} characters a token).\n   GPT-2, each token read with {cfg.warm} or more before "
          f"it (windows of {GPT2['context']}): {b:.3f} bits per token, {ours:.3f} bits per character.\n"
          f"   Beside the track's own models, each character with 64 or more before it:")
    for name, value in LADDER:
        print(f"   {name:58s} {value:.3f}")
    print(f"   {'GPT-2 small, never trained on this text by us':58s} {ours:.3f}")

    text_rows = speeches(tok, test_text, cfg.prompts, cfg.prompt_tokens, cfg.length).to(dev)
    prompts, human = text_rows[:, :cfg.prompt_tokens], text_rows[:, cfg.prompt_tokens:]
    print(f"\n4. {cfg.prompts} prompts of {cfg.prompt_tokens} tokens (starts of speeches in the test text), {cfg.length} "
          f"tokens after each, {cfg.seeds} seeds of the sampling.\n   Perplexity: 2 to the model's bits per token; "
          f"repetition: the passages that end in a phrase repeated 3 times or more.\n")
    print(f"   {'':18s} {'perplexity':45s} repetition")
    people, looping = perplexity(model, prompts, human), 100 * lab.mean([loops(r.tolist()) for r in human])
    lab.Run(cfg, 0, label="text").finish(perplexity=[people], repetition=[looping])
    print(f"   {'the text itself':18s} {people:<45.4g} {looping:5.1f}%")
    shown = {}
    for name, temperature, k, p in cfg.methods:
        values, repetition = [], []
        for seed in range(cfg.seeds if temperature else 1):
            drawn = generate(model, prompts, cfg.length, torch.Generator().manual_seed(seed), temperature, k, p)
            values.append(perplexity(model, prompts, drawn))
            repetition.append(100 * lab.mean([loops(r.tolist()) for r in drawn]))
            if seed == 0:
                shown[name] = drawn[0]
        lab.Run(cfg, 0, label=name.replace(", ", "-").replace("=", "").replace(" ", "_")).finish(
            perplexity=values, repetition=repetition)
        spread = lab.spread(values, 4) if temperature else f"{values[0]:.4g} (no chance in it)"
        print(f"   {name:18s} {spread:45s} {lab.mean(repetition):5.1f}% ({', '.join(f'{r:.0f}' for r in repetition)})")
    print(f"\n   Prompt 1: {tok.decode(prompts[0].tolist())!r}\n   the text:          {tok.decode(human[0].tolist())!r}")
    for name, drawn in shown.items():
        print(f"   {name + ':':18s} {tok.decode(drawn.tolist())!r}")
    print(f"\n{lab.clock(torch, dev) - start:.0f} s of loading, scoring and sampling on {dev.type}")


if __name__ == "__main__":
    main()
