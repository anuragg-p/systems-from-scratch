"""The research track's architecture map, one copy per lesson.

    python3 -B art/research/archmap.py              writes tracks/research/lessons/<module>/figures/NN.LL-map.svg
                                                    for every lesson written so far (its .md exists)
    python3 -B art/research/archmap.py 03 04.02     writes those lessons' maps, written or not (a module id
                                                    is all of its lessons): what a lesson writer runs
    python3 -B art/research/archmap.py --all DIR    writes every lesson's map under DIR/<module>/figures/
                                                    instead (a preview; DIR outside the repo or in build/)

From Python, write_map("03.02") does the same for one lesson and returns the file's path.

The map is the whole core (modules 00 to 15) as layers, the lab under everything:

    research      13 experiments that hold up | 14 the reproduction | 15 your own result
    models        06 images | 07 language models | 08 the GPT | 09 real weights |
                  10 today's architecture | 11 fast | 12 fine-tuning
    experiments   a curve | two groups | digits | deep networks | generalisation    the data:
    the engine    nudge | values | tensors | losses | layers | optimisers                points, MNIST, augment
    the lab       runs | seeds | plots | checkpoints | checks
    ------------  the current module's lessons, one box each (as dsa's strip)

In each lesson's copy, that lesson's piece (LESSONS below: exactly one per lesson) is drawn in
the accent colour, every piece whose code has arrived by that lesson (PIECES: the lesson it
comes with) solid, and everything still to come dashed and muted. The strip under the layers
is the current module's lessons, this one in the accent: it tells apart the lessons that share
a piece (03.02 to 03.05 are all "optimisers"). 00.01, the tour, lights every piece that has
code; models and research stay dashed until their code exists, as the map never claims what
the code does not have yet. Lessons reference it as

    ![Where NN.LL fits](figures/NN.LL-map.svg)

and the track's overview page shows 00.01's copy as the track's architecture.

When modules 06 on are built: give their pieces the lesson their code comes with (PIECES),
add their lessons (LESSONS, with a short label for the strip) and their module titles and
folders (MODULE_TITLES here, figlib.MODULE_DIRS), and split a model piece into several if the
code calls for it. Titles in LESSONS are the outline's: a lesson whose own title differs is
reported, so change the table's line with the lesson.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figlib  # noqa: E402
from figlib import Fig, tw  # noqa: E402

ROOT = figlib.ROOT

# The pieces, row by row, left to right in the order they are built: key -> (row, name, what it
# is, the lesson its code comes with; None: not built yet). A lesson whose own piece is another
# one can still bring a piece's code (00.03 brings the plots, 02.05 the checkpoint file, 03.01
# the optimisers' first one): that piece is solid from then on, never in the accent for it.
PIECES = {
    # research (not built yet)
    "13": ("research", "experiments that hold up", "13", None),
    "14": ("research", "the reproduction", "14", None),
    "15": ("research", "your own result", "15", None),
    # models (not built yet)
    "06": ("models", "images", "06", None),
    "07": ("models", "language models", "07", None),
    "08": ("models", "the GPT", "08", None),
    "09": ("models", "real weights", "09", None),
    "10": ("models", "today's architecture", "10", None),
    "11": ("models", "fast", "11", None),
    "12": ("models", "fine-tuning", "12", None),
    # experiments: experiments/<name>.py, one per lesson, here by module
    "curve": ("experiments", "a curve", "module 00", "00.01"),
    "groups": ("experiments", "two groups", "modules 01-02", "01.01"),
    "digits": ("experiments", "digits", "module 03", "03.01"),
    "deep": ("experiments", "deep networks", "module 04", "04.01"),
    "general": ("experiments", "generalisation", "module 05", "05.01"),
    # the engine: engine/
    "nudge": ("engine", "nudge", "gradient check", "01.01"),
    "values": ("engine", "values", "autograd", "01.02"),
    "tensors": ("engine", "tensors", "arrays", "02.01"),
    "losses": ("engine", "losses", "cross-entropy", "02.04"),
    "layers": ("engine", "layers", "nn.Module", "02.05"),
    "optim": ("engine", "optimisers", "SGD to AdamW", "03.01"),
    # the data: data/
    "points": ("data", "points", "made from a seed", "01.04"),
    "mnist": ("data", "MNIST", "fetched once", "03.01"),
    "augment": ("data", "augment", "shifted digits", "05.03"),
    # the lab: lab/
    "runs": ("lab", "runs", "config, seed, log", "00.02"),
    "seeds": ("lab", "seeds", "spread, Welch's t", "00.03"),
    "plots": ("lab", "plots", "curves from logs", "00.03"),
    "ckpt": ("lab", "checkpoints", "safetensors files", "02.05"),
    "checks": ("lab", "checks", "five bug checks", "04.06"),
}

# Every lesson: (id, title as the outline has it, its one piece, its label in the strip).
LESSONS = [
    ("00.01", "One experiment, end to end", "curve", "end to end"),
    ("00.02", "The same run twice: seeds, configs and logs", "runs", "the same run twice"),
    ("00.03", "Five seeds: how far a number moves by chance", "seeds", "five seeds"),
    ("01.01", "A derivative by nudging", "nudge", "nudging"),
    ("01.02", "A graph of values, and the chain rule backwards", "values", "a graph of values"),
    ("01.03", "A neuron, a layer, a network", "values", "a network"),
    ("01.04", "Training it: a loss that goes down", "groups", "training it"),
    ("02.01", "The scalar engine is a thousand times too slow", "tensors", "tensors"),
    ("02.02", "Broadcasting, and its backward", "tensors", "broadcasting"),
    ("02.03", "Matrix multiply, sums and indexing", "tensors", "matmul, sums"),
    ("02.04", "Softmax and cross-entropy without overflow", "losses", "cross-entropy"),
    ("02.05", "Modules, parameters, and a checkpoint file", "layers", "modules, a file"),
    ("03.01", "MNIST in batches, and a learning rate that is too big", "mnist", "MNIST, a big rate"),
    ("03.02", "Momentum: the zigzag in a narrow valley", "optim", "momentum"),
    ("03.03", "Adam: a step size for each parameter", "optim", "Adam"),
    ("03.04", "AdamW: weight decay is not L2", "optim", "AdamW"),
    ("03.05", "Learning-rate schedules: warmup and cosine decay", "optim", "schedules"),
    ("04.01", "Twenty layers that learn nothing: looking at activations and gradients", "deep", "twenty layers"),
    ("04.02", "Initialisation: keeping the signal the same size", "layers", "initialisation"),
    ("04.03", "Batch normalisation", "layers", "batch norm"),
    ("04.04", "Layer normalisation, and what the batch had to do with it", "layers", "layer norm"),
    ("04.05", "Residual connections: a path the gradient keeps", "deep", "residual"),
    ("04.06", "Five bugs that do not crash: a debugging checklist", "checks", "five bugs"),
    ("05.01", "Train, validation and test: a network that memorises random labels", "general", "random labels"),
    ("05.02", "Weight decay and dropout", "layers", "dropout"),
    ("05.03", "More data for free: augmentation", "augment", "augmentation"),
    ("05.04", "Double descent: when a bigger model overfits less", "general", "double descent"),
]

MODULE_TITLES = {
    "00": "The workbench",
    "01": "Backpropagation: an autograd engine",
    "02": "Tensors: a small PyTorch",
    "03": "Optimisers: from the plain step to AdamW",
    "04": "Deep networks that train",
    "05": "Generalisation",
}

# The rows, top to bottom: key -> its label over the row.
ROWS = {
    "research": "research",
    "models": "models",
    "experiments": "experiments: one script per lesson",
    "engine": "the engine: PyTorch's names, in numpy",
    "lab": "the lab: under every run",
}

# The layout.
LEFT, RIGHT = 14, 626
GAP = 6                              # between two pieces of a row
SPACE = 12                           # from a row's boxes down to the next row's label
DATA_W = 104                         # the data's column, right of the experiments and the engine
TOP = 6
HEIGHTS = {"research": 36, "models": 46, "experiments": 40, "engine": 40, "lab": 40}
STRIP_H = 40


def _rows():
    """{row: (its label's baseline, its boxes' top, their height)}, and the y under the last row."""
    out, y = {}, TOP
    for row in ROWS:
        out[row] = (y + 11, y + 17, HEIGHTS[row])
        y += 17 + HEIGHTS[row] + SPACE
    return out, y


ROW_Y, LAYERS_END = _rows()
STRIP_LABEL = LAYERS_END + 8 + 11
STRIP_Y = STRIP_LABEL + 6
HEIGHT = STRIP_Y + STRIP_H + 34


def order(lid):
    return [l[0] for l in LESSONS].index(lid)


def lesson(lid):
    return LESSONS[order(lid)]


def placed():
    """{key: (x, y, w, h)} for every piece."""
    out = {}
    for row in ROWS:
        keys = [k for k, p in PIECES.items() if p[0] == row]
        right = RIGHT - DATA_W - 2 * GAP if row in ("experiments", "engine") else RIGHT
        w = (right - LEFT - GAP * (len(keys) - 1)) / len(keys)
        _, y, h = ROW_Y[row]
        for i, k in enumerate(keys):
            out[k] = (LEFT + i * (w + GAP), y, w, h)
    data = [k for k, p in PIECES.items() if p[0] == "data"]
    top = ROW_Y["experiments"][1]
    bottom = ROW_Y["engine"][1] + HEIGHTS["engine"]
    h = (bottom - top - 5 * (len(data) - 1)) / len(data)
    for i, k in enumerate(data):
        out[k] = (RIGHT - DATA_W, top + i * (h + 5), DATA_W, h)
    return out


def state(key, lid, everything=False):
    """here, built or later: piece key in lesson lid's copy of the map."""
    comes = PIECES[key][3]
    if everything:
        return "here" if comes is not None else "later"
    if lesson(lid)[2] == key:
        return "here"
    return "built" if comes is not None and order(comes) <= order(lid) else "later"


