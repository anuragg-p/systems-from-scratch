"""05.06 Directories and path names

Paths with ., .., repeated slashes and over-long names all resolve to
the right inode; missing names and non-directories do not.
"""


def test(t):
    s = t.track.boot(t)
    t.track.selftest(s, "05.06", timeout=20)
