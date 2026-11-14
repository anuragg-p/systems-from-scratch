"""Data helpers and HTML pages for the web UI (no HTTP in here)."""

import html
import json
import fnmatch
import itertools
import os
import re
import threading
import urllib.parse

from harness import core
from harness import outlines as ol
from harness import timeline as tl
from harness import workspace as ws
from harness.web import art, highlight
from harness.web.markdown import inline, render, strip_comments

LESSON_ID = re.compile(r"^\d\d(\.\d\d)?$")
FULL_ID = re.compile(r"^\d\d\.\d\d$")
TRACK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
MAX_FILE = 400_000
TAGLINE = "Code first, theory second."
SITE = "systems from scratch"

_discover_lock = threading.Lock()
esc = html.escape

ARROW = '<svg class="ic" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3 8h10M9 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
CHEV_R = '<svg class="ic chev" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
CLOSE = '<svg class="ic" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
COPY = '<svg class="ic" viewBox="0 0 16 16" width="13" height="13" aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M10.5 3.5v-.5a1 1 0 00-1-1h-6a1 1 0 00-1 1v6a1 1 0 001 1h.5" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>'
FOLDER = '<svg class="ic" viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><path d="M1.8 4.2c0-.7.5-1.2 1.2-1.2h3l1.4 1.6H13c.7 0 1.2.5 1.2 1.2v6c0 .7-.5 1.2-1.2 1.2H3c-.7 0-1.2-.5-1.2-1.2z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>'
CHEV_L = '<svg class="ic" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M10 3L5 8l5 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
UPDOWN = '<svg class="ic" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M5 6l3-3 3 3M5 10l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
PLAY = '<svg class="ic" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M4 2.5v11l9-5.5z" fill="currentColor"/></svg>'
THEME = '<svg class="ic" viewBox="0 0 16 16" width="15" height="15" aria-hidden="true"><circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 2.5a5.5 5.5 0 010 11z" fill="currentColor"/></svg>'
MENU = '<svg class="ic" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'
GRID = '<svg class="ic" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><rect x="1.5" y="1.5" width="5" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="9.5" y="1.5" width="5" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="1.5" y="9.5" width="5" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="9.5" y="9.5" width="5" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>'
HOME = '<svg class="ic" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M2.5 7.5L8 2.5l5.5 5v6h-4v-4h-3v4h-4z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>'
EXT = '<svg class="ic" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M5 11l6-6M6.5 5H11v4.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
MAP = '<svg class="ic" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M1.5 3.5l4-1.5 5 1.5 4-1.5v10.5l-4 1.5-5-1.5-4 1.5zM5.5 2v10.5M10.5 3.5V14" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>'
# The vertical stroke folds away when the extensions are open, so the plus reads as a minus.
PLUS = ('<svg class="ic plus" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3 8h10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
        '<path class="plus-v" d="M8 3v10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>')
# Runs where the extensions list is parsed, before it is painted: a choice remembered in this
# browser wins over the server's default, except on an optional lesson, which always shows it.
EXT_SCRIPT = ('<script>(function(){var e=document.getElementById("ext");if(!e||e.getAttribute("data-force")==="1")return;'
              'var v=null;try{v=localStorage.getItem("ext:"+e.getAttribute("data-track"))}catch(x){}'
              'if(v!=="1"&&v!=="0")return;document.getElementById("ext-toggle").setAttribute("aria-expanded",v==="1"?"true":"false");'
              'document.getElementById("ext-list").hidden=v!=="1"})()</script>')


# ---------------------------------------------------------------- data

def tracks():
    with _discover_lock:
        return core.discover_tracks()


def find_track(track_id):
    if not TRACK_ID.match(track_id or ""):
        return None
    for t in tracks():
        if t.id == track_id:
            return t
    return None


def outlines():
    """Tracks that are only outlines so far (outlines/*.md), minus any id a real track has."""
    return ol.discover([t.id for t in tracks()])


def find_outline(track_id):
    if not TRACK_ID.match(track_id or ""):
        return None
    return next((o for o in outlines() if o.id == track_id), None)


def lesson_regions(track, lid):
    try:
        return [r for r in ws.scan_tree(track.module, track.root) if r.lesson == lid]
    except Exception:
        return []


def doc_info(lesson):
    """(meta header, body markdown) for a lesson doc, or ({}, None)."""
    if not lesson.doc:
        return {}, None
    meta = core.read_header(lesson.doc)
    with open(lesson.doc, encoding="utf-8", errors="replace") as f:
        text = f.read()
    # Authors' notes in HTML comments (./learn verify's annotations) are never part of the page:
    # gone before the doc is split into steps, so no step, lead-in or summary can show them.
    lines = strip_comments(text.replace("\r\n", "\n")).splitlines()
    if lines and lines[0].strip() == "---":
        for k in range(1, len(lines)):
            if lines[k].strip() == "---":
                lines = lines[k + 1:]
                break
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^# ", lines[0]):
        lines.pop(0)  # the page header already shows id and title
    return meta, "\n".join(lines)


def code_files(track, lesson, meta):
    """-> (list of (name, source, truncated), note or None)."""
    root = os.path.realpath(track.root)
    declared = [x.strip() for x in meta.get("code", "").split(",") if x.strip()]
    declared = [x for x in declared if "<" not in x]
    files, missing = [], []
    for name in declared:
        path = os.path.realpath(os.path.join(root, name))
        if not (path == root or path.startswith(root + os.sep)) or not os.path.isfile(path):
            missing.append(name)
            continue
        files.append((name, *_read(path)))
    note = None
    if files and missing:
        note = "Not in the track yet: " + ", ".join(missing)
    return files, note


def _read(path):
    with open(path, "rb") as f:
        data = f.read(MAX_FILE + 1)
    return data[:MAX_FILE].decode("utf-8", errors="replace"), len(data) > MAX_FILE


def safe_track(t):
    """Track metadata that survives a broken track.py."""
    try:
        return t.title, t.kind, getattr(t.module, "SUMMARY", "")
    except Exception as e:  # a track's track.py is someone's work in progress
        return t.id, "", f"track.py failed to load: {type(e).__name__}: {e}"


WEB_URL = re.compile(r"^https?://[^\s\"'<>]+$")
NOTICES = {"LICENSE", "NOTICE", "COPYING"}   # licence files: in the Files drawer, never under "The code"


def upstreams(track):
    """What a track is built on: UPSTREAM in its track.py, one dict or a list of them, each with
    name, url (http or https), licence, owes (one sentence: what the track owes it) and, as they
    apply, copyright, derived (the code is derived from it: every lesson says so), licence_file
    (under the track, shown whole on /credits), also ([(label, url)]) and chip (the home card's).
    [] without one, or when track.py does not load."""
    try:
        up = getattr(track.module, "UPSTREAM", None)
    except Exception:
        return []
    up = [up] if isinstance(up, dict) else up
    if not isinstance(up, (list, tuple)):
        return []
    return [u for u in up if isinstance(u, dict) and isinstance(u.get("name"), str) and u["name"]
            and WEB_URL.match(str(u.get("url") or ""))]


def licence_label(u):
    """"MIT" -> "MIT licence"; a value that says what it is already ("Public domain") stays."""
    lic = str(u.get("licence") or "").strip()
    return lic if not lic or re.search(r"licen[cs]e|domain", lic, re.I) else f"{lic} licence"


def licence_text(track, u):
    """The whole of u's licence_file, a file under the track's root, or ""."""
    name = u.get("licence_file")
    if not isinstance(name, str) or not name:
        return ""
    root = os.path.realpath(track.root)
    path = os.path.realpath(os.path.join(root, name))
    if not path.startswith(root + os.sep) or not os.path.isfile(path):
        return ""
    return _read(path)[0]


def is_notice(rel):
    """A licence file (LICENSE, NOTICE or COPYING, with any extension)."""
    return os.path.splitext(os.path.basename(rel))[0].upper() in NOTICES


def modules_of(track):
    """[(module id, title, [lessons])] in order."""
    out = []
    for l in track.lessons:
        if not out or out[-1][0] != l.module[0]:
            out.append((l.module[0], l.module[1], []))
        out[-1][2].append(l)
    return out


def split_modules(track):
    """(core modules, optional modules), each [(module id, title, [lessons])] in order."""
    mods = modules_of(track)
    return [m for m in mods if not track.is_optional(m[0])], [m for m in mods if track.is_optional(m[0])]


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def lesson_path(track, lesson):
    """The lessons one walks through with lesson: the core, or the one extension it belongs to."""
    if not lesson.optional:
        return track.core_lessons
    return [l for l in track.lessons if l.module[0] == lesson.module[0]]


# ---------------------------------------------------------------- shell

