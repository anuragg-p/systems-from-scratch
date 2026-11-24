"""CIFAR-10: 60,000 small colour photographs, 32 by 32 pixels, each of one of 10 classes.

load("train") gives the 50,000 training images, load("test") the 10,000
test images, as numpy arrays: images as float32 of shape (n, 3, 32, 32),
the red, green and blue channel of each, labels as int64 (CLASSES names
them). The files are read from the cache data/fetch.py fills; when they
are not there, the script stops and says how to fetch them.

The files are the dataset's binary version, plain records of bytes: a
label byte (0 to 9), then the 3072 pixel bytes (0 to 255), the 1024 of
the red channel, then the green, then the blue, each 32 rows of 32. Five
training files of 10,000 records, and one test file.
"""

from functools import lru_cache

import numpy as np

from data import fetch

FILES = {"train": [f"data_batch_{i}.bin" for i in range(1, 6)], "test": ["test_batch.bin"]}
CLASSES = ("airplane", "automobile", "bird", "cat", "deer", "dog", "frog", "horse", "ship", "truck")
RECORD = 1 + 3 * 32 * 32

# The mean and standard deviation of each channel (red, green, blue) over
# every pixel of the 50,000 training images, on the scale 0 to 1.
MEAN = np.array([0.4914, 0.4822, 0.4465], dtype=np.float32)
STD = np.array([0.2470, 0.2435, 0.2616], dtype=np.float32)


# @build 06.03 read_records
# The images and labels in one file of records: its bytes as unsigned
# 8-bit numbers, in rows of RECORD (nothing marks where a record ends:
# each is exactly that long, so a file that is not a whole number of them
# is not one of these); the first byte of each row is its label, and the
# other 3072 are its pixels, in the shape (3, 32, 32).
def read_records(filename):
    raw = np.fromfile(filename, dtype=np.uint8)
    if raw.size % RECORD:
        raise ValueError(f"{filename}: {raw.size} bytes is not a whole number of {RECORD}-byte records")
    rows = raw.reshape(-1, RECORD)
    return rows[:, 1:].reshape(-1, 3, 32, 32), rows[:, 0]
# @end


# @build 06.03 load
# (images, labels) of one split, the first n when n is given: the records
# of its files in order, reading only as many files as n needs; images
# scaled to 0..1 and standardised channel by channel with MEAN and STD,
# as float32; labels as int64. Stops the script with the fetch command if
# the files are not in the cache. The arrays are shared between calls:
# copy one before changing it.
@lru_cache(maxsize=4)
def load(split="train", n=None):
    fetch.need("cifar10")
    images, labels = [], []
    for name in FILES[split]:
        if n is not None and sum(len(l) for l in labels) >= n:
            break
        x, y = read_records(fetch.path("cifar10", name))
        images.append(x)
        labels.append(y)
    x = np.concatenate(images)[:n].astype(np.float32) / 255
    x = (x - MEAN[:, None, None]) / STD[:, None, None]
    return x, np.concatenate(labels)[:n].astype(np.int64)
# @end
