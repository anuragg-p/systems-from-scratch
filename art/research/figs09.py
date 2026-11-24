"""Figures for research module 09, GPT-2: the tokenizer and the real weights (lessons 09.01-09.04).

    RESEARCH_FIGS_CACHE=DIR python3 -B art/research/figs09.py [09.02 ...]
                                    all of them, or those whose name starts so (DIR keeps the runs)

Every bar, box, curve and number comes from the reference code (tracks/research), run as the page
runs it, from GPT-2's and TinyStories' fetched files, or from the recorded long run the page shows:

  09.01  python3 -m experiments.bpe (the page's run): its counts, bytes per token and every seed's bits;
         the same script with sizes to 8192 (part 5 cut to one seed of ten steps: the figure reads part 3
         only, and its first four rows must be the page's); the unseen words and the merges of two words
         from tokens/bpe.py at 09.01, trained as the run trains it (its first symbols must be the run's)
  09.02  python3 -m experiments.tokenizer (the page's run): bytes per token; GPT-2's byte table and the
         pieces and ids of the run's sentence, from tokens/gpt2.py at 09.02 and GPT-2's files; tiktoken
         (installed for the comparison: the project never imports it), built from the same two files, on
         U+1C89 and on every code point this Python's Unicode leaves unassigned, before 's; U+1C89's
         category in a newer Python's unicodedata (python3.14), when there is one
  09.03  python3 -m experiments.gpt2 (the page's run): the ladder and every way's perplexity; the names
         and shapes from model.safetensors' own header and GPT(**CONFIG); the next tokens, loaded right
         (they must be the run's) and with attn.c_proj untransposed; load_file's peak in a fresh python
         at 09.02 (02.05's load_file) and at 09.03
  09.04  python3 -m experiments.tinystories (the page's run): its stories' shared runs; the recorded long
         run, experiments/recorded/tinystories/ (its logs, summaries and output.txt); the training
         stories' lengths, from the tokens data/tinystories.py keeps in the data cache

Needs PyTorch, GPT-2's files and TinyStories (python3 -m data.fetch gpt2, python3 -m data.fetch
tinystories, in tracks/research), and tiktoken for 09.02's comparison. The runs take about five minutes
in all on the machine in NOTES.md.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                          # art/research/: figlib, figart
sys.path.insert(0, os.path.dirname(HERE))         # art/: steps.py, for the stepped figure
import figart  # noqa: E402
import figlib  # noqa: E402
import steps  # noqa: E402
from figlib import Fig, sig, tw, write  # noqa: E402

MOD = "09"
_memo = {}


def in_project(at, code):
    """Run python code in the project as it stands at lesson `at`, in a fresh python; the JSON it prints
    last (once per process for the same code)."""
    if (at, code) in _memo:
        return _memo[at, code]
    d = figart.project(at)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d)
    r = subprocess.run([sys.executable, "-B", "-c", code], cwd=d, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"python in the project at {at} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    _memo[at, code] = json.loads(r.stdout.strip().splitlines()[-1])
    return _memo[at, code]


def shown(s, space="_"):
    """Text as a figure writes it, in ASCII: a space as _ (or as space), a line break as \\n, a tab as
    \\t, and any other character outside printable ASCII as its escape (\\xe9, \\u1c89)."""
    out = []
    for c in s:
        if c == " ":
            out.append(space)
        elif c == "\n":
            out.append("\\n")
        elif c == "\t":
            out.append("\\t")
        elif 32 < ord(c) < 127:
            out.append(c)
        else:
            out.append(ascii(c)[1:-1])
    return "".join(out)


def mean(xs):
    return sum(xs) / len(xs)


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def chip(f, x, y, s, cls="s f", tcls="t", size=11, h=22, pad=8, weight=None, dash=False):
    """A box round one piece of text in mono, its width from the text; the x after it."""
    w = max(tw(s, size, mono=True) + 2 * pad, 18)
    f.rect(x, y, w, h, cls, 3, dash=dash)
    f.text(x + w / 2, y + h / 2 + size * 0.36, s, tcls, size, "middle", weight, mono=True)
    return x + w


# ------------------------------------------------------------------ the runs

def bpe_run():
    return figart.experiment("bpe", at="09.01")


def sizes_run():
    return figart.experiment("bpe", "sizes=[256,512,1024,2048,4096,8192]", "seeds=1", "steps=10", "every=5",
                             at="09.01")


def tok_run():
    return figart.experiment("tokenizer", at="09.02")


def gpt2_run():
    return figart.experiment("gpt2", at="09.03")


def ts_run():
    return figart.experiment("tinystories", at="09.04")


def bytes_table(out):
    """Part 3 of a bpe run: [(vocabulary, training text, test text)]."""
    part = out.split("3. Bytes per token")[1].split("\n\n")[0]
    return [(int(m.group(1).replace(",", "")), float(m.group(2)), float(m.group(3)))
            for m in re.finditer(r"^ +([\d,]+) +(\d\.\d{3}) +(\d\.\d{3})$", part, re.M)]


# ------------------------------------------------------------------ 09.01

UTF8 = [0x65, 0xE9, 0x4F60, 0x1F44B]


def utf80901():
    f = Fig("utf80901", "Four characters as UTF-8: each code point's bits cut into the pattern for its size; the "
                        "first byte says how many bytes the character takes, and every byte after it starts 10", 318)
    f.text(20, 22, "the character", "tm", 11)
    f.text(178, 22, "its code point in bits", "tm", 11)
    f.text(340, 22, "its UTF-8 bytes (in hex below)", "tm", 11)
    first = {1: 7, 2: 5, 3: 4, 4: 3}
    for r, cp in enumerate(UTF8):
        data = chr(cp).encode("utf-8")
        n = len(data)
        total = first[n] + 6 * (n - 1)
        bits = format(cp, f"0{total}b")
        groups = [bits[:first[n]]] + [bits[first[n] + 6 * k:first[n] + 6 * k + 6] for k in range(n - 1)]
        heads = ["0"] if n == 1 else ["1" * n + "0"] + ["10"] * (n - 1)
        assert [int(h + g, 2) for h, g in zip(heads, groups)] == list(data), cp
        y = 44 + r * 62
        f.text(20, y + 16, f"U+{cp:04X}", "t", 13, weight=700, mono=True)
        name = unicodedata.name(chr(cp)).lower()
        name = name.replace("cjk unified ideograph-4f60", "a Chinese character ('you')")
        f.text(20, y + 33, name, "tm", 10)
        f.text(20, y + 47, f"{n} byte{'s' * (n > 1)}", "tm", 10)
        x = 178
        for k, g in enumerate(groups):
            f.text(x, y + 16, g, "ta", 10, mono=True)
            x += tw(g, 10, mono=True) + 4
        f.text(178, y + 33, f"{total} bits", "tm", 10)
        for k, (h, g, b) in enumerate(zip(heads, groups, data)):
            bx = 340 + k * 73
            f.rect(bx, y + 2, 70, 24, "s f", 3)
            wh, wg = tw(h, 10, mono=True), tw(g, 10, mono=True)
            x0 = bx + 35 - (wh + wg) / 2
            f.text(x0, y + 18, h, "tm", 10, mono=True)
            f.text(x0 + wh, y + 18, g, "ta", 10, weight=700, mono=True)
            f.text(bx + 35, y + 41, f"{b:02x}", "t", 11, "middle", mono=True)
    yb = 44 + 4 * 62 + 4
    f.text(20, yb, "The pattern's bits muted, the code point's in the accent. The four patterns (RFC 3629): 0xxxxxxx "
                   "to U+007F;", "tm", 10.5)
    f.text(20, yb + 15, "110xxxxx 10xxxxxx to U+07FF; 1110xxxx and two 10xxxxxx to U+FFFF; 11110xxx and three to "
                        "U+10FFFF.", "tm", 10.5)
    return f


UNSEEN_CODE = """
import json
from collections import Counter
from data import shakespeare
from experiments import bpe as B
from tokens import bpe
text = shakespeare.load()
lo, mid, hi = (int(f * len(text)) for f in (0.9, 0.95, 1.0))
train_text, test_text = text[:lo], text[mid:hi]
words, held = B.WORD.findall(train_text), B.WORD.findall(test_text)
share, running = B.unseen(words, held)
known = set(words)
missing = Counter(w for w in held if w not in known)
merges = bpe.train(train_text, 2048)
table = bpe.vocab(merges)
def merged(w):
    ids = list(w.encode())
    out = [[0, None, [table[i].decode() for i in ids]]]
    while len(ids) > 1:
        pair = min(zip(ids, ids[1:]), key=lambda p: merges.get(p, float("inf")))
        if pair not in merges:
            break
        ids = bpe.merge(ids, pair, merges[pair])
        out.append([merges[pair] - 255, [table[pair[0]].decode(), table[pair[1]].decode(), merges[pair]],
                    [table[i].decode() for i in ids]])
    return out
