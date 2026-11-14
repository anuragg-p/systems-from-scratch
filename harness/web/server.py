"""The local web UI for ./learn serve. Standard library only, 127.0.0.1 only.

    GET  /                          home: tagline and every track
    GET  /t/<track>                 track map (for an outline in outlines/: its coming-soon overview)
    GET  /t/<track>/<NN.LL>         lesson page: one guided path of steps (an outline has none: 404)
    GET  /credits                   what each track is built on, with the licences in full
    GET  /api/file/<track>?path=P[&lesson=NN.LL]
                                    one file of the track as it stands at that lesson (at the end of the track
                                    without one), for the Files viewer; 404 for a file that is not there yet

The site is read-only: it shows the reference code in tracks/ and never runs anything.
Workspaces (./learn start, next, extend) are a command-line matter; nothing here touches them.
"""

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from harness.web.views import (FULL_ID, credits_page, error_page, find_outline, find_track, home_page, hidden_files,
                               lesson_page, outline_page, render_file_view, track_page, tree_files)

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
STATIC_FILE = re.compile(r"^/static/((?:fonts/)?[A-Za-z0-9._-]+\.(?:css|js|woff2|txt))$")
TYPES = {"css": "text/css", "js": "text/javascript", "woff2": "font/woff2", "txt": "text/plain"}


# ---------------------------------------------------------------- http

class Handler(BaseHTTPRequestHandler):
    server_version = "learn-web"

    def log_message(self, fmt, *args):
        if getattr(self.server, "verbose", False):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # -- plumbing
    def send_bytes(self, status, data, ctype="text/html; charset=utf-8", extra=()):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if not any(k == "Cache-Control" for k, _ in extra):
            self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def send_html(self, status, text):
        self.send_bytes(status, text.encode("utf-8"))

    def send_json(self, status, obj):
        self.send_bytes(status, json.dumps(obj).encode(), "application/json")

    def local_only(self):
        """Refuse foreign Host (DNS rebinding) and foreign Origin (cross-site POST)."""
        host = urlsplit("//" + (self.headers.get("Host") or "")).hostname
        if host not in LOCAL_HOSTS:
            self.send_html(403, error_page(403, "Only local requests are served."))
            return False
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).hostname not in {"127.0.0.1", "localhost", "::1"}:
            self.send_html(403, error_page(403, "Cross-site requests are refused."))
            return False
        return True

    # -- GET
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self.local_only():
            return
        path = urlsplit(self.path).path
        try:
            if path == "/":
                return self.send_html(200, home_page())
            if path in ("/credits", "/credits/"):
                return self.send_html(200, credits_page())
            sm = STATIC_FILE.match(path)
            if sm:
                full = os.path.join(HERE, *sm.group(1).split("/")) if not sm.group(1).startswith("fonts/") else \
                    os.path.join(HERE, "fonts", sm.group(1)[6:])
                if sm.group(1) == "fonts/LICENSE-OFL.txt" or not sm.group(1).endswith(".txt"):
                    if os.path.isfile(full):
                        with open(full, "rb") as f:
                            ext = full.rsplit(".", 1)[1]
                            return self.send_bytes(200, f.read(), TYPES[ext] + ("; charset=utf-8" if ext != "woff2" else ""),
                                                   (("Cache-Control", "max-age=86400"),) if ext == "woff2" else ())
                return self.send_html(404, error_page(404, "Page not found."))
            m = re.match(r"^/api/file/([^/]+)$", path)
            if m:
                return self.api_file(m.group(1), parse_qs(urlsplit(self.path).query))
            m = re.match(r"^/t/([^/]+)(?:/([^/]+))?/?$", path)
            if m:
                track = find_track(m.group(1))
                if not track:
                    outline = find_outline(m.group(1))
                    if outline is None:
                        return self.send_html(404, error_page(404, "No such track."))
                    if m.group(2) is None:
                        return self.send_html(200, outline_page(outline))
                    return self.send_html(404, error_page(404, "This track is an outline: its lessons are not written yet."))
                if m.group(2) is None:
                    return self.send_html(200, track_page(track))
                lid = m.group(2)
                lesson = next((l for l in track.lessons if l.id == lid), None) if FULL_ID.match(lid) else None
                if not lesson:
                    return self.send_html(404, error_page(404, "No such lesson."))
                return self.send_html(200, lesson_page(track, lesson))
            self.send_html(404, error_page(404, "Page not found."))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            self.send_html(500, error_page(500, f"{type(e).__name__}: {e}"))

    def api_file(self, track_id, query):
        track = find_track(track_id)
        if not track:
            return self.send_json(404, {"error": "no such track"})
        rel = (query.get("path") or [""])[0]
        lesson = (query.get("lesson") or [None])[0]
        parts = rel.split("/")
        if (not rel or "\0" in rel or "\\" in rel or rel.startswith("/") or ".." in parts or "." in parts
                or "" in parts or len(rel) > 400):
            return self.send_json(400, {"error": "bad path"})
        if lesson is not None and not FULL_ID.match(lesson):
            return self.send_json(400, {"error": "bad lesson id"})
        if rel not in set(tree_files(track.root, hidden_files(track))):
            return self.send_json(404, {"error": "no such file"})
        try:
            view = render_file_view(track, lesson, rel)
        except OSError:
            view = None
        if view is None:                       # not there yet at that lesson
            return self.send_json(404, {"error": "no such file at this lesson"})
        self.send_json(200, view)

    # -- POST: nothing on the site changes anything
    def do_POST(self):
        if not self.local_only():
            return
        self.send_bytes(404, b"not found\n", "text/plain; charset=utf-8")


class WebServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port=8000, verbose=False):
        super().__init__(("127.0.0.1", port), Handler)
        self.verbose = verbose


def serve(port=8000):
    try:
        srv = WebServer(port, verbose=True)
    except OSError as e:
        print(f"cannot listen on 127.0.0.1:{port}: {e}")
        return 1
    print(f"systems from scratch: http://127.0.0.1:{srv.server_address[1]}/  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        srv.server_close()
    return 0
