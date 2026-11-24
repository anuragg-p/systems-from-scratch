"""09.09 The editor without its screen

`kilo -l script.lua [file]` runs the editor with no raw mode, no screen and
no keys: the file is read if one is named, the script runs with the same
kilo.api, and kilo exits, 0, or 1 with the error on standard error.
print() and message() write a line to standard output; nothing is saved
unless the script calls save(); init.lua is not run; os.exit stays. The
API functions do not know which way they were called: the same Lua does
the same in the editor. What needs the keyboard (input(), feeding Ctrl-E
or Ctrl-F) is an error. Random calls of every function, under
AddressSanitizer (and a leak check where the platform has one), change
nothing of that.
"""

import importlib.util
import os
import subprocess
import sys
import time

UPPER = r"""
-- upper.lua: every line in capitals, and saved.
local n = 0
for row, line in kilo.lines() do
  local up = line:upper()
  if up ~= line then
    kilo.api.set_lines(row, row + 1, {up})
    n = n + 1
  end
end
kilo.api.save()
print(n .. ' lines upper-cased')
"""

TRIM = r"""
-- trim.lua: the same function for kilo -l and for the editor.
function trim()
  for row, line in kilo.lines() do
    local t = line:gsub('%s+$', '')
    if t ~= line then kilo.api.set_lines(row, row + 1, {t}) end
  end
end
"""