def page(title, body, track=None, lesson=None, home=False, bottom="", outline=None):
    """The shared shell. home=True is the landing layout (top bar only).
    outline is a track that is only an outline: its overview, with a sidebar of module anchors."""
    if home:
        # every track, built ones first, then the outlines (quieter); the CSS scrolls the row when it does not fit
        ids = [(t.id, "") for t in tracks()] + [(o.id, " is-soon") for o in outlines()]
        links = "".join(f'<a class="nav-link{soon}" href="/t/{esc(i)}">{esc(i)}</a>' for i, soon in ids)
        left = f'<a class="brand" href="/">{esc(SITE)}</a><nav class="nav-links" aria-label="Tracks">{links}</nav>'
        side, cls = "", "home"
    else:
        left = f'<a class="brand" href="/">{esc(SITE)}</a>'
        owner = track or outline
        if owner:
            tt = safe_track(track)[0] if track else outline.title
            icon = art.track_art(track, "icon") if track else art.outline_track_art(outline, "icon")
            icon = f'<span class="mod-ic tp-ic">{icon}</span>' if icon else GRID
            crumbs = f'<span class="bar-div"></span><a class="track-pill" href="/t/{esc(owner.id)}">{icon}<span>{esc(tt)}</span>{UPDOWN}</a>'
            if lesson:
                crumbs += f'<span class="crumbs"><a href="/t/{esc(track.id)}">Overview</a>{CHEV_R}<b>{esc(lesson.title)}</b></span>'
            else:
                crumbs += '<span class="crumbs"><b>Overview</b></span>'
            left += crumbs
        side = sidebar(track, lesson) if track else (outline_sidebar(outline) if outline else "")
        cls = "app"
    menu = f'<button class="btn icon menu-btn" id="menu" type="button" aria-label="Open navigation">{MENU}</button>' if side else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<script>var t="light";try{{t=localStorage.getItem("theme")||"light"}}catch(e){{}}document.documentElement.setAttribute("data-theme",t)</script>
<link rel="preload" href="/static/fonts/Figtree.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/static/fonts/GeistMonoVariable.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/static/app.css">
</head>
<body class="{cls}">
<header class="topbar"><div class="topbar-in">
{menu}{left}
<span class="spacer"></span>
<button class="btn icon" id="theme" type="button" aria-label="Toggle light and dark theme">{THEME}</button>
</div></header>
{side}
<main class="main">
{body}
{site_foot(track, lesson)}
</main>
{bottom}
<div class="scrim" id="scrim"></div>
<script src="/static/app.js"></script>
</body>
</html>
"""


def site_foot(track=None, lesson=None):
    """The quiet line at the foot of every page: the way to /credits and, on a lesson of a track
    whose code is derived from another project's, which project and its licence."""
    left = f'<span>{esc(SITE)}</span>'
    if track is not None and lesson is not None:
        derived = [u for u in upstreams(track) if u.get("derived")]
        if derived:
            left = "".join(f'<a class="sf-link" href="/credits#{esc(track.id)}">Code derived from {esc(u["name"])}'
                           f'{", " + esc(licence_label(u)) if licence_label(u) else ""}</a>' for u in derived)
    return (f'<footer class="site-foot{" wide" if lesson is not None else ""}"><span class="sf-l">{left}</span>'
            f'<a class="sf-link" href="/credits">Credits</a></footer>')


def side_module(track, mid, mtitle, lessons, lesson, optional=False):
    op = " open" if lesson and mid == lesson.module[0] else ""
    items = "".join(
        f'<li><a class="side-lesson{" active" if lesson and l.id == lesson.id else ""}" href="/t/{esc(track.id)}/{esc(l.id)}">'
        f'<span class="sl-t">{esc(l.title)}</span></a></li>' for l in lessons)
    icon = art.module_art(track, mid, "icon")
    icon = f'<span class="mod-ic">{icon}</span>' if icon else ""
    tag = '<span class="opt-tag">optional</span>' if optional else ""
    return (f'<details class="mod"{op}><summary><span class="mn">{esc(mid)}</span>{CHEV_R}{icon}'
            f'<span class="mt">{esc(mtitle)}</span>{tag}<span class="mc">{len(lessons)}</span></summary><ul>{items}</ul></details>')


def sidebar(track, lesson):
    overview_cls = " active" if lesson is None else ""
    out = [f'<aside class="side" id="side"><nav aria-label="Course">',
           f'<a class="side-item" href="/">{MAP}<span>All tracks</span></a>',
           '<div class="side-label">Track</div>',
           f'<a class="side-item{overview_cls}" href="/t/{esc(track.id)}">{HOME}<span>Overview</span></a>',
           '<div class="side-label">Modules</div>']
    core, optional = split_modules(track)
    for mid, mtitle, lessons in core:
        out.append(side_module(track, mid, mtitle, lessons, lesson))
    if optional:
        # Collapsed unless you are on an optional lesson; EXT_SCRIPT then applies the
        # choice this browser remembers for the track.
        viewing = bool(lesson and lesson.optional)
        mods = "".join(side_module(track, mid, mtitle, lessons, lesson, optional=True)
                       for mid, mtitle, lessons in optional)
        out.append(f'<div class="ext" id="ext" data-track="{esc(track.id)}" data-force="{"1" if viewing else "0"}">'
                   f'<button class="ext-toggle" type="button" id="ext-toggle" aria-expanded="{"true" if viewing else "false"}" aria-controls="ext-list">'
                   f'<span class="ext-ic">{PLUS}</span><span class="mt">Extensions</span><span class="mc">{len(optional)}</span></button>'
                   f'<div class="ext-list" id="ext-list"{"" if viewing else " hidden"}>{mods}</div></div>{EXT_SCRIPT}')
    out.append("</nav></aside>")
    return "".join(out)


def outline_sidebar(o):
    """An outline has no lessons to open: the overview, then its modules as anchors on the page."""
    out = ['<aside class="side" id="side"><nav aria-label="Course">',
           f'<a class="side-item" href="/">{MAP}<span>All tracks</span></a>',
           f'<div class="side-label">{esc(o.status_label)}</div>',
           f'<a class="side-item active" href="/t/{esc(o.id)}">{HOME}<span>Overview</span></a>',
           '<div class="side-label">Modules</div>']
    for m in o.modules:
        icon = art.outline_art(o, m.id, "icon")
        icon = f'<span class="mod-ic">{icon}</span>' if icon else ""
        out.append(f'<a class="side-mod" href="#m-{esc(m.id)}"><span class="mn">{esc(m.id)}</span>{icon}'
                   f'<span class="mt">{esc(m.title)}</span><span class="mc">{len(m.lessons)}</span></a>')
    out.append("</nav></aside>")
    return "".join(out)


# ---------------------------------------------------------------- home

def first_lesson(track):
    """Where a track starts: its first core lesson (or its first lesson, if it has only extensions)."""
    return (track.core_lessons or track.lessons or [None])[0]


def start_link(track, lg=False):
    """The primary way in: a plain link to the track's first lesson, or "" when it has none."""
    first = first_lesson(track)
    if first is None:
        return ""
    return (f'<a class="btn primary{" lg" if lg else ""}" href="/t/{esc(track.id)}/{esc(first.id)}">'
            f'<span>Start with {esc(first.id)} {esc(first.title)}</span>{ARROW}</a>')


def lesson_counts(track):
    """['33 lessons', '2 extensions']: the core's lessons, with extensions counted apart."""
    n_opt = len(track.optional_modules)
    return [plural(len(track.core_lessons), "lesson")] + ([plural(n_opt, "extension")] if n_opt else [])


def lesson_count(track):
    return " &middot; ".join(lesson_counts(track))


def track_card(href, picture, label, title, summary, chips, soon="", credits=()):
    """A home page card: the track's picture on top, then kind, title, summary, and the
    counts as chips pinned to the bottom so cards in a row line up; then credits, what the
    track is built on ("based on xv6-riscv"), as quieter outlined chips."""
    chips = "".join(f'<span class="pill">{c}</span>' for c in chips)
    chips += "".join(f'<span class="pill up-chip">{esc(c)}</span>' for c in credits)
    pill = f'<span class="pill soon">{esc(soon)}</span>' if soon else ""
    return f"""<a class="grid-card track-card{" is-soon" if soon else ""}" href="{href}">
<span class="card-art art">{picture}</span>
<span class="card-body"><span class="card-top"><span class="mono-label">{label}</span>{pill}</span>
<h3>{esc(title)}</h3><p>{summary}</p>
<span class="card-meta">{chips}</span></span></a>"""


def home_page():
    cards = []
    first = None
    for t in tracks():
        title, kind, summary = safe_track(t)
        first = first or t
        cards.append(track_card(f"/t/{esc(t.id)}", art.track_art(t, "art"), f"{esc(kind or 'track')} &middot; {esc(t.id)}",
                                title, esc(summary), lesson_counts(t),
                                credits=[str(u.get("chip") or f"based on {u['name']}") for u in upstreams(t)]))
    soon = outlines()
    for o in soon:
        label = " &middot; ".join(esc(x) for x in dict.fromkeys([o.kind or "track", o.id]))
        chips = [plural(len(o.modules), "module"), plural(len(o.lessons), "lesson") + " planned"]
        cards.append(track_card(f"/t/{esc(o.id)}", art.outline_track_art(o, "art"), label, o.title, esc(o.outcome),
                                chips, soon=o.status_label))
    if not cards:
        cards.append('<p class="empty">No tracks yet. Try <code>./learn new-track</code>.</p>')
    cta = start_link(first, lg=True) if first else ""
    n_open = len(tracks())
    soon_note = f'<span class="hero-soon">{len(soon)} coming soon</span>' if soon else ""
    body = f"""<section class="hero">
<div class="float float-l" aria-hidden="true"><span class="mono-label">kernel/main.c</span>
<pre>void main(void) {{
  uartinit();
  printf("hello\\n");
  for (;;) ;
}}</pre></div>
<div class="float float-r" aria-hidden="true"><span class="mono-label">serial console</span>
<pre>xv6 kernel is booting

hart 2 starting
init: starting sh
$ _</pre></div>
<span class="hero-pill"><span class="chip-dark">OPEN</span><b>{plural(n_open, "track")}</b>{soon_note}</span>
<h1 class="hero-title">Code first,<br><span class="px">theory second.</span></h1>
<p class="hero-sub">Real systems, a kernel and a database among them, taken apart one lesson at a time.
Read the code that does the work, run it, break it on purpose. Then read why it works.</p>
<div class="hero-cta">{cta}<a class="link-under" href="#tracks">{PLAY}<span>See the tracks</span></a></div>
</section>
<section class="tracks-sec" id="tracks">
<h2 class="divider-label"><span>Tracks</span></h2>
<div class="track-grid">{"".join(cards)}</div>
</section>"""
    return page(SITE, body, home=True)


