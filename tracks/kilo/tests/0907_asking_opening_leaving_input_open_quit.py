"""09.07 Asking, opening, leaving: input(), open(), quit()

input(prompt) asks for a line at the prompt Ctrl-E uses, and returns it,
or nil for Escape. open(path) edits another file in place of this one: not
with unsaved changes, not during a save's events, and a file that is there
but cannot be read is an error (not an exit); a path with no file is a new,
empty one; BufReadPost fires (and, inside BufReadPost, does not fire
again). quit(force) leaves, refusing unsaved changes unless force; kilo
exits only once the script has returned to the editor, never from inside
Lua.
"""

import os
import termios

# The 09.10 proof, cut down: go to a line, asked for on a key.
GOTO = r"""
kilo.api.set_keymap('<C-o>', function()
  local s = kilo.api.input('Go to line: ')
  local n = tonumber(s or '')
  if n and n >= 1 and n <= kilo.api.line_count() then
    kilo.api.set_cursor({math.floor(n) - 1, 0})
  elseif s then
    kilo.api.message('no line ' .. s)
  end
end)
reads = 0
kilo.api.create_autocmd('BufReadPost', function() reads = reads + 1 end)
"""


def test(t):
    tr = t.track
    for name, text in (("b.txt", "bee\n"), ("c.txt", "sea\n"), ("x.txt", "a file\n")):
        with open(os.path.join(t.tmp, name), "w") as f:
            f.write(text)
    ed = tr.edit(t, tr.lines_of(40), init=GOTO, asan=True)

    def lua(line):
        ed.keys(tr.ctrl("e"), line, tr.ENTER)
        return ed.message

    # input(): the line typed, or nil for Escape; the prompt cleaned for the terminal.
    ed.keys(tr.ctrl("e"), "kilo.api.message(kilo.api.input('Name? '))", tr.ENTER)
    t.check(ed.said("Name? ") and ed.message == "Name?", f"the prompt: {ed.message!r}")
    ed.keys("kilo", tr.BACKSPACE, "O", tr.ENTER)
    t.check(ed.message == "kilO", f"{ed.message!r}")
    ed.keys(tr.ctrl("e"), "print(kilo.api.input('x\\27[2J ') == nil)", tr.ENTER)
    t.check(ed.message == "x?[2J", f"{ed.message!r}")
    ed.keys("typed", tr.ESC)
    t.check(ed.message == "true" and b"\x1b[2J" not in ed.raw, f"Escape: nil: {ed.message!r}")
    # Go to a line, on a key.
    ed.keys(tr.ctrl("o"), "30", tr.ENTER)
    t.check(ed.cursor == (21, 0) and ed.status.endswith("30/40"), f"{ed.cursor} {ed.status!r}")
    ed.keys(tr.ctrl("o"), "99", tr.ENTER)
    t.check(ed.message == "no line 99" and ed.status.endswith("30/40"), f"{ed.message!r}")
    ed.keys(tr.ctrl("o"), "7", tr.ESC)
    t.check(ed.status.endswith("30/40"), f"Escape goes nowhere: {ed.status!r}")

    # open(): unsaved changes first; then another file, BufReadPost and all.
    ed.keys("!")
    t.check(lua("kilo.api.open('b.txt')") == "lua:1: open: unsaved changes" and ed.lines[21] == "!line 30",
            f"{ed.message!r} {ed.lines[21]!r}")
    ed.keys(tr.ctrl("s"))
    t.check(lua("kilo.api.open('b.txt') return reads") == "2", f"BufReadPost again: {ed.message!r}")
    t.check(ed.lines[:2] == ["bee", "~"] and ed.status.startswith("b.txt - 1 lines") and ed.cursor == (0, 0),
            f"{ed.lines[:2]} {ed.status!r} {ed.cursor}")
    for path, said in (("x.txt/y", "cannot read x.txt/y: Not a directory"), ("", '"" is not a file name'),
                       ("c\\0.txt", '"c" is not a file name')):
        t.check(lua(f"kilo.api.open('{path}')") == f"lua:1: open: {said}", f"open({path!r}): {ed.message!r}")
    t.check(ed.status.startswith("b.txt"), f"still b.txt: {ed.status!r}")
    # A path with no file there: a new, empty file of that name, as on the command line.
    lua("kilo.api.open('new.txt')")
    t.check(ed.status.startswith("new.txt - 0 lines") and lua("reads") == "3", f"{ed.status!r} {ed.message!r}")
    ed.keys("fresh", tr.ctrl("s"))
    with open(os.path.join(t.tmp, "new.txt")) as f:
        t.check(f.read() == "fresh\n", "saved to the new name")
    # open() inside BufReadPost: the file it opens has no BufReadPost of its own (no nesting).
    lua("kilo.api.create_autocmd('BufReadPost', function() if not done then done = true kilo.api.open('c.txt') end end)")
    t.check(lua("kilo.api.open('b.txt') return reads") == "4" and ed.lines[0] == "sea" and ed.status.startswith("c.txt"),
            f"{ed.message!r} {ed.lines[0]!r} {ed.status!r}")
    # input() inside an event; open() inside a save's is refused.
    lua("kilo.api.create_autocmd('BufWritePre', function() "
        "kilo.api.set_lines(0, 0, {kilo.api.input('Note: ') or '-'}) "
        "note = select(2, pcall(kilo.api.open, 'b.txt')) end)")
    ed.keys("+", tr.ctrl("s"))
    t.check(ed.said("Note: "), f"asked during the save: {ed.message!r}")
    ed.keys("first", tr.ENTER)
    with open(os.path.join(t.tmp, "c.txt")) as f:
        t.check(f.read() == "first\n+sea\n", "the answer went into the file before it was written")
    t.check(lua("note") == "open: a save is going on", f"{ed.message!r}")

    # quit(false) with unsaved changes is refused; quit(true) leaves, once the script is done
    # (what follows the call in it still runs), with nothing saved.
    ed.keys("?")
    t.check(lua("kilo.api.quit(false)") == "lua:1: quit: unsaved changes (quit(true) leaves anyway)", f"{ed.message!r}")
    after = os.path.join(t.tmp, "after.txt")
    ed.keys(tr.ctrl("e"), f"kilo.api.quit(true) io.open('{after}', 'w'):write('ran'):close()")
    ed.s.send(tr.ENTER)
    t.check(ed.s.wait_exit(10) == 0, "quit(true) exits 0")
    t.check(open(after).read() == "ran", "the rest of the script ran before kilo left")
    with open(os.path.join(t.tmp, "c.txt")) as f:
        t.check(f.read() == "first\n+sea\n", "nothing saved")
    t.check(ed.termios()[3] & termios.ECHO, "the terminal is put back")

    # quit(false) with nothing unsaved leaves; quit() inside BufWritePre: the save first.
    ed = tr.edit(t, "x\n", name="q.txt", init="kilo.api.create_autocmd('BufWritePre', function() kilo.api.quit(true) end)",
                 asan=True)
    ed.keys("y")
    ed.s.send(tr.ctrl("s"))
    t.check(ed.s.wait_exit(10) == 0 and ed.saved() == "yx\n", f"saved, then left: {ed.saved()!r}")
    ed = tr.edit(t, "x\n", name="q.txt", asan=True)
    ed.keys(tr.ctrl("e"), "kilo.api.quit(false)")
    ed.s.send(tr.ENTER)
    t.check(ed.s.wait_exit(10) == 0, "quit(false) with nothing unsaved")
