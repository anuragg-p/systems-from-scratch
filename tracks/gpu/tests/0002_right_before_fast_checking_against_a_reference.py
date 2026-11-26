"""00.02 Right before fast: checking against a reference

check_close counts the elements outside atol + rtol * |want| (numpy.isclose's rule): an element
off by less than or exactly its allowance is good, one off by more is bad; a NaN on either side
is bad; an infinity is good only against the same infinity; n = 0 reads nothing. The worst
element is the one furthest past its limit (err / allowed; a NaN beats everything; at the same
distance the larger error; a tie keeps the first), so among good elements the one closest to
it. check_report prints one line: "NAME: ok, worst error E at [I] of N (allowed A)", "NAME: ok,
no elements to compare", or "NAME: FAIL, B of N wrong; worst at [I]: got G, want W (error E,
allowed A)", and returns 1 only for a failure. wb check holds add to add_ref with nothing
allowed and prints that line; an add with a broken tail (a patched copy) fails it, naming an
index in the tail, and so does one that never writes its tail.
"""

import math

INF, NAN = math.inf, math.nan
# (what, rtol, atol, got, want, (bad, worst, err, allowed)); err and allowed None for NaN, as
# floats otherwise. Every value here is exact in a float, so each boundary is exact too.
CASES = [
    ("equal arrays", 0, 0, [0.5, -1, 3], [0.5, -1, 3], (0, 0, 0, 0)),
    ("-0 and +0 are equal", 0, 0, [-0.0], [0.0], (0, 0, 0, 0)),
    ("off by less than allowed", 0.125, 0.25, [1, 2.25, 4], [1, 2, 4], (0, 1, 0.25, 0.5)),
    ("off by exactly what is allowed", 0.125, 0.25, [1, 2.5, 4], [1, 2, 4], (0, 1, 0.5, 0.5)),
    ("off by more than allowed", 0.125, 0.25, [1, 2.5 + 2 ** -22, 4], [1, 2, 4], (1, 1, 0.5 + 2 ** -22, 0.5)),
    ("atol alone, near zero", 0, 2 ** -10, [2 ** -11, -2 ** -9], [0, 0], (1, 1, 2 ** -9, 2 ** -10)),
    ("rtol alone, nothing allowed at zero", 0.5, 0, [2 ** -40, 3], [0, 2], (1, 0, 2 ** -40, 0)),
    ("NaN in got", 1e-4, 1e-3, [1, NAN, 4], [1, 2, 4], (1, 1, None, 1e-3 + 1e-4 * 2)),
    ("NaN in want", 1e-4, 1e-3, [1, 2, 4], [1, NAN, 4], (1, 1, None, 0)),
    ("NaN in both", 1e-4, 1e-3, [NAN], [NAN], (1, 0, None, 0)),
    ("+inf against +inf", 1e-4, 1e-3, [INF, 1], [INF, 1], (0, 0, 0, 0)),
    ("-inf against -inf, nothing allowed", 0, 0, [-INF], [-INF], (0, 0, 0, 0)),
    ("+inf against -inf", 1e-4, 1e-3, [INF], [-INF], (1, 0, INF, 0)),
    ("+inf against a number", 1e-4, 1e-3, [1, INF], [1, 2], (1, 1, INF, 1e-3 + 1e-4 * 2)),
    ("a number against +inf", 1e-4, 1e-3, [1, 2], [1, INF], (1, 1, INF, 0)),
    ("the largest float against +inf", 1, 1, [3.4028234663852886e38], [INF], (1, 0, INF, 0)),
    ("n = 0", 1e-4, 1e-3, [], [], (0, 0, 0, 0)),
    ("several bad: the furthest", 0, 0.25, [1.5, 1, 3, 1, 2], [1, 1, 1, 1, 1], (3, 2, 2, 0.25)),
    ("several bad: a NaN beats them", 0, 0.25, [1.5, 1, 3, NAN, 2], [1] * 5, (4, 3, None, 0.25)),
    ("several bad: a NaN beats an infinity", 0, 0.25, [INF, NAN], [1, 1], (2, 1, None, 0.25)),
    ("several bad: a tie keeps the first", 0, 0.25, [3, 1, 3], [1, 1, 1], (2, 0, 2, 0.25)),
    ("further past the limit, not the larger error", 0.01, 0.01, [100.5, 1.5], [100, 1],
     (1, 1, 0.5, 0.01 + 0.01 * 1)),
    ("nothing allowed: any error is furthest", 0, 0, [1, 2.5, 4, 8.25], [1, 2, 4, 8], (2, 1, 0.5, 0)),
    ("all good: the one closest to its limit", 0, 0.5, [1.125, 1.25, 1], [1, 1, 1], (0, 1, 0.25, 0.5)),
    ("all good: at the same distance, the larger error", 0.5, 0, [1.25, 2.5, 1], [1, 2, 1],
     (0, 1, 0.5, 1.0)),
]


