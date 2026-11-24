"""What the differential checks share, in the python a test's inside() runs in (see track.py's
inside()). That python has the project under test on its path, so `engine` is the learner's (or
the reference) engine, and `torch` is PyTorch, the reference.

    same(ours, theirs, what, tol=1e-6)
                        numpy arrays or tensors of either engine: equal within tol, relative to
                        the size of theirs (|a - b| <= tol * (1 + |b|)), or AssertionError
    pair(arrays)        the arrays as float64 tensors of both engines, needing gradients
    same_op(fn, shapes, what, positive=False, seed=0)
                        fn(engine_module, *tensors) on random float64 inputs of those shapes, in
                        both engines; the outputs, and every input's gradient for the same random
                        output gradient, must be the same to 1e-6
    copy_weights(ours, theirs)
                        our module's state_dict into a PyTorch module, as float64
    params(model)       its parameters as numpy arrays, in order
    gpt_numpy(model, ids, heads)
                        (08.02 on) models/gpt.py's GPT computed again in float64 numpy from its own
                        weights, attention written out position by position (layer_norm,
                        attention_numpy, gelu_numpy and block_numpy are its pieces)
"""

import numpy as np
import torch

import engine

TOL = 1e-6


def array(x):
    if isinstance(x, torch.Tensor):
        return x.detach().numpy()
    if isinstance(x, engine.Tensor):
        return x.data
    return np.asarray(x)


def same(ours, theirs, what, tol=TOL):
    a, b = array(ours).astype(np.float64), array(theirs).astype(np.float64)
    if a.shape != b.shape:
        raise AssertionError(f"{what}: shape {a.shape}, PyTorch's {b.shape}")
    bad = np.abs(a - b) > tol * (1 + np.abs(b))
    if bad.any():
        i = np.unravel_index(int(np.argmax(np.abs(a - b))), a.shape) if a.ndim else ()
        raise AssertionError(f"{what}: at {i} ours {a[i]!r}, PyTorch's {b[i]!r} "
                             f"(largest difference {np.abs(a - b).max():.3e})")


def pair(arrays, requires_grad=True):
    ours = [engine.tensor(np.array(a, dtype=np.float64), requires_grad=requires_grad) for a in arrays]
    theirs = [torch.tensor(np.array(a, dtype=np.float64), requires_grad=requires_grad) for a in arrays]
    return ours, theirs


def same_op(fn, shapes, what, positive=False, seed=0, tol=TOL):
    rng = np.random.default_rng(seed)
    arrays = [rng.standard_normal(s) for s in shapes]
    if positive:
        arrays = [np.abs(a) + 0.5 for a in arrays]
    ours, theirs = pair(arrays)
    out, ref = fn(engine, *ours), fn(torch, *theirs)
    same(out, ref, f"{what}: forward", tol)
    g = rng.standard_normal(tuple(ref.shape))
    out.backward(engine.tensor(g))
    ref.backward(torch.tensor(g))
    for k, (a, b) in enumerate(zip(ours, theirs)):
        if b.grad is None:
            assert a.grad is None, f"{what}: input {k} has a gradient, PyTorch's has none"
            continue
        assert a.grad is not None, f"{what}: input {k} got no gradient"
        same(a.grad, b.grad, f"{what}: gradient of input {k}", tol)


def copy_weights(ours, theirs):
    theirs.double()
    theirs.load_state_dict({k: torch.tensor(np.array(v.data, dtype=np.float64 if v.data.dtype.kind == "f"
                                                     else v.data.dtype))
                            for k, v in ours.state_dict().items()})
    return theirs


def params(model):
    return [array(p).copy() for p in model.parameters()]


# ---------------------------------------------------------------- module 08: a GPT written again, in numpy

def layer_norm(x, weight, bias, eps=1e-5):
    """Each row of x minus its mean, over the root of its variance (dividing by n) plus eps, then times
    weight plus bias: nn.LayerNorm, as GPT-2 has it (eps 1e-5)."""
    mean = x.mean(-1, keepdims=True)
    var = ((x - mean) ** 2).mean(-1, keepdims=True)
    return (x - mean) / np.sqrt(var + eps) * weight + (0 if bias is None else bias)


def attention_numpy(x, p, prefix, heads, mask=True):
    """models/gpt.py's SelfAttention on x (B, T, W), from its weights in p (numpy, our names under prefix):
    each head's queries, keys and values a slice of width W / heads, and for each position i a softmax
    over j <= i (every j without the mask) of q_i . k_j / sqrt(W / heads), written out position by
    position."""
    B, T, W = x.shape
    d = W // heads
    q, k, v = (x @ p[prefix + n + ".weight"].T + p.get(prefix + n + ".bias", 0) for n in ("query", "key", "value"))
    y = np.zeros_like(q)
    for b in range(B):
        for h in range(heads):
            s = slice(h * d, (h + 1) * d)
            for i in range(T):
                seen = i + 1 if mask else T
                scores = np.array([q[b, i, s] @ k[b, j, s] for j in range(seen)]) / np.sqrt(d)
                w = np.exp(scores - scores.max())
                w /= w.sum()
                y[b, i, s] = w @ v[b, :seen, s]
    return y @ p[prefix + "out.weight"].T + p.get(prefix + "out.bias", 0)


def gelu_numpy(x):
    return 0.5 * x * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x ** 3)))


def block_numpy(x, p, prefix, heads):
    """One of models/gpt.py's Blocks, from its weights: x + attention(ln1(x)), then + mlp(ln2(x))."""
    x = x + attention_numpy(layer_norm(x, p[prefix + "norm1.weight"], p.get(prefix + "norm1.bias")), p,
                            prefix + "attention.", heads)
    h = layer_norm(x, p[prefix + "norm2.weight"], p.get(prefix + "norm2.bias"))
    u = h @ p[prefix + "mlp.up.weight"].T + p.get(prefix + "mlp.up.bias", 0)
    return x + gelu_numpy(u) @ p[prefix + "mlp.down.weight"].T + p.get(prefix + "mlp.down.bias", 0)


def gpt_numpy(model, ids, heads):
    """A GPT's scores for ids (a numpy array (B, T)), computed again in float64 numpy from the model's own
    weights: embeddings (and positions, when it has them), every block, the last layer norm, and the
    dot products with the embeddings."""
    p = {k: v.detach().double().numpy() for k, v in model.state_dict().items()}
    x = p["tokens.weight"][ids]
    if "positions.weight" in p:
        x = x + p["positions.weight"][:ids.shape[1]]
    layers = len({k.split(".")[1] for k in p if k.startswith("blocks.")})
    for i in range(layers):
        x = block_numpy(x, p, f"blocks.{i}.", heads)
    return layer_norm(x, p["norm.weight"], p.get("norm.bias")) @ p["tokens.weight"].T
