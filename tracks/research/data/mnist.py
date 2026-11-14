"""MNIST: 70,000 handwritten digits, 28 by 28 pixels, each with its label 0 to 9.

load("train") gives the 60,000 training images, load("test") the 10,000
test images, as numpy arrays: images as float32 rows of 784 numbers, labels
as int64. The files are read from the cache data/fetch.py fills; when they
are not there, the script stops and says how to fetch them.

The files are in IDX, a format of their own: gzip around a big-endian
header (a magic number, then the size of each dimension) and then the raw
bytes, one per pixel (0 white to 255 black) or one per label.
"""

import gzip
from functools import lru_cache

import numpy as np

from data import fetch

FILES = {"train": ("train-images-idx3-ubyte.gz", "train-labels-idx1-ubyte.gz"),
         "test": ("t10k-images-idx3-ubyte.gz", "t10k-labels-idx1-ubyte.gz")}

# The mean and standard deviation of every pixel of the training images, on
# the scale 0 to 1. Subtracting the one and dividing by the other centres
# the inputs on 0 with a spread of 1, the scale the starting weights assume.
MEAN, STD = 0.1307, 0.3081


# @build 03.01 read_idx
# The array in one IDX file: gunzip it; the magic number's third byte is the
# type (8: unsigned bytes, the only one MNIST uses) and its fourth the
# number of dimensions; then one big-endian 32-bit size per dimension; the
# rest is the data, in that shape.
def read_idx(filename):
    with gzip.open(filename, "rb") as f:
        raw = f.read()
    kind, ndim = raw[2], raw[3]
    if raw[:2] != b"\0\0" or kind != 8:
        raise ValueError(f"{filename}: not an IDX file of unsigned bytes")
    shape = tuple(int.from_bytes(raw[4 + 4 * i:8 + 4 * i], "big") for i in range(ndim))
    return np.frombuffer(raw, dtype=np.uint8, offset=4 + 4 * ndim).reshape(shape)
# @end


# @build 03.01 load
# (images, labels) of one split, the first n examples when n is given:
# each image flattened to 784 pixels and scaled to 0..1, then standardised
# with MEAN and STD unless standardise is False; labels as int64. Stops the
# script with the fetch command if the files are not in the cache. The
# arrays are shared between calls: copy one before changing it.
@lru_cache(maxsize=8)
def load(split="train", n=None, standardise=True):
    fetch.need("mnist")
    images_file, labels_file = FILES[split]
    images = read_idx(fetch.path("mnist", images_file))[:n]
    labels = read_idx(fetch.path("mnist", labels_file))[:n]
    x = images.reshape(len(images), 784).astype(np.float32) / 255
    if standardise:
        x = (x - MEAN) / STD
    return x, labels.astype(np.int64)
# @end
