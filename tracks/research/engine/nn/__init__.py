"""Layers: torch.nn.

A Module is a piece of a network that holds its own weights. Setting an
attribute to a Parameter (a tensor that is a weight) or to another Module
registers it, in order, so the module can list every weight under it with
a dotted name ("0.weight", "2.bias"): what an optimiser updates and what a
checkpoint saves. Calling a module runs its forward().
"""

import math

import numpy as np

from engine import tensors as _t
from engine.tensors import Tensor
from engine.nn import functional
from engine.nn import init          # @from 04.02


# @build 02.05 Parameter
# A tensor that is a weight of a module: it requires a gradient, and
# Module.__setattr__ knows it by its type. It shares the numbers of the
# tensor it is made from.
class Parameter(Tensor):
    def __init__(self, data, requires_grad=True):
        super().__init__(data.data if isinstance(data, Tensor) else np.asarray(data), requires_grad)

    def __repr__(self):
        return "Parameter containing:\n" + super().__repr__()
# @end


# @build 02.05 Module
# The base of every layer. __setattr__ files Parameters, Modules and
# buffers (tensors to save that are not weights, such as batch norm's
# running statistics) in three ordered dictionaries as they are set.
# named_parameters walks its own and then each child's, prefixed with the
# child's name, each weight once; state_dict gives the parameters and
# buffers by name (detached, sharing their numbers), and load_state_dict
# copies such a dictionary's numbers back in, refusing a missing or extra
# name or a different shape. train() and eval() set .training on every
# module below, and zero_grad() forgets every gradient.
# @stub class Module: pass  # 02.05: Module not written yet
class Module:
    def __init__(self):
        object.__setattr__(self, "_parameters", {})
        object.__setattr__(self, "_buffers", {})
        object.__setattr__(self, "_modules", {})
        object.__setattr__(self, "training", True)

    def __setattr__(self, name, value):
        if isinstance(value, Parameter):
            self._parameters[name] = value
        elif isinstance(value, Module):
            self._modules[name] = value
        elif name in self._buffers:
            self._buffers[name] = value
        object.__setattr__(self, name, value)

    def register_buffer(self, name, tensor):
        self._buffers[name] = tensor
        object.__setattr__(self, name, tensor)

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

    def forward(self, *args):
        raise NotImplementedError(f"{type(self).__name__} has no forward()")

    def named_modules(self, prefix=""):
        yield prefix, self
        for name, m in self._modules.items():
            yield from m.named_modules(prefix + ("." if prefix else "") + name)

    def modules(self):
        return [m for _, m in self.named_modules()]

    def children(self):
        return list(self._modules.values())

    def named_parameters(self, prefix=""):
        seen = set()
        for mname, m in self.named_modules(prefix):
            for name, p in m._parameters.items():
                if id(p) not in seen:
                    seen.add(id(p))
                    yield mname + ("." if mname else "") + name, p

    def parameters(self):
        return [p for _, p in self.named_parameters()]

    def state_dict(self):
        out = {}
        for mname, m in self.named_modules():
            dot = mname + ("." if mname else "")
            for name, p in m._parameters.items():
                out[dot + name] = p.detach()
            for name, b in m._buffers.items():
                out[dot + name] = b.detach()
        return out

    def load_state_dict(self, state_dict, strict=True):
        own = self.state_dict()
        missing = [k for k in own if k not in state_dict]
        unexpected = [k for k in state_dict if k not in own]
        if strict and (missing or unexpected):
            raise RuntimeError(f"Error(s) in loading state_dict for {type(self).__name__}: "
                               f"missing keys {missing}, unexpected keys {unexpected}")
        for k, t in own.items():
            if k not in state_dict:
                continue
            src = state_dict[k]
            src = src.data if isinstance(src, Tensor) else np.asarray(src)
            if src.shape != t.data.shape:
                raise RuntimeError(f"size mismatch for {k}: copying a param with shape {src.shape}, "
                                   f"the shape in the current model is {t.data.shape}")
            t.data[...] = src
        return missing, unexpected

    def train(self, mode=True):
        for m in self.modules():
            object.__setattr__(m, "training", mode)
        return self

    def eval(self):
        return self.train(False)

    def zero_grad(self):
        for p in self.parameters():
            p.grad = None

    def apply(self, fn):
        for m in self.children():
            m.apply(fn)
        fn(self)
        return self

    def double(self):
        return self._cast(np.float64)

    def float(self):
        return self._cast(np.float32)

    def _cast(self, dtype):
        for m in self.modules():
            for t in list(m._parameters.values()) + list(m._buffers.values()):
                if t.data.dtype.kind == "f":
                    t.data = t.data.astype(dtype)
                    if t.grad is not None:
                        t.grad.data = t.grad.data.astype(dtype)
        return self

    def extra_repr(self):
        return ""

    def __repr__(self):
        lines = [f"({name}): " + repr(m).replace("\n", "\n  ") for name, m in self._modules.items()]
        head = f"{type(self).__name__}({self.extra_repr()}"
        return head + ")" if not lines else head + "\n  " + "\n  ".join(lines) + "\n)"
# @end


