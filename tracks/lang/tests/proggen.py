"""Random programs of chapter 1's language, and a reference that runs them.

    parse(text)             the program's statements, from its text; raises Error on a syntax
                            error or a name used before the text gives it a value (the static rule)
    run(prog, text_in, limit=200000)
                            (how it stopped, what it printed): how is "ok", "no value", "division
                            by zero", "overflow division" (the most negative number by -1, which
                            gives itself, but C leaves undefined), "no more input", "not a number"
                            or "steps" (more than limit statements and conditions)
    evaluate(text, text_in) parse and run: (how, output)
    generate(rng)           (program text, input text): a random program that always stops, written
                            one statement a line, with comments, blank lines and indentation
    sample(seed, n)         n (text, input, output) whose run ends "ok": every way must agree on them

The reference is written apart from the C code, to be a second opinion: a scanner by regular
expression, a parser by recursion, Python's integers wrapped to 64 bits. The generator keeps to
what every way can take: loops counted by a variable of their own, names that are not C's
keywords, no "--" (C's decrement) and no leading zeros (C's octal), expressions shallow enough
for t0 to t6. A program whose run divides by zero or reads past its input is not kept.
"""

import random
import re

KEYWORDS = {"read", "write", "if", "then", "else", "end", "while", "do"}
TOKEN = re.compile(r"\s*(?:(#[^\n]*)|([A-Za-z_]\w*)|(\d+)|(:=|==|!=|<=|>=|[<>+\-*/()]))")
MIN, MAX = -2 ** 63, 2 ** 63 - 1


class Error(Exception):
    pass


def wrap(n):
    return (n - MIN) % 2 ** 64 + MIN


def tokens(text):
    out, pos = [], 0
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos == len(text):
            return out + [("eof", "")]
        m = TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise Error(f"unexpected character {text[pos]!r}")
        pos = m.end()
        if m.group(1):
            continue
        if m.group(2):
            out.append(("keyword" if m.group(2) in KEYWORDS else "name", m.group(2)))
        elif m.group(3):
            if int(m.group(3)) > MAX:
                raise Error("number too large")
            out.append(("number", m.group(3)))
        else:
            out.append(("op", m.group(4)))


def parse(text):
    """Statements: ("read", x) ("write", e) (":=", x, e) ("if", c, then, else) ("while", c, body);
    expressions: ("num", n) ("var", x) ("neg", e) (op, a, b); conditions: (cmp, a, b)."""
    toks = tokens(text)
    pos = 0
    given = set()

    def peek():
        return toks[pos]

    def take(text=None):
        nonlocal pos
        t = toks[pos]
        if text is not None and t[1] != text:
            raise Error(f"expected {text!r}, not {t[1]!r}")
        pos += 1
        return t

    def factor():
        kind, t = take()
        if kind == "number":
            return ("num", int(t))
        if kind == "name":
            if t not in given:
                raise Error(f"{t} is used before anything gives it a value")
            return ("var", t)
        if t == "(":
            e = expr()
            take(")")
            return e
        if t == "-":
            return ("neg", factor())
        raise Error(f"expected a number, a name or '(', not {t!r}")

    def chain(sub, ops):
        e = sub()
        while peek()[1] in ops and peek()[0] == "op":
            op = take()[1]
            e = (op, e, sub())
        return e

    def term():
        return chain(factor, ("*", "/"))

    def expr():
        return chain(term, ("+", "-"))

    def cond():
        a = expr()
        op = take()[1]
        if op not in ("==", "!=", "<", ">", "<=", ">="):
            raise Error("expected a comparison")
        return (op, a, expr())

    def block():
        out = []
        while peek()[0] == "name" or peek()[1] in ("read", "write", "if", "while"):
            out.append(stmt())
        return out

    def stmt():
        kind, t = take()
        if kind == "name":
            take(":=")
            e = expr()
            given.add(t)
            return (":=", t, e)
        if t == "read":
            kind, x = take()
            if kind != "name":
                raise Error("expected a name")
            given.add(x)
            return ("read", x)
        if t == "write":
            return ("write", expr())
        if t == "if":
            c = cond()
            take("then")
            then, els = block(), []
            if peek()[1] == "else":
                take()
                els = block()
            take("end")
            return ("if", c, then, els)
        if t == "while":
            c = cond()
            take("do")
            body = block()
            take("end")
            return ("while", c, body)
        raise Error(f"expected a statement, not {t!r}")

    prog = []
    while peek()[0] != "eof":
        prog.append(stmt())
    return prog


