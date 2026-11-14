"""04.06 Five bugs that do not crash: a debugging checklist

Each check of lab/checks.py passes what it should and fails what it should; run on the correct
training script and five broken copies of it, the checklist passes the correct one and catches
each bug with the check meant for it, and nothing else, on either engine.
"""

BUGS = {"none": None, "no zero_grad": "fresh gradients", "softmax twice": "one batch",
        "labels shuffled": "beats chance", "pixels 0-255": "starting loss", "eval in train mode": "same answers"}
CHECKS = ["starting loss", "one batch", "fresh gradients", "beats chance", "same answers"]


def table(out):
    rows = {}
    for line in out.splitlines():
        for bug in BUGS:
            if line.startswith(bug + " ") and len(line.split()) >= 5:
                cells = line[len(bug):].split()
                rows[bug] = [CHECKS[i] for i, c in enumerate(c for c in cells if c in ("ok", "FAILS")) if c == "FAILS"]
    return rows


def test(t):
    T = t.track
    T.need(t, "mnist")
    T.inside(t, __file__)
    for run in (T.experiment(t, "bugs", "seeds=1"), T.on_torch(t, "bugs", "seeds=1")):
        rows = table(run.out)
        t.check(set(rows) == set(BUGS), f"a row for every bug:\n{run.out}")
        for bug, check in BUGS.items():
            want = [check] if check else []
            t.check(rows[bug] == want, f"{bug}: should fail {want or 'nothing'}, failed {rows[bug]}:\n{run.out}")


def inside(S):
    import numpy as np
    from lab import checks

    assert checks.starting_loss(2.31, 10)[0] and not checks.starting_loss(12.8, 10)[0]
    assert checks.learns_one_batch([2.3, 0.01])[0] and not checks.learns_one_batch([2.3, 1.46])[0]
    g = [np.ones((2, 2)), np.arange(3.0)]
    ok, text = checks.gradients_fresh(g, [a.copy() for a in g])
    assert ok and "1.00 times" in text, text
    ok, text = checks.gradients_fresh(g, [2 * a for a in g])
    assert not ok and "2.00 times" in text, text
    assert checks.beats_chance(0.9, 10)[0] and not checks.beats_chance(0.11, 10)[0]
    assert checks.same_answers([1, 2, 3], [1, 2, 3])[0]
    ok, text = checks.same_answers([1, 2, 3], [1, 0, 3])
    assert not ok and "1 of 3" in text, text
