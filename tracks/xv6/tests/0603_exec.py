"""06.03 exec and the ELF loader

Internal check: programs load from the disk and get their arguments; a
missing program fails cleanly.
"""


def test(t):
    s = t.track.shell(t)
    out = t.track.run(s, "echo one two three")
    t.check("one two three" in out, out)
    out = t.track.run(s, "nosuchprogram")
    t.check("exec nosuchprogram failed" in out, out)
    out = t.track.run(s, "usertests exectest")
    t.check("exectest: OK" in out, out)
