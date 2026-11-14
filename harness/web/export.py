"""./learn export <outdir>: the site as plain files, for a static host such as Vercel.

The export is what ./learn serve serves, page for page:

    index.html                          /
    t/<track>/index.html                /t/<track>: a track's map, or an outline's overview
    t/<track>/<NN.LL>/index.html        /t/<track>/<NN.LL>: a lesson
    credits/index.html                  /credits: what each track is built on, the licences in full
    404.html                           any other path (Vercel serves it for a path it does not have)
    static/...                          app.css, app.js, the fonts and their licence
    api/file/<track>/<NN.LL>.json       the Files drawer's index for one lesson: {path: URL of its view}
    api/file/<track>/v/<hash>.json      one file as it stands at a lesson (what /api/file answers),
                                        stored once however many lessons it looks the same at

A static host cannot route on a query string, so lesson pages are rendered with static=True:
the drawer carries data-index and app.js reads that index instead of asking /api/file, and
"Open in editor", a link into the author's own checkout, is left out. Links to pages end in
"/" (/t/xv6/01.01/): every static host serves a directory's index.html for that form without
a redirect, whatever the last path segment looks like. Nothing in an export names a path on
this machine; export() checks that before it reports success.
"""

import hashlib
import json
import os
import re
import shutil

from harness import core
from harness import outlines as ol
from harness import timeline as tl
from harness.web import server, views

HERE = os.path.dirname(os.path.abspath(__file__))
OWN = {"index.html", "404.html", "static", "t", "api", "credits"}     # everything an export writes at its top
FOLD_ID = re.compile(r"fv-fold-(\d+)")
PAGE_LINK = re.compile(r'(href=")(/t/[^"#?]*?|/credits)/?((?:#[^"]*)?")')
TEXT = (".html", ".json", ".css", ".js", ".txt")


class ExportError(Exception):
    pass


def slash_links(html):
    """Page links in their directory form: /t/xv6/01.01 -> /t/xv6/01.01/, /t/xv6#m-01 -> /t/xv6/#m-01."""
    return PAGE_LINK.sub(lambda m: m.group(1) + m.group(2) + "/" + m.group(3), html)


def static_files():
    """[(path under /static/, file)]: every asset the server answers under /static/."""
    out = []
    for sub in ("", "fonts/"):
        folder = os.path.join(HERE, *sub.split("/"))
        for name in sorted(os.listdir(folder)):
            rel = sub + name
            if (server.STATIC_FILE.match("/static/" + rel) and os.path.isfile(os.path.join(folder, name))
                    and (not rel.endswith(".txt") or rel == "fonts/LICENSE-OFL.txt")):
                out.append((rel, os.path.join(folder, name)))
    return out


def file_view(track, lesson_id, rel, proj):
    """The JSON /api/file answers for rel at lesson_id, or None when the file is not there yet.
    Fold ids come from a counter that runs on across renders, so they are numbered afresh per
    view: a file that reads the same at two lessons is then the same bytes, and stored once."""
    try:
        view = views.render_file_view(track, lesson_id, rel, proj)
    except OSError:
        return None
    if view is None:
        return None
    ids = {}
    return FOLD_ID.sub(lambda m: "fv-fold-%d" % ids.setdefault(m.group(1), len(ids) + 1), json.dumps(view))


def prepare(out):
    """Make out an empty directory to write to: a new one, an empty one, or an earlier export
    (replaced whole, keeping dotfiles such as .vercel/ and a vercel.json of your own). Anything
    else is refused, so a mistyped path never loses files; so is a folder the site would show."""
    real = os.path.realpath(out)
    for inside in (core.TRACKS_DIR, ol.OUTLINES_DIR, os.path.join(core.ROOT, "harness")):
        inside = os.path.realpath(inside)
        if real == inside or real.startswith(inside + os.sep):
            raise ExportError(f"{out} is inside {os.path.relpath(inside, core.ROOT)}/, which the site itself is made from")
    if os.path.exists(out):
        if not os.path.isdir(out):
            raise ExportError(f"{out} is a file")
        names = [n for n in os.listdir(out) if not n.startswith(".") and n != "vercel.json"]
        if names and not (set(names) <= OWN and "index.html" in names):
            raise ExportError(f"{out} is not empty and not an earlier export: pick a new directory")
        for n in names:
            p = os.path.join(out, n)
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
    os.makedirs(out, exist_ok=True)


def leaks(out):
    """[(file, path)] for every exported text file that names a path on this machine (the
    longest one it names: the checkout, the tracks, the outlines, the home directory)."""
    needles = set()
    for p in (core.ROOT, core.TRACKS_DIR, ol.OUTLINES_DIR, os.path.expanduser("~")):
        needles |= {x for x in (p, os.path.realpath(p)) if x and len(x.strip(os.sep)) > 1}
    needles = sorted(needles, key=len, reverse=True)
    found = []
    for dirpath, _, filenames in os.walk(out):
        for fn in filenames:
            if not fn.endswith(TEXT):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            hit = next((n for n in needles if n in text), None)
            if hit:
                found.append((os.path.relpath(path, out), hit))
    return sorted(found)


def export(out):
    """Write the whole site to out (see the module doc). Returns a summary dict:
    files, bytes, pages, views (lesson x file responses) and stored (distinct views)."""
    prepare(out)
    stats = {"files": 0, "bytes": 0, "pages": 0, "views": 0, "stored": 0}

    def write(rel, data):
        data = data.encode("utf-8") if isinstance(data, str) else data
        path = os.path.join(out, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        stats["files"] += 1
        stats["bytes"] += len(data)

    def page(url, html):
        write((url.strip("/") + "/index.html").lstrip("/"), slash_links(html))
        stats["pages"] += 1

    page("/", views.home_page())
    page("/credits", views.credits_page())
    write("404.html", slash_links(views.error_page(404, "Page not found.")))
    stats["pages"] += 1
    for rel, full in static_files():
        with open(full, "rb") as f:
            write("static/" + rel, f.read())
    for o in views.outlines():
        page(f"/t/{o.id}", views.outline_page(o))
    for track in views.tracks():
        page(f"/t/{track.id}", views.track_page(track))
        proj = tl.Project(track)
        stored = set()
        for lesson in track.lessons:
            page(f"/t/{track.id}/{lesson.id}", views.lesson_page(track, lesson, static=True))
            index = {}
            for rel in proj.files_at(lesson.id):
                data = file_view(track, lesson.id, rel, proj)
                if data is None:
                    continue
                digest = hashlib.sha256(data.encode("utf-8")).hexdigest()[:20]
                index[rel] = f"/api/file/{track.id}/v/{digest}.json"
                stats["views"] += 1
                if digest not in stored:
                    stored.add(digest)
                    write(f"api/file/{track.id}/v/{digest}.json", data)
            write(views.STATIC_INDEX.format(track=track.id, lesson=lesson.id).lstrip("/"), json.dumps(index))
        stats["stored"] += len(stored)
    stats["leaks"] = leaks(out)
    return stats
