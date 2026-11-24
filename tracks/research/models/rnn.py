"""A recurrent network, written by hand: one cell, the same weights at every step of a sequence (07.03).

    RNNCell(input_size, hidden_size)    one step: h = tanh(ih(x) + hh(h)), two Linear layers and a tanh
    RNN(input_size, hidden_size)        the cell run along a sequence, the state carried from step to step

The state h is all the network keeps of what it has read: each step mixes
the new input into it and squashes the sum with tanh. torch.nn.RNN
computes the same thing; its weights are named weight_ih_l0, bias_ih_l0,
weight_hh_l0 and bias_hh_l0 where these are cell.ih.weight, cell.ih.bias,
cell.hh.weight and cell.hh.bias (copy one's into the other and the two give
the same states). It starts its weights differently: every one uniform in
+-1/sqrt(hidden_size), where nn.Linear uses 1/sqrt of its own inputs.
"""

import torch
from torch import nn


# @build 07.03 RNNCell
# One step of the recurrence: the new state from the input x, of shape
# (batch, input_size), and the state before it, h, of shape (batch,
# hidden_size): tanh(ih(x) + hh(h)), ih and hh two Linear layers, each with
# its bias.
class RNNCell(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.ih = nn.Linear(input_size, hidden_size)
        self.hh = nn.Linear(hidden_size, hidden_size)

    def forward(self, x, h):
        return torch.tanh(self.ih(x) + self.hh(h))
# @end


# @build 07.03 RNN
# The cell along a sequence: x of shape (batch, steps, input_size), the
# state starting at h (zeros when None), the cell applied at every step in
# turn, unrolled in a Python loop, each step's new state fed to the next.
# Returns every step's state, (batch, steps, hidden_size), and the last.
class RNN(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.cell = RNNCell(input_size, hidden_size)
        self.hidden_size = hidden_size

    def forward(self, x, h=None):
        if h is None:
            h = x.new_zeros(x.shape[0], self.hidden_size)
        states = []
        for t in range(x.shape[1]):
            h = self.cell(x[:, t], h)
            states.append(h)
        return torch.stack(states, dim=1), h
# @end
