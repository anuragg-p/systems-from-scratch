"""03.02 Timer interrupts

Each hart asks for a timer interrupt every 1,000,000 cycles of the
10 MHz clock. Hart 0 counts them in `ticks`; five of them take about
half a second of real time.
"""


def test(t):
    s = t.track.boot(t)
    ms = int(s.expect(r"\[03\.02\] waited for 5 timer ticks: (\d+) ms").group(1))
    t.check(350 <= ms <= 1500, f"5 ticks should take ~500 ms, took {ms} ms")
    t.track.selftest(s, "03.02")
