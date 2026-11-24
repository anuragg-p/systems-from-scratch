"""Tests for lists in the markdown renderer: loose lists, and the paragraphs and code blocks an
item holds; and for inline spans nested in one another (code in a link's text)."""

import random
import re
import unittest

from harness.web.markdown import inline, render

# The shape of a lesson's "Writing ..., step by step" section: numbered steps separated by
# blank lines, some with a second paragraph or a code block indented under them.
STEPS = """### Writing serial_get, step by step

1. **Start from an empty value,** so no field is left over.

2. **The types with no body bytes:** 0 is NULL, 8 and 9 are 0 and 1.

3. **A float:** assemble the eight bytes.

   ```
           for (int k = 0; k < 8; k++)
               bits = (bits << 8) | p[k];

           memcpy(&v->r, &bits, sizeof v->r);
   ```

4. **Text and blobs: point, do not copy.** The value points into the page.

   Copying every string would cost more than reading it.

5. **Done.**

After the list.
"""


def items(html, tag="ol"):
    """The <li> bodies of the only list of kind tag in html."""
    lists = re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.S)
    assert len(lists) == 1, f"expected one <{tag}>, got {len(lists)}:\n{html}"
    return re.findall(r"<li>(.*?)</li>", lists[0], re.S)


class LooseListTests(unittest.TestCase):
    def test_blank_lines_between_items_keep_one_list(self):
        out = render("1. one\n\n2. two\n\n3. three")
        self.assertEqual(out, "<ol><li><p>one</p></li><li><p>two</p></li><li><p>three</p></li></ol>")
        out = render("- a\n\n- b\n\n\n- c")
        self.assertEqual(out, "<ul><li><p>a</p></li><li><p>b</p></li><li><p>c</p></li></ul>")

    def test_tight_list_has_no_paragraphs(self):
        self.assertEqual(render("1. x\n2. y"), "<ol><li>x</li><li>y</li></ol>")

    def test_steps_section_is_one_list(self):
        out = render(STEPS)
        steps = items(out)
        self.assertEqual(len(steps), 5)
        self.assertTrue(steps[0].startswith("<p><strong>Start from an empty value,</strong>"))
        self.assertIn("<pre><code>", steps[2])
        self.assertIn("memcpy", steps[2])
        self.assertIn("\n\n", steps[2])      # the blank line inside the code block is kept
        self.assertEqual(steps[3].count("<p>"), 2)
        self.assertIn("<p>Copying every string would cost more than reading it.</p>", steps[3])
        self.assertTrue(out.endswith("</ol>\n<p>After the list.</p>"))
        self.assertNotIn("<pre>", out.split("</ol>")[1])

    def test_continuation_paragraph_belongs_to_its_item(self):
        steps = items(render("1. first\n\n   more about first\n2. second"))
        self.assertEqual(steps, ["<p>first</p>\n<p>more about first</p>", "<p>second</p>"])

    def test_code_block_in_an_item_keeps_every_line(self):
        md = "1. code:\n   ```\n   a\n\n- not an item\n# not a heading\n   ```\n2. next"
        steps = items(render(md))
        self.assertEqual(len(steps), 2)
        self.assertIn("a\n\n- not an item\n# not a heading</code></pre>", steps[0])
        self.assertEqual(steps[1], "next")     # a blank line inside code does not make the list loose

    def test_unindented_text_after_a_blank_line_ends_the_list(self):
        out = render("1. a\n\n2. b\n\nnot in the list\n\n```\ncode\n```")
        self.assertTrue(out.startswith("<ol><li><p>a</p></li><li><p>b</p></li></ol>\n<p>not in the list</p>"))
        self.assertTrue(out.endswith("<pre><code>code</code></pre>"))

    def test_nested_list_after_a_blank_line(self):
        out = render("- a\n\n  - a1\n  - a2\n\n- b")
        self.assertEqual(out.count("<ul>"), 2)
        self.assertIn("<ul><li>a1</li><li>a2</li></ul>", out)
        self.assertTrue(out.endswith("<li><p>b</p></li></ul>"))

    def test_other_kind_of_list_starts_a_new_one(self):
        out = render("1. a\n\n- b")
        self.assertEqual(out, "<ol><li>a</li></ol>\n<ul><li>b</li></ul>")

    def test_ordered_list_keeps_its_first_number(self):
        self.assertEqual(render("3. c\n\n4. d"), '<ol start="3"><li><p>c</p></li><li><p>d</p></li></ol>')
        self.assertTrue(render("1. a").startswith("<ol>"))

    def test_a_number_starting_a_wrapped_line_is_not_a_list(self):
        out = render("stored in one byte as fe would come back as\n254. Floats are assembled the same way.")
        self.assertEqual(out, "<p>stored in one byte as fe would come back as 254. Floats are assembled the same way.</p>")
        self.assertIn("<ol><li>x</li></ol>", render("text\n1. x"))      # 1. still starts a list
        self.assertIn("<ul><li>x</li></ul>", render("text\n- x"))
        self.assertIn('<ol start="254">', render("text\n\n254. x"))   # after a blank line it is a list


