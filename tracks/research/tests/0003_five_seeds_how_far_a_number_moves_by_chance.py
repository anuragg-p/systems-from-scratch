"""00.03 Five seeds: how far a number moves by chance

The mean and sample standard deviation agree with numpy's, Welch's t with its formula, and a
result prints as mean +- sd with its range; the plot draws round-numbered ticks and one line
per run, broken where a value is not finite; the curve experiment runs five seeds and prints
their spread, which is what the summaries say.
"""

import re
import xml.etree.ElementTree as ET


def test(t):
    T = t.track
    T.inside(t, __file__)
    r = T.experiment(t, "curve")
    losses = [s["test_loss"] for s in T.summaries(r)]
    t.check(len(losses) == 5, f"five seeds: {losses}")
    m = re.search(r"^test loss (\S+) \+- (\S+) \(min (\S+), max (\S+), 5 seeds\)$", r.out, re.M)
    t.check(m is not None, f"no spread line:\n{r.out}")
    mean = sum(losses) / 5
    t.check(abs(float(m.group(1)) - mean) < 1e-3 * mean and float(m.group(3)) == float(f"{min(losses):.3g}"),
            f"the printed spread is not the summaries': {m.group(0)} against {losses}")
    svg = ET.parse(f"{r.runs}/train_loss.svg").getroot()
    t.check(len([e for e in svg.iter() if e.tag.endswith("polyline")]) == 5, "one line per seed")


def inside(S):
    import math
    import os
    import tempfile
    import numpy as np
    import lab
    from lab.plot import ticks

    xs = [0.31, 0.29, 0.35, 0.33, 0.30]
    assert abs(lab.mean(xs) - np.mean(xs)) < 1e-15 and abs(lab.sd(xs) - np.std(xs, ddof=1)) < 1e-15
    assert math.isnan(lab.sd([1.0]))
    assert lab.spread(xs) == "0.316 +- 0.0241 (min 0.29, max 0.35, 5 seeds)", lab.spread(xs)
    a, b = [1.0, 1.2, 0.9, 1.1], [2.0, 2.3, 1.8]
    want = (np.mean(a) - np.mean(b)) / math.sqrt(np.var(a, ddof=1) / 4 + np.var(b, ddof=1) / 3)
    assert abs(lab.welch_t(a, b) - want) < 1e-12, (lab.welch_t(a, b), want)
    assert np.allclose(ticks(0, 1), [0, 0.2, 0.4, 0.6, 0.8, 1.0]), ticks(0, 1)
    assert np.allclose(ticks(0.013, 0.97), [0.2, 0.4, 0.6, 0.8]), ticks(0.013, 0.97)
    assert np.allclose(ticks(-3, 47), [0, 10, 20, 30, 40]), ticks(-3, 47)
    assert np.allclose(ticks(0.001, 10, log=True), [0.001, 0.01, 0.1, 1, 10]), ticks(0.001, 10, log=True)
    path = os.path.join(tempfile.mkdtemp(), "p", "plot.svg")
    lab.lines(path, [lab.Line("a", [0, 1, 2, 3], [1.0, 0.5, float("nan"), 0.2]), lab.Line("b", [0, 3], [2, 1], 1)],
              title="t", xlabel="step", ylabel="loss", logy=True)
    root = ET.parse(path).getroot()
    assert root.get("viewBox") == "0 0 640 360", root.attrib
    lines = [e for e in root.iter() if e.tag.endswith("polyline")]
    dots = [e for e in root.iter() if e.tag.endswith("circle")]
    assert len(lines) == 2 and len(dots) == 1, "a's line breaks at the nan: two points, then one alone"
    text = open(path, encoding="ascii").read()
    assert ">a<" in text and ">b<" in text and "currentColor" in text
