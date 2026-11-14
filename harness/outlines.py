"""Outlines: tracks that are planned but not built yet (templates/outline.md).

    outlines/<stem>.md              front matter, intro, modules, library
    outlines/<stem>/NN/cover.svg    optional module art, same contract as a track's
    outlines/<stem>/NN/icon.svg     (see harness/web/art.py)

An outline has no lessons to open, no workspace and no tests. The site shows it as a
coming-soon track: its modules, their planned lesson titles and its library.
Everything here is read generically, so a new outline file needs no code.
"""

import os
import re

from harness.core import ROOT, read_header

# LEARN_OUTLINES_DIR points the tools at another folder of outlines (the web tests use it).
OUTLINES_DIR = os.environ.get("LEARN_OUTLINES_DIR") or os.path.join(ROOT, "outlines")

ID_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
MODULE_HEAD = re.compile(r"^##\s+Module\s+(\d\d)\s*(?:-+|:)?\s*(.*?)\s*#*\s*$", re.I)
H2 = re.compile(r"^##\s+(.+?)\s*#*\s*$")
LESSON = re.compile(r"^(\d\d\.\d\d)\s+(.+)$")
FIELD = re.compile(r"^-\s+([A-Za-z][A-Za-z ]*?)\s*:\s*(.*)$")
KEY_REF = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_.-]*)\]")
URL = re.compile(r"https?://[^\s<>\"'|]+")
KIND_ORDER = ("book", "video", "article", "paper", "course", "code")
MAX_OUTLINE = 256 * 1024

_cache = {}


class Module:
    def __init__(self, mid, title):
        self.id = mid              # "00"
        self.title = title
        self.goal = ""
        self.build = ""            # "You build"
        self.value = ""
        self.lessons = []          # [(NN.LL, title)]
        self.learn_from = []       # library keys, in the order cited


class Resource:
    def __init__(self, key, kind, title, by, where):
        self.key, self.kind, self.title, self.by, self.where = key, kind, title, by, where
        m = URL.search(where or "")
        self.url = m.group(0).rstrip(".,;)") if m else None


class Outline:
    def __init__(self, path):
        self.path = path
        self.stem = os.path.splitext(os.path.basename(path))[0]
        self.art_dir = os.path.join(os.path.dirname(path), self.stem)
        self.meta = {}
        self.id = self.stem
        self.title = self.stem
        self.kind = ""
        self.status = "coming soon"
        self.audience = self.prerequisites = self.outcome = ""
        self.upstream = ""         # the industry repositories it is planned to follow, as proposed
        self.intro = ""
        self.modules = []
        self.library = []

    @property
    def lessons(self):
        return [l for m in self.modules for l in m.lessons]

    @property
    def status_label(self):
        """The status as a label: "Coming soon" unless the outline says otherwise."""
        s = self.status.strip() or "coming soon"
        return s[0].upper() + s[1:]

    def resource(self, key):
        return next((r for r in self.library if r.key == key), None)

    def library_by_kind(self):
        """[(kind, [resources])], known kinds in the template's order, then any others."""
        kinds = []
        for r in self.library:
            if r.kind not in kinds:
                kinds.append(r.kind)
        kinds.sort(key=lambda k: (KIND_ORDER.index(k) if k in KIND_ORDER else len(KIND_ORDER), k))
        return [(k, [r for r in self.library if r.kind == k]) for k in kinds]


