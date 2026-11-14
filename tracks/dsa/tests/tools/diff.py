"""diff and patch: comparing two files, and applying the difference (module 06). T is track.py.

    parse(text)         the hunks of a unified diff (bytes): [Hunk], each with a, na, b, nb from its
                        header and lines [(op, bytes)], a line's newline gone where "\\ No newline
                        at end of file" follows it. Header lines are skipped; a hunk is read by its
                        counts, so a line "--- x" inside one is a deleted "-- x".
    changes(text)       (deleted, inserted): the - and + lines of a unified diff
    lines(data)         the lines of bytes, each with its newline
    system_diff(t, a, b, args=("-u",))
                        the machine's diff -d, the fewest changes: without it, GNU's diff takes
                        shortcuts (119 + 119 changed lines where 93 + 93 do, on unrelated 120), and
                        Apple's writes "@@ -1,0 +1 @@" with -U0 for a line put before line 1, which
                        its own patch then puts after line 1. Its rc must be 0 or 1.
    reference_patch(diff, old, context=None)
                        apply a unified diff (bytes) to old (bytes) strictly: every hunk exactly at
                        its header's line on both sides, in order. Raises Fail, saying why, or
                        returns the new bytes. With context, also that each hunk has the context
                        diff -U context gives it: min(context, lines there) around each change,
                        and no two changes more than 2 x context unchanged lines apart in a hunk,
                        nor 2 x context or fewer apart in two.
    apply_system(t, diff, old_path)
                        the machine's patch (BSD or GNU) run on a copy of old_path with diff
                        (bytes): the bytes it made. Where there is no patch (Debian has none by
                        default), reference_patch.
    cases(t)            name -> (path_a, path_b): the pairs every test runs on, small ones made
                        by hand (empty files, no newline at the end, one line, CRLF, lines that
                        look like headers) and generated ones (versions, revised, unrelated)
    unique_cases(t)     name -> (path_a, path_b): pairs whose longest common subsequence is the
                        only one (numbered lines; new lines are new), so any minimal diff has the
                        same hunks: ours must print the system's bytes
    check(t, a, b, args=(), algo=None)
                        bin/diff [--algo=algo] args a b held to the system's: the same exit
                        status, the same numbers of lines deleted and inserted, headers naming the
                        files, hunks that are right about both files (reference_patch), and the
                        system's patch makes b of a with it. Returns ours, run with DS_STATS=1.
    same_text(t, ours, theirs, what)
                        two unified diffs (bytes) the same but for their header lines, whose times
                        BSD and GNU write differently ("2026-11-14 10:20:30" against GNU's and
                        ours, "2026-11-14 10:20:30.123456789 +0100")
"""

import os
import re
import shutil

from harness.core import Fail

PROGRAMS = {"diff": "06.01", "patch": "06.04"}
FILES_FROM = {"tools/diff/tool.mk": "06.01", "tools/diff/gen.py": "06.01", "lib/diff.h": "06.01",
              "tools/diff/diff.c": "06.01", "tools/patch/tool.mk": "06.04"}
HIDDEN = ["tools/diff/NOTES.md", "tools/diff/NOTICE.txt"]

