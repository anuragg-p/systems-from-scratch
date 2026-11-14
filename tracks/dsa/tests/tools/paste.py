"""paste -s: the workbench's small job (module 00). T is track.py."""

from harness.core import Fail

PROGRAMS = {"paste": "00.01"}
FILES_FROM = {
    "tools/paste/paste.c": "00.01",
    "tools/paste/tool.mk": "00.01",
}


def timeline_steps(k):
    return [
        T.sh_step("printf 'a\\nb\\nc\\n' | bin/paste -s -d ' '", "a b c\n"),
        T.sh_step("printf 'a\\nb\\nc\\n' | bin/paste -sd , --algo=strcat", "a,b,c\n"),
        T.sh_step("bin/paste -s --algo=fast < /dev/null", "paste: no --algo 'fast' (have: strcat, end)\n", 2),
    ]


def timeline_after(root, k):
    book = T.data(root, "book.txt")
    for algo in ("strcat", "end"):
        ours = T.run(root, "paste", ["-s", "-d", " ", f"--algo={algo}", book]).out
        theirs = T.system(root, ["paste", "-s", "-d", " ", book]).out
        if ours != theirs:
            raise Fail(f"bin/paste -s --algo={algo} and the system's paste -s differ on data/book.txt")
    return "paste -s: the system's bytes on the book"
