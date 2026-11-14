"""07.03 The utilities

Internal check: cat, ls, wc, grep, mkdir, ln and rm behave, and the
whole usertests suite passes. On the track's own code, xv6's own
usertests (tests/upstream) pass on the finished kernel too.
"""

import importlib.util
import os


def test(t):
    s = t.track.shell(t)
    out = t.track.run(s, "wc README")
    t.check(out.strip().endswith("README"), out)
    out = t.track.run(s, "ls")
    for name in ("README", "cat", "sh", "usertests"):
        t.check(name in out, f"ls is missing {name}: {out}")
    out = t.track.run(s, "usertests", timeout=180)
    t.check("ALL TESTS PASSED" in out, out[-1500:])
    s.close()
    upstream().check(t)


def upstream():
    """tests/upstream/run.py, which builds and boots its own kernel and disk."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upstream", "run.py")
    spec = importlib.util.spec_from_file_location("xv6_upstream_usertests", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
