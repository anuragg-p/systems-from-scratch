"""03.01 An editor, and its text in one array

bin/edit with its text in one array: its replay of random edits of the book prints exactly what a
Python model of the edits prints; on a terminal it shows the file, types, splits and joins lines,
saves and quits. Each insert moves every byte after it: typing k keys at the start of a text of S
bytes moves k*S bytes, while the editor itself reads only what the screen shows, a screenful a key
whatever the size of the file. Bad scripts and a missing terminal are ordinary errors.
"""


def test(t):
    T = t.track
    fx = T.fixtures("edit")
    book = T.data(t, "book.txt")
    with open(book, "rb") as f:
        data = f.read()

    # the replay, against the model: random edits of the book, and of an empty file
    for seed in (1, 2, 3):
        fx.check(t, fx.random_script(seed, data, 200, undo=False), book, algos=["array"])
    empty = T.write(t, "empty.txt", "")
    fx.check(t, fx.random_script(4, b"", 200, undo=False), empty, algos=["array"])
    fx.check(t, "type a\\tb\\\\c\\x41\\n\ngoto 1:2\ntype X\ngoto 2:1\npaste YZ\nprint\n", empty, algos=["array"])
    r = fx.replay(t, "array", "type new\nprint\n", t.tmp + "/no-such-file.txt")
    t.check(r.out == "new", f"a file that is not there is an empty text: {r.out!r}")

    # every insert moves every byte after it: k keys typed at the start of S bytes move k*S
    k, size = 500, len(data)
    r = fx.replay(t, "array", "goto 0\ntype " + "x" * k + "\n", book, env={"DS_STATS": "1"})
    a = T.stats(r.err)["flat array"]
    t.check(a["bytes loaded"] == size, f"the whole file is read into the array: {a}")
    t.check(a["inserts"] == k and a["bytes moved"] == k * size, f"{k} keys at the start move {k} * {size} bytes: {a}")
    r = fx.replay(t, "array", "goto end\ntype " + "x" * k + "\nback 100\n", book, env={"DS_STATS": "1"})
    a = T.stats(r.err)["flat array"]
    t.check(a["bytes moved"] == 0 and a["erases"] == 100, f"at the end nothing moves: {a}")
    t.check(a["grows"] == 1 and a["bytes copied"] == size, f"a full array moves once to one twice the size: {a}")

    # the editor on a terminal: the file, typing, Enter, Backspace joining lines, saving
    ed = fx.edit(t, "hello world\nsecond line\n", algo="array")
    t.check(ed.line(0) == "hello world" and ed.line(1) == "second line" and ed.line(2) == "~", ed.text())
    t.check(ed.status.startswith("f.txt - 2 lines") and ed.status.endswith("flat array 1/2"), f"{ed.status!r}")
    ed.keys(fx.RIGHT * 5, ",", fx.DOWN, fx.ENTER, "new ")
    t.check(ed.lines[:4] == ["hello, world", "second", "new  line", "~"] and ed.cursor == (2, 4), ed.text())
    ed.keys(fx.LEFT * 4, fx.BACKSPACE)
    t.check(ed.lines[:3] == ["hello, world", "secondnew  line", "~"] and ed.cursor == (1, 6), ed.text())
    t.check("(modified)" in ed.status and "2 lines" in ed.status, f"{ed.status!r}")
    ed.keys(fx.ctrl("s"))
    t.check(ed.saved() == b"hello, world\nsecondnew  line\n", f"saved {ed.saved()!r}")
    t.check(ed.message == "29 bytes written on disk", f"{ed.message!r}")
    ed.quit()

    # A key costs the editor a screenful of reading, in a file of 10 lines or of 20000: it
    # finds the lines on the screen and no others (it reads the whole file once, at the start,
    # to count its lines). The array moves the whole file at every key.
    cost = {}
    for lines in (10, 20000):
        text = "".join(f"line {i} of the file\n" for i in range(lines))
        ed = fx.edit(t, text, name=f"big{lines}.txt", algo="array", env={"DS_STATS": "1"})
        ed.keys(fx.DOWN, "a", "b", "c", "d", "e")
        ed.quit()
        s = ed.stats()
        cost[lines] = {"read a key": (s["edit"]["bytes read"] - len(text)) // 6,
                       "moved a key": s["flat array"]["bytes moved"] // 5}
    t.check(cost[20000]["read a key"] < 4 * cost[10]["read a key"] < 4 * 24 * 128,
            f"the editor reads at most a screenful (24 rows, 128 bytes each) a key, whatever the file: {cost}")
    t.check(cost[20000]["moved a key"] > 1000 * cost[10]["moved a key"], f"the array moves the file: {cost}")

    # ordinary errors
    for script, err in (("frobnicate\n", "script line 1: unknown command 'frobnicate'"),
                        ("type ab\ngoto 99999999\n", "script line 2: goto 99999999: the text is"),
                        ("goto 99999:1\n", "goto 99999:1: the last line is 11923"),
                        ("goto 1:500\n", "goto 1:500: line 1 has"),
                        ("back x\n", "back wants a count, not 'x'"),
                        ("type \\q\n", "no escape '\\q'")):
        r = fx.replay(t, "array", script, book, check=False)
        t.check(r.rc == 2 and err in r.err, f"{script!r}:\n{r}")
    r = T.run(t, "edit", ["--algo=array", book], check=False)
    t.check(r.rc == 2 and "must be a terminal" in r.err, f"no terminal:\n{r}")
    r = T.run(t, "edit", ["--frob", book], check=False)
    t.check(r.rc == 2 and "unknown option '--frob'" in r.err, f"--frob:\n{r}")
    r = T.run(t, "edit", [], check=False)
    t.check(r.rc == 2 and "usage: edit" in r.err, f"no file:\n{r}")
