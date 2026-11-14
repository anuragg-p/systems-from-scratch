#!/usr/bin/env python3
"""route's maps: the city map made from OpenStreetMap, and made-up cities of any size.

    python3 tools/route/gen.py osm EXTRACT.json [-o FILE]
                        the city map from an Overpass API extract (NOTICE.txt says which,
                        and the query that fetched it); the result is tools/route/london.map
    python3 data/gen.py citymap N [--seed S]
                        a made-up city of about N junctions (the KINDS below), for the
                        growth harness: python3 bench/grow.py --input citymap ...

The map format (route reads it, lib/roadgraph.c):

    # comment lines, anywhere before the numbers
    credit TEXT         optional: what the picture of the map must say (route writes it in
                        a corner of every SVG it draws)
    junctions N
    X Y                 N lines: junction 0, 1, ... at X metres east and Y metres north of
                        the map's south-west corner
    roads M
    A B METRES          M lines: a road between junctions A and B (A < B), both ways, and
                        its length in whole metres

Every length is at least the straight line between its two junctions as the file gives them
(gen checks it), so the straight line never overestimates the road: A* relies on that.

How the extract becomes the map (this is the whole method; ODbL 4.6 asks for it):

 1. Keep the nodes inside BOX (south, west, north, east, in degrees). A way is cut where it
    leaves the box: each run of its nodes inside the box is kept, the rest dropped.
 2. Put every node on a flat map in metres: x = R * dlon * cos(middle latitude), y = R * dlat,
    from the box's south-west corner, R = 6371008.8 m; round both to whole metres.
 3. Each pair of nodes next to each other on a kept way is a piece of road (once, however
    many ways share it). A node with other than two pieces of road is a junction (an end, or
    where three or more meet); a node with exactly two is a bend, and goes.
 4. Walk from each junction along each piece of road, through the bends, to the next
    junction: one road, whose length is the sum of its pieces (between the rounded points),
    rounded up to a whole metre. A road back to where it started is dropped; of two roads
    between the same two junctions only the shorter is kept. A loop with no junction on it is
    dropped.
 5. Steps 3 and 4 can leave a junction with two roads: it becomes a bend too (its two roads
    one road, their lengths added), until no junction has exactly two roads.
 6. Number the junctions south to north (by y, then x), and list the roads by their first
    junction, then their second.

Nothing else: no names, no tags, no one-way streets (every road goes both ways), no turns.
"""

import json
import math
import os
import sys

R = 6371008.8

# The extract: what was asked of the Overpass API, and the part of it the map keeps.
QUERY = """[out:json][timeout:300];
way["highway"~"^(trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|unclassified|residential|living_street|pedestrian)$"]["area"!="yes"]["access"!~"^(private|no)$"](51.475,-0.210,51.545,-0.030);
(._;>;);
out skel qt;"""
BOX = (51.475, -0.210, 51.545, -0.030)

CREDIT = ("Map data from OpenStreetMap (openstreetmap.org/copyright), "
          "under the Open Database License (ODbL 1.0)")


def load_overpass(path):
    """The nodes {id: (lat, lon)} and ways [[node id, ...]] of an Overpass JSON extract."""
    with open(path, "rb") as f:
        data = json.load(f)
    nodes, ways = {}, []
    for e in data["elements"]:
        if e["type"] == "node":
            nodes[e["id"]] = (e["lat"], e["lon"])
        elif e["type"] == "way":
            ways.append(e["nodes"])
    return nodes, ways, data.get("osm3s", {}).get("timestamp_osm_base", "")


def project(nodes, box):
    """Steps 1 and 2: {id: (x, y)} in whole metres, for the nodes inside box."""
    south, west, north, east = box
    k = math.cos(math.radians((south + north) / 2))
    out = {}
    for nid, (lat, lon) in nodes.items():
        if south <= lat <= north and west <= lon <= east:
            out[nid] = (round(R * math.radians(lon - west) * k), round(R * math.radians(lat - south)))
    return out


def dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def contract(xy, ways):
    """Steps 3 to 5: the junctions {id: (x, y)} and the roads {(a, b): metres}, a < b."""
    near = {}
    for way in ways:
        for a, b in zip(way, way[1:]):
            if a != b and a in xy and b in xy:
                near.setdefault(a, set()).add(b)
                near.setdefault(b, set()).add(a)
    junction = {n for n, s in near.items() if len(s) != 2}
    roads = {}
    for j in junction:
        for first in near[j]:
            prev, here, length = j, first, dist(xy[j], xy[first])
            while here not in junction:
                prev, here = here, next(n for n in near[here] if n != prev)
                length += dist(xy[prev], xy[here])
            if here == j:
                continue
            key = (min(j, here), max(j, here))
            metres = math.ceil(length - 1e-9)
            if key not in roads or metres < roads[key]:
                roads[key] = metres
    # step 5: a junction left with two roads is a bend
    adj = {}
    for (a, b), m in roads.items():
        adj.setdefault(a, {})[b] = m
        adj.setdefault(b, {})[a] = m
    work = [j for j in adj if len(adj[j]) == 2]
    while work:
        j = work.pop()
        if j not in adj or len(adj[j]) != 2:
            continue
        (a, ma), (b, mb) = adj.pop(j).items()
        del adj[a][j], adj[b][j]
        m = ma + mb
        if b not in adj[a] or m < adj[a][b]:
            adj[a][b] = adj[b][a] = m
        for k in (a, b):
            if len(adj[k]) == 2:
                work.append(k)
    adj = {j: s for j, s in adj.items() if s}
    roads = {(a, b): m for a, s in adj.items() for b, m in s.items() if a < b}
    return {j: xy[j] for j in adj}, roads


def number(junctions, roads):
    """Step 6: [(x, y)] in the file's order and [(a, b, metres)], a < b."""
    order = sorted(junctions, key=lambda j: (junctions[j][1], junctions[j][0], j))
    at = {j: i for i, j in enumerate(order)}
    pts = [junctions[j] for j in order]
    out = sorted((min(at[a], at[b]), max(at[a], at[b]), m) for (a, b), m in roads.items())
    for a, b, m in out:
        if dist(pts[a], pts[b]) > m:
            raise SystemExit(f"gen.py: road {a}-{b} of {m} m is shorter than the straight line")
    return pts, out


def write_map(pts, roads, header=(), credit=None):
    lines = ["# " + h if h else "#" for h in header]
    if credit:
        lines.append("credit " + credit)
    lines.append(f"junctions {len(pts)}")
    lines += [f"{x} {y}" for x, y in pts]
    lines.append(f"roads {len(roads)}")
    lines += [f"{a} {b} {m}" for a, b, m in roads]
    return ("\n".join(lines) + "\n").encode("ascii")


def osm_map(path, box=BOX):
    nodes, ways, stamp = load_overpass(path)
    xy = project(nodes, box)
    junctions, roads = contract(xy, ways)
    pts, roads = number(junctions, roads)
    south, west, north, east = box
    header = [
        "route map: the roads of central London, from OpenStreetMap.",
        "",
        "Map data (c) OpenStreetMap contributors, https://www.openstreetmap.org/copyright",
        "This map is a Derivative Database of OpenStreetMap, made available under the",
        "Open Database License (ODbL) 1.0: https://opendatacommons.org/licenses/odbl/1-0/",
        "It is not under this repository's MIT licence. tools/route/NOTICE.txt says where it",
        "came from, and tools/route/gen.py how it was made (every step).",
        "",
        f"OpenStreetMap data as of {stamp}; box {south},{west} to {north},{east} (lat,lon).",
        f"x and y are metres east and north of {south},{west}.",
    ]
    return write_map(pts, roads, header, CREDIT)


# ---------------------------------------------------------------- made-up cities (data/gen.py)

def citymap(n, rng):
    """A made-up city of about n junctions: a square grid of streets 100 m apart, each junction
    moved up to 60 m, each road up to a fifth longer than the straight line, and one north-south
    road in four left out (but those of the west edge, so that every junction can reach every
    other). Junction 0 is in the south-west corner, the last in the north-east. Ours, not
    OpenStreetMap's: no credit line."""
    side = max(2, round(math.sqrt(n)))
    pts = []
    for row in range(side):
        for col in range(side):
            pts.append((col * 100 + rng.below(61), row * 100 + rng.below(61)))
    roads = []
    for row in range(side):
        for col in range(side):
            j = row * side + col
            if col + 1 < side:
                roads.append((j, j + 1))
            if row + 1 < side and (col == 0 or rng.below(4) != 0):
                roads.append((j, j + side))
    roads = [(a, b, math.ceil(dist(pts[a], pts[b]) * (1 + rng.below(21) / 100))) for a, b in roads]
    return write_map(pts, roads, ["route map: a made-up city, a grid of %d junctions" % len(pts)])


KINDS = {
    "citymap": (citymap, "junctions", "a made-up city: a grid of streets, in route's map format"),
}


def main(argv):
    if len(argv) >= 2 and argv[0] == "osm":
        out = argv[argv.index("-o") + 1] if "-o" in argv else None
        data = osm_map(argv[1])
        if out:
            with open(out, "wb") as f:
                f.write(data)
        else:
            sys.stdout.buffer.write(data)
        return 0
    print(__doc__.split("\n\n")[0] + "\n\n" + __doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
