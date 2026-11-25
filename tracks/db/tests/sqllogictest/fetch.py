#!/usr/bin/env python3
"""Fetch more of the sqllogictest corpus for a long run, into build/ (never into the repo).

Internal, for authors. The repo keeps a small subset (test/ next to this file); MANIFEST
lists every script of test/ at the pinned commit (index/, evidence/, random/ and
select1-5) with its size and SHA-256, and this fetches any of them from that commit and
checks each one.

    python3 tracks/db/tests/sqllogictest/fetch.py [pattern ...] [--dest DIR] [--verify]

    pattern     fnmatch patterns on the paths in MANIFEST, such as 'test/index/in/*'
                or 'test/random/*' (default: all of them, about 1.1 GB)
    --dest DIR  where to put them (default: build/sqllogictest at the top of the repo)
    --verify    fetch nothing: check the vendored files against MANIFEST

Then run them:

    python3 tracks/db/tests/sqllogictest/runner.py build/sqllogictest/test
"""

import concurrent.futures
import fnmatch
import hashlib
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
MIRROR = "gregrahn/sqllogictest"
COMMIT = "c93ac416f05635ff5cc490009add936d9753d01d"
URL = f"https://raw.githubusercontent.com/{MIRROR}/{COMMIT}/"


def manifest():
    """[(sha256, size, path)] from MANIFEST."""
    out = []
    with open(os.path.join(HERE, "MANIFEST")) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                h, n, p = line.split()
                out.append((h, int(n), p))
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(entry, dest):
    h, n, p = entry
    out = os.path.join(dest, p)
    if os.path.exists(out) and os.path.getsize(out) == n and sha256(out) == h:
        return p, "have"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with urllib.request.urlopen(URL + p, timeout=300) as r:
        data = r.read()
    if len(data) != n or hashlib.sha256(data).hexdigest() != h:
        return p, "BAD (size or SHA-256 differs from MANIFEST)"
    with open(out + ".part", "wb") as f:
        f.write(data)
    os.replace(out + ".part", out)
    return p, "fetched"


def main(args):
    dest = os.path.join(REPO, "build", "sqllogictest")
    if "--dest" in args:
        i = args.index("--dest")
        dest = os.path.abspath(args[i + 1])
        args = args[:i] + args[i + 2:]
    entries = manifest()
    if "--verify" in args:
        bad = 0
        n = 0
        for h, size, p in entries:
            local = os.path.join(HERE, p)
            if os.path.exists(local):
                n += 1
                if sha256(local) != h:
                    bad += 1
                    print(f"{p}: differs from MANIFEST")
        print(f"{n} vendored files checked, {bad} differ")
        return 1 if bad or not n else 0
    pats = [a for a in args if not a.startswith("-")]
    if pats:
        entries = [e for e in entries if any(fnmatch.fnmatch(e[2], p) for p in pats)]
    if not entries:
        sys.exit("nothing in MANIFEST matches")
    print(f"{len(entries)} files, {sum(e[1] for e in entries) / 1e6:.1f} MB, into {dest}")
    bad = 0
    with concurrent.futures.ThreadPoolExecutor(6) as ex:
        for p, what in ex.map(lambda e: fetch(e, dest), entries):
            if what.startswith("BAD"):
                bad += 1
                print(f"  {p}: {what}")
    print(f"done: {len(entries) - bad} ok, {bad} bad")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
