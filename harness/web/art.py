"""Module art: icons, covers and lesson figures that a track ships as plain SVG files.

    tracks/<id>/art.svg                         the track's picture on its home page card: viewBox 0 0 280 160,
                                                styled by the .art classes; .flow, .draw (with pathLength="1")
                                                and .stream mark the one element that moves on hover
    tracks/<id>/icon.svg                        viewBox 0 0 20 20, a currentColor line icon for the top bar
    tracks/<id>/lessons/NN-slug/icon.svg        viewBox 0 0 20 20, a currentColor line icon
    tracks/<id>/lessons/NN-slug/cover.svg       viewBox 0 0 640 300, styled by the .art classes in app.css
    tracks/<id>/lessons/NN-slug/NN.LL-*.svg     a figure for one lesson (shown at the top of its notes)
    tracks/<id>/lessons/NN-slug/figures/*.svg   inline figures: a lesson line of its own
                                                ![Caption](figures/NN.LL-name.svg) renders it there
    outlines/<stem>/NN/icon.svg, cover.svg      the same two files for module NN of outlines/<stem>.md
    outlines/<stem>/art.svg, icon.svg           the track-level pair for an outline

Files are optional. Each is sanitized (see sanitize) and inlined, so currentColor and the theme
variables work in dark mode. Anything missing, oversized or unparseable renders as nothing.

Stepped figures. An inline figure can show a process (a sort, a heap fixing itself, a search
spreading over a graph) as frames the reader steps through. It is still one .svg file, referenced
the same way. Each direct child of the root <svg> that is a <g class="step"> is one frame, in
document order; every other top-level element is the base, drawn first, under every frame. A step
group may start with a <title>: that text is the step's own caption line (what just happened). The
page holds every frame, one under another, each a whole diagram (the base, then that step) with
"Step k of n" and its caption: what a reader without scripts and a printout get. app.js turns that
into one frame at a time with Back and Next. Each frame is sanitized with ids of its own, so a
marker in the base's <defs> resolves in every frame. A file with fewer than two step groups is an
ordinary figure. A stepped figure may have MAX_STEPS frames, and MAX_STEPPED bytes of markup over
all of them (the page carries the base once per frame); past either the page shows its last frame
as an ordinary still figure, and ./learn check reports it (figure_problems). art/steps.py helps a
figure generator write the step groups.
"""

import os
import re
import xml.etree.ElementTree as ET

from harness.web.markdown import FIGURE as FIGURE_LINE

MAX_SVG = 200 * 1024
MAX_STEPS = 40                  # frames a stepped figure may have
MAX_STEPPED = 1024 * 1024       # bytes of markup all its frames may come to together

TAGS = {"svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "tspan",
        "defs", "marker", "title", "desc"}
TEXT_TAGS = {"text", "tspan", "title", "desc"}
ATTRS = {
    # identity and structure
    "class", "id", "viewBox", "xmlns", "transform", "preserveAspectRatio",
    # geometry
    "d", "points", "x", "y", "width", "height", "r", "rx", "ry", "cx", "cy", "x1", "y1", "x2", "y2", "dx", "dy",
    # presentation
    "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset",
    "stroke-opacity", "stroke-miterlimit", "fill-opacity", "fill-rule", "opacity", "vector-effect",
    "marker-start", "marker-mid", "marker-end", "markerWidth", "markerHeight", "markerUnits", "refX", "refY", "orient",
    "pathLength",
    "text-anchor", "dominant-baseline", "font-size", "font-weight", "letter-spacing",
}
VALUE_OK = re.compile(r"^[#\w\s.,()%+\-/:]*$")
URL_REF = re.compile(r"url\(\s*#([\w.-]+)\s*\)")
BAD_VALUE = re.compile(r"javascript:|data:|expression\(|@import|<|&", re.I)
FIGURE_SRC = re.compile(r"^figures/[A-Za-z0-9][A-Za-z0-9_.-]*\.svg$")
FENCE_LINE = re.compile(r"^\s*(`{3,}|~{3,})")
_counter = [0]
_cache = {}


def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _parse(source):
    """The root element of the SVG text `source`, or None if it is too big, declares a DOCTYPE or
    an ENTITY, or does not parse."""
    if not isinstance(source, str) or len(source) > MAX_SVG or re.search(r"<!(DOCTYPE|ENTITY)", source, re.I):
        return None
    try:
        return ET.fromstring(source)
    except ET.ParseError:
        return None


