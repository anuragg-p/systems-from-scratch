"""Optimisers: torch.optim.

An optimiser holds the parameters of a model and, after backward() has
filled their gradients, step() moves each one. They come in param_groups:
a list of dictionaries, each a list of parameters and the settings for
them ("lr", ...). A script may change a group's "lr" between steps; a
schedule does exactly that. What an optimiser remembers about a parameter
from one step to the next (a velocity, running averages) is in
self.state[p].

The arithmetic is done on the numpy arrays themselves, in place: the
update is not part of any graph.
"""

import numpy as np

from engine.optim import lr_scheduler          # @from 03.05


class Optimizer:
    """The bookkeeping every optimiser shares: param_groups, state and zero_grad()."""

    def __init__(self, params, defaults):
        self.defaults = defaults
        self.state = {}
        self.param_groups = []
        params = list(params)
        if not params:
            raise ValueError("optimizer got an empty parameter list")
        if not isinstance(params[0], dict):
            params = [{"params": params}]
        for group in params:
            self.param_groups.append({**defaults, **group, "params": list(group["params"])})

    def zero_grad(self, set_to_none=True):
        for group in self.param_groups:
            for p in group["params"]:
                p.grad = None

    def step(self):
        raise NotImplementedError


class SGD(Optimizer):
    """Stochastic gradient descent: each parameter moves against its gradient, lr times it."""

    # @build 03.01 __init__
    # The settings, with PyTorch's names and defaults, kept as the defaults of
    # every param_group.
    # @from 03.02
    def __init__(self, params, lr=1e-3, momentum=0.0, dampening=0.0, nesterov=False):
        if nesterov and (momentum <= 0 or dampening != 0):
            raise ValueError("Nesterov momentum requires a momentum and zero dampening")
        super().__init__(params, dict(lr=lr, momentum=momentum, dampening=dampening, nesterov=nesterov))
    # @else
    # def __init__(self, params, lr=1e-3):
    #     super().__init__(params, dict(lr=lr))
    # @end
    # @end

    # @build 03.01 step
    # Move every parameter that has a gradient by -lr times it, in place.
    def step(self):
        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue
                d_p = p.grad.data
                # @from 03.02
                if group["momentum"]:
                    d_p = self.momentum(p, d_p, group)
                # @end
                p.data -= group["lr"] * d_p
    # @end

    # @build 03.02 momentum
    # The direction to move p in, with momentum: a velocity kept in
    # self.state[p], the gradient itself on the first step, after that
    # momentum times the old velocity plus (1 - dampening) times the
    # gradient. Steps that keep the same sign build up speed; steps that flip
    # (across a narrow valley) cancel. Nesterov's variant moves by the
    # gradient plus momentum times the new velocity: a look one step ahead.
    def momentum(self, p, d_p, group):
        state = self.state.setdefault(p, {})
        buf = state.get("momentum_buffer")
        if buf is None:
            buf = state["momentum_buffer"] = d_p.copy()
        else:
            buf *= group["momentum"]
            buf += (1 - group["dampening"]) * d_p
        return d_p + group["momentum"] * buf if group["nesterov"] else buf
    # @end


# @from 03.03
class Adam(Optimizer):
    """Adam (Kingma and Ba, 2014): a step size for each parameter, from running averages of its
    gradient and of its gradient squared."""

    # @build 03.03 __init__
    # PyTorch's names and defaults. weight_decay here is PyTorch's for Adam:
    # weight_decay times the weight added to the gradient (L2), which lesson
    # 03.04 takes apart.
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0):
        super().__init__(params, dict(lr=lr, betas=betas, eps=eps, weight_decay=weight_decay))
    # @end

    # @build 03.03 step
    # For each parameter with a gradient g, keeping in self.state[p] a count
    # of steps t and two running averages: m of g (weight beta1 on the old
    # value) and v of g squared (beta2). Both start at 0, so early on they are
    # too small by a factor 1 - beta**t; divide that out. Then move the
    # parameter by -lr * m / (sqrt(v) + eps): about lr in the direction of
    # the gradient's sign wherever the gradient is steady, whatever its size.
    def step(self):
        for group in self.param_groups:
            lr, (beta1, beta2), eps = group["lr"], group["betas"], group["eps"]
            for p in group["params"]:
                if p.grad is None:
                    continue
                g = self.weight_decay(p, p.grad.data, group)
                state = self.state.setdefault(p, {})
                if not state:
                    state.update(step=0, exp_avg=np.zeros_like(p.data), exp_avg_sq=np.zeros_like(p.data))
                state["step"] += 1
                t, m, v = state["step"], state["exp_avg"], state["exp_avg_sq"]
                m *= beta1
                m += (1 - beta1) * g
                v *= beta2
                v += (1 - beta2) * g * g
                m_hat = m / (1 - beta1 ** t)
                v_hat = v / (1 - beta2 ** t)
                p.data -= lr * m_hat / (np.sqrt(v_hat) + eps)
    # @end

    # @build 03.03 weight_decay
    # PyTorch's Adam: the gradient plus weight_decay times the weight, as if
    # the loss had an L2 term. It then goes through Adam's division like
    # the rest of the gradient.
    def weight_decay(self, p, g, group):
        return g + group["weight_decay"] * p.data if group["weight_decay"] else g
    # @end
# @end


# @from 03.04
class AdamW(Adam):
    """AdamW (Loshchilov and Hutter, 2017): Adam with the weight decay taken out of the gradient."""

    # @build 03.04 __init__
    # Adam's settings, with PyTorch's default decay for AdamW, 0.01.
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=1e-2):
        super().__init__(params, lr, betas, eps, weight_decay)
    # @end

    # @build 03.04 weight_decay
    # Decoupled weight decay: shrink the weight itself by a fraction
    # lr * weight_decay, in place, and leave the gradient alone, so the decay
    # never goes through Adam's division and every weight decays at the same
    # rate whatever its gradients have been.
    def weight_decay(self, p, g, group):
        p.data *= 1 - group["lr"] * group["weight_decay"]
        return g
    # @end
# @end
