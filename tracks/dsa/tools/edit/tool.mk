# edit: a text editor, with its text in a structure of lib/ (module 03).
# The structures are lib's own: text.c holds what they share, and each one
# is an object of LIB, so it goes into build/libds.a with the others.

TOOLS += bin/edit

EDIT_H = lib/ds.h lib/text.h lib/flat.h
EDIT_H += lib/gap.h        # @from 03.02
EDIT_H += lib/undo.h       # @from 03.03
EDIT_H += lib/pieces.h     # @from 03.04
EDIT_H += lib/ptree.h      # @from 03.05

LIB += build/lib/text.o build/lib/flat.o
LIB += build/lib/gap.o     # @from 03.02
LIB += build/lib/undo.o    # @from 03.03
LIB += build/lib/pieces.o  # @from 03.04
LIB += build/lib/ptree.o   # @from 03.05

bin/edit: build/edit/edit.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/edit build/edit/edit.o build/libds.a

build/edit/edit.o: tools/edit/edit.c $(EDIT_H)
	@mkdir -p build/edit
	$(CC) $(CFLAGS) -c -o build/edit/edit.o tools/edit/edit.c

build/lib/text.o: lib/text.c lib/ds.h lib/text.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/text.o lib/text.c

build/lib/flat.o: lib/flat.c lib/ds.h lib/text.h lib/flat.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/flat.o lib/flat.c

# @from 03.02
build/lib/gap.o: lib/gap.c lib/ds.h lib/text.h lib/gap.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/gap.o lib/gap.c
# @end

# @from 03.03
build/lib/undo.o: lib/undo.c lib/ds.h lib/text.h lib/undo.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/undo.o lib/undo.c
# @end

# @from 03.04
build/lib/pieces.o: lib/pieces.c lib/ds.h lib/text.h lib/pieces.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/pieces.o lib/pieces.c
# @end

# @from 03.05
build/lib/ptree.o: lib/ptree.c lib/ds.h lib/text.h lib/pieces.h lib/ptree.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/ptree.o lib/ptree.c
# @end
