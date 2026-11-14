"""07.01 A makefile as a graph

make reads this project's own Makefile, with every tools/*/tool.mk it includes, into a graph in
which each target needs the same prerequisites, in the same order, as in the system's make's own
database (make -p); its counts are the graph's nodes and edges. The obvious walk over the graph
makes a target once for every path to it: on a chain of N diamonds it comes to 2^(N+2) - 3 nodes,
twice as many with each level, and on this project it compiles each file of the library once for
each tool that links it.
"""


def test(t):
    T = t.track
    fx = T.fixtures("make")

    # the project's own Makefile, as a graph
    proj = fx.project(t)
    r = fx.ours(t, proj, ["--graph"], env={"DS_STATS": "1"})
    names, needs, phony = fx.graph(r.out)
    t.check(len(names) == len(set(names)) and "all" in names and names[0] == "all",
            f"each target once, all first:\n{r.out[:800]}")
    g = T.stats(r.err)["depgraph"]
    edges = sum(len(v) for v in needs.values())
    t.check(g["nodes"] == len(names) and g["edges"] == edges,
            f"the stats count {g['nodes']} nodes and {g['edges']} edges; --graph prints {len(names)} and {edges}")
    t.check(phony == {"all", "clean"}, f".PHONY: {phony}")
    t.check(needs["build/libds.a"][0] == "build/lib/util.o" and "build/lib/depgraph.o" in needs["build/libds.a"],
            f"LIB, added to in the tool.mk files: {needs['build/libds.a']}")
    tools = needs["all"]
    t.check(len(tools) >= 5 and "bin/make" in tools and tools == sorted(tools),
            f"all needs every tool, in the order of the glob: {tools}")
    if T.have("make"):
        db = fx.database(fx.theirs(t, proj, ["-p", "-q"], check=False).out)
        mine = {n: v for n, v in needs.items() if v}
        t.check(set(db) - {"Makefile"} == set(mine) or set(db) == set(mine),
                f"targets with prerequisites: ours {sorted(set(mine) - set(db))} not in make -p, "
                f"make -p's {sorted(set(db) - set(mine))} not in ours")
        for name in mine:
            t.check(db[name] == mine[name], f"{name}: ours needs {mine[name]}, make -p says {db[name]}")

    # the walk: every path, every time
    for n in range(1, 9):
        mk = T.gen(t, "diamonds", n)
        r = fx.ours(t, t.tmp, ["-n", "--algo=recurse", "-f", mk], env={"DS_STATS": "1"})
        s = T.stats(r.err)
        visits = 2 ** (n + 2) - 3
        t.check(s["depgraph"]["walk visits"] == visits and s["depgraph"]["walk edges"] == visits - 1,
                f"{n} diamonds: the walk should come to {visits} nodes: {s['depgraph']}")
        t.check(s["depgraph"]["nodes"] == 3 * n + 1 and s["depgraph"]["edges"] == 4 * n, f"{n} diamonds: {s}")
        t.check(len(r.lines()) == visits and s["make"]["recipes run"] == visits,
                f"{n} diamonds: a recipe at every visit, {visits}: {len(r.lines())} lines, {s['make']}")
        t.check(r.lines().count(f"touch d{n}") == 2 ** n, f"the bottom of {n} diamonds is made 2^{n} times")

    # this project, walked: each library file compiled once for each tool
    lines = fx.ours(t, proj, ["-n", "--algo=recurse"]).lines()
    util = [l for l in lines if l.endswith(" -c -o build/lib/util.o lib/util.c")]
    t.check(len(util) == len(tools), f"the walk compiles lib/util.c {len(util)} times, for {len(tools)} tools")
    once = [l for l in fx.ours(t, proj, ["-n"]).lines() if l.endswith(" -c -o build/lib/util.o lib/util.c")]
    t.check(len(once) == 1, f"make in order compiles it once: {len(once)}")

    # what it does not read is an ordinary error, at its line
    for text, what in (("X := 1\n", "':=' is not supported"), ("%.o: %.c\n\tcc -c $<\n", "pattern rules"),
                       ("ifeq (a,b)\nendif\n", "'ifeq' is not supported"), ("a:\n\techo $@\n", "'$@' is not supported"),
                       ("all: $(wildcard *.c)\n", "'$(wildcard *.c)' is not supported"), ("oops\n", "missing separator"),
                       ("X = $(X) more\nall:\n\techo $(X)\n", "the variable X refers to itself")):
        d = fx.case(t, "bad", text)
        r = fx.ours(t, d, ["-n"], check=False)
        t.check(r.rc == 2 and r.err.startswith("make: Makefile:") and what in r.err,
                f"{text!r}: want status 2 and {what!r}:\n{r}")
    r = fx.ours(t, t.tmp, ["-f", "no-such.mk"], check=False)
    t.check(r.rc == 2 and "no-such.mk" in r.err, f"no makefile:\n{r}")