# @build 02.05 Linear
# y = x @ weight.T + bias, with weight of shape (out_features, in_features)
# as PyTorch keeps it. Both start uniform in [-1/sqrt(in), 1/sqrt(in)], as
# PyTorch's do, from the engine's generator: the sum of `in` such products
# then stays about the size of one input.
class Linear(Module):
    def __init__(self, in_features, out_features, bias=True):
        super().__init__()
        self.in_features, self.out_features = in_features, out_features
        bound = 1 / math.sqrt(in_features)
        rng = _t.generator()
        self.weight = Parameter(rng.uniform(-bound, bound, (out_features, in_features)).astype(np.float32))
        if bias:
            self.bias = Parameter(rng.uniform(-bound, bound, (out_features,)).astype(np.float32))
        else:
            self.bias = None

    def forward(self, x):
        y = x @ self.weight.T
        return y if self.bias is None else y + self.bias

    def extra_repr(self):
        return f"in_features={self.in_features}, out_features={self.out_features}, bias={self.bias is not None}"
# @end


# @build 02.05 ReLU
# The activations as modules, so they can sit in a Sequential.
class ReLU(Module):
    def forward(self, x):
        return x.relu()


class Tanh(Module):
    def forward(self, x):
        return x.tanh()
# @end


class Sigmoid(Module):              # @from 04.03
    def forward(self, x):           # @from 04.03
        return x.sigmoid()          # @from 04.03


# @build 02.05 Sequential
# Modules applied one after another, registered under the names "0", "1",
# ... so their weights are "0.weight", "0.bias", ...
class Sequential(Module):
    def __init__(self, *modules):
        super().__init__()
        for i, m in enumerate(modules):
            setattr(self, str(i), m)

    def forward(self, x):
        for m in self._modules.values():
            x = m(x)
        return x

    def __getitem__(self, i):
        return list(self._modules.values())[i]

    def __len__(self):
        return len(self._modules)

    def __iter__(self):
        return iter(self._modules.values())
# @end


# @build 04.03 BatchNorm1d
# Normalise each feature over the batch: subtract the batch's mean and
# divide by its standard deviation (the biased one, over n, with eps
# inside the square root), then scale by weight and shift by bias, both
# learned (starting at 1 and 0). In training, the running statistics move
# a fraction `momentum` of the way to the batch's (the running variance to
# its unbiased variance, over n - 1); in eval() they are used instead of
# the batch's, so one input gives one answer whatever the batch. A batch of
# one has no spread to measure, so training on it is an error.
# num_batches_tracked counts the batches, as PyTorch's checkpoint has it.
class BatchNorm1d(Module):
    def __init__(self, num_features, eps=1e-5, momentum=0.1):
        super().__init__()
        self.num_features, self.eps, self.momentum = num_features, eps, momentum
        self.weight = Parameter(np.ones(num_features, dtype=np.float32))
        self.bias = Parameter(np.zeros(num_features, dtype=np.float32))
        self.register_buffer("running_mean", Tensor(np.zeros(num_features, dtype=np.float32)))
        self.register_buffer("running_var", Tensor(np.ones(num_features, dtype=np.float32)))
        self.register_buffer("num_batches_tracked", Tensor(np.array(0, dtype=np.int64)))

    def forward(self, x):
        if x.shape[-1] != self.num_features:
            raise RuntimeError(f"running_mean should contain {x.shape[-1]} elements not {self.num_features}")
        if self.training:
            n = x.shape[0]
            if n < 2:
                raise ValueError(f"Expected more than 1 value per channel when training, "
                                 f"got input size {tuple(x.shape)}")
            mean = x.mean(0)
            var = x.var(0, unbiased=False)
            m = self.momentum
            self.running_mean.data[...] = (1 - m) * self.running_mean.data + m * mean.data
            self.running_var.data[...] = (1 - m) * self.running_var.data + m * var.data * n / (n - 1)
            self.num_batches_tracked.data[...] += 1
        else:
            mean, var = self.running_mean, self.running_var
        return (x - mean) / (var + self.eps) ** 0.5 * self.weight + self.bias

    def extra_repr(self):
        return f"{self.num_features}, eps={self.eps}, momentum={self.momentum}"
# @end


# @build 04.04 LayerNorm
# Normalise each example over its own features (the last dimension):
# subtract its mean, divide by its standard deviation (biased, eps inside
# the root), then scale and shift by learned weight and bias. Nothing comes
# from the rest of the batch, so it is the same in training and in eval(),
# and a batch of one is fine.
class LayerNorm(Module):
    def __init__(self, normalized_shape, eps=1e-5):
        super().__init__()
        self.normalized_shape, self.eps = normalized_shape, eps
        self.weight = Parameter(np.ones(normalized_shape, dtype=np.float32))
        self.bias = Parameter(np.zeros(normalized_shape, dtype=np.float32))

    def forward(self, x):
        mean = x.mean(-1, keepdim=True)
        var = x.var(-1, unbiased=False, keepdim=True)
        return (x - mean) / (var + self.eps) ** 0.5 * self.weight + self.bias

    def extra_repr(self):
        return f"({self.normalized_shape},), eps={self.eps}"
# @end


# @build 05.02 Dropout
# functional.dropout as a module: it drops only while the module is
# training, so model.eval() turns it off.
class Dropout(Module):
    def __init__(self, p=0.5):
        super().__init__()
        self.p = p

    def forward(self, x):
        return functional.dropout(x, self.p, self.training)

    def extra_repr(self):
        return f"p={self.p}"
# @end
