"""Fetch the datasets the track does not ship, once, into a cache outside the project.

    python3 -m data.fetch mnist      MNIST's four files, 11,594,722 bytes in all
    python3 -m data.fetch            what can be fetched, and whether it is here

Nothing else in the track downloads anything. A script that needs a dataset
that is not here stops with one line that names this command.

The cache is $LEARN_CACHE when that is set, else ~/.cache/systems-from-scratch,
one folder per dataset. Every file is checked against the size and SHA-256
written below before it is kept, so what you train on is byte for byte what
these lessons were run on.

MNIST (LeCun, Cortes and Burges): its own page no longer serves the files
and states no licence; these are the original four files, from the mirror
torchvision uses. They are not part of this project and are not copied
into it.
"""

import hashlib
import os
import sys
import urllib.request

DATASETS = {
    "mnist": {
        "url": "https://ossci-datasets.s3.amazonaws.com/mnist/",
        "files": {
            "train-images-idx3-ubyte.gz": (9912422, "440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609"),
            "train-labels-idx1-ubyte.gz": (28881, "3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c"),
            "t10k-images-idx3-ubyte.gz": (1648877, "8d422c7b0a1c1c79245a5bcf07fe86e33eeafee792b84584aec276f5a2dbc4e6"),
            "t10k-labels-idx1-ubyte.gz": (4542, "f7ae60f92e00ec6debd23a6088c31dbd2371eca3ffa0defaefb259924204aec6"),
        },
    },
}


def cache_dir():
    return os.environ.get("LEARN_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "systems-from-scratch")


def path(dataset, name):
    return os.path.join(cache_dir(), dataset, name)


def missing(dataset):
    """The files of dataset that are not in the cache at their right size: [] when it is all here."""
    return [name for name, (size, _) in DATASETS[dataset]["files"].items()
            if not os.path.isfile(path(dataset, name)) or os.path.getsize(path(dataset, name)) != size]


def need(dataset):
    """Stop the script with one line, naming the fetch command, unless dataset is all here."""
    if missing(dataset):
        sys.exit(f"{dataset} is missing: it is not in {os.path.join(cache_dir(), dataset)}. "
                 f"Fetch it once with: python3 -m data.fetch {dataset}")


def sha256(filename):
    h = hashlib.sha256()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(dataset):
    spec = DATASETS[dataset]
    os.makedirs(os.path.join(cache_dir(), dataset), exist_ok=True)
    for name, (size, digest) in spec["files"].items():
        dest = path(dataset, name)
        if os.path.isfile(dest) and os.path.getsize(dest) == size and sha256(dest) == digest:
            print(f"  have  {name}")
            continue
        part = dest + ".part"
        print(f"  fetch {spec['url']}{name} ({size:,} bytes)", flush=True)
        with urllib.request.urlopen(spec["url"] + name, timeout=60) as r, open(part, "wb") as f:
            while True:
                block = r.read(1 << 16)
                if not block:
                    break
                f.write(block)
        got_size, got = os.path.getsize(part), sha256(part)
        if got_size != size or got != digest:
            os.remove(part)
            sys.exit(f"{name}: got {got_size} bytes with SHA-256 {got}, expected {size} bytes with {digest}; "
                     f"nothing kept")
        os.replace(part, dest)
    print(f"{dataset}: all {len(spec['files'])} files in {os.path.join(cache_dir(), dataset)}")


def main(argv):
    if not argv:
        for name in DATASETS:
            state = "here" if not missing(name) else "not fetched"
            print(f"{name:8s} {state:12s} {os.path.join(cache_dir(), name)}")
        return 0
    for name in argv:
        if name not in DATASETS:
            sys.exit(f"no dataset {name!r} (have: {', '.join(DATASETS)})")
        fetch(name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
