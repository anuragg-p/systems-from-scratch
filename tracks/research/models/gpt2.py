"""GPT-2 small in models/gpt.py's GPT: OpenAI's published weights, renamed and transposed (09.03).

    CONFIG                             GPT-2 small's settings, as GPT's arguments
    from_gpt2(tensors, layers, width)  the tensors of GPT-2's file under GPT's names, in GPT's shapes
    load(dev, path)                    GPT(**CONFIG) holding GPT-2's weights, in eval mode

GPT was shaped in module 08 so that these weights fit it: the same
layers in the same order, GPT-2's GELU, layer norms before attention
and the MLP, a last layer norm, learned positions, and the output tied
to the embedding. What differs is only how the file keeps them: its own
names (wte, h.0.attn.c_attn, ...), the queries', keys' and values'
weights side by side in one tensor, and every weight of a Linear layer
transposed. NOTES.md has the table, read from the file's own header.
"""

import torch

from data import fetch
from lab import safetensors
from models.gpt import GPT

CONFIG = dict(vocab=50257, context=1024, layers=12, heads=12, width=768, dropout=0.0, bias=True, positions=True)


# @build 09.03 from_gpt2
# GPT-2's tensors (a dict of numpy arrays, named as in its file) under
# GPT's names. The embeddings and the layer norms are as they are. GPT-2
# computes x @ W + b with W kept as (inputs, outputs), nn.Linear x @ W.T +
# b with W as (outputs, inputs): so every Linear weight is transposed, the
# square attn.c_proj too, which would load the wrong way round without a
# complaint. c_attn holds the queries', keys' and values' weights and
# biases side by side, in that order. h.i.attn.bias is not a bias but the
# causal mask, a table of ones and zeros GPT makes for itself: left out.
def from_gpt2(tensors, layers, width):
    out = {"tokens.weight": tensors["wte.weight"], "positions.weight": tensors["wpe.weight"],
           "norm.weight": tensors["ln_f.weight"], "norm.bias": tensors["ln_f.bias"]}
    for i in range(layers):
        h, b = f"h.{i}.", f"blocks.{i}."
        for ours, theirs in (("norm1", "ln_1"), ("norm2", "ln_2")):
            out[b + ours + ".weight"], out[b + ours + ".bias"] = tensors[h + theirs + ".weight"], tensors[h + theirs + ".bias"]
        w, bias = tensors[h + "attn.c_attn.weight"], tensors[h + "attn.c_attn.bias"]
        for j, name in enumerate(("query", "key", "value")):
            out[f"{b}attention.{name}.weight"] = w[:, j * width:(j + 1) * width].T
            out[f"{b}attention.{name}.bias"] = bias[j * width:(j + 1) * width]
        for ours, theirs in (("attention.out", "attn.c_proj"), ("mlp.up", "mlp.c_fc"), ("mlp.down", "mlp.c_proj")):
            out[b + ours + ".weight"], out[b + ours + ".bias"] = tensors[h + theirs + ".weight"].T, tensors[h + theirs + ".bias"]
    return out
# @end


# @build 09.03 load
# GPT-2 small on the device dev, in eval mode: GPT(**CONFIG), and the
# weights of the file at path (by default the one data/fetch.py keeps; the
# script stops with the fetch command when it is not there), read by
# lab/safetensors.py and put in by from_gpt2. load_state_dict refuses a
# missing name, one too many, or a shape that does not fit.
def load(dev, path=None):
    if path is None:
        fetch.need("gpt2")
        path = fetch.path("gpt2", "model.safetensors")
    model = GPT(**CONFIG)
    tensors = from_gpt2(safetensors.load_file(path), CONFIG["layers"], CONFIG["width"])
    model.load_state_dict({name: torch.from_numpy(a) for name, a in tensors.items()})
    return model.to(dev).eval()
# @end
