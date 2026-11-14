"""Starting weights: torch.nn.init.

Each function fills a tensor in place, from the engine's generator, and
returns it. A layer's output is a sum of fan_in products, so its variance
is fan_in times the weights' variance times the input's: weights of
variance 1 / fan_in keep the signal the same size from layer to layer.
Glorot and Bengio (2010) split the difference between the forward pass
(fan_in) and the backward one (fan_out): variance 2 / (fan_in + fan_out).
A relu zeroes half of its inputs and so halves the variance; He et al.
(2015) double the weights' variance to make up for it: 2 / fan_in.
"""

import math

from engine import tensors as _t


def _fill(tensor, values):
    tensor.data[...] = values.astype(tensor.data.dtype)
    return tensor


def _fans(tensor):
    """(fan_in, fan_out) of a weight of shape (out, in): the inputs each output sums, and the
    outputs each input feeds."""
    if tensor.data.ndim < 2:
        raise ValueError("Fan in and fan out can not be computed for tensor with fewer than 2 dimensions")
    return tensor.data.shape[1], tensor.data.shape[0]


def normal_(tensor, mean=0.0, std=1.0):
    return _fill(tensor, _t.generator().normal(mean, std, tensor.data.shape))


def uniform_(tensor, a=0.0, b=1.0):
    return _fill(tensor, _t.generator().uniform(a, b, tensor.data.shape))


def zeros_(tensor):
    tensor.data[...] = 0
    return tensor


def ones_(tensor):
    tensor.data[...] = 1
    return tensor


# @build 04.02 calculate_gain
# How much a nonlinearity shrinks the spread of what passes through it, to
# be made up for by the weights: 1 for "linear" and "sigmoid", 5/3 for
# "tanh", sqrt(2) for "relu", sqrt(2 / (1 + slope**2)) for "leaky_relu"
# (param is the slope, 0.01 when not given).
def calculate_gain(nonlinearity, param=None):
    if nonlinearity in ("linear", "sigmoid"):
        return 1.0
    if nonlinearity == "tanh":
        return 5.0 / 3
    if nonlinearity == "relu":
        return math.sqrt(2.0)
    if nonlinearity == "leaky_relu":
        slope = 0.01 if param is None else param
        return math.sqrt(2.0 / (1 + slope ** 2))
    raise ValueError(f"Unsupported nonlinearity {nonlinearity}")
# @end


# @build 04.02 xavier_normal_
# Glorot's initialisation: normal, standard deviation
# gain * sqrt(2 / (fan_in + fan_out)); the uniform one has the same
# variance, so its bound is sqrt(3) times that.
def xavier_normal_(tensor, gain=1.0):
    fan_in, fan_out = _fans(tensor)
    return normal_(tensor, 0.0, gain * math.sqrt(2.0 / (fan_in + fan_out)))


def xavier_uniform_(tensor, gain=1.0):
    fan_in, fan_out = _fans(tensor)
    bound = gain * math.sqrt(6.0 / (fan_in + fan_out))
    return uniform_(tensor, -bound, bound)
# @end


# @build 04.02 kaiming_normal_
# He's initialisation: normal, standard deviation gain / sqrt(fan), with
# fan the fan_in (mode "fan_in", the forward pass) or the fan_out
# ("fan_out", the backward one) and the gain of calculate_gain(nonlinearity,
# a): sqrt(2) for relu. The uniform one has the same variance.
def kaiming_normal_(tensor, a=0.0, mode="fan_in", nonlinearity="leaky_relu"):
    fan_in, fan_out = _fans(tensor)
    std = calculate_gain(nonlinearity, a) / math.sqrt(fan_in if mode == "fan_in" else fan_out)
    return normal_(tensor, 0.0, std)


def kaiming_uniform_(tensor, a=0.0, mode="fan_in", nonlinearity="leaky_relu"):
    fan_in, fan_out = _fans(tensor)
    bound = math.sqrt(3.0) * calculate_gain(nonlinearity, a) / math.sqrt(fan_in if mode == "fan_in" else fan_out)
    return uniform_(tensor, -bound, bound)
# @end
