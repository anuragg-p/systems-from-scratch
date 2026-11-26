"""00.01 A first function, and the plain version you trust

rng_u32 and rng_f32 are llama2.c's xorshift64* bit for bit: the reference values read from its
run.c for seeds 1, 42 and 1234 (RESEARCH.md 1.1), and the generator written again in Python for
many more; the seed is the state, and state 0 stays 0. rng_fill gives 2 * f - 1. add equals
add_ref bit for bit for every n from 0 to 67 (every tail length) and on long arrays, and writes
nothing outside out. wb show prints n, the seed and the first four values of a, b and add(a, b);
-s 0 is refused with the reason, and every bad number with status 2. Every source compiles with
-std=c11 -Wall -Wextra -pedantic -Werror.
"""

# llama2.c's random_u32 and random_f32 (run.c at commit 350e04fe), as RESEARCH.md records them.
LLAMA2C = {
    1: ([1206177355, 2882512552, 3117485455, 1303648416],
        ["0.280835032", "0.671137214", "0.725846112", "0.303529263"]),
    42: ([1456360119, 3359763283, 3393612768, 4054632243],
         ["0.339085221", "0.782255828", "0.790136993", "0.944042623"]),
    1234: ([3159758022, 1306163061, 1764681998, 1393191135],
           ["0.735688448", "0.304114759", "0.410872042", "0.324377537"]),
}

SEEDS = [1, 2, 3, 7, 42, 1003, 1234, 2 ** 31 - 1, 2 ** 32 - 1, 2 ** 32, 2 ** 63, 2 ** 64 - 1]


def test(t):
    tr = t.track

    # The generator against llama2.c's own outputs, and against the Python version.
    cases = [(s, 4) for s in LLAMA2C] + [(s, 50) for s in SEEDS] + [(0, 3)]
    lines = tr.driver(t, "rng_driver", "".join(f"{s} {c}\n" for s, c in cases))
    t.check(len(lines) == 3 * len(cases), f"rng_driver printed {len(lines)} lines, not {3 * len(cases)}")
    for i, (seed, count) in enumerate(cases):
        u32 = [int(w) for w in lines[3 * i].split()[1:]]
        f32 = tr.floats(lines[3 * i + 1].split()[1:])
        fill = tr.floats(lines[3 * i + 2].split()[1:])
        t.check(u32 == tr.rng_u32s(seed, count), f"rng_u32 from state {seed}: {u32[:6]}..., "
                                                  f"not {tr.rng_u32s(seed, count)[:6]}...")
        t.check(f32 == tr.rng_f32s(seed, count), f"rng_f32 from state {seed}: {f32[:4]}..., "
                                                  f"not {tr.rng_f32s(seed, count)[:4]}...")
        t.check(fill == tr.rng_fill(seed, count), f"rng_fill with seed {seed}: {fill[:4]}..., "
                                                   f"not {tr.rng_fill(seed, count)[:4]}...")
        t.check(all(0 <= f < 1 for f in f32) and all(-1 <= x < 1 for x in fill),
                f"seed {seed}: a number out of range: {min(fill)} {max(fill)}")
        if seed in LLAMA2C:
            want_u, want_f = LLAMA2C[seed]
            t.check(u32[:4] == want_u, f"seed {seed}: rng_u32 gives {u32[:4]}, llama2.c's random_u32 {want_u}")
            t.check([f"{f:.9g}" for f in f32[:4]] == want_f,
                    f"seed {seed}: rng_f32 gives {[f'{f:.9g}' for f in f32[:4]]}, llama2.c's random_f32 {want_f}")
    t.check(lines[-3:] == ["u32 0 0 0", "f32 0x0p+0 0x0p+0 0x0p+0", "fill -0x1p+0 -0x1p+0 -0x1p+0"],
            f"state 0 is the trap: it stays 0, every number 0 (and rng_fill's -1): {lines[-3:]}")

    # add against add_ref: every tail length, and long arrays; canaries either side.
    ns = [(n, 1) for n in range(68)] + [(1000, 3), (1003, 5), (4096, 2 ** 32 - 1), (1000003, 11)]
    got = tr.driver(t, "add_driver", "".join(f"{n} {s}\n" for n, s in ns))
    bad = [l for l in got if not l.startswith("ok ")]
    t.check(len(got) == len(ns) and not bad, f"add against add_ref: {bad[:5] or got[-3:]}")

    # wb show, value for value against the Python generator.
    for n, seed in ((1003, 1), (1003, 42), (2, 1234), (1, 7), (4, 99), (5, 4294967295)):
        st, out, err = tr.prog(t, "wb", ["show", "-n", str(n), "-s", str(seed)])
        want = tr.show_text(n, seed)
        t.check((st, out, err) == (0, want, ""), f"wb show -n {n} -s {seed}:\n{out}{err}\nnot:\n{want}")
    t.check(tr.prog(t, "wb", ["show"]) == (0, tr.show_text(1003, 1), ""), "wb show: n 1003 and seed 1")
    t.check(tr.prog(t, "wb", ["show", "-s", "7", "-n", "3"]) == (0, tr.show_text(3, 7), ""),
            "the options in either order")

    # A seed of 0 is refused, with the reason; so is every number out of range.
    st, out, err = tr.prog(t, "wb", ["show", "-s", "0"])
    t.check((st, out) == (2, "") and err == ("wb: -s 0: xorshift's state 0 never changes, so every number "
                                             "would be the same; a seed is 1 to 4294967295\n"),
            f"wb show -s 0: {st} {err!r}")
    for argv, msg in ((["-n", "0"], "-n wants a whole number from 1 to 268435456, not '0'"),
                      (["-n", "268435457"], "-n wants a whole number from 1 to 268435456, not '268435457'"),
                      (["-n", "12x"], "-n wants a whole number from 1 to 268435456, not '12x'"),
                      (["-n", "-5"], "-n wants a whole number from 1 to 268435456, not '-5'"),
                      (["-n", ""], "-n wants a whole number from 1 to 268435456, not ''"),
                      (["-s", "4294967296"], "-s wants a whole number from 1 to 4294967295, not '4294967296'"),
                      (["-s", "99999999999999999999999"],
                       "-s wants a whole number from 1 to 4294967295, not '99999999999999999999999'"),
                      (["-s", " 5"], "-s wants a whole number from 1 to 4294967295, not ' 5'"),
                      (["-s", "00"], "-s wants a whole number from 1 to 4294967295, not '00'")):
        st, out, err = tr.prog(t, "wb", ["show"] + argv)
        t.check((st, out, err) == (2, "", f"wb: {msg}\n"), f"wb show {' '.join(argv)}: {st} {err!r}")
    for argv in ([], ["shw"], ["show", "-n"], ["show", "-x", "1"], ["show", "5"]):
        st, out, err = tr.prog(t, "wb", argv)
        t.check(st == 2 and out == "" and err.startswith("usage: wb show [-n N] [-s SEED]\n"),
                f"wb {' '.join(argv)}: {st} {err!r}")

    said = tr.warnings(t)
    t.check(not said, f"the sources are not warning-free under -Werror:\n{said}")
