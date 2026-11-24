"""SmolLM2-135M in models/gpt.py's GPT: Hugging Face's published weights, renamed (10.04).

    CONFIG                          SmolLM2-135M's settings, as GPT's arguments
    from_smollm(tensors, layers)    the tensors of its file under GPT's names
    load(dev, path)                 GPT(**CONFIG) holding SmolLM2's weights, in eval mode

SmolLM2 (Allal et al. 2025) is a Llama: every piece module 10 adds to
GPT is in it, and nothing else is. Its config.json, read beside the
reference code (transformers' models/llama), gives the arguments:

    hidden_size 576, num_hidden_layers 30          width=576, layers=30
    num_attention_heads 9, num_key_value_heads 3   heads=9, kv_heads=3 (10.04): 64 numbers a head
    rms_norm_eps 1e-05                             norm="rms" (10.01), RMSNorm's eps
    rope_theta 100000, rope_interleaved false      positions="rotary", base=100000.0 (10.02): pairs i, i + 32
    hidden_act "silu", intermediate_size 1536      mlp="swiglu", hidden=1536 (10.03): 8 x 576 / 3
    attention_bias false (and no other bias)       bias=False
    tie_word_embeddings true                       GPT's output is its embedding (08.02)
    vocab_size 49152, max_position_embeddings 8192 vocab=49152, context=8192

Its file keeps every weight as nn.Linear does, (outputs, inputs), so
nothing is transposed (GPT-2's Conv1D layers were the other way round):
only the names change. Its 272 tensors are bfloat16, which
lab/safetensors.py widens to float32 (10.04).
"""

import torch

from data import fetch
from lab import safetensors
from models.gpt import GPT

CONFIG = dict(vocab=49152, context=8192, layers=30, heads=9, width=576, dropout=0.0, bias=False, positions="rotary",
              norm="rms", base=100000.0, mlp="swiglu", hidden=1536, kv_heads=3)


# @build 10.04 from_smollm
# SmolLM2's tensors (a dict of numpy arrays, named as in its file) under
# GPT's names, as they are: the embedding, and for each block its two
# RMSNorms' gains (input_layernorm before attention, post_attention_
# layernorm before the MLP), attention's four projections (q, k, v, o)
# and the MLP's three (gate, up, down); then the last norm. There is no
# output layer in the file: it is the embedding (tied).
def from_smollm(tensors, layers):
    out = {"tokens.weight": tensors["model.embed_tokens.weight"], "norm.weight": tensors["model.norm.weight"]}
    for i in range(layers):
        h, b = f"model.layers.{i}.", f"blocks.{i}."
        pairs = (("norm1", "input_layernorm"), ("norm2", "post_attention_layernorm"),
                 ("attention.query", "self_attn.q_proj"), ("attention.key", "self_attn.k_proj"),
                 ("attention.value", "self_attn.v_proj"), ("attention.out", "self_attn.o_proj"),
                 ("mlp.gate", "mlp.gate_proj"), ("mlp.up", "mlp.up_proj"), ("mlp.down", "mlp.down_proj"))
        for ours, theirs in pairs:
            out[b + ours + ".weight"] = tensors[h + theirs + ".weight"]
    return out
# @end


# @build 10.04 load
# SmolLM2-135M on the device dev, in eval mode: GPT(**CONFIG), and the
# weights of the file at path (by default the one data/fetch.py keeps; the
# script stops with the fetch command when it is not there), read by
# lab/safetensors.py and put in by from_smollm. load_state_dict refuses a
# missing name, one too many, or a shape that does not fit.
def load(dev, path=None):
    if path is None:
        fetch.need("smollm2")
        path = fetch.path("smollm2", "model.safetensors")
    model = GPT(**CONFIG)
    tensors = from_smollm(safetensors.load_file(path), CONFIG["layers"])
    model.load_state_dict({name: torch.from_numpy(a) for name, a in tensors.items()})
    return model.to(dev).eval()
# @end
