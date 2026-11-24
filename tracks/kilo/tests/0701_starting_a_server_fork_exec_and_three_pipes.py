"""07.01 Starting a server: fork, exec and three pipes

kilo starts the language server for a file as a child process: clangd for C
and C++ by the file's name, or whatever KILO_LSP names, for any file. The
child's standard input and output are pipes to kilo, its standard error is
/dev/null, and it has no other descriptor of kilo's. A third pipe brings
back execvp's errno, so a server that cannot start is said at once, in one
line, and the editor works as before. A file with no server is edited as it
was without the module, to the byte. At exit kilo stops the server within
half a second, killing it if it will not go, and reaps it.
"""

import os
import re
import time


def test(t):
    tr = t.track

    # No server for a .txt file: not a word, and the first screen is the core's, to the byte
    # (00.02 holds the same bytes), with KILO_LSP not set at all.
    ed = tr.edit(t, "ab\n", rows=6, cols=20, lsp="table")
    want = (b"\x1b[?25l\x1b[Hab\x1b[0K\r\n~\x1b[0K\r\n~\x1b[0K\r\n~\x1b[0K\r\n"
            b"\x1b[0K\x1b[7mf.txt - 1 lines  1/1\x1b[0m\r\n\x1b[0KHELP: Ctrl-S = save "
            b"\x1b[1;1H\x1b[?25h")
    t.check(ed.raw == want, f"a .txt file is drawn as without a server:\n{ed.raw!r}")
    t.check(tr.children(ed.s.proc.pid) == [], f"and nothing is started: {tr.children(ed.s.proc.pid)}")
    ed.quit()
    # KILO_LSP set and empty: no server, even for a C file.
    ed = tr.edit(t, "int x;\n", name="t.c", lsp=None)
    t.check(ed.message.startswith("HELP:") and tr.children(ed.s.proc.pid) == [],
            f"KILO_LSP= starts nothing: {ed.message!r} {tr.children(ed.s.proc.pid)}")
    ed.quit()

    # The scripted server: started, and said so on the first screen.
    ed = tr.edit(t, "hello\n", name="t.c", lsp="")
    m = re.search(rb"lsp: started scripted-lsp \(pid (\d+)\)", ed.raw)
    t.check(m, f"the first screen says the server started: {ed.message!r}")
    pid = int(m.group(1))
    ed.wait_for(lambda: any(e["event"] == "start" for e in ed.server_log()), "the server's start")
    start = next(e for e in ed.server_log() if e["event"] == "start")
    t.check(start["pid"] == pid and start["ppid"] == ed.s.proc.pid,
            f"pid {start['pid']} (said {pid}), parent {start['ppid']} (kilo is {ed.s.proc.pid})")
    # Its descriptors: the two pipes on 0 and 1, /dev/null on 2, and nothing else of kilo's
    # (not the terminal, not the third pipe, not kilo's own ends of the pipes).
    t.check(start["fds"] == {"0": "pipe", "1": "pipe", "2": "devnull"},
            f"the server's descriptors: {start['fds']}")
    # kilo holds SIGWINCH back across fork(); the server must not start with it still blocked.
    import signal
    t.check(int(signal.SIGWINCH) not in start["blocked"], f"signals blocked in the server: {start['blocked']}")
    t.check([p for p, _ in tr.children(ed.s.proc.pid)] == [pid], f"kilo's children: {tr.children(ed.s.proc.pid)}")
    # At exit it is stopped and reaped: by the time kilo has exited, it has too.
    t.check(ed.quit() == 0, "Ctrl-Q quits")
    t.check(not tr.alive(pid), f"the server {pid} is gone once kilo has exited")

    # A server that cannot start: one line, at once, and the editor edits and saves as before.
    env = dict(os.environ, KILO_LSP=os.path.join(t.tmp, "no-such-server"))
    ed = tr.edit(t, "abc\n", name="t.c", lsp="env", env=env)
    t.check(ed.message == "lsp: cannot start no-such-server: No such file or directory",
            f"a missing server: {ed.message!r}")
    t.check(tr.children(ed.s.proc.pid) == [], f"the child that failed to exec is reaped: {tr.children(ed.s.proc.pid)}")
    ed.keys("X", tr.ctrl("s"))
    t.check(ed.saved() == "Xabc\n", f"and kilo edits and saves: {ed.saved()!r}")
    ed.quit()
    # A file that is not a program: the errno that execvp() gave, whatever it is.
    notprog = os.path.join(t.tmp, "not-a-program")
    with open(notprog, "w") as f:
        f.write("just text\n")
    env = dict(os.environ, KILO_LSP=notprog)
    ed = tr.edit(t, "abc\n", name="t.c", lsp="env", env=env)
    t.check(ed.message == "lsp: cannot start not-a-program: Permission denied", f"{ed.message!r}")
    ed.quit()

    # A server that never reads and never exits: at Ctrl-Q kilo waits LSP_STOP_MS, half a
    # second, then kills it, and the terminal is put back.
    ed = tr.edit(t, "x\n", name="t.c", lsp="srv.read = False\n")
    ed.wait_for(lambda: any(e["event"] == "start" for e in ed.server_log()), "the server's start")
    pid = next(e for e in ed.server_log() if e["event"] == "start")["pid"]
    t0 = time.monotonic()
    t.check(ed.quit() == 0, "Ctrl-Q quits")
    took = time.monotonic() - t0
    t.check(0.4 < took < 3, f"kilo waited about half a second for the server: {took:.2f}s")
    t.check(not tr.alive(pid), f"and killed it: {pid} is gone")
    t.check(not any(e["event"] == "exit" for e in ed.server_log()),
            f"by SIGKILL (it never logged an exit of its own): {ed.log_text()}")
    import termios
    t.check(ed.termios()[3] & termios.ECHO, "the terminal is back in cooked mode (ECHO on)")
