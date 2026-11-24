"""09.02 GPT-2's tokenizer: the same ids as tiktoken

byte_symbols is GPT-2's table of the 256 bytes as printable characters (a space is U+0120); classes
holds exactly the code points unicodedata calls letters and numbers; split joins back to any text and
cuts as GPT-2's pattern does (against the regex module, when it is installed, on every character
this Python's Unicode has); a Tokenizer refuses merges that are not in order; data/fetch.py's
fetch_each resumes a dropped download and takes a range of bytes, against a server on this machine.
With GPT-2's files (python3 -m data.fetch gpt2; without them the rest is skipped, with a line that
says so): the same ids as tiktoken and as transformers' tokenizers, built from the same files (no
network), on all of Tiny Shakespeare and a large, awkward text: runs of spaces and line breaks,
contractions, digits, punctuation, combining marks, many scripts, emoji, characters of every
general category; every text decodes back to itself; and where the ids differ, it is a character
this Python's unicodedata does not know yet followed by a contraction, as NOTES.md explains. The
short run: the files' facts, the round trip, GPT-2 above 09.01's BPE in bytes per token on the
test text, and the cache faster than none.
"""


def test(t):
    T = t.track
    T.inside(t, __file__)
    if not T.need(t, "gpt2", skip=True):
        return
    out = T.inside(t, __file__, "with_data")
    print("      " + "\n      ".join(line for line in out.splitlines() if line.startswith("09.02")))
    r = T.experiment(t, "tokenizer", "repeats=1", "size=1024")
    t.check("50,257 symbols, 50,000 merges; the k-th merge makes symbol 256 + k (checked)" in r.out and
            "338,025 tokens, decoded the same: True" in r.out and "[15496, 995]" in r.out,
            f"the files' facts and the round trip:\n{r.out[:2500]}")
    line =[l for l in r.out.splitlines() if l.strip().startswith("test text")][0].split()
    t.check(float(line[2]) > float(line[3]) + 0.2, f"GPT-2 should take more bytes a token on the test text: {line}")
    slow, fast = T.value(r.out, r"without the cache: (\S+) s"), T.value(r.out, r"with +the cache: (\S+) s")
    t.check(fast < slow / 2, f"the cache should make encoding far faster: {slow} {fast}")