# ---------------------------------------------------------------- track map

def track_page(track):
    title, kind, summary = safe_track(track)
    core_mods, opt_mods = split_modules(track)
    structure = "".join(
        f'<a class="struct-row" href="#m-{esc(mid)}"><span class="sn">{esc(mid)}</span><span class="st-t">{esc(mt)}'
        f'<span class="mono-sm">{len(ls)} lessons{" &middot; optional" if opt else ""}</span></span>{ARROW}</a>'
        for opt, mods in ((False, core_mods), (True, opt_mods)) for mid, mt, ls in mods)

    def section(mid, mt, ls):
        cards = []
        for l in ls:
            labels = "".join(f'<span class="pill">{esc(x)}</span>' for x in l.labels)
            cards.append(f"""<a class="grid-card unit" href="/t/{esc(track.id)}/{esc(l.id)}">
<span class="unit-top"><span class="unit-code">{esc(l.id)}</span>{ARROW}</span>
<span class="unit-title">{esc(l.title)}</span>
<span class="unit-labels">{labels}</span></a>""")
        cover = art.module_art(track, mid, "cover")
        cover = f'<div class="art cover">{cover}</div>' if cover else ""
        return f"""<section class="module" id="m-{esc(mid)}">
<div class="module-strip"><span class="mono-sm">Module {esc(mid)} &middot; {len(ls)} lesson{"" if len(ls) == 1 else "s"}</span><i></i></div>
<h2>{esc(mt)}</h2>{cover}<div class="unit-grid">{"".join(cards)}</div></section>"""

    sections = [section(mid, mt, ls) for mid, mt, ls in core_mods]
    if opt_mods:
        sections.append('<h2 class="divider-label" id="extensions"><span>Extensions</span></h2>'
                        '<p class="ext-lede">Optional modules that build on the finished core, each independent of the others: '
                        'take any of them, in any order.</p>')
    sections += [section(mid, mt, ls) for mid, mt, ls in opt_mods]
    if not track.lessons:
        sections.append('<p class="empty">No lessons yet.</p>')
    go = start_link(track)
    strip = (f'<section class="strip-card"><span class="strip-text">{plural(len(core_mods), "module")} &middot; {lesson_count(track)}</span>'
             f'{go}</section>') if go else ""
    arch = art.track_map(track)
    arch = f'<figure class="art ov-map">{arch}</figure>' if arch else ""
    body = f"""<div class="wrap">
<section class="ov-hero"><h1 class="ov-title">{esc(title)}</h1><p class="ov-sub">{esc(summary)}</p>{upstream_lines(track)}{arch}</section>
{strip}
<section class="panel-card"><h2 class="mono-label">Curriculum structure</h2><div class="struct-grid">{structure}</div></section>
<h2 class="divider-label"><span>Full curriculum</span></h2>
{"".join(sections)}
</div>"""
    return page(f"{title} - {SITE}", body, track=track)


def upstream_lines(track):
    """The overview's "Built on" line: each upstream, linking out to its repository, its licence,
    and the one sentence on what the track owes it, with the way to /credits."""
    out = []
    for u in upstreams(track):
        name = ext_link(u["url"], f'<span>{esc(u["name"])}</span>{EXT}', "up-name")
        lic = f'<span class="up-lic">{esc(licence_label(u))}</span>' if licence_label(u) else ""
        owes = esc(str(u.get("owes") or ""))
        out.append(f'<div class="upstream"><p class="up-head"><span class="up-k">Built on</span>{name}{lic}</p>'
                   f'<p class="up-owes">{owes} <a class="up-more" href="/credits#{esc(track.id)}">Credits and licence</a></p></div>')
    return "".join(out)


def credits_page():
    """/credits: what each track is built on, with the whole licence where its code is derived
    from another project's, then what the site itself ships (its fonts)."""
    secs = []
    for t in tracks():
        ups = upstreams(t)
        if not ups:
            continue
        for k, u in enumerate(ups):
            sid = t.id if k == 0 else f"{t.id}-{k + 1}"
            facts = [("Licence", esc(licence_label(u)))]
            if u.get("copyright"):
                facts.append(("Copyright", esc(str(u["copyright"]))))
            if u.get("owes"):
                facts.append(("What this track owes it", esc(str(u["owes"]))))
            also = [(str(a[0]), str(a[1])) for a in u.get("also") or () if isinstance(a, (list, tuple)) and len(a) == 2
                    and WEB_URL.match(str(a[1]))]
            if also:
                facts.append(("See also", '<ul class="res-list">' + "".join(
                    f'<li>{ext_link(url, esc(label), "res-link")}</li>' for label, url in also) + "</ul>"))
            dl = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts)
            # the licence word for word, its paragraphs reflowed so it reads at any width
            paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", licence_text(t, u)) if p.strip()]
            text = (f'<p class="credit-note">The licence, whole, as it comes with the code '
                    f'(<code>tracks/{esc(t.id)}/{esc(u["licence_file"])}</code>):</p>'
                    f'<div class="licence-text">{"".join(f"<p>{esc(p)}</p>" for p in paras)}</div>') if paras else ""
            secs.append(f"""<section class="module credit" id="{esc(sid)}">
<div class="module-strip"><span class="mono-sm"><a href="/t/{esc(t.id)}">{esc(safe_track(t)[0])}</a></span><i></i></div>
<h2>{ext_link(u["url"], f'<span>{esc(u["name"])}</span>{EXT}', "up-name")}</h2>
<dl class="mod-facts credit-facts">{dl}</dl>{text}</section>""")
    if not secs:
        secs.append('<p class="empty">No track names an upstream yet.</p>')
    fonts = ('<section class="module credit" id="site"><div class="module-strip"><span class="mono-sm">This site</span><i></i></div>'
             '<h2>Fonts</h2><dl class="mod-facts credit-facts"><div><dt>Figtree</dt><dd>Copyright 2022 The Figtree Project Authors</dd></div>'
             '<div><dt>Geist Mono</dt><dd>Copyright 2024 The Geist Project Authors</dd></div>'
             '<div><dt>Licence</dt><dd><a class="res-link" href="/static/fonts/LICENSE-OFL.txt">SIL Open Font License 1.1</a></dd></div></dl></section>')
    body = f"""<div class="wrap credits">
<section class="ov-hero"><h1 class="ov-title">Credits</h1><p class="ov-sub">The real code and formats each track is built on,
with their licences. Where a track's code is derived from another project's, its licence is printed here whole.</p></section>
{"".join(secs)}
{fonts}
</div>"""
    return page(f"Credits - {SITE}", body, home=True)


# ---------------------------------------------------------------- outline overview

KIND_TITLE = {"book": "Books", "video": "Videos", "article": "Articles", "paper": "Papers", "course": "Courses",
              "code": "Code"}


def outline_text(text):
    """Inline markdown from an outline (code, emphasis, web links); other links go nowhere."""
    return inline(text or "", lambda h: None if re.match(r"^(https?:|mailto:)", h, re.I) else "#")


def ext_link(url, label, cls):
    return (f'<a class="{cls}" href="{esc(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
            f'{label}</a>')


def url_host(m):
    host = urllib.parse.urlsplit(m.group(0)).hostname or m.group(0)
    return host[4:] if host.startswith("www.") else host


def lib_anchor(key):
    return "lib-" + re.sub(r"[^a-z0-9_-]+", "-", key.lower())


