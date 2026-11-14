"""A small markdown renderer: standard library only, escapes everything first.

Supports headings, paragraphs, fenced code, inline code, bold, italic, links,
lists (nested), tables, blockquotes, rules and figures. Raw HTML in the source is
never passed through: every character is escaped before any markup is added. The
lines of a paragraph are joined with a space before inline markup is read, so a
span may wrap across them (a soft line break, as in CommonMark).

    render(text, resolve_link=None, figure=None) -> html string

resolve_link(href) may return a replacement href, or None to leave the link
as it is. Links that are not http(s), mailto, anchors or relative paths are
rendered as plain text.

A line of its own of the form ![Caption](path) is a figure. figure(path) returns
safe markup for it (inline SVG) or "" to refuse it; a refused figure, or any
figure when no figure callback is given, renders nothing, caption included.

HTML comments (<!-- ... -->) render as nothing at all, on lines of their own or inside a
line, over one line or several; in fenced code and in `code spans` they are text like any
other. Lessons carry their authors' notes for ./learn verify in them (strip_comments).
"""

import html
import re

from harness.web import highlight

FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+.-]*)")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
RULE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
QUOTE = re.compile(r"^\s{0,3}>")
LIST = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
SAFE_SCHEME = re.compile(r"^(https?:|mailto:|#|/|\.|[\w-]+(/|\.|#|$))", re.I)
BAD_SCHEME = re.compile(r"^\s*[a-z][a-z0-9+.-]*:", re.I)
FIGURE = re.compile(r"^\s{0,3}!\[([^\]\n]*)\]\(\s*([^)\s]+)\s*\)\s*$")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


# ---------------------------------------------------------------- comments

def _uncomment_line(line, open_comment):
    """(line without its comments, whether a comment is still open at its end). Backtick spans
    are skipped over, so a `<!--` inside one is text. open_comment: the line starts inside a
    comment opened on an earlier line."""
    out, i, n = [], 0, len(line)
    if open_comment:
        j = line.find("-->")
        if j < 0:
            return "", True
        i = j + 3
    while i < n:
        if line[i] == "`":
            run = len(line[i:]) - len(line[i:].lstrip("`"))
            close = line.find("`" * run, i + run)
            while close >= 0 and line[close + run:close + run + 1] == "`":   # a longer run is not the closer
                close = line.find("`" * run, close + run + 1)
            if close >= 0:
                out.append(line[i:close + run])
                i = close + run
                continue
            out.append(line[i:i + run])
            i += run
            continue
        if line.startswith("<!--", i):
            j = line.find("-->", i + 4)
            if j < 0:
                return "".join(out), True
            i = j + 3
            continue
        out.append(line[i])
        i += 1
    return "".join(out), False


def strip_comments(text):
    """text without its HTML comments. A line that held nothing but comment goes whole, so a
    comment between two lines of a paragraph leaves one paragraph; fenced code is left as it is."""
    out, fence, open_comment = [], None, False
    for line in text.split("\n"):
        if fence is not None:
            out.append(line)
            if _closes(fence, line):
                fence = None
            continue
        if not open_comment:
            m = FENCE.match(line)
            if m:
                fence = m.group(2)
                out.append(line)
                continue
            if "<!--" not in line:
                out.append(line)
                continue
        kept, open_comment = _uncomment_line(line, open_comment)
        if kept.strip() or not line.strip():
            out.append(kept.rstrip() if kept.strip() else kept)
    return "\n".join(out)


# ---------------------------------------------------------------- inline

def inline(text, resolve_link=None):
    text = html.escape(text.replace("\0", ""), quote=True)
    stash = []

    def keep(markup):
        stash.append(markup)
        return f"\0{len(stash) - 1}\0"

    text = re.sub(r"(`+)(.+?)\1", lambda m: keep(f"<code>{m.group(2).strip()}</code>"), text)

    def link(m):
        label, href = m.group(1), html.unescape(m.group(2))
        if resolve_link:
            href = resolve_link(href) or href
        if BAD_SCHEME.match(href) and not re.match(r"^(https?|mailto):", href, re.I):
            return emphasis(label)
        if not SAFE_SCHEME.match(href):
            return emphasis(label)
        return keep(f'<a href="{html.escape(href, quote=True)}">{emphasis(label)}</a>')

    text = re.sub(r"\[([^\]\n]+)\]\(([^)\s]+)(?:\s+&quot;[^)]*?&quot;)?\)", link, text)
    text = emphasis(text)
    return re.sub(r"\0(\d+)\0", lambda m: stash[int(m.group(1))], text)


