# diff: comparing two files line by line (module 06). The engine is in lib/:
# lib/diff.c (the table) and lib/myers.c (Myers' search), behind lib/diff.h,
# for git's diff to use as well; tools/diff/diff.c is the command.

TOOLS += bin/diff
LIB += build/lib/diff.o
LIB += build/lib/myers.o   # @from 06.03

bin/diff: build/diff/diff.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/diff build/diff/diff.o build/libds.a

build/diff/diff.o: tools/diff/diff.c lib/ds.h lib/diff.h
	@mkdir -p build/diff
	$(CC) $(CFLAGS) -c -o build/diff/diff.o tools/diff/diff.c

build/lib/diff.o: lib/diff.c lib/ds.h lib/diff.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/diff.o lib/diff.c

# @from 06.03
build/lib/myers.o: lib/myers.c lib/ds.h lib/diff.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/myers.o lib/myers.c
# @end
