"""Random integer expressions in C, and their values as C computes them for int.

Used by 0206's test and by fuzz_expr.py. Nothing here runs a compiler.

    gen(rng, depth)         a random tree: ("num", n), ("un", op, a) or ("bin", op, a, b)
    show(tree, rng)         its text: the parentheses C's precedence needs, a few more it does
                            not, and a space wherever two tokens could run together ("- -3")
    value(tree)             its value by C's rules for int (32 bits), or Undefined where C
                            leaves the result undefined: a value outside int, division by zero,
                            INT_MIN / -1, a shift by less than 0 or more than 31, a negative
                            number shifted left. ">>" of a negative number is implementation-
                            defined; gcc shifts in copies of the sign bit, as Python's >> does.
    sample(seed, n, depth)  n (text, value) pairs from a seed, the undefined ones left out

Since every value along the way fits in 32 bits, the 64-bit values this compiler computes are
the same numbers, so its answers, gcc's and Python's must agree.
"""

import random

INT_MIN, INT_MAX = -2 ** 31, 2 ** 31 - 1

# C's binary operators of module 02, tightest first, and their precedence (higher binds
# tighter). All are left-associative.
PREC = {"*": 10, "/": 10, "%": 10, "+": 9, "-": 9, "<<": 8, ">>": 8,
        "<": 7, "<=": 7, ">": 7, ">=": 7, "==": 6, "!=": 6, "&": 5, "^": 4, "|": 3}
BINARY = list(PREC)
UNARY = ["-", "+", "!", "~"]
UNARY_PREC = 11


class Undefined(Exception):
    pass


def _int(v):
    if not INT_MIN <= v <= INT_MAX:
        raise Undefined(f"{v} is not an int")
    return v


def _div(a, b):
    if b == 0 or (a == INT_MIN and b == -1):
        raise Undefined("division")
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q     # C rounds toward zero


def value(t):
    kind = t[0]
    if kind == "num":
        return _int(t[1])
    if kind == "un":
        a = value(t[2])
        return {"-": lambda: _int(-a), "+": lambda: a, "!": lambda: int(a == 0), "~": lambda: ~a}[t[1]]()
    op, a, b = t[1], value(t[2]), value(t[3])
    if op == "*":
        return _int(a * b)
    if op == "/":
        return _div(a, b)
    if op == "%":
        return _int(a - b * _div(a, b))
    if op == "+":
        return _int(a + b)
    if op == "-":
        return _int(a - b)
    if op in ("<<", ">>"):
        if not 0 <= b <= 31:
            raise Undefined("shift count")
        if op == ">>":
            return a >> b
        if a < 0:
            raise Undefined("negative shifted left")
        return _int(a << b)
    if op in ("&", "^", "|"):
        # Python's integers act as two's complement of any width, as a sign-extended register.
        return {"&": a & b, "^": a ^ b, "|": a | b}[op]
    return int({"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "==": a == b, "!=": a != b}[op])


def _number(rng):
    r = rng.random()
    if r < 0.75:
        return rng.randint(0, 20)
    if r < 0.95:
        return rng.randint(0, 5000)
    return rng.randint(0, INT_MAX)


def gen(rng, depth):
    if depth <= 0 or rng.random() < 0.1:
        return ("num", _number(rng))
    if rng.random() < 0.15:
        return ("un", rng.choice(UNARY), gen(rng, depth - 1))
    op = rng.choice(BINARY)
    if op in ("<<", ">>"):      # a shift count that is mostly in range
        return ("bin", op, gen(rng, depth - 1), ("num", rng.randint(0, 31)) if rng.random() < 0.7
                else gen(rng, depth - 1))
    # Lean right as often as left, so that values pile up in registers and spill.
    if rng.random() < 0.5:
        return ("bin", op, gen(rng, depth - 1), gen(rng, depth - 1))
    return ("bin", op, gen(rng, rng.randint(0, 2)), gen(rng, depth - 1))


def _prec(t):
    return {"num": 12, "un": UNARY_PREC}.get(t[0]) or PREC[t[1]]


def show(t, rng=None, ctx=0, right=False):
    """The text of tree t. With rng, a few parentheses more than C needs, at random."""
    kind = t[0]
    if kind == "num":
        s = str(t[1])
    elif kind == "un":
        inner = show(t[2], rng, UNARY_PREC)
        s = t[1] + (" " if inner[:1] in ("-", "+") else "") + inner
    else:
        p = PREC[t[1]]
        s = show(t[2], rng, p) + " " + t[1] + " " + show(t[3], rng, p, True)
    p = _prec(t)
    if p < ctx or (p == ctx and right) or (kind != "num" and rng is not None and rng.random() < 0.08):
        s = "(" + s + ")"
    return s


def num(n):
    return ("num", n)


def bin(op, a, b):
    return ("bin", op, a if isinstance(a, tuple) else num(a), b if isinstance(b, tuple) else num(b))


def sample_trees(seed, n, depth=8):
    """n (tree, text, value) triples from a seed, the undefined ones left out."""
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        t = gen(rng, rng.randint(2, depth))
        try:
            v = value(t)
        except Undefined:
            continue
        out.append((t, show(t, rng), v))
    return out


def sample(seed, n, depth=8):
    return [(s, v) for _, s, v in sample_trees(seed, n, depth)]


def registers(t):
    """How many registers this compiler's gen_expr wants for t, with the left operand at d and
    the right one at d + 1: past 6 (t0 to t5), it spills."""
    if t[0] == "num":
        return 1
    if t[0] == "un":
        return registers(t[2])
    return max(registers(t[2]), 1 + registers(t[3]))


def right_nested(n, op="-", first=1):
    """The tree of first op (first+1 op (first+2 op ... first+n)): n operators leaning right,
    so that n values wait in registers at the deepest one."""
    t = num(first + n)
    for i in range(n - 1, -1, -1):
        t = bin(op, first + i, t)
    return t


def left_nested(n, op="-", first=1):
    """The tree of ((first op first+1) op ...) op first+n: n operators leaning left."""
    t = num(first)
    for i in range(1, n + 1):
        t = bin(op, t, first + i)
    return t
