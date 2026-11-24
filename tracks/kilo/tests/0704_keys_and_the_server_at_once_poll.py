"""07.04 Keys and the server at once: poll()

kilo waits for a key and for the server in one poll(): what the server says
is acted on and drawn when it comes, with no key pressed; a server that
exits is noticed and reaped then. Keys are answered while a server floods
its output, since kilo reads at most 1 MB of it at a time and a key ends
the wait. Writes wait in a queue until the pipe takes them, so a server
that stops reading cannot hold up a key; once more than 8 MB waits for it,
it is stopped. A resize in the middle of the wait is drawn, and the wait
goes on.
"""

import time


def test(t):
    tr = t.track

    # A message that comes a second after the file is opened is drawn then, no key pressed.
    late = ("def on_message(srv, msg):\n"
            "    if msg and msg.get('method') == 'textDocument/didOpen':\n"
            "        srv.default(msg)\n"
            "        time.sleep(1)\n"
            "        srv.notify('textDocument/publishDiagnostics', {'uri': srv.uri, 'diagnostics': [\n"
            "            {'range': {'start': {'line': 0, 'character': 0}, 'end': {'line': 0, 'character': 3}},\n"
            "             'message': 'late'}]})\n"
            "        return True\n")
    ed = tr.edit(t, "abc def\n", name="t.c", lsp=late, asan=True)
    ed.wait_message(r"ready")
    frames = ed.screen.frames
    ed.wait_for(lambda: ed.under(0) == "[_:abc] def", "the late message's underline", timeout=10)
    t.check(ed.screen.frames > frames, "drawn by kilo itself, with no key")
    # A resize while kilo waits: drawn at the new size, and the wait goes on.
    ed.resize(20, 60)
    t.check(ed.under(0) == "[_:abc] def" and len(ed.status) == 60, f"after a resize: {ed.status!r}")
    ed.keys("x")
    t.check(ed.line(0) == "xabc def", f"keys still reach it: {ed.line(0)!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # A server that exits while kilo waits for a key: said, and reaped, at once.
    ed = tr.edit(t, "abc\n", name="t.c", lsp=(
        "def on_message(srv, msg):\n"
        "    if msg and msg.get('method') == 'initialized':\n"
        "        time.sleep(0.5)\n"
        "        srv.die(7)\n"))
    ed.wait_message(r"^lsp: scripted-lsp exited \(status 7\)$")
    t.check(tr.children(ed.s.proc.pid) == [], f"reaped: {tr.children(ed.s.proc.pid)}")
    ed.keys("x")
    t.check(ed.line(0) == "xabc", "and with no server, keys are read as before")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # A server that writes without end: every key is still answered at once.
    flood = ("def on_message(srv, msg):\n"
             "    if msg and msg.get('method') == 'initialized':\n"
             "        noise = srv.frame({'jsonrpc': '2.0', 'method': 'window/logMessage',\n"
             "                           'params': {'type': 4, 'message': 'x' * 1000}}) * 64\n"
             "        while True:\n"
             "            srv.raw(noise)\n"
             "    return False\n")
    ed = tr.edit(t, "abc\n", name="t.c", lsp=flood, asan=True)
    ed.wait_message(r"ready")
    for k in "hello":
        t0 = time.monotonic()
        ed.keys(k)
        t.check(time.monotonic() - t0 < 3, f"a key took {time.monotonic() - t0:.1f}s while the server floods")
    t.check(ed.line(0) == "helloabc", f"typed while it floods: {ed.line(0)!r}")
    ed.keys(tr.ctrl("s"))
    t0 = time.monotonic()
    t.check(ed.quit() == 0 and time.monotonic() - t0 < 3, "and it quits, within LSP_STOP_MS of waiting")

    # A server that stops reading: what kilo sends waits in the queue, keys go on being
    # answered, and once more than 8 MB waits the server is stopped. A 5 MB file: didOpen
    # (5 MB), then a change (5 MB more), then Ctrl-G's request finds the queue over 8 MB.
    big = "".join(f"line {i:07d} of a file larger than the pipe\n" for i in range(110000))
    stuck = ("def on_message(srv, msg):\n"
             "    if msg and msg.get('method') == 'initialize':\n"
             "        srv.default(msg)\n"
             "        time.sleep(1000)\n")
    ed = tr.edit(t, big, name="t.c", lsp=stuck)
    ed.wait_message(r"ready")
    t0 = time.monotonic()
    ed.keys("x")
    time.sleep(0.6)                     # the pause: the change is queued behind didOpen
    ed.keys("y")
    t.check(time.monotonic() - t0 < 5 and ed.line(0).startswith("xyline"), f"keys go on: {ed.line(0)!r}")
    ed.keys(tr.ctrl("g"))
    ed.wait_message(r"^lsp: scripted-lsp is not reading; stopped$")
    t.check(tr.children(ed.s.proc.pid) == [], f"stopped and reaped: {tr.children(ed.s.proc.pid)}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "xy" + big, "the file is saved as typed")
    ed.quit()