def _body(text):
    """The lines after the front matter."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for k in range(1, len(lines)):
            if lines[k].strip() == "---":
                return lines[k + 1:]
    return lines


def _cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _library(lines):
    rows = [l for l in lines if l.strip().startswith("|")]
    if not rows:
        return []
    head = [c.lower() for c in _cells(rows[0])]
    col = {name: head.index(name) for name in ("key", "kind", "title", "by", "where") if name in head}
    if "key" not in col or "title" not in col:
        return []
    out, seen = [], set()
    for row in rows[1:]:
        cells = _cells(row)
        if all(re.match(r"^:?-{2,}:?$", c) for c in cells if c):
            continue  # the separator row
        get = lambda name: cells[col[name]] if name in col and col[name] < len(cells) else ""
        key = get("key")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(Resource(key, get("kind").lower() or "other", get("title") or key, get("by"), get("where")))
    return out


def _module(mid, title, lines):
    mod = Module(mid, title or f"Module {mid}")
    field = None
    for raw in lines:
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        fm = FIELD.match(line) if indent < 2 else None
        if fm:
            field = fm.group(1).strip().lower()
            value = fm.group(2).strip()
            if field == "goal":
                mod.goal = value
            elif field == "you build":
                mod.build = value
            elif field == "value":
                mod.value = value
            elif field == "learn from":
                mod.learn_from = KEY_REF.findall(value)
            continue
        if field == "lessons" and line.startswith("- "):
            lm = LESSON.match(line[2:].strip())
            if lm:
                mod.lessons.append((lm.group(1), lm.group(2).strip()))
            continue
        # a wrapped line continues whatever came before it
        if field == "lessons" and mod.lessons:
            lid, lt = mod.lessons[-1]
            mod.lessons[-1] = (lid, f"{lt} {line}")
        elif field == "goal":
            mod.goal = f"{mod.goal} {line}".strip()
        elif field == "you build":
            mod.build = f"{mod.build} {line}".strip()
        elif field == "value":
            mod.value = f"{mod.value} {line}".strip()
        elif field == "learn from":
            mod.learn_from += KEY_REF.findall(line)
    return mod


def parse(path):
    """Read one outline file. Never raises on a malformed file: missing parts stay empty."""
    o = Outline(path)
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read(MAX_OUTLINE)
    meta = read_header(path)
    o.meta = meta
    if ID_OK.match(meta.get("id", "")):
        o.id = meta["id"]
    o.kind = meta.get("kind", "")
    o.status = meta.get("status", "") or "coming soon"
    o.audience = meta.get("audience", "")
    o.prerequisites = meta.get("prerequisites", "")
    o.outcome = meta.get("outcome", "")
    o.upstream = meta.get("upstream", "")

    lines = _body(text)
    sections, pre = [], []
    cur = None
    for line in lines:
        hm = H2.match(line)
        if hm:
            cur = [line, []]
            sections.append(cur)
        elif cur is None:
            pre.append(line)
        else:
            cur[1].append(line)

    title = meta.get("title", "")
    paras, para = [], []
    for line in pre + [""]:
        if re.match(r"^#\s+", line):
            title = title or line.lstrip("#").strip()
            continue
        if line.strip():
            para.append(line.strip())
        elif para:
            paras.append(" ".join(para))
            para = []
    o.title = title or o.stem
    # the intro is what comes before the first module, minus the status note ("**Coming soon.** ...")
    o.intro = "\n\n".join(p for p in paras if not p.startswith("**"))

    for head, body in sections:
        mm = MODULE_HEAD.match(head)
        if mm:
            if any(m.id == mm.group(1) for m in o.modules):
                continue
            o.modules.append(_module(mm.group(1), mm.group(2), body))
        elif H2.match(head).group(1).strip().lower() == "library":
            o.library = _library(body)
    o.modules.sort(key=lambda m: m.id)
    return o


def discover(track_ids=()):
    """Every outline in OUTLINES_DIR, by file name. An id taken by a real track (or by an
    earlier outline) is skipped: the built track wins."""
    try:
        names = sorted(n for n in os.listdir(OUTLINES_DIR) if n.endswith(".md") and not n.startswith("."))
    except OSError:
        return []
    out, taken = [], set(track_ids)
    for n in names:
        path = os.path.join(OUTLINES_DIR, n)
        try:
            st = os.stat(path)
            if not os.path.isfile(path):
                continue
            key = (path, st.st_mtime_ns, st.st_size)
            if key not in _cache:
                _cache[key] = parse(path)
            o = _cache[key]
        except OSError:
            continue
        if o.id in taken:
            continue
        taken.add(o.id)
        out.append(o)
    return out


def problems(o):
    """What `./learn check` reports for one outline: the format rules in templates/outline.md."""
    out = []
    name = os.path.relpath(o.path, ROOT)
    if not ID_OK.match(o.meta.get("id", "")):
        out.append(f"{name}: front matter needs an id (letters, digits, - and _)")
    if not o.meta.get("title"):
        out.append(f"{name}: front matter needs a title")
    if not o.modules:
        out.append(f"{name}: no '## Module NN - Title' sections")
    keys = {r.key for r in o.library}
    for m in o.modules:
        for field, value in (("Goal", m.goal), ("You build", m.build), ("Value", m.value)):
            if not value:
                out.append(f"{name}: module {m.id} has no {field}")
        if not m.lessons:
            out.append(f"{name}: module {m.id} lists no lessons")
        for lid, _ in m.lessons:
            if not lid.startswith(m.id + "."):
                out.append(f"{name}: lesson {lid} is listed under module {m.id}")
        for k in m.learn_from:
            if k not in keys:
                out.append(f"{name}: module {m.id} cites [{k}], which is not in the Library")
    return out
