"""07.03 Reading JSON: just enough of a parser

kilo reads each message into a tree and answers initialize's reply with
"lsp: NAME VERSION ready", from serverInfo: the name alone with no version,
the command's name with no serverInfo, a version's first word that starts
with a digit. A message that is not JSON (a bad escape, bytes after the
value, nesting deeper than 64) is dropped and the next one read: the server
goes on. Escapes decode to UTF-8, a lone surrogate and \\u0000 to U+FFFD,
and a control byte never reaches the terminal. A reply with an id kilo never
sent is ignored; an initialize reply with no object in it stops the server.
"""

import importlib.util
import os


def reply_with(result, before=()):
    """A scenario: initialize is answered with result (Python source of a value; None: the
    default) after the raw byte strings in before (Python source each)."""
    pre = "".join(f"        srv.raw({b})\n" for b in before)
    res = f"        srv.reply(msg, {result})\n" if result is not None else "        srv.default(msg)\n"
    return ("def on_message(srv, msg):\n"
            "    if msg and msg.get('method') == 'initialize':\n"
            f"{pre}{res}"
            "        return True\n")


def frame(body):
    """Python source for a whole message whose body is the bytes body (Python source too)."""
    return f"(lambda b: b'Content-Length: %d\\r\\n\\r\\n' % len(b) + b)({body})"


def test(t):
    tr = t.track
    caps = "'capabilities': {'textDocumentSync': 1}"

    # The name and version that serverInfo gives, or what there is of them.
    for info, said in [("{'name': 'scripted', 'version': '1.0'}", "scripted 1.0"),
                       ("{'name': 'onlyname'}", "onlyname"),
                       ("{'name': 'clangd', 'version': 'Apple clangd version 21.0.0 (clang-2100.1.1.101) mac'}",
                        "clangd 21.0.0"),
                       ("{'name': 'x', 'version': 'beta two'}", "x beta"),
                       (None, "scripted-lsp")]:
        result = "{" + caps + ("" if info is None else f", 'serverInfo': {info}") + "}"
        ed = tr.edit(t, "abc\n", name="t.c", lsp=reply_with(result), asan=True)
        ed.wait_message(rf"^lsp: {said} ready \| Ctrl-G")
        ed.quit()

    # Messages that are not JSON come first; each is dropped, and the reply after them read.
    bad = [frame("b'not json'"), frame("b'{\"id\":1,\"result\":{}} x'"),          # bytes after the value
           frame("b'{\"id\":1,\"result\":{\"serverInfo\":{\"name\":\"\\\\x\"}}}'"),   # an escape JSON has not
           frame("b'{\"id\":1,\"result\":{\"serverInfo\":{\"name\":\"a\\nb\"}}}'"),  # a raw newline in a string
           frame("b'{\"jsonrpc\":\"2.0\",\"method\":\"x\",\"params\":' + b'[' * 100000 + b']' * 100000 + b'}'"),
           frame("b'[' * 65 + b']' * 65"), frame("b'{\"id\":1,\"result\":[1,]}'"), frame("b''"),
           frame("b'{\"id\":1,\"result\":{\"a\":01}}'"), frame("b'\\xff\\xfe'")]
    ed = tr.edit(t, "abc\n", name="t.c", lsp=reply_with(None, bad), asan=True)
    ed.wait_message(r"^lsp: scripted 1\.0 ready")
    start = next(e for e in ed.server_log() if e["event"] == "start")
    t.check([p for p, _ in tr.children(ed.s.proc.pid)] == [start["pid"]],
            f"the server goes on after messages that are not JSON: {tr.children(ed.s.proc.pid)}")
    ed.quit()

    # Escapes: a pair is one character (4 bytes of UTF-8), a lone surrogate and \u0000 U+FFFD,
    # and a control byte becomes '?' before it reaches the screen.
    name = "\\\\u00e9\\\\ud83d\\\\ude00\\\\ud83d-\\\\udc00-\\\\u0000-\\\\u001b[31m"
    ed = tr.edit(t, "abc\n", name="t.c", lsp=reply_with(None, [frame(
        "b'{\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"capabilities\":{},\"serverInfo\":{\"name\":\"" + name + "\"}}}'")]),
        asan=True)
    want = "lsp: \u00e9\U0001F600\ufffd-\ufffd-\ufffd-?[31m ready".encode()
    ed.wait_for(lambda: want in ed.raw, "the decoded name")
    t.check(b"\x1b[31m" not in ed.raw, "no escape sequence from the server reaches the terminal")
    ed.quit()

    # Replies kilo cannot use: ids it never sent (or not as a whole number) are ignored ...
    others = [frame(f"b'{{\"jsonrpc\":\"2.0\",\"id\":{i},\"result\":{{}}}}'") for i in ("99", "\"1\"", "1.5", "1e400", "null")]
    ed = tr.edit(t, "abc\n", name="t.c", lsp=reply_with(None, others), asan=True)
    ed.wait_message(r"^lsp: scripted 1\.0 ready")
    ed.quit()
    # ... and an id of 1.0 is 1.
    ed = tr.edit(t, "abc\n", name="t.c", lsp=reply_with(None, [frame(
        "b'{\"jsonrpc\":\"2.0\",\"id\":1.0,\"result\":{\"serverInfo\":{\"name\":\"one\"}}}'")]), asan=True)
    ed.wait_message(r"^lsp: one ready")
    ed.quit()
    # A result that is not an object (or an error instead of a result): initialize failed.
    for reply in ("b'{\"id\":1,\"result\":\"yes\"}'", "b'{\"id\":1,\"result\":null}'",
                  "b'{\"id\":1,\"error\":{\"code\":-32603,\"message\":\"no\"}}'"):
        ed = tr.edit(t, "abc\n", name="t.c", lsp=reply_with(None, [frame(reply)]), asan=True)
        ed.wait_message(r"^lsp: scripted-lsp did not initialize; stopped$")
        t.check(tr.children(ed.s.proc.pid) == [], f"stopped and reaped: {tr.children(ed.s.proc.pid)}")
        ed.keys("X", tr.ctrl("s"))
        t.check(ed.saved() == "Xabc\n" and ed.quit() == 0, f"and kilo edits on: {ed.saved()!r}")

    # The reader alone, under AddressSanitizer: mutated and random input, for a while.
    out = fuzzer().fuzz(t, "json", 3)
    t.check("\"\\ud83d\"           -> ef bf bd" in out, f"the fuzzer checks the escapes: {out[:400]}")


def fuzzer():
    """The fuzz() of the 07.02 test, which builds and runs tests/lsp_fuzz.c."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = next(os.path.join(here, f) for f in os.listdir(here) if f.startswith("0702_"))
    spec = importlib.util.spec_from_file_location("test_0702_fuzz", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
