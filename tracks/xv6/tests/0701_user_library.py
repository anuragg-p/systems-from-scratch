"""07.01 The user library

Internal check: malloc/free and printf work in user programs.
"""


def test(t):
    s = t.track.shell(t)
    out = t.track.run(s, "usertests mallocmany")
    t.check("mallocmany: OK" in out, out)
