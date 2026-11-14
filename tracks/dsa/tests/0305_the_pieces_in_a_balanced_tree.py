"""03.05 The pieces in a balanced tree

bin/edit --algo=tree prints the model's bytes on random edits, as do the other three structures:
the four agree byte for byte on a long script. The tree keeps the AVL rule after every change
(checked node by node), so it is never more than 1.44 log2(pieces) high, even when every piece is
added at the end, which would make an unbalanced tree a list. Finding a position visits a node a
level: on edits all over the text the tree looks at a few dozen nodes an operation where the list
walks hundreds of pieces, and twice the edits cost it about twice as much, not four times.
"""

import math


def test(t):
    T = t.track
    fx = T.fixtures("edit")
    book = T.data(t, "book.txt")
    with open(book, "rb") as f:
        data = f.read()
    check = {"DS_CHECK": "1"}

    for seed in (41, 42, 43):
        script = fx.random_script(seed, data, 250)
        fx.check(t, script, book, algos=["tree"])
        r = fx.replay(t, "tree", script, book, env=check)        # the AVL rule, after every change
        t.check(r.rc == 0, f"DS_CHECK=1:\n{r}")
    fx.check(t, fx.random_script(44, b"", 300), T.write(t, "empty.txt", ""), algos=["tree"])
    long = fx.random_script(45, data, 2500)
    got = fx.check(t, long, book)                              # all four, byte for byte
    tr = got["tree"]["piece tree"]
    t.check(tr["height"] <= 1.44 * math.log2(tr["pieces"] + 2), f"the tree is balanced: {tr}")

    # every piece added at one end of the text or the other: in order, the worst case for a tree
    # left alone (a key typed at the start between them, so the one at the end is a new piece)
    script = "".join(f"goto end\ntype {w}\ngoto 0\ntype >\n" for w in ("one ", "two ", "three ") * 150) + "print\n"
    got = fx.check(t, script, book, algos=["tree"])
    tr = got["tree"]["piece tree"]
    t.check(tr["pieces"] == 901 and tr["height"] <= 1.44 * math.log2(tr["pieces"] + 2) and tr["rotations"] > 800,
            f"900 pieces added at the ends, rotated into a tree about log2(900) = 10 high: {tr}")
    r = fx.replay(t, "tree", script, book, env=check)
    t.check(r.rc == 0, f"DS_CHECK=1:\n{r}")

    # edits all over: the tree against the list
    visits, walks = {}, {}
    for edits in (300, 600):
        script = fx.scattered_script(edits, len(data), edits) + "print\n"
        got = fx.check(t, script, book, algos=["tree", "pieces"])
        tr, ls = got["tree"]["piece tree"], got["pieces"]["piece list"]
        ops = tr["inserts"] + tr["erases"]
        t.check(tr["nodes visited"] < 12 * ops * math.log2(tr["pieces"] + 2),
                f"a few passes down the tree an operation: {tr}")
        visits[edits], walks[edits] = tr["nodes visited"], ls["pieces walked"]
    t.check(walks[600] > 10 * visits[600], f"the list walks far more than the tree visits: {walks} {visits}")
    t.check(visits[600] / visits[300] < 2.6 and walks[600] / walks[300] > 3.2,
            f"twice the edits: about twice the visits, four times the walking: tree {visits}, list {walks}")

    # opening maps the file, as the list does; the default is the tree
    r = T.run(t, "edit", ["--replay", "-", book], input="goto end\ntype x\n", env={"DS_STATS": "1"})
    tr = T.stats(r.err)["piece tree"]
    t.check(tr["bytes mapped"] == len(data) and tr["bytes loaded"] == 0 and tr["pieces"] == 2,
            f"the default: the tree, the file mapped: {tr}")

    # on a terminal
    ed = fx.edit(t, "".join(f"row {i}\n" for i in range(100)), algo="tree")
    t.check(ed.status.endswith("piece tree 1/100"), f"{ed.status!r}")
    ed.keys(fx.PAGE_DOWN, fx.PAGE_DOWN, "**", fx.ctrl("f"), "row 9", fx.ENTER, ">")
    t.check(ed.line(0) == ">row 9" and ed.cursor == (0, 1), ed.text())
    ed.keys(fx.ctrl("z"), fx.ctrl("z"), fx.ctrl("s"))
    t.check(ed.saved() == "".join(f"row {i}\n" for i in range(100)).encode(), f"undone and saved {ed.saved()[:30]!r}")
    ed.quit()
