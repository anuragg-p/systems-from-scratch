"""Tests for the web UI: the markdown renderer and the server, against a sample track."""

import http.client
import json
import re
import os
import shutil
import tempfile
import threading
import unittest
import urllib.parse

from harness import outlines as outlines_mod

SAMPLE_TRACK = '''
from harness.core import Fail  # noqa: F401

TITLE = "Sample <b>track</b>"
KIND = "demo"
SUMMARY = "A tiny track for the web tests."
'''

# A track with the optional run hooks that `./learn run` uses (the site shows only the doc's Run it).
RUNNABLE = '''
import os

TITLE = "Forge"
KIND = "demo"
SUMMARY = "A track you build yourself."
SOURCES = ["src/*.c"]
STUBS = {".c": 'panic("{id}: {title} not written yet");'}


def prepare(root):
    if os.path.exists(os.path.join(root, "fail-build")):
        return ["sh", "-c", "echo compile error: oops; exit 3"]
    return ["echo", "built in " + root]


def run_argv(root):
    return ["cat"]
'''

DOC_ONE = """---
id: 01.01
title: Say hello
labels: with code, demo
code: src/hello.txt, src/missing.txt
test: tests/0101_say_hello.py
---

# 01.01 Say hello

Intro with `code` and <script>alert(1)</script>.

## Run it

See [the next one](01.02-second.md) and [outside](https://example.com).
"""

TEST_PASS = '''"""01.01 Say hello
"""


def test(t):
    s = t.spawn(["echo", "hello from sample"], name="echo")
    s.expect(r"hello from sample")
'''

TEST_FAIL = '''"""01.02 Second lesson, no doc
"""
from harness.core import Fail


def test(t):
    raise Fail("this one fails on purpose")
'''


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class RendererTests(unittest.TestCase):
    def render(self, text, resolve=None):
        from harness.web.markdown import render
        return render(text, resolve)

    def test_escapes_html_everywhere(self):
        out = self.render("# <img src=x onerror=1>\n\n<script>alert(1)</script> **<b>x</b>**\n\n"
                          "- <i>item</i>\n\n> <u>q</u>\n\n| <a> |\n|---|\n| <b> |\n\n```\n<div>\n```")
        for raw in ("<script", "<img", "<i>", "<u>", "<a>", "<b>", "<div>"):
            self.assertNotIn(raw, out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("&lt;div&gt;", out)

    def test_blocks(self):
        out = self.render("## Title\n\npara one\nstill one\n\n- a\n- b\n  - nested\n\n1. x\n2. y\n\n"
                          "> quote\n\n| h1 | h2 |\n|----|---:|\n| 1 | 2 |\n\n```c\nint x;\n```")
        self.assertIn('<h2 id="title">Title</h2>', out)
        self.assertIn("<p>para one still one</p>", out)
        self.assertIn("<ul><li>a</li><li>b", out)
        self.assertIn("<ul><li>nested</li></ul>", out)
        self.assertIn("<ol><li>x</li><li>y</li></ol>", out)
        self.assertIn("<blockquote><p>quote</p></blockquote>", out)
        self.assertIn("<th>h1</th>", out)
        self.assertIn('<td style="text-align:right">2</td>', out)
        self.assertIn('<pre><code class="lang-c">', out)
        self.assertIn('<span class="tk-t">int</span> x;</code></pre>', out)

    def test_inline(self):
        out = self.render("**bold** and *it* and `a < b` and _under_ and snake_case_name")
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn("<em>it</em>", out)
        self.assertIn("<code>a &lt; b</code>", out)
        self.assertIn("<em>under</em>", out)
        self.assertIn("snake_case_name", out)

    def test_code_is_not_formatted(self):
        out = self.render("`**x**` and\n\n```\n**y** [a](b)\n```")
        self.assertIn("<code>**x**</code>", out)
        self.assertIn("**y** [a](b)", out)

    def test_links(self):
        out = self.render("[a](https://e.com/?x=1&y=2) [b](02.03-x.md) [c](javascript:alert(1))",
                          lambda h: "/t/x/02.03" if h.endswith(".md") else None)
        self.assertIn('href="https://e.com/?x=1&amp;y=2"', out)
        self.assertIn('href="/t/x/02.03"', out)
        self.assertNotIn("javascript:", out)


class HighlightTests(unittest.TestCase):
    def hl(self, text, lang):
        from harness.web.highlight import highlight_lines
        return highlight_lines(text, lang)

    def test_language_from_file_names_and_fences(self):
        from harness.web.highlight import fence_lang, language_for
        names = {"kernel/proc.c": "c", "kernel/defs.h": "c", "kernel/entry.S": "asm", "a.s": "asm", "t.py": "python",
                 "Makefile": "make", "rules.mk": "make", "kernel/kernel.ld": "ld", "x.pl": "perl", "run.sh": "sh",
                 "README.md": "plain", "notes": "plain"}
        for name, lang in names.items():
            self.assertEqual(language_for(name), lang, name)
        for info, lang in {"c": "c", "asm": "asm", "sh": "sh", "python": "python", "make": "make", "text": "plain", "": "plain"}.items():
            self.assertEqual(fence_lang(info), lang, info)

    def test_c_tokens(self):
        out = self.hl('static struct spinlock lk;\nuint64 x = 0x1F + 10L;\nreturn kfree(PHYSTOP);', "c")
        self.assertIn('<span class="tk-k">static</span> <span class="tk-k">struct</span> <span class="tk-t">spinlock</span>', out[0])
        self.assertIn('<span class="tk-t">uint64</span>', out[1])
        self.assertIn('<span class="tk-n">0x1F</span>', out[1])
        self.assertIn('<span class="tk-n">10L</span>', out[1])
        self.assertIn('<span class="tk-f">kfree</span>', out[2])
        self.assertIn('<span class="tk-v">PHYSTOP</span>', out[2])
        self.assertIn('<span class="tk-t">pte_t</span>', self.hl("pte_t *pte;", "c")[0])

    def test_c_strings_with_escapes_and_slashes(self):
        line = self.hl('char *s = "a \\" // not a comment"; // real', "c")[0]
        self.assertIn('<span class="tk-s">&quot;a \\&quot; // not a comment&quot;</span>', line)
        self.assertEqual(line.count('class="tk-c"'), 1)
        self.assertTrue(line.endswith('<span class="tk-c">// real</span>'))
        self.assertIn('<span class="tk-s">&#x27;\\&#x27;&#x27;</span>', self.hl("c = '\\'';", "c")[0])

    def test_c_block_comments_span_lines_and_preprocessor(self):
        out = self.hl("int a; /* one\n   int b = 1;\n   end */ int c;\n#include <stdarg.h>\n#define N 4", "c")
        self.assertIn('<span class="tk-c">/* one</span>', out[0])
        self.assertEqual(out[1], '<span class="tk-c">   int b = 1;</span>')    # nothing inside is a keyword
        self.assertTrue(out[2].startswith('<span class="tk-c">   end */</span>'))
        self.assertIn('<span class="tk-t">int</span> c;', out[2])
        self.assertIn('<span class="tk-p">#include</span> <span class="tk-s">&lt;stdarg.h&gt;</span>', out[3])
        self.assertIn('<span class="tk-p">#define</span> N <span class="tk-n">4</span>', out[4])

    def test_build_markers_stay_comments(self):
        for line in ("// @build 02.02 kfree", "// @stub panic(1);", "// @end"):
            out = self.hl(line, "c")[0]
            self.assertEqual(out, f'<span class="tk-c">{line}</span>')

    def test_asm_tokens(self):
        src = '#include "riscv.h"\n.section .text\n.globl _entry\n_entry:\n  csrr a1, mhartid # who\n  li sp, 0x80000\n  ld t0, 8(sp)\n  call start'
        out = self.hl(src, "asm")
        self.assertIn('<span class="tk-p">#include</span>', out[0])
        self.assertIn('<span class="tk-p">.section</span>', out[1])
        self.assertIn('<span class="tk-p">.globl</span>', out[2])
        self.assertIn('<span class="tk-l">_entry</span>:', out[3])
        self.assertIn('<span class="tk-i">csrr</span> <span class="tk-r">a1</span>, <span class="tk-r">mhartid</span>', out[4])
        self.assertIn('<span class="tk-c"># who</span>', out[4])
        self.assertIn('<span class="tk-i">li</span> <span class="tk-r">sp</span>, <span class="tk-n">0x80000</span>', out[5])
        self.assertIn('<span class="tk-r">t0</span>, <span class="tk-n">8</span>(<span class="tk-r">sp</span>)', out[6])
        self.assertIn('<span class="tk-i">call</span> start', out[7])
        self.assertIn('<span class="tk-r">sstatus</span>', self.hl("csrw sstatus, t1", "asm")[0])
        self.assertIn('<span class="tk-r">satp</span>', self.hl("csrr t0, satp", "asm")[0])

    def test_python_strings_comments_and_triple_quotes(self):
        out = self.hl('def f(x):  # note\n    s = """doc\n    # not a comment\n    end""" + \'a\'\n    return x', "python")
        self.assertIn('<span class="tk-k">def</span> <span class="tk-f">f</span>', out[0])
        self.assertIn('<span class="tk-c"># note</span>', out[0])
        self.assertIn('<span class="tk-s">&quot;&quot;&quot;doc</span>', out[1])
        self.assertEqual(out[2], '<span class="tk-s">    # not a comment</span>')
        self.assertIn('<span class="tk-s">    end&quot;&quot;&quot;</span>', out[3])
        self.assertIn('<span class="tk-s">&#x27;a&#x27;</span>', out[3])
        self.assertIn('<span class="tk-k">return</span>', out[4])

    def test_make_shell_and_plain(self):
        out = self.hl("CC = gcc\nall: kernel\n\t$(CC) -o $@ \"x\" # c\nifeq ($(A),1)", "make")
        self.assertIn('<span class="tk-v">CC</span>', out[0])
        self.assertIn('<span class="tk-l">all</span>', out[1])
        self.assertIn('<span class="tk-v">$(CC)</span>', out[2])
        self.assertIn('<span class="tk-s">&quot;x&quot;</span>', out[2])
        self.assertIn('<span class="tk-k">ifeq</span>', out[3])
        self.assertEqual(self.hl("a < b & c", "plain"), ["a &lt; b &amp; c"])
        self.assertIn('<span class="tk-k">if</span>', self.hl("if [ -f x ]; then", "sh")[0])

    def test_everything_is_escaped_and_lines_are_preserved(self):
        evil = '<script>alert("&")</script>\n"<b>" /* <i> */ & x < y\n\n#define A <B>\n'
        for lang in ("c", "asm", "python", "make", "ld", "perl", "sh", "plain"):
            out = self.hl(evil, lang)
            self.assertEqual(len(out), len(evil.split("\n")), lang)
            joined = "".join(out)
            stripped = re.sub(r'<span class="tk-[a-z]">|</span>', "", joined)
            self.assertNotIn("<", stripped, lang)
            self.assertNotRegex(stripped, r"&(?!amp;|lt;|gt;|quot;|#x27;)", lang)
            self.assertEqual(plain("\n".join(out)), evil, lang)
        for text in ("", "x", "a\n", "\n\n"):
            self.assertEqual(len(self.hl(text, "c")), len(text.split("\n")))

    def test_comment_colors_are_readable(self):
        css = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "app.css")).read()

        def lum(h):
            r, g, b = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

        def ratio(a, b):
            hi, lo = sorted((lum(a), lum(b)), reverse=True)
            return (hi + 0.05) / (lo + 0.05)
        light = css[:css.index(':root[data-theme="dark"]')]
        dark = css[css.index(':root[data-theme="dark"]'):]
        for block, bg_name in ((light, "light"), (dark, "dark")):
            c = re.search(r"--tk-c: (#[0-9a-f]{6})", block).group(1)
            bg = re.search(r"--code-bg: (#[0-9a-f]{6})", block).group(1)
            self.assertGreaterEqual(ratio(c, bg), 4.5, bg_name)


SVG_ICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 10h14" stroke-linecap="round"/><circle cx="10" cy="10" r="4" class="icon-circle"/></svg>'
SVG_COVER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 300"><defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6z" class="fa"/></marker></defs><rect x="10" y="10" width="100" height="50" rx="6" class="s fs"/><path d="M110 35H300" class="a" marker-end="url(#arrow)"/><text x="20" y="40" class="t mono" font-size="14" text-anchor="start">COVER-LABEL</text></svg>'
SVG_FIGURE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect x="1" y="1" width="50" height="20" class="m"/><text x="5" y="15" class="tm" font-size="12">FIGURE-LABEL</text></svg>'
SVG_EVIL = ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 10 10" onload="alert(1)">'
            '<script>alert(1)</script><style>rect{fill:red}</style><foreignObject><div>html</div></foreignObject>'
            '<a href="https://evil.example"><rect x="1" y="1" width="2" height="2"/></a>'
            '<rect x="1" y="1" width="2" height="2" onclick="alert(2)" style="fill:red" href="javascript:alert(3)" class="s"/>'
            '<path d="M0 0L5 5" fill="url(https://evil.example/x)" stroke="currentColor"/>'
            '<image href="x.png"/><text x="1" y="1" xlink:href="#a">T &amp; <tspan>U</tspan></text></svg>')
