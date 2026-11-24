"""The residual network of He et al. (2015) for CIFAR-10, section 4.2, and its plain twin.

    resnet(n, residual=True, width=16)

6n + 2 layers with weights: a 3 by 3 convolution of `width` filters on
the image; three stages of 2n convolutions, all 3 by 3, with width, 2 *
width and 4 * width filters on maps of 32 by 32, 16 by 16 and 8 by 8
(the first convolution of the second and third stages steps 2 pixels at
a time, halving the map); then the mean of each final map over all its
positions, and one Linear layer to the 10 scores. Batch normalisation
after every convolution, then a relu. The paper's width is 16; n = 3, 5,
7, 9 give its 20, 32, 44 and 56 layers.

The convolutions come in pairs, and the residual network adds a shortcut
around each pair: the pair's input added to its output before the second
relu. When a pair halves the map and doubles the filters, the shortcut
is the paper's option A, which adds no weights: every second pixel of
every second row of the input, and zeros for the new channels. So the
plain and the residual network have exactly the same weights, as in the
paper; residual=False builds the plain one from the same code.
"""

import torch
from torch import nn
import torch.nn.functional as F


# @build 06.04 Block
# Two 3 by 3 convolutions, each followed by batch normalisation (no
# bias: batch norm's shift does its job), with a relu between them and
# one after. The first steps `stride` pixels at a time (2 halves the map)
# and goes from c_in to c_out channels. With residual, the block's input
# is added to the second batch norm's output before the last relu; when
# the shape changes, the input is cut to every stride-th pixel of every
# stride-th row and padded with c_out - c_in channels of zeros (F.pad
# pads the last dimensions first: width, height, then channels).
class Block(nn.Module):
    def __init__(self, c_in, c_out, stride, residual):
        super().__init__()
        self.conv1 = nn.Conv2d(c_in, c_out, 3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(c_out)
        self.conv2 = nn.Conv2d(c_out, c_out, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(c_out)
        self.stride, self.extra, self.residual = stride, c_out - c_in, residual

    def forward(self, x):
        out = self.bn2(self.conv2(F.relu(self.bn1(self.conv1(x)))))
        if self.residual:
            shortcut = x[:, :, ::self.stride, ::self.stride]
            if self.extra:
                shortcut = F.pad(shortcut, (0, 0, 0, 0, 0, self.extra))
            out = out + shortcut
        return F.relu(out)
# @end


# @build 06.04 ResNet
# The whole network: the first convolution with its batch norm and relu,
# then the three stages of n blocks each (the first block of the second
# and third stages has stride 2 and doubles the channels), the mean over
# every position of each of the last stage's maps, and the Linear layer.
# Every convolution starts as He et al. start them (normal, variance 2 /
# fan_in, 04.02), every batch norm at weight 1 and bias 0.
class ResNet(nn.Module):
    def __init__(self, n, residual=True, width=16, classes=10):
        super().__init__()
        self.conv = nn.Conv2d(3, width, 3, padding=1, bias=False)
        self.bn = nn.BatchNorm2d(width)
        blocks, c = [], width
        for stage in range(3):
            for i in range(n):
                c_out = width * 2 ** stage
                blocks.append(Block(c, c_out, 2 if stage > 0 and i == 0 else 1, residual))
                c = c_out
        self.blocks = nn.Sequential(*blocks)
        self.fc = nn.Linear(c, classes)
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, nonlinearity="relu")

    def forward(self, x):
        x = self.blocks(F.relu(self.bn(self.conv(x))))
        return self.fc(x.mean((2, 3)))
# @end


def resnet(n, residual=True, width=16):
    """The paper's network of 6n + 2 layers: residual, or plain with residual=False."""
    return ResNet(n, residual, width)


def layers(model):
    """How many layers have weights: every convolution and the Linear layer (6n + 2)."""
    return sum(1 for m in model.modules() if isinstance(m, (nn.Conv2d, nn.Linear)))
