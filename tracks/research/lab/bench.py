"""Timing that means something (11.01).

A time taken once is one draw from a spread, as a loss from one seed is
(00.03). The first call of anything is slow (memory to find, an optimiser
to set up, caches empty), so it is not timed; then the same work is timed
several times over. Other programs take the processor from it, now and
then, by different amounts: they can make a timing longer, never shorter,
so the smallest of several is the one closest to what the work itself
costs, and the median says what a run on this machine, as it is, takes.
The machine's load average is printed beside every timing: a number
taken at a load of 10 is not one taken at a load of 1.

    load_average()                       the processes running or waiting for a core, over the last minute
    timings(work, clock, ...)            seconds a call of work, several times over, after a warm-up
    spread_ms(seconds, load)             one line: the smallest, the median and the largest, in ms
    time_to(rows, times, target)         the step and the seconds at which a run's held-out bits reach target

lab knows nothing about tensors: clock is a function that returns the
time once the device is done, lab.clock with torch and the device given
(06.02).
"""

import os
import statistics


# @build 11.01 load_average
# How busy the machine is: the number of processes running or waiting for
# a core, averaged over the last minute (os.getloadavg's first number).
# Above the number of cores, work queues for them.
def load_average():
    return os.getloadavg()[0]
# @end


# @build 11.01 timings
# work() called `warmup` times untimed, then timed `repeats` times, each
# timing `number` calls in a row (a call shorter than the clock can see
# is timed many at a time), by clock() before and after. Returns the
# seconds a call, one number for each repeat, in the order taken.
def timings(work, clock, repeats=5, warmup=1, number=1):
    for _ in range(warmup):
        work()
    out = []
    for _ in range(repeats):
        start = clock()
        for _ in range(number):
            work()
        out.append((clock() - start) / number)
    return out
# @end


# @build 11.01 spread_ms
# Timings (seconds) in one line, in milliseconds to `digits` significant
# digits: the smallest first, then the median and the largest, how many,
# and the load average (when given) they were taken at.
def spread_ms(seconds, load=None, digits=3):
    g = f".{digits}g"
    ms = [1000 * s for s in seconds]
    text = f"{min(ms):{g}} ms (median {statistics.median(ms):{g}}, largest {max(ms):{g}}, {len(ms)} repeat{'s' * (len(ms) > 1)}"
    return text + (f", load {load:.1f})" if load is not None else ")")
# @end


# @build 11.01 time_to
# Where a run's held-out bits first reach target: rows are its log
# (dicts with "step" and "held_bits"), times the seconds of training at
# each row. Between the last row above the target and the first at or
# below it, the crossing is put on the straight line from one to the
# other. Returns (steps, seconds): the steps taken by then (a row's step
# counts from 0, so step + 1 have been taken) and the seconds, or (None,
# None) when no row reaches the target.
def time_to(rows, times, target):
    before = None
    for row, seconds in zip(rows, times):
        if row["held_bits"] <= target:
            if before is None:
                return row["step"] + 1, seconds
            (b, s0, t0), b1 = before, row["held_bits"]
            f = (b - target) / (b - b1)
            return s0 + 1 + f * (row["step"] - s0), t0 + f * (seconds - t0)
        before = (row["held_bits"], row["step"], seconds)
    return None, None
# @end
