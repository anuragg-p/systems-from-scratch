"""00.03 Timing: warm up, repeat, count the bytes

bench, on a clock the test scripts: one call first that the clock never sees (the warm-up), then
timed calls until there are min_runs of them and they add up to min_time, or there are max_runs;
it reads the clock exactly twice a run and never after it stops. The result's min, median (the
middle run, or the mean of the two middle ones) and total are exact. A field of 0 or less takes
its default (0.5 s, 5 runs, 1000 runs). On the real clock (bench_now, CLOCK_MONOTONIC_RAW) the
same rules hold. wb time [-n N] prints "add: n = N, R runs, min M ms, median D ms, G GB/s", min
no more than median, G counted as 12 bytes an element; a run too short for the clock says so
instead of dividing by 0.
"""

import re


def script(min_time, min_runs, max_runs, durations, start=0.0, gap=1.0):
    """A clock script for runs of these durations: a start reading and an end reading a run."""
    readings, now = [], start
    for d in durations:
        readings += [now, now + d]
        now += d + gap
    return (f"script {min_time!r} {min_runs} {max_runs} {len(readings)} " +
            " ".join(repr(r) for r in readings) + "\n")


def parse(line):
    w = line.split()
    t_ = {w[i]: w[i + 1] for i in range(0, len(w), 2)}
    return (int(t_["runs"]), float.fromhex(t_["min"]), float.fromhex(t_["median"]), float.fromhex(t_["total"]),
            int(t_["calls"]), int(t_["clocks"]), int(t_["first"]))


def test(t):
    tr = t.track
    # (what, case, runs, min, median, total)
    cases = [
        ("stops at min_runs once min_time is reached", script(0.5, 3, 100, [1, 1, 1]), 3, 1, 1, 3),
        ("goes on past min_runs until min_time", script(1.0, 2, 100, [0.25] * 4), 4, 0.25, 0.25, 1.0),
        ("stops at max_runs whatever the time", script(100, 2, 5, [1] * 5), 5, 1, 1, 5),
        ("max_runs below min_runs wins", script(100, 10, 3, [1] * 3), 3, 1, 1, 3),
        ("min and median, an odd count", script(2 ** -30, 5, 5, [5, 1, 4, 2, 3]), 5, 1, 3, 15),
        ("median of an even count: the mean of the middle two", script(2 ** -30, 4, 4, [4, 1, 3, 2]),
         4, 1, 2.5, 10),
        ("the fastest run, wherever it comes", script(2 ** -30, 6, 6, [0.5, 0.75, 0.5, 0.125, 2, 1]),
         6, 0.125, 0.625, 4.875),
        ("defaults: 5 runs when they pass 0.5 s", script(0, 0, 0, [0.25] * 5), 5, 0.25, 0.25, 1.25),
        ("defaults: past 5 runs until 0.5 s", script(0, 0, 0, [0.0625] * 8), 8, 0.0625, 0.0625, 0.5),
        ("defaults: at most 1000 runs", script(0, 0, 0, [2 ** -20] * 1000), 1000, 2 ** -20, 2 ** -20,
         1000 * 2 ** -20),
        ("below 0 is the default too", script(-1, -3, -7, [0.25] * 5), 5, 0.25, 0.25, 1.25),
        ("a clock that does not start at 0", script(2 ** -30, 3, 3, [1, 2, 3], start=1e6), 3, 1, 2, 6),
    ]
    lines = tr.driver(t, "bench_driver", "".join(c for _, c, *_ in cases))
    t.check(len(lines) == len(cases), f"bench_driver printed {len(lines)} lines for {len(cases)} cases")
    for (what, _, runs, mn, med, total), line in zip(cases, lines):
        got = parse(line)
        want = (runs, mn, med, total, runs + 1, 2 * runs, 1)
        t.check(got == want, f"{what}:\n  got  runs {got[0]} min {got[1]} median {got[2]} total {got[3]} "
                             f"calls {got[4]} clocks {got[5]} first {got[6]}\n"
                             f"  want runs {want[0]} min {want[1]} median {want[2]} total {want[3]} "
                             f"calls {want[4]} clocks {want[5]} first {want[6]}")

    # The real clock: the same rules, and times that make sense.
    for min_time, min_runs, max_runs in ((0.02, 3, 100000), (100, 2, 7), (0.001, 50, 60)):
        runs, mn, med, total, calls, clocks, first = parse(
            tr.driver(t, "bench_driver", f"real {min_time} {min_runs} {max_runs}\n")[0])
        t.check(min_runs <= runs <= max_runs and (total >= min_time or runs == max_runs),
                f"on the real clock with {min_time} {min_runs} {max_runs}: {runs} runs, total {total}")
        t.check(0 <= mn <= med <= total and calls == runs + 1 and clocks == 0 and first == -1,
                f"on the real clock: min {mn}, median {med}, total {total}, calls {calls}")

    # bench_now: never back, and fine enough to time a run shorter than a microsecond (macOS's
    # CLOCK_MONOTONIC moves in whole microseconds: a 4096-element add read as 0 or 1 us).
    w = tr.driver(t, "bench_driver", "steps 20000\n")[0].split()
    step, backwards = float.fromhex(w[1]), int(w[3])
    t.check(backwards == 0, f"bench_now went back {backwards} times in 20000 pairs of readings")
    t.check(0 < step < 2.5e-7, f"bench_now's smallest step is {step * 1e9:.0f} ns: too coarse to time a short run")

    # wb time.
    line = re.compile(r"^add: n = (\d+), (\d+) runs, min ([0-9.e+-]+) ms, median ([0-9.e+-]+) ms, "
                      r"(?:([0-9.]+) GB/s|too fast for the clock: try a larger -n)\n$")
    for n in (4096, 1000003):
        st, out, err = tr.prog(t, "wb", ["time", "-n", str(n)])
        m = line.match(out)
        t.check(st == 0 and err == "" and m, f"wb time -n {n}: {st} {out!r} {err!r}")
        t.check(int(m.group(1)) == n and int(m.group(2)) >= 5, f"wb time -n {n}: {out!r}")
        mn, med = float(m.group(3)), float(m.group(4))
        t.check(0 < mn <= med, f"wb time -n {n}: min {mn} ms and median {med} ms")
        t.check(m.group(5) is not None and float(m.group(5)) > 0, f"wb time -n {n}: no GB/s: {out!r}")
        gbs = 12 * n / (mn / 1e3) / 1e9
        t.check(abs(float(m.group(5)) - gbs) <= 0.01 * gbs + 0.1,
                f"wb time -n {n}: {m.group(5)} GB/s, but 12 bytes x {n} in {mn} ms is {gbs:.1f}")
    st, out, err = tr.prog(t, "wb", ["time", "-n", "1"])
    t.check(st == 0 and line.match(out) and "inf" not in out and "nan" not in out, f"wb time -n 1: {out!r}")
    st, out, err = tr.prog(t, "wb", ["time", "-n", "0"])
    t.check(st == 2 and "-n wants a whole number from 1 to 268435456" in err, f"wb time -n 0: {st} {err!r}")