class SoftBreakTests(unittest.TestCase):
    """A paragraph's lines are where the source wrapped, not breaks: an inline span may run
    across them (the lines are joined with a space first, as CommonMark does)."""

    def test_spans_wrapped_across_lines_in_a_paragraph(self):
        out = render("the call\n`write_page(p,\nbuf)` returns, **once the\npage** is *on\ndisk*.")
        self.assertEqual(out, "<p>the call <code>write_page(p, buf)</code> returns, <strong>once the page</strong> "
                              "is <em>on disk</em>.</p>")
        self.assertNotIn("`", out)
        self.assertNotIn("*", out)

    def test_spans_wrapped_in_list_items(self):
        out = render("- a tight item with `a\n  span` and **bold\n  text**\n- next")
        self.assertEqual(items(out, "ul"), ["a tight item with <code>a span</code> and <strong>bold text</strong>", "next"])
        out = render("1. a loose item, `lazy\ncontinuation`\n\n2. **two\n   lines**")
        self.assertEqual(items(out), ["<p>a loose item, <code>lazy continuation</code></p>",
                                      "<p><strong>two lines</strong></p>"])

    def test_a_link_label_may_wrap(self):
        self.assertEqual(render("see [the page\ncache](01.02-x.md)", lambda h: "/t/db/01.02"),
                         '<p>see <a href="/t/db/01.02">the page cache</a></p>')

    def test_a_blank_line_still_ends_the_paragraph(self):
        out = render("an open `span\n\nnever closes` here")
        self.assertEqual(out, "<p>an open `span</p>\n<p>never closes` here</p>")

    def test_code_blocks_and_tables_keep_their_lines(self):
        out = render("text\n\n```\n`a\nb`\n**x\ny**\n```\n\n| a | b |\n|---|---|\n| `c` | **d** |\n| e | f |")
        self.assertIn("<pre><code>`a\nb`\n**x\ny**</code></pre>", out)
        self.assertIn("<td><code>c</code></td><td><strong>d</strong></td></tr><tr><td>e</td>", out)
        steps = items(render("1. code:\n   ```\n   x = `a\n   b`\n   ```\n2. next"))
        self.assertIn("x = `a\nb`</code></pre>", steps[0])

    def test_wrapped_lines_join_without_making_new_blocks(self):
        out = render("1. one\n\n2. two `wraps\n   here`\n\n3. three")
        self.assertEqual(len(items(out)), 3)                          # a loose list stays one list
        self.assertIn("<code>wraps here</code>", out)
        out = render("a sentence that wraps to\n2. a number, `not\na list`")
        self.assertEqual(out, "<p>a sentence that wraps to 2. a number, <code>not a list</code></p>")


def lesson(href):
    """resolve_link as a lesson page has it: a lesson's file becomes its page."""
    return "/t/x/01.02" if href.endswith(".md") else None


