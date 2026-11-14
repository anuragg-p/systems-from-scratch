"""07.03 Topological order, and what is out of date

--order puts every target after everything it needs (checked here, and by the system's tsort).
Going once along that order, making a target only when it is out of date, ours runs what the
system's make runs, in the same order, on every makefile of the differential table: with -n on a
clean directory, for real, again, and with -n after one file has changed. On this project, -n
prints the system's commands to the byte, the programs ours builds are the same bytes as the
system's make's, and after a header changes both rebuild the same. Each target is visited once
(3N + 1 on N diamonds, where the walk it replaces makes 2^(N+2) - 3), and the walk, making a shared
target again after something that needs it, leaves the tree out of date.
"""

import os


def test(t):
    T = t.track
    fx = T.fixtures("make")
    ex = f"{T._root(t)}/tools/make/examples"

    # the order: everything a target needs comes before it
    r = fx.ours(t, t.tmp, ["--order", "-f", f"{ex}/diamond.mk"])
    t.check(r.lines() == ["common.h", "liba", "libb", "app"], f"--order:\n{r.out}")
    proj = fx.project(t)
    _, needs, _ = fx.graph(fx.ours(t, proj, ["--graph"]).out)
    for goals in ([], ["clean"], ["bin/make", "bin/freq"]):
        order = fx.ours(t, proj, ["--order"] + goals).lines()
        want = fx.reachable(needs, goals or ["all"])
        t.check(set(order) == want and len(order) == len(want), f"--order {goals}: not what the goals need")
        bad = fx.valid_order(order, needs)
        t.check(bad is None, f"--order {goals}: {bad[0]} comes before {bad[1]}, which it needs" if bad else "")
        fx.tsort_agrees(t, order, needs)

    # the same commands as the system's make, in the same order
    if T.have("make"):
        for name in fx.CASES:
            fx.differential(t, name)
        fx.differential(t, "diamond", ["-s"])

    # this project: the commands, the programs, and what a changed header rebuilds
    if T.have("make"):
        T.same(t, fx.ours(t, proj, ["-n"]).out, fx.theirs(t, proj, ["-n"]).out, "make -n on this project")
        theirs_run = fx.theirs(t, proj, []).out
        built = read_bin(proj)
        fx.theirs(t, proj, ["-s", "clean"])
        T.same(t, fx.ours(t, proj, []).out, theirs_run, "make on this project (the commands it prints)")
        t.check(read_bin(proj) == built, "the programs ours built are not the bytes the system's make built")
        when = int(os.path.getmtime(os.path.join(proj, "Makefile"))) - 1000
        everything = [os.path.relpath(os.path.join(dp, f), proj) for dp, _, fs in os.walk(proj) for f in fs]
        fx.stamp(proj, everything, when)
        T.same(t, fx.message(fx.ours(t, proj, ["-n"]).out), "make: Nothing to be done for 'all'.\n", "up to date")
        for changed in ("lib/ds.h", "lib/depgraph.h", "tools/sort/sort.c"):
            fx.stamp(proj, everything, when)
            fx.stamp(proj, [changed], when + 10)
            T.same(t, fx.ours(t, proj, ["-n"]).out, fx.theirs(t, proj, ["-n"]).out, f"make -n after {changed} changed")

    # each target once: N diamonds
    for n in (2, 6, 10):
        mk = T.gen(t, "diamonds", n)
        fast = T.stats(fx.ours(t, t.tmp, ["-n", "-f", mk], env={"DS_STATS": "1"}).err)
        slow = T.stats(fx.ours(t, t.tmp, ["-n", "--algo=recurse", "-f", mk], env={"DS_STATS": "1"}).err)
        t.check(fast["make"]["recipes run"] == 3 * n + 1 and slow["make"]["recipes run"] == 2 ** (n + 2) - 3,
                f"{n} diamonds: {fast['make']} against the walk's {slow['make']}")
        t.check(fast["depgraph"]["walk visits"] == 0 and slow["depgraph"]["walk visits"] == 2 ** (n + 2) - 3,
                f"{n} diamonds: {fast['depgraph']} {slow['depgraph']}")

    # what the walk leaves: common.h made again after liba used it, so liba is older than it
    # (each touch a twentieth of a second after the last: Linux keeps file times to a clock tick)
    d = fx.case(t, "walked", open(f"{ex}/diamond.mk").read().replace("\ttouch", "\t@sleep 0.05\n\ttouch"))
    r = fx.ours(t, d, ["--algo=recurse"])
    t.check(r.lines() == ["touch common.h", "touch liba", "touch common.h", "touch libb", "touch app"], r.out)
    r = fx.ours(t, d, ["-n"], env={"DS_TRACE": "1"})
    made = [l for l in r.lines() if l.startswith("touch")]
    t.check(made == ["touch liba", "touch app"] and "trace: check liba: common.h is newer\n" in r.err,
            f"after the walk, liba is out of date:\n{r}")
    fx.ours(t, d, ["-s"])
    t.check(fx.message(fx.ours(t, d, []).out) == "make: 'app' is up to date.\n", "and once made in order, it is not")

    # out of date: by time, by a prerequisite made in this run, or by being phony
    d = fx.case(t, "times", "out: mid\n\techo out >> log; touch out\nmid: in\n\techo mid >> log; touch mid\n",
                {"in": ""})
    fx.ours(t, d, ["-s"])
    for names, newer, want in ((["in", "mid", "out"], None, []), (["in", "mid", "out"], "in", ["mid", "out"]),
                               (["in", "mid", "out"], "mid", ["out"]), (["in", "mid", "out"], "out", [])):
        fx.stamp(d, names, 1000000000)
        if newer:
            fx.stamp(d, [newer], 1000000010)
        r = fx.ours(t, d, ["-n"], env={"DS_TRACE": "1"})
        got = [l.split()[1] for l in r.lines() if l.startswith("echo ")]
        t.check(got == want, f"{newer} newer: made {got}, want {want}\n{r.err}")
        if newer == "in":
            t.check("trace: check mid: in is newer\n" in r.err and "trace: check out: mid was made\n" in r.err,
                    f"why each is made:\n{r.err}")


def read_bin(d):
    out = {}
    for name in sorted(os.listdir(os.path.join(d, "bin"))):
        with open(os.path.join(d, "bin", name), "rb") as f:
            out[name] = f.read()
    return out