def outline_page(o):
    """The overview of a track that is only an outline: the same shape as a track overview,
    but nothing in it opens a lesson, because no lesson exists yet."""
    structure = "".join(
        f'<a class="struct-row" href="#m-{esc(m.id)}"><span class="sn">{esc(m.id)}</span><span class="st-t">{esc(m.title)}'
        f'<span class="mono-sm">{len(m.lessons)} lesson{"" if len(m.lessons) == 1 else "s"} planned</span></span>{ARROW}</a>'
        for m in o.modules)
    sections = []
    for m in o.modules:
        n = len(m.lessons)
        cards = "".join(
            f'<li class="grid-card unit is-planned"><span class="unit-top"><span class="unit-code">{esc(lid)}</span></span>'
            f'<span class="unit-title">{esc(title)}</span></li>' for lid, title in m.lessons)
        cards = f'<ul class="unit-grid plan-grid" aria-label="Planned lessons">{cards}</ul>' if cards else ""
        cover = art.outline_art(o, m.id, "cover")
        cover = f'<div class="art cover">{cover}</div>' if cover else ""
        facts = "".join(f'<div><dt>{name}</dt><dd>{outline_text(value)}</dd></div>'
                        for name, value in (("Goal", m.goal), ("What it builds", m.build), ("Value", m.value)) if value)
        reads = []
        for key in m.learn_from:
            r = o.resource(key)
            if r is None:
                reads.append(f'<li><span class="mono-sm">{esc(key)}</span></li>')
            elif r.url:
                reads.append(f'<li>{ext_link(r.url, esc(r.title), "res-link")}</li>')
            else:
                reads.append(f'<li><span title="{esc(r.by, quote=True)}">{esc(r.title)}</span></li>')
        if reads:
            facts += f'<div class="mf-wide"><dt>Learn from</dt><dd><ul class="res-list">{"".join(reads)}</ul></dd></div>'
        facts = f'<dl class="mod-facts">{facts}</dl>' if facts else ""
        sections.append(f"""<section class="module" id="m-{esc(m.id)}">
<div class="module-strip"><span class="mono-sm">Module {esc(m.id)} &middot; {n} lesson{"" if n == 1 else "s"} planned</span><i></i></div>
<h2>{esc(m.title)}</h2>{cover}{facts}{cards}</section>""")
    if not o.modules:
        sections.append('<p class="empty">No modules planned yet.</p>')

    groups = []
    for kind, items in o.library_by_kind():
        lis = []
        for r in items:
            title = ext_link(r.url, f"<span>{esc(r.title)}</span>{EXT}", "lib-title") if r.url else \
                f'<span class="lib-title">{esc(r.title)}</span>'
            where = ol.URL.sub(url_host, r.where or "")
            meta = " &middot; ".join(esc(x) for x in (r.by, where) if x)
            lis.append(f'<li id="{lib_anchor(r.key)}">{title}' + (f'<span class="lib-meta">{meta}</span>' if meta else "") + "</li>")
        groups.append(f'<section class="lib-group"><h3>{esc(KIND_TITLE.get(kind, kind.capitalize()))}</h3>'
                      f'<ul class="lib-list">{"".join(lis)}</ul></section>')
    library = ""
    if groups:
        library = (f'<h2 class="divider-label" id="library"><span>Library</span></h2>'
                   f'<p class="lib-lede">Everything the modules learn from, grouped by kind.</p>'
                   f'<div class="lib-grid">{"".join(groups)}</div>')

    about = ""
    facts = "".join(f'<div><dt>{name}</dt><dd>{outline_text(value)}</dd></div>'
                    for name, value in (("Who it is for", o.audience), ("What you need first", o.prerequisites),
                                        ("Planned to follow", o.upstream)) if value)
    intro = "".join(f"<p>{outline_text(p)}</p>" for p in o.intro.split("\n\n") if p.strip())
    if intro or facts:
        about = (f'<section class="panel-card"><h2 class="mono-label">About this track</h2><div class="about">'
                 + (f'<div class="about-intro">{intro}</div>' if intro else "")
                 + (f'<dl class="facts">{facts}</dl>' if facts else "") + "</div></section>")
    strip = (f'<section class="strip-card soon-strip"><span class="strip-text"><span class="pill soon">{esc(o.status_label)}</span>'
             f'<span>This track is an outline for now: the direction is set, but no lesson is written yet, '
             f'so there is nothing to open or build here today.</span></span></section>')
    sub = f'<p class="ov-sub">{outline_text(o.outcome)}</p>' if o.outcome else ""
    body = f"""<div class="wrap">
<section class="ov-hero"><h1 class="ov-title">{esc(o.title)}</h1>{sub}</section>
{strip}
{about}
<section class="panel-card"><h2 class="mono-label">Curriculum structure</h2><div class="struct-grid">{structure}</div></section>
<h2 class="divider-label"><span>Full curriculum</span></h2>
{"".join(sections)}
{library}
</div>"""
    return page(f"{o.title} - {SITE}", body, outline=o)


# ---------------------------------------------------------------- lesson

# ---------------------------------------------------------------- the project's files

MAX_VIEW = 512 * 1024
hidden_files = tl.hidden_files
tree_files = tl.tree_files
# A static export (harness/web/export.py) has no /api/file: per lesson it writes this index, {path: URL of the view}
STATIC_INDEX = "/api/file/{track}/{lesson}.json"


def files_drawer(track, lesson, proj, static=False):
    """The project as it stands at this lesson, in a side drawer opened from the lesson header:
    the files this lesson brings or adds to first, then every file there is by now. static: the
    drawer reads STATIC_INDEX (data-index) instead of asking the server for each file."""
    at = lesson.id
    paths = proj.files_at(at)
    status = {p: proj.status(p, at) for p in paths}
    mine = [p for p in paths if status[p] == "new"] + [p for p in paths if status[p] == "changed"]
    mine.sort(key=is_notice)             # a licence file last: the drawer opens on code
    tree = {}
    for p in paths:
        node = tree
        parts = p.split("/")
        for d in parts[:-1]:
            node = node.setdefault(d + "/", {})
        node[parts[-1]] = p

    def has_mine(node):
        return any(has_mine(v) if isinstance(v, dict) else status.get(v) for v in node.values())

    def count(node):
        return sum(count(v) if isinstance(v, dict) else 1 for v in node.values())

    def button(path, label):
        st = status.get(path)
        if st:
            mark, tip = f'<span class="mk this">{st}</span>', ("comes with this lesson" if st == "new" else "this lesson adds to it")
        else:
            intro = proj.intro(path)
            mark = f'<span class="mk ids">{esc(intro)}</span>' if intro else ""
            tip = f"came with {intro}" if intro else ""
        return (f'<li><button type="button" class="ft-file{" this" if st else ""}" data-path="{esc(path, quote=True)}" title="{esc(tip)}">'
                f'<span class="ft-name">{esc(label)}</span>{mark}</button></li>')

    def render_node(node):
        items = []
        for d in sorted(k for k, v in node.items() if isinstance(v, dict)):
            sub = node[d]
            items.append(f'<li><details class="ft-dir"{" open" if has_mine(sub) else ""}><summary>{CHEV_R}<span class="ft-name">{esc(d)}</span>'
                         f'<span class="ft-count">{count(sub)}</span></summary>{render_node(sub)}</details></li>')
        for f in sorted(k for k, v in node.items() if not isinstance(v, dict)):
            items.append(button(node[f], f))
        return '<ul class="ft-list">' + "".join(items) + "</ul>"

    legend = ('<span class="lg"><span class="mk this">new</span>comes with this lesson</span>'
              '<span class="lg"><span class="mk this">changed</span>this lesson adds to it</span>'
              '<span class="lg"><span class="mk ids">01.01</span>the lesson it came with</span>')
    n = len(paths)
    if not paths:
        inner = '<p class="quiet">There are no files yet at this lesson.</p>'
    else:
        group = ""
        if mine:
            group = ('<div class="ft-group"><p class="ft-head">This lesson</p><ul class="ft-list">'
                     + "".join(button(p, p) for p in mine) + '</ul><p class="ft-head">All files</p></div>')
        inner = f"""<div class="legend">{legend}</div>
<div class="files-body"><nav class="ft" aria-label="Project files">{group}{render_node(tree)}</nav>
<div class="fv"><div class="fv-bar"><span class="fv-path" data-role="fpath">Pick a file</span><span class="fv-side"><span class="fv-note" data-role="fnote"></span>{fold_bar("fv-body", hidden=True)}</span></div>
<div class="fv-body" id="fv-body" data-role="fbody" tabindex="0"><p class="quiet fv-empty">Pick a file on the left to read it.</p></div></div></div>"""
    index = f' data-index="{esc(STATIC_INDEX.format(track=track.id, lesson=at), quote=True)}"' if static else ""
    return f"""<div class="drawer" id="files-drawer" hidden data-files="/api/file/{esc(track.id)}"{index} data-lesson="{esc(at)}" data-open="{esc(mine[0] if mine else "", quote=True)}">
<div class="drawer-scrim" data-drawer-close></div>
<div class="drawer-panel" role="dialog" aria-modal="true" aria-labelledby="drawer-title" tabindex="-1">
<div class="drawer-head"><h2 class="sec-title" id="drawer-title">Files <span class="sec-count">{n} file{"" if n == 1 else "s"}</span></h2>
<button class="btn icon" type="button" data-drawer-close aria-label="Close files">{CLOSE}</button></div>
{inner}</div></div>"""


def render_file_view(track, lesson_id, rel, proj=None):
    """Server-rendered viewer body: the file as it stands at the lesson (lesson_id None: at the end
    of the track). Line numbers are the file's own; the lesson's own code gets a band. Returns a
    dict for the JSON response, or None when the file does not exist yet at that lesson."""
    proj = proj or tl.Project(track)
    if not proj.present(rel, lesson_id):
        return None
    head = proj.text(rel)[:8192]
    if b"\0" in head:
        return {"path": rel, "binary": True, "truncated": False, "first_band": None, "note": "",
                "html": '<p class="quiet fv-empty">This is a binary file, so there is nothing to show.</p>'}
    truncated = len(proj.text(rel)) > MAX_VIEW
    lines, shown, band = proj.lines_at(rel, lesson_id, limit=MAX_VIEW)
    fold = tl.is_c(rel)
    body = code_rows([lines[i] for i in shown], [i + 1 for i in shown], highlight.language_for(rel),
                     band={k for k, i in enumerate(shown) if i in band}, fold=fold, prefix="fv-fold")
    banded = [k for k, i in enumerate(shown) if i in band]
    return {"path": rel, "binary": False, "truncated": truncated, "first_band": banded[0] if banded else None,
            "note": "shown whole, not split by lesson" if proj.whole(rel) else "",
            "foldable": fold and bool(tl.function_bodies([lines[i] for i in shown])),
            "html": f'<div class="fv-in">{body}</div>'}


