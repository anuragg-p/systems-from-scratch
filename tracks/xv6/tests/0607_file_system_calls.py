"""06.07 File system calls

Internal check: open/read/write/close, big files, directories and links
through the system-call interface.
"""


def test(t):
    s = t.track.shell(t)
    for name in ("files", "bigfile", "dirs", "links", "fourfiles"):
        out = t.track.run(s, f"usertests {name}", timeout=60)
        t.check(f"{name}: OK" in out, out)