HUNK = re.compile(rb"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
HEADER = re.compile(r"^(---|\+\+\+) (.*)\t\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{9} [+-]\d{4}$")


def lines(data):
    return re.findall(rb"[^\n]*\n|[^\n]+$", data)


class Hunk:
    def __init__(self, a, na, b, nb, header):
        self.a, self.na, self.b, self.nb, self.header = a, na, b, nb, header
        self.lines = []

    def __repr__(self):
        return self.header.decode("utf-8", "replace")


def parse(text):
    ls = lines(text)
    hunks, i = [], 0
    while i < len(ls):
        m = HUNK.match(ls[i])
        if not m:
            i += 1
            continue
        h = Hunk(int(m.group(1)), int(m.group(2) or 1), int(m.group(3)), int(m.group(4) or 1), ls[i].rstrip(b"\n"))
        i += 1
        old = new = 0
        while old < h.na or new < h.nb:
            if i == len(ls):
                raise Fail(f"hunk {h} ends early: {old} of {h.na} old lines, {new} of {h.nb} new")
            l = ls[i]
            i += 1
            if l.startswith(b"\\"):
                op, body = h.lines[-1]
                h.lines[-1] = (op, body[:-1] if body.endswith(b"\n") else body)
                continue
            op = l[:1]
            if op not in (b" ", b"-", b"+"):
                raise Fail(f"hunk {h}: a line that is not ' ', '-' or '+': {l!r}")
            h.lines.append((op, l[1:]))
            old += op != b"+"
            new += op != b"-"
        if i < len(ls) and ls[i].startswith(b"\\"):
            op, body = h.lines[-1]
            h.lines[-1] = (op, body[:-1] if body.endswith(b"\n") else body)
            i += 1
        if old != h.na or new != h.nb:
            raise Fail(f"hunk {h} has {old} old lines and {new} new")
        hunks.append(h)
    return hunks


def changes(text):
    hunks = parse(text)
    return (sum(1 for h in hunks for op, _ in h.lines if op == b"-"),
            sum(1 for h in hunks for op, _ in h.lines if op == b"+"))


def reference_patch(diff, old, context=None):
    src = lines(old)
    out, pos = [], 0
    hunks = parse(diff)
    for k, h in enumerate(hunks):
        start = h.a - 1 if h.na else h.a
        if start < pos:
            raise Fail(f"hunk {h} starts before the hunk before it ends (line {pos})")
        out += src[pos:start]
        if (h.b - 1 if h.nb else h.b) != len(out):
            raise Fail(f"hunk {h}: its new lines would start at line {len(out) + 1} of the new file")
        want = [body for op, body in h.lines if op != b"+"]
        if src[start:start + h.na] != want:
            raise Fail(f"hunk {h}: its old lines are not lines {start + 1} to {start + h.na} of the old file")
        out += [body for op, body in h.lines if op != b"-"]
        pos = start + h.na
        if context is not None:
            ops = b"".join(op for op, _ in h.lines)
            lead = len(ops) - len(ops.lstrip(b" "))
            trail = len(ops) - len(ops.rstrip(b" "))
            if lead != min(context, start + lead) or lead == len(ops):
                raise Fail(f"hunk {h}: {lead} lines of context before its first change")
            if trail != min(context, len(src) - pos + trail):
                raise Fail(f"hunk {h}: {trail} lines of context after its last change")
            for run in re.findall(rb"(?<=[-+])( +)(?=[-+])", ops):
                if len(run) > 2 * context:
                    raise Fail(f"hunk {h}: {len(run)} unchanged lines between two changes in one hunk")
            if k > 0:
                gap = start + lead - (prev_end - prev_trail)
                if gap <= 2 * context:
                    raise Fail(f"hunk {h}: only {gap} unchanged lines after the last change of the hunk "
                               f"before it: they belong in one hunk")
            prev_end, prev_trail = pos, trail
    return b"".join(out + src[pos:])


def system_diff(t, a, b, args=("-u",)):
    r = T.system(t, ["diff", "-d"] + list(args) + [a, b], check=False)
    if r.rc not in (0, 1):
        raise Fail(f"the system's diff failed:\n{r}")
    return r


def read(path):
    with open(path, "rb") as f:
        return f.read()


def _tmp(t):
    return t.tmp if hasattr(t, "tmp") else T._root(t)


def apply_system(t, diff, old_path):
    if not T.have("patch"):
        return reference_patch(diff, read(old_path))
    tmp = os.path.join(_tmp(t), "system-patch")
    shutil.rmtree(tmp, ignore_errors=True)
    os.mkdir(tmp)
    work, dpath = os.path.join(tmp, "file"), os.path.join(tmp, "change.diff")
    shutil.copyfile(old_path, work)
    with open(dpath, "wb") as f:
        f.write(diff)
    r = T.system(t, ["patch", "-s", "-f", work, dpath], check=False)
    if r.rc != 0:
        raise Fail(f"the system's patch did not apply our diff:\n{r}\n--- the diff\n"
                   f"{diff[:1500].decode('utf-8', 'replace')}")
    out = read(work)
    shutil.rmtree(tmp)
    return out


def _context(args):
    args = list(args)
    for i, a in enumerate(args):
        if a == "-U":
            return int(args[i + 1])
        if a.startswith("-U"):
            return int(a[2:])
    return 3


def strip_headers(text):
    return re.sub(rb"\A--- [^\n]*\n\+\+\+ [^\n]*\n", b"", text)


def same_text(t, ours, theirs, what):
    o, s = strip_headers(ours), strip_headers(theirs)
    T.same(t, o.decode("utf-8", "surrogateescape"), s.decode("utf-8", "surrogateescape"), what)


def check(t, a, b, args=(), algo=None):
    argv = ([f"--algo={algo}"] if algo else []) + list(args) + [a, b]
    ours = T.run(t, "diff", argv, env={"DS_STATS": "1"}, check=False)
    what = f"bin/diff {' '.join(argv)}"
    theirs = system_diff(t, a, b)
    if ours.rc != theirs.rc:
        raise Fail(f"{what}: exit status {ours.rc}, the system's diff {theirs.rc}:\n{ours}")
    A, B = read(a), read(b)
    s = T.stats(ours.err)["diff"]
    want = changes(theirs.raw)
    if (s["deleted"], s["inserted"]) != want or s["common"] != len(lines(A)) - want[0]:
        raise Fail(f"{what}: {s}; the system's diff deletes {want[0]} lines and inserts {want[1]}")
    if "-q" in args:
        T.same(t, ours.out, T.system(t, ["diff", "-q", a, b], check=False).out, what)
        return ours
    if ours.rc == 0:
        if ours.raw:
            raise Fail(f"{what}: the files are the same, and it printed:\n{ours}")
        return ours
    head = ours.out.split("\n", 2)
    for line, mark, path in ((head[0], "---", a), (head[1], "+++", b)):
        m = HEADER.match(line)
        if not m or m.group(1) != mark or m.group(2) != path:
            raise Fail(f"{what}: not a header line for {path}: {line!r}")
    if changes(ours.raw) != want:
        raise Fail(f"{what}: deletes and inserts {changes(ours.raw)}, the system's diff {want}")
    if s["hunks"] != len(parse(ours.raw)):
        raise Fail(f"{what}: {len(parse(ours.raw))} hunks, and the stats say {s['hunks']}")
    try:
        made = reference_patch(ours.raw, A, _context(args))
    except Fail as e:
        raise Fail(f"{what}: {e}\n--- the diff\n{ours.out[:1500]}")
    if made != B:
        raise Fail(f"{what}: its hunks do not make {b} of {a}")
    if apply_system(t, ours.raw, a) != B:
        raise Fail(f"{what}: the system's patch, with our diff, does not make {b} of {a}")
    return ours


# ---------------------------------------------------------------- the pairs

HAND = {
    "same": (b"one\ntwo\nthree\n", b"one\ntwo\nthree\n"),
    "both-empty": (b"", b""),
    "from-empty": (b"", b"a\nb\n"),
    "to-empty": (b"a\nb\n", b""),
    "one-line": (b"x\n", b"y\n"),
    "add-newline": (b"a\nb", b"a\nb\n"),
    "drop-newline": (b"a\nb\n", b"a\nb"),
    "no-newline-kept": (b"a\nb\nc", b"a\nB\nc"),
    "no-newline-changed": (b"a\nb", b"a\nc"),
    "no-newline-only": (b"x", b"y"),
    "insert-first": (b"b\nc\n", b"a\nb\nc\n"),
    "insert-last": (b"a\nb\n", b"a\nb\nc\n"),
    "delete-middle": (b"a\nb\nc\n", b"a\nc\n"),
    "nothing-common": (b"a\nb\nc\n", b"d\ne\nf\ng\n"),
    "blank-lines": (b"\n\n}\n\n}\n\n", b"}\n\n\n}\n\n\n"),
    "crlf": (b"a\r\nb\r\n", b"a\r\nB\r\n"),
    "header-like": (b"--- x\n+++ y\n@@ -1 +1 @@\nk\n", b"k\n-- x\n++ y\n\\ x\n"),
    "long-line": (b"x" * 10000 + b"\n", b"x" * 9999 + b"y\n"),
    "swap": (b"a\nb\n", b"b\na\n"),
}


def cases(t, big=False):
    out = {}
    for name, (a, b) in HAND.items():
        out[name] = (T.write(t, f"{name}.a", a), T.write(t, f"{name}.b", b))
    for kind, n, seeds in (("versions", 500, 3), ("revised", 400, 2), ("unrelated", 120, 2), ("versions", 30, 4)):
        for s in range(1, seeds + 1):
            out[f"{kind}-{n}-{s}"] = tuple(T.gen(t, kind, n, seed=s))
    return out


def unique_cases(t):
    """Numbered lines, every one different, with changes that only delete lines or bring new ones:
    the lines in common are the numbered lines left, in order, and no other choice is as long."""
    def numbered(n):
        return [b"line %d\n" % i for i in range(1, n + 1)]

    def edit(n, edits, last_newline=True):
        a = numbered(n)
        b = list(a)
        for at, dele, ins in sorted(edits, reverse=True):
            b[at:at + dele] = [b"new %d.%d\n" % (at, j) for j in range(ins)]
        if not last_newline:
            a[-1], b[-1] = a[-1].rstrip(b"\n"), b[-1].rstrip(b"\n")
        return b"".join(a), b"".join(b)

    pairs = {
        "u-apart-6": edit(40, [(10, 1, 1), (17, 1, 1)]),      # 6 lines between: one hunk at -U3
        "u-apart-7": edit(40, [(10, 1, 1), (18, 1, 1)]),      # 7 lines between: two hunks
        "u-ends": edit(30, [(0, 1, 2), (29, 1, 0)]),          # the first line changed, the last gone
        "u-near-ends": edit(30, [(1, 0, 1), (28, 2, 1)]),
        "u-insert-first": edit(20, [(0, 0, 2)]),
        "u-insert-end": edit(20, [(20, 0, 3)]),
        "u-no-newline": edit(20, [(19, 1, 1)], last_newline=False),
        "u-no-newline-kept": edit(20, [(17, 1, 2)], last_newline=False),
        "u-many": edit(200, [(5, 2, 0), (30, 0, 4), (31, 3, 3), (60, 1, 1), (66, 1, 1), (120, 10, 2),
                             (150, 1, 0), (157, 0, 1), (199, 1, 1)]),
    }
    return {name: (T.write(t, f"{name}.a", a), T.write(t, f"{name}.b", b)) for name, (a, b) in pairs.items()}


# ---------------------------------------------------------------- the project at each lesson

DIFF_RE = (r"--- d1\.txt\t[-0-9: .]+ [+-]\d{4}\r?\n\+\+\+ d2\.txt\t[-0-9: .]+ [+-]\d{4}\r?\n"
           r"@@ -1,3 \+1,3 @@\r?\n a\r?\n-b\r?\n c\r?\n\+d\r?\n")


def timeline_steps(k):
    if k < (6, 1):
        return []
    have = "table, myers" if k >= (6, 3) else "table"
    steps = [T.sh_step("printf 'a\\nb\\nc\\n' > d1.txt; printf 'a\\nc\\nd\\n' > d2.txt; bin/diff d1.txt d1.txt", "", 0),
             T.sh_step("bin/diff --algo=bogo d1.txt d2.txt", f"diff: no --algo 'bogo' (have: {have})\n", 2),
             T.sh_step("bin/diff d1.txt", "diff: usage: diff [option ...] file1 file2\n", 2),
             T.sh_step("bin/diff d1.txt nonesuch.txt", "diff: nonesuch.txt: No such file or directory\n", 2)]
    if k < (6, 2):
        steps += [T.sh_step("bin/diff d1.txt d2.txt", "Files d1.txt and d2.txt differ\n", 1),
                  T.sh_step("bin/diff -u d1.txt d2.txt", "diff: unknown option -u\n", 2)]
    else:
        steps += [T.sh_step("bin/diff -q d1.txt d2.txt", "Files d1.txt and d2.txt differ\n", 1),
                  T.sh_step("bin/diff --algo=table d1.txt d2.txt", regex=DIFF_RE, status=1),
                  T.sh_step("bin/diff -U0 d1.txt d2.txt | tail -n +3", "@@ -2 +1,0 @@\n-b\n@@ -3,0 +3 @@\n+d\n")]
    if k < (6, 3):
        steps.append(T.sh_step("bin/diff --algo=myers d1.txt d2.txt", f"diff: no --algo 'myers' (have: table)\n", 2))
    else:
        steps.append(T.sh_step("bin/diff --algo=myers d1.txt d2.txt", regex=DIFF_RE, status=1))
    if k >= (6, 4):
        steps += [T.sh_step("bin/diff d1.txt d2.txt > d.diff; cp d1.txt d3.txt; bin/patch d3.txt d.diff && cat d3.txt",
                            "patching file d3.txt\na\nc\nd\n", 0),
                  T.sh_step("bin/patch d3.txt d.diff",
                            "patching file d3.txt\npatch: d3.txt: hunk #1 (line 3 of the patch) does not apply: "
                            "its lines are not in the file\npatch: d3.txt: 1 of 1 hunk did not apply: the file is "
                            "not changed\n", 1)]
    return steps


def timeline_after(root, k):
    if k < (6, 1):
        return None
    book = T.data(root, "book.txt")
    old, new = os.path.join(root, "book-old.txt"), os.path.join(root, "book-new.txt")
    T.sh(root, "head -n 1500 \"$0\" > \"$1\"; sed -e '3d' -e '700s/$/ (changed)/' -e '1200a\\\nA new line.' "
         "\"$1\" > \"$2\"", [book, old, new])
    theirs = changes(system_diff(root, old, new).raw)
    r = T.run(root, "diff", [old, new], env={"DS_STATS": "1"}, check=False)
    s = T.stats(r.err)["diff"]
    if r.rc != 1 or (s["deleted"], s["inserted"]) != theirs:
        raise Fail(f"bin/diff on 1500 lines of the book: {s}, the system's diff {theirs}:\n{r}")
    note = f"diff: the system's {theirs[0]} deleted and {theirs[1]} inserted lines"
    if k >= (6, 2):
        if apply_system(root, r.raw, old) != read(new):
            raise Fail("bin/diff on 1500 lines of the book: the system's patch does not make the new file")
        note += ", and its patch takes our diff"
    if k >= (6, 4):
        T.sh(root, "cp \"$0\" \"$1\"", [old, os.path.join(root, "book-work.txt")])
        theirs = system_diff(root, old, new).raw
        p = T.run(root, "patch", ["-s", "book-work.txt"], input=theirs)
        if read(os.path.join(root, "book-work.txt")) != read(new):
            raise Fail(f"bin/patch with the system's diff does not make the new file:\n{p}")
        note += "; bin/patch takes the system's"
    return note