class InlineNestingTests(unittest.TestCase):
    """Code spans and links are set aside as placeholders while the rest of a line is read. One
    span inside another (code in a link's text) must come out whole, never as a placeholder."""

    def test_code_in_a_link_s_text(self):
        self.assertEqual(render("See [antirez's `kilo.c`, the whole scanner](https://example.com/x) and `plain`."),
                         '<p>See <a href="https://example.com/x">antirez&#x27;s <code>kilo.c</code>, the whole scanner</a>'
                         ' and <code>plain</code>.</p>')
        self.assertEqual(inline("[`a`](/u)"), '<a href="/u"><code>a</code></a>')
        self.assertEqual(inline("[`a` and `b`](01.02-x.md)", lesson),
                         '<a href="/t/x/01.02"><code>a</code> and <code>b</code></a>')

    def test_code_in_bold_and_emphasis(self):
        self.assertEqual(inline("**`a`** *`b`* _`c`_ __`d`__"),
                         "<strong><code>a</code></strong> <em><code>b</code></em> <em><code>c</code></em> "
                         "<strong><code>d</code></strong>")

    def test_bold_and_emphasis_in_a_link_s_text(self):
        self.assertEqual(inline("[**b** and *i*](/u)"), '<a href="/u"><strong>b</strong> and <em>i</em></a>')
        self.assertEqual(inline("[**`x`** and *`y`*](/u)"),
                         '<a href="/u"><strong><code>x</code></strong> and <em><code>y</code></em></a>')

    def test_a_link_in_bold_or_emphasis(self):
        self.assertEqual(inline("**[`x`](/u)** and *[`y` z](/v)*"),
                         '<strong><a href="/u"><code>x</code></a></strong> and <em><a href="/v"><code>y</code> z</a></em>')

    def test_in_every_block_that_reads_inline_spans(self):
        self.assertIn('<h2 id="see-a-u">See <a href="/u"><code>a</code></a></h2>', render("## See [`a`](/u)"))
        self.assertIn('<li><a href="/u"><code>a</code></a></li>', render("- [`a`](/u)\n- b"))
        self.assertIn('<td><a href="/u"><code>a</code></a></td>', render("| h |\n|---|\n| [`a`](/u) |"))
        self.assertIn('<blockquote><p><a href="/u"><code>a</code></a></p></blockquote>', render("> [`a`](/u)"))

    def test_text_that_looks_like_a_placeholder(self):
        # A placeholder is NUL, a number, NUL. The text's own NULs are dropped, so none can pose as one.
        self.assertEqual(inline("a\x000\x00b \x001\x00 [`c`](/u) \x00"), 'a0b 1 <a href="/u"><code>c</code></a> ')
        self.assertEqual(inline("[1`2`3](/0/1) `0` [`0` `1`](/2)"),
                         '<a href="/0/1">1<code>2</code>3</a> <code>0</code> <a href="/2"><code>0</code> <code>1</code></a>')
        self.assertEqual(inline("[x\x000\x00](/u\x00)"), '<a href="/u">x0</a>')
        many = " ".join(f"`{k}`" for k in range(12))          # the link's code span is number 12: two digits
        self.assertEqual(inline(many + " [`k`](/u)"),
                         " ".join(f"<code>{k}</code>" for k in range(12)) + ' <a href="/u"><code>k</code></a>')

    def test_unbalanced_backticks_and_brackets(self):
        self.assertEqual(inline("[a `b](/u) c"), '<a href="/u">a `b</a> c')                 # no code span: a link
        self.assertEqual(inline("[a `b](/u)` c"), "[a <code>b](/u)</code> c")               # the code span wins
        self.assertEqual(inline("a]](/u) [b"), "a]](/u) [b")
        self.assertEqual(inline("[a `b`](/u"), "[a <code>b</code>](/u")
        self.assertEqual(inline("`` [a](/u) ``"), "<code>[a](/u)</code>")

    def test_a_code_span_holding_link_syntax(self):
        self.assertEqual(inline("[a `](` b](/u)"), '<a href="/u">a <code>](</code> b</a>')
        self.assertEqual(inline("[`a[0]`](/u)"), '<a href="/u"><code>a[0]</code></a>')

    def test_a_code_span_in_the_url_is_text_not_a_link(self):
        seen = []
        out = inline("[x](/a`b`c) [y](/u \"a `t` title\")", lambda h: seen.append(h))
        self.assertEqual(out, '[x](/a<code>b</code>c) <a href="/u">y</a>')
        self.assertEqual(seen, ["/u"])                                   # no URL with a placeholder in it
        self.assertEqual(inline("[`a`](x.md)", lambda h: "/t/\x000\x00x"), '<a href="/t/0x"><code>a</code></a>')

    def test_html_in_code_spans_and_link_text_stays_text(self):
        out = inline('[<img src=x onerror=alert(1)> `<script>` say "`x`"](/u) `</a><b>`')
        self.assertEqual(out, '<a href="/u">&lt;img src=x onerror=alert(1)&gt; <code>&lt;script&gt;</code> '
                              'say &quot;<code>x</code>&quot;</a> <code>&lt;/a&gt;&lt;b&gt;</code>')

    def test_a_refused_link_keeps_its_text_and_code(self):
        for href in ("javascript:alert(1)", "//evil.example", "data:text/html,x"):
            out = inline(f"[`a` b]({href})")
            self.assertTrue(out.startswith("<code>a</code> b"), out)
            self.assertNotIn("href", out)

    def test_random_text_leaves_no_placeholder_and_no_raw_html(self):
        rng = random.Random(1)
        pieces = ["[", "]", "](", "](/u)", "(", ")", "`", "``", "*", "**", "_", " ", "a", "0", "12", "/u", "\x00",
                  "\x000\x00", "<b>", "</a>", "&", '"', "'", "javascript:", "#", "01.02-x.md"]
        tags = re.compile(r'</?(?:code|strong|em)>|<a href="[^"<>]*">|</a>')
        for _ in range(5000):
            text = "".join(rng.choice(pieces) for _ in range(rng.randint(1, 14)))
            out = inline(text, lesson)
            self.assertNotIn("\x00", out, text)
            rest = tags.sub("", out)
            self.assertNotIn("<", rest, text)
            self.assertNotIn(">", rest, text)
            for href in re.findall(r'href="([^"]*)"', out):
                self.assertFalse(href.lower().startswith(("javascript:", "//")), text)

    def test_ordinary_paragraphs_render_as_before(self):
        # Outputs of the renderer before code spans in links were fixed, byte for byte.
        for text, want in (
            ("Plain text with **bold**, *emphasis*, _under_, __strong__, snake_case_name and `code < b && c`.",
             "<p>Plain text with <strong>bold</strong>, <em>emphasis</em>, <em>under</em>, <strong>strong</strong>, "
             "snake_case_name and <code>code &lt; b &amp;&amp; c</code>.</p>"),
            ('A [link](https://e.com/?a=1&b=2 "title") and [a lesson](01.02-x.md), [**bold** text](/t/db) and [*it*](#frag).',
             '<p>A <a href="https://e.com/?a=1&amp;b=2">link</a> and <a href="/t/x/01.02">a lesson</a>, '
             '<a href="/t/db"><strong>bold</strong> text</a> and <a href="#frag"><em>it</em></a>.</p>'),
            ("Refused: [c](javascript:alert(1)) [d](//evil.example) [e](data:text/html,x) and "
             "<script>alert('x')</script> & \"q\".",
             "<p>Refused: c) d e and &lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; &amp; &quot;q&quot;.</p>"),
            ("Mixed `a` then **`b`** then *`c`* then `` d`e `` then a lone ` backtick and [ bracket ] (paren).",
             "<p>Mixed <code>a</code> then <strong><code>b</code></strong> then <em><code>c</code></em> then "
             "<code>d`e</code> then a lone ` backtick and [ bracket ] (paren).</p>"),
            ("Numbers 0 1 22 next to `x`1 and 2`y` and [1](/2) 3.",
             '<p>Numbers 0 1 22 next to <code>x</code>1 and 2<code>y</code> and <a href="/2">1</a> 3.</p>'),
        ):
            self.assertEqual(render(text, lesson), want)


