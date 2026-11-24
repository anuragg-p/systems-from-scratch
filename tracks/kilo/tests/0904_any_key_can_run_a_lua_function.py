"""09.04 Any key can run a Lua function

set_keymap(key, fn) takes every key editorReadKey() returns, by name:
"<C-a>" to "<C-z>", "<Enter>", "<Esc>", "<Tab>", "<BS>", "<Del>", the
arrows, "<Home>", "<End>", "<PageUp>", "<PageDown>", "<Space>", a printable
character as itself, "<xNN>" for any other byte; bracketed names in either
case. "<C-q>" is refused: it is the way out. A mapping wins over the
editor's own key, and runs in place of it; it does not apply inside find
or a prompt. The dispatcher keeps a function as a reference in Lua's
registry; mapping a key again, or del_keymap(), lets it go. feed_key(key)
does what the editor itself does for a key, with no mapping consulted.
kilo.keymap.set() and kilo.lines() are Lua, on top of the API. In the
finished project, with module 08: what a key's scripts change is one step of
undo, its own, whatever keys were typed before; Ctrl-Z and Ctrl-R can be a
script's, and feed_key() reaches the editor's.
"""

import os


INIT = r"""
log = {}
function note(s) log[#log + 1] = s end
function L() local s = table.concat(log, ' ') log = {} return s end
function nfun()
  collectgarbage()
  local n = 0
  for _, v in pairs(debug.getregistry()) do
    if type(v) == 'function' then n = n + 1 end
  end
  return n
end

-- The lesson's two: Ctrl-D duplicates the cursor's line, Ctrl-T comments it or not.
kilo.keymap.set('<C-d>', function()
  local row = kilo.api.get_cursor()[1]
  local line = kilo.api.get_lines(row, row + 1)[1]
  kilo.api.set_lines(row + 1, row + 1, {line})
end)
kilo.keymap.set('<c-T>', function()
  local row = kilo.api.get_cursor()[1]
  local line = kilo.api.get_lines(row, row + 1)[1]
  if line:sub(1, 3) == '-- ' then line = line:sub(4) else line = '-- ' .. line end
  kilo.api.set_lines(row, row + 1, {line})
end)
"""

NAMED = [("<Enter>", "\r"), ("<Esc>", "\x1b"), ("<Tab>", "\t"), ("<BS>", "\x7f"), ("<Space>", " "),
         ("<Del>", "\x1b[3~"), ("<Up>", "\x1b[A"), ("<Down>", "\x1b[B"), ("<Left>", "\x1b[D"),
         ("<Right>", "\x1b[C"), ("<Home>", "\x1b[H"), ("<End>", "\x1b[F"), ("<PageUp>", "\x1b[5~"),
         ("<PageDown>", "\x1b[6~"), ("x", "x"), ("<", "<"), ("<C-a>", "\x01"), ("<xe9>", b"\xe9"),
         ("<x1c>", "\x1c")]


