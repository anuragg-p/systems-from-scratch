"""07.06 Diagnostics: errors as you type

The server's diagnostics for the open file are shown three ways: each range
underlined in the text (drawn over the row: its columns found past tabs, and
past text that is not ASCII, in UTF-16 or UTF-8 as the server chose), the
counts in the message line when they change ("lsp: 1 error, 1 warning",
"lsp: no problems"), and, when the cursor rests on a row with one, its
message: "4: error: ...". Diagnostics for another file, or for a version
older than the last sent, are ignored; a range past the end of a line ends
there, one on a line the file has not is dropped; at most 1000 are kept.
Nothing a server puts in one reaches the terminal raw.
"""

import importlib.util
import re
import os
import time
import urllib.parse


def publish(diags, extra=""):
    """A scenario: on didOpen, the diagnostics diags (Python source of a list; RNG(l, c, l2, c2)
    makes a range) for the file, instead of the tiny language's."""
    return ("srv.diagnose = False\n" + extra +
            "def RNG(l, c, l2, c2):\n"
            "    return {'start': {'line': l, 'character': c}, 'end': {'line': l2, 'character': c2}}\n"
            "def on_message(srv, msg):\n"
            "    if msg and msg.get('method') == 'textDocument/didOpen':\n"
            "        srv.default(msg)\n"
            f"        srv.notify('textDocument/publishDiagnostics', {{'uri': srv.uri, 'version': 1, 'diagnostics': {diags}}})\n"
            "        return True\n")


