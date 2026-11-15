# dsa - data structures and algorithms, by building the tools that use them.
#
# @from 01.01
#   make              build every tool: bin/paste, bin/freq, ...
#   make bin/freq     build one of them
# @else
# #   make              build every tool: bin/paste
# #   make bin/paste    build one of them
# @end
#   make clean        remove what make built
#
# Plain C11 and libc. The library in lib/ is compiled into build/lib/ and
# archived as build/libds.a; each tool is a directory under tools/ whose
# tool.mk says how to build it into bin/<name>. This file reads every
# tools/*/tool.mk, so adding a tool means adding its directory, nothing
# here. Only rules, recipes, variables and include are used.

CC = cc
CFLAGS = -std=c11 -O2 -g -Wall -Wextra -Wno-unused-parameter -Wno-unused-function -Ilib $(EXTRA_CFLAGS)
CFLAGS += -D_DEFAULT_SOURCE -D_DARWIN_C_SOURCE -D_POSIX_C_SOURCE=200809L

# The first rule is what plain "make" builds; each tool.mk adds its program
# to TOOLS, and the last line of this file makes "all" depend on them.
all:

# The library: one object for each file of lib/.
LIB = build/lib/util.o
LIB += build/lib/array.o   # @from 01.01
LIB += build/lib/table.o   # @from 01.02
LIB += build/lib/sort.o    # @from 02.01
LIB += build/lib/heap.o    # @from 02.04

build/lib/util.o: lib/util.c lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/util.o lib/util.c

# @from 01.01
build/lib/array.o: lib/array.c lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/array.o lib/array.c
# @end

# @from 01.02
build/lib/table.o: lib/table.c lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/table.o lib/table.c
# @end

# @from 02.01
build/lib/sort.o: lib/sort.c lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/sort.o lib/sort.c
# @end

# @from 02.04
build/lib/heap.o: lib/heap.c lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/heap.o lib/heap.c
# @end

# The tools. Each tool.mk adds "bin/<name>" to TOOLS and the rules that
# build it, linking its objects with build/libds.a. A tool that brings a
# structure of its own to lib/ adds its object to LIB there as well.
include tools/*/tool.mk

# Every object of LIB in one archive, made again when any of them changes.
# (Here at the end, after the tool.mk files, so it sees all of LIB.)
build/libds.a: $(LIB)
	@rm -f build/libds.a
	ar rcs build/libds.a $(LIB)

clean:
	rm -rf build bin

.PHONY: all clean

all: $(TOOLS)
