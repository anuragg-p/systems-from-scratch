"""Fetch the datasets the track does not ship, once, into a cache outside the project.

    python3 -m data.fetch mnist      MNIST's four files, 11,594,722 bytes in all
    python3 -m data.fetch cifar10    CIFAR-10, one archive of 170,052,171 bytes, unpacked  # @from 06.03
    python3 -m data.fetch gpt2       GPT-2 small: its vocabulary, merges and weights, 549,603,790 bytes  # @from 09.02
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
# @from 06.03

CIFAR-10 (Krizhevsky, "Learning Multiple Layers of Features from Tiny
Images", 2009): its page states no licence and asks that this report be
cited. The binary version comes from that page as one archive; the six
files of records and the list of class names are taken out of it (each
checked as above) and the archive is deleted. Nothing is unpickled.
# @end
# @from 09.02

GPT-2 small (Radford et al., "Language Models are Unsupervised Multitask
Learners", 2019): OpenAI's vocabulary (vocab.json), merges (merges.txt)
and weights (model.safetensors), from the openai-community/gpt2
repository on Hugging Face at one fixed commit. Its model card gives the
licence as MIT, the repository's licence file a modified MIT. A dropped
connection carries on where it stopped.
# @end
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
    # @from 06.03
    "cifar10": {
        "url": "https://www.cs.toronto.edu/~kriz/",
        "archive": ("cifar-10-binary.tar.gz", 170052171, "c4a38c50a1bc5f3a1c5537f2155ab9d68f9f25eb1ed8d9ddda3db29a59bca1dd"),
        "folder": "cifar-10-batches-bin/",
        "files": {
            "data_batch_1.bin": (30730000, "cee916563c9f80d84e3cc88e17fdc0941787f1244f00a67874d45b261883ada5"),
            "data_batch_2.bin": (30730000, "a591ca11fa1708a91ee40f54b3da4784ccd871ecf2137de63f51ada8b3fa57ed"),
            "data_batch_3.bin": (30730000, "bbe8596564c0f86427f876058170b84dac6670ddf06d79402899d93ceea26f67"),
            "data_batch_4.bin": (30730000, "014e562d6e23c72197cc727519169a60359f5eccd8945ad5a09d710285ff4e48"),
            "data_batch_5.bin": (30730000, "755304fc0b379caeae8c14f0dac912fbc7d6cd469eb67a1029a08a39453a9add"),
            "test_batch.bin": (30730000, "8e2eb146ae340b09e24670f29cabc6326dba54da8789dab6768acf480273f65b"),
            "batches.meta.txt": (61, "558e74b5e208382e186da55784b4bac2cd52e558448e1b5800990fdb28ed8033"),
        },
    },
    # @end
    # @from 09.02
    "gpt2": {
        "url": "https://huggingface.co/openai-community/gpt2/resolve/607a30d783dfa663caf39e06633721c8d4cfcd7e/",
        "each": True,
        "files": {
            "vocab.json": (1042301, "196139668be63f3b5d6574427317ae82f612a97c5d1cdaf36ed2256dbf636783"),
            "merges.txt": (456318, "1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5"),
            "model.safetensors": (548105171, "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707"),
        },
    },
    # @end
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
    # @from 06.03
    if "archive" in spec:
        return fetch_archive(dataset)
    # @end
    # @from 09.02
    if spec.get("each"):
        return fetch_each(dataset)
    # @end
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


# @from 06.03
def fetch_archive(dataset):
    """A dataset that comes as one archive: download it (a dropped connection carries on where it
    stopped, five times at most), check its size and SHA-256, take each file out of it and check that
    too, keep the files and delete the archive."""
    import tarfile
    spec = DATASETS[dataset]
    files = spec["files"]
    if all(os.path.isfile(path(dataset, n)) and os.path.getsize(path(dataset, n)) == s and sha256(path(dataset, n)) == d
           for n, (s, d) in files.items()):
        print(f"{dataset}: all {len(files)} files in {os.path.join(cache_dir(), dataset)}")
        return
    name, size, digest = spec["archive"]
    part = path(dataset, name + ".part")
    print(f"  fetch {spec['url']}{name} ({size:,} bytes)", flush=True)
    for attempt in range(5):
        have = os.path.getsize(part) if os.path.isfile(part) else 0
        if have >= size:
            break
        request = urllib.request.Request(spec["url"] + name, headers={"Range": f"bytes={have}-"} if have else {})
        try:
            with urllib.request.urlopen(request, timeout=60) as r, open(part, "ab" if r.status == 206 else "wb") as f:
                while True:
                    block = r.read(1 << 16)
                    if not block:
                        break
                    f.write(block)
        except OSError as e:
            print(f"  the connection dropped ({e}); carrying on from byte {os.path.getsize(part):,}", flush=True)
    got_size, got = os.path.getsize(part), sha256(part)
    if got_size != size or got != digest:
        os.remove(part)
        sys.exit(f"{name}: got {got_size} bytes with SHA-256 {got}, expected {size} bytes with {digest}; nothing kept")
    with tarfile.open(part, "r:gz") as tar:
        for fname, (fsize, fdigest) in files.items():
            dest = path(dataset, fname)
            with tar.extractfile(spec["folder"] + fname) as src, open(dest + ".part", "wb") as out:
                out.write(src.read())
            got_size, got = os.path.getsize(dest + ".part"), sha256(dest + ".part")
            if got_size != fsize or got != fdigest:
                os.remove(dest + ".part")
                sys.exit(f"{fname} in {name}: got {got_size} bytes with SHA-256 {got}, expected {fsize} bytes "
                         f"with {fdigest}; not kept")
            os.replace(dest + ".part", dest)
            print(f"  keep  {fname}")
    os.remove(part)
    print(f"{dataset}: all {len(files)} files in {os.path.join(cache_dir(), dataset)}")
# @end


# @from 09.02
def fetch_each(dataset):
    """A dataset of separate files, some of them large: each one downloaded as fetch_archive downloads
    its archive (a dropped connection carries on where it stopped, five times at most), then checked
    and kept. A file that spec["ranges"] names is only a range of the bytes of a larger file on the
    server: (its name there, the first byte); its size is the length of the range."""
    spec = DATASETS[dataset]
    for name, (size, digest) in spec["files"].items():
        dest = path(dataset, name)
        if os.path.isfile(dest) and os.path.getsize(dest) == size and sha256(dest) == digest:
            print(f"  have  {name}")
            continue
        source, first = spec.get("ranges", {}).get(name, (name, 0))
        part = dest + ".part"
        what = f"bytes {first:,} to {first + size - 1:,} of " if source != name else ""
        print(f"  fetch {what}{spec['url']}{source} ({size:,} bytes)", flush=True)
        for attempt in range(5):
            have = os.path.getsize(part) if os.path.isfile(part) else 0
            if have >= size:
                break
            request = urllib.request.Request(spec["url"] + source,
                                             headers={"Range": f"bytes={first + have}-{first + size - 1}"})
            try:
                with urllib.request.urlopen(request, timeout=60) as r:
                    if r.status != 206 and first + have > 0:
                        sys.exit(f"{name}: the server sent the whole file, not the bytes asked for; nothing kept")
                    with open(part, "ab" if r.status == 206 else "wb") as f:
                        while True:
                            block = r.read(1 << 16)
                            if not block:
                                break
                            f.write(block)
            except OSError as e:
                print(f"  the connection dropped ({e}); carrying on from byte {os.path.getsize(part):,}", flush=True)
        got_size, got = os.path.getsize(part), sha256(part)
        if got_size != size or got != digest:
            os.remove(part)
            sys.exit(f"{name}: got {got_size} bytes with SHA-256 {got}, expected {size} bytes with {digest}; "
                     f"nothing kept")
        os.replace(part, dest)
        print(f"  keep  {name}")
    print(f"{dataset}: all {len(spec['files'])} files in {os.path.join(cache_dir(), dataset)}")
# @end


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
