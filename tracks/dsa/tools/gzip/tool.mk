# gzip and gunzip: making files smaller with DEFLATE (module 09).
#
# @from 10.01
# What git reuses goes into the library:
# @else
# # The structures go into the library:
# @end
#   lib/huffman.c   Huffman codes
#   lib/inflate.c   raw inflate                                      @from 09.02
#   lib/lz77.c      LZ77                                             @from 09.03
#   lib/deflate.c   raw deflate                                      @from 09.04
# The gzip file format (tools/gzip/gz.c) and the two programs stay here.   @from 09.02

TOOLS += bin/gzip
TOOLS += bin/gunzip                       # @from 09.02

LIB += build/lib/huffman.o
LIB += build/lib/inflate.o                # @from 09.02
LIB += build/lib/lz77.o                   # @from 09.03
LIB += build/lib/deflate.o                # @from 09.04

# Every header of this module; each object here is built again when any changes.
GZIP_H = lib/ds.h lib/huffman.h
GZIP_H += lib/inflate.h tools/gzip/gz.h   # @from 09.02
GZIP_H += lib/lz77.h                      # @from 09.03
GZIP_H += lib/deflate.h                   # @from 09.04

GZIP_OBJ = build/gzip/gzip.o
GZIP_OBJ += build/gzip/gz.o               # @from 09.03

bin/gzip: $(GZIP_OBJ) build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/gzip $(GZIP_OBJ) build/libds.a

build/gzip/gzip.o: tools/gzip/gzip.c $(GZIP_H)
	@mkdir -p build/gzip
	$(CC) $(CFLAGS) -c -o build/gzip/gzip.o tools/gzip/gzip.c

build/lib/huffman.o: lib/huffman.c $(GZIP_H)
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/huffman.o lib/huffman.c

# @from 09.02
bin/gunzip: build/gzip/gunzip.o build/gzip/gz.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/gunzip build/gzip/gunzip.o build/gzip/gz.o build/libds.a

build/gzip/gunzip.o: tools/gzip/gunzip.c $(GZIP_H)
	@mkdir -p build/gzip
	$(CC) $(CFLAGS) -c -o build/gzip/gunzip.o tools/gzip/gunzip.c

build/gzip/gz.o: tools/gzip/gz.c $(GZIP_H)
	@mkdir -p build/gzip
	$(CC) $(CFLAGS) -c -o build/gzip/gz.o tools/gzip/gz.c

build/lib/inflate.o: lib/inflate.c $(GZIP_H)
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/inflate.o lib/inflate.c
# @end

# @from 09.03
build/lib/lz77.o: lib/lz77.c $(GZIP_H)
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/lz77.o lib/lz77.c
# @end

# @from 09.04
build/lib/deflate.o: lib/deflate.c $(GZIP_H)
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/deflate.o lib/deflate.c
# @end
