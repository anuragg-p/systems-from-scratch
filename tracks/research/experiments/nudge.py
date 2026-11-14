"""How close is a nudge to the derivative, and which nudge is closest?

f(x) = x^3 - 2x has the derivative 3x^2 - 2, which is 4.75 at x = 1.5.
The nudge estimates it for nudges h from 0.1 down to 1e-13, both the
central difference (f(x + h) - f(x - h)) / 2h and the one-sided one
(f(x + h) - f(x)) / h, and prints how far each lands from 4.75. Then it
finds every partial derivative of a function of two numbers and compares
them with the ones worked out by hand.

    python3 -m experiments.nudge
"""

import math

import lab
from engine import nudge

CONFIG = dict(x=1.5, smallest=13)


def f(x):
    return x ** 3 - 2 * x


def g(v):
    x, y = v
    return x * y ** 2 + math.sin(x) / y


# @build 01.01 by_hand
# The derivatives worked out by hand, to hold the nudges to: f'(x) =
# 3x^2 - 2, and g's partials: d/dx (x y^2 + sin(x) / y) = y^2 + cos(x) / y,
# d/dy = 2 x y - sin(x) / y^2.
def by_hand(x, v):
    gx, gy = v
    return 3 * x ** 2 - 2, [gy ** 2 + math.cos(gx) / gy, 2 * gx * gy - math.sin(gx) / gy ** 2]
# @end


def main():
    cfg = lab.config(CONFIG)
    x, v = cfg.x, [cfg.x, 2.0]
    exact, exact_g = by_hand(x, v)
    hs = [10.0 ** -k for k in range(1, cfg.smallest + 1)]
    central = [abs(nudge.derivative(f, x, h) - exact) for h in hs]
    one_sided = [abs((f(x + h) - f(x)) / h - exact) for h in hs]
    print(f"f(x) = x^3 - 2x at x = {x}: the derivative is {exact} exactly")
    print("        h   central error   one-sided error")
    for h, c, o in zip(hs, central, one_sided):
        print(f"  {h:7.0e}   {c:13.3e}   {o:15.3e}")
    best = hs[min(range(len(hs)), key=lambda i: central[i])]
    print(f"closest central nudge: h = {best:.0e}")
    got = nudge.gradient(g, v)
    for name, a, b in zip(("dg/dx", "dg/dy"), got, exact_g):
        print(f"{name} at {tuple(v)}: nudge {a:.9f}  by hand {b:.9f}  difference {abs(a - b):.1e}")
    floor = 1e-17
    path = lab.lines(f"{cfg.out}/{cfg.name}/error.svg",
                     [lab.Line("central", hs, [max(e, floor) for e in central], 0),
                      lab.Line("one-sided", hs, [max(e, floor) for e in one_sided], 1)],
                     xlabel="nudge h", ylabel="error of the estimate", logx=True, logy=True)
    print(f"plot in {path}")


if __name__ == "__main__":
    main()
