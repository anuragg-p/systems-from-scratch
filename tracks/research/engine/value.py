"""An automatic differentiation engine over single numbers.

A Value is one float (.data) that remembers how it was made: the Values it
came from (._prev), the operation (._op), and a function (._backward) that
passes the gradient of the final result on to those inputs. Arithmetic on
Values builds a graph as it computes. backward() then walks the graph from
the result to its inputs, applying the chain rule at every node, and leaves
in each Value's .grad the derivative of the result with respect to it.

On top of it, a neuron, a layer and a network of layers: the whole of a
small neural network written as arithmetic on Values.
"""

import math
import random


class Value:
    """One number in a computation, and its gradient once backward() has run."""

    def __init__(self, data, _prev=(), _op=""):
        self.data = float(data)
        self.grad = 0.0
        self._prev = _prev
        self._op = _op
        self._backward = None

    def __repr__(self):
        return f"Value(data={self.data:.6g}, grad={self.grad:.6g})"

    # @build 01.02 __add__
    # a + b. Each input moves the output one for one, so the gradient of the
    # output is added, unchanged, to the gradient of each input. A plain number
    # on either side is made a Value first (__radd__ covers 2 + a).
    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward():
            self.grad += out.grad
            other.grad += out.grad
        out._backward = _backward
        return out

    __radd__ = __add__
    # @end

    # @build 01.02 __mul__
    # a * b. Moving a by one moves the output by b, and the other way round,
    # so each input's gradient gains the output's gradient times the other
    # input's value.
    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad
        out._backward = _backward
        return out

    __rmul__ = __mul__
    # @end

    # @build 01.02 __pow__
    # a ** n for a plain number n (not a Value): the derivative is n * a**(n-1).
    def __pow__(self, n):
        out = Value(self.data ** n, (self,), f"**{n}")

        def _backward():
            self.grad += n * self.data ** (n - 1) * out.grad
        out._backward = _backward
        return out
    # @end

    # The rest of arithmetic is made of the three above, so it needs no
    # backward of its own: a - b is a + (-1 * b), a / b is a * b**-1.
    def __neg__(self):
        return self * -1

    def __sub__(self, other):
        return self + (-other)

    def __rsub__(self, other):
        return other + (-self)

    def __truediv__(self, other):
        return self * other ** -1

    def __rtruediv__(self, other):
        return other * self ** -1

    # @build 01.02 exp
    # e to the power a. Its derivative is itself: the output's own value.
    def exp(self):
        out = Value(math.exp(self.data), (self,), "exp")

        def _backward():
            self.grad += out.data * out.grad
        out._backward = _backward
        return out
    # @end

    # @build 01.02 log
    # The natural logarithm of a (a > 0). Its derivative is 1 / a.
    def log(self):
        out = Value(math.log(self.data), (self,), "log")

        def _backward():
            self.grad += out.grad / self.data
        out._backward = _backward
        return out
    # @end

    # @build 01.02 tanh
    # tanh(a), squashing any number into (-1, 1). Its derivative is
    # 1 - tanh(a)**2, which the output already holds.
    def tanh(self):
        t = math.tanh(self.data)
        out = Value(t, (self,), "tanh")

        def _backward():
            self.grad += (1 - t * t) * out.grad
        out._backward = _backward
        return out
    # @end

    # @build 01.02 relu
    # max(0, a): the number itself when positive, else 0. The gradient passes
    # through where the input was positive and stops where it was not.
    def relu(self):
        out = Value(self.data if self.data > 0 else 0.0, (self,), "relu")

        def _backward():
            self.grad += (self.data > 0) * out.grad
        out._backward = _backward
        return out
    # @end

    # @build 01.02 backward
    # Fill .grad of every Value this one was computed from. List the graph so
    # that each Value comes after everything it was made from (a topological
    # order, by depth-first search, without recursion so a deep graph cannot
    # overflow the stack), set this Value's gradient to 1, then walk the list
    # backwards calling each node's _backward: by the time a node passes its
    # gradient on, every use of it has added its share. Gradients add up, so
    # set them to zero before a second backward.
    def backward(self):
        order, seen = [], set()
        stack = [(self, False)]
        while stack:
            v, expanded = stack.pop()
            if expanded:
                order.append(v)
                continue
            if id(v) in seen:
                continue
            seen.add(id(v))
            stack.append((v, True))
            for p in v._prev:
                if id(p) not in seen:
                    stack.append((p, False))
        self.grad = 1.0
        for v in reversed(order):
            if v._backward is not None:
                v._backward()
    # @end


# @build 01.03 Neuron
# One neuron: a weight per input and a bias, all Values. Called on a list of
# inputs it returns the weighted sum plus the bias, through relu unless it
# is linear (the last layer). Weights start uniform in [-1, 1], drawn from
# rng (a random.Random), the bias at 0.
class Neuron:
    def __init__(self, nin, rng, linear=False):
        self.w = [Value(rng.uniform(-1, 1)) for _ in range(nin)]
        self.b = Value(0.0)
        self.linear = linear

    def __call__(self, x):
        act = sum((wi * xi for wi, xi in zip(self.w, x)), self.b)
        return act if self.linear else act.relu()

    def parameters(self):
        return self.w + [self.b]
# @end


# @build 01.03 Layer
# nout neurons that each see the same nin inputs. Called on a list of
# inputs, returns the list of the neurons' outputs.
class Layer:
    def __init__(self, nin, nout, rng, linear=False):
        self.neurons = [Neuron(nin, rng, linear) for _ in range(nout)]

    def __call__(self, x):
        return [n(x) for n in self.neurons]

    def parameters(self):
        return [p for n in self.neurons for p in n.parameters()]
# @end


# @build 01.03 MLP
# Layers one after another: MLP(2, [16, 16, 1]) takes 2 numbers through two
# layers of 16 relu neurons to one linear output. Called on a list of
# inputs it returns the last layer's outputs, or the one Value when there
# is only one. seed makes the starting weights the same every time.
class MLP:
    def __init__(self, nin, nouts, seed=0):
        rng = random.Random(seed)
        sizes = [nin] + list(nouts)
        self.layers = [Layer(sizes[i], sizes[i + 1], rng, linear=(i == len(nouts) - 1))
                       for i in range(len(nouts))]

    def __call__(self, x):
        for layer in self.layers:
            x = layer(x)
        return x[0] if len(x) == 1 else x

    def parameters(self):
        return [p for layer in self.layers for p in layer.parameters()]
# @end