top = missing.most_common(8)
print(json.dumps({"different": len(set(held)), "share": share, "running": running, "n_held": len(held),
                  "n_missing": sum(1 for w in set(held) if w not in known), "top": top, "merges": len(merges),
                  "pieces": {w: [table[i].decode() for i in bpe.encode(w, merges)] for w, _ in top},
                  "first": [table[i].decode() for i in list(merges.values())[:24]],
                  "in_training": {w: train_text.count(w) for w in WORDS}, "in_test": {w: test_text.count(w) for w in WORDS},
                  "steps": {w: merged(w) for w in WORDS}}))
""".replace("WORDS", repr([" heavens", " Prospero"]))


def unseen_data():
    d = in_project("09.01", UNSEEN_CODE)
    printed = re.search(r"The first 24 symbols it made: (.*)$", bpe_run().out, re.M).group(1)
    if printed != " ".join(repr(s) for s in d["first"]):
        raise SystemExit(f"the merges trained here differ from the run's:\n{printed}\n{d['first']}")
    out = bpe_run().out
    want = (f"{d['different']:,} different words {100 * d['share']:.1f}% never occur in training: "
            f"{100 * d['running']:.1f}% of its {d['n_held']:,} running words")
    if want not in out:
        raise SystemExit(f"the unseen words counted here are not the run's: {want}")
    return d


def unseen0901():
    d = unseen_data()
    f = Fig("unseen0901", f"The test text's words that the training text never had (a word: a run of letters): "
                          f"{d['n_missing']} of its {d['different']:,} different words, {100 * d['running']:.1f}% "
                          f"of its running words; the most frequent of them, and the pieces 09.01's 2,048 symbols "
                          f"write them in", 346)
    x0, W = 190, 420
    for k, (label, total, share, unit) in enumerate((("different words", d["different"], d["share"], "words"),
                                                     ("running words", d["n_held"], d["running"], "words"))):
        y = 30 + k * 46
        f.text(20, y + 15, f"the test text's {label}", "t", 11.5, weight=600)
        f.text(20, y + 30, f"{total:,} in all", "tm", 10.5)
        w = W * share
        f.rect(x0, y, W - w, 22, "s fs", 0)
        f.rect(x0 + W - w, y, w, 22, "a af", 0)
        f.text(x0 + 8, y + 15, f"in the training text: {100 * (1 - share):.1f}%", "t", 10.5)
        f.text(x0 + W - w - 6, y + 37, f"never in it: {100 * share:.1f}%", "ta", 10.5, "end", 600)
    y0 = 136
    f.text(20, y0, "never in the training text", "ta", 11.5, weight=700)
    f.text(214, y0, "times in the test text", "tm", 10.5, "middle")
    f.text(290, y0, "as 09.01's tokens (a vocabulary of 2,048, learned on the training text)", "tm", 10.5)
    for i, (w, n) in enumerate(d["top"]):
        y = y0 + 22 + i * 21
        f.text(20, y, w, "t", 11.5, mono=True)
        f.text(214, y, str(n), "t", 11, "middle", mono=True)
        x = 290
        for p in d["pieces"][w]:
            x = chip(f, x, y - 14, shown(p), "a af", "ta", 10.5, h=19, pad=6) + 3
    f.text(20, y0 + 22 + len(d["top"]) * 21 + 4,
           "A model with one symbol per training word has none of these; byte pair encoding writes each in pieces "
           "it has.", "tm", 10.5)
    return f


def merge0901():
    """The stepped figure: two words, one the training text has 35 times and one it never had, as the
    trainer's merges come, in the order learned."""
    d = unseen_data()
    words = list(d["steps"])
    events = sorted({s[0] for w in words for s in d["steps"][w][1:]})
    total = d["merges"]
    f = Fig("merge0901", f"One word the training text has and one it never had, as the trainer's merges come: each "
                         f"frame is a merge that changes one of them, numbered in the order learned "
                         f"({total:,} in all)", 252)
    rows = {}
    for k, w in enumerate(words):
        y = 34 + k * 74
        rows[w] = y
        n = d["in_training"][w]
        f.text(20, y, f"{shown(w)!r}", "t", 12.5, weight=700, mono=True)
        f.text(20 + tw(repr(shown(w)), 12.5, True) + 12, y,
               f"{n} times in the training text" if n else "never in the training text", "tm", 11)
    ax0, ax1, ay = 40, 600, 206

    def at(e):                                   # the merges on a log axis, 1 to the last
        return ax0 + (ax1 - ax0) * math.log(max(e, 1)) / math.log(total)
    f.line(ax0, ay, ax1, ay, "m")
    for e in (1, 10, 100, 1000, total):
        f.line(at(e), ay - 3, at(e), ay + 3, "m")
        f.text(at(e), ay + 16, f"merge {e:,}" if e == 1 else f"{e:,}", "tm", 10, "middle")
    for e in events:
        f.circle(at(e), ay, 2, "m f")
    f.text(20, 244, "_ is a space. The merges on a log scale. Each word is merged as encode() merges it: the pair "
                    "learned first, again and again.", "tm", 10.5)

    def state(w, upto):
        last = [s for s in d["steps"][w] if s[0] <= upto]
        return last[-1]

    for t, e in enumerate([0] + events):
        changed = [w for w in words if state(w, e)[0] == e and e]
        if e == 0:
            cap = (f"Before any merge each word is its bytes, one symbol each: {shown(words[0])!r} "
                   f"{len(words[0].encode())}, {shown(words[1])!r} {len(words[1].encode())}.")
        else:
            w = changed[0]
            a, b, new = state(w, e)[1]
            now = " ".join(repr(shown(p)) for p in state(w, e)[2])
            cap = (f"Merge {e:,} of {total:,}: {shown(a)!r} + {shown(b)!r}, the pair counted most often at that point, "
                   f"becomes symbol {new}; {shown(w)!r} is now {now}.")
            if e == events[-1]:
                cap += (f" No later merge changes either: {shown(words[1])!r}, which the training text never had, "
                        f"stays {len(state(words[1], e)[2])} pieces it did have.")
        with steps.step(f, cap):
            for w in words:
                y = rows[w] + 12
                num, rule, syms = state(w, e)
                x = 20
                for p in syms:
                    hot = w in changed and num == e and rule and p == rule[0] + rule[1]
                    x = chip(f, x, y, shown(p), "a af" if hot else "s f", "ta" if hot else "t", 13, h=28, pad=9,
                             weight=700 if hot else None) + 4
                f.text(x + 10, y + 19, f"{len(syms)} symbol{'s' * (len(syms) > 1)}", "tm", 11)
                if num:
                    f.text(600, y + 19, f"last changed by merge {num:,}", "ta" if w in changed else "tm", 10.5, "end")
            X = at(e)
            f.circle(X, ay, 5, "a fa")
            if e:
                f.text(X, ay - 10, f"{e:,}", "ta", 10.5, "middle" if 60 < X < 580 else ("start" if X <= 60 else "end"),
                       700)
    steps.check(f.svg())
    return f


