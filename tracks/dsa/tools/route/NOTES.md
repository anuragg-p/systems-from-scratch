# route: notes for the lesson writers (module 08)

Everything here was run on the reference code: Apple M4 Pro, macOS 26.6.2,
Apple clang 21; and the tests, check-skeleton and check-timeline also on
Linux (Docker, Debian stable, aarch64, gcc 14.2). Every "break it" was run on
the project as `./learn files dsa --at 08.0N` writes it, with that one change,
and its output is pasted. Times are the fastest of three runs.

## The tool and the map

```
lib/roadgraph.h, .c    08.01   the road graph: the map file read into arrays, and adjacency lists
tools/route/route.c    08.01-08.04
tools/route/london.map 08.01   central London from OpenStreetMap (ODbL: NOTICE.txt)
tools/route/tiny.map   08.01   a dozen junctions, ours, for traces and figures
tools/route/gen.py     08.01   how london.map was made; the citymap kind for bench/grow.py
tools/route/NOTICE.txt 08.01   source, bounds, date, hashes, licence and how its terms are met
```

`route [option ...] MAP FROM TO` and `route --info [option ...] MAP`. FROM
and TO are junction numbers, or `X,Y` (metres east and north of the map's
south-west corner) for the nearest junction. Options: `--info`,
`--graph=lists|edges` (08.01, --info only), `--svg=FILE`,
`--box=X0,Y0,X1,Y1` (08.01), `--algo=bfs|dijkstra-scan|dijkstra|astar`
(from 08.03; the default is the last built: bfs at 08.02, dijkstra at 08.03,
astar from 08.04). Errors are status 2 (`route: ...`); "no route" is status 1.
At 08.01 a route request is `route: no search to find a route with yet: try
--info`; at 08.02 `--algo=dijkstra` is `route: unknown option
'--algo=dijkstra'`; at 08.03 `--algo=astar` is `route: no --algo 'astar'
(have: bfs, dijkstra-scan, dijkstra)`.

The map file: `#` comments, an optional `credit` line, `junctions N` and N
lines `X Y`, `roads M` and M lines `A B METRES` (both ways). london.map:
17260 junctions, 22498 roads, 486185 bytes, a box of 12457 by 7783 m around
the centre, both banks of the Thames. Every road is at least the straight
line between its ends (gen.py checks it; the 08.04 test checks it again):
lengths are measured on the same flat projection as the coordinates, along
the road's bends, rounded up. Roads are two-way (no one-way streets, no
turns): a map for walking, not driving. Not fetched again by anything.

The picture (`--svg`): every road in grey, in blue the roads with an end the
search finished (with --info: every piece but the largest), the route in red,
the start green, the end red, the caption top left, and for london.map the
credit "Map data from OpenStreetMap (openstreetmap.org/copyright), under the
Open Database License (ODbL 1.0)" bottom right: the ODbL wants it on every
picture made from the map, so a lesson figure cut from one keeps it (or says
it beside the figure). Plain SVG with only the tags and attributes
harness/web/art.py allows; one unit is about a pixel of a picture 1000 wide
(13 m on the whole of London), roads as relative moves. Sizes: the whole map
300 KB grey, 400 to 570 KB with a search on it; over the 200 KB a figure may
be, so a figure uses `--box` (the search is not changed by the box, only the
drawing) or the tiny map. On a map of 50 junctions or fewer in the box, each
junction is drawn with its number. Good pair for "disc against wedge": `bin/route --algo=dijkstra --svg=d.svg
tools/route/london.map 4500,3500 8000,5000` and the same with astar:
4131 m both, 6040 junctions finished against 544.

## DS_STATS and DS_TRACE

`stats: route: junctions N, roads M, reached R, finished F, scanned S,
relaxed X, stale P, roads read Q`: the map's size; junctions given a
distance; junctions finished (distance known for good); junctions looked at
to pick the next (dijkstra-scan only: n for every pick); roads followed from
a finished junction; heap entries thrown away as out of date; roads read to
find the roads at a junction (--info). The heap prints its own line, and
its Array one.

`DS_TRACE=1` prints on stderr one line per junction finished (and per stale
entry thrown away), for figures. Formats (J a junction, D its distance):