# ---------------------------------------------------------------- the code a lesson teaches

FOLD_IDS = itertools.count(1)


def code_rows(lines, numbers, lang="plain", band=(), fold=False, prefix="fold", hl=None, shut=(), clip=None):
    """Highlighted code as rows, one per line, numbered with the file's own line numbers (band:
    positions of the lesson's own lines). With fold (C code) each function body is a fold of its
    own: the chevron on the function's first line shuts and opens it, and while it is shut a
    "..." stands in for it. "Functions only" (fold_bar) shuts them all.

    hl: the lines already highlighted, one each (a piece cut from a file highlighted whole). A
    line numbered None is a gap, code left out between two pieces: its text is only the indent
    the "..." standing for it gets. shut: positions of function bodies that start shut (and come
    back shut when "Functions only" is turned off). clip: rows from this position on are marked
    "clip-x", for a pane that starts with its first lines only (see code_block)."""
    hl = hl if hl is not None else highlight.highlight_lines("\n".join(lines), lang)
    fns = [f for f in tl.functions(lines) if f[1] <= f[2]] if fold else []
    ids = [f"{prefix}-{next(FOLD_IDS)}" for _ in fns]
    heads = {h: n for n, (h, _, _) in enumerate(fns)}
    starts = {a: n for n, (_, a, _) in enumerate(fns)}
    ends = {b for _, _, b in fns}
    out = []
    for k, text in enumerate(hl):
        cx = " clip-x" if clip is not None and k >= clip else ""
        if k in starts:
            n = starts[k]
            name = esc(tl.function_name(lines[fns[n][0]:k]) or "this function", quote=True)
            indent = lines[k][:len(lines[k]) - len(lines[k].lstrip())] or "  "
            closed = ' shut" data-shut="1' if k in shut else ""
            out.append(f'<div class="fbody{closed}" id="{ids[n]}"><div class="row fph{cx}"><span class="ln"></span><span class="tx">{indent}'
                       f'<button class="fold-more" type="button" aria-controls="{ids[n]}" aria-label="Show the body of {name}">'
                       f'...</button></span></div>')
        if numbers[k] is None:
            out.append(f'<div class="row gap{cx}"><span class="ln"></span><span class="tx">{esc(lines[k])}...</span></div>')
        else:
            ln = str(numbers[k])
            if k in heads:
                n = heads[k]
                name = esc(tl.function_name(lines[k:fns[n][1]]) or "this function", quote=True)
                ln = (f'<button class="fold-btn" type="button" aria-expanded="{"false" if fns[n][1] in shut else "true"}" '
                      f'aria-controls="{ids[n]}" aria-label="Fold {name}">{CHEV_R}</button>{ln}')
            out.append(f'<div class="row{" band" if k in band else ""}{cx}"><span class="ln">{ln}</span><span class="tx">{text}</span></div>')
        if k in ends:
            out.append("</div>")
    return "".join(out)


def code_pane(lines, numbers, lang="plain", fold=False, band=(), hl=None, shut=(), clip=None, pane_id=""):
    """A highlighted code pane; numbers are the real line numbers of the lines, one each (None
    for a gap: see code_rows). clip: show the first clip lines only, until the pane loses its
    "clipped" class (pane_id names it for the control that does that)."""
    attrs = f' id="{esc(pane_id, quote=True)}"' if pane_id else ""
    return (f'<div class="file on rows{" clipped" if clip is not None else ""}"{attrs}><div class="fv-in">'
            f'{code_rows(lines, numbers, lang, band=band, fold=fold, hl=hl, shut=shut, clip=clip)}</div></div>')


FOLD_ICON = ('<svg class="ic" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3 3.5h10M3 8h4M3 12.5h10M10 6.5l1.5 1.5L13 6.5" '
             'fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def fold_bar(target, label="Functions only", hidden=False):
    """The "Functions only" switch for the code in the element with id target: shuts every
    function's fold, so what is left is the list of functions, each under its comment; each one
    still opens on its own."""
    return (f'<button class="btn fold-toggle" type="button" data-fold-toggle aria-controls="{esc(target, quote=True)}" '
            f'aria-pressed="false"{" hidden" if hidden else ""} title="Fold every function body: see at a glance what this builds">'
            f'{FOLD_ICON}<span>{esc(label)}</span></button>')


definition_span = tl.definition_span


def code_blocks(track, lesson_id, proj=None):
    """What a lesson adds, as blocks to show: [{"titles", "names", "defs", "path", "shown", "new"}].

    A file that appears in this lesson is shown whole, as it stands at the lesson. In a file
    that was there already, each region of the lesson shows the whole top-level C definition
    around it (regions in the same definition share one block, with both titles); assembly and
    top-level regions show their own code. Marker lines, instruction comments, and code of
    later lessons are never shown. "names" are what a lesson's lead-in may be headed with;
    "defs" the names the code shown defines (see definitions), which a lead-in may name too.
    A new file also has "owner": {region title, lowercase: the function the region is in}."""
    proj = proj or tl.Project(track)
    at = lesson_id
    mine = [r for r in lesson_regions(track, at)]
    new = [f for f in proj.files_at(at) if proj.status(f, at) == "new" and not is_notice(f)]   # a licence: Files drawer only
    files = sorted({r.path for r in mine}) + [f for f in new if f not in {r.path for r in mine}]
    out = []
    for rel in files:
        try:
            lines, shown, _band = proj.lines_at(rel, at)
        except OSError:
            continue
        regs = [r for r in mine if r.path == rel]
        if rel in new:
            names, owner = [r.title for r in regs] + [os.path.basename(rel), rel], {}
            for r in regs:
                span = tl.definition_span(lines, r) if tl.is_c(rel) else None
                if span:
                    names.append(tl.function_name(lines[span[0]:span[1] + 1]))
                    owner[r.title.lower()] = names[-1]
            out.append({"titles": [os.path.basename(rel)], "names": names, "path": rel, "new": True,
                        "shown": [(i + 1, lines[i]) for i in shown], "owner": owner,
                        "defs": definitions([lines[i] for i in shown], rel)})
            continue
        groups, order = {}, []
        for r in regs:
            span = tl.definition_span(lines, r) if tl.is_c(rel) else None
            first, last = span or (r.instr_end, r.end - 1)
            if (first, last) not in groups:
                groups[(first, last)] = []
                order.append((first, last))
            groups[(first, last)].append(r)
        for first, last in order:
            regs_here = groups[(first, last)]
            fn = tl.function_name(lines[first:last + 1]) if tl.is_c(rel) else ""
            out.append({"titles": [r.title for r in regs_here], "names": [r.title for r in regs_here] + ([fn] if fn else []),
                        "defs": [fn] if fn else [],
                        "path": rel, "new": False, "shown": [(i + 1, lines[i]) for i in shown if first <= i <= last]})
    return [b for b in out if b["shown"]]


ASM_LABEL = re.compile(r"^([A-Za-z_]\w*):")
PY_DEF = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)")


def definitions(lines, path):
    """The names lines of a file define, in order: in C its functions and the structs, unions and
    enums it opens ("struct run {"); in assembly its labels at the start of a line; in Python its
    functions and classes. What a lead-in may name besides a region (see take_lead_ins)."""
    if tl.is_c(path):
        out = [tl.function_name(lines[head:body]) for head, body, _ in tl.functions(lines)]
        for line in lines:
            m = STRUCT_NAME.match(line)
            if m and "(" not in line and tl.code_part(line).endswith("{"):
                out.append(m.group(2))
    elif path.endswith((".S", ".s")):
        out = [m.group(1) for m in map(ASM_LABEL.match, lines) if m]
    elif path.endswith(".py"):
        out = [m.group(1) for m in map(PY_DEF.match, lines) if m]
    else:
        out = []
    return list(dict.fromkeys(x for x in out if x))


CONTEXT = 2         # an older definition a lesson adds to: its signature, and this many lines each side of each addition
FILL = 2            # code left out between two shown pieces that is this short is shown instead
LONG_ALSO = 120     # "Also added in this lesson" longer than this starts with what it brings folded
NEW_LONG = 150      # a new file longer than this that no lead-in talks about starts folded to its functions,
CLIP = 20           # or, with no function bodies to fold (data, declarations), as its first lines
STRUCT_NAME = re.compile(r"^(?:typedef\s+)?(struct|union|enum)\s+([A-Za-z_]\w*)")


def declaration(lines):
    """Whether lines (a piece of a C header, from its first line of code) are only a prototype or
    a declaration ("void kfree(void *);", "extern struct cpu cpus[NCPU];", "struct buf;"): one
    statement, no braces, not a typedef or a preprocessor line."""
    code = " ".join(tl.code_part(x) for x in lines).strip()
    return (code.endswith(";") and "{" not in code and "}" not in code
            and not code.startswith(("#", "typedef")))