def word(x):
    return "nan" if math.isnan(x) else ("inf" if x == INF else "-inf" if x == -INF else repr(float(x)))


def report(name, n, bad, worst, got, want, err, allowed):
    """check_report's line, as C's printf writes it."""
    if n == 0:
        return f"{name}: ok, no elements to compare"
    if bad == 0:
        return f"{name}: ok, worst error {'%.3g' % err} at [{worst}] of {n} (allowed {'%.3g' % allowed})"
    return (f"{name}: FAIL, {bad} of {n} wrong; worst at [{worst}]: got {'%.9g' % got}, want {'%.9g' % want} "
            f"(error {'%.3g' % err}, allowed {'%.3g' % allowed})")


BROKEN_TAIL = """#include "add.h"

void add_ref(const float *a, const float *b, float *out, size_t n)
{
    for (size_t i = 0; i < n; i++)
        out[i] = a[i] + b[i];
}

void add(const float *a, const float *b, float *out, size_t n)
{
    size_t i = 0;
    for (; i + 4 <= n; i += 4) {
        out[i] = a[i] + b[i];
        out[i + 1] = a[i + 1] + b[i + 1];
        out[i + 2] = a[i + 2] + b[i + 2];
        out[i + 3] = a[i + 3] + b[i + 3];
    }
    for (; i < n; i++)
        out[i] = a[i] - b[i];
}
"""
NO_TAIL = BROKEN_TAIL.replace("    for (; i < n; i++)\n        out[i] = a[i] - b[i];\n", "")
WRONG_LANE = BROKEN_TAIL.replace("out[i + 3] = a[i + 3] + b[i + 3]", "out[i + 3] = a[i + 3] + b[i + 2]") \
                        .replace("out[i] = a[i] - b[i]", "out[i] = a[i] + b[i]")