def emphasis(text):
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w_])__(?=\S)(.+?)(?<=\S)__(?![\w_])", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\w_])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w_])", r"<em>\1</em>", text)
    return text


# ---------------------------------------------------------------- blocks

def render(text, resolve_link=None, figure=None):
    text = strip_comments(text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = text.replace("\t", "    ").split("\n")
    return "\n".join(_blocks(lines, resolve_link, {}, figure))


def _starts_block(lines, i):
    """Whether lines[i] ends the paragraph before it and starts a block of its own."""
    line = lines[i]
    return bool(FENCE.match(line) or HEADING.match(line) or QUOTE.match(line) or FIGURE.match(line)
                or _interrupts(line) or RULE.match(line) or _is_table(lines, i))


def _interrupts(line):
    """A list item that may break into a paragraph: a bullet, or a numbered item
    numbered 1. A wrapped sentence whose next line begins "254. Floats ..." stays
    one paragraph (CommonMark's rule)."""
    m = LIST.match(line)
    return bool(m) and (not m.group(2)[0].isdigit() or int(m.group(2)[:-1]) == 1)


def _closes(fence, line):
    """Whether line closes a code block opened with fence (``` or ~~~, at least as long)."""
    return re.match(r"^\s*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$", line) is not None


def _figure(m, rl, figure):
    """<figure> for a figure line, or "" when there is no callback or it refuses the path."""
    svg = figure(m.group(2)) if figure else ""
    if not svg:
        return ""
    caption = m.group(1).strip()
    cap = f"<figcaption>{inline(caption, rl)}</figcaption>" if caption else ""
    return f'<figure class="art fig">{svg}{cap}</figure>'


def _is_table(lines, i):
    return (i + 1 < len(lines) and "|" in lines[i] and "|" in lines[i + 1]
            and TABLE_SEP.match(lines[i + 1]) is not None)


def _cells(line):
    line = line.strip().replace("\\|", "\0")
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.replace("\0", "|").strip() for c in line.split("|")]


