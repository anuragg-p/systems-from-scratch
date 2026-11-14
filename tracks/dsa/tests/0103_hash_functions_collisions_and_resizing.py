"""01.03 Hash functions, collisions and resizing

On a text whose vocabulary keeps growing (data/gen.py text 100000: 14000 words or so), FNV-1a with
buckets that double finds a word in under two probes on average. Summing the bytes takes over ten,
with the buckets growing or not, because the sums of words are few; FNV-1a in 1024 buckets that
never grow takes over four. All four print the pipeline's counts, and the buckets double each time
the entries reach their number: at the end there are fewer than twice as many buckets as entries.
"""


def test(t):
    T = t.track
    fx = T.fixtures("freq")
    text = T.gen(t, "text", 100000)
    got = {}
    for name, args in (("fnv1a", []), ("sum", ["--hash=sum"]), ("sum fixed", ["--hash=sum", "--no-grow"]),
                       ("fnv1a fixed", ["--no-grow"])):
        r = T.run(t, "freq", ["--algo=table", "-n", "200"] + args + [text], env={"DS_STATS": "1"})
        want = fx.pipeline(t, text)[:200]
        t.check(fx.counts(r.out) == want, f"freq {' '.join(args)} differs from the pipeline")
        got[name] = T.stats(r.err)["table"]
    per = {k: v["probes"] / v["lookups"] for k, v in got.items()}
    t.check(per["fnv1a"] < 2, f"FNV-1a with resizing: under 2 probes a lookup, not {per['fnv1a']:.2f}: {got}")
    t.check(per["sum"] > 10 and per["sum fixed"] > 10, f"summed bytes: over 10 probes a lookup: {per}")
    t.check(per["fnv1a fixed"] > 4, f"1024 buckets for 14000 words: over 4 probes a lookup: {per}")
    s = got["fnv1a"]
    buckets = 1024 << s["resizes"]
    t.check(s["resizes"] >= 1 and buckets >= s["inserts"] and buckets < 2 * s["inserts"] + 2048,
            f"the buckets double as entries reach them: {s['inserts']} entries, {buckets} buckets: {s}")
    t.check(got["fnv1a fixed"]["resizes"] == 0 and got["sum fixed"]["resizes"] == 0, f"--no-grow: {got}")

    # FNV-1a spreads the anagrams summing the bytes cannot tell apart
    words = "stop pots tops opts post spot " * 50
    for args, most in (([], 1.0), (["--hash=sum"], 2.5)):
        r = T.run(t, "freq", ["--algo=table"] + args, input=words, env={"DS_STATS": "1"})
        s = T.stats(r.err)["table"]
        t.check((s["probes"] / s["lookups"] <= most) == (args == []),
                f"six anagrams with {args or 'fnv1a'}: {s['probes'] / s['lookups']:.2f} probes a lookup: {s}")