def test(t):
    tr = t.track
    text = ""
    for what, rtol, atol, got, want, _ in CASES:
        text += f"close {rtol!r} {atol!r} {len(got)} " + " ".join(word(x) for x in got + want) + "\n"
    lines = tr.driver(t, "check_driver", text)
    t.check(len(lines) == len(CASES), f"check_driver printed {len(lines)} lines for {len(CASES)} cases")
    for (what, rtol, atol, got, want, (bad, worst, err, allowed)), line in zip(CASES, lines):
        w = line.split()
        n_, bad_, worst_ = int(w[0]), int(w[1]), int(w[2])
        got_, want_, err_, allowed_ = tr.floats(w[3:7])
        t.check((n_, bad_, worst_) == (len(got), bad, worst),
                f"{what}: n {n_}, bad {bad_}, worst [{worst_}]; want n {len(got)}, bad {bad}, worst [{worst}]")
        if err is None:
            t.check(math.isnan(err_), f"{what}: the worst error is {err_}, not NaN")
        else:
            t.check(err_ == err, f"{what}: the worst error is {err_!r}, not {err!r}")
        t.check(allowed_ == allowed or abs(allowed_ - allowed) <= 1e-15,
                f"{what}: allowed {allowed_!r} for the worst element, not {allowed!r}")
        if got:
            t.check((got_ == tr.f32(got[worst]) or math.isnan(got_) and math.isnan(got[worst])) and
                    (want_ == tr.f32(want[worst]) or math.isnan(want_) and math.isnan(want[worst])),
                    f"{what}: the worst element is got {got_}, want {want_}; not {got[worst]}, {want[worst]}")

    # check_report: the three kinds of line, and the status.
    for name, rtol, atol, got, want in (("x", 0, 0.25, [1.5, 1, 3], [1, 1, 1]),
                                       ("good", 1e-4, 1e-3, [1, 2.0009765625], [1, 2]),
                                       ("zeros", 0, 0, [0.5], [0.5]),
                                       ("none", 0, 0, [], []),
                                       ("nan", 0, 0, [1, NAN], [1, 2])):
        out = tr.driver(t, "check_driver", f"report {name} {rtol!r} {atol!r} {len(got)} " +
                        " ".join(word(x) for x in got + want) + "\n")
        close = tr.driver(t, "check_driver", f"close {rtol!r} {atol!r} {len(got)} " +
                          " ".join(word(x) for x in got + want) + "\n")[0].split()
        n, bad, worst = int(close[0]), int(close[1]), int(close[2])
        g, w_, e, a = tr.floats(close[3:7])
        want_line = report(name, n, bad, worst, g, w_, e, a)
        t.check(out == [want_line, f"status {1 if bad else 0}"], f"check_report for {name}: {out}, not "
                                                                    f"{[want_line, f'status {1 if bad else 0}']}")
    t.check(tr.driver(t, "check_driver", "report x 0 0.25 3 1.5 1 3 1 1 1\n")[0] ==
            "x: FAIL, 2 of 3 wrong; worst at [2]: got 3, want 1 (error 2, allowed 0.25)", "the FAIL line, by hand")

    # wb check: add against add_ref, nothing allowed.
    for argv, n in (([], 1003), (["-n", "1"], 1), (["-n", "4"], 4), (["-n", "67", "-s", "5"], 67),
                    (["-n", "1000003", "-s", "4294967295"], 1000003)):
        st, out, err = tr.prog(t, "wb", ["check"] + argv)
        t.check((st, out, err) == (0, f"add: ok, worst error 0 at [0] of {n} (allowed 0)\n", ""),
                f"wb check {' '.join(argv)}: {st} {out!r} {err!r}")

    # An add whose tail is wrong fails wb check, at an index in the tail; one that never writes its
    # tail fails it with a NaN; one wrong in a lane of the unrolled loop fails at that lane.
    wb = tr.build_with(t, "wb", {"add.c": BROKEN_TAIL})
    st, out, err = tr.prog(t, wb, ["check"])
    t.check(st == 1 and out.startswith("add: FAIL, 3 of 1003 wrong; worst at [100") and
            int(out.split("[")[1].split("]")[0]) in (1000, 1001, 1002), f"a broken tail: {st} {out!r}")
    st, out, err = tr.prog(t, wb, ["check", "-n", "1000"])
    t.check(st == 0 and out.startswith("add: ok"), f"a broken tail, but n a multiple of 4: {st} {out!r}")
    st, out, err = tr.prog(t, wb, ["check", "-n", "6", "-s", "3"])
    t.check(st == 1 and out.startswith("add: FAIL, 2 of 6 wrong; worst at [") and
            int(out.split("[")[1].split("]")[0]) in (4, 5), f"a broken tail at n = 6: {st} {out!r}")
    wb = tr.build_with(t, "wb", {"add.c": NO_TAIL})
    st, out, err = tr.prog(t, wb, ["check"])
    t.check(st == 1 and out.startswith("add: FAIL, 3 of 1003 wrong; worst at [1000]: got nan, want "),
            f"a tail never written: {st} {out!r}")
    wb = tr.build_with(t, "wb", {"add.c": WRONG_LANE})
    st, out, err = tr.prog(t, wb, ["check", "-n", "8"])
    t.check(st == 1 and out.startswith("add: FAIL, 2 of 8 wrong; worst at [") and
            int(out.split("[")[1].split("]")[0]) in (3, 7), f"a wrong lane: {st} {out!r}")
