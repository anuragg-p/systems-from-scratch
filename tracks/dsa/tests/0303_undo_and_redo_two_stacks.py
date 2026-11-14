"""03.03 Undo and redo: two stacks

Undo takes the last edit off one stack and does its opposite; redo takes it off the other and does
it again; a new edit empties the redo stack. Random edits with undo and redo give the model's bytes
on every structure. Typing is one edit, not one a key, and so is a run of Backspaces; moving the
cursor ends it. On a terminal Ctrl-Z and Ctrl-Y undo and redo, and the cursor goes where the edit
was, scrolling there if it is off the screen.
"""


def test(t):
    T = t.track
    fx = T.fixtures("edit")
    book = T.data(t, "book.txt")
    with open(book, "rb") as f:
        data = f.read()

    # random edits with undo and redo, on every structure there is
    for seed in (21, 22, 23):
        fx.check(t, fx.random_script(seed, data, 250), book)
    fx.check(t, fx.random_script(24, b"", 300), T.write(t, "empty.txt", ""))

    # what an edit is, and the two stacks
    f = T.write(t, "f.txt", "one two\n")
    script = ("goto 3\ntype  and a half\ntype , or so\nback 6\nback 1\n"      # one typed edit, one run of Backspace
              "print\nundo\nprint\nundo\nprint\nredo 5\nprint\n"
              "undo\ngoto 0\ntype >\nredo\nprint\n")                        # a new edit: nothing to redo
    got = fx.check(t, script, f)
    want = (b"one and a half two\n" + b"one and a half, or so two\n" + b"one two\n" +
            b"one and a half two\n" + b">one and a half, or so two\n")
    r = fx.replay(t, "tree", script, f, env={"DS_STATS": "1"})
    t.check(r.raw == want, f"undo and redo: {r.raw!r}")
    for algo in fx.ALGOS:
        u = got[algo]["undo"]
        t.check(u["edits"] == 3 and u["undos"] == 3 and u["redos"] == 2,
                f"--algo={algo}: typing is one edit, Backspaces one, '>' one; 3 undos, 2 redos: {u}")
        t.check(u["bytes kept"] == len(" and a half, or so") + 1,
                f"--algo={algo}: the redo stack was emptied by '>': {u}")
    r = fx.replay(t, "gap", "undo 3\nredo 2\nprint\n", f)
    t.check(r.out == "one two\n", f"nothing to undo or redo is no error: {r.out!r}")

    # on a terminal: Ctrl-Z, Ctrl-Y, and the cursor where the edit was
    text = "".join(f"line {i}\n" for i in range(1, 61))
    ed = fx.edit(t, text, algo="gap", rows=12, cols=40)
    ed.keys(fx.RIGHT * 4, "s", "!", fx.DOWN, fx.LEFT, fx.LEFT, fx.ENTER, fx.BACKSPACE)
    t.check(ed.line(0) == "lines! 1" and ed.line(1) == "line 2" and ed.cursor == (1, 4), ed.text())
    ed.keys(fx.ctrl("z"))                    # the Backspace: the line is split again
    t.check(ed.line(1) == "line" and ed.line(2) == " 2" and ed.cursor == (2, 0), ed.text())
    ed.keys(fx.ctrl("z"))                    # the Enter
    t.check(ed.line(1) == "line 2" and ed.cursor == (1, 4), ed.text())
    ed.keys(fx.PAGE_DOWN, fx.PAGE_DOWN, fx.PAGE_DOWN)
    t.check(ed.line(0) != "lines! 1", ed.text())
    ed.keys(fx.ctrl("z"))                    # "s!", far above the screen: it scrolls there
    t.check(ed.line(0) == "line 1" and ed.cursor == (0, 4), ed.text())
    ed.keys(fx.ctrl("z"))
    t.check(ed.message == "Nothing to undo", f"{ed.message!r}")
    ed.keys(fx.ctrl("y"), fx.ctrl("y"))
    t.check(ed.line(0) == "lines! 1" and ed.line(1) == "line" and ed.line(2) == " 2" and ed.cursor == (2, 0),
            ed.text())
    ed.keys(fx.ctrl("s"))
    t.check(ed.saved() == text.replace("line 1\n", "lines! 1\n", 1).replace("line 2\n", "line\n 2\n", 1).encode(),
            f"saved {ed.saved()[:40]!r}")
    ed.quit()
