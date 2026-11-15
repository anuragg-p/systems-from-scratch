# diff: comparing two files line by line (module 06). tools/diff/diff.c is
# @from 10.04
# the command; the engine, which git's diff uses as well, is in lib/, behind
# @else
# # the command; the engine, which other tools can use too, is in lib/, behind
# @end
# lib/diff.h:
#   lib/diff.c    the table
#   lib/myers.c   Myers' search   @from 06.03

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
