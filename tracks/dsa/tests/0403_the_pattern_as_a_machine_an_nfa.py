"""04.03 The pattern as a machine: an NFA

grep -E --algo=nfa, the expression compiled by Thompson's construction and run in every state at
once, prints the system's grep -E lines for the table, and agrees with Python's re on random
expressions. It reads each byte of a line once and never holds a state twice: on a?^n a^n against n
a's it reads n bytes with at most the machine's states live, where backtracking takes 2^n steps; and
"lines made only of words and spaces", which backtracking cannot finish on the book, takes it one
pass.
"""


def test(t):
    T = t.track
    fx = T.fixtures("grep")
    fx.table(t, "-E", "nfa")
    fx.oracle(t, "nfa", 150, seed=3)
    fx.oracle(t, "nfa", 60, seed=4, args=["-i"])

    # the machine: one state for each byte, anchor and choice, and one to match
    r = T.run(t, "grep", ["-E", "--algo=nfa", "ab|c*"], input="x\n", env={"DS_STATS": "1"})
    t.check(T.stats(r.err)["nfa"]["states"] == 6, f"ab|c*: a, b, c, a split for | and one for *, match:\n{r.err}")

    # a?^n a^n: each byte once, the live states never more than the machine's
    for n in (20, 40):
        pat, line = fx.expo(n)
        r = T.run(t, "grep", ["-E", "--algo=nfa", pat], input=line + "\n", env={"DS_STATS": "1"})
        s = T.stats(r.err)["nfa"]
        t.check(r.out == line + "\n", f"a?^{n}a^{n} matches {n} a's")
        t.check(s["examined"] == n and s["states"] == 3 * n + 1 and s["peak"] <= s["states"],
                f"{n} bytes read once, by a machine of 3n+1 states, never all of them live: {s}")
        t.check(s["live"] <= (n + 1) * s["peak"], f"the work is the live states, byte by byte: {s}")
    pat, line = fx.expo(20)
    b = T.stats(T.run(t, "grep", ["-E", "--algo=backtrack", pat], input=line + "\n", env={"DS_STATS": "1"}).err)
    s = T.stats(T.run(t, "grep", ["-E", "--algo=nfa", pat], input=line + "\n", env={"DS_STATS": "1"}).err)
    t.check(b["backtrack"]["steps"] > 10000 * s["nfa"]["live"],
            f"a?^20a^20: backtracking takes over ten thousand times the NFA's work: {b} {s}")

    # the book, and a pattern that hangs the backtracker on it: one pass, every byte once at most
    book = T.data(t, "book.txt")
    r = fx.check(t, ["-E", "-c", "^([A-Za-z]+ ?)*$"], [book], algo="nfa")
    s = T.stats(r.err)
    t.check(s["nfa"]["examined"] <= s["grep"]["bytes"] and s["nfa"]["peak"] <= s["nfa"]["states"],
            f"each byte of the book read at most once: {s}")
