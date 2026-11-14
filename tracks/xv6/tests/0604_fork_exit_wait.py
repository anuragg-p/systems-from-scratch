"""06.04 fork, exit and wait

Internal check: children copy their parent, exit statuses reach wait,
the process table fills up and empties, and kill works.
"""


def test(t):
    s = t.track.shell(t)
    for name in ("forkfull", "exitwait", "forkcopy", "killstatus"):
        out = t.track.run(s, f"usertests {name}", timeout=60)
        t.check(f"{name}: OK" in out, out)
