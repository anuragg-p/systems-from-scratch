"""03.02 The gap buffer

bin/edit --algo=gap prints what the model prints, and what the array prints, on random edits of the
book. Its gap moves only when the edit is somewhere else: typing in one place moves the bytes between
the end of the file and that place once, and nothing for every key after it, where the array moves
the whole file at every key; on edits all over the text it moves exactly the distances between them.
A gap used up grows the block to twice its size. On a terminal it edits and saves as the array does.
"""


def gap_moves(data_len, script):
    """What the gap must carry across for a script of goto and type: the distance from where the
    gap is (after the text, at the start) to each insert, which then leaves it just after the
    byte put in."""
    gap, length, cursor, moved = data_len, data_len, 0, 0
    for line in script.splitlines():
        word, _, arg = line.partition(" ")
        if word == "goto":
            cursor = length if arg == "end" else int(arg)
        elif word == "type":
            for _ in arg:
                moved += abs(cursor - gap)
                cursor += 1
                gap = cursor
                length += 1
    return moved


def test(t):
    T = t.track
    fx = T.fixtures("edit")
    book = T.data(t, "book.txt")
    with open(book, "rb") as f:
        data = f.read()

    for seed in (11, 12, 13):
        fx.check(t, fx.random_script(seed, data, 200, undo=False), book, algos=["gap", "array"])
    fx.check(t, fx.random_script(14, b"", 300, undo=False), T.write(t, "empty.txt", ""), algos=["gap", "array"])

    # typing in one place: the gap goes there once; the array moves the rest of the file every key
    k, size, at = 2000, len(data), 1000
    script = fx.typing_script(at, k)
    typed = sum(len(fx.unescape(l[5:])) for l in script.splitlines() if l.startswith("type "))
    got = fx.check(t, script + "print\n", book, algos=["gap", "array"])
    g, a = got["gap"]["gap buffer"], got["array"]["flat array"]
    t.check(g["bytes loaded"] == size, f"the gap buffer reads the file in too: {g}")
    t.check(g["bytes moved"] <= size - at + typed, f"the gap moves to {at} once, and backspacing moves "
            f"it no further than what was typed: {g}")
    t.check(a["bytes moved"] > 1000 * g["bytes moved"], f"the array moves the file for every key: array {a}, gap {g}")
    t.check(1 <= g["grows"] <= 10 and g["bytes copied"] < 3 * (size + typed),
            f"a gap used up: a block twice the size, a few times: {g}")

    # edits all over: the gap carries exactly the distances between them
    script = fx.scattered_script(5, size, 300)
    got = fx.check(t, script + "print\n", book, algos=["gap"])
    want = gap_moves(size, script)
    t.check(got["gap"]["gap buffer"]["bytes moved"] == want,
            f"the gap moves the distance between one edit and the next: {got['gap']['gap buffer']}, want {want}")
    t.check(want > 50 * size, f"300 edits all over the text move the gap {want} bytes, more than 50 books")

    # on a terminal
    ed = fx.edit(t, "one\ntwo\nthree\n", algo="gap")
    t.check(ed.status.endswith("gap buffer 1/3"), f"{ed.status!r}")
    ed.keys(fx.DOWN, fx.DOWN, fx.RIGHT * 5, " four", fx.UP, fx.UP, fx.LEFT * 3, "zero ", fx.ENTER)
    t.check(ed.lines[:5] == ["zero", "one", "two", "three four", "~"] and ed.cursor == (1, 0), ed.text())
    ed.keys(fx.ctrl("s"))
    t.check(ed.saved() == b"zero \none\ntwo\nthree four\n", f"saved {ed.saved()!r}")
    ed.quit()

    # bad names, and the default
    r = T.run(t, "edit", ["--algo=rope", "--replay", "-", book], input="", check=False)
    t.check(r.rc == 2 and "no --algo 'rope' (have: array, gap" in r.err, f"--algo=rope:\n{r}")
