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