# A track's home page picture, with hostile parts the sanitizer must drop.
SVG_TRACK_ART = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 160" onload="alert(1)"><script>alert(1)</script>'
                 '<rect class="s f" x="10" y="10" width="100" height="60" rx="8"/><path class="a draw" d="M10 80L200 80" pathLength="1"/>'
                 '<rect class="fa" x="1" y="1" width="2" height="2" onclick="alert(2)" style="fill:red"/>'
                 '<a href="https://evil.example"><rect x="1" y="1" width="2" height="2"/></a>'
                 '<text class="t mono" x="20" y="40" font-size="12">TRACK-ART-LABEL</text></svg>')


class ArtTests(unittest.TestCase):
    def test_sanitizer_strips_everything_dangerous(self):
        from harness.web.art import sanitize
        out = sanitize(SVG_EVIL)
        self.assertTrue(out.startswith("<svg "))
        for bad in ("script", "alert", "<style", "foreignObject", "onload", "onclick", "style=", "href", "javascript",
                    "evil.example", "<image", "<a "):
            self.assertNotIn(bad, out, bad)
        self.assertIn('<rect x="1" y="1" width="2" height="2" class="s"></rect>', out)   # safe attributes survive
        self.assertIn("T &amp; <tspan>U</tspan>", out)
        self.assertIn('stroke="currentColor"', out)

    def test_sanitizer_keeps_internal_refs_and_rejects_bad_input(self):
        from harness.web.art import sanitize
        out = sanitize(SVG_COVER, prefix="p1")
        self.assertIn('id="p1-arrow"', out)
        self.assertIn('marker-end="url(#p1-arrow)"', out)
        self.assertIn('viewBox="0 0 640 300"', out)
        self.assertEqual(sanitize("not svg"), "")
        self.assertEqual(sanitize("<html><body/></html>"), "")
        self.assertEqual(sanitize('<!DOCTYPE svg [<!ENTITY a "b">]><svg viewBox="0 0 1 1"/>'), "")
        self.assertEqual(sanitize('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'), "")  # no viewBox
        self.assertEqual(sanitize("<svg " + "x" * 300000), "")

    def test_sanitizer_drops_root_size_so_css_scales_it(self):
        from harness.web.art import sanitize
        out = sanitize('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 300" width="640" height="300"><rect width="5" height="5"/></svg>')
        self.assertNotIn('width="640"', out)
        self.assertIn('<rect width="5" height="5">', out)


class ArtPageTests(unittest.TestCase):
    """Icons, covers and figures render where they should, and nowhere else."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-art-test-")
        cls.saved = {k: os.environ.get(k) for k in ("LEARN_TRACKS_DIR", "LEARN_WORK_DIR")}
        os.environ["LEARN_TRACKS_DIR"] = cls.tmp
        os.environ["LEARN_WORK_DIR"] = os.path.join(cls.tmp, "work-none")
        for name, art in (("arty", True), ("bare", False)):
            root = os.path.join(cls.tmp, name)
            write(os.path.join(root, "track.py"), SAMPLE_TRACK)
            write(os.path.join(root, "lessons", "01-basics", "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
            write(os.path.join(root, "lessons", "02-more", "README.md"), "---\nid: 02\ntitle: More\n---\n")
            write(os.path.join(root, "lessons", "01-basics", "01.01-one.md"), "---\nid: 01.01\ntitle: One\n---\n\n# 01.01 One\n\nProse here.\n")
            write(os.path.join(root, "lessons", "02-more", "02.01-two.md"), "---\nid: 02.01\ntitle: Two\n---\n\n# 02.01 Two\n\nOther prose.\n")
            if art:
                write(os.path.join(root, "art.svg"), SVG_TRACK_ART)
                write(os.path.join(root, "icon.svg"), SVG_ICON)
                write(os.path.join(root, "src", "icon.svg"), SVG_ICON)      # a file of the system that happens to share the name
                write(os.path.join(root, "lessons", "01-basics", "icon.svg"), SVG_ICON)
                write(os.path.join(root, "lessons", "01-basics", "cover.svg"), SVG_COVER)
                write(os.path.join(root, "lessons", "01-basics", "01.01-fig.svg"), SVG_FIGURE)
                write(os.path.join(root, "lessons", "02-more", "cover.svg"), SVG_EVIL)
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.old = (core.TRACKS_DIR, workspace.WORK_DIR)
        core.TRACKS_DIR = cls.tmp
        workspace.WORK_DIR = os.path.join(cls.tmp, "work-none")
        cls.old_outlines = outlines_mod.OUTLINES_DIR
        outlines_mod.OUTLINES_DIR = os.path.join(cls.tmp, "no-outlines")
        from harness.web.server import WebServer
        cls.srv = WebServer(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.core.TRACKS_DIR, cls.ws.WORK_DIR = cls.old
        outlines_mod.OUTLINES_DIR = cls.old_outlines
        restore_env(cls.saved)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def get(self, path):
        return http_req(self.port, "GET", path)[1]

    def test_icon_in_sidebar_before_title_and_in_breadcrumb(self):
        page = self.get("/t/arty/01.01")
        side = page[page.index('<aside class="side"'):page.index("</aside>")]
        first = side[side.index('<details class="mod"'):]
        self.assertLess(first.index('class="mn"'), first.index('class="mod-ic"'))       # the number stays, the icon follows
        self.assertLess(first.index('class="mod-ic"'), first.index('class="mt"'))
        self.assertIn('class="icon-circle"', side)
        crumb = page[page.index('class="crumb-line"'):page.index("</p>", page.index('class="crumb-line"'))]
        self.assertIn('class="cl-mod"', crumb)
        self.assertIn('class="mod-ic"', crumb)
        self.assertLess(crumb.index('class="mod-ic"'), crumb.index("Module 01"))
        # module 02 has no icon, so its sidebar row has no icon element
        self.assertEqual(side.count('class="mod-ic"'), 1)

    def test_cover_on_the_track_overview_above_the_units(self):
        page = self.get("/t/arty")
        sec = page[page.index('id="m-01"'):page.index('id="m-02"')]
        self.assertIn('<div class="art cover"><svg', sec)
        self.assertIn("COVER-LABEL", sec)
        self.assertLess(sec.index("art cover"), sec.index("unit-grid"))
        self.assertGreater(sec.index("art cover"), sec.index("<h2>"))
        self.assertIn('class="t mono"', sec)

    def test_hostile_cover_is_sanitized_in_the_page(self):
        sec = self.get("/t/arty")
        sec = sec[sec.index('id="m-02"'):sec.index("</main>")]
        sec = sec[sec.index('<div class="art cover">'):sec.index("</svg></div>")]
        self.assertIn("art cover", sec)
        for bad in ("<script", "alert(", "<style", "foreignObject", "onload", "onclick", "href=", "evil.example", "<image"):
            self.assertNotIn(bad, sec, bad)

    def test_lesson_figure_sits_under_goal_after_the_intro(self):
        page = self.get("/t/arty/01.01")
        goal = page[page.index('id="step-goal"'):]
        self.assertIn('<figure class="art fig"><svg', goal)
        self.assertLess(goal.index("Prose here."), goal.index("FIGURE-LABEL"))
        self.assertNotIn("FIGURE-LABEL", self.get("/t/arty/02.01"))   # figures belong to their own lesson

    def test_track_art_leads_its_home_card_sanitized(self):
        home = self.get("/")
        card = home[home.index('<a class="grid-card track-card" href="/t/arty">'):]
        card = card[:card.index("</a>")]
        self.assertTrue(card.split(">", 1)[1].lstrip().startswith('<span class="card-art art"><svg'))   # the picture comes first
        self.assertIn("TRACK-ART-LABEL", card)
        self.assertIn('pathLength="1"', card)                                    # the draw-in motion survives
        picture = card[card.index('<span class="card-art art">'):card.index('<span class="card-body">')]
        for bad in ("<script", "onload", "onclick", "style=", "evil.example", "<a ", "href"):
            self.assertNotIn(bad, picture, bad)
        self.assertLess(card.index("card-art"), card.index('<span class="card-body">'))
        self.assertIn('<span class="card-meta"><span class="pill">2 lessons</span></span>', card)

    def test_a_track_without_art_gets_the_default_picture(self):
        from harness.web import art
        home = self.get("/")
        card = home[home.index('<a class="grid-card track-card" href="/t/bare">'):]
        card = card[:card.index("</a>")]
        self.assertIn('<span class="card-art art"><svg', card)
        self.assertIn("M150 128l-10 8 10 8", card)                               # DEFAULT_ART's brackets
        self.assertNotIn("TRACK-ART-LABEL", card)
        self.assertEqual(art.track_art(self.core.Track("bare"), "icon"), "")    # no icon: the switcher keeps its default

    def test_track_icon_in_the_top_bar_switcher(self):
        page = self.get("/t/arty/01.01")
        pill = page[page.index('<a class="track-pill"'):page.index("</a>", page.index('<a class="track-pill"'))]
        self.assertIn('<span class="mod-ic tp-ic"><svg', pill)
        self.assertIn("icon-circle", pill)
        pill = self.get("/t/bare")
        pill = pill[pill.index('<a class="track-pill"'):pill.index("</a>", pill.index('<a class="track-pill"'))]
        self.assertIn('<svg class="ic" viewBox="0 0 16 16" width="16" height="16"', pill)   # the neutral grid
        self.assertNotIn("tp-ic", pill)

    def test_track_art_is_not_part_of_the_system(self):
        page = self.get("/t/arty/01.01")
        drawer = page[page.index('<div class="drawer"'):]
        self.assertNotIn('data-path="art.svg"', drawer)
        self.assertNotIn('data-path="icon.svg"', drawer)
        self.assertIn('data-path="src/icon.svg"', drawer)                        # only the top-level pair is left out
        self.assertEqual(http_req(self.port, "GET", "/api/file/arty?path=art.svg")[0], 404)
        dest = os.path.join(self.tmp, "copy-of-arty")
        self.ws.copy_track(self.core.Track("arty"), dest)
        self.assertFalse(os.path.exists(os.path.join(dest, "art.svg")) or os.path.exists(os.path.join(dest, "icon.svg")))
        self.assertTrue(os.path.exists(os.path.join(dest, "src", "icon.svg")))
        self.assertNotIn("art.svg", self.ws.missing_files(self.core.Track("arty"), dest))

    def test_missing_art_renders_nothing(self):
        for path in ("/t/bare", "/t/bare/01.01", "/t/bare/02.01"):
            page = self.get(path)
            for marker in ('class="mod-ic"', 'class="art', "<figure", "cl-mod\"><span class=\"mod-ic"):
                self.assertNotIn(marker, page, f"{marker} on {path}")
        self.assertEqual(self.get("/t/arty/02.01").count('class="art fig"'), 0)

    def test_css_defines_the_cover_classes(self):
        css = self.get("/static/app.css")
        for cls in (".art .s", ".art .m", ".art .a", ".art .af", ".art .f", ".art .fs", ".art .fa", ".art .t", ".art .tm", ".art .ta", ".art .mono"):
            self.assertIn(cls + " {", css)
        self.assertIn("var(--accent-soft)", css)


FIG_DOC = """---
id: 01.01
title: Figures
---

# 01.01 Figures

The intro.

![Intro caption with `code`](figures/01.01-intro.svg)

## What you are building

Goal prose.
![Goal caption](figures/01.01-goal.svg)

## Run it

Run prose.

![Run caption](figures/01.01-run.svg)

```
![Fenced caption](figures/01.01-fenced.svg)
```

## How it works

Why prose.

![Hostile caption](figures/01.01-evil.svg)

