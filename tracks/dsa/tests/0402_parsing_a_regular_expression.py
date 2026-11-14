"""04.02 Parsing a regular expression

grep -E, parsing the pattern into a tree and matching it by backtracking, prints the system's grep -E
lines for a table of expressions on the book and on the project's own source, with -n -c -v -i, and
agrees with Python's re on random expressions of literals, ., classes, * + ?, | and anchors, with and
without -i. A pattern that is not one is an ordinary error, as it is for the system's grep. And the
backtracker is exponential: a?^n a^n against n a's takes about four times the steps for each two more
a's, while a line too long for its stack is an ordinary error, not a crash.
"""


def test(t):
    T = t.track
    fx = T.fixtures("grep")
    fx.table(t, "-E", "backtrack")
    fx.oracle(t, "backtrack", 150, seed=1)
    fx.oracle(t, "backtrack", 60, seed=2, args=["-i"])

    # without -E or -F, the pattern is an extended regular expression too, as for grep -E (the
    # system's grep without -E reads a basic one, where ( | and + stand for themselves)
    book = T.data(t, "book.txt")
    ours = T.run(t, "grep", ["--algo=backtrack", "-n", "(Holmes|Watson), ", book])
    T.same(t, ours.out, T.system(t, ["grep", "-E", "-n", "(Holmes|Watson), ", book]).out, "grep without -E")

    # bad patterns: an error from both (status 2, nothing printed); and what this grep leaves out
    for pat in ("(a", "a(b|c", "[a", "[^", "a\\", "[z-a]", "[[:nope:]]"):
        ours = T.run(t, "grep", ["-E", "--algo=backtrack", pat], input="a\n", check=False)
        theirs = T.system(t, ["grep", "-E", pat], input="a\n", check=False)
        t.check(ours.rc == 2 and theirs.rc == 2 and ours.out == "" and ours.err.startswith("grep: "),
                f"grep -E {pat!r}: an error, as the system's (exit {theirs.rc}):\n{ours}")
    for pat, words in (("a{2}", "intervals"), ("\\w", "not supported"), ("[[.a.]]", "not supported"),
                       ("*a", "nothing before it"), ("a|+b", "nothing before it"), ("^*", "cannot be repeated")):
        r = T.run(t, "grep", ["-E", pat], input="a\n", check=False)
        t.check(r.rc == 2 and words in r.err, f"grep -E {pat!r}: an ordinary error:\n{r}")

    # the tree: one node for each byte, anchor, operator and sequence step
    r = T.run(t, "grep", ["-E", "--algo=backtrack", "ab|c*"], input="x\n", env={"DS_STATS": "1"}, check=False)
    t.check(T.stats(r.err)["regex"]["nodes"] == 6, f"ab|c* is ALT(CAT(a, b), STAR(c)): 6 nodes:\n{r.err}")

    # exponential: each two more a's, about four times the steps
    steps = []
    for n in (8, 10, 12, 14, 16):
        pat, line = fx.expo(n)
        r = T.run(t, "grep", ["-E", "--algo=backtrack", pat], input=line + "\n", env={"DS_STATS": "1"})
        b = T.stats(r.err)["backtrack"]
        t.check(r.out == line + "\n" and b["deepest"] <= 8 * n, f"a?^{n}a^{n} matches {n} a's: {b}")
        steps.append(b["steps"])
    for a, b in zip(steps, steps[1:]):
        t.check(3.5 * a < b < 5 * a, f"two more a's should take about four times the steps: {steps}")
    t.check(steps[-1] > 500000, f"a?^16a^16 takes over half a million steps: {steps}")

    # the stack: a line too long to backtrack over is an ordinary error
    r = T.run(t, "grep", ["-E", "--algo=backtrack", "a*b"], input="a" * 30000 + "\n", check=False)
    t.check(r.rc == 2 and "calls deep" in r.err, f"a*b on 30000 a's: an error, not a crash:\n{r}")
