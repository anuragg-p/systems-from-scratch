"""03.04 The piece table: a list of pieces

bin/edit --algo=pieces prints the model's bytes on random edits. Opening a file maps it and copies
nothing (a pipe, which cannot be mapped, is read in). Typing in one place makes one piece longer;
each edit somewhere new adds pieces, and every read, insert and erase walks the list from its first
piece, so on edits all over the text the walking grows with the square of the edits. Saving
replaces the file by renaming a new one over it, so the mapped old file the pieces read from is
never changed under them.
"""


def test(t):
    T = t.track
    fx = T.fixtures("edit")
    book = T.data(t, "book.txt")
    with open(book, "rb") as f:
        data = f.read()

    for seed in (31, 32, 33):
        fx.check(t, fx.random_script(seed, data, 250), book, algos=["pieces", "array"])
    fx.check(t, fx.random_script(34, b"", 300), T.write(t, "empty.txt", ""), algos=["pieces"])

    # opening: mapped, nothing copied; a pipe is read in
    r = fx.replay(t, "pieces", "goto end\ntype x\n", book, env={"DS_STATS": "1"})
    p = T.stats(r.err)["piece list"]
    t.check(p["bytes mapped"] == len(data) and p["bytes loaded"] == 0 and p["bytes added"] == 1,
            f"the book is mapped, not read: {p}")
    r = fx.replay(t, "array", "goto end\ntype x\n", book, env={"DS_STATS": "1"})
    t.check(T.stats(r.err)["flat array"]["bytes loaded"] == len(data), "the array copies the whole file in")
    sp = T.write(t, "s.txt", "goto 0\ntype >\nprint\n")
    r = T.run(t, "edit", ["--algo=pieces", "--replay", sp, "/dev/stdin"], input=data[:1000], env={"DS_STATS": "1"})
    p = T.stats(r.err)["piece list"]
    t.check(r.raw == b">" + data[:1000] and p["bytes mapped"] == 0 and p["bytes loaded"] == 1000,
            f"a pipe cannot be mapped: it is read in: {p}")

    # typing in one place: one piece grows; three pieces in all
    got = fx.check(t, fx.typing_script(5000, 3000).replace("back 2\n", "") + "print\n", book, algos=["pieces"])
    p = got["pieces"]["piece list"]
    t.check(p["pieces"] == 3 and p["bytes added"] == p["inserts"] > 2500, f"the file, what was typed, the file: {p}")
    t.check(p["pieces walked"] <= 3 * p["inserts"], f"each key walks past one piece or two: {p}")

    # edits all over the text: pieces grow by two an edit, and the walks with them
    walked = {}
    for edits in (200, 400):
        got = fx.check(t, fx.scattered_script(edits, len(data), edits) + "print\n", book, algos=["pieces"])
        p = got["pieces"]["piece list"]
        t.check(edits <= p["pieces"] <= 2 * edits + 1, f"{edits} edits: up to two more pieces each: {p}")
        walked[edits] = p["pieces walked"]
    ratio = walked[400] / walked[200]
    t.check(3.2 < ratio < 4.8, f"twice the edits, four times the walking: {walked} (ratio {ratio:.2f})")

    # saving: the file is replaced, and the pieces still read the old one as it was
    f = T.write(t, "f.txt", "the old text\n")
    r = fx.replay(t, "pieces", "goto 4\ntype new and \nsave\ngoto end\npaste more\\n\nprint\n", f)
    t.check(r.out == "the new and old text\nmore\n", f"after a save the text is still right: {r.out!r}")
    with open(f, "rb") as fh:
        t.check(fh.read() == b"the new and old text\n", "the save wrote the text as it was then")
    ed = fx.edit(t, None, name="f.txt", algo="pieces")
    t.check(ed.line(0) == "the new and old text" and ed.status.endswith("piece list 1/1"), ed.text())
    ed.keys(fx.DOWN, "x", fx.ctrl("s"), fx.UP, fx.LEFT, "<", fx.ctrl("s"))
    t.check(ed.lines[:2] == ["<the new and old text", "x"], ed.text())
    t.check(ed.saved() == b"<the new and old text\nx", f"saved {ed.saved()!r}")
    ed.quit()