```
trace: pieces: take J into piece P; stack: J J ...          (--info: the stack after J's roads)
trace: bfs: finish J at D (from P); queue: J:D J:D ...      (D in roads; the queue front to back)
trace: dijkstra-scan: finish J at D (from P); reached: J:D ...   (every junction reached and not finished, by number)
trace: dijkstra: finish J at D (from P); heap: J:D J:D ...  (the heap's array, top first)
trace: dijkstra: skip J at D, finished at D2 already; heap: ...
trace: astar: finish J at G, guess H, sum F (from P); heap: J:F ...   (heap keys are G + H)
```

"(start)" in place of "(from P)" for the start. Each line shows the container
after the junction's roads were followed. A heap entry whose junction has
since been given a shorter distance is shown `J:D(old)`. Ties are broken by
the smaller junction number, in the scan and in the heap alike, so
dijkstra-scan and dijkstra finish the same junctions in the same order.

### tiny.map

Junctions 0 (100,0), 1 (900,0); 2 (100,300) to 8 (1400,300) along a main
street, 3 to 8 at 200 m a road; 9 (200,600), 10 (700,600), 11 (1100,600).
Roads: 0-1 800, 0-2 300, 0-3 430, 1-3 600, 1-6 320, 1-8 600, 2-3 300, 2-9
320, 3-4 200, 3-9 370, 4-5 200, 4-10 320, 5-6 200, 5-10 320, 6-7 200, 6-11
320, 7-8 200, 7-11 320, 8-11 430, 9-10 500, 10-11 400. From 3 to 8: the ring
3-1-8 is 2 roads and 1200 m (BFS), the main street 5 roads and 1000 m
(Dijkstra, A*). `--svg` on it draws every junction with its number.

```
$ DS_TRACE=1 bin/route --algo=bfs tools/route/tiny.map 3 8
trace: bfs: finish 3 at 0 (start); queue: 0:1 1:1 2:1 4:1 9:1
trace: bfs: finish 0 at 1 (from 3); queue: 1:1 2:1 4:1 9:1
trace: bfs: finish 1 at 1 (from 3); queue: 2:1 4:1 9:1 6:2 8:2
trace: bfs: finish 2 at 1 (from 3); queue: 4:1 9:1 6:2 8:2
trace: bfs: finish 4 at 1 (from 3); queue: 9:1 6:2 8:2 5:2 10:2
trace: bfs: finish 9 at 1 (from 3); queue: 6:2 8:2 5:2 10:2
trace: bfs: finish 6 at 2 (from 1); queue: 8:2 5:2 10:2 7:3 11:3
trace: bfs: finish 8 at 2 (from 1); queue: 5:2 10:2 7:3 11:3
$ DS_TRACE=1 bin/route --algo=dijkstra-scan tools/route/tiny.map 3 8
trace: dijkstra-scan: finish 3 at 0 (start); reached: 0:430 1:600 2:300 4:200 9:370
trace: dijkstra-scan: finish 4 at 200 (from 3); reached: 0:430 1:600 2:300 5:400 9:370 10:520
trace: dijkstra-scan: finish 2 at 300 (from 3); reached: 0:430 1:600 5:400 9:370 10:520
trace: dijkstra-scan: finish 9 at 370 (from 3); reached: 0:430 1:600 5:400 10:520
trace: dijkstra-scan: finish 5 at 400 (from 4); reached: 0:430 1:600 6:600 10:520
trace: dijkstra-scan: finish 0 at 430 (from 3); reached: 1:600 6:600 10:520
trace: dijkstra-scan: finish 10 at 520 (from 4); reached: 1:600 6:600 11:920
trace: dijkstra-scan: finish 1 at 600 (from 3); reached: 6:600 8:1200 11:920
trace: dijkstra-scan: finish 6 at 600 (from 5); reached: 7:800 8:1200 11:920
trace: dijkstra-scan: finish 7 at 800 (from 6); reached: 8:1000 11:920
trace: dijkstra-scan: finish 11 at 920 (from 10); reached: 8:1000
trace: dijkstra-scan: finish 8 at 1000 (from 7); reached:
$ DS_TRACE=1 bin/route --algo=astar tools/route/tiny.map 3 8
trace: astar: finish 3 at 0, guess 1000, sum 1000 (start); heap: 4:1000 1:1183 2:1600 0:1764 9:1607
trace: astar: finish 4 at 200, guess 800, sum 1000 (from 3); heap: 5:1000 1:1183 10:1282 0:1764 9:1607 2:1600
trace: astar: finish 5 at 400, guess 600, sum 1000 (from 4); heap: 6:1000 2:1600 1:1183 0:1764 9:1607 10:1282
trace: astar: finish 6 at 600, guess 400, sum 1000 (from 5); heap: 7:1000 2:1600 1:1183 0:1764 9:1607 10:1282 11:1344
trace: astar: finish 7 at 800, guess 200, sum 1000 (from 6); heap: 8:1000 2:1600 1:1183 0:1764 9:1607 11:1344 10:1282
trace: astar: finish 8 at 1000, guess 0, sum 1000 (from 7); heap: 1:1183 2:1600 10:1282 0:1764 9:1607 11:1344
```

