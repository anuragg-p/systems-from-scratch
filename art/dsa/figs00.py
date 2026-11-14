"""Figures for dsa module 00, The workbench (lessons 00.01 and 00.02).

    python3 art/dsa/figs00.py

Every count is from the real program: the script writes the project at the lesson with
./learn files, builds it, and runs bin/paste with DS_STATS=1 on the same input the figure
draws, then asserts that its own model of add() gives the same counts.

  00.01-strcat   printf 'one\\ntwo\\nthree\\n' | bin/paste -s -d , --algo=strcat
                 -> stats: paste: lines 3, bytes copied 13, bytes scanned 22 (end: 0)
  00.02-race     the growth harness on bin/paste -s --algo=strcat and --algo=end, n = 16000
                 to 1024000 words of gen.py text. The seconds are one run of
                   python3 bench/grow.py --start 16000 --max 1024000 --limit 100 \\
                       --json race.json bin/paste -s --algo=strcat     (and --algo=end)
                 on an Apple M4 Pro, macOS 26.6.2 (RACE below); the bytes scanned at each n
                 are counted here, by the real program, on the same bytes.
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import figlib  # noqa: E402
from figlib import Fig, write  # noqa: E402
import steps  # noqa: E402

figlib.LESSONS = os.path.join(ROOT, "tracks", "dsa", "lessons")
MOD = "00-workbench"

_built = {}


def project(at):
    """The project at lesson `at`, as ./learn files writes it, built: its directory."""
    if at not in _built:
        d = os.path.join(tempfile.mkdtemp(prefix="dsa-figs-"), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["make", "-s"], cwd=d, check=True)
        _built[at] = d
    return _built[at]


def stats(at, argv, data):
    """The DS_STATS=1 lines of bin/<argv> run on data: {"paste": {"lines": 3, ...}, ...}."""
    d = project(at)
    env = dict(os.environ, DS_STATS="1", LC_ALL="C")
    r = subprocess.run([os.path.join(d, "bin", argv[0])] + argv[1:], input=data, cwd=d, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    out = {}
    for m in re.finditer(r"^stats: ([^:]+): (.*)$", r.stderr.decode(), re.M):
        out[m.group(1)] = {k: int(v) for k, v in (p.rsplit(" ", 1) for p in m.group(2).split(", "))}
    return out


# ------------------------------------------------------------------ 00.01

def paste_model(lines, delim, strcat):
    """add() of tools/paste/paste.c, piece by piece: [(piece, line before, scanned)], copied, scanned."""
    out, rows, copied, scanned = "", [], 0, 0
    for k, line in enumerate(lines):
        pieces = ([delim] if k > 0 else []) + [line]
        for p in pieces:
            s = len(out) if strcat else 0
            rows.append((p, out, s))
            out += p
            copied += len(p)
            scanned += s
    return rows, copied, scanned


def strcat0001():
    lines = ["one", "two", "three"]
    data = "".join(l + "\n" for l in lines).encode()
    rows, copied, scanned = paste_model(lines, ",", True)
    _, _, scanned_end = paste_model(lines, ",", False)
    real = stats("00.01", ["paste", "-s", "-d", ",", "--algo=strcat"], data)["paste"]
    real_end = stats("00.01", ["paste", "-s", "-d", ","], data)["paste"]
    assert (real["lines"], real["bytes copied"], real["bytes scanned"]) == (3, copied, scanned), real
    assert real_end["bytes scanned"] == scanned_end == 0, real_end

    f = Fig("f0001a", "Joining one, two and three with commas: before each piece, strcat walks the whole line "
            "to find its end; the fast version remembers where the end is", 314)
    f.text(24, 22, "printf 'one\\ntwo\\nthree\\n' | bin/paste -s -d ,", "t", 11.5, mono=True)
    f.text(24, 40, "the line being built, as each piece is added (the box after the last byte is its '\\0')",
           "tm", 10.5)
    X, W, H = 140, 21, 24
    C1, C2 = 520, 604
    f.text(C1, 66, "strcat", "t", 11, "end", 600)
    f.text(C1, 80, "reads", "tm", 10, "end")
    f.text(C2, 66, "end", "t", 11, "end", 600)
    f.text(C2, 80, "reads", "tm", 10, "end")
    for i, (piece, before, s) in enumerate(rows):
        y = 94 + i * 34
        f.text(24, y + 16, f"add \"{piece}\"", "t", 11, mono=True)
        x = X
        for ch in before:
            f.rect(x, y, W - 2, H, "a af", 3)
            f.text(x + (W - 2) / 2, y + 16, ch, "ta", 11.5, "middle", mono=True)
            x += W
        for ch in piece:
            f.rect(x, y, W - 2, H, "s fs", 3)
            f.text(x + (W - 2) / 2, y + 16, ch, "t", 11.5, "middle", 600, mono=True)
            x += W
        f.rect(x, y, W - 2, H, "m f", 3)
        f.text(x + (W - 2) / 2, y + 15.5, "\\0", "tm", 9.5, "middle", mono=True)
        f.text(C1, y + 16, str(s), "ta" if s else "tm", 12, "end", 600, mono=True)
        f.text(C2, y + 16, "0", "tm", 12, "end", mono=True)
    yt = 94 + len(rows) * 34 + 4
    f.line(448, yt - 6, 616, yt - 6, "m")
    f.text(448, yt + 12, "in all", "tm", 10.5)
    f.text(C1, yt + 12, str(scanned), "ta", 12, "end", 700, mono=True)
    f.text(C2, yt + 12, "0", "t", 12, "end", 700, mono=True)
    f.rect(24, yt + 2, 12, 12, "a af", 2)
    f.text(42, yt + 12, "read again by strlen() to find the end", "tm", 10.5)
    f.rect(24, yt + 20, 12, 12, "s fs", 2)
    f.text(42, yt + 30, f"copied: {copied} bytes, the same in both", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 00.02

# One run of the growth harness on each version (see the docstring): n -> fastest of three, seconds.
RACE_STRCAT = {16000: 0.0041, 32000: 0.0095, 64000: 0.0293, 128000: 0.1119, 256000: 0.4555,
               512000: 1.8361, 1024000: 7.4163}
RACE_END = {16000: 0.0022, 32000: 0.0027, 64000: 0.0024, 128000: 0.0027, 256000: 0.0047,
            512000: 0.0037, 1024000: 0.0073}


def gen_text(n):
    d = project("00.02")
    return subprocess.run([sys.executable, os.path.join(d, "data", "gen.py"), "text", str(n)], cwd=d,
                          stdout=subprocess.PIPE, check=True).stdout


def fmt_s(t):
    return f"{t:.3f}"


def race0002():
    ns = sorted(RACE_STRCAT)
    scanned = {}
    for n in ns:
        st = stats("00.02", ["paste", "-s", "--algo=strcat"], gen_text(n))["paste"]
        scanned[n] = st["bytes scanned"]
    print("00.02 bytes scanned:", scanned)

    f = Fig("f0002a", "The doubling test, a row at a time: the same job, paste -s, done by strcat and by "
            "remembering the end, on inputs twice as big each time", 324)
    f.text(24, 22, "bin/paste -s on n words of gen.py text: the fastest of three runs, on an Apple M4 Pro", "tm", 11)
    cols = {"n": 100, "strcat": 184, "ratio": 232, "end": 306}
    y0, rh = 52, 32
    f.text(cols["n"], y0, "n", "tm", 11.5, "end")
    f.text(cols["strcat"], y0, "strcat, s", "ta", 11.5, "end", 600)
    f.text(cols["ratio"], y0, "ratio", "tm", 11.5, "end")
    f.text(cols["end"], y0, "end, s", "t", 11.5, "end", 600)
    bx, bw = 324, 290
    top = max(RACE_STRCAT.values())
    f.rect(bx + 8, y0 - 9, 12, 9, "fa", 1.5, sw=False)
    f.text(bx + 26, y0, "strcat", "tm", 11.5)
    f.rect(bx + 86, y0 - 9, 12, 9, "tm", 1.5, sw=False)
    f.text(bx + 104, y0, "end", "tm", 11.5)
    f.text(bx + bw, y0, f"{top:.1f} s", "tm", 11, "end", mono=True)
    f.line(bx, y0 + 8, bx, y0 + 10 + rh * len(ns), "m")
    f.line(bx + bw, y0 + 8, bx + bw, y0 + 10 + rh * len(ns), "m", dash=True)
    yf = y0 + 34 + rh * len(ns)
    for k, n in enumerate(ns):
        prev = ns[k - 1] if k else None
        r = RACE_STRCAT[n] / RACE_STRCAT[prev] if prev and min(RACE_STRCAT[n], RACE_STRCAT[prev]) >= 0.02 else None
        if k == 0:
            cap = (f"n = {n:,}: strcat {fmt_s(RACE_STRCAT[n])} s, end {fmt_s(RACE_END[n])} s. Both are mostly "
                   f"the time to start a program; no ratio yet.")
        elif r is None:
            cap = (f"n = {n:,}: strcat {fmt_s(RACE_STRCAT[n])} s, end {fmt_s(RACE_END[n])} s. Still too quick to "
                   f"time: a ratio needs both runs at 20 ms or more.")
        else:
            cap = (f"n = {n:,}: strcat {fmt_s(RACE_STRCAT[n])} s, {r:.1f} times the row before; it read "
                   f"{scanned[n] / scanned[prev]:.1f} times the bytes. end: {fmt_s(RACE_END[n])} s.")
        with steps.step(f, cap):
            for i, m in enumerate(ns):
                y = y0 + 12 + i * rh
                if i > k:
                    f.text(cols["n"], y + 18, f"{m:,}", "tm", 12.5, "end", mono=True)
                    continue
                new = i == k
                if new:
                    f.rect(18, y + 1, 300, rh - 4, "af", 4, sw=False)
                p = ns[i - 1] if i else None
                rr = RACE_STRCAT[m] / RACE_STRCAT[p] if p and min(RACE_STRCAT[m], RACE_STRCAT[p]) >= 0.02 else None
                f.text(cols["n"], y + 18, f"{m:,}", "ta" if new else "t", 12.5, "end", 600 if new else None, mono=True)
                f.text(cols["strcat"], y + 18, fmt_s(RACE_STRCAT[m]), "ta" if new else "t", 12.5, "end",
                       600 if new else None, mono=True)
                if rr is not None:
                    f.text(cols["ratio"], y + 18, f"{rr:.1f}", "ta" if new else "t", 12.5, "end", 600, mono=True)
                f.text(cols["end"], y + 18, fmt_s(RACE_END[m]), "t", 12.5, "end", mono=True)
                ws = max(2.0, bw * RACE_STRCAT[m] / top)
                we = max(2.0, bw * RACE_END[m] / top)
                f.rect(bx + 1, y + 4, round(ws, 1), 10, "fa", 1.5, sw=False)
                f.rect(bx + 1, y + 16, round(we, 1), 6, "tm", 1, sw=False)
            last = ns[k]
            f.text(24, yf, f"bytes strlen() read at n = {last:,}:", "tm", 11)
            f.text(bx + 8, yf, f"{scanned[last]:,}", "ta", 12, weight=600, mono=True)
    return f


def main():
    for name, fn in (("00.01-strcat", strcat0001), ("00.02-race", race0002)):
        fig = fn()
        text = fig.svg()
        if "step" in name or name.endswith("race"):
            print(name, "steps:", steps.check(text))
        print(write(MOD, name, fig))


if __name__ == "__main__":
    main()