class Stop(Exception):
    def __init__(self, how):
        self.how = how


def reader(text_in):
    """getint over text_in: white space, a sign, digits; a function giving the next number."""
    pos = 0

    def next_number():
        nonlocal pos
        while pos < len(text_in) and text_in[pos].isspace():
            pos += 1
        m = re.compile(r"[-+]?\d+").match(text_in, pos)
        if not m:
            raise Stop("no more input" if pos == len(text_in) else "not a number")
        pos = m.end()
        return wrap(int(m.group(0)))
    return next_number


def run(prog, text_in, limit=200000):
    env, out, steps = {}, [], [0]
    getint = reader(text_in)

    def tick():
        steps[0] += 1
        if steps[0] > limit:
            raise Stop("steps")

    def ev(e):
        k = e[0]
        if k == "num":
            return e[1]
        if k == "var":
            if e[1] not in env:
                raise Stop("no value")
            return env[e[1]]
        if k == "neg":
            return wrap(-ev(e[1]))
        a, b = ev(e[1]), ev(e[2])
        if k == "+":
            return wrap(a + b)
        if k == "-":
            return wrap(a - b)
        if k == "*":
            return wrap(a * b)
        if b == 0:
            raise Stop("division by zero")
        if a == MIN and b == -1:
            raise Stop("overflow division")
        q = abs(a) // abs(b)
        return q if (a < 0) == (b < 0) else -q

    def test(c):
        tick()
        a, b = ev(c[1]), ev(c[2])
        return {"==": a == b, "!=": a != b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b}[c[0]]

    def block(stmts):
        for s in stmts:
            tick()
            k = s[0]
            if k == "read":
                env[s[1]] = getint()
            elif k == "write":
                out.append(f"{ev(s[1])}\n")
            elif k == ":=":
                env[s[1]] = ev(s[2])
            elif k == "if":
                block(s[2] if test(s[1]) else s[3])
            else:
                while test(s[1]):
                    block(s[2])

    try:
        block(prog)
        return "ok", "".join(out)
    except Stop as e:
        return e.how, "".join(out)


def evaluate(text, text_in):
    return run(parse(text), text_in)


# ---------------------------------------------------------------- the generator

NAMES = ["a", "b", "x", "y", "n", "total", "k2", "_t", "left", "Right"]


def show(e, top=True):
    """An expression as text: binary operators spaced, parentheses where the grammar needs them
    (and now and then where it does not), a minus written so that it never makes "--"."""
    k = e[0]
    if k == "num":
        return str(e[1])
    if k == "var":
        return e[1]
    if k == "neg":
        inner = show(e[1], False)
        return "- " + inner if inner.startswith("-") else "-" + inner
    if k == "paren":
        return "(" + show(e[1]) + ")"
    a, b = show(e[1], False), show(e[2], False)
    return f"{a} {k} {b}"


def gen_expr(rng, names, depth):
    """A random expression over names, as a tree of the shapes show() writes; parentheses are
    nodes of their own so that the text is exactly what the grammar reads."""
    r = rng.random()
    if depth <= 0 or r < 0.3:
        if names and rng.random() < 0.6:
            return ("var", rng.choice(names))
        if rng.random() < 0.1:
            return ("num", rng.choice([2 ** 62, 2 ** 63 - 1, 4294967296, 1000000007]))
        return ("num", rng.randint(0, 20))
    if r < 0.4:
        return ("neg", factor_of(gen_expr(rng, names, depth - 1)))
    op = rng.choice(["+", "-", "*", "/", "+", "-", "*"])
    a = gen_expr(rng, names, depth - 1)
    b = gen_expr(rng, names, depth - 1)
    if op == "/" and rng.random() < 0.7:
        b = ("paren", ("+", ("*", factor_of(b), factor_of(b)), ("num", 1)))   # b * b + 1 is never 0 or -1
    if op in ("*", "/"):
        a, b = term_of(a), factor_of(b)
    else:
        b = term_of(b)
    return (op, a, b)


