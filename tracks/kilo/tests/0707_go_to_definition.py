"""07.07 Go to definition

Ctrl-G asks the server where the name under the cursor is defined, any
change not yet sent going first, the column in the server's units. In the
same file the cursor moves there. In another file, that file is read in
place of the open one, and the server told (didClose, didOpen), but only
with no unsaved changes; otherwise kilo says to save first. Ctrl-B goes
back to where the jump came from, and again forth. A key pressed before the
answer cancels the jump; an answer with nothing kilo can use says "no
definition found".
"""

import os
import time


def define(result, extra=""):
    """A scenario: the definition request is answered with result (Python source; it can use
    srv and path(name), the uri of a file in kilo's directory)."""
    return ("import urllib.parse\n" + extra +
            "def path(name):\n"
            "    return 'file://' + urllib.parse.quote(os.path.realpath(name), safe='/-._~')\n"
            "def on_message(srv, msg):\n"
            "    if msg and msg.get('method') == 'textDocument/definition':\n"
            f"        srv.reply(msg, {result})\n"
            "        return True\n")


def RNG(l, c):
    return f"{{'start': {{'line': {l}, 'character': {c}}}, 'end': {{'line': {l}, 'character': {c + 1}}}}}"


def test(t):
    tr = t.track

    # In the same file, past a tab: there, back, and forth again.
    text = "int total = 1;\nint main(void) {\n\treturn total;\n}\n"
    ed = tr.edit(t, text, name="t.c", lsp="", asan=True)
    ed.wait_message(r"^lsp: scripted 1\.0 ready \| Ctrl-G = definition \| Ctrl-B = back$")
    ed.keys(tr.ctrl("b"))
    t.check(ed.message == "lsp: no place to go back to", f"{ed.message!r}")
    ed.keys(tr.DOWN, tr.DOWN, *[tr.RIGHT] * 9)          # on "total", in "\treturn total;"
    t.check(ed.cursor == (2, 16), f"{ed.cursor}")
    ed.keys(tr.ctrl("g"))
    ed.wait_for(lambda: ed.cursor == (0, 4), "the jump to 'int total'")
    req = ed.received("textDocument/definition")[0]["params"]
    t.check(req["position"] == {"line": 2, "character": 9} and req["textDocument"]["uri"].endswith("/t.c"),
            f"the request: {req}")
    ed.keys(tr.ctrl("b"))
    t.check(ed.cursor == (2, 16), f"back: {ed.cursor}")
    ed.keys(tr.ctrl("b"))
    t.check(ed.cursor == (0, 4), f"and forth: {ed.cursor}")
    # A change not yet sent goes first: x typed, then Ctrl-G at once, with no pause.
    ed.keys(tr.DOWN, tr.DOWN)
    ed.s.send("x" + tr.ctrl("g"))
    ed.wait_received("textDocument/definition", 2)
    order = [m["method"] for m in ed.received() if m and m.get("method", "").startswith("textDocument/d")]
    t.check(order[-2:] == ["textDocument/didChange", "textDocument/definition"], f"{order}")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # Columns in UTF-16: two e-acutes before the name (2 bytes, 1 unit each).
    text = "int total = 1;\nchar *s = \"\u00e9\u00e9\"; int u = total;\n".encode("utf-8").decode("latin-1")
    ed = tr.edit(t, text, name="t.c", lsp="srv.encoding = None\n", asan=True)
    ed.wait_message(r"ready")
    ed.keys(tr.DOWN, *[tr.RIGHT] * 28)                   # byte 28: on "total"
    ed.keys(tr.ctrl("g"))
    ed.wait_for(lambda: ed.cursor == (0, 4), "the jump")
    req = ed.received("textDocument/definition")[0]["params"]
    t.check(req["position"] == {"line": 1, "character": 26}, f"26 UTF-16 units before byte 28: {req}")
    ed.quit()

    # Another file: read in place of this one, the server told; Ctrl-B comes back.
    with open(os.path.join(t.tmp, "lib.h"), "w") as f:
        f.write("/* lib.h */\nint helper(void);\n")
    ed = tr.edit(t, "int main(void) {\n\treturn helper();\n}\n", name="t.c",
                 lsp=define(f"[{{'uri': path('lib.h'), 'range': {RNG(1, 4)}}}, {{'uri': path('t.c'), 'range': {RNG(0, 0)}}}]"),
                 asan=True)
    ed.wait_message(r"ready")
    ed.keys(tr.DOWN, *[tr.RIGHT] * 8, tr.ctrl("g"))
    ed.wait_for(lambda: ed.status.startswith("lib.h - 2 lines"), "lib.h opened")
    t.check(ed.cursor == (1, 4) and ed.line(1) == "int helper(void);", f"{ed.cursor} {ed.line(1)!r}")
    ed.wait_received("textDocument/didOpen", 2)
    ms = [m for m in ed.received() if m and m.get("method") in ("textDocument/didClose", "textDocument/didOpen")]
    t.check([m["method"] for m in ms] == ["textDocument/didOpen", "textDocument/didClose", "textDocument/didOpen"],
            f"{[m['method'] for m in ms]}")
    t.check(ms[1]["params"]["textDocument"]["uri"].endswith("/t.c") and
            ms[2]["params"]["textDocument"]["uri"].endswith("/lib.h") and
            ms[2]["params"]["textDocument"]["version"] == 1 and
            ms[2]["params"]["textDocument"]["text"] == "/* lib.h */\nint helper(void);\n", f"{ms[1:]}")
    ed.keys(tr.ctrl("b"))
    t.check(ed.status.startswith("t.c - 3 lines") and ed.cursor == (1, 15), f"back: {ed.status!r} {ed.cursor}")
    # With unsaved changes, kilo does not leave the file.
    ed.keys("z", tr.LEFT, tr.ctrl("g"))
    ed.wait_message(r"^Unsaved changes: save first \(Ctrl-S\), then try again$")
    t.check(ed.status.startswith("t.c - 3 lines (modified)") and ed.line(1).endswith("zhelper();"),
            f"still t.c: {ed.status!r}")
    ed.keys(tr.ctrl("s"), tr.ctrl("g"))
    ed.wait_for(lambda: ed.status.startswith("lib.h"), "lib.h after the save")
    ed.quit()

    # Answers kilo cannot use, or that need care.
    cases = [("None", "^lsp: no definition found$", None),
             ("[]", "^lsp: no definition found$", None),
             ("{'uri': 'http://x/t.c', 'range': " + RNG(0, 0) + "}", "^lsp: no definition found$", None),
             ("{'uri': path('t.c') + '%00', 'range': " + RNG(0, 0) + "}", "^lsp: no definition found$", None),
             ("{'uri': path('t.c')}", "^lsp: no definition found$", None),
             ("{'uri': path('t.c'), 'range': {'start': {'line': -1, 'character': 0}}}", "^lsp: no definition found$", None),
             ("{'uri': path('t.c'), 'range': {'start': {'line': 0, 'character': 'x'}}}", "^lsp: no definition found$", None),
             ("'a string'", "^lsp: no definition found$", None),
             ("{'uri': path('missing.h'), 'range': " + RNG(0, 0) + "}", "^Can't open .*missing.h: No such file or directory$", None),
             # A LocationLink: its targetSelectionRange is where to go.
             ("[{'targetUri': path('t.c'), 'targetRange': " + RNG(0, 0) + ", 'targetSelectionRange': " + RNG(2, 1) + "}]", None, (2, 1)),
             # Past the end of the file: the last row (there is no line 99 to count a column in).
             ("{'uri': path('t.c'), 'range': {'start': {'line': 99, 'character': 99}}}", None, (2, 0)),
             # Past the end of a line: its end.
             ("{'uri': path('t.c'), 'range': {'start': {'line': 2, 'character': 99}}}", None, (2, 3))]
    for result, said, where in cases:
        ed = tr.edit(t, "abc\ndef\nghi\n", name="t.c", lsp=define(result), asan=True)
        ed.wait_message(r"ready")
        ed.keys(tr.DOWN, tr.ctrl("g"))
        if said:
            ed.wait_message(said)
            t.check(ed.cursor == (1, 0) and ed.status.startswith("t.c"), f"{result}: did not move: {ed.cursor}")
        else:
            ed.wait_for(lambda: ed.cursor == where, f"{result}: the cursor at {where}")
        ed.quit()

    # A key before the answer cancels the jump: a late answer never moves the cursor.
    ed = tr.edit(t, "int total;\nint x = total;\n", name="t.c", lsp=(
        "def on_message(srv, msg):\n"
        "    if msg and msg.get('method') == 'textDocument/definition':\n"
        "        time.sleep(1)\n"), asan=True)
    ed.wait_message(r"ready")
    ed.keys(tr.DOWN, *[tr.RIGHT] * 9, tr.ctrl("g"), tr.RIGHT)
    ed.wait_for(lambda: len(ed.received("textDocument/definition")) == 1, "the request")
    time.sleep(1.5)
    ed.keys(tr.ctrl("l"))
    t.check(ed.cursor == (1, 10), f"the late answer did not move the cursor: {ed.cursor}")
    ed.quit()

    # No server, a server not ready yet, a server that cannot find definitions.
    ed = tr.edit(t, "abc\n", name="t.c", lsp=None)
    ed.keys(tr.ctrl("g"))
    t.check(ed.message == "lsp: no server" and ed.line(0) == "abc", f"{ed.message!r}")
    ed.quit()
    ed = tr.edit(t, "abc\n", name="t.c", lsp=("def on_message(srv, msg):\n"
                                             "    if msg and msg.get('method') == 'initialize':\n"
                                             "        time.sleep(30)\n"))
    ed.keys(tr.ctrl("g"))
    t.check(ed.message == "lsp: not ready", f"{ed.message!r}")
    ed.quit()
    ed = tr.edit(t, "abc\n", name="t.c", lsp="srv.capabilities = {'textDocumentSync': 1}\n")
    ed.wait_message(r"ready")
    ed.keys(tr.ctrl("g"))
    t.check(ed.message == "lsp: scripted-lsp cannot find definitions", f"{ed.message!r}")
    ed.quit()

    # clangd, on the sample program, in a directory whose name has a space.
    if not tr.clangd():
        tr.skipped(t, "with clangd (not installed): definitions in the same file and in add.h")
        return
    d = os.path.join(t.tmp, "sam ple")
    os.makedirs(d)
    with open(os.path.join(d, "add.h"), "w") as f:
        f.write("/* add.h: the one function sum.c calls. */\nstatic inline int add(int a, int b) {\n\treturn a + b;\n}\n")
    sum_c = ('#include <stdio.h>\n#include "add.h"\n\nint main(void) {\n\tint total = add(2, 3);\n'
             '\tprintf("%d\\n", total);\n\treturn 0;\n}\n')
    ed = tr.edit(t, sum_c, name="sam ple/sum.c", lsp="table")
    ed.wait_message(r"^lsp: clangd \S+ ready", timeout=30)
    ed.keys(*[tr.DOWN] * 5, *[tr.RIGHT] * 17, tr.ctrl("g"))     # "total" in the printf line
    ed.wait_for(lambda: ed.cursor == (4, 12), "the jump to 'int total'", timeout=30)
    ed.keys(*[tr.RIGHT] * 9, tr.ctrl("g"))                     # "add" in that line
    ed.wait_for(lambda: ed.status.startswith("sam ple/add.h"), "add.h", timeout=30)
    t.check(ed.cursor == (1, 18), f"on add in add.h: {ed.cursor}")
    ed.keys(tr.ctrl("b"))
    t.check(ed.status.startswith("sam ple/sum.c") and ed.cursor == (4, 21), f"back: {ed.status!r} {ed.cursor}")
    # A space typed on the empty row 2 is an unsaved change; then Ctrl-G on add again.
    ed.keys(tr.UP, tr.UP, " ", tr.DOWN, tr.DOWN, *[tr.RIGHT] * 13, tr.ctrl("g"))
    ed.wait_message(r"^Unsaved changes: save first \(Ctrl-S\), then try again$", timeout=30)
    t.check(ed.status.startswith("sam ple/sum.c - 8 lines (modified)"), f"still sum.c: {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()