def test(t):
    tr = t.track

    # The tiny language: "oops" is an error, "meh" a warning. After a tab, the underline is
    # where the screen shows the word.
    text = "int a;\n\tx = oops;\n\tint meh;\n"
    ed = tr.edit(t, text, name="t.c", lsp="", asan=True)
    ed.wait_said("lsp: 1 error, 1 warning")
    t.check(ed.under(1) == "        x = [_:oops];" and ed.under(2) == "        int [_:meh];",
            f"underlined: {ed.under(1)!r} {ed.under(2)!r}")
    # The cursor comes to rest on the error's row: its message.
    ed.keys(tr.DOWN)
    ed.wait_message(r"^2: error: use of undeclared identifier 'oops'$")
    ed.keys(tr.DOWN)
    ed.wait_message(r"^3: warning: unused variable 'meh'$")
    # Fixed as you type: the counts change, and the underline goes.
    ed.keys(tr.UP, *[tr.RIGHT] * 9, *[tr.BACKSPACE] * 4, "y")
    ed.wait_said("lsp: 1 warning")
    t.check(ed.under(1) == "        x = y;", f"the error is gone: {ed.under(1)!r}")
    ed.keys(tr.DOWN, tr.RIGHT, tr.RIGHT, *[tr.BACKSPACE] * 3, "z")
    ed.wait_said("lsp: no problems")
    t.check(ed.underlined(2) == [], f"nothing underlined: {ed.under(2)!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()

    # Text that is not ASCII before the error: UTF-16 (the server leaves the encoding out, or
    # picks it) or UTF-8 (the server picks what kilo offers first). A tab, two e-acutes (2 bytes
    # each, 1 UTF-16 unit) and a grinning face (4 bytes, 2 units) before "oops".
    line = '\tprintf("\u00e9t\u00e9 \U0001F600 %d\\n", oops);'
    want = '        printf("\u00e9t\u00e9 \U0001F600 %d\\n", [_:oops]);'
    for enc, said in ((None, "utf-16"), ("'utf-16'", "utf-16"), ("'utf-8'", "utf-8")):
        ed = tr.edit(t, (line + "\n").encode("utf-8").decode("latin-1"), name="t.c",
                     lsp=f"srv.encoding = {enc}\n", utf8=True, asan=True)
        ed.wait_for(lambda: "[_:" in ed.under(0), "an underline")
        t.check(ed.under(0) == want, f"{said}: {ed.under(0)!r}, not {want!r}")
        ed.quit()

    # Ranges that are odd: over three rows; empty (one cell, a space at the end of a line);
    # an end before its start; past the end of a line; on a line the file has not (dropped).
    text = "abcdef\nghij\nklmnop\nqrs\n"
    diags = ("[{'range': RNG(0, 2, 2, 3), 'message': 'three rows'},"
             " {'range': RNG(3, 1, 3, 1), 'message': 'empty'},"
             " {'range': RNG(1, 99, 1, 99), 'message': 'past the end'},"
             " {'range': RNG(3, 3, 3, 0), 'message': 'backwards', 'severity': 2},"
             " {'range': RNG(9, 0, 9, 1), 'message': 'no such line'},"
             " {'range': RNG(0, 0, 40, 0), 'message': 'ends on no such line'}]")
    ed = tr.edit(t, text, name="t.c", lsp=publish(diags), asan=True)
    ed.wait_said("lsp: 3 errors, 1 warning")
    t.check(ed.under(0) == "ab[_:cdef]" and ed.under(1) == "[_:ghij]" and ed.under(2) == "[_:klm]nop",
            f"three rows: {[ed.under(n) for n in range(3)]}")
    t.check(ed.underlined(3) == [1, 3], f"row 3, one cell at 1 and one past the end, at 3: {ed.underlined(3)}")
    t.check(ed.underlined(1) == [0, 1, 2, 3, 4], f"row 1, and a cell past its end: {ed.underlined(1)}")
    ed.quit()

    # What is ignored: another file's, an older version's, URIs that are not file:// paths. What is
    # not: the same file named another way (through a link, letters escaped in lowercase hex).
    os.makedirs(os.path.join(t.tmp, "real"))
    os.symlink(os.path.join(t.tmp, "real"), os.path.join(t.tmp, "link"))
    ignored = ("[{'uri': 'file:///elsewhere/t.c'}, {'version': 0}, {'uri': 'http://x/t.c'}, {'uri': 'file://t.c'},"
               " {'uri': srv.uri + '%zz'}, {'uri': srv.uri + '%00'}, {'uri': 7}]")
    scen = ("srv.diagnose = False\n"
            "import urllib.parse\n"
            "def on_message(srv, msg):\n"
            "    if msg and msg.get('method') == 'textDocument/didOpen':\n"
            "        srv.default(msg)\n"
            "        d = {'range': {'start': {'line': 0, 'character': 0}, 'end': {'line': 0, 'character': 2}}}\n"
            f"        for p in {ignored}:\n"
            "            srv.notify('textDocument/publishDiagnostics', dict({'uri': srv.uri, 'version': 1, 'diagnostics': [d]}, **p))\n"
            "        path = os.path.abspath('link/t.c')\n"
            "        other = 'file://' + ''.join('%%%02x' % ord(c) if c.isalpha() and i % 2 else c\n"
            "                                    for i, c in enumerate(path))\n"
            "        d['range']['end']['character'] = 3\n"
            "        srv.notify('textDocument/publishDiagnostics', {'uri': other, 'diagnostics': [d]})\n"
            "        return True\n")
    ed = tr.edit(t, "abcdef\n", name="link/t.c", lsp=scen, asan=True)
    ed.wait_said("lsp: 1 error")
    t.check(ed.under(0) == "[_:abc]def", f"only the last, through the link: {ed.under(0)!r}")
    ed.quit()

    # Fields of the wrong type, a severity out of range, a message with newlines and an escape
    # sequence in it, a message that is not a string: no crash, nothing raw on the screen.
    diags = ("[{'range': 5}, {'range': {'start': 'x'}}, {'range': RNG(0, 0, 0, 1), 'severity': 9,"
             " 'message': 'first line\\x1b[2J\\nsecond line'}, {'range': RNG(0, 'a', 0, None)},"
             " {'range': RNG(-1, 0, 0, 1)}, {'range': RNG(0, -5, 0, 2), 'message': 7}, 'not an object']")
    ed = tr.edit(t, "abcdef\n", name="t.c", lsp=publish(diags), asan=True)
    ed.wait_said("lsp: 3 errors")
    ed.keys(tr.RIGHT)
    ed.wait_message(r"^1: error: first line\?\[2J$")
    t.check(b"\x1b[2J" not in ed.raw, "the escape sequence never reached the terminal")
    ed.quit()
    publish_type = ("srv.diagnose = False\n"
                    "def on_message(srv, msg):\n"
                    "    if msg and msg.get('method') == 'textDocument/didOpen':\n"
                    "        srv.default(msg)\n"
                    "        srv.notify('textDocument/publishDiagnostics', {'uri': srv.uri, 'diagnostics': 'none'})\n"
                    "        srv.notify('textDocument/publishDiagnostics', 'no params')\n"
                    "        srv.notify('textDocument/publishDiagnostics', None)\n"
                    "        srv.send({'jsonrpc': '2.0', 'method': 7})\n"
                    "        srv.notify('textDocument/publishDiagnostics', {'uri': srv.uri, 'diagnostics':\n"
                    "            [{'range': {'start': {'line': 0, 'character': 1}, 'end': {'line': 0, 'character': 2}}}]})\n"
                    "        return True\n")
    ed = tr.edit(t, "abc\n", name="t.c", lsp=publish_type, asan=True)
    ed.wait_said("lsp: 1 error")
    t.check(ed.under(0) == "a[_:b]c", f"{ed.under(0)!r}")
    ed.quit()

    # 1500 diagnostics, one on each row: all are counted, the first 1000 kept.
    many = "".join(f"x{i:04d} oops\n" for i in range(1500))
    ed = tr.edit(t, many, name="t.c", lsp="", asan=True)
    ed.wait_said("lsp: 1500 errors", timeout=30)
    ed.keys(tr.ctrl("f"), "x0999", tr.ENTER)
    t.check(ed.under(0) == "x0999 [_:oops]", f"the 1000th: {ed.under(0)!r}")
    ed.keys(tr.ctrl("f"), "x1000", tr.ENTER)
    t.check(ed.under(0) == "x1000 oops", f"the 1001st is not kept: {ed.under(0)!r}")
    ed.quit()

    # The view scrolled right: the underline is cut to the columns on the screen.
    ed = tr.edit(t, "x" * 76 + " oops more\n", name="t.c", lsp="", cols=80, asan=True)
    ed.wait_said("lsp: 1 error")
    t.check(ed.under(0) == "x" * 76 + " [_:oop]", f"cut at the edge: {ed.under(0)!r}")
    ed.keys(*[tr.RIGHT] * 82)
    # The view starts at column 3 now; the row fills the screen, so its last cell ("m") is
    # erased by the ESC [ 0 K after it, as on any full row (see NOTES.md).
    t.check(ed.under(0) == "x" * 73 + " [_:oops]", f"scrolled: {ed.under(0)!r}")
    ed.quit()

    # In the finished project, with module 06 there too: the colours stay where nothing is
    # underlined; the underlined span is drawn over in the default colour; a control character
    # in it (reverse video) is left as it was drawn.
    if "editorSelectSyntaxHighlight" in open(os.path.join(t.root, "kilo.c"), errors="replace").read():
        diags = "[{'range': RNG(0, 4, 0, 11), 'message': 'both'}]"
        ed = tr.edit(t, "int x\x01y = oops;\n", name="t.c", lsp=publish(diags), asan=True)
        ed.wait_for(lambda: "[_:" in ed.under(0), "the underline")
        t.check(ed.under(0) == "int [_:x]A[_:y = o]ops;", f"{ed.under(0)!r}")
        t.check(ed.painted(0) == "[g:int] x[#:A]y = oops;", f"colours: {ed.painted(0)!r}")
        ed.quit()

    # The protocol code alone, under AddressSanitizer: mutated messages, then the drawing.
    fuzzer().fuzz(t, "messages", 3)

    # And a real server: clangd, on the sample program, where it is installed.
    if not tr.clangd():
        tr.skipped(t, "with clangd (not installed): an error typed, underlined, fixed")
        return
    d = os.path.join(t.tmp, "sam ple")
    os.makedirs(d)
    with open(os.path.join(d, "add.h"), "w") as f:
        f.write("/* add.h: the one function sum.c calls. */\nstatic inline int add(int a, int b) {\n\treturn a + b;\n}\n")
    sum_c = ('#include <stdio.h>\n#include "add.h"\n\nint main(void) {\n\tint total = add(2, 3);\n'
             '\tprintf("%d\\n", total);\n\treturn 0;\n}\n')
    ed = tr.edit(t, sum_c, name="sam ple/sum.c", lsp="table")
    ed.wait_message(r"^lsp: clangd \S+ ready", timeout=30)
    ed.keys(*[tr.DOWN] * 5, *[tr.RIGHT] * 20, tr.BACKSPACE)
    ed.wait_for(lambda: "[_:totl]" in ed.under(5), "clangd's underline on totl", timeout=30)
    t.check(ed.under(5) == '        printf("%d\\n", [_:totl]);', f"{ed.under(5)!r}")
    ed.wait_for(lambda: re.search(rb"\x1b\[0Klsp: 1 error", ed.raw), "clangd's count", timeout=30)
    # clangd's list comes after the pause that sent the change: the row's message shows at the
    # next pause (here after Left and Right, the cursor where it was).
    ed.keys(tr.LEFT, tr.RIGHT)
    ed.wait_message(r"^6: error: Use of undeclared identifier 'totl'", timeout=30)
    ed.keys("a")
    ed.wait_for(lambda: ed.underlined(5) == [], "the underline gone", timeout=30)
    ed.wait_said("lsp: no problems", timeout=30)
    ed.keys(tr.ctrl("s"))
    ed.quit()


def fuzzer():
    """The fuzz() of the 07.02 test, which builds and runs tests/lsp_fuzz.c."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = next(os.path.join(here, f) for f in os.listdir(here) if f.startswith("0702_"))
    spec = importlib.util.spec_from_file_location("test_0702_fuzz", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
