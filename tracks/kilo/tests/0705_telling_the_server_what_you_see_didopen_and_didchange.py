"""07.05 Telling the server what you see: didOpen and didChange

Once initialize is answered, kilo sends initialized and then didOpen: the
file's uri (file:// and the absolute path, percent-encoded), its language,
version 1 and its text, which keys typed while the server started are
already in. kilo keeps a copy of the text the server has. When no key has
come for 300 ms and the text differs from the copy, it sends all of it in
one didChange, the next version: one per pause, not one per key, none for a
server that takes no changes. A change still waiting whole for a slow
server is replaced by a newer one. Requests from the server get "method not
found". At exit: shutdown, its answer, exit, all within half a second.
"""

import os
import time
import urllib.parse


def test(t):
    tr = t.track

    # A file in a directory whose name needs escaping in a URI, with text that needs it in JSON.
    text = 'int main(void) {\n\tchar *s = "a \\"q\\" \\\\ \t\x01\xc3\xa9";\n}\n'
    name = "a b%c/t.c"
    slow = ("def on_message(srv, msg):\n"
            "    if msg and msg.get('method') == 'initialize':\n"
            "        time.sleep(1)\n")
    ed = tr.edit(t, text, name=name, lsp=slow)
    ed.keys("X", "Y")                     # typed while the server is starting
    ed.wait_message(r"ready")
    opened = ed.wait_received("textDocument/didOpen")[0]["params"]["textDocument"]
    real = os.path.realpath(os.path.join(t.tmp, name))
    uri = "file://" + urllib.parse.quote(real, safe="/-._~")
    t.check(opened["uri"] == uri and "%20b%25c/t.c" in uri, f"the uri: {opened['uri']}, not {uri}")
    t.check(opened["languageId"] == "c" and opened["version"] == 1, f"{opened['languageId']} {opened['version']}")
    sent = text.encode("latin-1").decode("utf-8")
    t.check(opened["text"] == "XY" + sent, f"didOpen's text, keys typed meanwhile in it: {opened['text']!r}")
    methods = [m["method"] for m in ed.received() if m and "method" in m]
    t.check(methods[:3] == ["initialize", "initialized", "textDocument/didOpen"], f"in order: {methods}")

    # A burst of keys: one didChange after the pause, the whole text, version 2.
    for k in "abcde":
        ed.s.send(k)
        time.sleep(0.03)
    changes = ed.wait_received("textDocument/didChange")
    time.sleep(0.5)
    changes = ed.received("textDocument/didChange")
    t.check(len(changes) == 1, f"one didChange for the burst, not {len(changes)}")
    p = changes[0]["params"]
    t.check(p["textDocument"] == {"uri": uri, "version": 2} and p["contentChanges"] == [{"text": "XYabcde" + sent}],
            f"the change: {p}")
    # Keys that change nothing (arrows) send nothing; the next change is version 3.
    ed.keys(tr.DOWN, tr.RIGHT, tr.UP)
    time.sleep(0.6)
    t.check(len(ed.received("textDocument/didChange")) == 1, "no didChange for moving the cursor")
    ed.keys(tr.BACKSPACE)
    changes = ed.wait_received("textDocument/didChange", 2)
    t.check(changes[1]["params"]["textDocument"]["version"] == 3, f"{changes[1]['params']['textDocument']}")

    # A request from the server: answered "method not found", with its own id.
    ed.keys(tr.ctrl("s"))
    ed.quit()

    asks = ("def on_message(srv, msg):\n"
            "    if msg and msg.get('method') == 'initialized':\n"
            "        srv.send({'jsonrpc': '2.0', 'id': 'abc', 'method': 'workspace/configuration', 'params': {}})\n"
            "        srv.send({'jsonrpc': '2.0', 'id': 9, 'method': 'client/registerCapability'})\n")
    ed = tr.edit(t, "abc\n", name="t.c", lsp=asks, asan=True)
    ed.wait_for(lambda: len([m for m in ed.received() if m and "error" in m]) == 2, "two answers")
    answers = [m for m in ed.received() if m and "error" in m]
    t.check(answers == [{"jsonrpc": "2.0", "id": "abc", "error": {"code": -32601, "message": "method not found"}},
                        {"jsonrpc": "2.0", "id": 9, "error": {"code": -32601, "message": "method not found"}}],
            f"the answers: {answers}")
    # At exit: shutdown, the server's answer, exit; the server exits 0 by itself.
    t0 = time.monotonic()
    t.check(ed.quit() == 0, "Ctrl-Q quits")
    took = time.monotonic() - t0
    methods = [m["method"] for m in ed.received() if m and "method" in m]
    t.check(methods[-2:] == ["shutdown", "exit"], f"the last two: {methods[-3:]}")
    t.check(any(e["event"] == "exit" and e["status"] == 0 for e in ed.server_log()), f"{ed.log_text()}")
    t.check(took < 0.5, f"and quickly: {took:.2f}s")

    # Before initialize is answered there is nothing to shut down: kilo just stops it.
    ed = tr.edit(t, "abc\n", name="t.c", lsp=(
        "def on_message(srv, msg):\n"
        "    if msg and msg.get('method') == 'initialize':\n"
        "        time.sleep(30)\n"))
    ed.wait_received("initialize")
    t0 = time.monotonic()
    ed.quit()
    t.check(time.monotonic() - t0 < 2, f"quit took {time.monotonic() - t0:.2f}s")
    t.check(ed.received("shutdown") == [], "no shutdown before the server is ready")

    # A server that takes no changes (textDocumentSync 0) is sent none.
    ed = tr.edit(t, "abc\n", name="t.c", lsp="srv.capabilities = {'textDocumentSync': {'openClose': True, 'change': 0}}\n")
    ed.wait_received("textDocument/didOpen")
    ed.keys("x")
    time.sleep(0.8)
    t.check(ed.received("textDocument/didChange") == [], "no didChange to a server that takes none")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # A slow server: the change that is waiting whole is replaced by the next. The server
    # sleeps 3 s after didOpen; version 2 (1 MB) starts into the pipe and has to go whole,
    # version 3 waits behind it whole and is replaced by version 4.
    big = "".join(f"line {i:06d} {'x' * 40}\n" for i in range(20000))
    ed = tr.edit(t, big, name="t.c", lsp=(
        "def on_message(srv, msg):\n"
        "    if msg and msg.get('method') == 'textDocument/didOpen':\n"
        "        time.sleep(3)\n"))
    ed.wait_received("textDocument/didOpen")
    for k in "abc":
        ed.keys(k)
        time.sleep(0.6)
    ed.wait_for(lambda: len(ed.received("textDocument/didChange")) >= 2, "the changes", timeout=20)
    time.sleep(0.5)
    versions = [m["params"]["textDocument"]["version"] for m in ed.received("textDocument/didChange")]
    t.check(versions == [2, 4], f"versions sent: {versions} (3 should have been replaced by 4)")
    t.check(ed.received("textDocument/didChange")[-1]["params"]["contentChanges"][0]["text"] == "abc" + big,
            "the last is the text as it is")
    ed.keys(tr.ctrl("s"))
    ed.quit()
