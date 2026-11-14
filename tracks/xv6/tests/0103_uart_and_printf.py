"""01.03 The UART and printf

The kernel formats integers, pointers, strings and characters itself and
pushes each byte through the UART's transmit register.
"""


def test(t):
    s = t.track.boot(t)
    line = s.expect(r"\[01\.03\] printf: (.*)\r?\n").group(1).rstrip("\r")
    want = "42 -7 4000000000 2a deadbeefcafe 0x0000000080000000 hello (null) z %"
    t.check(line == want, f"printf formatted\n  {line!r}\nexpected\n  {want!r}")
    t.track.selftest(s, "01.03")
