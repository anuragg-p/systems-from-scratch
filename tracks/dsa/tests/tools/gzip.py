"""gzip and gunzip: DEFLATE in gzip files (module 09). T is track.py.

    Bits()              a bit writer packing as RFC 1951 does: .put(value, k) a number, lowest bit
                        first; .code(code, length) a Huffman code, highest bit first; .bytes()
    fixed_codes()       {"lit": [code], "dist": [code]} of the fixed codes, as (code, length) pairs
    canonical(lengths)  the canonical codes for those lengths (RFC 1951 3.2.2), as (code, length)
    member(raw, data, flg=0, extra=None, name=None, comment=None, hcrc=False, crc=None, size=None)
                        a gzip member around raw DEFLATE data standing for data: a header with those
                        fields, and the trailer (data's CRC-32 and size unless given)
    zlib_variants(data) [(what, gzip bytes)]: Python's zlib at every level and strategy, small
                        windows and small memory, raw data wrapped by member() and zlib's own framing
    zip_deflate(t, path)
                        the raw DEFLATE data the system's zip (Info-ZIP's own deflate, not zlib)
                        writes for path, or None when there is no zip
    unescape(s)         the bytes of a trace's quoted text ("a\\n\\x00")
    tokens(err, who)    the DS_TRACE literal and match lines of who ("lz77" or "inflate"):
                        [(pos, dist, length, bytes)], dist 0 for a literal
    rebuild(toks)       the bytes those tokens stand for, checking each match against the window
    huffman_table(out)  gzip --huffman's rows {byte: (count, length, code)} and its summary numbers
    huffman_cost(counts)
                        the fewest bits any prefix code can give those counts (Huffman, by heapq)
    roundtrip(t, path, args=())
                        bin/gzip args -c path; checks that the system's gunzip and gzip -t, our
                        gunzip and Python's zlib all give path's bytes back; returns gzip's Result
"""

import heapq
import os
import re
import struct
import zlib

from harness.core import Fail

PROGRAMS = {"gzip": "09.01", "gunzip": "09.02"}
FILES_FROM = {
    "tools/gzip/tool.mk": "09.01",
    "lib/huffman.h": "09.01",
    "lib/inflate.h": "09.02",
    "tools/gzip/gz.h": "09.02",
    "lib/lz77.h": "09.03",
    "lib/deflate.h": "09.04",
}
# The brief for the lesson writers, and what the top-level NOTICE takes from this module.
HIDDEN = ["tools/gzip/NOTES.md", "tools/gzip/NOTICE.txt"]
UPSTREAM = [
    {"name": "DEFLATE and gzip, RFC 1951 and RFC 1952",
     "url": "https://www.rfc-editor.org/rfc/rfc1951",
     "copyright": "Copyright (c) 1996 L. Peter Deutsch",
     "licence": "Free to copy and distribute with the notice kept (the RFCs' own licence)",
     "owes": "No code. Our gzip and gunzip are written from the two RFCs, and each reads what the "
             "system's gzip writes and writes what the system's gunzip reads.",
     "derived": False,
     "also": [("RFC 1952: GZIP file format specification", "https://www.rfc-editor.org/rfc/rfc1952")]},
    {"name": "GNU gzip",
     "url": "https://www.gnu.org/software/gzip/",
     "licence": "GPL-3.0-or-later",
     "owes": "No code. On Linux our gunzip reads what it writes at every level, and it reads what ours writes.",
     "derived": False},
]


# ---------------------------------------------------------------- writing DEFLATE by hand

class Bits:
    def __init__(self):
        self.acc, self.n, self.out = 0, 0, bytearray()

    def put(self, value, k):
        self.acc |= (value & ((1 << k) - 1)) << self.n
        self.n += k
        while self.n >= 8:
            self.out.append(self.acc & 0xFF)
            self.acc >>= 8
            self.n -= 8
        return self

    def code(self, code, length):
        for i in range(length - 1, -1, -1):
            self.put((code >> i) & 1, 1)
        return self

    def align(self):
        if self.n:
            self.put(0, 8 - self.n)
        return self

    def bytes(self):
        return bytes(self.align().out)