def factor_of(e):
    """e as a factor: in parentheses unless it is one already."""
    return e if e[0] in ("num", "var", "neg", "paren") else ("paren", e)


def term_of(e):
    return e if e[0] not in ("+", "-") else ("paren", e)


def gen_cond(rng, names):
    return f"{show(gen_expr(rng, names, 2))} {rng.choice(['==', '!=', '<', '>', '<=', '>='])} " \
           f"{show(gen_expr(rng, names, 2))}"


def generate(rng, size=14):
    """(text, input): a program of about `size` statements. Every name used has a value by then on
    every path (sure), so the dynamic rule never fails; loops count with a variable of their own."""
    lines = []
    counters = [0]
    budget = [size]

    def put(depth, text):
        r = rng.random()
        if r < 0.05:
            lines.append("")
        elif r < 0.1:
            lines.append("    " * depth + "# a comment, " + rng.choice(["while", "end", "if x then", "do"]))
        if rng.random() < 0.08:
            text += "    # " + rng.choice(["why", "end", "x := 1"])
        lines.append("    " * depth + text)

    def block(depth, sure):
        sure = list(sure)
        for _ in range(rng.randint(1, 4)):
            if budget[0] <= 0:
                break
            budget[0] -= 1
            r = rng.random()
            if r < 0.15 or not sure:
                x = rng.choice(NAMES)
                put(depth, f"read {x}")
                sure.append(x)
            elif r < 0.35:
                put(depth, f"write {show(gen_expr(rng, sure, 3))}")
            elif r < 0.65:
                x = rng.choice(NAMES)
                put(depth, f"{x} := {show(gen_expr(rng, sure, rng.randint(1, 4)))}")
                sure.append(x)
            elif r < 0.8 and depth < 3:
                put(depth, f"if {gen_cond(rng, sure)} then")
                block(depth + 1, sure)
                if rng.random() < 0.5:
                    put(depth, "else")
                    block(depth + 1, sure)
                put(depth, "end")
            elif depth < 3:
                counters[0] += 1
                c = f"c{counters[0]}"
                limit = rng.randint(0, 4)
                put(depth, f"{c} := 0")
                test = rng.choice([f"{c} < {limit}", f"{limit} > {c}", f"{c} != {limit}",
                                   f"{c} <= {limit} - 1", f"{c} + 1 <= {limit}"])
                put(depth, f"while {test} do")
                block(depth + 1, sure + [c])
                put(depth + 1, f"{c} := {c} + 1")
                put(depth, "end")
                sure.append(c)
        return sure

    block(0, [])
    while budget[0] > 0:
        budget[0] -= 1
        lines.append(f"write {rng.randint(0, 9)}")
    numbers = [rng.choice([rng.randint(-50, 50), rng.randint(-10 ** 6, 10 ** 6), rng.randint(MIN, MAX)])
               for _ in range(40)]
    text_in = " ".join(str(n) for n in numbers) + "\n"
    return "\n".join(lines) + "\n", text_in


def sample(seed, n, size=14):
    """n cases (text, input, output) that every way must run the same: each one's reference run
    ends "ok"."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        text, text_in = generate(rng, size)
        how, printed = evaluate(text, text_in)
        if how == "ok":
            out.append((text, text_in, printed))
    return out


if __name__ == "__main__":
    import sys
    for text, text_in, printed in sample(int(sys.argv[1]) if sys.argv[1:] else 1, 1):
        print(text + "--- input\n" + text_in + "--- output\n" + printed, end="")