class CommentTests(unittest.TestCase):
    """HTML comments, the authors' notes for ./learn verify, render as nothing anywhere, and are
    text like any other inside code."""

    def test_a_comment_on_lines_of_its_own_is_gone(self):
        self.assertEqual(render("a\n\n<!-- verify: session -->\n```\nout\n```"), "<p>a</p>\n<pre><code>out</code></pre>")
        out = render("before\n\n<!-- verify: session at=01.03\nlines 3-4 mixed\nvary 0x8 addr\n-->\n```\nx\n```\n\nafter")
        self.assertEqual(out, "<p>before</p>\n<pre><code>x</code></pre>\n<p>after</p>")
        self.assertNotIn("verify", out)
        self.assertNotIn("&lt;!--", out)

    def test_a_comment_inside_a_paragraph_leaves_one_paragraph(self):
        self.assertEqual(render("one\n<!-- verify: fact cmd='x' expect=59 -->\ntwo"), "<p>one two</p>")
        self.assertEqual(render("a <!-- note --> b"), "<p>a  b</p>")
        self.assertEqual(render("a <!-- starts here\nand ends -->b"), "<p>a b</p>")

    def test_comments_in_code_are_code(self):
        self.assertIn("&lt;!-- kept --&gt;", render("```\n<!-- kept -->\n```"))
        self.assertIn("<code>&lt;!-- span --&gt;</code>", render("see `<!-- span -->` here"))
        self.assertIn("&lt;!-- kept --&gt;", render("1. item\n   ```\n   <!-- kept -->\n   ```"))

    def test_comments_in_lists_and_quotes(self):
        out = render("1. step\n   <!-- verify: patch file=a.c\n   @block\n   -->\n   ```\n   x();\n   ```\n2. next")
        self.assertNotIn("verify", out)
        self.assertIn("<pre><code>x();</code></pre>", out)
        self.assertEqual(render("> quoted <!-- gone -->"), "<blockquote><p>quoted</p></blockquote>")


if __name__ == "__main__":
    unittest.main()
