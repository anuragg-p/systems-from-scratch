# freq: the most common words in a text (module 01).

TOOLS += bin/freq

bin/freq: build/freq/freq.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/freq build/freq/freq.o build/libds.a

build/freq/freq.o: tools/freq/freq.c lib/ds.h
	@mkdir -p build/freq
	$(CC) $(CFLAGS) -c -o build/freq/freq.o tools/freq/freq.c