def test(t):
    tr = t.track
    names = ", ".join(tr.lua_quote(n) for n, _ in NAMED)
    init = INIT + (f"NAMES = {{{names}}}\n"
                   "function mapall() for _, k in ipairs(NAMES) do kilo.api.set_keymap(k, function() note(k) end) end end\n"
                   "function unmapall() for _, k in ipairs(NAMES) do kilo.api.del_keymap(k) end end\n")
    ed = tr.edit(t, "one\ntwo\n-- three\n", init=init, asan=True)

    def lua(line):
        ed.keys(tr.ctrl("e"), line, tr.ENTER)
        return ed.message

    # The lesson's two mappings.
    ed.keys(tr.ctrl("d"))
    t.check(ed.lines[:4] == ["one", "one", "two", "-- three"], f"Ctrl-D: {ed.lines[:4]}")
    ed.keys(tr.DOWN, tr.DOWN, tr.ctrl("t"))
    t.check(ed.lines[2] == "-- two" and ed.cursor == (2, 0), f"Ctrl-T: {ed.lines[:4]} {ed.cursor}")
    ed.keys(tr.DOWN, tr.ctrl("t"))
    t.check(ed.lines[3] == "three", f"Ctrl-T again: {ed.lines[:4]}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.saved() == "one\none\n-- two\nthree\n", f"{ed.saved()!r}")

    # Every kind of key, by name; each runs its function and nothing else happens.
    lua("mapall()")
    for _, key in NAMED:
        ed.keys(key)
    t.check(lua("L() == " + tr.lua_quote(" ".join(n for n, _ in NAMED))) == "true", f"the keys ran: {ed.message!r}")
    t.check(ed.lines[:4] == ["one", "one", "-- two", "three"] and ed.cursor == (3, 0) and "(modified)" not in ed.status,
            f"and nothing else happened: {ed.lines[:4]} {ed.cursor} {ed.status!r}")
    lua("unmapall()")
    # Either case; Ctrl-M is Enter's byte and Ctrl-I Tab's, so they are the same keys. Ctrl-H
    # is byte 8: Backspace sends 127 here, and stays the editor's.
    lua("kilo.api.set_keymap('<c-M>', function() note('m') end) kilo.api.set_keymap('<C-I>', function() note('i') end)")
    lua("kilo.api.set_keymap('<ENTER>', function() note('enter') end) kilo.api.set_keymap('<c-h>', function() note('h') end)")
    ed.keys("\r", "\t", tr.ctrl("h"))
    t.check(lua("L()") == "enter i h", f"{ed.message!r}")
    for k in ("<Enter>", "<Tab>", "<C-h>"):
        lua(f"kilo.api.del_keymap('{k}')")
    ed.keys(*[tr.RIGHT] * 5, tr.BACKSPACE)
    t.check(ed.lines[3] == "thre", f"Backspace is the editor's: {ed.lines[3]!r}")

    # Refused: Ctrl-Q, in any case, and names that are no key's.
    for name, said in (("<C-q>", "<C-q> is the way out: no script can have it"),
                       ("<c-Q>", "<C-q> is the way out: no script can have it"),
                       ("<F1>", 'unknown key "<F1>"'), ("", 'unknown key ""'), ("ab", 'unknown key "ab"'),
                       ("<C-1>", 'unknown key "<C-1>"'), ("<x4g>", 'unknown key "<x4g>"'),
                       (" ", 'unknown key " "')):
        t.check(lua(f"kilo.api.set_keymap('{name}', print)") == f"lua:1: set_keymap: {said}",
                f"set_keymap({name!r}): {ed.message!r}")
    t.check(lua("kilo.api.del_keymap('<C-y>')") == "lua:1: del_keymap: <C-y> is not mapped", f"{ed.message!r}")
    t.check(lua("kilo.api.feed_key('<C-q>')") == "lua:1: feed_key: <C-q> is the way out: no script can have it",
            f"{ed.message!r}")
    t.check(lua("kilo.api.feed_key('<F1>')") == 'lua:1: feed_key: unknown key "<F1>"', f"{ed.message!r}")

    # Given back: after del_keymap, x types an x again.
    lua("kilo.api.set_keymap('x', function() note('x') end)")
    ed.keys("x")
    lua("kilo.api.del_keymap('x')")
    ed.keys("x")
    t.check(lua("L()") == "x", f"{ed.message!r}")
    t.check(ed.lines[3] == "threx", f"{ed.lines[3]!r}")
    # A mapping replaced: only the newest runs. One that replaces itself while it runs.
    lua("kilo.api.set_keymap('<C-y>', function() note(1) end)")
    lua("kilo.api.set_keymap('<C-y>', function() note(2) end)")
    lua("kilo.api.set_keymap('<C-k>', function() kilo.api.set_keymap('<C-k>', function() note('second') end) note('first') end)")
    ed.keys(tr.ctrl("y"), tr.ctrl("k"), tr.ctrl("k"))
    t.check(lua("L()") == "2 first second", f"{ed.message!r}")
    lua("kilo.api.set_keymap('<C-k>', function() kilo.api.del_keymap('<C-k>') note('gone') end)")
    ed.keys(tr.ctrl("k"))
    t.check(lua("L()") == "gone", f"a mapping that deletes itself: {ed.message!r}")
    t.check(lua("kilo.api.del_keymap('<C-k>')") == "lua:1: del_keymap: <C-k> is not mapped", f"{ed.message!r}")

    # The references are let go: 2000 mappings of one key leave the registry's count of
    # functions as it was; del_keymap takes one off.
    t.check(lua("before = nfun() for i = 1, 2000 do kilo.api.set_keymap('<C-y>', function() return i end) end "
                "print(nfun() - before)") == "0", f"mapping again lets the old one go: {ed.message!r}")
    t.check(lua("before = nfun() kilo.api.del_keymap('<C-y>') print(nfun() - before)") == "-1",
            f"del_keymap lets it go: {ed.message!r}")
    # A refused mapping keeps nothing either.
    t.check(lua("before = nfun() pcall(kilo.api.set_keymap, '<C-q>', function() end) print(nfun() - before)") == "0",
            f"{ed.message!r}")

    # A mapping wins over the editor's own key; feed_key() still reaches the editor's.
    lua("kilo.api.set_keymap('<C-s>', function() note('mine') kilo.api.feed_key('<C-s>') end)")
    ed.keys("!", tr.ctrl("s"))
    t.check(ed.saved() == "one\none\n-- two\nthrex!\n" and ed.message == "22 bytes written on disk",
            f"Ctrl-S mapped, then fed: {ed.saved()!r} {ed.message!r}")
    t.check(lua("L()") == "mine", f"{ed.message!r}")
    # A key whose function feeds the key itself: the editor's action, not the function again.
    lua("kilo.api.set_keymap('z', function() kilo.api.feed_key('z') kilo.api.feed_key('z') end)")
    ed.keys("z")
    t.check(ed.lines[3] == "threx!zz", f"z fed twice: {ed.lines[3]!r}")
    lua("kilo.api.feed_key('<Enter>') kilo.api.feed_key('<Left>')")
    t.check(ed.lines[3:5] == ["threx!zz", ""] and ed.lines[4] == "" and ed.cursor == (3, 8),
            f"fed keys move and edit: {ed.lines[3:6]} {ed.cursor}")

    # Mappings do not apply in find, or at the prompt: there the key is typed.
    lua("kilo.api.set_keymap('a', function() note('a') end)")
    ed.keys(tr.ctrl("f"), "a")
    t.check(ed.message == "Search: a (Use ESC/Arrows/Enter)", f"in find: {ed.message!r}")
    ed.keys(tr.ESC)
    t.check(lua("'a' .. L()") == "a", f"at the prompt, and the function never ran: {ed.message!r}")

    # The Lua on top: kilo.keymap.set with a list of keys; kilo.lines() from row 0.
    lua("kilo.keymap.set({'<C-o>', '<C-p>'}, function() note('o or p') end)")
    ed.keys(tr.ctrl("o"), tr.ctrl("p"))
    t.check(lua("L()") == "o or p o or p", f"{ed.message!r}")
    t.check(lua("for r, l in kilo.lines() do note(r .. '=' .. l) end return L()") ==
            "0=one 1=one 2=-- two 3=threx!zz 4=", f"kilo.lines(): {ed.message!r}")
    ed.keys(tr.ctrl("s"))
    t.check(ed.quit() == 0, "Ctrl-Q quits")

    # With module 08 (the finished project): set_lines undone by one Ctrl-Z and done again by
    # Ctrl-R, the cursor where 08's step puts it (before the step; after it); a script's step
    # not glued to the typing before it, nor the typing after it to the script's; several
    # changes one step; a row deleted and then the row now in its place changed, in one step;
    # Ctrl-Z mapped and Ctrl-R taken by KeyPress, feed_key() reaching the editor's. Module
    # 08's own check of its history runs after every key (KILO_TEST_UNDO_LOG).
    if "undoSave" not in open(os.path.join(t.root, "kilo.c"), errors="replace").read():
        return
    undo = (INIT + r"""
kilo.api.set_keymap('<C-y>', function() kilo.api.set_lines(0, 0, {'header'}) end)
kilo.api.set_keymap('x', function() kilo.api.set_lines(0, 0, {'by x'}) end)
kilo.api.set_keymap('<C-k>', function()
  kilo.api.set_lines(0, 1, {'A'})
  kilo.api.set_lines(2, 3, {'C'})
  kilo.api.set_cursor({1, 0})
  kilo.api.feed_key('B')
  kilo.api.feed_key('<Enter>')
end)
kilo.api.set_keymap('<C-o>', function()
  kilo.api.set_lines(1, 2, {})
  kilo.api.set_cursor({1, 0})
  kilo.api.feed_key('Z')
end)
kilo.api.set_keymap('<C-z>', function() note('undo') kilo.api.feed_key('<C-z>') end)
kilo.api.create_autocmd('KeyPress', function(k)
  if k == '<C-r>' then note('redo') kilo.api.feed_key('<C-r>') return true end
end)
""")
    log = os.path.join(t.tmp, "undo.log")
    ed = tr.edit(t, "one\ntwo\nthree\n", name="u.txt", init=undo, asan=True,
                 env=dict(os.environ, KILO_TEST_UNDO_LOG=log))
    base = ["one", "two", "three"]
    ed.keys(tr.DOWN, tr.RIGHT, tr.RIGHT, tr.ctrl("y"))
    t.check(ed.lines[:4] == ["header"] + base and ed.cursor == (2, 2), f"{ed.lines[:4]} {ed.cursor}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[:4] == base + ["~"] and ed.cursor == (1, 2), f"one Ctrl-Z: {ed.lines[:4]} {ed.cursor}")
    ed.keys(tr.ctrl("r"))
    t.check(ed.lines[:4] == ["header"] + base and ed.cursor == (2, 2), f"Ctrl-R: {ed.lines[:4]} {ed.cursor}")
    t.check(lua("L()") == "undo redo", f"both were the scripts': {ed.message!r}")
    ed.keys(tr.ctrl("z"))
    # Typing, then a typed key a script takes, then typing: three steps.
    ed.keys("ab", "x", "cd")
    t.check(ed.lines[:4] == ["by x", "one", "twabcdo", "three"], f"{ed.lines[:4]}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[:4] == ["by x", "one", "twabo", "three"], f"the typing after the script: {ed.lines[:4]}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[:4] == ["one", "twabo", "three", "~"], f"the script's step alone: {ed.lines[:4]}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[:4] == base + ["~"], f"then the typing before it: {ed.lines[:4]}")
    # Several changes, fed keys among them: one step.
    ed.keys(tr.ctrl("k"))
    t.check(ed.lines[:5] == ["A", "B", "two", "C", "~"], f"{ed.lines[:5]}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[:4] == base + ["~"], f"one Ctrl-Z for all of them: {ed.lines[:4]}")
    # A row deleted, then the row now at its index changed (a U_DEL, then a U_CHG of the same
    # row: a path 08's own keys never take).
    ed.keys(tr.ctrl("o"))
    t.check(ed.lines[:3] == ["one", "Zthree", "~"], f"{ed.lines[:3]}")
    ed.keys(tr.ctrl("z"))
    t.check(ed.lines[:4] == base + ["~"], f"undone: {ed.lines[:4]}")
    ed.keys(tr.ctrl("r"))
    t.check(ed.lines[:3] == ["one", "Zthree", "~"], f"redone: {ed.lines[:3]}")
    ed.keys(tr.ctrl("z"), tr.ctrl("s"))
    t.check(ed.saved() == "one\ntwo\nthree\n", f"{ed.saved()!r}")
    t.check(ed.quit() == 0, "Ctrl-Q quits")
    with open(log) as f:
        t.check(len(f.read().splitlines()) > 5, "module 08 checked its history after the keys")
