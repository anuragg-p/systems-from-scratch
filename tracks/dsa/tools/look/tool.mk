# look: lines of a sorted file that start with a string, by binary search (module 02).

TOOLS += bin/look

bin/look: build/look/look.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/look build/look/look.o build/libds.a

build/look/look.o: tools/look/look.c lib/ds.h
	@mkdir -p build/look
	$(CC) $(CFLAGS) -c -o build/look/look.o tools/look/look.c
