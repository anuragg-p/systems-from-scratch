"""A running program you talk to through stdin/stdout.

This is the one tool every track shares. The xv6 track uses it to drive
QEMU's serial console; a compiler track would use it to run a compiled
binary; an interpreter track would use it to drive a REPL. A test reads
like a person at a terminal: wait for some text, type something, wait
for the answer.

With pty=True the program runs on a pseudo-terminal instead of pipes, as
it would in a person's terminal: isatty() is true, the terminal echoes what
is typed, and stdout and stderr arrive in the order they were written.
`./learn verify` (harness/verify.py) replays lesson transcripts that way.
"""

import os
import pty as ptys
import re
import select
import signal
import subprocess
import time

from harness.core import Fail


class Session:
    def __init__(self, argv, name=None, cwd=None, env=None, fail_on=(), stdin=True, pty=False,
                 size=(50, 120)):
        self.name = name or os.path.basename(argv[0])
        self.argv = list(argv)
        # fail_on: regexes that mean "this run is already lost", such as a
        # kernel panic. expect() raises as soon as one shows up, instead of
        # waiting for its timeout.
        self.fail_on = [re.compile(p) for p in fail_on]
        self.master = None
        if pty:
            # One terminal for stdin, stdout and stderr; size: (rows, columns).
            self.master, slave = ptys.openpty()
            try:
                import fcntl
                import struct
                import termios
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", size[0], size[1], 0, 0))
            except (ImportError, OSError):
                pass
            try:
                self.proc = subprocess.Popen(self.argv, cwd=cwd, env=env, stdin=slave, stdout=slave,
                                             stderr=slave, start_new_session=True)
            except BaseException:
                os.close(self.master)
                raise
            finally:
                os.close(slave)
            os.set_blocking(self.master, False)
        else:
            self.proc = subprocess.Popen(
                self.argv,
                cwd=cwd,
                env=env,
                stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            os.set_blocking(self.proc.stdout.fileno(), False)
        self.buf = b""   # everything the program has printed
        self.pos = 0     # how far expect() has consumed self.buf
        self.eof = False

    # ------------------------------------------------------------ reading

    @property
    def output(self):
        return self.buf.decode("utf-8", "replace")

    def _pump(self, timeout):
        """Read whatever is available within timeout seconds."""
        if self.eof:
            time.sleep(min(timeout, 0.05))
            return False
        fd = self.master if self.master is not None else self.proc.stdout.fileno()
        r, _, _ = select.select([fd], [], [], max(timeout, 0))
        if not r:
            return False
        try:
            chunk = os.read(fd, 65536)
        except BlockingIOError:
            return False
        except OSError:          # a pty whose last writer has gone (EIO on Linux)
            chunk = b""
        if not chunk:
            self.eof = True
            return False
        self.buf += chunk
        return True

    def _unread(self):
        return self.buf[self.pos:].decode("utf-8", "replace")

    def expect(self, pattern, timeout=10, allow_fail=False):
        """Wait until pattern (a regex) appears in output not yet consumed.

        Returns the re.Match. Output up to the end of the match counts as
        consumed, so successive expect() calls walk forward through the
        transcript and cannot match the same text twice.
        """
        rx = re.compile(pattern)
        deadline = time.monotonic() + timeout
        while True:
            text = self._unread()
            m = rx.search(text)
            if m:
                self.pos += len(text[:m.end()].encode("utf-8", "replace"))
                return m
            if not allow_fail:
                for bad in self.fail_on:
                    b = bad.search(text)
                    if b:
                        raise Fail(f"{self.name}: saw {bad.pattern!r} while waiting for {pattern!r}")
            left = deadline - time.monotonic()
            if left <= 0:
                raise Fail(f"{self.name}: timed out after {timeout}s waiting for {pattern!r}")
            if self.eof and self.proc.poll() is not None:
                raise Fail(f"{self.name}: exited with {self.proc.returncode} while waiting for {pattern!r}")
            self._pump(min(left, 0.1))

    def expect_line(self, pattern, timeout=10, allow_fail=False):
        """Like expect(), but the match must end at the end of a line.

        Output arrives a few bytes at a time. A pattern ending in a capture
        like (\\d+) can match "12" while "345" is still on the wire; requiring
        the newline after the match means the whole line is there.
        """
        return self.expect(pattern + r"(?=\r?\n)", timeout=timeout, allow_fail=allow_fail)

    def expect_absent(self, pattern, within=1.0):
        """Fail if pattern shows up in the next `within` seconds."""
        rx = re.compile(pattern)
        deadline = time.monotonic() + within
        while time.monotonic() < deadline:
            self._pump(0.05)
            if rx.search(self._unread()):
                raise Fail(f"{self.name}: {pattern!r} appeared but should not have")

    def wait_quiet(self, quiet=0.5, timeout=20):
        """Wait until the program has printed nothing for `quiet` seconds."""
        deadline = time.monotonic() + timeout
        last = time.monotonic()
        while time.monotonic() < deadline:
            if self._pump(0.05):
                last = time.monotonic()
            elif time.monotonic() - last >= quiet:
                return
        raise Fail(f"{self.name}: never went quiet within {timeout}s")

    def skip(self):
        """Mark everything printed so far as consumed."""
        self._pump(0)
        self.pos = len(self.buf)

    # ------------------------------------------------------------ writing

    def send(self, text):
        if isinstance(text, str):
            text = text.encode()
        if self.master is not None:
            while text:
                try:
                    text = text[os.write(self.master, text):]
                except BlockingIOError:
                    self._pump(0.01)      # the terminal's input queue is full: let it drain
            return
        self.proc.stdin.write(text)
        self.proc.stdin.flush()

    def sendline(self, line):
        self.send(line + "\n")

    # ------------------------------------------------------------ ending

    def wait_exit(self, timeout=10):
        deadline = time.monotonic() + timeout
        while self.proc.poll() is None:
            if time.monotonic() > deadline:
                raise Fail(f"{self.name}: still running after {timeout}s")
            self._pump(0.05)
        while self._pump(0):
            pass
        return self.proc.returncode

    def close(self):
        if self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        for f in (self.proc.stdin, self.proc.stdout):
            try:
                if f:
                    f.close()
            except OSError:
                pass
        if self.master is not None:
            try:
                os.close(self.master)
            except OSError:
                pass
            self.master = None
            self.eof = True

    def tail(self, lines=40):
        return "\n".join(self.output.splitlines()[-lines:])