def _blocks(lines, rl, seen, fig=None):
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = FENCE.match(line)
        if m:
            indent, fence, lang = len(m.group(1)), m.group(2), m.group(3)
            body = []
            i += 1
            while i < n and not _closes(fence, lines[i]):
                body.append(lines[i][indent:] if lines[i][:indent].strip() == "" else lines[i])
                i += 1
            i += 1
            cls = f' class="lang-{html.escape(lang, quote=True)}"' if lang else ""
            code = "\n".join(highlight.highlight_lines("\n".join(body), highlight.fence_lang(lang)))
            out.append(f"<pre><code{cls}>{code}</code></pre>")
            continue
        m = FIGURE.match(line)
        if m:
            markup = _figure(m, rl, fig)
            if markup:
                out.append(markup)
            i += 1
            continue
        m = HEADING.match(line)
        if m:
            level, title = len(m.group(1)), m.group(2)
            sid = slug(title)
            seen[sid] = seen.get(sid, 0) + 1
            if seen[sid] > 1:
                sid += f"-{seen[sid]}"
            out.append(f'<h{level} id="{sid}">{inline(title, rl)}</h{level}>')
            i += 1
            continue
        if RULE.match(line):
            out.append("<hr>")
            i += 1
            continue
        if QUOTE.match(line):
            inner = []
            while i < n and QUOTE.match(lines[i]):
                inner.append(re.sub(r"^\s{0,3}>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + "\n".join(_blocks(inner, rl, seen, fig)) + "</blockquote>")
            continue
        if _is_table(lines, i):
            head = _cells(line)
            aligns = []
            for c in _cells(lines[i + 1]):
                aligns.append("center" if c.startswith(":") and c.endswith(":")
                              else "right" if c.endswith(":") else "")
            i += 2
            rows = []
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append(_cells(lines[i]))
                i += 1

            def cell(tag, k, c):
                a = f' style="text-align:{aligns[k]}"' if k < len(aligns) and aligns[k] else ""
                return f"<{tag}{a}>{inline(c, rl)}</{tag}>"

            t = "<div class=\"table-wrap\"><table><thead><tr>"
            t += "".join(cell("th", k, c) for k, c in enumerate(head)) + "</tr></thead><tbody>"
            for r in rows:
                t += "<tr>" + "".join(cell("td", k, c) for k, c in enumerate(r)) + "</tr>"
            out.append(t + "</tbody></table></div>")
            continue
        if LIST.match(line):
            html_, i = _list(lines, i, rl, seen, fig)
            out.append(html_)
            continue
        para = [line.strip()]
        i += 1
        while i < n and lines[i].strip() and not _starts_block(lines, i):
            para.append(lines[i].strip())
            i += 1
        # A line break inside a paragraph (or a list item's text) is only where the source
        # wrapped: joined with a space, as CommonMark does, so a `code span`, **bold** or
        # *emphasis* that wraps onto the next line is still one span.
        out.append("<p>" + inline(" ".join(para), rl) + "</p>")
    return out


def _list(lines, i, rl, seen, fig=None):
    """One list starting at lines[i]: (html, index of the first line after it).

    Items may be separated by blank lines (a loose list: every item's text
    becomes a paragraph). After a blank line, a line indented past the
    marker's column still belongs to the item before it, so an item can hold
    several paragraphs, a fenced code block (blank lines inside it included)
    or a nested list. An ordered list keeps the number it starts at."""
    n = len(lines)
    first = LIST.match(lines[i])
    base = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    start = int(first.group(2)[:-1]) if ordered else 1
    items, loose = [], False
    while i < n:
        m = LIST.match(lines[i])
        if not m or len(m.group(1)) > base + 1 or m.group(2)[0].isdigit() != ordered:
            break
        body = [m.group(3)]
        width = len(m.group(1)) + len(m.group(2)) + 1
        i += 1
        fence = None    # the fence of a code block opened in this item, until it closes
        while i < n:
            nxt = lines[i]
            indent = len(nxt) - len(nxt.lstrip())
            if fence:
                # Inside the item's code block every line is code, a blank or
                # an under-indented one too, up to the closing fence.
                body.append(nxt[min(indent, width):])
                if _closes(fence, nxt):
                    fence = None
                i += 1
                continue
            if not nxt.strip():
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and len(lines[j]) - len(lines[j].lstrip()) > base + 1:
                    body.extend([""] * (j - i))
                    loose = True
                    i = j
                    continue
                nm = LIST.match(lines[j]) if j < n else None
                if nm and len(nm.group(1)) <= base + 1 and nm.group(2)[0].isdigit() == ordered:
                    loose = True
                    i = j    # the next item of this list, not the end of it
                break
            if indent > base + 1:
                body.append(nxt[min(indent, width):])
                fm = FENCE.match(nxt)
                if fm:
                    fence = fm.group(2)
            elif LIST.match(nxt) or _starts_block(lines, i):
                break
            else:
                body.append(nxt.strip())
            i += 1
        items.append(body)
    tag = "ol" if ordered else "ul"
    parts = []
    for body in items:
        blocks = _blocks(body, rl, seen, fig)
        if not loose and blocks and blocks[0].startswith("<p>"):
            blocks[0] = re.sub(r"^<p>(.*?)</p>$", r"\1", blocks[0], flags=re.S)
        parts.append("<li>" + "\n".join(blocks) + "</li>")
    attrs = f' start="{start}"' if ordered and start != 1 else ""
    return f"<{tag}{attrs}>" + "".join(parts) + f"</{tag}>", i