def fit(s, width, sizes=(12.5, 12, 11.5, 11, 10.5), mono=False, weight=600):
    """The largest of sizes at which s fits in width (a bold line is a little wider)."""
    k = 1.04 if weight and weight >= 600 else 1.0
    return next((z for z in sizes if tw(s, z, mono) * k <= width), sizes[-1])


def wrap(s, width, size):
    """s in one line if it fits width at size, else in two, split at the space nearest the middle."""
    if tw(s, size) * 1.04 <= width or " " not in s:
        return [s]
    spaces = [i for i, c in enumerate(s) if c == " "]
    i = min(spaces, key=lambda i: abs(i - len(s) / 2))
    return [s[:i], s[i + 1:]]


def heading(f, x, y, bold, rest=""):
    """A muted label over a row: its first words bold, the rest plain, as one line of text."""
    f.add(f'<text class="tm" x="{x}" y="{y}" font-size="11.5"><tspan font-weight="600">{figlib.esc(bold)}</tspan>'
          f'{figlib.esc(rest)}</text>')


def draw(lid, everything=None):
    """The map for lesson lid (everything: light every built piece; default: lid is the first lesson)."""
    _, title, _, _ = lesson(lid)
    if everything is None:
        everything = lid == LESSONS[0][0]
    f = Fig("map" + lid.replace(".", ""), f"Where {lid} fits: {title}", HEIGHT)
    boxes = placed()
    look = {"here": ("a af", "ta", "ta", 700), "built": ("s f", "t", "tm", 600), "later": ("m f", "tm", "tm", 500)}

    # the row labels, and the data's over its column
    for row, label in ROWS.items():
        name, colon, rest = label.partition(": ")
        heading(f, LEFT, ROW_Y[row][0], name, colon + rest)
    heading(f, RIGHT - DATA_W, ROW_Y["experiments"][0], "the data")

    for key, (row, name, sub, comes) in PIECES.items():
        x, y, w, h = boxes[key]
        st = state(key, lid, everything)
        box, tcls, scls, weight = look[st]
        f.rect(x, y, w, h, box, 7, dash=st == "later")
        cx = x + w / 2
        if row in ("research", "models"):            # a module not built yet: its number, then its name
            f.text(cx, y + 13, sub, scls, 10, "middle", mono=True)
            lines = wrap(name, w - 10, 12)
            size = min(fit(line, w - 10, (12, 11.5, 11, 10.5), weight=weight) for line in lines)
            for i, line in enumerate(lines):
                f.text(cx, y + 28 + i * 13 + (0 if len(lines) > 1 or h < 40 else 3), line, tcls, size, "middle", weight)
        elif row == "data":                           # short boxes: name and what it is on two lines
            f.text(cx, y + h / 2 - 1.5, name, tcls, fit(name, w - 10, (12.5, 12, 11.5), weight=weight), "middle", weight)
            f.text(cx, y + h / 2 + 10.5, sub, scls, fit(sub, w - 10, (10, 9.5), weight=None), "middle")
        else:
            f.text(cx, y + 17, name, tcls, fit(name, w - 10, weight=weight), "middle", weight)
            f.text(cx, y + 31, sub, scls, fit(sub, w - 10, (10.5, 10, 9.5), weight=None), "middle")

    # the strip: the current module's lessons
    mod = lid[:2]
    mine = [l for l in LESSONS if l[0][:2] == mod]
    heading(f, LEFT, STRIP_LABEL, f"module {mod}", ", " + MODULE_TITLES.get(mod, ""))
    n = len(mine)
    bw = min(150, (RIGHT - LEFT - GAP * (n - 1)) / n)
    for k, (l, _, _, short) in enumerate(mine):
        st = "here" if l == lid else ("built" if order(l) < order(lid) else "later")
        box, tcls, icls, weight = look[st]
        bx = LEFT + k * (bw + GAP)
        f.rect(bx, STRIP_Y, bw, STRIP_H, box, 7, dash=st == "later")
        f.text(bx + bw / 2, STRIP_Y + 15, l, icls, 10.5, "middle", mono=True)
        f.text(bx + bw / 2, STRIP_Y + 31, short, tcls, fit(short, bw - 10, (12.5, 12, 11.5, 11, 10.5), weight=weight),
               "middle", weight)

    # legend
    ly = HEIGHT - 12
    x = LEFT
    keys = [("a af", False, f"{lid}: this lesson", "ta"), ("s f", False, "built so far", "t"),
            ("m f", True, "still to come", "tm")]
    if everything:
        keys[:2] = [("a af", False, f"{lid}: the tour, every piece built in modules 00 to 05", "ta")]
    for cls, dash, label, tcls in keys:
        f.rect(x, ly - 12, 20, 15, cls, 4, dash=dash)
        f.text(x + 27, ly, label, tcls, 12.5, weight=600 if tcls == "ta" else None)
        x += 27 + tw(label, 12.5) + 22
    return f


