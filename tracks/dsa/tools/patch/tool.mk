# patch: applying a unified diff (module 06). It reads files into lines with
# lib/diff.c, diff's own engine.

TOOLS += bin/patch

bin/patch: build/patch/patch.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/patch build/patch/patch.o build/libds.a

build/patch/patch.o: tools/patch/patch.c lib/ds.h lib/diff.h
	@mkdir -p build/patch
	$(CC) $(CFLAGS) -c -o build/patch/patch.o tools/patch/patch.c
