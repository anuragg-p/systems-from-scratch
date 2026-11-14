"""03.03 The PLIC and console input

Typed characters raise UART interrupt 10 through the PLIC; the console
echoes each one and collects the line. Control-U erases the line,
echoing a backspace-space-backspace for each character.
"""


def test(t):
    s = t.track.boot(t)
    s.wait_quiet(0.7)    # boot finished; nothing else is printing
    s.skip()
    s.send("abc")
    s.expect(r"abc", timeout=5)
    s.send("\x15")       # Control-U: kill the line
    s.expect(r"(\x08 \x08){3}", timeout=5)