def sizes0901():
    rows = bytes_table(sizes_run().out)
    page = bytes_table(bpe_run().out)
    if rows[:len(page)] != page:
        raise SystemExit(f"the longer run's first rows are not the page's: {rows} {page}")
    f = Fig("sizes0901", "Bytes per token against the size of the vocabulary, on the training text the merges were "
                         "learned from and on the test text: the later merges are the training plays' own words, so "
                         "the gap grows", 300)
    sizes = [r[0] for r in rows]
    series = [figart.Series("training text", sizes, [r[1] for r in rows], "s"),
              figart.Series("test text", sizes, [r[2] for r in rows], "a")]
    ax = figart.plot(f, (10, 8, 620, 284), series, xlabel="symbols in the vocabulary (256 bytes and the merges)",
                     ylabel="bytes per token", logx=True, xticks=sizes, xfmt=lambda v: f"{int(round(v)):,}",
                     xlim=(sizes[0], sizes[-1]), ylim=(0.9, 3.8), yticks=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5], legend="top")
    for v, a, b in rows:
        ax.dot(v, a, "s f", 3)
        ax.dot(v, b, "a fa", 3)
        if v > 256:
            ax.note(v, a, f"{a:.2f}", "t", 10, "middle", dy=-9)
            ax.note(v, b, f"{b:.2f}", "ta", 10, "middle", dy=16)
    last = page[-1][0]
    ax.vline(last, f"the page's run stops at {last:,}", "m")
    return f