def also_blocks(track, lesson_id, proj=None, main=None, apart=()):
    """The rest of what a lesson adds: the code that comes with it (@from) in files that were
    there before it, wherever no block of code_blocks (main) shows it already. One block per file,
    in file order, made of whole top-level pieces (timeline.units) with the file's own line
    numbers: a piece the lesson brings is shown whole; an older piece it adds lines to, however
    short, is shown as its signature (its first line), CONTEXT lines each side of each addition
    and its closing brace, the additions banded. A gap (line None) stands for what is left out
    between. Code of later lessons and @internal code are left out, as everywhere.

    In a C header, the prototypes and declarations a lesson adds (see declaration) are not
    listed: they are counted, in a block of their own at the end of the list with "decls" (how
    many), "lines" (how many lines of code they are) and nothing in "shown". The comment the
    lesson adds above them (a section heading, attached or on its own) goes with them. A struct,
    enum or #define it adds to a header is shown as code, as anywhere.

    apart: names (lowercase) of functions or structs the lesson's notes talk about. Those pieces
    get a block of their own, ahead of the rest of their file (titled "more in <file>"), so the
    notes sit right above their code instead of above a long list.

    Each block is as code_blocks makes them, plus "also": True, "band" (positions of the added
    lines in older pieces), "hl" (the lines highlighted as part of the whole file) and "fresh"
    ({position: function name or ""} for the pieces the lesson brings whole: what starts folded
    when the group is long), and "more": True on the rest of a file whose named pieces come just
    before it. "names" (and "defs", the same) are the functions and structs shown, for lead-ins."""
    proj = proj or tl.Project(track)
    at = lesson_id
    main = code_blocks(track, at, proj) if main is None else main
    covered = {}
    for b in main:
        covered.setdefault(b["path"], set()).update(n for n, _ in b["shown"])
    out, counted = [], []
    for rel in proj.files_at(at):
        if at not in proj.marked(rel) or proj.status(rel, at) == "new":
            continue
        try:
            lines, shown, band = proj.lines_at(rel, at)
        except OSError:
            continue
        text, nums = [lines[i] for i in shown], [i + 1 for i in shown]
        cov = covered.get(rel, set())
        added = {k for k, i in enumerate(shown) if i in band and i + 1 not in cov}
        if not added:
            continue
        c = tl.is_c(rel)
        header = c and rel.endswith(".h")
        pieces = []                                # (take, mark, fresh, names) of each piece shown
        decls, decl_lines, heading = 0, 0, None    # a header's new declarations, counted, not shown
        for first, head, last in tl.units(text, c):
            here = sorted(k for k in added if first <= k <= last)
            if heading is not None and not (here and header and declaration(text[head:last + 1])):
                pieces.append(heading)             # a comment on its own, above code that is not counted
                heading = None
            if not here or (c and any(nums[k] in cov for k in range(first, last + 1))):
                continue                           # nothing added here, or a block above shows it
            if header and declaration(text[head:last + 1]):
                decls += 1
                decl_lines += sum(1 for k in here if k >= head)   # its comment, if any, not counted
                heading = None                     # the comment just above them goes with them
                continue
            whole = range(first, last + 1)
            piece = text[first:last + 1]
            name = tl.function_name(piece) if c and tl.functions(piece) else ""
            take, mark, fresh = set(), set(), {}
            if head in added:                      # a piece this lesson brings
                take.update(whole)
                fresh.update(dict.fromkeys(whole, name))
            else:                                  # an older piece: around what is added, however short
                body = head
                while c and body < last and not tl.code_part(text[body]).endswith("{"):
                    body += 1
                take.update(range(head, body + 1))
                if c and body < last:
                    take.add(last)
                for k in here:                     # not up into the comment above it, unless that is what changed
                    take.update(range(max(first if k < head else head, k - CONTEXT), min(last + 1, k + CONTEXT + 1)))
                mark.update(here)
            names = [name]
            m = STRUCT_NAME.match(text[head]) if c else None
            if m:
                names += [m.group(2), f"{m.group(1)} {m.group(2)}"]
            got = (take, mark, fresh, [x for x in names if x])
            if header and head == first and head in added and text[head].startswith(("//", "/*")):
                heading = got                      # a comment alone: shown unless declarations follow it
                continue
            pieces.append(got)
        if heading is not None:
            pieces.append(heading)
        named = [p for p in pieces if apart and {x.lower() for x in p[3]} & set(apart)]
        rest = [p for p in pieces if p not in named]
        hl_all = highlight.highlight_lines("\n".join(text), highlight.language_for(rel))
        base = os.path.basename(rel)
        for group, title in ((named, base), (rest, f"more in {base}" if named else base)):
            if not group:
                continue
            take = set().union(*(p[0] for p in group))
            mark = set().union(*(p[1] for p in group))
            fresh = {k: v for p in group for k, v in p[2].items()}
            picked = sorted(take)
            for a, b in zip(picked, picked[1:]):   # a short run left out between two pieces: shown
                if 1 < b - a <= FILL + 1:
                    take.update(range(a + 1, b))
            picked = sorted(take)
            rows, hl, bmark, bfresh = [], [], set(), {}
            for n, k in enumerate(picked):
                if n and k > picked[n - 1] + 1:    # a gap, indented as the code it sits in
                    near = text[picked[n - 1]] if text[k].startswith("}") else text[k]
                    rows.append((None, near[:len(near) - len(near.lstrip())]))
                    hl.append("")
                if k in mark:
                    bmark.add(len(rows))
                if k in fresh:
                    bfresh[len(rows)] = fresh[k]
                rows.append((nums[k], text[k]))
                hl.append(hl_all[k])
            names = list(dict.fromkeys(x for p in group for x in p[3]))
            out.append({"titles": [title], "names": names, "defs": names, "path": rel,
                        "new": False, "also": True, "more": group is rest and bool(named), "shown": rows, "band": bmark,
                        "hl": hl, "fresh": bfresh})
        if decls:
            counted.append({"titles": [base], "names": [], "defs": [], "path": rel, "new": False, "also": True, "shown": [],
                            "decls": decls, "lines": decl_lines})
    return out + counted


def code_block(track, block, lead="", editor_link=True, shut=(), clip=None):
    """One block of "The code": its title, the lead-in that says why (from the lesson's notes),
    where it starts with Copy and Open in editor (not in a static export: editor_link False),
    then the code as the track has it, numbered by its real lines. A block of also_blocks is a
    quieter one (a smaller heading, the file's name), its additions to older code banded; shut:
    positions of its function bodies that start folded. clip: the code starts as its first clip
    lines, with a "Show all N lines" control under them (the Files drawer has it whole too)."""
    path, shown = block["path"], block["shown"]
    absolute = os.path.join(track.root, path)
    rel = os.path.relpath(absolute, core.ROOT)
    line = next(n for n, _ in shown if n is not None)
    target = f"{absolute if rel.startswith('..') else rel}:{line}"
    editor = "vscode://file/" + urllib.parse.quote(absolute, safe="/") + f":{line}"
    where = (f'<p class="where"><code class="where-path">{esc(target)}</code>'
             f'<button class="btn copy" type="button" data-copy="{esc(target, quote=True)}">{COPY}<span>Copy</span></button>'
             + (f'<a class="btn" href="{esc(editor, quote=True)}" data-editor>Open in editor</a>' if editor_link else "") + '</p>')
    clip = clip if clip is not None and clip < len(shown) else None
    pane_id = f"clip-{next(FOLD_IDS)}" if clip is not None else ""
    pane = code_pane([t for _, t in shown], [n for n, _ in shown], highlight.language_for(path), fold=tl.is_c(path),
                     band=block.get("band", ()), hl=block.get("hl"), shut=shut, clip=clip, pane_id=pane_id)
    if clip is not None:
        n = sum(1 for k, _ in shown if k is not None)
        more, less = f"Show all {n:,} lines", f"Show the first {clip} lines"
        pane += (f'<div class="clip-bar"><button class="clip-more" type="button" aria-expanded="false" aria-controls="{pane_id}" '
                 f'data-more="{more}" data-less="{less}">{CHEV_R}<span>{more}</span></button></div>')
    tag = '<span class="tag">new file</span>' if block["new"] else ""
    title = " &middot; ".join(esc(t) for t in block["titles"])
    heading = (f'<h4 class="region-title also-file">{title}</h4>' if block.get("also")
               else f'<h3 class="region-title">{title}{tag}</h3>')
    return f"""<div class="region{" also-region" if block.get("also") else ""}">
{heading}
{lead}
{where}
<div class="code-block-shell">{pane}</div>
</div>"""


H3 = re.compile(r"^###\s+(.+?)\s*#*\s*$")


WORD = re.compile(r"(?<![\w.])[A-Za-z_]\w*(?!\w|\.\w)")      # a word, not part of a number or a file name
# English words that are also names of functions in the tracks ("free", "main", "split"), and
# common ones that could be: a heading written in plain words never names those by accident.
# Headings name them in backticks ("### Writing `split`, step by step").
COMMON = frozenset("""
    about accept acquire add advance after again alarm alloc also append back before begin being
    binary bind block both boundary break bring buffer build built button cache call came cell
    change changed check child clear click client clock close code come commit compare connect
    console consumer context copy count crash create cursor data decide delete describe device
    disk does done down drag draw each else empty entry eval even every exec exit expect explain
    fail false fatal file files fill filter find first flush forget fork free from full give
    goes good grow handle hash have head header here hold holder holding home index inode input
    insert inserts integrity into just keep kernel kill killed know last leaf left less like
    limit line lines link links list listen load lock long look loop machine main make many
    match memory merge mine more most move much must name need never next node none once only
    open order other output over page panic parse part partition path peek pipe plan point
    pointer prelude prepare present print process producer pseudo push quiet read record recover
    redraw release remove repl report reset rest root rows same scan schema screen script search
    seek select send serve settle shell show side size skip sleep socket some sort spin spinner
    split start stat state stats step stop stroke such surface swap sync table take test than
    that their theirs them then there these they this those through time timer todo tool
    trampoline trap tree true turn under unlink unlock until update user value wait wake wakeup
    walk want well were what when where which while will with word work workloads writable write
    writing yield your zero
""".split())