def sanitize(source, prefix="art"):
    """Return safe inline SVG markup for `source`, or "" if it is not an acceptable SVG.

    Only allowlisted elements and attributes survive; script, foreignObject, style, on* handlers
    and any href are dropped, and url() may only point at an id inside the same file. `source` may
    also be an already parsed <svg> element (a frame of a stepped figure)."""
    root = source if ET.iselement(source) else _parse(source)
    if root is None or _local(root.tag) != "svg":
        return ""

    def render(el, top):
        name = _local(el.tag)
        if name not in TAGS:
            return ""
        attrs = []
        for key, value in el.attrib.items():
            key = _local(key) if not key.startswith("{") else ""
            if not key or key not in ATTRS or key.lower().startswith("on"):
                continue
            if top and key in ("width", "height", "xmlns"):
                continue  # CSS sizes the root; xmlns is added below
            if key == "id":
                if not re.match(r"^[\w.-]+$", value):
                    continue
                value = f"{prefix}-{value}"
            elif key == "class":
                if not re.match(r"^[\w\s-]*$", value):
                    continue
            elif key in ("d", "points", "transform", "viewBox"):
                if not re.match(r"^[\w\s.,()+\-]*$", value):
                    continue
            elif not VALUE_OK.match(value) or BAD_VALUE.search(value):
                continue
            if "url(" in value:
                refs = URL_REF.findall(value)
                if not refs or URL_REF.sub("", value).strip() not in ("", "none") and key not in ("fill", "stroke"):
                    continue
                value = URL_REF.sub(lambda m: f"url(#{prefix}-{m.group(1)})", value)
            attrs.append(f' {key}="{_esc(value)}"')
        if top:
            attrs.append(' xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false"')
        inner = _esc(el.text or "") if name in TEXT_TAGS else ""
        for child in el:
            inner += render(child, False)
            if name in TEXT_TAGS and child.tail:
                inner += _esc(child.tail)
        return f"<{name}{''.join(attrs)}>{inner}</{name}>"

    out = render(root, True)
    return out if "viewBox" in out.split(">", 1)[0] else ""


def module_dir(track, mid):
    ldir = os.path.join(track.root, "lessons")
    try:
        names = sorted(os.listdir(ldir))
    except OSError:
        return None
    for n in names:
        if re.match(r"^" + re.escape(mid) + r"-", n) and os.path.isdir(os.path.join(ldir, n)):
            return os.path.join(ldir, n)
    return None


def _load(path):
    """Sanitized markup for one SVG file, cached by mtime; "" when missing or unusable."""
    try:
        st = os.stat(path)
        if not os.path.isfile(path) or os.path.islink(path) or st.st_size > MAX_SVG:
            return ""
        key = (path, st.st_mtime_ns, st.st_size)
        if key not in _cache:
            _counter[0] += 1
            with open(path, encoding="utf-8", errors="replace") as f:
                _cache[key] = sanitize(f.read(), prefix=f"art{_counter[0]}")
        return _cache[key]
    except OSError:
        return ""


def module_art(track, mid, kind):
    """kind is "icon" or "cover". Returns markup or ""."""
    d = module_dir(track, mid)
    return _load(os.path.join(d, kind + ".svg")) if d else ""


# What a track without its own art.svg shows on its card: a neutral stack of source files.
DEFAULT_ART = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 160">
<rect class="m f" x="92" y="22" width="112" height="116" rx="8" stroke-width="1.5"/>
<rect class="m f" x="82" y="30" width="112" height="116" rx="8" stroke-width="1.5"/>
<rect class="s f" x="72" y="38" width="112" height="116" rx="8" stroke-width="1.75"/>
<path class="m" d="M88 62h48M88 76h66M88 90h40M88 104h58M88 118h30" stroke-width="2" stroke-linecap="round"/>
<path class="a" d="M150 128l-10 8 10 8M166 128l10 8-10 8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


def track_art(track, kind):
    """kind is "art" (the home page card) or "icon" (the top bar). Returns markup or "";
    for "art", a track with none gets DEFAULT_ART."""
    got = _load(os.path.join(track.root, kind + ".svg")) if kind in ("art", "icon") else ""
    return got or (sanitize(DEFAULT_ART, "art-default") if kind == "art" else "")


def outline_track_art(outline, kind):
    """The same pair for an outline: outlines/<stem>/art.svg and icon.svg."""
    got = _load(os.path.join(outline.art_dir, kind + ".svg")) if kind in ("art", "icon") else ""
    return got or (sanitize(DEFAULT_ART, "art-default") if kind == "art" else "")


def track_map(track):
    """The track's architecture: its first lesson's map, lessons/NN-slug/figures/<id>-map.svg, or ""."""
    first = (track.core_lessons or track.lessons or [None])[0]
    d = module_dir(track, first.module[0]) if first else None
    return _load(os.path.join(d, "figures", f"{first.id}-map.svg")) if d else ""


def outline_art(outline, mid, kind):
    """Module art for an outline (a track not built yet): outlines/<stem>/NN/<kind>.svg, or ""."""
    if kind not in ("icon", "cover") or not re.match(r"^\d\d$", mid or ""):
        return ""
    return _load(os.path.join(outline.art_dir, mid, kind + ".svg"))


def lesson_figure(track, lesson):
    d = module_dir(track, lesson.module[0])
    if not d:
        return ""
    try:
        names = sorted(n for n in os.listdir(d) if re.match(r"^" + re.escape(lesson.id) + r"-.*\.svg$", n))
    except OSError:
        return ""
    return _load(os.path.join(d, names[0])) if names else ""


