"""The Session class every track's fixtures are built on."""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harness.core import Fail  # noqa: E402
from harness.session import Session  # noqa: E402


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.sessions = []

    def tearDown(self):
        for s in self.sessions:
            s.close()

    def spawn(self, script, **kw):
        s = Session(["sh", "-c", script], **kw)
        self.sessions.append(s)
        return s

    def test_expect_send_and_consume(self):
        s = self.spawn("echo one; echo two; read x; echo got $x; sleep 30")
        s.expect(r"one")
        s.expect(r"two")
        s.sendline("three")
        s.expect(r"got three")
        t0 = time.monotonic()
        with self.assertRaises(Fail):
            s.expect(r"one", timeout=0.5)   # already consumed
        self.assertLess(time.monotonic() - t0, 2)

    def test_fail_on_is_fast(self):
        s = self.spawn("echo 'panic: on purpose'; sleep 30", fail_on=[r"panic: "])
        t0 = time.monotonic()
        with self.assertRaises(Fail) as e:
            s.expect(r"never printed", timeout=20)
        self.assertIn("panic", str(e.exception))
        self.assertLess(time.monotonic() - t0, 2)

    def test_expect_line_waits_for_the_whole_line(self):
        s = self.spawn("printf 'n=12'; sleep 0.3; printf '345\\n'; sleep 30")
        m = s.expect_line(r"n=(\d+)")
        self.assertEqual(m.group(1), "12345")


if __name__ == "__main__":
    unittest.main()
