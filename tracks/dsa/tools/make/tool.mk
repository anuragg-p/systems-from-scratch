# make: reads a makefile, builds what is out of date, in order (module 07).

TOOLS += bin/make

# The structures it adds to lib/.
LIB += build/lib/depgraph.o
LIB += build/lib/readyq.o   # @from 07.04

build/lib/depgraph.o: lib/depgraph.c lib/depgraph.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/depgraph.o lib/depgraph.c

# @from 07.04
build/lib/readyq.o: lib/readyq.c lib/readyq.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/readyq.o lib/readyq.c
# @end

bin/make: build/make/make.o build/make/read.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/make build/make/make.o build/make/read.o build/libds.a

build/make/make.o: tools/make/make.c tools/make/make.h lib/depgraph.h lib/ds.h
	@mkdir -p build/make
	$(CC) $(CFLAGS) -c -o build/make/make.o tools/make/make.c

build/make/make.o: lib/readyq.h   # @from 07.04

build/make/read.o: tools/make/read.c tools/make/make.h lib/depgraph.h lib/ds.h
	@mkdir -p build/make
	$(CC) $(CFLAGS) -c -o build/make/read.o tools/make/read.c
