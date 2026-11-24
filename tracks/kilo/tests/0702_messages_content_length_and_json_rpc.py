"""07.02 Messages: Content-Length and JSON-RPC

Every message, either way, is a header ("Content-Length: N", an empty
line) and N bytes of JSON-RPC. kilo's first is initialize, with id 1. It
reads what the server writes in whatever pieces the pipe brings: a byte at
a time, or two messages in one read. Header names are read without case;
Content-Type and headers it does not know are ignored. A header it cannot
read (no length, a bad number, one over 16 MB, a header over 4096 bytes)
leaves no way to find the next message, so the server is stopped, in one
line, and kilo edits on. A server that dies, at any point, is reaped and
said; one that closes its input while kilo writes does not kill kilo.
"""

import os
import subprocess
import sys

FUZZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lsp_fuzz.c")


def on_init(code):
    """A scenario: code to run (with srv and msg) instead of answering initialize."""
    body = "\n".join("        " + l for l in code.strip().split("\n"))
    return ("def on_message(srv, msg):\n"
            "    if msg and msg.get('method') == 'initialize':\n"
            "        result = {'capabilities': {'textDocumentSync': 1}, 'serverInfo': {'name': 'scripted', 'version': '1.0'}}\n"
            "        reply = srv.frame({'jsonrpc': '2.0', 'id': msg['id'], 'result': result})\n"
            f"{body}\n"
            "        return True\n")


def test(t):
    tr = t.track

    # The first message, to the byte: its header gives the body's length exactly.
    ed = tr.edit(t, "hello\n", name="t.c", lsp="")
    first = ed.wait_received("initialize")
    rec = next(e for e in ed.server_log() if e["event"] == "recv")
    want = ('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":%d,"rootUri":null,'
            '"capabilities":{"general":{"positionEncodings":["utf-8","utf-16"]},"textDocument":'
            '{"publishDiagnostics":{},"definition":{"linkSupport":false},"synchronization":'
            '{"didSave":false}}}}}' % ed.s.proc.pid)
    t.check(rec["body"] == want, f"initialize is\n{rec['body']}\nnot\n{want}")
    t.check(rec["header"] == f"Content-Length: {len(want)}", f"its header: {rec['header']!r}")
    t.check(first[0]["id"] == 1, "request 1")
    ed.wait_message(r"^lsp: scripted 1\.0 ready")
    ed.quit()

    # The answer in pieces: 10 bytes, 30, the rest, a tenth of a second apart; and a byte at a
    # time. kilo takes the message off only once all of it is there.
    for how in ("srv.pieces(reply, [10, 30], gap=0.1)", "srv.pieces(reply, [1] * len(reply), gap=0.003)"):
        ed = tr.edit(t, "hello\n", name="t.c", lsp=on_init(how), asan=True)
        ed.wait_message(r"^lsp: scripted 1\.0 ready", timeout=20)
        ed.wait_received("textDocument/didOpen")
        ed.quit()

    # Two messages in one write, the second a diagnostic: both are read.
    two = ("diag = srv.frame({'jsonrpc': '2.0', 'method': 'textDocument/publishDiagnostics', 'params': "
           "{'uri': 'file://' + os.path.realpath('t.c'), 'diagnostics': [{'range': {'start': {'line': 0, "
           "'character': 0}, 'end': {'line': 0, 'character': 5}}, 'message': 'two in one'}]}})\n"
           "srv.raw(reply + diag)")
    ed = tr.edit(t, "hello\n", name="t.c", lsp="srv.diagnose = False\n" + on_init(two), asan=True)
    ed.wait_for(lambda: ed.under(0) == "[_:hello]", "the second message's underline")
    ed.quit()

    # Header names without case, Content-Type, a header kilo does not know: all fine.
    ed = tr.edit(t, "hello\n", name="t.c", lsp=on_init(
        "body = reply.split(b'\\r\\n\\r\\n', 1)[1]\n"
        "srv.raw(b'content-LENGTH:  %d \\r\\nContent-Type: application/vscode-jsonrpc; charset=utf-8\\r\\n'"
        " b'X-Other: 1\\r\\n\\r\\n' % len(body) + body)"), asan=True)
    ed.wait_message(r"^lsp: scripted 1\.0 ready")
    ed.quit()

    # Headers that cannot be read: the server is stopped, kilo says so, and edits on.
    bad = {
        "no length": "b'Content-Type: x\\r\\n\\r\\n{}'",
        "not a number": "b'Content-Length: abc\\r\\n\\r\\n{}'",
        "a sign": "b'Content-Length: -5\\r\\n\\r\\n{}'",
        "two lengths": "b'Content-Length: 2\\r\\nContent-Length: 3\\r\\n\\r\\n{}'",
        "no colon": "b'Content-Length 2\\r\\n\\r\\n{}'",
        "over 16 MB": "b'Content-Length: 16777217\\r\\n\\r\\n'",
        "absurd": "b'Content-Length: 99999999999999999999999999\\r\\n\\r\\n'",
        "a header without end": "b'X' * 5000",
        "a header line too long": "b'X-Long: ' + b'a' * 5000 + b'\\r\\n'",
        "only newlines": "b'Content-Length: 2\\n\\n{}' + b'x' * 5000",
    }
    for what, raw in bad.items():
        ed = tr.edit(t, "abc\n", name="t.c", lsp=on_init(f"srv.raw({raw})"), asan=True)
        ed.wait_message(r"^lsp: bad message from scripted-lsp; stopped$")
        t.check(tr.children(ed.s.proc.pid) == [], f"{what}: the server is stopped and reaped: "
                                                     f"{tr.children(ed.s.proc.pid)}")
        ed.keys("X", tr.ctrl("s"))
        t.check(ed.saved() == "Xabc\n", f"{what}: kilo edits on: {ed.saved()!r}")
        t.check(ed.quit() == 0, f"{what}: and quits")

    # The largest body there may be is read whole (a notification kilo does not know).
    ed = tr.edit(t, "abc\n", name="t.c", lsp=on_init(
        "head = b'{\"jsonrpc\":\"2.0\",\"method\":\"x/big\",\"params\":\"'\n"
        "pad = head + b'a' * (16777216 - len(head) - 2) + b'\"}'\n"
        "assert len(pad) == 16777216\n"
        "srv.raw(srv.frame(pad) + reply)"), asan=True)
    ed.wait_message(r"^lsp: scripted 1\.0 ready", timeout=60)
    ed.quit()

    # A server that dies in the middle of a message, of its own accord or by a signal.
    for code, said in (("srv.raw(reply[:20]); srv.die(5)", "exited (status 5)"),
                       ("srv.raw(reply[:-1]); os.kill(os.getpid(), signal.SIGSEGV)", "exited (signal 11)")):
        ed = tr.edit(t, "abc\n", name="t.c", lsp=on_init(code), asan=True)
        ed.wait_message(rf"^lsp: scripted-lsp {said.replace('(', '[(]').replace(')', '[)]')}$")
        t.check(tr.children(ed.s.proc.pid) == [], f"reaped: {tr.children(ed.s.proc.pid)}")
        ed.keys("X", tr.ctrl("s"))
        t.check(ed.saved() == "Xabc\n", f"kilo edits on: {ed.saved()!r}")
        t.check(ed.quit() == 0, "and quits")

    # One that closes its input and stays: kilo's next write fails with EPIPE, not SIGPIPE;
    # kilo stops it, and says so once (the writes after the first send nothing).
    ed = tr.edit(t, "abc\n", name="t.c", lsp=on_init("os.close(0); srv.raw(reply); time.sleep(30)"), asan=True)
    ed.wait_message(r"^lsp: scripted-lsp exited \(signal 9\)$")
    t.check(tr.children(ed.s.proc.pid) == [], f"killed and reaped: {tr.children(ed.s.proc.pid)}")
    ed.keys("Y", tr.ctrl("s"))
    t.check(ed.saved() == "Yabc\n", f"kilo lives on: {ed.saved()!r}")
    t.check(ed.quit() == 0, "and quits")

    # The frame reader alone, under AddressSanitizer: random and mutated input, for a while.
    fuzz(t, "frames", 3)


