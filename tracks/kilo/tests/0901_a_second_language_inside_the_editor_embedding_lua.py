"""09.01 A second language inside the editor: embedding Lua

kilo starts a Lua state after it has read the file and runs the user's
init file in it: $KILO_INIT (set and empty: none), else
$XDG_CONFIG_HOME/kilo/init.lua, else $HOME/.config/kilo/init.lua; with no
file, not a word, and the screen is the core's to the byte. print() goes to
the message line, its control bytes shown as '?' (a tab as a space). An
error is one line there, "init.lua:3: ...", and the editor goes on.
Ctrl-E asks for a line of Lua ("lua: "): tried as an expression first,
its values shown; else run as a statement; Escape leaves; 256 bytes at most.
At exit the terminal is put back first, then the state is closed.
"""

import os


def test(t):
    tr = t.track

    # No init file: not a word, and the first screen is the core's, byte for byte (00.02).
    ed = tr.edit(t, "ab\n", rows=6, cols=20)
    want = (b"\x1b[?25l\x1b[Hab\x1b[0K\r\n~\x1b[0K\r\n~\x1b[0K\r\n~\x1b[0K\r\n"
            b"\x1b[0K\x1b[7mf.txt - 1 lines  1/1\x1b[0m\r\n\x1b[0KHELP: Ctrl-S = save "
            b"\x1b[1;1H\x1b[?25h")
    t.check(ed.raw == want, f"with no init file the first screen is the core's:\n{ed.raw!r}")
    ed.quit()

    # print() in init.lua: the message line, on the first screen.
    ed = tr.edit(t, "x\n", init='print("hello from init.lua")\n')
    t.check(ed.message == "hello from init.lua", f"{ed.message!r}")
    ed.quit()
    # Its arguments as Lua's print joins them, a tab between (shown as a space); a control
    # byte as '?', and the escape never reaches the terminal.
    ed = tr.edit(t, "x\n", init='print(1, "two", nil, true, "a\\27[2Jb\\0c")\n')
    t.check(ed.message == "1 two nil true a?[2Jb?c", f"{ed.message!r}")
    t.check(b"\x1b[2J" not in ed.raw, "the escape sequence reached the terminal")
    ed.quit()

    # An error: its first line, the file's own name in front; the editor edits and saves.
    ed = tr.edit(t, "abc\n", init="x = 1\nlocal t = nil\nt.y = 2\n")
    t.check(ed.message == "init.lua:3: attempt to index a nil value (local 't')", f"{ed.message!r}")
    ed.keys("Z", tr.ctrl("s"))
    t.check(ed.saved() == "Zabc\n", f"{ed.saved()!r}")
    ed.quit()
    for init, said in (("local x = = 1\n", "init.lua:1: unexpected symbol near '='"),
                       ('error("first line\\nsecond line")\n', "init.lua:1: first line"),
                       ("error({})\n", "(error object is a table value)"),
                       ("error(\"\\27[2J\")\n", "init.lua:1: ?[2J")):
        ed = tr.edit(t, "x\n", init=init)
        t.check(ed.message == said, f"{init!r}: {ed.message!r}, not {said!r}")
        ed.quit()
    # The init file is named by its own name, wherever it is.
    os.makedirs(os.path.join(t.tmp, "deep", "er"))
    with open(os.path.join(t.tmp, "deep", "er", "mine.lua"), "w") as f:
        f.write("\n\nnosuch()\n")
    env = dict(os.environ, KILO_INIT=os.path.join(t.tmp, "deep", "er", "mine.lua"))
    ed = tr.edit(t, "x\n", init="env", env=env)
    t.check(ed.message == "mine.lua:3: attempt to call a nil value (global 'nosuch')", f"{ed.message!r}")
    ed.quit()

    # Where the init file is looked for: XDG_CONFIG_HOME, else HOME; KILO_INIT set and empty
    # means none even when those have one; a path with no file there is not a word.
    xdg, home = os.path.join(t.tmp, "xdg"), os.path.join(t.tmp, "home")
    for d, says in ((os.path.join(xdg, "kilo"), "from xdg"), (os.path.join(home, ".config", "kilo"), "from home")):
        os.makedirs(d)
        with open(os.path.join(d, "init.lua"), "w") as f:
            f.write(f'print("{says}")\n')
    base = {k: v for k, v in os.environ.items() if k not in ("KILO_INIT", "XDG_CONFIG_HOME", "HOME")}
    for extra, said in (({"XDG_CONFIG_HOME": xdg, "HOME": home}, "from xdg"),
                        ({"XDG_CONFIG_HOME": "", "HOME": home}, "from home"),
                        ({"HOME": home}, "from home"),
                        ({"KILO_INIT": "", "XDG_CONFIG_HOME": xdg, "HOME": home}, "HELP:"),
                        ({"KILO_INIT": os.path.join(t.tmp, "none.lua"), "HOME": home}, "HELP:"),
                        ({}, "HELP:")):
        ed = tr.edit(t, "x\n", init="env", env=dict(base, **extra))
        t.check(ed.message.startswith(said), f"{extra}: {ed.message!r}, not {said!r}")
        ed.quit()

    # Ctrl-E: the prompt. An expression's values; a statement; its error; Escape.
    ed = tr.edit(t, "x\n")
    ed.keys(tr.ctrl("e"))
    t.check(ed.said("lua: ") and ed.message == "lua:", f"the prompt: {ed.message!r}")
    ed.keys("1+1")
    t.check(ed.message == "lua: 1+1" and ed.cursor[0] == 0, f"{ed.message!r}")
    ed.keys(tr.ENTER)
    t.check(ed.message == "2", f"1+1: {ed.message!r}")
    ed.keys(tr.ctrl("e"), "x = 5", tr.ENTER)
    t.check(ed.message == "", f"a statement shows nothing: {ed.message!r}")
    ed.keys(tr.ctrl("e"), "x * 2, 'a', nil", tr.ENTER)
    t.check(ed.message == "10 a nil", f"several values: {ed.message!r}")
    ed.keys(tr.ctrl("e"), "string.rep('ab', 3)", tr.ENTER)
    t.check(ed.message == "ababab", f"the standard libraries: {ed.message!r}")
    ed.keys(tr.ctrl("e"), "nosuch()", tr.ENTER)
    t.check(ed.message == "lua:1: attempt to call a nil value (global 'nosuch')", f"{ed.message!r}")
    ed.keys(tr.ctrl("e"), "x = 99", tr.BACKSPACE, tr.BACKSPACE, "7", tr.ESC)
    t.check(ed.message == "", f"Escape leaves: {ed.message!r}")
    ed.keys(tr.ctrl("e"), "x", tr.ENTER)
    t.check(ed.message == "5", f"Escape ran nothing: x is {ed.message!r}")
    # Backspace edits the line; keys that are not printable are not taken.
    ed.keys(tr.ctrl("e"), "x + 10", tr.BACKSPACE, tr.LEFT, tr.ctrl("t"), "1", tr.ENTER)
    t.check(ed.message == "16", f"{ed.message!r}")
    # 256 bytes at most: the 257th is not taken.
    line = "#'" + "x" * 253 + "'"
    ed.keys(tr.ctrl("e"), line, tr.ENTER)
    t.check(ed.message == "253", f"a line of 256 bytes: {ed.message!r}")
    ed.keys(tr.ctrl("e"), "#'" + "x" * 254 + "'", tr.ENTER)
    # The 257th byte, the closing quote, was dropped: neither form compiles, and the error is the
    # statement's.
    t.check(ed.message == "lua:1: unexpected symbol near '#'", f"the 257th byte was dropped: {ed.message!r}")
    t.check(ed.lines[0] == "x" and "(modified)" not in ed.status, "the prompt typed nothing into the text")
    ed.quit()

    # At exit: the terminal is put back first, then the state is closed, its finalizers run
    # (this one notes the terminal's mode then).
    note = os.path.join(t.tmp, "at-close.txt")
    init = ("keep = setmetatable({}, {__gc = function()\n"
            f"  os.execute('stty -a < /dev/tty > {note} 2>&1')\n"
            "end})\n")
    ed = tr.edit(t, "x\n", init=init)
    t.check(ed.quit() == 0, "Ctrl-Q quits")
    t.check(os.path.exists(note), "the state was closed at exit (its finalizer ran)")
    with open(note) as f:
        words = f.read().replace(";", " ").split()
    t.check("echo" in words and "-echo" not in words and "icanon" in words,
            f"the terminal was back in its own mode when the state closed: {' '.join(words)[:200]}")