def plain_name(word):
    """Whether a word written without backticks in a heading may be the name of a definition:
    it has an underscore, or it is longer than 3 letters and not a common English word."""
    return "_" in word or (len(word) > 3 and word.lower() not in COMMON)


def heading_names(heading, known=()):
    """What a "### " heading names, lowercased: its `code` spans ("kfree()" as "kfree"), all of it
    when it has none, and each word written plainly that is exactly the name of a definition in
    known and passes plain_name ("### Writing node_insert, step by step" names "node_insert")."""
    spans = re.findall(r"`([^`]+)`", heading)
    named = [re.sub(r"\(\)$", "", n.strip()).lower() for n in spans or [heading]]
    if known:
        named += [w.lower() for w in WORD.findall(re.sub(r"`[^`]*`", " ", heading)) if w in known and plain_name(w)]
    return list(dict.fromkeys(named))


def defined(blocks):
    """Every name the blocks' code defines (their "defs"), as written."""
    return {d for b in blocks for d in b.get("defs", ()) if d}


def lead_target(heading, blocks, known):
    """The index of the block a "### " heading names, or None. First the blocks it names by a
    title, a file or the function a region is in (the first such block, for its first such name);
    then the definitions a block shows (definitions), only where one block alone shows the name:
    two new files that both define main() leave "### `main`" with neither."""
    named = heading_names(heading, known)
    for n in named:
        for k, b in enumerate(blocks):
            if n in {x.lower() for x in b["names"] if x}:
                return k
    for n in named:
        hits = [k for k, b in enumerate(blocks) if n in {x.lower() for x in b.get("defs", ()) if x}]
        if len(hits) == 1:
            return hits[0]
    return None


def talked_about(block, headings, known):
    """The definitions in a block that the "### " headings of its lead-ins name, by name or by the
    title of a region in them (a new file's "owner"); None when one of the headings names none of
    them, so it talks about the file as a whole."""
    defs = {d.lower(): d for d in block.get("defs", ())}
    owner = block.get("owner", {})
    out = set()
    for heading in headings:
        here = set()
        for n in heading_names(heading, known):
            here.update(x for x in (defs.get(n), owner.get(n)) if x)
        if not here:
            return None
        out |= here
    return out


def take_lead_ins(md, blocks, leads):
    """Move the "### name" sections of md whose heading names a block (see lead_target: its
    title, function or file, case-insensitive; `code` in the heading counts, and so does a
    function's name written plainly) into leads[block index]. Returns md without them. A
    section goes to one block, once."""
    if not md:
        return md
    chunks, cur, fence = [[None, []]], None, None
    for line in md.split("\n"):
        fm = FENCE_LINE.match(line)
        if fm:
            fence = None if fence and line.strip().startswith(fence) else (fence or fm.group(1))
        hm = None if fence else H3.match(line)
        if hm or (not fence and re.match(r"^##\s", line)):
            chunks.append([hm.group(1) if hm else None, [line]])
        else:
            chunks[-1][1].append(line)
    keep, known = [], defined(blocks)
    for heading, lines in chunks:
        target = lead_target(heading, blocks, known) if heading else None
        if target is None:
            keep.append("\n".join(lines))
        else:
            leads.setdefault(target, []).append((heading, "\n".join(lines[1:]).strip()))
            leads.setdefault("order", []).append(target)          # the order the notes introduce them in
    return "\n".join(keep).strip()


# ---------------------------------------------------------------- the guided path

# Doc headings -> steps. Lesson docs are moving from the old headings to the new ones
# ("Where this fits", "The idea", "Go deeper"); both render.
STEP_OF = {"where this fits": "where", "the idea": "goal", "what you are building": "goal", "run it": "run",
           "how it works": "why", "decide the boundary": "why", "break it": "break", "go deeper": "deeper",
           "read more in ostep": "deeper"}
STEP_TITLE = {"where": "Where this fits", "idea": "The idea", "goal": "Goal", "code": "The code", "run": "Run it",
              "why": "How it works", "break": "Break it", "deeper": "Go deeper"}
FENCE_LINE = re.compile(r"^\s*(`{3,}|~{3,})")


def split_doc(md):
    """Split a lesson doc by its h2 headings into the steps around the code.

    Returns {part: markdown} for intro, where ("Where this fits"), goal ("The idea", or the older
    "What you are building"), run, why, break, deeper. A doc with none of the known headings goes whole into intro, which
    is shown under Goal. An unknown heading is kept, under why, as a subheading; so is "Decide
    the boundary". "Related:" lines move to deeper."""
    intro, secs, cur, fence = [], [], None, None
    for line in (md or "").split("\n"):
        fm = FENCE_LINE.match(line)
        if fm:
            fence = None if fence and line.strip().startswith(fence) else (fence or fm.group(1))
        hm = None if fence else re.match(r"^##\s+(.+?)\s*#*\s*$", line)
        if hm:
            cur = [hm.group(1), []]
            secs.append(cur)
        elif cur is None:
            intro.append(line)
        else:
            cur[1].append(line)
    if not any(h.lower() in STEP_OF for h, _ in secs):
        return {"intro": (md or "").strip()}
    out = {"intro": ["\n".join(intro).strip()], "where": [], "goal": [], "run": [], "why": [], "break": [], "deeper": []}
    related = []
    for heading, lines in secs:
        step = STEP_OF.get(heading.lower(), "why")
        keep, fence = [], None
        for line in lines:
            fm = FENCE_LINE.match(line)
            if fm:
                fence = None if fence and line.strip().startswith(fence) else (fence or fm.group(1))
            if not fence and not fm and line.startswith("Related:"):
                related.append(line)
            else:
                keep.append(line)
        body = "\n".join(keep).strip()
        if step == "why" and heading.lower() != "how it works":   # the step's own title needs no subheading
            body = f"### {heading}\n\n{body}"
        out[step].append(body)
    out["deeper"].extend(related)
    return {k: "\n\n".join(x for x in v if x).strip() for k, v in out.items()}