For lazy deletion in a figure, 0 to 8 (1400 m by the ring) has two stale pops:

```
$ DS_TRACE=1 bin/route --algo=dijkstra tools/route/tiny.map 0 8
trace: dijkstra: finish 0 at 0 (start); heap: 2:300 1:800 3:430
trace: dijkstra: finish 2 at 300 (from 0); heap: 3:430 1:800 9:620
trace: dijkstra: finish 3 at 430 (from 0); heap: 9:620 1:800 4:630
trace: dijkstra: finish 9 at 620 (from 2); heap: 4:630 1:800 10:1120
trace: dijkstra: finish 4 at 630 (from 3); heap: 1:800 10:950 5:830 10:1120(old)
trace: dijkstra: finish 1 at 800 (from 0); heap: 5:830 10:950 10:1120(old) 6:1120 8:1400
trace: dijkstra: finish 5 at 830 (from 4); heap: 10:950 6:1030 10:1120(old) 8:1400 6:1120(old)
trace: dijkstra: finish 10 at 950 (from 4); heap: 6:1030 6:1120(old) 10:1120(old) 8:1400 11:1350
trace: dijkstra: finish 6 at 1030 (from 5); heap: 6:1120(old) 7:1230 10:1120(old) 8:1400 11:1350
trace: dijkstra: skip 6 at 1120, finished at 1030 already; heap: 10:1120(old) 7:1230 11:1350 8:1400
trace: dijkstra: skip 10 at 1120, finished at 950 already; heap: 7:1230 8:1400 11:1350
trace: dijkstra: finish 7 at 1230 (from 6); heap: 11:1350 8:1400
trace: dijkstra: finish 11 at 1350 (from 10); heap: 8:1400
trace: dijkstra: finish 8 at 1400 (from 1); heap:
```

DS_STATS on tiny, 3 to 8: bfs finished 8, relaxed 25; dijkstra-scan finished
12, scanned 144 (12 x 12), relaxed 39; dijkstra finished 12, heap pushes 13,
pops 12, comparisons 31; astar finished 6, relaxed 18, heap pushes 12, pops 6.

## 08.01 A road map as a graph