def lesson_titles():
    """{"03.02": its title}: the lessons written so far, from their front matter."""
    out = {}
    for mid, folder in figlib.MODULE_DIRS.items():
        d = os.path.join(figlib.LESSONS, folder)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            m = re.match(r"^(\d\d\.\d\d)-.*\.md$", name)
            if m:
                with open(os.path.join(d, name), encoding="utf-8") as fh:
                    t = re.search(r"^title:\s*(.*?)\s*$", fh.read().split("\n---", 1)[0], re.M)
                out[m.group(1)] = t.group(1) if t else ""
    return out


def write_map(lid, base=None):
    """Write lesson lid's map to <base or tracks/research/lessons>/<module folder>/figures/lid-map.svg
    (checked against the site's sanitizer on the way, figlib.write); its path."""
    keep = figlib.LESSONS
    figlib.LESSONS = base or keep
    try:
        return figlib.write(lid[:2], f"{lid}-map", draw(lid))
    finally:
        figlib.LESSONS = keep


def _check_tables():
    ids = [l[0] for l in LESSONS]
    assert ids == sorted(ids) and len(set(ids)) == len(ids), "LESSONS out of order, or a lesson twice"
    for lid, _, piece, _ in LESSONS:
        assert piece in PIECES, f"{lid}: no piece {piece!r}"
        comes = PIECES[piece][3]
        assert comes is not None and order(comes) <= order(lid), f"{lid}: its piece {piece!r} comes later"
        assert lid[:2] in figlib.MODULE_DIRS and lid[:2] in MODULE_TITLES, f"{lid}: no folder or title for its module"
    for key, (_, _, _, comes) in PIECES.items():
        assert comes is None or comes in ids, f"{key}: comes with {comes}, which LESSONS does not have"


