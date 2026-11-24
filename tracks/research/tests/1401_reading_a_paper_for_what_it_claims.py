"""14.01 Reading a paper for what it claims

data/modular.py: every pair a, b appears exactly once for each operation (b from 1 for division),
each c is right (a = c times b modulo p for division, against Python's own arithmetic for + and -),
the tokens are a, op, b, =, c; split is disjoint, covers every equation, takes round(fraction x n)
to train on, and gives the same split for the same seed and another for another seed. The claims
table has every field, each claim a rule the verdict understands, and verdict applies the rules
(below, above, about within a factor of 3, a lower bound). The memoriser is right on every training
equation and near chance on the rest. The script prints every claim and the baselines.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.py(t, ["-m", "experiments.claims"])
    for key in ("memorise", "late", "loss_rises", "less_data", "decay", "norm_falls"):
        t.check(f". {key} (" in r.out, f"claims should print the claim {key}:\n{r.out[-1500:]}")
    t.check(T.value(r.out, r"A guess: accuracy 1/97 = (\S+);") == round(1 / 97, 4),
            f"chance is 1/97:\n{r.out[-800:]}")
    val = T.value(r.out, r"validation accuracy (\S+) \+-")
    t.check(val < 0.03, f"a memoriser should be near chance on the validation equations: {val}")


def inside(S):
    import math
    import numpy as np
    from data import modular
    from experiments import claims, predictions

    for p in (5, 7, 97):
        for op in ("+", "-", "/"):
            rows = modular.equations(p, op)
            first = 1 if op == "/" else 0
            pairs = [(a, b) for a, b, _ in rows.tolist()]
            assert len(pairs) == len(set(pairs)) == p * (p - first), (p, op, len(pairs))
            assert set(pairs) == {(a, b) for a in range(p) for b in range(first, p)}, (p, op)
            assert rows.dtype == np.int64 and ((rows >= 0) & (rows < p)).all()
            for a, b, c in rows.tolist():
                if op == "+":
                    assert c == (a + b) % p
                elif op == "-":
                    assert c == (a - b) % p
                else:
                    assert (c * b) % p == a, f"{a} / {b} = {c} mod {p}, but {c} x {b} = {c * b % p}"
            toks = modular.tokens(rows, p, op)
            names = modular.names(p)
            assert toks.shape == (len(rows), 5) and toks.dtype == np.int64
            assert (toks[:, [0, 2, 4]] == rows).all() and (toks[:, 3] == p).all()
            assert names[toks[0, 1]] == op and names[toks[0, 3]] == "=" and len(names) == p + len(modular.SYMBOLS)
    assert modular.divide(20, 15, 97) == 66 and (66 * 15) % 97 == 20
    try:
        modular.divide(3, 0, 7)
        raise AssertionError("dividing by 0 should be refused")
    except ZeroDivisionError:
        pass

    everything = {tuple(r) for r in modular.tokens(modular.equations(97, "/"), 97, "/").tolist()}
    for fraction in (0.3, 0.5):
        train, val = modular.split(97, "/", fraction, 0)
        tr, va = {tuple(r) for r in train.tolist()}, {tuple(r) for r in val.tolist()}
        assert len(tr) == len(train) == round(fraction * 9312) and len(va) == len(val), "no equation twice"
        assert not tr & va and tr | va == everything, "disjoint, and every equation in one of the two"
    a, _ = modular.split(97, "/", 0.5, 0)
    b, _ = modular.split(97, "/", 0.5, 0)
    c, _ = modular.split(97, "/", 0.5, 1)
    assert (a == b).all() and not (a == c).all(), "the same seed the same split, another seed another"

    CLAIMS = predictions.CLAIMS
    assert len(CLAIMS) >= 8 and len({c.key for c in CLAIMS}) == len(CLAIMS)
    for c in CLAIMS:
        assert all(isinstance(getattr(c, f), str) and getattr(c, f) for f in
                   ("key", "where", "says", "setting", "measure", "paper")), c
        assert c.rule[0] in ("below", "above", "about") and c.rule[1] > 0, c
        assert any(w in c.where for w in ("figure", "section", "abstract", "appendix")), c

    v = predictions.verdict
    assert v(("below", 1000), 600) == "held" and v(("below", 1000), 1000) == "did not hold"
    assert v(("below", 1000), 1200, more=True) == "did not hold" and v(("below", 1000), 500, more=True) == "not settled"
    assert v(("above", 1.0), 1.5) == "held" and v(("above", 1.0), 0.9) == "did not hold"
    assert v(("above", 1.0), 2.0, more=True) == "held" and v(("above", 1.0), 0.5, more=True) == "not settled"
    assert v(("about", 1000), 400) == "held" and v(("about", 1000), 2900) == "held"
    assert v(("about", 1000), 300) == "did not hold" and v(("about", 1000), 3100) == "did not hold"
    assert v(("about", 1000), 3100, more=True) == "did not hold" and v(("about", 10), 5, more=True) == "not settled"
    assert v(("below", 1.0), None) == "not settled"

    train, val = modular.split(97, "/", 0.5, 2)
    on_train, on_val = claims.memoriser(train, val)
    assert on_train == 1.0 and on_val < 3 / 97, (on_train, on_val)
    counts = np.bincount(train[:, 4])
    assert any(math.isclose(on_val, (val[:, 4] == c).mean()) for c in np.flatnonzero(counts == counts.max())), \
        "an unseen equation gets the commonest training answer"
