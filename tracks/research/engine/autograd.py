"""Checking a gradient against the nudge, for tensors.

torch.autograd.gradcheck(f, inputs) runs f, takes the gradients backward()
gives, and compares them with gradients found by nudging every number of
every input. It returns True, or raises with the first number that differs.
Use float64 inputs: in float32 the nudge itself is too coarse to tell a
right gradient from a slightly wrong one.
"""

import numpy as np

from engine.tensors import Tensor


# @build 02.02 gradcheck
# f takes the tensors in inputs (a tensor or a tuple of them) and returns a
# tensor of any shape. A fixed random v weighs the outputs, so one number,
# sum(f(inputs) * v), stands for all of them. backward(v) gives its gradient
# with respect to each input that requires one; nudging each number of that
# input by eps both ways, in place, gives the same thing by the central
# difference of 01.01. They must agree within atol + rtol * |nudged| for
# every number, or a RuntimeError names the input and the place. Leaves
# the inputs' numbers and gradients as they were.
def gradcheck(func, inputs, eps=1e-6, atol=1e-5, rtol=1e-3):
    inputs = (inputs,) if isinstance(inputs, Tensor) else tuple(inputs)
    out = func(*inputs)
    v = np.random.default_rng(0).standard_normal(out.data.shape)
    saved = [x.grad for x in inputs]
    for x in inputs:
        x.grad = None
    out.backward(Tensor(v.astype(out.data.dtype)))
    worked = [None if x.grad is None else x.grad.data.copy() for x in inputs]
    for x, g in zip(inputs, saved):
        x.grad = g

    def weighted():
        return float(np.sum(func(*inputs).data * v))

    for k, x in enumerate(inputs):
        if not x.requires_grad:
            continue
        flat = x.data.reshape(-1)          # a view: changing it changes x
        nudged = np.zeros(flat.size)
        for i in range(flat.size):
            keep = flat[i]
            flat[i] = keep + eps
            up = weighted()
            flat[i] = keep - eps
            down = weighted()
            flat[i] = keep
            nudged[i] = (up - down) / (2 * eps)
        got = np.zeros(flat.size) if worked[k] is None else worked[k].reshape(-1)
        bad = np.abs(got - nudged) > atol + rtol * np.abs(nudged)
        if bad.any():
            i = int(np.argmax(bad))
            place = tuple(int(j) for j in np.unravel_index(i, x.data.shape))
            raise RuntimeError(f"Jacobian mismatch for output 0 with respect to input {k}: at position "
                               f"{place} backward gives {got[i]:.8g}, the nudge {nudged[i]:.8g}")
    return True
# @end
