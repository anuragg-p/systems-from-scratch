"""The small convolutional network for CIFAR-10's images: 06.02 runs it on both libraries, 06.03
trains it. torch, its first argument, is the library it is built with: the engine or PyTorch."""


# @build 06.02 convnet
# Three 3 by 3 convolutions with width, 2 * width and 4 * width filters,
# each padded by one pixel and followed by a relu and a 2 by 2 max
# pooling: an image's 3 colour channels of 32 by 32 become width maps of
# 16 by 16, then 2 * width maps of 8 by 8, then 4 * width maps of 4 by 4.
# Then those maps in one row, and a Linear layer to the 10 scores.
def convnet(torch, width=32, classes=10):
    nn = torch.nn
    return nn.Sequential(nn.Conv2d(3, width, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                         nn.Conv2d(width, 2 * width, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                         nn.Conv2d(2 * width, 4 * width, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                         nn.Flatten(), nn.Linear(4 * width * 4 * 4, classes))
# @end
