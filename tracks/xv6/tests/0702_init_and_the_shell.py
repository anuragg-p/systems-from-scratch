"""07.02 init and the shell

Internal check: redirection, pipes, command lists and cd.
"""


def test(t):
    s = t.track.shell(t)
    t.track.run(s, "echo hi there > out")
    out = t.track.run(s, "cat < out")
    t.check("hi there" in out, out)
    out = t.track.run(s, "echo a; echo b")
    t.check("a" in out and "b" in out, out)
    t.track.run(s, "mkdir sub")
    t.track.run(s, "cd sub")
    out = t.track.run(s, "../ls ..")
    t.check("README" in out, out)