def inside(S):
    import json
    import os
    import re
    import tempfile
    import unicodedata
    import numpy as np
    from tokens import gpt2

    symbols = gpt2.byte_symbols()
    assert len(set(symbols)) == 256 and symbols[32] == "Ġ" and symbols[10] == "Ċ" and symbols[ord("a")] == "a"
    assert all(c.isprintable() and not c.isspace() for c in symbols), "every byte written as a printable character"
    assert symbols[0] == "Ā" and symbols[0xAD] == chr(256 + 67) and symbols[0xE9] == "\xe9"

    c = gpt2.classes()
    letter, number = re.compile(f"[{c['L']}]"), re.compile(f"[{c['N']}]")
    for i in range(0x110000):
        if 0xD800 <= i <= 0xDFFF:
            continue
        kind = unicodedata.category(chr(i))[0]
        assert bool(letter.match(chr(i))) == (kind == "L") and bool(number.match(chr(i))) == (kind == "N"), hex(i)
    space = re.compile(f"[{gpt2.SPACE}]")
    white = [i for i in range(0x110000) if space.match(chr(i))]
    assert white == [i for i in range(0x110000) if chr(i).isspace() and not 0x1C <= i <= 0x1F] and len(white) == 25

    assert gpt2.split("Hello world! It's 2019,  isn't it?\n\n  x") == [
        "Hello", " world", "!", " It", "'s", " 2019", ",", " ", " isn", "'t", " it", "?", "\n\n ", " x"]
    assert gpt2.split("IT'S  ") == ["IT", "'", "S", "  "] and gpt2.split("a\x1cb") == ["a", "\x1c", "b"]
    assert gpt2.split("x \x1c y") == ["x", " \x1c", " y"], "0x1c is not a space to GPT-2's pattern"
    pool, by = S.unicode_pool()
    known = [ch for ch in pool if unicodedata.category(ch) != "Cn"]
    rng = np.random.default_rng(0)
    texts = S.unicode_strings(rng, 3000, 60, known) + corpus()
    for s in texts:
        assert "".join(gpt2.split(s)) == s, ascii(s)
    try:
        import regex
    except ImportError:
        print("09.02 the regex module is not installed: split is not compared with GPT-2's own pattern")
    else:
        theirs = regex.compile(r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+""")
        for s in texts:
            assert gpt2.split(s) == theirs.findall(s), ascii(s)

    with tempfile.TemporaryDirectory() as d:
        vocab = {ch: i for i, ch in enumerate(symbols)}
        vocab.update({"ab": 256, "abc": 257})
        with open(os.path.join(d, "vocab.json"), "w", encoding="utf-8") as f:
            json.dump(vocab, f)
        for name, lines in (("good.txt", ["a b", "ab c"]), ("bad.txt", ["ab c", "a b"])):
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write("#version: 0.2\n" + "\n".join(lines) + "\n")
        tok = gpt2.Tokenizer(os.path.join(d, "vocab.json"), os.path.join(d, "good.txt"))
        ids = tok.encode("abc abcab ab")
        assert ids == [257, vocab["Ġ"], 257, 256, vocab["Ġ"], 256], ids
        assert tok.decode(ids) == "abc abcab ab" and tok.encode("abc", cache=False) == [257]
        try:
            gpt2.Tokenizer(os.path.join(d, "vocab.json"), os.path.join(d, "bad.txt"))
            raise AssertionError("merges out of order should be refused")
        except (ValueError, KeyError):
            pass

    fetch_each_resumes()


def corpus():
    """Built strings the tokenizer must cut and merge as GPT-2's does: runs of spaces and line breaks, contractions,
    digits, punctuation runs, combining marks, many scripts, emoji (non-ASCII as escapes: this file stays ASCII)."""
    runs = [" " * n for n in range(1, 13)] + ["\n" * n for n in range(1, 6)] + [
        " \n \n  ", "\t\t x", "\r\n", "a\r\nb", "  \t\n  y", "x  y", "　　z", "a   b", "end   "]
    runs += [f"a{' ' * n}b" for n in range(1, 9)] + [f"{' ' * n}word" for n in range(1, 9)] + [
        f"word{' ' * n}" for n in range(1, 9)] + [f"x{chr(10) * n}{' ' * m}y" for n in range(1, 4) for m in range(4)]
    contractions = ["it's", "IT'S", "you're", "we've", "I'm", "they'll", "he'd", "don't", "'s", "''s", "'st", " 's",
                    "x 's", "o'clock", "rock 'n' roll", "'''", "'ll'", "it’s", "y'all'd've", "'S'", " ''", "'1"]
    digits = ["1", "12", "123", "1234567890" * 3, " 2019", "3.14159", "1,000,000", "0x1F", "007", " 1 2 3",
              "١٢٣", "ⅣⅤ", "½ ²", "x2y3", "A1B2", "１２"]
    marks = ["!!!", "...", "?!?!", "---", "***", " ...", "\"'(", "<<>>", "@#$%^&*()_+-=[]{}|;:,./<>?`~", " $5",
             "«»", "——", "…", " !x", "!x!"]
    combining = ["é", "à́̂", "́", " ́", "ño", "각",
                 "ẍ̈̈", "क्ष"]
    scripts = ["καλημέρα", "привет",
               "שלום", "مرحبا", "नमस्ते",
               "สวัสดี", "你好，世界", "こんにちは",
               "안녕하세요", "ሰላም", "გამარჯობა",
               "Բարեւ", "வணக்கம்",
               "নমস্কার", "ᠠᠡᠢ", "\U00010400\U00010401",
               "\U0001d400\U0001d401 math", "\U00020000\U0002a6d6"]
    emoji = ["\U0001f600", "\U0001f44b\U0001f3fd", "\U0001f468‍\U0001f469‍\U0001f467", "\U0001f1ec\U0001f1e7",
             "1️⃣", "❤️", "a\U0001f600b", " \U0001f600 ", "\U0001f600'"]
    mixed = [a + b for a in contractions[:6] + scripts[:4] + emoji[:3] for b in digits[:4] + marks[:4] + runs[:3]]
    return runs + contractions + digits + marks + combining + scripts + emoji + mixed


def fetch_each_resumes():
    """data/fetch.py's fetch_each, against a server on this machine that serves ranges of bytes: a download cut
    short is carried on from where it stopped, a range of a larger file is fetched and checked, a wrong file is not
    kept."""
    import hashlib
    import http.server
    import os
    import tempfile
    import threading
    from data import fetch

    blob = bytes(range(256)) * 40
    seen = []

    class Ranges(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            first, last = (int(x) for x in self.headers["Range"].split("=")[1].split("-"))
            seen.append((first, last))
            body = blob[first:min(last + 1, first + 3000)]           # at most 3000 bytes a request: then it "drops"
            self.send_response(206)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Ranges)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    old = os.environ.get("LEARN_CACHE")
    try:
        with tempfile.TemporaryDirectory() as d:
            os.environ["LEARN_CACHE"] = d
            whole, part = blob[:7000], blob[1000:6000]
            fetch.DATASETS["test-ranges"] = {
                "url": f"http://127.0.0.1:{server.server_port}/", "each": True,
                "files": {"whole.bin": (len(whole), hashlib.sha256(whole).hexdigest()),
                          "part.bin": (len(part), hashlib.sha256(part).hexdigest())},
                "ranges": {"part.bin": ("big.bin", 1000)}}
            fetch.fetch("test-ranges")
            for name, want in (("whole.bin", whole), ("part.bin", part)):
                with open(fetch.path("test-ranges", name), "rb") as f:
                    assert f.read() == want, name
            assert seen == [(0, 6999), (3000, 6999), (6000, 6999), (1000, 5999), (4000, 5999)], seen
            assert fetch.missing("test-ranges") == []
            fetch.DATASETS["test-ranges"]["files"]["wrong.bin"] = (100, "0" * 64)
            try:
                fetch.fetch("test-ranges")
                raise AssertionError("a file with the wrong SHA-256 should not be kept")
            except SystemExit as e:
                assert "nothing kept" in str(e) and not os.path.exists(fetch.path("test-ranges", "wrong.bin"))
    finally:
        server.shutdown()
        del fetch.DATASETS["test-ranges"]
        if old is None:
            os.environ.pop("LEARN_CACHE", None)
        else:
            os.environ["LEARN_CACHE"] = old


def with_data(S):
    import os
    import unicodedata
    import warnings
    import numpy as np
    from data import fetch, shakespeare
    from tokens import gpt2

    warnings.filterwarnings("ignore")
    tok = gpt2.load()
    vocab, merges = fetch.path("gpt2", "vocab.json"), fetch.path("gpt2", "merges.txt")
    references = {}
    try:
        import tiktoken
        from tiktoken.load import data_gym_to_mergeable_bpe_ranks
        from tiktoken_ext import openai_public
        pattern = getattr(openai_public, "r50k_pat_str",
                          r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+""")
        enc = tiktoken.Encoding("gpt2-from-the-fetched-files", pat_str=pattern,
                                mergeable_ranks=data_gym_to_mergeable_bpe_ranks(merges, vocab), special_tokens={})
        references[f"tiktoken {tiktoken.__version__}"] = enc.encode_ordinary
    except ImportError:
        pass
    try:
        import transformers
        fast = transformers.GPT2TokenizerFast(vocab_file=vocab, merges_file=merges)
        references[f"transformers {transformers.__version__} GPT2TokenizerFast"] = fast.encode
        try:
            import regex  # noqa: F401: the slow tokenizer's pattern needs it
            slow = transformers.GPT2Tokenizer(vocab_file=vocab, merges_file=merges)
            references[f"transformers {transformers.__version__} GPT2Tokenizer"] = slow.encode
        except ImportError:
            pass
    except ImportError:
        pass
    assert references, "no reference: neither tiktoken nor transformers is installed"
    print(f"09.02 compared with {', '.join(references)}")

    text = shakespeare.load()
    ids = tok.encode(text)
    assert len(ids) == 338025 and tok.decode(ids) == text
    pool, _ = S.unicode_pool()
    known = [ch for ch in pool if unicodedata.category(ch) != "Cn" or 0x40000 <= ord(ch) < 0xE0000]
    rng = np.random.default_rng(1)
    texts = corpus() + S.unicode_strings(rng, 3000, 60, known) + [
        ctx.format(ch) for ch in known for ctx in ("x{}", "{}x", " {}", "{}'s", "1{}", "{}1", "'{}", " {}!")]
    for name, encode in references.items():
        assert encode(text) == ids, f"Tiny Shakespeare: other ids than {name}"
        for s in texts:
            assert tok.encode(s) == encode(s), f"{ascii(s)}: {tok.encode(s)}, {name} {encode(s)}"
    for s in texts:
        assert tok.decode(tok.encode(s)) == s, ascii(s)

    # Characters this Python's unicodedata calls unassigned (Cn), in the planes where Unicode has assigned
    # characters, each before a contraction. Where a reference's ids differ, the reference must have cut the
    # character from "'s" (to it a letter or a number, from a later Unicode) and this tokenizer cut it with the "'".
    unassigned = [chr(i) for i in range(0x40000) if not 0xD800 <= i <= 0xDFFF and unicodedata.category(chr(i)) == "Cn"]
    apostrophe_s = tok.encode("'s")
    for name, encode in references.items():
        differ = []
        for k in range(0, len(unassigned), 2000):
            chunk = unassigned[k:k + 2000]
            if tok.encode("\n".join(ch + "'s" for ch in chunk)) == encode("\n".join(ch + "'s" for ch in chunk)):
                continue
            differ += [ch for ch in chunk if tok.encode(ch + "'s") != encode(ch + "'s")]
        for ch in differ:
            assert encode(ch + "'s") == tok.encode(ch) + apostrophe_s, f"{name}: U+{ord(ch):04X} differs another way"
        print(f"09.02 {name}: {len(differ):,} of {len(unassigned):,} characters unassigned in this Python's Unicode "
              f"({unicodedata.unidata_version}) give other ids before 's"
              + (f", U+{ord(differ[0]):04X} to U+{ord(differ[-1]):04X}" if differ else ""))