def fuzz(t, mode, seconds):
    """Build tests/lsp_fuzz.c with the tree's lsp.c and json.c, with AddressSanitizer (and
    UndefinedBehaviorSanitizer) where the compiler has them, and run it in this mode."""
    exe = os.path.join(t.tmp, "lsp-fuzz")
    cc = os.environ.get("CC", "cc")
    for flags in (["-fsanitize=address,undefined", "-fno-sanitize-recover=undefined"], ["-fsanitize=address"], []):
        r = subprocess.run([cc, "-std=c99", "-g", "-O1", "-fno-omit-frame-pointer"] + flags +
                           ["-I", t.root, "-o", exe, FUZZ], capture_output=True, text=True)
        if r.returncode == 0:
            break
    t.check(r.returncode == 0, f"the fuzz driver does not build: {r.stderr[-800:]}")
    # Leaks too, where LeakSanitizer exists (Linux; not macOS): a tree the readers drop is one.
    env = dict(os.environ, UBSAN_OPTIONS="print_stacktrace=1")
    if sys.platform.startswith("linux"):
        env["ASAN_OPTIONS"] = "detect_leaks=1"
    try:
        p = subprocess.run([exe, mode, str(seconds)], capture_output=True, text=True, timeout=seconds + 60, env=env)
    except subprocess.TimeoutExpired:
        t.check(False, f"the {mode} fuzzer hung")
    t.check(p.returncode == 0 and "ok" in p.stdout,
            f"the {mode} fuzzer ({' '.join(flags) or 'no sanitizer'}): status {p.returncode}\n"
            f"{p.stdout[-400:]}{p.stderr[-2000:]}")
    return p.stdout
