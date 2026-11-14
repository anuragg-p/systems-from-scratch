# git: the capstone (module 10), on the library the other modules built:
# the hash table (01), the sorts and the heap (02), diff (06), inflate and
# deflate (09). What is new in lib/:
#   lib/sha1sum.c   SHA-1, the names of objects
#   lib/zframe.c    the zlib format around DEFLATE, with Adler-32
# The rest is git's own, in tools/git/.

TOOLS += bin/git
LIB += build/lib/sha1sum.o
LIB += build/lib/zframe.o

GIT_H = lib/ds.h lib/sha1sum.h lib/zframe.h lib/deflate.h lib/lz77.h lib/inflate.h tools/git/git.h
GIT_H += lib/diff.h                     # @from 10.04

GIT_OBJ = build/git/git.o build/git/repo.o build/git/object.o
GIT_OBJ += build/git/tree.o build/git/index.o      # @from 10.02
GIT_OBJ += build/git/refs.o build/git/commit.o     # @from 10.03
GIT_OBJ += build/git/compare.o                     # @from 10.04

bin/git: $(GIT_OBJ) build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/git $(GIT_OBJ) build/libds.a

build/lib/sha1sum.o: lib/sha1sum.c lib/sha1sum.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/sha1sum.o lib/sha1sum.c

build/lib/zframe.o: lib/zframe.c $(GIT_H)
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/zframe.o lib/zframe.c

build/git/git.o: tools/git/git.c $(GIT_H)
	@mkdir -p build/git
	$(CC) $(CFLAGS) -c -o build/git/git.o tools/git/git.c

build/git/repo.o: tools/git/repo.c $(GIT_H)
	@mkdir -p build/git
	$(CC) $(CFLAGS) -c -o build/git/repo.o tools/git/repo.c

build/git/object.o: tools/git/object.c $(GIT_H)
	@mkdir -p build/git
	$(CC) $(CFLAGS) -c -o build/git/object.o tools/git/object.c

# @from 10.02
build/git/tree.o: tools/git/tree.c $(GIT_H)
	@mkdir -p build/git
	$(CC) $(CFLAGS) -c -o build/git/tree.o tools/git/tree.c

build/git/index.o: tools/git/index.c $(GIT_H)
	@mkdir -p build/git
	$(CC) $(CFLAGS) -c -o build/git/index.o tools/git/index.c
# @end

# @from 10.03
build/git/refs.o: tools/git/refs.c $(GIT_H)
	@mkdir -p build/git
	$(CC) $(CFLAGS) -c -o build/git/refs.o tools/git/refs.c

build/git/commit.o: tools/git/commit.c $(GIT_H)
	@mkdir -p build/git
	$(CC) $(CFLAGS) -c -o build/git/commit.o tools/git/commit.c
# @end

# @from 10.04
build/git/compare.o: tools/git/compare.c $(GIT_H)
	@mkdir -p build/git
	$(CC) $(CFLAGS) -c -o build/git/compare.o tools/git/compare.c
# @end