def lesson_page(track, lesson, static=False):
    """static: for ./learn export (harness/web/export.py), with nothing that needs ./learn serve or this machine."""
    meta, md = doc_info(lesson)
    files, note = code_files(track, lesson, meta)

    def resolve(href):
        path = href.split("#", 1)[0]
        if re.match(r"^[a-z][a-z0-9+.-]*:|^/", path, re.I) or not path:
            return None
        base = os.path.basename(path)
        m = re.match(r"^(\d\d\.\d\d)-.*\.md$", base)
        if m and any(l.id == m.group(1) for l in track.lessons):
            return f"/t/{track.id}/{m.group(1)}"
        if base == "README.md":
            mm = re.search(r"(\d\d)-[^/]+/README\.md$", path) or re.match(r"^(\d\d)-", os.path.basename(os.path.dirname(path)))
            if mm:
                return f"/t/{track.id}#m-{mm.group(1)}"
        return None

    def resolve_or_dead(href):
        r = resolve(href)
        if r:
            return r
        if re.match(r"^(https?:|mailto:|#)", href, re.I):
            return None
        return "#"  # a relative link to something the web UI does not serve

    def figure(src):
        return art.doc_figure(lesson.doc, src)

    def reader(markdown, lede=False):
        return f'<div class="reader{" lede" if lede else ""}">{render(markdown, resolve_or_dead, figure)}</div>' if markdown else ""

    tabs, panes = [], []
    for k, (name, src, trunc) in enumerate(files):
        on = k == 0
        lines = src.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        gutter = "\n".join(str(i) for i in range(1, len(lines) + 1))
        tabs.append(f'<button class="tab" role="tab" type="button" id="tab-{k}" aria-controls="file-{k}" aria-selected="{"true" if on else "false"}">{esc(name)}</button>')
        cut = '<div class="file-note">File truncated for display.</div>' if trunc else ""
        panes.append(f'<div class="file{" on" if on else ""}" id="file-{k}" role="tabpanel" aria-labelledby="tab-{k}">'
                     f'<pre class="gutter" aria-hidden="true">{gutter}</pre><pre class="src"><code>{chr(10).join(highlight.highlight_lines(chr(10).join(lines), highlight.language_for(name)))}</code></pre></div>{cut}')
    path = lesson_path(track, lesson)    # the core, or this lesson's extension: the pager stays on it
    idx = path.index(lesson)
    proj = tl.Project(track)
    blocks = code_blocks(track, lesson.id, proj)

    def also(apart=()):
        """(blocks of also_blocks, its counted declarations: one per header)."""
        got = also_blocks(track, lesson.id, proj, blocks, apart)
        return [b for b in got if not b.get("decls")], [b for b in got if b.get("decls")]
    extra, decls = also()                # after the lesson's own blocks, indexes len(blocks)...
    parts = split_doc(md) if md else {}
    probe = {}                           # what the notes name among those: a block of its own, under its notes
    for part in ("where", "goal", "why"):
        if parts.get(part):
            take_lead_ins(parts[part], blocks + extra, probe)
    known = defined(blocks + extra)
    apart = {n for k, got in probe.items() if k != "order" and k >= len(blocks) for h, _ in got for n in heading_names(h, known)}
    if apart:
        extra, decls = also(apart)
    leads = {}                           # block index -> [(heading, markdown)]: the why, shown above the code
    for part in ("where", "goal", "why"):
        if parts.get(part):
            parts[part] = take_lead_ins(parts[part], blocks + extra, leads)

    steps = []   # (step id, inner html)
    head_extra = {}   # step id -> a control shown on that step's heading line

    # Where this fits (the intro and the map), then The idea; a doc without "Where this fits"
    # keeps one Goal step: the intro, the figure, then The idea.
    fig = art.lesson_figure(track, lesson) if md else ""
    fig = f'<figure class="art fig">{fig}</figure>' if fig else ""
    code_tabs = ""
    if files and not blocks:
        code_tabs = (f'<div class="code-block-shell goal-code"><div class="tabs" role="tablist">{"".join(tabs)}</div>{"".join(panes)}'
                     + (f'<div class="file-note">{esc(note)}</div>' if note else "") + "</div>")
    if md and parts.get("where"):
        steps.append(("where", reader(parts.get("intro", ""), lede=True) + reader(parts["where"])))
        idea = fig + reader(parts.get("goal", "")) + code_tabs
        if idea:
            steps.append(("idea", idea))
    else:
        goal_html = (reader(parts.get("intro", ""), lede=True) + fig + reader(parts.get("goal", ""))) if md else ""
        goal_html += code_tabs
        if goal_html:
            steps.append(("goal", goal_html))

    # The code: what this lesson adds, as the track has it, each piece after the why. Pieces the
    # notes introduce come in the order the notes do; the rest follow in file order. A new file
    # longer than NEW_LONG starts folded to its functions, all but those its lead-ins name (all of
    # it open when one talks about the file as a whole), or, with none to fold and no lead-in, as
    # its first CLIP lines. Then the rest of what the lesson adds to files that
    # were there already: a piece the notes introduce is shown like the lesson's own, under its
    # notes; everything else waits behind one quiet disclosure row, "Also added in this lesson",
    # closed at first (open, with no row, when it is all the code the lesson has). Inside it, when
    # the group is long, what it brings starts folded, a list of functions under their comments,
    # and the declarations a header gains are one counted row per file.
    if blocks or extra or decls:
        everything = blocks + extra
        seen = list(dict.fromkeys(k for k in leads.get("order", []) if k in leads))

        def ordered(ks):
            return [k for k in seen if k in ks] + [k for k in ks if k not in seen]

        long_extra = sum(len(b["shown"]) for b in extra) > LONG_ALSO

        def html_of(k):
            got = leads.get(k, [])
            lead = "".join(reader((f"#### {h}\n\n" if len(got) > 1 else "") + body) for h, body in got)
            b = everything[k]
            named = {n for h, _ in got for n in heading_names(h, known)}   # what the notes talk about stays open
            shut = {p for p, name in b.get("fresh", {}).items() if name.lower() not in named} if long_extra else ()
            clip = None
            if k < len(blocks) and b["new"] and len(b["shown"]) > NEW_LONG:
                text = [t for _, t in b["shown"]]
                fns = [(tl.function_name(text[head:first]), first) for head, first, last in tl.functions(text)
                       if first <= last] if tl.is_c(b["path"]) else []
                talked = talked_about(b, [h for h, _ in got], known)
                if fns and talked is not None:
                    shut = {a for name, a in fns if name not in talked}   # its functions, each under its comment
                elif not got:
                    clip = CLIP                                        # data: its first lines
            return code_block(track, b, f'<div class="lead">{lead}</div>' if lead else "", editor_link=not static,
                              shut=shut, clip=clip)
        html_blocks = "".join(html_of(k) for k in ordered(range(len(blocks))))
        if extra or decls:
            ks = ordered(range(len(blocks), len(everything)))
            for k in [k for k in ks if everything[k].get("more")]:   # the rest of a file right after its named part
                ks.remove(k)
                ks.insert(ks.index(k - 1) + 1, k)
            open_ks = [k for k in ks if leads.get(k)]                 # under the notes that introduce them
            rest = [k for k in ks if not leads.get(k)]
            counted = "".join(f'<li><code>{esc(d["titles"][0])}</code>: {plural(d["decls"], "declaration")}</li>'
                              for d in decls)
            counted = f'<ul class="also-decls">{counted}</ul>' if counted else ""
            inner = "".join(html_of(k) for k in rest) + counted
            if not blocks and not open_ks:
                html_blocks += f'<div class="also alone">{inner}</div>'
            else:
                n_files = len({everything[k]["path"] for k in rest} | {d["path"] for d in decls})
                n_lines = sum(1 for k in rest for n, _ in everything[k]["shown"] if n is not None) + sum(d["lines"] for d in decls)
                more = (f'<details class="also-more"><summary class="also-sum">{CHEV_R}<span class="also-t">Also added in this lesson</span> '
                        f'<span class="also-count">- {plural(n_files, "file")}, {n_lines:,} line{"" if n_lines == 1 else "s"}</span></summary>'
                        f'<div class="also-body">{inner}</div></details>') if inner else ""
                html_blocks += f'<div class="also{" first" if not blocks else ""}">{"".join(html_of(k) for k in open_ks)}{more}</div>'
        foldable = any(tl.is_c(b["path"]) and tl.function_bodies([t for _, t in b["shown"]]) for b in everything)
        if foldable:
            head_extra["code"] = fold_bar("code-fold")   # on the heading's line, not a row of its own
        steps.append(("code", f'<div class="code-fold" id="code-fold">{html_blocks}</div>'))

    # Run it, Why, Break it, Go deeper: the doc's own sections. The doc's "Run it" is the only
    # source of the commands to type; a doc without one has no Run it step.
    for sid in ("run", "why", "break", "deeper"):
        if parts.get(sid):
            steps.append((sid, reader(parts[sid])))

    sections = ""
    rail = ""
    for n, (sid, inner) in enumerate(steps, 1):
        title = STEP_TITLE[sid]
        head = f'<h2 class="sec-title"><span class="step-n">{n}</span><span>{title}</span></h2>'
        if sid in head_extra:   # a control beside the heading, outside the h2 so its name stays the title
            head = f'<div class="step-head">{head}{head_extra[sid]}</div>'
        sections += f'<section class="sec step step-{sid}" id="step-{sid}" aria-label="{title}">{head}{inner}</section>'
        rail += f'<li><a href="#step-{sid}"><span class="path-n">{n}</span><span class="path-t">{title}</span></a></li>'
    notice = '<p class="notice">The notes for this lesson are not written yet.</p>' if md is None else ""

    prev_l = path[idx - 1] if idx > 0 else None
    next_l = path[idx + 1] if idx + 1 < len(path) else None
    labels = ('<span class="tag opt">optional</span>' if lesson.optional else "") + \
        "".join(f'<span class="tag">{esc(x)}</span>' for x in lesson.labels)
    mod_icon = art.module_art(track, lesson.module[0], "icon")
    mod_icon = f'<span class="mod-ic">{mod_icon}</span>' if mod_icon else ""
    body = f"""<div class="wrap lesson-wrap">
<div class="lesson-cols"><div class="lesson-main">
<header class="lesson-head">
<p class="crumb-line"><a href="/t/{esc(track.id)}">{CHEV_L}<span>Overview</span></a><span class="sep">/</span><span class="cl-mod">{mod_icon}<span>Module {esc(lesson.module[0])} &middot; {esc(lesson.module[1])}</span></span><span class="sep">/</span><span class="cl-id">{esc(lesson.id)}</span></p>
<h1>{esc(lesson.title)}</h1>
<div class="head-meta">{labels}<span class="spacer"></span><button class="btn" type="button" data-drawer-open="files-drawer" aria-controls="files-drawer" aria-expanded="false" aria-haspopup="dialog">{FOLDER}<span>Files</span></button></div>
</header>
{notice}
{sections}
</div>
<aside class="lesson-rail"><nav class="path" aria-label="This lesson"><ol>{rail}</ol></nav></aside></div>
</div>
{files_drawer(track, lesson, proj, static)}"""
    # Plain navigation: previous, where you are in the module, and Next (none after the last
    # lesson of the core or of an extension).
    in_module = [l for l in track.lessons if l.module[0] == lesson.module[0]]
    pager = f'<nav class="lesson-bar" aria-label="Lessons"><span class="bar-mid">'
    pager += (f'<a class="round" href="/t/{esc(track.id)}/{esc(prev_l.id)}" aria-label="Previous lesson" title="{esc(prev_l.id)} {esc(prev_l.title)}">{CHEV_L}</a>'
              if prev_l else f'<span class="round off">{CHEV_L}</span>')
    pager += (f'<a class="bar-pill" href="/t/{esc(track.id)}#m-{esc(lesson.module[0])}"><span>{esc(lesson.module[1])}</span>'
              f'<em>{in_module.index(lesson) + 1}/{len(in_module)}</em></a></span>')
    if next_l:
        pager += (f'<a class="btn primary" href="/t/{esc(track.id)}/{esc(next_l.id)}" rel="next" title="{esc(next_l.id)} {esc(next_l.title)}">'
                  f'<span>Next</span>{ARROW}</a>')
    pager += '</nav>'
    return page(f"{lesson.id} {lesson.title} - {SITE}", body, track=track, lesson=lesson, bottom=pager)


def error_page(code, message):
    return page(f"{code} - {SITE}",
                f'<div class="wrap"><h1 class="ov-title">{code}</h1><p class="empty">{esc(message)} <a class="inline-link" href="/">Back to the map.</a></p></div>',
                home=True)
