"""09.10 Features as scripts

Three plugins written only in Lua, on the API of 09.01 to 09.09, each
standing in for a feature the editor or module 06 has in C: plugins/vi.lua
(a normal and an insert mode on KeyPress), plugins/colour.lua (colours for
C and Lua as module 06 gives C, by highlights over the rows on the screen)
and plugins/find.lua (find as you type and go to a line, on keys of their
own). init.lua loads them with require, the project's directory on
package.path. Driven as a user does at the project of 09.10 (the core and
module 09), and in the finished project, together with 06, 07 and 08.
"""

import os
import subprocess

from harness import core, timeline


def project(t):
    """The project at 09.10, written out as the site shows it and built (against the track's
    Lua), in the scratch directory: its directory and its kilo."""
    dest = os.path.join(t.tmp, "p0910")
    timeline.Project(core.Track("kilo")).materialize("09.10", dest)
    lua = os.path.join(t.root, "lua", "src")
    flags = []
    for extra in (["-fsanitize=address", "-g"], []):
        r = subprocess.run([os.environ.get("CC", "cc"), "-std=c99", "-o", "kilo", "kilo.c", "script.c", "-I" + lua,
                            os.path.join(lua, "liblua.a"), "-lm"] + extra, cwd=dest, capture_output=True, text=True)
        if r.returncode == 0:
            flags = extra
            break
    t.check(r.returncode == 0, f"the project at 09.10 does not build: {r.stderr[-500:]}")
    t.check(sorted(os.listdir(os.path.join(dest, "plugins"))) == ["colour.lua", "find.lua", "vi.lua"],
            f"the plugins at 09.10: {os.listdir(os.path.join(dest, 'plugins'))}")
    return dest, os.path.join(dest, "kilo"), bool(flags)


def loader(root, *names):
    """An init.lua that loads the plugins named, in that order."""
    return (f"package.path = {root!r} .. '/?.lua;' .. package.path\n"
            + "".join(f"require('plugins.{n}')\n" for n in names))


def editor(t, exe, text, name, init, **kw):
    tr = t.track
    path = os.path.join(t.tmp, name)
    with open(path, "w", encoding="latin-1", newline="") as f:
        f.write(text)
    ipath = os.path.join(t.tmp, name + ".init.lua")
    with open(ipath, "w") as f:
        f.write(init)
    env = dict(os.environ, KILO_INIT=ipath, KILO_LSP="", ASAN_OPTIONS="detect_leaks=0")
    ed = tr.Editor(t, [name], cwd=t.tmp, exe=exe, env=env, **kw)
    ed.path = path
    return ed


