# sort: sorting lines as LC_ALL=C sort does (module 02).

TOOLS += bin/sort

bin/sort: build/sort/sort.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/sort build/sort/sort.o build/libds.a

build/sort/sort.o: tools/sort/sort.c lib/ds.h
	@mkdir -p build/sort
	$(CC) $(CFLAGS) -c -o build/sort/sort.o tools/sort/sort.c
