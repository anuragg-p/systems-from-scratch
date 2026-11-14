"""07.02 Depth-first search, and finding a cycle

The search enters each node the goals need once and goes along each of its edges once (N
diamonds: 3N + 1 visits and 4N edges, where the walk makes 2^(N+2) - 3), entering and leaving in
nested order. A cycle stops make with status 2 and its path, each target needing the next: the
edge the system's make reports dropping ("Circular c <- a") is the last of our path. A cycle the
goals do not need is not reported, as make does not report it. On random graphs ours finds a
cycle exactly when the goal can reach one, and every step of the path it prints is an edge.
"""

import re


def test(t):
    T = t.track
    fx = T.fixtures("make")
    ex = f"{T._root(t)}/tools/make/examples"

    # the example: a -> b -> c -> a
    for algo in ([], ["--algo=recurse"], ["-j", "2"]):
        r = fx.ours(t, t.tmp, ["-n", "-f", f"{ex}/cycle.mk"] + algo, check=False)
        t.check(r.rc == 2 and r.err == "make: dependency cycle: a -> b -> c -> a\n" and r.out == "",
                f"cycle.mk {algo}:\n{r}")

    cases = [("self", "a: a\n\ttouch a\n", ["a"], [("a", "a")]),
             ("two", "x: y\n\ttouch x\ny: x\n\ttouch y\n", ["x"], [("y", "x")]),
             ("deep", "top: m\nm: p q\np:\n\ttouch p\nq: r\nr: s\ns: q\n\ttouch s\n", ["top"], [("s", "q")]),
             ("unreached", "all: ok\nok:\n\ttouch ok\nl1: l2\nl2: l1\n.PHONY: all\n", ["all"], []),
             ("later goal", "all: ok\nok:\n\ttouch ok\nl1: l2\nl2: l1\n.PHONY: all\n", ["all", "l1"], [("l2", "l1")])]
    for name, text, goals, want in cases:
        d = fx.case(t, name.replace(" ", "-"), text)
        r = fx.ours(t, d, ["-n"] + goals, check=False)
        if not want:
            t.check(r.rc == 0 and "cycle" not in r.err, f"{name}: no cycle the goals need:\n{r}")
            continue
        m = re.match(r"^make: dependency cycle: (.*)\n$", r.err)
        t.check(r.rc == 2 and m, f"{name}: want the cycle:\n{r}")
        path = m.group(1).split(" -> ")
        t.check(path[0] == path[-1] and (path[-2], path[-1]) == want[0],
                f"{name}: the path {path} should close with {want[0]}")
        if T.have("make"):
            theirs = fx.message(fx.theirs(t, d, ["-n"] + goals, check=False).err)
            dropped = re.findall(r"Circular (\S+) <- (\S+) dependency dropped", theirs)
            t.check(dropped and dropped[0] == (path[-2], path[-1]),
                    f"{name}: make says {dropped}, our path {path} closes with {(path[-2], path[-1])}")

    # each node once, each edge once
    for n in (1, 5, 20, 60):
        mk = T.gen(t, "diamonds", n)
        r = fx.ours(t, t.tmp, ["-n", "-f", mk], env={"DS_STATS": "1"})
        g = T.stats(r.err)["depgraph"]
        t.check(g["search visits"] == 3 * n + 1 and g["search edges"] == 4 * n and g["walk visits"] == 0,
                f"{n} diamonds: the search should enter {3 * n + 1} nodes and follow {4 * n} edges: {g}")

    # the path is an array, not the C stack: a chain 100000 deep is searched, and a cycle that
    # long is found
    n = 100000
    chain = "".join(f"t{i}: t{i + 1}\n" for i in range(n))
    d = fx.case(t, "chain", chain + f"t{n}:\n\ttouch bottom\n")
    r = fx.ours(t, d, ["-n"], env={"DS_STATS": "1"})
    g = T.stats(r.err)["depgraph"]
    t.check(r.out == "touch bottom\n" and g["search visits"] == n + 1 and g["search edges"] == n,
            f"a chain {n} deep: {r.out!r} {g}")
    d = fx.case(t, "long-cycle", chain + f"t{n}: t0\n")
    r = fx.ours(t, d, ["-n"], check=False)
    t.check(r.rc == 2 and r.err.startswith("make: dependency cycle: t0 -> t1 -> ")
            and r.err.endswith(f" -> t{n} -> t0\n") and r.err.count(" -> ") == n + 1, f"a cycle {n + 1} long")

    # entered and left in nested order, each node once; met again once it is done
    r = fx.ours(t, t.tmp, ["-n", "-f", f"{ex}/diamond.mk"], env={"DS_TRACE": "1"})
    path, entered = [], []
    for event, words in fx.trace(r.err):
        if event == "enter":
            t.check(int(words[0]) == len(path), f"enter at depth {words[0]} with {len(path)} open: {r.err}")
            path.append(words[1])
            entered.append(words[1])
        elif event == "leave":
            t.check(path and path[-1] == words[1], f"leave {words[1]} while {path} are open")
            path.pop()
        elif event == "again":
            t.check(words[1] in entered and words[1] not in path, f"again {words[1]}: {entered} {path}")
    t.check(entered == ["app", "liba", "common.h", "libb"] and not path, f"entered {entered}")
    t.check([w for e, w in fx.trace(r.err) if e == "again"] == [["2", "common.h"]], r.err)

    # random graphs: a cycle is found exactly when the goal can reach one
    rng = T._gen_module(T._root(t)).Rand(7)
    found = 0
    for k in range(60):
        nn = 3 + rng.below(9)
        edges = {i: [] for i in range(nn)}
        for _ in range(rng.below(3 * nn)):
            a, b = rng.below(nn), rng.below(nn)
            if b not in edges[a] and (a < b or rng.below(6) == 0):
                edges[a].append(b)
        text = "".join(f"n{a}: {' '.join(f'n{b}' for b in bs)}\n\ttouch n{a}\n" for a, bs in edges.items())
        d = fx.case(t, f"random{k}", text)
        r = fx.ours(t, d, ["-n", "n0"], check=False)
        cyclic = has_cycle(edges, 0)
        t.check((r.rc == 2) == cyclic, f"graph {edges}: a cycle the goal reaches: {cyclic}; ours:\n{r}")
        if cyclic:
            found += 1
            path = [int(x[1:]) for x in re.match(r"^make: dependency cycle: (.*)\n$", r.err).group(1).split(" -> ")]
            t.check(path[0] == path[-1] and all(b in edges[a] for a, b in zip(path, path[1:])),
                    f"graph {edges}: {path} is not a cycle of it")
    t.check(10 <= found <= 50, f"the random graphs should hold some cycles and some not: {found} of 60")


def has_cycle(edges, start):
    state = {}

    def visit(a):
        state[a] = 1
        for b in edges[a]:
            if state.get(b) == 1 or (b not in state and visit(b)):
                return True
        state[a] = 2
        return False

    return visit(start)