def figure_path(doc, src):
    """The file an inline figure names, or None when `src` is not a plain figures/<name>.svg
    next to the lesson doc `doc` (no subdirectories, no .., no absolute paths, no URLs)."""
    if not doc or not isinstance(src, str) or not FIGURE_SRC.match(src) or ".." in src:
        return None
    base = os.path.realpath(os.path.join(os.path.dirname(doc), "figures"))
    path = os.path.join(base, src.split("/", 1)[1])
    if os.path.dirname(os.path.realpath(path)) != base:
        return None
    return path


def doc_figure(doc, src):
    """Sanitized markup for an inline figure of the lesson doc `doc`, or "" if refused or missing.
    A stepped figure is a list [(frame markup, step caption)] instead (see the module doc); one
    past the limits is the markup of its last frame, an ordinary figure."""
    path = figure_path(doc, src)
    if not path:
        return ""
    frames = _load_steps(path)
    if frames is None:
        return _load(path)
    return frames[-1][0] if steps_over(frames) else frames


# ---------------------------------------------------------------- stepped figures

_steps_cache = {}


def _is_step(el):
    return _local(el.tag) == "g" and "step" in (el.get("class") or "").split()


def split_steps(source, prefix="art"):
    """[(markup, caption)] for the stepped figure `source`, one per step group in document order:
    the base (every other top-level element, in its order) with that step drawn on top, sanitized
    with ids of its own (prefix-1-..., prefix-2-...), so every frame's url(#...) finds its own copy.
    caption is the text of the step's leading <title> ("" without one), which leaves the frame.
    None when source is not a stepped figure: fewer than two step groups, or not a usable SVG."""
    root = _parse(source)
    if root is None or _local(root.tag) != "svg":
        return None
    steps = [el for el in root if _is_step(el)]
    if len(steps) < 2:
        return None
    base = [el for el in root if not _is_step(el)]
    frames = []
    for k, step in enumerate(steps, 1):
        kids = list(step)
        caption = ""
        if kids and _local(kids[0].tag) == "title":
            caption = " ".join("".join(kids[0].itertext()).split())
            kids = kids[1:]
        group = ET.Element(step.tag, step.attrib)
        group.extend(kids)
        frame = ET.Element(root.tag, root.attrib)
        frame.extend(base + [group])
        markup = sanitize(frame, f"{prefix}-{k}")
        if not markup:
            return None
        frames.append((markup, caption))
    return frames


def steps_over(frames):
    """Why a stepped figure is past the limits ("has 41 steps, more than 40"), or "" when it is not."""
    if len(frames) > MAX_STEPS:
        return f"has {len(frames)} steps, more than {MAX_STEPS}"
    size = sum(len(markup) for markup, _ in frames)
    if size > MAX_STEPPED:
        return f"comes to {size // 1024} KB over its {len(frames)} frames, more than {MAX_STEPPED // 1024} KB"
    return ""


def _load_steps(path):
    """split_steps for one file, cached by mtime; None when it is not a stepped figure. A file that
    is one takes the next art<N> prefix; any other file leaves the numbering as it was."""
    try:
        st = os.stat(path)
        if not os.path.isfile(path) or os.path.islink(path) or st.st_size > MAX_SVG:
            return None
        key = (path, st.st_mtime_ns, st.st_size)
        if key not in _steps_cache:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            n = _counter[0] + 1
            _steps_cache[key] = split_steps(text, prefix=f"art{n}")
            if _steps_cache[key] is not None:
                _counter[0] = n
        return _steps_cache[key]
    except OSError:
        return None


def figure_refs(text):
    """[(line number, caption, src)] for every figure line in a markdown doc, outside code fences."""
    out, fence = [], None
    for n, line in enumerate((text or "").split("\n"), 1):
        fm = FENCE_LINE.match(line)
        if fm:
            fence = None if fence and line.strip().startswith(fence) else (fence or fm.group(1))
            continue
        m = None if fence else FIGURE_LINE.match(line)
        if m:
            out.append((n, m.group(1).strip(), m.group(2)))
    return out


def figure_problems(doc):
    """Problems with the inline figures a lesson doc references: bad paths, missing or unusable files."""
    try:
        with open(doc, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return []
    out = []
    for n, _, src in figure_refs(text):
        path = figure_path(doc, src)
        if path is None:
            out.append((n, f"figure {src} is not a figures/<name>.svg next to the lesson"))
        elif not os.path.isfile(path):
            out.append((n, f"figure {src} does not exist"))
        elif not _load(path):
            out.append((n, f"figure {src} is not a usable SVG (too big, unparseable, or no viewBox)"))
        elif steps_over(_load_steps(path) or []):
            over = steps_over(_load_steps(path))
            out.append((n, f"figure {src} {over}: the page shows only its last step, as a still figure"))
    return out