def test(t):
    tr = t.track
    kilo = os.path.join(t.root, "kilo")

    r = tr.run_script(t, UPPER, "hello\nWorld\n123\n", script="upper.lua")
    t.check((r.returncode, r.stdout, r.stderr) == (0, "2 lines upper-cased\n", ""), f"{r}")
    with open(os.path.join(t.tmp, "f.txt")) as f:
        t.check(f.read() == "HELLO\nWORLD\n123\n", "saved")

    # No file: none to read, none to save to; the error on standard error, status 1.
    r = tr.run_script(t, "print(kilo.api.line_count(), kilo.api.get_name())\nkilo.api.save()\nprint('not here')\n")
    t.check((r.returncode, r.stdout, r.stderr) == (1, "0\t\n", "script.lua:2: save: no file name\n"), f"{r}")
    # print() and message() write lines as they are; nothing is saved unless save() is called.
    r = tr.run_script(t, "print('a\\27b', 2) kilo.api.message('m\\0n') kilo.api.set_lines(0, 1, {'changed'})",
                      "x\ny\n", name="g.txt")
    t.check((r.returncode, r.stdout) == (0, "a\x1bb\t2\nm\0n\n"), f"{r}")
    with open(os.path.join(t.tmp, "g.txt")) as f:
        t.check(f.read() == "x\ny\n", "nothing saved without save()")
    # A file named that is not there: a new one, made by save().
    r = tr.run_script(t, "kilo.api.set_lines(0, 0, {'new'}) print(kilo.api.save())", "", name="h.txt")
    t.check(r.stdout == "true\n" and open(os.path.join(t.tmp, "h.txt")).read() == "new\n", f"{r}")

    # init.lua is not run; os.exit stays, and its status is kilo's.
    marker = os.path.join(t.tmp, "init-ran")
    with open(os.path.join(t.tmp, "init.lua"), "w") as f:
        f.write(f"io.open('{marker}', 'w'):close()\n")
    r = tr.run_script(t, "os.exit(3)", "x\n", env=dict(os.environ, KILO_INIT=os.path.join(t.tmp, "init.lua")))
    t.check(r.returncode == 3 and not os.path.exists(marker), f"os.exit(3), no init.lua: {r.returncode}")

    # Errors: one that does not compile, one at run time, a script that is not there.
    for lua, said in (("local x = = 1", "script.lua:1: unexpected symbol near '='"),
                      ("\nerror('stop')", "script.lua:2: stop"),
                      ("error({})", "(error object is a table value)")):
        r = tr.run_script(t, lua, "x\n")
        t.check((r.returncode, r.stdout, r.stderr) == (1, "", said + "\n"), f"{lua!r}: {r}")
    r = subprocess.run([kilo, "-l", "nope.lua"], cwd=t.tmp, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=20)
    t.check((r.returncode, r.stderr) == (1, "cannot open nope.lua: No such file or directory\n"), f"{r}")
    # The usage: its first line the core's, a line for each other way.
    for args in ([], ["-l", "a.lua", "b", "c"], ["a", "b"]):
        r = subprocess.run([kilo] + args, cwd=t.tmp, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=20)
        t.check(r.returncode == 1 and r.stderr == "Usage: kilo <filename>\n       kilo --api-info\n"
                "       kilo -l <script.lua> [filename]\n", f"{args}: {r}")

    # What needs the keyboard is an error; keys that do not are fed to a 24 x 80 editor.
    r = tr.run_script(t, "print(pcall(kilo.api.input, 'x'))\n"
                         "print(pcall(kilo.api.feed_key, '<C-f>'))\n"
                         "print(pcall(kilo.api.feed_key, '<C-e>'))\n"
                         "print(table.concat(kilo.api.get_size(), ','))\n"
                         "for _, k in ipairs({'<PageDown>', '<PageDown>', '<PageUp>', 'x', '<Enter>', 'y', '<BS>', '<BS>'}) do\n"
                         "  kilo.api.feed_key(k)\n"
                         "end\n"
                         "print(kilo.api.get_lines(0, 1)[1], table.concat(kilo.api.get_cursor(), ','))\n"
                         "assert(kilo.api.get_lines(7, 8)[1] == 'xline 8')\n",
                      tr.lines_of(50))
    # Page Down twice, Page Up (to row 7), then x, Enter, y and two Backspaces: row 7 is
    # "xline 8" and the cursor after its x, as on a 24 x 80 terminal.
    want = ["false\tinput: no keyboard", "false\tfeed_key: <C-f> waits for the keyboard, and there is none",
            "false\tfeed_key: <C-e> waits for the keyboard, and there is none", "22,80", "line 1\t7,1", ""]
    t.check(r.returncode == 0 and r.stdout.split("\n") == want, f"{r}")
    # A function that fails in an event is said on standard error, and the script goes on.
    r = tr.run_script(t, "kilo.api.create_autocmd('BufWritePre', function() error('pre failed') end)\n"
                         "kilo.api.set_lines(0, 0, {'a'}) print(kilo.api.save())\n", "b\n")
    t.check((r.returncode, r.stdout, r.stderr) == (0, "true\n", "script.lua:1: pre failed\n"), f"{r}")
    # quit(): false refuses unsaved changes; true is kept for when the script has returned.
    r = tr.run_script(t, "kilo.api.quit(true) print('still here')", "x\n")
    t.check((r.returncode, r.stdout) == (0, "still here\n"), f"{r}")
    r = tr.run_script(t, "kilo.api.set_lines(0, 0, {'a'}) kilo.api.quit(false)", "x\n")
    t.check((r.returncode, r.stderr) == (1, "script.lua:1: quit: unsaved changes (quit(true) leaves anyway)\n"), f"{r}")

    # The same Lua in both: trim() with no screen, and on a key in the editor.
    with open(os.path.join(t.tmp, "trim.lua"), "w") as f:
        f.write(TRIM)
    r = tr.run_script(t, "dofile('trim.lua') trim() kilo.api.save()", "a  \nb\t\n c \n", name="t1.txt")
    ed = tr.edit(t, "a  \nb\t\n c \n", name="t2.txt", init="dofile('trim.lua') kilo.api.set_keymap('<C-t>', trim)")
    ed.keys(tr.ctrl("t"), tr.ctrl("s"))
    ed.quit()
    with open(os.path.join(t.tmp, "t1.txt")) as f1, open(os.path.join(t.tmp, "t2.txt")) as f2:
        a, b = f1.read(), f2.read()
    t.check(a == b == "a\nb\n c\n", f"the same: {a!r} {b!r}")

    # Random calls of every function, input() and quit() too, with no screen.
    spec = importlib.util.spec_from_file_location("api_fuzz", os.path.join(os.path.dirname(__file__), "api_fuzz.py"))
    fz = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fz)
    exe = tr.asan_build(t, "address,undefined") or tr.asan_build(t)
    leaks = sys.platform.startswith("linux")
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=%d" % leaks, UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    for name, text in (("b.txt", "bee\n"), ("x.txt", "an x\n")):
        with open(os.path.join(t.tmp, name), "w") as f:
            f.write(text)
    seed = int(time.time()) % 100000
    for run in range(3):
        lua = "\n".join(fz.calls(seed * 10 + run, 2000, False)) + "\nprint('done')\n"
        r = tr.run_script(t, lua, "".join(f"row {i}\n" for i in range(30)), script="fuzz.lua", exe=exe, env=env,
                          timeout=300)
        t.check(r.returncode == 0 and r.stdout.endswith("done\n") and "Sanitizer" not in r.stderr,
                f"seed {seed * 10 + run}: status {r.returncode}, {r.stdout[-200:]!r} {r.stderr[-1500:]!r}")
