"""Makefiles for make (module 07): kinds for data/gen.py and bench/grow.py.

  diamonds  [levels] a chain of N diamonds. d0 needs a1 and b1, which both
            need d1; d1 needs a2 and b2, which both need d2; and so on down
            to dN. Every target is a file its recipe touches. 3N + 1
            targets, 4N edges; but a walk that does not remember where it
            has been goes down both sides of every diamond, so it comes to
            dN by 2^N paths: 2^(N+2) - 3 visits in all.
  wide      [targets] all needs N targets that need nothing: each one
            sleeps a tenth of a second and touches its file. Run one at a
            time they take N/10 seconds; with make -j N, about a tenth.

As a makefile: python3 data/gen.py diamonds 20 -o d20.mk; bin/make -n -f d20.mk
"""


def diamonds(n, rng):
    out = [f"# A chain of {n} diamonds (tools/make/gen.py): d0 is the top, d{n} the bottom.", ""]
    for i in range(1, n + 1):
        out += [f"d{i - 1}: a{i} b{i}", f"\ttouch d{i - 1}",
                f"a{i}: d{i}", f"\ttouch a{i}",
                f"b{i}: d{i}", f"\ttouch b{i}"]
    out += [f"d{n}:", f"\ttouch d{n}"]
    return ("\n".join(out) + "\n").encode("ascii")


def wide(n, rng):
    names = [f"w{i}" for i in range(1, n + 1)]
    out = [f"# {n} targets that need nothing (tools/make/gen.py).", "", "all: " + " ".join(names), ""]
    for name in names:
        out += [f"{name}:", f"\tsleep 0.1; touch {name}"]
    out += ["", ".PHONY: all"]
    return ("\n".join(out) + "\n").encode("ascii")


KINDS = {
    "diamonds": (diamonds, "levels", "a chain of diamonds: one target needed by two paths, level after level"),
    "wide": (wide, "targets", "targets that need nothing, each a tenth of a second's work"),
}
