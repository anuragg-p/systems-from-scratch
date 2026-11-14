# grep: the lines of a text that match a pattern (module 04), and the
# structures it brings to lib/: a fixed-string search, then a regular
# expression's tree, its NFA, and a DFA built from the NFA as it runs.

TOOLS += bin/grep

LIB += build/lib/strsearch.o
LIB += build/lib/re.o      # @from 04.02
LIB += build/lib/nfa.o     # @from 04.03
LIB += build/lib/dfa.o     # @from 04.04

# The headers grep.c includes.
GREP_H = lib/ds.h lib/strsearch.h
GREP_H += lib/re.h         # @from 04.02
GREP_H += lib/nfa.h        # @from 04.03
GREP_H += lib/dfa.h        # @from 04.04

build/lib/strsearch.o: lib/strsearch.c lib/strsearch.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/strsearch.o lib/strsearch.c

# @from 04.02
build/lib/re.o: lib/re.c lib/re.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/re.o lib/re.c
# @end

# @from 04.03
build/lib/nfa.o: lib/nfa.c lib/nfa.h lib/re.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/nfa.o lib/nfa.c
# @end

# @from 04.04
build/lib/dfa.o: lib/dfa.c lib/dfa.h lib/nfa.h lib/re.h lib/ds.h
	@mkdir -p build/lib
	$(CC) $(CFLAGS) -c -o build/lib/dfa.o lib/dfa.c
# @end

bin/grep: build/grep/grep.o build/libds.a
	@mkdir -p bin
	$(CC) $(CFLAGS) -o bin/grep build/grep/grep.o build/libds.a

build/grep/grep.o: tools/grep/grep.c $(GREP_H)
	@mkdir -p build/grep
	$(CC) $(CFLAGS) -c -o build/grep/grep.o tools/grep/grep.c
