"""Tests for lists in the markdown renderer: loose lists, and the paragraphs and code blocks an
item holds."""

import re
import unittest

from harness.web.markdown import render

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
