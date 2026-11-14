"""07.04 Building in parallel: a queue of ready work

With -j N, make keeps a queue of the targets whose prerequisites have all finished (Kahn's
algorithm) and runs up to N of their recipes at once. It never starts a target before everything
it needs has finished (by make's own trace, and by the recipes' own log); it really runs N at once
(two recipes that each wait for the other to start can only finish together, and the most at once
is N); it runs the same commands as a serial build, and builds this project into the same bytes as
the system's make. Each target goes through the queue once. A recipe that fails stops the build
with status 2, and nothing that needs it is started.
"""

import os


def test(t):
    T = t.track
    fx = T.fixtures("make")
    ex = f"{T._root(t)}/tools/make/examples"

    # one at a time, the queue's own order: what is ready first goes first
    r = fx.ours(t, t.tmp, ["-n", "--algo=queue", "-f", f"{ex}/diamond.mk"], env={"DS_TRACE": "1"})
    t.check(r.lines() == ["touch common.h", "touch liba", "touch libb", "touch app"], r.out)
    steps = [(e, w[0]) for e, w in fx.trace(r.err) if e in ("ready", "start", "finish")]
    t.check(steps[:4] == [("ready", "common.h"), ("start", "common.h"), ("finish", "common.h"), ("ready", "liba")],
            f"the queue's steps: {steps}")

    # N at once: eight targets that need nothing, four at a time
    mk = T.gen(t, "wide", 8)
    d = fx.case(t, "wide", open(mk).read())
    s = T.stats(fx.ours(t, d, ["-s", "-j", "4"], env={"DS_STATS": "1"}).err)
    t.check(s["make"]["most at once"] == 4 and s["make"]["recipes run"] == 8, f"-j 4 on 8: {s['make']}")
    t.check(s["readyq"]["pushes"] == 9 and s["readyq"]["pops"] == 9, f"each target through the queue once: {s}")
    s = T.stats(fx.ours(t, d, ["-s", "-j", "4"], env={"DS_STATS": "1"}).err)
    t.check(s["make"]["recipes run"] == 0 and s["readyq"]["pops"] == 9, f"all up to date: {s}")

    # they really run together: each waits for the other to have started
    wait = ("touch {me}.started; i=0; while [ ! -e {other}.started ] && [ $$i -lt $(WAIT) ]; do sleep 0.05; "
            "i=$$((i+1)); done; test -e {other}.started")
    text = ("WAIT = 200\nall: a b\na:\n\t" + wait.format(me="a", other="b") + "\nb:\n\t" +
            wait.format(me="b", other="a") + "\n.PHONY: all a b\n")
    d = fx.case(t, "together", text)
    r = fx.ours(t, d, ["-s", "-j", "2"], env={"DS_STATS": "1"}, check=False)
    t.check(r.rc == 0 and T.stats(r.err)["make"]["most at once"] == 2, f"-j 2: a and b wait for each other:\n{r}")
    d = fx.case(t, "alone", text)
    r = fx.ours(t, d, ["-s", "-j", "1", "WAIT=4"], check=False)
    t.check(r.rc == 2 and "Error 1" in r.err, f"-j 1: a waits for b in vain:\n{r}")

    # never before what it needs: a random graph whose recipes take a little time
    rng = T._gen_module(T._root(t)).Rand(11)
    for trial in range(3):
        n = 14
        needs = {i: sorted({rng.below(i) for _ in range(rng.below(4))}) if i else [] for i in range(n)}
        rules = [f"all: {' '.join(f'n{i}' for i in range(n))}", ".PHONY: all"]
        for i in range(n):
            rules += [f"n{i}: {' '.join(f'n{j}' for j in needs[i])}",
                      f"\techo begin n{i} >> log; sleep 0.0{rng.below(5)}; echo end n{i} >> log; touch n{i}"]
        d = fx.case(t, f"order{trial}", "\n".join(rules) + "\n")
        r = fx.ours(t, d, ["-s", "-j", "4"], env={"DS_TRACE": "1", "DS_STATS": "1"})
        log = open(os.path.join(d, "log")).read().split("\n")
        at = {line: k for k, line in enumerate(log)}
        for i in range(n):
            for j in needs[i]:
                t.check(at[f"end n{j}"] < at[f"begin n{i}"], f"n{i} began before n{j}, which it needs, ended:\n{log}")
        named = {f"n{i}": [f"n{j}" for j in needs[i]] for i in range(n)}
        named["all"] = list(named)
        done = set()
        for e, w in fx.trace(r.err):
            if e == "start":
                t.check(all(m in done for m in named[w[0]]), f"{w[0]} started before {named[w[0]]} finished")
            elif e == "finish":
                done.add(w[0])
        t.check(len(done) == n + 1 and T.stats(r.err)["make"]["recipes run"] == n, f"every target once: {done}")

    # the same commands as a serial build, and the same files
    # (but for a recipe that makes two targets, which -j runs once for each, as GNU make does)
    for name, (text, files, goals, _) in fx.CASES.items():
        runs = {"-j": ["-j", "3"], "one": []}
        if T.have("make"):
            runs["system -j"] = ["-j", "3"]
        out = {}
        for what, args in runs.items():
            d = fx.case(t, f"{name}-{what.replace(' ', '-')}", text, files)
            r = (fx.theirs if what.startswith("system") else fx.ours)(t, d, args + goals, check=False)
            log = os.path.join(d, "log")
            out[what] = (sorted(fx.message(r.out).splitlines()), r.rc, sorted(open(log).read().split("\n")) if os.path.exists(log) else [])
        if "system -j" in out:
            t.check(out["-j"] == out["system -j"], f"{name}: -j 3, ours and the system's: {out}")
        if name != "variables":
            t.check(out["-j"] == out["one"], f"{name}: -j 3 against one at a time: {out}")

    # this project, four at a time: the same programs as the system's make builds
    if T.have("make"):
        proj = fx.project(t)
        fx.theirs(t, proj, ["-s"])
        built = read_bin(proj)
        fx.theirs(t, proj, ["-s", "clean"])
        s = T.stats(fx.ours(t, proj, ["-s", "-j", "4"], env={"DS_STATS": "1"}).err)
        t.check(read_bin(proj) == built, "-j 4: the programs differ from the system make's")
        t.check(s["make"]["most at once"] == 4, f"-j 4 on this project: {s['make']}")
        t.check(s["readyq"]["pushes"] == s["depgraph"]["search visits"], f"each target queued once: {s}")

    # a recipe fails: the build stops, and what needs it never starts
    text = ("all: slow bad later\nslow:\n\tsleep 0.3; touch slow\nbad:\n\tfalse\nlater: bad\n\ttouch later\n"
            ".PHONY: all\n")
    d = fx.case(t, "fails", text)
    r = fx.ours(t, d, ["-j", "3"], env={"DS_TRACE": "1"}, check=False)
    started = [w[0] for e, w in fx.trace(r.err) if e == "start"]
    t.check(r.rc == 2 and "make: *** [bad] Error 1" in r.err and "later" not in started,
            f"a failing recipe:\n{r}")
    t.check(os.path.exists(os.path.join(d, "slow")), "the recipe already running is waited for")
    for args in (["-j", "0"], ["-j", "x"], ["-j", "2", "--algo=topo"]):
        r = fx.ours(t, d, args, check=False)
        t.check(r.rc == 2 and r.err.startswith("make: "), f"make {' '.join(args)}:\n{r}")


def read_bin(d):
    out = {}
    for name in sorted(os.listdir(os.path.join(d, "bin"))):
        with open(os.path.join(d, "bin", name), "rb") as f:
            out[name] = f.read()
    return out
