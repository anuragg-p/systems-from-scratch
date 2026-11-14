"""engine: a small deep learning library over numpy, under PyTorch's names.

A script picks its engine in one line:

    import engine as torch        # this one
    import torch                  # PyTorch: the same script, unchanged

and from then on calls torch.tensor, torch.nn.Linear, torch.optim.Adam and
the rest. Only what the lessons use is here; each name behaves as
PyTorch's does, and the tests hold its gradients to PyTorch's.

The scalar engine of module 01 is engine.value, and the nudge is
engine.nudge; neither is part of PyTorch's names.
"""

from engine.tensors import Tensor, tensor, from_numpy, zeros, ones, zeros_like, ones_like     # @from 02.01
from engine.tensors import float32, float64, int64, bool, exp, log, tanh, relu                 # @from 02.01
from engine import autograd                                                                   # @from 02.02
from engine.tensors import no_grad, matmul                                                    # @from 02.03
from engine import nn                                                                         # @from 02.04
from engine.tensors import manual_seed, randn, rand                                           # @from 02.05
from engine import optim                                                                      # @from 03.01
from engine.tensors import sigmoid                                                            # @from 04.03
