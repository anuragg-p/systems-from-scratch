# paste -s: the workbench's job, done slow and done fast (module 00).

TOOLS += bin/paste

bin/paste: build/paste/paste.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/paste build/paste/paste.o build/libds.a

build/paste/paste.o: tools/paste/paste.c lib/ds.h
	@mkdir -p build/paste
	$(CC) $(CFLAGS) -c -o build/paste/paste.o tools/paste/paste.c