def canonical(lengths):
    count = [0] * 33
    for n in lengths:
        count[n] += 1
    count[0] = 0
    nxt, code = [0] * 33, 0
    for b in range(1, 33):
        code = (code + count[b - 1]) << 1
        nxt[b] = code
    out = []
    for n in lengths:
        if n:
            out.append((nxt[n], n))
            nxt[n] += 1
        else:
            out.append((0, 0))
    return out


def fixed_codes():
    lit = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
    return {"lit": canonical(lit), "dist": canonical([5] * 32)}


def crc32(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def member(raw, data, flg=0, extra=None, name=None, comment=None, hcrc=False, crc=None, size=None, mtime=0):
    flg |= (4 if extra is not None else 0) | (8 if name is not None else 0) | (16 if comment is not None else 0) \
        | (2 if hcrc else 0)
    h = bytearray(b"\x1f\x8b\x08" + bytes([flg]) + struct.pack("<I", mtime) + b"\x00\x03")
    if extra is not None:
        h += struct.pack("<H", len(extra)) + extra
    if name is not None:
        h += name + b"\x00"
    if comment is not None:
        h += comment + b"\x00"
    if hcrc:
        h += struct.pack("<H", crc32(bytes(h)) & 0xFFFF)
    crc = crc32(data) if crc is None else crc
    size = len(data) & 0xFFFFFFFF if size is None else size
    return bytes(h) + raw + struct.pack("<II", crc, size)


def zlib_variants(data):
    """Python's zlib (the system's libz) writing data every way worth reading."""
    out = []
    strategies = [("default", zlib.Z_DEFAULT_STRATEGY), ("filtered", zlib.Z_FILTERED),
                  ("huffman-only", zlib.Z_HUFFMAN_ONLY), ("rle", zlib.Z_RLE), ("fixed", zlib.Z_FIXED)]
    for level in range(0, 10):
        for sname, strategy in strategies:
            c = zlib.compressobj(level, zlib.DEFLATED, -15, 8, strategy)
            out.append((f"zlib -{level} {sname}", member(c.compress(data) + c.flush(), data)))
    for wbits in (9, 10, 12):
        for mem in (1, 9):
            c = zlib.compressobj(9, zlib.DEFLATED, -wbits, mem)
            out.append((f"zlib window 2^{wbits} memLevel {mem}", member(c.compress(data) + c.flush(), data)))
    c = zlib.compressobj(6, zlib.DEFLATED, 31)                  # zlib's own gzip header and trailer
    out.append(("zlib's gzip framing", c.compress(data) + c.flush()))
    c = zlib.compressobj(6, zlib.DEFLATED, -15)                 # flushed: empty stored blocks mid-stream
    raw = b""
    for i in range(0, len(data), 1000):
        raw += c.compress(data[i:i + 1000]) + c.flush(zlib.Z_SYNC_FLUSH if i % 2000 else zlib.Z_FULL_FLUSH)
    out.append(("zlib with sync and full flushes", member(raw + c.flush(), data)))
    return out


def zip_deflate(t, path):
    """The raw DEFLATE data Info-ZIP's zip writes for the file, from the zip's local header."""
    if not T.have("zip"):
        return None
    z = os.path.join(t.tmp, "zipped.zip")
    if os.path.exists(z):
        os.remove(z)
    T.system(t, ["zip", "-q", "-9", "-j", z, path])
    with open(z, "rb") as f:
        blob = f.read()
    sig, _, _, method, _, _, _, csize, _, nlen, xlen = struct.unpack("<IHHHHHIIIHH", blob[:30])
    if sig != 0x04034B50 or method != 8:
        raise Fail(f"zip wrote a header we did not expect (method {method})")
    start = 30 + nlen + xlen
    return blob[start:start + csize]


# ---------------------------------------------------------------- reading what the tools print

def unescape(s):
    out, i = bytearray(), 0
    while i < len(s):
        c = s[i]
        if c != "\\":
            out.append(ord(c))
            i += 1
        elif s[i + 1] == "x":
            out.append(int(s[i + 2:i + 4], 16))
            i += 4
        else:
            out.append({"n": 10, "t": 9}.get(s[i + 1], ord(s[i + 1])))
            i += 2
    return bytes(out)


TOKEN = re.compile(r'^trace: (\w+): (\d+): (?:literal|match distance (\d+) length (\d+)) "(.*)"$', re.M)


def tokens(err, who):
    return [(int(m.group(2)), int(m.group(3) or 0), int(m.group(4) or 1), unescape(m.group(5)))
            for m in TOKEN.finditer(err) if m.group(1) == who]


def rebuild(toks):
    out = bytearray()
    for pos, dist, length, text in toks:
        if pos != len(out):
            raise Fail(f"a token at {pos}, but {len(out)} bytes so far")
        if dist == 0:
            out += text
            continue
        if not (3 <= length <= 258 and 1 <= dist <= 32768 and dist <= len(out)):
            raise Fail(f"a match at {pos} of length {length}, distance {dist}: out of range")
        for _ in range(length):
            out.append(out[-dist])
        if bytes(out[-length:]) != text:
            raise Fail(f"the match at {pos} says {text!r}, but copies {bytes(out[-length:])!r}")
    return bytes(out)


ROW = re.compile(r"^('(?:\\x[0-9a-f]{2}|\\.|.)')\s+(\d+)\s+(\d+)\s+([01]+)$")
SUMMARY = re.compile(r"^(\d+) bytes, (\d+) different: (\d+) bits as bytes, (\d+) bits in these codes \((\d+) bytes\)$")


def huffman_table(out):
    lines = out.splitlines()
    if not lines or lines[0].split() != ["byte", "count", "bits", "code"]:
        raise Fail(f"gzip --huffman: no header line:\n{out[:500]}")
    rows = {}
    for line in lines[1:-1]:
        m = ROW.match(line)
        if not m:
            raise Fail(f"gzip --huffman: not a row: {line!r}")
        b = unescape(m.group(1)[1:-1].replace("\\'", "'"))
        if len(b) != 1:
            raise Fail(f"gzip --huffman: not one byte: {line!r}")
        rows[b[0]] = (int(m.group(2)), int(m.group(3)), m.group(4))
    m = SUMMARY.match(lines[-1])
    if not m:
        raise Fail(f"gzip --huffman: not a summary: {lines[-1]!r}")
    return rows, [int(x) for x in m.groups()]


def huffman_cost(counts):
    """Each join adds its weight once for every leaf below it: the sum of the joins is the bits."""
    h = [c for c in counts if c > 0]
    if len(h) == 1:
        return h[0]
    heapq.heapify(h)
    total = 0
    while len(h) > 1:
        a, b = heapq.heappop(h), heapq.heappop(h)
        total += a + b
        heapq.heappush(h, a + b)
    return total


# ---------------------------------------------------------------- round trips

def roundtrip(t, path, args=()):
    with open(path, "rb") as f:
        data = f.read()
    r = T.run(t, "gzip", list(args) + ["-c", path], env={"DS_STATS": "1"})
    gz = T.write(t, "roundtrip.gz", r.raw)
    T.system(t, ["gzip", "-t", gz])
    if T.system(t, ["gunzip", "-c", gz]).raw != data:
        raise Fail(f"the system's gunzip does not give {path} back from bin/gzip {' '.join(args)}")
    if T.run(t, "gunzip", ["-c", gz]).raw != data:
        raise Fail(f"bin/gunzip does not give {path} back from bin/gzip {' '.join(args)}")
    if zlib.decompress(r.raw, 31) != data:
        raise Fail(f"Python's zlib does not give {path} back from bin/gzip {' '.join(args)}")
    return r


# ---------------------------------------------------------------- the project at each lesson

ABRA = ("byte      count  bits  code\n"
        "'a'           5     1  0\n"
        "'b'           2     3  100\n"
        "'c'           1     3  101\n"
        "'d'           1     3  110\n"
        "'r'           2     3  111\n"
        "11 bytes, 5 different: 88 bits as bytes, 23 bits in these codes (3 bytes)\n")

USAGE = ["gzip: usage: gzip --huffman [file]",
         "       gzip --lz77 [--algo=NAME] [--chain=N] [file]"]


def timeline_steps(k):
    if k < (9, 1):
        return []
    steps = [T.sh_step("printf abracadabra | bin/gzip --huffman", ABRA)]
    if k >= (9, 2):
        steps += [T.sh_step("printf 'hello hello hello\\n' | gzip -9 | bin/gunzip", "hello hello hello\n"),
                  T.sh_step("printf 'not gzip' | bin/gunzip",
                            "gunzip: stdin: not in gzip format (it starts 6e 6f, not 1f 8b)\n", 2),
                  T.sh_step("printf 'hello\\n' | gzip | head -c 12 | bin/gunzip",
                            "gunzip: stdin: the data ends in the middle of a block\n", 2)]
    if k < (9, 3):
        steps.append(T.sh_step("bin/gzip < /dev/null", USAGE[0] + "\n", 2))
    else:
        steps += [T.sh_step("printf 'abcabcabcabc' | bin/gzip --lz77",
                            "12 bytes: 3 literals, 1 matches for the other 9 bytes\n"),
                  T.sh_step("printf 'abcabcabcabc' | bin/gzip --lz77 --algo=scan",
                            "12 bytes: 3 literals, 1 matches for the other 9 bytes\n")]
    if k < (9, 4):
        if k >= (9, 3):
            steps.append(T.sh_step("bin/gzip < /dev/null", USAGE[0] + "\n" + USAGE[1] + "\n", 2))
        steps.append(T.sh_step("bin/gzip -9 < /dev/null", None, 2, regex=r"gzip: usage: [^\n]*\r?\n(.*\r?\n)?"))
    else:
        steps += [T.sh_step("printf 'hello hello hello\\n' | bin/gzip -9 | gzip -dc", "hello hello hello\n"),
                  T.sh_step("printf 'hello hello hello\\n' | bin/gzip --blocks=dynamic | bin/gunzip",
                            "hello hello hello\n"),
                  T.sh_step("bin/gzip -c --blocks=huge < /dev/null",
                            "gzip: no --blocks 'huge' (have: best, stored, fixed, dynamic)\n", 2)]
    return steps


def timeline_after(root, k):
    if k < (9, 1):
        return None
    book = T.data(root, "book.txt")
    with open(book, "rb") as f:
        data = f.read()
    rows, summary = huffman_table(T.run(root, "gzip", ["--huffman", book]).out)
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    if summary[3] != huffman_cost(counts):
        raise Fail(f"gzip --huffman on the book: {summary[3]} bits, but a Huffman code takes {huffman_cost(counts)}")
    note = f"gzip --huffman: the book in {summary[3]} bits"
    if k >= (9, 2):
        gz = T.system(root, ["gzip", "-9", "-c", book]).raw
        if T.run(root, "gunzip", ["-c"], input=gz).raw != data:
            raise Fail("bin/gunzip does not give the book back from the system's gzip -9")
        note += "; gunzip: the book back from the system's gzip"
    if k >= (9, 4):
        gz = T.run(root, "gzip", ["-c", book]).raw
        if T.system(root, ["gunzip", "-c"], input=gz).raw != data:
            raise Fail("the system's gunzip does not give the book back from bin/gzip")
        note += f"; gzip: the book in {len(gz)} bytes, which the system's gunzip reads"
    return note
