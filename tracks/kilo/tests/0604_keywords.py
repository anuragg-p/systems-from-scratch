"""06.04 Keywords

In a C file the syntax's keywords are yellow and its types green: a word
from C_HL_keywords, after a separator and with one after it. A longer word
that starts with one (integer, iffy) is not one, nor is one inside a
string or a comment, or after a character that is no separator (<);
a file kilo has no language for has none.
"""


def test(t):
    tr = t.track
    text = ("int main(void) {\n"
            "\tif (x) return 0; else break;\n"
            "\tunsigned long n = sizeof(n);\n"
            "\tinteger = iffy + intx;\n"
            "\tdecltype(x) y = NULL;\n"
            "\tprintf(\"int\"); // int\n"
            "\tstatic_cast<int>(c)\n"
            "x = s\n")
    ed = tr.edit(t, text, name="t.c", asan=True)
    want = ["[g:int] main([g:void]) {",
            "        [y:if] (x) [y:return] [r:0]; [y:else] [y:break];",
            "        [g:unsigned] [g:long] n = [y:sizeof](n);",
            "        integer = iffy + intx;",
            "        [y:decltype](x) y = [y:NULL];",
            "        printf([m:\"int\"]); [c:// int]",
            "        static_cast<int>(c)",          # < is no separator: no keyword here
            "x = s"]
    for n, w in enumerate(want):
        t.check(ed.painted(n) == w, f"row {n}: {ed.painted(n)!r}, not {w!r}")
    # Typing makes and unmakes a keyword.
    ed.keys(tr.DOWN * 7, tr.RIGHT * 5, "witch")
    t.check(ed.painted(7) == "x = [y:switch]", f"{ed.painted(7)!r}")
    ed.keys("y")
    t.check(ed.painted(7) == "x = switchy", f"{ed.painted(7)!r}")

    ed = tr.edit(t, text, name="t.txt")
    t.check(all(set(ed.colors(n)) <= {"."} for n in range(8)), f"no colours: {ed.painted(0)!r}")
