"""A new head on a pretrained body: a GPT that sorts texts into classes (12.01).

    last_states(body, ids, lengths)   the body's vector at the last token of each text: what the head reads
    Classifier(body, classes, ...)    a GPT's body, and a Linear layer from that vector to a score for each class

Radford et al. (2018) fine-tuned a GPT to classify by reading "the final
transformer block's activation" at the last token of the input, which
they ended with a token of their own, and feeding it to "an added linear
output layer". GPT-2 has a token that ends a text already, <|endoftext|>
(END, 50256): the texts here end with it, and the head reads its vector.
The causal mask means that vector has looked at every token of the text
and at nothing after it, so a batch of texts of different lengths is
padded at the end and each text's vector is read where it ends.

GPT-2's vectors are lopsided: of the 768 numbers at a text's end, a few
are in the hundreds and vary by a few units from text to text, while
most vary by about 0.02. A new Linear layer started small learns from
them very slowly (12.01 shows it), so the head reads each number less
its mean over the training texts, over its spread there (standardise).

The body is models/gpt.py's GPT, untouched: the classifier uses its
embed, its blocks and its last layer norm, and leaves its scores for the
next token (the tied output) alone.
"""

import torch
from torch import nn
import torch.nn.functional as F


# @build 12.01 last_states
# The body's vector at the last token of each text, (batch, width): ids
# is (batch, T), each row a text then padding, lengths (batch,) how many
# tokens of each row are the text's own. The body runs as GPT.forward
# does, up to and including the last layer norm (embed, every block,
# norm), and the row of each text at position lengths - 1 is kept. The
# padding after it changes nothing: the mask keeps a position from
# looking at any after it.
def last_states(body, ids, lengths):
    x = body.embed(ids)
    for block in body.blocks:
        x = block(x)
    x = body.norm(x)
    return x[torch.arange(len(ids), device=ids.device), lengths - 1]
# @end


# @build 12.01 Classifier
# A GPT (body) with a new head: a Linear layer from the body's vector at
# each text's last token (last_states) to `classes` scores, started as
# GPT starts its layers (normal, sd 0.02, bias 0). The head reads that
# vector standardised: less center, over spread, two fixed vectors (not
# trained) that standardise(vectors) sets to the mean and the standard
# deviation of each number over the vectors given (the training texts',
# before any training); until then 0 and 1. dropout, when set, drops the
# standardised vector in training, as Radford et al. "add dropout to the
# classifier with a rate of 0.1". forward(ids, lengths) gives the scores,
# (batch, classes); features(ids, lengths) the body's vectors alone.
class Classifier(nn.Module):
    def __init__(self, body, classes, dropout=0.0):
        super().__init__()
        self.body = body
        width = body.tokens.weight.shape[1]
        self.head = nn.Linear(width, classes)
        nn.init.normal_(self.head.weight, 0.0, 0.02)
        nn.init.zeros_(self.head.bias)
        self.register_buffer("center", torch.zeros(width))
        self.register_buffer("spread", torch.ones(width))
        self.dropout = dropout

    def standardise(self, vectors):
        self.center.copy_(vectors.mean(0))
        self.spread.copy_(vectors.std(0))

    def features(self, ids, lengths):
        return last_states(self.body, ids, lengths)

    def scores(self, vectors):
        h = (vectors - self.center) / self.spread
        return self.head(F.dropout(h, self.dropout, self.training))

    def forward(self, ids, lengths):
        return self.scores(self.features(ids, lengths))
# @end
