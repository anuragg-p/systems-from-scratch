# route: the shortest way between two junctions of a road map (module 08).
# It brings a structure of its own to the library: the road graph.

TOOLS += bin/route
LIB += build/lib/roadgraph.o

build/lib/roadgraph.o: lib/roadgraph.c lib/roadgraph.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/roadgraph.o lib/roadgraph.c

bin/route: build/route/route.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/route build/route/route.o build/libds.a -lm

build/route/route.o: tools/route/route.c lib/ds.h lib/roadgraph.h
	@mkdir -p build/route
	$(CC) $(CFLAGS) -c -o build/route/route.o tools/route/route.c
