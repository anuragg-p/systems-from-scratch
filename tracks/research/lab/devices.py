"""Where a PyTorch run computes: the CPU, or a GPU when there is one (06.02 on).

Every PyTorch-era experiment has a `device` setting. Its default is "cpu",
so that the numbers and times a lesson prints are CPU numbers, the ones
any laptop can check; device=auto uses an NVIDIA GPU (cuda) when PyTorch
sees one, else an Apple GPU (mps), else the CPU. The same seed gives the
same numbers on the same machine and device, not across devices: a GPU
adds up in another order, so its last digits differ.

lab knows nothing about tensors, so it imports no engine: the script
passes torch in.
"""

import time


# @build 06.02 device
# The torch.device a run's `device` setting names: "cpu", "cuda" or "mps"
# as they are, and "auto" as cuda when torch.cuda.is_available(), else mps
# when torch.backends.mps.is_available(), else cpu.
def device(torch, name="cpu"):
    if name == "auto":
        if torch.cuda.is_available():
            name = "cuda"
        elif torch.backends.mps.is_available():
            name = "mps"
        else:
            name = "cpu"
    return torch.device(name)
# @end


# @build 06.02 clock
# The time in seconds (time.perf_counter) once the device has done all it
# was asked. A GPU works through its queue on its own while Python goes on
# to the next line, so a clock read without waiting would time the asking,
# not the work: wait first (torch.cuda.synchronize, torch.mps.synchronize).
# On the CPU every operation is done when its line returns.
def clock(torch, dev):
    if dev.type == "cuda":
        torch.cuda.synchronize()
    elif dev.type == "mps":
        torch.mps.synchronize()
    return time.perf_counter()
# @end
