"""09.03 Keyboard and mouse

events reads the input device and prints every event. With nothing
happening it sleeps in read. A key on the virtio keyboard arrives as
EV_KEY down and up with the key's code, each group ended by EV_SYN; the
virtio tablet's position arrives as EV_ABS x and y in screen pixels,
corners included, then EV_SYN; the left button as EV_KEY 272. Thirty keys
one after another all arrive, which takes every buffer going back to its
device many times over. Esc ends the program, and the shell carries on.
"""

import time


def test(t):
    tr = t.track
    s = tr.shell(t)
    q = s.qmp
    s.sendline("events")
    s.expect(r"events: reading /input", timeout=10)

    # Nothing has happened: it sleeps in read.
    time.sleep(0.5)
    s.send("\x10")                      # Control-P: the process list
    s.expect(r"\d+ sleep +events", timeout=5)

    def saw(line):
        s.expect(line + r"\r?\n", timeout=5)

    q.key("a")
    saw(r"EV_KEY 30 1  a down")
    saw(r"EV_SYN 0 0")
    saw(r"EV_KEY 30 0  a up")
    saw(r"EV_SYN 0 0")

    for x, y in ((100, 200), (0, 0), (639, 479), (320, 240)):
        q.move(x, y)
        saw(rf"EV_ABS 0 {x}  x = {x}")
        saw(rf"EV_ABS 1 {y}  y = {y}")
        saw(r"EV_SYN 0 0")

    q.button(True)
    saw(r"EV_KEY 272 1  left button down")
    saw(r"EV_SYN 0 0")
    q.button(False)
    saw(r"EV_KEY 272 0  left button up")

    # Thirty keys, each down and up: 120 events through 8 buffers.
    keys = "qwertyuiopasdfghjklzxcvbnm1234"
    for k in keys:
        q.key(k)
    for k in keys:
        saw(rf"EV_KEY \d+ 1  {k} down")
        saw(r"EV_SYN 0 0")
        saw(rf"EV_KEY \d+ 0  {k} up")
        saw(r"EV_SYN 0 0")

    q.key("esc")
    saw(r"EV_KEY 1 1  esc down")
    s.expect(r"\$ ", timeout=10)
    out = tr.run(s, "echo back at the shell")
    t.check("back at the shell" in out, f"echo printed {out!r}")
