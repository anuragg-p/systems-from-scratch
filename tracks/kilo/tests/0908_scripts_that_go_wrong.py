"""09.08 Scripts that go wrong

Module 07's standard: never a crash, a hang, or a lost file. A script that
never ends is stopped by Ctrl-C: a count hook looks at the keyboard every
100000 instructions, and raises "interrupted", again at every instruction
until the script is back in the editor, so a pcall() cannot swallow it;
other keys typed meanwhile are dropped. Lua's memory is counted by an
allocator of kilo's and refused past 64 MB ("not enough memory"), and a
full collection follows. Control bytes never reach the terminal. os.exit is
taken away in the editor. Ctrl-Q is never offered to a script. Lua's panic
function puts the terminal back and exits 1 (a test aid reaches it). A
finalizer that never ends at exit runs with the terminal already back, so
Ctrl-C ends it. And thousands of random calls of every API function, in
the editor under AddressSanitizer, change nothing of that.
"""

import importlib.util
import os
import signal
import termios
import time

INIT = r"""
kilo.api.set_keymap('<C-t>', function() while true do end end)
kilo.api.create_autocmd('KeyPress', function(key)
  if key == '<C-l>' then local n = 0 while true do n = n + 1 end end
end)
"""


def fuzz_module():
    spec = importlib.util.spec_from_file_location("api_fuzz", os.path.join(os.path.dirname(__file__), "api_fuzz.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test(t):
    tr = t.track
    ed = tr.edit(t, "safe text\n", init=INIT, asan=True)

    def lua(line):
        ed.keys(tr.ctrl("e"), line, tr.ENTER)
        return ed.message

    def stop(what, said):
        """The script is running (no screen comes); keys typed now are dropped; Ctrl-C stops it."""
        time.sleep(0.4)
        t.check(ed.s.proc.poll() is None, f"{what}: kilo is still there")
        ed.s.send("abc")
        time.sleep(0.2)
        t0 = time.monotonic()
        ed.keys(tr.ctrl("c"))
        took = time.monotonic() - t0
        t.check(ed.message == said, f"{what}: {ed.message!r}, not {said!r}")
        t.check(ed.lines[0] == "safe text", f"{what}: the keys typed meanwhile were dropped: {ed.lines[0]!r}")
        return took

    # A loop on a key, at the prompt, one that catches errors, one in a coroutine, in KeyPress.
    ed.s.send(tr.ctrl("t"))
    took = stop("a mapped key", "init.lua:2: interrupted")
    t.check(took < 1.0, f"stopped {took:.2f}s after Ctrl-C")
    for line, said in (("while true do end", "lua:1: interrupted"),
                       ("while true do pcall(function() while true do end end) end", "lua:1: interrupted"),
                       # coroutine.wrap() puts its own caller's place in front of an error that
                       # passes through it (Lua's lcorolib.c, auxwrap).
                       ("coroutine.wrap(function() while true do end end)()", "lua:1: lua:1: interrupted")):
        ed.keys(tr.ctrl("e"), line)
        ed.s.send(tr.ENTER)
        stop(line, said)
    ed.s.send(tr.ctrl("l"))
    stop("a KeyPress function", "init.lua:4: interrupted")
    # The file is intact, and the editor edits and saves after all of that.
    ed.keys("ok ", tr.ctrl("s"))
    t.check(ed.saved() == "ok safe text\n", f"{ed.saved()!r}")

    # Memory: refused past 64 MB, and given back by the collection that follows.
    t.check(lua("local t = {} for i = 1, 1e9 do t[i] = string.rep('x', 1000) .. i end") == "not enough memory",
            f"{ed.message!r}")
    t.check(float(lua("collectgarbage('count')")) < 1024, f"KB held after it: {ed.message!r}")
    t.check(lua("#string.rep('x', 30 * 2^20)") == "31457280", f"30 MB is room enough: {ed.message!r}")
    t.check(lua("s = string.rep('x', 30 * 2^20) return pcall(string.rep, 'y', 30 * 2^20)") == "false not enough memory",
            f"30 MB held, 30 more is not: {ed.message!r}")
    t.check(lua("s = nil collectgarbage() return #string.rep('y', 30 * 2^20)") == "31457280", f"{ed.message!r}")
    t.check(lua("string.rep('x', 2^30)") == "not enough memory", f"{ed.message!r}")
    # Recursion without end: in Lua, the memory runs out before Lua's own stack limit; through
    # a C function, Lua's limit on C calls.
    t.check(lua("local function f() return 1 + f() end f()") == "not enough memory", f"{ed.message!r}")
    t.check(lua("local function f(s) return (s:gsub('.', f)) end f('ab')") == "C stack overflow" or
            ed.message.endswith("C stack overflow"), f"{ed.message!r}")
    # Every control byte shown as '?', a tab as a space; none reaches the terminal raw.
    lua("kilo.api.message(string.char(" + ", ".join(str(i) for i in range(1, 32)) + ", 127))")
    t.check(ed.message == "????????" + " " + "?" * 23, f"{ed.message!r}")
    # os.exit is taken away in the editor.
    t.check(lua("os.exit(0)") == "lua:1: os.exit is taken away in the editor: kilo.api.quit() leaves", f"{ed.message!r}")
    ed.keys("!", tr.ctrl("s"))
    t.check(ed.saved() == "ok !safe text\n", f"and the editor goes on: {ed.saved()!r}")
    t.check(ed.quit() == 0, "Ctrl-Q quits")

    # Ctrl-Q is never offered to a script: every other key mapped, and a KeyPress function
    # that takes every key, and the user still leaves.
    grab = ("seen = {}\n"
            "for c = 1, 26 do if c ~= 17 then kilo.api.set_keymap('<C-' .. string.char(96 + c) .. '>', function() end) end end\n"
            "for c = 33, 126 do kilo.api.set_keymap(string.char(c), function() end) end\n"
            "kilo.api.create_autocmd('KeyPress', function(k) seen[#seen + 1] = k return true end)\n"
            "kilo.api.create_autocmd('BufWritePre', function() kilo.api.message('saved?') end)\n")
    ed = tr.edit(t, "x\n", init=grab, asan=True)
    t.check(ed.message.startswith("HELP"), f"{ed.message!r}")
    ed.keys("abc", tr.ctrl("s"), tr.ENTER, tr.ctrl("e"))
    t.check(ed.lines[0] == "x" and ed.message.startswith("HELP"), f"every key taken: {ed.lines[0]!r} {ed.message!r}")
    t.check(ed.quit() == 0, "Ctrl-Q still quits")

    # The panic function: the terminal put back, the error said, status 1.
    ed = tr.edit(t, "x\n", asan=True)
    ed.keys(tr.ctrl("e"), "kilo.test_panic()")
    ed.s.send(tr.ENTER)
    rc = ed.s.wait_exit(10)
    ed.pump(0)
    t.check(rc == 1, f"a panic exits 1: {rc}")
    t.check(b"kilo: Lua panic: a panic, on purpose" in ed.raw, f"said: {ed.raw[-200:]!r}")
    t.check(ed.termios()[3] & termios.ECHO, "the terminal is put back")

    # A finalizer that never ends: Lua runs it with its hooks off, so nothing stops it while
    # the editor runs; at exit it runs after the terminal is put back, and Ctrl-C ends kilo.
    ed = tr.edit(t, "x\n", init="keep = setmetatable({}, {__gc = function() while true do end end})")
    ed.s.send(tr.ctrl("q"))
    time.sleep(0.5)
    t.check(ed.s.proc.poll() is None, "kilo hangs in the finalizer")
    t.check(ed.termios()[3] & termios.ISIG, "with the terminal back in its own mode")
    ed.s.send("\x03")
    rc = ed.s.wait_exit(10)
    t.check(rc == -signal.SIGINT, f"Ctrl-C ended it: {rc}")

    # Random calls of every function in the editor, a block of 300 a key, the screen drawn
    # after each, under AddressSanitizer (and UndefinedBehaviorSanitizer where there is one).
    fz = fuzz_module()
    exe = tr.asan_build(t, "address,undefined") or tr.asan_build(t)
    for name, text in (("b.txt", "bee\n"), ("x.txt", "an x\n")):
        with open(os.path.join(t.tmp, name), "w") as f:
            f.write(text)
    seed = int(time.time()) % 100000
    blocks = []
    for b in range(10):
        blocks.append("blocks[%d] = function()\n  %s\nend\n" % (b + 1, "\n  ".join(fz.calls(seed * 100 + b, 300, True))))
    init = ("blocks, done = {}, 0\n"
            "kilo.api.create_autocmd('KeyPress', function(k)\n"
            "  if k ~= '<C-o>' then return false end\n"
            "  done = done + 1\n"
            "  if blocks[done] then blocks[done]() end\n"
            "  return true\n"
            "end)\n" + "".join(blocks))
    with open(os.path.join(t.tmp, "fuzz.lua"), "w") as f:
        f.write(init)
    with open(os.path.join(t.tmp, "f.txt"), "w") as f:
        f.write("".join(f"row {i}\n" for i in range(30)))
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0", UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1",
               KILO_INIT=os.path.join(t.tmp, "fuzz.lua"), KILO_LSP="")
    ed = tr.Editor(t, ["f.txt"], cwd=t.tmp, exe=exe or os.path.join(t.root, "kilo"), env=env, timeout=60)
    for b in range(10):
        try:
            ed.keys(tr.ctrl("o"))
        except Exception as e:
            raise tr.Fail(f"seed {seed}, block {b + 1}: {e}")
    t.check(ed.s.proc.poll() is None, f"seed {seed}: kilo is still there")
    for _ in range(4):
        ed.s.send(tr.ctrl("q"))
        time.sleep(0.1)
    rc = ed.s.wait_exit(20)
    t.check(rc == 0, f"seed {seed}: Ctrl-Q left after the fuzz, status {rc}: {ed.tail()}")
