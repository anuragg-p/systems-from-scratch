"""01.01 A derivative by nudging

The central difference gives the derivatives of known functions to about 1e-9, every partial of
a function of several numbers, and the error that grows on both sides of the best nudge (too big
a nudge measures a chord, too small loses the digits).
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "nudge")
    best = T.value(r.out, r"closest central nudge: h = (\S+)")
    t.check(1e-7 <= best <= 1e-3, f"the best nudge should be near 1e-5, not {best}")
    for name in ("dg/dx", "dg/dy"):
        t.check(T.value(r.out, rf"^{name} at .*difference (\S+)$") < 1e-6, f"{name} far from the hand-worked one")


def inside(S):
    import math
    from engine import nudge
    from experiments.nudge import by_hand, f, g

    assert abs(nudge.derivative(math.sin, 1.0) - math.cos(1.0)) < 1e-9
    assert abs(nudge.derivative(lambda x: x ** 3, 2.0) - 12) < 1e-7
    assert abs(nudge.derivative(math.exp, 0.5, h=1e-4) - math.exp(0.5)) < 1e-8
    grads = nudge.gradient(lambda v: v[0] * v[1] ** 2 + v[2], [1.0, 2.0, 5.0])
    assert all(abs(a - b) < 1e-7 for a, b in zip(grads, [4.0, 4.0, 1.0])), grads
    exact, partials = by_hand(1.5, [1.5, 2.0])
    assert exact == 4.75, exact
    assert all(abs(a - b) < 1e-7 for a, b in zip(nudge.gradient(g, [1.5, 2.0]), partials)), partials
    err = {h: abs(nudge.derivative(f, 1.5, h) - 4.75) for h in (1e-1, 1e-5, 1e-12)}
    assert err[1e-1] > 1e-3 and err[1e-12] > 100 * err[1e-5] and err[1e-5] < 1e-8, err
