"""08.04 The saved point, and a bound on memory

"(modified)" means the text differs from the file on disk: the undo
history keeps the saved point, the number of steps under the text that was
opened or last saved, and after every undo and redo the file is modified
exactly when the undo stack is not there. When the steps under it are
dropped, or undone and replaced by a new edit, the saved point is gone, and
the file stays modified until the next save. The history holds at most
UNDO_MAX_BYTES (8 MB): the oldest steps go first, a change bigger than all
of it is not remembered, and no edit is ever lost for the history's sake.
Under all of it, random keys undone to the end give back the file as it was
opened, and redone to the end the text as it was.
"""

import random


def modified(ed):
    return "(modified)" in ed.status


def test(t):
    tr = t.track

    # Undo back to the text on disk: not modified; past it, or redone past it: modified.
    ed = tr.edit(t, "one\n", asan=True)
    ed.keys("a")
    t.check(modified(ed), f"typed: {ed.status!r}")
    ed.keys(tr.ctrl("z"))
    t.check(not modified(ed), f"undone to the file as opened: {ed.status!r}")
    ed.keys(tr.ctrl("r"))
    t.check(modified(ed), f"redone: {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    t.check(not modified(ed), f"saved: {ed.status!r}")
    ed.keys(tr.ctrl("z"))
    t.check(modified(ed) and ed.line(0) == "one", f"undone past the save: {ed.status!r} {ed.line(0)!r}")
    ed.keys(tr.ctrl("r"))
    t.check(not modified(ed) and ed.line(0) == "aone", f"redone to the save: {ed.status!r}")
    ed.keys("b")
    ed.keys(tr.ctrl("z"))
    t.check(not modified(ed), f"a step after the save, undone: {ed.status!r}")
    # Back at the saved point Ctrl-Q quits at once: nothing would be lost.
    ed.keys(tr.RIGHT, "c", tr.ctrl("z"))
    t.check(ed.quit() == 0, "quit with one Ctrl-Q")

    # A new edit after undoing below the saved point: the text on disk cannot be reached by
    # undo or redo any more, so the file stays modified until it is saved.
    ed = tr.edit(t, "one\n", name="g.txt", asan=True)
    ed.keys("a", tr.ctrl("s"), tr.ctrl("z"), "c")
    t.check(ed.line(0) == "cone" and modified(ed), f"{ed.line(0)!r} {ed.status!r}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.line(0) == "one" and modified(ed), f"the file has 'aone': {ed.status!r}")
    # Redone, the undo stack is as high as it was at the save, but holds "c", not "a".
    ed.keys(tr.ctrl("r"))
    t.check(ed.line(0) == "cone" and modified(ed), f"redone, one step as at the save: {ed.status!r}")
    ed.keys(tr.ctrl("z"))
    t.check(modified(ed), f"{ed.status!r}")
    ed.keys(tr.ctrl("s"))
    t.check(not modified(ed) and ed.saved() == "one\n", f"saved again: {ed.status!r} {ed.saved()!r}")
    ed.keys(tr.ctrl("r"))
    t.check(modified(ed) and ed.line(0) == "cone", f"{ed.status!r}")
    ed.keys(tr.ctrl("z"))
    t.check(not modified(ed), f"{ed.status!r}")
    ed.quit()

    # The bound, made small. A step of one Enter on an empty file is one record and no text:
    # measure it, and allow ten.
    env, log = tr.undo_env(t)
    ed = tr.edit(t, "", name="h.txt", env=env)
    ed.keys(tr.ENTER)
    step = tr.undo_counts(log)[-1]["bytes"]
    ed.keys(tr.ctrl("z"))
    ed.quit()
    env, log = tr.undo_env(t, max_bytes=10 * step)
    # Saved after 6 steps, 12 in all: the 2 oldest are dropped, the saved point is still there.
    ed = tr.edit(t, "", name="i.txt", asan=True, env=env)
    ed.keys(*[tr.ENTER] * 6, tr.ctrl("s"), *[tr.ENTER] * 6)
    last = tr.undo_counts(log)[-1]
    t.check((last["undo"], last["saved"], last["bytes"]) == (10, 4, 10 * step), f"ten steps kept: {last}")
    t.check(all(c["bytes"] <= 10 * step for c in tr.undo_counts(log)), "never over the bound")
    ed.keys(*[tr.ctrl("z")] * 6)
    t.check(not modified(ed) and "6 lines" in ed.status, f"back to the save: {ed.status!r}")
    ed.keys(*[tr.ctrl("z")] * 4)
    t.check("2 lines" in ed.status and modified(ed), f"the 2 steps dropped stay done: {ed.status!r}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.message == "Nothing to undo", f"{ed.message!r}")
    ed.keys(*[tr.ctrl("r")] * 10)
    t.check("12 lines" in ed.status, f"all redone: {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()
    # Saved after 2 steps: 12 in all drop exactly those 2, and the saved point is the bottom of
    # the stack; one more, and it is gone.
    env, log = tr.undo_env(t, max_bytes=10 * step)
    ed = tr.edit(t, "", name="j.txt", asan=True, env=env)
    ed.keys(*[tr.ENTER] * 2, tr.ctrl("s"), *[tr.ENTER] * 10)
    t.check(tr.undo_counts(log)[-1]["saved"] == 0, f"{tr.undo_counts(log)[-1]}")
    ed.keys(*[tr.ctrl("z")] * 10)
    t.check(not modified(ed) and "2 lines" in ed.status, f"the save, at the bottom: {ed.status!r}")
    ed.keys(*[tr.ctrl("r")] * 10, tr.ENTER)
    t.check(tr.undo_counts(log)[-1]["saved"] == -1, f"{tr.undo_counts(log)[-1]}")
    ed.keys(*[tr.ctrl("z")] * 11)
    t.check(modified(ed) and "3 lines" in ed.status, f"the save is gone: {ed.status!r}")
    ed.keys(*[tr.ctrl("r")] * 10, tr.ctrl("s"))
    ed.quit()

    # A change bigger than the whole bound: not remembered, the history emptied, and said;
    # the edit is made all the same, and the rest of that step is not remembered either.
    env, log = tr.undo_env(t, max_bytes=1000)
    ed = tr.edit(t, "short\n" + "w" * 5000 + "\n", name="k.txt", asan=True, env=env)
    ed.keys("ab", tr.DOWN, tr.LEFT, tr.LEFT)
    t.check(tr.undo_counts(log)[-1]["undo"] == 1 and ed.cursor == (1, 0), f"{tr.undo_counts(log)[-1]}")
    ed.keys("X")
    t.check(ed.message == "undo: change too big to remember", f"{ed.message!r}")
    ed.keys("YZ")
    last = tr.undo_counts(log)[-1]
    t.check((last["undo"], last["records"], last["bytes"]) == (0, 0, 0), f"nothing kept: {last}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.message == "Nothing to undo" and ed.line(1).startswith("XYZw"), f"{ed.message!r}")
    ed.keys(tr.UP, "Q")
    ed.keys(tr.ctrl("z"))
    t.check(ed.line(0) == "abshort" and ed.line(1).startswith("XYZw"), f"{ed.lines[:2]}")
    t.check(modified(ed), f"the file on disk cannot be reached: {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "abshort\nXYZ" + "w" * 5000 + "\n", "the edits are all in the file")
    ed.quit()
    # A join of a short row onto that long one: the long row's record does not fit, and the
    # short row's, made after it in the same step, is not kept either: undone alone, it would
    # put "tail" back under the row that already ends in it.
    env, log = tr.undo_env(t, max_bytes=1000)
    ed = tr.edit(t, "w" * 5000 + "\ntail\n", name="l.txt", asan=True, env=env)
    ed.keys(tr.DOWN, tr.BACKSPACE)
    t.check(ed.message == "undo: change too big to remember" and "1 lines" in ed.status,
            f"joined: {ed.message!r} {ed.status!r}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.message == "Nothing to undo" and "1 lines" in ed.status, f"{ed.message!r} {ed.status!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "w" * 5000 + "tail\n", "the join is in the file")
    ed.quit()

    # Random keys, undone to the end and redone to the end, under AddressSanitizer, with the
    # history counted again after every key (kilo exits with status 4 if the count is wrong,
    # or if a record is applied to a row that is not in the file).
    text = "first line\n\tindented\n\n" + "x" * 100 + "\nlast\n"
    runs = [(1, 24, 80, "p.txt", False, None), (2, 10, 30, "q.txt", True, None),
            (3, 6, 20, "r.txt", False, None), (4, 12, 40, "s.c", True, None),
            (5, 10, 30, "u.txt", True, 2000)]
    for seed, rows, cols, name, with_undo, bound in runs:
        rnd = random.Random(seed)
        keys = ([chr(c) for c in range(ord("a"), ord("z") + 1)] * 2 + [" ", " ", tr.TAB] + [tr.ENTER] * 4
                + [tr.BACKSPACE] * 6 + [tr.DEL] + [tr.UP, tr.DOWN, tr.LEFT, tr.RIGHT] * 3
                + [tr.PAGE_UP, tr.PAGE_DOWN]
                + ([tr.ctrl("z"), tr.ctrl("z") * 3, tr.ctrl("z") * 6, tr.ctrl("r"), tr.ctrl("r") * 2] if with_undo else []))
        typed = [rnd.choice(keys) for _ in range(400)]
        env, log = tr.undo_env(t, max_bytes=bound, name=f"undo{seed}")
        what = f"seed {seed}, {rows}x{cols}, {name}" + (", undo and redo in it" if with_undo else "") \
            + (f", bound {bound}" if bound else "")
        ed = tr.edit(t, text, name=name, rows=rows, cols=cols, asan=True, env=env)
        for i in range(0, len(typed), 50):
            ed.keys("".join(typed[i:i + 50]))
        ed.keys(tr.ctrl("s"))
        done = ed.saved()
        steps = tr.undo_counts(log)[-1]["undo"]
        for i in range(0, steps + 2, 50):
            ed.keys(tr.ctrl("z") * min(50, steps + 2 - i))
        t.check(ed.message == "Nothing to undo", f"{what}: {ed.message!r} after {steps + 2} Ctrl-Z")
        ed.keys(tr.ctrl("s"))
        if bound is None:
            t.check(ed.saved() == text, f"{what}: all undone, saved {ed.saved()[:60]!r}")
        steps = tr.undo_counts(log)[-1]["redo"]
        for i in range(0, steps + 2, 50):
            ed.keys(tr.ctrl("r") * min(50, steps + 2 - i))
        t.check(ed.message == "Nothing to redo", f"{what}: {ed.message!r}")
        ed.keys(tr.ctrl("s"))
        t.check(ed.saved() == done, f"{what}: all redone, saved {ed.saved()[:60]!r}, not {done[:60]!r}")
        if bound:
            # An undo can take the history past the bound by what the step takes in to be
            # redone; with nothing to redo it is always within it.
            t.check(all(c["bytes"] <= bound for c in tr.undo_counts(log) if c["redo"] == 0),
                    f"{what}: over the bound with nothing to redo")
        ed.keys(tr.ctrl("z"))
        t.check(modified(ed) or cols < 40, f"{what}: one undone after the save")   # (narrower: cut)
        ed.keys(tr.ctrl("r"))
        t.check(not modified(ed), f"{what}: redone, at the save")
        ed.quit()
