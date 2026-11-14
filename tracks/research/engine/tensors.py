"""Tensors: arrays of numbers that remember how they were computed.

The scalar engine made one Python object per number. Here one object holds
a whole numpy array (.data), and one operation does the arithmetic for all
its numbers at once, in numpy's compiled loops. The rest is the scalar
engine again: an operation on tensors that need a gradient returns a new
tensor that keeps its inputs (._prev) and a function (._backward) that
passes the output's gradient back to them, and backward() walks the graph
from the result to the leaves.

Names and argument order are PyTorch's: a script that uses only what is
here runs on PyTorch by changing its one `import engine as torch` line.
Where PyTorch keeps a Tensor, so does this engine (.grad is a Tensor), but
.data is the numpy array itself, which PyTorch's is not: scripts never use
it, only the engine does.
"""

import numpy as np

float32 = np.dtype(np.float32)
float64 = np.dtype(np.float64)
int64 = np.dtype(np.int64)
bool = np.dtype(np.bool_)           # PyTorch's name; shadows the builtin in this file only

# Whether operations record the graph. no_grad turns it off.
GRAD_ENABLED = True


class Tensor:
    """A numpy array, and the gradient of a result with respect to it once backward() has run."""

    __hash__ = object.__hash__      # a tensor is a dictionary key by identity, as in PyTorch

    def __init__(self, data, requires_grad=False):
        self.data = data if isinstance(data, np.ndarray) else np.asarray(data)
        self.requires_grad = requires_grad
        self.grad = None
        self._prev = ()
        self._backward = None
        self._retain = False

    # ---------------------------------------------------------------- what it is

    @property
    def shape(self):
        return self.data.shape

    @property
    def dtype(self):
        return self.data.dtype

    @property
    def ndim(self):
        return self.data.ndim

    @property
    def is_leaf(self):
        return self._backward is None

    def size(self, dim=None):
        return self.data.shape if dim is None else self.data.shape[dim]

    def dim(self):
        return self.data.ndim

    def numel(self):
        return self.data.size

    def __len__(self):
        return len(self.data)

    def item(self):
        return self.data.item()

    def tolist(self):
        return self.data.tolist()

    def numpy(self):
        if self.requires_grad:
            raise RuntimeError("Can't call numpy() on Tensor that requires grad. "
                               "Use tensor.detach().numpy() instead.")
        return self.data

    def detach(self):
        return Tensor(self.data)

    def __repr__(self):
        body = np.array2string(self.data, precision=4, separator=", ", prefix="tensor(")
        extra = "" if self.data.dtype in (float32, int64, bool) else f", dtype={self.data.dtype}"
        if self._backward is not None:
            extra += f", grad_fn=<{self._op}>"
        elif self.requires_grad:
            extra += ", requires_grad=True"
        return f"tensor({body}{extra})"

    # ---------------------------------------------------------------- gradients

    # @build 02.01 _accumulate
    # Add g (a numpy array) to this tensor's gradient: nothing if it needs
    # none; a new .grad, a Tensor holding a copy of g, the first time; added in
    # place after that, since a tensor used twice gets a share from each use.
    # g comes in the output's shape: it must match this tensor's shape.
    def _accumulate(self, g):
        if not self.requires_grad:
            return
        # @from 02.02
        g = unbroadcast(g, self.data.shape)
        # @else
        # if g.shape != self.data.shape:
        #     raise ValueError(f"a gradient of shape {g.shape} for a tensor of shape {self.data.shape}: "
        #                      f"the inputs of an operation must have the same shape")
        # @end
        if self.grad is None:
            self.grad = Tensor(np.array(g, dtype=self.data.dtype))
        else:
            self.grad.data += g
    # @end

    # @build 02.01 backward
    # Fill .grad of every tensor this one was computed from, as the scalar
    # engine did: a topological order by depth-first search (no recursion),
    # this tensor's gradient set to `gradient` (or 1 when it holds one number;
    # anything bigger needs one given), then each node's _backward, last node
    # first. Afterwards drop the gradients of the tensors in between (not the
    # leaves, and not those retain_grad() asked to keep): only the leaves'
    # are wanted, and they would hold memory. numpy's warnings about inf and
    # nan are silenced: PyTorch has none, an overflow is just an inf.
    def backward(self, gradient=None):
        if not self.requires_grad:
            raise RuntimeError("element 0 of tensors does not require grad and does not have a grad_fn")
        if gradient is None:
            if self.data.size != 1:
                raise RuntimeError("grad can be implicitly created only for scalar outputs")
            gradient = np.ones_like(self.data)
        elif isinstance(gradient, Tensor):
            gradient = gradient.data
        order, seen = [], set()
        stack = [(self, False)]
        while stack:
            t, expanded = stack.pop()
            if expanded:
                order.append(t)
                continue
            if id(t) in seen:
                continue
            seen.add(id(t))
            stack.append((t, True))
            for p in t._prev:
                if id(p) not in seen:
                    stack.append((p, False))
        self._accumulate(np.asarray(gradient, dtype=self.data.dtype))
        with np.errstate(all="ignore"):         # an inf or nan is a value, as in PyTorch, not a warning
            for t in reversed(order):
                if t._backward is not None and t.grad is not None:
                    t._backward()
        for t in order:
            if t._backward is not None and not t._retain:
                t.grad = None
    # @end

    # @build 04.01 retain_grad
    # Keep this tensor's gradient after backward() even though it is not a
    # leaf: the gradient arriving at a layer's output, to look at.
    def retain_grad(self):
        self._retain = True
    # @end

    # ---------------------------------------------------------------- arithmetic

    # @build 02.01 __add__
    # a + b, for every number at once: the output's gradient goes, unchanged,
    # to each input (each input's _accumulate makes it that input's shape).
    def __add__(self, other):
        other = _as_tensor(other, self)
        with np.errstate(all="ignore"):
            out = _result(self.data + other.data, (self, other), "AddBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad.data)
                other._accumulate(out.grad.data)
            out._backward = _backward
        return out

    __radd__ = __add__
    # @end

    # @build 02.01 __mul__
    # a * b, number by number: each input's gradient is the output's
    # gradient times the other input.
    def __mul__(self, other):
        other = _as_tensor(other, self)
        with np.errstate(all="ignore"):
            out = _result(self.data * other.data, (self, other), "MulBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad.data * other.data)
                other._accumulate(out.grad.data * self.data)
            out._backward = _backward
        return out

    __rmul__ = __mul__
    # @end

    # @build 02.01 __pow__
    # a ** n for a plain number n: the gradient is n * a**(n-1) times the
    # output's. Like add and mul, it silences numpy's warnings about inf and
    # nan: PyTorch has none, an overflow is just an inf in the result.
    def __pow__(self, n):
        with np.errstate(all="ignore"):
            out = _result(self.data ** n, (self,), "PowBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(n * self.data ** (n - 1) * out.grad.data)
            out._backward = _backward
        return out
    # @end

    # Made of the three above, as in the scalar engine.
    def __neg__(self):
        return self * -1

    def __sub__(self, other):
        return self + (-_as_tensor(other, self))

    def __rsub__(self, other):
        return _as_tensor(other, self) + (-self)

    def __truediv__(self, other):
        return self * _as_tensor(other, self) ** -1

    def __rtruediv__(self, other):
        return _as_tensor(other, self) * self ** -1

    # @build 02.01 exp
    # e to the power of every number; its gradient is the output itself.
    def exp(self):
        with np.errstate(all="ignore"):
            out = _result(np.exp(self.data), (self,), "ExpBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.data * out.grad.data)
            out._backward = _backward
        return out
    # @end

    # @build 02.01 log
    # The natural logarithm of every number; its gradient is 1 / a. log(0) is
    # -inf, without a warning, as in PyTorch.
    def log(self):
        with np.errstate(all="ignore"):
            out = _result(np.log(self.data), (self,), "LogBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad.data / self.data)
            out._backward = _backward
        return out
    # @end

    # @build 02.01 tanh
    # tanh of every number; its gradient is 1 - tanh**2.
    def tanh(self):
        out = _result(np.tanh(self.data), (self,), "TanhBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate((1 - out.data ** 2) * out.grad.data)
            out._backward = _backward
        return out
    # @end

    # @build 02.01 relu
    # max(0, a) for every number; the gradient passes where a > 0.
    def relu(self):
        out = _result(np.maximum(self.data, 0), (self,), "ReluBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate((self.data > 0) * out.grad.data)
            out._backward = _backward
        return out
    # @end

    # @build 04.03 sigmoid
    # 1 / (1 + e**-a) for every number, between 0 and 1; its gradient is
    # s * (1 - s), at most 1/4, which the output already holds.
    def sigmoid(self):
        with np.errstate(all="ignore"):
            out = _result(1 / (1 + np.exp(-self.data)), (self,), "SigmoidBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.data * (1 - out.data) * out.grad.data)
            out._backward = _backward
        return out
    # @end

    # @build 04.01 abs
    # |a| for every number; the gradient is the sign of a (0 at 0).
    def abs(self):
        out = _result(np.abs(self.data), (self,), "AbsBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(np.sign(self.data) * out.grad.data)
            out._backward = _backward
        return out
    # @end

    # ---------------------------------------------------------------- shapes, sums, indexing

    # @build 02.03 __matmul__
    # a @ b, the matrix product. For a of shape (n, k) and b of shape (k, m),
    # out[i, j] is the sum over k of a[i, k] * b[k, j], so the gradient of
    # a is out.grad @ b.T and that of b is a.T @ out.grad. Tensors with more
    # than two dimensions are stacks of matrices (the leading dimensions
    # broadcast); a vector on either side is a matrix of one row or column.
    def __matmul__(self, other):
        out = _result(self.data @ other.data, (self, other), "MmBackward")
        if out.requires_grad:
            def _backward():
                a, b, g = self.data, other.data, out.grad.data
                if a.ndim == 1:
                    a, g = a[None, :], g[..., None, :]
                if b.ndim == 1:
                    b, g = b[:, None], g[..., None]
                ga = g @ np.swapaxes(b, -1, -2)
                gb = np.swapaxes(a, -1, -2) @ g
                self._accumulate(ga.reshape(ga.shape[:-2] + self.data.shape[-1:]) if self.data.ndim == 1 else ga)
                other._accumulate(gb.reshape(gb.shape[:-2] + other.data.shape[:1]) if other.data.ndim == 1 else gb)
            out._backward = _backward
        return out
    # @end

    # @build 02.03 sum
    # The sum of every number, or along dim (a number or a tuple of them),
    # keeping that dimension as size 1 when keepdim. Each input number
    # moved the sum one for one, so its gradient is the gradient of the sum
    # it went into: put the summed dimensions back (as size 1) and spread the
    # gradient along them.
    def sum(self, dim=None, keepdim=False):
        out = _result(np.sum(self.data, axis=dim, keepdims=keepdim), (self,), "SumBackward")
        if out.requires_grad:
            def _backward():
                g = out.grad.data
                if dim is not None and not keepdim:
                    g = np.expand_dims(g, dim)
                self._accumulate(np.broadcast_to(g, self.data.shape))
            out._backward = _backward
        return out
    # @end

    # @build 02.03 mean
    # The sum divided by how many numbers went into it.
    def mean(self, dim=None, keepdim=False):
        count = self.data.size if dim is None else np.prod([self.data.shape[d] for d in np.atleast_1d(dim)])
        return self.sum(dim, keepdim) / float(count)
    # @end

    # @build 04.01 var
    # The variance: the mean of the squared distances from the mean, divided
    # by n - 1 rather than n when unbiased (PyTorch's default, an estimate of
    # the whole population's from a sample of it).
    def var(self, dim=None, unbiased=True, keepdim=False):
        n = self.data.size if dim is None else np.prod([self.data.shape[d] for d in np.atleast_1d(dim)])
        d = self - self.mean(dim, keepdim=True)
        return (d * d).sum(dim, keepdim) / float(n - 1 if unbiased else n)

    def std(self, dim=None, unbiased=True, keepdim=False):
        return self.var(dim, unbiased, keepdim) ** 0.5
    # @end

    # @build 02.03 __getitem__
    # x[index]: anything numpy takes (numbers, slices, arrays or tensors of
    # positions, a mask). Each number picked passes its gradient back to the
    # place it was picked from; np.add.at adds, so a place picked twice gets
    # both.
    def __getitem__(self, index):
        if isinstance(index, tuple):
            index = tuple(i.data if isinstance(i, Tensor) else i for i in index)
        elif isinstance(index, Tensor):
            index = index.data
        out = _result(self.data[index], (self,), "IndexBackward")
        if out.requires_grad:
            def _backward():
                g = np.zeros_like(self.data)
                np.add.at(g, index, out.grad.data)
                self._accumulate(g)
            out._backward = _backward
        return out
    # @end

    # @build 02.03 transpose
    # Swap two dimensions; the gradient swaps them back. .T reverses them all
    # (for a matrix, its transpose).
    def transpose(self, dim0, dim1):
        out = _result(np.swapaxes(self.data, dim0, dim1), (self,), "TransposeBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(np.swapaxes(out.grad.data, dim0, dim1))
            out._backward = _backward
        return out

    @property
    def T(self):
        out = _result(self.data.T, (self,), "PermuteBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad.data.T)
            out._backward = _backward
        return out
    # @end

    # @build 02.03 reshape
    # The same numbers in another shape (one dimension may be -1: whatever is
    # left); the gradient takes the input's shape back. view is the same here.
    def reshape(self, *shape):
        if len(shape) == 1 and isinstance(shape[0], (tuple, list)):
            shape = tuple(shape[0])
        out = _result(self.data.reshape(shape), (self,), "ViewBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad.data.reshape(self.data.shape))
            out._backward = _backward
        return out

    view = reshape
    # @end

    # @build 02.03 argmax
    # The position of the largest number, along dim. Positions have no
    # gradient.
    def argmax(self, dim=None, keepdim=False):
        return Tensor(np.argmax(self.data, axis=dim, keepdims=keepdim).astype(np.int64))
    # @end

    # @build 02.03 __eq__
    # Comparisons, number by number: tensors of True and False, with no
    # gradient. float() makes them 1.0 and 0.0 (a mean of them is a fraction).
    def __eq__(self, other):
        return Tensor(self.data == _as_tensor(other, self).data)

    def __ne__(self, other):
        return Tensor(self.data != _as_tensor(other, self).data)

    def __gt__(self, other):
        return Tensor(self.data > _as_tensor(other, self).data)

    def __lt__(self, other):
        return Tensor(self.data < _as_tensor(other, self).data)

    def __ge__(self, other):
        return Tensor(self.data >= _as_tensor(other, self).data)

    def __le__(self, other):
        return Tensor(self.data <= _as_tensor(other, self).data)

    def float(self):
        return self._cast(float32)

    def double(self):
        return self._cast(float64)

    def _cast(self, dtype):
        out = _result(self.data.astype(dtype), (self,), "ToCopyBackward")
        if out.requires_grad:
            def _backward():
                self._accumulate(out.grad.data.astype(self.data.dtype))
            out._backward = _backward
        return out
    # @end

    # @build 02.03 __isub__
    # a -= b, changing a's numbers where they are: how an update step moves
    # a weight. Allowed only where nothing is being recorded (inside no_grad,
    # or on a tensor that needs no gradient), since the graph would otherwise
    # hold a value that has changed under it.
    def __isub__(self, other):
        if GRAD_ENABLED and self.requires_grad:
            raise RuntimeError("a leaf Variable that requires grad is being used in an in-place operation.")
        self.data -= _as_tensor(other, self).data
        return self
    # @end


# ---------------------------------------------------------------- making tensors

def _result(data, parents, op):
    """The tensor an operation returns. It keeps its parents only when gradients are being
    recorded and one of them needs a gradient; otherwise it is a plain value."""
    needs = GRAD_ENABLED and any(p.requires_grad for p in parents)
    out = Tensor(data, requires_grad=needs)
    if needs:
        out._prev = parents
        out._op = op
    return out


def _as_tensor(x, like):
    """x as a Tensor: a plain number takes like's type when like holds floats (2.0 * a float32
    tensor stays float32, as in PyTorch)."""
    if isinstance(x, Tensor):
        return x
    if like.data.dtype.kind == "f":
        return Tensor(np.asarray(x, dtype=like.data.dtype))
    return tensor(x)


def tensor(data, dtype=None, requires_grad=False):
    """A new tensor holding a copy of data. Plain Python floats become float32 (PyTorch's
    default); a numpy array keeps its own type; dtype= sets one."""
    if isinstance(data, Tensor):
        data = data.data
    arr = np.array(data, dtype=dtype)
    if dtype is None and not isinstance(data, np.ndarray) and arr.dtype == np.float64:
        arr = arr.astype(np.float32)
    return Tensor(arr, requires_grad=requires_grad)


def from_numpy(arr):
    """A tensor over the array itself, not a copy, with its type."""
    return Tensor(arr)


def _size(size):
    return tuple(size[0]) if len(size) == 1 and isinstance(size[0], (tuple, list)) else tuple(size)


def zeros(*size, dtype=None, requires_grad=False):
    return Tensor(np.zeros(_size(size), dtype=float32 if dtype is None else dtype), requires_grad=requires_grad)


def ones(*size, dtype=None, requires_grad=False):
    return Tensor(np.ones(_size(size), dtype=float32 if dtype is None else dtype), requires_grad=requires_grad)


def zeros_like(t, dtype=None):
    return Tensor(np.zeros_like(t.data, dtype=dtype))


def ones_like(t, dtype=None):
    return Tensor(np.ones_like(t.data, dtype=dtype))


# The functions PyTorch also has at the top level: torch.tanh(x) is x.tanh().
def exp(x):
    return x.exp()


def log(x):
    return x.log()


def tanh(x):
    return x.tanh()


def relu(x):
    return x.relu()


def sigmoid(x):            # @from 04.03
    return x.sigmoid()     # @from 04.03


def matmul(a, b):          # @from 02.03
    return a @ b           # @from 02.03


# @from 02.05
# The engine's random numbers come from one numpy generator: starting
# weights, random tensors, dropout. manual_seed starts it again.
_GENERATOR = [np.random.default_rng(0)]


def generator():
    return _GENERATOR[0]
# @end


# @build 02.05 manual_seed
# Start the engine's generator again from seed, so that everything random
# after it (starting weights, dropout) is the same on every run. The
# numbers differ from PyTorch's for the same seed: its generator is not
# numpy's.
def manual_seed(seed):
    _GENERATOR[0] = np.random.default_rng(seed)
# @end


# @build 02.05 randn
# A random tensor from the generator, from the normal distribution (mean
# 0, variance 1).
def randn(*size, dtype=None, requires_grad=False):
    data = generator().standard_normal(_size(size)).astype(float32 if dtype is None else dtype)
    return Tensor(data, requires_grad=requires_grad)
# @end


# @build 02.05 rand
# A random tensor from the generator, uniform in [0, 1).
def rand(*size, dtype=None, requires_grad=False):
    data = generator().random(_size(size)).astype(float32 if dtype is None else dtype)
    return Tensor(data, requires_grad=requires_grad)
# @end


# @build 02.02 unbroadcast
# numpy broadcasts: a (3, 1) array and a (1, 4) array add to a (3, 4) one,
# each input repeated along the dimensions where it has 1 (or that it lacks
# on the left). Every repeat used the same input number, so the gradient
# that comes back in the output's shape is summed over those dimensions to
# give the input's: first the extra leading ones, then the ones of size 1.
def unbroadcast(g, shape):
    while g.ndim > len(shape):
        g = g.sum(axis=0)
    for i, n in enumerate(shape):
        if n == 1 and g.shape[i] != 1:
            g = g.sum(axis=i, keepdims=True)
    return g
# @end


# @build 02.03 no_grad
# with no_grad(): ... runs its block without recording a graph: what an
# update step and an evaluation need. The old setting comes back after the
# block, even when it raised.
class no_grad:
    def __enter__(self):
        global GRAD_ENABLED
        self.prev = GRAD_ENABLED
        GRAD_ENABLED = False

    def __exit__(self, *exc):
        global GRAD_ENABLED
        GRAD_ENABLED = self.prev
        return False
# @end
