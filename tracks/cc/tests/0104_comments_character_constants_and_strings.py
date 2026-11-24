"""01.04 Comments, character constants and strings

The scanner skips // and /* */ comments (an unclosed one is an error);
reads a character constant as a number, with every escape C has (\\a \\b \\t
\\n \\v \\f \\r \\\\ \\' \\" \\?, octal and hex), and a string literal as a
token holding its decoded bytes; and reads numbers in hexadecimal (0x),
octal (0) and binary (0b). Unknown escapes, escapes past 255 and character
constants past 127 are errors, for now; so is anything but one character
between single quotes.
"""

ESCAPES = [("\\a", 7), ("\\b", 8), ("\\t", 9), ("\\n", 10), ("\\v", 11), ("\\f", 12), ("\\r", 13),
           ("\\\\", 92), ("\\'", 39), ('\\"', 34), ("\\?", 63), ("\\0", 0), ("\\7", 7), ("\\101", 65),
           ("\\177", 127), ("\\x41", 65), ("\\x7f", 127), ("\\x7F", 127), ("\\x0", 0), ("\\x00000041", 65),
           ('"', 34), ("a", 97), (" ", 32), ("~", 126)]


def test(t):
    tr = t.track
    got = [repr(x) for x in tr.tokens(t, "/* a comment */ \"a\\tb\" '\\n' 0x1F 017 0b101 // the end\n")]
    want = ['1:17 str "a\\tb" 3', "1:24 num '\\n' 10", "1:29 num 0x1F 31", "1:34 num 017 15",
            "1:38 num 0b101 5", "1:54 eof"]
    t.check(got == want, f"--tokens:\n{got}\nnot\n{want}")
    # Lines go on being counted through a comment.
    got = [repr(x) for x in tr.tokens(t, "1 /* one\ntwo\n three */ + // four\n2")]
    t.check(got == ["1:1 num 1 1", "3:11 punct +", "4:1 num 2 2", "4:2 eof"], f"through comments: {got}")
    got = [repr(x) for x in tr.tokens(t, "/**/1/*/ */+/***/2//")]
    t.check(got == ["1:5 num 1 1", "1:12 punct +", "1:18 num 2 2", "1:21 eof"], f"comments run together: {got}")

    # Every escape, as a token and as a value (gcc agrees through value()).
    for text, n in ESCAPES:
        toks = tr.tokens(t, f"'{text}'")
        t.check((toks[0].kind, toks[0].value, toks[0].text) == ("num", n, f"'{text}'"),
                f"'{text}' should be {n}: {toks[0]!r}")
    tr.value(t, "'a' + '\\n' - '\\x41' + '\\101'", 97 + 10)
    tr.value(t, "'\\\\' - '\\'' - '\\\"' - '\\?'", 92 - 39 - 34 - 63)

    # Strings: their bytes decoded, an embedded '\0' too.
    for text, n in (('"a\\tb"', 3), ('""', 0), ('"a\\0b"', 3), ('"\\x41\\102C"', 3), ('"// not a comment"', 16),
                    ('"/* nor this"', 11), ('"\\"q\\""', 3), ('"it\'s"', 4)):
        toks = tr.tokens(t, text)
        t.check((toks[0].kind, toks[0].text, toks[0].value, toks[1].kind) == ("str", text, n, "eof"),
                f"{text}: {toks}")

    # Numbers in four bases; gcc reads them the same.
    tr.value(t, "0x1F + 017 + 0b101", 51)
    tr.value(t, "0X1f + 0B11 + 0 + 00 + 0x0", 34)
    tr.value(t, "0x7fffffff - 2147483647", 0)
    tr.value(t, "010 - 8", 0)

    for src, msg, col in (("1 /* no end", "unclosed block comment", 3),
                          ("/* /* */ */", "expected an expression", 10),
                          ('"no end', "unclosed string literal", 1),
                          ('1 + "no end\n"', "unclosed string literal", 5),
                          ("'a", "unclosed character constant", 1),
                          ("'", "unclosed character constant", 1),
                          ("''", "empty character constant", 1),
                          ("'ab'", "a character constant holds one character", 1),
                          ("'\\q'", "unknown escape sequence", 2),
                          ("'\\e'", "unknown escape sequence", 2),
                          ("'\\x'", "invalid hex escape sequence", 4),
                          ("'\\x100'", "escape sequence out of range", 2),
                          ('"\\400"', "escape sequence out of range", 2),
                          ("'\\xff'", "a character constant above 127 is not supported yet", 1),
                          ("'\\200'", "a character constant above 127 is not supported yet", 1),
                          ("08", "invalid numeric constant", 1),
                          ("0x", "invalid numeric constant", 1),
                          ("0b2", "invalid numeric constant", 1),
                          ("0x1g", "invalid numeric constant", 1)):
        e = tr.error(t, src)
        t.check((e.msg, e.col) == (msg, col), f"{src!r}: {e!r}, not {msg!r} at column {col}")
    # A string is a token, but not yet an expression.
    e = tr.error(t, '"abc"')
    t.check(e.msg == "expected an expression", f"a string: {e!r}")
