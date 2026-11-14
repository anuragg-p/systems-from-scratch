"""06.06 Pipes

Internal check: bytes flow through a pipe in order, and the shell's
pipelines work.
"""


def test(t):
    s = t.track.shell(t)
    out = t.track.run(s, "usertests pipe1")
    t.check("pipe1: OK" in out, out)
    import os
    with open(os.path.join(t.root, "README.md")) as f:
        want = sum(1 for line in f if "cat" in line)
    out = t.track.run(s, "cat README | grep cat | wc")
    t.check(out.strip().startswith(f"{want} "), f"pipeline printed {out!r}, expected {want} lines")
