"""08.01 A road map as a graph

route --info reads a map into adjacency lists and prints its size, how many junctions have each
number of roads, and its connected pieces, all as a plain Python reading of the same file finds
them, on the London map, the tiny one and a made-up city. Finding the pieces reads each road twice
with the lists (once from each end), and every road once for each junction when it reads the list
of roads instead. DS_TRACE prints one line for each junction taken off the stack. --svg draws the
map with its credit. A file that is not a map is an ordinary error, with its line.
"""

import os
import xml.etree.ElementTree as ET


def info_of(fx, mp):
    """What route --info must print for mp."""
    out = [f"junctions {mp.n}, roads {mp.m}, {sum(r[2] for r in mp.roads) / 1000:.1f} km of road"]
    deg = {}
    for j in range(mp.n):
        deg[len(mp.adj[j])] = deg.get(len(mp.adj[j]), 0) + 1
    for d in sorted(deg):
        out.append(f"{deg[d]:8d} junction{' ' if deg[d] == 1 else 's'} with {d} road{'' if d == 1 else 's'}")
    sizes = fx.ref_pieces(mp)
    out.append(f"pieces {len(sizes)}: junctions in each, the largest first: "
               + ", ".join(str(s) for s in sizes[:10]) + (", ..." if len(sizes) > 10 else ""))
    return "\n".join(out) + "\n"


def test(t):
    T = t.track
    fx = T.fixtures("route")
    city = T.gen(t, "citymap", 400, name="city.map")
    for path in (fx.TINY, fx.LONDON, city):
        mp = fx.load(os.path.join(t.root, path))
        want = info_of(fx, mp)
        for graph in ("lists", "edges"):
            if graph == "edges" and mp.n > 1000:
                continue
            r = T.run(t, "route", ["--info", f"--graph={graph}", path], env={"DS_STATS": "1"})
            T.same(t, r.out, want, f"route --info --graph={graph} {os.path.basename(path)}")
            s = T.stats(r.err)["route"]
            t.check(s["junctions"] == mp.n and s["roads"] == mp.m, f"the map's size: {s}")
            read = 2 * mp.m if graph == "lists" else mp.n * mp.m
            t.check(s["roads read"] == read, f"--graph={graph} on {path}: {read} roads read, not {s}")

    # London: its pieces, by the lists only (the list of roads would read 388 million)
    mp = fx.load(os.path.join(t.root, fx.LONDON))
    t.check(mp.n > 15000 and len(fx.ref_pieces(mp)) > 1, f"London has {mp.n} junctions")
    r = T.run(t, "route", ["--info", fx.LONDON])
    t.check(r.out.startswith("junctions 17260, roads 22498,"), f"the London map:\n{r.out}")

    # DS_TRACE: one line for each junction taken off the stack, with the stack after
    r = T.run(t, "route", ["--info", fx.TINY], env={"DS_TRACE": "1"})
    lines = [l for l in r.err.splitlines() if l.startswith("trace: pieces: ")]
    t.check(len(lines) == 12, f"12 junctions, 12 lines:\n{r.err}")
    t.check(lines[0] == "trace: pieces: take 0 into piece 0; stack: 1 2 3", f"the first line: {lines[0]!r}")
    t.check(lines[-1] == "trace: pieces: take 1 into piece 0; stack:", f"the last line: {lines[-1]!r}")

    # the picture: every road, the pieces but the largest in colour, the credit the licence asks for
    svg = os.path.join(t.tmp, "london.svg")
    T.run(t, "route", ["--info", f"--svg={svg}", fx.LONDON])
    root = ET.parse(svg).getroot()
    paths = [e for e in root.iter() if e.tag.endswith("path")]
    t.check(len(paths) == 2 and paths[0].get("d").count("M") == mp.m, f"every road is drawn: {len(paths)} paths")
    texts = " ".join(e.text or "" for e in root.iter() if e.tag.endswith("text"))
    t.check("OpenStreetMap" in texts and "Open Database License" in texts, f"the credit: {texts!r}")
    box = os.path.join(t.tmp, "box.svg")
    T.run(t, "route", ["--info", f"--svg={box}", "--box=5000,3000,7000,5000", fx.LONDON])
    t.check(os.path.getsize(box) < os.path.getsize(svg) / 5, "a box draws only part of the map")
    tiny = os.path.join(t.tmp, "tiny.svg")
    T.run(t, "route", ["--info", f"--svg={tiny}", fx.TINY])
    t.check("OpenStreetMap" not in open(tiny).read(), "the tiny map is ours: no credit")

    # ordinary errors
    bad = T.write(t, "bad.map", "junctions 2\n0 0\n10 x\nroads 0\n")
    short = T.write(t, "short.map", "junctions 2\n0 0\n10 10\nroads 2\n0 1 15\n")
    wrong = T.write(t, "wrong.map", "junctions 2\n0 0\n10 10\nroads 1\n0 2 15\n")
    for args, msg in ((["--info", bad], "bad.map: line 3: expected a junction"),
                      (["--info", short], "short.map: line 5: expected a road"),
                      (["--info", wrong], "line 5: a road to a junction the map does not have"),
                      (["--info", "/no/such.map"], "/no/such.map: "),
                      (["--info", "--graph=matrix", fx.TINY], "no --graph 'matrix' (have: lists, edges)"),
                      (["--info", "--box=5,5,1,1", fx.TINY], "--box wants X0,Y0,X1,Y1"),
                      (["--info"], "usage: route"),
                      (["--graph=edges", fx.TINY, "1", "2"], "--graph goes with --info"),
                      (["--route", fx.TINY], "unknown option '--route'")):
        r = T.run(t, "route", args, check=False)
        t.check(r.rc == 2 and r.err.startswith("route: ") and msg in r.err, f"route {' '.join(args)}:\n{r}")
