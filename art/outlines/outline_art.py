"""Module art for the two outline tracks, in the xv6 covers' visual language.

Writes outlines/<stem>/NN/cover.svg (640x300 teaching diagram) and icon.svg (20x20 line icon).
Reuses the Art helpers from the xv6 generator (tools/art.py): 1.5 stroke, classes
s m a (stroke), f fs af fa (fill), t tm ta (text), mono.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
from art import Art, SW, esc  # noqa: E402

OUTLINES = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch/outlines")


def poly(a, pts, cls="s", dash=False, arrow=False):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    a.path(d, cls, arrow=arrow, dash=dash)


def dot(a, x, y, r=3.5, cls="s f"):
    a.circle(round(x, 1), round(y, 1), r, cls)


# =================================================================== inference

def inf_workbench():
    a = Art("i00", "One generation, and the three numbers the benchmark harness measures")
    a.text(24, 30, "prompt", "tm", 11)
    a.box(24, 38, 120, 40, "s f", rx=8); a.text(84, 63, '"The cat sat"', size=12, anchor="middle", mono=True)
    a.line(144, 58, 178, 58, arrow=True)
    a.text(180, 30, "token ids", "tm", 11)
    a.box(180, 38, 148, 40, "s f", rx=8); a.text(254, 63, "[464, 3797, 3332]", size=12, anchor="middle", mono=True)
    a.line(328, 58, 362, 58, arrow=True)
    a.text(364, 30, "model", "tm", 11)
    a.box(364, 38, 120, 40, "s fs", rx=8); a.text(424, 56, "GPT-2", size=12.5, anchor="middle", weight=700)
    a.text(424, 71, "124M parameters", "tm", 10, "middle")
    a.line(484, 58, 518, 58, arrow=True)
    a.text(520, 30, "next token", "tm", 11)
    a.box(520, 38, 96, 40, "s f", rx=8); a.text(568, 63, '" on"  319', size=12, anchor="middle", mono=True)
    a.path("M568 78 V 96 H 254 V 82", "m", arrow=True, dash=True)
    a.text(411, 110, "append it, run again, until the stop token", "tm", 10.5, "middle")

    # one request on a time axis
    a.text(24, 146, "one request, measured", "tm", 11)
    y0, h = 158, 30
    a.box(40, y0, 152, h, "s fs", rx=6); a.text(116, y0 + 19, "prefill: whole prompt", size=11, anchor="middle")
    toks = ['" on"', '" the"', '" mat"', '"."']
    xs = [196 + i * 62 for i in range(4)]
    for x, t in zip(xs, toks):
        a.box(x, y0, 58, h, "s f", rx=6); a.text(x + 29, y0 + 19, t, size=11, anchor="middle", mono=True)
    a.text(450, y0 + 19, "...", "tm", 12)
    a.line(24, 208, 616, 208, "m", arrow=True); a.text(616, 224, "time", "tm", 10.5, "end")
    for x in (40, 192, 254, 316, 378, 440):
        a.line(x, 203, x, 213, "m")
    # brackets
    a.path("M40 230 V 236 H 192 V 230", "a"); a.text(116, 254, "TTFT", "ta", 11.5, "middle", 600, mono=True)
    a.text(116, 270, "time to first token", "tm", 10.5, "middle")
    a.path("M196 230 V 236 H 254 V 230", "s"); a.text(225, 254, "TPOT", size=11.5, anchor="middle", weight=600, mono=True)
    a.text(225, 270, "time per output token", "tm", 10.5, "middle")
    a.text(536, 254, "tokens/s", size=11.5, anchor="middle", weight=600, mono=True)
    a.text(536, 270, "tokens out / total time", "tm", 10.5, "middle")
    return a


def inf_forward():
    a = Art("i01", "GPT-2 small as arithmetic: embeddings, 12 blocks on a residual stream, and the output head")
    ys = 168
    a.text(68, 142, "ids  [T]", "tm", 10.5, "middle", mono=True)
    a.box(24, 148, 88, 40, "s f", rx=8); a.text(68, 172, "wte + wpe", size=11, anchor="middle", mono=True)
    # block frame
    a.box(132, 44, 376, 178, "m", rx=12, dash=True)
    a.text(146, 66, "block", size=12, weight=700); a.text(186, 66, "x 12", "tm", 11, mono=True)
    # residual stream
    a.line(112, ys, 526, ys, "a", arrow=True)
    for bx, name, sub, w in ((150, "attention", "12 heads, causal", 96), (330, "MLP", "4x wider, GELU", 96)):
        a.path(f"M{bx} {ys} V 104 H {bx + 10}", "s")
        a.box(bx + 10, 92, 34, 24, "s f", rx=6); a.text(bx + 27, 108, "ln", size=11, anchor="middle", mono=True)
        a.line(bx + 44, 104, bx + 54, 104, "s")
        a.box(bx + 54, 84, w, 40, "s fs", rx=8)
        a.text(bx + 54 + w / 2, 101, name, size=12, anchor="middle", weight=700)
        a.text(bx + 54 + w / 2, 116, sub, "tm", 10, "middle")
        px = bx + 54 + w + 12
        a.path(f"M{bx + 54 + w} 104 H {px} V {ys - 10}", "s", arrow=True)
        a.circle(px, ys, 9, "s f")
        a.path(f"M{px - 4.5} {ys} H {px + 4.5} M{px} {ys - 4.5} V {ys + 4.5}", "s")
    a.text(232, 196, "residual stream  x: [T, 768]", "ta", 11, "middle", 600, mono=True)
    # head
    a.box(528, 148, 88, 40, "s f", rx=8); a.text(572, 166, "ln_f", size=11, anchor="middle", mono=True)
    a.text(572, 181, "@ wte.T", "tm", 10.5, "middle", mono=True)
    a.text(572, 208, "logits", size=12, anchor="middle", weight=700)
    a.text(572, 224, "[T, 50257]", "tm", 10.5, "middle", mono=True)
    a.text(24, 256, "attention = softmax(q k.T / sqrt(64) + mask) v, 12 heads of 64 dims", "tm", 10.5, mono=True)
    a.text(24, 276, "MLP: 768 -> 3072 -> 768;  the head reuses wte (tied weights)", "tm", 10.5, mono=True)
    return a


def inf_kv():
    a = Art("i02", "The KV cache: for each new token, compute one row of q, k, v and reuse every earlier k and v")
    toks = ["The", "cat", "sat", "on", "the", "mat"]
    weights = [".04", ".31", ".09", ".06", ".12", ".38"]
    ry = [52 + i * 30 for i in range(6)]
    mid = (ry[0] + ry[-1] + 24) / 2
    a.text(64, mid - 22, "new token", "ta", 10.5, "middle")
    a.box(24, mid - 14, 80, 28, "a af", rx=6); a.text(64, mid + 5, "q(mat)", "ta", 12, "middle", 600, mono=True)
    a.text(226, 40, "K cache", size=12, anchor="middle", weight=700)
    a.text(322, 40, "softmax", "tm", 11, "middle")
    a.text(418, 40, "V cache", size=12, anchor="middle", weight=700)
    a.text(560, mid - 22, "weighted sum", "tm", 10.5, "middle")
    for i, (y, t, w) in enumerate(zip(ry, toks, weights)):
        new = i == len(toks) - 1
        cls, tcl = ("a af", "ta") if new else ("s fs", "t")
        a.line(104, mid, 176, y + 12, "m")
        a.box(176, y, 100, 24, cls, rx=5); a.text(226, y + 16, f"k({t})", tcl, 11.5, "middle", mono=True)
        a.line(276, y + 12, 300, y + 12, "m")
        a.box(300, y, 44, 24, "m f", rx=5); a.text(322, y + 16, w, "tm", 10.5, "middle", mono=True)
        a.line(344, y + 12, 368, y + 12, "m")
        a.box(368, y, 100, 24, cls, rx=5); a.text(418, y + 16, f"v({t})", tcl, 11.5, "middle", mono=True)
        a.line(468, y + 12, 520, mid, "m")
    a.box(520, mid - 14, 80, 28, "s f", rx=6); a.text(560, mid + 5, "out(mat)", size=12, anchor="middle", mono=True)
    a.add(f'<rect class="s fs" x="24" y="244" width="12" height="12" rx="3" {SW}/>')
    a.text(42, 254, "reused from earlier steps", "tm", 11)
    a.add(f'<rect class="a af" x="196" y="244" width="12" height="12" rx="3" {SW}/>')
    a.text(214, 254, "computed now, then appended to the cache", "tm", 11)
    a.text(24, 280, "size: 2 x 12 layers x 768 x 4 bytes = 72 KiB per token (GPT-2 small, fp32)", "tm", 10.5, mono=True)
    return a


def inf_quant():
    a = Art("i03", "8-bit quantisation: a scale maps each float weight onto a grid of 255 integers")
    X = lambda v, lim: 320 + v * 260 / lim
    a.text(60, 26, "fp32 weights, 4 bytes each", "tm", 11)
    a.text(24, 70, "fp32", size=11, mono=True, weight=600)
    a.line(60, 66, 580, 66, "s")
    a.text(24, 158, "int8", size=11, mono=True, weight=600)
    a.line(60, 154, 580, 154, "s")
    for q in range(-120, 121, 8):
        a.line(round(X(q, 127), 1), 150, round(X(q, 127), 1), 158, "m")
    for q in (-127, 127):
        a.line(X(q, 127), 148, X(q, 127), 160, "s")
    a.line(320, 148, 320, 160, "s")
    a.text(60, 174, "-127", "tm", 10.5, "middle", mono=True); a.text(320, 174, "0", "tm", 10.5, "middle", mono=True)
    a.text(580, 174, "127", "tm", 10.5, "middle", mono=True)
    a.text(60, 190, "1 byte each", "tm", 11)
    ws = [(-1.27, "-1.270", -127), (-0.512, "-0.512", -51), (0.068, "0.068", 7), (0.423, "0.423", 42), (0.915, "0.915", 92)]
    for w, label, q in ws:
        x = round(X(w, 1.27), 1)
        foc = label == "0.423"
        a.text(x, 52, label, "ta" if foc else "tm", 10.5, "middle", 600 if foc else None, mono=True)
        a.line(x, 74, x, 144 if foc else 148, "a" if foc else "m", arrow=foc, dash=not foc)
        dot(a, x, 66, 4.5, "a fa" if foc else "s f")
        a.text(x + 6, 120, str(q), "ta" if foc else "tm", 10.5, weight=600 if foc else None, mono=True)
    a.text(66, 92, "max |w|", "tm", 10)
    # zoom
    zx0, zx1, zy = 330, 616, 262
    qx = lambda q: 376 + (q - 41) * 72
    a.path(f"M{X(41, 127):.1f} 160 L{zx0} 204", "m", dash=True)
    a.path(f"M{X(44, 127):.1f} 160 L{zx1} 204", "m", dash=True)
    a.box(zx0, 204, zx1 - zx0, 90, "m fs", rx=10)
    a.text(344, 224, "round to the nearest integer", "tm", 10.5)
    a.line(346, zy, 600, zy, "s")
    for q in range(41, 45):
        foc = q == 42
        a.line(qx(q), zy - 6, qx(q), zy + 6, "a" if foc else "s")
        a.text(qx(q), zy + 22, str(q), "ta" if foc else "tm", 11, "middle", 700 if foc else None, mono=True)
    wx = qx(42.3)
    dot(a, wx, 236, 4, "a fa")
    a.text(wx + 10, 240, "w / s = 42.3", "ta", 11, mono=True)
    a.path(f"M{wx - 3:.1f} 239 L{qx(42) + 2:.1f} {zy - 9}", "a", arrow=True)
    # the arithmetic
    rows = [("scale", "s = max|w| / 127 = 0.01"), ("store", "q = round(w / s) = 42"), ("use", "w' = q x s = 0.420"),
            ("error", "0.423 - 0.420 = 0.003")]
    for i, (k, v) in enumerate(rows):
        y = 218 + i * 20
        a.text(24, y, k, "tm", 11)
        a.text(70, y, v, "t", 11, mono=True)
    return a


def inf_batching():
    a = Art("i04", "Continuous batching: requests leave the batch when they finish and waiting ones join at the next step")
    x0, sw = 112, 41
    slots = [[("R1", 1, 5), ("R6", 6, 12)], [("R2", 1, 8), ("R8", 9, 12)], [("R3", 1, 3), ("R5", 4, 11), ("R9", 12, 12)],
             [("R4", 1, 7), ("R7", 8, 12)]]
    ys = [40 + i * 38 for i in range(4)]
    for i, (y, row) in enumerate(zip(ys, slots)):
        a.text(24, y + 19, f"slot {i + 1}", "tm", 11, mono=True)
        for name, s, e in row:
            foc = name == "R5"
            x = x0 + (s - 1) * sw + 2
            w = (e - s + 1) * sw - 4
            late = int(name[1:]) > 4
            a.box(x, y, w, 28, "a af" if foc else ("s fs" if late else "s f"), rx=6)
            a.text(x + 10, y + 18, name, "ta" if foc else "t", 11, weight=600 if foc else None, mono=True)
            if e < 12:
                a.circle(x + w - 10, y + 14, 3, "s")
    jx = x0 + 3 * sw
    a.line(jx, 30, jx, 196, "a", dash=True)
    for s in range(1, 13):
        a.text(x0 + (s - 1) * sw + sw / 2, 212, str(s), "tm", 10.5, "middle", mono=True)
    a.text(x0, 232, "decode step: one forward pass over every running request", "tm", 11)
    a.text(jx + 8, 26, "step 4: R3 is done, R5 joins", "ta", 11, weight=600)
    a.circle(24 + 4, 254, 3, "s"); a.text(36, 258, "request finished (stop token)", "tm", 11)
    a.text(24, 282, "No slot waits for the longest request in the batch, and no new request waits for a whole batch.", "tm", 11)
    return a


def inf_paged():
    a = Art("i05", "Paged KV memory: each sequence's cache lives in fixed-size blocks, placed anywhere through a block table")
    a.text(24, 30, "logical blocks", "tm", 11)
    a.text(150, 30, "block table", "tm", 11)
    a.text(400, 30, "KV blocks in memory", "tm", 11)
    seqs = [("A", [4, 4, 2], [7, 1, 12], 46), ("B", [4, 2], [3, 9], 166)]
    phys = {}
    for name, fills, table, y0 in seqs:
        foc = name == "A"
        for k, (n, p) in enumerate(zip(fills, table)):
            y = y0 + k * 30
            a.box(44, y, 80, 24, "s f", rx=4)
            for j in range(1, 4):
                a.line(44 + j * 20, y, 44 + j * 20, y + 24, "m")
            for j in range(n):
                a.circle(54 + j * 20, y + 12, 1.6, "s")
            a.text(132, y + 16, str(k), "tm", 10, mono=True)
            a.box(150, y, 40, 24, "a af" if foc else "s fs", rx=4)
            a.text(170, y + 16, str(p), "ta" if foc else "t", 11.5, "middle", 600, mono=True)
            phys[p] = f"{name}{k}"
        a.text(24, y0 + 16, name, "ta" if foc else "t", 13, weight=700, mono=True)
    gx, gy, bw, bh = 400, 44, 50, 34
    for p in range(16):
        r, c = divmod(p, 4)
        x, y = gx + c * (bw + 6), gy + r * (bh + 8)
        own = phys.get(p)
        if own is None:
            a.box(x, y, bw, bh, "m", rx=5, dash=True)
            a.text(x + 5, y + 12, str(p), "tm", 9, mono=True)
            continue
        foc = own.startswith("A")
        a.box(x, y, bw, bh, "a af" if foc else "s fs", rx=5)
        a.text(x + 5, y + 12, str(p), "tm", 9, mono=True)
        a.text(x + bw / 2, y + 27, own, "ta" if foc else "t", 11.5, "middle", 600, mono=True)
    # one mapping drawn out: A's block 2 -> physical block 12
    ty = 46 + 2 * 30 + 12
    by = gy + 3 * (bh + 8) + bh / 2
    a.path(f"M190 {ty} C 300 {ty}, 300 {by}, {gx - 2} {by}", "a", arrow=True)
    a.text(392, 226, "A's block 2 is block 12", "ta", 10.5, "end")
    a.text(24, 254, "4 tokens per block here (vLLM uses 16). A sequence takes a new block only when its last one is full,", "tm", 11)
    a.text(24, 272, "so each wastes less than one block, and its blocks need not sit next to each other. Dashed: free.", "tm", 11)
    return a


def inf_prod():
    a = Art("i06", "A load test finds the capacity at your latency target; the capacity sets what a token costs")
    px0, px1, py0, py1 = 64, 380, 40, 214
    X = lambda lam: px0 + lam / 20 * (px1 - px0)
    Y = lambda s: py1 - s / 2.5 * (py1 - py0)
    a.line(px0, py1, px1 + 6, py1, "m"); a.line(px0, py1, px0, py0 - 6, "m")
    for v in (0, 5, 10, 15, 20):
        a.text(X(v), py1 + 16, str(v), "tm", 10, "middle", mono=True)
    for s in (0, 1, 2):
        a.text(px0 - 8, Y(s) + 4, f"{s} s", "tm", 10, "end", mono=True)
    a.text(px0 + (px1 - px0) / 2, py1 + 34, "load: requests per second", "tm", 10.5, "middle")
    a.text(px0, 28, "latency", "tm", 10.5)

    def curve(base, k):
        pts = []
        lam = 0.0
        while lam < 19.6:
            r = lam / 20
            s = base + k * r / (1 - r)
            if s > 2.5:
                break
            pts.append((X(lam), Y(s)))
            lam += 0.2
        return pts
    p50 = curve(0.35, 0.08)
    p99 = curve(0.60, 0.25)
    poly(a, p50, "m")
    poly(a, p99, "s")
    a.text(p50[-1][0] - 4, p50[-1][1] + 2, "p50", "tm", 10.5, "end", mono=True)
    a.text(p99[-1][0] - 6, p99[-1][1] + 4, "p99", size=10.5, anchor="end", weight=600, mono=True)
    a.line(px0, Y(1.0), px1, Y(1.0), "m", dash=True)
    a.text(px0 + 6, Y(1.0) - 6, "target: p99 under 1 s", "tm", 10.5)
    # crossing: 0.6 + 0.25 r/(1-r) = 1  ->  r/(1-r) = 1.6  ->  r = 1.6/2.6
    lam_c = 20 * 1.6 / 2.6
    a.line(X(lam_c), Y(1.0), X(lam_c), py1, "a")
    dot(a, X(lam_c), Y(1.0), 4, "a fa")
    a.text(X(lam_c) + 8, py1 - 10, "capacity: 12 req/s", "ta", 11, weight=600)
    # cost
    cx = 428
    a.box(cx - 12, 40, 200, 174, "m fs", rx=10)
    a.text(cx, 64, "what a token costs", size=12, weight=700)
    rows = [("t", "$2.00 per hour"), ("tm", "machine price"), ("t", "1,500 tokens/s"), ("tm", "output at capacity"),
            ("t", "= 5.4M tokens/hour"), ("ta", "$0.37 per 1M tokens")]
    ys = [90, 105, 128, 143, 166, 196]
    for (cls, t), y in zip(rows, ys):
        mono = cls != "tm"
        a.text(cx, y, t, cls, 11 if mono else 10.5, weight=700 if cls == "ta" else None, mono=mono)
    a.line(cx, 178, cx + 176, 178, "m")
    a.text(24, 272, "Price per 1M tokens = hourly price / tokens per hour x 1,000,000. Measure it; never assume it.", "tm", 11)
    return a


def inf_capstone():
    a = Art("i07", "A fair comparison: hold everything fixed but the engine, and report spread, not one number")
    ins = [("same weights", "GPT-2, 8-bit"), ("same prompts", "200, fixed order"), ("same settings", "greedy, 256 tokens"),
           ("same machine", "same threads, idle")]
    for i, (t, sub) in enumerate(ins):
        y = 40 + i * 48
        a.box(24, y, 140, 40, "s f", rx=8)
        a.text(36, y + 17, t, size=12, weight=600)
        a.text(36, y + 32, sub, "tm", 10.5)
        a.line(164, y + 20, 186, y + 20, "m")
    a.line(186, 60, 186, 204, "m")
    a.line(186, 92, 214, 92, "s", arrow=True); a.line(186, 172, 214, 172, "s", arrow=True)
    a.box(216, 72, 120, 40, "a af", rx=8); a.text(276, 97, "your server", "ta", 12, "middle", 700)
    a.box(216, 152, 120, 40, "s fs", rx=8); a.text(276, 177, "llama.cpp", size=12, anchor="middle", weight=700, mono=True)
    a.path("M336 92 C 356 92, 356 132, 374 132", "a", arrow=True)
    a.path("M336 172 C 356 172, 356 132, 374 132", "s", arrow=True)
    # report table
    tx = 380
    a.box(tx, 40, 236, 176, "s f", rx=10)
    a.text(tx + 12, 60, "report", size=12, weight=700)
    a.text(512, 60, "yours", "ta", 11, "middle", 600)
    a.text(578, 60, "llama.cpp", "tm", 10.5, "middle", mono=True)
    a.line(tx, 70, tx + 236, 70, "m")
    rows = ["decode tok/s", "TTFT p50", "TTFT p99", "peak memory", "perplexity"]
    spread = [(0.30, 0.55), (0.42, 0.62), (0.25, 0.5), (0.5, 0.58), (0.45, 0.47)]
    for i, (r, (u, v)) in enumerate(zip(rows, spread)):
        y = 90 + i * 27
        a.text(tx + 12, y + 4, r, size=11)
        for cx, val, cls in ((512, u, "a"), (578, v, "s")):
            x = cx - 22 + val * 44
            a.line(x - 9 + i % 2 * 2, y, x + 8, y, "m")
            a.circle(round(x, 1), y, 3.2, f"{cls} f{'a' if cls == 'a' else 's'}")
        if i:
            a.line(tx + 8, y - 13, tx + 228, y - 13, "m")
    a.circle(392, 232, 3.2, "s fs"); a.line(382, 232, 402, 232, "m")
    a.text(410, 236, "median and range of 5 runs", "tm", 10.5)
    a.text(24, 282, "Change one thing at a time, keep the rest fixed, and publish the scripts so anyone can rerun the table.", "tm", 11)
    return a


# =================================================================== research

def res_workbench():
    a = Art("r00", "A reproducible run: the same config, seed and commit give the same curve")
    a.text(24, 30, "config.yaml", size=12, weight=600, mono=True)
    a.box(24, 40, 156, 112, "s fs", rx=8)
    for i, line in enumerate(["seed: 1234", "lr: 3e-4", "batch_size: 64", "steps: 2000", "commit: 9f2c1ab"]):
        a.text(38, 62 + i * 19, line, "ta" if line.startswith("seed") else "t", 11, weight=600 if line.startswith("seed") else None, mono=True)
    a.line(180, 96, 212, 96, arrow=True)
    a.box(214, 76, 96, 40, "s f", rx=8); a.text(262, 101, "train.py", size=12, anchor="middle", mono=True)
    a.text(262, 136, "writes", "tm", 10.5, "middle")
    a.text(262, 151, "metrics.jsonl", "tm", 10.5, "middle", mono=True)
    a.line(310, 96, 346, 96, arrow=True)
    px0, px1, py0, py1 = 362, 610, 40, 196
    a.line(px0, py1, px1, py1, "m"); a.line(px0, py1, px0, py0, "m")
    a.text(px0, 30, "loss", "tm", 10.5)
    a.text(px1, py1 + 16, "step 2000", "tm", 10, "end", mono=True)
    a.text(px0, py1 + 16, "0", "tm", 10, "middle", mono=True)

    def run(seed):
        pts = []
        for i in range(0, 101):
            s = i / 100
            noise = 0.05 * math.sin(37 * s * seed + seed) * math.exp(-1.2 * s) + 0.02 * math.sin(91 * s + 3 * seed)
            loss = 0.35 + 2.0 * math.exp(-s * 5.2) + noise
            pts.append((px0 + s * (px1 - px0), py1 - loss / 2.6 * (py1 - py0)))
        return pts
    poly(a, [(x, y - 9 * math.sin(math.pi * (x - px0) / (px1 - px0)) ** 2) for x, y in run(2.9)], "m", dash=True)
    poly(a, run(1.7), "a")
    a.text(470, 96, "runs 1 and 2, seed 1234:", "ta", 10.5, weight=600)
    a.text(470, 110, "one curve, drawn twice", "ta", 10.5)
    a.text(470, 72, "seed 99: close, not equal", "tm", 10.5)
    a.text(24, 248, "Fix the seed, the config and the code version, and log every number. Run it twice:", "tm", 11)
    a.text(24, 266, "if the two curves are not identical, something is not under your control yet.", "tm", 11)
    return a


def res_backprop():
    a = Art("r01", "Backpropagation on a small graph: values flow forward, gradients flow back")
    W, H = 96, 46
    nodes = {"a": (24, 36, "2.0", "6.0"), "b": (24, 112, "-3.0", "-4.0"), "e": (182, 72, "-6.0", "-2.0"),
             "c": (182, 158, "10.0", "-2.0"), "d": (342, 116, "4.0", "-2.0"), "f": (342, 200, "-2.0", "4.0"),
             "L": (504, 158, "-8.0", "1.0")}
    for name, (x, y, v, g) in nodes.items():
        a.box(x, y, W, H, "s f", rx=8)
        a.text(x + 12, y + 19, f"{name} = {v}", size=12, mono=True, weight=600)
        a.text(x + 12, y + 36, f"grad {g}", "ta", 11, mono=True)
    ops = {"m1": (152, 97, "*"), "p": (312, 139, "+"), "m2": (474, 181, "*")}
    for _, (x, y, s) in ops.items():
        a.circle(x, y, 12, "s fs")
        a.text(x, y + 4.5, s, size=13, anchor="middle", mono=True, weight=600)

    def edge(x1, y1, x2, y2):
        a.path(f"M{x1} {y1} C {x1 + 14} {y1}, {x2 - 16} {y2}, {x2} {y2}", "s")
    edge(120, 59, 140, 93); edge(120, 135, 140, 101)
    a.line(164, 97, 180, 95, arrow=True)
    edge(278, 95, 300, 135); edge(278, 181, 300, 143)
    a.line(324, 139, 340, 139, arrow=True)
    edge(438, 139, 462, 177); edge(438, 223, 462, 185)
    a.line(486, 181, 502, 181, arrow=True)
    a.line(24, 16, 300, 16, "s", arrow=True); a.text(308, 20, "forward: values", "tm", 10.5)
    a.text(24, 196, "chain rule, one step:", "tm", 10.5)
    a.text(24, 216, "a.grad = b x e.grad", "ta", 11, mono=True, weight=600)
    a.text(65, 234, "= -3.0 x -2.0 = 6.0", "ta", 11, mono=True)
    a.line(616, 280, 250, 280, "a", arrow=True)
    a.text(240, 284, "backward(): gradients, from L", "ta", 10.5, "end", 600)
    return a


def res_training():
    a = Art("r02", "What a loss curve tells you: one healthy run and three ways training goes wrong")
    panels = [("healthy", ["starts near ln 10 = 2.30,", "then falls smoothly"]),
              ("lr too high", ["falls, then blows up", "to nan: lower the lr"]),
              ("stuck", ["flat at 2.30: no signal", "reaches the weights"]),
              ("overfitting", ["train keeps falling,", "validation turns up"])]
    pw, py0, py1 = 136, 40, 176
    Y = lambda L: py1 - L / 3.0 * (py1 - py0)
    for i, (title, lines) in enumerate(panels):
        x0 = 24 + i * 152
        X = lambda s: x0 + 4 + s * (pw - 8)
        a.line(x0, py0, x0, py1, "m"); a.line(x0, py1, x0 + pw, py1, "m")
        a.line(x0, Y(2.303), x0 + pw, Y(2.303), "m", dash=True)
        n = 60
        if i == 0:
            pts = [(X(k / n), Y(0.3 + 2.0 * math.exp(-4.5 * k / n) + 0.025 * math.sin(k * 1.1) * (1 - k / n))) for k in range(n + 1)]
            poly(a, pts, "a")
        elif i == 1:
            pts = []
            for k in range(n + 1):
                s = k / n
                L = 0.9 + 1.4 * math.exp(-9 * s) + (0 if s < 0.45 else 8 * (s - 0.45) ** 2) + 0.03 * math.sin(k * 1.3)
                if L > 2.95:
                    pts.append((X(s), Y(2.95)))
                    break
                pts.append((X(s), Y(L)))
            poly(a, pts, "s")
            a.text(pts[-1][0] - 6, Y(2.95) + 4, "nan", size=10.5, anchor="end", mono=True, weight=600)
        elif i == 2:
            pts = [(X(k / n), Y(2.303 + 0.04 * math.sin(k * 0.9) + 0.025 * math.sin(k * 2.7))) for k in range(n + 1)]
            poly(a, pts, "s")
        else:
            tr = [(X(k / n), Y(0.15 + 1.9 * math.exp(-4.0 * k / n))) for k in range(n + 1)]
            va = [(X(k / n), Y(0.75 + 1.4 * math.exp(-6 * k / n) + 1.1 * max(0, k / n - 0.3) ** 1.5)) for k in range(n + 1)]
            poly(a, tr, "s")
            poly(a, va, "s", dash=True)
            a.text(x0 + pw, Y(0.15 + 1.9 * math.exp(-4)) - 6, "train", "tm", 10, "end")
            a.text(x0 + pw, va[-1][1] - 6, "val", "tm", 10, "end")
        a.text(x0, py1 + 22, title, size=12, weight=700)
        for j, ln in enumerate(lines):
            a.text(x0, py1 + 39 + j * 15, ln, "tm", 10.5)
    a.text(24 + pw, Y(2.303) - 5, "2.30", "tm", 9.5, "end", mono=True)
    a.text(24, 30, "loss", "tm", 10.5)
    a.text(24, 284, "First check, before any training: a 10-class model at init should score loss ln 10 = 2.30.", "tm", 11)
    return a


def res_arch():
    a = Art("r03", "Three model families and how each passes its input through: two residual blocks and a LoRA fine-tune")

    def plus(x, y):
        a.circle(x, y, 9, "s f")
        a.path(f"M{x - 4.5} {y} H {x + 4.5} M{x} {y - 4.5} V {y + 4.5}", "s")

    def blk(cx, y, w, label, cls="s f", size=10.5, mono=False):
        a.box(cx - w / 2, y, w, 22, cls, rx=5)
        a.text(cx, y + 15, label, "t", size, "middle", mono=mono)
    # ResNet
    cx = 104
    a.text(cx, 22, "residual network", size=12, anchor="middle", weight=700)
    a.text(cx, 254, "x", size=12, anchor="middle", mono=True)
    a.line(cx, 242, cx, 214, arrow=True)
    blk(cx, 190, 116, "3x3 conv, BN, ReLU")
    a.line(cx, 190, cx, 168, arrow=True)
    blk(cx, 144, 116, "3x3 conv, BN")
    a.line(cx, 144, cx, 128, arrow=True)
    plus(cx, 118)
    a.line(cx, 109, cx, 98, arrow=True)
    blk(cx, 74, 60, "ReLU")
    a.line(cx, 74, cx, 50, arrow=True)
    a.text(cx, 44, "y", size=12, anchor="middle", mono=True)
    a.path(f"M{cx} 232 H 178 V 118 H {cx + 11}", "a", arrow=True)
    a.text(184, 180, "x", "ta", 11, mono=True, weight=600)
    a.text(cx, 278, "y = relu(F(x) + x)", "tm", 10.5, "middle", mono=True)
    # transformer
    cx = 320
    a.text(cx, 22, "transformer block", size=12, anchor="middle", weight=700)
    a.text(cx, 254, "x", size=12, anchor="middle", mono=True)
    a.line(cx, 242, cx, 226, arrow=True)
    blk(cx, 202, 50, "ln", mono=True, size=11)
    a.line(cx, 202, cx, 192, arrow=True)
    blk(cx, 168, 96, "attention")
    a.line(cx, 168, cx, 158, arrow=True)
    plus(cx, 148)
    a.line(cx, 139, cx, 130, arrow=True)
    blk(cx, 106, 50, "ln", mono=True, size=11)
    a.line(cx, 106, cx, 96, arrow=True)
    blk(cx, 72, 96, "MLP")
    a.line(cx, 72, cx, 62, arrow=True)
    plus(cx, 52)
    a.line(cx, 43, cx, 32, "s")
    a.path(f"M{cx} 234 H 394 V 148 H {cx + 11}", "a", arrow=True)
    a.path(f"M{cx} 138 H 394 V 52 H {cx + 11}", "a", arrow=True)
    a.text(cx, 278, "x = x + attn(ln(x))", "tm", 10.5, "middle", mono=True)
    a.text(cx, 294, "x = x + mlp(ln(x))", "tm", 10.5, "middle", mono=True)
    # LoRA
    cx = 532
    a.text(cx, 22, "fine-tuning with LoRA", size=12, anchor="middle", weight=700)
    a.text(cx, 254, "x", size=12, anchor="middle", mono=True)
    a.path(f"M{cx} 242 V 232 H 494 V 214", "s", arrow=True)
    a.path(f"M{cx} 232 H 582 V 214", "s", arrow=True)
    a.box(456, 110, 76, 102, "s fs", rx=6)
    a.text(494, 150, "W", size=14, anchor="middle", mono=True, weight=700)
    a.text(494, 168, "frozen", "tm", 10.5, "middle")
    a.text(494, 184, "768 x 768", "tm", 9.5, "middle", mono=True)
    a.box(556, 184, 52, 28, "a af", rx=5); a.text(582, 197, "A", "ta", 12, "middle", 700, mono=True)
    a.text(582, 208, "8 x 768", "ta", 8, "middle", mono=True)
    a.line(582, 184, 582, 156, "a", arrow=True)
    a.box(556, 126, 52, 28, "a af", rx=5); a.text(582, 139, "B", "ta", 12, "middle", 700, mono=True)
    a.text(582, 150, "768 x 8", "ta", 8, "middle", mono=True)
    a.path("M494 110 V 82 H 521", "s", arrow=True)
    a.path("M582 126 V 82 H 543", "a", arrow=True)
    plus(cx, 82)
    a.line(cx, 73, cx, 50, arrow=True)
    a.text(cx, 44, "h", size=12, anchor="middle", mono=True)
    a.text(cx, 278, "h = W x + B A x", "tm", 10.5, "middle", mono=True)
    a.text(cx, 294, "only A, B train; B starts at 0", "tm", 10.5, "middle")
    return a


def res_grok():
    a = Art("r04", "Grokking, the figure to reproduce: train accuracy saturates early, validation jumps much later")
    px0, px1, py0, py1 = 72, 440, 52, 212
    X = lambda lg: px0 + (lg - 1) / 5 * (px1 - px0)
    Y = lambda acc: py1 - acc * (py1 - py0)
    a.line(px0, py1, px1, py1, "m"); a.line(px0, py1, px0, py0 - 4, "m")
    for e in range(1, 7):
        a.line(X(e), py1, X(e), py1 + 4, "m")
        a.text(X(e), py1 + 18, f"1e{e}", "tm", 10, "middle", mono=True)
    for acc, lab in ((0, "0%"), (0.5, "50%"), (1, "100%")):
        a.text(px0 - 8, Y(acc) + 4, lab, "tm", 10, "end", mono=True)
    a.line(px0, Y(1), px1, Y(1), "m", dash=True)
    a.text(px0 + (px1 - px0) / 2, py1 + 36, "optimization steps, log scale", "tm", 10.5, "middle")
    a.text(24, 30, "accuracy", "tm", 10.5)

    def logistic(c, k, lo):
        return [(X(lg), Y(lo + (1 - lo) / (1 + math.exp(-k * (lg - c))))) for lg in [1 + i * 0.05 for i in range(101)]]
    poly(a, logistic(2.5, 9, 0.01), "s")
    poly(a, logistic(5.35, 10, 0.01), "a")
    a.text(X(2.5) + 10, Y(0.42), "train", size=11, weight=600)
    a.text(X(5.35) + 10, Y(0.42), "validation", "ta", 11, weight=600)
    a.path(f"M{X(3.05):.1f} 38 H {X(5.3):.1f}", "m", arrow=True)
    a.text((X(3.05) + X(5.3)) / 2, 32, "about 100x more steps", "tm", 10.5, "middle")
    # the reproduction
    rx = 470
    a.text(rx, 64, "reproduce it", size=12, weight=700)
    for i, t in enumerate(["division mod 97", "train on 50% of the pairs", "the same optimizer and", "weight decay as the paper"]):
        a.text(rx, 86 + i * 17, t, "tm", 10.5)
    a.text(rx, 172, "Does the jump appear,", size=11, weight=600)
    a.text(rx, 188, "and at which step?", size=11, weight=600)
    a.text(24, 284, "After Power et al. 2022, Figure 1. A schematic: your own run produces the real curve.", "tm", 10.5)
    return a


def res_scientist():
    a = Art("r05", "One run can mislead: compare five seeds each, with error bars, and keep a test set you look at once")
    Y = lambda v: 230 - (v - 70) * 30
    base = [71.2, 72.0, 72.5, 73.1, 71.8]
    idea = [71.5, 72.9, 74.2, 72.1, 73.0]
    a.line(96, 50, 96, 230, "m")
    for v in (70, 72, 74, 76):
        a.text(88, Y(v) + 4, str(v), "tm", 10, "end", mono=True)
        a.line(92, Y(v), 96, Y(v), "m")
    a.text(96, 36, "accuracy %, 5 seeds each", "tm", 10.5)

    def column(cx, vals, foc):
        m = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
        for j, v in enumerate(vals):
            dot(a, cx - 20 + j * 8, Y(v), 3.5, "a af" if foc else "s f")
        bx = cx + 28
        cls = "a" if foc else "s"
        a.line(bx, Y(m - sd), bx, Y(m + sd), cls)
        a.line(bx - 5, Y(m - sd), bx + 5, Y(m - sd), cls); a.line(bx - 5, Y(m + sd), bx + 5, Y(m + sd), cls)
        dot(a, bx, Y(m), 4, "a fa" if foc else "s fs")
        return m, sd
    mb, sb = column(152, base, False)
    mi, si = column(286, idea, True)
    a.text(162, 252, "baseline", size=12, anchor="middle", weight=600)
    a.text(296, 252, "your idea", "ta", 12, "middle", 700)
    a.line(286 - 20 + 2 * 8 + 6, Y(74.2) - 4, 340, Y(75.1), "m")
    a.text(344, Y(75.1) + 4, "lucky seed", "tm", 10.5)
    rx = 420
    a.text(rx, 60, "one run each", size=12, weight=700)
    a.text(rx, 78, "74.2 vs 72.5: \"+1.7 points\"", "tm", 10.5, mono=True)
    a.text(rx, 110, "five seeds each", size=12, weight=700)
    a.text(rx, 128, f"{mi:.1f} +- {si:.1f} vs {mb:.1f} +- {sb:.1f}", "tm", 10.5, mono=True)
    a.text(rx, 146, "the bars overlap: no evidence yet", "ta", 11, weight=600)
    # the split
    a.text(rx, 188, "an evaluation you cannot game", size=12, weight=700)
    a.add(f'<rect class="s f" x="{rx}" y="198" width="104" height="26" {SW}/>')
    a.text(rx + 52, 215, "train", size=11, anchor="middle")
    a.add(f'<rect class="s f" x="{rx + 104}" y="198" width="46" height="26" {SW}/>')
    a.text(rx + 127, 215, "val", size=11, anchor="middle")
    a.add(f'<rect class="s fs" x="{rx + 150}" y="198" width="46" height="26" {SW}/>')
    a.text(rx + 173, 215, "test", size=11, anchor="middle", weight=700)
    a.text(rx, 242, "tune on val; open test once,", "tm", 10.5)
    a.text(rx, 257, "at the very end", "tm", 10.5)
    a.text(24, 284, "Bars: mean +- one standard deviation over seeds.", "tm", 10.5)
    return a


def res_circuit():
    a = Art("r06", "An induction head: two attention heads that together continue repeated text")
    toks = ["the", "cat", "sat", ".", "the"]
    xs = [110 + i * 92 for i in range(5)]
    ty = 196
    for i, (x, t) in enumerate(zip(xs, toks)):
        a.box(x, ty, 76, 30, "s f", rx=8)
        a.text(x + 38, ty + 20, t, size=12.5, anchor="middle", mono=True, weight=600 if i in (1, 4) else None)
    a.box(574, ty, 42, 30, "a af", rx=8); a.text(595, ty + 20, "cat", "ta", 12, "middle", 700, mono=True)
    a.text(595, ty - 8, "next", "ta", 10.5, "middle")
    # layer 0: each token reads the one before it
    for i in range(1, 5):
        x1, x2 = xs[i - 1] + 38, xs[i] + 30
        a.path(f"M{x1} {ty} C {x1} {ty - 26}, {x2} {ty - 26}, {x2} {ty - 2}", "s" if i == 1 else "m", arrow=i == 1)
    a.text(24, 160, "layer 0", size=12, weight=700)
    a.text(24, 176, "previous token", "tm", 10.5)
    # layer 1: the second "the" finds what followed the first one, and copies it
    x1, x2 = xs[1] + 44, xs[4] + 38
    a.path(f"M{x1} {ty} C {x1} 70, {x2} 70, {x2} {ty - 2}", "a", arrow=True)
    a.path(f"M{xs[4] + 76} {ty + 15} H 572", "a", arrow=True)
    a.text(24, 84, "layer 1", size=12, weight=700)
    a.text(24, 100, "induction head", "tm", 10.5)
    a.text((x1 + x2) / 2, 42, "the second 'the' attends to 'cat',", "ta", 10.5, "middle")
    a.text((x1 + x2) / 2, 57, "the token that followed 'the' before,", "ta", 10.5, "middle")
    a.text((x1 + x2) / 2, 72, "and copies it to the output", "ta", 10.5, "middle")
    a.text(xs[1] + 38, ty + 48, "'cat' now also holds: the token before me was 'the'", "tm", 10.5, "middle")
    a.text(24, 284, "Pattern: [A][B] ... [A] -> predict [B]. Found in small attention-only models (Elhage et al. 2021).", "tm", 10.5)
    return a


def res_result():
    a = Art("r07", "Your own result: a loop of question, prediction, experiment and doubt, and a way out to a public write-up")
    nodes = {"Q": (40, 46, "a small question"), "P": (230, 46, "a prediction"), "E": (230, 146, "the experiment"),
             "D": (40, 146, "try to break it")}
    for _, (x, y, t) in nodes.items():
        a.box(x, y, 130, 36, "s f", rx=18)
        a.text(x + 65, y + 23, t, size=12, anchor="middle", weight=600)
    a.line(170, 64, 228, 64, arrow=True)
    a.line(295, 82, 295, 144, arrow=True)
    a.line(230, 164, 172, 164, arrow=True)
    a.line(105, 146, 105, 84, "m", arrow=True)
    a.text(114, 120, "it breaks: refine", "tm", 10.5)
    a.path("M105 182 V 236 H 396 V 104 H 416", "a", arrow=True)
    a.text(250, 228, "it survives: write it up", "ta", 11, "middle", 600)
    # paper
    a.box(420, 30, 100, 140, "s f", rx=6)
    a.add(f'<rect class="s fs" x="432" y="42" width="76" height="9" rx="2" {SW}/>')
    for y in (62, 71, 80):
        a.line(432, y, 508, y, "m")
    a.line(436, 128, 436, 92, "m"); a.line(436, 128, 504, 128, "m")
    poly(a, [(440, 122), (452, 116), (464, 117), (476, 106), (488, 101), (500, 96)], "s")
    for y in (142, 151, 160):
        a.line(432, y, 508 if y < 160 else 480, y, "m")
    a.text(470, 188, "paper", size=12, anchor="middle", weight=700)
    # repo
    a.box(540, 30, 76, 140, "s fs", rx=6)
    for i, t in enumerate(["repo/", "README", "data/", "train.py", "plots.py", "Makefile"]):
        a.text(550, 52 + i * 19, t, "t" if i == 0 else "tm", 10.5, weight=600 if i == 0 else None, mono=True)
    a.text(578, 188, "code", size=12, anchor="middle", weight=700)
    a.text(420, 222, "$ make reproduce", size=11, mono=True, weight=600)
    a.text(420, 238, "rebuilds every number and figure", "tm", 10.5)
    a.text(24, 284, "Small, finished and public beats big and half done.", "tm", 11)
    return a


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{}</svg>\n')

TRACKS = {
    "inference-engineering": {
        "00": (inf_workbench, '<circle cx="10" cy="11.5" r="6"/><path d="M10 11.5V8.5M8 2.5h4M10 2.5v3M15 6l1.25-1.25"/>'),
        "01": (inf_forward, '<rect x="4" y="2.75" width="12" height="3.5" rx="1"/><rect x="4" y="8.25" width="12" height="3.5" rx="1"/><rect x="4" y="13.75" width="12" height="3.5" rx="1"/>'),
        "02": (inf_kv, '<path d="M3.5 14.5a6.5 6.5 0 1 1 13 0"/><path d="M10 14.5l3.25-4"/>'),
        "03": (inf_quant, '<path d="M3 7.5h4.5V3M17 12.5h-4.5V17M7.5 7.5L3 3M12.5 12.5L17 17"/>'),
        "04": (inf_batching, '<rect x="3" y="3.5" width="14" height="5.5" rx="1.5"/><rect x="3" y="11" width="14" height="5.5" rx="1.5"/><path d="M6.5 6.25h.01M6.5 13.75h.01" stroke-width="2"/>'),
        "05": (inf_paged, '<rect x="5" y="5" width="10" height="10" rx="1.5"/><rect x="8" y="8" width="4" height="4" rx=".5"/><path d="M8 2.5V5M12 2.5V5M8 15v2.5M12 15v2.5M2.5 8H5M2.5 12H5M15 8h2.5M15 12h2.5"/>'),
        "06": (inf_prod, '<path d="M2.5 10.5h3l2-5.5 4 10 2-4.5h4"/>'),
        "07": (inf_capstone, '<path d="M4.5 17.5V3M4.5 3.5h10l-2 3.5 2 3.5h-10"/>'),
    },
    "ai-research": {
        "00": (res_workbench, '<rect x="3" y="3" width="14" height="14" rx="3"/><path d="M7 7h.01M13 13h.01M10 10h.01M13 7h.01M7 13h.01" stroke-width="2.2"/>'),
        "01": (res_backprop, '<circle cx="5" cy="5.5" r="2"/><circle cx="5" cy="14.5" r="2"/><circle cx="15" cy="10" r="2"/><path d="M7 6.4l6 2.7M7 13.6l6-2.7"/>'),
        "02": (res_training, '<path d="M3 3v14h14"/><path d="M5.5 5c1.5 6.5 4.5 9 11 9.5"/>'),
        "03": (res_arch, '<rect x="5" y="12" width="7" height="4.5" rx="1"/><rect x="5" y="3.5" width="7" height="4.5" rx="1"/><path d="M8.5 12V8M8.5 17.5v.5M12 14.25h3.5V5.75H12"/>'),
        "04": (res_grok, '<path d="M5 2.5h6.5L15 6v11.5H5z"/><path d="M11.5 2.5V6H15M7.5 10h5M7.5 13h5"/>'),
        "05": (res_scientist, '<path d="M6 4v8M4.5 4h3M4.5 12h3M14 7v9M12.5 7h3M12.5 16h3"/><path d="M6 8h.01M14 11.5h.01" stroke-width="2.6"/>'),
        "06": (res_circuit, '<circle cx="8.5" cy="8.5" r="5"/><path d="M12.25 12.25L17 17"/>'),
        "07": (res_result, '<path d="M7.5 14.5h5M8.5 17.5h3"/><path d="M10 2.5a5 5 0 0 0-3 9c.6.5 1 1.2 1 2v1h4v-1c0-.8.4-1.5 1-2a5 5 0 0 0-3-9z"/>'),
    },
}


def main():
    n = 0
    for stem, mods in TRACKS.items():
        for mid, (fn, icon) in mods.items():
            d = os.path.join(OUTLINES, stem, mid)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "cover.svg"), "w") as f:
                f.write(fn().svg())
            with open(os.path.join(d, "icon.svg"), "w") as f:
                f.write(ICON.format(icon))
            n += 1
    print("wrote", n, "covers and icons under", OUTLINES)


if __name__ == "__main__":
    main()
