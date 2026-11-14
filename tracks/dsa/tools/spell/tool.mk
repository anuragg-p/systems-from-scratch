# spell: the words of a text that are not in the dictionary (module 05).
# It brings three structures to lib/: a trie, a Bloom filter and the edit
# distance, each in its own file with its own header.

TOOLS += bin/spell

LIB += build/lib/trie.o
LIB += build/lib/bloom.o   # @from 05.02
LIB += build/lib/edit.o    # @from 05.03

SPELL_H = lib/ds.h lib/trie.h
SPELL_H += lib/bloom.h     # @from 05.02
SPELL_H += lib/edit.h      # @from 05.03

bin/spell: build/spell/spell.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/spell build/spell/spell.o build/libds.a -lm

build/spell/spell.o: tools/spell/spell.c $(SPELL_H)
	@mkdir -p build/spell
	$(CC) $(CFLAGS) -c -o build/spell/spell.o tools/spell/spell.c

build/lib/trie.o: lib/trie.c $(SPELL_H)
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/trie.o lib/trie.c

# @from 05.02
build/lib/bloom.o: lib/bloom.c lib/bloom.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/bloom.o lib/bloom.c
# @end

# @from 05.03
build/lib/edit.o: lib/edit.c lib/edit.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/edit.o lib/edit.c
# @end