def bits0901():
    r = bpe_run()
    chars = [figart.summary(x)["test_bits"] for x in figart.seed_dirs(os.path.join(r.runs, "characters"))]
    toks = [figart.summary(x)["test_bits"] for x in figart.seed_dirs(os.path.join(r.runs, "bpe2048"))]
    reads = [int(m.group(1).replace(",", "")) for m in re.finditer(r"a step reads ([\d,]+) characters", r.out)]
    f = Fig("bits0901", "08.04's GPT for 300 steps on characters and on BPE tokens of 2,048, both scored in bits per "
                        "character of the test text (a ring per seed); and how much of the text one step reads", 290)
    figart.seeds_chart(f, (8, 4, 330, 280), [("characters\n65 symbols", chars, "s"),
                                             ("BPE tokens\n2,048 symbols", toks, "a")],
                       ylabel="bits per character, test text", ylim=(2.5, 3.5), yticks=[2.6, 2.8, 3.0, 3.2, 3.4])
    x0, y0 = 380, 40
    f.text(x0, 26, "characters one step reads", "tm", 11.5)
    f.text(x0, y0 + 14, "32 windows of 64 symbols:", "tm", 10.5)
    top = max(reads)
    for k, (label, v, cls, tcls) in enumerate((("characters", reads[0], "s fs", "t"), ("BPE tokens", reads[1], "a af", "ta"))):
        y = y0 + 34 + k * 64
        f.text(x0, y, label, tcls, 11.5, weight=600)
        f.rect(x0, y + 8, 180 * v / top, 24, cls, 2)
        f.text(x0 + 180 * v / top + 6, y + 25, f"{v:,}", tcls, 11, mono=True)
    f.text(x0, y0 + 180, f"A window of 64 tokens is about {reads[1] / 32 / 1:,.0f} characters", "tm", 10.5)
    f.text(x0, y0 + 195, "of the text: at equal steps the tokens", "tm", 10.5)
    f.text(x0, y0 + 210, f"see {reads[1] / reads[0]:.1f} times as much.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 09.02

TOK_CODE = """
import json, unicodedata
from experiments import tokenizer as E
from tokens import bpe, gpt2
tok = gpt2.load()
symbols = gpt2.byte_symbols()
s = E.SENTENCE
print(json.dumps({"symbols": [ord(c) for c in symbols], "first": tok.first, "sentence": s,
                  "pieces": [[p, tok.encode(p)] for p in gpt2.split(s)], "ids": tok.encode(s), "bpe": bpe.pieces(s)}))
"""


def tok_data():
    d = in_project("09.02", TOK_CODE)
    if [i for _, ids in d["pieces"] for i in ids] != d["ids"]:
        raise SystemExit("the pieces' ids, one piece at a time, are not the sentence's")
    printed = re.search(r"GPT-2's pattern: +(.*)$", tok_run().out, re.M).group(1)
    if printed != " ".join(ascii(p) for p, _ in d["pieces"]):
        raise SystemExit(f"the pieces here are not the run's:\n{printed}")
    return d


def bytes0902():
    d = tok_data()
    sym, first = d["symbols"], d["first"]
    moved = [b for b in range(256) if sym[b] != b]
    f = Fig("bytes0902", f"GPT-2's 256 byte symbols: the {256 - len(moved)} bytes that are printable characters stand "
                         f"for themselves; the other {len(moved)} (in the accent) are written as the characters "
                         f"U+{min(sym[b] for b in moved):04X} to U+{max(sym[b] for b in moved):04X}, in byte order", 420)
    x0, y0, c = 46, 40, 21
    f.text(x0, 22, "a byte's value in hex: row is its first digit, column its second", "tm", 10.5)
    for k in range(16):
        f.text(x0 + k * c + c / 2, y0 - 5, f"{k:x}", "tm", 10, "middle", mono=True)
        f.text(x0 - 6, y0 + k * c + 14, f"{k:x}_", "tm", 10, "end", mono=True)
    for b in range(256):
        X, Y = x0 + (b % 16) * c, y0 + (b // 16) * c
        hot = b in moved
        f.rect(X, Y, c, c, "a af" if hot else "s f", 0, sw=False)
        label = chr(b) if 33 <= b < 127 else f"{b:02x}"
        f.text(X + c / 2, Y + 14, label, "ta" if hot else ("t" if 33 <= b < 127 else "tm"),
               10 if 33 <= b < 127 else 8.5, "middle", 700 if hot else None, mono=True)
    for k in range(17):
        f.line(x0 + k * c, y0, x0 + k * c, y0 + 16 * c, "m")
        f.line(x0, y0 + k * c, x0 + 16 * c, y0 + k * c, "m")
    rx = 410
    f.text(rx, 52, "printable: written as itself", "t", 11.5, weight=600)
    f.text(rx, 68, "! to ~, and 0xa1 to 0xff but 0xad,", "tm", 10.5)
    f.text(rx, 82, "read as Latin-1 (hex shown here)", "tm", 10.5)
    f.text(rx, 112, f"the other {len(moved)}: U+0100 + n", "ta", 11.5, weight=700)
    f.text(rx, 128, "n counts them in byte order:", "tm", 10.5)
    for i, (b, name) in enumerate(((0x00, "NUL"), (0x09, "a tab"), (0x0A, "a line break"), (0x20, "a space"),
                                   (0x7F, "DEL"), (0xAD, "a soft hyphen"))):
        y = 150 + i * 19
        f.text(rx, y, f"0x{b:02x} -> U+{sym[b]:04X}", "ta", 11, mono=True)
        f.text(rx + 132, y, name, "tm", 10.5)
    f.text(rx, 284, "vocab.json numbers the 256 symbols", "t", 11.5, weight=600)
    f.text(rx, 300, "in its own order, not the bytes':", "tm", 10.5)
    for i, b in enumerate((0x21, 0x41, 0x61, 0x20, 0x0A)):
        y = 320 + i * 17
        f.text(rx, y, f"0x{b:02x} " + (f"({chr(b)!r})" if 32 < b < 127 else {0x20: "(space)", 0x0A: "(\\n)"}[b]), "t",
               10.5, mono=True)
        f.text(rx + 110, y, f"id {first[b]}", "ta" if first[b] != b else "t", 10.5, mono=True)
    f.text(x0 - 30, y0 + 16 * c + 24, "Why: the files are text, and a space or a control byte written as itself would "
                                      "break a line or vanish.", "tm", 10.5)
    return f


KINDS = [("contraction", "a af", "ta"), ("letters", "s f", "t"), ("numbers", "s fs", "t"), ("other marks", "m fs", "t"),
         ("spaces", "m f", "tm")]
DASHED = {2, 4}                                  # numbers and spaces: a dashed border


def kind(p):
    if p in ("'s", "'t", "'re", "'ve", "'m", "'ll", "'d"):
        return 0
    if not p.strip():
        return 4
    c = unicodedata.category(p.lstrip(" ")[0])[0]
    return 1 if c == "L" else 2 if c == "N" else 3


def pieces0902():
    d = tok_data()
    f = Fig("pieces0902", "GPT-2's pattern cutting the run's sentence into pieces, by kind, and each piece into its "
                          "ids; below, 09.01's pattern (re's \\w) on the same sentence, its pieces that GPT-2 does not "
                          "make in the accent", 262)
    x = 20
    for name, cls, tcls in KINDS:
        f.rect(x, 12, 14, 12, cls, 2, dash=KINDS.index((name, cls, tcls)) in DASHED)
        f.text(x + 19, 22, name, "tm", 10.5)
        x += 19 + tw(name, 10.5) + 16
    f.text(620, 22, "_ is a space", "tm", 10.5, "end")
    x, y = 20, 40
    for p, ids in d["pieces"]:
        s = shown(p)
        idt = " ".join(str(i) for i in ids)
        w = max(tw(s, 11.5, True) + 12, tw(idt, 9.5, True) + 6, 20)
        if x + w > 624:
            x, y = 20, y + 56
        name, cls, tcls = KINDS[kind(p)]
        f.rect(x, y, w, 24, cls, 3, dash=kind(p) in DASHED)
        f.text(x + w / 2, y + 16, s, tcls, 11.5, "middle", 700 if kind(p) == 0 else None, mono=True)
        f.text(x + w / 2, y + 38, idt, "ta", 9.5, "middle", mono=True)
        x += w + 4
    y += 70
    f.text(20, y, "09.01's pattern, with re's \\w: letters, digits and _ are one kind; no contractions; the spaces not "
                  "left to the next word", "tm", 10.5)
    gpt = [p for p, _ in d["pieces"]]
    x, y = 20, y + 10
    for p in d["bpe"]:
        s = shown(p)
        w = max(tw(s, 10.5, True) + 10, 18)
        if x + w > 624:
            x, y = 20, y + 28
        odd = p not in gpt
        f.rect(x, y, w, 21, "a af" if odd else "m f", 3)
        f.text(x + w / 2, y + 14.5, s, "ta" if odd else "tm", 10.5, "middle", 700 if odd else None, mono=True)
        x += w + 4
    return f


UNICODE_CODE = """
import json, unicodedata
import tiktoken
from tiktoken.load import data_gym_to_mergeable_bpe_ranks
from tiktoken_ext.openai_public import r50k_pat_str
from data import fetch
from tokens import gpt2
tok = gpt2.load()
ranks = data_gym_to_mergeable_bpe_ranks(fetch.path("gpt2", "merges.txt"), fetch.path("gpt2", "vocab.json"))
enc = tiktoken.Encoding("gpt2, from the fetched files", pat_str=r50k_pat_str, mergeable_ranks=ranks, special_tokens={})
c = chr(0x1C89)
s = c + "'s"
unassigned = [chr(i) for i in range(0x40000) if not 0xD800 <= i <= 0xDFFF and unicodedata.category(chr(i)) == "Cn"]
differ = []
for k in range(0, len(unassigned), 2000):
    chunk = unassigned[k:k + 2000]
    joined = chr(10).join(ch + "'s" for ch in chunk)
    if tok.encode(joined) != enc.encode_ordinary(joined):
        differ += [ch for ch in chunk if tok.encode(ch + "'s") != enc.encode_ordinary(ch + "'s")]
contexts = ["x{}", "{}x", " {}", "1{}", "{}1", "'{}", " {}!"]
others = sum(tok.encode(ctx.format(ch)) != enc.encode_ordinary(ctx.format(ch)) for ch in differ for ctx in contexts)
theirs = enc.encode_ordinary(s)
print(json.dumps({"version": unicodedata.unidata_version, "tiktoken": tiktoken.__version__,
                  "category": unicodedata.category(c), "ours": [[p, tok.encode(p)] for p in gpt2.split(s)],
                  "theirs": theirs, "theirs_bytes": [enc.decode_single_token_bytes(t).hex() for t in theirs],
                  "unassigned": len(unassigned), "differ": len(differ), "first": ord(differ[0]), "last": ord(differ[-1]),
                  "contexts": contexts, "others": int(others),
                  "same_rule": all(enc.encode_ordinary(ch + "'s") == tok.encode(ch) + tok.encode("'s") for ch in differ)}))
"""


def newer_unicode(cp):
    """(the Unicode version, cp's category, its name) in the newest python3.1x on PATH with a newer unicodedata
    than this one's; None when there is none."""
    for exe in ("python3.14", "python3.13"):
        path = shutil.which(exe)
        if not path:
            continue
        r = subprocess.run([path, "-I", "-c", f"import unicodedata as u; c = chr({cp}); "
                                              f"print(u.unidata_version, u.category(c), u.name(c, ''), sep='|')"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            version, cat, name = r.stdout.strip().split("|")
            if version != unicodedata.unidata_version:
                return version, cat, name
    return None


def unicode0902():
    d = in_project("09.02", UNICODE_CODE)
    if not d["same_rule"] or d["others"]:
        raise SystemExit(f"tiktoken differs another way than NOTES.md says: {d}")
    newer = newer_unicode(0x1C89)
    out = tok_run().out
    printed = re.search(r'^   "\\u1c89\'s" +(\[[\d, ]+\])', out, re.M).group(1)
    ours_ids = [i for _, ids in d["ours"] for i in ids]
    if json.loads(printed) != ours_ids:
        raise SystemExit(f"the run printed {printed} for U+1C89's, this {ours_ids}")
    f = Fig("unicode0902", f"Where the ids part from tiktoken's: U+1C89, a letter Unicode added in version 16.0, before "
                           f"'s. This Python's unicodedata ({d['version']}) does not know it, so the pattern cuts it "
                           f"with the apostrophe; tiktoken cuts it as a letter", 372)
    rows = [(f"this project: Python's unicodedata {d['version']}",
             f"U+1C89 is {d['category']}, unassigned: not a letter, so 'other marks'",
             [(p.encode().hex(" "), ids, shown(p)) for p, ids in d["ours"]], "s f", "t"),
            (f"tiktoken {d['tiktoken']}, built from the same two files",
             "a letter to it" + (f" (Unicode {newer[0]}: {newer[1]}, {newer[2].lower()})" if newer else ""),
             [], "a af", "ta")]
    tb = d["theirs_bytes"]
    pieces, cur, ids = [], "", []
    for t, h in zip(d["theirs"], tb):
        cur += h
        ids.append(t)
        if h in ("89", "2773"):                     # the end of U+1C89's bytes (e1 b2 89), and 's
            pieces.append((" ".join(cur[i:i + 2] for i in range(0, len(cur), 2)), ids, None))
            cur, ids = "", []
    if cur:
        pieces.append((" ".join(cur[i:i + 2] for i in range(0, len(cur), 2)), ids, None))
    rows[1] = rows[1][:2] + ([(b, i, shown(bytes.fromhex(b.replace(" ", "")).decode("utf-8"))) for b, i, _ in pieces],) \
        + rows[1][3:]
    for r, (who, why, ps, cls, tcls) in enumerate(rows):
        y = 34 + r * 116
        f.text(20, y, who, tcls, 12, weight=700)
        f.text(20, y + 16, why, "tm", 10.5)
        x = 20
        for b, ids, s in ps:
            idt = "ids " + " ".join(map(str, ids))
            w = max(tw("bytes " + b, 10, True), tw(idt, 10.5, True)) + 24
            f.rect(x, y + 28, w, 26, cls, 4)
            f.text(x + w / 2, y + 45, s, tcls, 11.5, "middle", 700, mono=True)
            f.text(x + w / 2, y + 70, "bytes " + b, "tm", 10, "middle", mono=True)
            f.text(x + w / 2, y + 86, idt, tcls, 10.5, "middle", 600, mono=True)
            x += w + 10
        total = [i for _, ids, _ in ps for i in ids]
        f.text(x + 20, y + 45, f"= [{', '.join(map(str, total))}]", tcls, 12, weight=700, mono=True)
    y = 276
    n, k = d["unassigned"], d["differ"]
    f.text(20, y, f"Every code point unassigned in Unicode {d['version']}, planes 0 to 3: {n:,}. Before 's, "
                  f"{k:,} give other ids than tiktoken's,", "t", 10.5)
    f.text(20, y + 15, f"U+{d['first']:04X} to U+{d['last']:04X}: the letters and numbers newer Unicode added; in each, "
                       f"tiktoken's ids are ours for the character", "t", 10.5)
    f.text(20, y + 30, f"alone, then ours for 's. In {len(d['contexts'])} other places (after x, a space or a digit; "
                       f"before x or a digit; ...) all {k:,} give the same ids.", "t", 10.5)
    W = 600
    f.rect(20, y + 44, W, 14, "s fs", 0)
    f.rect(20, y + 44, max(1.5, W * k / n), 14, "a af", 0)
    f.text(20, y + 74, f"{100 * k / n:.1f}% of them; everything else the project encodes gives exactly tiktoken's ids. "
                       f"A newer Python's tables close the gap.", "tm", 10.5)
    return f


def compress0902():
    out = tok_run().out
    part = out.split("4. Bytes per token")[1].split("\n\n")[0]
    rows = [(m.group(1), float(m.group(2)), float(m.group(3)))
            for m in re.finditer(r"^   (training text|test text) +(\d\.\d{3}) +(\d\.\d{3})$", part, re.M)]
    gpt2_n = re.search(r"GPT-2 \(([\d,]+)\)", part).group(1)
    ours_n = re.search(r"09\.01's \(([\d,]+),", part).group(1)
    f = Fig("compress0902", f"Bytes per token on Tiny Shakespeare: GPT-2's {gpt2_n} symbols, learned on web pages, "
                            f"against 09.01's {ours_n}, learned on the training text", 200)
    x0, W, lo, hi = 230, 330, 2.5, 3.5
    f.text(x0, 20, "bytes per token (the axis starts at 2.5)", "tm", 10.5)
    for t in (2.5, 3.0, 3.5):
        X = x0 + W * (t - lo) / (hi - lo)
        f.line(X, 28, X, 176, "m", dash=True)
        f.text(X, 190, f"{t}", "tm", 10, "middle", mono=True)
    for k, (name, g, o) in enumerate(rows):
        y = 36 + k * 74
        f.text(20, y + 26, f"the {name}", "t", 12, weight=700)
        for j, (who, v, cls, tcls) in enumerate(((f"GPT-2 ({gpt2_n})", g, "a af", "ta"),
                                                 (f"09.01's ({ours_n})", o, "s fs", "t"))):
            Y = y + j * 28
            f.text(x0 - 8, Y + 15, who, tcls, 10.5, "end")
            f.rect(x0, Y + 2, W * (v - lo) / (hi - lo), 20, cls, 2)
            f.text(x0 + W * (v - lo) / (hi - lo) + 6, Y + 16, f"{v:.3f}", tcls, 11, mono=True)
        f.text(620, y + 26, f"+{100 * (g / o - 1):.0f}%", "ta", 12, "end", 700)
    return f


# ------------------------------------------------------------------ 09.03

NAMES_CODE = """
import json
from data import fetch
from lab import safetensors
from models.gpt import GPT
from models.gpt2 import CONFIG
header, n = safetensors.read_header(fetch.path("gpt2", "model.safetensors"))
header.pop("__metadata__", None)
model = GPT(**CONFIG)
print(json.dumps({"theirs": {k: v["shape"] for k, v in header.items()}, "dtypes": sorted({v["dtype"] for v in header.values()}),
                  "ours": {k: list(v.shape) for k, v in model.state_dict().items()},
                  "count": sum(p.numel() for p in model.parameters())}))
"""


def names0903():
    d = in_project("09.03", NAMES_CODE)
    T, O = d["theirs"], d["ours"]
    out = gpt2_run().out
    if f"{len(T)} tensors read from its file, {d['count']:,} weights" not in out:
        raise SystemExit("the file's tensors or the weight count are not the run's")
    rows = [  # theirs, ours, how, style
        (["wte.weight"], ["tokens.weight"], "as is", "s"),
        (["wpe.weight"], ["positions.weight"], "as is", "s"),
        (["h.0.ln_1.weight"], ["blocks.0.norm1.weight"], "as is (and .bias)", "s"),
        (["h.0.attn.c_attn.weight"], ["blocks.0.attention.query.weight", "blocks.0.attention.key.weight",
                                      "blocks.0.attention.value.weight"], "thirds, each transposed", "a"),
        (["h.0.attn.c_attn.bias"], ["blocks.0.attention.query.bias"], "thirds (key, value too)", "s"),
        (["h.0.attn.c_proj.weight"], ["blocks.0.attention.out.weight"], "transposed: square!", "a"),
        (["h.0.ln_2.weight"], ["blocks.0.norm2.weight"], "as is (and .bias)", "s"),
        (["h.0.mlp.c_fc.weight"], ["blocks.0.mlp.up.weight"], "transposed", "a"),
        (["h.0.mlp.c_proj.weight"], ["blocks.0.mlp.down.weight"], "transposed", "a"),
        (["ln_f.weight"], ["norm.weight"], "as is (and .bias)", "s"),
        (["h.0.attn.bias"], [], "left out: the causal mask", "m"),
    ]
    for theirs, ours, _, _ in rows:
        for k in theirs:
            assert k in T, k
        for k in ours:
            assert k in O, k
    f = Fig("names0903", f"GPT-2's checkpoint beside the GPT of module 08, for block i of 12: the file's names and "
                         f"shapes, ours, and the weights that must be transposed (in the accent)", 470)
    xl, xr = 20, 382
    f.text(xl, 20, f"model.safetensors: {len(T)} tensors, {', '.join(d['dtypes'])}", "t", 11.5, weight=700)
    f.text(xr, 20, "models/gpt.py's GPT(**CONFIG)", "t", 11.5, weight=700)
    y = 36
    for theirs, ours, how, style in rows:
        h = 30 + 15 * max(0, len(ours) - 1)
        tcls = {"a": "ta", "s": "t", "m": "tm"}[style]
        name = theirs[0].replace("h.0.", "h.i.")
        f.text(xl, y + 13, name, tcls, 10.5, weight=600 if style == "a" else None, mono=True)
        f.text(xl, y + 26, str(T[theirs[0]]), "tm", 10, mono=True)
        mid = y + 10 + 7.5 * max(0, len(ours) - 1)
        if ours:
            f.line(242, mid, xr - 10, mid, style, arrow=True, dash=style == "m")
            f.text((242 + xr) / 2, mid - 5, how, tcls, 10, "middle", 600 if style == "a" else None)
            for j, k in enumerate(ours):
                f.text(xr, y + 13 + 15 * j, k.replace("blocks.0.", "blocks.i."), tcls, 10.5,
                       weight=600 if style == "a" else None, mono=True)
            f.text(xr, y + 26 + 15 * (len(ours) - 1), str(O[ours[0]]) + (" each" if len(ours) > 1 else ""), "tm", 10,
                   mono=True)
        else:
            f.line(242, mid, xr - 10, mid, "m", dash=True)
            f.text((242 + xr) / 2, mid - 5, how, "tm", 10, "middle")
            f.text(xr, y + 13, "(none: GPT makes its mask itself)", "tm", 10)
        y += h
    f.text(xl, y + 14, "The file keeps a weight as (inputs, outputs) and computes x @ W + b (OpenAI's conv1d, "
                       "transformers' Conv1D);", "tm", 10.5)
    f.text(xl, y + 29, "nn.Linear keeps (outputs, inputs) and computes x @ W.T + b. A non-square weight left as it is "
                       "is refused", "tm", 10.5)
    f.text(xl, y + 44, f"by load_state_dict (size mismatch); the square attn.c_proj loads without a word. "
                       f"{d['count']:,} weights, wte counted once.", "tm", 10.5)
    return f


EXPECTS_CODE = """
import json
import torch
import torch.nn.functional as F
from data import fetch
from lab import safetensors
from models.gpt import GPT
from models.gpt2 import CONFIG, from_gpt2
from tokens import gpt2
tok = gpt2.load()
tensors = safetensors.load_file(fetch.path("gpt2", "model.safetensors"))
model = GPT(**CONFIG).eval()
out = {}
for label in ("right", "wrong"):
    weights = from_gpt2(tensors, 12, 768)
    if label == "wrong":
        for i in range(12):
            weights[f"blocks.{i}.attention.out.weight"] = tensors[f"h.{i}.attn.c_proj.weight"]
    model.load_state_dict({k: torch.from_numpy(v) for k, v in weights.items()})
    with torch.no_grad():
        p = F.softmax(model(torch.tensor([tok.encode("The meaning of life is")]))[0, -1], dim=-1)
    top = p.topk(8)
    out[label] = [[tok.decode([int(i)]), float(v)] for v, i in zip(top.values, top.indices)]
print(json.dumps(out))
"""


def expects0903():
    d = in_project("09.03", EXPECTS_CODE)
    printed = re.search(r"its 5 likeliest next tokens:\n   (.*)$", gpt2_run().out, re.M).group(1)
    mine = "   ".join(f"{t!r} {p:.3f}" for t, p in d["right"][:5])
    if printed != mine:
        raise SystemExit(f"the next tokens here are not the run's:\n{printed}\n{mine}")
    f = Fig("expects0903", "After 'The meaning of life is', GPT-2's eight likeliest next tokens: loaded right, and "
                           "with the square attn.c_proj of every block left as the file has it", 250)
    top = max(p for k in d for _, p in d[k])
    for k, (label, note, cls, tcls) in enumerate((("right", "loaded right (transposed)", "a af", "ta"),
                                                  ("wrong", "attn.c_proj left as it is: it loads, no complaint", "s fs",
                                                   "t"))):
        x0 = 20 + k * 312
        f.text(x0, 22, note, tcls, 11.5, weight=700)
        for i, (t, p) in enumerate(d[label]):
            y = 36 + i * 24
            s = shown(t, " ")
            f.text(x0 + 92, y + 14, f"'{s}'" if "'" not in s else f'"{s}"', tcls, 11, "end", mono=True)
            f.rect(x0 + 98, y + 3, max(1.5, 170 * p / top), 16, cls, 2)
            f.text(x0 + 104 + 170 * p / top, y + 15, f"{p:.3f}", tcls, 10.5, mono=True)
    f.text(20, 240, "Chances after the softmax, on one scale for both. Loaded wrong, the model still writes, and "
                    "still says words; it has lost the sense.", "tm", 10.5)
    return f


def ladder0903():
    out = gpt2_run().out
    part = out.split("Beside the track's own models")[1].split("\n\n")[0]
    rows = [(m.group(1).strip(), float(m.group(2))) for m in re.finditer(r"^   (.+?) +(\d\.\d{3})$", part, re.M)]
    if len(rows) != 7:
        raise SystemExit(f"gpt2: expected 7 rows on the ladder, read {rows}")
    f = Fig("ladder0903", "Bits per character on Tiny Shakespeare's test text: modules 07 and 08's ladder, each "
                          "trained here on the training plays, and GPT-2 small, trained by OpenAI on web pages and "
                          "never by us on this text", 18 * 7 + 90)
    x0, x1 = 330, 600
    lo, hi = 1.6, 3.8
    ax = figart.Axes(f, x0, 30, x1 - x0, 18 * 7 + 12, (lo, hi), (7, 0))
    ax.draw(xticks=[1.8, 2.2, 2.6, 3.0, 3.4, 3.8], yticks=[], xlabel="bits per character on the test text")
    for i, (name, b) in enumerate(rows):
        y = ax.y + 14 + i * 18
        gpt2 = name.startswith("GPT-2")
        f.text(x0 - 8, y + 4, name, "ta" if gpt2 else "t", 10.5, "end", 700 if gpt2 else None)
        if b > hi:
            f.line(x1 - 30, y, x1 - 4, y, "m", arrow=True)
            f.text(x1 - 34, y + 4, f"{b:.3f}", "tm", 9.5, "end", mono=True)
            continue
        f.circle(ax.px(b), y, 4 if gpt2 else 3.5, "a fa" if gpt2 else "s fs")
        f.text(ax.px(b) + 9, y + 4, f"{b:.3f}", "ta" if gpt2 else "t", 10, weight=700 if gpt2 else None, mono=True)
    return f


def sampling0903():
    r = gpt2_run()
    table = r.out.split("\n   Prompt 1")[0]
    names = [m.group(1) for m in re.finditer(r"^   ((?:greedy|pure sampling|sampling, t=\S+|top-k=\S+|nucleus, p=\S+)) ",
                                             table, re.M)]
    if len(names) != 6:
        raise SystemExit(f"gpt2: expected 6 ways in the table, read {names}")
    groups = []
    for name in names:
        label = name.replace(", ", "-").replace("=", "").replace(" ", "_")
        s = figart.summary(os.path.join(r.runs, label, "seed0"))
        groups.append((f"{name}\nloops {mean(s['repetition']):.0f}%", s["perplexity"],
                       "a" if name.startswith("nucleus") else "s"))
    text = figart.summary(os.path.join(r.runs, "text", "seed0"))["perplexity"][0]
    n = re.search(r"^4\. (\d+) prompts of (\d+) tokens", r.out, re.M)
    length = re.search(r"\), (\d+) tokens after each", r.out).group(1)
    f = Fig("sampling0903", f"Perplexity of what each way of choosing wrote with GPT-2 small, to GPT-2 itself, beside "
                            f"the real text after the same {n.group(1)} prompts of {n.group(2)} tokens ({length} tokens "
                            f"each; the dashed line): a ring per seed, the bar their mean; and the passages that end "
                            f"in a loop", 310)
    ax = figart.seeds_chart(f, (8, 4, 624, 300), groups, ylabel="perplexity, 2 to the bits per token",
                            ylim=(0, 72), yticks=[0, 10, 20, 30, 40, 50, 60, 70])
    ax.hline(text, f"the real text: {sig(text, 4)}", cls="s", side="right")
    return f


MEMORY_CODE = """
import json, os, resource, sys
from data import fetch
from lab import safetensors
unit = 1 if sys.platform == "darwin" else 1024
path = fetch.path("gpt2", "model.safetensors")
before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit
got = safetensors.load_file(path)
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * unit
print(json.dumps({"file": os.path.getsize(path), "arrays": sum(a.nbytes for a in got.values()), "before": before,
                  "peak": peak}))
"""


def memory0903():
    old, new = in_project("09.02", MEMORY_CODE), in_project("09.03", MEMORY_CODE)
    mb = 1e6
    f = Fig("memory0903", "Reading GPT-2's 548 MB file in a fresh python: the most memory the process held at once, "
                          "with 02.05's load_file (the whole file read, then copied out twice) and with 09.03's (each "
                          "tensor read from the file straight into its own array)", 214)
    x0, W = 210, 300
    top = max(old["peak"], new["peak"]) / mb
    rows = [("the file on disk", old["file"] / mb, "m fs", "tm", ""),
            ("02.05's load_file", old["peak"] / mb, "s fs", "t", f"{old['peak'] / old['file']:.1f} times the file"),
            ("09.03's load_file", new["peak"] / mb, "a af", "ta", f"{new['peak'] / new['file']:.2f} times the file")]
    for k, (name, v, cls, tcls, note) in enumerate(rows):
        y = 26 + k * 46
        f.text(x0 - 10, y + 17, name, tcls, 11.5, "end", 700 if tcls == "ta" else None)
        f.rect(x0, y + 2, W * v / top, 24, cls, 2)
        f.text(x0 + W * v / top + 6, y + 18, f"{v:,.0f} MB", tcls, 11, mono=True)
        if note:
            f.text(x0 + W * v / top + 6, y + 33, note, "tm", 10)
    f.text(20, 178, f"The peak of the whole process (ru_maxrss), python and numpy included ({old['before'] / mb:.0f} MB "
                    f"before reading). The arrays are {new['arrays'] / mb:.0f} MB:", "tm", 10.5)
    f.text(20, 193, "the file less its header. 1 MB here is a million bytes.", "tm", 10.5)
    return f


# ------------------------------------------------------------------ 09.04

def recorded():
    return os.path.join(figlib.TRACK, "experiments", "recorded", "tinystories")


LENGTHS_CODE = """
import json
import numpy as np
from data import tinystories
ids = tinystories.tokens("train", 4096)
ends = np.flatnonzero(ids == 4095)
lengths = np.diff(np.concatenate([[-1], ends])) - 1
print(json.dumps({"n": len(lengths), "bins": np.bincount(np.minimum(lengths // 32, 32), minlength=33).tolist(),
                  "median": float(np.median(lengths)), "fit256": float((lengths + 1 <= 256).mean()),
                  "fit512": float((lengths + 1 <= 512).mean()), "longest": int(lengths.max()),
                  "p90": float(np.percentile(lengths, 90))}))
"""


def data0904():
    d = in_project("09.04", LENGTHS_CODE)
    if f"{d['n']:,} training stories" not in ts_run().out:
        raise SystemExit("the stories counted here are not the run's")
    bins = d["bins"]
    f = Fig("data0904", f"TinyStories' {d['n']:,} training stories by their length in tokens (09.01's byte pair encoding, "
                        f"4,096 symbols, learned on the first 10,000 stories): median {d['median']:.0f}; "
                        f"{100 * d['fit256']:.0f}% fit, with their END, in a window of 256", 282)
    x0, y0, W, H = 56, 30, 560, 180
    top = max(bins)
    ax = figart.Axes(f, x0, y0, W, H, (0, 33 * 32), (0, top * 1.08))
    yt = [t for t in figart.ticks(0, top * 1.08) if t <= top * 1.08]
    ax.draw(xticks=[0, 128, 256, 384, 512, 640, 768, 896, 1024], yticks=yt,
            xlabel="tokens in the story (the last bar: 1,024 or more)", ylabel="stories")
    for k, n in enumerate(bins):
        X0, X1 = ax.px(k * 32) + 1, ax.px((k + 1) * 32) - 1
        cls = "a af" if (k + 1) * 32 <= 256 else "s fs"
        f.rect(X0, ax.py(n), X1 - X0, ax.py(0) - ax.py(n), cls, 0, sw=False)
    X = ax.px(256)
    f.line(X, y0, X, y0 + H, "a", dash=True)
    f.text(X + 6, y0 + 14, "a window of 256: the long run's", "ta", 10.5)
    f.text(X + 6, y0 + 28, f"{100 * d['fit256']:.0f}% of stories fit whole; 512: {100 * d['fit512']:.0f}%", "ta", 10.5)
    f.text(x0, 272, f"In the accent the bins of stories shorter than 256 tokens. The longest story is "
                    f"{d['longest']:,} tokens; 90% are {d['p90']:.0f} or fewer.", "tm", 10.5)
    return f


def curves0904():
    d = recorded()
    dirs = figart.seed_dirs(d)
    f = Fig("curves0904", "The recorded long run: bits per token of the training batch (dashed) and of 64 held-out "
                          "windows (solid), every 250 steps, two seeds; at step 0 both are 12.0, log2 of 4,096: every "
                          "symbol about equally likely", 300)
    rows = [figart.read_log(x) for x in dirs]
    ax = figart.Axes(f, 60, 34, 470, 210, (0, 4000), (2.6, 5.4))
    ax.draw(xticks=[0, 1000, 2000, 3000, 4000], yticks=[2.6, 3.0, 3.4, 3.8, 4.2, 4.6, 5.0, 5.4],
            xlabel="step (32 windows of 256 tokens each)", ylabel="bits per token")
    for k, r in enumerate(rows):
        xs, tr = figart.column(r, "bits")
        _, va = figart.column(r, "held_bits")
        ax.curve(xs, tr, "s" if k == 0 else "m", dash=True, width=1.5)
        ax.curve(xs, va, "a", width=2 if k == 0 else 1.5)
    for k, r in enumerate(rows):
        e = r[-1]
        f.text(538, ax.py(e["held_bits"]) + 4 + (8 if k else -4), f"seed {k}: {e['held_bits']:.3f}", "ta", 10)
    s = [figart.summary(x)["bits_per_byte"] for x in dirs]
    f.text(60, 290, f"Bits per byte on the first 2,000 held-out stories at the end: {s[0]:.4f} and {s[1]:.4f}. "
                    f"Step 0 (12.0) is off the scale.", "tm", 10.5)
    figart.legend(f, 280, 24, [("training batch", "s", True), ("held-out windows", "a", False)], across=True)
    return f


def copying0904():
    d = recorded()
    mine = figart.summary(os.path.join(d, "stories-trained-here", "seed0"))
    held = figart.summary(os.path.join(d, "stories-held-out", "seed0"))
    r = ts_run()
    page = figart.summary(os.path.join(r.runs, "stories-trained-here", "seed0"))
    page_held = figart.summary(os.path.join(r.runs, "stories-held-out", "seed0"))
    if page_held["copied"] != held["copied"][:len(page_held["copied"])]:
        raise SystemExit("the page's held-out stories are not the first of the long run's")
    cols = [(f"the page's model\n(1 minute): {len(page['copied'])} stories", page["copied"], "m"),
            (f"the long run's model\n(45 minutes): {len(mine['copied'])} stories", mine["copied"], "a"),
            (f"held-out stories\nno model saw: {len(held['copied'])}", held["copied"], "s")]
    f = Fig("copying0904", "The longest run of tokens each story shares with the 16.7 million training tokens (runs "
                           "under 8 count 0), a dot per story, the bar the median: the stories the models wrote, and "
                           "real stories no model trained on", 300)
    ax = figart.Axes(f, 60, 30, 560, 200, (-0.5, 2.5), (0, 25))
    ax.draw(xticks=[], yticks=[0, 5, 10, 15, 20, 25], ylabel="tokens in the longest shared run")
    for i, (label, vals, style) in enumerate(cols):
        X = ax.px(i)
        for k, line in enumerate(label.split("\n")):
            f.text(X, ax.y + ax.h + 16 + 14 * k, line, {"a": "ta", "s": "t", "m": "tm"}[style] if k == 0 else "tm",
                   11, "middle", 600 if style == "a" and k == 0 else None)
        seen = {}
        for v in vals:
            j = seen.get(v, 0)
            seen[v] = j + 1
            dx = (j // 2 + 1) * 8 * (1 if j % 2 else -1) if j else 0
            f.circle(X + dx, ax.py(v), 3.2, f"{style} f" if style != "a" else "a fa")
        m = median(vals)
        f.line(X - 40, ax.py(m), X + 40, ax.py(m), style if style != "m" else "s")
        f.text(X + 46, ax.py(m) + 4, f"median {m:g}", {"a": "ta", "s": "t", "m": "tm"}[style], 10.5)
    f.text(60, 292, "The long run's stories share shorter runs with the training text than unseen real stories "
                    "do.", "tm", 10.5)
    return f


def story0904():
    with open(os.path.join(recorded(), "output.txt")) as fh:
        out = fh.read()
    longest = re.search(r"; the longest: '(.*)'$", out.split("The model trained here")[1], re.M).group(1)
    held_longest = re.search(r"^   [\d, ]+ \(in words: [\d, ]+\); the longest: '(.*)'$", out, re.M).group(1)
    first = out.split("\n\n      ")[1].split("\n      [END]")[0].replace("\n      ", "\n")
    if not first.startswith(longest):
        raise SystemExit("the first story does not start with the longest shared run")
    s = figart.summary(os.path.join(recorded(), "stories-trained-here", "seed0"))
    h = figart.summary(os.path.join(recorded(), "stories-held-out", "seed0"))
    size, width = 10.5, 92
    lines = []
    for para in first.split("\n"):
        cur = ""
        for word in para.split(" "):
            if cur and len(cur) + 1 + len(word) > width:
                lines.append(cur)
                cur = word
            else:
                cur = (cur + " " + word) if cur else word
        lines.append(cur)
    f = Fig("story0904", f"The long run's first story as it wrote it (seed 0, temperature 1, ended by END after "
                         f"{s['words'][0]} words): in the accent, the longest run of tokens it shares with the training "
                         f"text, {s['copied'][0]} tokens; below, the longest a held-out story shares, {max(h['copied'])}",
            30 + 15 * len(lines) + 56)
    shared = len(longest)
    pos = 0
    y = 30
    f.rect(12, 14, 616, 18 + 15 * len(lines), "s fs", 6)
    for line in lines:
        a = max(0, min(len(line), shared - pos))
        parts = ([f'<tspan class="ta mono" font-weight="600">{figlib.esc(line[:a])}</tspan>'] if a else []) + \
            ([f'<tspan class="t mono">{figlib.esc(line[a:])}</tspan>'] if a < len(line) else [])
        f.add(f'<text class="t mono" x="22" y="{y}" font-size="{size}">{"".join(parts)}</text>')
        pos += len(line) + 1
        y += 15
    y += 22
    f.text(20, y, f"a held-out story's longest shared run, {max(h['copied'])} tokens:", "tm", 10.5)
    f.text(20, y + 16, held_longest, "t", 10.5, mono=True)
    return f


FIGS = [
    ("09.01-utf8", utf80901),
    ("09.01-unseen", unseen0901),
    ("09.01-merge", merge0901),
    ("09.01-sizes", sizes0901),
    ("09.01-bits", bits0901),
    ("09.02-bytes", bytes0902),
    ("09.02-pieces", pieces0902),
    ("09.02-unicode", unicode0902),
    ("09.02-compress", compress0902),
    ("09.03-names", names0903),
    ("09.03-memory", memory0903),
    ("09.03-expects", expects0903),
    ("09.03-ladder", ladder0903),
    ("09.03-sampling", sampling0903),
    ("09.04-data", data0904),
    ("09.04-curves", curves0904),
    ("09.04-copying", copying0904),
    ("09.04-story", story0904),
]


def main():
    only = sys.argv[1:]
    for name, fn in FIGS:
        if only and not any(name.startswith(o) for o in only):
            continue
        print(write(MOD, name, fn()))


if __name__ == "__main__":
    main()
