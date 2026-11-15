"""Module art for the inference outline, in the xv6 covers' visual language.

Writes outlines/<stem>/NN/cover.svg (640x300 teaching diagram) and icon.svg (20x20 line icon).
Reuses the Art helpers from the xv6 generator (tools/art.py): 1.5 stroke, classes
s m a (stroke), f fs af fa (fill), t tm ta (text), mono.

The research outline's art used to be here too, under an older module numbering; it now lives
in research_art.py, which owns every file under outlines/ai-research/NN/.
"""
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