![Up caption](figures/../secret.svg)
![Deep caption](figures/../../track.py)
![Abs caption](/etc/passwd)
![Url caption](https://evil.example/x.svg)
![Sub caption](figures/sub/01.01-sub.svg)
![Bare caption](01.01-goal.svg)
![Link caption](figures/01.01-link.svg)

## Break it

![Missing caption](figures/01.01-nope.svg)

![Break caption](figures/01.01-break.svg)
"""


def fig_svg(label):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 200" width="640">'
            f'<rect x="1" y="1" width="50" height="20" class="s fs"/><text x="5" y="15" class="t mono">{label}</text></svg>')


class InlineFigureTests(unittest.TestCase):
    """![Caption](figures/x.svg) on a line of its own renders a sanitized figure in its step."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-fig-test-")
        cls.saved = {k: os.environ.get(k) for k in ("LEARN_TRACKS_DIR", "LEARN_WORK_DIR")}
        os.environ["LEARN_TRACKS_DIR"] = cls.tmp
        os.environ["LEARN_WORK_DIR"] = os.path.join(cls.tmp, "work-none")
        root = os.path.join(cls.tmp, "figgy")
        mod = os.path.join(root, "lessons", "01-basics")
        cls.doc = os.path.join(mod, "01.01-figures.md")
        write(os.path.join(root, "track.py"), SAMPLE_TRACK)
        write(os.path.join(mod, "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
        write(cls.doc, FIG_DOC)
        # not a lesson ./learn verify holds to its text: check reports only its figures here
        write(os.path.join(root, "lessons", "verify-pending.txt"), "01.01\n")
        for name in ("intro", "goal", "run", "break", "fenced"):
            write(os.path.join(mod, "figures", f"01.01-{name}.svg"), fig_svg(name.upper() + "-FIG"))
        write(os.path.join(mod, "figures", "01.01-evil.svg"), SVG_EVIL.replace("<text", '<text class="t">EVIL-FIG</text><text'))
        write(os.path.join(mod, "figures", "sub", "01.01-sub.svg"), fig_svg("SUB-FIG"))
        write(os.path.join(mod, "secret.svg"), fig_svg("SECRET-FIG"))
        write(os.path.join(cls.tmp, "outside.svg"), fig_svg("LINKED-FIG"))
        try:
            os.symlink(os.path.join(cls.tmp, "outside.svg"), os.path.join(mod, "figures", "01.01-link.svg"))
        except OSError:
            pass
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.old = (core.TRACKS_DIR, workspace.WORK_DIR)
        core.TRACKS_DIR = cls.tmp
        workspace.WORK_DIR = os.path.join(cls.tmp, "work-none")
        cls.old_outlines = outlines_mod.OUTLINES_DIR
        outlines_mod.OUTLINES_DIR = os.path.join(cls.tmp, "no-outlines")
        from harness.web.server import WebServer
        cls.srv = WebServer(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.page = http_req(cls.port, "GET", "/t/figgy/01.01")[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.core.TRACKS_DIR, cls.ws.WORK_DIR = cls.old
        outlines_mod.OUTLINES_DIR = cls.old_outlines
        restore_env(cls.saved)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def step(self, sid):
        page = self.page
        start = page.index(f'id="step-{sid}"')
        end = page.find('<section class="sec step', start + 1)
        return page[start:end if end != -1 else len(page)]

    def test_each_figure_renders_inside_its_own_step(self):
        for sid, label, cap in (("goal", "INTRO-FIG", "Intro caption"), ("goal", "GOAL-FIG", "Goal caption"),
                                ("run", "RUN-FIG", "Run caption"), ("break", "BREAK-FIG", "Break caption")):
            sec = self.step(sid)
            self.assertIn(label, sec, sid)
            fig = sec[sec.rindex('<figure class="art fig">', 0, sec.index(label)):]
            fig = fig[:fig.index("</figure>")]
            self.assertTrue(fig.startswith('<figure class="art fig"><svg '), sid)
            self.assertIn(f"<figcaption>{cap}", fig)
            self.assertNotIn('width="640"', fig)          # CSS sizes it
        self.assertLess(self.step("goal").index("Goal prose."), self.step("goal").index("GOAL-FIG"))
        self.assertIn("<figcaption>Intro caption with <code>code</code></figcaption>", self.page)
        self.assertEqual(self.page.count("<figure"), 5)

    def test_figure_svg_is_sanitized(self):
        sec = self.step("why")
        self.assertIn("EVIL-FIG", sec)
        self.assertIn("<figcaption>Hostile caption</figcaption>", sec)
        for bad in ("<script", "alert(", "<style", "foreignObject", "onload", "onclick", "href=", "evil.example", "<image"):
            self.assertNotIn(bad, sec, bad)

    def test_paths_outside_the_lessons_figures_dir_are_refused(self):
        for label in ("SECRET-FIG", "SUB-FIG", "LINKED-FIG", "FENCED-FIG", "import Fail"):
            self.assertNotIn(label, self.page, label)
        for cap in ("Up caption", "Deep caption", "Abs caption", "Url caption", "Sub caption", "Bare caption", "Link caption"):
            self.assertNotIn(cap, self.page, cap)        # nothing at all: no figure, no caption, no link
        self.assertNotIn("passwd", self.page)
        self.assertIn("![Fenced caption](figures/01.01-fenced.svg)", self.step("run"))   # code stays code
        from harness.web import art
        for src in ("figures/../secret.svg", "figures/../../track.py", "/etc/passwd", "https://e.com/x.svg",
                    "figures/sub/x.svg", "figures/.hidden.svg", "figures\\x.svg", "figures/x.SVG", "x.svg", ""):
            self.assertIsNone(art.figure_path(self.doc, src), src)
        self.assertTrue(art.figure_path(self.doc, "figures/01.01-goal.svg").endswith("/figures/01.01-goal.svg"))

    def test_missing_file_renders_nothing(self):
        sec = self.step("break")
        self.assertNotIn("Missing caption", sec)
        self.assertNotIn("01.01-nope", sec)
        self.assertEqual(sec.count("<figure"), 1)

    def test_renderer_without_a_figure_callback_renders_nothing(self):
        from harness.web.markdown import render
        out = render("before\n![Cap](figures/a.svg)\nafter")
        self.assertEqual(out, "<p>before</p>\n<p>after</p>")
        out = render("![Cap](figures/a.svg)", figure=lambda src: "<svg>X</svg>" if src == "figures/a.svg" else "")
        self.assertEqual(out, '<figure class="art fig"><svg>X</svg><figcaption>Cap</figcaption></figure>')
        self.assertEqual(render("![<b>](figures/a.svg)", figure=lambda s: "<svg></svg>"),
                         '<figure class="art fig"><svg></svg><figcaption>&lt;b&gt;</figcaption></figure>')
        self.assertNotIn("<figure", render("text ![Cap](figures/a.svg) inline", figure=lambda s: "<svg/>"))   # own line only

    def test_check_reports_figures_that_do_not_exist(self):
        import contextlib
        import io
        from harness import cli
        old_root = cli.ROOT
        cli.ROOT = self.tmp
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = cli.cmd_check([])
        finally:
            cli.ROOT = old_root
        out = buf.getvalue()
        self.assertEqual(code, 1)
        rel = os.path.join("figgy", "lessons", "01-basics", "01.01-figures.md")
        self.assertIn(f"{rel}:43: figure figures/01.01-nope.svg does not exist", out)
        self.assertIn("figure figures/../secret.svg is not a figures/<name>.svg", out)
        self.assertNotIn("figure figures/01.01-goal.svg", out)
        self.assertNotIn("01.01-fenced.svg", out)
        self.assertNotIn("01.01-evil.svg", out)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-web-test-")
        cls.old = {k: os.environ.get(k) for k in ("LEARN_TRACKS_DIR", "LEARN_WORK_DIR")}
        os.environ["LEARN_TRACKS_DIR"] = cls.tmp
        os.environ["LEARN_WORK_DIR"] = os.path.join(cls.tmp, "work-none")
        root = os.path.join(cls.tmp, "sample")
        write(os.path.join(root, "track.py"), SAMPLE_TRACK)
        write(os.path.join(root, "src", "hello.txt"), "line one\nline <two>\n")
        write(os.path.join(root, "lessons", "01-basics", "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
        write(os.path.join(root, "lessons", "01-basics", "01.01-say-hello.md"), DOC_ONE)
        write(os.path.join(root, "tests", "0101_say_hello.py"), TEST_PASS)
        write(os.path.join(root, "tests", "0102_second.py"), TEST_FAIL)
        # harness.core reads the env at import time, so point it (and workspace) explicitly
        from harness import core, workspace
        cls.core, cls.ws, cls.saved = core, workspace, (core.TRACKS_DIR, workspace.WORK_DIR)
        core.TRACKS_DIR = cls.tmp
        workspace.WORK_DIR = os.path.join(cls.tmp, "work-none")
        cls.old_outlines = outlines_mod.OUTLINES_DIR
        outlines_mod.OUTLINES_DIR = os.path.join(cls.tmp, "no-outlines")
        from harness.web.server import WebServer
        cls.srv = WebServer(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.core.TRACKS_DIR, cls.ws.WORK_DIR = cls.saved
        outlines_mod.OUTLINES_DIR = cls.old_outlines
        restore_env(cls.old)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def req(self, method, path, headers=None, body=None):
        return http_req(self.port, method, path, headers, body)

    def test_home(self):
        status, body = self.req("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Code first,", body)
        self.assertIn("theory second.", body)
        self.assertIn("Sample &lt;b&gt;track&lt;/b&gt;", body)
        self.assertNotIn("<b>track</b>", body)
        self.assertIn("2 lessons", body)

    def test_track_map(self):
        status, body = self.req("GET", "/t/sample")
        self.assertEqual(status, 200)
        self.assertIn("Basics", body)
        self.assertIn("#m-01", body)
        self.assertIn("Say hello", body)
        self.assertIn("Second lesson, no doc", body)  # titled from the test docstring

    def test_lesson_page_code_before_theory(self):
        status, body = self.req("GET", "/t/sample/01.01")
        self.assertEqual(status, 200)
        self.assertLess(body.index("code-block-shell"), body.index('id="step-run"'))   # the code is under Goal, before Run
        self.assertIn("src/hello.txt", body)
        self.assertIn("line &lt;two&gt;", body)
        self.assertNotIn("line <two>", body)
        self.assertIn("Not in the track yet: src/missing.txt", body)
        self.assertNotIn("<script>alert(1)", body)
        self.assertIn('href="/t/sample/01.02"', body)  # relative lesson link and pager

    def test_no_code_to_build(self):
        status, body = self.req("GET", "/t/sample/01.02")
        self.assertEqual(status, 200)
        self.assertIn("not written yet", body)
        self.assertNotIn('class="sec build"', body)   # no empty Code section
        self.assertNotIn("this one fails on purpose", body)  # the test source is never shown
        self.assertIn("Previous lesson", body)

    def test_nothing_about_tests_is_shown(self):
        for path in ("/", "/t/sample", "/t/sample/01.01", "/t/sample/01.02"):
            body = self.req("GET", path)[1]
            for word in ("Run test", "PASS", "FAIL", "passing", "learn test", "never run", "results"):
                self.assertNotIn(word, body, f"{word!r} on {path}")
        css_js = self.req("GET", "/static/app.js")[1]
        self.assertNotIn("results", css_js)

    def test_static_assets_and_fonts(self):
        status, css = self.req("GET", "/static/app.css")
        self.assertEqual(status, 200)
        self.assertIn("Geist", css)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", "/static/fonts/Figtree.woff2")
        r = c.getresponse()
        self.assertEqual((r.status, r.getheader("Content-Type")), (200, "font/woff2"))
        self.assertEqual(r.read()[:4], b"wOF2")
        c.close()
        self.assertEqual(self.req("GET", "/static/fonts/LICENSE-OFL.txt")[0], 200)
        for path in ("/static/fonts/..%2f..%2fserver.py", "/static/server.py", "/static/fonts/nope.woff2"):
            self.assertEqual(self.req("GET", path)[0], 404, path)

    def test_unknown_pages_and_old_test_endpoints(self):
        self.assertEqual(self.req("GET", "/t/nope")[0], 404)
        self.assertEqual(self.req("GET", "/t/sample/09.09")[0], 404)
        self.assertEqual(self.req("GET", "/t/sample/..%2f..")[0], 404)
        self.assertEqual(self.req("GET", "/api/results/sample")[0], 404)  # results are not exposed
        self.assertEqual(self.req("POST", "/api/run/sample/01.01")[0], 404)  # tests cannot be run from the UI

    def test_refuses_foreign_host_and_origin(self):
        self.assertEqual(self.req("GET", "/", {"Host": "evil.example"})[0], 403)
        self.assertEqual(self.req("POST", "/api/start/sample", {"Origin": "http://evil.example"})[0], 403)

    def test_a_track_without_run_hooks_shows_no_run_command(self):
        page = self.req("GET", "/t/sample/01.01")[1]
        self.assertNotIn("learn run", page)

def http_req(port, method, path, headers=None, body=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse()
    text = r.read().decode("utf-8")
    c.close()
    return r.status, text


def plain(markup):
    """Visible text of an HTML fragment: tags removed, entities decoded."""
    import html as _html
    import re as _re
    return _html.unescape(_re.sub(r"<[^>]+>", "", markup))


def restore_env(saved):
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


FORGE_A = """int x;
    // @build 01.01 adder
    // Return the sum of two ints.
    //
    // Overflow is <b>not</b> handled; see `limits`.
    // @stub panic("01.01: adder custom stub");
    int sum = a + b;
    // SOLUTION-HINT: mind the order of the operands
    return sum;
    // @end
"""

FORGE_B = """// @build 01.02 doubler
// Return twice the argument.
return 2 * a;
// @end
"""


FORGE_DOC_ONE = """---
id: 01.01
title: Adder
labels: with code
---

# 01.01 Adder

First intro paragraph, see [the next lesson](01.02-doubler.md).

Second intro paragraph.

## What you are building

BUILDING-TEXT about `add`.

## Run it

RUN-TEXT expected output:

```
## not a heading, only a line in a fence
hello
```

## How it works

HOW-TEXT here.

## An unexpected heading

ODD-TEXT must not be lost.

## Decide the boundary

BOUNDARY-TEXT here.

## Break it

BREAK-TEXT here.

## Read more in OSTEP

OSTEP-TEXT chapter links.

Related: 01.02 Doubler
"""


FORGE_DOC_NEW = """---
id: 01.03
title: Tripler
labels: with code
---

# 01.03 Tripler

NEW-INTRO paragraph.

## The idea

IDEA-TEXT about tripling.

## Run it

NEW-RUN-TEXT.

## How it works

NEW-HOW-TEXT.

## Break it

NEW-BREAK-TEXT.

## Go deeper

NEW-DEEPER-TEXT.
"""

# Words of the old exercise framing: none may appear anywhere on the site.
EXERCISE_WORDS = ("Not written yet", "not written yet", "Your code", "Show a hint", "Show solution", "Reference solution",
                  "Start building", "Continue", "Finish this lesson", "Use the solution", "Back to your lesson",
                  "Start this extension", "workspace", "Workspace", " built", "you are here", "fill the", "stub", "@stub",
                  "data-start", "data-continue", "data-solution", "data-extend", "data-live", "/api/start", "/api/next",
                  "/api/state", "/api/extend", "build it yourself")


class LessonTests(unittest.TestCase):
    """The lesson page as a lesson: the steps around the reference code, plain navigation, no workspace."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-forge-test-")
        cls.work = os.path.join(cls.tmp, "work")
        cls.saved = {k: os.environ.get(k) for k in ("LEARN_TRACKS_DIR", "LEARN_WORK_DIR")}
        os.environ["LEARN_TRACKS_DIR"] = os.path.join(cls.tmp, "tracks")
        os.environ["LEARN_WORK_DIR"] = cls.work
        cls.root = os.path.join(cls.tmp, "tracks", "forge")
        write(os.path.join(cls.root, "track.py"), RUNNABLE)
        write(os.path.join(cls.root, "src", "a.c"), FORGE_A)
        write(os.path.join(cls.root, "src", "b.c"), FORGE_B)
        write(os.path.join(cls.root, "lessons", "01-basics", "README.md"), "---\nid: 01\ntitle: Basics\n---\n")
        write(os.path.join(cls.root, "lessons", "01-basics", "01.01-adder.md"), FORGE_DOC_ONE)
        write(os.path.join(cls.root, "lessons", "01-basics", "01.02-doubler.md"),
              "---\nid: 01.02\ntitle: Doubler\n---\n\n# 01.02 Doubler\n\nMore theory with no known headings.\n\n## Odd\n\nOdd body.\n")
        write(os.path.join(cls.root, "lessons", "01-basics", "01.03-tripler.md"), FORGE_DOC_NEW)
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.old = (core.TRACKS_DIR, workspace.WORK_DIR)
        core.TRACKS_DIR = os.path.join(cls.tmp, "tracks")
        workspace.WORK_DIR = cls.work
        cls.old_outlines = outlines_mod.OUTLINES_DIR
        outlines_mod.OUTLINES_DIR = os.path.join(cls.tmp, "no-outlines")
        from harness.web.server import WebServer
        cls.srv = WebServer(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.core.TRACKS_DIR, cls.ws.WORK_DIR = cls.old
        outlines_mod.OUTLINES_DIR = cls.old_outlines
        restore_env(cls.saved)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def req(self, method, path, headers=None, body=None):
        return http_req(self.port, method, path, headers, body)

    @staticmethod
    def steps(page):
        """{step id: html of that step's section}, in page order."""
        out = {}
        for m in re.finditer(r'<section class="sec step step-(\w+)" id="step-\1"', page):
            end = page.find('<section class="sec step', m.end())
            end = len(page) if end < 0 else end
            out[m.group(1)] = page[m.start():end]
        return out

    @staticmethod
    def bar(page):
        return page[page.index('<nav class="lesson-bar"'):page.index("</nav>", page.index('<nav class="lesson-bar"'))]

    # ---- the steps and where each part of the doc goes

    def test_steps_in_order_with_the_old_headings_mapped_into_them(self):
        page = self.req("GET", "/t/forge/01.01")[1]
        steps = self.steps(page)
        self.assertEqual(list(steps), ["goal", "code", "run", "why", "break", "deeper"])
        for sid, title in (("goal", "Goal"), ("code", "The code"), ("run", "Run it"), ("why", "How it works"),
                           ("break", "Break it"), ("deeper", "Go deeper")):
            self.assertIn(f"<span>{title}</span></h2>", steps[sid])
        goal = plain(steps["goal"])
        self.assertIn("First intro paragraph", goal)
        self.assertIn("Second intro paragraph", goal)
        self.assertIn("BUILDING-TEXT", goal)                                                # "What you are building"
        self.assertLess(goal.index("Second intro paragraph"), goal.index("BUILDING-TEXT"))
        self.assertIn("RUN-TEXT", plain(steps["run"]))
        self.assertIn("## not a heading, only a line in a fence", plain(steps["run"]))   # a fence is not split
        why = plain(steps["why"])
        for text in ("HOW-TEXT", "ODD-TEXT must not be lost", "BOUNDARY-TEXT"):
            self.assertIn(text, why)
        self.assertLess(why.index("HOW-TEXT"), why.index("ODD-TEXT"))                      # doc order is kept
        self.assertLess(why.index("ODD-TEXT"), why.index("BOUNDARY-TEXT"))
        self.assertIn("<h3", steps["why"].split("ODD-TEXT")[0].split("HOW-TEXT")[1])       # other headings stay as subheadings
        self.assertNotIn(">How it works</h3>", steps["why"])                                # the step's own title is not repeated
        self.assertIn("BREAK-TEXT", plain(steps["break"]))
        deeper = plain(steps["deeper"])
        self.assertIn("OSTEP-TEXT", deeper)
        self.assertIn("Related: 01.02 Doubler", deeper)
        for text in ("BUILDING-TEXT", "RUN-TEXT", "HOW-TEXT", "BREAK-TEXT", "OSTEP-TEXT", "Related:"):   # each lands once
            self.assertEqual(plain(page).count(text), 1, text)
        self.assertIn('href="/t/forge/01.02"', steps["goal"])                               # lesson links still resolve

    def test_the_new_headings_map_the_same_way(self):
        steps = self.steps(self.req("GET", "/t/forge/01.03")[1])
        self.assertEqual(list(steps), ["goal", "run", "why", "break", "deeper"])            # no regions: no code step
        goal = plain(steps["goal"])
        self.assertIn("NEW-INTRO paragraph", goal)
        self.assertIn("IDEA-TEXT about tripling", goal)                                     # "The idea" is the Goal
        self.assertLess(goal.index("NEW-INTRO"), goal.index("IDEA-TEXT"))
        self.assertNotIn("The idea", goal)
        for sid, text in (("run", "NEW-RUN-TEXT"), ("why", "NEW-HOW-TEXT"), ("break", "NEW-BREAK-TEXT"), ("deeper", "NEW-DEEPER-TEXT")):
            self.assertIn(text, plain(steps[sid]), sid)
        self.assertNotIn("<h3", steps["why"])

    def test_a_doc_without_known_headings_renders_whole_under_goal(self):
        steps = self.steps(self.req("GET", "/t/forge/01.02")[1])
        self.assertEqual(list(steps)[:2], ["goal", "code"])
        self.assertNotIn("why", steps)
        goal = plain(steps["goal"])
        self.assertIn("More theory with no known headings.", goal)
        self.assertIn("Odd body.", goal)

    def test_rail_is_the_list_of_steps_and_nothing_else(self):
        page = self.req("GET", "/t/forge/01.01")[1]
        start = page.index('<aside class="lesson-rail">')
        rail = page[start:page.index("</aside>", start)]
        self.assertEqual(re.findall(r'href="#step-(\w+)"', rail), ["goal", "code", "run", "why", "break", "deeper"])
        self.assertEqual(rail.count("<a "), 6)
        self.assertNotIn("<button", rail)
        self.assertNotIn("path-done", rail)

    # ---- the code step: the reference, in full

    def test_the_code_step_shows_a_new_file_whole_as_it_stands(self):
        code = self.steps(self.req("GET", "/t/forge/01.01")[1])["code"]
        self.assertIn('<h3 class="region-title">a.c<span class="tag">new file</span></h3>', code)
        absolute = os.path.join(self.root, "src", "a.c")
        target = f"{absolute}:1"                                                           # the first line shown
        self.assertIn(f'<code class="where-path">{target}</code>', code)
        self.assertIn(f'data-copy="{target}"', code)                                       # Copy copies what is shown
        self.assertIn(f'href="vscode://file/{urllib.parse.quote(absolute, safe="/")}:1"', code)
        self.assertIn("Open in editor", code)
        text = plain(code)
        for line in ("int x;", "int sum = a + b;", "// SOLUTION-HINT: mind the order of the operands", "return sum;"):
            self.assertIn(line, text)                                                       # every line of the code
        gutter = re.findall(r'<span class="ln">(?:<button[^>]*>.*?</button>)?(\d*)</span>', code, re.S)
        self.assertEqual(gutter, ["1", "7", "8", "9"])                                      # its real line numbers
        self.assertIn('<span class="tk-t">int</span>', code)                                # highlighted
        self.assertNotIn("<details", code)                                                 # nothing behind a toggle
        for word in ("Return the sum", "Overflow is", "region-prose", "custom stub", "@stub", "@build", "@end",
                     "Not written", "Your code", "hint", "solution", "Solution"):
            self.assertNotIn(word, code.replace("SOLUTION-HINT", ""), word)                 # no orders to a learner
        self.assertIn("return 2 * a;", plain(self.steps(self.req("GET", "/t/forge/01.02")[1])["code"]))

    def test_no_exercise_or_workspace_wording_anywhere(self):
        for path in ("/", "/t/forge", "/t/forge/01.01", "/t/forge/01.02", "/t/forge/01.03"):
            page = self.req("GET", path)[1]
            for word in EXERCISE_WORDS:
                self.assertNotIn(word, page, f"{word!r} on {path}")
        js = self.req("GET", "/static/app.js")[1]
        for word in ("/api/start", "/api/next", "/api/state", "/api/extend", "setInterval", "data-start", "data-solution", "confirm("):
            self.assertNotIn(word, js, word)
        css = self.req("GET", "/static/app.css")[1]
        for rule in (".next-action", ".linkbtn", ".help ", ".built", ".here ", ".path-done", ".step-state", ".start-wrap", ".mk.done"):
            self.assertNotIn(rule, css, rule)

    def test_a_workspace_on_disk_changes_nothing_on_the_site(self):
        self.ws.start(self.core.Track("forge"))                                             # cuts 01.01 in work/forge
        with open(os.path.join(self.work, "forge", "src", "a.c")) as f:
            self.assertIn("custom stub", f.read())
        page = self.req("GET", "/t/forge/01.01")[1]
        code = self.steps(page)["code"]
        self.assertIn("int sum = a + b;", plain(code))                                     # still the reference
        self.assertNotIn("custom stub", page)
        self.assertNotIn(self.work, page)                                                  # links point into tracks/
        self.assertIn(os.path.join(self.root, "src", "a.c"), code)
        for word in EXERCISE_WORDS:
            self.assertNotIn(word, page, word)
        j = json.loads(self.req("GET", "/api/file/forge?path=src/a.c&lesson=01.01")[1])
        rows = re.findall(r'<span class="ln">(\d+)</span><span class="tx">(.*?)</span></div>', j["html"])
        self.assertEqual([plain(t).strip() for _, t in rows],                              # the track's file, not the workspace's
                         ["int x;", "int sum = a + b;", "// SOLUTION-HINT: mind the order of the operands", "return sum;"])

    def test_the_workspace_endpoints_are_gone(self):
        for method, path in (("POST", "/api/start/forge"), ("POST", "/api/next/forge"), ("POST", "/api/next/forge?use_solution=1"),
                             ("POST", "/api/extend/forge/02"), ("POST", "/api/extend/forge/02?fill_core=1"),
                             ("GET", "/api/state/forge"), ("GET", "/api/state/nope"), ("POST", "/api/start/nope")):
            self.assertEqual(self.req(method, path)[0], 404, f"{method} {path}")
        self.assertFalse(os.path.exists(self.work))                                         # nothing was created
        self.assertEqual(self.req("POST", "/api/start/forge", {"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.req("POST", "/api/start/forge", {"Host": "evil.example"})[0], 403)
        from harness.web import server
        for name in ("workspace_action", "extend_action"):
            self.assertFalse(hasattr(server.Handler, name), name)
        self.assertFalse(hasattr(self.srv, "ws_lock"))

    # ---- run: the doc's Run it, and nothing the site adds to it

    def test_run_step_is_only_the_docs_run_it(self):
        page = self.req("GET", "/t/forge/01.01")[1]
        run = self.steps(page)["run"]
        body = plain(run.split("</h2>", 1)[1]).strip()
        self.assertTrue(body.startswith("RUN-TEXT"), body[:80])                           # right under the heading, the doc's text
        self.assertNotIn("learn run", page)                                              # no command line of the site's own
        self.assertNotIn("cmd-line", page)
        self.assertNotIn("data-copy", run)
        steps = self.steps(self.req("GET", "/t/forge/01.02")[1])                         # runnable, but no Run it in the doc
        self.assertNotIn("run", steps)
        self.assertNotIn('href="#step-run"', self.req("GET", "/t/forge/01.02")[1])

    # ---- navigation

    def test_the_bottom_bar_is_plain_navigation(self):
        bar = self.bar(self.req("GET", "/t/forge/01.01")[1])
        self.assertIn('<span class="round off">', bar)                                     # no previous lesson
        self.assertIn('<a class="bar-pill" href="/t/forge#m-01"><span>Basics</span><em>1/3</em></a>', bar)
        self.assertRegex(bar, r'<a class="btn primary" href="/t/forge/01.02" rel="next" title="01.02 Doubler"><span>Next</span>')
        self.assertEqual(bar.count("btn primary"), 1)
        bar = self.bar(self.req("GET", "/t/forge/01.03")[1])
        self.assertIn('href="/t/forge/01.02" aria-label="Previous lesson"', bar)
        self.assertIn("<em>3/3</em>", bar)
        self.assertNotIn("Next", bar)                                                      # the last lesson leads nowhere
        self.assertNotIn("<button", bar)

    def test_overview_and_home_start_with_the_first_lesson(self):
        for path in ("/", "/t/forge"):
            page = self.req("GET", path)[1]
            self.assertIn('href="/t/forge/01.01"><span>Start with 01.01 Adder</span>', page)
            self.assertNotIn("<button", page.split('<main class="main">')[1].split("</main>")[0])   # links only
        over = self.req("GET", "/t/forge")[1]
        self.assertIn("1 module &middot; 3 lessons", over)
        for cls in ("is-built", "is-here", "is-ahead", "unit-foot", 'class="bar"'):
            self.assertNotIn(cls, over)
            self.assertNotIn(cls, self.req("GET", "/")[1])
        self.assertIn('<span class="card-meta"><span class="pill">3 lessons</span></span>', self.req("GET", "/")[1])

    # ---- the files drawer

    def test_files_are_a_drawer_not_a_section(self):
        page = self.req("GET", "/t/forge/01.01")[1]
        self.assertNotIn('class="sec files-card"', page)
        self.assertNotIn('id="step-files"', page)
        main = page[page.index("<main"):page.index("</main>")]
        flow = main[:main.index('<div class="drawer"')]
        self.assertNotIn("ft-file", flow)                                # the tree is not in the page flow
        self.assertRegex(page, r'<button class="btn" type="button" data-drawer-open="files-drawer" aria-controls="files-drawer" aria-expanded="false" aria-haspopup="dialog">')
        hs = page.index('<header class="lesson-head">')
        head = page[hs:page.index("</header>", hs)]
        self.assertIn("data-drawer-open", head)                          # the button is in the header row
        drawer = page[page.index('<div class="drawer" id="files-drawer"'):]
        self.assertIn(" hidden ", drawer[:80])
        self.assertIn('role="dialog" aria-modal="true"', drawer)
        self.assertEqual(drawer.count("data-drawer-close"), 2)           # the scrim and the close button
        self.assertIn('data-path="src/a.c"', drawer)
        self.assertIn('data-files="/api/file/forge"', drawer)
        js = self.req("GET", "/static/app.js")[1]
        self.assertIn('"Escape"', js)                                    # closes on Escape
        self.assertIn("opener.focus()", js)                              # focus goes back to the button
        css = self.req("GET", "/static/app.css")[1]
        self.assertIn("width: 100vw", css)                               # full width on phones

    def test_every_run_route_and_the_panel_are_gone(self):
        for method, path in (("POST", "/api/run/forge"), ("POST", "/api/run/forge/input"), ("POST", "/api/run/forge/stop"),
                             ("POST", "/api/run/forge/01.01"), ("GET", "/api/run/forge"), ("POST", "/api/run/nope")):
            self.assertEqual(self.req(method, path, body="x" if method == "POST" else None)[0], 404, path)
        for path in ("/", "/t/forge", "/t/forge/01.01"):
            page = self.req("GET", path)[1]
            for word in ("data-sys", "data-console", "/api/run", "Output appears", "Stop</button>"):
                self.assertNotIn(word, page, f"{word!r} on {path}")
        self.assertNotIn("data-sys", self.req("GET", "/static/app.js")[1])
        self.assertNotIn(".console", self.req("GET", "/static/app.css")[1])


def region(lesson, title, code):
    return f"// @build {lesson} {title}\n// Instructions for {title}.\n{code}\n// @end\n"


class FilesTests(unittest.TestCase):
    """The Files card: the project tree, its markers, and the file endpoint and viewer."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-files-test-")
        cls.work = os.path.join(cls.tmp, "work")
        cls.saved = {k: os.environ.get(k) for k in ("LEARN_TRACKS_DIR", "LEARN_WORK_DIR")}
        os.environ["LEARN_TRACKS_DIR"] = os.path.join(cls.tmp, "tracks")
        os.environ["LEARN_WORK_DIR"] = cls.work
        cls.root = root = os.path.join(cls.tmp, "tracks", "atlas")
        write(os.path.join(root, "track.py"), RUNNABLE.replace('"Forge"', '"Atlas"') + '\nFILES_FROM = {"docs/*": "01.02"}\n')
        write(os.path.join(root, "src", "a.c"), "int a;\n" + region("01.01", "one", "int SECRET_ONE = 1;") + "int tail_a;\n")
        write(os.path.join(root, "src", "b.c"), region("01.02", "two", "int SECRET_TWO = 2;")
              + "int middle_b;\n" + region("01.03", "three b", "int SECRET_THREE_B = 3;"))
        write(os.path.join(root, "src", "c.c"), region("01.03", "three c", "int SECRET_THREE_C = 3;"))
        write(os.path.join(root, "src", "e.c"), region("01.01", "e one", "int E1;") + region("01.03", "e three", "int SECRET_E3;"))
        write(os.path.join(root, "docs", "notes.txt"), "plain <notes>\n")
        write(os.path.join(root, ".hidden"), "x")
        write(os.path.join(root, ".test-logs", "results.json"), "{}")
        write(os.path.join(root, ".learn.json"), "{}")
        write(os.path.join(root, "build-x", "out.o"), "x")
        write(os.path.join(root, "__pycache__", "z.pyc"), "x")
        write(os.path.join(root, "src", "bin.dat"), "ab\0cd")
        os.symlink("/etc/hosts", os.path.join(root, "src", "escape.txt"))
        for lid, name in (("01.01", "one"), ("01.02", "two"), ("01.03", "three")):
            write(os.path.join(root, "lessons", "01-m", f"{lid}-{name}.md"),
                  f"---\nid: {lid}\ntitle: {name.capitalize()}\n---\n\n# {lid} {name}\n\nText.\n")
        write(os.path.join(root, "lessons", "01-m", "README.md"), "---\nid: 01\ntitle: M\n---\n")
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.old = (core.TRACKS_DIR, workspace.WORK_DIR)
        core.TRACKS_DIR = os.path.join(cls.tmp, "tracks")
        workspace.WORK_DIR = cls.work
        cls.old_outlines = outlines_mod.OUTLINES_DIR
        outlines_mod.OUTLINES_DIR = os.path.join(cls.tmp, "no-outlines")
        from harness.web.server import WebServer
        cls.srv = WebServer(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.core.TRACKS_DIR, cls.ws.WORK_DIR = cls.old
        outlines_mod.OUTLINES_DIR = cls.old_outlines
        restore_env(cls.saved)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def req(self, method, path, headers=None, body=None):
        return http_req(self.port, method, path, headers, body)

    def file(self, path, lesson=None):
        q = "path=" + path + ("&lesson=" + lesson if lesson else "")
        status, body = self.req("GET", "/api/file/atlas?" + q)
        return status, json.loads(body)

    def paths_in(self, page):
        import re
        return re.findall(r'data-path="([^"]+)"', page)

    # ---- the tree

    def tree_paths(self, page):
        """The paths of the "All files" tree (the "This lesson" group lists some again above it)."""
        nav = page[page.index('<nav class="ft"'):page.index("</nav>", page.index('<nav class="ft"'))]
        return self.paths_in(nav.split('<p class="ft-head">All files</p>')[-1])

    def test_tree_lists_what_a_workspace_copy_keeps_and_nothing_else(self):
        page = self.req("GET", "/t/atlas/01.03")[1]
        self.assertEqual(self.tree_paths(page), ["docs/notes.txt", "src/a.c", "src/b.c", "src/bin.dat", "src/c.c", "src/e.c"])
        self.assertIn(">6 files</span>", page)
        for hidden in (".hidden", ".learn.json", ".test-logs", "build-x", "__pycache__", "track.py", "tests", "lessons", "escape.txt"):
            self.assertNotIn(f'data-path="{hidden}', page)
            self.assertNotIn(f">{hidden}<", page)

    def test_the_drawer_grows_lesson_by_lesson(self):
        def group(page):
            nav = page[page.index('<nav class="ft"'):]
            return self.paths_in(nav.split('<p class="ft-head">All files</p>')[0]) if "All files" in nav else []
        p1, p2, p3 = (self.req("GET", f"/t/atlas/01.0{n}")[1] for n in (1, 2, 3))
        self.assertEqual(self.tree_paths(p1), ["src/a.c", "src/bin.dat", "src/e.c"])         # b.c, c.c, notes come later
        self.assertIn(">3 files</span>", p1)
        self.assertEqual(group(p1), ["src/a.c", "src/e.c"])                                   # new, listed first
        self.assertEqual(self.tree_paths(p2), ["docs/notes.txt", "src/a.c", "src/b.c", "src/bin.dat", "src/e.c"])
        self.assertEqual(group(p2), ["docs/notes.txt", "src/b.c"])
        self.assertEqual(group(p3), ["src/c.c", "src/b.c", "src/e.c"])                       # new, then changed
        self.assertIn('data-open="src/c.c"', p3)
        self.assertNotIn("src/bin.dat", " ".join(group(p1)))                                   # unplaced: there, never new

    def test_the_tree_lives_in_the_drawer_after_the_steps(self):
        page = self.req("GET", "/t/atlas/01.02")[1]
        self.assertIn('<div class="drawer" id="files-drawer" hidden data-files="/api/file/atlas"', page)
        self.assertGreater(page.index('data-files="/api/file/atlas"'), page.index('id="step-code"'))
        self.assertNotIn('class="sec files-card"', page)

    def test_markers_are_new_changed_and_the_lesson_a_file_came_with(self):
        page = self.req("GET", "/t/atlas/01.03")[1]
        tree = page[page.index('<p class="ft-head">All files</p>'):]

        def button(path):
            i = tree.index(f'data-path="{path}"')
            return tree[i:tree.index("</button>", i)]
        self.assertIn('<span class="mk this">new</span>', button("src/c.c"))
        self.assertIn('<span class="mk this">changed</span>', button("src/b.c"))
        self.assertIn('<span class="mk this">changed</span>', button("src/e.c"))
        self.assertIn('<span class="mk ids">01.01</span>', button("src/a.c"))                 # the lesson it came with
        self.assertIn('<span class="mk ids">01.02</span>', button("docs/notes.txt"))
        self.assertNotIn("mk", button("src/bin.dat"))                                        # unplaced: no lesson to name
        self.assertIn("the lesson it came with", page)                                       # legend
        for gone in (">done<", "mk done", "lg-dim", "files you write", "builds it", "later"):
            self.assertNotIn(gone, page[page.index('<div class="drawer"'):])
        self.assertIn('<details class="ft-dir" open><summary>', page)                         # folders with this lesson's files open
        self.assertRegex(page, r'<details class="ft-dir"><summary>[^<]*<svg.*?</svg><span class="ft-name">docs/')

    def test_a_workspace_with_built_lessons_marks_nothing_done(self):
        self.ws.start(self.core.Track("atlas"))
        with open(os.path.join(self.work, "atlas", ".learn.json"), "w") as f:
            json.dump({"current": "01.02", "done": ["01.01"]}, f)
        page = self.req("GET", "/t/atlas/01.02")[1]
        self.assertNotIn("done", page[page.index('<div class="drawer"'):])

    def test_lesson_without_regions_still_shows_the_tree(self):
        write(os.path.join(self.root, "lessons", "01-m", "01.09-plain.md"), "---\nid: 01.09\ntitle: Plain\n---\n\nText.\n")
        try:
            page = self.req("GET", "/t/atlas/01.09")[1]
        finally:
            os.remove(os.path.join(self.root, "lessons", "01-m", "01.09-plain.md"))
        self.assertEqual(len(self.paths_in(page)), 6)
        self.assertNotIn("this lesson &middot;", page)
        self.assertIn('data-open=""', page)

    # ---- the file endpoint

    def test_file_endpoint_happy_path_and_escaping(self):
        status, j = self.file("docs/notes.txt")
        self.assertEqual(status, 200)
        self.assertIn("plain &lt;notes&gt;", j["html"])
        self.assertNotIn("<notes>", j["html"])
        self.assertEqual((j["path"], j["truncated"], j["binary"]), ("docs/notes.txt", False, False))
        self.assertIn('<span class="ln">1</span>', j["html"])
        self.assertEqual(self.file("src/bin.dat")[1]["binary"], True)

    def test_file_endpoint_rejects_bad_requests(self):
        for path in ("../tracks/atlas/track.py", "src/../track.py", "/etc/passwd", "%2fetc%2fpasswd", "src//a.c", "src%5Ca.c", "src/a.c%00", ".", ""):
            self.assertEqual(self.req("GET", "/api/file/atlas?path=" + path)[0], 400, path)
        for path in ("track.py", "src/missing.c", "src/escape.txt", ".hidden", ".learn.json", "lessons/01-m/01.01-one.md", "build-x/out.o", "src"):
            self.assertEqual(self.req("GET", "/api/file/atlas?path=" + path)[0], 404, path)
        self.assertEqual(self.req("GET", "/api/file/nope?path=src/a.c")[0], 404)
        self.assertEqual(self.req("GET", "/api/file/..%2f..?path=src/a.c")[0], 404)
        self.assertEqual(self.req("GET", "/api/file/atlas")[0], 400)
        self.assertEqual(self.req("GET", "/api/file/atlas?path=src/a.c&lesson=xx")[0], 400)
        self.assertEqual(self.req("GET", "/api/file/atlas?path=src/a.c", {"Host": "evil.example"})[0], 403)

    def test_file_endpoint_caps_size(self):
        big = os.path.join(self.root, "docs", "big.txt")
        write(big, "x" * (600 * 1024))
        try:
            status, j = self.file("docs/big.txt")
        finally:
            os.remove(big)
        self.assertEqual(status, 200)
        self.assertTrue(j["truncated"])
        self.assertLess(len(j["html"]), 700 * 1024)

    # ---- the viewer

    def rows(self, html):
        return [(int(n), plain(t)) for n, t in re.findall(r'<span class="ln">(\d+)</span><span class="tx">(.*?)</span></div>', html)]

    def test_viewer_shows_each_file_as_it_stands_at_the_lesson(self):
        j = self.file("src/b.c", "01.02")[1]
        self.assertEqual(self.rows(j["html"]), [(3, "int SECRET_TWO = 2;"), (5, "int middle_b;")])   # 01.03's code is not there yet
        self.assertEqual(re.findall(r'class="row band"><span class="ln">(\d+)<', j["html"]), ["3"])  # this lesson's own code
        self.assertEqual(j["first_band"], 0)
        j3 = self.file("src/b.c", "01.03")[1]
        self.assertEqual(self.rows(j3["html"]), [(3, "int SECRET_TWO = 2;"), (5, "int middle_b;"), (8, "int SECRET_THREE_B = 3;")])
        self.assertEqual(re.findall(r'class="row band"><span class="ln">(\d+)<', j3["html"]), ["8"])
        j0 = self.file("src/b.c")[1]                                                          # no lesson: the end of the track
        self.assertEqual(self.rows(j0["html"]), self.rows(j3["html"]))
        self.assertIsNone(j0["first_band"])
        for html in (j["html"], j3["html"], j0["html"]):
            for gone in ("@build", "@end", "Instructions for"):                               # no markers, no orders
                self.assertNotIn(gone, plain(html))
        self.assertEqual(self.req("GET", "/api/file/atlas?path=src/c.c&lesson=01.02")[0], 404)   # not there yet
        self.assertEqual(self.req("GET", "/api/file/atlas?path=docs/notes.txt&lesson=01.01")[0], 404)
        self.assertEqual(self.file("docs/notes.txt", "01.02")[1]["note"], "shown whole, not split by lesson")
        self.assertEqual(self.file("src/b.c", "01.02")[1]["note"], "")

    def test_viewer_shows_the_reference_even_with_a_workspace(self):
        self.ws.start(self.core.Track("atlas"))                   # cuts 01.01 in the workspace
        with open(os.path.join(self.work, "atlas", "src", "a.c")) as f:
            self.assertIn("01.01: one not written yet", f.read())
        html = self.file("src/a.c", "01.01")[1]["html"]
        self.assertEqual([t for _, t in self.rows(html)], ["int a;", "int SECRET_ONE = 1;", "int tail_a;"])

    def test_viewer_output_is_highlighted(self):
        html = self.file("src/b.c", "01.02")[1]["html"]
        self.assertIn('<span class="tk-t">int</span>', html)
        self.assertIn('<span class="tk-n">2</span>', html)
        page = self.req("GET", "/t/atlas/01.02")[1]
        self.assertIn('class="tk-', page)                               # the code step too


SPAN_C = """#include "x.h"

// Free the page at pa.
// It goes back on the list.
void
kfree(void *pa)
{
  struct run *r;
  // @build 01.04 check
  // Panic unless pa is aligned.
  if(pa == 0)
    panic("kfree");
  // @end
  r = pa;
  // @build 01.04 push
  // Put r on the list.
  // @stub panic("push");
  r->next = freelist;
  freelist = r;
  // @end
}

/* Put a cell into a page. */
static int node_insert(Pager *p, int i)
{
    // @build 01.05 insert
    // Copy the cell in.
    return i + 1;
    // @end
}

static int table[] = {
  // @build 01.06 entries
  // Fill the table.
  1, 2, 3,
  // @end
};

int helper(void) {
  // @build 01.06 helper
  // Return seven.
  return 7;
  // @end
}

// @build 01.06 whole
// A definition that is all of it.
int whole(void)
{
  return 1;
}
// @end

int
labelled(void)
{
  if(x)
    goto found;
  return 0;
found:
  // @build 01.07 after a label
  // Finish up.
  return 1;
  // @end
}

void
both(void)
{
  // @build 01.08 first half
  // Do the first half.
  one();
  // @end
  // @build 01.09 second half
  // Then the second.
  two();
  // @end
}
"""

SPAN_S = """.globl _entry
_entry:
        # @build 01.07 a stack
        # Set up a stack.
        # @stub j spin
        la sp, stack0
        # @end
        call start
"""


SPAN_DOC = """---
id: 01.04
title: Free
---

# 01.04 Free

OPENING sentence.

## Where this fits

WHERE-TEXT about the map.

## The idea

IDEA-TEXT before the pieces.

### `kfree`

WHY-KFREE: pages come back here so they can be used again.

### Something else

OTHER-TEXT stays where it is.

## Run it

RUN-TEXT.

## How it works

HOW-TEXT.
"""


class CodeBlockTests(unittest.TestCase):
    """"The code" shows the whole definition a region sits in, as the file has it, minus the markers."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-span-test-")
        root = os.path.join(cls.tmp, "spans")
        write(os.path.join(root, "track.py"), RUNNABLE.replace('SOURCES = ["src/*.c"]', 'SOURCES = ["src/*.c", "src/*.S"]')
              + '\nFILES_FROM = {"src/*": "01.01"}\n')
        write(os.path.join(root, "src", "fn.c"), SPAN_C)
        write(os.path.join(root, "src", "entry.S"), SPAN_S)
        write(os.path.join(root, "lessons", "01-m", "README.md"), "---\nid: 01\ntitle: M\n---\n")
        write(os.path.join(root, "lessons", "01-m", "01.04-free.md"), SPAN_DOC)
        write(os.path.join(root, "lessons", "01-m", "figures", "01.04-map.svg"), SVG_FIGURE.replace("FIGURE-LABEL", "MAP-LABEL"))
        from harness import core, workspace
        cls.core, cls.ws = core, workspace
        cls.old = core.TRACKS_DIR
        core.TRACKS_DIR = cls.tmp
        cls.track = core.Track("spans")
        cls.lines = SPAN_C.split("\n")

    @classmethod
    def tearDownClass(cls):
        cls.core.TRACKS_DIR = cls.old
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def blocks(self, lid):
        from harness.web.views import code_blocks
        return code_blocks(self.track, lid)

    def numbers(self, block):
        return [n for n, _ in block["shown"]]

    def text(self, block):
        return [t for _, t in block["shown"]]

    def test_two_regions_in_one_function_show_it_once_with_both_titles(self):
        (block,) = self.blocks("01.04")
        self.assertEqual((block["titles"], block["path"], block["new"]), (["check", "push"], "src/fn.c", False))
        self.assertIn("kfree", block["names"])                                               # what a lead-in may be headed
        self.assertEqual(self.numbers(block), [3, 4, 5, 6, 7, 8, 11, 12, 14, 18, 19, 21])   # comment, signature ... closing brace
        self.assertEqual(self.text(block)[:5], ["// Free the page at pa.", "// It goes back on the list.", "void", "kfree(void *pa)", "{"])
        self.assertEqual(self.text(block)[-1], "}")
        for gone in ("@build", "@end", "@stub", "Panic unless", "Put r on the list"):
            self.assertFalse(any(gone in t for t in self.text(block)), gone)                 # no markers, no orders

    def test_a_one_line_signature_with_a_block_comment_above(self):
        (block,) = self.blocks("01.05")
        self.assertEqual(self.numbers(block), [23, 24, 25, 28, 30])
        self.assertEqual(self.text(block)[:2], ["/* Put a cell into a page. */", "static int node_insert(Pager *p, int i)"])

    def test_initializers_braces_on_the_signature_line_and_top_level_regions(self):
        table, helper, whole = self.blocks("01.06")
        self.assertEqual(self.numbers(table), [32, 35, 37])                                   # "= {" ... "};"
        self.assertEqual(self.text(table)[0], "static int table[] = {")
        self.assertEqual(self.numbers(helper), [39, 42, 44])                                  # "int helper(void) {"
        self.assertEqual(self.numbers(whole), [48, 49, 50, 51])                               # already the whole thing
        self.assertEqual(self.text(whole), ["int whole(void)", "{", "  return 1;", "}"])

    def test_a_goto_label_does_not_end_the_function(self):
        by_path = {b["path"]: b for b in self.blocks("01.07")}
        c, s = by_path["src/fn.c"], by_path["src/entry.S"]
        self.assertEqual(self.text(c)[:2], ["int", "labelled(void)"])
        self.assertIn("found:", self.text(c))
        self.assertEqual(self.text(c)[-1], "}")
        self.assertEqual((s["path"], self.numbers(s), self.text(s)), ("src/entry.S", [6], ["        la sp, stack0"]))   # assembly: as it is

    def lines_at(self, rel, at):
        from harness import timeline
        lines, shown, band = timeline.Project(self.track).lines_at(rel, at)
        return [lines[i] for i in shown], band

    def test_a_file_at_a_lesson_holds_only_what_is_built_by_then(self):
        text, _ = self.lines_at("src/fn.c", "01.04")
        joined = "\n".join(text)
        self.assertIn("kfree(void *pa)", joined)
        for later in ("node_insert", "Put a cell", "table", "helper", "whole", "labelled", "both", "one();"):
            self.assertNotIn(later, joined, later)                                          # whole definitions of later lessons
        for gone in ("@build", "@end", "@stub", "Panic unless"):
            self.assertNotIn(gone, joined)
        self.assertFalse(any(a == b == "" for a, b in zip(text, text[1:])), "two blank lines in a row")
        self.assertEqual(text[-1], "}")

    def test_a_function_two_lessons_share_keeps_what_is_reached(self):
        text, band = self.lines_at("src/fn.c", "01.08")
        joined = "\n".join(text)
        self.assertIn("both(void)", joined)
        self.assertIn("one();", joined)                                                        # 01.08's half
        self.assertNotIn("two();", joined)                                                     # 01.09's half, not yet
        text9, _ = self.lines_at("src/fn.c", "01.09")
        self.assertIn("two();", "\n".join(text9))
        (block,) = self.blocks("01.09")
        self.assertEqual(self.text(block)[:3], ["void", "both(void)", "{"])                    # the function, once more, with both halves
        self.assertIn("  one();", self.text(block))

    def test_lead_ins_move_above_their_code_and_where_this_fits_leads(self):
        from harness.web.views import lesson_page
        lesson = next(l for l in self.track.lessons if l.id == "01.04")
        page = lesson_page(self.track, lesson)
        steps = re.findall(r'<section class="sec step step-(\w+)"', page)
        self.assertEqual(steps, ["where", "idea", "code", "run", "why"])
        for sid, title in (("where", "Where this fits"), ("idea", "The idea"), ("code", "The code")):
            self.assertIn(f'id="step-{sid}" aria-label="{title}"', page)
        where = page[page.index('id="step-where"'):page.index('id="step-idea"')]
        self.assertIn("OPENING sentence.", plain(where))                                       # the intro sentence, then the map text
        self.assertIn("WHERE-TEXT", plain(where))
        idea = page[page.index('id="step-idea"'):page.index('id="step-code"')]
        self.assertIn("IDEA-TEXT", plain(idea))
        self.assertIn("OTHER-TEXT", plain(idea))                                               # a heading naming no code stays
        self.assertNotIn("WHY-KFREE", idea)                                                    # moved ...
        code = page[page.index('id="step-code"'):page.index('id="step-run"')]
        self.assertLess(code.index('class="region-title"'), code.index("WHY-KFREE"))           # ... under the block's title
        self.assertLess(code.index("WHY-KFREE"), code.index('class="code-block-shell"'))       # ... and before its code
        self.assertEqual(plain(page).count("WHY-KFREE"), 1)

    def test_the_overview_leads_with_the_track_map(self):
        from harness.web.views import track_page
        page = track_page(self.track)
        hero = page[page.index('<section class="ov-hero">'):page.index("</section>", page.index('<section class="ov-hero">'))]
        self.assertIn('<figure class="art ov-map">', hero)
        self.assertIn("MAP-LABEL", hero)

    def test_the_page_header_matches_the_first_line_shown(self):
        from harness.web.views import lesson_page
        lesson = next(l for l in self.track.lessons if l.id == "01.04")
        page = lesson_page(self.track, lesson)
        code = page[page.index('id="step-code"'):page.index('id="step-run"')]
        self.assertIn('<h3 class="region-title">check &middot; push</h3>', code)
        self.assertNotIn("new file", code)                                                  # fn.c was there from 01.01
        self.assertEqual(code.count('class="region"'), 1)
        target = os.path.join(self.tmp, "spans", "src", "fn.c") + ":3"
        self.assertIn(f'<code class="where-path">{target}</code>', code)
        self.assertIn(f'data-copy="{target}"', code)
        self.assertIn(":3\" data-editor", code)
        gutter = re.findall(r'<span class="ln">(?:<button[^>]*>.*?</button>)?(\d*)</span>', code, re.S)
        self.assertEqual(gutter[0], "3")
        for gone in ("@build", "@end", "@stub", "Panic unless", "region-prose"):
            self.assertNotIn(gone, code)



ALSO_C = ("""#include "a.h"
#include "b.h"  // @from 01.02

/* Grows by a line at 01.02. */
int grow(void)
{
  one();
  two();  // @from 01.02
  return 0;
}

int keep(void)
{
  return 1;
}

int medium(void)
{
  m1();
  m2();
  m3();
  m4();
  m5();
  added_m();  // @from 01.02
  m6();
  m7();
  m8();
  m9();
  m10();
  m11();
}

int built(void)
{
  // @build 01.02 built
  // Build it.
  x();
  // @end
}

// @from 01.02
/* Walks down. */
int walk(int n)
{
  if (n)
    return walk(n - 1);
  // @from 01.03
  later();
  // @end
  return 0;
}
// @end

// @internal
int test_aid(void)
{
  return 7;
}
// @end

int longer(void)
{
""" + "".join(f"  step{i}();\n" for i in range(1, 25)) + "  added();  // @from 01.02\n"
          + "".join(f"  step{i}();\n" for i in range(25, 50)) + """}

// @from 01.02
/* Big. */
int big(void)
{
""" + "".join(f"  big{i}();\n" for i in range(130)) + """}
// @end
""")

ALSO_H = """// Every function one file calls in another.

struct cache;  // @from 01.02

// old.c
int grow(void);
int keep(void);
int walk(int n);  // @from 01.02

// @from 01.02
// big.c - what 01.02 brings
void big(void);
extern int nbig;
// @end

struct pair {
  int a;
  int b;  // @from 01.02
};

// @from 01.02
#define LIMIT 10
// @end

// @from 01.02
/* ---- grow2.c */

int grow2(void);
// @end
"""

# New at 01.02 and long: a C file with functions, one the notes talk about, and one that is only data.
GEN_FNS = "".join(f"/* Step {i}. */\nint fn{i}(void)\n{{\n" + "".join(f"  s{i}_{j}();\n" for j in range(8)) + "}\n\n"
                  for i in range(20))
GEN_DATA = "unsigned char glyphs[] = {\n" + "".join(f"  0x{i:02x}, 0x00, 0xff,\n" for i in range(200)) + "};\n"

ALSO_DOC = """---
id: 01.02
title: Grow
---

# 01.02 Grow

OPENING.

## The idea

IDEA.

### `walk`: down to zero

WHY-WALK.

### `talked.c`: one the notes talk about

WHY-TALKED.

## How it works

HOW.
"""


class AlsoBlockTests(unittest.TestCase):
    """"The code" also shows what a lesson adds through @from in files that were there already:
    whole pieces, after the lesson's own blocks, under a quieter heading."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-also-test-")
        root = os.path.join(cls.tmp, "also")
        write(os.path.join(root, "track.py"), RUNNABLE + '\nFILES_FROM = {"src/*": "01.01", "gen/*": "01.02"}\n')
        write(os.path.join(root, "src", "old.c"), ALSO_C)
        write(os.path.join(root, "src", "old.h"), ALSO_H)
        write(os.path.join(root, "gen", "fns.c"), GEN_FNS)
        write(os.path.join(root, "gen", "talked.c"), GEN_FNS)
        write(os.path.join(root, "gen", "glyphs.c"), GEN_DATA)
        write(os.path.join(root, "lessons", "01-m", "README.md"), "---\nid: 01\ntitle: M\n---\n")
        write(os.path.join(root, "lessons", "01-m", "01.01-base.md"), "---\nid: 01.01\ntitle: Base\n---\n\n# 01.01 Base\n\nB.\n")
        write(os.path.join(root, "lessons", "01-m", "01.02-grow.md"), ALSO_DOC)
        write(os.path.join(root, "lessons", "01-m", "01.03-later.md"), "---\nid: 01.03\ntitle: Later\n---\n\n# 01.03 Later\n\nL.\n")
        from harness import core
        cls.core = core
        cls.old = core.TRACKS_DIR
        core.TRACKS_DIR = cls.tmp
        cls.track = core.Track("also")
        cls.src = ALSO_C.split("\n")

    @classmethod
    def tearDownClass(cls):
        cls.core.TRACKS_DIR = cls.old
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def blocks(self, lid, apart=(), path="src/old.c"):
        from harness.web.views import also_blocks
        return [b for b in also_blocks(self.track, lid, apart=apart) if b["path"] == path]

    def line(self, text):
        return self.src.index(text) + 1

    def test_whole_pieces_with_real_line_numbers_and_nothing_shown_twice(self):
        (b,) = self.blocks("01.02")
        self.assertEqual((b["path"], b["titles"], b["also"], b["new"]), ("src/old.c", ["old.c"], True, False))
        rows = dict((n, t) for n, t in b["shown"] if n is not None)
        for n, t in rows.items():
            self.assertEqual(t, self.src[n - 1].split("  // @from")[0])                    # the file's own lines, markers off
        self.assertIn(self.line("int walk(int n)"), rows)                                  # a function the lesson brings: whole
        self.assertIn(self.line("/* Walks down. */"), rows)                                # with its comment
        self.assertIn(self.line("int grow(void)"), rows)                                   # an older one it adds a line to: whole, short
        self.assertIn(self.line("  one();"), rows)
        self.assertNotIn(self.line("int keep(void)"), rows)                                # nothing added there
        self.assertNotIn(self.line("int built(void)"), rows)                               # the lesson's own block shows it
        for gone in ("later();", "test_aid", "@from", "@end", "@internal"):                # a later lesson's, never-shown, markers
            self.assertFalse(any(gone in t for t in rows.values()), gone)
        self.assertEqual(set(b["names"]) >= {"walk", "grow", "longer", "big"}, True)
        (b3,) = self.blocks("01.03")                                                     # at 01.03 walk is older code it adds to
        pos = {n: k for k, (n, _) in enumerate(b3["shown"]) if n is not None}
        self.assertIn(pos[self.line("  later();")], b3["band"])
        self.assertNotIn(pos[self.line("int walk(int n)")], b3["fresh"])
        self.assertNotIn(self.line("int big(void)"), pos)

    def test_a_long_older_function_shows_its_signature_and_a_window(self):
        (b,) = self.blocks("01.02")
        shown = b["shown"]
        at = [k for k, (n, _) in enumerate(shown) if n == self.line("  added();  // @from 01.02")][0]
        self.assertIn(at, b["band"])                                                       # the added line, banded
        sig = [k for k, (n, _) in enumerate(shown) if n == self.line("int longer(void)")][0]
        self.assertEqual(shown[sig + 1][1], "{")
        self.assertIsNone(shown[sig + 2][0])                                               # a gap, then two lines each side
        self.assertEqual([t.strip() for _, t in shown[at - 2:at + 3]],
                         ["step23();", "step24();", "added();", "step25();", "step26();"])
        self.assertIsNone(shown[at - 3][0])
        self.assertIsNone(shown[at + 3][0])
        self.assertEqual(shown[at + 4], (self.line("  step49();") + 1, "}"))              # and the closing brace
        self.assertEqual(shown[at + 3][1], "  ")                                          # the gap is indented as the body

    def test_a_short_older_function_is_never_shown_whole_for_one_added_line(self):
        (b,) = self.blocks("01.02")
        rows = [(n, t.strip()) for n, t in b["shown"]]
        at = rows.index((self.line("  added_m();  // @from 01.02"), "added_m();"))
        sig = self.line("int medium(void)")
        self.assertEqual(rows[at - 5:at + 5], [(sig, "int medium(void)"), (sig + 1, "{"), (None, ""),       # its signature,
                                               (self.line("  m4();"), "m4();"), (self.line("  m5();"), "m5();"),
                                               rows[at], (self.line("  m6();"), "m6();"), (self.line("  m7();"), "m7();"),
                                               (None, ""), (self.line("  m11();") + 1, "}")])      # two lines each side, its brace
        self.assertIn(at, b["band"])
        for gone in ("  m1();", "  m9();"):
            self.assertNotIn(self.line(gone), [n for n, _ in rows])

    def test_a_headers_new_declarations_are_counted_not_listed(self):
        (code,) = [b for b in self.blocks("01.02", path="src/old.h") if not b.get("decls")]
        (count,) = [b for b in self.blocks("01.02", path="src/old.h") if b.get("decls")]
        self.assertEqual((count["decls"], count["lines"], count["titles"], count["shown"]), (5, 5, ["old.h"], []))
        text = [t for n, t in code["shown"] if n is not None]
        for gone in ("struct cache;", "int walk(int n);", "void big(void);", "extern int nbig;", "// big.c - what 01.02 brings",
                     "/* ---- grow2.c */", "int grow2(void);"):
            self.assertNotIn(gone, text)                                                   # counted, and their heading with them
        self.assertIn("  int b;", text)                                                    # a struct gaining a field: code
        self.assertIn("#define LIMIT 10", text)                                            # a #define: code
        from harness.web.views import also_blocks
        got = also_blocks(self.track, "01.02")
        self.assertTrue(got[-1].get("decls") and not any(b.get("decls") for b in got[:-1]))   # counted ones come last
        self.assertFalse(self.blocks("01.03", path="src/old.h"))                          # nothing added at 01.03

    def test_the_lines_a_lesson_brings_whole_are_fresh_and_older_ones_banded(self):
        (b,) = self.blocks("01.02")
        pos = {n: k for k, (n, _) in enumerate(b["shown"]) if n is not None}
        self.assertEqual(b["fresh"][pos[self.line("int walk(int n)")]], "walk")
        self.assertEqual(b["fresh"][pos[self.line("int big(void)")]], "big")
        self.assertIn(pos[self.line('#include "b.h"  // @from 01.02')], b["fresh"])
        self.assertIn(pos[self.line("  two();  // @from 01.02")], b["band"])
        self.assertNotIn(pos[self.line("  one();")], b["band"])
        self.assertNotIn(pos[self.line("int walk(int n)")], b["band"])

    def test_pieces_the_notes_name_get_a_block_of_their_own_first(self):
        named, rest = self.blocks("01.02", apart={"walk"})
        self.assertEqual((named["titles"], rest["titles"], rest.get("more")), (["old.c"], ["more in old.c"], True))
        self.assertEqual(named["names"], ["walk"])
        self.assertEqual(named["shown"][0], (self.line("/* Walks down. */"), "/* Walks down. */"))
        self.assertNotIn("walk", rest["names"])

    def test_units_split_a_c_file_into_whole_pieces(self):
        from harness import timeline
        lines = ["/* a */", "int x;", "", "struct s {", "  int y;", "};", "", "#define A \\", "  1",
                 "void", "f(void)", "{", "  if (x) {", "  }", "}", "int g(void) { return 1; }", "/* alone */", ""]
        self.assertEqual(timeline.units(lines), [(0, 1, 1), (3, 3, 5), (7, 7, 8), (9, 9, 14), (15, 15, 15), (16, 16, 16)])
        self.assertEqual(timeline.units(["a", "b", "", "c"], c=False), [(0, 0, 1), (3, 3, 3)])
        self.assertEqual(timeline.code_part('  x = "//";  // y'), '  x = "//";')

    def test_the_page_shows_them_after_the_lessons_own_code_under_a_quiet_heading(self):
        from harness.web.views import lesson_page
        lesson = next(l for l in self.track.lessons if l.id == "01.02")
        page = lesson_page(self.track, lesson)
        start = page.index('id="step-code"')
        ends = [i for i in (page.find('<section class="sec step', start), page.find('<aside class="lesson-rail"', start)) if i > 0]
        code = page[start:min(ends)]                                                       # the code step, up to what follows it
        self.assertLess(code.index('<h3 class="region-title">built</h3>'), code.index('class="also"'))
        also = code[code.index('<div class="also">'):]
        titles = re.findall(r'<h4 class="region-title also-file">(.*?)</h4>', also)
        self.assertEqual(titles, ["old.c", "more in old.c", "old.h"])                      # walk, under its notes, then the rest
        self.assertLess(also.index("WHY-WALK"), also.index("more in old.c"))
        self.assertNotIn("WHY-WALK", page[page.index('id="step-goal"'):page.index('id="step-code"')])
        first = also[:also.index("<details")]                                              # walk: outside the disclosure, open
        self.assertIn("old.c</h4>", first)
        self.assertNotIn("more in old.c", first)
        self.assertNotIn("data-shut", first)                                               # what the notes talk about stays open
        more = also[also.index("<details"):]
        self.assertTrue(more.startswith('<details class="also-more"><summary class="also-sum">'))   # closed: no open attribute
        summary = plain(more[:more.index("</summary>")])
        rest = more[more.index("</summary>"):]
        shown = sum(1 for b in self.blocks("01.02", apart={"walk"})[1:] for n, _ in b["shown"] if n is not None)
        shown += sum(1 for b in self.blocks("01.02", path="src/old.h") if not b.get("decls") for n, _ in b["shown"] if n is not None)
        self.assertEqual(summary, f"Also added in this lesson - 2 files, {shown + 5:,} lines")
        self.assertIn('class="fbody shut" data-shut="1"', rest)                             # a long group: what it brings, folded
        self.assertIn('aria-expanded="false"', rest)
        self.assertIn('<div class="row gap">', rest)
        self.assertIn('class="row band"', rest)
        self.assertIn('<ul class="also-decls"><li><code>old.h</code>: 5 declarations</li></ul>', rest)
        self.assertIn("</ul></div></details></div>", rest)                                 # the counted rows close the group
        for gone in ("@from", "@internal", "test_aid", "later();"):
            self.assertNotIn(gone, code)
        self.assertIn("data-fold-toggle", page)

    def test_a_long_new_file_no_lead_in_talks_about_starts_folded_or_clipped(self):
        from harness.web.views import lesson_page, CLIP
        lesson = next(l for l in self.track.lessons if l.id == "01.02")
        page = lesson_page(self.track, lesson)
        code = page[page.index('id="step-code"'):page.index('class="also"')]               # the lesson's own blocks
        blocks = {m.group(1): m.start() for m in re.finditer(r'<h3 class="region-title">([\w.]+)<span class="tag">new file', code)}
        self.assertEqual(sorted(blocks), ["fns.c", "glyphs.c", "talked.c"])

        def block(name):
            start = blocks[name]
            return code[start:min([p for p in blocks.values() if p > start] + [len(code)])]
        fns = block("fns.c")
        self.assertEqual(fns.count('class="fbody shut" data-shut="1"'), 20)                # every body shut: its functions
        self.assertEqual(fns.count('class="fbody"'), 0)
        self.assertNotIn("clip", fns)
        talked = block("talked.c")                                                         # a lead-in talks about it: open
        self.assertIn("WHY-TALKED", talked)
        self.assertNotIn("data-shut", talked)
        glyphs = block("glyphs.c")                                                         # nothing to fold: its first lines
        pane = re.search(r'<div class="file on rows clipped" id="(clip-\d+)">', glyphs)
        self.assertTrue(pane)
        rows = re.findall(r'<div class="row( clip-x)?">', glyphs)
        self.assertEqual(len(rows), 202)
        self.assertEqual([bool(x) for x in rows], [False] * CLIP + [True] * (202 - CLIP))
        self.assertIn(f'aria-expanded="false" aria-controls="{pane.group(1)}" data-more="Show all 202 lines" '
                      f'data-less="Show the first {CLIP} lines">', glyphs)
        css = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "app.css")).read()
        self.assertIn(".rows.clipped .row.clip-x { display: none; }", css)

    def test_a_group_that_is_all_the_code_is_not_behind_a_disclosure(self):
        from harness.web import views
        lesson = next(l for l in self.track.lessons if l.id == "01.03")
        page = views.lesson_page(self.track, lesson)
        code = page[page.index('id="step-code"'):]
        self.assertIn('<div class="also alone">', code)                                    # 01.03 adds only through @from
        self.assertNotIn("<details", code[:code.index('<aside class="lesson-rail"')])

    def test_functions_only_off_puts_the_folded_ones_back(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "app.js")) as f:
            js = f.read()
        self.assertIn('setFold(f, shut || f.hasAttribute("data-shut"))', js)


# New at 01.02: a long file of functions with underscores in their names, and free(), whose name
# is an English word; and two short files that both define main() and shared_fn().
PLAIN_BIG = ("".join(f"/* Step {i}. */\nint step_{i}(int x)\n{{\n" + "".join(f"  s{i}_{j}(x);\n" for j in range(8)) + "}\n\n"
                     for i in range(20)) + "/* Give it back. */\nvoid free(void *p)\n{\n  put(p);\n}\n")
PLAIN_TWIN = "int main(void)\n{\n  return shared_fn();\n}\n\nint shared_fn(void)\n{\n  return 1;\n}\n"

PLAIN_DOC = """---
id: 01.02
title: Plain
---

# 01.02 Plain

OPENING.

## The idea

IDEA.

### step_7: the seventh step

WHY-SEVEN.

### The main loop

WHY-MAIN-PLAIN.

### Writing `main` in `twin.c`

WHY-TWIN-MAIN.

## How it works

HOW.

### Writing step_3, step by step

HOW-THREE.

### Writing shared_fn, step by step

HOW-SHARED.

### Why free pages come back

HOW-FREE-PLAIN.

### Writing `free`, step by step

HOW-FREE.
"""


class PlainNameLeadInTests(unittest.TestCase):
    """A lead-in's heading may name a function without backticks, when the word is exactly the
    name of one the lesson shows and could not be an ordinary English word."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="learn-plain-test-")
        root = os.path.join(cls.tmp, "plain")
        write(os.path.join(root, "track.py"), RUNNABLE + '\nFILES_FROM = {"src/*": "01.01", "gen/*": "01.02"}\n')
        write(os.path.join(root, "src", "old.c"), "int base(void)\n{\n  return 0;\n}\n")
        write(os.path.join(root, "gen", "big.c"), PLAIN_BIG)
        write(os.path.join(root, "gen", "twin.c"), PLAIN_TWIN)
        write(os.path.join(root, "gen", "other.c"), PLAIN_TWIN)
        write(os.path.join(root, "lessons", "01-m", "README.md"), "---\nid: 01\ntitle: M\n---\n")
        write(os.path.join(root, "lessons", "01-m", "01.01-base.md"), "---\nid: 01.01\ntitle: Base\n---\n\n# 01.01 Base\n\nB.\n")
        write(os.path.join(root, "lessons", "01-m", "01.02-plain.md"), PLAIN_DOC)
        from harness import core
        cls.core = core
        cls.old = core.TRACKS_DIR
        core.TRACKS_DIR = cls.tmp
        cls.track = core.Track("plain")

    @classmethod
    def tearDownClass(cls):
        cls.core.TRACKS_DIR = cls.old
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_a_plain_word_names_a_definition_only_when_it_cannot_be_english(self):
        from harness.web.views import heading_names, plain_name
        known = {"node_insert", "kalloc", "free", "main", "line", "split", "ls", "wc", "udpecho", "x80"}
        self.assertIn("node_insert", heading_names("Writing node_insert, step by step", known))
        self.assertIn("kalloc", heading_names("Writing kalloc, step by step", known))
        self.assertEqual(heading_names("Writing node_insert, step by step"), ["writing node_insert, step by step"])
        for heading in ("Why free pages come back", "The main loop", "One line at a time", "Writing split, step by step",
                        "ls and wc", "Kalloc first", "udpecho.c", "0x80 and above", "Writing node_inserts"):
            got = heading_names(heading, known)
            self.assertFalse(set(got) & known, heading)                                     # prose, a file, a number, case
        self.assertEqual(set(heading_names("`free`, `ls` and `wc()`", known)), {"free", "ls", "wc"})   # backticks always count
        self.assertEqual([plain_name(w) for w in ("seek_raw", "fbinit", "free", "main", "line", "ls", "wc", "arp")],
                         [True, True, False, False, False, False, False, False])

    def test_one_block_alone_may_take_a_definition_and_a_region_or_file_comes_first(self):
        from harness.web.views import lead_target
        a = {"names": ["a.c", "src/a.c"], "defs": ["main", "shared_fn", "only_a"]}
        b = {"names": ["the main loop", "b.c", "src/b.c", "main"], "defs": ["main", "shared_fn"]}
        known = {"main", "shared_fn", "only_a"}
        self.assertEqual(lead_target("Writing `main`, step by step", [a, b], known), 1)       # a region in b is main
        self.assertIsNone(lead_target("Writing shared_fn, step by step", [a, b], known))     # in both: neither
        self.assertEqual(lead_target("Writing `shared_fn` in `a.c`", [a, b], known), 0)       # the file says which
        self.assertEqual(lead_target("Writing only_a, step by step", [a, b], known), 0)
        self.assertEqual(lead_target("The main loop", [a, b], known), 1)                      # a region's title
        self.assertIsNone(lead_target("Writing the main part", [a, b], known))                # main is a word too

    def page(self):
        from harness.web.views import lesson_page
        lesson = next(l for l in self.track.lessons if l.id == "01.02")
        page = lesson_page(self.track, lesson)
        return page, page[page.index('id="step-code"'):page.index('id="step-why"')]

    def test_plain_names_attach_and_the_rest_stays_in_its_step(self):
        page, code = self.page()
        idea = page[page.index('id="step-idea"') if 'id="step-idea"' in page else page.index('id="step-goal"'):page.index('id="step-code"')]
        how = page[page.index('id="step-why"'):]
        for moved in ("WHY-SEVEN", "HOW-THREE", "HOW-FREE.", "WHY-TWIN-MAIN"):
            self.assertIn(moved, code, moved)
            self.assertEqual(plain(page).count(moved), 1, moved)
        self.assertIn("WHY-MAIN-PLAIN", plain(idea))                                          # "main": a word, no region
        self.assertIn("HOW-SHARED", plain(how))                                               # two files define it
        self.assertIn("HOW-FREE-PLAIN", plain(how))                                           # "free": a word
        blocks = {m.group(1): m.start() for m in re.finditer(r'<h3 class="region-title">([\w.]+)<span class="tag">new file', code)}

        def block(name):
            start = blocks[name]
            return code[start:min([p for p in blocks.values() if p > start] + [len(code)])]
        self.assertIn("WHY-TWIN-MAIN", block("twin.c"))
        self.assertNotIn("WHY-TWIN-MAIN", block("other.c"))

    def test_a_long_new_file_opens_the_functions_its_lead_ins_name_and_folds_the_rest(self):
        _, code = self.page()
        start = code.index('<h3 class="region-title">big.c')
        big = code[start:code.index('<h3 class="region-title">', start + 1)]
        self.assertIn("WHY-SEVEN", big)
        self.assertEqual(big.count('class="fbody shut" data-shut="1"'), 18)                 # every other body: folded
        self.assertEqual(big.count('class="fbody"'), 3)
        expanded = dict((m.group(2), m.group(1)) for m in
                        re.finditer(r'aria-expanded="(\w+)" aria-controls="[^"]+" aria-label="Fold (\w+)"', big))
        self.assertEqual({n for n, e in expanded.items() if e == "true"}, {"step_7", "step_3", "free"})
        self.assertEqual(len(expanded), 21)


class TimelineCheckTests(unittest.TestCase):
    """What `./learn check` says about when files appear."""

    def test_problems(self):
        from harness import core, timeline
        tmp = tempfile.mkdtemp(prefix="learn-timeline-test-")
        old = core.TRACKS_DIR
        try:
            root = os.path.join(tmp, "tl")
            write(os.path.join(root, "track.py"), RUNNABLE + '\nFILES_FROM = {"src/late.c": "01.02", "docs/*": "09.09", "nothing/*": "01.01"}\n')
            write(os.path.join(root, "src", "late.c"), region("01.01", "early", "int x;"))
            write(os.path.join(root, "src", "orphan.h"), "int y;\n")
            write(os.path.join(root, "docs", "a.txt"), "a\n")
            for lid in ("01.01", "01.02"):
                write(os.path.join(root, "lessons", "01-m", f"{lid}-x.md"), f"---\nid: {lid}\ntitle: X\n---\n")
            core.TRACKS_DIR = tmp
            got = timeline.Project(core.Track("tl")).problems()
        finally:
            core.TRACKS_DIR = old
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIn("src/orphan.h: no lesson introduces it (add it to FILES_FROM in track.py)", got)
        self.assertIn("FILES_FROM['docs/*']: '09.09' is not a lesson of this track", got)
        self.assertIn("FILES_FROM['nothing/*']: matches no file", got)
        self.assertIn("src/late.c: FILES_FROM says 01.02, but 01.01 already has code in it", got)
        self.assertEqual(len(got), 4, got)
        from harness import cli
        self.assertIn("timeline.Project(tr).problems()", open(cli.__file__).read())          # ./learn check runs it


if __name__ == "__main__":
    unittest.main()
