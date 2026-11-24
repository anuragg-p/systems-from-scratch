"""Checkpoints in the safetensors format, from numpy arrays.

The file is three parts, nothing else:

    8 bytes        N, the length of the header, an unsigned 64-bit integer, little-endian
    N bytes        the header: JSON, {"name": {"dtype": "F32", "shape": [16, 2],
                   "data_offsets": [begin, end]}, ...}, and optionally "__metadata__":
                   {text: text}; padded with spaces so the data starts at a multiple of 8
    the rest       every tensor's numbers, little-endian, row after row, back to back;
                   each tensor's begin and end count bytes from the start of this part

It holds only numbers and names: loading one runs no code, unlike a pickle.
save_file and load_file take and give a dictionary of numpy arrays, as the
safetensors library's numpy functions do, so the real library opens what
these write and the other way round. A model's state_dict goes in as
{name: tensor.detach().numpy()}, from this engine or PyTorch alike.
"""

import json
import os                                                           # @from 09.03
import struct

import numpy as np

DTYPES = {"F64": np.float64, "F32": np.float32, "F16": np.float16, "I64": np.int64, "I32": np.int32,
          "I16": np.int16, "I8": np.int8, "U8": np.uint8, "BOOL": np.bool_}
CODES = {np.dtype(v): k for k, v in DTYPES.items()}
DTYPES["BF16"] = np.uint16    # read as its 16 bits, then widened by bfloat16() (load_file); never written  # @from 10.04


# @build 02.05 save_file
# Write the arrays in tensors (a dict of name -> numpy array) to filename,
# in name order: the header lists each one's type code, shape and byte
# range, the metadata (a dict of text -> text) goes in "__metadata__" when
# given, the header is padded with spaces to make 8 + N a multiple of 8,
# and then each array's bytes follow, as little-endian in C order.
def save_file(tensors, filename, metadata=None):
    header, chunks, offset = {}, [], 0
    if metadata:
        header["__metadata__"] = {str(k): str(v) for k, v in metadata.items()}
    for name in sorted(tensors):
        arr = np.asarray(tensors[name])
        if arr.dtype not in CODES:
            raise ValueError(f"{name}: no safetensors type for {arr.dtype}")
        data = np.ascontiguousarray(arr, dtype=arr.dtype.newbyteorder("<")).tobytes()
        header[name] = {"dtype": CODES[arr.dtype], "shape": list(arr.shape),
                        "data_offsets": [offset, offset + len(data)]}
        chunks.append(data)
        offset += len(data)
    text = json.dumps(header, separators=(",", ":")).encode("utf-8")
    text += b" " * (-(8 + len(text)) % 8)
    with open(filename, "wb") as f:
        f.write(struct.pack("<Q", len(text)))
        f.write(text)
        for data in chunks:
            f.write(data)
# @end


# @build 02.05 load_file
# The arrays in filename, as a dict of name -> numpy array (each its own
# writable copy). Checks what a reader must: the header fits in the file,
# every type code is known, each tensor's byte range is the size its shape
# and type say, and the ranges cover the data part exactly, in order, with
# no gaps and no overlaps. Anything else is a ValueError, not a guess.
def load_file(filename):
    # @from 09.03
    # Read in place: the header, its checks, then each tensor's bytes from
    # the file straight into an array of its own (np.fromfile). Reading the
    # whole file and copying out of it held the file four times over at the
    # peak: 2.1 GB for GPT-2's 548 MB (09.03).
    size = os.path.getsize(filename)
    with open(filename, "rb") as f:
        if size < 8:
            raise ValueError(f"{filename}: too short to be a safetensors file")
        (n,) = struct.unpack("<Q", f.read(8))
        if 8 + n > size:
            raise ValueError(f"{filename}: header of {n} bytes in a file of {size}")
        header = json.loads(f.read(n))
        header.pop("__metadata__", None)
        specs, end = sorted(header.items(), key=lambda kv: kv[1]["data_offsets"]), 0
        for name, spec in specs:
            if spec["dtype"] not in DTYPES:
                raise ValueError(f"{name}: unknown dtype {spec['dtype']}")
            begin, stop = spec["data_offsets"]
            if begin != end or stop - begin != int(np.prod(spec["shape"])) * np.dtype(DTYPES[spec["dtype"]]).itemsize:
                raise ValueError(f"{name}: bytes {begin} to {stop} do not follow on from {end} "
                                 f"at the size of a {spec['dtype']} {spec['shape']}")
            end = stop
        if end != size - 8 - n:
            raise ValueError(f"{filename}: {size - 8 - n - end} bytes after the last tensor")
        out = {}
        for name, spec in specs:
            dtype = np.dtype(DTYPES[spec["dtype"]]).newbyteorder("<")
            count = int(np.prod(spec["shape"]))
            out[name] = np.fromfile(f, dtype=dtype, count=count).reshape(spec["shape"]).astype(
                dtype.newbyteorder("="), copy=False)
            # @from 10.04
            if spec["dtype"] == "BF16":
                out[name] = bfloat16(out[name])
            # @end
    return out
    # @else
    # with open(filename, "rb") as f:
    #     raw = f.read()
    # if len(raw) < 8:
    #     raise ValueError(f"{filename}: too short to be a safetensors file")
    # (n,) = struct.unpack("<Q", raw[:8])
    # if 8 + n > len(raw):
    #     raise ValueError(f"{filename}: header of {n} bytes in a file of {len(raw)}")
    # header = json.loads(raw[8:8 + n])
    # header.pop("__metadata__", None)
    # data = bytearray(raw[8 + n:])
    # out, end = {}, 0
    # for name, spec in sorted(header.items(), key=lambda kv: kv[1]["data_offsets"]):
    #     if spec["dtype"] not in DTYPES:
    #         raise ValueError(f"{name}: unknown dtype {spec['dtype']}")
    #     dtype = np.dtype(DTYPES[spec["dtype"]]).newbyteorder("<")
    #     begin, stop = spec["data_offsets"]
    #     if begin != end or stop - begin != int(np.prod(spec["shape"])) * dtype.itemsize:
    #         raise ValueError(f"{name}: bytes {begin} to {stop} do not follow on from {end} "
    #                          f"at the size of a {spec['dtype']} {spec['shape']}")
    #     out[name] = np.frombuffer(data, dtype=dtype, count=(stop - begin) // dtype.itemsize,
    #                               offset=begin).reshape(spec["shape"]).astype(dtype.newbyteorder("="))
    #     end = stop
    # if end != len(data):
    #     raise ValueError(f"{filename}: {len(data) - end} bytes after the last tensor")
    # return out
    # @end
# @end


# @build 10.04 bfloat16
# bfloat16 numbers (BF16), given as their 16 bits (an array of uint16),
# as the float32 numbers they are; numpy has no bfloat16. A bfloat16 is
# the top half of a float32: the sign, the 8 bits of the exponent and the
# first 7 of the 23 bits of the fraction. So the 16 bits moved into the
# top half of 32 (the bottom half zeros) and read as a float32 are the
# same number, exactly.
def bfloat16(bits):
    return (bits.astype(np.uint32) << 16).view(np.float32)
# @end


def read_header(filename):
    """The JSON header of a safetensors file, and its length in bytes: what the file says it holds."""
    with open(filename, "rb") as f:
        (n,) = struct.unpack("<Q", f.read(8))
        return json.loads(f.read(n)), n