def test(t):
    tr = t.track
    root, exe, asan = project(t)

    def lua(ed, line):
        ed.keys(tr.ctrl("e"), line, tr.ENTER)
        return ed.message

    paste = "".join(chr(97 + i % 26) for i in range(60))

    def pasted(ed, rest, what):
        """Sixty letters in one write, as a paste arrives, in vi's insert mode: colour.lua runs
        on each, its count hook reads the letters that arrive meanwhile, and they are kept for
        the editor: all sixty arrive, in order."""
        ed.keys("i")
        before = ed.screen.frames
        ed.s.send(paste)
        ed.wait_frame(before)
        got = ed.lines[0][:-len(rest)] if ed.lines[0].endswith(rest) else ed.lines[0]
        t.check(ed.lines[0] == paste + rest, f"{what}: a paste of 60 letters, {len(got)} arrive: {got!r}")

    # vi.lua: normal mode, then insert mode, the mode in the status bar.
    ed = editor(t, exe, "alpha beta\ngamma\ndelta epsilon\n", "v.txt", loader(root, "vi"))
    t.check(ed.status.startswith("-- NORMAL -- v.txt ") and ed.status.endswith("1/3"), f"{ed.status!r}")
    ed.keys("l", "l")
    t.check(ed.cursor == (0, 2), f"l l: {ed.cursor}")
    ed.keys("$")
    t.check(ed.cursor == (0, 9), f"$: on the last character: {ed.cursor}")
    ed.keys("0", "h")
    t.check(ed.cursor == (0, 0), f"0, and h at the start stays: {ed.cursor}")
    ed.keys("j", "j", "j", "k")
    t.check(ed.cursor == (1, 0), f"j j j (stops at the last row) k: {ed.cursor}")
    ed.keys("q", "w", "Z")
    t.check(ed.lines[:3] == ["alpha beta", "gamma", "delta epsilon"], f"unbound keys do nothing: {ed.lines[:3]}")
    ed.keys("k", "x")
    t.check(ed.lines[0] == "lpha beta", f"x: {ed.lines[0]!r}")
    ed.keys("j", "d", "d")
    t.check(ed.lines[:3] == ["lpha beta", "delta epsilon", "~"] and ed.cursor == (1, 0), f"dd: {ed.lines[:3]} {ed.cursor}")
    ed.keys("o")
    t.check(ed.status.startswith("-- INSERT --") and ed.cursor == (2, 0), f"o: {ed.status!r} {ed.cursor}")
    ed.keys("new")
    t.check(ed.lines[2] == "new", f"typed in insert mode: {ed.lines[:4]}")
    ed.keys(tr.ESC)
    t.check(ed.status.startswith("-- NORMAL --") and ed.cursor == (2, 2), f"Esc: back one: {ed.status!r} {ed.cursor}")
    ed.keys("i", "X", tr.ESC, "a", "Y", tr.ESC)
    t.check(ed.lines[2] == "neXYw", f"i and a: {ed.lines[2]!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "lpha beta\ndelta epsilon\nneXYw\n", f"Ctrl-S, a named key, is the editor's: {ed.saved()!r}")
    t.check(ed.quit() == 0, "Ctrl-Q quits")

    # colour.lua: C as module 06 colours it, and Lua, at a project with no module 06.
    c = 'int x = 42; /* a\n comment */ char *s = "/* str";\n// line\nreturn 3.14;\n'
    ed = editor(t, exe, c, "t.c", loader(root, "colour"))
    want = ["[g:int] x = [r:42]; [c:/* a]", '[c: comment */] [g:char] *s = [m:"/* str"];', "[c:// line]",
            "[y:return] [r:3.14];"]
    t.check([ed.painted(r) for r in range(4)] == want, f"C: {[ed.painted(r) for r in range(4)]}")
    ed.keys(tr.DOWN, tr.DOWN, tr.DOWN, "while ")
    t.check(ed.painted(3) == "[y:while] [y:return] [r:3.14];", f"after a key (TextChanged): {ed.painted(3)!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()
    l = "local n = 10 -- note\nprint('hi', n)\n--[[ a block\nend ]] x = nil\n"
    ed = editor(t, exe, l, "t.lua", loader(root, "colour"))
    want = ["[y:local] n = [r:10] [c:-- note]", "print([m:'hi'], n)", "[c:--[[ a block]", "[c:end ]]] x = [g:nil]"]
    t.check([ed.painted(r) for r in range(4)] == want, f"Lua: {[ed.painted(r) for r in range(4)]}")
    ed.quit()
    # A comment opened far above the view: the rows above are read for it, again as the view moves.
    far = "/* opened\n" + "".join(f"inside {i}\n" for i in range(60)) + "*/ int y = 1;\n" + "int z = 2;\n" * 30
    ed = editor(t, exe, far, "far.c", loader(root, "colour"))
    lua(ed, "kilo.api.set_cursor({61, 0})")
    t.check(ed.painted(0) == "[c:inside 39]" and ed.line(0) == "inside 39", f"{ed.painted(0)!r}")
    t.check(ed.painted(21) == "[c:*/] [g:int] y = [r:1];", f"the comment's end: {ed.painted(21)!r}")
    ed.quit()

    # A paste with colour.lua loaded (the lesson's run found 5 of 60 arriving).
    ed = editor(t, exe, c, "p.c", loader(root, "colour", "find", "vi"))
    pasted(ed, "int x = 42; /* a", "at 09.10")
    ed.keys(tr.ESC, tr.ctrl("s"))
    t.check(ed.quit() == 0, "Ctrl-Q quits")

    # find.lua: find as you type, next and previous, Escape back; go to a line.
    ed = editor(t, exe, tr.lines_of(40), "f.txt", loader(root, "find"))
    lua(ed, "kilo.api.set_view({10, 0}) kilo.api.set_cursor({20, 3})")
    t.check(ed.line(0) == "line 11" and ed.cursor == (10, 3), f"{ed.line(0)!r} {ed.cursor}")
    ed.keys(tr.ctrl("n"))
    t.check(ed.message == "Search:  (Use ESC/Arrows/Enter)", f"{ed.message!r}")
    ed.keys("line 3")
    t.check(ed.painted(0) == "[b:line 3]" and ed.cursor == (0, 0) and ed.status.endswith("3/40"),
            f"the first match at the top: {ed.painted(0)!r} {ed.cursor} {ed.status!r}")
    t.check(ed.message == "Search: line 3 (Use ESC/Arrows/Enter)", f"{ed.message!r}")
    ed.keys(tr.DOWN)
    t.check(ed.painted(0) == "[b:line 3]0" and ed.status.endswith("30/40"), f"next: {ed.painted(0)!r}")
    ed.keys(tr.UP)
    t.check(ed.painted(0) == "[b:line 3]" and ed.status.endswith("3/40"), f"previous: {ed.painted(0)!r}")
    ed.keys(tr.UP)
    t.check(ed.painted(0) == "[b:line 3]9" and ed.status.endswith("39/40"), f"round the top: {ed.painted(0)!r}")
    ed.keys(tr.BACKSPACE, "7")
    t.check(ed.painted(0) == "[b:line 7]" and ed.status.endswith("7/40"), f"the query changed: {ed.painted(0)!r}")
    ed.keys(tr.ESC)
    t.check(ed.line(0) == "line 11" and ed.cursor == (10, 3) and ed.message == "" and "[b:" not in ed.painted(0),
            f"Escape: the cursor and the view as they were: {ed.line(0)!r} {ed.cursor} {ed.message!r}")
    ed.keys(tr.ctrl("n"), "zzz")
    t.check(ed.line(0) == "line 11" and ed.cursor == (10, 3), "no match: nothing moves")
    ed.keys(tr.ESC, tr.ctrl("n"), "line 25", tr.ENTER)
    t.check(ed.status.endswith("25/40") and ed.line(0) == "line 25" and ed.message == "", f"Enter stays: {ed.status!r}")
    ed.keys(tr.ctrl("o"), "7", tr.ENTER)
    t.check(ed.status.endswith("7/40"), f"go to line 7: {ed.status!r}")
    ed.keys(tr.ctrl("o"), "99", tr.ENTER)
    t.check(ed.message == "no line 99", f"{ed.message!r}")
    ed.quit()

    # Two plugins that want the same key. find, then vi: a find takes every key while it
    # lasts, before vi sees it. vi, then find: vi's normal mode takes the query's letters
    # first (l moves right), and the find never gets them; Escape, a named key, vi gives back.
    ed = editor(t, exe, tr.lines_of(40), "o1.txt", loader(root, "find", "vi"))
    ed.keys(tr.ctrl("n"), "line 4")
    t.check(ed.status.endswith("4/40") and ed.message == "Search: line 4 (Use ESC/Arrows/Enter)",
            f"find first: {ed.status!r} {ed.message!r}")
    ed.keys(tr.ESC)
    ed.quit()
    ed = editor(t, exe, tr.lines_of(40), "o2.txt", loader(root, "vi", "find"))
    ed.keys(tr.ctrl("n"), "l", "l")
    t.check(ed.message == "Search:  (Use ESC/Arrows/Enter)" and ed.cursor == (0, 2),
            f"vi first: the letters went to vi: {ed.message!r} {ed.cursor}")
    ed.keys(tr.ESC)
    t.check(ed.message == "", f"Escape reached the find: {ed.message!r}")
    # Two mappings of one key: the later wins.
    lua(ed, "kilo.api.set_keymap('<C-o>', function() kilo.api.message('mine') end)")
    ed.keys(tr.ctrl("o"))
    t.check(ed.message == "mine", f"{ed.message!r}")
    ed.quit()

    # The finished project: the three together with module 06's colours, module 07's server
    # (scripted) and module 08's undo.
    if not all(os.path.exists(os.path.join(t.root, f)) for f in ("lsp.c",)) or \
            "undoSave" not in open(os.path.join(t.root, "kilo.c"), errors="replace").read():
        return
    c = 'int total = 0;\nint main(void) {\n\ttotal = total + oops; /* sum */\n\treturn total;\n}\n'
    plain = tr.edit(t, c, name="plain.c")             # module 06 alone, for comparison
    sixes = [plain.painted(r) for r in range(5)]
    plain.quit()
    ed = tr.edit(t, c, name="all.c", lsp="", init=loader(t.root, "colour", "find", "vi"), asan=True)
    t.check([ed.painted(r) for r in range(5)] == sixes,
            f"colour.lua drawn over module 06's colours looks the same: {[ed.painted(r) for r in range(5)]} "
            f"against {sixes}")
    ed.wait_for(lambda: "[_:" in ed.under(2), "07's underline")
    t.check(ed.under(2) == "        total = total + [_:oops]; /* sum */", f"{ed.under(2)!r}")
    ed.keys("j", "j", "d", "d")
    t.check(ed.lines[2] == "        return total;", f"vi's dd: {ed.lines[:4]}")
    changes = len(ed.wait_received("textDocument/didChange"))
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[2] == "        total = total + oops; /* sum */", f"08's Ctrl-Z, a named key vi gives back: {ed.lines[:4]}")
    ed.wait_received("textDocument/didChange", changes + 1)
    # find's match in blue, over 06's colours and colour.lua's (find draws it again on
    # CursorMoved, after colour.lua, which was loaded first).
    ed.keys(tr.ctrl("n"), "total")
    t.check(ed.painted(0) == "[g:int] [b:total] = [r:0];", f"find, with 06's colours: {ed.painted(0)!r}")
    ed.keys(tr.ESC, tr.ctrl("n"), "return")
    t.check(ed.line(0) == "        return total;" and ed.painted(0) == "        [b:return] total;",
            f"a coloured word's match: {ed.painted(0)!r}")
    ed.keys(tr.ESC, tr.ctrl("s"))
    t.check(ed.saved() == c, f"{ed.saved()!r}")
    t.check(ed.quit() == 0, "Ctrl-Q quits")
    # Loaded the other way, find before colour: on a key that moves the cursor (Down, to the
    # next match), colour.lua draws again after find, and its yellow covers find's blue.
    for order, want in ((("colour", "find"), "[b:return] [r:2];"), (("find", "colour"), "[y:return] [r:2];")):
        ed = tr.edit(t, "return 1;\nreturn 2;\n", name="order.c", init=loader(t.root, *order))
        ed.keys(tr.ctrl("n"), "return", tr.DOWN)
        t.check(ed.painted(0) == want, f"{order}: {ed.painted(0)!r}, not {want!r}")
        ed.keys(tr.ESC)
        ed.quit()
    # The paste in the finished project, with the server: keys kept are taken without waiting
    # on the keyboard and the server (lspWaitKey()) first.
    ed = tr.edit(t, c, name="paste.c", lsp="", init=loader(t.root, "colour", "find", "vi"), asan=True)
    ed.wait_for(lambda: "[_:" in ed.under(2), "07's underline")
    pasted(ed, "int total = 0;", "finished")
    ed.keys(tr.ESC, tr.ctrl("s"))
    t.check(ed.quit() == 0, "Ctrl-Q quits")
