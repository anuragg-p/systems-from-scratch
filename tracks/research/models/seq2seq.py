"""An encoder and a decoder: one sequence of symbols read, another written (07.04).

    Encoder(symbols, embed, hidden)              07.03's recurrent network over the input's embeddings
    Decoder(symbols, embed, hidden)              writes the output a symbol at a time from one state, which
                                                 starts as the encoder's last
    AttentionDecoder(symbols, embed, hidden, size)
                                                 the same, and at every step a weighted sum of all the
                                                 encoder's states, the weights its own (models/attention.py)
    Seq2Seq(encoder, decoder)                    the two together: forward(x, previous) scores every output
                                                 position from the right previous symbols (teacher forcing);
                                                 generate(x, length) writes from its own

Without attention, everything the decoder knows of the input has to pass
through one vector of `hidden` numbers, the encoder's last state, however
long the input is (Sutskever et al., 2014; Cho et al., 2014). Bahdanau,
Cho and Bengio (2015) let the decoder look back at every one of the
encoder's states instead, each step choosing its own weights.

A decoder's step takes the symbol it wrote last (START, numbered
`symbols`, before the first), its state, and the encoder's states, and
returns scores for the next symbol, its new state, and its attention
weights (None without attention).
"""

import torch
from torch import nn

from models.attention import Additive, attend
from models.rnn import RNN, RNNCell


# @build 07.04 Encoder
# The input symbols' embeddings read by a recurrent network (07.03): x of
# shape (batch, length) gives every step's state, (batch, length, hidden),
# and the last.
class Encoder(nn.Module):
    def __init__(self, symbols, embed, hidden):
        super().__init__()
        self.embed = nn.Embedding(symbols, embed)
        self.rnn = RNN(embed, hidden)

    def forward(self, x):
        return self.rnn(self.embed(x))
# @end


# @build 07.04 Decoder
# The decoder without attention: an embedding for each symbol and for
# START (symbols + 1 of them), one recurrent cell, and a Linear layer from
# its state to a score for each symbol. A step reads the previous symbol's
# embedding into the state; the encoder's states go unused.
class Decoder(nn.Module):
    def __init__(self, symbols, embed, hidden):
        super().__init__()
        self.embed = nn.Embedding(symbols + 1, embed)
        self.cell = RNNCell(embed, hidden)
        self.out = nn.Linear(hidden, symbols)

    def step(self, previous, h, states):
        h = self.cell(self.embed(previous), h)
        return self.out(h), h, None
# @end


# @build 07.04 AttentionDecoder
# The same decoder with attention, the paper's section 3.1: at each step,
# scores of its state before the step (the query) against every encoder
# state (the keys), and their softmax-weighted sum of the encoder states
# (the values): the context, (batch, hidden). The cell reads the previous
# symbol's embedding and the context side by side, and the scores of the
# next symbol come from the new state and the context side by side.
class AttentionDecoder(nn.Module):
    def __init__(self, symbols, embed, hidden, size):
        super().__init__()
        self.embed = nn.Embedding(symbols + 1, embed)
        self.score = Additive(hidden, hidden, size)
        self.cell = RNNCell(embed + hidden, hidden)
        self.out = nn.Linear(2 * hidden, symbols)

    def step(self, previous, h, states):
        context, weights = attend(self.score(h[:, None], states), states)
        context = context[:, 0]
        h = self.cell(torch.cat([self.embed(previous), context], dim=1), h)
        return self.out(torch.cat([h, context], dim=1)), h, weights[:, 0]
# @end


# @build 07.04 Seq2Seq
# The encoder and a decoder. forward(x, previous): the encoder reads x
# (batch, length); the decoder's state starts as the encoder's last, and
# at step i it is given previous[:, i], the symbol that should have come
# before (START, then the right output: teacher forcing, the way it is
# trained). Returns the scores (batch, steps, symbols) and the attention
# weights (batch, steps, length), or None. generate(x, length) is the
# same, each step given the symbol it scored highest at the step before:
# returns the symbols written and the weights.
class Seq2Seq(nn.Module):
    def __init__(self, encoder, decoder):
        super().__init__()
        self.encoder, self.decoder = encoder, decoder
        self.start = decoder.out.out_features

    def forward(self, x, previous):
        states, h = self.encoder(x)
        scores, weights = [], []
        for i in range(previous.shape[1]):
            s, h, w = self.decoder.step(previous[:, i], h, states)
            scores.append(s)
            weights.append(w)
        return torch.stack(scores, dim=1), None if weights[0] is None else torch.stack(weights, dim=1)

    def generate(self, x, length):
        states, h = self.encoder(x)
        symbol = torch.full((x.shape[0],), self.start, dtype=torch.long, device=x.device)
        written, weights = [], []
        for i in range(length):
            s, h, w = self.decoder.step(symbol, h, states)
            symbol = s.argmax(dim=1)
            written.append(symbol)
            weights.append(w)
        return torch.stack(written, dim=1), None if weights[0] is None else torch.stack(weights, dim=1)
# @end