Regions: build_lists (lib/roadgraph.c: count each junction's roads into
first[], prefix sums, then place each road's two arcs with a moving cursor),
pieces (route.c: a flood fill from each junction not in a piece yet, with a
stack of n ints; --graph=edges finds a junction's roads by reading all M).
read_map, the SVG writer, --info's printing and the option parsing are plain
code that comes with the file. The roads are kept twice: as the file lists
them (road_a, road_b, road_len) and as arcs (first, to, len): the edge list
is what --graph=edges and the SVG read.

```
$ bin/route --info tools/route/london.map
junctions 17260, roads 22498, 1621.4 km of road
    4336 junctions with 1 road
   11075 junctions with 3 roads
    1812 junctions with 4 roads
      35 junctions with 5 roads
       2 junctions with 6 roads
pieces 163: junctions in each, the largest first: 16748, 18, 17, 17, 16, 12, 11, 11, 9, 8, ...
```

No junction has 2 roads: a point where a road only bends is not a junction
(gen.py step 3). Of the 4336 dead ends, 405 are within 60 m of the box's
edge (roads the box cut); of the 162 small pieces, 36 come within 100 m of
it. The rest are inside the map: cul-de-sacs, and (my reading, not
checked road by road) roads whose only way out is a service road, footpath
or private road, which the extract left out. `--info --svg` draws the small
pieces in blue.

Slow against fast (`roads read` in DS_STATS): the lists read each road twice
(44996 on London); the list of roads reads all 22498 for each of the 17260
junctions: 388315480. Times on London: `--info` 4.7 ms, `--info --graph=edges`
0.16 s. Measured on made-up cities (`citymap`: a grid, n junctions, about
1.75n roads):

```
$ python3 bench/grow.py --input citymap --start 1000 --limit 5 bin/route --info --graph=edges {}
        n       bytes   seconds  ratio
     8000      260803     0.047
    16000      556216     0.180    3.8
    32000     1181606     0.731    4.1
    64000     2424133     2.943    4.0
   128000     5032970    11.807    4.0
growth: about n^2
$ python3 bench/grow.py --input citymap --start 64000 --max 2048000 bin/route --info {}
   256000    10486870     0.044    1.9
   512000    21456811     0.093    2.1
  1024000    43461368     0.169    1.8
  2048000    92131925     0.340    2.0
growth: about n
```

(With lists the time is reading the file.) The list of roads is fine for
London and unusable at about 100000 junctions: a city's whole road network,
not its centre.

Break it (count only one end of each road: delete `g->first[g->road_b[r] +
1]++;` in build_lists). Each junction's arcs then overlap the next one's:

```
$ bin/route --info tools/route/tiny.map
junctions 12, roads 21, 7.7 km of road
       1 junction  with 0 roads
       3 junctions with 1 road
       6 junctions with 2 roads
       2 junctions with 3 roads
pieces 2: junctions in each, the largest first: 11, 1
$ bin/route --info tools/route/london.map
junctions 17260, roads 22498, 1621.4 km of road
    2310 junctions with 0 roads
    7658 junctions with 1 road
    7036 junctions with 2 roads
     256 junctions with 3 roads
pieces 3336: junctions in each, the largest first: 9602, 124, 46, 38, 28, 28, 27, 26, 25, 25, ...
```

(No crash: the arcs are written past their junction's share but inside the
2M array, and first[n] is M, so the second half is never read.)

## 08.02 Breadth-first search: the fewest junctions

Region: search_bfs (a queue of n ints, head and tail; a junction is marked
REACHED when it goes in, so it goes in once; the search stops when the end
comes off the queue). The search state (dist, prev, state; start(),
route_of(), print_route(), the Algo table and pick()) is an `@from 08.02`
block; dist counts roads for bfs. The route's metres are added up from the
roads when it is printed.

```
$ bin/route tools/route/tiny.map 3 8          (at 08.02; --algo=bfs later)
from 3 to 8: 1200 metres, 3 junctions
  metres  junction       x       y
       0         3     400     300
     600         1     900       0
    1200         8    1400     300
```

The fewest junctions are not the fewest metres, on London (`--algo=bfs`
against `--algo=dijkstra`):

```
300,3500 to 12000,4000 (west to east):  bfs 14480 metres, 134 junctions;  shortest 12973 metres, 210 junctions
4500,3500 to 8000,5000 (the centre):    bfs  6146 metres,  55 junctions;  shortest  4131 metres,  71 junctions
```

BFS takes long roads with few junctions on them (the main roads); the
shortest route goes through the side streets. The 08.02 test finds BFS
longer on most of its table of 22 pairs. BFS finished 14657 junctions on the
west-east crossing: it does not look towards anything either.

No route: `bin/route tools/route/london.map 8524 2` prints `from 8524 to 2:
no route: no road joins them`, status 1, after finishing all 16748
junctions of the large piece. A junction to itself: `from 8524 to 8524: 0
metres, 1 junction`.

Break it (a stack for a queue: `int u = queue[head++];` becomes `int u =
queue[--tail];`). Junctions come off newest first, a depth-first walk, and
the route is whatever that walk found first:

```
$ bin/route tools/route/tiny.map 3 8
from 3 to 8: 1700 metres, 5 junctions
  metres  junction       x       y
       0         3     400     300
     370         9     200     600
     870        10     700     600
    1270        11    1100     600
    1700         8    1400     300
$ bin/route tools/route/london.map 300,3500 12000,4000 | head -1
from 7484 to 8119: 200316 metres, 2540 junctions
```

(200 km to cross 12 km; finished 13936 on the way.)

## 08.03 Dijkstra, with a heap

Regions: search_dijkstra_scan (look at all n junctions for the nearest
REACHED one; ties to the smaller number), search_dijkstra (the heap of
lib/heap.c). `@from 08.03`: trace_reached, the Waiting entry type with its
pool and by_key, trace_heap and trace_stale, and the --algo option.

The heap (lib/heap.c, 02.04) holds pointers, ordered by a Cmp, and has push,
pop, top and len, no decrease-key and no way to find an item. So: **lazy
deletion**. A junction given a shorter distance is pushed again, as a new
entry (key, distance, junction) from a pool of 2M+1 entries (each road is
followed once from each end at most, and only an improvement pushes, so that
is enough, and the pointers never move). The newer, smaller entry comes off
first and finishes the junction; the old one stays in the heap until it
comes to the top, when its junction is FINISHED already and it is thrown
away (`stale`). Pops = finished + stale; the heap can hold more entries than
junctions (at most the pushes). The cost is a larger heap: log of entries,
not of junctions, which is at most log(2M+1), a step or so more.

On London, west to east (300,3500 to 12000,4000), 12973 metres:

```
dijkstra-scan: finished 15492, reached 15585, scanned 267391920, relaxed 41480
dijkstra:      finished 15492, reached 15585, relaxed 41480, stale 1674
               heap: pushes 17270, pops 17166, comparisons 220317, moves 135195
```

The same junctions finished, in the same order; 267 million junctions looked
at against 220 thousand comparisons. Times (London, 50 random pairs, each a
whole run of route): dijkstra-scan 53.5 ms a route (82.6 ms west to east),
dijkstra 5.4 ms, of which loading the map is 4.7 ms (`--info`): the search
itself is under a millisecond. Measured on made-up cities, junction 0 to the
far corner:

```
$ python3 bench/grow.py --input citymap --start 1000 --limit 5 bin/route --algo=dijkstra-scan {} 0,0 100000000,100000000
        n       bytes   seconds  ratio
    16000      556216     0.081    3.4
    32000     1181606     0.302    3.7
    64000     2424133     1.164    3.9
   128000     5032970     4.598    3.9
   256000    10486870    18.041    3.9
growth: about n^2
$ python3 bench/grow.py --input citymap --start 16000 --max 2048000 bin/route --algo=dijkstra {} 0,0 100000000,100000000
   256000    10486870     0.064    1.9
   512000    21456811     0.125    2.0
  1024000    43461368     0.257    2.1
  2048000    92131925     0.536    2.1
growth: about n
```

(The heap's times are mostly reading the file: compare --info above.) Where
the scan stops being usable: on central London it is 50 to 80 ms a route,
usable for one route and not for a service answering many; at 256000
junctions, a whole city's roads, 18 s a route; at 2 million (by the ratio, not
run) about 20 minutes, against half a second.

Break it 1 (order the heap by junction number, not distance: delete the two
lines `if (x->key != y->key) return x->key < y->key ? -1 : 1;` in by_key).
Junctions are finished before their distance is known, and stay finished:

```
$ bin/route tools/route/london.map 300,3500 12000,4000 | head -1
from 7484 to 8119: 27130 metres, 310 junctions          (12973 before)
$ bin/route tools/route/london.map 4500,3500 8000,5000 | head -1
from 7410 to 11582: 13323 metres, 172 junctions         (4131 before)
```

(The tiny map's 3 to 8 still comes out right: its main street happens to be
in number order. Use London.)

Break it 2 (forget the stale check: delete the `if (state[u] == FINISHED) {
... continue; }` block in search_dijkstra). Nothing goes wrong with the
route, but every old entry finishes its junction again and follows its
roads again for nothing:

```
stats: route: ..., reached 15585, finished 17166, ..., relaxed 46861, stale 0     (west to east)
trace: dijkstra: finish 6 at 1030 (from 5); heap: 6:1120(old) 7:1230 10:1120(old) 8:1400 11:1350
trace: dijkstra: finish 6 at 1030 (from 5); heap: 10:1120(old) 7:1230 11:1350 8:1400   (tiny, 0 to 8)
```

More finished than reached is the giveaway. (It stays right because dist[u]
is already the shortest, so following the roads again improves nothing.)

## 08.04 A*: searching towards the goal

Regions: guess (the straight line to TO: sqrt of dx*dx + dy*dy), search_astar
(search_dijkstra with the key distance + guess; the start pushed with its
guess). The Algo line is `@from 08.04`; astar is the default from here.

Why the guess must never overestimate: A* finishes the junction with the
smallest distance + guess. If the guess at a junction on the best route is
too big, the end can come off the heap first, by a worse route, and the
search stops there. With a guess no bigger than the real rest of the way,
the end's key (its distance, guess 0) cannot come off before any junction of
a shorter route. The straight line is such a guess because no road is shorter
than the straight line between its ends (the map is made so: gen.py rounds
every length up and checks it), and a route is a chain of roads. It is also
consistent (guess(u) <= road(u,v) + guess(v), the triangle inequality), so
a junction once finished is never improved later, which is what lets the
code skip finished junctions. A guess of 0 is Dijkstra: with `return 0 *
sqrt(...)` route finished 15492 west to east, as dijkstra does.

Counts on London (dijkstra against astar, same metres):

```
west to east, 12973 m:     finished 15492 against 5245;  reached 15585 against 5582
centre, 4131 m:            finished  6040 against  544;  reached  6276 against  657
```

(The 08.04 test: over 16 pairs, A* finishes less than half of Dijkstra's
junctions, and exactly the junctions whose distance plus guess is below the
route, plus perhaps some equal to it.) Times are no different here (5.6 ms
against 5.4 ms a route): loading the map is most of it. Counts tell this one,
or the picture: `--svg` of the centre pair shows Dijkstra's disc of 6040
junctions round the start and A*'s narrow band along the route.

On the made-up grid, corner to corner, A* gains little: on 99856 junctions
it finishes 89074 against Dijkstra's 99856 (and 2048000 junctions take
0.572 s against 0.536 s). Between two corners of a grid the junctions off
the diagonal are nearly as good a way as those on it, so the guess rules
little out. Worth a sentence.

Break it (a guess twice the straight line: `return sqrt(dx * dx + dy * dy);`
becomes `return 2 * sqrt(dx * dx + dy * dy);`):

```
$ bin/route tools/route/tiny.map 3 8
from 3 to 8: 1200 metres, 3 junctions                 (the ring: 1000 before)
west to east:  13458 metres, 222 junctions; finished 238   (12973; 5245 before)
centre:         4141 metres,  71 junctions; finished  78   (4131; 544 before)
$ DS_TRACE=1 bin/route tools/route/tiny.map 3 8
trace: astar: finish 3 at 0, guess 2000, sum 2000 (start); heap: 1:1766 4:1800 2:2900 0:3098 9:2844
trace: astar: finish 1 at 600, guess 1166, sum 1766 (from 3); heap: 8:1200 4:1800 6:1720 0:3098 9:2844 2:2900
trace: astar: finish 8 at 1200, guess 0, sum 1200 (from 1); heap: 6:1720 4:1800 2:2900 0:3098 9:2844
```

A guess just 1.1 times the line: west to east 12974 metres (1 too many),
finished 1404; centre 4131 (right), finished 239. Overestimating trades
the guarantee for speed (weighted A*), which some route planners do on
purpose; the lesson's point is that it is then a trade, not the shortest.

## The tests and the timeline

tests/tools/route.py has the references: load() (the map read plainly),
ref_dijkstra (heapq), ref_bfs, ref_pieces, nearest(), parse() of route's
output and check_route() (each junction joined to the next by a road, the
metres adding up, coordinates right). 08.01: --info against the reference on
tiny, London and a made-up city, roads read exactly 2M (lists) and N*M
(edges), the trace, the SVG and its credit, errors. 08.02: 22 pairs, hops
equal to the reference's, the finished junctions between those nearer and
those as near, BFS longer on at least half. 08.03: 16 pairs, both Dijkstras
equal to the reference, finished bounds, scan and heap finishing the same,
scanned = n * finished, pops = finished + stale, some stale on London, and
heap comparisons under a hundredth of the scan's looks west to east; the
traces. 08.04: every road at least its straight line; 16 pairs, astar =
dijkstra = reference, A*'s finished junctions bounded by distance + guess,
under half of Dijkstra's in total; the tiny trace. Nothing asserts on time.

check-timeline types, at 08.01: `bin/route --info tools/route/tiny.map`
and the "no search yet" error; at 08.02 the BFS route 3 to 8 and the
unknown --algo; at 08.03 the shortest route, --algo=bfs and dijkstra-scan,
and the missing astar; at 08.04 dijkstra. timeline_after holds --info's
pieces on London to the reference, and from 08.02 four routes (hops at
08.02, metres after).
