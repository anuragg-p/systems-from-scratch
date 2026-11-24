"""models: the networks experiments share, one file each, from 06.02 on.

A network is built by a function or a class in its own file, and an
experiment imports it (from models.convnet import convnet). convnet takes
the library as its first argument, as experiments/loop.py's functions do,
so that one function builds the same network on the engine and on
PyTorch; the models after it are PyTorch's only, and import torch.
"""