def main(argv):
    _check_tables()
    base, ids, bad = None, [], []
    if argv[:1] == ["--all"] and len(argv) == 2:
        base = os.path.abspath(argv[1])
        ids = [l[0] for l in LESSONS]
    elif argv and all(re.match(r"^\d\d(\.\d\d)?$", a) for a in argv):
        ids = [l[0] for l in LESSONS if any(l[0] == a or l[0][:2] == a for a in argv)]
        unknown = [a for a in argv if not any(l[0] == a or l[0][:2] == a for l in LESSONS)]
        bad += [f"{a}: no such lesson in the map's table" for a in unknown]
    elif argv:
        print(__doc__.strip().split("\n\n")[1])
        return 2
    written = lesson_titles()
    if not argv:
        ids = [l[0] for l in LESSONS if l[0] in written]
    for lid in ids:
        if lid in written and written[lid] != lesson(lid)[1]:
            bad.append(f"{lid}: the lesson's title is {written[lid]!r}, this table says {lesson(lid)[1]!r}")
        p = write_map(lid, base)
        print(os.path.relpath(p, ROOT) if p.startswith(ROOT) else p)
    bad += [f"{lid}: a lesson this table does not have" for lid in written if lid not in {l[0] for l in LESSONS}]
    if not ids and not bad:
        print("no lessons written yet: name them (archmap.py 03 04.02) or preview with --all DIR")
    for b in bad:
        print("problem:", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
