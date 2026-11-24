"""09.05 Events: autocommands

create_autocmd(event, fn) binds a function to an event, and returns its id
(del_autocmd(id) unbinds it): BufReadPost (a file is in the editor: once
after init.lua for the first, and at the end of each editorOpen()),
BufWritePre (before the text is made into a string to save), BufWritePost
(after a good write), TextChanged and CursorMoved (after a key's work, when
the changed tick, or the cursor's place, is not what it was), KeyPress
(before the mapping and the editor see a key, with its name; a function
that returns true takes it). The functions run in the order they were
made; one that fails is said, and the next runs, and the save goes on.
While an event's functions run, no event fires. A save asked for inside
BufWritePre or BufWritePost is an error. AUTOCMD_MAX is 64.
"""

INIT = r"""
log = {}
function note(s) log[#log + 1] = tostring(s) end
function L() local s = table.concat(log, ' ') log = {} return s end
reads, changed, moved = 0, 0, 0
kilo.api.create_autocmd('BufReadPost', function(ev) reads = reads + 1 note(ev) end)
kilo.api.create_autocmd('TextChanged', function() changed = changed + 1 return true end)
kilo.api.create_autocmd('CursorMoved', function() moved = moved + 1 end)

-- The lesson's two: trailing spaces trimmed before a save; the words counted as you type.
kilo.api.create_autocmd('BufWritePre', function()
  for row, line in kilo.lines() do
    local trimmed = line:gsub('%s+$', '')
    if trimmed ~= line then kilo.api.set_lines(row, row + 1, {trimmed}) end
  end
end)
kilo.api.create_autocmd('TextChanged', function()
  local words = 0
  for _, line in kilo.lines() do
    for _ in line:gmatch('%S+') do words = words + 1 end
  end
  kilo.api.message(words .. ' words')
end)
"""


def test(t):
    tr = t.track
    ed = tr.edit(t, "hello world  \nsecond line\t\n", init=INIT, asan=True)

    def lua(line):
        ed.keys(tr.ctrl("e"), line, tr.ENTER)
        return ed.message

    # BufReadPost: once, after init.lua, for the file named on the command line.
    t.check(lua("reads, L()") == "1 BufReadPost", f"{ed.message!r}")
    # A key that changes the text: TextChanged, once (the word count); one that moves the
    # cursor: CursorMoved; the prompt itself is neither.
    t.check(lua("changed, moved") == "0 0", f"nothing yet: {ed.message!r}")
    ed.keys("a")
    t.check(ed.message == "4 words", f"TextChanged after a key: {ed.message!r}")
    ed.keys(" ")
    t.check(ed.message == "5 words", f"{ed.message!r}")
    ed.keys(tr.DOWN, tr.RIGHT, tr.ctrl("l"))
    t.check(lua("changed, moved") == "2 4", f"2 changes, 4 moves (2 typed, 2 arrows): {ed.message!r}")
    t.check(lua("kilo.api.get_changedtick() - kilo.api.get_changedtick()") == "0", f"{ed.message!r}")
    tick = int(lua("kilo.api.get_changedtick()"))
    ed.keys("xy", tr.ENTER)
    t.check(int(lua("kilo.api.get_changedtick()")) == tick + 4, f"2 characters, a row put in and one cut: {ed.message!r}")
    ed.keys(tr.BACKSPACE, tr.BACKSPACE, tr.BACKSPACE)
    t.check(ed.lines[:2] == ["a hello world", "second line"], f"{ed.lines[:2]}")

    # Around a save: BufWritePre (the trailing spaces go), the write, BufWritePost.
    lua("kilo.api.create_autocmd('BufWritePre', function(ev) note(ev) note(kilo.api.is_modified()) end)")
    lua("kilo.api.create_autocmd('BufWritePost', function(ev) note(ev) note(kilo.api.is_modified()) end)")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "a hello world\nsecond line\n", f"trimmed before the save: {ed.saved()!r}")
    t.check(lua("L()") == "BufWritePre true BufWritePost false", f"{ed.message!r}")
    # A save asked for inside them is an error; feeding Ctrl-S too. The save goes on.
    lua("kilo.api.create_autocmd('BufWritePre', function() note(select(2, pcall(kilo.api.save))) end)")
    lua("kilo.api.create_autocmd('BufWritePost', function() note(select(2, pcall(kilo.api.feed_key, '<C-s>'))) end)")
    lua("kilo.api.set_cursor({1, 0})")
    ed.keys("!", tr.ctrl("s"))
    want = "BufWritePre true save: a save is already going on BufWritePost false feed_key: a save is already going on"
    t.check(lua("L() == " + tr.lua_quote(want)) == "true", f"{want!r} (the message line holds 79 bytes)")
    # A function that fails is said, the next still runs, and the save goes on.
    lua("kilo.api.create_autocmd('BufWritePre', function() error('pre failed') end)")
    lua("kilo.api.create_autocmd('BufWritePost', function() error('post failed') end)")
    lua("kilo.api.create_autocmd('BufWritePost', function() note('after') end)")
    ed.keys("?", tr.ctrl("s"))
    t.check(ed.saved() == "a hello world\n!?second line\n", f"saved all the same: {ed.saved()!r}")
    t.check(ed.message == "lua:1: post failed", f"said: {ed.message!r}")
    t.check(lua("L():sub(-42)") == "feed_key: a save is already going on after", f"{ed.message!r}")

    # No nesting: a TextChanged function's own change is not heard again, and a save it asks
    # for has no BufWritePre.
    pre = "kilo.api.create_autocmd('BufWritePre', function() note('pre') end)"
    lua(pre)
    lua("kilo.api.create_autocmd('TextChanged', function() local n = kilo.api.line_count() "
        "kilo.api.set_lines(n, n, {'.'}) kilo.api.save() end)")
    before = int(lua("changed"))
    ed.keys("z")
    t.check(ed.lines[2:4] == [".", "~"] and lua("changed") == str(before + 1),
            f"one row put in, once: {ed.lines[:4]} {ed.message!r}")
    t.check("pre" not in lua("L()"), f"no BufWritePre inside TextChanged: {ed.message!r}")
    ed.keys(tr.RIGHT, tr.RIGHT)
    t.check(ed.lines[2:4] == [".", "~"], f"moving changes nothing: {ed.lines[:4]}")

    # Errors: an unknown event (names are exact), an unknown id; at most AUTOCMD_MAX.
    for call, said in (("create_autocmd('Nope', print)", 'create_autocmd: unknown event "Nope"'),
                       ("create_autocmd('bufwritepre', print)", 'create_autocmd: unknown event "bufwritepre"'),
                       ("del_autocmd(999)", "del_autocmd: no autocommand 999")):
        t.check(lua(f"kilo.api.{call}") == f"lua:1: {said}", f"{call}: {ed.message!r}")
    n = int(lua("print(kilo.api.create_autocmd('KeyPress', function() end))"))
    t.check(lua(f"kilo.api.del_autocmd({n}) print(kilo.api.create_autocmd('KeyPress', print) - {n})") == "1",
            f"ids are never given twice: {ed.message!r}")
    t.check(lua("for i = 1, 64 do kilo.api.create_autocmd('BufWritePost', print) end") ==
            "lua:1: create_autocmd: too many autocommands (64)", f"{ed.message!r}")
    ed.quit()

    # KeyPress, before mappings and the editor: a vi-like layer, Escape into "normal" keys, j
    # and k move, i gives the keys back to the editor; and it never sees a fed key, nor the
    # keys typed in find or at a prompt.
    vi = r"""
normal, seen = false, {}
kilo.api.create_autocmd('KeyPress', function(key)
  seen[#seen + 1] = key
  if not normal then
    if key == '<Esc>' then normal = true return true end
    return false
  end
  if key == 'j' then kilo.api.feed_key('<Down>') return true end
  if key == 'k' then kilo.api.feed_key('<Up>') return true end
  if key == 'i' then normal = false return true end
  return true
end)
kilo.api.set_keymap('<C-y>', function() seen[#seen + 1] = 'mapped' end)
function S() local s = table.concat(seen, ' ') seen = {} return s end
"""
    ed = tr.edit(t, "one\ntwo\nthree\n", init=vi, asan=True)
    ed.keys(tr.ESC, "j", "j", "x", "k", tr.ctrl("y"))
    t.check(ed.cursor == (1, 0) and ed.lines[:3] == ["one", "two", "three"], f"normal keys: {ed.cursor} {ed.lines[:3]}")
    ed.keys("i", "x", tr.ctrl("y"))
    t.check(ed.lines[1] == "xtwo", f"inserting again: {ed.lines[:3]}")
    ed.keys(tr.ctrl("f"), "thr", tr.ESC)
    t.check(lua("S()") == "<Esc> j j x k <C-y> i x <C-y> mapped <C-f> <C-e>",
            f"what KeyPress saw (not the fed arrows, not find's keys): {ed.message!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.quit() == 0, "Ctrl-Q quits")

    # BufReadPost for a file that is not there yet: it is in the editor all the same.
    ed = tr.edit(t, None, name="new.txt", init="n = 0 kilo.api.create_autocmd('BufReadPost', function() n = n + 1 end)")
    t.check(lua("n") == "1", f"{ed.message!r}")
    # Functions made during an event do not run in it; one deleted during it does not run.
    lua("kilo.api.create_autocmd('TextChanged', function() n = n * 10 "
        "kilo.api.create_autocmd('TextChanged', function() n = n + 1 end) end)")
    ed.keys("q")
    t.check(lua("n") == "10", f"the new one did not run: {ed.message!r}")
    ed.keys("q")
    t.check(lua("n") == "101", f"it runs from the next change: {ed.message!r}")
    ed.keys(tr.ctrl("s"))
    ed.quit()
